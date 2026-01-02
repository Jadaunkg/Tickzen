"""
WordPress Article Fetcher
Fetches all published articles from a WordPress site via REST API
Supports pagination and builds a searchable index of articles
"""

import requests
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


class HTMLStripper(HTMLParser):
    """Helper class to strip HTML tags from content"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return ''.join(self.text)


def strip_html_tags(html_content: str) -> str:
    """Remove HTML tags from content"""
    if not html_content:
        return ""
    stripper = HTMLStripper()
    try:
        stripper.feed(html_content)
        return stripper.get_data()
    except Exception as e:
        logger.warning(f"Error stripping HTML tags: {e}")
        return html_content


def extract_keywords(title: str, content: str, max_keywords: int = 15) -> List[str]:
    """
    Extract keywords from title and content
    Uses frequency analysis with broader keyword coverage for better linking
    """
    if not title or not content:
        return []
    
    # Combine and convert to lowercase
    text = (title + " " + content).lower()
    
    # Remove HTML and special characters
    text = strip_html_tags(text)
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Common stop words to exclude (refined list - less aggressive)
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'that', 'this', 'it', 'as',
        'if', 'about', 'all', 'each', 'every', 'some', 'any', 'which', 'who',
        'what', 'where', 'when', 'why', 'how', 'also', 'just', 'more', 'than',
        'up', 'out', 'so', 'no', 'not', 'only', 'same', 'such', 'then', 'there',
        'their', 'your', 'me', 'my', 'he', 'she', 'we', 'they', 'you', 'him', 'her',
        # Remove aggressive filtering of common sports words
        # Keep: 'says', 'said', 'according', 'see', 'get'
    }
    
    # Extract words with length > 2 (lowered from 3 for better matching)
    words = [w for w in text.split() if len(w) > 2 and w not in stop_words]
    
    # Count word frequencies
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, freq in sorted_words[:max_keywords]]
    
    return keywords


class WordPressArticleFetcher:
    """Fetches and indexes articles from WordPress REST API"""
    
    def __init__(self, site_url: str, username: Optional[str] = None, app_password: Optional[str] = None):
        """
        Initialize WordPress fetcher
        
        Args:
            site_url: Base URL of WordPress site (e.g., https://example.com)
            username: WordPress username for authenticated requests
            app_password: WordPress app password for authenticated requests
        """
        self.site_url = site_url.rstrip('/')
        self.username = username
        self.app_password = app_password
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        
        # Setup authentication if provided
        self.auth = None
        self.headers = {'Content-Type': 'application/json'}
        if username and app_password:
            import base64
            creds = base64.b64encode(f"{username}:{app_password}".encode()).decode()
            self.headers['Authorization'] = f"Basic {creds}"
            self.auth = (username, app_password)
    
    def fetch_all_posts(self, category_id: Optional[int] = None, search: Optional[str] = None) -> List[Dict]:
        """
        Fetch all published posts from the site
        
        Args:
            category_id: Optional category ID to filter by
            search: Optional search term to filter by
        
        Returns:
            List of article dictionaries
        """
        all_posts = []
        page = 1
        posts_per_page = 100
        
        try:
            while True:
                params = {
                    'per_page': posts_per_page,
                    'page': page,
                    'status': 'publish',
                    'orderby': 'modified',
                    'order': 'desc'
                }
                
                if category_id:
                    params['categories'] = category_id
                
                if search:
                    params['search'] = search
                
                logger.info(f"Fetching posts from {self.site_url} - Page {page}")
                response = requests.get(
                    f"{self.api_base}/posts",
                    params=params,
                    headers=self.headers,
                    auth=self.auth,
                    timeout=30
                )
                
                if response.status_code == 404:
                    logger.warning(f"Posts endpoint not found for {self.site_url}")
                    break
                
                response.raise_for_status()
                posts = response.json()
                
                if not posts:
                    logger.info(f"No more posts to fetch (page {page})")
                    break
                
                all_posts.extend(posts)
                logger.info(f"Fetched {len(posts)} posts (total: {len(all_posts)})")
                
                # Check if there are more pages
                if len(posts) < posts_per_page:
                    break
                
                page += 1
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching posts from {self.site_url}: {e}")
        
        return all_posts
    
    def fetch_all_categories(self) -> List[Dict]:
        """Fetch all categories from the site"""
        try:
            logger.info(f"Fetching categories from {self.site_url}")
            response = requests.get(
                f"{self.api_base}/categories",
                params={'per_page': 100},
                headers=self.headers,
                auth=self.auth,
                timeout=30
            )
            response.raise_for_status()
            categories = response.json()
            logger.info(f"Fetched {len(categories)} categories")
            return categories
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching categories from {self.site_url}: {e}")
            return []
    
    def parse_post_data(self, post: Dict) -> Dict:
        """
        Parse WordPress post data into standardized format
        
        Args:
            post: Raw WordPress post data
        
        Returns:
            Parsed article dictionary
        """
        try:
            content = post.get('content', {}).get('rendered', '')
            content_text = strip_html_tags(content)
            
            title = post.get('title', {}).get('rendered', '').strip() if isinstance(post.get('title'), dict) else post.get('title', '').strip()
            
            # Extract categories
            categories = post.get('categories', [])
            category_names = []
            if categories:
                # Category IDs are returned, we'd need to map them to names
                category_names = [str(c) for c in categories]
            
            # Generate keywords from title and content
            keywords = extract_keywords(title, content_text)
            
            article = {
                'id': post.get('id'),
                'post_id': post.get('id'),
                'title': title,
                'url': post.get('link', ''),
                'permalink': post.get('link', ''),
                'content': content_text[:500] if content_text else '',  # First 500 chars
                'content_full': content_text,
                'excerpt': post.get('excerpt', {}).get('rendered', '').strip() if isinstance(post.get('excerpt'), dict) else post.get('excerpt', '').strip(),
                'published_date': post.get('date', ''),
                'modified_date': post.get('modified', ''),
                'categories': categories,
                'category_names': category_names,
                'keywords': keywords,
                'author': post.get('author', ''),
                'featured_media': post.get('featured_media'),
                'slug': post.get('slug', ''),
                'status': post.get('status', ''),
            }
            
            return article
        
        except Exception as e:
            logger.error(f"Error parsing post data: {e}")
            return {}
    
    def fetch_and_index_all_articles(self, category_id: Optional[int] = None) -> Tuple[List[Dict], Dict]:
        """
        Fetch all posts and create an index for fast searching
        
        Args:
            category_id: Optional category ID to fetch
        
        Returns:
            Tuple of (articles_list, indexed_by_keyword_dict)
        """
        logger.info(f"Fetching and indexing articles from {self.site_url}")
        
        raw_posts = self.fetch_all_posts(category_id=category_id)
        articles = []
        keyword_index = {}  # keyword -> list of article IDs
        
        for post in raw_posts:
            article = self.parse_post_data(post)
            if article:
                articles.append(article)
                
                # Build keyword index
                for keyword in article.get('keywords', []):
                    if keyword not in keyword_index:
                        keyword_index[keyword] = []
                    keyword_index[keyword].append(article['id'])
        
        logger.info(f"Successfully indexed {len(articles)} articles with {len(keyword_index)} unique keywords")
        
        return articles, keyword_index
    
    def search_articles(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search articles on the WordPress site
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of matching articles
        """
        try:
            logger.info(f"Searching articles on {self.site_url} for: {query}")
            response = requests.get(
                f"{self.api_base}/posts",
                params={
                    'search': query,
                    'per_page': limit,
                    'status': 'publish'
                },
                headers=self.headers,
                auth=self.auth,
                timeout=30
            )
            response.raise_for_status()
            posts = response.json()
            
            articles = []
            for post in posts:
                article = self.parse_post_data(post)
                if article:
                    articles.append(article)
            
            logger.info(f"Found {len(articles)} articles matching '{query}'")
            return articles
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching articles on {self.site_url}: {e}")
            return []
    
    def get_articles_by_category(self, category_id: int) -> List[Dict]:
        """
        Get all articles in a specific category
        
        Args:
            category_id: WordPress category ID
        
        Returns:
            List of articles in that category
        """
        raw_posts = self.fetch_all_posts(category_id=category_id)
        articles = []
        
        for post in raw_posts:
            article = self.parse_post_data(post)
            if article:
                articles.append(article)
        
        logger.info(f"Found {len(articles)} articles in category {category_id}")
        return articles
