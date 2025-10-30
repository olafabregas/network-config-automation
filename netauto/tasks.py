"""
Tasks - Main automation routines and orchestration logic.
Coordinates device connections, configuration, and validation.
"""

import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from .connect import NetworkDevice, DeviceConnectionError
from .config_templates import TemplateManager
from .validators import ConfigValidator, ValidationError
from .logger import setup_logger


logger = setup_logger("netauto.tasks")


class ConfigurationTask:
    """Orchestrates configuration deployment tasks."""
    
    def __init__(
        self,
        devices: List[Dict[str, Any]],
        template_dir: Optional[str] = None,
        dry_run: bool = False,
    ):
        """
        Initialize a configuration task.
        
        Args:
            devices: List of device dictionaries with connection parameters
            template_dir: Path to templates directory
            dry_run: If True, only simulate without applying changes
        """
        self.devices = devices
        self.template_manager = TemplateManager(template_dir)
        self.dry_run = dry_run
        self.results: Dict[str, Any] = {}
        
        logger.info(f"ConfigurationTask initialized with {len(devices)} devices")
        if dry_run:
            logger.info("DRY RUN MODE: No changes will be applied")
    
    def configure_device(
        self,
        device_info: Dict[str, Any],
        config_commands: Optional[List[str]] = None,
        template_name: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None,
        save_config: bool = True,
        validate_after: bool = True,
    ) -> Dict[str, Any]:
        """
        Configure a single device.
        
        Args:
            device_info: Device connection parameters
            config_commands: List of commands to apply (optional)
            template_name: Template file to use (optional)
            template_vars: Variables for template rendering (optional)
            save_config: Save configuration after applying
            validate_after: Run validation after configuration
            
        Returns:
            Dictionary with task results
        """
        host = device_info.get("host", "unknown")
        result: Dict[str, Any] = {
            "host": host,
            "success": False,
            "message": "",
            "output": "",
            "validation": {},
        }
        
        try:
            # Create device connection
            device = NetworkDevice(
                host=device_info["host"],
                device_type=device_info.get("device_type", "cisco_ios"),
                port=device_info.get("port", 22),
                username=device_info.get("username"),
                password=device_info.get("password"),
                secret=device_info.get("secret"),
            )
            
            # Connect to device
            logger.info(f"Connecting to {host}...")
            device.connect()
            
            # Prepare configuration
            if template_name and template_vars:
                config_text = self.template_manager.render_template(
                    template_name, template_vars
                )
                config_commands = config_text.strip().split("\n")
                logger.info(f"Rendered template {template_name} for {host}")
            
            if not config_commands:
                raise ValueError("No configuration commands or template provided")
            
            # Apply configuration
            if self.dry_run:
                logger.info(f"DRY RUN: Would apply {len(config_commands)} commands to {host}")
                result["output"] = "DRY RUN - No changes applied"
            else:
                logger.info(f"Applying {len(config_commands)} commands to {host}")
                output = device.send_config_set(config_commands)
                result["output"] = output
                
                # Save configuration
                if save_config:
                    logger.info(f"Saving configuration on {host}")
                    save_output = device.save_config()
                    result["output"] += f"\n{save_output}"
            
            # Validation
            if validate_after and not self.dry_run:
                logger.info(f"Running validation on {host}")
                validator = ConfigValidator(device)
                result["validation"] = {
                    "connectivity": validator.verify_connectivity(),
                    "device_info": validator.get_device_info(),
                }
            
            # Disconnect
            device.disconnect()
            
            result["success"] = True
            result["message"] = "Configuration applied successfully"
            logger.info(f"Configuration task completed successfully for {host}")
            
        except DeviceConnectionError as e:
            result["message"] = f"Connection error: {str(e)}"
            logger.error(f"Connection error for {host}: {str(e)}")
            
        except ValidationError as e:
            result["message"] = f"Validation error: {str(e)}"
            logger.error(f"Validation error for {host}: {str(e)}")
            
        except Exception as e:
            result["message"] = f"Error: {str(e)}"
            logger.error(f"Unexpected error for {host}: {str(e)}")
        
        return result
    
    def configure_multiple_devices(
        self,
        config_commands: Optional[List[str]] = None,
        template_name: Optional[str] = None,
        template_vars_list: Optional[List[Dict[str, Any]]] = None,
        save_config: bool = True,
        validate_after: bool = True,
        parallel: bool = False,
        max_workers: int = 5,
    ) -> Dict[str, Any]:
        """
        Configure multiple devices.
        
        Args:
            config_commands: List of commands to apply to all devices
            template_name: Template file to use
            template_vars_list: List of template variables (one per device)
            save_config: Save configuration after applying
            validate_after: Run validation after configuration
            parallel: Execute in parallel if True
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary with aggregated results
        """
        start_time = time.time()
        results: List[Dict[str, Any]] = []

        if parallel:
            logger.info(f"Starting parallel configuration with {max_workers} workers")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures: Dict[Future[Dict[str, Any]], str] = {}

                for idx, device_info in enumerate(self.devices):
                    template_vars: Optional[Dict[str, Any]] = None
                    if template_vars_list and idx < len(template_vars_list):
                        template_vars = template_vars_list[idx]

                    future = executor.submit(
                        self.configure_device,
                        device_info,
                        config_commands,
                        template_name,
                        template_vars,
                        save_config,
                        validate_after,
                    )
                    futures[future] = device_info.get("host", "unknown")

                for future in as_completed(list(futures.keys())):
                    host = futures[future]
                    try:
                        result: Dict[str, Any] = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Task failed for {host}: {str(e)}")
                        results.append({
                            "host": host,
                            "success": False,
                            "message": f"Task exception: {str(e)}",
                        })
        else:
            logger.info("Starting sequential configuration")
            for idx, device_info in enumerate(self.devices):
                template_vars: Optional[Dict[str, Any]] = None
                if template_vars_list and idx < len(template_vars_list):
                    template_vars = template_vars_list[idx]

                result = self.configure_device(
                    device_info,
                    config_commands,
                    template_name,
                    template_vars,
                    save_config,
                    validate_after,
                )
                results.append(result)

        # Aggregate results
        elapsed_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])
        failure_count = len(results) - success_count

        summary: Dict[str, Any] = {
            "total_devices": len(self.devices),
            "successful": success_count,
            "failed": failure_count,
            "elapsed_time": round(elapsed_time, 2),
            "results": results,
        }

        logger.info(
            f"Configuration task completed: {success_count} successful, "
            f"{failure_count} failed, {elapsed_time:.2f}s elapsed"
        )

        self.results = summary
        return summary
    
    def backup_configs(
        self,
        backup_dir: str,
        parallel: bool = False,
        max_workers: int = 5,
    ) -> Dict[str, Any]:
        """
        Backup configurations from all devices.
        
        Args:
            backup_dir: Directory to save backup files
            parallel: Execute in parallel if True
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary with backup results
        """
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting configuration backup to {backup_dir}")
        
        def backup_single_device(device_info: Dict[str, Any]) -> Dict[str, Any]:
            """Backup configuration from a single device."""
            host = device_info.get("host", "unknown")
            result: Dict[str, Any] = {"host": host, "success": False, "message": "", "file": ""}

            try:
                device = NetworkDevice(
                    host=device_info["host"],
                    device_type=device_info.get("device_type", "cisco_ios"),
                    username=device_info.get("username"),
                    password=device_info.get("password"),
                    secret=device_info.get("secret"),
                )

                device.connect()
                config = device.send_command("show running-config")
                device.disconnect()

                # Save to file
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{host}_{timestamp}.cfg"
                file_path = backup_path / filename

                with open(file_path, "w") as f:
                    f.write(config)

                result["success"] = True
                result["message"] = "Backup completed successfully"
                result["file"] = str(file_path)
                logger.info(f"Backup completed for {host}: {filename}")

            except Exception as e:
                result["message"] = f"Backup failed: {str(e)}"
                logger.error(f"Backup failed for {host}: {str(e)}")

            return result
        
        results: List[Dict[str, Any]] = []

        if parallel:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures: List[Future[Dict[str, Any]]] = [
                    executor.submit(backup_single_device, dev)
                    for dev in self.devices
                ]
                results = [f.result() for f in as_completed(futures)]
        else:
            results = [backup_single_device(dev) for dev in self.devices]
        
        success_count = sum(1 for r in results if r["success"])
        
        summary: Dict[str, Any] = {
            "total_devices": len(self.devices),
            "successful": success_count,
            "failed": len(results) - success_count,
            "backup_directory": str(backup_path),
            "results": results,
        }
        
        logger.info(f"Backup completed: {success_count}/{len(self.devices)} successful")
        return summary
