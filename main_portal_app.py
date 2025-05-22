# main_portal_app.py

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
import os
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import io
from functools import wraps
import re # For basic URL validation
import traceback


FIREBASE_INITIALIZED_SUCCESSFULLY = True # Placeholder
AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY = True # Placeholder
PIPELINE_IMPORTED_SUCCESSFULLY = True # Placeholder

try:
    from firebase_admin_setup import initialize_firebase_admin, verify_firebase_token, get_firestore_client
    initialize_firebase_admin()
    from firebase_admin_setup import _firebase_app_initialized # Assuming this exposes the status
    FIREBASE_INITIALIZED_SUCCESSFULLY = _firebase_app_initialized
    if not FIREBASE_INITIALIZED_SUCCESSFULLY:
        print("CRITICAL: Firebase Admin SDK initialized according to firebase_admin_setup, but _firebase_app_initialized is False.")
except ImportError as e_fb_admin:
    print(f"CRITICAL: Failed to import or initialize Firebase Admin from firebase_admin_setup: {e_fb_admin}")
    FIREBASE_INITIALIZED_SUCCESSFULLY = False
    # Dummy functions if firebase_admin_setup fails
    def verify_firebase_token(token): print("Firebase dummy: verify_firebase_token called"); return None
    def get_firestore_client(): print("Firebase dummy: get_firestore_client called"); return None

try:
    import auto_publisher # Your auto_publisher module
    AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY = True
except ImportError as e_ap:
    print(f"CRITICAL: Failed to import auto_publisher.py: {e_ap}")
    AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY = False
    class MockAutoPublisher: # Simplified mock
        ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP = 10
        def load_state(self, user_uid=None, current_profile_ids_from_run=None): return {}
        def trigger_publishing_run(self, *args, **kwargs): print("MockAutoPublisher: trigger_publishing_run called"); return {}
    auto_publisher = MockAutoPublisher()


try:
    from pipeline import run_pipeline, run_wp_pipeline # Your pipeline module
    PIPELINE_IMPORTED_SUCCESSFULLY = True
except ImportError as e_pipeline:
    print(f"CRITICAL: Failed to import pipeline.py: {e_pipeline}")
    PIPELINE_IMPORTED_SUCCESSFULLY = False
    def run_pipeline(*args, **kwargs): print("Mock Pipeline: run_pipeline called"); return None, None, "Error: Mock Stock Analysis Pipeline not available", None
    def run_wp_pipeline(*args, **kwargs): print("Mock Pipeline: run_wp_pipeline called"); return None, None, "Error: Mock WordPress Asset Pipeline not available", {}


load_dotenv()
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER_PATH = os.path.join(APP_ROOT, 'static')
TEMPLATE_FOLDER_PATH = os.path.join(APP_ROOT, 'templates')
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'temp_uploads')
STOCK_REPORTS_SUBDIR = 'stock_reports'
STOCK_REPORTS_PATH = os.path.join(STATIC_FOLDER_PATH, STOCK_REPORTS_SUBDIR)

app = Flask(__name__,
            static_folder=STATIC_FOLDER_PATH,
            template_folder=TEMPLATE_FOLDER_PATH)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_strong_default_secret_key_here_CHANGE_ME_TOO")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

for folder_path in [UPLOAD_FOLDER, STATIC_FOLDER_PATH, STOCK_REPORTS_PATH]:
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
            app.logger.info(f"Created directory: {folder_path}")
        except OSError as e:
            app.logger.error(f"Could not create directory {folder_path}: {e}")

@app.context_processor
def inject_globals_and_helpers():
    return {
        'now': datetime.now(timezone.utc),
        'is_user_logged_in': 'firebase_user_uid' in session,
        'user_email': session.get('firebase_user_email'),
        'user_displayName': session.get('firebase_user_displayName'),
        'FIREBASE_INITIALIZED_SUCCESSFULLY': FIREBASE_INITIALIZED_SUCCESSFULLY,
        'zip': zip # Adding zip for iterating multiple lists in templates if needed
    }

