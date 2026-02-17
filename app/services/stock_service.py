import logging
import time
import os
import gzip
import base64
from datetime import datetime, timezone

from firebase_admin import firestore
from app.services.quota_service import get_quota_service, QuotaExceededException
from app.models.quota_models import ResourceType
from app.core.database import get_firestore_client
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Pipeline state
PIPELINE_AVAILABLE = False
PIPELINE_IMPORT_ERROR = None
_RUN_PIPELINE = None


def _load_pipeline():
    """Lazy-load the stock analysis pipeline to avoid heavy imports at startup."""
    global PIPELINE_AVAILABLE, PIPELINE_IMPORT_ERROR, _RUN_PIPELINE
    if _RUN_PIPELINE:
        return _RUN_PIPELINE
    try:
        from automation_scripts.pipeline import run_pipeline
        _RUN_PIPELINE = run_pipeline
        PIPELINE_AVAILABLE = True
        PIPELINE_IMPORT_ERROR = None
        logger.info("Stock analysis pipeline loaded successfully.")
        return _RUN_PIPELINE
    except Exception as exc:
        PIPELINE_AVAILABLE = False
        PIPELINE_IMPORT_ERROR = str(exc)
        logger.error("Failed to import stock analysis pipeline: %s", exc, exc_info=True)
        return None


# Executor for running analysis in background
analysis_executor = ThreadPoolExecutor(max_workers=3)


def run_pipeline_task(ticker, socketio_instance, task_room, user_uid, app_root):
    """
    Execute the stock analysis pipeline in a background thread.
    """
    run_pipeline = _load_pipeline()
    if not run_pipeline:
        if socketio_instance:
            socketio_instance.emit('analysis_error', {
                'message': 'Stock Analysis service is temporarily unavailable (pipeline not loaded).',
                'ticker': ticker
            }, room=task_room)
        return

    logger.info("Starting stock analysis task for %s in room %s", ticker, task_room)

    try:
        request_ts = str(int(time.time()))
        result = run_pipeline(
            ticker,
            request_ts,
            app_root,
            socketio_instance=socketio_instance,
            task_room=task_room
        )

        if result is None:
            logger.warning("Pipeline returned no result for %s", ticker)
            return

        report_path = None
        report_html = None
        if isinstance(result, (list, tuple)) and len(result) >= 4:
            report_path = result[2]
            report_html = result[3]

        if socketio_instance:
            socketio_instance.emit('analysis_progress', {
                'stage': 'complete',
                'progress': 100,
                'message': f'Analysis completed for {ticker}'
            }, room=task_room)

            if report_path:
                filename = os.path.basename(report_path)
                report_url = f"/report/{ticker}/{filename}"
                socketio_instance.emit('analysis_complete', {
                    'ticker': ticker,
                    'report_url': report_url
                }, room=task_room)
            elif report_html:
                socketio_instance.emit('analysis_error', {
                    'message': 'Report generated but could not be saved for viewing.',
                    'ticker': ticker
                }, room=task_room)

        if user_uid and report_path:
            try:
                db = get_firestore_client()
                if db:
                    filename = os.path.basename(report_path)
                    storage_type = 'local_file_only'
                    html_content = None
                    compressed_content = None
                    compression_type = None

                    if report_html and isinstance(report_html, str):
                        content_size = len(report_html.encode('utf-8'))
                        if content_size < 900000:
                            storage_type = 'firestore_content'
                            html_content = report_html
                        else:
                            compressed = gzip.compress(report_html.encode('utf-8'))
                            encoded = base64.b64encode(compressed).decode('utf-8')
                            if len(encoded.encode('utf-8')) < 900000:
                                storage_type = 'firestore_compressed'
                                compressed_content = encoded
                                compression_type = 'gzip_base64'

                    report_doc = {
                        'user_uid': user_uid,
                        'ticker': ticker,
                        'filename': filename,
                        'generated_at': firestore.SERVER_TIMESTAMP,
                        'timestamp': int(time.time()),
                        'storage_type': storage_type,
                        'compression_type': compression_type,
                        'html_content': html_content,
                        'compressed_content': compressed_content,
                        'local_file_exists': True,
                        'status': 'completed'
                    }
                    db.collection('userGeneratedReports').add(report_doc)
                else:
                    logger.error("Firestore client unavailable; report not saved for %s", user_uid)
            except Exception as exc:
                logger.error("Failed to save report history for %s: %s", user_uid, exc, exc_info=True)

            try:
                quota_service = get_quota_service()
                quota_service.consume_quota(
                    user_uid,
                    ResourceType.STOCK_REPORT.value,
                    {
                        'ticker': ticker,
                        'status': 'success',
                        'report_id': filename,
                        'generation_time_ms': None
                    }
                )
                logger.info("Quota consumed for user %s - ticker %s", user_uid, ticker)
            except QuotaExceededException as exc:
                logger.warning("Quota exceeded during consumption for %s: %s", user_uid, exc)
            except Exception as exc:
                logger.error("Failed to consume quota for %s: %s", user_uid, exc, exc_info=True)

    except Exception as exc:
        logger.error("Error in analysis pipeline for %s: %s", ticker, exc, exc_info=True)
        if socketio_instance:
            socketio_instance.emit('analysis_error', {
                'message': f"Analysis failed: {str(exc)}",
                'ticker': ticker
            }, room=task_room)


def start_stock_analysis_service(ticker, user_uid, socketio_instance, task_room, app_root):
    """
    Service entry point to start analysis.
    Validates pipeline availability and submits task.
    """
    run_pipeline = _load_pipeline()
    if not run_pipeline:
        logger.error("Pipeline not available: %s", PIPELINE_IMPORT_ERROR)
        return False, "Analysis service unavailable"

    analysis_executor.submit(
        run_pipeline_task,
        ticker,
        socketio_instance,
        task_room,
        user_uid,
        app_root
    )

    return True, "Analysis started"
