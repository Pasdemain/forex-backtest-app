"""
MetaTrader 5 Connector Module

This module handles all interactions with the MetaTrader 5 terminal,
including connection, initialization, and data retrieval.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
import pytz
import traceback

# Import MetaTrader5 with error handling
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from src.utils.config import get_config
from src.data.database import insert_candle_data, init_db

logger = logging.getLogger(__name__)

def check_mt5_installed():
    """
    Check if MetaTrader 5 is installed and available.
    
    Returns:
        bool: True if MetaTrader 5 is available, False otherwise
    """
    if mt5 is None:
        logger.error("MetaTrader5 module not found. Please install it using: pip install MetaTrader5")
        return False
    return True

def initialize_mt5():
    """
    Initialize connection to MetaTrader 5 terminal.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    if not check_mt5_installed():
        return False
    
    try:
        if not mt5.initialize():
            logger.error(f"MetaTrader5 initialization failed: {mt5.last_error()}")
            return False
        
        logger.info("MetaTrader5 initialized successfully")
        logger.info(f"MetaTrader5 terminal info: {mt5.terminal_info()}")
        logger.info(f"MetaTrader5 version: {mt5.version()}")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing MetaTrader5: {e}")
        logger.error(traceback.format_exc())
        return False

def shutdown_mt5():
    """
    Shut down connection to MetaTrader 5 terminal.
    """
    if mt5 is not None:
        mt5.shutdown()
        logger.info("MetaTrader5 connection closed")

def get_mt5_timeframe(timeframe_str):
    """
    Convert a timeframe string to a MetaTrader 5 timeframe constant.
    
    Args:
        timeframe_str (str): The timeframe string (e.g., 'M15')
        
    Returns:
        int: The MetaTrader 5 timeframe constant
    """
    timeframe_map = {
        'M1': mt5.TIMEFRAME_M1,
        'M5': mt5.TIMEFRAME_M5,
        'M15': mt5.TIMEFRAME_M15,
        'M30': mt5.TIMEFRAME_M30,
        'H1': mt5.TIMEFRAME_H1,
        'H4': mt5.TIMEFRAME_H4,
        'D1': mt5.TIMEFRAME_D1,
        'W1': mt5.TIMEFRAME_W1,
        'MN1': mt5.TIMEFRAME_MN1
    }
    
    if timeframe_str not in timeframe_map:
        logger.error(f"Invalid timeframe: {timeframe_str}")
        logger.error(f"Valid timeframes: {list(timeframe_map.keys())}")
        return None
    
    return timeframe_map[timeframe_str]

def fetch_historical_data(symbol, timeframe_str, from_date, to_date=None):
    """
    Fetch historical data from MetaTrader 5.
    
    Args:
        symbol (str): The trading symbol
        timeframe_str (str): The timeframe string (e.g., 'M15')
        from_date (datetime): The start date
        to_date (datetime, optional): The end date. If None, current time is used.
        
    Returns:
        DataFrame or None: A pandas DataFrame with the historical data, or None if an error occurred
    """
    if not check_mt5_installed() or not initialize_mt5():
        return None
    
    try:
        # Convert timeframe string to MT5 constant
        timeframe = get_mt5_timeframe(timeframe_str)
        if timeframe is None:
            return None
        
        # Set timezone
        config = get_config()
        timezone = pytz.timezone(config['mt5']['timezone'])
        
        # Apply timezone to dates
        from_date = from_date.replace(tzinfo=timezone)
        if to_date is None:
            to_date = datetime.now(timezone)
        else:
            to_date = to_date.replace(tzinfo=timezone)
        
        logger.info(f"Fetching {timeframe_str} data for {symbol} from {from_date} to {to_date}")
        
        # Get the rates
        rates = mt5.copy_rates_range(symbol, timeframe, from_date, to_date)
        
        if rates is None or len(rates) == 0:
            logger.warning(f"No data returned for {symbol} on {timeframe_str} from {from_date} to {to_date}")
            logger.warning(f"MT5 error: {mt5.last_error()}")
            return None
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(rates)
        
        # Convert time column from Unix timestamp to datetime
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df['time'] = df['time'].dt.tz_convert(timezone)
        
        logger.info(f"Retrieved {len(df)} bars for {symbol} on {timeframe_str}")
        
        return df
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        logger.error(traceback.format_exc())
        return None
    finally:
        shutdown_mt5()

