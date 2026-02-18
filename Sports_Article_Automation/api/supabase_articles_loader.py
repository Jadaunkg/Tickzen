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
    
    def load_article_links(self, category: str = None, limit: int = None) -> List[Dict]:
        """
        Load articles from the article_links table
        
        Args:
            category (str): Sport category to filter by (optional)
            limit (int): Maximum number of articles to load (None for all articles)
            
        Returns:
            list: List of articles from the article_links table
        """
        if not self.is_available():
            logger.warning("Supabase client not available")
            return []
        
        try:
            # Query article_links from Supabase with proper ordering
            query = self.supabase_client.table('article_links').select(
                '*'
            ).order(
                'published_at', desc=True
            )
            
            # Add category filter if specified
            if category:
                standardized_category = self._standardize_sport_category(category)
                query = query.eq('sport_category', standardized_category)
            
            # Only apply limit if specified
            if limit is not None:
                query = query.limit(limit)
            
            response = query.execute()
            
            if not response.data:
                category_info = f" for category: {category}" if category else ""
                logger.info(f"No article_links found in Supabase database{category_info}")
                return []
            
            # Format articles
            articles = []
            for article_data in response.data:
                # Convert article_links to format compatible with existing system
                formatted_article = self._format_article_links_article(article_data)
                if formatted_article:
                    articles.append(formatted_article)
            
            category_info = f" for category: {category}" if category else ""
            logger.info(f"Loaded {len(articles)} articles from article_links table{category_info}")
            return articles
            
        except Exception as e:
            category_info = f" for category {category}" if category else ""
            logger.error(f"Error loading article_links from Supabase{category_info}: {e}")
            return []

    def load_database_articles_by_category(self, sport_category: str, limit: int = None) -> List[Dict]:
        """
        Load articles from article_links table filtered by sport category
        
        Args:
            sport_category (str): Sport category to filter by (e.g., 'cricket', 'football', 'basketball')
            limit (int): Maximum number of articles to load (None for all articles)
            
        Returns:
            list: List of articles from article_links table for the specified category
        """
        if not self.is_available():
            logger.warning("Supabase client not available")
            return []
        
        try:
            # Standardize the category name for querying
            standardized_category = self._standardize_sport_category(sport_category)
            
            # Load only from article_links table
            article_links_data = self.load_article_links(standardized_category, limit)
            
            logger.info(f"Loaded articles for category '{standardized_category}': {len(article_links_data)} from article_links table")
            return article_links_data
            
        except Exception as e:
            logger.error(f"Error loading articles from article_links for category {sport_category}: {e}")
            return []
            
    def _load_articles_table_by_category(self, sport_category: str, limit: int = None) -> List[Dict]:
        """
        Load articles from the original articles table filtered by sport category
        
        Args:
            sport_category (str): Sport category to filter by
            limit (int): Maximum number of articles to load (None for all articles)
            
        Returns:
            list: List of articles from the articles table for the specified category
        """
        try:
            # Query articles from Supabase with proper ordering and category filter
            query = self.supabase_client.table('articles').select(
                '*'
            ).eq('ready_for_analysis', True).eq(
                'sport_category', sport_category
            ).order(
                'publish_date', desc=True
            )
            
            # Only apply limit if specified
            if limit is not None:
                query = query.limit(limit)
            
            response = query.execute()
            
            if not response.data:
                logger.info(f"No articles found in articles table for category: {sport_category}")
                return []
            
            # Format articles
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
            
            logger.info(f"Loaded {len(articles)} articles from articles table for category: {sport_category}")
            return articles
            
        except Exception as e:
            logger.error(f"Error loading articles table for category {sport_category}: {e}")
            return []
    
    def load_database_articles(self, limit: int = None) -> List[Dict]:
        """
        Load articles from article_links table in Supabase database
        
        Args:
            limit (int): Maximum number of articles to load (None for all articles)
            
        Returns:
            list: List of articles from article_links table
        """
        if not self.is_available():
            logger.warning("Supabase client not available")
            return []
        
        try:
            # Load only from article_links table
            article_links_data = self.load_article_links(limit=limit)
            
            logger.info(f"Loaded articles from database: {len(article_links_data)} from article_links table")
            return article_links_data
            
        except Exception as e:
            logger.error(f"Error loading articles from Supabase: {e}")
            return []
            
    def _load_articles_table(self, limit: int = None) -> List[Dict]:
        """
        Load articles from the original articles table
        
        Args:
            limit (int): Maximum number of articles to load (None for all articles)
            
        Returns:
            list: List of articles from the articles table
        """
        try:
            # Query articles from Supabase with proper ordering
            query = self.supabase_client.table('articles').select(
                '*'
            ).eq('ready_for_analysis', True).order(
                'publish_date', desc=True
            )
            
            # Only apply limit if specified
            if limit is not None:
                query = query.limit(limit)
            
            response = query.execute()
            
            if not response.data:
                logger.info("No articles found in articles table")
                return []
            
            # Format articles
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
                
                # Convert article to format compatible with existing system
                formatted_article = self._format_database_article(article_data)
                if formatted_article:
                    articles.append(formatted_article)
            
            logger.info(f"Loaded {len(articles)} articles from articles table")
            return articles
            
        except Exception as e:
            logger.error(f"Error loading articles table: {e}")
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
                
                # Categorization - standardize sport categories
                'category': self._standardize_sport_category(article_data.get('sport_category', 'UNCATEGORIZED')),
                'sport_category': self._standardize_sport_category(article_data.get('sport_category', 'UNCATEGORIZED')),
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
    
    def _format_article_links_article(self, article_data: Dict) -> Optional[Dict]:
        """
        Format article_links data to match existing article format
        
        Args:
            article_data (dict): Raw article data from article_links table
            
        Returns:
            dict: Formatted article data
        """
        try:
            # Parse and format dates - article_links uses different field names
            published_at = article_data.get('published_at')
            first_seen_at = article_data.get('first_seen_at')
            last_modified = article_data.get('last_modified')
            
            # Format published date with timezone handling
            formatted_publish_date = None
            display_date_ist = None
            display_date_iso = None
            published_date_parsed = None
            
            # Use published_at as the primary date field
            if published_at:
                try:
                    # Parse the datetime string
                    if isinstance(published_at, str):
                        pub_dt = parser.parse(published_at)
                    else:
                        pub_dt = published_at
                    
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
                    logger.warning(f"Error parsing published_at for article {article_data.get('id')}: {e}")
            
            # Handle first_seen_at as fallback date
            first_seen_ist = None
            if first_seen_at:
                try:
                    if isinstance(first_seen_at, str):
                        first_seen_dt = parser.parse(first_seen_at)
                    else:
                        first_seen_dt = first_seen_at
                    
                    if first_seen_dt.tzinfo is None:
                        first_seen_dt = first_seen_dt.replace(tzinfo=self.utc)
                    
                    first_seen_ist_dt = first_seen_dt.astimezone(self.ist)
                    first_seen_ist = first_seen_ist_dt.strftime('%Y-%m-%d %H:%M:%S IST')
                except Exception as e:
                    logger.warning(f"Error parsing first_seen_at for article {article_data.get('id')}: {e}")
                    first_seen_ist = str(first_seen_at)
            
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
                
                # Categorization - standardize sport categories
                'category': self._standardize_sport_category(article_data.get('sport_category', 'UNCATEGORIZED')),
                'sport_category': self._standardize_sport_category(article_data.get('sport_category', 'UNCATEGORIZED')),
                'source': article_data.get('source_site', 'Unknown Source'),
                'source_name': article_data.get('source_site', 'Unknown Source'),
                'source_site': article_data.get('source_site', 'Unknown Source'),
                'source_domain': '', # Could extract from URL if needed
                
                # Dates (multiple formats for compatibility)
                'published_date': formatted_publish_date,
                'published_date_parsed': published_date_parsed,  # For sorting
                'published_date_ist': display_date_ist,
                'display_date_ist': display_date_ist,
                'display_date_iso': display_date_iso,
                'published_time': display_date_ist,  # This field is used in the UI template
                'collected_date': first_seen_ist or first_seen_at,
                'collected_date_parsed': published_date_parsed,  # For time bracket calculation
                'crawl_time': first_seen_ist or first_seen_at,
                
                # Metadata for UI display
                'importance_tier': self._calculate_importance_tier(article_data),
                'importance_score': self._calculate_importance_score(article_data),
                'time_bracket': self._determine_time_bracket(published_date_parsed),
                
                # Source type identifier
                'data_source': 'article_links',  # This identifies articles from the new table
                'source_type': 'supabase_article_links',
                
                # Additional metadata
                'last_modified': last_modified,
                'first_seen_at': first_seen_at,
                'site_id': article_data.get('site_id'),
            }
            
            return formatted_article
            
        except Exception as e:
            logger.error(f"Error formatting article_links data: {e}")
            return None
    
    def _get_sort_date(self, article: Dict):
        """
        Get sort date for an article, handling different date field names from both tables
        
        Args:
            article (dict): Formatted article data
            
        Returns:
            datetime: Parsed datetime object for sorting, or epoch if no valid date
        """
        try:
            # Try parsed date first
            parsed_date = article.get('published_date_parsed')
            if parsed_date:
                return parsed_date
            
            # Try other date fields
            date_str = (article.get('published_date_ist') or 
                       article.get('published_date') or 
                       article.get('collected_date') or '')
            
            if date_str and isinstance(date_str, str):
                try:
                    parsed = parser.parse(date_str)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=self.utc)
                    return parsed
                except:
                    pass
            
            # Fallback to epoch (oldest possible)
            return datetime.min.replace(tzinfo=self.utc)
            
        except:
            return datetime.min.replace(tzinfo=self.utc)
    
    def _standardize_sport_category(self, category: str) -> str:
        """Standardize sport category names to match the system's expected categories"""
        if not category:
            return 'UNCATEGORIZED'
        
        category_lower = category.lower().strip()
        
        # Map common variations to standard category names
        category_mappings = {
            'cricket': 'CRICKET',
            'football': 'FOOTBALL',
            'soccer': 'FOOTBALL',
            'basketball': 'BASKETBALL',
            'tennis': 'TENNIS',
            'hockey': 'HOCKEY',
            'baseball': 'BASEBALL',
            'rugby': 'RUGBY',
            'golf': 'GOLF',
            'volleyball': 'VOLLEYBALL',
            'badminton': 'BADMINTON',
            'swimming': 'SWIMMING',
            'athletics': 'ATHLETICS',
            'boxing': 'BOXING',
            'mma': 'MMA',
            'motorsport': 'MOTORSPORT',
            'racing': 'MOTORSPORT',
            'f1': 'MOTORSPORT',
            'formula 1': 'MOTORSPORT',
        }
        
        # Return standardized category or the original uppercased if not in mapping
        return category_mappings.get(category_lower, category.upper())
    
    def _extract_summary(self, content: str, max_length: int = 200) -> str:
        """Extract summary from article content"""
        if not content:
            return "No summary available"
        
        # Simple text cleaning and truncation
        try:
            # Only use BeautifulSoup if content looks like HTML
            if '<' in content and '>' in content:
                from bs4 import BeautifulSoup
                # Remove HTML tags if present
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text()
            else:
                # Content is likely plain text
                text = content
            
            # Clean and truncate
            text = ' '.join(text.split())  # Remove extra whitespace
            if len(text) > max_length:
                text = text[:max_length] + '...'
            
            return text if text else "No summary available"
        except Exception as e:
            logger.warning(f"Error extracting summary: {e}")
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
        """Get total count of articles from article_links table only"""
        if not self.is_available():
            return 0
        
        try:
            # Count only from article_links table
            article_links_response = self.supabase_client.table('article_links').select(
                'id', count='exact'
            ).execute()
            
            article_links_count = article_links_response.count if article_links_response.count else 0
            
            logger.info(f"Total articles count: {article_links_count} from article_links table")
            
            return article_links_count
            
        except Exception as e:
            logger.error(f"Error getting articles count: {e}")
            return 0

    def get_articles_by_category(self, category: str, limit: int = 100) -> List[Dict]:
        """
        Get articles from both tables filtered by sport category
        
        Args:
            category (str): Sport category to filter by
            limit (int): Maximum number of articles
            
        Returns:
            list: Filtered articles from both tables
        """
        if not self.is_available():
            return []
        
        # Use the existing method that already combines both tables
        return self.load_database_articles_by_category(category, limit)
    def test_connection(self) -> Dict:
        """Test Supabase connection and return status for article_links table"""
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
            # Test only article_links table
            article_links_response = self.supabase_client.table('article_links').select('id').limit(1).execute()
            
            total_count = self.get_articles_count()
            
            return {
                'success': True,
                'message': 'Connection successful to article_links table',
                'available_articles': total_count,
                'tables_accessible': ['article_links']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'recommendation': 'Check database connection and credentials for article_links table'
            }


# Convenience functions
def get_supabase_loader():
    """Get the Supabase articles loader instance"""
    return SupabaseArticlesLoader()


def test_supabase_connection():
    """Test Supabase connection"""
    loader = get_supabase_loader()
    return loader.test_connection()