#!/usr/bin/env python3
"""
Enhanced Timezone Test Script

This script tests the timezone conversion across European time changes
to verify the dynamic timezone handling works correctly.
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
    sys.exit(1)

from utils.config import get_config, setup_config
from data.mt5_connector import get_broker_timezone_for_date

def test_timezone_conversion():
    """Test timezone conversion for different periods."""
    
    print("=" * 80)
    print("ENHANCED TIMEZONE TEST - DST HANDLING")
    print("=" * 80)
    
    # Test dates around European time changes
    test_dates = [
        datetime(2025, 1, 15, 12, 0),   # Winter time (CET, UTC+1)
        datetime(2025, 3, 25, 12, 0),   # Just before spring change
        datetime(2025, 4, 15, 12, 0),   # Summer time (CEST, UTC+2)
        datetime(2025, 8, 15, 12, 0),   # Summer time (CEST, UTC+2)
        datetime(2025, 10, 25, 12, 0),  # Just before autumn change
        datetime(2025, 12, 15, 12, 0),  # Winter time (CET, UTC+1)
    ]
    
    print("Testing broker timezone detection for different dates:")
    print("-" * 60)
    
    for test_date in test_dates:
        broker_tz = get_broker_timezone_for_date(test_date)
        paris_tz = pytz.timezone('Europe/Paris')
        
        # Check if Paris is in DST for this date
        paris_date = paris_tz.localize(test_date)
        is_dst = bool(paris_date.dst())
        paris_offset = paris_date.strftime('%Z (UTC%z)')
        
        print(f"Date: {test_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Paris timezone: {paris_offset}, DST: {is_dst}")
        print(f"  Detected broker timezone: {broker_tz}")
        print(f"  Expected: {'GMT+3' if is_dst else 'GMT+2'}")
        print()
    
    print("=" * 80)
    print("INSTRUCTIONS:")
    print("1. Check that broker timezone switches between GMT+2 (winter) and GMT+3 (summer)")
    print("2. Winter periods should show GMT+2")  
    print("3. Summer periods should show GMT+3")
    print("4. Re-import your data and test with candles from different periods")
    print("=" * 80)

if __name__ == "__main__":
    setup_config()
    test_timezone_conversion()
