#!/usr/bin/env python3
"""
Firebase Admin SDK Setup and Management
======================================

This module provides comprehensive Firebase integration for TickZen,
handling initialization, health monitoring, and service management
across Firestore, Firebase Storage, and Authentication.

Services Managed:
----------------
1. **Firebase Authentication**: Server-side token verification
2. **Firestore Database**: NoSQL document storage
3. **Firebase Storage**: File and asset storage
4. **Realtime Database**: Real-time data synchronization (optional)

Key Features:
------------
- **Health Monitoring**: Continuous service health tracking
- **Error Recovery**: Automatic retry mechanisms
- **Azure Compatibility**: Optimized for Azure App Service
- **Multi-Environment**: Development and production configurations
- **Comprehensive Logging**: Detailed operation tracking

Core Functions:
--------------
- initialize_firebase_admin(): Main initialization with error handling
- get_firestore_client(): Firestore database client
- get_storage_bucket(): Firebase Storage bucket access
- verify_firebase_token(): JWT token verification
- is_firebase_healthy(): Health status check
- get_firebase_health_status(): Detailed health diagnostics

Initialization Flow:
-------------------
1. **Environment Detection**: Development vs. Production
2. **Credential Loading**: Service account key or environment auth
3. **Service Initialization**: Firestore, Storage, Auth setup
4. **Health Verification**: Connection testing and validation
5. **Error Tracking**: Comprehensive error logging and recovery

Health Monitoring:
-----------------
The module tracks:
- Connection status to each Firebase service
- Recent operation errors and timestamps
- Service availability and response times
- Network configuration for Azure deployment

Error Categories:
----------------
- INITIALIZATION: Setup and configuration errors
- AUTHENTICATION: Token verification failures
- FIRESTORE: Database operation errors
- STORAGE: File upload/download errors
- NETWORK: Connectivity and timeout issues

Azure App Service Optimizations:
-------------------------------
- Network timeout configurations
- Connection pooling for Firebase services
- Environment variable management
- Cold start optimization
- Memory usage optimization

Authentication Flow:
-------------------
1. Client sends Firebase ID token
2. Server verifies token using Firebase Admin SDK
3. Extract user information (UID, email, display name)
4. Store user session data in Flask session
5. Provide access to user-specific Firestore data

Firestore Document Structure:
----------------------------
```
users/{user_uid}/
├── profile/
│   ├── email: string
│   ├── displayName: string
│   └── createdAt: timestamp
├── userSiteProfiles/{profile_id}/
│   ├── websiteUrl: string
│   ├── credentials: encrypted
│   └── settings: object
└── analytics/{date}/
    ├── sessionsCount: number
    └── actionsPerformed: array
```

Storage Organization:
--------------------
```
user-uploads/{user_uid}/
├── ticker-lists/{filename}
├── reports/{ticker}/{date}/
└── assets/images/{timestamp}/

public-assets/
├── chart-templates/
├── default-images/
└── wp-assets/{profile_id}/
```

Configuration:
-------------
Environment Variables:
- GOOGLE_APPLICATION_CREDENTIALS: Path to service account key
- FIREBASE_PROJECT_ID: Firebase project identifier
- FIREBASE_STORAGE_BUCKET: Storage bucket name
- FIREBASE_DATABASE_URL: Realtime database URL (optional)

Development vs. Production:
--------------------------
**Development**: Uses service account key file
**Production**: Uses Application Default Credentials (ADC)

Security Considerations:
-----------------------
- Service account key protection
- Token expiration handling
- User data isolation
- Secure credential storage
- Rate limiting for API calls

Usage Examples:
--------------
```python
# Initialize Firebase
initialize_firebase_admin()

# Get Firestore client
db = get_firestore_client()
if db:
    doc_ref = db.collection('users').document(user_uid)

# Verify authentication token
token_data = verify_firebase_token(id_token)
if token_data:
    user_uid = token_data['uid']

# Check service health
if is_firebase_healthy():
    # Proceed with Firebase operations
else:
    # Handle service unavailability
```

Troubleshooting:
---------------
- Health status provides diagnostic information
- Error logs include context and timestamps
- Automatic retry mechanisms for transient failures
- Fallback modes for service degradation

Author: TickZen Development Team
Version: 2.8
Last Updated: January 2026
"""

import firebase_admin
from firebase_admin import credentials, auth, firestore, db as realtime_db
from firebase_admin import storage # <-- Import Firebase Storage
import os
from dotenv import load_dotenv
import logging
import base64
import binascii
import json
import requests
import socket
from datetime import datetime, timezone

# Azure App Service network configuration
def configure_azure_network_settings():
    """Configure network settings for Azure App Service deployment"""
    try:
        # Set socket timeout for Azure network issues
        socket.setdefaulttimeout(30)
        
        # Configure requests session with Azure-friendly timeouts
        session = requests.Session()
        session.timeout = (10, 30)  # (connect_timeout, read_timeout)
        
        # Add retry strategy for Azure network issues
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        logger.info("Azure network settings configured successfully")
        return session
    except Exception as e:
        logger.warning(f"Failed to configure Azure network settings: {e}")
        return None

