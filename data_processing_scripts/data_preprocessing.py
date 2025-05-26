import yfinance as yf
import pandas as pd

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
    data = data.rename(columns=column_map)

    # Handle date column

    date_cols = [col for col in data.columns if 'date' in str(col).lower()]
    if date_cols:
        data = data.rename(columns={date_cols[0]: 'Date'})
    
    # Convert and validate dates
    data['Date'] = pd.to_datetime(data['Date'], errors='coerce', utc=True).dt.tz_localize(None)
    data = data.dropna(subset=['Date']).sort_values('Date')

    # Validate required columns
    required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Data quality checks
    if len(data) < 100:
        raise ValueError(f"Need ≥100 data points (got {len(data)})")

    data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')
    if data['Volume'].mean() < 900:
        raise ValueError(f"Low liquidity (avg volume: {data['Volume'].mean():.0f})")

    return data[required]

#Ensuring DataFrame has a properly formatted “Date” column
import pandas as pd
from data_processing_scripts.feature_engineering import add_technical_indicators

def enforce_date_column(df, df_name):
    """Standardize date column across datasets"""
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"{df_name} data is not a DataFrame")
    
    # Clean column names similarly to fetch_stock_data
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() for col in df.columns]
        df.columns = [col.split('_')[0] for col in df.columns]
    
    # Find and rename date column
    date_cols = [col for col in df.columns if 'date' in str(col).lower()]
    if date_cols:
        df = df.rename(columns={date_cols[0]: 'Date'})
    elif 'Date' not in df.columns:
        raise ValueError(f"{df_name} data missing Date column")
    
    # Convert and validate dates
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce', utc=True)
    df['Date'] = df['Date'].dt.tz_localize(None)
    df = df.dropna(subset=['Date']).sort_values('Date')
    
    return df

#Preprocessing the data

def preprocess_data(stock_df, macro_df):
    """Merge and align stock data with macroeconomic data"""
    # Standardize both datasets
    stock = enforce_date_column(stock_df.copy(), "Stock")
    macro = enforce_date_column(macro_df.copy(), "Macro")

    # Rename stock columns (ensure consistency)
    stock = stock.rename(columns={
        'Open': 'Open', 'High': 'High', 'Low': 'Low',
        'Close': 'Close', 'Volume': 'Volume'
    })

    # Date Alignment
    start_date = max(stock['Date'].min(), macro['Date'].min())
    end_date = min(stock['Date'].max(), macro['Date'].max())
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    # Reindex and forward-fill missing values
    stock_processed = (
        stock.set_index('Date').reindex(date_range)
        .rename_axis('Date').ffill().bfill().reset_index()
    )
    macro_processed = (
        macro.set_index('Date').reindex(date_range)
        .rename_axis('Date').ffill().bfill().reset_index()
    )

    # Merge datasets
    merged = pd.merge_asof(
        stock_processed.sort_values('Date'),
        macro_processed.sort_values('Date'),
        on='Date',
        direction='nearest' # Or consider 'forward'/'backward' based on data needs
    )

    # Verify presence of essential raw/MA macroeconomic features from macro_data.py
    # BEFORE adding technical indicators
    required_macro_features = ['Interest_Rate', 'SP500', 'Interest_Rate_MA30', 'SP500_MA30']
    missing_macro = [f for f in required_macro_features if f not in merged.columns]
    if missing_macro:
        # It's better to raise an error if essential macro features are missing after merge
        raise ValueError(f"Missing essential macro features after merge: {missing_macro}")

    # Ensure minimum data points for technical indicator calculations
    if len(merged) < 30: # Adjust if needed for specific indicators
        raise ValueError(f"Not enough merged data ({len(merged)} rows) to compute technical indicators. Minimum 30 required.")

    # Add technical indicators using external function
    # This function should add 'Days', 'RSI', 'MACD', etc.
    merged = add_technical_indicators(merged)

    # Verify presence of essential stock market data columns AFTER feature engineering
    required_stock_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing_stock = [col for col in required_stock_columns if col not in merged.columns]
    if missing_stock:
        raise ValueError(f"Missing stock columns after feature engineering: {missing_stock}")

    # Final Feature Selection for model input
    # Define the *exact* list of columns needed by prophet_model.py
    # This includes 'Date', 'Close' and any regressors used ('RSI', 'MACD', 'Interest_Rate', etc.)
    # Also include OHLCV if needed by the report generator directly from this output
    required_output_features = [
        'Date', 'Open', 'High', 'Low', 'Close', 'Volume', # Base OHLCV for report
        'Days',                       # Time feature generated
        'Interest_Rate', 'SP500',     # Raw Macro needed?
        'Interest_Rate_MA30',         # Processed Macro needed?
        'SP500_MA30',                 # Processed Macro needed?
        # Technical Indicators generated in feature_engineering
        'RSI',
        'MACD',
        'BB_Upper',                   # Add BB if used as regressor or needed later
        'MA_7',                       # Add MA_7 if used as regressor or needed later
        'Volatility_7'                # Add Volatility_7 if used as regressor or needed later
    ]
    # Filter the list to only include columns that actually exist in 'merged'
    # This prevents errors if a feature failed to generate
    final_features = [col for col in required_output_features if col in merged.columns]

    # Check if core columns 'Date' and 'Close' are present
    if 'Date' not in final_features or 'Close' not in final_features:
         raise ValueError("Core 'Date' or 'Close' column missing from final features.")

    print(f"Final features selected: {final_features}")
    return merged[final_features] # Return only existing required features