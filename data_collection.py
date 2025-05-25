# data_collection.py (MODIFIED with improved caching path and logging)

import time
import logging
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    return None, 'US Stock Exchange'  # Default to US exchange if no suffix found

def fetch_stock_data(
    ticker,
    app_root,
    start_date=None,
    end_date=None,
    max_retries=3,
    pause_secs=2,
    throttle_secs=0.3,
    timeout=30  
):
    """
    Fetch and process historical stock data for a single ticker,
    checking local cache first. Uses app_root for consistent cache path.
    Handles all stock exchanges supported by yfinance.
    """
    # Construct cache path using app_root
    if not app_root:
        logger.error("app_root not provided to fetch_stock_data. Cannot determine cache directory.")
        raise ValueError("app_root is required for cache path construction.")

    # Get exchange information
    exchange_suffix, exchange_name = get_exchange_info(ticker)
    logger.info(f"Processing {exchange_name} ticker: {ticker}")

    cache_dir = os.path.join(app_root, 'data_cache')
    os.makedirs(cache_dir, exist_ok=True)

    cache_filename = f"{ticker}_stock_data.csv"
    cache_filepath = os.path.join(cache_dir, cache_filename)
    logger.info(f"Checking cache for {ticker} at: {cache_filepath}")

    # --- Check Cache First ---
    cache_exists = os.path.exists(cache_filepath)
    logger.info(f"Cache file exists: {cache_exists}")

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
            else:
                logger.info(f"Successfully loaded {len(data)} rows for '{ticker}' from cache.")
                return data
        except Exception as e:
            logger.warning(f"Failed to load or validate cached file {cache_filename}: {e}. Re-downloading.")

    # --- Download Logic (If Cache Miss or Invalid) ---
    logger.info(f"Cache miss or invalid for {ticker}. Proceeding to download.")

    if start_date and end_date:
        if pd.to_datetime(start_date) > pd.to_datetime(end_date):
            raise ValueError("start_date must be before end_date")

    period = "10y" if (start_date is None and end_date is None) else None

    logger.info(
        f"Fetching data for ticker: {ticker} "
        f"from {start_date or 'the beginning'} to {end_date or 'today'}"
    )

    attempt = 0
    data = None
    while attempt < max_retries:
        try:
            time.sleep(throttle_secs)
            # Verify the ticker exists before downloading
            try:
                yf_ticker = yf.Ticker(ticker)
                info = yf_ticker.info
                if not info or 'regularMarketPrice' not in info:
                    logger.warning(f"Ticker {ticker} appears to be invalid or has no data.")
                    return None
            except Exception as e:
                logger.error(f"Error verifying ticker {ticker}: {e}")
                return None

            data = yf.download(
                tickers=ticker,
                start=start_date,
                end=end_date,
                period=period,
                auto_adjust=True,
                progress=False,
                threads=False
            )
            
            if data.empty:
                logger.warning(f"No data found for ticker: {ticker} via yfinance.")
                data = None
                break
            break
        except Exception as e:
            msg = str(e).lower()
            if "rate limit" in msg or "too many requests" in msg:
                attempt += 1
                wait = pause_secs * attempt
                logger.warning(f"Rate limit on '{ticker}', retry {attempt}/{max_retries} in {wait}s: {e}")
                time.sleep(wait)
                continue
            logger.error(f"Error fetching '{ticker}': {e}")
            raise
    else:
        logger.error(f"Failed to download '{ticker}' after {max_retries} retries.")
        return None

    if data is None or data.empty:
         logger.error(f"Data for {ticker} could not be retrieved.")
         return None

    # --- Process Downloaded Data ---
    data = data.reset_index()
    logger.info(f"Fetched columns: {list(data.columns)}")

    if isinstance(data.columns[0], tuple):
        data.columns = [col[0] for col in data.columns]
    else:
        data.columns = [col.split('_')[0] if isinstance(col, str) and '_' in col else col for col in data.columns]

    date_cols = [c for c in data.columns if 'date' in c.lower()]
    if date_cols: data = data.rename(columns={date_cols[0]: 'Date'})

    try:
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce', utc=True).dt.tz_localize(None)
    except Exception as e:
        logger.error(f"Error processing dates after download: {e}")
        return None

    invalid_dates = data['Date'].isna().sum()
    if invalid_dates > 0:
        logger.warning(f"Found {invalid_dates} invalid dates post-download; dropping them.")
    data = data.dropna(subset=['Date']).sort_values('Date')

    required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required if col not in data.columns]
    if missing:
        logger.error(f"Downloaded data missing required columns: {missing}. Available: {list(data.columns)}")
        return None

    data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')

    # --- Save to Cache ---
    try:
        data_to_save = data[required]
        data_to_save.to_csv(cache_filepath, index=False)
        logger.info(f"Saved downloaded data for {ticker} to cache: {cache_filename}")
    except Exception as e:
        logger.error(f"Failed to save data for {ticker} to cache file {cache_filename}: {e}")

    logger.info(f"Successfully fetched and processed {len(data)} rows for '{ticker}'.")
    return data[required]


# Example usage (if run directly, needs a placeholder app_root)
if __name__ == "__main__":
    try:
        # Test with different exchanges
        test_tickers = [
            "TSLA",           # US
            "ADANIPOWER.NS",  # India NSE
            "RELIANCE.BO",    # India BSE
            "HSBA.L",         # London
            "BMW.DE",         # XETRA
            "AIR.PA",         # Paris
            "RY.TO",          # Toronto
            "DBS.SI",         # Singapore
            "BHP.AX",         # Australia
            "FPH.NZ",         # New Zealand
            "0700.HK",        # Hong Kong
            "005930.KS",      # Korea
            "7203.T",         # Tokyo
            "600519.SS",      # Shanghai
            "000001.SZ"       # Shenzhen
        ]
        
        current_app_root = os.path.dirname(os.path.abspath(__file__))
        
        for ticker in test_tickers:
            logger.info(f"\nTesting ticker: {ticker}")
            df = fetch_stock_data(ticker, app_root=current_app_root)
            if df is not None:
                logger.info(f"Successfully fetched {len(df)} rows for {ticker}")
                print(df.head())
            else:
                logger.error(f"Failed to fetch data for {ticker}")
                
    except Exception as e:
        logger.error(f"An error occurred: {e}")