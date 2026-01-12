"""
Automation Utilities Module
===========================

This module provides shared utilities for automation blueprints,
avoiding circular imports by using late binding patterns.

The functions are registered by main_portal_app after initialization,
and blueprints access them through this module.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, request, current_app

# --- Callback Registry ---
# These will be set by main_portal_app after initialization
_get_firestore_client = None
_get_firebase_app_initialized = None
_auto_publisher = None
_project_root = None
_cache = None  # Flask-Caching instance

# Section configuration
ALL_SECTIONS = [
    {"key": "company_overview", "name": "Company Overview", "icon": "building"},
    {"key": "financial_health", "name": "Financial Health", "icon": "chart-bar"},
    {"key": "stock_performance", "name": "Stock Performance", "icon": "chart-line"},
    {"key": "earnings_analysis", "name": "Earnings Analysis", "icon": "coins"},
    {"key": "valuation_metrics", "name": "Valuation Metrics", "icon": "calculator"},
    {"key": "technical_indicators", "name": "Technical Indicators", "icon": "wave-square"},
    {"key": "ownership_structure", "name": "Ownership Structure", "icon": "users"},
    {"key": "analyst_ratings", "name": "Analyst Ratings", "icon": "star"},
    {"key": "market_sentiment", "name": "Market Sentiment", "icon": "comments"},
    {"key": "risk_analysis", "name": "Risk Analysis", "icon": "exclamation-triangle"},
    {"key": "growth_metrics", "name": "Growth Metrics", "icon": "arrow-up"},
    {"key": "dividend_analysis", "name": "Dividend Analysis", "icon": "hand-holding-usd"},
    {"key": "sector_comparison", "name": "Sector Comparison", "icon": "chart-pie"},
    {"key": "profitability", "name": "Profitability", "icon": "percentage"},
    {"key": "cash_flow", "name": "Cash Flow Analysis", "icon": "money-bill-wave"},
    {"key": "debt_analysis", "name": "Debt Analysis", "icon": "file-invoice-dollar"},
    {"key": "sec_filings", "name": "SEC Filings Analysis", "icon": "file-alt"},
    {"key": "insider_activity", "name": "Insider Activity", "icon": "user-secret"},
    {"key": "ai_recommendations", "name": "AI Recommendations", "icon": "robot"},
    {"key": "competitive_position", "name": "Competitive Position", "icon": "chess-knight"},
    {"key": "esg_analysis", "name": "ESG Analysis", "icon": "leaf"},
    {"key": "revenue_breakdown", "name": "Revenue Breakdown", "icon": "sitemap"},
    {"key": "guidance_outlook", "name": "Guidance & Outlook", "icon": "binoculars"},
    {"key": "historical_performance", "name": "Historical Performance", "icon": "history"},
    {"key": "macro_impact", "name": "Macro Impact", "icon": "globe"},
    {"key": "volatility_analysis", "name": "Volatility Analysis", "icon": "bolt"},
    {"key": "liquidity_metrics", "name": "Liquidity Metrics", "icon": "tint"},
    {"key": "management_quality", "name": "Management Quality", "icon": "user-tie"},
    {"key": "patents_ip", "name": "Patents & IP", "icon": "lightbulb"},
    {"key": "supply_chain", "name": "Supply Chain", "icon": "truck"},
    {"key": "regulatory_environment", "name": "Regulatory Environment", "icon": "gavel"},
    {"key": "price_prediction", "name": "AI Price Prediction", "icon": "crystal-ball"}
]


def register_dependencies(get_firestore_client_func, get_firebase_app_initialized_func, 
                          auto_publisher_module=None, project_root=None, cache_instance=None):
    """
    Register dependencies from main_portal_app.
    Called after app initialization to avoid circular imports.
    """
    global _get_firestore_client, _get_firebase_app_initialized, _auto_publisher, _project_root, _cache
    _get_firestore_client = get_firestore_client_func
    _get_firebase_app_initialized = get_firebase_app_initialized_func
    _auto_publisher = auto_publisher_module
    _project_root = project_root
    _cache = cache_instance


def get_project_root():
    """Get the project root directory."""
    return _project_root


def get_cache():
    """Get the Flask-Caching instance."""
    return _cache


def login_required(f):
    """
    Decorator to require user authentication.
    Redirects to login page if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check Firebase initialization
        firebase_initialized = _get_firebase_app_initialized() if _get_firebase_app_initialized else False
        
        if not firebase_initialized:
            current_app.logger.error("Login attempt failed: Firebase Admin SDK not initialized.")
            flash("Authentication service is currently unavailable. Please try again later.", "danger")
            return redirect(url_for('stock_analysis_homepage_route'))
        
        if 'firebase_user_uid' not in session:
            flash("Please login to access this page.", "warning")
            return redirect(url_for('login', next=request.full_path))
        
        return f(*args, **kwargs)
    return decorated_function


