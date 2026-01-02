"""
Advanced Article Filtering System for Sports Content
Filters articles based on multiple criteria to select best candidates for publishing

Filtering Criteria:
1. Category (Cricket, Football, Basketball - ONLY these 3)
2. Importance Score/Tier (Critical, High, Medium, Low, Minimal)
3. Recency (Last 24h, 12h, 6h, 3h)
4. Source Authority (Premium, Standard, Low)
5. Content Type (Breaking News, Transfer, Match Report, etc.)
6. Keyword Presence (specific topics)
7. Team/Player Popularity
8. Duplicate Detection
9. Publishing Readiness (has all required fields)

Usage:
    filter = ArticleFilter()
    filtered = filter.filter_articles(articles, criteria={...})
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dateutil import parser
import re

class ArticleFilter:
    """Advanced filtering system for sports articles"""
    
    # Only these 3 categories are allowed
    ALLOWED_CATEGORIES = {'cricket', 'football', 'basketball'}
    
    # Importance tiers
    IMPORTANCE_TIERS = {
        'critical': {'min_score': 8.0, 'label': 'Critical'},
        'high': {'min_score': 6.0, 'label': 'High'},
        'medium': {'min_score': 4.0, 'label': 'Medium'},
        'low': {'min_score': 2.0, 'label': 'Low'},
        'minimal': {'min_score': 0.0, 'label': 'Minimal'}
    }
    
    # Source authority levels
    SOURCE_AUTHORITY = {
        'premium': {
            'sources': ['bbc sport', 'bbc cricket', 'bbc', 'espn', 'espncricinfo', 
                       'sky sports', 'the athletic', 'guardian', 'reuters', 'ap'],
            'min_score': 8
        },
        'standard': {
            'sources': ['yahoo sports', 'goal.com', 'talksport', 'espn fc', 
                       'sky sports football', 'cricinfo'],
            'min_score': 5
        },
        'low': {
            'sources': ['mirror', 'sun', 'daily mail', 'express'],
            'min_score': 3
        }
    }
    
    # Content types and their importance
    CONTENT_TYPES = {
        'breaking': {'keywords': ['breaking', 'urgent', 'confirmed', 'official'], 'priority': 10},
        'transfer': {'keywords': ['transfer', 'signing', 'deal', 'bid', 'move'], 'priority': 9},
        'injury': {'keywords': ['injury', 'injured', 'out', 'surgery', 'medical'], 'priority': 8},
        'match_result': {'keywords': ['win', 'loss', 'defeat', 'victory', 'score'], 'priority': 7},
        'controversy': {'keywords': ['scandal', 'banned', 'suspended', 'investigation'], 'priority': 9},
        'record': {'keywords': ['record', 'milestone', 'achievement', 'historic'], 'priority': 7},
        'preview': {'keywords': ['preview', 'prediction', 'upcoming', 'fixture'], 'priority': 4},
        'analysis': {'keywords': ['analysis', 'opinion', 'review', 'tactical'], 'priority': 5}
    }
    
    def __init__(self):
        """Initialize the article filter"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def filter_articles(self, articles: List[Dict], criteria: Dict) -> List[Dict]:
        """
        Filter articles based on multiple criteria
        
        Args:
            articles: List of article dictionaries
            criteria: Dictionary with filtering criteria
                - categories: List of categories (cricket, football, basketball)
                - importance_tiers: List of importance tiers
                - max_age_hours: Maximum article age in hours
                - source_authority: List of authority levels (premium, standard, low)
                - content_types: List of content types
                - min_importance_score: Minimum importance score
                - keywords_include: List of keywords that must be present
                - keywords_exclude: List of keywords to exclude
                - limit: Maximum number of articles to return
                - sort_by: Field to sort by (importance_score, published_date, hybrid_rank)
                - require_complete: Only articles with all required fields
        
        Returns:
            List of filtered articles
        """
        filtered = articles.copy()
        
        self.logger.info(f"Starting filter with {len(filtered)} articles")
        self.logger.info(f"Filter criteria: {criteria}")
        
        # Step 1: Category filter (STRICT - only allowed categories)
        filtered = self._filter_by_category(filtered, criteria.get('categories'))
        self.logger.info(f"After category filter: {len(filtered)} articles")
        
        # Step 2: Importance tier filter
        filtered = self._filter_by_importance_tier(filtered, criteria.get('importance_tiers'))
        self.logger.info(f"After importance tier filter: {len(filtered)} articles")
        
        # Step 3: Recency filter
        max_age = criteria.get('max_age_hours')
        if max_age:
            filtered = self._filter_by_recency(filtered, max_age)
            self.logger.info(f"After recency filter ({max_age}h): {len(filtered)} articles")
        
        # Step 4: Source authority filter
        filtered = self._filter_by_source_authority(filtered, criteria.get('source_authority'))
        self.logger.info(f"After source authority filter: {len(filtered)} articles")
        
        # Step 5: Content type filter
        filtered = self._filter_by_content_type(filtered, criteria.get('content_types'))
        self.logger.info(f"After content type filter: {len(filtered)} articles")
        
        # Step 6: Minimum importance score
        min_score = criteria.get('min_importance_score')
        if min_score:
            filtered = self._filter_by_min_score(filtered, min_score)
            self.logger.info(f"After min score filter ({min_score}): {len(filtered)} articles")
        
        # Step 7: Keyword inclusion filter
        keywords_include = criteria.get('keywords_include')
        if keywords_include:
            filtered = self._filter_by_keywords_include(filtered, keywords_include)
            self.logger.info(f"After keyword inclusion filter: {len(filtered)} articles")
        
        # Step 8: Keyword exclusion filter
        keywords_exclude = criteria.get('keywords_exclude')
        if keywords_exclude:
            filtered = self._filter_by_keywords_exclude(filtered, keywords_exclude)
            self.logger.info(f"After keyword exclusion filter: {len(filtered)} articles")
        
        # Step 9: Publishing readiness filter
        if criteria.get('require_complete', False):
            filtered = self._filter_by_completeness(filtered)
            self.logger.info(f"After completeness filter: {len(filtered)} articles")
        
        # Step 10: Remove duplicates
        filtered = self._remove_duplicates(filtered)
        self.logger.info(f"After duplicate removal: {len(filtered)} articles")
        
        # Step 11: Sort articles
        sort_by = criteria.get('sort_by', 'hybrid_rank')
        filtered = self._sort_articles(filtered, sort_by)
        
        # Step 12: Limit results
        limit = criteria.get('limit')
        if limit and len(filtered) > limit:
            filtered = filtered[:limit]
            self.logger.info(f"After limit ({limit}): {len(filtered)} articles")
        
        return filtered
    
    def _filter_by_category(self, articles: List[Dict], categories: Optional[List[str]]) -> List[Dict]:
        """Filter by category - ONLY cricket, football, basketball allowed"""
        if not categories:
            # Default: all allowed categories
            categories = list(self.ALLOWED_CATEGORIES)
        
        # Ensure only allowed categories
        categories = [cat.lower() for cat in categories if cat.lower() in self.ALLOWED_CATEGORIES]
        
        if not categories:
            self.logger.warning("No valid categories specified, using all allowed categories")
            categories = list(self.ALLOWED_CATEGORIES)
        
        return [a for a in articles if a.get('category', '').lower() in categories]
    
    def _filter_by_importance_tier(self, articles: List[Dict], tiers: Optional[List[str]]) -> List[Dict]:
        """Filter by importance tier"""
        if not tiers:
            return articles
        
        tiers = [t.lower() for t in tiers]
        return [a for a in articles if a.get('importance_tier', '').lower() in tiers]
    
    def _filter_by_recency(self, articles: List[Dict], max_age_hours: int) -> List[Dict]:
        """Filter articles by maximum age
        
        Handles:
        - Missing dates (keeps article with warning)
        - Multiple date formats
        - Timezone-aware datetimes
        """
        from dateutil.tz import UTC
        
        cutoff_time = datetime.now(UTC) - timedelta(hours=max_age_hours)
        filtered = []
        unparseable_count = 0
        
        for article in articles:
            pub_date_str = article.get('published_date') or article.get('collected_date')
            
            if not pub_date_str:
                # No date field - keep article to avoid data loss
                self.logger.warning(f"Article '{article.get('title', '')[:50]}' has no date, keeping it")
                filtered.append(article)
                continue
            
            try:
                # Parse date with flexible parser
                pub_date = parser.parse(pub_date_str)
                
                # Normalize to UTC if timezone-aware
                if pub_date.tzinfo is not None:
                    pub_date = pub_date.astimezone(UTC)
                else:
                    pub_date = pub_date.replace(tzinfo=UTC)
                
                # Check recency
                if pub_date >= cutoff_time:
                    filtered.append(article)
                # else: article is older than threshold, exclude it
                    
            except Exception as e:
                # Date parsing failed - keep article to avoid data loss
                unparseable_count += 1
                self.logger.warning(f"Could not parse date '{pub_date_str}' for article '{article.get('title', '')[:50]}': {e}. Keeping article.")
                filtered.append(article)
        
        if unparseable_count > 0:
            self.logger.info(f"Recency filter: {unparseable_count} articles with unparseable dates were kept")
        
        return filtered
    
    def _filter_by_source_authority(self, articles: List[Dict], authority_levels: Optional[List[str]]) -> List[Dict]:
        """Filter by source authority level"""
        if not authority_levels:
            return articles
        
        allowed_sources = []
        for level in authority_levels:
            if level.lower() in self.SOURCE_AUTHORITY:
                allowed_sources.extend(self.SOURCE_AUTHORITY[level.lower()]['sources'])
        
        if not allowed_sources:
            return articles
        
        filtered = []
        for article in articles:
            source = article.get('source_name', '').lower()
            if any(allowed in source for allowed in allowed_sources):
                filtered.append(article)
        
        return filtered
    
    def _filter_by_content_type(self, articles: List[Dict], content_types: Optional[List[str]]) -> List[Dict]:
        """Filter by content type"""
        if not content_types:
            return articles
        
        keywords_to_match = []
        for ctype in content_types:
            if ctype.lower() in self.CONTENT_TYPES:
                keywords_to_match.extend(self.CONTENT_TYPES[ctype.lower()]['keywords'])
        
        if not keywords_to_match:
            return articles
        
        filtered = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            if any(keyword in text for keyword in keywords_to_match):
                filtered.append(article)
        
        return filtered
    
    def _filter_by_min_score(self, articles: List[Dict], min_score: float) -> List[Dict]:
        """Filter by minimum importance score"""
        return [a for a in articles if a.get('importance_score', 0) >= min_score]
    
    def _filter_by_keywords_include(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """Include only articles containing specified keywords"""
        keywords_lower = [k.lower() for k in keywords]
        
        filtered = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            if any(keyword in text for keyword in keywords_lower):
                filtered.append(article)
        
        return filtered
    
    def _filter_by_keywords_exclude(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """Exclude articles containing specified keywords"""
        keywords_lower = [k.lower() for k in keywords]
        
        filtered = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            if not any(keyword in text for keyword in keywords_lower):
                filtered.append(article)
        
        return filtered
    
    def _filter_by_completeness(self, articles: List[Dict]) -> List[Dict]:
        """Filter articles that have all required fields for publishing
        
        Required fields:
        - title: Article headline (min 10 chars)
        - url/link: Article URL
        - category: Sport category (cricket, football, basketball)
        - published_date or collected_date: Publication timestamp
        - source_name: Source of the article
        """
        required_fields = ['title', 'category', 'source_name']
        url_fields = ['link', 'url']
        date_fields = ['published_date', 'collected_date']
        
        filtered = []
        for article in articles:
            # Check required fields
            if not all(article.get(field) for field in required_fields):
                continue
            
            # Check title length
            if len(article.get('title', '')) < 10:
                continue
            
            # Check URL exists (in either 'link' or 'url' field)
            if not any(article.get(field) for field in url_fields):
                continue
            
            # Check date exists (in either 'published_date' or 'collected_date')
            if not any(article.get(field) for field in date_fields):
                continue
            
            filtered.append(article)
        
        return filtered
    
    def _remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on intelligent matching
        
        Strategy:
        1. First: Exact URL matching (fastest, most accurate)
        2. Second: Title+Summary similarity (catches rewrites)
        3. Fallback: Normalized title matching (catches variations)
        """
        if not articles:
            return []
        
        from difflib import SequenceMatcher
        import hashlib
        
        unique_articles = []
        seen_urls = set()
        seen_title_hashes = {}
        
        # Pass 1: Deduplicate by URL (exact matches and normalized)
        for article in articles:
            url = article.get('link', '') or article.get('url', '')
            
            if url:
                # Normalize URL for comparison
                norm_url = self._normalize_url(url)
                
                if norm_url not in seen_urls:
                    seen_urls.add(norm_url)
                    seen_title_hashes[article.get('title', '')] = article
                    unique_articles.append(article)
            else:
                # No URL, use title-based dedup
                title = article.get('title', '').lower().strip()
                
                # Check for similar titles
                is_duplicate = False
                for seen_title, seen_article in seen_title_hashes.items():
                    if self._are_articles_duplicate(article, seen_article):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    seen_title_hashes[title] = article
                    unique_articles.append(article)
        
        return unique_articles
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication"""
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
        # Remove query params
        if '?' in url:
            url = url.split('?')[0]
        
        return url
    
    def _are_articles_duplicate(self, article1: Dict, article2: Dict, threshold: float = 0.75) -> bool:
        """Check if two articles are duplicates based on title and summary similarity"""
        title1 = article1.get('title', '').lower().strip()
        title2 = article2.get('title', '').lower().strip()
        
        # Exact title match
        if title1 == title2:
            return True
        
        # Title similarity
        matcher = SequenceMatcher(None, title1, title2)
        title_sim = matcher.ratio()
        
        if title_sim >= threshold:
            return True
        
        # Check summary similarity if available
        summary1 = article1.get('summary', '').lower().strip()[:200]
        summary2 = article2.get('summary', '').lower().strip()[:200]
        
        if summary1 and summary2:
            summary_matcher = SequenceMatcher(None, summary1, summary2)
            summary_sim = summary_matcher.ratio()
            
            # Both title and summary similar = duplicate
            if title_sim >= 0.6 and summary_sim >= 0.7:
                return True
        
        return False
    
    def _sort_articles(self, articles: List[Dict], sort_by: str) -> List[Dict]:
        """Sort articles by specified field"""
        if sort_by == 'importance_score':
            return sorted(articles, key=lambda x: x.get('importance_score', 0), reverse=True)
        elif sort_by == 'published_date':
            return sorted(articles, key=lambda x: x.get('published_date', ''), reverse=True)
        elif sort_by == 'hybrid_rank':
            # Hybrid: newest first, then by importance within time brackets
            return sorted(articles, 
                         key=lambda x: (x.get('time_bracket', 0), -x.get('importance_score', 0)), 
                         reverse=False)
        else:
            return articles
    
    def get_filter_summary(self, articles: List[Dict]) -> Dict:
        """Get summary statistics of filtered articles"""
        if not articles:
            return {
                'total': 0,
                'by_category': {},
                'by_importance': {},
                'by_source_authority': {},
                'by_content_type': {},
                'avg_importance_score': 0
            }
        
        summary = {
            'total': len(articles),
            'by_category': {},
            'by_importance': {},
            'by_source_authority': {},
            'by_content_type': {},
            'avg_importance_score': sum(a.get('importance_score', 0) for a in articles) / len(articles)
        }
        
        # Count by category
        for article in articles:
            cat = article.get('category', 'unknown')
            summary['by_category'][cat] = summary['by_category'].get(cat, 0) + 1
            
            # Count by importance tier
            tier = article.get('importance_tier', 'Minimal')
            summary['by_importance'][tier] = summary['by_importance'].get(tier, 0) + 1
        
        return summary
    
    def create_preset_filter(self, preset_name: str) -> Dict:
        """
        Create predefined filter configurations
        
        Presets:
        - 'publish_ready': High-quality, recent articles ready for publishing
        - 'breaking_news': Critical breaking news only
        - 'transfers': Transfer news and rumors
        - 'match_day': Match results and reports
        - 'premium_only': Only from premium sources
        - 'last_24h': All articles from last 24 hours
        """
        presets = {
            'publish_ready': {
                'categories': ['cricket', 'football', 'basketball'],
                'importance_tiers': ['critical', 'high'],
                'max_age_hours': 24,
                'source_authority': ['premium', 'standard'],
                'min_importance_score': 6.0,
                'require_complete': True,
                'sort_by': 'hybrid_rank',
                'limit': 50
            },
            'breaking_news': {
                'categories': ['cricket', 'football', 'basketball'],
                'importance_tiers': ['critical'],
                'max_age_hours': 6,
                'content_types': ['breaking', 'transfer', 'controversy'],
                'min_importance_score': 7.0,
                'sort_by': 'published_date',
                'limit': 20
            },
            'transfers': {
                'categories': ['cricket', 'football', 'basketball'],
                'content_types': ['transfer'],
                'max_age_hours': 48,
                'min_importance_score': 5.0,
                'sort_by': 'importance_score',
                'limit': 30
            },
            'match_day': {
                'categories': ['cricket', 'football', 'basketball'],
                'content_types': ['match_result'],
                'max_age_hours': 12,
                'min_importance_score': 4.0,
                'sort_by': 'published_date',
                'limit': 40
            },
            'premium_only': {
                'categories': ['cricket', 'football', 'basketball'],
                'source_authority': ['premium'],
                'max_age_hours': 24,
                'min_importance_score': 5.0,
                'require_complete': True,
                'sort_by': 'hybrid_rank',
                'limit': 50
            },
            'last_24h': {
                'categories': ['cricket', 'football', 'basketball'],
                'max_age_hours': 24,
                'sort_by': 'published_date',
                'limit': 100
            }
        }
        
        return presets.get(preset_name, {})


if __name__ == "__main__":
    # Example usage
    filter_system = ArticleFilter()
    
    # Test with sample articles
    sample_articles = [
        {
            'title': 'BREAKING: Manchester United sign new striker',
            'category': 'football',
            'importance_score': 8.5,
            'importance_tier': 'Critical',
            'published_date': datetime.now().isoformat(),
            'source_name': 'BBC Sport',
            'url': 'http://example.com/1'
        },
        {
            'title': 'Cricket: India vs Australia preview',
            'category': 'cricket',
            'importance_score': 5.0,
            'importance_tier': 'Medium',
            'published_date': (datetime.now() - timedelta(hours=2)).isoformat(),
            'source_name': 'ESPN Cricinfo',
            'url': 'http://example.com/2'
        }
    ]
    
    # Test publish_ready preset
    criteria = filter_system.create_preset_filter('publish_ready')
    filtered = filter_system.filter_articles(sample_articles, criteria)
    
    print(f"\nFiltered {len(filtered)} articles for publishing:")
    for article in filtered:
        print(f"  - {article['title']} ({article['category']}, score: {article['importance_score']})")
    
    print("\nFilter Summary:")
    summary = filter_system.get_filter_summary(filtered)
    print(json.dumps(summary, indent=2))
