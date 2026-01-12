"""
Google Trends API Loader
Provides access to Google Trends database for the automation system
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger("GoogleTrendsAPI")


def get_google_trends_loader():
    """
    Get the Google Trends loader instance
    
    Returns:
        GoogleTrendsLoader: An instance of the Google Trends loader
    """
    return GoogleTrendsLoader()


class GoogleTrendsLoader:
    """Loader for Google Trends data"""
    
    def __init__(self):
        """Initialize the Google Trends loader"""
        self.project_root = Path(__file__).parent.parent
        self.trends_db_path = self.project_root / "google_trends_database.json"
        
    def get_trending_topics(self, limit: Optional[int] = None, category: Optional[str] = None) -> List[Dict]:
        """
        Load trending topics from the Google Trends database
        
        Args:
            limit (int, optional): Maximum number of trends to return
            category (str, optional): Filter by category (e.g., 'sports')
            
        Returns:
            list: List of trending topics with their metadata
        """
        if not self.trends_db_path.exists():
            logger.warning(f"Google Trends database not found: {self.trends_db_path}")
            return []
        
        try:
            with open(self.trends_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract trends list
            trends = data.get('trends', [])
            
            if not trends:
                logger.warning("No trends found in database")
                return []
            
            # Filter by category if specified
            if category:
                trends = [t for t in trends if t.get('category', '').lower() == category.lower()]
            
            # Sort by rank or importance_score
            trends.sort(key=lambda x: (x.get('rank', 999), -x.get('importance_score', 0)))
            
            # Apply limit if specified
            if limit:
                trends = trends[:limit]
            
            logger.info(f"Loaded {len(trends)} trending topics from database")
            return trends
            
        except Exception as e:
            logger.error(f"Error loading Google Trends database: {e}")
            return []
    
    def get_trends_count(self, category: Optional[str] = None) -> int:
        """
        Get count of trending topics
        
        Args:
            category (str, optional): Filter by category
            
        Returns:
            int: Number of trending topics
        """
        trends = self.get_trending_topics(category=category)
        return len(trends)
    
    def get_latest_collection_date(self) -> Optional[str]:
        """
        Get the latest collection date from the database
        
        Returns:
            str: ISO format date string of latest collection
        """
        trends = self.get_trending_topics(limit=1)
        if trends:
            return trends[0].get('collected_date')
        return None
