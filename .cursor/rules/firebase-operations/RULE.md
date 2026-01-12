---
description: "Firebase operations patterns and best practices for TickZen - Firestore, Storage, and Auth"
alwaysApply: false
globs:
  - "**/config/firebase*.py"
  - "**/*firebase*.py"
  - "**/*firestore*.py"
---

# TickZen Firebase Operations Standards

## Golden Rule: ALWAYS Check Firebase Availability First

```python
# REQUIRED pattern for ALL Firebase operations
if not get_firebase_app_initialized():
    log_firebase_operation_error("operation_name", "Firebase not initialized")
    # Handle gracefully - return None, use fallback, or show error
    return None

# Only then proceed with Firebase operation
```

## Firestore Best Practices

### Document Structure
```python
# User Profile Document
userProfiles/{user_uid}
{
    "email": "user@example.com",
    "displayName": "John Doe",
    "created_at": Timestamp,
    "subscription_tier": "free|pro|enterprise",
    "preferences": {
        "notifications": {"email": bool, "automation": bool},
        "timezone": "America/New_York"
    }
}

# User Report Document
userGeneratedReports/{report_id}
{
    "user_uid": "user123",
    "ticker": "AAPL",
    "created_at": Timestamp,
    "report_path": "local/path/to/report.html",
    "storage_path": "user_reports/user123/AAPL_timestamp.html",
    "metadata": {
        "sections_count": 32,
        "word_count": 4500,
        "generation_time_seconds": 45
    }
}

# WordPress Profile Document
userSiteProfiles/{user_uid}/profiles/{profile_id}
{
    "site_name": "My Finance Blog",
    "site_url": "https://myblog.com",
    "username": "admin",
    "password": "encrypted_password",  # Consider encrypting
    "daily_limit": 5,
    "created_at": Timestamp,
    "last_used": Timestamp
}

# Processed Ticker Sub-Document
userSiteProfiles/{user_uid}/profiles/{profile_id}/processedTickers/{ticker}
{
    "status": "completed|failed|in_progress|queued",
    "publishedDate": Timestamp,
    "wordpressPostId": 12345,
    "errorMessage": "Error details if failed",
    "contentHash": "sha256_hash",
    "last_updated_at": Timestamp
}
```

### Querying Patterns

#### Simple Query
```python
def get_user_profile(user_uid):
    """Get user profile with error handling"""
    if not get_firebase_app_initialized():
        return None
    
    try:
        db = get_firestore_client()
        doc_ref = db.collection('userProfiles').document(user_uid)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            app.logger.info(f"User profile not found: {user_uid}")
            return None
            
    except Exception as e:
        app.logger.error(f"Error getting user profile: {e}", exc_info=True)
        log_firebase_operation_error("get_user_profile", str(e), {'user_uid': user_uid})
        return None
```

#### Query with Filters
```python
def get_recent_reports(user_uid, limit=20):
    """Get user's recent reports"""
    if not get_firebase_app_initialized():
        return []
    
    try:
        db = get_firestore_client()
        query = db.collection('userGeneratedReports') \
                 .where('user_uid', '==', user_uid) \
                 .order_by('created_at', direction='DESCENDING') \
                 .limit(limit)
        
        docs = query.stream()
        reports = []
        
        for doc in docs:
            try:
                data = doc.to_dict()
                data['id'] = doc.id
                reports.append(data)
            except Exception as parse_error:
                app.logger.warning(f"Failed to parse document {doc.id}: {parse_error}")
                continue
        
        return reports
        
    except Exception as e:
        app.logger.error(f"Error querying reports: {e}", exc_info=True)
        log_firebase_operation_error("get_recent_reports", str(e), {'user_uid': user_uid})
        return []
```

#### Pagination
```python
def get_reports_paginated(user_uid, page_size=20, start_after_doc=None):
    """Paginated query using cursor"""
    if not get_firebase_app_initialized():
        return {'reports': [], 'has_more': False, 'last_doc': None}
    
    try:
        db = get_firestore_client()
        query = db.collection('userGeneratedReports') \
                 .where('user_uid', '==', user_uid) \
                 .order_by('created_at', direction='DESCENDING') \
                 .limit(page_size + 1)  # Fetch one extra to check if there's more
        
        if start_after_doc:
            query = query.start_after(start_after_doc)
        
        docs = list(query.stream())
        has_more = len(docs) > page_size
        
        if has_more:
            docs = docs[:-1]  # Remove the extra document
        
        reports = [doc.to_dict() for doc in docs]
        last_doc = docs[-1] if docs else None
        
        return {
            'reports': reports,
            'has_more': has_more,
            'last_doc': last_doc
        }
        
    except Exception as e:
        app.logger.error(f"Pagination error: {e}", exc_info=True)
        return {'reports': [], 'has_more': False, 'last_doc': None}
```

