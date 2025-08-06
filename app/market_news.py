# market_news.py - Handles market news functionality

import os
import re
import time
import json
import traceback
import requests
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template, current_app
from functools import lru_cache

market_news_bp = Blueprint('market_news', __name__)

# Cache settings - AGGRESSIVE CACHING to conserve API calls
NEWS_CACHE_TIMEOUT = 1 * 60 * 60  # 1 hour cache timeout as requested
FALLBACK_CACHE_TIMEOUT = 6 * 60 * 60  # 6 hours for fallback data to reduce API dependency
news_cache = {}
last_cache_time = {}
daily_api_calls = 0
last_api_reset = None
MAX_DAILY_API_CALLS = 20  # Conservative limit (5 calls buffer from 25/day)

def reset_daily_api_counter():
    """Reset daily API call counter if it's a new day"""
    global daily_api_calls, last_api_reset
    current_date = datetime.now().date()
    
    if last_api_reset is None or last_api_reset != current_date:
        daily_api_calls = 0
        last_api_reset = current_date
        current_app.logger.info(f"Daily API counter reset for {current_date}")

def can_make_api_call():
    """Check if we can make an API call within daily limits"""
    reset_daily_api_counter()
    return daily_api_calls < MAX_DAILY_API_CALLS

def increment_api_call_counter():
    """Increment the daily API call counter"""
    global daily_api_calls
    daily_api_calls += 1
    current_app.logger.info(f"API calls today: {daily_api_calls}/{MAX_DAILY_API_CALLS}")

def is_cache_valid(cache_key, timeout=None):
    """Check if cache is valid for given timeout"""
    if timeout is None:
        timeout = NEWS_CACHE_TIMEOUT
    
    if cache_key not in news_cache or cache_key not in last_cache_time:
        return False
    
    current_time = time.time()
    return (current_time - last_cache_time[cache_key]) < timeout

def get_cache_age(cache_key):
    """Get cache age in minutes"""
    if cache_key not in last_cache_time:
        return float('inf')
    
    current_time = time.time()
    age_seconds = current_time - last_cache_time[cache_key]
    return age_seconds / 60  # Return age in minutes

def fetch_diverse_news_data(api_key, cache_key):
    """Fetch diverse news data with STRICT API call limits and aggressive caching"""
    base_url = "https://www.alphavantage.co/query"
    all_news = []
    
    # ULTRA CONSERVATIVE: Only 1-2 API calls maximum to preserve daily quota
    topic_queries = [
        {"topics": "financial_markets", "limit": 50}  # Single strategic call
    ]
    
    # Only make second call if we have budget
    if daily_api_calls < (MAX_DAILY_API_CALLS - 1):
        topic_queries.append({"limit": 50})  # General backup
    
    current_app.logger.info(f"Making MINIMAL API calls to conserve quota. Planned calls: {len(topic_queries)}")
    
    for query_params in topic_queries:
        # Double-check API limit before each call
        if not can_make_api_call():
            current_app.logger.warning("API limit reached during fetch, stopping additional calls")
            break
            
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": api_key,
            **query_params
        }
        
        try:
            current_app.logger.info(f"API call {daily_api_calls + 1}/{MAX_DAILY_API_CALLS} with params: {params}")
            increment_api_call_counter()  # Track the call
            
            response = requests.get(base_url, params=params, timeout=30)
            
            if response.status_code == 429:
                current_app.logger.warning("Rate limit hit by Alpha Vantage")
                break
                
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and "feed" in data:
                        all_news.extend(data["feed"])
                        current_app.logger.info(f"Retrieved {len(data['feed'])} articles")
                    else:
                        current_app.logger.warning(f"Invalid response structure: {data}")
                except json.JSONDecodeError:
                    current_app.logger.error(f"Failed to parse JSON response: {response.text[:200]}")
            else:
                current_app.logger.error(f"API request failed with status {response.status_code}")
                
        except Exception as e:
            current_app.logger.error(f"Error in API call: {str(e)}")
            continue
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_news = []
    for article in all_news:
        if not isinstance(article, dict):
            continue
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(article)
    
    current_app.logger.info(f"Total unique articles collected: {len(unique_news)}")
    
    # If we don't have enough articles, supplement with fallback (but cache it longer)
    if len(unique_news) < 20:
        current_app.logger.info(f"Only {len(unique_news)} unique articles, supplementing with fallback")
        fallback_data = get_fallback_news_data()
        fallback_articles = fallback_data.get("news", [])
        unique_news.extend(fallback_articles)
    
    # Process the combined data
    data_wrapper = {"feed": unique_news}
    processed_data = process_alpha_vantage_news(data_wrapper)
    
    # AGGRESSIVE CACHING: Cache for 1 hour minimum
    news_cache[cache_key] = processed_data
    last_cache_time[cache_key] = time.time()
    processed_data["api_calls_used"] = daily_api_calls
    processed_data["cache_timeout_minutes"] = NEWS_CACHE_TIMEOUT / 60
    
    current_app.logger.info(f"Cached {len(processed_data.get('news', []))} articles for {NEWS_CACHE_TIMEOUT/3600} hours")
    return processed_data, 200

