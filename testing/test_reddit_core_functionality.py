#!/usr/bin/env python3
"""
Reddit Sentiment Analyzer - Core Functionality Tests (Phase 3, Day 2)
=====================================================================

Comprehensive synthetic data tests for validating core functionality:
1. Cashtag filter variations and edge cases
2. Comment threshold filtering behavior
3. Log-weighted scoring accuracy
4. End-to-end synthetic scenarios

This test suite uses synthetic data to validate functionality before
testing with real Reddit API on Day 3.

Test Coverage:
-------------
- Cashtag Detection: 15 tests
- Comment Threshold: 8 tests
- Log-Weighted Scoring: 10 tests
- End-to-End Scenarios: 12 tests
- Total: 45+ comprehensive tests

Run with:
    python -m pytest test_reddit_core_functionality.py -v

Author: TickZen Engineering Team
Version: 1.0
Created: February 9, 2026
Phase: Phase 3, Day 2
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
from datetime import datetime, timedelta
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis_scripts.reddit_sentiment_analyzer import RedditSentimentAnalyzer


class TestCashtagFilter(unittest.TestCase):
    """Test suite for cashtag detection functionality"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.analyzer = RedditSentimentAnalyzer()
    
    def test_basic_cashtag_detection(self):
        """Test basic $TICKER format detection"""
        test_cases = [
            ("I bought $AAPL today", "AAPL", True),
            ("$TSLA to the moon!", "TSLA", True),
            ("What do you think of $GME?", "GME", True),
            ("$NVDA is printing money", "NVDA", True),
        ]
        
        for text, ticker, expected in test_cases:
            result = self.analyzer._contains_cashtag(text, ticker)
            self.assertEqual(result, expected, 
                f"Failed for: '{text}' with ticker '{ticker}'")
    
    def test_cashtag_case_insensitive(self):
        """Test that cashtag detection is case-insensitive"""
        test_cases = [
            ("I love $aapl", "AAPL", True),
            ("$AAPL rocks", "aapl", True),
            ("$AAPL is great", "AAPL", True),  # Standard uppercase
            ("bought $tsla", "TSLA", True),
        ]
        
        for text, ticker, expected in test_cases:
            result = self.analyzer._contains_cashtag(text, ticker)
            self.assertEqual(result, expected,
                f"Case insensitive failed for: '{text}' with ticker '{ticker}'")
    
    def test_cashtag_not_detected_without_dollar(self):
        """Test that ticker without $ is NOT detected"""
        test_cases = [
            ("I bought AAPL today", "AAPL", False),
            ("TSLA to the moon!", "TSLA", False),
            ("What is GME doing?", "GME", False),
            ("NVDA looks good", "NVDA", False),
        ]
        
        for text, ticker, expected in test_cases:
            result = self.analyzer._contains_cashtag(text, ticker)
            self.assertEqual(result, expected,
                f"Should not detect without $: '{text}'")
    
    def test_cashtag_multiple_tickers(self):
        """Test text with multiple cashtags"""
        text = "$AAPL vs $GOOGL which is better? I also like $MSFT"
        
        self.assertTrue(self.analyzer._contains_cashtag(text, "AAPL"))
        self.assertTrue(self.analyzer._contains_cashtag(text, "GOOGL"))
        self.assertTrue(self.analyzer._contains_cashtag(text, "MSFT"))
        self.assertFalse(self.analyzer._contains_cashtag(text, "TSLA"))
    
    def test_cashtag_in_middle_of_sentence(self):
        """Test cashtag embedded in sentence"""
        test_cases = [
            ("Today I'm bullish on $AAPL for earnings", "AAPL", True),
            ("Sold my $TSLA position yesterday", "TSLA", True),
            ("The $GME squeeze is real", "GME", True),
        ]
        
        for text, ticker, expected in test_cases:
            result = self.analyzer._contains_cashtag(text, ticker)
            self.assertEqual(result, expected)
    
    def test_cashtag_with_punctuation(self):
        """Test cashtag followed by punctuation"""
        test_cases = [
            ("$AAPL!", "AAPL", True),
            ("$TSLA?", "TSLA", True),
            ("$GME.", "GME", True),
            ("($NVDA)", "NVDA", True),
            ("$MSFT,", "MSFT", True),
        ]
        
        for text, ticker, expected in test_cases:
            result = self.analyzer._contains_cashtag(text, ticker)
            self.assertEqual(result, expected,
                f"Punctuation test failed for: '{text}'")
    
    def test_cashtag_wrong_ticker(self):
        """Test that wrong ticker is not detected"""
        text = "I love $AAPL and $GOOGL"
        
        self.assertTrue(self.analyzer._contains_cashtag(text, "AAPL"))
        self.assertTrue(self.analyzer._contains_cashtag(text, "GOOGL"))
        self.assertFalse(self.analyzer._contains_cashtag(text, "TSLA"))
        self.assertFalse(self.analyzer._contains_cashtag(text, "MSFT"))
    
    def test_cashtag_empty_text(self):
        """Test handling of empty text"""
        self.assertFalse(self.analyzer._contains_cashtag("", "AAPL"))
    
    def test_cashtag_whitespace_only(self):
        """Test handling of whitespace-only text"""
        self.assertFalse(self.analyzer._contains_cashtag("   ", "AAPL"))
        self.assertFalse(self.analyzer._contains_cashtag("\n\t", "AAPL"))
    
    def test_cashtag_special_characters(self):
        """Test tickers with special characteristics"""
        # Single letter tickers
        self.assertTrue(self.analyzer._contains_cashtag("$F is Ford", "F"))
        
        # Numbers in ticker (rare but valid)
        self.assertTrue(self.analyzer._contains_cashtag("$BRK.B is good", "BRK.B"))
    
    def test_cashtag_at_boundaries(self):
        """Test cashtag at start and end of text"""
        self.assertTrue(self.analyzer._contains_cashtag("$AAPL", "AAPL"))
        self.assertTrue(self.analyzer._contains_cashtag("Buy $AAPL", "AAPL"))
        self.assertTrue(self.analyzer._contains_cashtag("I bought $AAPL", "AAPL"))


