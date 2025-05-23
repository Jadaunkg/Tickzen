# auto_publisher.py
import pandas as pd
import time
from datetime import datetime, timedelta, timezone
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
import io

load_dotenv()

try:
    from wordpress_reporter import generate_wordpress_report, ALL_REPORT_SECTIONS
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
    log_file_path = os.path.join(APP_ROOT_PATH_FOR_LOG, LOG_FILE)
    handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(APP_ROOT, "wordpress_publisher_state_v11.pkl")
PROFILES_CONFIG_FILE = os.path.join(APP_ROOT, "profiles_config.json")

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

def generate_feature_image(headline_text, site_display_name_for_wm, profile_config_entry, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        from PIL import Image, ImageDraw, ImageFont
        img_width = int(os.getenv("FEATURE_IMAGE_WIDTH", 1200))
        img_height = int(os.getenv("FEATURE_IMAGE_HEIGHT", 630))
        env_prefix = profile_config_entry.get('env_prefix_for_feature_image_colors', 'DEFAULT')
        bg_hex = os.getenv(f"{env_prefix}_FEATURE_BG_COLOR", os.getenv("DEFAULT_FEATURE_BG_COLOR","#F0F0F0"))
        txt_hex = os.getenv(f"{env_prefix}_FEATURE_TEXT_COLOR", os.getenv("DEFAULT_FEATURE_TEXT_COLOR","#333333"))
        wm_hex = os.getenv(f"{env_prefix}_FEATURE_WATERMARK_COLOR", os.getenv("DEFAULT_FEATURE_WATERMARK_COLOR","#AAAAAA80"))

        def hex_to_rgba(h, a=255):
            h = (h or "").lstrip('#')
            try:
                if len(h) == 6: return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (a,)
                if len(h) == 8: return tuple(int(h[i:i+2], 16) for i in (0, 2, 4, 6))
            except: pass
            return (221,221,221,255) if a == 255 else (170,170,170,128)

        bg_color, txt_color, wm_color = hex_to_rgba(bg_hex), hex_to_rgba(txt_hex), hex_to_rgba(wm_hex, 128)
        img = Image.new('RGBA', (img_width, img_height), bg_color)
        draw = ImageDraw.Draw(img)
        font_hl_p = os.path.join(APP_ROOT, os.getenv("FONT_PATH_HEADLINE","fonts/arialbd.ttf"))
        font_wm_p = os.path.join(APP_ROOT, os.getenv("FONT_PATH_WATERMARK","fonts/arial.ttf"))
        hl_fs, wm_fs = max(40, img_height//10), max(20, img_height//28)
        try: font_hl, font_wm = ImageFont.truetype(font_hl_p, hl_fs), ImageFont.truetype(font_wm_p, wm_fs)
        except IOError: font_hl, font_wm = ImageFont.load_default(), ImageFont.load_default()
        
        bbox = draw.textbbox((0,0), headline_text, font=font_hl, anchor="lt")
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = (img_width - w) / 2, (img_height - h) / 2 - wm_fs
        draw.text((x, y), headline_text, font=font_hl, fill=txt_color, anchor="lt")
        draw.text((img_width - 10, img_height - 10), site_display_name_for_wm, font=font_wm, fill=wm_color, anchor="rs")
        img.save(output_path,"PNG")
        return output_path
    except ImportError: app_logger.error("Pillow (PIL) not installed."); return None
    except Exception as e: app_logger.error(f"Image generation error: {e}", exc_info=True); return None

def upload_image_to_wordpress(image_path, site_url, author, title="Featured Image"):
    if not image_path or not os.path.exists(image_path): return None
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/media"
    creds = base64.b64encode(f"{author['wp_username']}:{author['app_password']}".encode()).decode('utf-8')
    filename = os.path.basename(image_path)
    headers = {"Authorization": f"Basic {creds}", "Content-Disposition": f'attachment; filename="{filename}"'}
    try:
        with open(image_path, 'rb') as f: files = {'file': (filename, f, 'image/png')}
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
            img_dir = os.path.join(APP_ROOT, "temp_images", profile_id)
            os.makedirs(img_dir, exist_ok=True)
            img_path = os.path.join(img_dir, f"{re.sub(r'[^\\w]', '_', ticker)}_{int(time.time())}.png")
            
            _emit_automation_progress(socketio_instance, user_room, profile_id, ticker, "Publishing", "Image Gen", "Generating image...", "info")
            gen_img_path = generate_feature_image(title, profile_name, profile_config, img_path)
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