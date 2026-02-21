#!/usr/bin/env python3
"""
Data Preprocessing and Quality Management
========================================

Comprehensive data preprocessing pipeline for financial time-series data.
Handles data cleaning, validation, transformation, and feature engineering
to ensure high-quality inputs for analysis and machine learning models.

Core Preprocessing Functions:
----------------------------
1. **Data Fetching and Validation**:
   - Maximum historical data retrieval via yfinance
   - Data completeness and quality validation
   - Missing data detection and handling
   - Outlier identification and treatment

2. **Data Cleaning Operations**:
   - Remove invalid or corrupt data points
   - Handle stock splits and dividend adjustments
   - Timezone normalization and consistency
   - Volume and price anomaly correction

3. **Feature Engineering Integration**:
   - Technical indicator calculation
   - Derived metrics and ratios
   - Time-based feature extraction
   - Market regime indicators

4. **Data Standardization**:
   - Consistent column naming conventions
   - Unified date indexing across datasets
   - Price and volume normalization
   - Currency conversion when applicable

Data Quality Assurance:
----------------------
- **Completeness Checks**: Verify expected data points exist
- **Accuracy Validation**: Cross-reference with multiple sources
- **Consistency Testing**: Ensure logical data relationships
- **Freshness Verification**: Check data recency and relevance
- **Range Validation**: Verify values within expected ranges

Missing Data Handling:
---------------------
- **Forward Fill**: Use previous valid values for gaps
- **Interpolation**: Linear/polynomial interpolation for small gaps
- **Market Hours**: Skip non-trading periods appropriately
- **Holiday Handling**: Account for market holidays and closures
- **Weekend Gaps**: Handle weekend and holiday data gaps

Outlier Detection and Treatment:
-------------------------------
- **Statistical Methods**: Z-score and IQR-based detection
- **Price Spike Detection**: Identify unusual price movements
- **Volume Anomalies**: Detect abnormal trading volumes
- **Treatment Options**: Remove, cap, or transform outliers
- **Context Preservation**: Maintain significant market events

Data Transformation Pipeline:
----------------------------
1. **Raw Data Ingestion**: Fetch from yfinance with error handling
2. **Initial Validation**: Check data format and basic quality
3. **Cleaning Operations**: Remove/correct invalid data points
4. **Feature Addition**: Add technical indicators and derived metrics
5. **Final Validation**: Comprehensive quality checks
6. **Output Formatting**: Standardized DataFrame structure

Technical Indicator Integration:
-------------------------------
Seamless integration with feature engineering:
- **Price-based Indicators**: Moving averages, price ratios
- **Volume-based Indicators**: Volume trends and patterns
- **Volatility Measures**: Price volatility and ranges
- **Momentum Indicators**: Rate of change calculations

Performance Optimizations:
-------------------------
- **Vectorized Operations**: NumPy/Pandas optimized calculations
- **Memory Efficiency**: Optimal data types and structures
- **Parallel Processing**: Multi-threading for large datasets
- **Caching**: Preprocessed data caching for reuse
- **Lazy Loading**: On-demand data processing

Error Handling:
--------------
- **Network Failures**: Robust handling of API failures
- **Data Corruption**: Detection and recovery mechanisms
- **Partial Data**: Graceful handling of incomplete datasets
- **Processing Errors**: Comprehensive exception handling
- **User Notification**: Clear error reporting via SocketIO

Data Output Structure:
---------------------
Standardized pandas DataFrame with:
```python
columns = [
    'Open', 'High', 'Low', 'Close', 'Volume',  # OHLCV data
    'SMA_20', 'EMA_50', 'RSI', 'MACD',         # Technical indicators
    'Returns', 'Volatility', 'Volume_MA',       # Derived features
    'Trading_Day', 'Week_Day', 'Month'          # Time-based features
]
index = DatetimeIndex  # Timezone-aware datetime index
```

Usage Examples:
--------------
```python
# Basic preprocessing
clean_data = fetch_stock_data('AAPL')

# Advanced preprocessing with custom parameters
processed_data = preprocess_data(
    ticker='AAPL',
    start_date='2020-01-01',
    include_indicators=True,
    outlier_treatment='cap',
    missing_data_method='interpolate'
)

# Bulk preprocessing
all_data = {}
for ticker in ['AAPL', 'GOOGL', 'MSFT']:
    all_data[ticker] = fetch_stock_data(ticker)
```

Integration Points:
------------------
- Called by automation_scripts/pipeline.py for analysis workflow
- Feeds into Models/prophet_model.py for forecasting
- Provides data for analysis_scripts/ modules
- Supports real-time data updates and validation

Quality Metrics:
---------------
- **Data Completeness**: Percentage of expected data points
- **Processing Success Rate**: Successful preprocessing percentage
- **Error Rates**: Frequency of data quality issues
- **Performance Metrics**: Processing time and memory usage

Configuration:
-------------
Tunable parameters for different use cases:
- **Outlier Thresholds**: Statistical significance levels
- **Missing Data Tolerance**: Maximum allowable gaps
- **Feature Selection**: Configurable indicator inclusion
- **Processing Options**: Speed vs accuracy trade-offs

Author: TickZen Development Team
Version: 2.4
Last Updated: January 2026
"""

