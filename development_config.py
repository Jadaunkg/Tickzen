# Development Configuration for Tickzen
# This file contains settings optimized for local development

import os

# Development-specific SocketIO settings
SOCKETIO_DEV_CONFIG = {
    'ping_timeout': 120,  # 2 minutes
    'ping_interval': 30,  # 30 seconds
    'async_mode': 'threading',  # More stable than eventlet in development
    'cors_allowed_origins': "*",
    'logger': True,
    'engineio_logger': True,
    'max_http_buffer_size': 1e6,  # 1MB
    'allow_upgrades': True,
    'http_compression': True,
    'compression_threshold': 1024,
}

# Development server settings
DEV_SERVER_CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': True,
    'use_reloader': True,
    'allow_unsafe_werkzeug': True,
    'threaded': True,
}

# Timeout settings for development
DEV_TIMEOUT_CONFIG = {
    'socket_timeout': 30,
    'request_timeout': (10, 30),  # (connect, read)
    'firebase_timeout': 30,
}

# Logging configuration for development
DEV_LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(name)s - %(module)s:%(lineno)d - %(message)s',
    'file': 'development.log',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}

# Environment variables for development
DEV_ENV_VARS = {
    'APP_ENV': 'development',
    'FLASK_DEBUG': 'True',
    'FLASK_ENV': 'development',
    'WEBSITES_PORT': '5000',
}

def get_dev_config():
    """Get development configuration"""
    return {
        'socketio': SOCKETIO_DEV_CONFIG,
        'server': DEV_SERVER_CONFIG,
        'timeout': DEV_TIMEOUT_CONFIG,
        'logging': DEV_LOGGING_CONFIG,
        'env': DEV_ENV_VARS,
    }

def apply_dev_config():
    """Apply development configuration to environment"""
    for key, value in DEV_ENV_VARS.items():
        if key not in os.environ:
            os.environ[key] = value

if __name__ == '__main__':
    print("Development Configuration:")
    print(get_dev_config()) 