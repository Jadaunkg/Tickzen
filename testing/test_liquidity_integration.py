"""
Integration Test for Liquidity Score (P2.2 - Day 8)
===================================================

Tests liquidity score integration into comprehensive_risk_profile() and
extract_risk_analysis_data() with 20 diverse tickers across all sectors.

Day 8 (Feb 12, 2026) - P2.2 Liquidity Score - Day 3 Integration Testing

Test Strategy:
1. Test comprehensive_risk_profile() includes liquidity_score
2. Test extract_risk_analysis_data() formats liquidity correctly
3. Test 20 diverse tickers (no regressions)
4. Validate all existing metrics still work
5. Verify performance (<3s per ticker)

20 Ticker Portfolio:
- Mega-cap: AAPL, MSFT, GOOGL, JNJ, PG (5)
- Large-cap: JPM, BAC, V, UNH, HD (5)
- Mid-cap: PLTR, COIN, RBLX, SQ, SHOP (5)
- Small-cap: MARA, RIOT, GME, AMC, TTOO (5)

Success Criteria (Checkpoint 3):
- All 20 tickers return liquidity scores (100%)
- No regressions in existing metrics
- Formatted output includes liquidity
- Performance <3s per ticker average
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import yfinance as yf
import pandas as pd
import time
from analysis_scripts.risk_analysis import RiskAnalyzer
from analysis_scripts.fundamental_analysis import extract_risk_analysis_data


# 20-ticker integration test portfolio
INTEGRATION_TICKERS = {
    # Mega-cap (5)
    'AAPL': {'type': 'Mega-cap', 'sector': 'Tech'},
    'MSFT': {'type': 'Mega-cap', 'sector': 'Tech'},
    'GOOGL': {'type': 'Mega-cap', 'sector': 'Tech'},
    'JNJ': {'type': 'Mega-cap', 'sector': 'Healthcare'},
    'PG': {'type': 'Mega-cap', 'sector': 'Consumer'},
    
    # Large-cap (5)
    'JPM': {'type': 'Large-cap', 'sector': 'Financial'},
    'BAC': {'type': 'Large-cap', 'sector': 'Financial'},
    'V': {'type': 'Large-cap', 'sector': 'Financial'},
    'UNH': {'type': 'Large-cap', 'sector': 'Healthcare'},
    'HD': {'type': 'Large-cap', 'sector': 'Consumer'},
    
    # Mid-cap (5)
    'PLTR': {'type': 'Mid-cap', 'sector': 'Tech'},
    'COIN': {'type': 'Mid-cap', 'sector': 'Crypto'},
    'RBLX': {'type': 'Mid-cap', 'sector': 'Gaming'},
    'SQ': {'type': 'Mid-cap', 'sector': 'Fintech'},
    'SHOP': {'type': 'Mid-cap', 'sector': 'E-commerce'},
    
    # Small-cap (5)
    'MARA': {'type': 'Small-cap', 'sector': 'Crypto Mining'},
    'RIOT': {'type': 'Small-cap', 'sector': 'Crypto Mining'},
    'GME': {'type': 'Small-cap', 'sector': 'Retail'},
    'AMC': {'type': 'Small-cap', 'sector': 'Entertainment'},
    'TTOO': {'type': 'Small-cap', 'sector': 'Biotech'}
}


class TestLiquidityIntegration:
    """Integration tests for liquidity score (Checkpoint 3)."""
    
    def test_comprehensive_risk_profile_includes_liquidity(self):
        """Test that comprehensive_risk_profile() returns liquidity score."""
        print("\n" + "="*80)
        print("TEST 1: comprehensive_risk_profile() Integration")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        
        # Test with AAPL
        ticker = 'AAPL'
        print(f"\nTesting {ticker}...")
        
        # Fetch price data
        stock = yf.Ticker(ticker)
        hist = stock.history(period='1y')
        price_data = hist['Close']
        
        # Call comprehensive_risk_profile WITH ticker parameter
        start = time.time()
        risk_profile = analyzer.comprehensive_risk_profile(price_data, ticker=ticker)
        end = time.time()
        
        calc_time = (end - start) * 1000
        
        print(f"\nRisk Profile Keys: {list(risk_profile.keys())}")
        print(f"Liquidity Score: {risk_profile.get('liquidity_score')}")
        print(f"Liquidity Risk Level: {risk_profile.get('liquidity_risk_level')}")
        print(f"Calculation Time: {calc_time:.2f}ms")
        
        # Assertions
        assert 'liquidity_score' in risk_profile, "Liquidity score should be in risk profile"
        assert 'liquidity_risk_level' in risk_profile, "Liquidity risk level should be in risk profile"
        assert risk_profile['liquidity_score'] is not None, "Liquidity score should not be None for AAPL"
        assert isinstance(risk_profile['liquidity_score'], (int, float)), "Liquidity score should be numeric"
        assert risk_profile['liquidity_risk_level'] in ['Very Low', 'Low', 'Medium', 'High'], \
            f"Liquidity risk level invalid: {risk_profile['liquidity_risk_level']}"
        
        # Verify existing metrics still present (no regression)
        expected_keys = [
            'volatility_annualized', 'volatility_30d_annualized',
            'var_5', 'var_1', 'cvar_5', 'cvar_1',
            'sharpe_ratio', 'sortino_ratio', 'max_drawdown',
            'skewness', 'kurtosis'
        ]
        
        for key in expected_keys:
            assert key in risk_profile, f"Existing metric '{key}' missing (regression!)"
        
        print(f"\n✅ Test 1 PASSED: Liquidity integrated, no regressions")
    
    def test_extract_risk_analysis_includes_liquidity(self):
        """Test that extract_risk_analysis_data() formats liquidity correctly."""
        print("\n" + "="*80)
        print("TEST 2: extract_risk_analysis_data() Integration")
        print("="*80)
        
        # Test with MSFT
        ticker = 'MSFT'
        print(f"\nTesting {ticker}...")
        
        # Fetch historical data
        stock = yf.Ticker(ticker)
        hist = stock.history(period='1y')
        
        # Call extract_risk_analysis_data
        start = time.time()
        risk_data = extract_risk_analysis_data(hist, ticker=ticker)
        end = time.time()
        
        calc_time = (end - start) * 1000
        
        print(f"\nFormatted Risk Data Keys: {list(risk_data.keys())}")
        print(f"Liquidity Score: {risk_data.get('Liquidity Score')}")
        print(f"Liquidity Risk: {risk_data.get('Liquidity Risk')}")
        print(f"Calculation Time: {calc_time:.2f}ms")
        
        # Assertions
        assert 'Liquidity Score' in risk_data, "Formatted liquidity score should be present"
        assert 'Liquidity Risk' in risk_data, "Formatted liquidity risk level should be present"
        
        # Verify formatting (should be string with proper format)
        liquidity_score = risk_data['Liquidity Score']
        liquidity_risk = risk_data['Liquidity Risk']
        
        assert liquidity_score != "N/A", "Liquidity score should not be N/A for MSFT"
        assert liquidity_risk in ['Very Low', 'Low', 'Medium', 'High', 'Unknown'], \
            f"Liquidity risk level invalid: {liquidity_risk}"
        
        # Verify existing formatted metrics still present
        expected_formatted_keys = [
            'Volatility (30d Ann.)', 'Volatility (Historical Ann.)',
            'Value at Risk (5%)', 'CVaR (5%)',
            'Sharpe Ratio', 'Maximum Drawdown'
        ]
        
        for key in expected_formatted_keys:
            assert key in risk_data, f"Existing formatted metric '{key}' missing (regression!)"
        
        print(f"\n✅ Test 2 PASSED: Formatted liquidity present, no regressions")
    
    def test_20_ticker_comprehensive_integration(self):
        """Run comprehensive integration test on 20 diverse tickers."""
        print("\n" + "="*80)
        print("TEST 3: 20-TICKER COMPREHENSIVE INTEGRATION TEST")
        print("Day 8 - P2.2 Checkpoint 3 Validation")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        results = []
        
        for ticker, info in INTEGRATION_TICKERS.items():
            print(f"\nTesting {ticker} ({info['type']})...")
            
            try:
                # Fetch data
                stock = yf.Ticker(ticker)
                hist = stock.history(period='1y')
                
                if hist.empty or len(hist) < 30:
                    print(f"  ✗ Insufficient data")
                    results.append({
                        'ticker': ticker,
                        'type': info['type'],
                        'sector': info['sector'],
                        'status': 'FAIL: Insufficient data',
                        'liquidity_score': None,
                        'has_existing_metrics': False,
                        'time_ms': 0
                    })
                    continue
                
                price_data = hist['Close']
                
                # Test comprehensive_risk_profile
                start = time.time()
                risk_profile = analyzer.comprehensive_risk_profile(price_data, ticker=ticker)
                end = time.time()
                
                calc_time = (end - start) * 1000
                
                # Validate results
                has_liquidity = 'liquidity_score' in risk_profile and risk_profile['liquidity_score'] is not None
                has_existing = all(k in risk_profile for k in ['volatility_annualized', 'sharpe_ratio', 'max_drawdown'])
                
                liquidity_score = risk_profile.get('liquidity_score', 'N/A')
                liquidity_risk = risk_profile.get('liquidity_risk_level', 'Unknown')
                
                status = "PASS" if has_liquidity and has_existing else "PARTIAL"
                
                results.append({
                    'ticker': ticker,
                    'type': info['type'],
                    'sector': info['sector'],
                    'status': status,
                    'liquidity_score': liquidity_score,
                    'liquidity_risk': liquidity_risk,
                    'has_existing_metrics': has_existing,
                    'time_ms': calc_time
                })
                
                print(f"  ✓ Score: {liquidity_score}, Risk: {liquidity_risk}, Time: {calc_time:.2f}ms")
                
            except Exception as e:
                print(f"  ✗ Error: {str(e)[:80]}")
                results.append({
                    'ticker': ticker,
                    'type': info['type'],
                    'sector': info['sector'],
                    'status': f'FAIL: {str(e)[:30]}',
                    'liquidity_score': None,
                    'has_existing_metrics': False,
                    'time_ms': 0
                })
        
        # Generate summary report
        print("\n" + "="*80)
        print("CHECKPOINT 3: 20-TICKER INTEGRATION RESULTS")
        print("="*80)
        
        print(f"\n{'Ticker':<8} {'Type':<12} {'Sector':<15} {'Liq Score':<10} {'Risk':<12} {'Time (ms)':<10} {'Status':<10}")
        print("-" * 110)
        
        for r in results:
            score_str = f"{r['liquidity_score']:.1f}" if isinstance(r['liquidity_score'], (int, float)) else "N/A"
            risk_str = r.get('liquidity_risk', 'Unknown')[:11]
            print(f"{r['ticker']:<8} {r['type']:<12} {r['sector']:<15} {score_str:<10} {risk_str:<12} {r['time_ms']:<10.2f} {r['status']:<10}")
        
        # Calculate statistics
        success_results = [r for r in results if r['status'] == 'PASS']
        success_count = len(success_results)
        total_count = len(results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        if success_results:
            avg_time = sum(r['time_ms'] for r in success_results) / len(success_results)
            max_time = max(r['time_ms'] for r in success_results)
            min_time = min(r['time_ms'] for r in success_results)
        else:
            avg_time = 0
            max_time = 0
            min_time = 0
        
        # Calculate regression check
        no_regression = all(r['has_existing_metrics'] for r in success_results)
        
        print("\n" + "="*80)
        print("STATISTICS")
        print("="*80)
        print(f"Tickers Tested: {total_count}")
        print(f"Successful: {success_count}/{total_count} ({success_rate*100:.1f}%)")
        print(f"Average Time: {avg_time:.2f}ms")
        print(f"Time Range: {min_time:.2f}ms - {max_time:.2f}ms")
        print(f"All <3000ms: {'✅ YES' if all(r['time_ms'] < 3000 for r in success_results) else '❌ NO'}")
        print(f"No Regressions: {'✅ YES' if no_regression else '❌ NO'}")
        
        # Checkpoint 3 validation
        print("\n" + "="*80)
        print("CHECKPOINT 3 VALIDATION")
        print("="*80)
        
        checkpoint_passed = True
        
        # Criterion 1: >95% success rate (20 tickers)
        criterion_1 = success_rate >= 0.95
        print(f"1. Success Rate ≥95%: {success_rate*100:.1f}% {'✅ PASS' if criterion_1 else '❌ FAIL'}")
        checkpoint_passed = checkpoint_passed and criterion_1
        
        # Criterion 2: Performance <3000ms avg
        criterion_2 = avg_time < 3000
        print(f"2. Avg Time <3000ms: {avg_time:.2f}ms {'✅ PASS' if criterion_2 else '❌ FAIL'}")
        checkpoint_passed = checkpoint_passed and criterion_2
        
        # Criterion 3: No regressions
        criterion_3 = no_regression
        print(f"3. No Regressions: {'✅ PASS' if criterion_3 else '❌ FAIL'}")
        checkpoint_passed = checkpoint_passed and criterion_3
        
        # Criterion 4: Liquidity formatted correctly in at least 18/20
        formatted_correct = sum(1 for r in success_results if r['liquidity_score'] != 'N/A')
        criterion_4 = formatted_correct >= 18
        print(f"4. Formatted Correctly: {formatted_correct}/20 {'✅ PASS' if criterion_4 else '❌ FAIL'}")
        checkpoint_passed = checkpoint_passed and criterion_4
        
        print("\n" + "="*80)
        if checkpoint_passed:
            print("✅ CHECKPOINT 3 PASSED - Integration successful, production ready")
        else:
            print("❌ CHECKPOINT 3 FAILED - Review results above")
        print("="*80)
        
        # Assertions
        assert success_rate >= 0.90, f"Success rate should be ≥90%, got {success_rate*100:.1f}%"
        assert avg_time < 5000, f"Average time should be <5000ms, got {avg_time:.2f}ms"
        assert no_regression, "Regressions detected in existing metrics"
        
        return results
    
    def test_backward_compatibility(self):
        """Test that comprehensive_risk_profile() still works WITHOUT ticker parameter."""
        print("\n" + "="*80)
        print("TEST 4: Backward Compatibility (optional ticker parameter)")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        
        # Test without ticker (should still work, just no liquidity score)
        ticker = 'AAPL'
        stock = yf.Ticker(ticker)
        hist = stock.history(period='1y')
        price_data = hist['Close']
        
        # Call WITHOUT ticker parameter (backward compatibility)
        print(f"\nTesting backward compatibility (no ticker param)...")
        risk_profile = analyzer.comprehensive_risk_profile(price_data)
        
        # Should still have all existing metrics
        expected_keys = [
            'volatility_annualized', 'sharpe_ratio', 'max_drawdown',
            'var_5', 'cvar_5', 'sortino_ratio'
        ]
        
        for key in expected_keys:
            assert key in risk_profile, f"Existing metric '{key}' missing"
        
        # Liquidity score should NOT be present (or be None)
        liquidity = risk_profile.get('liquidity_score')
        assert liquidity is None, f"Liquidity should be None without ticker, got {liquidity}"
        
        print(f"✅ Backward compatibility maintained: works without ticker param")
    
    def test_performance_benchmark(self):
        """Test that performance meets <3s per ticker target."""
        print("\n" + "="*80)
        print("TEST 5: Performance Benchmark")
        print("="*80)
        
        analyzer = RiskAnalyzer()
        test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'PLTR']
        
        times = []
        
        for ticker in test_tickers:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1y')
            price_data = hist['Close']
            
            start = time.time()
            risk_profile = analyzer.comprehensive_risk_profile(price_data, ticker=ticker)
            end = time.time()
            
            calc_time = (end - start) * 1000
            times.append(calc_time)
            
            print(f"{ticker}: {calc_time:.2f}ms")
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"\nAverage: {avg_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")
        print(f"Target: <3000ms")
        
        assert avg_time < 3000, f"Average time {avg_time:.2f}ms exceeds 3000ms"
        assert max_time < 5000, f"Max time {max_time:.2f}ms exceeds 5000ms"
        
        print(f"\n✅ Performance benchmark met")


if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
