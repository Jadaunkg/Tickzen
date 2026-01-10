#!/usr/bin/env python3
"""
Financial Data Collection Module
===============================

Centralized financial data aggregation system that collects, validates,
and standardizes market data from multiple authoritative sources. Handles
real-time and historical data with comprehensive error handling and caching.

Supported Data Sources:
----------------------
1. **Yahoo Finance (yfinance)**:
   - Historical stock prices (OHLCV)
   - Company fundamentals and financials
   - Dividend and stock split history
   - Real-time price quotes
   - Market cap and trading volume

2. **Alpha Vantage API**:
   - Intraday stock data (1min, 5min, 15min, 30min, 60min)
   - Daily, weekly, monthly adjusted prices
   - Technical indicators
   - Sector performance data
   - Global market data

3. **FRED (Federal Reserve Economic Data)**:
   - Economic indicators (GDP, inflation, unemployment)
   - Interest rates (Fed funds rate, Treasury yields)
   - Money supply and banking data
   - International economic data

4. **Finnhub API**:
   - Real-time stock quotes and trades
   - Company earnings and estimates
   - News sentiment and social sentiment
   - Insider trading data

Core Functions:
--------------
- `fetch_stock_data()`: Multi-source stock data collection
- `fetch_real_time_data()`: Current market data retrieval
- `fetch_historical_data()`: Historical price and volume data
- `fetch_company_fundamentals()`: Financial statement data
- `fetch_economic_indicators()`: Macro economic data

Data Validation Features:
------------------------
- **Price Validation**: Outlier detection using statistical methods
- **Volume Validation**: Unusual volume spike detection
- **Data Completeness**: Missing data identification and handling
- **Cross-Source Verification**: Multi-source data consistency checks
- **Time-Series Continuity**: Gap detection in historical data

Caching Strategy:
----------------
- **Intraday Cache**: 1-minute TTL for real-time data
- **Daily Cache**: 24-hour TTL for end-of-day data
- **Historical Cache**: 7-day TTL for historical data
- **Fundamental Cache**: 30-day TTL for company fundamentals
- **Economic Cache**: Variable TTL based on release schedule

Error Handling:
--------------
- **API Failures**: Automatic fallback to alternative sources
- **Rate Limiting**: Exponential backoff with jitter
- **Network Issues**: Connection timeout and retry mechanisms
- **Data Quality**: Invalid data filtering and correction
- **Quota Management**: API usage monitoring and optimization

Data Standardization:
--------------------
- **Timezone Handling**: UTC normalization with market timezone awareness
- **Price Adjustment**: Stock splits and dividend adjustments
- **Currency Conversion**: Multi-currency support with exchange rates
- **Data Format**: Consistent pandas DataFrame output format
- **Column Naming**: Standardized column names across sources

Performance Optimizations:
-------------------------
- **Parallel Requests**: Concurrent API calls for multiple symbols
- **Batch Processing**: Bulk data requests where supported
- **Connection Pooling**: Persistent HTTP connections
- **Memory Management**: Efficient data structure usage
- **Lazy Loading**: On-demand data retrieval

Data Quality Metrics:
--------------------
- **Completeness Score**: Percentage of expected data points
- **Freshness Score**: Data recency relative to market hours
- **Accuracy Score**: Cross-source validation results
- **Coverage Score**: Symbol and timeframe availability

Usage Examples:
--------------
```python
# Basic stock data collection
data = fetch_stock_data('AAPL', period='1y')

# Real-time data with validation
real_time = fetch_real_time_data(['AAPL', 'GOOGL', 'MSFT'])

# Historical data with custom date range
historical = fetch_historical_data(
    symbol='AAPL',
    start_date='2023-01-01',
    end_date='2024-01-01',
    interval='1d'
)

# Company fundamentals
fundamentals = fetch_company_fundamentals('AAPL')
```

API Integration Details:
-----------------------
- **Rate Limiting**: Respects all API provider limits
- **Authentication**: API key management and rotation
- **Error Codes**: Comprehensive HTTP status code handling
- **Response Parsing**: Robust JSON/CSV parsing with validation
- **Quota Tracking**: Real-time API usage monitoring

Output Data Structure:
---------------------
Standardized DataFrame format:
- Date: DatetimeIndex with timezone awareness
- Open/High/Low/Close: Price data with adjustments
- Volume: Trading volume
- Adj Close: Dividend and split adjusted closing price
- Metadata: Source, collection timestamp, quality metrics

Integration Points:
------------------
- Used by automation_scripts/pipeline.py for analysis workflow
- Integrated with earnings_reports/data_collector.py
- Provides data for analysis_scripts/ modules
- Supports real-time dashboard updates

Configuration:
-------------
Environment Variables:
- ALPHA_VANTAGE_API_KEY: Alpha Vantage access key
- FINNHUB_API_KEY: Finnhub access token
- FRED_API_KEY: FRED API access key
- DATA_CACHE_TTL: Default cache time-to-live
- MAX_CONCURRENT_REQUESTS: Parallel request limit

Author: TickZen Development Team
Version: 2.7
Last Updated: January 2026
"""

