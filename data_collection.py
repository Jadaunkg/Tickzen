# data_collection.py (MODIFIED with improved caching path and logging)

import time
import logging
import yfinance as yf
import pandas as pd
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Removed CACHE_DIR definition here, will be constructed using app_root

def fetch_stock_data(
    ticker,
    app_root, # Added app_root argument
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
    """
    # Construct cache path using app_root
    if not app_root:
        logger.error("app_root not provided to fetch_stock_data. Cannot determine cache directory.")
        # Fallback or raise error - let's raise for clarity
        raise ValueError("app_root is required for cache path construction.")

    cache_dir = os.path.join(app_root, 'data_cache')
    os.makedirs(cache_dir, exist_ok=True) # Ensure cache directory exists

    cache_filename = f"{ticker}_stock_data.csv"
    cache_filepath = os.path.join(cache_dir, cache_filename)
    logger.info(f"Checking cache for {ticker} at: {cache_filepath}") # Log the exact path

    # --- Check Cache First ---
    cache_exists = os.path.exists(cache_filepath)
    logger.info(f"Cache file exists: {cache_exists}") # Log if file exists

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
            # Fall through to download

    # --- Download Logic (If Cache Miss or Invalid) ---
    logger.info(f"Cache miss or invalid for {ticker}. Proceeding to download.")
    # (Rest of the download and processing logic remains the same as previous version)
    # ... (yf.download call, processing, validation) ...

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
            data = yf.download(
                tickers=ticker, start=start_date, end=end_date, period=period,
                auto_adjust=True, progress=False, threads=False
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
                time.sleep(wait); continue
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
        logger.error(f"Error processing dates after download: {e}"); return None

    invalid_dates = data['Date'].isna().sum()
    if invalid_dates > 0: logger.warning(f"Found {invalid_dates} invalid dates post-download; dropping them.")
    data = data.dropna(subset=['Date']).sort_values('Date')

    required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required if col not in data.columns]
    if missing:
        logger.error(f"Downloaded data missing required columns: {missing}. Available: {list(data.columns)}"); return None

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
        ticker_symbol = "TSLA"
        # In standalone execution, define APP_ROOT relative to this script
        current_app_root = os.path.dirname(os.path.abspath(__file__))
        df = fetch_stock_data(ticker_symbol, app_root=current_app_root)
        if df is not None:
             logger.info(f"Fetched {len(df)} rows for {ticker_symbol}.")
             print(df.head())
        else:
             logger.error(f"Failed to fetch data for {ticker_symbol}.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")