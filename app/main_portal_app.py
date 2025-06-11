# main_portal_app.py

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import io
from functools import wraps
import re
import traceback
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import firestore
# Note: `storage` is not directly imported here anymore at the top level.
# We will use get_storage_bucket from firebase_admin_setup

import pandas as pd

FIREBASE_INITIALIZED_SUCCESSFULLY = True
AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY = True
PIPELINE_IMPORTED_SUCCESSFULLY = True

try:
    # Ensure get_storage_bucket is imported from your setup file
    from config.firebase_admin_setup import initialize_firebase_admin, verify_firebase_token, get_firestore_client, get_storage_bucket
    initialize_firebase_admin()
    from config.firebase_admin_setup import _firebase_app_initialized
    FIREBASE_INITIALIZED_SUCCESSFULLY = _firebase_app_initialized
    if not FIREBASE_INITIALIZED_SUCCESSFULLY:
        print("CRITICAL: Firebase Admin SDK not initialized correctly via firebase_admin_setup.")
except ImportError as e_fb_admin:
    print(f"CRITICAL: Failed to import or initialize Firebase Admin from firebase_admin_setup: {e_fb_admin}")
    FIREBASE_INITIALIZED_SUCCESSFULLY = False
    def verify_firebase_token(token): print("Firebase dummy: verify_firebase_token called"); return None
    def get_firestore_client(): print("Firebase dummy: get_firestore_client called"); return None
    def get_storage_bucket(): print("Firebase dummy: get_storage_bucket called from dummy setup"); return None # Mock

try:
    from automation_scripts import auto_publisher
    AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY = True
except ImportError as e_ap:
    print(f"CRITICAL: Failed to import auto_publisher.py: {e_ap}")
    AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY = False
    class MockAutoPublisher:
        ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP = 10
        def load_state(self, user_uid=None, current_profile_ids_from_run=None): return {}
        def trigger_publishing_run(self, user_uid, profiles_to_process_data_list, articles_to_publish_per_profile_map,
                                   custom_tickers_by_profile_id=None, uploaded_file_details_by_profile_id=None,
                                   socketio_instance=None, user_room=None, save_status_callback=None): # Added callback
            print("MockAutoPublisher: trigger_publishing_run called");
            if socketio_instance and user_room:
                 socketio_instance.emit('automation_update', {
                    'profile_id': "MockProfile", 'ticker': "MOCK", 'phase': "Mocking",
                    'stage': "Called", 'message': "Automation service is mocked.", 'status': "warning",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, room=user_room)
            # Simulate saving status via callback for one ticker
            if save_status_callback and profiles_to_process_data_list:
                mock_profile_id = profiles_to_process_data_list[0].get('profile_id', "MockProfile")
                mock_status_data = {
                    # 'ticker' key is not needed here as it's passed as a separate arg to save_processed_ticker_status
                    'status': 'Published (Mock)',
                    'generation_time': datetime.now(timezone.utc).isoformat(),
                    'publish_time': datetime.now(timezone.utc).isoformat(),
                    'writer_username': 'MockWriter',
                    # 'last_updated_at' will be set by save_processed_ticker_status
                }
                # The ticker symbol itself is passed as the third argument
                save_status_callback(user_uid, mock_profile_id, 'MOCKAAPL', mock_status_data)
            return {}
    auto_publisher = MockAutoPublisher()


try:
    from automation_scripts.pipeline import run_pipeline, run_wp_pipeline
    PIPELINE_IMPORTED_SUCCESSFULLY = True
except ImportError as e_pipeline:
    print(f"CRITICAL: Failed to import pipeline.py: {e_pipeline}")
    PIPELINE_IMPORTED_SUCCESSFULLY = False
    def run_pipeline(*args, socketio_instance=None, task_room=None, **kwargs):
        print("Mock Pipeline: run_pipeline called");
        if socketio_instance and task_room:
            socketio_instance.emit('analysis_error', {'message': 'Stock Analysis service is temporarily unavailable (mocked).', 'ticker': args[0] if args else 'N/A'}, room=task_room)
        return None, None, "Error: Mock Stock Analysis Pipeline not available", None
    def run_wp_pipeline(*args, socketio_instance=None, task_room=None, **kwargs):
        print("Mock Pipeline: run_wp_pipeline called");
        if socketio_instance and task_room:
            socketio_instance.emit('wp_asset_error', {'message': 'WordPress Asset service is temporarily unavailable (mocked).', 'ticker': args[0] if args else 'N/A'}, room=task_room)
        return None, None, "Error: Mock WordPress Asset Pipeline not available", {}


load_dotenv()
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER_PATH = os.path.join(APP_ROOT, 'static')
TEMPLATE_FOLDER_PATH = os.path.join(APP_ROOT, 'templates')
UPLOAD_FOLDER = os.path.join(APP_ROOT, '..', 'generated_data', 'temp_uploads')
STOCK_REPORTS_SUBDIR = 'stock_reports'
STOCK_REPORTS_PATH = os.path.join(APP_ROOT, '..', 'generated_data', 'stock_reports')

app = Flask(__name__,
            static_folder=STATIC_FOLDER_PATH,
            template_folder=TEMPLATE_FOLDER_PATH)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_strong_default_secret_key_here_CHANGE_ME_TOO")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

socketio = SocketIO(app,
                    async_mode='eventlet',
                    cors_allowed_origins="*",
                    ping_timeout=60,
                    ping_interval=25,
                    logger=True,
                    engineio_logger=True
                   )


for folder_path in [UPLOAD_FOLDER, STATIC_FOLDER_PATH, STOCK_REPORTS_PATH]:
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
            app.logger.info(f"Created directory: {folder_path}")
        except OSError as e:
            app.logger.error(f"Could not create directory {folder_path}: {e}")

# --- Helper Functions for Firebase Storage and Ticker Parsing ---

def upload_file_to_storage(user_uid, profile_id, file_object, original_filename):
    """Uploads a file to Firebase Storage and returns its path."""
    bucket = get_storage_bucket() # Uses the imported function
    if not bucket:
        app.logger.error(f"Storage bucket not available for upload. Profile: {profile_id}, User: {user_uid}")
        return None
    if file_object and original_filename:
        filename = secure_filename(original_filename)
        storage_path = f"user_ticker_files/{user_uid}/{profile_id}/{filename}"
        app.logger.info(f"Attempting to upload '{filename}' to Firebase Storage path: {storage_path}")
        try:
            blob = bucket.blob(storage_path)
            file_object.seek(0)
            blob.upload_from_file(file_object, content_type=file_object.content_type)
            app.logger.info(f"File {filename} uploaded successfully to {storage_path} for profile {profile_id}.")
            return storage_path
        except Exception as e:
            app.logger.error(f"Firebase Storage Upload Error for '{filename}' (Path: '{storage_path}'): {e}", exc_info=True)
            return None
    app.logger.warning(f"Upload to Firebase Storage skipped: file_object or original_filename missing for profile {profile_id}")
    return None

def delete_file_from_storage(storage_path):
    """Deletes a file from Firebase Storage."""
    if not storage_path:
        app.logger.info("Delete from Firebase Storage skipped: No storage_path provided.")
        return True
    bucket = get_storage_bucket() # Uses the imported function
    if not bucket:
        app.logger.error(f"Storage bucket not available for deletion of '{storage_path}'.")
        return False
    try:
        blob = bucket.blob(storage_path)
        if blob.exists():
            blob.delete()
            app.logger.info(f"File {storage_path} deleted successfully from Firebase Storage.")
        else:
            app.logger.info(f"File {storage_path} not found in Firebase Storage for deletion (already deleted or never existed).")
        return True
    except Exception as e:
        app.logger.error(f"Firebase Storage Deletion Error for '{storage_path}': {e}", exc_info=True)
        return False

def extract_ticker_metadata_from_file_content(content_bytes, original_filename):
    MAX_TICKERS_TO_STORE_IN_FIRESTORE = 500 
    tickers = []
    common_ticker_column_names = ["Ticker", "Tickers", "Symbol", "Symbols", "Stock", "Stocks", "Keyword", "Keywords"]
    try:
        if original_filename.lower().endswith('.csv'):
            try: content_str = content_bytes.decode('utf-8')
            except UnicodeDecodeError: content_str = content_bytes.decode('latin1')
            df = pd.read_csv(io.StringIO(content_str))
        elif original_filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content_bytes))
        else:
            return {'count': 0, 'preview': [], 'all_tickers': [], 'error': 'Unsupported file type'}

        if df.empty:
            return {'count': 0, 'preview': [], 'all_tickers': [], 'error': 'File is empty or unparsable'}

        ticker_col_found = None
        for col_name_option in common_ticker_column_names:
            if col_name_option in df.columns:
                ticker_col_found = col_name_option
                break
        if not ticker_col_found: ticker_col_found = df.columns[0]

        tickers = df[ticker_col_found].dropna().astype(str).str.strip().str.upper().tolist()
        
        limited_all_tickers = tickers[:MAX_TICKERS_TO_STORE_IN_FIRESTORE]
        if len(tickers) > MAX_TICKERS_TO_STORE_IN_FIRESTORE:
            app.logger.warning(f"File '{original_filename}' contains {len(tickers)} tickers. Storing only the first {MAX_TICKERS_TO_STORE_IN_FIRESTORE} in Firestore for 'all_tickers_from_file'.")

        return {
            'count': len(tickers),
            'preview': tickers[:5],
            'all_tickers': limited_all_tickers
        }
    except Exception as e:
        app.logger.error(f"Error extracting ticker metadata from {original_filename}: {e}", exc_info=True)
        return {'count': 0, 'preview': [], 'all_tickers': [], 'error': str(e)}

@app.context_processor
def inject_globals_and_helpers():
    return {
        'now': datetime.now(timezone.utc),
        'is_user_logged_in': 'firebase_user_uid' in session,
        'user_email': session.get('firebase_user_email'),
        'user_displayName': session.get('firebase_user_displayName'),
        'FIREBASE_INITIALIZED_SUCCESSFULLY': FIREBASE_INITIALIZED_SUCCESSFULLY,
        'zip': zip
    }

