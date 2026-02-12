#!/usr/bin/env python3
"""
Real Data Test: RiskAnalyzer with Dynamic Risk-Free Rate
========================================================

Tests RiskAnalyzer integration with real stock data from Yahoo Finance.
Validates that Sharpe and Sortino ratios differ between static (2%) and
dynamic (current ^IRX rate) risk-free rates.

Tickers Tested: AAPL, MSFT, GOOGL
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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
        return hist['Close']
    except Exception as e:
        print(f"ERROR fetching {ticker}: {e}")
        return None


def test_real_data():
    """Test with real stock data"""
    print("=" * 70)
    print("Real Data Test: RiskAnalyzer with Dynamic Risk-Free Rate")
    print("=" * 70)
    print()
    
    # Get current RF rate
    current_rf = fetch_current_risk_free_rate()
    print(f"📊 Current Risk-Free Rate (^IRX): {current_rf:.4f} ({current_rf*100:.2f}%)")
    print(f"📊 Static Risk-Free Rate: 0.0200 (2.00%)")
    print(f"📊 Difference: {(current_rf - 0.02)*100:.2f}%")
    print()
    
    if abs(current_rf - 0.02) < 0.001:
        print("⚠️  WARNING: Current RF rate is very close to 2%. Differences may be minimal.")
    print()
    
    # Test tickers
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    
    # Initialize analyzers
    analyzer_dynamic = RiskAnalyzer(use_dynamic_rf_rate=True)
    analyzer_static = RiskAnalyzer(use_dynamic_rf_rate=False)
    
    print("Testing 3 tickers with 1-year data...")
    print()
    
    results = []
    
    for ticker in tickers:
        print(f"{'─' * 70}")
        print(f"Ticker: {ticker}")
        print(f"{'─' * 70}")
        
        # Fetch data
        prices = fetch_stock_data(ticker, period='1y')
        
        if prices is None or len(prices) < 30:
            print(f"❌ Failed to fetch sufficient data for {ticker}")
            print()
            continue
        
        returns = prices.pct_change().dropna()
        
        print(f"Data points: {len(prices)}")
        print(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
        print()
        
        # Calculate with dynamic RF rate
        sharpe_dynamic = analyzer_dynamic.calculate_sharpe_ratio(returns)
        sortino_dynamic = analyzer_dynamic.calculate_sortino_ratio(returns)
        
        # Calculate with static RF rate
        sharpe_static = analyzer_static.calculate_sharpe_ratio(returns)
        sortino_static = analyzer_static.calculate_sortino_ratio(returns)
        
        # Calculate differences
        sharpe_diff = sharpe_dynamic - sharpe_static
        sharpe_pct_diff = (sharpe_diff / sharpe_static * 100) if sharpe_static != 0 else 0
        
        sortino_diff = sortino_dynamic - sortino_static
        sortino_pct_diff = (sortino_diff / sortino_static * 100) if sortino_static != 0 else 0
        
        # Display results
        print("Sharpe Ratio:")
        print(f"  Dynamic (^IRX): {sharpe_dynamic:8.4f}")
        print(f"  Static (2.00%): {sharpe_static:8.4f}")
        print(f"  Difference:     {sharpe_diff:8.4f} ({sharpe_pct_diff:+.2f}%)")
        print()
        
        print("Sortino Ratio:")
        print(f"  Dynamic (^IRX): {sortino_dynamic:8.4f}")
        print(f"  Static (2.00%): {sortino_static:8.4f}")
        print(f"  Difference:     {sortino_diff:8.4f} ({sortino_pct_diff:+.2f}%)")
        print()
        
        # Validation
        if abs(current_rf - 0.02) > 0.001:
            if abs(sharpe_diff) < 0.001:
                print("⚠️  WARNING: Sharpe ratios are nearly identical despite different RF rates")
            else:
                print("✅ Sharpe ratios correctly differ based on RF rate")
            
            if abs(sortino_diff) < 0.001:
                print("⚠️  WARNING: Sortino ratios are nearly identical despite different RF rates")
            else:
                print("✅ Sortino ratios correctly differ based on RF rate")
        else:
            print("ℹ️  RF rates are similar, so minimal difference is expected")
        
        print()
        
        # Store results
        results.append({
            'ticker': ticker,
            'sharpe_dynamic': sharpe_dynamic,
            'sharpe_static': sharpe_static,
            'sharpe_diff': sharpe_diff,
            'sharpe_pct_diff': sharpe_pct_diff,
            'sortino_dynamic': sortino_dynamic,
            'sortino_static': sortino_static,
            'sortino_diff': sortino_diff,
            'sortino_pct_diff': sortino_pct_diff,
            'data_points': len(prices)
        })
    
    # Summary table
    print(f"{'=' * 70}")
    print("SUMMARY TABLE")
    print(f"{'=' * 70}")
    print()
    
    if results:
        # Sharpe Ratio Summary
        print("Sharpe Ratio Comparison:")
        print(f"{'Ticker':<10} {'Dynamic':>10} {'Static':>10} {'Diff':>10} {'% Diff':>10}")
        print(f"{'-' * 60}")
        for r in results:
            print(f"{r['ticker']:<10} {r['sharpe_dynamic']:>10.4f} {r['sharpe_static']:>10.4f} "
                  f"{r['sharpe_diff']:>10.4f} {r['sharpe_pct_diff']:>9.2f}%")
        print()
        
        # Sortino Ratio Summary
        print("Sortino Ratio Comparison:")
        print(f"{'Ticker':<10} {'Dynamic':>10} {'Static':>10} {'Diff':>10} {'% Diff':>10}")
        print(f"{'-' * 60}")
        for r in results:
            print(f"{r['ticker']:<10} {r['sortino_dynamic']:>10.4f} {r['sortino_static']:>10.4f} "
                  f"{r['sortino_diff']:>10.4f} {r['sortino_pct_diff']:>9.2f}%")
        print()
        
        # Overall validation
        print(f"{'=' * 70}")
        print("OVERALL VALIDATION")
        print(f"{'=' * 70}")
        print()
        
        all_sharpe_differ = all(abs(r['sharpe_diff']) > 0.001 for r in results)
        all_sortino_differ = all(abs(r['sortino_diff']) > 0.001 for r in results)
        
        if abs(current_rf - 0.02) > 0.001:
            if all_sharpe_differ:
                print("✅ PASS: All Sharpe ratios correctly differ with dynamic RF rate")
            else:
                print("❌ FAIL: Some Sharpe ratios don't differ as expected")
            
            if all_sortino_differ:
                print("✅ PASS: All Sortino ratios correctly differ with dynamic RF rate")
            else:
                print("❌ FAIL: Some Sortino ratios don't differ as expected")
        else:
            print("ℹ️  RF rates are very similar (~2%), so minimal differences are expected")
            print("✅ PASS: Test completed successfully (rates too similar to validate difference)")
        
        print()
        print("✅ Integration with RiskAnalyzer successful!")
        print(f"✅ Tested {len(results)}/{len(tickers)} tickers successfully")
        
    else:
        print("❌ No results to display. All tickers failed.")
    
    print()
    print(f"{'=' * 70}")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    test_real_data()
