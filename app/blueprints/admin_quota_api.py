"""
Admin API Blueprint for Quota Management
Provides endpoints for admin to view and manage user quotas
"""
from flask import Blueprint, jsonify, request, session
from functools import wraps
from app.services.quota_service import QuotaService
from app.models.quota_models import UserQuota
from config.quota_plans import QUOTA_PLANS
from config.admin_config import is_admin_user
import logging

logger = logging.getLogger(__name__)

admin_quota_bp = Blueprint('admin_quota', __name__, url_prefix='/admin/api/quota')

# Cache for admin data (5 minute TTL)
_admin_cache = {}
_admin_cache_ttl = 300  # 5 minutes


def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        user_id = session.get('firebase_user_uid')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Check if user is admin (using secure config)
        user_email = session.get('firebase_user_email', '')
        
        if not is_admin_user(user_email):
            logger.warning(f"Unauthorized admin access attempt by {user_email}")
            return jsonify({'error': 'Admin access required'}), 403
        
        logger.info(f"Admin access granted to {user_email}")
        return f(*args, **kwargs)
    return decorated_function


@admin_quota_bp.route('/users', methods=['GET'])
@require_admin
def get_all_users():
    """Get all users with their quota information"""
    try:
        import time
        
        # Check cache first
        cache_key = 'all_users_quota'
        if cache_key in _admin_cache:
            cached_data, timestamp = _admin_cache[cache_key]
            if time.time() - timestamp < _admin_cache_ttl:
                logger.info(f"Returning cached user data ({len(cached_data['users'])} users)")
                return jsonify(cached_data)
        
        # Fetch fresh data
        quota_service = QuotaService()
        users = quota_service.get_all_users_quota()
        
        # Calculate statistics
        statistics = {
            'total_users': len(users),
            'total_reports_used': sum(u.get('stock_reports_used', 0) for u in users),
            'premium_users': sum(1 for u in users if u.get('plan_name') != 'Free'),
            'exceeded_users': sum(1 for u in users 
                                if not u.get('stock_reports_unlimited', False) and 
                                u.get('stock_reports_used', 0) >= u.get('stock_reports_limit', 0))
        }
        
        response_data = {
            'success': True,
            'users': users,
            'statistics': statistics
        }
        
        # Cache the response
        _admin_cache[cache_key] = (response_data, time.time())
        logger.info(f"Cached user data for {len(users)} users")
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error fetching all users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users', 'details': str(e)}), 500


@admin_quota_bp.route('/update', methods=['POST'])
@require_admin
def update_user_quota():
    """Update a user's quota and plan"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        plan_name = data.get('plan_name')
        stock_reports_limit = data.get('stock_reports_limit')
        stock_reports_used = data.get('stock_reports_used')
        
        if not user_id or not plan_name:
            logger.error(f"Missing required fields: user_id={user_id}, plan_name={plan_name}")
            return jsonify({'error': 'user_id and plan_name are required'}), 400
        
        quota_service = QuotaService()
        
        # Get current quota
        current_quota = quota_service.get_user_quota(user_id)
        if not current_quota:
            logger.error(f"User not found: {user_id}")
            return jsonify({'error': 'User not found'}), 404
        
        # Normalize plan name (Free -> free, Pro+ -> pro_plus, etc.)
        plan_name_normalized = plan_name.lower().replace('+', '_plus').replace(' ', '_')
        
        # Get plan configuration
        plan_config = QUOTA_PLANS.get(plan_name_normalized)
        if not plan_config:
            logger.error(f"Invalid plan name: {plan_name} (normalized: {plan_name_normalized})")
            return jsonify({
                'error': f'Invalid plan name: {plan_name}',
                'valid_plans': ['Free', 'Pro', 'Pro+', 'Enterprise']
            }), 400
        
        # Prepare update data (use normalized plan name for storage)
        update_data = {
            'plan_type': plan_name_normalized,
        }
        
        # Update stock reports quota
        if stock_reports_limit is not None:
            unlimited = stock_reports_limit >= 999999
            current_used = current_quota.current_usage.stock_reports if current_quota.current_usage else 0
            
            update_data['stock_reports'] = {
                'used': stock_reports_used if stock_reports_used is not None else current_used,
                'limit': stock_reports_limit if not unlimited else plan_config['limits']['stock_reports_monthly'],
                'unlimited': unlimited
            }
        
        # Update quota in Firestore
        success = quota_service.update_user_quota(user_id, update_data)
        
        if success:
            # Invalidate cache
            _admin_cache.clear()
            logger.info(f"Admin updated quota for user {user_id}: {plan_name_normalized}")
            return jsonify({
                'success': True,
                'message': f'User quota updated to {plan_name} plan'
            })
        else:
            return jsonify({'error': 'Failed to update user quota'}), 500
    
    except Exception as e:
        logger.error(f"Error updating user quota: {str(e)}")
        return jsonify({'error': 'Failed to update quota', 'details': str(e)}), 500


@admin_quota_bp.route('/reset', methods=['POST'])
@require_admin
def reset_user_quota():
    """Reset a user's quota usage to 0"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        quota_service = QuotaService()
        
        # Reset quota
        update_data = {
            'stock_reports.used': 0
        }
        
        success = quota_service.update_user_quota(user_id, update_data)
        
        if success:
            # Invalidate cache
            _admin_cache.clear()
            logger.info(f"Admin reset quota for user {user_id}")
            return jsonify({
                'success': True,
                'message': 'User quota reset successfully'
            })
        else:
            return jsonify({'error': 'Failed to reset user quota'}), 500
    
    except Exception as e:
        logger.error(f"Error resetting user quota: {str(e)}")
        return jsonify({'error': 'Failed to reset quota', 'details': str(e)}), 500


