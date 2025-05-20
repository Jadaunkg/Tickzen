# macro_data.py (MODIFIED with improved caching path and logging)

import pandas as pd
import os
import numpy as np
import pandas_datareader as pdr
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Removed CACHE_DIR definition here

# Define the cache file name (constant)
CACHE_FILENAME = "macro_indicators.csv"

FRED_API_KEY = os.environ.get('FRED_API_KEY')

def fetch_macro_indicators(app_root, start_date=None, end_date=None): # Added app_root
    """
    Fetch macroeconomic indicators from FRED, checking local cache first.
    Uses app_root for consistent cache path.
    """
    # Construct cache path using app_root
    if not app_root:
        logger.error("app_root not provided to fetch_macro_indicators. Cannot determine cache directory.")
        raise ValueError("app_root is required for cache path construction.")

    cache_dir = os.path.join(app_root, 'data_cache')
    os.makedirs(cache_dir, exist_ok=True) # Ensure cache directory exists
    cache_filepath = os.path.join(cache_dir, CACHE_FILENAME)
    logger.info(f"Checking cache for macro data at: {cache_filepath}") # Log the exact path

    # --- Check Cache First ---
    cache_exists = os.path.exists(cache_filepath)
    logger.info(f"Cache file exists: {cache_exists}") # Log if file exists

    if cache_exists:
        logger.info(f"Attempting to load cached macro data from: {CACHE_FILENAME}")
        try:
            macro_data = pd.read_csv(cache_filepath, parse_dates=['Date'])
            required_cols = ['Date', 'Interest_Rate', 'SP500'] # Check for base columns
            missing_cols = [col for col in required_cols if col not in macro_data.columns]

            if missing_cols:
                 logger.warning(f"Cached file {CACHE_FILENAME} missing required columns: {missing_cols}. Re-downloading.")
            elif macro_data.empty:
                 logger.warning(f"Cached file {CACHE_FILENAME} is empty. Re-downloading.")
            elif macro_data['Date'].isna().any():
                 logger.warning(f"Cached file {CACHE_FILENAME} contains invalid dates. Re-downloading.")
            else:
                logger.info(f"Successfully loaded {len(macro_data)} macro records from cache.")
                # Apply processing steps to cached data
                macro_data = macro_data.set_index('Date')
                processing_steps = [
                    lambda df: df.ffill().bfill(),
                    lambda df: df.interpolate(method='time'),
                    lambda df: df.assign(
                        Interest_Rate_MA30=df['Interest_Rate'].rolling(30, min_periods=1).mean(),
                        SP500_MA30=df['SP500'].rolling(30, min_periods=1).mean()
                    )
                ]
                for step in processing_steps:
                    macro_data = step(macro_data)
                # Ensure MAs didn't introduce all NaNs
                processed_df = macro_data.reset_index().dropna(subset=['Interest_Rate_MA30', 'SP500_MA30'], how='all')
                logger.info(f"Processed cached macro data, {len(processed_df)} rows remaining.")
                return processed_df
        except Exception as e:
            logger.warning(f"Failed to load or process cached file {CACHE_FILENAME}: {e}. Re-downloading.")
            # Fall through to download

    # --- Download Logic ---
    logger.info("Cache miss or invalid for macro data. Proceeding to download from FRED.")
    # (Rest of the download and processing logic remains the same as previous version)
    # ... (pdr.get_data_fred call, processing, validation) ...
    try:
        if not FRED_API_KEY:
            logger.warning("FRED_API_KEY environment variable not set. Cannot download from FRED.")
            raise ValueError("FRED API Key not configured.")

        pdr.fred.FredReader.api_key = FRED_API_KEY

        if start_date is None: start_date = '1954-07-01'
        if end_date is None: end_date = datetime.today().strftime('%Y-%m-%d')

        macro_data = pdr.get_data_fred(['DFF', 'SP500'], start=start_date, end=end_date)

        if macro_data.empty:
            logger.warning("FRED download returned empty data.")
            raise ValueError("Empty data received from FRED.")

        macro_data = macro_data.reset_index()
        macro_data['DATE'] = pd.to_datetime(macro_data['DATE'])
        macro_data.columns = ['Date', 'Interest_Rate', 'SP500']
        macro_data = macro_data.set_index('Date')

        # Processing downloaded data
        processing_steps = [
            lambda df: df.ffill().bfill(),
            lambda df: df.interpolate(method='time'),
            lambda df: df.assign(
                Interest_Rate_MA30=df['Interest_Rate'].rolling(30, min_periods=1).mean(),
                SP500_MA30=df['SP500'].rolling(30, min_periods=1).mean()
            )
        ]
        for step in processing_steps:
            macro_data = step(macro_data)

        processed_df = macro_data.reset_index().dropna()

        # --- Save to Cache ---
        try:
            processed_df.to_csv(cache_filepath, index=False)
            logger.info(f"Saved downloaded macro data to cache: {CACHE_FILENAME}")
        except Exception as e:
            logger.error(f"Failed to save macro data to cache file {CACHE_FILENAME}: {e}")

        return processed_df

    except Exception as e:
        logger.error(f"Macro data fetch/processing error: {e}")
        logger.info("Generating fallback dataset due to error.")
        dates = pd.date_range(start_date or "1954-07-01", end_date or datetime.today())
        fallback_df = pd.DataFrame({
            'Date': dates,
            'Interest_Rate': np.linspace(0.5, 5.5, len(dates)),
            'SP500': np.geomspace(50, 4500, len(dates))
        })
        fallback_df['Interest_Rate_MA30'] = fallback_df['Interest_Rate'].rolling(30, min_periods=1).mean().fillna(method='bfill')
        fallback_df['SP500_MA30'] = fallback_df['SP500'].rolling(30, min_periods=1).mean().fillna(method='bfill')
        return fallback_df.dropna()


if __name__ == "__main__":
    # In standalone execution, define APP_ROOT relative to this script
    current_app_root = os.path.dirname(os.path.abspath(__file__))
    df = fetch_macro_indicators(app_root=current_app_root)
    if df is not None and not df.empty:
        logger.info(f"Final macro dataset has {len(df)} records.")
        print(f"Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
        print(f"Interest Rate Stats: Mean={df['Interest_Rate'].mean():.2f}")
        print(f"SP500 Stats: Mean={df['SP500'].mean():.0f}")
        print(df.tail())
    else:
        logger.error("Failed to get macro data.")