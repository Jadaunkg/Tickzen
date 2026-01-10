"""
Advanced Article Filtering System for Sports Content
Filters articles based on multiple criteria to select best candidates for publishing

Filtering Criteria:
1. Category (Cricket, Football, Basketball - ONLY these 3)
2. Minimum Importance Score (0.0-10.0 continuous scale, replaces tier system)
3. Recency (Last 24h, 12h, 6h, 3h)
4. Source Authority (Premium, Standard, Low with secure domain matching)
5. Content Type (Breaking News, Transfer, Match Report, etc.)
6. Keyword Presence (specific topics with AND/OR logic)
7. Duplicate Detection (O(n) optimized with title bucketing)
8. Publishing Readiness (has all required fields)

Usage:
    filter = ArticleFilter(strict_mode=True)  # strict_mode for production
    filtered = filter.filter_articles(articles, criteria={'min_importance_score': 6.0, ...})
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union
from dateutil import parser
from difflib import SequenceMatcher
from urllib.parse import urlparse
import logging
import re

# Configure logging for the module (outside the class to avoid conflicts)
logger = logging.getLogger(__name__)

# Set up logging configuration for production use
# Recommended levels: DEBUG for development, INFO for production, WARNING for minimal output
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # Default to INFO level - can be overridden externally
    logger.setLevel(logging.INFO)

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
    
    # Content types and their keywords
    CONTENT_TYPES = {
        'breaking': {'keywords': ['breaking', 'urgent', 'confirmed', 'official']},
        'transfer': {'keywords': ['transfer', 'signing', 'deal', 'bid', 'move']},
        'injury': {'keywords': ['injury', 'injured', 'out', 'surgery', 'medical']},
        'match_result': {'keywords': ['win', 'loss', 'defeat', 'victory', 'score']},
        'controversy': {'keywords': ['scandal', 'banned', 'suspended', 'investigation']},
        'record': {'keywords': ['record', 'milestone', 'achievement', 'historic']},
        'preview': {'keywords': ['preview', 'prediction', 'upcoming', 'fixture']},
        'analysis': {'keywords': ['analysis', 'opinion', 'review', 'tactical']}
    }
    
    def __init__(self, strict_mode: bool = False):
        """Initialize the article filter
        
        Args:
            strict_mode: If True, drop articles with invalid/missing data
                        If False, keep articles with warnings
        """
        self.logger = logging.getLogger(__name__)
        self.strict_mode = strict_mode
    
    def normalize_article_data(self, article: Dict) -> Dict:
        """Normalize article data for consistent processing"""
        normalized = article.copy()
        
        # Set default time_bracket for hybrid ranking stability
        normalized['time_bracket'] = 3  # Default to oldest bracket
        
        # CRITICAL FIX: Handle actual database structure
        # Articles have 'categories' (list) but filter expects 'category' (single value)
        if 'category' not in normalized or normalized.get('category') is None:
            categories_list = normalized.get('categories', [])
            normalized['category'] = self._extract_sports_category(categories_list, normalized)
        
        # In strict mode, validate required fields early
        if self.strict_mode:
            required_fields = ['title', 'category', 'source_name']
            if not all(normalized.get(field) for field in required_fields):
                self.logger.debug(f"Strict mode: Dropping article with missing required fields: {normalized.get('title', 'No title')[:50]}")
                return None  # Signal to drop this article
        
        # Normalize importance_score to float
        score = normalized.get('importance_score', 0)
        try:
            normalized['importance_score'] = float(score)
        except (ValueError, TypeError):
            if self.strict_mode:
                self.logger.debug(f"Strict mode: Dropping article with invalid importance_score: {normalized.get('title', '')[:50]}")
                return None
            normalized['importance_score'] = 0.0
            self.logger.warning(f"Invalid importance_score '{score}' for article: {article.get('title', '')[:50]}")
        
        # Derive importance_tier from score (don't trust input)
        score = normalized['importance_score']
        if score >= 8.0:
            normalized['importance_tier'] = 'critical'
        elif score >= 6.0:
            normalized['importance_tier'] = 'high'
        elif score >= 4.0:
            normalized['importance_tier'] = 'medium'
        elif score >= 2.0:
            normalized['importance_tier'] = 'low'
        else:
            normalized['importance_tier'] = 'minimal'
        
        # Normalize category to lowercase
        if 'category' in normalized and normalized['category']:
            normalized['category'] = str(normalized['category']).lower().strip()
            # In strict mode, validate category
            if self.strict_mode and normalized['category'] not in self.ALLOWED_CATEGORIES:
                self.logger.debug(f"Strict mode: Dropping article with invalid category '{normalized['category']}': {normalized.get('title', '')[:50]}")
                return None
        else:
            # Default to 'uncategorized' for non-sports articles
            normalized['category'] = 'uncategorized'
            if self.strict_mode:
                self.logger.debug(f"Strict mode: Dropping uncategorized article: {normalized.get('title', '')[:50]}")
                return None
        
        # Normalize source_name
        if 'source_name' in normalized:
            normalized['source_name'] = str(normalized['source_name']).lower().strip()
        
        # Extract domain from URL for source authority matching
        url = normalized.get('url') or normalized.get('link', '')
        if url:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.lower().replace('www.', '')
                normalized['source_domain'] = domain
            except Exception:
                normalized['source_domain'] = ''
        else:
            normalized['source_domain'] = ''
        
        # Validate and normalize dates
        for date_field in ['published_date', 'collected_date', 'published_date_ist']:
            if date_field in normalized and normalized[date_field]:
                try:
                    # Parse and convert to ISO format for consistent sorting
                    parsed_date = parser.parse(str(normalized[date_field]))
                    normalized[date_field] = parsed_date.isoformat()
                    normalized[f'{date_field}_parsed'] = parsed_date
                except Exception as e:
                    if self.strict_mode:
                        self.logger.debug(f"Strict mode: Dropping article with invalid {date_field}: {normalized.get('title', '')[:50]}")
                        return None
                    self.logger.warning(f"Invalid {date_field} '{normalized[date_field]}' for article: {article.get('title', '')[:50]}")
                    # Keep original value in lenient mode
        
        return normalized
    
    def _extract_sports_category(self, categories_list: List[str], article: Dict) -> str:
        """Extract single sports category from categories list"""
        if not categories_list:
            return self._categorize_by_content(article)
        
        # Convert categories to lowercase for matching
        categories_lower = [cat.lower().strip() for cat in categories_list if cat]
        
        # Direct sport matches
        for category in categories_lower:
            if category in self.ALLOWED_CATEGORIES:
                return category
        
        # Keyword-based detection from categories
        sport_keywords = {
            'football': ['football', 'soccer', 'premier league', 'fa cup', 'champions league', 'europa league', 'fifa', 'uefa'],
            'cricket': ['cricket', 'ipl', 'test', 'odi', 't20', 'county', 'ashes', 'bcci'],
            'basketball': ['basketball', 'nba', 'nfl', 'ncaa basketball', 'euroleague basketball']
        }
        
        for sport, keywords in sport_keywords.items():
            if any(keyword in cat for cat in categories_lower for keyword in keywords):
                return sport
        
        # Fallback to content-based categorization
        return self._categorize_by_content(article)
    
    def _categorize_by_content(self, article: Dict) -> str:
        """Categorize article by analyzing title and content"""
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        source = article.get('source_name', '').lower()
        
        text_content = f"{title} {summary} {source}"
        
        # Enhanced sport detection keywords
        sport_patterns = {
            'football': [
                # Teams
                'manchester united', 'manchester city', 'liverpool', 'arsenal', 'chelsea',
                'tottenham', 'real madrid', 'barcelona', 'bayern munich', 'psg',
                # Terms
                'football', 'soccer', 'goal', 'penalty', 'premier league', 'fa cup',
                'champions league', 'europa league', 'transfer', 'striker', 'midfielder',
                'goalkeeper', 'defender', 'var', 'offside'
            ],
            'cricket': [
                # Terms
                'cricket', 'wicket', 'batting', 'bowling', 'century', 'innings', 'over',
                'test match', 'odi', 't20', 'ipl', 'ashes', 'world cup cricket',
                # Players/Teams
                'kohli', 'sharma', 'root', 'smith', 'england cricket', 'india cricket',
                'australia cricket', 'pakistan cricket'
            ],
            'basketball': [
                # Terms
                'basketball', 'nba', 'three-pointer', 'dunk', 'rebound', 'assist',
                'playoffs', 'finals', 'draft', 'trade',
                # Teams
                'lakers', 'warriors', 'celtics', 'bulls', 'heat', 'spurs'
            ]
        }
        
        # Score each sport
        sport_scores = {}
        for sport, keywords in sport_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_content)
            if score > 0:
                sport_scores[sport] = score
        
        if sport_scores:
            best_sport = max(sport_scores, key=sport_scores.get)
            if sport_scores[best_sport] >= 2:  # Require at least 2 keyword matches
                return best_sport
        
        return 'uncategorized'
    
    def filter_articles(self, articles: List[Dict], criteria: Dict) -> List[Dict]:
        """
        Filter articles based on multiple criteria
        
        Args:
            articles: List of article dictionaries
            criteria: Dictionary with filtering criteria
                - categories: List of categories (cricket, football, basketball)
                - min_importance_score: Minimum importance score (replaces importance_tiers)
                - max_age_hours: Maximum article age in hours
                - source_authority: List of authority levels (premium, standard, low)
                - content_types: List of content types
                - keywords_include: List of keywords that must be present
                - keyword_match_mode: 'any' (OR) or 'all' (AND) for keyword matching
                - keywords_exclude: List of keywords to exclude
                - limit: Maximum number of articles to return
                - sort_by: Field to sort by (importance_score, published_date, published_date_asc, hybrid_rank)
                - require_complete: Only articles with all required fields
        
        Returns:
            List of filtered articles
        """
        # Step 0: Normalize all article data first
        self.logger.info(f"Starting filter with {len(articles)} articles")
        self.logger.info(f"Filter criteria: {criteria}")
        
        normalized_articles = []
        for article in articles:
            normalized = self.normalize_article_data(article)
            if normalized is not None:  # Skip articles dropped in strict mode
                normalized_articles.append(normalized)
        
        filtered = normalized_articles
        self.logger.info(f"After normalization: {len(filtered)} articles")
        
        # Step 1: Category filter (STRICT - only allowed categories)
        filtered = self._filter_by_category(filtered, criteria.get('categories'))
        self.logger.info(f"After category filter: {len(filtered)} articles")
        
        # Step 2: Minimum importance score filter (replaces importance tier filtering)
        min_score = criteria.get('min_importance_score')
        if min_score:
            filtered = self._filter_by_min_score(filtered, min_score)
            self.logger.info(f"After min score filter ({min_score}): {len(filtered)} articles")
        # Note: Removed redundant importance_tiers filter to avoid conflicting logic
        
        # Step 3: Recency filter
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
        
        # Step 6: Keyword inclusion filter
        keywords_include = criteria.get('keywords_include')
        if keywords_include:
            match_mode = criteria.get('keyword_match_mode', 'any')
            filtered = self._filter_by_keywords_include(filtered, keywords_include, match_mode)
            self.logger.info(f"After keyword inclusion filter ({match_mode}): {len(filtered)} articles")
        
        # Step 7: Keyword exclusion filter
        keywords_exclude = criteria.get('keywords_exclude')
        if keywords_exclude:
            filtered = self._filter_by_keywords_exclude(filtered, keywords_exclude)
            self.logger.info(f"After keyword exclusion filter: {len(filtered)} articles")
        
        # Step 8: Publishing readiness filter
        if criteria.get('require_complete', False):
            filtered = self._filter_by_completeness(filtered)
            self.logger.info(f"After completeness filter: {len(filtered)} articles")
        
        # Step 9: Remove duplicates
        filtered = self._remove_duplicates(filtered)
        self.logger.info(f"After duplicate removal: {len(filtered)} articles")
        
        # Step 10: Sort articles
        sort_by = criteria.get('sort_by', 'hybrid_rank')
        filtered = self._sort_articles(filtered, sort_by)
        
        # Step 11: Limit results
        limit = criteria.get('limit')
        if limit and len(filtered) > limit:
            filtered = filtered[:limit]
            self.logger.info(f"After limit ({limit}): {len(filtered)} articles")
        
        return filtered
    
    def _filter_by_category(self, articles: List[Dict], categories: Optional[List[str]]) -> List[Dict]:
        """Filter by category - ONLY cricket, football, basketball allowed
        
        Args:
            categories: List of specific categories to filter for.
                       If None or empty, returns empty list (no articles)
                       If contains invalid categories, those are ignored
        
        Returns:
            Filtered articles matching the specified categories only
        """
        if categories is None:
            # No categories specified - return empty list (user must explicitly choose)
            self.logger.info("No categories specified in filter - returning no articles")
            return []
        
        if not categories:  # Empty list
            self.logger.info("Empty categories list provided - returning no articles")
            return []
        
        # Ensure only allowed categories, preserve original case for logging
        original_categories = categories.copy()
        valid_categories = [cat.lower() for cat in categories if cat.lower() in self.ALLOWED_CATEGORIES]
        invalid_categories = [cat for cat in original_categories if cat.lower() not in self.ALLOWED_CATEGORIES]
        
        if invalid_categories:
            self.logger.warning(f"Invalid categories ignored: {invalid_categories}")
        
        if not valid_categories:
            self.logger.warning("No valid categories after filtering - returning no articles")
            return []
        
        self.logger.info(f"Filtering for categories: {valid_categories}")
        
        # Filter articles
        filtered_articles = [a for a in articles if a.get('category', '').lower() in valid_categories]
        
        # Log category breakdown
        category_counts = {}
        for article in filtered_articles:
            cat = article.get('category', 'unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        if category_counts:
            self.logger.info(f"Category distribution: {category_counts}")
        
        return filtered_articles
    
    def _filter_by_recency(self, articles: List[Dict], max_age_hours: int) -> List[Dict]:
        """Filter articles by maximum age with configurable strict mode
        
        Computes time_bracket for hybrid ranking:
        0: 0-6h (newest)
        1: 6-24h  
        2: 24-48h
        3: 48h+ (oldest)
        """
        from dateutil.tz import UTC
        
        now = datetime.now(UTC)
        cutoff_time = now - timedelta(hours=max_age_hours)
        filtered = []
        invalid_date_count = 0
        
        for article in articles:
            # Use pre-parsed date from normalization if available, prefer IST time
            pub_date = (article.get('published_date_ist_parsed') or 
                       article.get('published_date_parsed') or 
                       article.get('collected_date_parsed'))
            pub_date_str = (article.get('published_date_ist') or 
                           article.get('published_date') or 
                           article.get('collected_date'))
            
            if not pub_date and not pub_date_str:
                invalid_date_count += 1
                if self.strict_mode:
                    self.logger.debug(f"Strict mode: Dropping article with no date: {article.get('title', '')[:50]}")
                    continue
                else:
                    self.logger.warning(f"No date found for article: {article.get('title', '')[:50]}")
                    article['time_bracket'] = 3  # Treat as oldest
                    filtered.append(article)
                    continue
            
            # Parse date if not already parsed
            if not pub_date:
                try:
                    pub_date = parser.parse(pub_date_str)
                    if pub_date.tzinfo is not None:
                        pub_date = pub_date.astimezone(UTC)
                    else:
                        pub_date = pub_date.replace(tzinfo=UTC)
                    article['published_date_parsed'] = pub_date
                except Exception as e:
                    invalid_date_count += 1
                    if self.strict_mode:
                        self.logger.debug(f"Strict mode: Dropping article with unparseable date '{pub_date_str}': {article.get('title', '')[:50]}")
                        continue
                    else:
                        self.logger.warning(f"Unparseable date '{pub_date_str}' for article: {article.get('title', '')[:50]}")
                        article['time_bracket'] = 3
                        filtered.append(article)
                        continue
            
            # Check recency
            if pub_date >= cutoff_time:
                # Compute time bracket for hybrid ranking
                hours_old = (now - pub_date).total_seconds() / 3600
                if hours_old <= 6:
                    article['time_bracket'] = 0
                elif hours_old <= 24:
                    article['time_bracket'] = 1
                elif hours_old <= 48:
                    article['time_bracket'] = 2
                else:
                    article['time_bracket'] = 3
                
                filtered.append(article)
        
        if invalid_date_count > 0:
            self.logger.info(f"Recency filter: {invalid_date_count} articles with invalid dates ({'dropped' if self.strict_mode else 'kept'})")
        
        return filtered
    
    def _filter_by_source_authority(self, articles: List[Dict], authority_levels: Optional[List[str]]) -> List[Dict]:
        """Filter by source authority with URL domain matching preferred over source_name"""
        if not authority_levels:
            return articles
        
        # Build authority criteria
        authority_criteria = []
        for level in authority_levels:
            if level.lower() in self.SOURCE_AUTHORITY:
                authority_criteria.append((level.lower(), self.SOURCE_AUTHORITY[level.lower()]))
        
        if not authority_criteria:
            return articles
        
        filtered = []
        for article in articles:
            domain = article.get('source_domain', '')
            source_name = article.get('source_name', '').lower().strip()
            importance_score = article.get('importance_score', 0)
            
            # Check each authority level
            source_matches = False
            matched_authority_level = None
            
            for level_name, criteria in authority_criteria:
                # First try domain matching (preferred)
                if domain:
                    for allowed_source in criteria['sources']:
                        if self._is_domain_match(domain, allowed_source):
                            if importance_score >= criteria['min_score']:
                                source_matches = True
                                matched_authority_level = level_name
                                break
                
                # Fallback to source_name matching
                if not source_matches and source_name:
                    for allowed_source in criteria['sources']:
                        if self._is_source_match(source_name, allowed_source):
                            if importance_score >= criteria['min_score']:
                                source_matches = True
                                matched_authority_level = level_name
                                break
                
                if source_matches:
                    break
            
            if source_matches:
                article['matched_authority_level'] = matched_authority_level
                filtered.append(article)
        
        return filtered
    
    def _is_domain_match(self, article_domain: str, canonical_source: str) -> bool:
        """Check if article domain matches canonical source with subdomain spoofing protection"""
        if not article_domain or not canonical_source:
            return False
        
        canonical_source = canonical_source.lower().strip()
        
        # Extract domain from canonical source if it's a URL-like string
        if '.' in canonical_source:
            canonical_domain = canonical_source.replace('www.', '').replace('http://', '').replace('https://', '')
            if '/' in canonical_domain:
                canonical_domain = canonical_domain.split('/')[0]
            
            # Secure domain matching: prevent subdomain spoofing (fakebbc.com)
            return article_domain == canonical_domain or article_domain.endswith('.' + canonical_domain)
        
        # For brand names, check if domain contains the brand
        return canonical_source in article_domain
    
    def _is_source_match(self, article_source: str, canonical_source: str) -> bool:
        """Check if article source matches canonical source with exact domain logic"""
        if not article_source or not canonical_source:
            return False
        
        article_source = article_source.lower().strip()
        canonical_source = canonical_source.lower().strip()
        
        # Exact match
        if article_source == canonical_source:
            return True
        
        # Domain-based matching for URLs
        if ('.' in canonical_source or 'www.' in canonical_source):
            # Extract domain from canonical source
            canonical_domain = canonical_source.replace('www.', '').replace('http://', '').replace('https://', '')
            if '/' in canonical_domain:
                canonical_domain = canonical_domain.split('/')[0]
            
            # Check if article source contains this domain
            if canonical_domain in article_source:
                # Ensure it's not a substring match like "notbbc" matching "bbc"
                # Check word boundaries
                import re
                pattern = r'\b' + re.escape(canonical_domain) + r'\b'
                return bool(re.search(pattern, article_source))
        
        # Brand name matching with word boundaries
        import re
        pattern = r'\b' + re.escape(canonical_source) + r'\b'
        return bool(re.search(pattern, article_source))
    
    def _filter_by_content_type(self, articles: List[Dict], content_types: Optional[List[str]]) -> List[Dict]:
        """Filter by content type with OR logic between types and OR logic within type keywords"""
        if not content_types:
            return articles
        
        filtered = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            
            # Check each content type separately (OR logic between types)
            matches_any_type = False
            article_content_types = []
            
            for ctype in content_types:
                if ctype.lower() in self.CONTENT_TYPES:
                    keywords = self.CONTENT_TYPES[ctype.lower()]['keywords']
                    
                    # Enhanced matching: require multiple keywords for match_result to reduce over-tagging
                    if ctype.lower() == 'match_result':
                        # Require at least 2 keyword hits for match results to avoid misclassifying opinions/previews
                        keyword_hits = sum(1 for keyword in keywords if keyword in text)
                        if keyword_hits >= 2:
                            matches_any_type = True
                            article_content_types.append(ctype.lower())
                    else:
                        # OR logic within type - if ANY keyword matches, article matches this type
                        if any(keyword in text for keyword in keywords):
                            matches_any_type = True
                            article_content_types.append(ctype.lower())
            
            if matches_any_type:
                # Store detected content types for summary reporting
                article['detected_content_types'] = article_content_types
                filtered.append(article)
        
        return filtered
    
    def _filter_by_min_score(self, articles: List[Dict], min_score: float) -> List[Dict]:
        """Filter by minimum importance score"""
        return [a for a in articles if a.get('importance_score', 0) >= min_score]
    
    def _filter_by_keywords_include(self, articles: List[Dict], keywords: List[str], match_mode: str = 'any') -> List[Dict]:
        """Include only articles containing specified keywords
        
        Args:
            match_mode: 'any' (OR logic) or 'all' (AND logic)
        """
        if not keywords:
            return articles
            
        keywords_lower = [k.lower() for k in keywords]
        
        filtered = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            
            if match_mode == 'all':
                # AND logic - all keywords must be present
                if all(keyword in text for keyword in keywords_lower):
                    filtered.append(article)
            else:
                # OR logic - any keyword must be present (default)
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
        
        Revalidates category against ALLOWED_CATEGORIES to prevent bypass.
        
        Required fields:
        - title: Article headline (min 10 chars)
        - url/link: Article URL
        - category: Sport category (cricket, football, basketball)
        - published_date or collected_date: Publication timestamp
        - source_name: Source of the article
        - importance_score: Valid numeric score
        """
        required_fields = ['title', 'category', 'source_name']
        url_fields = ['link', 'url']
        date_fields = ['published_date', 'collected_date', 'published_date_ist']
        
        filtered = []
        for article in articles:
            # Check required fields exist
            if not all(article.get(field) for field in required_fields):
                continue
            
            # Check title length
            title = article.get('title', '')
            if len(str(title).strip()) < 10:
                continue
            
            # REVALIDATE category against allowed categories (prevent bypass)
            category = article.get('category', '').lower().strip()
            if category not in self.ALLOWED_CATEGORIES:
                self.logger.warning(f"Article with invalid category '{category}' rejected: {title[:50]}")
                continue
            
            # Check URL exists
            if not any(article.get(field) for field in url_fields):
                continue
            
            # Check date exists (including IST date)
            has_valid_date = False
            for field in date_fields:
                if article.get(field) or article.get(f'{field}_parsed'):
                    has_valid_date = True
                    break
            
            if not has_valid_date:
                continue
            
            # Check importance_score is valid numeric
            score = article.get('importance_score')
            try:
                float(score)
            except (ValueError, TypeError):
                self.logger.warning(f"Article with invalid importance_score '{score}' rejected: {title[:50]}")
                continue
            
            filtered.append(article)
        
        return filtered
    
    def _remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles with O(n) optimized matching
        
        Strategy:
        1. Cheap pre-filtering using title hash and length
        2. URL-based exact matching
        3. Title similarity only for pre-filter matches
        """
        if not articles:
            return []
        
        unique_articles = []
        seen_urls = {}
        title_buckets = {}  # Group by first 5 words hash for O(n) pre-filtering
        
        for article in articles:
            url = article.get('link', '') or article.get('url', '')
            title = article.get('title', '').lower().strip()
            
            # Normalize title and URL
            norm_title = self._normalize_title(title)
            is_duplicate = False
            
            # First check: URL-based deduplication (O(1))
            if url:
                norm_url = self._normalize_url(url)
                
                if norm_url in seen_urls:
                    is_duplicate = True
                else:
                    seen_urls[norm_url] = article
            
            # Second check: Title similarity with pre-filtering
            if not is_duplicate:
                # Create bucket key from first 5 words for cheap pre-filtering
                words = norm_title.split()[:5]
                bucket_key = ' '.join(words) if len(words) >= 3 else norm_title
                title_length = len(norm_title)
                
                # Direct bucket access for O(n) performance - only check exact matching bucket
                potential_matches = title_buckets.get(bucket_key, [])
                
                # Optional: check similar length buckets only if exact bucket is empty (rare case)
                if not potential_matches:
                    for existing_key, existing_articles in title_buckets.items():
                        if abs(len(existing_key) - len(bucket_key)) <= 10:
                            potential_matches.extend(existing_articles)
                            break  # Only check one similar bucket to maintain performance
                
                # Expensive similarity check only for pre-filtered candidates
                for existing_article in potential_matches:
                    if self._are_articles_duplicate(article, existing_article):
                        is_duplicate = True
                        break
                
                # Add to bucket if not duplicate
                if not is_duplicate:
                    if bucket_key not in title_buckets:
                        title_buckets[bucket_key] = []
                    title_buckets[bucket_key].append(article)
            
            if not is_duplicate:
                unique_articles.append(article)
        
        return unique_articles
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for deduplication"""
        if not title:
            return ""
        
        import re
        # Convert to lowercase and strip
        normalized = title.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common punctuation at the end
        normalized = normalized.rstrip('.,!?:;')
        
        return normalized
    
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
        title1 = self._normalize_title(article1.get('title', ''))
        title2 = self._normalize_title(article2.get('title', ''))
        
        # Exact title match
        if title1 == title2:
            return True
        
        # Title similarity with SequenceMatcher
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
        """Sort articles by specified field with proper datetime handling"""
        from dateutil.tz import UTC
        
        if sort_by == 'importance_score':
            return sorted(articles, key=lambda x: x.get('importance_score', 0), reverse=True)
        elif sort_by == 'published_date' or sort_by == 'published_date_desc':
            # Use parsed datetime for proper sorting, prefer IST (newest first)
            def date_key(article):
                parsed_date = (article.get('published_date_ist_parsed') or 
                              article.get('published_date_parsed') or 
                              article.get('collected_date_parsed'))
                if parsed_date:
                    # Ensure timezone-aware for consistent comparison
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=UTC)
                    return parsed_date
                    
                # Fallback to string date if somehow not parsed
                date_str = (article.get('published_date_ist') or 
                           article.get('published_date') or 
                           article.get('collected_date') or '')
                try:
                    if date_str:
                        parsed = parser.parse(date_str)
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=UTC)
                        return parsed
                    return datetime.min.replace(tzinfo=UTC)
                except:
                    return datetime.min.replace(tzinfo=UTC)
            
            return sorted(articles, key=date_key, reverse=True)
        elif sort_by == 'published_date_asc':
            # Same logic but oldest first
            def date_key(article):
                parsed_date = (article.get('published_date_ist_parsed') or 
                              article.get('published_date_parsed') or 
                              article.get('collected_date_parsed'))
                if parsed_date:
                    # Ensure timezone-aware for consistent comparison
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=UTC)
                    return parsed_date
                    
                # Fallback to string date if somehow not parsed
                date_str = (article.get('published_date_ist') or 
                           article.get('published_date') or 
                           article.get('collected_date') or '')
                try:
                    if date_str:
                        parsed = parser.parse(date_str)
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=UTC)
                        return parsed
                    return datetime.min.replace(tzinfo=UTC)
                except:
                    return datetime.min.replace(tzinfo=UTC)
            
            return sorted(articles, key=date_key, reverse=False)  # Oldest first
        elif sort_by == 'hybrid_rank':
            # Hybrid: time bracket first (0=newest), then by importance within bracket
            return sorted(articles, 
                         key=lambda x: (x.get('time_bracket', 3), -x.get('importance_score', 0)))
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
        
        # Count by category, importance, authority level, and content type
        for article in articles:
            # Category counts
            cat = article.get('category', 'unknown')
            summary['by_category'][cat] = summary['by_category'].get(cat, 0) + 1
            
            # Importance tier counts
            tier = article.get('importance_tier', 'minimal')
            summary['by_importance'][tier] = summary['by_importance'].get(tier, 0) + 1
            
            # Source authority level counts
            authority_level = article.get('matched_authority_level', 'unmatched')
            summary['by_source_authority'][authority_level] = summary['by_source_authority'].get(authority_level, 0) + 1
            
            # Content type counts
            detected_types = article.get('detected_content_types', [])
            for content_type in detected_types:
                summary['by_content_type'][content_type] = summary['by_content_type'].get(content_type, 0) + 1
            
            # Count articles with no detected content type
            if not detected_types:
                summary['by_content_type']['none'] = summary['by_content_type'].get('none', 0) + 1
        
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
                'min_importance_score': 6.0,  # High + Critical tiers
                'max_age_hours': 24,
                'source_authority': ['premium', 'standard'],
                'require_complete': True,
                'sort_by': 'hybrid_rank',
                'limit': 50
            },
            'breaking_news': {
                'categories': ['cricket', 'football', 'basketball'],
                'min_importance_score': 8.0,  # Critical tier only
                'max_age_hours': 6,
                'content_types': ['breaking', 'transfer', 'controversy'],
                'keywords_include': ['breaking', 'urgent', 'confirmed'],
                'keyword_match_mode': 'any',
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
    # Example usage with strict mode for testing
    filter_system = ArticleFilter(strict_mode=True)
    
    # Test with sample articles
    sample_articles = [
        {
            'title': 'BREAKING: Manchester United sign new striker',
            'category': 'football',
            'importance_score': '8.5',  # Test string to float conversion
            'published_date': datetime.now().isoformat(),
            'source_name': 'BBC Sport',
            'url': 'http://example.com/1'
        },
        {
            'title': 'Cricket: India vs Australia preview',
            'category': 'cricket',
            'importance_score': 5.0,
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
