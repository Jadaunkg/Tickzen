#!/usr/bin/env python3
"""
Batch Stock Data Exporter
==========================

Exports stock data for multiple tickers in batches to avoid API rate limits.
Tracks progress and allows resuming from where it left off.

Features:
- Processes stocks in batches of 25 (configurable)
- Maintains export progress state
- Auto-resume from last successful export
- Detailed logging and error reporting
- Summary statistics after each batch
- **FORCED DIVIDEND UPDATES**: Always fetches fresh dividend data (cache bypassed)
  to ensure recent dividend formatting bug fixes are applied

Usage:
-----
    # Export all stocks in the list
    python batch_export_stocks.py
    
    # Export with custom batch size
    python batch_export_stocks.py --batch-size 10
    
    # Reset progress and start fresh
    python batch_export_stocks.py --reset
    
    # Export specific batch number
    python batch_export_stocks.py --batch 1

Recent Changes:
--------------
- Dividend data collection now bypasses monthly cache to ensure fresh yields
- Dividend table updates are forced on every run (no conditional skipping)
- This ensures dividend bug fixes are immediately applied to all stocks
"""

import os
import sys
import json
import argparse
import logging
import time
from datetime import datetime
from typing import List, Dict, Set
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from database.export_to_supabase import SupabaseDataExporter

# Configure logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / f'batch_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)


