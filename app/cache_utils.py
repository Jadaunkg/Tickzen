#!/usr/bin/env python3
"""
Cache Utilities for TickZen
===========================

Provides caching helpers, decorators, and utilities for optimizing
Firestore API calls and improving application performance.

Features:
---------
- Query performance monitoring
- Automatic cache invalidation
- Session-based caching for user data
- Counter document management
- Batch operation helpers
"""

import time
import logging
from functools import wraps
from flask import session, request, current_app
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

def monitor_query_performance(query_name):
    """
    Decorator to monitor Firestore query performance and log slow queries.
    
    Usage:
        @monitor_query_performance('get_user_reports')
        def fetch_reports(user_uid):
            return db.collection('reports').where('user_uid', '==', user_uid).get()
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = f(*args, **kwargs)
                duration = (time.time() - start) * 1000  # Convert to milliseconds
                
                # Log slow queries (>500ms)
                if duration > 500:
                    logger.warning(
                        f"SLOW QUERY: {query_name} took {duration:.2f}ms | "
                        f"Function: {f.__name__} | Args: {args[:2] if args else 'none'}"
                    )
                else:
                    logger.debug(f"Query {query_name} completed in {duration:.2f}ms")
                
                # You can integrate with monitoring services here
                # Example: metrics.histogram('firestore.query.duration', duration, tags=[f'query:{query_name}'])
                
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.error(
                    f"QUERY FAILED: {query_name} failed after {duration:.2f}ms | "
                    f"Error: {str(e)} | Function: {f.__name__}"
                )
                # metrics.increment('firestore.query.error', tags=[f'query:{query_name}'])
                raise
        
        return wrapper
    return decorator


# ============================================================================
# SESSION-BASED CACHING
# ============================================================================

def get_cached_user_profile(user_uid, fetch_function, ttl=600):
    """
    Get user profile from session cache or fetch from Firestore.
    
    Args:
        user_uid: User's unique identifier
        fetch_function: Function to fetch profile from Firestore (called if cache miss)
        ttl: Time to live in seconds (default 10 minutes)
    
    Returns:
        User profile data dictionary
    """
    cache_key = f'user_profile_{user_uid}'
    
    # Check session cache
    if cache_key in session:
        cache_data = session[cache_key]
        # Check if cache is still valid
        if time.time() - cache_data.get('timestamp', 0) < ttl:
            logger.debug(f"Cache HIT: User profile for {user_uid}")
            return cache_data.get('profile')
    
    # Cache miss - fetch from Firestore
    logger.debug(f"Cache MISS: Fetching user profile for {user_uid}")
    profile_data = fetch_function(user_uid)
    
    # Store in session cache
    if profile_data:
        session[cache_key] = {
            'profile': profile_data,
            'timestamp': time.time()
        }
    
    return profile_data


def invalidate_user_profile_cache(user_uid):
    """
    Invalidate cached user profile data.
    Call this after updating user profile in Firestore.
    """
    cache_key = f'user_profile_{user_uid}'
    if cache_key in session:
        del session[cache_key]
        logger.info(f"Cache INVALIDATE: User profile for {user_uid}")


def get_cached_site_profiles(user_uid, fetch_function, ttl=300):
    """
    Get site profiles from session cache or fetch from Firestore.
    
    Args:
        user_uid: User's unique identifier
        fetch_function: Function to fetch profiles from Firestore
        ttl: Time to live in seconds (default 5 minutes)
    
    Returns:
        List of site profile dictionaries
    """
    cache_key = f'site_profiles_{user_uid}'
    
    # Check session cache
    if cache_key in session:
        cache_data = session[cache_key]
        if time.time() - cache_data.get('timestamp', 0) < ttl:
            logger.debug(f"Cache HIT: Site profiles for {user_uid}")
            return cache_data.get('profiles')
    
    # Cache miss - fetch from Firestore
    logger.debug(f"Cache MISS: Fetching site profiles for {user_uid}")
    profiles = fetch_function(user_uid)
    
    # Store in session cache
    if profiles:
        session[cache_key] = {
            'profiles': profiles,
            'timestamp': time.time()
        }
    
    return profiles


def invalidate_site_profiles_cache(user_uid):
    """Invalidate cached site profiles."""
    cache_key = f'site_profiles_{user_uid}'
    if cache_key in session:
        del session[cache_key]
        logger.info(f"Cache INVALIDATE: Site profiles for {user_uid}")


# ============================================================================
# COUNTER DOCUMENT HELPERS
# ============================================================================

def get_counter_value(db, user_uid, counter_name, default=0):
    """
    Get counter value from userMetadata document.
    Much faster than using .count() queries.
    
    Args:
        db: Firestore client
        user_uid: User's unique identifier
        counter_name: Name of the counter field (e.g., 'totalReports', 'totalProfiles')
        default: Default value if counter doesn't exist
    
    Returns:
        Counter value as integer
    """
    try:
        counter_doc = db.collection('userMetadata').document(user_uid).get()
        if counter_doc.exists:
            return counter_doc.to_dict().get(counter_name, default)
        return default
    except Exception as e:
        logger.error(f"Error fetching counter {counter_name} for {user_uid}: {e}")
        return default


def increment_counter(db, user_uid, counter_name, increment_by=1):
    """
    Increment a counter in userMetadata document.
    
    Args:
        db: Firestore client
        user_uid: User's unique identifier
        counter_name: Name of the counter to increment
        increment_by: Amount to increment (default 1)
    """
    try:
        from firebase_admin import firestore
        
        counter_ref = db.collection('userMetadata').document(user_uid)
        counter_ref.set({
            counter_name: firestore.Increment(increment_by),
            'updatedAt': firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        logger.debug(f"Incremented {counter_name} for {user_uid} by {increment_by}")
    except Exception as e:
        logger.error(f"Error incrementing counter {counter_name} for {user_uid}: {e}")


def initialize_user_counters(db, user_uid):
    """
    Initialize counter document for a new user.
    
    Args:
        db: Firestore client
        user_uid: User's unique identifier
    """
    try:
        from firebase_admin import firestore
        
        counter_ref = db.collection('userMetadata').document(user_uid)
        
        # Only initialize if doesn't exist
        if not counter_ref.get().exists:
            counter_ref.set({
                'totalReports': 0,
                'totalProfiles': 0,
                'reportsToday': 0,
                'lastReportDate': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            logger.info(f"Initialized counters for user {user_uid}")
    except Exception as e:
        logger.error(f"Error initializing counters for {user_uid}: {e}")


def initialize_collection_counters(db):
    """
    Initialize counter documents for tracking collection statistics.
    This should be run once during setup to create the counter documents.
    
    Args:
        db: Firestore client
    
    Returns:
        dict: Initialization results
    """
    try:
        from firebase_admin import firestore
        
        results = {
            'initialized': [],
            'errors': []
        }
        
        # Initialize counters document for userGeneratedReports
        counter_ref = db.collection('_counters').document('userGeneratedReports')
        counter_ref.set({
            'total_count': 0,
            'initialized_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        results['initialized'].append('userGeneratedReports')
        logger.info("Initialized userGeneratedReports counter document")
        
        # Initialize counters document for userProfiles
        counter_ref = db.collection('_counters').document('userProfiles')
        counter_ref.set({
            'total_count': 0,
            'initialized_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        results['initialized'].append('userProfiles')
        logger.info("Initialized userProfiles counter document")
        
        # Initialize counters document for userPublishedArticles
        counter_ref = db.collection('_counters').document('userPublishedArticles')
        counter_ref.set({
            'total_count': 0,
            'initialized_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        results['initialized'].append('userPublishedArticles')
        logger.info("Initialized userPublishedArticles counter document")
        
        return results
    except Exception as e:
        logger.error(f"Error initializing collection counters: {e}")
        return {'initialized': [], 'errors': [str(e)]}


def sync_counters_with_actual_counts(db):
    """
    Synchronize counter documents with actual collection counts.
    This should be run periodically or after bulk operations to ensure counters are accurate.
    
    Args:
        db: Firestore client
    
    Returns:
        dict: Synchronization results with counts
    """
    try:
        from firebase_admin import firestore
        
        results = {}
        
        # Sync userGeneratedReports
        reports_count_query = db.collection('userGeneratedReports').count()
        reports_result = reports_count_query.get()
        actual_reports_count = reports_result[0][0].value if reports_result else 0
        
        counter_ref = db.collection('_counters').document('userGeneratedReports')
        counter_ref.set({
            'total_count': actual_reports_count,
            'last_synced_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        results['userGeneratedReports'] = actual_reports_count
        logger.info(f"Synced userGeneratedReports counter: {actual_reports_count}")
        
        # Sync userProfiles
        profiles_count_query = db.collection('userProfiles').count()
        profiles_result = profiles_count_query.get()
        actual_profiles_count = profiles_result[0][0].value if profiles_result else 0
        
        counter_ref = db.collection('_counters').document('userProfiles')
        counter_ref.set({
            'total_count': actual_profiles_count,
            'last_synced_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        results['userProfiles'] = actual_profiles_count
        logger.info(f"Synced userProfiles counter: {actual_profiles_count}")
        
        # Sync per-user counters for userGeneratedReports
        user_reports = db.collection('userGeneratedReports').stream()
        user_counts = {}
        for report in user_reports:
            user_uid = report.to_dict().get('user_uid')
            if user_uid:
                user_counts[user_uid] = user_counts.get(user_uid, 0) + 1
        
        # Update per-user counters
        for user_uid, count in user_counts.items():
            counter_ref = db.collection('_counters').document('userGeneratedReports')
            counter_ref.set({
                f'user_{user_uid}': count
            }, merge=True)
        
        results['per_user_counters'] = len(user_counts)
        logger.info(f"Synced {len(user_counts)} per-user counters")
        
        return results
    except Exception as e:
        logger.error(f"Error syncing counters: {e}")
        return {'error': str(e)}


def reset_daily_counters(db, user_uid):
    """
    Reset daily counters (should be called on new day).
    
    Args:
        db: Firestore client
        user_uid: User's unique identifier
    """
    try:
        from firebase_admin import firestore
        
        counter_ref = db.collection('userMetadata').document(user_uid)
        counter_ref.set({
            'reportsToday': 0,
            'lastReportDate': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'updatedAt': firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        logger.info(f"Reset daily counters for {user_uid}")
    except Exception as e:
        logger.error(f"Error resetting daily counters for {user_uid}: {e}")


# ============================================================================
# BATCH OPERATION HELPERS
# ============================================================================

def batch_get_documents(db, document_refs, max_batch_size=500):
    """
    Batch fetch multiple documents from Firestore.
    Much more efficient than individual get() calls.
    
    Args:
        db: Firestore client
        document_refs: List of document references
        max_batch_size: Maximum documents per batch (Firestore limit is 500)
    
    Returns:
        List of document snapshots
    """
    if not document_refs:
        return []
    
    all_docs = []
    
    # Split into batches if needed
    for i in range(0, len(document_refs), max_batch_size):
        batch_refs = document_refs[i:i + max_batch_size]
        try:
            docs = db.get_all(batch_refs)
            all_docs.extend(docs)
            logger.debug(f"Batch fetched {len(batch_refs)} documents")
        except Exception as e:
            logger.error(f"Error in batch get: {e}")
    
    return all_docs


def batch_write_documents(db, operations, max_batch_size=500):
    """
    Batch write multiple operations to Firestore.
    
    Args:
        db: Firestore client
        operations: List of tuples (operation_type, doc_ref, data)
                   operation_type can be 'set', 'update', or 'delete'
        max_batch_size: Maximum operations per batch (Firestore limit is 500)
    
    Returns:
        Number of successfully written operations
    """
    if not operations:
        return 0
    
    total_written = 0
    
    # Split into batches if needed
    for i in range(0, len(operations), max_batch_size):
        batch_ops = operations[i:i + max_batch_size]
        batch = db.batch()
        
        try:
            for op_type, doc_ref, data in batch_ops:
                if op_type == 'set':
                    batch.set(doc_ref, data)
                elif op_type == 'update':
                    batch.update(doc_ref, data)
                elif op_type == 'delete':
                    batch.delete(doc_ref)
            
            batch.commit()
            total_written += len(batch_ops)
            logger.debug(f"Batch wrote {len(batch_ops)} operations")
        except Exception as e:
            logger.error(f"Error in batch write: {e}")
    
    return total_written


# ============================================================================
# CACHE WARMING
# ============================================================================

def warm_user_cache(db, user_uid):
    """
    Pre-load frequently accessed user data into cache.
    Call this after user login for better performance.
    
    Args:
        db: Firestore client
        user_uid: User's unique identifier
    """
    try:
        # Fetch and cache user profile
        profile_doc = db.collection('userProfiles').document(user_uid).get()
        if profile_doc.exists:
            session[f'user_profile_{user_uid}'] = {
                'profile': profile_doc.to_dict(),
                'timestamp': time.time()
            }
        
        # Fetch and cache site profiles
        profiles_ref = db.collection('userSiteProfiles').document(user_uid).collection('profiles')
        profiles = [doc.to_dict() | {'profile_id': doc.id} for doc in profiles_ref.stream()]
        
        session[f'site_profiles_{user_uid}'] = {
            'profiles': profiles,
            'timestamp': time.time()
        }
        
        logger.info(f"Cache warmed for user {user_uid}")
    except Exception as e:
        logger.error(f"Error warming cache for {user_uid}: {e}")


# ============================================================================
# DECORATOR FOR CACHED ROUTES
# ============================================================================

def cached_user_profile(ttl=600):
    """
    Decorator to automatically cache user profile data for route handlers.
    
    Usage:
        @app.route('/profile')
        @login_required
        @cached_user_profile(ttl=600)
        def profile_page():
            profile = request.cached_profile  # Automatically available
            return render_template('profile.html', profile=profile)
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import session
            
            user_uid = session.get('firebase_user_uid')
            if not user_uid:
                return f(*args, **kwargs)
            
            cache_key = f'user_profile_{user_uid}'
            
            # Check session cache
            if cache_key in session:
                cache_data = session[cache_key]
                if time.time() - cache_data.get('timestamp', 0) < ttl:
                    # Attach cached profile to request
                    request.cached_profile = cache_data['profile']
                    return f(*args, **kwargs)
            
            # No valid cache - let the route handler fetch it
            # The route can use get_cached_user_profile() which will cache it
            request.cached_profile = None
            return f(*args, **kwargs)
        
        return wrapper
    return decorator