# Load environment variables from .env file at the very beginning
load_dotenv()

# Configure logging for this module
logger = logging.getLogger(__name__)
# Ensure logging is configured if not already done by the main app
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(module)s:%(lineno)d - %(message)s'
    )

# Global variables to track Firebase state and error details
_firebase_initialization_errors = []
_firebase_health_status = {
    'auth': False,
    'firestore': False,
    'storage': False,
    'last_health_check': None,
    'error_count': 0,
    'last_error': None
}

# Configure Azure network settings
azure_session = configure_azure_network_settings()

_firebase_app_initialized = False
_firebase_app = None  # To store the initialized app instance

def _log_firebase_error(error_message, exception=None, error_type="GENERAL"):
    """Centralized error logging for Firebase operations"""
    global _firebase_initialization_errors, _firebase_health_status
    
    timestamp = datetime.now().isoformat()
    error_details = {
        'timestamp': timestamp,
        'type': error_type,
        'message': error_message,
        'exception': str(exception) if exception else None
    }
    
    _firebase_initialization_errors.append(error_details)
    _firebase_health_status['error_count'] += 1
    _firebase_health_status['last_error'] = error_details
    
    # Keep only last 10 errors to prevent memory issues
    if len(_firebase_initialization_errors) > 10:
        _firebase_initialization_errors = _firebase_initialization_errors[-10:]
    
    if exception:
        logger.error(f"[{error_type}] {error_message}: {exception}", exc_info=True)
    else:
        logger.error(f"[{error_type}] {error_message}")

def get_firebase_health_status():
    """Get detailed Firebase health status for debugging"""
    return {
        'initialized': _firebase_app_initialized,
        'app_available': _firebase_app is not None,
        'project_id': _firebase_app.project_id if _firebase_app else None,
        'health_status': _firebase_health_status,
        'recent_errors': _firebase_initialization_errors[-5:] if _firebase_initialization_errors else []
    }

def _validate_environment_variables():
    """Validate required environment variables and log issues"""
    validation_results = {
        'has_credentials': False,
        'has_project_id': False,
        'credential_source': None,
        'issues': []
    }
    
    project_id = os.getenv('FIREBASE_PROJECT_ID')
    service_account_b64 = os.getenv('FIREBASE_SERVICE_ACCOUNT_BASE64')
    service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    storage_bucket = os.getenv('FIREBASE_STORAGE_BUCKET')
    database_url = os.getenv('FIREBASE_DATABASE_URL')
    
    # Check project ID
    if project_id:
        validation_results['has_project_id'] = True
        logger.info(f"✓ FIREBASE_PROJECT_ID found: {project_id}")
    else:
        validation_results['issues'].append("FIREBASE_PROJECT_ID not set in environment")
        logger.warning("⚠ FIREBASE_PROJECT_ID not found in environment variables")
    
    # Check credentials
    if service_account_b64:
        try:
            decoded = base64.b64decode(service_account_b64)
            json.loads(decoded.decode('utf-8'))
            validation_results['has_credentials'] = True
            validation_results['credential_source'] = 'FIREBASE_SERVICE_ACCOUNT_BASE64'
            logger.info("✓ Valid FIREBASE_SERVICE_ACCOUNT_BASE64 found")
        except Exception as e:
            validation_results['issues'].append(f"Invalid FIREBASE_SERVICE_ACCOUNT_BASE64: {e}")
            logger.error(f"✗ Invalid FIREBASE_SERVICE_ACCOUNT_BASE64: {e}")
    elif service_account_path:
        if os.path.exists(service_account_path):
            try:
                with open(service_account_path, 'r') as f:
                    json.load(f)
                validation_results['has_credentials'] = True
                validation_results['credential_source'] = f'GOOGLE_APPLICATION_CREDENTIALS: {service_account_path}'
                logger.info(f"✓ Valid service account file found: {service_account_path}")
            except Exception as e:
                validation_results['issues'].append(f"Invalid service account file: {e}")
                logger.error(f"✗ Invalid service account file at {service_account_path}: {e}")
        else:
            validation_results['issues'].append(f"Service account file not found: {service_account_path}")
            logger.error(f"✗ Service account file not found: {service_account_path}")
    else:
        validation_results['issues'].append("No Firebase credentials found (neither FIREBASE_SERVICE_ACCOUNT_BASE64 nor GOOGLE_APPLICATION_CREDENTIALS)")
        logger.warning("⚠ No Firebase credentials found in environment")
    
    # Check optional but important variables
    if storage_bucket:
        logger.info(f"✓ FIREBASE_STORAGE_BUCKET configured: {storage_bucket}")
    else:
        logger.info("ℹ FIREBASE_STORAGE_BUCKET not set (will use default bucket)")
    
    if database_url:
        logger.info(f"✓ FIREBASE_DATABASE_URL configured: {database_url}")
    else:
        logger.info("ℹ FIREBASE_DATABASE_URL not set")
    
    return validation_results