@app.template_filter('format_datetime')
def format_datetime_filter(value, fmt="%Y-%m-%d %H:%M:%S"):
    if not value: return "N/A"
    try:
        if isinstance(value, str):
            dt_obj = datetime.fromisoformat(value.replace('Z', '+00:00')) if value.endswith('Z') else datetime.fromisoformat(value)
        elif isinstance(value, (int, float)):
            if value > 10**10: 
                 dt_obj = datetime.fromtimestamp(value / 1000, timezone.utc)
            else: 
                 dt_obj = datetime.fromtimestamp(value, timezone.utc)
        elif isinstance(value, datetime):
            dt_obj = value
        elif hasattr(value, 'seconds') and hasattr(value, 'nanoseconds'): 
            dt_obj = datetime.fromtimestamp(value.seconds + value.nanoseconds / 1e9, timezone.utc)
        else:
            return value 

        if dt_obj.tzinfo is None: 
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)

        return dt_obj.strftime(fmt)
    except (ValueError, AttributeError, TypeError) as e:
        app.logger.warning(f"Could not format datetime value '{value}' (type: {type(value)}): {e}")
        return value


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_all_report_section_keys():
    try:
        from reporting_tools.wordpress_reporter import ALL_REPORT_SECTIONS
        return list(ALL_REPORT_SECTIONS.keys())
    except ImportError:
        app.logger.warning("Could not import ALL_REPORT_SECTIONS from wordpress_reporter. Using fallback list.")
        return ["introduction", "metrics_summary", "detailed_forecast_table", "company_profile",
                "valuation_metrics", "total_valuation", "profitability_growth", "analyst_insights",
                "financial_health", "technical_analysis_summary", "short_selling_info",
                "stock_price_statistics", "dividends_shareholder_returns", "conclusion_outlook",
                "risk_factors", "faq", "historical_performance"] 
ALL_SECTIONS = get_all_report_section_keys()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not FIREBASE_INITIALIZED_SUCCESSFULLY:
            app.logger.error("Login attempt failed: Firebase Admin SDK not initialized.")
            flash("Authentication service is currently unavailable. Please try again later.", "danger")
            return redirect(url_for('stock_analysis_homepage_route'))
        if 'firebase_user_uid' not in session:
            flash("Please login to access this page.", "warning")
            return redirect(url_for('login', next=request.full_path))
        return f(*args, **kwargs)
    return decorated_function

def get_user_site_profiles_from_firestore(user_uid):
    if not FIREBASE_INITIALIZED_SUCCESSFULLY: return []
    db = get_firestore_client()
    if not db: app.logger.error(f"Firestore client not available for get_user_site_profiles_from_firestore (user: {user_uid})."); return []
    profiles = []
    try:
        profiles_ref = db.collection(u'userSiteProfiles').document(user_uid).collection(u'profiles').order_by(u'profile_name').stream()
        for profile_doc in profiles_ref:
            profile_data = profile_doc.to_dict()
            profile_data['profile_id'] = profile_doc.id
            profile_data.setdefault('authors', [])
            profile_data.setdefault('uploaded_ticker_file_name', None)
            profile_data.setdefault('ticker_file_storage_path', None)
            profile_data.setdefault('ticker_file_uploaded_at', None)
            profile_data.setdefault('ticker_count_from_file', None)
            profile_data.setdefault('ticker_preview_from_file', [])
            profile_data.setdefault('all_tickers_from_file', []) 
            profiles.append(profile_data)
    except Exception as e:
        app.logger.error(f"Error fetching site profiles for user {user_uid} from Firestore: {e}", exc_info=True)
    return profiles

def save_user_site_profile_to_firestore(user_uid, profile_data_to_save): 
    if not FIREBASE_INITIALIZED_SUCCESSFULLY: return False
    db = get_firestore_client()
    if not db: app.logger.error(f"Firestore client not available for save_user_site_profile_to_firestore (user: {user_uid})."); return False
    
    profile_data = profile_data_to_save.copy()

    try:
        profile_id_to_save = profile_data.pop('profile_id', None) 
        now_iso = datetime.now(timezone.utc).isoformat()
        profile_data['last_updated_at'] = now_iso
        
        profile_data.setdefault('authors', [])
        profile_data.setdefault('uploaded_ticker_file_name', None)
        profile_data.setdefault('ticker_file_storage_path', None)
        profile_data.setdefault('ticker_file_uploaded_at', None)
        profile_data.setdefault('ticker_count_from_file', None)
        profile_data.setdefault('ticker_preview_from_file', [])
        profile_data.setdefault('all_tickers_from_file', [])

        if profile_id_to_save:
            doc_ref = db.collection(u'userSiteProfiles').document(user_uid).collection(u'profiles').document(profile_id_to_save)
            doc_ref.set(profile_data, merge=True)
            app.logger.info(f"Updated site profile {profile_id_to_save} for user {user_uid} in Firestore.")
            return profile_id_to_save
        else:
            profile_data['created_at'] = now_iso
            new_doc_ref = db.collection(u'userSiteProfiles').document(user_uid).collection(u'profiles').document()
            new_doc_ref.set(profile_data)
            profile_id_new = new_doc_ref.id
            app.logger.info(f"Added new site profile {profile_id_new} for user {user_uid} in Firestore.")
            return profile_id_new
    except Exception as e:
        app.logger.error(f"Error saving site profile for user {user_uid} to Firestore: {e}", exc_info=True)
        return False

def delete_user_site_profile_from_firestore(user_uid, profile_id_to_delete): # Modified
    if not FIREBASE_INITIALIZED_SUCCESSFULLY: return False
    db = get_firestore_client()
    if not db: app.logger.error(f"Firestore client not available for delete_user_site_profile_from_firestore (user: {user_uid})."); return False
    try:
        profile_doc_ref = db.collection(u'userSiteProfiles').document(user_uid).collection(u'profiles').document(profile_id_to_delete)
        profile_snapshot = profile_doc_ref.get()
        
        if profile_snapshot.exists:
            profile_data = profile_snapshot.to_dict()
            old_storage_path = profile_data.get('ticker_file_storage_path')
            if old_storage_path:
                delete_file_from_storage(old_storage_path)
        
        # Delete persisted ticker statuses for this profile
        processed_tickers_ref = profile_doc_ref.collection(u'processedTickers')
        docs = processed_tickers_ref.limit(500).stream() # Batch delete if many, or use async helper
        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        if deleted_count > 0:
            app.logger.info(f"Deleted {deleted_count} persisted ticker statuses for profile {profile_id_to_delete}.")

        profile_doc_ref.delete() 
        app.logger.info(f"Deleted site profile {profile_id_to_delete} and its data for user {user_uid}.")
        return True
    except Exception as e:
        app.logger.error(f"Error deleting site profile {profile_id_to_delete} for user {user_uid}: {e}", exc_info=True)
        return False

# --- NEW HELPER FUNCTIONS FOR PERSISTED TICKER STATUS ---
# --- NEW HELPER FUNCTIONS FOR PERSISTED TICKER STATUS ---
def save_processed_ticker_status(user_uid, profile_id, ticker_symbol, status_data):
    """Saves the processed status of a single ticker to Firestore."""
    # Assuming FIREBASE_INITIALIZED_SUCCESSFULLY, db (get_firestore_client),
    # app.logger, and socketio are accessible in this function's scope.
    # This typically means they are global or passed around.

    if not FIREBASE_INITIALIZED_SUCCESSFULLY:
        # In a real scenario, app.logger might not be available if Flask app context is not present.
        # Consider a more robust logging setup for library-like functions.
        print(f"Firebase not initialized. Cannot save status for {ticker_symbol}") # Or use a basic logger
        return False
    
    db = get_firestore_client()
    if not db:
        # app.logger.error(...) - Assuming app.logger is available
        print(f"Firestore client not available for save_processed_ticker_status (user: {user_uid}, profile: {profile_id}).")
        return False

    try:
        ticker_symbol_safe = str(ticker_symbol).replace('/', '_SLASH_') # More robust sanitization
        if not ticker_symbol_safe:
            # app.logger.error(...)
            print(f"Invalid ticker symbol for Firestore document ID: '{ticker_symbol}'")
            return False

        doc_ref = db.collection(u'userSiteProfiles').document(user_uid)\
                    .collection(u'profiles').document(profile_id)\
                    .collection(u'processedTickers').document(ticker_symbol_safe)

        data_to_save = status_data.copy()
        data_to_save['last_updated_at'] = firestore.SERVER_TIMESTAMP
        # Ensure datetime objects are converted to ISO strings if they are not already
        for key in ['generated_at', 'published_at']:
            if key in data_to_save and isinstance(data_to_save[key], datetime):
                data_to_save[key] = data_to_save[key].isoformat()
        
        # Backward compatibility: if 'generation_time' or 'publish_time' are present, map them
        # These keys come from auto_publisher.py's status_data_for_persistence potentially
        if 'generation_time' in data_to_save and data_to_save['generation_time'] is not None:
            data_to_save['generated_at'] = data_to_save.pop('generation_time')
        elif 'generation_time' in data_to_save: # if it's None, remove it
             data_to_save.pop('generation_time')


        if 'publish_time' in data_to_save and data_to_save['publish_time'] is not None:
            data_to_save['published_at'] = data_to_save.pop('publish_time')
        elif 'publish_time' in data_to_save: # if it's None, remove it
            data_to_save.pop('publish_time')

        doc_ref.set(data_to_save, merge=True)
        # app.logger.info(...)
        print(f"Saved/Updated status for ticker '{ticker_symbol_safe}' (original: {ticker_symbol}) in profile '{profile_id}'.")

        if socketio:
            emit_data = data_to_save.copy()
            emit_data['ticker'] = ticker_symbol # Use original ticker symbol for frontend
            # Ensure all datetime objects in emit_data are ISO strings for JSON serialization
            for key_emit, value_emit in emit_data.items():
                if isinstance(value_emit, datetime): # Should already be isoformat from above
                    emit_data[key_emit] = value_emit.isoformat()
                # Firestore server timestamp will be an object, handle if necessary or let frontend ignore
                if key_emit == 'last_updated_at' and not isinstance(value_emit, str): # SERVER_TIMESTAMP
                    emit_data[key_emit] = datetime.now(timezone.utc).isoformat() # Approximate for emit

            socketio.emit('ticker_status_persisted', {
                'profile_id': profile_id,
                **emit_data
            }, room=user_uid)
            # app.logger.info(...)
            print(f"Emitted 'ticker_status_persisted' for {ticker_symbol} in profile {profile_id}.")
        return True
    except Exception as e:
        # app.logger.error(...)
        print(f"Error saving processed ticker status for '{ticker_symbol}' in profile '{profile_id}': {e}")
        # Consider import traceback and print traceback.format_exc() for more details
        return False
    
