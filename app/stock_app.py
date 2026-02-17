import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, current_app, send_from_directory
from flask_socketio import SocketIO
from flask_session import Session  # Added session support
from app.core.config import Config
from app.core.database import init_firebase, verify_firebase_token, get_firestore_client, safe_get_storage_bucket
from app.core.utils import format_datetime_filter, format_earnings_date_filter
from app.core.auth import login_required
from firebase_admin import firestore
import requests

# Import dependencies for injection
from app.services.report_service import get_report_history_for_user

_ticker_data_cache = None
_ticker_data_last_loaded = None
STOCK_REPORTS_PATH = os.path.join(PROJECT_ROOT, 'generated_data', 'stock_reports')

def load_ticker_data():
    """Load ticker data from JSON file with caching."""
    global _ticker_data_cache, _ticker_data_last_loaded

    current_time = time.time()
    if (_ticker_data_cache is not None and
        _ticker_data_last_loaded is not None and
        current_time - _ticker_data_last_loaded < 300):
        return _ticker_data_cache

    try:
        ticker_file_path = os.path.join(PROJECT_ROOT, 'data', 'all-us-tickers.json')
        with open(ticker_file_path, 'r', encoding='utf-8') as f:
            _ticker_data_cache = json.load(f)
        _ticker_data_last_loaded = current_time
        logger = current_app.logger if current_app else None
        if logger:
            logger.info(f"Loaded {len(_ticker_data_cache)} tickers from JSON file")
        return _ticker_data_cache
    except Exception as e:
        logger = current_app.logger if current_app else None
        if logger:
            logger.error(f"Error loading ticker data: {e}")
        return []

