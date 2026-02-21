"""
Stock Analysis Blueprint
========================

This blueprint handles all stock analysis related routes:
- Dashboard
- Analyzer
- Analytics
- AI Assistant
- Market News (via market_news blueprint)
- Reports

Routes:
-------
/stock-analysis/dashboard - Stock analysis dashboard
/stock-analysis/analyzer - Stock analysis input form
/stock-analysis/analytics - Portfolio analytics
/stock-analysis/ai-assistant - AI chatbot
/stock-analysis/api/reports - User reports API
/stock-analysis/market-news - Market news (redirects to market_news blueprint)

Note: This blueprint uses late-binding pattern to avoid circular imports.
Dependencies are registered via register_dependencies() before blueprint registration.
"""

from flask import Blueprint, render_template, jsonify, session, current_app, redirect, url_for, request
from functools import wraps
import time
import sys

# --- Callback Registry ---
# These will be set by main_portal_app after initialization via register_dependencies()
_login_required_func = None
_get_report_history_func = None


def register_dependencies(login_required_func=None, get_report_history_func=None):
    """
    Register dependencies from main_portal_app.
    Called before blueprint registration to avoid circular imports.
    
    Args:
        login_required_func: The login_required decorator from main_portal_app
        get_report_history_func: The get_report_history_for_user function
    """
    global _login_required_func, _get_report_history_func
    _login_required_func = login_required_func
    _get_report_history_func = get_report_history_func


def login_required(f):
    """
    Wrapper for the login_required decorator.
    Uses the registered function from main_portal_app.
    Defers registration check to REQUEST TIME, not decorator time.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check at RUNTIME, not at decorator application time
        if _login_required_func:
            # Delegate to the registered login_required function
            return _login_required_func(f)(*args, **kwargs)
        else:
            # Fallback: DENY access if registration was missed
            current_app.logger.error(
                "SECURITY: login_required called in stock_analysis blueprint but "
                "no auth function was registered. Denying access to: %s",
                request.path,
            )
            return redirect(url_for('login'))
    return decorated_function


def get_report_history_for_user(user_uid, display_limit=10):
    """
    Wrapper for getting report history.
    Uses the registered function from main_portal_app.
    """
    if _get_report_history_func:
        return _get_report_history_func(user_uid, display_limit=display_limit)
    else:
        current_app.logger.warning("get_report_history_func not registered")
        return [], 0


# Create blueprint
stock_analysis_bp = Blueprint('stock_analysis', __name__, url_prefix='/stock-analysis')

# Shared caching helpers from automation utilities
from app.blueprints.automation_utils import get_cache


@stock_analysis_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Stock analysis dashboard page.
    
    Renders immediately without blocking on data fetch.
    Data is loaded asynchronously via API.
    """
    return render_template('stock_analysis/dashboard.html', title="Dashboard - Tickzen")


@stock_analysis_bp.route('/api/reports')
@login_required
def api_reports():
    """
    API endpoint for async report history loading.
    
    Returns JSON with user's stock analysis reports.
    """
    try:
        start = time.time()
        user_uid = session.get('firebase_user_uid')
        
        if not user_uid:
            return jsonify({
                'error': 'User not authenticated',
                'reports': [],
                'total_reports': 0
            }), 401

        cache = get_cache()
        cache_key = f'stock_reports_{user_uid}'

        # Fast path: return cached response when available
        if cache:
            cached = cache.get(cache_key)
            if cached:
                return jsonify(cached), 200
        
        # Fetch report history
        report_history, total_reports = get_report_history_for_user(user_uid, display_limit=10)
        
        # Convert reports to JSON-serializable format
        reports_data = []
        for report in report_history:
            report_dict = {
                'ticker': report.ticker if hasattr(report, 'ticker') else report.get('ticker'),
                'filename': report.filename if hasattr(report, 'filename') else report.get('filename'),
                'generated_at': (
                    report.generated_at.strftime('%Y-%m-%d %I:%M %p UTC')
                    if hasattr(report, 'generated_at') and report.generated_at
                    else report.get('generated_at', 'N/A')
                ),
                'storage_location': (
                    report.storage_location
                    if hasattr(report, 'storage_location')
                    else report.get('storage_location')
                ),
                'content_available': (
                    report.content_available
                    if hasattr(report, 'content_available')
                    else report.get('content_available', True)
                ),
                'file_exists': (
                    report.file_exists
                    if hasattr(report, 'file_exists')
                    else report.get('file_exists', True)
                ),
                'has_storage_path': (
                    report.has_storage_path
                    if hasattr(report, 'has_storage_path')
                    else report.get('has_storage_path', False)
                )
            }
            reports_data.append(report_dict)
        
        elapsed = time.time() - start
        current_app.logger.info(
            f"API /stock-analysis/api/reports completed in {elapsed:.3f}s - "
            f"returned {len(reports_data)} reports"
        )
        
        response_payload = {
            'reports': reports_data,
            'total_reports': total_reports,
            'count': len(reports_data),
            'load_time': round(elapsed, 3)
        }

        # Cache for 5 minutes to match automation dashboards
        if cache:
            cache.set(cache_key, response_payload, timeout=300)

        return jsonify(response_payload), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in /stock-analysis/api/reports: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'reports': [],
            'total_reports': 0
        }), 500


@stock_analysis_bp.route('/analytics')
def analytics():
    """Portfolio analytics dashboard with interactive charts."""
    return render_template('stock_analysis/analytics.html', title="Portfolio Analytics - Tickzen")


@stock_analysis_bp.route('/analyzer', methods=['GET'])
def analyzer():
    """Stock analysis input form."""
    return render_template('stock_analysis/analyzer.html', title="Stock Analyzer Input")


@stock_analysis_bp.route('/ai-assistant')
def ai_assistant():
    """Tickzen AI Assistant chatbot page."""
    return render_template('stock_analysis/ai_assistant.html', title="Tickzen AI Assistant")
