# Production Configuration for Tickzen
# This file contains settings optimized for Azure App Service production

import os

# Production-specific SocketIO settings
SOCKETIO_PROD_CONFIG = {
    'ping_timeout': 60,  # 1 minute
    'ping_interval': 25,  # 25 seconds
    'async_mode': 'threading',  # Use threading for better third-party SDK compatibility
    'cors_allowed_origins': os.environ.get('ALLOWED_ORIGINS', '').split(',') if os.environ.get('ALLOWED_ORIGINS') else [],
    'logger': False,  # Disable verbose logging in production
    'engineio_logger': False,
    'max_http_buffer_size': 1e6,  # 1MB
    'allow_upgrades': True,
    'http_compression': True,
    'compression_threshold': 1024,
}

# Production server settings for Gunicorn
PROD_SERVER_CONFIG = {
    'bind': '0.0.0.0:5000',
    'workers': 1,  # Single worker for SocketIO with threading
    'worker_class': 'sync',  # Use sync worker class with threads
    'threads': 100,  # Number of threads per worker for concurrent connections
    'worker_connections': 1000,
    'timeout': 120,
    'keepalive': 5,
    'max_requests': 1000,
    'max_requests_jitter': 100,
    'preload_app': True,
    'access_log_format': '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
    'capture_output': True,
    'enable_stdio_inheritance': True,
}

# Timeout settings for production
PROD_TIMEOUT_CONFIG = {
    'socket_timeout': 60,
    'request_timeout': (10, 60),  # (connect, read)
    'firebase_timeout': 60,
}

# Logging configuration for production
PROD_LOGGING_CONFIG = {
    'level': 'WARNING',  # Less verbose in production
    'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    'handlers': ['console'],  # Azure App Service captures console output
}

# Environment variables for production
PROD_ENV_VARS = {
    'APP_ENV': 'production',
    'FLASK_DEBUG': 'False',
    'FLASK_ENV': 'production',
    'WEBSITES_PORT': '5000',
    'PYTHONPATH': '/home/site/wwwroot',
}

def get_prod_config():
    """Get production configuration"""
    return {
        'socketio': SOCKETIO_PROD_CONFIG,
        'server': PROD_SERVER_CONFIG,
        'timeout': PROD_TIMEOUT_CONFIG,
        'logging': PROD_LOGGING_CONFIG,
        'env': PROD_ENV_VARS,
    }

def apply_prod_config():
    """Apply production configuration to environment"""
    for key, value in PROD_ENV_VARS.items():
        if key not in os.environ:
            os.environ[key] = str(value)

if __name__ == '__main__':
    print("Production Configuration:")
    print(get_prod_config())
