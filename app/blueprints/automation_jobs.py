"""
Government Jobs Article Automation Blueprint
=============================================

This blueprint handles government jobs, exam results, and admit card automation:
- Dashboard
- Run Automation
- Publishing History

Routes:
-------
/automation/jobs/dashboard - Jobs automation dashboard
/automation/jobs/run - Run jobs automation
/api/automation/jobs/dashboard-stats - Dashboard statistics API
/api/automation/jobs/fetch-items - Fetch items by type API
"""

from flask import Blueprint, render_template, redirect, url_for, session, current_app, request, jsonify
import requests

# Create jobs automation blueprint
jobs_automation_bp = Blueprint('jobs_automation', __name__, url_prefix='/jobs')

# Import dependencies from shared utils module
from app.blueprints.automation_utils import (
    login_required,
    get_user_site_profiles_from_firestore,
    get_automation_shared_context
)


@jobs_automation_bp.route('/dashboard')
@login_required
def dashboard():
    """Government jobs automation dashboard - shows overview and stats."""
    user_uid = session['firebase_user_uid']
    
    # Get user site profiles
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    
    # Get shared context for automation
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    return render_template('automation/jobs/dashboard.html',
                         title="Government Jobs Dashboard - Tickzen",
                         user_site_profiles=user_site_profiles,
                         **shared_context)


