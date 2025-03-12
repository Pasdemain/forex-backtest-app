"""
Backtest Analysis Module

This module handles backtesting trading strategies against historical data.
It simulates trades and analyzes performance.
"""

import logging
from datetime import datetime, timedelta
import pandas as pd

from src.utils.config import get_config
from src.utils.time_utils import (
    format_datetime_for_db, 
    format_display_date, 
    format_display_time,
    get_session_for_time,
    combine_date_and_time
)
from src.data.database import (
    get_candle_at_time,
    get_subsequent_candles,
    get_news_around_time,
    insert_trading_entry
)

logger = logging.getLogger(__name__)

def backtest_trade(db_path, symbol, entry_data):
    """
    Backtest a single trade with the given parameters.
    
    Args:
        db_path (str): Path to the database file
        symbol (str): The trading symbol
        entry_data (dict): Entry data including date, time, position, etc.
        
    Returns:
        dict: Results of the backtest including performance metrics
    """
    logger.info(f"Backtesting trade for {symbol} on {entry_data.get('day')} at {entry_data.get('OpenTime')}")
    
    try:
        config = get_config()
        
        # Get pip multiplier for the symbol
        pip_multipliers = config['trading']['pips_multiplication']
        ratio_pips = pip_multipliers.get(symbol, 10000)
        
        # Get currency ratio for price calculation
        currency_ratios = config['trading']['currency_ratios']
        ratiopips = currency_ratios.get(symbol, 0.0001)
        
        # Get day and time info
        day_open = entry_data.get('day')
        open_time = entry_data.get('OpenTime')
        
        # Convert to datetime
        start_datetime = combine_date_and_time(day_open, open_time)
        if start_datetime is None:
            logger.error(f"Failed to parse date and time: {day_open} {open_time}")
            return None
        
        # Format for database query
        db_time_str = format_datetime_for_db(start_datetime)
        
        # Determine trading session
        session = get_session_for_time(start_datetime)
        
        # Get open price
        candle = get_candle_at_time(db_path, symbol, 'M15', db_time_str)
        if candle is None:
            logger.error(f"No candle found for {symbol} at {db_time_str}")
            return None
        
        open_value = candle['open']
        logger.info(f"Open value: {open_value}")
        
        # Get stoploss sizes and trade ratios from config
        stoploss_sizes = entry_data.get('stoploss_sizes') or config['trading']['stoploss_sizes']
        trade_ratios = entry_data.get('trade_ratios') or config['trading']['trade_ratios']
        
        # Position type
        position = entry_data.get('position')
        if not position:
            logger.error("Position type not specified")
            return None
        
        # Process each combination of stoploss size and trade ratio
        results = []
        
        for stoploss_size in stoploss_sizes:
            for ratio in trade_ratios:
                stoploss_price = stoploss_size * ratiopips
                
                if position == 'Buy':
                    take_profit_price = open_value + (stoploss_price * ratio)
                    stop_loss_price = open_value - stoploss_price
                else:  # Sell
                    take_profit_price = open_value - (stoploss_price * ratio)
                    stop_loss_price = open_value + stoploss_price
                
                logger.info(f"Testing: SL={stoploss_size}, Ratio=1:{ratio}, TP={take_profit_price}, SL={stop_loss_price}")
                
                # Get subsequent candles to simulate trade progression
                subsequent_candles = get_subsequent_candles(db_path, symbol, 'M15', db_time_str)
                
                # Simulate the trade
                found_result = False
                for subcandle in subsequent_candles:
                    high = subcandle['high']
                    low = subcandle['low']
                    candle_time = subcandle['time']
                    
                    if position == 'Buy':
                        if high >= take_profit_price:
                            result_status = 'Winning'
                            found_result = True
                        elif low <= stop_loss_price:
                            result_status = 'Losing'
                            found_result = True
                    else:  # Sell
                        if low <= take_profit_price:
                            result_status = 'Winning'
                            found_result = True
                        elif high >= stop_loss_price:
                            result_status = 'Losing'
                            found_result = True
                    
                    if found_result:
                        day_close_datetime = datetime.strptime(candle_time, '%Y-%m-%d %H:%M:%S')
                        
                        # Format for display
                        day_close_str = format_display_date(day_close_datetime)
                        hour_close_str = format_display_time(day_close_datetime)
                        
                        # Calculate trade duration
                        duration = day_close_datetime - start_datetime
                        duration_hours = round(duration.total_seconds() / 3600, 1)
                        
                        # Create result entry
                        entry_result = {
                            **entry_data,
                            'session': session,
                            'StoplossSize': stoploss_size,
                            'TradeRatio': f'1:{ratio}',
                            'Closeday': day_close_str,
                            'CloseTime': hour_close_str,
                            'Result': result_status,
                            'StartDatetime': start_datetime.strftime('%Y-%m-%d %H:%M'),
                            'EndDatetime': day_close_datetime.strftime('%Y-%m-%d %H:%M'),
                            'duration_hours': duration_hours
                        }
                        
                        results.append(entry_result)
                        
                        # Save to database if requested
                        if entry_data.get('save_to_db', True):
                            success, message = insert_trading_entry(db_path, entry_result)
                            if not success:
                                logger.warning(f"Failed to save entry to database: {message}")
                        
                        logger.info(f"Result: {result_status} at {day_close_datetime}, duration: {duration_hours} hours")
                        break  # Exit loop after finding result
                
                if not found_result:
                    logger.warning("No trade outcome found after analyzing all available candles")
                    
                    # Create an inconclusive result entry
                    entry_result = {
                        **entry_data,
                        'session': session,
                        'StoplossSize': stoploss_size,
                        'TradeRatio': f'1:{ratio}',
                        'Closeday': 'N/A',
                        'CloseTime': 'N/A',
                        'Result': 'Inconclusive',
                        'StartDatetime': start_datetime.strftime('%Y-%m-%d %H:%M'),
                        'EndDatetime': 'N/A',
                        'duration_hours': 0
                    }
                    results.append(entry_result)
        
        return results
    
    except Exception as e:
        logger.error(f"Error in backtest_trade: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def batch_backtest(db_path, symbol, entries):
    """
    Run a batch of backtests for multiple entries.
    
    Args:
        db_path (str): Path to the database file
        symbol (str): The trading symbol
        entries (list): List of entry data dictionaries
        
    Returns:
        dict: Aggregated results of all backtests
    """
    logger.info(f"Running batch backtest for {symbol} with {len(entries)} entries")
    
    all_results = []
    
    for entry in entries:
        result = backtest_trade(db_path, symbol, entry)
        if result:
            all_results.extend(result)
    
    # Calculate summary statistics
    summary = summarize_backtest_results(all_results)
    
    return {
        'individual_results': all_results,
        'summary': summary
    }

def summarize_backtest_results(results):
    """
    Summarize the results of a backtest.
    
    Args:
        results (list): List of backtest result dictionaries
        
    Returns:
        dict: Summary statistics
    """
    if not results:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'inconclusive_trades': 0,
            'win_rate': 0,
            'average_duration': 0,
            'by_stoploss': {},
            'by_ratio': {},
            'by_session': {},
            'by_h4': {},
            'by_h1': {},
            'by_m15': {},
            'by_entry_point': {}
        }
    
    # Count overall statistics
    total_trades = len(results)
    winning_trades = sum(1 for r in results if r.get('Result') == 'Winning')
    losing_trades = sum(1 for r in results if r.get('Result') == 'Losing')
    inconclusive_trades = sum(1 for r in results if r.get('Result') == 'Inconclusive')
    
    win_rate = (winning_trades / (winning_trades + losing_trades)) * 100 if (winning_trades + losing_trades) > 0 else 0
    
    # Calculate average duration (excluding inconclusive trades)
    durations = [r.get('duration_hours', 0) for r in results if r.get('Result') != 'Inconclusive' and r.get('duration_hours', 0) > 0]
    average_duration = sum(durations) / len(durations) if durations else 0
    
    # Group results by different parameters
    by_stoploss = {}
    by_ratio = {}
    by_session = {}
    by_h4 = {}
    by_h1 = {}
    by_m15 = {}
    by_entry_point = {}
    
    for result in results:
        # Skip inconclusive results for win rate calculations
        if result.get('Result') == 'Inconclusive':
            continue
        
        # By stop loss size
        sl_size = result.get('StoplossSize')
        if sl_size not in by_stoploss:
            by_stoploss[sl_size] = {'total': 0, 'wins': 0, 'win_rate': 0}
        by_stoploss[sl_size]['total'] += 1
        if result.get('Result') == 'Winning':
            by_stoploss[sl_size]['wins'] += 1
        
        # By trade ratio
        ratio = result.get('TradeRatio')
        if ratio not in by_ratio:
            by_ratio[ratio] = {'total': 0, 'wins': 0, 'win_rate': 0}
        by_ratio[ratio]['total'] += 1
        if result.get('Result') == 'Winning':
            by_ratio[ratio]['wins'] += 1
        
        # By session
        session = result.get('session')
        if session not in by_session:
            by_session[session] = {'total': 0, 'wins': 0, 'win_rate': 0}
        by_session[session]['total'] += 1
        if result.get('Result') == 'Winning':
            by_session[session]['wins'] += 1
        
        # By H4 trend
        h4 = result.get('H4')
        if h4 and h4 not in by_h4:
            by_h4[h4] = {'total': 0, 'wins': 0, 'win_rate': 0}
        if h4:
            by_h4[h4]['total'] += 1
            if result.get('Result') == 'Winning':
                by_h4[h4]['wins'] += 1
        
        # By H1 trend
        h1 = result.get('H1')
        if h1 and h1 not in by_h1:
            by_h1[h1] = {'total': 0, 'wins': 0, 'win_rate': 0}
        if h1:
            by_h1[h1]['total'] += 1
            if result.get('Result') == 'Winning':
                by_h1[h1]['wins'] += 1
        
        # By M15 structure
        m15 = result.get('M15')
        if m15 and m15 not in by_m15:
            by_m15[m15] = {'total': 0, 'wins': 0, 'win_rate': 0}
        if m15:
            by_m15[m15]['total'] += 1
            if result.get('Result') == 'Winning':
                by_m15[m15]['wins'] += 1
        
        # By entry point
        entry_point = result.get('EntryPoint')
        if entry_point and entry_point not in by_entry_point:
            by_entry_point[entry_point] = {'total': 0, 'wins': 0, 'win_rate': 0}
        if entry_point:
            by_entry_point[entry_point]['total'] += 1
            if result.get('Result') == 'Winning':
                by_entry_point[entry_point]['wins'] += 1
    
    # Calculate win rates for each group
    for group in [by_stoploss, by_ratio, by_session, by_h4, by_h1, by_m15, by_entry_point]:
        for key in group:
            group[key]['win_rate'] = (group[key]['wins'] / group[key]['total']) * 100 if group[key]['total'] > 0 else 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'inconclusive_trades': inconclusive_trades,
        'win_rate': win_rate,
        'average_duration': average_duration,
        'by_stoploss': by_stoploss,
        'by_ratio': by_ratio,
        'by_session': by_session,
        'by_h4': by_h4,
        'by_h1': by_h1,
        'by_m15': by_m15,
        'by_entry_point': by_entry_point
    }