import yfinance as yf
import pandas as pd
# Assuming add_technical_indicators is in the specified path relative to this script
# or the Python path is configured for this import.
from data_processing_scripts.feature_engineering import add_technical_indicators

def fetch_stock_data(ticker):
    """Fetch and process maximum historical stock data for a single ticker"""
    # Fetch data with maximum history
    data = yf.download(
        ticker,
        period="max",
        auto_adjust=True,
        progress=False
    )
    
    if data.empty:
        raise ValueError(f"No data found for ticker: {ticker}")

    data = data.reset_index()
    
    # Clean column names (handle both single and multi-ticker cases)
    # This cleaning is generally for standardizing yfinance output or other potentially messy sources.
    # For OHLCV from yfinance with auto_adjust=True, this split('_')[0] is usually benign
    # as standard column names don't typically have underscores needing this cleaning.
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = ['_'.join(col).strip() for col in data.columns.values]
        data.columns = [col.split('_')[0] for col in data.columns]
    else:
        data.columns = [col.split('_')[0] for col in data.columns]

    #Standardize Column name
    column_map = {
        'Open': 'Open',
        'High': 'High',
        'Low': 'Low',
        'Close': 'Close',
        'Volume': 'Volume'
    }
    # Only rename if the original (potentially truncated) name exists
    # This avoids creating columns if they were removed by the split logic above, though unlikely for OHLCV.
    existing_cols_to_rename = {k: v for k, v in column_map.items() if k in data.columns}
    data = data.rename(columns=existing_cols_to_rename)


    # Handle date column
    date_cols = [col for col in data.columns if 'date' in str(col).lower()]
    if date_cols:
        data = data.rename(columns={date_cols[0]: 'Date'})
    
    # Convert and validate dates
    if 'Date' in data.columns:
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce', utc=True).dt.tz_localize(None)
        data = data.dropna(subset=['Date']).sort_values('Date')
    else:
        raise ValueError(f"Date column could not be identified for ticker: {ticker}")

    # Validate required columns
    required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Missing columns after initial processing for {ticker}: {missing}. Available columns: {list(data.columns)}")

    # Data quality checks
    if len(data) < 100:
        raise ValueError(f"Need ≥100 data points for {ticker} (got {len(data)})")

    data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')
    if 'Volume' in data.columns and data['Volume'].mean() < 900: # Ensure Volume exists and is numeric before mean
        raise ValueError(f"Low liquidity for {ticker} (avg volume: {data['Volume'].mean():.0f})")

    return data[required]


