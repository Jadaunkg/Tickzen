"""  
Perplexity AI Integration for Intent-Based Sports News Research
Uses intent detection to classify article types and apply targeted research strategies.
Focuses on source credibility and journalistic safety for auto-publishing.

Supported Intent Types:
- Rumour/Transfer/Trade
- Injury/Suspension 
- Match Preview
- Coach/Manager News
- Team Internal Updates
- General Reporting

Role: Intent-Based Research Information Collector
Output: Structured research data with source tier classification and safety gates
"""

import requests
import json
import logging
import os
import sys
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Import enhanced configuration
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
    # Try absolute import first
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

class IntentDetector:
    """
    Detects article intent from headlines to optimize research approach
    Maps headlines to specific research strategies for journalistic safety
    """
    
    # Intent classification patterns
    INTENT_PATTERNS = {
        'rumour_transfer': {
            'keywords': [
                'interest', 'linked', 'move', 'monitoring', 'talks', 'approach', 
                'deal close', 'expected', 'set to join', 'transfer', 'signing', 
                'bid', 'offer', 'wants', 'target', 'chase', 'pursue', 'swoop',
                'deal', 'agreement', 'negotiate', 'contract'
            ],
            'priority': 'high'  # Needs careful source verification
        },
        'injury_suspension': {
            'keywords': [
                'injured', 'out', 'ruled out', 'fitness', 'doubt', 'recovery',
                'set to miss', 'sidelined', 'suspended', 'ban', 'medical', 
                'surgery', 'treatment', 'rehabilitation', 'diagnosis', 'scan'
            ],
            'priority': 'high'  # Needs official confirmation
        },
        'match_preview': {
            'keywords': [
                'preview', 'ahead of', 'face', 'clash', 'vs', 'fixture', 
                'meeting', 'showdown', 'gameweek', 'series opener', 'prepare',
                'team news', 'lineup', 'squad', 'tactics', 'prediction'
            ],
            'priority': 'medium'  # Usually safe for auto-publish
        },
        'coach_manager': {
            'keywords': [
                'manager said', 'coach confirms', 'training', 'club statement',
                'press conference', 'interview', 'speaks', 'reveals', 'admits',
                'defends', 'criticizes', 'praises', 'explains', 'announces'
            ],
            'priority': 'medium'  # Direct quotes are usually safe
        },
        'team_internal': {
            'keywords': [
                'staff', 'dressing room', 'ownership', 'board', 'discipline',
                'behind scenes', 'internal', 'club news', 'boardroom', 
                'executives', 'management', 'restructure', 'policy'
            ],
            'priority': 'high'  # Often speculative
        },
        'general_reporting': {
            'keywords': [
                'report', 'news', 'update', 'latest', 'breaking', 'development',
                'story', 'exclusive', 'reveals', 'confirms', 'announces'
            ],
            'priority': 'medium'  # Depends on content
        }
    }
    
    @classmethod
    def detect_intent(cls, headline: str) -> Tuple[str, Dict]:
        """
        Detect article intent from headline
        
        Args:
            headline (str): Article headline
            
        Returns:
            Tuple[str, Dict]: (intent_type, intent_details)
        """
        headline_lower = headline.lower()
        intent_scores = {}
        
        # Score each intent based on keyword matches
        for intent_type, config in cls.INTENT_PATTERNS.items():
            score = 0
            matched_keywords = []
            
            for keyword in config['keywords']:
                if keyword.lower() in headline_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                intent_scores[intent_type] = {
                    'score': score,
                    'matched_keywords': matched_keywords,
                    'priority': config['priority']
                }
        
        if not intent_scores:
            return 'general_reporting', {
                'score': 1,
                'matched_keywords': ['general'],
                'priority': 'medium',
                'fallback': True
            }
        
        # Get highest scoring intent
        top_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k]['score'])
        
        return top_intent, intent_scores[top_intent]
    
    @classmethod
    def get_safety_level(cls, intent_type: str) -> str:
        """
        Get safety level for auto-publishing based on intent
        
        Returns:
            str: 'high', 'medium', 'low'
        """
        safety_mapping = {
            'match_preview': 'high',
            'coach_manager': 'high', 
            'general_reporting': 'high',
            'injury_suspension': 'medium',  # Needs official confirmation
            'rumour_transfer': 'low',       # Needs multiple tier verification
            'team_internal': 'low'          # Often speculative
        }
        
        return safety_mapping.get(intent_type, 'medium')


