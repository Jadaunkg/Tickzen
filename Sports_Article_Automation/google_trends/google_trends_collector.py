"""
Google Trends Data Collector (Selenium-based)
Collects real trending search queries using Selenium with headless Chrome
Stores data in JSON format with scoring metadata
Integrated with Firebase for cloud backup
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time
import hashlib
import re

logger = logging.getLogger(__name__)

# Lazy import - will be loaded when needed
SELENIUM_AVAILABLE = True
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    import undetected_chromedriver as uc
except ImportError as e:
    logger.warning(f"Selenium not fully available at import time: {e}")
    SELENIUM_AVAILABLE = False

# Configuration
TRENDS_CACHE_TIMEOUT = 3600  # 1 hour in seconds
TRENDS_FALLBACK_TIMEOUT = 86400  # 24 hours in seconds
MAX_DAILY_API_CALLS = 20  # Rate limiting
COLLECTION_INTERVAL = 3600  # Collect every hour
REQUEST_DELAY = 5  # Delay between requests (seconds) - increased to avoid 429
MAX_RETRIES = 2  # Number of retries on failure
RETRY_DELAY = 10  # Delay between retries (seconds) - increased

# Categories for sports (primary) and others
TRENDS_CATEGORIES = {
    'sports': 17,  # Category 17 is all sports
    'technology': 13,
    'entertainment': 26,
    'business': 12,
    'health': 45
}

REGIONS = ['US', 'GB', 'CA', 'AU', 'IN']


class GoogleTrendsCollector:
    """Collect real Google Trends data using Selenium with headless Chrome"""
    
    def __init__(self, database_path: Optional[str] = None, project_root: Optional[str] = None):
        """
        Initialize the Google Trends collector

        Args:
            database_path: Path to google_trends_database.json
            project_root: Path to project root for data storage
        """
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent

        self.project_root = Path(project_root)

        if database_path is None:
            database_path = self.project_root / "google_trends_database.json"

        self.database_path = Path(database_path)
        self.trends_data = []
        self.last_collection_time = None
        self.collection_count = 0
        self.use_demo_mode = False
        self.driver = None
        
        logger.info("✅ GoogleTrendsCollector initialized")
        
        # Load existing data
        self._load_database()
    
    
    def _init_selenium_driver(self):
        """Initialize Selenium Chrome driver in headless mode"""
        try:
            # Attempt 1: Undetected Chromedriver
            try:
                import undetected_chromedriver as uc
                from webdriver_manager.chrome import ChromeDriverManager
                
                self.driver = uc.Chrome(version_main=None, use_subprocess=False)
                self.driver.set_page_load_timeout(30)
                logger.info("✅ Undetected Chrome driver initialized")
                return True
            except Exception as uc_e:
                logger.warning(f"Undetected driver failed or not installed: {uc_e}")
            
            # Attempt 2: Standard Selenium
            logger.info("⚠️  Falling back to standard Selenium...")
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                import platform
                
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--disable-extensions')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--disable-web-security')
                chrome_options.add_argument('--allow-running-insecure-content')
                chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                
                # Force win64 architecture if on Windows 64-bit
                os_type = platform.machine().lower()
                if 'amd64' in os_type or 'x86_64' in os_type:
                    logger.info(f"🖥️  Detected {os_type} architecture - using win64 ChromeDriver")
                    chrome_manager = ChromeDriverManager(os_type="win64")
                else:
                    chrome_manager = ChromeDriverManager()
                
                service = Service(chrome_manager.install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_page_load_timeout(30)
                logger.info("✅ Standard Chrome driver initialized (fallback)")
                return True
            except Exception as std_e:
                logger.error(f"❌ Standard Selenium failed: {std_e}")
                
                # Attempt 3: Try with explicit executable path workaround
                logger.info("🔧 Attempting ChromeDriver executable path workaround...")
                try:
                    import glob
                    import os
                    
                    # Find the chromedriver executable in cache
                    wdm_path = os.path.expanduser("~/.wdm/drivers/chromedriver/*/")
                    possible_drivers = glob.glob(wdm_path + "**/chromedriver.exe", recursive=True)
                    
                    if not possible_drivers:
                        # Try Windows cache path
                        wdm_path = os.path.expanduser("~\\.wdm\\drivers\\chromedriver\\*\\")
                        possible_drivers = glob.glob(wdm_path + "**\\chromedriver.exe", recursive=True)
                    
                    if possible_drivers:
                        driver_path = possible_drivers[0]
                        logger.info(f"🎯 Found ChromeDriver at: {driver_path}")
                        
                        service = Service(driver_path)
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        self.driver.set_page_load_timeout(30)
                        logger.info("✅ ChromeDriver initialized with explicit path")
                        return True
                    else:
                        logger.error("❌ No ChromeDriver found in cache")
                        
                except Exception as path_e:
                    logger.error(f"❌ Explicit path attempt failed: {path_e}")
            
            # If we get here, both failed
            self.use_demo_mode = True
            return False
            
        except Exception as e:
            logger.error(f"❌ Critical error in driver initialization: {e}")
            self.use_demo_mode = True
            return False
    
    def _close_driver(self):
        """Close Selenium driver"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except Exception as e:
            logger.error(f"Error closing driver: {e}")

    def _load_database(self) -> None:
        """Load existing trends data from JSON file"""
        try:
            if self.database_path.exists():
                with open(self.database_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.trends_data = data.get('trends', [])
                        self.last_collection_time = data.get('last_updated')
                    else:
                        self.trends_data = data
                logger.info(f"✅ Loaded {len(self.trends_data)} trends from database")
            else:
                logger.info("📝 Creating new trends database")
                self._initialize_database()
        except Exception as e:
            logger.error(f"❌ Error loading database: {e}")
            self.trends_data = []
            self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize empty trends database"""
        try:
            initial_data = {
                'trends': [],
                'last_updated': datetime.utcnow().isoformat(),
                'metadata': {
                    'total_collections': 0,
                    'total_trends_collected': 0,
                    'categories_tracked': list(TRENDS_CATEGORIES.keys()),
                    'regions_tracked': REGIONS
                }
            }
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Initialized trends database at {self.database_path}")
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")

    def _save_database(self) -> None:
        """Save trends data to JSON file"""
        try:
            data = {
                'trends': self.trends_data,
                'last_updated': datetime.utcnow().isoformat(),
                'metadata': {
                    'total_collections': self.collection_count,
                    'total_trends_collected': len(self.trends_data),
                    'categories_tracked': list(TRENDS_CATEGORIES.keys()),
                    'regions_tracked': REGIONS
                }
            }
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Saved {len(self.trends_data)} trends to database")
        except Exception as e:
            logger.error(f"❌ Error saving database: {e}")

    
    def collect_daily_trends(self, category: str = 'sports', region: str = 'US') -> Dict:
        """
        Collect daily trends using Selenium
        
        Args:
            category: Trend category (sports, technology, etc.)
            region: Geographic region code (US, GB, CA, etc.)
        
        Returns:
            Dictionary with collection results
        """
        # Enforce Sports/US only as requested
        category = 'sports'
        region = 'US'
        
        result = {
            'category': category,
            'region': region,
            'success': False,
            'trends_count': 0,
            'new_trends': 0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"\n🔍 Collecting {category} trends for {region}...")
        
        # Try to fetch real data from Google Trends
        for attempt in range(MAX_RETRIES + 1):
            try:
                # Initialize driver if needed
                if self.driver is None:
                    if not self._init_selenium_driver():
                        raise Exception("Failed to initialize driver")
                
                # Fetch from Google Trends
                trends = self._fetch_from_google_trends(category, region)
                
                if trends:
                    # Add trends to database
                    self._add_trends_to_database(trends, category, region)
                    result['success'] = True
                    result['trends_count'] = len(trends)
                    result['new_trends'] = len(trends)
                    logger.info(f"✅ Successfully collected {len(trends)} real trends for {category}/{region}")
                    return result
                    
            except Exception as e:
                delay = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"⚠️  Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}")
                time.sleep(delay)
        
        logger.error(f"❌ Failed to fetch {category} trends after {MAX_RETRIES + 1} attempts")
        return result
    
    def _fetch_from_google_trends(self, category: str, region: str) -> Optional[List[Dict]]:
        """
        Fetch real Google Trends data using Selenium
        
        Args:
            category: Trend category
            region: Region code
        
        Returns:
            List of trend dictionaries or None if failed
        """
        try:
            if self.driver is None:
                return None
            
            # Enforce US Sports (Category 17) for last 4 hours
            url = f"https://trends.google.com/trending?geo=US&category=17&hours=4"
            
            logger.info(f"🌐 Loading Google Trends Daily Trends: {url}")
            self.driver.get(url)
            
            # Wait for trends to load
            wait = WebDriverWait(self.driver, 20)
            
            try:
                # Try waiting for the main content div
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[role='gridcell']")))
                logger.info("✅ Found gridcell elements")
            except:
                try:
                    # Fallback: wait for any title or heading elements
                    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span[data-nosnippet]")))
                    logger.info("✅ Found nosnippet elements")
                except:
                    logger.warning("⚠️  Timeout waiting for trends to load, continuing anyway...")
            
            time.sleep(REQUEST_DELAY)
            
            # Extract trend items from Daily Trends section
            trends = []
            unique_trends = set()  # Avoid duplicates
            
            # Scroll down to load more trends dynamically
            logger.info("📜 Scrolling to load additional trends...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 5
            
            while scroll_attempts < max_scroll_attempts:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for new content to load
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    logger.info("📜 Reached end of page")
                    break
                last_height = new_height
                scroll_attempts += 1
                logger.info(f"📜 Scroll attempt {scroll_attempts}, new content loaded")
            
            # Strategy 1: Try to find elements with specific data attributes or classes
            try:
                # Google Trends renders trends in list items or cards
                # Look for various selectors that contain trend data
                title_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    "a[href*='/trends/explore'], "  # Links to explore page
                    "div[aria-label*='trend'], "     # Elements with aria labels
                    "span[role='link'], "            # Span links
                    "li[role='listitem'] span, "     # List item spans
                    ".trend-item, "                  # Trend item class
                    "[data-trend-name], "            # Data attribute
                    "td:first-child, "               # Table first column
                    "div[title]"                     # Div with title
                )
                
                logger.info(f"Found {len(title_elements)} potential trend elements")
                
                for idx, element in enumerate(title_elements): # Check ALL elements, not just first 40
                    try:
                        # Try to get text from the element or its aria-label
                        query = element.text.strip() if element.text else element.get_attribute('aria-label')
                        if not query:
                            query = element.get_attribute('title')
                        
                        if not query:
                            # Try to get text from child elements
                            try:
                                query = element.find_element(By.XPATH, ".//span | .//a").text.strip()
                            except:
                                pass
                        
                        if not query:
                            continue

                        query = query.split('\n')[0].strip()  # Get first line only
                        
                        # Clean and validate the trend
                        if query and len(query) > 2 and len(query) < 200:
                            # Filter out numbers, volume strings, and common UI text
                            if (not query.isdigit() and 
                                not query.startswith('+') and 
                                not re.match(r'^\d+[K|M]\+$', query) and
                                query not in unique_trends):
                                
                                # Remove common noise patterns
                                if not any(x in query.lower() for x in ['sign in', 'search interest', 'rising', 'explore', 'visits', 'share', 'more_vert', 'go back', 'filters', 'daily search trends', 'realtime search trends']):
                                    unique_trends.add(query)
                                    trends.append({
                                        'query': query,
                                        'rank': len(trends) + 1,
                                        'category': category,
                                        'region': region,
                                        'collected_date': datetime.utcnow().isoformat(),
                                        'source': 'google_trends_selenium',
                                        'importance_score': max(100 - (len(trends) * 5), 40)  # Reduced penalty for ranking
                                    })
                                    logger.info(f"  📍 Trend {len(trends)}: {query}")
                    except Exception as e:
                        continue
            except Exception as e:
                logger.warning(f"⚠️  Could not find trends with primary selector: {e}")
            
            # Strategy 2: Text Parsing (Fallback) - More effective extraction
            if len(trends) < 5:
                logger.info("📄 Trying to extract trends from page HTML using comprehensive text analysis...")
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    
                    # Split into lines and clean
                    lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                    
                    # Define comprehensive exclusion lists
                    ui_keywords = {
                        'trends', 'home', 'explore', 'search interest', 'updated', 'past',
                        'hours', 'you might like', 'scroll', 'sign in', 'related searches',
                        'trending', 'more', 'browse', 'trend breakdown', 'did you know',
                        'searches related to', 'rising searches', 'year-end review',
                        'search volume', 'started', 'active', 'rows per page',
                        'by relevance', 'export', 'sort', 'category', 'language',
                        'privacy', 'terms', 'about', 'help', 'send feedback', 'got it',
                        'english', 'united states', 'this site uses cookies'
                    }
                    
                    # Material icons and special characters
                    icon_keywords = {
                        'location_on', 'calendar_month', 'grid_3x3', 'sort', 'ios_share',
                        'search', 'info', 'help', 'language', 'arrow_upward', 'arrow_downward',
                        'trending_up', 'trending_down', 'more_vert', 'timelapse'
                    }
                    
                    # Time indicators
                    time_keywords = {
                        'hour ago', 'hours ago', 'minutes ago', 'minute ago', 'day ago',
                        'days ago', 'week ago', 'weeks ago', 'lasted', 'peak', 'january',
                        'february', 'march', 'april', 'may', 'june', 'july', 'august',
                        'september', 'october', 'november', 'december'
                    }
                    
                    # Footer and legal text
                    footer_keywords = {
                        'privacy', 'terms', 'about', 'help', 'feedback', 'cookies',
                        'site uses', 'deliver', 'quality', 'services', 'analyze traffic'
                    }
                    
                    # Process all lines to find trend keywords
                    for line in lines:
                        # Skip if empty or too short/long
                        if not line or len(line) < 3 or len(line) > 150:
                            continue
                        
                        # Skip pure numbers, percentages, symbols
                        if (re.match(r'^[\d\+\-%\.\,\–\s]+$', line) or
                            re.match(r'^\d+[KMB]\+?$', line.replace(',', ''))):
                            continue
                        
                        line_lower = line.lower()
                        
                        # Skip if contains UI/time/footer keywords
                        if (any(keyword in line_lower for keyword in ui_keywords | time_keywords | footer_keywords) or
                            any(icon in line for icon in icon_keywords)):
                            continue
                        
                        # Skip pagination indicators (e.g., "1–21 of 21")
                        if re.match(r'^\d+[–\-]\d+\s+of\s+\d+', line):
                            continue
                        
                        # Skip lines with special dropdown indicators
                        if '▾' in line or '▸' in line:
                            continue
                        
                        # Skip very short common words that are likely UI
                        if len(line.split()) == 1 and line_lower in {'search', 'sort', 'export', 'import', 'filter', 'settings', 'info', 'help'}:
                            continue
                        
                        # Valid trend keyword found
                        if line not in unique_trends:
                            unique_trends.add(line)
                            trends.append({
                                'query': line,
                                'rank': len(trends) + 1,
                                'category': category,
                                'region': region,
                                'collected_date': datetime.utcnow().isoformat(),
                                'source': 'google_trends_collector',
                                'importance_score': max(100 - (len(trends) * 5), 40)
                            })
                            logger.info(f"  📍 Trend {len(trends)}: {line}")
                        
                except Exception as e:
                    logger.warning(f"⚠️  Could not extract from page HTML: {e}")
            
            if trends:
                logger.info(f"📊 Found {len(trends)} trends from Google Trends")
                return trends
            else:
                # If no trends found, might be a page loading issue
                logger.warning(f"⚠️  No trend elements found on page, returning None to retry")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching from Google Trends: {e}")
            return None
    
    def _add_trends_to_database(self, trends: List[Dict], category: str, region: str) -> None:
        """Add trends to the database, replacing old trends with new ones"""
        # Clear old trends for this category and region
        self.trends_data = [
            t for t in self.trends_data 
            if not (t.get('category') == category and t.get('region') == region)
        ]
        
        # Add all new trends (they will replace the old ones)
        self.trends_data.extend(trends)
        new_count = len(trends)
        
        logger.info(f"✅ Replaced database with {new_count} new trends for {category}/{region}")
    
    def collect_related_queries(self, query: str, region: str = 'US') -> List[Dict]:
        """Fetch related search queries"""
        try:
            if not self.driver:
                self._init_selenium_driver()
            
            if not self.driver:
                return []
            
            url = f"https://trends.google.com/trends/explore?q={query}&geo={region}"
            self.driver.get(url)
            time.sleep(REQUEST_DELAY)
            
            # Try to extract related queries
            related = []
            try:
                related_elements = self.driver.find_elements(By.XPATH, "//span[contains(@class, 'related')]")
                for elem in related_elements[:5]:
                    try:
                        related_query = elem.text
                        if related_query:
                            related.append({
                                'query': related_query,
                                'original_query': query,
                                'source': 'google_trends'
                            })
                    except:
                        continue
            except:
                pass
            
            return related
        except Exception as e:
            logger.error(f"Error fetching related queries: {e}")
            return []
    
    def run_collection_pipeline(self) -> Dict:
        """Run the complete collection pipeline for all categories"""
        logger.info("\n" + "="*70)
        logger.info("🌍 STARTING GOOGLE TRENDS COLLECTION PIPELINE")
        logger.info("="*70)
        
        results = {
            'success': False,
            'timestamp': datetime.utcnow().isoformat(),
            'categories_collected': [],
            'total_new_trends': 0,
            'total_trends_collected': 0,
            'by_category': {},
            'errors': []
        }
        
        initial_count = len(self.trends_data)
        
        try:
            # Collect trends for each category
            # Enforce Sports only as requested
            target_categories = ['sports']
            
            for category in target_categories:
                logger.info(f"\n📌 Collecting {category.upper()} trends...")
                
                category_results = {'regions': {}}
                
                # Only collect for US (sports only)
                target_regions = ['US']
                
                for region in target_regions:
                    try:
                        result = self.collect_daily_trends(category, region)
                        category_results['regions'][region] = result
                        results['total_new_trends'] += result.get('new_trends', 0)
                    except Exception as e:
                        logger.error(f"Error collecting {category}/{region}: {e}")
                        results['errors'].append(f"{category}/{region}: {str(e)}")
                
                # Save after each category
                self._save_database()
                results['by_category'][category] = category_results
                results['categories_collected'].append(category)
        
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results['errors'].append(str(e))
        
        finally:
            # Close driver
            self._close_driver()
        
        # Final stats
        results['total_trends_collected'] = len(self.trends_data)
        final_new = len(self.trends_data) - initial_count
        
        logger.info("\n" + "="*70)
        logger.info("✅ Collection Pipeline Complete")
        logger.info(f"   Total New Trends: {final_new:<3}")
        logger.info(f"   Total Trends in Database: {len(self.trends_data)}")
        logger.info("="*70)
        
        results['success'] = final_new > 0
        return results
    
    def get_trends(self, category: Optional[str] = None, region: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get collected trends with optional filtering"""
        trends = self.trends_data
        
        if category and category != 'all':
            trends = [t for t in trends if t.get('category') == category]
        
        if region and region != 'all':
            trends = [t for t in trends if t.get('region') == region]
        
        # Sort by rank
        trends = sorted(trends, key=lambda x: x.get('rank', 999))
        
        return trends[:limit]
    
    def get_all_trends(self, category: Optional[str] = None, region: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get all collected trends with optional filtering (alias for get_trends)"""
        return self.get_trends(category=category, region=region, limit=limit)
    
    def export_report(self, output_format: str = 'json') -> Dict:
        """Export trends report"""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_trends': len(self.trends_data),
            'categories': list(TRENDS_CATEGORIES.keys()),
            'regions': REGIONS,
            'trends_by_category': {},
            'last_updated': self.last_collection_time
        }
        
        for category in TRENDS_CATEGORIES.keys():
            cat_trends = [t for t in self.trends_data if t.get('category') == category]
            report['trends_by_category'][category] = len(cat_trends)
        
        return report
    
    def _calculate_importance_score(self, rank: int) -> float:
        """Calculate importance score based on rank"""
        if rank < 5:
            return 95.0
        elif rank < 10:
            return 85.0
        elif rank < 15:
            return 75.0
        else:
            return 65.0
    
    def _find_trend(self, query: str, region: str) -> Optional[Dict]:
        """Find a trend by query and region"""
        for trend in self.trends_data:
            if trend.get('query', '').lower() == query.lower() and trend.get('region') == region:
                return trend
        return None
    
    def _update_trend(self, query: str, region: str, new_data: Dict) -> None:
        """Update an existing trend"""
        for i, trend in enumerate(self.trends_data):
            if trend.get('query', '').lower() == query.lower() and trend.get('region') == region:
                new_data['collected_date'] = trend.get('collected_date')
                self.trends_data[i] = new_data
                break
    
    def clear_old_trends(self, days: int = 30) -> int:
        """
        Remove trends older than specified days

        Args:
            days: Days to keep (default 30)

        Returns:
            Number of trends removed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        initial_count = len(self.trends_data)

        self.trends_data = [
            t for t in self.trends_data
            if datetime.fromisoformat(t.get('collected_date', '')) > cutoff_date
        ]

        removed = initial_count - len(self.trends_data)
        if removed > 0:
            self._save_database()
            logger.info(f"🗑️  Removed {removed} trends older than {days} days")

        return removed