def get_persisted_ticker_statuses_for_profile(user_uid, profile_id): # New
    """Retrieves all persisted ticker statuses for a given profile."""
    if not FIREBASE_INITIALIZED_SUCCESSFULLY: return {}
    db = get_firestore_client()
    if not db: 
        app.logger.error(f"Firestore client not available for get_persisted_ticker_statuses_for_profile (user: {user_uid}, profile: {profile_id}).")
        return {}
    
    statuses = {}
    try:
        docs_stream = db.collection(u'userSiteProfiles').document(user_uid)\
                        .collection(u'profiles').document(profile_id)\
                        .collection(u'processedTickers').stream()
        for doc in docs_stream:
            status_data = doc.to_dict()
            
            for time_key in ['last_updated_at', 'generation_time', 'publish_time']:
                if time_key in status_data and hasattr(status_data[time_key], 'isoformat'): # Check if it's a Firestore Timestamp or datetime
                    status_data[time_key] = status_data[time_key].isoformat()
                elif time_key in status_data and isinstance(status_data[time_key], (int,float)): # if stored as unix
                    if status_data[time_key] > 10**10: status_data[time_key] = datetime.fromtimestamp(status_data[time_key]/1000, timezone.utc).isoformat()
                    else: status_data[time_key] = datetime.fromtimestamp(status_data[time_key], timezone.utc).isoformat()


            original_ticker_symbol = doc.id.replace('_SLASH_', '/') # Convert safe ID back
            statuses[original_ticker_symbol] = status_data 
            
    except Exception as e:
        app.logger.error(f"Error fetching persisted ticker statuses for profile '{profile_id}': {e}", exc_info=True)
    return statuses

# Helper to fetch previous ticker status for a profile/ticker

def get_previous_ticker_status(user_uid, profile_id, ticker_symbol):
    if not FIREBASE_INITIALIZED_SUCCESSFULLY: return None
    db = get_firestore_client()
    if not db:
        app.logger.error(f"Firestore client not available for get_previous_ticker_status (user: {user_uid}, profile: {profile_id}).")
        return None
    try:
        ticker_symbol_safe = str(ticker_symbol).replace('/', '_SLASH_')
        doc_ref = db.collection(u'userSiteProfiles').document(user_uid)\
                    .collection(u'profiles').document(profile_id)\
                    .collection(u'processedTickers').document(ticker_symbol_safe)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        app.logger.error(f"Error fetching previous ticker status for '{ticker_symbol}' in profile '{profile_id}': {e}", exc_info=True)
    return None
# --- END NEW HELPER FUNCTIONS ---


def get_automation_shared_context(user_uid, profiles_list): # Modified
    context = {}
    try:
        current_profile_ids = [p['profile_id'] for p in profiles_list if 'profile_id' in p]
        state = auto_publisher.load_state(user_uid=user_uid, current_profile_ids_from_run=current_profile_ids) if AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY else {}
        context['posts_today_by_profile'] = state.get('posts_today_by_profile', {})
        context['last_run_date_for_counts'] = state.get('last_run_date', 'N/A')
        context['processed_tickers_log_map'] = state.get('processed_tickers_detailed_log_by_profile', {}) 
        context['absolute_max_posts_cap'] = getattr(auto_publisher, 'ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP', 10)

        context.setdefault('persisted_file_info', {})
        context.setdefault('persisted_ticker_statuses_map', {}) # For the new section

        for profile in profiles_list: 
            pid = profile.get('profile_id')
            if pid:
                all_tickers = profile.get('all_tickers_from_file', [])
                total_count = len(all_tickers)
                # Get processed count from state
                processed_count = 0
                if 'last_processed_ticker_index_by_profile' in state and pid in state['last_processed_ticker_index_by_profile']:
                    processed_count = state['last_processed_ticker_index_by_profile'][pid] + 1
                context['persisted_file_info'][pid] = {
                    'name': profile.get('uploaded_ticker_file_name'),
                    'path': profile.get('ticker_file_storage_path'),
                    'uploaded_at': profile.get('ticker_file_uploaded_at'),
                    'count': profile.get('ticker_count_from_file'),
                    'preview': profile.get('ticker_preview_from_file', []),
                    'all_tickers': all_tickers,
                    'processed_count': processed_count,
                    'total_count': total_count
                }
                context['persisted_ticker_statuses_map'][pid] = get_persisted_ticker_statuses_for_profile(user_uid, pid) #
                
    except Exception as e:
        app.logger.error(f"Error loading shared_context (user: {user_uid}): {e}", exc_info=True)
        context.update({'posts_today_by_profile': {}, 'last_run_date_for_counts': "Error",
                        'processed_tickers_log_map': {}, 'absolute_max_posts_cap': 10,
                        'persisted_file_info': {}, 'persisted_ticker_statuses_map': {}})
    return context

def is_valid_url(url_string):
    if not url_string: return False
    if not (url_string.startswith('http://') or url_string.startswith('https://')): return False
    try:
        domain_part = url_string.split('//')[1].split('/')[0]
        if '.' not in domain_part or len(domain_part) < 3: return False
    except IndexError: return False
    return True

# --- Core Application Routes --- 
@app.route('/')
def stock_analysis_homepage_route():
    return render_template('stock-analysis-homepage.html', title="AI Stock Predictions & Analysis")

@app.route('/dashboard')
@login_required
def dashboard_page():
    user_uid = session.get('firebase_user_uid')
    report_history, total_reports = [], 0
    if user_uid:
        report_history, total_reports = get_report_history_for_user(user_uid, display_limit=10)
    return render_template('dashboard.html',
                           title="Dashboard - Tickzen",
                           report_history=report_history,
                           total_reports=total_reports)


@app.route('/analyzer', methods=['GET'])
def analyzer_input_page():
    return render_template('analyzer_input.html', title="Stock Analyzer Input")

@app.route('/start-analysis', methods=['POST'])
def start_stock_analysis():
    ticker = request.form.get('ticker', '').strip().upper()

    room_id = session.get('firebase_user_uid')
    client_sid_from_form = request.form.get('client_sid')

    if not room_id and client_sid_from_form:
        room_id = client_sid_from_form
        app.logger.info(f"Anonymous analysis task. Using client_sid {room_id} as room.")
    elif not room_id and not client_sid_from_form:
        room_id = "task_room_" + str(int(time.time()))
        app.logger.warning(f"No user UID or client SID for analysis task. Generated room_id: {room_id}")

    app.logger.info(f"\n--- Received /start-analysis for ticker: {ticker} (Target Room: {room_id}) ---")

    valid_ticker_pattern = r'^[A-Z0-9\^.-]+(\.[A-Z]{1,2})?$'
    if not ticker or not re.match(valid_ticker_pattern, ticker):
        flash(f"Invalid ticker format: '{ticker}'. Please use standard stock symbols (e.g., AAPL, ADANIPOWER.NS).", "danger")
        socketio.emit('analysis_error', {'message': f"Invalid ticker format: '{ticker}'.", 'ticker': ticker}, room=room_id)
        return redirect(url_for('analyzer_input_page'))

    if not PIPELINE_IMPORTED_SUCCESSFULLY:
        flash("The Stock Analysis service is temporarily unavailable. Please try again later.", "danger")
        socketio.emit('analysis_error', {'message': 'Stock Analysis service is temporarily unavailable.', 'ticker': ticker}, room=room_id)
        return redirect(url_for('analyzer_input_page'))

    try:
        request_timestamp_for_report = int(time.time())
        app.logger.info(f"Running full stock analysis for ticker {ticker} (Timestamp: {request_timestamp_for_report}) for room {room_id}...")

        pipeline_result = run_pipeline(ticker, str(request_timestamp_for_report), APP_ROOT,
                                       socketio_instance=socketio, task_room=room_id)

        report_html_content_from_pipeline = None
        path_info_from_pipeline = None
        report_filename_for_url = None
        absolute_report_filepath_on_disk = None

        if pipeline_result and isinstance(pipeline_result, tuple) and len(pipeline_result) >= 4:
            model_obj, forecast_obj, path_info_from_pipeline, report_html_content_from_pipeline = pipeline_result[:4]

            if isinstance(report_html_content_from_pipeline, str) and \
               "<html" in report_html_content_from_pipeline.lower() and \
               "Error Generating Report" not in report_html_content_from_pipeline:
                generated_filename = f"{ticker}_report_dynamic_{request_timestamp_for_report}.html"
                absolute_report_filepath_on_disk = os.path.join(STOCK_REPORTS_PATH, generated_filename)
                try:
                    with open(absolute_report_filepath_on_disk, 'w', encoding='utf-8') as f:
                        f.write(report_html_content_from_pipeline)
                    report_filename_for_url = generated_filename
                    app.logger.info(f"HTML content from pipeline saved to: {absolute_report_filepath_on_disk}")
                except Exception as e_save:
                    app.logger.error(f"Could not save HTML content for {ticker}: {e_save}. Will try path_info.")

            if not report_filename_for_url and isinstance(path_info_from_pipeline, str) and path_info_from_pipeline.endswith(".html"):
                if os.path.isabs(path_info_from_pipeline) and path_info_from_pipeline.startswith(STOCK_REPORTS_PATH):
                    if os.path.exists(path_info_from_pipeline):
                        absolute_report_filepath_on_disk = path_info_from_pipeline
                        report_filename_for_url = os.path.relpath(absolute_report_filepath_on_disk, STOCK_REPORTS_PATH).replace(os.sep, '/')
                    else: app.logger.warning(f"Absolute path from pipeline {path_info_from_pipeline} does not exist.")
                else:
                    potential_filename_for_url = path_info_from_pipeline.lstrip(os.sep).replace(os.sep, '/')
                    if potential_filename_for_url.startswith(STOCK_REPORTS_SUBDIR + '/'):
                        potential_filename_for_url = potential_filename_for_url[len(STOCK_REPORTS_SUBDIR)+1:]
                    potential_abs_path_in_reports_dir = os.path.join(STOCK_REPORTS_PATH, potential_filename_for_url)
                    if os.path.exists(potential_abs_path_in_reports_dir):
                        absolute_report_filepath_on_disk = potential_abs_path_in_reports_dir
                        report_filename_for_url = potential_filename_for_url
                    else: app.logger.warning(f"Report file from path_info '{path_info_from_pipeline}' as '{potential_filename_for_url}' not found.")

            if not report_filename_for_url:
                error_detail = f"Pipeline output unclear or report file missing. Path: '{path_info_from_pipeline}'"
                socketio.emit('analysis_error', {'message': "Report generation failed (file path issue).", 'ticker': ticker}, room=room_id)
                raise ValueError("Stock analysis report path issue: " + error_detail)
        else:
            socketio.emit('analysis_error', {'message': "Pipeline did not return expected result.", 'ticker': ticker}, room=room_id)
            raise ValueError("Stock analysis pipeline did not return the expected result.")

        if not (report_filename_for_url and absolute_report_filepath_on_disk and os.path.exists(absolute_report_filepath_on_disk)):
            socketio.emit('analysis_error', {'message': "Report file invalid post-generation.", 'ticker': ticker}, room=room_id)
            raise ValueError("Report generation unsuccessful or final report path invalid.")

        user_uid_for_history = session.get('firebase_user_uid')
        if user_uid_for_history and report_filename_for_url:
            generated_at_dt = datetime.fromtimestamp(request_timestamp_for_report, timezone.utc)
            save_report_to_history(user_uid_for_history, ticker, report_filename_for_url, generated_at_dt)

        view_report_url = url_for('view_generated_report', ticker=ticker, filename=report_filename_for_url)
        app.logger.info(f"Analysis for {ticker} complete. Signaling client in room {room_id} to redirect to: {view_report_url}")
        socketio.emit('analysis_complete', {'report_url': view_report_url, 'ticker': ticker}, room=room_id)

        return jsonify({'status': 'analysis_completed_redirect_via_socket', 'ticker': ticker, 'report_url': view_report_url}), 200

    except Exception as e:
        app.logger.error(f"Error during stock analysis for {ticker}: {e}", exc_info=True)
        socketio.emit('analysis_error', {'message': str(e)[:150] + "...", 'ticker': ticker}, room=room_id)
        flash(f"An error occurred while analyzing {ticker}: {str(e)[:150]}...", "danger")
        return jsonify({'status': 'error', 'message': f"Error analyzing {ticker}: {str(e)[:150]}..."}), 500

