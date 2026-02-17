-- ============================================================================
-- TICKZEN2 COMPLETE DATABASE SCHEMA
-- ============================================================================
-- Generated: 2026-02-16 10:00:00
-- Database: Supabase PostgreSQL
-- Purpose: Complete schema for database replication
-- Status: Complete with stock_news_data table and all associated configurations
--
-- Usage:
--   1. Create new Supabase project
--   2. Go to SQL Editor
--   3. Run this entire script
--   4. Database structure will be recreated
-- ============================================================================

-- TABLE SUMMARY
-- ============================================================================
-- altman_zscore_data            :  15 columns
-- analyst_data                  :  10 columns
-- daily_price_data              :  13 columns
-- data_sync_log                 :  15 columns
-- dividend_data                 :  16 columns
-- forecast_data                 :   9 columns
-- fundamental_data              :  44 columns
-- insider_transactions          :  10 columns
-- liquidity_risk_data           :  10 columns
-- market_price_snapshot         :  27 columns
-- ownership_data                :  12 columns
-- peer_comparison_data          :  17 columns
-- regime_risk_data              :  11 columns
-- risk_data                     :  83 columns (19 base + 64 metadata)
-- sentiment_data                :   9 columns
-- stock_news_data               :  14 columns
-- stocks                        :  25 columns
-- technical_indicators          :  29 columns
-- ============================================================================

-- DETAILED COLUMN LISTING
-- ============================================================================

-- ALTMAN_ZSCORE_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • date
--   • z_score
--   • risk_zone
--   • bankruptcy_risk
--   • data_quality
--   • working_capital_ratio
--   • retained_earnings_ratio
--   • ebit_ratio
--   • market_value_ratio
--   • sales_ratio
--   • components
--   • created_at
--   • updated_at

-- ANALYST_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • target_price_mean
--   • target_price_median
--   • target_price_high
--   • target_price_low
--   • analyst_rating
--   • analyst_count
--   • next_earnings_date
--   • updated_at

-- DAILY_PRICE_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • date
--   • open_price
--   • high_price
--   • low_price
--   • close_price
--   • adjusted_close
--   • volume
--   • daily_return_pct
--   • price_change
--   • created_at
--   • updated_at

-- DATA_SYNC_LOG
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • sync_type
--   • sync_date
--   • records_inserted
--   • records_updated
--   • records_deleted
--   • records_failed
--   • sync_status
--   • error_message
--   • sync_duration_seconds
--   • data_quality_score
--   • source_api
--   • api_version
--   • created_at

-- DIVIDEND_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • dividend_rate
--   • dividend_yield_pct
--   • payout_ratio
--   • avg_dividend_yield_5y
--   • dividend_forward_rate
--   • dividend_forward_yield
--   • dividend_trailing_rate
--   • dividend_trailing_yield
--   • ex_dividend_date
--   • payment_date
--   • last_split_date
--   • last_split_factor
--   • created_at
--   • updated_at

-- FORECAST_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • forecast_date
--   • forecast_price_1y
--   • forecast_avg_price
--   • forecast_range_width
--   • forecast_period
--   • created_at
--   • updated_at

-- FUNDAMENTAL_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • period_date
--   • period_type
--   • pe_ratio
--   • pe_forward
--   • price_to_sales
--   • price_to_book
--   • ev_to_revenue
--   • ev_to_ebitda
--   • price_to_fcf
--   • net_margin
--   • operating_margin
--   • gross_margin
--   • ebitda_margin
--   • roe
--   • roa
--   • debt_to_equity
--   • total_cash
--   • total_debt
--   • free_cash_flow
--   • operating_cash_flow
--   • current_ratio
--   • quick_ratio
--   • revenue_ttm
--   • revenue_growth_yoy
--   • net_income_ttm
--   • earnings_growth_yoy
--   • ebitda_ttm
--   • gross_profit_ttm
--   • created_at
--   • updated_at
--   • peg_ratio
--   • roic
--   • asset_turnover
--   • inventory_turnover
--   • receivables_turnover
--   • working_capital_turnover
--   • dso
--   • dio
--   • ccc
--   • operating_income
--   • eps_basic
--   • eps_diluted

-- INSIDER_TRANSACTIONS
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • insider_name
--   • relation_to_company
--   • transaction_date
--   • shares_change
--   • transaction_price
--   • estimated_value
--   • created_at
--   • updated_at

-- LIQUIDITY_RISK_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • date
--   • liquidity_score
--   • risk_level
--   • trading_volume_consistency
--   • market_depth_score
--   • components
--   • created_at
--   • updated_at

-- MARKET_PRICE_SNAPSHOT
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • date
--   • current_price
--   • price_change
--   • change_pct
--   • change_15d_pct
--   • change_52w_pct
--   • performance_1y_pct
--   • overall_pct_change
--   • high_52w
--   • low_52w
--   • market_cap
--   • enterprise_value
--   • shares_outstanding
--   • float_shares
--   • sp500_index
--   • interest_rate
--   • created_at
--   • updated_at
--   • from_52wk_high_pct
--   • from_52wk_low_pct
--   • pe_ratio
--   • pb_ratio
--   • day_trend
--   • momentum_score
--   • price_alert_flags

