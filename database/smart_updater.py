#!/usr/bin/env python3
"""
Smart Stock Data Updater
=========================

Intelligent update system that knows:
1. Which tables to update daily vs weekly vs monthly
2. When a stock is NEW (needs full historical load)
3. When a stock is EXISTING (needs only incremental update)
4. Which data has actually changed

Table Classification:
- DAILY: daily_price_data, technical_indicators, market_price_snapshot, sentiment_data
- WEEKLY: forecast_data, risk_data, analyst_data
- MONTHLY: fundamental_data, dividend_data, ownership_data, insider_transactions
- STATIC: stocks (metadata only)

Performance:
- NEW stock: 30-60s (one-time full load)
- EXISTING stock: 3-5s (daily incremental)
- 500 stocks: ~35 minutes (vs 4+ hours)
"""

import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from pathlib import Path
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import SupabaseClient
from database.data_mapper import DataMapper
from database.pipeline_data_collector import PipelineDataCollector
from data_processing_scripts.data_collection import fetch_real_time_data, get_current_market_price
from data_processing_scripts.data_preprocessing import preprocess_data
from data_processing_scripts.macro_data import fetch_macro_indicators

logger = logging.getLogger(__name__)


class UpdateFrequency(Enum):
    """Update frequencies for different table types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    STATIC = "static"


class TableUpdateConfig:
    """Configuration for which tables to update at which frequency"""
    
    # Tables that MUST be updated every trading day
    DAILY_TABLES = {
        'daily_price_data',
        'technical_indicators',
        'market_price_snapshot',
        'sentiment_data',
    }
    
    # Tables that should be updated weekly
    WEEKLY_TABLES = {
        'forecast_data',
        'risk_data',
        'analyst_data',
    }
    
    # Tables that should be updated monthly
    MONTHLY_TABLES = {
        'ownership_data',
        'peer_comparison_data',
    }
    
    # Tables that should be updated quarterly (with financial statements)
    QUARTERLY_TABLES = {
        'fundamental_data',
    }
    
    # Tables updated when events occur
    EVENT_TABLES = {
        'dividend_data',  # When dividend declared
        'insider_transactions',  # When trade filed
    }
    
    # Static/metadata tables (rarely change)
    STATIC_TABLES = {
        'stocks',  # Company metadata
    }
    
    # Audit table (always updated)
    AUDIT_TABLES = {
        'data_sync_log',
    }


class SmartStockUpdater:
    """
    Intelligent stock data updater that determines update strategy
    based on stock status (new/existing) and table requirements.
    """
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize smart updater
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
        """
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials required")
        
        self.db = SupabaseClient(url=self.supabase_url, key=self.supabase_key)
        self.mapper = DataMapper()
        self.collector = PipelineDataCollector()
        self.config = TableUpdateConfig()
        
        logger.info("SmartStockUpdater initialized")
    
    def is_new_stock(self, ticker: str) -> bool:
        """
        Check if this is a new stock (not in database)
        
        Args:
            ticker: Stock symbol
            
        Returns:
            True if new stock, False if exists
        """
        stock = self.db.get_stock_by_symbol(ticker)
        return stock is None
    
    def should_update_today(self, ticker: str, force_intraday: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Determine if stock needs updating today
        
        Args:
            ticker: Stock symbol
            force_intraday: Allow intraday updates during market hours
            
        Returns:
            Tuple of (should_update, reason)
        """
        # New stocks always need full load
        if self.is_new_stock(ticker):
            return True, "NEW STOCK - needs full historical load"
        
        # Get stock record
        stock = self.db.get_stock_by_symbol(ticker)
        
        # Check last sync date
        last_sync = stock.get('last_sync_date')
        if not last_sync:
            return True, "No previous sync found"
        
        # Parse last sync datetime (not just date)
        if isinstance(last_sync, str):
            try:
                # Handle different datetime formats from database
                if last_sync.endswith('Z'):
                    # Has Z suffix (UTC indicator)
                    last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                elif '+' in last_sync or last_sync.endswith('00:00'):
                    # Already has timezone info
                    last_sync_dt = datetime.fromisoformat(last_sync)
                else:
                    # No timezone info - database appears to be in Indian timezone
                    last_sync_dt = datetime.fromisoformat(last_sync)
                    ist = pytz.timezone('Asia/Kolkata')
                    last_sync_dt = ist.localize(last_sync_dt)
            except:
                try:
                    last_sync_dt = datetime.strptime(last_sync, '%Y-%m-%d %H:%M:%S')
                    ist = pytz.timezone('Asia/Kolkata')
                    last_sync_dt = ist.localize(last_sync_dt)
                except:
                    last_sync_dt = datetime.strptime(last_sync, '%Y-%m-%d')
        else:
            last_sync_dt = last_sync
        
        today = date.today()
        now = datetime.now()
        
        # Get current time in US Eastern timezone for market checks
        et = pytz.timezone('US/Eastern')
        now_et = datetime.now(et)
        
        # Check if it's a weekend (no trading) - use ET timezone
        if now_et.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False, f"Weekend - market closed (ET: {now_et.strftime('%A %H:%M')})"
        
        # Get last sync date (not datetime)
        last_sync_date = last_sync_dt.date() if hasattr(last_sync_dt, 'date') else last_sync_dt
        
        # If never updated today, definitely update
        if last_sync_date < today:
            return True, f"Last sync: {last_sync_date}, needs daily update"
        
        # ENHANCED CHECK: Even if synced today, check if we have actual data for today
        if last_sync_date == today:
            stock_id = stock['id']
            last_data_date = self.get_last_data_date(stock_id)
            
            # If no data for today despite sync timestamp, we need to update
            if last_data_date is None or last_data_date < today:
                return True, f"Synced today but no data for {today} (last data: {last_data_date})"
        
        # Already updated today - check if we should update intraday
        if force_intraday and last_sync_date == today:
            # Get current time in US Eastern timezone
            et = pytz.timezone('US/Eastern')
            now_et = datetime.now(et)
            
            # Check if it's during market hours (9:30 AM - 4:00 PM ET)
            current_hour_et = now_et.hour
            
            # Market hours check (9 AM - 5 PM EST/EDT)
            if 9 <= current_hour_et <= 17:
                # Convert last_sync to ET for proper comparison  
                # Handle timezone conversion - database stores IST timestamps
                if last_sync_dt.tzinfo is None:
                    # If no timezone, assume IST (database timezone)
                    ist = pytz.timezone('Asia/Kolkata')
                    last_sync_dt = ist.localize(last_sync_dt)
                
                # Convert to ET for comparison
                last_sync_et = last_sync_dt.astimezone(et)
                
                # Check time since last update (ensure both times are timezone-aware)
                hours_since_update = (now_et - last_sync_et).total_seconds() / 3600
                
                if hours_since_update >= 1:  # Update if more than 1 hour since last update
                    return True, f"Intraday update: {hours_since_update:.1f}h since last sync during market hours (ET: {now_et.strftime('%H:%M')})"
                else:
                    return False, f"Recently updated {hours_since_update:.1f}h ago during market hours (ET: {now_et.strftime('%H:%M')})"
            else:
                return False, f"Already updated today ({last_sync_date}) - market closed (ET: {now_et.strftime('%H:%M')})"
        
        return False, f"Already updated today ({last_sync_date})"
    
    def get_last_data_date(self, stock_id: int, table: str = 'daily_price_data') -> Optional[date]:
        """
        Get the most recent date in database for a stock in a specific table
        
        Args:
            stock_id: Stock database ID
            table: Table name to check
            
        Returns:
            Last date or None
        """
        try:
            result = self.db.client.table(table)\
                .select('date')\
                .eq('stock_id', stock_id)\
                .order('date', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                last_date_str = result.data[0]['date']
                # Handle both date and datetime strings
                if 'T' in last_date_str:
                    return datetime.fromisoformat(last_date_str).date()
                else:
                    return datetime.strptime(last_date_str, '%Y-%m-%d').date()
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not get last date for stock_id {stock_id} in {table}: {e}")
            return None
    
    def initial_load_new_stock(self, ticker: str) -> Dict:
        """
        Full historical data load for a NEW stock
        Loads ALL tables with complete 10-year history
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dict with load results
        """
        ticker = ticker.upper()
        start_time = datetime.now()
        
        result = {
            'ticker': ticker,
            'status': 'success',
            'is_new_stock': True,
            'records_inserted': {},
            'errors': [],
            'duration_seconds': 0
        }
        
        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"INITIAL LOAD - NEW STOCK: {ticker}")
            logger.info(f"{'='*70}")
            logger.info("Loading 10 years of historical data...")
            
            # Collect complete data using full pipeline
            logger.info("\n[Phase 1/3] Collecting complete historical data...")
            collected_data = self.collector.collect_all_data(ticker)
            
            if collected_data['collection_status'] == 'failed':
                result['status'] = 'failed'
                result['errors'] = collected_data['errors']
                return result
            
            logger.info("\n[Phase 2/3] Mapping to database schema...")
            
            # 1. Insert stock metadata
            logger.info("  [1/12] Inserting stock metadata...")
            stock_record = self.mapper.map_stock_metadata(
                ticker,
                collected_data['info'],
                collected_data['processed_data']
            )
            
            stock_result = self.db.client.table('stocks').upsert(
                stock_record,
                on_conflict='symbol'
            ).execute()
            
            stock_id = stock_result.data[0]['id']
            result['records_inserted']['stocks'] = 1
            logger.info(f"    ✓ Stock registered: ID = {stock_id}")
            
            # 2. Insert daily price data (bulk)
            logger.info("  [2/12] Inserting daily price data...")
            price_records = self.mapper.map_daily_prices(
                stock_id,
                collected_data['processed_data']
            )
            
            # Batch insert in chunks
            batch_size = 1000
            total = 0
            for i in range(0, len(price_records), batch_size):
                batch = price_records[i:i+batch_size]
                self.db.client.table('daily_price_data').upsert(
                    batch,
                    on_conflict='stock_id,date'
                ).execute()
                total += len(batch)
            
            result['records_inserted']['daily_price_data'] = total
            logger.info(f"    ✓ Inserted {total} price records")
            
            # 3. Insert technical indicators (bulk)
            logger.info("  [3/12] Inserting technical indicators...")
            tech_records = self.mapper.map_technical_indicators(
                stock_id,
                collected_data['processed_data']
            )
            
            total = 0
            for i in range(0, len(tech_records), batch_size):
                batch = tech_records[i:i+batch_size]
                self.db.client.table('technical_indicators').upsert(
                    batch,
                    on_conflict='stock_id,date'
                ).execute()
                total += len(batch)
            
            result['records_inserted']['technical_indicators'] = total
            logger.info(f"    ✓ Inserted {total} technical records")
            
            # 4. Insert fundamental data
            logger.info("  [4/12] Inserting fundamental data...")
            fund_records = self.mapper.map_fundamental_data(
                stock_id,
                collected_data['info']
            )
            
            if fund_records:
                self.db.client.table('fundamental_data').upsert(
                    fund_records,
                    on_conflict='stock_id,period_date,period_type'
                ).execute()
                result['records_inserted']['fundamental_data'] = len(fund_records) if isinstance(fund_records, list) else 1
                logger.info(f"    ✓ Inserted fundamental data")
            
            # 5. Insert forecast data
            logger.info("  [5/12] Inserting forecast data...")
            forecast_record = self.mapper.map_forecast_data(
                stock_id,
                collected_data.get('forecast_data'),
                collected_data.get('info')
            )
            
            if forecast_record:
                self.db.client.table('forecast_data').upsert(
                    forecast_record,
                    on_conflict='stock_id,forecast_date'
                ).execute()
                result['records_inserted']['forecast_data'] = 1
                logger.info(f"    ✓ Inserted forecast data")
            
            # 6. Insert risk data
            logger.info("  [6/12] Inserting risk data...")
            risk_record = self.mapper.map_risk_data(
                stock_id,
                collected_data['processed_data'],
                collected_data['info'],
                risk_profile=None,
                market_data=None,  # TODO: Add S&P 500 data if available
                ticker=ticker  # Pass ticker for liquidity/Altman metadata
            )
            
            if risk_record:
                self.db.client.table('risk_data').upsert(
                    risk_record,
                    on_conflict='stock_id,date'
                ).execute()
                result['records_inserted']['risk_data'] = 1
                logger.info(f"    ✓ Inserted risk data")
            
            # 7. Insert market price snapshot
            logger.info("  [7/12] Inserting market price snapshot...")
            snapshot_record = self.mapper.map_market_price_snapshot(
                stock_id,
                collected_data['processed_data'],
                collected_data.get('current_price'),
                collected_data['info']
            )
            
            self.db.client.table('market_price_snapshot').upsert(
                snapshot_record,
                on_conflict='stock_id'
            ).execute()
            result['records_inserted']['market_price_snapshot'] = 1
            logger.info(f"    ✓ Inserted market snapshot")
            
            # 8. Insert dividend data
            logger.info("  [8/12] Inserting dividend data...")
            div_record = self.mapper.map_dividend_data(
                stock_id,
                collected_data['info']
            )
            
            if div_record:
                self.db.client.table('dividend_data').upsert(
                    div_record,
                    on_conflict='stock_id,ex_dividend_date'
                ).execute()
                result['records_inserted']['dividend_data'] = 1
                logger.info(f"    ✓ Inserted dividend data")
            
            # 9. Insert ownership data
            logger.info("  [9/12] Inserting ownership data...")
            own_record = self.mapper.map_ownership_data(
                stock_id,
                collected_data['info']
            )
            
            if own_record:
                self.db.client.table('ownership_data').upsert(
                    own_record,
                    on_conflict='stock_id,report_date'
                ).execute()
                result['records_inserted']['ownership_data'] = 1
                logger.info(f"    ✓ Inserted ownership data")
            
            # 10. Insert sentiment data
            logger.info("  [10/12] Inserting sentiment data...")
            sent_record = self.mapper.map_sentiment_data(
                stock_id,
                collected_data.get('news', []),
                collected_data['info']
            )
            
            if sent_record:
                self.db.client.table('sentiment_data').upsert(
                    sent_record,
                    on_conflict='stock_id,date'
                ).execute()
                result['records_inserted']['sentiment_data'] = 1
                logger.info(f"    ✓ Inserted sentiment data")
            
            # 11. Insert insider transactions
            logger.info("  [11/12] Inserting insider transactions...")
            insider_records = self.mapper.map_insider_transactions(
                stock_id,
                collected_data.get('insider_transactions', pd.DataFrame())
            )
            
            if insider_records:
                self.db.client.table('insider_transactions').insert(
                    insider_records
                ).execute()
                result['records_inserted']['insider_transactions'] = len(insider_records )
                logger.info(f"    ✓ Inserted {len(insider_records)} insider transactions")
            
            # 12. Insert analyst data
            logger.info("  [12/12] Inserting analyst data...")
            analyst_record = self.mapper.map_analyst_data(
                stock_id,
                collected_data['info']
            )
            
            if analyst_record:
                self.db.client.table('analyst_data').upsert(
                    analyst_record,
                    on_conflict='stock_id'
                ).execute()
                result['records_inserted']['analyst_data'] = 1
                logger.info(f"    ✓ Inserted analyst data")
            
            logger.info("\n[Phase 3/3] Logging sync...")
            
            # Log to data_sync_log
            duration = (datetime.now() - start_time).total_seconds()
            total_records = sum(result['records_inserted'].values())
            
            sync_log = {
                'stock_id': stock_id,
                'sync_type': 'full_history',
                'sync_date': datetime.now().isoformat(),
                'records_inserted': total_records,
                'records_updated': 0,
                'records_deleted': 0,
                'records_failed': len(result['errors']),
                'sync_status': result['status'],
                'error_message': '; '.join(result['errors']) if result['errors'] else None,
                'sync_duration_seconds': int(duration),
                'data_quality_score': 1.0,
                'source_api': 'yfinance',
                'api_version': '0.2.x'
            }
            
            self.db.client.table('data_sync_log').insert(sync_log).execute()
            
            result['duration_seconds'] = round(duration, 2)
            result['status'] = 'success'
            
            logger.info(f"\n{'='*70}")
            logger.info(f"✓ INITIAL LOAD COMPLETE")
            logger.info(f"  Duration: {duration:.2f}s")
            logger.info(f"  Total records: {total_records}")
            logger.info(f"{'='*70}\n")
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"Initial load failed: {e}"
            result['status'] = 'failed'
            result['errors'].append(error_msg)
            result['duration_seconds'] = round(duration, 2)
            
            logger.error(f"\n✗ {error_msg}", exc_info=True)
            
            return result
    
    def daily_update_existing_stock(self, ticker: str, force: bool = False, force_intraday: bool = False) -> Dict:
        """
        Fast incremental update for EXISTING stock
        Only updates DAILY tables with NEW data
        
        Args:
            ticker: Stock symbol
            force: Force update even if already done
            force_intraday: Force intraday update during market hours
            
        Returns:
            Dict with update results
        """
        ticker = ticker.upper()
        start_time = datetime.now()
        
        result = {
            'ticker': ticker,
            'status': 'success',
            'is_new_stock': False,
            'updated': False,
            'records_inserted': {},
            'errors': [],
            'duration_seconds': 0
        }
        
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"DAILY UPDATE: {ticker}")
            logger.info(f"{'='*60}")
            
            # Check if update needed
            if not force:
                should_update, reason = self.should_update_today(ticker, force_intraday=force_intraday)
                logger.info(f"Update check: {reason}")
                
                if not should_update:
                    result['status'] = 'skipped'
                    result['message'] = reason
                    return result
            
            # Get stock record
            stock = self.db.get_stock_by_symbol(ticker)
            stock_id = stock['id']
            
            # Get last data date
            last_date = self.get_last_data_date(stock_id)
            logger.info(f"Last data date in DB: {last_date}")
            
            # Determine date ranges
            # For technical indicators, we need at least 250 days of context (for 200-day MA)
            # But we'll only INSERT records after last_date
            if last_date:
                # Fetch 250 days back for technical indicator calculation context (200-day MA + buffer)
                fetch_start_date = last_date - timedelta(days=250)
                # But only insert records after last_date
                insert_after_date = last_date
            else:
                # No data in DB - fetch 1 year
                fetch_start_date = date.today() - timedelta(days=365)
                insert_after_date = None  # Insert all
            
            end_date = date.today() + timedelta(days=1)
            
            logger.info(f"Fetching data from {fetch_start_date} to {end_date} (for context)...")
            logger.info(f"Will insert only records after: {insert_after_date}")
            
            # Get yfinance data (with context for indicators)
            yf_ticker = yf.Ticker(ticker)
            hist_data = yf_ticker.history(start=fetch_start_date, end=end_date)
            
            if hist_data.empty:
                result['status'] = 'no_new_data'
                result['message'] = 'No data available'
                logger.info("No data available")
                return result
            
            hist_data = hist_data.reset_index()
            logger.info(f"Fetched {len(hist_data)} records total (includes context)")
            
            # Filter to only NEW records for insertion
            if insert_after_date:
                hist_data['Date'] = pd.to_datetime(hist_data['Date']).dt.date
                
                # For intraday updates, replace today's data if it exists
                today = date.today()
                if insert_after_date == today:
                    # Replace today's data
                    new_records = hist_data[hist_data['Date'] >= today]
                    logger.info(f"Intraday update: Replacing today's data ({len(new_records)} records)")
                    
                    # Delete today's existing data first
                    try:
                        self.db.client.table('daily_price_data').delete().eq('stock_id', stock_id).eq('date', today.isoformat()).execute()
                        self.db.client.table('technical_indicators').delete().eq('stock_id', stock_id).eq('date', today.isoformat()).execute()
                        logger.info("Deleted existing today's data for replacement")
                    except Exception as e:
                        logger.warning(f"Could not delete existing today's data: {e}")
                else:
                    # Normal case - only new data after last date
                    new_records = hist_data[hist_data['Date'] > insert_after_date]
                
                if new_records.empty:
                    result['status'] = 'no_new_data'
                    result['message'] = f'No new data after {insert_after_date}'
                    logger.info(f"No new data after {insert_after_date}")
                    
                    # Update stock metadata even when no new data (to track last check)
                    self.db.client.table('stocks').update({
                        'last_sync_date': datetime.now().isoformat(),
                        'last_sync_status': 'no_new_data',
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', stock_id).execute()
                    
                    return result
                logger.info(f"Found {len(new_records)} records to insert/update")
            else:
                new_records = hist_data
            
            # Get current price
            current_price = get_current_market_price(ticker)
            info = yf_ticker.info or {}
            
            # Calculate technical indicators on FULL dataset (with context)
            app_root = Path(__file__).parent.parent  # tickzen2 directory
            macro_data = fetch_macro_indicators(app_root=str(app_root), stock_data=hist_data)
            processed_data = preprocess_data(hist_data, macro_data)
            
            # Debug: Check processed data
            logger.info(f"Processed data total records: {len(processed_data)}")
            if not processed_data.empty:
                processed_data['Date'] = pd.to_datetime(processed_data['Date']).dt.date
                logger.info(f"Date range in processed data: {processed_data['Date'].min()} to {processed_data['Date'].max()}")
            
            # Filter processed_data to only NEW records for insertion
            if insert_after_date:
                processed_new_records = processed_data[processed_data['Date'] > insert_after_date]
                logger.info(f"Processed data: {len(processed_new_records)} new records after filtering (date > {insert_after_date})")
                if len(processed_new_records) > 0:
                    logger.info(f"New records date range: {processed_new_records['Date'].min()} to {processed_new_records['Date'].max()}")
            else:
                processed_new_records = processed_data
            
            # Update DAILY tables only (with NEW records only)
            logger.info(f"\nUpdating DAILY tables...")
            
            # 1. daily_price_data
            logger.info("  [1/4] Updating daily_price_data...")
            price_records = self.mapper.map_daily_prices(stock_id, processed_new_records)
            
            if price_records:
                self.db.client.table('daily_price_data').upsert(
                    price_records,
                    on_conflict='stock_id,date'
                ).execute()
                result['records_inserted']['daily_price_data'] = len(price_records)
                logger.info(f"    ✓ Updated {len(price_records)} price records")
            
            # 2. technical_indicators
            logger.info("  [2/4] Updating technical_indicators...")
            tech_records = self.mapper.map_technical_indicators(stock_id, processed_new_records)
            
            if tech_records:
                self.db.client.table('technical_indicators').upsert(
                    tech_records,
                    on_conflict='stock_id,date'
                ).execute()
                result['records_inserted']['technical_indicators'] = len(tech_records)
                logger.info(f"    ✓ Updated {len(tech_records)} technical records")
            
            # 3. market_price_snapshot (always update - it's the current state)
            # Use full processed_data for snapshot (needs latest values)
            logger.info("  [3/4] Updating market_price_snapshot...")
            snapshot_record = self.mapper.map_market_snapshot(
                stock_id,
                current_price,
                info,
                processed_data  # Use full processed data for snapshot calculations
            )
            
            # Use update instead of upsert for market_price_snapshot
            # (table may not have unique constraint on stock_id)
            self.db.client.table('market_price_snapshot').update(
                snapshot_record
            ).eq('stock_id', stock_id).execute()
            result['records_inserted']['market_price_snapshot'] = 1
            logger.info(f"    ✓ Updated market snapshot")
            
            # 4. sentiment_data (if news available)
            logger.info("  [4/4] Updating sentiment_data...")
            try:
                news = yf_ticker.news if hasattr(yf_ticker, 'news') else []
                if news:
                    sent_record = self.mapper.map_sentiment_data(stock_id, news, info)
                    if sent_record:
                        self.db.client.table('sentiment_data').upsert(
                            sent_record,
                            on_conflict='stock_id,date'
                        ).execute()
                        result['records_inserted']['sentiment_data'] = 1
                        logger.info(f"    ✓ Updated sentiment data")
            except Exception as e:
                logger.warning(f"    ! Could not update sentiment: {e}")
            
            # Update stock metadata (last sync time)
            self.db.client.table('stocks').update({
                'last_sync_date': datetime.now().isoformat(),
                'last_sync_status': 'success',
                'updated_at': datetime.now().isoformat()
            }).eq('id', stock_id).execute()
            
            # Log to data_sync_log
            duration = (datetime.now() - start_time).total_seconds()
            total_records = sum(result['records_inserted'].values())
            
            sync_log = {
                'stock_id': stock_id,
                'sync_type': 'daily',
                'sync_date': datetime.now().isoformat(),
                'records_inserted': total_records,
                'records_updated': 0,
                'records_deleted': 0,
                'records_failed': 0,
                'sync_status': 'success',
                'sync_duration_seconds': int(duration),
                'data_quality_score': 1.0,
                'source_api': 'yfinance',
                'api_version': '0.2.x'
            }
            
            self.db.client.table('data_sync_log').insert(sync_log).execute()
            
            result['updated'] = True
            result['duration_seconds'] = round(duration, 2)
            
            logger.info(f"\n✓ Update completed in {duration:.2f}s")
            logger.info(f"  Total records updated: {total_records}")
            logger.info(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"Daily update failed: {e}"
            result['status'] = 'failed'
            result['errors'].append(error_msg)
            result['duration_seconds'] = round(duration, 2)
            
            logger.error(f"\n✗ {error_msg}", exc_info=True)
            
            return result
    
    def update_stock(self, ticker: str, force: bool = False) -> Dict:
        """
        Smart update: automatically determines if stock is new or existing
        and applies appropriate update strategy
        
        Args:
            ticker: Stock symbol
            force: Force update even if already done
            
        Returns:
            Dict with update results
        """
        # Detect if this is a new stock
        if self.is_new_stock(ticker):
            logger.info(f"Detected NEW stock: {ticker}")
            return self.initial_load_new_stock(ticker)
        else:
            logger.info(f"Detected EXISTING stock: {ticker}")
            return self.daily_update_existing_stock(ticker, force=force)
    
    def update_multiple_stocks(self, tickers: List[str],
                               delay_between: float = 1.0) -> Dict:
        """
        Update multiple stocks with smart detection
        
        Args:
            tickers: List of stock symbols
            delay_between: Seconds to wait between stocks
            
        Returns:
            Dict with batch results
        """
        start_time = datetime.now()
        
        results = {
            'total': len(tickers),
            'new_stocks': 0,
            'existing_stocks': 0,
            'updated': 0,
            'skipped': 0,
            'no_new_data': 0,
            'failed': 0,
            'details': {}
        }
        
        logger.info(f"\n{'='*70}")
        logger.info(f"SMART BATCH UPDATE - {len(tickers)} stocks")
        logger.info(f"{'='*70}\n")
        
        for i, ticker in enumerate(tickers, 1):
            logger.info(f"[{i}/{len(tickers)}] Processing {ticker}...")
            
            try:
                # Smart update (auto-detects new vs existing)
                result = self.update_stock(ticker)
                results['details'][ticker] = result
                
                # Track stats
                if result.get('is_new_stock'):
                    results['new_stocks'] += 1
                else:
                    results['existing_stocks'] += 1
                
                if result['status'] == 'success':
                    results['updated'] += 1
                elif result['status'] == 'skipped':
                    results['skipped'] += 1
                elif result['status'] == 'no_new_data':
                    results['no_new_data'] += 1
                else:
                    results['failed'] += 1
                
                # Rate limiting
                if i < len(tickers):
                    import time
                    time.sleep(delay_between)
                    
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                results['failed'] += 1
                results['details'][ticker] = {
                    'status': 'failed',
                    'errors': [str(e)]
                }
        
        # Calculate metrics
        total_duration = (datetime.now() - start_time).total_seconds()
        results['total_duration_seconds'] = round(total_duration, 2)
        results['avg_time_per_stock'] = round(total_duration / len(tickers), 2)
        
        # Print summary
        logger.info(f"\n{'='*70}")
        logger.info(f"SMART BATCH UPDATE SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"Total Stocks:       {results['total']}")
        logger.info(f"🆕 New Stocks:      {results['new_stocks']} (full load)")
        logger.info(f"♻️  Existing Stocks:  {results['existing_stocks']} (incremental)")
        logger.info(f"✅ Updated:          {results['updated']}")
        logger.info(f"⏭️  Skipped:          {results['skipped']}")
        logger.info(f"📊 No New Data:      {results['no_new_data']}")
        logger.info(f"❌ Failed:           {results['failed']}")
        logger.info(f"⏱️  Total Time:       {int(total_duration//60)}m {int(total_duration%60)}s")
        logger.info(f"📈 Avg Per Stock:    {results['avg_time_per_stock']:.2f}s")
        logger.info(f"{'='*70}\n")
        
        return results


def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Smart stock data updater with auto-detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update single stock (auto-detects if new or existing)
  python smart_updater.py AAPL
  
  # Update multiple stocks
  python smart_updater.py AAPL GOOGL MSFT TSLA
  
  # Update all stocks in database
  python smart_updater.py --all
  
  # Force update even if already done today
  python smart_updater.py AAPL --force
        """
    )
    
    parser.add_argument(
        'tickers',
        nargs='*',
        help='Stock ticker symbols to update'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Update all stocks in database'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force update even if already updated today'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between stocks in seconds (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize updater
        updater = SmartStockUpdater()
        
        # Get tickers to update
        if args.all:
            # Fetch all tickers from database
            logger.info("Fetching all stocks from database...")
            db_client = SupabaseClient()
            response = db_client.client.table('stocks').select('symbol').order('symbol').execute()
            tickers = [row['symbol'] for row in response.data]
            logger.info(f"Found {len(tickers)} stocks to update")
        elif args.tickers:
            tickers = args.tickers
        else:
            parser.error("Either provide ticker symbols or use --all flag")
            sys.exit(1)
        
        # Update stocks
        if len(tickers) == 1:
            result = updater.update_stock(tickers[0], force=args.force)
            sys.exit(0 if result['status'] in ['success', 'skipped', 'no_new_data'] else 1)
        else:
            results = updater.update_multiple_stocks(tickers, delay_between=args.delay)
            sys.exit(0 if results['failed'] == 0 else 1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