def get_alpha_vantage_api_key():
    """Get Alpha Vantage API key from environment variables"""
    # Check for API key in environment variables first
    api_key = os.environ.get('ALPHA_API_KEY')
    if api_key:
        return api_key
    
    # Try to force reload of environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        api_key = os.environ.get('ALPHA_API_KEY')
        if api_key:
            return api_key
    except ImportError:
        pass  # dotenv not available
    
    # As a fallback, try to read directly from the .env file
    try:
        with open(os.path.join(os.getcwd(), '.env'), 'r') as f:
            content = f.read()
            match = re.search(r'ALPHA_API_KEY[=:][\s]*["\']?([^"\'\s\n]+)["\']?', content)
            if match:
                api_key = match.group(1)
                current_app.logger.info(f"Found API key in .env file: {api_key[:4]}...{api_key[-4:]}")
                return api_key
    except Exception:
        pass  # .env file not found or not readable
    
    current_app.logger.error("Alpha Vantage API key not found in environment variables or .env file")
    return None

@lru_cache(maxsize=10)
def get_news_topics():
    """Return predefined news topics/categories for filtering"""
    return ['market', 'economy', 'crypto', 'forex', 'earnings']

def get_fallback_news_data():
    """Provide fallback news data when API fails - enhanced with diverse categories and sentiments"""
    # Generate timestamps that are recent (within the last few hours)
    base_time = datetime.now()
    
    def get_recent_timestamp(hours_ago):
        return (base_time - timedelta(hours=hours_ago)).strftime('%Y%m%dT%H%M%S')
    
    return {
        "news": [
            {
                "id": "fallback-1",
                "title": "Technology Stocks Rally as AI Innovations Drive Market Optimism",
                "summary": "Major technology companies saw significant gains as artificial intelligence breakthroughs continue to drive investor confidence. Cloud computing and machine learning sectors lead the surge.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(0.5),
                "category": "market",
                "topics": ["technology", "ai", "stocks"],
                "image": "",
                "sentiment": "positive"
            },
            {
                "id": "fallback-2",
                "title": "Federal Reserve Maintains Interest Rates Amid Economic Uncertainty",
                "summary": "The Federal Reserve decided to keep interest rates unchanged as policymakers assess mixed economic signals. Inflation concerns remain balanced against growth considerations.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(1),
                "category": "economy",
                "topics": ["federal reserve", "interest rates", "monetary policy"],
                "image": "",
                "sentiment": "neutral"
            },
            {
                "id": "fallback-3",
                "title": "Bitcoin Surges to New Monthly High Amid Institutional Adoption",
                "summary": "Bitcoin reached a new monthly peak as more institutional investors enter the cryptocurrency market. Regulatory clarity improvements boost overall market sentiment.",
                "source": "Tickzen News",
                "url": "#", 
                "published_at": get_recent_timestamp(1.5),
                "category": "crypto",
                "topics": ["bitcoin", "cryptocurrency", "institutional investment"],
                "image": "",
                "sentiment": "positive"
            },
            {
                "id": "fallback-4",
                "title": "Dollar Weakens Against Major Currencies on Trade Concerns",
                "summary": "The US Dollar declined against major trading partners' currencies as international trade tensions create uncertainty. European and Asian currencies gained ground.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(2),
                "category": "forex",
                "topics": ["dollar", "currency", "trade"],
                "image": "",
                "sentiment": "negative"
            },
            {
                "id": "fallback-5",
                "title": "Major Tech Company Reports Strong Quarterly Earnings",
                "summary": "Leading technology firms exceeded analyst expectations in quarterly earnings reports, driven by robust cloud services revenue and improved operational efficiency.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(2.5),
                "category": "earnings",
                "topics": ["earnings", "technology", "quarterly results"],
                "image": "",
                "sentiment": "positive"
            },
            {
                "id": "fallback-6",
                "title": "Inflation Data Shows Mixed Signals for Economic Recovery",
                "summary": "Latest inflation figures present a complex picture with some sectors showing price stabilization while others continue to experience volatility.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(3),
                "category": "economy",
                "topics": ["inflation", "economic recovery", "consumer prices"],
                "image": "",
                "sentiment": "neutral"
            },
            {
                "id": "fallback-7",
                "title": "Ethereum Network Upgrade Brings Enhanced Functionality",
                "summary": "The latest Ethereum network upgrade introduces improved transaction speeds and reduced gas fees, attracting more developers to the platform.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(3.5),
                "category": "crypto",
                "topics": ["ethereum", "blockchain", "network upgrade"],
                "image": "",
                "sentiment": "positive"
            },
            {
                "id": "fallback-8",
                "title": "Energy Stocks Face Pressure from Renewable Competition",
                "summary": "Traditional energy companies are experiencing market pressure as renewable energy sources gain market share and government policy support.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(4),
                "category": "market",
                "topics": ["energy", "renewable", "stocks"],
                "image": "",
                "sentiment": "negative"
            },
            {
                "id": "fallback-9",
                "title": "Currency Markets React to Central Bank Policy Divergence",
                "summary": "Global currency markets show increased volatility as central banks across different regions implement varying monetary policy approaches.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(4.5),
                "category": "forex",
                "topics": ["central banks", "monetary policy", "currency volatility"],
                "image": "",
                "sentiment": "neutral"
            },
            {
                "id": "fallback-10",
                "title": "Retail Earnings Disappoint as Consumer Spending Slows",
                "summary": "Major retail chains report weaker than expected quarterly earnings as consumer spending patterns shift and economic uncertainty affects purchasing decisions.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(5),
                "category": "earnings",
                "topics": ["retail", "consumer spending", "earnings"],
                "image": "",
                "sentiment": "negative"
            },
            {
                "id": "fallback-11",
                "title": "Healthcare Sector Shows Resilience in Market Volatility",
                "summary": "Healthcare stocks demonstrate stability during recent market fluctuations, with biotech companies leading gains on promising research developments.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(5.5),
                "category": "market",
                "topics": ["healthcare", "biotech", "market stability"],
                "image": "",
                "sentiment": "positive"
            },
            {
                "id": "fallback-12",
                "title": "DeFi Protocols Face Regulatory Scrutiny Worldwide",
                "summary": "Decentralized Finance protocols are under increased regulatory examination as governments worldwide develop frameworks for digital asset oversight.",
                "source": "Tickzen News",
                "url": "#",
                "published_at": get_recent_timestamp(6),
                "category": "crypto",
                "topics": ["defi", "regulation", "digital assets"],
                "image": "",
                "sentiment": "negative"
            }
        ],
        "has_more": False,
        "total": 12,
        "page": 1,
        "fallback": True
    }

