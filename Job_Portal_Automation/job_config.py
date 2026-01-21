"""
Job Portal Automation Configuration
====================================

Configuration settings for the job portal automation system.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration"""
    
    # Job Crawler API
    JOB_API_BASE_URL = "https://job-crawler-api-0885.onrender.com"
    JOB_API_TIMEOUT = 30
    JOB_API_MAX_RETRIES = 3
    JOB_API_RETRY_DELAY = 1
    
    # Perplexity AI
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY', '')
    PERPLEXITY_MODEL = "sonar"
    PERPLEXITY_TIMEOUT = 90
    PERPLEXITY_MAX_TOKENS = 4000
    PERPLEXITY_TEMPERATURE = 0.2
    
    # Gemini AI (for Phase 3)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = "gemini-2.5-pro"
    
    # WordPress (for Phase 4)
    WORDPRESS_DEFAULT_STATUS = "draft"  # or "publish"
    WORDPRESS_FEATURED_IMAGE_URL = None
    WORDPRESS_CATEGORIES = {
        'jobs': 'Government Jobs',
        'results': 'Exam Results',
        'admit_cards': 'Admit Cards'
    }
    WORDPRESS_DEFAULT_AUTHOR_ID = 1
    WORDPRESS_DRY_RUN = os.getenv('JOB_AUTOMATION_WP_DRY_RUN', 'true').lower() in ('1', 'true', 'yes')
    WORDPRESS_DEFAULT_CATEGORY_ID = int(os.getenv('JOB_AUTOMATION_WP_CATEGORY_ID', '0')) or None
    
    # Content generation
    MIN_ARTICLE_LENGTH = 600
    MAX_ARTICLE_LENGTH = 1200
    INCLUDE_SEO_OPTIMIZATION = True
    INCLUDE_INTERNAL_LINKS = True
    INCLUDE_EXTERNAL_LINKS = True
    
    # State management
    STATE_STORAGE_DIR = os.path.join(
        os.path.dirname(__file__), '..', 'data'
    )
    USE_FIRESTORE = True
    LOCAL_STATE_BACKUP = True
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(
        os.path.dirname(__file__), '..', 'logs', 'job_automation.log'
    )
    
    # Feature flags
    ENABLE_PERPLEXITY_RESEARCH = True
    ENABLE_FIRESTORE = True
    ENABLE_BATCH_PROCESSING = True
    ENABLE_REAL_TIME_UPDATES = True
    
    # Pagination
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 100
    
    # Rate limiting
    RATE_LIMIT_JOBS_PER_HOUR = 100
    RATE_LIMIT_ARTICLES_PER_DAY = 50
    
    # Scheduling intervals for 'future' posts (matches sports article scheduling)
    MIN_SCHEDULING_INTERVAL_MINUTES = int(os.getenv('JOB_MIN_INTERVAL', '45'))
    MAX_SCHEDULING_INTERVAL_MINUTES = int(os.getenv('JOB_MAX_INTERVAL', '90'))


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    WORDPRESS_DEFAULT_STATUS = "draft"  # Always draft for testing
    PERPLEXITY_TEMPERATURE = 0.3  # Slightly higher for testing


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    WORDPRESS_DEFAULT_STATUS = "draft"  # Review before publishing
    PERPLEXITY_TEMPERATURE = 0.2  # Lower for consistency


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    WORDPRESS_DEFAULT_STATUS = "draft"
    PERPLEXITY_TIMEOUT = 30  # Lower for faster tests
    JOB_API_MAX_RETRIES = 1  # No retries in tests


def get_config(env: str = None) -> Config:
    """
    Get configuration object based on environment
    
    Args:
        env: Environment name (development, production, testing)
             If None, reads from ENVIRONMENT variable
    
    Returns:
        Configuration object
    """
    if env is None:
        env = os.getenv('ENVIRONMENT', 'development').lower()
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return config_map.get(env, DevelopmentConfig)()
