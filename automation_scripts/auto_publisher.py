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
try:
    from firebase_admin import storage 
except ImportError:
    storage = None 
# --- END: Firebase Admin Storage Import ---

try:
    from app.main_portal_app import get_previous_ticker_status
except ImportError:
    def get_previous_ticker_status(user_uid, profile_id, ticker_symbol):
        return None

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
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True) # Ensure logs directory exists
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

def get_file_content_from_storage(storage_path, original_filename):
    if not storage:
        app_logger.error("Firebase Admin SDK (storage) not available. Cannot download from storage.")
        return None
    if not storage_path:
        app_logger.error(f"No storage path provided for file {original_filename}.")
        return None
    try:
        bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')
        bucket = storage.bucket(bucket_name if bucket_name else None) 
        
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
        'last_author_index_by_profile': lambda: -1,
        'last_processed_ticker_index_by_profile': lambda: -1
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
            specific_env_var = f"{env_prefix}_{var_name}" if env_prefix else var_name # MODIFIED to allow empty env_prefix
            default_env_var_with_default_prefix = f"DEFAULT_{var_name}"
            
            color_val = os.getenv(specific_env_var, os.getenv(default_env_var_with_default_prefix, default_hex))
            source = "env specific" if os.getenv(specific_env_var) else "env default" if os.getenv(default_env_var_with_default_prefix) else "hardcoded"
            app_logger.info(f"[FeatureImage] Color for '{var_name}': '{color_val}' (Source: {source})")
            return color_val

        bg_hex = get_env_color("FEATURE_BG_COLOR", "#0A264E")
        headline_color_hex = get_env_color("FEATURE_HEADLINE_TEXT_COLOR", "#FFFFFF")
        sub_headline_color_hex = get_env_color("FEATURE_SUBTEXT_COLOR", "#E0E0E0")
        watermark_text_color_hex = get_env_color("FEATURE_WATERMARK_TEXT_COLOR", "#A0A0A0")
        right_panel_bg_hex = get_env_color("FEATURE_RIGHT_PANEL_BG_COLOR", "#1C3A6E")
        ticker_text_color_hex = get_env_color("FEATURE_TICKER_TEXT_COLOR", "#FFFFFF")

        resolved_site_logo_path_specific_var = f"{env_prefix}_SITE_LOGO_PATH" if env_prefix else "SITE_LOGO_PATH"
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
                    return ImageFont.truetype("arial.ttf", default_size) # Common fallback
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
                logo_img = logo_img.resize((new_w, new_h), Image.Resampling.LANCZOS) # Updated
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
            # Use textbbox for more accurate width calculation
            if draw.textbbox((0,0), current_line + word, font=font_headline)[2] <= text_area_width:
                current_line += word + " "
            else:
                lines.append(current_line.strip()); current_line = word + " "
        lines.append(current_line.strip())
        for line in lines:
            # Use textbbox for height and correct drawing
            text_box = draw.textbbox((text_area_left_margin, current_y), line, font=font_headline, anchor="lt")
            line_height = text_box[3] - text_box[1]
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
    except ImportError: app_logger.error("Pillow (PIL) not installed or ImageFont.truetype failed."); return None # Added check for truetype
    except Exception as e: app_logger.error(f"Feature image error for '{headline_text}': {e}", exc_info=True); return None


def upload_image_to_wordpress(image_path, site_url, author, title="Featured Image"):
    if not image_path or not os.path.exists(image_path): return None
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/media"
    creds = base64.b64encode(f"{author['wp_username']}:{author['app_password']}".encode()).decode('utf-8')
    filename = os.path.basename(image_path)
    headers = {"Authorization": f"Basic {creds}", "Content-Disposition": f'attachment; filename="{filename}"'}
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (filename, f, 'image/png')} # Assuming PNG, adjust if other types
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
        response.raise_for_status(); 
        post_id = response.json().get('id')
        app_logger.info(f"Post '{title}' scheduled on {site_url}. ID: {post_id}")
        return post_id # MODIFIED: Return post ID
    except Exception as e: app_logger.error(f"WP post error for '{title}' on {site_url}: {e}"); return None # MODIFIED: Return None on error


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