-- OWNERSHIP_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • report_date
--   • insider_ownership_pct
--   • institutional_ownership_pct
--   • shares_short
--   • short_ratio_days
--   • short_pct_float
--   • shares_short_prev
--   • shares_outstanding_diluted
--   • created_at
--   • updated_at

-- PEER_COMPARISON_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • peer_ticker
--   • peer_name
--   • is_target
--   • market_cap
--   • pe_ratio
--   • revenue_growth
--   • net_margin
--   • eps
--   • roe
--   • debt_to_equity
--   • dividend_yield
--   • week_52_high
--   • week_52_low
--   • created_at
--   • updated_at

-- REGIME_RISK_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • date
--   • current_regime
--   • regime_confidence
--   • bull_volatility
--   • bear_downside_capture
--   • correction_volatility
--   • regime_analysis
--   • created_at
--   • updated_at

-- RISK_DATA
-- ----------------------------------------------------------------------------
-- Base Columns (19):
--   • id
--   • stock_id
--   • date
--   • var_95
--   • var_99
--   • cvar_95
--   • cvar_99
--   • sharpe_ratio
--   • sortino_ratio
--   • calmar_ratio
--   • max_drawdown
--   • beta
--   • market_correlation
--   • volatility_30d_annual
--   • volatility_historical_annual
--   • skewness
--   • kurtosis
--   • created_at
--   • updated_at
--
-- VaR Metadata (10):
--   • var_95_data_period_days
--   • var_95_sample_size
--   • var_95_calculation_method
--   • var_95_confidence_level
--   • var_95_return_frequency
--   • var_99_data_period_days
--   • var_99_sample_size
--   • var_99_calculation_method
--   • var_99_confidence_level
--   • var_99_return_frequency
--
-- CVaR Metadata (8):
--   • cvar_95_data_period_days
--   • cvar_95_tail_size
--   • cvar_95_calculation_method
--   • cvar_95_confidence_level
--   • cvar_99_data_period_days
--   • cvar_99_tail_size
--   • cvar_99_calculation_method
--   • cvar_99_confidence_level
--
-- Volatility Metadata (12):
--   • volatility_30d_sample_days
--   • volatility_30d_calculation_method
--   • volatility_30d_annualization_factor
--   • volatility_30d_return_frequency
--   • volatility_30d_model_type
--   • volatility_30d_fallback_logic
--   • volatility_historical_sample_days
--   • volatility_historical_calculation_method
--   • volatility_historical_annualization_factor
--   • volatility_historical_return_frequency
--   • volatility_historical_model_type
--   • volatility_trading_days_annual
--
-- Liquidity Metadata (13):
--   • liquidity_calculation_method
--   • liquidity_data_period_days
--   • liquidity_actual_sample_days
--   • liquidity_volume_weight
--   • liquidity_volume_benchmark
--   • liquidity_mcap_weight
--   • liquidity_mcap_benchmark
--   • liquidity_stability_weight
--   • liquidity_stability_metric
--   • liquidity_data_freshness
--   • liquidity_minimum_required_days
--   • liquidity_sufficient_data
--   • liquidity_mcap_benchmark
--
-- Altman Z-Score Metadata (18):
--   • altman_calculation_method
--   • altman_financial_period
--   • altman_financial_period_end_date
--   • altman_financial_data_source
--   • altman_data_age_days
--   • altman_filing_type
--   • altman_required_fields_count
--   • altman_available_fields_count
--   • altman_data_completeness_percent
--   • altman_minimum_completeness_percent
--   • altman_retained_earnings_imputed
--   • altman_imputation_method
--   • altman_next_update_expected
--   • altman_coefficient_a
--   • altman_coefficient_b
--   • altman_coefficient_c
--   • altman_coefficient_d
--   • altman_coefficient_e
--
-- Sharpe & Sortino Metadata (10):
--   • sharpe_ratio_calculation_method
--   • sharpe_ratio_data_period_days
--   • sharpe_ratio_risk_free_rate_used
--   • sharpe_ratio_risk_free_rate_source
--   • sharpe_ratio_annualization_factor
--   • sharpe_ratio_daily_rf_rate
--   • sortino_ratio_calculation_method
--   • sortino_ratio_data_period_days
--   • sortino_ratio_annualization_factor
--   • sortino_ratio_downside_focus
--
-- Other Metrics Metadata (15):
--   • max_drawdown_calculation_method
--   • max_drawdown_data_period_days
--   • max_drawdown_definition
--   • beta_calculation_method
--   • beta_data_period_days
--   • beta_market_benchmark
--   • beta_return_frequency
--   • correlation_calculation_method
--   • correlation_data_period_days
--   • correlation_market_benchmark
--   • skewness_calculation_method
--   • skewness_data_period_days
--   • skewness_interpretation
--   • kurtosis_calculation_method
--   • kurtosis_data_period_days
--
-- Confidence & Quality Scores (11):
--   • var_estimation_confidence
--   • volatility_estimation_confidence
--   • liquidity_estimation_confidence
--   • altman_estimation_confidence
--   • sharpe_estimation_confidence
--   • overall_profile_confidence
--   • has_data_gaps
--   • missing_price_data
--   • missing_financial_data
--   • insufficient_liquidity_data
--   • data_quality_score
--
-- Tracking Fields (3):
--   • metadata_calculation_timestamp
--   • metadata_version
--   • risk_profile_calculation_method

