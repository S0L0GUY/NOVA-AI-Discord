"""Centralized logging configuration for NOVA Discord Bot.

This module provides structured logging with different log levels (DEBUG, INFO, WARNING, ERROR),
file and console handlers, and automatic log rotation to prevent disk space issues.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(name: str = "nova_bot", log_level: str = "INFO") -> logging.Logger:
    """Set up and return a configured logger with file and console handlers.

    Args:
        name: Logger name (default: "nova_bot")
        log_level: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Convert log level string to logging level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Define log file paths
    log_file = os.path.join(logs_dir, "nova_bot.log")
    error_log_file = os.path.join(logs_dir, "nova_bot_errors.log")

    # Create formatter with timestamp, logger name, level, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (INFO level minimum to avoid spam)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation (10 MB max per file, keep 5 backups)
    # This prevents disk space issues by rotating logs automatically
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,  # Keep 5 backup files
    )
    file_handler.setLevel(logging.DEBUG)  # File captures all levels
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Error handler - logs only WARNING and ERROR level messages
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # Log initial setup message
    logger.info(f"Logger initialized - Level: {log_level}")
    logger.debug(f"Log files: {log_file} and {error_log_file}")

    return logger


# Get log level from environment variable or default to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Initialize the main logger for the application
logger = setup_logger("nova_bot", LOG_LEVEL)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(name)
