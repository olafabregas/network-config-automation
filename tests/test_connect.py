"""
Unit tests for the connect module.
Tests SSH connection handling and device communication.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any
from netauto.connect import NetworkDevice, DeviceConnectionError


@pytest.fixture
def mock_device_params() -> Dict[str, Any]:
    """Fixture providing mock device connection parameters."""
    return {
        "host": "192.168.1.1",
        "device_type": "cisco_ios",
        "port": 22,
        "username": "admin",
        "password": "password123",
        "secret": "enable123",
    }


@pytest.fixture
def network_device(mock_device_params: Dict[str, Any]) -> NetworkDevice:
    """Fixture providing a NetworkDevice instance."""
    with patch("netauto.connect.SecretsManager.get_device_credentials") as mock_creds:
        mock_creds.return_value = {
            "username": "admin",
            "password": "password123",
            "secret": "enable123",
        }
        device = NetworkDevice(**mock_device_params)
        return device


class TestNetworkDevice:
    """Test cases for NetworkDevice class."""
    
    def test_device_initialization(self, mock_device_params: Dict[str, Any]):
        """Test device initialization with parameters."""
        with patch("netauto.connect.SecretsManager.get_device_credentials") as mock_creds:
            mock_creds.return_value = {
                "username": "admin",
                "password": "password123",
                "secret": "enable123",
            }
            
            device = NetworkDevice(**mock_device_params)
            
            assert device.host == mock_device_params["host"]
            assert device.device_type == mock_device_params["device_type"]
            assert device.port == mock_device_params["port"]
            assert device.username == mock_device_params["username"]
            assert device.password == mock_device_params["password"]
    
    @patch("netauto.connect.ConnectHandler")
    def test_successful_connection(self, mock_connect_handler: MagicMock, network_device: NetworkDevice):
        """Test successful device connection."""
        mock_connection = MagicMock()
        mock_connection.check_enable_mode.return_value = True
        mock_connect_handler.return_value = mock_connection
        
        result = network_device.connect()
        
        assert result is True
        assert network_device.connection is not None
        mock_connect_handler.assert_called_once()
    
    @patch("netauto.connect.ConnectHandler")
    def test_connection_timeout(self, mock_connect_handler: MagicMock, network_device: NetworkDevice):
        """Test connection timeout handling."""
        from netmiko.exceptions import NetmikoTimeoutException  # type: ignore[reportMissingTypeStubs]

        mock_connect_handler.side_effect = NetmikoTimeoutException("Timeout")
        
        with pytest.raises(DeviceConnectionError) as exc_info:
            network_device.connect()
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch("netauto.connect.ConnectHandler")
    def test_authentication_failure(self, mock_connect_handler: MagicMock, network_device: NetworkDevice):
        """Test authentication failure handling."""
        from netmiko.exceptions import NetmikoAuthenticationException  # type: ignore[reportMissingTypeStubs]
        
        mock_connect_handler.side_effect = NetmikoAuthenticationException("Auth failed")
        
        with pytest.raises(DeviceConnectionError) as exc_info:
            network_device.connect()
        
        assert "authentication" in str(exc_info.value).lower()
    
    def test_disconnect(self, network_device: NetworkDevice):
        """Test device disconnection."""
        mock_connection = MagicMock()
        network_device.connection = mock_connection
        
        network_device.disconnect()
        
        mock_connection.disconnect.assert_called_once()
        assert network_device.connection is None
    
    @patch("netauto.connect.ConnectHandler")
    def test_send_command(self, mock_connect_handler: MagicMock, network_device: NetworkDevice):
        """Test sending commands to device."""
        mock_connection = MagicMock()
        mock_connection.send_command.return_value = "Command output"
        mock_connect_handler.return_value = mock_connection
        
        network_device.connect()
        result = network_device.send_command("show version")
        
        assert result == "Command output"
        mock_connection.send_command.assert_called_once()
    
    def test_send_command_not_connected(self, network_device: NetworkDevice):
        """Test sending command when not connected."""
        with pytest.raises(DeviceConnectionError) as exc_info:
            network_device.send_command("show version")
        
        assert "not connected" in str(exc_info.value).lower()
    
    @patch("netauto.connect.ConnectHandler")
    def test_send_config_set(self, mock_connect_handler: MagicMock, network_device: NetworkDevice):
        """Test sending configuration commands."""
        mock_connection = MagicMock()
        mock_connection.send_config_set.return_value = "Config applied"
        mock_connect_handler.return_value = mock_connection
        
        network_device.connect()
        commands = ["interface GigabitEthernet0/1", "description Test Interface"]
        result = network_device.send_config_set(commands)
        
        assert result == "Config applied"
        mock_connection.send_config_set.assert_called_once_with(
            commands, exit_config_mode=True, delay_factor=1
        )
    
    @patch("netauto.connect.ConnectHandler")
    def test_context_manager(self, mock_connect_handler: MagicMock, network_device: NetworkDevice):
        """Test using device as context manager."""
        mock_connection = MagicMock()
        mock_connection.check_enable_mode.return_value = True
        mock_connect_handler.return_value = mock_connection
        
        with network_device as device:
            assert device.connection is not None
        
        mock_connection.disconnect.assert_called_once()
    
    @patch("netauto.connect.ConnectHandler")
    def test_is_alive(self, mock_connect_handler: MagicMock, network_device: NetworkDevice):
        """Test connection alive check."""
        mock_connection = MagicMock()
        mock_connection.is_alive.return_value = True
        mock_connect_handler.return_value = mock_connection
        
        network_device.connect()
        
        assert network_device.is_alive() is True
        mock_connection.is_alive.assert_called_once()
    
    def test_repr(self, network_device: NetworkDevice):
        """Test string representation of device."""
        repr_str = repr(network_device)
        
        assert "NetworkDevice" in repr_str
        assert network_device.host in repr_str
        assert network_device.device_type in repr_str


class TestDeviceConnectionError:
    """Test cases for DeviceConnectionError exception."""
    
    def test_exception_message(self):
        """Test exception can be raised with message."""
        with pytest.raises(DeviceConnectionError) as exc_info:
            raise DeviceConnectionError("Test error message")
        
        assert "Test error message" in str(exc_info.value)