@app.template_filter('format_datetime')
def format_datetime_filter(value, fmt="%Y-%m-%d %H:%M:%S"):
    if not value: return "N/A"
    try:
        if isinstance(value, str):
            dt_obj = datetime.fromisoformat(value.replace('Z', '+00:00')) if value.endswith('Z') else datetime.fromisoformat(value)
        elif isinstance(value, (int, float)): # Handle timestamps
            # Attempt to determine if it's seconds or milliseconds
            if value > 10**10: # Likely milliseconds
                 dt_obj = datetime.fromtimestamp(value / 1000, timezone.utc)
            else: # Likely seconds
                 dt_obj = datetime.fromtimestamp(value, timezone.utc)
        elif isinstance(value, datetime):
            dt_obj = value
        # Handling Firestore Timestamp (google.cloud.firestore_v1.base_timestamp.Timestamp)
        elif hasattr(value, 'seconds') and hasattr(value, 'nanoseconds'): # Heuristic for Firestore Timestamp
            dt_obj = datetime.fromtimestamp(value.seconds + value.nanoseconds / 1e9, timezone.utc)
        else:
            return value # Fallback for unknown types
        
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc) # Assume UTC if naive
        
        return dt_obj.strftime(fmt)
    except (ValueError, AttributeError, TypeError) as e:
        app.logger.warning(f"Could not format datetime value '{value}' (type: {type(value)}): {e}")
        return value


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_all_report_section_keys():
    try:
        from wordpress_reporter import ALL_REPORT_SECTIONS
        return list(ALL_REPORT_SECTIONS.keys())
    except ImportError:
        app.logger.warning("Could not import ALL_REPORT_SECTIONS from wordpress_reporter. Using fallback list.")
        return ["introduction", "metrics_summary", "detailed_forecast_table", "company_profile",
                "valuation_metrics", "total_valuation", "profitability_growth", "analyst_insights",
                "financial_health", "technical_analysis_summary", "short_selling_info",
                "stock_price_statistics", "dividends_shareholder_returns", "conclusion_outlook",
                "risk_factors", "faq"]
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
            # Ensure authors is a list
            if 'authors' not in profile_data or not isinstance(profile_data['authors'], list):
                profile_data['authors'] = []
            profiles.append(profile_data)
    except Exception as e:
        app.logger.error(f"Error fetching site profiles for user {user_uid} from Firestore: {e}", exc_info=True)
    return profiles

def save_user_site_profile_to_firestore(user_uid, profile_data):
    if not FIREBASE_INITIALIZED_SUCCESSFULLY: return False
    db = get_firestore_client()
    if not db: app.logger.error(f"Firestore client not available for save_user_site_profile_to_firestore (user: {user_uid})."); return False
    try:
        profile_id_to_save = profile_data.pop('profile_id', None)
        now_iso = datetime.now(timezone.utc).isoformat()
        profile_data['last_updated_at'] = now_iso
        if 'authors' not in profile_data or not isinstance(profile_data['authors'], list):
            profile_data['authors'] = [] # Ensure authors is always a list

        if profile_id_to_save:
            doc_ref = db.collection(u'userSiteProfiles').document(user_uid).collection(u'profiles').document(profile_id_to_save)
            doc_ref.set(profile_data, merge=True) # Use set with merge=True for updates
            app.logger.info(f"Updated site profile {profile_id_to_save} for user {user_uid} in Firestore.")
            return profile_id_to_save
        else:
            profile_data['created_at'] = now_iso
            # Generate a new document ID if not provided (Firestore handles this)
            new_doc_ref = db.collection(u'userSiteProfiles').document(user_uid).collection(u'profiles').document()
            new_doc_ref.set(profile_data)
            profile_id_new = new_doc_ref.id
            app.logger.info(f"Added new site profile {profile_id_new} for user {user_uid} in Firestore.")
            return profile_id_new
    except Exception as e:
        app.logger.error(f"Error saving site profile for user {user_uid} to Firestore: {e}", exc_info=True)
        return False

def delete_user_site_profile_from_firestore(user_uid, profile_id_to_delete):
    if not FIREBASE_INITIALIZED_SUCCESSFULLY: return False
    db = get_firestore_client()
    if not db: app.logger.error(f"Firestore client not available for delete_user_site_profile_from_firestore (user: {user_uid})."); return False
    try:
        db.collection(u'userSiteProfiles').document(user_uid).collection(u'profiles').document(profile_id_to_delete).delete()
        app.logger.info(f"Deleted site profile {profile_id_to_delete} for user {user_uid}.")
        return True
    except Exception as e:
        app.logger.error(f"Error deleting site profile {profile_id_to_delete} for user {user_uid}: {e}", exc_info=True)
        return False

