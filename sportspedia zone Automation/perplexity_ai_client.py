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

# Load environment variables from .env file
load_dotenv()

# Ensure console can handle UTF-8 output to avoid encoding errors on Windows terminals
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    # If reconfigure is unsupported, continue with default encoding
    pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('perplexity_research.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class PerplexityResearchCollector:
    """
    Collects research information from internet using Perplexity AI
    Role: Pure research data collection from latest and trusted sources
    Output: Structured research with citations for Gemini AI article generation
    """
    
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
        
    def collect_research_for_headline(self, headline: str, 
                                     source: Optional[str] = None,
                                     category: Optional[str] = None) -> Dict:
        """
        Collect comprehensive research information about a headline
        OPTIMIZED: Uses 1 comprehensive request to minimize API calls
        
        Args:
            headline (str): Article headline to research
            source (str): Original source of the headline
            category (str): Article category (cricket, football, basketball, etc.)
            
        Returns:
            Dict: Structured research data with citations and sources for article generation
        """
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
            comprehensive_query = self._build_comprehensive_query(headline, category)
            
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
        """Build main topic research query"""
        query = f"""Research and provide detailed information about: {headline}
        
Please provide:
1. What exactly happened or is the news about
2. Key facts and details
3. People/teams involved
4. Why this is important or interesting
5. Latest status and developments

Focus on latest, verified information from trusted sources."""
        return query
    
    def _build_comprehensive_query(self, headline: str, category: Optional[str] = None) -> str:
        """
        OPTIMIZED: Build ONE comprehensive query to get all research data
        This replaces 3 separate queries with 1 efficient request
        Focuses on trusted sports sources and recent updates
        """
        category_context = f" in {category}" if category else ""
        
        # Define trusted sources based on category
        trusted_sources = "ESPN, BBC Sport, Reuters Sports, Associated Press, The Athletic, Sky Sports, Goal.com, Bleacher Report, Sports Illustrated, official league websites"
        
        if category:
            if 'cricket' in category.lower():
                trusted_sources = "ESPN Cricinfo, ICC Official, Cricbuzz, Wisden, BBC Sport Cricket, The Guardian Cricket, Cricket Australia, BCCI, Sky Sports Cricket"
            elif 'football' in category.lower() or 'soccer' in category.lower():
                trusted_sources = "ESPN FC, BBC Sport Football, Sky Sports Football, Goal.com, The Athletic, FIFA.com, UEFA.com, transfermarkt, Guardian Football, FourFourTwo"
            elif 'basketball' in category.lower() or 'nba' in category.lower():
                trusted_sources = "ESPN NBA, NBA.com, The Athletic, Bleacher Report NBA, Basketball Reference, Yahoo Sports, CBS Sports, NBC Sports"
        
        query = f"""Search and compile the latest, most accurate information about this sports news{category_context}:

"{headline}"

IMPORTANT: Only use information from these TRUSTED SOURCES: {trusted_sources}

Provide comprehensive coverage including:

BREAKING NEWS & LATEST UPDATES (Priority):
- What happened in the last 24-48 hours?
- Most recent official statements or announcements
- Latest scores, statistics, or results
- Breaking developments as of today
- Current status right now

KEY FACTS & DETAILS:
- Specific numbers, scores, statistics, records
- Exact dates and times of events
- Players, teams, coaches involved (with correct spellings)
- Locations, venues, stadiums
- Competition or tournament details

STORY CONTEXT:
- What led to this event?
- Recent form or performance of teams/players involved
- How this fits into the bigger picture (season, career, etc.)
- Previous meetings or similar situations
- Historical significance if relevant

REACTIONS & IMPACT:
- Official statements from coaches, players, or officials
- Expert analysis or commentary
- Fan or public reaction
- What this means for upcoming games or events
- Implications for standings, rankings, or championships

HUMAN INTEREST:
- Any emotional or dramatic elements
- Personal stories or backgrounds
- Memorable moments or quotes
- Why fans care about this

ACCURACY REQUIREMENTS:
- Verify all facts from multiple trusted sources
- Use most recent information available (within last 48 hours preferred)
- Include specific timestamps when available
- Correct player/team names and spellings
- Provide source URLs for verification

Deliver information in a clear, factual manner that can be used to write an engaging story for sports fans."""
        return query
    
    def _build_latest_query(self, headline: str) -> str:
        """Legacy method - kept for backward compatibility"""
        return self._build_comprehensive_query(headline)
    
    def _build_context_query(self, headline: str, category: Optional[str] = None) -> str:
        """Build context and background query - Legacy method"""
        return self._build_comprehensive_query(headline, category)
    
    def _call_perplexity_api(self, query: str) -> Optional[Dict]:
        """
        Make actual API call to Perplexity AI
        
        Args:
            query (str): Search query
            
        Returns:
            Dict: API response or None if failed
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a sports research assistant. Provide detailed, accurate, and up-to-date information from trusted sports news sources. Focus on recent developments and verified facts."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": 3000,
                "temperature": 0.3,
                "top_p": 0.9,
                "stream": False,
                "return_images": False,
                "return_related_questions": False,
                "search_recency_filter": "week",
                "citations": True
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