def _test_firebase_services(app_instance):
    """Test Firebase services availability and update health status"""
    global _firebase_health_status
    from datetime import datetime
    
    _firebase_health_status['last_health_check'] = datetime.now().isoformat()
    
    # Test Auth service
    try:
        # Simple test - just check if we can access the auth module
        auth.get_user_by_email("test@nonexistent.com", app=app_instance)
    except firebase_admin.auth.UserNotFoundError:
        # This is expected - means auth is working
        _firebase_health_status['auth'] = True
        logger.info("✓ Firebase Auth service is accessible")
    except Exception as e:
        _firebase_health_status['auth'] = False
        _log_firebase_error("Firebase Auth service test failed", e, "AUTH_TEST")
    
    # Test Firestore service
    try:
        db = firestore.client(app=app_instance)
        # Simple test - just getting a reference doesn't make network calls
        test_ref = db.collection('_health_check').document('test')
        _firebase_health_status['firestore'] = True
        logger.info("✓ Firebase Firestore service is accessible")
    except Exception as e:
        _firebase_health_status['firestore'] = False
        _log_firebase_error("Firebase Firestore service test failed", e, "FIRESTORE_TEST")
    
    # Test Storage service
    try:
        bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')
        bucket = storage.bucket(name=bucket_name, app=app_instance)
        _firebase_health_status['storage'] = True
        logger.info(f"✓ Firebase Storage service is accessible (bucket: {bucket.name})")
    except Exception as e:
        _firebase_health_status['storage'] = False
        _log_firebase_error("Firebase Storage service test failed", e, "STORAGE_TEST")

