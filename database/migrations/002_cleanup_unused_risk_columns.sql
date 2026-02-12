-- Cleanup Unused Risk Columns Migration
-- ========================================
-- Removes columns that will never be populated because RiskAnalyzer doesn't calculate them
-- This saves database space and eliminates confusion

-- ============================================================================
-- 1. LIQUIDITY_RISK_DATA - Remove bid_ask_spread_avg
-- ============================================================================
-- Reason: Requires Level 2 market data (order book) which we don't have access to
-- yfinance only provides OHLCV data, not bid-ask spreads

ALTER TABLE liquidity_risk_data 
DROP COLUMN IF EXISTS bid_ask_spread_avg;

COMMENT ON TABLE liquidity_risk_data IS 'Liquidity risk using Hasbrouck model (2009): 60% Volume + 15% Market Cap + 25% Volume Stability. Does not include bid-ask spread (requires L2 data).';

-- ============================================================================
-- 2. REGIME_RISK_DATA - Remove per-regime beta/correlation columns
-- ============================================================================
-- Reason: RiskAnalyzer calculates volatility per regime, not beta/correlation
-- These require regime-conditional covariance calculations not currently implemented

ALTER TABLE regime_risk_data 
DROP COLUMN IF EXISTS bull_beta,
DROP COLUMN IF EXISTS bull_correlation,
DROP COLUMN IF EXISTS bear_beta,
DROP COLUMN IF EXISTS bear_max_drawdown,
DROP COLUMN IF EXISTS correction_recovery_days;

COMMENT ON TABLE regime_risk_data IS 'Market regime risk analysis using 50/200 MA crossover + S&P drawdown detection. Provides volatility and Sharpe ratio per regime (bull/bear/volatile). Beta and correlation per regime not currently calculated.';

COMMENT ON COLUMN regime_risk_data.current_regime IS 'Stock behavior profile based on defensive_score: Defensive (>60) / Balanced (40-60) / Aggressive (<40)';
COMMENT ON COLUMN regime_risk_data.regime_confidence IS 'Data quality percentage based on historical coverage (0-100%)';
COMMENT ON COLUMN regime_risk_data.bull_volatility IS 'Annualized volatility during bull market periods';
COMMENT ON COLUMN regime_risk_data.bear_downside_capture IS 'Inverse of volatility ratio - lower is more defensive';
COMMENT ON COLUMN regime_risk_data.correction_volatility IS 'Annualized volatility during volatile/correction periods';

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- Columns removed:
-- - liquidity_risk_data.bid_ask_spread_avg (1 column)
-- - regime_risk_data: bull_beta, bull_correlation, bear_beta, bear_max_drawdown, correction_recovery_days (5 columns)
-- Total space saved: 6 columns across 2 tables
