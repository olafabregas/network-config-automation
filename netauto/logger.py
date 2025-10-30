"""
Logger - Centralized logging configuration with JSON support.
Provides structured logging for debugging and auditing.
"""

import logging
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Any


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        # Use getattr to safely access optional attributes added by callers
        device = getattr(record, "device", None)
        if device is not None:
            log_data["device"] = device

        command = getattr(record, "command", None)
        if command is not None:
            log_data["command"] = command
        
        return json.dumps(log_data)


def setup_logger(
    name: str = "netauto",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
) -> logging.Logger:
    """
    Set up and configure a logger instance.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, logs to console only.
        json_format: If True, use JSON format for logs
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    if json_format:
        console_formatter = JSONFormatter()
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        if json_format:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# Create default logger instance
default_logger = setup_logger()