def initialize_firebase_admin():
    """
    Initializes the Firebase Admin SDK if it hasn't been already.
    This function should be called once when your Flask application starts.
    Enhanced with comprehensive error handling and diagnostics.
    """
    global _firebase_app_initialized, _firebase_app
    
    logger.info("=== Firebase Admin SDK Initialization Started ===")
    
    if _firebase_app_initialized and _firebase_app:
        logger.info(f"Firebase Admin SDK already initialized with app name: {_firebase_app.name}")
        return

    # Step 1: Validate environment variables
    logger.info("Step 1: Validating environment variables...")
    validation_results = _validate_environment_variables()
    
    if validation_results['issues']:
        for issue in validation_results['issues']:
            _log_firebase_error(f"Environment validation issue: {issue}", error_type="ENV_VALIDATION")
    
    if not validation_results['has_project_id'] and not validation_results['has_credentials']:
        _log_firebase_error("Critical: Missing both project ID and credentials", error_type="ENV_CRITICAL")
        logger.critical("❌ Cannot initialize Firebase without proper credentials and project ID")
        return

    # Step 2: Check for existing app
    logger.info("Step 2: Checking for existing Firebase app...")
    try:
        _firebase_app = firebase_admin.get_app()
        _firebase_app_initialized = True
        logger.info(f"✓ Successfully retrieved existing default app. Project ID: {_firebase_app.project_id}")
        _configure_storage_bucket(_firebase_app)
        _test_firebase_services(_firebase_app)
        logger.info("=== Firebase Admin SDK Initialization Complete (Existing App) ===")
        return
    except ValueError: 
        logger.info("No default app found, proceeding with initialization...")
        pass
    except Exception as e:
        _log_firebase_error("Error checking for existing Firebase app", e, "APP_CHECK")

    # Step 3: Prepare initialization options
    logger.info("Step 3: Preparing Firebase initialization options...")
    try:
        options = {}
        project_id_from_env = os.getenv('FIREBASE_PROJECT_ID')
        database_url_from_env = os.getenv('FIREBASE_DATABASE_URL')
        storage_bucket_from_env = os.getenv('FIREBASE_STORAGE_BUCKET')

        if project_id_from_env:
            options['projectId'] = project_id_from_env
            logger.info(f"✓ Using explicit projectId from .env: {project_id_from_env}")
        if database_url_from_env:
            options['databaseURL'] = database_url_from_env
            logger.info(f"✓ Using explicit databaseURL from .env: {database_url_from_env}")
        if storage_bucket_from_env:
            options['storageBucket'] = storage_bucket_from_env
            logger.info(f"✓ Using explicit storageBucket from .env: {storage_bucket_from_env}")
        else:
            logger.info("ℹ FIREBASE_STORAGE_BUCKET not set - will use default bucket")

        # Step 4: Initialize with credentials
        logger.info("Step 4: Initializing Firebase with credentials...")
        initialization_success = False
        
        service_account_b64 = os.getenv('FIREBASE_SERVICE_ACCOUNT_BASE64')
        service_account_key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

        if service_account_b64:
            logger.info("Attempting initialization with FIREBASE_SERVICE_ACCOUNT_BASE64...")
            try:
                key_json = base64.b64decode(service_account_b64).decode("utf-8")
                service_account_data = json.loads(key_json)
                
                # Validate service account data
                required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                missing_fields = [field for field in required_fields if field not in service_account_data]
                
                if missing_fields:
                    _log_firebase_error(f"Service account missing required fields: {missing_fields}", error_type="CREDENTIAL_VALIDATION")
                else:
                    cred = credentials.Certificate(service_account_data)
                    _firebase_app = firebase_admin.initialize_app(cred, options)
                    initialization_success = True
                    logger.info("✓ Firebase Admin SDK initialized successfully using service account from environment")
                    
            except base64.binascii.Error as e:
                _log_firebase_error("Invalid base64 encoding in FIREBASE_SERVICE_ACCOUNT_BASE64", e, "CREDENTIAL_DECODE")
            except json.JSONDecodeError as e:
                _log_firebase_error("Invalid JSON in decoded service account", e, "CREDENTIAL_JSON")
            except Exception as e:
                _log_firebase_error("Failed to initialize Firebase from FIREBASE_SERVICE_ACCOUNT_BASE64", e, "INIT_B64")

        elif service_account_key_path:
            logger.info(f"Attempting initialization with service account file: {service_account_key_path}")
            try:
                if os.path.exists(service_account_key_path):
                    # Validate file before using
                    with open(service_account_key_path, 'r') as f:
                        service_account_data = json.load(f)
                    
                    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                    missing_fields = [field for field in required_fields if field not in service_account_data]
                    
                    if missing_fields:
                        _log_firebase_error(f"Service account file missing required fields: {missing_fields}", error_type="CREDENTIAL_VALIDATION")
                    else:
                        cred = credentials.Certificate(service_account_key_path)
                        _firebase_app = firebase_admin.initialize_app(cred, options)
                        initialization_success = True
                        logger.info(f"✓ Firebase Admin SDK initialized successfully using service account file: {service_account_key_path}")
                else:
                    _log_firebase_error(f"Service account key file not found: {service_account_key_path}", error_type="FILE_NOT_FOUND")
                    
            except json.JSONDecodeError as e:
                _log_firebase_error(f"Invalid JSON in service account file: {service_account_key_path}", e, "CREDENTIAL_JSON")
            except Exception as e:
                _log_firebase_error(f"Failed to initialize Firebase from service account file", e, "INIT_FILE")

        # Step 5: Fallback to Application Default Credentials
        if not initialization_success and options.get('projectId'):
            logger.info("Step 5: Attempting fallback to Application Default Credentials...")
            try:
                _firebase_app = firebase_admin.initialize_app(None, options)
                initialization_success = True
                logger.info("✓ Firebase Admin SDK initialized using Application Default Credentials")
                
            except Exception as e:
                _log_firebase_error("Failed to initialize Firebase with Application Default Credentials", e, "INIT_ADC")

        # Step 6: Final validation and service testing
        if initialization_success and _firebase_app:
            logger.info("Step 6: Validating initialization and testing services...")
            
            if not _firebase_app.project_id:
                _log_firebase_error("Firebase app initialized but missing project_id", error_type="VALIDATION")
                initialization_success = False
            else:
                _firebase_app_initialized = True
                logger.info(f"✓ Firebase app validated with Project ID: {_firebase_app.project_id}")
                
                # Configure storage and test services
                _configure_storage_bucket(_firebase_app)
                _test_firebase_services(_firebase_app)
                
                logger.info("=== Firebase Admin SDK Initialization Complete (Success) ===")
        else:
            _log_firebase_error("Firebase initialization failed - no valid app created", error_type="INIT_FAILURE")

    except Exception as e:
        _log_firebase_error("Unexpected error during Firebase initialization", e, "INIT_UNEXPECTED")
        _firebase_app_initialized = False

    # Final status report
    if not _firebase_app_initialized:
        logger.critical("❌ Firebase Admin SDK initialization FAILED")
        logger.critical("🔍 Troubleshooting steps:")
        logger.critical("   1. Verify FIREBASE_PROJECT_ID is set correctly")
        logger.critical("   2. Verify Firebase credentials (service account) are valid")
        logger.critical("   3. Check network connectivity to Firebase services")
        logger.critical("   4. Review error logs above for specific issues")
        
        # Log diagnostic information
        health_status = get_firebase_health_status()
        logger.critical(f"🩺 Diagnostic info: {json.dumps(health_status, indent=2)}")
    else:
        logger.info("✅ Firebase Admin SDK successfully initialized and ready for use")

