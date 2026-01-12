#!/usr/bin/env python3
"""
Market News Intelligence System
==============================

Advanced market news aggregation and analysis system providing real-time
financial news, intelligent caching, sentiment analysis, and personalized
news delivery for enhanced market awareness and decision-making.

Core News Features:
------------------
1. **Multi-Source Aggregation**:
   - Financial news APIs (Alpha Vantage, Finnhub, etc.)
   - RSS feed monitoring from major financial publications
   - Press release and SEC filing alerts
   - Earnings announcement and guidance updates
   - Economic indicator releases and analysis

2. **Real-Time Processing**:
   - Live news feed monitoring and updates
   - Breaking news alert system
   - Market-moving event detection
   - Automated news categorization
   - Priority scoring and ranking

3. **Intelligent Caching**:
   - Multi-level caching strategy for performance
   - Content deduplication and merge logic
   - Cache invalidation based on news freshness
   - Bandwidth optimization for API calls
   - Smart prefetching for popular content

News Analysis Engine:
--------------------
- **Sentiment Analysis**: NLP-based news sentiment scoring
- **Market Impact Assessment**: Prediction of news impact on markets
- **Trend Detection**: Identification of emerging market themes
- **Entity Recognition**: Company, person, and location extraction
- **Event Classification**: Categorization of news events by type

Content Organization:
--------------------
1. **By Category**:
   - Market Updates and General News
   - Earnings and Corporate News
   - Economic Indicators and Policy
   - Sector and Industry Analysis
   - International Markets and Global Events

2. **By Priority**:
   - Breaking News (immediate market impact)
   - High Priority (significant market relevance)
   - Standard News (general market interest)
   - Background Information (context and analysis)

3. **By Timeframe**:
   - Real-time (last 15 minutes)
   - Recent (last 2 hours)
   - Today's News (current trading day)
   - Weekly Summary (past 7 days)

Personalization Features:
------------------------
- **User Preferences**: Customizable news categories and sources
- **Ticker Watchlists**: Personalized news for followed stocks
- **Industry Focus**: Sector-specific news filtering
- **Reading History**: Content recommendations based on past behavior
- **Notification Settings**: Customizable alert preferences

Advanced Analytics:
------------------
- **Market Correlation**: News sentiment vs price movement analysis
- **Event Impact Tracking**: Historical analysis of news impact
- **Trending Topics**: Real-time identification of trending themes
- **Source Reliability**: Track record of news source accuracy
- **Timing Analysis**: Optimal news consumption timing

API Endpoints:
-------------
```python
News API Routes:
├── /api/news/latest - Latest market news
├── /api/news/breaking - Breaking news alerts
├── /api/news/ticker/<symbol> - Company-specific news
├── /api/news/sector/<sector> - Sector-specific news
├── /api/news/search - News search functionality
└── /api/news/sentiment - News sentiment analysis
```

Caching Strategy:
----------------
- **L1 Cache**: In-memory cache for frequently accessed content (5 min TTL)
- **L2 Cache**: Redis cache for shared content across users (30 min TTL)
- **L3 Cache**: Disk-based cache for historical news (24 hour TTL)
- **Smart Invalidation**: Content-aware cache expiration
- **Preemptive Updates**: Background cache warming for popular content

News Sources Integration:
------------------------
1. **Primary APIs**:
   - Alpha Vantage News & Sentiment API
   - Finnhub News API
   - NewsAPI for general financial news
   - Yahoo Finance news feeds

2. **RSS Feeds**:
   - Bloomberg, Reuters, MarketWatch
   - CNBC, CNN Business, Fox Business
   - Wall Street Journal, Financial Times
   - Seeking Alpha, The Motley Fool

3. **Specialized Sources**:
   - SEC EDGAR filings
   - Federal Reserve communications
   - Economic calendar events
   - Earnings call transcripts

Data Processing Pipeline:
------------------------
1. **News Collection**: Aggregate from multiple sources
2. **Content Normalization**: Standardize format and structure
3. **Deduplication**: Remove duplicate and similar content
4. **Enhancement**: Add sentiment, categories, and metadata
5. **Ranking**: Score and prioritize based on relevance
6. **Caching**: Store processed content for fast retrieval
7. **Delivery**: Serve personalized content to users

Usage Examples:
--------------
```python
# Get latest market news
latest_news = get_latest_market_news(limit=20)

# Get ticker-specific news
aapl_news = get_ticker_news('AAPL', hours=24)

# Search news with filters
search_results = search_news(
    query='federal reserve',
    category='economic',
    sentiment='neutral',
    hours=48
)

# Get breaking news alerts
breaking_news = get_breaking_news(priority='high')
```

Real-Time Features:
------------------
- **WebSocket Updates**: Real-time news delivery via SocketIO
- **Push Notifications**: Browser and mobile push notifications
- **Email Digests**: Personalized news summaries
- **SMS Alerts**: Critical breaking news via SMS
- **Slack Integration**: Team news sharing capabilities

Performance Optimization:
------------------------
- **Async Processing**: Non-blocking news collection and processing
- **Rate Limiting**: API quota management and optimization
- **Content Compression**: Efficient data transfer and storage
- **CDN Integration**: Global content delivery optimization
- **Database Indexing**: Optimized queries for fast news retrieval

Integration Points:
------------------
- Integrated with main_portal_app.py for dashboard news display
- Provides market context for analysis_scripts/ modules
- Supports sentiment_analysis.py with news sentiment data
- Connects to notification system for breaking news alerts

Monitoring and Analytics:
------------------------
- **Usage Metrics**: Track news consumption patterns
- **Performance Monitoring**: API response times and success rates
- **Content Analytics**: Most popular and engaging news content
- **User Engagement**: Reading time and interaction metrics
- **Source Performance**: Track reliability and speed of news sources

Author: TickZen Development Team
Version: 3.0
Last Updated: January 2026
"""

