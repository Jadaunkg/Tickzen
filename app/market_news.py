# market_news.py - Handles market news functionality with intelligent caching

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


NEWS_CACHE_TIMEOUT = 60 * 60  # 1 hour for fresh cache (reduced API calls)
FALLBACK_CACHE_TIMEOUT = 24 * 60 * 60  # 24 hours - keep cache much longer as fallback
API_RATE_LIMIT_WINDOW = 60 * 60  # 1 hour - minimum time between API calls for same data
news_cache = {}
last_cache_time = {}
last_api_call_time = {}  # Track when we last made an API call for each cache key
last_successful_fetch = {}  # Track when we last successfully fetched from API
daily_api_calls = 0
last_api_reset = None
MAX_DAILY_API_CALLS = 22  # Use 22 out of 25, leaving 3 as buffer

def reset_daily_api_counter():
    """Reset daily API call counter if it's a new day"""
    global daily_api_calls, last_api_reset
    current_date = datetime.now().date()
    
    if last_api_reset is None or last_api_reset != current_date:
        daily_api_calls = 0
        last_api_reset = current_date
        current_app.logger.info(f"Daily API counter reset for {current_date}")

def can_make_api_call():
    """Simple API call check for backward compatibility"""
    return can_make_api_call_with_strategy()

def increment_api_call_counter():
    """Increment the daily API call counter"""
    global daily_api_calls
    daily_api_calls += 1
    current_app.logger.info(f"API calls today: {daily_api_calls}/{MAX_DAILY_API_CALLS}")

def can_make_api_call_for_cache_key(cache_key):
    """Check if we can make an API call for a specific cache key (1-hour rate limit)"""
    if not can_make_api_call_with_strategy():
        return False
    
    current_time = time.time()
    
    # Check if we've made an API call for this cache key within the last hour
    if cache_key in last_api_call_time:
        time_since_last_call = current_time - last_api_call_time[cache_key]
        if time_since_last_call < API_RATE_LIMIT_WINDOW:
            remaining_time = API_RATE_LIMIT_WINDOW - time_since_last_call
            current_app.logger.info(f"API rate limit active for {cache_key}. {remaining_time/60:.1f} minutes remaining")
            return False
    
    return True

def mark_api_call_for_cache_key(cache_key):
    """Mark that we made an API call for a specific cache key"""
    last_api_call_time[cache_key] = time.time()
    increment_api_call_counter()

def get_next_api_call_time(cache_key):
    """Get when the next API call is allowed for a cache key"""
    if cache_key not in last_api_call_time:
        return "now"
    
    next_allowed = last_api_call_time[cache_key] + API_RATE_LIMIT_WINDOW
    current_time = time.time()
    
    if next_allowed <= current_time:
        return "now"
    
    minutes_remaining = (next_allowed - current_time) / 60
    return f"{minutes_remaining:.1f} minutes"

def should_attempt_background_refresh(cache_key):
    """Check if we should attempt a refresh (now with 1-hour rate limiting)"""
    if cache_key not in last_cache_time:
        return True
    
    current_time = time.time()
    cache_age = current_time - last_cache_time[cache_key]
    
    # Only attempt refresh if cache is older than 1 hour AND we can make API calls
    if cache_age > NEWS_CACHE_TIMEOUT:
        return can_make_api_call_for_cache_key(cache_key)
    
    return False

