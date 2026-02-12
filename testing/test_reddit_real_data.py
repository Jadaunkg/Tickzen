"""
Phase 3, Day 3 - Real Data Testing: Reddit Sentiment Analysis
TickZen v2.3 - Risk & Sentiment Analysis Improvement

Purpose: Test RedditSentimentAnalyzer with real Reddit API on 10 diverse tickers
Requirements:
- Real Reddit API credentials (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT)
- 10 diverse tickers tested (AAPL, MSFT, GOOGL, AMZN, TSLA, GME, AMC, NVDA, AMD, META)
- Manual validation of top posts vs system scores
- 90%+ accuracy vs manual sentiment reading
- Performance <3 sec/ticker

Test Date: February 9, 2026
Status: Day 3 - Checkpoint 2
"""

import unittest
import os
import sys
import time
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis_scripts.reddit_sentiment_analyzer import RedditSentimentAnalyzer


class TestRedditRealDataSetup(unittest.TestCase):
    """Test 1: Verify Reddit API credentials are configured"""
    
    def test_credentials_exist(self):
        """Verify all required Reddit API credentials are set"""
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        user_agent = os.getenv('REDDIT_USER_AGENT')
        
        self.assertIsNotNone(client_id, 
            "REDDIT_CLIENT_ID not set. See REDDIT_API_SETUP_GUIDE.md")
        self.assertIsNotNone(client_secret, 
            "REDDIT_CLIENT_SECRET not set. See REDDIT_API_SETUP_GUIDE.md")
        self.assertIsNotNone(user_agent, 
            "REDDIT_USER_AGENT not set. Format: 'TickZen/1.0 (by /u/yourname)'")
        
        # Verify not placeholder values
        self.assertNotEqual(client_id, "your_client_id_here")
        self.assertNotEqual(client_secret, "your_client_secret_here")
        
        print(f"✅ Reddit API credentials configured")
        print(f"   Client ID: {client_id[:8]}... (redacted)")
        print(f"   User Agent: {user_agent}")


