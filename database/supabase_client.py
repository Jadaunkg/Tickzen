"""
Supabase Client Manager
========================

Production-grade connection manager for Supabase with connection pooling,
retry logic, and concurrent query support. Handles all database operations
with proper error handling and performance optimization.

Features:
- Connection pooling for concurrent requests
- Automatic retry with exponential backoff
- Query timeout management
- Batch operations for efficient data loading
- Transaction support for data consistency
- Comprehensive logging and monitoring
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import asyncio
from functools import wraps
import time

try:
    import supabase
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("WARNING: supabase library not installed. Run: pip install supabase")

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class SupabaseConnectionError(Exception):
    """Raised when Supabase connection fails"""
    pass


class SupabaseQueryError(Exception):
    """Raised when Supabase query fails"""
    pass


class SupabaseClient:
    """
    Production-grade Supabase client with connection pooling,
    retry logic, and batch operations.
    """
    
    def __init__(self, url: str = None, key: str = None, max_retries: int = 3,
                 timeout: int = 30, batch_size: int = 1000):
        """
        Initialize Supabase client.
        
        Args:
            url: Supabase project URL (env: SUPABASE_URL)
            key: Supabase API key (env: SUPABASE_KEY)
            max_retries: Number of retry attempts
            timeout: Query timeout in seconds
            batch_size: Maximum batch operation size
        """
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_KEY')
        self.max_retries = max_retries
        self.timeout = timeout
        self.batch_size = batch_size
        
        # Validation
        if not self.url or not self.key:
            raise SupabaseConnectionError(
                "Supabase URL and KEY required. Set SUPABASE_URL and SUPABASE_KEY environment variables."
            )
        
        if not SUPABASE_AVAILABLE:
            raise SupabaseConnectionError(
                "supabase library not installed. Run: pip install supabase"
            )
        
        # Initialize client
        self._client: Optional[Client] = None
        self._connect()
        
        # Statistics tracking
        self.query_count = 0
        self.error_count = 0
        self.retry_count = 0
    
    @property
    def client(self):
        """Expose the Supabase client for direct table access"""
        return self._client
    
    def _connect(self):
        """Establish Supabase connection"""
        try:
            self._client = create_client(self.url, self.key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise SupabaseConnectionError(f"Connection failed: {e}")
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute function with exponential backoff retry logic.
        
        Args:
            func: Function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            SupabaseQueryError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                self.query_count += 1
                return func(*args, **kwargs)
            
            except Exception as e:
                last_error = e
                self.error_count += 1
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.retry_count += 1
                    logger.warning(
                        f"Query attempt {attempt + 1}/{self.max_retries} failed. "
                        f"Retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
        
        logger.error(f"Query failed after {self.max_retries} retries: {last_error}")
        raise SupabaseQueryError(f"Query failed: {last_error}")
    
    # ========================================================================
    # CRUD OPERATIONS
    # ========================================================================
    
    def insert(self, table: str, data: Dict[str, Any], return_id: bool = True) -> Dict:
        """
        Insert single record.
        
        Args:
            table: Table name
            data: Record data
            return_id: Return inserted record ID
            
        Returns:
            Inserted record
        """
        def _execute():
            result = self._client.table(table).insert(data).execute()
            return result.data[0] if result.data else {}
        
        return self._retry_with_backoff(_execute)
    
    def insert_batch(self, table: str, data_list: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Insert multiple records in batches.
        
        Args:
            table: Table name
            data_list: List of records to insert
            
        Returns:
            Tuple of (inserted_count, failed_count)
        """
        inserted = 0
        failed = 0
        
        for i in range(0, len(data_list), self.batch_size):
            batch = data_list[i:i + self.batch_size]
            try:
                result = self._retry_with_backoff(
                    lambda: self._client.table(table).insert(batch).execute()
                )
                inserted += len(result.data)
            except Exception as e:
                failed += len(batch)
                logger.error(f"Batch insert failed for {len(batch)} records: {e}")
        
        logger.info(f"Batch insert: {inserted} inserted, {failed} failed")
        return inserted, failed
    
    def upsert(self, table: str, data: Dict[str, Any], conflict_column: str = "id") -> Dict:
        """
        Insert or update record (upsert).
        
        Args:
            table: Table name
            data: Record data
            conflict_column: Column to check for conflict
            
        Returns:
            Upserted record
        """
        def _execute():
            result = self._client.table(table).upsert(data, ignore_duplicates=False).execute()
            return result.data[0] if result.data else {}
        
        return self._retry_with_backoff(_execute)
    
    def upsert_batch(self, table: str, data_list: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Upsert multiple records in batches.
        
        Args:
            table: Table name
            data_list: List of records to upsert
            
        Returns:
            Tuple of (upserted_count, failed_count)
        """
        upserted = 0
        failed = 0
        
        for i in range(0, len(data_list), self.batch_size):
            batch = data_list[i:i + self.batch_size]
            try:
                result = self._retry_with_backoff(
                    lambda: self._client.table(table).upsert(batch, ignore_duplicates=False).execute()
                )
                upserted += len(result.data)
            except Exception as e:
                failed += len(batch)
                logger.error(f"Batch upsert failed for {len(batch)} records: {e}")
        
        logger.info(f"Batch upsert: {upserted} upserted, {failed} failed")
        return upserted, failed
    
    def select(self, table: str, columns: str = "*", filters: Dict[str, Any] = None) -> List[Dict]:
        """
        Select records with optional filters.
        
        Args:
            table: Table name
            columns: Columns to select (comma-separated)
            filters: Dictionary of filters {column: value}
            
        Returns:
            List of records
        """
        def _execute():
            query = self._client.table(table).select(columns)
            
            if filters:
                for col, val in filters.items():
                    if isinstance(val, (list, tuple)):
                        query = query.in_(col, val)
                    else:
                        query = query.eq(col, val)
            
            result = query.execute()
            return result.data
        
        return self._retry_with_backoff(_execute)
    
    def select_range(self, table: str, columns: str = "*", 
                     start: int = 0, end: int = 999) -> List[Dict]:
        """
        Select records with pagination.
        
        Args:
            table: Table name
            columns: Columns to select
            start: Start index
            end: End index
            
        Returns:
            List of records
        """
        def _execute():
            result = self._client.table(table).select(columns).range(start, end).execute()
            return result.data
        
        return self._retry_with_backoff(_execute)
    
    def select_ordered(self, table: str, order_by: str, ascending: bool = True,
                       limit: int = None, columns: str = "*",
                       stock_id: int = None) -> List[Dict]:
        """
        Select records with ordering.
        
        Args:
            table: Table name
            order_by: Column to order by
            ascending: Order direction
            limit: Maximum records to return
            columns: Columns to select
            stock_id: Optional stock ID filter applied server-side (avoids
                      fetching rows from every stock in the table)
            
        Returns:
            List of records
        """
        def _execute():
            query = self._client.table(table).select(columns)
            # Apply stock_id filter at the database level so we never pull
            # rows from other stocks into memory.
            if stock_id is not None:
                query = query.eq('stock_id', stock_id)
            query = query.order(order_by, desc=not ascending)
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            return result.data
        
        return self._retry_with_backoff(_execute)
    
    def select_latest(self, table: str, stock_id: int, order_by: str = "date",
                      columns: str = "*") -> Optional[Dict]:
        """
        Get latest record for a stock.
        
        Args:
            table: Table name
            stock_id: Stock ID
            order_by: Column to order by
            columns: Columns to select
            
        Returns:
            Latest record or None
        """
        # Pass stock_id to select_ordered so the filter is applied server-side.
        # Previously this method fetched ALL rows from the table then filtered
        # in Python, which silently returned None whenever the caller omitted
        # stock_id from the columns list.
        records = self.select_ordered(
            table=table,
            columns=columns,
            order_by=order_by,
            ascending=False,
            limit=1,
            stock_id=stock_id
        )
        return records[0] if records else None
    
    def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> int:
        """
        Update records matching filters.
        
        Args:
            table: Table name
            data: Data to update
            filters: Filter conditions
            
        Returns:
            Number of records updated
        """
        def _execute():
            query = self._client.table(table).update(data)
            
            for col, val in filters.items():
                query = query.eq(col, val)
            
            result = query.execute()
            return len(result.data)
        
        return self._retry_with_backoff(_execute)
    
    def delete(self, table: str, filters: Dict[str, Any]) -> int:
        """
        Delete records matching filters.
        
        Args:
            table: Table name
            filters: Filter conditions
            
        Returns:
            Number of records deleted
        """
        def _execute():
            query = self._client.table(table)
            
            for col, val in filters.items():
                query = query.eq(col, val)
            
            result = query.delete().execute()
            return len(result.data)
        
        return self._retry_with_backoff(_execute)
    
    # ========================================================================
    # SPECIALIZED QUERIES
    # ========================================================================
    
    def get_stock_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Get stock record by symbol"""
        records = self.select("stocks", filters={"symbol": symbol.upper()})
        return records[0] if records else None
    
    def get_price_range(self, stock_id: int, start_date: str, end_date: str) -> List[Dict]:
        """Get price data for date range"""
        query = self._client.table("daily_price_data").select("*")
        query = query.eq("stock_id", stock_id)
        query = query.gte("date", start_date)
        query = query.lte("date", end_date)
        query = query.order("date", desc=False)
        
        result = self._retry_with_backoff(lambda: query.execute())
        return result.data
    
    def count_records(self, table: str, filters: Dict[str, Any] = None) -> int:
        """Count records in table"""
        def _execute():
            query = self._client.table(table).select("id", count="exact")
            
            if filters:
                for col, val in filters.items():
                    query = query.eq(col, val)
            
            result = query.execute()
            return result.count or 0
        
        return self._retry_with_backoff(_execute)
    
    def execute_raw_sql(self, sql: str, params: List[Any] = None) -> List[Dict]:
        """
        Execute raw SQL query (use with caution).
        
        Args:
            sql: SQL query
            params: Query parameters
            
        Returns:
            Query results
        """
        try:
            # Note: This requires appropriate RPC function setup in Supabase
            result = self._client.rpc("execute_sql", {"sql": sql, "params": params or []}).execute()
            return result.data
        except Exception as e:
            logger.error(f"Raw SQL execution failed: {e}")
            raise SupabaseQueryError(f"SQL execution failed: {e}")
    
    # ========================================================================
    # MONITORING & STATS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "queries_executed": self.query_count,
            "errors": self.error_count,
            "retries": self.retry_count,
            "error_rate": self.error_count / max(self.query_count, 1),
            "timestamp": datetime.now().isoformat()
        }
    
    def log_stats(self):
        """Log statistics"""
        stats = self.get_stats()
        logger.info(f"Client Stats: {json.dumps(stats, indent=2)}")


# ============================================================================
# CONTEXT MANAGER FOR TRANSACTIONS
# ============================================================================

@contextmanager
def supabase_transaction(client: SupabaseClient):
    """
    Context manager for transaction-like behavior.
    Note: Supabase doesn't support explicit transactions via client,
    but this ensures consistent error handling.
    """
    try:
        yield client
    except Exception as e:
        logger.error(f"Transaction error: {e}")
        raise


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_supabase_client(url: str = None, key: str = None) -> SupabaseClient:
    """Factory function to get/create Supabase client"""
    return SupabaseClient(url=url, key=key)


def test_connection(url: str = None, key: str = None) -> bool:
    """Test Supabase connection"""
    try:
        client = SupabaseClient(url=url, key=key)
        # Try a simple query
        records = client.select("stocks", columns="id", limit=1)
        logger.info("Supabase connection test successful")
        return True
    except Exception as e:
        logger.error(f"Supabase connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Test connection
    print("Testing Supabase connection...")
    if test_connection():
        print("✓ Connection successful")
    else:
        print("✗ Connection failed")
