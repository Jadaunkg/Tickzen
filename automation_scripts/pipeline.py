# pipeline.py
import os
import time
import traceback
import re
import logging 
from datetime import datetime, date 

import pandas as pd
import yfinance as yf

import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config.config import TICKERS
from data_processing_scripts.data_collection import fetch_stock_data
from data_processing_scripts.macro_data import fetch_macro_indicators
from data_processing_scripts.data_preprocessing import preprocess_data
from Models.prophet_model import train_prophet_model
from reporting_tools.report_generator import create_full_report, create_wordpress_report_assets

pipeline_logger = logging.getLogger(__name__)
if not pipeline_logger.handlers: 
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - PIPELINE - %(levelname)s - %(message)s')


def _get_processed_data_filepath(ticker, app_root):
    today_str = date.today().strftime('%Y-%m-%d')
    cache_dir = os.path.join(app_root, '..', 'generated_data', 'data_cache')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{ticker}_processed_data_{today_str}.csv")

def _is_processed_data_current(processed_filepath, stock_data, macro_data, ticker):
    """
    Check if processed data exists and is based on current source data.
    Returns True if processed data is current, False otherwise.
    """
    if not os.path.exists(processed_filepath):
        return False
    
    try:
        # Load processed data
        processed_data = pd.read_csv(processed_filepath)
        if processed_data.empty:
            return False
        
        # Check if processed data has current dates
        if 'Date' in processed_data.columns:
            processed_data['Date'] = pd.to_datetime(processed_data['Date'], errors='coerce')
            latest_processed_date = processed_data['Date'].max().date() if pd.notna(processed_data['Date'].max()) else None
            
            # Check stock data currency
            if stock_data is not None and not stock_data.empty and 'Date' in stock_data.columns:
                if not pd.api.types.is_datetime64_any_dtype(stock_data['Date']):
                    stock_data_copy = stock_data.copy()
                    stock_data_copy['Date'] = pd.to_datetime(stock_data_copy['Date'], errors='coerce')
                else:
                    stock_data_copy = stock_data
                
                latest_stock_date = stock_data_copy['Date'].max().date() if pd.notna(stock_data_copy['Date'].max()) else None
                
                if latest_stock_date and latest_processed_date:
                    # If stock data is newer than processed data, reprocess
                    if latest_stock_date > latest_processed_date:
                        pipeline_logger.info(f"Stock data ({latest_stock_date}) is newer than processed data ({latest_processed_date}) for {ticker}. Reprocessing.")
                        return False
            
            # Check if processed data is current (within last 3 days)
            today = date.today()
            if latest_processed_date:
                days_diff = (today - latest_processed_date).days
                if days_diff > 3:
                    pipeline_logger.info(f"Processed data for {ticker} is {days_diff} days old. Reprocessing for current data.")
                    return False
        
        pipeline_logger.info(f"Processed data for {ticker} is current.")
        return True
        
    except Exception as e:
        pipeline_logger.warning(f"Error checking processed data currency for {ticker}: {e}")
        return False

def cleanup_old_processed_data(cache_dir, max_age_days=7):
    """
    Clean up old processed data files to prevent accumulation.
    """
    try:
        if not os.path.exists(cache_dir):
            return
        
        current_time = datetime.now()
        files_cleaned = 0
        
        for filename in os.listdir(cache_dir):
            if 'processed_data' in filename and filename.endswith('.csv'):
                filepath = os.path.join(cache_dir, filename)
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    age_days = (current_time - file_mtime).days
                    
                    if age_days > max_age_days:
                        os.remove(filepath)
                        files_cleaned += 1
                        pipeline_logger.info(f"Cleaned up old processed data file: {filename} (age: {age_days} days)")
                
                except Exception as e:
                    pipeline_logger.warning(f"Error cleaning processed data file {filename}: {e}")
        
        if files_cleaned > 0:
            pipeline_logger.info(f"Cleaned up {files_cleaned} old processed data files from {cache_dir}")
            
    except Exception as e:
        pipeline_logger.error(f"Error during processed data cleanup: {e}")