def check_news_for_entry(db_path, start_datetime, hours_before=6, hours_after=6):
    """
    Check for news events around a potential entry time.
    
    Args:
        db_path (str): Path to the database file
        start_datetime (datetime): The entry time
        hours_before (int): Hours to look back for news
        hours_after (int): Hours to look ahead for news
        
    Returns:
        list: News events around the entry time
    """
    return get_news_around_time(db_path, start_datetime, hours_before, hours_after)

def calculate_drawdown(results):
    """
    Calculate maximum drawdown based on a series of trade results.
    
    Args:
        results (list): List of trade result dictionaries
        
    Returns:
        dict: Drawdown metrics
    """
    # Sort results by start datetime
    sorted_results = sorted(results, key=lambda x: x.get('StartDatetime', ''))
    
    # Initialize tracking variables
    balance = 100  # Start with 100 units
    peak_balance = 100
    current_drawdown = 0
    max_drawdown = 0
    max_drawdown_start = None
    max_drawdown_end = None
    drawdown_periods = []
    
    for result in sorted_results:
        # Skip inconclusive results
        if result.get('Result') == 'Inconclusive':
            continue
        
        # Get risk-reward details
        sl_size = float(result.get('StoplossSize', 0))
        ratio_str = result.get('TradeRatio', '1:1')
        ratio = float(ratio_str.split(':')[1]) if ':' in ratio_str else 1
        
        # Calculate profit/loss
        risk_percent = 2  # Risk 2% per trade
        if result.get('Result') == 'Winning':
            profit_percent = risk_percent * ratio
            balance += profit_percent
        else:  # Losing
            balance -= risk_percent
        
        # Update peak balance
        if balance > peak_balance:
            peak_balance = balance
            
            # If we were in a drawdown, record it
            if current_drawdown > 0:
                drawdown_periods.append({
                    'start': max_drawdown_start,
                    'end': result.get('EndDatetime'),
                    'depth': current_drawdown,
                    'recovery_trades': 1  # Simplified
                })
                current_drawdown = 0
                max_drawdown_start = None
        
        # Calculate current drawdown
        current_drawdown = (peak_balance - balance) / peak_balance * 100
        
        # Update max drawdown if needed
        if current_drawdown > max_drawdown:
            max_drawdown = current_drawdown
            if max_drawdown_start is None:
                max_drawdown_start = result.get('StartDatetime')
            max_drawdown_end = result.get('EndDatetime')
    
    return {
        'max_drawdown_percent': max_drawdown,
        'max_drawdown_start': max_drawdown_start,
        'max_drawdown_end': max_drawdown_end,
        'final_balance': balance,
        'peak_balance': peak_balance,
        'drawdown_periods': drawdown_periods
    }

