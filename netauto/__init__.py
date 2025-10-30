"""
Network Configuration Automation Package
A professional-grade automation system for network device management.
"""

__version__ = "1.0.0"
__author__ = "Network Automation Team"

from .connect import NetworkDevice, DeviceConnectionError
from .tasks import ConfigurationTask
from .validators import ConfigValidator
from .logger import setup_logger

__all__ = [
    "NetworkDevice",
    "DeviceConnectionError",
    "ConfigurationTask",
    "ConfigValidator",
    "setup_logger",
]
