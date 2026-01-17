"""
Job Portal Automation API Client
=================================

Comprehensive client for Job Crawler API with error handling,
retry logic, caching, and response models.

API Base URL: https://job-crawler-api-0885.onrender.com
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import time
from enum import Enum
from urllib.parse import urljoin
import json

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Supported content types"""
    JOB = "job"
    RESULT = "result"
    ADMIT_CARD = "admit_card"
    AUTO = "auto"


class APIError(Exception):
    """Base API error"""
    pass


class APIConnectionError(APIError):
    """Connection/network error"""
    pass


class APIResponseError(APIError):
    """Invalid API response"""
    pass


class APITimeoutError(APIError):
    """API request timeout"""
    pass


class APIRateLimitError(APIError):
    """Rate limit exceeded"""
    pass


@dataclass
class JobItem:
    """Job listing model"""
    id: str
    title: str
    portal: str
    date_posted: str
    url: str
    description: Optional[str] = None
    status: str = "active"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ResultItem:
    """Exam result listing model"""
    id: str
    title: str
    portal: str
    date_posted: str
    url: str
    description: Optional[str] = None
    status: str = "active"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AdmitCardItem:
    """Admit card listing model"""
    id: str
    title: str
    portal: str
    date_posted: str
    url: str
    description: Optional[str] = None
    status: str = "active"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DetailedInfo:
    """Detailed information from URL crawling"""
    url: str
    content_type: str
    full_description: str
    important_dates: Dict[str, Any] = field(default_factory=dict)
    eligibility: Optional[str] = None
    application_fee: Optional[str] = None
    how_to_apply: Optional[str] = None
    important_links: List[str] = field(default_factory=list)
    key_details: Dict[str, Any] = field(default_factory=dict)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)


