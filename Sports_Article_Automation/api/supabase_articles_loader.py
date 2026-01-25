"""
Supabase Articles Loader module for Sports_Article_Automation

This module provides functions to load sports articles from Supabase database
using the new data source schema.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dateutil import parser
import pytz

# Import Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

logger = logging.getLogger("SupabaseArticlesLoader")


class SupabaseArticlesLoader:
    """Loader for sports articles from Supabase database"""
    
    def __init__(self):
        """Initialize the Supabase articles loader"""
        self.supabase_client = None
        self.ist = pytz.timezone('Asia/Kolkata')
        self.utc = pytz.UTC
        
        if SUPABASE_AVAILABLE:
            self._initialize_supabase_client()
        else:
            logger.warning("Supabase not available - install with: pip install supabase")
    
    def _initialize_supabase_client(self):
        """Initialize Supabase client with sports database credentials"""
        try:
            # Get sports-specific Supabase credentials from environment
            supabase_url = os.getenv('SPORTS_SUPABASE_URL')
            supabase_key = os.getenv('SPORTS_SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                logger.error("Missing SPORTS_SUPABASE_URL or SPORTS_SUPABASE_ANON_KEY in environment variables")
                return
                
            self.supabase_client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully for sports database")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.supabase_client = None
    
    def is_available(self) -> bool:
        """Check if Supabase client is available and working"""
        return self.supabase_client is not None and SUPABASE_AVAILABLE
    
    def load_database_articles(self, limit: int = 500) -> List[Dict]:
        """
        Load articles from Supabase database
        
        Args:
            limit (int): Maximum number of articles to load
            
        Returns:
            list: List of articles from the database
        """
        if not self.is_available():
            logger.warning("Supabase client not available")
            return []
        
        try:
            # Query articles from Supabase with proper ordering
            # Note: We'll query articles first, then get site info separately if needed
            response = self.supabase_client.table('articles').select(
                '*'  # Start with just articles data
            ).eq('ready_for_analysis', True).order(
                'publish_date', desc=True
            ).limit(limit).execute()
            
            if not response.data:
                logger.info("No articles found in Supabase database")
                return []
            
            # For each article, we might need to get site information separately
            # if there are foreign key relationships
            articles = []
            for article_data in response.data:
                # Try to get site information if site_id exists
                site_info = {}
                site_id = article_data.get('site_id')
                if site_id:
                    try:
                        site_response = self.supabase_client.table('sites').select(
                            'name, domain'
                        ).eq('id', site_id).limit(1).execute()
                        if site_response.data:
                            site_info = site_response.data[0]
                    except Exception as site_error:
                        logger.warning(f"Could not fetch site info for article {article_data.get('id')}: {site_error}")
                
                # Add site info to article data
                article_data['sites'] = site_info
                
                # Convert Supabase article to format compatible with existing system
                formatted_article = self._format_database_article(article_data)
                if formatted_article:
                    articles.append(formatted_article)
            
            logger.info(f"Loaded {len(articles)} articles from Supabase database")
            return articles
            
        except Exception as e:
            logger.error(f"Error loading articles from Supabase: {e}")
            return []
    
    def _format_database_article(self, article_data: Dict) -> Optional[Dict]:
        """
        Format Supabase article data to match existing article format
        
        Args:
            article_data (dict): Raw article data from Supabase
            
        Returns:
            dict: Formatted article data
        """
        try:
            # Extract site information
            site_info = article_data.get('sites', {})
            site_name = site_info.get('name', 'Unknown Site') if site_info else 'Unknown Site'
            site_domain = site_info.get('domain', '') if site_info else ''
            
            # Parse and format dates
            publish_date = article_data.get('publish_date')
            crawl_time = article_data.get('crawl_time')
            
            # Format publish date with timezone handling
            formatted_publish_date = None
            display_date_ist = None
            display_date_iso = None
            published_date_parsed = None
            
            if publish_date:
                try:
                    # Parse the datetime string
                    if isinstance(publish_date, str):
                        pub_dt = parser.parse(publish_date)
                    else:
                        pub_dt = publish_date
                    
                    # Ensure timezone awareness - assume UTC if no timezone
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=self.utc)
                    
                    # Store parsed datetime for sorting and time bracket calculation
                    published_date_parsed = pub_dt
                    
                    # Convert to IST for display
                    ist_dt = pub_dt.astimezone(self.ist)
                    display_date_ist = ist_dt.strftime('%Y-%m-%d %H:%M:%S IST')
                    display_date_iso = ist_dt.isoformat()
                    formatted_publish_date = pub_dt.isoformat()
                    
                except Exception as e:
                    logger.warning(f"Error parsing publish date for article {article_data.get('id')}: {e}")
            
            # Handle crawl_time formatting
            crawl_time_ist = None
            if crawl_time:
                try:
                    if isinstance(crawl_time, str):
                        crawl_dt = parser.parse(crawl_time)
                    else:
                        crawl_dt = crawl_time
                    
                    if crawl_dt.tzinfo is None:
                        crawl_dt = crawl_dt.replace(tzinfo=self.utc)
                    
                    crawl_ist = crawl_dt.astimezone(self.ist)
                    crawl_time_ist = crawl_ist.strftime('%Y-%m-%d %H:%M:%S IST')
                except Exception as e:
                    logger.warning(f"Error parsing crawl time for article {article_data.get('id')}: {e}")
                    crawl_time_ist = str(crawl_time)
            
            # Generate article in compatible format
            formatted_article = {
                # Core identifiers
                'id': article_data.get('id', ''),
                'hash': article_data.get('url_hash', ''),
                'url_hash': article_data.get('url_hash', ''),
                
                # Content fields
                'title': article_data.get('title', 'Untitled Article'),
                'link': article_data.get('url', ''),
                'url': article_data.get('url', ''),
                'author': article_data.get('author', 'Unknown Author'),
                'content': article_data.get('content', ''),
                'summary': self._extract_summary(article_data.get('content', '')),
                
                # Categorization
                'category': article_data.get('sport_category', 'UNCATEGORIZED'),
                'source': site_name,
                'source_name': article_data.get('source_site', site_name),  # Map to source_name for display
                'source_site': article_data.get('source_site', site_name),
                'source_domain': site_domain,
                
                # Dates (multiple formats for compatibility)
                'published_date': formatted_publish_date,
                'published_date_parsed': published_date_parsed,  # For sorting
                'published_date_ist': display_date_ist,
                'display_date_ist': display_date_ist,
                'display_date_iso': display_date_iso,
                'published_time': display_date_ist,  # This field is used in the UI template
                'collected_date': crawl_time_ist or crawl_time,
                'collected_date_parsed': published_date_parsed,  # For time bracket calculation
                'crawl_time': crawl_time_ist or crawl_time,  # Convert to IST for display
                
                # Metadata for UI display
                'importance_tier': self._calculate_importance_tier(article_data),
                'importance_score': self._calculate_importance_score(article_data),
                'time_bracket': self._determine_time_bracket(published_date_parsed),
                
                # Source type identifier
                'data_source': 'database',  # This is the key field to identify database articles
                'source_type': 'supabase_database',
                
                # Additional metadata
                'ready_for_analysis': article_data.get('ready_for_analysis', True),
                'created_at': article_data.get('created_at'),
            }
            
            return formatted_article
            
        except Exception as e:
            logger.error(f"Error formatting article data: {e}")
            return None
    
    def _extract_summary(self, content: str, max_length: int = 200) -> str:
        """Extract summary from article content"""
        if not content:
            return "No summary available"
        
        # Simple text cleaning and truncation
        from bs4 import BeautifulSoup
        try:
            # Remove HTML tags if present
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text()
            
            # Clean and truncate
            text = ' '.join(text.split())  # Remove extra whitespace
            if len(text) > max_length:
                text = text[:max_length] + '...'
            
            return text if text else "No summary available"
        except:
            # Fallback to simple truncation
            text = content[:max_length] + '...' if len(content) > max_length else content
            return text if text else "No summary available"
    
    def _calculate_importance_tier(self, article_data: Dict) -> str:
        """Calculate importance tier based on article data"""
        # Simple scoring based on available metadata
        score = 0
        
        # Check for important indicators
        title = article_data.get('title', '').lower()
        content = article_data.get('content', '').lower()
        
        # Keywords that indicate higher importance
        high_importance_keywords = [
            'breaking', 'exclusive', 'major', 'championship', 'final', 
            'win', 'winner', 'victory', 'defeat', 'match', 'game',
            'world', 'national', 'international', 'olympic', 'premier'
        ]
        
        medium_importance_keywords = [
            'score', 'team', 'player', 'season', 'league', 'tournament',
            'update', 'news', 'report', 'analysis'
        ]
        
        # Score based on title keywords
        for keyword in high_importance_keywords:
            if keyword in title:
                score += 2
        
        for keyword in medium_importance_keywords:
            if keyword in title:
                score += 1
        
        # Check content length (longer articles might be more important)
        content_length = len(content)
        if content_length > 2000:
            score += 2
        elif content_length > 1000:
            score += 1
        
        # Determine tier
        if score >= 4:
            return 'High'
        elif score >= 2:
            return 'Medium'
        else:
            return 'Low'
    
    def _calculate_importance_score(self, article_data: Dict) -> float:
        """Calculate numerical importance score"""
        tier = self._calculate_importance_tier(article_data)
        
        score_mapping = {
            'High': 85.0,
            'Medium': 60.0,
            'Low': 35.0
        }
        
        base_score = score_mapping.get(tier, 50.0)
        
        # Add some randomness to avoid ties
        import random
        random.seed(hash(article_data.get('id', '')))
        adjustment = random.uniform(-5.0, 5.0)
        
        return max(0.0, min(100.0, base_score + adjustment))
    
    def _determine_time_bracket(self, publish_date) -> str:
        """Determine time bracket for the article"""
        if not publish_date:
            return 'recent'
        
        try:
            # publish_date should already be a parsed datetime object
            if isinstance(publish_date, str):
                pub_dt = parser.parse(publish_date)
            else:
                pub_dt = publish_date
            
            # Ensure timezone awareness
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=self.utc)
            
            # Compare with current time in UTC
            now = datetime.now(self.utc)
            time_diff = now - pub_dt
            
            if time_diff.total_seconds() < 0:
                return 'future'  # Article is from the future (possible timezone issue)
            elif time_diff.days == 0:
                if time_diff.total_seconds() < 3600:  # Less than 1 hour
                    return 'latest'
                else:
                    return 'today'
            elif time_diff.days == 1:
                return 'yesterday'
            elif time_diff.days <= 7:
                return 'this_week'
            elif time_diff.days <= 30:
                return 'this_month'
            else:
                return 'older'
                
        except Exception as e:
            logger.warning(f"Error determining time bracket: {e}")
            return 'recent'
    
    def _determine_time_bracket(self, publish_date) -> str:
        """Determine time bracket for the article"""
        if not publish_date:
            return 'recent'
        
        try:
            if isinstance(publish_date, str):
                pub_dt = parser.parse(publish_date)
            else:
                pub_dt = publish_date
            
            # Ensure timezone awareness
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=self.utc)
            
            now = datetime.now(self.utc)
            time_diff = now - pub_dt
            
            if time_diff.days == 0:
                return 'today'
            elif time_diff.days == 1:
                return 'yesterday'
            elif time_diff.days <= 7:
                return 'this_week'
            elif time_diff.days <= 30:
                return 'this_month'
            else:
                return 'older'
                
        except Exception as e:
            logger.warning(f"Error determining time bracket: {e}")
            return 'recent'
    
    def get_articles_count(self) -> int:
        """Get total count of articles in database"""
        if not self.is_available():
            return 0
        
        try:
            response = self.supabase_client.table('articles').select(
                'id', count='exact'
            ).eq('ready_for_analysis', True).execute()
            
            return response.count if response.count else 0
            
        except Exception as e:
            logger.error(f"Error getting articles count: {e}")
            return 0
    
    def get_articles_by_category(self, category: str, limit: int = 100) -> List[Dict]:
        """
        Get articles filtered by sport category
        
        Args:
            category (str): Sport category to filter by
            limit (int): Maximum number of articles
            
        Returns:
            list: Filtered articles
        """
        if not self.is_available():
            return []
        
        try:
            response = self.supabase_client.table('articles').select(
                '*'  # Get articles without join initially
            ).eq('ready_for_analysis', True).eq(
                'sport_category', category
            ).order(
                'publish_date', desc=True
            ).limit(limit).execute()
            
            articles = []
            for article_data in response.data or []:
                # Try to get site information if site_id exists
                site_info = {}
                site_id = article_data.get('site_id')
                if site_id:
                    try:
                        site_response = self.supabase_client.table('sites').select(
                            'name, domain'
                        ).eq('id', site_id).limit(1).execute()
                        if site_response.data:
                            site_info = site_response.data[0]
                    except Exception:
                        pass  # Site info is optional
                
                # Add site info to article data
                article_data['sites'] = site_info
                
                formatted_article = self._format_database_article(article_data)
                if formatted_article:
                    articles.append(formatted_article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error loading articles by category {category}: {e}")
            return []
    
    def test_connection(self) -> Dict:
        """Test Supabase connection and return status"""
        if not SUPABASE_AVAILABLE:
            return {
                'success': False,
                'error': 'Supabase library not installed',
                'recommendation': 'Install with: pip install supabase'
            }
        
        if not self.supabase_client:
            return {
                'success': False,
                'error': 'Supabase client not initialized',
                'recommendation': 'Check SPORTS_SUPABASE_URL and SPORTS_SUPABASE_ANON_KEY environment variables'
            }
        
        try:
            # Simple test query
            response = self.supabase_client.table('articles').select('id').limit(1).execute()
            
            return {
                'success': True,
                'message': 'Connection successful',
                'available_articles': self.get_articles_count()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'recommendation': 'Check database connection and credentials'
            }


# Convenience functions
def get_supabase_loader():
    """Get the Supabase articles loader instance"""
    return SupabaseArticlesLoader()


def test_supabase_connection():
    """Test Supabase connection"""
    loader = get_supabase_loader()
    return loader.test_connection()