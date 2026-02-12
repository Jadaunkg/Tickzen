"""
Perplexity AI Integration for Research Information Collection
Uses Perplexity AI's search capabilities to collect detailed research information 
from latest and trusted internet sources based on article headlines.
This collected research is then passed to Gemini AI for SEO-optimized article generation.

Role: Research Information Collector Only
Output: Structured research data with citations and sources
"""

import requests
import json
import logging
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Import enhanced configuration
try:
    from .enhanced_config import EnhancedConfig
except ImportError:
    try:
        from enhanced_config import EnhancedConfig
    except ImportError:
        # Fallback configuration for single-request approach
        class EnhancedConfig:
            ENABLE_ENHANCED_RESEARCH = True
            MAX_FOLLOWUP_QUERIES = 0  # Single request only
            INCLUDE_SOCIAL_MEDIA_RESEARCH = True
            INCLUDE_FINANCIAL_ANALYSIS = True
            @classmethod
            def get_perplexity_config(cls): 
                return {"max_tokens": 4000, "temperature": 0.2, "search_recency_filter": "week"}
            @classmethod
            def get_enhanced_sources(cls, category=None): 
                return ["ESPN", "BBC Sport", "The Athletic", "Reuters", "Associated Press", "Twitter/X verified", "YouTube official", "Reddit sports", "official team sites", "player social media"]

# Load environment variables from .env file
load_dotenv()

# Import content freshness validation using dynamic imports to avoid import errors
import importlib
FRESHNESS_VALIDATOR_AVAILABLE = False
ContentFreshnessValidator = None
track_article_usage = None

try:
    # Try relative import first
    module = importlib.import_module('.content_freshness_validator', package=__package__)
    ContentFreshnessValidator = getattr(module, 'ContentFreshnessValidator')
    track_article_usage = getattr(module, 'track_article_usage')
    FRESHNESS_VALIDATOR_AVAILABLE = True
except (ImportError, AttributeError):
    try:
        # Try absolute import as fallback
        module = importlib.import_module('content_freshness_validator')
        ContentFreshnessValidator = getattr(module, 'ContentFreshnessValidator')
        track_article_usage = getattr(module, 'track_article_usage')
        FRESHNESS_VALIDATOR_AVAILABLE = True
    except (ImportError, AttributeError):
        # Module not available - use placeholder implementations
        class ContentFreshnessValidator:
            """Placeholder implementation when content freshness validator is not available."""
            def __init__(self):
                pass
            
            def validate_article_collection(self, *args, **kwargs):
                return {"status": "not_available", "message": "Content freshness validation not available"}
            
            def filter_fresh_articles(self, articles):
                return articles, []  # Return all articles as fresh, none as outdated
        
        def track_article_usage(*args, **kwargs):
            """Placeholder function for tracking article usage."""
            pass
        
        print("⚠️ Content Freshness Validator not found for Perplexity client - using placeholder implementation")
        FRESHNESS_VALIDATOR_AVAILABLE = False

# Ensure console can handle UTF-8 output to avoid encoding errors on Windows terminals
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    # If reconfigure is unsupported, continue with default encoding
    pass

