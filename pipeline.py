# pipeline.py (This version is compatible with main_portal_app.py's expectations)
import os
import time
import traceback
import re
import logging # Added for logging within pipeline if needed
from datetime import datetime, date # Added for daily cache management

import pandas as pd
import yfinance as yf

# Assuming config.py and other local modules are in the correct path
from config import TICKERS # Used for standalone testing in __main__
from data_collection import fetch_stock_data
from macro_data import fetch_macro_indicators
from data_preprocessing import preprocess_data
from prophet_model import train_prophet_model
# Ensure this import matches your report generator module and function name
from report_generator import create_full_report, create_wordpress_report_assets

# Configure logging if needed within the pipeline itself
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# Helper function for processed data file paths
def _get_processed_data_filepath(ticker, app_root):
    """Constructs the daily-stamped path for processed data CSV in data_cache."""
    today_str = date.today().strftime('%Y-%m-%d')
    cache_dir = os.path.join(app_root, 'data_cache')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{ticker}_processed_data_{today_str}.csv")

# --- Original pipeline function (for full HTML reports) ---
def run_pipeline(ticker, ts, app_root):
    """
    Runs the full analysis pipeline for a given stock ticker.
    Relies on fetch functions for caching, passing app_root for path consistency.
    """
    # reports_dir_path = os.path.join(app_root, 'static', 'stock_reports')
    # os.makedirs(reports_dir_path, exist_ok=True) # Directory created by report_generator

    processed_filepath = None # Will store the path to the processed CSV for potential cleanup
    model = forecast = None
    report_path = report_html = None

    try:
        print(f"\n----- Starting ORIGINAL pipeline for {ticker} -----")
        valid_ticker_pattern = r'^[A-Z0-9\^.-]+$'
        if not ticker or not re.match(valid_ticker_pattern, ticker):
            raise ValueError(f"[Original Pipeline] Invalid ticker format: {ticker}.")

        # --- 1. Data Collection (Pass app_root) ---
        # This function should handle its own caching based on current day
        print("Step 1: Fetching stock data (checking cache)...")
        stock_data = fetch_stock_data(ticker, app_root=app_root) # Pass app_root
        if stock_data is None or stock_data.empty:
            raise RuntimeError(f"Failed to fetch or load stock data for ticker: {ticker}.")

        print("Step 1b: Fetching macroeconomic data (checking cache)...")
        macro_data = fetch_macro_indicators(app_root=app_root) # Pass app_root
        if macro_data is None or macro_data.empty:
            print(f"Warning: Failed to fetch or load macroeconomic data for {ticker}. Proceeding without it.")

        # --- 2. Data Preprocessing (with caching for processed data) ---
        processed_filepath = _get_processed_data_filepath(ticker, app_root)
        processed_data = None

        if os.path.exists(processed_filepath):
            print(f"Step 2: Loading processed data for {ticker} from today's cache: {os.path.basename(processed_filepath)}")
            processed_data = pd.read_csv(processed_filepath)
            # Ensure 'Date' column is datetime if loaded from CSV
            if 'Date' in processed_data.columns:
                processed_data['Date'] = pd.to_datetime(processed_data['Date'])
            # Additional check to ensure it's not empty after loading
            if processed_data.empty:
                 print(f"Warning: Cached processed data for {ticker} is empty. Reprocessing.")
                 processed_data = None # Force reprocessing
        
        if processed_data is None: # If not loaded from cache or cache was empty
            print("Step 2: Preprocessing data...")
            processed_data = preprocess_data(stock_data, macro_data if macro_data is not None else None)
            if processed_data is None or processed_data.empty:
                raise RuntimeError(f"Preprocessing resulted in empty dataset for {ticker}.")
            
            # Save the newly processed data to cache
            processed_data.to_csv(processed_filepath, index=False)
            print(f"   Saved new processed data -> {os.path.basename(processed_filepath)}")

        # --- 3. Prophet Model Training & Aggregation ---
        print("Step 3: Training Prophet model & predicting...")
        model, forecast, actual_df, forecast_df = train_prophet_model(
            processed_data, ticker, forecast_horizon='1y', timestamp=ts
        )
        if model is None or forecast is None or actual_df is None or forecast_df is None:
            raise RuntimeError(f"Prophet model training or forecasting failed for {ticker}.")
        print(f"   Model trained. Forecast generated for {len(forecast_df)} periods.")

        # --- 4. Fetch Fundamentals ---
        print("Step 4: Fetching fundamentals via yfinance...")
        try:
            yf_ticker_obj = yf.Ticker(ticker)
            info_data = {}
            recs_data = pd.DataFrame()
            news_data = []
            try: info_data = yf_ticker_obj.info or {}
            except Exception as info_err: print(f"   Warning: Could not fetch .info for {ticker}: {info_err}")
            try: recs_data = yf_ticker_obj.recommendations if hasattr(yf_ticker_obj, 'recommendations') and yf_ticker_obj.recommendations is not None else pd.DataFrame()
            except Exception as rec_err: print(f"   Warning: Could not fetch .recommendations for {ticker}: {rec_err}")
            try: news_data = yf_ticker_obj.news if hasattr(yf_ticker_obj, 'news') and yf_ticker_obj.news is not None else []
            except Exception as news_err: print(f"   Warning: Could not fetch .news for {ticker}: {news_err}")
            
            fundamentals = {
                'info': info_data,
                'recommendations': recs_data,
                'news': news_data
            }
            if not fundamentals['info'].get('symbol'):
                print(f"Warning: Could not fetch detailed info symbol for {ticker} via yfinance.")
        except Exception as yf_err:
            print(f"Warning: Error fetching yfinance fundamentals object for {ticker}: {yf_err}.")
            fundamentals = {'info': {}, 'recommendations': pd.DataFrame(), 'news': []}


        # --- 5. Generate FULL HTML Report ---
        print("Step 5: Generating FULL HTML report...")
        report_path, report_html = create_full_report(
            ticker=ticker, actual_data=actual_df, forecast_data=forecast_df,
            historical_data=processed_data, fundamentals=fundamentals, ts=ts,
            app_root=app_root # report_generator will save to static/stock_reports based on this
        )
        if report_html is None or "Error Generating Report" in report_html:
            raise RuntimeError(f"Original report generator failed or returned error HTML for {ticker}")
        if report_path:
            print(f"   Report saved -> {os.path.basename(report_path)}")
        else:
            print(f"   Report HTML generated, but failed to save file.")

        print(f"----- ORIGINAL Pipeline successful for {ticker} -----")
        return model, forecast, report_path, report_html

    except (ValueError, RuntimeError) as err:
        print(f"----- ORIGINAL Pipeline Error for {ticker} -----")
        print(f"Error: {err}")
        return None, None, None, None # Return four values on error
    except Exception as e:
        print(f"----- ORIGINAL Pipeline failure for {ticker} -----")
        print(f"Unexpected Error: {e}")
        traceback.print_exc()
        # No need to remove processed_csv here, as it's intended to be cached
        return None, None, None, None # Return four values on error


