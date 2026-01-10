#!/usr/bin/env python3
"""
Stock Analysis Pipeline Module
=============================

This module orchestrates the complete stock analysis pipeline, from data
collection to report generation. It handles time-series forecasting using
Prophet, technical analysis, and comprehensive report creation.

Pipeline Stages:
---------------
1. **Data Collection** (5-25% progress):
   - Historical stock data via yfinance
   - Real-time market data
   - Macroeconomic indicators from FRED
   - Earnings and fundamental data

2. **Data Preprocessing** (25-35% progress):
   - Data cleaning and validation
   - Missing value handling
   - Outlier detection and treatment
   - Feature engineering

3. **Model Training** (35-60% progress):
   - Prophet time-series forecasting
   - Technical indicator calculations
   - Volatility modeling
   - Trend analysis

4. **Report Generation** (60-100% progress):
   - Comprehensive analysis reports
   - WordPress-ready content
   - Chart and visualization creation
   - Asset optimization for web

Key Functions:
-------------
- run_pipeline(): Main pipeline orchestrator
- preprocess_data(): Data cleaning and preparation
- train_model(): Prophet model training
- generate_report(): Report creation and formatting
- cleanup_old_processed_data(): Maintenance and cleanup

Data Flow:
---------
```
Ticker Input → Data Collection → Preprocessing → Model Training → Report Generation
     ↓              ↓               ↓              ↓               ↓
  Validation    Cache Storage   Feature Eng.   Forecasting    Web Assets
     ↓              ↓               ↓              ↓               ↓
 Error Check    Progress Update  Progress Update Progress Update  Final Output
```

Progress Tracking:
-----------------
Real-time progress updates via SocketIO:
- Stage identification (Data Collection, Model Training, etc.)
- Percentage completion (0-100%)
- Current operation description
- Error notifications for failures

Caching Strategy:
----------------
- Processed data cached in generated_data/data_cache/
- Cache invalidation based on data freshness (24 hours)
- Ticker-specific cache files with timestamp validation
- Automatic cleanup of stale cache files (7+ days old)

Error Handling:
--------------
- Comprehensive exception handling at each stage
- User-friendly error messages via SocketIO
- Detailed logging for debugging
- Graceful degradation for missing data

Configuration:
-------------
Supported tickers defined in config/config.py
Environment variables for API keys:
- ALPHA_VANTAGE_API_KEY: Alpha Vantage API access
- FRED_API_KEY: Federal Reserve Economic Data
- FINNHUB_API_KEY: Financial market data

Output Formats:
--------------
1. **PDF Reports**: Comprehensive analysis documents
2. **WordPress Assets**: Web-optimized images and content
3. **JSON Data**: Structured analysis results
4. **CSV Exports**: Raw and processed data

Usage Example:
-------------
```python
from automation_scripts.pipeline import run_pipeline

result = run_pipeline(
    ticker='AAPL',
    timestamp='2026-01-05',
    app_root='/path/to/app',
    socketio_instance=socketio,
    task_room='user123'
)
```

Performance Considerations:
--------------------------
- Lazy loading of ML libraries (Prophet, scikit-learn)
- Efficient data structures for large datasets
- Memory management for long-running processes
- Parallel processing where applicable

Data Sources:
------------
- Yahoo Finance (yfinance): Primary stock data
- Alpha Vantage: Alternative data source
- FRED: Economic indicators
- Finnhub: Real-time market data
- Custom data preprocessing pipelines

Author: TickZen Development Team
Version: 3.0
Last Updated: January 2026
"""

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
from data_processing_scripts.data_collection import fetch_stock_data, fetch_real_time_data
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
    Enhanced to handle multiple files per ticker and keep only the most recent.
    """
    try:
        if not os.path.exists(cache_dir):
            return
        
        current_time = datetime.now()
        files_cleaned = 0
        ticker_files = {}  # Group files by ticker
        
        # First pass: Group files by ticker
        for filename in os.listdir(cache_dir):
            if 'processed_data' in filename and filename.endswith('.csv'):
                filepath = os.path.join(cache_dir, filename)
                try:
                    # Extract ticker from filename (format: TICKER_processed_data_YYYY-MM-DD.csv)
                    ticker = filename.split('_processed_data_')[0]
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if ticker not in ticker_files:
                        ticker_files[ticker] = []
                    
                    ticker_files[ticker].append({
                        'filepath': filepath,
                        'filename': filename,
                        'mtime': file_mtime,
                        'age_days': (current_time - file_mtime).days
                    })
                    
                except Exception as e:
                    pipeline_logger.warning(f"Error processing cache file {filename}: {e}")
        
        # Second pass: For each ticker, keep only the most recent file and clean old ones
        for ticker, files in ticker_files.items():
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x['mtime'], reverse=True)
            
            for i, file_info in enumerate(files):
                if i == 0:  # Keep the most recent file if it's not too old
                    if file_info['age_days'] > max_age_days:
                        try:
                            os.remove(file_info['filepath'])
                            files_cleaned += 1
                            pipeline_logger.info(f"Cleaned up old processed data: {file_info['filename']} (age: {file_info['age_days']} days)")
                        except Exception as e:
                            pipeline_logger.warning(f"Error cleaning cache file {file_info['filename']}: {e}")
                else:  # Remove all older files for this ticker
                    try:
                        os.remove(file_info['filepath'])
                        files_cleaned += 1
                        pipeline_logger.info(f"Cleaned up duplicate processed data: {file_info['filename']}")
                    except Exception as e:
                        pipeline_logger.warning(f"Error cleaning cache file {file_info['filename']}: {e}")
        
        if files_cleaned > 0:
            pipeline_logger.info(f"Cleaned up {files_cleaned} old/duplicate processed data files from {cache_dir}")
            
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
        
        # More permissive ticker pattern that allows common special characters including futures (=)
        valid_ticker_pattern = r'^[A-Z0-9\^.\-$&/=]+(\.[A-Z]{1,2})?$'
        if not ticker or not re.match(valid_ticker_pattern, ticker):
            raise ValueError(f"Invalid ticker format: {ticker}.")

        _emit_progress(socketio_instance, task_room, 5, "Fetching real-time stock data and generating introduction...", "Real-time Data & Key Metrics", ticker, event_name_progress)
        
        # Fetch real-time data for more accurate analysis
        real_time_data = fetch_real_time_data(ticker, app_root, include_price=True, include_intraday=True)
        stock_data = real_time_data.get('daily_data')
        current_price_info = real_time_data.get('current_price_data')
        
        if stock_data is None or stock_data.empty:
            error_msg = f"No data found for ticker '{ticker}'. This could mean:\n• The ticker symbol is incorrect\n• The stock is delisted or not available\n• No trading data exists for this symbol\n\nPlease try again with a different stock symbol (e.g., AAPL, MSFT, GOOGL)."
            raise RuntimeError(error_msg)
        
        # Log current price information if available
        if current_price_info:
            pipeline_logger.info(f"Current price for {ticker}: ${current_price_info.get('current_price', 'N/A')} "
                               f"({current_price_info.get('market_state', 'Unknown')})")
        
        # Add current price data to processing context for enhanced reporting
        if current_price_info:
            # Add current price as the most recent data point for analysis
            latest_close = current_price_info.get('current_price')
            if latest_close:
                # Convert today's date to string format to match existing data format
                today_str = pd.Timestamp.now().normalize().strftime('%Y-%m-%d')
                
                # Check if today's date already exists to avoid duplicates
                if today_str not in stock_data['Date'].values:
                    stock_data.loc[len(stock_data), 'Date'] = today_str
                    stock_data.loc[len(stock_data)-1, 'Close'] = latest_close
                    # Convert Date column to datetime for proper sorting
                    stock_data['Date'] = pd.to_datetime(stock_data['Date'])
                    stock_data = stock_data.sort_values('Date').reset_index(drop=True)
                    # Convert back to string format to maintain consistency
                    stock_data['Date'] = stock_data['Date'].dt.strftime('%Y-%m-%d')
                else:
                    # Update the existing row for today with the latest close price
                    today_mask = stock_data['Date'] == today_str
                    if today_mask.any():
                        stock_data.loc[today_mask, 'Close'] = latest_close

        _emit_progress(socketio_instance, task_room, 10, "Fetching macroeconomic data...", "Data Collection", ticker, event_name_progress)
        macro_data = fetch_macro_indicators(app_root=app_root, stock_data=stock_data)
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
        # Check if forecasting data is valid (model can be None when using WSL bridge)
        if forecast is None or actual_df is None or forecast_df is None or forecast.empty or actual_df.empty or forecast_df.empty:
            error_msg = f"Unable to generate predictions for ticker '{ticker}'. The stock may not have enough historical data for reliable forecasting.\n\nPlease try again with a more established stock that has longer trading history."
            raise RuntimeError(error_msg)
        pipeline_logger.info(f"Model trained for {ticker}. Forecast generated.")

        _emit_progress(socketio_instance, task_room, 50, "Analyzing fundamental ratios and metrics...", "Fundamental Analysis & Ratios", ticker, event_name_progress)
        _emit_progress(socketio_instance, task_room, 60, "Fetching fundamental data...", "Fundamentals", ticker, event_name_progress)
        try:
            yf_ticker_obj = yf.Ticker(ticker)
            info_data = yf_ticker_obj.info or {}
            recs_data = yf_ticker_obj.recommendations if hasattr(yf_ticker_obj, 'recommendations') and yf_ticker_obj.recommendations is not None else pd.DataFrame()
            # News will be fetched via Finnhub API in extract_news function
            
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
                'news': yf_ticker_obj.news if hasattr(yf_ticker_obj, 'news') and yf_ticker_obj.news else [],  # Get actual news data for sentiment analysis
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
            app_root=app_root_for_report, # Use the adjusted app_root here
            current_price_info=current_price_info  # Pass real-time current price data
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
        # More permissive ticker pattern that allows common special characters including futures (=)
        valid_ticker_pattern = r'^[A-Z0-9\^.\-$&/=]+$'
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
        # Check if forecasting data is valid (model can be None when using WSL bridge)
        if forecast is None or actual_df is None or forecast_df is None or forecast.empty or actual_df.empty or forecast_df.empty:
            error_msg = f"Unable to generate predictions for ticker '{ticker}'. The stock may not have enough historical data for reliable forecasting.\n\nPlease try again with a more established stock that has longer trading history."
            raise RuntimeError(error_msg)
        pipeline_logger.info(f"WP Model trained for {ticker}.")
        
        _emit_progress(socketio_instance, task_room, 60, "Fetching fundamentals for WP assets...", "WP Fundamentals", ticker, event_name_progress)
        try:
            yf_ticker_obj = yf.Ticker(ticker)
            info_data = yf_ticker_obj.info or {}
            recs_data = yf_ticker_obj.recommendations if hasattr(yf_ticker_obj, 'recommendations') and yf_ticker_obj.recommendations is not None else pd.DataFrame()
            # News will be fetched via Finnhub API in extract_news function
            
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
                'news': yf_ticker_obj.news if hasattr(yf_ticker_obj, 'news') and yf_ticker_obj.news else [],  # Get actual news data for sentiment analysis
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
        # Handle the return value: img_urls_dict_or_path is either a file path (str) or None
        image_urls_dict = {}
        if img_urls_dict_or_path is not None:
            if isinstance(img_urls_dict_or_path, str) and img_urls_dict_or_path.strip(): 
                image_urls_dict = {"featured_image_path": img_urls_dict_or_path}
            elif isinstance(img_urls_dict_or_path, dict):
                image_urls_dict = img_urls_dict_or_path
            else:
                pipeline_logger.warning(f"Unexpected return type for image_urls from create_wordpress_report_assets for {ticker}: {type(img_urls_dict_or_path)}")
        else:
            pipeline_logger.info(f"No featured image path returned for {ticker} (normal if chart generation had issues)")


        if text_report_html is None or "Error Generating Report" in text_report_html:
             raise RuntimeError(f"WordPress asset HTML generation failed for {ticker}")
        
        pipeline_logger.info(f"   Text HTML for WP generated for {ticker}.")
        # Safely check if image_urls_dict is valid and has content
        if image_urls_dict and isinstance(image_urls_dict, dict) and len(image_urls_dict) > 0:
            pipeline_logger.info(f"   Chart image assets processed for {ticker}: {len(image_urls_dict)} items.")
        else: 
            pipeline_logger.warning(f"   No chart image assets returned for WP {ticker}.")

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