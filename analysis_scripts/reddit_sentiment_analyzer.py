#!/usr/bin/env python3
"""
Reddit Sentiment Analyzer
=========================

Production-grade Reddit sentiment analysis with rate limiting, caching,
and robust error handling for tracking stock sentiment across Reddit communities.

Features:
---------
1. **Rate Limiting**: 1000 requests per 10 minutes (Reddit API limit)
2. **Caching**: 1-hour TTL to reduce API calls for popular tickers
3. **Cashtag Filtering**: Only counts posts with proper ticker mention ($AAPL)
4. **Quality Thresholds**: Filters low-quality posts (>3 comments required)
5. **Log-Weighted Scoring**: np.log1p(upvotes) to reduce outlier impact
6. **Multi-Subreddit Support**: r/wallstreetbets, r/stocks, r/investing

Configuration Required:
----------------------
Set environment variables or config file:
- REDDIT_CLIENT_ID: Your Reddit app client ID
- REDDIT_CLIENT_SECRET: Your Reddit app client secret
- REDDIT_USER_AGENT: Your app user agent (e.g., "TickZen/1.0")

Usage:
------
```python
from reddit_sentiment_analyzer import RedditSentimentAnalyzer

analyzer = RedditSentimentAnalyzer()
result = analyzer.analyze_ticker_sentiment('AAPL')

print(f"Sentiment Score: {result['score']}")
print(f"Mention Count: {result['mention_count']}")
print(f"Confidence: {result['confidence']}")
```

Author: TickZen Engineering Team
Version: 1.0
Created: February 9, 2026
Phase: Phase 3, Day 1
"""

import os
import time
import json
import hashlib
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional, Any
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Reddit API imports (will be installed)
try:
    import praw
    from praw.exceptions import PRAWException
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    print("Warning: praw not installed. Run: pip install praw")


class RateLimiter:
    """
    Token bucket rate limiter for Reddit API.
    Allows 1000 requests per 10 minutes as per Reddit API guidelines.
    """
    
    def __init__(self, max_requests: int = 1000, time_window: int = 600):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window: Time window in seconds (default 600 = 10 minutes)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = deque()
    
    def can_make_request(self) -> bool:
        """
        Check if a request can be made without exceeding rate limit.
        
        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        
        # Remove timestamps outside the time window
        while self.request_times and self.request_times[0] < now - self.time_window:
            self.request_times.popleft()
        
        return len(self.request_times) < self.max_requests
    
    def record_request(self):
        """Record that a request was made."""
        self.request_times.append(time.time())
    
    def wait_time(self) -> float:
        """
        Calculate time to wait before next request can be made.
        
        Returns:
            Seconds to wait, 0 if request can be made immediately
        """
        if self.can_make_request():
            return 0.0
        
        # Calculate when oldest request will expire
        oldest_request = self.request_times[0]
        wait_seconds = (oldest_request + self.time_window) - time.time()
        return max(0.0, wait_seconds)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current rate limiter statistics.
        
        Returns:
            Dictionary with request count, limit, and window info
        """
        now = time.time()
        # Clean old requests
        while self.request_times and self.request_times[0] < now - self.time_window:
            self.request_times.popleft()
        
        return {
            'requests_used': len(self.request_times),
            'requests_remaining': self.max_requests - len(self.request_times),
            'max_requests': self.max_requests,
            'time_window_seconds': self.time_window,
            'wait_time_seconds': self.wait_time()
        }


