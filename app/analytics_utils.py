import os
import sys
from datetime import datetime
from flask import current_app

# Import Firebase related functions
from config.firebase_admin_setup import get_firestore_client, get_firebase_app_initialized

# Don't import directly from main_portal_app to avoid circular imports
FIREBASE_INITIALIZED_SUCCESSFULLY = False  # Default value

def get_firebase_initialized_status():
    """Get the Firebase initialization status without causing circular imports"""
    try:
        from config.firebase_admin_setup import get_firebase_app_initialized
        return get_firebase_app_initialized()
    except ImportError:
        return FIREBASE_INITIALIZED_SUCCESSFULLY

def log_failed_analysis_attempt(user_uid, ticker, error_message):
    """Log failed analysis attempts to 'failed_analyses' collection for monitoring and analytics"""
    # Get current Firebase initialization status
    current_firebase_status = get_firebase_initialized_status()
    
    # Use current_app.logger if available, otherwise print
    if hasattr(current_app, 'logger'):
        logger = current_app.logger
    else:
        import logging
        logger = logging.getLogger(__name__)
    
    if not current_firebase_status:
        logger.warning("Firestore not available for logging failed analysis.")
        return False
    
    db = get_firestore_client()
    if not db:
        logger.warning("Firestore client not available for logging failed analysis.")
        return False
    
    try:
        # Get current timestamp
        now = datetime.now()
        timestamp = int(now.timestamp())
        
        # Create failure log document
        log_data = {
            'ticker': ticker.upper(),
            'timestamp': timestamp,
            'date': now,
            'user_id': user_uid,
            'error_message': error_message
        }
            
        # Save to Firestore 'failed_analyses' collection
        failed_analyses_collection = db.collection('failed_analyses')
        doc_ref = failed_analyses_collection.add(log_data)
        
        logger.info(f"Failed analysis logged for ticker {ticker}. Document ID: {doc_ref[1].id}")
        return True
        
    except Exception as e:
        logger.error(f"Error logging failed analysis for ticker {ticker}: {e}")
        return False

def save_report_metadata_for_analytics(user_uid, ticker, filename, generated_at_dt, file_size=0, file_path=None, storage_path=None):
    """Save report metadata to 'reports' collection for analytics purposes"""
    # Get current Firebase initialization status
    current_firebase_status = get_firebase_initialized_status()
    
    # Use current_app.logger if available, otherwise print
    if hasattr(current_app, 'logger'):
        logger = current_app.logger
    else:
        import logging
        logger = logging.getLogger(__name__)
    
    if not current_firebase_status:
        logger.warning("Firestore not available for saving report analytics metadata.")
        return False
    
    db = get_firestore_client()
    if not db:
        logger.warning("Firestore client not available for saving report analytics metadata.")
        return False
    
    try:
        # Convert timestamp for Firestore
        timestamp = int(generated_at_dt.timestamp())
        
        # Try to determine the sector for the ticker (you could expand this with a more complete mapping)
        sector_mapping = {
            'TSLA': 'Technology', 'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
            'AMZN': 'Consumer', 'NVDA': 'Technology', 'META': 'Technology', 'NFLX': 'Consumer',
            'JPM': 'Finance', 'JNJ': 'Healthcare', 'XOM': 'Energy', 'JSM': 'Other'
        }
        
        # Create analytics metadata document
        metadata = {
            'ticker': ticker.upper(),
            'timestamp': timestamp,
            'date': generated_at_dt,
            'filename': filename,
            'user_id': user_uid,
            'published': True,  # Assuming all reports are published by default
            'sector': sector_mapping.get(ticker.upper(), 'Other'),
            'file_size': file_size
        }
        
        # Add file path if provided
        if file_path:
            metadata['file_path'] = file_path
            
        # Add storage path if provided
        if storage_path:
            metadata['storage_path'] = storage_path
            
        # Save to Firestore 'reports' collection
        reports_collection = db.collection('reports')
        doc_ref = reports_collection.add(metadata)
        
        logger.info(f"Report analytics metadata saved for ticker {ticker}. Document ID: {doc_ref[1].id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving report analytics metadata for ticker {ticker}: {e}")
        return False
