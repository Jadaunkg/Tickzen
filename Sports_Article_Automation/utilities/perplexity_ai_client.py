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
                return {"max_tokens": 4000, "temperature": 0.2, "search_recency_filter": "day"}
            @classmethod
            def get_enhanced_sources(cls, category=None): 
                return ["ESPN", "BBC Sport", "The Athletic", "Reuters", "Associated Press", "Twitter/X verified", "YouTube official", "Reddit sports", "official team sites", "player social media"]

# Load environment variables from .env file
load_dotenv()

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
        
    def collect_enhanced_research_for_headline(self, headline: str, 
                                              source: Optional[str] = None,
                                              category: Optional[str] = None) -> Dict:
        """
        ENHANCED SINGLE-REQUEST METHOD: Collect maximum information in one comprehensive query
        Designed to respect Perplexity API rate limits (2 requests/minute)
        Packs all research angles into one ultra-comprehensive request
        """
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
        Simple and focused query to find latest relevant information from trusted sources
        """
        query = f"""Find the latest maximum possible relevant information available about this headline from trusted internet sources:

"{headline}"

Only include verified information from trusted sources. Do not include assumptions, speculation, or unconfirmed reports."""
        
        return query
    

    
    def _build_latest_query(self, headline: str) -> str:
        """Legacy method - redirects to ultra-comprehensive query"""
        return self._build_ultra_comprehensive_query(headline)
    
    def _build_context_query(self, headline: str, category: Optional[str] = None) -> str:
        """Legacy method - redirects to ultra-comprehensive query"""
        return self._build_ultra_comprehensive_query(headline, category)
    
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
                        "content": "You are a factual information researcher. Find the latest relevant information from trusted internet sources only. Include exact quotes with proper attribution when available. Do not include assumptions, speculation, or unverified information. Only report what can be confirmed from reliable sources."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": 4000,  # Increased for comprehensive research
                "temperature": 0.2,  # Lower for more focused, factual research
                "top_p": 0.85,
                "stream": False,
                "return_images": True,  # Include relevant images/videos
                "return_related_questions": True,  # Get follow-up angles
                "search_recency_filter": "day",  # Focus on most recent (24h)
                "citations": True,
                "search_domain_filter": ["espn.com", "bbc.com", "theguardian.com", "nba.com", "fifa.com", "twitter.com", "youtube.com"]  # Prioritize top sources
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
