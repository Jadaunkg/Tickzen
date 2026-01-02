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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin
import re

# Web scraping imports
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    print("⚠️  BeautifulSoup not found. Install with: pip install beautifulsoup4")
    BEAUTIFULSOUP_AVAILABLE = False

try:
    import newspaper
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    print("⚠️  Newspaper3k not found. Install with: pip install newspaper3k")
    NEWSPAPER_AVAILABLE = False

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
        
        # Enhanced search config for better results (keep last 10 days)
        self.search_config = {
            'num': 10,  # Number of results per request
            'dateRestrict': 'd10',  # Last 10 days as requested
            'sort': 'date:r:20231201:20251231',  # Sort by date (recent first)
            'safe': 'medium',
            'cx': self.search_engine_id,
            'key': self.api_key
        }
        
        # Trusted domains for sports news
        self.trusted_domains = [
            'espn.com', 'bbc.com', 'cnn.com/sport', 'reuters.com', 'apnews.com',
            'skysports.com', 'theguardian.com', 'bleacherreport.com',
            'goal.com', 'sportsnet.ca', 'foxsports.com', 'cbssports.com',
            'athletic.com', 'si.com', 'nfl.com', 'nba.com', 'premierleague.com'
        ]
        
        # Content extraction settings
        self.request_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        self.available = bool(self.api_key and self.search_engine_id and BEAUTIFULSOUP_AVAILABLE)
        
        if not self.available:
            if not (self.api_key and self.search_engine_id):
                print("❌ Search API not configured. Set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID")
            if not BEAUTIFULSOUP_AVAILABLE:
                print("❌ BeautifulSoup not available. Install with: pip install beautifulsoup4")
    
    def collect_comprehensive_research(self, headline: str, category: str = None, 
                                     max_sources: int = 5) -> Dict:
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
        print(f"   📰 Headline: {headline}")
        if category:
            print(f"   🏷️  Category: {category}")
        print(f"   📚 Max Sources: {max_sources}")
        print("="*70)
        
        try:
            # Step 1: Get search results
            print("🔍 Step 1: Getting search results...")
            search_results = self._get_search_results(headline, category)
            
            if search_results.get('status') != 'success':
                return search_results
            
            urls = search_results.get('urls', [])[:max_sources]
            print(f"   Found {len(urls)} URLs to process")
            
            # Step 2: Fetch full content from each URL
            print(f"📄 Step 2: Fetching full content from {len(urls)} sources...")
            article_contents = []
            successful_fetches = 0
            javascript_failures = 0
            other_failures = 0
            
            for i, url in enumerate(urls, 1):
                print(f"   Processing {i}/{len(urls)}: {urlparse(url).netloc}")
                
                content = self._fetch_article_content(url)
                if content.get('status') == 'success':
                    article_contents.append(content)
                    successful_fetches += 1
                    time.sleep(1)  # Respectful delay
                elif 'JavaScript' in content.get('error', ''):
                    javascript_failures += 1
                    print(f"   🚫 Skipped {urlparse(url).netloc}: Requires JavaScript")
                else:
                    other_failures += 1
                    error_msg = content.get('error', 'Unknown error')
                    print(f"   ⚠️  Failed to fetch from {urlparse(url).netloc}: {error_msg[:50]}")
            
            print(f"   ✅ Successfully fetched {successful_fetches}/{len(urls)} articles")
            if javascript_failures > 0:
                print(f"   🚫 Skipped {javascript_failures} JavaScript-required sites (X.com, Facebook, etc.)")
            if other_failures > 0:
                print(f"   ❌ Failed to fetch {other_failures} due to other issues")
            
            # Step 3: Process and combine content
            print("🔄 Step 3: Processing and combining content...")
            comprehensive_research = self._process_combined_content(
                article_contents, headline, search_results
            )
            
            print(f"✅ Enhanced research complete!")
            print(f"   📚 Articles processed: {len(article_contents)}")
            print(f"   📝 Total content: {len(comprehensive_research.get('combined_content', ''))} characters")
            
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
            
            print(f"   🎯 Using single comprehensive query for maximum coverage")
            print(f"   🔍 Query: {comprehensive_query[:100]}...")
            
            # Configure for maximum results in single request
            params = self.search_config.copy()
            params['q'] = comprehensive_query
            params['num'] = 10  # Maximum results per request
            
            # Make single API request
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                print(f"   📊 Found {len(items)} results from single comprehensive search")
                
                if len(items) > 0:
                    all_results = []
                    all_urls = []
                    unique_urls = set()
                    
                    # Process all results
                    for item in items:
                        url = item.get('link', '')
                        domain = item.get('displayLink', '')
                        title = item.get('title', '')
                        
                        if url and url not in unique_urls and self._is_valid_article_url(url):
                            unique_urls.add(url)
                            all_results.append({
                                'title': title,
                                'url': url,
                                'domain': domain,
                                'snippet': item.get('snippet', ''),
                                'is_trusted': any(trusted in domain for trusted in self.trusted_domains),
                                'found_by_query': 'comprehensive_single_query',
                                'query_used': comprehensive_query
                            })
                            all_urls.append(url)
                            print(f"   ✅ Added: {title[:40]}... ({domain})")
                    
                    print(f"   📋 SUCCESS! Found {len(all_urls)} unique URLs from single comprehensive query")
                    
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
                    print("   ⚠️  No results from comprehensive query, trying fallback")
                    return self._fallback_broader_search(headline, category)
            else:
                print(f"   ❌ Search failed with status {response.status_code}")
                return self._fallback_broader_search(headline, category)
                
        except Exception as e:
            print(f"   ❌ Exception in search: {str(e)}")
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
            
            # 7. Add date restriction for recent content
            query_parts.append('after:2024-12-14')  # Last 10 days
            
            # Combine all parts with AND logic
            comprehensive_query = ' '.join(query_parts)
            
            # Ensure we don't exceed query length limits
            if len(comprehensive_query) > 200:
                # Fallback to simpler but still comprehensive query
                simple_parts = [
                    f'"{core_subject}"',
                    f"({' OR '.join(key_entities['persons'][:2])})" if key_entities['persons'] else '',
                    f"({' OR '.join(key_entities['teams'][:1])})" if key_entities['teams'] else '',
                    '(transfer OR news OR latest)' if key_entities['transfer_related'] else '(news OR latest)',
                    'after:2024-12-14'
                ]
                comprehensive_query = ' '.join([part for part in simple_parts if part])
            
            return comprehensive_query
                    
        except Exception as e:
            print(f"   ❌ Exception in comprehensive search: {str(e)}")
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
            for person in key_entities['persons'][:2]:  # Top 2 persons
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
            for team in key_entities['teams'][:2]:  # Top 2 teams
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
            key_terms = ' '.join(words[:4])  # First 4 words
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
        
        return unique_queries[:8]  # Limit to 8 diverse queries
    
    def _extract_key_entities(self, headline: str) -> Dict:
        """Extract key entities and context from headline for related queries"""
        words = headline.split()
        lower_headline = headline.lower()
        
        # Common sports names (simplified detection)
        person_indicators = ['chelsea', 'manchester', 'liverpool', 'arsenal', 'tottenham', 
                            'city', 'united', 'fc', 'athletic', 'real', 'barcelona']
        
        # Team/Club detection
        teams = []
        team_patterns = ['Chelsea', 'Manchester City', 'Manchester United', 'Liverpool', 
                        'Arsenal', 'Tottenham', 'Leicester', 'Newcastle', 'Brighton',
                        'Bournemouth', 'Real Madrid', 'Barcelona', 'Bayern Munich']
        
        for team in team_patterns:
            if team.lower() in lower_headline:
                teams.append(team)
        
        # Person detection (look for capitalized names)
        persons = []
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 3 and word not in team_patterns:
                # Check if it's likely a person name (next to other caps or in certain positions)
                if i < len(words) - 1 and words[i + 1][0].isupper():
                    persons.append(f"{word} {words[i + 1]}")
                elif not any(indicator in word.lower() for indicator in person_indicators):
                    persons.append(word)
        
        # Amount detection (£, $, million, etc.)
        amounts = []
        for word in words:
            if '£' in word or '$' in word or 'million' in word.lower() or 'm' in word:
                amounts.append(word)
        
        # Transfer related detection
        transfer_keywords = ['transfer', 'sign', 'hunt', 'target', 'bid', 'offer', 'deal', 
                           'move', 'interest', 'pursue', 'acquire', 'buy', 'sell']
        transfer_related = any(keyword in lower_headline for keyword in transfer_keywords)
        
        # News angles
        news_angles = []
        angle_patterns = ['breaking', 'exclusive', 'latest', 'update', 'confirmed', 
                         'rumour', 'report', 'analysis', 'opinion', 'reaction']
        for pattern in angle_patterns:
            if pattern in lower_headline:
                news_angles.append(pattern)
        
        # Context detection
        context = []
        context_patterns = ['Premier League', 'Champions League', 'World Cup', 'Euro', 
                           'transfer window', 'January window', 'summer window']
        for pattern in context_patterns:
            if pattern.lower() in lower_headline:
                context.append(pattern)
        
        return {
            'persons': persons[:3],  # Top 3 persons
            'teams': teams[:3],      # Top 3 teams
            'amounts': amounts[:2],   # Top 2 amounts
            'transfer_related': transfer_related,
            'news_angles': news_angles[:3],
            'context': context[:2]
        }
    
    def _fallback_broader_search(self, headline: str, category: str = None) -> Dict:
        """Fallback to broader search if 10-day restriction yields no results"""
        try:
            print("   🔄 Attempting broader fallback search...")
            
            # Use most basic query without date restriction
            words = headline.split()
            basic_query = ' '.join(words[:5])  # First 5 words
            if category:
                basic_query += f" {category}"
                
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': basic_query,
                'num': 10,
                'safe': 'medium'
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
                                'is_trusted': any(trusted in domain for trusted in self.trusted_domains),
                                'found_by_query': 'fallback_broader',
                                'query_used': basic_query
                            })
                            urls.append(url)
                    
                    if len(urls) > 0:
                        print(f"   ✅ Fallback successful! Found {len(urls)} URLs")
                        return {
                            'status': 'success',
                            'results': results,
                            'urls': urls,
                            'total_found': len(items),
                            'fallback_used': True,
                            'query_used': basic_query
                        }
            
            print("   ❌ Fallback search also failed")
            return {
                'status': 'error',
                'error': "No results found even with broader search"
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Fallback search failed: {str(e)}"
            }
    
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
    
    def _fetch_article_content(self, url: str) -> Dict:
        """Fetch full article content from URL"""
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
            
            # Method 1: Try newspaper3k first (best for news articles)
            if NEWSPAPER_AVAILABLE:
                try:
                    article = Article(url)
                    article.download()
                    article.parse()
                    
                    if article.text and len(article.text) > 200:
                        return {
                            'status': 'success',
                            'url': url,
                            'title': article.title or 'No title',
                            'content': article.text,
                            'publish_date': str(article.publish_date) if article.publish_date else None,
                            'authors': article.authors,
                            'method': 'newspaper3k',
                            'word_count': len(article.text.split())
                        }
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
                    pass  # Fall back to BeautifulSoup
            
            # Method 2: BeautifulSoup fallback
            response = requests.get(url, headers=self.request_headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
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
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # Try to find article content using common selectors
            article_content = None
            content_selectors = [
                'article', '.article-content', '.story-content', 
                '.post-content', '.entry-content', '.content',
                '[data-module="ArticleBody"]', '.article-body'
            ]
            
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    article_content = element.get_text(separator=' ', strip=True)
                    if len(article_content) > 200:
                        break
            
            # Fallback: get all paragraph text
            if not article_content or len(article_content) < 200:
                paragraphs = soup.find_all('p')
                article_content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            
            if article_content and len(article_content) > 100:
                # Clean up the content
                article_content = re.sub(r'\s+', ' ', article_content)
                article_content = article_content.strip()
                
                return {
                    'status': 'success',
                    'url': url,
                    'title': soup.title.string if soup.title else 'No title',
                    'content': article_content,
                    'method': 'beautifulsoup',
                    'word_count': len(article_content.split())
                }
            else:
                return {
                    'status': 'error',
                    'error': 'Insufficient content found'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _process_combined_content(self, article_contents: List[Dict], 
                                 headline: str, search_results: Dict) -> Dict:
        """Process and combine all article contents into comprehensive research"""
        
        # Combine all article text
        combined_text_parts = []
        source_info = []
        total_words = 0
        
        for content in article_contents:
            if content.get('status') == 'success':
                article_text = content.get('content', '')
                title = content.get('title', 'Unknown Title')
                url = content.get('url', '')
                word_count = content.get('word_count', 0)
                
                # Add to combined content
                combined_text_parts.append(f"SOURCE: {title}\nURL: {url}\nCONTENT: {article_text}\n")
                
                # Track source info
                source_info.append({
                    'title': title,
                    'url': url,
                    'word_count': word_count,
                    'domain': urlparse(url).netloc
                })
                
                total_words += word_count
        
        combined_content = "\n" + "="*50 + "\n".join(combined_text_parts)
        
        # Create summary
        content_summary = self._create_research_summary(
            article_contents, headline, total_words
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
            'compiled_citations': [f"{info['title']} - {info['domain']}" for info in source_info],
            'search_results_metadata': search_results,
            'test_metadata': {
                'test_timestamp': datetime.now().isoformat(),
                'test_type': 'enhanced_search_api_research'
            }
        }
    
    def _create_research_summary(self, contents: List[Dict], headline: str, total_words: int) -> str:
        """Create a comprehensive research summary"""
        summary_parts = []
        
        summary_parts.append(f"COMPREHENSIVE RESEARCH SUMMARY")
        summary_parts.append(f"Headline: {headline}")
        summary_parts.append(f"Total Sources Processed: {len(contents)}")
        summary_parts.append(f"Total Words Collected: {total_words}")
        summary_parts.append("")
        
        summary_parts.append("SOURCES PROCESSED:")
        for i, content in enumerate(contents, 1):
            if content.get('status') == 'success':
                title = content.get('title', 'Unknown')[:60]
                domain = urlparse(content.get('url', '')).netloc
                words = content.get('word_count', 0)
                summary_parts.append(f"{i}. {title} ({domain}) - {words} words")
        
        summary_parts.append("")
        summary_parts.append("RESEARCH CONTENT ANALYSIS:")
        
        # Extract key information from all articles
        all_content = " ".join([c.get('content', '') for c in contents if c.get('status') == 'success'])
        
        # Simple keyword extraction
        important_terms = self._extract_key_terms(all_content, headline)
        if important_terms:
            summary_parts.append("Key Terms Found:")
            for term in important_terms[:10]:
                summary_parts.append(f"  • {term}")
        
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
            print(f"   📄 Text: {txt_filepath}")
            print(f"   📄 JSON: {json_filepath}")
            
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
                print(f"   ✅ Status: Success")
                print(f"   📚 Sources with Full Content: {sources}")
                print(f"   📝 Total Words Collected: {words}")
                print(f"   🔗 Citations: {citations}")
                
                # Show content preview
                combined_content = research_result.get('combined_content', '')
                if combined_content:
                    preview = combined_content[:400] + "..." if len(combined_content) > 400 else combined_content
                    print(f"\n📖 Full Content Preview:")
                    print(f"   {preview}")
                
                # Save results
                saved_file = self.save_enhanced_research_output(research_result, headline)
                
                print(f"\n🎯 This comprehensive content can now be used for article generation!")
                
            else:
                error = research_result.get('error', 'Unknown error')
                print(f"\n❌ Enhanced Research Failed:")
                print(f"   Error: {error}")
            
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