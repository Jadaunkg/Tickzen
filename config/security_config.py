"""
Security and monitoring configuration for the Flask application
"""
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Environment detection
APP_ENV = os.getenv('APP_ENV', 'development').lower()
IS_PRODUCTION = APP_ENV == 'production'

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# Session Configuration
SESSION_TYPE = 'redis'
SESSION_REDIS_URL = REDIS_URL
SESSION_KEY_PREFIX = 'flask_session:'
SESSION_PERMANENT = True
SESSION_USE_SIGNER = True
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CORS Configuration
CORS_ORIGINS = {
    'development': ['http://localhost:3000', 'http://localhost:5000', 'http://127.0.0.1:5000'],
    'production': os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else []
}

CORS_CONFIG = {
    'origins': CORS_ORIGINS.get(APP_ENV, ['http://localhost:5000']),
    'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    'allow_headers': ['Content-Type', 'Authorization', 'X-Requested-With'],
    'supports_credentials': True,
    'max_age': 3600
}

# Rate Limiting Configuration
RATE_LIMIT_CONFIG = {
    'default': '200 per day;50 per hour;10 per minute',
    'api': '1000 per day;100 per hour;20 per minute',
    'auth': '100 per day;10 per hour;5 per minute',
    'upload': '50 per day;10 per hour;2 per minute',
    'analysis': '100 per day;20 per hour;5 per minute',
    'automation': '50 per day;10 per hour;2 per minute'
}

# File Upload Security
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generated_data', 'temp_uploads')

# File content validation
MAGIC_NUMBERS = {
    'xlsx': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],
    'xls': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'],
    'csv': [b'text/csv', b'text/plain']
}

# Monitoring Configuration
MONITORING_CONFIG = {
    'enabled': os.getenv('ENABLE_MONITORING', 'true').lower() == 'true',
    'sentry_dsn': os.getenv('SENTRY_DSN'),
    'prometheus_port': int(os.getenv('PROMETHEUS_PORT', '9090')),
    'health_check_interval': int(os.getenv('HEALTH_CHECK_INTERVAL', '300')),  # 5 minutes
    'firestore_quota_alert_threshold': int(os.getenv('FIRESTORE_QUOTA_THRESHOLD', '80')),  # 80%
    'celery_queue_alert_threshold': int(os.getenv('CELERY_QUEUE_THRESHOLD', '100')),  # 100 tasks
}

# Security Headers
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'SAMEORIGIN',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains' if IS_PRODUCTION else None,
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' ws: wss:;" if IS_PRODUCTION else None,
}

# Error Handling
ERROR_CONFIG = {
    'log_exceptions': True,
    'log_tracebacks': True,
    'user_friendly_messages': {
        'file_upload_error': 'File upload failed. Please check the file format and size.',
        'rate_limit_exceeded': 'Too many requests. Please try again later.',
        'authentication_error': 'Authentication failed. Please log in again.',
        'permission_error': 'You do not have permission to perform this action.',
        'validation_error': 'Invalid input provided. Please check your data.',
        'server_error': 'An unexpected error occurred. Please try again later.',
        'service_unavailable': 'Service temporarily unavailable. Please try again later.'
    }
}

# Health Check Configuration
HEALTH_CHECK_ENDPOINTS = {
    'redis': REDIS_URL,
    'firestore': 'firebase_admin',
    'celery': 'celery_app',
    'storage': 'firebase_storage'
}

# Alert Configuration
ALERT_CONFIG = {
    'email_alerts': {
        'enabled': os.getenv('EMAIL_ALERTS_ENABLED', 'false').lower() == 'true',
        'smtp_server': os.getenv('SMTP_SERVER'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_username': os.getenv('SMTP_USERNAME'),
        'smtp_password': os.getenv('SMTP_PASSWORD'),
        'alert_recipients': os.getenv('ALERT_EMAILS', '').split(',') if os.getenv('ALERT_EMAILS') else []
    },
    'webhook_alerts': {
        'enabled': os.getenv('WEBHOOK_ALERTS_ENABLED', 'false').lower() == 'true',
        'webhook_url': os.getenv('ALERT_WEBHOOK_URL'),
        'webhook_secret': os.getenv('WEBHOOK_SECRET')
    }
}

def get_cors_origins() -> List[str]:
    """Get CORS origins based on environment"""
    return CORS_ORIGINS.get(APP_ENV, ['http://localhost:5000'])

def get_rate_limit_string(endpoint: str) -> str:
    """Get rate limit string for specific endpoint"""
    return RATE_LIMIT_CONFIG.get(endpoint, RATE_LIMIT_CONFIG['default'])

def is_allowed_file_extension(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_friendly_error_message(error_type: str) -> str:
    """Get user-friendly error message"""
    return ERROR_CONFIG['user_friendly_messages'].get(error_type, 'An error occurred.')

def should_log_traceback() -> bool:
    """Check if tracebacks should be logged"""
    return ERROR_CONFIG['log_tracebacks'] and not IS_PRODUCTION 