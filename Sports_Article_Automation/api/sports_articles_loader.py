"""
Sports Articles Loader module for Sports_Article_Automation

This module provides functions to load and retrieve sports articles
from various sources and databases.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("SportsArticlesLoader")


def get_sports_loader():
    """
    Get the sports articles loader instance
    
    Returns:
        SportsArticlesLoader: An instance of the sports articles loader
    """
    return SportsArticlesLoader()


class SportsArticlesLoader:
    """Loader for sports articles from various sources"""
    
    def __init__(self):
        """Initialize the sports articles loader"""
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "Sports_Article_Automation" / "data"
        
    def load_basketball_articles(self):
        """Load basketball articles from database"""
        return self._load_from_database("basketball_news_database.json")
    
    def load_cricket_articles(self):
        """Load cricket articles from database"""
        return self._load_from_database("cricket_news_database.json")
    
    def load_football_articles(self):
        """Load football articles from database"""
        return self._load_from_database("football_news_database.json")
    
    def load_sports_articles(self):
        """Load all sports articles"""
        return self._load_from_database("sports_news_database.json")
    
    def _load_from_database(self, filename):
        """
        Load articles from a database file
        
        Args:
            filename (str): Name of the database file
            
        Returns:
            list: List of articles from the database
        """
        db_path = self.data_dir / filename
        
        if not db_path.exists():
            logger.warning(f"Database file not found: {db_path}")
            return []
        
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract articles list if it's a dict with 'articles' key
            if isinstance(data, dict) and 'articles' in data:
                return data['articles']
            elif isinstance(data, list):
                return data
            else:
                logger.warning(f"Unexpected data format in {filename}")
                return []
                
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return []
    
    def get_article_count(self, article_type="all"):
        """
        Get count of articles by type
        
        Args:
            article_type (str): Type of articles ('basketball', 'cricket', 'football', 'database', 'all')
            
        Returns:
            int: Number of articles
        """
        if article_type == "basketball":
            articles = self.load_basketball_articles()
        elif article_type == "cricket":
            articles = self.load_cricket_articles()
        elif article_type == "football":
            articles = self.load_football_articles()
        elif article_type == "database":
            articles = self.load_database_articles()
        elif article_type == "all":
            articles = self.load_articles()
        else:
            articles = []
        
        return len(articles)
    
    def load_database_articles(self):
        """Load articles from Supabase database"""
        try:
            # Try different import paths for better compatibility
            try:
                from Sports_Article_Automation.api.supabase_articles_loader import get_supabase_loader
            except ImportError:
                # Try relative import if we're running from within the Sports_Article_Automation directory
                from .supabase_articles_loader import get_supabase_loader
            except ImportError:
                # Try absolute import if that fails
                import sys
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.dirname(current_dir)
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                from api.supabase_articles_loader import get_supabase_loader
            
            supabase_loader = get_supabase_loader()
            
            if supabase_loader.is_available():
                database_articles = supabase_loader.load_database_articles()
                logger.info(f"Successfully loaded {len(database_articles)} articles from database")
                return database_articles
            else:
                logger.warning("Supabase database loader not available")
                return []
                
        except ImportError as e:
            logger.error(f"Could not import Supabase loader: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading database articles: {e}")
            return []
    
    def load_articles(self, category=None, force_refresh=False):
        """
        Load articles by category
        
        Args:
            category (str): Category of articles ('cricket', 'football', 'basketball', 'database', or None for all)
            force_refresh (bool): Force refresh from disk (default: False)
            
        Returns:
            list: List of articles from the specified category
        """
        # Handle database category separately
        if category and category.lower() == 'database':
            return self.load_database_articles()
        
        # First, ensure RSS articles are categorized
        self._ensure_categorized()
        
        if category and category.lower() == 'cricket':
            return self.load_cricket_articles()
        elif category and category.lower() == 'football':
            return self.load_football_articles()
        elif category and category.lower() == 'basketball':
            return self.load_basketball_articles()
        else:
            # Load all sports articles (combines all categories including database)
            logger.info("🔄 Loading all article categories (including database)...")
            
            cricket = self.load_cricket_articles()
            football = self.load_football_articles()
            basketball = self.load_basketball_articles()
            database_articles = self.load_database_articles()
            
            logger.info(f"📊 Category breakdown: Cricket={len(cricket)}, Football={len(football)}, Basketball={len(basketball)}, Database={len(database_articles)}")
            
            # Combine all articles
            all_articles = cricket + football + basketball + database_articles
            
            # Also include uncategorized articles from main RSS database
            main_articles = self.load_sports_articles()
            uncategorized = [a for a in main_articles if a.get('category', 'UNCATEGORIZED') == 'UNCATEGORIZED']
            all_articles.extend(uncategorized)
            
            logger.info(f"📈 Total articles after combining: {len(all_articles)} (including {len(uncategorized)} uncategorized RSS)")
            
            return all_articles
    
    def _ensure_categorized(self):
        """
        Ensure articles are categorized if not already
        Runs categorization on uncategorized articles
        """
        try:
            main_articles = self.load_sports_articles()
            
            # Check if any articles are uncategorized
            uncategorized_count = len([a for a in main_articles if a.get('category', 'UNCATEGORIZED') == 'UNCATEGORIZED'])
            
            if uncategorized_count > 0:
                logger.info(f"🔄 Found {uncategorized_count} uncategorized articles, running categorization...")
                
                from Sports_Article_Automation.utilities.sports_categorizer import SportsNewsCategorizer
                
                categorizer = SportsNewsCategorizer(str(self.data_dir / "sports_news_database.json"))
                
                # Step 1: Categorize articles and save to individual files
                categorizer.categorize_all_articles(save_individual_files=True)
                
                # Step 2: Update main database with category information
                categorizer.update_main_database_with_categories()
                
                logger.info(f"✅ Categorization complete - main database updated")
        except Exception as e:
            logger.warning(f"Could not categorize articles: {e}")
    
    def collect_and_load_articles(self, override_existing=False):
        """
        Collect articles from RSS sources and load them
        
        Args:
            override_existing (bool): Whether to override existing articles
            
        Returns:
            dict: Result with status and article count
        """
        try:
            # Try to use RSS collector
            from Sports_Article_Automation.utilities.rss_analyzer import RSSNewsCollector
            
            csv_path = self.data_dir / "rss_sources.csv"
            db_path = self.data_dir / "sports_news_database.json"
            
            collector = RSSNewsCollector(str(csv_path), str(db_path))
            collector.collect()
            
            # Load the newly collected articles
            articles = self.load_sports_articles()
            
            return {
                'success': True,
                'article_count': len(articles),
                'status': f'Collected and loaded {len(articles)} articles'
            }
        except Exception as e:
            logger.error(f"Error collecting articles: {e}")
            # Fall back to loading existing articles
            articles = self.load_sports_articles()
            return {
                'success': False,
                'article_count': len(articles),
                'status': f'Error during collection, loaded {len(articles)} existing articles',
                'error': str(e)
            }
    
    def sync_articles_to_firebase(self, db, user_uid):
        """
        Sync articles to Firebase
        
        Args:
            db: Firestore database instance
            user_uid (str): User ID for syncing
            
        Returns:
            dict: Result with sync status
        """
        try:
            articles = self.load_sports_articles()
            synced_count = 0
            
            # Sync articles to Firebase
            if articles and db:
                try:
                    # Store articles in Firebase under user's collection
                    user_articles_ref = db.collection('users').document(user_uid).collection('articles')
                    
                    for article in articles[:100]:  # Limit to first 100 articles
                        article_id = article.get('id') or article.get('hash')
                        if article_id:
                            user_articles_ref.document(str(article_id)).set(article, merge=True)
                            synced_count += 1
                    
                    return {
                        'success': True,
                        'synced_count': synced_count,
                        'status': f'Synced {synced_count} articles to Firebase'
                    }
                except Exception as e:
                    logger.warning(f"Could not sync to Firebase: {e}")
                    return {
                        'success': False,
                        'synced_count': 0,
                        'status': 'Could not sync to Firebase',
                        'error': str(e)
                    }
            else:
                return {
                    'success': True,
                    'synced_count': 0,
                    'status': 'No articles to sync'
                }
        except Exception as e:
            logger.error(f"Error syncing articles: {e}")
            return {
                'success': False,
                'synced_count': 0,
                'status': 'Error during sync',
                'error': str(e)
            }


# Create a global instance for convenience
_sports_loader = None


def initialize_loader():
    """Initialize the global sports articles loader"""
    global _sports_loader
    if _sports_loader is None:
        _sports_loader = SportsArticlesLoader()
    return _sports_loader
