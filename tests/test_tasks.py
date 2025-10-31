"""
Unit tests for the tasks module.
Tests configuration task orchestration and automation.
"""

import pytest  # type: ignore[reportMissingImports]
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from netauto.tasks import ConfigurationTask
from netauto.connect import DeviceConnectionError


@pytest.fixture
def mock_devices() -> List[Dict[str, Any]]:
    """Fixture providing mock device list."""
    return [
        {
            "host": "192.168.1.1",
            "device_type": "cisco_ios",
            "username": "admin",
            "password": "password123",
        },
        {
            "host": "192.168.1.2",
            "device_type": "cisco_ios",
            "username": "admin",
            "password": "password123",
        },
    ]


@pytest.fixture
def config_task(mock_devices: List[Dict[str, Any]]) -> ConfigurationTask:
    """Fixture providing a ConfigurationTask instance."""
    return ConfigurationTask(devices=mock_devices)


class TestConfigurationTask:
    """Test cases for ConfigurationTask class."""
    
    def test_task_initialization(self, mock_devices: List[Dict[str, Any]]):
        """Test task initialization."""
        task = ConfigurationTask(devices=mock_devices, dry_run=True)
        
        assert len(task.devices) == 2
        assert task.dry_run is True
        assert task.results == {}
    
    @patch("netauto.tasks.NetworkDevice")
    def test_configure_single_device_success(
        self, mock_network_device: MagicMock, config_task: ConfigurationTask
    ):
        """Test successful single device configuration."""
        mock_device_instance = MagicMock()
        mock_device_instance.host = "192.168.1.1"
        mock_device_instance.send_config_set.return_value = "Config applied"
        mock_device_instance.save_config.return_value = "Config saved"
        mock_device_instance.is_alive.return_value = True
        mock_network_device.return_value = mock_device_instance
        
        device_info = {
            "host": "192.168.1.1",
            "device_type": "cisco_ios",
        }
        config_commands = ["interface GigabitEthernet0/1", "description Test"]
        
        result: Dict[str, Any] = config_task.configure_device(
            device_info=device_info,
            config_commands=config_commands,
            save_config=True,
            validate_after=False,
        )
        
        assert result["success"] is True
        assert result["host"] == "192.168.1.1"
        assert "successfully" in result["message"].lower()
        mock_device_instance.connect.assert_called_once()
        mock_device_instance.send_config_set.assert_called_once()
        mock_device_instance.save_config.assert_called_once()
        mock_device_instance.disconnect.assert_called_once()
    
    @patch("netauto.tasks.NetworkDevice")
    def test_configure_device_with_template(
        self, mock_network_device: MagicMock, config_task: ConfigurationTask
    ):
        """Test device configuration using template."""
        mock_device_instance = MagicMock()
        mock_device_instance.host = "192.168.1.1"
        mock_device_instance.send_config_set.return_value = "Config applied"
        mock_device_instance.save_config.return_value = "Config saved"
        mock_network_device.return_value = mock_device_instance
        
        device_info = {"host": "192.168.1.1"}
        template_vars = {"hostname": "ROUTER-01"}
        
        with patch.object(config_task.template_manager, "render_template") as mock_render:
            mock_render.return_value = "hostname ROUTER-01\n"
            
            result: Dict[str, Any] = config_task.configure_device(
                device_info=device_info,
                template_name="base_config.j2",
                template_vars=template_vars,
                save_config=False,
                validate_after=False,
            )
        
        assert result["success"] is True
        mock_render.assert_called_once_with("base_config.j2", template_vars)
    
    @patch("netauto.tasks.NetworkDevice")
    def test_configure_device_dry_run(self, mock_network_device: MagicMock):
        """Test dry run mode."""
        mock_device_instance = MagicMock()
        mock_network_device.return_value = mock_device_instance
        
        task = ConfigurationTask(devices=[{"host": "192.168.1.1"}], dry_run=True)
        
        result: Dict[str, Any] = task.configure_device(
            device_info={"host": "192.168.1.1"},
            config_commands=["hostname TEST"],
        )
        
        assert result["success"] is True
        assert "DRY RUN" in result["output"]
        mock_device_instance.send_config_set.assert_not_called()
    
    @patch("netauto.tasks.NetworkDevice")
    def test_configure_device_connection_error(
        self, mock_network_device: MagicMock, config_task: ConfigurationTask
    ):
        """Test handling of connection errors."""
        mock_device_instance = MagicMock()
        mock_device_instance.connect.side_effect = DeviceConnectionError("Connection failed")
        mock_network_device.return_value = mock_device_instance
        
        result: Dict[str, Any] = config_task.configure_device(
            device_info={"host": "192.168.1.1"},
            config_commands=["hostname TEST"],
        )
        
        assert result["success"] is False
        assert "connection error" in result["message"].lower()
    
    @patch("netauto.tasks.NetworkDevice")
    @patch("netauto.tasks.ConfigValidator")
    def test_configure_with_validation(
        self,
        mock_validator: MagicMock,
        mock_network_device: MagicMock,
        config_task: ConfigurationTask,
    ):
        """Test configuration with post-deployment validation."""
        mock_device_instance = MagicMock()
        mock_device_instance.send_config_set.return_value = "Config applied"
        mock_device_instance.is_alive.return_value = True
        mock_network_device.return_value = mock_device_instance
        
        mock_validator_instance = MagicMock()
        mock_validator_instance.verify_connectivity.return_value = True
        mock_validator_instance.get_device_info.return_value = {"hostname": "TEST"}
        mock_validator.return_value = mock_validator_instance
        
        result: Dict[str, Any] = config_task.configure_device(
            device_info={"host": "192.168.1.1"},
            config_commands=["hostname TEST"],
            save_config=False,
            validate_after=True,
        )
        
        assert result["success"] is True
        assert "validation" in result
        mock_validator_instance.verify_connectivity.assert_called_once()
    
    @patch("netauto.tasks.NetworkDevice")
    def test_configure_multiple_devices_sequential(
        self, mock_network_device: MagicMock, config_task: ConfigurationTask
    ):
        """Test sequential configuration of multiple devices."""
        mock_device_instance = MagicMock()
        mock_device_instance.send_config_set.return_value = "Config applied"
        mock_device_instance.save_config.return_value = "Saved"
        mock_network_device.return_value = mock_device_instance
        
        config_commands = ["hostname TEST"]
        
        summary: Dict[str, Any] = config_task.configure_multiple_devices(
            config_commands=config_commands,
            save_config=False,
            validate_after=False,
            parallel=False,
        )
        
        assert summary["total_devices"] == 2
        assert summary["successful"] == 2
        assert summary["failed"] == 0
        assert len(summary["results"]) == 2
    
    @patch("netauto.tasks.NetworkDevice")
    def test_configure_multiple_devices_parallel(
        self, mock_network_device: MagicMock, config_task: ConfigurationTask
    ):
        """Test parallel configuration of multiple devices."""
        mock_device_instance = MagicMock()
        mock_device_instance.send_config_set.return_value = "Config applied"
        mock_device_instance.save_config.return_value = "Saved"
        mock_network_device.return_value = mock_device_instance
        
        config_commands = ["hostname TEST"]
        
        summary: Dict[str, Any] = config_task.configure_multiple_devices(
            config_commands=config_commands,
            save_config=False,
            validate_after=False,
            parallel=True,
            max_workers=2,
        )
        
        assert summary["total_devices"] == 2
        assert summary["successful"] == 2
        assert len(summary["results"]) == 2
    
    @patch("netauto.tasks.NetworkDevice")
    def test_configure_multiple_with_template_vars(
        self, mock_network_device: MagicMock, config_task: ConfigurationTask
    ):
        """Test multiple device config with individual template variables."""
        mock_device_instance = MagicMock()
        mock_device_instance.send_config_set.return_value = "Config applied"
        mock_network_device.return_value = mock_device_instance
        
        template_vars_list = [
            {"hostname": "ROUTER-01"},
            {"hostname": "ROUTER-02"},
        ]
        
        with patch.object(config_task.template_manager, "render_template") as mock_render:
            mock_render.return_value = "hostname TEST\n"
            
            summary: Dict[str, Any] = config_task.configure_multiple_devices(
                template_name="base_config.j2",
                template_vars_list=template_vars_list,
                save_config=False,
                validate_after=False,
                parallel=False,
            )
        
        assert summary["successful"] == 2
        assert mock_render.call_count == 2
    
    @patch("netauto.tasks.NetworkDevice")
    @patch("netauto.tasks.Path")
    def test_backup_configs(
        self, mock_path: MagicMock, mock_network_device: MagicMock, config_task: ConfigurationTask
    ):
        """Test configuration backup from devices."""
        mock_device_instance = MagicMock()
        mock_device_instance.send_command.return_value = "Running config output"
        mock_network_device.return_value = mock_device_instance
        
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        
        with patch("builtins.open", create=True):
            summary: Dict[str, Any] = config_task.backup_configs(
                backup_dir="/tmp/backups",
                parallel=False,
            )
        
        assert summary["total_devices"] == 2
        assert summary["successful"] == 2
    
    @patch("netauto.tasks.NetworkDevice")
    def test_backup_configs_with_failure(
        self, mock_network_device: MagicMock, config_task: ConfigurationTask
    ):
        """Test backup with device failure."""
        mock_device_instance = MagicMock()
        mock_device_instance.connect.side_effect = [
            None,  # First device succeeds
            DeviceConnectionError("Connection failed"),  # Second fails
        ]
        mock_device_instance.send_command.return_value = "Config output"
        mock_network_device.return_value = mock_device_instance
        
        with patch("builtins.open", create=True):
            with patch("netauto.tasks.Path"):
                summary: Dict[str, Any] = config_task.backup_configs(
                    backup_dir="/tmp/backups",
                    parallel=False,
                )
        
        assert summary["total_devices"] == 2
        assert summary["failed"] >= 1
    
    @patch("netauto.tasks.NetworkDevice")
    def test_no_config_commands_error(
        self,
        mock_network_device: MagicMock,
        config_task: ConfigurationTask,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test error when no configuration provided."""
        # ensure required credentials are present for this test run
        monkeypatch.setenv("DEVICE_USERNAME", "testuser")
        monkeypatch.setenv("DEVICE_PASSWORD", "testpass")

        result: Dict[str, Any] = config_task.configure_device(
            device_info={"host": "192.168.1.1"},
        )
        
        assert result["success"] is False
        assert "no configuration" in result["message"].lower()


class TestConfigurationTaskEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_device_list(self):
        """Test task with empty device list."""
        task = ConfigurationTask(devices=[])
        
        assert task.devices == []
        assert len(task.devices) == 0
    
    @patch("netauto.tasks.NetworkDevice")
    def test_missing_device_host(self, mock_network_device: MagicMock):
        """Test handling of missing host parameter."""
        task = ConfigurationTask(devices=[{}])
        
        # Should handle gracefully without crashing
        result: Dict[str, Any] = task.configure_device(
            device_info={},
            config_commands=["hostname TEST"],
        )

        # May fail but shouldn't crash
        assert "host" in result