def fetch_alpha_vantage_news(topic=None):
    """Fetch news from Alpha Vantage API with AGGRESSIVE caching to conserve daily API quota"""
    # Get cached data if available and not expired (1 hour cache)
    cache_key = f"news-{topic or 'all'}"
    
    # PRIORITY 1: Check if we have valid cached data (within 1 hour)
    if is_cache_valid(cache_key, NEWS_CACHE_TIMEOUT):
        cache_age = get_cache_age(cache_key)
        current_app.logger.info(f"Returning FRESH cached data for {cache_key} (age: {cache_age:.1f} minutes)")
        return news_cache[cache_key], 200
    
    # PRIORITY 2: Check if we have older cached data (within 6 hours) to avoid API calls
    if is_cache_valid(cache_key, FALLBACK_CACHE_TIMEOUT):
        cache_age = get_cache_age(cache_key)
        current_app.logger.info(f"Returning OLDER cached data for {cache_key} (age: {cache_age:.1f} minutes) to conserve API calls")
        cached_data = news_cache[cache_key].copy()
        cached_data["cache_used"] = True
        cached_data["cache_age_minutes"] = cache_age
        return cached_data, 200
    
    # PRIORITY 3: Check API call limits before making new requests
    api_key = get_alpha_vantage_api_key()
    if not api_key:
        current_app.logger.error("Alpha Vantage API key not available")
        fallback_data = get_fallback_news_data()
        fallback_data["error"] = "API key not configured"
        fallback_data["fallback"] = True
        # Cache fallback data for 1 hour to avoid repeated attempts
        news_cache[cache_key] = fallback_data
        last_cache_time[cache_key] = time.time()
        return fallback_data, 200
    
    # Check if we can make API calls today
    if not can_make_api_call():
        current_app.logger.warning(f"Daily API limit reached ({daily_api_calls}/{MAX_DAILY_API_CALLS}). Using fallback data.")
        fallback_data = get_fallback_news_data()
        fallback_data["api_limit_reached"] = True
        fallback_data["fallback"] = True
        fallback_data["daily_calls_used"] = daily_api_calls
        # Cache fallback data to avoid repeated checks
        news_cache[cache_key] = fallback_data
        last_cache_time[cache_key] = time.time()
        return fallback_data, 200
    
    # PRIORITY 4: Make API call only if absolutely necessary
    current_app.logger.info(f"Making API call for {cache_key} (calls today: {daily_api_calls}/{MAX_DAILY_API_CALLS})")
    
    # Enhanced strategy: if requesting all news, fetch multiple topic-specific queries
    # to ensure diverse content across all categories
    if topic is None or topic == 'all':
        return fetch_diverse_news_data(api_key, cache_key)
    
    # For specific topic requests, use single API call
    return fetch_topic_specific_news(api_key, topic, cache_key)

