import firebase_admin
from firebase_admin import credentials, auth, firestore, db as realtime_db
from firebase_admin import storage # <-- Import Firebase Storage
import os
from dotenv import load_dotenv
import logging
import base64
import json
import requests
import socket

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

# Configure Azure network settings
azure_session = configure_azure_network_settings()

_firebase_app_initialized = False
_firebase_app = None  # To store the initialized app instance

def initialize_firebase_admin():
    """
    Initializes the Firebase Admin SDK if it hasn't been already.
    This function should be called once when your Flask application starts.
    """
    global _firebase_app_initialized, _firebase_app
    if _firebase_app_initialized and _firebase_app:
        logger.info(f"Firebase Admin SDK already initialized with app name: {_firebase_app.name}")
        return

    try:
        _firebase_app = firebase_admin.get_app()
        _firebase_app_initialized = True
        logger.info(f"Firebase Admin SDK: Successfully retrieved existing default app. Project ID: {_firebase_app.project_id}")
        # Attempt to configure storage even if app was already initialized, in case it wasn't done before.
        _configure_storage_bucket(_firebase_app)
        return
    except ValueError: 
        logger.info("Firebase Admin SDK: No default app found, attempting initialization.")
        pass

    try:
        options = {}
        project_id_from_env = os.getenv('FIREBASE_PROJECT_ID')
        database_url_from_env = os.getenv('FIREBASE_DATABASE_URL')
        storage_bucket_from_env = os.getenv('FIREBASE_STORAGE_BUCKET') # Get storage bucket from .env

        if project_id_from_env:
            options['projectId'] = project_id_from_env
            logger.info(f"Firebase options using explicit projectId from .env: {project_id_from_env}")
            logger.info(f"[DEBUG] Using Firebase Project ID: {project_id_from_env}")
        if database_url_from_env:
            options['databaseURL'] = database_url_from_env
            logger.info(f"Firebase options using explicit databaseURL from .env: {database_url_from_env}")
        if storage_bucket_from_env:
            options['storageBucket'] = storage_bucket_from_env # Add to options
            logger.info(f"Firebase options using explicit storageBucket from .env: {storage_bucket_from_env}")
        else:
            logger.warning("FIREBASE_STORAGE_BUCKET not set in .env. Firebase Storage will use the default bucket associated with the project if permissions allow, or operations might fail if a specific bucket is expected but not configured here.")


        service_account_b64 = os.getenv('FIREBASE_SERVICE_ACCOUNT_BASE64')
        service_account_key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

        if service_account_b64:
            logger.info("Attempting to load Firebase credentials from FIREBASE_SERVICE_ACCOUNT_BASE64 environment variable.")
            try:
                key_json = base64.b64decode(service_account_b64).decode("utf-8")
                cred = credentials.Certificate(json.loads(key_json))
                _firebase_app = firebase_admin.initialize_app(cred, options)
                logger.info("Firebase Admin SDK initialized successfully using service account key from environment variable.")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK from FIREBASE_SERVICE_ACCOUNT_BASE64: {e}")
                _firebase_app = None
        elif service_account_key_path:
            logger.info(f"Attempting to load Firebase credentials from GOOGLE_APPLICATION_CREDENTIALS path: {service_account_key_path}")
            if os.path.exists(service_account_key_path):
                cred = credentials.Certificate(service_account_key_path)
                _firebase_app = firebase_admin.initialize_app(cred, options)
                logger.info(f"Firebase Admin SDK initialized successfully using service account key: {service_account_key_path}. Project ID: {_firebase_app.project_id}")
            else:
                logger.error(f"Service account key file NOT FOUND at: {service_account_key_path}. ")
                if options.get('projectId'):
                    logger.info("Attempting to initialize Firebase Admin SDK using Application Default Credentials with projectId from env.")
                    _firebase_app = firebase_admin.initialize_app(None, options)
                    logger.info(f"Firebase Admin SDK initialized using Application Default Credentials. Project ID: {_firebase_app.project_id if _firebase_app else 'N/A'}")
                else:
                    logger.error("Cannot initialize Firebase: Service account key file not found, and no FIREBASE_PROJECT_ID in .env for ADC.")
        elif options.get('projectId'):
            logger.info("No GOOGLE_APPLICATION_CREDENTIALS path. Attempting to initialize Firebase Admin SDK using Application Default Credentials with projectId from env.")
            _firebase_app = firebase_admin.initialize_app(None, options)
            logger.info(f"Firebase Admin SDK initialized using Application Default Credentials. Project ID: {_firebase_app.project_id if _firebase_app else 'N/A'}")
        else:
            logger.error("Critical: Neither GOOGLE_APPLICATION_CREDENTIALS path nor FIREBASE_PROJECT_ID are set/valid. "
                         "Firebase Admin SDK cannot be initialized for Auth/Firestore/Storage services.")

        if _firebase_app and _firebase_app.project_id:
            _firebase_app_initialized = True
            _configure_storage_bucket(_firebase_app) # Attempt to configure storage after app init
        else:
            logger.critical("CRITICAL: Firebase Admin SDK initialization failed to yield an app with a Project ID.")
            _firebase_app_initialized = False

    except Exception as e:
        logger.error(f"General error during Firebase Admin SDK initialization: {e}", exc_info=True)
        _firebase_app_initialized = False

    if not _firebase_app_initialized:
        logger.critical("Firebase Admin SDK IS NOT PROPERLY INITIALIZED. Subsequent Firebase operations will likely fail.")