def get_automation_shared_context(user_uid, profiles_list):
    context = {}
    try:
        current_profile_ids = [p['profile_id'] for p in profiles_list if 'profile_id' in p]
        state = auto_publisher.load_state(user_uid=user_uid, current_profile_ids_from_run=current_profile_ids) if AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY else {}
        context['posts_today_by_profile'] = state.get('posts_today_by_profile', {})
        context['last_run_date_for_counts'] = state.get('last_run_date', 'N/A')
        context['processed_tickers_log_map'] = state.get('processed_tickers_detailed_log_by_profile', {})
        context['absolute_max_posts_cap'] = getattr(auto_publisher, 'ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP', 10)
    except Exception as e:
        app.logger.error(f"Error loading publisher state for shared_context (user: {user_uid}): {e}", exc_info=True)
        context.update({'posts_today_by_profile': {}, 'last_run_date_for_counts': "Error", 'processed_tickers_log_map': {}, 'absolute_max_posts_cap': 10})
    return context

def is_valid_url(url_string):
    if not url_string:
        return False
    if not (url_string.startswith('http://') or url_string.startswith('https://')):
        return False
    try:
        domain_part = url_string.split('//')[1].split('/')[0]
        if '.' not in domain_part or len(domain_part) < 3:
            return False
    except IndexError:
        return False
    return True

# --- Core Application Routes ---
@app.route('/')
def stock_analysis_homepage_route():
    return render_template('stock-analysis-homepage.html', title="AI Stock Predictions & Analysis")

@app.route('/dashboard')
@login_required
def dashboard_page():
    user_uid = session.get('firebase_user_uid')
    report_history, total_reports = [], 0 # Default values
    if user_uid:
        report_history, total_reports = get_report_history_for_user(user_uid, display_limit=10) # Get last 10 reports
    return render_template('dashboard.html',
                           title="Dashboard - Tickzen",
                           report_history=report_history,
                           total_reports=total_reports)


@app.route('/analyzer', methods=['GET'])
def analyzer_input_page():
    return render_template('analyzer_input.html', title="Stock Analyzer Input")

