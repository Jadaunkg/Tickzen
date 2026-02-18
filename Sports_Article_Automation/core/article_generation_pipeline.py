#!/usr/bin/env python3
"""
Sports Article Generation Pipeline
=================================

Advanced two-stage AI content creation system for sports journalism.
Combines research capabilities with human-quality writing to produce
SEO-optimized, engaging sports articles at scale.

Two-Stage AI Architecture:
-------------------------
1. **Research Phase** (Perplexity AI):
   - Real-time internet research
   - Latest sports news and statistics
   - Player performance data
   - Historical context and trends
   - Multiple source verification

2. **Writing Phase** (Gemini AI):
   - Human-quality article generation
   - SEO optimization and keyword integration
   - Multiple writing styles and tones
   - Fact-based narrative construction
   - Social media snippet generation

Content Pipeline Workflow:
-------------------------
1. **RSS Data Collection**: Monitor sports news feeds
2. **Headline Analysis**: Select trending and engaging topics
3. **Research Orchestration**: Perplexity AI gathers comprehensive data
4. **Content Generation**: Gemini AI creates polished articles
5. **SEO Optimization**: Keyword integration and meta optimization
6. **Quality Assurance**: Automated content validation
7. **Publishing Preparation**: WordPress-ready formatting

Supported Sports Categories:
---------------------------
- NFL (National Football League)
- NBA (National Basketball Association)
- MLB (Major League Baseball)
- NHL (National Hockey League)
- College Sports (NCAA)
- International Sports (Soccer, Tennis, etc.)
- Olympic Sports and Events
- Esports and Gaming

Content Types Generated:
-----------------------
- **Game Recaps**: Post-game analysis and highlights
- **Player Profiles**: Biographical and performance articles
- **Trade Analysis**: Transfer and trade impact analysis
- **Season Previews**: Pre-season analysis and predictions
- **Statistical Deep Dives**: Advanced analytics articles
- **Breaking News**: Real-time news article generation
- **Opinion Pieces**: Editorial and analysis content

Research Data Sources:
---------------------
- Official league APIs and statistics
- Sports news websites and RSS feeds
- Social media sentiment analysis
- Player and team performance databases
- Historical records and archives
- Real-time game data and scores

SEO and Content Optimization:
----------------------------
- Keyword density optimization
- Meta description generation
- Internal linking suggestions
- Featured snippet optimization
- Social media integration
- Image alt-text generation

State Management Integration:
----------------------------
- Publishing history tracking
- Content deduplication
- Performance analytics
- Author attribution management
- Category-specific publishing limits

Quality Control Features:
------------------------
- Fact-checking against reliable sources
- Plagiarism detection and prevention
- Content freshness validation
- Readability score optimization
- Brand voice consistency

WordPress Integration:
---------------------
- Automated post creation
- Category and tag assignment
- Featured image optimization
- Social media auto-posting
- SEO plugin compatibility

Usage Example:
-------------
```python
pipeline = ArticleGenerationPipeline()

# Generate article from RSS headline
article = pipeline.generate_from_headline(
    headline="Lakers Trade Rumors Heat Up",
    category="NBA",
    target_keywords=["Lakers trade", "NBA rumors"]
)

# Publish to WordPress
result = pipeline.publish_article(article, profile_id="sports_site_1")
```

Configuration:
-------------
Environment Variables:
- PERPLEXITY_API_KEY: Research AI access key
- GEMINI_API_KEY: Content generation AI key
- SPORTS_RSS_FEEDS: JSON list of monitored feeds
- CONTENT_QUALITY_THRESHOLD: Minimum quality score

Performance Metrics:
-------------------
- Article generation time (target: <5 minutes)
- Research comprehensiveness score
- SEO optimization rating
- Content uniqueness percentage
- Publishing success rate

Error Handling:
--------------
- AI service fallback mechanisms
- Content validation and retry logic
- Research depth adjustment
- Quality threshold enforcement
- Comprehensive error logging

Author: TickZen Development Team
Version: 3.1
Last Updated: January 2026
"""

import json
import logging
import os
import sys
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Enhanced Search is DISABLED - not imported
# from Sports_Article_Automation.testing.test_enhanced_search_content import EnhancedSearchContentFetcher

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Import state manager for tracking publishing status
try:
    from .sports_publishing_state_manager import SportsPublishingStateManager