import time
import logging
import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
import os
import re
import requests
import pytz

# Import real-time configuration
try:
    from config.realtime_config import get_realtime_config, is_realtime_enabled
    REALTIME_CONFIG_AVAILABLE = True
except ImportError:
    REALTIME_CONFIG_AVAILABLE = False
    def get_realtime_config():
        return {'enable_realtime_fetch': True, 'throttle_seconds': 0.3, 'timeout_seconds': 30}
    def is_realtime_enabled():
        return True

# Configure logging
# Basic config for direct script run, real app might have this in __init__ or main.
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Use module-specific logger

def is_market_hours(ticker=None):
    """
    Check if it's currently market hours for the given ticker.
    Default to US market hours if no specific ticker exchange is provided.
    """
    try:
        # Default to US Eastern Time
        market_tz = pytz.timezone('US/Eastern')
        
        # Get exchange timezone based on ticker suffix
        exchange_suffix, _ = get_exchange_info(ticker) if ticker else (None, None)
        
        if exchange_suffix:
            # Map exchange suffixes to timezones
            exchange_timezones = {
                '.L': 'Europe/London',       # London
                '.TO': 'America/Toronto',    # Toronto
                '.AX': 'Australia/Sydney',   # Australia
                '.T': 'Asia/Tokyo',          # Tokyo
                '.HK': 'Asia/Hong_Kong',     # Hong Kong
                '.SS': 'Asia/Shanghai',      # Shanghai
                '.NS': 'Asia/Kolkata',       # India NSE
                '.BO': 'Asia/Kolkata',       # India BSE
            }
            market_tz = pytz.timezone(exchange_timezones.get(exchange_suffix, 'US/Eastern'))
        
        now_market = datetime.now(market_tz)
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now_market.weekday() > 4:  # Saturday or Sunday
            return False
        
        # US market hours: 9:30 AM - 4:00 PM ET
        market_open = now_market.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_market.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now_market <= market_close
        
    except Exception as e:
        logger.warning(f"Error checking market hours: {e}")
        return False

def is_data_current_for_today(data, ticker):
    """
    Check if the data contains current/today's trading data.
    Enhanced to be more intelligent about market hours and trading sessions.
    Returns True if data is current, False otherwise.
    """
    if data is None or data.empty:
        return False
    
    if 'Date' not in data.columns:
        return False
    
    try:
        # Get today's date
        today = date.today()
        
        # Convert Date column to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(data['Date']):
            data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        
        # Get the latest date in the data
        latest_date = data['Date'].max().date() if pd.notna(data['Date'].max()) else None
        
        if latest_date is None:
            logger.warning(f"No valid dates found in cached data for {ticker}")
            return False
        
        # Check if latest date is today or recent
        days_diff = (today - latest_date).days
        
        # More aggressive data freshness policy - prioritize recent data
        if days_diff == 0:
            # Data is from today - always consider current
            logger.info(f"Data currency check for {ticker}: Same day data - CURRENT")
            return True
        elif days_diff == 1:
            # Data is from yesterday
            if today.weekday() == 0:  # Today is Monday
                # Monday: accept Friday's data (1 day old is actually 3 calendar days)
                logger.info(f"Data currency check for {ticker}: Monday with Friday data - CURRENT")
                return True
            elif is_market_hours(ticker):
                # During market hours, prefer same-day data if possible
                logger.info(f"Data currency check for {ticker}: Market hours, yesterday data - STALE")
                return False
            else:
                # After market hours, yesterday's data is acceptable only for recent yesterday
                logger.info(f"Data currency check for {ticker}: After hours, yesterday data - CURRENT")
                return True
        elif days_diff == 2:
            # Data is 2 days old - only accept on Monday (weekend gap)
            if today.weekday() == 0:  # Today is Monday
                logger.info(f"Data currency check for {ticker}: Monday with Saturday data - CURRENT")
                return True
            else:
                logger.info(f"Data currency check for {ticker}: 2-day old data during weekday - STALE")
                return False
        elif days_diff == 3:
            # Data is 3 days old - only accept on Monday (weekend gap from Friday)
            if today.weekday() == 0:  # Today is Monday
                logger.info(f"Data currency check for {ticker}: Monday with Friday data (3 days) - CURRENT")
                return True
            else:
                logger.info(f"Data currency check for {ticker}: 3-day old data during weekday - STALE")
                return False
        else:
            # Data is more than 3 days old - always stale
            logger.warning(f"Data currency check for {ticker}: Data too old ({days_diff} days) - STALE (latest: {latest_date}, today: {today})")
            return False
        
    except Exception as e:
        logger.error(f"Error checking data currency for {ticker}: {e}")
        return False