class SentimentCache:
    """
    In-memory cache for Reddit sentiment with TTL support.
    Reduces API calls for frequently queried tickers.
    """
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize sentiment cache.
        
        Args:
            ttl_seconds: Time-to-live in seconds (default 3600 = 1 hour)
        """
        self.ttl_seconds = ttl_seconds
        self.cache = {}  # {cache_key: {'data': result, 'timestamp': time}}
    
    def get(self, key: str) -> Optional[Dict]:
        """
        Retrieve cached sentiment if not expired.
        
        Args:
            key: Cache key (typically ticker symbol)
            
        Returns:
            Cached sentiment data or None if not found/expired
        """
        if key not in self.cache:
            return None
        
        cached_item = self.cache[key]
        age = time.time() - cached_item['timestamp']
        
        if age > self.ttl_seconds:
            # Expired, remove from cache
            del self.cache[key]
            return None
        
        return cached_item['data']
    
    def set(self, key: str, data: Dict):
        """
        Store sentiment in cache.
        
        Args:
            key: Cache key (typically ticker symbol)
            data: Sentiment data to cache
        """
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def clear(self):
        """Clear all cached data."""
        self.cache.clear()
    
    def cleanup_expired(self):
        """Remove all expired cache entries."""
        now = time.time()
        expired_keys = [
            key for key, value in self.cache.items()
            if now - value['timestamp'] > self.ttl_seconds
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache size, hits, and other metrics
        """
        now = time.time()
        self.cleanup_expired()
        
        return {
            'total_entries': len(self.cache),
            'ttl_seconds': self.ttl_seconds,
            'oldest_entry_age': min([now - v['timestamp'] for v in self.cache.values()]) if self.cache else 0
        }


