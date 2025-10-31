#!/usr/bin/env python3
"""
Network Configuration Automation CLI
Command-line interface for network automation tasks.
"""

import argparse
import sys
import yaml  # type: ignore[reportMissingModuleSource]
from pathlib import Path
from typing import List, Dict, Any, Optional

# Pre-declare names so static type checkers don't report them as possibly unbound
Console: Any = None
Progress: Any = None
console: Optional[Any] = None
rich_available: bool = False

from typing import cast

try:
    from rich.console import Console as _Console  # type: ignore[reportMissingImports]
    from rich.progress import Progress as _Progress  # type: ignore[reportMissingImports]

    # Cast unknown third-party types to Any for the type checker while keeping
    # the runtime classes available when Rich is installed.
    Console = cast(Any, _Console)
    Progress = cast(Any, _Progress)
    rich_available = True
    # instantiate console only when rich is available
    console = cast(Optional[Any], Console())
except ImportError:
    rich_available = False

from netauto import NetworkDevice, ConfigurationTask, ConfigValidator, setup_logger
from netauto.secrets_manager import SecretsManager
from netauto.config_templates import TemplateManager


# Initialize logger and console
logger = setup_logger("cli", log_level="INFO")
# console is created during import if rich is available; otherwise remains None

from argparse import Namespace


def print_output(message: str, style: str = ""):
    """Print output with optional Rich formatting."""
    if rich_available and console:
        console.print(message, style=style)
    else:
        print(message)


def load_inventory(inventory_file: str) -> List[Dict[str, Any]]:
    """
    Load device inventory from YAML file.
    
    Args:
        inventory_file: Path to inventory file
        
    Returns:
        List of device dictionaries
    """
    inventory_path = Path(inventory_file)
    
    if not inventory_path.exists():
        print_output(f"[red]Error: Inventory file not found: {inventory_file}[/red]")
        sys.exit(1)
    
    with open(inventory_path, 'r') as f:
        inventory = yaml.safe_load(f)
    
    return inventory.get('devices', [])


