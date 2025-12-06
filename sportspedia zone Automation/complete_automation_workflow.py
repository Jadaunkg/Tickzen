"""
Complete Automation Workflow
Orchestrates the full pipeline from data collection → headline selection → article generation
Ready for deployment and automation on the website
"""

import json
import logging
import os
import sys
import time
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
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
        logging.FileHandler('automation_workflow.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)


class CompleteAutomationWorkflow:
    """
    Complete end-to-end automation workflow
    Orchestrates: Data Collection → Scoring → Categorization → Headline Selection → Article Generation
    """
    
    def __init__(self):
        """Initialize the complete automation workflow"""
        self.workflow_start = time.time()
        self.results = {
            'workflow_start': datetime.now().isoformat(),
            'stages': {},
            'articles_generated': [],
            'errors': []
        }
        
    def run_complete_workflow(self,
                             collect_data: bool = True,
                             category: Optional[str] = None,
                             num_articles: int = 1,
                             selection_method: str = "top_importance") -> Dict:
        """
        Run the complete automation workflow
        
        Args:
            collect_data (bool): Whether to run RSS collection first
            category (str): Category to focus on (cricket, football, basketball, etc.)
            num_articles (int): Number of articles to generate
            selection_method (str): How to select articles (top_importance, latest, hybrid)
            
        Returns:
            Dict: Complete workflow results
        """
        try:
            logging.info("\n" + "="*70)
            logging.info("🚀 STARTING COMPLETE AUTOMATION WORKFLOW")
            logging.info("="*70)
            logging.info(f"⏰ Workflow Start: {self.results['workflow_start']}")
            logging.info(f"🎯 Target: Generate {num_articles} {category or 'mixed'} article(s)")
            
            # Stage 1: Data Collection (optional)
            if collect_data:
                self._stage_data_collection()
            
            # Stage 2: Load and Select Headlines
            self._stage_headline_selection(category, num_articles, selection_method)
            
            # Stage 3: Generate Articles
            self._stage_article_generation()
            
            # Stage 4: Save Results
            self._stage_save_results()
            
            # Print final summary
            self._print_workflow_summary()
            
            return self.results
            
        except Exception as e:
            logging.error(f"❌ Workflow error: {e}")
            self.results['errors'].append(str(e))
            return self.results
    
    def _stage_data_collection(self):
        """Stage 1: Run RSS data collection pipeline"""
        try:
            logging.info("\n" + "-"*70)
            logging.info("📡 STAGE 1: DATA COLLECTION")
            logging.info("-"*70)
            
            from enhanced_news_pipeline import EnhancedNewsPipeline
            
            logging.info("🔄 Running enhanced news pipeline...")
            pipeline = EnhancedNewsPipeline()
            stats = pipeline.run_complete_pipeline()
            
            self.results['stages']['data_collection'] = {
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            }
            
            logging.info("✅ Data collection complete!")
            
        except Exception as e:
            logging.error(f"❌ Data collection failed: {e}")
            self.results['errors'].append(f"Data collection: {e}")
            self.results['stages']['data_collection'] = {'status': 'failed', 'error': str(e)}
    
    def _stage_headline_selection(self, category: Optional[str], 
                                 num_articles: int, 
                                 selection_method: str):
        """Stage 2: Load and select headlines"""
        try:
            logging.info("\n" + "-"*70)
            logging.info("📋 STAGE 2: HEADLINE SELECTION")
            logging.info("-"*70)
            
            from article_generation_pipeline import ArticleGenerationPipeline
            
            # Initialize pipeline (without Perplexity for now)
            pipeline = ArticleGenerationPipeline()
            
            # Load articles
            logging.info(f"📂 Loading articles {f'from {category}' if category else ''}...")
            articles = pipeline.load_articles_from_database(category=category, limit=num_articles*2)
            
            # Select headline
            logging.info(f"🎯 Selecting by '{selection_method}' method...")
            selected_articles = []
            
            for i, article in enumerate(articles[:num_articles]):
                selected = pipeline.select_headline_for_processing([article], selection_method)
                if selected:
                    selected_articles.append(selected)
            
            self.results['stages']['headline_selection'] = {
                'status': 'completed',
                'articles_selected': len(selected_articles),
                'category': category or 'mixed',
                'selection_method': selection_method,
                'timestamp': datetime.now().isoformat()
            }
            
            # Store selected articles for next stage
            self.results['selected_articles'] = selected_articles
            
            logging.info(f"✅ Selected {len(selected_articles)} headline(s)")
            
        except Exception as e:
            logging.error(f"❌ Headline selection failed: {e}")
            self.results['errors'].append(f"Headline selection: {e}")
            self.results['stages']['headline_selection'] = {'status': 'failed', 'error': str(e)}
    
    def _stage_article_generation(self):
        """Stage 3: Generate articles from selected headlines"""
        try:
            logging.info("\n" + "-"*70)
            logging.info("✍️  STAGE 3: ARTICLE GENERATION (Perplexity + Gemini)")
            logging.info("-"*70)
            
            from perplexity_ai_client import PerplexityResearchCollector
            from gemini_article_generator import GeminiArticleGenerator
            from article_generation_pipeline import ArticleGenerationPipeline
            
            selected_articles = self.results.get('selected_articles', [])
            
            if not selected_articles:
                logging.warning("⚠️  No articles to generate")
                return
            
            # Initialize clients
            perplexity_client = PerplexityResearchCollector()
            gemini_client = GeminiArticleGenerator()
            pipeline = ArticleGenerationPipeline(
                perplexity_client=perplexity_client,
                gemini_client=gemini_client
            )
            
            # Create output directory
            os.makedirs('generated_articles', exist_ok=True)
            
            # Generate articles
            for i, article in enumerate(selected_articles, 1):
                logging.info(f"\n[{i}/{len(selected_articles)}] Generating article...")
                
                generated = pipeline.generate_article_for_headline(article)
                
                if generated:
                    # Save article
                    filepath = pipeline.save_generated_article(generated)
                    
                    # Store results
                    self.results['articles_generated'].append({
                        'headline': article.get('title'),
                        'source': article.get('source_name'),
                        'category': article.get('category'),
                        'filepath': filepath,
                        'status': generated.get('status'),
                        'content_length': len(generated.get('article_content', '')),
                        'timestamp': datetime.now().isoformat()
                    })
            
            self.results['stages']['article_generation'] = {
                'status': 'completed',
                'articles_generated': len(self.results['articles_generated']),
                'timestamp': datetime.now().isoformat()
            }
            
            logging.info(f"✅ Generated {len(self.results['articles_generated'])} article(s)")
            
        except Exception as e:
            logging.error(f"❌ Article generation failed: {e}")
            self.results['errors'].append(f"Article generation: {e}")
            self.results['stages']['article_generation'] = {'status': 'failed', 'error': str(e)}
    
    def _stage_save_results(self):
        """Stage 4: Save final results"""
        try:
            logging.info("\n" + "-"*70)
            logging.info("💾 STAGE 4: SAVING RESULTS")
            logging.info("-"*70)
            
            self.results['workflow_end'] = datetime.now().isoformat()
            self.results['workflow_duration_seconds'] = time.time() - self.workflow_start
            
            # Save workflow results into dedicated folder
            results_dir = Path("outputs/workflows")
            results_dir.mkdir(parents=True, exist_ok=True)
            results_file = results_dir / f"workflow_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            logging.info(f"✅ Results saved to: {results_file}")
            
            self.results['stages']['save_results'] = {
                'status': 'completed',
                'results_file': results_file,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"❌ Save results failed: {e}")
            self.results['errors'].append(f"Save results: {e}")
    
    def _print_workflow_summary(self):
        """Print comprehensive workflow summary"""
        logging.info("\n" + "="*70)
        logging.info("📊 WORKFLOW SUMMARY")
        logging.info("="*70)
        
        logging.info(f"⏱️  Duration: {self.results['workflow_duration_seconds']:.2f} seconds")
        logging.info(f"\n📈 Stages Completed:")
        
        for stage_name, stage_data in self.results.get('stages', {}).items():
            status = stage_data.get('status', 'unknown')
            status_emoji = "✅" if status == "completed" else "❌"
            logging.info(f"   {status_emoji} {stage_name}: {status}")
        
        logging.info(f"\n📰 Articles Generated: {len(self.results['articles_generated'])}")
        
        for i, article in enumerate(self.results['articles_generated'], 1):
            logging.info(f"   [{i}] {article['headline'][:60]}...")
            logging.info(f"       📍 Source: {article['source']}")
            logging.info(f"       ✅ Status: {article['status']}")
        
        if self.results['errors']:
            logging.info(f"\n⚠️  Errors ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                logging.info(f"   • {error}")
        
        logging.info("\n" + "="*70)
        logging.info("🎉 WORKFLOW COMPLETE!")
        logging.info("="*70)


def main():
    """
    Main entry point for complete automation workflow
    """
    # Create workflow instance
    workflow = CompleteAutomationWorkflow()
    
    # Run complete workflow
    results = workflow.run_complete_workflow(
        collect_data=False,  # Set to True to run RSS collection first
        category=None,       # Use 'cricket', 'football', 'basketball', or None for mixed
        num_articles=1,      # Number of articles to generate
        selection_method="top_importance"  # or "latest", "hybrid", "first"
    )
    
    return results


if __name__ == "__main__":
    main()