except ImportError:
    try:
        from sports_publishing_state_manager import SportsPublishingStateManager
    except ImportError:
        SportsPublishingStateManager = None

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
    file_handler = logging.FileHandler('article_generation_pipeline.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)


class ArticleGenerationPipeline:
    """
    Complete pipeline for generating articles from collected news headlines
    Two-stage process: Research Collection → Article Generation
    Integrated with publishing state management for tracking and history
    """
    
    def __init__(self, 
                 database_file: str = str(DATA_DIR / "sports_news_database.json"),
                 perplexity_client=None,
                 gemini_client=None,
                 enhanced_search_client=None,
                 state_manager: Optional[Any] = None,
                 profile_id: Optional[str] = None):
        """
        Initialize Article Generation Pipeline
        
        Args:
            database_file (str): Path to collected articles database
            perplexity_client: Configured Perplexity AI client for research
            gemini_client: Configured Gemini AI client for article writing
            enhanced_search_client: Optional Enhanced Search client for additional research
            state_manager: Optional state manager for tracking publishing status
            profile_id: Profile ID for state tracking
        """
        self.database_file = database_file
        self.perplexity_client = perplexity_client
        self.gemini_client = gemini_client
        # Enhanced Search is DISABLED - always None
        self.enhanced_search_client = None
        self.state_manager = state_manager or (SportsPublishingStateManager() if SportsPublishingStateManager else None)
        self.profile_id = profile_id
        self.generated_articles = []
        self.processing_stats = {
            'total_processed': 0,
            'research_collected': 0,
            'articles_generated': 0,
            'failed': 0,
            'total_content_length': 0
        }
        
        if self.state_manager:
            logging.info(f"Article Generation Pipeline initialized with state tracking (Profile: {profile_id})")
        
    def load_articles_from_database(self, 
                                   category: Optional[str] = None,
                                   limit: Optional[int] = None) -> List[Dict]:
        """
        Load articles from the collected news database
        
        Args:
            category (str): Optional category filter (cricket, football, basketball, uncategorized)
            limit (int): Maximum number of articles to load
            
        Returns:
            List[Dict]: List of articles from database
        """
        try:
            # Check if category-specific database exists (in root or data dir)
            if category:
                # Try root directory first (where categorization saves them)
                category_file = BASE_DIR / f"{category}_news_database.json"
                if not category_file.exists():
                    # Try data directory
                    category_file = DATA_DIR / f"{category}_news_database.json"
                
                if category_file.exists():
                    logging.info(f"📂 Loading {category} articles from {category_file}...")
                    with open(category_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        articles = data.get('articles', [])
                else:
                    logging.warning(f"⚠️  Category file not found: {category_file}")
                    articles = []
            else:
                # Load from main database
                main_file = Path(self.database_file)
                if main_file.exists():
                    logging.info(f"📂 Loading articles from {main_file}...")
                    with open(main_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        articles = data.get('articles', [])
                else:
                    logging.warning(f"⚠️  Database file not found: {main_file}")
                    articles = []
            
            if limit:
                articles = articles[:limit]
            
            logging.info(f"✅ Loaded {len(articles)} articles")
            return articles
            
        except Exception as e:
            logging.error(f"❌ Error loading articles: {e}")
            return []
    
    def select_headline_for_processing(self, articles: List[Dict], 
                                       selection_method: str = "top_importance") -> Optional[Dict]:
        """
        Select a single headline for article generation processing
        
        Args:
            articles (List[Dict]): List of available articles
            selection_method (str): Method for selection
                - 'top_importance': Select article with highest importance score
                - 'latest': Select most recently published article
                - 'hybrid': Select based on hybrid ranking
                - 'first': Select first article in list
                
        Returns:
            Dict: Selected article or None
        """
        if not articles:
            logging.warning("⚠️  No articles available for selection")
            return None
        
        try:
            if selection_method == "top_importance":
                # Select by highest importance score
                selected = max(articles, key=lambda x: x.get('importance_score', 0))
                logging.info(f"📍 Selected by importance score: {selected.get('importance_score', 0)}")
                
            elif selection_method == "latest":
                # Select by most recent (lowest hybrid_rank)
                selected = min(articles, key=lambda x: x.get('hybrid_rank', float('inf')))
                logging.info(f"📍 Selected by latest (rank {selected.get('hybrid_rank', 'N/A')})")
                
            elif selection_method == "hybrid":
                # Already sorted by hybrid rank, pick first
                selected = articles[0] if articles else None
                logging.info(f"📍 Selected by hybrid ranking (rank 1)")
                
            else:  # first
                selected = articles[0]
                logging.info(f"📍 Selected first article")
            
            if selected:
                logging.info(f"📰 Headline: {selected.get('title', 'No title')[:80]}...")
                logging.info(f"📊 Score: {selected.get('importance_score', 'N/A')}")
                logging.info(f"🏷️  Category: {selected.get('category', 'uncategorized')}")
            
            return selected
            
        except Exception as e:
            logging.error(f"❌ Error selecting headline: {e}")
            return None
    
    def generate_article_for_headline(self, article_entry: Dict) -> Dict:
        """
        Complete workflow to generate article from headline
        Steps:
        1. Collect research using Perplexity AI
        2. Generate article using Gemini AI
        
        Args:
            article_entry (Dict): Article entry from database
            
        Returns:
            Dict: Generated article with full content
        """
        if not self.perplexity_client or not self.gemini_client:
            logging.error("❌ Perplexity or Gemini client not configured")
            return {
                'status': 'error',
                'error': 'Clients not initialized',
                'article_entry': article_entry
            }
        
        try:
            headline = article_entry.get('title', '')
            source = article_entry.get('source_name', '')
            category = article_entry.get('category', '')
            
            logging.info(f"\n{'='*70}")
            logging.info(f"🎯 COMPLETE ARTICLE GENERATION WORKFLOW")
            logging.info(f"{'='*70}")
            logging.info(f"📰 Headline: {headline}")
            logging.info(f"📍 Source: {source}")
            logging.info(f"🏷️  Category: {category}")
            
            # Stage 1: Collect research from Perplexity AI ONLY
            logging.info(f"\n{'='*70}")
            logging.info(f"STAGE 1️⃣: PERPLEXITY AI RESEARCH COLLECTION (Enhanced Search DISABLED)")
            logging.info(f"{'='*70}")
            
            # Sub-stage 1A: Collect Intent-Based Perplexity research
            logging.info(f"\n🔍 Sub-stage 1A: Intent-Based Perplexity AI Research Collection")
            logging.info(f"-"*50)
            
            perplexity_research = None
            intent_analysis = None
            safety_level = "unknown"
            auto_publish_safe = False
            
            if self.perplexity_client:
                if hasattr(self.perplexity_client, 'collect_intent_based_research'):
                    logging.info("🎯 Using INTENT-BASED Perplexity research (journalistic safety optimized)...")
                    research_result = self.perplexity_client.collect_intent_based_research(
                        headline=headline,
                        source=source,
                        category=category
                    )
                    
                    if research_result and research_result.get('status') == 'success':
                        perplexity_research = research_result
                        
                        # Debug logging to see what we actually received
                        logging.info(f"📊 DEBUG: Research result keys: {list(research_result.keys())}")
                        if 'intent_classification' in research_result:
                            logging.info(f"📊 DEBUG: Intent classification found: {research_result['intent_classification']}")
                        else:
                            logging.info(f"📊 DEBUG: No intent_classification in research result")
                        
                        intent_classification = research_result.get('intent_classification', {})
                        intent_analysis = {
                            'intent_type': intent_classification.get('detected_intent', 'unknown'),
                            'safety_level': intent_classification.get('safety_level', 'unknown'),
                            'auto_publish_safe': intent_classification.get('auto_publish_recommended', False),
                            'confidence_score': 'N/A',
                            'matched_keywords': intent_classification.get('intent_details', {}).get('matched_keywords', []),
                            'priority': intent_classification.get('intent_details', {}).get('priority', 'medium'),
                            'manual_review_reason': 'Safety threshold not met' if not intent_classification.get('auto_publish_recommended', False) else None
                        }
                        safety_level = intent_analysis.get('safety_level', 'unknown')
                        auto_publish_safe = intent_analysis.get('auto_publish_safe', False)
                        
                        logging.info(f"\n🎯 INTENT ANALYSIS RESULTS:")
                        logging.info(f"   🔍 Intent Type: {intent_analysis.get('intent_type', 'unknown')}")
                        logging.info(f"   🛡️ Safety Level: {safety_level}")
                        logging.info(f"   🤖 Auto-publish recommended: {'✅ YES' if auto_publish_safe else '❌ MANUAL REVIEW REQUIRED'}")
                        logging.info(f"   📊 Confidence: {intent_analysis.get('confidence_score', 'N/A')}")
                        logging.info(f"   🏷️ Keywords: {', '.join(intent_analysis.get('matched_keywords', []))}") 
                        
                        # Log safety gate decision
                        if not auto_publish_safe:
                            logging.warning(f"⚠️ SAFETY GATE: Article flagged for manual review")
                            logging.warning(f"   Reason: {intent_analysis.get('manual_review_reason', 'Safety threshold not met')}")
                        else:
                            logging.info(f"✅ SAFETY GATE: Article approved for auto-publishing")
                            
                    else:
                        logging.warning("⚠️ Intent-based research failed, attempting fallback...")
                        # Fallback to old research method if available
                        if hasattr(self.perplexity_client, 'collect_enhanced_research_for_headline'):
                            logging.info("📡 Using enhanced research fallback...")
                            perplexity_research = self.perplexity_client.collect_enhanced_research_for_headline(
                                headline=headline, source=source, category=category
                            )
                        elif hasattr(self.perplexity_client, 'collect_research_for_headline'):
                            logging.info("📡 Using standard research fallback...")
                            perplexity_research = self.perplexity_client.collect_research_for_headline(
                                headline=headline, source=source, category=category
                            )
                else:
                    logging.warning("⚠️ Intent-based research not available, using legacy method...")
                    if hasattr(self.perplexity_client, 'collect_enhanced_research_for_headline'):
                        logging.info("📡 Using enhanced research collection...")
                        perplexity_research = self.perplexity_client.collect_enhanced_research_for_headline(
                            headline=headline, source=source, category=category
                        )
                    else:
                        logging.info("📡 Using standard research collection...")
                        perplexity_research = self.perplexity_client.collect_research_for_headline(
                            headline=headline, source=source, category=category
                        )
            else:
                logging.warning("⚠️ Perplexity client not available")
            
            # Log Intent-Based research content size and save to file
            if perplexity_research and perplexity_research.get('status') in ['success', 'placeholder']:
                perplexity_content_length = 0
                perplexity_content = ""
                
                # Handle both intent-based and legacy research formats
                if 'research_content' in perplexity_research:
                    # New intent-based research format - research_content is already a string
                    perplexity_content = perplexity_research.get('research_content', '')
                    perplexity_content_length = len(perplexity_content)
                elif 'research_sections' in perplexity_research:
                    # Legacy research format
                    comprehensive = perplexity_research['research_sections'].get('comprehensive', {})
                    perplexity_content = comprehensive.get('content', '')
                    perplexity_content_length = len(perplexity_content)
                
                # Use correct field names for intent-based research
                if 'sources' in perplexity_research and 'citations' in perplexity_research:
                    perplexity_sources_count = len(perplexity_research.get('sources', []))
                    perplexity_citations_count = len(perplexity_research.get('citations', []))
                else:
                    # Fallback to legacy field names
                    perplexity_sources_count = len(perplexity_research.get('compiled_sources', []))
                    perplexity_citations_count = len(perplexity_research.get('compiled_citations', []))
                
                logging.info(f"\n📊 INTENT-BASED RESEARCH SIZE:")
                logging.info(f"   📄 Content length: {perplexity_content_length:,} characters")
                logging.info(f"   📚 Sources: {perplexity_sources_count}")
                logging.info(f"   🔗 Citations: {perplexity_citations_count}")
                
                # Save Intent-Based research to file (includes safety analysis)
                if perplexity_content:
                    # Get sources and citations using correct field names
                    sources = perplexity_research.get('sources', perplexity_research.get('compiled_sources', []))
                    citations = perplexity_research.get('citations', perplexity_research.get('compiled_citations', []))
                    
                    saved_file = self._save_intent_based_research(
                        headline=headline,
                        research_content=perplexity_content,
                        sources=sources,
                        citations=citations,
                        intent_analysis=intent_analysis,
                        safety_level=safety_level,
                        auto_publish_safe=auto_publish_safe
                    )
                    if saved_file:
                        logging.info(f"   💾 Research saved to: {saved_file}")
                        if intent_analysis:
                            logging.info(f"   🎯 Intent analysis included for manual review")
            
            # Enhanced Search is DISABLED - skipping completely
            logging.info(f"\n⚠️ Enhanced Search: DISABLED (Not used in pipeline)")
            enhanced_search_research = None
            
            # Sub-stage 1C: Process Perplexity research only
            logging.info(f"\n🔗 Sub-stage 1C: Combining Research Sources")
            logging.info(f"-"*50)
            
            combined_research = self._combine_research_sources(
                perplexity_research=perplexity_research,
                enhanced_search_research=enhanced_search_research,
                headline=headline,
                source=source,
                category=category
            )
            
            self.processing_stats['research_collected'] += 1
            
            if combined_research.get('status') not in ['success', 'partial_success', 'placeholder']:
                logging.error(f"❌ Research collection failed completely")
                self.processing_stats['failed'] += 1
                return {
                    'status': 'error',
                    'error': 'Research collection failed from all sources',
                    'article_entry': article_entry
                }
            
            research_data = combined_research
            
            # Log final research data being sent to Gemini
            gemini_input_content_length = 0
            if 'research_sections' in research_data:
                comprehensive = research_data['research_sections'].get('comprehensive', {})
                gemini_input_content_length = len(comprehensive.get('content', ''))
            
            logging.info(f"\n📊 FINAL RESEARCH DATA FOR GEMINI:")
            logging.info(f"   📄 Total content length: {gemini_input_content_length:,} characters")
            logging.info(f"   📚 Total sources: {len(research_data.get('compiled_sources', []))}")
            logging.info(f"   🔗 Total citations: {len(research_data.get('compiled_citations', []))}")
            logging.info(f"   ✅ Research method: {research_data.get('research_method', 'unknown')}")
            logging.info(f"   🎯 Sources used: {', '.join(research_data.get('sources_used', []))}")
            
            # Stage 2: Generate article from research
            logging.info(f"\n{'='*70}")
            logging.info(f"STAGE 2️⃣: ARTICLE GENERATION (Gemini AI)")
            logging.info(f"{'='*70}")
            
            # Prepare research context for Gemini
            research_context = {
                'article_headline': headline,
                'article_source': source,
                'article_category': category,
                'article_url': article_entry.get('url', ''),
                'published_date': article_entry.get('published_date', ''),
                'importance_score': article_entry.get('importance_score', 0),
                'research_data': research_data
            }
            
            # Generate article using Gemini with sports-specific prompt
            article = self.gemini_client.generate_article_from_research(research_context)
            
            self.processing_stats['total_processed'] += 1
            
            if article.get('status') in ['success', 'placeholder']:
                self.processing_stats['articles_generated'] += 1
                self.processing_stats['total_content_length'] += len(
                    article.get('article_content', '')
                )
            else:
                self.processing_stats['failed'] += 1
            
            # Enhance with original metadata
            article['workflow_metadata'] = {
                'original_title': headline,
                'original_source': source,
                'published_date': article_entry.get('published_date'),
                'article_url': article_entry.get('url'),
                'importance_score': article_entry.get('importance_score'),
                'category': category,
                'hybrid_rank': article_entry.get('hybrid_rank'),
                'time_bracket': article_entry.get('time_bracket')
            }
            
            logging.info(f"\n✅ Complete workflow successful!")
            
            return article
            
        except Exception as e:
            logging.error(f"❌ Error in article generation workflow: {e}")
            self.processing_stats['failed'] += 1
            return {
                'status': 'error',
                'error': str(e),
                'article_entry': article_entry
            }
    
    def _save_perplexity_research(self, headline: str, research_content: str, 
                                   sources: List[str], citations: List) -> Optional[str]:
        """
        Save Perplexity research content to a text file
        
        Args:
            headline (str): Article headline
            research_content (str): Research content from Perplexity
            sources (List[str]): List of source URLs
            citations (List): List of citations
            
        Returns:
            str: Path to saved file or None if failed
        """
        try:
            # Create directory for research data
            research_dir = BASE_DIR / "perplexity_researched_data"
            research_dir.mkdir(exist_ok=True)
            
            # Generate safe filename from headline
            safe_filename = "".join(c for c in headline if c.isalnum() or c in (' ', '-', '_'))[:50]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_filename}_{timestamp}.txt"
            
            filepath = research_dir / filename
            
            # Format the research content with metadata
            content_lines = []
            content_lines.append("="*70)
            content_lines.append("PERPLEXITY AI RESEARCH DATA")
            content_lines.append("="*70)
            content_lines.append(f"Headline: {headline}")
            content_lines.append(f"Collected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content_lines.append(f"Content Length: {len(research_content)} characters")
            content_lines.append(f"Sources: {len(sources)}")
            content_lines.append(f"Citations: {len(citations)}")
            content_lines.append("="*70)
            content_lines.append("")
            content_lines.append("RESEARCH CONTENT:")
            content_lines.append("-"*70)
            content_lines.append(research_content)
            content_lines.append("")
            content_lines.append("="*70)
            content_lines.append("SOURCES:")
            content_lines.append("-"*70)
            for idx, source in enumerate(sources, 1):
                content_lines.append(f"{idx}. {source}")
            content_lines.append("")
            content_lines.append("="*70)
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content_lines))
            
            logging.info(f"💾 Perplexity research saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logging.error(f"❌ Error saving Perplexity research: {e}")
            return None
    
    def _save_intent_based_research(self, headline: str, research_content: str, 
                                   sources: List[str], citations: List, 
                                   intent_analysis: Dict, safety_level: str,
                                   auto_publish_safe: bool) -> Optional[str]:
        """
        Save Intent-Based research content to a text file with safety analysis
        
        Args:
            headline (str): Article headline
            research_content (str): Research content from Perplexity
            sources (List[str]): List of source URLs
            citations (List): List of citations
            intent_analysis (Dict): Intent detection and analysis data
            safety_level (str): Safety level (high/medium/low)
            auto_publish_safe (bool): Whether auto-publishing is recommended
            
        Returns:
            str: Path to saved file or None if failed
        """
        try:
            # Create directory for research data (same as legacy for consistency)
            research_dir = BASE_DIR / "perplexity_researched_data"
            research_dir.mkdir(exist_ok=True)
            
            # Generate safe filename from headline
            safe_filename = "".join(c for c in headline if c.isalnum() or c in (' ', '-', '_'))[:50]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_filename}_{timestamp}_INTENT.txt"
            
            filepath = research_dir / filename
            
            # Format the research content with intent analysis metadata
            content_lines = []
            content_lines.append("="*80)
            content_lines.append("INTENT-BASED PERPLEXITY AI RESEARCH DATA")
            content_lines.append("="*80)
            content_lines.append(f"Headline: {headline}")
            content_lines.append(f"Collected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content_lines.append(f"Content Length: {len(research_content)} characters")
            content_lines.append(f"Sources: {len(sources)}")
            content_lines.append(f"Citations: {len(citations)}")
            content_lines.append("")
            
            # Intent Analysis Section
            content_lines.append("="*80)
            content_lines.append("🎯 INTENT ANALYSIS & SAFETY ASSESSMENT")
            content_lines.append("="*80)
            content_lines.append(f"Intent Type: {str(intent_analysis.get('intent_type', 'unknown'))}")
            content_lines.append(f"Safety Level: {str(safety_level)}")
            content_lines.append(f"Auto-publish Safe: {'✅ YES' if auto_publish_safe else '❌ MANUAL REVIEW REQUIRED'}")
            content_lines.append(f"Confidence Score: {str(intent_analysis.get('confidence_score', 'N/A'))}")
            
            # Safely handle matched_keywords list
            matched_keywords = intent_analysis.get('matched_keywords', [])
            if isinstance(matched_keywords, list):
                keywords_str = ', '.join(str(kw) for kw in matched_keywords)
            else:
                keywords_str = str(matched_keywords)
            content_lines.append(f"Matched Keywords: {keywords_str}")
            content_lines.append(f"Priority Level: {str(intent_analysis.get('priority', 'medium'))}")
            
            if not auto_publish_safe:
                reason = intent_analysis.get('manual_review_reason', 'Safety threshold not met')
                content_lines.append(f"Manual Review Reason: {str(reason)}")
                
            # Source Tier Analysis if available
            if 'source_tier' in intent_analysis:
                content_lines.append(f"Source Tier: {str(intent_analysis.get('source_tier', 'unknown'))}")
                content_lines.append(f"Source Credibility: {str(intent_analysis.get('source_credibility', 'unknown'))}")
            
            content_lines.append("")
            content_lines.append("="*80)
            content_lines.append("📄 RESEARCH CONTENT:")
            content_lines.append("-"*80)
            # Ensure research_content is a string
            content_lines.append(str(research_content))
            content_lines.append("")
            content_lines.append("="*80)
            content_lines.append("📚 SOURCES:")
            content_lines.append("-"*80)
            for idx, source in enumerate(sources, 1):
                # Ensure source is a string
                if isinstance(source, dict):
                    source_str = source.get('title', source.get('url', source.get('name', str(source))))
                else:
                    source_str = str(source)
                content_lines.append(f"{idx}. {source_str}")
            content_lines.append("")
            
            # Citations section
            if citations:
                content_lines.append("="*80)
                content_lines.append("🔗 CITATIONS:")
                content_lines.append("-"*80)
                for idx, citation in enumerate(citations, 1):
                    # Ensure citation is a string
                    if isinstance(citation, dict):
                        citation_str = citation.get('title', citation.get('url', citation.get('text', str(citation))))
                    else:
                        citation_str = str(citation)
                    content_lines.append(f"{idx}. {citation_str}")
                content_lines.append("")
            
            content_lines.append("="*80)
            content_lines.append("🤖 AUTOMATION DECISION TREE:")
            content_lines.append("-"*80)
            if auto_publish_safe:
                content_lines.append("✅ APPROVED FOR AUTO-PUBLISHING")
                content_lines.append(f"   Reason: {safety_level.title()} safety level article type")
                content_lines.append("   Action: Can proceed with automated article generation")
            else:
                content_lines.append("❌ FLAGGED FOR MANUAL REVIEW")
                content_lines.append(f"   Reason: {intent_analysis.get('manual_review_reason', 'Safety concerns')}")
                content_lines.append("   Action: Human review required before publishing")
            content_lines.append("="*80)
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content_lines))
            
            logging.info(f"💾 Intent-based research saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logging.error(f"❌ Error saving intent-based research: {e}")
            return None

    def save_generated_article(self, article_data: Dict, 
                              output_dir: str = "outputs/articles") -> Optional[str]:
        """
        Save generated article to JSON, plus HTML and PDF versions
        
        Args:
            article_data (Dict): Generated article data
            output_dir (str): Directory to save articles
            
        Returns:
            str: Path to saved JSON file or None if failed
        """
        try:
            # Create output directory if needed
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename from headline
            headline = article_data.get('headline', 'article')
            safe_filename = "".join(c for c in headline if c.isalnum() or c in (' ', '-', '_'))[:50]
            filename = f"{safe_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"✅ Article saved to: {filepath}")

            # Also save HTML and PDF versions for publication
            html_path = self._save_article_html(article_data, output_dir, safe_filename)
            pdf_path = self._save_article_pdf(article_data, output_dir, safe_filename, html_path)
            if html_path:
                logging.info(f"✅ HTML version saved to: {html_path}")
            if pdf_path:
                logging.info(f"✅ PDF version saved to: {pdf_path}")
            return filepath
            
        except Exception as e:
            logging.error(f"❌ Error saving article: {e}")
            return None

    def _markdown_to_html(self, markdown_text: str) -> str:
        """Very light markdown to HTML converter for headings, bold, italics, and links."""
        html = markdown_text
        # Headings
        html = re.sub(r"^### (.*)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.*)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.*)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        # Bold and italics
        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)
        # Links [text](url)
        html = re.sub(r"\[(.*?)\]\((.*?)\)", r"<a href='\2' target='_blank'>\1</a>", html)
        # Paragraphs
        html = "".join(f"<p>{line.strip()}</p>" if line.strip() and not line.strip().startswith("<h") else f"{line}\n" for line in html.split('\n'))
        return html

    def _save_article_html(self, article_data: Dict, output_dir: str, safe_filename: str) -> Optional[str]:
        """Render SEO-optimized HTML file for the article."""
        try:
            html_dir = os.path.join(output_dir, "html")
            os.makedirs(html_dir, exist_ok=True)

            seo = article_data.get('seo_metadata', {})
            meta_description = seo.get('meta_description', '')
            keywords = ", ".join(seo.get('keywords', []))
            title = seo.get('title', article_data.get('headline', 'Article'))
            body_html = self._markdown_to_html(article_data.get('article_content', ''))
            sources = article_data.get('sources', [])

            html_template = f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>{title}</title>
  <meta name='description' content="{meta_description}">
  <meta name='keywords' content="{keywords}">
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background:#f7f8fa; color:#1f2933; }}
    .page {{ max-width: 860px; margin: 0 auto; padding: 40px 24px 80px; background: #fff; box-shadow:0 8px 24px rgba(15,23,42,0.06); }}
    h1 {{ font-size: 30px; margin-bottom: 12px; color:#0f172a; }}
    h2 {{ font-size: 22px; margin-top: 28px; color:#111827; }}
    h3 {{ font-size: 18px; margin-top: 20px; color:#111827; }}
    p {{ line-height: 1.7; margin: 10px 0; font-size: 15px; }}
    strong {{ color:#0f172a; }}
    a {{ color:#2563eb; text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    .meta {{ color:#6b7280; font-size: 13px; margin-bottom: 24px; }}
    .badge {{ display:inline-block; padding:4px 10px; border-radius:999px; background:#e0f2fe; color:#0ea5e9; font-weight:600; font-size:12px; margin-right:8px; }}
    .sources {{ margin-top:32px; padding:16px; background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px; }}
    .sources h4 {{ margin:0 0 8px 0; font-size:14px; color:#111827; }}
    .sources ul {{ margin:0; padding-left:16px; }}
    .sources li {{ margin:4px 0; font-size:13px; }}
  </style>
</head>
<body>
  <main class='page'>
    <div class='meta'>
      <span class='badge'>{article_data.get('category','General').title()}</span>
      <span>{article_data.get('generated_at','')}</span>
    </div>
    <h1>{article_data.get('headline','')}</h1>
    {body_html}
    <div class='sources'>
      <h4>Sources</h4>
      <ul>
        {''.join(f"<li><a href='{s}' target='_blank'>{s}</a></li>" for s in sources)}
      </ul>
    </div>
  </main>
</body>
</html>"""

            html_path = os.path.join(html_dir, f"{safe_filename}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            return html_path
        except Exception as e:
            logging.warning(f"⚠️  Could not save HTML version: {e}")
            return None

    def _save_article_pdf(self, article_data: Dict, output_dir: str, safe_filename: str, html_path: Optional[str]) -> Optional[str]:
        """Save PDF version if fpdf is available; otherwise skip gracefully."""
        try:
            try:
                from fpdf import FPDF
            except ImportError:
                logging.warning("⚠️  PDF export skipped (fpdf not installed). Install with: pip install fpdf2")
                return None

            pdf_dir = os.path.join(output_dir, "pdf")
            os.makedirs(pdf_dir, exist_ok=True)

            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", "B", 16)
            pdf.multi_cell(0, 10, article_data.get('headline', ''))

            pdf.set_font("Arial", "", 11)
            pdf.ln(4)
            pdf.multi_cell(0, 6, f"Category: {article_data.get('category','')}")
            pdf.multi_cell(0, 6, f"Generated: {article_data.get('generated_at','')}")
            pdf.ln(6)

            # Content (strip markdown for PDF readability)
            content_plain = re.sub(r"[#*_`]", "", article_data.get('article_content',''))
            pdf.multi_cell(0, 6, content_plain)

            # Sources
            sources = article_data.get('sources', [])
            if sources:
                pdf.ln(4)
                pdf.set_font("Arial", "B", 12)
                pdf.multi_cell(0, 8, "Sources")
                pdf.set_font("Arial", "", 11)
                for s in sources:
                    pdf.multi_cell(0, 6, s)

            pdf_path = os.path.join(pdf_dir, f"{safe_filename}.pdf")
            pdf.output(pdf_path)
            return pdf_path
        except Exception as e:
            logging.warning(f"⚠️  Could not save PDF version: {e}")
            return None
    
    def _combine_research_sources(self,
                                perplexity_research: Optional[Dict],
                                enhanced_search_research: Optional[Dict],
                                headline: str,
                                source: str,
                                category: str) -> Dict:
        """
        Combine research from both Perplexity and Enhanced Search sources
        
        Args:
            perplexity_research: Research from Perplexity AI
            enhanced_search_research: Research from Enhanced Search with full article content
            headline: Article headline
            source: Article source
            category: Article category
            
        Returns:
            Dict: Combined research data ready for article generation
        """
        logging.info(f"🔗 Combining research from multiple sources...")
        
        # Start with base structure
        combined_research = {
            'headline': headline,
            'source': source,
            'category': category,
            'collection_timestamp': datetime.now().isoformat(),
            'status': 'success',
            'research_method': 'perplexity_only',  # Changed from hybrid
            'sources_used': []
        }
        
        # Collect all sources and content
        all_sources = []
        all_citations = []
        combined_content_parts = []
        
        # Process Perplexity research
        if perplexity_research and perplexity_research.get('status') in ['success', 'placeholder']:
            logging.info("✅ Including Perplexity AI research")
            combined_research['sources_used'].append('Perplexity AI')
            
            # Extract Perplexity content (support both intent-based and legacy formats)
            perplexity_content = ""
            if 'research_content' in perplexity_research:
                # New intent-based format
                perplexity_content = perplexity_research.get('research_content', '')
            elif 'research_sections' in perplexity_research:
                # Legacy format
                comprehensive_section = perplexity_research['research_sections'].get('comprehensive', {})
                perplexity_content = comprehensive_section.get('content', '')
            
            if perplexity_content:
                combined_content_parts.append("RESEARCH FROM PERPLEXITY AI:")
                combined_content_parts.append("-" * 50)
                combined_content_parts.append(perplexity_content)
                combined_content_parts.append("")
            
            # Collect Perplexity sources and citations (support both formats)
            if 'sources' in perplexity_research and 'citations' in perplexity_research:
                # New intent-based format
                perplexity_sources = perplexity_research.get('sources', [])
                perplexity_citations = perplexity_research.get('citations', [])
            else:
                # Legacy format
                perplexity_sources = perplexity_research.get('compiled_sources', [])
                perplexity_citations = perplexity_research.get('compiled_citations', [])
            
            all_sources.extend(perplexity_sources)
            all_citations.extend(perplexity_citations)
            
        else:
            logging.warning("⚠️ Perplexity research not available or failed")
        
        # Enhanced Search is DISABLED - this block is now inactive
        # Enhanced Search research will always be None
        if enhanced_search_research:
            # This should never execute since enhanced_search_research is always None
            logging.warning("⚠️ Enhanced Search was unexpectedly provided - ignoring it")
        else:
            logging.info("ℹ️ Enhanced Search: DISABLED (using Perplexity only)")
        
        # Determine final status (Perplexity-only approach)
        if not combined_content_parts:
            # No research available
            combined_research['status'] = 'error'
            combined_research['error'] = 'No research data available from Perplexity'
            logging.error("❌ No research content available from Perplexity")
        else:
            # Success - Perplexity research available
            combined_research['status'] = 'success'
            logging.info(f"✅ Research collection successful using Perplexity only")
        
        # Combine all content
        if combined_content_parts:
            full_combined_content = "\\n".join(combined_content_parts)
            
            # Safely deduplicate sources and citations
            unique_sources = []
            unique_citations = []
            
            # Convert sources to strings and deduplicate
            seen_sources = set()
            for source in all_sources:
                if isinstance(source, dict):
                    source_str = source.get('title', source.get('url', source.get('name', str(source))))
                else:
                    source_str = str(source)
                if source_str not in seen_sources:
                    seen_sources.add(source_str)
                    unique_sources.append(source_str)
            
            # Convert citations to strings and deduplicate
            seen_citations = set()
            for citation in all_citations:
                if isinstance(citation, dict):
                    citation_str = citation.get('title', citation.get('url', citation.get('text', str(citation))))
                else:
                    citation_str = str(citation)
                if citation_str not in seen_citations:
                    seen_citations.add(citation_str)
                    unique_citations.append(citation_str)
            
            combined_research['research_sections'] = {
                'comprehensive': {
                    'content': full_combined_content,
                    'sources': unique_sources,
                    'citations': unique_citations
                }
            }
        else:
            # Fallback empty content
            combined_research['research_sections'] = {
                'comprehensive': {
                    'content': f"Limited research available for: {headline}",
                    'sources': [],
                    'citations': []
                }
            }
        
        # Set compiled sources and citations for compatibility
        if 'research_sections' in combined_research:
            combined_research['compiled_sources'] = combined_research['research_sections']['comprehensive']['sources']
            combined_research['compiled_citations'] = combined_research['research_sections']['comprehensive']['citations']
        else:
            combined_research['compiled_sources'] = []
            combined_research['compiled_citations'] = []
        
        # Add statistics
        combined_research['statistics'] = {
            'total_sources': len(combined_research['compiled_sources']),
            'total_citations': len(combined_research['compiled_citations']),
            'content_length': len(combined_research['research_sections']['comprehensive']['content']),
            'perplexity_available': bool(perplexity_research and perplexity_research.get('status') in ['success', 'placeholder']),
            'enhanced_search_available': bool(enhanced_search_research and enhanced_search_research.get('status') == 'success')
        }
        
        logging.info(f"📊 Combined research statistics:")
        logging.info(f"   📚 Total sources: {combined_research['statistics']['total_sources']}")
        logging.info(f"   🔗 Total citations: {combined_research['statistics']['total_citations']}")
        logging.info(f"   📄 Content length: {combined_research['statistics']['content_length']} characters")
        logging.info(f"   ✅ Sources used: {', '.join(combined_research['sources_used'])}")
        
        return combined_research
    
    def generate_article_batch(self, 
                              category: Optional[str] = None,
                              selection_method: str = "top_importance",
                              num_articles: int = 1,
                              save_articles: bool = True) -> List[Dict]:
        """
        Generate articles for a batch of headlines
        
        Args:
            category (str): Optional category filter
            selection_method (str): Method for selecting which articles to process
            num_articles (int): Number of articles to generate
            save_articles (bool): Whether to save generated articles to files
            
        Returns:
            List[Dict]: List of generated articles
        """
        try:
            logging.info(f"\n{'='*70}")
            logging.info(f"🚀 STARTING ARTICLE GENERATION BATCH PROCESS")
            logging.info(f"{'='*70}")
            logging.info(f"📂 Category: {category or 'All'}")
            logging.info(f"🎯 Selection Method: {selection_method}")
            logging.info(f"📊 Articles to Generate: {num_articles}")
            
            # Load articles
            articles = self.load_articles_from_database(category=category)
            
            if not articles:
                logging.error("❌ No articles available to process")
                return []
            
            # Process articles
            for i in range(min(num_articles, len(articles))):
                logging.info(f"\n[{i+1}/{min(num_articles, len(articles))}] Processing article...")
                
                # Select article
                selected = self.select_headline_for_processing([articles[i]], selection_method)
                
                if not selected:
                    continue
                
                # Generate article
                generated = self.generate_article_for_headline(selected)
                
                if generated:
                    self.generated_articles.append(generated)
                    
                    # Save article if requested
                    if save_articles:
                        self.save_generated_article(generated)
            
            # Print summary
            self._print_summary()
            
            return self.generated_articles
            
        except Exception as e:
            logging.error(f"❌ Error in batch generation: {e}")
            return self.generated_articles
    
    def generate_and_publish_to_wordpress(self,
                                          category: Optional[str] = None,
                                          num_articles: int = 1,
                                          wp_publisher=None) -> List[Dict]:
        """
        Complete workflow: Generate articles AND publish to WordPress
        
        Args:
            category (str): Category filter
            num_articles (int): Number of articles to publish
            wp_publisher: SportsWordPressPublisher instance
            
        Returns:
            List[Dict]: Publishing results
        """
        try:
            if not wp_publisher:
                logging.error("❌ WordPress publisher not provided")
                return []
            
            logging.info(f"\n{'='*70}")
            logging.info(f"🚀 GENERATE AND PUBLISH WORKFLOW")
            logging.info(f"{'='*70}")
            
            # Load articles
            articles = self.load_articles_from_database(category=category, limit=num_articles * 2)
            
            if not articles:
                logging.error("❌ No articles to process")
                return []
            
            from datetime import timedelta, timezone
            import random
            
            schedule_time = datetime.now(timezone.utc) + timedelta(minutes=15)
            published_results = []
            
            for i in range(min(num_articles, len(articles))):
                logging.info(f"\n[{i+1}/{num_articles}] Processing and publishing...")
                
                # Select article
                selected = self.select_headline_for_processing([articles[i]], "top_importance")
                if not selected:
                    continue
                
                # Generate article (Perplexity research + Gemini writing)
                generated = self.generate_article_for_headline(selected)
                
                if generated.get('status') not in ['success', 'placeholder']:
                    logging.warning("⚠️  Generation failed, skipping...")
                    continue
                
                # Publish to WordPress
                post_id = wp_publisher.publish_article_to_wordpress(
                    article_data=generated,
                    schedule_time=schedule_time,
                    status="future"
                )
                
                if post_id:
                    published_results.append({
                        'post_id': post_id,
                        'title': generated.get('headline'),
                        'category': generated.get('category'),
                        'scheduled_time': schedule_time.isoformat()
                    })
                    
                    # Increment schedule for next post
                    schedule_time += timedelta(minutes=random.randint(45, 90))
            
            # Print summaries
            self._print_summary()
            wp_publisher.print_publishing_stats()
            
            return published_results
            
        except Exception as e:
            logging.error(f"❌ Error in publish workflow: {e}")
            return []
    
    def _print_summary(self):
        """Print processing summary"""
        logging.info(f"\n{'='*70}")
        logging.info(f"✅ BATCH PROCESSING COMPLETE")
        logging.info(f"{'='*70}")
        logging.info(f"📊 Statistics:")
        logging.info(f"   • Total Processed: {self.processing_stats['total_processed']}")
        logging.info(f"   • Research Collected: {self.processing_stats['research_collected']}")
        logging.info(f"   • Articles Generated: {self.processing_stats['articles_generated']}")
        logging.info(f"   • Failed: {self.processing_stats['failed']}")
        logging.info(f"   • Total Content: {self.processing_stats['total_content_length']} characters")
        
        if self.processing_stats['articles_generated'] > 0:
            avg_length = self.processing_stats['total_content_length'] / self.processing_stats['articles_generated']
            logging.info(f"   • Avg Content Per Article: {int(avg_length)} characters")


def demonstrate_pipeline(perplexity_client, gemini_client):
    """
    Demonstrate the complete research-to-article workflow
    
    Args:
        perplexity_client: Configured Perplexity AI client
        gemini_client: Configured Gemini AI client
    """
    logging.info("\n" + "="*70)
    logging.info("ARTICLE GENERATION PIPELINE - DEMONSTRATION")
    logging.info("="*70)
    
    # Initialize pipeline
    pipeline = ArticleGenerationPipeline(
        database_file="sports_news_database.json",
        perplexity_client=perplexity_client,
        gemini_client=gemini_client
    )
    
    # Example: Generate article from headline
    logging.info("\n📋 WORKFLOW EXAMPLE: Complete article generation")
    logging.info("-" * 70)
    
    articles = pipeline.load_articles_from_database(limit=5)
    if articles:
        selected = pipeline.select_headline_for_processing(articles, "top_importance")
        if selected:
            article = pipeline.generate_article_for_headline(selected)
            filepath = pipeline.save_generated_article(article)
            if filepath:
                logging.info(f"✅ Article generated and saved: {filepath}")


def demonstrate_pipeline(perplexity_client):
    """
    Demonstrate the complete article generation pipeline
    
    Args:
        perplexity_client: Configured Perplexity AI client
    """
    logging.info("\n" + "="*70)
    logging.info("ARTICLE GENERATION PIPELINE - DEMONSTRATION")
    logging.info("="*70)
    
    # Initialize pipeline
    pipeline = ArticleGenerationPipeline(
        database_file="sports_news_database.json",
        perplexity_client=perplexity_client
    )
    
    # Example 1: Generate article from top importance
    logging.info("\n📋 EXAMPLE 1: Generate article from top importance headline")
    logging.info("-" * 70)
    
    articles = pipeline.load_articles_from_database(limit=10)
    if articles:
        selected = pipeline.select_headline_for_processing(articles, "top_importance")
        if selected:
            article = pipeline.generate_article_for_headline(selected)
            pipeline.save_generated_article(article)
    
    # Example 2: Generate articles by category
    logging.info("\n📋 EXAMPLE 2: Generate cricket article")
    logging.info("-" * 70)
    
    cricket_articles = pipeline.load_articles_from_database(category="cricket", limit=5)
    if cricket_articles:
        selected = pipeline.select_headline_for_processing(cricket_articles, "hybrid")
        if selected:
            article = pipeline.generate_article_for_headline(selected)
            pipeline.save_generated_article(article)


if __name__ == "__main__":
    from Sports_Article_Automation.utilities.perplexity_ai_client import PerplexityAIClient
    
    # Initialize Perplexity client
    perplexity_client = PerplexityAIClient()
    
    # Run demonstration
    demonstrate_pipeline(perplexity_client)
