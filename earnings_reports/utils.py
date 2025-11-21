"""
Earnings Pipeline Utilities

Helper functions and utilities for the earnings report pipeline.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None):
    """
    Setup logging configuration for the earnings pipeline.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format
        )
    
    logger.info(f"Logging initialized at {log_level} level")


def validate_ticker(ticker: str) -> bool:
    """
    Validate if a ticker symbol is properly formatted.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        True if valid, False otherwise
    """
    if not ticker or not isinstance(ticker, str):
        return False
    
    # Basic validation: 1-5 uppercase letters
    ticker = ticker.strip().upper()
    if len(ticker) < 1 or len(ticker) > 5:
        return False
    
    if not ticker.isalpha():
        return False
    
    return True


def format_ticker(ticker: str) -> str:
    """
    Format ticker symbol to standard format (uppercase, stripped).
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Formatted ticker
    """
    return ticker.strip().upper()


def calculate_earnings_date_range(days_before: int = 30, days_after: int = 30) -> tuple:
    """
    Calculate date range for earnings calendar queries.
    
    Args:
        days_before: Days before today to include
        days_after: Days after today to include
        
    Returns:
        Tuple of (start_date, end_date) as strings in YYYY-MM-DD format
    """
    today = datetime.now()
    start_date = (today - timedelta(days=days_before)).strftime('%Y-%m-%d')
    end_date = (today + timedelta(days=days_after)).strftime('%Y-%m-%d')
    
    return start_date, end_date


def is_earnings_date_upcoming(earnings_date: str, days_threshold: int = 7) -> bool:
    """
    Check if an earnings date is upcoming within a threshold.
    
    Args:
        earnings_date: Earnings date as string (YYYY-MM-DD)
        days_threshold: Number of days to consider as "upcoming"
        
    Returns:
        True if upcoming, False otherwise
    """
    if not earnings_date or earnings_date == 'N/A':
        return False
    
    try:
        date_obj = datetime.strptime(earnings_date[:10], '%Y-%m-%d')
        today = datetime.now()
        days_until = (date_obj - today).days
        
        return 0 <= days_until <= days_threshold
    except (ValueError, TypeError):
        return False


def is_earnings_date_recent(earnings_date: str, days_threshold: int = 7) -> bool:
    """
    Check if an earnings date recently passed within a threshold.
    
    Args:
        earnings_date: Earnings date as string (YYYY-MM-DD)
        days_threshold: Number of days to consider as "recent"
        
    Returns:
        True if recent, False otherwise
    """
    if not earnings_date or earnings_date == 'N/A':
        return False
    
    try:
        date_obj = datetime.strptime(earnings_date[:10], '%Y-%m-%d')
        today = datetime.now()
        days_since = (today - date_obj).days
        
        return 0 <= days_since <= days_threshold
    except (ValueError, TypeError):
        return False


def save_json(data: Dict[str, Any], filepath: str):
    """
    Save data to JSON file with pretty formatting.
    
    Args:
        data: Data to save
        filepath: Output file path
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.info(f"Saved JSON data to: {filepath}")


def load_json(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file.
    
    Args:
        filepath: Input file path
        
    Returns:
        Loaded data or None if file doesn't exist
    """
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {filepath}: {e}")
        return None


def get_fiscal_quarter(date_str: str) -> str:
    """
    Determine fiscal quarter from a date string.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        Fiscal quarter (Q1, Q2, Q3, Q4) or 'N/A'
    """
    if not date_str or date_str == 'N/A':
        return 'N/A'
    
    try:
        date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
        month = date_obj.month
        
        if 1 <= month <= 3:
            return 'Q1'
        elif 4 <= month <= 6:
            return 'Q2'
        elif 7 <= month <= 9:
            return 'Q3'
        else:
            return 'Q4'
    except (ValueError, TypeError):
        return 'N/A'


