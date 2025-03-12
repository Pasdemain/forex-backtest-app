"""
Database Management Module

This module handles all interactions with the SQLite database, including
creation, querying, and maintenance.
"""

import os
import logging
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

from src.utils.config import get_config
from src.utils.time_utils import format_datetime_for_db, normalize_time_for_m15

logger = logging.getLogger(__name__)

def get_db_path(symbol):
    """
    Get the database path for a specific symbol.
    
    Args:
        symbol (str): The trading symbol
        
    Returns:
        str: The full path to the database file
    """
    config = get_config()
    db_dir = config['database']['path']
    return os.path.join(db_dir, f"trading_data_{symbol}.db")

def init_db(db_path):
    """
    Initialize the database with required tables.
    
    Args:
        db_path (str): Path to the database file
    """
    logger.info(f"Initializing database at {db_path}")
    
    config = get_config()
    timeframes = config['mt5']['timeframes']
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create tables for each timeframe
    for timeframe in timeframes:
        c.execute(f'''
        CREATE TABLE IF NOT EXISTS candle_{timeframe} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            time TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            spread INTEGER NOT NULL,
            UNIQUE(symbol, time)
        )
        ''')
    
    # Create News table
    c.execute('''
    CREATE TABLE IF NOT EXISTS News (
        id INTEGER PRIMARY KEY,
        time TEXT NOT NULL,
        impact TEXT NOT NULL,
        currency TEXT NOT NULL,
        news TEXT NOT NULL,
        actual TEXT,
        forecast TEXT,
        previous TEXT,
        close_before TEXT,
        high_after TEXT,
        low_after TEXT,
        Pips_Highest_Shadow TEXT,
        Pips_Lowest_Shadow TEXT
    )
    ''')
    
    # Create Trading Entries table
    c.execute('''
    CREATE TABLE IF NOT EXISTS trading_entries (
        id INTEGER PRIMARY KEY, 
        day TEXT, 
        OpenTime TEXT, 
        ImpactPosition TEXT, 
        NewsTypes TEXT, 
        session TEXT, 
        position TEXT, 
        H4 TEXT, 
        H1 TEXT, 
        M15 TEXT, 
        EntryPoint TEXT, 
        StoplossSize INTEGER, 
        TradeRatio TEXT, 
        Closeday TEXT, 
        CloseTime TEXT, 
        Result TEXT,
        StartDatetime TEXT, 
        EndDatetime TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def insert_candle_data(db_path, df, timeframe, symbol):
    """
    Insert candle data into the database.
    
    Args:
        db_path (str): Path to the database file
        df (DataFrame): Pandas DataFrame with the candle data
        timeframe (str): The timeframe for the data (e.g., 'M15')
        symbol (str): The trading symbol
    """
    logger.info(f"Inserting {len(df)} candles for {symbol} on {timeframe} timeframe")
    
    # Add symbol column if it doesn't exist
    if 'symbol' not in df.columns:
        df['symbol'] = symbol
    
    # Format time column if it's not a string
    if df['time'].dtype != 'object':
        if hasattr(df['time'], 'dt'):
            df['time'] = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # If it's not already a string and doesn't have dt accessor
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Rename volume column if needed
    if 'tick_volume' in df.columns:
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    elif 'real_volume' in df.columns:
        df.rename(columns={'real_volume': 'volume'}, inplace=True)
    
    # Keep only needed columns
    df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume', 'spread']].copy()
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Insert data using the OR IGNORE syntax to avoid duplicates
        insert_sql = f"""
        INSERT OR IGNORE INTO candle_{timeframe} 
        (symbol, time, open, high, low, close, volume, spread)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Convert DataFrame to list of tuples for faster insertion
        data_tuples = [tuple(x) for x in df.to_numpy()]
        
        # Insert data in chunks to avoid memory issues with large datasets
        chunk_size = 1000
        for i in range(0, len(data_tuples), chunk_size):
            chunk = data_tuples[i:i + chunk_size]
            conn.executemany(insert_sql, chunk)
            conn.commit()
            
        logger.info(f"Inserted {len(df)} rows into candle_{timeframe}")
        
    except Exception as e:
        logger.error(f"Error inserting candle data: {e}")
        raise
    finally:
        if conn:
            conn.close()

def insert_news_data(db_path, df):
    """
    Insert news data into the database.
    
    Args:
        db_path (str): Path to the database file
        df (DataFrame): Pandas DataFrame with the news data
    """
    logger.info(f"Inserting {len(df)} news events")
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Insert news data
        df.to_sql('News', conn, if_exists='append', index=False, method='multi')
        
        logger.info(f"Inserted {len(df)} news events")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error inserting news data: {e}")
        raise

def insert_trading_entry(db_path, entry_data):
    """
    Insert a trading entry into the database.
    
    Args:
        db_path (str): Path to the database file
        entry_data (dict): Dictionary with the trading entry data
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Inserting trading entry for {entry_data.get('day')} {entry_data.get('OpenTime')}")
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Check if there's an overlapping entry
        if 'StartDatetime' in entry_data and 'EndDatetime' in entry_data:
            c.execute('''
                SELECT * FROM trading_entries 
                WHERE StoplossSize = ? AND TradeRatio = ? 
                AND NOT (EndDatetime <= ? OR StartDatetime >= ?)
            ''', (
                entry_data.get('StoplossSize'), 
                entry_data.get('TradeRatio'),
                entry_data.get('StartDatetime'),
                entry_data.get('EndDatetime')
            ))
            
            existing_entry = c.fetchone()
            if existing_entry:
                logger.warning(f"Found existing overlapping entry: {existing_entry}")
                conn.close()
                return False, existing_entry
        
        # Build columns and placeholders for the SQL query
        columns = ', '.join(entry_data.keys())
        placeholders = ', '.join(['?' for _ in entry_data])
        
        # Insert data
        c.execute(f'''
            INSERT INTO trading_entries
            ({columns})
            VALUES ({placeholders})
        ''', list(entry_data.values()))
        
        conn.commit()
        conn.close()
        
        logger.info("Trading entry inserted successfully")
        return True, None
        
    except Exception as e:
        logger.error(f"Error inserting trading entry: {e}")
        if conn:
            conn.close()
        return False, str(e)

def get_candle_at_time(db_path, symbol, timeframe, time_str):
    """
    Get a candle at a specific time.
    
    Args:
        db_path (str): Path to the database file
        symbol (str): The trading symbol
        timeframe (str): The timeframe for the data (e.g., 'M15')
        time_str (str): The time string in format 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        dict: A dictionary with the candle data, or None if not found
    """
    logger.debug(f"Getting {timeframe} candle for {symbol} at {time_str}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        c = conn.cursor()
        
        # Query for the candle
        c.execute(f'''
            SELECT * FROM candle_{timeframe}
            WHERE symbol = ? AND time = ?
        ''', (symbol, time_str))
        
        row = c.fetchone()
        conn.close()
        
        if row:
            # Convert the row to a dictionary
            candle = dict(row)
            logger.debug(f"Found candle: {candle}")
            return candle
        else:
            logger.warning(f"No {timeframe} candle found for {symbol} at {time_str}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting candle data: {e}")
        if conn:
            conn.close()
        return None

def get_subsequent_candles(db_path, symbol, timeframe, start_time, limit=None):
    """
    Get candles after a specific time.
    
    Args:
        db_path (str): Path to the database file
        symbol (str): The trading symbol
        timeframe (str): The timeframe for the data (e.g., 'M15')
        start_time (str): The starting time string in format 'YYYY-MM-DD HH:MM:SS'
        limit (int, optional): Maximum number of candles to return
        
    Returns:
        list: A list of dictionaries with candle data
    """
    logger.debug(f"Getting subsequent {timeframe} candles for {symbol} after {start_time}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Build query based on whether a limit is provided
        query = f'''
            SELECT * FROM candle_{timeframe}
            WHERE symbol = ? AND time > ?
            ORDER BY time ASC
        '''
        
        params = [symbol, start_time]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        # Execute query
        c.execute(query, params)
        
        # Fetch all results and convert to dictionaries
        rows = c.fetchall()
        candles = [dict(row) for row in rows]
        
        conn.close()
        
        logger.debug(f"Found {len(candles)} subsequent candles")
        return candles
            
    except Exception as e:
        logger.error(f"Error getting subsequent candles: {e}")
        if conn:
            conn.close()
        return []

def get_candles_in_range(db_path, symbol, timeframe, start_time, end_time):
    """
    Get candles within a specific time range.
    
    Args:
        db_path (str): Path to the database file
        symbol (str): The trading symbol
        timeframe (str): The timeframe for the data (e.g., 'M15')
        start_time (str): The starting time string in format 'YYYY-MM-DD HH:MM:SS'
        end_time (str): The ending time string in format 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        list: A list of dictionaries with candle data
    """
    logger.debug(f"Getting {timeframe} candles for {symbol} between {start_time} and {end_time}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Query for candles in range
        c.execute(f'''
            SELECT * FROM candle_{timeframe}
            WHERE symbol = ? AND time >= ? AND time <= ?
            ORDER BY time ASC
        ''', (symbol, start_time, end_time))
        
        # Fetch all results and convert to dictionaries
        rows = c.fetchall()
        candles = [dict(row) for row in rows]
        
        conn.close()
        
        logger.debug(f"Found {len(candles)} candles in range")
        return candles
            
    except Exception as e:
        logger.error(f"Error getting candles in range: {e}")
        if conn:
            conn.close()
        return []

def get_news_around_time(db_path, time_obj, hours_before=6, hours_after=6):
    """
    Get news events around a specific time.
    
    Args:
        db_path (str): Path to the database file
        time_obj (datetime): The reference time
        hours_before (int): Hours to look back
        hours_after (int): Hours to look forward
        
    Returns:
        list: A list of dictionaries with news data
    """
    time_before = time_obj - timedelta(hours=hours_before)
    time_after = time_obj + timedelta(hours=hours_after)
    
    time_before_str = format_datetime_for_db(time_before)
    time_after_str = format_datetime_for_db(time_after)
    
    logger.debug(f"Getting news between {time_before_str} and {time_after_str}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Query for news in range
        c.execute('''
            SELECT * FROM News 
            WHERE time BETWEEN ? AND ?
            ORDER BY time ASC
        ''', (time_before_str, time_after_str))
        
        # Fetch all results and convert to dictionaries
        rows = c.fetchall()
        news_events = [dict(row) for row in rows]
        
        conn.close()
        
        logger.debug(f"Found {len(news_events)} news events")
        return news_events
            
    except Exception as e:
        logger.error(f"Error getting news events: {e}")
        if conn:
            conn.close()
        return []

def get_similar_news(db_path, news_name, before_time):
    """
    Get similar news events before a specific time.
    
    Args:
        db_path (str): Path to the database file
        news_name (str): The name of the news event
        before_time (datetime): Only include news before this time
        
    Returns:
        list: A list of dictionaries with news data
    """
    before_time_str = format_datetime_for_db(before_time)
    
    logger.debug(f"Getting similar news '{news_name}' before {before_time_str}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Query for similar news
        c.execute('''
            SELECT * FROM News
            WHERE news = ? AND time < ?
            ORDER BY time DESC
        ''', (news_name, before_time_str))
        
        # Fetch all results and convert to dictionaries
        rows = c.fetchall()
        news_events = [dict(row) for row in rows]
        
        conn.close()
        
        logger.debug(f"Found {len(news_events)} similar news events")
        return news_events
            
    except Exception as e:
        logger.error(f"Error getting similar news: {e}")
        if conn:
            conn.close()
        return []

def get_trading_statistics(db_path, filters=None):
    """
    Get trading statistics from the database.
    
    Args:
        db_path (str): Path to the database file
        filters (dict, optional): Filters to apply to the query
        
    Returns:
        dict: A dictionary with trading statistics
    """
    logger.info(f"Getting trading statistics with filters: {filters}")
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Base query
        query = "SELECT * FROM trading_entries"
        params = []
        
        # Add filters if provided
        if filters:
            conditions = []
            for key, value in filters.items():
                if value:
                    conditions.append(f"{key} = ?")
                    params.append(value)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        # Execute query
        c.execute(query, params)
        
        # Fetch all results
        rows = c.fetchall()
        
        # Process results
        column_names = [description[0] for description in c.description]
        entries = []
        for row in rows:
            entry = dict(zip(column_names, row))
            entries.append(entry)
        
        conn.close()
        
        # Calculate statistics
        total_entries = len(entries)
        winning_entries = sum(1 for entry in entries if entry['Result'] == 'Winning')
        win_rate = (winning_entries / total_entries) * 100 if total_entries > 0 else 0
        
        # Group by parameters
        by_session = {}
        by_position = {}
        by_h4 = {}
        by_h1 = {}
        by_m15 = {}
        by_entry_point = {}
        by_stoploss_size = {}
        by_trade_ratio = {}
        
        for entry in entries:
            # Session
            session = entry['session']
            by_session[session] = by_session.get(session, []) + [entry]
            
            # Position
            position = entry['position']
            by_position[position] = by_position.get(position, []) + [entry]
            
            # H4
            h4 = entry['H4']
            by_h4[h4] = by_h4.get(h4, []) + [entry]
            
            # H1
            h1 = entry['H1']
            by_h1[h1] = by_h1.get(h1, []) + [entry]
            
            # M15
            m15 = entry['M15']
            by_m15[m15] = by_m15.get(m15, []) + [entry]
            
            # Entry Point
            entry_point = entry['EntryPoint']
            by_entry_point[entry_point] = by_entry_point.get(entry_point, []) + [entry]
            
            # Stoploss Size
            stoploss_size = entry['StoplossSize']
            by_stoploss_size[stoploss_size] = by_stoploss_size.get(stoploss_size, []) + [entry]
            
            # Trade Ratio
            trade_ratio = entry['TradeRatio']
            by_trade_ratio[trade_ratio] = by_trade_ratio.get(trade_ratio, []) + [entry]
        
        # Calculate win rates for each group
        stats = {
            'total_entries': total_entries,
            'winning_entries': winning_entries,
            'win_rate': win_rate,
            'by_session': {k: {'count': len(v), 'win_rate': sum(1 for e in v if e['Result'] == 'Winning') / len(v) * 100} for k, v in by_session.items()},
            'by_position': {k: {'count': len(v), 'win_rate': sum(1 for e in v if e['Result'] == 'Winning') / len(v) * 100} for k, v in by_position.items()},
            'by_h4': {k: {'count': len(v), 'win_rate': sum(1 for e in v if e['Result'] == 'Winning') / len(v) * 100} for k, v in by_h4.items()},
            'by_h1': {k: {'count': len(v), 'win_rate': sum(1 for e in v if e['Result'] == 'Winning') / len(v) * 100} for k, v in by_h1.items()},
            'by_m15': {k: {'count': len(v), 'win_rate': sum(1 for e in v if e['Result'] == 'Winning') / len(v) * 100} for k, v in by_m15.items()},
            'by_entry_point': {k: {'count': len(v), 'win_rate': sum(1 for e in v if e['Result'] == 'Winning') / len(v) * 100} for k, v in by_entry_point.items()},
            'by_stoploss_size': {k: {'count': len(v), 'win_rate': sum(1 for e in v if e['Result'] == 'Winning') / len(v) * 100} for k, v in by_stoploss_size.items()},
            'by_trade_ratio': {k: {'count': len(v), 'win_rate': sum(1 for e in v if e['Result'] == 'Winning') / len(v) * 100} for k, v in by_trade_ratio.items()},
        }
        
        logger.info("Successfully calculated trading statistics")
        return stats
            
    except Exception as e:
        logger.error(f"Error getting trading statistics: {e}")
        if conn:
            conn.close()
        return {
            'total_entries': 0,
            'winning_entries': 0,
            'win_rate': 0,
            'error': str(e)
        }

def calculate_pips_movement(db_path, news_events):
    """
    Calculate price movement after news events.
    
    This adds the Pips_Highest_Shadow and Pips_Lowest_Shadow fields
    to the news events data in the database.
    
    Args:
        db_path (str): Path to the database file
        news_events (list): List of news events
    """
    logger.info("Calculating price movement after news events")
    
    # Get the symbol from the database path
    base_name = os.path.basename(db_path)
    symbol = base_name.replace('trading_data_', '').replace('.db', '')
    
    # Get pip multiplication factor from config
    config = get_config()
    pip_multipliers = config['trading']['pips_multiplication']
    ratio_pips = pip_multipliers.get(symbol, 10000)
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Process each news event
        for event in news_events:
            news_time = datetime.strptime(event['time'], '%Y-%m-%d %H:%M:%S')
            
            # Get the candle before the news
            candle_before_query = f"""
                SELECT * FROM candle_M15 
                WHERE time < '{event['time']}' 
                ORDER BY time DESC LIMIT 1
            """
            df_candle_before = pd.read_sql_query(candle_before_query, conn)
            
            if not df_candle_before.empty:
                close_before = df_candle_before.iloc[0]['close']
                
                # Get the candles after the news (for the next hour)
                candle_after_end_time = news_time + timedelta(minutes=60)
                candles_after_query = f"""
                    SELECT MAX(high) AS max_high, MIN(low) AS min_low 
                    FROM candle_M15 
                    WHERE time > '{event['time']}' 
                    AND time <= '{candle_after_end_time.strftime('%Y-%m-%d %H:%M:%S')}'
                """
                df_candles_after = pd.read_sql_query(candles_after_query, conn)
                
                if not df_candles_after.empty:
                    max_high = df_candles_after.iloc[0]['max_high']
                    min_low = df_candles_after.iloc[0]['min_low']
                    
                    # Update the news event with movement information
                    update_query = """
                        UPDATE News SET 
                        close_before = ?, 
                        high_after = ?,
                        low_after = ?,
                        Pips_Highest_Shadow = ?,
                        Pips_Lowest_Shadow = ?
                        WHERE id = ?
                    """
                    
                    # Calculate pip movements
                    highest_shadow_pips = None
                    lowest_shadow_pips = None
                    
                    if max_high is not None and close_before is not None and max_high > close_before:
                        highest_shadow_pips = '{:.1f}'.format((max_high - close_before) * ratio_pips)
                        
                    if min_low is not None and close_before is not None and min_low < close_before:
                        lowest_shadow_pips = '{:.1f}'.format((close_before - min_low) * ratio_pips)
                    
                    # Format values for update
                    high_after = '{:.5f}'.format(max_high) if max_high is not None else None
                    low_after = '{:.5f}'.format(min_low) if min_low is not None else None
                    close_before_str = '{:.5f}'.format(close_before) if close_before is not None else None
                    
                    conn.execute(update_query, (
                        close_before_str,
                        high_after,
                        low_after,
                        highest_shadow_pips,
                        lowest_shadow_pips,
                        event['id']
                    ))
        
        conn.commit()
        conn.close()
        
        logger.info("Successfully calculated price movement for news events")
        
    except Exception as e:
        logger.error(f"Error calculating price movement: {e}")
        if conn:
            conn.close()
