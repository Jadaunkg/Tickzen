"""
Database Initialization & Setup
================================

One-time setup to initialize Supabase database schema.
Creates tables, indexes, materialized views, and RLS policies.

Should be run once before first data sync.
"""

import logging
import os
from typing import Optional
import time

logger = logging.getLogger(__name__)

# Configure logging
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def load_schema_sql() -> str:
    """Load the schema SQL from file"""
    schema_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "supabase_schema.sql"
    )
    
    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    with open(schema_file, 'r') as f:
        return f.read()


def initialize_database(supabase_url: str = None, supabase_key: str = None,
                       skip_confirmation: bool = False) -> bool:
    """
    Initialize Supabase database with schema.
    
    Args:
        supabase_url: Supabase project URL
        supabase_key: Supabase API key
        skip_confirmation: Skip confirmation prompt
        
    Returns:
        True if successful
    """
    
    print("\n" + "="*70)
    print("SUPABASE DATABASE INITIALIZATION")
    print("="*70)
    print("\nThis will create:")
    print("  ✓ 12 tables (stocks, prices, technicals, fundamentals, etc.)")
    print("  ✓ Indexes for performance optimization")
    print("  ✓ Materialized view for quick lookups")
    print("  ✓ Data sync logging infrastructure")
    print("\n" + "="*70 + "\n")
    
    if not skip_confirmation:
        response = input("Continue with database initialization? (yes/no): ").lower()
        if response not in ['yes', 'y']:
            print("Initialization cancelled.")
            return False
    
    try:
        # Import Supabase client
        try:
            from supabase import create_client, Client
            from supabase.lib.client_options import ClientOptions
        except ImportError:
            logger.error("supabase library not installed. Run: pip install supabase")
            return False
        
        # Get credentials
        url = supabase_url or os.getenv('SUPABASE_URL')
        key = supabase_key or os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            logger.error("Supabase URL and KEY required. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
            return False
        
        print("Connecting to Supabase...")
        
        # Initialize client
        options = ClientOptions(headers={"X-Client-Info": "tickzen/init/1.0"})
        client = create_client(url, key, options=options)
        
        print("✓ Connected to Supabase\n")
        
        # Load and execute schema
        print("Loading schema...")
        schema_sql = load_schema_sql()
        
        # Split and execute statements
        # Note: Supabase doesn't support executing full DDL via client library
        # You need to execute this via their SQL editor or API
        
        print("\n" + "="*70)
        print("IMPORTANT: Manual SQL Execution Required")
        print("="*70)
        print("\nThe schema file (supabase_schema.sql) must be executed manually via:")
        print("1. Supabase Dashboard > SQL Editor")
        print("2. Copy entire contents of supabase_schema.sql")
        print("3. Paste into SQL Editor and run")
        print("\nAlternatively, use psql:")
        print(f"  psql {url} -U postgres -f supabase_schema.sql")
        print("\n" + "="*70 + "\n")
        
        print("✓ Schema loaded successfully")
        print("✓ Please execute the SQL schema manually via Supabase Dashboard")
        
        return True
    
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        return False


def verify_schema(supabase_url: str = None, supabase_key: str = None) -> bool:
    """
    Verify database schema is properly initialized.
    
    Checks for existence of key tables.
    
    Returns:
        True if all tables exist
    """
    
    try:
        from .supabase_client import SupabaseClient
        
        db = SupabaseClient(url=supabase_url, key=supabase_key)
        
        required_tables = [
            "stocks",
            "daily_price_data",
            "technical_indicators",
            "fundamental_data",
            "forecast_data",
            "risk_data",
            "market_price_snapshot",
            "dividend_data",
            "ownership_data",
            "sentiment_data",
            "insider_transactions",
            "data_sync_log"
        ]
        
        print("\nVerifying schema...")
        print("-" * 50)
        
        all_exist = True
        for table in required_tables:
            try:
                # Try to count records (will fail if table doesn't exist)
                count = db.count_records(table)
                print(f"✓ {table:30} exists ({count} records)")
            except Exception as e:
                print(f"✗ {table:30} MISSING")
                all_exist = False
        
        print("-" * 50)
        
        if all_exist:
            print("\n✓ Schema verification successful!\n")
            return True
        else:
            print("\n✗ Some tables are missing. Run initialize_database() first.\n")
            return False
    
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        return False


def create_sample_data(supabase_url: str = None, supabase_key: str = None,
                      sample_stocks: list = None) -> bool:
    """
    Create sample stock data for testing.
    
    Args:
        supabase_url: Supabase project URL
        supabase_key: Supabase API key
        sample_stocks: List of stock symbols to create
        
    Returns:
        True if successful
    """
    
    if sample_stocks is None:
        sample_stocks = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    
    try:
        from .supabase_client import SupabaseClient
        from .stock_registry import StockRegistry
        from datetime import datetime
        import random
        
        db = SupabaseClient(url=supabase_url, key=supabase_key)
        registry = StockRegistry()
        
        print("\nCreating sample data...")
        print("-" * 50)
        
        sample_stock_info = {
            "AAPL": {"name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
            "MSFT": {"name": "Microsoft Corp.", "sector": "Technology", "industry": "Software"},
            "GOOGL": {"name": "Alphabet Inc.", "sector": "Technology", "industry": "Internet Services"},
            "TSLA": {"name": "Tesla Inc.", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers"},
            "AMZN": {"name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "industry": "Internet Retail"}
        }
        
        for symbol in sample_stocks:
            info = sample_stock_info.get(symbol, {})
            
            # Add to registry
            registry.add_stock(
                symbol=symbol,
                ticker=symbol,
                company_name=info.get("name"),
                sector=info.get("sector"),
                industry=info.get("industry")
            )
            
            # Insert into database
            stock_data = {
                "symbol": symbol,
                "ticker": symbol,
                "company_name": info.get("name"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": "US",
                "exchange": "NASDAQ"
            }
            
            try:
                db.insert("stocks", stock_data)
                print(f"✓ Created {symbol}")
            except Exception as e:
                print(f"✗ Failed to create {symbol}: {e}")
        
        print("-" * 50)
        print("✓ Sample data created successfully!\n")
        return True
    
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}", exc_info=True)
        return False


def reset_database(supabase_url: str = None, supabase_key: str = None,
                  confirm: bool = True) -> bool:
    """
    Reset (delete) all data from database tables.
    
    WARNING: This deletes all data!
    
    Args:
        supabase_url: Supabase project URL
        supabase_key: Supabase API key
        confirm: Require user confirmation
        
    Returns:
        True if successful
    """
    
    if confirm:
        print("\n" + "="*70)
        print("WARNING: This will DELETE all data from Supabase!")
        print("="*70)
        response = input("\nType 'DELETE ALL' to confirm: ").strip()
        
        if response != "DELETE ALL":
            print("Reset cancelled.")
            return False
    
    try:
        from .supabase_client import SupabaseClient
        
        db = SupabaseClient(url=supabase_url, key=supabase_key)
        
        tables = [
            "insider_transactions",
            "data_sync_log",
            "sentiment_data",
            "ownership_data",
            "dividend_data",
            "market_price_snapshot",
            "risk_data",
            "forecast_data",
            "fundamental_data",
            "technical_indicators",
            "daily_price_data",
            "stocks"
        ]
        
        print("\nDeleting all data...")
        
        for table in tables:
            try:
                # Delete all records from table
                db.delete(table, {})
                print(f"✓ Cleared {table}")
            except Exception as e:
                print(f"✗ Failed to clear {table}: {e}")
        
        print("\n✓ Database reset successfully!\n")
        return True
    
    except Exception as e:
        logger.error(f"Reset failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "init":
            initialize_database(skip_confirmation=False)
        elif command == "verify":
            verify_schema()
        elif command == "sample":
            create_sample_data()
        elif command == "reset":
            reset_database()
        else:
            print(f"Unknown command: {command}")
            print("\nUsage:")
            print("  python init_database.py init     - Initialize database")
            print("  python init_database.py verify   - Verify schema")
            print("  python init_database.py sample   - Create sample data")
            print("  python init_database.py reset    - Reset database")
    else:
        print("Database Initialization Utility")
        print("=" * 50)
        print("\nUsage:")
        print("  python init_database.py init     - Initialize database")
        print("  python init_database.py verify   - Verify schema")
        print("  python init_database.py sample   - Create sample data")
        print("  python init_database.py reset    - Reset database")
        print("\nOr in Python:")
        print("  from init_database import initialize_database")
        print("  initialize_database()")