def get_firestore_client():
    """Get the Firestore client."""
    if _get_firestore_client:
        return _get_firestore_client()
    return None


def get_user_site_profiles_from_firestore(user_uid, limit_profiles=20):
    """
    Fetch user's WordPress site profiles from Firestore.
    
    Args:
        user_uid: The user's Firebase UID
        limit_profiles: Maximum number of profiles to fetch
        
    Returns:
        List of profile dictionaries
    """
    from datetime import datetime, timezone
    
    # Check Firebase initialization
    firebase_initialized = _get_firebase_app_initialized() if _get_firebase_app_initialized else False
    if not firebase_initialized:
        return []
    
    db = get_firestore_client()
    if not db:
        current_app.logger.error(f"Firestore client not available for get_user_site_profiles_from_firestore (user: {user_uid}).")
        return []
    
    profiles = []
    try:
        profiles_ref = db.collection(u'userSiteProfiles').document(user_uid).collection(u'profiles').order_by(u'profile_name').limit(limit_profiles).stream()
        for profile_doc in profiles_ref:
            profile_data = profile_doc.to_dict()
            profile_data['profile_id'] = profile_doc.id
            profile_data.setdefault('authors', [])
            profile_data.setdefault('uploaded_ticker_file_name', None)
            profile_data.setdefault('ticker_file_storage_path', None)
            profile_data.setdefault('ticker_file_uploaded_at', None)
            profile_data.setdefault('ticker_count_from_file', None)
            profile_data.setdefault('ticker_preview_from_file', [])
            profile_data.setdefault('all_tickers_from_file', [])
            profiles.append(profile_data)
    except Exception as e:
        current_app.logger.error(f"Error fetching site profiles for user {user_uid} from Firestore: {e}", exc_info=True)
    
    return profiles


