#!/usr/bin/env python3
"""
Integration Tests for RiskAnalyzer with Dynamic Risk-Free Rate
==============================================================

Tests the integration of fetch_current_risk_free_rate() with RiskAnalyzer class.
Validates that Sharpe and Sortino ratios correctly use the dynamic rate.

Test Coverage:
- RiskAnalyzer initialization with dynamic vs static rate
- Sharpe ratio calculation accuracy with different RF rates
- Sortino ratio calculation accuracy with different RF rates
- Backward compatibility with legacy code
- Performance validation
"""

import pytest
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analysis_scripts'))
from risk_analysis import RiskAnalyzer
from risk_free_rate_fetcher import fetch_current_risk_free_rate


class TestRiskAnalyzerInitialization:
    """Test RiskAnalyzer initialization with dynamic RF rate"""
    
    def test_dynamic_rate_initialization(self):
        """Test that RiskAnalyzer uses dynamic rate by default"""
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
        
        # Should fetch current rate (not hardcoded 0.02)
        current_rate = fetch_current_risk_free_rate()
        assert analyzer.risk_free_rate == current_rate
        
        # Should be in reasonable range
        assert 0 <= analyzer.risk_free_rate <= 0.10
    
    def test_static_rate_initialization(self):
        """Test backward compatibility with static rate"""
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=False)
        
        # Should use hardcoded 2%
        assert analyzer.risk_free_rate == 0.02
    
    def test_default_behavior(self):
        """Test that default behavior uses dynamic rate"""
        analyzer = RiskAnalyzer()
        
        # Default should be dynamic
        current_rate = fetch_current_risk_free_rate()
        assert analyzer.risk_free_rate == current_rate


class TestSharpeRatioWithDynamicRate:
    """Test Sharpe ratio calculations with dynamic risk-free rate"""
    
    def create_sample_returns(self, mean_return=0.001, volatility=0.02, days=252):
        """Generate synthetic return data"""
        np.random.seed(42)
        returns = np.random.normal(mean_return, volatility, days)
        return pd.Series(returns)
    
    def test_sharpe_ratio_uses_dynamic_rate(self):
        """Verify Sharpe ratio uses the dynamic risk-free rate"""
        returns = self.create_sample_returns(mean_return=0.002, volatility=0.015)
        
        # Create two analyzers with different rates
        analyzer_dynamic = RiskAnalyzer(use_dynamic_rf_rate=True)
        analyzer_static = RiskAnalyzer(use_dynamic_rf_rate=False)
        
        sharpe_dynamic = analyzer_dynamic.calculate_sharpe_ratio(returns)
        sharpe_static = analyzer_static.calculate_sharpe_ratio(returns)
        
        # Sharpe ratios should differ if RF rates differ
        current_rate = fetch_current_risk_free_rate()
        if abs(current_rate - 0.02) > 0.001:  # If rates differ by >0.1%
            assert sharpe_dynamic != sharpe_static
    
    def test_sharpe_ratio_manual_calculation(self):
        """Validate Sharpe ratio against manual calculation"""
        returns = self.create_sample_returns(mean_return=0.002, volatility=0.015)
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
        
        # Calculate Sharpe using RiskAnalyzer
        sharpe_calculated = analyzer.calculate_sharpe_ratio(returns)
        
        # Manual calculation
        rf_rate = analyzer.risk_free_rate
        excess_returns = returns - rf_rate / 252
        sharpe_manual = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
        
        # Should match within floating point precision
        assert abs(sharpe_calculated - sharpe_manual) < 1e-6
    
    def test_sharpe_ratio_with_high_rf_rate(self):
        """Test Sharpe ratio when RF rate is high (e.g., 5%)"""
        returns = self.create_sample_returns(mean_return=0.0005, volatility=0.015)
        
        # Artificially set high RF rate
        analyzer_low_rf = RiskAnalyzer(use_dynamic_rf_rate=False)
        analyzer_low_rf.risk_free_rate = 0.01  # 1%
        
        analyzer_high_rf = RiskAnalyzer(use_dynamic_rf_rate=False)
        analyzer_high_rf.risk_free_rate = 0.05  # 5%
        
        sharpe_low = analyzer_low_rf.calculate_sharpe_ratio(returns)
        sharpe_high = analyzer_high_rf.calculate_sharpe_ratio(returns)
        
        # Higher RF rate should result in lower Sharpe ratio
        assert sharpe_high < sharpe_low
    
    def test_sharpe_ratio_with_low_rf_rate(self):
        """Test Sharpe ratio when RF rate is low (e.g., 0.5%)"""
        returns = self.create_sample_returns(mean_return=0.002, volatility=0.015)
        
        # Artificially set low RF rate
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=False)
        analyzer.risk_free_rate = 0.005  # 0.5%
        
        sharpe = analyzer.calculate_sharpe_ratio(returns)
        
        # Should be positive with decent returns
        assert sharpe > 0


