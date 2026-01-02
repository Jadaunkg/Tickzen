"""
Internal Link Suggester
Finds related articles from a WordPress site to create internal links
Uses keyword matching and category filtering for relevance
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class InternalLinkSuggester:
    """Suggests internal links for articles based on keyword and category matching"""
    
    def __init__(self, min_similarity: float = 0.15, max_links_per_article: int = 5):
        """
        Initialize internal link suggester
        
        Args:
            min_similarity: Minimum similarity score (0-1) for keyword matching (lowered from 0.3 to 0.15)
            max_links_per_article: Maximum number of internal links to suggest per article
        """
        self.min_similarity = min_similarity
        self.max_links_per_article = max_links_per_article
    
    def _calculate_keyword_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """
        Calculate similarity between two keyword lists
        
        Args:
            keywords1: First list of keywords
            keywords2: Second list of keywords
        
        Returns:
            Similarity score (0-1)
        """
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(keywords1)
        set2 = set(keywords2)
        
        if not set1 or not set2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_unique_keywords(self, keywords: List[str]) -> List[str]:
        """Extract unique, meaningful keywords"""
        return list(set(keywords))
    
    def _calculate_relevance_score(self, article1: Dict, article2: Dict, 
                                   same_category: bool = False) -> float:
        """
        Calculate relevance score for linking article1 to article2
        Improved algorithm with better title and partial keyword matching
        
        Args:
            article1: Source article (the one being published)
            article2: Target article (existing article to link to)
            same_category: Whether articles are in same category
        
        Returns:
            Relevance score (0-1)
        """
        score = 0.0
        
        # Keyword similarity (35% of score)
        keywords1 = article1.get('keywords', [])
        keywords2 = article2.get('keywords', [])
        keyword_sim = self._calculate_keyword_similarity(keywords1, keywords2)
        score += keyword_sim * 0.35
        
        # Partial keyword matching - if ANY keywords match, give bonus (15% of score)
        if keywords1 and keywords2:
            set1 = set(keywords1)
            set2 = set(keywords2)
            if set1 & set2:  # If there's any intersection
                score += 0.15
        
        # Category matching (20% of score) - strong signal
        if same_category:
            score += 0.2
        
        # Title similarity (20% of score) - use both exact and partial matching
        title1 = article1.get('title', '').lower()
        title2 = article2.get('title', '').lower()
        if title1 and title2:
            # Use SequenceMatcher for intelligent string similarity
            title_sim = SequenceMatcher(None, title1, title2).ratio()
            
            # Also check for common words in titles (helps with related topics)
            title_words1 = set(title1.split())
            title_words2 = set(title2.split())
            common_words = title_words1 & title_words2
            # Weight words by removing common stop words for this check
            meaningful_common = [w for w in common_words if len(w) > 3]
            if meaningful_common:
                title_sim = max(title_sim, 0.35)  # Minimum boost if key words match
            
            score += title_sim * 0.2
        
        # Freshness bonus (10% of score) - prefer recent articles
        date1 = article1.get('published_date', '')
        date2 = article2.get('published_date', '')
        if date1 and date2:
            try:
                from datetime import datetime
                d1 = datetime.fromisoformat(date1.replace('Z', '+00:00'))
                d2 = datetime.fromisoformat(date2.replace('Z', '+00:00'))
                days_diff = abs((d1 - d2).days)
                # Prefer articles within 180 days (extended from 90)
                if days_diff <= 180:
                    freshness_score = 1.0 - (days_diff / 180.0)
                    score += freshness_score * 0.1
            except Exception as e:
                logger.debug(f"Error calculating freshness score: {e}")
        
        return min(score, 1.0)
    
    def find_related_articles(self, source_article: Dict, candidate_articles: List[Dict],
                             same_category_only: bool = True, limit: int = None) -> List[Dict]:
        """
        Find related articles from candidates for linking
        
        Args:
            source_article: The article being published
            candidate_articles: List of existing articles to consider
            same_category_only: If True, only link within same category
            limit: Maximum number of suggestions (uses self.max_links_per_article if None)
        
        Returns:
            List of related articles with their relevance scores and suggested anchor text
        """
        if limit is None:
            limit = self.max_links_per_article
        
        if not source_article or not candidate_articles:
            return []
        
        source_categories = source_article.get('categories', [])
        source_keywords = source_article.get('keywords', [])
        
        related = []
        
        for candidate in candidate_articles:
            # Skip if same article
            if candidate.get('id') == source_article.get('id'):
                continue
            
            # Check category match if required
            candidate_categories = candidate.get('categories', [])
            same_category = bool(set(source_categories) & set(candidate_categories)) if source_categories and candidate_categories else False
            
            if same_category_only and not same_category and source_categories and candidate_categories:
                continue
            
            # Calculate relevance
            relevance_score = self._calculate_relevance_score(
                source_article, candidate, same_category=same_category
            )
            
            # Only include if score meets minimum threshold
            if relevance_score >= self.min_similarity:
                # Generate anchor text - prefer specific keyword matches
                anchor_text = self._generate_anchor_text(source_article, candidate)
                
                related.append({
                    'id': candidate.get('id'),
                    'title': candidate.get('title'),
                    'url': candidate.get('url'),
                    'relevance_score': relevance_score,
                    'anchor_text': anchor_text,
                    'same_category': same_category,
                    'keywords': candidate.get('keywords', [])
                })
        
        # Sort by relevance score (descending) and return top results
        related.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        logger.info(f"Found {len(related)} related articles for '{source_article.get('title')}'")
        
        return related[:limit]
    
    def _generate_anchor_text(self, source_article: Dict, target_article: Dict) -> str:
        """
        Generate natural anchor text for the link
        Prefers keywords that match between articles
        
        Args:
            source_article: Article being published
            target_article: Article to link to
        
        Returns:
            Suggested anchor text
        """
        source_keywords = set(source_article.get('keywords', []))
        target_keywords = set(target_article.get('keywords', []))
        target_title = target_article.get('title', '')
        
        # Find common keywords
        common_keywords = source_keywords & target_keywords
        
        if common_keywords:
            # Sort by length (longer keywords are often more specific)
            sorted_keywords = sorted(list(common_keywords), key=len, reverse=True)
            keyword = sorted_keywords[0]
            
            # Use the keyword directly as anchor text (natural linking)
            return keyword
        
        # Extract meaningful phrases from title
        if target_title:
            # Clean title and extract key phrases
            title_clean = re.sub(r'[^\w\s-]', '', target_title.lower())
            title_words = title_clean.split()
            
            # Skip common words
            skip_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'do', 'does', 'did', 'get', 'gets', 'got', 'this', 'that', 'these', 'those', 'how', 'what', 'when', 'where', 'why', 'who'}
            meaningful_words = [word for word in title_words if word not in skip_words and len(word) > 2]
            
            if len(meaningful_words) >= 2:
                # Use first 2-3 meaningful words
                phrase_words = meaningful_words[:3] if len(meaningful_words) >= 3 else meaningful_words[:2]
                return ' '.join(phrase_words)
            elif meaningful_words:
                return meaningful_words[0]
        
        return "related article"
    
    def embed_internal_links_in_content(self, content: str, related_articles: List[Dict],
                                       max_links: int = 4) -> Tuple[str, List[Dict]]:
        """
        Embed internal links into article content with fallback strategy:
        - First tries to add inline keyword links (natural linking within content)
        - If not enough keyword matches, always adds related articles section at the end
        - Ensures minimum 3 links, maximum 4 links total
        
        Args:
            content: HTML or plain text content
            related_articles: List of related articles with relevance scores
            max_links: Maximum number of links to embed (default 4)
        
        Returns:
            Tuple of (modified_content, embedded_links_list)
        """
        if not related_articles or not content:
            return content, []
        
        # Ensure reasonable limits
        max_links = min(max_links, 4)  # Hard cap at 4 links
        max_links = max(max_links, 3)  # Minimum 3 links
        available_articles = related_articles[:max_links + 3]  # Get extra articles for fallback
        
        embedded_links = []
        modified_content = content
        
        # Phase 1: Try to add inline keyword links (prioritized)
        logger.info(f"Phase 1: Attempting to add inline keyword links")
        linked_phrases = set()
        inline_links_added = 0
        
        for article in available_articles:
            if inline_links_added >= max_links:
                break
                
            anchor_text = article['anchor_text']
            
            # Skip if this phrase was already linked
            if anchor_text.lower() in linked_phrases:
                continue
            
            # Look for exact matches of the anchor text in the content (case-insensitive)
            pattern = r'\b' + re.escape(anchor_text) + r'\b'
            matches = list(re.finditer(pattern, modified_content, re.IGNORECASE))
            
            if matches:
                # Link the first occurrence only
                match = matches[0]
                original_text = match.group()
                
                # Create the link HTML (preserve original case)
                link_html = f'<a href="{article["url"]}" title="{article["title"]}">{original_text}</a>'
                
                # Replace the first occurrence
                modified_content = modified_content[:match.start()] + link_html + modified_content[match.end():]
                
                embedded_links.append({
                    'title': article['title'],
                    'url': article['url'],
                    'anchor_text': anchor_text,
                    'relevance_score': article['relevance_score'],
                    'position': 'inline',
                    'matched_text': original_text,
                    'link_type': 'keyword'
                })
                
                # Mark this phrase as linked
                linked_phrases.add(anchor_text.lower())
                inline_links_added += 1
                
                logger.info(f"Inline link {inline_links_added}: '{original_text}' -> '{article['title']}'")
            else:
                # If exact match not found, try individual words from the anchor text
                words = anchor_text.split()
                if len(words) > 1:
                    for word in words:
                        if inline_links_added >= max_links:
                            break
                            
                        if len(word) > 3 and word.lower() not in linked_phrases:  # Skip short words
                            word_pattern = r'\b' + re.escape(word) + r'\b'
                            word_matches = list(re.finditer(word_pattern, modified_content, re.IGNORECASE))
                            
                            if word_matches:
                                match = word_matches[0]
                                original_word = match.group()
                                
                                # Link this word
                                link_html = f'<a href="{article["url"]}" title="{article["title"]}">{original_word}</a>'
                                modified_content = modified_content[:match.start()] + link_html + modified_content[match.end():]
                                
                                embedded_links.append({
                                    'title': article['title'],
                                    'url': article['url'],
                                    'anchor_text': word,
                                    'relevance_score': article['relevance_score'],
                                    'position': 'inline',
                                    'matched_text': original_word,
                                    'link_type': 'keyword'
                                })
                                
                                linked_phrases.add(word.lower())
                                inline_links_added += 1
                                logger.info(f"Inline link {inline_links_added}: '{original_word}' -> '{article['title']}'")
                                break
        
        # Phase 2: Always add Related Articles section if we need more links to reach minimum (3-4 total)
        current_links = len(embedded_links)
        min_required = max(3 - current_links, 0)  # Need at least 3 total links
        max_remaining = max_links - current_links  # Don't exceed max links
        
        if min_required > 0 or current_links < 2:  # Always add if we have less than 2 inline links
            # Get articles not already used
            unused_articles = [art for art in available_articles 
                             if not any(link['url'] == art['url'] for link in embedded_links)]
            
            if unused_articles:
                # Calculate how many related links to add
                links_to_add = min(max_remaining, len(unused_articles))
                links_to_add = max(links_to_add, min_required)  # Ensure we meet minimum
                links_to_add = min(links_to_add, 4)  # Cap at 4 total for related section
                
                related_section_articles = unused_articles[:links_to_add]
                
                logger.info(f"Phase 2: Adding {len(related_section_articles)} links to Related Articles section")
                
                related_section = """
