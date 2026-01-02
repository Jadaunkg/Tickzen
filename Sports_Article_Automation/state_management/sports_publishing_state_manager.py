"""
Sports Article Publishing State Manager

Handles article publishing state with dual persistence:
- Primary: Firestore (for cloud/containerized deployments)
- Fallback: Pickle file (for local development)

State tracked:
- Pending/queued articles
- Published articles log
- Failed articles
- Daily article count
- Processing history
"""
import os
import pickle
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("SportsPublishingStateManager")

# Try to import Firestore state manager
try:
    from .sports_firestore_state_manager import sports_firestore_state_manager
    FIRESTORE_STATE_AVAILABLE = True
except ImportError:
    FIRESTORE_STATE_AVAILABLE = False
    logger.warning("Firestore state manager not available, will use pickle file only")


class SportsPublishingStateManager:
    """Manages sports article publishing state with Firestore/pickle persistence"""
    
    def __init__(self, pickle_file_path: Optional[str] = None):
        """
        Initialize state manager
        
        Args:
            pickle_file_path: Path to pickle file for state backup/fallback
        """
        if pickle_file_path is None:
            # Default location relative to Sports Article Automation folder
            base_dir = Path(__file__).parent.parent
            pickle_file_path = base_dir / "state" / "sports_publishing_state.pkl"
        
        self.pickle_file = pickle_file_path
        os.makedirs(os.path.dirname(self.pickle_file), exist_ok=True)
    
    def load_state(self, user_uid: Optional[str] = None, 
                   profile_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Load publishing state from Firestore or pickle file
        
        Args:
            user_uid: User ID for Firestore lookup
            profile_ids: List of profile IDs to include in state
            
        Returns:
            Dict: Current publishing state
        """
        # Use Firestore if available and user_uid provided
        if FIRESTORE_STATE_AVAILABLE and user_uid:
            logger.info(f"Loading sports article state from Firestore for user {user_uid}")
            return sports_firestore_state_manager.load_state_from_firestore(
                user_uid, 
                profile_ids=profile_ids
            )
        
        # Fall back to pickle file
        logger.info(f"Loading sports article state from pickle file: {self.pickle_file}")
        return self._load_state_from_pickle(profile_ids)
    
    def save_state(self, state: Dict[str, Any], 
                   user_uid: Optional[str] = None) -> bool:
        """
        Save publishing state to Firestore or pickle file
        
        Args:
            state: State dictionary to save
            user_uid: User ID for Firestore
            
        Returns:
            bool: True if save successful
        """
        # Try Firestore first if available and user_uid provided
        if FIRESTORE_STATE_AVAILABLE and user_uid:
            success = sports_firestore_state_manager.save_state_to_firestore(user_uid, state)
            if success:
                logger.info(f"Saved sports article state to Firestore for user {user_uid}")
                return True
            else:
                logger.warning("Firestore save failed, falling back to pickle file")
        
        # Fall back to pickle file
        return self._save_state_to_pickle(state)
    
    def _load_state_from_pickle(self, profile_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Load state from pickle file with fallback to defaults"""
        default_state = self._create_default_state(profile_ids)
        
        if not os.path.exists(self.pickle_file):
            logger.info(f"No existing state file at {self.pickle_file}, creating default")
            return default_state
        
        try:
            with open(self.pickle_file, 'rb') as f:
                state = pickle.load(f)
            logger.info(f"Loaded sports article state from pickle: {self.pickle_file}")
            
            # Ensure all required keys exist
            for key in default_state:
                if key not in state:
                    state[key] = default_state[key]
            
            # Check if we need to reset daily counts
            current_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            if state.get('last_run_date') != current_date_str:
                logger.info(f"New day ({current_date_str}). Resetting daily article counts.")
                for pid in state.get('articles_today_by_profile', {}):
                    state['articles_today_by_profile'][pid] = 0
                for pid in state.get('processed_articles_detailed_log_by_profile', {}):
                    state['processed_articles_detailed_log_by_profile'][pid] = []
                for pid in state.get('article_publish_count_by_profile', {}):
                    state['article_publish_count_by_profile'][pid] = {}
                state['last_run_date'] = current_date_str
            
            return state
        except Exception as e:
            logger.error(f"Error loading pickle state: {e}, using default", exc_info=True)
            return default_state
    
    def _save_state_to_pickle(self, state: Dict[str, Any]) -> bool:
        """Save state to pickle file"""
        try:
            os.makedirs(os.path.dirname(self.pickle_file), exist_ok=True)
            with open(self.pickle_file, 'wb') as f:
                pickle.dump(state, f)
            logger.info(f"Saved sports article state to pickle: {self.pickle_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving pickle state: {e}", exc_info=True)
            return False
    
    def _create_default_state(self, profile_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create default state structure"""
        profile_ids = [str(pid) for pid in profile_ids] if profile_ids else []
        
        default_factories = {
            'pending_articles_by_profile': list,  # Queue of articles waiting to publish
            'failed_articles_by_profile': list,   # Articles that failed generation
            'last_successful_schedule_time_by_profile': lambda: None,
            'articles_today_by_profile': lambda: 0,  # Count published today
            'published_articles_log_by_profile': list,  # Published article titles
            'processed_articles_detailed_log_by_profile': list,  # Processing history
            'last_article_index_by_profile': lambda: -1,  # Last processed article index
            'article_publish_count_by_profile': lambda: {}  # Variation tracking
        }
        
        state = {}
        for key, factory in default_factories.items():
            state[key] = {}
            for pid in profile_ids:
                state[key][pid] = factory() if callable(factory) else factory
        
        state['last_run_date'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        return state
    
    def add_article_to_queue(self, state: Dict[str, Any], 
                            profile_id: str, article: Dict[str, Any]) -> None:
        """Add article to processing queue"""
        pid_str = str(profile_id)
        if 'pending_articles_by_profile' not in state:
            state['pending_articles_by_profile'] = {}
        if pid_str not in state['pending_articles_by_profile']:
            state['pending_articles_by_profile'][pid_str] = []
        
        state['pending_articles_by_profile'][pid_str].append(article)
        logger.info(f"Added article '{article.get('title', 'Unknown')}' to queue for profile {profile_id}")
    
    def mark_article_published(self, state: Dict[str, Any], 
                              profile_id: str, article_title: str,
                              wordpress_post_id: Optional[int] = None) -> None:
        """Mark article as published"""
        pid_str = str(profile_id)
        
        if 'published_articles_log_by_profile' not in state:
            state['published_articles_log_by_profile'] = {}
        if pid_str not in state['published_articles_log_by_profile']:
            state['published_articles_log_by_profile'][pid_str] = []
        
        article_log = {
            'title': article_title,
            'wordpress_post_id': wordpress_post_id,
            'published_at': datetime.now(timezone.utc).isoformat()
        }
        state['published_articles_log_by_profile'][pid_str].append(article_log)
        
        # Increment daily count
        if 'articles_today_by_profile' not in state:
            state['articles_today_by_profile'] = {}
        if pid_str not in state['articles_today_by_profile']:
            state['articles_today_by_profile'][pid_str] = 0
        state['articles_today_by_profile'][pid_str] += 1
        
        logger.info(f"Marked article '{article_title}' as published (Post ID: {wordpress_post_id}) for profile {profile_id}")
    
    def mark_article_failed(self, state: Dict[str, Any], 
                           profile_id: str, article_title: str, 
                           reason: str) -> None:
        """Mark article as failed"""
        pid_str = str(profile_id)
        
        if 'failed_articles_by_profile' not in state:
            state['failed_articles_by_profile'] = {}
        if pid_str not in state['failed_articles_by_profile']:
            state['failed_articles_by_profile'][pid_str] = []
        
        article_fail_log = {
            'title': article_title,
            'reason': reason,
            'failed_at': datetime.now(timezone.utc).isoformat()
        }
        state['failed_articles_by_profile'][pid_str].append(article_fail_log)
        logger.warning(f"Marked article '{article_title}' as failed: {reason}")
    
    def log_processing_detail(self, state: Dict[str, Any], 
                             profile_id: str, article_title: str,
                             status: str, message: str) -> None:
        """Log detailed processing information"""
        pid_str = str(profile_id)
        
        if 'processed_articles_detailed_log_by_profile' not in state:
            state['processed_articles_detailed_log_by_profile'] = {}
        if pid_str not in state['processed_articles_detailed_log_by_profile']:
            state['processed_articles_detailed_log_by_profile'][pid_str] = []
        
        log_entry = {
            'article_title': article_title,
            'status': status,  # 'queued', 'in_progress', 'published', 'failed'
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        state['processed_articles_detailed_log_by_profile'][pid_str].append(log_entry)
    
    def get_article_count_today(self, state: Dict[str, Any], profile_id: str) -> int:
        """Get number of articles published today for a profile"""
        pid_str = str(profile_id)
        return state.get('articles_today_by_profile', {}).get(pid_str, 0)
    
    def get_published_articles(self, state: Dict[str, Any], profile_id: str) -> List[Dict]:
        """Get list of published articles for a profile"""
        pid_str = str(profile_id)
        return state.get('published_articles_log_by_profile', {}).get(pid_str, [])
    
    def get_failed_articles(self, state: Dict[str, Any], profile_id: str) -> List[Dict]:
        """Get list of failed articles for a profile"""
        pid_str = str(profile_id)
        return state.get('failed_articles_by_profile', {}).get(pid_str, [])
    
    def get_processing_history(self, state: Dict[str, Any], profile_id: str) -> List[Dict]:
        """Get processing history for a profile"""
        pid_str = str(profile_id)
        return state.get('processed_articles_detailed_log_by_profile', {}).get(pid_str, [])