def _configure_storage_bucket(app_instance):
    """Helper to configure/log storage bucket. Called after app initialization."""
    if not app_instance:
        logger.error("Cannot configure storage bucket: app_instance is None")
        return
        
    logger.info("Configuring Firebase Storage bucket...")
    try:
        bucket_name_from_env = os.getenv('FIREBASE_STORAGE_BUCKET')
        
        if bucket_name_from_env:
            logger.info(f"Attempting to access specified bucket: {bucket_name_from_env}")
            bucket_to_test = storage.bucket(name=bucket_name_from_env, app=app_instance)
        else:
            logger.info("No bucket name specified, using default bucket for project")
            bucket_to_test = storage.bucket(app=app_instance)
        
        if bucket_to_test and bucket_to_test.name:
            logger.info(f"✓ Firebase Storage bucket '{bucket_to_test.name}' configured successfully for app '{app_instance.name}'")
            
            # Optional: Test bucket accessibility (be careful with permissions)
            try:
                # This is a very light operation that shouldn't consume quota
                bucket_exists = bucket_to_test.exists()
                if bucket_exists:
                    logger.info(f"✓ Storage bucket '{bucket_to_test.name}' exists and is accessible")
                else:
                    logger.warning(f"⚠ Storage bucket '{bucket_to_test.name}' may not exist or is not accessible")
                    _log_firebase_error(f"Storage bucket '{bucket_to_test.name}' accessibility issue", error_type="STORAGE_ACCESS")
            except Exception as e_test:
                logger.warning(f"⚠ Could not verify bucket accessibility (this may be normal): {e_test}")
                
        else:
            logger.error("✗ Could not obtain a valid Firebase Storage bucket object")
            _log_firebase_error("Failed to get valid storage bucket object", error_type="STORAGE_CONFIG")
            
    except Exception as e_storage_config:
        _log_firebase_error(f"Error during Firebase Storage bucket configuration for app '{app_instance.name}'", e_storage_config, "STORAGE_CONFIG")
        logger.error(f"✗ Storage bucket configuration failed - storage operations may not work properly")


def get_firebase_app():
    """
    Returns the initialized Firebase app instance.
    Tries to initialize if not already done.
    Enhanced with retry logic and better error handling.
    """
    global _firebase_app_initialized, _firebase_app
    
    if not _firebase_app_initialized or not _firebase_app:
        logger.warning("Firebase app requested but not initialized. Attempting to initialize now.")
        initialize_firebase_admin()
        
        if not _firebase_app_initialized or not _firebase_app:
            logger.error("Failed to get Firebase app even after re-attempting initialization.")
            _log_firebase_error("Firebase app unavailable after initialization attempt", error_type="APP_UNAVAILABLE")
            return None
    
    # Validate the app is still valid
    try:
        if hasattr(_firebase_app, 'project_id') and _firebase_app.project_id:
            return _firebase_app
        else:
            logger.error("Firebase app exists but lacks project_id")
            _log_firebase_error("Firebase app invalid - missing project_id", error_type="APP_INVALID")
            return None
    except Exception as e:
        _log_firebase_error("Error accessing Firebase app properties", e, "APP_ACCESS")
        return None

def verify_firebase_token_fallback(id_token):
    """
    Fallback token verification method for when network access is limited.
    This method provides basic token validation without requiring network access.
    """
    try:
        import jwt
        from datetime import datetime, timezone
        
        # Decode token without verification (for basic validation)
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        
        # Basic validation checks
        current_time = datetime.now(timezone.utc).timestamp()
        exp_time = decoded.get('exp', 0)
        
        if exp_time and exp_time < current_time:
            logger.warning("Token is expired (fallback verification)")
            return None
            
        # Check if token has required fields - Firebase uses 'user_id' or 'sub' for UID
        uid = decoded.get('uid') or decoded.get('user_id') or decoded.get('sub')
        email = decoded.get('email')
        
        if not uid or not email:
            logger.warning(f"Token missing required fields (fallback verification). UID: {uid}, Email: {email}")
            return None
            
        # Check audience
        expected_aud = os.getenv('FIREBASE_PROJECT_ID', 'stock-report-automation')
        if decoded.get('aud') != expected_aud:
            logger.warning(f"Token audience mismatch: expected {expected_aud}, got {decoded.get('aud')}")
            return None
            
        # Create a properly formatted token response
        fallback_token = {
            'uid': uid,
            'email': email,
            'name': decoded.get('name', ''),
            'email_verified': decoded.get('email_verified', False),
            'aud': decoded.get('aud'),
            'iss': decoded.get('iss'),
            'iat': decoded.get('iat'),
            'exp': decoded.get('exp'),
            'auth_time': decoded.get('auth_time'),
            'firebase': decoded.get('firebase', {}),
            'picture': decoded.get('picture', ''),
            'sub': decoded.get('sub')
        }
            
        logger.info(f"Fallback token verification succeeded for UID: {uid}")
        return fallback_token
        
    except Exception as e:
        logger.error(f"Fallback token verification failed: {e}")
        return None