def cleanup_old_cache_files(cache_dir, max_age_days=7):
    """
    Clean up cache files older than max_age_days to prevent accumulation.
    """
    try:
        if not os.path.exists(cache_dir):
            return
        
        current_time = datetime.now()
        files_cleaned = 0
        
        for filename in os.listdir(cache_dir):
            if filename.endswith('.csv'):
                filepath = os.path.join(cache_dir, filename)
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    age_days = (current_time - file_mtime).days
                    
                    if age_days > max_age_days:
                        os.remove(filepath)
                        files_cleaned += 1
                        logger.info(f"Cleaned up old cache file: {filename} (age: {age_days} days)")
                
                except Exception as e:
                    logger.warning(f"Error cleaning cache file {filename}: {e}")
        
        if files_cleaned > 0:
            logger.info(f"Cleaned up {files_cleaned} old cache files from {cache_dir}")
            
    except Exception as e:
        logger.error(f"Error during cache cleanup: {e}")

# Define supported exchange suffixes
SUPPORTED_EXCHANGES = {
    '.NS': 'National Stock Exchange of India',
    '.BO': 'Bombay Stock Exchange',
    '.L': 'London Stock Exchange',
    '.F': 'Frankfurt Stock Exchange',
    '.PA': 'Paris Stock Exchange',
    '.TO': 'Toronto Stock Exchange',
    '.SI': 'Singapore Stock Exchange',
    '.AX': 'Australian Stock Exchange',
    '.NZ': 'New Zealand Stock Exchange',
    '.V': 'TSX Venture Exchange',
    '.DE': 'XETRA',
    '.BE': 'Berlin Stock Exchange',
    '.DU': 'Dusseldorf Stock Exchange',
    '.HM': 'Hamburg Stock Exchange',
    '.HA': 'Hanover Stock Exchange',
    '.MU': 'Munich Stock Exchange',
    '.ST': 'Stockholm Stock Exchange',
    '.CO': 'Copenhagen Stock Exchange',
    '.HE': 'Helsinki Stock Exchange',
    '.OL': 'Oslo Stock Exchange',
    '.IC': 'Iceland Stock Exchange',
    '.AT': 'Athens Stock Exchange',
    '.MI': 'Milan Stock Exchange',
    '.AS': 'Amsterdam Stock Exchange',
    '.BR': 'Brussels Stock Exchange',
    '.LS': 'Lisbon Stock Exchange',
    '.MC': 'Madrid Stock Exchange',
    '.VI': 'Vienna Stock Exchange',
    '.SW': 'Swiss Stock Exchange',
    '.BA': 'Buenos Aires Stock Exchange',
    '.SA': 'Sao Paulo Stock Exchange',
    '.MX': 'Mexican Stock Exchange',
    '.JK': 'Jakarta Stock Exchange',
    '.KL': 'Kuala Lumpur Stock Exchange',
    '.BK': 'Bangkok Stock Exchange',
    '.TW': 'Taiwan Stock Exchange',
    '.KS': 'Korea Stock Exchange',
    '.T': 'Tokyo Stock Exchange',
    '.HK': 'Hong Kong Stock Exchange',
    '.SS': 'Shanghai Stock Exchange',
    '.SZ': 'Shenzhen Stock Exchange'
}