def _emit_progress(socketio_instance, task_room, progress, message, stage_detail="", ticker="N/A", event_name='analysis_progress'):
    if socketio_instance and task_room:
        payload = {'progress': progress, 'message': message, 'stage': stage_detail, 'ticker': ticker}
        pipeline_logger.info(f"Emitting to room '{task_room}' (Event: {event_name}): {payload}")
        socketio_instance.emit(event_name, payload, room=task_room)
        socketio_instance.sleep(0.05) 
    elif socketio_instance: 
        pipeline_logger.warning(f"Task room not specified for {event_name}, emitting globally for ticker {ticker}: {message}")
        socketio_instance.emit(event_name, {'progress': progress, 'message': message, 'stage': stage_detail, 'ticker': ticker})
        socketio_instance.sleep(0.05)
    else:
        pipeline_logger.info(f"Progress for {ticker} (No SocketIO - Event: {event_name}): {progress}% - {message} ({stage_detail})")


def run_pipeline(ticker, ts, app_root, socketio_instance=None, task_room=None):
    processed_filepath = None
    model = forecast = None
    report_path = report_html = None
    event_name_progress = 'analysis_progress' 
    event_name_error = 'analysis_error'     

    try:
        pipeline_logger.info(f"\n----- Starting ORIGINAL pipeline for {ticker} (Room: {task_room}) -----")
        _emit_progress(socketio_instance, task_room, 0, f"Initiating analysis for {ticker}...", "Initialization", ticker, event_name_progress)
        
        # More permissive ticker pattern that allows common special characters
        valid_ticker_pattern = r'^[A-Z0-9\^.\-$&/]+(\.[A-Z]{1,2})?$'
        if not ticker or not re.match(valid_ticker_pattern, ticker):
            raise ValueError(f"Invalid ticker format: {ticker}.")

        _emit_progress(socketio_instance, task_room, 5, "Fetching stock data and generating introduction...", "Introduction & Key Metrics", ticker, event_name_progress)
        stock_data = fetch_stock_data(ticker, app_root=app_root)
        if stock_data is None or stock_data.empty:
            error_msg = f"No data found for ticker '{ticker}'. This could mean:\n• The ticker symbol is incorrect\n• The stock is delisted or not available\n• No trading data exists for this symbol\n\nPlease try again with a different stock symbol (e.g., AAPL, MSFT, GOOGL)."
            raise RuntimeError(error_msg)

        _emit_progress(socketio_instance, task_room, 10, "Fetching macroeconomic data...", "Data Collection", ticker, event_name_progress)
        macro_data = fetch_macro_indicators(app_root=app_root)
        if macro_data is None or macro_data.empty:
            pipeline_logger.warning(f"Macro data fetch failed for {ticker}. Proceeding.")

        _emit_progress(socketio_instance, task_room, 15, "Processing 15-year price history and charts...", "15-Year Price History & Charts", ticker, event_name_progress)
        _emit_progress(socketio_instance, task_room, 20, "Preprocessing data...", "Preprocessing", ticker, event_name_progress)
        processed_filepath = _get_processed_data_filepath(ticker, app_root)
        
        # Clean up old processed data files periodically
        cache_dir = os.path.join(app_root, '..', 'generated_data', 'data_cache')
        cleanup_old_processed_data(cache_dir)
        
        processed_data = None
        
        # Check if processed data exists and is current
        if _is_processed_data_current(processed_filepath, stock_data, macro_data, ticker):
            pipeline_logger.info(f"Loading current processed data for {ticker} from cache...")
            processed_data = pd.read_csv(processed_filepath)
            if 'Date' in processed_data.columns:
                processed_data['Date'] = pd.to_datetime(processed_data['Date'])
            if processed_data.empty: 
                processed_data = None
        
        if processed_data is None:
            pipeline_logger.info(f"Preprocessing data for {ticker} with current source data...")
            processed_data = preprocess_data(stock_data, macro_data if macro_data is not None else None)
            if processed_data is None or processed_data.empty:
                error_msg = f"Unable to process data for ticker '{ticker}'. The stock data may be insufficient for analysis.\n\nPlease try again with a different stock symbol that has more trading history."
                raise RuntimeError(error_msg)
            processed_data.to_csv(processed_filepath, index=False)
            pipeline_logger.info(f"Saved new processed data for {ticker} based on current source data.")

        _emit_progress(socketio_instance, task_room, 30, "Calculating technical indicators (RSI, MACD, Histogram)...", "Technical Indicators (RSI, MACD, Histogram)", ticker, event_name_progress)
        _emit_progress(socketio_instance, task_room, 40, "Training predictive model...", "Model Training", ticker, event_name_progress)
        model, forecast, actual_df, forecast_df = train_prophet_model(
            processed_data.copy(), ticker, forecast_horizon='1y', timestamp=ts
        )
        if model is None or forecast is None or actual_df is None or forecast_df is None:
            error_msg = f"Unable to generate predictions for ticker '{ticker}'. The stock may not have enough historical data for reliable forecasting.\n\nPlease try again with a more established stock that has longer trading history."
            raise RuntimeError(error_msg)
        pipeline_logger.info(f"Model trained for {ticker}. Forecast generated.")

        _emit_progress(socketio_instance, task_room, 50, "Analyzing fundamental ratios and metrics...", "Fundamental Analysis & Ratios", ticker, event_name_progress)
        _emit_progress(socketio_instance, task_room, 60, "Fetching fundamental data...", "Fundamentals", ticker, event_name_progress)
        try:
            yf_ticker_obj = yf.Ticker(ticker)
            info_data = yf_ticker_obj.info or {}
            recs_data = yf_ticker_obj.recommendations if hasattr(yf_ticker_obj, 'recommendations') and yf_ticker_obj.recommendations is not None else pd.DataFrame()
            news_data = yf_ticker_obj.news if hasattr(yf_ticker_obj, 'news') and yf_ticker_obj.news is not None else []
            
            # Add balance sheet and financial data for enhanced financial efficiency analysis
            balance_sheet_data = None
            financials_data = None
            try:
                balance_sheet_data = yf_ticker_obj.balance_sheet
                financials_data = yf_ticker_obj.financials
            except Exception as fin_err:
                pipeline_logger.warning(f"yfinance financial statements error for {ticker}: {fin_err}.")
            
            fundamentals = {
                'info': info_data, 
                'recommendations': recs_data, 
                'news': news_data,
                'balance_sheet': balance_sheet_data,
                'financials': financials_data
            }
        except Exception as yf_err:
            pipeline_logger.warning(f"yfinance fundamentals error for {ticker}: {yf_err}.")
            fundamentals = {'info': {}, 'recommendations': pd.DataFrame(), 'news': [], 'balance_sheet': None, 'financials': None}

        _emit_progress(socketio_instance, task_room, 65, "Gathering analyst consensus and recommendations...", "Analyst Consensus & Recommendations", ticker, event_name_progress)
        _emit_progress(socketio_instance, task_room, 70, "Analyzing macro economic indicators...", "Macro Economic Indicators", ticker, event_name_progress)
        _emit_progress(socketio_instance, task_room, 75, "Generating forecast table and price targets...", "Forecast Table & Price Targets", ticker, event_name_progress)
        _emit_progress(socketio_instance, task_room, 80, "Generating report components...", "Report Generation", ticker, event_name_progress)
        
        # Determine the correct app_root for report generation
        # If the passed app_root is .../automation_scripts (likely standalone), adjust to .../app
        # Otherwise, assume app_root is already .../app (from web call)
        app_root_for_report = app_root
        if os.path.basename(app_root) == 'automation_scripts':
            app_root_for_report = os.path.join(app_root, '..', 'app')
            pipeline_logger.info(f"Adjusted app_root for report generation (standalone detected): {app_root_for_report}")
        elif os.path.basename(app_root) != 'app':
             pipeline_logger.warning(f"Unexpected app_root ('{app_root}') for report generation. Expected 'app' or 'automation_scripts'. Report path may be incorrect.")

        report_path, report_html = create_full_report(
            ticker=ticker, actual_data=actual_df, forecast_data=forecast_df,
            historical_data=processed_data.copy(), fundamentals=fundamentals, ts=ts,
            app_root=app_root_for_report # Use the adjusted app_root here
        )
        if report_html is None or "Error Generating Report" in report_html:
            raise RuntimeError(f"Report generator failed for {ticker}")
        if report_path: pipeline_logger.info(f"Report saved for {ticker} -> {os.path.basename(report_path)}")
        else: pipeline_logger.warning(f"Report HTML for {ticker} generated, but save failed.")

        _emit_progress(socketio_instance, task_room, 90, "Assessing risk factors and finalizing analysis...", "Risk Factors & Assessment", ticker, event_name_progress)
        _emit_progress(socketio_instance, task_room, 100, "Analysis complete! Redirecting soon...", "Complete", ticker, event_name_progress)
        pipeline_logger.info(f"----- ORIGINAL Pipeline successful for {ticker} -----")
        return model, forecast, report_path, report_html

    except Exception as err:
        pipeline_logger.error(f"----- ORIGINAL Pipeline Error for {ticker}: {err} -----", exc_info=True)
        if socketio_instance and task_room:
             socketio_instance.emit(event_name_error, {'message': str(err), 'ticker': ticker}, room=task_room)
        return None, None, None, None