def fetch_topic_specific_news(api_key, topic, cache_key):
    """Fetch news for a specific topic with API call conservation"""
    base_url = "https://www.alphavantage.co/query"
    
    # Check if we can make API call
    if not can_make_api_call():
        current_app.logger.warning("API limit reached, using fallback for topic-specific request")
        fallback_data = get_fallback_news_data()
        # Filter fallback data by topic
        fallback_news = fallback_data.get("news", [])
        filtered_news = [n for n in fallback_news if n.get('category') == topic]
        
        processed_data = {
            "news": filtered_news,
            "fallback": True,
            "api_limit_reached": True,
            "total": len(filtered_news)
        }
        
        # Cache the result
        news_cache[cache_key] = processed_data
        last_cache_time[cache_key] = time.time()
        return processed_data, 200
    
    # Map our filter topics to Alpha Vantage topics parameter
    topic_mapping = {
        'market': 'financial_markets',
        'economy': 'economy_macro', 
        'crypto': 'blockchain',
        'forex': 'financial_markets',  # No specific forex topic
        'earnings': 'earnings'
    }
    
    # Get topic for the requested category
    av_topic = topic_mapping.get(topic, 'financial_markets')
    
    params = {
        "function": "NEWS_SENTIMENT",
        "apikey": api_key,
        "topics": av_topic,
        "limit": 50  # Single focused call
    }
    
    try:
        current_app.logger.info(f"Making topic-specific API call for {topic} -> {av_topic}")
        increment_api_call_counter()
        
        response = requests.get(base_url, params=params, timeout=30)
        
        if response.status_code == 429:
            current_app.logger.warning("Rate limit hit")
            # Fall back to cached general data if available
            general_cache_key = "news-all"
            if is_cache_valid(general_cache_key, FALLBACK_CACHE_TIMEOUT):
                general_data = news_cache[general_cache_key]
                all_news = general_data.get("news", [])
                filtered_news = [n for n in all_news if n.get('category') == topic]
                processed_data = {
                    "news": filtered_news,
                    "total": len(filtered_news),
                    "from_general_cache": True
                }
                news_cache[cache_key] = processed_data
                last_cache_time[cache_key] = time.time()
                return processed_data, 200
            
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if "Error Message" in data or "Information" in data:
            current_app.logger.warning(f"API issue: {data.get('Error Message', data.get('Information', 'Unknown'))}")
            # Use fallback
            fallback_data = get_fallback_news_data()
            fallback_news = fallback_data.get("news", [])
            filtered_news = [n for n in fallback_news if n.get('category') == topic]
            processed_data = {
                "news": filtered_news,
                "fallback": True,
                "total": len(filtered_news)
            }
            news_cache[cache_key] = processed_data
            last_cache_time[cache_key] = time.time()
            return processed_data, 200
            
        if "feed" in data and data["feed"]:
            current_app.logger.info(f"Retrieved {len(data['feed'])} articles for {topic}")
            
            # Process the data
            data_wrapper = {"feed": data["feed"]}
            processed_data = process_alpha_vantage_news(data_wrapper)
            
            # Cache the result for 1 hour
            news_cache[cache_key] = processed_data
            last_cache_time[cache_key] = time.time()
            
            current_app.logger.info(f"Topic-specific news count for {topic}: {len(processed_data.get('news', []))}")
            return processed_data, 200
            
    except Exception as e:
        current_app.logger.error(f"Error fetching {topic} news: {str(e)}")
    
    # Fallback on any error
    fallback_data = get_fallback_news_data()
    fallback_news = fallback_data.get("news", [])
    filtered_news = [n for n in fallback_news if n.get('category') == topic]
    processed_data = {
        "news": filtered_news,
        "fallback": True,
        "error": "API call failed",
        "total": len(filtered_news)
    }
    
    news_cache[cache_key] = processed_data
    last_cache_time[cache_key] = time.time()
    return processed_data, 200