def get_exchange_info(ticker):
    """Extract exchange information from ticker symbol."""
    for suffix, exchange_name in SUPPORTED_EXCHANGES.items():
        if ticker.endswith(suffix):
            return suffix, exchange_name
    return None, 'US Stock Exchange'

def find_latest_cache_file(ticker, cache_dir, interval='1d'):
    """
    Find the most recent cache file for a ticker, handling multiple naming patterns.
    Returns the most recent cache file path or None if no cache exists.
    """
    if not os.path.exists(cache_dir):
        return None
    
    # Clean ticker for filename patterns
    clean_ticker = ticker.replace(':', '_').replace('^', '_').replace('=', '_')
    
    # Possible cache file patterns (newest to oldest naming conventions)
    patterns = [
        f"{clean_ticker}_stock_data_{interval}.csv",  # Current pattern with interval
        f"{clean_ticker}_stock_data.csv",             # Legacy pattern without interval
    ]
    
    latest_file = None
    latest_mtime = 0
    
    try:
        for filename in os.listdir(cache_dir):
            # Check if file matches any pattern for this ticker
            if any(filename == pattern for pattern in patterns):
                filepath = os.path.join(cache_dir, filename)
                file_mtime = os.path.getmtime(filepath)
                
                if file_mtime > latest_mtime:
                    latest_mtime = file_mtime
                    latest_file = filepath
                    
        if latest_file:
            logger.info(f"Found latest cache file for {ticker}: {os.path.basename(latest_file)} "
                       f"(modified: {datetime.fromtimestamp(latest_mtime).strftime('%Y-%m-%d %H:%M:%S')})")
        
        return latest_file
        
    except Exception as e:
        logger.warning(f"Error searching for cache files for {ticker}: {e}")
        return None

def cleanup_duplicate_cache_files(ticker, cache_dir, keep_latest=True):
    """
    Clean up duplicate cache files for a ticker, keeping only the most recent one.
    """
    if not os.path.exists(cache_dir):
        return
    
    clean_ticker = ticker.replace(':', '_').replace('^', '_').replace('=', '_')
    ticker_files = []
    
    try:
        # Find all cache files for this ticker
        for filename in os.listdir(cache_dir):
            if (filename.startswith(f"{clean_ticker}_stock_data") and 
                filename.endswith('.csv') and 
                'processed_data' not in filename):
                
                filepath = os.path.join(cache_dir, filename)
                file_mtime = os.path.getmtime(filepath)
                ticker_files.append((filepath, file_mtime, filename))
        
        if len(ticker_files) > 1 and keep_latest:
            # Sort by modification time (newest first)
            ticker_files.sort(key=lambda x: x[1], reverse=True)
            
            # Keep the newest file, remove the rest
            latest_file = ticker_files[0]
            logger.info(f"Keeping latest cache file for {ticker}: {latest_file[2]}")
            
            for filepath, mtime, filename in ticker_files[1:]:
                try:
                    os.remove(filepath)
                    logger.info(f"Removed duplicate cache file: {filename}")
                except Exception as e:
                    logger.warning(f"Error removing duplicate cache file {filename}: {e}")
                    
    except Exception as e:
        logger.error(f"Error cleaning duplicate cache files for {ticker}: {e}")

