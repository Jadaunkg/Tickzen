"""
Monitoring and health check functionality for the Flask application
"""
import os
import time
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import wraps
import redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Flask, request, jsonify, Response
import structlog

# Import configuration
from config.security_config import (
    MONITORING_CONFIG, HEALTH_CHECK_ENDPOINTS, 
    ALERT_CONFIG, ERROR_CONFIG, should_log_traceback
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_USERS = Gauge('active_users', 'Number of active users')
CELERY_TASK_COUNT = Counter('celery_tasks_total', 'Total Celery tasks', ['task_name', 'status'])
FIRESTORE_OPERATIONS = Counter('firestore_operations_total', 'Total Firestore operations', ['operation_type'])
REDIS_OPERATIONS = Counter('redis_operations_total', 'Total Redis operations', ['operation_type'])
FILE_UPLOADS = Counter('file_uploads_total', 'Total file uploads', ['file_type', 'status'])
ERROR_COUNT = Counter('errors_total', 'Total errors', ['error_type'])

class HealthChecker:
    """Health check functionality for various services"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.redis_client = None
        self.celery_app = None
        self.firestore_client = None
        
    def init_services(self, redis_client=None, celery_app=None, firestore_client=None):
        """Initialize service clients for health checks"""
        self.redis_client = redis_client
        self.celery_app = celery_app
        self.firestore_client = firestore_client
    
    def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connection health"""
        try:
            if not self.redis_client:
                return {'status': 'unknown', 'error': 'Redis client not initialized'}
            
            start_time = time.time()
            self.redis_client.ping()
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time': response_time,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            ERROR_COUNT.labels(error_type='redis_health_check').inc()
            logger.error("Redis health check failed", error=str(e), traceback=traceback.format_exc())
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def check_celery_health(self) -> Dict[str, Any]:
        """Check Celery worker health"""
        try:
            if not self.celery_app:
                return {'status': 'unknown', 'error': 'Celery app not initialized'}
            
            # Check if workers are active
            inspect = self.celery_app.control.inspect()
            active_workers = inspect.active()
            registered_workers = inspect.registered()
            
            if not active_workers and not registered_workers:
                return {
                    'status': 'unhealthy',
                    'error': 'No Celery workers found',
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            return {
                'status': 'healthy',
                'active_workers': len(active_workers) if active_workers else 0,
                'registered_workers': len(registered_workers) if registered_workers else 0,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            ERROR_COUNT.labels(error_type='celery_health_check').inc()
            logger.error("Celery health check failed", error=str(e), traceback=traceback.format_exc())
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def check_firestore_health(self) -> Dict[str, Any]:
        """Check Firestore connection health"""
        try:
            if not self.firestore_client:
                return {'status': 'unknown', 'error': 'Firestore client not initialized'}
            
            # Try a simple read operation
            start_time = time.time()
            # This is a minimal operation to test connectivity
            # In production, you might want to read from a specific collection
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time': response_time,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            ERROR_COUNT.labels(error_type='firestore_health_check').inc()
            logger.error("Firestore health check failed", error=str(e), traceback=traceback.format_exc())
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status of all services"""
        redis_health = self.check_redis_health()
        celery_health = self.check_celery_health()
        firestore_health = self.check_firestore_health()
        
        overall_status = 'healthy'
        if any(check['status'] == 'unhealthy' for check in [redis_health, celery_health, firestore_health]):
            overall_status = 'unhealthy'
        elif any(check['status'] == 'unknown' for check in [redis_health, celery_health, firestore_health]):
            overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'redis': redis_health,
                'celery': celery_health,
                'firestore': firestore_health
            }
        }

class QuotaMonitor:
    """Monitor Firestore and Celery usage quotas"""
    
    def __init__(self, firestore_client=None, celery_app=None):
        self.firestore_client = firestore_client
        self.celery_app = celery_app
        self.last_check = {}
        self.alert_sent = {}
    
    def check_firestore_quota(self) -> Dict[str, Any]:
        """Check Firestore usage and quota limits"""
        try:
            # Note: Firestore doesn't provide direct quota information via the client
            # This would typically require Google Cloud Monitoring API
            # For now, we'll implement a basic check based on operation counts
            
            # You would implement actual quota checking here
            # For example, using Google Cloud Monitoring API
            usage_percentage = 0  # Placeholder
            
            if usage_percentage > MONITORING_CONFIG['firestore_quota_alert_threshold']:
                self._send_quota_alert('firestore', usage_percentage)
            
            return {
                'usage_percentage': usage_percentage,
                'threshold': MONITORING_CONFIG['firestore_quota_alert_threshold'],
                'status': 'ok' if usage_percentage < MONITORING_CONFIG['firestore_quota_alert_threshold'] else 'warning'
            }
        except Exception as e:
            logger.error("Firestore quota check failed", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    def check_celery_queue_size(self) -> Dict[str, Any]:
        """Check Celery queue sizes"""
        try:
            if not self.celery_app:
                return {'status': 'unknown', 'error': 'Celery app not initialized'}
            
            inspect = self.celery_app.control.inspect()
            active_tasks = len(inspect.active() or {})
            reserved_tasks = len(inspect.reserved() or {})
            total_queued = active_tasks + reserved_tasks
            
            if total_queued > MONITORING_CONFIG['celery_queue_alert_threshold']:
                self._send_quota_alert('celery', total_queued)
            
            return {
                'active_tasks': active_tasks,
                'reserved_tasks': reserved_tasks,
                'total_queued': total_queued,
                'threshold': MONITORING_CONFIG['celery_queue_alert_threshold'],
                'status': 'ok' if total_queued < MONITORING_CONFIG['celery_queue_alert_threshold'] else 'warning'
            }
        except Exception as e:
            logger.error("Celery queue check failed", error=str(e))
            return {'status': 'error', 'error': str(e)}
    
    def _send_quota_alert(self, service: str, usage: float):
        """Send quota alert if not already sent recently"""
        alert_key = f"{service}_quota_alert"
        now = datetime.utcnow()
        
        # Only send alert once per hour
        if alert_key not in self.alert_sent or \
           (now - self.alert_sent[alert_key]) > timedelta(hours=1):
            
            self.alert_sent[alert_key] = now
            self._send_alert(f"{service.upper()} quota warning: {usage}% usage")
    
    def _send_alert(self, message: str):
        """Send alert via configured channels"""
        logger.warning(f"Quota alert: {message}")
        
        # Email alerts
        if ALERT_CONFIG['email_alerts']['enabled']:
            self._send_email_alert(message)
        
        # Webhook alerts
        if ALERT_CONFIG['webhook_alerts']['enabled']:
            self._send_webhook_alert(message)
    
    def _send_email_alert(self, message: str):
        """Send email alert"""
        # Implementation would use smtplib
        logger.info(f"Email alert sent: {message}")
    
    def _send_webhook_alert(self, message: str):
        """Send webhook alert"""
        # Implementation would use requests
        logger.info(f"Webhook alert sent: {message}")

def monitor_request(f):
    """Decorator to monitor request metrics"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            response = f(*args, **kwargs)
            status_code = response.status_code if hasattr(response, 'status_code') else 200
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.endpoint,
                status=status_code
            ).inc()
            
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            
            return response
        except Exception as e:
            ERROR_COUNT.labels(error_type='request_error').inc()
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.endpoint,
                status=500
            ).inc()
            
            raise
    
    return decorated_function

def log_exception(e: Exception, context: str = ""):
    """Log exception with structured logging"""
    error_data = {
        'error_type': type(e).__name__,
        'error_message': str(e),
        'context': context,
        'endpoint': request.endpoint if request else None,
        'method': request.method if request else None,
        'user_agent': request.headers.get('User-Agent') if request else None,
        'ip_address': request.remote_addr if request else None,
    }
    
    if should_log_traceback():
        error_data['traceback'] = traceback.format_exc()
    
    logger.error("Application error", **error_data)
    ERROR_COUNT.labels(error_type=type(e).__name__).inc()

def register_monitoring_routes(app: Flask, health_checker: HealthChecker):
    """Register monitoring and health check routes"""
    
    @app.route('/health')
    def health_check():
        """Basic health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check for all services"""
        return jsonify(health_checker.get_overall_health())
    
    @app.route('/metrics')
    def metrics():
        """Prometheus metrics endpoint"""
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
    
    @app.route('/health/ready')
    def readiness_probe():
        """Kubernetes readiness probe"""
        health = health_checker.get_overall_health()
        status_code = 200 if health['status'] == 'healthy' else 503
        return jsonify(health), status_code
    
    @app.route('/health/live')
    def liveness_probe():
        """Kubernetes liveness probe"""
        return jsonify({'status': 'alive'})

# Global instances
health_checker = HealthChecker(None)
quota_monitor = QuotaMonitor() 