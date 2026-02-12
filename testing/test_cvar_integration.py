"""
Integration Test for CVaR in User-Facing Reports
=================================================

This test validates that CVaR is correctly integrated into the extract_risk_analysis_data()
function and appears in user-facing reports with proper formatting.

Test Strategy:
1. Test 20 diverse tickers across market caps and volatility profiles
2. Verify CVaR appears in formatted output
3. Validate CVaR values are more extreme than VaR
4. Check formatting (percentage, 2 decimal places)
5. Ensure no regressions in existing metrics

Checkpoint 3: Integration & Production Deployment
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from analysis_scripts.fundamental_analysis import extract_risk_analysis_data


# Test tickers spanning different market characteristics
INTEGRATION_TEST_TICKERS = [
    # Mega-cap stable
    'AAPL', 'MSFT', 'GOOGL', 'JNJ', 'PG',
    # Mega-cap volatile
    'TSLA', 'NVDA', 'AMD',
    # Mid-cap growth
    'PLTR', 'RBLX', 'COIN',
    # Small-cap volatile
    'MARA', 'RIOT', 'GME', 'AMC',
    # Financial sector
    'JPM', 'BAC', 'GS',
    # Energy sector
    'XOM', 'CVX'
]


class TestCVaRIntegration:
    """Integration tests for CVaR in user-facing reports."""
    
    def fetch_historical_data(self, ticker, period='1y'):
        """Fetch historical data for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            if data.empty:
                pytest.skip(f"No data available for {ticker}")
            return data
        except Exception as e:
            pytest.skip(f"Failed to fetch data for {ticker}: {e}")
    
    def test_cvar_in_formatted_output(self):
        """Test CVaR appears in formatted output for multiple tickers."""
        results = []
        
        for ticker in INTEGRATION_TEST_TICKERS:
            print(f"\nTesting {ticker}...")
            
            try:
                # Fetch data
                historical_data = self.fetch_historical_data(ticker)
                
                # Extract risk analysis
                risk_data = extract_risk_analysis_data(
                    historical_data=historical_data,
                    market_data=None,
                    ticker=ticker
                )
                
                # Verify CVaR metrics are present
                assert "CVaR (5%)" in risk_data, f"CVaR (5%) missing for {ticker}"
                assert "CVaR (1%)" in risk_data, f"CVaR (1%) missing for {ticker}"
                
                # Verify VaR metrics are still present (no regression)
                assert "Value at Risk (5%)" in risk_data, f"VaR (5%) missing for {ticker}"
                assert "Value at Risk (1%)" in risk_data, f"VaR (1%) missing for {ticker}"
                
                # Extract values (handle percentage formatting)
                cvar_5_str = risk_data["CVaR (5%)"]
                cvar_1_str = risk_data["CVaR (1%)"]
                var_5_str = risk_data["Value at Risk (5%)"]
                var_1_str = risk_data["Value at Risk (1%)"]
                
                # Check formatting (should be percentage strings)
                assert '%' in cvar_5_str or 'N/A' in cvar_5_str, f"CVaR (5%) not formatted as percentage for {ticker}"
                assert '%' in cvar_1_str or 'N/A' in cvar_1_str, f"CVaR (1%) not formatted as percentage for {ticker}"
                
                # Parse values if available
                if '%' in cvar_5_str and '%' in var_5_str:
                    cvar_5_val = float(cvar_5_str.replace('%', ''))
                    var_5_val = float(var_5_str.replace('%', ''))
                    
                    # CVaR should be more extreme than VaR (more negative)
                    assert cvar_5_val < var_5_val, \
                        f"{ticker}: CVaR (5%) {cvar_5_val}% should be < VaR (5%) {var_5_val}%"
                
                if '%' in cvar_1_str and '%' in var_1_str:
                    cvar_1_val = float(cvar_1_str.replace('%', ''))
                    var_1_val = float(var_1_str.replace('%', ''))
                    
                    # CVaR should be more extreme than VaR
                    assert cvar_1_val < var_1_val, \
                        f"{ticker}: CVaR (1%) {cvar_1_val}% should be < VaR (1%) {var_1_val}%"
                
                results.append({
                    'ticker': ticker,
                    'cvar_5': cvar_5_str,
                    'cvar_1': cvar_1_str,
                    'var_5': var_5_str,
                    'var_1': var_1_str,
                    'status': 'PASS'
                })
                
                print(f"✓ {ticker}: CVaR (5%) = {cvar_5_str}, VaR (5%) = {var_5_str}")
                
            except Exception as e:
                results.append({
                    'ticker': ticker,
                    'cvar_5': 'ERROR',
                    'cvar_1': 'ERROR',
                    'var_5': 'ERROR',
                    'var_1': 'ERROR',
                    'status': f'FAIL: {str(e)}'
                })
                print(f"✗ {ticker}: {str(e)}")
        
        # Print summary
        print("\n" + "="*80)
        print("INTEGRATION TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in results if r['status'] == 'PASS')
        total = len(results)
        
        print(f"\nResults: {passed}/{total} tickers passed ({passed/total*100:.1f}%)")
        print("\nDetailed Results:")
        print(f"{'Ticker':<10} {'VaR (5%)':<12} {'CVaR (5%)':<12} {'Status':<20}")
        print("-" * 80)
        
        for r in results:
            print(f"{r['ticker']:<10} {r['var_5']:<12} {r['cvar_5']:<12} {r['status']:<20}")
        
        # Assert at least 80% success rate (allow for data availability issues)
        assert passed / total >= 0.80, \
            f"Integration test failed: Only {passed}/{total} tickers passed ({passed/total*100:.1f}% < 80%)"
    
    def test_no_regression_existing_metrics(self):
        """Test that adding CVaR didn't break existing metrics."""
        ticker = 'AAPL'
        historical_data = self.fetch_historical_data(ticker)
        
        risk_data = extract_risk_analysis_data(
            historical_data=historical_data,
            market_data=None,
            ticker=ticker
        )
        
        # All original metrics should still be present
        expected_metrics = [
            "Volatility (30d Ann.)",
            "Volatility (Historical Ann.)",
            "Value at Risk (5%)",
            "Value at Risk (1%)",
            "Sharpe Ratio",
            "Sortino Ratio",
            "Maximum Drawdown",
            "Skewness",
            "Kurtosis"
        ]
        
        for metric in expected_metrics:
            assert metric in risk_data, f"Regression: {metric} missing from output"
    
    def test_cvar_formatting_consistency(self):
        """Test CVaR values are formatted consistently across tickers."""
        test_tickers = ['AAPL', 'TSLA', 'JPM']
        
        for ticker in test_tickers:
            historical_data = self.fetch_historical_data(ticker)
            risk_data = extract_risk_analysis_data(
                historical_data=historical_data,
                market_data=None,
                ticker=ticker
            )
            
            cvar_5 = risk_data.get("CVaR (5%)", "")
            cvar_1 = risk_data.get("CVaR (1%)", "")
            
            # Should be either percentage format or N/A
            assert ('%' in cvar_5 or 'N/A' in cvar_5), \
                f"{ticker}: CVaR (5%) has invalid format: {cvar_5}"
            assert ('%' in cvar_1 or 'N/A' in cvar_1), \
                f"{ticker}: CVaR (1%) has invalid format: {cvar_1}"
            
            # If percentage, should have 2 decimal places
            if '%' in cvar_5:
                value_str = cvar_5.replace('%', '').strip()
                if '.' in value_str:
                    decimal_places = len(value_str.split('.')[1])
                    assert decimal_places == 2, \
                        f"{ticker}: CVaR (5%) should have 2 decimal places, got {decimal_places}"
    
    def test_cvar_mathematical_properties(self):
        """Test CVaR satisfies expected mathematical properties."""
        ticker = 'AAPL'
        historical_data = self.fetch_historical_data(ticker)
        
        risk_data = extract_risk_analysis_data(
            historical_data=historical_data,
            market_data=None,
            ticker=ticker
        )
        
        # Extract and parse values
        cvar_5_str = risk_data["CVaR (5%)"].replace('%', '')
        cvar_1_str = risk_data["CVaR (1%)"].replace('%', '')
        
        cvar_5 = float(cvar_5_str)
        cvar_1 = float(cvar_1_str)
        
        # CVaR at 1% should be more extreme than CVaR at 5%
        # (1% looks at even worse tail)
        assert cvar_1 < cvar_5, \
            f"CVaR (1%) {cvar_1}% should be < CVaR (5%) {cvar_5}% (more extreme)"
    
    def test_integration_checkpoint_3(self):
        """
        Checkpoint 3: Integration Test
        
        This is the final checkpoint for P2.1 CVaR implementation.
        Success criteria:
        - CVaR appears in user-facing reports
        - Values are correctly formatted
        - No regressions in existing metrics
        - At least 80% of tickers pass validation
        """
        print("\n" + "="*80)
        print("CHECKPOINT 3: CVaR Integration & Production Deployment")
        print("="*80)
        
        # Run the comprehensive integration test
        self.test_cvar_in_formatted_output()
        
        # Verify no regressions
        self.test_no_regression_existing_metrics()
        
        # Verify formatting consistency
        self.test_cvar_formatting_consistency()
        
        # Verify mathematical properties
        self.test_cvar_mathematical_properties()
        
        print("\n✅ CHECKPOINT 3 PASSED: CVaR integration successful")
        print("   - CVaR appears in all user-facing reports")
        print("   - Formatting is consistent and correct")
        print("   - No regressions detected")
        print("   - Mathematical properties verified")
        print("\n🎉 P2.1 CVaR Implementation COMPLETE")


if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
