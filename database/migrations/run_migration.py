"""
Advanced Risk Schema Migration Runner
=====================================
Applies SQL migrations to Supabase database.

USAGE OPTIONS:
1. Run specific migration:
   python run_migration.py 002_cleanup_unused_risk_columns.sql
   
2. Run all pending migrations:
   python run_migration.py all
   
3. Manual instructions:
   python run_migration.py 002_cleanup_unused_risk_columns.sql manual
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def print_manual_instructions(migration_file: Path):
    """Print instructions for manual migration."""
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    print("=" * 70)
    print("MANUAL MIGRATION INSTRUCTIONS")
    print("=" * 70)
    print(f"\n📋 Migration: {migration_file.name}\n")
    print("Follow these steps to apply the schema migration:\n")
    print("1. Go to your Supabase Dashboard")
    print("2. Navigate to: SQL Editor")
    print("3. Create a new query")
    print("4. Copy and paste the SQL below:")
    print("5. Click 'Run' to execute\n")
    print("=" * 70)
    print("SQL TO EXECUTE:")
    print("=" * 70)
    print(migration_sql)
    print("=" * 70)

def run_migration_auto(migration_file: Path):
    """Attempt automated migration via Supabase client."""
    try:
        from dotenv import load_dotenv
        from database.supabase_client import SupabaseClient
        
        # Load environment
        env_path = project_root / '.env'
        load_dotenv(dotenv_path=env_path)
        
        print("=" * 70)
        print(f"AUTOMATED MIGRATION: {migration_file.name}")
        print("=" * 70)
        
        # Read migration SQL
        print(f"\n📄 Reading migration: {migration_file.name}")
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Initialize Supabase client
        print("🔗 Connecting to Supabase...")
        supabase_client = SupabaseClient()
        
        # Try to execute the full migration SQL
        print("📤 Executing migration SQL...")
        
        try:
            # Attempt raw SQL execution (requires execute_sql RPC function in Supabase)
            result = supabase_client.execute_raw_sql(migration_sql)
            
            print(f"\n✅ Migration {migration_file.name} executed successfully!")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if 'function execute_sql' in error_msg.lower() or 'does not exist' in error_msg.lower():
                print(f"\n⚠️  Automated execution not available: {error_msg}")
                return False
            else:
                raise
                
    except Exception as e:
        print(f"\n❌ Automated migration failed: {e}")
        return False

def main():
    """Main entry point."""
    migrations_dir = Path(__file__).parent
    
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <migration_file|all> [manual]")
        print("\nExamples:")
        print("  python run_migration.py 002_cleanup_unused_risk_columns.sql")
        print("  python run_migration.py all")
        print("  python run_migration.py 002_cleanup_unused_risk_columns.sql manual")
        sys.exit(1)
    
    migration_arg = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'auto'
    
    # Get migration files
    if migration_arg == 'all':
        migration_files = sorted(migrations_dir.glob('*.sql'))
        if not migration_files:
            print("❌ No migration files found")
            sys.exit(1)
    else:
        migration_file = migrations_dir / migration_arg
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            sys.exit(1)
        migration_files = [migration_file]
    
    # Run migrations
    for migration_file in migration_files:
        if mode == 'manual':
            print_manual_instructions(migration_file)
        else:
            success = run_migration_auto(migration_file)
            if not success:
                print(f"\n🔄 Falling back to manual instructions for {migration_file.name}...\n")
                print_manual_instructions(migration_file)
                
                response = input("\n✋ Have you run the SQL in Supabase Dashboard? (yes/no): ")
                if response.lower() != 'yes':
                    print("⚠️  Migration halted. Apply the SQL manually and re-run this script.")
                    sys.exit(1)
        
        print(f"\n✅ {migration_file.name} complete\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