@app.route('/view-report/<ticker>/<path:filename>')
@login_required
def view_generated_report(ticker, filename):
    report_url = url_for('serve_generated_report', filename=filename)
    return render_template('view_report_page.html',
                           title=f"Analysis Report: {ticker.upper()}",
                           ticker=ticker.upper(),
                           report_url=report_url,
                           download_filename=filename)


@app.route('/generated_reports/<path:filename>')
def serve_generated_report(filename):
    return send_from_directory(STOCK_REPORTS_PATH, filename)

@app.route('/static/<path:filename>')
def serve_static_general(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/login', methods=['GET'])
def login():
    if 'firebase_user_uid' in session: return redirect(url_for('dashboard_page'))
    return render_template('login.html', title="Login - Tickzen")

@app.route('/register', methods=['GET'])
def register():
    if 'firebase_user_uid' in session: return redirect(url_for('dashboard_page'))
    return render_template('register.html', title="Register - Tickzen")

@app.route('/verify-token', methods=['POST'])
def verify_token_route():
    if not FIREBASE_INITIALIZED_SUCCESSFULLY:
        app.logger.error("Token verification failed: Firebase Admin SDK not initialized.")
        return jsonify({"error": "Authentication service is currently unavailable."}), 503
    data = request.get_json()
    if not data or 'idToken' not in data:
        return jsonify({"error": "No ID token provided."}), 400
    id_token = data['idToken']
    decoded_token = verify_firebase_token(id_token)
    if decoded_token and 'uid' in decoded_token:
        session['firebase_user_uid'] = decoded_token['uid']
        session['firebase_user_email'] = decoded_token.get('email')
        session['firebase_user_displayName'] = decoded_token.get('name', '')
        session.permanent = True
        app.logger.info(f"User {decoded_token['uid']} logged in. Email: {decoded_token.get('email')}, Name: {decoded_token.get('name')}")

        try:
            db = get_firestore_client()
            if db:
                user_uid = decoded_token['uid']
                user_profile_ref = db.collection(u'userProfiles').document(user_uid)
                profile_doc = user_profile_ref.get()

                if not profile_doc.exists:
                    user_data_for_firestore = {
                        u'display_name': decoded_token.get('name', ''),
                        u'email': decoded_token.get('email'),
                        u'created_at': firestore.SERVER_TIMESTAMP,
                        u'notifications': {
                            u'email': False,
                            u'automation': False
                        }
                    }
                    user_profile_ref.set(user_data_for_firestore)
                    app.logger.info(f"Created Firestore profile for new user {user_uid}.")
                else:
                    firestore_profile_data = profile_doc.to_dict()
                    auth_display_name = decoded_token.get('name', '')
                    update_payload = {}
                    if firestore_profile_data.get('display_name') != auth_display_name:
                        update_payload['display_name'] = auth_display_name
                    if update_payload: 
                        user_profile_ref.update(update_payload)
                        app.logger.info(f"Synced display_name for user {user_uid} from Auth to Firestore.")
        except Exception as e_firestore:
            app.logger.error(f"Error ensuring user profile in Firestore for {decoded_token.get('uid')}: {e_firestore}", exc_info=True)

        return jsonify({"status": "success", "uid": decoded_token['uid'], "next_url": url_for('dashboard_page')}), 200
    else:
        app.logger.warning(f"Token verification failed. Decoded token: {decoded_token}")
        return jsonify({"error": "Invalid or expired token."}), 401

@app.route('/logout')
def logout():
    user_uid = session.get('firebase_user_uid')
    if user_uid:
        app.logger.info(f"User {user_uid} logging out. Client {request.sid if hasattr(request, 'sid') else '(no socket SID in HTTP context)'} should handle disconnect.")
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('stock_analysis_homepage_route'))

# --- USER & PROFILE MANAGEMENT ---
@app.route('/user-profile')
@login_required
def user_profile_page():
    user_uid = session['firebase_user_uid']
    db = get_firestore_client()

    user_profile_data = {
        'display_name': session.get('user_displayName', ''),
        'bio': '',
        'profile_picture': session.get('user_profile_picture', ''),
        'notifications': { 'email': False, 'automation': False },
        'created_at': None, 'total_automations': 0, 'active_profiles': 0
    }

    if db:
        try:
            profile_doc = db.collection('userProfiles').document(user_uid).get()
            if profile_doc.exists:
                profile_data = profile_doc.to_dict()
                user_profile_data.update({
                    'display_name': profile_data.get('display_name', user_profile_data['display_name']),
                    'bio': profile_data.get('bio', ''),
                    'profile_picture': profile_data.get('profile_picture', user_profile_data['profile_picture']),
                    'notifications': profile_data.get('notifications', user_profile_data['notifications']),
                    'created_at': profile_data.get('created_at', None)
                })

            automations_query = db.collection('userGeneratedReports').where('user_uid', '==', user_uid).count()
            user_profile_data['total_automations'] = automations_query.get()[0][0].value

            profiles_query = db.collection('userSiteProfiles').document(user_uid).collection('profiles').count()
            user_profile_data['active_profiles'] = profiles_query.get()[0][0].value

        except Exception as e:
            app.logger.error(f"Error fetching user profile data: {str(e)}")

    return render_template('user_profile.html',
                         title="Your Profile - Tickzen",
                         user_profile_picture=user_profile_data['profile_picture'],
                         user_displayName=user_profile_data['display_name'],
                         user_bio=user_profile_data['bio'],
                         user_notifications=user_profile_data['notifications'],
                         user_created_at=user_profile_data['created_at'],
                         total_automations=user_profile_data['total_automations'],
                         active_profiles=user_profile_data['active_profiles'])

@app.route('/site-profiles')
@login_required
def manage_site_profiles():
    user_uid = session['firebase_user_uid']
    profiles = get_user_site_profiles_from_firestore(user_uid)
    shared_context = get_automation_shared_context(user_uid, profiles)
    form_data_add = session.pop('form_data_add_repopulate', None)
    show_add_form_on_load_flag = session.pop('show_add_form_on_load_flag', False)
    errors_add_repopulate = session.pop('errors_add_repopulate', None)

    return render_template('manage_profiles.html',
                           title="Publishing Profiles - Tickzen",
                           profiles=profiles,
                           all_report_sections=ALL_SECTIONS,
                           form_data_add=form_data_add,
                           show_add_form_on_load=show_add_form_on_load_flag,
                           errors_add=errors_add_repopulate,
                           **shared_context)

