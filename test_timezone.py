#!/usr/bin/env python3
"""
Timezone Test Script

This script fetches current GBPJPY data from MT5 and displays the timestamps
in different formats to help diagnose timezone conversion issues.
"""

import sys
import os
from datetime import datetime, timedelta
import pytz

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import MetaTrader5 with error handling
try:
    import MetaTrader5 as mt5
    import pandas as pd
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required packages: pip install MetaTrader5 pandas")
    sys.exit(1)

from utils.config import get_config, setup_config

def test_mt5_timezone():
    """Test MT5 timezone and data retrieval."""
    
    print("=" * 60)
    print("MT5 TIMEZONE TEST")
    print("=" * 60)
    
    # Initialize MT5
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return False
    
    try:
        # Get current configuration
        setup_config()
        config = get_config()
        configured_timezone = config['mt5']['timezone']
        
        print(f"Configured timezone: {configured_timezone}")
        print(f"Current system time: {datetime.now()}")
        print(f"Current UTC time: {datetime.utcnow()}")
        
        # Get timezone objects
        paris_tz = pytz.timezone('Europe/Paris')
        configured_tz = pytz.timezone(configured_timezone)
        utc_tz = pytz.UTC
        
        print(f"Paris time now: {datetime.now(paris_tz)}")
        print(f"Configured timezone now: {datetime.now(configured_tz)}")
        print()
        
        # Get terminal info
        terminal_info = mt5.terminal_info()
        if terminal_info:
            print("MT5 Terminal Info:")
            print(f"  Company: {terminal_info.company}")
            print(f"  Name: {terminal_info.name}")
            print(f"  Path: {terminal_info.path}")
            print()
        
        # Get account info to see server details
        account_info = mt5.account_info()
        if account_info:
            print("MT5 Account Info:")
            print(f"  Server: {account_info.server}")
            print(f"  Company: {account_info.company}")
            print()
        
        # Test with GBPJPY - get last few candles
        symbol = "GBPJPY"
        timeframe = mt5.TIMEFRAME_M15
        
        print(f"Fetching recent {symbol} M15 data...")
        
        # Get the last 5 candles
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 5)
        
        if rates is None or len(rates) == 0:
            print(f"No data returned for {symbol}")
            print(f"MT5 error: {mt5.last_error()}")
            return False
        
        print(f"Retrieved {len(rates)} candles")
        print()
        
        # Convert to DataFrame
        df = pd.DataFrame(rates)
        
        print("RAW MT5 DATA:")
        print("-" * 40)
        for i, row in df.iterrows():
            unix_timestamp = row['time']
            price = row['close']
            
            print(f"Candle {i+1}:")
            print(f"  Unix timestamp: {unix_timestamp}")
            print(f"  Close price: {price}")
            
            # Convert timestamp to different timezone representations
            
            # Method 1: Assume it's UTC (current code approach)
            dt_utc = pd.to_datetime(unix_timestamp, unit='s', utc=True)
            dt_paris_from_utc = dt_utc.tz_convert('Europe/Paris')
            
            print(f"  As UTC: {dt_utc}")
            print(f"  UTC->Paris: {dt_paris_from_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Method 2: Assume it's already in Paris timezone
            dt_naive = pd.to_datetime(unix_timestamp, unit='s')
            dt_paris_direct = dt_naive.tz_localize('Europe/Paris')
            
            print(f"  As naive: {dt_naive}")
            print(f"  Localized to Paris: {dt_paris_direct.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Method 3: Try other common broker timezones
            # Many brokers use GMT+2 or GMT+3
            try:
                dt_gmt2 = dt_naive.tz_localize('Etc/GMT-2')  # GMT+2
                dt_gmt3 = dt_naive.tz_localize('Etc/GMT-3')  # GMT+3
                print(f"  If GMT+2: {dt_gmt2.tz_convert('Europe/Paris').strftime('%Y-%m-%d %H:%M:%S %Z')}")
                print(f"  If GMT+3: {dt_gmt3.tz_convert('Europe/Paris').strftime('%Y-%m-%d %H:%M:%S %Z')}")
            except:
                pass
            
            print()
        
        # Get current market price for comparison
        print("CURRENT MARKET DATA:")
        print("-" * 40)
        
        # Get current tick
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            current_time = datetime.now()
            print(f"Current system time: {current_time}")
            print(f"Current {symbol} bid: {tick.bid}")
            print(f"Current {symbol} ask: {tick.ask}")
            print(f"Tick time (unix): {tick.time}")
            
            # Convert tick time
            tick_dt_utc = pd.to_datetime(tick.time, unit='s', utc=True)
            tick_dt_paris = tick_dt_utc.tz_convert('Europe/Paris')
            print(f"Tick time as UTC: {tick_dt_utc}")
            print(f"Tick time in Paris: {tick_dt_paris.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Also try assuming it's already in the right timezone
            tick_dt_naive = pd.to_datetime(tick.time, unit='s')
            tick_dt_paris_direct = tick_dt_naive.tz_localize('Europe/Paris')
            print(f"Tick time localized to Paris: {tick_dt_paris_direct.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        print()
        print("=" * 60)
        print("INSTRUCTIONS:")
        print("1. Compare the times above with your TradingView")
        print("2. Find which conversion method gives the correct time")
        print("3. Note the close price to verify we have the right candle")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    test_mt5_timezone()
