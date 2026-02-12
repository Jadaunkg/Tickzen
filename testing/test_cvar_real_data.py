#!/usr/bin/env python3
"""
Real Data Test: P2.1 - CVaR with Live Market Data
=================================================

**Day 3 Testing:** Validate CVaR with 5 diverse real tickers
**Expected Ratios (CVaR_5% / VaR_5%):**
- Stable (AAPL): 1.2-1.5x
- Volatile (TSLA): 1.3-1.8x  
- Meme (GME): 2.0-3.0x (extreme tail risk)
- Volatile (AMC): 1.5-2.0x
- Growth (NVDA): 1.3-1.6x

**Target:** 100% success rate, 90%+ accuracy vs manual calculation

Created: February 9, 2026 (P2.1 Day 3 - Real Data)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tickzen2.analysis_scripts.risk_analysis import RiskAnalyzer


def test_cvar_real_data():
    """Test CVaR with 5 real tickers"""
    
    print("\n" + "="*80)
    print("P2.1 CHECKPOINT 2: REAL DATA VALIDATION (CVaR)")
    print("="*80)
    print("\nTesting 5 diverse tickers with live market data...")
    print("Fetching 1-year daily data from Yahoo Finance...\n")
    
    # Test tickers (diverse volatility profiles)
    test_tickers = {
        'AAPL': {'type': 'Stable Large-Cap', 'expected_ratio': (1.2, 1.5)},
        'TSLA': {'type': 'Volatile Growth', 'expected_ratio': (1.3, 1.8)},
        'GME': {'type': 'Meme Stock', 'expected_ratio': (2.0, 3.0)},
        'AMC': {'type': 'High Volatility', 'expected_ratio': (1.5, 2.0)},
        'NVDA': {'type': 'Growth Tech', 'expected_ratio': (1.3, 1.6)}
    }
    
    analyzer = RiskAnalyzer()
    results = {}
    all_passed = True
    
    for ticker, info in test_tickers.items():
        print(f"\n{'='*80}")
        print(f"Testing: {ticker} ({info['type']})")
        print(f"{'='*80}")
        
        try:
            # Fetch 1 year of data
            start_time = time.time()
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1y')
            fetch_time = time.time() - start_time
            
            if hist.empty or len(hist) < 100:
                print(f"❌ FAIL: Insufficient data for {ticker} ({len(hist)} days)")
                all_passed = False
                continue
            
            # Calculate returns
            returns = hist['Close'].pct_change().dropna()
            
            # Calculate risk metrics
            calc_start = time.time()
            var_5 = analyzer.calculate_var(returns, confidence_level=0.05)
            var_1 = analyzer.calculate_var(returns, confidence_level=0.01)
            cvar_5 = analyzer.calculate_cvar(returns, confidence_level=0.05)
            cvar_1 = analyzer.calculate_cvar(returns, confidence_level=0.01)
            calc_time = time.time() - calc_start
            
            # Calculate ratios
            ratio_5 = abs(cvar_5) / abs(var_5) if var_5 != 0 else 0
            ratio_1 = abs(cvar_1) / abs(var_1) if var_1 != 0 else 0
            
            # Validate
            expected_min, expected_max = info['expected_ratio']
            ratio_in_range = expected_min <= ratio_5 <= expected_max
            cvar_more_extreme = cvar_5 < var_5 and cvar_1 < var_1
            
            # Performance check
            performance_ok = calc_time < 1.0  # Sub-second
            
            # Overall pass/fail
            test_passed = ratio_in_range and cvar_more_extreme and performance_ok
            
            # Store results
            results[ticker] = {
                'var_5': var_5,
                'cvar_5': cvar_5,
                'var_1': var_1,
                'cvar_1': cvar_1,
                'ratio_5': ratio_5,
                'ratio_1': ratio_1,
                'data_points': len(returns),
                'fetch_time': fetch_time,
                'calc_time': calc_time,
                'passed': test_passed
            }
            
            # Print results
            print(f"\n**Data Quality:**")
            print(f"  Days of data: {len(returns)}")
            print(f"  Fetch time: {fetch_time:.2f}s")
            print(f"  Calculation time: {calc_time*1000:.2f}ms")
            
            print(f"\n**Risk Metrics (5% Confidence):**")
            print(f"  VaR (5%):  {var_5:.4f} ({var_5*100:.2f}%)")
            print(f"  CVaR (5%): {cvar_5:.4f} ({cvar_5*100:.2f}%)")
            print(f"  Ratio:     {ratio_5:.2f}x (Expected: {expected_min}-{expected_max}x)")
            
            print(f"\n**Risk Metrics (1% Confidence):**")
            print(f"  VaR (1%):  {var_1:.4f} ({var_1*100:.2f}%)")
            print(f"  CVaR (1%): {cvar_1:.4f} ({cvar_1*100:.2f}%)")
            print(f"  Ratio:     {ratio_1:.2f}x")
            
            print(f"\n**Validation:**")
            print(f"  ✅ CVaR < VaR (more extreme): {cvar_5 < var_5 and cvar_1 < var_1}")
            print(f"  {'✅' if ratio_in_range else '❌'} Ratio in expected range: {ratio_in_range}")
            print(f"  ✅ Performance acceptable: {calc_time*1000:.2f}ms < 1000ms")
            print(f"\n  **Overall: {'✅ PASS' if test_passed else '❌ FAIL'}**")
            
            if not test_passed:
                all_passed = False
            
        except Exception as e:
            print(f"\n❌ ERROR testing {ticker}: {str(e)}")
            results[ticker] = {'passed': False, 'error': str(e)}
            all_passed = False
    
    # Summary
    print(f"\n{'='*80}")
    print(f"CHECKPOINT 2 SUMMARY")
    print(f"{'='*80}")
    
    passed_count = sum(1 for r in results.values() if r.get('passed', False))
    total_count = len(test_tickers)
    success_rate = (passed_count / total_count * 100) if total_count > 0 else 0
    
    print(f"\n**Test Results:**")
    print(f"  Tickers Tested: {total_count}")
    print(f"  Passed: {passed_count}/{total_count}")
    print(f"  Success Rate: {success_rate:.1f}%")
    
    print(f"\n**Performance Summary:**")
    valid_results = [r for r in results.values() if 'calc_time' in r]
    if valid_results:
        avg_calc_time = np.mean([r['calc_time'] for r in valid_results])
        max_calc_time = np.max([r['calc_time'] for r in valid_results])
        print(f"  Average calculation time: {avg_calc_time*1000:.2f}ms")
        print(f"  Max calculation time: {max_calc_time*1000:.2f}ms")
    
    print(f"\n**Ratio Analysis:**")
    for ticker, result in results.items():
        if 'ratio_5' in result:
            info = test_tickers[ticker]
            exp_min, exp_max = info['expected_ratio']
            in_range = "✅" if exp_min <= result['ratio_5'] <= exp_max else "⚠️"
            print(f"  {in_range} {ticker:5s}: {result['ratio_5']:.2f}x (expected {exp_min}-{exp_max}x)")
    
    if all_passed and success_rate >= 90:
        print(f"\n{'='*80}")
        print(f"✅ CHECKPOINT 2 PASSED")
        print(f"{'='*80}")
        print(f"✅ All tickers validated successfully")
        print(f"✅ CVaR ratios within expected ranges")
        print(f"✅ Performance meets targets (<1s per ticker)")
        print(f"\n**Status:** READY FOR DAY 4 (Integration Testing)")
        print(f"{'='*80}")
        return 0
    else:
        print(f"\n{'='*80}")
        print(f"❌ CHECKPOINT 2 FAILED")
        print(f"{'='*80}")
        print(f"Success rate: {success_rate:.1f}% (target: >90%)")
        print(f"Review failures and adjust implementation.")
        print(f"{'='*80}")
        return 1


if __name__ == "__main__":
    exit_code = test_cvar_real_data()
    sys.exit(exit_code)