### Writing Data

#### Create Document
```python
def create_user_profile(user_uid, email, display_name):
    """Create new user profile"""
    if not get_firebase_app_initialized():
        return False
    
    try:
        db = get_firestore_client()
        doc_ref = db.collection('userProfiles').document(user_uid)
        
        profile_data = {
            'email': email,
            'displayName': display_name,
            'created_at': firestore.SERVER_TIMESTAMP,
            'subscription_tier': 'free',
            'preferences': {
                'notifications': {
                    'email': False,
                    'automation': False
                }
            }
        }
        
        doc_ref.set(profile_data)
        app.logger.info(f"Created user profile: {user_uid}")
        return True
        
    except Exception as e:
        app.logger.error(f"Error creating profile: {e}", exc_info=True)
        log_firebase_operation_error("create_user_profile", str(e), {'user_uid': user_uid})
        return False
```

#### Update Document
```python
def update_user_preferences(user_uid, preferences):
    """Update user preferences (partial update)"""
    if not get_firebase_app_initialized():
        return False
    
    try:
        db = get_firestore_client()
        doc_ref = db.collection('userProfiles').document(user_uid)
        
        # Use merge=True for partial update
        doc_ref.set({
            'preferences': preferences,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        app.logger.info(f"Updated preferences for {user_uid}")
        return True
        
    except Exception as e:
        app.logger.error(f"Error updating preferences: {e}", exc_info=True)
        log_firebase_operation_error("update_user_preferences", str(e), {'user_uid': user_uid})
        return False
```

#### Atomic Updates
```python
def increment_report_count(user_uid):
    """Atomically increment report count"""
    if not get_firebase_app_initialized():
        return False
    
    try:
        db = get_firestore_client()
        doc_ref = db.collection('userProfiles').document(user_uid)
        
        # Atomic increment
        doc_ref.update({
            'total_reports': firestore.Increment(1),
            'last_report_at': firestore.SERVER_TIMESTAMP
        })
        
        return True
        
    except Exception as e:
        app.logger.error(f"Error incrementing count: {e}", exc_info=True)
        return False
```

#### Batch Writes
```python
def save_multiple_ticker_statuses(user_uid, profile_id, ticker_statuses):
    """Save multiple ticker statuses in a batch (atomic)"""
    if not get_firebase_app_initialized():
        return False
    
    try:
        db = get_firestore_client()
        batch = db.batch()
        
        for ticker, status_data in ticker_statuses.items():
            doc_ref = db.collection('userSiteProfiles') \
                       .document(user_uid) \
                       .collection('profiles') \
                       .document(profile_id) \
                       .collection('processedTickers') \
                       .document(ticker)
            
            batch.set(doc_ref, {
                **status_data,
                'last_updated_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
        
        # Commit all writes atomically
        batch.commit()
        app.logger.info(f"Batch saved {len(ticker_statuses)} ticker statuses")
        return True
        
    except Exception as e:
        app.logger.error(f"Batch write error: {e}", exc_info=True)
        log_firebase_operation_error("save_multiple_ticker_statuses", str(e), 
                                    {'user_uid': user_uid, 'count': len(ticker_statuses)})
        return False
```

#### Transactions
```python
from google.cloud.firestore import transactional

@transactional
def transfer_credits_transaction(transaction, from_uid, to_uid, amount):
    """Transfer credits between users atomically"""
    db = get_firestore_client()
    
    from_ref = db.collection('userProfiles').document(from_uid)
    to_ref = db.collection('userProfiles').document(to_uid)
    
    # Read phase
    from_doc = from_ref.get(transaction=transaction)
    from_credits = from_doc.to_dict().get('credits', 0)
    
    if from_credits < amount:
        raise ValueError("Insufficient credits")
    
    # Write phase
    transaction.update(from_ref, {'credits': from_credits - amount})
    transaction.update(to_ref, {'credits': firestore.Increment(amount)})

def transfer_credits(from_uid, to_uid, amount):
    """Wrapper for credit transfer"""
    if not get_firebase_app_initialized():
        return False
    
    try:
        db = get_firestore_client()
        transaction = db.transaction()
        transfer_credits_transaction(transaction, from_uid, to_uid, amount)
        return True
    except ValueError as ve:
        app.logger.warning(f"Credit transfer failed: {ve}")
        return False
    except Exception as e:
        app.logger.error(f"Transaction error: {e}", exc_info=True)
        return False
```