class BatchStockExporter:
    """
    Manages batch export of multiple stocks with progress tracking
    """
    
    def __init__(self, 
                 tickers_file: str = None, 
                 progress_file: str = None,
                 batch_size: int = 25,
                 delay_between_stocks: int = 2):
        """
        Initialize batch exporter
        
        Args:
            tickers_file: Path to JSON file containing stock tickers
            progress_file: Path to JSON file for tracking progress
            batch_size: Number of stocks to process in each batch
            delay_between_stocks: Seconds to wait between stock exports
        """
        # File paths
        self.base_dir = Path(__file__).parent
        self.tickers_file = Path(tickers_file) if tickers_file else self.base_dir / 'stock_tickers_list.json'
        self.progress_file = Path(progress_file) if progress_file else self.base_dir / 'export_progress.json'
        
        # Configuration
        self.batch_size = batch_size
        self.delay_between_stocks = delay_between_stocks
        
        # Load stock tickers
        self.tickers = self._load_tickers()
        logger.info(f"Loaded {len(self.tickers)} stock tickers from {self.tickers_file}")
        
        # Load or initialize progress
        self.progress = self._load_progress()
        
        # Initialize exporter
        self.exporter = SupabaseDataExporter()
        
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Delay between stocks: {self.delay_between_stocks}s")
    
    def _load_tickers(self) -> List[str]:
        """Load stock tickers from JSON file"""
        try:
            with open(self.tickers_file, 'r') as f:
                data = json.load(f)
                return data.get('tickers', [])
        except FileNotFoundError:
            logger.error(f"Tickers file not found: {self.tickers_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in tickers file: {e}")
            raise
    
    def _load_progress(self) -> Dict:
        """Load export progress from file"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                    logger.info(f"Loaded progress: {len(progress.get('completed', []))} stocks completed")
                    return progress
            except json.JSONDecodeError:
                logger.warning("Progress file corrupted, starting fresh")
        
        # Initialize new progress
        return {
            'started_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'completed': [],
            'failed': [],
            'partial': [],
            'current_batch': 0,
            'statistics': {
                'total_stocks': len(self.tickers),
                'successful': 0,
                'failed': 0,
                'partial': 0,
                'pending': len(self.tickers)
            }
        }
    
    def _save_progress(self):
        """Save current progress to file"""
        self.progress['last_updated'] = datetime.now().isoformat()
        self.progress['statistics']['successful'] = len(self.progress['completed'])
        self.progress['statistics']['failed'] = len(self.progress['failed'])
        self.progress['statistics']['partial'] = len(self.progress['partial'])
        self.progress['statistics']['pending'] = (
            self.progress['statistics']['total_stocks'] - 
            len(self.progress['completed']) - 
            len(self.progress['failed']) - 
            len(self.progress['partial'])
        )
        
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def reset_progress(self):
        """Reset progress and start fresh"""
        logger.info("Resetting export progress...")
        if self.progress_file.exists():
            self.progress_file.unlink()
        self.progress = self._load_progress()
        logger.info("Progress reset complete")
    
    def get_pending_tickers(self) -> List[str]:
        """Get list of tickers that haven't been successfully exported yet"""
        completed_set = set(self.progress.get('completed', []))
        pending = [ticker for ticker in self.tickers if ticker not in completed_set]
        return pending
    
    def export_batch(self, batch_number: int = None) -> Dict:
        """
        Export a specific batch of stocks
        
        Args:
            batch_number: Which batch to export (0-indexed). If None, exports next pending batch.
            
        Returns:
            Dict with batch export results
        """
        pending_tickers = self.get_pending_tickers()
        
        if not pending_tickers:
            logger.info("✓ All stocks have been exported!")
            return {'status': 'complete', 'message': 'All stocks exported'}
        
        # Determine batch to process
        if batch_number is not None:
            start_idx = batch_number * self.batch_size
            end_idx = start_idx + self.batch_size
            batch_tickers = pending_tickers[start_idx:end_idx]
            current_batch = batch_number
        else:
            # Process next pending batch
            batch_tickers = pending_tickers[:self.batch_size]
            current_batch = self.progress.get('current_batch', 0)
        
        if not batch_tickers:
            logger.info("No tickers in this batch")
            return {'status': 'empty', 'message': 'No tickers to process'}
        
        total_batches = (len(self.tickers) + self.batch_size - 1) // self.batch_size
        
        # Log batch info
        logger.info(f"\n{'='*100}")
        logger.info(f"BATCH {current_batch + 1}/{total_batches}")
        logger.info(f"Processing {len(batch_tickers)} stocks: {', '.join(batch_tickers)}")
        logger.info(f"{'='*100}\n")
        
        batch_results = {
            'batch_number': current_batch,
            'total_in_batch': len(batch_tickers),
            'successful': 0,
            'failed': 0,
            'partial': 0,
            'details': {}
        }
        
        # Process each ticker in the batch
        for idx, ticker in enumerate(batch_tickers, 1):
            logger.info(f"\n[{idx}/{len(batch_tickers)}] Processing {ticker}...")
            
            try:
                # Export the stock
                result = self.exporter.export_stock_data(ticker)
                batch_results['details'][ticker] = result
                
                # Update progress based on result
                if result['status'] == 'success':
                    self.progress['completed'].append(ticker)
                    batch_results['successful'] += 1
                    logger.info(f"✓ {ticker} exported successfully")
                elif result['status'] == 'partial':
                    self.progress['partial'].append(ticker)
                    batch_results['partial'] += 1
                    logger.warning(f"⚠ {ticker} exported with warnings")
                else:
                    self.progress['failed'].append(ticker)
                    batch_results['failed'] += 1
                    logger.error(f"✗ {ticker} export failed")
                
                # Save progress after each stock
                self._save_progress()
                
                # Delay between stocks (except for last one)
                if idx < len(batch_tickers):
                    logger.info(f"Waiting {self.delay_between_stocks}s before next stock...")
                    time.sleep(self.delay_between_stocks)
                
            except Exception as e:
                logger.error(f"Critical error exporting {ticker}: {e}")
                logger.exception("Traceback:")
                self.progress['failed'].append(ticker)
                batch_results['failed'] += 1
                batch_results['details'][ticker] = {
                    'status': 'failed',
                    'errors': [str(e)]
                }
                self._save_progress()
        
        # Update batch number
        self.progress['current_batch'] = current_batch + 1
        self._save_progress()
        
        # Print batch summary
        self._print_batch_summary(batch_results, current_batch, total_batches)
        
        return batch_results
    
    def export_all(self):
        """Export all pending stocks in batches"""
        logger.info(f"\n{'='*100}")
        logger.info("STARTING BULK EXPORT")
        logger.info(f"{'='*100}")
        
        pending_tickers = self.get_pending_tickers()
        total_batches = (len(pending_tickers) + self.batch_size - 1) // self.batch_size
        
        logger.info(f"Total stocks to export: {len(pending_tickers)}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Number of batches: {total_batches}")
        logger.info(f"Estimated time: {len(pending_tickers) * self.delay_between_stocks / 60:.1f} minutes")
        
        start_time = time.time()
        
        # Process all batches
        batch_num = 0
        while True:
            pending_tickers = self.get_pending_tickers()
            if not pending_tickers:
                break
            
            logger.info(f"\n{'*'*100}")
            logger.info(f"Starting batch {batch_num + 1}/{total_batches}")
            logger.info(f"{'*'*100}\n")
            
            self.export_batch(batch_number=None)
            batch_num += 1
        
        duration = time.time() - start_time
        
        # Final summary
        self._print_final_summary(duration)
    
    def _print_batch_summary(self, batch_results: Dict, batch_num: int, total_batches: int):
        """Print summary for a completed batch"""
        logger.info(f"\n{'='*100}")
        logger.info(f"BATCH {batch_num + 1}/{total_batches} COMPLETE")
        logger.info(f"{'='*100}")
        logger.info(f"Successful: {batch_results['successful']}/{batch_results['total_in_batch']}")
        logger.info(f"Partial: {batch_results['partial']}/{batch_results['total_in_batch']}")
        logger.info(f"Failed: {batch_results['failed']}/{batch_results['total_in_batch']}")
        
        # Overall progress
        stats = self.progress['statistics']
        logger.info(f"\nOVERALL PROGRESS:")
        logger.info(f"  Completed: {stats['successful']}")
        logger.info(f"  Partial: {stats['partial']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Pending: {stats['pending']}")
        logger.info(f"  Total: {stats['total_stocks']}")
        
        completion_pct = ((stats['successful'] + stats['partial']) / stats['total_stocks']) * 100
        logger.info(f"  Completion: {completion_pct:.1f}%")
        logger.info(f"{'='*100}\n")
    
    def _print_final_summary(self, duration: float):
        """Print final summary after all exports"""
        stats = self.progress['statistics']
        
        logger.info(f"\n{'='*100}")
        logger.info("BULK EXPORT COMPLETE")
        logger.info(f"{'='*100}")
        logger.info(f"Total Duration: {duration/60:.1f} minutes ({duration:.0f} seconds)")
        logger.info(f"\nFINAL STATISTICS:")
        logger.info(f"  Total Stocks: {stats['total_stocks']}")
        logger.info(f"  ✓ Successful: {stats['successful']} ({stats['successful']/stats['total_stocks']*100:.1f}%)")
        logger.info(f"  ⚠ Partial: {stats['partial']} ({stats['partial']/stats['total_stocks']*100:.1f}%)")
        logger.info(f"  ✗ Failed: {stats['failed']} ({stats['failed']/stats['total_stocks']*100:.1f}%)")
        
        if self.progress['failed']:
            logger.info(f"\nFailed tickers ({len(self.progress['failed'])}):")
            for ticker in self.progress['failed']:
                logger.info(f"  • {ticker}")
        
        if self.progress['partial']:
            logger.info(f"\nPartially exported tickers ({len(self.progress['partial'])}):")
            for ticker in self.progress['partial']:
                logger.info(f"  • {ticker}")
        
        logger.info(f"{'='*100}\n")
    
    def show_status(self):
        """Display current export status"""
        pending = self.get_pending_tickers()
        stats = self.progress['statistics']
        
        print(f"\n{'='*80}")
        print("EXPORT STATUS")
        print(f"{'='*80}")
        print(f"Started: {self.progress.get('started_at', 'N/A')}")
        print(f"Last Updated: {self.progress.get('last_updated', 'N/A')}")
        print(f"\nProgress:")
        print(f"  ✓ Completed: {stats['successful']}")
        print(f"  ⚠ Partial: {stats['partial']}")
        print(f"  ✗ Failed: {stats['failed']}")
        print(f"  ⏳ Pending: {stats['pending']}")
        print(f"  📊 Total: {stats['total_stocks']}")
        
        completion_pct = ((stats['successful'] + stats['partial']) / stats['total_stocks']) * 100
        print(f"\nCompletion: {completion_pct:.1f}%")
        
        if pending:
            print(f"\nNext batch ({min(self.batch_size, len(pending))} stocks):")
            for ticker in pending[:self.batch_size]:
                print(f"  • {ticker}")
        else:
            print("\n✓ All stocks have been exported!")
        
        print(f"{'='*80}\n")


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='Batch export stock data to Supabase',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=25,
        help='Number of stocks to process per batch (default: 25)'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=2,
        help='Seconds to wait between stock exports (default: 2)'
    )
    
    parser.add_argument(
        '--batch',
        type=int,
        help='Export specific batch number (0-indexed)'
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset progress and start fresh'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show current export status and exit'
    )
    
    parser.add_argument(
        '--tickers-file',
        help='Path to JSON file with stock tickers'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize exporter
        exporter = BatchStockExporter(
            tickers_file=args.tickers_file,
            batch_size=args.batch_size,
            delay_between_stocks=args.delay
        )
        
        # Handle different modes
        if args.status:
            exporter.show_status()
            return
        
        if args.reset:
            exporter.reset_progress()
            logger.info("Progress reset. Ready to start fresh export.")
            return
        
        if args.batch is not None:
            # Export specific batch
            exporter.export_batch(batch_number=args.batch)
        else:
            # Export all pending stocks
            exporter.export_all()
        
    except KeyboardInterrupt:
        logger.info("\n\nExport interrupted by user. Progress has been saved.")
        logger.info("Run the script again to resume from where you left off.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception("Traceback:")
        sys.exit(1)


if __name__ == '__main__':
    main()
