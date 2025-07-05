# data_collection.py

import time
import logging
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import re
import requests

# Configure logging
# Basic config for direct script run, real app might have this in __init__ or main.
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Use module-specific logger

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
    if not app_root:
        logger.error("app_root not provided to fetch_stock_data. Cannot determine cache directory.")
        raise ValueError("app_root is required for cache path construction.")

    exchange_suffix, exchange_name = get_exchange_info(ticker)
    logger.info(f"Processing {exchange_name} ticker: {ticker}")

    cache_dir = os.path.join(app_root, '..', 'generated_data', 'data_cache')
    os.makedirs(cache_dir, exist_ok=True)

    cache_filename = f"{ticker.replace(':', '_').replace('^', '_')}_stock_data.csv" # Sanitize ticker for filename
    cache_filepath = os.path.join(cache_dir, cache_filename)
    logger.info(f"Checking cache for {ticker} at: {cache_filepath}")

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

    logger.info(f"Cache miss or invalid for {ticker}. Proceeding to download.")

    if start_date and end_date:
        if pd.to_datetime(start_date) > pd.to_datetime(end_date):
            logger.error("start_date must be before end_date") # Log error, don't raise here directly
            return None # Return None if date range is invalid

    period = "10y" if (start_date is None and end_date is None) else None

    logger.info(
        f"Fetching data for ticker: {ticker} "
        f"from {start_date or 'the beginning'} to {end_date or 'today'}"
    )

    # Optimized single API call approach
    try:
        time.sleep(throttle_secs)
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info # Attempt to get info first
        
        # A more robust check for valid ticker info.
        # 'regularMarketPrice' is a common field. 'symbol' should also exist.
        if not info or not info.get('symbol') or info.get('regularMarketPrice') is None :
            logger.error(f"Ticker {ticker} appears to be invalid or delisted. yf.Ticker.info was empty or lacked key fields (e.g. regularMarketPrice). This could mean the ticker symbol is incorrect, the stock is delisted, or not available on Yahoo Finance.")
            return None # Critical: If info suggests invalid ticker, stop.
        
        data = yf.download(
            tickers=ticker,
            start=start_date,
            end=end_date,
            period=period,
            auto_adjust=True,
            progress=False,
            threads=False,
            timeout=timeout
        )
        
        if data.empty:
            logger.warning(f"No data returned by yfinance.download for ticker: {ticker}. This could mean the ticker symbol is incorrect, the stock is delisted, or there's no trading data available for the requested period.")
            return None # If download returns empty, it's a failure for this ticker.
        
        logger.info(f"Successfully downloaded data for {ticker} in single attempt.")
        
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
    data.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
    # Fill NaN in Volume with 0 after attempting numeric conversion, as Volume can sometimes be 0.
    if 'Volume' in data.columns:
        data['Volume'].fillna(0, inplace=True)


    if data.empty:
        logger.warning(f"Data for {ticker} became empty after cleaning and type conversion.")
        return None

    try:
        data_to_save = data[required]
        data_to_save.to_csv(cache_filepath, index=False)
        logger.info(f"Saved downloaded data for {ticker} to cache: {cache_filename}")
    except Exception as e:
        logger.error(f"Failed to save data for {ticker} to cache file {cache_filename}: {e}")

    logger.info(f"Successfully fetched and processed {len(data)} rows for '{ticker}'.")
    return data[required]


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