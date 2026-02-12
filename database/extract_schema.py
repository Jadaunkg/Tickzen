"""
Database Schema Extractor
==========================
Extracts complete schema from Supabase database by querying all tables and their columns.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from database.supabase_client import SupabaseClient

def extract_schema():
    """Extract complete database schema."""
    print("=" * 80)
    print("DATABASE SCHEMA EXTRACTOR")
    print("=" * 80)
    
    db = SupabaseClient()
    
    # List of all tables in our database
    tables = [
        'stocks',
        'daily_price_data',
        'technical_indicators',
        'analyst_data',
        'forecast_data',
        'fundamental_data',
        'risk_data',
        'liquidity_risk_data',
        'altman_zscore_data',
        'regime_risk_data',
        'market_price_snapshot',
        'dividend_data',
        'ownership_data',
        'sentiment_data',
        'insider_transactions',
        'peer_comparison_data',
        'data_sync_log',
    ]
    
    schema_info = {}
    
    print(f"\n🔍 Extracting schema from {len(tables)} tables...\n")
    
    for table in tables:
        try:
            # Get sample record to extract columns
            result = db.select(table)
            
            if result:
                # Just get first record
                columns = list(result[0].keys())
                schema_info[table] = {
                    'columns': columns,
                    'sample_count': len(result)
                }
                print(f"✅ {table:<30}: {len(columns):>3} columns")
            else:
                # Table exists but is empty, try to get schema info differently
                print(f"⚠️  {table:<30}: Empty (will use base schema)")
                schema_info[table] = {
                    'columns': [],
                    'sample_count': 0
                }
                
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'relation' in error_msg.lower():
                print(f"❌ {table:<30}: Table doesn't exist")
            else:
                print(f"❌ {table:<30}: Error - {error_msg}")
    
    return schema_info

def generate_schema_file(schema_info):
    """Generate complete SQL schema file."""
    
    # Paths
    db_dir = Path(__file__).parent
    base_schema_path = db_dir / 'supabase_schema.sql'
    output_path = db_dir / 'COMPLETE_DATABASE_SCHEMA.sql'
    
    if base_schema_path.exists():
        print(f"\n📄 Reading base schema from: {base_schema_path.name}")
        with open(base_schema_path, 'r', encoding='utf-8') as f:
            base_schema = f.read()
    else:
        print("\n⚠️  No base schema found, will generate from scratch")
        base_schema = None
    
    print(f"\n📝 Generating complete schema...")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("-- ============================================================================\n")
        f.write("-- TICKZEN2 COMPLETE DATABASE SCHEMA\n")
        f.write("-- ============================================================================\n")
        f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- Database: Supabase PostgreSQL\n")
        f.write("-- Purpose: Complete schema for database replication\n")
        f.write("--\n")
        f.write("-- Usage:\n")
        f.write("--   1. Create new Supabase project\n")
        f.write("--   2. Go to SQL Editor\n")
        f.write("--   3. Run this entire script\n")
        f.write("--   4. Database structure will be recreated\n")
        f.write("-- ============================================================================\n\n")
        
        # Table summary
        f.write("-- TABLE SUMMARY\n")
        f.write("-- ============================================================================\n")
        for table, info in sorted(schema_info.items()):
            col_count = len(info['columns'])
            f.write(f"-- {table:<30}: {col_count:>3} columns\n")
        f.write("-- ============================================================================\n\n")
        
        # Column details
        f.write("-- DETAILED COLUMN LISTING\n")
        f.write("-- ============================================================================\n")
        for table, info in sorted(schema_info.items()):
            f.write(f"\n-- {table.upper()}\n")
            f.write("-- " + "-" * 76 + "\n")
            if info['columns']:
                for col in info['columns']:
                    f.write(f"--   • {col}\n")
            else:
                f.write("--   (Empty table - see base schema)\n")
        f.write("\n-- ============================================================================\n\n")
        
        # Include base schema if available
        if base_schema:
            f.write("-- ============================================================================\n")
            f.write("-- SCHEMA DEFINITIONS (from supabase_schema.sql)\n")
            f.write("-- ============================================================================\n\n")
            f.write(base_schema)
        else:
            f.write("-- ============================================================================\n")
            f.write("-- NOTE: Base schema not found\n")
            f.write("-- Please manually create tables or include supabase_schema.sql\n")
            f.write("-- ============================================================================\n")
    
    print(f"✅ Schema saved to: {output_path.name}")
    return output_path

def print_schema_summary(schema_info):
    """Print summary of extracted schema."""
    print("\n" + "=" * 80)
    print("SCHEMA EXTRACTION SUMMARY")
    print("=" * 80)
    
    total_tables = len(schema_info)
    total_columns = sum(len(info['columns']) for info in schema_info.values())
    
    print(f"\n📊 Statistics:")
    print(f"  • Total Tables: {total_tables}")
    print(f"  • Total Columns: {total_columns}")
    print(f"  • Average Columns per Table: {total_columns/total_tables:.1f}")
    
    print(f"\n📋 Largest Tables (by column count):")
    sorted_tables = sorted(schema_info.items(), key=lambda x: len(x[1]['columns']), reverse=True)
    for table, info in sorted_tables[:5]:
        print(f"  • {table:<30}: {len(info['columns']):>3} columns")

if __name__ == "__main__":
    try:
        # Extract schema
        schema_info = extract_schema()
        
        # Generate schema file
        output_path = generate_schema_file(schema_info)
        
        # Print summary
        print_schema_summary(schema_info)
        
        print(f"\n✅ Complete schema generated successfully!")
        print(f"\n📂 Location: {output_path}")
        print(f"\n💡 Use this file to recreate the exact database structure in a new Supabase project")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