# --- WordPress Pipeline Function (Optimized for main_portal_app.py) ---
def run_wp_pipeline(ticker, ts, app_root):
    """
    Runs the analysis pipeline specifically to generate WordPress assets.
    Returns model, forecast, HTML content, and a dictionary of image URLs.
    """
    # static_dir_path = os.path.join(app_root, 'static')
    # os.makedirs(static_dir_path, exist_ok=True) # No longer directly saving to static_dir_path here

    processed_filepath = None # Will store the path to the processed CSV for potential cleanup
    text_report_html = None
    image_urls = {} # Expecting a dictionary
    model = forecast = None

    try:
        print(f"\n>>>>> Starting WORDPRESS pipeline for {ticker} <<<<<")
        valid_ticker_pattern = r'^[A-Z0-9\^.-]+$'
        if not ticker or not re.match(valid_ticker_pattern, ticker):
            raise ValueError(f"[WP Pipeline] Invalid ticker format: {ticker}.")

        # --- Steps 1-4: Data Fetching, Preprocessing, Model Training, Fundamentals ---
        # (These steps are largely the same as the original pipeline, with caching)
        print("WP Step 1: Fetching stock data (checking cache)...")
        stock_data = fetch_stock_data(ticker, app_root=app_root)
        if stock_data is None or stock_data.empty: raise RuntimeError(f"Failed to fetch/load stock data for {ticker}.")

        print("WP Step 1b: Fetching macroeconomic data (checking cache)...")
        macro_data = fetch_macro_indicators(app_root=app_root)
        if macro_data is None or macro_data.empty: print(f"Warning: Failed to fetch/load macro data for {ticker}.")

        # WP Step 2: Preprocessing data (with caching for processed data)
        processed_filepath = _get_processed_data_filepath(ticker, app_root)
        processed_data = None

        if os.path.exists(processed_filepath):
            print(f"WP Step 2: Loading processed data for {ticker} from today's cache: {os.path.basename(processed_filepath)}")
            processed_data = pd.read_csv(processed_filepath)
            if 'Date' in processed_data.columns:
                processed_data['Date'] = pd.to_datetime(processed_data['Date'])
            if processed_data.empty:
                 print(f"Warning: Cached WP processed data for {ticker} is empty. Reprocessing.")
                 processed_data = None
        
        if processed_data is None: # If not loaded from cache or cache was empty
            print("WP Step 2: Preprocessing data...")
            processed_data = preprocess_data(stock_data, macro_data if macro_data is not None else None)
            if processed_data is None or processed_data.empty: raise RuntimeError(f"Preprocessing resulted in empty dataset for {ticker}.")
            
            # Save the newly processed data to cache
            processed_data.to_csv(processed_filepath, index=False)
            print(f"   Saved new WP processed data -> {os.path.basename(processed_filepath)}")

        print("WP Step 3: Training Prophet model & predicting...")
        model, forecast, actual_df, forecast_df = train_prophet_model(
            processed_data, ticker, forecast_horizon='1y', timestamp=ts
        )
        if model is None or forecast is None or actual_df is None or forecast_df is None:
            raise RuntimeError(f"Prophet model training or forecasting failed for {ticker}.")
        print(f"   WP Model trained for {ticker}.")

        print(f"WP Step 4: Fetching fundamentals for {ticker}...")
        try:
            yf_ticker_obj = yf.Ticker(ticker)
            info_data = {}
            recs_data = pd.DataFrame()
            news_data = []
            try: info_data = yf_ticker_obj.info or {}
            except Exception as info_err: print(f"   Warning: Could not fetch .info for {ticker}: {info_err}")
            try: recs_data = yf_ticker_obj.recommendations if hasattr(yf_ticker_obj, 'recommendations') and yf_ticker_obj.recommendations is not None else pd.DataFrame()
            except Exception as rec_err: print(f"   Warning: Could not fetch .recommendations for {ticker}: {rec_err}")
            try: news_data = yf_ticker_obj.news if hasattr(yf_ticker_obj, 'news') and yf_ticker_obj.news is not None else []
            except Exception as news_err: print(f"   Warning: Could not fetch .news for {ticker}: {news_err}")
            
            fundamentals = {
                'info': info_data,
                'recommendations': recs_data,
                'news': news_data
            }
            if not fundamentals['info'].get('symbol'): print(f"Warning: Could not fetch detailed info symbol for {ticker}.")
        except Exception as yf_err:
            print(f"Warning: Error fetching yfinance fundamentals object for {ticker}: {yf_err}.")
            fundamentals = {'info': {}, 'recommendations': pd.DataFrame(), 'news': []}


        # --- Step 5: Generate WORDPRESS Assets (text HTML + Image URLs) ---
        print(f"WP Step 5: Generating WordPress assets for {ticker} (Text HTML + Image URLs)...")
        # This assumes create_wordpress_report_assets returns (html_string, image_urls_dictionary)
        text_report_html, image_urls = create_wordpress_report_assets(
            ticker=ticker, actual_data=actual_df, forecast_data=forecast_df,
            historical_data=processed_data, fundamentals=fundamentals, ts=ts,
            app_root=app_root
        )
        if text_report_html is None or "Error Generating Report" in text_report_html:
            print(f"Error HTML from report generator for {ticker}: {text_report_html}")
            raise RuntimeError(f"WordPress asset generator failed or returned error HTML for {ticker}")

        print(f"   Text HTML generated for {ticker}.")
        if isinstance(image_urls, dict) and image_urls:
            print(f"   Chart image URLs generated: {len(image_urls)} URLs returned.")
        elif image_urls: # If it's not a dict but has a value, log a warning
            print(f"   WARNING: Chart image URLs for {ticker} were returned but not as a dictionary: {type(image_urls)}")
        else: # If it's None or empty dict
            print(f"   WARNING: No chart image URLs were generated or returned for {ticker}.")


        print(f">>>>> WORDPRESS Pipeline successful for {ticker} <<<<<")
        return model, forecast, text_report_html, image_urls # image_urls should be a dict

    except (ValueError, RuntimeError) as err:
        print(f">>>>> WORDPRESS Pipeline Error for {ticker} <<<<<")
        print(f"Error: {err}")
        return None, None, None, {} # Return empty dict for image_urls on error
    except Exception as e:
        print(f">>>>> WORDPRESS Pipeline failure for {ticker} <<<<<")
        print(f"Unexpected Error: {e}")
        traceback.print_exc()
        # No need to remove processed_csv here, as it's intended to be cached
        return None, None, None, {} # Return empty dict for image_urls on error


