"""
Google Trends Article Generation Pipeline
========================================

This pipeline takes Google Trends keywords and generates high-quality sports articles by:
1. Loading trending keywords from Google Trends database
2. Using enhanced search to gather comprehensive information about each trend
3. Generating human-like articles using Gemini AI with the existing sports journalist prompt
4. Storing and managing generated articles

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
import traceback

# Add parent directories to path for imports
current_dir = Path(__file__).parent
sports_automation_dir = current_dir.parent
project_root = sports_automation_dir.parent
sys.path.extend([str(sports_automation_dir), str(project_root)])

# Import our components
from testing.test_enhanced_search_content import EnhancedSearchContentFetcher
from utilities.sports_article_generator import SportsArticleGenerator
from utilities.perplexity_ai_client import PerplexityResearchCollector
from core.article_generation_pipeline import ArticleGenerationPipeline

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GoogleTrendsDataLoader:
    """Load and process Google Trends data for article generation"""
    
    def __init__(self, database_path: Optional[str] = None):
        """Initialize the Google Trends data loader"""
        if database_path:
            self.database_path = Path(database_path)
        else:
            # Default to the google_trends_database.json in the same directory
            self.database_path = current_dir / "google_trends_database.json"
        
        self.generated_articles_path = current_dir / "generated_trends_articles.json"
        
        logger.info(f"Google Trends database: {self.database_path}")
        logger.info(f"Generated articles tracking: {self.generated_articles_path}")
    
    def load_trends_data(self) -> List[Dict]:
        """Load trends data from JSON file"""
        try:
            if not self.database_path.exists():
                logger.error(f"Trends database not found: {self.database_path}")
                return []
            
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            trends = data.get('trends', [])
            logger.info(f"Loaded {len(trends)} trends from database")
            return trends
        
        except Exception as e:
            logger.error(f"Error loading trends data: {e}")
            return []
    
    def get_generated_articles_history(self) -> List[Dict]:
        """Get history of previously generated articles"""
        try:
            if not self.generated_articles_path.exists():
                return []
            
            with open(self.generated_articles_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('generated_articles', [])
        
        except Exception as e:
            logger.warning(f"Could not load generated articles history: {e}")
            return []
    
    def save_generated_article(self, trend_query: str, article_data: Dict):
        """Save generated article to history"""
        try:
            # Load existing data
            if self.generated_articles_path.exists():
                with open(self.generated_articles_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'generated_articles': []}
            
            # Add new article
            article_record = {
                'trend_query': trend_query,
                'generated_at': datetime.now().isoformat(),
                'headline': article_data.get('headline', ''),
                'word_count': article_data.get('word_count', 0),
                'status': article_data.get('status', 'unknown'),
                'file_path': article_data.get('file_path', ''),
                'sources_used': len(article_data.get('sources', [])),
                'importance_score': article_data.get('importance_score', 0)
            }
            
            data['generated_articles'].append(article_record)
            
            # Save back to file
            with open(self.generated_articles_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved article record for trend: {trend_query}")
        
        except Exception as e:
            logger.error(f"Error saving generated article record: {e}")
    
    def filter_trends_for_generation(self, 
                                   trends: List[Dict], 
                                   max_articles: int = 5,
                                   min_importance_score: int = 40,
                                   exclude_already_generated: bool = True,
                                   max_age_days: int = 7) -> List[Dict]:
        """
        Filter and select trends for article generation
        
        Args:
            trends: List of trend data
            max_articles: Maximum number of articles to generate
            min_importance_score: Minimum importance score to consider
            exclude_already_generated: Skip trends we've already generated articles for
            max_age_days: Skip trends older than this many days
            
        Returns:
            List of selected trends for generation
        """
        logger.info(f"Filtering trends for generation...")
        
        # Get already generated trends if excluding
        generated_queries = set()
        if exclude_already_generated:
            generated_articles = self.get_generated_articles_history()
            generated_queries = {article['trend_query'] for article in generated_articles}
            logger.info(f"Excluding {len(generated_queries)} already generated trends")
        
        # Filter trends
        selected_trends = []
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for trend in trends:
            # Skip if already generated
            if exclude_already_generated and trend['query'] in generated_queries:
                continue
            
            # Check importance score
            importance_score = trend.get('importance_score', 0)
            if importance_score < min_importance_score:
                continue
            
            # Check age
            try:
                collected_date = datetime.fromisoformat(trend.get('collected_date', ''))
                if collected_date < cutoff_date:
                    continue
            except (ValueError, TypeError):
                # Skip if date parsing fails
                continue
            
            # Check if it's sports-related
            category = trend.get('category', '').lower()
            if category != 'sports':
                continue
            
            selected_trends.append(trend)
        
        # Sort by importance score and rank
        selected_trends.sort(key=lambda x: (x.get('importance_score', 0), -x.get('rank', 999)), reverse=True)
        
        # Limit to max_articles
        selected_trends = selected_trends[:max_articles]
        
        logger.info(f"Selected {len(selected_trends)} trends for generation:")
        for i, trend in enumerate(selected_trends, 1):
            logger.info(f"  {i}. {trend['query']} (score: {trend.get('importance_score', 0)}, rank: {trend.get('rank', 'N/A')})")
        
        return selected_trends


class GoogleTrendsArticlePipeline:
    """Main pipeline for generating articles from Google Trends data"""
    
    def __init__(self):
        """Initialize the Google Trends Article Pipeline"""
        logger.info("="*70)
        logger.info("🚀 INITIALIZING GOOGLE TRENDS ARTICLE PIPELINE")
        logger.info("="*70)
        
        # Initialize components
        self.trends_loader = GoogleTrendsDataLoader()
        self.search_fetcher = EnhancedSearchContentFetcher()
        self.sports_generator = SportsArticleGenerator()
        
        # Initialize Perplexity client (backup research method)
        try:
            self.perplexity_client = PerplexityResearchCollector()
            self.perplexity_available = True
        except Exception as e:
            logger.warning(f"Perplexity client not available: {e}")
            self.perplexity_available = False
        
        # Initialize article generation pipeline for advanced features
        try:
            if self.perplexity_available:
                self.article_pipeline = ArticleGenerationPipeline(
                    perplexity_client=self.perplexity_client,
                    gemini_client=self.sports_generator
                )
            else:
                self.article_pipeline = None
        except Exception as e:
            logger.warning(f"Article pipeline not fully available: {e}")
            self.article_pipeline = None
        
        # Setup output directory
        self.output_dir = current_dir / "generated_articles"
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info("✅ Google Trends Article Pipeline initialized")
        logger.info(f"📂 Output directory: {self.output_dir}")
        logger.info(f"🔍 Enhanced Search available: {self.search_fetcher.available}")
        logger.info(f"🤖 Sports Generator available: {self.sports_generator.available}")
        logger.info(f"🔄 Perplexity available: {self.perplexity_available}")
    
    def generate_article_from_trend(self, trend_data: Dict) -> Dict:
        """
        Generate a complete article from a single trend
        
        Args:
            trend_data: Single trend data dict from Google Trends
            
        Returns:
            Dict: Article generation result
        """
        trend_query = trend_data['query']
        
        logger.info(f"\n🎯 GENERATING ARTICLE FOR TREND: {trend_query}")
        logger.info("="*70)
        
        start_time = time.time()
        
        try:
            # Step 1: Enhanced Search for comprehensive information
            logger.info(f"🔍 Step 1: Gathering comprehensive information...")
            
            search_start = time.time()
            search_result = self.search_fetcher.collect_comprehensive_research(
                headline=trend_query,
                category="sports"
            )
            search_time = time.time() - search_start
            
            if search_result.get('status') != 'success':
                error_msg = search_result.get('error', 'Search failed')
                logger.error(f"❌ Search failed: {error_msg}")
                return {
                    'status': 'error',
                    'error': f"Search failed: {error_msg}",
                    'trend_query': trend_query,
                    'search_time': search_time
                }
            
            logger.info(f"✅ Search completed in {search_time:.2f}s")
            logger.info(f"   📊 Sources found: {search_result.get('total_sources_processed', 0)}")
            logger.info(f"   📝 Total words collected: {search_result.get('total_words_collected', 0)}")
            
            # Step 2: Generate article using the sports article generator
            logger.info(f"🤖 Step 2: Generating human-style sports article...")
            
            generation_start = time.time()
            
            # Prepare data for the sports generator (same format as existing pipeline)
            article_entry = {
                'title': trend_query,
                'url': '',  # No specific URL for trends
                'source_name': 'Google Trends',
                'category': 'sports',
                'published_date': trend_data.get('collected_date', datetime.now().isoformat()),
                'importance_score': trend_data.get('importance_score', 50)
            }
            
            # Use the existing sports article generation pipeline
            if self.article_pipeline:
                # Use the full pipeline if available
                article_result = self.article_pipeline.generate_article_for_headline(article_entry)
            else:
                # Fallback to direct generation
                research_content = search_result.get('comprehensive_research', '')
                sources = search_result.get('source_urls', [])
                
                article_result = self.sports_generator.generate_article_from_research(
                    headline=trend_query,
                    source="Google Trends",
                    category="sports",
                    importance_score=trend_data.get('importance_score', 50),
                    research_content=research_content,
                    sources=sources,
                    url=""
                )
            
            generation_time = time.time() - generation_start
            
            if not article_result or article_result.get('status') != 'success':
                error_msg = article_result.get('error', 'Article generation failed') if article_result else 'No response from generator'
                logger.error(f"❌ Article generation failed: {error_msg}")
                return {
                    'status': 'error',
                    'error': f"Article generation failed: {error_msg}",
                    'trend_query': trend_query,
                    'search_time': search_time,
                    'generation_time': generation_time
                }
            
            logger.info(f"✅ Article generated in {generation_time:.2f}s")
            logger.info(f"   📝 Word count: {article_result.get('word_count', 0)}")
            logger.info(f"   📄 Headline: {article_result.get('headline', trend_query)}")
            
            # Step 3: Save the article
            logger.info(f"💾 Step 3: Saving generated article...")
            
            save_result = self._save_article(trend_query, article_result, search_result)
            
            if save_result.get('status') != 'success':
                logger.error(f"❌ Failed to save article: {save_result.get('error', 'Unknown error')}")
                return {
                    'status': 'error',
                    'error': f"Failed to save article: {save_result.get('error', 'Unknown error')}",
                    'trend_query': trend_query,
                    'search_time': search_time,
                    'generation_time': generation_time
                }
            
            # Step 4: Record in history
            self.trends_loader.save_generated_article(trend_query, {
                **article_result,
                'file_path': save_result.get('file_path', ''),
                'importance_score': trend_data.get('importance_score', 0)
            })
            
            total_time = time.time() - start_time
            
            logger.info(f"🎉 ARTICLE GENERATION COMPLETED!")
            logger.info(f"   ⏱️  Total time: {total_time:.2f}s")
            logger.info(f"   📁 Saved to: {save_result.get('file_path', 'Unknown')}")
            
            return {
                'status': 'success',
                'trend_query': trend_query,
                'article_data': article_result,
                'file_path': save_result.get('file_path', ''),
                'search_time': search_time,
                'generation_time': generation_time,
                'total_time': total_time,
                'sources_analyzed': search_result.get('total_sources_processed', 0),
                'research_words': search_result.get('total_words_collected', 0)
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"❌ Pipeline error: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                'status': 'error',
                'error': error_msg,
                'trend_query': trend_query,
                'total_time': total_time,
                'traceback': traceback.format_exc()
            }
    
    def _save_article(self, trend_query: str, article_result: Dict, search_result: Dict) -> Dict:
        """Save generated article to file"""
        try:
            # Create filename
            safe_filename = "".join(c for c in trend_query if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename.replace(' ', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"trends_{safe_filename}_{timestamp}.html"
            
            filepath = self.output_dir / filename
            
            # Prepare article content
            article_content = article_result.get('article_content', '')
            headline = article_result.get('headline', trend_query)
            
            # Create complete HTML document
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{headline}</title>
    <meta name="description" content="{article_result.get('seo_metadata', {}).get('meta_description', '')}">
    <meta name="keywords" content="{', '.join(article_result.get('seo_metadata', {}).get('keywords', []))}">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .meta {{ background: #f5f5f5; padding: 10px; margin-bottom: 20px; border-radius: 5px; }}
        .article-content {{ margin-bottom: 30px; }}
        .sources {{ background: #e8f4f8; padding: 15px; border-radius: 5px; }}
        .sources h3 {{ margin-top: 0; }}
        .sources a {{ display: block; margin: 5px 0; color: #0066cc; }}
    </style>
</head>
<body>
    <div class="meta">
        <h3>Article Generated from Google Trend</h3>
        <p><strong>Trending Query:</strong> {trend_query}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Word Count:</strong> {article_result.get('word_count', 0)}</p>
        <p><strong>Sources Analyzed:</strong> {search_result.get('total_sources_processed', 0)}</p>
    </div>
    
    <div class="article-content">
        {article_content}
    </div>
    
    <div class="sources">
        <h3>Research Sources</h3>
        {self._format_sources_html(search_result.get('source_urls', []))}
    </div>
</body>
</html>"""
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ Article saved to: {filepath}")
            
            return {
                'status': 'success',
                'file_path': str(filepath),
                'filename': filename
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Failed to save article: {str(e)}"
            }
    
    def _format_sources_html(self, sources: List[str]) -> str:
        """Format sources as HTML links"""
        if not sources:
            return "<p>No sources available</p>"
        
        html = ""
        for i, source in enumerate(sources[:10], 1):  # Limit to top 10 sources
            html += f'<a href="{source}" target="_blank">{i}. {source}</a>\n'
        
        return html
    
    def run_batch_generation(self, 
                           max_articles: int = 5,
                           min_importance_score: int = 40,
                           exclude_already_generated: bool = True) -> Dict:
        """
        Run batch generation for multiple trends
        
        Args:
            max_articles: Maximum number of articles to generate
            min_importance_score: Minimum importance score for trends
            exclude_already_generated: Skip already generated trends
            
        Returns:
            Dict: Batch generation results
        """
        logger.info("\n" + "="*70)
        logger.info("🚀 RUNNING GOOGLE TRENDS BATCH ARTICLE GENERATION")
        logger.info("="*70)
        
        batch_start = time.time()
        results = {
            'status': 'success',
            'total_requested': max_articles,
            'articles_generated': [],
            'failed_articles': [],
            'skipped_trends': [],
            'total_time': 0,
            'summary': {}
        }
        
        try:
            # Load trends data
            logger.info("📚 Loading Google Trends data...")
            trends = self.trends_loader.load_trends_data()
            
            if not trends:
                return {
                    'status': 'error',
                    'error': 'No trends data available',
                    'total_time': time.time() - batch_start
                }
            
            # Filter trends for generation
            selected_trends = self.trends_loader.filter_trends_for_generation(
                trends=trends,
                max_articles=max_articles,
                min_importance_score=min_importance_score,
                exclude_already_generated=exclude_already_generated
            )
            
            if not selected_trends:
                logger.warning("⚠️  No trends selected for generation after filtering")
                results['status'] = 'warning'
                results['error'] = 'No suitable trends found after filtering'
                results['total_time'] = time.time() - batch_start
                return results
            
            logger.info(f"🎯 Generating articles for {len(selected_trends)} trends...")
            
            # Generate articles for each trend
            for i, trend in enumerate(selected_trends, 1):
                logger.info(f"\n--- Processing Trend {i}/{len(selected_trends)} ---")
                
                trend_result = self.generate_article_from_trend(trend)
                
                if trend_result.get('status') == 'success':
                    results['articles_generated'].append(trend_result)
                    logger.info(f"✅ Successfully generated article for: {trend['query']}")
                else:
                    results['failed_articles'].append(trend_result)
                    logger.error(f"❌ Failed to generate article for: {trend['query']}")
                
                # Small delay between generations to avoid rate limits
                if i < len(selected_trends):
                    logger.info("⏸️  Brief pause before next generation...")
                    time.sleep(2)
            
            # Compile summary
            results['total_time'] = time.time() - batch_start
            results['summary'] = {
                'successful_articles': len(results['articles_generated']),
                'failed_articles': len(results['failed_articles']),
                'total_trends_processed': len(selected_trends),
                'average_time_per_article': results['total_time'] / max(len(selected_trends), 1),
                'success_rate': len(results['articles_generated']) / max(len(selected_trends), 1) * 100
            }
            
            # Log final summary
            logger.info("\n" + "="*70)
            logger.info("🎊 BATCH GENERATION COMPLETED")
            logger.info("="*70)
            logger.info(f"✅ Successful articles: {results['summary']['successful_articles']}")
            logger.info(f"❌ Failed articles: {results['summary']['failed_articles']}")
            logger.info(f"📊 Success rate: {results['summary']['success_rate']:.1f}%")
            logger.info(f"⏱️  Total time: {results['total_time']:.2f}s")
            logger.info(f"📂 Articles saved to: {self.output_dir}")
            
            return results
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            results['total_time'] = time.time() - batch_start
            logger.error(f"❌ Batch generation error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return results


def main():
    """Main function for testing the pipeline"""
    logger.info("🧪 TESTING GOOGLE TRENDS ARTICLE PIPELINE")
    
    # Initialize pipeline
    pipeline = GoogleTrendsArticlePipeline()
    
    # Test single trend generation
    trends = pipeline.trends_loader.load_trends_data()
    if trends:
        # Get the top trend
        top_trend = trends[0]
        logger.info(f"🧪 Testing with top trend: {top_trend['query']}")
        
        result = pipeline.generate_article_from_trend(top_trend)
        
        if result.get('status') == 'success':
            logger.info("🎉 Single trend test successful!")
        else:
            logger.error(f"❌ Single trend test failed: {result.get('error', 'Unknown error')}")
    
    # Test batch generation (small batch for testing)
    logger.info("\n🧪 Testing batch generation...")
    batch_result = pipeline.run_batch_generation(max_articles=2, min_importance_score=30)
    
    if batch_result.get('status') in ['success', 'warning']:
        logger.info("🎉 Batch generation test completed!")
    else:
        logger.error(f"❌ Batch generation test failed: {batch_result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()