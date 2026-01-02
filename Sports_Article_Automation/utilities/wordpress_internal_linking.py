"""
WordPress Internal Linking Integration
Complete workflow for fetching articles from WordPress and suggesting internal links
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import os
import json

from Sports_Article_Automation.utilities.wordpress_article_fetcher import WordPressArticleFetcher
from Sports_Article_Automation.utilities.internal_link_suggester import InternalLinkSuggester

logger = logging.getLogger(__name__)


class WordPressInternalLinkingSystem:
    """
    Complete system for managing internal links across WordPress sites
    Fetches published articles and suggests links for new articles
    """
    
    def __init__(self, site_url: str, username: Optional[str] = None, 
                 app_password: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        Initialize the internal linking system
        
        Args:
            site_url: WordPress site URL
            username: WordPress username
            app_password: WordPress app password
            cache_dir: Directory to cache article data (optional)
        """
        self.site_url = site_url
        self.username = username
        self.app_password = app_password
        self.cache_dir = cache_dir
        
        self.fetcher = WordPressArticleFetcher(site_url, username, app_password)
        self.suggester = InternalLinkSuggester(
            min_similarity=0.25,  # Lower threshold for sports content
            max_links_per_article=4  # Maximum 4 links total (minimum 3)
        )
        
        self.cached_articles = []
        self.keyword_index = {}
        self.last_fetch_time = None
    
    def refresh_article_cache(self, category_id: Optional[int] = None, 
                             cache_expiry_hours: int = 24) -> Tuple[List[Dict], Dict]:
        """
        Fetch and cache all articles from the WordPress site
        
        Args:
            category_id: Optional category to filter by
            cache_expiry_hours: How long to keep cache before refreshing
        
        Returns:
            Tuple of (articles_list, keyword_index)
        """
        # Check if cache is still fresh
        if self.last_fetch_time:
            time_since_fetch = (datetime.now() - self.last_fetch_time).total_seconds() / 3600
            if time_since_fetch < cache_expiry_hours:
                logger.info(f"Using cached articles (fetched {time_since_fetch:.1f} hours ago)")
                return self.cached_articles, self.keyword_index
        
        logger.info(f"Refreshing article cache from {self.site_url}")
        articles, keyword_index = self.fetcher.fetch_and_index_all_articles(category_id)
        
        self.cached_articles = articles
        self.keyword_index = keyword_index
        self.last_fetch_time = datetime.now()
        
        # Optionally save to disk cache
        if self.cache_dir:
            self._save_cache_to_disk()
        
        logger.info(f"Cached {len(articles)} articles with {len(keyword_index)} keywords")
        return articles, keyword_index
    
    def _save_cache_to_disk(self):
        """Save article cache to disk"""
        if not self.cache_dir:
            return
        
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            
            cache_file = os.path.join(self.cache_dir, f"wp_articles_cache_{self.site_url.replace('://', '_').replace('/', '_')}.json")
            
            cache_data = {
                'timestamp': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
                'articles': self.cached_articles,
                'keyword_index': self.keyword_index
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"Saved article cache to {cache_file}")
        
        except Exception as e:
            logger.warning(f"Could not save article cache: {e}")
    
    def _load_cache_from_disk(self) -> bool:
        """Load article cache from disk if available"""
        if not self.cache_dir:
            return False
        
        try:
            cache_file = os.path.join(self.cache_dir, f"wp_articles_cache_{self.site_url.replace('://', '_').replace('/', '_')}.json")
            
            if not os.path.exists(cache_file):
                return False
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.cached_articles = cache_data.get('articles', [])
            self.keyword_index = cache_data.get('keyword_index', {})
            
            if cache_data.get('timestamp'):
                self.last_fetch_time = datetime.fromisoformat(cache_data['timestamp'])
            
            logger.info(f"Loaded {len(self.cached_articles)} articles from disk cache")
            return True
        
        except Exception as e:
            logger.warning(f"Could not load article cache from disk: {e}")
            return False
    
    def suggest_internal_links(self, new_article: Dict, same_category_only: bool = True,
                              refresh_cache: bool = False) -> List[Dict]:
        """
        Suggest internal links for a new article
        
        Args:
            new_article: The new article (must have 'title', 'keywords', 'categories')
            same_category_only: If True, only link within same category
            refresh_cache: If True, refresh article cache before suggesting
        
        Returns:
            List of suggested internal links
        """
        # Refresh cache if needed or if empty
        if refresh_cache or not self.cached_articles:
            self.refresh_article_cache()
        
        if not self.cached_articles:
            logger.warning(f"No cached articles available for {self.site_url}")
            return []
        
        # Find related articles
        related = self.suggester.find_related_articles(
            new_article,
            self.cached_articles,
            same_category_only=same_category_only
        )
        
        logger.info(f"Suggested {len(related)} internal links for '{new_article.get('title')}'")
        
        return related
    
    def add_internal_links_to_content(self, new_article: Dict, content: str,
                                     same_category_only: bool = True,
                                     max_inline_links: int = 3) -> Tuple[str, List[Dict]]:
        """
        Add internal links to article content
        If no relevant articles found, adds "You may Like" section with latest 3 posts
        
        Args:
            new_article: Article metadata (title, keywords, categories)
            content: Article HTML/text content
            same_category_only: Only link within same category
            max_inline_links: Maximum inline links to embed
        
        Returns:
            Tuple of (modified_content, embedded_links_list)
        """
        # Get suggestions
        related = self.suggest_internal_links(new_article, same_category_only=same_category_only)
        
        if not related:
            logger.info("No related articles found for internal linking")
            # Add "You may Like" section with latest 3 posts
            you_may_like_html = self._generate_you_may_like_section(limit=3)
            if you_may_like_html:
                logger.info("Adding 'You may Like' section with latest posts")
                return content + you_may_like_html, []
            return content, []
        
        # Embed links in content
        modified_content, embedded_links = self.suggester.embed_internal_links_in_content(
            content,
            related,
            max_links=max_inline_links
        )
        
        return modified_content, embedded_links
    
    def _generate_you_may_like_section(self, limit: int = 3) -> str:
        """
        Generate HTML for "You may Like" section with latest posts
        
        Args:
            limit: Number of latest posts to include (default: 3)
        
        Returns:
            HTML string for the section, or empty string if no articles
        """
        if not self.cached_articles:
            logger.warning("No cached articles available for 'You may Like' section")
            return ""
        
        # Sort articles by published date (newest first)
        sorted_articles = sorted(
            self.cached_articles,
            key=lambda x: x.get('published_date', ''),
            reverse=True
        )
        
        # Get the latest N articles
        latest_articles = sorted_articles[:limit]
        
        if not latest_articles:
            logger.warning("No articles available for 'You may Like' section")
            return ""
        
        # Build HTML for the section
        html = '<div class="you-may-like-section" style="margin-top: 40px; padding: 20px; background-color: #f5f5f5; border-left: 4px solid #0066cc; border-radius: 4px;">'
        html += '<h3 style="margin-top: 0; color: #333; font-size: 18px;">You may Like</h3>'
        html += '<ul style="list-style: none; padding: 0; margin: 10px 0;">'
        
        for article in latest_articles:
            title = article.get('title', 'Untitled')
            # Use 'url' field (from WordPress link), fallback to 'link', fallback to 'permalink'
            url = article.get('url') or article.get('link') or article.get('permalink') or '#'
            
            # Clean up HTML entities in title if present
            title = title.replace('&#8216;', "'").replace('&#8217;', "'")
            title = title.replace('&#8220;', '"').replace('&#8221;', '"')
            
            html += f'<li style="margin: 8px 0;"><a href="{url}" style="color: #0066cc; text-decoration: none; font-weight: 500;" target="_blank">{title}</a></li>'
        
        html += '</ul>'
        html += '</div>'
        
        logger.info(f"Generated 'You may Like' section with {len(latest_articles)} articles")
        return html
    
    def search_articles_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict]:
        """
        Search for articles by keyword using cached data
        
        Args:
            keyword: Search keyword
            limit: Maximum results
        
        Returns:
            List of matching articles
        """
        if not self.cached_articles:
            logger.warning("No cached articles. Call refresh_article_cache first.")
            return []
        
        keyword_lower = keyword.lower()
        matching = []
        
        for article in self.cached_articles:
            article_keywords = [k.lower() for k in article.get('keywords', [])]
            title = article.get('title', '').lower()
            
            if keyword_lower in article_keywords or keyword_lower in title:
                matching.append(article)
        
        return matching[:limit]
    
    def get_trending_topics(self, days: int = 7, min_articles: int = 2) -> List[Dict]:
        """
        Find trending topics based on articles published in recent days
        
        Args:
            days: Look back this many days
            min_articles: Minimum articles needed for a topic to be "trending"
        
        Returns:
            List of trending topics with article counts
        """
        if not self.cached_articles:
            logger.warning("No cached articles. Call refresh_article_cache first.")
            return []
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        keyword_counts = {}
        
        for article in self.cached_articles:
            pub_date = article.get('published_date', '')
            if pub_date < cutoff_date:
                continue
            
            for keyword in article.get('keywords', []):
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Filter by minimum article count
        trending = [
            {'keyword': k, 'article_count': v}
            for k, v in keyword_counts.items()
            if v >= min_articles
        ]
        
        # Sort by count descending
        trending.sort(key=lambda x: x['article_count'], reverse=True)
        
        logger.info(f"Found {len(trending)} trending topics in last {days} days")
        
        return trending
    
    def get_related_articles_section_html(self, new_article: Dict,
                                         same_category_only: bool = True) -> str:
        """
        Generate complete HTML for "Related Articles" section
        
        Args:
            new_article: Article metadata
            same_category_only: Only link within same category
        
        Returns:
            HTML string ready to append to article
        """
        related = self.suggest_internal_links(new_article, same_category_only=same_category_only)
        
        if not related:
            return ""
        
        return self.suggester.generate_related_articles_section(related)