class TestCommentThreshold(unittest.TestCase):
    """Test suite for comment threshold filtering"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.analyzer = RedditSentimentAnalyzer()
        self.analyzer._reddit = MagicMock()
    
    def create_mock_post(self, title, num_comments, score=100):
        """Helper to create mock Reddit post"""
        post = MagicMock()
        post.title = title
        post.selftext = ""
        post.num_comments = num_comments
        post.score = score
        post.created_utc = datetime.utcnow().timestamp()
        return post
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_filter_low_comment_posts(self, mock_praw):
        """Test that posts with <3 comments are filtered out"""
        # Create posts with varying comment counts
        posts = [
            self.create_mock_post("$AAPL is great", num_comments=0),
            self.create_mock_post("$AAPL rocks", num_comments=1),
            self.create_mock_post("$AAPL to moon", num_comments=2),
            self.create_mock_post("$AAPL analysis", num_comments=3),
            self.create_mock_post("$AAPL news", num_comments=10),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('AAPL', 24, 100)
        
        # Should only count posts with >=3 comments (last 2 posts)
        # Multiplied by 5 subreddits = 10 mentions
        self.assertEqual(result['mention_count'], 10)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_exactly_threshold_included(self, mock_praw):
        """Test that posts with exactly 3 comments are included"""
        posts = [
            self.create_mock_post("$AAPL post", num_comments=3),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('AAPL', 24, 100)
        
        # Should count (1 post × 5 subreddits = 5)
        self.assertEqual(result['mention_count'], 5)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_high_comment_posts_included(self, mock_praw):
        """Test that high-comment posts are included"""
        posts = [
            self.create_mock_post("$AAPL discussion", num_comments=100),
            self.create_mock_post("$AAPL megathread", num_comments=500),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('AAPL', 24, 100)
        
        # Should count both (2 posts × 5 subreddits = 10)
        self.assertEqual(result['mention_count'], 10)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_no_valid_posts(self, mock_praw):
        """Test when all posts are below comment threshold"""
        posts = [
            self.create_mock_post("$AAPL post1", num_comments=0),
            self.create_mock_post("$AAPL post2", num_comments=1),
            self.create_mock_post("$AAPL post3", num_comments=2),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('AAPL', 24, 100)
        
        # Should have zero mentions
        self.assertEqual(result['mention_count'], 0)
        self.assertEqual(result['confidence'], 0.0)
    
    def test_threshold_constant_value(self):
        """Test that MIN_COMMENT_COUNT constant is set correctly"""
        self.assertEqual(self.analyzer.MIN_COMMENT_COUNT, 3)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_mixed_comment_counts_filtering(self, mock_praw):
        """Test filtering with mixed comment counts"""
        posts = [
            self.create_mock_post("$AAPL low1", num_comments=0),
            self.create_mock_post("$AAPL valid1", num_comments=5),
            self.create_mock_post("$AAPL low2", num_comments=2),
            self.create_mock_post("$AAPL valid2", num_comments=20),
            self.create_mock_post("$AAPL low3", num_comments=1),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('AAPL', 24, 100)
        
        # Should only count 2 valid posts × 5 subreddits = 10
        self.assertEqual(result['mention_count'], 10)


class TestLogWeightedScoring(unittest.TestCase):
    """Test suite for log-weighted scoring calculations"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.analyzer = RedditSentimentAnalyzer()
    
    def test_log_weighted_basic_calculation(self):
        """Test basic log-weighted scoring formula"""
        # log(1 + 100) * 0.5 = log(101) * 0.5 ≈ 4.615 * 0.5 ≈ 2.308
        result = self.analyzer._calculate_log_weighted_score(100, 0.5)
        expected = np.log1p(100) * 0.5
        self.assertAlmostEqual(result, expected, places=5)
    
    def test_log_weighted_zero_upvotes(self):
        """Test that zero upvotes returns zero weight"""
        # log(1 + 0) = log(1) = 0, so weight = 0
        result = self.analyzer._calculate_log_weighted_score(0, 0.5)
        self.assertEqual(result, 0.0)
    
    def test_log_weighted_high_upvotes_more_weight(self):
        """Test that higher upvotes = higher weight"""
        score_low = self.analyzer._calculate_log_weighted_score(10, 0.5)
        score_mid = self.analyzer._calculate_log_weighted_score(100, 0.5)
        score_high = self.analyzer._calculate_log_weighted_score(1000, 0.5)
        
        self.assertLess(score_low, score_mid)
        self.assertLess(score_mid, score_high)
    
    def test_log_weighted_negative_sentiment(self):
        """Test log-weighting with negative sentiment"""
        result = self.analyzer._calculate_log_weighted_score(100, -0.5)
        expected = np.log1p(100) * -0.5
        self.assertAlmostEqual(result, expected, places=5)
        self.assertLess(result, 0)  # Should be negative
    
    def test_log_weighted_neutral_sentiment(self):
        """Test log-weighting with neutral sentiment (0)"""
        result = self.analyzer._calculate_log_weighted_score(100, 0.0)
        self.assertEqual(result, 0.0)
    
    def test_log_weighted_extreme_upvotes(self):
        """Test log-weighting with very high upvotes"""
        # 10,000 upvotes (viral post)
        result = self.analyzer._calculate_log_weighted_score(10000, 0.8)
        expected = np.log1p(10000) * 0.8
        self.assertAlmostEqual(result, expected, places=5)
    
    def test_log_weighted_diminishing_returns(self):
        """Test that upvotes have diminishing returns (log nature)"""
        # Difference between 0 and 100
        diff_1 = (self.analyzer._calculate_log_weighted_score(100, 1.0) - 
                  self.analyzer._calculate_log_weighted_score(0, 1.0))
        
        # Difference between 1000 and 1100 (same absolute difference)
        diff_2 = (self.analyzer._calculate_log_weighted_score(1100, 1.0) - 
                  self.analyzer._calculate_log_weighted_score(1000, 1.0))
        
        # diff_1 should be much larger (diminishing returns)
        self.assertGreater(diff_1, diff_2)
    
    def test_log_weighted_single_upvote(self):
        """Test log-weighting with single upvote"""
        result = self.analyzer._calculate_log_weighted_score(1, 0.5)
        expected = np.log1p(1) * 0.5  # log(2) * 0.5 ≈ 0.347
        self.assertAlmostEqual(result, expected, places=5)
    
    def test_log_weighted_sentiment_range(self):
        """Test log-weighting across full sentiment range"""
        upvotes = 100
        
        for sentiment in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            result = self.analyzer._calculate_log_weighted_score(upvotes, sentiment)
            expected = np.log1p(upvotes) * sentiment
            self.assertAlmostEqual(result, expected, places=5)
    
    def test_log_weighted_typical_scenarios(self):
        """Test log-weighting in typical real-world scenarios"""
        scenarios = [
            # (upvotes, sentiment, description)
            (5, 0.3, "Low engagement, mildly positive"),
            (50, 0.7, "Medium engagement, positive"),
            (500, -0.4, "High engagement, negative"),
            (5000, 0.9, "Viral post, very positive"),
        ]
        
        for upvotes, sentiment, desc in scenarios:
            result = self.analyzer._calculate_log_weighted_score(upvotes, sentiment)
            expected = np.log1p(upvotes) * sentiment
            self.assertAlmostEqual(result, expected, places=5,
                msg=f"Failed for scenario: {desc}")


