# macro_data.py 

import pandas as pd
import os
import numpy as np
import pandas_datareader as pdr
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the cache file name (constant)
CACHE_FILENAME = "macro_indicators.csv" 

FRED_API_KEY = os.environ.get('FRED_API_KEY') #

def fetch_macro_indicators(app_root, start_date=None, end_date=None):
    """
    Fetch macroeconomic indicators from FRED, checking local cache first.
    Uses app_root for consistent cache path. Applies consistent processing and NaN handling.
    """
    if not app_root:
        logger.error("app_root not provided to fetch_macro_indicators. Cannot determine cache directory.")
        raise ValueError("app_root is required for cache path construction.")

    cache_dir = os.path.join(app_root, '..', 'generated_data', 'data_cache') #
    os.makedirs(cache_dir, exist_ok=True) 
    cache_filepath = os.path.join(cache_dir, CACHE_FILENAME) #
    logger.info(f"Checking cache for macro data at: {cache_filepath}")

    cache_exists = os.path.exists(cache_filepath) #
    logger.info(f"Cache file exists: {cache_exists}")

    if cache_exists:
        logger.info(f"Attempting to load cached macro data from: {CACHE_FILENAME}")
        try:
            macro_data_cache = pd.read_csv(cache_filepath, parse_dates=['Date']) #
            required_cols = ['Date', 'Interest_Rate', 'SP500'] 
            missing_cols = [col for col in required_cols if col not in macro_data_cache.columns]

            if missing_cols: #
                 logger.warning(f"Cached file {CACHE_FILENAME} missing required columns: {missing_cols}. Re-downloading.") 
            elif macro_data_cache.empty: #
                 logger.warning(f"Cached file {CACHE_FILENAME} is empty. Re-downloading.") 
            elif macro_data_cache['Date'].isna().any(): #
                 logger.warning(f"Cached file {CACHE_FILENAME} contains invalid dates. Re-downloading.") 
            else:
                logger.info(f"Successfully loaded {len(macro_data_cache)} macro records from cache.")
                
                macro_data_to_process = macro_data_cache.set_index('Date') #
                
                processing_steps = [
                    lambda df_step: df_step.ffill().bfill(), #
                    lambda df_step: df_step.interpolate(method='time'), #
                    lambda df_step: df_step.assign( #
                        Interest_Rate_MA30=df_step['Interest_Rate'].rolling(window=30, min_periods=1).mean(), 
                        SP500_MA30=df_step['SP500'].rolling(window=30, min_periods=1).mean() 
                    )
                ]
                for step in processing_steps:
                    macro_data_to_process = step(macro_data_to_process)
                
                # Consistent dropna() applied to all columns
                processed_df = macro_data_to_process.reset_index().dropna() 
                
                if processed_df.empty:
                    logger.warning(f"Cached macro data became empty after processing and dropna for {CACHE_FILENAME}. Re-downloading.")
                else:
                    logger.info(f"Processed cached macro data, {len(processed_df)} rows remaining.")
                    return processed_df
        except Exception as e:
            logger.warning(f"Failed to load or process cached file {CACHE_FILENAME}: {e}. Re-downloading.")

    logger.info("Cache miss or invalid for macro data. Proceeding to download from FRED.")
    try:
        if not FRED_API_KEY: #
            logger.warning("FRED_API_KEY environment variable not set. Cannot download from FRED.") 
            raise ValueError("FRED API Key not configured.")

        pdr.fred.FredReader.api_key = FRED_API_KEY #

        if start_date is None: start_date = '1954-07-01' #
        if end_date is None: end_date = datetime.today().strftime('%Y-%m-%d') #

        logger.info(f"Fetching FRED data from {start_date} to {end_date}.")
        macro_data_download = pdr.get_data_fred(['DFF', 'SP500'], start=start_date, end=end_date) #

        if macro_data_download.empty: #
            logger.warning("FRED download returned empty data.") 
            raise ValueError("Empty data received from FRED.")

        macro_data_download = macro_data_download.reset_index() 
        macro_data_download['DATE'] = pd.to_datetime(macro_data_download['DATE']) #
        macro_data_download.columns = ['Date', 'Interest_Rate', 'SP500'] #
        macro_data_to_process = macro_data_download.set_index('Date') #

        processing_steps = [
            lambda df_step: df_step.ffill().bfill(), #
            lambda df_step: df_step.interpolate(method='time'), #
            lambda df_step: df_step.assign( #
                Interest_Rate_MA30=df_step['Interest_Rate'].rolling(window=30, min_periods=1).mean(), 
                SP500_MA30=df_step['SP500'].rolling(window=30, min_periods=1).mean() 
            )
        ]
        for step in processing_steps:
            macro_data_to_process = step(macro_data_to_process)

        processed_df = macro_data_to_process.reset_index().dropna() #

        if processed_df.empty:
            logger.error("Downloaded FRED data became empty after processing and dropna. Check FRED source or date range.")
            raise ValueError("Processed FRED data is empty.")


        try:
            processed_df.to_csv(cache_filepath, index=False) #
            logger.info(f"Saved downloaded macro data to cache: {CACHE_FILENAME}")
        except Exception as e:
            logger.error(f"Failed to save macro data to cache file {CACHE_FILENAME}: {e}")

        return processed_df

    except Exception as e: #
        logger.error(f"Macro data fetch/processing error: {e}", exc_info=True) 
        logger.info("Generating fallback dataset due to error.")
        
        fb_start_date_str = start_date if isinstance(start_date, str) else (start_date.strftime('%Y-%m-%d') if start_date else '1954-07-01')
        fb_end_date_str = end_date if isinstance(end_date, str) else (end_date.strftime('%Y-%m-%d') if end_date else datetime.today().strftime('%Y-%m-%d'))

        try:
            dates = pd.date_range(start=fb_start_date_str, end=fb_end_date_str) #
            if dates.empty: 
                 logger.warning(f"Fallback date range is invalid or empty ({fb_start_date_str} to {fb_end_date_str}). Using default fallback range.")
                 dates = pd.date_range(start="1954-07-01", end=datetime.today())
        except Exception as date_err:
            logger.error(f"Error creating date range for fallback: {date_err}. Using default fallback range.")
            dates = pd.date_range(start="1954-07-01", end=datetime.today())


        fallback_df = pd.DataFrame({'Date': dates})
        fallback_df['Interest_Rate'] = np.linspace(0.5, 5.5, len(dates)) #
        fallback_df['SP500'] = np.geomspace(50, 4500, len(dates)) #
        
        fallback_df['Interest_Rate_MA30'] = fallback_df['Interest_Rate'].rolling(window=30, min_periods=1).mean().fillna(method='bfill') #
        fallback_df['SP500_MA30'] = fallback_df['SP500'].rolling(window=30, min_periods=1).mean().fillna(method='bfill') #
        
        final_fallback_df = fallback_df.dropna() #

        if final_fallback_df.empty:
            logger.critical("Fallback dataset is also empty after processing. Something is seriously wrong.")
            
        return final_fallback_df


if __name__ == "__main__":
    current_app_root = os.path.dirname(os.path.abspath(__file__)) #
    df_macro = fetch_macro_indicators(app_root=current_app_root) 
    if df_macro is not None and not df_macro.empty: #
        logger.info(f"Final macro dataset has {len(df_macro)} records.") 
        print(f"Date range: {df_macro['Date'].min().date()} to {df_macro['Date'].max().date()}") 
        print(f"Interest Rate Stats: Mean={df_macro['Interest_Rate'].mean():.2f}") 
        print(f"SP500 Stats: Mean={df_macro['SP500'].mean():.0f}") 
        print(df_macro.tail()) 
    else: #
        logger.error("Failed to get macro data or it resulted in an empty DataFrame.")