-- ============================================================================
-- RISK METADATA ENHANCEMENT MIGRATION
-- ============================================================================
-- Migration: Add 64 metadata columns to risk_data table
-- Date: February 11, 2026
-- Purpose: Enhance risk metrics with comprehensive metadata for transparency
--
-- EXECUTION INSTRUCTIONS:
-- 1. Open Supabase Dashboard → SQL Editor
-- 2. Copy and paste this entire script
-- 3. Click "Run" to execute
-- 4. Verify completion (should show "Success" with no errors)
-- 5. Run verification query at bottom to confirm all columns added
-- ============================================================================

BEGIN;

-- ============================================================================
-- GROUP 1: VaR METADATA (10 columns)
-- ============================================================================

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_95_data_period_days INTEGER;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_95_sample_size INTEGER;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_95_calculation_method VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_95_confidence_level NUMERIC(5, 4);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_95_return_frequency VARCHAR(50);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_99_data_period_days INTEGER;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_99_sample_size INTEGER;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_99_calculation_method VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_99_confidence_level NUMERIC(5, 4);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_99_return_frequency VARCHAR(50);

-- ============================================================================
-- GROUP 2: CVaR METADATA (8 columns)
-- ============================================================================

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_95_data_period_days INTEGER;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_95_tail_size INTEGER;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_95_calculation_method VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_95_confidence_level NUMERIC(5, 4);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_99_data_period_days INTEGER;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_99_tail_size INTEGER;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_99_calculation_method VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS cvar_99_confidence_level NUMERIC(5, 4);

-- ============================================================================
-- GROUP 3: VOLATILITY METADATA (12 columns)
-- ============================================================================

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_30d_sample_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_30d_calculation_method VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_30d_annualization_factor NUMERIC(10, 4);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_30d_return_frequency VARCHAR(50);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_30d_model_type VARCHAR(50);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_30d_fallback_logic VARCHAR(255);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_historical_sample_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_historical_calculation_method VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_historical_annualization_factor NUMERIC(10, 4);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_historical_return_frequency VARCHAR(50);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_historical_model_type VARCHAR(50);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_trading_days_annual INTEGER DEFAULT 252;

