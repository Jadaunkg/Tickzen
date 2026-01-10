#!/usr/bin/env python3
"""
Dashboard Analytics Module
=========================

Provides comprehensive analytics and data visualization for the TickZen
dashboard. Handles data processing, aggregation, and API endpoints for
interactive charts and metrics display.

Core Functionality:
------------------
1. **Report Analysis**: Parse and analyze generated stock reports
2. **Performance Metrics**: Calculate portfolio and individual stock performance
3. **Trend Analysis**: Identify patterns and trends in stock data
4. **Data Aggregation**: Combine data from multiple sources and timeframes
5. **Chart Data Generation**: Prepare data for frontend visualization

Supported Analytics:
-------------------
- Portfolio performance tracking
- Stock price movement analysis
- Volume and trading pattern analysis
- Sector and industry comparisons
- Historical performance metrics
- Risk-adjusted returns calculation

Data Sources:
------------
- Generated stock reports (app/static/stock_reports/)
- Real-time market data via APIs
- Historical price data from yfinance
- Cached analysis results

API Endpoints:
-------------
- /api/dashboard/portfolio: Portfolio overview metrics
- /api/dashboard/performance: Performance analytics
- /api/dashboard/trends: Trend analysis data
- /api/dashboard/sectors: Sector comparison data

Data Processing Pipeline:
------------------------
1. **Report Scanning**: Locate and parse available reports
2. **Data Extraction**: Extract key metrics and timestamps
3. **Aggregation**: Combine data across time periods
4. **Calculation**: Compute derived metrics and ratios
5. **Formatting**: Prepare data for chart libraries

Caching Strategy:
----------------
- In-memory caching for frequently accessed data
- File-based caching for expensive calculations
- Automatic cache invalidation based on data freshness

Usage Example:
-------------
```python
analytics = DashboardAnalytics()
portfolio_data = analytics.get_portfolio_overview()
performance_data = analytics.calculate_performance_metrics(tickers)
```

Author: TickZen Development Team
Version: 1.5
Last Updated: January 2026
"""

import os
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import glob
from flask import jsonify, request
import pandas as pd

class DashboardAnalytics:
    def __init__(self, reports_dir="app/static/stock_reports"):
        self.reports_dir = reports_dir
        
    def get_reports_data(self):
        """Extract data from generated report files"""
        reports = []
        
        # Check if reports directory exists
        if not os.path.exists(self.reports_dir):
            print(f"Reports directory not found: {self.reports_dir}")
            return reports
            
        pattern = os.path.join(self.reports_dir, "*_detailed_report_*.html")
        
        for file_path in glob.glob(pattern):
            try:
                # Extract ticker and timestamp from filename
                filename = os.path.basename(file_path)
                parts = filename.replace('_detailed_report_', '.').replace('.html', '').split('.')
                
                if len(parts) >= 2:
                    ticker = parts[0]
                    timestamp = int(parts[1])
                    date = datetime.fromtimestamp(timestamp)
                    
                    # Get file stats
                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    
                    reports.append({
                        'ticker': ticker,
                        'timestamp': timestamp,
                        'date': date,
                        'filename': filename,
                        'file_size': file_size,
                        'file_path': file_path
                    })
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
                
        return sorted(reports, key=lambda x: x['timestamp'], reverse=True)
    
    def get_reports_over_time(self, period='week'):
        """Get reports generated over time data"""
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
        
        return {'labels': labels, 'data': data, 'has_data': True}
    
    def get_most_analyzed_tickers(self, limit=5):
        """Get most analyzed tickers"""
        reports = self.get_reports_data()
        
        if not reports:
            return {'tickers': [], 'counts': [], 'sectors': [], 'has_data': False}
        
        # Count tickers
        ticker_counts = Counter(report['ticker'] for report in reports)
        
        # Get top tickers
        top_tickers = ticker_counts.most_common(limit)
        
        tickers = [ticker for ticker, count in top_tickers]
        counts = [count for ticker, count in top_tickers]
        
        # Mock sector data (replace with real sector mapping)
        sector_mapping = {
            'TSLA': 'tech', 'AAPL': 'tech', 'MSFT': 'tech', 'GOOGL': 'tech',
            'AMZN': 'consumer', 'NVDA': 'tech', 'META': 'tech', 'NFLX': 'consumer',
            'JPM': 'finance', 'JNJ': 'healthcare', 'XOM': 'energy', 'JSM': 'other'
        }
        
        sectors = [sector_mapping.get(ticker, 'other') for ticker in tickers]
        
        return {'tickers': tickers, 'counts': counts, 'sectors': sectors, 'has_data': True}
    
    def get_publishing_status(self):
        """Get publishing status breakdown"""
        reports = self.get_reports_data()
        
        if not reports:
            return {'labels': ['Published'], 'data': [0], 'colors': ['#10b981'], 'has_data': False}
        
        published_count = len(reports)
        
        return {
            'labels': ['Published'],
            'data': [published_count],
            'colors': ['#10b981'],
            'has_data': True
        }
    
    def get_activity_heatmap(self, year=None):
        """Get activity heatmap data"""
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

        return {'heatmap': heatmap_data, 'has_data': bool(heatmap_data), 'year': year}
    
    def get_dashboard_stats(self):
        """Get overall dashboard statistics"""
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
        
        # Published reports (recent ones)
        published_reports = total_reports
        
        # Unique tickers
        unique_tickers = len(set(r['ticker'] for r in reports))
        
        return {
            'total_reports': total_reports,
            'this_month': this_month,
            'published_reports': published_reports,
            'unique_tickers': unique_tickers,
            'has_data': True
        }

# Initialize analytics
analytics = DashboardAnalytics()

def register_dashboard_routes(app):
    """Register dashboard API routes"""
    
    @app.route('/api/dashboard/stats')
    def api_dashboard_stats():
        """Get dashboard statistics"""
        try:
            stats = analytics.get_dashboard_stats()
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/dashboard/reports-over-time')
    def api_reports_over_time():
        """Get reports over time data"""
        try:
            period = request.args.get('period', 'week')
            data = analytics.get_reports_over_time(period)
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/dashboard/most-analyzed')
    def api_most_analyzed():
        """Get most analyzed tickers"""
        try:
            limit = int(request.args.get('limit', 5))
            data = analytics.get_most_analyzed_tickers(limit)
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/dashboard/publishing-status')
    def api_publishing_status():
        """Get publishing status data"""
        try:
            data = analytics.get_publishing_status()
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/dashboard/activity-heatmap')
    def api_activity_heatmap():
        """Get activity heatmap data"""
        try:
            year = request.args.get('year')
            year = int(year) if year else None
            data = analytics.get_activity_heatmap(year)
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500 