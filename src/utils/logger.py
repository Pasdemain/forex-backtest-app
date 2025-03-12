"""
Logging Utility Module

This module sets up and configures the application logging system to provide
detailed information about application events and errors.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logging(log_file=None, level=logging.INFO):
    """
    Set up the logging configuration for the application.
    
    Args:
        log_file (str): Path to the log file. If None, logs are only sent to console.
        level (int): The logging level (e.g., logging.DEBUG, logging.INFO)
    """
    # Create the logs directory if it doesn't exist
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    # Create a formatter for detailed output
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
    )
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers (in case function is called multiple times)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # Add a file handler if a log file is specified
    if log_file:
        # Use RotatingFileHandler to limit file size
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)
    
    # Suppress excessive logging from third-party libraries
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    # Log the start of the logging system
    logging.getLogger(__name__).info(f"Logging initialized (level={level})")
    if log_file:
        logging.getLogger(__name__).info(f"Logging to file: {log_file}")

def get_logger(name):
    """
    Get a logger with the specified name.
    
    Args:
        name (str): The name for the logger
        
    Returns:
        Logger: A configured logger
    """
    return logging.getLogger(name)
