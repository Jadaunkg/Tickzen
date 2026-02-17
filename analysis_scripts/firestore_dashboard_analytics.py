"""
Firestore Dashboard Analytics Module
Handles data processing and API endpoints for dashboard charts using Firestore as data source
"""

import os
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import glob
from flask import jsonify, request, current_app, session
import pandas as pd
import threading
import time

# Import Firebase related functions
from config.firebase_admin_setup import get_firestore_client

class FirestoreDashboardAnalytics:
    def __init__(self):
        """Initialize Firestore dashboard analytics"""
        self._cache = {}
        self._cache_timestamp = {}
        self._cache_ttl = 180  # Cache TTL in seconds (3 minutes - reduced for faster updates)
        self._cache_lock = threading.RLock()
    
    def _get_cache(self, key):
        """Get data from cache if available and not expired"""
        with self._cache_lock:
            if key in self._cache and key in self._cache_timestamp:
                if time.time() - self._cache_timestamp[key] < self._cache_ttl:
                    return self._cache[key]
        return None
    
    def _set_cache(self, key, data):
        """Set data in cache with current timestamp"""
        with self._cache_lock:
            self._cache[key] = data
            self._cache_timestamp[key] = time.time()
    
    def get_failed_analyses(self, user_uid=None, use_cache=True, limit=1000):
        """Extract failed analysis attempts from Firestore with user filtering
        
        Args:
            user_uid: User ID to filter failed analyses (optional)
            use_cache: Whether to use cached data
            limit: Maximum number of failed analyses to fetch (default 1000 to get all data)
        """
        cache_key = f'failed_analyses_data_{user_uid if user_uid else "all"}'
        
        # Try to get from cache first if use_cache is True
        if use_cache:
            cached_data = self._get_cache(cache_key)
            if cached_data is not None:
                return cached_data
        
        failed_analyses = []
        
        try:
            # Get Firestore client
            db = get_firestore_client()
            if db is None:
                current_app.logger.error("Firestore client not available")
                return failed_analyses
            
            # Query failed_analyses collection
            analyses_ref = db.collection('failed_analyses')
            
            # Apply user filter if user_uid is provided
            if user_uid:
                try:
                    from google.cloud import firestore
                    analyses_ref = analyses_ref.where(filter=firestore.FieldFilter('user_id', '==', user_uid))
                except (ImportError, TypeError, AttributeError):
                    analyses_ref = analyses_ref.where('user_id', '==', user_uid)
            
            try:
                # Try to get ALL failed analyses with ordering (no artificial limit)
                query_result = analyses_ref.order_by('timestamp', direction='DESCENDING').get()
            except Exception as query_error:
                # Fallback to simple query if ordering fails (might happen with missing indexes)
                current_app.logger.warning(f"Error with ordered query: {query_error}. Falling back to simple query.")
                query_result = analyses_ref.get()
            
            for doc in query_result:
                try:
                    analysis_data = doc.to_dict()
                    # Ensure we have the minimum required fields
                    if 'ticker' in analysis_data and 'timestamp' in analysis_data:
                        # Convert Firestore timestamp to Python datetime if needed
                        if hasattr(analysis_data.get('date'), 'timestamp'):
                            # Firestore timestamp object
                            date = analysis_data['date'].timestamp()
                            date = datetime.fromtimestamp(date)
                        elif isinstance(analysis_data.get('date'), datetime):
                            date = analysis_data['date']
                        else:
                            # Integer timestamp
                            date = datetime.fromtimestamp(analysis_data['timestamp'])
                        
                        failed_analyses.append({
                            'ticker': analysis_data['ticker'],
                            'timestamp': analysis_data['timestamp'],
                            'date': date,
                            'error_message': analysis_data.get('error_message', 'Unknown error'),
                            'user_id': analysis_data.get('user_id', ''),
                            'doc_id': doc.id
                        })
                except Exception as doc_error:
                    current_app.logger.error(f"Error processing failed analysis document {doc.id}: {doc_error}")
                    continue
            
        except Exception as e:
            current_app.logger.error(f"Error fetching failed analyses from Firestore: {e}")
        
        # Save to cache
        self._set_cache(cache_key, failed_analyses)
        return failed_analyses

    def get_reports_data(self, user_uid=None, use_cache=True, limit=1000):
        """Extract data from Firestore userGeneratedReports collection with user filtering
        
        Args:
            user_uid: User ID to filter reports (required for user-specific data)
            use_cache: Whether to use cached data
            limit: Maximum number of reports to fetch (default 1000 to get all user data)
        """
        import time
        from flask import g
        
        # Use request-level cache to avoid duplicate queries in parallel API calls
        cache_attr = f'_reports_cache_{user_uid if user_uid else "all"}'
        if hasattr(g, cache_attr):
            current_app.logger.info(f"Returning request-cached reports for user {user_uid[:8] if user_uid else 'all'}...")
            return getattr(g, cache_attr)
        
        # User-specific cache key
        cache_key = f'reports_data_{user_uid if user_uid else "all"}'
        
        # Try to get from cache first if use_cache is True
        if use_cache:
            cached_data = self._get_cache(cache_key)
            if cached_data is not None:
                current_app.logger.info(f"Returning cached reports for user {user_uid[:8] if user_uid else 'all'}... ({len(cached_data)} reports)")
                # Also set in request context
                setattr(g, cache_attr, cached_data)
                return cached_data
        
        start_time = time.time()
        reports = []
        
        try:
            # Get Firestore client
            db = get_firestore_client()
            if db is None:
                current_app.logger.error("Firestore client not available")
                return reports
            
            # Query userGeneratedReports collection (correct collection)
            reports_ref = db.collection('userGeneratedReports')
            
            # Apply user filter if user_uid is provided
            if user_uid:
                try:
                    # Try new Firestore API first (v2)
                    from google.cloud import firestore
                    reports_ref = reports_ref.where(filter=firestore.FieldFilter('user_uid', '==', user_uid))
                except (ImportError, TypeError, AttributeError):
                    # Fallback to old API
                    reports_ref = reports_ref.where('user_uid', '==', user_uid)
            
            query_start = time.time()
            try:
                # Try to get ALL reports with ordering (no artificial limit for user data)
                query_result = reports_ref.order_by('generated_at', direction='DESCENDING').get()
            except Exception as query_error:
                # Fallback to simple query if ordering fails (might happen with missing indexes)
                current_app.logger.warning(f"Error with ordered query: {query_error}. Falling back to simple query.")
                query_result = reports_ref.get()
            
            query_duration = time.time() - query_start
            current_app.logger.info(f"Firestore query for user {user_uid[:8] if user_uid else 'all'}... took {query_duration:.2f}s")
            
            for doc in query_result:
                try:
                    report_data = doc.to_dict()
                    # Ensure we have the minimum required fields
                    if 'ticker' in report_data:
                        # Normalize date - handle multiple date field formats
                        date = None
                        if 'generated_at' in report_data:
                            if hasattr(report_data['generated_at'], 'timestamp'):
                                date = datetime.fromtimestamp(report_data['generated_at'].timestamp())
                            elif isinstance(report_data['generated_at'], datetime):
                                date = report_data['generated_at']
                            elif isinstance(report_data['generated_at'], str):
                                try:
                                    date = datetime.fromisoformat(report_data['generated_at'].replace('Z', '+00:00'))
                                except ValueError:
                                    pass
                        
                        if not date:
                            date = datetime.now()
                        
                        timestamp = int(date.timestamp()) if date else 0
                        
                        reports.append({
                            'ticker': report_data['ticker'],
                            'timestamp': timestamp,
                            'date': date,
                            'filename': report_data.get('filename', f"{report_data['ticker']}_detailed_report_{timestamp}.html"),
                            'file_size': report_data.get('file_size', 0),
                            'file_path': report_data.get('file_path', ''),
                            'user_id': report_data.get('user_uid', ''),
                            'published': report_data.get('published', True),
                            'sector': report_data.get('sector', 'Other'),
                            'doc_id': doc.id
                        })
                except Exception as doc_error:
                    current_app.logger.error(f"Error processing document {doc.id}: {doc_error}")
                    continue
            
            total_duration = time.time() - start_time
            current_app.logger.info(f"Fetched {len(reports)} reports for user {user_uid[:8] if user_uid else 'all'}... in {total_duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            current_app.logger.error(f"Error fetching reports from Firestore after {duration:.2f}s: {e}")
            import traceback
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Save to cache with shorter TTL for user-specific data
        self._set_cache(cache_key, reports)
        # Also set in request context to avoid duplicate queries
        setattr(g, cache_attr, reports)
        return reports
    
    def get_reports_over_time(self, period='week', user_uid=None):
        """Get reports generated over time data
        
        Args:
            period: Time period grouping ('week', 'month', 'quarter', 'year')
            user_uid: User ID to filter reports
        """
        cache_key = f'reports_over_time_{user_uid}_{period}'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data(user_uid=user_uid)
        
        if not reports:
            return {'labels': [], 'data': [], 'has_data': False}
        
        # Group by period
        grouped = defaultdict(int)
        
        for report in reports:
            date = report['date']
            
            if period == 'week':
                # Group by day of week
                key = date.strftime('%a')
            elif period == 'month':
                # Group by week
                key = f"Week {date.isocalendar()[1]}"
            elif period == 'quarter':
                # Group by month
                key = date.strftime('%b')
            else:
                key = date.strftime('%Y-%m-%d')
            
            grouped[key] += 1
        
        # Sort and format
        if period == 'week':
            days_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            labels = days_order
            data = [grouped.get(day, 0) for day in days_order]
        else:
            sorted_items = sorted(grouped.items())
            labels = [item[0] for item in sorted_items]
            data = [item[1] for item in sorted_items]
        
        result = {'labels': labels, 'data': data, 'has_data': True}
        self._set_cache(cache_key, result)
        return result
    
    def get_most_analyzed_tickers(self, limit=5, user_uid=None):
        """Get most analyzed tickers
        
        Args:
            limit: Number of top tickers to return
            user_uid: User ID to filter reports
        """
        cache_key = f'most_analyzed_tickers_{user_uid}_{limit}'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data(user_uid=user_uid)
        
        if not reports:
            return {'tickers': [], 'counts': [], 'sectors': [], 'has_data': False}
        
        # Count tickers
        ticker_counts = Counter(report['ticker'] for report in reports)
        
        # Get top tickers
        top_tickers = ticker_counts.most_common(limit)
        
        tickers = [ticker for ticker, count in top_tickers]
        counts = [count for ticker, count in top_tickers]
        
        # Get sectors from report data if available, otherwise use default mapping
        sector_mapping = {
            'TSLA': 'Technology', 'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
            'AMZN': 'Consumer', 'NVDA': 'Technology', 'META': 'Technology', 'NFLX': 'Consumer',
            'JPM': 'Finance', 'JNJ': 'Healthcare', 'XOM': 'Energy', 'JSM': 'Other'
        }
        
        sectors = []
        for ticker in tickers:
            # Find reports for this ticker
            ticker_reports = [r for r in reports if r['ticker'] == ticker]
            if ticker_reports and 'sector' in ticker_reports[0]:
                sectors.append(ticker_reports[0]['sector'])
            else:
                sectors.append(sector_mapping.get(ticker, 'Other'))
        
        result = {'tickers': tickers, 'counts': counts, 'sectors': sectors, 'has_data': True}
        self._set_cache(cache_key, result)
        return result
    
    def get_publishing_status(self, user_uid=None):
        """Get publishing status breakdown
        
        Args:
            user_uid: User ID to filter reports
        """
        cache_key = f'publishing_status_{user_uid}'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data(user_uid=user_uid)
        
        if not reports:
            return {'labels': ['Published'], 'data': [0], 'colors': ['#10b981'], 'has_data': False}
        
        published_count = len([r for r in reports if r.get('published', True)])
        unpublished_count = len(reports) - published_count
        
        labels = ['Published']
        data = [published_count]
        colors = ['#10b981']  # Green
        
        # Only add unpublished if there are any
        if unpublished_count > 0:
            labels.append('Unpublished')
            data.append(unpublished_count)
            colors.append('#f43f5e')  # Red
        
        result = {
            'labels': labels,
            'data': data,
            'colors': colors,
            'has_data': True
        }
        self._set_cache(cache_key, result)
        return result
    
    def get_activity_heatmap(self, year=None, user_uid=None):
        """Get activity heatmap data
        
        Args:
            year: Year to show heatmap for (defaults to most recent)
            user_uid: User ID to filter reports
        """
        cache_key = f'activity_heatmap_{user_uid}_{year}'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data(user_uid=user_uid)
        if not reports:
            return {'heatmap': {}, 'has_data': False, 'year': None}

        # If year is not provided, use the most recent year with data
        years_with_data = sorted(set(r['date'].year for r in reports), reverse=True)
        if not years_with_data:
            return {'heatmap': {}, 'has_data': False, 'year': None}

        if year is None:
            year = years_with_data[0]
        elif year not in years_with_data:
            # If requested year has no data, use most recent year
            year = years_with_data[0]

        # Count reports per day for the selected year
        heatmap_data = {}
        for report in reports:
            if report['date'].year == year:
                date_str = report['date'].strftime('%Y-%m-%d')
                heatmap_data[date_str] = heatmap_data.get(date_str, 0) + 1
        
        result = {'heatmap': heatmap_data, 'has_data': bool(heatmap_data), 'year': year}
        self._set_cache(cache_key, result)
        return result
    
    def get_dashboard_stats(self, user_uid=None):
        """Get overall dashboard statistics
        
        Args:
            user_uid: User ID to filter reports
        """
        cache_key = f'dashboard_stats_{user_uid}'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data(user_uid=user_uid)
        
        if not reports:
            return {
                'total_reports': 0,
                'this_month': 0,
                'published_reports': 0,
                'unique_tickers': 0,
                'has_data': False
            }
        
        total_reports = len(reports)
        
        # This month
        now = datetime.now()
        this_month = len([r for r in reports if r['date'].month == now.month and r['date'].year == now.year])
        
        # Published reports
        published_reports = len([r for r in reports if r.get('published', True)])
        
        # Unique tickers
        unique_tickers = len(set(r['ticker'] for r in reports))
        
        result = {
            'total_reports': total_reports,
            'this_month': this_month,
            'published_reports': published_reports,
            'unique_tickers': unique_tickers,
            'has_data': True
        }
        self._set_cache(cache_key, result)
        return result
    
    def get_failed_analyses_stats(self, user_uid=None):
        """Get statistics about failed analyses
        
        Args:
            user_uid: User ID to filter failed analyses
        """
        cache_key = f'failed_analyses_stats_{user_uid}'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        failed_analyses = self.get_failed_analyses(user_uid=user_uid)
        
        if not failed_analyses:
            return {'has_data': False, 'counts': {}}
        
        # Count failed analyses by ticker
        ticker_counts = Counter([analysis['ticker'] for analysis in failed_analyses])
        most_common = ticker_counts.most_common(10)  # Get top 10 failed tickers
        
        # Group by date (daily)
        today = datetime.now().date()
        last_week = today - timedelta(days=7)
        
        daily_counts = Counter()
        for analysis in failed_analyses:
            analysis_date = analysis['date'].date()
            if analysis_date >= last_week:
                daily_counts[analysis_date.isoformat()] += 1
        
        # Recent errors (last 24 hours)
        recent_errors = [
            analysis for analysis in failed_analyses 
            if (datetime.now() - analysis['date']).total_seconds() < 86400  # 24 hours
        ]
        
        result = {
            'has_data': len(failed_analyses) > 0,
            'total_failures': len(failed_analyses),
            'top_failed_tickers': [
                {'ticker': ticker, 'count': count} for ticker, count in most_common
            ],
            'daily_failures': [
                {'date': date, 'count': count} for date, count in sorted(daily_counts.items())
            ],
            'recent_failures': len(recent_errors),
            'recent_errors': [
                {
                    'ticker': err['ticker'],
                    'timestamp': err['timestamp'],
                    'date': err['date'].isoformat(),
                    'error_message': err['error_message']
                }
                for err in sorted(recent_errors, key=lambda x: x['timestamp'], reverse=True)[:5]  # Top 5 recent errors
            ]
        }
        
        self._set_cache(cache_key, result)
        return result

    def clear_cache(self):
        """Clear all cached data"""
        with self._cache_lock:
            self._cache.clear()
            self._cache_timestamp.clear()
        return {"status": "success", "message": "Cache cleared successfully"}

# Initialize analytics
firestore_analytics = FirestoreDashboardAnalytics()

def register_firestore_dashboard_routes(app, cache_instance=None):
    """Register Firestore dashboard API routes"""
    cache = cache_instance
    
    @app.route('/api/dashboard/stats')
    def api_dashboard_stats():
        """Get dashboard statistics from Firestore"""
        try:
            user_uid = session.get('firebase_user_uid', 'anonymous')
            cache_key = f"analytics_stats_{user_uid}"

            if cache:
                cached = cache.get(cache_key)
                if cached:
                    return jsonify(cached)

            stats = firestore_analytics.get_dashboard_stats(user_uid=user_uid)

            if cache:
                cache.set(cache_key, stats, timeout=300)

            return jsonify(stats)
        except Exception as e:
            app.logger.error(f"Error in dashboard stats API: {e}")
            # Return a user-friendly error message without exposing internal details
            return jsonify({
                'error': "Could not fetch dashboard statistics",
                'has_data': False,
                'total_reports': 0,
                'this_month': 0,
                'published_reports': 0,
                'unique_tickers': 0
            }), 500
    
    @app.route('/api/dashboard/reports-over-time')
    def api_reports_over_time():
        """Get reports over time data"""
        try:
            period = request.args.get('period', 'week')
            # Validate period parameter
            if period not in ['week', 'month', 'quarter', 'year']:
                period = 'week'  # Default to week if invalid
            
            user_uid = session.get('firebase_user_uid', 'anonymous')
            cache_key = f"analytics_reports_over_time_{user_uid}_{period}"

            if cache:
                cached = cache.get(cache_key)
                if cached:
                    return jsonify(cached)
            
            data = firestore_analytics.get_reports_over_time(period, user_uid=user_uid)

            if cache:
                cache.set(cache_key, data, timeout=300)

            return jsonify(data)
        except Exception as e:
            app.logger.error(f"Error in reports over time API: {e}")
            return jsonify({
                'error': "Could not fetch reports over time data",
                'labels': [],
                'data': [],
                'has_data': False
            }), 500
    
    @app.route('/api/dashboard/most-analyzed')
    def api_most_analyzed():
        """Get most analyzed tickers"""
        try:
            # Parse and validate limit parameter with fallback
            try:
                limit = int(request.args.get('limit', 5))
                # Ensure limit is reasonable
                if limit < 1:
                    limit = 5
                elif limit > 50:  # Cap at a reasonable maximum
                    limit = 50
            except (ValueError, TypeError):
                limit = 5  # Default if invalid
                
            user_uid = session.get('firebase_user_uid', 'anonymous')
            cache_key = f"analytics_most_analyzed_{user_uid}_{limit}"

            if cache:
                cached = cache.get(cache_key)
                if cached:
                    return jsonify(cached)

            data = firestore_analytics.get_most_analyzed_tickers(limit, user_uid=user_uid)

            if cache:
                cache.set(cache_key, data, timeout=300)

            return jsonify(data)
        except Exception as e:
            app.logger.error(f"Error in most analyzed tickers API: {e}")
            return jsonify({
                'error': "Could not fetch most analyzed tickers",
                'tickers': [],
                'counts': [],
                'sectors': [],
                'has_data': False
            }), 500
    
    @app.route('/api/dashboard/publishing-status')
    def api_publishing_status():
        """Get publishing status data"""
        try:
            user_uid = session.get('firebase_user_uid', 'anonymous')
            cache_key = f"analytics_publishing_status_{user_uid}"

            if cache:
                cached = cache.get(cache_key)
                if cached:
                    return jsonify(cached)

            data = firestore_analytics.get_publishing_status(user_uid=user_uid)

            if cache:
                cache.set(cache_key, data, timeout=300)

            return jsonify(data)
        except Exception as e:
            app.logger.error(f"Error in publishing status API: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/dashboard/activity-heatmap')
    def api_activity_heatmap():
        """Get activity heatmap data"""
        try:
            year = request.args.get('year')
            year = int(year) if year else None
            user_uid = session.get('firebase_user_uid', 'anonymous')
            cache_key = f"analytics_activity_heatmap_{user_uid}_{year if year else 'all'}"

            if cache:
                cached = cache.get(cache_key)
                if cached:
                    return jsonify(cached)

            data = firestore_analytics.get_activity_heatmap(year, user_uid=user_uid)

            if cache:
                cache.set(cache_key, data, timeout=300)

            return jsonify(data)
        except Exception as e:
            app.logger.error(f"Error in activity heatmap API: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/dashboard/failed-analyses')
    def api_failed_analyses():
        """Get statistics about failed analyses"""
        try:
            user_uid = session.get('firebase_user_uid', 'anonymous')
            cache_key = f"analytics_failed_analyses_{user_uid}"

            if cache:
                cached = cache.get(cache_key)
                if cached:
                    return jsonify(cached)

            data = firestore_analytics.get_failed_analyses_stats(user_uid=user_uid)

            if cache:
                cache.set(cache_key, data, timeout=300)

            return jsonify(data)
        except Exception as e:
            app.logger.error(f"Error in failed analyses API: {e}")
            return jsonify({
                'error': "Could not fetch failed analyses data",
                'has_data': False,
                'total_failures': 0,
                'top_failed_tickers': [],
                'daily_failures': [],
                'recent_failures': 0,
                'recent_errors': []
            }), 500
            
    @app.route('/api/dashboard/clear-cache')
    def api_clear_cache():
        """Clear dashboard analytics cache"""
        try:
            result = firestore_analytics.clear_cache()
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error clearing cache: {e}")
            return jsonify({'error': str(e)}), 500
