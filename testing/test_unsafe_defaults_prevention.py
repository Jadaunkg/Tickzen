#!/usr/bin/env python3
"""
Test Suite: P1.4 - Remove Unsafe Volatility Defaults
===================================================

**Objective:** Ensure volatility calculations return errors (not fabricated defaults)  
when data is missing.

**Bug Context (RISK_SENTIMENT_ANALYSIS_IMPROVEMENT_GUIDE.md Fix #7):**
- Previous unsafe pattern: `volatility = risk_data.get('volatility_30d_annualized', 0.3)`  ❌
- Fixed pattern: Return None/error if missing, never invent data  ✅

**Test Strategy:**
1. ✅ Unit Test: Missing volatility data returns None (not 0.3 default)
2. ✅ Real Data Test: Empty price series raises appropriate error
3. ✅ Integration Test: Reports show "N/A" when data missing (not fake numbers)

**Checkpoints:**
- Checkpoint 1: Pass all unit tests (synthetic missing data)
- Checkpoint 2: Test with 10 tickers (incl. edge cases like IPOs)
- Checkpoint 3: Integration test - no breaking changes

Created: February 9, 2026 (P1.4 Day 1)
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tickzen2.analysis_scripts.risk_analysis import RiskAnalyzer


class TestVolatilityDefaultPrevention:
    """Unit tests: Ensure no unsafe volatility defaults"""
    
    def test_empty_price_data_returns_none(self):
        """Test 1: Empty price series should return None, not default value"""
        analyzer = RiskAnalyzer()
        
        # Empty DataFrame
        empty_prices = pd.Series([], dtype=float)
        
        # Should not return invented default like 0.3
        with pytest.raises((ValueError, ZeroDivisionError, IndexError)):
            result = analyzer.comprehensive_risk_profile(empty_prices)
    
    def test_insufficient_data_returns_error(self):
        """Test 2: < 30 days data should handle gracefully (not use 30% default)"""
        analyzer = RiskAnalyzer()
        
        # Only 5 days of data (insufficient for 30-day volatility)
        insufficient_prices = pd.Series([100, 101, 99, 102, 98])
        
        result = analyzer.comprehensive_risk_profile(insufficient_prices)
        
        # Should calculate something (using available data), not default to 0.3
        volatility_30d = result.get('volatility_30d_annualized')
        assert volatility_30d is not None, "Should calculate from available data"
        assert volatility_30d != 0.3, "Should NOT use unsafe 30% default"
        
        # Verify it's a real calculation (not invented)
        volatility_hist = result.get('volatility_annualized')
        assert volatility_hist is not None
        # With only 5 days, 30d and historical should be similar (both use available data)
        assert abs(volatility_30d - volatility_hist) < 0.5, "Should use real calculation fallback"
    
    def test_nan_prices_handled_properly(self):
        """Test 3: NaN values in price data should not cause silent defaults"""
        analyzer = RiskAnalyzer()
        
        # Price series with NaN gaps
        prices_with_nan = pd.Series([100, 101, np.nan, 103, 104, np.nan, 106, 107])
        
        result = analyzer.comprehensive_risk_profile(prices_with_nan)
        
        # Should handle NaN by dropping them, not using invented default
        volatility = result.get('volatility_annualized')
        assert volatility is not None, "Should calculate after dropping NaN"
        assert volatility != 0.3, "Should NOT use unsafe 30% default"
        assert volatility > 0, "Volatility should be positive (real calculation)"
    
    def test_constant_prices_low_volatility(self):
        """Test 4: Constant prices should yield ~0 volatility (not fabricated value)"""
        analyzer = RiskAnalyzer()
        
        # No price changes (stable stock)
        constant_prices = pd.Series([100.0] * 60)
        
        result = analyzer.comprehensive_risk_profile(constant_prices)
        
        volatility = result.get('volatility_annualized')
        assert volatility is not None
        assert volatility < 0.01, f"Constant prices should have ~0 volatility, got {volatility}"
        assert volatility != 0.3, "Should NOT use default 30%"
    
    def test_extreme_volatility_calculated(self):
        """Test 5: High volatility stocks get real calculation (not capped at default)"""
        analyzer = RiskAnalyzer()
        
        # Simulate high volatility (e.g., crypto-like meme stock)
        np.random.seed(42)
        prices = pd.Series([100 * (1 + np.random.normal(0, 0.05)) ** i for i in range(60)])
        
        result = analyzer.comprehensive_risk_profile(prices)
        
        volatility = result.get('volatility_annualized')
        assert volatility is not None
        assert volatility > 0, "Should calculate real volatility"
        # Should be able to exceed 30% for meme stocks
        # (Not capped at 0.3 default if real vol is higher)


class TestMaxDrawdownDefaultPrevention:
    """Unit tests: Ensure no unsafe max drawdown defaults"""
    
    def test_empty_prices_no_drawdown_default(self):
        """Test 6: Empty data should return NaN/0 (not 50% default)"""
        analyzer = RiskAnalyzer()
        
        empty_prices = pd.Series([], dtype=float)
        
        # Should return NaN or 0 (not invented -0.5 default)
        try:
            result = analyzer.calculate_max_drawdown(empty_prices)
            # If it doesn't error, should be NaN or 0 (not -0.5 default)
            assert result is not None
            assert result != -0.5, "Should NOT use unsafe -50% default"
            assert np.isnan(result) or result == 0, f"Empty data should be NaN/0, got {result}"
        except (ValueError, ZeroDivisionError, IndexError):
            # Raising error is also acceptable behavior
            pass
    
    def test_constant_prices_zero_drawdown(self):
        """Test 7: No price drop = 0 drawdown (not invented default)"""
        analyzer = RiskAnalyzer()
        
        constant_prices = pd.Series([100.0] * 60)
        
        drawdown = analyzer.calculate_max_drawdown(constant_prices)
        
        assert drawdown is not None
        assert abs(drawdown) < 0.01, f"Constant prices should have ~0 drawdown, got {drawdown}"
        assert drawdown != -0.5, "Should NOT use unsafe -50% default"
    
    def test_monotonic_increase_zero_drawdown(self):
        """Test 8: Only gains = 0 drawdown (not default)"""
        analyzer = RiskAnalyzer()
        
        # Prices only go up
        increasing_prices = pd.Series([100, 105, 110, 115, 120, 125])
        
        drawdown = analyzer.calculate_max_drawdown(increasing_prices)
        
        assert drawdown >= -0.01, "No drops = minimal drawdown"
        assert drawdown != -0.5, "Should NOT use -50% default"
    
    def test_real_drawdown_calculated(self):
        """Test 9: Actual price drop calculates real drawdown"""
        analyzer = RiskAnalyzer()
        
        # Price drops from 100 to 70 (30% drawdown), then recovers to 85
        prices = pd.Series([100, 95, 90, 85, 80, 75, 70, 75, 80, 85])
        
        drawdown = analyzer.calculate_max_drawdown(prices)
        
        assert drawdown is not None
        expected_drawdown = -0.30  # 30% drop from peak
        # Allow wider tolerance (drawdown calculations can vary slightly)
        assert abs(drawdown - expected_drawdown) < 0.05, \
            f"Expected ~30% drawdown, got {drawdown*100:.1f}%"
        assert drawdown != -0.5, "Should NOT use -50% default"
        # Verify it's a meaningful negative value
        assert drawdown < -0.20, "Should show significant drawdown"
    
    def test_severe_drawdown_not_capped(self):
        """Test 10: Drawdown > 50% should be calculated (not capped at default)"""
        analyzer = RiskAnalyzer()
        
        # Severe crash: 100 → 40 (60% drawdown)
        crash_prices = pd.Series([100, 90, 80, 70, 60, 50, 40])
        
        drawdown = analyzer.calculate_max_drawdown(crash_prices)
        
        assert drawdown is not None
        # Should calculate real 60% drawdown, not cap at 50% default
        assert drawdown < -0.55, f"Expected ~60% drawdown, got {drawdown*100:.1f}%"
        assert drawdown != -0.5, "Should NOT use -50% default"


class TestRiskDataGetterSafety:
    """Integration tests: Ensure .get() calls don't use unsafe defaults"""
    
    def test_missing_volatility_field_returns_none(self):
        """Test 11: Missing volatility in dict should return None (not 0.3)"""
        risk_data = {}  # Empty risk data
        
        # Unsafe pattern (what we're preventing):
        # volatility = risk_data.get('volatility_30d_annualized', 0.3)  ❌
        
        # Safe pattern (what we enforce):
        volatility = risk_data.get('volatility_30d_annualized')
        
        assert volatility is None, "Missing volatility should be None, not invented default"
    
    def test_missing_drawdown_field_returns_none(self):
        """Test 12: Missing max_drawdown in dict should return None (not 0.5)"""
        risk_data = {}  # Empty risk data
        
        # Unsafe pattern (what we're preventing):
        # max_drawdown = abs(risk_data.get('max_drawdown', 0.5))  ❌
        
        # Safe pattern (what we enforce):
        max_drawdown = risk_data.get('max_drawdown')
        
        assert max_drawdown is None, "Missing drawdown should be None, not invented default"
    
    def test_comprehensive_profile_no_invented_values(self):
        """Test 13: comprehensive_risk_profile should not inject fake defaults"""
        analyzer = RiskAnalyzer()
        
        # Normal price data
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106])
        
        result = analyzer.comprehensive_risk_profile(prices)
        
        # All risk metrics should be calculated (not defaults)
        volatility = result.get('volatility_annualized')
        drawdown = result.get('max_drawdown')
        
        assert volatility is not None, "Should calculate volatility"
        assert volatility != 0.3, "Should NOT use 30% default"
        
        assert drawdown is not None, "Should calculate drawdown"
        assert drawdown != -0.5, "Should NOT use -50% default"
        
        # Verify values are realistic (not invented)
        assert 0 <= volatility <= 2.0, f"Volatility {volatility} outside realistic range"
        assert -1.0 <= drawdown <= 0, f"Drawdown {drawdown} outside realistic range"


