"""
Stock Data Sync Manager
=======================

Daily batch sync system for updating Supabase with 10 years of stock data.
Exports data from your analysis scripts and efficiently upserts to database.

Features:
- Daily automatic refresh scheduling
- 10-year historical data export
- Transaction-like batch processing
- Data validation and quality scoring
- Comprehensive error handling and logging
- Dry-run and validation modes
"""

import os
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
from enum import Enum

from .supabase_client import SupabaseClient, supabase_transaction
from .stock_registry import StockRegistry

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class SyncType(Enum):
    """Sync operation types"""
    FULL_HISTORY = "full_history"  # 10 years of data
    DAILY = "daily"               # Last 1 day
    WEEKLY = "weekly"             # Last 7 days
    MONTHLY = "monthly"           # Last 30 days
    RECOVERY = "recovery"         # Recover missing data


@dataclass
class SyncStats:
    """Statistics for a sync operation"""
    stock_symbol: str
    sync_type: SyncType
    start_time: datetime
    
    # Results
    total_records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_failed: int = 0
    
    # Quality
    data_quality_score: float = 1.0
    data_start_date: Optional[str] = None
    data_end_date: Optional[str] = None
    
    # Status
    status: str = "pending"  # pending, in_progress, success, partial, failed
    error_message: Optional[str] = None
    
    def end(self):
        """Mark end of sync"""
        self.duration_seconds = int((datetime.now() - self.start_time).total_seconds())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stock_symbol": self.stock_symbol,
            "sync_type": self.sync_type.value,
            "start_time": self.start_time.isoformat(),
            "duration_seconds": getattr(self, 'duration_seconds', 0),
            "total_records": self.total_records_processed,
            "inserted": self.records_inserted,
            "updated": self.records_updated,
            "failed": self.records_failed,
            "quality_score": self.data_quality_score,
            "data_start": self.data_start_date,
            "data_end": self.data_end_date,
            "status": self.status
        }


