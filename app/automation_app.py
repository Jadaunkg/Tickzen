import os
import sys
import json
import logging
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_socketio import SocketIO
from flask_session import Session  # Added session support
from app.core.config import Config
from app.core.auth import login_required  # Add login_required import
from app.core.database import (
    init_firebase, verify_firebase_token,
    get_firestore_client, get_firebase_app_initialized
)
from app.core.utils import format_datetime_filter, format_earnings_date_filter

logger = logging.getLogger(__name__)

def create_automation_app(config_class=Config):
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
    
    # --- Register automation_utils dependencies (CRITICAL) ---
    # This injects Firestore client, Firebase init status, auto_publisher,
    # project root, and cache into the shared automation_utils module.
    # Without this, login_required and all Firestore queries will fail.
    auto_publisher_module = None
    try:
        from automation_scripts import auto_publisher as auto_publisher_module_import
        auto_publisher_module = auto_publisher_module_import
        logger.info("auto_publisher module loaded successfully")
    except ImportError as e:
        logger.warning(f"auto_publisher not available (non-critical): {e}")
    
    from app.blueprints.automation_utils import register_dependencies
    register_dependencies(
        get_firestore_client_func=get_firestore_client,
        get_firebase_app_initialized_func=get_firebase_app_initialized,
        auto_publisher_module=auto_publisher_module,
        project_root=PROJECT_ROOT,
        cache_instance=cache
    )
    logger.info("Automation dependencies registered successfully")
        
    # Register Context Processors
    from app.core.context_processors import register_context_processors
    register_context_processors(app)
    
    # Register Template Filters
    app.add_template_filter(format_datetime_filter, 'format_datetime')
    app.add_template_filter(format_earnings_date_filter, 'format_earnings_date')

    # Register Blueprints (Automation Hub)
    from app.blueprints.automation import automation_bp
    
    # Import child automation blueprints
    from app.blueprints.automation_stock import stock_automation_bp
    from app.blueprints.automation_earnings import earnings_automation_bp
    from app.blueprints.automation_sports import sports_automation_bp
    from app.blueprints.automation_jobs import jobs_automation_bp
    
    # Register children to the main automation hub blueprint (mimicking main app structure)
    # Note: These blueprints already have url_prefixes like '/stock-analysis'
    # automation_bp has url_prefix='/automation'
    # So final route is /automation/stock-analysis/...
    automation_bp.register_blueprint(stock_automation_bp)
    automation_bp.register_blueprint(earnings_automation_bp)
    automation_bp.register_blueprint(sports_automation_bp)
    automation_bp.register_blueprint(jobs_automation_bp)
    
    # Register the hub blueprint to the app
    app.register_blueprint(automation_bp)

    # Auth placeholder routes to satisfy login_required redirects
    @app.route('/login', methods=['GET'])
    def login():
        # Return JSON response - automation service is API-based
        return jsonify({
            'message': 'Please authenticate to access automation features.',
            'auth_required': True
        }), 401

    @app.route('/register', methods=['GET'])
    def register():
        # Return JSON response - automation service is API-based
        return jsonify({
            'message': 'Registration is handled through the main portal.',
            'redirect': '/'
        }), 403

    @app.route('/logout')
    def logout():
        session.clear()
        return jsonify({
            'message': 'Logged out successfully.',
            'status': 'success'
        }), 200

    # Admin routes
    @app.route('/admin/panel')
    def admin_panel():
        """Admin panel for automation service"""
        from app.blueprints.automation_utils import admin_required
        
        @admin_required
        def _admin_panel():
            # Get admin statistics
            from app.blueprints.automation_utils import get_firestore_client
            
            stats = {
                'total_users': 0,
                'total_articles': 0,
                'active_automations': 0,
                'system_health': 'Good'
            }
            
            db = get_firestore_client()
            if db:
                try:
                    # Count total users with published articles
                    users_query = db.collection('userPublishedArticles').get()
                    user_uids = set()
                    total_articles = 0
                    
                    for doc in users_query:
                        data = doc.to_dict()
                        user_uids.add(data.get('user_uid', ''))
                        total_articles += 1
                    
                    stats['total_users'] = len(user_uids)
                    stats['total_articles'] = total_articles
                    
                except Exception as e:
                    logger.error(f"Error fetching admin stats: {e}")
            
            return jsonify({
                'message': 'Admin Panel - Automation Service',
                'stats': stats,
                'service': 'automation',
                'admin_user': session.get('firebase_user_email')
            })
        
        return _admin_panel()

    @app.route('/admin/quota-management')
    def admin_quota_management():
        """Admin quota management for automation service"""
        from app.blueprints.automation_utils import admin_required
        
        @admin_required
        def _quota_management():
            return jsonify({
                'message': 'Quota Management - Automation Service',
                'quotas': {
                    'daily_article_limit': 50,
                    'monthly_user_limit': 1000,
                    'api_requests_per_hour': 10000
                },
                'service': 'automation',
                'admin_user': session.get('firebase_user_email')
            })
        
        return _quota_management()

    @app.route('/api/firebase-config', methods=['GET'])
    def firebase_config_api():
        """Return Firebase client configuration for frontend"""
        return jsonify(Config.get_firebase_client_config())

    @app.route('/api/notifications', methods=['GET'])
    def api_notifications():
        """Notifications API endpoint (stub for automation service)"""
        # Return empty notifications for automation service
        return jsonify({
            'notifications': [],
            'unread_count': 0,
            'status': 'success'
        })

    @app.route('/api/publishing-history', methods=['GET'])
    def api_publishing_history():
        """Publishing history API endpoint - returns all articles (published, draft, scheduled, future)"""
        if 'firebase_user_uid' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_uid = session['firebase_user_uid']
        
        # Import utilities for fetching publishing history
        from app.blueprints.automation_utils import get_firestore_client
        
        try:
            db = get_firestore_client()
            if not db:
                return jsonify({'articles': [], 'total_count': 0})
            
            # Get ALL articles for this user (published, draft, scheduled, etc.)
            from google.cloud.firestore_v1.base_query import FieldFilter
            articles_query = db.collection('userPublishedArticles')\
                .where(filter=FieldFilter('user_uid', '==', user_uid))
            
            articles = []
            for doc in articles_query.stream():
                article_data = doc.to_dict()
                articles.append({
                    'id': doc.id,
                    'title': article_data.get('title', ''),
                    'article_type': article_data.get('article_type', ''),
                    'status': article_data.get('status', 'draft'),
                    'site': article_data.get('site', ''),
                    'published_at': article_data.get('published_at', ''),
                    'created_at': article_data.get('created_at', ''),
                    'word_count': article_data.get('word_count', 0),
                    'profile_name': article_data.get('profile_name', ''),
                    'ticker': article_data.get('ticker', ''),
                    'content_type': article_data.get('content_type', ''),
                    'author': article_data.get('author', ''),
                    'category': article_data.get('category', ''),
                    'post_url': article_data.get('post_url', '')
                })
            
            # Sort in Python by published_at or created_at (fallback)
            def sort_key(article):
                pub_date = article.get('published_at') or article.get('created_at') or ''
                return pub_date
            
            articles_sorted = sorted(articles, key=sort_key, reverse=True)
            
            # Calculate stats by status for all article types
            published_count = len([a for a in articles if a.get('status') == 'published'])
            draft_count = len([a for a in articles if a.get('status') == 'draft'])
            scheduled_count = len([a for a in articles if a.get('status') == 'scheduled'])
            future_count = len([a for a in articles if a.get('status') == 'future'])
            total_articles = len(articles)
            
            return jsonify({
                'articles': articles_sorted,
                'total_count': total_articles,
                'published_count': published_count,
                'draft_count': draft_count,
                'scheduled_count': scheduled_count,
                'future_count': future_count,
                'status': 'success'
            })
            
        except Exception as e:
            logger.error(f"Error fetching publishing history for user {user_uid}: {e}", exc_info=True)
            return jsonify({'articles': [], 'total_count': 0, 'error': str(e)}), 500
    
    @app.route('/run-sports-automation', methods=['POST'])
    @login_required
    def run_sports_automation():
        """Run sports article publishing to WordPress sites"""
        user_uid = session['firebase_user_uid']
        db = get_firestore_client()
        
        app.logger.info(f"Sports automation endpoint hit by user {user_uid}")

        # Get selected profile IDs
        profile_ids_to_run = request.form.getlist('run_profile_ids[]')
        app.logger.info(f"Profile IDs from form: {profile_ids_to_run}")
        
        if not profile_ids_to_run:
            session['notification_message'] = "No profiles selected to run sports automation."
            session['notification_type'] = "info"
            return redirect(url_for('automation.sports_automation.run'))

        # Get selected articles from form
        selected_articles_json = request.form.get('selected_articles', '[]')
        app.logger.info(f"Received selected_articles JSON: {selected_articles_json}")
        
        try:
            selected_articles = json.loads(selected_articles_json)
            app.logger.info(f"Parsed {len(selected_articles)} selected articles")
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON decode error for selected_articles: {e}")
            selected_articles = []
        
        if not selected_articles:
            app.logger.warning(f"No articles selected - received: {selected_articles_json}")
            session['notification_message'] = "Please select at least one article to publish."
            session['notification_type'] = "warning"
            return redirect(url_for('automation.sports_automation.run'))

        try:
            # Import the actual sports automation runner
            import sys
            from pathlib import Path
            
            # Add Sports Article Automation to path
            automation_root = Path(__file__).resolve().parent.parent / "Sports_Article_Automation"
            if str(automation_root) not in sys.path:
                sys.path.insert(0, str(automation_root))
            
            # Import and run sports automation using the same system as main_portal_app
            from Sports_Article_Automation.api.sports_articles_loader import get_sports_loader
            from Sports_Article_Automation.utilities.perplexity_ai_client import PerplexityResearchCollector
            from Sports_Article_Automation.utilities.sports_article_generator import SportsArticleGenerator
            from Sports_Article_Automation.core.article_generation_pipeline import ArticleGenerationPipeline
            
            # Initialize result tracking
            total_published = 0
            failed_articles = []
            
            # Get profile data from Firestore
            selected_profiles_data_for_run = []
            for profile_id in profile_ids_to_run:
                try:
                    profile_doc = db.collection('userSiteProfiles').document(user_uid).collection('profiles').document(profile_id).get()
                    if profile_doc.exists:
                        profile_data = profile_doc.to_dict()
                        profile_data['profile_id'] = profile_id
                        selected_profiles_data_for_run.append(profile_data)
                    else:
                        app.logger.warning(f"Profile {profile_id} not found")
                except Exception as e:
                    app.logger.error(f"Error fetching profile {profile_id}: {e}")
            
            if not selected_profiles_data_for_run:
                session['notification_message'] = "Failed to load profile data."
                session['notification_type'] = "danger"
                return redirect(url_for('automation.sports_automation.run'))
            
            # Load state for writer rotation tracking
            from Sports_Article_Automation.state_management.firestore_state_manager import firestore_state_manager
            profile_ids = [p.get('profile_id') for p in selected_profiles_data_for_run]
            state = firestore_state_manager.load_state_from_firestore(user_uid, profile_ids)
            
            # Ensure last_author_index_by_profile exists in state
            if 'last_author_index_by_profile' not in state:
                state['last_author_index_by_profile'] = {}
            for pid in profile_ids:
                if pid not in state['last_author_index_by_profile']:
                    state['last_author_index_by_profile'][pid] = -1  # Start from beginning
            
            app.logger.info(f"[SPORTS_WRITER_ROTATION] Loaded state for user {user_uid}: last_author_index_by_profile = {state.get('last_author_index_by_profile', {})}")
            
            # Initialize SocketIO instance
            socketio = current_app.extensions.get('socketio')
            if not socketio:
                # Fallback if socketio not found
                app.logger.warning("SocketIO instance not found in app extensions")
                from flask_socketio import SocketIO
                socketio = SocketIO()
            
            # Process each article and profile combination
            for article_idx, article in enumerate(selected_articles, 1):
                article_id = article.get('id')
                article_title = article.get('title', 'Untitled Article')
                article_category = article.get('category', 'General')
                article_url = article.get('url', '')
                
                # Step 1: Generate full AI article using Perplexity + Gemini
                try:
                    socketio.emit('sports_automation_update', {
                        'stage': 'generation',
                        'message': f'[{article_idx}/{len(selected_articles)}] 🤖 Generating AI article: {article_title[:60]}...',
                        'level': 'info'
                    }, room=user_uid)
                    
                    # Import AI generation classes (lazy loading)
                    try:
                        from Sports_Article_Automation.utilities.sports_article_generator import SportsArticleGenerator
                        from Sports_Article_Automation.utilities.perplexity_ai_client import PerplexityResearchCollector
                        from Sports_Article_Automation.core.article_generation_pipeline import ArticleGenerationPipeline
                    except ImportError as e:
                        app.logger.error(f"AI generation modules not available: {e}")
                        socketio.emit('sports_automation_update', {
                            'stage': 'generation',
                            'message': f'[{article_title[:40]}] ✗ AI modules not available',
                            'level': 'error'
                        }, room=user_uid)
                        failed_articles.append(f"{article_title} (AI modules missing)")
                        continue
                    
                    # Initialize AI generation pipeline
                    perplexity_client = PerplexityResearchCollector()
                    gemini_client = SportsArticleGenerator()
                    
                    # Initialize pipeline
                    pipeline = ArticleGenerationPipeline(
                        perplexity_client=perplexity_client,
                        gemini_client=gemini_client
                    )
                    
                    # Create article entry format expected by pipeline
                    article_entry = {
                        'title': article_title,
                        'url': article_url,
                        'source_name': article.get('source', 'Sports News'),
                        'category': article_category,
                        'published_date': article.get('published_date', datetime.now().strftime('%Y-%m-%d')),
                        'importance_score': article.get('importance_score', 5)
                    }
                    
                    # Generate article
                    app.logger.info(f"Generating article for: {article_title}")
                    generated_article = pipeline.generate_article_for_headline(article_entry)
                    
                    if not generated_article or generated_article.get('status') not in ['success', 'placeholder']:
                        error_msg = generated_article.get('error', 'AI generation failed') if generated_article else 'No response from AI'
                        app.logger.error(f"{error_msg} for: {article_title}")
                        socketio.emit('sports_automation_update', {
                            'stage': 'generation',
                            'message': f'[{article_title[:40]}] ✗ {error_msg}',
                            'level': 'error'
                        }, room=user_uid)
                        failed_articles.append(f"{article_title} (AI generation failed)")
                        continue
                    
                    # Get generated content and headline
                    article_content = generated_article.get('article_content', '')
                    generated_headline = generated_article.get('headline', article_title)  # Use Gemini headline
                    word_count = len(article_content.split())
                    
                    # Log headline change
                    if generated_headline != article_title:
                        app.logger.info(f"Headline rewritten: '{article_title}' -> '{generated_headline}'")
                        
                    socketio.emit('sports_automation_update', {
                        'stage': 'generation',
                        'message': f'[{article_title[:40]}] ✅ AI generated ({word_count} words)',
                        'level': 'success'
                    }, room=user_uid)
                    
                except Exception as e:
                    error_msg = str(e)
                    app.logger.error(f"AI generation error for {article_title}: {error_msg}")
                    socketio.emit('sports_automation_update', {
                        'stage': 'generation',
                        'message': f'[{article_title[:40]}] ✗ AI Error: {error_msg}',
                        'level': 'error'
                    }, room=user_uid)
                    failed_articles.append(f"{article_title} (AI error: {error_msg})")
                    continue

                # Step 2: Publish to each selected profile
                for profile_data in selected_profiles_data_for_run:
                    profile_id = profile_data.get('profile_id')
                    profile_name = profile_data.get('profile_name', 'Unknown Site')
                    
                    try:
                        socketio.emit('sports_automation_update', {
                            'stage': 'publishing',
                            'message': f'[{article_idx}/{len(selected_articles)}] 📝 Publishing "{article_title[:40]}" to {profile_name}...',
                            'level': 'info'
                        }, room=user_uid)
                        
                        # Get site configuration
                        site_url = profile_data.get('site_url', '').rstrip('/')
                        username = profile_data.get('username', '')
                        password = profile_data.get('password', '')
                        
                        # Get category ID
                        cat_id = profile_data.get('sports_category_id', 1)  # Default to sports category
                        
                        # Get author rotation
                        authors = profile_data.get('authors', [{'name': 'Admin', 'display_name': 'Admin'}])
                        if not authors:
                            authors = [{'name': 'Admin', 'display_name': 'Admin'}]
                        
                        # Rotate author
                        current_author_index = state['last_author_index_by_profile'].get(profile_id, -1)
                        next_author_index = (current_author_index + 1) % len(authors)
                        author = authors[next_author_index]
                        writer_name = author.get('display_name', author.get('name', 'Unknown'))
                        
                        # Update state
                        state['last_author_index_by_profile'][profile_id] = next_author_index
                        
                        app.logger.info(f"[SPORTS_PUBLISHING] Publishing '{generated_headline}' by {writer_name} to {profile_name}")
                        
                        # Import WordPress publishing function
                        from automation_scripts import auto_publisher
                        
                        # Create WordPress post
                        post_id = auto_publisher.create_wordpress_post(
                            site_url=site_url,
                            author=author,
                            title=generated_headline,
                            content=article_content,
                            sched_time=None,  # Immediate publish
                            cat_id=cat_id,
                            media_id=None,
                            ticker=None,
                            company_name=article_category,
                            status='publish',
                            profile_config=profile_data
                        )
                        
                        if post_id:
                            total_published += 1
                            
                            socketio.emit('sports_automation_update', {
                                'stage': 'publishing',
                                'message': f'[{article_title[:40]}] ✅ Published by {writer_name} ({word_count} words)',
                                'level': 'success'
                            }, room=user_uid)
                            
                            # Log successful publication
                            app.logger.info(f"Successfully published '{article_title}' on {profile_name} by {writer_name}")
                            
                            # Save article metadata to Firestore
                            try:
                                published_article_data = {
                                    'user_uid': user_uid,
                                    'title': generated_headline,
                                    'content': article_content[:500],  # First 500 chars
                                    'word_count': word_count,
                                    'status': 'published',
                                    'published_at': datetime.now().isoformat(),
                                    'created_at': datetime.now().isoformat(),
                                    'site': profile_name,
                                    'profile_name': profile_name,
                                    'profile_id': profile_id,
                                    'author': writer_name,
                                    'category': article_category,
                                    'article_type': 'sports',
                                    'post_url': f"{site_url}/wp-admin/post.php?post={post_id}&action=edit",
                                    'post_id': str(post_id)
                                }
                                
                                db.collection('userPublishedArticles').add(published_article_data)
                                app.logger.info(f"Saved sports article metadata to Firestore for {article_title}")
                                
                            except Exception as e:
                                app.logger.error(f"Error saving article metadata: {e}")
                        else:
                            failed_articles.append(f"{article_title} on {profile_name} (WordPress error)")
                            socketio.emit('sports_automation_update', {
                                'stage': 'publishing',
                                'message': f'[{article_title[:40]}] ✗ Failed to publish on {profile_name}',
                                'level': 'error'
                            }, room=user_uid)
                            
                    except Exception as e:
                        error_msg = str(e)
                        app.logger.error(f"Publishing error for {article_title} on {profile_name}: {error_msg}")
                        failed_articles.append(f"{article_title} on {profile_name} ({error_msg})")
                        socketio.emit('sports_automation_update', {
                            'stage': 'publishing',
                            'message': f'[{article_title[:40]}] ✗ Error on {profile_name}: {error_msg}',
                            'level': 'error'
                        }, room=user_uid)

            # Summary
            socketio.emit('sports_automation_update', {
                'stage': 'publishing',
                'message': f'🎉 Complete! Published {total_published} article(s)',
                'level': 'success'
            }, room=user_uid)

            # Save final state to Firestore
            app.logger.info(f"[SPORTS_WRITER_ROTATION] Final state save - last_author_index_by_profile: {state.get('last_author_index_by_profile', {})}")
            firestore_state_manager.save_state_to_firestore(user_uid, state)

            if failed_articles:
                session['notification_message'] = f"Completed with {len(failed_articles)} failures: {', '.join(failed_articles[:2])}"
                session['notification_type'] = "warning"
            else:
                session['notification_message'] = f"Successfully published {total_published} sports articles"
                session['notification_type'] = "success"
            
            return jsonify({'success': True, 'message': 'Sports automation completed'}), 200
            
        except Exception as e:
            app.logger.error(f"Error in sports automation: {e}")
            session['notification_message'] = f"Sports automation error: {str(e)}"
            session['notification_type'] = "danger"
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/refresh-sports-articles', methods=['POST'])
    @login_required
    def refresh_sports_articles():
        """Refresh sports articles from automation folder and sync to Firebase"""
        user_uid = session['firebase_user_uid']
        
        try:
            from Sports_Article_Automation.api.sports_articles_loader import get_sports_loader
            
            sports_loader = get_sports_loader()
            
            # Force reload from disk
            articles = sports_loader.load_articles(force_refresh=True)
            
            app.logger.info(f"Refreshed {len(articles)} sports articles for user {user_uid}")
            
            return jsonify({
                'success': True, 
                'message': f'Successfully refreshed {len(articles)} sports articles',
                'count': len(articles)
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error refreshing sports articles: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for monitoring"""
        return jsonify({
            'status': 'healthy',
            'service': 'automation',
            'version': '2.0',
            'timestamp': datetime.now().isoformat()
        }), 200

    # Main Automation Dashboard Route
    @app.route('/')
    def index():
        """Root redirect to automation overview. No auth required for redirect."""
        try:
            return redirect(url_for('automation.overview'))
        except Exception:
            # Fallback to a known safe path (not '/' to avoid infinite loop)
            return redirect('/automation/overview')

    return app

def create_automation_socketio(app):
    socket_config = Config.get_socketio_config(app)
    socketio = SocketIO(app, **socket_config)
    
    # Register Socket Handlers
    # Using the new socket handlers we created in Phase 2
    from app.sockets.auto_sockets import register_automation_sockets
    register_automation_sockets(socketio)
    
    return socketio

if __name__ == '__main__':
    app = create_automation_app()
    socketio = create_automation_socketio(app)
    socketio.run(app, port=5002, debug=True)
