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

        # Enhanced search config for better results (relies on dateRestrict only)
        self.search_config = {
            'num': 10,  # Number of results per request
            'dateRestrict': 'd7',  # Last 7 days only - ONLY reliable date filter for Custom Search
            'safe': 'medium',
            'cx': self.search_engine_id,
            'key': self.api_key
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

            # Step 3: Process and combine content
            print("🔄 Step 3: Processing and combining content...")
            comprehensive_research = self._process_combined_content(
                article_contents, headline, search_results
            )

            print(f"✅ Enhanced research complete!")
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
        """Get comprehensive search results with a single powerful API request"""
        try:
            # Build one comprehensive query combining multiple search strategies
            comprehensive_query = self._build_comprehensive_query(headline, category)
            print(f"  🎯 Using single comprehensive query for maximum coverage")
            print(f"  🔍 Query: {comprehensive_query[:100]}...")

            # Configure for maximum results in single request
            params = self.search_config.copy()
            params['q'] = comprehensive_query
            params['num'] = 10  # Maximum results per request

            # Bug #10 fix: Add rate limiting and retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(self.base_url, params=params, timeout=30)
                    # Handle rate limiting (HTTP 429)
                    if response.status_code == 429:
                        wait_time = 2 ** attempt  # Exponential backoff
                        print(f"  ⏳ Rate limited. Waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    response.raise_for_status()
                    break  # Success
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise e
                    wait_time = 2 ** attempt
                    print(f"  🔄 Request failed. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                print(f"  📊 Found {len(items)} results from single comprehensive search")

                if len(items) > 0:
                    all_results = []
                    all_urls = []
                    unique_urls = set()
                    trusted_count = 0
                    rumor_count = 0

                    # Process all results
                    for item in items:
                        url = item.get('link', '')
                        domain = item.get('displayLink', '')
                        title = item.get('title', '')

                        if url and url not in unique_urls and self._is_valid_article_url(url):
                            unique_urls.add(url)
                            is_trusted = self._is_trusted_domain(domain)
                            # Quick rumor detection from snippet
                            snippet = item.get('snippet', '').lower()
                            is_likely_rumor = any(word in snippet for word in ['rumour', 'rumor', 'sources say', 'reportedly', 'claim'])

                            if is_trusted:
                                trusted_count += 1
                            if is_likely_rumor:
                                rumor_count += 1

                            all_results.append({
                                'title': title,
                                'url': url,
                                'domain': domain,
                                'snippet': item.get('snippet', ''),
                                'is_trusted': is_trusted,
                                'is_likely_rumor': is_likely_rumor,
                                'found_by_query': 'comprehensive_single_query',
                                'query_used': comprehensive_query
                            })
                            all_urls.append(url)
                            print(f"  ✅ Added: {title[:40]}... ({domain})")

                    # Bug #11 partial fix: Check if we need second page
                    need_second_page = (trusted_count < 2 or (rumor_count > trusted_count and trusted_count < 3))

                    if need_second_page and len(all_results) >= 8:
                        print(f"  🔄 Fetching second page (low trusted source count: {trusted_count})")
                        second_page_results = self._fetch_second_page(comprehensive_query)
                        if second_page_results:
                            for result in second_page_results:
                                if result['url'] not in unique_urls:
                                    all_results.append(result)
                                    all_urls.append(result['url'])
                                    print(f"  ✅ Page 2: {result['title'][:40]}... ({result['domain']})")

                    print(f"  📋 SUCCESS! Found {len(all_urls)} unique URLs (trusted: {trusted_count}, total results: {len(all_results)})")
                    return {
                        'status': 'success',
                        'results': all_results,
                        'urls': all_urls,
                        'total_found': len(all_results),
                        'queries_tried': 1,  # Only one query now
                        'successful_queries': 1,
                        'query_types_used': ['comprehensive_single_query'],
                        'comprehensive_search': True
                    }
                else:
                    print("  ⚠️ No results from comprehensive query, trying fallback")
                    return self._fallback_broader_search(headline, category)
            else:
                print(f"  ❌ Search failed with status {response.status_code}")
                return self._fallback_broader_search(headline, category)

        except Exception as e:
            print(f"  ❌ Exception in search: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _build_comprehensive_query(self, headline: str, category: str = None) -> str:
        """Build a single powerful query that captures diverse sources"""
        try:
            # Extract key entities for better targeting
            key_entities = self._extract_key_entities(headline)
            words = headline.split()
            
            # Start with main headline terms
            query_parts = []
            
            # 1. Core subject (first 3-4 words)
            core_subject = ' '.join(words[:4])
            query_parts.append(f'"{core_subject}"')
            
            # 2. Add key persons with OR operator
            if key_entities['persons']:
                persons_query = ' OR '.join([f'"{person}"' for person in key_entities['persons'][:3]])
                query_parts.append(f"({persons_query})")
                
            # 3. Add key teams/clubs with OR operator
            if key_entities['teams']:
                teams_query = ' OR '.join([f'"{team}"' for team in key_entities['teams'][:2]])
                query_parts.append(f"({teams_query})")
                
            # 4. Add transfer/market terms if relevant
            if key_entities['transfer_related']:
                transfer_terms = ['transfer', 'signing', 'move', 'deal', 'market']
                query_parts.append(f"({' OR '.join(transfer_terms)})")
                
            # 5. Add amounts/numbers if present
            if key_entities['amounts']:
                amounts_query = ' OR '.join([f'"{amount}"' for amount in key_entities['amounts'][:2]])
                query_parts.append(f"({amounts_query})")
                
            # 6. Add news context terms
            news_terms = ['news', 'latest', 'report', 'update']
            if category:
                news_terms.append(category)
            query_parts.append(f"({' OR '.join(news_terms)})")
            
            # NOTE: Removed 'after:' date operator - Google Custom Search API doesn't support it
            # Relying on dateRestrict=d7 parameter instead for last 7 days filtering
            
            # Combine all parts with AND logic
            comprehensive_query = ' '.join(query_parts)
            
            # Ensure we don't exceed query length limits
            if len(comprehensive_query) > 200:
                # Fallback to simpler but still comprehensive query
                simple_parts = [
                    f'"{core_subject}"',
                    f"({' OR '.join(key_entities['persons'][:2])})" if key_entities['persons'] else '',
                    f"({' OR '.join(key_entities['teams'][:1])})" if key_entities['teams'] else '',
                    '(transfer OR news OR latest)' if key_entities['transfer_related'] else '(news OR latest)'
                    # NOTE: Removed date filter - handled by API parameter dateRestrict=d7
                ]
                comprehensive_query = ' '.join([part for part in simple_parts if part])
                
            return comprehensive_query
            
        except Exception as e:
            print(f"  ❌ Exception in comprehensive search: {str(e)}")
            return ""

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

        # Enhanced person detection (handles 2-3 word names, common patterns)
        persons = []
        # Pattern 1: Two consecutive capitalized words not in teams/competitions
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
                            len(words[i+2]) > 2 and words[i+2].lower() not in ['fc', 'united', 'city']):
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
        """Extract publish date from HTML meta tags (Bug #3 fix)"""
        try:
            # Try various meta tag patterns
            date_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="publishdate"]',
                'meta[name="publication-date"]',
                'meta[name="date"]',
                'time[datetime]',
                '.publish-date', '.publication-date'
            ]
            
            for selector in date_selectors:
                element = soup.select_one(selector)
                if element:
                    # Try different attribute names
                    for attr in ['content', 'datetime', 'data-date']:
                        if element.get(attr):
                            return element[attr]
                    # Try text content for time elements
                    if element.get_text(strip=True):
                        return element.get_text(strip=True)
            return None
        except Exception:
            return None

    def _validate_publish_date(self, publish_date, url: str) -> bool:
        """Validate if article publish date is recent (Bug #3 fix)"""
        if not publish_date:
            return False  # Treat missing dates as potentially old
            
        try:
            from dateutil import parser as date_parser
            parsed_date = date_parser.parse(str(publish_date))
            # Check if within last 7 days (matching our search criteria)
            seven_days_ago = datetime.now() - timedelta(days=7)
            is_recent = parsed_date.replace(tzinfo=None) >= seven_days_ago.replace(tzinfo=None)
            
            if not is_recent:
                print(f"  ⚠️ Old article detected ({parsed_date.date()}): {urlparse(url).netloc}")
                
            return is_recent
        except Exception:
            return False

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