class ResearchSaver:
    """
    Saves research data for manual review and quality assessment
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize research saver
        
        Args:
            base_dir (str): Base directory for saving research files
        """
        if base_dir:
            self.research_dir = Path(base_dir) / "research"
        else:
            # Default to Sports_Article_Automation/research
            current_file = Path(__file__).parent
            self.research_dir = current_file.parent / "research"
        
        # Create research directory if it doesn't exist
        self.research_dir.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"📁 Research saver initialized: {self.research_dir}")
    
    def save_research(self, headline: str, research_data: Dict) -> str:
        """
        Save research data to file for manual review
        
        Args:
            headline (str): Article headline
            research_data (Dict): Complete research data
            
        Returns:
            str: Path to saved file
        """
        try:
            # Create safe filename from headline
            safe_headline = self._create_safe_filename(headline)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_headline}_{timestamp}_research.json"
            
            file_path = self.research_dir / filename
            
            # Add metadata
            save_data = {
                'headline': headline,
                'saved_timestamp': datetime.now().isoformat(),
                'research_data': research_data,
                'file_info': {
                    'filename': filename,
                    'save_location': str(file_path)
                }
            }
            
            # Save to JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"💾 Research saved: {filename}")
            return str(file_path)
            
        except Exception as e:
            logging.error(f"❌ Error saving research: {e}")
            return ""
    
    def _create_safe_filename(self, headline: str) -> str:
        """
        Create a filesystem-safe filename from headline
        
        Args:
            headline (str): Article headline
            
        Returns:
            str: Safe filename
        """
        # Remove/replace unsafe characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '', headline)
        safe_name = re.sub(r'\s+', '_', safe_name.strip())
        
        # Limit length
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        return safe_name