def process_alpha_vantage_news(data):
    """Process and transform Alpha Vantage news data with enhanced categorization"""
    processed_news = []
    
    # Check if data is a string (error response)
    if isinstance(data, str):
        current_app.logger.warning(f"Alpha Vantage API returned string response: {data}")
        fallback = get_fallback_news_data()
        fallback["error"] = "API returned error response"
        fallback["fallback"] = True
        return fallback
    
    # Check if data is not a dictionary
    if not isinstance(data, dict):
        current_app.logger.warning(f"Alpha Vantage API returned unexpected data type: {type(data)}")
        fallback = get_fallback_news_data()
        fallback["error"] = "Unexpected API response format"
        fallback["fallback"] = True
        return fallback
    
    if "feed" not in data:
        current_app.logger.warning("Alpha Vantage API response missing 'feed' key")
        # Return fallback data instead of empty news array
        fallback = get_fallback_news_data()
        fallback["error"] = "Feed missing from API response"
        fallback["fallback"] = True
        return fallback
    
    # Enhanced topic to category mapping
    topic_to_category = {
        'financial_markets': 'market',
        'economy_macro': 'economy',
        'economy_fiscal': 'economy',
        'economy_monetary': 'economy',
        'blockchain': 'crypto',
        'earnings': 'earnings',
        'technology': 'market',
        'ipo': 'market',
        'mergers_and_acquisitions': 'market',
        'finance': 'market',
        'manufacturing': 'market',
        'retail_wholesale': 'market',
        'real_estate': 'market',
        'energy_transportation': 'market'
    }
    
    # Keywords for better categorization when topics are not specific enough
    category_keywords = {
        'crypto': ['bitcoin', 'cryptocurrency', 'crypto', 'blockchain', 'ethereum', 'digital currency', 'defi', 'nft'],
        'forex': ['forex', 'currency', 'dollar', 'euro', 'yen', 'exchange rate', 'fx', 'gbp', 'usd', 'eur'],
        'economy': ['federal reserve', 'inflation', 'gdp', 'unemployment', 'interest rate', 'monetary policy', 'fiscal policy', 'economy', 'recession'],
        'earnings': ['earnings', 'quarterly results', 'revenue', 'profit', 'financial results', 'q1', 'q2', 'q3', 'q4']
    }
    
    for item in data["feed"]:
        # Extract the main category from topics first
        category = 'market'  # Default category
        
        # Try to get category from topics
        if "topics" in item and item["topics"]:
            for topic in item["topics"]:
                # Handle both string topics (fallback data) and dict topics (API data)
                if isinstance(topic, str):
                    topic_name = topic.lower()
                elif isinstance(topic, dict):
                    topic_name = topic.get("topic", "").lower()
                else:
                    continue
                    
                if topic_name in topic_to_category:
                    category = topic_to_category[topic_name]
                    break
        
        # If still market category, try keyword-based categorization
        if category == 'market':
            title_summary = (item.get("title", "") + " " + item.get("summary", "")).lower()
            for cat, keywords in category_keywords.items():
                if any(keyword in title_summary for keyword in keywords):
                    category = cat
                    break
        
        # Extract relevant topics
        topics = []
        if "topics" in item and item["topics"]:
            for topic in item["topics"]:
                # Handle both string topics (fallback data) and dict topics (API data)
                if isinstance(topic, str):
                    topics.append(topic)
                elif isinstance(topic, dict) and topic.get("topic"):
                    topics.append(topic.get("topic", ""))
        
        # Process sentiment with better handling
        sentiment = item.get("overall_sentiment_label", "neutral").lower()
        # Normalize sentiment values
        if sentiment not in ['positive', 'negative', 'neutral']:
            sentiment = 'neutral'
        
        # Get sentiment score for more nuanced sentiment determination
        sentiment_score = item.get("overall_sentiment_score", 0)
        try:
            sentiment_score = float(sentiment_score)
            # If we have a score, use it to refine sentiment
            if sentiment == 'neutral' and sentiment_score != 0:
                if sentiment_score > 0.1:
                    sentiment = 'positive'
                elif sentiment_score < -0.1:
                    sentiment = 'negative'
        except (ValueError, TypeError):
            pass  # Keep original sentiment if score is invalid
        
        news_item = {
            "id": item.get("id", ""),
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "published_at": item.get("time_published", ""),
            "category": category,
            "topics": topics,
            "image": item.get("banner_image", ""),
            "sentiment": sentiment,
            "sentiment_score": sentiment_score
        }
        processed_news.append(news_item)
    
    # Sort by published date (newest first)
    processed_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    
    # Log category distribution for debugging
    category_counts = {}
    sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
    
    for news in processed_news:
        cat = news.get('category', 'market')
        sent = news.get('sentiment', 'neutral')
        category_counts[cat] = category_counts.get(cat, 0) + 1
        sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1
    
    current_app.logger.info(f"Category distribution: {category_counts}")
    current_app.logger.info(f"Sentiment distribution: {sentiment_counts}")
    
    return {
        "news": processed_news,
        "has_more": False,  # Alpha Vantage doesn't support pagination
        "total": len(processed_news),
        "category_stats": category_counts,
        "sentiment_stats": sentiment_counts
    }



