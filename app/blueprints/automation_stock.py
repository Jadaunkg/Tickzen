"""
Stock Analysis Automation Blueprint
===================================

This blueprint handles stock analysis automation routes:
- Dashboard
- Run Automation
- Manage Profiles
- Publishing History

Routes:
-------
/automation/stock-analysis/dashboard - Stock automation dashboard
/automation/stock-analysis/run - Run stock automation
/automation/stock-analysis/profiles - Manage WordPress profiles
/automation/stock-analysis/history - Publishing history (redirects to shared history)
"""

from flask import Blueprint, render_template, redirect, url_for, session, current_app, request, flash, jsonify
import time
import sys
import os

# Add project root to path when running directly
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Always create a fresh blueprint - Flask handles duplicate registration checks internally
stock_automation_bp = Blueprint('stock_automation', __name__, url_prefix='/stock-analysis')

# Import dependencies from shared utils module (no circular import)
from app.blueprints.automation_utils import (
    login_required,
    get_user_site_profiles_from_firestore,
    get_automation_shared_context,
    ALL_SECTIONS,
    get_cache
)


@stock_automation_bp.route('/dashboard')
@login_required
def dashboard():
    """Stock analysis automation dashboard - Instant load with skeleton."""
    return render_template('automation/stock_analysis/dashboard.html', 
                           title="Stock Analysis Dashboard - Tickzen")


@stock_automation_bp.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    """API endpoint to fetch dashboard stats with caching."""
    cache = get_cache()
    user_uid = session['firebase_user_uid']
    
    # Try to get from cache first (5 minute cache)
    cache_key = f'stock_dashboard_stats_{user_uid}'
    
    if cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
    
    # Fetch data if not cached
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    connected_sites = len(user_site_profiles) if user_site_profiles else 0
    
    response_data = {
        'connected_sites': connected_sites,
        'stock_published': 0,  # TODO: Fetch from Firestore
        'total_tickers': 0,    # TODO: Fetch from Firestore
        'success_rate': "100%",
        'recent_reports': [],  # TODO: Fetch recent reports
        'has_profiles': shared_context.get('has_profiles', False),
        **shared_context
    }
    
    # Cache for 5 minutes
    if cache:
        cache.set(cache_key, response_data, timeout=300)
    
    return jsonify(response_data)


@stock_automation_bp.route('/run')
@login_required
def run():
    """Run stock analysis automation."""
    start = time.time()
    user_uid = session['firebase_user_uid']
    
    t1 = time.time()
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    t2 = time.time()
    current_app.logger.info(f"get_user_site_profiles_from_firestore took {t2-t1:.3f} seconds")
    
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    t3 = time.time()
    current_app.logger.info(f"get_automation_shared_context took {t3-t2:.3f} seconds")
    
    result = render_template('automation/stock_analysis/run.html',
                           title="Run Automation - Tickzen",
                           user_site_profiles=user_site_profiles,
                           **shared_context)
    t4 = time.time()
    current_app.logger.info(f"render_template took {t4-t3:.3f} seconds")
    current_app.logger.info(f"/automation/stock-analysis/run total time: {t4-start:.3f} seconds")
    return result


@stock_automation_bp.route('/profiles')
@login_required
def profiles():
    """Manage WordPress site profiles."""
    user_uid = session['firebase_user_uid']
    profiles = get_user_site_profiles_from_firestore(user_uid)
    shared_context = get_automation_shared_context(user_uid, profiles)
    
    form_data_add = session.pop('form_data_add_repopulate', None)
    show_add_form_on_load_flag = session.pop('show_add_form_on_load_flag', False)
    errors_add_repopulate = session.pop('errors_add_repopulate', None)

    return render_template('automation/stock_analysis/profiles.html',
                           title="Publishing Profiles - Tickzen",
                           profiles=profiles,
                           all_report_sections=ALL_SECTIONS,
                           form_data_add=form_data_add,
                           show_add_form_on_load=show_add_form_on_load_flag,
                           errors_add=errors_add_repopulate,
                           **shared_context)


@stock_automation_bp.route('/history')
@login_required
def history():
    """Redirect to global publishing history."""
    return redirect(url_for('automation.history'))