-- SENTIMENT_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • date
--   • sentiment_score
--   • sentiment_label
--   • sentiment_confidence
--   • analyst_sentiment
--   • created_at
--   • updated_at

-- STOCK_NEWS_DATA
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • title
--   • summary
--   • url
--   • publisher
--   • published_date
--   • sentiment_score
--   • sentiment_label
--   • relevance_score
--   • category
--   • source_api
--   • created_at
--   • updated_at

-- STOCKS
-- ----------------------------------------------------------------------------
--   • id
--   • symbol
--   • ticker
--   • company_name
--   • sector
--   • industry
--   • country
--   • exchange
--   • website_url
--   • employee_count
--   • business_summary
--   • long_business_summary
--   • created_at
--   • updated_at
--   • last_sync_date
--   • last_sync_status
--   • data_quality_score
--   • data_start_date
--   • data_end_date
--   • total_records
--   • is_active
--   • sync_enabled
--   • headquarters
--   • ceo_name
--   • founded_year

-- TECHNICAL_INDICATORS
-- ----------------------------------------------------------------------------
--   • id
--   • stock_id
--   • date
--   • sma_7
--   • sma_20
--   • sma_50
--   • sma_100
--   • sma_200
--   • ema_12
--   • ema_26
--   • rsi_14
--   • macd_line
--   • macd_signal
--   • macd_histogram
--   • stochastic_osc
--   • bb_upper
--   • bb_middle
--   • bb_lower
--   • atr_14
--   • volatility_7d
--   • volatility_30d_annual
--   • volume_sma_20
--   • obv
--   • green_days_count
--   • support_30d
--   • resistance_30d
--   • adx
--   • created_at
--   • updated_at

-- ============================================================================

-- ============================================================================
-- SCHEMA DEFINITIONS (from supabase_schema.sql)
-- ============================================================================


-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- Shared trigger function to keep updated_at columns accurate on writes
CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 1. STOCKS REGISTRY TABLE - Track all managed stocks
-- ============================================================================
CREATE TABLE IF NOT EXISTS stocks (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(50),
    exchange VARCHAR(50),
    website_url VARCHAR(255),
    employee_count INT,
    headquarters VARCHAR(255),
    ceo_name VARCHAR(255),
    founded_year INT,
    business_summary TEXT,
    long_business_summary TEXT,
    first_trade_date BIGINT,  -- epoch timestamp
    
    -- Database management
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_sync_date TIMESTAMP,
    last_sync_status VARCHAR(20),  -- 'success', 'failed', 'partial'
    data_quality_score NUMERIC(3, 2),  -- 0.00 to 1.00
    
    -- Data coverage
    data_start_date DATE,
    data_end_date DATE,
    total_records INT DEFAULT 0,
    
    -- Tracking
    is_active BOOLEAN DEFAULT TRUE,
    sync_enabled BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_stock_symbol ON stocks (symbol);
CREATE INDEX idx_stock_ticker ON stocks (ticker);
CREATE INDEX idx_stock_sector ON stocks (sector);
CREATE INDEX idx_stock_active ON stocks (is_active);

-- ============================================================================
-- 2. DAILY PRICE DATA - Core OHLCV data for 10 years
-- ============================================================================
CREATE TABLE IF NOT EXISTS daily_price_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- OHLCV Data
    open_price NUMERIC(12, 4),
    high_price NUMERIC(12, 4),
    low_price NUMERIC(12, 4),
    close_price NUMERIC(12, 4),
    adjusted_close NUMERIC(12, 4),
    volume BIGINT,
    
    -- Derived metrics
    daily_return_pct NUMERIC(8, 4),
    price_change NUMERIC(12, 4),
    
    -- Data metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, date)
);

CREATE INDEX idx_stock_date ON daily_price_data (stock_id, date DESC);
CREATE INDEX idx_date_range ON daily_price_data (stock_id, date);
CREATE INDEX idx_stock_close ON daily_price_data (stock_id, close_price);

-- ============================================================================
-- 3. FUNDAMENTAL DATA - Financial metrics (quarterly/annual)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fundamental_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    period_date DATE NOT NULL,  -- Quarter/Year end date
    period_type VARCHAR(10) NOT NULL,  -- 'Q' or 'FY'
    
    -- Valuation
    pe_ratio NUMERIC(10, 2),
    pe_forward NUMERIC(10, 2),
    price_to_sales NUMERIC(10, 2),
    price_to_book NUMERIC(10, 2),
    peg_ratio NUMERIC(10, 2),
    ev_to_revenue NUMERIC(10, 2),
    ev_to_ebitda NUMERIC(10, 2),
    price_to_fcf NUMERIC(10, 2),
    
    -- Profitability
    net_margin NUMERIC(8, 4),
    operating_margin NUMERIC(8, 4),
    gross_margin NUMERIC(8, 4),
    ebitda_margin NUMERIC(8, 4),
    roe NUMERIC(8, 4),
    roa NUMERIC(8, 4),
    roic NUMERIC(8, 4),
    
    -- Quarterly Earnings Specials
    operating_income NUMERIC(18, 2),
    eps_basic NUMERIC(10, 4),
    eps_diluted NUMERIC(10, 4),
    
    -- Financial Health
    debt_to_equity NUMERIC(10, 2),
    total_cash NUMERIC(18, 2),
    total_debt NUMERIC(18, 2),
    free_cash_flow NUMERIC(18, 2),
    operating_cash_flow NUMERIC(18, 2),
    current_ratio NUMERIC(8, 4),
    quick_ratio NUMERIC(8, 4),
    
    -- Growth
    revenue_ttm NUMERIC(18, 2),
    revenue_growth_yoy NUMERIC(8, 4),
    net_income_ttm NUMERIC(18, 2),
    earnings_growth_yoy NUMERIC(8, 4),
    ebitda_ttm NUMERIC(18, 2),
    gross_profit_ttm NUMERIC(18, 2),
    capex_to_revenue NUMERIC(8, 4),
    
    -- Efficiency
    asset_turnover NUMERIC(8, 4),
    inventory_turnover NUMERIC(8, 4),
    receivables_turnover NUMERIC(8, 4),
    working_capital_turnover NUMERIC(8, 4),
    dso NUMERIC(8, 2),
    dio NUMERIC(8, 2),
    ccc NUMERIC(8, 2),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, period_date, period_type)
);

