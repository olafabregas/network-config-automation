"""
Validators - Configuration and state validation logic.
Provides pre and post-deployment verification.
"""

import re
from typing import List, Dict, Any
from .logger import setup_logger
from .connect import NetworkDevice, DeviceConnectionError


logger = setup_logger("netauto.validators")


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class ConfigValidator:
    """Validates device configurations and states."""
    
    def __init__(self, device: NetworkDevice):
        """
        Initialize validator with a network device.
        
        Args:
            device: NetworkDevice instance
        """
        self.device = device
        logger.info(f"Validator initialized for {device.host}")
    
    def verify_connectivity(self) -> bool:
        """
        Verify basic connectivity to the device.
        
        Returns:
            True if device is reachable
            
        Raises:
            ValidationError: If connectivity check fails
        """
        try:
            if not self.device.is_alive():
                raise ValidationError(f"Device {self.device.host} is not reachable")
            
            logger.info(f"Connectivity verified for {self.device.host}")
            return True
            
        except Exception as e:
            error_msg = f"Connectivity check failed for {self.device.host}: {str(e)}"
            logger.error(error_msg)
            raise ValidationError(error_msg)
    
    def verify_interface_status(
        self,
        interface: str,
        expected_status: str = "up",
    ) -> bool:
        """
        Verify interface status.
        
        Args:
            interface: Interface name (e.g., 'GigabitEthernet0/1')
            expected_status: Expected status ('up' or 'down')
            
        Returns:
            True if interface status matches expected
            
        Raises:
            ValidationError: If status doesn't match or check fails
        """
        try:
            command = f"show interface {interface}"
            output = self.device.send_command(command)
            
            # Parse interface status
            if expected_status.lower() == "up":
                if "up" in output.lower() and "line protocol is up" in output.lower():
                    logger.info(f"Interface {interface} is up on {self.device.host}")
                    return True
                else:
                    raise ValidationError(
                        f"Interface {interface} is not up on {self.device.host}"
                    )
            else:
                if "down" in output.lower():
                    logger.info(f"Interface {interface} is down on {self.device.host}")
                    return True
                else:
                    raise ValidationError(
                        f"Interface {interface} is not down on {self.device.host}"
                    )
                    
        except DeviceConnectionError as e:
            raise ValidationError(str(e))
    
    def verify_routing_protocol(self, protocol: str) -> bool:
        """
        Verify if a routing protocol is running.
        
        Args:
            protocol: Protocol name ('ospf', 'eigrp', 'bgp')
            
        Returns:
            True if protocol is running
            
        Raises:
            ValidationError: If protocol is not running or check fails
        """
        try:
            command_map = {
                "ospf": "show ip ospf",
                "eigrp": "show ip eigrp neighbors",
                "bgp": "show ip bgp summary",
            }
            
            command = command_map.get(protocol.lower())
            if not command:
                raise ValidationError(f"Unknown protocol: {protocol}")
            
            output = self.device.send_command(command)
            
            # Check if output indicates protocol is running
            if "not running" in output.lower() or "% " in output:
                raise ValidationError(
                    f"Protocol {protocol} is not running on {self.device.host}"
                )
            
            logger.info(f"Protocol {protocol} verified on {self.device.host}")
            return True
            
        except DeviceConnectionError as e:
            raise ValidationError(str(e))
    
    def verify_ip_connectivity(self, target_ip: str, count: int = 3) -> bool:
        """
        Verify IP connectivity using ping.
        
        Args:
            target_ip: Target IP address to ping
            count: Number of ping packets
            
        Returns:
            True if ping is successful
            
        Raises:
            ValidationError: If ping fails
        """
        try:
            command = f"ping {target_ip} repeat {count}"
            output = self.device.send_command(command, delay_factor=2)
            
            # Parse ping results
            success_pattern = r"Success rate is (\d+) percent"
            match = re.search(success_pattern, output)
            
            if match:
                success_rate = int(match.group(1))
                if success_rate >= 80:  # At least 80% success
                    logger.info(
                        f"Ping to {target_ip} successful ({success_rate}%) "
                        f"from {self.device.host}"
                    )
                    return True
                else:
                    raise ValidationError(
                        f"Ping to {target_ip} failed ({success_rate}%) "
                        f"from {self.device.host}"
                    )
            else:
                raise ValidationError(
                    f"Could not parse ping results for {target_ip} "
                    f"from {self.device.host}"
                )
                
        except DeviceConnectionError as e:
            raise ValidationError(str(e))
    
    def verify_config_contains(self, config_snippet: str) -> bool:
        """
        Verify that running config contains a specific snippet.
        
        Args:
            config_snippet: Configuration text to search for
            
        Returns:
            True if snippet is found in running config
            
        Raises:
            ValidationError: If snippet not found
        """
        try:
            output = self.device.send_command("show running-config")
            
            if config_snippet in output:
                logger.info(
                    f"Config snippet found in running config on {self.device.host}"
                )
                return True
            else:
                raise ValidationError(
                    f"Config snippet not found in running config on {self.device.host}"
                )
                
        except DeviceConnectionError as e:
            raise ValidationError(str(e))
    
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get basic device information.
        
        Returns:
            Dictionary with device information
        """
        try:
            version_output = self.device.send_command("show version")
            hostname_output = self.device.send_command("show running-config | include hostname")
            
            # Parse hostname
            hostname_match = re.search(r"hostname (\S+)", hostname_output)
            hostname = hostname_match.group(1) if hostname_match else "Unknown"
            
            # Parse version (simplified for Cisco)
            version_match = re.search(r"Version (\S+)", version_output)
            version = version_match.group(1) if version_match else "Unknown"
            
            # Parse uptime
            uptime_match = re.search(r"uptime is (.+)", version_output)
            uptime = uptime_match.group(1) if uptime_match else "Unknown"
            
            device_info: Dict[str, Any] = {
                "hostname": hostname,
                "version": version,
                "uptime": uptime,
                "device_type": self.device.device_type,
                "host": self.device.host,
            }
            
            logger.info(f"Retrieved device info for {self.device.host}")
            return device_info
            
        except Exception as e:
            logger.error(f"Error getting device info for {self.device.host}: {str(e)}")
            return {}
    
    def run_validation_suite(
        self,
        validations: List[Dict[str, Any]],
    ) -> Dict[str, bool]:
        """
        Run a suite of validation checks.
        
        Args:
            validations: List of validation dictionaries with 'type' and parameters
            
        Returns:
            Dictionary with validation results
            
        Example:
            validations = [
                {"type": "connectivity"},
                {"type": "interface", "interface": "Gi0/1", "status": "up"},
                {"type": "protocol", "protocol": "ospf"},
            ]
        """
        results: Dict[str, bool] = {}

        for idx, validation in enumerate(validations):
            val_type = validation.get("type")

            try:
                if val_type == "connectivity":
                    result: bool = self.verify_connectivity()
                elif val_type == "interface":
                    result = self.verify_interface_status(
                        validation["interface"],
                        validation.get("status", "up"),
                    )
                elif val_type == "protocol":
                    result = self.verify_routing_protocol(validation["protocol"])
                elif val_type == "ping":
                    result = self.verify_ip_connectivity(
                        validation["target"],
                        validation.get("count", 3),
                    )
                elif val_type == "config":
                    result = self.verify_config_contains(validation["snippet"])
                else:
                    logger.warning(f"Unknown validation type: {val_type}")
                    result = False

                results[f"validation_{idx}_{val_type}"] = result

            except ValidationError as e:
                logger.error(f"Validation failed: {str(e)}")
                results[f"validation_{idx}_{val_type}"] = False

        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        logger.info(
            f"Validation suite completed: {success_count}/{total_count} passed "
            f"for {self.device.host}"
        )

        return results
