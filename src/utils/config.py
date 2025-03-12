"""
Configuration Management Module

This module handles the application configuration,
including default settings and user preferences.
"""

import os
import json
import logging

# Default configuration
DEFAULT_CONFIG = {
    "database": {
        "path": "./data",
    },
    "mt5": {
        "timeframes": ["M5", "M15", "H1", "H4", "D1"],
        "symbols": ["GBPUSD", "GBPJPY", "XAUUSD", "EURUSD", "AUDUSD", 
                    "EURGBP", "EURAUD", "EURJPY", "USDJPY"],
        "history_days": 730,  # 2 years
        "timezone": "Etc/GMT-5"
    },
    "trading": {
        "stoploss_sizes": [20, 25, 30],
        "trade_ratios": [2, 3, 4, 5],
        "currency_ratios": {
            "GBPJPY": 0.01,
            "GBPUSD": 0.0001,
            "EURUSD": 0.0001,
            "AUDUSD": 0.0001,
            "XAUUSD": 0.1,
            "EURGBP": 0.0001,
            "EURAUD": 0.0001,
            "EURJPY": 0.01,
            "USDJPY": 0.01
        },
        "pips_multiplication": {
            "GBPJPY": 100,
            "GBPUSD": 10000,
            "EURUSD": 10000,
            "AUDUSD": 10000,
            "XAUUSD": 10,
            "EURGBP": 10000,
            "EURAUD": 10000,
            "EURJPY": 100,
            "USDJPY": 100
        }
    },
    "gui": {
        "theme": "default",
        "accent_color": "#FF99CC",
        "font": {
            "family": "Arial",
            "size": 10
        },
        "window_position": {
            "x": 100,
            "y": 100
        }
    },
    "news": {
        "excel_path": "",
        "hours_before": 6,
        "hours_after": 200
    }
}

# Global variable to hold the configuration
_CONFIG = None

def setup_config():
    """
    Set up the configuration by loading user settings or creating defaults.
    """
    global _CONFIG
    logger = logging.getLogger(__name__)
    
    # Create config directory if it doesn't exist
    os.makedirs('config', exist_ok=True)
    config_path = 'config/settings.json'
    
    # Load existing config or create default
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                
            # Merge with default config to ensure all keys exist
            _CONFIG = DEFAULT_CONFIG.copy()
            _update_dict_recursive(_CONFIG, user_config)
            logger.info("Configuration loaded from settings.json")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            _CONFIG = DEFAULT_CONFIG.copy()
            logger.info("Using default configuration")
    else:
        _CONFIG = DEFAULT_CONFIG.copy()
        
        # Save default config
        try:
            with open(config_path, 'w') as f:
                json.dump(_CONFIG, f, indent=2)
            logger.info("Default configuration saved to settings.json")
        except Exception as e:
            logger.error(f"Error saving default configuration: {e}")
    
    # Create data directory if it doesn't exist
    os.makedirs(_CONFIG['database']['path'], exist_ok=True)

def get_config():
    """
    Get the current configuration.
    
    Returns:
        dict: The current configuration dictionary
    """
    if _CONFIG is None:
        setup_config()
    return _CONFIG

def save_config(config):
    """
    Save the current configuration to the settings file.
    
    Args:
        config (dict): The configuration to save
    """
    logger = logging.getLogger(__name__)
    config_path = 'config/settings.json'
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved to settings.json")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")

def _update_dict_recursive(base_dict, update_dict):
    """
    Update a dictionary recursively.
    
    Args:
        base_dict (dict): The base dictionary to update
        update_dict (dict): The dictionary with new values
    """
    for key, value in update_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            _update_dict_recursive(base_dict[key], value)
        else:
            base_dict[key] = value
