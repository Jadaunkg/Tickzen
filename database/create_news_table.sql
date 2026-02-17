-- NEWS TABLE SCHEMA FOR SUPABASE
-- ================================
-- Table to store stock-specific news articles for each stock
-- Run this in Supabase SQL Editor after the main schema

CREATE TABLE IF NOT EXISTS stock_news_data (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    publisher TEXT,
    published_date TIMESTAMP WITH TIME ZONE,
    sentiment_score NUMERIC(8, 4),
    sentiment_label TEXT,
    relevance_score NUMERIC(8, 4) DEFAULT 1.0,
    category TEXT,
    source_api TEXT DEFAULT 'yfinance',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
    UNIQUE(stock_id, url, published_date)
);

-- Create indexes for optimal query performance
CREATE INDEX idx_stock_news_stock_id ON stock_news_data (stock_id);
CREATE INDEX idx_stock_news_published ON stock_news_data (published_date DESC);
CREATE INDEX idx_stock_news_stock_published ON stock_news_data (stock_id, published_date DESC);

-- Add RLS (Row Level Security) if needed
ALTER TABLE stock_news_data ENABLE ROW LEVEL SECURITY;

-- Optional: Create policy for read access (adjust as needed)
CREATE POLICY "Enable read access for all users" ON stock_news_data
    FOR SELECT USING (true);

-- Optional: Create policy for insert/update (adjust as needed)
CREATE POLICY "Enable insert for authenticated users" ON stock_news_data
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for authenticated users" ON stock_news_data
    FOR UPDATE USING (true);

-- Add a function to auto-update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_stock_news_data_updated_at
    BEFORE UPDATE ON stock_news_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comment for documentation
COMMENT ON TABLE stock_news_data IS 'Stock-specific news articles with timestamps and sentiment analysis';
COMMENT ON COLUMN stock_news_data.stock_id IS 'Foreign key reference to stocks table';
COMMENT ON COLUMN stock_news_data.published_date IS 'Original publication timestamp from news source';
COMMENT ON COLUMN stock_news_data.sentiment_score IS 'Sentiment score from -1 (negative) to 1 (positive)';
COMMENT ON COLUMN stock_news_data.relevance_score IS 'Relevance score from 0 to 1 for stock-specific content';
COMMENT ON COLUMN stock_news_data.source_api IS 'Which API source provided the news (yfinance/finnhub)';