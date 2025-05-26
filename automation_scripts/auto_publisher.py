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
    ALL_REPORT_SECTIONS = { # Fallback
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
    default_state = {key: {pid: factory() for pid in active_profile_ids} for key, factory in default_factories.items()}
    default_state['last_run_date'] = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'rb') as f: state = pickle.load(f)
            app_logger.info(f"Loaded state from {STATE_FILE}")
            for key, factory in default_factories.items():
                if key not in state: state[key] = {pid: factory() for pid in active_profile_ids}
                else: 
                    for pid in active_profile_ids:
                        if pid not in state[key]: state[key][pid] = factory()
            
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
            
            for pid in active_profile_ids:
                state.setdefault('posts_today_by_profile', {})[pid] = state.get('posts_today_by_profile', {}).get(pid, 0)
                state.setdefault('processed_tickers_detailed_log_by_profile', {}).setdefault(pid, [])
            return state
        except Exception as e:
            app_logger.warning(f"Could not load/process state file '{STATE_FILE}': {e}. Using default.", exc_info=True)
    save_state(default_state)
    return default_state

def save_state(state):
    try:
        with open(STATE_FILE, 'wb') as f: pickle.dump(state, f)
        app_logger.info(f"Saved state to {STATE_FILE}")
    except Exception as e:
        app_logger.error(f"Could not save state to {STATE_FILE}: {e}", exc_info=True)

