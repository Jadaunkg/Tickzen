-- Fix for numeric field overflow in insider_transactions table
-- Run this SQL command in your Supabase SQL Editor

-- Increase precision of transaction_price column to handle larger values
ALTER TABLE insider_transactions 
ALTER COLUMN transaction_price TYPE NUMERIC(18, 4);

-- Verify the change
SELECT column_name, data_type, numeric_precision, numeric_scale 
FROM information_schema.columns 
WHERE table_name = 'insider_transactions' 
AND column_name = 'transaction_price';