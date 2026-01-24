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
        
        logger.info("SupabaseDataExporter initialized successfully")
    
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
            
            # 2.1: Export stock metadata
            logger.info("\n[1/11] Exporting stock metadata...")
            stock_record = self.mapper.map_stock_metadata(
                ticker,
                collected_data['info'],
                collected_data['processed_data']
            )
            
            # Upsert stock record
            stock_result = self.db.client.table('stocks').upsert(
                stock_record,
                on_conflict='symbol'
            ).execute()
            
            if not stock_result.data:
                raise Exception("Failed to insert/update stock record")
            
            stock_id = stock_result.data[0]['id']
            logger.info(f"  ✓ Stock registered: ID = {stock_id}")
            result['records_exported']['stocks'] = 1
            self.mapper.sync_stats['records_inserted'] += 1
            
            # 2.2: Export daily price data
            logger.info("\n[2/11] Exporting daily price data...")
            price_records = self.mapper.map_daily_prices(
                stock_id,
                collected_data['processed_data']
            )
            
            # Batch insert prices
            batch_size = 1000
            total_inserted = 0
            for i in range(0, len(price_records), batch_size):
                batch = price_records[i:i+batch_size]
                self.db.client.table('daily_price_data').upsert(
                    batch,
                    on_conflict='stock_id,date'
                ).execute()
                total_inserted += len(batch)
                logger.info(f"  Progress: {total_inserted}/{len(price_records)} records...")
            
            logger.info(f"  ✓ Exported {total_inserted} price records")
            result['records_exported']['daily_price_data'] = total_inserted
            self.mapper.sync_stats['records_inserted'] += total_inserted
            
            # 2.3: Export technical indicators
            logger.info("\n[3/11] Exporting technical indicators...")
            tech_records = self.mapper.map_technical_indicators(
                stock_id,
                collected_data['processed_data']
            )
            
            # Batch insert technical indicators
            total_inserted = 0
            for i in range(0, len(tech_records), batch_size):
                batch = tech_records[i:i+batch_size]
                self.db.client.table('technical_indicators').upsert(
                    batch,
                    on_conflict='stock_id,date'
                ).execute()
                total_inserted += len(batch)
                logger.info(f"  Progress: {total_inserted}/{len(tech_records)} records...")
            
            logger.info(f"  ✓ Exported {total_inserted} indicator records")
            result['records_exported']['technical_indicators'] = total_inserted
            self.mapper.sync_stats['records_inserted'] += total_inserted
            
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
            
            # 2.5: Export forecast data (12 monthly forecasts without redundant analyst data)
            logger.info("\n[5/11] Exporting forecast data...")
            if collected_data.get('forecast_data') is not None:
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
            
            # 2.7: Export risk data
            logger.info("\n[7/12] Exporting risk data...")
            risk_record = self.mapper.map_risk_data(
                stock_id,
                collected_data['processed_data'],
                collected_data['info']
            )
            
            self.db.client.table('risk_data').upsert(
                [risk_record],
                on_conflict='stock_id,date'
            ).execute()
            logger.info(f"  ✓ Exported risk metrics")
            result['records_exported']['risk_data'] = 1
            self.mapper.sync_stats['records_inserted'] += 1
            
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
            
            # 2.12: Export insider transactions
            logger.info("\n[12/12] Exporting insider transactions...")
            if collected_data.get('insider_transactions') is not None and not collected_data['insider_transactions'].empty:
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
