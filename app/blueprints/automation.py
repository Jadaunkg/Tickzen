"""
Automation Hub Blueprint
========================

This blueprint serves as the main hub for all automation features:
- Stock Analysis Automation
- Earnings Report Automation
- Sports Article Automation

Routes:
-------
/automation/overview - Main automation hub overview page
/automation/history - Shared publishing history for all automation types
"""

from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
import sys
import os

# Force fresh blueprint on each import to handle Flask reloader properly
# This is needed because Flask's reloader re-imports modules but keeps cached objects
_force_new = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

# Create main automation blueprint
automation_bp = Blueprint('automation', __name__, url_prefix='/automation')

# Import dependencies from shared utils module (no circular import)
from app.blueprints.automation_utils import (
    login_required,
    get_user_site_profiles_from_firestore,
    get_automation_shared_context,
    get_cache
)


@automation_bp.route('/overview')
@login_required
def overview():
    """
    Automation hub overview page - Instant load with skeleton.
    Data is fetched via AJAX after page renders.
    """
    # Just render the page shell immediately - no data fetching
    return render_template('automation/overview.html',
                         title="Automation Hub - Tickzen")


@automation_bp.route('/api/overview-stats')
@login_required
def api_overview_stats():
    """
    API endpoint to fetch overview stats with caching.
    Called via AJAX after page loads for better perceived performance.
    """
    cache = get_cache()
    user_uid = session['firebase_user_uid']
    
    # Try to get from cache first (5 minute cache)
    cache_key = f'overview_stats_{user_uid}'
    
    if cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
    
    # Fetch data if not cached
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    # Calculate stats
    total_sites = len(user_site_profiles) if user_site_profiles else 0
    
    response_data = {
        'total_sites': total_sites,
        'total_published_count': shared_context.get('total_published_count', 0),
        'this_week_count': shared_context.get('this_week_count', 0),
        'pending_count': shared_context.get('pending_count', 0),
        'has_profiles': shared_context.get('has_profiles', False),
        'user_site_profiles': user_site_profiles or [],
        'recent_activity': shared_context.get('recent_activity', [])
    }
    
    # Cache for 5 minutes
    if cache:
        cache.set(cache_key, response_data, timeout=300)
    
    return jsonify(response_data)


@automation_bp.route('/history')
@login_required
def history():
    """Shared publishing history for all automation types."""
    user_uid = session['firebase_user_uid']
    
    # Get article type filter from URL parameter
    filter_article_type = request.args.get('type', None)
    
    # Debug logging
    print(f"DEBUG: URL args: {request.args}")
    print(f"DEBUG: filter_article_type: '{filter_article_type}'")
    print(f"DEBUG: Full URL: {request.url}")
    
    # Get user site profiles for context
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    
    # Get shared context for automation
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    return render_template('automation/history.html',
                         title="Publishing History - Tickzen",
                         user_site_profiles=user_site_profiles,
                         filter_article_type=filter_article_type,
                         **shared_context)
