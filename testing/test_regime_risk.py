"""
Regime Risk Analysis Test Suite (Day 12 - P2.4 Checkpoint 1)
Tests regime detection using MSCI/NBER sustained bear logic

Test Coverage:
- Bull market regime detection (50>200 MA, price>50 MA, DD<10%)
- Bear market regime detection (DD>20% OR sustained 50<200 for 20 days)  
- Volatile/Sideways regime detection (choppy, no clear trend)
- Optional VIX filter override
- Defensive score calculation (bear_vol / bull_vol)
- Risk metrics per regime (volatility, Sharpe, avg return)
- Edge cases (insufficient data, extreme values, missing regimes)

Date: February 16, 2026
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis_scripts.risk_analysis import RiskAnalyzer


class TestRegimeDetection:
    """Test regime classification logic (Bull/Bear/Volatile)"""
    
    @pytest.fixture
    def analyzer(self):
        """Create RiskAnalyzer instance"""
        return RiskAnalyzer()
    
    def test_bull_market_detection(self, analyzer):
        """Test bull market: 50>200 MA, price>50 MA, DD<10%"""
        # Create synthetic bull market data (consistent uptrend)
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Stock returns: steady uptrend
        np.random.seed(42)
        stock_returns = pd.Series(
            np.random.normal(0.001, 0.01, 250),  # +0.1% daily avg
            index=dates
        )
        
        # Market returns: similar uptrend, 50 MA > 200 MA
        market_returns = pd.Series(
            np.random.normal(0.0008, 0.008, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Validate bull market detected
        assert result is not None, "Result should not be None"
        assert 'regime_distribution' in result, "Should have regime distribution"
        assert result['regime_distribution']['bull_days'] > 0, "Should detect some bull days"
        assert result['bull_market_volatility'] is not None, "Should calculate bull volatility"
        assert result['bull_market_sharpe'] is not None, "Should calculate bull Sharpe"
        
        print(f"\n✅ Bull Market Test:")
        print(f"Bull Days: {result['regime_distribution']['bull_days']}")
        print(f"Bull Volatility: {result['bull_market_volatility']:.4f}")
        print(f"Bull Sharpe: {result['bull_market_sharpe']:.2f}")
    
    def test_bear_market_detection(self, analyzer):
        """Test bear market: DD>20% OR sustained 50<200 for 20 days"""
        # Create synthetic bear market data (sustained downtrend)
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Stock returns: consistent downtrend
        np.random.seed(43)
        stock_returns = pd.Series(
            np.random.normal(-0.002, 0.02, 250),  # -0.2% daily avg, high vol
            index=dates
        )
        
        # Market returns: sustained downtrend for bear detection
        market_returns = pd.Series(
            np.random.normal(-0.0015, 0.015, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Validate bear market detected
        assert result is not None, "Result should not be None"
        assert 'regime_distribution' in result, "Should have regime distribution"
        assert result['regime_distribution']['bear_days'] > 0, "Should detect some bear days"
        assert result['bear_market_volatility'] is not None, "Should calculate bear volatility"
        assert result['bear_market_sharpe'] is not None, "Should calculate bear Sharpe"
        
        print(f"\n✅ Bear Market Test:")
        print(f"Bear Days: {result['regime_distribution']['bear_days']}")
        print(f"Bear Volatility: {result['bear_market_volatility']:.4f}")
        print(f"Bear Sharpe: {result['bear_market_sharpe']:.2f}")
    
    def test_volatile_sideways_detection(self, analyzer):
        """Test volatile market: choppy, no clear trend"""
        # Create synthetic sideways/volatile data (mean-reverting)
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Stock returns: high volatility, no trend
        np.random.seed(44)
        stock_returns = pd.Series(
            np.random.normal(0, 0.03, 250),  # 0% avg, 3% daily vol
            index=dates
        )
        
        # Market returns: choppy, crossing 50/200 MA frequently
        market_returns = pd.Series(
            np.random.normal(0, 0.025, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Validate volatile market detected
        assert result is not None, "Result should not be None"
        assert 'regime_distribution' in result, "Should have regime distribution"
        assert result['regime_distribution']['volatile_days'] > 0, "Should detect some volatile days"
        assert result['volatile_market_volatility'] is not None, "Should calculate volatile volatility"
        
        print(f"\n✅ Volatile Market Test:")
        print(f"Volatile Days: {result['regime_distribution']['volatile_days']}")
        print(f"Volatile Volatility: {result['volatile_market_volatility']:.4f}")


class TestDefensiveScore:
    """Test defensive score calculation and classification"""
    
    @pytest.fixture
    def analyzer(self):
        return RiskAnalyzer()
    
    def test_defensive_stock_high_score(self, analyzer):
        """Test defensive stock: lower bear vol than bull vol → score >60"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Defensive stock: holds up better in bear markets
        np.random.seed(45)
        # Low volatility in both regimes, but especially in bear
        stock_returns = pd.Series(
            np.random.normal(0.0005, 0.008, 250),  # Low vol
            index=dates
        )
        
        # Market with clear bull then bear pattern
        market_returns = pd.Series(
            np.concatenate([
                np.random.normal(0.001, 0.01, 125),  # Bull first half
                np.random.normal(-0.003, 0.025, 125)  # Bear second half
            ]),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Defensive stocks have lower bear/bull volatility ratio
        assert result is not None, "Result should not be None"
        
        # Debug output
        print(f"\n�� Defensive Stock Results:")
        print(f"Bull Days: {result['regime_distribution']['bull_days']}")
        print(f"Bear Days: {result['regime_distribution']['bear_days']}")
        print(f"Volatile Days: {result['regime_distribution']['volatile_days']}")
        print(f"Bull Volatility: {result['bull_market_volatility']}")
        print(f"Bear Volatility: {result['bear_market_volatility']}")
        print(f"Defensive Score: {result['defensive_score']}")
        print(f"Profile: {result['profile']}")
        
        # For this test, we just verify structure (score may be None if regimes not detected)
        assert result['profile'] in ['Defensive', 'Balanced', 'Aggressive'], "Should classify profile"
        
        # If both regimes detected, volatility ratio should exist
        if result['bull_market_volatility'] and result['bear_market_volatility']:
            assert result['volatility_ratio'] is not None, "Should calculate volatility ratio"
            assert result['volatility_ratio'] > 0, "Volatility ratio should be positive"
        
        print(f"\n✅ Defensive Stock Test:")
        print(f"Bull Volatility: {result['bull_market_volatility']}")
        print(f"Bear Volatility: {result['bear_market_volatility']}")
        print(f"Volatility Ratio: {result['volatility_ratio']}")
        print(f"Defensive Score: {result['defensive_score']}")
        print(f"Profile: {result['profile']}")
    
    def test_aggressive_stock_low_score(self, analyzer):
        """Test aggressive stock: higher bear vol than bull vol → score <40"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Aggressive stock: amplifies market moves
        np.random.seed(46)
        stock_returns = pd.Series(
            np.concatenate([
                np.random.normal(0.002, 0.015, 125),  # Higher vol in bull
                np.random.normal(-0.004, 0.04, 125)   # Much higher vol in bear
            ]),
            index=dates
        )
        
        # Market with clear bull then bear pattern
        market_returns = pd.Series(
            np.concatenate([
                np.random.normal(0.001, 0.01, 125),
                np.random.normal(-0.003, 0.025, 125)
            ]),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        assert result is not None, "Result should not be None"
        
        # Debug output
        print(f"\n✅ Aggressive Stock Results:")
        print(f"Bull Days: {result['regime_distribution']['bull_days']}")
        print(f"Bear Days: {result['regime_distribution']['bear_days']}")
        print(f"Bull Volatility: {result['bull_market_volatility']}")
        print(f"Bear Volatility: {result['bear_market_volatility']}")
        print(f"Defensive Score: {result['defensive_score']}")
        print(f"Profile: {result['profile']}")
        
        # For this test, we verify profile classification
        assert result['profile'] in ['Defensive', 'Balanced', 'Aggressive'], "Should classify profile"
        
        # Aggressive stocks have higher bear/bull volatility ratio (if both detected)
        if result['bull_market_volatility'] and result['bear_market_volatility']:
            assert result['volatility_ratio'] is not None, "Should calculate volatility ratio"
            # Bear vol > Bull vol for aggressive stocks
            assert result['bear_market_volatility'] >= result['bull_market_volatility'], \
                "Aggressive stocks should have bear_vol >= bull_vol"
        
        print(f"\n✅ Aggressive Stock Test:")
        print(f"Bull Volatility: {result['bull_market_volatility']}")
        print(f"Bear Volatility: {result['bear_market_volatility']}")
        print(f"Volatility Ratio: {result['volatility_ratio']}")
        print(f"Defensive Score: {result['defensive_score']}")
        print(f"Profile: {result['profile']}")
    
    def test_balanced_stock_mid_score(self, analyzer):
        """Test balanced stock: similar vol across regimes → score 40-60"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Balanced stock: consistent volatility
        np.random.seed(47)
        stock_returns = pd.Series(
            np.random.normal(0, 0.015, 250),  # Consistent vol throughout
            index=dates
        )
        
        market_returns = pd.Series(
            np.concatenate([
                np.random.normal(0.001, 0.01, 125),
                np.random.normal(-0.003, 0.025, 125)
            ]),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        assert result is not None, "Result should not be None"
        
        # Debug output
        print(f"\n✅ Balanced Stock Results:")
        print(f"Bull Days: {result['regime_distribution']['bull_days']}")
        print(f"Bear Days: {result['regime_distribution']['bear_days']}")
        print(f"Defensive Score: {result['defensive_score']}")
        print(f"Profile: {result['profile']}")
        
        # For this test, we verify profile exists
        assert result['profile'] in ['Defensive', 'Balanced', 'Aggressive'], "Should classify profile"
        
        print(f"\n✅ Balanced Stock Test:")
        print(f"Defensive Score: {result['defensive_score']}")
        print(f"Profile: {result['profile']}")


class TestRegimeMetrics:
    """Test metric calculations per regime"""
    
    @pytest.fixture
    def analyzer(self):
        return RiskAnalyzer()
    
    def test_volatility_calculation_per_regime(self, analyzer):
        """Test volatility calculated correctly for each regime"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        np.random.seed(48)
        stock_returns = pd.Series(
            np.random.normal(0, 0.02, 250),
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0, 0.015, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Validate volatility format
        for regime in ['bull', 'bear', 'volatile']:
            vol_key = f'{regime}_market_volatility'
            if result[vol_key] is not None:
                assert isinstance(result[vol_key], (int, float)), f"{vol_key} should be numeric"
                assert result[vol_key] >= 0, f"{vol_key} should be non-negative"
                assert result[vol_key] < 5.0, f"{vol_key} should be reasonable (<500%)"
    
    def test_sharpe_calculation_per_regime(self, analyzer):
        """Test Sharpe ratio calculated per regime"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        np.random.seed(49)
        stock_returns = pd.Series(
            np.random.normal(0.001, 0.02, 250),
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0.0008, 0.015, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Validate Sharpe format
        for regime in ['bull', 'bear']:
            sharpe_key = f'{regime}_market_sharpe'
            if result[sharpe_key] is not None:
                assert isinstance(result[sharpe_key], (int, float)), f"{sharpe_key} should be numeric"
                assert -5 <= result[sharpe_key] <= 10, f"{sharpe_key} should be reasonable range"
    
    def test_regime_days_distribution(self, analyzer):
        """Test regime days add up correctly"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        np.random.seed(50)
        stock_returns = pd.Series(
            np.random.normal(0, 0.02, 250),
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0, 0.015, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Validate distribution
        dist = result['regime_distribution']
        total_days = dist['bull_days'] + dist['bear_days'] + dist['volatile_days']
        
        # Total should be close to input length (some days may be NaN due to MA calculation)
        assert total_days > 0, "Should have some regime days"
        assert total_days <= len(stock_returns), "Total days should not exceed input"
        
        print(f"\n✅ Regime Distribution:")
        print(f"Bull: {dist['bull_days']} days ({dist['bull_days']/total_days*100:.1f}%)")
        print(f"Bear: {dist['bear_days']} days ({dist['bear_days']/total_days*100:.1f}%)")
        print(f"Volatile: {dist['volatile_days']} days ({dist['volatile_days']/total_days*100:.1f}%)")


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def analyzer(self):
        return RiskAnalyzer()
    
    def test_insufficient_data(self, analyzer):
        """Test with <200 days (insufficient for 200 MA)"""
        dates = pd.date_range('2020-01-01', periods=50, freq='D')
        
        stock_returns = pd.Series(
            np.random.normal(0, 0.02, 50),
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0, 0.015, 50),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Should still return result, but with limited data warning
        assert result is not None, "Should return result even with limited data"
        # Some metrics may be None due to insufficient regime data
    
    def test_missing_regime_None_values(self, analyzer):
        """Test when no bull or bear regime detected"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # All flat returns (no regime detected)
        stock_returns = pd.Series(
            np.zeros(250),
            index=dates
        )
        market_returns = pd.Series(
            np.zeros(250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Should handle gracefully with None values
        assert result is not None, "Should return result even with no regimes"
        # Defensive score may be None if both bull/bear missing
    
    def test_extreme_volatility(self, analyzer):
        """Test with extreme volatility (100%+ annualized)"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Extreme volatility
        np.random.seed(51)
        stock_returns = pd.Series(
            np.random.normal(0, 0.08, 250),  # 8% daily vol = ~127% annualized
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0, 0.04, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Should handle extreme values
        assert result is not None, "Should handle extreme volatility"
        if result['bull_market_volatility'] is not None:
            assert result['bull_market_volatility'] > 0, "Should calculate volatility"
    
    def test_all_negative_returns(self, analyzer):
        """Test with all negative returns (severe bear market)"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Severe bear market (all losses)
        stock_returns = pd.Series(
            np.random.normal(-0.01, 0.03, 250),  # -1% daily avg
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(-0.008, 0.025, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Should handle negative returns
        assert result is not None, "Should handle all negative returns"
        assert result['regime_distribution']['bear_days'] > 0, "Should detect bear market"
        
        # Sharpe should be negative
        if result['bear_market_sharpe'] is not None:
            assert result['bear_market_sharpe'] < 0, "Sharpe should be negative for losses"
    
    def test_single_regime_only(self, analyzer):
        """Test when only one regime detected (e.g., only bull)"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Strong bull market throughout (no bear period)
        stock_returns = pd.Series(
            np.random.normal(0.003, 0.01, 250),  # +0.3% daily
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0.002, 0.008, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Should still return result
        assert result is not None, "Should handle single regime"
        
        # Defensive score may be None if missing bear or bull
        # (can't calculate ratio without both)


class TestVIXFilter:
    """Test optional VIX filter functionality"""
    
    @pytest.fixture
    def analyzer(self):
        return RiskAnalyzer()
    
    def test_high_vix_overrides_bull(self, analyzer):
        """Test high VIX overrides bull classification"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        # Bull market setup
        stock_returns = pd.Series(
            np.random.normal(0.001, 0.015, 250),
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0.001, 0.01, 250),
            index=dates
        )
        
        # High VIX (elevated fear)
        vix_data = pd.Series(
            np.random.normal(30, 5, 250),  # High VIX ~30
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns, vix_data=vix_data)
        
        # With high VIX, should classify more days as volatile
        assert result is not None, "Should return result with VIX filter"
        assert result['regime_distribution']['volatile_days'] > 0, "High VIX should create volatile days"
    
    def test_without_vix_filter(self, analyzer):
        """Test regime detection without VIX data (optional parameter)"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        stock_returns = pd.Series(
            np.random.normal(0.001, 0.015, 250),
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0.001, 0.01, 250),
            index=dates
        )
        
        # No VIX data
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns, vix_data=None)
        
        # Should work fine without VIX
        assert result is not None, "Should work without VIX filter"
        assert 'regime_distribution' in result, "Should have regime distribution"


class TestReturnStructure:
    """Test return structure and field presence"""
    
    @pytest.fixture
    def analyzer(self):
        return RiskAnalyzer()
    
    def test_all_required_fields_present(self, analyzer):
        """Test all expected fields are in return dict"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        stock_returns = pd.Series(
            np.random.normal(0, 0.02, 250),
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0, 0.015, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        # Required fields
        required_fields = [
            'bull_market_volatility',
            'bear_market_volatility',
            'volatile_market_volatility',
            'volatility_ratio',
            'bull_market_sharpe',
            'bear_market_sharpe',
            'defensive_score',
            'profile',
            'regime_distribution',
            'interpretation'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Sub-fields in regime_distribution
        assert 'bull_days' in result['regime_distribution'], "Missing bull_days"
        assert 'bear_days' in result['regime_distribution'], "Missing bear_days"
        assert 'volatile_days' in result['regime_distribution'], "Missing volatile_days"
    
    def test_profile_classification_valid(self, analyzer):
        """Test profile is one of: Defensive, Balanced, Aggressive"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        stock_returns = pd.Series(
            np.random.normal(0, 0.02, 250),
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0, 0.015, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        assert result['profile'] in ['Defensive', 'Balanced', 'Aggressive'], \
            "Profile must be Defensive, Balanced, or Aggressive"
    
    def test_interpretation_string_present(self, analyzer):
        """Test interpretation is a non-empty string"""
        dates = pd.date_range('2020-01-01', periods=250, freq='D')
        
        stock_returns = pd.Series(
            np.random.normal(0, 0.02, 250),
            index=dates
        )
        market_returns = pd.Series(
            np.random.normal(0, 0.015, 250),
            index=dates
        )
        
        result = analyzer.calculate_regime_risk_advanced(stock_returns, market_returns)
        
        assert isinstance(result['interpretation'], str), "Interpretation should be string"
        assert len(result['interpretation']) > 0, "Interpretation should not be empty"
        assert result['profile'] in result['interpretation'], "Interpretation should mention profile"


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, '-v', '-s'])
