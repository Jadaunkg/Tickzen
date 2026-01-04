"""
Enhanced Sports Article Automation Configuration
Controls advanced features and optimizations for research collection and article generation

RATE LIMIT OPTIMIZATION: 
- Perplexity API allows 2 requests per minute
- System now uses single comprehensive request per article
- All enhanced research packed into one ultra-comprehensive query
- Follow-up queries disabled to respect rate limits
"""

import os
from typing import Dict, List

class EnhancedConfig:
    """Configuration for enhanced sports article automation features"""
    
    # Enhanced Research Collection Settings
    ENABLE_ENHANCED_RESEARCH = True  # Use comprehensive single-request approach
    MAX_FOLLOWUP_QUERIES = 0  # DISABLED: Use only 1 request due to Perplexity rate limits (2 req/min)
    RESEARCH_RECENCY_FILTER = "week"  # Options: "hour", "day", "week", "month" - Set to week (7 days)
    INCLUDE_SOCIAL_MEDIA_RESEARCH = True  # Include Twitter, Reddit, YouTube in research
    INCLUDE_FINANCIAL_ANALYSIS = True  # Include business/economic impact analysis
    
    # Enhanced Article Generation Settings
    ENABLE_PREMIUM_WRITING = True  # Use advanced journalism prompts
    TARGET_ARTICLE_LENGTH = "long"  # Options: "standard" (800-1100), "long" (1000-1400), "detailed" (1400-2000)
    WRITING_STYLE = "investigative"  # Options: "standard", "investigative", "breaking", "feature"
    INCLUDE_MULTIMEDIA_ELEMENTS = True  # Add stat boxes, enhanced quotes, callouts
    
    # Source Diversification Settings
    ENABLE_INTERNATIONAL_SOURCES = True  # Include global sports outlets
    INCLUDE_OFFICIAL_SOURCES = True  # Team/league official websites and social media
    MAX_SOURCES_PER_ARTICLE = 8  # Maximum number of sources to link in article
    
    # API Optimization Settings
    PERPLEXITY_MAX_TOKENS = 4000  # Increased from 3000 for comprehensive research
    GEMINI_MAX_TOKENS = 12000  # Increased from 8192 for detailed articles
    GEMINI_TEMPERATURE = 0.8  # Balanced creativity vs accuracy
    
    # Content Quality Controls
    REQUIRE_DIRECT_QUOTES = True  # Must include at least 3 direct quotes
    REQUIRE_STATISTICAL_DATA = True  # Must include specific numbers/stats
    REQUIRE_EXPERT_ANALYSIS = True  # Must include expert commentary
    REQUIRE_FUTURE_IMPLICATIONS = True  # Must discuss what happens next
    
    # SEO and Publishing Optimization
    OPTIMIZE_FOR_FEATURED_SNIPPETS = True  # Structure content for Google featured snippets
    INCLUDE_FAQ_SECTIONS = False  # Add FAQ sections for complex topics
    GENERATE_META_DESCRIPTIONS = True  # Auto-generate SEO meta descriptions
    OPTIMIZE_HEADLINE_LENGTH = True  # Enforce 55-65 character headlines
    
    # Publishing and Scheduling Settings
    DEFAULT_PUBLISH_STATUS = "future"  # Options: "publish", "draft", "future"
    MIN_SCHEDULING_INTERVAL = 30  # Minimum minutes between scheduled posts
    MAX_SCHEDULING_INTERVAL = 90  # Maximum minutes between scheduled posts
    RESPECT_PROFILE_INTERVALS = True  # Use profile-specific intervals when available
    AUTO_CATEGORY_MAPPING = True  # Automatically map article categories to WordPress categories
    
    @classmethod
    def get_perplexity_config(cls) -> Dict:
        """Get optimized Perplexity API configuration"""
        return {
            "max_tokens": cls.PERPLEXITY_MAX_TOKENS,
            "temperature": 0.2,  # Low for factual research
            "top_p": 0.85,
            "search_recency_filter": cls.RESEARCH_RECENCY_FILTER,
            "return_images": cls.INCLUDE_MULTIMEDIA_ELEMENTS,
            "return_related_questions": cls.ENABLE_ENHANCED_RESEARCH,
            "citations": True
        }
    
    @classmethod
    def get_gemini_config(cls) -> Dict:
        """Get optimized Gemini generation configuration"""
        return {
            "temperature": cls.GEMINI_TEMPERATURE,
            "top_p": 0.9,
            "top_k": 50,
            "max_output_tokens": cls.GEMINI_MAX_TOKENS,
            "candidate_count": 1,
            "stop_sequences": ["END_ARTICLE"]
        }
    
    @classmethod
    def get_article_length_target(cls) -> tuple:
        """Get target word count based on configuration"""
        length_targets = {
            "standard": (800, 1100),
            "long": (1000, 1400), 
            "detailed": (1400, 2000)
        }
        return length_targets.get(cls.TARGET_ARTICLE_LENGTH, (1000, 1400))
    
    @classmethod
    def get_enhanced_sources(cls, category: str = None) -> List[str]:
        """Get comprehensive source list based on configuration"""
        base_sources = [
            "ESPN", "BBC Sport", "Reuters Sports", "Associated Press", "The Athletic", 
            "Sky Sports", "Yahoo Sports", "CBS Sports", "NBC Sports", "Fox Sports"
        ]
        
        if cls.ENABLE_INTERNATIONAL_SOURCES:
            international_sources = [
                "Guardian Sport", "Daily Mail Sport", "Telegraph Sport", "Marca", 
                "L'Equipe", "Gazzetta dello Sport", "Bild Sport", "AS", "Sport1"
            ]
            base_sources.extend(international_sources)
        
        if cls.INCLUDE_OFFICIAL_SOURCES:
            official_sources = [
                "official league websites", "team official accounts", 
                "player verified social media", "coach press conferences"
            ]
            base_sources.extend(official_sources)
        
        if cls.INCLUDE_SOCIAL_MEDIA_RESEARCH:
            social_sources = [
                "Twitter/X verified accounts", "Reddit sports communities",
                "YouTube official channels", "Instagram verified posts"
            ]
            base_sources.extend(social_sources)
        
        return base_sources
    
    @classmethod
    def get_writing_prompt_style(cls) -> str:
        """Get writing style configuration for prompts"""
        style_configs = {
            "standard": "professional sports journalist",
            "investigative": "award-winning investigative sports journalist with insider access",
            "breaking": "breaking news sports reporter with real-time sources",
            "feature": "long-form sports feature writer with storytelling expertise"
        }
        return style_configs.get(cls.WRITING_STYLE, "award-winning sports journalist")
    
    @classmethod
    def get_category_mapping(cls) -> Dict[str, int]:
        """Get automatic category mapping for different sports"""
        return {
            'football': 2,
            'soccer': 2,
            'basketball': 3,
            'nba': 3,
            'cricket': 4,
            'baseball': 5,
            'mlb': 5,
            'hockey': 6,
            'nhl': 6,
            'tennis': 7,
            'golf': 8,
            'general': 1,
            'sports': 1
        }
    
    @classmethod
    def get_publishing_config(cls) -> Dict:
        """Get publishing configuration settings"""
        return {
            'default_status': cls.DEFAULT_PUBLISH_STATUS,
            'min_interval': cls.MIN_SCHEDULING_INTERVAL,
            'max_interval': cls.MAX_SCHEDULING_INTERVAL,
            'respect_profile_intervals': cls.RESPECT_PROFILE_INTERVALS,
            'auto_category_mapping': cls.AUTO_CATEGORY_MAPPING,
            'category_mapping': cls.get_category_mapping()
        }