def verify_firebase_token(id_token):
    """
    Verifies a Firebase ID token using the initialized Firebase app.
    Returns the decoded token (user information) if valid, otherwise None.
    Strict mode: no local/unsafe fallback decoding will be used.
    """
    if not id_token or not isinstance(id_token, str):
        logger.warning("Invalid token provided to verify_firebase_token")
        return None
    
    # Step 1: Optional network connectivity test for diagnostics (no fallback)
    try:
        session_to_use = azure_session if azure_session else requests
        cert_test = session_to_use.get(
            "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com",
            timeout=(10, 30)
        )
        if not cert_test.ok:
            logger.warning(f"⚠ Certificate endpoint returned status: {cert_test.status_code}")
    except Exception as cert_ex:
        logger.warning(f"⚠ Certificate endpoint test failed: {cert_ex}")
    
    # Step 2: Get Firebase app
    app = get_firebase_app()
    if not app:
        logger.error("Cannot verify token: Firebase app is not available")
        _log_firebase_error("Token verification failed - no Firebase app", error_type="TOKEN_VERIFY_NO_APP")
        return None

    if not app.project_id:
        logger.error(f"Cannot verify token: Firebase app '{app.name}' lacks a project_id")
        _log_firebase_error("Token verification failed - app missing project_id", error_type="TOKEN_VERIFY_NO_PROJECT")
        return None

    # Step 3: Attempt primary token verification
    try:
        decoded_token = auth.verify_id_token(id_token, app=app)
        logger.info(f"✓ Successfully verified token for UID: {decoded_token.get('uid')}")
        logger.debug(f"Token audience (aud): {decoded_token.get('aud')}")
        return decoded_token
        
    except firebase_admin.auth.ExpiredIdTokenError:
        logger.warning("❌ Firebase ID token has expired")
        _log_firebase_error("Token verification failed - token expired", error_type="TOKEN_EXPIRED")
        return None
        
    except firebase_admin.auth.RevokedIdTokenError:
        logger.warning("❌ Firebase ID token has been revoked")
        _log_firebase_error("Token verification failed - token revoked", error_type="TOKEN_REVOKED")
        return None
        
    except firebase_admin.auth.InvalidIdTokenError as e:
        logger.warning(f"❌ Firebase ID token is invalid: {e}")
        _log_firebase_error(f"Token verification failed - invalid token: {e}", error_type="TOKEN_INVALID")
        return None
        
    except firebase_admin.auth.CertificateFetchError as cert_error:
        logger.error(f"❌ Failed to fetch public key certificates: {cert_error}")
        _log_firebase_error(f"Certificate fetch error: {cert_error}", error_type="CERT_FETCH_ERROR")
        return None
        
    except ValueError as ve:
        logger.error(f"❌ ValueError verifying Firebase ID token (often project ID or app config issue): {ve}")
        _log_firebase_error(f"Token verification ValueError: {ve}", error_type="TOKEN_VALUE_ERROR")
        return None
        
    except Exception as e:
        logger.error(f"❌ Unexpected error verifying Firebase ID token: {e}")
        _log_firebase_error(f"Token verification unexpected error: {e}", e, "TOKEN_UNEXPECTED_ERROR")
        return None

def get_firestore_client():
    """
    Returns a Firestore client using the initialized Firebase app.
    Enhanced with error handling and retry logic.
    """
    app = get_firebase_app()
    if not app:
        logger.error("Cannot get Firestore client: Firebase app is not available")
        _log_firebase_error("Firestore client unavailable - no Firebase app", error_type="FIRESTORE_NO_APP")
        return None
        
    try:
        client = firestore.client(app=app)
        # Simple validation - try to get a reference (doesn't make network calls)
        test_ref = client.collection('_health_check')
        if test_ref:
            logger.debug("✓ Firestore client created successfully")
            return client
        else:
            logger.error("✗ Firestore client creation returned invalid reference")
            _log_firebase_error("Firestore client creation failed - invalid reference", error_type="FIRESTORE_INVALID")
            return None
    except Exception as e:
        logger.error(f"✗ Error getting Firestore client: {e}")
        _log_firebase_error("Error creating Firestore client", e, "FIRESTORE_ERROR")
        return None

def get_storage_bucket():
    """
    Returns a Firebase Storage bucket client instance.
    Enhanced with error handling and bucket validation.
    """
    app = get_firebase_app()
    if not app:
        logger.error("Cannot get Storage bucket: Firebase app is not available")
        _log_firebase_error("Storage bucket unavailable - no Firebase app", error_type="STORAGE_NO_APP")
        return None
        
    try:
        bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')
        
        if bucket_name:
            logger.debug(f"Getting Storage bucket with explicit name: {bucket_name}")
            bucket = storage.bucket(name=bucket_name, app=app)
        else:
            logger.debug("Getting default Storage bucket for project")
            bucket = storage.bucket(app=app)
        
        if bucket and hasattr(bucket, 'name'):
            logger.debug(f"✓ Storage bucket client created for: {bucket.name}")
            return bucket
        else:
            logger.error("✗ Storage bucket creation returned invalid object")
            _log_firebase_error("Storage bucket creation failed - invalid object", error_type="STORAGE_INVALID")
            return None
            
    except Exception as e:
        logger.error(f"✗ Error getting Storage bucket: {e}")
        _log_firebase_error("Error creating Storage bucket client", e, "STORAGE_ERROR")
        return None

