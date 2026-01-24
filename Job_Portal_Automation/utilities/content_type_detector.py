"""
Content Type Detector
=====================

Intelligent detection of content type (jobs/admit_cards/results) from multiple sources:
1. Database/cache file location
2. Title pattern matching
3. URL patterns
4. Content analysis

This ensures accurate content type determination for headline and feature image generation.
"""

import logging
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ContentTypeDetector:
    """
    Intelligent detector for content type based on multiple signals.
    
    Detection methods (in order of priority):
    1. Database file location (most reliable)
    2. Title keyword patterns
    3. URL patterns
    4. Content analysis
    """
    
    # Cache file paths
    CACHE_DIR = Path(__file__).parent.parent / "data_cache"
    JOBS_CACHE = CACHE_DIR / "jobs_cache.json"
    ADMIT_CARDS_CACHE = CACHE_DIR / "admit_cards_cache.json"
    RESULTS_CACHE = CACHE_DIR / "results_cache.json"
    
    # Title pattern keywords for each type
    JOBS_KEYWORDS = [
        r'\b(?:recruitment|vacancy|vacancies|posts?|hiring|application|apply)\b',
        r'\b(?:online\s+form|notification|bharti)\b',
        r'\b(?:SI|ASI|constable|clerk|officer|assistant|engineer)\b.*?(?:recruitment|posts?)',
    ]
    
    ADMIT_CARD_KEYWORDS = [
        r'\b(?:admit\s+card|hall\s+ticket|call\s+letter)\b',
        r'\b(?:exam\s+city|exam\s+date|download)\b.*?(?:admit|hall\s+ticket)',
        r'\b(?:PET|PST|written\s+exam).*?(?:admit|call\s+letter)\b',
    ]
    
    RESULT_KEYWORDS = [
        r'\b(?:result|merit\s+list|answer\s+key|cut\s+off|cutoff)\b',
        r'\b(?:marks|score|selected|qualifying|final\s+result)\b',
        r'\b(?:declared|announced|released).*?(?:result|merit)\b',
    ]
    
    def __init__(self):
        """Initialize content type detector."""
        self.cache_data = self._load_cache_files()
        logger.info("✅ Content Type Detector initialized")
        logger.info(f"   Loaded {len(self.cache_data['jobs'])} jobs")
        logger.info(f"   Loaded {len(self.cache_data['admit_cards'])} admit cards")
        logger.info(f"   Loaded {len(self.cache_data['results'])} results")
    
    def _load_cache_files(self) -> Dict[str, List[Dict]]:
        """Load all cache files into memory for fast lookup."""
        cache_data = {
            'jobs': [],
            'admit_cards': [],
            'results': []
        }
        
        # Load jobs cache
        if self.JOBS_CACHE.exists():
            try:
                with open(self.JOBS_CACHE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cache_data['jobs'] = data.get('data', [])
            except Exception as e:
                logger.warning(f"Failed to load jobs cache: {e}")
        
        # Load admit cards cache
        if self.ADMIT_CARDS_CACHE.exists():
            try:
                with open(self.ADMIT_CARDS_CACHE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cache_data['admit_cards'] = data.get('data', [])
            except Exception as e:
                logger.warning(f"Failed to load admit cards cache: {e}")
        
        # Load results cache
        if self.RESULTS_CACHE.exists():
            try:
                with open(self.RESULTS_CACHE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cache_data['results'] = data.get('data', [])
            except Exception as e:
                logger.warning(f"Failed to load results cache: {e}")
        
        return cache_data
    
    def detect_content_type(self, item: Dict[str, Any]) -> str:
        """
        Detect content type from item data using multiple signals.
        
        Args:
            item: Item dictionary with id, title, url, etc.
            
        Returns:
            Content type: 'jobs', 'admit_cards', or 'results'
        """
        item_id = item.get('id')
        title = item.get('title', '')
        url = item.get('url', '')
        
        logger.info(f"🔍 Detecting content type for: {title[:60]}...")
        
        # Method 1: Database lookup (most reliable)
        db_type = self._detect_from_database(item_id, title, url)
        if db_type:
            logger.info(f"   ✅ Detected from database: {db_type}")
            return db_type
        
        # Method 2: Title pattern matching
        title_type = self._detect_from_title(title)
        if title_type:
            logger.info(f"   ✅ Detected from title patterns: {title_type}")
            return title_type
        
        # Method 3: URL pattern matching
        url_type = self._detect_from_url(url)
        if url_type:
            logger.info(f"   ✅ Detected from URL: {url_type}")
            return url_type
        
        # Fallback: default to jobs
        logger.warning(f"   ⚠️  Could not detect type, defaulting to: jobs")
        return 'jobs'
    
    def _detect_from_database(self, item_id: str, title: str, url: str) -> Optional[str]:
        """
        Detect content type by checking which database contains the item.
        
        Args:
            item_id: Item ID
            title: Item title
            url: Item URL
            
        Returns:
            Content type if found in database, None otherwise
        """
        if not item_id:
            return None
        
        # Check jobs cache
        for job in self.cache_data['jobs']:
            if (job.get('id') == item_id or 
                job.get('title') == title or 
                job.get('url') == url):
                return 'jobs'
        
        # Check admit cards cache
        for card in self.cache_data['admit_cards']:
            if (card.get('id') == item_id or 
                card.get('title') == title or 
                card.get('url') == url):
                return 'admit_cards'
        
        # Check results cache
        for result in self.cache_data['results']:
            if (result.get('id') == item_id or 
                result.get('title') == title or 
                result.get('url') == url):
                return 'results'
        
        return None
    
    def _detect_from_title(self, title: str) -> Optional[str]:
        """
        Detect content type from title using keyword patterns.
        
        Args:
            title: Article title
            
        Returns:
            Content type if pattern matches, None otherwise
        """
        title_lower = title.lower()
        
        # Check for admit card keywords (check first as they're most specific)
        admit_card_score = sum(
            1 for pattern in self.ADMIT_CARD_KEYWORDS
            if re.search(pattern, title_lower, re.IGNORECASE)
        )
        
        # Check for result keywords
        result_score = sum(
            1 for pattern in self.RESULT_KEYWORDS
            if re.search(pattern, title_lower, re.IGNORECASE)
        )
        
        # Check for job keywords
        job_score = sum(
            1 for pattern in self.JOBS_KEYWORDS
            if re.search(pattern, title_lower, re.IGNORECASE)
        )
        
        # Return type with highest score
        scores = {
            'admit_cards': admit_card_score,
            'results': result_score,
            'jobs': job_score
        }
        
        max_score = max(scores.values())
        if max_score > 0:
            # Return the type with highest score
            for content_type, score in scores.items():
                if score == max_score:
                    return content_type
        
        return None
    
    def _detect_from_url(self, url: str) -> Optional[str]:
        """
        Detect content type from URL patterns.
        
        Args:
            url: Article URL
            
        Returns:
            Content type if URL pattern matches, None otherwise
        """
        url_lower = url.lower()
        
        # Check URL for type indicators
        if any(keyword in url_lower for keyword in ['admit-card', 'hall-ticket', 'call-letter']):
            return 'admit_cards'
        
        if any(keyword in url_lower for keyword in ['result', 'answer-key', 'merit-list', 'cutoff', 'cut-off']):
            return 'results'
        
        if any(keyword in url_lower for keyword in ['recruitment', 'vacancy', 'bharti', 'online-form', 'notification']):
            return 'jobs'
        
        return None
    
    def extract_key_info_from_content(self, content: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key information from generated content for headline generation.
        
        Args:
            content: Generated article HTML content
            details: API details dictionary
            
        Returns:
            Dictionary with extracted information (vacancies, dates, etc.)
        """
        import re
        
        extracted = {
            'vacancy_count': None,
            'total_posts': None,
            'last_date': None,
            'exam_date': None,
            'result_date': None,
            'organization': None
        }
        
        # Extract vacancy count from content or details
        vacancy_patterns = [
            r'(\d{1,3}(?:,\d{3})*|\d+)\s*(?:posts?|vacancies|vacancy|openings)',
            r'total\s+(?:posts?|vacancies):\s*(\d{1,3}(?:,\d{3})*|\d+)',
        ]
        
        for pattern in vacancy_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                extracted['vacancy_count'] = match.group(1)
                break
        
        # Extract from key_details if not found in content
        if not extracted['vacancy_count']:
            key_details = details.get('key_details', {})
            for key in ['Total Posts', 'Vacancies', 'Posts', 'total_posts', 'Total Vacancy']:
                if key in key_details:
                    value = key_details[key]
                    if isinstance(value, dict):
                        value = value.get('raw', '')
                    extracted['vacancy_count'] = str(value) if value else None
                    break
        
        # Extract dates from important_dates
        important_dates = details.get('important_dates', {})
        
        for key in ['Last Date', 'Application End Date', 'Closing Date', 'last_date']:
            if key in important_dates:
                value = important_dates[key]
                if isinstance(value, dict):
                    value = value.get('raw', '')
                extracted['last_date'] = str(value) if value else None
                break
        
        for key in ['Exam Date', 'Test Date', 'exam_date']:
            if key in important_dates:
                value = important_dates[key]
                if isinstance(value, dict):
                    value = value.get('raw', '')
                extracted['exam_date'] = str(value) if value else None
                break
        
        for key in ['Result Date', 'Declaration Date', 'result_date']:
            if key in important_dates:
                value = important_dates[key]
                if isinstance(value, dict):
                    value = value.get('raw', '')
                extracted['result_date'] = str(value) if value else None
                break
        
        logger.info(f"📊 Extracted info: vacancies={extracted['vacancy_count']}, "
                   f"last_date={extracted['last_date']}, exam_date={extracted['exam_date']}, "
                   f"result_date={extracted['result_date']}")
        
        return extracted


# Singleton instance for reuse
_detector_instance = None

def get_content_type_detector() -> ContentTypeDetector:
    """Get singleton instance of content type detector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = ContentTypeDetector()
    return _detector_instance