# Environment variable overrides
def load_env_overrides():
    """Load configuration overrides from environment variables"""
    if os.getenv('SPORTS_ENHANCED_RESEARCH', '').lower() == 'true':
        EnhancedConfig.ENABLE_ENHANCED_RESEARCH = True
    
    if os.getenv('SPORTS_ARTICLE_LENGTH'):
        EnhancedConfig.TARGET_ARTICLE_LENGTH = os.getenv('SPORTS_ARTICLE_LENGTH')
    
    if os.getenv('SPORTS_WRITING_STYLE'):
        EnhancedConfig.WRITING_STYLE = os.getenv('SPORTS_WRITING_STYLE')
    
    if os.getenv('SPORTS_MAX_SOURCES'):
        EnhancedConfig.MAX_SOURCES_PER_ARTICLE = int(os.getenv('SPORTS_MAX_SOURCES'))
    
    # Publishing configuration overrides
    if os.getenv('SPORTS_DEFAULT_PUBLISH_STATUS'):
        EnhancedConfig.DEFAULT_PUBLISH_STATUS = os.getenv('SPORTS_DEFAULT_PUBLISH_STATUS')
    
    if os.getenv('SPORTS_MIN_INTERVAL'):
        EnhancedConfig.MIN_SCHEDULING_INTERVAL = int(os.getenv('SPORTS_MIN_INTERVAL'))
    
    if os.getenv('SPORTS_MAX_INTERVAL'):
        EnhancedConfig.MAX_SCHEDULING_INTERVAL = int(os.getenv('SPORTS_MAX_INTERVAL'))
    
    if os.getenv('SPORTS_AUTO_CATEGORY_MAPPING', '').lower() == 'false':
        EnhancedConfig.AUTO_CATEGORY_MAPPING = False

# Load overrides on import
load_env_overrides()