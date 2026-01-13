"""
Quota Utilities
Helper functions for quota management
"""

from flask import session
from app.services.quota_service import get_quota_service, QuotaExceededException
from app.models.quota_models import ResourceType
import logging
import time

logger = logging.getLogger(__name__)


def consume_user_quota(resource_type, metadata=None):
    """
    Consume quota for the current user
    
    Args:
        resource_type: Type of resource (e.g., ResourceType.STOCK_REPORT.value)
        metadata: Additional metadata about the usage (dict)
            Example: {
                'ticker': 'AAPL',
                'status': 'success',
                'report_id': 'xyz',
                'generation_time_ms': 1234
            }
    
    Returns:
        Dict with consumption result or None on error
    
    Usage:
        consume_user_quota(
            ResourceType.STOCK_REPORT.value,
            {'ticker': 'AAPL', 'status': 'success'}
        )
    """
    try:
        # Get user ID from session
        user_uid = session.get('firebase_user_uid')
        
        if not user_uid:
            logger.warning("Cannot consume quota - no user ID in session")
            return None
        
        # Default metadata if not provided
        if metadata is None:
            metadata = {
                'status': 'success',
                'timestamp': time.time()
            }
        
        # Get quota service
        quota_service = get_quota_service()
        
        # Consume quota
        result = quota_service.consume_quota(
            user_uid,
            resource_type,
            metadata
        )
        
        logger.info(f"Quota consumed for user {user_uid}: {metadata.get('ticker', 'N/A')}")
        
        return result
        
    except QuotaExceededException as e:
        logger.error(f"Quota exceeded during consumption: {e}")
        # Don't fail the request, but log it
        return None
        
    except Exception as e:
        logger.error(f"Failed to consume quota: {e}", exc_info=True)
        # Don't fail the request if quota consumption fails
        # But log it for monitoring
        return None


def get_user_quota_status(resource_type=None):
    """
    Get quota status for the current user
    
    Args:
        resource_type: Type of resource (optional, defaults to stock_report)
    
    Returns:
        Dict with quota status or None on error
    """
    try:
        user_uid = session.get('firebase_user_uid')
        
        if not user_uid:
            return None
        
        if resource_type is None:
            resource_type = ResourceType.STOCK_REPORT.value
        
        quota_service = get_quota_service()
        has_quota, quota_info = quota_service.check_quota(user_uid, resource_type)
        
        return {
            'has_quota': has_quota,
            'info': quota_info
        }
        
    except Exception as e:
        logger.error(f"Failed to get quota status: {e}")
        return None


def get_user_remaining_quota(resource_type=None):
    """
    Get remaining quota count for the current user
    
    Args:
        resource_type: Type of resource (optional, defaults to stock_report)
    
    Returns:
        Remaining quota count or -1 if unlimited, None on error
    """
    try:
        user_uid = session.get('firebase_user_uid')
        
        if not user_uid:
            return None
        
        if resource_type is None:
            resource_type = ResourceType.STOCK_REPORT.value
        
        quota_service = get_quota_service()
        remaining = quota_service.get_remaining_quota(user_uid, resource_type)
        
        return remaining
        
    except Exception as e:
        logger.error(f"Failed to get remaining quota: {e}")
        return None


def initialize_quota_for_new_user(user_uid, plan_type='free', user_email=None, user_display_name=None):
    """
    Initialize quota for a new user (call during registration)
    
    Args:
        user_uid: User's unique identifier
        plan_type: Plan type (defaults to 'free')
        user_email: User email (optional, for admin reference)
        user_display_name: User display name (optional, for admin reference)
    
    Returns:
        UserQuota object or None on error
    """
    try:
        quota_service = get_quota_service()
        quota = quota_service.initialize_user_quota(
            user_uid, 
            plan_type,
            user_email=user_email,
            user_display_name=user_display_name
        )
        
        logger.info(f"Initialized quota for new user {user_uid} with {plan_type} plan")
        
        return quota
        
    except Exception as e:
        logger.error(f"Failed to initialize quota for user {user_uid}: {e}")
        return None


def check_and_warn_quota_threshold(resource_type=None, threshold=0.8):
    """
    Check if user is approaching quota limit and return warning message
    
    Args:
        resource_type: Type of resource (optional, defaults to stock_report)
        threshold: Threshold percentage (default 0.8 = 80%)
    
    Returns:
        Warning message string or None
    """
    try:
        user_uid = session.get('firebase_user_uid')
        
        if not user_uid:
            return None
        
        if resource_type is None:
            resource_type = ResourceType.STOCK_REPORT.value
        
        quota_service = get_quota_service()
        has_quota, quota_info = quota_service.check_quota(user_uid, resource_type)
        
        # Skip for unlimited plans
        if quota_info.get('unlimited', False):
            return None
        
        limit = quota_info.get('limit', 0)
        used = quota_info.get('used', 0)
        
        if limit > 0:
            usage_percentage = used / limit
            
            if usage_percentage >= threshold:
                remaining = quota_info.get('remaining', 0)
                
                if remaining == 0:
                    return f"⚠️ You've used all {limit} reports this month. Upgrade to continue."
                elif remaining == 1:
                    return f"⚠️ You have only 1 report remaining this month. Consider upgrading."
                else:
                    return f"⚠️ You've used {used} of {limit} reports. {remaining} remaining this month."
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to check quota threshold: {e}")
        return None
