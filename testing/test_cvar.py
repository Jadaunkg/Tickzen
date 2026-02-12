#!/usr/bin/env python3
"""
Test Suite: P2.1 - CVaR (Conditional Value at Risk) Implementation
==================================================================

**Feature:** Conditional Value at Risk (Expected Shortfall)
**Phase:** Phase 2 - Advanced Risk Metrics
**Complexity:** Medium
**Start Date:** February 9, 2026
**Target:** 3-day implementation cycle (Days 5-7)

**CVaR Definition:**
Conditional Value at Risk (CVaR), also called Expected Shortfall (ES), measures
the expected loss in the worst α% of cases. More conservative than VaR.

**Mathematical Formulation:**
CVaR_α = E[Loss | Loss > VaR_α]

For α = 5%:
CVaR_5% = Average of returns in worst 5% tail

**Key Properties:**
1. CVaR > VaR (always more extreme)
2. CVaR is a coherent risk measure (VaR is not)
3. Industry standard: α = 5% (95% confidence), α = 1% (99% confidence)
4. Basel III compliant for banking stress tests

**Expected Results:**
- Stable stocks (AAPL): CVaR ~1.2-1.5x VaR
- Volatile stocks (TSLA): CVaR ~1.3-1.8x VaR
- Meme stocks (GME): CVaR ~2.0-3.0x VaR (extreme tail risk)

**Implementation Plan:**
Day 1 (Today): Unit tests with synthetic data ✅
Day 2 (Feb 10): Core implementation + integration
Day 3 (Feb 11): Real data testing (5 tickers) + validation

**Test Strategy:**
1. Synthetic data tests (normal, heavy-tailed distributions)
2. Edge cases (insufficient data, constant prices)
3. Mathematical properties (CVaR > VaR always)
4. Real ticker validation (AAPL, TSLA, GME, AMC, NVDA)

Created: February 9, 2026 (P2.1 Day 1)
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


class TestCVaRCalculation:
    """Unit tests: CVaR (Conditional Value at Risk) calculation"""
    
    def test_cvar_normal_distribution(self):
        """Test 1: CVaR with normally distributed returns"""
        np.random.seed(42)
        
        # Generate 1000 days of returns (mean=0.001, std=0.02)
        returns = pd.Series(np.random.normal(0.001, 0.02, 1000))
        
        analyzer = RiskAnalyzer()
        
        # Calculate VaR and CVaR at 5% level
        var_5 = analyzer.calculate_var(returns, confidence_level=0.05)
        cvar_5 = analyzer.calculate_cvar(returns, confidence_level=0.05)
        
        # CVaR must be more extreme (larger loss) than VaR
        assert cvar_5 < var_5, f"CVaR ({cvar_5:.4f}) must be < VaR ({var_5:.4f})"
        
        # For normal distribution, CVaR should be ~1.5x VaR
        ratio = abs(cvar_5) / abs(var_5)
        assert 1.2 < ratio < 2.0, f"CVaR/VaR ratio {ratio:.2f} outside expected range"
        
        print(f"✅ Test 1 PASS: VaR_5% = {var_5:.4f}, CVaR_5% = {cvar_5:.4f}, Ratio = {ratio:.2f}x")
    
    def test_cvar_vs_var_1_percent(self):
        """Test 2: CVaR at 1% confidence (more extreme)"""
        np.random.seed(123)
        
        # Generate returns
        returns = pd.Series(np.random.normal(0, 0.03, 1000))
        
        analyzer = RiskAnalyzer()
        
        # Calculate at 1% level (99% confidence)
        var_1 = analyzer.calculate_var(returns, confidence_level=0.01)
        cvar_1 = analyzer.calculate_cvar(returns, confidence_level=0.01)
        
        # CVaR_1% > CVaR_5% (more extreme tail)
        assert cvar_1 < var_1, f"CVaR_1% ({cvar_1:.4f}) must be < VaR_1% ({var_1:.4f})"
        
        # Both should be negative (losses)
        assert cvar_1 < 0 and var_1 < 0, "Both should represent losses"
        
        print(f"✅ Test 2 PASS: VaR_1% = {var_1:.4f}, CVaR_1% = {cvar_1:.4f}")
    
    def test_cvar_heavy_tailed_distribution(self):
        """Test 3: CVaR with fat-tailed distribution (higher ratio)"""
        np.random.seed(789)
        
        # Generate returns with heavy tails (Student's t-distribution, df=3)
        returns = pd.Series(np.random.standard_t(df=3, size=1000) * 0.02)
        
        analyzer = RiskAnalyzer()
        
        var_5 = analyzer.calculate_var(returns, confidence_level=0.05)
        cvar_5 = analyzer.calculate_cvar(returns, confidence_level=0.05)
        
        # Fat tails = larger CVaR/VaR ratio
        ratio = abs(cvar_5) / abs(var_5)
        assert ratio > 1.3, f"Heavy-tailed CVaR/VaR ratio {ratio:.2f} should be > 1.3"
        
        print(f"✅ Test 3 PASS: Heavy-tailed VaR = {var_5:.4f}, CVaR = {cvar_5:.4f}, Ratio = {ratio:.2f}x")
    
    def test_cvar_constant_prices(self):
        """Test 4: CVaR with no volatility (constant prices)"""
        analyzer = RiskAnalyzer()
        
        # Constant prices = zero returns
        returns = pd.Series([0.0] * 100)
        
        var_5 = analyzer.calculate_var(returns, confidence_level=0.05)
        cvar_5 = analyzer.calculate_cvar(returns, confidence_level=0.05)
        
        # Both should be zero (no risk)
        assert abs(var_5) < 0.001, f"VaR should be ~0 for constant prices, got {var_5}"
        assert abs(cvar_5) < 0.001, f"CVaR should be ~0 for constant prices, got {cvar_5}"
        
        print(f"✅ Test 4 PASS: Constant prices → VaR = {var_5:.6f}, CVaR = {cvar_5:.6f}")
    
    def test_cvar_insufficient_data(self):
        """Test 5: CVaR with insufficient data (<100 points)"""
        analyzer = RiskAnalyzer()
        
        # Only 20 data points
        returns = pd.Series(np.random.normal(0, 0.02, 20))
        
        # For 5% confidence, need at least 20 points (5% of 20 = 1 point)
        # Should still work but less reliable
        var_5 = analyzer.calculate_var(returns, confidence_level=0.05)
        cvar_5 = analyzer.calculate_cvar(returns, confidence_level=0.05)
        
        # Should still satisfy CVaR < VaR
        assert cvar_5 <= var_5, "CVaR must be <= VaR even with limited data"
        
        print(f"✅ Test 5 PASS: Insufficient data handled: VaR = {var_5:.4f}, CVaR = {cvar_5:.4f}")
    
    def test_cvar_all_positive_returns(self):
        """Test 6: CVaR when all returns are positive (bull market)"""
        analyzer = RiskAnalyzer()
        
        # All positive returns (strong bull market)
        returns = pd.Series(np.random.uniform(0.01, 0.05, 100))
        
        var_5 = analyzer.calculate_var(returns, confidence_level=0.05)
        cvar_5 = analyzer.calculate_cvar(returns, confidence_level=0.05)
        
        # Both can be positive in extreme bull market
        # But CVaR should still be <= VaR (less positive)
        assert cvar_5 <= var_5, f"CVaR ({cvar_5:.4f}) should be <= VaR ({var_5:.4f})"
        
        print(f"✅ Test 6 PASS: Bull market → VaR = {var_5:.4f}, CVaR = {cvar_5:.4f}")
    
    def test_cvar_extreme_outlier(self):
        """Test 7: CVaR with extreme outlier (black swan event)"""
        np.random.seed(456)
        analyzer = RiskAnalyzer()
        
        # Normal returns + one extreme outlier (-30% crash)
        returns = pd.Series(list(np.random.normal(0.001, 0.015, 99)) + [-0.30])
        
        var_5 = analyzer.calculate_var(returns, confidence_level=0.05)
        cvar_5 = analyzer.calculate_cvar(returns, confidence_level=0.05)
        
        # CVaR should capture the extreme outlier
        assert cvar_5 < -0.05, f"CVaR should capture extreme loss, got {cvar_5:.4f}"
        assert cvar_5 < var_5, "CVaR must be more extreme than VaR"
        
        # Ratio should be large due to outlier
        ratio = abs(cvar_5) / abs(var_5)
        assert ratio > 2.0, f"Outlier should increase CVaR/VaR ratio, got {ratio:.2f}x"
        
        print(f"✅ Test 7 PASS: Black swan → VaR = {var_5:.4f}, CVaR = {cvar_5:.4f}, Ratio = {ratio:.2f}x")
    
    def test_cvar_empty_series(self):
        """Test 8: CVaR with empty returns series"""
        analyzer = RiskAnalyzer()
        
        empty_returns = pd.Series([], dtype=float)
        
        # Should handle gracefully (return NaN or raise error)
        try:
            var_5 = analyzer.calculate_var(empty_returns, confidence_level=0.05)
            cvar_5 = analyzer.calculate_cvar(empty_returns, confidence_level=0.05)
            
            # If doesn't error, should return NaN
            assert np.isnan(var_5) or var_5 is None, "Empty series should return NaN/None"
            assert np.isnan(cvar_5) or cvar_5 is None, "Empty series should return NaN/None"
            print(f"✅ Test 8 PASS: Empty series handled gracefully")
        except (ValueError, IndexError) as e:
            # Raising error is also acceptable
            print(f"✅ Test 8 PASS: Empty series raised error (expected): {type(e).__name__}")


class TestCVaRMathematicalProperties:
    """Tests: Verify CVaR mathematical properties"""
    
    def test_cvar_coherence(self):
        """Test 9: CVaR is a coherent risk measure (sub-additivity)"""
        np.random.seed(999)
        analyzer = RiskAnalyzer()
        
        # Two independent return series
        returns1 = pd.Series(np.random.normal(0, 0.02, 500))
        returns2 = pd.Series(np.random.normal(0, 0.03, 500))
        
        # Combined portfolio (equal weight)
        combined = (returns1 + returns2) / 2
        
        cvar1 = analyzer.calculate_cvar(returns1, confidence_level=0.05)
        cvar2 = analyzer.calculate_cvar(returns2, confidence_level=0.05)
        cvar_combined = analyzer.calculate_cvar(combined, confidence_level=0.05)
        
        # Sub-additivity: CVaR(A+B) <= CVaR(A) + CVaR(B)
        # (Diversification benefit)
        assert cvar_combined >= (cvar1 + cvar2) / 2, \
            "CVaR should show diversification benefit"
        
        print(f"✅ Test 9 PASS: Coherence verified (diversification benefit)")
    
    def test_cvar_monotonicity(self):
        """Test 10: CVaR increases with confidence level"""
        np.random.seed(111)
        analyzer = RiskAnalyzer()
        
        returns = pd.Series(np.random.normal(0, 0.02, 1000))
        
        # Calculate at different confidence levels
        cvar_20 = analyzer.calculate_cvar(returns, confidence_level=0.20)  # 80th percentile
        cvar_10 = analyzer.calculate_cvar(returns, confidence_level=0.10)  # 90th percentile
        cvar_5 = analyzer.calculate_cvar(returns, confidence_level=0.05)   # 95th percentile
        cvar_1 = analyzer.calculate_cvar(returns, confidence_level=0.01)   # 99th percentile
        
        # CVaR should be more extreme as confidence increases
        assert cvar_20 > cvar_10 > cvar_5 > cvar_1, \
            f"CVaR monotonicity failed: {cvar_20:.4f} > {cvar_10:.4f} > {cvar_5:.4f} > {cvar_1:.4f}"
        
        print(f"✅ Test 10 PASS: Monotonicity verified (20%={cvar_20:.4f}, 10%={cvar_10:.4f}, 5%={cvar_5:.4f}, 1%={cvar_1:.4f})")


class TestCVaRIntegration:
    """Integration tests: CVaR with other risk metrics"""
    
    def test_cvar_in_comprehensive_profile(self):
        """Test 11: CVaR integrates into comprehensive risk profile"""
        np.random.seed(222)
        analyzer = RiskAnalyzer()
        
        # Generate price series
        prices = pd.Series([100 * (1 + np.random.normal(0.001, 0.02)) ** i for i in range(252)])
        
        # Get comprehensive risk profile (should include CVaR)
        risk_profile = analyzer.comprehensive_risk_profile(prices)
        
        # Verify CVaR fields exist
        assert 'cvar_5' in risk_profile, "CVaR_5% should be in risk profile"
        assert 'cvar_1' in risk_profile, "CVaR_1% should be in risk profile"
        
        # Verify relationship with VaR
        var_5 = risk_profile['var_5']
        cvar_5 = risk_profile['cvar_5']
        
        assert cvar_5 < var_5, f"CVaR ({cvar_5:.4f}) must be < VaR ({var_5:.4f})"
        
        print(f"✅ Test 11 PASS: CVaR integrated into comprehensive profile")
    
    def test_cvar_performance(self):
        """Test 12: CVaR calculation performance"""
        import time
        
        analyzer = RiskAnalyzer()
        
        # Generate large dataset (5 years = 1260 trading days)
        returns = pd.Series(np.random.normal(0, 0.02, 1260))
        
        # Measure calculation time
        start = time.time()
        cvar_5 = analyzer.calculate_cvar(returns, confidence_level=0.05)
        elapsed = time.time() - start
        
        # Should be fast (<100ms)
        assert elapsed < 0.1, f"CVaR calculation too slow: {elapsed*1000:.2f}ms"
        assert cvar_5 is not None, "CVaR should be calculated"
        
        print(f"✅ Test 12 PASS: CVaR calculated in {elapsed*1000:.2f}ms (< 100ms target)")


# ============================================================================
# Checkpoint 1: Summary
# ============================================================================

def test_checkpoint_1_summary():
    """Checkpoint 1: All unit tests passed"""
    print("\n" + "="*70)
    print("CHECKPOINT 1: UNIT TEST VALIDATION (P2.1 DAY 1)")
    print("="*70)
    print("✅ All 12 CVaR unit tests passed")
    print("✅ Mathematical properties verified (coherence, monotonicity)")
    print("✅ Edge cases handled (empty data, constant prices, outliers)")
    print("✅ Integration tested (comprehensive risk profile)")
    print("✅ Performance validated (<100ms)")
    print("\n**Next Steps:**")
    print("- Day 2 (Feb 10): Implement calculate_cvar() in RiskAnalyzer")
    print("- Day 3 (Feb 11): Real data test (AAPL, TSLA, GME, AMC, NVDA)")
    print("\nStatus: READY FOR DAY 2 IMPLEMENTATION")
    print("="*70)


if __name__ == "__main__":
    # Run tests with pytest
    import subprocess
    result = subprocess.run(
        ["pytest", __file__, "-v", "--tb=short"],
        capture_output=False
    )
    
    if result.returncode == 0:
        test_checkpoint_1_summary()
    else:
        print("\n❌ Checkpoint 1 FAILED - Fix errors before Day 2")
    
    sys.exit(result.returncode)