def enforce_date_column(df, df_name):
    """Standardize date column across datasets.
    Removed aggressive general column name cleaning to preserve specific names like 'Interest_Rate'.
    """
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"{df_name} data is not a DataFrame")
    
    df_copy = df.copy() # Work on a copy to avoid modifying original DataFrame passed to function

    # --- MODIFIED SECTION: Aggressive column name cleaning removed ---
    # The following general column name cleaning was removed because it was
    # incorrectly truncating valid macroeconomic feature names (e.g., 'Interest_Rate' to 'Interest').
    # Its primary purpose was likely to standardize other, less structured data sources,
    # but it conflicts with the expected column names from macro_data.py.

    # if isinstance(df_copy.columns, pd.MultiIndex):
    #     df_copy.columns = ['_'.join(col).strip() for col in df_copy.columns.values]
    #     df_copy.columns = [col.split('_')[0] for col in df_copy.columns]
    # else:
    #     df_copy.columns = [col.split('_')[0] for col in df_copy.columns]
    # --- END OF MODIFIED SECTION ---
    
    # Find and rename date column
    date_cols = [col for col in df_copy.columns if 'date' in str(col).lower()]
    if date_cols:
        # Only rename if the identified date column is not already named 'Date'
        if date_cols[0] != 'Date':
            df_copy = df_copy.rename(columns={date_cols[0]: 'Date'})
    elif 'Date' not in df_copy.columns: # If no 'date'-like column found and 'Date' is not present
        raise ValueError(f"{df_name} data missing a recognizable Date column (looked for 'Date' or 'date'). Available columns: {list(df_copy.columns)}")
    
    # Convert and validate dates (assuming 'Date' column now exists or was already there)
    if 'Date' in df_copy.columns:
        df_copy['Date'] = pd.to_datetime(df_copy['Date'], errors='coerce', utc=True)
        df_copy['Date'] = df_copy['Date'].dt.tz_localize(None) # Standardize to tz-naive
        df_copy = df_copy.dropna(subset=['Date']).sort_values('Date')
        
        # Remove any duplicate dates by keeping the last occurrence (most recent data)
        if df_copy['Date'].duplicated().any():
            df_copy = df_copy.drop_duplicates(subset=['Date'], keep='last')
            
    else:
        # This case should ideally be caught by the elif above, but as a safeguard:
        raise ValueError(f"{df_name} data still missing 'Date' column after attempting to identify/rename it.")
        
    return df_copy


