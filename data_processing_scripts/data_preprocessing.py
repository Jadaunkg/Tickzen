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
    start_date = max(stock['Date'].min(), macro['Date'].min())
    end_date = min(stock['Date'].max(), macro['Date'].max())
    
    if start_date > end_date:
        raise ValueError(f"Date range misalignment: Stock data range {stock['Date'].min()} to {stock['Date'].max()}, Macro data range {macro['Date'].min()} to {macro['Date'].max()}. No overlapping period found.")

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
    required_output_features = [
        'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 
        'Days',                       
        'Interest_Rate', 'SP500',     
        'Interest_Rate_MA30',         
        'SP500_MA30',                 
        'RSI',                        
        'MACD',                       
        'BB_Upper',                   
        'MA_7',                       
        'Volatility_7'                
    ]
    
    final_features = [col for col in required_output_features if col in merged.columns]

    if 'Date' not in final_features or 'Close' not in final_features:
         raise ValueError("Core 'Date' or 'Close' column missing from final features.")

    print(f"Final features selected for output: {final_features}")
    return merged[final_features]