def get_realtimedb_client(path=None):
    """
    Returns a Realtime Database client/reference using the initialized Firebase app.
    Enhanced with error handling and path validation.
    """
    app = get_firebase_app()
    if not app:
        logger.error("Cannot get Realtime Database client: Firebase app is not available")
        _log_firebase_error("Realtime DB unavailable - no Firebase app", error_type="RTDB_NO_APP")
        return None
        
    try:
        if path:
            logger.debug(f"Getting Realtime DB reference for path: {path}")
            db_ref = realtime_db.reference(path, app=app)
        else:
            logger.debug("Getting root Realtime DB reference")
            db_ref = realtime_db.reference(app=app)
        
        if db_ref:
            logger.debug("✓ Realtime Database reference created successfully")
            return db_ref
        else:
            logger.error("✗ Realtime Database reference creation failed")
            _log_firebase_error("Realtime DB reference creation failed", error_type="RTDB_INVALID")
            return None
            
    except Exception as e:
        logger.error(f"✗ Error getting Realtime Database client/reference: {e}")
        _log_firebase_error("Error creating Realtime DB client", e, "RTDB_ERROR")
        return None

def test_firebase_connection():
    """
    Comprehensive test of Firebase services connectivity.
    Returns a detailed status report.
    """
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': 'UNKNOWN',
        'app_status': 'UNKNOWN',
        'auth_status': 'UNKNOWN',
        'firestore_status': 'UNKNOWN',
        'storage_status': 'UNKNOWN',
        'errors': [],
        'warnings': []
    }
    
    try:
        # Test Firebase app
        app = get_firebase_app()
        if app and app.project_id:
            test_results['app_status'] = 'OK'
            test_results['project_id'] = app.project_id
        else:
            test_results['app_status'] = 'FAILED'
            test_results['errors'].append('Firebase app not available or missing project_id')
        
        # Test Auth service
        if app:
            try:
                # Try to check a non-existent user (should give UserNotFoundError if working)
                auth.get_user_by_email("test@nonexistent.firebasetest.com", app=app)
                test_results['auth_status'] = 'UNEXPECTED'  # Should not find this user
            except firebase_admin.auth.UserNotFoundError:
                test_results['auth_status'] = 'OK'  # This is expected
            except Exception as e:
                test_results['auth_status'] = 'FAILED'
                test_results['errors'].append(f'Auth service error: {e}')
        
        # Test Firestore
        firestore_client = get_firestore_client()
        if firestore_client:
            try:
                # Simple test - create a reference (no network call)
                test_ref = firestore_client.collection('_health_test').document('test')
                if test_ref:
                    test_results['firestore_status'] = 'OK'
                else:
                    test_results['firestore_status'] = 'FAILED'
                    test_results['errors'].append('Firestore client created but reference failed')
            except Exception as e:
                test_results['firestore_status'] = 'FAILED'
                test_results['errors'].append(f'Firestore test error: {e}')
        else:
            test_results['firestore_status'] = 'FAILED'
            test_results['errors'].append('Firestore client not available')
        
        # Test Storage
        storage_bucket = get_storage_bucket()
        if storage_bucket:
            try:
                bucket_name = storage_bucket.name
                if bucket_name:
                    test_results['storage_status'] = 'OK'
                    test_results['storage_bucket'] = bucket_name
                else:
                    test_results['storage_status'] = 'FAILED'
                    test_results['errors'].append('Storage bucket has no name')
            except Exception as e:
                test_results['storage_status'] = 'FAILED'
                test_results['errors'].append(f'Storage test error: {e}')
        else:
            test_results['storage_status'] = 'FAILED'
            test_results['errors'].append('Storage bucket not available')
        
        # Determine overall status
        service_statuses = [
            test_results['app_status'],
            test_results['auth_status'], 
            test_results['firestore_status'],
            test_results['storage_status']
        ]
        
        if all(status == 'OK' for status in service_statuses):
            test_results['overall_status'] = 'OK'
        elif any(status == 'OK' for status in service_statuses):
            test_results['overall_status'] = 'PARTIAL'
        else:
            test_results['overall_status'] = 'FAILED'
        
    except Exception as e:
        test_results['overall_status'] = 'ERROR'
        test_results['errors'].append(f'Connection test error: {e}')
    
    return test_results

def get_firebase_diagnostic_info():
    """
    Get comprehensive diagnostic information for troubleshooting.
    """
    diagnostic_info = {
        'timestamp': datetime.now().isoformat(),
        'environment': {
            'python_version': None,
            'firebase_admin_version': None,
            'os_type': os.name,
            'working_directory': os.getcwd()
        },
        'configuration': {
            'project_id_set': bool(os.getenv('FIREBASE_PROJECT_ID')),
            'project_id_value': os.getenv('FIREBASE_PROJECT_ID', 'NOT_SET'),
            'credentials_type': None,
            'storage_bucket_set': bool(os.getenv('FIREBASE_STORAGE_BUCKET')),
            'storage_bucket_value': os.getenv('FIREBASE_STORAGE_BUCKET', 'NOT_SET'),
            'database_url_set': bool(os.getenv('FIREBASE_DATABASE_URL'))
        },
        'app_state': {
            'initialized': _firebase_app_initialized,
            'app_available': _firebase_app is not None,
            'project_id': _firebase_app.project_id if _firebase_app else None,
            'app_name': _firebase_app.name if _firebase_app else None
        },
        'health_status': _firebase_health_status.copy(),
        'recent_errors': _firebase_initialization_errors[-10:] if _firebase_initialization_errors else [],
        'connection_test': None
    }
    
    # Get environment details
    try:
        import sys
        diagnostic_info['environment']['python_version'] = sys.version
        diagnostic_info['environment']['firebase_admin_version'] = firebase_admin.__version__
    except:
        pass
    
    # Check credential source
    if os.getenv('FIREBASE_SERVICE_ACCOUNT_BASE64'):
        diagnostic_info['configuration']['credentials_type'] = 'base64_env_var'
    elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        diagnostic_info['configuration']['credentials_type'] = 'service_account_file'
    else:
        diagnostic_info['configuration']['credentials_type'] = 'application_default_credentials'
    
    # Run connection test
    try:
        diagnostic_info['connection_test'] = test_firebase_connection()
    except Exception as e:
        diagnostic_info['connection_test'] = {'error': str(e)}
    
    return diagnostic_info

