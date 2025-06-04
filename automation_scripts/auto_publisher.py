# auto_publisher.py
import sys
import os
import pandas as pd
import time
from datetime import datetime, timedelta, timezone
import re
import pickle
import random
from itertools import cycle
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import requests
import base64
import json
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- START: Firebase Admin Storage Import (Conceptual) ---
# You'll need to ensure firebase_admin is available and initialized
# in a way that storage can be accessed.
try:
    from firebase_admin import storage # For storage operations
except ImportError:
    storage = None # Fallback if firebase_admin is not available in this context
# --- END: Firebase Admin Storage Import ---


# Add the project root to Python's module search path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

try:
    from reporting_tools.wordpress_reporter import generate_wordpress_report, ALL_REPORT_SECTIONS
except ImportError:
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.error("CRITICAL: Failed to import 'generate_wordpress_report' or 'ALL_REPORT_SECTIONS'. Ensure it's accessible.")
    ALL_REPORT_SECTIONS = {
        "introduction": None, "metrics_summary": None, "detailed_forecast_table": None,
        "company_profile": None, "valuation_metrics": None, "total_valuation": None,
        "profitability_growth": None, "analyst_insights": None, "financial_health": None,
        "technical_analysis_summary": None, "short_selling_info": None,
        "stock_price_statistics": None, "dividends_shareholder_returns": None,
        "conclusion_outlook": None, "risk_factors": None, "faq": None
    }
    if __name__ == '__main__': exit(1)
    else: raise

LOG_FILE = "auto_publisher.log"
app_logger = logging.getLogger("AutoPublisherLogger")
if not app_logger.handlers:
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    APP_ROOT_PATH_FOR_LOG = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(APP_ROOT_PATH_FOR_LOG, '..', 'logs', LOG_FILE)
    handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(APP_ROOT, "..", "state", "wordpress_publisher_state_v11.pkl")
PROFILES_CONFIG_FILE = os.path.join(APP_ROOT, "..", "config", "profiles_config.json")

FRED_API_KEY = os.getenv("FRED_API_KEY")
ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP = int(os.getenv("MAX_POSTS_PER_DAY_PER_SITE", "20"))

SITES_PROFILES_CONFIG = []

# --- START: New Helper for Firebase Storage (Conceptual) ---
def get_file_content_from_storage(storage_path, original_filename):
    """
    Conceptual function to download file content from Firebase Storage.
    Returns file content as bytes, or None on error.
    """
    if not storage:
        app_logger.error("Firebase Admin SDK (storage) not available. Cannot download from storage.")
        return None
    if not storage_path:
        app_logger.error(f"No storage path provided for file {original_filename}.")
        return None

    try:
        # This assumes your firebase_admin_setup.py provides a way to get the default bucket
        # or you have a bucket instance available.
        # from config.firebase_admin_setup import get_storage_bucket_instance # Conceptual
        # bucket = get_storage_bucket_instance()
        # For now, we'll mock this part or assume 'storage.bucket()' works if initialized
        bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')
        bucket = storage.bucket(bucket_name if bucket_name else None) # Get default or named bucket
        
        blob = bucket.blob(storage_path)
        if not blob.exists():
            app_logger.error(f"File not found in Firebase Storage at path: {storage_path}")
            return None
        
        app_logger.info(f"Downloading '{original_filename}' from Firebase Storage path: {storage_path}")
        content_bytes = blob.download_as_bytes()
        app_logger.info(f"Successfully downloaded {len(content_bytes)} bytes for '{original_filename}'.")
        return content_bytes
    except Exception as e:
        app_logger.error(f"Error downloading '{original_filename}' from Firebase Storage path '{storage_path}': {e}", exc_info=True)
        return None
# --- END: New Helper for Firebase Storage ---