def run_wp_pipeline(ticker, ts, app_root, socketio_instance=None, task_room=None):
    pipeline_logger.info(f"\n>>>>> Starting WORDPRESS pipeline for {ticker} (Room: {task_room}) <<<<<")
    event_name_progress = 'wp_asset_progress' 
    event_name_error = 'wp_asset_error'     

    _emit_progress(socketio_instance, task_room, 0, f"Initiating WP asset generation for {ticker}", "WP Init", ticker, event_name_progress)
    
    processed_filepath = None
    text_report_html = None
    image_urls_dict = {} 
    model = forecast = None

    try:
        # More permissive ticker pattern that allows common special characters
        valid_ticker_pattern = r'^[A-Z0-9\^.\-$&/]+$'
        if not ticker or not re.match(valid_ticker_pattern, ticker):
            raise ValueError(f"Invalid ticker format: {ticker}.")

        _emit_progress(socketio_instance, task_room, 5, "Fetching stock data for WP...", "WP Data Collection", ticker, event_name_progress)
        stock_data = fetch_stock_data(ticker, app_root=app_root)
        if stock_data is None or stock_data.empty: 
            error_msg = f"No data found for ticker '{ticker}'. This could mean:\n• The ticker symbol is incorrect\n• The stock is delisted or not available\n• No trading data exists for this symbol\n\nPlease try again with a different stock symbol (e.g., AAPL, MSFT, GOOGL)."
            raise RuntimeError(error_msg)

        _emit_progress(socketio_instance, task_room, 10, "Fetching macro data for WP...", "WP Data Collection", ticker, event_name_progress)
        macro_data = fetch_macro_indicators(app_root=app_root)
        if macro_data is None or macro_data.empty: pipeline_logger.warning(f"WP Macro data fetch failed for {ticker}.")

        _emit_progress(socketio_instance, task_room, 20, "Preprocessing data for WP...", "WP Preprocessing", ticker, event_name_progress)
        processed_filepath = _get_processed_data_filepath(ticker, app_root)
        processed_data = None
        if os.path.exists(processed_filepath):
            pipeline_logger.info(f"Loading processed WP data for {ticker} from cache...")
            processed_data = pd.read_csv(processed_filepath)
            if 'Date' in processed_data.columns: processed_data['Date'] = pd.to_datetime(processed_data['Date'])
            if processed_data.empty: processed_data = None
        
        if processed_data is None:
            pipeline_logger.info(f"Preprocessing WP data for {ticker}...")
            processed_data = preprocess_data(stock_data, macro_data if macro_data is not None else None)
            if processed_data is None or processed_data.empty: 
                error_msg = f"Unable to process data for ticker '{ticker}'. The stock data may be insufficient for analysis.\n\nPlease try again with a different stock symbol that has more trading history."
                raise RuntimeError(error_msg)
            processed_data.to_csv(processed_filepath, index=False)
            pipeline_logger.info(f"Saved new processed WP data for {ticker}.")

        _emit_progress(socketio_instance, task_room, 40, "Training model for WP assets...", "WP Model Training", ticker, event_name_progress)
        model, forecast, actual_df, forecast_df = train_prophet_model(processed_data.copy(), ticker, forecast_horizon='1y', timestamp=ts)
        if model is None or forecast is None or actual_df is None or forecast_df is None:
            error_msg = f"Unable to generate predictions for ticker '{ticker}'. The stock may not have enough historical data for reliable forecasting.\n\nPlease try again with a more established stock that has longer trading history."
            raise RuntimeError(error_msg)
        pipeline_logger.info(f"WP Model trained for {ticker}.")
        
        _emit_progress(socketio_instance, task_room, 60, "Fetching fundamentals for WP assets...", "WP Fundamentals", ticker, event_name_progress)
        try:
            yf_ticker_obj = yf.Ticker(ticker)
            info_data = yf_ticker_obj.info or {}
            recs_data = yf_ticker_obj.recommendations if hasattr(yf_ticker_obj, 'recommendations') and yf_ticker_obj.recommendations is not None else pd.DataFrame()
            news_data = yf_ticker_obj.news if hasattr(yf_ticker_obj, 'news') and yf_ticker_obj.news is not None else []
            
            # Add balance sheet and financial data for enhanced financial efficiency analysis
            balance_sheet_data = None
            financials_data = None
            try:
                balance_sheet_data = yf_ticker_obj.balance_sheet
                financials_data = yf_ticker_obj.financials
            except Exception as fin_err:
                pipeline_logger.warning(f"yfinance WP financial statements error for {ticker}: {fin_err}.")
            
            fundamentals = {
                'info': info_data, 
                'recommendations': recs_data, 
                'news': news_data,
                'balance_sheet': balance_sheet_data,
                'financials': financials_data
            }
        except Exception as e: 
            fundamentals = {'info': {}, 'recommendations': pd.DataFrame(), 'news': [], 'balance_sheet': None, 'financials': None}
            pipeline_logger.warning(f"WP Fundamentals Warning for {ticker}: {e}")

        _emit_progress(socketio_instance, task_room, 75, "Generating HTML and chart assets...", "WP Asset Generation", ticker, event_name_progress)
        text_report_html, img_urls_dict_or_path = create_wordpress_report_assets(
            ticker=ticker, actual_data=actual_df, forecast_data=forecast_df,
            historical_data=processed_data.copy(), fundamentals=fundamentals, ts=ts, app_root=app_root
        )
        if isinstance(img_urls_dict_or_path, str): 
            image_urls_dict = {"featured_image_path": img_urls_dict_or_path}
        elif isinstance(img_urls_dict_or_path, dict):
            image_urls_dict = img_urls_dict_or_path
        else:
            image_urls_dict = {} 
            pipeline_logger.warning(f"Unexpected return type for image_urls from create_wordpress_report_assets for {ticker}: {type(img_urls_dict_or_path)}")


        if text_report_html is None or "Error Generating Report" in text_report_html:
             raise RuntimeError(f"WordPress asset HTML generation failed for {ticker}")
        
        pipeline_logger.info(f"   Text HTML for WP generated for {ticker}.")
        if image_urls_dict: pipeline_logger.info(f"   Chart image assets processed for {ticker}: {len(image_urls_dict)} items.")
        else: pipeline_logger.warning(f"   No chart image assets dictionary returned for WP {ticker}.")

        _emit_progress(socketio_instance, task_room, 100, "WP assets ready!", "WP Complete", ticker, event_name_progress)
        pipeline_logger.info(f">>>>> WORDPRESS Pipeline successful for {ticker} <<<<<")
        return model, forecast, text_report_html, image_urls_dict

    except Exception as err:
        pipeline_logger.error(f">>>>> WORDPRESS Pipeline Error for {ticker}: {err} <<<<<", exc_info=True)
        if socketio_instance and task_room: 
            socketio_instance.emit(event_name_error, {'message': str(err), 'ticker': ticker}, room=task_room)
        return None, None, None, {}


