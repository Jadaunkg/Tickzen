"""
Sports Article Automation Blueprint
===================================

This blueprint handles sports article automation routes:
- Dashboard
- Run Automation
- Trends Dashboard
- Content Library
- Publishing History

Routes:
-------
/automation/sports/dashboard - Sports automation dashboard
/automation/sports/run - Run sports automation
/automation/sports/trends - Google Trends dashboard
/automation/sports/library - Sports articles content library
/automation/sports/history - Publishing history (redirects to shared history)
"""

from flask import Blueprint, render_template, redirect, url_for, session, current_app, request, jsonify

# Always create a fresh blueprint - Flask handles duplicate registration checks internally
sports_automation_bp = Blueprint('sports_automation', __name__, url_prefix='/sports')

# Import dependencies from shared utils module (no circular import)
from app.blueprints.automation_utils import (
    login_required,
    get_user_site_profiles_from_firestore,
    get_automation_shared_context
)


@sports_automation_bp.route('/dashboard')
@login_required
def dashboard():
    """Sports automation dashboard - shows overview and stats with optimized queries."""
    user_uid = session['firebase_user_uid']
    
    # Get user site profiles
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    
    # Get shared context for automation
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    # Get Firestore client
    from app.blueprints.automation_utils import get_firestore_client
    db = get_firestore_client()
    
    # Initialize stats
    sports_published = 0
    rss_articles = 0
    trending_topics = []
    category_counts = {}
    
    # Fetch real published sports articles count from Firestore
    if db:
        try:
            # Query userPublishedArticles for sports articles
            sports_articles_ref = db.collection('userPublishedArticles')\
                .where('user_uid', '==', user_uid)\
                .where('article_type', '==', 'sports')
            
            sports_docs = list(sports_articles_ref.stream())
            sports_published = len(sports_docs)
            
            # Count articles by category with improved matching logic
            for doc in sports_docs:
                article_data = doc.to_dict()
                category = article_data.get('category', 'Uncategorized')
                
                # Normalize category name for better matching
                category_lower = category.lower().strip()
                
                # Map variations to standard category names
                if category_lower in ['cricket']:
                    category = 'Cricket'
                elif category_lower in ['football', 'soccer']:
                    category = 'Football'
                elif category_lower in ['basketball', 'nba']:
                    category = 'Basketball'
                elif category_lower in ['tennis']:
                    category = 'Tennis'
                elif category_lower in ['formula 1', 'f1', 'formula1']:
                    category = 'Formula 1'
                elif category_lower in ['golf']:
                    category = 'Golf'
                elif category_lower in ['baseball']:
                    category = 'Baseball'
                elif category_lower in ['hockey', 'nhl']:
                    category = 'Hockey'
                elif category_lower in ['rugby']:
                    category = 'Rugby'
                else:
                    category = 'Other'
                
                category_counts[category] = category_counts.get(category, 0) + 1
            
            current_app.logger.info(f"Found {sports_published} published sports articles for user {user_uid}")
            current_app.logger.info(f"Category counts: {category_counts}")
        except Exception as e:
            current_app.logger.warning(f"Error fetching published sports articles: {e}")
    
    # Fetch trending topics from Google Trends database
    try:
        from Sports_Article_Automation.api.google_trends_api import get_google_trends_loader
        
        trends_loader = get_google_trends_loader()
        # Get all sports trending topics (not limited)
        all_trends = trends_loader.get_trending_topics(category='sports')
        
        if all_trends and isinstance(all_trends, list):
            # Filter out invalid trends (like UI elements)
            valid_trends = [
                t for t in all_trends 
                if t.get('query') and 
                t.get('query') not in ['arrow_forward_ios', 'Sports'] and
                len(t.get('query', '')) > 2
            ]
            trending_topics = valid_trends[:5]  # Top 5 valid trending topics
            
            current_app.logger.info(f"Loaded {len(all_trends)} total trends, {len(valid_trends)} valid trends from Google Trends database")
        else:
            current_app.logger.warning("No trending topics found in Google Trends database")
    except ImportError as ie:
        current_app.logger.warning(f"Could not import Google Trends loader: {ie}")
    except Exception as e:
        current_app.logger.warning(f"Could not load trending topics for dashboard: {e}")
    
    # Load RSS articles count from sports article loader
    try:
        from Sports_Article_Automation.api.sports_articles_loader import get_sports_loader
        
        sports_loader = get_sports_loader()
        rss_articles_data = sports_loader.load_articles()
        rss_articles = len(rss_articles_data) if rss_articles_data else 0
        
        current_app.logger.info(f"Found {rss_articles} RSS articles in sports loader")
    except ImportError as ie:
        current_app.logger.warning(f"Could not import sports loader: {ie}")
    except Exception as e:
        current_app.logger.warning(f"Could not load RSS articles count: {e}")
    
    # Sport categories with real counts (optimized with consolidated logic)
    sport_categories = [
        {
            'name': 'Cricket', 
            'icon': 'fa-baseball-ball', 
            'count': category_counts.get('Cricket', 0)
        },
        {
            'name': 'Football', 
            'icon': 'fa-futbol', 
            'count': category_counts.get('Football', 0)
        },
        {
            'name': 'Basketball', 
            'icon': 'fa-basketball-ball', 
            'count': category_counts.get('Basketball', 0)
        },
        {
            'name': 'Tennis', 
            'icon': 'fa-table-tennis', 
            'count': category_counts.get('Tennis', 0)
        },
        {
            'name': 'Formula 1', 
            'icon': 'fa-flag-checkered', 
            'count': category_counts.get('Formula 1', 0)
        },
        {
            'name': 'Golf', 
            'icon': 'fa-golf-ball', 
            'count': category_counts.get('Golf', 0)
        }
    ]
    
    return render_template('automation/sports/dashboard.html',
                         title="Sports Dashboard - Tickzen",
                         user_site_profiles=user_site_profiles,
                         sports_published=sports_published,
                         trending_count=len(trending_topics),
                         rss_articles=rss_articles,
                         connected_sites=len(user_site_profiles) if user_site_profiles else 0,
                         trending_topics=trending_topics,
                         sport_categories=sport_categories,
                         **shared_context)


