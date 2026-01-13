"""
Shared Decorators for TickZen Application
=========================================

This module provides decorators for authentication and quota management.
"""

from functools import wraps
from flask import session, jsonify, redirect, url_for
import logging

logger = logging.getLogger(__name__)


def require_quota(resource_type):
    """
    Decorator to check quota before route execution
    
    Args:
        resource_type: Type of resource (e.g., 'stock_report')
    
    Usage:
        @app.route('/start-analysis', methods=['POST'])
        @require_quota(ResourceType.STOCK_REPORT.value)
        def start_analysis():
            # Your route logic here
            pass
    
    Returns:
        - If quota available: Executes the decorated function
        - If quota exceeded: Returns 403 error with quota info
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                from app.services.quota_service import get_quota_service
                from app.models.quota_models import ResourceType
                
                # Get user ID from session
                user_uid = session.get('firebase_user_uid')
                
                # Allow anonymous users to proceed (they won't have quota tracking)
                if not user_uid:
                    logger.warning(f"Anonymous user accessing {f.__name__}, skipping quota check")
                    return f(*args, **kwargs)
                
                # Get quota service
                quota_service = get_quota_service()
                
                # Check quota
                has_quota, quota_info = quota_service.check_quota(
                    user_uid, 
                    resource_type
                )
                
                if not has_quota:
                    logger.warning(f"Quota exceeded for user {user_uid}: {quota_info}")
                    
                    # Return JSON error for API calls
                    return jsonify({
                        'error': 'quota_exceeded',
                        'message': f"You've used all {quota_info.get('limit', 0)} reports this month.",
                        'quota_info': {
                            'limit': quota_info.get('limit', 0),
                            'used': quota_info.get('used', 0),
                            'remaining': quota_info.get('remaining', 0),
                            'period_end': quota_info.get('period_end', ''),
                            'plan_type': quota_info.get('plan_type', 'free')
                        },
                        'upgrade_url': '/pricing',
                        'current_plan': quota_info.get('plan_type', 'free')
                    }), 403
                
                # Store quota info in session for use in route
                session['_quota_info'] = quota_info
                
                logger.info(f"Quota check passed for user {user_uid}: {quota_info['remaining']} remaining")
                
                # Execute the route
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in quota check decorator: {e}", exc_info=True)
                # On error, allow the request to proceed (fail open)
                # but log it for monitoring
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator

