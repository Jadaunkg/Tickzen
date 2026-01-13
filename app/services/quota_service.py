"""
Quota Service
Core service for managing user quotas and usage tracking
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from calendar import monthrange
import time

from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter, Transaction

from app.models.quota_models import (
    UserQuota, UsageHistory, QuotaLimits, CurrentUsage,
    StockReportUsage, LifetimeStats, ResourceType
)
from config.quota_plans import (
    QUOTA_PLANS, DEFAULT_PLAN, get_plan_limits, 
    get_plan_info, is_unlimited
)

# Setup logging
logger = logging.getLogger(__name__)


class QuotaExceededException(Exception):
    """Raised when user quota is exceeded"""
    def __init__(self, message: str, quota_info: Dict[str, Any] = None):
        super().__init__(message)
        self.quota_info = quota_info or {}


class QuotaServiceError(Exception):
    """General quota service error"""
    pass


class QuotaService:
    """
    Service for managing user quotas and usage tracking
    
    Features:
    - Check quota availability
    - Consume quota with atomic transactions
    - Track usage history
    - Handle monthly resets
    - In-memory caching for performance
    """
    
    def __init__(self, db=None):
        """
        Initialize QuotaService
        
        Args:
            db: Firestore database instance (optional, will use default if not provided)
        """
        self.db = db if db else firestore.client()
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 60  # Cache TTL in seconds
        
        logger.info("QuotaService initialized")
    
    def _get_cache_key(self, user_uid: str, resource_type: str) -> str:
        """Generate cache key"""
        return f"{user_uid}:{resource_type}"
    
    def _get_cached_quota(self, user_uid: str, resource_type: str) -> Optional[UserQuota]:
        """Get quota from cache if available and not expired"""
        cache_key = self._get_cache_key(user_uid, resource_type)
        
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached_data
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
        
        return None
    
    def _set_cached_quota(self, user_uid: str, resource_type: str, quota: UserQuota):
        """Set quota in cache"""
        cache_key = self._get_cache_key(user_uid, resource_type)
        self._cache[cache_key] = (quota, time.time())
    
    def _invalidate_cache(self, user_uid: str, resource_type: str = None):
        """Invalidate cache for user"""
        if resource_type:
            cache_key = self._get_cache_key(user_uid, resource_type)
            if cache_key in self._cache:
                del self._cache[cache_key]
        else:
            # Invalidate all cache entries for this user
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"{user_uid}:")]
            for key in keys_to_delete:
                del self._cache[key]
    
    def _get_current_period(self) -> Tuple[datetime, datetime]:
        """Get current billing period (month start and end)"""
        now = datetime.now(timezone.utc)
        
        # First day of current month
        period_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Last day of current month
        last_day = monthrange(now.year, now.month)[1]
        period_end = datetime(now.year, now.month, last_day, 23, 59, 59, tzinfo=timezone.utc)
        
        return period_start, period_end
    
    def _get_period_string(self, dt: datetime = None) -> str:
        """Get period string in YYYY-MM format"""
        if dt is None:
            dt = datetime.now(timezone.utc)
        return dt.strftime('%Y-%m')
    
    def initialize_user_quota(self, user_uid: str, plan_type: str = None, user_email: str = None, user_display_name: str = None) -> UserQuota:
        """
        Initialize quota document for a new user
        
        Args:
            user_uid: User's unique identifier
            plan_type: Plan type (defaults to free)
            user_email: User email (optional, for admin reference)
            user_display_name: User display name (optional, for admin reference)
        
        Returns:
            UserQuota object
        """
        try:
            if plan_type is None:
                plan_type = DEFAULT_PLAN
            
            # Get plan limits
            plan_info = get_plan_info(plan_type)
            limits = QuotaLimits.from_dict(plan_info['limits'])
            
            # Get current period
            period_start, period_end = self._get_current_period()
            
            # Create user quota
            now = datetime.now(timezone.utc)
            user_quota = UserQuota(
                user_uid=user_uid,
                plan_type=plan_type,
                plan_updated_at=now,
                quota_limits=limits,
                current_usage=CurrentUsage(),
                current_period_start=period_start,
                current_period_end=period_end,
                last_reset=now,
                created_at=now,
                updated_at=now,
                lifetime_stats=LifetimeStats(member_since=now)
            )
            
            # Save to Firestore with additional user info
            quota_ref = self.db.collection('userQuotas').document(user_uid)
            quota_dict = user_quota.to_dict()
            
            # Add email and display name for admin reference
            if user_email:
                quota_dict['user_email'] = user_email
            if user_display_name:
                quota_dict['user_displayName'] = user_display_name
            
            quota_ref.set(quota_dict)
            
            logger.info(f"Initialized quota for user {user_uid} with plan {plan_type}")
            
            return user_quota
            
        except Exception as e:
            logger.error(f"Error initializing user quota: {e}")
            raise QuotaServiceError(f"Failed to initialize user quota: {e}")
    
    def get_user_quota(self, user_uid: str, use_cache: bool = True) -> Optional[UserQuota]:
        """
        Get user quota document
        
        Args:
            user_uid: User's unique identifier
            use_cache: Whether to use cache
        
        Returns:
            UserQuota object or None if not found
        """
        try:
            # Check cache first
            if use_cache:
                cached = self._get_cached_quota(user_uid, 'quota')
                if cached:
                    return cached
            
            # Get from Firestore
            quota_ref = self.db.collection('userQuotas').document(user_uid)
            quota_doc = quota_ref.get()
            
            if not quota_doc.exists:
                logger.warning(f"Quota document not found for user {user_uid}")
                return None
            
            quota = UserQuota.from_dict(quota_doc.to_dict())
            
            # Cache it
            if use_cache:
                self._set_cached_quota(user_uid, 'quota', quota)
            
            return quota
            
        except Exception as e:
            logger.error(f"Error getting user quota: {e}")
            raise QuotaServiceError(f"Failed to get user quota: {e}")
    
    def check_quota(self, user_uid: str, resource_type: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if user has quota available for a resource
        
        Args:
            user_uid: User's unique identifier
            resource_type: Type of resource (e.g., 'stock_report')
        
        Returns:
            Tuple of (has_quota: bool, quota_info: dict)
        """
        try:
            start_time = time.time()
            
            # Validate resource type
            if resource_type not in [rt.value for rt in ResourceType]:
                raise ValueError(f"Invalid resource type: {resource_type}")
            
            # Get user quota
            quota = self.get_user_quota(user_uid)
            
            if not quota:
                # User doesn't have quota initialized, create it
                # Try to get user info from session for better admin visibility
                from flask import session
                user_email = session.get('firebase_user_email')
                user_display_name = session.get('firebase_user_displayName')
                
                quota = self.initialize_user_quota(
                    user_uid,
                    user_email=user_email,
                    user_display_name=user_display_name
                )
            
            # Check if suspended
            if quota.is_suspended:
                quota_info = {
                    'has_quota': False,
                    'reason': 'suspended',
                    'suspension_reason': quota.suspension_reason,
                    'check_time_ms': int((time.time() - start_time) * 1000)
                }
                return False, quota_info
            
            # Check if period needs reset
            now = datetime.now(timezone.utc)
            if now > quota.current_period_end:
                self.reset_monthly_quota(user_uid)
                quota = self.get_user_quota(user_uid, use_cache=False)
            
            # Get limit and usage for this resource
            if resource_type == ResourceType.STOCK_REPORT.value:
                limit = quota.quota_limits.stock_reports_monthly
                current = quota.current_usage.stock_reports
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")
            
            # Check if unlimited
            if is_unlimited(limit):
                quota_info = {
                    'has_quota': True,
                    'limit': -1,
                    'used': current,
                    'remaining': -1,
                    'unlimited': True,
                    'plan_type': quota.plan_type,
                    'check_time_ms': int((time.time() - start_time) * 1000)
                }
                return True, quota_info
            
            # Check if under limit
            has_quota = current < limit
            remaining = max(0, limit - current)
            
            quota_info = {
                'has_quota': has_quota,
                'limit': limit,
                'used': current,
                'remaining': remaining,
                'unlimited': False,
                'plan_type': quota.plan_type,
                'period_end': quota.current_period_end.isoformat(),
                'check_time_ms': int((time.time() - start_time) * 1000)
            }
            
            logger.info(f"Quota check for {user_uid}/{resource_type}: {has_quota} ({current}/{limit})")
            
            return has_quota, quota_info
            
        except Exception as e:
            logger.error(f"Error checking quota: {e}")
            raise QuotaServiceError(f"Failed to check quota: {e}")
    
    def _consume_quota_transaction(self, transaction: Transaction, user_uid: str, 
                                   resource_type: str, metadata: Dict[str, Any]) -> UserQuota:
        """
        Consume quota in an atomic transaction
        
        This runs inside a Firestore transaction to ensure atomicity
        """
        quota_ref = self.db.collection('userQuotas').document(user_uid)
        quota_doc = quota_ref.get(transaction=transaction)
        
        if not quota_doc.exists:
            raise QuotaServiceError(f"Quota document not found for user {user_uid}")
        
        quota_data = quota_doc.to_dict()
        quota = UserQuota.from_dict(quota_data)
        
        # Increment usage counter
        if resource_type == ResourceType.STOCK_REPORT.value:
            quota.current_usage.stock_reports += 1
            quota.lifetime_stats.total_stock_reports += 1
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        
        # Update timestamp
        quota.updated_at = datetime.now(timezone.utc)
        
        # Update in transaction
        transaction.update(quota_ref, quota.to_dict())
        
        return quota
    
    def consume_quota(self, user_uid: str, resource_type: str, 
                     metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consume quota for a resource (atomic operation)
        
        Args:
            user_uid: User's unique identifier
            resource_type: Type of resource
            metadata: Additional metadata about the usage
        
        Returns:
            Dict with consumption details
        
        Raises:
            QuotaExceededException: If quota is exceeded
            QuotaServiceError: If consumption fails
        """
        try:
            start_time = time.time()
            
            # Check quota first
            has_quota, quota_info = self.check_quota(user_uid, resource_type)
            
            if not has_quota:
                raise QuotaExceededException(
                    f"Quota exceeded for {resource_type}",
                    quota_info=quota_info
                )
            
            # Consume quota in transaction
            @firestore.transactional
            def update_quota(transaction):
                quota_ref = self.db.collection('userQuotas').document(user_uid)
                quota_doc = quota_ref.get(transaction=transaction)
                
                if not quota_doc.exists:
                    raise QuotaServiceError(f"Quota document not found for user {user_uid}")
                
                quota_data = quota_doc.to_dict()
                quota = UserQuota.from_dict(quota_data)
                
                # Increment usage counter
                if resource_type == ResourceType.STOCK_REPORT.value:
                    quota.current_usage.stock_reports += 1
                    quota.lifetime_stats.total_stock_reports += 1
                else:
                    raise ValueError(f"Unsupported resource type: {resource_type}")
                
                # Update timestamp
                quota.updated_at = datetime.now(timezone.utc)
                
                # Update in transaction
                transaction.update(quota_ref, quota.to_dict())
                
                return quota
            
            transaction = self.db.transaction()
            updated_quota = update_quota(transaction)
            
            # Invalidate cache
            self._invalidate_cache(user_uid)
            
            # Record usage history
            self._record_usage_history(user_uid, resource_type, metadata)
            
            consumption_time = int((time.time() - start_time) * 1000)
            
            result = {
                'success': True,
                'user_uid': user_uid,
                'resource_type': resource_type,
                'quota_used': updated_quota.current_usage.to_dict(),
                'quota_limits': updated_quota.quota_limits.to_dict(),
                'consumption_time_ms': consumption_time
            }
            
            logger.info(f"Quota consumed for {user_uid}/{resource_type} in {consumption_time}ms")
            
            return result
            
        except QuotaExceededException:
            raise
        except Exception as e:
            logger.error(f"Error consuming quota: {e}")
            raise QuotaServiceError(f"Failed to consume quota: {e}")
    
    def _record_usage_history(self, user_uid: str, resource_type: str, 
                              metadata: Dict[str, Any]):
        """Record usage in history collection"""
        try:
            period = self._get_period_string()
            history_ref = (self.db.collection('userQuotas')
                          .document(user_uid)
                          .collection('usage_history')
                          .document(period))
            
            # Get or create history document
            history_doc = history_ref.get()
            
            if history_doc.exists:
                history = UsageHistory.from_dict(history_doc.to_dict())
            else:
                history = UsageHistory(period=period, user_uid=user_uid)
            
            # Add usage record
            if resource_type == ResourceType.STOCK_REPORT.value:
                usage = StockReportUsage(
                    ticker=metadata.get('ticker', 'UNKNOWN'),
                    report_id=metadata.get('report_id'),
                    status=metadata.get('status', 'success'),
                    generation_time_ms=metadata.get('generation_time_ms', 0)
                )
                history.add_stock_report(usage)
            
            # Save history
            history_ref.set(history.to_dict())
            
        except Exception as e:
            logger.error(f"Error recording usage history: {e}")
            # Don't raise - usage history is important but not critical
    
    def get_usage_stats(self, user_uid: str, period: str = None) -> Dict[str, Any]:
        """
        Get usage statistics for a user
        
        Args:
            user_uid: User's unique identifier
            period: Period in YYYY-MM format (defaults to current month)
        
        Returns:
            Dict with usage statistics
        """
        try:
            if period is None:
                period = self._get_period_string()
            
            # Get current quota
            quota = self.get_user_quota(user_uid)
            
            if not quota:
                return {'error': 'User quota not found'}
            
            # Get usage history
            history_ref = (self.db.collection('userQuotas')
                          .document(user_uid)
                          .collection('usage_history')
                          .document(period))
            
            history_doc = history_ref.get()
            
            stats = {
                'user_uid': user_uid,
                'plan_type': quota.plan_type,
                'period': period,
                'quota_limits': quota.quota_limits.to_dict(),
                'current_usage': quota.current_usage.to_dict(),
                'period_start': quota.current_period_start.isoformat(),
                'period_end': quota.current_period_end.isoformat(),
                'lifetime_stats': quota.lifetime_stats.to_dict()
            }
            
            if history_doc.exists:
                history = UsageHistory.from_dict(history_doc.to_dict())
                stats['history'] = {
                    'daily_stats': history.daily_stats,
                    'summary': history.summary.to_dict(),
                    'total_records': len(history.stock_reports)
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            raise QuotaServiceError(f"Failed to get usage stats: {e}")
    
    def get_remaining_quota(self, user_uid: str, resource_type: str) -> int:
        """
        Get remaining quota for a resource
        
        Args:
            user_uid: User's unique identifier
            resource_type: Type of resource
        
        Returns:
            Remaining quota count (-1 if unlimited)
        """
        has_quota, quota_info = self.check_quota(user_uid, resource_type)
        
        if quota_info.get('unlimited'):
            return -1
        
        return quota_info.get('remaining', 0)
    
    def reset_monthly_quota(self, user_uid: str) -> bool:
        """
        Reset monthly quota for a user
        
        Args:
            user_uid: User's unique identifier
        
        Returns:
            True if successful
        """
        try:
            quota_ref = self.db.collection('userQuotas').document(user_uid)
            quota_doc = quota_ref.get()
            
            if not quota_doc.exists:
                logger.warning(f"Cannot reset quota - user {user_uid} not found")
                return False
            
            quota = UserQuota.from_dict(quota_doc.to_dict())
            
            # Reset usage counters
            quota.current_usage.reset()
            
            # Update period
            period_start, period_end = self._get_current_period()
            quota.current_period_start = period_start
            quota.current_period_end = period_end
            quota.last_reset = datetime.now(timezone.utc)
            quota.updated_at = datetime.now(timezone.utc)
            
            # Update in Firestore
            quota_ref.update(quota.to_dict())
            
            # Invalidate cache
            self._invalidate_cache(user_uid)
            
            logger.info(f"Reset monthly quota for user {user_uid}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting quota: {e}")
            raise QuotaServiceError(f"Failed to reset quota: {e}")
    
    def update_user_plan(self, user_uid: str, new_plan: str) -> bool:
        """
        Update user's subscription plan
        
        Args:
            user_uid: User's unique identifier
            new_plan: New plan type
        
        Returns:
            True if successful
        """
        try:
            if new_plan not in QUOTA_PLANS:
                raise ValueError(f"Invalid plan type: {new_plan}")
            
            quota_ref = self.db.collection('userQuotas').document(user_uid)
            quota_doc = quota_ref.get()
            
            if not quota_doc.exists:
                logger.warning(f"Cannot update plan - user {user_uid} not found")
                return False
            
            quota = UserQuota.from_dict(quota_doc.to_dict())
            
            # Update plan
            quota.plan_type = new_plan
            quota.plan_updated_at = datetime.now(timezone.utc)
            quota.updated_at = datetime.now(timezone.utc)
            
            # Update limits
            plan_info = get_plan_info(new_plan)
            quota.quota_limits = QuotaLimits.from_dict(plan_info['limits'])
            
            # Update in Firestore
            quota_ref.update(quota.to_dict())
            
            # Invalidate cache
            self._invalidate_cache(user_uid)
            
            logger.info(f"Updated plan for user {user_uid} to {new_plan}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating user plan: {e}")
            raise QuotaServiceError(f"Failed to update user plan: {e}")
    
    # ==================== ADMIN METHODS ====================
    
    def get_all_users_quota(self) -> list:
        """
        Get quota information for all users (Admin only)
        Optimized - uses data already in quota documents
        
        Returns:
            List of user quota dictionaries
        """
        try:
            import time
            start_time = time.time()
            
            users = []
            quotas_ref = self.db.collection('userQuotas')
            
            # Stream all quota documents (single query)
            for doc in quotas_ref.stream():
                user_uid = doc.id
                quota_data = doc.to_dict()
                
                # Get stock reports limit
                stock_reports_limit = quota_data.get('quota_limits', {}).get('stock_reports_monthly', 10)
                
                # Get email and display name (backfilled data)
                email = quota_data.get('user_email', 'N/A')
                display_name = quota_data.get('user_displayName')
                
                # Fallback to email username if no display name
                if not display_name or display_name == 'N/A':
                    display_name = email.split('@')[0] if email != 'N/A' else 'User'
                
                user_info = {
                    'user_id': user_uid,
                    'email': email,
                    'display_name': display_name,
                    'plan_name': quota_data.get('plan_type', 'Free'),
                    'stock_reports_used': quota_data.get('current_usage', {}).get('stock_reports_used', 0),
                    'stock_reports_limit': stock_reports_limit,
                    'stock_reports_unlimited': is_unlimited(stock_reports_limit),
                    'last_reset_at': quota_data.get('last_reset'),
                    'created_at': quota_data.get('created_at'),
                    'is_suspended': quota_data.get('is_suspended', False)
                }
                
                users.append(user_info)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Retrieved quota info for {len(users)} users in {elapsed_time:.2f}s")
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users quota: {e}")
            raise QuotaServiceError(f"Failed to get all users quota: {e}")
    
    def update_user_quota(self, user_uid: str, update_data: dict) -> bool:
        """
        Update user quota (Admin only)
        
        Args:
            user_uid: User's unique identifier
            update_data: Dictionary with fields to update
        
        Returns:
            True if successful
        """
        try:
            quota_ref = self.db.collection('userQuotas').document(user_uid)
            quota_doc = quota_ref.get()
            
            if not quota_doc.exists:
                logger.warning(f"Cannot update quota - user {user_uid} not found")
                return False
            
            quota = UserQuota.from_dict(quota_doc.to_dict())
            
            # Update plan if provided
            if 'plan_name' in update_data or 'plan_type' in update_data:
                new_plan = update_data.get('plan_name') or update_data.get('plan_type')
                if new_plan in QUOTA_PLANS:
                    quota.plan_type = new_plan
                    quota.plan_updated_at = datetime.now(timezone.utc)
                    
                    # Update limits
                    plan_info = get_plan_info(new_plan)
                    quota.quota_limits = QuotaLimits.from_dict(plan_info['limits'])
            
            # Update stock reports if provided
            if 'stock_reports' in update_data:
                sr_data = update_data['stock_reports']
                if 'used' in sr_data:
                    quota.current_usage.stock_reports_used = sr_data['used']
                if 'limit' in sr_data:
                    quota.quota_limits.stock_reports_monthly = sr_data['limit']
            
            # Update tier if provided
            if 'tier' in update_data:
                # Tier is part of plan, already handled above
                pass
            
            # Update timestamp
            quota.updated_at = datetime.now(timezone.utc)
            
            # Save to Firestore
            quota_ref.update(quota.to_dict())
            
            # Invalidate cache
            self._invalidate_cache(user_uid)
            
            logger.info(f"Admin updated quota for user {user_uid}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating user quota: {e}")
            raise QuotaServiceError(f"Failed to update user quota: {e}")
    
    def reset_all_quotas(self) -> dict:
        """
        Reset all users' quotas (Admin only - for monthly reset)
        
        Returns:
            Dictionary with reset statistics
        """
        try:
            quotas_ref = self.db.collection('userQuotas')
            reset_count = 0
            failed_count = 0
            
            for doc in quotas_ref.stream():
                try:
                    user_uid = doc.id
                    self.reset_monthly_quota(user_uid)
                    reset_count += 1
                except Exception as e:
                    logger.error(f"Failed to reset quota for user {user_uid}: {e}")
                    failed_count += 1
            
            result = {
                'reset_count': reset_count,
                'failed_count': failed_count,
                'total_users': reset_count + failed_count
            }
            
            logger.info(f"Bulk quota reset completed: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in bulk quota reset: {e}")
            raise QuotaServiceError(f"Failed to reset all quotas: {e}")


# Singleton instance
_quota_service_instance = None

def get_quota_service(db=None) -> QuotaService:
    """Get or create QuotaService singleton instance"""
    global _quota_service_instance
    
    if _quota_service_instance is None:
        _quota_service_instance = QuotaService(db)
    
    return _quota_service_instance