class RedditSentimentAnalyzer:
    """
    Production-grade Reddit sentiment analyzer with rate limiting and caching.
    """
    
    # Subreddits to monitor for stock sentiment
    TARGET_SUBREDDITS = [
        'wallstreetbets',
        'stocks',
        'investing',
        'StockMarket',
        'options'
    ]
    
    # Quality thresholds
    MIN_COMMENT_COUNT = 3  # Filter out low-engagement posts
    MIN_MENTIONS_FOR_CONFIDENCE = 5  # Minimum mentions to report confident sentiment
    
    def __init__(self, client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None, 
                 user_agent: Optional[str] = None):
        """
        Initialize Reddit sentiment analyzer.
        
        Args:
            client_id: Reddit API client ID (or set REDDIT_CLIENT_ID env var)
            client_secret: Reddit API client secret (or set REDDIT_CLIENT_SECRET env var)
            user_agent: Reddit API user agent (or set REDDIT_USER_AGENT env var)
        """
        # Get credentials from parameters or environment variables
        self.client_id = client_id or os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('REDDIT_CLIENT_SECRET')
        self.user_agent = user_agent or os.getenv('REDDIT_USER_AGENT', 'TickZen/1.0')
        
        # Initialize components
        self.rate_limiter = RateLimiter(max_requests=1000, time_window=600)
        self.cache = SentimentCache(ttl_seconds=3600)
        self.vader = SentimentIntensityAnalyzer()
        
        # Reddit API client (initialized lazily)
        self._reddit = None
        
        # Statistics tracking
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'rate_limit_waits': 0
        }
    
    @property
    def reddit(self):
        """
        Lazy initialization of Reddit API client.
        
        Returns:
            Authenticated Reddit API client
            
        Raises:
            ValueError: If credentials are not configured
            ImportError: If praw is not installed
        """
        if self._reddit is None:
            if not PRAW_AVAILABLE:
                raise ImportError("praw library not installed. Run: pip install praw")
            
            if not all([self.client_id, self.client_secret]):
                raise ValueError(
                    "Reddit API credentials not configured. "
                    "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables, "
                    "or pass them to __init__()"
                )
            
            self._reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
        
        return self._reddit
    
    def _wait_for_rate_limit(self):
        """Wait if rate limit is reached."""
        wait_time = self.rate_limiter.wait_time()
        if wait_time > 0:
            self.stats['rate_limit_waits'] += 1
            print(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)
    
    def _normalize_ticker(self, ticker: str) -> str:
        """
        Normalize ticker symbol for consistency.
        
        Args:
            ticker: Raw ticker symbol
            
        Returns:
            Normalized ticker (uppercase, no $)
        """
        return ticker.upper().replace('$', '').strip()
    
    def _contains_cashtag(self, text: str, ticker: str) -> bool:
        """
        Check if text contains ticker cashtag ($AAPL style).
        
        Args:
            text: Text to search
            ticker: Ticker symbol to look for
            
        Returns:
            True if cashtag found, False otherwise
        """
        cashtag = f"${ticker}"
        return cashtag.upper() in text.upper()
    
    def _calculate_log_weighted_score(self, upvotes: int, sentiment: float) -> float:
        """
        Calculate log-weighted sentiment to reduce outlier impact.
        
        Args:
            upvotes: Number of upvotes
            sentiment: Raw sentiment score (-1 to 1)
            
        Returns:
            Weighted sentiment contribution
        """
        weight = np.log1p(upvotes)  # log(1 + upvotes) to handle 0 upvotes
        return sentiment * weight
    
    def analyze_ticker_sentiment(self, ticker: str, lookback_hours: int = 24,
                                 limit_per_subreddit: int = 100) -> Dict[str, Any]:
        """
        Analyze Reddit sentiment for a ticker symbol.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            lookback_hours: Hours to look back for posts (default 24)
            limit_per_subreddit: Max posts to fetch per subreddit (default 100)
            
        Returns:
            Dictionary containing:
                - score: Sentiment score (-1 to 1)
                - classification: 'positive', 'negative', or 'neutral'
                - confidence: Confidence level (0 to 1)
                - mention_count: Number of valid mentions found
                - post_count: Number of posts analyzed
                - top_post: Summary of most upvoted mention
                - source: 'reddit'
        """
        ticker = self._normalize_ticker(ticker)
        
        # Check cache first
        cache_key = f"{ticker}_{lookback_hours}h"
        cached_result = self.cache.get(cache_key)
        
        if cached_result is not None:
            self.stats['cache_hits'] += 1
            cached_result['from_cache'] = True
            return cached_result
        
        self.stats['cache_misses'] += 1
        
        # Fetch and analyze Reddit data
        try:
            result = self._fetch_and_analyze(ticker, lookback_hours, limit_per_subreddit)
            
            # Cache the result
            self.cache.set(cache_key, result)
            
            return result
            
        except Exception as e:
            # Return error result
            return {
                'score': 0.0,
                'classification': 'neutral',
                'confidence': 0.0,
                'mention_count': 0,
                'post_count': 0,
                'error': str(e),
                'source': 'reddit'
            }
    
    def _fetch_and_analyze(self, ticker: str, lookback_hours: int,
                          limit_per_subreddit: int) -> Dict[str, Any]:
        """
        Internal method to fetch and analyze Reddit posts.
        
        Args:
            ticker: Normalized ticker symbol
            lookback_hours: Hours to look back
            limit_per_subreddit: Max posts per subreddit
            
        Returns:
            Analysis result dictionary
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        all_mentions = []
        total_posts_checked = 0
        top_post = None
        max_upvotes = 0
        
        for subreddit_name in self.TARGET_SUBREDDITS:
            try:
                # Rate limit check
                self._wait_for_rate_limit()
                
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Fetch recent hot posts
                for post in subreddit.hot(limit=limit_per_subreddit):
                    self.rate_limiter.record_request()
                    self.stats['api_calls'] += 1
                    
                    total_posts_checked += 1
                    
                    # Check if post is within time range
                    post_time = datetime.utcfromtimestamp(post.created_utc)
                    if post_time < cutoff_time:
                        continue
                    
                    # Quality filter: Must have minimum comments
                    if post.num_comments < self.MIN_COMMENT_COUNT:
                        continue
                    
                    # Check for ticker cashtag in title or selftext
                    text = f"{post.title} {post.selftext}"
                    
                    if not self._contains_cashtag(text, ticker):
                        continue
                    
                    # Valid mention found - analyze sentiment
                    sentiment_scores = self.vader.polarity_scores(text)
                    compound_score = sentiment_scores['compound']
                    
                    weighted_score = self._calculate_log_weighted_score(
                        post.score, compound_score
                    )
                    
                    all_mentions.append({
                        'text': post.title,
                        'sentiment': compound_score,
                        'weighted_sentiment': weighted_score,
                        'upvotes': post.score,
                        'comments': post.num_comments,
                        'subreddit': subreddit_name,
                        'created': post_time
                    })
                    
                    # Track top post
                    if post.score > max_upvotes:
                        max_upvotes = post.score
                        top_post = {
                            'title': post.title,
                            'upvotes': post.score,
                            'sentiment': compound_score,
                            'subreddit': subreddit_name
                        }
            
            except PRAWException as e:
                print(f"Error fetching from r/{subreddit_name}: {e}")
                continue
        
        # Calculate aggregate sentiment
        mention_count = len(all_mentions)
        
        if mention_count == 0:
            return {
                'score': 0.0,
                'classification': 'neutral',
                'confidence': 0.0,
                'mention_count': 0,
                'post_count': total_posts_checked,
                'source': 'reddit',
                'message': f'No mentions of ${ticker} found in last {lookback_hours} hours'
            }
        
        # Calculate weighted average sentiment
        total_weight = sum(mention['weighted_sentiment'] for mention in all_mentions)
        total_log_upvotes = sum(np.log1p(mention['upvotes']) for mention in all_mentions)
        
        if total_log_upvotes > 0:
            avg_sentiment = total_weight / total_log_upvotes
        else:
            avg_sentiment = np.mean([m['sentiment'] for m in all_mentions])
        
        # Determine classification
        if avg_sentiment > 0.1:
            classification = 'positive'
        elif avg_sentiment < -0.1:
            classification = 'negative'
        else:
            classification = 'neutral'
        
        # Calculate confidence based on mention count and sentiment consistency
        if mention_count < self.MIN_MENTIONS_FOR_CONFIDENCE:
            confidence = mention_count / self.MIN_MENTIONS_FOR_CONFIDENCE * 0.5
        else:
            # High confidence if many mentions with consistent sentiment
            sentiment_std = np.std([m['sentiment'] for m in all_mentions])
            consistency_factor = max(0, 1 - sentiment_std)
            confidence = min(0.5 + (consistency_factor * 0.5), 1.0)
        
        result = {
            'score': float(avg_sentiment),
            'classification': classification,
            'confidence': float(confidence),
            'mention_count': mention_count,
            'post_count': total_posts_checked,
            'source': 'reddit',
            'top_post': top_post,
            'from_cache': False
        }
        
        return result
    
    def get_analyzer_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive analyzer statistics.
        
        Returns:
            Dictionary with API calls, cache stats, rate limit info
        """
        return {
            'api_stats': self.stats,
            'cache_stats': self.cache.get_stats(),
            'rate_limit_stats': self.rate_limiter.get_stats()
        }
    
    def clear_cache(self):
        """Clear all cached sentiment data."""
        self.cache.clear()


# Example usage and testing
if __name__ == "__main__":
    print("Reddit Sentiment Analyzer - Phase 3, Day 1")
    print("=" * 60)
    print("\nThis module requires Reddit API credentials.")
    print("\nSetup Instructions:")
    print("1. Go to https://www.reddit.com/prefs/apps")
    print("2. Create a new app (script type)")
    print("3. Note your client_id and client_secret")
    print("4. Set environment variables:")
    print("   - REDDIT_CLIENT_ID")
    print("   - REDDIT_CLIENT_SECRET")
    print("   - REDDIT_USER_AGENT (optional)")
    print("\nExample:")
    print("  export REDDIT_CLIENT_ID='your_client_id'")
    print("  export REDDIT_CLIENT_SECRET='your_secret'")
    print("  export REDDIT_USER_AGENT='TickZen/1.0'")
    print("\n" + "=" * 60)
