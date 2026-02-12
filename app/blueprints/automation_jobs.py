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
import json
import time
from datetime import datetime
from pathlib import Path

# Create jobs automation blueprint
jobs_automation_bp = Blueprint('jobs_automation', __name__, url_prefix='/jobs')

# Import dependencies from shared utils module
from app.blueprints.automation_utils import (
    login_required,
    get_user_site_profiles_from_firestore,
    get_automation_shared_context
)

# Data directory for caching API responses
DATA_CACHE_DIR = Path(__file__).parent.parent.parent / 'Job_Portal_Automation' / 'data_cache'
DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def save_api_data_to_json(jobs=None, results=None, admit_cards=None):
    """Save API response data to JSON files for caching."""
    timestamp = datetime.now().isoformat()
    
    if jobs is not None:
        jobs_cache = {
            'timestamp': timestamp,
            'success': True,
            'count': len(jobs),
            'data': jobs
        }
        with open(DATA_CACHE_DIR / 'jobs_cache.json', 'w', encoding='utf-8') as f:
            json.dump(jobs_cache, f, indent=2, ensure_ascii=False)
        current_app.logger.info(f"Saved {len(jobs)} jobs to cache")
    
    if results is not None:
        results_cache = {
            'timestamp': timestamp,
            'success': True,
            'count': len(results),
            'data': results
        }
        with open(DATA_CACHE_DIR / 'results_cache.json', 'w', encoding='utf-8') as f:
            json.dump(results_cache, f, indent=2, ensure_ascii=False)
        current_app.logger.info(f"Saved {len(results)} results to cache")
    
    if admit_cards is not None:
        admit_cards_cache = {
            'timestamp': timestamp,
            'success': True,
            'count': len(admit_cards),
            'data': admit_cards
        }
        with open(DATA_CACHE_DIR / 'admit_cards_cache.json', 'w', encoding='utf-8') as f:
            json.dump(admit_cards_cache, f, indent=2, ensure_ascii=False)
        current_app.logger.info(f"Saved {len(admit_cards)} admit cards to cache")