def generate_equity_curve(results):
    """
    Generate an equity curve from a series of trade results.
    
    Args:
        results (list): List of trade result dictionaries
        
    Returns:
        DataFrame: Equity curve data
    """
    # Sort results by start datetime
    sorted_results = sorted(results, key=lambda x: x.get('StartDatetime', ''))
    
    # Initialize data for equity curve
    equity_data = []
    balance = 100  # Start with 100 units
    
    for result in sorted_results:
        # Skip inconclusive results
        if result.get('Result') == 'Inconclusive':
            continue
        
        # Get risk-reward details
        sl_size = float(result.get('StoplossSize', 0))
        ratio_str = result.get('TradeRatio', '1:1')
        ratio = float(ratio_str.split(':')[1]) if ':' in ratio_str else 1
        
        # Calculate profit/loss
        risk_percent = 2  # Risk 2% per trade
        if result.get('Result') == 'Winning':
            profit_percent = risk_percent * ratio
            balance += profit_percent
        else:  # Losing
            balance -= risk_percent
        
        # Add point to equity curve
        equity_data.append({
            'datetime': result.get('EndDatetime'),
            'balance': balance,
            'trade_result': result.get('Result'),
            'position': result.get('position'),
            'stoploss': result.get('StoplossSize'),
            'ratio': result.get('TradeRatio')
        })
    
    # Convert to DataFrame
    if equity_data:
        df = pd.DataFrame(equity_data)
        return df
    else:
        return pd.DataFrame(columns=['datetime', 'balance', 'trade_result', 'position', 'stoploss', 'ratio'])