CREATE INDEX idx_stock_period ON fundamental_data (stock_id, period_date DESC);
CREATE INDEX idx_stock_type ON fundamental_data (stock_id, period_type);

-- ============================================================================
-- 4. TECHNICAL INDICATORS - Calculated indicators for trend analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS technical_indicators (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Trend Indicators
    sma_7 NUMERIC(12, 4),
    sma_20 NUMERIC(12, 4),
    sma_50 NUMERIC(12, 4),
    sma_100 NUMERIC(12, 4),
    sma_200 NUMERIC(12, 4),
    ema_12 NUMERIC(12, 4),
    ema_26 NUMERIC(12, 4),
    
    -- Momentum
    rsi_14 NUMERIC(8, 4),
    macd_line NUMERIC(12, 4),
    macd_signal NUMERIC(12, 4),
    macd_histogram NUMERIC(12, 4),
    stochastic_osc NUMERIC(8, 4),
    williams_r NUMERIC(8, 4),
    
    -- Volatility
    bb_upper NUMERIC(12, 4),
    bb_middle NUMERIC(12, 4),
    bb_lower NUMERIC(12, 4),
    atr_14 NUMERIC(12, 4),
    volatility_7d NUMERIC(8, 4),
    volatility_30d_annual NUMERIC(8, 4),
    keltner_upper NUMERIC(12, 4),
    keltner_lower NUMERIC(12, 4),
    
    -- Volume
    volume_sma_20 BIGINT,
    volume_sma_ratio NUMERIC(8, 4),
    volume_trend_5d VARCHAR(20),  -- 'Increasing', 'Decreasing', 'Mixed'
    obv NUMERIC(18, 2),
    vpt NUMERIC(18, 2),
    chaikin_money_flow NUMERIC(8, 4),
    avg_volume_3m BIGINT,
    green_days_count INT,
    
    -- Support/Resistance
    support_30d NUMERIC(12, 4),
    resistance_30d NUMERIC(12, 4),
    
    -- ADX for trend strength
    adx NUMERIC(8, 4),
    parabolic_sar NUMERIC(12, 4),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, date)
);

CREATE INDEX idx_tech_stock_date ON technical_indicators (stock_id, date DESC);
CREATE INDEX idx_tech_rsi ON technical_indicators (stock_id, rsi_14);
CREATE INDEX idx_tech_sma20 ON technical_indicators (stock_id, sma_20);
CREATE INDEX idx_tech_bb ON technical_indicators (stock_id, bb_upper, bb_lower);

-- ============================================================================
-- 5. FORECAST DATA - Price and earnings forecasts
-- ============================================================================
CREATE TABLE IF NOT EXISTS forecast_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,  -- When forecast was generated
    
    -- Price Forecast
    forecast_price_1y NUMERIC(12, 4),
    forecast_avg_price NUMERIC(12, 4),
    forecast_range_width NUMERIC(12, 4),
    forecast_period INT,  -- Days in forecast period
    
    -- Analyst Targets
    target_price_mean NUMERIC(12, 4),
    target_price_median NUMERIC(12, 4),
    target_price_high NUMERIC(12, 4),
    target_price_low NUMERIC(12, 4),
    analyst_rating VARCHAR(50),  -- 'Buy', 'Hold', 'Sell', 'Underperform', 'Overperform'
    analyst_count INT,
    
    -- Earnings Timing
    next_earnings_date DATE,
    earnings_call_time_utc TIME,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_forecast_stock_date ON forecast_data (stock_id, forecast_date DESC);
CREATE INDEX idx_forecast_earnings ON forecast_data (stock_id, next_earnings_date);

-- ============================================================================
-- 5a. ANALYST DATA - Analyst ratings and price targets
-- ============================================================================
CREATE TABLE IF NOT EXISTS analyst_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    
    -- Analyst Targets
    target_price_mean NUMERIC(12, 4),
    target_price_median NUMERIC(12, 4),
    target_price_high NUMERIC(12, 4),
    target_price_low NUMERIC(12, 4),
    analyst_rating VARCHAR(50),  -- 'Buy', 'Hold', 'Sell', 'Strong Buy', 'Strong Sell'
    analyst_count INT,
    
    -- Earnings Timing
    next_earnings_date DATE,
    
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id)
);