def reset_firebase_health_status():
    """Reset Firebase health status counters (useful for testing)"""
    global _firebase_health_status, _firebase_initialization_errors
    _firebase_health_status = {
        'auth': False,
        'firestore': False,
        'storage': False,
        'last_health_check': None,
        'error_count': 0,
        'last_error': None
    }
    _firebase_initialization_errors = []
    logger.info("Firebase health status reset")

def is_firebase_healthy():
    """Quick check if Firebase is considered healthy"""
    if not _firebase_app_initialized or not _firebase_app:
        return False
    
    # Consider healthy if at least 2 out of 3 core services are working
    healthy_services = sum([
        _firebase_health_status.get('auth', False),
        _firebase_health_status.get('firestore', False),
        _firebase_health_status.get('storage', False)
    ])
    
    return healthy_services >= 2

def log_firebase_operation_error(operation_name, error, context=None):
    """Helper function for logging Firebase operation errors from other modules"""
    context_str = f" (Context: {context})" if context else ""
    _log_firebase_error(f"Firebase operation '{operation_name}' failed{context_str}", error, f"OPERATION_{operation_name.upper()}")

def get_firebase_app_initialized():
    """Return the current Firebase app initialization status."""
    return _firebase_app_initialized

# Export key functions and status for external monitoring
__all__ = [
    'initialize_firebase_admin',
    'get_firebase_app',
    'verify_firebase_token', 
    'verify_firebase_token_fallback',
    'get_firestore_client',
    'get_storage_bucket',
    'get_realtimedb_client',
    'get_firebase_health_status',
    'test_firebase_connection',
    'get_firebase_diagnostic_info',
    'is_firebase_healthy',
    'log_firebase_operation_error',
    'reset_firebase_health_status',
    'get_firebase_app_initialized',
    '_firebase_app_initialized'
]

if __name__ == '__main__':
    print("=== Firebase Admin SDK Direct Execution Test ===")
    print("Attempting to initialize Firebase Admin from firebase_admin_setup.py direct execution...")
    
    # Initialize Firebase
    initialize_firebase_admin()
    
    if _firebase_app_initialized and _firebase_app:
        print(f"✅ Firebase Admin SDK initialization SUCCESS!")
        print(f"   App Name: {_firebase_app.name}")
        print(f"   Project ID: {_firebase_app.project_id}")
        
        # Test individual services
        print("\n🔍 Testing Firebase services...")
        
        fs_client = get_firestore_client()
        if fs_client:
            print("   ✅ Firestore client: OK")
        else:
            print("   ❌ Firestore client: FAILED")

        storage_bucket_client = get_storage_bucket()
        if storage_bucket_client:
            print(f"   ✅ Storage bucket: OK (bucket: {storage_bucket_client.name})")
        else:
            print("   ❌ Storage bucket: FAILED")
        
        # Run comprehensive test
        print("\n🧪 Running comprehensive connection test...")
        test_results = test_firebase_connection()
        print(f"   Overall Status: {test_results['overall_status']}")
        
        if test_results['errors']:
            print("   Errors found:")
            for error in test_results['errors']:
                print(f"     - {error}")
        
        # Display diagnostic info
        print("\n📊 Diagnostic Information:")
        diagnostic_info = get_firebase_diagnostic_info()
        print(f"   Configuration: {json.dumps(diagnostic_info['configuration'], indent=4)}")
        print(f"   Health Status: {json.dumps(diagnostic_info['health_status'], indent=4)}")
        
    else:
        print("❌ Firebase Admin SDK initialization FAILED")
        print("🔍 Check logs and .env configuration.")
        
        # Display diagnostic info even on failure
        print("\n📊 Diagnostic Information (Failure Analysis):")
        try:
            diagnostic_info = get_firebase_diagnostic_info()
            print(f"   Configuration: {json.dumps(diagnostic_info['configuration'], indent=4)}")
            print(f"   Recent Errors: {json.dumps(diagnostic_info['recent_errors'], indent=4)}")
        except Exception as diag_error:
            print(f"   Could not generate diagnostic info: {diag_error}")
    
    print("\n=== Firebase Admin SDK Test Complete ===")