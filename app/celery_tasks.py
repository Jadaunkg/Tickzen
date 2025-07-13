"""
Celery tasks for background processing
"""
import os
import sys
import io
import time
import traceback
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from celery import current_task
from werkzeug.utils import secure_filename

# Import Firebase setup
try:
    from config.firebase_admin_setup import get_storage_bucket, get_firestore_client
except ImportError as e:
    logging.error(f"Failed to import Firebase setup: {e}")
    get_storage_bucket = None
    get_firestore_client = None

# Import Celery app
from app.celery_config import celery_app

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_TICKERS_TO_STORE_IN_FIRESTORE = 500
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}


class TaskStatus:
    """Task status tracking"""
    PENDING = 'PENDING'
    STARTED = 'STARTED'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    RETRY = 'RETRY'


def update_task_progress(progress: int, message: str, status: str = 'PROGRESS'):
    """Update task progress"""
    if current_task:
        current_task.update_state(
            state=status,
            meta={
                'current': progress,
                'total': 100,
                'status': message
            }
        )


@celery_app.task(bind=True, name='app.celery_tasks.file_upload.upload_file_to_storage_task')
def upload_file_to_storage_task(self, user_uid: str, profile_id: str, file_bytes: bytes, 
                               original_filename: str, content_type: str = None) -> Dict[str, Any]:
    """
    Background task to upload file to Firebase Storage
    """
    task_id = self.request.id
    logger.info(f"Starting file upload task {task_id} for user {user_uid}, profile {profile_id}")
    
    try:
        update_task_progress(10, "Initializing upload...")
        
        if not get_storage_bucket:
            raise Exception("Firebase Storage not available")
        
        bucket = get_storage_bucket()
        if not bucket:
            raise Exception("Storage bucket not available")
        
        if not file_bytes or not original_filename:
            raise Exception("File data or filename missing")
        
        filename = secure_filename(original_filename)
        storage_path = f"user_ticker_files/{user_uid}/{profile_id}/{filename}"
        
        update_task_progress(30, "Uploading to Firebase Storage...")
        
        # Create blob and upload
        blob = bucket.blob(storage_path)
        file_obj = io.BytesIO(file_bytes)
        
        # Set content type if provided
        if content_type:
            blob.content_type = content_type
        
        blob.upload_from_file(file_obj)
        
        update_task_progress(80, "Upload completed, extracting metadata...")
        
        # Extract ticker metadata
        ticker_meta = extract_ticker_metadata_from_file_content_task.delay(
            file_bytes, original_filename
        ).get()
        
        update_task_progress(100, "Upload and metadata extraction completed")
        
        result = {
            'storage_path': storage_path,
            'filename': filename,
            'ticker_metadata': ticker_meta,
            'uploaded_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"File upload task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"File upload failed: {str(e)}"
        logger.error(f"File upload task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=60, max_retries=3, exc=e)


@celery_app.task(bind=True, name='app.celery_tasks.file_upload.extract_ticker_metadata_from_file_content_task')
def extract_ticker_metadata_from_file_content_task(self, content_bytes: bytes, 
                                                  original_filename: str) -> Dict[str, Any]:
    """
    Background task to extract ticker metadata from file content
    """
    task_id = self.request.id
    logger.info(f"Starting metadata extraction task {task_id} for file {original_filename}")
    
    try:
        update_task_progress(20, "Reading file content...")
        
        tickers = []
        common_ticker_column_names = ["Ticker", "Tickers", "Symbol", "Symbols", "Stock", "Stocks", "Keyword", "Keywords"]
        
        # Determine file type and read
        if original_filename.lower().endswith('.csv'):
            try:
                content_str = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                content_str = content_bytes.decode('latin1')
            df = pd.read_csv(io.StringIO(content_str))
        elif original_filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content_bytes))
        else:
            raise Exception('Unsupported file type')
        
        update_task_progress(50, "Processing ticker data...")
        
        if df.empty:
            raise Exception('File is empty or unparsable')
        
        # Find ticker column
        ticker_col_found = None
        for col_name_option in common_ticker_column_names:
            if col_name_option in df.columns:
                ticker_col_found = col_name_option
                break
        if not ticker_col_found:
            ticker_col_found = df.columns[0]
        
        # Extract tickers
        tickers = df[ticker_col_found].dropna().astype(str).str.strip().str.upper().tolist()
        
        update_task_progress(80, "Finalizing metadata...")
        
        # Limit tickers for storage
        limited_all_tickers = tickers[:MAX_TICKERS_TO_STORE_IN_FIRESTORE]
        if len(tickers) > MAX_TICKERS_TO_STORE_IN_FIRESTORE:
            logger.warning(f"File '{original_filename}' contains {len(tickers)} tickers. "
                          f"Storing only the first {MAX_TICKERS_TO_STORE_IN_FIRESTORE} in Firestore.")
        
        result = {
            'count': len(tickers),
            'preview': tickers[:5],
            'all_tickers': limited_all_tickers
        }
        
        update_task_progress(100, "Metadata extraction completed")
        logger.info(f"Metadata extraction task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Metadata extraction failed: {str(e)}"
        logger.error(f"Metadata extraction task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=30, max_retries=2, exc=e)


@celery_app.task(bind=True, name='app.celery_tasks.analysis.run_stock_analysis_task')
def run_stock_analysis_task(self, ticker: str, user_uid: str = None, room_id: str = None) -> Dict[str, Any]:
    """
    Background task to run stock analysis
    """
    task_id = self.request.id
    logger.info(f"Starting stock analysis task {task_id} for ticker {ticker}")
    
    try:
        update_task_progress(10, f"Initializing analysis for {ticker}...")
        
        # Import pipeline
        try:
            from automation_scripts.pipeline import run_pipeline
        except ImportError as e:
            raise Exception(f"Pipeline module not available: {e}")
        
        update_task_progress(20, "Running analysis pipeline...")
        
        # Run the pipeline
        request_timestamp = str(int(time.time()))
        pipeline_result = run_pipeline(
            ticker, 
            request_timestamp, 
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            socketio_instance=None,  # Will handle separately
            task_room=room_id
        )
        
        update_task_progress(80, "Processing results...")
        
        if pipeline_result is None:
            raise Exception("Analysis pipeline returned no results")
        
        if isinstance(pipeline_result, tuple) and len(pipeline_result) >= 4:
            model_obj, forecast_obj, path_info_from_pipeline, report_html_content_from_pipeline = pipeline_result[:4]
            
            if not isinstance(report_html_content_from_pipeline, str) or "Error Generating Report" in report_html_content_from_pipeline:
                raise Exception("Report generation failed")
            
            # Save report to file
            generated_filename = f"{ticker}_report_dynamic_{request_timestamp}.html"
            reports_path = os.path.join(PROJECT_ROOT, 'generated_data', 'stock_reports')
            os.makedirs(reports_path, exist_ok=True)
            
            absolute_report_filepath = os.path.join(reports_path, generated_filename)
            with open(absolute_report_filepath, 'w', encoding='utf-8') as f:
                f.write(report_html_content_from_pipeline)
            
            update_task_progress(90, "Saving to history...")
            
            # Save to history if user is logged in
            if user_uid:
                try:
                    from app.main_portal_app import save_report_to_history
                    generated_at_dt = datetime.fromtimestamp(int(request_timestamp), timezone.utc)
                    save_report_to_history(user_uid, ticker, generated_filename, generated_at_dt)
                except Exception as e:
                    logger.warning(f"Failed to save report to history: {e}")
            
            update_task_progress(100, "Analysis completed successfully")
            
            result = {
                'success': True,
                'ticker': ticker,
                'report_filename': generated_filename,
                'report_path': absolute_report_filepath,
                'word_count': len(report_html_content_from_pipeline.split()),
                'timestamp': request_timestamp
            }
            
            logger.info(f"Stock analysis task {task_id} completed successfully")
            return result
            
        else:
            raise Exception("Invalid pipeline result format")
        
    except Exception as e:
        error_msg = f"Stock analysis failed: {str(e)}"
        logger.error(f"Stock analysis task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=120, max_retries=2, exc=e)


@celery_app.task(bind=True, name='app.celery_tasks.wp_assets.generate_wp_assets_task')
def generate_wp_assets_task(self, ticker: str, user_uid: str = None, room_id: str = None) -> Dict[str, Any]:
    """
    Background task to generate WordPress assets
    """
    task_id = self.request.id
    logger.info(f"Starting WP asset generation task {task_id} for ticker {ticker}")
    
    try:
        update_task_progress(10, f"Initializing WP asset generation for {ticker}...")
        
        # Import pipeline
        try:
            from automation_scripts.pipeline import run_wp_pipeline
        except ImportError as e:
            raise Exception(f"WP pipeline module not available: {e}")
        
        update_task_progress(30, "Running WP asset pipeline...")
        
        # Run the WP pipeline
        timestamp = str(int(time.time()))
        model_obj, forecast_obj, html_report_fragment, img_urls_dict = run_wp_pipeline(
            ticker, 
            timestamp, 
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            socketio_instance=None,  # Will handle separately
            task_room=room_id
        )
        
        update_task_progress(80, "Processing WP assets...")
        
        if not isinstance(img_urls_dict, dict):
            img_urls_dict = {}
        
        if not html_report_fragment or "Error Generating Report" in html_report_fragment:
            raise Exception("WP asset HTML generation failed")
        
        update_task_progress(100, "WP asset generation completed")
        
        result = {
            'success': True,
            'ticker': ticker,
            'report_html': html_report_fragment,
            'chart_urls': img_urls_dict,
            'timestamp': timestamp
        }
        
        logger.info(f"WP asset generation task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"WP asset generation failed: {str(e)}"
        logger.error(f"WP asset generation task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=60, max_retries=2, exc=e)


@celery_app.task(bind=True, name='app.celery_tasks.firestore.save_user_site_profile_task')
def save_user_site_profile_task(self, user_uid: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task to save user site profile to Firestore
    """
    task_id = self.request.id
    logger.info(f"Starting profile save task {task_id} for user {user_uid}")
    
    try:
        update_task_progress(20, "Connecting to Firestore...")
        
        if not get_firestore_client:
            raise Exception("Firestore client not available")
        
        db = get_firestore_client()
        if not db:
            raise Exception("Firestore client not available")
        
        update_task_progress(50, "Saving profile data...")
        
        # Generate profile ID if not present
        if 'profile_id' not in profile_data:
            profile_data['profile_id'] = f"profile_{int(time.time())}"
        
        # Add timestamps
        profile_data['created_at'] = datetime.now(timezone.utc).isoformat()
        profile_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Save to Firestore
        profile_ref = db.collection('userSiteProfiles').document(user_uid).collection('profiles').document(profile_data['profile_id'])
        profile_ref.set(profile_data)
        
        update_task_progress(100, "Profile saved successfully")
        
        result = {
            'success': True,
            'profile_id': profile_data['profile_id'],
            'message': 'Profile saved successfully'
        }
        
        logger.info(f"Profile save task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Profile save failed: {str(e)}"
        logger.error(f"Profile save task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=30, max_retries=3, exc=e)


@celery_app.task(bind=True, name='app.celery_tasks.firestore.get_user_site_profiles_task')
def get_user_site_profiles_task(self, user_uid: str, limit_profiles: int = 20) -> Dict[str, Any]:
    """
    Background task to get user site profiles from Firestore
    """
    task_id = self.request.id
    logger.info(f"Starting profile retrieval task {task_id} for user {user_uid}")
    
    try:
        update_task_progress(20, "Connecting to Firestore...")
        
        if not get_firestore_client:
            raise Exception("Firestore client not available")
        
        db = get_firestore_client()
        if not db:
            raise Exception("Firestore client not available")
        
        update_task_progress(50, "Retrieving profiles...")
        
        # Get profiles from Firestore
        profiles_ref = db.collection('userSiteProfiles').document(user_uid).collection('profiles')
        profiles_snap = profiles_ref.limit(limit_profiles).stream()
        
        profiles = []
        for doc in profiles_snap:
            profile_data = doc.to_dict()
            profile_data['profile_id'] = doc.id
            profiles.append(profile_data)
        
        update_task_progress(100, "Profiles retrieved successfully")
        
        result = {
            'success': True,
            'profiles': profiles,
            'count': len(profiles)
        }
        
        logger.info(f"Profile retrieval task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Profile retrieval failed: {str(e)}"
        logger.error(f"Profile retrieval task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=30, max_retries=2, exc=e)


@celery_app.task(bind=True, name='app.celery_tasks.automation.run_automation_task')
def run_automation_task(self, user_uid: str, profiles_data: List[Dict], 
                       articles_map: Dict[str, int], custom_tickers: Dict[str, List[str]] = None,
                       uploaded_file_details: Dict[str, Dict] = None) -> Dict[str, Any]:
    """
    Background task to run automation
    """
    task_id = self.request.id
    logger.info(f"Starting automation task {task_id} for user {user_uid}")
    
    try:
        update_task_progress(10, "Initializing automation...")
        
        # Import automation modules
        try:
            from automation_scripts import auto_publisher
        except ImportError as e:
            raise Exception(f"Automation module not available: {e}")
        
        update_task_progress(30, "Running automation pipeline...")
        
        # Run automation with progress updates
        def progress_callback(progress: int, message: str):
            update_task_progress(30 + int(progress * 0.6), message)
        
        # Call the automation publisher
        results = auto_publisher.trigger_publishing_run(
            user_uid=user_uid,
            profiles_to_process_data_list=profiles_data,
            articles_to_publish_per_profile_map=articles_map,
            custom_tickers_by_profile_id=custom_tickers or {},
            uploaded_file_details_by_profile_id=uploaded_file_details or {},
            socketio_instance=None,  # Will be handled separately
            user_room=user_uid,
            save_status_callback=lambda uid, pid, ticker, status: save_processed_ticker_status_task.delay(uid, pid, ticker, status)
        )
        
        update_task_progress(100, "Automation completed")
        
        result = {
            'success': True,
            'results': results,
            'task_id': task_id
        }
        
        logger.info(f"Automation task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Automation failed: {str(e)}"
        logger.error(f"Automation task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=60, max_retries=2, exc=e)


@celery_app.task(bind=True, name='app.celery_tasks.firestore.save_processed_ticker_status_task')
def save_processed_ticker_status_task(self, user_uid: str, profile_id: str, 
                                     ticker_symbol: str, status_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task to save processed ticker status
    """
    task_id = self.request.id
    logger.info(f"Starting ticker status save task {task_id} for {ticker_symbol}")
    
    try:
        if not get_firestore_client:
            raise Exception("Firestore client not available")
        
        db = get_firestore_client()
        if not db:
            raise Exception("Firestore client not available")
        
        # Add timestamp
        status_data['last_updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Save to Firestore
        status_ref = db.collection('userSiteProfiles').document(user_uid).collection('profiles').document(profile_id).collection('tickerStatuses').document(ticker_symbol)
        status_ref.set(status_data, merge=True)
        
        result = {
            'success': True,
            'ticker': ticker_symbol,
            'profile_id': profile_id
        }
        
        logger.info(f"Ticker status save task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Ticker status save failed: {str(e)}"
        logger.error(f"Ticker status save task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=30, max_retries=2, exc=e)


@celery_app.task(bind=True, name='app.celery_tasks.file_upload.delete_file_from_storage_task')
def delete_file_from_storage_task(self, storage_path: str) -> Dict[str, Any]:
    """
    Background task to delete file from Firebase Storage
    """
    task_id = self.request.id
    logger.info(f"Starting file deletion task {task_id} for {storage_path}")
    
    try:
        if not storage_path:
            return {'success': True, 'message': 'No storage path provided'}
        
        if not get_storage_bucket:
            raise Exception("Firebase Storage not available")
        
        bucket = get_storage_bucket()
        if not bucket:
            raise Exception("Storage bucket not available")
        
        blob = bucket.blob(storage_path)
        if blob.exists():
            blob.delete()
            message = f"File {storage_path} deleted successfully"
        else:
            message = f"File {storage_path} not found (already deleted or never existed)"
        
        result = {
            'success': True,
            'message': message,
            'storage_path': storage_path
        }
        
        logger.info(f"File deletion task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"File deletion failed: {str(e)}"
        logger.error(f"File deletion task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=30, max_retries=2, exc=e)


@celery_app.task(bind=True, name='app.celery_tasks.cache.update_ticker_cache_task')
def update_ticker_cache_task(self) -> Dict[str, Any]:
    """
    Background task to update ticker data cache
    """
    task_id = self.request.id
    logger.info(f"Starting ticker cache update task {task_id}")
    
    try:
        update_task_progress(20, "Loading ticker data...")
        
        ticker_file_path = os.path.join(PROJECT_ROOT, 'all-us-tickers.json')
        with open(ticker_file_path, 'r', encoding='utf-8') as f:
            import json
            ticker_data = json.load(f)
        
        update_task_progress(80, "Updating cache...")
        
        # Here you would update your cache (Redis, etc.)
        # For now, we'll just return the data
        result = {
            'success': True,
            'ticker_count': len(ticker_data),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        update_task_progress(100, "Cache updated successfully")
        logger.info(f"Ticker cache update task {task_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Cache update failed: {str(e)}"
        logger.error(f"Cache update task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise self.retry(countdown=60, max_retries=3, exc=e) 