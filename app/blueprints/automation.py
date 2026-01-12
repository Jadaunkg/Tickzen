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

from flask import Blueprint, render_template, redirect, url_for, session
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
    get_automation_shared_context
)


@automation_bp.route('/overview')
@login_required
def overview():
    """
    Automation hub overview page.
    
    Shows an overview of all automation types with quick access links.
    """
    user_uid = session['firebase_user_uid']
    
    # Get user site profiles for context
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    
    # Get shared context for automation
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    # Calculate stats for the overview
    total_sites = len(user_site_profiles) if user_site_profiles else 0
    
    return render_template('automation/overview.html',
                         title="Automation Hub - Tickzen",
                         total_sites=total_sites,
                         **shared_context)


@automation_bp.route('/history')
@login_required
def history():
    """Shared publishing history for all automation types."""
    user_uid = session['firebase_user_uid']
    
    # Get user site profiles for context
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    
    # Get shared context for automation
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    return render_template('automation/history.html',
                         title="Publishing History - Tickzen",
                         user_site_profiles=user_site_profiles,
                         **shared_context)
