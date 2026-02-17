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
    
    def _is_forecast_calculated_this_month(self, ticker: str) -> bool:
        """
        Check if forecast has already been calculated for this ticker this month
        
        Args:
            ticker: Stock symbol
            
        Returns:
            True if forecast calculated this month, False otherwise
        """
        try:
            from datetime import datetime
            from pathlib import Path
            
            current_month = datetime.now().strftime('%Y-%m')
            
            # Check if cached forecast file exists for this month
            cache_dir = Path(self.app_root) / 'generated_data' / 'forecast_cache'
            cache_file = cache_dir / f'{ticker}_forecast_{current_month}.json'
            
            if cache_file.exists():
                logger.info(f"  ℹ Forecast already calculated for {ticker} this month ({current_month}) - using cached")
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"Error checking forecast cache: {e}")
            return False  # If we can't check, proceed with calculation to be safe
    
    def _save_forecast_cache(self, ticker: str, forecast_df: pd.DataFrame) -> None:
        """
        Save forecast data to monthly cache file
        
        Args:
            ticker: Stock symbol
            forecast_df: Forecast dataframe to cache
        """
        try:
            from datetime import datetime
            from pathlib import Path
            import json
            
            current_month = datetime.now().strftime('%Y-%m')
            
            # Create cache directory
            cache_dir = Path(self.app_root) / 'generated_data' / 'forecast_cache'
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Save forecast data as JSON
            cache_file = cache_dir / f'{ticker}_forecast_{current_month}.json'
            forecast_data = {
                'ticker': ticker,
                'month': current_month,
                'created_at': datetime.now().isoformat(),
                'forecast': forecast_df.to_dict('records') if forecast_df is not None else None
            }
            
            with open(cache_file, 'w') as f:
                json.dump(forecast_data, f, default=str)
                
            logger.info(f"  ✓ Cached forecast data for {ticker} ({current_month})")
            
        except Exception as e:
            logger.warning(f"Failed to cache forecast data: {e}")
    
    def _load_forecast_cache(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Load cached forecast data for current month
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Cached forecast DataFrame or None
        """
        try:
            from datetime import datetime
            from pathlib import Path
            import json
            
            current_month = datetime.now().strftime('%Y-%m')
            
            cache_dir = Path(self.app_root) / 'generated_data' / 'forecast_cache'
            cache_file = cache_dir / f'{ticker}_forecast_{current_month}.json'
            
            if not cache_file.exists():
                return None
                
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            if cache_data.get('forecast'):
                return pd.DataFrame(cache_data['forecast'])
                
            return None
            
        except Exception as e:
            logger.warning(f"Failed to load forecast cache: {e}")
            return None
    
    def _is_company_profile_cached_this_month(self, ticker: str) -> bool:
        """
        Check if company profile has been cached for this ticker this month
        
        Args:
            ticker: Stock symbol
            
        Returns:
            True if company profile cached this month, False otherwise
        """
        try:
            from datetime import datetime
            from pathlib import Path
            
            current_month = datetime.now().strftime('%Y-%m')
            
            # Check if cached company profile exists for this month
            cache_dir = Path(self.app_root) / 'generated_data' / 'profile_cache'
            cache_file = cache_dir / f'{ticker}_profile_{current_month}.json'
            
            if cache_file.exists():
                logger.info(f"  ℹ Company profile already cached for {ticker} this month ({current_month}) - using cached")
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"Error checking company profile cache: {e}")
            return False
    
    def _is_insider_transactions_cached_this_month(self, ticker: str) -> bool:
        """
        Check if insider transactions have been cached for this ticker this month
        
        Args:
            ticker: Stock symbol
            
        Returns:
            True if insider transactions cached this month, False otherwise
        """
        try:
            from datetime import datetime
            from pathlib import Path
            
            current_month = datetime.now().strftime('%Y-%m')
            
            # Check if cached insider transactions exist for this month
            cache_dir = Path(self.app_root) / 'generated_data' / 'insider_cache'
            cache_file = cache_dir / f'{ticker}_insider_{current_month}.json'
            
            if cache_file.exists():
                logger.info(f"  ℹ Insider transactions already cached for {ticker} this month ({current_month}) - using cached")
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"Error checking insider transactions cache: {e}")
            return False
    
    def _save_company_profile_cache(self, ticker: str, profile_data: dict) -> None:
        """
        Save company profile data to monthly cache file
        
        Args:
            ticker: Stock symbol
            profile_data: Company profile dictionary to cache
        """
        try:
            from datetime import datetime
            from pathlib import Path
            import json
            
            current_month = datetime.now().strftime('%Y-%m')
            
            # Create cache directory
            cache_dir = Path(self.app_root) / 'generated_data' / 'profile_cache'
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Save profile data as JSON
            cache_file = cache_dir / f'{ticker}_profile_{current_month}.json'
            cache_data = {
                'ticker': ticker,
                'month': current_month,
                'created_at': datetime.now().isoformat(),
                'profile': profile_data
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, default=str)
                
            logger.info(f"  ✓ Cached company profile for {ticker} ({current_month})")
            
        except Exception as e:
            logger.warning(f"Failed to cache company profile: {e}")
    
    def _save_insider_transactions_cache(self, ticker: str, insider_data: pd.DataFrame) -> None:
        """
        Save insider transactions data to monthly cache file
        
        Args:
            ticker: Stock symbol
            insider_data: Insider transactions dataframe to cache
        """
        try:
            from datetime import datetime
            from pathlib import Path
            import json
            
            current_month = datetime.now().strftime('%Y-%m')
            
            # Create cache directory
            cache_dir = Path(self.app_root) / 'generated_data' / 'insider_cache'
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Save insider data as JSON
            cache_file = cache_dir / f'{ticker}_insider_{current_month}.json'
            cache_data = {
                'ticker': ticker,
                'month': current_month,
                'created_at': datetime.now().isoformat(),
                'insider_transactions': insider_data.to_dict('records') if not insider_data.empty else []
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, default=str)
                
            logger.info(f"  ✓ Cached insider transactions for {ticker} ({current_month})")
            
        except Exception as e:
            logger.warning(f"Failed to cache insider transactions: {e}")
    
    def _load_company_profile_cache(self, ticker: str) -> Optional[dict]:
        """
        Load cached company profile data for current month
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Cached company profile dict or None
        """
        try:
            from datetime import datetime
            from pathlib import Path
            import json
            
            current_month = datetime.now().strftime('%Y-%m')
            
            cache_dir = Path(self.app_root) / 'generated_data' / 'profile_cache'
            cache_file = cache_dir / f'{ticker}_profile_{current_month}.json'
            
            if not cache_file.exists():
                return None
                
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            return cache_data.get('profile', {})
            
        except Exception as e:
            logger.warning(f"Failed to load company profile cache: {e}")
            return None
    
    def _load_insider_transactions_cache(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Load cached insider transactions data for current month
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Cached insider transactions DataFrame or None
        """
        try:
            from datetime import datetime
            from pathlib import Path
            import json
            
            current_month = datetime.now().strftime('%Y-%m')
            
            cache_dir = Path(self.app_root) / 'generated_data' / 'insider_cache'
            cache_file = cache_dir / f'{ticker}_insider_{current_month}.json'
            
            if not cache_file.exists():
                return None
                
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            insider_records = cache_data.get('insider_transactions', [])
            return pd.DataFrame(insider_records) if insider_records else pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"Failed to load insider transactions cache: {e}")
            return None
    
    def _check_forecast_exists_in_database(self, ticker: str) -> bool:
        """
        Check if forecast data already exists in database for current month
        
        Args:
            ticker: Stock symbol
            
        Returns:
            True if forecast data exists in DB for this month, False otherwise
        """
        try:
            from datetime import datetime
            from .supabase_client import get_supabase_client
            
            # Get current month start date
            current_month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            
            # Get supabase client
            supabase = get_supabase_client()
            
            # Get stock_id for this ticker
            stock_response = supabase.client.table('stocks').select('id').eq('symbol', ticker).execute()
            
            if not stock_response.data:
                return False
                
            stock_id = stock_response.data[0]['id']
            
            # Check if forecast data exists for this month
            forecast_response = supabase.client.table('forecast_data')\
                .select('forecast_date')\
                .eq('stock_id', stock_id)\
                .gte('created_at', current_month_start)\
                .limit(1)\
                .execute()
            
            exists = len(forecast_response.data) > 0
            
            if exists:
                logger.info(f"  ℹ️ Database already contains forecast data for {ticker} this month")
            
            return exists
            
        except Exception as e:
            logger.warning(f"Error checking database forecast: {e}")
            return False
    
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
            
            # Step 4: Generate forecast using Prophet (with monthly caching)
            logger.info("\nStep 4/6: Generating price forecast...")
            
            forecast_skipped = False
            
            # First check if forecast already exists in database for this month
            forecast_exists_in_db = self._check_forecast_exists_in_database(ticker)
            
            if forecast_exists_in_db:
                # Skip expensive model training if database already has current month's data
                result['forecast_data'] = pd.DataFrame()  # Empty - will be loaded from DB during export
                result['forecast_model'] = None
                result['actual_data'] = None
                forecast_skipped = True
                logger.info(f"  ⏭️  Forecast already exists in database for this month - skipping Prophet training")
            
            # If no database record, check file cache
            elif self._is_forecast_calculated_this_month(ticker):
                # Load cached forecast
                cached_forecast = self._load_forecast_cache(ticker)
                if cached_forecast is not None:
                    result['forecast_data'] = cached_forecast
                    result['forecast_model'] = None  # Model not needed for cached data
                    result['actual_data'] = None
                    forecast_skipped = True
                    logger.info(f"  ⏭️  Using cached forecast data ({len(cached_forecast)} records)")
                else:
                    logger.info("  ⚠️  Cache file found but data invalid - recalculating...")
                    # Proceed to calculation below
            
            # Calculate forecast if not cached or cache invalid
            if not forecast_skipped:
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
                    
                    # Cache the forecast for future use this month
                    self._save_forecast_cache(ticker, forecast_df)
                    
                    logger.info(f"  ✓ Generated {len(forecast_df)} days of forecast")
                    
                except Exception as e:
                    error_msg = f"Failed to generate forecast: {e}"
                    result['errors'].append(error_msg)
                    logger.error(f"  ✗ {error_msg}")
                    result['collection_status'] = 'partial'
                    result['forecast_data'] = None
            
            # Step 5: Fetch fundamental data (with monthly caching for profile and insider data)
            logger.info("\nStep 5/6: Fetching fundamental data...")
            try:
                yf_ticker = yf.Ticker(ticker)
                
                # Get company info (with selective fresh data for dividend fields)
                if self._is_company_profile_cached_this_month(ticker):
                    cached_profile = self._load_company_profile_cache(ticker)
                    result['info'] = cached_profile or {}
                    
                    # CRITICAL FIX: Always fetch fresh dividend data to ensure bug fixes are applied
                    # Dividend data can change frequently and we recently fixed dividend formatting bugs
                    logger.info(f"  ⏭️  Using cached company profile ({len(result['info'])} fields)")
                    logger.info("  🔄 Fetching fresh dividend data to ensure accurate yields...")
                    
                    try:
                        # Get fresh dividend-related fields from yfinance
                        fresh_info = yf_ticker.info or {}
                        dividend_fields = [
                            'dividendYield', 'dividendRate', 'forwardDividendYield', 'forwardDividendRate',
                            'trailingAnnualDividendYield', 'trailingAnnualDividendRate',
                            'fiveYearAvgDividendYield', 'payoutRatio', 'exDividendDate',
                            'lastSplitDate', 'lastSplitFactor'
                        ]
                        
                        # Update cached profile with fresh dividend data
                        for field in dividend_fields:
                            if field in fresh_info:
                                result['info'][field] = fresh_info[field]
                        
                        logger.info(f"  ✓ Updated {len([f for f in dividend_fields if f in fresh_info])} dividend fields with fresh data")
                                
                    except Exception as e:
                        logger.warning(f"  ⚠️  Could not fetch fresh dividend data: {e} - using cached data")
                        
                else:
                    result['info'] = yf_ticker.info or {}
                    self._save_company_profile_cache(ticker, result['info'])
                    logger.info(f"  ✓ Fetched {len(result['info'])} company info fields (including fresh dividend data)")
                
                # Get news (always fresh)
                try:
                    news_data = yf_ticker.news if hasattr(yf_ticker, 'news') else []
                    
                    # Log raw structure for debugging
                    logger.info(f"  🔍 Raw news_data type: {type(news_data).__name__}")
                    
                    # Handle different news data structures from yfinance
                    if isinstance(news_data, dict):
                        # If it's a dict, try to extract the list from common keys
                        if 'result' in news_data:
                            result['news'] = news_data['result'] if isinstance(news_data['result'], list) else []
                            logger.info(f"  🔍 Extracted from 'result' key: {len(result['news'])} items")
                        else:
                            # Try to get it as a list of values
                            result['news'] = list(news_data.values()) if news_data else []
                            logger.info(f"  🔍 Extracted dict values: {len(result['news'])} items")
                    elif isinstance(news_data, list):
                        result['news'] = news_data
                        logger.info(f"  🔍 News is already a list: {len(news_data)} items")
                    else:
                        result['news'] = []
                        logger.info(f"  🔍 Unexpected type {type(news_data).__name__}, setting to empty list")
                    
                    if len(result['news']) > 0:
                        # Log first article structure for diagnostics
                        first = result['news'][0]
                        first_keys = list(first.keys()) if isinstance(first, dict) else 'N/A'
                        logger.info(f"  🔍 First article structure: {first_keys}")
                    
                    logger.info(f"  ✓ Fetched {len(result['news'])} news articles")
                except Exception as e:
                    result['news'] = []
                    logger.warning(f"  ! No news available: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                
                # Get analyst recommendations (always fresh)
                try:
                    result['recommendations'] = yf_ticker.recommendations if hasattr(yf_ticker, 'recommendations') and yf_ticker.recommendations is not None else pd.DataFrame()
                    logger.info(f"  ✓ Fetched {len(result['recommendations'])} recommendations")
                except:
                    result['recommendations'] = pd.DataFrame()
                    logger.warning("  ! No recommendations available")
                
                # Get balance sheet (always fresh)
                try:
                    result['balance_sheet'] = yf_ticker.balance_sheet
                    logger.info(f"  ✓ Fetched balance sheet data")
                except:
                    result['balance_sheet'] = None
                    logger.warning("  ! No balance sheet available")
                
                # Get financials (always fresh)
                try:
                    result['financials'] = yf_ticker.financials
                    logger.info(f"  ✓ Fetched financial statements")
                except:
                    result['financials'] = None
                    logger.warning("  ! No financials available")
                
                # Get insider transactions (with monthly caching)
                if self._is_insider_transactions_cached_this_month(ticker):
                    cached_insider = self._load_insider_transactions_cache(ticker)
                    result['insider_transactions'] = cached_insider if cached_insider is not None else pd.DataFrame()
                    logger.info(f"  ⏭️  Using cached insider transactions ({len(result['insider_transactions'])} records)")
                else:
                    try:
                        result['insider_transactions'] = yf_ticker.insider_transactions if hasattr(yf_ticker, 'insider_transactions') else pd.DataFrame()
                        self._save_insider_transactions_cache(ticker, result['insider_transactions'])
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