# ============================================================================
# EXAMPLE USAGE - How to integrate with the sports article automation system
# ============================================================================

def example_usage():
    """Example of how to use the internal linking system"""
    
    # Initialize for a WordPress site
    system = WordPressInternalLinkingSystem(
        site_url="https://example.com",
        username="your_wp_username",
        app_password="your_app_password",
        cache_dir="generated_data/wp_cache"
    )
    
    # Refresh the cache of published articles
    articles, keywords = system.refresh_article_cache(cache_expiry_hours=24)
    print(f"Cached {len(articles)} articles")
    
    # Your new article (would come from the sports article generation pipeline)
    new_article = {
        'title': 'Virat Kohli\'s Latest Cricket Performance Analysis',
        'keywords': ['virat kohli', 'cricket', 'performance', 'india', 'bcci'],
        'categories': [5],  # Category ID 5 = Sports/Cricket
        'content': '<p>Detailed analysis...</p>'
    }
    
    # Method 1: Get suggestions
    suggestions = system.suggest_internal_links(new_article, same_category_only=True)
    for suggestion in suggestions:
        print(f"Link: {suggestion['anchor_text']} -> {suggestion['url']} (Score: {suggestion['relevance_score']:.2f})")
    
    # Method 2: Automatically embed in content
    modified_content, embedded = system.add_internal_links_to_content(
        new_article,
        new_article['content'],
        same_category_only=True
    )
    print(f"Embedded {len(embedded)} internal links")
    
    # Method 3: Add as Related Articles section
    related_html = system.get_related_articles_section_html(new_article)
    final_content = modified_content + related_html
    
    # Method 4: Find trending topics
    trending = system.get_trending_topics(days=7, min_articles=2)
    print(f"Trending topics: {trending}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    example_usage()