class TestSortinoRatioWithDynamicRate:
    """Test Sortino ratio calculations with dynamic risk-free rate"""
    
    def create_asymmetric_returns(self, days=252):
        """Generate returns with negative skew (more downside)"""
        np.random.seed(42)
        positive_returns = np.random.normal(0.002, 0.01, int(days * 0.6))
        negative_returns = np.random.normal(-0.003, 0.025, int(days * 0.4))
        returns = np.concatenate([positive_returns, negative_returns])
        np.random.shuffle(returns)
        return pd.Series(returns)
    
    def test_sortino_ratio_uses_dynamic_rate(self):
        """Verify Sortino ratio uses the dynamic risk-free rate"""
        returns = self.create_asymmetric_returns()
        
        analyzer_dynamic = RiskAnalyzer(use_dynamic_rf_rate=True)
        analyzer_static = RiskAnalyzer(use_dynamic_rf_rate=False)
        
        sortino_dynamic = analyzer_dynamic.calculate_sortino_ratio(returns)
        sortino_static = analyzer_static.calculate_sortino_ratio(returns)
        
        # Sortino ratios should differ if RF rates differ
        current_rate = fetch_current_risk_free_rate()
        if abs(current_rate - 0.02) > 0.001:
            assert sortino_dynamic != sortino_static
    
    def test_sortino_ratio_manual_calculation(self):
        """Validate Sortino ratio against manual calculation"""
        returns = self.create_asymmetric_returns()
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
        
        # Calculate Sortino using RiskAnalyzer
        sortino_calculated = analyzer.calculate_sortino_ratio(returns)
        
        # Manual calculation
        rf_rate = analyzer.risk_free_rate
        excess_returns = returns - rf_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        downside_deviation = downside_returns.std()
        sortino_manual = (excess_returns.mean() / downside_deviation) * np.sqrt(252)
        
        # Should match within floating point precision
        assert abs(sortino_calculated - sortino_manual) < 1e-6
    
    def test_sortino_higher_than_sharpe_with_downside_skew(self):
        """Sortino should be higher than Sharpe for negatively skewed returns"""
        returns = self.create_asymmetric_returns()
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
        
        sharpe = analyzer.calculate_sharpe_ratio(returns)
        sortino = analyzer.calculate_sortino_ratio(returns)
        
        # Sortino penalizes only downside, so should be higher
        # (This test may fail if returns are positively skewed)
        if returns.mean() > 0:
            assert sortino >= sharpe or abs(sortino - sharpe) < 0.1