@app.route('/site-profiles/add', methods=['POST'])
@login_required
def add_site_profile():
    user_uid = session['firebase_user_uid']
    errors = {}

    profile_name = request.form.get('profile_name', '').strip()
    site_url = request.form.get('site_url', '').strip()
    sheet_name = request.form.get('sheet_name', '').strip()
    stockforecast_category_id_str = request.form.get('stockforecast_category_id', '').strip()
    min_scheduling_gap_minutes_str = request.form.get('min_scheduling_gap_minutes', '45').strip()
    max_scheduling_gap_minutes_str = request.form.get('max_scheduling_gap_minutes', '68').strip()
    env_prefix = request.form.get('env_prefix_for_feature_image_colors', '').strip().upper()
    report_sections = request.form.getlist('report_sections_to_include[]')

    if not profile_name: errors['profile_name_add'] = "Profile Name is required."
    if not site_url: errors['site_url_add'] = "Site URL is required."
    elif not is_valid_url(site_url): errors['site_url_add'] = "Please enter a valid Site URL (e.g., https://example.com)."

    min_sched_gap = 0
    if not min_scheduling_gap_minutes_str: errors['min_scheduling_gap_minutes_add'] = "Min Scheduling Gap is required."
    else:
        try:
            min_sched_gap = int(min_scheduling_gap_minutes_str)
            if min_sched_gap <= 0: errors['min_scheduling_gap_minutes_add'] = "Min Scheduling Gap must be a positive number."
        except ValueError: errors['min_scheduling_gap_minutes_add'] = "Min Scheduling Gap must be a valid number."

    max_sched_gap = 0
    if not max_scheduling_gap_minutes_str: errors['max_scheduling_gap_minutes_add'] = "Max Scheduling Gap is required."
    else:
        try:
            max_sched_gap = int(max_scheduling_gap_minutes_str)
            if max_sched_gap <= 0: errors['max_scheduling_gap_minutes_add'] = "Max Scheduling Gap must be a positive number."
        except ValueError: errors['max_scheduling_gap_minutes_add'] = "Max Scheduling Gap must be a valid number."

    if 'min_scheduling_gap_minutes_add' not in errors and 'max_scheduling_gap_minutes_add' not in errors:
        if min_sched_gap >= max_sched_gap: errors['scheduling_gaps_general'] = "Min Gap must be less than Max Gap."

    stockforecast_category_id = None
    if stockforecast_category_id_str:
        try: stockforecast_category_id = int(stockforecast_category_id_str)
        except ValueError: errors['stockforecast_category_id_add'] = "Category ID must be a number if provided."

    if not report_sections: report_sections = ALL_SECTIONS

    authors_data = []
    submitted_authors_raw_for_repopulation = []
    author_idx = 0
    has_any_author_input = False
    while True:
        username_field_key = f'author_wp_username_{author_idx}'
        userid_field_key = f'author_wp_user_id_{author_idx}'
        app_password_field_key = f'author_app_password_{author_idx}'

        if author_idx > 0 and username_field_key not in request.form: break
        if author_idx >= 10: app.logger.warning(f"Author limit (10) reached for user {user_uid}"); break

        wp_username = request.form.get(username_field_key, '').strip()
        wp_user_id_str = request.form.get(userid_field_key, '').strip()
        app_password = request.form.get(app_password_field_key, '')

        if wp_username or wp_user_id_str or app_password: has_any_author_input = True

        submitted_authors_raw_for_repopulation.append({"wp_username": wp_username, "wp_user_id": wp_user_id_str})

        if wp_username or wp_user_id_str or app_password:
            author_error_key_prefix = f'author_{author_idx}'
            current_author_errors = []
            if not wp_username: current_author_errors.append("Username required.")
            wp_user_id_int = None
            if not wp_user_id_str: current_author_errors.append("User ID required.")
            else:
                try: wp_user_id_int = int(wp_user_id_str)
                except ValueError: current_author_errors.append("User ID must be a number.")
            if not app_password: current_author_errors.append("Application Password required.")

            if current_author_errors: errors[f'{author_error_key_prefix}_general'] = f"Author {author_idx + 1} incomplete: {' '.join(current_author_errors)}"
            elif wp_user_id_int is not None:
                authors_data.append({"id": f"author_{int(time.time())}_{author_idx}", "wp_username": wp_username, "wp_user_id": str(wp_user_id_int), "app_password": app_password})

        if not request.form.get(username_field_key) and not request.form.get(userid_field_key) and not request.form.get(app_password_field_key) and author_idx == 0 and not has_any_author_input:
             break
        if not request.form.get(username_field_key) and author_idx > 0 :
             break

        author_idx += 1

    if not authors_data:
        if has_any_author_input:
            if not any(key.startswith('author_') and '_general' in key for key in errors):
                errors['authors_general'] = "Ensure all fields (Username, User ID, App Password) are filled for each writer."
        else: errors['authors_general'] = "At least one complete writer is required."

    if errors:
        session['form_data_add_repopulate'] = {
            "profile_name": profile_name, "site_url": site_url, "sheet_name": sheet_name,
            "stockforecast_category_id": stockforecast_category_id_str,
            "min_scheduling_gap_minutes": min_scheduling_gap_minutes_str,
            "max_scheduling_gap_minutes": max_scheduling_gap_minutes_str,
            "env_prefix_for_feature_image_colors": env_prefix,
            "report_sections_to_include": report_sections,
            "authors_raw": submitted_authors_raw_for_repopulation
        }
        session['errors_add_repopulate'] = errors
        session['show_add_form_on_load_flag'] = True
        flash("Please correct the errors in the 'Add New Publishing Profile' form.", "danger")
        return redirect(url_for('manage_site_profiles'))

    new_profile_data = {
        "profile_name": profile_name, "site_url": site_url, "sheet_name": sheet_name,
        "stockforecast_category_id": str(stockforecast_category_id) if stockforecast_category_id is not None else "",
        "min_scheduling_gap_minutes": min_sched_gap, "max_scheduling_gap_minutes": max_sched_gap,
        "env_prefix_for_feature_image_colors": env_prefix, "authors": authors_data,
        "report_sections_to_include": report_sections
    }

    if save_user_site_profile_to_firestore(user_uid, new_profile_data):
        flash(f"Publishing Profile '{new_profile_data['profile_name']}' added successfully!", "success")
    else:
        flash(f"Failed to add publishing profile '{new_profile_data['profile_name']}'. An unexpected error occurred.", "danger")
    return redirect(url_for('manage_site_profiles'))


@app.route('/site-profiles/edit/<profile_id_from_firestore>', methods=['GET', 'POST'])
@login_required
def edit_site_profile(profile_id_from_firestore):
    user_uid = session['firebase_user_uid']
    db = get_firestore_client()
    if not db:
        flash("Database service is currently unavailable. Please try again later.", "danger")
        return redirect(url_for('manage_site_profiles'))

    profile_doc_ref = db.collection(u'userSiteProfiles').document(user_uid).collection(u'profiles').document(profile_id_from_firestore)
    profile_snap = profile_doc_ref.get()

    if not profile_snap.exists:
        flash(f"Publishing Profile ID '{profile_id_from_firestore}' not found.", "error")
        return redirect(url_for('manage_site_profiles'))

    profile_data_original = profile_snap.to_dict()
    profile_data_original['profile_id'] = profile_id_from_firestore 
    profile_data_original.setdefault('authors', []) 


    if request.method == 'POST':
        errors = {}
        profile_name = request.form.get('profile_name', '').strip()
        site_url = request.form.get('site_url', '').strip()
        sheet_name = request.form.get('sheet_name', '').strip()
        stockforecast_category_id_str = request.form.get('stockforecast_category_id', '').strip()
        min_scheduling_gap_minutes_str = request.form.get('min_scheduling_gap_minutes', '').strip()
        max_scheduling_gap_minutes_str = request.form.get('max_scheduling_gap_minutes', '').strip()
        env_prefix = request.form.get('env_prefix_for_feature_image_colors', '').strip().upper()
        report_sections = request.form.getlist('report_sections_to_include[]')

        if not profile_name: errors['profile_name'] = "Profile Name is required."
        if not site_url: errors['site_url'] = "Site URL is required."
        elif not is_valid_url(site_url): errors['site_url'] = "Please enter a valid Site URL."

        min_sched_gap = 0
        if not min_scheduling_gap_minutes_str: errors['min_scheduling_gap_minutes'] = "Min Scheduling Gap is required."
        else:
            try:
                min_sched_gap = int(min_scheduling_gap_minutes_str)
                if min_sched_gap <= 0: errors['min_scheduling_gap_minutes'] = "Min Gap must be positive."
            except ValueError: errors['min_scheduling_gap_minutes'] = "Min Gap must be a number."

        max_sched_gap = 0
        if not max_scheduling_gap_minutes_str: errors['max_scheduling_gap_minutes'] = "Max Scheduling Gap is required."
        else:
            try:
                max_sched_gap = int(max_scheduling_gap_minutes_str)
                if max_sched_gap <= 0: errors['max_scheduling_gap_minutes'] = "Max Gap must be positive."
            except ValueError: errors['max_scheduling_gap_minutes'] = "Max Gap must be a number."

        if 'min_scheduling_gap_minutes' not in errors and 'max_scheduling_gap_minutes' not in errors:
            if min_sched_gap >= max_sched_gap: errors['scheduling_gaps_general'] = "Min Gap must be less than Max Gap."

        stockforecast_category_id = None
        if stockforecast_category_id_str:
            try: stockforecast_category_id = int(stockforecast_category_id_str)
            except ValueError: errors['stockforecast_category_id'] = "Category ID must be a number."

        if not report_sections: report_sections = ALL_SECTIONS

        updated_authors = []
        author_idx = 0
        submitted_authors_raw_for_repopulation = [] 
        has_any_author_input_edit = False
        original_authors_map_by_id = {str(a.get('id','')): a for a in profile_data_original.get('authors', [])}


        while True:
            author_internal_id_field = f'author_id_{author_idx}'
            username_field_key = f'author_wp_username_{author_idx}'
            userid_field_key = f'author_wp_user_id_{author_idx}'
            app_password_field_key = f'author_app_password_{author_idx}'
            
            if not (request.form.get(author_internal_id_field) or \
                    request.form.get(username_field_key) or \
                    request.form.get(userid_field_key) or \
                    request.form.get(app_password_field_key)) and author_idx > 0 : 
                break 

            if author_idx >=10 : app.logger.warning(f"Author limit for edit reached user {user_uid}"); break

            author_internal_id = request.form.get(author_internal_id_field, '').strip()
            wp_username = request.form.get(username_field_key, '').strip()
            wp_user_id_str = request.form.get(userid_field_key, '').strip()
            app_password_new = request.form.get(app_password_field_key, '') 

            if wp_username or wp_user_id_str or app_password_new: 
                has_any_author_input_edit = True
            elif not author_internal_id and author_idx == 0 and not (wp_username or wp_user_id_str or app_password_new): 
                break 

            submitted_authors_raw_for_repopulation.append({
                "id": author_internal_id,
                "wp_username": wp_username,
                "wp_user_id": wp_user_id_str,
            })

            if wp_username or wp_user_id_str: 
                author_error_key_prefix = f'author_{author_idx}'
                current_author_errors = []
                final_app_password = app_password_new
                wp_user_id_int = None

                if not wp_username: current_author_errors.append("Username required.")
                if not wp_user_id_str: current_author_errors.append("User ID required.")
                else:
                    try: wp_user_id_int = int(wp_user_id_str)
                    except ValueError: current_author_errors.append("User ID must be a number.")

                if not app_password_new: 
                    original_author_details = original_authors_map_by_id.get(author_internal_id)
                    if original_author_details and original_author_details.get('app_password'):
                        final_app_password = original_author_details['app_password'] 
                    elif author_internal_id and not original_author_details: 
                        current_author_errors.append("App Password required for this new writer entry.")
                    elif not author_internal_id: 
                        current_author_errors.append("App Password required for new writer.")
                
                if current_author_errors: errors[f'{author_error_key_prefix}_general'] = f"Author {author_idx + 1} error: {' '.join(current_author_errors)}"
                elif wp_user_id_int is not None:
                     updated_authors.append({
                        "id": author_internal_id if author_internal_id else f"newauthor_{int(time.time())}_{author_idx}", 
                        "wp_username": wp_username,
                        "wp_user_id": str(wp_user_id_int),
                        "app_password": final_app_password
                    })
            elif author_internal_id and not (wp_username or wp_user_id_str or app_password_new): 
                app.logger.info(f"Author {author_internal_id} fields cleared, effectively removing them for profile {profile_id_from_firestore}.")

            author_idx += 1
            if author_idx >= 10: break 


        if not updated_authors and has_any_author_input_edit : 
             if not any(key.startswith('author_') and '_general' in key for key in errors):
                errors['authors_general'] = "Ensure all fields (Username, User ID, App Password) are filled correctly for each writer you intend to keep or add."
        elif not updated_authors and not has_any_author_input_edit and not profile_data_original.get('authors'): 
            errors['authors_general'] = "At least one writer is required for the profile."


        if errors:
            flash("Please correct the errors in the form.", "danger")
            profile_data_repopulate = {
                "profile_id": profile_id_from_firestore,
                "profile_name": profile_name, "site_url": site_url, "sheet_name": sheet_name,
                "stockforecast_category_id": stockforecast_category_id_str,
                "min_scheduling_gap_minutes": min_scheduling_gap_minutes_str,
                "max_scheduling_gap_minutes": max_scheduling_gap_minutes_str,
                "env_prefix_for_feature_image_colors": env_prefix,
                "report_sections_to_include": report_sections,
                "authors": submitted_authors_raw_for_repopulation 
            }
            profile_data_repopulate['uploaded_ticker_file_name'] = profile_data_original.get('uploaded_ticker_file_name')
            profile_data_repopulate['ticker_file_storage_path'] = profile_data_original.get('ticker_file_storage_path')
            profile_data_repopulate['ticker_file_uploaded_at'] = profile_data_original.get('ticker_file_uploaded_at')
            profile_data_repopulate['ticker_count_from_file'] = profile_data_original.get('ticker_count_from_file')
            profile_data_repopulate['ticker_preview_from_file'] = profile_data_original.get('ticker_preview_from_file', [])
            profile_data_repopulate['all_tickers_from_file'] = profile_data_original.get('all_tickers_from_file', [])


            return render_template('edit_profile.html',
                                   title=f"Edit {profile_data_original.get('profile_name')}",
                                   profile=profile_data_repopulate,
                                   all_report_sections=ALL_SECTIONS,
                                   errors=errors)

        profile_data_to_save = {
            "profile_id": profile_id_from_firestore, 
            'profile_name': profile_name, 'site_url': site_url, 'sheet_name': sheet_name,
            'stockforecast_category_id': str(stockforecast_category_id) if stockforecast_category_id is not None else "",
            'min_scheduling_gap_minutes': min_sched_gap, 'max_scheduling_gap_minutes': max_sched_gap,
            'env_prefix_for_feature_image_colors': env_prefix,
            'authors': updated_authors,
            'report_sections_to_include': report_sections
        }
        profile_data_to_save['uploaded_ticker_file_name'] = profile_data_original.get('uploaded_ticker_file_name')
        profile_data_to_save['ticker_file_storage_path'] = profile_data_original.get('ticker_file_storage_path')
        profile_data_to_save['ticker_file_uploaded_at'] = profile_data_original.get('ticker_file_uploaded_at')
        profile_data_to_save['ticker_count_from_file'] = profile_data_original.get('ticker_count_from_file')
        profile_data_to_save['ticker_preview_from_file'] = profile_data_original.get('ticker_preview_from_file', [])
        profile_data_to_save['all_tickers_from_file'] = profile_data_original.get('all_tickers_from_file', [])


        if save_user_site_profile_to_firestore(user_uid, profile_data_to_save):
            flash(f"Publishing Profile '{profile_data_to_save['profile_name']}' updated successfully!", "success")
        else:
            flash(f"Failed to update publishing profile '{profile_data_to_save['profile_name']}'.", "danger")
        return redirect(url_for('manage_site_profiles'))

    return render_template('edit_profile.html',
                           title=f"Edit {profile_data_original.get('profile_name')}",
                           profile=profile_data_original,
                           all_report_sections=ALL_SECTIONS,
                           errors=None)


