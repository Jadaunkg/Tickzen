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

from flask import Blueprint, render_template, redirect, url_for, session, current_app, jsonify
from google.cloud.firestore_v1.base_query import FieldFilter
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
    """Earnings automation dashboard - Instant load with skeleton."""
    return render_template('automation/earnings/dashboard.html',
                         title="Earnings Dashboard - Tickzen")


@earnings_automation_bp.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    """API endpoint to fetch earnings dashboard stats with caching."""
    from app.blueprints.automation_utils import get_firestore_client, get_cache
    from datetime import datetime, timezone, timedelta
    
    cache = get_cache()
    user_uid = session.get('firebase_user_uid')
    
    if not user_uid:
        current_app.logger.error("No user_uid available in session, cannot fetch earnings data")
        return jsonify({
            'error': 'No user authentication found',
            'connected_sites': 0,
            'earnings_reports_published': 0,
            'total_companies_analyzed': 0,
            'upcoming_count': 0,
            'success_rate': '0%',
            'recent_reports': [],
            'upcoming_earnings': [],
            'has_profiles': False
        })
    
    # Try to get from cache first (5 minute cache) - but check for cache bust parameter
    cache_key = f'earnings_dashboard_stats_{user_uid}'
    
    # Allow cache busting for debugging
    from flask import request
    cache_bust = request.args.get('cache_bust', '0')
    
    if cache and cache_bust == '0':
        cached_data = cache.get(cache_key)
        if cached_data:
            current_app.logger.info(f"Returning cached data for user {user_uid}")
            return jsonify(cached_data)
    else:
        current_app.logger.info(f"Cache busting enabled or no cache available")
    
    # Fetch data if not cached
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    connected_sites = len(user_site_profiles) if user_site_profiles else 0
    
    # Initialize earnings stats
    earnings_reports_published = 0
    total_companies_analyzed = 0
    success_rate = "100%"
    recent_reports = []
    upcoming_earnings = []
    
    # Fetch real earnings data from Firestore
    db = get_firestore_client()
    if db:
        try:
            # Get ALL articles first to debug what's available
            all_articles_query = db.collection('userPublishedArticles')\
                .where(filter=FieldFilter('user_uid', '==', user_uid))
            
            all_articles = list(all_articles_query.stream())
            
            # Debug: Count article types
            article_type_counts = {}
            for article_doc in all_articles:
                article_type = article_doc.to_dict().get('article_type', 'MISSING')
                article_type_counts[article_type] = article_type_counts.get(article_type, 0) + 1
            current_app.logger.info(f"Article type counts for user {user_uid}: {article_type_counts}")
            
            # Filter for earnings articles in Python
            earnings_articles = [article for article in all_articles 
                               if article.to_dict().get('article_type') == 'earnings']
            
            current_app.logger.info(f"Found {len(earnings_articles)} earnings articles out of {len(all_articles)} total")
            
            # If no earnings articles found, check for articles that might be earnings based on title/content
            if not earnings_articles:
                current_app.logger.info("No articles with article_type='earnings', checking for earnings keywords in titles")
                # Look for articles with earnings-related keywords in title
                earnings_keywords = ['earnings', 'quarterly', 'q1', 'q2', 'q3', 'q4', 'revenue', 'eps', 'financials', 'report']
                keyword_matches = []
                for article_doc in all_articles:
                    article_data = article_doc.to_dict()
                    title = (article_data.get('title', '') or '').lower()
                    matched_keywords = [kw for kw in earnings_keywords if kw in title]
                    if matched_keywords:
                        keyword_matches.append((article_doc, matched_keywords))
                        earnings_articles.append(article_doc)
                
                current_app.logger.info(f"Found {len(keyword_matches)} articles with earnings keywords")
                for article_doc, keywords in keyword_matches[:5]:  # Log first 5
                    title = article_doc.to_dict().get('title', 'No title')
                    current_app.logger.info(f"  - '{title[:50]}...' matched: {keywords}")
            
            earnings_reports_published = len([article for article in earnings_articles 
                                            if article.to_dict().get('status') == 'published'])
            
            # Get total unique companies analyzed
            unique_companies = set()
            recent_reports_data = []
            
            for article_doc in earnings_articles:
                article_data = article_doc.to_dict()
                ticker = article_data.get('ticker', '')
                company = article_data.get('company_name', ticker)
                if company:
                    unique_companies.add(company.upper())
                
                # Build recent reports (last 10)
                if len(recent_reports_data) < 10:
                    published_at_str = article_data.get('published_at', '')
                    report_data = {
                        'title': article_data.get('title', 'Earnings Analysis Report'),
                        'ticker': ticker.upper() if ticker else 'N/A',
                        'company': company or 'Unknown Company',
                        'site': article_data.get('site', article_data.get('profile_name', 'Site')),
                        'status': article_data.get('status', 'draft'),
                        'published_at': published_at_str,
                        'earnings_date': article_data.get('earnings_date', ''),
                        'article_type': article_data.get('article_type', 'MISSING')  # Debug field
                    }
                    recent_reports_data.append(report_data)
                    current_app.logger.info(f"Added recent report: {report_data['ticker']} - {report_data['title'][:30]}... [{report_data['article_type']}]")
            
            total_companies_analyzed = len(unique_companies)
            
            # Sort recent reports by published_at descending
            recent_reports_data.sort(key=lambda x: x.get('published_at', ''), reverse=True)
            recent_reports = recent_reports_data[:10]
            
            # Calculate success rate (published / total)
            if earnings_articles:
                success_count = sum(1 for article in earnings_articles 
                                  if article.to_dict().get('status') == 'published')
                success_rate = f"{int((success_count / len(earnings_articles)) * 100)}%"
            
        except Exception as e:
            current_app.logger.error(f"Error fetching earnings dashboard stats for user {user_uid}: {e}", exc_info=True)
    
    # Load upcoming earnings from calendar
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
                
                # Flatten calendar to get upcoming earnings  
                for date_key, companies in calendar.items():
                    if isinstance(companies, list):
                        # Convert date_key (YYYY-MM-DD format) to proper day name
                        try:
                            date_obj = datetime.strptime(date_key, '%Y-%m-%d')
                            day_name = date_obj.strftime('%A')  # Full day name like "Monday"
                            short_date = date_obj.strftime('%m/%d')  # MM/DD format
                        except ValueError:
                            # Fallback if date parsing fails
                            day_name = date_key
                            short_date = date_key
                            
                        for company in companies[:5]:  # Limit per day
                            upcoming_earnings.append({
                                'ticker': company.get('ticker', 'N/A'),
                                'company': company.get('name') or company.get('company_name') or company.get('ticker', 'Unknown'),
                                'day': f"{day_name[:3]} {short_date}",  # "Mon 01/13"
                                'time': company.get('time', 'BMO')  # Default to Before Market Open
                            })
                
                # Limit total upcoming earnings
                upcoming_earnings = upcoming_earnings[:10]
                
        except Exception as e:
            current_app.logger.error(f"Error loading earnings calendar for dashboard: {e}")
    
    response_data = {
        'connected_sites': connected_sites,
        'earnings_reports_published': earnings_reports_published,
        'total_companies_analyzed': total_companies_analyzed,
        'upcoming_count': len(upcoming_earnings),
        'success_rate': success_rate,
        'recent_reports': recent_reports,
        'upcoming_earnings': upcoming_earnings,
        'has_profiles': shared_context.get('has_profiles', False)
    }
    
    # Final debug log
    current_app.logger.info(f"Earnings Dashboard Response Summary:")
    current_app.logger.info(f"  User: {user_uid}")
    current_app.logger.info(f"  Earnings Published: {earnings_reports_published}")
    current_app.logger.info(f"  Companies Analyzed: {total_companies_analyzed}")
    current_app.logger.info(f"  Recent Reports: {len(recent_reports)}")
    current_app.logger.info(f"  Upcoming Earnings: {len(upcoming_earnings)}")
    current_app.logger.info(f"  Success Rate: {success_rate}")
    
    # Cache for 5 minutes
    if cache:
        cache.set(cache_key, response_data, timeout=300)
    
    return jsonify(response_data)


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
