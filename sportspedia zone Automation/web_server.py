"""
Sports News Viewer Web Application
A Flask web server to view and filter sports news articles from JSON database
"""

from flask import Flask, render_template_string, send_file, jsonify
import json
import os
from datetime import datetime, timedelta
from dateutil import parser

app = Flask(__name__)

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, 'sports_news_database.json')
HTML_FILE = os.path.join(BASE_DIR, 'news_viewer.html')

def load_news_database():
    """Load the news database from JSON file"""
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {JSON_FILE} not found")
        return {"metadata": {"total_articles": 0, "sources": []}, "articles": []}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return {"metadata": {"total_articles": 0, "sources": []}, "articles": []}

def cleanup_old_articles_on_startup(json_file, hours_threshold=24):
    """Clean up old articles when server starts"""
    try:
        if not os.path.exists(json_file):
            return
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = data.get('articles', [])
        if not articles:
            return
            
        current_time = datetime.now()
        recent_articles = []
        removed_count = 0
        
        for article in articles:
            published_date = article.get('published_date', '')
            collected_date = article.get('collected_date', '')
            
            try:
                # Parse article date
                if published_date:
                    if 'GMT' in published_date:
                        article_date = datetime.strptime(published_date, '%a, %d %b %Y %H:%M:%S GMT')
                    else:
                        article_date = parser.parse(published_date)
                        if article_date.tzinfo:
                            article_date = article_date.replace(tzinfo=None)
                else:
                    article_date = parser.parse(collected_date)
                    if article_date.tzinfo:
                        article_date = article_date.replace(tzinfo=None)
                
                # Check if article is recent
                time_diff = current_time - article_date
                if time_diff.total_seconds() <= (hours_threshold * 3600):
                    recent_articles.append(article)
                else:
                    removed_count += 1
                    
            except Exception:
                # If date parsing fails, remove the article
                removed_count += 1
        
        # Update database if cleanup needed
        if removed_count > 0:
            data['articles'] = recent_articles
            data['metadata']['total_articles'] = len(recent_articles)
            data['metadata']['last_startup_cleanup'] = datetime.now().isoformat()
            
            # Save updated database
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"🧹 Startup cleanup: Removed {removed_count} old articles, kept {len(recent_articles)} recent articles")
        
    except Exception as e:
        print(f"Warning: Startup cleanup failed: {e}")

@app.route('/')
def index():
    """Serve the main HTML page"""
    try:
        with open(HTML_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #dc3545; }
            </style>
        </head>
        <body>
            <h1 class="error">Error: HTML file not found</h1>
            <p>Please make sure news_viewer.html exists in the same directory.</p>
        </body>
        </html>
        """, 404

@app.route('/sports_news_database.json')
def get_json_data():
    """Serve the JSON data file"""
    try:
        return send_file(JSON_FILE, mimetype='application/json')
    except FileNotFoundError:
        return jsonify({
            "error": "JSON file not found",
            "metadata": {"total_articles": 0, "sources": []}, 
            "articles": []
        }), 404

@app.route('/api/stats')
def get_stats():
    """API endpoint to get database statistics"""
    data = load_news_database()
    metadata = data.get('metadata', {})
    articles = data.get('articles', [])
    
    # Calculate additional stats
    sources = list(set(article.get('source_name', '') for article in articles))
    categories = list(set(cat for article in articles for cat in article.get('categories', [])))
    
    recent_articles = []
    if articles:
        # Sort by date and get last 5
        sorted_articles = sorted(articles, 
                               key=lambda x: x.get('published_date', ''), 
                               reverse=True)
        recent_articles = sorted_articles[:5]
    
    return jsonify({
        'total_articles': len(articles),
        'sources_count': len(sources),
        'categories_count': len(categories),
        'sources': sources,
        'categories': categories,
        'last_updated': metadata.get('last_updated'),
        'created_date': metadata.get('created_date'),
        'recent_articles': recent_articles
    })

@app.route('/api/search')
def search_articles():
    """API endpoint for searching articles"""
    from flask import request
    
    data = load_news_database()
    articles = data.get('articles', [])
    
    # Get query parameters
    query = request.args.get('q', '').lower()
    source = request.args.get('source', '')
    category = request.args.get('category', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Filter articles
    filtered_articles = articles
    
    if query:
        filtered_articles = [
            article for article in filtered_articles
            if query in article.get('title', '').lower() or 
               query in article.get('summary', '').lower()
        ]
    
    if source:
        filtered_articles = [
            article for article in filtered_articles
            if article.get('source_name', '') == source
        ]
    
    if category:
        filtered_articles = [
            article for article in filtered_articles
            if category in article.get('categories', [])
        ]
    
    # Date filtering
    if date_from or date_to:
        def parse_date(date_str):
            try:
                return datetime.strptime(date_str[:10], '%Y-%m-%d')
            except:
                return None
        
        if date_from:
            from_date = parse_date(date_from)
            if from_date:
                filtered_articles = [
                    article for article in filtered_articles
                    if parse_date(article.get('published_date', '')) and 
                       parse_date(article.get('published_date', '')) >= from_date
                ]
        
        if date_to:
            to_date = parse_date(date_to)
            if to_date:
                filtered_articles = [
                    article for article in filtered_articles
                    if parse_date(article.get('published_date', '')) and 
                       parse_date(article.get('published_date', '')) <= to_date
                ]
    
    return jsonify({
        'total': len(filtered_articles),
        'articles': filtered_articles
    })

@app.errorhandler(404)
def not_found(error):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Not Found</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .error { color: #dc3545; }
        </style>
    </head>
    <body>
        <h1 class="error">404 - Page Not Found</h1>
        <p>The requested page could not be found.</p>
        <a href="/">← Back to Sports News Viewer</a>
    </body>
    </html>
    """, 404

if __name__ == '__main__':
    print("🏆 Sports News Viewer Server")
    print("="*40)
    
    # Clean up old articles on startup
    cleanup_old_articles_on_startup(JSON_FILE, hours_threshold=24)
    
    # Check if files exist
    if os.path.exists(JSON_FILE):
        data = load_news_database()
        article_count = len(data.get('articles', []))
        print(f"✅ JSON Database: {article_count} articles loaded (last 24 hours)")
    else:
        print(f"❌ JSON Database: {JSON_FILE} not found")
    
    if os.path.exists(HTML_FILE):
        print(f"✅ HTML Template: news_viewer.html found")
    else:
        print(f"❌ HTML Template: news_viewer.html not found")
    
    print(f"\n🌐 Server starting at: http://localhost:5000")
    print("📱 Features available:")
    print("   • Advanced article filtering")
    print("   • Multiple view formats (Cards, List, Table)")
    print("   • Search functionality")
    print("   • Date range filtering")
    print("   • Source and category filtering")
    print("   • Pagination support")
    print("\n🔍 API Endpoints:")
    print("   • /api/stats - Database statistics")
    print("   • /api/search - Search articles with filters")
    print("\nPress Ctrl+C to stop the server")
    print("="*40)
    
    app.run(debug=True, host='0.0.0.0', port=5000)