class StockDataSyncManager:
    """Manages daily sync of stock data to Supabase"""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None,
                 registry_file: str = None, data_dir: str = None):
        """
        Initialize sync manager.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            registry_file: Stock registry file path
            data_dir: Directory containing exported stock data
        """
        self.db = SupabaseClient(url=supabase_url, key=supabase_key)
        self.registry = StockRegistry(registry_file=registry_file)
        
        # Set data directory (where exported data is stored)
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(__file__),
                "..",
                "generated_data",
                "stock_data_exports"
            )
        
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Sync statistics
        self.sync_results: List[SyncStats] = []
    
    # ========================================================================
    # MAIN SYNC OPERATIONS
    # ========================================================================
    
    def sync_stock(self, symbol: str, sync_type: SyncType = SyncType.DAILY,
                   dry_run: bool = False, validate_only: bool = False) -> SyncStats:
        """
        Sync stock data to Supabase.
        
        Args:
            symbol: Stock symbol
            sync_type: Type of sync (full, daily, weekly, etc.)
            dry_run: Don't actually write to database
            validate_only: Only validate without syncing
            
        Returns:
            SyncStats with results
        """
        symbol = symbol.upper()
        stats = SyncStats(symbol, sync_type, datetime.now())
        
        try:
            logger.info(f"Starting {sync_type.value} sync for {symbol}")
            self.registry.mark_sync_start(symbol)
            
            # Step 1: Load data from export
            data = self._load_stock_data(symbol, sync_type)
            if not data:
                raise ValueError(f"No data found for {symbol}")
            
            stats.total_records_processed = len(data)
            stats.data_start_date = data[0].get("date") if data else None
            stats.data_end_date = data[-1].get("date") if data else None
            
            # Step 2: Validate data
            if validate_only:
                stats.status = "success"
                stats.data_quality_score = self._validate_data(data)
                logger.info(f"Validation complete for {symbol}: quality={stats.data_quality_score:.2f}")
                return stats
            
            # Step 3: Ensure stock exists in registry
            stock_id = self._ensure_stock_registered(symbol, data[0] if data else {})
            if not stock_id:
                raise ValueError(f"Failed to register stock {symbol}")
            
            # Step 4: Prepare and sync data
            if not dry_run:
                inserted, updated, failed = self._sync_data_to_supabase(
                    stock_id, symbol, data, sync_type
                )
                stats.records_inserted = inserted
                stats.records_updated = updated
                stats.records_failed = failed
            else:
                logger.info(f"[DRY RUN] Would sync {len(data)} records for {symbol}")
            
            # Step 5: Calculate quality score
            stats.data_quality_score = self._calculate_quality_score(data, stats)
            stats.status = "success" if stats.records_failed == 0 else "partial"
            
            # Update registry
            if not dry_run:
                self.registry.mark_sync_success(
                    symbol,
                    records_count=stats.total_records_processed,
                    data_start=stats.data_start_date,
                    data_end=stats.data_end_date,
                    quality_score=stats.data_quality_score
                )
            
            logger.info(f"Sync completed for {symbol}: {stats.records_inserted} inserted, "
                       f"{stats.records_updated} updated, {stats.records_failed} failed")
        
        except Exception as e:
            stats.status = "failed"
            stats.error_message = str(e)
            self.registry.mark_sync_failed(symbol, str(e))
            logger.error(f"Sync failed for {symbol}: {e}", exc_info=True)
        
        finally:
            stats.end()
            self.sync_results.append(stats)
        
        return stats
    
    def sync_multiple(self, symbols: List[str], sync_type: SyncType = SyncType.DAILY,
                      dry_run: bool = False) -> List[SyncStats]:
        """
        Sync multiple stocks.
        
        Args:
            symbols: List of stock symbols
            sync_type: Type of sync
            dry_run: Don't actually write
            
        Returns:
            List of SyncStats
        """
        results = []
        
        for symbol in symbols:
            try:
                result = self.sync_stock(symbol, sync_type, dry_run=dry_run)
                results.append(result)
                
                # Small delay between syncs to avoid overwhelming API
                import time
                time.sleep(0.5)
            
            except Exception as e:
                logger.error(f"Failed to sync {symbol}: {e}")
        
        return results
    
    def sync_pending(self, sync_type: SyncType = SyncType.FULL_HISTORY,
                     dry_run: bool = False, max_stocks: int = None) -> List[SyncStats]:
        """
        Sync all stocks pending initial sync.
        
        Args:
            sync_type: Type of sync (usually FULL_HISTORY for initial)
            dry_run: Don't actually write
            max_stocks: Maximum stocks to sync (for testing)
            
        Returns:
            List of SyncStats
        """
        pending = self.registry.get_pending_sync()
        
        if max_stocks:
            pending = pending[:max_stocks]
        
        logger.info(f"Syncing {len(pending)} pending stocks")
        
        symbols = [s["symbol"] for s in pending]
        return self.sync_multiple(symbols, sync_type, dry_run=dry_run)
    
    def sync_due(self, hours: int = 24, dry_run: bool = False) -> List[SyncStats]:
        """
        Sync all stocks due for refresh.
        
        Args:
            hours: Hours since last sync before due
            dry_run: Don't actually write
            
        Returns:
            List of SyncStats
        """
        due = self.registry.get_due_for_sync(hours=hours)
        logger.info(f"Syncing {len(due)} stocks due for refresh")
        
        symbols = [s["symbol"] for s in due]
        return self.sync_multiple(symbols, SyncType.DAILY, dry_run=dry_run)
    
    # ========================================================================
    # DATA LOADING AND PREPARATION
    # ========================================================================
    
    def _load_stock_data(self, symbol: str, sync_type: SyncType) -> List[Dict[str, Any]]:
        """
        Load stock data from export files.
        
        This method loads pre-exported data (you export from your analysis scripts).
        The data should be in JSON format with daily records.
        
        Args:
            symbol: Stock symbol
            sync_type: Type of sync (determines date range)
            
        Returns:
            List of data records
        """
        # Format: generated_data/stock_data_exports/{SYMBOL}_data.json
        export_file = os.path.join(self.data_dir, f"{symbol.upper()}_data.json")
        
        if not os.path.exists(export_file):
            logger.warning(f"No export file found: {export_file}")
            return []
        
        try:
            with open(export_file, 'r') as f:
                all_data = json.load(f)
            
            # Filter by sync type (date range)
            filtered_data = self._filter_by_sync_type(all_data, sync_type)
            
            logger.info(f"Loaded {len(filtered_data)} records for {symbol}")
            return filtered_data
        
        except Exception as e:
            logger.error(f"Failed to load data for {symbol}: {e}")
            return []
    
    def _filter_by_sync_type(self, data: List[Dict], sync_type: SyncType) -> List[Dict]:
        """Filter data by sync type (date range)"""
        if not data:
            return []
        
        now = datetime.now()
        cutoff_date = None
        
        if sync_type == SyncType.FULL_HISTORY:
            # 10 years back
            cutoff_date = now - timedelta(days=3650)
        elif sync_type == SyncType.DAILY:
            # Last 1 day
            cutoff_date = now - timedelta(days=1)
        elif sync_type == SyncType.WEEKLY:
            # Last 7 days
            cutoff_date = now - timedelta(days=7)
        elif sync_type == SyncType.MONTHLY:
            # Last 30 days
            cutoff_date = now - timedelta(days=30)
        else:
            # Return all
            return data
        
        filtered = []
        for record in data:
            try:
                record_date = datetime.fromisoformat(record.get("date", ""))
                if record_date >= cutoff_date:
                    filtered.append(record)
            except:
                filtered.append(record)  # Include if date parsing fails
        
        return filtered
    
    def _ensure_stock_registered(self, symbol: str, sample_data: Dict) -> Optional[int]:
        """
        Ensure stock exists in stocks table.
        
        Returns:
            Stock ID from database
        """
        # Check if stock exists in database
        stock = self.db.get_stock_by_symbol(symbol)
        
        if stock:
            return stock["id"]
        
        # Create new stock entry
        stock_data = {
            "symbol": symbol,
            "ticker": symbol,
            "company_name": sample_data.get("company_name", symbol),
            "sector": sample_data.get("sector"),
            "industry": sample_data.get("industry"),
            "country": sample_data.get("country", "US"),
            "exchange": sample_data.get("exchange", "NASDAQ"),
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        try:
            result = self.db.insert("stocks", stock_data)
            logger.info(f"Registered stock {symbol} with ID {result.get('id')}")
            return result.get("id")
        except Exception as e:
            logger.error(f"Failed to register stock {symbol}: {e}")
            return None
    
    # ========================================================================
    # DATA SYNC TO SUPABASE
    # ========================================================================
    
    def _sync_data_to_supabase(self, stock_id: int, symbol: str,
                               data: List[Dict], sync_type: SyncType) -> Tuple[int, int, int]:
        """
        Sync data to Supabase using appropriate table mapping.
        
        Returns:
            Tuple of (inserted, updated, failed)
        """
        inserted = 0
        updated = 0
        failed = 0
        
        # Map data to different tables based on content
        tables_to_sync = self._map_data_to_tables(data)
        
        for table_name, records in tables_to_sync.items():
            if not records:
                continue
            
            try:
                # Prepare records with stock_id
                prepared = []
                for record in records:
                    record["stock_id"] = stock_id
                    prepared.append(record)
                
                # Upsert to table
                ins, upd = self.db.upsert_batch(table_name, prepared)
                inserted += ins
                updated += upd
                
                logger.info(f"Upserted {ins} new + {upd} updated records to {table_name}")
            
            except Exception as e:
                failed += len(records)
                logger.error(f"Failed to sync {len(records)} records to {table_name}: {e}")
        
        return inserted, updated, failed
    
    def _map_data_to_tables(self, data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Map records to appropriate tables based on data structure.
        
        Analyzes record content and routes to:
        - daily_price_data
        - technical_indicators
        - fundamental_data
        - forecast_data
        - risk_data
        - market_price_snapshot
        - sentiment_data
        """
        mapping = {
            "daily_price_data": [],
            "technical_indicators": [],
            "fundamental_data": [],
            "forecast_data": [],
            "risk_data": [],
            "market_price_snapshot": [],
            "sentiment_data": []
        }
        
        for record in data:
            # Extract common fields
            date = record.get("date")
            
            # Daily price data
            if any(k in record for k in ["open_price", "high_price", "low_price", "close_price"]):
                price_record = {
                    "date": date,
                    "open_price": record.get("open_price"),
                    "high_price": record.get("high_price"),
                    "low_price": record.get("low_price"),
                    "close_price": record.get("close_price"),
                    "adjusted_close": record.get("adjusted_close"),
                    "volume": record.get("volume"),
                    "daily_return_pct": record.get("daily_return_pct"),
                    "price_change": record.get("price_change")
                }
                mapping["daily_price_data"].append(self._clean_record(price_record))
            
            # Technical indicators
            if any(k in record for k in ["sma_20", "rsi_14", "macd_line", "bb_upper"]):
                tech_record = {
                    "date": date,
                    "sma_7": record.get("sma_7"),
                    "sma_20": record.get("sma_20"),
                    "sma_50": record.get("sma_50"),
                    "sma_100": record.get("sma_100"),
                    "sma_200": record.get("sma_200"),
                    "ema_12": record.get("ema_12"),
                    "ema_26": record.get("ema_26"),
                    "rsi_14": record.get("rsi_14"),
                    "macd_line": record.get("macd_line"),
                    "macd_signal": record.get("macd_signal"),
                    "macd_histogram": record.get("macd_histogram"),
                    "bb_upper": record.get("bb_upper"),
                    "bb_middle": record.get("bb_middle"),
                    "bb_lower": record.get("bb_lower"),
                    "atr_14": record.get("atr_14"),
                    "support_30d": record.get("support_30d"),
                    "resistance_30d": record.get("resistance_30d")
                }
                mapping["technical_indicators"].append(self._clean_record(tech_record))
            
            # Fundamental data
            if any(k in record for k in ["pe_ratio", "net_margin", "roe"]):
                fund_record = {
                    "period_date": date,
                    "period_type": "Q" if record.get("period_type") == "Q" else "FY",
                    "pe_ratio": record.get("pe_ratio"),
                    "net_margin": record.get("net_margin"),
                    "roe": record.get("roe"),
                    "debt_to_equity": record.get("debt_to_equity"),
                    "total_cash": record.get("total_cash"),
                    "revenue_ttm": record.get("revenue_ttm")
                }
                mapping["fundamental_data"].append(self._clean_record(fund_record))
            
            # Market price snapshot
            if any(k in record for k in ["current_price", "market_cap", "pe_ratio"]):
                market_record = {
                    "date": date,
                    "current_price": record.get("current_price"),
                    "market_cap": record.get("market_cap"),
                    "change_pct": record.get("change_pct")
                }
                mapping["market_price_snapshot"].append(self._clean_record(market_record))
            
            # Risk data
            if any(k in record for k in ["beta", "sharpe_ratio", "var_95"]):
                risk_record = {
                    "date": date,
                    "beta": record.get("beta"),
                    "sharpe_ratio": record.get("sharpe_ratio"),
                    "var_95": record.get("var_95")
                }
                mapping["risk_data"].append(self._clean_record(risk_record))
            
            # Sentiment data
            if any(k in record for k in ["sentiment_score", "sentiment_label"]):
                sentiment_record = {
                    "date": date,
                    "sentiment_score": record.get("sentiment_score"),
                    "sentiment_label": record.get("sentiment_label")
                }
                mapping["sentiment_data"].append(self._clean_record(sentiment_record))
        
        return mapping
    
    def _clean_record(self, record: Dict) -> Dict:
        """Remove None values from record"""
        return {k: v for k, v in record.items() if v is not None}
    
    # ========================================================================
    # DATA VALIDATION & QUALITY
    # ========================================================================
    
    def _validate_data(self, data: List[Dict]) -> float:
        """
        Calculate data quality score (0.0 to 1.0).
        
        Factors:
        - Record completeness
        - Value ranges
        - Missing fields
        """
        if not data:
            return 0.0
        
        scores = []
        
        for record in data:
            completeness = len([v for v in record.values() if v is not None]) / len(record)
            scores.append(completeness)
        
        avg_completeness = sum(scores) / len(scores) if scores else 0.0
        
        # Quality score based on completeness and record count
        quality = min(avg_completeness, 1.0) * 0.8 + min(len(data) / 2500, 1.0) * 0.2
        
        return quality
    
    def _calculate_quality_score(self, data: List[Dict], stats: SyncStats) -> float:
        """Calculate final quality score for sync"""
        if stats.records_failed > 0:
            # Reduce score based on failure rate
            failure_rate = stats.records_failed / stats.total_records_processed
            base_score = 1.0 - failure_rate
        else:
            base_score = 1.0
        
        # Additional factors
        completeness = self._validate_data(data)
        
        return base_score * 0.7 + completeness * 0.3
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def get_sync_report(self) -> Dict[str, Any]:
        """Get comprehensive sync report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_syncs": len(self.sync_results),
            "successful": len([s for s in self.sync_results if s.status == "success"]),
            "partial": len([s for s in self.sync_results if s.status == "partial"]),
            "failed": len([s for s in self.sync_results if s.status == "failed"]),
            "total_records_processed": sum(s.total_records_processed for s in self.sync_results),
            "total_inserted": sum(s.records_inserted for s in self.sync_results),
            "total_updated": sum(s.records_updated for s in self.sync_results),
            "avg_quality_score": sum(s.data_quality_score for s in self.sync_results) / len(self.sync_results) if self.sync_results else 0.0,
            "syncs": [s.to_dict() for s in self.sync_results]
        }
    
    def print_sync_report(self) -> None:
        """Print sync report to console"""
        report = self.get_sync_report()
        
        print("\n" + "="*70)
        print("STOCK DATA SYNC REPORT")
        print("="*70)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Total Syncs: {report['total_syncs']}")
        print(f"  Success: {report['successful']}")
        print(f"  Partial: {report['partial']}")
        print(f"  Failed: {report['failed']}")
        print(f"\nData Statistics:")
        print(f"  Records Processed: {report['total_records_processed']:,}")
        print(f"  Records Inserted: {report['total_inserted']:,}")
        print(f"  Records Updated: {report['total_updated']:,}")
        print(f"  Avg Quality Score: {report['avg_quality_score']:.2f}")
        print("="*70 + "\n")


if __name__ == "__main__":
    # Example usage
    print("Initializing Stock Data Sync Manager...")
    
    sync_manager = StockDataSyncManager()
    
    # Example: Dry run of a single stock
    print("\n--- DRY RUN EXAMPLE ---")
    result = sync_manager.sync_stock("AAPL", SyncType.FULL_HISTORY, dry_run=True)
    print(f"Result: {result.to_dict()}")
    
    # Print stats
    sync_manager.print_sync_report()
