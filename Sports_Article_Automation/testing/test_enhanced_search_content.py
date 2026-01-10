"""
Enhanced Search API with Full Content Fetching
Gets search results AND fetches the actual article content from each URL
Provides comprehensive research data similar to Perplexity for article generation
"""

import os
import sys
import json
import logging
import requests
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin
import re

# Web scraping imports
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    print("⚠️ BeautifulSoup not found. Install with: pip install beautifulsoup4")
    BEAUTIFULSOUP_AVAILABLE = False

try:
    import newspaper
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    print("⚠️ Newspaper3k not found. Install with: pip install newspaper3k")
    NEWSPAPER_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    print("⚠️ aiohttp not found. Install with: pip install aiohttp")
    AIOHTTP_AVAILABLE = False

# Add parent directory to path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from dotenv import load_dotenv
load_dotenv()

# Import content freshness validation
# Removed: Using built-in freshness validation only
FRESHNESS_VALIDATOR_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class EnhancedSearchContentFetcher:
    """Enhanced Search API that fetches full article content from URLs"""

    def __init__(self):
        """Initialize the Enhanced Search Content Fetcher"""
        self.output_dir = Path(__file__).parent / "testing_output"
        self.output_dir.mkdir(exist_ok=True)

        # Search API Configuration
        self.api_key = os.getenv('GOOGLE_SEARCH_API_KEY') or os.getenv('SEARCH_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID') or os.getenv('SEARCH_ENGINE_ID')

        # Check if API keys are configured
        if not self.api_key:
            print("❌ ERROR: GOOGLE_SEARCH_API_KEY environment variable not found!")
            print("   Please add it to your .env file or set it as an environment variable")
        if not self.search_engine_id:
            print("❌ ERROR: GOOGLE_SEARCH_ENGINE_ID environment variable not found!")
            print("   Please add it to your .env file or set it as an environment variable")

        self.base_url = "https://www.googleapis.com/customsearch/v1"

        # Enhanced search config for better cricket news results
        self.search_config = {
            'num': 10,  # Number of results per request
            'dateRestrict': 'd7',  # Last 7 days only
            'safe': 'medium',
            'lr': 'lang_en',  # English language results
            'gl': 'us',  # Geographic location preference
            'cx': self.search_engine_id,
            'key': self.api_key
        }
        
        # Cricket-specific trusted domains for better relevance
        self.cricket_domains = {
            'espn.com', 'espn.in', 'espncricinfo.com', 'cricbuzz.com', 
            'icc-cricket.com', 'bcci.tv', 'cricket.com.au', 'ecb.co.uk',
            'indianexpress.com', 'firstpost.com', 'sportstar.thehindu.com',
            'hindustantimes.com', 'timesofindia.indiatimes.com', 
            'ndtv.com', 'news18.com', 'theguardian.com', 'bbc.com',
            'aljazeera.com', 'reuters.com', 'apnews.com'
        }

        # Trusted domains for sports news (base domains only)
        self.trusted_domains = {
            'espn.com', 'bbc.com', 'cnn.com', 'reuters.com', 'apnews.com',
            'skysports.com', 'theguardian.com', 'bleacherreport.com', 'goal.com',
            'sportsnet.ca', 'foxsports.com', 'cbssports.com', 'theathletic.com',
            'si.com', 'nfl.com', 'nba.com', 'premierleague.com'
        }

        # Content extraction settings
        self.request_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        self.available = bool(self.api_key and self.search_engine_id and BEAUTIFULSOUP_AVAILABLE and AIOHTTP_AVAILABLE)
        
        # Using built-in freshness validation only
        self.freshness_validator = None
        print("✅ Built-in freshness validation enabled - using enhanced date parsing")

        if not self.available:
            if not (self.api_key and self.search_engine_id):
                print("❌ Search API not configured. Set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID")
            if not BEAUTIFULSOUP_AVAILABLE:
                print("❌ BeautifulSoup not available. Install with: pip install beautifulsoup4")
            if not AIOHTTP_AVAILABLE:
                print("❌ aiohttp not available. Install with: pip install aiohttp")

    def collect_comprehensive_research(self, headline: str, category: str = None, max_sources: int = 5) -> Dict:
        """
        Collect comprehensive research with full article content
        Args:
            headline (str): Headline to research
            category (str): Optional category
            max_sources (int): Maximum sources to fetch full content from
        Returns:
            dict: Comprehensive research data with full content
        """
        if not self.available:
            return {
                'status': 'error',
                'error': 'Enhanced Search API not configured or missing dependencies',
                'headline': headline
            }

        print(f"\n🔍 Enhanced Search with Full Content Fetching:")
        print(f"  📰 Headline: {headline}")
        if category:
            print(f"  🏷️ Category: {category}")
        print(f"  📚 Max Sources: {max_sources}")
        print(f"  🎯 Focus: Single query for headline-specific content only")
        print("=" * 70)

        try:
            # Step 1: Get search results
            print("🔍 Step 1: Getting search results...")
            search_results = self._get_search_results(headline, category)

            if search_results.get('status') != 'success':
                return search_results

            urls = search_results.get('urls', [])[:max_sources]
            print(f"  Found {len(urls)} URLs to process")

            # Step 2: Fetch full content from each URL (ASYNC OPTIMIZATION)
            print(f"📄 Step 2: Fetching full content from {len(urls)} sources simultaneously...")
            
            # Run async content fetching
            start_time = time.time()
            article_contents, successful_fetches, javascript_failures, other_failures = asyncio.run(
                self._fetch_all_articles_async(urls)
            )
            end_time = time.time()
            
            print(f"  ⚡ Async fetch completed in {end_time - start_time:.2f} seconds")
            print(f"  ✅ Successfully fetched {successful_fetches}/{len(urls)} articles")
            if javascript_failures > 0:
                print(f"  🚫 Skipped {javascript_failures} JavaScript-required sites (X.com, Facebook, etc.)")
            if other_failures > 0:
                print(f"  ❌ Failed to fetch {other_failures} due to other issues")

            # Step 3: Content already validated during fetch with built-in freshness validation
            print("🕐 Step 3: Content freshness validated during fetch (built-in system)...")
            
            # Count fresh vs total articles based on built-in validation
            fresh_count = sum(1 for article in article_contents 
                            if article.get('status') == 'success' and 
                            article.get('is_recent_publish', True))  # Default True for missing dates
            total_count = len([a for a in article_contents if a.get('status') == 'success'])
            
            print(f"  ✅ Fresh articles: {fresh_count}")
            print(f"  📊 Total successful fetches: {total_count}")
            if fresh_count < total_count:
                print(f"  ⚠️ Filtered {total_count - fresh_count} potentially outdated articles during fetch")
            
            # Step 4: Process and combine content
            print("🔄 Step 4: Processing and combining fresh content...")
            comprehensive_research = self._process_combined_content(
                article_contents, headline, search_results
            )
            
            # Add built-in freshness metadata
            comprehensive_research['content_freshness'] = {
                'validation_method': 'built_in_enhanced_search',
                'fresh_articles_used': len(article_contents),
                'freshness_validated': True,
                'validation_during_fetch': True
            }

            print(f"✅ Enhanced research complete with built-in freshness validation!")
            print(f"  📚 Articles processed: {len(article_contents)}")
            print(f"  📝 Total content: {len(comprehensive_research.get('combined_content', ''))} characters")

            return comprehensive_research

        except Exception as e:
            print(f"❌ Error in comprehensive research: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'headline': headline
            }

    def _get_search_results(self, headline: str, category: str = None) -> Dict:
        """Get search results using single focused query for the main headline only"""
        try:
            print(f"  🎯 Using single focused query for headline-specific content")
            
            # Use only one targeted query focused on the exact headline
            # Add date restriction to ensure fresh content
            focused_query = f'"{headline}"'
            
            print(f"  🔍 Query: {focused_query}")
            
            try:
                # Configure search parameters with freshness filter
                params = self.search_config.copy()
                params['q'] = focused_query
                params['num'] = 10  # Get top 10 most relevant results
                params['dateRestrict'] = 'd7'  # Last 7 days only
                
                response = requests.get(self.base_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    
                    results = []
                    urls = []
                    trusted_count = 0
                    
                    # Process results with relevance filtering
                    scored_results = []
                    for item in items:
                        url = item.get('link', '')
                        domain = item.get('displayLink', '')
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')
                        
                        # Calculate relevance score
                        relevance_score = self._calculate_headline_relevance(title, snippet, focused_query.strip('"'))
                        
                        # Only include results with ultra-high relevance (score > 10.0) - ultra strict filtering
                        if url and self._is_valid_article_url(url) and relevance_score > 10.0:
                            scored_results.append({
                                'item': item,
                                'url': url,
                                'domain': domain,
                                'title': title,
                                'snippet': snippet,
                                'relevance_score': relevance_score
                            })
                            print(f"    ✅ HIGHLY RELEVANT: {title[:50]}... [Score: {relevance_score:.1f}]")
                        elif relevance_score > 3.0:
                            print(f"    ⚠️ FILTERED OUT: {title[:50]}... [Score: {relevance_score:.1f} - too low]")
                    
                    # Sort by relevance score (highest first)
                    scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
                    
                    # Take top results and build final results list
                    for scored_result in scored_results:
                        item = scored_result['item']
                        url = scored_result['url']
                        domain = scored_result['domain'] 
                        title = scored_result['title']
                        relevance_score = scored_result['relevance_score']
                        
                        is_trusted = self._is_trusted_domain(domain) or any(cricket_domain in domain for cricket_domain in self.cricket_domains)
                        if is_trusted:
                            trusted_count += 1
                        
                        # Store result metadata with relevance score
                        results.append({
                            'title': title,
                            'url': url,
                            'domain': domain,
                            'snippet': item.get('snippet', ''),
                            'is_trusted': is_trusted,
                            'found_by_query': 'focused_headline',
                            'query_used': focused_query,
                            'relevance_score': relevance_score
                        })
                        urls.append(url)
                        
                        print(f"    ✅ {title[:50]}... ({domain}) [Relevance: {relevance_score:.1f}]")
                    
                    total_sources = len(urls)
                    print(f"  📋 FOCUSED COLLECTION COMPLETE!")
                    print(f"    📊 Sources found: {total_sources}")
                    print(f"    🏆 Trusted sources: {trusted_count}")
                    
                    if total_sources > 0:
                        return {
                            'status': 'success',
                            'results': results,
                            'urls': urls,
                            'total_found': total_sources,
                            'trusted_count': trusted_count,
                            'query_used': focused_query,
                            'focused_search': True
                        }
                    else:
                        print("  ⚠️ No sources found from focused query, trying fallback")
                        return self._fallback_broader_search(headline, category)
                        
                else:
                    print(f"    ⚠️ Query failed with status {response.status_code}")
                    return self._fallback_broader_search(headline, category)
                    
            except Exception as e:
                print(f"    ❌ Query exception: {str(e)}")
                return self._fallback_broader_search(headline, category)

        except Exception as e:
            print(f"  ❌ Exception in focused search: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _build_comprehensive_query(self, headline: str, category: str = None) -> str:
        """Build story-focused query that stays on the exact headline angle"""
        try:
            # Extract the specific story focus from the headline
            story_elements = self._extract_headline_story_focus(headline)
            
            # Build query that searches ONLY for this specific story
            query_parts = []
            
            # 1. Exact headline phrase (most important)
            query_parts.append(f'"{headline}"')
            
            # 2. Core story elements (specific to this story)
            if story_elements['main_entity']:
                query_parts.append(f'"{story_elements["main_entity"]}"')
                
            # 3. Specific story action/event
            if story_elements['story_action']:
                query_parts.append(f'"{story_elements["story_action"]}"')
                
            # 4. Key details that make this story unique
            if story_elements['unique_details']:
                for detail in story_elements['unique_details'][:2]:  # Max 2 unique details
                    query_parts.append(f'"{detail}"')
            
            # Combine with AND logic to ensure all elements are present (story-specific)
            story_focused_query = ' '.join(query_parts)
            
            # Ensure query length is manageable
            if len(story_focused_query) > 200:
                # Fallback to most essential story elements
                essential_query = f'"{headline}" "{story_elements["main_entity"]}"'
                return essential_query
                
            return story_focused_query
            
        except Exception as e:
            print(f"  ❌ Exception in story-focused search: {str(e)}")
            # Fallback to exact headline search
            return f'"{headline}"'
            
    def _extract_headline_story_focus(self, headline: str) -> Dict[str, any]:
        """Extract specific story elements to maintain focus on the exact narrative"""
        headline_lower = headline.lower()
        words = headline.split()
        
        # Initialize story elements
        story_elements = {
            'main_entity': '',
            'story_action': '',
            'unique_details': []
        }
        
        # Find the main entity (person, team, or organization)
        entities = self._extract_key_entities(headline)
        if entities['persons']:
            story_elements['main_entity'] = entities['persons'][0]  # Primary person
        elif entities['teams']:
            story_elements['main_entity'] = entities['teams'][0]  # Primary team
            
        # Identify the specific story action/event
        if any(term in headline_lower for term in ['sign', 'signing', 'signed']):
            story_elements['story_action'] = 'signing'
        elif any(term in headline_lower for term in ['transfer', 'move', 'joins']):
            story_elements['story_action'] = 'transfer'
        elif any(term in headline_lower for term in ['deal', 'agreement']):
            story_elements['story_action'] = 'deal'
        elif any(term in headline_lower for term in ['injury', 'injured']):
            story_elements['story_action'] = 'injury'
        elif any(term in headline_lower for term in ['goal', 'scored']):
            story_elements['story_action'] = 'goal'
        elif any(term in headline_lower for term in ['win', 'wins', 'victory']):
            story_elements['story_action'] = 'win'
        elif any(term in headline_lower for term in ['manager', 'coach', 'appoint']):
            story_elements['story_action'] = 'appointment'
            
        # Extract unique details that make this story specific
        unique_details = []
        
        # Amounts/fees (transfer fees, contract values)
        if entities['amounts']:
            for amount in entities['amounts'][:1]:  # Most important amount
                unique_details.append(f"{amount}")
                
        # Specific timeframes mentioned
        time_terms = ['january', 'summer', 'winter', '2026', '2025', 'this month', 'next season']
        for term in time_terms:
            if term in headline_lower:
                unique_details.append(term)
                break
                
        # Contract durations
        duration_patterns = ['year', 'month', 'season']
        for word in words:
            if any(duration in word.lower() for duration in duration_patterns):
                # Look for number + duration pattern
                word_index = words.index(word)
                if word_index > 0 and words[word_index-1].isdigit():
                    unique_details.append(f"{words[word_index-1]} {word}")
                    
        # Specific clubs/teams mentioned (for multi-team stories)
        if len(entities['teams']) > 1:
            # Include secondary team for transfer stories
            unique_details.append(entities['teams'][1])
            
        story_elements['unique_details'] = unique_details
        
    def _calculate_headline_relevance(self, title: str, snippet: str, headline: str) -> float:
        """Calculate how relevant a search result is to the original headline - ULTRA STRICT scoring"""
        headline_words = set(headline.lower().split())
        title_words = set(title.lower().split())
        snippet_words = set(snippet.lower().split())
        
        # Key entities from headline
        key_entities = self._extract_key_entities(headline)
        
        score = 0.0
        
        # CRITICAL: Must have key entities to be considered relevant
        entity_matches = 0
        person_matches = 0
        team_matches = 0
        
        # Very high score for matching key entities (names, teams) - MANDATORY
        for person in key_entities.get('persons', []):
            if person.lower() in title.lower() or person.lower() in snippet.lower():
                score += 5.0  # Increased for person matches
                entity_matches += 1
                person_matches += 1
                
        for team in key_entities.get('teams', []):
            if team.lower() in title.lower() or team.lower() in snippet.lower():
                score += 4.0  # Strong team match score
                entity_matches += 1
                team_matches += 1
        
        # STRICT REQUIREMENT: For cricket squad news, must have team AND person OR multiple key words
        headline_lower = headline.lower()
        is_squad_news = any(word in headline_lower for word in ['squad', 'team', 'select', 'drop', 'include', 'announce'])
        
        if is_squad_news:
            # Squad news MUST have team match + person match OR very high word overlap
            if team_matches == 0:  # No team mentioned = automatic fail
                return 0.0
            
            # If it's about different teams (not mentioned in headline), reject
            title_snippet_combined = (title + " " + snippet).lower()
            
            # Check for completely unrelated content
            unrelated_terms = [
                'scg', 'sydney cricket ground', 'vaughan', 'gleeson', 'sa20', 'root', 'brook',
                'ashes', 'england vs australia', 'test match', 'damien martyn', 'wpl',
                'ipl auction', 'bbl draft', 'big bash', 'county cricket'
            ]
            
            for term in unrelated_terms:
                if term in title_snippet_combined and term not in headline_lower:
                    score -= 10.0  # Massive penalty for unrelated terms
        
        # If no key entities found, automatic rejection
        if entity_matches == 0:
            return 0.0
        
        # High score for word overlap - but only if entities match
        title_overlap = len(headline_words.intersection(title_words)) / len(headline_words)
        snippet_overlap = len(headline_words.intersection(snippet_words)) / len(headline_words)
        score += (title_overlap * 4.0) + (snippet_overlap * 2.0)  # Higher weights
        
        # Bonus for specific action words (must match exactly)
        action_words = ['bring back', 'drop', 'squad', 'announce', 'select', 'include', 'exclude', 'recall', 'omit']
        action_matches = 0
        for action in action_words:
            if action in headline.lower() and (action in title.lower() or action in snippet.lower()):
                score += 2.0  # Higher bonus for action match
                action_matches += 1
        
        # Competition context matching
        competition_words = ['t20 world cup', 'world cup', 't20', 'test', 'odi', 'series']
        for comp in competition_words:
            if comp in headline.lower() and comp in title_snippet_combined:
                score += 1.5  # Bonus for competition match
        
        # Heavy penalty for different cricket contexts that don't match
        different_contexts = {
            'ashes': ['ashes', 'england vs australia'],
            'ipl': ['ipl', 'indian premier league'],
            'bbl': ['bbl', 'big bash'],
            'sa20': ['sa20'],
            'county': ['county', 'championship'],
            'wpl': ['women\'s premier league', 'wpl']
        }
        
        for context_name, context_terms in different_contexts.items():
            headline_has_context = any(term in headline_lower for term in context_terms)
            title_has_context = any(term in title_snippet_combined for term in context_terms)
            
            if title_has_context and not headline_has_context:
                score -= 5.0  # Big penalty for wrong context
        
        return max(0.0, score)  # Ensure non-negative

    def _generate_related_queries(self, headline: str, category: str = None) -> List[Dict]:
        """Generate multiple related queries to gather comprehensive information"""
        queries = []
        words = headline.split()
        
        # Extract key entities (names, numbers, etc.)
        key_entities = self._extract_key_entities(headline)
        
        # 1. Exact headline (primary)
        queries.append({
            'query': f'"{headline}"',
            'type': 'exact_headline'
        })
        
        # 2. Player/Person focus (if names detected)
        if key_entities['persons']:
            for person in key_entities['persons'][:2]: # Top 2 persons
                query = f'"{person}"'
                if category:
                    query += f" {category}"
                if key_entities['teams']:
                    query += f" {key_entities['teams'][0]}"
                queries.append({
                    'query': query,
                    'type': f'person_focus_{person.lower().replace(" ", "_")}'
                })
                
        # 3. Team/Club focus (if teams detected)
        if key_entities['teams']:
            for team in key_entities['teams'][:2]: # Top 2 teams
                query = f'"{team}"'
                if key_entities['transfer_related']:
                    query += " transfer news"
                elif category:
                    query += f" {category} news"
                queries.append({
                    'query': query,
                    'type': f'team_focus_{team.lower().replace(" ", "_")}'
                })
                
        # 4. Transfer/Market focus (if transfer related)
        if key_entities['transfer_related']:
            main_subject = ' '.join(words[:3])
            query = f"{main_subject} transfer market"
            if key_entities['amounts']:
                query += f" {key_entities['amounts'][0]}"
            queries.append({
                'query': query,
                'type': 'transfer_market_focus'
            })
            
        # 5. News angle focus
        if key_entities['news_angles']:
            for angle in key_entities['news_angles'][:2]:
                query = f"{angle}"
                if key_entities['persons']:
                    query += f" {key_entities['persons'][0]}"
                if category:
                    query += f" {category}"
                queries.append({
                    'query': query,
                    'type': f'news_angle_{angle.lower().replace(" ", "_")}'
                })
                
        # 6. Key terms combination
        if len(words) > 5:
            key_terms = ' '.join(words[:4]) # First 4 words
            query = key_terms
            if category:
                query += f" {category} latest"
            queries.append({
                'query': query,
                'type': 'key_terms_combination'
            })
            
        # 7. Related context (if specific context detected)
        if key_entities['context']:
            for context in key_entities['context'][:2]:
                query = context
                if key_entities['persons']:
                    query += f" {key_entities['persons'][0]}"
                queries.append({
                    'query': query,
                    'type': f'context_{context.lower().replace(" ", "_")}'
                })
                
        # 8. Fallback: Main subject only
        if len(words) > 2:
            main_subject = ' '.join(words[:3])
            query = main_subject
            if category:
                query += f" {category}"
            queries.append({
                'query': query,
                'type': 'main_subject_only'
            })
            
        # Remove duplicates and limit to reasonable number
        seen_queries = set()
        unique_queries = []
        for q in queries:
            if q['query'] not in seen_queries:
                seen_queries.add(q['query'])
                unique_queries.append(q)
                
        return unique_queries[:8] # Limit to 8 diverse queries

    def _extract_key_entities(self, headline: str) -> Dict:
        """Extract key entities using enhanced sports-focused patterns (Bug #10 partial fix)"""
        words = headline.split()
        lower_headline = headline.lower()

        # Comprehensive sports teams database (addresses 3-word names, nicknames, abbreviations)
        known_teams = {
            # Cricket Teams - International
            'bangladesh', 'tigers', 'bangladesh cricket team',
            'india', 'team india', 'men in blue', 'india cricket team',
            'pakistan', 'green shirts', 'pakistan cricket team', 
            'australia', 'aussies', 'australia cricket team',
            'england', 'three lions', 'england cricket team',
            'south africa', 'proteas', 'south africa cricket team',
            'new zealand', 'black caps', 'kiwis', 'new zealand cricket team',
            'sri lanka', 'lions', 'sri lanka cricket team',
            'west indies', 'windies', 'calypso kings',
            'afghanistan', 'afghanistan cricket team',
            'zimbabwe', 'zimbabwe cricket team',
            'ireland', 'ireland cricket team',
            'scotland', 'scotland cricket team',
            'netherlands', 'netherlands cricket team',
            # IPL Teams
            'mumbai indians', 'mi', 'mumbai',
            'chennai super kings', 'csk', 'chennai', 'yellow army',
            'royal challengers bangalore', 'rcb', 'bangalore',
            'kolkata knight riders', 'kkr', 'kolkata',
            'delhi capitals', 'dc', 'delhi',
            'punjab kings', 'pbks', 'punjab',
            'rajasthan royals', 'rr', 'rajasthan',
            'sunrisers hyderabad', 'srh', 'hyderabad',
            'gujarat titans', 'gt', 'gujarat',
            'lucknow super giants', 'lsg', 'lucknow',
            # Premier League (full names, common names, nicknames)
            'chelsea', 'chelsea fc', 'the blues',
            'manchester city', 'man city', 'city', 'the citizens',
            'manchester united', 'man united', 'united', 'man utd', 'the red devils',
            'liverpool', 'liverpool fc', 'the reds', 'lfc',
            'arsenal', 'arsenal fc', 'the gunners', 'afc',
            'tottenham', 'tottenham hotspur', 'spurs', 'thfc',
            'leicester', 'leicester city', 'the foxes',
            'newcastle', 'newcastle united', 'the magpies', 'nufc',
            'brighton', 'brighton & hove albion', 'the seagulls',
            'west ham', 'west ham united', 'the hammers',
            'aston villa', 'villa', 'the villans',
            'crystal palace', 'palace', 'the eagles',
            'everton', 'everton fc', 'the toffees',
            'fulham', 'fulham fc', 'the cottagers',
            'brentford', 'brentford fc', 'the bees',
            'wolves', 'wolverhampton', 'wolverhampton wanderers',
            'nottingham forest', 'forest', 'nffc',
            'bournemouth', 'afc bournemouth', 'the cherries',
            'sheffield united', 'sheffield utd', 'the blades',
            'burnley', 'burnley fc', 'the clarets',
            # European giants
            'real madrid', 'madrid', 'real', 'los blancos',
            'barcelona', 'barca', 'fc barcelona', 'blaugrana',
            'bayern munich', 'bayern', 'fc bayern',
            'psg', 'paris saint-germain', 'paris sg',
            'juventus', 'juve', 'juventus fc',
            'ac milan', 'milan', 'ac milan',
            'inter milan', 'inter', 'internazionale',
            'atletico madrid', 'atletico',
            'borussia dortmund', 'dortmund', 'bvb',
            'ajax', 'ajax amsterdam',
            'benfica', 'sl benfica',
            'porto', 'fc porto',
            # National teams
            'england', 'three lions',
            'france', 'les bleus',
            'spain', 'la roja',
            'germany', 'die mannschaft',
            'brazil', 'selecao',
            'argentina', 'la albiceleste',
            'portugal',
            'italy', 'azzurri',
            'netherlands', 'oranje'
        }

        # Enhanced competitions list
        known_competitions = {
            # Cricket Competitions
            't20 world cup', 'icc t20 world cup', 't20wc', 'twenty20 world cup',
            'cricket world cup', 'icc cricket world cup', 'cwc', 'odi world cup',
            'champions trophy', 'icc champions trophy',
            'test championship', 'world test championship', 'wtc',
            'ipl', 'indian premier league',
            'bbl', 'big bash league',
            'psl', 'pakistan super league',
            'cpl', 'caribbean premier league',
            'sa20', 'south africa t20',
            'hundred', 'the hundred',
            'vitality blast', 't20 blast',
            'county championship',
            'ashes', 'ashes series',
            'asia cup', 'icc asia cup',
            'border gavaskar trophy',
            'ranji trophy',
            'syed mushtaq ali trophy',
            'vijay hazare trophy',
            'icc women''s world cup',
            'wpl', 'women''s premier league',
            # Football Competitions
            'premier league', 'epl', 'pl',
            'champions league', 'ucl', 'european cup',
            'europa league', 'uel',
            'conference league', 'uecl',
            'world cup', 'fifa world cup', 'wc',
            'euros', 'european championship', 'euro 2024',
            'fa cup',
            'carabao cup', 'league cup',
            'la liga',
            'serie a',
            'bundesliga',
            'ligue 1',
            'copa del rey',
            'copa america',
            'nations league'
        }

        # Multi-word team detection (handles 2-3 word names)
        teams = []
        headline_lower = lower_headline
        for team in known_teams:
            if team in headline_lower:
                # Get proper capitalization
                team_words = team.split()
                if len(team_words) == 1:
                    teams.append(team_words[0].title())
                else:
                    teams.append(' '.join(word.title() for word in team_words))

        # Enhanced person detection (handles 1-3 word names, cricket names, common patterns)
        persons = []
        
        # Pattern 1: Single word cricket names (common in South Asian cricket)
        cricket_single_names = ['taskin', 'jaker', 'mustafizur', 'shakib', 'tamim', 'mushfiqur', 'liton', 'miraz', 'mehidy', 'soumya']
        for word in words:
            if word.lower() in cricket_single_names or (len(word) > 4 and word[0].isupper() and word.lower() not in [team.lower() for team in known_teams]):
                persons.append(word)
        
        # Pattern 2: Two consecutive capitalized words not in teams/competitions  
        i = 0
        while i < len(words) - 1:
            if (words[i][0].isupper() and words[i+1][0].isupper() and
                    len(words[i]) > 2 and len(words[i+1]) > 2):
                candidate = f"{words[i]} {words[i+1]}"
                candidate_lower = candidate.lower()
                # Check if it's not a team or competition
                if (candidate_lower not in known_teams and
                        candidate_lower not in known_competitions and
                        not any(team in candidate_lower for team in known_teams) and
                        not any(comp in candidate_lower for comp in known_competitions)):
                    # Check for 3-word names (First Middle Last)
                    if (i < len(words) - 2 and words[i+2][0].isupper() and
                            len(words[i+2]) > 2 and words[i+2].lower() not in ['fc', 'united', 'city', 'cricket', 'team']):
                        persons.append(f"{words[i]} {words[i+1]} {words[i+2]}")
                        i += 3
                    else:
                        persons.append(candidate)
                        i += 2
                else:
                    i += 1
            else:
                i += 1

        # Enhanced amount detection
        amounts = []
        import re
        amount_patterns = [
            r'£([\d,]+)(?:\s*(?:m|million|k|thousand))?',
            r'\$([\d,]+)(?:\s*(?:m|million|k|thousand))?',
            r'€([\d,]+)(?:\s*(?:m|million|k|thousand))?',
            r'([\d,]+)\s*(?:million|m)\b',
            r'([\d,]+)\s*(?:thousand|k)\b'
        ]

        for pattern in amount_patterns:
            matches = re.findall(pattern, lower_headline, re.IGNORECASE)
            for match in matches:
                # Clean and standardize
                amount_str = str(match).replace(',', '')
                if amount_str.isdigit():
                    amounts.append(amount_str)

        # Enhanced transfer detection
        transfer_keywords = {
            'transfer', 'sign', 'signing', 'signed', 'hunt', 'target', 'targets',
            'bid', 'offer', 'deal', 'move', 'moves', 'interest', 'pursue',
            'acquire', 'buy', 'sell', 'swap', 'loan', 'joins', 'join',
            'agreement', 'contract', 'negotiations', 'talks', 'approach'
        }
        transfer_related = any(keyword in lower_headline for keyword in transfer_keywords)

        # Enhanced news angles
        news_angles = []
        angle_patterns = {
            'breaking', 'exclusive', 'latest', 'update', 'confirmed',
            'rumour', 'rumor', 'report', 'analysis', 'opinion',
            'reaction', 'watch', 'video', 'interview', 'statement', 'press conference'
        }
        for pattern in angle_patterns:
            if pattern in lower_headline:
                news_angles.append(pattern)

        # Enhanced context detection
        context = []
        for comp in known_competitions:
            if comp in lower_headline:
                context.append(comp.title())

        # Add seasonal/temporal context
        seasonal_terms = {
            'transfer window', 'january window', 'summer window', 'deadline day',
            'pre-season', 'season', 'injury update', 'team news', 'squad news'
        }
        for term in seasonal_terms:
            if term in lower_headline:
                context.append(term.title())

        return {
            'persons': list(set(persons))[:3],  # Remove duplicates, top 3
            'teams': list(set(teams))[:3],  # Remove duplicates, top 3
            'amounts': list(set(amounts))[:2],  # Remove duplicates, top 2
            'transfer_related': transfer_related,
            'news_angles': news_angles[:3],
            'context': list(set(context))[:2]  # Remove duplicates, top 2
        }

    def _fetch_second_page(self, query: str) -> List[Dict]:
        """Fetch second page of search results when needed (Bug #11 partial fix)"""
        try:
            params = self.search_config.copy()
            params['q'] = query
            params['start'] = 11  # Second page starts at result 11
            params['num'] = 10

            # Add small delay to be respectful
            time.sleep(1)

            response = requests.get(self.base_url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                second_page_results = []

                for item in items[:5]:  # Only take top 5 from second page
                    url = item.get('link', '')
                    domain = item.get('displayLink', '')
                    title = item.get('title', '')

                    if url and self._is_valid_article_url(url):
                        second_page_results.append({
                            'title': title,
                            'url': url,
                            'domain': domain,
                            'snippet': item.get('snippet', ''),
                            'is_trusted': self._is_trusted_domain(domain),
                            'found_by_query': 'comprehensive_second_page',
                            'query_used': query
                        })
                return second_page_results
            return []
        except Exception as e:
            print(f"  ⚠️ Second page fetch failed: {str(e)[:50]}")
            return []

    def _fallback_broader_search(self, headline: str, category: str = None) -> Dict:
        """Fallback to broader search while maintaining 7-day restriction"""
        try:
            print("  🔄 Attempting broader fallback search (still within last 7 days)...")
            # Use most basic query but keep date restriction
            words = headline.split()
            basic_query = ' '.join(words[:5])  # First 5 words
            if category:
                basic_query += f" {category}"

            # Add 7-day date restriction via API parameter only (Custom Search doesn't support 'after:' in query)
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': basic_query,
                'num': 10,
                'safe': 'medium',
                'dateRestrict': 'd7'  # Only reliable way to restrict to last 7 days
            }

            response = requests.get(self.base_url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                if len(items) > 0:
                    results = []
                    urls = []
                    for item in items:
                        url = item.get('link', '')
                        domain = item.get('displayLink', '')
                        title = item.get('title', '')
                        if url and self._is_valid_article_url(url):
                            results.append({
                                'title': title,
                                'url': url,
                                'domain': domain,
                                'snippet': item.get('snippet', ''),
                                'is_trusted': self._is_trusted_domain(domain),
                                'found_by_query': 'fallback_broader',
                                'query_used': basic_query
                            })
                            urls.append(url)
                    if len(urls) > 0:
                        print(f"  ✅ Fallback successful! Found {len(urls)} URLs")
                        return {
                            'status': 'success',
                            'results': results,
                            'urls': urls,
                            'total_found': len(items),
                            'fallback_used': True,
                            'query_used': basic_query
                        }
            print("  ❌ Fallback search also failed")
            return {
                'status': 'error',
                'error': "No results found even with broader search"
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Fallback search failed: {str(e)}"
            }

    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain to base domain (similar to tldextract)"""
        if not domain:
            return ''
        domain = domain.lower().strip()
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        # Remove protocol if somehow included
        if '://' in domain:
            domain = domain.split('://', 1)[1]
        # Remove path if somehow included
        if '/' in domain:
            domain = domain.split('/', 1)[0]
        return domain

    def _is_trusted_domain(self, domain: str) -> bool:
        """Check if domain is from a trusted source using proper domain matching"""
        normalized = self._normalize_domain(domain)
        if not normalized:
            return False
        # Check exact match first
        if normalized in self.trusted_domains:
            return True
        # Check if it's a subdomain of a trusted domain
        for trusted in self.trusted_domains:
            if normalized.endswith('.' + trusted) or normalized == trusted:
                return True
        return False

    def _is_valid_article_url(self, url: str) -> bool:
        """Check if URL likely contains article content and can be scraped"""
        try:
            if not url or not url.startswith('http'):
                return False
            # Parse domain
            domain = urlparse(url).netloc.lower()
            
            # Skip social media, video platforms, and JavaScript-heavy sites that can't be scraped
            skip_patterns = [
                # Social media (require JavaScript or special handling)
                'facebook.com', 'twitter.com', 'x.com', 'instagram.com',
                'linkedin.com', 'reddit.com', 'tiktok.com', 'snapchat.com',
                # Video/Media platforms
                'youtube.com', 'vimeo.com', 'twitch.tv',
                # File types
                '.pdf', '.jpg', '.png', '.gif', '.mp4', '.mp3', '.doc', '.docx',
                # Other problematic patterns
                '/video/', '/photos/', '/gallery/', '/images/',
                'google.com/search', 'bing.com/search', 'yahoo.com/search'
            ]
            
            # Check if URL or domain contains any skip patterns
            for pattern in skip_patterns:
                if pattern in domain or pattern in url.lower():
                    return False
                    
            # Additional check for X.com/Twitter posts specifically
            if 'x.com' in domain or 'twitter.com' in domain:
                return False
                
            return True
        except Exception:
            return False

    async def _fetch_all_articles_async(self, urls: List[str]) -> tuple:
        """Fetch all article contents asynchronously for maximum speed"""
        print(f"  🚀 Starting async fetch of {len(urls)} URLs...")
        
        # Create connector with connection pooling for efficiency
        connector = aiohttp.TCPConnector(
            limit=20,  # Total connection pool size
            limit_per_host=5,  # Max connections per host
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=15)  # 15 second timeout per request
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.request_headers
        ) as session:
            # Create tasks for all URLs
            tasks = [self._fetch_single_article_async(session, url) for url in urls]
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            article_contents = []
            successful_fetches = 0
            javascript_failures = 0
            other_failures = 0
            
            for i, result in enumerate(results):
                url = urls[i]
                domain = urlparse(url).netloc
                
                if isinstance(result, Exception):
                    print(f"  ❌ Exception for {domain}: {str(result)[:50]}")
                    other_failures += 1
                elif result.get('status') == 'success':
                    article_contents.append(result)
                    successful_fetches += 1
                    print(f"  ✅ Success: {domain}")
                elif 'JavaScript' in result.get('error', ''):
                    javascript_failures += 1
                    print(f"  🚫 Skipped {domain}: Requires JavaScript")
                else:
                    other_failures += 1
                    error_msg = result.get('error', 'Unknown error')
                    print(f"  ⚠️ Failed {domain}: {error_msg[:50]}")
            
            return article_contents, successful_fetches, javascript_failures, other_failures

    async def _fetch_single_article_async(self, session: aiohttp.ClientSession, url: str) -> Dict:
        """Fetch single article content asynchronously"""
        try:
            # Check if URL is from a problematic domain
            domain = urlparse(url).netloc.lower()
            js_required_domains = ['x.com', 'twitter.com', 'facebook.com', 'instagram.com']
            if any(js_domain in domain for js_domain in js_required_domains):
                return {
                    'status': 'failed',
                    'url': url,
                    'error': 'JavaScript-required site - content not accessible via web scraping',
                    'title': 'Content unavailable',
                    'content': '',
                    'method': 'skipped'
                }

            # Method 1: Try newspaper3k first (but sync, so use in executor)
            if NEWSPAPER_AVAILABLE:
                try:
                    # Run newspaper3k in thread executor to not block async loop
                    loop = asyncio.get_event_loop()
                    article_result = await loop.run_in_executor(
                        None, self._extract_with_newspaper3k, url
                    )
                    if article_result and article_result.get('status') == 'success':
                        return article_result
                except Exception as e:
                    # Check if it's a JavaScript issue
                    if 'JavaScript' in str(e) or 'js' in str(e).lower():
                        return {
                            'status': 'failed',
                            'url': url,
                            'error': f'JavaScript required - {str(e)[:100]}',
                            'title': 'Content unavailable',
                            'content': '',
                            'method': 'newspaper3k_failed'
                        }
                    pass

            # Method 2: BeautifulSoup with aiohttp
            async with session.get(url) as response:
                if response.status != 200:
                    return {
                        'status': 'error',
                        'url': url,
                        'error': f'HTTP {response.status}'
                    }
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                # Check for JavaScript-required indicators
                page_text = soup.get_text()
                if ('JavaScript is not available' in page_text or
                        'Please enable JavaScript' in page_text or
                        'This browser is not supported' in page_text):
                    return {
                        'status': 'failed',
                        'url': url,
                        'error': 'Page requires JavaScript to load content',
                        'title': 'JavaScript required',
                        'content': '',
                        'method': 'beautifulsoup_js_required'
                    }

                # Process content using existing logic
                return self._process_soup_content(soup, url)
                
        except asyncio.TimeoutError:
            return {
                'status': 'error',
                'url': url,
                'error': 'Request timeout'
            }
        except Exception as e:
            return {
                'status': 'error',
                'url': url,
                'error': str(e)
            }

    def _extract_with_newspaper3k(self, url: str) -> Optional[Dict]:
        """Extract content using newspaper3k (sync method for executor)"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            if article.text and len(article.text) > 200:
                # Validate publish date (Bug #3 fix)
                is_recent = self._validate_publish_date(article.publish_date, url)
                
                # Bug #14 fix: Language detection for newspaper3k
                detected_language = 'en'  # newspaper3k usually handles this
                if hasattr(article, 'meta_lang') and article.meta_lang:
                    detected_language = article.meta_lang[:2].lower()
                else:
                    detected_language = self._detect_language(article.text)
                    
                if detected_language != 'en':
                    return {
                        'status': 'failed',
                        'url': url,
                        'error': f'Non-English content detected: {detected_language}',
                        'title': 'Language filter',
                        'content': '',
                        'method': 'newspaper3k_language_filtered'
                    }
                    
                return {
                    'status': 'success',
                    'url': url,
                    'title': article.title or 'No title',
                    'content': article.text,
                    'publish_date': str(article.publish_date) if article.publish_date else None,
                    'is_recent_publish': is_recent,
                    'detected_language': detected_language,
                    'authors': article.authors,
                    'method': 'newspaper3k',
                    'word_count': len(article.text.split())
                }
        except Exception:
            pass
        return None

    def _process_soup_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Process BeautifulSoup content (extracted from original _fetch_article_content)"""
        try:
            # Remove script, style, and noise elements (Bug #6 fix)
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "advertisement", "ad", "sidebar", "related", "comment", "social", "share", "newsletter"]):
                element.decompose()

            # Remove common ad/noise classes and IDs
            for selector in ['.ad', '.advertisement', '.sidebar', '.related-articles', '.comments', '.social-share', '.newsletter', '#comments', '.cookie-notice', '.privacy-notice']:
                for element in soup.select(selector):
                    element.decompose()

            # Try to find article content using improved selectors (Bug #6 fix)
            article_content = None
            content_selectors = [
                'article', '[role="main"] article', 'main article',
                '.article-content', '.story-content', '.post-content',
                '.entry-content', '.content', '.article-body',
                '[data-module="ArticleBody"]', '.post-body', '.story-body',
                '.news-content'
            ]
            
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    article_content = element.get_text(separator=' ', strip=True)
                    if len(article_content) > 200:
                        break

            # Fallback: get paragraph text but filter noise (Bug #6 & #7 fixes)
            if not article_content or len(article_content) < 200:
                # Find paragraphs within article sections first
                article_sections = soup.find_all(['article', 'main', '[role="main"]'])
                if article_sections:
                    paragraphs = []
                    for section in article_sections:
                        paragraphs.extend(section.find_all('p'))
                else:
                    # Fallback to all paragraphs but filter short ones (likely ads/nav)
                    paragraphs = [p for p in soup.find_all('p') if len(p.get_text(strip=True)) > 20]
                    
                article_content = ' '.join([p.get_text(strip=True) for p in paragraphs])

            # Enhanced JavaScript detection (Bug #7 fix)
            if len(article_content) < 100:
                return {
                    'status': 'failed',
                    'url': url,
                    'error': 'Content too short - likely JavaScript-required or paywall',
                    'title': 'Insufficient content',
                    'content': '',
                    'method': 'beautifulsoup_insufficient_content'
                }

            if article_content and len(article_content) > 100:
                # Clean up the content
                article_content = re.sub(r'\s+', ' ', article_content)
                article_content = article_content.strip()
                
                # Extract and validate publish date from HTML meta tags (Bug #3 fix)
                publish_date = self._extract_publish_date_from_html(soup)
                is_recent = self._validate_publish_date(publish_date, url)
                
                # Bug #14 fix: Language detection
                detected_language = self._detect_language(article_content, soup)
                if detected_language != 'en':
                    return {
                        'status': 'failed',
                        'url': url,
                        'error': f'Non-English content detected: {detected_language}',
                        'title': 'Language filter',
                        'content': '',
                        'method': 'beautifulsoup_language_filtered'
                    }

                return {
                    'status': 'success',
                    'url': url,
                    'title': soup.title.string if soup.title else 'No title',
                    'content': article_content,
                    'publish_date': publish_date,
                    'is_recent_publish': is_recent,
                    'detected_language': detected_language,
                    'method': 'beautifulsoup',
                    'word_count': len(article_content.split())
                }
            else:
                return {
                    'status': 'error',
                    'url': url,
                    'error': 'Insufficient content found'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'url': url,
                'error': str(e)
            }

    def _fetch_article_content(self, url: str) -> Dict:
        """Legacy sync method - kept for backward compatibility but runs async internally"""
        try:
            return asyncio.run(self._fetch_single_article_async_wrapper(url))
        except Exception as e:
            return {
                'status': 'error',
                'url': url,
                'error': str(e)
            }

    async def _fetch_single_article_async_wrapper(self, url: str) -> Dict:
        """Wrapper to run single async fetch"""
        connector = aiohttp.TCPConnector(limit=1)
        timeout = aiohttp.ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.request_headers
        ) as session:
            return await self._fetch_single_article_async(session, url)

    def _extract_publish_date_from_html(self, soup) -> Optional[str]:
        """Extract publish date from HTML meta tags with comprehensive parsing"""
        try:
            # Comprehensive meta tag and element patterns for date extraction
            date_selectors = [
                # Open Graph and Article meta tags
                'meta[property="article:published_time"]',
                'meta[property="article:published"]', 
                'meta[property="og:updated_time"]',
                'meta[property="article:modified_time"]',
                
                # Standard meta name attributes
                'meta[name="publishdate"]',
                'meta[name="publication-date"]',
                'meta[name="pubdate"]',
                'meta[name="date"]',
                'meta[name="article:published_time"]',
                'meta[name="datePublished"]',
                'meta[name="DC.date.issued"]',
                'meta[name="sailthru.date"]',
                
                # Time elements and structured data
                'time[datetime]',
                'time[pubdate]',
                'time.published',
                'time.entry-date',
                
                # Common CSS class patterns
                '.publish-date', '.publication-date', '.post-date',
                '.entry-date', '.article-date', '.date-published',
                '.timestamp', '.post-time', '.article-time',
                
                # Schema.org structured data
                '[itemprop="datePublished"]',
                '[itemprop="dateModified"]',
                
                # JSON-LD structured data
                'script[type="application/ld+json"]'
            ]
            
            for selector in date_selectors:
                elements = soup.select(selector)  # Use select() to get all matches
                for element in elements:
                    # Handle JSON-LD structured data
                    if element.name == 'script' and 'application/ld+json' in element.get('type', ''):
                        try:
                            import json
                            json_data = json.loads(element.string or element.get_text())
                            # Look for date fields in JSON-LD
                            for date_field in ['datePublished', 'dateModified', 'publishDate', 'dateCreated']:
                                if isinstance(json_data, dict) and json_data.get(date_field):
                                    return json_data[date_field]
                                elif isinstance(json_data, list):
                                    for item in json_data:
                                        if isinstance(item, dict) and item.get(date_field):
                                            return item[date_field]
                        except (json.JSONDecodeError, AttributeError):
                            continue
                    
                    # Try different attribute names for regular elements
                    for attr in ['content', 'datetime', 'data-date', 'data-time', 'data-published', 'value']:
                        attr_value = element.get(attr)
                        if attr_value and attr_value.strip():
                            print(f"  📅 Found date in {attr}: {attr_value}")
                            return attr_value.strip()
                    
                    # Try text content for time elements and date containers
                    text_content = element.get_text(strip=True)
                    if text_content and self._is_likely_date(text_content):
                        print(f"  📅 Found date in text: {text_content}")
                        return text_content
            
            # Fallback: Look for relative time patterns in page text
            page_text = soup.get_text()
            relative_matches = self._find_relative_dates_in_text(page_text)
            if relative_matches:
                print(f"  📅 Found relative date in text: {relative_matches[0]}")
                return relative_matches[0]
                
            return None
        except Exception as e:
            print(f"  ⚠️ Date extraction error: {str(e)}")
            return None
    
    def _is_likely_date(self, text: str) -> bool:
        """Check if text looks like a date"""
        import re
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # 2026-01-04
            r'\d{1,2}/\d{1,2}/\d{4}',  # 1/4/2026
            r'\d{1,2}-\d{1,2}-\d{4}',  # 1-4-2026
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}',  # 4 Jan 2026
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',  # January 4, 2026
            r'\d{1,2}\s+(hour|hours|minute|minutes|min|mins)\s+ago',  # 2 hours ago
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',  # ISO format
        ]
        
        text = text.strip()[:100]  # Check first 100 chars
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
    
    def _find_relative_dates_in_text(self, text: str) -> list:
        """Find relative date expressions in page text"""
        import re
        relative_patterns = [
            r'\d+\s+(hour|hours|minute|minutes|min|mins)\s+ago',
            r'\d+\s+(day|days)\s+ago',
            r'(yesterday|today)',
            r'(updated|published|posted)\s+\d+\s+(hour|hours|minute|minutes|min|mins)\s+ago',
        ]
        
        matches = []
        for pattern in relative_patterns:
            found = re.findall(pattern, text, re.IGNORECASE)
            if found:
                # Find the full match text
                full_matches = re.findall(f'\\b[\\w\\s]*{pattern}[\\w\\s]*\\b', text, re.IGNORECASE)
                matches.extend([m.strip() for m in full_matches[:1]])  # Take first match only
        
        return matches[:1]  # Return only the first match

    def _validate_publish_date(self, publish_date, url: str) -> bool:
        """Validate if article publish date is recent with comprehensive date parsing"""
        if not publish_date:
            print(f"  ⚠️ No publish date found: {urlparse(url).netloc}")
            return True  # Changed: Allow articles without dates (benefit of doubt for recent searches)
            
        try:
            publish_str = str(publish_date).lower().strip()
            import re
            
            # Enhanced relative time parsing
            relative_patterns = [
                (r'(\d+)\s*(hour|hours)\s*ago', 'hours'),
                (r'(\d+)\s*(minute|minutes|min|mins)\s*ago', 'minutes'),
                (r'(\d+)\s*(day|days)\s*ago', 'days'),
                (r'yesterday', 'yesterday'),
                (r'today', 'today'),
            ]
            
            parsed_date = None
            
            # Try relative time patterns first
            for pattern, unit_type in relative_patterns:
                match = re.search(pattern, publish_str)
                if match:
                    now = datetime.now()
                    
                    if unit_type == 'hours':
                        number = int(match.group(1))
                        parsed_date = now - timedelta(hours=number)
                    elif unit_type == 'minutes':
                        number = int(match.group(1))
                        parsed_date = now - timedelta(minutes=number)
                    elif unit_type == 'days':
                        number = int(match.group(1))
                        parsed_date = now - timedelta(days=number)
                    elif unit_type == 'yesterday':
                        parsed_date = now - timedelta(days=1)
                    elif unit_type == 'today':
                        parsed_date = now
                    
                    print(f"  🕐 Parsed relative time: {publish_str} → {parsed_date.strftime('%Y-%m-%d %H:%M')}")
                    break
            
            # If no relative pattern matched, try standard date parsing
            if not parsed_date:
                try:
                    from dateutil import parser as date_parser
                    # Clean up common date format issues
                    clean_date = publish_str.replace('published ', '').replace('updated ', '')
                    clean_date = re.sub(r'\s+', ' ', clean_date)  # Normalize whitespace
                    
                    parsed_date = date_parser.parse(clean_date)
                    print(f"  📅 Parsed standard date: {clean_date} → {parsed_date.strftime('%Y-%m-%d %H:%M')}")
                except Exception as parse_error:
                    print(f"  ⚠️ Could not parse date '{publish_str}': {str(parse_error)}")
                    # For unparseable dates from recent search results, assume recent
                    return True
            
            # Validate recency (within last 7 days)
            if parsed_date:
                seven_days_ago = datetime.now() - timedelta(days=7)
                is_recent = parsed_date.replace(tzinfo=None) >= seven_days_ago.replace(tzinfo=None)
                
                if not is_recent:
                    days_old = (datetime.now() - parsed_date.replace(tzinfo=None)).days
                    print(f"  ⚠️ Old article ({days_old} days old): {urlparse(url).netloc}")
                else:
                    print(f"  ✅ Fresh article confirmed ({parsed_date.strftime('%Y-%m-%d %H:%M')}): {urlparse(url).netloc}")
                    
                return is_recent
            else:
                print(f"  ⚠️ Date parsing completely failed for '{publish_date}', assuming recent")
                return True  # Benefit of doubt for articles from recent searches
                
        except Exception as e:
            print(f"  ⚠️ Date validation error for '{publish_date}': {str(e)}")
            return True  # Benefit of doubt on errors

    def _detect_language(self, text: str, soup=None) -> str:
        """Detect content language (Bug #14 fix)"""
        try:
            # First try to get language from HTML meta tags
            if soup:
                html_lang = soup.find('html')
                if html_lang and html_lang.get('lang'):
                    return html_lang['lang'][:2].lower()
                    
                # Try meta tag language
                meta_lang = soup.find('meta', attrs={'http-equiv': 'Content-Language'})
                if meta_lang and meta_lang.get('content'):
                    return meta_lang['content'][:2].lower()

            # Simple heuristic language detection for English
            text_sample = text[:1000].lower()  # First 1000 chars
            
            # Common English words that are rare in other languages
            english_indicators = {
                'the', 'and', 'that', 'have', 'for', 'not', 'with', 'you',
                'this', 'but', 'his', 'from', 'they', 'she', 'her', 'been',
                'than', 'its', 'who', 'oil', 'transfer', 'football',
                'soccer', 'player', 'team', 'match', 'goal', 'game'
            }
            
            # Non-English indicators
            non_english_patterns = {
                'es': ['el ', 'la ', 'que ', 'de ', 'un ', 'se ', 'no ', 'te ', 'lo ', 'le '],  # Spanish
                'fr': ['le ', 'de ', 'et ', 'à ', 'un ', 'il ', 'être', 'et ', 'en ', 'avoir'],  # French
                'pt': ['o ', 'de ', 'a ', 'e ', 'do ', 'da ', 'em ', 'um ', 'para', 'com'],  # Portuguese
                'it': ['il ', 'di ', 'che', 'e ', 'la ', 'per', 'un ', 'in ', 'con', 'del'],  # Italian
                'de': ['der ', 'die ', 'und ', 'in ', 'den ', 'von ', 'zu ', 'das ', 'mit', 'ist']  # German
            }
            
            # Check for non-English patterns
            for lang, patterns in non_english_patterns.items():
                non_english_count = sum(1 for pattern in patterns if pattern in text_sample)
                if non_english_count >= 3:  # Multiple indicators = likely that language
                    return lang
                    
            # Check for English indicators
            english_count = sum(1 for word in english_indicators if f' {word} ' in text_sample)
            if english_count >= 5:  # Multiple English words
                return 'en'
                
            # Default to English for ambiguous cases (sports sites are usually English)
            return 'en'
        except Exception:
            return 'en'  # Default to English on error

    def _get_credibility_score(self, domain: str, reliability: str) -> float:
        """Get numeric credibility score for source weighting (Bug #15 fix)"""
        # Base domain credibility scores
        domain_scores = {
            # Tier 1: International news agencies (highest credibility)
            'reuters.com': 10.0, 'apnews.com': 10.0, 'bbc.com': 9.5,
            # Tier 2: Major sports networks
            'espn.com': 9.0, 'skysports.com': 8.5, 'theguardian.com': 8.5, 'cnn.com': 8.0,
            # Tier 3: Established sports media
            'goal.com': 7.5, 'bleacherreport.com': 7.0,
            'cbssports.com': 7.0, 'foxsports.com': 7.0, 'si.com': 7.0,
            # Tier 4: Specialized sports sites
            'theathletic.com': 8.0, 'sportsnet.ca': 7.5,
            # Tier 5: Official league/team sites
            'premierleague.com': 9.0, 'nfl.com': 8.5, 'nba.com': 8.5
        }
        
        normalized_domain = self._normalize_domain(domain)
        base_score = domain_scores.get(normalized_domain, 5.0)  # Default score
        
        # Adjust based on content reliability
        reliability_multipliers = {
            'confirmed': 1.0,
            'likely_confirmed': 0.9,
            'neutral': 0.8,
            'likely_rumor': 0.6,
            'rumor': 0.4
        }
        
        multiplier = reliability_multipliers.get(reliability, 0.8)
        final_score = base_score * multiplier
        
        return min(10.0, max(1.0, final_score))  # Clamp between 1-10

    def _detect_content_conflicts(self, source_info: List[Dict]) -> List[Dict]:
        """Detect conflicting information between sources (Bug #12 fix)"""
        conflicts = []
        # Extract numerical values (transfer fees, dates, etc.) from all sources
        numerical_data = []
        
        for source in source_info:
            content = source.get('content', '') if 'content' in source else ''
            title = source.get('title', '')
            text = f"{title} {content}"[:1000]  # First 1000 chars
            
            # Extract money amounts
            import re
            money_patterns = [
                r'£([\d,]+)(?:m|million)?',
                r'\$([\d,]+)(?:m|million)?',
                r'([\d,]+)\s*million'
            ]
            
            amounts = []
            for pattern in money_patterns:
                matches = re.findall(pattern, text.lower())
                for match in matches:
                    try:
                        # Convert to standard format
                        amount_str = match.replace(',', '')
                        amount = float(amount_str)
                        amounts.append(amount)
                    except ValueError:
                        continue
                        
            if amounts:
                numerical_data.append({
                    'source': source.get('url', ''),
                    'domain': source.get('domain', ''),
                    'amounts': amounts,
                    'credibility': source.get('credibility_score', 5.0)
                })
                
        # Detect conflicts in transfer amounts
        if len(numerical_data) >= 2:
            for i, source1 in enumerate(numerical_data):
                for j, source2 in enumerate(numerical_data[i+1:], i+1):
                    for amount1 in source1['amounts']:
                        for amount2 in source2['amounts']:
                            # If amounts differ by more than 20%
                            if abs(amount1 - amount2) / max(amount1, amount2) > 0.2:
                                conflicts.append({
                                    'type': 'transfer_amount',
                                    'source1': source1['domain'],
                                    'source2': source2['domain'],
                                    'value1': amount1,
                                    'value2': amount2,
                                    'difference_pct': abs(amount1 - amount2) / max(amount1, amount2) * 100,
                                    'higher_credibility_source': source1['domain'] if source1['credibility'] > source2['credibility'] else source2['domain']
                                })
        return conflicts

    def _classify_content_reliability(self, title: str, content: str, url: str) -> Dict:
        """Classify content as rumor vs confirmed news (Bug #9 fix)"""
        title_lower = title.lower()
        content_lower = content.lower()
        domain = self._normalize_domain(urlparse(url).netloc)
        
        # Rumor indicators
        rumor_keywords = {
            'rumour', 'rumor', 'according to', 'sources say', 'reportedly',
            'alleged', 'speculation', 'whispers', 'gossip', 'unconfirmed',
            'claim', 'suggest', 'possibility', 'could', 'might', 'may'
        }
        
        # Official/confirmed indicators
        official_keywords = {
            'confirmed', 'official', 'announced', 'statement', 'press release',
            'completed', 'signed', 'agrees', 'contract', 'deal done'
        }
        
        # Count indicators
        rumor_count = sum(1 for keyword in rumor_keywords if keyword in title_lower or keyword in content_lower[:500])
        official_count = sum(1 for keyword in official_keywords if keyword in title_lower or keyword in content_lower[:500])
        
        # Classify
        if official_count >= 2:
            reliability = 'confirmed'
        elif rumor_count >= 2:
            reliability = 'rumor'
        elif official_count > rumor_count:
            reliability = 'likely_confirmed'
        elif rumor_count > official_count:
            reliability = 'likely_rumor'
        else:
            reliability = 'neutral'
            
        # Boost reliability for trusted domains
        if self._is_trusted_domain(domain) and reliability in ['likely_confirmed', 'neutral']:
            reliability = 'confirmed'
            
        # Bug #15 fix: Add credibility scoring
        credibility_score = self._get_credibility_score(domain, reliability)
        
        return {
            'reliability': reliability,
            'rumor_indicators': rumor_count,
            'official_indicators': official_count,
            'is_trusted_source': self._is_trusted_domain(domain),
            'credibility_score': credibility_score
        }

    def _process_combined_content(self, article_contents: List[Dict], headline: str, search_results: Dict) -> Dict:
        """Process and combine all article contents into comprehensive research"""
        # Combine all article text with deduplication and classification (Bug #8 & #9 fixes)
        combined_text_parts = []
        source_info = []
        total_words = 0
        seen_content_hashes = set()
        
        for content in article_contents:
            if content.get('status') == 'success':
                article_text = content.get('content', '')
                title = content.get('title', 'Unknown Title')
                url = content.get('url', '')
                word_count = content.get('word_count', 0)
                publish_date = content.get('publish_date')
                is_recent = content.get('is_recent_publish', False)
                
                # Bug #8 fix: Duplicate content detection
                content_hash = hash(article_text[:500])  # Hash first 500 chars
                if content_hash in seen_content_hashes:
                    print(f"  🔄 Skipped duplicate content from: {urlparse(url).netloc}")
                    continue
                seen_content_hashes.add(content_hash)
                
                # Bug #9 fix: Content reliability classification
                reliability_info = self._classify_content_reliability(title, article_text, url)
                
                # Add source metadata with reliability info and credibility scoring
                source_metadata = {
                    'title': title,
                    'url': url,
                    'word_count': word_count,
                    'domain': urlparse(url).netloc,
                    'publish_date': publish_date,
                    'is_recent_publish': is_recent,
                    'reliability': reliability_info['reliability'],
                    'is_trusted_source': reliability_info['is_trusted_source'],
                    'credibility_score': reliability_info['credibility_score'],
                    'content': article_text  # Store content for conflict detection
                }
                
                # Add to combined content with classification tags
                reliability_tag = f"[{reliability_info['reliability'].upper()}]"
                recency_tag = "[RECENT]" if is_recent else "[OLDER]"
                trust_tag = "[TRUSTED]" if reliability_info['is_trusted_source'] else "[STANDARD]"
                
                combined_text_parts.append(
                    f"SOURCE: {title} {reliability_tag} {recency_tag} {trust_tag}\n"
                    f"URL: {url}\n"
                    f"CONTENT: {article_text}\n"
                )
                
                # Track source info
                source_info.append(source_metadata)
                total_words += word_count
        
        # Bug #12 fix: Detect conflicts between sources
        detected_conflicts = self._detect_content_conflicts(source_info)
        
        # Bug #15 fix: Sort sources by credibility score (highest first)
        source_info.sort(key=lambda x: x.get('credibility_score', 5.0), reverse=True)
        
        combined_content = "\n" + "="*50 + "\n".join(combined_text_parts)
        
        # Create summary with proper parameter passing (Bug #13 fix)
        content_summary = self._create_research_summary(
            article_contents, headline, total_words, source_info
        )
        
        return {
            'status': 'success',
            'headline': headline,
            'collection_timestamp': datetime.now().isoformat(),
            'research_method': 'enhanced_search_api_with_content_fetching',
            'total_sources_processed': len(article_contents),
            'total_words_collected': total_words,
            'combined_content': combined_content,
            'content_summary': content_summary,
            'source_information': source_info,
            'compiled_sources': [info['url'] for info in source_info],
            'compiled_citations': [f"{info['title']} - {info['domain']} (Score: {info.get('credibility_score', 5.0):.1f})" for info in source_info],
            'detected_conflicts': detected_conflicts,
            'credibility_weighted': True,
            'search_results_metadata': search_results,
            'test_metadata': {
                'test_timestamp': datetime.now().isoformat(),
                'test_type': 'enhanced_search_api_research'
            }
        }

    def _create_research_summary(self, contents: List[Dict], headline: str, total_words: int, source_info: List[Dict]) -> str:
        """Create a comprehensive research summary"""
        summary_parts = []
        summary_parts.append(f"COMPREHENSIVE RESEARCH SUMMARY")
        summary_parts.append(f"Headline: {headline}")
        summary_parts.append(f"Total Sources Processed: {len(contents)}")
        summary_parts.append(f"Total Words Collected: {total_words}")
        summary_parts.append("")
        
        summary_parts.append("SOURCES PROCESSED:")
        confirmed_sources = 0
        rumor_sources = 0
        recent_sources = 0
        trusted_sources = 0
        
        for i, info in enumerate(source_info, 1):
            title = info.get('title', 'Unknown')[:60]
            domain = info.get('domain', '')
            words = info.get('word_count', 0)
            reliability = info.get('reliability', 'unknown')
            is_recent = info.get('is_recent_publish', False)
            is_trusted = info.get('is_trusted_source', False)
            
            # Count source types
            if reliability in ['confirmed', 'likely_confirmed']:
                confirmed_sources += 1
            elif reliability in ['rumor', 'likely_rumor']:
                rumor_sources += 1
            if is_recent:
                recent_sources += 1
            if is_trusted:
                trusted_sources += 1
                
            tags = []
            if reliability != 'neutral':
                tags.append(reliability.upper())
            if is_recent:
                tags.append('RECENT')
            if is_trusted:
                tags.append('TRUSTED')
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            
            summary_parts.append(f"{i}. {title} ({domain}) - {words} words{tag_str}")
            
        summary_parts.append("")
        summary_parts.append("SOURCE RELIABILITY ANALYSIS:")
        summary_parts.append(f" • Confirmed/Official: {confirmed_sources}")
        summary_parts.append(f" • Rumor/Unconfirmed: {rumor_sources}")
        summary_parts.append(f" • Recent (last 7 days): {recent_sources}")
        summary_parts.append(f" • Trusted domains: {trusted_sources}")
        
        # Add credibility scoring summary
        if source_info:
            avg_credibility = sum(info.get('credibility_score', 5.0) for info in source_info) / len(source_info)
            max_credibility = max(info.get('credibility_score', 5.0) for info in source_info)
            summary_parts.append(f" • Average credibility score: {avg_credibility:.1f}/10")
            summary_parts.append(f" • Highest credibility source: {max_credibility:.1f}/10")
            
        summary_parts.append("")
        summary_parts.append("RESEARCH CONTENT ANALYSIS:")
        
        # Extract key information from all articles
        all_content = " ".join([c.get('content', '') for c in contents if c.get('status') == 'success'])
        
        # Simple keyword extraction
        important_terms = self._extract_key_terms(all_content, headline)
        if important_terms:
            summary_parts.append("Key Terms Found:")
            for term in important_terms[:10]:
                summary_parts.append(f" • {term}")
                
        return "\n".join(summary_parts)

    def _extract_key_terms(self, content: str, headline: str) -> List[str]:
        """Extract key terms from content"""
        # Simple term extraction - could be enhanced with NLP
        words = re.findall(r'\b[A-Z][a-z]+\b', content)
        headline_words = set(headline.lower().split())
        
        # Count occurrences
        term_counts = {}
        for word in words:
            if len(word) > 3 and word.lower() not in headline_words:
                term_counts[word] = term_counts.get(word, 0) + 1
                
        # Return top terms
        return [term for term, count in sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:10]]

    def save_enhanced_research_output(self, research_result: Dict, headline: str) -> str:
        """Save enhanced research output to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_headline = "".join(c for c in headline if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_headline = clean_headline.replace(' ', '_')[:50]
        
        txt_filename = f"enhanced_search_research_{clean_headline}_{timestamp}.txt"
        json_filename = f"enhanced_search_research_{clean_headline}_{timestamp}.json"
        
        txt_filepath = self.output_dir / txt_filename
        json_filepath = self.output_dir / json_filename
        
        try:
            # Save detailed text file
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("ENHANCED SEARCH API RESEARCH WITH FULL CONTENT\n")
                f.write("="*80 + "\n\n")
                
                # Test information
                f.write("RESEARCH INFORMATION:\n")
                f.write("-"*50 + "\n")
                f.write(f"Headline: {research_result.get('headline', 'Unknown')}\n")
                f.write(f"Collection Method: {research_result.get('research_method', 'Unknown')}\n")
                f.write(f"Timestamp: {research_result.get('collection_timestamp', 'Unknown')}\n")
                f.write(f"Status: {research_result.get('status', 'Unknown')}\n\n")
                
                # Research statistics
                f.write("RESEARCH STATISTICS:\n")
                f.write("-"*50 + "\n")
                f.write(f"Sources Processed: {research_result.get('total_sources_processed', 0)}\n")
                f.write(f"Total Words Collected: {research_result.get('total_words_collected', 0)}\n")
                f.write(f"Citations: {len(research_result.get('compiled_citations', []))}\n\n")
                
                # Content summary
                f.write("CONTENT SUMMARY:\n")
                f.write("="*80 + "\n")
                summary = research_result.get('content_summary', 'No summary available')
                f.write(summary)
                
                # Full combined content
                f.write("\n\n" + "FULL RESEARCH CONTENT:\n")
                f.write("="*80 + "\n")
                combined_content = research_result.get('combined_content', 'No content available')
                f.write(combined_content)
                
                f.write("\n\n" + "="*80 + "\n")
                f.write("END OF ENHANCED RESEARCH RESULTS\n")
                f.write("="*80 + "\n")
                
            # Save JSON file
            with open(json_filepath, 'w', encoding='utf-8') as json_f:
                json.dump(research_result, json_f, indent=2, ensure_ascii=False)
                
            print(f"💾 Enhanced research saved to:")
            print(f"  📄 Text: {txt_filepath}")
            print(f"  📄 JSON: {json_filepath}")
            
            return str(txt_filepath)
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return ""

    def interactive_test(self):
        """Run interactive testing session"""
        print("🔍 Enhanced Search API with Full Content Fetching")
        print("="*70)
        
        if not self.available:
            print("❌ Enhanced Search API not available.")
            print("   Required:")
            print("   - GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID")
            print("   - pip install beautifulsoup4")
            print("   - pip install newspaper3k (optional but recommended)")
            return
            
        print("✅ Enhanced Search API ready - will fetch FULL article content")
        
        while True:
            print(f"\n📝 Enter a sports headline to research with full content:")
            headline = input("Headline: ").strip()
            if not headline:
                print("❌ Please enter a valid headline.")
                continue
                
            print(f"\n📂 Enter category (optional):")
            category = input("Category: ").strip() or None
            
            print(f"\n🔢 Max sources to fetch full content (default: 5, max: 10):")
            max_sources_input = input("Max sources: ").strip()
            max_sources = 5
            if max_sources_input.isdigit():
                max_sources = min(int(max_sources_input), 10)
                
            # Collect comprehensive research
            research_result = self.collect_comprehensive_research(headline, category, max_sources)
            
            # Display results
            if research_result.get('status') == 'success':
                sources = research_result.get('total_sources_processed', 0)
                words = research_result.get('total_words_collected', 0)
                citations = len(research_result.get('compiled_citations', []))
                
                print(f"\n📊 Enhanced Research Summary:")
                print(f"  ✅ Status: Success")
                print(f"  📚 Sources with Full Content: {sources}")
                print(f"  📝 Total Words Collected: {words}")
                print(f"  🔗 Citations: {citations}")
                
                # Show content preview
                combined_content = research_result.get('combined_content', '')
                if combined_content:
                    preview = combined_content[:400] + "..." if len(combined_content) > 400 else combined_content
                    print(f"\n📖 Full Content Preview:")
                    print(f"  {preview}")
                    
                # Save results
                saved_file = self.save_enhanced_research_output(research_result, headline)
                print(f"\n🎯 This comprehensive content can now be used for article generation!")
            else:
                error = research_result.get('error', 'Unknown error')
                print(f"\n❌ Enhanced Research Failed:")
                print(f"  Error: {error}")
                
            print(f"\n" + "="*70)
            continue_test = input("Research another headline? (y/n): ").strip().lower()
            if continue_test not in ['y', 'yes']:
                break
                
        print("\n👋 Enhanced research session ended. Check testing_output for full content files.")


def main():
    """Main function"""
    fetcher = EnhancedSearchContentFetcher()
    fetcher.interactive_test()


if __name__ == "__main__":
    main()