@app.route('/site-profiles/delete/<profile_id_to_delete>', methods=['POST'])
@login_required
def delete_site_profile(profile_id_to_delete):
    user_uid = session['firebase_user_uid']
    if delete_user_site_profile_from_firestore(user_uid, profile_id_to_delete): # Modified
        flash(f"Publishing Profile ID '{profile_id_to_delete}' deleted successfully, including its persisted ticker statuses.", "success") # Modified
    else:
        flash(f"Failed to delete publishing profile ID '{profile_id_to_delete}'.", "error")
    return redirect(url_for('manage_site_profiles'))

# --- REPORT HISTORY MANAGEMENT ---
def save_report_to_history(user_uid, ticker, filename, generated_at_dt):
    if not FIREBASE_INITIALIZED_SUCCESSFULLY:
        app.logger.error("Firestore not available for saving report history.")
        return False
    db = get_firestore_client()
    if not db:
        app.logger.error("Firestore client not available for saving report history.")
        return False
    try:
        reports_history_collection = db.collection(u'userGeneratedReports')
        if generated_at_dt.tzinfo is None:
            generated_at_dt = generated_at_dt.replace(tzinfo=timezone.utc)

        reports_history_collection.add({
            u'user_uid': user_uid,
            u'ticker': ticker.upper(),
            u'filename': filename,
            u'generated_at': generated_at_dt
        })
        app.logger.info(f"Report history saved for user {user_uid}, ticker {ticker}, filename {filename}.")
        return True
    except Exception as e:
        app.logger.error(f"Error saving report history for user {user_uid}, ticker {ticker}: {e}", exc_info=True)
        return False

def get_report_history_for_user(user_uid, display_limit=10):
    if not FIREBASE_INITIALIZED_SUCCESSFULLY:
        app.logger.error(f"Firestore not available for fetching report history for user {user_uid}.")
        return [], 0
    db = get_firestore_client()
    if not db:
        app.logger.error(f"Firestore client not available for fetching report history for user {user_uid}.")
        return [], 0

    reports_for_display = []
    total_user_reports_count = 0

    try:
        base_query = db.collection(u'userGeneratedReports').where(u'user_uid', u'==', user_uid)
        try:
            count_query = base_query.count()
            count_result = count_query.get()
            total_user_reports_count = count_result[0][0].value if count_result else 0
        except AttributeError: 
            app.logger.warning("Firestore count() aggregate not available, falling back to streaming for count.")
            all_user_reports_stream = base_query.stream()
            all_user_reports_docs = list(all_user_reports_stream)
            total_user_reports_count = len(all_user_reports_docs)

        display_query = base_query.order_by(u'generated_at', direction='DESCENDING').limit(display_limit)
        docs_for_display_stream = display_query.stream()

        for doc_snapshot in docs_for_display_stream:
            report_data = doc_snapshot.to_dict()
            report_data['id'] = doc_snapshot.id
            generated_at_val = report_data.get('generated_at')
            if hasattr(generated_at_val, 'seconds'): 
                 report_data['generated_at'] = datetime.fromtimestamp(generated_at_val.seconds + generated_at_val.nanoseconds / 1e9, timezone.utc)
            elif isinstance(generated_at_val, (int, float)): 
                if generated_at_val > 10**10: 
                    report_data['generated_at'] = datetime.fromtimestamp(generated_at_val / 1000, timezone.utc)
                else: 
                    report_data['generated_at'] = datetime.fromtimestamp(generated_at_val, timezone.utc)
            reports_for_display.append(report_data)
        app.logger.info(f"Fetched {len(reports_for_display)} reports for user {user_uid} (Limit: {display_limit}, Total: {total_user_reports_count}).")
        return reports_for_display, total_user_reports_count
    except Exception as e:
        app.logger.error(f"Error fetching report history for user {user_uid}: {e}", exc_info=True)
        return [], 0


# --- WORDPRESS AUTOMATION SPECIFIC ROUTES ---
@app.route('/wordpress-automation-portal')
@login_required
def wordpress_automation_portal_route():
    return render_template('automate_homepage.html', title="WordPress Automation - Tickzen")

@app.route('/automation-runner')
@login_required
def automation_runner_page(): # Modified
    user_uid = session['firebase_user_uid']
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    shared_context = get_automation_shared_context(user_uid, user_site_profiles) # This now includes persisted_ticker_statuses_map
    return render_template('run_automation_page.html',
                           title="Run Automation - Tickzen",
                           user_site_profiles=user_site_profiles,
                           **shared_context)

