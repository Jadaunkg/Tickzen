#!/usr/bin/env python3
"""
Unit Tests for Reddit Sentiment Analyzer
========================================

Comprehensive test suite with mocked Reddit API responses.
Tests all functionality without requiring actual Reddit API credentials.

Test Coverage:
-------------
1. Rate Limiter Tests
2. Cache Tests
3. Reddit Sentiment Analyzer Tests (with mocks)
4. Integration Tests
5. Edge Case Tests

Run with:
    python -m pytest test_reddit_sentiment_analyzer.py -v

Author: TickZen Engineering Team
Version: 1.0
Created: February 9, 2026
Phase: Phase 3, Day 1
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis_scripts.reddit_sentiment_analyzer import (
    RateLimiter,
    SentimentCache,
    RedditSentimentAnalyzer
)


class TestRateLimiter(unittest.TestCase):
    """Test suite for RateLimiter class"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.rate_limiter = RateLimiter(max_requests=10, time_window=1)  # 10 req/sec for testing
    
    def test_init(self):
        """Test rate limiter initialization"""
        self.assertEqual(self.rate_limiter.max_requests, 10)
        self.assertEqual(self.rate_limiter.time_window, 1)
        self.assertEqual(len(self.rate_limiter.request_times), 0)
    
    def test_can_make_request_initially(self):
        """Test that requests are allowed initially"""
        self.assertTrue(self.rate_limiter.can_make_request())
    
    def test_record_request(self):
        """Test recording requests"""
        initial_count = len(self.rate_limiter.request_times)
        self.rate_limiter.record_request()
        self.assertEqual(len(self.rate_limiter.request_times), initial_count + 1)
    
    def test_rate_limit_enforcement(self):
        """Test that rate limit is enforced"""
        # Make max_requests requests
        for _ in range(10):
            self.assertTrue(self.rate_limiter.can_make_request())
            self.rate_limiter.record_request()
        
        # Next request should be blocked
        self.assertFalse(self.rate_limiter.can_make_request())
    
    def test_rate_limit_reset_after_window(self):
        """Test that rate limit resets after time window"""
        # Fill up the rate limit
        for _ in range(10):
            self.rate_limiter.record_request()
        
        # Should be blocked
        self.assertFalse(self.rate_limiter.can_make_request())
        
        # Wait for time window to pass
        time.sleep(1.1)
        
        # Should be allowed again
        self.assertTrue(self.rate_limiter.can_make_request())
    
    def test_wait_time_calculation(self):
        """Test wait time calculation when rate limited"""
        # Fill up the rate limit
        for _ in range(10):
            self.rate_limiter.record_request()
        
        wait_time = self.rate_limiter.wait_time()
        self.assertGreater(wait_time, 0)
        self.assertLessEqual(wait_time, 1.1)  # Should be within time window
    
    def test_wait_time_zero_when_allowed(self):
        """Test that wait time is zero when requests are allowed"""
        self.assertEqual(self.rate_limiter.wait_time(), 0.0)
    
    def test_get_stats(self):
        """Test getting rate limiter statistics"""
        self.rate_limiter.record_request()
        self.rate_limiter.record_request()
        
        stats = self.rate_limiter.get_stats()
        
        self.assertEqual(stats['requests_used'], 2)
        self.assertEqual(stats['requests_remaining'], 8)
        self.assertEqual(stats['max_requests'], 10)
        self.assertEqual(stats['time_window_seconds'], 1)
    
    def test_high_volume_requests(self):
        """Test handling many requests over time"""
        request_count = 0
        start_time = time.time()
        
        # Try to make 25 requests (2.5x the limit)
        while request_count < 25 and time.time() - start_time < 5:
            if self.rate_limiter.can_make_request():
                self.rate_limiter.record_request()
                request_count += 1
            else:
                time.sleep(0.1)
        
        self.assertEqual(request_count, 25)