def _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, phase, stage, message, status="info"):
    if socketio_instance and user_room:
        payload = {
            'profile_id': profile_id,
            'ticker': ticker,
            'phase': phase,
            'stage': stage,
            'message': message,
            'status': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        try:
            socketio_instance.emit('automation_update', payload, room=user_room)
            socketio_instance.sleep(0.01)
        except Exception as e:
            app_logger.error(f"Failed to emit SocketIO message to room {user_room}: {e}")
    else:
        log_level = logging.INFO
        if status == "error": log_level = logging.ERROR
        elif status == "warning": log_level = logging.WARNING
        app_logger.log(log_level, f"Progress (Profile: {profile_id}, Ticker: {ticker}, Phase: {phase}, Stage: {stage}): {message}")

def load_profiles_config():
    global SITES_PROFILES_CONFIG
    if not os.path.exists(PROFILES_CONFIG_FILE):
        app_logger.warning(f"{PROFILES_CONFIG_FILE} not found. No site profiles loaded for CLI mode.")
        SITES_PROFILES_CONFIG = []
        return SITES_PROFILES_CONFIG
    try:
        with open(PROFILES_CONFIG_FILE, 'r', encoding='utf-8') as f:
            SITES_PROFILES_CONFIG = json.load(f)
        app_logger.info(f"Successfully loaded {len(SITES_PROFILES_CONFIG)} site profiles from {PROFILES_CONFIG_FILE} for CLI mode.")
    except Exception as e:
        app_logger.error(f"Failed to load {PROFILES_CONFIG_FILE}: {e}")
        SITES_PROFILES_CONFIG = []
    return SITES_PROFILES_CONFIG

def load_state(user_uid=None, current_profile_ids_from_run=None):
    active_profile_ids = set()
    if current_profile_ids_from_run:
        active_profile_ids.update(str(pid) for pid in current_profile_ids_from_run if pid)
    else:
        if not SITES_PROFILES_CONFIG and os.path.exists(PROFILES_CONFIG_FILE):
            load_profiles_config()
        for profile in SITES_PROFILES_CONFIG:
            if profile.get("profile_id"):
                active_profile_ids.add(str(profile.get("profile_id")))

    default_factories = {
        'pending_tickers_by_profile': list, 'failed_tickers_by_profile': list,
        'last_successful_schedule_time_by_profile': lambda: None,
        'posts_today_by_profile': lambda: 0, 'published_tickers_log_by_profile': set,
        'processed_tickers_detailed_log_by_profile': list,
        'last_author_index_by_profile': lambda: -1
    }
    default_state = {key: {str(pid): factory() for pid in active_profile_ids} for key, factory in default_factories.items()}
    default_state['last_run_date'] = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'rb') as f: state = pickle.load(f)
            app_logger.info(f"Loaded state from {STATE_FILE}")
            for key, factory in default_factories.items():
                if key not in state: state[key] = {str(pid): factory() for pid in active_profile_ids}
                else:
                    for pid in active_profile_ids:
                        if str(pid) not in state[key]: state[key][str(pid)] = factory()
                        if key == 'processed_tickers_detailed_log_by_profile' and not isinstance(state[key].get(str(pid)), list):
                            state[key][str(pid)] = []


            if current_profile_ids_from_run is None:
                for key in default_factories.keys():
                    if key in state:
                        for spid_del in [spid for spid in state[key] if spid not in active_profile_ids]:
                            del state[key][spid_del]

            current_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            if state.get('last_run_date') != current_date_str:
                app_logger.info(f"New day ({current_date_str}). Resetting daily counts and processed logs.")
                for pid_in_state in list(state.get('posts_today_by_profile', {}).keys()):
                    state['posts_today_by_profile'][pid_in_state] = 0
                for pid_in_state in list(state.get('processed_tickers_detailed_log_by_profile', {}).keys()):
                     state['processed_tickers_detailed_log_by_profile'][pid_in_state] = []
                state['last_run_date'] = current_date_str

            for pid_str in active_profile_ids:
                state.setdefault('posts_today_by_profile', {})[pid_str] = state.get('posts_today_by_profile', {}).get(pid_str, 0)
                state.setdefault('processed_tickers_detailed_log_by_profile', {}).setdefault(pid_str, [])
            return state
        except Exception as e:
            app_logger.warning(f"Could not load/process state file '{STATE_FILE}': {e}. Using default.", exc_info=True)
    save_state(default_state)
    return default_state

def save_state(state):
    try:
        if 'processed_tickers_detailed_log_by_profile' in state:
            for profile_id, log_list in state['processed_tickers_detailed_log_by_profile'].items():
                if not isinstance(log_list, list):
                    app_logger.warning(f"Correcting processed_tickers_detailed_log_by_profile for {profile_id} to be a list before saving.")
                    state['processed_tickers_detailed_log_by_profile'][profile_id] = []

        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'wb') as f: pickle.dump(state, f)
        app_logger.info(f"Saved state to {STATE_FILE}")
    except Exception as e:
        app_logger.error(f"Could not save state to {STATE_FILE}: {e}", exc_info=True)

def generate_feature_image(headline_text, site_display_name_for_wm, profile_config_entry, output_path, ticker="N/A"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        img_width = int(os.getenv("FEATURE_IMAGE_WIDTH", 1200))
        img_height = int(os.getenv("FEATURE_IMAGE_HEIGHT", 630))
        env_prefix = profile_config_entry.get('env_prefix_for_feature_image_colors', 'DEFAULT')
        app_logger.info(f"[FeatureImage] Resolved env_prefix: '{env_prefix}'")

        def get_env_color(var_name, default_hex):
            specific_env_var = f"{env_prefix}_{var_name}"
            default_env_var = f"DEFAULT_{var_name}"
            color_val = os.getenv(specific_env_var, os.getenv(default_env_var, default_hex))
            source = "env specific" if os.getenv(specific_env_var) else "env default" if os.getenv(default_env_var) else "hardcoded"
            app_logger.info(f"[FeatureImage] Color for '{var_name}': '{color_val}' (Source: {source})")
            return color_val

        bg_hex = get_env_color("FEATURE_BG_COLOR", "#0A264E")
        headline_color_hex = get_env_color("FEATURE_HEADLINE_TEXT_COLOR", "#FFFFFF")
        sub_headline_color_hex = get_env_color("FEATURE_SUBTEXT_COLOR", "#E0E0E0")
        watermark_text_color_hex = get_env_color("FEATURE_WATERMARK_TEXT_COLOR", "#A0A0A0")
        right_panel_bg_hex = get_env_color("FEATURE_RIGHT_PANEL_BG_COLOR", "#1C3A6E")
        ticker_text_color_hex = get_env_color("FEATURE_TICKER_TEXT_COLOR", "#FFFFFF")

        resolved_site_logo_path_specific_var = f"{env_prefix}_SITE_LOGO_PATH"
        resolved_site_logo_path_default_var = "DEFAULT_SITE_LOGO_PATH"
        site_logo_path = os.getenv(resolved_site_logo_path_specific_var, os.getenv(resolved_site_logo_path_default_var))
        app_logger.info(f"[FeatureImage] Attempting to use Site Logo. Specific var: '{resolved_site_logo_path_specific_var}', Default var: '{resolved_site_logo_path_default_var}'. Resolved path: '{site_logo_path}'")

        def hex_to_rgba(h, default_color=(0,0,0,0)):
            original_hex = h
            h = (h or "").lstrip('#')
            try:
                if len(h) == 6: return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)
                if len(h) == 8: return tuple(int(h[i:i+2], 16) for i in (0, 2, 4, 6))
            except ValueError as e_hex_val:
                app_logger.warning(f"[FeatureImage] hex_to_rgba ValueError for '{original_hex}' (parsed as '{h}'): {e_hex_val}. Using default: {default_color}")
                return default_color
            except Exception as e_hex_other:
                app_logger.warning(f"[FeatureImage] hex_to_rgba unexpected error for '{original_hex}': {e_hex_other}. Using default: {default_color}")
                return default_color
            app_logger.warning(f"[FeatureImage] hex_to_rgba: '{original_hex}' (parsed as '{h}') is invalid format. Using default: {default_color}")
            return default_color

        bg_color = hex_to_rgba(bg_hex, (10, 38, 78, 255))
        headline_color = hex_to_rgba(headline_color_hex, (255,255,255,255))
        sub_headline_color = hex_to_rgba(sub_headline_color_hex, (224,224,224,255))
        watermark_text_color = hex_to_rgba(watermark_text_color_hex, (160,160,160,255))
        right_panel_bg_color = hex_to_rgba(right_panel_bg_hex, (28, 58, 110, 255))
        ticker_text_color = hex_to_rgba(ticker_text_color_hex, (255,255,255,255))

        def get_font(env_var_name, default_font_name, default_size):
            font_path_env = os.getenv(env_var_name)
            if font_path_env:
                 font_path = font_path_env if os.path.isabs(font_path_env) else os.path.join(PROJECT_ROOT, font_path_env)
            else:
                 font_path = os.path.join(PROJECT_ROOT, default_font_name)

            try:
                return ImageFont.truetype(font_path, default_size)
            except IOError:
                app_logger.warning(f"Font not found at {font_path} (from env '{env_var_name}' or default '{default_font_name}'). Using Pillow's default.")
                try:
                    return ImageFont.truetype("arial.ttf", default_size)
                except IOError:
                    return ImageFont.load_default()


        font_headline = get_font("FONT_PATH_HEADLINE", "fonts/arialbd.ttf", img_height // 12)
        font_sub_headline = get_font("FONT_PATH_SUB_HEADLINE", "fonts/arial.ttf", img_height // 25)
        font_watermark = get_font("FONT_PATH_WATERMARK", "fonts/arial.ttf", img_height // 30)
        font_ticker = get_font("FONT_PATH_TICKER", "fonts/arialbd.ttf", img_height // 5)

        img = Image.new('RGBA', (img_width, img_height), bg_color)
        app_logger.info(f"[FeatureImage] Base image created with bg_color (RGBA): {bg_color}")
        draw = ImageDraw.Draw(img)
        padding = img_width // 25
        logo_max_h = img_height // 8
        text_area_left_margin = padding
        right_panel_width = int(img_width * 0.40)
        right_panel_x_start = img_width - right_panel_width
        draw.rectangle([right_panel_x_start, 0, img_width, img_height], fill=right_panel_bg_color)
        current_y = padding
        if site_logo_path and os.path.exists(site_logo_path):
            try:
                logo_img = Image.open(site_logo_path).convert("RGBA")
                ratio = min(logo_max_h / logo_img.height, (right_panel_x_start - 2*padding) / logo_img.width)
                new_w = int(logo_img.width * ratio); new_h = int(logo_img.height * ratio)
                logo_img = logo_img.resize((new_w, new_h), Image.LANCZOS)
                img.paste(logo_img, (text_area_left_margin, current_y), logo_img)
                current_y += new_h + padding // 2
            except Exception as e_logo:
                app_logger.error(f"Error loading or pasting site logo from {site_logo_path}: {e_logo}")
                initials = "".join([name[0] for name in site_display_name_for_wm.split()[:2]]).upper()
                if initials:
                    draw.text((text_area_left_margin, current_y), initials, font=font_headline, fill=headline_color)
                    current_y += font_headline.getbbox(initials)[3] + padding // 2
        else:
            app_logger.info(f"Site logo not found or path not set. Skipping logo.")
        text_area_width = right_panel_x_start - text_area_left_margin - padding
        words = headline_text.split(); lines = []; current_line = ""
        for word in words:
            if draw.textbbox((0,0), current_line + word, font=font_headline)[2] <= text_area_width:
                current_line += word + " "
            else:
                lines.append(current_line.strip()); current_line = word + " "
        lines.append(current_line.strip())
        for line in lines:
            line_bbox = font_headline.getbbox(line); line_height = line_bbox[3] - line_bbox[1]
            if current_y + line_height > img_height - padding - font_sub_headline.getbbox("A")[3] - font_watermark.getbbox("A")[3]: break
            draw.text((text_area_left_margin, current_y), line, font=font_headline, fill=headline_color, anchor="lt")
            current_y += line_height * 1.2
        current_y += padding // 3
        sub_headline_text = f"Analysis by {site_display_name_for_wm} Team"
        sub_headline_bbox = font_sub_headline.getbbox(sub_headline_text)
        sub_headline_height = sub_headline_bbox[3] - sub_headline_bbox[1]
        if current_y + sub_headline_height < img_height - padding - font_watermark.getbbox("A")[3]:
            draw.text((text_area_left_margin, current_y), sub_headline_text, font=font_sub_headline, fill=sub_headline_color, anchor="lt")
        if ticker and ticker != "N/A":
            ticker_x_centered = right_panel_x_start + (right_panel_width / 2)
            ticker_y_centered = img_height / 2
            draw.text((ticker_x_centered, ticker_y_centered), ticker, font=font_ticker, fill=ticker_text_color, anchor="mm")
        watermark_text = f"@{site_display_name_for_wm}"
        wm_x_centered = img_width / 2
        wm_y_bottom = img_height - (padding // 2)
        draw.text((wm_x_centered, wm_y_bottom), watermark_text, font=font_watermark, fill=watermark_text_color, anchor="mb")
        img.save(output_path, "PNG", quality=90, optimize=True)
        return output_path
    except ImportError: app_logger.error("Pillow (PIL) not installed."); return None
    except Exception as e: app_logger.error(f"Feature image error for '{headline_text}': {e}", exc_info=True); return None

def upload_image_to_wordpress(image_path, site_url, author, title="Featured Image"):
    if not image_path or not os.path.exists(image_path): return None
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/media"
    creds = base64.b64encode(f"{author['wp_username']}:{author['app_password']}".encode()).decode('utf-8')
    filename = os.path.basename(image_path)
    headers = {"Authorization": f"Basic {creds}", "Content-Disposition": f'attachment; filename="{filename}"'}
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (filename, f, 'image/png')}
            response = requests.post(url, headers=headers, files=files, data={'title': title, 'alt_text': title}, timeout=120)
        response.raise_for_status(); return response.json().get('id')
    except Exception as e: app_logger.error(f"Image upload error to {site_url} for {title}: {e}"); return None

def create_wordpress_post(site_url, author, title, content, sched_time, cat_id=None, media_id=None):
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
    creds = base64.b64encode(f"{author['wp_username']}:{author['app_password']}".encode()).decode('utf-8')
    headers = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
    slug = re.sub(r'[^\w]+', '-', title.lower()).strip('-')[:70]
    payload = {"title": title, "content": content, "status": "future", "date_gmt": sched_time.isoformat(), "author": author['wp_user_id'], "slug": slug}
    if media_id: payload["featured_media"] = media_id
    if cat_id:
        try: payload["categories"] = [int(cat_id)]
        except ValueError: app_logger.warning(f"Invalid category_id '{cat_id}'.")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status(); app_logger.info(f"Post '{title}' scheduled on {site_url}. ID: {response.json().get('id')}")
        return True
    except Exception as e: app_logger.error(f"WP post error for '{title}' on {site_url}: {e}"); return False

def load_tickers_from_excel(profile_config):
    sheet_name = profile_config.get('sheet_name')
    excel_path = os.getenv("EXCEL_FILE_PATH")
    if excel_path and not os.path.isabs(excel_path):
        excel_path = os.path.join(PROJECT_ROOT, excel_path)

    ticker_column_names = [
        "Ticker", "Tickers", "Symbol", "Symbols",
        "Stock", "Stocks", "Keyword", "Keywords"
    ]

    if not sheet_name:
        app_logger.warning(f"No sheet_name provided for profile '{profile_config.get('profile_name', 'Unknown Profile')}'. Cannot load tickers from Excel.")
        return []
    if not excel_path:
        app_logger.error("EXCEL_FILE_PATH environment variable not set or empty. Cannot load tickers from Excel.")
        return []
    if not os.path.exists(excel_path):
        app_logger.error(f"Excel file not found at specified path: {excel_path}")
        return []

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        ticker_col_found = None
        for col_name_option in ticker_column_names:
            if col_name_option in df.columns:
                ticker_col_found = col_name_option
                break

        if not ticker_col_found:
            app_logger.warning(f"No standard ticker column (e.g., {', '.join(ticker_column_names)}) found in sheet '{sheet_name}' of '{excel_path}'. Trying first column.")
            if not df.empty:
                ticker_col_found = df.columns[0]
            else:
                app_logger.warning(f"Sheet '{sheet_name}' in '{excel_path}' is empty.")
                return []

        app_logger.info(f"Using column '{ticker_col_found}' for tickers from sheet '{sheet_name}'.")
        return df[ticker_col_found].dropna().astype(str).str.strip().str.upper().tolist()

    except Exception as e:
        app_logger.error(f"Error reading tickers from Excel file '{excel_path}', sheet '{sheet_name}': {e}", exc_info=True)
        return []


# MODIFIED: Function to load tickers from uploaded file (now from storage path)
def load_tickers_from_uploaded_file(storage_path, original_filename, user_uid=None, profile_id=None):
    """
    Loads tickers from a file specified by its storage_path in Firebase Storage.
    """
    app_logger.info(f"Attempting to load tickers from storage: '{storage_path}' (original: '{original_filename}') for profile {profile_id}, user {user_uid}.")
    content_bytes = get_file_content_from_storage(storage_path, original_filename)
    if content_bytes is None:
        app_logger.error(f"Failed to download file content from storage path: {storage_path}")
        return []

    common_ticker_column_names = ["Ticker", "Tickers", "Symbol", "Symbols", "Stock", "Stocks", "Keyword", "Keywords"]
    try:
        if original_filename.lower().endswith('.csv'):
            try: content_str = content_bytes.decode('utf-8')
            except UnicodeDecodeError: content_str = content_bytes.decode('latin1')
            df = pd.read_csv(io.StringIO(content_str))
        elif original_filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content_bytes))
        else:
            app_logger.warning(f"Unsupported file type for ticker loading: {original_filename}")
            return []

        if df.empty:
            app_logger.warning(f"File '{original_filename}' (from storage) is empty or could not be parsed.")
            return []

        ticker_col_found = None
        for col_name_option in common_ticker_column_names:
            if col_name_option in df.columns:
                ticker_col_found = col_name_option
                break

        if not ticker_col_found:
            ticker_col_found = df.columns[0]
            app_logger.info(f"No standard ticker column found in '{original_filename}' (from storage). Using first column: '{ticker_col_found}'.")
        else:
            app_logger.info(f"Found ticker column '{ticker_col_found}' in '{original_filename}' (from storage).")

        tickers = df[ticker_col_found].dropna().astype(str).str.strip().str.upper().tolist()
        app_logger.info(f"Loaded {len(tickers)} tickers from '{original_filename}' (from storage).")
        return tickers

    except Exception as e:
        app_logger.error(f"Error processing file '{original_filename}' (from storage): {e}", exc_info=True)
        return []


def generate_dynamic_headline(ticker, profile_name):
    site_specific_prefix = ""
    if "Forecast" in profile_name or "Radar" in profile_name:
        site_specific_prefix = f"{ticker} Stock Forecast: "
    elif "Bernini" in profile_name:
        site_specific_prefix = f"{ticker} Analysis by Bernini Capital: "

    base_headlines = [
        f"Is {ticker} a Smart Investment Now?",
        f"{ticker} Stock Deep Dive: Price Prediction & Analysis",
        f"Future of {ticker}: Expert Analysis and Forecast",
        f"Should You Buy {ticker} Stock? A detailed Review"
    ]
    return site_specific_prefix + random.choice(base_headlines)


_active_runs = {}

def stop_publishing_run(user_uid, profile_id):
    global _active_runs
    if user_uid in _active_runs and profile_id in _active_runs[user_uid]:
        _active_runs[user_uid][profile_id]["stop_requested"] = True
        app_logger.info(f"Stop request registered for profile {profile_id} (User: {user_uid})")
        return {'success': True, 'message': 'Stop request received. The process will halt after the current ticker.'}
    app_logger.warning(f"No active run found to stop for profile {profile_id} (User: {user_uid})")
    return {'success': False, 'message': 'No active run found for this profile to stop.'}


# MODIFIED: trigger_publishing_run to use storage_path
def trigger_publishing_run(user_uid, profiles_to_process_data_list, articles_to_publish_per_profile_map,
                           custom_tickers_by_profile_id=None, uploaded_file_details_by_profile_id=None, # This now contains storage_path
                           socketio_instance=None, user_room=None):
    global _active_runs
    if user_uid not in _active_runs: _active_runs[user_uid] = {}
    for profile_config in profiles_to_process_data_list:
        profile_id = profile_config.get("profile_id")
        if profile_id: _active_runs[user_uid][profile_id] = {"active": True, "stop_requested": False}

    _emit_automation_progress(socketio_instance, user_room, "Overall", "N/A", "Initialization", "Run Started", f"Processing {len(profiles_to_process_data_list)} profiles.", "info")
    profile_ids_for_run = [p.get("profile_id") for p in profiles_to_process_data_list if p.get("profile_id")]
    state = load_state(user_uid=user_uid, current_profile_ids_from_run=profile_ids_for_run)
    run_results_summary = {}

    for profile_config in profiles_to_process_data_list:
        profile_id = str(profile_config.get("profile_id"))
        profile_name = profile_config.get("profile_name", profile_id)
        current_run_detailed_logs_for_profile = []

        _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Profile Processing", "Starting", f"Processing profile: {profile_name}", "info")
        if not profile_id: continue
        if _active_runs[user_uid][profile_id].get("stop_requested", False):
            msg = f"Halted by user: {profile_name}"; _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Processing", "Halted", msg, "warning")
            current_run_detailed_logs_for_profile.append({"ticker": "N/A", "status": "Halted", "message": msg, "generation_timestamp": None, "publication_timestamp": None, "writer_username": None})
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            _active_runs[user_uid][profile_id]["active"] = False; continue

        authors = profile_config.get('authors', [])
        if not authors:
            msg = f"No authors for '{profile_name}'. Skipping."; _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Setup", "Skipped", msg, "warning")
            current_run_detailed_logs_for_profile.append({"ticker": "N/A", "status": "Skipped - No Authors", "message": msg, "generation_timestamp": None, "publication_timestamp": None, "writer_username": None})
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            _active_runs[user_uid][profile_id]["active"] = False; continue

        posts_today = state['posts_today_by_profile'].get(profile_id, 0)
        requested_posts = articles_to_publish_per_profile_map.get(profile_id, 0)
        can_publish = ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP - posts_today
        to_attempt = min(requested_posts, can_publish)

        if to_attempt <= 0:
            msg = f"Limit reached for '{profile_name}'. Today: {posts_today}/{ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP}, Req: {requested_posts}"
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Setup", "Skipped - Limit", msg, "info")
            current_run_detailed_logs_for_profile.append({"ticker": "N/A", "status": "Skipped - Daily Limit", "message": msg, "generation_timestamp": None, "publication_timestamp": None, "writer_username": None})
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            _active_runs[user_uid][profile_id]["active"] = False; continue
        _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Setup", "Post Count", f"Attempting {to_attempt} posts for {profile_name}.", "info")

        tickers_for_this_profile_run = []
        source_type = "Excel/State (Default)"

        if custom_tickers_by_profile_id and profile_id in custom_tickers_by_profile_id and custom_tickers_by_profile_id[profile_id]:
            tickers_for_this_profile_run = custom_tickers_by_profile_id[profile_id]
            source_type = "Manual Entry"
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "Custom", f"Processing {len(tickers_for_this_profile_run)} custom tickers.", "info")
        elif uploaded_file_details_by_profile_id and profile_id in uploaded_file_details_by_profile_id:
            f_details = uploaded_file_details_by_profile_id[profile_id]
            storage_path = f_details.get("storage_path")
            original_filename = f_details.get("original_filename")
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "File", f"Reading tickers from '{original_filename}' (from storage).", "info")
            # Call the modified load_tickers_from_uploaded_file
            tickers_for_this_profile_run = load_tickers_from_uploaded_file(storage_path, original_filename, user_uid, profile_id)
            source_type = "Uploaded File (Storage)"
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "File", f"Found {len(tickers_for_this_profile_run)} tickers in file from storage.", "info")
        else: # Fallback to state/excel (no change needed here for this part of the logic)
            pending = state['pending_tickers_by_profile'].get(profile_id, [])
            if not pending:
                excel_tickers = load_tickers_from_excel(profile_config)
                failed = list(state['failed_tickers_by_profile'].get(profile_id, []))
                published = state['published_tickers_log_by_profile'].get(profile_id, set())
                tickers_for_this_profile_run = [t for t in failed + excel_tickers if t not in published and t not in tickers_for_this_profile_run]
                state['pending_tickers_by_profile'][profile_id] = tickers_for_this_profile_run
                state['failed_tickers_by_profile'][profile_id] = []
                _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "Excel/State", f"Loaded {len(tickers_for_this_profile_run)} tickers from Excel/State.", "info")
            else:
                tickers_for_this_profile_run = pending
                _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "State", f"Resuming with {len(tickers_for_this_profile_run)} pending tickers.", "info")

        if not tickers_for_this_profile_run:
            msg = f"No tickers to process for '{profile_name}' from {source_type}."
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "Skipped - No Tickers", msg, "warning")
            current_run_detailed_logs_for_profile.append({"ticker": "N/A", "status": "Skipped - No Tickers", "message": msg, "generation_timestamp": None, "publication_timestamp": None, "writer_username": None})
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            _active_runs[user_uid][profile_id]["active"] = False; continue

        author_start_index = state.get('last_author_index_by_profile', {}).get(profile_id, -1)
        author_iterator = cycle(authors)
        for _ in range((author_start_index + 1) % len(authors)):
            next(author_iterator)


        last_sched_iso = state.get('last_successful_schedule_time_by_profile', {}).get(profile_id)
        next_schedule_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(1,3))
        if last_sched_iso:
            try:
                last_sched_dt = datetime.fromisoformat(last_sched_iso).replace(tzinfo=timezone.utc)
                min_gap = profile_config.get("min_scheduling_gap_minutes", 45)
                max_gap = profile_config.get("max_scheduling_gap_minutes", 68)
                random_gap = random.randint(min_gap, max_gap)
                next_schedule_time = last_sched_dt + timedelta(minutes=random_gap)
            except:
                pass
        if next_schedule_time < datetime.now(timezone.utc):
            next_schedule_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(2,5))


        published_count_this_profile_run = 0
        total_tickers_for_profile = len(tickers_for_this_profile_run)

        for i, ticker_to_process in enumerate(tickers_for_this_profile_run):
            if _active_runs[user_uid][profile_id].get("stop_requested", False):
                msg = f"Halted by user for {profile_name} before processing ticker '{ticker_to_process}'."; app_logger.info(msg)
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Processing", "Halted", msg, "warning")
                current_run_detailed_logs_for_profile.append({"ticker": ticker_to_process, "status": "Halted", "message": msg, "generation_timestamp": None, "publication_timestamp": None, "writer_username": None})
                break

            if published_count_this_profile_run >= to_attempt:
                app_logger.info(f"Reached target of {to_attempt} posts for profile '{profile_name}' in this run.")
                break
            if state['posts_today_by_profile'].get(profile_id, 0) >= ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP:
                app_logger.info(f"Daily cap of {ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP} reached for profile '{profile_name}'.")
                break
            if ticker_to_process in state.get('published_tickers_log_by_profile', {}).get(profile_id, set()):
                msg = f"Ticker '{ticker_to_process}' already published for '{profile_name}'. Skipping."
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Article", "Skipped", msg, "info")
                current_run_detailed_logs_for_profile.append({"ticker": ticker_to_process, "status": "Skipped - Already Published", "message": msg, "generation_timestamp": None, "publication_timestamp": None, "writer_username": None})
                socketio_instance.emit('ticker_processed_update', {
                    'profile_id': profile_id, 'ticker': ticker_to_process, 'status': "Skipped - Already Published",
                    'generation_time': None, 'publish_time': None, 'writer_username': None
                }, room=user_room)
                continue

            current_author = next(author_iterator)
            state['last_author_index_by_profile'][profile_id] = authors.index(current_author)

            _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Ticker Processing", "Begin", f"Starting {ticker_to_process}", "info")

            gen_time = None; pub_time = None; writer_name = current_author['wp_username']; post_status = "Processing"
            error_message = None

            try:
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Report Gen", "Starting", "Generating content...", "info")
                # The APP_ROOT for generate_wordpress_report is the root of the 'app' directory
                # automation_scripts is one level up from app in this structure, so adjust.
                report_app_root = os.path.join(APP_ROOT, '..', 'app')
                rdata, html_content, css_content = generate_wordpress_report(
                    profile_name,
                    ticker_to_process,
                    report_app_root, # Pass the correct app root for template/static access
                    profile_config.get("report_sections_to_include", list(ALL_REPORT_SECTIONS.keys()))
                )
                gen_time = datetime.now(timezone.utc).isoformat()

                if "Error generating report" in html_content or not html_content or not rdata:
                    error_message = f"Content generation failed for {ticker_to_process}."
                    _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Report Gen", "Failed", error_message, "error")
                    post_status = f"Failed: {error_message}"
                    state.get('failed_tickers_by_profile', {}).setdefault(profile_id, []).append(ticker_to_process)
                else:
                    _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Report Gen", "Done", "Content generated.", "success")
                    post_status = "Generated"

                    socketio_instance.emit('ticker_processed_update', {
                        'profile_id': profile_id, 'ticker': ticker_to_process, 'status': post_status,
                        'generation_time': gen_time, 'publish_time': None, 'writer_username': writer_name,
                        'error_message': error_message
                    }, room=user_room)

                    if _active_runs[user_uid][profile_id].get("stop_requested", False):
                        msg = f"Halted for {profile_name} after generating content for '{ticker_to_process}'."; app_logger.info(msg)
                        _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Processing", "Halted", msg, "warning")
                        current_run_detailed_logs_for_profile.append({"ticker": ticker_to_process, "status": f"Halted - {post_status}", "message": msg, "generation_timestamp": gen_time, "publication_timestamp": None, "writer_username": writer_name})
                        break

                    article_title = generate_dynamic_headline(ticker_to_process, profile_name)
                    feature_img_dir = os.path.join(APP_ROOT, "..", "generated_data", "temp_images", profile_id)
                    os.makedirs(feature_img_dir, exist_ok=True)
                    feature_img_filename = f"{re.sub(r'[^\\w]', '_', ticker_to_process)}_{int(time.time())}.png"
                    feature_img_path = os.path.join(feature_img_dir, feature_img_filename)

                    _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Image Gen", "Generating feature image...", "info")
                    generated_image_path = generate_feature_image(article_title, profile_name, profile_config, feature_img_path, ticker_to_process)
                    wp_media_id = None
                    if generated_image_path:
                        _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Image Upload", "Uploading image...", "info")
                        wp_media_id = upload_image_to_wordpress(generated_image_path, profile_config['site_url'], current_author, article_title)
                        if wp_media_id: _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Image OK", f"Image ID: {wp_media_id}", "success")
                        else: _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Image Fail", "Image upload failed.", "warning")
                        try: os.remove(generated_image_path)
                        except Exception as e_rm: app_logger.error(f"Failed to remove temp image {generated_image_path}: {e_rm}")
                    else: _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Image Fail", "Image gen failed.", "warning")

                    if _active_runs[user_uid][profile_id].get("stop_requested", False):
                        msg = f"Halted for {profile_name} after image processing for '{ticker_to_process}'."; app_logger.info(msg)
                        _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Processing", "Halted", msg, "warning")
                        current_run_detailed_logs_for_profile.append({"ticker": ticker_to_process, "status": "Halted - After Image", "message": msg, "generation_timestamp": gen_time, "publication_timestamp": None, "writer_username": writer_name})
                        break

                    if published_count_this_profile_run > 0:
                        min_gap = profile_config.get("min_scheduling_gap_minutes",45)
                        max_gap = profile_config.get("max_scheduling_gap_minutes",68)
                        next_schedule_time += timedelta(minutes=random.randint(min_gap, max_gap))

                    if next_schedule_time < datetime.now(timezone.utc):
                        next_schedule_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(2,5))

                    _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Scheduling", f"Scheduling for {next_schedule_time.strftime('%H:%M')} by {current_author['wp_username']}", "info")
                    publish_success = create_wordpress_post(profile_config['site_url'], current_author, article_title, html_content, next_schedule_time, profile_config.get('stockforecast_category_id'), wp_media_id)
                    pub_time = datetime.now(timezone.utc).isoformat()

                    if publish_success:
                        state['last_successful_schedule_time_by_profile'][profile_id] = next_schedule_time.isoformat()
                        state['posts_today_by_profile'][profile_id] = state['posts_today_by_profile'].get(profile_id, 0) + 1
                        state.get('published_tickers_log_by_profile', {}).setdefault(profile_id, set()).add(ticker_to_process)
                        published_count_this_profile_run += 1
                        post_status = "Published"
                        _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Scheduled", f"Post for {ticker_to_process} scheduled by {writer_name} at {next_schedule_time.strftime('%H:%M')}.", "success")
                    else:
                        error_message = f"WordPress post creation failed for {ticker_to_process}."
                        _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Failed", error_message, "error")
                        post_status = f"Failed: {error_message}"
                        state.get('failed_tickers_by_profile', {}).setdefault(profile_id, []).append(ticker_to_process)

                current_run_detailed_logs_for_profile.append({
                    "ticker": ticker_to_process, "status": post_status, "message": error_message or f"{post_status} by {writer_name}",
                    "generation_timestamp": gen_time, "publication_timestamp": pub_time if post_status=="Published" else None,
                    "writer_username": writer_name if post_status=="Published" else None
                })
                socketio_instance.emit('ticker_processed_update', {
                    'profile_id': profile_id, 'ticker': ticker_to_process, 'status': post_status,
                    'generation_time': gen_time, 'publish_time': pub_time if post_status=="Published" else None,
                    'writer_username': writer_name if post_status=="Published" else None,
                    'error_message': error_message
                }, room=user_room)

                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process,
                                        "Ticker Processing", "Progress",
                                        f"Processed {i+1}/{total_tickers_for_profile} for {profile_name}.", "info")

                if not _active_runs[user_uid][profile_id].get("stop_requested", False):
                     time.sleep(random.uniform(1, 3))

            except Exception as e_ticker_loop:
                app_logger.error(f"Error processing ticker {ticker_to_process} for profile {profile_name}: {e_ticker_loop}", exc_info=True)
                error_message = f"Error with {ticker_to_process}: {str(e_ticker_loop)[:100]}"
                post_status = f"Failed: {error_message}"
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Ticker Processing", "Error", error_message, "error")
                state.get('failed_tickers_by_profile', {}).setdefault(profile_id, []).append(ticker_to_process)
                current_run_detailed_logs_for_profile.append({
                    "ticker": ticker_to_process, "status": post_status, "message": error_message,
                    "generation_timestamp": gen_time, "publication_timestamp": None, "writer_username": None
                })
                socketio_instance.emit('ticker_processed_update', {
                    'profile_id': profile_id, 'ticker': ticker_to_process, 'status': post_status,
                    'generation_time': gen_time, 'publish_time': None, 'writer_username': None, 'error_message': error_message
                }, room=user_room)

        if not (source_type == "Manual Entry" or source_type == "Uploaded File (Storage)"):
            current_pending = state.get('pending_tickers_by_profile', {}).get(profile_id, [])
            processed_in_this_batch = {log_item['ticker'] for log_item in current_run_detailed_logs_for_profile}
            state['pending_tickers_by_profile'][profile_id] = [t for t in current_pending if t not in processed_in_this_batch]

        if not isinstance(state.get('processed_tickers_detailed_log_by_profile', {}).get(profile_id), list):
            state.setdefault('processed_tickers_detailed_log_by_profile', {})[profile_id] = []
        state['processed_tickers_detailed_log_by_profile'][profile_id].extend(current_run_detailed_logs_for_profile)

        was_halted_profile = _active_runs[user_uid][profile_id].get("stop_requested", False)
        summary_msg = f"Halted by user. Published {published_count_this_profile_run}." if was_halted_profile else f"Finished. Published {published_count_this_profile_run} of {to_attempt} planned. Today's total: {state['posts_today_by_profile'].get(profile_id,0)}."
        _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Profile Processing", "Complete", summary_msg, "warning" if was_halted_profile else "success")
        run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": summary_msg, "tickers_processed": current_run_detailed_logs_for_profile}
        _active_runs[user_uid][profile_id]["active"] = False

    save_state(state)
    _emit_automation_progress(socketio_instance, user_room, "Overall", "N/A", "Completion", "Run Finished", "All selected profiles processed.", "success")
    if user_uid in _active_runs and all(not info.get("active", False) for info in _active_runs[user_uid].values()):
        del _active_runs[user_uid]

    return run_results_summary


