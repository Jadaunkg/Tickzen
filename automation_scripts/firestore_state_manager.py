"""
Firestore state management module for WordPress publisher
This module replaces the pickle-based state management with Firestore-based state
to ensure persistence across container restarts in Azure App Service.
"""
import os
import pickle
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Configure logger
logger = logging.getLogger("FirestoreStateManager")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    logger.propagate = True  # Let the parent logger handle output

# Import Firestore client
try:
    from config.firebase_admin_setup import get_firestore_client
except ImportError:
    logger.error("Failed to import get_firestore_client from firebase_admin_setup")
    get_firestore_client = lambda: None

class FirestoreStateManager:
    """Manages WordPress publisher state in Firestore"""
    
    def __init__(self):
        """Initialize the Firestore state manager"""
        self.db = None
        
    def _get_db(self):
        """Get or initialize the Firestore client"""
        if self.db is None:
            self.db = get_firestore_client()
            if self.db is None:
                logger.error("Firestore client not available")
        return self.db
    
    def _create_default_state(self, profile_ids=None):
        """Create default state structure"""
        profile_ids = profile_ids or []
        profile_ids = [str(pid) for pid in profile_ids]
        
        default_factories = {
            'pending_tickers_by_profile': list, 
            'failed_tickers_by_profile': list,
            'last_successful_schedule_time_by_profile': lambda: None,
            'posts_today_by_profile': lambda: 0, 
            'published_tickers_log_by_profile': list,  # Changed from set to list for Firestore
            'processed_tickers_detailed_log_by_profile': list,
            'last_author_index_by_profile': lambda: -1,
            'last_processed_ticker_index_by_profile': lambda: -1,
            'ticker_publish_count_by_profile': lambda: {}  # Track variations per ticker per profile
        }
        
        state = {}
        for key, factory in default_factories.items():
            state[key] = {}
            for pid in profile_ids:
                state[key][pid] = factory() if callable(factory) else factory
                
        state['last_run_date'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # No global tracker needed - we track variations per profile
        
        return state
    
    def load_state_from_firestore(self, user_uid, profile_ids=None):
        """Load WordPress publisher state from Firestore"""
        db = self._get_db()
        if not db:
            logger.error("Firestore client not available for loading state")
            return self._create_default_state(profile_ids)
            
        try:
            # Get state document
            state_doc_ref = db.collection('wordpress_publisher_state').document(user_uid)
            state_doc = state_doc_ref.get()
            
            if state_doc.exists:
                state_data = state_doc.to_dict()
                
                # Handle profile_ids that might not be in the state yet
                if profile_ids:
                    default_state = self._create_default_state(profile_ids)
                    for key in default_state:
                        if key == 'last_run_date':
                            continue
                        if key not in state_data:
                            state_data[key] = {}
                        for pid in profile_ids:
                            pid_str = str(pid)
                            if pid_str not in state_data[key]:
                                state_data[key][pid_str] = default_state[key][pid_str]
                
                # Convert lists back to sets for 'published_tickers_log_by_profile'
                if 'published_tickers_log_by_profile' in state_data:
                    for pid, tickers in state_data['published_tickers_log_by_profile'].items():
                        state_data['published_tickers_log_by_profile'][pid] = set(tickers)
                
                # Ensure ticker_publish_count_by_profile exists
                if 'ticker_publish_count_by_profile' not in state_data:
                    state_data['ticker_publish_count_by_profile'] = {str(pid): {} for pid in profile_ids} if profile_ids else {}
                
                logger.info(f"Loaded state from Firestore for user {user_uid}")
                
                # Check if we need to reset daily counts
                current_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                if state_data.get('last_run_date') != current_date_str:
                    logger.info(f"New day ({current_date_str}). Resetting daily counts and processed logs.")
                    for pid_in_state in list(state_data.get('posts_today_by_profile', {}).keys()):
                        state_data['posts_today_by_profile'][pid_in_state] = 0
                    for pid_in_state in list(state_data.get('processed_tickers_detailed_log_by_profile', {}).keys()):
                        state_data['processed_tickers_detailed_log_by_profile'][pid_in_state] = []
                    # Reset ticker publish counts for new day (allow fresh variations)
                    for pid_in_state in list(state_data.get('ticker_publish_count_by_profile', {}).keys()):
                        state_data['ticker_publish_count_by_profile'][pid_in_state] = {}
                    state_data['last_run_date'] = current_date_str
                    # Save the updated state back to Firestore
                    self.save_state_to_firestore(user_uid, state_data)
                
                return state_data
            else:
                # Create default state
                default_state = self._create_default_state(profile_ids)
                logger.info(f"No existing state in Firestore for user {user_uid}, creating default")
                state_doc_ref.set(default_state)
                return default_state
        except Exception as e:
            logger.error(f"Error loading state from Firestore: {e}", exc_info=True)
            return self._create_default_state(profile_ids)
    
    def save_state_to_firestore(self, user_uid, state):
        """Save WordPress publisher state to Firestore"""
        db = self._get_db()
        if not db:
            logger.error("Firestore client not available for saving state")
            return False
            
        try:
            # Sanitize state data (ensure all values are Firestore-compatible)
            sanitized_state = self._sanitize_state_for_firestore(state)
            
            # Save state document
            state_doc_ref = db.collection('wordpress_publisher_state').document(user_uid)
            state_doc_ref.set(sanitized_state, merge=True)
            logger.info(f"Saved state to Firestore for user {user_uid}")
            return True
        except Exception as e:
            logger.error(f"Error saving state to Firestore: {e}", exc_info=True)
            return False
    
    def _sanitize_state_for_firestore(self, state):
        """Ensure all values in state are Firestore-compatible"""
        # Convert sets to lists for Firestore compatibility
        sanitized_state = {}
        for key, value in state.items():
            if isinstance(value, dict):
                sanitized_state[key] = self._sanitize_state_for_firestore(value)
            elif isinstance(value, set):
                sanitized_state[key] = list(value)
            else:
                sanitized_state[key] = value
        return sanitized_state
    
    # Migration functionality removed as it's not needed

# Create a singleton instance
firestore_state_manager = FirestoreStateManager()
