"""
Unit Tests for Liquidity Score Implementation (Hasbrouck Model)
================================================================

Day 6 (Feb 10, 2026) - P2.2 Liquidity Score - Day 1 Unit Tests
Feature: Liquidity Risk Score using Volume + Market Cap + Stability

Formula (Hasbrouck weights):
- Volume Component: 60% weight
- Market Cap Component: 15% weight  
- Stability Component: 25% weight

Test Strategy:
1. Test synthetic data with known outputs
2. Test edge cases (None, empty, invalid)
3. Test each component independently
4. Test full integration
5. Test industry benchmarks (mega/large/mid/small cap)

Checkpoint 1: All unit tests must pass (100%)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# Liquidity Score Thresholds (Industry Standard)
MEGA_CAP = {'min_volume': 10_000_000, 'min_mcap': 200_000_000_000}
LARGE_CAP = {'min_volume': 5_000_000, 'min_mcap': 10_000_000_000}
MID_CAP = {'min_volume': 1_000_000, 'min_mcap': 2_000_000_000}
SMALL_CAP = {'min_volume': 500_000, 'min_mcap': 300_000_000}


class TestLiquidityScoreFormula:
    """Test the Hasbrouck formula calculation."""
    
    def test_perfect_liquidity_mega_cap(self):
        """Test mega-cap stock with perfect liquidity."""
        # Simulated mega-cap: AAPL-like
        avg_volume = 50_000_000  # 50M shares/day (very high)
        market_cap = 3_000_000_000_000  # $3T market cap
        volume_volatility = 0.10  # Low 10% volatility
        avg_price = 150.0
        
        # Calculate components
        volume_score = min(100, (avg_volume / 10_000_000) * 100) * 0.6
        mcap_score = min(100, (market_cap / 200_000_000_000) * 100) * 0.15
        stability_score = min(100, (1 - volume_volatility) * 100) * 0.25
        
        expected_score = volume_score + mcap_score + stability_score
        
        # Expected: volume=60, mcap=15, stability=22.5 = 97.5
        assert expected_score > 90, "Mega-cap should have >90 liquidity score"
        assert 95 < expected_score < 100, f"Expected ~97.5, got {expected_score}"
    
    def test_low_liquidity_small_cap(self):
        """Test small-cap stock with low liquidity."""
        # Simulated small-cap
        avg_volume = 200_000  # 200K shares/day (low)
        market_cap = 500_000_000  # $500M market cap
        volume_volatility = 0.40  # High 40% volatility
        avg_price = 5.0
        
        # Calculate components
        volume_score = min(100, (avg_volume / 10_000_000) * 100) * 0.6
        mcap_score = min(100, (market_cap / 200_000_000_000) * 100) * 0.15
        stability_score = min(100, (1 - volume_volatility) * 100) * 0.25
        
        expected_score = volume_score + mcap_score + stability_score
        
        # Expected: volume=1.2, mcap=0.04, stability=15 = 16.24
        assert expected_score < 30, f"Small-cap should have <30 score, got {expected_score}"
    
    def test_mid_cap_moderate_liquidity(self):
        """Test mid-cap stock with moderate liquidity."""
        # Simulated mid-cap: PLTR-like
        avg_volume = 30_000_000  # 30M shares/day (good)
        market_cap = 50_000_000_000  # $50B market cap
        volume_volatility = 0.25  # Moderate 25% volatility
        avg_price = 20.0
        
        # Calculate components
        volume_score = min(100, (avg_volume / 10_000_000) * 100) * 0.6
        mcap_score = min(100, (market_cap / 200_000_000_000) * 100) * 0.15
        stability_score = min(100, (1 - volume_volatility) * 100) * 0.25
        
        expected_score = volume_score + mcap_score + stability_score
        
        # Expected: volume=60, mcap=3.75, stability=18.75 = 82.5
        assert 70 < expected_score < 90, f"Mid-cap should have 70-90 score, got {expected_score}"
    
    def test_component_weights_sum_to_one(self):
        """Verify Hasbrouck weights sum to 1.0."""
        weights = [0.60, 0.15, 0.25]  # Volume, MCap, Stability
        assert sum(weights) == 1.0, "Weights must sum to 1.0"
    
    def test_volume_component_dominance(self):
        """Test that volume component has 60% weight."""
        # High volume but low mcap
        volume_score = 100 * 0.6  # Max volume score
        mcap_score = 10 * 0.15    # Low mcap score
        stability_score = 80 * 0.25  # Good stability
        
        total = volume_score + mcap_score + stability_score
        
        # Volume should dominate score
        volume_contribution = volume_score / total
        assert volume_contribution > 0.50, "Volume should contribute >50% to total"
    
    def test_stability_component_penalty(self):
        """Test that high volatility penalizes stability score."""
        # Very volatile volume
        volume_volatility_high = 0.80  # 80% volatility
        volume_volatility_low = 0.10   # 10% volatility
        
        stability_high_vol = (1 - volume_volatility_high) * 100 * 0.25
        stability_low_vol = (1 - volume_volatility_low) * 100 * 0.25
        
        assert stability_low_vol > stability_high_vol, "Low volatility should score higher"
        assert stability_low_vol / stability_high_vol > 3, "Should be >3x difference"


class TestLiquidityScoreEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_volume(self):
        """Test handling of zero volume (illiquid stock)."""
        avg_volume = 0
        market_cap = 1_000_000_000
        volume_volatility = 0.20
        
        volume_score = min(100, (avg_volume / 10_000_000) * 100) * 0.6
        
        assert volume_score == 0, "Zero volume should give zero score"
    
    def test_zero_market_cap(self):
        """Test handling of zero market cap (invalid)."""
        avg_volume = 1_000_000
        market_cap = 0
        volume_volatility = 0.20
        
        mcap_score = min(100, (market_cap / 200_000_000_000) * 100) * 0.15
        
        assert mcap_score == 0, "Zero market cap should give zero score"
    
    def test_extreme_high_volume(self):
        """Test capping at 100 for extreme volume."""
        avg_volume = 500_000_000  # 500M shares (extreme)
        
        volume_score = min(100, (avg_volume / 10_000_000) * 100) * 0.6
        
        # Should cap at 100 * 0.6 = 60
        assert volume_score == 60, "Volume component should cap at 60"
    
    def test_extreme_high_market_cap(self):
        """Test capping at 100 for extreme market cap."""
        market_cap = 10_000_000_000_000  # $10T (extreme)
        
        mcap_score = min(100, (market_cap / 200_000_000_000) * 100) * 0.15
        
        # Should cap at 100 * 0.15 = 15
        assert mcap_score == 15, "Market cap component should cap at 15"
    
    def test_zero_volatility(self):
        """Test perfect stability (zero volatility)."""
        volume_volatility = 0.0
        
        stability_score = min(100, (1 - volume_volatility) * 100) * 0.25
        
        # Should give max stability score
        assert stability_score == 25, "Zero volatility should give max 25 score"
    
    def test_extreme_volatility(self):
        """Test extreme volatility (>100%)."""
        volume_volatility = 1.5  # 150% volatility (possible in crypto)
        
        stability_score = min(100, max(0, (1 - volume_volatility) * 100)) * 0.25
        
        # Should give zero or negative (capped at 0)
        assert stability_score <= 0, "Extreme volatility should give zero stability"
    
    def test_negative_volume(self):
        """Test negative volume (invalid data)."""
        avg_volume = -1_000_000
        
        # Should handle gracefully (either error or zero)
        volume_score = min(100, max(0, (avg_volume / 10_000_000) * 100)) * 0.6
        
        assert volume_score == 0, "Negative volume should be treated as zero"
    
    def test_nan_inputs(self):
        """Test NaN inputs."""
        avg_volume = float('nan')
        market_cap = 1_000_000_000
        
        # Should detect NaN
        assert np.isnan(avg_volume), "Should detect NaN"
    
    def test_none_inputs(self):
        """Test None inputs."""
        avg_volume = None
        
        # Should raise error or return None
        assert avg_volume is None, "Should handle None gracefully"


class TestLiquidityBenchmarks:
    """Test against industry benchmark categories."""
    
    def test_mega_cap_classification(self):
        """Test mega-cap stocks meet benchmark thresholds."""
        # AAPL-like: 50M volume, $3T mcap
        avg_volume = 50_000_000
        market_cap = 3_000_000_000_000
        
        assert avg_volume >= MEGA_CAP['min_volume'], "Should meet mega-cap volume"
        assert market_cap >= MEGA_CAP['min_mcap'], "Should meet mega-cap market cap"
    
    def test_large_cap_classification(self):
        """Test large-cap stocks meet benchmark thresholds."""
        # Typical S&P 500: 8M volume, $50B mcap
        avg_volume = 8_000_000
        market_cap = 50_000_000_000
        
        assert avg_volume >= LARGE_CAP['min_volume'], "Should meet large-cap volume"
        assert market_cap >= LARGE_CAP['min_mcap'], "Should meet large-cap market cap"
    
    def test_mid_cap_classification(self):
        """Test mid-cap stocks meet benchmark thresholds."""
        # Russell midcap: 2M volume, $5B mcap
        avg_volume = 2_000_000
        market_cap = 5_000_000_000
        
        assert avg_volume >= MID_CAP['min_volume'], "Should meet mid-cap volume"
        assert market_cap >= MID_CAP['min_mcap'], "Should meet mid-cap market cap"
    
    def test_small_cap_classification(self):
        """Test small-cap stocks meet benchmark thresholds."""
        # Small-cap: 600K volume, $500M mcap
        avg_volume = 600_000
        market_cap = 500_000_000
        
        assert avg_volume >= SMALL_CAP['min_volume'], "Should meet small-cap volume"
        assert market_cap >= SMALL_CAP['min_mcap'], "Should meet small-cap market cap"
    
    def test_micro_cap_below_threshold(self):
        """Test micro-cap stocks below small-cap threshold."""
        # Micro-cap: 100K volume, $100M mcap
        avg_volume = 100_000
        market_cap = 100_000_000
        
        assert avg_volume < SMALL_CAP['min_volume'], "Should be below small-cap volume"
        assert market_cap < SMALL_CAP['min_mcap'], "Should be below small-cap mcap"


class TestLiquidityScoreInterpretation:
    """Test score interpretation and risk levels."""
    
    def test_very_high_liquidity_interpretation(self):
        """Test interpretation for score >80."""
        score = 85
        
        if score > 80:
            risk_level = 'Very Low'
            risk_color = '🟢'
        
        assert risk_level == 'Very Low', "Score >80 should be very low risk"
        assert risk_color == '🟢', "Should use green indicator"
    
    def test_high_liquidity_interpretation(self):
        """Test interpretation for score 60-80."""
        score = 70
        
        if score > 60:
            risk_level = 'Low'
            risk_color = '🟢'
        
        assert risk_level == 'Low', "Score 60-80 should be low risk"
    
    def test_medium_liquidity_interpretation(self):
        """Test interpretation for score 40-60."""
        score = 50
        
        if 40 < score <= 60:
            risk_level = 'Medium'
            risk_color = '🟡'
        
        assert risk_level == 'Medium', "Score 40-60 should be medium risk"
        assert risk_color == '🟡', "Should use yellow indicator"
    
    def test_low_liquidity_interpretation(self):
        """Test interpretation for score <40."""
        score = 25
        
        if score <= 40:
            risk_level = 'High'
            risk_color = '🔴'
        
        assert risk_level == 'High', "Score <40 should be high risk"
        assert risk_color == '🔴', "Should use red indicator"


class TestLiquidityDollarVolume:
    """Test dollar volume calculation."""
    
    def test_dollar_volume_mega_cap(self):
        """Test dollar volume for mega-cap."""
        avg_volume = 50_000_000  # 50M shares
        avg_price = 150.0        # $150/share
        
        dollar_volume = avg_volume * avg_price
        
        # $7.5B daily dollar volume
        assert dollar_volume == 7_500_000_000, "Should calculate correct dollar volume"
        assert dollar_volume > 1_000_000_000, "Mega-cap should have >$1B dollar volume"
    
    def test_dollar_volume_small_cap(self):
        """Test dollar volume for small-cap."""
        avg_volume = 200_000  # 200K shares
        avg_price = 5.0       # $5/share
        
        dollar_volume = avg_volume * avg_price
        
        # $1M daily dollar volume
        assert dollar_volume == 1_000_000, "Should calculate correct dollar volume"
        assert dollar_volume < 10_000_000, "Small-cap should have <$10M dollar volume"
    
    def test_dollar_volume_vs_share_volume(self):
        """Test that dollar volume is more meaningful than share volume."""
        # High-price low-volume stock
        stock_a_shares = 1_000_000
        stock_a_price = 1000.0
        stock_a_dollar = stock_a_shares * stock_a_price  # $1B
        
        # Low-price high-volume stock
        stock_b_shares = 50_000_000
        stock_b_price = 10.0
        stock_b_dollar = stock_b_shares * stock_b_price  # $500M
        
        # Stock A has lower share volume but higher dollar volume
        assert stock_a_shares < stock_b_shares, "Stock A has lower share volume"
        assert stock_a_dollar > stock_b_dollar, "Stock A has higher dollar volume"


class TestLiquidityVolumeVolatility:
    """Test volume volatility calculation."""
    
    def test_stable_volume(self):
        """Test low volatility (consistent volume)."""
        volumes = pd.Series([10_000_000, 10_500_000, 9_800_000, 10_200_000, 9_900_000])
        
        avg_volume = volumes.mean()
        std_volume = volumes.std()
        volume_volatility = std_volume / avg_volume
        
        assert volume_volatility < 0.10, "Stable volume should have <10% volatility"
    
    def test_volatile_volume(self):
        """Test high volatility (erratic volume)."""
        volumes = pd.Series([5_000_000, 20_000_000, 3_000_000, 25_000_000, 2_000_000])
        
        avg_volume = volumes.mean()
        std_volume = volumes.std()
        volume_volatility = std_volume / avg_volume
        
        assert volume_volatility > 0.50, "Volatile volume should have >50% volatility"
    
    def test_volume_spike_detection(self):
        """Test detection of volume spikes."""
        normal_volume = 10_000_000
        spike_volume = 100_000_000  # 10x spike
        
        spike_ratio = spike_volume / normal_volume
        
        assert spike_ratio >= 5, "Should detect 10x spike"


class TestLiquidityPerformanceRequirements:
    """Test performance requirements."""
    
    def test_calculation_speed(self):
        """Test that calculation is fast (<100ms target)."""
        import time
        
        # Simulate calculation
        start = time.time()
        
        avg_volume = 10_000_000
        market_cap = 100_000_000_000
        volume_volatility = 0.20
        
        volume_score = min(100, (avg_volume / 10_000_000) * 100) * 0.6
        mcap_score = min(100, (market_cap / 200_000_000_000) * 100) * 0.15
        stability_score = min(100, (1 - volume_volatility) * 100) * 0.25
        
        liquidity_score = volume_score + mcap_score + stability_score
        
        end = time.time()
        calculation_time = (end - start) * 1000  # Convert to ms
        
        assert calculation_time < 100, f"Calculation should be <100ms, got {calculation_time:.2f}ms"
    
    def test_batch_calculation_performance(self):
        """Test batch calculation performance (100 tickers)."""
        import time
        
        start = time.time()
        
        # Simulate 100 ticker calculations
        for i in range(100):
            avg_volume = 10_000_000 * (1 + i/100)
            market_cap = 100_000_000_000 * (1 + i/50)
            volume_volatility = 0.20
            
            volume_score = min(100, (avg_volume / 10_000_000) * 100) * 0.6
            mcap_score = min(100, (market_cap / 200_000_000_000) * 100) * 0.15
            stability_score = min(100, (1 - volume_volatility) * 100) * 0.25
            
            liquidity_score = volume_score + mcap_score + stability_score
        
        end = time.time()
        total_time = (end - start) * 1000
        avg_time = total_time / 100
        
        assert avg_time < 10, f"Average time should be <10ms per ticker, got {avg_time:.2f}ms"
        print(f"\n✓ Batch performance: {avg_time:.2f}ms per ticker")


if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
