"""
Internal Linking Utility for Job Portal Automation
Fetches random articles from WordPress and adds "More from Site" section
"""

import logging
import random
import requests
import base64
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)


class JobPortalInternalLinker:
    """Adds internal links section to job portal articles"""
    
    def __init__(self):
        """Initialize the internal linker"""
        self.article_cache = {}  # Cache articles per site
    
    def add_internal_links_section(
        self,
        content: str,
        site_url: str,
        site_name: str,
        username: Optional[str] = None,
        app_password: Optional[str] = None,
        num_links: int = 5
    ) -> str:
        """
        Add internal links section at the end of article content.
        
        Args:
            content: Article HTML content
            site_url: WordPress site URL
            site_name: Website name (e.g., "Stockdunia")
            username: WordPress username for API access
            app_password: WordPress app password
            num_links: Number of internal links to add (default: 5)
            
        Returns:
            Content with internal links section appended
        """
        try:
            # Fetch random articles from the site
            articles = self._fetch_random_articles(
                site_url=site_url,
                username=username,
                app_password=app_password,
                count=num_links
            )
            
            if not articles:
                logger.warning(f"No articles found for internal linking on {site_url}")
                return content
            
            # Build the internal links section
            links_section = self._build_links_section(articles, site_name)
            
            # Append to content
            enhanced_content = content + "\n\n" + links_section
            
            logger.info(f"✅ Added {len(articles)} internal links to article")
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Failed to add internal links: {e}")
            return content  # Return original content on error
    
    def _fetch_random_articles(
        self,
        site_url: str,
        username: Optional[str],
        app_password: Optional[str],
        count: int = 5
    ) -> List[Dict[str, str]]:
        """
        Fetch random published articles from WordPress site.
        
        Args:
            site_url: WordPress site URL
            username: WordPress username
            app_password: WordPress app password
            count: Number of articles to fetch
            
        Returns:
            List of article dicts with 'title' and 'url' keys
        """
        try:
            # Check cache first
            cache_key = site_url
            if cache_key in self.article_cache and len(self.article_cache[cache_key]) >= count:
                cached_articles = self.article_cache[cache_key]
                return random.sample(cached_articles, min(count, len(cached_articles)))
            
            # Setup authentication
            headers = {'Content-Type': 'application/json'}
            if username and app_password:
                creds = base64.b64encode(f"{username}:{app_password}".encode()).decode()
                headers['Authorization'] = f"Basic {creds}"
            
            # Fetch recent published posts
            api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
            params = {
                'per_page': 50,  # Fetch 50 recent posts
                'status': 'publish',
                'orderby': 'date',
                'order': 'desc'
            }
            
            logger.info(f"📡 Fetching articles from {site_url} for internal linking...")
            
            response = requests.get(
                api_url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 404:
                logger.warning(f"WordPress REST API not available at {site_url}")
                return []
            
            response.raise_for_status()
            posts = response.json()
            
            if not posts:
                logger.warning(f"No published posts found on {site_url}")
                return []
            
            # Extract title and URL
            articles = []
            for post in posts:
                articles.append({
                    'title': post.get('title', {}).get('rendered', 'Untitled'),
                    'url': post.get('link', '')
                })
            
            # Cache for future use
            self.article_cache[cache_key] = articles
            
            logger.info(f"✅ Fetched {len(articles)} articles from {site_url}")
            
            # Return random selection
            return random.sample(articles, min(count, len(articles)))
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching articles from {site_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching articles: {e}")
            return []
    
    def _build_links_section(self, articles: List[Dict[str, str]], site_name: str) -> str:
        """
        Build HTML section for internal links.
        
        Args:
            articles: List of article dicts with 'title' and 'url'
            site_name: Website name for heading
            
        Returns:
            HTML string for internal links section
        """
        # Clean up HTML entities in titles
        def clean_title(title: str) -> str:
            """Remove HTML entities and tags from title"""
            # Remove HTML tags
            title = re.sub(r'<[^>]+>', '', title)
            # Decode common HTML entities
            title = title.replace('&amp;', '&')
            title = title.replace('&quot;', '"')
            title = title.replace('&#8217;', "'")
            title = title.replace('&#8211;', '–')
            title = title.replace('&#8212;', '—')
            title = title.replace('&nbsp;', ' ')
            return title.strip()
        
        # Build simple box with border
        html_parts = [
            '<div style="margin-top: 40px; padding: 20px; border: 2px solid #ddd; border-radius: 8px;">',
            f'<h3 style="margin-top: 0; margin-bottom: 15px; font-size: 20px; font-weight: 600;">More from {site_name}</h3>',
            '<ul style="list-style: disc; padding-left: 20px; margin: 0;">'
        ]
        
        for article in articles:
            title = clean_title(article['title'])
            url = article['url']
            
            html_parts.append(
                f'<li style="margin-bottom: 10px;">'
                f'<a href="{url}" style="color: #0066cc; text-decoration: none;">{title}</a>'
                f'</li>'
            )
        
        html_parts.append('</ul>')
        html_parts.append('</div>')
        
        return '\n'.join(html_parts)