# Setup logging (prevent duplicate handlers completely)
root_logger = logging.getLogger()
if not root_logger.handlers:
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler('perplexity_research.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

class PerplexityResearchCollector:
    """
    Collects research information from internet using Perplexity AI
    Role: Pure research data collection from latest and trusted sources
    Output: Structured research with citations for Gemini AI article generation
    
    Sport-Specific Research:
    - Each sport has dedicated domain lists (up to 20 domains per sport)
    - Custom query templates optimized for sport-specific terminology
    - Automatic routing based on category parameter
    """
    
    # FOOTBALL/SOCCER DOMAINS (20 trusted sources)
    FOOTBALL_DOMAINS = [
        # Major Football News & Analysis (8)
        "espn.com", "bbc.com", "skysports.com", "goal.com", 
        "theathletic.com", "theguardian.com", "telegraph.co.uk", "onefootball.com",
        # Transfer & Squad News (4)
        "transfermarkt.com", "90min.com", "fourfourtwo.com", "football365.com",
        # League-Specific (4)
        "premierleague.com", "uefa.com", "laliga.com", "bundesliga.com",
        # Analysis & Stats (4)
        "whoscored.com", "fbref.com", "sportsmole.co.uk", "talksport.com"
    ]
    
    # CRICKET DOMAINS (20 trusted sources)
    CRICKET_DOMAINS = [
        # Major Cricket News (6)
        "espncricinfo.com", "cricbuzz.com", "cricket.com.au", 
        "ecb.co.uk", "bcci.tv", "icc-cricket.com",
        # News & Analysis (6)
        "wisden.com", "cricketaddictor.com", "thecricketer.com",
        "crictracker.com", "cricket-world.com", "sportskeeda.com",
        # Regional Cricket (4)
        "hindustantimes.com", "indianexpress.com", "timesofindia.indiatimes.com",
        "news18.com",
        # International (4)
        "bbc.com", "theguardian.com", "skysports.com", "espn.com"
    ]
    
    # BASKETBALL/NBA DOMAINS (20 trusted sources)
    BASKETBALL_DOMAINS = [
        # Official & Major Networks (6)
        "nba.com", "espn.com", "bbc.com", "cbssports.com",
        "nbcsports.com", "skysports.com",
        # Analysis & News (6)
        "theathletic.com", "bleacherreport.com", "hoopshype.com",
        "clutchpoints.com", "slamonline.com", "basketball-reference.com",
        # Trade & Rumors (4)
        "sportingnews.com", "fansided.com", "yardbarker.com", "realgm.com",
        # International Basketball (4)
        "fiba.basketball", "eurohoops.net", "euroleague.net", "nbl.com.au"
    ]
    
    # GENERAL SPORTS DOMAINS (fallback for other sports)
    GENERAL_SPORTS_DOMAINS = [
        # Major Multi-Sport Networks (8)
        "espn.com", "bbc.com", "skysports.com", "reuters.com", 
        "cbssports.com", "nbcsports.com", "theguardian.com", "telegraph.co.uk",
        # Analysis & News (6)
        "theathletic.com", "bleacherreport.com", "sportingnews.com",
        "si.com", "yahoo.com", "fansided.com",
        # International (6)
        "apnews.com", "marca.com", "lequipe.fr", 
        "gazzetta.it", "sport1.de", "sportsnet.ca"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Perplexity Research Collector
        
        Args:
            api_key (str): Perplexity API key. If None, reads from PERPLEXITY_API_KEY env var
        """
        self.api_key = api_key or os.getenv('PERPLEXITY_API_KEY')
        
        if not self.api_key:
            logging.warning("⚠️  PERPLEXITY_API_KEY not found in environment variables")
            logging.info("ℹ️  To use Perplexity AI:")
            logging.info("   1. Get API key from https://www.perplexity.ai/api")
            logging.info("   2. Set environment variable: set PERPLEXITY_API_KEY=your_key")
            
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar"  # Latest Perplexity model with real-time internet access and up-to-date sources
        self.timeout = 90  # Increased timeout for comprehensive research
        
        # Content freshness validator
        if FRESHNESS_VALIDATOR_AVAILABLE:
            self.freshness_validator = ContentFreshnessValidator()
            logging.info("✅ Perplexity - Content Freshness Validation enabled")
        else:
            self.freshness_validator = None
            logging.warning("⚠️ Perplexity - Content Freshness Validation disabled")
        
    def collect_enhanced_research_for_headline(self, headline: str, 
                                              source: Optional[str] = None,
                                              category: Optional[str] = None) -> Dict:
        """
        ENHANCED SINGLE-REQUEST METHOD: Collect maximum information in one comprehensive query
        Designed to respect Perplexity API rate limits (2 requests/minute)
        Packs all research angles into one ultra-comprehensive request
        
        SPORT-SPECIFIC ROUTING: Automatically routes to sport-specific methods
        based on category parameter for optimized domain filtering.
        """
        # Route to sport-specific method if category is recognized
        if category:
            category_lower = category.lower()
            if 'football' in category_lower or 'soccer' in category_lower:
                return self.collect_football_research_for_headline(headline, source, category)
            elif 'cricket' in category_lower:
                return self.collect_cricket_research_for_headline(headline, source, category)
            elif 'basketball' in category_lower or 'nba' in category_lower:
                return self.collect_basketball_research_for_headline(headline, source, category)
        try:
            if not self.api_key:
                logging.error("❌ Perplexity API key not configured")
                return self._get_placeholder_research(headline, "API key not configured")
            
            logging.info(f"\n{'='*80}")
            logging.info(f"🚀 ENHANCED SINGLE-REQUEST RESEARCH (RATE LIMIT OPTIMIZED)")
            logging.info(f"{'='*80}")
            logging.info(f"📰 Headline: {headline}")
            logging.info(f"📍 Source: {source or 'Unknown'}")
            logging.info(f"🏷️  Category: {category or 'General'}")
            
            # Build ultra-comprehensive single query with all research angles
            logging.info(f"\n🔍 Building comprehensive single-request query...")
            comprehensive_query = self._build_ultra_comprehensive_query(headline, category)
            
            # Make SINGLE API call with all research requirements
            research_result = self._call_perplexity_api(comprehensive_query)
            
            # Add freshness validation to citations
            if self.freshness_validator and research_result.get('status') == 'success':
                citations = research_result.get('citations', [])
                articles = self._convert_citations_to_articles(citations)
                
                if articles:
                    validation_results = self.freshness_validator.validate_article_collection(
                        articles, "perplexity_research"
                    )
                    
                    # Filter for only fresh citations
                    fresh_articles, outdated_articles = self.freshness_validator.filter_fresh_articles(articles)
                    
                    # Update citations to only include fresh sources
                    fresh_citations = []
                    fresh_sources = []
                    
                    for article in fresh_articles:
                        # Find corresponding citation
                        for citation in citations:
                            if isinstance(citation, dict) and citation.get('url') == article.get('url'):
                                fresh_citations.append(citation)
                                fresh_sources.append(article.get('url'))
                                break
                    
                    # Update research result with only fresh citations
                    research_result['citations'] = fresh_citations
                    research_result['sources'] = fresh_sources
                    
                    logging.info(f"🕐 Perplexity freshness validation:")
                    logging.info(f"   ✅ Fresh citations: {len(fresh_citations)}")
                    logging.info(f"   🚫 Outdated excluded: {len(outdated_articles)}")
                    logging.info(f"   📊 Quality score: {validation_results['validation_summary']['quality_score']:.1f}%")
            
            # Structure the enhanced research data
            research_data = {
                'headline': headline,
                'source': source,
                'category': category,
                'collection_timestamp': datetime.now().isoformat(),
                'research_sections': {
                    'comprehensive': research_result
                },
                'compiled_sources': research_result.get('sources', []),
                'compiled_citations': research_result.get('citations', []),
                'enhanced_research': True,
                'single_request_optimized': True,
                'total_research_calls': 1,  # Only 1 request used
                'status': research_result.get('status', 'unknown')
            }
            
            # Add freshness metadata if validation was performed
            if self.freshness_validator and 'validation_results' in locals():
                research_data['content_freshness'] = {
                    'validation_results': validation_results['validation_summary'],
                    'fresh_citations_used': len(fresh_citations) if 'fresh_citations' in locals() else 0,
                    'outdated_citations_excluded': len(outdated_articles) if 'outdated_articles' in locals() else 0,
                    'freshness_validated': True,
                    'perplexity_7day_filter': True
                }
            
            if research_result.get('status') == 'success':
                logging.info(f"✅ Enhanced single-request research complete!")
                logging.info(f"   📚 Sources collected: {len(research_data['compiled_sources'])}")
                logging.info(f"   🔗 Citations: {len(research_data['compiled_citations'])}")
                logging.info(f"   ⚡ API calls used: 1 (rate limit friendly)")
            else:
                logging.warning(f"⚠️  Research collection returned with status: {research_result.get('status')}")
            
            return research_data
                
        except Exception as e:
            logging.error(f"❌ Error in enhanced single-request research: {e}")
            # Fallback to standard method
            return self.collect_research_for_headline(headline, source, category)
    
    def collect_research_for_headline(self, headline: str, 
                                     source: Optional[str] = None,
                                     category: Optional[str] = None) -> Dict:
        """
        Collect comprehensive research information about a headline
        OPTIMIZED: Uses 1 comprehensive request to minimize API calls
        SPORT-SPECIFIC: Automatically routes to specialized methods based on category
        
        Args:
            headline (str): Article headline to research
            source (str): Original source of the headline
            category (str): Article category (cricket, football, basketball, etc.)
            
        Returns:
            Dict: Structured research data with citations and sources for article generation
        """
        # Route to sport-specific method if category is recognized
        if category:
            category_lower = category.lower()
            if 'football' in category_lower or 'soccer' in category_lower:
                return self.collect_football_research_for_headline(headline, source, category)
            elif 'cricket' in category_lower:
                return self.collect_cricket_research_for_headline(headline, source, category)
            elif 'basketball' in category_lower or 'nba' in category_lower:
                return self.collect_basketball_research_for_headline(headline, source, category)
        try:
            if not self.api_key:
                logging.error("❌ Perplexity API key not configured")
                return self._get_placeholder_research(headline, "API key not configured")
            
            logging.info(f"\n{'='*70}")
            logging.info(f"📡 RESEARCH COLLECTION PHASE (OPTIMIZED - 1 REQUEST)")
            logging.info(f"{'='*70}")
            logging.info(f"📰 Headline: {headline}")
            logging.info(f"📍 Source: {source or 'Unknown'}")
            logging.info(f"🏷️  Category: {category or 'General'}")
            
            # Build ONE comprehensive query to get all needed information
            logging.info(f"\n🔍 Making comprehensive research request...")
            comprehensive_query = self._build_ultra_comprehensive_query(headline, category)
            
            # Make SINGLE API call
            research_result = self._call_perplexity_api(comprehensive_query)
            
            # Structure the research data
            research_data = {
                'headline': headline,
                'source': source,
                'category': category,
                'collection_timestamp': datetime.now().isoformat(),
                'research_sections': {
                    'comprehensive': research_result
                },
                'compiled_sources': research_result.get('sources', []),
                'compiled_citations': research_result.get('citations', []),
                'status': research_result.get('status', 'unknown')
            }
            
            # Add freshness validation for Perplexity sources
            if self.freshness_validator and research_result.get('status') == 'success':
                # Convert Perplexity citations to article format for validation
                perplexity_articles = self._convert_citations_to_articles(research_result.get('citations', []))
                
                if perplexity_articles:
                    validation_results = self.freshness_validator.validate_article_collection(
                        perplexity_articles, "perplexity_research"
                    )
                    
                    research_data['content_freshness'] = {
                        'validation_results': validation_results['validation_summary'],
                        'sources_validated': len(perplexity_articles),
                        'freshness_validated': True,
                        'perplexity_7day_filter': True  # Perplexity already filters last 7 days
                    }
                    
                    logging.info(f"   🕐 Freshness validation: {validation_results['validation_summary']['quality_score']:.1f}% fresh")
            
            if research_result.get('status') == 'success':
                logging.info(f"✅ Research collection complete!")
                logging.info(f"   📚 Sources collected: {len(research_data['compiled_sources'])}")
                logging.info(f"   🔗 Citations: {len(research_data['compiled_citations'])}")
            else:
                logging.warning(f"⚠️  Research collection returned with status: {research_result.get('status')}")
            
            return research_data
                
        except Exception as e:
            logging.error(f"❌ Error collecting research for '{headline}': {e}")
            return self._get_placeholder_research(headline, str(e))
    
    def _build_main_query(self, headline: str, category: Optional[str] = None) -> str:
        """Build main topic research query with enhanced quote collection"""
        query = f"""Find out the latest and trending overall related information to this article, {headline}
        

Focus on latest, verified information from trusted sources."""
        return query
    
    def _build_ultra_comprehensive_query(self, headline: str, category: Optional[str] = None) -> str:
        """
        Build structured research query for sports headlines
        Returns research notes format (400-500 words, bullet points)
        """
        query = f"""Find all verified and relevant information about the following sports headline from trusted sources:

"{headline}"

Provide structured research notes with the following rules:

**Output requirements:**
- Total length: 500-600 words
- Use bullet points or short factual paragraphs only
- Do not write an article or narrative flow
- Avoid stylistic or descriptive language
- Do not add opinions or predictions

**Mandatory sections:**
1. Event summary
2. Key facts and statistics
3. Timeline
4. Official statements and quotes
5. Sport-specific context (based on headline type)

**Sport-specific rules:**
- For transfers or trades: clearly separate confirmed and reported
- For injuries: mention recovery only if officially stated
- For performance news: include recent form stats

**Source rules:**
- Trusted sources only
- No speculation
- Cite sources clearly

Provide factual research material suitable for editorial reference."""
        
        return query
        
    def _extract_story_focus(self, headline: str) -> Dict[str, str]:
        """
        Extract the core story elements to keep search focused
        """
        headline_lower = headline.lower()
        words = headline.split()
        
        # Identify main subject (usually first entity mentioned)
        main_subject = ""
        key_action = ""
        story_focus = headline
        
        # Detect story type and extract focus
        if any(term in headline_lower for term in ['transfer', 'signing', 'sign', 'deal', 'move']):
            # Transfer story
            key_action = "the transfer/signing deal"
            # Find player/team names
            entities = self._extract_key_entities_simple(headline)
            if entities['persons']:
                main_subject = f"{entities['persons'][0]}'s potential move"
            elif entities['teams']:
                main_subject = f"{entities['teams'][0]}'s transfer activity"
            story_focus = f"this specific transfer deal involving {entities['persons'][0] if entities['persons'] else entities['teams'][0] if entities['teams'] else 'the parties'}"
            
        elif any(term in headline_lower for term in ['injury', 'injured', 'hurt', 'fitness']):
            # Injury story
            key_action = "the injury situation"
            entities = self._extract_key_entities_simple(headline)
            if entities['persons']:
                main_subject = f"{entities['persons'][0]}'s injury"
                story_focus = f"this specific injury to {entities['persons'][0]}"
            
        elif any(term in headline_lower for term in ['goal', 'scored', 'match', 'game', 'win', 'lose', 'draw']):
            # Match/performance story
            key_action = "the match/performance details"
            entities = self._extract_key_entities_simple(headline)
            if entities['teams']:
                main_subject = f"{entities['teams'][0]}'s match"
                story_focus = f"this specific match involving {entities['teams'][0]}"
                
        elif any(term in headline_lower for term in ['manager', 'coach', 'appointment', 'sacked', 'fired']):
            # Management story
            key_action = "the management change"
            entities = self._extract_key_entities_simple(headline)
            if entities['persons']:
                main_subject = f"{entities['persons'][0]}'s managerial situation"
                story_focus = f"this specific management change involving {entities['persons'][0]}"
                
        else:
            # General story - extract first key entity
            entities = self._extract_key_entities_simple(headline)
            if entities['persons']:
                main_subject = f"{entities['persons'][0]}"
            elif entities['teams']:
                main_subject = f"{entities['teams'][0]}"
            else:
                main_subject = " ".join(words[:3])  # First 3 words
            key_action = "the reported situation"
            story_focus = "this specific story"
            
        return {
            'main_subject': main_subject,
            'key_action': key_action, 
            'story_focus': story_focus
        }
        
    def _extract_key_entities_simple(self, headline: str) -> Dict[str, List[str]]:
        """
        Simple entity extraction for story focus
        """
        words = headline.split()
        persons = []
        teams = []
        
        # Simple pattern: Two consecutive capitalized words
        for i in range(len(words) - 1):
            if (words[i][0].isupper() and words[i+1][0].isupper() and 
                len(words[i]) > 2 and len(words[i+1]) > 2):
                candidate = f"{words[i]} {words[i+1]}"
                # Simple heuristic: if contains common team words, it's a team
                if any(team_word in candidate.lower() for team_word in ['united', 'city', 'fc', 'real', 'barcelona']):
                    teams.append(candidate)
                else:
                    persons.append(candidate)
                    
        return {'persons': persons, 'teams': teams}
    

    
    def _build_latest_query(self, headline: str) -> str:
        """Legacy method - redirects to ultra-comprehensive query"""
        return self._build_ultra_comprehensive_query(headline)
    
    def _build_context_query(self, headline: str, category: Optional[str] = None) -> str:
        """Legacy method - redirects to ultra-comprehensive query"""
        return self._build_ultra_comprehensive_query(headline, category)
    
    # ========================================================================
    # SPORT-SPECIFIC RESEARCH METHODS
    # ========================================================================
    
    def collect_football_research_for_headline(self, headline: str,
                                              source: Optional[str] = None,
                                              category: Optional[str] = None) -> Dict:
        """
        FOOTBALL-SPECIFIC RESEARCH: Optimized for football/soccer news
        Uses 20 dedicated football domains for maximum relevance
        """
        try:
            if not self.api_key:
                logging.error("❌ Perplexity API key not configured")
                return self._get_placeholder_research(headline, "API key not configured")
            
            logging.info(f"\n{'='*80}")
            logging.info(f"⚽ FOOTBALL-SPECIFIC RESEARCH")
            logging.info(f"{'='*80}")
            logging.info(f"📰 Headline: {headline}")
            logging.info(f"📍 Source: {source or 'Unknown'}")
            logging.info(f"🎯 Using {len(self.FOOTBALL_DOMAINS)} football-specific domains")
            
            # Build football-specific query
            football_query = self._build_football_query(headline)
            
            # Make API call with football domains
            research_result = self._call_perplexity_api(
                query=football_query,
                domain_filter=self.FOOTBALL_DOMAINS,
                sport_context="football"
            )
            
            # Apply freshness validation
            if self.freshness_validator and research_result.get('status') == 'success':
                citations = research_result.get('citations', [])
                articles = self._convert_citations_to_articles(citations)
                
                if articles:
                    fresh_articles, outdated_articles = self.freshness_validator.filter_fresh_articles(articles)
                    fresh_citations = [c for c in citations if isinstance(c, dict) and 
                                     any(c.get('url') == a.get('url') for a in fresh_articles)]
                    
                    research_result['citations'] = fresh_citations
                    research_result['sources'] = [c.get('url') for c in fresh_citations if isinstance(c, dict)]
                    
                    logging.info(f"⚽ Football research freshness: {len(fresh_citations)} fresh citations")
            
            # Extract SEO keywords from research content
            seo_data = self._extract_seo_keywords(
                research_result.get('content', ''),
                headline
            )
            research_result['seo_keywords'] = seo_data
            
            return self._structure_research_data(headline, source, category, research_result, "football")
            
        except Exception as e:
            logging.error(f"❌ Error in football research: {e}")
            return self._get_placeholder_research(headline, str(e))
    
    def collect_cricket_research_for_headline(self, headline: str,
                                             source: Optional[str] = None,
                                             category: Optional[str] = None) -> Dict:
        """
        CRICKET-SPECIFIC RESEARCH: Optimized for cricket news
        Uses 20 dedicated cricket domains for maximum relevance
        """
        try:
            if not self.api_key:
                logging.error("❌ Perplexity API key not configured")
                return self._get_placeholder_research(headline, "API key not configured")
            
            logging.info(f"\n{'='*80}")
            logging.info(f"🏏 CRICKET-SPECIFIC RESEARCH")
            logging.info(f"{'='*80}")
            logging.info(f"📰 Headline: {headline}")
            logging.info(f"📍 Source: {source or 'Unknown'}")
            logging.info(f"🎯 Using {len(self.CRICKET_DOMAINS)} cricket-specific domains")
            
            # Build cricket-specific query
            cricket_query = self._build_cricket_query(headline)
            
            # Make API call with cricket domains
            research_result = self._call_perplexity_api(
                query=cricket_query,
                domain_filter=self.CRICKET_DOMAINS,
                sport_context="cricket"
            )
            
            # Apply freshness validation
            if self.freshness_validator and research_result.get('status') == 'success':
                citations = research_result.get('citations', [])
                articles = self._convert_citations_to_articles(citations)
                
                if articles:
                    fresh_articles, outdated_articles = self.freshness_validator.filter_fresh_articles(articles)
                    fresh_citations = [c for c in citations if isinstance(c, dict) and 
                                     any(c.get('url') == a.get('url') for a in fresh_articles)]
                    
                    research_result['citations'] = fresh_citations
                    research_result['sources'] = [c.get('url') for c in fresh_citations if isinstance(c, dict)]
                    
                    logging.info(f"🏏 Cricket research freshness: {len(fresh_citations)} fresh citations")
            
            # Extract SEO keywords from research content
            seo_data = self._extract_seo_keywords(
                research_result.get('content', ''),
                headline
            )
            research_result['seo_keywords'] = seo_data
            
            return self._structure_research_data(headline, source, category, research_result, "cricket")
            
        except Exception as e:
            logging.error(f"❌ Error in cricket research: {e}")
            return self._get_placeholder_research(headline, str(e))
    
    def collect_basketball_research_for_headline(self, headline: str,
                                                source: Optional[str] = None,
                                                category: Optional[str] = None) -> Dict:
        """
        BASKETBALL-SPECIFIC RESEARCH: Optimized for basketball/NBA news
        Uses 20 dedicated basketball domains for maximum relevance
        """
        try:
            if not self.api_key:
                logging.error("❌ Perplexity API key not configured")
                return self._get_placeholder_research(headline, "API key not configured")
            
            logging.info(f"\n{'='*80}")
            logging.info(f"🏀 BASKETBALL-SPECIFIC RESEARCH")
            logging.info(f"{'='*80}")
            logging.info(f"📰 Headline: {headline}")
            logging.info(f"📍 Source: {source or 'Unknown'}")
            logging.info(f"🎯 Using {len(self.BASKETBALL_DOMAINS)} basketball-specific domains")
            
            # Build basketball-specific query
            basketball_query = self._build_basketball_query(headline)
            
            # Make API call with basketball domains
            research_result = self._call_perplexity_api(
                query=basketball_query,
                domain_filter=self.BASKETBALL_DOMAINS,
                sport_context="basketball"
            )
            
            # Apply freshness validation
            if self.freshness_validator and research_result.get('status') == 'success':
                citations = research_result.get('citations', [])
                articles = self._convert_citations_to_articles(citations)
                
                if articles:
                    fresh_articles, outdated_articles = self.freshness_validator.filter_fresh_articles(articles)
                    fresh_citations = [c for c in citations if isinstance(c, dict) and 
                                     any(c.get('url') == a.get('url') for a in fresh_articles)]
                    
                    research_result['citations'] = fresh_citations
                    research_result['sources'] = [c.get('url') for c in fresh_citations if isinstance(c, dict)]
                    
                    logging.info(f"🏀 Basketball research freshness: {len(fresh_citations)} fresh citations")
            
            # Extract SEO keywords from research content
            seo_data = self._extract_seo_keywords(
                research_result.get('content', ''),
                headline
            )
            research_result['seo_keywords'] = seo_data
            
            return self._structure_research_data(headline, source, category, research_result, "basketball")
            
        except Exception as e:
            logging.error(f"❌ Error in basketball research: {e}")
            return self._get_placeholder_research(headline, str(e))
    
    # ========================================================================
    # SPORT-SPECIFIC QUERY BUILDERS
    # ========================================================================
    
    def _build_football_query(self, headline: str) -> str:
        """
        Build football-specific research query
        Optimized for transfers, matches, injuries, tactics, and league news
        """
        query = f"""Find all verified and relevant information about the following football/soccer headline from trusted sources:

"{headline}"

Provide structured research notes with the following rules:

**Output requirements:**
- Total length: 500-600 words
- Use bullet points or short factual paragraphs only
- Do not write an article or narrative flow
- Avoid stylistic or descriptive language
- Do not add opinions or predictions
- Include commonly searched terms and trending keywords related to this topic

**Mandatory sections for FOOTBALL:**
1. Event summary (match result, transfer status, injury update, etc.)
2. Key facts and statistics (goals, assists, transfer fee, contract length, etc.)
3. Timeline of events
4. Official statements and quotes from players, managers, or clubs
5. Team/player context (current form, league position, recent performances)
6. Tactical analysis (if match-related)
7. Transfer market implications (if transfer-related)

**Football-specific rules:**
- For transfers: clearly separate confirmed deals from rumors/negotiations
- For matches: include scorers, key moments, league standings impact
- For injuries: mention expected return date only if officially confirmed
- For manager news: include win rate, recent results, contract details
- Include competition context (league, Champions League, cup, etc.)

**Source rules:**
- Trusted football sources only (official clubs, reputable journalists)
- No speculation unless clearly marked as rumors
- Cite sources clearly

**SEO Optimization:**
- Include popular search terms people use to find this type of news
- Mention key player names, team names, and event names that drive searches
- Use terminology that appears in trending football/soccer searches

Provide factual research material suitable for editorial reference."""
        
        return query
    
    def _build_cricket_query(self, headline: str) -> str:
        """
        Build cricket-specific research query
        Optimized for matches, player performances, tournaments, and records
        """
        query = f"""Find all verified and relevant information about the following cricket headline from trusted sources:

"{headline}"

Provide structured research notes with the following rules:

**Output requirements:**
- Total length: 500-600 words
- Use bullet points or short factual paragraphs only
- Do not write an article or narrative flow
- Avoid stylistic or descriptive language
- Do not add opinions or predictions
- Include commonly searched terms and trending keywords related to this topic

**Mandatory sections for CRICKET:**
1. Event summary (match result, player milestone, tournament update, etc.)
2. Key statistics (runs, wickets, strike rates, economy rates, averages)
3. Timeline of events (innings breakdown, key partnerships, fall of wickets)
4. Official statements and quotes from players, coaches, or cricket boards
5. Player/team context (current form, rankings, head-to-head records)
6. Format-specific analysis (Test, ODI, T20, IPL, etc.)
7. Tournament implications (points table, qualification scenarios)

**Cricket-specific rules:**
- For matches: include scorecard details, key partnerships, bowling figures
- For player news: mention current form, career stats, records
- For injuries: specify match availability and recovery timeline if confirmed
- For selection news: include squad composition, tactical reasoning
- For records: provide historical context and previous record holders
- Include format and competition context (Test series, World Cup, IPL, etc.)

**Source rules:**
- Trusted cricket sources only (ICC, cricket boards, established cricket media)
- No speculation unless clearly marked as rumors
- Cite sources clearly

**SEO Optimization:**
- Include popular search terms people use to find cricket news
- Mention key player names, teams, tournaments, and match details that drive searches
- Use terminology that appears in trending cricket searches

Provide factual research material suitable for editorial reference."""
        
        return query
    
    def _build_basketball_query(self, headline: str) -> str:
        """
        Build basketball-specific research query
        Optimized for NBA games, trades, player performances, and team news
        """
        query = f"""Find all verified and relevant information about the following basketball/NBA headline from trusted sources:

"{headline}"

Provide structured research notes with the following rules:

**Output requirements:**
- Total length: 500-600 words
- Use bullet points or short factual paragraphs only
- Do not write an article or narrative flow
- Avoid stylistic or descriptive language
- Do not add opinions or predictions
- Include commonly searched terms and trending keywords related to this topic

**Mandatory sections for BASKETBALL:**
1. Event summary (game result, trade details, player performance, etc.)
2. Key statistics (points, rebounds, assists, shooting percentages, +/-)
3. Timeline of events (quarter-by-quarter breakdown, key plays)
4. Official statements and quotes from players, coaches, or front office
5. Player/team context (season stats, standings, playoff implications)
6. Impact analysis (trade implications, lineup changes, playoff race)
7. Historical context (career highs, franchise records, comparisons)

**Basketball-specific rules:**
- For games: include box score highlights, quarter scores, key runs
- For trades: clearly separate finalized deals from rumors/negotiations
- For player news: mention per-game averages, advanced stats (PER, TS%, etc.)
- For injuries: specify games missed and expected return if confirmed
- For draft/roster news: include draft position, college stats, contract details
- Include league context (NBA, EuroLeague, NCAA, etc.)

**Source rules:**
- Trusted basketball sources only (NBA official, verified reporters, team sites)
- No speculation unless clearly marked as rumors
- Cite sources clearly

**SEO Optimization:**
- Include popular search terms people use to find NBA/basketball news
- Mention key player names, teams, stats, and game details that drive searches
- Use terminology that appears in trending basketball searches

Provide factual research material suitable for editorial reference."""
        
        return query
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _structure_research_data(self, headline: str, source: Optional[str],
                                 category: Optional[str], research_result: Dict,
                                 sport_type: str) -> Dict:
        """
        Structure research data in standardized format
        """
        research_data = {
            'headline': headline,
            'source': source,
            'category': category,
            'sport_type': sport_type,  # football, cricket, basketball
            'collection_timestamp': datetime.now().isoformat(),
            'research_sections': {
                'comprehensive': research_result
            },
            'compiled_sources': research_result.get('sources', []),
            'compiled_citations': research_result.get('citations', []),
            'seo_optimization': research_result.get('seo_keywords', {}),  # SEO keywords and optimized sentences
            'enhanced_research': True,
            'sport_specific_research': True,
            'domains_used': getattr(self, f'{sport_type.upper()}_DOMAINS', []),
            'total_research_calls': 1,
            'status': research_result.get('status', 'unknown')
        }
        
        if research_result.get('status') == 'success':
            logging.info(f"✅ {sport_type.title()} research complete!")
            logging.info(f"   📚 Sources collected: {len(research_data['compiled_sources'])}")
            logging.info(f"   🔗 Citations: {len(research_data['compiled_citations'])}")
            logging.info(f"   🎯 Sport-specific domains: {len(research_data['domains_used'])}")
            
            # Log SEO keywords if available
            seo_info = research_data.get('seo_optimization', {})
            if seo_info.get('seo_keywords'):
                logging.info(f"   🔍 SEO Keywords extracted: {len(seo_info['seo_keywords'])}")
                logging.info(f"   🎯 Top keyword: {seo_info.get('top_keyword', 'N/A')}")
                if seo_info.get('headline_relevant_keywords'):
                    logging.info(f"   📰 Headline-relevant: {', '.join(seo_info['headline_relevant_keywords'][:3])}")
        
        return research_data
    
    def _call_perplexity_api(self, query: str, domain_filter: Optional[List[str]] = None,
                            sport_context: Optional[str] = None) -> Optional[Dict]:
        """
        Make actual API call to Perplexity AI
        
        Args:
            query (str): Search query
            domain_filter (List[str]): Optional list of domains to filter search (max 20)
            sport_context (str): Sport context for system prompt (football, cricket, basketball)
            
        Returns:
            Dict: API response or None if failed
        """
        try:
            # Use provided domain filter or default to general sports domains
            domains_to_use = domain_filter if domain_filter else self.GENERAL_SPORTS_DOMAINS
            
            # Customize system prompt based on sport context
            if sport_context == "football":
                system_prompt = "You are a professional football/soccer news researcher. Your task is to collect verified research material focusing on transfers, match reports, player performances, and tactical analysis. Present information in neutral, factual language suitable for editorial reference."
            elif sport_context == "cricket":
                system_prompt = "You are a professional cricket news researcher. Your task is to collect verified research material focusing on match statistics, player performances, tournament updates, and records. Present information in neutral, factual language suitable for editorial reference."
            elif sport_context == "basketball":
                system_prompt = "You are a professional basketball/NBA news researcher. Your task is to collect verified research material focusing on game statistics, trades, player performances, and team dynamics. Present information in neutral, factual language suitable for editorial reference."
            else:
                system_prompt = "You are a professional sports news researcher. Your task is to collect verified research material only, not to write a publishable article. Present information in neutral, factual language suitable for editorial reference."
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar",  # Use latest Sonar model
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": 3000,
                "temperature": 0.1,  # Very low for factual accuracy
                "top_p": 0.9,
                "stream": False,
                "return_images": False,  # Focus on text content
                "search_recency_filter": "day",  # Last 24 hours for very recent news
                "citations": True,
                "search_domain_filter": domains_to_use  # Use sport-specific or general domains
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract content from response
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                citations = data.get('citations', [])
                
                logging.info(f"✅ Perplexity search successful - Retrieved content")
                
                return {
                    'status': 'success',
                    'content': content,
                    'citations': citations,
                    'sources': self._extract_sources(citations),
                    'tokens_used': data.get('usage', {})
                }
            else:
                logging.error(f"❌ Perplexity API error: {response.status_code} - {response.text}")
                return {
                    'status': 'error',
                    'error': f"API error: {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            logging.error("❌ Perplexity API request timeout")
            return {'status': 'error', 'error': 'Request timeout'}
        except Exception as e:
            logging.error(f"❌ Error calling Perplexity API: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _extract_sources(self, citations: List) -> List[str]:
        """
        Extract source URLs and names from citations
        
        Args:
            citations (List): List of citation objects from API response
            
        Returns:
            List[str]: List of source URLs
        """
        sources = []
        try:
            for citation in citations:
                if isinstance(citation, dict):
                    url = citation.get('url') or citation.get('link')
                    if url:
                        sources.append(url)
                elif isinstance(citation, str):
                    sources.append(citation)
        except Exception as e:
            logging.warning(f"Error extracting sources: {e}")
        
        return sources
    
    def _extract_sources(self, citations: List) -> List[str]:
        """
        Extract source URLs and names from citations
        
        Args:
            citations (List): List of citation objects from API response
            
        Returns:
            List[str]: List of source URLs
        """
        sources = []
        try:
            for citation in citations:
                if isinstance(citation, dict):
                    url = citation.get('url') or citation.get('link')
                    if url:
                        sources.append(url)
                elif isinstance(citation, str):
                    sources.append(citation)
        except Exception as e:
            logging.warning(f"Error extracting sources: {e}")
        
        return sources
    
    def _convert_citations_to_articles(self, citations: List) -> List[Dict]:
        """Convert Perplexity citations to article format for freshness validation"""
        articles = []
        try:
            for citation in citations:
                if isinstance(citation, dict):
                    article = {
                        'url': citation.get('url', ''),
                        'title': citation.get('title', ''),
                        'content': citation.get('text', ''),
                        'published_date': citation.get('date', ''),
                        'source': 'perplexity_research'
                    }
                    if article['url']:  # Only include articles with URLs
                        articles.append(article)
        except Exception as e:
            logging.warning(f"Error converting citations to articles: {e}")
        
        return articles
    
    def _extract_seo_keywords(self, content: str, headline: str, max_keywords: int = 10) -> Dict:
        """
        Extract SEO keywords from research content
        Returns highly relevant keywords and sentences containing them
        
        Args:
            content (str): Research content
            headline (str): Article headline
            max_keywords (int): Maximum number of keywords to extract
            
        Returns:
            Dict: SEO keywords with context sentences
        """
        try:
            import re
            from collections import Counter
            
            # Common stop words to exclude
            stop_words = set([
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'been', 'be',
                'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
                'it', 'its', 'he', 'she', 'they', 'them', 'their', 'his', 'her',
                'as', 'all', 'not', 'so', 'if', 'than', 'when', 'where', 'who',
                'which', 'what', 'how', 'said', 'about', 'after', 'also', 'into'
            ])
            
            # Extract words from content (2-3 word phrases are better for SEO)
            content_lower = content.lower()
            headline_lower = headline.lower()
            
            # Extract individual words
            words = re.findall(r'\b[a-z]{3,}\b', content_lower)
            word_freq = Counter([w for w in words if w not in stop_words])
            
            # Extract 2-word phrases (bigrams) - better for SEO
            sentences = re.split(r'[.!?\n]', content)
            bigrams = []
            for sentence in sentences:
                words_in_sent = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
                for i in range(len(words_in_sent) - 1):
                    if words_in_sent[i] not in stop_words:
                        bigram = f"{words_in_sent[i]} {words_in_sent[i+1]}"
                        bigrams.append(bigram)
            
            bigram_freq = Counter(bigrams)
            
            # Get top keywords (mix of single words and phrases)
            top_single_words = [word for word, count in word_freq.most_common(max_keywords * 2)]
            top_bigrams = [phrase for phrase, count in bigram_freq.most_common(max_keywords)]
            
            # Prioritize keywords that appear in headline
            headline_words = set(re.findall(r'\b[a-z]{3,}\b', headline_lower))
            priority_keywords = [kw for kw in top_single_words if kw in headline_words]
            
            # Combine and deduplicate
            all_keywords = priority_keywords[:3] + top_bigrams[:5] + top_single_words[:max_keywords]
            unique_keywords = []
            seen = set()
            for kw in all_keywords:
                if kw not in seen and len(unique_keywords) < max_keywords:
                    unique_keywords.append(kw)
                    seen.add(kw)
            
            # Extract sentences containing top keywords
            keyword_sentences = {}
            for keyword in unique_keywords[:5]:  # Top 5 keywords
                for sentence in sentences:
                    if keyword in sentence.lower() and len(sentence.strip()) > 30:
                        if keyword not in keyword_sentences:
                            keyword_sentences[keyword] = sentence.strip()[:200]  # First 200 chars
                        break
            
            return {
                'seo_keywords': unique_keywords,
                'keyword_sentences': keyword_sentences,
                'top_keyword': unique_keywords[0] if unique_keywords else None,
                'headline_relevant_keywords': priority_keywords[:3]
            }
            
        except Exception as e:
            logging.warning(f"Error extracting SEO keywords: {e}")
            return {
                'seo_keywords': [],
                'keyword_sentences': {},
                'top_keyword': None,
                'headline_relevant_keywords': []
            }
    
    def _get_placeholder_research(self, headline: str, error: str) -> Dict:
        """
        Return a placeholder research response when API is not available
        Useful for development and testing
        
        Args:
            headline (str): Article headline
            error (str): Error message
            
        Returns:
            Dict: Placeholder research structure
        """
        return {
            'headline': headline,
            'error': error,
            'collection_timestamp': datetime.now().isoformat(),
            'status': 'placeholder',
            'research_sections': {
                'main_topic': {
                    'status': 'placeholder',
                    'content': f"Research information about: {headline}\n\n[Perplexity will provide detailed research from trusted internet sources]",
                    'sources': [],
                    'citations': []
                },
                'latest_developments': {
                    'status': 'placeholder',
                    'content': '[Latest developments will be collected]',
                    'sources': [],
                    'citations': []
                },
                'context_background': {
                    'status': 'placeholder',
                    'content': '[Background context will be collected]',
                    'sources': [],
                    'citations': []
                }
            },
            'compiled_sources': [],
            'compiled_citations': [],
            'note': 'This is placeholder research. Configure Perplexity API for real research data.'
        }


class ResearchToArticleOrchestrator:
    """
    Orchestrates the complete research-to-article workflow:
    1. Collect research using Perplexity
    2. Generate SEO-optimized article using Gemini
    """
    
    def __init__(self, perplexity_client: PerplexityResearchCollector, 
                 gemini_client=None):
        """
        Initialize Research-to-Article Orchestrator
        
        Args:
            perplexity_client (PerplexityResearchCollector): Configured Perplexity client
            gemini_client: Configured Gemini AI client (will be used later)
        """
        self.perplexity = perplexity_client
        self.gemini = gemini_client
    
    def orchestrate_research_collection(self, article_entry: Dict) -> Dict:
        """
        Orchestrate research collection for an article headline
        
        Args:
            article_entry (Dict): Article entry from database
            
        Returns:
            Dict: Complete research data ready for Gemini article generation
        """
        headline = article_entry.get('title', '')
        source = article_entry.get('source_name', '')
        category = article_entry.get('category', '')
        
        logging.info(f"\n{'='*70}")
        logging.info(f"🔬 RESEARCH ORCHESTRATION PHASE")
        logging.info(f"{'='*70}")
        
        # Step 1: Collect research
        logging.info(f"\n📡 Step 1: Collecting research from internet sources...")
        research_data = self.perplexity.collect_research_for_headline(
            headline=headline,
            source=source,
            category=category
        )
        
        # Step 2: Prepare research context
        logging.info(f"\n📝 Step 2: Preparing research context for article generation...")
        research_context = self._prepare_research_context(research_data, article_entry)
        
        logging.info(f"✅ Research orchestration complete!")
        logging.info(f"   📚 Research sections: {len(research_data.get('research_sections', {}))}")
        logging.info(f"   🔗 Total sources: {len(research_data.get('compiled_sources', []))}")
        
        return research_context
    
    def _prepare_research_context(self, research_data: Dict, article_entry: Dict) -> Dict:
        """
        Prepare structured research context for Gemini article generation
        
        Args:
            research_data (Dict): Research collected from Perplexity
            article_entry (Dict): Original article metadata
            
        Returns:
            Dict: Structured research context ready for article generation
        """
        context = {
            'article_headline': article_entry.get('title', ''),
            'article_source': article_entry.get('source_name', ''),
            'article_category': article_entry.get('category', ''),
            'article_url': article_entry.get('url', ''),
            'published_date': article_entry.get('published_date', ''),
            'importance_score': article_entry.get('importance_score', 0),
            
            'research_data': research_data,
            
            'article_generation_instructions': {
                'tone': 'professional, engaging, informative',
                'format': 'blog post / news article',
                'length': '1000-1500 words',
                'requirements': [
                    'SEO optimized with relevant keywords',
                    'Include citations to research sources',
                    'Professional journalistic style',
                    'Engaging introduction and conclusion',
                    'Well-structured with clear sections',
                    'Human-written quality content'
                ]
            },
            
            'prepared_timestamp': datetime.now().isoformat()
        }
        
        return context


def main():
    """
    Demonstration of Perplexity Research Collection
    Shows how research is collected and prepared for Gemini article generation
    """
    import json
    
    logging.info("="*70)
    logging.info("PERPLEXITY AI RESEARCH COLLECTION - DEMONSTRATION")
    logging.info("="*70)
    
    # Initialize Perplexity client
    perplexity_client = PerplexityResearchCollector()
    
    # Example headlines for testing
    test_headline = "Messi scores stunning goal in Inter Miami's MLS Cup campaign"
    test_source = "ESPN"
    test_category = "football"
    
    logging.info(f"\n🧪 Testing research collection with example headline:\n")
    logging.info(f"📰 {test_headline}")
    
    # Collect research
    research_data = perplexity_client.collect_research_for_headline(
        headline=test_headline,
        source=test_source,
        category=test_category
    )
    
    # Display research summary
    logging.info(f"\n📊 RESEARCH COLLECTION RESULTS:")
    logging.info(f"Status: {research_data.get('status', 'unknown')}")
    logging.info(f"Research sections: {list(research_data.get('research_sections', {}).keys())}")
    logging.info(f"Total sources: {len(research_data.get('compiled_sources', []))}")
    logging.info(f"Citations: {len(research_data.get('compiled_citations', []))}")
    
    # Show sample research content
    main_section = research_data.get('research_sections', {}).get('main_topic', {})
    if main_section.get('content'):
        logging.info(f"\n📝 Sample research content preview:")
        logging.info(f"{main_section.get('content')[:300]}...")
    
    # Save demonstration output
    output_file = "perplexity_research_demo_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(research_data, f, indent=2, ensure_ascii=False)
    logging.info(f"\n✅ Research output saved to {output_file}")
    
    logging.info(f"\n{'='*70}")
    logging.info(f"This research data is now ready to be passed to Gemini AI")
    logging.info(f"for SEO-optimized article generation!")
    logging.info(f"{'='*70}")


if __name__ == "__main__":
    main()