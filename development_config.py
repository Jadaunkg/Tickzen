# Development Configuration for Tickzen
# This file contains settings optimized for local development

import os

# Development-specific SocketIO settings - OPTIMIZED
SOCKETIO_DEV_CONFIG = {
    'ping_timeout': 60,  # Reduced from 120 to 60 seconds for faster detection
    'ping_interval': 25,  # Reduced from 30 to 25 seconds for more responsive pings
    'async_mode': 'threading',  # More stable than eventlet in development
    'cors_allowed_origins': "*",
    'logger': True,
    'engineio_logger': True,
    'max_http_buffer_size': 1e6,  # 1MB
    'allow_upgrades': True,
    'http_compression': True,
    'compression_threshold': 1024,
    'manage_session': False,  # Let Flask handle sessions
    'cors_credentials': False,  # Disable credentials for better compatibility
    'always_connect': True,  # Always allow connections
    'transports': ['websocket', 'polling'],  # Allow both transports
    'cookie': None,  # Disable cookie-based sessions
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

# Timeout settings for development - OPTIMIZED
DEV_TIMEOUT_CONFIG = {
    'socket_timeout': 15,  # Reduced from 30 to 15 seconds
    'request_timeout': (5, 15),  # Reduced from (10, 30) to (5, 15) seconds
    'firebase_timeout': 15,  # Reduced from 30 to 15 seconds
    'reconnection_attempts': 3,  # Reduced from 5 to 3
    'reconnection_delay': 500,  # Reduced from 1000 to 500ms
    'reconnection_delay_max': 3000,  # Reduced from 5000 to 3000ms
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

# Performance optimization settings
PERFORMANCE_CONFIG = {
    'cache_enabled': True,
    'cache_ttl_hours': 24,  # Cache time-to-live in hours
    'max_cache_size': 100,  # Maximum number of cached items
    'enable_memory_cache': True,
    'enable_file_cache': True,
    'batch_processing': True,
    'parallel_processing': False,  # Disabled in development for stability
}

# SocketIO client configuration for development
SOCKETIO_CLIENT_CONFIG = {
    'reconnection': True,
    'reconnectionAttempts': 3,
    'reconnectionDelay': 500,
    'reconnectionDelayMax': 3000,
    'timeout': 15000,
    'autoConnect': False,  # Prevent auto-connection issues
    'transports': ['websocket', 'polling'],
    'forceNew': False,
    'multiplex': False,
}

def get_dev_config():
    """Get development configuration"""
    return {
        'socketio': SOCKETIO_DEV_CONFIG,
        'server': DEV_SERVER_CONFIG,
        'timeout': DEV_TIMEOUT_CONFIG,
        'logging': DEV_LOGGING_CONFIG,
        'env': DEV_ENV_VARS,
        'performance': PERFORMANCE_CONFIG,
        'socketio_client': SOCKETIO_CLIENT_CONFIG,
    }

def get_optimized_socketio_config():
    """Get optimized SocketIO configuration for development"""
    return SOCKETIO_DEV_CONFIG

def get_optimized_client_config():
    """Get optimized client-side SocketIO configuration"""
    return SOCKETIO_CLIENT_CONFIG

def apply_dev_config():
    """Apply development configuration to environment"""
    for key, value in DEV_ENV_VARS.items():
        if key not in os.environ:
            os.environ[key] = value

if __name__ == '__main__':
    print("Development Configuration:")
    print(get_dev_config()) 