# Lazy load helpers
def create_stock_app():
    config_class = Config
    
    # Initialize Flask
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')
    
    # Load Config
    flask_config = config_class.get_flask_config(app.root_path)
    app.config.update(flask_config)
    
    # Initialize Core Services
    init_firebase()
    
    # Initialize Extensions
    from flask_caching import Cache
    cache = Cache(app)
    
    # Initialize Server-side Session
    if app.config.get('SESSION_TYPE'):
        Session(app)
        
    # Register Context Processors
    from app.core.context_processors import register_context_processors
    register_context_processors(app)
    
    # Register Template Filters
    app.add_template_filter(format_datetime_filter, 'format_datetime')
    app.add_template_filter(format_earnings_date_filter, 'format_earnings_date')

    # Register Blueprints (Stock Analysis Specific)
    from app.info_routes import info_bp
    app.register_blueprint(info_bp, url_prefix='/info')
    
    # Import market_news safely - assuming it's a blueprint object
    from app.market_news import market_news_bp
    app.register_blueprint(market_news_bp, url_prefix='/stock-analysis')
    
    from app.blueprints.quota_api import quota_bp
    app.register_blueprint(quota_bp)
    
    from app.blueprints.admin_quota_api import admin_quota_bp
    app.register_blueprint(admin_quota_bp)
    
    # Register Optimized Dashboard Analytics Routes
    try:
        from analysis_scripts.firestore_dashboard_analytics import register_firestore_dashboard_routes
        register_firestore_dashboard_routes(app, cache_instance=cache)
        app.logger.info("Registered optimized Firestore dashboard analytics routes")
    except ImportError as e:
        app.logger.error(f"Failed to register dashboard analytics routes: {e}")
    
    # Main Stock Analysis Blueprint
    from app.blueprints.stock_analysis import stock_analysis_bp, register_dependencies
    
    # Inject dependencies
    register_dependencies(
        login_required_func=login_required, 
        get_report_history_func=get_report_history_for_user
    )
    
    app.register_blueprint(stock_analysis_bp)
    
    # SEO/Static Routes (Root) - Redefined here to avoid importing main_portal_app
    @app.route('/')
    def stock_analysis_homepage_route():
        return render_template('stock-analysis-homepage.html', title="AI Stock Predictions & Analysis")

    @app.route('/pricing')
    def pricing_page():
        """Public pricing page for stock analysis plans."""
        return render_template('pricing.html', title="Pricing - TickZen")

    @app.route('/login', methods=['GET'])
    def login():
        # This is just a placeholder GET for testing separate service. 
        # Ideally auth routes should be in a blueprint (auth_bp)
        return render_template('login.html', title="Login - TickZen")

    @app.route('/register', methods=['GET'])
    def register():
        return render_template('register.html', title="Register - TickZen")

    @app.route('/forgot_password', methods=['GET'])
    def forgot_password():
        return render_template('auth/forgot_password.html', title="Forgot Password - TickZen")

    @app.route('/wp-asset-generator', methods=['GET'])
    @login_required
    def wp_generator_page():
        return render_template('wp-asset.html', title="WP Asset Generator - TickZen")

    @app.route('/user-profile')
    @login_required
    def user_profile_page():
        user_uid = session['firebase_user_uid']
        db = get_firestore_client()

        user_profile_data = {
            'display_name': session.get('user_displayName', ''),
            'bio': '',
            'profile_picture': session.get('user_profile_picture', ''),
            'notifications': {'email': False, 'automation': False},
            'created_at': None,
            'total_automations': 0,
            'active_profiles': 0
        }

        if db:
            try:
                profile_doc = db.collection('userProfiles').document(user_uid).get()
                if profile_doc.exists:
                    profile_data = profile_doc.to_dict()
                    user_profile_data.update({
                        'display_name': profile_data.get('display_name', user_profile_data['display_name']),
                        'bio': profile_data.get('bio', ''),
                        'profile_picture': profile_data.get('profile_picture', user_profile_data['profile_picture']),
                        'notifications': profile_data.get('notifications', user_profile_data['notifications']),
                        'created_at': profile_data.get('created_at', None)
                    })

                try:
                    automations_query = db.collection('userGeneratedReports')\
                        .where(filter=firestore.FieldFilter('user_uid', '==', user_uid)).count()
                    user_profile_data['total_automations'] = automations_query.get()[0][0].value
                except Exception:
                    user_profile_data['total_automations'] = 0

                try:
                    profiles_query = db.collection('userSiteProfiles').document(user_uid).collection('profiles').count()
                    user_profile_data['active_profiles'] = profiles_query.get()[0][0].value
                except Exception:
                    user_profile_data['active_profiles'] = 0

            except Exception as e:
                app.logger.error(f"Error fetching user profile data: {str(e)}")

        return render_template(
            'user_profile.html',
            title="Your Profile - TickZen",
            user_profile_picture=user_profile_data['profile_picture'],
            user_displayName=user_profile_data['display_name'],
            user_bio=user_profile_data['bio'],
            user_notifications=user_profile_data['notifications'],
            user_created_at=user_profile_data['created_at'],
            total_automations=user_profile_data['total_automations'],
            active_profiles=user_profile_data['active_profiles']
        )

    @app.route('/update-user-profile', methods=['POST'])
    @login_required
    def update_user_profile():
        try:
            user_uid = session['firebase_user_uid']
            db = get_firestore_client()

            if not db:
                return jsonify({'success': False, 'message': 'Database service unavailable'}), 503

            display_name = request.form.get('display_name', '').strip()
            email_notifications = request.form.get('email_notifications') == 'on'
            automation_alerts = request.form.get('automation_alerts') == 'on'

            user_profile_ref = db.collection('userProfiles').document(user_uid)

            update_data = {
                'display_name': display_name,
                'notifications': {
                    'email': email_notifications,
                    'automation': automation_alerts
                },
                'updated_at': firestore.SERVER_TIMESTAMP
            }

            user_profile_ref.set(update_data, merge=True)
            session['user_displayName'] = display_name

            return jsonify({
                'success': True,
                'message': 'Profile updated successfully',
                'data': {'display_name': display_name}
            })

        except Exception as e:
            app.logger.error(f"Error updating user profile: {str(e)}")
            return jsonify({'success': False, 'message': 'Failed to update profile'}), 500

    @app.route('/change-password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        if request.method == 'GET':
            return render_template('change_password.html', title="Change Password - TickZen")

        try:
            user_uid = session['firebase_user_uid']
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not all([current_password, new_password, confirm_password]):
                return jsonify({'success': False, 'message': 'All fields are required'}), 400

            if new_password != confirm_password:
                return jsonify({'success': False, 'message': 'New passwords do not match'}), 400

            if len(new_password) < 8:
                return jsonify({'success': False, 'message': 'Password must be at least 8 characters long'}), 400

            from firebase_admin import auth
            user = auth.get_user(user_uid)
            user_email = user.email

            if not user_email:
                return jsonify({'success': False, 'message': 'User email not found. Cannot verify current password.'}), 400

            firebase_api_key = os.getenv('FIREBASE_API_KEY')
            if not firebase_api_key:
                app.logger.error("FIREBASE_API_KEY not found in environment variables")
                return jsonify({'success': False, 'message': 'Server configuration error'}), 500

            verify_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={firebase_api_key}"
            verify_data = {
                "email": user_email,
                "password": current_password,
                "returnSecureToken": True
            }

            verify_response = requests.post(verify_url, json=verify_data)
            verify_result = verify_response.json()

            if verify_response.status_code != 200:
                if "INVALID_PASSWORD" in str(verify_result):
                    return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400
                if "EMAIL_NOT_FOUND" in str(verify_result):
                    return jsonify({'success': False, 'message': 'User account not found'}), 404
                app.logger.error(f"Firebase Auth verification error: {verify_result}")
                return jsonify({'success': False, 'message': 'Failed to verify current password'}), 500

            auth.update_user(user_uid, password=new_password)

            return jsonify({'success': True, 'message': 'Password updated successfully'})

        except Exception as e:
            app.logger.error(f"Error in change password: {str(e)}")
            return jsonify({'success': False, 'message': 'An error occurred while updating password'}), 500

    @app.route('/activity-log')
    @login_required
    def view_activity_log():
        user_uid = session['firebase_user_uid']
        db = get_firestore_client()

        activity_log = []
        member_since = None

        if db:
            try:
                profile_doc = db.collection('userProfiles').document(user_uid).get()
                if profile_doc.exists:
                    profile_data = profile_doc.to_dict()
                    member_since = profile_data.get('created_at')

                automations_query = db.collection('userGeneratedReports')\
                    .where(filter=firestore.FieldFilter('user_uid', '==', user_uid))\
                    .order_by('generated_at', direction='DESCENDING')\
                    .limit(50)

                for doc in automations_query.stream():
                    data = doc.to_dict()
                    generated_at = data.get('generated_at')
                    timestamp = generated_at.timestamp() if hasattr(generated_at, 'timestamp') else 0

                    activity_log.append({
                        'type': 'automation',
                        'ticker': data.get('ticker', 'N/A'),
                        'timestamp': timestamp,
                        'details': f"Generated stock analysis report for {data.get('ticker', 'N/A')}"
                    })

            except Exception as e:
                app.logger.error(f"Error fetching activity log: {str(e)}")

        return render_template(
            'activity_log.html',
            title="Activity Log - Tickzen",
            activity_log=activity_log,
            member_since=member_since
        )

    @app.route('/api/dashboard/reports')
    @login_required
    def api_dashboard_reports():
        """API endpoint to get user's report history for dashboard"""
        user_uid = session.get('firebase_user_uid')
        if not user_uid:
            return jsonify({'status': 'error', 'message': 'Not authenticated', 'reports': [], 'total_reports': 0}), 401

        try:
            display_limit = request.args.get('limit', 10, type=int)
            cache_key = f"dashboard_reports_{user_uid}_limit_{display_limit}"

            if cache:
                cached_payload = cache.get(cache_key)
                if cached_payload:
                    return jsonify(cached_payload)

            reports, total_reports = get_report_history_for_user(user_uid, display_limit=display_limit)

            formatted_reports = []
            for report in reports:
                formatted_report = {
                    'id': report.get('id', ''),
                    'ticker': report.get('ticker', 'N/A'),
                    'filename': report.get('filename', 'N/A'),
                    'generated_at': report.get('generated_at').isoformat() if hasattr(report.get('generated_at'), 'isoformat') else str(report.get('generated_at', 'N/A')),
                    'storage_location': report.get('storage_location', ''),
                    'file_url': report.get('file_url', ''),
                    'status': report.get('status', 'completed')
                }
                formatted_reports.append(formatted_report)

            response_payload = {
                'status': 'success',
                'reports': formatted_reports,
                'total_reports': total_reports
            }

            if cache:
                cache.set(cache_key, response_payload, timeout=300)

            return jsonify(response_payload)

        except Exception as e:
            app.logger.error(f"Error fetching dashboard reports for user {user_uid}: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e), 'reports': [], 'total_reports': 0}), 500

    @app.route('/api/ticker-suggestions')
    def ticker_suggestions():
        """API endpoint for ticker autocomplete suggestions."""
        query = request.args.get('q', '').strip()

        if not query or len(query) < 1:
            return jsonify([])

        try:
            ticker_data = load_ticker_data()
            if not ticker_data:
                return jsonify([])

            query_upper = query.upper()
            query_lower = query.lower()

            matches = []
            for ticker_info in ticker_data:
                symbol = ticker_info.get('symbol', '').upper()
                company = ticker_info.get('company', '')
                company_lower = company.lower()

                symbol_match = symbol.startswith(query_upper)
                company_match = query_lower in company_lower

                if symbol_match or company_match:
                    if symbol_match and company_match:
                        match_type = "both"
                        display = f"{symbol} - {company} (Symbol & Company)"
                    elif symbol_match:
                        match_type = "symbol"
                        display = f"{symbol} - {company}"
                    else:
                        match_type = "company"
                        display = f"{symbol} - {company} (Company match)"

                    matches.append({
                        'symbol': symbol,
                        'company': company,
                        'display': display,
                        'match_type': match_type
                    })

            def sort_key(item):
                match_type_order = {"symbol": 0, "both": 1, "company": 2}
                return (match_type_order.get(item['match_type'], 3), len(item['symbol']))

            matches.sort(key=sort_key)
            matches = matches[:10]

            app.logger.info(f"Ticker suggestions for '{query}': {len(matches)} matches")
            return jsonify(matches)

        except Exception as e:
            app.logger.error(f"Error in ticker suggestions: {e}")
            return jsonify([])

    def _normalize_report_date(report_data):
        raw_date = report_data.get('generated_at') or report_data.get('timestamp') or report_data.get('date')
        if hasattr(raw_date, 'timestamp'):
            return datetime.fromtimestamp(raw_date.timestamp(), timezone.utc)
        if isinstance(raw_date, (int, float)):
            ts = raw_date / 1000 if raw_date > 10**10 else raw_date
            return datetime.fromtimestamp(ts, timezone.utc)
        if isinstance(raw_date, str):
            try:
                return datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None

    def _fetch_user_reports(user_uid, limit=None):
        """Fetch user reports from Firestore with improved error handling and logging.
        
        Args:
            user_uid: Firebase user ID
            limit: Maximum number of reports to fetch (None = fetch all)
        """
        import time
        from flask import g
        
        # Use request-level cache to avoid duplicate queries in parallel API calls
        cache_attr = f'_reports_cache_{user_uid}'
        if hasattr(g, cache_attr):
            app.logger.info(f"Returning cached reports for {user_uid[:8]}... from request context")
            return getattr(g, cache_attr)
        
        start_time = time.time()
        
        db = get_firestore_client()
        if not db:
            app.logger.error("Firestore client unavailable in _fetch_user_reports")
            return []
        
        try:
            try:
                base_query = db.collection('userGeneratedReports').where(filter=firestore.FieldFilter('user_uid', '==', user_uid))
            except TypeError:
                base_query = db.collection('userGeneratedReports').where('user_uid', '==', user_uid)

            # Apply ordering and optional limit
            reports_query = base_query.order_by('generated_at', direction=firestore.Query.DESCENDING)
            if limit:
                reports_query = reports_query.limit(limit)
            
            # Fetch documents from Firestore
            query_start = time.time()
            docs = list(reports_query.stream())
            query_duration = time.time() - query_start
            
            app.logger.info(f"Firestore query for user {user_uid[:8]}... took {query_duration:.2f}s, returned {len(docs)} docs")
            
            reports = []
            for doc in docs:
                data = doc.to_dict()
                data['date'] = _normalize_report_date(data)
                if data.get('ticker') and data.get('date'):
                    reports.append(data)
            
            total_duration = time.time() - start_time
            app.logger.info(f"_fetch_user_reports for {user_uid[:8]}... completed in {total_duration:.2f}s with {len(reports)} valid reports")
            
            # Cache in request context to avoid duplicate queries
            from flask import g
            cache_attr = f'_reports_cache_{user_uid}'
            setattr(g, cache_attr, reports)
            
            return reports
            
        except Exception as e:
            duration = time.time() - start_time
            app.logger.error(f"Error fetching analytics reports for user {user_uid[:8]}... after {duration:.2f}s: {type(e).__name__}: {e}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    # NOTE: Dashboard analytics routes are now handled by firestore_dashboard_analytics
    # The routes below are DEPRECATED and kept for reference only
    # To use optimized routes, see register_firestore_dashboard_routes() above
    
    # @app.route('/api/dashboard/stats')
    # @login_required
    # def api_dashboard_stats_DEPRECATED():
        """Dashboard stats based on userGeneratedReports."""
        import time
        start_time = time.time()
        
        user_uid = session.get('firebase_user_uid')
        cache_key = f"dashboard_stats_{user_uid}"

        if cache:
            cached = cache.get(cache_key)
            if cached:
                app.logger.info(f"Returning cached dashboard stats for {user_uid[:8]}...")
                return jsonify(cached)

        try:
            reports = _fetch_user_reports(user_uid)
            if not reports:
                app.logger.warning(f"No reports found for user {user_uid[:8]}...")
                payload = {
                    'total_reports': 0,
                    'this_month': 0,
                    'published_reports': 0,
                    'unique_tickers': 0,
                    'has_data': False
                }
                return jsonify(payload)

            now = datetime.now(timezone.utc)
            total_reports = len(reports)
            this_month = len([r for r in reports if r.get('date') and r['date'].month == now.month and r['date'].year == now.year])
            published_reports = len([r for r in reports if r.get('published', True)])
            unique_tickers = len(set(r.get('ticker') for r in reports if r.get('ticker')))

            payload = {
                'total_reports': total_reports,
                'this_month': this_month,
                'published_reports': published_reports,
                'unique_tickers': unique_tickers,
                'has_data': True
            }

            if cache:
                cache.set(cache_key, payload, timeout=900)  # Cache for 15 minutes

            duration = time.time() - start_time
            app.logger.info(f"Dashboard stats for {user_uid[:8]}... completed in {duration:.2f}s")
            return jsonify(payload)
            
        except Exception as e:
            duration = time.time() - start_time
            app.logger.error(f"Error in api_dashboard_stats for {user_uid[:8]}... after {duration:.2f}s: {type(e).__name__}: {e}")
            return jsonify({
                'total_reports': 0,
                'this_month': 0,
                'published_reports': 0,
                'unique_tickers': 0,
                'has_data': False,
                'error': 'Failed to load dashboard stats'
            }), 500

    # @app.route('/api/dashboard/reports-over-time')
    # @login_required
    # def api_reports_over_time_DEPRECATED():
        """Reports over time chart data."""
        import time
        start_time = time.time()
        
        period = request.args.get('period', 'week')
        if period not in ['week', 'month', 'quarter', 'year']:
            period = 'week'

        user_uid = session.get('firebase_user_uid')
        cache_key = f"reports_over_time_{user_uid}_{period}"

        if cache:
            cached = cache.get(cache_key)
            if cached:
                return jsonify(cached)

        try:
            reports = _fetch_user_reports(user_uid)
            if not reports:
                app.logger.warning(f"No reports for reports-over-time chart for user {user_uid[:8]}...")
                return jsonify({'labels': [], 'data': [], 'has_data': False})

            grouped = defaultdict(int)
            for report in reports:
                date = report.get('date')
                if not date:
                    continue
                if period == 'week':
                    key = date.strftime('%a')
                elif period == 'month':
                    key = f"Week {date.isocalendar()[1]}"
                elif period == 'quarter':
                    key = date.strftime('%b')
                else:
                    key = date.strftime('%Y-%m-%d')
                grouped[key] += 1

            if period == 'week':
                days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                labels = days_order
                data = [grouped.get(day, 0) for day in days_order]
            else:
                sorted_items = sorted(grouped.items())
                labels = [item[0] for item in sorted_items]
                data = [item[1] for item in sorted_items]

            payload = {'labels': labels, 'data': data, 'has_data': True}
            if cache:
                cache.set(cache_key, payload, timeout=900)  # Cache for 15 minutes
            
            duration = time.time() - start_time
            app.logger.info(f"Reports-over-time for {user_uid[:8]}... completed in {duration:.2f}s")
            return jsonify(payload)
            
        except Exception as e:
            duration = time.time() - start_time
            app.logger.error(f"Error in api_reports_over_time for {user_uid[:8]}... after {duration:.2f}s: {type(e).__name__}: {e}")
            return jsonify({'labels': [], 'data': [], 'has_data': False, 'error': 'Failed to load chart'}), 500

    # @app.route('/api/dashboard/most-analyzed')
    # @login_required
    # def api_most_analyzed_DEPRECATED():
        """Most analyzed tickers data."""
        import time
        start_time = time.time()
        
        try:
            limit = int(request.args.get('limit', 5))
        except (ValueError, TypeError):
            limit = 5
        limit = max(1, min(limit, 50))

        user_uid = session.get('firebase_user_uid')
        cache_key = f"most_analyzed_{user_uid}_{limit}"
        if cache:
            cached = cache.get(cache_key)
            if cached:
                return jsonify(cached)

        try:
            reports = _fetch_user_reports(user_uid)
            if not reports:
                app.logger.warning(f"No reports for most-analyzed chart for user {user_uid[:8]}...")
                return jsonify({'tickers': [], 'counts': [], 'sectors': [], 'has_data': False})

            ticker_counts = Counter([r.get('ticker') for r in reports if r.get('ticker')])
            top_tickers = ticker_counts.most_common(limit)
            tickers = [ticker for ticker, _ in top_tickers]
            counts = [count for _, count in top_tickers]

            sectors = []
            for ticker in tickers:
                report = next((r for r in reports if r.get('ticker') == ticker), None)
                sectors.append(report.get('sector', 'Other') if report else 'Other')

            payload = {'tickers': tickers, 'counts': counts, 'sectors': sectors, 'has_data': True}
            if cache:
                cache.set(cache_key, payload, timeout=900)  # Cache for 15 minutes
            
            duration = time.time() - start_time
            app.logger.info(f"Most-analyzed for {user_uid[:8]}... completed in {duration:.2f}s")
            return jsonify(payload)
            
        except Exception as e:
            duration = time.time() - start_time
            app.logger.error(f"Error in api_most_analyzed for {user_uid[:8]}... after {duration:.2f}s: {type(e).__name__}: {e}")
            return jsonify({'tickers': [], 'counts': [], 'sectors': [], 'has_data': False, 'error': 'Failed to load chart'}), 500

    # @app.route('/api/dashboard/publishing-status')
    # @login_required
    # def api_publishing_status_DEPRECATED():
        """Publishing status breakdown."""
        user_uid = session.get('firebase_user_uid')
        cache_key = f"publishing_status_{user_uid}"
        if cache:
            cached = cache.get(cache_key)
            if cached:
                return jsonify(cached)

        reports = _fetch_user_reports(user_uid)
        if not reports:
            return jsonify({'labels': ['Published'], 'data': [0], 'colors': ['#10b981'], 'has_data': False})

        published_count = len([r for r in reports if r.get('published', True)])
        unpublished_count = len(reports) - published_count

        labels = ['Published']
        data = [published_count]
        colors = ['#10b981']
        if unpublished_count > 0:
            labels.append('Unpublished')
            data.append(unpublished_count)
            colors.append('#f43f5e')

        payload = {'labels': labels, 'data': data, 'colors': colors, 'has_data': True}
        if cache:
            cache.set(cache_key, payload, timeout=900)  # Cache for 15 minutes
        return jsonify(payload)

    # @app.route('/api/dashboard/activity-heatmap')
    # @login_required
    # def api_activity_heatmap_DEPRECATED():
        """Activity heatmap data."""
        year = request.args.get('year')
        try:
            year = int(year) if year else None
        except (ValueError, TypeError):
            year = None

        user_uid = session.get('firebase_user_uid')
        cache_key = f"activity_heatmap_{user_uid}_{year if year else 'all'}"
        if cache:
            cached = cache.get(cache_key)
            if cached:
                return jsonify(cached)

        reports = _fetch_user_reports(user_uid)
        if not reports:
            return jsonify({'heatmap': {}, 'has_data': False, 'year': None})

        years_with_data = sorted({r['date'].year for r in reports if r.get('date')}, reverse=True)
        if not years_with_data:
            return jsonify({'heatmap': {}, 'has_data': False, 'year': None})

        if year is None or year not in years_with_data:
            year = years_with_data[0]

        heatmap = {}
        for report in reports:
            date = report.get('date')
            if date and date.year == year:
                key = date.strftime('%Y-%m-%d')
                heatmap[key] = heatmap.get(key, 0) + 1

        payload = {'heatmap': heatmap, 'has_data': bool(heatmap), 'year': year}
        if cache:
            cache.set(cache_key, payload, timeout=900)  # Cache for 15 minutes
        return jsonify(payload)

    # @app.route('/api/dashboard/failed-analyses')
    # @login_required
    # def api_failed_analyses_DEPRECATED():
        """Failed analyses statistics."""
        user_uid = session.get('firebase_user_uid')
        cache_key = f"failed_analyses_{user_uid}"
        if cache:
            cached = cache.get(cache_key)
            if cached:
                return jsonify(cached)

        db = get_firestore_client()
        if not db:
            return jsonify({'has_data': False, 'total_failures': 0, 'top_failed_tickers': [], 'daily_failures': [], 'recent_failures': 0, 'recent_errors': []})

        failed_analyses = []
        try:
            try:
                query = db.collection('failed_analyses').where(filter=firestore.FieldFilter('user_id', '==', user_uid))
            except TypeError:
                query = db.collection('failed_analyses').where('user_id', '==', user_uid)
            query_result = query.order_by('timestamp', direction='DESCENDING').limit(500).get()
        except Exception:
            query_result = []

        for doc in query_result:
            data = doc.to_dict()
            if data.get('ticker') and data.get('timestamp'):
                date = _normalize_report_date(data) or datetime.fromtimestamp(data['timestamp'], timezone.utc)
                failed_analyses.append({
                    'ticker': data.get('ticker'),
                    'timestamp': data.get('timestamp'),
                    'date': date,
                    'error_message': data.get('error_message', 'Unknown error')
                })

        if not failed_analyses:
            payload = {
                'has_data': False,
                'total_failures': 0,
                'top_failed_tickers': [],
                'daily_failures': [],
                'recent_failures': 0,
                'recent_errors': []
            }
            return jsonify(payload)

        ticker_counts = Counter([f['ticker'] for f in failed_analyses])
        most_common = ticker_counts.most_common(10)
        today = datetime.now(timezone.utc).date()
        last_week = today - timedelta(days=7)

        daily_counts = Counter()
        recent_errors = []
        for failure in failed_analyses:
            failure_date = failure['date'].date() if failure.get('date') else None
            if failure_date and failure_date >= last_week:
                daily_counts[failure_date.isoformat()] += 1
            if failure.get('date') and (datetime.now(timezone.utc) - failure['date']).total_seconds() < 86400:
                recent_errors.append(failure)

        payload = {
            'has_data': True,
            'total_failures': len(failed_analyses),
            'top_failed_tickers': [{'ticker': ticker, 'count': count} for ticker, count in most_common],
            'daily_failures': [{'date': date, 'count': count} for date, count in sorted(daily_counts.items())],
            'recent_failures': len(recent_errors),
            'recent_errors': [
                {
                    'ticker': err['ticker'],
                    'timestamp': err['timestamp'],
                    'date': err['date'].isoformat() if err.get('date') else None,
                    'error_message': err.get('error_message', 'Unknown error')
                }
                for err in sorted(recent_errors, key=lambda x: x['timestamp'], reverse=True)[:5]
            ]
        }

        if cache:
            cache.set(cache_key, payload, timeout=900)  # Cache for 15 minutes

        return jsonify(payload)

    # Notifications stub endpoints (actual notifications are on main portal)
    @app.route('/api/notifications')
    @login_required
    def api_notifications_stub():
        """Stub endpoint to prevent 404s when stock analysis pages poll for notifications."""
        return jsonify({'notifications': [], 'unread_count': 0})

    @app.route('/api/notifications/<notification_id>/read', methods=['POST'])
    @login_required
    def api_notification_read_stub(notification_id):
        """Stub endpoint for marking notifications as read."""
        return jsonify({'status': 'success'})

    @app.route('/api/notifications/<notification_id>/delete', methods=['POST'])
    @login_required
    def api_notification_delete_stub(notification_id):
        """Stub endpoint for deleting notifications."""
        return jsonify({'status': 'success'})

    @app.route('/api/notifications/mark-all-read', methods=['POST'])
    @login_required
    def api_notifications_mark_all_read_stub():
        """Stub endpoint for marking all notifications as read."""
        return jsonify({'status': 'success'})

    @app.route('/api/notifications/clear-all', methods=['POST'])
    @login_required
    def api_notifications_clear_all_stub():
        """Stub endpoint for clearing all notifications."""
        return jsonify({'status': 'success'})

    @app.route('/verify-token', methods=['POST'])
    def verify_token_route():
        data = request.get_json()
        if not data or 'idToken' not in data:
            return jsonify({"error": "No ID token provided."}), 400

        id_token = data['idToken']
        decoded_token = verify_firebase_token(id_token)

        if decoded_token and 'uid' in decoded_token:
            session['firebase_user_uid'] = decoded_token['uid']
            session['firebase_user_email'] = decoded_token.get('email')
            session['firebase_user_displayName'] = decoded_token.get('name', '')
            session.permanent = True
            try:
                next_url = url_for('stock_analysis.dashboard')
            except Exception:
                try:
                    next_url = url_for('stock_analysis_homepage_route')
                except Exception:
                    next_url = '/'
            return jsonify({"status": "success", "uid": decoded_token['uid'], "next_url": next_url}), 200

        return jsonify({"error": "Invalid or expired token."}), 401

    @app.route('/api/firebase-config', methods=['GET'])
    def firebase_config_api():
        return jsonify(Config.get_firebase_client_config())
        
    @app.route('/logout')
    def logout():
        session.clear()
        try:
            return redirect(url_for('stock_analysis_homepage_route'))
        except Exception:
            return redirect('/')

    @app.route('/start-analysis', methods=['POST'], endpoint='start_stock_analysis')
    def start_analysis_route():
        from app.services.stock_service import start_stock_analysis_service
        try:
            ticker = request.form.get('ticker', '').strip().upper()
            user_uid = session.get('firebase_user_uid')
            client_sid = request.form.get('client_sid')
            
            # Simple room logic
            room_id = client_sid or user_uid
            if not room_id:
                # Fallback to a generated ID or anonymous room
                import time
                room_id = "task_room_" + str(int(time.time()))
            
            # Get socketio instance
            # We can't easily get the socketio object created in create_stock_socketio here 
            # unless we store it on app or use current_app extensions if allocated
            # Flask-SocketIO usually stores itself in current_app.extensions['socketio']
            socketio = app.extensions.get('socketio')
            
            if not socketio:
                return "SocketIO not initialized", 500

            if user_uid:
                try:
                    from app.services.quota_service import get_quota_service
                    from app.models.quota_models import ResourceType

                    quota_service = get_quota_service()
                    has_quota, quota_info = quota_service.check_quota(user_uid, ResourceType.STOCK_REPORT.value)

                    if not has_quota:
                        error_msg = f"You've used all {quota_info.get('limit', 0)} stock analysis reports this month."
                        socketio.emit('quota_exceeded', {
                            'message': error_msg,
                            'quota_info': quota_info,
                            'upgrade_url': '/pricing'
                        }, room=room_id)
                        return jsonify({
                            'error': 'quota_exceeded',
                            'message': error_msg,
                            'quota_info': quota_info
                        }), 403
                except Exception as e:
                    app.logger.error(f"Error checking quota: {e}", exc_info=True)
                    # Fail open if quota check errors

            success, msg = start_stock_analysis_service(ticker, user_uid, socketio, room_id, app.root_path)
            
            if success:
                return jsonify({'status': 'processing_initiated', 'message': msg}), 200
            else:
                return jsonify({'error': msg}), 500
                
        except Exception as e:
            app.logger.error(f"Error in start-analysis: {e}")
            return "Internal Server Error", 500

    def get_report_content_from_firebase_storage(storage_path):
        bucket = safe_get_storage_bucket()
        if not bucket:
            app.logger.error("Storage bucket not available for downloading report.")
            return None
        try:
            blob = bucket.blob(storage_path)
            if not blob.exists():
                app.logger.error(f"Report not found in Firebase Storage: {storage_path}")
                return None
            return blob.download_as_text()
        except Exception as e:
            app.logger.error(f"Error downloading report from Firebase Storage {storage_path}: {e}", exc_info=True)
            return None

    def get_report_content_from_firestore(report_data):
        try:
            storage_type = report_data.get('storage_type', 'unknown')

            if storage_type == 'firestore_content':
                return report_data.get('html_content')

            if storage_type == 'firestore_compressed':
                compressed_content = report_data.get('compressed_content')
                if compressed_content:
                    import gzip
                    import base64
                    decoded_content = base64.b64decode(compressed_content.encode('utf-8'))
                    decompressed_content = gzip.decompress(decoded_content)
                    return decompressed_content.decode('utf-8')

            if storage_type == 'firebase_storage':
                storage_path = report_data.get('storage_path')
                if storage_path:
                    return get_report_content_from_firebase_storage(storage_path)

            return None

        except Exception as e:
            app.logger.error(f"Error retrieving report content from Firestore: {e}")
            return None

    @app.route('/report/<ticker>/<path:filename>')
    @login_required
    def report_shortcut(ticker, filename):
        return redirect(url_for('display_report', ticker=ticker, filename=filename))

    @app.route('/display-report/<ticker>/<path:filename>')
    @login_required
    def display_report(ticker, filename):
        try:
            import urllib.parse
            clean_filename = urllib.parse.unquote(filename)
            clean_filename = os.path.basename(clean_filename)

            user_uid = session.get('firebase_user_uid')
            if not user_uid:
                session['notification_message'] = "Please log in to view reports."
                session['notification_type'] = "error"
                try:
                    return redirect(url_for('login'))
                except Exception:
                    return redirect('/')

            report_url = url_for('view_generated_report', ticker=ticker, filename=clean_filename)
            download_filename = f"{ticker.upper()}_Analysis_Report.html"

            return render_template(
                'report_display.html',
                ticker=ticker,
                report_url=report_url,
                download_filename=download_filename
            )
        except Exception as e:
            app.logger.error(f"Error in display_report: {e}", exc_info=True)
            session['notification_message'] = f"Error loading report for {ticker.upper()}. Please try again."
            session['notification_type'] = "error"
            try:
                return redirect(url_for('stock_analysis.analyzer'))
            except Exception:
                return redirect('/')

    @app.route('/view-report/<ticker>/<path:filename>')
    @login_required
    def view_generated_report(ticker, filename):
        try:
            import urllib.parse
            clean_filename = urllib.parse.unquote(filename)
            clean_filename = os.path.basename(clean_filename)

            user_uid = session.get('firebase_user_uid')
            if not user_uid:
                session['notification_message'] = "Please log in to view reports."
                session['notification_type'] = "error"
                try:
                    return redirect(url_for('login'))
                except Exception:
                    return redirect('/')

            db = get_firestore_client()
            if db:
                try:
                    reports_query = db.collection('userGeneratedReports')\
                        .where('user_uid', '==', user_uid)\
                        .where('filename', '==', clean_filename)\
                        .limit(1)

                    for doc in reports_query.stream():
                        report_data = doc.to_dict()
                        content = get_report_content_from_firestore(report_data)
                        if content:
                            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
                        break
                except Exception as e:
                    app.logger.error(f"Error querying Firestore for report: {e}")

            static_reports_path = os.path.join(app.static_folder, 'stock_reports')
            static_report_file = os.path.join(static_reports_path, clean_filename)
            if os.path.exists(static_report_file):
                with open(static_report_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content, 200, {'Content-Type': 'text/html; charset=utf-8'}

            full_file_path = os.path.join(STOCK_REPORTS_PATH, clean_filename)
            if os.path.exists(full_file_path):
                with open(full_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content, 200, {'Content-Type': 'text/html; charset=utf-8'}

            app.logger.error(f"Report file not found in database or locally: {clean_filename}")
            session['notification_message'] = f"Report file for {ticker.upper()} not found. It may have been deleted."
            session['notification_type'] = "error"
            try:
                return redirect(url_for('stock_analysis.analyzer'))
            except Exception:
                return redirect('/')

        except Exception as e:
            app.logger.error(f"Error in view_generated_report: {e}", exc_info=True)
            session['notification_message'] = f"Error loading report for {ticker.upper()}. Please try again."
            session['notification_type'] = "error"
            try:
                return redirect(url_for('stock_analysis.analyzer'))
            except Exception:
                return redirect('/')


    @app.route('/generate-wp-assets', methods=['POST'])
    @login_required
    def generate_wp_assets():
        import time
        import re
        start_time = time.time()

        if not request.is_json:
            return jsonify({'status': 'error', 'message': 'Invalid request: Expected JSON data.'}), 400

        data = request.get_json()
        ticker = data.get('ticker', '').strip().upper()

        room_id = session.get('firebase_user_uid', data.get('client_sid'))
        if not room_id:
            room_id = "wp_asset_task_" + str(int(time.time()))

        valid_ticker_pattern = r'^[A-Z0-9\^\.\-$&/=]{1,15}$'
        if not ticker or not re.match(valid_ticker_pattern, ticker):
            return jsonify({'status': 'error', 'message': f"Invalid ticker symbol: '{ticker}'."}), 400

        try:
            from automation_scripts.pipeline import run_wp_pipeline
        except Exception as exc:
            app.logger.error(f"WP asset pipeline unavailable: {exc}")
            return jsonify({'status': 'error', 'message': 'WordPress Asset generation service is temporarily unavailable.'}), 503

        socketio = app.extensions.get('socketio')
        if not socketio:
            return jsonify({'status': 'error', 'message': 'SocketIO not initialized.'}), 500

        try:
            timestamp = str(int(time.time()))
            _, _, html_report_fragment, img_urls_dict = run_wp_pipeline(
                ticker, timestamp, app.root_path, socketio_instance=socketio, task_room=room_id
            )

            if not isinstance(img_urls_dict, dict):
                img_urls_dict = {}

            if html_report_fragment and "Error Generating Report" not in html_report_fragment:
                duration = time.time() - start_time
                return jsonify({
                    'status': 'success',
                    'ticker': ticker,
                    'report_html': html_report_fragment,
                    'chart_urls': img_urls_dict,
                    'duration': f"{duration:.2f}s"
                })

            return jsonify({'status': 'error', 'message': 'Report generation failed.'}), 500

        except Exception as e:
            app.logger.error(f"Error generating WP assets for {ticker}: {e}")
            return jsonify({'status': 'error', 'message': 'WordPress Asset generation failed.'}), 500

    return app

def create_stock_socketio(app):
    socket_config = Config.get_socketio_config(app)
    socketio = SocketIO(app, **socket_config)
    
    # Register Socket Handlers
    from app.sockets.stock_sockets import register_stock_sockets
    register_stock_sockets(socketio)
    
    return socketio

if __name__ == '__main__':
    app = create_stock_app()
    socketio = create_stock_socketio(app)
    socketio.run(app, port=5001, debug=True)