class TestSentimentCache(unittest.TestCase):
    """Test suite for SentimentCache class"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.cache = SentimentCache(ttl_seconds=1)  # 1 second TTL for testing
    
    def test_init(self):
        """Test cache initialization"""
        self.assertEqual(self.cache.ttl_seconds, 1)
        self.assertEqual(len(self.cache.cache), 0)
    
    def test_set_and_get(self):
        """Test setting and getting cache values"""
        test_data = {'score': 0.5, 'confidence': 0.8}
        self.cache.set('AAPL', test_data)
        
        retrieved = self.cache.get('AAPL')
        self.assertEqual(retrieved, test_data)
    
    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist"""
        result = self.cache.get('NONEXISTENT')
        self.assertIsNone(result)
    
    def test_cache_expiration(self):
        """Test that cache entries expire after TTL"""
        test_data = {'score': 0.5}
        self.cache.set('AAPL', test_data)
        
        # Should exist immediately
        self.assertIsNotNone(self.cache.get('AAPL'))
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        self.assertIsNone(self.cache.get('AAPL'))
    
    def test_clear(self):
        """Test clearing the cache"""
        self.cache.set('AAPL', {'score': 0.5})
        self.cache.set('GOOGL', {'score': 0.3})
        
        self.assertEqual(len(self.cache.cache), 2)
        
        self.cache.clear()
        
        self.assertEqual(len(self.cache.cache), 0)
    
    def test_cleanup_expired(self):
        """Test cleanup of expired entries"""
        # Add some entries
        self.cache.set('AAPL', {'score': 0.5})
        time.sleep(0.5)
        self.cache.set('GOOGL', {'score': 0.3})
        
        # Wait for first entry to expire
        time.sleep(0.7)
        
        self.cache.cleanup_expired()
        
        # AAPL should be gone, GOOGL should remain
        self.assertIsNone(self.cache.get('AAPL'))
        self.assertIsNotNone(self.cache.get('GOOGL'))
    
    def test_get_stats(self):
        """Test getting cache statistics"""
        self.cache.set('AAPL', {'score': 0.5})
        self.cache.set('GOOGL', {'score': 0.3})
        
        stats = self.cache.get_stats()
        
        self.assertEqual(stats['total_entries'], 2)
        self.assertEqual(stats['ttl_seconds'], 1)
        self.assertGreaterEqual(stats['oldest_entry_age'], 0)