def load_tickers_from_uploaded_file(storage_path, original_filename, user_uid=None, profile_id=None):
    app_logger.info(f"Attempting to load tickers from storage: '{storage_path}' (original: '{original_filename}') for profile {profile_id}, user {user_uid}.")
    global get_file_content_from_storage
    _original_get_file_content_from_storage = get_file_content_from_storage # Save original

    def cli_mock_get_file_content_from_storage(storage_path, original_filename):
        # If storage_path in CLI mode is a local path to the dummy file
        if os.path.exists(storage_path): # Check if it's a direct local path
            try:
                with open(storage_path, "rb") as f_local:
                    app_logger.info(f"[CLI_MOCK_STORAGE] Reading local file: {storage_path}")
                    return f_local.read()
            except Exception as e_local_read:
                app_logger.error(f"[CLI_MOCK_STORAGE] Error reading local file {storage_path}: {e_local_read}")
                return None
        return _original_get_file_content_from_storage(storage_path, original_filename) # Fallback

    get_file_content_from_storage = cli_mock_get_file_content_from_storage

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
    # Example: customize prefix based on profile_name
    if "Forecast" in profile_name or "Radar" in profile_name or "MoneyStocker" in profile_name: # Added MoneyStocker
        site_specific_prefix = f"{ticker} Stock Forecast: "
    elif "Bernini" in profile_name:
        site_specific_prefix = f"{ticker} Analysis by Bernini Capital: "
    
    base_headlines = [
        f"Is {ticker} a Smart Investment Now?",
        f"{ticker} Stock Deep Dive: Price Prediction & Analysis",
        f"Future of {ticker}: Expert Analysis and Forecast", # This was selected in logs
        f"Should You Buy {ticker} Stock? A detailed Review"
    ]
    # If no specific prefix, one of the base headlines might be chosen directly by other logic
    # This function provides a prefix if applicable, or the caller can use base headlines.
    # For the log example "Future of AMED: Expert Analysis and Forecast", this implies ticker was AMED
    # and one of the base_headlines was selected.
    if site_specific_prefix: #Only return prefixed if site_specific_prefix is non-empty
        return site_specific_prefix + random.choice(base_headlines)
    return random.choice(base_headlines) # Fallback to a random base if no prefix


_active_runs = {}

def stop_publishing_run(user_uid, profile_id):
    global _active_runs
    if user_uid in _active_runs and profile_id in _active_runs[user_uid]:
        _active_runs[user_uid][profile_id]["stop_requested"] = True
        app_logger.info(f"Stop request registered for profile {profile_id} (User: {user_uid})")
        return {'success': True, 'message': 'Stop request received. The process will halt after the current ticker.'}
    app_logger.warning(f"No active run found to stop for profile {profile_id} (User: {user_uid})")
    return {'success': False, 'message': 'No active run found for this profile to stop.'}


