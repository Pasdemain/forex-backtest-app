"""
News Analysis Module

This module handles importing, processing, and analyzing forex news events.
"""

import logging
import os
import pandas as pd
from datetime import datetime

from src.data.database import insert_news_data, calculate_pips_movement
from src.utils.config import get_config

logger = logging.getLogger(__name__)

def import_news_from_excel(excel_path, db_path):
    """
    Import news data from an Excel file into the database.
    
    Args:
        excel_path (str): Path to the Excel file containing news data
        db_path (str): Path to the database file
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Importing news data from Excel file: {excel_path}")
    
    try:
        # Check if the file exists
        if not os.path.exists(excel_path):
            logger.error(f"Excel file not found: {excel_path}")
            return False
        
        # Read the Excel file
        df = pd.read_excel(excel_path)
        
        # Check if the required columns are present
        required_columns = ['time', 'impact', 'currency', 'news']
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"Required column '{col}' not found in Excel file")
                return False
        
        # Convert Unix timestamp to datetime string if needed
        if df['time'].dtype != 'object':
            df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Ensure other columns are present (add empty ones if missing)
        for col in ['actual', 'forecast', 'previous']:
            if col not in df.columns:
                df[col] = None
        
        # Sort by time
        df.sort_values(by='time', inplace=True)
        
        # Insert into database
        insert_news_data(db_path, df)
        
        # Calculate price movement after news events
        calculate_pips_movement(db_path, df.to_dict('records'))
        
        logger.info(f"Successfully imported {len(df)} news events")
        return True
    except Exception as e:
        logger.error(f"Error importing news data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def analyze_news_impact(db_path, currency=None, min_pips=10.0):
    """
    Analyze the impact of news events on price movement.
    
    Args:
        db_path (str): Path to the database file
        currency (str, optional): Filter by currency
        min_pips (float, optional): Minimum pips movement to consider
        
    Returns:
        DataFrame: Analysis results
    """
    logger.info(f"Analyzing news impact for database: {db_path}")
    
    try:
        # Connect to the database
        conn = pd.read_sql_query("SELECT * FROM News", db_path)
        
        # Filter by currency if specified
        if currency:
            conn = conn[conn['currency'] == currency]
        
        # Convert numeric columns
        conn['Pips_Highest_Shadow'] = pd.to_numeric(conn['Pips_Highest_Shadow'], errors='coerce')
        conn['Pips_Lowest_Shadow'] = pd.to_numeric(conn['Pips_Lowest_Shadow'], errors='coerce')
        
        # Filter by minimum pips movement
        significant_moves = conn[(conn['Pips_Highest_Shadow'] >= min_pips) | (conn['Pips_Lowest_Shadow'] >= min_pips)]
        
        # Group by news name and calculate average movement
        news_impact = significant_moves.groupby('news').agg({
            'Pips_Highest_Shadow': ['count', 'mean', 'max'],
            'Pips_Lowest_Shadow': ['count', 'mean', 'max'],
            'impact': lambda x: x.mode().iloc[0] if not x.empty else None
        }).reset_index()
        
        # Flatten the multi-level columns
        news_impact.columns = ['news', 'upward_count', 'upward_mean', 'upward_max', 
                             'downward_count', 'downward_mean', 'downward_max', 'typical_impact']
        
        # Calculate total count and combined average
        news_impact['total_count'] = news_impact['upward_count'] + news_impact['downward_count']
        news_impact['avg_movement'] = (news_impact['upward_mean'] + news_impact['downward_mean']) / 2
        
        # Sort by total count and average movement
        news_impact.sort_values(by=['total_count', 'avg_movement'], ascending=False, inplace=True)
        
        logger.info(f"Found {len(news_impact)} news events with significant price impact")
        return news_impact
    except Exception as e:
        logger.error(f"Error analyzing news impact: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return pd.DataFrame()

def find_upcoming_similar_news(news_name, recent_news_data):
    """
    Find similar news events to a given news name in recent data.
    
    Args:
        news_name (str): The name of the news event
        recent_news_data (DataFrame): Recent news data
        
    Returns:
        DataFrame: Filtered news events
    """
    try:
        # Filter by exact name match
        similar_news = recent_news_data[recent_news_data['news'] == news_name]
        
        # If no exact matches, try fuzzy matching
        if similar_news.empty:
            # Try partial matches
            similar_news = recent_news_data[recent_news_data['news'].str.contains(news_name, case=False)]
        
        return similar_news
    except Exception as e:
        logger.error(f"Error finding similar news: {e}")
        return pd.DataFrame()

def get_high_impact_news(db_path, start_date, end_date=None):
    """
    Get high-impact news events within a date range.
    
    Args:
        db_path (str): Path to the database file
        start_date (datetime): The start date
        end_date (datetime, optional): The end date. If None, current time is used.
        
    Returns:
        DataFrame: High-impact news events
    """
    logger.info(f"Getting high-impact news from {start_date} to {end_date or 'now'}")
    
    try:
        # Convert dates to strings
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S') if end_date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Query the database
        query = f"""
            SELECT * FROM News 
            WHERE impact = 'High' AND time BETWEEN '{start_date_str}' AND '{end_date_str}'
            ORDER BY time ASC
        """
        
        news_data = pd.read_sql_query(query, db_path)
        
        logger.info(f"Found {len(news_data)} high-impact news events")
        return news_data
    except Exception as e:
        logger.error(f"Error getting high-impact news: {e}")
        return pd.DataFrame()

def classify_news_event(news_name, impact, pip_movement):
    """
    Classify a news event based on its name, impact, and typical pip movement.
    
    Args:
        news_name (str): The name of the news event
        impact (str): The impact level (e.g., 'High', 'Medium', 'Low')
        pip_movement (float): Typical pip movement caused by this news
        
    Returns:
        dict: Classification details
    """
    # List of important economic indicators
    rate_decisions = ['Rate Decision', 'Interest Rate Decision', 'Cash Rate', 'Policy Rate']
    inflation_reports = ['CPI', 'Inflation', 'Consumer Price', 'PPI', 'Producer Price']
    employment_reports = ['NFP', 'Non-Farm', 'Employment Change', 'Unemployment', 'Jobless Claims']
    gdp_reports = ['GDP', 'Gross Domestic Product']
    manufacturing = ['PMI', 'Manufacturing', 'Industrial Production']
    retail = ['Retail Sales', 'Consumer Spending']
    sentiment = ['Consumer Confidence', 'Consumer Sentiment', 'Business Confidence']
    central_bank = ['Fed', 'Federal Reserve', 'ECB', 'BOE', 'BOJ', 'RBA', 'RBNZ', 'FOMC']
    
    # Classification dictionary
    classification = {
        'category': 'Other',
        'importance': 'Low',
        'volatility': 'Low',
        'trade_advice': 'No specific advice'
    }
    
    # Classify by name
    if any(term in news_name for term in rate_decisions):
        classification['category'] = 'Interest Rate Decision'
    elif any(term in news_name for term in inflation_reports):
        classification['category'] = 'Inflation Report'
    elif any(term in news_name for term in employment_reports):
        classification['category'] = 'Employment Report'
    elif any(term in news_name for term in gdp_reports):
        classification['category'] = 'GDP Report'
    elif any(term in news_name for term in manufacturing):
        classification['category'] = 'Manufacturing Report'
    elif any(term in news_name for term in retail):
        classification['category'] = 'Retail Sales'
    elif any(term in news_name for term in sentiment):
        classification['category'] = 'Sentiment Indicator'
    elif any(term in news_name for term in central_bank):
        classification['category'] = 'Central Bank Communication'
    
    # Classify by impact
    if impact == 'High':
        classification['importance'] = 'High'
    elif impact == 'Medium':
        classification['importance'] = 'Medium'
    
    # Classify by pip movement
    if pip_movement >= 50:
        classification['volatility'] = 'Very High'
        classification['trade_advice'] = 'Consider staying out of the market or using very wide stops'
    elif pip_movement >= 30:
        classification['volatility'] = 'High'
        classification['trade_advice'] = 'Use wider stops than usual and reduced position size'
    elif pip_movement >= 15:
        classification['volatility'] = 'Medium'
        classification['trade_advice'] = 'Use standard stops but be cautious'
    else:
        classification['volatility'] = 'Low'
        classification['trade_advice'] = 'Normal trading conditions expected'
    
    return classification