CREATE INDEX idx_analyst_stock ON analyst_data (stock_id);
CREATE INDEX idx_analyst_earnings ON analyst_data (stock_id, next_earnings_date);

-- ============================================================================
-- 6. RISK & VOLATILITY DATA (Enhanced with 64 Metadata Columns)
-- ============================================================================
CREATE TABLE IF NOT EXISTS risk_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- ========================================================================
    -- BASE RISK METRICS (19 columns)
    -- ========================================================================
    
    -- Value at Risk
    var_95 NUMERIC(8, 4),
    var_99 NUMERIC(8, 4),
    
    -- Conditional Value at Risk (Enhanced Tail Risk)
    cvar_95 NUMERIC(8, 4),
    cvar_99 NUMERIC(8, 4),
    
    -- Risk-adjusted metrics
    sharpe_ratio NUMERIC(8, 4),
    sortino_ratio NUMERIC(8, 4),
    calmar_ratio NUMERIC(8, 4),
    max_drawdown NUMERIC(8, 4),
    
    -- Market Risk
    beta NUMERIC(8, 4),
    market_correlation NUMERIC(8, 4),
    
    -- Enhanced Volatility Metrics
    volatility_30d_annual NUMERIC(8, 4),
    volatility_historical_annual NUMERIC(8, 4),
    
    -- Distribution stats
    skewness NUMERIC(8, 4),
    kurtosis NUMERIC(8, 4),
    
    -- ========================================================================
    -- METADATA COLUMNS (64 columns) - Added 2026-02-11
    -- ========================================================================
    
    -- VaR Metadata (10 columns)
    var_95_data_period_days INTEGER,
    var_95_sample_size INTEGER,
    var_95_calculation_method VARCHAR(100),
    var_95_confidence_level NUMERIC(5, 4),
    var_95_return_frequency VARCHAR(50),
    var_99_data_period_days INTEGER,
    var_99_sample_size INTEGER,
    var_99_calculation_method VARCHAR(100),
    var_99_confidence_level NUMERIC(5, 4),
    var_99_return_frequency VARCHAR(50),
    
    -- CVaR Metadata (8 columns)
    cvar_95_data_period_days INTEGER,
    cvar_95_tail_size INTEGER,
    cvar_95_calculation_method VARCHAR(100),
    cvar_95_confidence_level NUMERIC(5, 4),
    cvar_99_data_period_days INTEGER,
    cvar_99_tail_size INTEGER,
    cvar_99_calculation_method VARCHAR(100),
    cvar_99_confidence_level NUMERIC(5, 4),
    
    -- Volatility Metadata (12 columns)
    volatility_30d_sample_days NUMERIC(8, 2),
    volatility_30d_calculation_method VARCHAR(100),
    volatility_30d_annualization_factor NUMERIC(10, 4),
    volatility_30d_return_frequency VARCHAR(50),
    volatility_30d_model_type VARCHAR(50),
    volatility_30d_fallback_logic VARCHAR(255),
    volatility_historical_sample_days NUMERIC(8, 2),
    volatility_historical_calculation_method VARCHAR(100),
    volatility_historical_annualization_factor NUMERIC(10, 4),
    volatility_historical_return_frequency VARCHAR(50),
    volatility_historical_model_type VARCHAR(50),
    volatility_trading_days_annual INTEGER DEFAULT 252,
    
    -- Liquidity Metadata (13 columns)
    liquidity_calculation_method VARCHAR(100),
    liquidity_data_period_days NUMERIC(8, 2),
    liquidity_actual_sample_days NUMERIC(8, 2),
    liquidity_volume_weight NUMERIC(5, 2),
    liquidity_volume_benchmark BIGINT,
    liquidity_mcap_weight NUMERIC(5, 2),
    liquidity_mcap_benchmark BIGINT,
    liquidity_stability_weight NUMERIC(5, 2),
    liquidity_stability_metric VARCHAR(100),
    liquidity_data_freshness VARCHAR(50),
    liquidity_minimum_required_days INTEGER DEFAULT 30,
    liquidity_sufficient_data BOOLEAN,
    
    -- Altman Z-Score Metadata (18 columns)
    altman_calculation_method VARCHAR(100),
    altman_financial_period VARCHAR(20),
    altman_financial_period_end_date DATE,
    altman_financial_data_source VARCHAR(100),
    altman_data_age_days NUMERIC(8, 2),
    altman_filing_type VARCHAR(20),
    altman_required_fields_count INTEGER DEFAULT 6,
    altman_available_fields_count INTEGER,
    altman_data_completeness_percent NUMERIC(5, 2),
    altman_minimum_completeness_percent NUMERIC(5, 2) DEFAULT 67.0,
    altman_retained_earnings_imputed BOOLEAN DEFAULT FALSE,
    altman_imputation_method VARCHAR(255),
    altman_next_update_expected DATE,
    altman_coefficient_a NUMERIC(8, 4) DEFAULT 1.2,
    altman_coefficient_b NUMERIC(8, 4) DEFAULT 1.4,
    altman_coefficient_c NUMERIC(8, 4) DEFAULT 3.3,
    altman_coefficient_d NUMERIC(8, 4) DEFAULT 0.6,
    altman_coefficient_e NUMERIC(8, 4) DEFAULT 1.0,
    
    -- Sharpe & Sortino Metadata (10 columns)
    sharpe_ratio_calculation_method VARCHAR(255),
    sharpe_ratio_data_period_days NUMERIC(8, 2),
    sharpe_ratio_risk_free_rate_used NUMERIC(8, 6),
    sharpe_ratio_risk_free_rate_source VARCHAR(100),
    sharpe_ratio_annualization_factor NUMERIC(10, 4) DEFAULT 15.8745,
    sharpe_ratio_daily_rf_rate NUMERIC(8, 8),
    sortino_ratio_calculation_method VARCHAR(255),
    sortino_ratio_data_period_days NUMERIC(8, 2),
    sortino_ratio_annualization_factor NUMERIC(10, 4) DEFAULT 15.8745,
    sortino_ratio_downside_focus VARCHAR(100),
    
    -- Other Metrics Metadata (15 columns)
    max_drawdown_calculation_method VARCHAR(255),
    max_drawdown_data_period_days NUMERIC(8, 2),
    max_drawdown_definition VARCHAR(255),
    beta_calculation_method VARCHAR(255),
    beta_data_period_days NUMERIC(8, 2),
    beta_market_benchmark VARCHAR(50),
    beta_return_frequency VARCHAR(50),
    correlation_calculation_method VARCHAR(255),
    correlation_data_period_days NUMERIC(8, 2),
    correlation_market_benchmark VARCHAR(50),
    skewness_calculation_method VARCHAR(255),
    skewness_data_period_days NUMERIC(8, 2),
    skewness_interpretation VARCHAR(255),
    kurtosis_calculation_method VARCHAR(255),
    kurtosis_data_period_days NUMERIC(8, 2),
    
    -- Confidence & Quality Scores (11 columns)
    var_estimation_confidence NUMERIC(5, 2),
    volatility_estimation_confidence NUMERIC(5, 2),
    liquidity_estimation_confidence NUMERIC(5, 2),
    altman_estimation_confidence NUMERIC(5, 2),
    sharpe_estimation_confidence NUMERIC(5, 2),
    overall_profile_confidence NUMERIC(5, 2),
    has_data_gaps BOOLEAN DEFAULT FALSE,
    missing_price_data BOOLEAN DEFAULT FALSE,
    missing_financial_data BOOLEAN DEFAULT FALSE,
    insufficient_liquidity_data BOOLEAN DEFAULT FALSE,
    data_quality_score NUMERIC(5, 2),
    
    -- Tracking Fields (3 columns)
    metadata_calculation_timestamp TIMESTAMP,
    metadata_version INTEGER DEFAULT 1,
    risk_profile_calculation_method VARCHAR(100),
    
    -- ========================================================================
    -- SYSTEM COLUMNS
    -- ========================================================================
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, date)
);

