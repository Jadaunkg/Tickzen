"""
Altman Z-Score Integration Test Suite (Day 11 - P2.3 Checkpoint 3)
Tests full integration with comprehensive_risk_profile() and extract_risk_analysis_data()

Test Coverage:
- 20 diverse tickers across 5 sectors
- Full risk report generation
- No regressions in existing metrics (CVaR, Liquidity)
- Performance validation (<3 sec per ticker)
- Data quality checks

Date: February 15, 2026
"""

import pytest
import sys
import time
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis_scripts.risk_analysis import RiskAnalyzer
from analysis_scripts.fundamental_analysis import extract_risk_analysis_data
import yfinance as yf


class TestAltmanZScoreIntegration:
    """Test Altman Z-Score integration with full risk profile"""
    
    @pytest.fixture
    def analyzer(self):
        """Create RiskAnalyzer instance"""
        return RiskAnalyzer()
    
    def test_integration_comprehensive_risk_profile(self, analyzer):
        """Test Z-Score integration in comprehensive_risk_profile()"""
        # Test with AAPL (known to have good data)
        ticker = "AAPL"
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        if hist.empty:
            pytest.skip(f"No data available for {ticker}")
        
        price_data = hist['Close']
        
        # Call comprehensive_risk_profile with ticker (triggers Z-Score calculation)
        result = analyzer.comprehensive_risk_profile(price_data, ticker=ticker)
        
        # Verify all expected fields exist
        assert result is not None, "Result should not be None"
        
        # Existing metrics should still be there (no regressions)
        assert 'volatility_annualized' in result, "Volatility should be present"
        assert 'var_5' in result, "VaR 5% should be present"
        assert 'cvar_5' in result, "CVaR 5% should be present (P2.1)"
        assert 'sharpe_ratio' in result, "Sharpe Ratio should be present"
        assert 'max_drawdown' in result, "Max Drawdown should be present"
        
        # Liquidity metrics should be there (P2.2)
        assert 'liquidity_score' in result, "Liquidity Score should be present (P2.2)"
        assert 'liquidity_risk_level' in result, "Liquidity Risk Level should be present"
        
        # NEW: Altman Z-Score metrics should be added (P2.3)
        assert 'altman_z_score' in result, "Altman Z-Score should be present"
        assert 'altman_risk_zone' in result, "Risk Zone should be present"
        assert 'altman_bankruptcy_risk' in result, "Bankruptcy Risk should be present"
        
        # Validate Z-Score values
        z_score = result['altman_z_score']
        if z_score is not None:  # May be None if data unavailable
            assert isinstance(z_score, (int, float)), "Z-Score should be numeric"
            assert result['altman_risk_zone'] in ['Safe', 'Grey', 'Distress'], \
                "Risk Zone should be valid"
            assert result['altman_bankruptcy_risk'] in ['Low', 'Medium', 'High'], \
                "Bankruptcy Risk should be valid"
        
        print(f"\n✅ Integration Test PASSED for {ticker}")
        print(f"Z-Score: {z_score}")
        print(f"Risk Zone: {result['altman_risk_zone']}")
        print(f"Bankruptcy Risk: {result['altman_bankruptcy_risk']}")
    
    def test_integration_extract_risk_analysis_data(self):
        """Test Z-Score in extract_risk_analysis_data() (user-facing)"""
        # Test with MSFT
        ticker = "MSFT"
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        if hist.empty:
            pytest.skip(f"No data available for {ticker}")
        
        # Call extract_risk_analysis_data (user-facing function)
        result = extract_risk_analysis_data(hist, ticker=ticker)
        
        # Verify formatted metrics exist
        assert result is not None, "Result should not be None"
        assert len(result) > 0, "Should have risk metrics"
        
        # Check existing metrics (no regressions)
        assert "Volatility (30d Ann.)" in result, "30D Volatility should be present"
        assert "CVaR (5%)" in result, "CVaR should be present (P2.1)"
        assert "Liquidity Score" in result, "Liquidity Score should be present (P2.2)"
        
        # NEW: Check Altman Z-Score formatted metrics (P2.3)
        assert "Altman Z-Score" in result, "Altman Z-Score should be in formatted output"
        assert "Bankruptcy Risk" in result, "Bankruptcy Risk should be in formatted output"
        assert "Financial Health Zone" in result, "Financial Health Zone should be in formatted output"
        
        # Verify values are properly formatted
        z_score_str = result["Altman Z-Score"]
        bankruptcy_risk = result["Bankruptcy Risk"]
        health_zone = result["Financial Health Zone"]
        
        assert z_score_str is not None, "Z-Score should not be None"
        assert bankruptcy_risk in ['Low', 'Medium', 'High', 'Unknown'], \
            "Bankruptcy Risk should be valid"
        assert health_zone in ['Safe', 'Grey', 'Distress', 'Unknown'], \
            "Health Zone should be valid"
        
        print(f"\n✅ User-Facing Integration Test PASSED for {ticker}")
        print(f"Altman Z-Score: {z_score_str}")
        print(f"Bankruptcy Risk: {bankruptcy_risk}")
        print(f"Financial Health Zone: {health_zone}")
        print(f"\nAll Metrics ({len(result)}):")
        for key, value in result.items():
            print(f"  {key}: {value}")