if __name__ == "__main__":
    pipeline_logger.info("Starting batch pipeline execution (with Caching)...")
    APP_ROOT_STANDALONE = os.path.dirname(os.path.abspath(__file__))
    pipeline_logger.info(f"Running standalone from: {APP_ROOT_STANDALONE}")

    class MockSocketIO:
        def emit(self, event, data, room=None):
            pipeline_logger.info(f"MOCK EMIT to room '{room}': Event='{event}', Data='{data}'")
        def sleep(self, duration):
            time.sleep(duration) 

    mock_socket_io_instance = MockSocketIO()
    test_room_id_prefix = "test_pipeline_room"

    successful_orig, failed_orig = [], []
    successful_wp, failed_wp = [], []

    pipeline_logger.info("\n--- Running Original Pipeline Batch (with mock SocketIO) ---")
    for ticker_item in TICKERS: 
        ts = str(int(time.time()))
        model, forecast, report_path, report_html_content = run_pipeline(
            ticker_item, ts, APP_ROOT_STANDALONE,
            socketio_instance=mock_socket_io_instance, task_room=f"{test_room_id_prefix}_{ticker_item}_orig"
        )
        if report_path and report_html_content and "Error Generating Report" not in report_html_content:
            successful_orig.append(ticker_item)
        else:
            failed_orig.append(ticker_item)
        time.sleep(0.1) 

    pipeline_logger.info("\nBatch Summary (Original Reports):")
    pipeline_logger.info(f"   Successful: {', '.join(successful_orig) or 'None'}")
    pipeline_logger.info(f"   Failed:     {', '.join(failed_orig) or 'None'}")

    pipeline_logger.info("\n--- Running WP Asset Pipeline Batch (with mock SocketIO) ---")
    for ticker_item in TICKERS:
        ts_wp = str(int(time.time()))
        model_wp, forecast_wp, text_html_wp, img_urls_dict_wp = run_wp_pipeline(
            ticker_item, ts_wp, APP_ROOT_STANDALONE,
            socketio_instance=mock_socket_io_instance, task_room=f"{test_room_id_prefix}_{ticker_item}_wp"
        )
        if text_html_wp and "Error Generating Report" not in text_html_wp and isinstance(img_urls_dict_wp, dict):
            successful_wp.append(ticker_item)
        else:
            failed_wp.append(ticker_item)
        time.sleep(0.1)

    pipeline_logger.info("\nBatch Summary (WordPress Assets):")
    pipeline_logger.info(f"   Successful: {', '.join(successful_wp) or 'None'}")
    pipeline_logger.info(f"   Failed:     {', '.join(failed_wp) or 'None'}")

    pipeline_logger.info("\nBatch pipeline execution completed.")