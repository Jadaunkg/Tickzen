"""
Reset Monthly Quotas Script

This script resets quotas for all users at the start of each month
Can be run as a cron job or Cloud Function
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from firebase_admin import firestore
from config.firebase_admin_setup import initialize_firebase_admin
from app.services.quota_service import get_quota_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reset_all_monthly_quotas(dry_run: bool = True):
    """
    Reset monthly quotas for all users
    
    Args:
        dry_run: If True, only simulate reset without writing to database
    """
    try:
        logger.info("=" * 60)
        logger.info("Monthly Quota Reset Script")
        logger.info(f"Run Date: {datetime.now(timezone.utc).isoformat()}")
        logger.info("=" * 60)
        
        # Initialize Firebase
        logger.info("\n[Step 1/3] Initializing Firebase Admin...")
        initialize_firebase_admin()
        db = firestore.client()
        logger.info("✅ Firebase initialized")
        
        # Get quota service
        logger.info("\n[Step 2/3] Initializing Quota Service...")
        quota_service = get_quota_service(db)
        logger.info("✅ Quota service ready")
        
        # Get all quota documents
        logger.info(f"\n[Step 3/3] Fetching quota documents (dry_run={dry_run})...")
        quotas_ref = db.collection('userQuotas')
        quota_docs = quotas_ref.stream()
        
        reset_count = 0
        error_count = 0
        
        for doc in quota_docs:
            try:
                user_uid = doc.id
                quota_data = doc.to_dict()
                
                if dry_run:
                    logger.info(f"  [DRY RUN] Would reset quota for user {user_uid}")
                    reset_count += 1
                else:
                    # Reset quota
                    quota_service.reset_monthly_quota(user_uid)
                    logger.info(f"  ✅ Reset quota for user {user_uid}")
                    reset_count += 1
                    
            except Exception as e:
                logger.error(f"  ❌ Error resetting quota for user {doc.id}: {e}")
                error_count += 1
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Reset Summary")
        logger.info("=" * 60)
        logger.info(f"Quotas reset: {reset_count}")
        logger.info(f"Errors: {error_count}")
        logger.info("=" * 60)
        
        if dry_run:
            logger.info("\n⚠️  This was a DRY RUN - no changes were made")
            logger.info("Run with --execute to actually reset quotas")
        else:
            logger.info("\n✅ Monthly reset complete!")
        
        return reset_count, error_count
        
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset monthly quotas for all users')
    parser.add_argument('--execute', action='store_true', help='Execute reset (default is dry run)')
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    reset_all_monthly_quotas(dry_run=dry_run)


if __name__ == "__main__":
    main()