-- Base Indexes
CREATE INDEX idx_risk_stock_date ON risk_data (stock_id, date DESC);
CREATE INDEX idx_risk_beta ON risk_data (stock_id, beta);
CREATE INDEX idx_risk_cvar ON risk_data (stock_id, cvar_95);
CREATE INDEX idx_risk_volatility ON risk_data (stock_id, volatility_30d_annual);

-- Metadata Indexes (Added 2026-02-11)
CREATE INDEX IF NOT EXISTS idx_risk_var_confidence 
ON risk_data(stock_id, var_estimation_confidence DESC);

CREATE INDEX IF NOT EXISTS idx_risk_overall_confidence 
ON risk_data(stock_id, overall_profile_confidence DESC);

CREATE INDEX IF NOT EXISTS idx_risk_data_quality 
ON risk_data(stock_id, data_quality_score DESC);

CREATE INDEX IF NOT EXISTS idx_risk_altman_age 
ON risk_data(stock_id, altman_data_age_days ASC);

CREATE INDEX IF NOT EXISTS idx_risk_metadata_timestamp 
ON risk_data(stock_id, metadata_calculation_timestamp DESC);

-- ============================================================================
-- 6a. LIQUIDITY RISK DATA - Hasbrouck Model
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
CREATE INDEX idx_liquidity_stock_date ON liquidity_risk_data (stock_id, date DESC);
CREATE INDEX idx_liquidity_score ON liquidity_risk_data (stock_id, liquidity_score);
CREATE INDEX idx_liquidity_risk_level ON liquidity_risk_data (risk_level);

-- Liquidity risk update trigger
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

-- ============================================================================
-- 6b. ALTMAN Z-SCORE DATA - Bankruptcy Risk
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
CREATE INDEX idx_altman_stock_date ON altman_zscore_data (stock_id, date DESC);
CREATE INDEX idx_altman_zscore ON altman_zscore_data (stock_id, z_score);
CREATE INDEX idx_altman_risk_zone ON altman_zscore_data (risk_zone);

-- Altman Z-Score update trigger
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

-- ============================================================================
-- 6c. REGIME RISK DATA - Market Regime Analysis
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
CREATE INDEX idx_regime_stock_date ON regime_risk_data (stock_id, date DESC);  
CREATE INDEX idx_regime_current ON regime_risk_data (current_regime);
CREATE INDEX idx_regime_confidence ON regime_risk_data (regime_confidence);

