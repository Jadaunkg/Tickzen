# feature_engineering.py (MODIFIED)

import pandas as pd
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

def add_technical_indicators(data):
    """Create technical indicators with strict feature control"""
    if 'Date' not in data.columns:
        raise ValueError("Missing Date column in feature engineering input data")
    
    df = data.copy()  # Create a copy of the input DataFrame to avoid modifying the original
    
    # Add fallback if Volume is missing
    if 'Volume' not in df.columns:
        # Ensure 'Close' exists before trying to create synthetic volume
        if 'Close' not in df.columns:
            raise ValueError("Missing 'Close' column, cannot create synthetic 'Volume'")
        df['Volume'] = df['Close'].rolling(window=7, min_periods=1).mean() * 1000  # Synthetic volume, added min_periods
        
    # Calculate Market_Cap_Relative, requires 'SP500' from merged macro data
    if 'SP500' not in df.columns:
        raise ValueError("Missing 'SP500' column, cannot calculate 'Market_Cap_Relative'")
    if 'Close' not in df.columns: 
        raise ValueError("Missing 'Close' column, cannot calculate 'Market_Cap_Relative'")

    # Calculation for Market_Cap_Relative
    df['Market_Cap_Relative'] = (df['Close'] * df['Volume']) / df['SP500']
    # Replace infinity with NaN, then fill NaN with 0
    df['Market_Cap_Relative'] = df['Market_Cap_Relative'].replace([float('inf'), -float('inf')], float('nan')).fillna(0)


    # Clean column names (preserve macro columns and other specified columns)
    # These preserved columns are expected to be in the input 'data' if they need to be preserved.
    preserved_columns = ['Interest_Rate', 'SP500', 'Interest_Rate_MA30', 'SP500_MA30',
                         'Volatility_14', 'Momentum_7', 'Price_Diff'] 
    
    new_column_names = []   

    for col_name in df.columns: 
        if col_name in preserved_columns:
           new_column_names.append(col_name)
        else:
            new_column_names.append(str(col_name).split('_')[0] if '_' in str(col_name) else str(col_name))

    df.columns = new_column_names # Update DataFrame with cleaned column names
    
    # Validate essential price columns after potential renaming
    required_price_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'] 
    missing_price_columns = [col for col in required_price_columns if col not in df.columns] 
    if missing_price_columns:
        raise ValueError(f"Missing essential price columns after name cleaning: {missing_price_columns}. Available columns: {list(df.columns)}")
    
    # Convert 'Date' column to datetime format and sort the DataFrame by date
    df['Date'] = pd.to_datetime(df['Date']) 
    df = df.sort_values('Date').reset_index(drop=True) 
    
    # Technical indicators
    try:
        df['Close'] = pd.to_numeric(df['Close'], errors='raise')

        df['MACD'] = MACD(close=df['Close'], window_slow=26, window_fast=12, window_sign=9, fillna=False).macd() #
        df['RSI'] = RSIIndicator(close=df['Close'], window=14, fillna=False).rsi() #
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2, fillna=False) #
        df['BB_Upper'] = bb.bollinger_hband() #

        df['MA_7'] = df['Close'].rolling(window=7, min_periods=1).mean() #
        # Default min_periods is window size for std(), making it explicit. NaNs for first 6 periods.
        df['Volatility_7'] = df['Close'].rolling(window=7, min_periods=7).std() 
        
        df['Days'] = (df['Date'] - df['Date'].min()).dt.days #
    
    except KeyError as e: 
        raise ValueError(f"Missing 'Close' column for technical indicator calculation: {str(e)}")
    except Exception as e: 
        raise ValueError(f"Error calculating technical indicators: {e}")
        
    # Final validation for technical indicators
    expected_ta_features = ['MACD', 'RSI', 'BB_Upper', 'MA_7', 'Volatility_7', 'Days'] 
    missing_ta_features = [f for f in expected_ta_features if f not in df.columns] 
    if missing_ta_features:
        raise ValueError(f"Failed to create all expected technical indicators: {missing_ta_features}")
    
    df_cleaned = df.dropna() #
    
    if df_cleaned.empty:
        raise ValueError("DataFrame became empty after calculating technical indicators and dropping NaNs. Input data may be too short or unsuitable.")
        
    return df_cleaned