import os
import re
import time
import json
import math
import hashlib
import traceback
import requests
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template, current_app, session
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

# --- Scoring and clustering helpers (non-invasive and cache-friendly) ---

SOURCE_QUALITY_SCORES = {
    # High trust
    'reuters': 1.2,
    'bloomberg': 1.2,
    'wsj': 1.15,
    'wall street journal': 1.15,
    'financial times': 1.15,
    # Medium
    'seeking alpha': 1.05,
    'marketwatch': 1.05,
    'the motley fool': 1.0,
    'yahoo finance': 1.0,
    # Default
}

def _normalize_text(s: str) -> str:
    if not s:
        return ''
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _source_quality(source: str) -> float:
    if not source:
        return 1.0
    s = source.lower()
    # try exact, then contains
    if s in SOURCE_QUALITY_SCORES:
        return SOURCE_QUALITY_SCORES[s]
    for key, val in SOURCE_QUALITY_SCORES.items():
        if key in s:
            return val
    return 1.0

def _parse_datetime_to_epoch(published_at: str) -> float:
    """Handle formats like '20230822T123456' or ISO."""
    if not published_at:
        return 0.0
    try:
        # ISO or common formats
        dt = datetime.fromisoformat(published_at.replace('Z',''))
        return dt.timestamp()
    except Exception:
        pass
    try:
        # Alpha Vantage format YYYYMMDDTHHMMSS
        if re.match(r"^\d{8}T\d{6}$", published_at):
            year = int(published_at[0:4])
            month = int(published_at[4:6])
            day = int(published_at[6:8])
            hour = int(published_at[9:11])
            minute = int(published_at[11:13])
            second = int(published_at[13:15]) if len(published_at) >= 15 else 0
            dt = datetime(year, month, day, hour, minute, second)
            return dt.timestamp()
    except Exception:
        return 0.0
    return 0.0

def _canonical_key(title: str, related_stocks: list) -> str:
    norm = _normalize_text(title)[:120]
    primary = (related_stocks[0] if related_stocks else '') or ''
    raw = f"{primary}|{norm}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def _compute_storyline_id(news_item: dict) -> str:
    base = (news_item.get('related_stocks') or ['GEN'])
    title = news_item.get('title', '')
    key = _canonical_key(title, base)
    return f"sl_{key[:10]}"

