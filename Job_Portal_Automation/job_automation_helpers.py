"""
Job Automation Helpers Module
==============================

Centralized business logic for job automation operations.
Handles fetching, validation, and orchestration of automation runs.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

from Job_Portal_Automation.api.job_api_client import JobAPIClient, APIError, ContentType
from Job_Portal_Automation.api.perplexity_client import PerplexityResearchCollector
from Job_Portal_Automation.state_management.job_publishing_state_manager import JobPublishingStateManager, RunStatus
from Job_Portal_Automation.job_config import Config

logger = logging.getLogger(__name__)


class JobAutomationManager:
    """
    Central manager for all job automation operations.
    
    Responsibilities:
    - Fetching jobs, results, admit cards from API
    - Validating user selections
    - Initiating automation runs
    - Managing state and progress
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize automation manager
        
        Args:
            config: Configuration object (uses default if not provided)
        """
        self.config = config or Config()
        self.api_client = JobAPIClient(
            timeout=self.config.JOB_API_TIMEOUT,
            max_retries=self.config.JOB_API_MAX_RETRIES
        )
        self.research_client = PerplexityResearchCollector(
            api_key=self.config.PERPLEXITY_API_KEY
        )
        self.state_manager = JobPublishingStateManager(
            use_firestore=self.config.USE_FIRESTORE
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    # ===================== LISTING OPERATIONS =====================
    
    def fetch_jobs_list(self, page: int = 1, limit: int = 50,
                       portal: Optional[str] = None,
                       search: Optional[str] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch list of jobs from API
        
        Args:
            page: Page number
            limit: Items per page
            portal: Filter by portal
            search: Search keyword
            date_from: Filter from date
            date_to: Filter to date
            
        Returns:
            Dictionary with paginated results and metadata
        """
        try:
            self.logger.info(f"Fetching jobs - page {page}, limit {limit}")
            
            # Use search if provided
            if search:
                response = self.api_client.search_jobs(search, page, limit)
            # Use filter if dates provided
            elif date_from or date_to:
                response = self.api_client.filter_jobs(
                    date_from=date_from,
                    date_to=date_to,
                    portal=portal,
                    page=page,
                    limit=limit
                )
            # Default: get jobs
            else:
                response = self.api_client.get_jobs(page, limit, portal)
            
            # Extract and structure response
            # API returns 'items' not 'data'
            data = response.get('items', response.get('data', []))
            
            return {
                'success': True,
                'data': data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': response.get('total', len(data)),
                    'total_pages': response.get('total_pages', 1)
                }
            }
            
        except APIError as e:
            self.logger.error(f"Failed to fetch jobs: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'pagination': {}
            }
    
    def fetch_results_list(self, page: int = 1, limit: int = 50,
                          portal: Optional[str] = None,
                          search: Optional[str] = None,
                          date_from: Optional[str] = None,
                          date_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch list of exam results from API
        
        Args:
            page: Page number
            limit: Items per page
            portal: Filter by portal
            search: Search keyword
            date_from: Filter from date
            date_to: Filter to date
            
        Returns:
            Dictionary with paginated results and metadata
        """
        try:
            self.logger.info(f"Fetching results - page {page}, limit {limit}")
            
            if search:
                response = self.api_client.search_results(search, page, limit)
            elif date_from or date_to:
                response = self.api_client.filter_results(
                    date_from=date_from,
                    date_to=date_to,
                    portal=portal,
                    page=page,
                    limit=limit
                )
            else:
                response = self.api_client.get_results(page, limit, portal)
            
            # API returns 'items' not 'data'
            data = response.get('items', response.get('data', []))
            
            return {
                'success': True,
                'data': data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': response.get('total', len(data)),
                    'total_pages': response.get('total_pages', 1)
                }
            }
            
        except APIError as e:
            self.logger.error(f"Failed to fetch results: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'pagination': {}
            }
    
    def fetch_admit_cards_list(self, page: int = 1, limit: int = 50,
                              portal: Optional[str] = None,
                              search: Optional[str] = None,
                              date_from: Optional[str] = None,
                              date_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch list of admit cards from API
        
        Args:
            page: Page number
            limit: Items per page
            portal: Filter by portal
            search: Search keyword
            date_from: Filter from date
            date_to: Filter to date
            
        Returns:
            Dictionary with paginated results and metadata
        """
        try:
            self.logger.info(f"Fetching admit cards - page {page}, limit {limit}")
            
            if search:
                response = self.api_client.search_admit_cards(search, page, limit)
            elif date_from or date_to:
                response = self.api_client.filter_admit_cards(
                    date_from=date_from,
                    date_to=date_to,
                    portal=portal,
                    page=page,
                    limit=limit
                )
            else:
                response = self.api_client.get_admit_cards(page, limit, portal)
            
            # API returns 'items' not 'data'
            data = response.get('items', response.get('data', []))
            
            return {
                'success': True,
                'data': data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': response.get('total', len(data)),
                    'total_pages': response.get('total_pages', 1)
                }
            }
            
        except APIError as e:
            self.logger.error(f"Failed to fetch admit cards: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'pagination': {}
            }
    
    # ===================== DETAIL OPERATIONS =====================
    
    def fetch_item_details(self, url: str,
                          content_type: str = "auto") -> Dict[str, Any]:
        """
        Fetch detailed information for a specific item
        
        Args:
            url: URL to fetch details from
            content_type: Type of content (job, result, admit_card, auto)
            
        Returns:
            Dictionary with detailed information
        """
        try:
            self.logger.info(f"Fetching details for {content_type} from {url}")
            
            # Validate content type
            if content_type not in ["job", "result", "admit_card", "auto"]:
                return {
                    'success': False,
                    'error': f"Invalid content type: {content_type}",
                    'details': {}
                }
            
            # Validate URL
            if not url or not isinstance(url, str) or not url.startswith('http'):
                return {
                    'success': False,
                    'error': "Invalid URL provided",
                    'details': {}
                }
            
            # Fetch details
            detailed_info = self.api_client.fetch_details_post(
                url=url,
                content_type=content_type,
                timeout=self.config.JOB_API_TIMEOUT
            )
            
            return {
                'success': True,
                'url': url,
                'content_type': detailed_info.content_type,
                'details': {
                    'full_description': detailed_info.full_description,
                    'important_dates': detailed_info.important_dates,
                    'eligibility': detailed_info.eligibility,
                    'application_fee': detailed_info.application_fee,
                    'how_to_apply': detailed_info.how_to_apply,
                    'important_links': detailed_info.important_links,
                    'key_details': detailed_info.key_details,
                    'tables': detailed_info.tables
                }
            }
            
        except APIError as e:
            self.logger.error(f"Failed to fetch item details: {e}")
            return {
                'success': False,
                'error': str(e),
                'details': {}
            }
    
    # ===================== VALIDATION OPERATIONS =====================
    
    def validate_selected_items(self, items: List[Dict[str, Any]],
                               content_type: str) -> Tuple[bool, List[str]]:
        """
        Validate selected items
        
        Args:
            items: List of selected items
            content_type: Type of content (jobs, results, admit_cards)
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Validate content type
        if content_type not in ["jobs", "results", "admit_cards"]:
            errors.append(f"Invalid content type: {content_type}")
            return False, errors
        
        # Check items list
        if not items or not isinstance(items, list):
            errors.append("No items selected")
            return False, errors
        
        if len(items) > 100:
            errors.append("Too many items selected (max 100)")
            return False, errors
        
        # Validate each item
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"Item {idx + 1}: Invalid format")
                continue
            
            # Check required fields
            if 'id' not in item:
                errors.append(f"Item {idx + 1}: Missing ID")
            if 'title' not in item:
                errors.append(f"Item {idx + 1}: Missing title")
            if 'url' not in item:
                errors.append(f"Item {idx + 1}: Missing URL")
            
            # Validate URL
            if 'url' in item:
                url = item['url']
                if not isinstance(url, str) or not url.startswith('http'):
                    errors.append(f"Item {idx + 1}: Invalid URL")
        
        return len(errors) == 0, errors
    
    def validate_target_profiles(self, profiles: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate target WordPress profiles
        
        Args:
            profiles: List of profile names/IDs
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check profiles list
        if not profiles or not isinstance(profiles, list):
            errors.append("No target profiles selected")
            return False, errors
        
        if len(profiles) > 10:
            errors.append("Too many profiles (max 10)")
            return False, errors
        
        # Validate each profile
        for idx, profile in enumerate(profiles):
            if not isinstance(profile, str) or not profile.strip():
                errors.append(f"Profile {idx + 1}: Invalid format")
        
        return len(errors) == 0, errors
    
    def validate_automation_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate automation configuration
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if not isinstance(config, dict):
            errors.append("Invalid configuration format")
            return False, errors
        
        # Validate article length
        if 'article_length' in config:
            length = config['article_length']
            if length not in ['short', 'medium', 'long']:
                errors.append("Invalid article length (use short, medium, or long)")
        
        # Validate publish status
        if 'publish_status' in config:
            status = config['publish_status']
            if status not in ['draft', 'publish']:
                errors.append("Invalid publish status (use draft or publish)")
        
        # Validate boolean flags
        for flag in ['include_seo', 'include_links']:
            if flag in config:
                if not isinstance(config[flag], bool):
                    errors.append(f"{flag} must be boolean")
        
        return len(errors) == 0, errors
    
    # ===================== AUTOMATION OPERATIONS =====================
    
    def initiate_automation_run(self, user_uid: str, content_type: str,
                              selected_items: List[Dict[str, Any]],
                              target_profiles: List[str],
                              config: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, str]:
        """
        Initiate a new automation run
        
        Args:
            user_uid: Firebase user ID
            content_type: Type of content (jobs, results, admit_cards)
            selected_items: List of items to process
            target_profiles: List of target WordPress profiles
            config: Optional configuration dictionary
            
        Returns:
            Tuple of (success, run_id, message)
        """
        try:
            # Validate all inputs
            valid_items, item_errors = self.validate_selected_items(selected_items, content_type)
            if not valid_items:
                error_msg = "; ".join(item_errors)
                self.logger.warning(f"Invalid items: {error_msg}")
                return False, "", f"Invalid items: {error_msg}"
            
            valid_profiles, profile_errors = self.validate_target_profiles(target_profiles)
            if not valid_profiles:
                error_msg = "; ".join(profile_errors)
                self.logger.warning(f"Invalid profiles: {error_msg}")
                return False, "", f"Invalid profiles: {error_msg}"
            
            if config:
                valid_config, config_errors = self.validate_automation_config(config)
                if not valid_config:
                    error_msg = "; ".join(config_errors)
                    self.logger.warning(f"Invalid config: {error_msg}")
                    return False, "", f"Invalid config: {error_msg}"
            else:
                config = {}
            
            # Create automation run in state manager
            run_id = self.state_manager.create_run(
                user_uid=user_uid,
                content_type=content_type,
                selected_items=selected_items,
                target_profiles=target_profiles,
                config=config
            )
            
            self.logger.info(f"Initiated automation run {run_id} for user {user_uid}")
            
            return True, run_id, f"Automation run {run_id} created successfully"
            
        except Exception as e:
            self.logger.error(f"Failed to initiate automation: {e}")
            return False, "", f"Failed to initiate automation: {str(e)}"
    
    # ===================== STATE OPERATIONS =====================
    
    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get the current status of a run
        
        Args:
            run_id: Run ID
            
        Returns:
            Dictionary with run status and progress
        """
        try:
            run = self.state_manager.get_run(run_id)
            
            if not run:
                return {
                    'success': False,
                    'error': f"Run {run_id} not found"
                }
            
            return {
                'success': True,
                'run_id': run_id,
                'status': run.get('status'),
                'progress': run.get('progress'),
                'results': run.get('results', []),
                'errors': run.get('errors', []),
                'timestamp': run.get('timestamp'),
                'updated_at': run.get('updated_at')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get run status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_history(self, user_uid: str, limit: int = 50) -> Dict[str, Any]:
        """
        Get automation history for a user
        
        Args:
            user_uid: Firebase user ID
            limit: Max number of runs to return
            
        Returns:
            Dictionary with run history
        """
        try:
            runs = self.state_manager.get_run_history(user_uid, limit)
            
            return {
                'success': True,
                'runs': runs,
                'total': len(runs)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get user history: {e}")
            return {
                'success': False,
                'error': str(e),
                'runs': [],
                'total': 0
            }
    
    def get_user_statistics(self, user_uid: str) -> Dict[str, Any]:
        """
        Get automation statistics for a user
        
        Args:
            user_uid: Firebase user ID
            
        Returns:
            Dictionary with statistics
        """
        try:
            stats = self.state_manager.get_statistics(user_uid)
            
            return {
                'success': True,
                'statistics': stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                'success': False,
                'error': str(e),
                'statistics': {}
            }
    
    # ===================== CLEANUP =====================
    
    def close(self):
        """Close all client connections"""
        try:
            self.api_client.close()
            self.logger.info("JobAutomationManager closed")
        except Exception as e:
            self.logger.warning(f"Error closing automation manager: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