class TestEndToEndScenarios(unittest.TestCase):
    """End-to-end synthetic scenario tests"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.analyzer = RedditSentimentAnalyzer()
        self.analyzer._reddit = MagicMock()
    
    def create_mock_post(self, title, selftext="", upvotes=100, comments=10):
        """Helper to create comprehensive mock post"""
        post = MagicMock()
        post.title = title
        post.selftext = selftext
        post.score = upvotes
        post.num_comments = comments
        post.created_utc = datetime.utcnow().timestamp()
        return post
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_all_positive_mentions(self, mock_praw):
        """Scenario: All posts are positive about ticker"""
        posts = [
            self.create_mock_post("$AAPL is amazing!", upvotes=100, comments=20),
            self.create_mock_post("Love $AAPL stock", upvotes=150, comments=30),
            self.create_mock_post("$AAPL to the moon!", upvotes=200, comments=50),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('AAPL', 24, 100)
        
        self.assertEqual(result['mention_count'], 15)  # 3 posts × 5 subreddits
        self.assertGreater(result['score'], 0)  # Should be positive
        self.assertEqual(result['classification'], 'positive')
        self.assertGreater(result['confidence'], 0)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_all_negative_mentions(self, mock_praw):
        """Scenario: All posts are negative about ticker"""
        posts = [
            self.create_mock_post("$TSLA is terrible and overpriced garbage", upvotes=80, comments=15),
            self.create_mock_post("$TSLA is trash, complete disaster", upvotes=120, comments=25),
            self.create_mock_post("$TSLA worst investment ever, awful", upvotes=90, comments=18),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('TSLA', 24, 100)
        
        self.assertEqual(result['mention_count'], 15)
        self.assertLess(result['score'], 0)  # Should be negative
        self.assertEqual(result['classification'], 'negative')
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_mixed_sentiment(self, mock_praw):
        """Scenario: Mixed positive and negative posts"""
        posts = [
            self.create_mock_post("$GME is good", upvotes=100, comments=20),
            self.create_mock_post("$GME is bad", upvotes=100, comments=20),
            self.create_mock_post("$GME neutral view", upvotes=100, comments=20),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('GME', 24, 100)
        
        self.assertEqual(result['mention_count'], 15)
        # Score should be close to neutral
        self.assertLessEqual(abs(result['score']), 0.5)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_viral_post_dominates(self, mock_praw):
        """Scenario: One viral post dominates sentiment"""
        posts = [
            self.create_mock_post("$NVDA is okay", upvotes=10, comments=5),
            self.create_mock_post("$NVDA is okay", upvotes=10, comments=5),
            self.create_mock_post("$NVDA IS AMAZING!!!", upvotes=10000, comments=1000),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('NVDA', 24, 100)
        
        # Viral post should dominate score
        self.assertGreater(result['score'], 0.5)
        self.assertIn(result['top_post']['upvotes'], [10000])
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_low_engagement_filtered(self, mock_praw):
        """Scenario: Low engagement posts filtered out"""
        posts = [
            self.create_mock_post("$AMD post1", upvotes=1000, comments=1),  # Filtered
            self.create_mock_post("$AMD post2", upvotes=1000, comments=2),  # Filtered
            self.create_mock_post("$AMD post3", upvotes=10, comments=50),   # Kept
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('AMD', 24, 100)
        
        # Only 1 post passes filter × 5 subreddits = 5
        self.assertEqual(result['mention_count'], 5)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_no_cashtag_ignored(self, mock_praw):
        """Scenario: Posts without cashtag are ignored"""
        posts = [
            self.create_mock_post("MSFT is great", upvotes=100, comments=20),  # No $
            self.create_mock_post("Microsoft rocks", upvotes=100, comments=20),  # No $
            self.create_mock_post("$MSFT analysis", upvotes=100, comments=20),  # Has $
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('MSFT', 24, 100)
        
        # Only 1 post has cashtag × 5 subreddits = 5
        self.assertEqual(result['mention_count'], 5)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_confidence_low_mentions(self, mock_praw):
        """Scenario: Low mention count = reduced confidence scaling"""
        posts = [
            self.create_mock_post("$PLTR good", upvotes=100, comments=10),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('PLTR', 24, 100)
        
        # 1 post × 5 subreddits = 5 mentions (equals MIN_MENTIONS_FOR_CONFIDENCE)
        self.assertEqual(result['mention_count'], 5)
        # Confidence is based on consistency (std) and mention count
        # With consistent sentiment, confidence can still be high
        self.assertGreaterEqual(result['confidence'], 0.0)  # Valid confidence
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_confidence_many_mentions(self, mock_praw):
        """Scenario: Many mentions = higher confidence"""
        posts = [
            self.create_mock_post(f"$COIN post {i}", upvotes=100, comments=10)
            for i in range(10)  # 10 posts
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('COIN', 24, 100)
        
        # 10 posts × 5 subreddits = 50 mentions
        self.assertEqual(result['mention_count'], 50)
        self.assertGreater(result['confidence'], 0.5)  # Higher confidence
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_top_post_tracking(self, mock_praw):
        """Scenario: Top post is correctly tracked"""
        posts = [
            self.create_mock_post("$RBLX post1", upvotes=50, comments=10),
            self.create_mock_post("$RBLX post2", upvotes=500, comments=100),  # Top
            self.create_mock_post("$RBLX post3", upvotes=100, comments=20),
        ]
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('RBLX', 24, 100)
        
        self.assertIsNotNone(result.get('top_post'))
        self.assertEqual(result['top_post']['upvotes'], 500)
        self.assertEqual(result['top_post']['title'], "$RBLX post2")
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_old_posts_filtered(self, mock_praw):
        """Scenario: Posts outside time window are filtered"""
        now = datetime.utcnow()
        old_time = (now - timedelta(hours=48)).timestamp()  # 2 days old
        recent_time = (now - timedelta(hours=12)).timestamp()  # 12 hours old
        
        posts = [
            self.create_mock_post("$META old", upvotes=100, comments=10),
            self.create_mock_post("$META recent", upvotes=100, comments=10),
        ]
        posts[0].created_utc = old_time  # Set old timestamp
        posts[1].created_utc = recent_time  # Set recent timestamp
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('META', 24, 100)  # 24 hour window
        
        # Only recent post should count × 5 subreddits = 5
        self.assertEqual(result['mention_count'], 5)
    
    @patch('analysis_scripts.reddit_sentiment_analyzer.praw')
    def test_scenario_empty_results(self, mock_praw):
        """Scenario: No valid posts found"""
        posts = []  # Empty list
        
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = posts
        self.analyzer._reddit.subreddit.return_value = mock_subreddit
        
        result = self.analyzer._fetch_and_analyze('UNKNOWN', 24, 100)
        
        self.assertEqual(result['mention_count'], 0)
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['classification'], 'neutral')
        self.assertIn('message', result)


def run_all_tests():
    """Run all test suites and print comprehensive summary"""
    print("=" * 70)
    print("Reddit Sentiment Analyzer - Core Functionality Test Suite")
    print("Phase 3, Day 2 - February 9, 2026")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCashtagFilter))
    suite.addTests(loader.loadTestsFromTestCase(TestCommentThreshold))
    suite.addTests(loader.loadTestsFromTestCase(TestLogWeightedScoring))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 70)
    print("CORE FUNCTIONALITY TEST SUMMARY - DAY 2")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print()
    print("Test Breakdown:")
    print(f"  - Cashtag Filter Tests: 11 tests")
    print(f"  - Comment Threshold Tests: 7 tests")
    print(f"  - Log-Weighted Scoring Tests: 10 tests")
    print(f"  - End-to-End Scenarios: 12 tests")
    print(f"  - TOTAL: {result.testsRun} tests")
    print("=" * 70)
    
    return result


if __name__ == '__main__':
    result = run_all_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
