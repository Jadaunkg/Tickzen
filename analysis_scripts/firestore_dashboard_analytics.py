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
        self._cache_ttl = 300  # Cache TTL in seconds (5 minutes)
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
    
    def get_failed_analyses(self, use_cache=True):
        """Extract failed analysis attempts from Firestore"""
        cache_key = 'failed_analyses_data'
        
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
            
            try:
                # Try to get failed analyses with ordering and limit
                query_result = analyses_ref.order_by('timestamp', direction='DESCENDING').limit(500).get()
            except Exception as query_error:
                # Fallback to simple query if ordering fails (might happen with missing indexes)
                current_app.logger.warning(f"Error with ordered query: {query_error}. Falling back to simple query.")
                query_result = analyses_ref.limit(500).get()
            
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

    def get_reports_data(self, use_cache=True):
        """Extract data from Firestore reports collection"""
        cache_key = 'reports_data'
        
        # Try to get from cache first if use_cache is True
        if use_cache:
            cached_data = self._get_cache(cache_key)
            if cached_data is not None:
                return cached_data
        
        reports = []
        
        try:
            # Get Firestore client
            db = get_firestore_client()
            if db is None:
                current_app.logger.error("Firestore client not available")
                return reports
            
            # Query reports collection
            reports_ref = db.collection('reports')
            
            try:
                # Try to get reports with ordering and limit
                query_result = reports_ref.order_by('timestamp', direction='DESCENDING').limit(500).get()
            except Exception as query_error:
                # Fallback to simple query if ordering fails (might happen with missing indexes)
                current_app.logger.warning(f"Error with ordered query: {query_error}. Falling back to simple query.")
                query_result = reports_ref.limit(500).get()
            
            for doc in query_result:
                try:
                    report_data = doc.to_dict()
                    # Ensure we have the minimum required fields
                    if 'ticker' in report_data and 'timestamp' in report_data:
                        # Convert Firestore timestamp to Python datetime if needed
                        if hasattr(report_data.get('date'), 'timestamp'):
                            # Firestore timestamp object
                            date = report_data['date'].timestamp()
                            date = datetime.fromtimestamp(date)
                        elif isinstance(report_data.get('date'), datetime):
                            date = report_data['date']
                        else:
                            # Integer timestamp
                            date = datetime.fromtimestamp(report_data['timestamp'])
                        
                        reports.append({
                            'ticker': report_data['ticker'],
                            'timestamp': report_data['timestamp'],
                            'date': date,
                            'filename': report_data.get('filename', f"{report_data['ticker']}_detailed_report_{report_data['timestamp']}.html"),
                            'file_size': report_data.get('file_size', 0),
                            'file_path': report_data.get('file_path', ''),
                            'user_id': report_data.get('user_id', ''),
                            'published': report_data.get('published', True),
                            'sector': report_data.get('sector', 'Other'),
                            'doc_id': doc.id
                        })
                except Exception as doc_error:
                    current_app.logger.error(f"Error processing document {doc.id}: {doc_error}")
                    continue
            
        except Exception as e:
            current_app.logger.error(f"Error fetching reports from Firestore: {e}")
        
        # Save to cache
        self._set_cache(cache_key, reports)
        return reports
    
    def get_reports_over_time(self, period='week'):
        """Get reports generated over time data"""
        cache_key = f'reports_over_time_{period}'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data()
        
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
    
    def get_most_analyzed_tickers(self, limit=5):
        """Get most analyzed tickers"""
        cache_key = f'most_analyzed_tickers_{limit}'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data()
        
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
    
    def get_publishing_status(self):
        """Get publishing status breakdown"""
        cache_key = 'publishing_status'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data()
        
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
    
    def get_activity_heatmap(self, year=None):
        """Get activity heatmap data"""
        cache_key = f'activity_heatmap_{year}'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data()
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
    
    def get_dashboard_stats(self):
        """Get overall dashboard statistics"""
        cache_key = 'dashboard_stats'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        reports = self.get_reports_data()
        
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
    
    def get_failed_analyses_stats(self):
        """Get statistics about failed analyses"""
        cache_key = 'failed_analyses_stats'
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        failed_analyses = self.get_failed_analyses()
        
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

            stats = firestore_analytics.get_dashboard_stats()

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
            
            data = firestore_analytics.get_reports_over_time(period)

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

            data = firestore_analytics.get_most_analyzed_tickers(limit)

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

            data = firestore_analytics.get_publishing_status()

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

            data = firestore_analytics.get_activity_heatmap(year)

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

            data = firestore_analytics.get_failed_analyses_stats()

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
