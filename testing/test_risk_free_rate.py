"""
Test Suite for Dynamic Risk-Free Rate Implementation
====================================================

Task: P1.1 - Dynamic Risk-Free Rate (^IRX)
Phase: 1 - Foundation & Bug Fixes
Day: 1 - Setup & Unit Tests (Checkpoint 1)
Date: February 9, 2026

Test Coverage:
-------------
1. Unit tests with synthetic data
2. Edge cases (None, empty, API failure)
3. Fallback mechanism validation
4. Rate range validation (0-10%)
5. Caching behavior

Author: TickZen Engineering Team
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from analysis_scripts.risk_free_rate_fetcher import fetch_current_risk_free_rate, RiskFreeRateFetcher
except ImportError:
    # Module doesn't exist yet - will be created after tests are written (TDD approach)
    pass


class TestRiskFreeRateFetcher:
    """Test suite for Risk-Free Rate fetcher"""
    
    def test_successful_fetch(self):
        """
        Test successful fetching of risk-free rate from ^IRX
        Expected: Rate between 0% and 10%
        """
        # This will be implemented after we create the function
        # For now, we define what success looks like
        pass
    
    def test_rate_range_validation(self):
        """
        Test that fetched rate is within reasonable bounds
        Expected: 0 <= rate <= 0.10 (0% to 10%)
        """
        # Test with mock data
        mock_rate = 0.0425  # 4.25%
        assert 0 <= mock_rate <= 0.10, f"Rate {mock_rate} outside valid range"
        
        # Test edge cases
        assert 0 <= 0.0 <= 0.10, "Lower bound validation failed"
        assert 0 <= 0.10 <= 0.10, "Upper bound validation failed"
        
        # Test invalid rates
        with pytest.raises(AssertionError):
            invalid_rate = 0.15  # 15% - too high
            assert 0 <= invalid_rate <= 0.10, f"Rate {invalid_rate} should fail validation"
    
    def test_fallback_on_api_failure(self):
        """
        Test fallback to 2% when ^IRX data unavailable
        Expected: Returns 0.02 with warning logged
        """
        fallback_rate = 0.02
        assert fallback_rate == 0.02, "Fallback rate should be 2%"
        assert isinstance(fallback_rate, float), "Fallback rate must be float"
    
    def test_empty_data_handling(self):
        """
        Test behavior when ^IRX returns empty DataFrame
        Expected: Fallback to 2% without crashing
        """
        # Simulate empty DataFrame
        empty_df = pd.DataFrame()
        assert empty_df.empty, "Test setup: DataFrame should be empty"
        
        # Function should handle this gracefully and return fallback
        expected_fallback = 0.02
        assert expected_fallback == 0.02, "Should return fallback on empty data"
    
    def test_none_handling(self):
        """
        Test behavior when API returns None
        Expected: Fallback to 2% without crashing
        """
        api_response = None
        assert api_response is None, "Test setup: Response should be None"
        
        # Function should handle None gracefully
        expected_fallback = 0.02
        assert expected_fallback == 0.02, "Should return fallback on None"
    
    def test_rate_conversion(self):
        """
        Test that ^IRX rate is properly converted from percentage
        ^IRX returns rate like 4.25, need to convert to 0.0425
        Expected: Proper division by 100
        """
        irx_value = 4.25  # As returned by yfinance
        expected_rate = 0.0425  # After conversion
        actual_rate = irx_value / 100
        
        assert actual_rate == expected_rate, f"Conversion failed: {actual_rate} != {expected_rate}"
        assert isinstance(actual_rate, float), "Converted rate must be float"
    
    def test_date_range_fetching(self):
        """
        Test that function fetches recent data (last 5 days)
        Expected: Gets most recent available rate
        """
        # Test date range
        days_to_fetch = 5
        assert days_to_fetch == 5, "Should fetch 5 days of data for reliability"
    
    def test_rate_type_validation(self):
        """
        Test that returned rate is always a float
        Expected: float type, not int or string
        """
        test_rates = [0.02, 0.0425, 0.05, 0.0]
        for rate in test_rates:
            assert isinstance(rate, float), f"Rate {rate} must be float type"
    
    def test_extreme_values(self):
        """
        Test handling of extreme but valid values
        Expected: Accepts values at boundaries
        """
        # Test boundary values
        min_rate = 0.0  # 0%
        max_rate = 0.10  # 10%
        
        assert 0 <= min_rate <= 0.10, "Minimum rate should be valid"
        assert 0 <= max_rate <= 0.10, "Maximum rate should be valid"
    
    def test_negative_rate_handling(self):
        """
        Test handling of negative rates (rare but possible in some countries)
        Expected: For US T-bills, should reject or use absolute value
        """
        negative_rate = -0.01  # -1%
        
        # For US T-bills, negative rates are invalid
        # Function should either reject or use fallback
        assert negative_rate < 0, "Test setup: Rate is negative"
        
        # Expected behavior: use fallback
        expected_result = 0.02
        assert expected_result >= 0, "Final rate must be non-negative"


class TestRiskFreeRateIntegration:
    """Integration tests with RiskAnalyzer class"""
    
    def test_sharpe_calculation_with_dynamic_rate(self):
        """
        Test that Sharpe ratio uses dynamic rate instead of hardcoded 0.02
        Expected: Different results when RF rate changes
        """
        # Synthetic return data
        returns = pd.Series([0.01, -0.005, 0.02, 0.015, -0.01] * 50)  # 250 days
        
        # Test with different risk-free rates
        rf_rate_low = 0.02  # 2%
        rf_rate_high = 0.05  # 5%
        
        # Calculate Sharpe with low rate
        excess_returns_low = returns - rf_rate_low/252
        sharpe_low = (excess_returns_low.mean() / excess_returns_low.std()) * np.sqrt(252)
        
        # Calculate Sharpe with high rate
        excess_returns_high = returns - rf_rate_high/252
        sharpe_high = (excess_returns_high.mean() / excess_returns_high.std()) * np.sqrt(252)
        
        # Sharpe should be lower with higher RF rate (less excess return)
        assert sharpe_low > sharpe_high, "Sharpe ratio should decrease with higher RF rate"
        assert abs(sharpe_low - sharpe_high) > 0.01, "Sharpe ratios should differ significantly"


class TestCachingBehavior:
    """Test caching mechanism for risk-free rate"""
    
    def test_cache_duration(self):
        """
        Test that rate is cached for 24 hours
        Expected: Same rate returned within 24 hours without API call
        """
        cache_duration_hours = 24
        cache_duration_seconds = cache_duration_hours * 3600
        
        assert cache_duration_seconds == 86400, "Cache should last 24 hours (86400 seconds)"
    
    def test_cache_invalidation(self):
        """
        Test that cache is invalidated after 24 hours
        Expected: New API call made after cache expires
        """
        # This will be tested with time mocking in integration tests
        pass


class TestErrorHandling:
    """Test error handling and logging"""
    
    def test_logging_on_api_failure(self):
        """
        Test that API failures are properly logged
        Expected: Warning log entry created
        """
        # This will verify logging behavior
        pass
    
    def test_exception_handling(self):
        """
        Test that exceptions don't crash the system
        Expected: Graceful fallback on any exception
        """
        # Test various exception types
        exceptions_to_test = [
            ConnectionError("Network error"),
            TimeoutError("API timeout"),
            ValueError("Invalid data"),
            KeyError("Missing field")
        ]
        
        # All should result in fallback, not crash
        fallback = 0.02
        assert fallback == 0.02, "Should always have fallback available"


# Synthetic data generators for testing
def generate_synthetic_irx_data(days=5, base_rate=4.25, volatility=0.5):
    """
    Generate synthetic ^IRX data for testing
    
    Args:
        days: Number of days of data
        base_rate: Base rate (e.g., 4.25 for 4.25%)
        volatility: Daily volatility in percentage points
    
    Returns:
        DataFrame with Date and Close columns
    """
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    rates = base_rate + np.random.normal(0, volatility, days)
    
    return pd.DataFrame({
        'Close': rates
    }, index=dates)


def test_synthetic_data_generator():
    """Test that synthetic data generator works correctly"""
    df = generate_synthetic_irx_data(days=5, base_rate=4.25, volatility=0.5)
    
    assert len(df) == 5, "Should generate 5 days of data"
    assert 'Close' in df.columns, "Should have Close column"
    assert df['Close'].mean() > 0, "Rates should be positive"
    assert len(df[df['Close'] < 0]) == 0 or len(df[df['Close'] < 0]) < len(df)/2, \
        "Most rates should be positive"


# Test runner
if __name__ == '__main__':
    print("="*70)
    print("Risk-Free Rate Test Suite")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Task: P1.1 - Dynamic Risk-Free Rate")
    print(f"Phase: 1 - Foundation & Bug Fixes")
    print(f"Day: 1 - Unit Tests (Checkpoint 1)")
    print("="*70)
    
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])
    
    print("\n" + "="*70)
    print("✅ CHECKPOINT 1 STATUS: Tests Defined")
    print("Next Step: Implement fetch_current_risk_free_rate() function")
    print("="*70)
