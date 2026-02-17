import os
from datetime import datetime, timezone
import logging
from flask import current_app
from firebase_admin import firestore
from app.core.database import get_firestore_client

logger = logging.getLogger(__name__)

def get_report_history_for_user(user_uid, display_limit=10):
    """Get report history for a user with enhanced storage information (optimized)"""
    db = get_firestore_client()
    if not db:
        logger.error(f"Firestore client not available for fetching report history for user {user_uid}.")
        return [], 0

    reports_for_display = []
    total_user_reports_count = 0

    try:
        # Try to get counter from collection counter document, fallback to query if not available
        try:
            counter_doc = db.collection('_counters').document('userGeneratedReports').get()
            if counter_doc.exists:
                # The field name in main_portal_app was f'user_{user_uid}'
                data = counter_doc.to_dict()
                if data:
                    total_user_reports_count = data.get(f'user_{user_uid}', 0)
            else:
                # Fallback: estimate from query
                total_user_reports_count = 0
        except Exception as counter_err:
            logger.warning(f"Counter lookup failed, will estimate count: {counter_err}")
            total_user_reports_count = 0
        
        # Only fetch the latest N reports for display
        # Note: 'filter' keyword argument requires newer google-cloud-firestore
        # If 'filter' kwarg fails, use .where().where() chain
        try:
            base_query = db.collection(u'userGeneratedReports').where(filter=firestore.FieldFilter(u'user_uid', u'==', user_uid))
        except TypeError:
             base_query = db.collection(u'userGeneratedReports').where(u'user_uid', u'==', user_uid)

        # Fix for direction: in python client it is often Query.DESCENDING or string 'DESCENDING'
        # The main_app used direction='DESCENDING' string
        display_query = base_query.order_by(u'generated_at', direction=firestore.Query.DESCENDING).limit(display_limit)
        docs_for_display_stream = display_query.stream()
        
        for doc_snapshot in docs_for_display_stream:
            report_data = doc_snapshot.to_dict()
            report_data['id'] = doc_snapshot.id
            
            # Process generated_at timestamp
            generated_at_val = report_data.get('generated_at')
            if hasattr(generated_at_val, 'seconds'): # Timestamp object
                report_data['generated_at'] = datetime.fromtimestamp(generated_at_val.timestamp(), timezone.utc)
            elif isinstance(generated_at_val, (int, float)):
                if generated_at_val > 10**10:
                     # Milliseconds
                    report_data['generated_at'] = datetime.fromtimestamp(generated_at_val / 1000, timezone.utc)
                else:
                    report_data['generated_at'] = datetime.fromtimestamp(generated_at_val, timezone.utc)
            
            # Ensure filename is clean and determine storage info
            filename = report_data.get('filename')
            storage_type = report_data.get('storage_type', 'unknown')
            storage_path = report_data.get('storage_path')
            local_file_exists = report_data.get('local_file_exists', False)
            
            clean_filename = "unknown_report"
            if filename:
                # Clean the filename (ensure no path separators)
                clean_filename = os.path.basename(filename)
                report_data['filename'] = clean_filename
                
                # Determine content availability based on storage type (without verification)
                content_available = False
                storage_location = "Unknown"
                storage_details = {}
                
                if storage_type == 'firestore_content':
                    content_available = bool(report_data.get('html_content'))
                    storage_location = "Database (Direct)"
                    storage_details = {
                        'type': 'database_direct',
                        'size': len(report_data.get('html_content', '')) if content_available else 0
                    }
                elif storage_type == 'firestore_compressed':
                    content_available = bool(report_data.get('compressed_content'))
                    storage_location = "Database (Compressed)"
                    storage_details = {
                        'type': 'database_compressed',
                        'compression': report_data.get('compression_type', 'unknown'),
                        'compressed_size': len(report_data.get('compressed_content', '')) if content_available else 0
                    }
                elif storage_type == 'firebase_storage':
                    # Trust metadata - assume storage path exists if present
                    content_available = bool(storage_path)
                    storage_location = "Cloud Storage"
                    storage_details = {
                        'type': 'cloud_storage',
                        'path': storage_path
                    }
                elif storage_type == 'local_file_only':
                    # Trust metadata - file exists flag from last save
                    content_available = local_file_exists
                    storage_location = "Local File Only"
                    storage_details = {
                        'type': 'local_only',
                        'exists': local_file_exists
                    }
                else:
                    # Legacy handling or unknown storage type
                    if storage_path:
                        content_available = True
                        storage_location = "Cloud Storage (Legacy)"
                        storage_details = {
                            'type': 'cloud_storage_legacy',
                            'path': storage_path
                        }
                    elif local_file_exists:
                        content_available = True
                        storage_location = "Local File"
                        storage_details = {
                            'type': 'local_file',
                            'exists': content_available
                        }
                    else:
                        content_available = False
                        storage_location = "Missing"
                        storage_details = {
                            'type': 'missing'
                        }
                
                # Update report data with enhanced storage information
                report_data['file_exists'] = content_available
                report_data['content_available'] = content_available
                report_data['storage_location'] = storage_location
                report_data['storage_details'] = storage_details
                report_data['has_storage_path'] = bool(storage_path)
                
                if not content_available:
                   logger.debug(f"Report content missing for user {user_uid}: {clean_filename} (Storage Type: {storage_type})")
                
            reports_for_display.append(report_data)
        
        logger.info(f"Fetched {len(reports_for_display)} reports for user {user_uid} (Limit: {display_limit}, Total: {total_user_reports_count}).")
        return reports_for_display, total_user_reports_count
    except Exception as e:
        logger.error(f"Error fetching report history for user {user_uid}: {e}", exc_info=True)
        return [], 0