@sports_automation_bp.route('/run')
@login_required
def run():
    """Run sports article automation."""
    user_uid = session['firebase_user_uid']
    
    # Get user site profiles
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    
    # Get shared context for automation
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    # Fetch sports articles from Sports Article Automation folder
    sports_articles = []
    try:
        from Sports_Article_Automation.api.sports_articles_loader import get_sports_loader
        
        # Get sports loader and load articles
        sports_loader = get_sports_loader()
        articles = sports_loader.load_articles()
        
        # Sort by published date (newest first)
        articles.sort(key=lambda x: x.get('published_date', ''), reverse=True)
        
        # Load ALL articles - pagination handled by frontend
        sports_articles = articles
        
        # Convert timestamps to IST for display
        def convert_articles_to_ist_display(articles_list):
            import pytz
            from datetime import datetime
            from email.utils import parsedate_to_datetime
            
            ist = pytz.timezone('Asia/Kolkata')
            utc = pytz.UTC
            
            for article in articles_list:
                if article.get('published_date'):
                    try:
                        # Parse the timestamp - support multiple formats
                        if isinstance(article['published_date'], str):
                            pub_date = article['published_date']
                            
                            # Try ISO format first
                            try:
                                dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                            except ValueError:
                                # Try RFC 2822 format (e.g., "Mon, 12 Jan 2026 15:03:34 GMT")
                                try:
                                    dt = parsedate_to_datetime(pub_date)
                                except (ValueError, TypeError):
                                    # Try common datetime formats
                                    for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%a, %d %b %Y %H:%M:%S %Z']:
                                        try:
                                            dt = datetime.strptime(pub_date, fmt)
                                            break
                                        except ValueError:
                                            continue
                                    else:
                                        raise ValueError(f"Unable to parse date format: {pub_date}")
                        else:
                            dt = article['published_date']
                        
                        # Convert to IST
                        if dt.tzinfo is None:
                            dt = utc.localize(dt)
                        ist_time = dt.astimezone(ist)
                        
                        article['display_date_ist'] = ist_time.strftime('%Y-%m-%d %H:%M:%S IST')
                    except Exception as e:
                        current_app.logger.warning(f"Error converting timestamp for article: {e}")
                        article['display_date_ist'] = article.get('published_date', 'N/A')
            
            return articles_list
        
        sports_articles = convert_articles_to_ist_display(sports_articles)
        
    except ImportError as e:
        current_app.logger.warning(f"Could not import sports loader: {e}")
    except Exception as e:
        current_app.logger.error(f"Error loading sports articles: {e}")
    
    return render_template('automation/sports/run.html',
                         title="Sports Article Automation - Tickzen",
                         user_site_profiles=user_site_profiles,
                         sports_articles=sports_articles,
                         **shared_context)