# === Modify the /start-analysis route ===
@app.route('/start-analysis', methods=['POST'])
def start_stock_analysis():
    ticker = request.form.get('ticker', '').strip().upper()
    app.logger.info(f"\n--- Received /start-analysis for ticker: {ticker} ---")
    valid_ticker_pattern = r'^[A-Z0-9\^.-]{1,10}$' # Regex for typical stock tickers
    if not ticker or not re.match(valid_ticker_pattern, ticker):
        flash(f"Invalid ticker format: '{ticker}'. Please use standard stock symbols (e.g., AAPL, ^GSPC).", "danger")
        return redirect(url_for('analyzer_input_page'))

    if not PIPELINE_IMPORTED_SUCCESSFULLY:
        flash("The Stock Analysis service is temporarily unavailable. Please try again later.", "danger")
        return redirect(url_for('analyzer_input_page'))

    try:
        request_timestamp_for_report = int(time.time()) # Use this for report generation and history
        app.logger.info(f"Running full stock analysis for ticker {ticker} with timestamp {request_timestamp_for_report}...")

        pipeline_result = run_pipeline(ticker, str(request_timestamp_for_report), APP_ROOT)
        
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
                    app.logger.error(f"Could not save HTML content from pipeline for {ticker}: {e_save}. Will try path_info if available.")
            
            if not report_filename_for_url and isinstance(path_info_from_pipeline, str) and path_info_from_pipeline.endswith(".html"):
                if os.path.isabs(path_info_from_pipeline) and path_info_from_pipeline.startswith(STOCK_REPORTS_PATH):
                    if os.path.exists(path_info_from_pipeline):
                        absolute_report_filepath_on_disk = path_info_from_pipeline
                        report_filename_for_url = os.path.relpath(absolute_report_filepath_on_disk, STOCK_REPORTS_PATH).replace(os.sep, '/')
                        app.logger.info(f"Using existing absolute report file from pipeline: {absolute_report_filepath_on_disk}. Relative for URL: {report_filename_for_url}")
                    else:
                        app.logger.warning(f"Absolute path from pipeline {path_info_from_pipeline} does not exist.")
                else:
                    potential_filename_for_url = path_info_from_pipeline.lstrip(os.sep).replace(os.sep, '/')
                    if potential_filename_for_url.startswith(STOCK_REPORTS_SUBDIR + '/'):
                        potential_filename_for_url = potential_filename_for_url[len(STOCK_REPORTS_SUBDIR)+1:]
                    potential_abs_path_in_reports_dir = os.path.join(STOCK_REPORTS_PATH, potential_filename_for_url)

                    if os.path.exists(potential_abs_path_in_reports_dir):
                        absolute_report_filepath_on_disk = potential_abs_path_in_reports_dir
                        report_filename_for_url = potential_filename_for_url 
                        app.logger.info(f"Using report file: {absolute_report_filepath_on_disk} (derived from path_info: '{path_info_from_pipeline}')")
                    elif os.path.isabs(path_info_from_pipeline): 
                         app.logger.warning(f"Absolute path_info {path_info_from_pipeline} not in STOCK_REPORTS_PATH and its interpretation as '{potential_filename_for_url}' not found in STOCK_REPORTS_PATH.")
                    else: 
                        app.logger.warning(f"Report file from relative path_info ('{path_info_from_pipeline}') interpreted as '{potential_filename_for_url}' not found in {STOCK_REPORTS_PATH}.")

            if not report_filename_for_url:
                error_detail = f"Pipeline output was unclear or report file could not be located/processed. Path: '{path_info_from_pipeline}', HTML content (start): '{str(report_html_content_from_pipeline)[:100]}...'"
                app.logger.error(error_detail)
                raise ValueError("Stock analysis report generation failed: " + error_detail)
        
        else: 
            app.logger.error(f"Unexpected or empty result structure from run_pipeline: {pipeline_result}")
            raise ValueError("Stock analysis pipeline did not return the expected result.")

        if not (report_filename_for_url and absolute_report_filepath_on_disk and os.path.exists(absolute_report_filepath_on_disk)):
            app.logger.error(f"Post-processing: Report filename for URL or absolute disk path is invalid or file does not exist. URL Filename: '{report_filename_for_url}', Disk Path: '{absolute_report_filepath_on_disk}'")
            raise ValueError("Report generation was unsuccessful or the final report path is invalid.")

        # --- SAVE TO HISTORY ---
        if 'firebase_user_uid' in session and report_filename_for_url:
            user_uid = session['firebase_user_uid']
            # Use the same timestamp that was used for the report filename for consistency
            generated_at_dt = datetime.fromtimestamp(request_timestamp_for_report, timezone.utc)
            save_report_to_history(user_uid, ticker, report_filename_for_url, generated_at_dt)
            app.logger.info(f"Attempted to save report to history for user {user_uid}, ticker {ticker}, filename {report_filename_for_url}")
        # --- END SAVE TO HISTORY ---

        view_report_url = url_for('view_generated_report', ticker=ticker, filename=report_filename_for_url)
        app.logger.info(f"Redirecting to new report viewer for {ticker}. Filename: '{report_filename_for_url}'. Viewer URL: {view_report_url}")
        return redirect(view_report_url)

    except Exception as e:
        app.logger.error(f"Error during stock analysis for {ticker}: {e}", exc_info=True)
        flash(f"An error occurred while analyzing {ticker}: {str(e)[:150]}...", "danger")
        return redirect(url_for('analyzer_input_page'))


# --- REPORT VIEWING ROUTES ---
@app.route('/view-report/<ticker>/<path:filename>')
@login_required 
def view_generated_report(ticker, filename):
    report_url = url_for('serve_static_report', filename=filename)
    return render_template('view_report_page.html',
                           title=f"Analysis Report: {ticker.upper()}",
                           ticker=ticker.upper(),
                           report_url=report_url,
                           download_filename=filename) 


@app.route('/static/stock_reports/<path:filename>')
def serve_static_report(filename):
    return send_from_directory(STOCK_REPORTS_PATH, filename)

@app.route('/static/<path:filename>')
def serve_static_general(filename): 
    return send_from_directory(app.static_folder, filename)


# --- AUTHENTICATION ROUTES ---
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
        return jsonify({"status": "success", "uid": decoded_token['uid'], "next_url": url_for('dashboard_page')}), 200
    else:
        app.logger.warning(f"Token verification failed. Decoded token: {decoded_token}")
        return jsonify({"error": "Invalid or expired token."}), 401

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('stock_analysis_homepage_route')) 

