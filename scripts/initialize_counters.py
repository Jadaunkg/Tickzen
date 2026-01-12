#!/usr/bin/env python3
"""
Initialize Counter Documents
=============================

This script initializes counter documents in Firestore for efficient
count queries without using expensive count() aggregations.

Usage:
    python scripts/initialize_counters.py

What it does:
    1. Creates counter documents in _counters collection
    2. Syncs counters with actual collection counts
    3. Sets up per-user counters for userGeneratedReports
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.firebase_admin_setup import get_firestore_client
from app.cache_utils import initialize_collection_counters, sync_counters_with_actual_counts

def main():
    """Initialize and sync counter documents"""
    print("=" * 70)
    print("FIRESTORE COUNTER INITIALIZATION")
    print("=" * 70)
    print()
    
    # Get Firestore client
    db = get_firestore_client()
    if not db:
        print("❌ ERROR: Could not get Firestore client!")
        print("Please check your firebase_admin_setup.py configuration.")
        return 1
    
    print("✅ Firebase client obtained successfully")
    print()
    
    # Step 1: Initialize counter documents
    print("Step 1: Initializing counter documents...")
    print("-" * 70)
    init_results = initialize_collection_counters(db)
    
    if init_results['initialized']:
        print(f"✅ Initialized {len(init_results['initialized'])} counter documents:")
        for collection in init_results['initialized']:
            print(f"   - {collection}")
    
    if init_results['errors']:
        print(f"❌ Errors during initialization:")
        for error in init_results['errors']:
            print(f"   - {error}")
    
    print()
    
    # Step 2: Sync counters with actual counts
    print("Step 2: Syncing counters with actual collection counts...")
    print("-" * 70)
    print("⏳ This may take a while for large collections...")
    print()
    
    sync_results = sync_counters_with_actual_counts(db)
    
    if 'error' in sync_results:
        print(f"❌ Error during synchronization: {sync_results['error']}")
        return 1
    
    print("✅ Counter synchronization complete!")
    print()
    print("Results:")
    print(f"   - userGeneratedReports: {sync_results.get('userGeneratedReports', 0)} documents")
    print(f"   - userProfiles: {sync_results.get('userProfiles', 0)} documents")
    print(f"   - Per-user counters: {sync_results.get('per_user_counters', 0)} users tracked")
    print()
    
    # Summary
    print("=" * 70)
    print("INITIALIZATION COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Counter documents are now ready to use")
    print("2. The application will use get_counter_value() for fast counts")
    print("3. Counters will auto-increment when new documents are added")
    print("4. Run this script periodically to ensure counters stay in sync")
    print()
    print("Counter documents location: _counters collection")
    print("You can view them in Firebase Console > Firestore Database")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