def generate_feature_image(headline_text, site_display_name_for_wm, profile_config_entry, output_path, ticker="N/A"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        # --- Configuration & Colors ---
        img_width = int(os.getenv("FEATURE_IMAGE_WIDTH", 1200))
        img_height = int(os.getenv("FEATURE_IMAGE_HEIGHT", 630))
        
        env_prefix = profile_config_entry.get('env_prefix_for_feature_image_colors', 'DEFAULT')
        app_logger.info(f"[FeatureImage] Resolved env_prefix: '{env_prefix}'")

        def get_env_color(var_name, default_hex):
            # Determine specific and default env var names
            specific_env_var = f"{env_prefix}_{var_name}"
            default_env_var = f"DEFAULT_{var_name}"
            
            # Try to get from specific env var
            color_val = os.getenv(specific_env_var)
            source = f"env ('{specific_env_var}')"
            
            # If not found, try default env var
            if color_val is None:
                color_val = os.getenv(default_env_var)
                source = f"env ('{default_env_var}')"
            
            # If still not found, use hardcoded default_hex
            if color_val is None:
                color_val = default_hex
                source = f"hardcoded default ('{default_hex}')"
            
            app_logger.info(f"[FeatureImage] Color for '{var_name}': '{color_val}' (Source: {source})")
            return color_val

        bg_hex = get_env_color("FEATURE_BG_COLOR", "#0A264E") 
        headline_color_hex = get_env_color("FEATURE_HEADLINE_TEXT_COLOR", "#FFFFFF")
        sub_headline_color_hex = get_env_color("FEATURE_SUBTEXT_COLOR", "#E0E0E0")
        watermark_text_color_hex = get_env_color("FEATURE_WATERMARK_TEXT_COLOR", "#A0A0A0")
        
        right_panel_bg_hex = get_env_color("FEATURE_RIGHT_PANEL_BG_COLOR", "#1C3A6E") 
        ticker_text_color_hex = get_env_color("FEATURE_TICKER_TEXT_COLOR", "#FFFFFF")

        # Correcting how site_logo_path is determined and logged
        resolved_site_logo_path_specific_var = f"{env_prefix}_SITE_LOGO_PATH"
        resolved_site_logo_path_default_var = "DEFAULT_SITE_LOGO_PATH"
        site_logo_path = os.getenv(resolved_site_logo_path_specific_var, os.getenv(resolved_site_logo_path_default_var))
        app_logger.info(f"[FeatureImage] Attempting to use Site Logo. Specific var: '{resolved_site_logo_path_specific_var}', Default var: '{resolved_site_logo_path_default_var}'. Resolved path: '{site_logo_path}'")

        def hex_to_rgba(h, default_color=(0,0,0,0)):
            original_hex = h # Keep original hex for logging
            h = (h or "").lstrip('#')
            try:
                if len(h) == 6: 
                    rgba = tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)
                    return rgba # Successful conversion, no log needed here per refinement
                if len(h) == 8: 
                    rgba = tuple(int(h[i:i+2], 16) for i in (0, 2, 4, 6))
                    return rgba # Successful conversion
            except ValueError as e_hex_val: # Catch specific ValueError for int conversion
                app_logger.warning(f"[FeatureImage] hex_to_rgba ValueError for '{original_hex}' (parsed as '{h}'): {e_hex_val}. Using default: {default_color}")
                return default_color # Return default on ValueError
            except Exception as e_hex_other: # Catch any other unexpected errors during conversion
                app_logger.warning(f"[FeatureImage] hex_to_rgba unexpected error for '{original_hex}': {e_hex_other}. Using default: {default_color}")
                return default_color # Return default on other errors
            
            # If h was not length 6 or 8, it's an invalid format (e.g., too short, too long, or empty after lstrip)
            app_logger.warning(f"[FeatureImage] hex_to_rgba: '{original_hex}' (parsed as '{h}') is invalid format. Using default: {default_color}")
            return default_color

        bg_color = hex_to_rgba(bg_hex, (10, 38, 78, 255))
        headline_color = hex_to_rgba(headline_color_hex, (255,255,255,255))
        sub_headline_color = hex_to_rgba(sub_headline_color_hex, (224,224,224,255))
        watermark_text_color = hex_to_rgba(watermark_text_color_hex, (160,160,160,255))
        right_panel_bg_color = hex_to_rgba(right_panel_bg_hex, (28, 58, 110, 255))
        ticker_text_color = hex_to_rgba(ticker_text_color_hex, (255,255,255,255))

        # --- Fonts ---
        def get_font(env_var_name, default_font_name, default_size):
            font_path = os.path.join(APP_ROOT, "..", os.getenv(env_var_name, default_font_name))
            try:
                return ImageFont.truetype(font_path, default_size)
            except IOError:
                app_logger.warning(f"Font not found at {font_path}. Using default.")
                return ImageFont.load_default()

        font_headline = get_font("FONT_PATH_HEADLINE", "fonts/arialbd.ttf", img_height // 12)
        font_sub_headline = get_font("FONT_PATH_SUB_HEADLINE", "fonts/arial.ttf", img_height // 25)
        font_watermark = get_font("FONT_PATH_WATERMARK", "fonts/arial.ttf", img_height // 30)
        font_ticker = get_font("FONT_PATH_TICKER", "fonts/arialbd.ttf", img_height // 5)

        # --- Create Base Image ---
        img = Image.new('RGBA', (img_width, img_height), bg_color)
        app_logger.info(f"[FeatureImage] Base image created with bg_color (RGBA): {bg_color}")
        draw = ImageDraw.Draw(img)

        # --- Layout Constants ---
        padding = img_width // 25 
        logo_max_h = img_height // 8 
        text_area_left_margin = padding
        
        # --- Right Panel for Ticker/Visual ---
        right_panel_width = int(img_width * 0.40)
        right_panel_x_start = img_width - right_panel_width
        draw.rectangle([right_panel_x_start, 0, img_width, img_height], fill=right_panel_bg_color)

        # --- Site Logo (Top-Left) ---
        current_y = padding
        if site_logo_path and os.path.exists(site_logo_path):
            try:
                logo_img = Image.open(site_logo_path).convert("RGBA")
                
                ratio = min(logo_max_h / logo_img.height, (right_panel_x_start - 2*padding) / logo_img.width)
                new_w = int(logo_img.width * ratio)
                new_h = int(logo_img.height * ratio)
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
            app_logger.info(f"Site logo not found or path not set (env var: {resolved_site_logo_path_specific_var} or {resolved_site_logo_path_default_var}). Skipping logo.")

        # --- Main Headline (Left, below logo) ---
        text_area_width = right_panel_x_start - text_area_left_margin - padding 
        
        words = headline_text.split()
        lines = []
        current_line = ""
        for word in words:
            # Check width using textbbox which is more accurate for TrueType
            if draw.textbbox((0,0), current_line + word, font=font_headline)[2] <= text_area_width:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        lines.append(current_line.strip()) # Add the last line

        for line in lines:
            # Use getbbox for height, anchor lt for positioning
            line_bbox = font_headline.getbbox(line)
            line_height = line_bbox[3] - line_bbox[1] # height = y1 - y0
            if current_y + line_height > img_height - padding - font_sub_headline.getbbox("A")[3] - font_watermark.getbbox("A")[3]:
                break 
            draw.text((text_area_left_margin, current_y), line, font=font_headline, fill=headline_color, anchor="lt")
            current_y += line_height * 1.2 # Add 20% extra for line spacing

        # --- Sub-Headline ---
        current_y += padding // 3 
        sub_headline_text = f"Analysis by {site_display_name_for_wm} Team"
        sub_headline_bbox = font_sub_headline.getbbox(sub_headline_text)
        sub_headline_height = sub_headline_bbox[3] - sub_headline_bbox[1]

        if current_y + sub_headline_height < img_height - padding - font_watermark.getbbox("A")[3]:
            draw.text((text_area_left_margin, current_y), sub_headline_text, font=font_sub_headline, fill=sub_headline_color, anchor="lt")
            # current_y += sub_headline_height + padding # This line was removed as it's not used after this.

        # --- Ticker Symbol (Right Panel) ---
        if ticker and ticker != "N/A":
            # Calculate available height for ticker text to avoid overlap with any top/bottom elements if they existed in this panel
            # For now, we assume ticker is the main element in this panel, so vertical centering is relative to panel height
            
            # Use textlength for width and approx height for initial estimate for centering
            # For TrueType fonts, getbbox is more accurate for specific text after rendering potential
            # However, for rough centering before complex rendering, textlength is often used.
            # anchor="mm" handles precise centering based on the font's metrics for the given text.
            
            ticker_x_centered = right_panel_x_start + (right_panel_width / 2)
            ticker_y_centered = img_height / 2
            
            draw.text((ticker_x_centered, ticker_y_centered), ticker, font=font_ticker, fill=ticker_text_color, anchor="mm")

        # --- Watermark (Bottom-Center) ---
        watermark_text = f"@{site_display_name_for_wm}"
        # For anchor="mb", Pillow positions the text so its middle-bottom point is at the given (x,y)
        # So, x should be the horizontal center of the image, y is the bottom position.
        wm_x_centered = img_width / 2
        wm_y_bottom = img_height - (padding // 2) # Positioned from bottom
        draw.text((wm_x_centered, wm_y_bottom), watermark_text, font=font_watermark, fill=watermark_text_color, anchor="mb")

        # --- Save Image ---
        img.save(output_path, "PNG", quality=90, optimize=True)
        return output_path
        
    except ImportError:
        app_logger.error("Pillow (PIL) not installed. Cannot generate feature image.")
        return None
    except Exception as e:
        app_logger.error(f"Feature image generation error for headline '{headline_text}': {e}", exc_info=True)
        return None

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
    sheet = profile_config.get('sheet_name')
    excel_p = os.getenv("EXCEL_FILE_PATH")
    col_name = os.getenv("EXCEL_TICKER_COLUMN_NAME", "Keyword")
    if not sheet: return []
    if not excel_p or not os.path.exists(excel_p): app_logger.error(f"Excel path not found: {excel_p}"); return []
    try:
        df = pd.read_excel(excel_p, sheet_name=sheet)
        if col_name not in df.columns: return []
        return df[col_name].dropna().astype(str).str.strip().str.upper().tolist()
    except Exception as e: app_logger.error(f"Excel read error for '{sheet}': {e}"); return []

def load_tickers_from_uploaded_file(content_bytes, filename):
    try:
        if filename.lower().endswith('.csv'):
            try: content_str = content_bytes.decode('utf-8')
            except UnicodeDecodeError: content_str = content_bytes.decode('latin1') # Fallback
            df = pd.read_csv(io.StringIO(content_str))
        elif filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content_bytes))
        else: return []
        cols = ['Ticker', 'Tickers', 'Symbol', 'Symbols', 'Keyword', 'Keywords']
        t_col = next((c for c in df.columns if str(c).strip().lower() in [pc.lower() for pc in cols]), None)
        if not t_col: return []
        return df[t_col].dropna().astype(str).str.strip().str.upper().tolist()
    except Exception as e: app_logger.error(f"Uploaded file error '{filename}': {e}", exc_info=True); return []

def generate_dynamic_headline(ticker, profile_name):
    yr = f"{datetime.now(timezone.utc).year}-{datetime.now(timezone.utc).year+1}"
    templates = [f"{ticker} Stock Forecast: Price Prediction for {profile_name} ({yr})", f"Outlook for {ticker}: {profile_name}'s Analysis & {yr} Forecast"]
    return random.choice(templates)

def trigger_publishing_run(user_uid, profiles_to_process_data_list, articles_to_publish_per_profile_map, 
                           custom_tickers_by_profile_id=None, uploaded_file_details_by_profile_id=None,
                           socketio_instance=None, user_room=None): 
    _emit_automation_progress(socketio_instance, user_room, "Overall", "N/A", "Initialization", "Run Started", f"Processing {len(profiles_to_process_data_list)} profiles.", "info")

    profile_ids_for_run = [p.get("profile_id") for p in profiles_to_process_data_list if p.get("profile_id")]
    state = load_state(user_uid=user_uid, current_profile_ids_from_run=profile_ids_for_run)
    run_results_summary = {}

    for profile_config in profiles_to_process_data_list: 
        profile_id = profile_config.get("profile_id")
        current_run_profile_log_details = [] 
        profile_name = profile_config.get("profile_name", profile_id)
        _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Profile Processing", "Starting", f"Processing profile: {profile_name}", "info")

        if not profile_id: continue
            
        authors = profile_config.get('authors', [])
        if not authors:
            msg = f"No authors for '{profile_name}'. Skipping."
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Setup", "Skipped", msg, "warning")
            current_run_profile_log_details.append({"ticker": "N/A", "status": "skipped_setup", "timestamp": datetime.now(timezone.utc).isoformat(),"message": msg})
            state.setdefault('processed_tickers_detailed_log_by_profile', {}).setdefault(profile_id, []).extend(current_run_profile_log_details)
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": current_run_profile_log_details}
            continue

        posts_today = state['posts_today_by_profile'].get(profile_id, 0)
        requested_posts = articles_to_publish_per_profile_map.get(profile_id, 0)
        can_publish = ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP - posts_today
        to_attempt = min(requested_posts, can_publish)

        if to_attempt <= 0:
            msg = f"Limit reached for '{profile_name}'. Today: {posts_today}/{ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP}, Req: {requested_posts}"
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Setup", "Skipped", msg, "info")
            current_run_profile_log_details.append({"ticker": "N/A", "status": "skipped_limit", "timestamp": datetime.now(timezone.utc).isoformat(),"message": msg})
            state.setdefault('processed_tickers_detailed_log_by_profile', {}).setdefault(profile_id, []).extend(current_run_profile_log_details)
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": current_run_profile_log_details}
            continue
        
        _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Setup", "Post Count", f"Attempting {to_attempt} posts.", "info")
        
        author_cycle = cycle(authors) # Simplified author cycling for this run

        tickers_for_profile = []
        if custom_tickers_by_profile_id and profile_id in custom_tickers_by_profile_id and custom_tickers_by_profile_id[profile_id]:
            tickers_for_profile = custom_tickers_by_profile_id[profile_id]
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "Custom", f"Using {len(tickers_for_profile)} custom tickers.", "info")
        elif uploaded_file_details_by_profile_id and profile_id in uploaded_file_details_by_profile_id:
            f_details = uploaded_file_details_by_profile_id[profile_id]
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "File", f"Processing file '{f_details['original_filename']}'.", "info")
            tickers_for_profile = load_tickers_from_uploaded_file(f_details['content_bytes'], f_details['original_filename'])
        else:
            pending = state['pending_tickers_by_profile'].get(profile_id, [])
            if not pending:
                excel_tickers = load_tickers_from_excel(profile_config)
                failed = list(state['failed_tickers_by_profile'].get(profile_id, []))
                published = state['published_tickers_log_by_profile'].get(profile_id, set())
                tickers_for_profile = [t for t in failed + excel_tickers if t not in published and t not in tickers_for_profile] # Avoid duplicates
                state['pending_tickers_by_profile'][profile_id] = tickers_for_profile
                state['failed_tickers_by_profile'][profile_id] = []
            else: tickers_for_profile = pending

        if not tickers_for_profile:
            msg = f"No tickers for '{profile_name}'."
            _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Ticker Loading", "Skipped", msg, "warning")
            current_run_profile_log_details.append({"ticker": "N/A", "status": "skipped_no_tickers", "timestamp": datetime.now(timezone.utc).isoformat(),"message": msg})
            state.setdefault('processed_tickers_detailed_log_by_profile', {}).setdefault(profile_id, []).extend(current_run_profile_log_details)
            run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": msg, "tickers_processed": current_run_profile_log_details}
            continue

        last_sched_iso = state.get('last_successful_schedule_time_by_profile', {}).get(profile_id)
        sched_time = datetime.now(timezone.utc)
        if last_sched_iso:
            try: sched_time = datetime.fromisoformat(last_sched_iso).replace(tzinfo=timezone.utc) + timedelta(minutes=random.randint(profile_config.get("min_scheduling_gap_minutes",45), profile_config.get("max_scheduling_gap_minutes",68)))
            except: sched_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(profile_config.get("min_scheduling_gap_minutes",45),profile_config.get("max_scheduling_gap_minutes",68)))
        if sched_time < datetime.now(timezone.utc): sched_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(2,5))
        
        published_this_run = 0
        processed_tickers_this_run_list = []

        for ticker in tickers_for_profile:
            processed_tickers_this_run_list.append(ticker)
            if published_this_run >= to_attempt or state['posts_today_by_profile'].get(profile_id, 0) >= ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP: break
            if ticker in state.get('published_tickers_log_by_profile', {}).get(profile_id, set()):
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Article", "Skipped", "Already published.", "info")
                current_run_profile_log_details.append({"ticker": ticker, "status": "skipped", "timestamp": datetime.now(timezone.utc).isoformat(), "message": "Already published."})
                continue

            author = next(author_cycle)
            state['last_author_index_by_profile'][profile_id] = profile_config['authors'].index(author)
            
            _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Report Gen", "Starting", "Generating report...", "info")
            rdata, html, _ = generate_wordpress_report(profile_name, ticker, APP_ROOT, profile_config.get("report_sections_to_include", list(ALL_REPORT_SECTIONS.keys())))
            if "Error generating report" in html or not html or not rdata:
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Report Gen", "Failed", "Report generation failed.", "error")
                state.get('failed_tickers_by_profile', {}).setdefault(profile_id, []).append(ticker)
                current_run_profile_log_details.append({"ticker": ticker, "status": "failure", "timestamp": datetime.now(timezone.utc).isoformat(), "message": "Report gen failed."})
                continue
            _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Report Gen", "Done", "Report generated.", "success")

            title = generate_dynamic_headline(ticker, profile_name)
            img_dir = os.path.join(APP_ROOT, "..", "generated_data", "temp_images", profile_id)
            os.makedirs(img_dir, exist_ok=True)
            img_path = os.path.join(img_dir, f"{re.sub(r'[^\\w]', '_', ticker)}_{int(time.time())}.png")
            
            _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Publishing", "Image Gen", "Generating image...", "info")
            gen_img_path = generate_feature_image(title, profile_name, profile_config, img_path, ticker)
            media_id = None
            if gen_img_path:
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Publishing", "Image Upload", "Uploading image...", "info")
                media_id = upload_image_to_wordpress(gen_img_path, profile_config['site_url'], author, title)
                if media_id: _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Publishing", "Image OK", f"Image ID: {media_id}", "success")
                else: _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Publishing", "Image Fail", "Image upload failed.", "warning")
                try: os.remove(gen_img_path)
                except: pass
            else: _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Publishing", "Image Fail", "Image gen failed.", "warning")

            if published_this_run > 0: sched_time += timedelta(minutes=random.randint(profile_config.get("min_scheduling_gap_minutes",45), profile_config.get("max_scheduling_gap_minutes",68)))
            if sched_time < datetime.now(timezone.utc): sched_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(2,5))
            
            _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Publishing", "Scheduling", f"Scheduling for {sched_time.strftime('%H:%M')} by {author['wp_username']}", "info")
            success = create_wordpress_post(profile_config['site_url'], author, title, html, sched_time, profile_config.get('stockforecast_category_id'), media_id)
            
            ts_now_iso = datetime.now(timezone.utc).isoformat()
            if success:
                state['last_successful_schedule_time_by_profile'][profile_id] = sched_time.isoformat()
                state['posts_today_by_profile'][profile_id] = state['posts_today_by_profile'].get(profile_id, 0) + 1
                state.get('published_tickers_log_by_profile', {}).setdefault(profile_id, set()).add(ticker)
                published_this_run += 1
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Publishing", "Scheduled", f"Post scheduled for {sched_time.strftime('%H:%M')}.", "success")
                current_run_profile_log_details.append({"ticker": ticker, "status": "success", "timestamp": ts_now_iso, "message": f"Scheduled for {sched_time.strftime('%H:%M:%S')} UTC."})
            else:
                _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Publishing", "Failed", "Post scheduling failed.", "error")
                state.get('failed_tickers_by_profile', {}).setdefault(profile_id, []).append(ticker)
                current_run_profile_log_details.append({"ticker": ticker, "status": "failure", "timestamp": ts_now_iso, "message": "WP post creation failed."})
        
        if not (custom_tickers_by_profile_id and profile_id in custom_tickers_by_profile_id and custom_tickers_by_profile_id[profile_id]) and \
           not (uploaded_file_details_by_profile_id and profile_id in uploaded_file_details_by_profile_id):
            current_pending = state.get('pending_tickers_by_profile', {}).get(profile_id, [])
            state['pending_tickers_by_profile'][profile_id] = [t for t in current_pending if t not in processed_tickers_this_run_list]
        
        state.setdefault('processed_tickers_detailed_log_by_profile', {}).setdefault(profile_id, []).extend(current_run_profile_log_details)
        
        summary = f"Successfully Published article {published_this_run}. Total published article for today: {state['posts_today_by_profile'].get(profile_id,0)}."
        _emit_automation_progress(socketio_instance, user_room, profile_id, "N/A", "Profile Processing", "Complete", summary, "success" if published_this_run > 0 else "info")
        run_results_summary[profile_id] = {"profile_name": profile_name, "status_summary": summary, "tickers_processed": current_run_profile_log_details}
    
    save_state(state)
    _emit_automation_progress(socketio_instance, user_room, "Overall", "N/A", "Completion", "Run Finished", "All selected profiles processed.", "success")
    return run_results_summary

if __name__ == '__main__':
    app_logger.info(f"--- Auto Publisher CLI Mode ---")
    cli_profiles = load_profiles_config()
    if not cli_profiles: app_logger.error("No profiles for CLI mode. Exiting."); exit(1)
    articles_map = {p.get('profile_id'): 1 for p in cli_profiles if p.get('profile_id')}
    results = trigger_publishing_run("cli_user_standalone", cli_profiles, articles_map)
    if results:
        for pid, data in results.items():
            app_logger.info(f"Profile {data.get('profile_name',pid)}: {data.get('status_summary','No summary.')}")
            for log in data.get("tickers_processed",[]): app_logger.info(f"  - {log['ticker']}: {log['status']} - {log['message']}")
    app_logger.info("--- CLI Run Finished ---")