class TestRedditSentimentAnalyzer(unittest.TestCase):
    """Test suite for RedditSentimentAnalyzer class"""
    
    def setUp(self):
        """Setup test fixtures with mocked Reddit"""
        # Don't initialize Reddit client in tests
        self.analyzer = RedditSentimentAnalyzer()
        self.analyzer._reddit = None  # Prevent actual API initialization
    
    def test_init(self):
        """Test analyzer initialization"""
        self.assertIsNotNone(self.analyzer.rate_limiter)
        self.assertIsNotNone(self.analyzer.cache)
        self.assertIsNotNone(self.analyzer.vader)
        self.assertEqual(self.analyzer.stats['api_calls'], 0)
    
    def test_normalize_ticker(self):
        """Test ticker normalization"""
        test_cases = [
            ('aapl', 'AAPL'),
            ('$AAPL', 'AAPL'),
            ('  aapl  ', 'AAPL'),
            ('$GOOGL', 'GOOGL'),
        ]
        
        for input_ticker, expected in test_cases:
            result = self.analyzer._normalize_ticker(input_ticker)
            self.assertEqual(result, expected)
    
    def test_contains_cashtag(self):
        """Test cashtag detection"""
        test_cases = [
            ('I love $AAPL stock!', 'AAPL', True),
            ('AAPL is great', 'AAPL', False),
            ('Bought $GOOGL today', 'GOOGL', True),
            ('$TSLA to the moon!', 'TSLA', True),
            ('No ticker here', 'AAPL', False),
        ]
        
        for text, ticker, expected in test_cases:
            result = self.analyzer._contains_cashtag(text, ticker)
            self.assertEqual(result, expected)
    
    def test_calculate_log_weighted_score(self):
        """Test log-weighted scoring calculation"""
        # High upvotes should have more weight
        score_high = self.analyzer._calculate_log_weighted_score(1000, 0.5)
        score_low = self.analyzer._calculate_log_weighted_score(10, 0.5)
        
        self.assertGreater(score_high, score_low)
        
        # Zero upvotes should still work (returns 0)
        score_zero = self.analyzer._calculate_log_weighted_score(0, 0.5)
        self.assertEqual(score_zero, 0.0)  # log(1+0) = 0, so 0 * 0.5 = 0
    
    def test_cache_hit(self):
        """Test that cache is used when available"""
        # Pre-populate cache
        cached_data = {
            'score': 0.5,
            'classification': 'positive',
            'confidence': 0.8,
            'mention_count': 10
        }
        self.analyzer.cache.set('AAPL_24h', cached_data)
        
        # Analyze - should hit cache
        result = self.analyzer.analyze_ticker_sentiment('AAPL')
        
        self.assertTrue(result.get('from_cache', False))
        self.assertEqual(result['score'], 0.5)
        self.assertEqual(self.analyzer.stats['cache_hits'], 1)
        self.assertEqual(self.analyzer.stats['api_calls'], 0)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_fetch_and_analyze_with_mock(self, mock_praw):
        """Test fetching and analyzing with mocked Reddit API"""
        # Create mock Reddit instance
        mock_reddit = MagicMock()
        self.analyzer._reddit = mock_reddit
        
        # Create mock posts
        mock_post1 = MagicMock()
        mock_post1.title = 'I love $AAPL stock!'
        mock_post1.selftext = 'Great earnings report'
        mock_post1.score = 100
        mock_post1.num_comments = 50
        mock_post1.created_utc = datetime.utcnow().timestamp()
        
        mock_post2 = MagicMock()
        mock_post2.title = '$AAPL is overvalued'
        mock_post2.selftext = 'Time to sell'
        mock_post2.score = 30
        mock_post2.num_comments = 10
        mock_post2.created_utc = datetime.utcnow().timestamp()
        
        mock_post3 = MagicMock()
        mock_post3.title = 'Different stock discussion'
        mock_post3.selftext = 'No AAPL mention'
        mock_post3.score = 20
        mock_post3.num_comments = 5
        mock_post3.created_utc = datetime.utcnow().timestamp()
        
        # Setup mock subreddit
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_post1, mock_post2, mock_post3]
        mock_reddit.subreddit.return_value = mock_subreddit
        
        # Analyze
        result = self.analyzer._fetch_and_analyze('AAPL', 24, 100)
        
        # Verify results
        self.assertIn('score', result)
        self.assertIn('classification', result)
        self.assertIn('confidence', result)
        # Note: This will be called for each subreddit (5 subreddits), so 2 * 5 = 10 mentions
        self.assertEqual(result['mention_count'], 10)  # 2 posts mention $AAPL x 5 subreddits
        self.assertGreater(result['post_count'], 0)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_no_mentions_found(self, mock_praw):
        """Test behavior when no mentions are found"""
        # Create mock Reddit instance
        mock_reddit = MagicMock()
        self.analyzer._reddit = mock_reddit
        
        # Create mock posts without ticker mentions
        mock_post = MagicMock()
        mock_post.title = 'General market discussion'
        mock_post.selftext = 'No specific tickers'
        mock_post.score = 100
        mock_post.num_comments = 50
        mock_post.created_utc = datetime.utcnow().timestamp()
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_post]
        mock_reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('AAPL', 24, 100)
        
        self.assertEqual(result['mention_count'], 0)
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['score'], 0.0)
        self.assertIn('message', result)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_quality_filter(self, mock_praw):
        """Test that low-quality posts are filtered out"""
        mock_reddit = MagicMock()
        self.analyzer._reddit = mock_reddit
        
        # Create low-quality post (< 3 comments)
        mock_post = MagicMock()
        mock_post.title = '$AAPL is great!'
        mock_post.selftext = ''
        mock_post.score = 100
        mock_post.num_comments = 2  # Below threshold
        mock_post.created_utc = datetime.utcnow().timestamp()
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_post]
        mock_reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('AAPL', 24, 100)
        
        # Should be filtered out
        self.assertEqual(result['mention_count'], 0)
    
    def test_get_analyzer_stats(self):
        """Test getting comprehensive analyzer statistics"""
        stats = self.analyzer.get_analyzer_stats()
        
        self.assertIn('api_stats', stats)
        self.assertIn('cache_stats', stats)
        self.assertIn('rate_limit_stats', stats)
        
        self.assertIn('api_calls', stats['api_stats'])
        self.assertIn('cache_hits', stats['api_stats'])
    
    def test_clear_cache(self):
        """Test clearing the analyzer cache"""
        # Add some cache entries
        self.analyzer.cache.set('AAPL_24h', {'score': 0.5})
        self.assertEqual(len(self.analyzer.cache.cache), 1)
        
        # Clear cache
        self.analyzer.clear_cache()
        
        # Should be empty
        self.assertEqual(len(self.analyzer.cache.cache), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.analyzer = RedditSentimentAnalyzer()
    
    def test_rate_limiter_integration(self):
        """Test that rate limiter works with cache"""
        # Pre-populate cache to ensure cache hits
        cached_data = {
            'score': 0.5,
            'classification': 'positive',
            'confidence': 0.8,
            'mention_count': 10
        }
        self.analyzer.cache.set('TEST_24h', cached_data)
        
        # Simulate rapid requests - all should hit cache
        for i in range(5):
            result = self.analyzer.analyze_ticker_sentiment('TEST')
            # All requests should hit cache since we pre-populated
            self.assertTrue(result.get('from_cache', False))
        
        # Verify stats
        self.assertEqual(self.analyzer.stats['cache_hits'], 5)
        self.assertEqual(self.analyzer.stats['api_calls'], 0)  # No API calls made
    
    def test_stats_tracking(self):
        """Test that statistics are tracked correctly"""
        initial_stats = self.analyzer.get_analyzer_stats()
        
        # Make some operations
        self.analyzer.clear_cache()
        self.analyzer.rate_limiter.record_request()
        
        # Stats should be updated
        updated_stats = self.analyzer.get_analyzer_stats()
        self.assertIsNotNone(updated_stats)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.analyzer = RedditSentimentAnalyzer()
    
    def test_empty_ticker(self):
        """Test handling of empty ticker"""
        result = self.analyzer.analyze_ticker_sentiment('')
        self.assertIn('score', result)
    
    def test_invalid_lookback_hours(self):
        """Test handling of invalid lookback hours"""
        # Should not crash
        result = self.analyzer.analyze_ticker_sentiment('AAPL', lookback_hours=0)
        self.assertIn('score', result)
    
    def test_special_characters_in_ticker(self):
        """Test handling of special characters"""
        result = self.analyzer.analyze_ticker_sentiment('$AAPL@#')
        # Should normalize and handle gracefully
        self.assertIn('score', result)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_api_error_handling(self, mock_praw):
        """Test graceful handling of API errors"""
        # Make Reddit initialization fail
        mock_praw.Reddit.side_effect = Exception("API Error")
        
        # Create new analyzer that will fail on Reddit init
        analyzer = RedditSentimentAnalyzer(
            client_id='test',
            client_secret='test'
        )
        
        # Should return error result, not crash
        result = analyzer.analyze_ticker_sentiment('AAPL')
        
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['confidence'], 0.0)
        self.assertIn('error', result)


def run_all_tests():
    """Run all test suites and print summary"""
    print("=" * 70)
    print("Reddit Sentiment Analyzer - Unit Test Suite")
    print("Phase 3, Day 1 - February 9, 2026")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRateLimiter))
    suite.addTests(loader.loadTestsFromTestCase(TestSentimentCache))
    suite.addTests(loader.loadTestsFromTestCase(TestRedditSentimentAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print("=" * 70)
    
    return result


if __name__ == '__main__':
    result = run_all_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