# --- Main execution block (for standalone testing) ---
if __name__ == "__main__":
    print("Starting batch pipeline execution (with Caching)...")
    APP_ROOT_STANDALONE = os.path.dirname(os.path.abspath(__file__))
    print(f"Running standalone from: {APP_ROOT_STANDALONE}")

    successful_orig, failed_orig = [], []
    successful_wp, failed_wp = [], []

    print("\n--- Running Original Pipeline Batch ---")
    for ticker_item in TICKERS:
        ts = str(int(time.time()))
        model, forecast, report_path, report_html_content = run_pipeline(ticker_item, ts, APP_ROOT_STANDALONE)
        if report_path and report_html_content and "Error Generating Report" not in report_html_content:
            successful_orig.append(ticker_item)
            print(f"[✔ Orig] {ticker_item} - Report HTML generated and saved.")
        elif report_html_content and "Error Generating Report" not in report_html_content:
            successful_orig.append(f"{ticker_item} (HTML Only)")
            print(f"[✔ Orig] {ticker_item} - Report HTML generated (Save Failed).")
        else:
            failed_orig.append(ticker_item)
            print(f"[✖ Orig] {ticker_item} - Failed.")
        time.sleep(1)

    print("\nBatch Summary (Original Reports):")
    print(f"   Successful: {', '.join(successful_orig) or 'None'}")
    print(f"   Failed:     {', '.join(failed_orig) or 'None'}")

    print("\n--- Running WP Asset Pipeline Batch ---")
    for ticker_item in TICKERS:
        ts_wp = str(int(time.time()))
        # Expecting 4 values: model, forecast, html_text, image_urls_dict
        model_wp, forecast_wp, text_html_wp, img_urls_dict_wp = run_wp_pipeline(ticker_item, ts_wp, APP_ROOT_STANDALONE)
        
        if text_html_wp and "Error Generating Report" not in text_html_wp and isinstance(img_urls_dict_wp, dict):
            successful_wp.append(ticker_item)
            print(f"[✔ WP] {ticker_item} - Text HTML generated.")
            if img_urls_dict_wp:
                print(f"[✔ WP] {ticker_item} - Image URLs generated: {len(img_urls_dict_wp)} URLs")
            else:
                print(f"[✔ WP] {ticker_item} - Image URLs dictionary is empty.")
        else:
            failed_wp.append(ticker_item)
            print(f"[✖ WP] {ticker_item} - Failed. HTML: {'OK' if text_html_wp and 'Error' not in text_html_wp else 'Fail/Error'}, Img URLs Dict: {isinstance(img_urls_dict_wp, dict)}")
        time.sleep(1)

    print("\nBatch Summary (WordPress Assets):")
    print(f"   Successful: {', '.join(successful_wp) or 'None'}")
    print(f"   Failed:     {', '.join(failed_wp) or 'None'}")

    print("\nBatch pipeline execution completed.")