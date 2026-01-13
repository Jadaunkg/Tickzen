"""
Quota API Blueprint
Provides API endpoints for quota management
"""

from flask import Blueprint, jsonify, session
from app.services.quota_service import get_quota_service
from app.models.quota_models import ResourceType
from config.quota_plans import QUOTA_PLANS
import logging

logger = logging.getLogger(__name__)

# Create blueprint
quota_bp = Blueprint('quota_api', __name__, url_prefix='/api/quota')


def login_required_api(f):
    """Decorator to check if user is logged in for API calls"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'firebase_user_uid' not in session:
            return jsonify({
                'error': 'unauthorized',
                'message': 'Please log in to access this resource'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


@quota_bp.route('/status', methods=['GET'])
@login_required_api
def get_quota_status():
    """
    Get current quota status for the logged-in user
    
    Returns:
        JSON with quota information for all resource types
    """
    try:
        user_uid = session.get('firebase_user_uid')
        quota_service = get_quota_service()
        
        # Get stock report quota
        has_quota, info = quota_service.check_quota(
            user_uid, 
            ResourceType.STOCK_REPORT.value
        )
        
        response = {
            'stock_reports': {
                'has_quota': has_quota,
                'limit': info.get('limit', 0),
                'used': info.get('used', 0),
                'remaining': info.get('remaining', 0),
                'unlimited': info.get('unlimited', False),
                'period_end': info.get('period_end', ''),
                'period_start': info.get('period_start', '')
            },
            'plan_type': info.get('plan_type', 'free'),
            'is_suspended': info.get('reason') == 'suspended'
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting quota status: {e}", exc_info=True)
        return jsonify({
            'error': 'server_error',
            'message': 'Failed to retrieve quota status'
        }), 500


@quota_bp.route('/usage', methods=['GET'])
@login_required_api
def get_quota_usage():
    """
    Get detailed usage statistics for the logged-in user
    
    Returns:
        JSON with detailed usage information
    """
    try:
        user_uid = session.get('firebase_user_uid')
        quota_service = get_quota_service()
        
        stats = quota_service.get_usage_stats(user_uid)
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting quota usage: {e}", exc_info=True)
        return jsonify({
            'error': 'server_error',
            'message': 'Failed to retrieve usage statistics'
        }), 500


@quota_bp.route('/plans', methods=['GET'])
def get_quota_plans():
    """
    Get available subscription plans
    
    Returns:
        JSON with all available plans and their limits
    """
    try:
        plans = []
        
        for plan_id, plan_data in QUOTA_PLANS.items():
            plans.append({
                'id': plan_id,
                'name': plan_data['display_name'],
                'price': plan_data['price_monthly'],
                'limits': plan_data['limits'],
                'features': plan_data['features'],
                'is_active': plan_data.get('is_active', True)
            })
        
        # Sort by price
        plans.sort(key=lambda x: x['price'])
        
        return jsonify({'plans': plans}), 200
        
    except Exception as e:
        logger.error(f"Error getting quota plans: {e}", exc_info=True)
        return jsonify({
            'error': 'server_error',
            'message': 'Failed to retrieve plans'
        }), 500


@quota_bp.route('/remaining/<resource_type>', methods=['GET'])
@login_required_api
def get_remaining_quota(resource_type):
    """
    Get remaining quota for a specific resource type
    
    Args:
        resource_type: Type of resource (stock_report, etc.)
    
    Returns:
        JSON with remaining quota count
    """
    try:
        user_uid = session.get('firebase_user_uid')
        quota_service = get_quota_service()
        
        # Validate resource type
        if resource_type not in [rt.value for rt in ResourceType]:
            return jsonify({
                'error': 'invalid_resource',
                'message': f'Invalid resource type: {resource_type}'
            }), 400
        
        remaining = quota_service.get_remaining_quota(user_uid, resource_type)
        
        return jsonify({
            'resource_type': resource_type,
            'remaining': remaining,
            'unlimited': remaining == -1
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting remaining quota: {e}", exc_info=True)
        return jsonify({
            'error': 'server_error',
            'message': 'Failed to get remaining quota'
        }), 500


@quota_bp.route('/check/<resource_type>', methods=['GET'])
@login_required_api
def check_quota_endpoint(resource_type):
    """
    Check if user has quota available for a resource type
    
    Args:
        resource_type: Type of resource (stock_report, etc.)
    
    Returns:
        JSON with quota check result
    """
    try:
        user_uid = session.get('firebase_user_uid')
        quota_service = get_quota_service()
        
        # Validate resource type
        if resource_type not in [rt.value for rt in ResourceType]:
            return jsonify({
                'error': 'invalid_resource',
                'message': f'Invalid resource type: {resource_type}'
            }), 400
        
        has_quota, quota_info = quota_service.check_quota(user_uid, resource_type)
        
        return jsonify({
            'has_quota': has_quota,
            'quota_info': quota_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking quota: {e}", exc_info=True)
        return jsonify({
            'error': 'server_error',
            'message': 'Failed to check quota'
        }), 500