if __name__ == '__main__':
    app_logger.info(f"--- Auto Publisher CLI Mode ---")
    cli_profiles = load_profiles_config()
    if not cli_profiles: app_logger.error("No profiles for CLI mode. Exiting."); exit(1)
    articles_map = {p.get('profile_id'): 1 for p in cli_profiles if p.get('profile_id')}

    custom_tickers_sim = {}
    uploaded_files_sim = {}

    # Simulate: first profile uses custom tickers, second uses a (mocked) uploaded file
    if len(cli_profiles) > 0 and cli_profiles[0].get("profile_id"):
        pid1 = cli_profiles[0].get("profile_id")
        custom_tickers_sim[pid1] = ["GOOG", "MSFT"]
        app_logger.info(f"CLI: Simulating custom tickers for profile {pid1}")

    if len(cli_profiles) > 1 and cli_profiles[1].get("profile_id"):
        pid2 = cli_profiles[1].get("profile_id")
        # This would be a conceptual storage path if you were testing actual storage download
        # For now, it's just to show the structure.
        # `load_tickers_from_uploaded_file` would need a mock for CLI if not using real storage.
        uploaded_files_sim[pid2] = {"storage_path": "user_ticker_files/cli_user_standalone/mock_profile_id/cli_test_tickers.csv",
                                    "original_filename": "cli_test_tickers.csv"}
        app_logger.info(f"CLI: Simulating uploaded file for profile {pid2} (path: {uploaded_files_sim[pid2]['storage_path']})")
        # To make this CLI test runnable without actual Firebase Storage, you might need to mock
        # `get_file_content_from_storage` if `load_tickers_from_uploaded_file` calls it.
        # Example mock for get_file_content_from_storage if needed for CLI:
        # def mock_get_file_content_from_storage(storage_path, original_filename):
        # if "cli_test_tickers.csv" in storage_path:
        # return b"Ticker\nNDAQ\nSPY" # Mock CSV content
        # return None
        # global get_file_content_from_storage # if it's a global function
        # get_file_content_from_storage = mock_get_file_content_from_storage


    results = trigger_publishing_run(
        "cli_user_standalone",
        cli_profiles,
        articles_map,
        custom_tickers_by_profile_id=custom_tickers_sim,
        uploaded_file_details_by_profile_id=uploaded_files_sim
    )

    if results:
        for pid, data in results.items():
            app_logger.info(f"Profile {data.get('profile_name',pid)}: {data.get('status_summary','No summary.')}")
            for log_entry in data.get("tickers_processed", []):
                app_logger.info(f"  - Ticker: {log_entry.get('ticker', 'N/A')}, Status: {log_entry.get('status', 'N/A')}, GenTime: {log_entry.get('generation_timestamp', 'N/A')}, PubTime: {log_entry.get('publication_timestamp', 'N/A')}, Writer: {log_entry.get('writer_username', 'N/A')}, Msg: {log_entry.get('message', '')}")
    app_logger.info("--- CLI Run Finished ---")