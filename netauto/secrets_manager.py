"""
Secrets Manager - Handles credentials and sensitive data securely.
Uses environment variables and supports .env files via python-dotenv.
"""

import os
from typing import Optional, Dict
from pathlib import Path
from dotenv import load_dotenv


class SecretsManager:
    """Manages secure credential retrieval from environment variables."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize the secrets manager.
        
        Args:
            env_file: Path to .env file. If None, uses default .env in project root.
        """
        if env_file:
            env_path = Path(env_file)
        else:
            env_path = Path(__file__).parent.parent / ".env"
        
        if env_path.exists():
            load_dotenv(env_path)
    
    @staticmethod
    def get_credential(key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a credential from environment variables.
        
        Args:
            key: The environment variable name
            default: Default value if not found
            
        Returns:
            The credential value or default
        """
        return os.getenv(key, default)
    
    @staticmethod
    def get_device_credentials() -> Dict[str, str]:
        """
        Get common device credentials from environment.
        
        Returns:
            Dictionary with username and password
            
        Raises:
            ValueError: If required credentials are missing
        """
        username = os.getenv("DEVICE_USERNAME")
        password = os.getenv("DEVICE_PASSWORD")
        enable_secret = os.getenv("DEVICE_ENABLE_SECRET")
        
        if not username or not password:
            raise ValueError(
                "Missing required credentials. "
                "Please set DEVICE_USERNAME and DEVICE_PASSWORD environment variables."
            )
        
        credentials = {
            "username": username,
            "password": password,
        }
        
        if enable_secret:
            credentials["secret"] = enable_secret
        
        return credentials
    
    @staticmethod
    def validate_credentials() -> bool:
        """
        Validate that required credentials are available.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            SecretsManager.get_device_credentials()
            return True
        except ValueError:
            return False
