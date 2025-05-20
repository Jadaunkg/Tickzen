import pandas as pd
import time
from datetime import datetime, timedelta, timezone # Added timezone
import os
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
import io # For handling in-memory file objects for custom uploads

load_dotenv()

try:
    # Expects new signature: generate_wordpress_report(profile_name, ticker, app_root, report_sections_to_include)
    from wordpress_reporter import generate_wordpress_report, ALL_REPORT_SECTIONS
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

# --- Logging Setup ---
LOG_FILE = "auto_publisher.log"
app_logger = logging.getLogger("AutoPublisherLogger")
if not app_logger.handlers:
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    APP_ROOT_PATH_FOR_LOG = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(APP_ROOT_PATH_FOR_LOG, LOG_FILE)
    handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(APP_ROOT, "wordpress_publisher_state_v11.pkl")
PROFILES_CONFIG_FILE = os.path.join(APP_ROOT, "profiles_config.json") # Used by CLI mode

FRED_API_KEY = os.getenv("FRED_API_KEY")
ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP = int(os.getenv("MAX_POSTS_PER_DAY_PER_SITE", "20"))

SITES_PROFILES_CONFIG = [] # Primarily for CLI mode now

def load_profiles_config(): # For CLI mode
    global SITES_PROFILES_CONFIG
    if not os.path.exists(PROFILES_CONFIG_FILE):
        app_logger.warning(f"{PROFILES_CONFIG_FILE} not found. No site profiles loaded for CLI mode.")
        SITES_PROFILES_CONFIG = []
        return SITES_PROFILES_CONFIG
    try:
        with open(PROFILES_CONFIG_FILE, 'r', encoding='utf-8') as f:
            SITES_PROFILES_CONFIG = json.load(f) # This will be a list of profile dicts
        app_logger.info(f"Successfully loaded {len(SITES_PROFILES_CONFIG)} site profiles from {PROFILES_CONFIG_FILE} for CLI mode.")
    except json.JSONDecodeError:
        app_logger.error(f"Error decoding JSON from {PROFILES_CONFIG_FILE}. Please check its format.")
        SITES_PROFILES_CONFIG = []
    except Exception as e:
        app_logger.error(f"Failed to load {PROFILES_CONFIG_FILE}: {e}")
        SITES_PROFILES_CONFIG = []
    return SITES_PROFILES_CONFIG