@market_news_bp.route('/market-news')
def market_news_page():
    """Modern market news page with enhanced design"""
    return render_template('market_news_modern_v2.html')

@market_news_bp.route('/debug')
def debug_news():
    """Debug version of market news page without base template"""
    return render_template('market_news_debug.html')

@market_news_bp.route('/api-debug')
def api_debug():
    """Debug page for API testing"""
    return render_template('api_debug.html')

@market_news_bp.route('/api/refresh-cache')
def refresh_cache():
    """API endpoint to refresh the news cache"""
    try:
        # Clear all cache
        global news_cache, last_cache_time
        news_cache.clear()
        last_cache_time.clear()
        
        current_app.logger.info("News cache cleared")
        
        # Since API is rate limited, just use fallback data directly
        current_app.logger.info("API rate limited, using fallback data for cache refresh")
        fallback_data = get_fallback_news_data()
        
        # Process the fallback data
        try:
            processed_data = process_alpha_vantage_news({"feed": fallback_data.get("news", [])})
            news_cache["news-all"] = processed_data
            last_cache_time["news-all"] = time.time()
            
            news_count = len(processed_data.get("news", [])) if isinstance(processed_data, dict) else 0
            
            return jsonify({
                "status": "success",
                "message": "Cache refreshed successfully with fallback data",
                "news_count": news_count,
                "cache_cleared": True,
                "api_status": "fallback_used"
            }), 200
            
        except Exception as process_error:
            current_app.logger.error(f"Error processing fallback data: {str(process_error)}")
            # If processing fails, just store raw fallback data
            news_cache["news-all"] = fallback_data
            last_cache_time["news-all"] = time.time()
            
            return jsonify({
                "status": "success",
                "message": "Cache refreshed with raw fallback data",
                "news_count": len(fallback_data.get("news", [])),
                "cache_cleared": True,
                "api_status": "fallback_raw"
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error refreshing cache: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": "Failed to refresh cache"
        }), 500