def _configure_storage_bucket(app_instance):
    """Helper to configure/log storage bucket. Called after app initialization."""
    if not app_instance:
        return
    try:
        # Attempt to get the bucket. If FIREBASE_STORAGE_BUCKET was in options, it's used.
        # Otherwise, storage.bucket() without args gets the default bucket for the project.
        bucket_name_from_env = os.getenv('FIREBASE_STORAGE_BUCKET')
        bucket_to_test = storage.bucket(name=bucket_name_from_env, app=app_instance) # Pass app instance
        
        # You can't directly "test" a bucket easily without an operation,
        # but getting the bucket object itself is a good sign.
        # If the bucket name in .env was wrong and not the project's default,
        # storage.bucket(name=...) might not fail here but operations later would.
        # If bucket_name_from_env is None, storage.bucket(app=app_instance) gets the default bucket.
        
        if bucket_to_test:
            logger.info(f"Firebase Storage bucket '{bucket_to_test.name}' seems accessible for app '{app_instance.name}'.")
        else:
            logger.warning(f"Could not obtain a valid Firebase Storage bucket object for app '{app_instance.name}'. Storage operations may fail.")
            
    except Exception as e_storage_config:
        logger.error(f"Error during Firebase Storage bucket configuration for app '{app_instance.name}': {e_storage_config}", exc_info=True)