class PerplexityResearchCollector:
    """
    Collects research information from internet using Perplexity AI
    Role: Pure research data collection from latest and trusted sources
    Output: Structured research with citations for Gemini AI article generation
    """
    
    def __init__(self, api_key: Optional[str] = None, research_save_dir: Optional[str] = None):
        """
        Initialize Perplexity Research Collector with Intent-Based System
        
        Args:
            api_key (str): Perplexity API key. If None, reads from PERPLEXITY_API_KEY env var
            research_save_dir (str): Directory to save research files for manual review
        """
        self.api_key = api_key or os.getenv('PERPLEXITY_API_KEY')
        
        if not self.api_key:
            logging.warning("⚠️  PERPLEXITY_API_KEY not found in environment variables")
            logging.info("ℹ️  To use Perplexity AI:")
            logging.info("   1. Get API key from https://www.perplexity.ai/api")
            logging.info("   2. Set environment variable: set PERPLEXITY_API_KEY=your_key")
            
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar"  # Latest Perplexity model with real-time internet access
        self.timeout = 90
        
        # Initialize intent detection and research saving
        self.intent_detector = IntentDetector()
        self.research_saver = ResearchSaver(research_save_dir)
        
        # Content freshness validator
        if FRESHNESS_VALIDATOR_AVAILABLE:
            self.freshness_validator = ContentFreshnessValidator()
            logging.info("✅ Perplexity - Content Freshness Validation enabled")
        else:
            self.freshness_validator = None
            logging.warning("⚠️ Perplexity - Content Freshness Validation disabled")
        
    def collect_intent_based_research(self, headline: str, 
                                      source: Optional[str] = None,
                                      category: Optional[str] = None) -> Dict:
        """
        NEW METHOD: Intent-based research collection optimized for auto-publishing safety
        
        Args:
            headline (str): Article headline to research
            source (str): Original source of the headline  
            category (str): Article category (cricket, football, basketball, etc.)
            
        Returns:
            Dict: Structured research data with intent classification and safety assessment
        """
        try:
            if not self.api_key:
                logging.error("❌ Perplexity API key not configured")
                return self._get_placeholder_research(headline, "API key not configured")
            
            logging.info(f"\n{'='*80}")
            logging.info(f"🎯 INTENT-BASED RESEARCH COLLECTION")
            logging.info(f"{'='*80}")
            logging.info(f"📰 Headline: {headline}")
            logging.info(f"📍 Source: {source or 'Unknown'}")
            logging.info(f"🏷️  Category: {category or 'General'}")
            
            # Step 1: Detect article intent
            intent_type, intent_details = self.intent_detector.detect_intent(headline)
            safety_level = self.intent_detector.get_safety_level(intent_type)
            
            logging.info(f"\n🔍 Intent Detection Results:")
            logging.info(f"   📊 Intent Type: {intent_type}")
            logging.info(f"   🎯 Matched Keywords: {', '.join(intent_details.get('matched_keywords', []))}")
            logging.info(f"   ⚡ Priority Level: {intent_details.get('priority', 'medium')}")
            logging.info(f"   🛡️  Safety Level: {safety_level}")
            
            # Step 2: Build intent-specific research query
            research_query = self._build_intent_based_query(headline, intent_type, category)
            
            # Step 3: Execute single comprehensive API call
            logging.info(f"\n📡 Executing intent-optimized research call...")
            research_result = self._call_perplexity_api(research_query)
            
            # Step 4: Process and structure results
            research_data = {
                'headline': headline,
                'source': source,
                'category': category,
                'collection_timestamp': datetime.now().isoformat(),
                
                # Intent classification
                'intent_classification': {
                    'detected_intent': intent_type,
                    'intent_details': intent_details,
                    'safety_level': safety_level,
                    'auto_publish_recommended': safety_level in ['high', 'medium']
                },
                
                # Research data
                'research_content': research_result.get('content', ''),
                'sources': research_result.get('sources', []),
                'citations': research_result.get('citations', []),
                
                # Quality metrics
                'quality_assessment': self._assess_research_quality(research_result, intent_type),
                
                # Processing metadata
                'intent_based_research': True,
                'api_calls_used': 1,
                'status': research_result.get('status', 'unknown')
            }
            
            # Step 5: Add freshness validation
            if self.freshness_validator and research_result.get('status') == 'success':
                citations = research_result.get('citations', [])
                articles = self._convert_citations_to_articles(citations)
                
                if articles:
                    validation_results = self.freshness_validator.validate_article_collection(
                        articles, "perplexity_intent_research"
                    )
                    
                    research_data['content_freshness'] = {
                        'validation_results': validation_results['validation_summary'],
                        'sources_validated': len(articles),
                        'freshness_validated': True,
                        'perplexity_recency_filter': 'day'  # Using daily filter
                    }
            
            # Step 6: Save research for manual review
            saved_path = self.research_saver.save_research(headline, research_data)
            if saved_path:
                research_data['research_file_saved'] = saved_path
            
            # Step 7: Log results
            if research_result.get('status') == 'success':
                logging.info(f"\n✅ Intent-based research complete!")
                logging.info(f"   📊 Intent: {intent_type} (Safety: {safety_level})")
                logging.info(f"   📚 Sources: {len(research_data['sources'])}")
                logging.info(f"   🔗 Citations: {len(research_data['citations'])}")
                logging.info(f"   🛡️  Auto-publish safe: {research_data['intent_classification']['auto_publish_recommended']}")
                logging.info(f"   💾 Research saved: {saved_path}")
            else:
                logging.warning(f"⚠️  Research collection returned status: {research_result.get('status')}")
            
            return research_data
                
        except Exception as e:
            logging.error(f"❌ Error in intent-based research: {e}")
            # Fallback to legacy method
            return self.collect_research_for_headline(headline, source, category)
    def _build_intent_based_query(self, headline: str, intent_type: str, category: Optional[str] = None) -> str:
        """
        Build research query tailored to specific article intent for comprehensive coverage
        
        Args:
            headline (str): Article headline
            intent_type (str): Detected intent type
            category (str): Sport category
            
        Returns:
            str: Intent-optimized research query
        """
        base_instruction = f'Research this headline comprehensively with source tier classification: "{headline}"\n\n'
        
        # Enhanced research requirements
        research_requirements = """RESEARCH REQUIREMENTS:
📊 TARGET: 700-800 words comprehensive research
🔍 FALLBACK: If limited information available, provide structured key points covering all angles
📰 SOURCES: Search ALL available sources - no domain restrictions
⏱️  RECENCY: Latest information preferred

SOURCE TIER CLASSIFICATION:
- Tier 1: Official club sites, league websites, wire services (Reuters, AP), verified social media
- Tier 2: Major broadcasters (BBC, Sky Sports, ESPN), established news outlets
- Tier 3: Digital sports outlets (Goal, The Athletic), specialized sports media  
- Tier 4: Secondary sports blogs/websites, fan sites
- Tier 5: Social media, forums, unofficial sources

For each fact, specify the source tier and exact source name.\n\n"""
        
        if intent_type == 'rumour_transfer':
            specific_instruction = """TRANSFER/RUMOUR RESEARCH PROTOCOL (700-800 words target):
            
📋 COMPREHENSIVE COVERAGE REQUIRED:

1. CONFIRMED FACTS (Tier 1-2 sources):
   - Official club announcements (full details)
   - Medical scheduled/completed status
   - Contract specifics (fee, duration, wages, bonuses)
   - Player/agent official statements
   - League registration status

2. REPORTED DEVELOPMENTS (by tier with timestamps):
   - Tier 1: Wire service reports (Reuters, AP)
   - Tier 2: Major broadcaster exclusives (BBC, Sky, ESPN)
   - Tier 3: Sports outlet reports (Goal, Athletic, etc.)
   - Tier 4+: Include if corroborated by multiple sources

3. TRANSFER TIMELINE & PROGRESS:
   - Initial interest reports (when first reported)
   - Negotiation phases and current status
   - Medical examination scheduling
   - Personal terms agreement status
   - Expected completion timeline

4. CONTEXT & BACKGROUND:
   - Player's current situation
   - Previous transfer history
   - Financial fair play considerations
   - Competition from other clubs
   - Market value analysis

5. EXPERT OPINIONS (if available):
   - Transfer market analysts
   - Former players/managers comments
   - Financial experts on deal structure

FALLBACK (if limited info): Provide structured bullet points covering:
• What's confirmed vs. speculated
• Key stakeholders involved
• Potential obstacles
• Timeline expectations
• Market context

List each source's claim separately with tier classification."""
            
        elif intent_type == 'injury_suspension':
            specific_instruction = """INJURY/MEDICAL RESEARCH PROTOCOL (700-800 words target):
            
🏥 COMPREHENSIVE MEDICAL COVERAGE REQUIRED:

1. OFFICIAL MEDICAL UPDATES (Tier 1-2 sources):
   - Club medical team detailed statements
   - Manager press conference confirmations with context
   - League official injury reports
   - Player's own statements/social media
   - Medical staff interviews
   - Scan results (if disclosed)

2. INJURY DETAILS & CONTEXT:
   - Type and severity of injury
   - How injury occurred (match circumstances)
   - Previous injury history
   - Treatment approach being taken
   - Specialists consulted

3. RECOVERY TIMELINE ANALYSIS:
   - Official prognosis with source
   - Typical recovery times for similar injuries
   - Rehabilitation program details
   - Return to training schedule
   - Match availability projections

4. TEAM IMPACT ASSESSMENT:
   - Next fixture availability status
   - Training participation updates
   - Squad selection implications
   - Tactical adjustments needed
   - Squad depth considerations
   - Alternative player options

5. HISTORICAL CONTEXT:
   - Similar injuries to same player
   - Club's recent injury record
   - Medical team's track record
   - Previous recovery timelines

6. EXPERT OPINIONS (if available):
   - Sports medicine experts
   - Former players with similar injuries
   - Medical journalists' analysis

FALLBACK (if limited info): Structured points covering:
• Official vs. speculated information
• Confirmed timeline details
• Team impact assessment
• Recovery expectations
• Historical context

Mark all estimated timelines clearly with source credibility level."""
            
        elif intent_type == 'match_preview':
            specific_instruction = """MATCH PREVIEW RESEARCH PROTOCOL (700-800 words target):
            
⚽ COMPREHENSIVE MATCH ANALYSIS REQUIRED:

1. SQUAD AVAILABILITY & TEAM NEWS:
   - Confirmed injuries/suspensions with sources
   - Player availability status updates
   - Squad rotation plans (if officially stated)
   - New signings eligibility
   - Youth players called up
   - Disciplinary issues affecting selection

2. PERFORMANCE DATA & STATISTICS:
   - Last 5 matches record for both teams
   - Head-to-head statistics (recent history)
   - Recent goal/points averages
   - Home/away form comparison
   - Scoring patterns and defensive records
   - Set-piece effectiveness

3. TACTICAL ANALYSIS:
   - Formation changes (if announced)
   - Recent coaching statements about tactics
   - Key player roles and matchups
   - Strategic considerations
   - Previous tactical approaches in similar fixtures

4. EXTERNAL FACTORS & CONTEXT:
   - Weather conditions forecast
   - Venue information and significance
   - Referee appointments and history
   - Fan attendance expectations
   - Scheduling advantages/disadvantages

5. PRESSURE POINTS & STORYLINES:
   - League position implications
   - Rivalry history and significance
   - Managerial pressure situations
   - Player personal milestones
   - Recent controversial incidents

6. EXPERT PREDICTIONS & ANALYSIS:
   - Pundit opinions from credible sources
   - Former players' tactical insights
   - Statistical analysis from sports data sites

FALLBACK (if limited info): Key points covering:
• Team news and availability
• Recent form comparison
• Key tactical battles
• Historical context
• External factors

Provide performance data with sources separately. Focus on factual data and official announcements."""
            
        elif intent_type == 'coach_manager':
            specific_instruction = """COACH/MANAGER NEWS RESEARCH PROTOCOL (700-800 words target):
            
🎙️ COMPREHENSIVE MANAGERIAL COVERAGE REQUIRED:

1. OFFICIAL STATEMENTS & QUOTES:
   - Press conference quotes (exact and in context)
   - Club website official statements
   - Post-match interview transcripts
   - Training ground comments to media
   - Social media posts (if applicable)
   - Written statements or club announcements

2. SOURCE VERIFICATION & CONTEXT:
   - Official club site confirmations
   - Accredited press conference attendance
   - Broadcasting rights holder recordings
   - Wire service verifications
   - Multiple media outlet confirmations
   - Timestamp and location of statements

3. BACKGROUND & CONTEXT ANALYSIS:
   - What prompted the statement/comment
   - Recent team performance context
   - Pressure situations or controversies
   - Previous related statements
   - Club circumstances at time of statement

4. TACTICAL & STRATEGIC INSIGHTS:
   - Team selection philosophy explained
   - Tactical approach discussions
   - Player development comments
   - Transfer strategy indications
   - Long-term vision statements

5. REACTIONS & IMPLICATIONS:
   - Player reactions (if available)
   - Fan response on official channels
   - Media analysis from credible sources
   - Club hierarchy response
   - Opposition reactions

6. HISTORICAL PATTERN ANALYSIS:
   - Manager's typical communication style
   - Previous similar situations
   - Track record of following through
   - Communication patterns under pressure

FALLBACK (if limited info): Structured points covering:
• Direct quotes with full context
• Source verification details
• Background circumstances
• Implications and reactions
• Historical perspective

Only include direct, attributable quotes from verified sources with full context.
Separate official statements from media interpretation."""
            
        elif intent_type == 'team_internal':
            specific_instruction = """TEAM INTERNAL NEWS RESEARCH PROTOCOL (700-800 words target):
            
🏢 COMPREHENSIVE INTERNAL COVERAGE REQUIRED:

1. OFFICIAL CLUB STATEMENTS & ANNOUNCEMENTS:
   - Board meeting outcomes and decisions
   - Executive appointments with backgrounds
   - Policy changes and implementations
   - Disciplinary actions and procedures
   - Governance structure changes
   - Strategic direction announcements

2. VERIFIED INSTITUTIONAL SOURCES:
   - Official club website statements
   - Stock exchange filings and reports
   - League administration communications
   - Regulatory body announcements
   - Government/legal documentation
   - Audit reports and financial disclosures

3. FINANCIAL & BUSINESS ANALYSIS:
   - Published financial accounts with details
   - Investment and partnership announcements
   - Revenue stream developments
   - Cost-cutting or expansion measures
   - Debt restructuring or refinancing
   - Commercial deal announcements

4. LEADERSHIP & STAFFING DEVELOPMENTS:
   - Executive appointments with experience
   - Confirmed departures and reasons
   - Role changes and responsibilities
   - Board composition changes
   - Management structure updates
   - Succession planning announcements

5. STRATEGIC IMPLICATIONS:
   - Impact on sporting operations
   - Fan and stakeholder reactions
   - Market response (if publicly traded)
   - Competitor analysis and positioning
   - Long-term strategic implications

6. TRANSPARENCY & VERIFICATION:
   - Multiple source confirmations
   - Timeline of developments
   - Previous related decisions
   - Regulatory compliance aspects

FALLBACK (if limited info): Key verified points:
• Official announcements only
• Source verification details
• Timeline and context
• Stakeholder impact
• Strategic implications

STRICTLY AVOID: Unnamed sources, speculation, rumors, or unverified claims.
Only include information from official channels or verified public records."""
            
        else:  # general_reporting
            specific_instruction = """GENERAL SPORTS NEWS RESEARCH PROTOCOL (700-800 words target):
            
📰 COMPREHENSIVE NEWS COVERAGE REQUIRED:

1. CORE FACTS & EVENT DETAILS:
   - What happened (confirmed events with specifics)
   - When it happened (precise timing/dates)
   - Who was involved (all parties with roles)
   - Where it occurred (venues, locations)
   - How it developed (sequence of events)
   - Why it's significant (importance/impact)

2. SOURCE VERIFICATION & CREDIBILITY:
   - Primary sources (official statements, witnesses)
   - Secondary sources (established media reports)
   - Third-party verification (independent sources)
   - Expert commentary from credible analysts
   - Stakeholder statements and reactions

3. BACKGROUND CONTEXT & HISTORY:
   - Recent related events and timeline
   - Historical precedents or patterns
   - Relevant policy or rule context
   - Previous similar situations
   - Ongoing storylines and connections

4. COMPREHENSIVE IMPACT ASSESSMENT:
   - Immediate consequences and effects
   - Short-term implications for involved parties
   - Potential long-term ramifications
   - Stakeholder reactions and responses
   - Market/competitive impact (if applicable)
   - Fan and public response

5. STATISTICAL & PERFORMANCE DATA:
   - Relevant performance statistics
   - Comparative analysis where appropriate
   - League standings or ranking implications
   - Financial or commercial impact data

6. EXPERT ANALYSIS & COMMENTARY:
   - Industry expert opinions
   - Former players/coaches perspectives
   - Analyst predictions and assessments
   - Media commentary from credible sources

FALLBACK (if limited info): Essential points covering:
• Confirmed facts with sources
• Key stakeholders and reactions
• Context and background
• Immediate implications
• Expert perspectives

Focus on verified facts from credible sources across all available media.
Clearly separate confirmed information from speculation and analysis."""
        
        return base_instruction + research_requirements + specific_instruction
    
    def _assess_research_quality(self, research_result: Dict, intent_type: str) -> Dict:
        """
        Assess research quality and safety for auto-publishing
        
        Args:
            research_result (Dict): Raw research results from Perplexity
            intent_type (str): Article intent type
            
        Returns:
            Dict: Quality assessment with safety recommendations
        """
        quality_score = 0
        safety_signals = []
        warnings = []
        
        content = research_result.get('content', '')
        sources = research_result.get('sources', [])
        citations = research_result.get('citations', [])
        
        # Basic quality checks
        if len(content) > 200:
            quality_score += 20
        if len(sources) >= 2:
            quality_score += 20
        if len(citations) >= 2:
            quality_score += 20
        
        # Intent-specific safety checks
        if intent_type in ['rumour_transfer', 'team_internal']:
            # High-risk intents need extra verification
            if 'tier 1' in content.lower() or 'official' in content.lower():
                safety_signals.append('Official sources mentioned')
                quality_score += 20
            else:
                warnings.append('No official sources detected')
                quality_score -= 10
                
        elif intent_type == 'injury_suspension':
            if any(term in content.lower() for term in ['club confirmed', 'medical', 'official']):
                safety_signals.append('Medical information from official sources')
                quality_score += 20
            else:
                warnings.append('Medical information may be unconfirmed')
                quality_score -= 15
        
        # Source tier analysis
        tier_keywords = {
            'tier_1': ['reuters', 'associated press', 'official', 'club website'],
            'tier_2': ['bbc', 'sky sports', 'espn', 'broadcaster'],
            'tier_3': ['goal', 'athletic', 'digital outlet']
        }
        
        for tier, keywords in tier_keywords.items():
            if any(keyword in content.lower() for keyword in keywords):
                safety_signals.append(f'{tier.replace("_", " ").title()} sources detected')
                quality_score += 10
        
        # Determine auto-publish recommendation
        auto_publish_safe = quality_score >= 60 and len(warnings) == 0
        
        if intent_type in ['rumour_transfer', 'team_internal'] and quality_score < 70:
            auto_publish_safe = False
            warnings.append('High-risk intent needs manual review')
        
        return {
            'quality_score': min(100, max(0, quality_score)),
            'auto_publish_safe': auto_publish_safe,
            'safety_signals': safety_signals,
            'warnings': warnings,
            'recommendation': 'auto_publish' if auto_publish_safe else 'manual_review',
            'assessment_timestamp': datetime.now().isoformat()
        }
    
    def collect_research_for_headline(self, headline: str, 
                                     source: Optional[str] = None,
                                     category: Optional[str] = None) -> Dict:
        """
        LEGACY METHOD: Collect comprehensive research information about a headline
        
        NOTE: This method is maintained for backwards compatibility.
        For new implementations, use collect_intent_based_research() instead.
        
        Args:
            headline (str): Article headline to research
            source (str): Original source of the headline
            category (str): Article category (cricket, football, basketball, etc.)
            
        Returns:
            Dict: Structured research data with citations and sources for article generation
        """
        logging.info(f"\n⚠️  Using legacy research method. Consider upgrading to collect_intent_based_research()")
        
        # Redirect to new intent-based method
        return self.collect_intent_based_research(headline, source, category)
    
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
                "model": "sonar",  # Use latest Sonar model
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional sports researcher providing comprehensive, factual information for news articles. Focus on verified facts from credible sources and gather the latest information from all available sources. Aim for 700-800 words of comprehensive research. If limited information is available, provide key points covering all important angles."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": 4000,  # Increased for comprehensive 700-800 word research
                "temperature": 0.1,  # Very low for factual accuracy
                "top_p": 0.9,
                "stream": False,
                "return_images": False,  # Focus on text content
                "search_recency_filter": "day",  # Last 24 hours for very recent news
                "citations": True
                # Domain filter removed to get broader, latest information from all sources
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
    Demonstration of Intent-Based Perplexity Research Collection
    Shows how different article types are handled with specialized research strategies
    """
    import json
    
    logging.info("="*80)
    logging.info("INTENT-BASED PERPLEXITY AI RESEARCH - DEMONSTRATION")
    logging.info("="*80)
    
    # Initialize Perplexity client with intent-based system
    perplexity_client = PerplexityResearchCollector()
    
    # Test headlines for each intent type
    test_cases = [
        {
            'headline': "Manchester United monitoring Kylian Mbappe move with PSG talks ongoing",
            'category': "football",
            'source': "Sky Sports",
            'expected_intent': "rumour_transfer"
        },
        {
            'headline': "Lionel Messi ruled out for three weeks with hamstring injury",
            'category': "football", 
            'source': "ESPN",
            'expected_intent': "injury_suspension"
        },
        {
            'headline': "Arsenal vs Liverpool team news and preview ahead of Premier League clash",
            'category': "football",
            'source': "BBC Sport",
            'expected_intent': "match_preview"
        },
        {
            'headline': "Pep Guardiola confirms rotation plans in press conference",
            'category': "football",
            'source': "Manchester City Official",
            'expected_intent': "coach_manager"
        },
        {
            'headline': "Chelsea board meeting discusses transfer policy changes", 
            'category': "football",
            'source': "The Athletic",
            'expected_intent': "team_internal"
        }
    ]
    
    logging.info(f"\n🧪 Testing intent-based research with {len(test_cases)} article types:")
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        logging.info(f"\n{'='*60}")
        logging.info(f"TEST {i}/{len(test_cases)}: {test_case['expected_intent'].upper()}")
        logging.info(f"{'='*60}")
        logging.info(f"📰 Headline: {test_case['headline']}")
        logging.info(f"📍 Source: {test_case['source']}")
        logging.info(f"🏷️ Category: {test_case['category']}")
        logging.info(f"🎯 Expected Intent: {test_case['expected_intent']}")
        
        # First show intent detection only
        intent_type, intent_details = perplexity_client.intent_detector.detect_intent(test_case['headline'])
        safety_level = perplexity_client.intent_detector.get_safety_level(intent_type)
        
        logging.info(f"\n🔍 Intent Detection Results:")
        logging.info(f"   ✅ Detected: {intent_type} (Expected: {test_case['expected_intent']})")
        logging.info(f"   🎯 Keywords: {', '.join(intent_details.get('matched_keywords', []))}")
        logging.info(f"   ⚡ Priority: {intent_details.get('priority')}")
        logging.info(f"   🛡️ Safety: {safety_level}")
        logging.info(f"   🤖 Auto-publish: {'✅ Recommended' if safety_level in ['high', 'medium'] else '❌ Manual review'}")
        
        # Store result
        result_summary = {
            'test_case': test_case,
            'detected_intent': intent_type,
            'intent_details': intent_details,
            'safety_level': safety_level,
            'intent_match': intent_type == test_case['expected_intent'],
            'auto_publish_safe': safety_level in ['high', 'medium']
        }
        results.append(result_summary)
        
        # Note: In a real demo, you would uncomment this to actually call Perplexity API
        # research_data = perplexity_client.collect_intent_based_research(
        #     headline=test_case['headline'],
        #     source=test_case['source'], 
        #     category=test_case['category']
        # )
    
    # Summary of results
    logging.info(f"\n{'='*80}")
    logging.info(f"📊 INTENT DETECTION SUMMARY")
    logging.info(f"{'='*80}")
    
    correct_detections = sum(1 for r in results if r['intent_match'])
    auto_publish_safe_count = sum(1 for r in results if r['auto_publish_safe'])
    
    logging.info(f"✅ Correct intent detection: {correct_detections}/{len(results)} ({correct_detections/len(results)*100:.1f}%)")
    logging.info(f"🛡️ Auto-publish safe articles: {auto_publish_safe_count}/{len(results)} ({auto_publish_safe_count/len(results)*100:.1f}%)")
    
    # Show intent-specific safety levels
    intent_safety = {}
    for result in results:
        intent = result['detected_intent']
        if intent not in intent_safety:
            intent_safety[intent] = {'safe': 0, 'total': 0}
        intent_safety[intent]['total'] += 1
        if result['auto_publish_safe']:
            intent_safety[intent]['safe'] += 1
    
    logging.info(f"\n📈 Safety by Intent Type:")
    for intent, stats in intent_safety.items():
        safety_pct = stats['safe'] / stats['total'] * 100 if stats['total'] > 0 else 0
        logging.info(f"   {intent}: {stats['safe']}/{stats['total']} safe ({safety_pct:.1f}%)")
    
    # Save demonstration results
    demo_output = {
        'demonstration_timestamp': datetime.now().isoformat(),
        'intent_detection_accuracy': correct_detections / len(results) * 100,
        'auto_publish_safety_rate': auto_publish_safe_count / len(results) * 100,
        'test_results': results,
        'intent_safety_breakdown': intent_safety
    }
    
    output_file = "intent_based_research_demo_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(demo_output, f, indent=2, ensure_ascii=False)
    
    logging.info(f"\n💾 Demo results saved to {output_file}")
    logging.info(f"\n{'='*80}")
    logging.info(f"🎯 INTENT-BASED RESEARCH SYSTEM READY FOR PRODUCTION")
    logging.info(f"{'='*80}")
    logging.info(f"✅ Research files will be saved to: Sports_Article_Automation/research/")
    logging.info(f"✅ Source tier classification implemented")
    logging.info(f"✅ Auto-publish safety gates configured")
    logging.info(f"✅ Maximum 1 API call per article") 
    logging.info(f"✅ Manual review queue for high-risk content")
    logging.info(f"{'='*80}")


if __name__ == "__main__":
    main()