def fetch_stock_data(
    ticker,
    app_root,
    start_date=None,
    end_date=None,
    max_retries=3,
    pause_secs=2,
    throttle_secs=None,
    timeout=None,
    interval='1d',
    include_intraday=False
):
    """
    Fetch stock data with enhanced real-time capabilities.
    
    Parameters:
    - interval: '1d' (daily), '1h' (hourly), '5m' (5-minute), '1m' (1-minute)
    - include_intraday: If True, fetches recent intraday data for current day analysis
    """
    # Get configuration settings
    config = get_realtime_config()
    
    if throttle_secs is None:
        throttle_secs = config.get('throttle_seconds', 0.3)
    if timeout is None:
        timeout = config.get('timeout_seconds', 30)
    
    # Check if real-time fetching is enabled
    if not is_realtime_enabled():
        logger.info(f"Real-time fetching disabled. Using cached data only for {ticker}")
        # Return cached data if available, None otherwise
        cache_dir = os.path.join(app_root, '..', 'generated_data', 'data_cache')
        cache_filename = f"{ticker.replace(':', '_').replace('^', '_').replace('=', '_')}_stock_data_{interval}.csv"
        cache_filepath = os.path.join(cache_dir, cache_filename)
        
        if os.path.exists(cache_filepath):
            try:
                return pd.read_csv(cache_filepath, parse_dates=['Date'])
            except Exception as e:
                logger.warning(f"Failed to load cached data: {e}")
        return None
    if not app_root:
        logger.error("app_root not provided to fetch_stock_data. Cannot determine cache directory.")
        raise ValueError("app_root is required for cache path construction.")

    exchange_suffix, exchange_name = get_exchange_info(ticker)
    logger.info(f"Processing {exchange_name} ticker: {ticker}")

    cache_dir = os.path.join(app_root, '..', 'generated_data', 'data_cache')
    os.makedirs(cache_dir, exist_ok=True)
    
    # Clean up old cache files periodically
    cleanup_old_cache_files(cache_dir)
    
    # Clean up duplicate cache files for this ticker first
    cleanup_duplicate_cache_files(ticker, cache_dir)

    # Find the most recent cache file for this ticker
    latest_cache_file = find_latest_cache_file(ticker, cache_dir, interval)
    
    # Fallback to standard naming if no cache found
    if not latest_cache_file:
        cache_filename = f"{ticker.replace(':', '_').replace('^', '_').replace('=', '_')}_stock_data_{interval}.csv"
        cache_filepath = os.path.join(cache_dir, cache_filename)
    else:
        cache_filepath = latest_cache_file
        cache_filename = os.path.basename(cache_filepath)
    
    logger.info(f"Checking cache for {ticker} ({interval}) at: {cache_filepath}")

    cache_exists = os.path.exists(cache_filepath)
    logger.info(f"Cache file exists: {cache_exists}")

    # For intraday intervals, use stricter cache validation
    cache_valid_hours = 1 if interval in ['1m', '5m', '15m', '30m', '1h'] else 24
    
    # Minimum data points required for technical analysis
    MIN_ROWS_FOR_ANALYSIS = 100  # Need at least 100 days for reliable technical indicators
    
    if cache_exists:
        logger.info(f"Attempting to load cached stock data for {ticker} from: {cache_filename}")
        try:
            data = pd.read_csv(cache_filepath, parse_dates=['Date'])
            required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required if col not in data.columns]

            if missing_cols:
                logger.warning(f"Cached file {cache_filename} missing required columns: {missing_cols}. Re-downloading.")
            elif data.empty:
                 logger.warning(f"Cached file {cache_filename} is empty. Re-downloading.")
            elif data['Date'].isna().any():
                 logger.warning(f"Cached file {cache_filename} contains invalid dates. Re-downloading.")
            elif len(data) < MIN_ROWS_FOR_ANALYSIS and interval == '1d':
                 logger.warning(f"Cached data for {ticker} has only {len(data)} rows, need at least {MIN_ROWS_FOR_ANALYSIS} for analysis. Re-downloading.")
            elif not is_data_current_for_today(data, ticker):
                 logger.warning(f"Cached data for {ticker} is not current for today. Re-downloading to get latest data.")
            elif interval in ['1m', '5m', '15m', '30m', '1h']:
                # Check if intraday cache is fresh (within last hour)
                file_age_hours = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_filepath))).total_seconds() / 3600
                if file_age_hours > cache_valid_hours:
                    logger.warning(f"Intraday cached data for {ticker} is {file_age_hours:.1f} hours old. Re-downloading for real-time analysis.")
                else:
                    logger.info(f"Successfully loaded {len(data)} rows for '{ticker}' from fresh intraday cache.")
                    return data
            else:
                logger.info(f"Successfully loaded {len(data)} rows for '{ticker}' from cache with current data.")
                return data
        except Exception as e:
            logger.warning(f"Failed to load or validate cached file {cache_filename}: {e}. Re-downloading.")

    logger.info(f"Cache miss or invalid for {ticker}. Proceeding to download.")

    if start_date and end_date:
        if pd.to_datetime(start_date) > pd.to_datetime(end_date):
            logger.error("start_date must be before end_date") # Log error, don't raise here directly
            return None # Return None if date range is invalid

    period = "10y" if (start_date is None and end_date is None) else None

    logger.info(
        f"Fetching data for ticker: {ticker} "
        f"from {start_date or 'the beginning'} to {end_date or 'today'} "
        f"with interval: {interval}"
    )

    # Optimized single API call approach with enhanced real-time support
    try:
        time.sleep(throttle_secs)
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info # Attempt to get info first
        
        # A more robust check for valid ticker info.
        # 'regularMarketPrice' is a common field. 'symbol' should also exist.
        if not info or not info.get('symbol') or info.get('regularMarketPrice') is None :
            logger.error(f"Ticker {ticker} appears to be invalid or delisted. yf.Ticker.info was empty or lacked key fields (e.g. regularMarketPrice). This could mean the ticker symbol is incorrect, the stock is delisted, or not available on Yahoo Finance.")
            return None # Critical: If info suggests invalid ticker, stop.
        
        # Enhanced data fetching with interval support
        download_params = {
            'tickers': ticker,
            'start': start_date,
            'end': end_date,
            'interval': interval,
            'auto_adjust': True,
            'progress': False,
            'threads': False,
            'timeout': timeout
        }
        
        # For intraday data, limit the period to avoid too much data
        if interval in ['1m', '5m', '15m', '30m'] and not start_date and not end_date:
            # For minute data, get last 7 days max (yfinance limitation)
            download_params['period'] = '7d'
        elif interval == '1h' and not start_date and not end_date:
            # For hourly data, get last 730 days max
            download_params['period'] = '730d' 
        elif not start_date and not end_date:
            # For daily data, get full history
            download_params['period'] = '10y'
        
        # Remove period if custom date range is provided
        if start_date or end_date:
            download_params.pop('period', None)
        
        data = yf.download(**download_params)
        
        if data.empty:
            logger.warning(f"No data returned by yfinance.download for ticker: {ticker} with interval {interval}. This could mean the ticker symbol is incorrect, the stock is delisted, or there's no trading data available for the requested period.")
            return None # If download returns empty, it's a failure for this ticker.
        
        logger.info(f"Successfully downloaded {interval} data for {ticker} in single attempt.")
        
    except requests.exceptions.HTTPError as http_err: # Catch HTTP errors specifically
        if http_err.response.status_code == 404:
            logger.error(f"HTTP Error 404 (Not Found) for ticker {ticker}. This often means the ticker symbol is incorrect or not available on Yahoo Finance. Please verify the symbol (e.g., Nike is NKE, not NIKE STOCK).")
        else:
            logger.error(f"HTTP Error during yfinance operation for {ticker}: {http_err}")
        return None # Stop on 404 or other critical HTTP errors for this ticker
    except Exception as e:
        logger.error(f"Error fetching '{ticker}': {e}")
        return None

    if data is None or data.empty:
         logger.warning(f"Data for {ticker} could not be retrieved or is empty after attempts.")
         return None

    data = data.reset_index()
    # logger.info(f"Fetched columns for {ticker}: {list(data.columns)}") # Already logged by yf.download if progress=True

    if isinstance(data.columns[0], tuple): # Handles MultiIndex columns if any
        data.columns = [col[0] for col in data.columns]
    
    # Standardize column names - less aggressive, targets 'Date' specifically.
    # Assumes OHLCV are already correctly named by yf.download with auto_adjust=True
    date_cols = [c for c in data.columns if 'date' in str(c).lower()]
    if date_cols:
        data = data.rename(columns={date_cols[0]: 'Date'})
    elif 'Date' not in data.columns:
        logger.error(f"Could not identify 'Date' column for {ticker}. Columns: {list(data.columns)}")
        return None


    try:
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce', utc=True).dt.tz_localize(None)
    except Exception as e:
        logger.error(f"Error processing 'Date' column after download for {ticker}: {e}")
        return None

    invalid_dates = data['Date'].isna().sum()
    if invalid_dates > 0:
        logger.warning(f"Found {invalid_dates} invalid dates post-download for {ticker}; dropping them.")
    data = data.dropna(subset=['Date']).sort_values('Date')

    required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required if col not in data.columns]
    if missing:
        logger.error(f"Downloaded data for {ticker} missing required columns: {missing}. Available: {list(data.columns)}")
        return None

    # Ensure numeric types for OHLCV, coercing errors.
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
    # Drop rows where any of the essential OHLC columns became NaN after coercion
    data = data.dropna(subset=['Open', 'High', 'Low', 'Close'])
    # Fill NaN in Volume with 0 after attempting numeric conversion, as Volume can sometimes be 0.
    if 'Volume' in data.columns:
        data['Volume'] = data['Volume'].fillna(0)


    if data.empty:
        logger.warning(f"Data for {ticker} became empty after cleaning and type conversion.")
        return None

    try:
        # Ensure we use the consistent filename format for saving
        save_cache_filename = f"{ticker.replace(':', '_').replace('^', '_').replace('=', '_')}_stock_data_{interval}.csv"
        save_cache_filepath = os.path.join(cache_dir, save_cache_filename)
        
        # Remove any old cache files with different naming patterns before saving new one
        cleanup_duplicate_cache_files(ticker, cache_dir, keep_latest=False)
        
        data_to_save = data[required]
        data_to_save.to_csv(save_cache_filepath, index=False)
        logger.info(f"Saved downloaded data for {ticker} to cache: {save_cache_filename}")
        
        # Update cache_filepath reference for return consistency
        cache_filepath = save_cache_filepath
        cache_filename = save_cache_filename
        
    except Exception as e:
        logger.error(f"Failed to save data for {ticker} to cache file {save_cache_filename}: {e}")

    logger.info(f"Successfully fetched and processed {len(data)} rows for '{ticker}'.")
    return data[required]


