-- Advanced Risk Factors Schema Migration
-- ========================================
-- Adds support for enhanced risk metrics including CVaR, liquidity risk, 
-- Altman Z-Score, and regime risk analysis

-- ============================================================================
-- 1. EXTEND EXISTING RISK_DATA TABLE
-- ============================================================================

-- Add enhanced tail risk metrics
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_95 NUMERIC(8, 4);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_99 NUMERIC(8, 4);

-- Add enhanced volatility metrics
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_30d_annual NUMERIC(8, 4);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_historical_annual NUMERIC(8, 4);

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_risk_cvar ON risk_data (stock_id, cvar_95);
CREATE INDEX IF NOT EXISTS idx_risk_volatility ON risk_data (stock_id, volatility_30d_annual);

-- ============================================================================
-- 2. LIQUIDITY RISK DATA TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS liquidity_risk_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Core Metrics
    liquidity_score NUMERIC(5, 2), -- 0-100 scale
    risk_level VARCHAR(10), -- Low/Medium/High/Extreme
    
    -- Component Analysis
    bid_ask_spread_avg NUMERIC(8, 6),
    trading_volume_consistency NUMERIC(8, 4),
    market_depth_score NUMERIC(8, 4),
    components JSONB, -- Detailed breakdown
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, date)
);

-- Liquidity Risk Indexes
CREATE INDEX IF NOT EXISTS idx_liquidity_stock_date ON liquidity_risk_data (stock_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_liquidity_score ON liquidity_risk_data (stock_id, liquidity_score);
CREATE INDEX IF NOT EXISTS idx_liquidity_risk_level ON liquidity_risk_data (risk_level);

-- ============================================================================
-- 3. ALTMAN Z-SCORE DATA TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS altman_zscore_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Core Z-Score 
    z_score NUMERIC(8, 4),
    risk_zone VARCHAR(20), -- Safe/Caution/Distress
    bankruptcy_risk NUMERIC(5, 2), -- Percentage
    data_quality VARCHAR(20), -- High/Medium/Low/Unknown
    
    -- Component Ratios
    working_capital_ratio NUMERIC(8, 4),
    retained_earnings_ratio NUMERIC(8, 4), 
    ebit_ratio NUMERIC(8, 4),
    market_value_ratio NUMERIC(8, 4),
    sales_ratio NUMERIC(8, 4),
    components JSONB, -- Full breakdown
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, date)
);

-- Altman Z-Score Indexes
CREATE INDEX IF NOT EXISTS idx_altman_stock_date ON altman_zscore_data (stock_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_altman_zscore ON altman_zscore_data (stock_id, z_score);
CREATE INDEX IF NOT EXISTS idx_altman_risk_zone ON altman_zscore_data (risk_zone);

-- ============================================================================
-- 4. REGIME RISK DATA TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS regime_risk_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Current Regime
    current_regime VARCHAR(20), -- Bull/Bear/Correction
    regime_confidence NUMERIC(5, 2), -- 0-100%
    
    -- Bull Market Behavior
    bull_beta NUMERIC(8, 4),
    bull_correlation NUMERIC(8, 4),
    bull_volatility NUMERIC(8, 4),
    
    -- Bear Market Behavior  
    bear_beta NUMERIC(8, 4),
    bear_downside_capture NUMERIC(8, 4),
    bear_max_drawdown NUMERIC(8, 4),
    
    -- Correction Behavior
    correction_recovery_days NUMERIC(8, 2),
    correction_volatility NUMERIC(8, 4),
    
    -- Full Analysis
    regime_analysis JSONB, -- Complete regime breakdown
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, date)
);

-- Regime Risk Indexes
CREATE INDEX IF NOT EXISTS idx_regime_stock_date ON regime_risk_data (stock_id, date DESC);  
CREATE INDEX IF NOT EXISTS idx_regime_current ON regime_risk_data (current_regime);
CREATE INDEX IF NOT EXISTS idx_regime_confidence ON regime_risk_data (regime_confidence);

-- ============================================================================
-- 5. UPDATE TRIGGERS
-- ============================================================================

-- Update timestamp trigger for liquidity_risk_data
CREATE OR REPLACE FUNCTION update_liquidity_risk_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_liquidity_risk_updated
BEFORE UPDATE ON liquidity_risk_data
FOR EACH ROW EXECUTE FUNCTION update_liquidity_risk_timestamp();

-- Update timestamp trigger for altman_zscore_data
CREATE OR REPLACE FUNCTION update_altman_zscore_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_altman_zscore_updated
BEFORE UPDATE ON altman_zscore_data
FOR EACH ROW EXECUTE FUNCTION update_altman_zscore_timestamp();

-- Update timestamp trigger for regime_risk_data
CREATE OR REPLACE FUNCTION update_regime_risk_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_regime_risk_updated
BEFORE UPDATE ON regime_risk_data
FOR EACH ROW EXECUTE FUNCTION update_regime_risk_timestamp();

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- This migration adds:
-- - 4 new columns to risk_data table
-- - 3 new advanced risk tables
-- - Appropriate indexes for performance
-- - Update triggers for data freshness
