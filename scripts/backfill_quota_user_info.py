"""
Backfill User Email and Display Name to Quota Documents
Updates existing quota documents with user email and display name from userProfiles
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from firebase_admin import firestore
from config.firebase_admin_setup import initialize_firebase_admin

def backfill_user_info():
    """Backfill email and display_name to quota documents"""
    
    # Initialize Firebase
    initialize_firebase_admin()
    db = firestore.client()
    
    print("🔄 Starting user info backfill for quota documents...")
    print("=" * 60)
    
    # Get all quota documents
    quotas_ref = db.collection('userQuotas')
    quota_docs = list(quotas_ref.stream())
    
    total_users = len(quota_docs)
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"📊 Found {total_users} quota documents\n")
    
    for doc in quota_docs:
        user_uid = doc.id
        quota_data = doc.to_dict()
        
        try:
            # Check if already has email and display_name
            has_email = 'user_email' in quota_data and quota_data.get('user_email') != 'N/A'
            has_name = 'user_displayName' in quota_data and quota_data.get('user_displayName') != 'N/A'
            
            if has_email and has_name:
                print(f"⏭️  Skip: {user_uid[:8]}... (already has user info)")
                skipped_count += 1
                continue
            
            # Get user profile
            profile_ref = db.collection('userProfiles').document(user_uid)
            profile_doc = profile_ref.get()
            
            if not profile_doc.exists:
                print(f"⚠️  No profile for {user_uid[:8]}... - skipping")
                skipped_count += 1
                continue
            
            profile_data = profile_doc.to_dict()
            email = profile_data.get('email', 'N/A')
            display_name = profile_data.get('display_name', email.split('@')[0] if email != 'N/A' else 'User')
            
            # Update quota document
            update_data = {}
            if not has_email:
                update_data['user_email'] = email
            if not has_name:
                update_data['user_displayName'] = display_name
            
            if update_data:
                quotas_ref.document(user_uid).update(update_data)
                print(f"✅ Updated: {user_uid[:8]}... → {display_name} ({email})")
                updated_count += 1
            else:
                skipped_count += 1
                
        except Exception as e:
            print(f"❌ Error updating {user_uid[:8]}...: {str(e)}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print("📈 Backfill Summary:")
    print(f"   Total Users: {total_users}")
    print(f"   ✅ Updated: {updated_count}")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print(f"   ❌ Errors: {error_count}")
    print("=" * 60)
    
    if error_count > 0:
        print("\n⚠️  Some updates failed. Check errors above.")
        return 1
    
    print("\n🎉 Backfill completed successfully!")
    return 0


if __name__ == '__main__':
    try:
        exit_code = backfill_user_info()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏸️  Backfill interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
