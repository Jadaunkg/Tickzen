"""
Stock Registry Manager
======================

Manages the list of stocks whose data is stored in Supabase.
Tracks update status, last sync dates, and data coverage.

Features:
- Register/unregister stocks
- Track last update dates and status
- Monitor data quality and coverage
- Bulk operations support
- JSON persistence for easy management
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StockRegistry:
    """Manage stock list and sync status"""
    
    def __init__(self, registry_file: str = None):
        """
        Initialize stock registry.
        
        Args:
            registry_file: Path to registry JSON file
                          Default: tickzen2/data/stocks_registry.json
        """
        if registry_file is None:
            registry_file = os.path.join(
                os.path.dirname(__file__),
                "..",
                "data",
                "stocks_registry.json"
            )
        
        self.registry_file = registry_file
        self.stocks: Dict[str, Dict[str, Any]] = {}
        
        # Ensure directory exists
        Path(self.registry_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing registry
        self._load()
    
    # ========================================================================
    # CORE OPERATIONS
    # ========================================================================
    
    def add_stock(self, symbol: str, ticker: str = None, company_name: str = None,
                  sector: str = None, industry: str = None) -> Dict[str, Any]:
        """
        Add stock to registry.
        
        Args:
            symbol: Stock symbol
            ticker: Ticker symbol
            company_name: Company full name
            sector: Industry sector
            industry: Industry classification
            
        Returns:
            Stock entry
        """
        symbol = symbol.upper()
        
        if symbol in self.stocks:
            logger.warning(f"Stock {symbol} already in registry")
            return self.stocks[symbol]
        
        entry = {
            "symbol": symbol,
            "ticker": ticker or symbol,
            "company_name": company_name,
            "sector": sector,
            "industry": industry,
            
            # Status tracking
            "is_active": True,
            "sync_enabled": True,
            "last_sync_date": None,
            "last_sync_status": "pending",  # pending, success, partial, failed
            
            # Data coverage
            "data_start_date": None,
            "data_end_date": None,
            "total_records": 0,
            "data_quality_score": 0.0,  # 0.0 to 1.0
            
            # Timestamps
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.stocks[symbol] = entry
        self._save()
        
        logger.info(f"Added stock: {symbol}")
        return entry
    
    def remove_stock(self, symbol: str) -> bool:
        """
        Remove stock from registry.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if removed, False if not found
        """
        symbol = symbol.upper()
        
        if symbol not in self.stocks:
            logger.warning(f"Stock {symbol} not found in registry")
            return False
        
        del self.stocks[symbol]
        self._save()
        
        logger.info(f"Removed stock: {symbol}")
        return True
    
    def get_stock(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get stock entry by symbol"""
        return self.stocks.get(symbol.upper())
    
    def list_stocks(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        List all stocks in registry.
        
        Args:
            active_only: Only return active stocks
            
        Returns:
            List of stock entries
        """
        stocks = list(self.stocks.values())
        
        if active_only:
            stocks = [s for s in stocks if s.get("is_active", True)]
        
        return stocks
    
    # ========================================================================
    # UPDATE STATUS TRACKING
    # ========================================================================
    
    def mark_sync_start(self, symbol: str) -> None:
        """Mark sync as in-progress"""
        symbol = symbol.upper()
        if symbol in self.stocks:
            self.stocks[symbol]["last_sync_status"] = "in_progress"
            self.stocks[symbol]["updated_at"] = datetime.now().isoformat()
            self._save()
    
    def mark_sync_success(self, symbol: str, records_count: int = None,
                          data_start: str = None, data_end: str = None,
                          quality_score: float = 1.0) -> None:
        """
        Mark sync as successful.
        
        Args:
            symbol: Stock symbol
            records_count: Number of records synced
            data_start: Data start date (YYYY-MM-DD)
            data_end: Data end date (YYYY-MM-DD)
            quality_score: Data quality score (0.0-1.0)
        """
        symbol = symbol.upper()
        if symbol not in self.stocks:
            return
        
        self.stocks[symbol]["last_sync_date"] = datetime.now().isoformat()
        self.stocks[symbol]["last_sync_status"] = "success"
        
        if records_count is not None:
            self.stocks[symbol]["total_records"] = records_count
        
        if data_start:
            self.stocks[symbol]["data_start_date"] = data_start
        
        if data_end:
            self.stocks[symbol]["data_end_date"] = data_end
        
        self.stocks[symbol]["data_quality_score"] = min(max(quality_score, 0.0), 1.0)
        self.stocks[symbol]["updated_at"] = datetime.now().isoformat()
        
        self._save()
        logger.info(f"Marked {symbol} sync as success")
    
    def mark_sync_failed(self, symbol: str, error_message: str = None) -> None:
        """
        Mark sync as failed.
        
        Args:
            symbol: Stock symbol
            error_message: Error details
        """
        symbol = symbol.upper()
        if symbol not in self.stocks:
            return
        
        self.stocks[symbol]["last_sync_date"] = datetime.now().isoformat()
        self.stocks[symbol]["last_sync_status"] = "failed"
        self.stocks[symbol]["last_error"] = error_message
        self.stocks[symbol]["updated_at"] = datetime.now().isoformat()
        
        self._save()
        logger.error(f"Marked {symbol} sync as failed: {error_message}")
    
    def mark_sync_partial(self, symbol: str, records_count: int = None,
                          quality_score: float = 0.7) -> None:
        """Mark sync as partially successful"""
        symbol = symbol.upper()
        if symbol not in self.stocks:
            return
        
        self.stocks[symbol]["last_sync_date"] = datetime.now().isoformat()
        self.stocks[symbol]["last_sync_status"] = "partial"
        
        if records_count is not None:
            self.stocks[symbol]["total_records"] = records_count
        
        self.stocks[symbol]["data_quality_score"] = quality_score
        self.stocks[symbol]["updated_at"] = datetime.now().isoformat()
        
        self._save()
        logger.warning(f"Marked {symbol} sync as partial")
    
    # ========================================================================
    # QUERYING
    # ========================================================================
    
    def get_pending_sync(self) -> List[Dict[str, Any]]:
        """Get stocks pending initial sync"""
        return [
            s for s in self.stocks.values()
            if s.get("is_active") and s.get("sync_enabled") and
               s.get("last_sync_status") in [None, "pending", "failed"]
        ]
    
    def get_due_for_sync(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get stocks due for refresh.
        
        Args:
            hours: Hours since last sync before due
            
        Returns:
            List of stocks due for sync
        """
        due = []
        now = datetime.now()
        threshold = now - timedelta(hours=hours)
        
        for stock in self.stocks.values():
            if not stock.get("is_active") or not stock.get("sync_enabled"):
                continue
            
            last_sync = stock.get("last_sync_date")
            
            # If never synced or old, it's due
            if last_sync is None:
                due.append(stock)
            else:
                last_sync_dt = datetime.fromisoformat(last_sync)
                if last_sync_dt < threshold:
                    due.append(stock)
        
        return due
    
    def get_by_sector(self, sector: str) -> List[Dict[str, Any]]:
        """Get stocks by sector"""
        return [
            s for s in self.stocks.values()
            if s.get("sector", "").lower() == sector.lower() and s.get("is_active")
        ]
    
    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get stocks by sync status"""
        return [
            s for s in self.stocks.values()
            if s.get("last_sync_status") == status
        ]
    
    def get_low_quality_stocks(self, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Get stocks with low data quality"""
        return [
            s for s in self.stocks.values()
            if s.get("is_active") and s.get("data_quality_score", 0.0) < threshold
        ]
    
    # ========================================================================
    # BATCH OPERATIONS
    # ========================================================================
    
    def add_stocks_batch(self, stocks_list: List[Dict[str, Any]]) -> int:
        """
        Add multiple stocks from list.
        
        Args:
            stocks_list: List of stock dicts with symbol, ticker, etc.
            
        Returns:
            Number of stocks added
        """
        count = 0
        
        for stock_data in stocks_list:
            try:
                self.add_stock(
                    symbol=stock_data.get("symbol"),
                    ticker=stock_data.get("ticker"),
                    company_name=stock_data.get("company_name"),
                    sector=stock_data.get("sector"),
                    industry=stock_data.get("industry")
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to add stock {stock_data.get('symbol')}: {e}")
        
        return count
    
    def activate_stocks(self, symbols: List[str]) -> int:
        """Activate multiple stocks"""
        count = 0
        for symbol in symbols:
            symbol = symbol.upper()
            if symbol in self.stocks:
                self.stocks[symbol]["is_active"] = True
                self.stocks[symbol]["updated_at"] = datetime.now().isoformat()
                count += 1
        
        self._save()
        return count
    
    def deactivate_stocks(self, symbols: List[str]) -> int:
        """Deactivate multiple stocks"""
        count = 0
        for symbol in symbols:
            symbol = symbol.upper()
            if symbol in self.stocks:
                self.stocks[symbol]["is_active"] = False
                self.stocks[symbol]["updated_at"] = datetime.now().isoformat()
                count += 1
        
        self._save()
        return count
    
    # ========================================================================
    # PERSISTENCE
    # ========================================================================
    
    def _load(self) -> None:
        """Load registry from file"""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    self.stocks = {k.upper(): v for k, v in data.items()}
                logger.info(f"Loaded registry with {len(self.stocks)} stocks")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self.stocks = {}
        else:
            self.stocks = {}
    
    def _save(self) -> None:
        """Save registry to file"""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.stocks, f, indent=2)
            logger.debug(f"Registry saved: {len(self.stocks)} stocks")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def export_json(self) -> str:
        """Export registry as JSON string"""
        return json.dumps(self.stocks, indent=2)
    
    def import_json(self, json_str: str) -> int:
        """
        Import registry from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            Number of stocks imported
        """
        try:
            data = json.loads(json_str)
            self.stocks = {k.upper(): v for k, v in data.items()}
            self._save()
            return len(self.stocks)
        except Exception as e:
            logger.error(f"Failed to import registry: {e}")
            return 0
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        active = [s for s in self.stocks.values() if s.get("is_active")]
        synced = [s for s in active if s.get("last_sync_status") == "success"]
        
        return {
            "total_stocks": len(self.stocks),
            "active_stocks": len(active),
            "synced_stocks": len(synced),
            "pending_stocks": len(self.get_pending_sync()),
            "avg_quality_score": sum(s.get("data_quality_score", 0) for s in active) / len(active) if active else 0,
            "by_sector": self._stats_by_sector(),
            "by_status": self._stats_by_status(),
            "last_updated": datetime.now().isoformat()
        }
    
    def _stats_by_sector(self) -> Dict[str, int]:
        """Get stock count by sector"""
        stats = {}
        for stock in self.stocks.values():
            if stock.get("is_active"):
                sector = stock.get("sector", "Unknown")
                stats[sector] = stats.get(sector, 0) + 1
        return stats
    
    def _stats_by_status(self) -> Dict[str, int]:
        """Get stock count by sync status"""
        stats = {}
        for stock in self.stocks.values():
            if stock.get("is_active"):
                status = stock.get("last_sync_status", "pending")
                stats[status] = stats.get(status, 0) + 1
        return stats
    
    def print_stats(self) -> None:
        """Print registry statistics"""
        stats = self.get_stats()
        print("\n" + "="*60)
        print("STOCK REGISTRY STATISTICS")
        print("="*60)
        print(f"Total Stocks: {stats['total_stocks']}")
        print(f"Active Stocks: {stats['active_stocks']}")
        print(f"Synced Stocks: {stats['synced_stocks']}")
        print(f"Pending Sync: {stats['pending_stocks']}")
        print(f"Avg Quality Score: {stats['avg_quality_score']:.2f}")
        
        if stats['by_sector']:
            print("\nBy Sector:")
            for sector, count in sorted(stats['by_sector'].items()):
                print(f"  {sector}: {count}")
        
        if stats['by_status']:
            print("\nBy Status:")
            for status, count in sorted(stats['by_status'].items()):
                print(f"  {status}: {count}")
        print("="*60 + "\n")


if __name__ == "__main__":
    # Example usage
    registry = StockRegistry()
    
    # Add some stocks
    registry.add_stock("AAPL", "AAPL", "Apple Inc.", "Technology", "Consumer Electronics")
    registry.add_stock("MSFT", "MSFT", "Microsoft Corp.", "Technology", "Software")
    registry.add_stock("GOOGL", "GOOGL", "Alphabet Inc.", "Technology", "Internet Services")
    
    # Check stats
    registry.print_stats()
    
    # Mark one as synced
    registry.mark_sync_success("AAPL", records_count=2500, 
                              data_start="2014-01-01", data_end="2024-01-22",
                              quality_score=0.98)
    
    registry.print_stats()
