#!/usr/bin/env python3
"""
Pipeline Data Collector
========================

Data-only pipeline that collects comprehensive stock data without generating reports.
Uses existing pipeline functions to gather all necessary data for Supabase export.

Data Collection:
---------------
1. Historical price data (10+ years)
2. Real-time market data
3. Technical indicators (calculated)
4. Forecast predictions (Prophet)
5. Fundamental metrics
6. Risk analysis
7. Dividend information
8. Ownership data
9. Sentiment analysis
10. Insider transactions

This module focuses purely on data collection and does NOT generate any reports.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional, List
import pandas as pd
import yfinance as yf

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import data collection functions
from data_processing_scripts.data_collection import fetch_real_time_data
from data_processing_scripts.macro_data import fetch_macro_indicators
from data_processing_scripts.data_preprocessing import preprocess_data
from Models.prophet_model import train_prophet_model
from analysis_scripts.fundamental_analysis import extract_quarterly_earnings_data, extract_peer_comparison_data

logger = logging.getLogger(__name__)


class PipelineDataCollector:
    """
    Collects comprehensive stock data using existing pipeline functions.
    Does NOT generate reports - only collects and prepares data.
    """
    
    def __init__(self, app_root: str = None):
        """
        Initialize data collector
        
        Args:
            app_root: Root directory of the application
        """
        if app_root is None:
            app_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        
        self.app_root = app_root
        self.ticker = None
        self.timestamp = None
    
    def collect_all_data(self, ticker: str) -> Dict:
        """
        Collect all stock data using pipeline functions
        
        Args:
            ticker: Stock symbol to collect data for
            
        Returns:
            Dict containing all collected data:
            {
                'ticker': str,
                'timestamp': str,
                'stock_data': pd.DataFrame,  # Historical OHLCV
                'processed_data': pd.DataFrame,  # With technical indicators
                'current_price': Dict,  # Real-time price info
                'forecast_data': pd.DataFrame,  # Prophet predictions
                'info': Dict,  # Company fundamentals
                'news': List[Dict],  # News articles
                'recommendations': pd.DataFrame,  # Analyst recommendations
                'balance_sheet': pd.DataFrame,  # Balance sheet data
                'financials': pd.DataFrame,  # Financial statements
                'collection_status': str,  # success/partial/failed
                'errors': List[str]  # Any errors encountered
            }
        """
        self.ticker = ticker
        self.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        result = {
            'ticker': ticker,
            'timestamp': self.timestamp,
            'collection_status': 'success',
            'errors': []
        }
        
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"COLLECTING DATA FOR: {ticker}")
            logger.info(f"{'='*80}\n")
            
            # Step 1: Fetch real-time and historical data
            logger.info("Step 1/6: Fetching real-time and historical price data...")
            try:
                real_time_data = fetch_real_time_data(
                    ticker, 
                    self.app_root, 
                    include_price=True, 
                    include_intraday=True
                )
                result['stock_data'] = real_time_data.get('daily_data')
                result['current_price'] = real_time_data.get('current_price_data')
                
                if result['stock_data'] is None or result['stock_data'].empty:
                    raise ValueError(f"No historical data found for {ticker}")
                
                logger.info(f"  ✓ Collected {len(result['stock_data'])} days of price data")
                logger.info(f"  ✓ Current price: ${result['current_price']['current_price']}")
                
            except Exception as e:
                error_msg = f"Failed to fetch price data: {e}"
                result['errors'].append(error_msg)
                logger.error(f"  ✗ {error_msg}")
                result['collection_status'] = 'failed'
                return result
            
            # Step 2: Fetch macroeconomic indicators
            logger.info("\nStep 2/6: Fetching macroeconomic indicators...")
            try:
                macro_data = fetch_macro_indicators(
                    app_root=self.app_root,
                    stock_data=result['stock_data']
                )
                logger.info(f"  ✓ Macro indicators loaded")
            except Exception as e:
                error_msg = f"Failed to fetch macro data: {e}"
                result['errors'].append(error_msg)
                logger.warning(f"  ! {error_msg} - Continuing without macro data")
                macro_data = None
            
            # Step 3: Calculate technical indicators
            logger.info("\nStep 3/6: Calculating technical indicators...")
            try:
                processed_data = preprocess_data(
                    result['stock_data'], 
                    macro_data
                )
                
                if processed_data is None or processed_data.empty:
                    raise ValueError("Preprocessing returned empty data")
                
                result['processed_data'] = processed_data
                
                # Count available indicators
                indicator_cols = [col for col in processed_data.columns if col not in ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']]
                logger.info(f"  ✓ Calculated {len(indicator_cols)} technical indicators")
                logger.info(f"  ✓ Total rows: {len(processed_data)}")
                
            except Exception as e:
                error_msg = f"Failed to calculate indicators: {e}"
                result['errors'].append(error_msg)
                logger.error(f"  ✗ {error_msg}")
                result['collection_status'] = 'partial'
                result['processed_data'] = result['stock_data']  # Use unprocessed data
            
            # Step 4: Generate forecast using Prophet
            logger.info("\nStep 4/6: Generating price forecast...")
            try:
                model, forecast, actual_df, forecast_df = train_prophet_model(
                    result['processed_data'].copy(),
                    ticker,
                    forecast_horizon='1y',
                    timestamp=self.timestamp
                )
                
                if forecast_df is None or forecast_df.empty:
                    raise ValueError("Prophet returned empty forecast")
                
                result['forecast_data'] = forecast_df
                result['forecast_model'] = model
                result['actual_data'] = actual_df
                
                logger.info(f"  ✓ Generated {len(forecast_df)} days of forecast")
                
            except Exception as e:
                error_msg = f"Failed to generate forecast: {e}"
                result['errors'].append(error_msg)
                logger.error(f"  ✗ {error_msg}")
                result['collection_status'] = 'partial'
                result['forecast_data'] = None
            
            # Step 5: Fetch fundamental data
            logger.info("\nStep 5/6: Fetching fundamental data...")
            try:
                yf_ticker = yf.Ticker(ticker)
                
                # Get company info
                result['info'] = yf_ticker.info or {}
                logger.info(f"  ✓ Fetched {len(result['info'])} info fields")
                
                # Get news
                try:
                    result['news'] = yf_ticker.news if hasattr(yf_ticker, 'news') else []
                    logger.info(f"  ✓ Fetched {len(result['news'])} news articles")
                except:
                    result['news'] = []
                    logger.warning("  ! No news available")
                
                # Get analyst recommendations
                try:
                    result['recommendations'] = yf_ticker.recommendations if hasattr(yf_ticker, 'recommendations') and yf_ticker.recommendations is not None else pd.DataFrame()
                    logger.info(f"  ✓ Fetched {len(result['recommendations'])} recommendations")
                except:
                    result['recommendations'] = pd.DataFrame()
                    logger.warning("  ! No recommendations available")
                
                # Get balance sheet
                try:
                    result['balance_sheet'] = yf_ticker.balance_sheet
                    logger.info(f"  ✓ Fetched balance sheet data")
                except:
                    result['balance_sheet'] = None
                    logger.warning("  ! No balance sheet available")
                
                # Get financials
                try:
                    result['financials'] = yf_ticker.financials
                    logger.info(f"  ✓ Fetched financial statements")
                except:
                    result['financials'] = None
                    logger.warning("  ! No financials available")
                
                # Get insider transactions
                try:
                    result['insider_transactions'] = yf_ticker.insider_transactions if hasattr(yf_ticker, 'insider_transactions') else pd.DataFrame()
                    logger.info(f"  ✓ Fetched {len(result['insider_transactions'])} insider transactions")
                except:
                    result['insider_transactions'] = pd.DataFrame()
                    logger.warning("  ! No insider transactions available")
                
                
                # Get quarterly earnings data
                try:
                    result['quarterly_earnings'] = extract_quarterly_earnings_data(result, ticker)
                    logger.info(f"  ✓ Fetched quarterly earnings data")
                except Exception as e:
                    result['quarterly_earnings'] = {}
                    logger.warning(f"  ! Failed to fetch quarterly earnings: {e}")

                # Get peer comparison data
                try:
                    result['peer_comparison'] = extract_peer_comparison_data(ticker)
                    peer_count = len(result['peer_comparison']) - 1  # Exclude target stock
                    logger.info(f"  ✓ Fetched peer comparison data ({peer_count} peers)")
                except Exception as e:
                    result['peer_comparison'] = {}
                    logger.warning(f"  ! Failed to fetch peer comparison: {e}")

                # Get dividends
                try:
                    result['dividends'] = yf_ticker.dividends
                    logger.info(f"  ✓ Fetched {len(result['dividends'])} dividend records")
                except:
                    result['dividends'] = pd.DataFrame()
                    logger.warning("  ! No dividend history available")
                
            except Exception as e:
                error_msg = f"Failed to fetch fundamentals: {e}"
                result['errors'].append(error_msg)
                logger.error(f"  ✗ {error_msg}")
                result['collection_status'] = 'partial'
                result['info'] = {}
                result['news'] = []
                result['recommendations'] = pd.DataFrame()
            
            # Step 6: Collection summary
            logger.info("\nStep 6/6: Data collection summary...")
            logger.info(f"  • Historical Data: {len(result.get('stock_data', []))} rows")
            logger.info(f"  • Technical Indicators: {len(result.get('processed_data', []))} rows")
            logger.info(f"  • Forecast: {len(result.get('forecast_data', []))} rows")
            logger.info(f"  • Fundamental Fields: {len(result.get('info', {}))}")
            logger.info(f"  • News Articles: {len(result.get('news', []))}")
            logger.info(f"  • Errors: {len(result['errors'])}")
            logger.info(f"  • Status: {result['collection_status'].upper()}")
            
            logger.info(f"\n{'='*80}")
            logger.info(f"DATA COLLECTION COMPLETE: {ticker}")
            logger.info(f"{'='*80}\n")
            
            return result
            
        except Exception as e:
            error_msg = f"Critical error during data collection: {e}"
            result['errors'].append(error_msg)
            logger.error(f"\n✗ {error_msg}")
            result['collection_status'] = 'failed'
            return result
    
    def validate_data(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate collected data for completeness and quality
        
        Args:
            data: Collected data dictionary
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        required_fields = ['stock_data', 'processed_data', 'current_price', 'info']
        for field in required_fields:
            if field not in data or data[field] is None:
                issues.append(f"Missing required field: {field}")
        
        # Check data quality
        if 'stock_data' in data and data['stock_data'] is not None:
            if len(data['stock_data']) < 252:  # Less than 1 year
                issues.append(f"Insufficient historical data: only {len(data['stock_data'])} days")
        
        if 'processed_data' in data and data['processed_data'] is not None:
            required_cols = ['Date', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in data['processed_data'].columns]
            if missing_cols:
                issues.append(f"Missing required columns: {missing_cols}")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def get_data_summary(self, data: Dict) -> Dict:
        """
        Generate summary statistics for collected data
        
        Args:
            data: Collected data dictionary
            
        Returns:
            Dict with summary statistics
        """
        summary = {
            'ticker': data.get('ticker'),
            'timestamp': data.get('timestamp'),
            'status': data.get('collection_status'),
            'total_errors': len(data.get('errors', [])),
            'data_counts': {}
        }
        
        # Count records in each dataset
        if 'stock_data' in data and data['stock_data'] is not None:
            summary['data_counts']['historical_prices'] = len(data['stock_data'])
        
        if 'processed_data' in data and data['processed_data'] is not None:
            summary['data_counts']['technical_indicators'] = len(data['processed_data'])
        
        if 'forecast_data' in data and data['forecast_data'] is not None:
            summary['data_counts']['forecast_periods'] = len(data['forecast_data'])
        
        if 'info' in data:
            summary['data_counts']['fundamental_fields'] = len(data['info'])
        
        if 'news' in data:
            summary['data_counts']['news_articles'] = len(data['news'])
        
        return summary


def main():
    """Test the data collector"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test with AAPL
    collector = PipelineDataCollector()
    data = collector.collect_all_data('AAPL')
    
    # Validate data
    is_valid, issues = collector.validate_data(data)
    
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    print(f"Valid: {is_valid}")
    if issues:
        print("Issues:")
        for issue in issues:
            print(f"  - {issue}")
    
    # Print summary
    summary = collector.get_data_summary(data)
    print("\n" + "="*80)
    print("DATA SUMMARY")
    print("="*80)
    print(f"Ticker: {summary['ticker']}")
    print(f"Status: {summary['status']}")
    print(f"Errors: {summary['total_errors']}")
    print("\nData Counts:")
    for key, value in summary['data_counts'].items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