### Delete Operations
```python
def delete_user_data(user_uid):
    """Delete all user data (GDPR compliance)"""
    if not get_firebase_app_initialized():
        return False
    
    try:
        db = get_firestore_client()
        batch = db.batch()
        
        # Delete user profile
        profile_ref = db.collection('userProfiles').document(user_uid)
        batch.delete(profile_ref)
        
        # Delete reports
        reports = db.collection('userGeneratedReports') \
                   .where('user_uid', '==', user_uid) \
                   .stream()
        
        for report in reports:
            batch.delete(report.reference)
        
        # Commit deletions
        batch.commit()
        app.logger.info(f"Deleted all data for user {user_uid}")
        return True
        
    except Exception as e:
        app.logger.error(f"Error deleting user data: {e}", exc_info=True)
        return False
```

## Firebase Storage Best Practices

### Upload File
```python
def save_report_to_firebase_storage(user_uid, ticker, filename, content):
    """Upload report to Firebase Storage with retry"""
    if not get_firebase_app_initialized():
        app.logger.warning("Firebase unavailable, saving locally only")
        return None
    
    try:
        bucket = get_storage_bucket()
        blob_path = f"user_reports/{user_uid}/{filename}"
        blob = bucket.blob(blob_path)
        
        # Upload with metadata
        blob.metadata = {
            'user_uid': user_uid,
            'ticker': ticker,
            'uploaded_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Upload with retry on transient failures
        blob.upload_from_string(
            content,
            content_type='text/html',
            timeout=60,
            retry=google.api_core.retry.Retry(
                initial=1.0,
                maximum=10.0,
                multiplier=2.0,
                deadline=60.0
            )
        )
        
        app.logger.info(f"Uploaded report to Storage: {blob_path}")
        return blob_path
        
    except google.api_core.exceptions.GoogleAPIError as e:
        app.logger.error(f"Firebase Storage API error: {e}", exc_info=True)
        log_firebase_operation_error("storage_upload", str(e), 
                                    {'user_uid': user_uid, 'filename': filename})
        return None
        
    except Exception as e:
        app.logger.error(f"Unexpected storage error: {e}", exc_info=True)
        return None
```

### Download File
```python
def get_report_from_firebase_storage(storage_path):
    """Download report from Firebase Storage"""
    if not get_firebase_app_initialized():
        return None
    
    try:
        bucket = get_storage_bucket()
        blob = bucket.blob(storage_path)
        
        if not blob.exists():
            app.logger.warning(f"Blob not found: {storage_path}")
            return None
        
        # Download as string
        content = blob.download_as_text()
        return content
        
    except google.api_core.exceptions.NotFound:
        app.logger.warning(f"Storage object not found: {storage_path}")
        return None
        
    except Exception as e:
        app.logger.error(f"Error downloading from storage: {e}", exc_info=True)
        return None
```

### Generate Signed URL
```python
from datetime import timedelta

def generate_signed_url(storage_path, expiration_hours=24):
    """Generate temporary signed URL for file access"""
    if not get_firebase_app_initialized():
        return None
    
    try:
        bucket = get_storage_bucket()
        blob = bucket.blob(storage_path)
        
        # Generate URL valid for specified hours
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET"
        )
        
        return url
        
    except Exception as e:
        app.logger.error(f"Error generating signed URL: {e}", exc_info=True)
        return None
```

### List Files
```python
def list_user_reports_in_storage(user_uid, max_results=100):
    """List user's reports in Storage"""
    if not get_firebase_app_initialized():
        return []
    
    try:
        bucket = get_storage_bucket()
        prefix = f"user_reports/{user_uid}/"
        
        blobs = bucket.list_blobs(prefix=prefix, max_results=max_results)
        
        files = []
        for blob in blobs:
            files.append({
                'name': blob.name,
                'size': blob.size,
                'created': blob.time_created,
                'updated': blob.updated,
                'public_url': blob.public_url if blob.public_url else None
            })
        
        return files
        
    except Exception as e:
        app.logger.error(f"Error listing storage files: {e}", exc_info=True)
        return []
```