@jobs_automation_bp.route('/run')
@login_required
def run():
    """Run government jobs automation."""
    user_uid = session['firebase_user_uid']
    
    # Get user site profiles
    user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
    
    # Get shared context for automation
    shared_context = get_automation_shared_context(user_uid, user_site_profiles)
    
    # Initialize empty lists for items
    jobs_items = []
    results_items = []
    admit_cards_items = []
    
    # Try to load data from Job Portal API/Database
    try:
        from Job_Portal_Automation.job_automation_helpers import JobAutomationManager
        from Job_Portal_Automation.job_config import Config
        
        config = Config()
        manager = JobAutomationManager(config)
        
        # Fetch jobs data
        try:
            jobs_response = manager.fetch_jobs_list(page=1, limit=100)
            current_app.logger.info(f"Jobs response type: {type(jobs_response)}, data: {jobs_response}")
            if isinstance(jobs_response, dict):
                if jobs_response.get('success'):
                    jobs_items = jobs_response.get('data', [])
                    current_app.logger.info(f"Loaded {len(jobs_items)} jobs items")
                    
                    # If API returns empty data but shows total count, check if we need sample data
                    if len(jobs_items) == 0 and jobs_response.get('pagination', {}).get('total', 0) > 0:
                        current_app.logger.warning("API returned empty data despite having items. External API may be down. Using sample data.")
                        # Continue to sample data fallback below
                else:
                    # Try alternate response formats
                    if 'items' in jobs_response:
                        jobs_items = jobs_response.get('items', [])
                    elif isinstance(jobs_response.get('data'), list):
                        jobs_items = jobs_response.get('data', [])
                    current_app.logger.info(f"Loaded {len(jobs_items)} jobs items (alternate format)")
            elif isinstance(jobs_response, list):
                jobs_items = jobs_response
                current_app.logger.info(f"Loaded {len(jobs_items)} jobs items (direct list)")
        except Exception as e:
            current_app.logger.warning(f"Could not fetch jobs: {e}")
        
        # Fetch results data
        try:
            results_response = manager.fetch_results_list(page=1, limit=100)
            current_app.logger.info(f"Results response type: {type(results_response)}, keys: {results_response.keys() if isinstance(results_response, dict) else 'N/A'}")
            if isinstance(results_response, dict):
                if results_response.get('success'):
                    results_items = results_response.get('data', [])
                    current_app.logger.info(f"Loaded {len(results_items)} results items")
                else:
                    # Try alternate response formats
                    if 'items' in results_response:
                        results_items = results_response.get('items', [])
                    elif isinstance(results_response.get('data'), list):
                        results_items = results_response.get('data', [])
                    current_app.logger.info(f"Loaded {len(results_items)} results items (alternate format)")
            elif isinstance(results_response, list):
                results_items = results_response
                current_app.logger.info(f"Loaded {len(results_items)} results items (direct list)")
        except Exception as e:
            current_app.logger.warning(f"Could not fetch results: {e}")
        
        # Fetch admit cards data
        try:
            admit_cards_response = manager.fetch_admit_cards_list(page=1, limit=100)
            current_app.logger.info(f"Admit cards response type: {type(admit_cards_response)}, keys: {admit_cards_response.keys() if isinstance(admit_cards_response, dict) else 'N/A'}")
            if isinstance(admit_cards_response, dict):
                if admit_cards_response.get('success'):
                    admit_cards_items = admit_cards_response.get('data', [])
                    current_app.logger.info(f"Loaded {len(admit_cards_items)} admit cards items")
                else:
                    # Try alternate response formats
                    if 'items' in admit_cards_response:
                        admit_cards_items = admit_cards_response.get('items', [])
                    elif isinstance(admit_cards_response.get('data'), list):
                        admit_cards_items = admit_cards_response.get('data', [])
                    current_app.logger.info(f"Loaded {len(admit_cards_items)} admit cards items (alternate format)")
            elif isinstance(admit_cards_response, list):
                admit_cards_items = admit_cards_response
                current_app.logger.info(f"Loaded {len(admit_cards_items)} admit cards items (direct list)")
        except Exception as e:
            current_app.logger.warning(f"Could not fetch admit cards: {e}")
            
    except Exception as e:
        current_app.logger.error(f"Error loading job portal data: {e}")
    
    # If no items loaded (API issue), use sample data for testing
    if len(jobs_items) == 0 and len(results_items) == 0 and len(admit_cards_items) == 0:
        current_app.logger.warning("No data from API - using sample data for UI testing")
        from datetime import datetime
        
        # Sample jobs
        jobs_items = [
            {
                'id': 'job_sample_1',
                'job_id': 'job_sample_1',
                'title': 'Railway Recruitment Board - Junior Engineer Positions',
                'description': 'RRB is recruiting for Junior Engineer positions across all zones. Application deadline: 31st January 2026.',
                'posted_date': '2026-01-10',
                'published_date': '2026-01-10',
                'source': 'RRB Official',
                'priority': 'high'
            },
            {
                'id': 'job_sample_2',
                'job_id': 'job_sample_2',
                'title': 'UPSC Civil Services Examination 2026',
                'description': 'Union Public Service Commission announces Civil Services Examination. Registration opens February 2026.',
                'posted_date': '2026-01-12',
                'published_date': '2026-01-12',
                'source': 'UPSC Official',
                'priority': 'critical'
            },
            {
                'id': 'job_sample_3',
                'job_id': 'job_sample_3',
                'title': 'State Bank of India - Clerk Recruitment',
                'description': 'SBI is recruiting for Clerk positions across India. 5000+ vacancies announced.',
                'posted_date': '2026-01-14',
                'published_date': '2026-01-14',
                'source': 'SBI Careers',
                'priority': 'high'
            }
        ]
        
        # Sample results
        results_items = [
            {
                'id': 'result_sample_1',
                'result_id': 'result_sample_1',
                'title': 'SSC CGL 2025 Tier-I Results Declared',
                'description': 'Staff Selection Commission has declared CGL Tier-I examination results. Check your roll number now.',
                'announced_date': '2026-01-13',
                'published_date': '2026-01-13',
                'source': 'SSC Official',
                'priority': 'critical'
            },
            {
                'id': 'result_sample_2',
                'result_id': 'result_sample_2',
                'title': 'IBPS PO Prelims Result 2026',
                'description': 'Institute of Banking Personnel Selection announces PO prelims results. Mains exam scheduled for March.',
                'announced_date': '2026-01-11',
                'published_date': '2026-01-11',
                'source': 'IBPS Official',
                'priority': 'high'
            }
        ]
        
        # Sample admit cards
        admit_cards_items = [
            {
                'id': 'admit_sample_1',
                'admit_id': 'admit_sample_1',
                'title': 'NEET 2026 Admit Card Released',
                'description': 'National Eligibility cum Entrance Test admit cards are now available for download. Exam date: 5th May 2026.',
                'released_date': '2026-01-15',
                'published_date': '2026-01-15',
                'source': 'NTA Official',
                'priority': 'critical'
            },
            {
                'id': 'admit_sample_2',
                'admit_id': 'admit_sample_2',
                'title': 'JEE Main 2026 Session 1 Admit Card',
                'description': 'Joint Entrance Examination Main Session 1 admit cards available. Download from official website.',
                'released_date': '2026-01-14',
                'published_date': '2026-01-14',
                'source': 'NTA Official',
                'priority': 'critical'
            }
        ]
    
    current_app.logger.info(f"Final counts - Jobs: {len(jobs_items)}, Results: {len(results_items)}, Admit Cards: {len(admit_cards_items)}")
    
    return render_template('automation/jobs/run.html',
                         title="Government Jobs Automation - Tickzen",
                         user_site_profiles=user_site_profiles,
                         jobs_items=jobs_items,
                         results_items=results_items,
                         admit_cards_items=admit_cards_items,
                         **shared_context)


