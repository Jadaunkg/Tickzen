"""
Earnings Report Automation Blueprint
====================================

This blueprint handles earnings report automation routes:
- Dashboard
- Run Automation
- Earnings Calendar
- Publishing History

Routes:
-------
/automation/earnings/dashboard - Earnings automation dashboard
/automation/earnings/run - Run earnings automation
/automation/earnings/calendar - Weekly earnings calendar
/automation/earnings/history - Publishing history (redirects to shared history)
"""

from flask import Blueprint, render_template, redirect, url_for, session, current_app
import os
import json
from datetime import datetime

# Always create a fresh blueprint - Flask handles duplicate registration checks internally
earnings_automation_bp = Blueprint('earnings_automation', __name__, url_prefix='/earnings')

# Import dependencies from shared utils module (no circular import)
from app.blueprints.automation_utils import (
    login_required,
    get_user_site_profiles_from_firestore,
    get_automation_shared_context,
    get_project_root
)


@earnings_automation_bp.route('/dashboard')
@login_required
def dashboard():
    """Earnings automation dashboard - shows overview and stats."""
    user_uid = session['firebase_user_uid']
    
    # Get user site profiles
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    
    # Get shared context for automation
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    # Calculate earnings-specific stats
    earnings_published = 0
    success_rate = 0
    
    # Load weekly earnings calendar for upcoming earnings
    upcoming_earnings = []
    project_root = get_project_root()
    calendar_path = os.path.join(project_root, 'data', 'weekly_earnings_calendar.json') if project_root else None
    if calendar_path and os.path.exists(calendar_path):
        try:
            with open(calendar_path, 'r', encoding='utf-8') as f:
                calendar_data = json.load(f)
                
                if isinstance(calendar_data, dict) and 'calendar' in calendar_data:
                    calendar = calendar_data.get('calendar', {})
                else:
                    calendar = calendar_data
                
                # Get today's day name
                today = datetime.now().strftime('%A')
                
                # Flatten calendar to get upcoming earnings
                for day, companies in calendar.items():
                    if isinstance(companies, list):
                        for company in companies[:5]:  # Limit per day
                            upcoming_earnings.append({
                                'ticker': company.get('ticker', 'N/A'),
                                'company': company.get('company_name', company.get('ticker', 'Unknown')),
                                'day': day,
                                'time': company.get('time', 'N/A')
                            })
                
                # Limit total upcoming earnings
                upcoming_earnings = upcoming_earnings[:10]
                
        except Exception as e:
            current_app.logger.error(f"Error loading earnings calendar for dashboard: {e}")
    
    return render_template('automation/earnings/dashboard.html',
                         title="Earnings Dashboard - Tickzen",
                         user_site_profiles=user_site_profiles,
                         earnings_published=earnings_published,
                         upcoming_count=len(upcoming_earnings),
                         success_rate=success_rate,
                         connected_sites=len(user_site_profiles) if user_site_profiles else 0,
                         upcoming_earnings=upcoming_earnings,
                         **shared_context)


@earnings_automation_bp.route('/run')
@login_required
def run():
    """Run earnings report automation."""
    user_uid = session['firebase_user_uid']
    
    # Get user site profiles
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    
    # Get shared context for automation
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    # Load weekly earnings calendar
    earnings_calendar = None
    last_refreshed = None
    last_refreshed_date = None
    calendar_outdated = False
    
    project_root = get_project_root()
    calendar_path = os.path.join(project_root, 'data', 'weekly_earnings_calendar.json') if project_root else None
    if calendar_path and os.path.exists(calendar_path):
        try:
            with open(calendar_path, 'r', encoding='utf-8') as f:
                calendar_data = json.load(f)
                
                # Check if it's the new format with metadata
                if isinstance(calendar_data, dict) and 'calendar' in calendar_data:
                    earnings_calendar = calendar_data.get('calendar', {})
                    last_refreshed = calendar_data.get('last_refreshed')
                    last_refreshed_date = calendar_data.get('last_refreshed_date')
                    
                    # Check if calendar is outdated (older than today)
                    if last_refreshed_date:
                        refresh_date = datetime.strptime(last_refreshed_date, '%Y-%m-%d').date()
                        today = datetime.now().date()
                        calendar_outdated = refresh_date < today
                else:
                    # Old format without metadata
                    earnings_calendar = calendar_data
                    calendar_outdated = True  # Assume outdated if no metadata
                    
        except Exception as e:
            current_app.logger.error(f"Error loading earnings calendar: {e}")
    
    return render_template('automation/earnings/run.html',
                         title="Earnings Report Automation - Tickzen",
                         user_site_profiles=user_site_profiles,
                         earnings_calendar=earnings_calendar,
                         last_refreshed=last_refreshed,
                         last_refreshed_date=last_refreshed_date,
                         calendar_outdated=calendar_outdated,
                         **shared_context)


@earnings_automation_bp.route('/calendar')
@login_required
def calendar():
    """Weekly earnings calendar view."""
    import json
    import os
    from datetime import datetime
    
    # Load earnings calendar data
    calendar_data = None
    total_earnings = 0
    busiest_day_count = 0
    avg_per_day = 0
    
    try:
        calendar_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'weekly_earnings_calendar.json')
        if os.path.exists(calendar_path):
            with open(calendar_path, 'r') as f:
                calendar_data = json.load(f)
                
            # Calculate statistics
            if calendar_data and 'calendar' in calendar_data:
                for date, earnings_list in calendar_data['calendar'].items():
                    count = len(earnings_list)
                    total_earnings += count
                    busiest_day_count = max(busiest_day_count, count)
                    
                num_days = len(calendar_data['calendar'])
                avg_per_day = total_earnings / num_days if num_days > 0 else 0
                
    except Exception as e:
        print(f"Error loading earnings calendar: {e}")
        calendar_data = None
    
    user_uid = session['firebase_user_uid']
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    return render_template('automation/earnings/calendar.html',
                         title="Earnings Calendar - Tickzen",
                         user_site_profiles=user_site_profiles,
                         calendar_data=calendar_data,
                         total_earnings=total_earnings,
                         busiest_day_count=busiest_day_count,
                         avg_per_day=avg_per_day,
                         **shared_context)


@earnings_automation_bp.route('/history')
@login_required
def history():
    """Redirect to global publishing history."""
    return redirect(url_for('automation.history'))