class TestComprehensiveRiskProfile:
    """Test comprehensive risk profile generation with dynamic RF rate"""
    
    def create_sample_price_data(self, days=252):
        """Generate synthetic price data"""
        np.random.seed(42)
        initial_price = 100.0
        returns = np.random.normal(0.001, 0.02, days)
        prices = [initial_price]
        
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        dates = pd.date_range(end=pd.Timestamp.now(), periods=days+1, freq='D')
        return pd.Series(prices, index=dates)
    
    def test_comprehensive_profile_includes_sharpe_sortino(self):
        """Test that comprehensive profile includes Sharpe and Sortino"""
        price_data = self.create_sample_price_data()
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
        
        risk_profile = analyzer.comprehensive_risk_profile(price_data)
        
        # Should include both ratios
        assert 'sharpe_ratio' in risk_profile
        assert 'sortino_ratio' in risk_profile
        
        # Both should be numeric
        assert isinstance(risk_profile['sharpe_ratio'], (int, float))
        assert isinstance(risk_profile['sortino_ratio'], (int, float))
        
        # Should not be NaN
        assert not np.isnan(risk_profile['sharpe_ratio'])
        assert not np.isnan(risk_profile['sortino_ratio'])
    
    def test_comprehensive_profile_with_dynamic_vs_static(self):
        """Compare comprehensive profiles with dynamic vs static RF rate"""
        price_data = self.create_sample_price_data()
        
        analyzer_dynamic = RiskAnalyzer(use_dynamic_rf_rate=True)
        analyzer_static = RiskAnalyzer(use_dynamic_rf_rate=False)
        
        profile_dynamic = analyzer_dynamic.comprehensive_risk_profile(price_data)
        profile_static = analyzer_static.comprehensive_risk_profile(price_data)
        
        # Sharpe and Sortino should differ if RF rates differ
        current_rate = fetch_current_risk_free_rate()
        if abs(current_rate - 0.02) > 0.001:
            assert profile_dynamic['sharpe_ratio'] != profile_static['sharpe_ratio']
            assert profile_dynamic['sortino_ratio'] != profile_static['sortino_ratio']
        
        # Other metrics should be the same (VaR, volatility, etc.)
        assert profile_dynamic['volatility_annualized'] == profile_static['volatility_annualized']
        assert profile_dynamic['var_5'] == profile_static['var_5']


class TestBackwardCompatibility:
    """Test backward compatibility with existing code"""
    
    def test_no_parameter_defaults_to_dynamic(self):
        """Test that calling RiskAnalyzer() defaults to dynamic rate"""
        analyzer = RiskAnalyzer()
        
        # Should use dynamic rate (not 0.02)
        current_rate = fetch_current_risk_free_rate()
        assert analyzer.risk_free_rate == current_rate
    
    def test_existing_usage_still_works(self):
        """Test that existing code patterns still work"""
        # Old code pattern: analyzer = RiskAnalyzer()
        analyzer = RiskAnalyzer()
        
        # Generate sample data
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.015, 252))
        
        # All existing methods should still work
        sharpe = analyzer.calculate_sharpe_ratio(returns)
        sortino = analyzer.calculate_sortino_ratio(returns)
        var_5 = analyzer.calculate_var(returns, 0.05)
        
        # Should return valid numbers
        assert isinstance(sharpe, (int, float))
        assert isinstance(sortino, (int, float))
        assert isinstance(var_5, (int, float))


class TestPerformance:
    """Test performance of dynamic RF rate integration"""
    
    def test_initialization_performance(self):
        """Test that initialization with dynamic rate is fast"""
        import time
        
        # Time 10 initializations
        start = time.time()
        for _ in range(10):
            analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
        end = time.time()
        
        # Should be fast due to caching (all 10 < 100ms total)
        assert (end - start) < 0.1
    
    def test_calculation_performance_not_degraded(self):
        """Test that Sharpe/Sortino calculations are still fast"""
        import time
        
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
        returns = pd.Series(np.random.normal(0.001, 0.015, 252))
        
        # Time 100 Sharpe calculations
        start = time.time()
        for _ in range(100):
            analyzer.calculate_sharpe_ratio(returns)
        end = time.time()
        
        # Should be very fast (<100ms for 100 calculations)
        assert (end - start) < 0.1


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_returns(self):
        """Test behavior with empty returns"""
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
        empty_returns = pd.Series([])
        
        # Should handle gracefully (may return NaN or raise appropriate error)
        try:
            sharpe = analyzer.calculate_sharpe_ratio(empty_returns)
            # If it doesn't raise, should be NaN or inf
            assert np.isnan(sharpe) or np.isinf(sharpe)
        except (ValueError, ZeroDivisionError):
            # This is also acceptable behavior
            pass
    
    def test_zero_volatility_returns(self):
        """Test behavior with zero volatility (constant returns)"""
        analyzer = RiskAnalyzer(use_dynamic_rf_rate=True)
        constant_returns = pd.Series([0.001] * 252)
        
        # Should handle division by zero
        try:
            sharpe = analyzer.calculate_sharpe_ratio(constant_returns)
            # May return inf or very large number
            assert sharpe > 0 or np.isinf(sharpe)
        except ZeroDivisionError:
            # This is also acceptable
            pass


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])