@jobs_automation_bp.route('/history')
@login_required
def history():
    """Redirect to global publishing history."""
    return redirect(url_for('automation.history', type='government_jobs'))


# ============= API ENDPOINTS =============

@jobs_automation_bp.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    """Get dashboard statistics from job automation runs."""
    user_uid = session['firebase_user_uid']
    
    try:
        from Job_Portal_Automation.state_management.job_publishing_state_manager import JobPublishingStateManager
        from datetime import datetime, timedelta
        
        # Initialize state manager to get stats
        state_manager = JobPublishingStateManager()
        
        # Get run history - this fetches from job_automation_runs collection
        run_history = state_manager.get_run_history(user_uid, limit=100)
        
        # Initialize stats
        stats = {
            'total_runs': len(run_history),
            'published_count': 0,
            'this_week_count': 0,
            'jobs_count': 0,
            'results_count': 0,
            'admit_cards_count': 0,
            'recent_runs': []
        }
        
        # Process run history to calculate statistics
        if run_history:
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            
            for run in run_history:
                # Get run data
                timestamp_str = run.get('timestamp') or run.get('created_at', '')
                content_type = run.get('content_type', 'jobs')
                results = run.get('results', [])
                
                # Count by content type from run
                if content_type == 'jobs':
                    stats['jobs_count'] += len(results)
                elif content_type == 'results':
                    stats['results_count'] += len(results)
                elif content_type == 'admit_cards':
                    stats['admit_cards_count'] += len(results)
                
                # Total published articles in this run
                stats['published_count'] += len(results)
                
                # Count this week
                try:
                    if timestamp_str:
                        run_date = datetime.fromisoformat(str(timestamp_str).replace('Z', '+00:00'))
                        # Handle timezone-naive datetime
                        if run_date.tzinfo is None:
                            run_date = run_date.replace(tzinfo=None)
                            week_check = week_ago.replace(tzinfo=None)
                        else:
                            week_check = week_ago
                        
                        if run_date >= week_check:
                            stats['this_week_count'] += len(results)
                except Exception as e:
                    current_app.logger.debug(f"Error parsing timestamp: {e}")
                
                # Build recent runs list (limit to 10 most recent)
                if len(stats['recent_runs']) < 10:
                    recent_run = {
                        'id': run.get('run_id', 'unknown'),
                        'item_count': len(results),
                        'status': run.get('status', 'completed'),
                        'created_at': run.get('timestamp') or run.get('created_at'),
                        'content_type': content_type
                    }
                    stats['recent_runs'].append(recent_run)
            
            current_app.logger.info(f"Dashboard stats for user {user_uid}: {stats['total_runs']} runs, {stats['published_count']} published articles")
        
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to load statistics',
            'total_runs': 0,
            'published_count': 0,
            'this_week_count': 0,
            'jobs_count': 0,
            'results_count': 0,
            'admit_cards_count': 0,
            'recent_runs': []
        }), 500


