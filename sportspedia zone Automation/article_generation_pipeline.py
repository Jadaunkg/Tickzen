"""
Article Generation Pipeline with Research-to-Article Workflow
Complete pipeline: RSS Data → Headline Selection → Perplexity Research → Gemini Article Generation

Two-stage article creation:
1. Perplexity AI: Collects research and latest information from internet
2. Gemini AI: Generates SEO-optimized, human-written articles from research
"""

import json
import logging
import os
import sys
import re
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

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
        logging.FileHandler('article_generation_pipeline.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)


class ArticleGenerationPipeline:
    """
    Complete pipeline for generating articles from collected news headlines
    Two-stage process: Research Collection → Article Generation
    """
    
    def __init__(self, 
                 database_file: str = str(DATA_DIR / "sports_news_database.json"),
                 perplexity_client=None,
                 gemini_client=None):
        """
        Initialize Article Generation Pipeline
        
        Args:
            database_file (str): Path to collected articles database
            perplexity_client: Configured Perplexity AI client for research
            gemini_client: Configured Gemini AI client for article writing
        """
        self.database_file = database_file
        self.perplexity_client = perplexity_client
        self.gemini_client = gemini_client
        self.generated_articles = []
        self.processing_stats = {
            'total_processed': 0,
            'research_collected': 0,
            'articles_generated': 0,
            'failed': 0,
            'total_content_length': 0
        }
        
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
            base_dir = DATA_DIR
            # Check if category-specific database exists
            if category:
                category_file = base_dir / f"{category}_news_database.json"
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
            
            # Stage 1: Collect research
            logging.info(f"\n{'='*70}")
            logging.info(f"STAGE 1️⃣: RESEARCH COLLECTION (Perplexity AI)")
            logging.info(f"{'='*70}")
            
            research_data = self.perplexity_client.collect_research_for_headline(
                headline=headline,
                source=source,
                category=category
            )
            
            self.processing_stats['research_collected'] += 1
            
            if research_data.get('status') not in ['success', 'placeholder']:
                logging.error(f"❌ Research collection failed")
                self.processing_stats['failed'] += 1
                return {
                    'status': 'error',
                    'error': 'Research collection failed',
                    'article_entry': article_entry
                }
            
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
            
            # Generate article
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
    from perplexity_ai_client import PerplexityAIClient
    
    # Initialize Perplexity client
    perplexity_client = PerplexityAIClient()
    
    # Run demonstration
    demonstrate_pipeline(perplexity_client)
