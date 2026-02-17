import os
import sys
from datetime import timedelta
from dotenv import load_dotenv, dotenv_values

# Define Project Root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class Config:
    @staticmethod
    def load_env():
        # Load main .env from project root
        main_env = os.path.join(PROJECT_ROOT, '.env')
        load_dotenv(main_env, override=True)
        if os.path.exists(main_env):
            for key, value in dotenv_values(main_env).items():
                if value is not None:
                    os.environ[key] = value
        
        # Load Sports Automation .env
        sports_automation_env = os.path.join(PROJECT_ROOT, 'Sports_Article_Automation', '.env')
        if os.path.exists(sports_automation_env):
            load_dotenv(sports_automation_env, override=True)
            for key, value in dotenv_values(sports_automation_env).items():
                if value is not None:
                    os.environ[key] = value
        
        # Set Firebase credentials path if not set
        FIREBASE_SERVICE_ACCOUNT_PATH = os.path.join(PROJECT_ROOT, 'config', 'firebase-service-account-key.json')
        if os.path.exists(FIREBASE_SERVICE_ACCOUNT_PATH):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = FIREBASE_SERVICE_ACCOUNT_PATH

    @staticmethod
    def get_firebase_client_config():
        """Get Firebase client configuration from environment variables"""
        return {
            'apiKey': os.getenv('FIREBASE_API_KEY'),
            'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN') or f"{os.getenv('FIREBASE_PROJECT_ID')}.firebaseapp.com",
            'projectId': os.getenv('FIREBASE_PROJECT_ID'),
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', f"{os.getenv('FIREBASE_PROJECT_ID')}.appspot.com"),
            'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
            'appId': os.getenv('FIREBASE_APP_ID')
        }

    @staticmethod
    def get_flask_config(app_root):
        """Return dict of Flask config values"""
        Config.load_env()
        
        UPLOAD_FOLDER = os.path.join(app_root, '..', 'generated_data', 'temp_uploads')
        
        # Redis Configuration
        REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        USE_REDIS = os.getenv('USE_REDIS', 'False').lower() == 'true'
        
        config = {
            'SECRET_KEY': os.getenv("FLASK_SECRET_KEY", "your_strong_default_secret_key_here_CHANGE_ME_TOO"),
            'UPLOAD_FOLDER': UPLOAD_FOLDER,
            'MAX_CONTENT_LENGTH': 5 * 1024 * 1024,
            'SEND_FILE_MAX_AGE_DEFAULT': 0,
            'PERMANENT_SESSION_LIFETIME': timedelta(days=7),
        }
        
        # Cache & Session Configuration
        if USE_REDIS:
            try:
                import redis
                redis_client = redis.from_url(REDIS_URL)
                config.update({
                    'CACHE_TYPE': 'RedisCache',
                    'CACHE_REDIS_URL': REDIS_URL,
                    'CACHE_DEFAULT_TIMEOUT': 300,
                    'CACHE_THRESHOLD': 2000,
                    
                    'SESSION_TYPE': 'redis',
                    'SESSION_PERMANENT': True,
                    'SESSION_USE_SIGNER': True,
                    'SESSION_REDIS': redis_client,
                    'SESSION_KEY_PREFIX': 'tickzen:session:'
                })
            except ImportError:
                print("Redis library not installed, fallback to local cache/session")
                USE_REDIS = False
            except Exception as e:
                print(f"Failed to connect to Redis: {e}, fallback to local cache/session")
                USE_REDIS = False
        
        if not USE_REDIS:
            config.update({
                'CACHE_TYPE': 'SimpleCache',
                'CACHE_DEFAULT_TIMEOUT': 300,
                'CACHE_THRESHOLD': 500,
                'SESSION_TYPE': 'filesystem',
                'SESSION_FILE_DIR': os.path.join(app_root, '..', 'flask_session'),
                'SESSION_PERMANENT': True,
                'SESSION_USE_SIGNER': True
            })
            
        return config

    @staticmethod
    def get_app_env():
        """Get current environment (development/production)"""
        env = os.getenv('APP_ENV', 'development').lower()
        if os.getenv('WEBSITE_SITE_NAME') or os.getenv('WEBSITE_INSTANCE_ID'):
            env = 'production'
        return env

    @staticmethod
    def get_socketio_config(app):
        """Get SocketIO configuration based on environment"""
        env = Config.get_app_env()
        
        REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        USE_REDIS = os.getenv('USE_REDIS', 'False').lower() == 'true'
        
        config = {}
        
        if env == 'production':
            try:
                from config.production_config import SOCKETIO_PROD_CONFIG
                config = SOCKETIO_PROD_CONFIG.copy() # Avoid modifying original
            except ImportError:
                config = {
                    'async_mode': 'threading', # Or 'eventlet'/'gevent' if installed
                    'cors_allowed_origins': "*",
                    'ping_timeout': 60,
                    'ping_interval': 25,
                    'logger': False,
                    'engineio_logger': False
                }
        else:
            try:
                from config.development_config import SOCKETIO_DEV_CONFIG
                config = SOCKETIO_DEV_CONFIG.copy()
            except ImportError:
                config = {
                    'cors_allowed_origins': "*",
                    'ping_timeout': 120,
                    'ping_interval': 30,
                    'logger': True,
                    'engineio_logger': True,
                    'async_mode': 'threading'
                }

        # Add Message Queue if Redis is enabled
        if USE_REDIS:
            config['message_queue'] = REDIS_URL
            
        return config
