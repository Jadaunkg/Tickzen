import os
import traceback
from datetime import datetime, timezone

# We import from the existing config module
# This maintains compatibility while providing a centralized access point
try:
    from config.firebase_admin_setup import (
        initialize_firebase_admin, 
        verify_firebase_token, 
        get_firestore_client, 
        get_storage_bucket, 
        get_firebase_app, 
        get_firebase_health_status,
        is_firebase_healthy, 
        log_firebase_operation_error, 
        get_firebase_app_initialized
    )
    CONFIG_IMPORT_SUCCESS = True
except ImportError:
    CONFIG_IMPORT_SUCCESS = False
    # Define minimal mocks if import fails
    def verify_firebase_token(token): return None
    def get_firestore_client(): return None
    def get_storage_bucket(): return None
    def get_firebase_app(): return None
    def is_firebase_healthy(): return False
    def log_firebase_operation_error(operation, error, context=None): pass
    def get_firebase_app_initialized(): return False
    def get_firebase_health_status(): return {'recent_errors': [], 'status': 'unavailable'}
    def initialize_firebase_admin(): pass

# Global state for initialization status
FIREBASE_INITIALIZED_SUCCESSFULLY = False

def init_firebase(is_worker_process=True):
    """
    Initialize Firebase Admin SDK with error handling and mocking fallback.
    Returns boolean indicating success.
    """
    global FIREBASE_INITIALIZED_SUCCESSFULLY
    
    if not is_worker_process:
        print("⏭️  Skipping Firebase initialization in reloader parent process")
        FIREBASE_INITIALIZED_SUCCESSFULLY = True
        return True

    if not CONFIG_IMPORT_SUCCESS:
        print("CRITICAL: Failed to import config.firebase_admin_setup")
        FIREBASE_INITIALIZED_SUCCESSFULLY = False
        return False

    try:
        print("Initializing Firebase Admin SDK...")
        initialize_firebase_admin()
        
        # Get the current initialization status after initialization
        FIREBASE_INITIALIZED_SUCCESSFULLY = get_firebase_app_initialized()
        
        if FIREBASE_INITIALIZED_SUCCESSFULLY:
            print("✅ Firebase Admin SDK initialized successfully")
            
            # Get health status for logging
            health_status = get_firebase_health_status()
            if health_status.get('recent_errors'):
                print("⚠ Note: Some Firebase services had initialization warnings:")
                for error in health_status.get('recent_errors', [])[-3:]:
                    print(f"   - {error.get('type', 'UNKNOWN')}: {error.get('message', 'No message')}")
        else:
            print("❌ CRITICAL: Firebase Admin SDK not initialized correctly")
            _log_diagnostic_info()
            
    except Exception as e:
        print(f"UNEXPECTED: Error during Firebase setup: {e}")
        FIREBASE_INITIALIZED_SUCCESSFULLY = False
        
    return FIREBASE_INITIALIZED_SUCCESSFULLY

def _log_diagnostic_info():
    try:
        health_status = get_firebase_health_status()
        print("🔍 Diagnostic information:")
        print(f"   - Recent errors: {len(health_status.get('recent_errors', []))}")
        if health_status.get('recent_errors'):
            latest_error = health_status['recent_errors'][-1]
            print(f"   - Latest error: {latest_error.get('type')}: {latest_error.get('message')}")
    except Exception as diag_error:
        print(f"   - Could not get diagnostic info: {diag_error}")

# Wrapper functions that handle failure states safely
def safe_get_firestore_client():
    if not CONFIG_IMPORT_SUCCESS: return None
    return get_firestore_client()

def safe_verify_firebase_token(token):
    if not CONFIG_IMPORT_SUCCESS: return None
    try:
        return verify_firebase_token(token)
    except Exception:
        return None

def safe_get_storage_bucket():
    if not CONFIG_IMPORT_SUCCESS: return None
    return get_storage_bucket()
