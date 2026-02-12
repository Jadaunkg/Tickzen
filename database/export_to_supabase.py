#!/usr/bin/env python3
"""
Production Supabase Data Exporter
==================================

Complete pipeline for collecting stock data and exporting to Supabase.
Uses existing pipeline for data collection, then transforms and exports
to all relevant Supabase tables.

Workflow:
--------
1. Collect data using PipelineDataCollector
2. Transform data using DataMapper
3. Export to Supabase using SupabaseClient
4. Log sync status and statistics
5. Handle errors gracefully

Usage:
-----
    python export_to_supabase.py AAPL
    python export_to_supabase.py AAPL GOOGL MSFT
"""

import os
import sys
import argparse
import logging
import time
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from database.pipeline_data_collector import PipelineDataCollector
from database.data_mapper import DataMapper
from database.supabase_client import SupabaseClient
from analysis_scripts.risk_analysis import RiskAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'supabase_export_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)

logger = logging.getLogger(__name__)


class SupabaseDataExporter:
    """
    Complete data export pipeline from collection to Supabase storage
    """
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize exporter with Supabase credentials
        
        Args:
            supabase_url: Supabase project URL (or from env)
            supabase_key: Supabase API key (or from env)
        """
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials required. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
        
        # Initialize components
        self.collector = PipelineDataCollector()
        self.mapper = DataMapper()
        self.db = SupabaseClient(url=self.supabase_url, key=self.supabase_key)
        self.risk_analyzer = RiskAnalyzer()
        
        logger.info("SupabaseDataExporter initialized successfully")
    
    def _get_latest_data_date(self, stock_id: int, table_name: str, date_column: str = 'date') -> str:
        """
        Get the latest date we have data for in the specified table
        
        Args:
            stock_id: Database ID of the stock
            table_name: Name of the table to check
            date_column: Name of the date column (default: 'date')
            
        Returns:
            Latest date as string (YYYY-MM-DD) or None if no data exists
        """
        try:
            result = self.db.client.table(table_name)\
                .select(date_column)\
                .eq('stock_id', stock_id)\
                .order(date_column, desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                latest_date = result.data[0][date_column]
                logger.info(f"  📅 Latest {table_name} date in DB: {latest_date}")
                return latest_date
            else:
                logger.info(f"  📅 No existing {table_name} data found - full export needed")
                return None
                
        except Exception as e:
            logger.warning(f"Error checking latest date in {table_name}: {e}")
            return None
    
    def _filter_new_data_only(self, data, latest_db_date: str, date_column: str = 'Date'):
        """
        Filter dataframe to only include records newer than the latest database date
        
        Args:
            data: pandas DataFrame with date column
            latest_db_date: Latest date we have in database (YYYY-MM-DD)
            date_column: Name of the date column in data
            
        Returns:
            Filtered DataFrame with only new records
        """
        try:
            import pandas as pd
            from datetime import datetime
            
            if data is None or data.empty or latest_db_date is None:
                return data
                
            # Convert date column to datetime for comparison
            data_dates = pd.to_datetime(data[date_column], errors='coerce')
            latest_db_datetime = pd.to_datetime(latest_db_date)
            
            # Filter to only dates after the latest database date
            mask = data_dates > latest_db_datetime
            new_data = data[mask].copy()
            
            original_count = len(data)
            new_count = len(new_data)
            
            if new_count > 0:
                logger.info(f"  📊 Incremental update: {original_count} total → {new_count} new records (after {latest_db_date})")
            else:
                logger.info(f"  ⏭️  No new data found after {latest_db_date} - skipping export")
            
            return new_data
            
        except Exception as e:
            logger.warning(f"Error filtering new data: {e}")
            return data  # Return original data if filtering fails
    
    def _filter_last_two_years(self, data, column_name='Date'):
        """
        Filter dataframe to only include the last 2 years of data
        
        Args:
            data: pandas DataFrame with date column
            column_name: Name of the date column (default: 'Date')
            
        Returns:
            Filtered DataFrame with last 2 years of data
        """
        try:
            import pandas as pd
            from datetime import datetime, timedelta
            
            if data is None or data.empty:
                return data
                
            # Convert to DataFrame if not already
            if not isinstance(data, pd.DataFrame):
                return data
                
            # Check if date column exists
            if column_name not in data.columns:
                logger.warning(f"Date column '{column_name}' not found, returning full dataset")
                return data
            
            # Calculate cutoff date (2 years ago from today)
            cutoff_date = datetime.now() - timedelta(days=730)  # 2 years = 730 days
            
            # Convert date column to datetime if needed
            date_col = pd.to_datetime(data[column_name], errors='coerce')
            
            # Filter to last 2 years
            mask = date_col >= cutoff_date
            filtered_data = data[mask].copy()
            
            original_count = len(data)
            filtered_count = len(filtered_data)
            
            logger.info(f"  📅 Filtered data: {original_count} → {filtered_count} rows (last 2 years only)")
            
            return filtered_data
            
        except Exception as e:
            logger.warning(f"Error filtering data to last 2 years: {e}")
            return data  # Return original data if filtering fails
    
    def _is_forecast_updated_this_month(self, stock_id: int) -> bool:
        """
        Check if forecast data has been updated for this stock in the current month
        
        Args:
            stock_id: Database ID of the stock
            
        Returns:
            True if forecast data exists for current month, False otherwise
        """
        try:
            from datetime import datetime
            current_month = datetime.now().strftime('%Y-%m')
            
            # Check if there's any forecast data for this stock created/updated this month
            result = self.db.client.table('forecast_data')\
                .select('forecast_date')\
                .eq('stock_id', stock_id)\
                .gte('created_at', f'{current_month}-01')\
                .limit(1)\
                .execute()
            
            has_data = bool(result.data)
            if has_data:
                logger.info(f"  ℹ Forecast data already updated this month ({current_month}) - skipping")
            
            return has_data
            
        except Exception as e:
            logger.warning(f"Error checking forecast update status: {e}")
            return False  # If we can't check, proceed with update to be safe
    
    def _is_company_profile_updated_this_month(self, stock_id: int) -> bool:
        """
        Check if company profile data has been updated for this stock in the current month
        
        Args:
            stock_id: Database ID of the stock
            
        Returns:
            True if company profile updated this month, False otherwise
        """
        try:
            from datetime import datetime
            current_month = datetime.now().strftime('%Y-%m')
            
            # Check if stock metadata was updated this month
            result = self.db.client.table('stocks')\
                .select('updated_at')\
                .eq('id', stock_id)\
                .gte('updated_at', f'{current_month}-01')\
                .limit(1)\
                .execute()
            
            has_data = bool(result.data)
            if has_data:
                logger.info(f"  ℹ Company profile already updated this month ({current_month}) - skipping")
            
            return has_data
            
        except Exception as e:
            logger.warning(f"Error checking company profile update status: {e}")
            return False
    
    def _is_insider_transactions_updated_this_month(self, stock_id: int) -> bool:
        """
        Check if insider transactions have been updated for this stock in the current month
        
        Args:
            stock_id: Database ID of the stock
            
        Returns:
            True if insider transactions updated this month, False otherwise
        """
        try:
            from datetime import datetime
            current_month = datetime.now().strftime('%Y-%m')
            
            # Check if there are any insider transactions for this stock created this month
            result = self.db.client.table('insider_transactions')\
                .select('transaction_date')\
                .eq('stock_id', stock_id)\
                .gte('created_at', f'{current_month}-01')\
                .limit(1)\
                .execute()
            
            has_data = bool(result.data)
            if has_data:
                logger.info(f"  ℹ Insider transactions already updated this month ({current_month}) - skipping")
            
            return has_data
            
        except Exception as e:
            logger.warning(f"Error checking insider transactions update status: {e}")
            return False
    
    def _get_latest_data_date(self, stock_id: int, table_name: str, date_column: str = 'date') -> str:
        """
        Get the latest date available in database for a stock's time-series data
        
        Args:
            stock_id: Database ID of the stock
            table_name: Name of the table to check (e.g., 'daily_price_data', 'technical_indicators') 
            date_column: Name of the date column (default: 'date')
            
        Returns:
            Latest date as string (YYYY-MM-DD) or None if no data exists
        """
        try:
            result = self.db.client.table(table_name)\
                .select(date_column)\
                .eq('stock_id', stock_id)\
                .order(date_column, desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                latest_date = result.data[0][date_column]
                logger.info(f"  📅 Latest {table_name} date in DB: {latest_date}")
                return latest_date
            else:
                logger.info(f"  📅 No existing {table_name} data found in DB - will export full dataset")
                return None
                
        except Exception as e:
            logger.warning(f"Error checking latest {table_name} date: {e}")
            return None
    
    def _filter_new_records_only(self, data, latest_db_date: str, date_column: str = 'Date'):
        """
        Filter dataframe to only include records newer than the latest database date
        
        Args:
            data: pandas DataFrame with date column
            latest_db_date: Latest date in database (YYYY-MM-DD) or None
            date_column: Name of the date column (default: 'Date')
            
        Returns:
            Filtered DataFrame with only new records
        """
        try:
            import pandas as pd
            from datetime import datetime
            
            if data is None or data.empty:
                return data
                
            if latest_db_date is None:
                # No existing data in DB - return full 2-year filtered dataset
                logger.info(f"  🆕 No existing data in DB - exporting full filtered dataset")
                return data
            
            # Convert to DataFrame if not already
            if not isinstance(data, pd.DataFrame):
                return data
                
            # Check if date column exists
            if date_column not in data.columns:
                logger.warning(f"Date column '{date_column}' not found, returning full dataset")
                return data
            
            # Convert dates for comparison
            data_dates = pd.to_datetime(data[date_column], errors='coerce')
            latest_db_datetime = pd.to_datetime(latest_db_date)
            
            # Filter to only records newer than latest DB date
            mask = data_dates > latest_db_datetime
            filtered_data = data[mask].copy()
            
            original_count = len(data)
            filtered_count = len(filtered_data)
            
            if filtered_count == 0:
                logger.info(f"  ✅ All data is already in DB - no new records to export")
            else:
                logger.info(f"  🆕 Filtered to new records only: {original_count} → {filtered_count} new records")
            
            return filtered_data
            
        except Exception as e:
            logger.warning(f"Error filtering new records: {e}")
            return data  # Return original data if filtering fails
    
    def export_stock_data(self, ticker: str) -> Dict:
        """
        Complete export workflow for a single stock
        
        Args:
            ticker: Stock symbol to export
            
        Returns:
            Dict with export results and statistics
        """
        start_time = time.time()
        
        result = {
            'ticker': ticker,
            'status': 'success',
            'errors': [],
            'records_exported': {},
            'duration_seconds': 0
        }
        
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"STARTING EXPORT: {ticker}")
            logger.info(f"{'='*80}\n")
            
            # Step 1: Collect data
            logger.info("PHASE 1: DATA COLLECTION")
            logger.info("-" * 40)
            
            collected_data = self.collector.collect_all_data(ticker)
            
            if collected_data['collection_status'] == 'failed':
                result['status'] = 'failed'
                result['errors'] = collected_data['errors']
                logger.error(f"Data collection failed for {ticker}")
                return result
            
            if collected_data['collection_status'] == 'partial':
                result['status'] = 'partial'
                result['errors'] = collected_data['errors']
                logger.warning(f"Data collection partially completed for {ticker}")
            
            # Validate collected data
            is_valid, issues = self.collector.validate_data(collected_data)
            if not is_valid:
                logger.warning(f"Data validation issues: {issues}")
                result['errors'].extend(issues)
                result['status'] = 'partial'
            
            # Step 2: Transform and export data
            logger.info("\nPHASE 2: DATA TRANSFORMATION & EXPORT")
            logger.info("-" * 40)
            
            # Reset mapper stats
            self.mapper.reset_sync_stats()
            
            # 2.1: Export stock metadata (company profile - monthly update)
            logger.info("\n[1/11] Exporting stock metadata...")
            
            # First, get or create basic stock record to get stock_id
            basic_stock_record = {
                'symbol': ticker,
                'ticker': ticker,
                'is_active': True,
                'sync_enabled': True
            }
            
            stock_result = self.db.client.table('stocks').upsert(
                basic_stock_record,
                on_conflict='symbol'
            ).execute()
            
            if not stock_result.data:
                raise Exception("Failed to insert/update basic stock record")
            
            stock_id = stock_result.data[0]['id']
            
            # Check if company profile needs updating this month
            if self._is_company_profile_updated_this_month(stock_id):
                logger.info("  ⏭️  Company profile already updated this month - skipping")
                result['records_exported']['stocks'] = 0  # Track as skipped
            else:
                # Update full company profile
                stock_record = self.mapper.map_stock_metadata(
                    ticker,
                    collected_data['info'],
                    collected_data['processed_data']
                )
                
                stock_result = self.db.client.table('stocks').upsert(
                    stock_record,
                    on_conflict='symbol'
                ).execute()
                
                logger.info(f"  ✓ Stock profile updated: ID = {stock_id}")
                result['records_exported']['stocks'] = 1
                self.mapper.sync_stats['records_inserted'] += 1
            
            # 2.2: Export daily price data (incremental - only new records)
            logger.info("\n[2/11] Exporting daily price data...")
            
            # First filter to last 2 years for database storage policy
            filtered_price_data = self._filter_last_two_years(
                collected_data['processed_data'], 
                'Date'
            )
            
            # Get latest date in database for this stock
            latest_price_date = self._get_latest_data_date(stock_id, 'daily_price_data', 'date')
            
            # Filter to only new records (newer than latest DB date)
            incremental_price_data = self._filter_new_records_only(
                filtered_price_data, 
                latest_price_date, 
                'Date'
            )
            
            if incremental_price_data is not None and len(incremental_price_data) > 0:
                price_records = self.mapper.map_daily_prices(
                    stock_id,
                    incremental_price_data
                )
                
                # Batch insert only new price records
                batch_size = 1000
                total_inserted = 0
                for i in range(0, len(price_records), batch_size):
                    batch = price_records[i:i+batch_size]
                    self.db.client.table('daily_price_data').upsert(
                        batch,
                        on_conflict='stock_id,date'
                    ).execute()
                    total_inserted += len(batch)
                    if len(price_records) > batch_size:  # Only show progress for large batches
                        logger.info(f"  Progress: {total_inserted}/{len(price_records)} records...")
                
                logger.info(f"  ✓ Exported {total_inserted} new price records")
                result['records_exported']['daily_price_data'] = total_inserted
                self.mapper.sync_stats['records_inserted'] += total_inserted
            else:
                logger.info(f"  ✅ No new price data to export")
                result['records_exported']['daily_price_data'] = 0
            
            # 2.3: Export technical indicators (incremental - only new records)
            logger.info("\n[3/11] Exporting technical indicators...")
            
            # Get latest date in database for this stock's technical indicators
            latest_indicators_date = self._get_latest_data_date(stock_id, 'technical_indicators', 'date')
            
            # Filter to only new records (newer than latest DB date)
            incremental_indicators_data = self._filter_new_records_only(
                filtered_price_data,  # Uses same data as price (filtered to 2 years) 
                latest_indicators_date, 
                'Date'
            )
            
            if incremental_indicators_data is not None and len(incremental_indicators_data) > 0:
                tech_records = self.mapper.map_technical_indicators(
                    stock_id,
                    incremental_indicators_data
                )
                
                # Batch insert only new indicator records
                total_inserted = 0
                for i in range(0, len(tech_records), batch_size):
                    batch = tech_records[i:i+batch_size]
                    self.db.client.table('technical_indicators').upsert(
                        batch,
                        on_conflict='stock_id,date'
                    ).execute()
                    total_inserted += len(batch)
                    if len(tech_records) > batch_size:  # Only show progress for large batches
                        logger.info(f"  Progress: {total_inserted}/{len(tech_records)} records...")
                
                logger.info(f"  ✓ Exported {total_inserted} new indicator records")
                result['records_exported']['technical_indicators'] = total_inserted
                self.mapper.sync_stats['records_inserted'] += total_inserted
            else:
                logger.info(f"  ✅ No new technical indicators to export")
                result['records_exported']['technical_indicators'] = 0
            
            # 2.4: Export analyst data (one record per stock)
            logger.info("\n[4/11] Exporting analyst data...")
            analyst_record = self.mapper.map_analyst_data(
                stock_id,
                collected_data['info']
            )
            
            self.db.client.table('analyst_data').upsert(
                [analyst_record],
                on_conflict='stock_id'
            ).execute()
            logger.info(f"  ✓ Exported analyst information")
            result['records_exported']['analyst_data'] = 1
            self.mapper.sync_stats['records_inserted'] += 1
            
            # 2.5: Export forecast data (12 monthly forecasts - updated monthly only)
            logger.info("\n[5/11] Exporting forecast data...")
            
            # Check if forecast data was already updated this month
            if self._is_forecast_updated_this_month(stock_id):
                logger.info("  ⏭️  Forecast data already updated this month - skipping")
                result['records_exported']['forecast_data'] = 0  # Track as skipped
            elif collected_data.get('forecast_data') is not None:
                forecast_records = self.mapper.map_forecast_data(
                    stock_id,
                    collected_data['forecast_data'],
                    collected_data['info']
                )
                
                if forecast_records:
                    # Delete existing forecasts for this stock first, then insert new
                    self.db.client.table('forecast_data').delete().eq('stock_id', stock_id).execute()
                    self.db.client.table('forecast_data').insert(forecast_records).execute()
                    logger.info(f"  ✓ Exported {len(forecast_records)} forecast records")
                    result['records_exported']['forecast_data'] = len(forecast_records)
                    self.mapper.sync_stats['records_inserted'] += len(forecast_records)
                else:
                    logger.info("  ℹ No forecast data to export")
            else:
                logger.info("  ℹ Forecast data not available")
            
            # 2.6: Export fundamental data
            logger.info("\n[6/12] Exporting fundamental data...")
            fundamental_record = self.mapper.map_fundamental_data(
                stock_id,
                collected_data['info'],
                collected_data.get('balance_sheet'),
                collected_data.get('financials')
            )
            
            self.db.client.table('fundamental_data').upsert(
                [fundamental_record],
                on_conflict='stock_id,period_date,period_type'
            ).execute()
            logger.info(f"  ✓ Exported fundamental metrics")
            result['records_exported']['fundamental_data'] = 1
            self.mapper.sync_stats['records_inserted'] += 1
            
            # 2.6b: Export quarterly fundamental data
            logger.info("\n[6b/12] Exporting quarterly fundamental data...")
            if collected_data.get('quarterly_earnings') is not None:
                quarterly_records = self.mapper.map_quarterly_fundamental_data(
                    stock_id,
                    collected_data['quarterly_earnings']
                )
                
                if quarterly_records:
                    self.db.client.table('fundamental_data').upsert(
                        quarterly_records,
                        on_conflict='stock_id,period_date,period_type'
                    ).execute()
                    logger.info(f"  ✓ Exported {len(quarterly_records)} quarterly fundamental records")
                    result['records_exported']['quarterly_fundamental_data'] = len(quarterly_records)
                    self.mapper.sync_stats['records_inserted'] += len(quarterly_records)
                else:
                    logger.info("  ℹ No quarterly fundamental data to export")
            else:
                logger.info("  ℹ Quarterly data not available")
            
            # 2.7: Export risk data (basic + advanced metrics)
            logger.info("\n[7/12] Exporting risk data...")
            
            # Calculate comprehensive risk profile using RiskAnalyzer
            risk_profile = None
            try:
                price_data = collected_data['processed_data']['Close']
                
                # Get market data (S&P 500) if available
                market_data = None
                if 'SP500' in collected_data['processed_data'].columns:
                    market_data = collected_data['processed_data']['SP500']
                
                # Calculate comprehensive risk profile
                risk_profile = self.risk_analyzer.comprehensive_risk_profile(
                    price_data=price_data,
                    market_data=market_data,
                    ticker=ticker
                )
                logger.info("  ✓ Calculated comprehensive risk profile")
            except Exception as e:
                logger.warning(f"  ⚠ Could not calculate comprehensive risk profile: {e}")
                risk_profile = None
            
            # Map and export basic risk data (includes CVaR and volatility)
            risk_record = self.mapper.map_risk_data(
                stock_id,
                collected_data['processed_data'],
                collected_data['info'],
                risk_profile=risk_profile,
                market_data=None,  # TODO: Add S&P 500 data if available
                ticker=ticker  # Pass ticker for liquidity/Altman metadata
            )
            
            self.db.client.table('risk_data').upsert(
                [risk_record],
                on_conflict='stock_id,date'
            ).execute()
            logger.info(f"  ✓ Exported enhanced risk metrics (basic)")
            result['records_exported']['risk_data'] = 1
            self.mapper.sync_stats['records_inserted'] += 1
            
            # Export advanced risk tables (if data available)
            if risk_profile:
                # 2.7a: Export liquidity risk data
                liquidity_record = self.mapper.map_liquidity_risk_data(stock_id, risk_profile)
                if liquidity_record:
                    self.db.client.table('liquidity_risk_data').upsert(
                        [liquidity_record],
                        on_conflict='stock_id,date'
                    ).execute()
                    logger.info(f"  ✓ Exported liquidity risk metrics")
                    result['records_exported']['liquidity_risk_data'] = 1
                    self.mapper.sync_stats['records_inserted'] += 1
                else:
                    logger.info("  ℹ No liquidity risk data available")
                
                # 2.7b: Export Altman Z-Score data
                altman_record = self.mapper.map_altman_zscore_data(stock_id, risk_profile)
                if altman_record:
                    self.db.client.table('altman_zscore_data').upsert(
                        [altman_record],
                        on_conflict='stock_id,date'
                    ).execute()
                    logger.info(f"  ✓ Exported Altman Z-Score metrics")
                    result['records_exported']['altman_zscore_data'] = 1
                    self.mapper.sync_stats['records_inserted'] += 1
                else:
                    logger.info("  ℹ No Altman Z-Score data available")
                
                # 2.7c: Export regime risk data
                regime_record = self.mapper.map_regime_risk_data(stock_id, risk_profile)
                if regime_record:
                    self.db.client.table('regime_risk_data').upsert(
                        [regime_record],
                        on_conflict='stock_id,date'
                    ).execute()
                    logger.info(f"  ✓ Exported regime risk metrics")
                    result['records_exported']['regime_risk_data'] = 1
                    self.mapper.sync_stats['records_inserted'] += 1
                else:
                    logger.info("  ℹ No regime risk data available")
            else:
                logger.info("  ℹ Skipping advanced risk exports (no risk profile)")
            
            # 2.8: Export market snapshot
            logger.info("\n[8/12] Exporting market snapshot...")
            snapshot_record = self.mapper.map_market_snapshot(
                stock_id,
                collected_data['current_price'],
                collected_data['info'],
                collected_data['processed_data']
            )
            
            self.db.client.table('market_price_snapshot').upsert(
                [snapshot_record],
                on_conflict='stock_id,date'
            ).execute()
            logger.info(f"  ✓ Exported market snapshot")
            result['records_exported']['market_price_snapshot'] = 1
            self.mapper.sync_stats['records_inserted'] += 1
            
            # 2.9: Export dividend data
            logger.info("\n[9/12] Exporting dividend data...")
            dividend_record = self.mapper.map_dividend_data(
                stock_id,
                collected_data['info']
            )
            
            if dividend_record.get('ex_dividend_date'):
                self.db.client.table('dividend_data').upsert(
                    [dividend_record],
                    on_conflict='stock_id,ex_dividend_date'
                ).execute()
                logger.info(f"  ✓ Exported dividend data")
                result['records_exported']['dividend_data'] = 1
                self.mapper.sync_stats['records_inserted'] += 1
            else:
                logger.info("  ℹ No dividend data available")
            
            # 2.10: Export ownership data
            logger.info("\n[10/12] Exporting ownership data...")
            ownership_record = self.mapper.map_ownership_data(
                stock_id,
                collected_data['info']
            )
            
            self.db.client.table('ownership_data').upsert(
                [ownership_record],
                on_conflict='stock_id,report_date'
            ).execute()
            logger.info(f"  ✓ Exported ownership data")
            result['records_exported']['ownership_data'] = 1
            self.mapper.sync_stats['records_inserted'] += 1
            
            # 2.11: Export sentiment data
            logger.info("\n[11/12] Exporting sentiment data...")
            sentiment_record = self.mapper.map_sentiment_data(
                stock_id,
                collected_data.get('news', []),
                collected_data['info']
            )
            
            self.db.client.table('sentiment_data').upsert(
                [sentiment_record],
                on_conflict='stock_id,date'
            ).execute()
            logger.info(f"  ✓ Exported sentiment data")
            result['records_exported']['sentiment_data'] = 1
            self.mapper.sync_stats['records_inserted'] += 1
            
            # 2.12: Export insider transactions (monthly update)
            logger.info("\n[12/12] Exporting insider transactions...")
            
            # Check if insider transactions were already updated this month
            if self._is_insider_transactions_updated_this_month(stock_id):
                logger.info("  ⏭️  Insider transactions already updated this month - skipping")
                result['records_exported']['insider_transactions'] = 0  # Track as skipped
            elif collected_data.get('insider_transactions') is not None and not collected_data['insider_transactions'].empty:
                insider_records = self.mapper.map_insider_transactions(
                    stock_id,
                    collected_data['insider_transactions']
                )
                
                if insider_records:
                    # Batch insert insider transactions
                    total_inserted = 0
                    batch_size = 1000
                    for i in range(0, len(insider_records), batch_size):
                        batch = insider_records[i:i+batch_size]
                        self.db.client.table('insider_transactions').insert(batch).execute()
                        total_inserted += len(batch)
                    
                    logger.info(f"  ✓ Exported {total_inserted} insider transactions")
                    result['records_exported']['insider_transactions'] = total_inserted
                    self.mapper.sync_stats['records_inserted'] += total_inserted
                else:
                    logger.info("  ℹ No insider transactions to export")
            else:
                logger.info("  ℹ Insider transactions data not available")
            
            # 2.13: Export peer comparison data
            logger.info("\n[13/13] Exporting peer comparison data...")
            if collected_data.get('peer_comparison'):
                peer_records = self.mapper.map_peer_comparison_data(
                    stock_id,
                    collected_data['peer_comparison'],
                    ticker
                )
                
                if peer_records:
                    # Delete existing peer data for this stock
                    self.db.client.table('peer_comparison_data').delete().eq('stock_id', stock_id).execute()
                    
                    # Insert new peer data
                    self.db.client.table('peer_comparison_data').upsert(
                        peer_records,
                        on_conflict='stock_id,peer_ticker'
                    ).execute()
                    logger.info(f"  ✓ Exported {len(peer_records)} peer comparison records")
                    result['records_exported']['peer_comparison_data'] = len(peer_records)
                    self.mapper.sync_stats['records_inserted'] += len(peer_records)
                else:
                    logger.info("  ℹ No peer comparison data to export")
            else:
                logger.info("  ℹ Peer comparison data not available")
            
            # Step 3: Create sync log
            logger.info("\nPHASE 3: SYNC LOGGING")
            logger.info("-" * 40)
            
            duration = int(time.time() - start_time)
            sync_log = self.mapper.create_sync_log(
                stock_id=stock_id,
                sync_type='full_history',
                sync_status=result['status'],
                error_message='; '.join(result['errors']) if result['errors'] else None,
                sync_duration=duration
            )
            
            self.db.client.table('data_sync_log').insert(sync_log).execute()
            logger.info(f"  ✓ Sync log created")
            
            # Calculate total records
            total_records = sum(result['records_exported'].values())
            result['duration_seconds'] = duration
            
            # Final summary
            logger.info(f"\n{'='*80}")
            logger.info(f"EXPORT COMPLETE: {ticker}")
            logger.info(f"{'='*80}")
            logger.info(f"Status: {result['status'].upper()}")
            logger.info(f"Duration: {duration} seconds")
            logger.info(f"Total Records: {total_records}")
            logger.info(f"Errors: {len(result['errors'])}")
            
            logger.info("\nRecords by Table:")
            for table, count in result['records_exported'].items():
                logger.info(f"  • {table}: {count}")
            
            if result['errors']:
                logger.info("\nErrors Encountered:")
                for error in result['errors']:
                    logger.info(f"  • {error}")
            
            logger.info(f"{'='*80}\n")
            
            return result
            
        except Exception as e:
            duration = int(time.time() - start_time)
            error_msg = f"Critical export error: {e}"
            result['status'] = 'failed'
            result['errors'].append(error_msg)
            result['duration_seconds'] = duration
            
            logger.error(f"\n✗ {error_msg}")
            logger.exception("Full traceback:")
            
            return result
    
    def export_multiple_stocks(self, tickers: List[str]) -> Dict:
        """
        Export data for multiple stocks
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            Dict with aggregated results
        """
        results = {
            'total': len(tickers),
            'successful': 0,
            'partial': 0,
            'failed': 0,
            'details': {}
        }
        
        for ticker in tickers:
            result = self.export_stock_data(ticker)
            results['details'][ticker] = result
            
            if result['status'] == 'success':
                results['successful'] += 1
            elif result['status'] == 'partial':
                results['partial'] += 1
            else:
                results['failed'] += 1
        
        # Print summary
        logger.info(f"\n{'='*80}")
        logger.info("BATCH EXPORT SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Total Stocks: {results['total']}")
        logger.info(f"Successful: {results['successful']}")
        logger.info(f"Partial: {results['partial']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info(f"{'='*80}\n")
        
        return results


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='Export stock data to Supabase',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Export single stock:
    python export_to_supabase.py AAPL
  
  Export multiple stocks:
    python export_to_supabase.py AAPL GOOGL MSFT TSLA
        """
    )
    
    parser.add_argument(
        'tickers',
        nargs='+',
        help='Stock ticker symbols to export (e.g., AAPL GOOGL MSFT)'
    )
    
    parser.add_argument(
        '--url',
        help='Supabase project URL (default: from SUPABASE_URL env var)'
    )
    
    parser.add_argument(
        '--key',
        help='Supabase API key (default: from SUPABASE_KEY env var)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize exporter
        exporter = SupabaseDataExporter(
            supabase_url=args.url,
            supabase_key=args.key
        )
        
        # Export data
        if len(args.tickers) == 1:
            result = exporter.export_stock_data(args.tickers[0])
            sys.exit(0 if result['status'] in ['success', 'partial'] else 1)
        else:
            results = exporter.export_multiple_stocks(args.tickers)
            sys.exit(0 if results['failed'] == 0 else 1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception("Traceback:")
        sys.exit(1)


if __name__ == '__main__':
    main()