# --- USER & PROFILE MANAGEMENT ---
@app.route('/user-profile')
@login_required
def user_profile_page():
    return render_template('user_profile.html', title="Your Profile - Tickzen")

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
                           title="Site Profiles - Tickzen",
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
        flash("Please correct the errors in the 'Add New Profile' form.", "danger")
        return redirect(url_for('manage_site_profiles'))

    new_profile_data = {
        "profile_name": profile_name, "site_url": site_url, "sheet_name": sheet_name,
        "stockforecast_category_id": str(stockforecast_category_id) if stockforecast_category_id is not None else "",
        "min_scheduling_gap_minutes": min_sched_gap, "max_scheduling_gap_minutes": max_sched_gap,
        "env_prefix_for_feature_image_colors": env_prefix, "authors": authors_data,
        "report_sections_to_include": report_sections
    }

    if save_user_site_profile_to_firestore(user_uid, new_profile_data):
        flash(f"Profile '{new_profile_data['profile_name']}' added successfully!", "success")
    else:
        flash(f"Failed to add profile '{new_profile_data['profile_name']}'. An unexpected error occurred.", "danger")
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
        flash(f"Profile ID '{profile_id_from_firestore}' not found.", "error")
        return redirect(url_for('manage_site_profiles'))

    profile_data_original = profile_snap.to_dict()
    profile_data_original['profile_id'] = profile_id_from_firestore
    if 'authors' not in profile_data_original or not isinstance(profile_data_original['authors'], list):
        profile_data_original['authors'] = []


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

            if author_idx > 0 and username_field_key not in request.form : break
            if author_idx >=10 : app.logger.warning(f"Author limit for edit reached user {user_uid}"); break

            author_internal_id = request.form.get(author_internal_id_field, '').strip()
            wp_username = request.form.get(username_field_key, '').strip()
            wp_user_id_str = request.form.get(userid_field_key, '').strip()
            app_password_new = request.form.get(app_password_field_key, '') 

            if wp_username or wp_user_id_str or app_password_new: has_any_author_input_edit = True
            
            submitted_authors_raw_for_repopulation.append({
                "id": author_internal_id, 
                "wp_username": wp_username,
                "wp_user_id": wp_user_id_str,
            })

            if wp_username or wp_user_id_str or app_password_new: 
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
                    else: 
                        current_author_errors.append("App Password required for new/updated writer.")
                
                if current_author_errors: errors[f'{author_error_key_prefix}_general'] = f"Author {author_idx + 1} error: {' '.join(current_author_errors)}"
                elif wp_user_id_int is not None:
                     updated_authors.append({
                        "id": author_internal_id if author_internal_id else f"newauthor_{int(time.time())}_{author_idx}",
                        "wp_username": wp_username,
                        "wp_user_id": str(wp_user_id_int),
                        "app_password": final_app_password
                    })
            
            if not request.form.get(username_field_key) and author_idx == 0 and not has_any_author_input_edit: break
            if not request.form.get(username_field_key) and author_idx > 0 : break
            author_idx += 1


        if not updated_authors:
            if has_any_author_input_edit: errors['authors_general'] = "Ensure all fields are filled for each writer."
            else: errors['authors_general'] = "At least one writer is required."
        
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

        if save_user_site_profile_to_firestore(user_uid, profile_data_to_save):
            flash(f"Profile '{profile_data_to_save['profile_name']}' updated successfully!", "success")
        else:
            flash(f"Failed to update profile '{profile_data_to_save['profile_name']}'.", "danger")
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
    if delete_user_site_profile_from_firestore(user_uid, profile_id_to_delete):
        flash(f"Profile ID '{profile_id_to_delete}' deleted successfully.", "success")
    else:
        flash(f"Failed to delete profile ID '{profile_id_to_delete}'.", "error")
    return redirect(url_for('manage_site_profiles'))