def load_cached_data():
    """Load data from JSON cache files."""
    jobs_items = []
    results_items = []
    admit_cards_items = []
    
    # Load jobs
    jobs_cache_file = DATA_CACHE_DIR / 'jobs_cache.json'
    if jobs_cache_file.exists():
        try:
            with open(jobs_cache_file, 'r', encoding='utf-8') as f:
                jobs_cache = json.load(f)
                jobs_items = jobs_cache.get('data', [])
                current_app.logger.info(f"Loaded {len(jobs_items)} jobs from cache (updated: {jobs_cache.get('timestamp', 'unknown')})")
        except Exception as e:
            current_app.logger.warning(f"Failed to load jobs cache: {e}")
    
    # Load results
    results_cache_file = DATA_CACHE_DIR / 'results_cache.json'
    if results_cache_file.exists():
        try:
            with open(results_cache_file, 'r', encoding='utf-8') as f:
                results_cache = json.load(f)
                results_items = results_cache.get('data', [])
                current_app.logger.info(f"Loaded {len(results_items)} results from cache (updated: {results_cache.get('timestamp', 'unknown')})")
        except Exception as e:
            current_app.logger.warning(f"Failed to load results cache: {e}")
    
    # Load admit cards
    admit_cards_cache_file = DATA_CACHE_DIR / 'admit_cards_cache.json'
    if admit_cards_cache_file.exists():
        try:
            with open(admit_cards_cache_file, 'r', encoding='utf-8') as f:
                admit_cards_cache = json.load(f)
                admit_cards_items = admit_cards_cache.get('data', [])
                current_app.logger.info(f"Loaded {len(admit_cards_items)} admit cards from cache (updated: {admit_cards_cache.get('timestamp', 'unknown')})")
        except Exception as e:
            current_app.logger.warning(f"Failed to load admit cards cache: {e}")
    
    return jobs_items, results_items, admit_cards_items


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
    
    # Try to load data from JSON cache first (unlimited data)
    jobs_items, results_items, admit_cards_items = load_cached_data()
    data_source = 'cache' if (jobs_items or results_items or admit_cards_items) else 'api'
    
    # If no cached data exists, try to load from Job Portal API/Database (limited)
    if not jobs_items and not results_items and not admit_cards_items:
        data_source = 'api'
        current_app.logger.info("No cached data found, attempting to load from API (limited)")
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
                        current_app.logger.info(f"Loaded {len(jobs_items)} jobs items from API")
                        
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
                        current_app.logger.info(f"Loaded {len(results_items)} results items from API")
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
                        current_app.logger.info(f"Loaded {len(admit_cards_items)} admit cards items from API")
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
    else:
        current_app.logger.info(f"Loaded data from cache: {len(jobs_items)} jobs, {len(results_items)} results, {len(admit_cards_items)} admit cards")
    
    # If no items loaded (API issue), use sample data for testing
    if len(jobs_items) == 0 and len(results_items) == 0 and len(admit_cards_items) == 0:
        data_source = 'sample'
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
    
    # Combine all items into a single list sorted by collection order (most recent first)
    from datetime import datetime
    
    all_items = []
    
    # Add jobs with content type metadata
    for item in jobs_items:
        item_copy = dict(item)
        item_copy['content_type'] = 'jobs'
        item_copy['content_label'] = 'JOBS'
        item_copy['sort_date'] = item.get('posted_date') or item.get('published_date') or '2000-01-01'
        all_items.append(item_copy)
    
    # Add results with content type metadata
    for item in results_items:
        item_copy = dict(item)
        item_copy['content_type'] = 'results'
        item_copy['content_label'] = 'RESULTS'
        item_copy['sort_date'] = item.get('announced_date') or item.get('published_date') or '2000-01-01'
        all_items.append(item_copy)
    
    # Add admit cards with content type metadata
    for item in admit_cards_items:
        item_copy = dict(item)
        item_copy['content_type'] = 'admit_cards'
        item_copy['content_label'] = 'ADMIT CARDS'
        item_copy['sort_date'] = item.get('released_date') or item.get('published_date') or '2000-01-01'
        all_items.append(item_copy)
    
    # Sort all items by new status first, then by date (new articles at top)
    try:
        all_items.sort(key=lambda x: (
            not x.get('is_new', False),  # New articles first (False sorts before True)
            -datetime.strptime(x['sort_date'][:10], '%Y-%m-%d').timestamp()  # Then by date (recent first)
        ))
    except ValueError:
        # If date parsing fails, sort by new status only
        all_items.sort(key=lambda x: not x.get('is_new', False))
        current_app.logger.warning("Date parsing failed for sorting, sorting by new status only")
    
    current_app.logger.info(f"Final counts - Jobs: {len(jobs_items)}, Results: {len(results_items)}, Admit Cards: {len(admit_cards_items)}, Total combined: {len(all_items)}, Data source: {data_source}")
    
    return render_template('automation/jobs/run.html',
                         title="Government Jobs Automation - Tickzen",
                         user_site_profiles=user_site_profiles,
                         jobs_items=jobs_items,
                         results_items=results_items,
                         admit_cards_items=admit_cards_items,
                         all_items=all_items,
                         data_source=data_source,
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
    Trigger data refresh from external job crawler API and fetch unlimited data with new article detection
    """
    try:
        import traceback
        from Job_Portal_Automation.job_automation_helpers import JobAutomationManager
        from Job_Portal_Automation.job_config import Config
        
        # Get previous article IDs for comparison (optimized approach)
        # Only load cached data to extract existing IDs - we will REPLACE the cache completely
        previous_jobs, previous_results, previous_admits = load_cached_data()
        
        # Create sets of existing IDs for efficient lookup (to detect new articles)
        existing_job_ids = set()
        existing_result_ids = set()
        existing_admit_ids = set()
        
        if previous_jobs:
            existing_job_ids = {item.get('id') for item in previous_jobs if item.get('id')}
        if previous_results:
            existing_result_ids = {item.get('id') for item in previous_results if item.get('id')}
        if previous_admits:
            existing_admit_ids = {item.get('id') for item in previous_admits if item.get('id')}
        
        current_app.logger.info(f"Previous article counts from cache - Jobs: {len(previous_jobs)}, Results: {len(previous_results)}, Admits: {len(previous_admits)}")
        current_app.logger.info(f"Previous article IDs extracted - Job IDs: {len(existing_job_ids)}, Result IDs: {len(existing_result_ids)}, Admit IDs: {len(existing_admit_ids)}")
        
        # External API endpoint
        api_url = 'https://job-crawler-api-0885.onrender.com/api/refresh/now'
        
        current_app.logger.info(f"Triggering data refresh from external API: {api_url}")
        
        # Call external API to trigger refresh
        response = requests.post(api_url, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            current_app.logger.info(f"Refresh triggered successfully: {result}")
            
            # Wait for the crawler to complete (check status endpoint)
            status_url = 'https://job-crawler-api-0885.onrender.com/api/refresh/status'
            max_wait_time = 60  # Maximum 60 seconds
            check_interval = 3  # Check every 3 seconds
            elapsed_time = 0
            
            current_app.logger.info("Waiting for crawler to complete...")
            
            while elapsed_time < max_wait_time:
                try:
                    status_response = requests.get(status_url, timeout=10)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        current_app.logger.info(f"Crawler status: {status_data.get('status')}")
                        
                        # Check if crawler is done
                        if status_data.get('status') in ['completed', 'idle', 'ready']:
                            current_app.logger.info(f"Crawler completed after {elapsed_time} seconds")
                            # Log detailed crawler stats from external API
                            external_items_found = status_data.get('items_found', 'unknown')
                            external_message = status_data.get('message', 'No message')
                            external_last_refresh = status_data.get('last_refresh', 'unknown')
                            current_app.logger.info(f"External crawler report: {external_message} (items: {external_items_found}, last refresh: {external_last_refresh})")
                            break
                        elif status_data.get('status') == 'error':
                            current_app.logger.warning(f"Crawler encountered an error: {status_data}")
                            break
                    
                    time.sleep(check_interval)
                    elapsed_time += check_interval
                    
                except Exception as e:
                    current_app.logger.warning(f"Error checking crawler status: {e}")
                    break
            
            if elapsed_time >= max_wait_time:
                current_app.logger.warning(f"Crawler did not complete within {max_wait_time} seconds. Proceeding with data fetch...")
            
            # Now fetch unlimited data and save to JSON cache
            current_app.logger.info("Fetching unlimited data after refresh...")
            
            config = Config()
            manager = JobAutomationManager(config)
            
            # Initialize lists for all data
            all_jobs = []
            all_results = []
            all_admit_cards = []
            
            # Fetch all jobs (multiple pages, no limit)
            page = 1
            while True:
                try:
                    jobs_response = manager.fetch_jobs_list(page=page, limit=100)
                    if isinstance(jobs_response, dict) and jobs_response.get('success'):
                        page_jobs = jobs_response.get('data', [])
                        if not page_jobs:
                            break
                        all_jobs.extend(page_jobs)
                        current_app.logger.info(f"Fetched page {page}: {len(page_jobs)} jobs (total: {len(all_jobs)})")
                        page += 1
                        if len(page_jobs) < 100:  # Last page
                            break
                    else:
                        break
                except Exception as e:
                    current_app.logger.warning(f"Error fetching jobs page {page}: {e}")
                    break
            
            # Detect duplicates and new articles in jobs
            # Group by URL to find duplicates, and check IDs against previous cache to find new items
            seen_urls = {}
            new_jobs = []
            duplicate_jobs = []
            jobs_with_ids = 0
            jobs_without_ids = 0
            
            for item in all_jobs:
                item_id = item.get('id')
                item_url = item.get('url', '')
                
                # Check for duplicates by URL
                if item_url in seen_urls:
                    item['is_duplicate'] = True
                    item['is_new'] = False
                    duplicate_jobs.append(item)
                else:
                    seen_urls[item_url] = True
                    item['is_duplicate'] = False
                    
                    # Check if it's a new article (not in previous cache)
                    if item_id:
                        jobs_with_ids += 1
                        if item_id not in existing_job_ids:
                            item['is_new'] = True
                            new_jobs.append(item)
                        else:
                            item['is_new'] = False
                    else:
                        jobs_without_ids += 1
                        item['is_new'] = False
            
            current_app.logger.info(f"Jobs: {len(all_jobs)} total, {jobs_with_ids} with IDs, {jobs_without_ids} without IDs, {len(new_jobs)} new, {len(duplicate_jobs)} duplicates")
            
            # Fetch all results (multiple pages, no limit)
            page = 1
            while True:
                try:
                    results_response = manager.fetch_results_list(page=page, limit=100)
                    if isinstance(results_response, dict) and results_response.get('success'):
                        page_results = results_response.get('data', [])
                        if not page_results:
                            break
                        all_results.extend(page_results)
                        current_app.logger.info(f"Fetched page {page}: {len(page_results)} results (total: {len(all_results)})")
                        page += 1
                        if len(page_results) < 100:  # Last page
                            break
                    else:
                        break
                except Exception as e:
                    current_app.logger.warning(f"Error fetching results page {page}: {e}")
                    break
            
            # Detect duplicates and new articles in results
            seen_urls = {}
            new_results = []
            duplicate_results = []
            results_with_ids = 0
            results_without_ids = 0
            
            for item in all_results:
                item_id = item.get('id')
                item_url = item.get('url', '')
                
                # Check for duplicates by URL
                if item_url in seen_urls:
                    item['is_duplicate'] = True
                    item['is_new'] = False
                    duplicate_results.append(item)
                else:
                    seen_urls[item_url] = True
                    item['is_duplicate'] = False
                    
                    # Check if it's a new article (not in previous cache)
                    if item_id:
                        results_with_ids += 1
                        if item_id not in existing_result_ids:
                            item['is_new'] = True
                            new_results.append(item)
                        else:
                            item['is_new'] = False
                    else:
                        results_without_ids += 1
                        item['is_new'] = False
            
            current_app.logger.info(f"Results: {len(all_results)} total, {results_with_ids} with IDs, {results_without_ids} without IDs, {len(new_results)} new, {len(duplicate_results)} duplicates")
            
            # Fetch all admit cards (multiple pages, no limit)
            page = 1
            while True:
                try:
                    admit_cards_response = manager.fetch_admit_cards_list(page=page, limit=100)
                    if isinstance(admit_cards_response, dict) and admit_cards_response.get('success'):
                        page_admit_cards = admit_cards_response.get('data', [])
                        if not page_admit_cards:
                            break
                        all_admit_cards.extend(page_admit_cards)
                        current_app.logger.info(f"Fetched page {page}: {len(page_admit_cards)} admit cards (total: {len(all_admit_cards)})")
                        page += 1
                        if len(page_admit_cards) < 100:  # Last page
                            break
                    else:
                        break
                except Exception as e:
                    current_app.logger.warning(f"Error fetching admit cards page {page}: {e}")
                    break
            
            # Detect duplicates and new articles in admit cards
            seen_urls = {}
            new_admits = []
            duplicate_admits = []
            admits_with_ids = 0
            admits_without_ids = 0
            
            for item in all_admit_cards:
                item_id = item.get('id')
                item_url = item.get('url', '')
                
                # Check for duplicates by URL
                if item_url in seen_urls:
                    item['is_duplicate'] = True
                    item['is_new'] = False
                    duplicate_admits.append(item)
                else:
                    seen_urls[item_url] = True
                    item['is_duplicate'] = False
                    
                    # Check if it's a new article (not in previous cache)
                    if item_id:
                        admits_with_ids += 1
                        if item_id not in existing_admit_ids:
                            item['is_new'] = True
                            new_admits.append(item)
                        else:
                            item['is_new'] = False
                    else:
                        admits_without_ids += 1
                        item['is_new'] = False
            
            current_app.logger.info(f"Admit cards: {len(all_admit_cards)} total, {admits_with_ids} with IDs, {admits_without_ids} without IDs, {len(new_admits)} new, {len(duplicate_admits)} duplicates")
            
            # COMPLETELY REPLACE the JSON cache files with fresh data from API
            # The local JSON files are only for backup/cache purposes
            current_app.logger.info("Completely replacing local JSON cache with fresh API data...")
            save_api_data_to_json(
                jobs=all_jobs,
                results=all_results, 
                admit_cards=all_admit_cards
            )
            
            # Calculate statistics
            total_new = len(new_jobs) + len(new_results) + len(new_admits)
            total_duplicates = len(duplicate_jobs) + len(duplicate_results) + len(duplicate_admits)
            
            current_app.logger.info(f"✅ JSON cache completely replaced with fresh data!")
            current_app.logger.info(f"Data refresh completed: {len(all_jobs)} jobs, {len(all_results)} results, {len(all_admit_cards)} admit cards")
            current_app.logger.info(f"New articles: {total_new}, Duplicates detected: {total_duplicates}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully refreshed and cached data. Found {total_new} new articles!',
                'data': {
                    'refresh_result': result,
                    'cached_stats': {
                        'jobs': len(all_jobs),
                        'results': len(all_results),
                        'admit_cards': len(all_admit_cards),
                        'total': len(all_jobs) + len(all_results) + len(all_admit_cards),
                        'new_jobs': len(new_jobs),
                        'new_results': len(new_results),
                        'new_admits': len(new_admits),
                        'total_new': total_new,
                        'duplicate_jobs': len(duplicate_jobs),
                        'duplicate_results': len(duplicate_results),
                        'duplicate_admits': len(duplicate_admits),
                        'total_duplicates': total_duplicates
                    }
                }
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
