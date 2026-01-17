"""
Job Portal Automation State Manager
====================================

Handles state persistence, tracking, and recovery for job automation runs.
Integrates with Firestore for cloud storage and local JSON files for backup.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class RunStatus(Enum):
    """Job automation run status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class JobPublishingStateManager:
    """
    Manages state for job portal automation runs.
    
    Features:
    - Local JSON-based state backup
    - Firestore integration (when available)
    - Run history tracking
    - Progress monitoring
    - Error recovery
    """
    
    def __init__(self, local_state_dir: Optional[str] = None,
                 use_firestore: bool = True):
        """
        Initialize state manager
        
        Args:
            local_state_dir: Directory for local state files (default: Job_Portal_Automation/data)
            use_firestore: Whether to use Firestore integration (default: True)
        """
        # Set up local state directory
        if local_state_dir is None:
            # Try to find Job_Portal_Automation directory
            current_dir = Path(__file__).parent.parent
            self.local_state_dir = current_dir / "data"
        else:
            self.local_state_dir = Path(local_state_dir)
        
        self.local_state_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"State directory: {self.local_state_dir}")
        
        # Initialize Firestore if available
        self.use_firestore = use_firestore
        self.firestore_client = None
        self.db = None
        
        if use_firestore:
            self._init_firestore()
    
    def _init_firestore(self):
        """Initialize Firestore connection"""
        try:
            import firebase_admin
            from firebase_admin import firestore, credentials
            
            # Check if Firebase app is already initialized
            try:
                self.db = firestore.client()
                logger.info("✅ Firestore initialized (existing Firebase app)")
            except ValueError:
                # Firebase not initialized, try to initialize
                logger.warning("Firebase app not initialized, skipping Firestore integration")
                self.db = None
                self.use_firestore = False
        
        except ImportError:
            logger.warning("Firebase admin SDK not installed. Using local state only.")
            self.use_firestore = False
            self.db = None
    
    def create_run(self, user_uid: str, content_type: str,
                   selected_items: List[Dict],
                   target_profiles: List[str],
                   config: Optional[Dict] = None) -> str:
        """
        Create a new automation run
        
        Args:
            user_uid: Firebase user ID
            content_type: Type of content ("jobs", "results", "admit_cards")
            selected_items: List of selected items to process
            target_profiles: List of WordPress profiles to publish to
            config: Optional configuration for the run
            
        Returns:
            Run ID
        """
        run_id = self._generate_run_id()
        
        run_data = {
            'run_id': run_id,
            'user_uid': user_uid,
            'timestamp': datetime.now().isoformat(),
            'content_type': content_type,
            'selected_items': selected_items,
            'target_profiles': target_profiles,
            'config': config or {},
            'status': RunStatus.PENDING.value,
            'progress': {
                'total': len(selected_items),
                'completed': 0,
                'failed': 0,
                'current_item': None
            },
            'results': [],
            'errors': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Save locally
        self._save_local_run(run_id, run_data)
        
        # Save to Firestore if available
        if self.db:
            self._save_firestore_run(run_id, run_data)
        
        logger.info(f"✅ Created run {run_id}")
        return run_id
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run data"""
        # Try Firestore first
        if self.db:
            try:
                doc = self.db.collection('job_automation_runs').document(run_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.warning(f"Failed to fetch from Firestore: {e}")
        
        # Fallback to local storage
        return self._load_local_run(run_id)
    
    def update_run_status(self, run_id: str, status: RunStatus) -> bool:
        """Update run status"""
        run_data = self.get_run(run_id)
        if not run_data:
            logger.error(f"Run {run_id} not found")
            return False
        
        run_data['status'] = status.value
        run_data['updated_at'] = datetime.now().isoformat()
        
        if status == RunStatus.COMPLETED:
            run_data['completed_at'] = datetime.now().isoformat()
        
        return self._save_run(run_id, run_data)
    
    def update_run_progress(self, run_id: str, 
                           completed: int, failed: int,
                           current_item: Optional[str] = None) -> bool:
        """Update run progress"""
        run_data = self.get_run(run_id)
        if not run_data:
            logger.error(f"Run {run_id} not found")
            return False
        
        run_data['progress']['completed'] = completed
        run_data['progress']['failed'] = failed
        run_data['progress']['current_item'] = current_item
        run_data['updated_at'] = datetime.now().isoformat()
        
        return self._save_run(run_id, run_data)
    
    def add_run_result(self, run_id: str, item_id: str, 
                      item_title: str, published_url: str,
                      profile_name: str) -> bool:
        """Add a successful publishing result"""
        run_data = self.get_run(run_id)
        if not run_data:
            logger.error(f"Run {run_id} not found")
            return False
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'item_id': item_id,
            'item_title': item_title,
            'published_url': published_url,
            'profile_name': profile_name,
            'status': 'success'
        }
        
        run_data['results'].append(result)
        run_data['updated_at'] = datetime.now().isoformat()
        
        return self._save_run(run_id, run_data)
    
    def add_run_error(self, run_id: str, item_id: str,
                     item_title: str, error_message: str,
                     step: str = "unknown") -> bool:
        """Add an error to the run"""
        run_data = self.get_run(run_id)
        if not run_data:
            logger.error(f"Run {run_id} not found")
            return False
        
        error = {
            'timestamp': datetime.now().isoformat(),
            'item_id': item_id,
            'item_title': item_title,
            'error_message': error_message,
            'step': step
        }
        
        run_data['errors'].append(error)
        run_data['updated_at'] = datetime.now().isoformat()
        
        return self._save_run(run_id, run_data)
    
    def get_run_history(self, user_uid: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get run history for a user"""
        # Try Firestore first
        if self.db:
            try:
                docs = (self.db.collection('job_automation_runs')
                        .where('user_uid', '==', user_uid)
                        .order_by('timestamp', direction='DESCENDING')
                        .limit(limit)
                        .stream())
                
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                logger.warning(f"Failed to fetch history from Firestore: {e}")
        
        # Fallback to local storage
        return self._get_local_run_history(user_uid, limit)
    
    def get_statistics(self, user_uid: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for job automation"""
        stats = {
            'total_runs': 0,
            'completed_runs': 0,
            'failed_runs': 0,
            'total_published': 0,
            'by_content_type': {
                'jobs': 0,
                'results': 0,
                'admit_cards': 0
            },
            'success_rate': 0.0
        }
        
        # Try Firestore first
        if self.db:
            try:
                query = self.db.collection('job_automation_runs')
                if user_uid:
                    query = query.where('user_uid', '==', user_uid)
                
                docs = list(query.stream())
                
                if not docs:
                    return stats
                
                stats['total_runs'] = len(docs)
                
                for doc in docs:
                    data = doc.to_dict()
                    
                    if data.get('status') == 'completed':
                        stats['completed_runs'] += 1
                    elif data.get('status') == 'failed':
                        stats['failed_runs'] += 1
                    
                    stats['total_published'] += len(data.get('results', []))
                    
                    content_type = data.get('content_type')
                    if content_type in stats['by_content_type']:
                        stats['by_content_type'][content_type] += 1
                
                if stats['total_runs'] > 0:
                    stats['success_rate'] = (
                        stats['completed_runs'] / stats['total_runs'] * 100
                    )
                
                return stats
            except Exception as e:
                logger.warning(f"Failed to fetch stats from Firestore: {e}")
        
        # Fallback to local storage
        return self._get_local_statistics(user_uid)
    
    def _save_run(self, run_id: str, run_data: Dict) -> bool:
        """Save run data (both local and Firestore)"""
        # Save locally
        self._save_local_run(run_id, run_data)
        
        # Save to Firestore if available
        if self.db:
            return self._save_firestore_run(run_id, run_data)
        
        return True
    
    def _save_local_run(self, run_id: str, run_data: Dict) -> bool:
        """Save run data to local JSON file"""
        try:
            run_file = self.local_state_dir / f"{run_id}.json"
            
            with open(run_file, 'w', encoding='utf-8') as f:
                json.dump(run_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved run {run_id} to local storage")
            return True
        except Exception as e:
            logger.error(f"Failed to save local run {run_id}: {e}")
            return False
    
    def _load_local_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load run data from local JSON file"""
        try:
            run_file = self.local_state_dir / f"{run_id}.json"
            
            if not run_file.exists():
                logger.warning(f"Local run file not found: {run_id}")
                return None
            
            with open(run_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"Loaded run {run_id} from local storage")
            return data
        except Exception as e:
            logger.error(f"Failed to load local run {run_id}: {e}")
            return None
    
    def _save_firestore_run(self, run_id: str, run_data: Dict) -> bool:
        """Save run data to Firestore"""
        try:
            self.db.collection('job_automation_runs').document(run_id).set(run_data)
            logger.debug(f"Saved run {run_id} to Firestore")
            return True
        except Exception as e:
            logger.error(f"Failed to save run to Firestore {run_id}: {e}")
            return False
    
    def _get_local_run_history(self, user_uid: str, limit: int) -> List[Dict[str, Any]]:
        """Get run history from local files"""
        try:
            runs = []
            
            for run_file in sorted(
                self.local_state_dir.glob("*.json"),
                key=os.path.getctime,
                reverse=True
            ):
                if len(runs) >= limit:
                    break
                
                try:
                    with open(run_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if data.get('user_uid') == user_uid:
                        runs.append(data)
                except Exception as e:
                    logger.warning(f"Failed to load {run_file}: {e}")
            
            return runs
        except Exception as e:
            logger.error(f"Failed to get local run history: {e}")
            return []
    
    def _get_local_statistics(self, user_uid: Optional[str]) -> Dict[str, Any]:
        """Get statistics from local files"""
        stats = {
            'total_runs': 0,
            'completed_runs': 0,
            'failed_runs': 0,
            'total_published': 0,
            'by_content_type': {
                'jobs': 0,
                'results': 0,
                'admit_cards': 0
            },
            'success_rate': 0.0
        }
        
        try:
            for run_file in self.local_state_dir.glob("*.json"):
                try:
                    with open(run_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if user_uid and data.get('user_uid') != user_uid:
                        continue
                    
                    stats['total_runs'] += 1
                    
                    if data.get('status') == 'completed':
                        stats['completed_runs'] += 1
                    elif data.get('status') == 'failed':
                        stats['failed_runs'] += 1
                    
                    stats['total_published'] += len(data.get('results', []))
                    
                    content_type = data.get('content_type')
                    if content_type in stats['by_content_type']:
                        stats['by_content_type'][content_type] += 1
                
                except Exception as e:
                    logger.warning(f"Failed to process {run_file}: {e}")
            
            if stats['total_runs'] > 0:
                stats['success_rate'] = (
                    stats['completed_runs'] / stats['total_runs'] * 100
                )
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get local statistics: {e}")
            return stats
    
    @staticmethod
    def _generate_run_id() -> str:
        """Generate a unique run ID"""
        import uuid
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"run_{timestamp}_{unique_id}"