def load_state(user_uid=None, current_profile_ids_from_run=None):
    """
    Loads the state of the publisher.
    If current_profile_ids_from_run is provided, ensures state entries exist for these profiles.
    Otherwise, relies on SITES_PROFILES_CONFIG (from JSON, for CLI) to determine relevant profiles.
    """
    app_logger.info(f"load_state called. user_uid: {user_uid}, current_profile_ids_from_run: {current_profile_ids_from_run}")
    active_profile_ids = set()
    if current_profile_ids_from_run:
        active_profile_ids.update(str(pid) for pid in current_profile_ids_from_run if pid)
    else: # Fallback for CLI or general state loading without specific runtime profiles
        if not SITES_PROFILES_CONFIG and os.path.exists(PROFILES_CONFIG_FILE):
            load_profiles_config() # Load from JSON for CLI
        for profile in SITES_PROFILES_CONFIG:
            if profile.get("profile_id"):
                active_profile_ids.add(str(profile.get("profile_id")))
    
    app_logger.info(f"Active profile IDs for state management: {active_profile_ids}")

    # Define default structure for new state entries
    default_factories = {
        'pending_tickers_by_profile': list,
        'failed_tickers_by_profile': list,
        'last_successful_schedule_time_by_profile': lambda: None,
        'posts_today_by_profile': lambda: 0,
        'published_tickers_log_by_profile': set,
        'processed_tickers_detailed_log_by_profile': list,
        'last_author_index_by_profile': lambda: -1
    }

    # Initialize default state structure for all active profiles
    default_state = {key: {pid: factory() for pid in active_profile_ids} for key, factory in default_factories.items()}
    default_state['last_run_date'] = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'rb') as f:
                state = pickle.load(f)
            app_logger.info(f"Loaded state from {STATE_FILE}")

            # Ensure all keys from default_factories exist in the loaded state
            for key, factory in default_factories.items():
                if key not in state:
                    state[key] = {pid: factory() for pid in active_profile_ids}
                    app_logger.info(f"Initialized new state key '{key}'.")
                else: # Key exists, ensure all active profiles have entries
                    for pid in active_profile_ids:
                        if pid not in state[key]:
                            state[key][pid] = factory()
                            app_logger.info(f"Initialized state for new profile '{pid}' in existing key '{key}'.")
            
            # Prune obsolete profiles from state if not in active_profile_ids (ONLY if not a targeted run)
            if current_profile_ids_from_run is None: # This means it's a general load, e.g., CLI
                for key in default_factories.keys():
                    if key in state:
                        state_pids_to_remove = [spid for spid in state[key] if spid not in active_profile_ids]
                        for spid_del in state_pids_to_remove:
                            del state[key][spid_del]
                            app_logger.info(f"Removed obsolete profile '{spid_del}' from state key '{key}'.")

            # Daily reset logic
            if state.get('last_run_date') != datetime.now(timezone.utc).strftime('%Y-%m-%d'):
                app_logger.info(f"New day detected ({datetime.now(timezone.utc).strftime('%Y-%m-%d')}). Resetting daily counts for relevant profiles.")
                # Iterate over profiles known to the state at the moment of reset
                for pid_in_state in list(state.get('posts_today_by_profile', {}).keys()):
                    state['posts_today_by_profile'][pid_in_state] = 0
                for pid_in_state in list(state.get('processed_tickers_detailed_log_by_profile', {}).keys()):
                     state['processed_tickers_detailed_log_by_profile'][pid_in_state] = []
                state['last_run_date'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # Ensure all currently active profiles have entries for daily resettable fields, even if state was loaded
            for pid in active_profile_ids:
                state.setdefault('posts_today_by_profile', {})[pid] = state.get('posts_today_by_profile', {}).get(pid, 0)
                state.setdefault('processed_tickers_detailed_log_by_profile', {})[pid] = state.get('processed_tickers_detailed_log_by_profile', {}).get(pid, [])


            return state
        except Exception as e:
            app_logger.warning(f"Could not load or process state file '{STATE_FILE}': {e}. Using default state.", exc_info=True)
            # default_state is already initialized for active_profile_ids
            save_state(default_state) # Save a clean default state
            return default_state
    else:
        app_logger.info(f"No state file at {STATE_FILE}. Initializing default state for active profiles.")
        save_state(default_state)
        return default_state

def save_state(state):
    try:
        with open(STATE_FILE, 'wb') as f:
            pickle.dump(state, f)
        app_logger.info(f"Saved state to {STATE_FILE}")
    except Exception as e:
        app_logger.error(f"Could not save state to {STATE_FILE}: {e}", exc_info=True)


# --- Feature Image, WP Interaction, Headline functions ---
# (These functions: generate_feature_image, upload_image_to_wordpress, create_wordpress_post, generate_dynamic_headline remain largely the same)
# Ensure they exist and are correctly implemented as in your previous version.
def generate_feature_image(headline_text, site_display_name_for_wm, profile_config_entry, output_path):
    app_logger.info(f"Generating feature image for '{site_display_name_for_wm}': '{headline_text}' -> {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        from PIL import Image, ImageDraw, ImageFont
        img_width = int(os.getenv("FEATURE_IMAGE_WIDTH", 1200))
        img_height = int(os.getenv("FEATURE_IMAGE_HEIGHT", 630))
        
        env_prefix_for_colors = profile_config_entry.get('env_prefix_for_feature_image_colors', 'DEFAULT')
        bg_hex = os.getenv(f"{env_prefix_for_colors}_FEATURE_BG_COLOR", os.getenv("DEFAULT_FEATURE_BG_COLOR","#F0F0F0"))
        txt_hex = os.getenv(f"{env_prefix_for_colors}_FEATURE_TEXT_COLOR", os.getenv("DEFAULT_FEATURE_TEXT_COLOR","#333333"))
        wm_hex = os.getenv(f"{env_prefix_for_colors}_FEATURE_WATERMARK_COLOR", os.getenv("DEFAULT_FEATURE_WATERMARK_COLOR","#AAAAAA80"))

        def hex_to_rgba(hex_color_str, default_alpha=255):
            h_str = (hex_color_str or "").lstrip('#')
            try:
                if len(h_str) == 6: return tuple(int(h_str[i:i+2], 16) for i in (0, 2, 4)) + (default_alpha,)
                if len(h_str) == 8: return tuple(int(h_str[i:i+2], 16) for i in (0, 2, 4, 6))
            except (ValueError, TypeError): pass
            return (221,221,221,255) if default_alpha == 255 else (170,170,170,128)

        bg_color = hex_to_rgba(bg_hex); text_color = hex_to_rgba(txt_hex); watermark_color = hex_to_rgba(wm_hex, default_alpha=128) # Ensure alpha for watermark
        base_image = Image.new('RGBA', (img_width, img_height), bg_color)
        draw = ImageDraw.Draw(base_image)
        
        font_hl_name = os.getenv("FONT_PATH_HEADLINE","fonts/arialbd.ttf") # Ensure these font files exist in a 'fonts' subfolder or provide full paths
        font_wm_name = os.getenv("FONT_PATH_WATERMARK","fonts/arial.ttf")
        font_hl_path = os.path.join(APP_ROOT, font_hl_name); font_wm_path = os.path.join(APP_ROOT, font_wm_name)
        hl_fs = max(40, img_height//10); wm_fs = max(20, img_height//28)
        try:
            font_hl = ImageFont.truetype(font_hl_path, size=hl_fs)
            font_wm = ImageFont.truetype(font_wm_path, size=wm_fs)
        except IOError: 
            font_hl=ImageFont.load_default(); font_wm=ImageFont.load_default()
            app_logger.warning(f"Custom fonts not found. Using default fonts. Searched at: {font_hl_path}, {font_wm_path}")

        # Simplified text drawing
        text_bbox = draw.textbbox((0,0), headline_text, font=font_hl, anchor="lt")
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Crude centering logic, adjust as needed
        x_pos = (img_width - text_width) / 2
        y_pos = (img_height - text_height) / 2 - wm_fs # Move up slightly to make space for watermark if it's at bottom
        
        draw.text((x_pos, y_pos), headline_text, font=font_hl, fill=text_color, anchor="lt")
        draw.text((img_width - 10, img_height - 10), site_display_name_for_wm, font=font_wm, fill=watermark_color, anchor="rs") # rs = right, baseline

        base_image.save(output_path,"PNG")
        app_logger.info(f"Generated image: {output_path}")
        return output_path
    except ImportError: app_logger.error("Pillow (PIL) not installed for image generation."); return None
    except Exception as e_img: app_logger.error(f"Image generation error: {e_img}", exc_info=True); return None

def upload_image_to_wordpress(image_path, site_url, author_details, image_title="Featured Image"):
    if not image_path or not os.path.exists(image_path): return None
    media_api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/media"
    api_username = author_details['wp_username']
    api_password = author_details['app_password']
    credentials = f"{api_username}:{api_password}"; token = base64.b64encode(credentials.encode()).decode('utf-8')
    img_filename = os.path.basename(image_path)
    headers = {"Authorization": f"Basic {token}", "Content-Disposition": f'attachment; filename="{img_filename}"'}
    try:
        with open(image_path, 'rb') as img_file:
            files = {'file': (img_filename, img_file, 'image/png')} # Assuming PNG
            data = {'title': image_title, 'alt_text': f"Featured Image for: {image_title}"}
            response = requests.post(media_api_url, headers=headers, files=files, data=data, timeout=120)
        response.raise_for_status(); media_data = response.json(); return media_data.get('id')
    except Exception as e_upload: app_logger.error(f"Image upload error to {site_url} for {image_title}: {e_upload}"); return None

def create_wordpress_post(site_url, author_details, title, content_html, scheduled_time, category_id_str=None, featured_media_id=None):
    posts_api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
    api_username = author_details['wp_username']
    api_password = author_details['app_password']
    author_id_payload = author_details['wp_user_id']
    credentials = f"{api_username}:{api_password}"; token = base64.b64encode(credentials.encode()).decode('utf-8')
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    slug = re.sub(r'[^\w]+', '-', title.lower()).strip('-')[:70]
    payload = {"title": title, "content": content_html, "status": "future", "date_gmt": scheduled_time.isoformat(), "author": author_id_payload, "slug": slug} # Use date_gmt for UTC
    if featured_media_id: payload["featured_media"] = featured_media_id
    if category_id_str:
        try: payload["categories"] = [int(category_id_str)]
        except ValueError: app_logger.warning(f"Invalid category_id '{category_id_str}' for post '{title}'. Posting without category.")
    try:
        response = requests.post(posts_api_url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        post_data = response.json()
        app_logger.info(f"Successfully created/scheduled post '{title}' on {site_url}. Post ID: {post_data.get('id')}")
        return True
    except Exception as e_post: app_logger.error(f"WP post creation error for '{title}' on {site_url}: {e_post}"); return False

def load_tickers_from_excel(profile_config_entry):
    sheet_name = profile_config_entry.get('sheet_name') # Get from passed profile_config
    excel_path = os.getenv("EXCEL_FILE_PATH")
    ticker_col_name = os.getenv("EXCEL_TICKER_COLUMN_NAME", "Keyword")
    
    if not sheet_name: app_logger.warning(f"No sheet_name in profile {profile_config_entry.get('profile_name')}, cannot load Excel tickers."); return []
    if not excel_path or not os.path.exists(excel_path): app_logger.error(f"EXCEL_FILE_PATH not set or file not found: {excel_path}"); return []
    
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        if ticker_col_name not in df.columns:
            app_logger.error(f"Ticker column '{ticker_col_name}' not found in sheet '{sheet_name}' of '{excel_path}'.")
            return []
        tickers = df[ticker_col_name].dropna().astype(str).str.strip().str.upper().tolist()
        app_logger.info(f"Loaded {len(tickers)} tickers from Excel sheet '{sheet_name}'.")
        return tickers
    except Exception as e_excel: app_logger.error(f"Excel read error for sheet '{sheet_name}': {e_excel}"); return []

def load_tickers_from_uploaded_file(file_content_bytes, filename):
    try:
        if filename.lower().endswith('.csv'):
            try: content_str = file_content_bytes.decode('utf-8')
            except UnicodeDecodeError: content_str = file_content_bytes.decode('latin1')
            df = pd.read_csv(io.StringIO(content_str))
        elif filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(file_content_bytes))
        else:
            app_logger.error(f"Unsupported file type for custom tickers: {filename}")
            return []

        possible_ticker_cols = ['Ticker', 'Tickers', 'Symbol', 'Symbols', 'Keyword', 'Keywords']
        ticker_col_name = None
        for col in df.columns:
            if str(col).strip().lower() in [ptc.lower() for ptc in possible_ticker_cols]:
                ticker_col_name = col; break
        
        if not ticker_col_name:
            app_logger.error(f"Could not find a standard ticker column in uploaded file '{filename}'. Checked for: {possible_ticker_cols}")
            return []
            
        tickers = df[ticker_col_name].dropna().astype(str).str.strip().str.upper().tolist()
        app_logger.info(f"Loaded {len(tickers)} tickers from uploaded file '{filename}'.")
        return tickers
    except Exception as e:
        app_logger.error(f"Error processing uploaded ticker file '{filename}': {e}", exc_info=True)
        return []

def generate_dynamic_headline(ticker_symbol, site_profile_name):
    yr = f"{datetime.now(timezone.utc).year}-{datetime.now(timezone.utc).year+1}"
    templates = [
        f"{ticker_symbol} Stock Forecast: Price Prediction for {site_profile_name} ({yr})",
        f"Outlook for {ticker_symbol}: {site_profile_name}'s Analysis & {yr} Forecast",
        f"Is {ticker_symbol} a Buy? {site_profile_name} {yr} Stock Prediction",
        f"{ticker_symbol} ({site_profile_name}): {yr} Investment Outlook and Price Targets",
        f"Future of {ticker_symbol}: {site_profile_name} Analysis and {yr} Forecast",
    ]
    return random.choice(templates)


# Modified function signature to accept list of profile data dicts
def trigger_publishing_run(user_uid, profiles_to_process_data_list, articles_to_publish_per_profile_map, custom_tickers_by_profile_id=None, uploaded_file_details_by_profile_id=None):
    app_logger.info(f"Triggering publishing run for user: {user_uid}. Profiles to process: {len(profiles_to_process_data_list)}")

    profile_ids_for_this_run = [
        profile_data.get("profile_id") for profile_data in profiles_to_process_data_list 
        if profile_data.get("profile_id") # Ensure profile_id exists
    ]
    state = load_state(user_uid=user_uid, current_profile_ids_from_run=profile_ids_for_this_run)

    run_results_summary = {}
    # The detailed log will be appended to state['processed_tickers_detailed_log_by_profile'][profile_id]

    for profile_config in profiles_to_process_data_list: # Iterate over the provided list of profile data
        profile_id = profile_config.get("profile_id")
        profile_run_details = [] # To collect log entries for this specific profile in this run

        if not profile_id: # Should be rare if input list is clean
            app_logger.warning("Profile data item found without a 'profile_id'. Skipping.")
            continue # Skip this profile
            
        profile_name = profile_config.get("profile_name", profile_id)
        app_logger.info(f"\n--- Processing Profile: {profile_name} (ID: {profile_id}) ---")
        
        authors_list = profile_config.get('authors', [])
        if not authors_list:
            msg = f"No authors configured for profile '{profile_name}'. Skipping."
            app_logger.warning(msg)
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            profile_run_details.append({"ticker": "N/A", "status": "skipped_setup", "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),"message": msg})
            state['processed_tickers_detailed_log_by_profile'].setdefault(profile_id, []).extend(profile_run_details)
            continue

        min_gap = profile_config.get("min_scheduling_gap_minutes", int(os.getenv("MIN_SCHEDULING_GAP_MINUTES", "45")))
        max_gap = profile_config.get("max_scheduling_gap_minutes", int(os.getenv("MAX_SCHEDULING_GAP_MINUTES", "68")))

        posts_already_made_today = state['posts_today_by_profile'].get(profile_id, 0)
        requested_posts_for_this_run = articles_to_publish_per_profile_map.get(profile_id, 0)
        
        potential_new_posts_today = ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP - posts_already_made_today
        num_new_posts_to_attempt = min(requested_posts_for_this_run, potential_new_posts_today)

        if num_new_posts_to_attempt <= 0:
            msg = f"No posts requested or daily limit reached for '{profile_name}'. (Today: {posts_already_made_today}/{ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP}, Requested: {requested_posts_for_this_run})"
            app_logger.info(msg)
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            profile_run_details.append({"ticker": "N/A", "status": "skipped_limit", "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),"message": msg})
            state['processed_tickers_detailed_log_by_profile'].setdefault(profile_id, []).extend(profile_run_details)
            continue
        
        app_logger.info(f"Profile '{profile_name}': {posts_already_made_today} posts today. Will attempt: {num_new_posts_to_attempt} new posts.")

        last_author_idx = state.get('last_author_index_by_profile', {}).get(profile_id, -1)
        author_offset = (last_author_idx + 1) % len(authors_list) if authors_list else 0
        author_cycle = cycle(authors_list[author_offset:] + authors_list[:author_offset]) if authors_list else cycle([None])

        # --- Ticker Loading Logic ---
        tickers_for_this_profile = []
        # Priority: Custom tickers, then uploaded file, then Excel from profile config
        if custom_tickers_by_profile_id and profile_id in custom_tickers_by_profile_id and custom_tickers_by_profile_id[profile_id]:
            tickers_for_this_profile = custom_tickers_by_profile_id[profile_id]
            app_logger.info(f"Using {len(tickers_for_this_profile)} custom text input tickers for profile '{profile_name}'.")
        elif uploaded_file_details_by_profile_id and profile_id in uploaded_file_details_by_profile_id:
            file_details = uploaded_file_details_by_profile_id[profile_id]
            # Expects {'original_filename': str, 'content_bytes': bytes}
            tickers_for_this_profile = load_tickers_from_uploaded_file(file_details['content_bytes'], file_details['original_filename'])
            app_logger.info(f"Using {len(tickers_for_this_profile)} tickers from uploaded file '{file_details['original_filename']}' for profile '{profile_name}'.")
        else:
            # Fallback to Excel sheet defined in profile or pending list
            pending_tickers = state['pending_tickers_by_profile'].get(profile_id, [])
            if not pending_tickers:
                excel_tickers = load_tickers_from_excel(profile_config) # Uses the passed profile_config
                failed_tickers = list(state['failed_tickers_by_profile'].get(profile_id, []))
                published_log_for_profile = state['published_tickers_log_by_profile'].get(profile_id, set())
                
                combined_tickers = []
                seen_for_reload = set()
                for ft in failed_tickers:
                    if ft not in published_log_for_profile and ft not in seen_for_reload: combined_tickers.append(ft); seen_for_reload.add(ft)
                for et in excel_tickers:
                    if et not in published_log_for_profile and et not in seen_for_reload: combined_tickers.append(et); seen_for_reload.add(et)
                
                state['pending_tickers_by_profile'][profile_id] = combined_tickers
                state['failed_tickers_by_profile'][profile_id] = [] 
                tickers_for_this_profile = combined_tickers
                app_logger.info(f"Loaded {len(tickers_for_this_profile)} tickers from Excel/failed list for '{profile_name}'.")
            else:
                tickers_for_this_profile = pending_tickers
                app_logger.info(f"Using {len(tickers_for_this_profile)} pending tickers for profile '{profile_name}'.")

        if not tickers_for_this_profile:
            msg = f"No tickers available (custom, uploaded, Excel, or pending) for profile '{profile_name}'. Cannot publish."
            app_logger.warning(msg)
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": []}
            profile_run_details.append({"ticker": "N/A", "status": "skipped_no_tickers", "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),"message": msg})
            state['processed_tickers_detailed_log_by_profile'].setdefault(profile_id, []).extend(profile_run_details)
            continue

        # --- Scheduling Logic ---
        current_schedule_time_utc = datetime.now(timezone.utc) # Start with now in UTC
        last_sched_iso = state.get('last_successful_schedule_time_by_profile', {}).get(profile_id)

        if last_sched_iso:
            try:
                last_sched_utc = datetime.fromisoformat(last_sched_iso)
                if last_sched_utc.tzinfo is None: # If no timezone, assume UTC (or local, then convert)
                    last_sched_utc = last_sched_utc.replace(tzinfo=timezone.utc) # Or your local timezone
                current_schedule_time_utc = last_sched_utc + timedelta(minutes=random.randint(min_gap, max_gap))
            except Exception as e_sched_parse:
                app_logger.warning(f"Could not parse last schedule time '{last_sched_iso}': {e_sched_parse}. Defaulting schedule gap.")
                current_schedule_time_utc = datetime.now(timezone.utc) + timedelta(minutes=random.randint(min_gap, max_gap))

        if current_schedule_time_utc < datetime.now(timezone.utc):
            current_schedule_time_utc = datetime.now(timezone.utc) + timedelta(minutes=random.randint(5, 10)) # Short future gap
        
        posts_published_this_session = 0
        processed_tickers_in_current_list_for_state_update = []
        published_log_for_profile = state.get('published_tickers_log_by_profile', {}).get(profile_id, set())

        for ticker_to_process in tickers_for_this_profile:
            processed_tickers_in_current_list_for_state_update.append(ticker_to_process)
            
            if posts_published_this_session >= num_new_posts_to_attempt:
                app_logger.info(f"Reached attempt limit ({num_new_posts_to_attempt}) for profile '{profile_name}'.")
                break 
            if state.get('posts_today_by_profile', {}).get(profile_id, 0) >= ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP:
                app_logger.info(f"Reached absolute daily cap ({ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP}) for profile '{profile_name}'.")
                break

            if ticker_to_process in published_log_for_profile:
                msg = f"Ticker '{ticker_to_process}' already published for profile '{profile_name}'. Skipping."
                app_logger.info(msg)
                profile_run_details.append({
                    "ticker": ticker_to_process, "status": "skipped", 
                    "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), "message": "Already published."
                })
                continue

            app_logger.info(f"Processing ticker '{ticker_to_process}' for profile '{profile_name}'...")
            current_author_details = next(author_cycle)
            if current_author_details is None:
                app_logger.error(f"No author available for profile {profile_name}. This should not happen if authors_list was checked.")
                profile_run_details.append({
                     "ticker": ticker_to_process, "status": "failure", 
                     "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), "message": "No author available."
                })
                continue
            state['last_author_index_by_profile'][profile_id] = authors_list.index(current_author_details)

            report_sections = profile_config.get("report_sections_to_include", list(ALL_REPORT_SECTIONS.keys()))
            
            rdata_dict, html_content, css_content_unused = generate_wordpress_report(
                profile_name, ticker_to_process, APP_ROOT, report_sections
            )

            if "Error generating report" in html_content or not html_content or not rdata_dict:
                err_msg = f"Report generation failed for {ticker_to_process} on {profile_name}."
                app_logger.error(err_msg)
                state.get('failed_tickers_by_profile',{}).setdefault(profile_id, []).append(ticker_to_process)
                profile_run_details.append({
                    "ticker": ticker_to_process, "status": "failure", 
                    "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), "message": "Report generation failed."
                })
                continue

            post_title = generate_dynamic_headline(ticker_to_process, profile_name)
            
            temp_image_dir = os.path.join(APP_ROOT, "temp_images", profile_id)
            os.makedirs(temp_image_dir, exist_ok=True)
            safe_ticker_fn = re.sub(r'[^\w\-.]', '_', ticker_to_process)
            temp_image_path = os.path.join(temp_image_dir, f"{safe_ticker_fn}_{int(time.time())}.png")
            
            generated_image_path = generate_feature_image(post_title, profile_name, profile_config, temp_image_path)
            media_id = None
            if generated_image_path:
                media_id = upload_image_to_wordpress(generated_image_path, profile_config['site_url'], current_author_details, post_title)
                try: os.remove(generated_image_path)
                except OSError as e_remove: app_logger.warning(f"Could not remove temp image {generated_image_path}: {e_remove}")
            else:
                app_logger.warning(f"Feature image generation failed for {post_title}, proceeding without it.")

            if posts_published_this_session > 0:
                current_schedule_time_utc += timedelta(minutes=random.randint(min_gap, max_gap))
            if current_schedule_time_utc < datetime.now(timezone.utc):
                current_schedule_time_utc = datetime.now(timezone.utc) + timedelta(minutes=random.randint(2,5))

            post_creation_success = create_wordpress_post(
                profile_config['site_url'], current_author_details, post_title, html_content, 
                current_schedule_time_utc, # Pass UTC time
                profile_config.get('stockforecast_category_id'), media_id
            )

            current_time_str_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            if post_creation_success:
                state.get('last_successful_schedule_time_by_profile', {})[profile_id] = current_schedule_time_utc.isoformat()
                state.get('posts_today_by_profile', {})[profile_id] = state.get('posts_today_by_profile', {}).get(profile_id, 0) + 1
                state.get('published_tickers_log_by_profile', {}).setdefault(profile_id, set()).add(ticker_to_process)
                posts_published_this_session += 1
                app_logger.info(f"Successfully scheduled '{ticker_to_process}' for '{profile_name}' at {current_schedule_time_utc.strftime('%Y-%m-%d %H:%M')} UTC. Total today: {state['posts_today_by_profile'][profile_id]}.")
                profile_run_details.append({
                    "ticker": ticker_to_process, "status": "success", 
                    "timestamp": current_time_str_utc, "message": f"Post scheduled for {current_schedule_time_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC."
                })
            else:
                app_logger.error(f"Failed to create WordPress post for '{ticker_to_process}' on '{profile_name}'.")
                state.get('failed_tickers_by_profile', {}).setdefault(profile_id, []).append(ticker_to_process)
                profile_run_details.append({
                    "ticker": ticker_to_process, "status": "failure", 
                    "timestamp": current_time_str_utc, "message": "WordPress post creation failed."
                })
        
        # Update pending list for this profile if tickers were not from custom/uploaded source
        if not (custom_tickers_by_profile_id and profile_id in custom_tickers_by_profile_id and custom_tickers_by_profile_id[profile_id]) and \
           not (uploaded_file_details_by_profile_id and profile_id in uploaded_file_details_by_profile_id):
            current_pending_for_profile = state.get('pending_tickers_by_profile', {}).get(profile_id, [])
            state.get('pending_tickers_by_profile', {})[profile_id] = [
                t for t in current_pending_for_profile if t not in processed_tickers_in_current_list_for_state_update
            ]
        
        # Append this run's details to the persistent daily log in state
        state.get('processed_tickers_detailed_log_by_profile', {}).setdefault(profile_id, []).extend(profile_run_details)

        summary_msg = f"Attempted {num_new_posts_to_attempt}. Published {posts_published_this_session} new posts for '{profile_name}'. Total today: {state.get('posts_today_by_profile',{}).get(profile_id, 0)}."
        run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": summary_msg, "tickers_processed": profile_run_details} # Pass back details of this run
    
    save_state(state)
    app_logger.info("Triggered publishing run finished.")
    return run_results_summary


if __name__ == '__main__':
    app_logger.info(f"--- Auto Publisher CLI Mode ---")
    cli_profiles_data_list = load_profiles_config() # Returns list of profile dicts from JSON
    
    if not cli_profiles_data_list:
        app_logger.error("No site profiles loaded from profiles_config.json for CLI mode. Exiting.")
        exit(1)
    
    mock_user_uid_cli = "cli_user_standalone"
    # Prepare articles_map based on profile_id from the loaded data
    articles_map_cli = {profile.get('profile_id'): 1 for profile in cli_profiles_data_list if profile.get('profile_id')}
    
    # Example custom tickers for CLI if needed for testing
    # custom_tickers_example_cli = {"some_cli_profile_id": ["AAPL", "TSLA"]}

    results = trigger_publishing_run(
        mock_user_uid_cli,
        cli_profiles_data_list, # Pass the list of profile dictionaries
        articles_map_cli
        # custom_tickers_by_profile_id=custom_tickers_example_cli # Optional
    )
    
    if results:
        for pid_res, res_data in results.items():
            profile_name_res = res_data.get("profile_name", pid_res)
            status_summary_res = res_data.get("status_summary", "No summary.")
            app_logger.info(f"Profile {profile_name_res}: {status_summary_res}")
            if res_data.get("tickers_processed"):
                for ticker_res_log_entry in res_data["tickers_processed"]:
                    app_logger.info(f"  - Ticker: {ticker_res_log_entry['ticker']}, Status: {ticker_res_log_entry['status']}, Msg: {ticker_res_log_entry['message']}")
    app_logger.info("--- CLI Run Finished ---")