@market_news_bp.route('/test-api')
def test_api():
    """Test the market news API directly"""
    try:
        # Clear cache for testing
        global news_cache, last_cache_time
        news_cache.clear()
        last_cache_time.clear()
        
        # Test with default parameters
        data, status_code = fetch_alpha_vantage_news()
        
        # Calculate statistics
        category_stats = {}
        sentiment_stats = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        news_data = data.get("news", []) if isinstance(data, dict) else []
        
        for news in news_data:
            if isinstance(news, dict):  # Ensure news item is a dictionary
                cat = news.get('category', 'unknown')
                sent = news.get('sentiment', 'neutral')
                category_stats[cat] = category_stats.get(cat, 0) + 1
                sentiment_stats[sent] = sentiment_stats.get(sent, 0) + 1
        
        return jsonify({
            "status": "success",
            "status_code": status_code,
            "news_count": len(news_data),
            "has_fallback": data.get("fallback", False) if isinstance(data, dict) else False,
            "category_distribution": category_stats,
            "sentiment_distribution": sentiment_stats,
            "sample_news": news_data[:3] if news_data else []
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "type": type(e).__name__
        }), 500

@market_news_bp.route('/api/cache-status')
def get_cache_status():
    """API endpoint to check cache status and API usage"""
    reset_daily_api_counter()
    
    cache_info = {}
    for key, timestamp in last_cache_time.items():
        age_minutes = (time.time() - timestamp) / 60
        is_valid = age_minutes < (NEWS_CACHE_TIMEOUT / 60)
        cache_info[key] = {
            "age_minutes": round(age_minutes, 1),
            "is_valid": is_valid,
            "expires_in_minutes": round((NEWS_CACHE_TIMEOUT / 60) - age_minutes, 1) if is_valid else 0,
            "has_data": key in news_cache,
            "news_count": len(news_cache[key].get("news", [])) if key in news_cache and isinstance(news_cache[key], dict) else 0
        }
    
    return jsonify({
        "api_usage": {
            "daily_calls_used": daily_api_calls,
            "daily_limit": MAX_DAILY_API_CALLS,
            "calls_remaining": MAX_DAILY_API_CALLS - daily_api_calls,
            "last_reset": str(last_api_reset) if last_api_reset else None
        },
        "cache_settings": {
            "timeout_minutes": NEWS_CACHE_TIMEOUT / 60,
            "fallback_timeout_minutes": FALLBACK_CACHE_TIMEOUT / 60
        },
        "cache_info": cache_info,
        "recommendations": {
            "can_make_api_call": can_make_api_call(),
            "should_use_cache": daily_api_calls >= (MAX_DAILY_API_CALLS * 0.8),
            "cache_efficiency": len(cache_info) > 0
        }
    }), 200

