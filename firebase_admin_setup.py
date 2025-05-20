import firebase_admin
from firebase_admin import credentials, auth, firestore, db as realtime_db # Added realtime_db for clarity
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
    Uses a unique app name to prevent re-initialization errors in some contexts.
    """
    global _firebase_app_initialized, _firebase_app
    if _firebase_app_initialized and _firebase_app:
        logger.info(f"Firebase Admin SDK already initialized with app name: {_firebase_app.name}")
        return

    # Generate a unique app name to avoid conflicts, e.g., during hot-reloading
    # Using a fixed name if you want to ensure you always get the same app instance.
    # For simplicity and avoiding "already initialized" with different configs,
    # let's try to get the default app first if it exists.
    try:
        _firebase_app = firebase_admin.get_app()
        _firebase_app_initialized = True
        logger.info(f"Firebase Admin SDK: Successfully retrieved existing default app. Project ID: {_firebase_app.project_id}")
        return
    except ValueError: # No default app exists, proceed to initialize
        logger.info("Firebase Admin SDK: No default app found, attempting initialization.")
        pass # Proceed to initialize a new app or default app

    try:
        options = {}
        project_id_from_env = os.getenv('FIREBASE_PROJECT_ID')
        database_url_from_env = os.getenv('FIREBASE_DATABASE_URL')
        storage_bucket_from_env = os.getenv('FIREBASE_STORAGE_BUCKET')

        if project_id_from_env:
            options['projectId'] = project_id_from_env
            logger.info(f"Firebase options using explicit projectId from .env: {project_id_from_env}")
        if database_url_from_env:
            options['databaseURL'] = database_url_from_env
            logger.info(f"Firebase options using explicit databaseURL from .env: {database_url_from_env}")
        if storage_bucket_from_env:
            options['storageBucket'] = storage_bucket_from_env
            logger.info(f"Firebase options using explicit storageBucket from .env: {storage_bucket_from_env}")

        service_account_key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

        if service_account_key_path:
            # Ensure the path is absolute or correctly resolvable
            # No, os.path.exists will use the path as is.
            # If relative, it's relative to the current working directory.
            
            logger.info(f"Attempting to load Firebase credentials from GOOGLE_APPLICATION_CREDENTIALS path: {service_account_key_path}")
            if os.path.exists(service_account_key_path):
                cred = credentials.Certificate(service_account_key_path)
                _firebase_app = firebase_admin.initialize_app(cred, options)
                logger.info(f"Firebase Admin SDK initialized successfully using service account key: {service_account_key_path}. Project ID: {_firebase_app.project_id}")
            else:
                logger.error(f"Service account key file NOT FOUND at: {service_account_key_path}. ")
                if options.get('projectId'):
                    logger.info("Attempting to initialize Firebase Admin SDK using Application Default Credentials with projectId from env.")
                    _firebase_app = firebase_admin.initialize_app(None, options) # ADC
                    logger.info(f"Firebase Admin SDK initialized using Application Default Credentials. Project ID: {_firebase_app.project_id if _firebase_app else 'N/A'}")
                else:
                    logger.error("Cannot initialize Firebase: Service account key file not found, and no FIREBASE_PROJECT_ID in .env for ADC.")
        elif options.get('projectId'):
            logger.info("No GOOGLE_APPLICATION_CREDENTIALS path. Attempting to initialize Firebase Admin SDK using Application Default Credentials with projectId from env.")
            _firebase_app = firebase_admin.initialize_app(None, options) # ADC
            logger.info(f"Firebase Admin SDK initialized using Application Default Credentials. Project ID: {_firebase_app.project_id if _firebase_app else 'N/A'}")
        else:
            logger.error("Critical: Neither GOOGLE_APPLICATION_CREDENTIALS path nor FIREBASE_PROJECT_ID are set/valid. "
                         "Firebase Admin SDK cannot be initialized for Auth/Firestore services.")

        if _firebase_app and _firebase_app.project_id:
            _firebase_app_initialized = True
        else:
            logger.critical("CRITICAL: Firebase Admin SDK initialization failed to yield an app with a Project ID.")
            _firebase_app_initialized = False # Ensure this is false if no project ID

    except Exception as e:
        logger.error(f"General error during Firebase Admin SDK initialization: {e}", exc_info=True)
        _firebase_app_initialized = False # Ensure this is false on any error

    if not _firebase_app_initialized:
        logger.critical("Firebase Admin SDK IS NOT PROPERLY INITIALIZED. Subsequent Firebase operations will likely fail.")


def get_firebase_app():
    """
    Returns the initialized Firebase app instance.
    Tries to initialize if not already done (should ideally be done at app startup).
    """
    if not _firebase_app_initialized or not _firebase_app:
        logger.warning("Firebase app requested but not initialized. Attempting to initialize now.")
        initialize_firebase_admin() # Attempt initialization
        if not _firebase_app_initialized or not _firebase_app: # Check again
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
    
    if not app.project_id: # Explicit check
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
        logger.warning(f"Firebase ID token is invalid: {e}") # More detailed log for invalid token
        return None
    except firebase_admin.auth.CertificateFetchError:
        logger.error("Failed to fetch public key certificates to verify token. Check network or Firebase Auth status.")
        return None
    except ValueError as ve: # Catch the specific project ID error more explicitly
        logger.error(f"ValueError verifying Firebase ID token (often project ID or app config issue): {ve}", exc_info=True)
        return None
    except Exception as e: # General catch-all
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
    # This block is for testing the module directly
    print("Attempting to initialize Firebase Admin from firebase_admin_setup.py direct execution...")
    initialize_firebase_admin()
    if _firebase_app_initialized and _firebase_app:
        print(f"Firebase Admin SDK initialization attempt complete. App Name: {_firebase_app.name}, Project ID: {_firebase_app.project_id}")
        # Example: try to get a firestore client
        fs_client = get_firestore_client()
        if fs_client:
            print("Successfully obtained Firestore client.")
        else:
            print("Failed to obtain Firestore client.")
    else:
        print("Firebase Admin SDK initialization FAILED from __main__. Check logs and .env configuration.")