def get_automation_shared_context(user_uid, profiles_list, ticker_status_limit=5):
    """
    Get shared context for automation pages.
    
    Args:
        user_uid: The user's Firebase UID
        profiles_list: List of user's site profiles
        ticker_status_limit: Maximum number of ticker statuses to fetch per profile
        
    Returns:
        Dictionary with shared context data
    """
    from datetime import datetime, timezone, timedelta
    
    context = {}
    try:
        current_profile_ids = [p['profile_id'] for p in profiles_list if 'profile_id' in p]
        
        # Load state from auto_publisher if available
        if _auto_publisher:
            state = _auto_publisher.load_state(user_uid=user_uid, current_profile_ids_from_run=current_profile_ids)
        else:
            state = {}
        
        context['posts_today_by_profile'] = state.get('posts_today_by_profile', {})
        context['last_run_date_for_counts'] = state.get('last_run_date', 'N/A')
        context['processed_tickers_log_map'] = state.get('processed_tickers_detailed_log_by_profile', {})
        context['absolute_max_posts_cap'] = getattr(_auto_publisher, 'ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP', 10) if _auto_publisher else 10
        context.setdefault('persisted_file_info', {})
        context.setdefault('persisted_ticker_statuses_map', {})
        
        db = get_firestore_client()
        
        # Calculate publishing stats from userPublishedArticles collection
        total_published_count = 0
        this_week_count = 0
        pending_count = 0
        recent_activity = []
        
        if db:
            try:
                # Get all published articles for this user (without order_by to avoid index requirement)
                articles_query = db.collection('userPublishedArticles')\
                    .where('user_uid', '==', user_uid)\
                    .limit(100)
                
                articles = list(articles_query.stream())
                total_published_count = len(articles)
                
                # Calculate this week's count
                now = datetime.now(timezone.utc)
                week_start = now - timedelta(days=now.weekday())
                week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Sort articles by published_at in Python (to avoid Firestore index requirement)
                articles_with_dates = []
                for article_doc in articles:
                    article_data = article_doc.to_dict()
                    published_at_str = article_data.get('published_at')
                    published_at = None
                    
                    if published_at_str:
                        try:
                            if isinstance(published_at_str, str):
                                published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                            elif hasattr(published_at_str, 'isoformat'):
                                published_at = published_at_str
                        except Exception:
                            pass
                    
                    articles_with_dates.append((published_at or datetime.min.replace(tzinfo=timezone.utc), article_data, article_doc))
                
                # Sort by published_at descending
                articles_with_dates.sort(key=lambda x: x[0], reverse=True)
                
                # Count this week from all articles and get recent activity (last 10)
                for published_at, article_data, article_doc in articles_with_dates:
                    # Check if published this week
                    if published_at >= week_start:
                        this_week_count += 1
                    
                    # Build recent activity item (only for first 10)
                    if len(recent_activity) < 10:
                        published_at_str = article_data.get('published_at', '')
                        if isinstance(published_at_str, str):
                            time_display = published_at_str
                        elif hasattr(published_at_str, 'isoformat'):
                            time_display = published_at_str.isoformat()
                        else:
                            time_display = 'Recently'
                        
                        activity_item = {
                            'title': article_data.get('title', 'Published article'),
                            'site': article_data.get('site', article_data.get('profile_name', 'Site')),
                            'status': article_data.get('status', 'published'),
                            'time': time_display,
                            'type': article_data.get('article_type', 'stock')
                        }
                        recent_activity.append(activity_item)
                
                # Count pending articles (status is 'pending' or 'scheduled')
                # Use separate queries to avoid 'in' operator which requires index
                pending_query1 = db.collection('userPublishedArticles')\
                    .where('user_uid', '==', user_uid)\
                    .where('status', '==', 'pending')\
                    .limit(50)
                pending_query2 = db.collection('userPublishedArticles')\
                    .where('user_uid', '==', user_uid)\
                    .where('status', '==', 'scheduled')\
                    .limit(50)
                
                pending_articles1 = list(pending_query1.stream())
                pending_articles2 = list(pending_query2.stream())
                pending_count = len(pending_articles1) + len(pending_articles2)
                
            except Exception as e:
                current_app.logger.error(f"Error fetching publishing stats for user {user_uid}: {e}", exc_info=True)
        
        context['total_published_count'] = total_published_count
        context['this_week_count'] = this_week_count
        context['pending_count'] = pending_count
        context['recent_activity'] = recent_activity
        
        for profile in profiles_list:
            pid = profile.get('profile_id')
            if pid:
                all_tickers = profile.get('all_tickers_from_file', [])
                total_count = len(all_tickers)
                processed_count = 0
                if 'last_processed_ticker_index_by_profile' in state and pid in state['last_processed_ticker_index_by_profile']:
                    processed_count = state['last_processed_ticker_index_by_profile'][pid] + 1
                
                context['persisted_file_info'][pid] = {
                    'name': profile.get('uploaded_ticker_file_name'),
                    'path': profile.get('ticker_file_storage_path'),
                    'uploaded_at': profile.get('ticker_file_uploaded_at'),
                    'count': profile.get('ticker_count_from_file'),
                    'preview': profile.get('ticker_preview_from_file', []),
                    'all_tickers': all_tickers,
                    'processed_count': processed_count,
                    'total_count': total_count
                }
                
                # Only fetch the most recent ticker statuses (limit)
                try:
                    statuses = {}
                    if db:
                        docs_stream = db.collection(u'userSiteProfiles').document(user_uid)\
                            .collection(u'profiles').document(pid)\
                            .collection(u'processedTickers').order_by(u'last_updated_at', direction='DESCENDING').limit(ticker_status_limit).stream()
                        for doc in docs_stream:
                            status_data = doc.to_dict()
                            for time_key in ['last_updated_at', 'generation_time', 'publish_time']:
                                if time_key in status_data and hasattr(status_data[time_key], 'isoformat'):
                                    status_data[time_key] = status_data[time_key].isoformat()
                                elif time_key in status_data and isinstance(status_data[time_key], (int, float)):
                                    if status_data[time_key] > 10**10:
                                        status_data[time_key] = datetime.fromtimestamp(status_data[time_key]/1000, timezone.utc).isoformat()
                                    else:
                                        status_data[time_key] = datetime.fromtimestamp(status_data[time_key], timezone.utc).isoformat()
                            original_ticker_symbol = doc.id.replace('_SLASH_', '/')
                            statuses[original_ticker_symbol] = status_data
                    context['persisted_ticker_statuses_map'][pid] = statuses
                except Exception as e:
                    current_app.logger.error(f"Error fetching limited ticker statuses for profile '{pid}': {e}", exc_info=True)
                    context['persisted_ticker_statuses_map'][pid] = {}
                    
    except Exception as e:
        current_app.logger.error(f"Error loading shared_context (user: {user_uid}): {e}", exc_info=True)
        context.update({
            'posts_today_by_profile': {}, 
            'last_run_date_for_counts': "Error",
            'processed_tickers_log_map': {}, 
            'absolute_max_posts_cap': 10,
            'persisted_file_info': {}, 
            'persisted_ticker_statuses_map': {},
            'total_published_count': 0,
            'this_week_count': 0,
            'pending_count': 0,
            'recent_activity': []
        })
    
    return context
