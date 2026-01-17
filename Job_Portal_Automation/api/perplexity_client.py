"""
Perplexity AI Research Collector for Job Portal Automation
===========================================================

Collects latest research information about government jobs, exam results,
and admit cards from Perplexity AI for content enrichment.

Adapted from Sports_Article_Automation with education/job focus.
"""

import requests
import json
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class PerplexityResearchCollector:
    """
    Collects research information from Perplexity AI about jobs, results, and admit cards.
    
    Role: Pure research data collection from latest and trusted sources
    Output: Structured research with citations for Gemini AI article generation
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Perplexity Research Collector
        
        Args:
            api_key: Perplexity API key. If None, reads from PERPLEXITY_API_KEY env var
        """
        self.api_key = api_key or os.getenv('PERPLEXITY_API_KEY')
        
        if not self.api_key:
            logger.warning("⚠️ PERPLEXITY_API_KEY not found in environment variables")
            logger.info("To use Perplexity AI:")
            logger.info("  1. Get API key from https://www.perplexity.ai/api")
            logger.info("  2. Set PERPLEXITY_API_KEY environment variable")
        
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar"  # Real-time internet access with up-to-date sources
        self.timeout = 90  # Increased timeout for comprehensive research
        
    def collect_research_for_job(self, job_title: str, 
                                 job_portal: Optional[str] = None,
                                 details: Optional[Dict] = None) -> Dict:
        """
        Collect comprehensive research about a government job
        
        Args:
            job_title: Title of the job posting
            job_portal: Portal where job was posted (e.g., SarkariResult)
            details: Extracted job details from API (optional)
            
        Returns:
            Dictionary with research data and citations
        """
        try:
            if not self.api_key:
                logger.error("❌ Perplexity API key not configured")
                return self._get_placeholder_research(job_title, "API key not configured")
            
            logger.info(f"\n{'='*70}")
            logger.info("📡 JOB RESEARCH COLLECTION")
            logger.info(f"{'='*70}")
            logger.info(f"📋 Job Title: {job_title}")
            logger.info(f"🏢 Portal: {job_portal or 'Unknown'}")
            
            # Build comprehensive query for job research
            query = self._build_job_query(job_title, job_portal)
            
            logger.info("🔍 Making research request to Perplexity AI...")
            research_result = self._call_perplexity_api(query)
            
            # Structure the research data
            research_data = {
                'item_title': job_title,
                'item_type': 'job',
                'portal': job_portal,
                'collection_timestamp': datetime.now().isoformat(),
                'research': research_result,
                'compiled_sources': research_result.get('sources', []),
                'compiled_citations': research_result.get('citations', []),
                'status': research_result.get('status', 'unknown')
            }

            # Lightly summarize for downstream Gemini prompt
            research_text = research_result.get('content', '') if isinstance(research_result, dict) else ''
            research_data['summary'] = self._summarize_text(research_text)
            research_data['bullets'] = self._extract_bullets(research_text)
            
            if research_result.get('status') == 'success':
                logger.info(f"✅ Research collection complete!")
                logger.info(f"   📚 Sources: {len(research_data['compiled_sources'])}")
                logger.info(f"   🔗 Citations: {len(research_data['compiled_citations'])}")
            
            return research_data
            
        except Exception as e:
            logger.error(f"❌ Error collecting job research: {e}")
            return self._get_placeholder_research(job_title, str(e))
    
    def collect_research_for_result(self, result_title: str,
                                   result_portal: Optional[str] = None,
                                   details: Optional[Dict] = None) -> Dict:
        """
        Collect comprehensive research about an exam result
        
        Args:
            result_title: Title of the result announcement
            result_portal: Portal where result was announced
            details: Extracted result details from API (optional)
            
        Returns:
            Dictionary with research data and citations
        """
        try:
            if not self.api_key:
                logger.error("❌ Perplexity API key not configured")
                return self._get_placeholder_research(result_title, "API key not configured")
            
            logger.info(f"\n{'='*70}")
            logger.info("📡 RESULT RESEARCH COLLECTION")
            logger.info(f"{'='*70}")
            logger.info(f"📊 Result Title: {result_title}")
            logger.info(f"🏢 Portal: {result_portal or 'Unknown'}")
            
            # Build comprehensive query for result research
            query = self._build_result_query(result_title, result_portal)
            
            logger.info("🔍 Making research request to Perplexity AI...")
            research_result = self._call_perplexity_api(query)
            
            # Structure the research data
            research_data = {
                'item_title': result_title,
                'item_type': 'result',
                'portal': result_portal,
                'collection_timestamp': datetime.now().isoformat(),
                'research': research_result,
                'compiled_sources': research_result.get('sources', []),
                'compiled_citations': research_result.get('citations', []),
                'status': research_result.get('status', 'unknown')
            }

            research_text = research_result.get('content', '') if isinstance(research_result, dict) else ''
            research_data['summary'] = self._summarize_text(research_text)
            research_data['bullets'] = self._extract_bullets(research_text)
            
            if research_result.get('status') == 'success':
                logger.info(f"✅ Research collection complete!")
                logger.info(f"   📚 Sources: {len(research_data['compiled_sources'])}")
                logger.info(f"   🔗 Citations: {len(research_data['compiled_citations'])}")
            
            return research_data
            
        except Exception as e:
            logger.error(f"❌ Error collecting result research: {e}")
            return self._get_placeholder_research(result_title, str(e))
    
    def collect_research_for_admit_card(self, admit_card_title: str,
                                       admit_card_portal: Optional[str] = None,
                                       details: Optional[Dict] = None) -> Dict:
        """
        Collect comprehensive research about an admit card
        
        Args:
            admit_card_title: Title of the admit card
            admit_card_portal: Portal where admit card was announced
            details: Extracted admit card details from API (optional)
            
        Returns:
            Dictionary with research data and citations
        """
        try:
            if not self.api_key:
                logger.error("❌ Perplexity API key not configured")
                return self._get_placeholder_research(admit_card_title, "API key not configured")
            
            logger.info(f"\n{'='*70}")
            logger.info("📡 ADMIT CARD RESEARCH COLLECTION")
            logger.info(f"{'='*70}")
            logger.info(f"🎫 Admit Card Title: {admit_card_title}")
            logger.info(f"🏢 Portal: {admit_card_portal or 'Unknown'}")
            
            # Build comprehensive query for admit card research
            query = self._build_admit_card_query(admit_card_title, admit_card_portal)
            
            logger.info("🔍 Making research request to Perplexity AI...")
            research_result = self._call_perplexity_api(query)
            
            # Structure the research data
            research_data = {
                'item_title': admit_card_title,
                'item_type': 'admit_card',
                'portal': admit_card_portal,
                'collection_timestamp': datetime.now().isoformat(),
                'research': research_result,
                'compiled_sources': research_result.get('sources', []),
                'compiled_citations': research_result.get('citations', []),
                'status': research_result.get('status', 'unknown')
            }

            research_text = research_result.get('content', '') if isinstance(research_result, dict) else ''
            research_data['summary'] = self._summarize_text(research_text)
            research_data['bullets'] = self._extract_bullets(research_text)
            
            if research_result.get('status') == 'success':
                logger.info(f"✅ Research collection complete!")
                logger.info(f"   📚 Sources: {len(research_data['compiled_sources'])}")
                logger.info(f"   🔗 Citations: {len(research_data['compiled_citations'])}")
            
            return research_data
            
        except Exception as e:
            logger.error(f"❌ Error collecting admit card research: {e}")
            return self._get_placeholder_research(admit_card_title, str(e))
    
    def _build_job_query(self, job_title: str, job_portal: Optional[str]) -> str:
        """Build comprehensive research query for a job"""
        portal_context = f" posted on {job_portal}" if job_portal else ""
        
        query = f"""Find all relevant and complete information about this government job{portal_context}:

"{job_title}"

Please provide comprehensive details including:
- Latest updates and notifications about this recruitment
- Official announcements from recruiting organization
- Complete eligibility criteria requirements
- Detailed application process and timeline
- Important dates and deadlines
- Selection process and exam patterns
- Previous year cutoff marks and qualification statistics
- Salary structure and job benefits
- Job location and posting details
- Official links and contact information

Requirements:
- Use only trusted government sources and official recruitment websites
- Focus on the most recent and accurate information
- Provide specific facts, dates, and official announcements
- Include eligibility details and qualification requirements
- Mention important contact details and official links

Please provide a comprehensive overview of this job opportunity with all important details."""
        
        return query
    
    def _build_result_query(self, result_title: str, result_portal: Optional[str]) -> str:
        """Build comprehensive research query for a result"""
        portal_context = f" announced on {result_portal}" if result_portal else ""
        
        query = f"""Find all relevant and complete information about this exam result{portal_context}:

"{result_title}"

Please provide comprehensive details including:
- Official result announcement details and cutoff marks
- Qualification and merit list information
- Result release timeline and notification procedures
- Score card download process and details
- Next steps after result (interview, document verification, etc.)
- Previous year result statistics and analysis
- Cutoff marks by category and qualification
- Official notification links and download portals
- Important instructions for successful candidates
- Contact information and official sources

Requirements:
- Use only trusted government sources and official recruitment websites
- Focus on the most recent and accurate result information
- Provide specific facts, dates, and official announcements
- Include details about cutoff marks and merit lists
- Mention official links and download procedures

Please provide a comprehensive overview of this result announcement with all important details."""
        
        return query
    
    def _build_admit_card_query(self, admit_card_title: str, admit_card_portal: Optional[str]) -> str:
        """Build comprehensive research query for an admit card"""
        portal_context = f" from {admit_card_portal}" if admit_card_portal else ""
        
        query = f"""Find all relevant and complete information about this admit card{portal_context}:

"{admit_card_title}"

Please provide comprehensive details including:
- Admit card release announcement and notification details
- How to download and access the admit card
- Required documents and information on admit card
- Exam date, time and center details
- Exam pattern and duration
- Instructions for exam day
- Admit card validity and requirements
- Reporting time and venue information
- Contact information for exam queries
- Important instructions and rules
- Official download links and portals

Requirements:
- Use only trusted government sources and official recruitment websites
- Focus on the most recent admit card information
- Provide specific facts, dates, and official announcements
- Include step-by-step download instructions
- Mention all important guidelines and rules

Please provide a comprehensive overview of this admit card announcement with all important details."""
        
        return query
    
    def _call_perplexity_api(self, query: str) -> Dict:
        """
        Call Perplexity API with the given query
        
        Args:
            query: Research query string
            
        Returns:
            API response with research data
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
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": 0.2,
                "top_p": 0.9,
                "return_citations": True,
                "search_recency_filter": "week"
            }
            
            logger.debug(f"Calling Perplexity API with model: {self.model}")
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            # Parse response
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = result.get("citations", [])
            
            logger.debug(f"Received response with {len(citations)} citations")
            
            return {
                'status': 'success',
                'content': content,
                'citations': citations,
                'sources': citations if isinstance(citations, list) else [citations] if citations else []
            }
            
        except requests.exceptions.Timeout:
            logger.error("Perplexity API request timeout")
            return {
                'status': 'error',
                'content': '',
                'citations': [],
                'sources': [],
                'error': 'Request timeout'
            }
        except requests.exceptions.ConnectionError:
            logger.error("Perplexity API connection error")
            return {
                'status': 'error',
                'content': '',
                'citations': [],
                'sources': [],
                'error': 'Connection error'
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"Perplexity API HTTP error: {e}")
            return {
                'status': 'error',
                'content': '',
                'citations': [],
                'sources': [],
                'error': f'HTTP {e.response.status_code}'
            }
        except json.JSONDecodeError:
            logger.error("Failed to parse Perplexity API response")
            return {
                'status': 'error',
                'content': '',
                'citations': [],
                'sources': [],
                'error': 'Invalid JSON response'
            }
        except Exception as e:
            logger.error(f"Unexpected error calling Perplexity API: {e}")
            return {
                'status': 'error',
                'content': '',
                'citations': [],
                'sources': [],
                'error': str(e)
            }

    @staticmethod
    def _summarize_text(text: str, max_len: int = 600) -> str:
        if not text:
            return ""
        compact = " ".join(text.split())
        return compact[:max_len]

    @staticmethod
    def _extract_bullets(text: str, max_items: int = 8) -> List[str]:
        if not text:
            return []
        sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
        return sentences[:max_items]
    
    def _get_placeholder_research(self, title: str, reason: str) -> Dict:
        """
        Return placeholder research when API is unavailable
        
        Args:
            title: Item title
            reason: Reason for placeholder
            
        Returns:
            Placeholder research dictionary
        """
        logger.warning(f"Returning placeholder research for '{title}': {reason}")
        
        return {
            'item_title': title,
            'collection_timestamp': datetime.now().isoformat(),
            'research': {
                'status': 'placeholder',
                'content': f'Research unavailable: {reason}. Please refer to official government portals for latest information.',
                'citations': [],
                'sources': []
            },
            'compiled_sources': [],
            'compiled_citations': [],
            'status': 'placeholder'
        }