-- ============================================================================
-- GROUP 4: LIQUIDITY METADATA (13 columns)
-- ============================================================================

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_calculation_method VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_data_period_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_actual_sample_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_volume_weight NUMERIC(5, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_volume_benchmark BIGINT;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_mcap_weight NUMERIC(5, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_mcap_benchmark BIGINT;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_stability_weight NUMERIC(5, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_stability_metric VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_data_freshness VARCHAR(50);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_minimum_required_days INTEGER DEFAULT 30;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_sufficient_data BOOLEAN;

-- ============================================================================
-- GROUP 5: ALTMAN Z-SCORE METADATA (16 columns)
-- ============================================================================

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_calculation_method VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_financial_period VARCHAR(20);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_financial_period_end_date DATE;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_financial_data_source VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_data_age_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_filing_type VARCHAR(20);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_required_fields_count INTEGER DEFAULT 6;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_available_fields_count INTEGER;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_data_completeness_percent NUMERIC(5, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_minimum_completeness_percent NUMERIC(5, 2) DEFAULT 67.0;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_retained_earnings_imputed BOOLEAN DEFAULT FALSE;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_imputation_method VARCHAR(255);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_next_update_expected DATE;

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_coefficient_a NUMERIC(8, 4) DEFAULT 1.2;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_coefficient_b NUMERIC(8, 4) DEFAULT 1.4;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_coefficient_c NUMERIC(8, 4) DEFAULT 3.3;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_coefficient_d NUMERIC(8, 4) DEFAULT 0.6;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_coefficient_e NUMERIC(8, 4) DEFAULT 1.0;

-- ============================================================================
-- GROUP 6: SHARPE & SORTINO METADATA (10 columns)
-- ============================================================================

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sharpe_ratio_calculation_method VARCHAR(255);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sharpe_ratio_data_period_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sharpe_ratio_risk_free_rate_used NUMERIC(8, 6);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sharpe_ratio_risk_free_rate_source VARCHAR(100);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sharpe_ratio_annualization_factor NUMERIC(10, 4) DEFAULT 15.8745;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sharpe_ratio_daily_rf_rate NUMERIC(8, 8);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sortino_ratio_calculation_method VARCHAR(255);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sortino_ratio_data_period_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sortino_ratio_annualization_factor NUMERIC(10, 4) DEFAULT 15.8745;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sortino_ratio_downside_focus VARCHAR(100);

-- ============================================================================
-- GROUP 7: OTHER METRICS METADATA (15 columns)
-- ============================================================================

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS max_drawdown_calculation_method VARCHAR(255);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS max_drawdown_data_period_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS max_drawdown_definition VARCHAR(255);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS beta_calculation_method VARCHAR(255);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS beta_data_period_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS beta_market_benchmark VARCHAR(50);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS beta_return_frequency VARCHAR(50);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS correlation_calculation_method VARCHAR(255);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS correlation_data_period_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS correlation_market_benchmark VARCHAR(50);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS skewness_calculation_method VARCHAR(255);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS skewness_data_period_days NUMERIC(8, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS skewness_interpretation VARCHAR(255);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS kurtosis_calculation_method VARCHAR(255);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS kurtosis_data_period_days NUMERIC(8, 2);

-- ============================================================================
-- GROUP 8: CONFIDENCE & QUALITY SCORES (11 columns)
-- ============================================================================

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS var_estimation_confidence NUMERIC(5, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS volatility_estimation_confidence NUMERIC(5, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS liquidity_estimation_confidence NUMERIC(5, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS altman_estimation_confidence NUMERIC(5, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS sharpe_estimation_confidence NUMERIC(5, 2);
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS overall_profile_confidence NUMERIC(5, 2);

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS has_data_gaps BOOLEAN DEFAULT FALSE;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS missing_price_data BOOLEAN DEFAULT FALSE;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS missing_financial_data BOOLEAN DEFAULT FALSE;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS insufficient_liquidity_data BOOLEAN DEFAULT FALSE;

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS data_quality_score NUMERIC(5, 2);

-- ============================================================================
-- GROUP 9: TRACKING FIELDS (3 columns)
-- ============================================================================

ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS metadata_calculation_timestamp TIMESTAMP;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS metadata_version INTEGER DEFAULT 1;
ALTER TABLE risk_data ADD COLUMN IF NOT EXISTS risk_profile_calculation_method VARCHAR(100);

-- ============================================================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Index for querying by confidence scores
CREATE INDEX IF NOT EXISTS idx_risk_var_confidence 
ON risk_data(stock_id, var_estimation_confidence DESC);

CREATE INDEX IF NOT EXISTS idx_risk_overall_confidence 
ON risk_data(stock_id, overall_profile_confidence DESC);

-- Index for querying by data quality
CREATE INDEX IF NOT EXISTS idx_risk_data_quality 
ON risk_data(stock_id, data_quality_score DESC);

-- Index for querying by Altman data freshness
CREATE INDEX IF NOT EXISTS idx_risk_altman_age 
ON risk_data(stock_id, altman_data_age_days ASC);

-- Index for metadata timestamp
CREATE INDEX IF NOT EXISTS idx_risk_metadata_timestamp 
ON risk_data(stock_id, metadata_calculation_timestamp DESC);

COMMIT;

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================
-- Run this after migration to verify all columns were added successfully

SELECT 
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'risk_data'
AND column_name LIKE '%var_%'
   OR column_name LIKE '%cvar_%'
   OR column_name LIKE '%volatility_%'
   OR column_name LIKE '%liquidity_%'
   OR column_name LIKE '%altman_%'
   OR column_name LIKE '%sharpe_%'
   OR column_name LIKE '%sortino_%'
   OR column_name LIKE '%beta_%'
   OR column_name LIKE '%confidence%'
   OR column_name LIKE '%metadata_%'
ORDER BY ordinal_position;

-- Expected: 64+ rows (64 new columns + original columns with matching patterns)
-- If you see fewer, check for errors in the migration execution

-- ============================================================================
-- COLUMN COUNT VERIFICATION
-- ============================================================================

SELECT COUNT(*) as total_columns
FROM information_schema.columns
WHERE table_name = 'risk_data';

-- Expected: ~83 columns (19 original + 64 new = 83 total)

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✓ Migration Complete: Added 64 metadata columns to risk_data table';
    RAISE NOTICE '✓ Created 5 performance indexes';
    RAISE NOTICE '→ Next Step: Update RiskAnalyzer Python code to populate metadata';
END $$;
