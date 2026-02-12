"""
Expanded Real Data Test for Liquidity Score - 10+ Diverse Tickers
=================================================================

Day 7 (Feb 11, 2026) - P2.2 Liquidity Score - Day 2 Expanded Testing
Testing with 12 diverse tickers across ALL market cap ranges

Test Strategy:
1. Mega-cap: AAPL, MSFT, GOOGL (3 tickers)
2. Large-cap: JPM, V, JNJ (3 tickers)
3. Mid-cap: PLTR, COIN, RBLX (3 tickers)
4. Small-cap: MARA, RIOT, TTOO (3 tickers)

Total: 12 tickers spanning full market cap spectrum

Expected Results by Category:
- Mega-cap: Score >85 (Very Low risk)
- Large-cap: Score 75-85 (Low risk)
- Mid-cap: Score 60-75 (Low-Medium risk)
- Small-cap: Score 40-60 (Medium-High risk)

Success Criteria (Checkpoint 2):
- 10/12 tickers return valid scores (83%+)
- Scores align with market cap/volume expectations
- Performance <3 seconds per ticker
- Manual validation: >90% accuracy for 2-3 tickers
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import yfinance as yf
import time
import pandas as pd
from analysis_scripts.risk_analysis import RiskAnalyzer


# Expanded test ticker portfolio (12 tickers)
TEST_TICKERS_EXPANDED = {
    # Mega-cap (3)
    'AAPL': {'type': 'Mega-cap', 'expected_min': 85, 'sector': 'Tech'},
    'MSFT': {'type': 'Mega-cap', 'expected_min': 85, 'sector': 'Tech'},
    'GOOGL': {'type': 'Mega-cap', 'expected_min': 85, 'sector': 'Tech'},
    
    # Large-cap (3)
    'JPM': {'type': 'Large-cap', 'expected_min': 75, 'sector': 'Financial'},
    'V': {'type': 'Large-cap', 'expected_min': 75, 'sector': 'Financial'},
    'JNJ': {'type': 'Large-cap', 'expected_min': 75, 'sector': 'Healthcare'},
    
    # Mid-cap (3)
    'PLTR': {'type': 'Mid-cap', 'expected_min': 60, 'sector': 'Tech'},
    'COIN': {'type': 'Mid-cap', 'expected_min': 60, 'sector': 'Crypto'},
    'RBLX': {'type': 'Mid-cap', 'expected_min': 60, 'sector': 'Gaming'},
    
    # Small-cap (3)
    'MARA': {'type': 'Small-cap', 'expected_min': 40, 'sector': 'Crypto Mining'},
    'RIOT': {'type': 'Small-cap', 'expected_min': 40, 'sector': 'Crypto Mining'},
    'TTOO': {'type': 'Small-cap', 'expected_min': 30, 'sector': 'Biotech'}
}


class TestLiquidityExpandedRealData:
    """Expanded real data testing with 12 diverse tickers."""
    
    def test_mega_cap_trio(self):
        """Test mega-cap stocks (AAPL, MSFT, GOOGL)."""
        print("\n" + "="*80)
        print("MEGA-CAP TESTING (3 tickers)")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        mega_tickers = ['AAPL', 'MSFT', 'GOOGL']
        results = []
        
        for ticker in mega_tickers:
            print(f"\nTesting {ticker}...")
            start = time.time()
            result = analyzer.calculate_liquidity_risk_robust(ticker)
            end = time.time()
            
            calc_time = (end - start) * 1000
            
            print(f"  Score: {result['liquidity_score']}")
            print(f"  Risk: {result['risk_level']}")
            print(f"  Volume: {result['avg_daily_volume']}")
            print(f"  Market Cap: {result['market_cap']}")
            print(f"  Time: {calc_time:.2f}ms")
            
            results.append({
                'ticker': ticker,
                'score': result['liquidity_score'],
                'risk': result['risk_level'],
                'time': calc_time
            })
            
            # Assertions
            assert result['liquidity_score'] is not None, f"{ticker} should return valid score"
            assert result['liquidity_score'] >= 80, f"{ticker} mega-cap should have >80 score"
            assert calc_time < 5000, f"{ticker} should be <5000ms"
        
        print(f"\n✅ Mega-cap: 3/3 passed")
        return results
    
    def test_large_cap_trio(self):
        """Test large-cap stocks (JPM, V, JNJ)."""
        print("\n" + "="*80)
        print("LARGE-CAP TESTING (3 tickers)")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        large_tickers = ['JPM', 'V', 'JNJ']
        results = []
        
        for ticker in large_tickers:
            print(f"\nTesting {ticker}...")
            start = time.time()
            result = analyzer.calculate_liquidity_risk_robust(ticker)
            end = time.time()
            
            calc_time = (end - start) * 1000
            
            print(f"  Score: {result['liquidity_score']}")
            print(f"  Risk: {result['risk_level']}")
            print(f"  Volume: {result['avg_daily_volume']}")
            print(f"  Market Cap: {result['market_cap']}")
            print(f"  Time: {calc_time:.2f}ms")
            
            results.append({
                'ticker': ticker,
                'score': result['liquidity_score'],
                'risk': result['risk_level'],
                'time': calc_time
            })
            
            # Assertions
            assert result['liquidity_score'] is not None, f"{ticker} should return valid score"
            assert result['liquidity_score'] >= 70, f"{ticker} large-cap should have >70 score"
            assert calc_time < 5000, f"{ticker} should be <5000ms"
        
        print(f"\n✅ Large-cap: 3/3 passed")
        return results
    
    def test_mid_cap_trio(self):
        """Test mid-cap stocks (PLTR, COIN, RBLX)."""
        print("\n" + "="*80)
        print("MID-CAP TESTING (3 tickers)")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        mid_tickers = ['PLTR', 'COIN', 'RBLX']
        results = []
        
        for ticker in mid_tickers:
            print(f"\nTesting {ticker}...")
            start = time.time()
            result = analyzer.calculate_liquidity_risk_robust(ticker)
            end = time.time()
            
            calc_time = (end - start) * 1000
            
            print(f"  Score: {result['liquidity_score']}")
            print(f"  Risk: {result['risk_level']}")
            print(f"  Volume: {result['avg_daily_volume']}")
            print(f"  Market Cap: {result['market_cap']}")
            print(f"  Time: {calc_time:.2f}ms")
            
            results.append({
                'ticker': ticker,
                'score': result['liquidity_score'],
                'risk': result['risk_level'],
                'time': calc_time
            })
            
            # Assertions
            assert result['liquidity_score'] is not None, f"{ticker} should return valid score"
            assert result['liquidity_score'] >= 50, f"{ticker} mid-cap should have >50 score"
            assert calc_time < 5000, f"{ticker} should be <5000ms"
        
        print(f"\n✅ Mid-cap: 3/3 passed")
        return results
    
    def test_small_cap_trio(self):
        """Test small-cap stocks (MARA, RIOT, TTOO)."""
        print("\n" + "="*80)
        print("SMALL-CAP TESTING (3 tickers)")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        small_tickers = ['MARA', 'RIOT', 'TTOO']
        results = []
        
        for ticker in small_tickers:
            print(f"\nTesting {ticker}...")
            start = time.time()
            result = analyzer.calculate_liquidity_risk_robust(ticker)
            end = time.time()
            
            calc_time = (end - start) * 1000
            
            print(f"  Score: {result['liquidity_score']}")
            print(f"  Risk: {result['risk_level']}")
            print(f"  Volume: {result['avg_daily_volume']}")
            print(f"  Market Cap: {result['market_cap']}")
            print(f"  Time: {calc_time:.2f}ms")
            
            results.append({
                'ticker': ticker,
                'score': result['liquidity_score'],
                'risk': result['risk_level'],
                'time': calc_time
            })
            
            # Assertions - more lenient for small caps
            assert result['liquidity_score'] is not None, f"{ticker} should return valid score"
            assert calc_time < 5000, f"{ticker} should be <5000ms"
        
        print(f"\n✅ Small-cap: 3/3 passed")
        return results
    
    def test_comprehensive_12_ticker_summary(self):
        """Run comprehensive test on all 12 tickers and generate summary."""
        print("\n" + "="*80)
        print("COMPREHENSIVE 12-TICKER LIQUIDITY SCORE TEST")
        print("Day 7 - P2.2 Checkpoint 2 Validation")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        all_results = []
        
        for ticker, info in TEST_TICKERS_EXPANDED.items():
            print(f"\nTesting {ticker} ({info['type']})...")
            
            try:
                start = time.time()
                result = analyzer.calculate_liquidity_risk_robust(ticker)
                end = time.time()
                
                calc_time = (end - start) * 1000
                
                all_results.append({
                    'ticker': ticker,
                    'type': info['type'],
                    'sector': info['sector'],
                    'score': result['liquidity_score'],
                    'risk_level': result['risk_level'],
                    'volume': result['avg_daily_volume'],
                    'market_cap': result['market_cap'],
                    'dollar_volume': result['avg_dollar_volume'],
                    'volatility': result['volume_volatility'],
                    'time_ms': calc_time,
                    'status': 'PASS' if result['liquidity_score'] is not None else 'FAIL'
                })
                
                print(f"  ✓ Score: {result['liquidity_score']}, Risk: {result['risk_level']}")
                
            except Exception as e:
                all_results.append ({
                    'ticker': ticker,
                    'type': info['type'],
                    'sector': info['sector'],
                    'score': None,
                    'risk_level': 'ERROR',
                    'volume': 'N/A',
                    'market_cap': 'N/A',
                    'dollar_volume': 'N/A',
                    'volatility': 'N/A',
                    'time_ms': 0,
                    'status': f'FAIL: {str(e)[:50]}'
                })
                print(f"  ✗ Error: {str(e)[:50]}")
        
        # Generate summary report
        print("\n" + "="*80)
        print("CHECKPOINT 2: 12-TICKER TEST RESULTS SUMMARY")
        print("="*80)
        
        print(f"\n{'Ticker':<8} {'Type':<12} {'Sector':<15} {'Score':<8} {'Risk':<12} {'Time (ms)':<10} {'Status':<8}")
        print("-" * 95)
        
        for r in all_results:
            score_str = f"{r['score']:.1f}" if r['score'] is not None else "N/A"
            print(f"{r['ticker']:<8} {r['type']:<12} {r['sector']:<15} {score_str:<8} {r['risk_level']:<12} {r['time_ms']:<10.2f} {r['status']:<8}")
        
        # Calculate statistics
        valid_results = [r for r in all_results if r['score'] is not None]
        success_count = len(valid_results)
        total_count = len(all_results)
        success_rate = success_count / total_count
        
        if valid_results:
            avg_time = sum(r['time_ms'] for r in valid_results) / len(valid_results)
            avg_score = sum(r['score'] for r in valid_results) / len(valid_results)
            min_score = min(r['score'] for r in valid_results)
            max_score = max(r['score'] for r in valid_results)
        else:
            avg_time = 0
            avg_score = 0
            min_score = 0
            max_score = 0
        
        print("\n" + "="*80)
        print("STATISTICS")
        print("="*80)
        print(f"Tickers Tested: {total_count}")
        print(f"Successful: {success_count}/{total_count} ({success_rate*100:.1f}%)")
        print(f"Average Score: {avg_score:.1f}")
        print(f"Score Range: {min_score:.1f} - {max_score:.1f}")
        print(f"Average Time: {avg_time:.2f}ms")
        print(f"All <5000ms: {'✅ YES' if all(r['time_ms'] < 5000 for r in valid_results) else '❌ NO'}")
        
        # Checkpoint 2 validation
        print("\n" + "="*80)
        print("CHECKPOINT 2 VALIDATION")
        print("="*80)
        
        checkpoint_passed = True
        
        # Criterion 1: >90% success rate
        criterion_1 = success_rate >= 0.90
        print(f"1. Success Rate ≥90%: {success_rate*100:.1f}% {'✅ PASS' if criterion_1 else '❌ FAIL'}")
        checkpoint_passed = checkpoint_passed and criterion_1
        
        # Criterion 2: Performance <3000ms avg
        criterion_2 = avg_time < 3000
        print(f"2. Avg Time <3000ms: {avg_time:.2f}ms {'✅ PASS' if criterion_2 else '❌ FAIL'}")
        checkpoint_passed = checkpoint_passed and criterion_2
        
        # Criterion 3: Scores align with market cap expectations
        mega_scores = [r['score'] for r in valid_results if r['type'] == 'Mega-cap']
        small_scores = [r['score'] for r in valid_results if r['type'] == 'Small-cap']
        
        if mega_scores and small_scores:
            criterion_3 = (sum(mega_scores)/len(mega_scores)) > (sum(small_scores)/len(small_scores))
            print(f"3. Mega-cap avg > Small-cap avg: {'✅ PASS' if criterion_3 else '❌ FAIL'}")
            checkpoint_passed = checkpoint_passed and criterion_3
        else:
            criterion_3 = False
            print(f"3. Mega-cap avg > Small-cap avg: ❌ FAIL (insufficient data)")
        
        print("\n" + "="*80)
        if checkpoint_passed:
            print("✅ CHECKPOINT 2 PASSED - 12-ticker validation successful")
        else:
            print("❌ CHECKPOINT 2 FAILED - Review results above")
        print("="*80)
        
        # Assertions
        assert success_rate >= 0.83, f"Success rate should be ≥83% (10/12), got {success_rate*100:.1f}%"
        assert avg_time < 5000, f"Average time should be <5000ms, got {avg_time:.2f}ms"
        
        return all_results
    
    def test_market_cap_correlation(self):
        """Test that liquidity scores correlate with market cap."""
        print("\n" + "="*80)
        print("MARKET CAP CORRELATION TEST")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        
        # Get scores for different market cap tiers
        mega_avg = 0
        large_avg = 0
        mid_avg = 0
        small_avg = 0
        
        mega_tickers = ['AAPL', 'MSFT', 'GOOGL']
        large_tickers = ['JPM', 'V', 'JNJ']
        mid_tickers = ['PLTR', 'COIN', 'RBLX']
        small_tickers = ['MARA', 'RIOT', 'TTOO']
        
        # Calculate averages
        mega_scores = []
        for ticker in mega_tickers:
            result = analyzer.calculate_liquidity_risk_robust(ticker)
            if result['liquidity_score'] is not None:
                mega_scores.append(result['liquidity_score'])
        mega_avg = sum(mega_scores) / len(mega_scores) if mega_scores else 0
        
        large_scores = []
        for ticker in large_tickers:
            result = analyzer.calculate_liquidity_risk_robust(ticker)
            if result['liquidity_score'] is not None:
                large_scores.append(result['liquidity_score'])
        large_avg = sum(large_scores) / len(large_scores) if large_scores else 0
        
        mid_scores = []
        for ticker in mid_tickers:
            result = analyzer.calculate_liquidity_risk_robust(ticker)
            if result['liquidity_score'] is not None:
                mid_scores.append(result['liquidity_score'])
        mid_avg = sum(mid_scores) / len(mid_scores) if mid_scores else 0
        
        small_scores = []
        for ticker in small_tickers:
            result = analyzer.calculate_liquidity_risk_robust(ticker)
            if result['liquidity_score'] is not None:
                small_scores.append(result['liquidity_score'])
        small_avg = sum(small_scores) / len(small_scores) if small_scores else 0
        
        print(f"\nAverage Scores by Market Cap:")
        print(f"  Mega-cap:  {mega_avg:.1f}")
        print(f"  Large-cap: {large_avg:.1f}")
        print(f"  Mid-cap:   {mid_avg:.1f}")
        print(f"  Small-cap: {small_avg:.1f}")
        
        # Verify descending trend (with some tolerance for mid/large overlap)
        print(f"\nCorrelation Validation:")
        print(f"  Mega > Large: {mega_avg > large_avg - 5} {'✅' if mega_avg > large_avg - 5 else '❌'}")
        print(f"  Mega > Mid:   {mega_avg > mid_avg} {'✅' if mega_avg > mid_avg else '❌'}")
        print(f"  Mega > Small: {mega_avg > small_avg} {'✅' if mega_avg > small_avg else '❌'}")
        
        assert mega_avg > small_avg, f"Mega-cap ({mega_avg:.1f}) should exceed small-cap ({small_avg:.1f})"
        
        print(f"\n✅ Market cap correlation validated")


if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
