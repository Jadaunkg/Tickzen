from functools import wraps
from flask import session, request, redirect, url_for, current_app, flash, jsonify
from werkzeug.routing import BuildError
from app.core.database import get_firebase_app_initialized, FIREBASE_INITIALIZED_SUCCESSFULLY

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get current Firebase initialization status
        # We try to use the imported function, but fallback to global flag if function fails/mocked differently
        try:
            status = get_firebase_app_initialized()
        except:
            status = FIREBASE_INITIALIZED_SUCCESSFULLY
            
        if not status:
            current_app.logger.error("Login attempt failed: Firebase Admin SDK not initialized.")
            session['notification_message'] = "Authentication service is currently unavailable. Please try again later."
            session['notification_type'] = "danger"
            try:
                return redirect(url_for('login'))
            except (BuildError, Exception):
                return redirect('/')

        if 'firebase_user_uid' not in session:
            # Check for Authorization header (Bearer token) for API access
            # This is optional enhancement but good for separation later
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                # Verify logic would go here, omitting for exact parity first
                pass
            
            # API requests should get JSON 401
            if request.path.startswith('/api/') and not request.path.startswith('/api/auth'):
                return {'error': 'Unauthorized', 'message': 'Please login to continue'}, 401

            session['notification_message'] = "Please login to access this page."
            session['notification_type'] = "warning"
            # Use request.full_path to preserve query params like ?next=/dashboard
            next_url = request.full_path if request.full_path != '/' else None
            # Handle next_url encoding if needed
            try:
                login_url = url_for('login')
                if next_url:
                    from urllib.parse import urlencode
                    login_url = f"{login_url}?{urlencode({'next': next_url})}"
                return redirect(login_url)
            except (BuildError, Exception):
                # Fallback for services that do not expose a login endpoint
                return redirect('/')
            
        return f(*args, **kwargs)
        
    return decorated_function

def admin_required(f):
    """Decorator to require admin access for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First ensure user is logged in (reuse login_required logic or explicit check)
        if 'firebase_user_uid' not in session:
            if request.path.startswith('/api/'):
                 return {'error': 'Unauthorized'}, 401
            session['notification_message'] = "Please login to access admin area."
            session['notification_type'] = "warning"
            try:
                login_url = url_for('login')
                next_url = request.full_path
                if next_url:
                    from urllib.parse import urlencode
                    login_url = f"{login_url}?{urlencode({'next': next_url})}"
                return redirect(login_url)
            except (BuildError, Exception):
                return redirect('/')
            
        # Check admin claim or specific email
        # This is hardcoded for now as per main_portal_app.py reference
        admin_emails = [
            'admin@tickzen.com',
            'jadaunkg@gmail.com',
            'vishaal@tickzen.app'
        ]
        
        user_email = session.get('firebase_user_email', '').lower()
        is_admin = user_email in admin_emails
        
        if not is_admin:
            if request.path.startswith('/api/'):
                 return {'error': 'Forbidden'}, 403
            current_app.logger.warning(f"Non-admin user {user_email} attempted to access admin route: {request.endpoint}")
            session['notification_message'] = "Access denied. Administrator privileges required."
            session['notification_type'] = "danger"
            # For API requests, return JSON error. For HTML requests, redirect to root
            if request.accept_mimetypes.best == 'application/json':
                return jsonify({'error': 'Forbidden', 'message': 'Administrator privileges required.'}), 403
            return redirect('/')
            
        current_app.logger.info(f"Admin access granted to {user_email} for route: {request.endpoint}")
        return f(*args, **kwargs)
        
    return decorated_function
