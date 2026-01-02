"""
Enhanced News Pipeline for Sportspedia Zone
Comprehensive pipeline for RSS collection, preprocessing, cleanup, and hybrid ranking
Latest articles get priority, then sorted by importance within time brackets
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import time
from dateutil import parser

# Import our existing modules
from Sports_Article_Automation.utilities.rss_analyzer import RSSNewsCollector
from Sports_Article_Automation.utilities.article_scorer import ArticleImportanceScorer
from Sports_Article_Automation.utilities.sports_categorizer import SportsNewsCategorizer

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Setup logging (prevent duplicate handlers completely)
root_logger = logging.getLogger()
if not root_logger.handlers:
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler('pipeline.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

class EnhancedNewsPipeline:
    def __init__(self, csv_sources: str = None, database_file: str = None):
        self.csv_sources = csv_sources or str(DATA_DIR / "rss_sources.csv")
        self.database_file = database_file or str(DATA_DIR / "sports_news_database.json")
        self.collector = RSSNewsCollector(self.csv_sources, self.database_file)
        self.scorer = ArticleImportanceScorer()
        self.categorizer = SportsNewsCategorizer(self.database_file)
        
    def run_complete_pipeline(self, max_hours: int = 24):
        """
        Run the complete news pipeline:
        1. Collect latest RSS feeds (includes automatic scoring and cleanup)
        2. Apply hybrid ranking (latest + importance)
        3. Categorize articles into Cricket, Football, Basketball
        """
        pipeline_start = time.time()
        logging.info("=" * 60)
        logging.info("STARTING ENHANCED NEWS PIPELINE")
        logging.info("=" * 60)
        
        try:
            # Step 1: RSS Collection (includes automatic scoring and cleanup)
            logging.info("\n🔄 STEP 1: RSS Feed Collection (with automatic scoring & cleanup)")
            collection_stats = self.collect_rss_feeds()
            
            # Step 2: Apply hybrid ranking
            logging.info("\n📊 STEP 2: Apply hybrid ranking (latest + importance)")
            ranking_stats = self.apply_hybrid_ranking()
            
            # Step 3: Categorize articles by sport
            logging.info("\n🏆 STEP 3: Categorize articles by sport (Cricket, Football, Basketball)")
            categorization_stats = self.categorize_articles()
            
            # Step 4: Generate summary
            pipeline_end = time.time()
            self.generate_pipeline_summary(collection_stats, ranking_stats, categorization_stats, pipeline_end - pipeline_start)
            
        except Exception as e:
            logging.error(f"Pipeline failed: {e}")
            raise

    def collect_rss_feeds(self) -> Dict:
        """Collect news from all RSS sources"""
        collection_start = time.time()
        
        # Load existing database to track before/after
        initial_count = len(self.collector.news_database['articles'])
        
        # Run RSS collection
        collection_summary = self.collector.collect_all_news()
        
        # Calculate stats
        final_count = len(self.collector.news_database['articles'])
        new_articles = collection_summary.get('new_articles_added', 0)
        
        stats = {
            'initial_articles': initial_count,
            'final_articles': final_count,
            'new_articles_collected': new_articles,
            'sources_processed': collection_summary.get('sources_processed', 0),
            'successful_sources': len([r for r in collection_summary.get('source_results', {}).values() if r.get('status') == 'success']),
            'duration': time.time() - collection_start
        }
        
        logging.info(f"✅ Collection complete: {new_articles} new articles from {stats['successful_sources']}/{stats['sources_processed']} sources")
        return stats

    def cleanup_old_articles(self, max_hours: int = 24) -> Dict:
        """Remove articles older than specified hours"""
        cleanup_start = time.time()
        
        before_count = len(self.collector.news_database['articles'])
        
        # Run cleanup using the collector's method
        self.collector.cleanup_old_articles(hours_threshold=max_hours)
        
        # Save the database after cleanup
        self.collector.save_database()
        after_count = len(self.collector.news_database['articles'])
        
        cleanup_stats = {
            'articles_before': before_count,
            'articles_after': after_count,
            'articles_removed': before_count - after_count,
            'hours_threshold': max_hours,
            'duration': time.time() - cleanup_start
        }
        
        logging.info(f"✅ Cleanup complete: Removed {cleanup_stats['articles_removed']} old articles")
        return cleanup_stats

    def score_all_articles(self) -> Dict:
        """Score all articles for importance"""
        scoring_start = time.time()
        
        articles = self.collector.news_database['articles']
        scored_count = 0
        score_distribution = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for article in articles:
            # Calculate importance score
            score = self.scorer.calculate_article_score(
                title=article.get('title', ''),
                summary=article.get('summary', ''),
                source_name=article.get('source_name', ''),
                pub_date=article.get('published_date', '')
            )
            
            # Update article with score
            article['importance_score'] = score
            article['last_scored'] = datetime.now().isoformat()
            
            # Categorize importance
            if score >= 80:
                article['importance_level'] = 'critical'
                score_distribution['critical'] += 1
            elif score >= 60:
                article['importance_level'] = 'high'
                score_distribution['high'] += 1
            elif score >= 40:
                article['importance_level'] = 'medium'
                score_distribution['medium'] += 1
            else:
                article['importance_level'] = 'low'
                score_distribution['low'] += 1
                
            scored_count += 1
        
        # Save updated database
        self.collector.save_database()
        
        stats = {
            'articles_scored': scored_count,
            'score_distribution': score_distribution,
            'duration': time.time() - scoring_start
        }
        
        logging.info(f"✅ Scoring complete: {scored_count} articles scored")
        return stats

    def apply_hybrid_ranking(self) -> Dict:
        """
        Apply hybrid ranking: Latest articles first, then by importance within time brackets
        
        Ranking Strategy:
        1. Group articles by time brackets (0-2h, 2-6h, 6-12h, 12-24h)
        2. Within each bracket, sort by importance score (highest first)
        3. Assign hybrid rank based on this hierarchy
        """
        ranking_start = time.time()
        
        articles = self.collector.news_database['articles']
        current_time = datetime.now()
        
        # Create time brackets
        time_brackets = {
            'ultra_fresh': [],    # 0-2 hours
            'very_fresh': [],     # 2-6 hours  
            'fresh': [],          # 6-12 hours
            'recent': []          # 12-24 hours
        }
        
        # Sort articles into time brackets
        for article in articles:
            pub_date_str = article.get('published_date', '')
            if not pub_date_str:
                continue
                
            try:
                # Parse publication date
                if isinstance(pub_date_str, str):
                    pub_date = parser.parse(pub_date_str.replace(' GMT', ''))
                else:
                    pub_date = pub_date_str
                    
                # Make timezone-aware if needed
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=current_time.tzinfo)
                    
                # Calculate age
                time_diff = (current_time.replace(tzinfo=None) - pub_date.replace(tzinfo=None)).total_seconds() / 3600
                
                # Categorize into brackets
                if time_diff <= 2:
                    time_brackets['ultra_fresh'].append(article)
                elif time_diff <= 6:
                    time_brackets['very_fresh'].append(article)
                elif time_diff <= 12:
                    time_brackets['fresh'].append(article)
                elif time_diff <= 24:
                    time_brackets['recent'].append(article)
                    
            except Exception as e:
                logging.warning(f"Date parsing error for article: {e}")
                time_brackets['recent'].append(article)  # Default to recent
        
        # Sort each bracket by importance score (highest first)
        for bracket_name, bracket_articles in time_brackets.items():
            bracket_articles.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
        
        # Assign hybrid ranking
        ranked_articles = []
        current_rank = 1
        
        for bracket_name in ['ultra_fresh', 'very_fresh', 'fresh', 'recent']:
            for article in time_brackets[bracket_name]:
                article['hybrid_rank'] = current_rank
                article['time_bracket'] = bracket_name
                ranked_articles.append(article)
                current_rank += 1
        
        # Update database with ranked articles
        self.collector.news_database['articles'] = ranked_articles
        self.collector.news_database['last_ranked'] = current_time.isoformat()
        self.collector.save_database()
        
        # Calculate stats
        stats = {
            'total_articles': len(ranked_articles),
            'ultra_fresh_count': len(time_brackets['ultra_fresh']),
            'very_fresh_count': len(time_brackets['very_fresh']),
            'fresh_count': len(time_brackets['fresh']),
            'recent_count': len(time_brackets['recent']),
            'duration': time.time() - ranking_start
        }
        
        logging.info(f"✅ Hybrid ranking complete: {stats['total_articles']} articles ranked")
        logging.info(f"   Ultra-fresh (0-2h): {stats['ultra_fresh_count']} articles")
        logging.info(f"   Very fresh (2-6h): {stats['very_fresh_count']} articles")
        logging.info(f"   Fresh (6-12h): {stats['fresh_count']} articles")
        logging.info(f"   Recent (12-24h): {stats['recent_count']} articles")
        
        return stats

    def categorize_articles(self) -> Dict:
        """Categorize articles into sport-specific databases"""
        categorization_start = time.time()
        
        # Run categorization
        result = self.categorizer.categorize_all_articles(save_individual_files=True)
        
        # Update main database with category information
        self.categorizer.update_main_database_with_categories()
        
        # Reload the updated database
        self.collector.load_existing_database()
        
        stats = {
            'total_articles': result['stats']['total_articles'],
            'cricket_count': result['stats']['categorized'].get('cricket', 0),
            'football_count': result['stats']['categorized'].get('football', 0),
            'basketball_count': result['stats']['categorized'].get('basketball', 0),
            'uncategorized_count': result['stats']['uncategorized'],
            'duration': time.time() - categorization_start
        }
        
        logging.info(f"✅ Categorization complete:")
        logging.info(f"   Cricket: {stats['cricket_count']} articles")
        logging.info(f"   Football: {stats['football_count']} articles")
        logging.info(f"   Basketball: {stats['basketball_count']} articles")
        logging.info(f"   Uncategorized: {stats['uncategorized_count']} articles")
        
        return stats

    def generate_pipeline_summary(self, collection_stats: Dict, ranking_stats: Dict, categorization_stats: Dict, total_duration: float):
        """Generate comprehensive pipeline summary"""
        
        logging.info("\n" + "=" * 60)
        logging.info("PIPELINE EXECUTION SUMMARY")
        logging.info("=" * 60)
        
        logging.info(f"⏱️  Total Pipeline Duration: {total_duration:.2f} seconds")
        logging.info("")
        
        logging.info(f"📡 RSS COLLECTION:")
        logging.info(f"   • Sources processed: {collection_stats['sources_processed']}")
        logging.info(f"   • Successful sources: {collection_stats['successful_sources']}")
        logging.info(f"   • New articles collected: {collection_stats['new_articles_collected']}")
        logging.info(f"   • Total articles in database: {collection_stats['final_articles']}")
        logging.info(f"   • Duration: {collection_stats['duration']:.2f}s")
        logging.info("")
        
        # Ranking Summary
        logging.info("📊 HYBRID RANKING:")
        logging.info(f"   • Total articles ranked: {ranking_stats['total_articles']}")
        logging.info(f"   • Ultra-fresh (0-2h): {ranking_stats['ultra_fresh_count']}")
        logging.info(f"   • Very fresh (2-6h): {ranking_stats['very_fresh_count']}")
        logging.info(f"   • Fresh (6-12h): {ranking_stats['fresh_count']}")
        logging.info(f"   • Recent (12-24h): {ranking_stats['recent_count']}")
        logging.info(f"   • Duration: {ranking_stats['duration']:.2f}s")
        logging.info("")
        
        # Categorization Summary
        logging.info("🏆 SPORT CATEGORIZATION:")
        logging.info(f"   • Total articles categorized: {categorization_stats['total_articles']}")
        logging.info(f"   • Cricket articles: {categorization_stats['cricket_count']}")
        logging.info(f"   • Football articles: {categorization_stats['football_count']}")
        logging.info(f"   • Basketball articles: {categorization_stats['basketball_count']}")
        logging.info(f"   • Uncategorized articles: {categorization_stats['uncategorized_count']}")
        logging.info(f"   • Duration: {categorization_stats['duration']:.2f}s")
        
        logging.info("\n✅ PIPELINE COMPLETED SUCCESSFULLY!")
        logging.info("="*60)
        logging.info("\n📁 GENERATED FILES:")
        logging.info("   🏏 cricket_news_database.json")
        logging.info("   ⚽ football_news_database.json")
        logging.info("   🏀 basketball_news_database.json")
        logging.info("   📰 uncategorized_news_database.json")

    def get_top_articles(self, limit: int = 20) -> List[Dict]:
        """Get top articles according to hybrid ranking"""
        articles = self.collector.news_database['articles']
        
        # Sort by hybrid rank (ascending - rank 1 is best)
        sorted_articles = sorted(articles, key=lambda x: x.get('hybrid_rank', float('inf')))
        
        return sorted_articles[:limit]

    def get_articles_by_time_bracket(self, bracket: str) -> List[Dict]:
        """Get articles from specific time bracket"""
        valid_brackets = ['ultra_fresh', 'very_fresh', 'fresh', 'recent']
        if bracket not in valid_brackets:
            raise ValueError(f"Invalid bracket. Must be one of: {valid_brackets}")
            
        articles = self.collector.news_database['articles']
        return [article for article in articles if article.get('time_bracket') == bracket]


def main():
    """Run the enhanced news pipeline"""
    logging.info("Initializing Enhanced News Pipeline...")
    
    try:
        # Initialize pipeline
        pipeline = EnhancedNewsPipeline()
        
        # Run complete pipeline
        pipeline.run_complete_pipeline(max_hours=24)
        
        # Show top 10 articles
        logging.info("\n🏆 TOP 10 ARTICLES (Latest + Most Important):")
        top_articles = pipeline.get_top_articles(10)
        
        for i, article in enumerate(top_articles, 1):
            logging.info(f"{i:2d}. [{article.get('time_bracket', 'unknown'):>11}] "
                        f"Score: {article.get('importance_score', 0):5.1f} - "
                        f"{article.get('title', 'No title')[:80]}...")
        
    except Exception as e:
        logging.error(f"Pipeline execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()