-- Regime risk update trigger
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
-- 7. MARKET PRICE SNAPSHOT - Real-time overview data
-- ============================================================================
CREATE TABLE IF NOT EXISTS market_price_snapshot (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Current Price & Changes
    current_price NUMERIC(12, 4),
    price_change NUMERIC(12, 4),
    change_pct NUMERIC(8, 4),
    
    -- Performance metrics
    change_15d_pct NUMERIC(8, 4),
    change_52w_pct NUMERIC(8, 4),
    performance_1y_pct NUMERIC(8, 4),
    overall_pct_change NUMERIC(8, 4),
    
    -- 52 Week Range
    high_52w NUMERIC(12, 4),
    low_52w NUMERIC(12, 4),
    
    -- Market Size
    market_cap NUMERIC(18, 2),
    enterprise_value NUMERIC(18, 2),
    shares_outstanding NUMERIC(15, 2),
    float_shares NUMERIC(15, 2),
    
    -- Market Context
    sp500_index NUMERIC(12, 4),
    interest_rate NUMERIC(8, 4),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, date),
    
    -- Data integrity constraint: float_shares must be <= shares_outstanding
    CONSTRAINT chk_float_le_outstanding CHECK (
        float_shares IS NULL OR 
        shares_outstanding IS NULL OR 
        float_shares <= shares_outstanding
    )
);

CREATE INDEX idx_mps_stock_date ON market_price_snapshot (stock_id, date DESC);

-- ============================================================================
-- 8. DIVIDEND DATA - Dividend history
-- ============================================================================
CREATE TABLE IF NOT EXISTS dividend_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    
    -- Dividend Info
    dividend_rate NUMERIC(10, 4),
    dividend_yield_pct NUMERIC(8, 4),
    payout_ratio NUMERIC(8, 4),
    avg_dividend_yield_5y NUMERIC(8, 4),
    dividend_forward_rate NUMERIC(10, 4),
    dividend_forward_yield NUMERIC(8, 4),
    dividend_trailing_rate NUMERIC(10, 4),
    dividend_trailing_yield NUMERIC(8, 4),
    
    -- Dates
    ex_dividend_date DATE,
    payment_date DATE,
    last_split_date DATE,
    last_split_factor NUMERIC(8, 4),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, ex_dividend_date)
);

CREATE INDEX idx_div_stock_date ON dividend_data (stock_id, ex_dividend_date DESC);

-- ============================================================================
-- 9. OWNERSHIP DATA - Insider and institutional ownership
-- ============================================================================
CREATE TABLE IF NOT EXISTS ownership_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    
    -- Ownership percentages
    insider_ownership_pct NUMERIC(8, 4),
    institutional_ownership_pct NUMERIC(8, 4),
    
    -- Short Selling
    shares_short NUMERIC(15, 2),
    short_ratio_days NUMERIC(8, 2),
    short_pct_float NUMERIC(8, 4),
    shares_short_prev NUMERIC(15, 2),
    shares_change_yoy NUMERIC(15, 2),
    
    -- Dilution
    shares_outstanding_diluted NUMERIC(15, 2),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, report_date)
);

CREATE INDEX idx_own_stock_date ON ownership_data (stock_id, report_date DESC);

-- ============================================================================
-- 10. SENTIMENT DATA - Sentiment analysis results
-- ============================================================================
CREATE TABLE IF NOT EXISTS sentiment_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Overall Sentiment
    sentiment_score NUMERIC(8, 4),  -- -1.0 to 1.0
    sentiment_label VARCHAR(50),  -- 'Bullish', 'Neutral', 'Bearish'
    sentiment_confidence NUMERIC(8, 4),
    
    -- Component Sentiments
    news_sentiment NUMERIC(8, 4),
    analyst_sentiment NUMERIC(8, 4),
    options_sentiment NUMERIC(8, 4),
    
    -- Options Activity
    put_call_ratio NUMERIC(8, 4),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, date)
);

CREATE INDEX idx_sent_stock_date ON sentiment_data (stock_id, date DESC);
CREATE INDEX idx_sent_score ON sentiment_data (stock_id, sentiment_score);

-- ============================================================================
-- 10b. STOCK NEWS DATA - Stock-specific news articles
-- ============================================================================
CREATE TABLE IF NOT EXISTS stock_news_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    publisher VARCHAR(255),
    published_date TIMESTAMP WITH TIME ZONE,
    
    -- Sentiment
    sentiment_score NUMERIC(8, 4),  -- -1.0 to 1.0
    sentiment_label VARCHAR(50),  -- 'Bullish', 'Neutral', 'Bearish'
    
    -- Relevance
    relevance_score NUMERIC(8, 4) DEFAULT 1.0,
    category VARCHAR(100),
    
    -- Source tracking
    source_api VARCHAR(50) DEFAULT 'yfinance',  -- 'yfinance' or 'finnhub'
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, url, published_date)
);

CREATE INDEX idx_news_stock ON stock_news_data (stock_id);
CREATE INDEX idx_news_published ON stock_news_data (published_date DESC);
CREATE INDEX idx_news_stock_published ON stock_news_data (stock_id, published_date DESC);

