#!/usr/bin/env python3
"""
Day 3: Real Data Testing - 10 Diverse Tickers (Checkpoint 2)
============================================================

Tests dynamic risk-free rate integration with 10 diverse tickers as per
DAILY_IMPLEMENTATION_CHECKLIST.md Day 3 requirements.

Required Test Tickers (10):
1. AAPL (Apple) - Large Cap Stable
2. MSFT (Microsoft) - Large Cap Stable
3. GOOGL (Google) - Large Cap Tech
4. AMZN (Amazon) - Mega Cap
5. TSLA (Tesla) - Volatile Growth
6. GME (GameStop) - Meme Stock
7. AMC (AMC Entertainment) - Volatile
8. NVDA (Nvidia) - Growth Tech
9. AMD (AMD) - Growth Tech
10. META (Meta) - Large Cap Stable

Success Criteria:
- 90%+ accuracy vs manual calculation
- All 10 tickers tested successfully
- Performance acceptable (<3 sec/ticker)
- Edge cases documented
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analysis_scripts'))
from risk_analysis import RiskAnalyzer
from risk_free_rate_fetcher import fetch_current_risk_free_rate

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Install with: pip install yfinance")
    sys.exit(1)


def fetch_stock_data(ticker, period='1y'):
    """Fetch historical stock data"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if hist.empty or len(hist) < 30:
            return None
        return hist['Close']
    except Exception as e:
        print(f"ERROR fetching {ticker}: {e}")
        return None


def calculate_sharpe_manually(returns, rf_rate_annual):
    """
    Manual Sharpe ratio calculation for validation.
    
    Formula: Sharpe = (Mean_Return - RF_Rate_Daily) / Std_Return * sqrt(252)
    """
    rf_rate_daily = rf_rate_annual / 252
    excess_returns = returns - rf_rate_daily
    sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
    return sharpe


def calculate_sortino_manually(returns, rf_rate_annual):
    """
    Manual Sortino ratio calculation for validation.
    
    Formula: Sortino = (Mean_Return - RF_Rate_Daily) / Downside_Std * sqrt(252)
    """
    rf_rate_daily = rf_rate_annual / 252
    excess_returns = returns - rf_rate_daily
    downside_returns = excess_returns[excess_returns < 0]
    downside_std = downside_returns.std()
    
    if downside_std == 0 or np.isnan(downside_std):
        return np.nan
    
    sortino = (excess_returns.mean() / downside_std) * np.sqrt(252)
    return sortino


def compare_accuracy(system_value, manual_value, tolerance=0.10):
    """
    Compare system vs manual calculation.
    
    Returns:
    - accuracy_pct: Percentage match (100% = perfect match)
    - within_tolerance: True if difference < tolerance (default 10%)
    """
    if np.isnan(system_value) or np.isnan(manual_value):
        return 0.0, False
    
    if manual_value == 0:
        # Special case: if manual is 0, check if system is very close
        if abs(system_value) < 0.01:
            return 100.0, True
        else:
            return 0.0, False
    
    difference = abs(system_value - manual_value)
    relative_diff = difference / abs(manual_value)
    accuracy_pct = max(0, (1 - relative_diff) * 100)
    within_tolerance = relative_diff < tolerance
    
    return accuracy_pct, within_tolerance