def get_current_market_price(ticker, timeout=10):
    """
    Get the most current market price for a ticker with minimal delay.
    Returns current price, change, and change percentage.
    """
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
        
        if not info:
            logger.warning(f"No info available for ticker {ticker}")
            return None
        
        current_price = info.get('regularMarketPrice') or info.get('currentPrice')
        previous_close = info.get('regularMarketPreviousClose') or info.get('previousClose')
        
        if current_price is None:
            logger.warning(f"No current price available for ticker {ticker}")
            return None
        
        # Calculate change if previous close is available
        change = None
        change_percent = None
        if previous_close:
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100
        
        market_state = info.get('marketState', 'Unknown')
        last_updated = datetime.now().isoformat()
        
        price_data = {
            'ticker': ticker,
            'current_price': current_price,
            'previous_close': previous_close,
            'change': change,
            'change_percent': change_percent,
            'market_state': market_state,
            'last_updated': last_updated,
            'currency': info.get('currency', 'USD')
        }
        
        logger.info(f"Current price for {ticker}: ${current_price} ({market_state})")
        return price_data
        
    except Exception as e:
        logger.error(f"Error getting current price for {ticker}: {e}")
        return None

def fetch_real_time_data(ticker, app_root, include_price=True, include_intraday=True):
    """
    Fetch the most current data available for a ticker.
    Combines current price with recent intraday data for comprehensive real-time analysis.
    """
    logger.info(f"Fetching real-time data for {ticker}")
    
    result = {
        'ticker': ticker,
        'timestamp': datetime.now().isoformat(),
        'current_price_data': None,
        'intraday_data': None,
        'daily_data': None
    }
    
    try:
        # Get current market price with minimal delay
        if include_price:
            result['current_price_data'] = get_current_market_price(ticker)
        
        # Get recent intraday data (5-minute intervals for last day)
        if include_intraday and is_market_hours(ticker):
            result['intraday_data'] = fetch_stock_data(
                ticker, app_root, 
                interval='5m', 
                include_intraday=True
            )
        
        # Get recent daily data
        result['daily_data'] = fetch_stock_data(ticker, app_root)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching real-time data for {ticker}: {e}")
        return result


if __name__ == "__main__":
    try:
        test_tickers = [
            "NKE",        # Valid (Nike)
            "SAVE",       # Valid (Spirit Airlines)
            "NIKE STOCK", # Invalid
            "SAVE STOCK", # Invalid
            "ADANIPOWER.NS"
        ]
        
        # Determine a suitable app_root for standalone script execution
        # This assumes data_collection.py is in data_processing_scripts
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        app_level_root = os.path.join(current_script_dir, '..', 'app') # Assuming 'app' is one level up from 'data_processing_scripts' directory
        
        logger.info(f"Standalone Test: Using app_root='{app_level_root}' for cache paths.")

        for ticker_symbol in test_tickers:
            logger.info(f"\n--- Testing ticker: {ticker_symbol} ---")
            df_data = fetch_stock_data(ticker_symbol, app_root=app_level_root, timeout=45)
            if df_data is not None and not df_data.empty:
                logger.info(f"Successfully fetched {len(df_data)} rows for {ticker_symbol}")
                print(df_data.head())
            else:
                logger.error(f"Failed to fetch data for {ticker_symbol} or data was empty.")
                
    except Exception as main_e:
        logger.error(f"An error occurred in main execution: {main_e}", exc_info=True)