class JobAPIClient:
    """
    Comprehensive Job Crawler API Client
    
    Handles all API endpoints with retry logic, caching, error handling,
    and response parsing.
    """
    
    BASE_URL = "https://job-crawler-api-0885.onrender.com"
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    RETRY_BACKOFF = 2  # exponential backoff multiplier
    REQUEST_TIMEOUT = 30
    
    def __init__(self, timeout: int = REQUEST_TIMEOUT, max_retries: int = MAX_RETRIES):
        """
        Initialize API client
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # For compatibility
        self.base_url = self.BASE_URL
        
    def _get(self, endpoint: str, params: Optional[Dict] = None, 
             with_retry: bool = True) -> Dict[str, Any]:
        """
        Perform GET request with retry logic
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            with_retry: Whether to retry on failure
            
        Returns:
            Parsed JSON response
            
        Raises:
            APIConnectionError: Network/connection error
            APITimeoutError: Request timeout
            APIResponseError: Invalid response
            APIRateLimitError: Rate limit exceeded
        """
        url = urljoin(self.BASE_URL, endpoint)
        
        for attempt in range(self.max_retries if with_retry else 1):
            try:
                self.logger.debug(f"GET {url} (attempt {attempt + 1})")
                
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    headers={"User-Agent": "TickzenJobAutomation/1.0"}
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self.logger.warning(f"Rate limited. Retry after {retry_after}s")
                    if attempt < self.max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    raise APIRateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
                
                # Handle server errors with retry
                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        delay = self.RETRY_DELAY * (self.RETRY_BACKOFF ** attempt)
                        self.logger.warning(f"Server error {response.status_code}. Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    raise APIResponseError(f"Server error {response.status_code}")
                
                # Handle client errors (no retry)
                if 400 <= response.status_code < 500:
                    raise APIResponseError(
                        f"Client error {response.status_code}: {response.text}"
                    )
                
                response.raise_for_status()
                
                try:
                    data = response.json()
                    self.logger.debug(f"Response status: {response.status_code}")
                    return data
                except json.JSONDecodeError as e:
                    raise APIResponseError(f"Invalid JSON response: {str(e)}")
                    
            except requests.Timeout as e:
                self.logger.error(f"Timeout on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.RETRY_DELAY * (self.RETRY_BACKOFF ** attempt)
                    time.sleep(delay)
                    continue
                raise APITimeoutError(f"Request timeout after {self.max_retries} attempts")
            
            except requests.ConnectionError as e:
                self.logger.error(f"Connection error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.RETRY_DELAY * (self.RETRY_BACKOFF ** attempt)
                    time.sleep(delay)
                    continue
                raise APIConnectionError(f"Connection error after {self.max_retries} attempts")
        
        raise APIConnectionError("Max retries exceeded")
    
    def _post(self, endpoint: str, data: Dict[str, Any], 
              with_retry: bool = True) -> Dict[str, Any]:
        """
        Perform POST request with retry logic
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            with_retry: Whether to retry on failure
            
        Returns:
            Parsed JSON response
            
        Raises:
            APIConnectionError: Network/connection error
            APITimeoutError: Request timeout
            APIResponseError: Invalid response
        """
        url = urljoin(self.BASE_URL, endpoint)
        
        for attempt in range(self.max_retries if with_retry else 1):
            try:
                self.logger.debug(f"POST {url} (attempt {attempt + 1})")
                
                response = self.session.post(
                    url,
                    json=data,
                    timeout=self.timeout,
                    headers={"User-Agent": "TickzenJobAutomation/1.0"}
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < self.max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    raise APIRateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
                
                # Handle server errors with retry
                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        delay = self.RETRY_DELAY * (self.RETRY_BACKOFF ** attempt)
                        self.logger.warning(f"Server error {response.status_code}. Retrying...")
                        time.sleep(delay)
                        continue
                    raise APIResponseError(f"Server error {response.status_code}")
                
                # Handle client errors (no retry)
                if 400 <= response.status_code < 500:
                    raise APIResponseError(
                        f"Client error {response.status_code}: {response.text}"
                    )
                
                response.raise_for_status()
                
                try:
                    data = response.json()
                    return data
                except json.JSONDecodeError as e:
                    raise APIResponseError(f"Invalid JSON response: {str(e)}")
                    
            except requests.Timeout:
                if attempt < self.max_retries - 1:
                    delay = self.RETRY_DELAY * (self.RETRY_BACKOFF ** attempt)
                    time.sleep(delay)
                    continue
                raise APITimeoutError(f"Request timeout after {self.max_retries} attempts")
            
            except requests.ConnectionError:
                if attempt < self.max_retries - 1:
                    delay = self.RETRY_DELAY * (self.RETRY_BACKOFF ** attempt)
                    time.sleep(delay)
                    continue
                raise APIConnectionError(f"Connection error after {self.max_retries} attempts")
        
        raise APIConnectionError("Max retries exceeded")
    
    # ==================== Health & System ====================
    
    def check_health(self) -> bool:
        """
        Check API health status
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self._get("/health", with_retry=True)
            return response.get("status") == "healthy" or response.get("success") is True
        except APIError as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get detailed system status and info
        
        Returns:
            System status information
        """
        try:
            return self._get("/api/system/status")
        except APIError as e:
            self.logger.error(f"Failed to get system status: {str(e)}")
            raise
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics (total counts)
        
        Returns:
            Statistics dictionary
        """
        try:
            return self._get("/api/system/stats")
        except APIError as e:
            self.logger.error(f"Failed to get system stats: {str(e)}")
            raise
    
    def get_stats_by_portal(self) -> Dict[str, Any]:
        """
        Get statistics broken down by portal
        
        Returns:
            Stats by portal
        """
        try:
            return self._get("/api/system/stats/by-portal")
        except APIError as e:
            self.logger.error(f"Failed to get portal stats: {str(e)}")
            raise
    
    # ==================== Jobs ====================
    
    def get_jobs(self, page: int = 1, limit: int = 50, 
                 portal: Optional[str] = None, sort: Optional[str] = None) -> Dict[str, Any]:
        """
        List all jobs (paginated)
        
        Args:
            page: Page number (default: 1)
            limit: Items per page (default: 50, max: 100)
            portal: Filter by portal name (optional)
            sort: Sort order (default: None)
            
        Returns:
            Paginated job listings
        """
        params = {
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        if portal:
            params["portal"] = portal
        if sort:
            params["sort"] = sort
        
        try:
            return self._get("/api/jobs", params=params)
        except APIError as e:
            self.logger.error(f"Failed to fetch jobs: {str(e)}")
            raise
    
    def get_job_by_id(self, job_id: str) -> Dict[str, Any]:
        """
        Get single job by ID
        
        Args:
            job_id: Job ID
            
        Returns:
            Job details
        """
        try:
            return self._get(f"/api/jobs/{job_id}")
        except APIError as e:
            self.logger.error(f"Failed to fetch job {job_id}: {str(e)}")
            raise
    
    def search_jobs(self, search: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Search jobs by title, portal, date
        
        Args:
            search: Search keyword
            page: Page number
            limit: Items per page
            
        Returns:
            Search results
        """
        params = {
            "search": search,
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        
        try:
            return self._get("/api/jobs/search", params=params)
        except APIError as e:
            self.logger.error(f"Failed to search jobs: {str(e)}")
            raise
    
    def filter_jobs(self, date_from: Optional[str] = None, 
                   date_to: Optional[str] = None, 
                   portal: Optional[str] = None,
                   page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Filter jobs by date range or portal
        
        Args:
            date_from: Start date (YYYY-MM-DD format)
            date_to: End date (YYYY-MM-DD format)
            portal: Portal filter
            page: Page number
            limit: Items per page
            
        Returns:
            Filtered results
        """
        params = {
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if portal:
            params["portal"] = portal
        
        try:
            return self._get("/api/jobs/filter", params=params)
        except APIError as e:
            self.logger.error(f"Failed to filter jobs: {str(e)}")
            raise
    
    def filter_jobs_with_details(self, date_from: Optional[str] = None,
                                date_to: Optional[str] = None,
                                portal: Optional[str] = None,
                                page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Filter jobs with full details included
        
        Args:
            date_from: Start date (YYYY-MM-DD format)
            date_to: End date (YYYY-MM-DD format)
            portal: Portal filter
            page: Page number
            limit: Items per page
            
        Returns:
            Filtered results with details
        """
        params = {
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if portal:
            params["portal"] = portal
        
        try:
            return self._get("/api/jobs/filter/with-details", params=params)
        except APIError as e:
            self.logger.error(f"Failed to filter jobs with details: {str(e)}")
            raise
    
    # ==================== Results ====================
    
    def get_results(self, page: int = 1, limit: int = 50,
                   portal: Optional[str] = None, sort: Optional[str] = None) -> Dict[str, Any]:
        """
        List all exam results (paginated)
        
        Args:
            page: Page number
            limit: Items per page
            portal: Filter by portal
            sort: Sort order
            
        Returns:
            Paginated results
        """
        params = {
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        if portal:
            params["portal"] = portal
        if sort:
            params["sort"] = sort
        
        try:
            return self._get("/api/results", params=params)
        except APIError as e:
            self.logger.error(f"Failed to fetch results: {str(e)}")
            raise
    
    def get_result_by_id(self, result_id: str) -> Dict[str, Any]:
        """Get single result by ID"""
        try:
            return self._get(f"/api/results/{result_id}")
        except APIError as e:
            self.logger.error(f"Failed to fetch result {result_id}: {str(e)}")
            raise
    
    def search_results(self, search: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Search results by title, portal, date"""
        params = {
            "search": search,
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        
        try:
            return self._get("/api/results/search", params=params)
        except APIError as e:
            self.logger.error(f"Failed to search results: {str(e)}")
            raise
    
    def filter_results(self, date_from: Optional[str] = None,
                      date_to: Optional[str] = None,
                      portal: Optional[str] = None,
                      page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Filter results by date range or portal"""
        params = {
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if portal:
            params["portal"] = portal
        
        try:
            return self._get("/api/results/filter", params=params)
        except APIError as e:
            self.logger.error(f"Failed to filter results: {str(e)}")
            raise
    
    def filter_results_with_details(self, date_from: Optional[str] = None,
                                   date_to: Optional[str] = None,
                                   portal: Optional[str] = None,
                                   page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Filter results with full details included"""
        params = {
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if portal:
            params["portal"] = portal
        
        try:
            return self._get("/api/results/filter/with-details", params=params)
        except APIError as e:
            self.logger.error(f"Failed to filter results with details: {str(e)}")
            raise
    
    # ==================== Admit Cards ====================
    
    def get_admit_cards(self, page: int = 1, limit: int = 50,
                       portal: Optional[str] = None, sort: Optional[str] = None) -> Dict[str, Any]:
        """
        List all admit cards (paginated)
        
        Args:
            page: Page number
            limit: Items per page
            portal: Filter by portal
            sort: Sort order
            
        Returns:
            Paginated admit cards
        """
        params = {
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        if portal:
            params["portal"] = portal
        if sort:
            params["sort"] = sort
        
        try:
            return self._get("/api/admit-cards", params=params)
        except APIError as e:
            self.logger.error(f"Failed to fetch admit cards: {str(e)}")
            raise
    
    def get_admit_card_by_id(self, admit_card_id: str) -> Dict[str, Any]:
        """Get single admit card by ID"""
        try:
            return self._get(f"/api/admit-cards/{admit_card_id}")
        except APIError as e:
            self.logger.error(f"Failed to fetch admit card {admit_card_id}: {str(e)}")
            raise
    
    def search_admit_cards(self, search: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Search admit cards by title, portal, date"""
        params = {
            "search": search,
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        
        try:
            return self._get("/api/admit-cards/search", params=params)
        except APIError as e:
            self.logger.error(f"Failed to search admit cards: {str(e)}")
            raise
    
    def filter_admit_cards(self, date_from: Optional[str] = None,
                          date_to: Optional[str] = None,
                          portal: Optional[str] = None,
                          page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Filter admit cards by date range or portal"""
        params = {
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if portal:
            params["portal"] = portal
        
        try:
            return self._get("/api/admit-cards/filter", params=params)
        except APIError as e:
            self.logger.error(f"Failed to filter admit cards: {str(e)}")
            raise
    
    def filter_admit_cards_with_details(self, date_from: Optional[str] = None,
                                       date_to: Optional[str] = None,
                                       portal: Optional[str] = None,
                                       page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Filter admit cards with full details included"""
        params = {
            "page": max(1, page),
            "limit": min(limit, 100)
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if portal:
            params["portal"] = portal
        
        try:
            return self._get("/api/admit-cards/filter/with-details", params=params)
        except APIError as e:
            self.logger.error(f"Failed to filter admit cards with details: {str(e)}")
            raise
    
    # ==================== Detail Extraction ====================
    
    def fetch_details_get(self, url: str, content_type: str = "auto",
                         timeout: int = 30) -> DetailedInfo:
        """
        Fetch complete details from a URL (GET request)
        
        Args:
            url: Full URL to crawl
            content_type: "job", "result", "admit_card", or "auto"
            timeout: Request timeout in seconds
            
        Returns:
            DetailedInfo object with extracted information
        """
        params = {
            "url": url,
            "content_type": content_type,
            "timeout": timeout
        }
        
        try:
            response = self._get("/api/details/fetch", params=params)
            return self._parse_detail_response(response)
        except APIError as e:
            self.logger.error(f"Failed to fetch details from {url}: {str(e)}")
            raise
    
    def fetch_details_post(self, url: str, content_type: str = "auto",
                          timeout: int = 30) -> DetailedInfo:
        """
        Fetch complete details from a URL (POST request)
        
        Args:
            url: Full URL to crawl
            content_type: "job", "result", "admit_card", or "auto"
            timeout: Request timeout in seconds
            
        Returns:
            DetailedInfo object with extracted information
        """
        data = {
            "url": url,
            "content_type": content_type,
            "timeout": timeout
        }
        
        try:
            response = self._post("/api/details/fetch", data)
            return self._parse_detail_response(response)
        except APIError as e:
            self.logger.error(f"Failed to fetch details from {url}: {str(e)}")
            raise
    
    def fetch_batch_details(self, urls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fetch details from multiple URLs at once
        
        Args:
            urls: List of dicts with 'url' and optional 'content_type' keys
                  Example: [
                      {'url': 'https://...', 'content_type': 'job'},
                      {'url': 'https://...'}  # auto-detect
                  ]
        
        Returns:
            Response with details for each URL
        """
        data = {"urls": urls}
        
        try:
            return self._post("/api/details/batch", data)
        except APIError as e:
            self.logger.error(f"Failed to fetch batch details: {str(e)}")
            raise
    
    def _parse_detail_response(self, response: Dict[str, Any]) -> DetailedInfo:
        """
        Parse detail API response into DetailedInfo object
        
        Args:
            response: Raw API response
            
        Returns:
            DetailedInfo object
        """
        details_data = response.get("details", {})
        
        return DetailedInfo(
            url=response.get("url", ""),
            content_type=response.get("content_type", "unknown"),
            full_description=details_data.get("full_description", ""),
            important_dates=details_data.get("important_dates", {}),
            eligibility=details_data.get("eligibility"),
            application_fee=details_data.get("application_fee"),
            how_to_apply=details_data.get("how_to_apply"),
            important_links=details_data.get("important_links", []),
            key_details=details_data.get("key_details", {}),
            tables=details_data.get("tables", []),
            raw_response=response
        )
    
    # ==================== Data Refresh ====================
    
    def get_refresh_info(self) -> Dict[str, Any]:
        """Get last refresh time and next scheduled refresh"""
        try:
            return self._get("/api/refresh/info")
        except APIError as e:
            self.logger.error(f"Failed to get refresh info: {str(e)}")
            raise
    
    def trigger_refresh(self) -> Dict[str, Any]:
        """Trigger immediate data refresh"""
        try:
            return self._post("/api/refresh/now", {})
        except APIError as e:
            self.logger.error(f"Failed to trigger refresh: {str(e)}")
            raise
    
    def get_refresh_status(self) -> Dict[str, Any]:
        """Get current refresh status"""
        try:
            return self._get("/api/refresh/status")
        except APIError as e:
            self.logger.error(f"Failed to get refresh status: {str(e)}")
            raise
    
    def reset_refresh(self) -> Dict[str, Any]:
        """Reset refresh scheduler"""
        try:
            return self._post("/api/refresh/reset", {})
        except APIError as e:
            self.logger.error(f"Failed to reset refresh: {str(e)}")
            raise
    
    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()
            self.logger.info("API client session closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