<div class="related-articles" style="margin-top: 30px; padding: 20px; background-color: #f5f5f5; border-left: 4px solid #007cba;">
  <h3>Related Articles</h3>
  <ul>
"""
                
                for article in related_section_articles:
                    related_section += f'    <li><a href="{article["url"]}" title="{article["title"]}">{article["title"]}</a></li>\n'
                    embedded_links.append({
                        'title': article['title'],
                        'url': article['url'],
                        'anchor_text': article['title'],
                        'relevance_score': article['relevance_score'],
                        'position': 'section',
                        'link_type': 'related_article'
                    })
                    logger.info(f"Related article: '{article['title']}'")
                
                related_section += "  </ul>\n</div>"
                modified_content += related_section
        
        # Summary
        inline_count = len([l for l in embedded_links if l['link_type'] == 'keyword'])
        related_count = len([l for l in embedded_links if l['link_type'] == 'related_article'])
        
        logger.info(f"Internal linking complete: {inline_count} inline keyword links + {related_count} related article links = {len(embedded_links)} total links")
        
        # Ensure we always have at least 3 links total
        if len(embedded_links) < 3:
            logger.warning(f"Only {len(embedded_links)} links added, expected minimum 3")
        
        return modified_content, embedded_links
    
    def generate_related_articles_section(self, related_articles: List[Dict]) -> str:
        """
        Generate a complete "Related Articles" HTML section
        
        Args:
            related_articles: List of related articles
        
        Returns:
            HTML string with related articles section
        """
        if not related_articles:
            return ""
        
        html = """
<hr />
<div class="related-articles" style="margin-top: 40px; padding: 25px; background-color: #f9f9f9; border-left: 5px solid #007cba; border-radius: 3px;">
  <h3 style="margin-top: 0; color: #333;">Related Articles</h3>
  <ul style="list-style: none; padding: 0;">
"""
        
        for article in related_articles[:10]:  # Show max 10 related articles
            score_pct = int(article['relevance_score'] * 100)
            html += f'    <li style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #eee;"><a href="{article["url"]}" title="{article["title"]}" style="color: #007cba; text-decoration: none; font-weight: 500;">{article["title"]}</a><br /><small style="color: #666;">Relevance: {score_pct}%</small></li>\n'
        
        html += """  </ul>
</div>
"""
        
        return html
