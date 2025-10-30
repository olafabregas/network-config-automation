"""
Connect - Handles SSH connections to network devices.
Uses Netmiko for Cisco-like devices with robust error handling.
"""

from typing import Optional, Any, List
from netmiko import ConnectHandler  # type: ignore[reportMissingTypeStubs]
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException  # type: ignore[reportMissingTypeStubs]
from paramiko.ssh_exception import SSHException
from .logger import setup_logger
from .secrets_manager import SecretsManager


logger = setup_logger("netauto.connect")


class DeviceConnectionError(Exception):
    """Custom exception for device connection errors."""
    pass


class NetworkDevice:
    """Represents a network device connection using Netmiko."""
    
    def __init__(
        self,
        host: str,
        device_type: str = "cisco_ios",
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: int = 30,
        session_timeout: int = 60,
    ):
        """
        Initialize a network device connection.
        
        Args:
            host: Device IP address or hostname
            device_type: Netmiko device type (e.g., 'cisco_ios', 'arista_eos')
            port: SSH port number
            username: SSH username (from env if not provided)
            password: SSH password (from env if not provided)
            secret: Enable secret (from env if not provided)
            timeout: Connection timeout in seconds
            session_timeout: Session timeout in seconds
        """
        self.host = host
        self.device_type = device_type
        self.port = port
        self.timeout = timeout
        self.session_timeout = session_timeout
        self.connection: Optional[Any] = None
        
        # Get credentials from environment if not provided
        if not username or not password:
            secrets = SecretsManager.get_device_credentials()
            self.username = username or secrets["username"]
            self.password = password or secrets["password"]
            self.secret = secret or secrets.get("secret")
        else:
            self.username = username
            self.password = password
            self.secret = secret
        
        logger.info(f"Initialized connection parameters for {self.host}")
    
    def connect(self) -> bool:
        """
        Establish SSH connection to the device.
        
        Returns:
            True if connection successful
            
        Raises:
            DeviceConnectionError: If connection fails
        """
        device_params: dict[str, Any] = {
            "device_type": self.device_type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "timeout": self.timeout,
            "session_timeout": self.session_timeout,
        }
        
        if self.secret:
            device_params["secret"] = self.secret
        
        try:
            logger.info(f"Connecting to {self.host}...")
            self.connection = ConnectHandler(**device_params)
            
            # Enter enable mode if secret is provided
            if self.secret and not self.connection.check_enable_mode():
                self.connection.enable()
            
            logger.info(f"Successfully connected to {self.host}")
            return True
            
        except NetmikoTimeoutException as e:
            error_msg = f"Connection timeout to {self.host}: {str(e)}"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg)
            
        except NetmikoAuthenticationException as e:
            error_msg = f"Authentication failed for {self.host}: {str(e)}"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg)
            
        except SSHException as e:
            error_msg = f"SSH error connecting to {self.host}: {str(e)}"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error connecting to {self.host}: {str(e)}"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg)
    
    def disconnect(self) -> None:
        """Disconnect from the device."""
        if self.connection:
            try:
                self.connection.disconnect()
                logger.info(f"Disconnected from {self.host}")
            except Exception as e:
                logger.warning(f"Error during disconnect from {self.host}: {str(e)}")
            finally:
                self.connection = None
    
    def send_command(
        self,
        command: str,
        expect_string: Optional[str] = None,
        delay_factor: int = 1,
    ) -> str:
        """
        Send a command to the device and return output.
        
        Args:
            command: Command to send
            expect_string: Expected string in output (optional)
            delay_factor: Multiplier for command delay
            
        Returns:
            Command output as string
            
        Raises:
            DeviceConnectionError: If not connected or command fails
        """
        if not self.connection:
            raise DeviceConnectionError(f"Not connected to {self.host}")
        
        try:
            logger.debug(f"Sending command to {self.host}: {command}")
            output = self.connection.send_command(
                command,
                expect_string=expect_string,
                delay_factor=delay_factor,
            )
            logger.debug(f"Command executed successfully on {self.host}")
            return str(output)
            
        except Exception as e:
            error_msg = f"Error executing command on {self.host}: {str(e)}"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg)
    
    def send_config_set(
        self,
        config_commands: List[str],
        exit_config_mode: bool = True,
        delay_factor: int = 1,
    ) -> str:
        """
        Send configuration commands to the device.
        
        Args:
            config_commands: List of configuration commands
            exit_config_mode: Exit config mode after sending commands
            delay_factor: Multiplier for command delay
            
        Returns:
            Configuration output as string
            
        Raises:
            DeviceConnectionError: If not connected or configuration fails
        """
        if not self.connection:
            raise DeviceConnectionError(f"Not connected to {self.host}")
        
        try:
            logger.info(f"Sending {len(config_commands)} config commands to {self.host}")
            output = self.connection.send_config_set(
                config_commands,
                exit_config_mode=exit_config_mode,
                delay_factor=delay_factor,
            )
            logger.info(f"Configuration applied successfully on {self.host}")
            return str(output)
            
        except Exception as e:
            error_msg = f"Error applying configuration on {self.host}: {str(e)}"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg)
    
    def send_config_from_file(
        self,
        config_file: str,
        exit_config_mode: bool = True,
    ) -> str:
        """
        Send configuration from a file.
        
        Args:
            config_file: Path to configuration file
            exit_config_mode: Exit config mode after sending commands
            
        Returns:
            Configuration output as string
            
        Raises:
            DeviceConnectionError: If not connected or configuration fails
        """
        if not self.connection:
            raise DeviceConnectionError(f"Not connected to {self.host}")
        
        try:
            logger.info(f"Sending config from file to {self.host}: {config_file}")
            output = self.connection.send_config_from_file(
                config_file,
                exit_config_mode=exit_config_mode,
            )
            logger.info(f"Configuration from file applied successfully on {self.host}")
            return str(output)
            
        except Exception as e:
            error_msg = f"Error applying config from file on {self.host}: {str(e)}"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg)
    
    def save_config(self) -> str:
        """
        Save the running configuration.
        
        Returns:
            Command output as string
        """
        if not self.connection:
            raise DeviceConnectionError(f"Not connected to {self.host}")

        logger.info(f"Saving configuration on {self.host}")
        result = self.connection.save_config()
        return str(result)
    
    def is_alive(self) -> bool:
        """
        Check if the connection is still alive.
        
        Returns:
            True if connection is alive, False otherwise
        """
        if not self.connection:
            return False
        return self.connection.is_alive()
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()
    
    def __repr__(self) -> str:
        """String representation of the device."""
        return f"NetworkDevice(host='{self.host}', device_type='{self.device_type}')"
