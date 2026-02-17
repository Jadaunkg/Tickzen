import os
import sys
from datetime import datetime
from flask import current_app, session, url_for
from werkzeug.routing import BuildError
from app.core.config import Config, PROJECT_ROOT

def safe_url_for(endpoint, **kwargs):
    """
    Safe url_for that gracefully handles missing endpoints.
    Returns '/' if the endpoint doesn't exist.
    """
    try:
        return url_for(endpoint, **kwargs)
    except (BuildError, Exception):
        # Fallback: return root path or a sensible default
        return '/'

def inject_firebase_config():
    """Inject Firebase configuration into all templates"""
    # Ensure environment variables are loaded before reading config
    Config.load_env()
    return {'firebase_config': Config.get_firebase_client_config()}

def inject_date():
    """Inject the current date into all templates"""
    return {'now': datetime.now()}

def inject_user_session():
    """Inject user session context for nav rendering."""
    return {
        'is_user_logged_in': 'firebase_user_uid' in session,
        'user_email': session.get('firebase_user_email'),
        'user_displayName': session.get('firebase_user_displayName')
    }

def inject_seo_config():
    """Inject SEO configuration into all templates"""
    print("DEBUG: inject_seo_config running")
    # Try to import from config/seo_config.py
    try:
        # Add project root to path if not already there to find config module
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
            
        from config.seo_config import (
            GOOGLE_ANALYTICS_ID, 
            GOOGLE_VERIFICATION_CODE, 
            BING_VERIFICATION_CODE,
            TWITTER_HANDLE,
            SUPPORT_EMAIL,
            COMPANY_NAME
        )
        
        # Use environment variables in production, fallback to seo_config values
        return {
            'seo_config': {
                'google_analytics_id': os.getenv('GOOGLE_ANALYTICS_ID', GOOGLE_ANALYTICS_ID),
                'google_verification_code': os.getenv('GOOGLE_VERIFICATION_CODE', GOOGLE_VERIFICATION_CODE),
                'bing_verification_code': os.getenv('BING_VERIFICATION_CODE', BING_VERIFICATION_CODE),
                'twitter_handle': os.getenv('TWITTER_HANDLE', TWITTER_HANDLE),
                'support_email': os.getenv('SUPPORT_EMAIL', SUPPORT_EMAIL),
                'company_name': os.getenv('COMPANY_NAME', COMPANY_NAME)
            }
        }
    except ImportError:
        # Fallback if config module is missing
        print("DEBUG: ImportError in inject_seo_config")
        return {
            'seo_config': {
                'google_analytics_id': os.getenv('GOOGLE_ANALYTICS_ID', ''),
                'google_verification_code': os.getenv('GOOGLE_VERIFICATION_CODE', ''),
                'bing_verification_code': os.getenv('BING_VERIFICATION_CODE', ''),
                'twitter_handle': os.getenv('TWITTER_HANDLE', '@tickzen'),
                'support_email': os.getenv('SUPPORT_EMAIL', 'support@tickzen.app'),
                'company_name': os.getenv('COMPANY_NAME', 'Tickzen')
            }
        }

def inject_service_urls():
    """Inject service base URLs for cross-service navigation."""
    automation_base_url = os.getenv('AUTOMATION_BASE_URL', '').rstrip('/')
    return {
        'automation_base_url': automation_base_url,
        'admin_tools_enabled': os.getenv('ENABLE_ADMIN_TOOLS', 'false').lower() == 'true'
    }

def register_context_processors(app):
    """Register all global context processors"""
    print("DEBUG: Registering context processors")
    app.context_processor(inject_firebase_config)
    app.context_processor(inject_date)
    app.context_processor(inject_user_session)
    app.context_processor(inject_seo_config)
    app.context_processor(inject_service_urls)
    
    # Override Jinja's url_for to handle missing endpoints gracefully
    # Store original url_for for reference
    original_url_for = app.jinja_env.globals.get('url_for', url_for)
    
    def safe_jinja_url_for(endpoint, **kwargs):
        """Wrapped url_for that handles missing endpoints"""
        try:
            return original_url_for(endpoint, **kwargs)
        except (BuildError, Exception):
            return '/'
    
    app.jinja_env.globals['url_for'] = safe_jinja_url_for
    
    # Also register safe_url_for and safe_jinja_url_for for explicit use if needed
    app.jinja_env.globals['safe_url_for'] = safe_url_for
    app.jinja_env.globals['safe_jinja_url_for'] = safe_jinja_url_for
    
    # Ensure seo_config is always present for templates rendered early
    try:
        app.jinja_env.globals.setdefault('seo_config', inject_seo_config().get('seo_config', {}))
    except Exception:
        app.jinja_env.globals.setdefault('seo_config', {
            'google_analytics_id': '',
            'google_verification_code': '',
            'bing_verification_code': '',
            'twitter_handle': '@tickzen',
            'support_email': 'support@tickzen.app',
            'company_name': 'Tickzen'
        })
    # Ensure firebase_config is always present for templates rendered early
    try:
        app.jinja_env.globals.setdefault('firebase_config', inject_firebase_config().get('firebase_config', {}))
    except Exception:
        app.jinja_env.globals.setdefault('firebase_config', {
            'apiKey': '',
            'authDomain': '',
            'projectId': '',
            'storageBucket': '',
            'messagingSenderId': '',
            'appId': ''
        })
