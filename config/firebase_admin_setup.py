import firebase_admin
from firebase_admin import credentials, auth, firestore, db as realtime_db
from firebase_admin import storage # <-- Import Firebase Storage
import os
from dotenv import load_dotenv
import logging

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
        if database_url_from_env:
            options['databaseURL'] = database_url_from_env
            logger.info(f"Firebase options using explicit databaseURL from .env: {database_url_from_env}")
        if storage_bucket_from_env:
            options['storageBucket'] = storage_bucket_from_env # Add to options
            logger.info(f"Firebase options using explicit storageBucket from .env: {storage_bucket_from_env}")
        else:
            logger.warning("FIREBASE_STORAGE_BUCKET not set in .env. Firebase Storage will use the default bucket associated with the project if permissions allow, or operations might fail if a specific bucket is expected but not configured here.")


        service_account_key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

        if service_account_key_path:
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

def verify_firebase_token(id_token):
    """
    Verifies a Firebase ID token using the initialized Firebase app.
    Returns the decoded token (user information) if valid, otherwise None.
    """
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
        return None
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