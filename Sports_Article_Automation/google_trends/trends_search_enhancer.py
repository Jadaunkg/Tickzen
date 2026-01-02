"""
Google Trends Enhanced Search Wrapper
===================================

Specialized wrapper around the enhanced_search_content.py functionality
specifically optimized for Google Trends keywords and sports content.

This module adapts the existing enhanced search logic to work better with
trending search terms by:
1. Adding trend-specific search query optimization
2. Prioritizing sports-related content sources
3. Enhanced filtering for trend-relevant articles
4. Better handling of trending keywords vs traditional headlines

Author: Tickzen AI System
Created: December 25, 2025
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
import re

# Add parent directories to path
current_dir = Path(__file__).parent
sports_automation_dir = current_dir.parent
project_root = sports_automation_dir.parent
sys.path.extend([str(sports_automation_dir), str(project_root)])

# Import the original enhanced search
from testing.test_enhanced_search_content import EnhancedSearchContentFetcher

# Setup logging
logger = logging.getLogger(__name__)


class GoogleTrendsSearchEnhancer:
    """Enhanced search specifically optimized for Google Trends keywords"""
    
    def __init__(self):
        """Initialize the Google Trends Search Enhancer"""
        self.base_searcher = EnhancedSearchContentFetcher()
        self.available = self.base_searcher.available
        
        # Trend-specific search modifiers
        self.trend_query_enhancers = [
            "latest news",
            "breaking news", 
            "recent updates",
            "today",
            "2025",
            "sports news",
            "what happened"
        ]
        
        # Sports-specific keywords to boost relevance
        self.sports_keywords = [
            "game", "match", "player", "team", "coach", "season", "tournament",
            "championship", "victory", "defeat", "score", "goal", "touchdown", 
            "basket", "run", "win", "loss", "draft", "trade", "injury",
            "contract", "signing", "transfer", "league", "division", "playoff"
        ]
        
        logger.info("✅ Google Trends Search Enhancer initialized")
        logger.info(f"🔍 Base searcher available: {self.available}")
    
    def enhance_trend_query(self, trend_query: str) -> List[str]:
        """
        Generate 3 focused search variations for a trending keyword
        
        Args:
            trend_query: Original trending keyword/phrase
            
        Returns:
            List[str]: Enhanced search queries (max 3)
        """
        enhanced_queries = []
        
        # Original query
        enhanced_queries.append(trend_query)
        
        # Add sports context if not already present - most important variation
        if not any(keyword in trend_query.lower() for keyword in ["sports", "game", "match", "player"]):
            enhanced_queries.append(f"{trend_query} sports news")
        
        # Add specific context based on trend type
        if self._looks_like_person_name(trend_query):
            # For person names, focus on latest news
            enhanced_queries.append(f"{trend_query} latest news")
        elif any(indicator in trend_query.lower() for indicator in ["vs", "v ", "against", "game", "match"]):
            # For games/matches, focus on results
            enhanced_queries.append(f"{trend_query} result")
        else:
            # For general trends, use breaking news
            enhanced_queries.append(f"{trend_query} breaking news")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in enhanced_queries:
            if query.lower() not in seen:
                seen.add(query.lower())
                unique_queries.append(query)
        
        # Limit to exactly 3 variations to conserve search requests
        final_queries = unique_queries[:3]
        logger.info(f"📈 Enhanced '{trend_query}' into {len(final_queries)} search variations")
        return final_queries
    
    def _looks_like_person_name(self, query: str) -> bool:
        """Check if query looks like a person's name"""
        words = query.split()
        
        # Simple heuristics for person names
        if len(words) == 2 and all(word.isalpha() and word.istitle() for word in words):
            return True
        
        if len(words) == 3 and all(word.isalpha() for word in words):
            return True
        
        # Check for common name patterns
        name_patterns = [
            r'^[A-Z][a-z]+ [A-Z][a-z]+$',  # First Last
            r'^[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+$',  # First M. Last
            r'^[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+$'  # First Middle Last
        ]
        
        return any(re.match(pattern, query) for pattern in name_patterns)
    
    def search_trend_comprehensive(self, 
                                  trend_query: str,
                                  category: str = "sports",
                                  max_search_variations: int = 3) -> Dict:
        """
        Perform comprehensive search for a trending topic
        
        Args:
            trend_query: The trending keyword/phrase
            category: Content category (default: sports)  
            max_search_variations: Maximum search query variations to try
            
        Returns:
            Dict: Comprehensive search results
        """
        logger.info(f"\n🔍 COMPREHENSIVE TREND SEARCH: {trend_query}")
        logger.info("="*60)
        
        search_start = time.time()
        
        # Generate enhanced search queries
        enhanced_queries = self.enhance_trend_query(trend_query)[:max_search_variations]
        
        logger.info(f"🎯 Searching with {len(enhanced_queries)} query variations:")
        for i, query in enumerate(enhanced_queries, 1):
            logger.info(f"   {i}. {query}")
        
        # Collect results from all query variations
        all_results = []
        total_sources = 0
        total_words = 0
        search_errors = []
        
        for i, query in enumerate(enhanced_queries, 1):
            logger.info(f"\n📊 Search {i}/{len(enhanced_queries)}: '{query}'")
            
            try:
                # Use the base searcher with enhanced query
                result = self.base_searcher.collect_comprehensive_research(
                    headline=query,
                    category=category
                )
                
                if result.get('status') == 'success':
                    all_results.append(result)
                    sources = result.get('total_sources_processed', 0)
                    words = result.get('total_words_collected', 0)
                    total_sources += sources
                    total_words += words
                    
                    logger.info(f"   ✅ Found {sources} sources, {words} words")
                else:
                    error = result.get('error', 'Unknown error')
                    search_errors.append(f"Query '{query}': {error}")
                    logger.warning(f"   ⚠️  Search failed: {error}")
                
                # Brief pause between searches to avoid rate limits
                if i < len(enhanced_queries):
                    time.sleep(1)
                    
            except Exception as e:
                error_msg = str(e)
                search_errors.append(f"Query '{query}': {error_msg}")
                logger.error(f"   ❌ Search error: {error_msg}")
        
        search_time = time.time() - search_start
        
        if not all_results:
            return {
                'status': 'error',
                'error': f"All {len(enhanced_queries)} search variations failed",
                'search_errors': search_errors,
                'search_time': search_time,
                'trend_query': trend_query,
                'queries_attempted': enhanced_queries
            }
        
        # Combine and deduplicate results
        combined_result = self._combine_search_results(
            trend_query=trend_query,
            search_results=all_results,
            search_time=search_time
        )
        
        logger.info(f"\n🎉 TREND SEARCH COMPLETED")
        logger.info(f"   ✅ Successful searches: {len(all_results)}/{len(enhanced_queries)}")
        logger.info(f"   📊 Total unique sources: {combined_result.get('total_sources_processed', 0)}")
        logger.info(f"   📝 Total words collected: {combined_result.get('total_words_collected', 0)}")
        logger.info(f"   ⏱️  Search time: {search_time:.2f}s")
        
        return combined_result
    
    def _combine_search_results(self, 
                               trend_query: str, 
                               search_results: List[Dict],
                               search_time: float) -> Dict:
        """
        Combine multiple search results into one comprehensive result
        
        Args:
            trend_query: Original trending query
            search_results: List of successful search results
            search_time: Total time taken for searches
            
        Returns:
            Dict: Combined search result
        """
        logger.info(f"🔄 Combining {len(search_results)} search results...")
        
        # Collect all unique sources and content
        all_sources = set()
        all_content_pieces = []
        all_urls = set()
        combined_research = []
        
        for result in search_results:
            # Collect source URLs
            if 'source_urls' in result:
                all_urls.update(result['source_urls'])
            
            # Collect research sections
            if 'comprehensive_research' in result:
                combined_research.append(result['comprehensive_research'])
            
            # Collect article contents for deduplication
            if 'article_contents' in result:
                for content in result['article_contents']:
                    if content.get('status') == 'success':
                        content_text = content.get('content', '')
                        if content_text and len(content_text) > 200:
                            # Simple deduplication based on content similarity
                            is_duplicate = any(
                                self._content_similarity(content_text, existing.get('content', '')) > 0.8
                                for existing in all_content_pieces
                            )
                            if not is_duplicate:
                                all_content_pieces.append(content)
        
        # Create comprehensive research text
        comprehensive_research = self._create_comprehensive_research(
            trend_query=trend_query,
            research_sections=combined_research,
            content_pieces=all_content_pieces
        )
        
        # Calculate final metrics
        total_words = len(comprehensive_research.split())
        
        return {
            'status': 'success',
            'trend_query': trend_query,
            'headline': f"Breaking: {trend_query}",  # Create engaging headline
            'comprehensive_research': comprehensive_research,
            'source_urls': list(all_urls),
            'article_contents': all_content_pieces,
            'total_sources_processed': len(all_urls),
            'total_words_collected': total_words,
            'unique_content_pieces': len(all_content_pieces),
            'search_time': search_time,
            'search_method': 'google_trends_enhanced',
            'generated_at': datetime.now().isoformat()
        }
    
    def _content_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity between two content pieces (simple implementation)
        
        Returns:
            float: Similarity score between 0 and 1
        """
        if not content1 or not content2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _create_comprehensive_research(self, 
                                     trend_query: str,
                                     research_sections: List[str],
                                     content_pieces: List[Dict]) -> str:
        """Create comprehensive research summary from all collected data"""
        
        # Start with trend context
        research_parts = [
            f"TRENDING TOPIC ANALYSIS: {trend_query}",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # Add research from different queries
        if research_sections:
            research_parts.append("COMPREHENSIVE RESEARCH FROM MULTIPLE SEARCHES:")
            research_parts.append("-" * 50)
            
            for i, research in enumerate(research_sections, 1):
                if research and len(research.strip()) > 100:
                    research_parts.append(f"\nRESEARCH SECTION {i}:")
                    research_parts.append(research.strip())
                    research_parts.append("")
        
        # Add key content pieces
        if content_pieces:
            research_parts.append("\nKEY ARTICLE EXCERPTS:")
            research_parts.append("-" * 50)
            
            for i, content in enumerate(content_pieces[:5], 1):  # Top 5 pieces
                title = content.get('title', 'Unknown Title')
                content_text = content.get('content', '')
                
                if content_text and len(content_text) > 200:
                    # Take first 500 words of each piece
                    excerpt = ' '.join(content_text.split()[:500])
                    
                    research_parts.append(f"\nSOURCE {i}: {title}")
                    research_parts.append(excerpt)
                    research_parts.append("")
        
        return '\n'.join(research_parts)


def main():
    """Test the Google Trends Search Enhancer"""
    logger.info("🧪 TESTING GOOGLE TRENDS SEARCH ENHANCER")
    
    enhancer = GoogleTrendsSearchEnhancer()
    
    if not enhancer.available:
        logger.error("❌ Search enhancer not available - check API configuration")
        return
    
    # Test with a sample trend
    test_trend = "fernando mendoza"
    
    logger.info(f"🧪 Testing with trend: {test_trend}")
    
    result = enhancer.search_trend_comprehensive(test_trend)
    
    if result.get('status') == 'success':
        logger.info("🎉 Test successful!")
        logger.info(f"   📊 Sources: {result.get('total_sources_processed', 0)}")
        logger.info(f"   📝 Words: {result.get('total_words_collected', 0)}")
        logger.info(f"   ⏱️  Time: {result.get('search_time', 0):.2f}s")
    else:
        logger.error(f"❌ Test failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()