@app.route('/run-automation-now', methods=['POST'])
@login_required
def run_automation_now(): # Modified
    user_uid = session['firebase_user_uid']
    db = get_firestore_client()

    if not AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY:
        flash("Automation service is currently unavailable. Please try again later.", "danger")
        return redirect(url_for('automation_runner_page'))

    profile_ids_to_run = request.form.getlist('run_profile_ids[]')
    if not profile_ids_to_run:
        flash("No profiles selected to run automation.", "info")
        return redirect(url_for('automation_runner_page'))

    all_user_profiles_from_db = get_user_site_profiles_from_firestore(user_uid)
    selected_profiles_data_for_run = []
    profiles_db_map = {p.get("profile_id"): p for p in all_user_profiles_from_db}

    articles_map = {}
    automation_input_source_map = {}


    for profile_id_from_form in profile_ids_to_run:
        profile_data_from_db = profiles_db_map.get(profile_id_from_form)
        if not profile_data_from_db:
            flash(f"Profile ID {profile_id_from_form} not found for user. Skipping.", "warning")
            continue
        selected_profiles_data_for_run.append(profile_data_from_db)

        pid = profile_id_from_form
        try:
            articles_map[pid] = max(0, int(request.form.get(f'posts_for_profile_{pid}', 0)))
        except ValueError:
            articles_map[pid] = 0
            flash(f"Invalid number of posts for '{profile_data_from_db.get('profile_name', pid)}', defaulting to 0.", "warning")

        ticker_source_method = request.form.get(f'ticker_source_{pid}', 'file')

        if ticker_source_method == 'manual':
            custom_tickers_str = request.form.get(f'custom_tickers_{pid}', '').strip()
            if custom_tickers_str:
                automation_input_source_map[pid] = {
                    "source_type": "manual",
                    "tickers": [t.strip().upper() for t in custom_tickers_str.split(',') if t.strip()]
                }
                if profile_data_from_db.get('ticker_file_storage_path'):
                    app.logger.info(f"Manual ticker entry for profile {pid}. Attempting to delete old file: {profile_data_from_db['ticker_file_storage_path']}")
                    delete_file_from_storage(profile_data_from_db['ticker_file_storage_path'])
                    profile_update_for_manual = profile_data_from_db.copy() 
                    profile_update_for_manual.update({
                        'profile_id': pid, 
                        'uploaded_ticker_file_name': None, 'ticker_file_storage_path': None,
                        'ticker_file_uploaded_at': None, 'ticker_count_from_file': None,
                        'ticker_preview_from_file': [], 'all_tickers_from_file': []
                    })
                    save_user_site_profile_to_firestore(user_uid, profile_update_for_manual)
                    app.logger.info(f"Cleared persisted file metadata for profile {pid} from Firestore due to manual ticker entry.")
            else:
                 flash(f"Manual ticker entry selected for '{profile_data_from_db.get('profile_name', pid)}' but no tickers provided. Will attempt to use existing ticker source if available or default.", "warning")
                 if profile_data_from_db.get('ticker_file_storage_path'):
                     automation_input_source_map[pid] = {
                        "source_type": "persisted_file",
                        "storage_path": profile_data_from_db.get('ticker_file_storage_path'),
                        "original_filename": profile_data_from_db.get('uploaded_ticker_file_name')
                    }
                     app.logger.info(f"No manual tickers for {pid}, but a persisted file exists. Using persisted file.")
                 else:
                    automation_input_source_map[pid] = {"source_type": "excel_or_persisted"}
                    app.logger.info(f"No manual tickers for {pid} and no persisted file. Defaulting to Excel/State.")


        elif ticker_source_method == 'file':
            file_obj = request.files.get(f'ticker_file_{pid}')
            if file_obj and file_obj.filename and allowed_file(file_obj.filename):
                app.logger.info(f"New file '{file_obj.filename}' uploaded for profile {pid}.")
                old_storage_path = profile_data_from_db.get('ticker_file_storage_path')
                if old_storage_path:
                    app.logger.info(f"Deleting old file from {old_storage_path} for profile {pid}.")
                    delete_file_from_storage(old_storage_path)

                uploaded_storage_path = upload_file_to_storage(user_uid, pid, file_obj, file_obj.filename)
                if uploaded_storage_path:
                    file_obj.seek(0)
                    file_content_bytes_for_meta = file_obj.read()

                    ticker_meta = extract_ticker_metadata_from_file_content(file_content_bytes_for_meta, file_obj.filename)

                    profile_update_payload = profile_data_from_db.copy() 
                    profile_update_payload.update({ 
                        'profile_id': pid,
                        'uploaded_ticker_file_name': file_obj.filename,
                        'ticker_file_storage_path': uploaded_storage_path,
                        'ticker_file_uploaded_at': datetime.now(timezone.utc).isoformat(),
                        'ticker_count_from_file': ticker_meta.get('count', 0),
                        'ticker_preview_from_file': ticker_meta.get('preview', []),
                        'all_tickers_from_file': ticker_meta.get('all_tickers', [])
                    })
                    
                    save_user_site_profile_to_firestore(user_uid, profile_update_payload)
                    app.logger.info(f"Persisted new file '{file_obj.filename}' and metadata for profile {pid}.")
                    automation_input_source_map[pid] = {
                        "source_type": "uploaded_file",
                        "storage_path": uploaded_storage_path,
                        "original_filename": file_obj.filename
                    }
                    flash(f"File '{file_obj.filename}' uploaded and saved for profile '{profile_data_from_db.get('profile_name', pid)}'. {ticker_meta.get('count', 0)} tickers found.", "success")
                else:
                    flash(f"Error uploading new file for '{profile_data_from_db.get('profile_name', pid)}'. Check logs. Will use previous file if any, or Excel/State.", "danger")
                    app.logger.error(f"Upload failed for profile {pid}, file '{file_obj.filename}'. Fallback logic will apply.")
                    if profile_data_from_db.get('ticker_file_storage_path'):
                         automation_input_source_map[pid] = {
                            "source_type": "persisted_file",
                            "storage_path": profile_data_from_db.get('ticker_file_storage_path'),
                            "original_filename": profile_data_from_db.get('uploaded_ticker_file_name')
                        }
                         app.logger.info(f"Using previously persisted file for profile {pid} after new upload failed.")
                    else:
                         automation_input_source_map[pid] = {"source_type": "excel_or_persisted"}
                         app.logger.info(f"No new or persisted file for profile {pid} after upload failure. Defaulting to Excel/State.")

            elif file_obj and file_obj.filename:
                flash(f"File type of '{file_obj.filename}' not allowed for profile '{profile_data_from_db.get('profile_name', pid)}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}. Using existing file or Excel/State.", "warning")
                app.logger.warning(f"File type not allowed for '{file_obj.filename}' (profile {pid}). Using fallback.")
                if profile_data_from_db.get('ticker_file_storage_path'):
                    automation_input_source_map[pid] = {
                        "source_type": "persisted_file",
                        "storage_path": profile_data_from_db.get('ticker_file_storage_path'),
                        "original_filename": profile_data_from_db.get('uploaded_ticker_file_name')
                    }
                    app.logger.info(f"Using persisted file for profile {pid} due to disallowed new file type.")
                else:
                    automation_input_source_map[pid] = {"source_type": "excel_or_persisted"}
                    app.logger.info(f"No persisted file for profile {pid} after disallowed new file type. Defaulting to Excel/State.")
            else: 
                db_profile_data_check = profiles_db_map.get(pid, {})
                if db_profile_data_check.get('ticker_file_storage_path'):
                    automation_input_source_map[pid] = {
                        "source_type": "persisted_file",
                        "storage_path": db_profile_data_check.get('ticker_file_storage_path'),
                        "original_filename": db_profile_data_check.get('uploaded_ticker_file_name')
                    }
                    app.logger.info(f"No new file uploaded for profile {pid}. Using persisted file: {db_profile_data_check.get('uploaded_ticker_file_name')}")
                else:
                    automation_input_source_map[pid] = {"source_type": "excel_or_persisted"}
                    app.logger.info(f"No new or persisted file for profile {pid}. Defaulting to Excel/State.")
        else:
            app.logger.info(f"Ticker source method for profile {pid} is '{ticker_source_method}'. Defaulting to Excel/State or persisted file if available.")
            if profile_data_from_db.get('ticker_file_storage_path'):
                automation_input_source_map[pid] = {
                    "source_type": "persisted_file",
                    "storage_path": profile_data_from_db.get('ticker_file_storage_path'),
                    "original_filename": profile_data_from_db.get('uploaded_ticker_file_name')
                }
                app.logger.info(f"Using persisted file for profile {pid} as default fallback.")
            else:
                automation_input_source_map[pid] = {"source_type": "excel_or_persisted"}
                app.logger.info(f"No persisted file for profile {pid}. Defaulting to Excel/State as ultimate fallback.")


    custom_tickers_for_run = {}
    uploaded_file_details_for_run = {}
    for pid, source_info in automation_input_source_map.items():
        if source_info["source_type"] == "manual":
            custom_tickers_for_run[pid] = source_info["tickers"]
        elif source_info["source_type"] == "uploaded_file" or source_info["source_type"] == "persisted_file":
            uploaded_file_details_for_run[pid] = {
                "storage_path": source_info["storage_path"],
                "original_filename": source_info["original_filename"]
            }

    try:
        # Pass the save_processed_ticker_status function as a callback
        results = auto_publisher.trigger_publishing_run(
            user_uid,
            selected_profiles_data_for_run,
            articles_map,
            custom_tickers_by_profile_id=custom_tickers_for_run,
            uploaded_file_details_by_profile_id=uploaded_file_details_for_run,
            socketio_instance=socketio,
            user_room=user_uid,
            save_status_callback=save_processed_ticker_status # NEW: Pass callback here
        )
        socketio.emit('automation_status', {'message': "Automation run processing started. Monitor individual profile logs for live updates.", 'status': 'info'}, room=user_uid)

        if results:
            for pid_res, res_data in results.items():
                pname = res_data.get("profile_name", pid_res)
                summary = res_data.get("status_summary", "No summary provided for this profile.")
                errors_list = res_data.get("errors", [])

                log_category = "success"
                if errors_list or "failed" in summary.lower() or "error" in summary.lower():
                    log_category = "danger"
                elif "warning" in summary.lower() or "skipped" in summary.lower() or "issue" in summary.lower():
                    log_category = "warning"
                elif "no new posts" in summary.lower() or "limit reached" in summary.lower():
                    log_category = "info"

                flash_message = f"Profile '{pname}': {summary}"
                if errors_list:
                    flash_message += f" Details: {'; '.join(errors_list[:2])}{'...' if len(errors_list) > 2 else ''}"
                flash(flash_message, log_category)
        else:
            flash("Automation run initiated. No immediate summary returned (might be fully asynchronous). Check logs for updates.", "info")
    except Exception as e_auto_run:
        app.logger.error(f"Error triggering automation run for user {user_uid}: {e_auto_run}", exc_info=True)
        flash("An unexpected error occurred while starting the automation run. Please check system logs or contact support.", "danger")
        socketio.emit('automation_status', {'message': f'Failed to start automation: {str(e_auto_run)[:100]}...', 'status': 'error'}, room=user_uid)

    return redirect(url_for('automation_runner_page'))