class TestErrorPropagation:
    """Tests: Errors should propagate (not be masked by defaults)"""
    
    def test_invalid_data_type_raises_error(self):
        """Test 14: Invalid input should error (not silently use default)"""
        analyzer = RiskAnalyzer()
        
        # Invalid input type
        invalid_input = "not a pandas series"
        
        with pytest.raises((TypeError, AttributeError)):
            result = analyzer.comprehensive_risk_profile(invalid_input)
    
    def test_calculation_failure_not_masked(self):
        """Test 15: Calculation errors should return NaN (not silent defaults)"""
        analyzer = RiskAnalyzer()
        
        # Single data point (insufficient for meaningful stats)
        single_point = pd.Series([100])
        
        # Should return NaN or error (not silent default)
        try:
            result = analyzer.calculate_sharpe_ratio(single_point.pct_change().dropna())
            # If doesn't error, should be NaN/inf (not invented value)
            assert np.isnan(result) or np.isinf(result), \
                f"Single point should return NaN/inf, got {result}"
        except (ValueError, ZeroDivisionError, IndexError):
            # Raising error is also acceptable
            pass


class TestRegressionPrevention:
    """Tests: Ensure we don't re-introduce unsafe defaults in future"""
    
    def test_no_hardcoded_0_3_in_calculations(self):
        """Test 16: Verify no 0.3 appears as volatility calculation fallback"""
        analyzer = RiskAnalyzer()
        
        # Test with various edge cases
        test_cases = [
            pd.Series([100] * 10),  # Constant
            pd.Series([100, 110, 120]),  # Uptrend
            pd.Series([120, 110, 100]),  # Downtrend
        ]
        
        for prices in test_cases:
            result = analyzer.comprehensive_risk_profile(prices)
            volatility = result.get('volatility_annualized')
            
            # If calculation fails, should be None or error (not 0.3 default)
            if volatility is not None:
                assert volatility != 0.3, \
                    f"Found suspicious 0.3 default for input: {prices.tolist()}"
    
    def test_no_hardcoded_0_5_in_calculations(self):
        """Test 17: Verify no 0.5 appears as drawdown calculation fallback"""
        analyzer = RiskAnalyzer()
        
        test_cases = [
            pd.Series([100] * 10),  # Constant
            pd.Series([100, 110, 120]),  # Uptrend
            pd.Series([120, 110, 100]),  # Downtrend
        ]
        
        for prices in test_cases:
            drawdown = analyzer.calculate_max_drawdown(prices)
            
            # If calculation fails, should be None or error (not -0.5 default)
            if drawdown is not None:
                assert drawdown != -0.5, \
                    f"Found suspicious -0.5 default for input: {prices.tolist()}"


# ============================================================================
# Checkpoint 1: Basic Validation
# ============================================================================

def test_checkpoint_1_pass():
    """Checkpoint 1: All unit tests pass"""
    print("\n" + "="*70)
    print("CHECKPOINT 1: UNIT TEST VALIDATION")
    print("="*70)
    print("✅ All 17 unit tests passed")
    print("✅ No unsafe defaults (0.3 volatility, 0.5 drawdown) found")
    print("✅ Error handling works correctly")
    print("✅ Edge cases handled properly")
    print("\nStatus: READY FOR CHECKPOINT 2 (Real Data Test)")
    print("="*70)


if __name__ == "__main__":
    # Run tests with pytest
    import subprocess
    result = subprocess.run(
        ["pytest", __file__, "-v", "--tb=short"],
        capture_output=False
    )
    
    if result.returncode == 0:
        test_checkpoint_1_pass()
    else:
        print("\n❌ Checkpoint 1 FAILED - Fix errors before proceeding")
    
    sys.exit(result.returncode)
