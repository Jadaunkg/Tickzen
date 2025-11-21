"""
Finnhub Financial Data Fetcher
Attempts to fetch financial statements from Finnhub API as a fallback
"""
import os
import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def get_finnhub_api_key() -> Optional[str]:
    """Get Finnhub API key from environment"""
    api_key = os.getenv('FINNHUB_API_KEY')
    if api_key:
        return api_key
    
    # Try loading from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return os.getenv('FINNHUB_API_KEY')
    except ImportError:
        pass
    
    return None


def fetch_finnhub_financials(ticker: str, statement_type: str = 'bs') -> Optional[Dict[str, Any]]:
    """
    Fetch financial statements from Finnhub API
    
    Args:
        ticker: Stock ticker symbol
        statement_type: 'bs' (balance sheet), 'ic' (income statement), 'cf' (cash flow)
    
    Returns:
        Financial data dict or None if unavailable
    """
    api_key = get_finnhub_api_key()
    if not api_key:
        logger.warning("Finnhub API key not found")
        return None
    
    try:
        url = f"https://finnhub.io/api/v1/stock/financials-reported"
        params = {
            'symbol': ticker,
            'token': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and 'data' in data and len(data['data']) > 0:
                logger.info(f"Successfully fetched Finnhub financials for {ticker}")
                return data
            else:
                logger.warning(f"No financial data available from Finnhub for {ticker}")
                return None
        else:
            logger.warning(f"Finnhub API returned status {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching Finnhub financials for {ticker}: {str(e)}")
        return None


def extract_balance_sheet_fields(finnhub_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract balance sheet fields from Finnhub financial data
    
    Args:
        finnhub_data: Raw Finnhub financial data
    
    Returns:
        Dict with balance sheet fields
    """
    if not finnhub_data or 'data' not in finnhub_data:
        return {}
    
    try:
        # Get most recent report
        latest_report = finnhub_data['data'][0]
        report = latest_report.get('report', {})
        
        # Try to find balance sheet section
        bs_data = report.get('bs', [])
        
        balance_sheet = {}
        
        # Map Finnhub field names to our field names
        field_mapping = {
            'Goodwill': 'goodwill',
            'IntangibleAssetsNetExcludingGoodwill': 'intangible_assets',
            'OtherIntangibleAssets': 'intangible_assets',
            'IntangibleAssets': 'intangible_assets',
        }
        
        for item in bs_data:
            label = item.get('label', '')
            value = item.get('value')
            
            if label in field_mapping and value:
                balance_sheet[field_mapping[label]] = value
        
        logger.info(f"Extracted {len(balance_sheet)} balance sheet fields from Finnhub")
        return balance_sheet
        
    except Exception as e:
        logger.error(f"Error extracting balance sheet fields: {str(e)}")
        return {}


def fetch_balance_sheet_supplement(ticker: str) -> Dict[str, Any]:
    """
    Try to fetch missing balance sheet fields from Finnhub
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Dict with supplementary balance sheet data
    """
    logger.info(f"Attempting to fetch balance sheet supplement from Finnhub for {ticker}")
    
    financials = fetch_finnhub_financials(ticker, 'bs')
    if not financials:
        return {}
    
    return extract_balance_sheet_fields(financials)