# --- REPORT HISTORY MANAGEMENT ---
def save_report_to_history(user_uid, ticker, filename, generated_at_dt):
    """Saves a record of a generated report to Firestore."""
    if not FIREBASE_INITIALIZED_SUCCESSFULLY:
        app.logger.error("Firestore not available for saving report history.")
        return False
    db = get_firestore_client()
    if not db:
        app.logger.error("Firestore client not available for saving report history.")
        return False
    try:
        reports_history_collection = db.collection(u'userGeneratedReports')
        # Ensure generated_at_dt is timezone-aware (UTC) before saving
        if generated_at_dt.tzinfo is None:
            generated_at_dt = generated_at_dt.replace(tzinfo=timezone.utc)

        reports_history_collection.add({
            u'user_uid': user_uid,
            u'ticker': ticker.upper(), # Store ticker in uppercase for consistency
            u'filename': filename,
            u'generated_at': generated_at_dt 
        })
        app.logger.info(f"Report history saved for user {user_uid}, ticker {ticker}, filename {filename}.")
        return True
    except Exception as e:
        app.logger.error(f"Error saving report history for user {user_uid}, ticker {ticker}: {e}", exc_info=True)
        return False

def get_report_history_for_user(user_uid, display_limit=10):
    """Fetches report history for a user and the total count of their reports."""
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
        
        # Efficiently count documents (if supported by Firestore client library version for direct count)
        # Otherwise, streaming all and counting is a fallback.
        # For very large collections, consider maintaining a counter in a separate document.
        try:
            count_query = base_query.count() # Attempt to use aggregate count
            count_result = count_query.get()
            total_user_reports_count = count_result[0][0].value if count_result else 0
        except AttributeError: # Fallback if .count() is not available or behaves differently
            app.logger.warning("Firestore count() aggregate not available or failed, falling back to streaming for count.")
            all_user_reports_stream = base_query.stream()
            all_user_reports_docs = list(all_user_reports_stream) # Consume stream to count
            total_user_reports_count = len(all_user_reports_docs)
            # If we fell back, we already have the docs, so we can sort these instead of re-querying
            # However, the original logic sorted after fetching with limit, which is more efficient.
            # To maintain that, we will re-query with ordering and limit if we used the fallback.
            # For simplicity here, if fallback used, we sort 'all_user_reports_docs' if display_limit is large.
            # But ideally, we always use a query with orderBy and limit for display.

        # Query for display with ordering and limit
        display_query = base_query.order_by(u'generated_at', direction='DESCENDING').limit(display_limit)
        docs_for_display_stream = display_query.stream()

        for doc_snapshot in docs_for_display_stream:
            report_data = doc_snapshot.to_dict()
            report_data['id'] = doc_snapshot.id 
            
            # Ensure 'generated_at' is a datetime object for the template filter
            generated_at_val = report_data.get('generated_at')
            if hasattr(generated_at_val, 'seconds'): # Firestore Timestamp
                 report_data['generated_at'] = datetime.fromtimestamp(generated_at_val.seconds + generated_at_val.nanoseconds / 1e9, timezone.utc)
            elif isinstance(generated_at_val, (int, float)): # Unix timestamp (seconds or ms)
                if generated_at_val > 10**10: # Likely ms
                    report_data['generated_at'] = datetime.fromtimestamp(generated_at_val / 1000, timezone.utc)
                else: # Likely s
                    report_data['generated_at'] = datetime.fromtimestamp(generated_at_val, timezone.utc)

            reports_for_display.append(report_data)
                
        app.logger.info(f"Fetched {len(reports_for_display)} report history items for user {user_uid} (Display Limit: {display_limit}, Total Found: {total_user_reports_count}).")
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
def automation_runner_page():
    user_uid = session['firebase_user_uid']
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    return render_template('run_automation_page.html',
                           title="Run Automation - Tickzen",
                           user_site_profiles=user_site_profiles,
                           **shared_context)