@jobs_automation_bp.route('/api/refresh-data', methods=['POST'])
@login_required
def refresh_data():
    """
    Trigger data refresh from external job crawler API
    """
    try:
        import traceback
        # External API endpoint
        api_url = 'https://job-crawler-api-0885.onrender.com/api/refresh/now'
        
        current_app.logger.info(f"Triggering data refresh from external API: {api_url}")
        
        # Call external API to trigger refresh
        response = requests.post(api_url, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            current_app.logger.info(f"Refresh triggered successfully: {result}")
            return jsonify({
                'success': True,
                'message': 'Data refresh triggered successfully',
                'data': result
            })
        else:
            current_app.logger.error(f"Refresh failed with status {response.status_code}: {response.text}")
            return jsonify({
                'success': False,
                'message': f'API returned status {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.Timeout:
        current_app.logger.error("Refresh request timed out")
        return jsonify({
            'success': False,
            'message': 'Request timed out. Refresh may still be processing in background.'
        }), 504
    except Exception as e:
        current_app.logger.error(f"Error triggering refresh: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@jobs_automation_bp.route('/api/fetch-items', methods=['GET'])
@login_required
def api_fetch_items():
    """Fetch items by content type from Job API."""
    content_type = request.args.get('type', 'jobs')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', None)
    
    try:
        from Job_Portal_Automation.job_automation_helpers import JobAutomationManager
        from Job_Portal_Automation.job_config import Config
        
        # Initialize manager
        config = Config()
        manager = JobAutomationManager(config)
        
        # Fetch based on content type
        if content_type == 'jobs':
            response = manager.fetch_jobs_list(page=page, limit=limit, search=search)
        elif content_type == 'results':
            response = manager.fetch_results_list(page=page, limit=limit, search=search)
        elif content_type == 'admit_cards':
            response = manager.fetch_admit_cards_list(page=page, limit=limit, search=search)
        else:
            return jsonify({'error': 'Invalid content type'}), 400
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching {content_type}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'pagination': {}
        }), 500


@jobs_automation_bp.route('/api/start-automation', methods=['POST'])
@login_required
def api_start_automation():
    """Start a government jobs automation run."""
    user_uid = session['firebase_user_uid']
    
    try:
        data = request.get_json()
        
        # Validate request
        selected_items = data.get('selected_items', [])
        content_type = data.get('content_type', 'jobs')
        target_profiles = data.get('target_profiles', [])
        article_length = data.get('article_length', 'medium')
        
        if not selected_items:
            return jsonify({'success': False, 'error': 'No items selected'}), 400
        
        if not target_profiles:
            return jsonify({'success': False, 'error': 'No WordPress profiles selected'}), 400
        
        from Job_Portal_Automation.job_automation_helpers import JobAutomationManager
        from Job_Portal_Automation.job_config import Config
        
        # Initialize manager
        config = Config()
        manager = JobAutomationManager(config)
        
        # Fetch user's WordPress profiles from Firestore
        user_site_profiles = get_user_site_profiles_from_firestore(user_uid)
        
        if not user_site_profiles:
            return jsonify({'success': False, 'error': 'No WordPress profiles configured. Please add a WordPress site first.'}), 400
        
        # Process profile configurations
        processed_profiles = []
        profile_ids = []
        
        for profile_config in target_profiles:
            profile_id = profile_config.get('profile_id')
            
            # Find the profile in Firestore data
            profile_data = None
            for profile in user_site_profiles:
                if profile.get('profile_id') == profile_id:
                    profile_data = profile.copy()
                    break
            
            if not profile_data:
                current_app.logger.warning(f"Profile {profile_id} not found in Firestore")
                continue
            
            # Add configuration to profile
            profile_data['category_id'] = profile_config.get('category_id')
            profile_data['publish_status'] = profile_config.get('publish_status', 'draft')
            profile_data['min_interval'] = profile_config.get('min_interval')
            profile_data['max_interval'] = profile_config.get('max_interval')
            
            processed_profiles.append(profile_data)
            profile_ids.append(profile_id)
        
        if not processed_profiles:
            return jsonify({'success': False, 'error': 'No valid WordPress profiles found. Please check your profile selection.'}), 400
        
        # Prepare automation config with full profile data
        automation_config = {
            'article_length': article_length,
            'profiles': processed_profiles  # Full profile data in config
        }
        
        # Initiate automation run (pass profile IDs for validation, full profiles in config)
        success, run_id, message = manager.initiate_automation_run(
            user_uid=user_uid,
            content_type=content_type,
            selected_items=selected_items,
            target_profiles=profile_ids,  # Just IDs for validation
            config=automation_config  # Full profiles in config
        )
        
        if success:
            # Start background processing
            from Job_Portal_Automation.job_automation_processor import JobAutomationProcessor
            from Job_Portal_Automation.state_management.job_publishing_state_manager import JobPublishingStateManager
            
            state_manager = JobPublishingStateManager()
            processor = JobAutomationProcessor(manager, state_manager)
            processor.start_run(run_id, blocking=False)
            
            return jsonify({
                'success': True,
                'run_id': run_id,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error starting automation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@jobs_automation_bp.route('/api/run-status/<run_id>', methods=['GET'])
@login_required
def api_run_status(run_id):
    """Get status of a government jobs automation run."""
    user_uid = session['firebase_user_uid']
    
    try:
        from Job_Portal_Automation.state_management.job_publishing_state_manager import JobPublishingStateManager
        
        # Initialize state manager
        state_manager = JobPublishingStateManager()
        
        # Get run status
        run = state_manager.get_run(run_id)
        
        if not run:
            return jsonify({
                'success': False,
                'error': f'Run {run_id} not found'
            }), 404
        
        # Verify user owns this run
        if run.get('user_uid') != user_uid:
            return jsonify({
                'success': False,
                'error': 'Unauthorized'
            }), 403
        
        return jsonify({
            'success': True,
            'run_id': run_id,
            'status': run.get('status'),
            'progress': run.get('progress', {}),
            'results': run.get('results', []),
            'errors': run.get('errors', []),
            'timestamp': run.get('timestamp'),
            'completed_at': run.get('completed_at')
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting run status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get run status',
            'status': 'unknown'
        }), 500