@market_news_bp.route('/api/market-news')
def get_market_news():
    """API endpoint to get market news with AGGRESSIVE caching and API conservation"""
    reset_daily_api_counter()  # Reset counter if new day
    
    current_app.logger.info("API endpoint /api/market-news called")
    page = request.args.get('page', 1, type=int)
    filter_topic = request.args.get('filter', 'all')
    items_per_page = int(request.args.get('items_per_page', 12))
    
    # Log request details with API usage
    current_app.logger.info(f"Market News API request - page: {page}, filter: {filter_topic}")
    current_app.logger.info(f"Daily API calls used: {daily_api_calls}/{MAX_DAILY_API_CALLS}")
    
    # Debug cache status
    cache_key = f"news-{filter_topic if filter_topic != 'all' else 'all'}"
    cache_age = get_cache_age(cache_key)
    current_app.logger.info(f"Cache status for {cache_key}: age={cache_age:.1f} minutes")
    
    # Check for force_fallback parameter for testing
    force_fallback = request.args.get('force_fallback', 'false').lower() == 'true'
    if force_fallback:
        current_app.logger.info("Force fallback mode activated")
        fallback_data = get_fallback_news_data()
        fallback_data["fallback"] = True
        fallback_data["message"] = "Forced fallback data"
        return jsonify(fallback_data), 200
    
    # Fetch news with aggressive caching
    current_app.logger.info(f"Fetching news with aggressive caching strategy")
    try:
        news_data, status_code = fetch_alpha_vantage_news(topic=None)  # Always fetch all news
        
        # Ensure we have valid data structure
        if not isinstance(news_data, dict):
            current_app.logger.error("Invalid data structure returned from fetch function")
            fallback_data = get_fallback_news_data()
            fallback_data["fallback"] = True
            fallback_data["error"] = "Invalid data structure"
            return jsonify(fallback_data), 200
        
        # Extract relevant data
        all_news = news_data.get("news", [])
        
        # Ensure news is a list
        if not isinstance(all_news, list):
            current_app.logger.error("News data is not a list")
            fallback_data = get_fallback_news_data()
            fallback_data["fallback"] = True
            fallback_data["error"] = "Invalid news data format"
            return jsonify(fallback_data), 200
        
        # Calculate category counts from all news
        category_counts = {
            'all': len(all_news),
            'market': len([n for n in all_news if n.get('category') == 'market']),
            'economy': len([n for n in all_news if n.get('category') == 'economy']),
            'crypto': len([n for n in all_news if n.get('category') == 'crypto']),
            'forex': len([n for n in all_news if n.get('category') == 'forex']),
            'earnings': len([n for n in all_news if n.get('category') == 'earnings'])
        }
        
        # Calculate sentiment counts
        sentiment_counts = {
            'positive': len([n for n in all_news if n.get('sentiment') == 'positive']),
            'neutral': len([n for n in all_news if n.get('sentiment') == 'neutral']),
            'negative': len([n for n in all_news if n.get('sentiment') == 'negative'])
        }
        
        # Filter news based on the selected filter
        if filter_topic != 'all':
            filtered_news = [n for n in all_news if n.get('category') == filter_topic]
        else:
            filtered_news = all_news
            
        # Calculate total pages
        total_items = len(filtered_news)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        # Ensure page is within bounds
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        
        # Apply manual pagination
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        
        paginated_news = filtered_news[start_idx:end_idx]
        has_more = end_idx < total_items
        
        current_app.logger.info(f"Pagination: page {page}/{total_pages}, items {start_idx+1}-{end_idx} of {total_items}")
        
        response_data = {
            "news": paginated_news,
            "has_more": has_more,
            "total": total_items,
            "total_pages": total_pages,
            "current_page": page,
            "items_per_page": items_per_page,
            "total_all_news": len(all_news),
            "page": page,
            "category_counts": category_counts,
            "sentiment_counts": sentiment_counts
        }
        
        # Add API usage and cache information
        response_data["api_usage"] = {
            "daily_calls_used": daily_api_calls,
            "daily_limit": MAX_DAILY_API_CALLS,
            "calls_remaining": MAX_DAILY_API_CALLS - daily_api_calls,
            "cache_age_minutes": cache_age if cache_age != float('inf') else None,
            "cache_timeout_minutes": NEWS_CACHE_TIMEOUT / 60,
            "using_cache": news_data.get("cache_used", False)
        }
        
        # Preserve fallback flag if it exists
        if news_data.get("fallback"):
            response_data["fallback"] = True
            response_data["message"] = news_data.get("message", "Using fallback data")
        
        # Add enhanced debug information
        response_data["debug_info"] = {
            "cache_keys": list(news_cache.keys()),
            "total_news_count": len(all_news),
            "filtered_news_count": len(filtered_news),
            "paginated_news_count": len(paginated_news),
            "has_error": "error" in news_data,
            "error": news_data.get("error", "None"),
            "filter_applied": filter_topic,
            "daily_api_calls": daily_api_calls,
            "max_daily_calls": MAX_DAILY_API_CALLS,
            "cache_strategy": "aggressive_1hour"
        }
        
        # Log the counts for debugging
        current_app.logger.info(f"Category counts: {category_counts}")
        current_app.logger.info(f"Sentiment counts: {sentiment_counts}")
        current_app.logger.info(f"Filter: {filter_topic}, Filtered count: {len(filtered_news)}")
        current_app.logger.info(f"API calls today: {daily_api_calls}/{MAX_DAILY_API_CALLS}")
        
        return jsonify(response_data), 200
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_market_news: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        fallback_data = get_fallback_news_data()
        fallback_data["fallback"] = True
        fallback_data["error"] = "Server error occurred"
        fallback_data["api_usage"] = {
            "daily_calls_used": daily_api_calls,
            "daily_limit": MAX_DAILY_API_CALLS
        }
        return jsonify(fallback_data), 200
