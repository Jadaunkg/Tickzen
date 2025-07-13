"""
Task manager for handling background task status and progress tracking
"""
import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from flask import jsonify, request
from celery.result import AsyncResult

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import Celery app
from app.celery_config import celery_app
from app.async_utils import create_task_status

# Configure logging
logger = logging.getLogger(__name__)

# In-memory task cache (in production, use Redis)
_task_cache = {}


class TaskManager:
    """Manages background task status and progress"""
    
    def __init__(self):
        self.task_cache = _task_cache
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a Celery task
        
        Args:
            task_id: The Celery task ID
            
        Returns:
            Task status dictionary
        """
        try:
            # Get task result from Celery
            task_result = AsyncResult(task_id, app=celery_app)
            
            # Map Celery states to our states
            state_mapping = {
                'PENDING': 'PENDING',
                'STARTED': 'STARTED',
                'SUCCESS': 'SUCCESS',
                'FAILURE': 'FAILURE',
                'RETRY': 'RETRY',
                'REVOKED': 'FAILURE'
            }
            
            status = state_mapping.get(task_result.state, 'UNKNOWN')
            
            # Get progress and message from task info
            progress = 0
            message = ""
            result = None
            error = None
            
            if task_result.info:
                if isinstance(task_result.info, dict):
                    progress = task_result.info.get('current', 0)
                    message = task_result.info.get('status', '')
                    result = task_result.info.get('result')
                else:
                    result = task_result.info
            
            if task_result.failed():
                error = str(task_result.info)
            
            return create_task_status(
                task_id=task_id,
                status=status,
                progress=progress,
                message=message,
                result=result,
                error=error
            )
            
        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {e}")
            return create_task_status(
                task_id=task_id,
                status='FAILURE',
                error=str(e)
            )
    
    def get_user_tasks(self, user_uid: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all tasks for a specific user
        
        Args:
            user_uid: User ID
            limit: Maximum number of tasks to return
            
        Returns:
            List of task status dictionaries
        """
        try:
            # In a real implementation, you'd store task-user mappings in a database
            # For now, we'll return tasks from cache that match the user
            user_tasks = []
            
            for task_id, task_info in self.task_cache.items():
                if task_info.get('user_uid') == user_uid:
                    task_status = self.get_task_status(task_id)
                    user_tasks.append(task_status)
            
            # Sort by timestamp (newest first)
            user_tasks.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return user_tasks[:limit]
            
        except Exception as e:
            logger.error(f"Error getting user tasks for {user_uid}: {e}")
            return []
    
    def store_task_mapping(self, task_id: str, user_uid: str, task_type: str, 
                          metadata: Dict[str, Any] = None):
        """
        Store task-user mapping for tracking
        
        Args:
            task_id: Celery task ID
            user_uid: User ID
            task_type: Type of task (upload, automation, etc.)
            metadata: Additional metadata
        """
        try:
            self.task_cache[task_id] = {
                'user_uid': user_uid,
                'task_type': task_type,
                'metadata': metadata or {},
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Clean up old tasks (keep last 1000)
            if len(self.task_cache) > 1000:
                # Remove oldest tasks
                sorted_tasks = sorted(
                    self.task_cache.items(),
                    key=lambda x: x[1].get('created_at', '')
                )
                tasks_to_remove = sorted_tasks[:-1000]
                for task_id_to_remove, _ in tasks_to_remove:
                    del self.task_cache[task_id_to_remove]
                    
        except Exception as e:
            logger.error(f"Error storing task mapping for {task_id}: {e}")
    
    def cleanup_old_tasks(self, days_old: int = 7):
        """
        Clean up old completed tasks
        
        Args:
            days_old: Remove tasks older than this many days
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            tasks_to_remove = []
            
            for task_id, task_info in self.task_cache.items():
                created_at = task_info.get('created_at')
                if created_at:
                    try:
                        task_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if task_date < cutoff_date:
                            tasks_to_remove.append(task_id)
                    except ValueError:
                        # Invalid date format, remove the task
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.task_cache[task_id]
                
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
            
        except Exception as e:
            logger.error(f"Error cleaning up old tasks: {e}")


# Global task manager instance
task_manager = TaskManager()


def register_task_routes(app):
    """Register task-related routes with Flask app"""
    
    @app.route('/api/task-status/<task_id>', methods=['GET'])
    def get_task_status_route(task_id):
        """Get status of a specific task"""
        try:
            status = task_manager.get_task_status(task_id)
            return jsonify(status)
        except Exception as e:
            logger.error(f"Error in task status route: {e}")
            return jsonify({
                'error': 'Failed to get task status',
                'task_id': task_id
            }), 500
    
    @app.route('/api/user-tasks/<user_uid>', methods=['GET'])
    def get_user_tasks_route(user_uid):
        """Get all tasks for a user"""
        try:
            limit = request.args.get('limit', 50, type=int)
            tasks = task_manager.get_user_tasks(user_uid, limit)
            return jsonify({
                'tasks': tasks,
                'count': len(tasks),
                'user_uid': user_uid
            })
        except Exception as e:
            logger.error(f"Error in user tasks route: {e}")
            return jsonify({
                'error': 'Failed to get user tasks',
                'user_uid': user_uid
            }), 500
    
    @app.route('/api/task-cancel/<task_id>', methods=['POST'])
    def cancel_task_route(task_id):
        """Cancel a running task"""
        try:
            task_result = AsyncResult(task_id, app=celery_app)
            
            if task_result.state in ['PENDING', 'STARTED']:
                celery_app.control.revoke(task_id, terminate=True)
                return jsonify({
                    'success': True,
                    'message': 'Task cancelled successfully',
                    'task_id': task_id
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Cannot cancel task in state: {task_result.state}',
                    'task_id': task_id
                }), 400
                
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return jsonify({
                'error': 'Failed to cancel task',
                'task_id': task_id
            }), 500
    
    @app.route('/api/task-cleanup', methods=['POST'])
    def cleanup_tasks_route():
        """Clean up old completed tasks (admin only)"""
        try:
            days_old = request.json.get('days_old', 7) if request.is_json else 7
            task_manager.cleanup_old_tasks(days_old)
            return jsonify({
                'success': True,
                'message': f'Cleaned up tasks older than {days_old} days'
            })
        except Exception as e:
            logger.error(f"Error in task cleanup route: {e}")
            return jsonify({
                'error': 'Failed to cleanup tasks'
            }), 500


def create_task_with_tracking(task_func, user_uid: str, task_type: str, 
                            *args, **kwargs) -> str:
    """
    Create a Celery task and track it for a user
    
    Args:
        task_func: Celery task function
        user_uid: User ID
        task_type: Type of task
        *args: Arguments for the task
        **kwargs: Keyword arguments for the task
        
    Returns:
        Task ID
    """
    try:
        # Create the task
        task = task_func.delay(*args, **kwargs)
        task_id = task.id
        
        # Store task mapping
        task_manager.store_task_mapping(task_id, user_uid, task_type)
        
        logger.info(f"Created task {task_id} of type {task_type} for user {user_uid}")
        return task_id
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise


def get_task_progress(task_id: str) -> Dict[str, Any]:
    """
    Get task progress for WebSocket updates
    
    Args:
        task_id: Task ID
        
    Returns:
        Progress information
    """
    try:
        status = task_manager.get_task_status(task_id)
        return {
            'task_id': task_id,
            'status': status.get('status'),
            'progress': status.get('progress', 0),
            'message': status.get('message', ''),
            'error': status.get('error')
        }
    except Exception as e:
        logger.error(f"Error getting task progress for {task_id}: {e}")
        return {
            'task_id': task_id,
            'status': 'FAILURE',
            'progress': 0,
            'message': 'Error getting task status',
            'error': str(e)
        } 