def trigger_publishing_run(user_uid, profiles_to_process_data_list, articles_to_publish_per_profile_map,
                           custom_tickers_by_profile_id=None, uploaded_file_details_by_profile_id=None, 
                           socketio_instance=None, user_room=None, save_status_callback=None): # MODIFIED: Added save_status_callback
    global _active_runs
    if user_uid not in _active_runs: _active_runs[user_uid] = {}
    for profile_config in profiles_to_process_data_list:
        profile_id = profile_config.get("profile_id")
        if profile_id: _active_runs[user_uid][str(profile_id)] = {"active": True, "stop_requested": False} # Ensure profile_id is string key

    _emit_automation_progress(socketio_instance, user_room, "Overall", "N/A", "Initialization", "Run Started", f"Processing {len(profiles_to_process_data_list)} profiles.", "info")
    profile_ids_for_run = [p.get("profile_id") for p in profiles_to_process_data_list if p.get("profile_id")]
    state = load_state(user_uid=user_uid, current_profile_ids_from_run=profile_ids_for_run)
    run_results_summary = {}

    for profile_config in profiles_to_process_data_list:
        profile_id = str(profile_config.get("profile_id")) # Ensure string key
        profile_name = profile_config.get("profile_name", profile_id)
        current_run_detailed_logs_for_profile = []

        _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Profile Processing", "Starting", f"Processing profile: {profile_name}", "info")
        if not profile_id: continue
        if _active_runs[user_uid][profile_id].get("stop_requested", False):
            msg = f"Halted by user: {profile_name}"; 
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Processing", "Halted", msg, "warning")
            # NEW: Call save_status_callback for halt if needed (assuming N/A ticker for profile-level halt)
            if save_status_callback:
                status_data = {'status': "Halted (Profile Level)", 'generated_at': None, 'published_at': None, 'writer_username': None}
                save_status_callback(user_uid, profile_id, "N/A_PROFILE_HALT", status_data) # Use a special ticker
            current_run_detailed_logs_for_profile.append({"ticker": "N/A", "status": "Halted", "message": msg, "generated_at": None, "published_at": None, "writer_username": None})
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            _active_runs[user_uid][profile_id]["active"] = False; continue

        authors = profile_config.get('authors', [])
        if not authors:
            msg = f"No authors for '{profile_name}'. Skipping."; 
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Setup", "Skipped", msg, "warning")
            # NEW: Call save_status_callback
            if save_status_callback:
                status_data = {'status': "Skipped - No Authors", 'generated_at': None, 'published_at': None, 'writer_username': None}
                save_status_callback(user_uid, profile_id, "N/A_NO_AUTHORS", status_data)
            current_run_detailed_logs_for_profile.append({"ticker": "N/A", "status": "Skipped - No Authors", "message": msg, "generated_at": None, "published_at": None, "writer_username": None})
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            _active_runs[user_uid][profile_id]["active"] = False; continue

        posts_today = state['posts_today_by_profile'].get(profile_id, 0)
        requested_posts = articles_to_publish_per_profile_map.get(profile_id, 0)
        can_publish = ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP - posts_today
        to_attempt = min(requested_posts, can_publish)

        if to_attempt <= 0:
            msg = f"Limit reached for '{profile_name}'. Today: {posts_today}/{ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP}, Req: {requested_posts}"
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Setup", "Skipped - Limit", msg, "info")
            # NEW: Call save_status_callback
            if save_status_callback:
                status_data = {'status': "Skipped - Daily Limit", 'generated_at': None, 'published_at': None, 'writer_username': None}
                save_status_callback(user_uid, profile_id, "N/A_DAILY_LIMIT", status_data)
            current_run_detailed_logs_for_profile.append({"ticker": "N/A", "status": "Skipped - Daily Limit", "message": msg, "generated_at": None, "published_at": None, "writer_username": None})
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            _active_runs[user_uid][profile_id]["active"] = False; continue
        _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Setup", "Post Count", f"Attempting {to_attempt} posts for {profile_name}.", "info")

        tickers_for_this_profile_run = []
        source_type = "Excel/State (Default)"

        if custom_tickers_by_profile_id and profile_id in custom_tickers_by_profile_id and custom_tickers_by_profile_id[profile_id]:
            tickers_for_this_profile_run = custom_tickers_by_profile_id[profile_id]
            source_type = "Manual Entry"
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "Custom", f"Processing {len(tickers_for_this_profile_run)} custom tickers.", "info")
            last_processed_index = -1
            initial_last_processed_index_for_file = -1
            total_items_in_file = 0
        elif uploaded_file_details_by_profile_id and profile_id in uploaded_file_details_by_profile_id:
            f_details = uploaded_file_details_by_profile_id[profile_id]
            storage_path = f_details.get("storage_path")
            original_filename = f_details.get("original_filename")
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "File", f"Reading tickers from '{original_filename}' (from storage).", "info")
            all_tickers = load_tickers_from_uploaded_file(storage_path, original_filename, user_uid, profile_id)
            source_type = "Uploaded File (Storage)"
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "File", f"Found {len(all_tickers)} tickers in file from storage.", "info")
            last_processed_index = state.get('last_processed_ticker_index_by_profile', {}).get(profile_id, -1)
            initial_last_processed_index_for_file = last_processed_index
            tickers_for_this_profile_run = all_tickers[last_processed_index+1:] if last_processed_index+1 < len(all_tickers) else []
            total_items_in_file = profile_config.get('ticker_count_from_file', len(all_tickers))
            if total_items_in_file == 0 and len(all_tickers) > 0:
                total_items_in_file = len(all_tickers)
        else:
            pending = state['pending_tickers_by_profile'].get(profile_id, [])
            if not pending:
                excel_tickers = load_tickers_from_excel(profile_config)
                failed = list(state['failed_tickers_by_profile'].get(profile_id, []))
                published_log_set = state['published_tickers_log_by_profile'].get(profile_id, set())
                current_tickers_set = set(tickers_for_this_profile_run)
                tickers_from_excel_state = [t for t in failed + excel_tickers if t not in published_log_set and t not in current_tickers_set]
                tickers_for_this_profile_run.extend(tickers_from_excel_state)
                state['pending_tickers_by_profile'][profile_id] = tickers_for_this_profile_run
                state['failed_tickers_by_profile'][profile_id] = []
                _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "Excel/State", f"Loaded {len(tickers_for_this_profile_run)} tickers from Excel/State.", "info")
            else:
                tickers_for_this_profile_run = pending
                _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "State", f"Resuming with {len(tickers_for_this_profile_run)} pending tickers.", "info")
            last_processed_index = -1
            initial_last_processed_index_for_file = -1
            total_items_in_file = profile_config.get('ticker_count_from_file', 0)


        if not tickers_for_this_profile_run:
            msg = f"No tickers to process for '{profile_name}' from {source_type}."
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "Skipped - No Tickers", msg, "warning")
            # NEW: Call save_status_callback
            if save_status_callback:
                status_data = {'status': "Skipped - No Tickers", 'generated_at': None, 'published_at': None, 'writer_username': None}
                save_status_callback(user_uid, profile_id, "N/A_NO_TICKERS", status_data)
            current_run_detailed_logs_for_profile.append({"ticker": "N/A", "status": "Skipped - No Tickers", "message": msg, "generated_at": None, "published_at": None, "writer_username": None})
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
            except: pass
        if next_schedule_time < datetime.now(timezone.utc):
            next_schedule_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(2,5))


        published_count_this_profile_run = 0
        total_tickers_for_profile = len(tickers_for_this_profile_run)

        for i, ticker_to_process in enumerate(tickers_for_this_profile_run):
            gen_time_iso = None; pub_time_iso = None; writer_name = None; final_post_status = "Processing" # Default
            error_message_for_log = None # For detailed log
            
            if _active_runs[user_uid][profile_id].get("stop_requested", False):
                msg = f"Halted by user for {profile_name} before processing ticker '{ticker_to_process}'."; app_logger.info(msg)
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Processing", "Halted", msg, "warning")
                final_post_status = "Halted"
                # NEW: Call save_status_callback for this ticker
                if save_status_callback and final_post_status == "Scheduled":
                    status_data_for_persistence = {
                        'status': final_post_status,
                        'generated_at': gen_time_iso,
                        'published_at': pub_time_iso,
                        'writer_username': writer_name,
                        'message_log': error_message_for_log
                    }
                    app_logger.info(f"[SAVE_CALLBACK] Attempting to save status for ticker {ticker_to_process} (Profile: {profile_id}): {status_data_for_persistence}")
                    try:
                        save_status_callback(user_uid, profile_id, ticker_to_process, status_data_for_persistence)
                    except Exception as e_cb_call:
                        app_logger.error(f"Error during save_status_callback for {ticker_to_process}: {e_cb_call}", exc_info=True)
                # Always append log before break
                current_run_detailed_logs_for_profile.append({
                    "ticker": ticker_to_process, "status": final_post_status, "message": msg, "generated_at": gen_time_iso, "published_at": pub_time_iso, "writer_username": writer_name
                })
                break

            if published_count_this_profile_run >= to_attempt:
                app_logger.info(f"Reached target of {to_attempt} posts for profile '{profile_name}' in this run.")
                # Always append log before break
                current_run_detailed_logs_for_profile.append({
                    "ticker": ticker_to_process, "status": "Limit Reached", "message": f"Reached post limit for this run.", "generated_at": gen_time_iso, "published_at": pub_time_iso, "writer_username": writer_name
                })
                break
            if state['posts_today_by_profile'].get(profile_id, 0) >= ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP:
                app_logger.info(f"Daily cap of {ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP} reached for profile '{profile_name}'.")
                # Always append log before break
                current_run_detailed_logs_for_profile.append({
                    "ticker": ticker_to_process, "status": "Daily Cap Reached", "message": f"Daily cap reached for this profile.", "generated_at": gen_time_iso, "published_at": pub_time_iso, "writer_username": writer_name
                })
                break 
            
            # Ensure published_tickers_log_by_profile and its sub-dict/set exist
            state.setdefault('published_tickers_log_by_profile', {}).setdefault(profile_id, set())
            if ticker_to_process in state['published_tickers_log_by_profile'][profile_id]:
                msg = f"Ticker '{ticker_to_process}' already published for '{profile_name}'. Skipping."
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Article", "Skipped", msg, "info")
                final_post_status = "Skipped - Already Published"
                # Fetch previous status for this ticker
                previous_status = None
                if save_status_callback:
                    previous_status = get_previous_ticker_status(user_uid, profile_id, ticker_to_process)
                gen_time_val = previous_status.get('generated_at') if previous_status else None
                pub_time_val = previous_status.get('published_at') if previous_status else None
                writer_val = previous_status.get('writer_username') if previous_status else None
                # NEW: Call save_status_callback
                if save_status_callback:
                    status_data = {'status': final_post_status, 'generated_at': gen_time_val, 'published_at': pub_time_val, 'writer_username': writer_val}
                    app_logger.info(f"[SAVE_CALLBACK] Pre-call for {ticker_to_process} (Skipped - Already Published): {status_data}")
                    save_status_callback(user_uid, profile_id, ticker_to_process, status_data)
                current_run_detailed_logs_for_profile.append({"ticker": ticker_to_process, "status": final_post_status, "message": msg, "generated_at": gen_time_val, "published_at": pub_time_val, "writer_username": writer_val})
                socketio_instance.emit('ticker_processed_update', { # This is for progress bar
                    'profile_id': profile_id, 'ticker': ticker_to_process, 'status': final_post_status,
                    'generated_at': gen_time_val, 'published_at': pub_time_val, 'writer_username': writer_val
                }, room=user_room)
                continue

            current_author = next(author_iterator)
            state['last_author_index_by_profile'][profile_id] = authors.index(current_author)
            writer_name = current_author['wp_username']

            _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Ticker Processing", "Begin", f"Starting {ticker_to_process}", "info")

            try:
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Report Gen", "Starting", "Generating content...", "info")
                report_app_root = os.path.join(APP_ROOT, '..', 'app')
                rdata, html_content, css_content = generate_wordpress_report(
                    profile_name, ticker_to_process, report_app_root, 
                    profile_config.get("report_sections_to_include", list(ALL_REPORT_SECTIONS.keys()))
                )
                gen_time_iso = datetime.now(timezone.utc).isoformat()

                if "Error generating report" in html_content or not html_content or not rdata:
                    error_message_for_log = f"Content generation failed for {ticker_to_process}."
                    _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Report Gen", "Failed", error_message_for_log, "error")
                    final_post_status = f"Failed: Content Gen"
                    state.get('failed_tickers_by_profile', {}).setdefault(profile_id, []).append(ticker_to_process)
                else:
                    _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Report Gen", "Done", "Content generated.", "success")
                    final_post_status = "Generated" # Intermediate status

                    socketio_instance.emit('ticker_processed_update', { # For progress bar
                        'profile_id': profile_id, 'ticker': ticker_to_process, 'status': final_post_status,
                        'generated_at': gen_time_iso, 'published_at': None, 'writer_username': writer_name
                    }, room=user_room)

                    if _active_runs[user_uid][profile_id].get("stop_requested", False):
                        msg = f"Halted for {profile_name} after generating content for '{ticker_to_process}'."; app_logger.info(msg)
                        _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Processing", "Halted", msg, "warning")
                        final_post_status = "Halted - After Gen"
                        # Always append log before break
                        current_run_detailed_logs_for_profile.append({
                            "ticker": ticker_to_process, "status": final_post_status, "message": msg, "generated_at": gen_time_iso, "published_at": pub_time_iso, "writer_username": writer_name
                        })
                        break 

                    article_title = generate_dynamic_headline(ticker_to_process, profile_name)
                    feature_img_dir = os.path.join(APP_ROOT, "..", "generated_data", "temp_images", profile_id)
                    os.makedirs(feature_img_dir, exist_ok=True)
                    sanitized_ticker = re.sub(r'[^\w]', '_', ticker_to_process)
                    feature_img_filename = f"{sanitized_ticker}_{int(time.time())}.png"
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
                        final_post_status = "Halted - After Image"
                        # Always append log before break
                        current_run_detailed_logs_for_profile.append({
                            "ticker": ticker_to_process, "status": final_post_status, "message": msg, "generated_at": gen_time_iso, "published_at": pub_time_iso, "writer_username": writer_name
                        })
                        break 

                    if published_count_this_profile_run > 0: # Adjust schedule time for subsequent posts
                        min_gap = profile_config.get("min_scheduling_gap_minutes",45)
                        max_gap = profile_config.get("max_scheduling_gap_minutes",68)
                        next_schedule_time += timedelta(minutes=random.randint(min_gap, max_gap))
                    
                    # Ensure next schedule time is in the future
                    if next_schedule_time < datetime.now(timezone.utc):
                        next_schedule_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(2,5))

                    _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Scheduling", f"Scheduling for {next_schedule_time.strftime('%H:%M')} by {writer_name}", "info")
                    
                    # create_wordpress_post now returns post_id or None
                    created_post_id = create_wordpress_post(profile_config['site_url'], current_author, article_title, html_content, next_schedule_time, profile_config.get('stockforecast_category_id'), wp_media_id)
                    
                    if created_post_id: # If post creation was successful
                        pub_time_iso = next_schedule_time.isoformat() # Use scheduled time as publish time
                        state['last_successful_schedule_time_by_profile'][profile_id] = pub_time_iso
                        state['posts_today_by_profile'][profile_id] = state['posts_today_by_profile'].get(profile_id, 0) + 1
                        state['published_tickers_log_by_profile'].setdefault(profile_id, set()).add(ticker_to_process)
                        published_count_this_profile_run += 1
                        final_post_status = "Scheduled" # MODIFIED: Status is Scheduled, not Published immediately
                        _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Scheduled", f"Post for {ticker_to_process} scheduled by {writer_name} for {next_schedule_time.strftime('%Y-%m-%d %H:%M')}. WP ID: {created_post_id}", "success")
                        
                        # NEW: Save status after successful scheduling
                        if save_status_callback:
                            status_data = {
                                'status': final_post_status,
                                'generated_at': gen_time_iso,
                                'published_at': pub_time_iso,
                                'writer_username': writer_name,
                                'message_log': f"Scheduled for {next_schedule_time.strftime('%Y-%m-%d %H:%M')} by {writer_name}"
                            }
                            app_logger.info(f"[SAVE_CALLBACK] Saving status for successfully scheduled ticker {ticker_to_process}: {status_data}")
                            try:
                                save_status_callback(user_uid, profile_id, ticker_to_process, status_data)
                            except Exception as e_cb:
                                app_logger.error(f"Error saving status for scheduled ticker {ticker_to_process}: {e_cb}", exc_info=True)
                        
                        # Update last_processed_ticker_index_by_profile
                        if uploaded_file_details_by_profile_id and profile_id in uploaded_file_details_by_profile_id:
                            # Only update for file-based runs
                            if 'last_processed_ticker_index_by_profile' not in state:
                                state['last_processed_ticker_index_by_profile'] = {}
                            # The index in all_tickers is last_processed_index + i + 1 (i is loop index in tickers_for_this_profile_run)
                            state['last_processed_ticker_index_by_profile'][profile_id] = last_processed_index + i + 1
                            save_state(state)
                    else:
                        error_message_for_log = f"WordPress post creation failed for {ticker_to_process}."
                        _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Publishing", "Failed", error_message_for_log, "error")
                        final_post_status = f"Failed: WP Post"
                        state.get('failed_tickers_by_profile', {}).setdefault(profile_id, []).append(ticker_to_process)
                        
                        # NEW: Save status for failed case
                        if save_status_callback:
                            status_data = {
                                'status': final_post_status,
                                'generated_at': gen_time_iso,
                                'published_at': None,
                                'writer_username': None,
                                'message_log': error_message_for_log
                            }
                            app_logger.info(f"[SAVE_CALLBACK] Saving status for failed ticker {ticker_to_process}: {status_data}")
                            try:
                                save_status_callback(user_uid, profile_id, ticker_to_process, status_data)
                            except Exception as e_cb:
                                app_logger.error(f"Error saving status for failed ticker {ticker_to_process}: {e_cb}", exc_info=True)

            except Exception as e_ticker_loop:
                app_logger.error(f"Error processing ticker {ticker_to_process} for profile {profile_name}: {e_ticker_loop}", exc_info=True)
                error_message_for_log = f"Error with {ticker_to_process}: {str(e_ticker_loop)[:100]}"
                final_post_status = f"Failed: {error_message_for_log}"
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process, "Ticker Processing", "Error", error_message_for_log, "error")
                state.get('failed_tickers_by_profile', {}).setdefault(profile_id, []).append(ticker_to_process)
                
                # NEW: Save status for exception case
                if save_status_callback:
                    status_data = {
                        'status': final_post_status,
                        'generated_at': gen_time_iso,
                        'published_at': None,
                        'writer_username': None,
                        'message_log': error_message_for_log
                    }
                    app_logger.info(f"[SAVE_CALLBACK] Saving status for error ticker {ticker_to_process}: {status_data}")
                    try:
                        save_status_callback(user_uid, profile_id, ticker_to_process, status_data)
                    except Exception as e_cb:
                        app_logger.error(f"Error saving status for error ticker {ticker_to_process}: {e_cb}", exc_info=True)
            
            # Log and save status regardless of outcome inside the loop
            current_run_detailed_logs_for_profile.append({
                "ticker": ticker_to_process, "status": final_post_status, "message": error_message_for_log or f"{final_post_status} by {writer_name}",
                "generated_at": gen_time_iso, "published_at": pub_time_iso if final_post_status=="Scheduled" else None, # Use pub_time_iso
                "writer_username": writer_name if final_post_status=="Scheduled" else None # Only log writer if successfully scheduled
            })
            
            # Calculate current progress for event emission (for attractive progress bar)
            current_overall_item_index_0_based = initial_last_processed_index_for_file + 1 + i
            processed_item_count_for_event = current_overall_item_index_0_based + 1
            # Emit 'ticker_processed_update' for the attractive progress bar (file-based runs only)
            if socketio_instance and user_room and total_items_in_file > 0:
                event_payload_for_attractive_bar = {
                    'profile_id': profile_id,
                    'last_processed_index': processed_item_count_for_event,
                    'total_count': total_items_in_file
                }
                socketio_instance.emit('ticker_processed_update', event_payload_for_attractive_bar, room=user_room)

            _emit_automation_progress(socketio_instance, user_room, profile_id, ticker_to_process,
                                    "Ticker Processing", "Progress",
                                    f"Processed {i+1}/{total_tickers_for_profile} for {profile_name}.", "info")

            if not _active_runs[user_uid][profile_id].get("stop_requested", False):
                 time.sleep(random.uniform(1, 3)) # Small delay between tickers if not stopping

        # After loop for a profile finishes or breaks
        if not (source_type == "Manual Entry" or source_type == "Uploaded File (Storage)"): # Only manage pending list for Excel/State
            current_pending = state.get('pending_tickers_by_profile', {}).get(profile_id, [])
            processed_in_this_batch = {log_item['ticker'] for log_item in current_run_detailed_logs_for_profile}
            state['pending_tickers_by_profile'][profile_id] = [t for t in current_pending if t not in processed_in_this_batch]

        # Ensure the log list exists before extending
        state.setdefault('processed_tickers_detailed_log_by_profile', {}).setdefault(profile_id, [])
        state['processed_tickers_detailed_log_by_profile'][profile_id].extend(current_run_detailed_logs_for_profile)

        was_halted_profile = _active_runs[user_uid][profile_id].get("stop_requested", False)
        summary_msg = f"Halted by user. Published/Scheduled {published_count_this_profile_run}." if was_halted_profile else f"Finished. Published/Scheduled {published_count_this_profile_run} of {to_attempt} planned. Today's total for profile: {state['posts_today_by_profile'].get(profile_id,0)}."
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
    
    def cli_mock_save_status_callback(user_uid, profile_id, ticker_symbol, status_data):
        app_logger.info(f"[CLI_CALLBACK] User: {user_uid}, Profile: {profile_id}, Ticker: {ticker_symbol}, Status Data: {status_data}")

    if len(cli_profiles) > 0 and cli_profiles[0].get("profile_id"):
        pid1 = cli_profiles[0].get("profile_id")
        custom_tickers_sim[pid1] = ["GOOG", "MSFT"]
        app_logger.info(f"CLI: Simulating custom tickers for profile {pid1}")

    if len(cli_profiles) > 1 and cli_profiles[1].get("profile_id"):
        pid2 = cli_profiles[1].get("profile_id")
        # Create a dummy CSV file for CLI testing of load_tickers_from_uploaded_file
        dummy_csv_content = "Ticker\nNDAQ\nSPY"
        dummy_csv_path = os.path.join(APP_ROOT, "..", "generated_data", "temp_uploads", "cli_test_tickers.csv")
        os.makedirs(os.path.dirname(dummy_csv_path), exist_ok=True)
        with open(dummy_csv_path, "w") as f_dummy:
            f_dummy.write(dummy_csv_content)
        
        # For CLI, get_file_content_from_storage needs to be able to read this local dummy file
        # This requires mocking or adjusting get_file_content_from_storage if storage SDK is not fully available/mocked for local files.
        # Let's assume for CLI, 'storage_path' can be a local path that load_tickers_from_uploaded_file can handle if get_file_content_from_storage is adapted.
        # OR, we adjust load_tickers_from_uploaded_file to also accept local paths for CLI mode.

        # For simplicity in CLI, let's assume load_tickers_from_uploaded_file can handle a local path if storage_path points to it.
        # This might need a temporary mock of get_file_content_from_storage for CLI.
        
        results = trigger_publishing_run(
            "cli_user_standalone",
            cli_profiles,
            articles_map,
            custom_tickers_by_profile_id=custom_tickers_sim,
            uploaded_file_details_by_profile_id=uploaded_files_sim,
            save_status_callback=cli_mock_save_status_callback # MODIFIED: Pass mock callback for CLI
        )

        if results:
            for pid, data in results.items():
                app_logger.info(f"Profile {data.get('profile_name',pid)}: {data.get('status_summary','No summary.')}")
                for log_entry in data.get("tickers_processed", []):
                    app_logger.info(f"  - Ticker: {log_entry.get('ticker', 'N/A')}, Status: {log_entry.get('status', 'N/A')}, GenTime: {log_entry.get('generated_at', 'N/A')}, PubTime: {log_entry.get('published_at', 'N/A')}, Writer: {log_entry.get('writer_username', 'N/A')}, Msg: {log_entry.get('message', '')}")
        app_logger.info("--- CLI Run Finished ---")