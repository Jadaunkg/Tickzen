"""
Article Deduplicator - Removes duplicate articles and keeps best source version
Uses multi-field similarity matching to identify duplicate stories from different sources
Handles edge cases: URL variations, title rewording, timezone differences
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher
import json
import hashlib
from datetime import datetime
from dateutil import parser

logger = logging.getLogger(__name__)


class ArticleDeduplicator:
    """Remove duplicate articles while keeping the highest quality source"""
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize deduplicator
        
        Args:
            database_path: Path to articles database (optional)
        """
        self.database_path = database_path
        self.database = {}
        self.removed_ids = set()
        
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to catch variations of same article
        
        Removes query params, trailing slashes, www, protocol
        """
        if not url:
            return ""
        
        url = url.lower().strip()
        # Remove protocol
        if '://' in url:
            url = url.split('://', 1)[1]
        # Remove www
        url = url.replace('www.', '')
        # Remove trailing slash
        url = url.rstrip('/')
        # Remove query params for comparison (but keep base URL)
        if '?' in url:
            url = url.split('?')[0]
        
        return url
    
    def _generate_content_hash(self, title: str, summary: str = "") -> str:
        """Generate hash of article content for fast duplicate detection
        
        Uses title + first 200 chars of summary
        """
        content = f"{title.lower().strip()}{(summary or '').lower()[:200].strip()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _calculate_similarity(self, title1: str, title2: str, summary1: str = "", summary2: str = "") -> float:
        """Calculate similarity between two articles (0.0 to 1.0)
        
        Combines title and summary similarity for better accuracy
        """
        # Normalize strings
        t1 = title1.lower().strip()
        t2 = title2.lower().strip()
        s1 = (summary1 or "").lower().strip()
        s2 = (summary2 or "").lower().strip()
        
        # Exact match
        if t1 == t2:
            return 1.0
        
        # Title similarity (weighted: 70%)
        title_matcher = SequenceMatcher(None, t1, t2)
        title_similarity = title_matcher.ratio()
        
        # Summary similarity (weighted: 30%) - optional if summary exists
        summary_similarity = 0.0
        if s1 and s2:
            summary_matcher = SequenceMatcher(None, s1, s2)
            summary_similarity = summary_matcher.ratio()
        
        # Combine: title is more important than summary
        if s1 and s2:
            overall_similarity = (title_similarity * 0.7) + (summary_similarity * 0.3)
        else:
            overall_similarity = title_similarity
        
        return overall_similarity
    
    def _get_article_quality_score(self, article: Dict) -> float:
        """Calculate quality score for an article
        Higher scores are better sources
        
        Factors:
        1. Source reliability (most important)
        2. Article length/completeness
        3. Importance score
        4. Freshness (newer is better)
        """
        score = 0.0
        
        # Source reliability scores (normalized to 0-10)
        reliable_sources = {
            'bbc': 10, 'bbc sport': 10, 'bbc cricket': 10,
            'cnn': 9, 'reuters': 9, 'ap': 9, 'associated press': 9,
            'guardian': 8, 'ft': 8, 'financial times': 8,
            'espn': 8, 'espncricinfo': 8, 'sky sports': 8, 'sky': 8,
            'independent': 7, 'telegraph': 6, 
            'daily mail': 5, 'mirror': 4, 'sun': 4, 'express': 4
        }
        
        source = article.get('source_name', '').lower()
        source_score = 3  # Default for unknown sources
        for key, val in reliable_sources.items():
            if key in source:
                source_score = val
                break
        
        score += source_score  # Max 10 points
        
        # Content completeness (0-3 points)
        title = article.get('title', '')
        summary = article.get('summary', '') or article.get('description', '')
        
        if len(title) >= 50 and len(summary) >= 100:
            score += 3
        elif len(title) >= 30 and len(summary) >= 50:
            score += 2
        elif len(title) >= 10:
            score += 1
        
        # Importance score (0-3 points)
        importance = article.get('importance_score', 0)
        if importance:
            score += min(importance / 30, 3)  # Normalize to max 3 points
        
        # Freshness bonus (0-2 points) - newer articles preferred
        try:
            pub_date_str = article.get('published_date') or article.get('collected_date')
            if pub_date_str:
                pub_date = parser.parse(pub_date_str)
                age_hours = (datetime.now() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
                
                if age_hours < 1:
                    score += 2  # < 1 hour old
                elif age_hours < 6:
                    score += 1.5  # < 6 hours old
                elif age_hours < 12:
                    score += 1  # < 12 hours old
        except Exception:
            pass  # If date parsing fails, just skip freshness bonus
        
        return score
    
    def deduplicate_articles(self, similarity_threshold: float = 0.75, url_threshold: float = 0.85, backup: bool = True) -> Dict:
        """Remove duplicate articles across sources
        
        Args:
            similarity_threshold: Similarity score needed to consider articles duplicates (0.0-1.0)
                                  Default 0.75 = 75% similar titles/content
            url_threshold: URL similarity threshold for URL-based dedup (0.0-1.0)
            backup: Whether to create a backup before deduplication
            
        Returns:
            Dictionary with deduplication statistics
        """
        if not self.database:
            logger.warning("No articles in database to deduplicate")
            return {'removed_count': 0, 'final_count': 0}
        
        try:
            # Create backup if requested
            if backup and self.database_path:
                try:
                    backup_path = self.database_path.replace('.json', '_backup.json')
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(self.database, f, indent=2, ensure_ascii=False)
                    logger.info(f"Created backup at {backup_path}")
                except Exception as e:
                    logger.warning(f"Could not create backup: {e}")
            
            initial_count = len(self.database)
            articles_by_type = {}
            
            # Group articles by type (cricket, football, basketball, etc.)
            for article_id, article in self.database.items():
                article_type = article.get('category', 'general')
                if article_type not in articles_by_type:
                    articles_by_type[article_type] = {}
                articles_by_type[article_type][article_id] = article
            
            # Deduplicate within each category
            for category, articles in articles_by_type.items():
                article_list = list(articles.items())
                
                # Build lookup for URLs (normalized)
                url_lookup = {}
                for article_id, article in article_list:
                    url = article.get('link', '') or article.get('url', '')
                    if url:
                        norm_url = self._normalize_url(url)
                        if norm_url not in url_lookup:
                            url_lookup[norm_url] = []
                        url_lookup[norm_url].append(article_id)
                
                # Mark URL-exact duplicates (same URL = same article)
                for norm_url, id_list in url_lookup.items():
                    if len(id_list) > 1:
                        # Keep article with best quality score, remove others
                        best_id = max(id_list, key=lambda aid: self._get_article_quality_score(article_list[next(i for i, (aid2, _) in enumerate(article_list) if aid2 == aid)][1]))
                        
                        for aid in id_list:
                            if aid != best_id:
                                self.removed_ids.add(aid)
                                logger.debug(f"Removed URL duplicate: {aid} (kept: {best_id})")
                
                # Compare articles for title/content similarity
                for i in range(len(article_list)):
                    article_id1, article1 = article_list[i]
                    
                    if article_id1 in self.removed_ids:
                        continue
                    
                    title1 = article1.get('title', '')
                    summary1 = article1.get('summary', '')
                    
                    # Compare with subsequent articles
                    for j in range(i + 1, len(article_list)):
                        article_id2, article2 = article_list[j]
                        
                        if article_id2 in self.removed_ids:
                            continue
                        
                        title2 = article2.get('title', '')
                        summary2 = article2.get('summary', '')
                        
                        # Calculate similarity
                        similarity = self._calculate_similarity(title1, title2, summary1, summary2)
                        
                        # If similar enough, mark lower quality one as duplicate
                        if similarity >= similarity_threshold:
                            score1 = self._get_article_quality_score(article1)
                            score2 = self._get_article_quality_score(article2)
                            
                            if score1 >= score2:
                                self.removed_ids.add(article_id2)
                                logger.debug(f"Removed content duplicate: {article_id2} (similarity: {similarity:.2f}, kept: {article_id1})")
                            else:
                                self.removed_ids.add(article_id1)
                                logger.debug(f"Removed content duplicate: {article_id1} (similarity: {similarity:.2f}, kept: {article_id2})")
                                break  # Move to next article1
            
            # Remove duplicate articles from database
            for removed_id in self.removed_ids:
                if removed_id in self.database:
                    del self.database[removed_id]
            
            final_count = len(self.database)
            removed_count = initial_count - final_count
            
            logger.info(f"Deduplication complete: {removed_count} duplicates removed, {final_count} articles kept")
            logger.info(f"  Removal rate: {(removed_count/initial_count*100):.1f}%")
            
            return {
                'initial_count': initial_count,
                'removed_count': removed_count,
                'final_count': final_count,
                'similarity_threshold': similarity_threshold,
                'url_threshold': url_threshold
            }
            
        except Exception as e:
            logger.error(f"Error during deduplication: {e}")
            return {'removed_count': 0, 'final_count': len(self.database), 'error': str(e)}