def calculate_percentage_change(current: float, previous: float) -> Optional[float]:
    """
    Calculate percentage change between two values.
    
    Args:
        current: Current value
        previous: Previous value
        
    Returns:
        Percentage change or None if calculation not possible
    """
    if previous == 0 or previous is None or current is None:
        return None
    
    try:
        return ((current - previous) / abs(previous)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a percentage value with sign.
    
    Args:
        value: Percentage value
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    if value is None:
        return 'N/A'
    
    try:
        sign = '+' if value > 0 else ''
        return f"{sign}{value:.{decimals}f}%"
    except (ValueError, TypeError):
        return 'N/A'


def create_earnings_summary(processed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a concise summary of earnings data.
    
    Args:
        processed_data: Processed earnings data
        
    Returns:
        Summary dictionary
    """
    earnings_data = processed_data.get('earnings_data', {})
    
    summary = {
        'ticker': processed_data.get('ticker', 'N/A'),
        'company_name': earnings_data.get('company_identification', {}).get('company_name', 'N/A'),
        'earnings_date': earnings_data.get('earnings_timeline', {}).get('earnings_date', 'N/A'),
        'fiscal_period': f"{earnings_data.get('earnings_timeline', {}).get('fiscal_quarter', 'N/A')} {earnings_data.get('earnings_timeline', {}).get('fiscal_year', 'N/A')}",
        'eps': earnings_data.get('income_statement', {}).get('earnings_per_share_diluted', 'N/A'),
        'revenue': earnings_data.get('income_statement', {}).get('total_revenue', 'N/A'),
        'net_income': earnings_data.get('income_statement', {}).get('net_income', 'N/A'),
        'profit_margin': earnings_data.get('calculated_ratios', {}).get('profit_margin', 'N/A'),
        'current_price': earnings_data.get('stock_price', {}).get('price', 'N/A'),
        'data_quality_score': processed_data.get('data_quality', {}).get('completeness_score', 'N/A')
    }
    
    return summary


def get_missing_data_report(processed_data: Dict[str, Any]) -> List[str]:
    """
    Generate a report of missing data fields.
    
    Args:
        processed_data: Processed earnings data
        
    Returns:
        List of missing field descriptions
    """
    missing = []
    earnings_data = processed_data.get('earnings_data', {})
    
    categories = [
        ('company_identification', 'Company Information'),
        ('earnings_timeline', 'Earnings Timeline'),
        ('income_statement', 'Income Statement'),
        ('balance_sheet', 'Balance Sheet'),
        ('cash_flow', 'Cash Flow'),
        ('analyst_estimates', 'Analyst Estimates'),
        ('actual_vs_estimate', 'Actual vs Estimate'),
        ('stock_price', 'Stock Price'),
        ('guidance', 'Guidance'),
        ('calculated_ratios', 'Financial Ratios')
    ]
    
    for category_key, category_name in categories:
        category_data = earnings_data.get(category_key, {})
        if not category_data:
            missing.append(f"Entire {category_name} section is missing")
            continue
        
        na_fields = [k for k, v in category_data.items() if v == 'N/A']
        if na_fields:
            missing.append(f"{category_name}: {', '.join(na_fields)}")
    
    return missing


def check_api_credentials() -> Dict[str, bool]:
    """
    Check if required API credentials are configured.
    
    Returns:
        Dictionary with API availability status
    """
    status = {
        'finnhub': bool(os.getenv('FINNHUB_API_KEY')),
        'alpha_vantage': bool(os.getenv('ALPHA_API_KEY'))
    }
    
    return status


def estimate_cache_size(cache_dir: str) -> Dict[str, Any]:
    """
    Estimate the size and count of cached files.
    
    Args:
        cache_dir: Cache directory path
        
    Returns:
        Dictionary with cache statistics
    """
    if not os.path.exists(cache_dir):
        return {'count': 0, 'size_mb': 0}
    
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk(cache_dir):
        for file in files:
            filepath = os.path.join(root, file)
            total_size += os.path.getsize(filepath)
            file_count += 1
    
    return {
        'count': file_count,
        'size_mb': round(total_size / (1024 * 1024), 2)
    }


def clear_old_cache(cache_dir: str, days_old: int = 7):
    """
    Clear cache files older than specified days.
    
    Args:
        cache_dir: Cache directory path
        days_old: Age threshold in days
    """
    if not os.path.exists(cache_dir):
        return
    
    threshold_time = datetime.now() - timedelta(days=days_old)
    removed_count = 0
    
    for root, dirs, files in os.walk(cache_dir):
        for file in files:
            filepath = os.path.join(root, file)
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            if file_time < threshold_time:
                try:
                    os.remove(filepath)
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove {filepath}: {e}")
    
    logger.info(f"Removed {removed_count} old cache files")


def batch_validate_tickers(tickers: List[str]) -> Dict[str, bool]:
    """
    Validate multiple tickers at once.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Dictionary mapping tickers to validation status
    """
    results = {}
    for ticker in tickers:
        formatted = format_ticker(ticker)
        results[ticker] = validate_ticker(formatted)
    
    return results
