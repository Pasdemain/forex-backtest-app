"""
Time Utility Functions

This module provides utility functions for working with time,
which is crucial for accurate backtesting and data analysis.
"""

import logging
from datetime import datetime, timedelta
import pytz
from src.utils.config import get_config

logger = logging.getLogger(__name__)

def get_mt5_timezone():
    """
    Get the timezone configured for MetaTrader 5 data.
    
    Returns:
        pytz.timezone: The configured timezone
    """
    config = get_config()
    timezone_str = config['mt5']['timezone']
    return pytz.timezone(timezone_str)

def normalize_time_for_m15(time_obj):
    """
    Normalize a datetime object to the nearest previous M15 candle time.
    
    Args:
        time_obj (datetime): The datetime object to normalize
        
    Returns:
        datetime: The normalized datetime object
    """
    # Adjust to the previous 15-minute mark
    minutes = time_obj.minute
    adjusted_minutes = (minutes // 15) * 15
    
    return time_obj.replace(
        minute=adjusted_minutes,
        second=0,
        microsecond=0
    )

def format_datetime_for_db(dt):
    """
    Format a datetime object for database storage.
    
    Args:
        dt (datetime): The datetime object to format
        
    Returns:
        str: The formatted datetime string
    """
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def parse_db_datetime(datetime_str):
    """
    Parse a datetime string from the database.
    
    Args:
        datetime_str (str): The datetime string to parse
        
    Returns:
        datetime: The parsed datetime object
    """
    return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

def format_display_date(dt):
    """
    Format a datetime object for display in the GUI.
    
    Args:
        dt (datetime): The datetime object to format
        
    Returns:
        str: The formatted date string
    """
    return dt.strftime('%d/%m/%y')

def format_display_time(dt):
    """
    Format a datetime object's time for display in the GUI.
    
    Args:
        dt (datetime): The datetime object to format
        
    Returns:
        str: The formatted time string
    """
    return dt.strftime('%H:%M')

def get_session_for_time(time_obj):
    """
    Determine the trading session for a given time.
    
    Args:
        time_obj (datetime or time): The time to check
        
    Returns:
        str: The session name ('London', 'New York', 'Tokyo', or 'Unknown')
    """
    # Extract the time component if a datetime is provided
    if isinstance(time_obj, datetime):
        time_only = time_obj.time()
    else:
        time_only = time_obj
    
    # Define session times
    london_start = datetime.strptime('15:00', '%H:%M').time()
    london_end = datetime.strptime('20:00', '%H:%M').time()
    new_york_start = datetime.strptime('20:00', '%H:%M').time()
    new_york_end = datetime.strptime('05:00', '%H:%M').time()
    tokyo_start = datetime.strptime('05:00', '%H:%M').time()
    tokyo_end = datetime.strptime('15:00', '%H:%M').time()
    
    # Determine the session
    if london_start <= time_only < london_end:
        return "London"
    elif tokyo_start <= time_only < tokyo_end:
        return "Tokyo"
    elif new_york_start <= time_only or time_only < new_york_end:
        return "New York"
    else:
        return "Unknown"

def combine_date_and_time(date_str, time_str):
    """
    Combine a date string and time string into a datetime object.
    
    Args:
        date_str (str): The date string in format 'dd/mm/yy'
        time_str (str): The time string in format 'HH:MM'
        
    Returns:
        datetime: The combined datetime object
    """
    try:
        return datetime.strptime(f"{date_str} {time_str}", '%d/%m/%y %H:%M')
    except ValueError as e:
        logger.error(f"Error combining date and time: {e}")
        logger.error(f"Date: '{date_str}', Time: '{time_str}'")
        return None
