"""
Shared Filesystem Logging Configuration

This module configures logging to write to the shared filesystem so that
logs can be accessed from any server (CPU or GPU) regardless of where
Claude Code is running.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from .config import settings


def setup_shared_logging(
    logger_name: str = "backend", 
    log_level: str = None,
    console_output: bool = True
) -> logging.Logger:
    """
    Configure logging to write to shared filesystem and optionally console.
    
    Args:
        logger_name: Name for the logger (e.g., "backend", "gpu_processing")
        log_level: Log level (INFO, DEBUG, WARNING, ERROR). Defaults to settings.LOG_LEVEL
        console_output: Whether to also output to console (default: True)
    
    Returns:
        Configured logger instance
    """
    
    # Get shared filesystem path from environment
    shared_filesystem_path = settings.SHARED_FILESYSTEM_MOUNT_PATH
    if not shared_filesystem_path:
        raise ValueError("SHARED_FILESYSTEM_MOUNT_PATH environment variable is required but not set!")
    
    # Create logs directory on shared filesystem
    logs_dir = Path(shared_filesystem_path) / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Determine log file path
    log_file_path = logs_dir / f"{logger_name}.log"
    
    # Configure log level
    if log_level is None:
        log_level = settings.LOG_LEVEL
    
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level_value)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add file handler (shared filesystem)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(log_level_value)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level_value)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Log the configuration
    logger.info(f"Backend logging configured - writing to: {log_file_path}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Console output: {console_output}")
    
    return logger


def get_shared_logger(name: str = "backend") -> logging.Logger:
    """
    Get or create a shared filesystem logger.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance configured for shared filesystem
    """
    return setup_shared_logging(name)


def get_log_file_paths() -> dict:
    """
    Get paths to all log files on shared filesystem.
    
    Returns:
        Dictionary mapping service names to log file paths
    """
    shared_filesystem_path = settings.SHARED_FILESYSTEM_MOUNT_PATH
    if not shared_filesystem_path:
        return {}
    
    logs_dir = Path(shared_filesystem_path) / "logs"
    
    log_files = {}
    if logs_dir.exists():
        for log_file in logs_dir.glob("*.log"):
            service_name = log_file.stem  # filename without .log extension
            log_files[service_name] = str(log_file)
    
    return log_files


# Configure root logger for backend when module is imported
try:
    backend_logger = setup_shared_logging("backend")
    # Set as default logger for the entire backend
    logging.getLogger().handlers = backend_logger.handlers
    logging.getLogger().setLevel(backend_logger.level)
except Exception as e:
    # Fallback to console logging if shared filesystem is not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.getLogger(__name__).warning(f"Failed to setup shared logging, using console only: {e}")