def test_10_tickers():
    """
    Main test function for Day 3 - Test 10 diverse tickers
    """
    print("=" * 80)
    print("DAY 3: Real Data Testing - 10 Diverse Tickers (Checkpoint 2)")
    print("=" * 80)
    print()
    
    # Get current RF rate
    current_rf = fetch_current_risk_free_rate()
    print(f"📊 Current Risk-Free Rate (^IRX): {current_rf:.4f} ({current_rf*100:.2f}%)")
    print()
    
    # 10 Required Test Tickers (as per checklist)
    tickers = [
        ('AAPL', 'Large Cap Stable'),
        ('MSFT', 'Large Cap Stable'),
        ('GOOGL', 'Large Cap Tech'),
        ('AMZN', 'Mega Cap'),
        ('TSLA', 'Volatile Growth'),
        ('GME', 'Meme Stock'),
        ('AMC', 'Volatile'),
        ('NVDA', 'Growth Tech'),
        ('AMD', 'Growth Tech'),
        ('META', 'Large Cap Stable')
    ]
    
    print(f"Testing {len(tickers)} diverse tickers with 1-year data...")
    print()
    
    # Initialize analyzer with dynamic RF rate
    analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
    
    results = []
    performance_times = []
    
    for ticker, category in tickers:
        print(f"{'─' * 80}")
        print(f"Ticker: {ticker} ({category})")
        print(f"{'─' * 80}")
        
        # Start timing
        start_time = time.time()
        
        # Fetch data
        prices = fetch_stock_data(ticker, period='1y')
        
        if prices is None or len(prices) < 30:
            print(f"❌ Failed to fetch sufficient data for {ticker}")
            print()
            results.append({
                'ticker': ticker,
                'category': category,
                'status': 'FAILED',
                'reason': 'Insufficient data',
                'sharpe_system': None,
                'sharpe_manual': None,
                'sharpe_accuracy': 0,
                'sortino_system': None,
                'sortino_manual': None,
                'sortino_accuracy': 0,
                'time_sec': time.time() - start_time
            })
            continue
        
        returns = prices.pct_change().dropna()
        
        print(f"Data points: {len(prices)}")
        print(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
        print()
        
        # System calculations
        sharpe_system = analyzer.calculate_sharpe_ratio(returns)
        sortino_system = analyzer.calculate_sortino_ratio(returns)
        
        # Manual calculations (for validation)
        sharpe_manual = calculate_sharpe_manually(returns, current_rf)
        sortino_manual = calculate_sortino_manually(returns, current_rf)
        
        # Compare accuracy
        sharpe_accuracy, sharpe_pass = compare_accuracy(sharpe_system, sharpe_manual, tolerance=0.10)
        sortino_accuracy, sortino_pass = compare_accuracy(sortino_system, sortino_manual, tolerance=0.10)
        
        # End timing
        elapsed_time = time.time() - start_time
        performance_times.append(elapsed_time)
        
        # Display results
        print("Sharpe Ratio:")
        print(f"  System Calculation: {sharpe_system:8.4f}")
        print(f"  Manual Calculation: {sharpe_manual:8.4f}")
        print(f"  Accuracy:           {sharpe_accuracy:7.2f}%")
        print(f"  Within Tolerance:   {'✅ YES' if sharpe_pass else '❌ NO'}")
        print()
        
        print("Sortino Ratio:")
        print(f"  System Calculation: {sortino_system:8.4f}")
        print(f"  Manual Calculation: {sortino_manual:8.4f}")
        print(f"  Accuracy:           {sortino_accuracy:7.2f}%")
        print(f"  Within Tolerance:   {'✅ YES' if sortino_pass else '❌ NO'}")
        print()
        
        print(f"Performance: {elapsed_time:.2f}s")
        print(f"  Target: <3.00s per ticker {'✅ PASS' if elapsed_time < 3.0 else '❌ FAIL'}")
        print()
        
        # Store results
        results.append({
            'ticker': ticker,
            'category': category,
            'status': 'SUCCESS',
            'reason': '',
            'sharpe_system': sharpe_system,
            'sharpe_manual': sharpe_manual,
            'sharpe_accuracy': sharpe_accuracy,
            'sharpe_pass': sharpe_pass,
            'sortino_system': sortino_system,
            'sortino_manual': sortino_manual,
            'sortino_accuracy': sortino_accuracy,
            'sortino_pass': sortino_pass,
            'time_sec': elapsed_time
        })
    
    # =========================================================================
    # SUMMARY TABLE
    # =========================================================================
    print(f"{'=' * 80}")
    print("SUMMARY TABLE - 10 TICKER TEST RESULTS")
    print(f"{'=' * 80}")
    print()
    
    successful_tests = [r for r in results if r['status'] == 'SUCCESS']
    
    if successful_tests:
        # Sharpe Ratio Summary
        print("Sharpe Ratio Results:")
        print(f"{'Ticker':<8} {'Category':<20} {'System':>10} {'Manual':>10} {'Accuracy':>10} {'Pass':>8}")
        print(f"{'-' * 80}")
        for r in successful_tests:
            pass_str = '✅' if r['sharpe_pass'] else '❌'
            print(f"{r['ticker']:<8} {r['category']:<20} {r['sharpe_system']:>10.4f} "
                  f"{r['sharpe_manual']:>10.4f} {r['sharpe_accuracy']:>9.2f}% {pass_str:>8}")
        print()
        
        # Sortino Ratio Summary
        print("Sortino Ratio Results:")
        print(f"{'Ticker':<8} {'Category':<20} {'System':>10} {'Manual':>10} {'Accuracy':>10} {'Pass':>8}")
        print(f"{'-' * 80}")
        for r in successful_tests:
            pass_str = '✅' if r['sortino_pass'] else '❌'
            print(f"{r['ticker']:<8} {r['category']:<20} {r['sortino_system']:>10.4f} "
                  f"{r['sortino_manual']:>10.4f} {r['sortino_accuracy']:>9.2f}% {pass_str:>8}")
        print()
        
        # Performance Summary
        print("Performance Results:")
        print(f"{'Ticker':<8} {'Category':<20} {'Time (sec)':>12} {'Status':>10}")
        print(f"{'-' * 80}")
        for r in successful_tests:
            status = '✅ PASS' if r['time_sec'] < 3.0 else '❌ FAIL'
            print(f"{r['ticker']:<8} {r['category']:<20} {r['time_sec']:>12.2f} {status:>10}")
        print()
    
    # =========================================================================
    # CHECKPOINT 2 VALIDATION
    # =========================================================================
    print(f"{'=' * 80}")
    print("CHECKPOINT 2 VALIDATION - DAY 3 SUCCESS CRITERIA")
    print(f"{'=' * 80}")
    print()
    
    # Criterion 1: All 10 tickers tested successfully
    successful_count = len(successful_tests)
    criterion1_pass = successful_count == 10
    print(f"1. All 10 tickers tested successfully:")
    print(f"   Result: {successful_count}/10 tickers {'✅ PASS' if criterion1_pass else '❌ FAIL'}")
    print()
    
    # Criterion 2: 90%+ accuracy vs manual calculation
    if successful_tests:
        avg_sharpe_accuracy = np.mean([r['sharpe_accuracy'] for r in successful_tests])
        avg_sortino_accuracy = np.mean([r['sortino_accuracy'] for r in successful_tests])
        avg_overall_accuracy = (avg_sharpe_accuracy + avg_sortino_accuracy) / 2
        
        criterion2_pass = avg_overall_accuracy >= 90.0
        print(f"2. 90%+ accuracy vs manual calculation:")
        print(f"   Sharpe Accuracy:  {avg_sharpe_accuracy:.2f}%")
        print(f"   Sortino Accuracy: {avg_sortino_accuracy:.2f}%")
        print(f"   Overall Accuracy: {avg_overall_accuracy:.2f}% {'✅ PASS' if criterion2_pass else '❌ FAIL'}")
        print()
    else:
        criterion2_pass = False
        print(f"2. 90%+ accuracy vs manual calculation:")
        print(f"   ❌ FAIL - No successful tests to calculate accuracy")
        print()
    
    # Criterion 3: Performance acceptable (<3 sec/ticker)
    if performance_times:
        avg_time = np.mean(performance_times)
        max_time = np.max(performance_times)
        all_within_time = all(t < 3.0 for t in performance_times)
        
        criterion3_pass = all_within_time
        print(f"3. Performance acceptable (<3 sec/ticker):")
        print(f"   Average time: {avg_time:.2f}s")
        print(f"   Max time:     {max_time:.2f}s")
        print(f"   All < 3 sec:  {'✅ PASS' if criterion3_pass else '❌ FAIL'}")
        print()
    else:
        criterion3_pass = False
        print(f"3. Performance acceptable (<3 sec/ticker):")
        print(f"   ❌ FAIL - No performance data")
        print()
    
    # Overall Checkpoint 2 Result
    checkpoint2_pass = criterion1_pass and criterion2_pass and criterion3_pass
    
    print(f"{'=' * 80}")
    if checkpoint2_pass:
        print("✅ CHECKPOINT 2 PASSED - Real Data Test Complete!")
    else:
        print("❌ CHECKPOINT 2 FAILED - Review issues above")
    print(f"{'=' * 80}")
    print()
    
    # Edge Cases Documentation
    print(f"{'=' * 80}")
    print("EDGE CASES DOCUMENTED")
    print(f"{'=' * 80}")
    print()
    
    print("Edge Cases Encountered:")
    edge_cases_found = False
    
    for r in results:
        if r['status'] == 'FAILED':
            print(f"• {r['ticker']}: {r['reason']}")
            edge_cases_found = True
    
    if not edge_cases_found:
        print("• No edge cases encountered - all tickers processed successfully")
    
    print()
    
    # Data Quality Checks
    print("Data Quality Checks:")
    print("✅ Missing data handled correctly (filtered tickers with <30 days)")
    print("✅ API failures handled gracefully (try/except blocks)")
    print("✅ Edge cases captured (documented above)")
    print()
    
    print(f"{'=' * 80}")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}")
    
    return checkpoint2_pass, results


if __name__ == '__main__':
    checkpoint_passed, results = test_10_tickers()
    
    # Exit with appropriate code
    sys.exit(0 if checkpoint_passed else 1)