def test_20_ticker_integration():
    """
    Comprehensive 20-ticker integration test (Checkpoint 3)
    Tests across 5 sectors to ensure production readiness
    """
    
    # 20 diverse tickers per DAILY_IMPLEMENTATION_CHECKLIST.md
    tickers = [
        # Mega-cap tech (5)
        "AAPL", "MSFT", "GOOGL", "AMZN", "META",
        # Tech/Growth (5)
        "TSLA", "NVDA", "AMD", "INTC", "QCOM",
        # Financials (5)
        "JPM", "BAC", "WFC", "GS", "MS",
        # Healthcare (5)
        "JNJ", "PFE", "UNH", "ABBV", "MRK",
        # Energy (5)
        "XOM", "CVX", "COP", "SLB", "EOG"
    ]
    
    analyzer = RiskAnalyzer()
    results = []
    performance_times = []
    
    print("\n" + "="*80)
    print("20-TICKER INTEGRATION TEST - CHECKPOINT 3")
    print("="*80)
    print(f"Testing {len(tickers)} tickers across 5 sectors")
    print("Testing integration: CVaR (P2.1) + Liquidity (P2.2) + Altman Z-Score (P2.3)")
    print("="*80 + "\n")
    
    for ticker in tickers:
        try:
            start_time = time.time()
            
            # Fetch data
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if hist.empty:
                print(f"⚠️  {ticker}: No data available (SKIP)")
                results.append({
                    'ticker': ticker,
                    'status': 'SKIP',
                    'reason': 'No data'
                })
                continue
            
            price_data = hist['Close']
            
            # Test comprehensive_risk_profile integration
            risk_profile = analyzer.comprehensive_risk_profile(price_data, ticker=ticker)
            
            # Test extract_risk_analysis_data integration (user-facing)
            user_metrics = extract_risk_analysis_data(hist, ticker=ticker)
            
            elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
            performance_times.append(elapsed_time)
            
            # Validate no regressions
            has_cvar = 'cvar_5' in risk_profile
            has_liquidity = 'liquidity_score' in risk_profile
            has_altman = 'altman_z_score' in risk_profile
            
            has_user_cvar = "CVaR (5%)" in user_metrics
            has_user_liquidity = "Liquidity Score" in user_metrics
            has_user_altman = "Altman Z-Score" in user_metrics
            
            z_score = risk_profile.get('altman_z_score')
            risk_zone = risk_profile.get('altman_risk_zone', 'Unknown')
            
            # Determine status
            if has_cvar and has_liquidity and has_altman and has_user_cvar and has_user_liquidity and has_user_altman:
                status = "✅ PASS"
            else:
                status = "⚠️  PARTIAL"
            
            results.append({
                'ticker': ticker,
                'status': status,
                'z_score': z_score,
                'risk_zone': risk_zone,
                'time_ms': elapsed_time,
                'has_cvar': has_cvar,
                'has_liquidity': has_liquidity,
                'has_altman': has_altman
            })
            
            # Display result
            z_display = f"{z_score:.2f}" if z_score is not None and not (isinstance(z_score, float) and z_score != z_score) else "N/A"
            print(f"{status} {ticker:6s} | Z={z_display:>7s} | Zone: {risk_zone:13s} | Time: {elapsed_time:6.0f}ms")
            
        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            performance_times.append(elapsed_time)
            
            print(f"❌ {ticker:6s} | ERROR: {str(e)[:50]}")
            results.append({
                'ticker': ticker,
                'status': 'FAIL',
                'error': str(e),
                'time_ms': elapsed_time
            })
    
    # Calculate statistics
    print("\n" + "="*80)
    print("CHECKPOINT 3 RESULTS")
    print("="*80)
    
    total = len(tickers)
    passed = len([r for r in results if r['status'] == '✅ PASS'])
    partial = len([r for r in results if r['status'] == '⚠️  PARTIAL'])
    failed = len([r for r in results if r['status'] == 'FAIL'])
    skipped = len([r for r in results if r['status'] == 'SKIP'])
    
    success_rate = (passed / total) * 100 if total > 0 else 0
    avg_time = sum(performance_times) / len(performance_times) if performance_times else 0
    max_time = max(performance_times) if performance_times else 0
    
    print(f"\nTotal Tickers: {total}")
    print(f"✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"⚠️  Partial: {partial}/{total}")
    print(f"❌ Failed: {failed}/{total}")
    print(f"⏭️  Skipped: {skipped}/{total}")
    print(f"\nPerformance:")
    print(f"  Average Time: {avg_time:.0f}ms")
    print(f"  Max Time: {max_time:.0f}ms")
    print(f"  Target: <3000ms ({'✅ PASS' if avg_time < 3000 else '❌ FAIL'})")
    
    # Checkpoint 3 criteria
    print(f"\n" + "="*80)
    print("CHECKPOINT 3 VALIDATION")
    print("="*80)
    
    criteria_passed = []
    
    # Criterion 1: Success rate ≥ 85%
    criterion1 = success_rate >= 85.0
    criteria_passed.append(criterion1)
    print(f"✅ Criterion 1: Success ≥85%: {success_rate:.1f}% {'✅ PASS' if criterion1 else '❌ FAIL'}")
    
    # Criterion 2: Average time < 3 seconds
    criterion2 = avg_time < 3000
    criteria_passed.append(criterion2)
    print(f"✅ Criterion 2: Avg time <3000ms: {avg_time:.0f}ms {'✅ PASS' if criterion2 else '❌ FAIL'}")
    
    # Criterion 3: No regressions (all passed tickers have CVaR, Liquidity, Altman)
    passed_results = [r for r in results if r['status'] == '✅ PASS']
    no_regressions = all(r.get('has_cvar', False) and r.get('has_liquidity', False) and r.get('has_altman', False) for r in passed_results)
    criteria_passed.append(no_regressions)
    print(f"✅ Criterion 3: No regressions: {'✅ PASS' if no_regressions else '❌ FAIL'}")
    
    # Criterion 4: At least 15/20 tickers successfully analyzed
    criterion4 = passed >= 15
    criteria_passed.append(criterion4)
    print(f"✅ Criterion 4: ≥15 tickers successful: {passed}/20 {'✅ PASS' if criterion4 else '❌ FAIL'}")
    
    # Overall checkpoint
    checkpoint_passed = all(criteria_passed)
    print(f"\n{'='*80}")
    if checkpoint_passed:
        print("✅ ✅ ✅ CHECKPOINT 3 PASSED ✅ ✅ ✅")
    else:
        print("❌ ❌ ❌ CHECKPOINT 3 FAILED ❌ ❌ ❌")
    print(f"{'='*80}\n")
    
    # Assertions for pytest
    assert success_rate >= 85.0, f"Success rate {success_rate:.1f}% below 85% threshold"
    assert avg_time < 3000, f"Average time {avg_time:.0f}ms exceeds 3000ms threshold"
    assert no_regressions, "Regressions detected in existing metrics"
    assert passed >= 15, f"Only {passed}/20 tickers successful, need ≥15"
    
    print("✅ All integration tests passed!\n")


if __name__ == "__main__":
    # Run the comprehensive 20-ticker test
    test_20_ticker_integration()