### Delete File
```python
def delete_from_storage(storage_path):
    """Delete file from Firebase Storage"""
    if not get_firebase_app_initialized():
        return False
    
    try:
        bucket = get_storage_bucket()
        blob = bucket.blob(storage_path)
        
        if blob.exists():
            blob.delete()
            app.logger.info(f"Deleted from storage: {storage_path}")
            return True
        else:
            app.logger.warning(f"Blob doesn't exist: {storage_path}")
            return False
            
    except Exception as e:
        app.logger.error(f"Error deleting from storage: {e}", exc_info=True)
        return False
```

## Firebase Auth Integration

### Verify Token
```python
def verify_user_token(id_token):
    """Verify Firebase Auth token"""
    if not get_firebase_app_initialized():
        return None
    
    try:
        decoded_token = verify_firebase_token(id_token)
        if decoded_token:
            return {
                'uid': decoded_token.get('uid'),
                'email': decoded_token.get('email'),
                'email_verified': decoded_token.get('email_verified', False)
            }
        return None
        
    except Exception as e:
        app.logger.error(f"Token verification error: {e}", exc_info=True)
        return None
```

### Create User
```python
def create_firebase_user(email, password, display_name):
    """Create user in Firebase Auth"""
    if not get_firebase_app_initialized():
        return None
    
    try:
        user = firebase_auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=False
        )
        
        app.logger.info(f"Created Firebase user: {user.uid}")
        
        # Also create Firestore profile
        create_user_profile(user.uid, email, display_name)
        
        return user.uid
        
    except Exception as e:
        app.logger.error(f"Error creating user: {e}", exc_info=True)
        return None
```

## Performance Optimization

### Caching Firestore Queries
```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache user profiles for 5 minutes
@lru_cache(maxsize=1000)
def get_cached_user_profile(user_uid, cache_time):
    """Cached user profile retrieval"""
    return get_user_profile(user_uid)

def get_user_profile_with_cache(user_uid):
    """Get user profile with time-based cache invalidation"""
    # Cache key changes every 5 minutes
    cache_key = datetime.now().replace(second=0, microsecond=0) // timedelta(minutes=5)
    return get_cached_user_profile(user_uid, cache_key)
```

### Batch Operations
```python
# Instead of N separate writes:
for ticker in tickers:
    save_ticker_status(user_uid, profile_id, ticker, status)  # ❌ Slow

# Use batch write:
save_multiple_ticker_statuses(user_uid, profile_id, all_statuses)  # ✅ Fast
```

## Security Rules

### Firestore Rules Example
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // User profiles - users can only read/write their own
    match /userProfiles/{uid} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }
    
    // Reports - users can only access their own
    match /userGeneratedReports/{reportId} {
      allow read: if request.auth != null && 
                   resource.data.user_uid == request.auth.uid;
      allow write: if request.auth != null && 
                    request.resource.data.user_uid == request.auth.uid;
    }
    
    // WordPress profiles - user-scoped
    match /userSiteProfiles/{uid}/profiles/{profileId} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }
  }
}
```

### Storage Rules Example
```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // User reports - users can only access their own
    match /user_reports/{uid}/{allPaths=**} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }
  }
}
```

## Monitoring & Logging

### Log All Firebase Operations
```python
def log_firebase_operation(operation, success, **context):
    """Log Firebase operation for monitoring"""
    log_entry = {
        'operation': operation,
        'success': success,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **context
    }
    
    if success:
        app.logger.info(f"Firebase operation succeeded: {json.dumps(log_entry)}")
    else:
        app.logger.error(f"Firebase operation failed: {json.dumps(log_entry)}")
```

## Testing Firebase Operations

### Mock Firebase in Tests
```python
from unittest.mock import Mock, patch

def test_save_report():
    """Test report saving with mocked Firebase"""
    with patch('config.firebase_admin_setup.get_firebase_app_initialized', return_value=True), \
         patch('config.firebase_admin_setup.get_firestore_client') as mock_db:
        
        mock_collection = Mock()
        mock_db.return_value.collection.return_value = mock_collection
        
        # Call function
        result = save_report_metadata(user_uid, ticker, metadata)
        
        # Verify Firebase was called correctly
        mock_collection.document.assert_called_once()
        assert result is True
```

## Checklist

Before deploying Firebase operations:
- [ ] All Firebase calls check `get_firebase_app_initialized()` first
- [ ] Error handling for all Firebase operations
- [ ] Logging with context for debugging
- [ ] Graceful fallbacks when Firebase is unavailable
- [ ] Batch operations used where appropriate
- [ ] Security rules configured correctly
- [ ] Indexes created for all queries
- [ ] Data backup strategy in place
- [ ] Tests mock Firebase (don't hit real database)
- [ ] Production Firebase project configured