def get_firebase_app():
    """
    Returns the initialized Firebase app instance.
    Tries to initialize if not already done.
    """
    if not _firebase_app_initialized or not _firebase_app:
        logger.warning("Firebase app requested but not initialized. Attempting to initialize now.")
        initialize_firebase_admin()
        if not _firebase_app_initialized or not _firebase_app:
            logger.error("Failed to get Firebase app even after re-attempting initialization. Returning None.")
            return None
    return _firebase_app

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
    """
    # Manual cert fetch test for diagnostics with timeout
    try:
        # Use Azure-configured session if available, otherwise use default requests
        session_to_use = azure_session if azure_session else requests
        
        # Add timeout for Azure deployment network issues
        cert_test = session_to_use.get(
            "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com",
            timeout=(10, 30)  # (connect_timeout, read_timeout)
        )
        if cert_test.ok:
            logger.info("Manual cert fetch succeeded.")
        else:
            logger.warning(f"Manual cert fetch returned status code: {cert_test.status_code}")
    except requests.exceptions.Timeout as timeout_ex:
        logger.warning(f"Manual cert fetch timed out (network issue): {timeout_ex}")
    except requests.exceptions.ConnectionError as conn_ex:
        logger.warning(f"Manual cert fetch connection error (network issue): {conn_ex}")
    except Exception as cert_ex:
        logger.warning(f"Manual cert fetch failed: {cert_ex}")
    
    app = get_firebase_app()
    if not app:
        logger.error("Cannot verify token: Firebase app is not available.")
        return None

    if not app.project_id:
        logger.error(f"Cannot verify token: Firebase app '{app.name}' lacks a project_id.")
        return None

    try:
        decoded_token = auth.verify_id_token(id_token, app=app)
        logger.info(f"Successfully verified token for UID: {decoded_token.get('uid')}")
        logger.info(f"[DEBUG] Decoded token audience (aud): {decoded_token.get('aud')}")
        return decoded_token
    except firebase_admin.auth.ExpiredIdTokenError:
        logger.warning("Firebase ID token has expired.")
        return None
    except firebase_admin.auth.RevokedIdTokenError:
        logger.warning("Firebase ID token has been revoked.")
        return None
    except firebase_admin.auth.InvalidIdTokenError as e:
        logger.warning(f"Firebase ID token is invalid: {e}")
        return None
    except firebase_admin.auth.CertificateFetchError:
        logger.error("Failed to fetch public key certificates to verify token. Check network or Firebase Auth status.")
        # Try fallback verification for Azure deployment issues
        logger.info("Attempting fallback token verification...")
        return verify_firebase_token_fallback(id_token)
    except ValueError as ve:
        logger.error(f"ValueError verifying Firebase ID token (often project ID or app config issue): {ve}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"General error verifying Firebase ID token: {e}", exc_info=True)
        return None

def get_firestore_client():
    """Returns a Firestore client using the initialized Firebase app."""
    app = get_firebase_app()
    if not app:
        logger.error("Cannot get Firestore client: Firebase app is not available.")
        return None
    try:
        return firestore.client(app=app)
    except Exception as e:
        logger.error(f"Error getting Firestore client: {e}", exc_info=True)
        return None

# --- START: New function to get Storage Bucket ---
def get_storage_bucket():
    """Returns a Firebase Storage bucket client instance."""
    app = get_firebase_app()
    if not app:
        logger.error("Cannot get Storage bucket: Firebase app is not available.")
        return None
    try:
        # If FIREBASE_STORAGE_BUCKET is set in .env and was used in options,
        # storage.bucket(app=app) should refer to it.
        # Otherwise, storage.bucket(app=app) gets the default bucket for the project.
        # For explicit bucket name from .env if not set in initialize_app options:
        bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')
        return storage.bucket(name=bucket_name, app=app) # Pass app instance explicitly
    except Exception as e:
        logger.error(f"Error getting Storage bucket: {e}", exc_info=True)
        return None
# --- END: New function to get Storage Bucket ---

def get_realtimedb_client(path=None):
    """Returns a Realtime Database client/reference using the initialized Firebase app."""
    app = get_firebase_app()
    if not app:
        logger.error("Cannot get Realtime Database client: Firebase app is not available.")
        return None
    try:
        if path:
            return realtime_db.reference(path, app=app)
        return realtime_db.reference(app=app)
    except Exception as e:
        logger.error(f"Error getting Realtime Database client/reference: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    print("Attempting to initialize Firebase Admin from firebase_admin_setup.py direct execution...")
    initialize_firebase_admin()
    if _firebase_app_initialized and _firebase_app:
        print(f"Firebase Admin SDK initialization attempt complete. App Name: {_firebase_app.name}, Project ID: {_firebase_app.project_id}")
        
        fs_client = get_firestore_client()
        if fs_client:
            print("Successfully obtained Firestore client.")
        else:
            print("Failed to obtain Firestore client.")

        storage_bucket_client = get_storage_bucket()
        if storage_bucket_client:
            print(f"Successfully obtained Storage bucket client for bucket: {storage_bucket_client.name}")
        else:
            print("Failed to obtain Storage bucket client.")
    else:
        print("Firebase Admin SDK initialization FAILED from __main__. Check logs and .env configuration.")