-- ============================================================================
-- 11. INSIDER TRANSACTIONS - Insider trading activity
-- ============================================================================
CREATE TABLE IF NOT EXISTS insider_transactions (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    
    -- Insider Info
    insider_name VARCHAR(255),
    relation_to_company VARCHAR(100),
    
    -- Transaction Details
    transaction_date DATE NOT NULL,
    filing_date DATE,
    transaction_code VARCHAR(10),
    code_description VARCHAR(100),
    shares_change NUMERIC(15, 2),
    transaction_price NUMERIC(18, 4),
    estimated_value NUMERIC(18, 2),
    shares_after NUMERIC(15, 2),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_insider_stock_date ON insider_transactions (stock_id, transaction_date DESC);
CREATE INDEX idx_insider_name ON insider_transactions (insider_name);

-- ============================================================================
-- 12. DATA SYNC LOG - Track all data updates for audit and debugging
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_sync_log (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    
    sync_type VARCHAR(50),  -- 'daily', 'weekly', 'full_history'
    sync_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Sync Statistics
    records_inserted INT,
    records_updated INT,
    records_deleted INT,
    records_failed INT,
    
    -- Status and Errors
    sync_status VARCHAR(20),  -- 'success', 'partial', 'failed'
    error_message TEXT,
    
    -- Duration
    sync_duration_seconds INT,
    data_quality_score NUMERIC(3, 2),
    
    -- Metadata
    source_api VARCHAR(100),
    api_version VARCHAR(50),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sync_stock_date ON data_sync_log (stock_id, sync_date DESC);
CREATE INDEX idx_sync_status ON data_sync_log (sync_status);
CREATE INDEX idx_sync_type ON data_sync_log (sync_type, sync_date DESC);

-- ============================================================================
-- 13. PEER COMPARISON DATA - Industry peer metrics for comparison
-- ============================================================================
CREATE TABLE IF NOT EXISTS peer_comparison_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    peer_ticker VARCHAR(10) NOT NULL,
    peer_name VARCHAR(255),
    is_target BOOLEAN DEFAULT FALSE,  -- TRUE if this is the target stock, FALSE for peers
    
    -- Metrics
    market_cap NUMERIC(18, 2),
    pe_ratio NUMERIC(10, 2),
    revenue_growth NUMERIC(8, 4),
    net_margin NUMERIC(8, 4),
    eps NUMERIC(10, 4),
    roe NUMERIC(8, 4),
    debt_to_equity NUMERIC(10, 4),
    dividend_yield NUMERIC(8, 4),
    week_52_high NUMERIC(12, 4),
    week_52_low NUMERIC(12, 4),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, peer_ticker)
);

CREATE INDEX idx_peer_stock ON peer_comparison_data (stock_id);
CREATE INDEX idx_peer_ticker ON peer_comparison_data (peer_ticker);


-- ============================================================================
-- MATERIALIZED VIEW - Last known values for fast access
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS latest_stock_metrics AS
SELECT 
    s.id,
    s.symbol,
    s.company_name,
    s.sector,
    mpd.current_price,
    mpd.change_pct,
    mpd.market_cap,
    fd.pe_ratio,
    fd.ev_to_ebitda,
    td.rsi_14,
    td.macd_line,
    td.sma_200,
    rd.beta,
    sd.sentiment_score,
    mpd.date as last_update_date
FROM stocks s
LEFT JOIN market_price_snapshot mpd ON s.id = mpd.stock_id 
    AND mpd.date = (SELECT MAX(date) FROM market_price_snapshot WHERE stock_id = s.id)
LEFT JOIN fundamental_data fd ON s.id = fd.stock_id
    AND fd.period_date = (SELECT MAX(period_date) FROM fundamental_data WHERE stock_id = s.id)
LEFT JOIN technical_indicators td ON s.id = td.stock_id
    AND td.date = (SELECT MAX(date) FROM technical_indicators WHERE stock_id = s.id)
LEFT JOIN risk_data rd ON s.id = rd.stock_id
    AND rd.date = (SELECT MAX(date) FROM risk_data WHERE stock_id = s.id)
LEFT JOIN sentiment_data sd ON s.id = sd.stock_id
    AND sd.date = (SELECT MAX(date) FROM sentiment_data WHERE stock_id = s.id)
WHERE s.is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_latest_metrics_symbol ON latest_stock_metrics(symbol);

-- ============================================================================
-- ROW LEVEL SECURITY - Restrict data access (if using Supabase Auth)
-- ============================================================================
-- ALTER TABLE stocks ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE daily_price_data ENABLE ROW LEVEL SECURITY;
-- -- Add policies as needed for multi-tenancy

-- ============================================================================
-- PARTITIONING - For very large tables (optional for production)
-- ============================================================================
-- Uncomment if implementing partitioning for daily_price_data by year

-- SELECT create_hypertable('daily_price_data', 'date', if_not_exists => TRUE);
-- SELECT create_hypertable('technical_indicators', 'date', if_not_exists => TRUE);
-- SELECT create_hypertable('risk_data', 'date', if_not_exists => TRUE);

-- ============================================================================
-- PERFORMANCE TUNING - Analyze tables after initial load
-- ============================================================================
-- ANALYZE stocks;
-- ANALYZE daily_price_data;
-- ANALYZE technical_indicators;
