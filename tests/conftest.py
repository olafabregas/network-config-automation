"""
Pytest configuration file.
Provides shared fixtures and configuration for all tests.
"""

import pytest
import sys
from pathlib import Path

# Add the parent directory to the path so we can import netauto
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture providing path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def sample_config_commands():
    """Fixture providing sample configuration commands."""
    return [
        "hostname TEST-DEVICE",
        "interface GigabitEthernet0/1",
        "description Test Interface",
        "no shutdown",
    ]


@pytest.fixture
def sample_device_info():
    """Fixture providing sample device information."""
    return {
        "host": "192.168.1.1",
        "device_type": "cisco_ios",
        "port": 22,
        "username": "admin",
        "password": "password123",
        "secret": "enable123",
    }