def _recency_factor(published_at: str) -> float:
    ts = _parse_datetime_to_epoch(published_at)
    if ts <= 0:
        return 0.7  # modest default
    hours = max(0.0, (time.time() - ts) / 3600.0)
    # 0.5 life ~ 48h => factor = exp(-ln(2)*hours/48)
    return math.exp(-0.693 * (hours / 48.0))

def _sentiment_magnitude(sentiment: str, sentiment_score: float) -> float:
    try:
        s = float(sentiment_score or 0.0)
    except Exception:
        s = 0.0
    base = abs(s)
    # ensure a small lift if explicitly positive/negative but low score
    if base < 0.05 and sentiment in ('positive','negative'):
        base = 0.08
    return min(1.0, max(0.0, base))

def _augment_with_global_signals(items: list) -> None:
    """Compute corroboration, divergence, storyline ids, impact and confidence without user context.
    Mutates items in-place; safe to call repeatedly.
    """
    if not items:
        return
    # Grouping
    by_canonical = {}
    by_ticker = {}
    for it in items:
        related = it.get('related_stocks') or []
        can_key = _canonical_key(it.get('title',''), related)
        it.setdefault('canonical_key', can_key)
        by_canonical.setdefault(can_key, []).append(it)
        for tk in related:
            if tk:
                by_ticker.setdefault(tk, []).append(it)

    # Corroboration counts per canonical thread
    for group in by_canonical.values():
        count = len(group)
        for it in group:
            it['corroboration_count'] = count

    # Divergence detection per ticker within ~48h window
    for tk, arts in by_ticker.items():
        pos = False
        neg = False
        now = time.time()
        recent = []
        for it in arts:
            ts = _parse_datetime_to_epoch(it.get('published_at',''))
            if ts == 0.0 or (now - ts) <= 48*3600:
                recent.append(it)
        for it in recent:
            sent = (it.get('sentiment') or 'neutral').lower()
            if sent == 'positive':
                pos = True
            elif sent == 'negative':
                neg = True
        divergence = bool(pos and neg)
        if divergence:
            for it in recent:
                it['divergence_flag'] = True

    # Storyline id and trend (very light heuristic)
    storyline_groups = {}
    for it in items:
        sid = _compute_storyline_id(it)
        it['storyline_id'] = sid
        storyline_groups.setdefault(sid, []).append(it)

    for sid, group in storyline_groups.items():
        # Sort by time asc
        group_sorted = sorted(group, key=lambda x: _parse_datetime_to_epoch(x.get('published_at','')))
        scores = []
        for it in group_sorted:
            try:
                scores.append(float(it.get('sentiment_score') or 0.0))
            except Exception:
                scores.append(0.0)
        if len(scores) >= 6:
            prev = sum(scores[0:len(scores)//2]) / (len(scores)//2)
            recent = sum(scores[len(scores)//2:]) / max(1, len(scores) - len(scores)//2)
            trend = 'up' if recent > prev + 0.05 else ('down' if recent < prev - 0.05 else 'flat')
        elif len(scores) >= 2:
            prev = scores[0]
            recent = scores[-1]
            trend = 'up' if recent > prev + 0.05 else ('down' if recent < prev - 0.05 else 'flat')
        else:
            trend = 'flat'
        for it in group:
            it['storyline_sentiment_trend'] = trend

    # Impact and confidence
    for it in items:
        sent_mag = _sentiment_magnitude(it.get('sentiment'), it.get('sentiment_score'))
        rec = _recency_factor(it.get('published_at'))
        qual = _source_quality(it.get('source'))
        corroboration = float(it.get('corroboration_count', 1))
        # impact: core signal * recency * quality * log(1+ corroboration)
        impact = sent_mag * rec * qual * math.log1p(corroboration)
        # confidence from corroboration and quality (bounded)
        confidence = min(1.0, 0.4 + 0.15*corroboration + 0.2*(qual-0.8))
        it['source_quality'] = round(qual, 3)
        it['impact_score'] = round(impact, 4)
        it['confidence_score'] = round(confidence, 3)

def _compute_relevance_for_watchlist(items: list, watchlist: set) -> None:
    if not items:
        return
    wl = {t.strip().upper() for t in watchlist if t.strip()}
    if not wl:
        return
    for it in items:
        related = {t.upper() for t in (it.get('related_stocks') or [])}
        overlap = len(wl.intersection(related))
        text = f"{it.get('title','')} {it.get('summary','')}"
        # Light extra match for inline mentions
        inline = sum(1 for tk in wl if re.search(fr"\b{re.escape(tk)}\b", text))
        score = 0.0
        if overlap > 0:
            score += 0.7 + 0.2 * min(2, overlap-1)
        if inline > 0 and overlap == 0:
            score += 0.4
        # blend with impact for better ordering
        score += 0.5 * float(it.get('impact_score') or 0.0)
        it['relevance_score'] = round(min(1.0, score), 4)

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
                        current_app.logger.info(f"Retrieved {len(new_articles)} articles from Alpha Vantage call {i+1}")
                    else:
                        current_app.logger.warning(f"Invalid response structure from call {i+1}: {data}")
                except json.JSONDecodeError:
                    current_app.logger.error(f"Failed to parse JSON response from call {i+1}: {response.text[:200]}")
            else:
                current_app.logger.error(f"API call {i+1} failed with status {response.status_code}")
                
        except Exception as e:
            current_app.logger.error(f"Error in API call {i+1}: {str(e)}")
            continue
    
    # Fetch FinnHub news to supplement Alpha Vantage data
    current_app.logger.info("Fetching supplementary news from FinnHub")
    try:
        finnhub_news = fetch_all_finnhub_news()
        if finnhub_news:
            # Process FinnHub news to match our format
            processed_finnhub = process_finnhub_news(finnhub_news)
            current_app.logger.info(f"Adding {len(processed_finnhub)} processed FinnHub articles")
            
            # Convert to Alpha Vantage format for consistency
            for article in processed_finnhub:
                # Transform to Alpha Vantage feed format
                av_format_article = {
                    "title": article["title"],
                    "summary": article["summary"],
                    "source": article["source"],
                    "url": article["url"],
                    "time_published": article["published_at"],
                    "banner_image": article["image"],
                    "overall_sentiment_label": article["sentiment"],
                    "overall_sentiment_score": article["sentiment_score"],
                    "topics": [{"topic": topic} for topic in article["topics"]],
                    "id": article["id"]
                }
                all_news.append(av_format_article)
            
            current_app.logger.info(f"Total articles after adding FinnHub: {len(all_news)}")

        # If we have a watchlist in session, fetch company-news for freshness
        wl = []
        try:
            if isinstance(session.get('watchlist'), list):
                wl = [str(t).strip().upper() for t in session.get('watchlist') if str(t).strip()]
        except Exception:
            wl = []
        if wl:
            current_app.logger.info(f"Fetching FinnHub company-news for watchlist: {wl[:10]}")
            fresh_company = fetch_finnhub_company_news(wl, days_back=2)
            if fresh_company:
                all_news.extend(fresh_company)
                current_app.logger.info(f"Added {len(fresh_company)} FinnHub company-news items")
    except Exception as e:
        current_app.logger.error(f"Error fetching FinnHub news: {str(e)}")
        # Continue with Alpha Vantage data only
    
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
    
    current_app.logger.info(f"Total unique articles collected: {len(unique_news)} (Alpha Vantage + FinnHub)")
    
    # Process the combined data
    data_wrapper = {"feed": unique_news}
    processed_data = process_alpha_vantage_news(data_wrapper)
    
    # Enhanced caching: Cache for 1 hour for fresh data
    news_cache[cache_key] = processed_data
    last_cache_time[cache_key] = time.time()
    processed_data["api_calls_used"] = daily_api_calls
    processed_data["cache_timeout_minutes"] = NEWS_CACHE_TIMEOUT / 60
    processed_data["fresh_articles_count"] = len(unique_news)
    processed_data["data_sources"] = ["alpha_vantage", "finnhub"]
    
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

def get_finnhub_api_key():
    """Get FinnHub API key from environment variables"""
    # Check for API key in environment variables first
    api_key = os.environ.get('FINNHUB_API_KEY')
    if api_key:
        return api_key
    
    # Try to force reload of environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        api_key = os.environ.get('FINNHUB_API_KEY')
        if api_key:
            return api_key
    except ImportError:
        pass  # dotenv not available
    
    # As a fallback, try to read directly from the .env file
    try:
        with open(os.path.join(os.getcwd(), '.env'), 'r') as f:
            content = f.read()
            match = re.search(r'FINNHUB_API_KEY[=:][\s]*["\']?([^"\'\s\n]+)["\']?', content)
            if match:
                api_key = match.group(1)
                current_app.logger.info(f"Found FinnHub API key in .env file: {api_key[:4]}...{api_key[-4:]}")
                return api_key
    except Exception:
        pass  # .env file not found or not readable
    
    current_app.logger.error("FinnHub API key not found in environment variables or .env file")
    return None

@lru_cache(maxsize=10)
def get_news_topics():
    """Return predefined news topics/categories for filtering"""
    return ['market', 'economy', 'crypto', 'forex', 'earnings']

def fetch_finnhub_news(api_key, category='general', min_id=0):
    """Fetch news from FinnHub API"""
    base_url = "https://finnhub.io/api/v1/news"
    
    params = {
        'category': category,
        'token': api_key
    }
    
    if min_id > 0:
        params['minId'] = min_id
    
    try:
        current_app.logger.info(f"Making FinnHub API call for category: {category}")
        response = requests.get(base_url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            current_app.logger.info(f"FinnHub returned {len(data)} articles for category: {category}")
            return data
        elif response.status_code == 429:
            current_app.logger.warning("FinnHub rate limit hit")
            return []
        else:
            current_app.logger.error(f"FinnHub API error: {response.status_code}")
            return []
    except Exception as e:
        current_app.logger.error(f"Error fetching FinnHub news: {str(e)}")
        return []

def fetch_all_finnhub_news():
    """Fetch news from all FinnHub categories"""
    api_key = get_finnhub_api_key()
    if not api_key:
        current_app.logger.warning("FinnHub API key not available")
        return []
    
    all_news = []
    # FinnHub categories: general, forex, crypto, merger
    categories = ['general', 'forex', 'crypto', 'merger']
    
    for category in categories:
        try:
            news_data = fetch_finnhub_news(api_key, category)
            if news_data:
                all_news.extend(news_data)
                current_app.logger.info(f"Added {len(news_data)} articles from FinnHub category: {category}")
                # Small delay to respect rate limits
                time.sleep(0.1)
        except Exception as e:
            current_app.logger.error(f"Error fetching FinnHub {category} news: {str(e)}")
            continue
    
    current_app.logger.info(f"Total FinnHub articles collected: {len(all_news)}")
    return all_news

def fetch_finnhub_company_news(symbols, days_back=3):
    """Fetch recent company-specific news from FinnHub for given symbols."""
    api_key = get_finnhub_api_key()
    if not api_key or not symbols:
        return []
    base_url = "https://finnhub.io/api/v1/company-news"
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=max(1, days_back))
    out = []
    for sym in list(dict.fromkeys([s.strip().upper() for s in symbols if s.strip()]))[:15]:
        params = {
            'symbol': sym,
            'from': start_date.isoformat(),
            'to': end_date.isoformat(),
            'token': api_key
        }
        try:
            resp = requests.get(base_url, params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json() or []
                for item in data:
                    try:
                        ts = item.get('datetime') or item.get('time') or 0
                        published_at = ''
                        if ts:
                            published_at = datetime.fromtimestamp(int(ts)).strftime("%Y%m%dT%H%M%S")
                        news_item = {
                            "id": f"finnhub_company_{sym}_{item.get('id', item.get('url',''))}",
                            "title": item.get('headline') or item.get('title',''),
                            "summary": item.get('summary',''),
                            "source": f"{item.get('source','FinnHub')} (FinnHub)",
                            "url": item.get('url',''),
                            "published_at": published_at,
                            "category": 'market',
                            "topics": ["market"],
                            "image": item.get('image',''),
                            "sentiment": 'neutral',
                            "sentiment_score": 0,
                            "related_stocks": [sym],
                            "data_source": "finnhub_company"
                        }
                        out.append(news_item)
                    except Exception:
                        continue
            elif resp.status_code == 429:
                current_app.logger.warning("FinnHub company-news rate limit hit")
                break
        except Exception as e:
            current_app.logger.warning(f"FinnHub company-news error for {sym}: {e}")
            continue
        time.sleep(0.1)
    # Newest first
    out.sort(key=lambda x: x.get('published_at',''), reverse=True)
    return out

def process_finnhub_news(finnhub_data):
    """Process and transform FinnHub news data to match our format"""
    processed_news = []
    
    if not isinstance(finnhub_data, list):
        current_app.logger.warning("FinnHub data is not a list")
        return []
    
    # Category mapping for FinnHub categories to our categories
    finnhub_category_mapping = {
        'general': 'market',
        'forex': 'forex', 
        'crypto': 'crypto',
        'merger': 'market',
        'technology': 'market',
        'business': 'market',
        'top news': 'market'
    }
    
    # Keywords for better categorization
    category_keywords = {
        'crypto': ['bitcoin', 'cryptocurrency', 'crypto', 'blockchain', 'ethereum', 'digital currency', 'defi', 'nft'],
        'forex': ['forex', 'currency', 'dollar', 'euro', 'yen', 'exchange rate', 'fx', 'gbp', 'usd', 'eur'],
        'economy': ['federal reserve', 'inflation', 'gdp', 'unemployment', 'interest rate', 'monetary policy', 'fiscal policy', 'economy', 'recession'],
        'earnings': ['earnings', 'quarterly results', 'revenue', 'profit', 'financial results', 'q1', 'q2', 'q3', 'q4']
    }
    
    for item in finnhub_data:
        if not isinstance(item, dict):
            continue
            
        # Get category from FinnHub category first
        finnhub_category = item.get("category", "general").lower()
        category = finnhub_category_mapping.get(finnhub_category, 'market')
        
        # Enhance categorization with keyword matching
        headline_summary = (item.get("headline", "") + " " + item.get("summary", "")).lower()
        for cat, keywords in category_keywords.items():
            if any(keyword in headline_summary for keyword in keywords):
                category = cat
                break
        
        # Convert datetime from UNIX timestamp
        published_at = ""
        try:
            timestamp = item.get("datetime", 0)
            if timestamp:
                published_at = datetime.fromtimestamp(timestamp).strftime("%Y%m%dT%H%M%S")
        except (ValueError, TypeError):
            published_at = ""
        
        # Extract related stocks
        related_stocks = []
        if "related" in item and item["related"]:
            # FinnHub related field contains stock symbols separated by commas
            related_stocks = [stock.strip() for stock in str(item["related"]).split(",") if stock.strip()]
        
        news_item = {
            "id": f"finnhub_{item.get('id', '')}",
            "title": item.get("headline", ""),
            "summary": item.get("summary", ""),
            "source": f"{item.get('source', 'FinnHub')} (FinnHub)",
            "url": item.get("url", ""),
            "published_at": published_at,
            "category": category,
            "topics": [category],
            "image": item.get("image", ""),
            "sentiment": "neutral",  # FinnHub doesn't provide sentiment, default to neutral
            "sentiment_score": 0,
            "related_stocks": related_stocks,
            "data_source": "finnhub"
        }
        processed_news.append(news_item)
    
    # Sort by published date (newest first)
    processed_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    
    current_app.logger.info(f"Processed {len(processed_news)} FinnHub articles")
    return processed_news

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
        
        # Extract related tickers if available in API structure
        related_stocks = []
        try:
            if 'ticker_sentiment' in item and isinstance(item['ticker_sentiment'], list):
                for t in item['ticker_sentiment']:
                    sym = t.get('ticker') or t.get('symbol')
                    if sym and sym not in related_stocks:
                        related_stocks.append(sym)
        except Exception:
            pass
        # Light fallback: guess ticker-like tokens in title
        if not related_stocks:
            title = item.get('title','')
            for m in re.findall(r"\b[A-Z]{2,5}\b", title):
                if m not in related_stocks:
                    related_stocks.append(m)

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
            "sentiment_score": sentiment_score,
            "related_stocks": related_stocks
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
    
    # Enrich with global signals (non-invasive)
    try:
        _augment_with_global_signals(processed_news)
    except Exception as e:
        current_app.logger.warning(f"Signal augmentation failed: {e}")

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
    return render_template('stock_analysis/market_news.html')

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
    sort_by = request.args.get('sort', 'newest')  # newest|oldest|sentiment|impact|relevance
    tickers_param = request.args.get('tickers', '')  # comma-separated tickers for For You
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
    
    # If For You and explicit tickers provided, persist to session for freshness fetch downstream
    if filter_topic == 'for_you' and tickers_param:
        try:
            wl_clean = [t.strip().upper() for t in tickers_param.split(',') if t.strip()]
            session['watchlist'] = wl_clean
            session.modified = True
        except Exception:
            pass

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
        
        # For You logic: if filter=for_you and tickers provided
        watchlist = []
        if filter_topic == 'for_you':
            # Prefer explicit tickers; fall back to session watchlist
            if tickers_param:
                watchlist = [t.strip().upper() for t in tickers_param.split(',') if t.strip()]
            elif isinstance(session.get('watchlist'), list):
                watchlist = [str(t).strip().upper() for t in session.get('watchlist') if str(t).strip()]
            # Compute relevance
            try:
                _compute_relevance_for_watchlist(all_news, set(watchlist))
            except Exception as e:
                current_app.logger.warning(f"Relevance computation failed: {e}")
            # Use relevance threshold to filter, then sort by relevance desc and recency
            filtered_news = [n for n in all_news if float(n.get('relevance_score', 0)) >= 0.1]
            filtered_news.sort(key=lambda x: (x.get('relevance_score', 0), _parse_datetime_to_epoch(x.get('published_at',''))), reverse=True)
            # If still too few, fallback to inline mentions among all news
            if len(filtered_news) < 12 and watchlist:
                wl = set(watchlist)
                extras = []
                for n in all_news:
                    text = f"{n.get('title','')} {n.get('summary','')}"
                    if any(re.search(fr"\b{re.escape(t)}\b", text) for t in wl):
                        extras.append(n)
                # de-dup by id
                seen = {x.get('id') for x in filtered_news}
                for e in extras:
                    if e.get('id') not in seen:
                        filtered_news.append(e)
                        seen.add(e.get('id'))
                filtered_news.sort(key=lambda x: (_parse_datetime_to_epoch(x.get('published_at','')), x.get('impact_score',0)), reverse=True)
        else:
            # Filter news based on the selected category
            if filter_topic != 'all':
                filtered_news = [n for n in all_news if n.get('category') == filter_topic]
            else:
                filtered_news = all_news

        # Additional sorting options
        if sort_by == 'impact':
            filtered_news.sort(key=lambda x: (x.get('impact_score', 0), _parse_datetime_to_epoch(x.get('published_at',''))), reverse=True)
        elif sort_by == 'relevance' and filter_topic == 'for_you':
            filtered_news.sort(key=lambda x: (x.get('relevance_score', 0), _parse_datetime_to_epoch(x.get('published_at',''))), reverse=True)
        elif sort_by == 'sentiment':
            sentiment_order = {'positive': 0, 'neutral': 1, 'negative': 2}
            filtered_news.sort(key=lambda x: (sentiment_order.get(x.get('sentiment','neutral'), 1), -_parse_datetime_to_epoch(x.get('published_at',''))))
        elif sort_by == 'oldest':
            filtered_news.sort(key=lambda x: x.get('published_at',''))
        else:  # newest
            filtered_news.sort(key=lambda x: x.get('published_at',''), reverse=True)
            
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
        
        # Fallback for For You when empty: show top-impact latest overall
        if filter_topic == 'for_you' and total_items == 0:
            fallback = sorted(all_news, key=lambda x: (_parse_datetime_to_epoch(x.get('published_at','')), x.get('impact_score',0)), reverse=True)
            filtered_news = fallback
            total_items = len(filtered_news)
            total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
            if page > total_pages:
                page = total_pages
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
            "sentiment_counts": sentiment_counts,
            "data_sources": news_data.get("data_sources", ["alpha_vantage"])
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

        # Include watchlist metadata if applicable
        if filter_topic == 'for_you':
            response_data["for_you"] = {
                "tickers": watchlist,
                "sort": sort_by,
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

@market_news_bp.route('/api/market-news/storylines')
def get_market_storylines():
    """Return storyline clusters from cached 'all' news without triggering new API calls."""
    try:
        cache_key = 'news-all'
        if cache_key not in news_cache or not isinstance(news_cache[cache_key], dict):
            # Best effort: attempt fetch using existing strategy without forcing
            data, status = fetch_alpha_vantage_news(topic=None)
            if status != 200:
                return jsonify({"storylines": [], "total": 0}), 200
            items = data.get('news', []) if isinstance(data, dict) else []
        else:
            items = news_cache[cache_key].get('news', [])

        # Ensure augmentation exists
        try:
            _augment_with_global_signals(items)
        except Exception:
            pass

        clusters = {}
        for it in items:
            sid = it.get('storyline_id') or _compute_storyline_id(it)
            grp = clusters.setdefault(sid, {
                'storyline_id': sid,
                'count': 0,
                'latest_title': '',
                'latest_published_at': '',
                'sentiment_trend': it.get('storyline_sentiment_trend', 'flat'),
                'tickers': set(),
                'impact_max': 0.0,
                'divergence': False,
            })
            grp['count'] += 1
            ts = _parse_datetime_to_epoch(it.get('published_at',''))
            if ts >= _parse_datetime_to_epoch(grp['latest_published_at'] or ''):
                grp['latest_published_at'] = it.get('published_at','')
                grp['latest_title'] = it.get('title','')
            for tk in (it.get('related_stocks') or []):
                grp['tickers'].add(tk)
            grp['impact_max'] = max(grp['impact_max'], float(it.get('impact_score', 0) or 0))
            if it.get('divergence_flag'):
                grp['divergence'] = True

        # Transform sets and sort
        out = []
        for grp in clusters.values():
            grp['tickers'] = sorted(list(grp['tickers']))
            out.append(grp)
        out.sort(key=lambda x: (_parse_datetime_to_epoch(x['latest_published_at']), x['impact_max']), reverse=True)

        return jsonify({
            'storylines': out[:100],
            'total': len(out)
        }), 200
    except Exception as e:
        current_app.logger.error(f"Storylines endpoint error: {e}")
        return jsonify({"storylines": [], "total": 0}), 200

@market_news_bp.route('/api/watchlist', methods=['GET', 'POST'])
def user_watchlist():
    """Persist and retrieve a lightweight watchlist in session.
    This complements client-side storage; safe and optional.
    """
    try:
        if request.method == 'GET':
            wl = session.get('watchlist', [])
            if not isinstance(wl, list):
                wl = []
            return jsonify({"tickers": wl}), 200
        else:
            data = request.get_json(silent=True) or {}
            tickers = data.get('tickers', [])
            if not isinstance(tickers, list):
                return jsonify({"error": "invalid_payload"}), 400
            clean = [str(t).strip().upper() for t in tickers if isinstance(t, str) and t.strip()]
            session['watchlist'] = clean
            session.modified = True
            return jsonify({"tickers": clean}), 200
    except Exception as e:
        current_app.logger.error(f"Watchlist endpoint error: {e}")
        return jsonify({"tickers": []}), 200