def fetch_and_store_data_for_symbol(symbol, db_path, timeframes=None, days_history=730):
    """
    Fetch historical data for a symbol and store it in the database.
    
    Args:
        symbol (str): The trading symbol
        db_path (str): Path to the database file
        timeframes (list, optional): List of timeframes to fetch. If None, all configured timeframes are used.
        days_history (int, optional): Number of days of history to fetch
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not check_mt5_installed() or not initialize_mt5():
        return False
    
    try:
        # Initialize the database
        init_db(db_path)
        
        # Get configuration
        config = get_config()
        
        # Use provided timeframes or get from config
        if timeframes is None:
            timeframes = config['mt5']['timeframes']
        
        # Set timezone
        timezone = pytz.timezone(config['mt5']['timezone'])
        current_time = datetime.now(timezone)
        
        # Fetch and store data for each timeframe
        for timeframe in timeframes:
            logger.info(f"Processing {timeframe} timeframe for {symbol}")
            
            if timeframe == 'M5':
                # For M5 timeframe, fetch data month by month to avoid memory issues
                start_date = current_time - timedelta(days=days_history)
                end_date = current_time
                
                while start_date < end_date:
                    # Calculate end of month
                    month_end = (start_date.replace(day=28) + timedelta(days=4))
                    month_end = month_end.replace(day=1) - timedelta(days=1)
                    month_end = month_end.replace(hour=23, minute=59, second=59)
                    
                    # Ensure we don't go past the end date
                    if month_end > end_date:
                        month_end = end_date
                    
                    # Fetch data for this month
                    rates = mt5.copy_rates_range(symbol, get_mt5_timeframe(timeframe), start_date, month_end)
                    
                    if rates is not None and len(rates) > 0:
                        df = pd.DataFrame(rates)
                        # Store in database
                        insert_candle_data(db_path, df, timeframe, symbol)
                        logger.info(f"Inserted {len(df)} {timeframe} candles for {symbol} for month starting {start_date.strftime('%Y-%m-%d')}")
                    
                    # Move to next month
                    start_date = (month_end + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # For other timeframes, fetch all data at once
                from_date = current_time - timedelta(days=days_history)
                
                # Fetch the data
                df = fetch_historical_data(symbol, timeframe, from_date, current_time)
                
                if df is not None and not df.empty:
                    # Store in database
                    insert_candle_data(db_path, df, timeframe, symbol)
                    logger.info(f"Inserted {len(df)} {timeframe} candles for {symbol}")
        
        logger.info(f"Successfully fetched and stored data for {symbol}")
        return True
    except Exception as e:
        logger.error(f"Error fetching and storing data for {symbol}: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        shutdown_mt5()

def validate_symbol(symbol):
    """
    Validate that a symbol exists in MetaTrader 5.
    
    Args:
        symbol (str): The trading symbol to validate
        
    Returns:
        bool: True if the symbol exists, False otherwise
    """
    if not check_mt5_installed() or not initialize_mt5():
        return False
    
    try:
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        
        if symbol_info is None:
            logger.warning(f"Symbol {symbol} not found in MetaTrader 5")
            return False
        
        logger.info(f"Symbol {symbol} is valid")
        return True
    except Exception as e:
        logger.error(f"Error validating symbol {symbol}: {e}")
        return False
    finally:
        shutdown_mt5()

def get_available_symbols():
    """
    Get a list of all available symbols in MetaTrader 5.
    
    Returns:
        list: A list of available symbol names
    """
    if not check_mt5_installed() or not initialize_mt5():
        return []
    
    try:
        # Get all symbols
        symbols = mt5.symbols_get()
        
        # Extract symbol names
        symbol_names = [symbol.name for symbol in symbols]
        
        logger.info(f"Found {len(symbol_names)} symbols in MetaTrader 5")
        return symbol_names
    except Exception as e:
        logger.error(f"Error getting available symbols: {e}")
        return []
    finally:
        shutdown_mt5()

def get_account_info():
    """
    Get account information from MetaTrader 5.
    
    Returns:
        dict: Account information, or None if an error occurred
    """
    if not check_mt5_installed() or not initialize_mt5():
        return None
    
    try:
        # Get account info
        account_info = mt5.account_info()
        
        if account_info is None:
            logger.warning("Failed to get account information")
            return None
        
        # Convert to dictionary
        account_info_dict = {
            'login': account_info.login,
            'server': account_info.server,
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'margin_free': account_info.margin_free,
            'currency': account_info.currency,
        }
        
        logger.info(f"Account information retrieved: {account_info_dict}")
        return account_info_dict
    except Exception as e:
        logger.error(f"Error getting account information: {e}")
        return None
    finally:
        shutdown_mt5()
