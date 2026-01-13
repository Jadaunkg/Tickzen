"""
Migrate Existing Users to Quota System

This script initializes quota documents for all existing users in Firebase Auth
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Add parent directory to path to import app modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from firebase_admin import auth, firestore
from config.firebase_admin_setup import initialize_firebase_admin
from app.services.quota_service import QuotaService, get_quota_service
from config.quota_plans import DEFAULT_PLAN

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_all_users():
    """Get all users from Firebase Auth"""
    users = []
    page = auth.list_users()
    
    while page:
        for user in page.users:
            users.append(user)
        
        # Get next page
        page = page.get_next_page()
    
    return users


def migrate_user_quotas(dry_run: bool = True):
    """
    Migrate all existing users to quota system
    
    Args:
        dry_run: If True, only simulate migration without writing to database
    """
    try:
        logger.info("=" * 60)
        logger.info("User Quota Migration Script")
        logger.info("=" * 60)
        
        # Initialize Firebase
        logger.info("\n[Step 1/4] Initializing Firebase Admin...")
        initialize_firebase_admin()
        logger.info("✅ Firebase initialized")
        
        # Get quota service
        logger.info("\n[Step 2/4] Initializing Quota Service...")
        quota_service = get_quota_service()
        logger.info("✅ Quota service ready")
        
        # Get all users
        logger.info("\n[Step 3/4] Fetching users from Firebase Auth...")
        users = get_all_users()
        logger.info(f"✅ Found {len(users)} users")
        
        # Migrate users
        logger.info(f"\n[Step 4/4] Migrating users (dry_run={dry_run})...")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for user in users:
            try:
                user_uid = user.uid
                email = user.email or "no-email"
                
                # Check if user already has quota
                existing_quota = quota_service.get_user_quota(user_uid, use_cache=False)
                
                if existing_quota:
                    logger.info(f"  ⏭️  Skipping {email} - already has quota")
                    skipped_count += 1
                    continue
                
                if dry_run:
                    logger.info(f"  [DRY RUN] Would create quota for {email}")
                    migrated_count += 1
                else:
                    # Initialize quota for user
                    quota_service.initialize_user_quota(user_uid, plan_type=DEFAULT_PLAN)
                    logger.info(f"  ✅ Created quota for {email} with {DEFAULT_PLAN} plan")
                    migrated_count += 1
                    
            except Exception as e:
                logger.error(f"  ❌ Error migrating user {user.uid}: {e}")
                error_count += 1
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        logger.info(f"Total users: {len(users)}")
        logger.info(f"Migrated: {migrated_count}")
        logger.info(f"Skipped (already have quota): {skipped_count}")
        logger.info(f"Errors: {error_count}")
        logger.info("=" * 60)
        
        if dry_run:
            logger.info("\n⚠️  This was a DRY RUN - no changes were made")
            logger.info("Run with --execute to actually migrate users")
        else:
            logger.info("\n✅ Migration complete!")
        
        return migrated_count, skipped_count, error_count
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


def verify_migration():
    """Verify that all users have quotas"""
    try:
        logger.info("\n" + "=" * 60)
        logger.info("Verifying Migration")
        logger.info("=" * 60)
        
        # Initialize Firebase
        initialize_firebase_admin()
        quota_service = get_quota_service()
        
        # Get all users
        users = get_all_users()
        logger.info(f"Checking {len(users)} users...")
        
        missing_quotas = []
        
        for user in users:
            quota = quota_service.get_user_quota(user.uid, use_cache=False)
            if not quota:
                missing_quotas.append(user.email or user.uid)
        
        if missing_quotas:
            logger.warning(f"\n⚠️  {len(missing_quotas)} users missing quotas:")
            for email in missing_quotas:
                logger.warning(f"  - {email}")
        else:
            logger.info("\n✅ All users have quotas!")
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate existing users to quota system')
    parser.add_argument('--execute', action='store_true', help='Execute migration (default is dry run)')
    parser.add_argument('--verify', action='store_true', help='Verify migration')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_migration()
    else:
        dry_run = not args.execute
        migrate_user_quotas(dry_run=dry_run)


if __name__ == "__main__":
    main()