def can_make_api_call_with_strategy():
    """Enhanced API call check with intelligent distribution strategy"""
    reset_daily_api_counter()
    
    if daily_api_calls >= MAX_DAILY_API_CALLS:
        return False
    
    # Calculate how many hours left in the day
    current_hour = datetime.now().hour
    hours_remaining = 24 - current_hour
    
    # Reserve some calls for the remaining hours
    calls_remaining = MAX_DAILY_API_CALLS - daily_api_calls
    
    # If we have less than 2 hours left, use remaining calls more freely
    if hours_remaining <= 2:
        return calls_remaining > 0
    
    # Otherwise, ensure we have at least 1 call per remaining 2-hour period
    min_calls_to_reserve = max(1, hours_remaining // 2)
    
    return calls_remaining > min_calls_to_reserve

def mark_successful_fetch(cache_key):
    """Mark a successful API fetch for tracking"""
    global last_successful_fetch
    last_successful_fetch[cache_key] = time.time()
    current_app.logger.info(f"Marked successful fetch for {cache_key}")

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
    """Fetch diverse news data with intelligent API call distribution - optimized for market news"""
    base_url = "https://www.alphavantage.co/query"
    all_news = []
    
    # STRATEGIC: Make 1-2 well-targeted API calls to get 100+ market-focused articles
    topic_queries = [
        {"topics": "financial_markets", "limit": 100}  # Primary market-focused call with max limit
    ]
    
    # Only make second call if we have sufficient API budget
    remaining_calls = MAX_DAILY_API_CALLS - daily_api_calls
    current_hour = datetime.now().hour
    hours_left = 24 - current_hour
    
    # Conservative check: ensure we have calls for rest of day
    if remaining_calls > max(2, hours_left // 4):
        # Second call also focused on market content with different parameters
        topic_queries.append({"topics": "earnings", "limit": 100})  # Market earnings call
        current_app.logger.info("Adding second market-focused API call for earnings data")
    
    current_app.logger.info(f"Making {len(topic_queries)} strategic market-focused API calls to fetch 100+ articles")
    
    for i, query_params in enumerate(topic_queries):
        # Double-check API limit before each call
        if not can_make_api_call_with_strategy():
            current_app.logger.warning(f"API limit reached during fetch at call {i+1}, stopping additional calls")
            break
            
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": api_key,
            **query_params
        }
        
        try:
            current_app.logger.info(f"API call {daily_api_calls + 1}/{MAX_DAILY_API_CALLS} with params: {query_params}")
            increment_api_call_counter()  # Track the call
            
            response = requests.get(base_url, params=params, timeout=30)
            
            if response.status_code == 429:
                current_app.logger.warning("Rate limit hit by Alpha Vantage")
                break
                
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and "feed" in data:
                        new_articles = data["feed"]
                        all_news.extend(new_articles)
                        current_app.logger.info(f"Retrieved {len(new_articles)} articles from call {i+1}")
                    else:
                        current_app.logger.warning(f"Invalid response structure from call {i+1}: {data}")
                except json.JSONDecodeError:
                    current_app.logger.error(f"Failed to parse JSON response from call {i+1}: {response.text[:200]}")
            else:
                current_app.logger.error(f"API call {i+1} failed with status {response.status_code}")
                
        except Exception as e:
            current_app.logger.error(f"Error in API call {i+1}: {str(e)}")
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
    
    # Process the combined data
    data_wrapper = {"feed": unique_news}
    processed_data = process_alpha_vantage_news(data_wrapper)
    
    # Enhanced caching: Cache for 1 hour for fresh data
    news_cache[cache_key] = processed_data
    last_cache_time[cache_key] = time.time()
    processed_data["api_calls_used"] = daily_api_calls
    processed_data["cache_timeout_minutes"] = NEWS_CACHE_TIMEOUT / 60
    processed_data["fresh_articles_count"] = len(unique_news)
    
    current_app.logger.info(f"Cached {len(processed_data.get('news', []))} articles for {NEWS_CACHE_TIMEOUT/60} minutes")
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

def fetch_alpha_vantage_news(topic=None):
    """Fetch news from Alpha Vantage API with intelligent caching and continuous refresh strategy"""
    cache_key = f"news-{topic or 'all'}"
    
    # PRIORITY 1: Return cached data if available and relatively fresh (1 hour)
    if is_cache_valid(cache_key, NEWS_CACHE_TIMEOUT):
        cache_age = get_cache_age(cache_key)
        current_app.logger.info(f"Returning FRESH cached data for {cache_key} (age: {cache_age:.1f} minutes)")
        return news_cache[cache_key], 200
    
    # PRIORITY 2: If we have older cached data (within 24 hours), return it while attempting refresh
    if is_cache_valid(cache_key, FALLBACK_CACHE_TIMEOUT):
        cache_age = get_cache_age(cache_key)
        current_app.logger.info(f"Returning OLDER cached data for {cache_key} (age: {cache_age:.1f} minutes) while attempting refresh")
        
        cached_data = news_cache[cache_key].copy()
        cached_data["cache_used"] = True
        cached_data["cache_age_minutes"] = cache_age
        
        # Attempt to refresh ONLY if we can make API calls and haven't called within 1 hour
        if can_make_api_call_for_cache_key(cache_key):
            current_app.logger.info(f"Attempting refresh for older cache data {cache_key}")
            try:
                new_data = attempt_background_refresh(cache_key, topic)
                if new_data:
                    current_app.logger.info(f"Successfully refreshed older cache for {cache_key}")
                    mark_successful_fetch(cache_key)
                    mark_api_call_for_cache_key(cache_key)
                    return new_data, 200  # Return fresh data if refresh succeeds
            except Exception as e:
                current_app.logger.warning(f"Refresh attempt failed for {cache_key}: {e}")
        else:
            current_app.logger.info(f"API rate limit active for {cache_key}, returning cached data")
        
        return cached_data, 200
    
    # PRIORITY 3: No cache available, must fetch new data
    current_app.logger.info(f"No valid cache for {cache_key}, attempting fresh fetch")
    
    api_key = get_alpha_vantage_api_key()
    if not api_key:
        current_app.logger.error("Alpha Vantage API key not available")
        error_data = {
            "news": [],
            "error": "API key not configured",
            "total": 0,
            "has_more": False
        }
        # Cache error data for 1 hour to avoid repeated attempts
        news_cache[cache_key] = error_data
        last_cache_time[cache_key] = time.time()
        return error_data, 200
    
    # Check if we can make API calls with 1-hour rate limiting
    if not can_make_api_call_for_cache_key(cache_key):
        current_app.logger.warning(f"API rate limit active for {cache_key}. No data available.")
        error_data = {
            "news": [],
            "api_rate_limited": True,
            "daily_calls_used": daily_api_calls,
            "error": "API rate limit active",
            "total": 0,
            "has_more": False
        }
        # Cache error data
        news_cache[cache_key] = error_data
        last_cache_time[cache_key] = time.time()
        return error_data, 200
    
    # PRIORITY 4: Make API call for fresh data
    current_app.logger.info(f"Making API call for {cache_key} (calls today: {daily_api_calls}/{MAX_DAILY_API_CALLS})")
    
    try:
        # Enhanced strategy: if requesting all news, fetch multiple topic-specific queries
        if topic is None or topic == 'all':
            result_data, status_code = fetch_diverse_news_data(api_key, cache_key)
            if status_code == 200:
                mark_successful_fetch(cache_key)
                mark_api_call_for_cache_key(cache_key)  # Mark the API call
            return result_data, status_code
        else:
            # For specific topic requests, use single API call
            result_data, status_code = fetch_topic_specific_news(api_key, topic, cache_key)
            if status_code == 200:
                mark_successful_fetch(cache_key)
                mark_api_call_for_cache_key(cache_key)  # Mark the API call
            return result_data, status_code
            
    except Exception as e:
        current_app.logger.error(f"API fetch failed for {cache_key}: {e}")
        # Return error data on any error
        error_data = {
            "news": [],
            "error": f"API fetch failed: {str(e)}",
            "total": 0,
            "has_more": False
        }
        news_cache[cache_key] = error_data
        last_cache_time[cache_key] = time.time()
        return error_data, 200

def attempt_background_refresh(cache_key, topic):
    """Attempt to refresh cache with 1-hour rate limiting"""
    api_key = get_alpha_vantage_api_key()
    if not api_key:
        current_app.logger.warning("API key not available for refresh")
        return None
    
    # Use the new rate limiting function
    if not can_make_api_call_for_cache_key(cache_key):
        current_app.logger.warning(f"Cannot make API call for {cache_key} - rate limited")
        return None
    
    try:
        current_app.logger.info(f"API refresh attempt for {cache_key}")
        
        if topic is None or topic == 'all':
            result_data, status_code = fetch_diverse_news_data(api_key, cache_key)
        else:
            result_data, status_code = fetch_topic_specific_news(api_key, topic, cache_key)
        
        if status_code == 200 and result_data:
            current_app.logger.info(f"API refresh successful for {cache_key}")
            # Mark that we made an API call
            mark_api_call_for_cache_key(cache_key)
            return result_data
        else:
            current_app.logger.warning(f"API refresh returned status {status_code}")
            return None
            
    except Exception as e:
        current_app.logger.error(f"Background refresh error for {cache_key}: {e}")
        return None

def fetch_topic_specific_news(api_key, topic, cache_key):
    """Fetch news for a specific topic with intelligent API call management"""
    base_url = "https://www.alphavantage.co/query"
    
    # Check if we can make API call with strategy
    if not can_make_api_call_with_strategy():
        current_app.logger.warning("API limit reached for topic-specific request")
        
        processed_data = {
            "news": [],
            "api_limit_reached": True,
            "total": 0,
            "has_more": False,
            "cache_timeout_minutes": NEWS_CACHE_TIMEOUT / 60
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
        "limit": 100  # Increased limit for more comprehensive coverage
    }
    
    try:
        current_app.logger.info(f"Making topic-specific API call for {topic} -> {av_topic} (calls: {daily_api_calls + 1}/{MAX_DAILY_API_CALLS})")
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
                    "from_general_cache": True,
                    "cache_timeout_minutes": NEWS_CACHE_TIMEOUT / 60
                }
                news_cache[cache_key] = processed_data
                last_cache_time[cache_key] = time.time()
                return processed_data, 200
            
        if response.status_code == 200:
            data = response.json()
            
            # Check for API errors
            if "Error Message" in data or "Information" in data:
                current_app.logger.warning(f"API issue: {data.get('Error Message', data.get('Information', 'Unknown'))}")
                # Return error data
                processed_data = {
                    "news": [],
                    "total": 0,
                    "has_more": False,
                    "api_error": data.get('Error Message', data.get('Information', 'Unknown')),
                    "cache_timeout_minutes": NEWS_CACHE_TIMEOUT / 60
                }
                news_cache[cache_key] = processed_data
                last_cache_time[cache_key] = time.time()
                return processed_data, 200
                
            if "feed" in data and data["feed"]:
                current_app.logger.info(f"Retrieved {len(data['feed'])} articles for {topic}")
                
                # Process the data
                data_wrapper = {"feed": data["feed"]}
                processed_data = process_alpha_vantage_news(data_wrapper)
                
                # Cache the result for 15 minutes
                news_cache[cache_key] = processed_data
                last_cache_time[cache_key] = time.time()
                processed_data["cache_timeout_minutes"] = NEWS_CACHE_TIMEOUT / 60
                
                current_app.logger.info(f"Topic-specific news count for {topic}: {len(processed_data.get('news', []))}")
                return processed_data, 200
        else:
            current_app.logger.error(f"API request failed with status {response.status_code}")
            
    except Exception as e:
        current_app.logger.error(f"Error fetching {topic} news: {str(e)}")
    
    # Return error data on any error
    processed_data = {
        "news": [],
        "error": "API call failed",
        "total": 0,
        "has_more": False,
        "cache_timeout_minutes": NEWS_CACHE_TIMEOUT / 60
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
        return {
            "news": [],
            "error": "API returned error response",
            "total": 0,
            "has_more": False
        }
    
    # Check if data is not a dictionary
    if not isinstance(data, dict):
        current_app.logger.warning(f"Alpha Vantage API returned unexpected data type: {type(data)}")
        return {
            "news": [],
            "error": "Unexpected API response format",
            "total": 0,
            "has_more": False
        }
    
    if "feed" not in data:
        current_app.logger.warning("Alpha Vantage API response missing 'feed' key")
        # Return empty data instead of fallback
        return {
            "news": [],
            "error": "Feed missing from API response",
            "total": 0,
            "has_more": False
        }
    
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

@market_news_bp.route('/api/refresh-cache')
def refresh_cache():
    """API endpoint to refresh the news cache with intelligent strategy"""
    try:
        force_api_call = request.args.get('force_api', 'false').lower() == 'true'
        
        # Clear specific cache if requested
        cache_key = request.args.get('cache_key', 'news-all')
        
        if force_api_call:
            current_app.logger.info(f"Force API refresh requested for {cache_key}")
            # Clear cache to force API call
            if cache_key in news_cache:
                del news_cache[cache_key]
            if cache_key in last_cache_time:
                del last_cache_time[cache_key]
        else:
            current_app.logger.info(f"Standard cache refresh requested for {cache_key}")
        
        # Check if we can make API calls
        if not can_make_api_call_with_strategy() and not force_api_call:
            current_app.logger.info("API limit reached, cannot refresh cache")
            
            return jsonify({
                "status": "error",
                "message": "API limit reached, cannot refresh cache",
                "daily_calls_used": daily_api_calls,
                "daily_limit": MAX_DAILY_API_CALLS
            }), 429
        
        # Attempt to fetch fresh data
        try:
            topic = cache_key.replace('news-', '') if cache_key.startswith('news-') else None
            if topic == 'all':
                topic = None
                
            current_app.logger.info(f"Attempting fresh fetch for cache refresh: {cache_key} (topic: {topic})")
            news_data, status_code = fetch_alpha_vantage_news(topic=topic)
            
            if status_code == 200 and news_data:
                news_count = len(news_data.get("news", [])) if isinstance(news_data, dict) else 0
                
                return jsonify({
                    "status": "success",
                    "message": "Cache refreshed successfully with fresh data",
                    "news_count": news_count,
                    "cache_cleared": force_api_call,
                    "api_status": "fresh_api_call",
                    "daily_calls_used": daily_api_calls,
                    "daily_limit": MAX_DAILY_API_CALLS,
                    "fresh_articles": news_data.get("fresh_articles_count", 0)
                }), 200
            else:
                return jsonify({
                    "status": "error",
                    "message": f"Failed to refresh cache, status code: {status_code}",
                    "cache_key": cache_key
                }), 500
                
        except Exception as fetch_error:
            current_app.logger.error(f"Error during fresh fetch: {str(fetch_error)}")
            
            return jsonify({
                "status": "error",
                "message": f"API call failed: {str(fetch_error)}",
                "cache_cleared": force_api_call,
                "error": str(fetch_error)
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error refreshing cache: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": "Failed to refresh cache"
        }), 500

@market_news_bp.route('/api/cache-status')
def get_cache_status():
    """API endpoint to check cache status and API usage with enhanced intelligence"""
    reset_daily_api_counter()
    
    cache_info = {}
    for key, timestamp in last_cache_time.items():
        age_minutes = (time.time() - timestamp) / 60
        is_fresh = age_minutes < (NEWS_CACHE_TIMEOUT / 60)
        is_valid_fallback = age_minutes < (FALLBACK_CACHE_TIMEOUT / 60)
        should_refresh = should_attempt_background_refresh(key)
        
        cache_info[key] = {
            "age_minutes": round(age_minutes, 1),
            "is_fresh": is_fresh,
            "is_valid_fallback": is_valid_fallback,
            "expires_in_minutes": round((NEWS_CACHE_TIMEOUT / 60) - age_minutes, 1) if is_fresh else 0,
            "fallback_expires_in_hours": round((FALLBACK_CACHE_TIMEOUT / 3600) - (age_minutes / 60), 1) if is_valid_fallback else 0,
            "has_data": key in news_cache,
            "news_count": len(news_cache[key].get("news", [])) if key in news_cache and isinstance(news_cache[key], dict) else 0,
            "should_attempt_refresh": should_refresh,
            "last_successful_fetch": last_successful_fetch.get(key),
            "time_since_success_minutes": round((time.time() - last_successful_fetch[key]) / 60, 1) if key in last_successful_fetch else None
        }
    
    # Calculate time distribution for API calls
    current_hour = datetime.now().hour
    hours_remaining = 24 - current_hour
    calls_remaining = MAX_DAILY_API_CALLS - daily_api_calls
    
    return jsonify({
        "api_usage": {
            "daily_calls_used": daily_api_calls,
            "daily_limit": MAX_DAILY_API_CALLS,
            "calls_remaining": calls_remaining,
            "last_reset": str(last_api_reset) if last_api_reset else None,
            "current_hour": current_hour,
            "hours_remaining": hours_remaining,
            "recommended_calls_per_hour": round(calls_remaining / max(1, hours_remaining), 2)
        },
        "cache_settings": {
            "fresh_timeout_minutes": NEWS_CACHE_TIMEOUT / 60,
            "api_rate_limit_minutes": API_RATE_LIMIT_WINDOW / 60,
            "fallback_timeout_hours": FALLBACK_CACHE_TIMEOUT / 3600
        },
        "cache_info": cache_info,
        "strategy_status": {
            "can_make_api_call": can_make_api_call_with_strategy(),
            "intelligent_distribution": True,
            "background_refresh_enabled": True,
            "continuous_data_flow": True
        },
        "recommendations": {
            "cache_efficiency": len(cache_info) > 0,
            "api_usage_healthy": daily_api_calls < (MAX_DAILY_API_CALLS * 0.9),
            "background_refresh_active": any(cache_info[key]["should_attempt_refresh"] for key in cache_info),
            "fallback_usage_minimal": all(not cache_info[key].get("is_fresh", True) for key in cache_info)
        }
    }), 200

@market_news_bp.route('/api/market-news')
def get_market_news():
    """API endpoint to get market news with intelligent caching and continuous refresh strategy"""
    reset_daily_api_counter()  # Reset counter if new day
    
    current_app.logger.info("API endpoint /api/market-news called")
    page = request.args.get('page', 1, type=int)
    filter_topic = request.args.get('filter', 'all')
    items_per_page = int(request.args.get('items_per_page', 12))
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    # Log request details with API usage
    current_app.logger.info(f"Market News API request - page: {page}, filter: {filter_topic}, force_refresh: {force_refresh}")
    current_app.logger.info(f"Daily API calls used: {daily_api_calls}/{MAX_DAILY_API_CALLS}")
    
    # Debug cache status
    cache_key = f"news-{filter_topic if filter_topic != 'all' else 'all'}"
    cache_age = get_cache_age(cache_key)
    current_app.logger.info(f"Cache status for {cache_key}: age={cache_age:.1f} minutes")
    
    # Force refresh cache if requested (for admin/testing)
    if force_refresh and cache_key in news_cache:
        current_app.logger.info(f"Force refresh requested for {cache_key}")
        del news_cache[cache_key]
        if cache_key in last_cache_time:
            del last_cache_time[cache_key]
    
    # Fetch news with intelligent caching strategy
    current_app.logger.info(f"Fetching news with intelligent caching and continuous refresh strategy")
    try:
        news_data, status_code = fetch_alpha_vantage_news(topic=None)  # Always fetch all news for better caching
        
        # Ensure we have valid data structure
        if not isinstance(news_data, dict):
            current_app.logger.error("Invalid data structure returned from fetch function")
            return jsonify({
                "news": [],
                "error": "Invalid data structure",
                "total": 0,
                "has_more": False
            }), 500
        
        # Extract relevant data
        all_news = news_data.get("news", [])
        
        # Ensure news is a list
        if not isinstance(all_news, list):
            current_app.logger.error("News data is not a list")
            return jsonify({
                "news": [],
                "error": "Invalid news data format",
                "total": 0,
                "has_more": False
            }), 500
        
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
        
        # Add enhanced API usage and cache information
        response_data["api_usage"] = {
            "daily_calls_used": daily_api_calls,
            "daily_limit": MAX_DAILY_API_CALLS,
            "calls_remaining": MAX_DAILY_API_CALLS - daily_api_calls,
            "cache_age_minutes": cache_age if cache_age != float('inf') else None,
            "cache_timeout_minutes": NEWS_CACHE_TIMEOUT / 60,
            "using_cache": news_data.get("cache_used", False),
            "api_rate_limit_minutes": API_RATE_LIMIT_WINDOW / 60,
            "can_make_api_call": can_make_api_call_with_strategy()
        }
        
        # Add success tracking information
        response_data["fetch_status"] = {
            "last_successful_fetch": last_successful_fetch.get(cache_key),
            "fresh_articles_count": news_data.get("fresh_articles_count", 0),
            "should_attempt_refresh": should_attempt_background_refresh(cache_key)
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
            "cache_strategy": "1hour_api_rate_limiting",
            "cache_valid": is_cache_valid(cache_key),
            "api_rate_limited": not can_make_api_call_for_cache_key(cache_key),
            "next_api_call_allowed": get_next_api_call_time(cache_key)
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
        return jsonify({
            "news": [],
            "error": "Server error occurred",
            "total": 0,
            "has_more": False,
            "api_usage": {
                "daily_calls_used": daily_api_calls,
                "daily_limit": MAX_DAILY_API_CALLS
            }
        }), 500