@app.route('/stop_automation_run/<profile_id>', methods=['POST'])
@login_required
def stop_automation_run(profile_id):
    user_uid = session['firebase_user_uid']
    if not AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY:
        app.logger.error(f"Stop automation request failed: Auto publisher module not available (User: {user_uid}, Profile: {profile_id})")
        return jsonify({'status': 'error', 'message': 'Automation service is currently unavailable.'}), 503

    try:
        if hasattr(auto_publisher, 'stop_publishing_run'):
            result = auto_publisher.stop_publishing_run(user_uid, profile_id)
            if result and isinstance(result, dict):
                was_successful = result.get('success', False)
                message = result.get('message', 'Stop request processed.')

                if was_successful:
                    app.logger.info(f"Stop request successful for profile {profile_id} (User: {user_uid}): {message}")
                    return jsonify({'status': 'success', 'message': message})
                else:
                    app.logger.warning(f"Stop request unsuccessful for profile {profile_id} (User: {user_uid}): {message}")
                    return jsonify({'status': 'error', 'message': message}), 400
            else:
                app.logger.info(f"Stop request sent for profile {profile_id} (User: {user_uid}) - no detailed response")
                return jsonify({'status': 'success', 'message': 'Stop request sent.'})
        else:
            socketio.emit('automation_update', {
                'profile_id': profile_id,
                'phase': 'Control',
                'stage': 'Stop Requested',
                'message': 'Stop request received. Processing.',
                'status': 'info',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, room=user_uid)

            app.logger.warning(f"Using fallback stop method for profile {profile_id} (User: {user_uid}) - auto_publisher lacks stop_publishing_run")
            return jsonify({'status': 'success', 'message': 'Stop request acknowledged using fallback method.'})

    except Exception as e:
        app.logger.error(f"Error in stop_automation_run for profile {profile_id} (User: {user_uid}): {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'An error occurred while processing the stop request: {str(e)[:100]}...'}), 500


@app.route('/wp-asset-generator')
@login_required
def wp_generator_page():
    return render_template('wp-asset.html', title="WordPress Asset Generator - Tickzen")

@app.route('/generate-wp-assets', methods=['POST'])
@login_required
def generate_wp_assets():
    start_time = time.time()
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid request: Expected JSON data.'}), 400

    data = request.get_json()
    ticker = data.get('ticker', '').strip().upper()

    room_id = session.get('firebase_user_uid', data.get('client_sid'))
    if not room_id: room_id = "wp_asset_task_" + str(int(time.time()))
    app.logger.info(f"WP Asset request for {ticker} (Room: {room_id})")


    valid_ticker_pattern = r'^[A-Z0-9\^.-]{1,10}$'
    if not ticker or not re.match(valid_ticker_pattern, ticker):
        socketio.emit('wp_asset_error', {'message': f"Invalid ticker: '{ticker}'.", 'ticker': ticker}, room=room_id)
        return jsonify({'status': 'error', 'message': f"Invalid ticker symbol: '{ticker}'. Please use standard symbols."}), 400

    if not PIPELINE_IMPORTED_SUCCESSFULLY:
        socketio.emit('wp_asset_error', {'message': 'WP Asset service unavailable.', 'ticker': ticker}, room=room_id)
        return jsonify({'status': 'error', 'message': 'WordPress Asset generation service is temporarily unavailable.'}), 503

    try:
        timestamp = str(int(time.time()))
        app.logger.info(f"Running WordPress asset pipeline for ticker: {ticker} (Timestamp: {timestamp})...")

        model_obj, forecast_obj, html_report_fragment, img_urls_dict = run_wp_pipeline(
            ticker, timestamp, APP_ROOT, socketio_instance=socketio, task_room=room_id
        )

        if not isinstance(img_urls_dict, dict):
            app.logger.warning(f"run_wp_pipeline for {ticker} returned img_urls not as dict: {type(img_urls_dict)}. Defaulting.")
            img_urls_dict = {}

        if html_report_fragment and "Error Generating Report" not in html_report_fragment:
            duration = time.time() - start_time
            app.logger.info(f"WordPress asset pipeline for {ticker} completed in {duration:.2f}s.")
            result_payload = {
                'status': 'success', 'ticker': ticker,
                'report_html': html_report_fragment, 'chart_urls': img_urls_dict,
                'duration': f"{duration:.2f}s"
            }
            socketio.emit('wp_asset_complete', result_payload, room=room_id)
            return jsonify(result_payload)
        else:
            error_detail = f"WP Asset HTML generation failed. Detail: {str(html_report_fragment)[:200]}"
            socketio.emit('wp_asset_error', {'message': error_detail, 'ticker': ticker}, room=room_id)
            raise ValueError(error_detail)

    except Exception as e:
        app.logger.error(f"Error in /generate-wp-assets for ticker {ticker}: {e}", exc_info=True)
        socketio.emit('wp_asset_error', {'message': f"Server error for {ticker}.", 'ticker': ticker}, room=room_id)
        return jsonify({'status': 'error', 'message': f"A server error occurred while generating assets for {ticker}."}), 500

@socketio.on('connect')
def handle_connect():
    user_uid = session.get('firebase_user_uid')
    client_sid = request.sid

    if user_uid:
        join_room(user_uid)
        app.logger.info(f"Client {client_sid} connected and joined user room: {user_uid}")
        emit('status', {'message': f'Connected to real-time updates! User Room: {user_uid}. Your SID: {client_sid}'}, room=client_sid)
    else:
        app.logger.info(f"Client {client_sid} connected (anonymous or pre-login).")
        emit('status', {'message': f'Connected! Your SID is {client_sid}. Login for personalized features.'}, room=client_sid)


@socketio.on('disconnect')
def handle_disconnect():
    user_uid = session.get('firebase_user_uid')
    client_sid = request.sid
    if user_uid:
        leave_room(user_uid)
        app.logger.info(f"Client {client_sid} disconnected and left user room: {user_uid}")
    else:
        app.logger.info(f"Client {client_sid} disconnected (anonymous or pre-login).")


@socketio.on('join_task_room')
def handle_join_task_room(data):
    task_room_id = data.get('room_id')
    client_sid = request.sid
    if task_room_id:
        join_room(task_room_id)
        app.logger.info(f"Client {client_sid} explicitly joined task room: {task_room_id}")
        emit('status', {'message': f'Successfully joined task room {task_room_id}.'}, room=client_sid)


@app.route('/update-user-profile', methods=['POST'])
@login_required
def update_user_profile():
    try:
        user_uid = session['firebase_user_uid']
        db = get_firestore_client()

        if not db:
            return jsonify({'success': False, 'message': 'Database service unavailable'}), 503

        display_name = request.form.get('display_name', '').strip()
        email_notifications = request.form.get('email_notifications') == 'on'
        automation_alerts = request.form.get('automation_alerts') == 'on'

        user_profile_ref = db.collection('userProfiles').document(user_uid)

        update_data = {
            'display_name': display_name,
            'notifications': {
                'email': email_notifications,
                'automation': automation_alerts
            },
            'updated_at': firestore.SERVER_TIMESTAMP
        }

        user_profile_ref.set(update_data, merge=True)
        session['user_displayName'] = display_name

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': { 'display_name': display_name }
        })

    except Exception as e:
        app.logger.error(f"Error updating user profile: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update profile'}), 500

@app.route('/change-password')
@login_required
def change_password():
    return render_template('change_password.html', title="Change Password - Tickzen")

@app.route('/activity-log')
@login_required
def view_activity_log():
    user_uid = session['firebase_user_uid']
    db = get_firestore_client()

    activity_log = []
    member_since = None

    if db:
        try:
            profile_doc = db.collection('userProfiles').document(user_uid).get()
            if profile_doc.exists:
                profile_data = profile_doc.to_dict()
                member_since = profile_data.get('created_at')

            automations_query = db.collection('userGeneratedReports')\
                .where('user_uid', '==', user_uid)\
                .order_by('generated_at', direction='DESCENDING')\
                .limit(50)

            for doc in automations_query.stream():
                data = doc.to_dict()
                generated_at = data.get('generated_at')
                if hasattr(generated_at, 'timestamp'): timestamp = generated_at.timestamp()
                else: timestamp = 0

                activity_log.append({
                    'type': 'automation', 'ticker': data.get('ticker', 'N/A'),
                    'timestamp': timestamp,
                    'details': f"Generated stock analysis report for {data.get('ticker', 'N/A')}"
                })

            profiles_query = db.collection('userSiteProfiles')\
                .document(user_uid)\
                .collection('profiles')\
                .order_by('last_updated_at', direction='DESCENDING')\
                .limit(20)

            for doc in profiles_query.stream():
                data = doc.to_dict()
                last_updated = data.get('last_updated_at')
                if hasattr(last_updated, 'timestamp'): timestamp = last_updated.timestamp()
                else: timestamp = 0

                activity_log.append({
                    'type': 'profile_update', 'timestamp': timestamp,
                    'details': f"Updated profile: {data.get('profile_name', 'N/A')}"
                })

            activity_log.sort(key=lambda x: x['timestamp'], reverse=True)

        except Exception as e:
            app.logger.error(f"Error fetching activity log: {str(e)}")
            flash("Error loading activity log. Please try again later.", "error")

    return render_template('activity_log.html',
                         title="Activity Log - Tickzen",
                         activity_log=activity_log,
                         member_since=member_since)

if __name__ == '__main__':
    try:
        app
        socketio
    except NameError:
        print("CRITICAL: Flask app or SocketIO instance not defined before __main__ block. Exiting.")
        exit(1)

    app.logger.info(f"Current CWD: {os.getcwd()}")
    app.logger.info(f"APP_ROOT: {APP_ROOT}, Static: {app.static_folder}, Templates: {app.template_folder}")
    app.logger.info(f"Stock reports save path: {STOCK_REPORTS_PATH}")
    if not FIREBASE_INITIALIZED_SUCCESSFULLY: app.logger.error("CRITICAL: Firebase NOT INITIALIZED.")
    else: app.logger.info(f"Firebase Init Status: {FIREBASE_INITIALIZED_SUCCESSFULLY}")
    if not AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY: app.logger.warning("WARNING: MOCK auto_publisher in use or import failed.")
    else: app.logger.info("Auto Publisher Imported Successfully.")
    if not PIPELINE_IMPORTED_SUCCESSFULLY: app.logger.warning("WARNING: MOCK pipeline in use or import failed.")
    else: app.logger.info("Pipeline Imported Successfully.")

    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")

    app.logger.info(f"Attempting to start Flask-SocketIO server on http://0.0.0.0:{port} (Debug: {debug_mode})")
    try:
        socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode,
                     use_reloader=debug_mode,
                     allow_unsafe_werkzeug=True if debug_mode else False)
    except Exception as e_run:
        app.logger.error(f"CRITICAL: Failed to start Flask-SocketIO server: {e_run}", exc_info=True)
        print(f"CRITICAL: Server could not start. Check logs. Error: {e_run}")