
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

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
-- 6. RISK & VOLATILITY DATA
-- ============================================================================
CREATE TABLE IF NOT EXISTS risk_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Value at Risk
    var_95 NUMERIC(8, 4),
    var_99 NUMERIC(8, 4),
    
    -- Risk-adjusted metrics
    sharpe_ratio NUMERIC(8, 4),
    sortino_ratio NUMERIC(8, 4),
    calmar_ratio NUMERIC(8, 4),
    max_drawdown NUMERIC(8, 4),
    
    -- Market Risk
    beta NUMERIC(8, 4),
    market_correlation NUMERIC(8, 4),
    
    -- Distribution stats
    skewness NUMERIC(8, 4),
    kurtosis NUMERIC(8, 4),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(stock_id, date)
);

CREATE INDEX idx_risk_stock_date ON risk_data (stock_id, date DESC);
CREATE INDEX idx_risk_beta ON risk_data (stock_id, beta);

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