@app.route('/run-automation-now', methods=['POST'])
@login_required
def run_automation_now():
    user_uid = session['firebase_user_uid']
    if not AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY:
        flash("Automation service is currently unavailable. Please try again later.", "danger")
        return redirect(url_for('automation_runner_page'))

    profile_ids_to_run = request.form.getlist('run_profile_ids[]')
    if not profile_ids_to_run:
        flash("No profiles selected to run automation.", "info")
        return redirect(url_for('automation_runner_page'))

    all_user_profiles = get_user_site_profiles_from_firestore(user_uid)
    selected_profiles_data = [p for p in all_user_profiles if p.get("profile_id") in profile_ids_to_run]

    if not selected_profiles_data:
        flash("Selected profiles could not be found. Please try again.", "warning")
        return redirect(url_for('automation_runner_page'))

    articles_map = {}
    custom_tickers_map = {}
    uploaded_files_map = {}

    for profile_data_item in selected_profiles_data:
        pid = profile_data_item["profile_id"]
        try:
            articles_map[pid] = max(0, int(request.form.get(f'posts_for_profile_{pid}', 0)))
        except ValueError:
            articles_map[pid] = 0
            flash(f"Invalid number of posts for '{profile_data_item.get('profile_name', pid)}', defaulting to 0.", "warning")

        ticker_source_method = request.form.get(f'ticker_source_{pid}', 'file') 

        if ticker_source_method == 'manual':
            custom_tickers_str = request.form.get(f'custom_tickers_{pid}', '').strip()
            if custom_tickers_str:
                custom_tickers_map[pid] = [t.strip().upper() for t in custom_tickers_str.split(',') if t.strip()]
        elif ticker_source_method == 'file':
            file_field_name = f'ticker_file_{pid}'
            if file_field_name in request.files:
                file_obj = request.files[file_field_name]
                if file_obj and file_obj.filename and allowed_file(file_obj.filename):
                    from werkzeug.utils import secure_filename
                    s_filename = secure_filename(file_obj.filename)
                    try:
                        file_content_bytes = file_obj.read()
                        uploaded_files_map[pid] = {"original_filename": s_filename, "content_bytes": file_content_bytes}
                        app.logger.info(f"File '{s_filename}' queued for profile {pid}.")
                    except Exception as e_file_read:
                        app.logger.error(f"Error reading uploaded file '{s_filename}' for profile {pid}: {e_file_read}")
                        flash(f"Error processing file for '{profile_data_item.get('profile_name', pid)}'.", "danger")
                elif file_obj and file_obj.filename: 
                    flash(f"File type of '{file_obj.filename}' not allowed for profile '{profile_data_item.get('profile_name', pid)}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", "warning")

    flash(f"Initiating automation for {len(selected_profiles_data)} profile(s)... Check logs for details.", "info")
    try:
        results = auto_publisher.trigger_publishing_run(
            user_uid,
            selected_profiles_data, 
            articles_map,
            custom_tickers_by_profile_id=custom_tickers_map,
            uploaded_file_details_by_profile_id=uploaded_files_map
        )
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
            flash("Automation run completed but returned no specific results. Check system logs.", "warning")
    except Exception as e:
        flash(f"A critical error occurred during the automation run: {str(e)}", "danger")
        app.logger.error(f"Automation run failed for user {user_uid}: {e}", exc_info=True)
    return redirect(url_for('automation_runner_page'))


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

    valid_ticker_pattern = r'^[A-Z0-9\^.-]{1,10}$'
    if not ticker or not re.match(valid_ticker_pattern, ticker):
        return jsonify({'status': 'error', 'message': f"Invalid ticker symbol: '{ticker}'. Please use standard symbols."}), 400

    if not PIPELINE_IMPORTED_SUCCESSFULLY:
        return jsonify({'status': 'error', 'message': 'WordPress Asset generation service is temporarily unavailable.'}), 503

    try:
        timestamp = str(int(time.time()))
        app.logger.info(f"Running WordPress asset pipeline for ticker: {ticker} (Timestamp: {timestamp})...")

        model_obj, forecast_obj, html_report_fragment, img_urls_dict = run_wp_pipeline(ticker, timestamp, APP_ROOT)

        if not isinstance(img_urls_dict, dict):
            app.logger.warning(f"run_wp_pipeline for {ticker} returned img_urls not as dict: {type(img_urls_dict)}. Defaulting to empty.")
            img_urls_dict = {} 

        if html_report_fragment and "Error Generating Report" not in html_report_fragment:
            duration = time.time() - start_time
            app.logger.info(f"WordPress asset pipeline for {ticker} completed in {duration:.2f}s.")
            
            return jsonify({
                'status': 'success',
                'ticker': ticker,
                'report_html': html_report_fragment,
                'chart_urls': img_urls_dict, 
                'duration': f"{duration:.2f}s"
            })
        else:
            error_detail = f"WordPress Asset HTML generation failed or returned error. Detail: {str(html_report_fragment)[:200]}"
            app.logger.error(error_detail)
            raise ValueError(error_detail)

    except Exception as e:
        app.logger.error(f"Error in /generate-wp-assets for ticker {ticker}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"A server error occurred while generating assets for {ticker}."}), 500


#--- Main Execution ---
if __name__ == '__main__':
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
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port, threaded=True, use_reloader=debug_mode)