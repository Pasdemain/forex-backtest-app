#!/usr/bin/env python3
"""
Forex Backtest Application Main Entry Point

This script launches the main application GUI, which provides access to all features
of the forex backtesting application.
"""

import os
import sys
import logging
from datetime import datetime
import tkinter as tk

# Set up proper path for importing modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import application modules
from src.gui.main_window import MainApplication
from src.utils.config import setup_config, get_config
from src.utils.logger import setup_logging

def main():
    """Main entry point for the Forex Backtest Application."""
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Set up logging
    log_filename = f"logs/app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    setup_logging(log_filename)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Forex Backtest Application")
    
    # Set up configuration
    setup_config()
    config = get_config()
    logger.debug(f"Configuration loaded: {config}")
    
    # Create and run the GUI application
    root = tk.Tk()
    app = MainApplication(root)
    logger.info("GUI initialized")
    
    # Start the main event loop
    root.mainloop()
    
    logger.info("Application closed")

if __name__ == "__main__":
    main()