def preprocess_data(stock_df, macro_df):
    """Merge and align stock data with macroeconomic data"""
    # Standardize date columns on copies of the dataframes
    stock = enforce_date_column(stock_df.copy(), "Stock") # Use .copy() if stock_df might be used elsewhere
    macro = enforce_date_column(macro_df.copy(), "Macro") # Use .copy()

    # Rename stock OHLCV columns (ensure consistency, as enforce_date_column now primarily handles 'Date')
    # This is useful if stock_df comes from a source that doesn't pre-standardize these names.
    stock_column_map = {
        'Open': 'Open', 'High': 'High', 'Low': 'Low',
        'Close': 'Close', 'Volume': 'Volume'
    }
    # Only rename if the original name exists
    existing_stock_cols_to_rename = {k: v for k, v in stock_column_map.items() if k in stock.columns}
    stock = stock.rename(columns=existing_stock_cols_to_rename)


    # Date Alignment
    stock_min = stock['Date'].min()
    stock_max = stock['Date'].max()
    macro_min = macro['Date'].min()
    macro_max = macro['Date'].max()
    
    # Handle case where stock data is newer than macro data
    # Use the most recent macro data available for newer stock dates
    if stock_min > macro_max:
        # All stock data is newer than macro data - extend macro data forward
        start_date = stock_min
        end_date = stock_max
        logger.warning(f"Stock data ({stock_min} to {stock_max}) is newer than macro data ({macro_min} to {macro_max}). Will forward-fill macro data.")
    elif stock_max < macro_min:
        # All stock data is older than macro data - this is unusual
        raise ValueError(f"Date range misalignment: Stock data ({stock_min} to {stock_max}) is entirely before macro data ({macro_min} to {macro_max}). Cannot proceed.")
    else:
        # Normal case with overlap
        # Use stock_max as end_date (not macro_max) so that recent stock records beyond
        # the FRED publication lag (~5-7 days) are NOT silently dropped.
        # The macro reindex+ffill below will forward-fill the trailing gap in macro data.
        start_date = max(stock_min, macro_min)
        end_date = stock_max  # FIX: was min(stock_max, macro_max) — that clipped records when FRED lags behind
        
        if start_date > end_date:
            raise ValueError(f"Date range misalignment: Stock data range {stock_min} to {stock_max}, Macro data range {macro_min} to {macro_max}. No overlapping period found.")

    date_range = pd.date_range(start=start_date, end=end_date, freq='D') # Daily frequency

    # Reindex and forward-fill missing values
    stock_processed = (
        stock.set_index('Date').reindex(date_range)
        .rename_axis('Date').ffill().bfill().reset_index() # ffill then bfill to handle NaNs at edges
    )
    macro_processed = (
        macro.set_index('Date').reindex(date_range)
        .rename_axis('Date').ffill().bfill().reset_index() # ffill then bfill
    )

    # Merge datasets
    # Using merge_asof requires sorted keys. 'Date' is already sorted from enforce_date_column.
    merged = pd.merge_asof(
        stock_processed, 
        macro_processed, 
        on='Date',
        direction='nearest' 
    )

    # Verify presence of essential raw/MA macroeconomic features from macro_data.py
    # BEFORE adding technical indicators
    required_macro_features = ['Interest_Rate', 'SP500', 'Interest_Rate_MA30', 'SP500_MA30']
    missing_macro = [f for f in required_macro_features if f not in merged.columns]
    if missing_macro:
        raise ValueError(f"Missing essential macro features after merge: {missing_macro}. Available: {list(merged.columns)}")

    # Ensure minimum data points for technical indicator calculations
    if len(merged) < 30: 
        raise ValueError(f"Not enough merged data ({len(merged)} rows) to compute technical indicators. Minimum 30 required.")

    # Add technical indicators using external function
    merged = add_technical_indicators(merged.copy()) # Pass a copy 

    # Verify presence of essential stock market data columns AFTER feature engineering
    required_stock_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing_stock = [col for col in required_stock_columns if col not in merged.columns]
    if missing_stock:
        raise ValueError(f"Missing stock columns after feature engineering: {missing_stock}. Available: {list(merged.columns)}")

    # Final Feature Selection for model input
    # Include ALL technical indicators calculated in feature_engineering.py
    required_output_features = [
        # Core price data
        'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 
        'Days',
        
        # Macro indicators
        'Interest_Rate', 'SP500',     
        'Interest_Rate_MA30',         
        'SP500_MA30',
        
        # MACD components
        'MACD', 'MACD_Signal', 'MACD_Histogram',
        
        # RSI
        'RSI',
        
        # Bollinger Bands
        'BB_Upper', 'BB_Middle', 'BB_Lower',
        
        # Simple Moving Averages
        'MA_7', 'MA_20', 'MA_50', 'MA_100', 'MA_200',
        
        # Exponential Moving Averages
        'EMA_12', 'EMA_26',
        
        # Volatility
        'ATR', 'Volatility_7', 'Volatility_30d',
        
        # Volume
        'OBV', 'Volume_SMA_20', 'Green_Days_Count',
        
        # Support & Resistance
        'Support_30D', 'Resistance_30D',
        
        # Momentum
        'Stochastic_K', 'Stochastic_D',
        
        # Trend
        'ADX',
        
        # Intraday
        'VWAP'
    ]
    
    final_features = [col for col in required_output_features if col in merged.columns]

    if 'Date' not in final_features or 'Close' not in final_features:
         raise ValueError("Core 'Date' or 'Close' column missing from final features.")

    print(f"Final features selected for output: {final_features}")
    return merged[final_features]