def cmd_configure(args: Namespace) -> None:
    """Configure a single device."""
    print_output(f"\n[cyan]Configuring device: {args.host}[/cyan]")
    
    try:
        # Create device connection
        host: str = args.host
        device_type: str = args.device_type
        port: int = args.port

        device = NetworkDevice(host=host, device_type=device_type, port=port)
        
        device.connect()
        print_output(f"[green]✓ Connected to {args.host}[/green]")
        
        # Prepare configuration
        if args.template:
            # Load template variables from file if provided
            template_vars: Dict[str, Any] = {}
            if args.vars_file:
                vars_path = Path(args.vars_file)
                if vars_path.exists():
                    with vars_path.open('r') as f:
                        template_vars = yaml.safe_load(f)
            
            # Render template
            template_manager = TemplateManager()
            config_text = template_manager.render_template(str(args.template), template_vars)
            config_commands = config_text.strip().split('\n')
            
            print_output(f"[cyan]Applying configuration from template: {args.template}[/cyan]")
        elif args.commands:
            config_commands: List[str] = list(args.commands)
            print_output(f"[cyan]Applying {len(config_commands)} commands[/cyan]")
        else:
            print_output("[red]Error: Must provide either --template or --commands[/red]")
            sys.exit(1)
        
        # Apply configuration
        dry_run: bool = bool(args.dry_run)
        save: bool = bool(args.save)
        verbose: bool = bool(args.verbose)

        if dry_run:
            print_output("[yellow]DRY RUN - Configuration not applied[/yellow]")
            for cmd in config_commands:
                print_output(f"  {cmd}")
        else:
            output = device.send_config_set(config_commands)

            if save:
                device.save_config()
                print_output("[green]✓ Configuration saved[/green]")

            if verbose:
                print_output("\n[cyan]Device Output:[/cyan]")
                print_output(output)
        
        device.disconnect()
        print_output(f"[green]✓ Configuration completed for {args.host}[/green]\n")
        
    except Exception as e:
        print_output(f"[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


def cmd_configure_inventory(args: Namespace) -> None:
    """Configure multiple devices from inventory."""
    print_output(f"\n[cyan]Loading inventory: {args.inventory}[/cyan]")
    
    devices: List[Dict[str, Any]] = load_inventory(args.inventory)
    print_output(f"[green]Loaded {len(devices)} devices[/green]\n")
    
    # Create configuration task
    task = ConfigurationTask(
        devices=devices,
        dry_run=args.dry_run,
    )
    
    # Prepare configuration
    config_commands = None
    template_name = None
    template_vars_list = None
    
    if args.template:
        template_name = args.template
        print_output(f"[cyan]Using template: {template_name}[/cyan]")
        
        # Load device-specific variables from inventory
        if args.vars_file:
            vars_path = Path(args.vars_file)
            if vars_path.exists():
                with vars_path.open('r') as f:
                    all_vars = yaml.safe_load(f)
                    template_vars_list = [
                        all_vars.get('device_vars', {}).get(dev.get('name', ''), {})
                        for dev in devices
                    ]
    elif args.commands:
        config_commands = list(args.commands) if args.commands else None
        if config_commands:
            print_output(f"[cyan]Using {len(config_commands)} commands[/cyan]")
    
    # Execute configuration
    if rich_available:
        with Progress() as progress:
            task_id = progress.add_task("[cyan]Configuring devices...", total=len(devices))
            
            result = task.configure_multiple_devices(
                config_commands=config_commands,
                template_name=template_name,
                template_vars_list=template_vars_list,
                save_config=args.save,
                validate_after=args.validate,
                parallel=args.parallel,
                max_workers=args.max_workers,
            )
            
            progress.update(task_id, completed=len(devices))
    else:
        result = task.configure_multiple_devices(
            config_commands=config_commands,
            template_name=template_name,
            template_vars_list=template_vars_list,
            save_config=args.save,
            validate_after=args.validate,
            parallel=args.parallel,
            max_workers=args.max_workers,
        )
    
    # Display results
    print_output(f"\n[cyan]Configuration Summary:[/cyan]")
    print_output(f"  Total devices: {result['total_devices']}")
    print_output(f"  [green]Successful: {result['successful']}[/green]")
    print_output(f"  [red]Failed: {result['failed']}[/red]")
    print_output(f"  Elapsed time: {result['elapsed_time']}s\n")
    
    if args.verbose:
        for dev_result in result['results']:
            status = "[green]✓[/green]" if dev_result.get('success') else "[red]✗[/red]"
            print_output(f"{status} {dev_result.get('host')}: {dev_result.get('message')}")


def cmd_backup(args: Namespace) -> None:
    """Backup device configurations."""
    print_output(f"\n[cyan]Backing up configurations...[/cyan]")
    
    if args.inventory:
        devices = load_inventory(args.inventory)
    else:
        devices = [{
            "host": args.host,
            "device_type": args.device_type,
            "port": args.port,
        }]
    
    task = ConfigurationTask(devices=devices)
    result = task.backup_configs(
        backup_dir=args.output,
        parallel=args.parallel,
        max_workers=args.max_workers,
    )
    
    print_output(f"\n[cyan]Backup Summary:[/cyan]")
    print_output(f"  Total devices: {result['total_devices']}")
    print_output(f"  [green]Successful: {result['successful']}[/green]")
    print_output(f"  [red]Failed: {result['failed']}[/red]")
    print_output(f"  Backup directory: {result['backup_directory']}\n")


def cmd_validate(args: Namespace) -> None:
    """Run validation checks on a device."""
    print_output(f"\n[cyan]Validating device: {args.host}[/cyan]")
    
    try:
        host: str = args.host
        device_type: str = args.device_type
        port: int = args.port

        device = NetworkDevice(host=host, device_type=device_type, port=port)
        
        device.connect()
        validator = ConfigValidator(device)
        
        # Run basic validation
        print_output("[cyan]Running connectivity check...[/cyan]")
        validator.verify_connectivity()
        print_output("[green]✓ Connectivity verified[/green]")
        
        # Get device info
        info = validator.get_device_info()
        print_output(f"\n[cyan]Device Information:[/cyan]")
        print_output(f"  Hostname: {info.get('hostname', 'Unknown')}")
        print_output(f"  Version: {info.get('version', 'Unknown')}")
        print_output(f"  Uptime: {info.get('uptime', 'Unknown')}")
        
        device.disconnect()
        print_output(f"\n[green]✓ Validation completed for {args.host}[/green]\n")
        
    except Exception as e:
        print_output(f"[red]✗ Validation failed: {str(e)}[/red]")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Network Configuration Automation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Configure command
    configure_parser = subparsers.add_parser('configure', help='Configure a single device')
    configure_parser.add_argument('--host', required=True, help='Device IP or hostname')
    configure_parser.add_argument('--device-type', default='cisco_ios', help='Device type')
    configure_parser.add_argument('--port', type=int, default=22, help='SSH port')
    configure_parser.add_argument('--template', help='Configuration template file')
    configure_parser.add_argument('--vars-file', help='Template variables YAML file')
    configure_parser.add_argument('--commands', nargs='+', help='Configuration commands')
    configure_parser.add_argument('--save', action='store_true', help='Save configuration')
    configure_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    configure_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    # Configure inventory command
    inventory_parser = subparsers.add_parser('configure-inventory', 
                                              help='Configure devices from inventory')
    inventory_parser.add_argument('--inventory', required=True, help='Inventory YAML file')
    inventory_parser.add_argument('--template', help='Configuration template file')
    inventory_parser.add_argument('--vars-file', help='Template variables YAML file')
    inventory_parser.add_argument('--commands', nargs='+', help='Configuration commands')
    inventory_parser.add_argument('--save', action='store_true', help='Save configuration')
    inventory_parser.add_argument('--validate', action='store_true', help='Run validation')
    inventory_parser.add_argument('--parallel', action='store_true', help='Parallel execution')
    inventory_parser.add_argument('--max-workers', type=int, default=5, 
                                   help='Max parallel workers')
    inventory_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    inventory_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Backup device configurations')
    backup_parser.add_argument('--host', help='Device IP or hostname')
    backup_parser.add_argument('--inventory', help='Inventory YAML file')
    backup_parser.add_argument('--device-type', default='cisco_ios', help='Device type')
    backup_parser.add_argument('--port', type=int, default=22, help='SSH port')
    backup_parser.add_argument('--output', default='backups', help='Backup output directory')
    backup_parser.add_argument('--parallel', action='store_true', help='Parallel execution')
    backup_parser.add_argument('--max-workers', type=int, default=5, 
                                help='Max parallel workers')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate device state')
    validate_parser.add_argument('--host', required=True, help='Device IP or hostname')
    validate_parser.add_argument('--device-type', default='cisco_ios', help='Device type')
    validate_parser.add_argument('--port', type=int, default=22, help='SSH port')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Check credentials
    if not SecretsManager.validate_credentials():
        print_output("[red]Error: Missing credentials. Please set environment variables.[/red]")
        print_output("Required: DEVICE_USERNAME, DEVICE_PASSWORD")
        sys.exit(1)
    
    # Route to appropriate command handler
    if args.command == 'configure':
        cmd_configure(args)
    elif args.command == 'configure-inventory':
        cmd_configure_inventory(args)
    elif args.command == 'backup':
        cmd_backup(args)
    elif args.command == 'validate':
        cmd_validate(args)


if __name__ == '__main__':
    main()