@admin_quota_bp.route('/bulk-reset', methods=['POST'])
@require_admin
def bulk_reset_quotas():
    """Reset all users' quotas (monthly reset simulation)"""
    try:
        quota_service = QuotaService()
        result = quota_service.reset_all_quotas()
        
        logger.info(f"Admin triggered bulk quota reset: {result['reset_count']} users")
        
        return jsonify({
            'success': True,
            'message': f"Reset {result['reset_count']} user quotas",
            'reset_count': result['reset_count'],
            'failed_count': result['failed_count']
        })
    
    except Exception as e:
        logger.error(f"Error in bulk quota reset: {str(e)}")
        return jsonify({'error': 'Failed to reset quotas', 'details': str(e)}), 500


@admin_quota_bp.route('/plans', methods=['GET'])
@require_admin
def get_available_plans():
    """Get all available quota plans"""
    try:
        plans = []
        for plan_name, config in QUOTA_PLANS.items():
            plans.append({
                'name': plan_name,
                'tier': config['tier'],
                'stock_reports_limit': config['stock_reports']['limit'],
                'stock_reports_unlimited': config['stock_reports']['unlimited'],
                'features': config.get('features', [])
            })
        
        return jsonify({
            'success': True,
            'plans': plans
        })
    
    except Exception as e:
        logger.error(f"Error fetching plans: {str(e)}")
        return jsonify({'error': 'Failed to fetch plans', 'details': str(e)}), 500


@admin_quota_bp.route('/user/<user_id>', methods=['GET'])
@require_admin
def get_user_quota_detail(user_id):
    """Get detailed quota information for a specific user"""
    try:
        quota_service = QuotaService()
        quota = quota_service.get_user_quota(user_id)
        
        if not quota:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'quota': quota.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error fetching user quota: {str(e)}")
        return jsonify({'error': 'Failed to fetch user quota', 'details': str(e)}), 500


@admin_quota_bp.route('/statistics', methods=['GET'])
@require_admin
def get_quota_statistics():
    """Get overall quota system statistics"""
    try:
        quota_service = QuotaService()
        users = quota_service.get_all_users_quota()
        
        # Plan distribution
        plan_distribution = {}
        for user in users:
            plan = user.get('plan_name', 'Free')
            plan_distribution[plan] = plan_distribution.get(plan, 0) + 1
        
        # Usage statistics
        total_used = sum(u.get('stock_reports_used', 0) for u in users)
        total_limit = sum(u.get('stock_reports_limit', 0) for u in users 
                         if not u.get('stock_reports_unlimited', False))
        
        # Users by status
        active_users = sum(1 for u in users 
                          if not u.get('stock_reports_unlimited', False) and 
                          (u.get('stock_reports_used', 0) / max(u.get('stock_reports_limit', 1), 1)) < 0.8)
        warning_users = sum(1 for u in users 
                           if not u.get('stock_reports_unlimited', False) and 
                           0.8 <= (u.get('stock_reports_used', 0) / max(u.get('stock_reports_limit', 1), 1)) < 1.0)
        exceeded_users = sum(1 for u in users 
                            if not u.get('stock_reports_unlimited', False) and 
                            u.get('stock_reports_used', 0) >= u.get('stock_reports_limit', 0))
        
        statistics = {
            'total_users': len(users),
            'plan_distribution': plan_distribution,
            'total_reports_used': total_used,
            'total_reports_limit': total_limit,
            'active_users': active_users,
            'warning_users': warning_users,
            'exceeded_users': exceeded_users,
            'premium_users': sum(1 for u in users if u.get('plan_name') != 'Free')
        }
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
    
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}")
        return jsonify({'error': 'Failed to fetch statistics', 'details': str(e)}), 500