@sports_automation_bp.route('/trends')
@login_required
def trends():
    """Google Trends dashboard for sports content - redesigned."""
    from datetime import datetime
    user_uid = session['firebase_user_uid']
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    trends_data = []
    total_trends = 0
    sports_trends_count = 0
    last_collection_date = None
    system_active = False
    
    try:
        # Import Google Trends loader
        from Sports_Article_Automation.api.google_trends_api import get_google_trends_loader
        
        trends_loader = get_google_trends_loader()
        
        # Get all trending topics
        all_trends = trends_loader.get_trending_topics()
        
        if all_trends:
            system_active = True
            total_trends = len(all_trends)
            
            # Filter valid trends (remove UI elements and generic terms)
            valid_trends = [
                t for t in all_trends 
                if t.get('query') and 
                t.get('query') not in ['arrow_forward_ios', 'Sports'] and
                len(t.get('query', '')) > 2
            ]
            
            # Re-index the ranks to start from 1
            for idx, trend in enumerate(valid_trends, start=1):
                trend['display_rank'] = idx
            
            trends_data = valid_trends
            
            # Count sports trends
            sports_trends_count = len([t for t in trends_data if t.get('category', '').lower() == 'sports'])
            
            # Get latest collection date
            if trends_data:
                last_collection_date = trends_data[0].get('collected_date')
                if last_collection_date:
                    try:
                        dt = datetime.fromisoformat(last_collection_date.replace('Z', '+00:00'))
                        last_collection_date = dt.strftime('%d %b, %H:%M')
                    except:
                        last_collection_date = 'Unknown'
            
            current_app.logger.info(f"Loaded {total_trends} trends ({sports_trends_count} sports) for trends monitor")
        else:
            current_app.logger.warning("No trends data available")
            
    except ImportError as e:
        current_app.logger.warning(f"Could not import Google Trends loader: {e}")
    except Exception as e:
        current_app.logger.error(f"Error loading trends data: {e}")
    
    return render_template('automation/sports/trends.html',
                         title="Google Trends Monitor - Tickzen",
                         user_site_profiles=user_site_profiles,
                         trends_data=trends_data,
                         total_trends=total_trends,
                         sports_trends_count=sports_trends_count,
                         last_collection_date=last_collection_date,
                         system_active=system_active,
                         **shared_context)


@sports_automation_bp.route('/trends/collect', methods=['POST'])
@login_required
def collect_trends():
    """Collect latest Google Trends data."""
    user_uid = session['firebase_user_uid']
    
    try:
        current_app.logger.info(f"[TRENDS_COLLECTION] Starting trends collection for user {user_uid}")
        
        # Import the Google Trends pipeline
        from Sports_Article_Automation.google_trends.google_trends_pipeline import GoogleTrendsAutomationPipeline
        from pathlib import Path
        
        # Initialize the pipeline
        sports_root = Path(current_app.root_path).parent / "Sports_Article_Automation"
        pipeline = GoogleTrendsAutomationPipeline(project_root=str(sports_root))
        
        # Run the collection
        current_app.logger.info("[TRENDS_COLLECTION] Running full collection pipeline...")
        results = pipeline.run_full_collection()
        
        if results.get('success'):
            current_app.logger.info(f"[TRENDS_COLLECTION] ✅ Success! New trends: {results.get('total_new_trends', 0)}")
            return jsonify({
                'success': True,
                'message': f"Successfully collected {results.get('total_new_trends', 0)} new trends!",
                'total_new_trends': results.get('total_new_trends', 0),
                'timestamp': results.get('timestamp')
            })
        else:
            error_msg = ', '.join(results.get('errors', ['Unknown error']))
            current_app.logger.error(f"[TRENDS_COLLECTION] ❌ Failed: {error_msg}")
            return jsonify({
                'success': False,
                'message': f"Collection failed: {error_msg[:100]}"
            }), 500
            
    except ImportError as e:
        current_app.logger.error(f"[TRENDS_COLLECTION] Import error: {e}")
        return jsonify({
            'success': False,
            'message': 'Google Trends collection system not available'
        }), 503
    except Exception as e:
        current_app.logger.error(f"[TRENDS_COLLECTION] Error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error collecting trends: {str(e)[:100]}'
        }), 500


@sports_automation_bp.route('/library')
@login_required
def library():
    """Sports articles content library - shows all available articles."""
    # For now, redirect to run page which shows the articles
    # Later, this can be replaced with a dedicated library template
    return redirect(url_for('automation.sports_automation.run'))


@sports_automation_bp.route('/history')
@login_required
def history():
    """Redirect to global publishing history."""
    return redirect(url_for('automation.history'))