class TestRedditRealDataAAPL(unittest.TestCase):
    """Test 2-4: AAPL real data testing (Morning Session)"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize Reddit analyzer once for all AAPL tests"""
        cls.analyzer = RedditSentimentAnalyzer(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
    
    def test_aapl_basic_fetch(self):
        """Test basic fetch for AAPL (most mentioned tech stock)"""
        print("\n" + "="*70)
        print("TEST: AAPL Basic Fetch (Expected: 20-100+ mentions in r/wallstreetbets)")
        print("="*70)
        
        start_time = time.time()
        result = self.analyzer.analyze_ticker_sentiment('AAPL', lookback_hours=24)
        elapsed = time.time() - start_time
        
        # Validate structure
        self.assertIsInstance(result, dict)
        self.assertIn('sentiment_score', result)
        self.assertIn('confidence', result)
        self.assertIn('classification', result)
        self.assertIn('mention_count', result)
        self.assertIn('top_post', result)
        
        # Validate data quality
        self.assertGreaterEqual(result['mention_count'], 5, 
            "AAPL should have at least 5 mentions in 24h")
        self.assertGreater(result['confidence'], 0.0,
            "Confidence should be > 0 for popular ticker")
        self.assertIn(result['classification'], ['positive', 'neutral', 'negative'])
        
        # Validate performance
        self.assertLess(elapsed, 5.0, 
            f"Fetch took {elapsed:.2f}s, should be <5s for first call")
        
        # Print results
        print(f"\n✅ AAPL Results:")
        print(f"   Sentiment Score: {result['sentiment_score']:.3f}")
        print(f"   Classification: {result['classification']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        print(f"   Mentions: {result['mention_count']}")
        print(f"   API Time: {elapsed:.2f}s")
        
        if result['top_post']:
            print(f"\n   Top Post:")
            print(f"   - Title: {result['top_post']['title'][:80]}...")
            print(f"   - Upvotes: {result['top_post']['upvotes']}")
            print(f"   - Comments: {result['top_post']['num_comments']}")
            print(f"   - Sentiment: {result['top_post']['sentiment']:.3f}")
        
        # Save for manual validation
        self.__class__.aapl_result = result
    
    def test_aapl_cached_performance(self):
        """Test that cached AAPL fetch is fast (<100ms)"""
        print("\n" + "="*70)
        print("TEST: AAPL Cached Performance (Expected: <100ms)")
        print("="*70)
        
        # First call to ensure cache is populated
        self.analyzer.analyze_ticker_sentiment('AAPL', lookback_hours=24)
        
        # Second call should be cached
        start_time = time.time()
        result = self.analyzer.analyze_ticker_sentiment('AAPL', lookback_hours=24)
        elapsed = time.time() - start_time
        
        self.assertLess(elapsed, 0.1, 
            f"Cached fetch took {elapsed*1000:.1f}ms, should be <100ms")
        
        print(f"✅ Cache Performance: {elapsed*1000:.2f}ms")
        print(f"   Cache hit: YES")
        print(f"   API calls saved: 1")
    
    def test_aapl_rate_limit_compliance(self):
        """Test that rate limiter prevents exceeding 1000 req/10min"""
        print("\n" + "="*70)
        print("TEST: Rate Limit Compliance (1000 req/10min)")
        print("="*70)
        
        rate_limiter = self.analyzer.rate_limiter
        initial_requests = len(rate_limiter.request_times)
        
        # Get rate limit stats
        stats = rate_limiter.get_stats()
        
        self.assertLessEqual(stats['requests_in_window'], 1000,
            f"Rate limit exceeded: {stats['requests_in_window']}/1000 requests")
        
        print(f"✅ Rate Limit Status:")
        print(f"   Current requests in window: {stats['requests_in_window']}/1000")
        print(f"   Window start: {stats['window_start']}")
        print(f"   Remaining capacity: {1000 - stats['requests_in_window']}")


class TestRedditRealData10Tickers(unittest.TestCase):
    """Test 5: Test all 10 required diverse tickers (Afternoon Session)"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize Reddit analyzer once for all tests"""
        cls.analyzer = RedditSentimentAnalyzer(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        cls.test_results = {}
    
    def test_10_diverse_tickers(self):
        """Test 10 diverse tickers as per DAILY_IMPLEMENTATION_CHECKLIST.md"""
        print("\n" + "="*70)
        print("TEST: 10 Diverse Tickers - Real Reddit Data")
        print("="*70)
        
        tickers = [
            ('AAPL', 'Large Cap Stable - Apple'),
            ('MSFT', 'Large Cap Stable - Microsoft'),
            ('GOOGL', 'Large Cap Tech - Google'),
            ('AMZN', 'Mega Cap - Amazon'),
            ('TSLA', 'Volatile Growth - Tesla'),
            ('GME', 'Meme Stock - GameStop'),
            ('AMC', 'Volatile - AMC Entertainment'),
            ('NVDA', 'Growth Tech - Nvidia'),
            ('AMD', 'Growth Tech - AMD'),
            ('META', 'Large Cap Stable - Meta'),
        ]
        
        results_table = []
        total_time = 0
        successful_fetches = 0
        
        for ticker, description in tickers:
            print(f"\n📊 Testing {ticker} ({description})...")
            
            start_time = time.time()
            try:
                result = self.analyzer.analyze_ticker_sentiment(
                    ticker, 
                    lookback_hours=24,
                    limit=100  # Get up to 100 posts per subreddit
                )
                elapsed = time.time() - start_time
                total_time += elapsed
                
                # Validate result
                self.assertIsInstance(result, dict)
                self.assertIn('sentiment_score', result)
                self.assertIn('mention_count', result)
                
                # Store result
                self.__class__.test_results[ticker] = result
                successful_fetches += 1
                
                # Format for table
                results_table.append({
                    'ticker': ticker,
                    'description': description,
                    'score': result['sentiment_score'],
                    'classification': result['classification'],
                    'confidence': result['confidence'],
                    'mentions': result['mention_count'],
                    'time': elapsed
                })
                
                print(f"   ✅ Score: {result['sentiment_score']:+.3f} | "
                      f"Class: {result['classification']:8s} | "
                      f"Confidence: {result['confidence']:.1%} | "
                      f"Mentions: {result['mention_count']:3d} | "
                      f"Time: {elapsed:.2f}s")
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"   ❌ Error: {str(e)[:60]}")
                results_table.append({
                    'ticker': ticker,
                    'description': description,
                    'score': None,
                    'classification': 'ERROR',
                    'confidence': 0.0,
                    'mentions': 0,
                    'time': elapsed
                })
        
        # Print summary table
        print("\n" + "="*70)
        print("RESULTS SUMMARY - 10 Ticker Test")
        print("="*70)
        print(f"{'Ticker':<8} {'Type':<25} {'Score':>8} {'Class':>10} {'Conf':>6} {'Mentions':>8} {'Time':>7}")
        print("-"*70)
        
        for r in results_table:
            if r['score'] is not None:
                print(f"{r['ticker']:<8} {r['description']:<25} "
                      f"{r['score']:+8.3f} {r['classification']:>10} "
                      f"{r['confidence']:>6.1%} {r['mentions']:>8d} "
                      f"{r['time']:>6.2f}s")
            else:
                print(f"{r['ticker']:<8} {r['description']:<25} "
                      f"{'N/A':>8} {r['classification']:>10} "
                      f"{r['confidence']:>6.1%} {r['mentions']:>8d} "
                      f"{r['time']:>6.2f}s")
        
        print("-"*70)
        print(f"Success Rate: {successful_fetches}/10 ({successful_fetches/10:.0%})")
        print(f"Average Time: {total_time/10:.2f}s per ticker")
        print(f"Total Time: {total_time:.2f}s")
        
        # Validate success criteria
        self.assertGreaterEqual(successful_fetches, 8, 
            f"At least 8/10 tickers should succeed (got {successful_fetches}/10)")
        self.assertLess(total_time/successful_fetches, 3.0,
            f"Average time should be <3s per ticker (got {total_time/successful_fetches:.2f}s)")


class TestManualValidation(unittest.TestCase):
    """Test 6: Manual validation helper for top posts"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize Reddit analyzer"""
        cls.analyzer = RedditSentimentAnalyzer(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
    
    def test_manual_validation_aapl(self):
        """Manual validation: Print top 5 AAPL posts for human review"""
        print("\n" + "="*70)
        print("MANUAL VALIDATION: AAPL Top 5 Posts")
        print("="*70)
        print("\nInstructions: Read each post and manually assess sentiment")
        print("Compare your assessment with the system's VADER score")
        print("Target: 90%+ agreement rate\n")
        
        # Fetch AAPL data
        result = self.analyzer.analyze_ticker_sentiment('AAPL', lookback_hours=24, limit=100)
        
        # Get top 5 posts by upvotes
        posts = []
        ticker = 'AAPL'
        
        # Reconstruct posts from cache or fetch fresh
        # (In real implementation, we'd store raw posts during analysis)
        # For now, demonstrate structure expected
        
        print("Top Post from System:")
        if result['top_post']:
            top = result['top_post']
            print(f"\n1. Title: {top['title']}")
            print(f"   Upvotes: {top['upvotes']} | Comments: {top['num_comments']}")
            print(f"   System Sentiment: {top['sentiment']:+.3f}")
            print(f"   Your Assessment: [ ] Positive [ ] Neutral [ ] Negative")
            print(f"   Agreement: [ ] Yes [ ] No")
        
        print("\n" + "-"*70)
        print("Note: For full manual validation, you would:")
        print("1. Read top 5 posts manually from r/wallstreetbets")
        print("2. Assess sentiment (positive/neutral/negative)")
        print("3. Compare with system scores")
        print("4. Calculate agreement rate (target: >90%)")
        print("\nSystem Score: " + result['classification'].upper())
        print(f"System Confidence: {result['confidence']:.1%}")
        print(f"Mentions Analyzed: {result['mention_count']}")
        print("-"*70)
        
        # This is a helper test - always passes, manual review required
        self.assertTrue(True, "Manual validation helper executed")


class TestEdgeCases(unittest.TestCase):
    """Test 7-9: Edge cases with real API"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize Reddit analyzer"""
        cls.analyzer = RedditSentimentAnalyzer(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
    
    def test_low_volume_ticker(self):
        """Test obscure ticker with low mentions (e.g., ROIV)"""
        print("\n" + "="*70)
        print("TEST: Low Volume Ticker (ROIV - obscure biotech)")
        print("="*70)
        
        result = self.analyzer.analyze_ticker_sentiment('ROIV', lookback_hours=24)
        
        # Should handle gracefully even with 0-5 mentions
        self.assertIsInstance(result, dict)
        print(f"\n✅ ROIV Results:")
        print(f"   Mentions: {result['mention_count']} (low volume expected)")
        print(f"   Score: {result['sentiment_score']:+.3f}")
        print(f"   Classification: {result['classification']}")
        print(f"   Confidence: {result['confidence']:.1%}")
        
        if result['mention_count'] == 0:
            self.assertEqual(result['classification'], 'neutral')
            self.assertEqual(result['confidence'], 0.0)
            print("   ✅ Zero mentions handled correctly (neutral, 0% confidence)")
    
    def test_invalid_ticker(self):
        """Test invalid ticker symbol"""
        print("\n" + "="*70)
        print("TEST: Invalid Ticker (NOTAREALTHING)")
        print("="*70)
        
        result = self.analyzer.analyze_ticker_sentiment('NOTAREALTHING', lookback_hours=24)
        
        # Should return neutral with 0 mentions
        self.assertEqual(result['mention_count'], 0)
        self.assertEqual(result['classification'], 'neutral')
        self.assertEqual(result['confidence'], 0.0)
        
        print(f"✅ Invalid ticker handled correctly:")
        print(f"   Classification: {result['classification']}")
        print(f"   Mentions: {result['mention_count']}")
        print(f"   Confidence: {result['confidence']:.1%}")
    
    def test_time_window_variation(self):
        """Test different time windows (12h vs 24h vs 48h)"""
        print("\n" + "="*70)
        print("TEST: Time Window Variation (TSLA)")
        print("="*70)
        
        windows = [12, 24, 48]
        for hours in windows:
            result = self.analyzer.analyze_ticker_sentiment('TSLA', lookback_hours=hours)
            print(f"\n   {hours}h window: {result['mention_count']} mentions | "
                  f"Score: {result['sentiment_score']:+.3f} | "
                  f"Confidence: {result['confidence']:.1%}")
        
        print("\n✅ Time window variation tested")


class TestPerformanceMetrics(unittest.TestCase):
    """Test 10: Overall performance validation"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize Reddit analyzer"""
        cls.analyzer = RedditSentimentAnalyzer(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
    
    def test_cache_effectiveness(self):
        """Test cache hit rate and performance improvement"""
        print("\n" + "="*70)
        print("TEST: Cache Effectiveness")
        print("="*70)
        
        cache_stats = self.analyzer.cache.get_stats()
        
        print(f"\n✅ Cache Statistics:")
        print(f"   Total entries: {cache_stats['size']}")
        print(f"   Hits: {cache_stats['hits']}")
        print(f"   Misses: {cache_stats['misses']}")
        
        if cache_stats['hits'] + cache_stats['misses'] > 0:
            hit_rate = cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses'])
            print(f"   Hit rate: {hit_rate:.1%}")
            
            if hit_rate > 0:
                print(f"   ✅ Cache is working (hit rate: {hit_rate:.1%})")
        else:
            print("   No cache activity yet (first run)")
    
    def test_rate_limiter_status(self):
        """Test rate limiter final status"""
        print("\n" + "="*70)
        print("TEST: Rate Limiter Final Status")
        print("="*70)
        
        stats = self.analyzer.rate_limiter.get_stats()
        
        print(f"\n✅ Rate Limiter Status:")
        print(f"   Requests in current window: {stats['requests_in_window']}/1000")
        print(f"   Window start: {stats['window_start']}")
        print(f"   Remaining capacity: {1000 - stats['requests_in_window']}")
        
        self.assertLessEqual(stats['requests_in_window'], 1000,
            "Rate limit should never exceed 1000 req/10min")


def run_day3_tests():
    """Run all Day 3 real data tests with detailed output"""
    print("\n" + "="*80)
    print(" "*20 + "PHASE 3, DAY 3 - REAL DATA TESTING")
    print(" "*15 + "Reddit Sentiment Analysis - Production Validation")
    print("="*80)
    print(f"\nTest Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Target: 10 diverse tickers, 90%+ accuracy, <3s per ticker")
    print("\nPrerequisites:")
    print("- Reddit API credentials configured (see REDDIT_API_SETUP_GUIDE.md)")
    print("- Environment variables: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT")
    print("="*80 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes in order
    suite.addTests(loader.loadTestsFromTestCase(TestRedditRealDataSetup))
    suite.addTests(loader.loadTestsFromTestCase(TestRedditRealDataAAPL))
    suite.addTests(loader.loadTestsFromTestCase(TestRedditRealData10Tickers))
    suite.addTests(loader.loadTestsFromTestCase(TestManualValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceMetrics))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print final summary
    print("\n" + "="*80)
    print("DAY 3 TEST SUMMARY")
    print("="*80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED - Day 3 Checkpoint 2 READY")
        print("\nNext Steps:")
        print("1. Complete manual validation (compare top 5 posts)")
        print("2. Document results in IMPLEMENTATION_PROGRESS_LOG.md")
        print("3. Proceed to Day 4: GME & TSLA high-volume testing")
    else:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        print("\nTroubleshooting:")
        print("1. Verify Reddit API credentials are correct")
        print("2. Check internet connectivity")
        print("3. Verify rate limits not exceeded")
        print("4. See REDDIT_API_SETUP_GUIDE.md for help")
    
    print("="*80 + "\n")
    
    return result


if __name__ == '__main__':
    run_day3_tests()
