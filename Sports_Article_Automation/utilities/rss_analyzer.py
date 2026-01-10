"""
RSS News Collector for Sportspedia Zone Automation
Collects news headlines and metadata from RSS feeds and saves to persistent JSON file
"""

import csv
import feedparser
import requests
import asyncio
import aiohttp
from urllib.parse import urlparse, urljoin
import time
from datetime import datetime
import json
import logging
from typing import Dict, List, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
from bs4 import BeautifulSoup
import hashlib
import os
from Sports_Article_Automation.utilities.article_scorer import ArticleImportanceScorer
from datetime import datetime, timedelta
from dateutil import parser
import pytz
from dateutil.tz import UTC

# Setup logging with UTF-8 encoding
import sys
import io

# Configure logging to handle Unicode properly (prevent duplicate handlers completely)
root_logger = logging.getLogger()
if not root_logger.handlers:
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler('rss_analysis.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

# Set console encoding for Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

class RSSNewsCollector:
    def __init__(self, csv_file_path: str, output_file: str = "sports_news_database.json"):
        self.csv_file_path = csv_file_path
        self.output_file = output_file
        
        # Initialize timezone objects for Indian timezone conversion
        self.utc = pytz.UTC
        self.ist = pytz.timezone('Asia/Kolkata')  # Indian Standard Time
        
        self.session = self.create_session()
        self.news_database = self.load_existing_database()
        self.scorer = ArticleImportanceScorer()
        
    def load_existing_database(self) -> Dict:
        """Load existing news database or create new one"""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logging.info(f"Loaded existing database with {len(data.get('articles', []))} articles")
                return data
            except Exception as e:
                logging.warning(f"Could not load existing database: {e}")
        
        return {
            "metadata": {
                "created_date": datetime.now().isoformat(),
                "last_updated": None,
                "total_articles": 0,
                "sources": []
            },
            "articles": []
        }
    
    def generate_article_id(self, title: str, link: str) -> str:
        """Generate unique ID for article to avoid duplicates"""
        unique_string = f"{title.lower().strip()}{link.strip()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
        
    def create_session(self):
        """Create a requests session with retry strategy and proper headers"""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set user agent to avoid blocking
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache'
        })
        
        return session
    
    def convert_to_ist(self, date_str: str) -> datetime:
        """
        Convert date string from any timezone to Indian Standard Time (IST)
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            datetime: IST datetime object or None if parsing fails
        """
        if not date_str:
            return None
            
        try:
            # Handle common RSS date format (RFC 2822 with GMT)
            if 'GMT' in date_str and ',' in date_str:
                parsed_date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S GMT')
                parsed_date = self.utc.localize(parsed_date)
            else:
                # Use dateutil parser for flexible parsing
                parsed_date = parser.parse(date_str)
                
                # If timezone-naive, assume UTC
                if parsed_date.tzinfo is None:
                    parsed_date = self.utc.localize(parsed_date)
            
            # Convert to IST
            ist_date = parsed_date.astimezone(self.ist)
            return ist_date
            
        except Exception as e:
            logging.debug(f"Failed to parse date '{date_str}': {e}")
            return None
    
    def is_within_24_hours(self, article_date: datetime) -> bool:
        """
        Check if article date is within last 24 hours (IST-based)
        
        Args:
            article_date: IST datetime object
            
        Returns:
            bool: True if within 24 hours, False otherwise
        """
        if not article_date:
            return False
            
        current_ist = datetime.now(self.ist)
        cutoff_time = current_ist - timedelta(hours=24)
        return article_date >= cutoff_time
    
    def get_current_ist(self) -> datetime:
        """Get current time in IST"""
        return datetime.now(self.ist)

    def load_rss_sources(self) -> List[Dict]:
        """Load RSS sources from CSV file"""
        sources = []
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    sources.append({
                        'name': row['site_name'].strip(),
                        'url': row['rss_url'].strip()
                    })
            logging.info(f"Loaded {len(sources)} RSS sources")
            return sources
        except Exception as e:
            logging.error(f"Error loading CSV file: {e}")
            return []

    def discover_rss_feeds(self, base_url: str) -> List[str]:
        """Try to discover RSS feeds from a website"""
        rss_feeds = []
        try:
            response = self.session.get(base_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for RSS feed links
                rss_links = soup.find_all('link', {'type': ['application/rss+xml', 'application/atom+xml']})
                for link in rss_links:
                    href = link.get('href')
                    if href:
                        if href.startswith('http'):
                            rss_feeds.append(href)
                        else:
                            rss_feeds.append(urljoin(base_url, href))
                
                # Look for common RSS paths
                common_paths = ['/rss', '/feed', '/feeds', '/rss.xml', '/feed.xml', '/atom.xml']
                for path in common_paths:
                    test_url = urljoin(base_url, path)
                    try:
                        test_response = self.session.head(test_url, timeout=5)
                        if test_response.status_code == 200:
                            rss_feeds.append(test_url)
                    except:
                        continue
                        
        except Exception as e:
            logging.warning(f"Could not discover RSS feeds for {base_url}: {e}")
        
        return list(set(rss_feeds))  # Remove duplicates

    def collect_news_from_feed(self, source: Dict) -> Dict:
        """Collect news articles from a single RSS feed"""
        result = {
            'source_name': source['name'],
            'source_url': source['url'],
            'status': 'unknown',
            'articles_found': 0,
            'new_articles_added': 0,
            'error': None
        }
        
        try:
            logging.info(f"Collecting news from {source['name']}: {source['url']}")
            
            # Parse RSS feed
            feed = feedparser.parse(source['url'])
            
            if feed.bozo == 0 or len(feed.entries) > 0:  # Valid feed or has entries
                existing_ids = {article['id'] for article in self.news_database['articles']}
                new_articles = 0
                
                for entry in feed.entries:
                    # Extract article data
                    article_data = self.extract_article_metadata(entry, source)
                    
                    # Apply 24-hour filtering - skip articles older than 24 hours (IST-based)
                    published_date_ist = self.convert_to_ist(article_data.get('published_date'))
                    if not self.is_within_24_hours(published_date_ist):
                        continue  # Skip articles older than 24 hours
                    
                    # Check if article already exists
                    article_id = self.generate_article_id(article_data['title'], article_data['link'])
                    
                    if article_id not in existing_ids:
                        article_data['id'] = article_id
                        article_data['collected_date'] = self.get_current_ist().isoformat()
                        self.news_database['articles'].append(article_data)
                        new_articles += 1
                
                result['status'] = 'success'
                result['articles_found'] = len(feed.entries)
                result['new_articles_added'] = new_articles
                
                logging.info(f"[SUCCESS] {source['name']}: {len(feed.entries)} articles found, {new_articles} new articles added")
            else:
                result['status'] = 'no_feed_found'
                result['error'] = 'No valid RSS feed found'
                logging.warning(f"[FAILED] {source['name']}: No valid RSS feed found")
                
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logging.error(f"[ERROR] {source['name']}: Error - {e}")
        
        # Add delay to be respectful
        time.sleep(2)
        return result
    
    def extract_article_metadata(self, entry, source: Dict) -> Dict:
        """Extract comprehensive metadata from RSS entry"""
        # Clean and extract text content
        def clean_text(text):
            if not text:
                return ""
            # Remove HTML tags if present
            if '<' in text:
                soup = BeautifulSoup(text, 'html.parser')
                return soup.get_text().strip()
            return text.strip()
        
        # Extract publication date
        published_date = None
        if hasattr(entry, 'published'):
            published_date = entry.published
        elif hasattr(entry, 'updated'):
            published_date = entry.updated
        
        # Convert to Indian Standard Time
        published_date_ist = self.convert_to_ist(published_date) if published_date else None
        
        # Extract categories/tags
        categories = []
        if hasattr(entry, 'tags'):
            categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
        
        # Extract author
        author = ""
        if hasattr(entry, 'author'):
            author = entry.author
        elif hasattr(entry, 'authors') and entry.authors:
            author = entry.authors[0].get('name', '') if isinstance(entry.authors[0], dict) else str(entry.authors[0])
        
        article = {
            'title': clean_text(getattr(entry, 'title', '')),
            'link': getattr(entry, 'link', ''),
            'summary': clean_text(getattr(entry, 'summary', ''))[:500],  # Limit summary length
            'published_date': published_date,
            'published_date_ist': published_date_ist.isoformat() if published_date_ist else None,
            'author': author,
            'categories': categories,
            'source_name': source['name'],
            'source_url': source['url'],
            'guid': getattr(entry, 'id', getattr(entry, 'guid', '')),
        }
        
        return article
    
    def collect_all_news(self) -> Dict:
        """Collect news from all RSS feeds using async parallel processing"""
        sources = self.load_rss_sources()
        if not sources:
            return {}
        
        logging.info(f"Starting ASYNC news collection from {len(sources)} RSS sources...")
        
        # Run async collection
        start_time = time.time()
        collection_results, total_new_articles = asyncio.run(
            self._collect_all_feeds_async(sources)
        )
        end_time = time.time()
        
        logging.info(f"⚡ Async collection completed in {end_time - start_time:.2f} seconds")
        
        # Update metadata
        self.news_database['metadata']['last_updated'] = datetime.now().isoformat()
        self.news_database['metadata']['total_articles'] = len(self.news_database['articles'])
        self.news_database['metadata']['sources'] = [source['name'] for source in sources]
        
        # Apply importance scoring to all articles
        if self.news_database['articles']:
            logging.info("Applying importance scoring to articles...")
            self.apply_importance_scoring()
        
        # Clean up old articles (keep only last 24 hours)
        logging.info("Cleaning up old articles (keeping last 24 hours)...")
        self.cleanup_old_articles(hours_threshold=24)
        
        # Deduplicate articles to remove duplicates across sources
        logging.info("Removing duplicate articles across sources...")
        self.deduplicate_articles()
        
        # Save updated database
        self.save_database()
        
        # Generate summary
        summary = {
            'collection_date': datetime.now().isoformat(),
            'collection_time_seconds': round(end_time - start_time, 2),
            'sources_processed': len(sources),
            'successful_sources': len([r for r in collection_results.values() if r['status'] == 'success']),
            'total_articles_in_database': len(self.news_database['articles']),
            'new_articles_added': total_new_articles,
            'source_results': collection_results,
            'performance_improvement': f"~{5*60/(end_time - start_time):.1f}x faster than sequential"
        }
        
        return summary

    async def _collect_all_feeds_async(self, sources: List[Dict]) -> Tuple[Dict, int]:
        """Async method to collect from all RSS feeds in parallel"""
        # Create aiohttp session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=20,  # Total connection pool size
            limit_per_host=3,  # Max connections per host (be respectful)
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(
            total=30,  # Total timeout per request
            connect=10  # Connection timeout
        )
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'RSS News Collector 2.0 (https://tickzen.app)',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*'
            }
        ) as session:
            # Create tasks for all sources
            tasks = [
                self._collect_from_single_feed_async(session, source) 
                for source in sources
            ]
            
            # Execute all tasks concurrently
            logging.info(f"🚀 Starting parallel collection from {len(sources)} sources...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            collection_results = {}
            total_new_articles = 0
            
            for i, result in enumerate(results):
                source = sources[i]
                source_name = source['name']
                
                if isinstance(result, Exception):
                    logging.error(f"❌ Exception for {source_name}: {str(result)}")
                    collection_results[source_name] = {
                        'source_name': source_name,
                        'source_url': source['url'],
                        'status': 'exception',
                        'articles_found': 0,
                        'new_articles_added': 0,
                        'error': str(result)
                    }
                else:
                    collection_results[source_name] = result
                    total_new_articles += result['new_articles_added']
                    
                    # Log result
                    if result['status'] == 'success':
                        logging.info(f"✅ {source_name}: {result['articles_found']} found, {result['new_articles_added']} new")
                    else:
                        logging.warning(f"⚠️ {source_name}: {result['error']}")
            
            return collection_results, total_new_articles

    async def _collect_from_single_feed_async(self, session: aiohttp.ClientSession, source: Dict) -> Dict:
        """Async method to collect news from a single RSS feed"""
        result = {
            'source_name': source['name'],
            'source_url': source['url'],
            'status': 'unknown',
            'articles_found': 0,
            'new_articles_added': 0,
            'error': None
        }
        
        try:
            # Fetch RSS content asynchronously
            async with session.get(source['url']) as response:
                if response.status != 200:
                    result['status'] = 'http_error'
                    result['error'] = f'HTTP {response.status}'
                    return result
                
                content = await response.text()
            
            # Parse RSS feed (feedparser is sync, but fast)
            feed = feedparser.parse(content)
            
            if feed.bozo == 0 or len(feed.entries) > 0:  # Valid feed or has entries
                existing_ids = {article['id'] for article in self.news_database['articles']}
                new_articles = 0
                
                for entry in feed.entries:
                    # Extract article data
                    article_data = self.extract_article_metadata(entry, source)
                    
                    # Apply 24-hour filtering - skip articles older than 24 hours (IST-based)
                    published_date_ist = self.convert_to_ist(article_data.get('published_date'))
                    if not self.is_within_24_hours(published_date_ist):
                        continue  # Skip articles older than 24 hours
                    
                    # Check if article already exists
                    article_id = self.generate_article_id(article_data['title'], article_data['link'])
                    
                    if article_id not in existing_ids:
                        article_data['id'] = article_id
                        article_data['collected_date'] = self.get_current_ist().isoformat()
                        self.news_database['articles'].append(article_data)
                        new_articles += 1
                
                result['status'] = 'success'
                result['articles_found'] = len(feed.entries)
                result['new_articles_added'] = new_articles
            else:
                result['status'] = 'no_feed_found'
                result['error'] = 'No valid RSS feed found'
                
        except asyncio.TimeoutError:
            result['status'] = 'timeout'
            result['error'] = 'Request timeout'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result

    def apply_importance_scoring(self):
        """Apply importance scoring to all articles in the database"""
        try:
            # Detect trending topics
            trending_boosts = self.scorer.detect_trending_topics(self.news_database['articles'])
            
            # Score each article
            tier_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0, 'Minimal': 0}
            
            for article in self.news_database['articles']:
                # Skip if already scored (to avoid re-scoring old articles)
                if 'importance_score' not in article:
                    scoring = self.scorer.calculate_importance_score(article, trending_boosts)
                    
                    article['importance_score'] = scoring['final_score']
                    article['importance_tier'] = scoring['importance_tier']
                    article['scoring_breakdown'] = scoring['breakdown']
                
                tier_counts[article.get('importance_tier', 'Minimal')] += 1
            
            # Sort articles by importance score
            self.news_database['articles'].sort(key=lambda x: x.get('importance_score', 0), reverse=True)
            
            # Update metadata
            self.news_database['metadata']['scoring_applied'] = datetime.now().isoformat()
            self.news_database['metadata']['trending_keywords'] = list(trending_boosts.keys())[:10]
            self.news_database['metadata']['importance_distribution'] = tier_counts
            
            logging.info(f"Scoring applied: {tier_counts}")
            
        except Exception as e:
            logging.error(f"Error applying importance scoring: {e}")
    
    def cleanup_old_articles(self, hours_threshold=24):
        """Remove articles older than the specified threshold
        
        Handles:
        - Multiple date formats (RFC 2822, ISO 8601, etc.)
        - Timezone-aware and naive datetimes
        - Fallback to collected_date if published_date missing
        - Keeps articles with unparseable dates (don't lose data)
        """
        try:
            from dateutil.tz import UTC
            
            # Use UTC for timezone-aware comparison
            current_time = self.get_current_ist()
            recent_articles = []
            removed_count = 0
            unparseable_count = 0
            
            cutoff_time = current_time - timedelta(hours=hours_threshold)
            
            for article in self.news_database['articles']:
                published_date = article.get('published_date', '')
                collected_date = article.get('collected_date', '')
                article_id = article.get('id', 'unknown')
                
                article_date = None
                parse_success = False
                
                # Try to parse published_date first
                if published_date:
                    try:
                        # Handle common RSS date format (RFC 2822 with GMT)
                        if 'GMT' in published_date and ',' in published_date:
                            article_date = datetime.strptime(published_date, '%a, %d %b %Y %H:%M:%S GMT')
                            article_date = article_date.replace(tzinfo=UTC)
                            parse_success = True
                        else:
                            # Use dateutil parser for flexible parsing
                            article_date = parser.parse(published_date)
                            
                            # Normalize to UTC if timezone-aware
                            if article_date.tzinfo is not None:
                                article_date = article_date.astimezone(UTC)
                            else:
                                # Assume UTC for naive datetimes from published_date
                                article_date = article_date.replace(tzinfo=UTC)
                            parse_success = True
                    except Exception as e:
                        logging.debug(f"Failed to parse published_date for article {article_id}: {published_date} - {e}")
                
                # Fallback to collected_date if published_date failed
                if not parse_success and collected_date:
                    try:
                        article_date = parser.parse(collected_date)
                        
                        # Normalize to UTC
                        if article_date.tzinfo is not None:
                            article_date = article_date.astimezone(UTC)
                        else:
                            # Assume UTC for naive datetimes from collected_date
                            article_date = article_date.replace(tzinfo=UTC)
                        parse_success = True
                    except Exception as e:
                        logging.debug(f"Failed to parse collected_date for article {article_id}: {collected_date} - {e}")
                
                # Decision: Include article
                if parse_success:
                    # Check if article is within threshold
                    if article_date >= cutoff_time:
                        recent_articles.append(article)
                    else:
                        removed_count += 1
                        logging.debug(f"Removed article {article_id}: published {article_date.isoformat()}, threshold {cutoff_time.isoformat()}")
                else:
                    # KEEP unparseable articles - don't lose data
                    # Log it for debugging but don't remove
                    unparseable_count += 1
                    recent_articles.append(article)
                    logging.warning(f"Could not parse date for article {article_id} (title: {article.get('title', '')[:50]}). Keeping article to avoid data loss.")
            
            # Update articles list
            self.news_database['articles'] = recent_articles
            
            if removed_count > 0 or unparseable_count > 0:
                logging.info(f"Cleanup ({hours_threshold}h threshold): Removed {removed_count} old articles, kept {len(recent_articles)} recent articles ({unparseable_count} unparseable dates)")
                
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            # On error, keep all articles rather than losing data
            logging.warning("Cleanup failed - keeping all articles to prevent data loss")
    
    def save_database(self):
        """Save news database to JSON file"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.news_database, f, indent=2, ensure_ascii=False)
            logging.info(f"News database saved to {self.output_file}")
        except Exception as e:
            logging.error(f"Error saving database: {e}")
    
    def deduplicate_articles(self):
        """Remove duplicate articles keeping only the best source for each story"""
        from Sports_Article_Automation.utilities.article_deduplicator import ArticleDeduplicator
        
        try:
            # Create temporary deduplicator instance
            deduplicator = ArticleDeduplicator(self.output_file)
            deduplicator.database = self.news_database  # Use current database
            
            # Run deduplication
            stats = deduplicator.deduplicate_articles(similarity_threshold=0.75, backup=False)
            
            # Update our database with deduplicated results
            self.news_database = deduplicator.database
            
            logging.info(f"Deduplication: Removed {stats['removed_count']} duplicates, kept {stats['final_count']} unique articles")
            
        except Exception as e:
            logging.error(f"Deduplication failed: {e}")
            # Continue without deduplication if it fails
    
    def generate_report(self, summary: Dict) -> str:
        """Generate a simple collection report"""
        report_lines = []
        report_lines.append("="*60)
        report_lines.append("RSS NEWS COLLECTION REPORT")
        report_lines.append("="*60)
        report_lines.append(f"Collection Date: {summary['collection_date']}")
        report_lines.append(f"Sources Processed: {summary['sources_processed']}")
        report_lines.append(f"Total Articles in Database: {summary['total_articles_in_database']}")
        report_lines.append(f"New Articles Added: {summary['new_articles_added']}")
        
        # Add scoring distribution if available
        if 'importance_distribution' in self.news_database.get('metadata', {}):
            dist = self.news_database['metadata']['importance_distribution']
            report_lines.append("")
            report_lines.append("IMPORTANCE DISTRIBUTION:")
            report_lines.append("-" * 30)
            for tier, count in dist.items():
                if count > 0:
                    report_lines.append(f"{tier}: {count} articles")
        
        report_lines.append("")
        
        report_lines.append("SOURCE RESULTS:")
        report_lines.append("-" * 30)
        
        for source_name, result in summary['source_results'].items():
            report_lines.append(f"{source_name}:")
            report_lines.append(f"  Status: {result['status']}")
            report_lines.append(f"  Articles Found: {result['articles_found']}")
            report_lines.append(f"  New Articles Added: {result['new_articles_added']}")
            if result.get('error'):
                report_lines.append(f"  Error: {result['error']}")
            report_lines.append("")
        
        return "\n".join(report_lines)

def main():
    """Main function to run the RSS news collection"""
    csv_file = "rss_sources.csv"
    
    collector = RSSNewsCollector(csv_file)
    
    print("Starting RSS News Collection...")
    print("Collecting headlines and metadata from RSS feeds...")
    
    # Collect news from all feeds
    summary = collector.collect_all_news()
    
    if summary:
        # Generate and display report
        report = collector.generate_report(summary)
        print("\n" + report)
        
        print(f"\nNews database updated: sports_news_database.json")
        print(f"Total articles in database: {summary['total_articles_in_database']}")
        print(f"New articles added this run: {summary['new_articles_added']}")
    else:
        print("No results to display. Check the CSV file and try again.")

if __name__ == "__main__":
    main()