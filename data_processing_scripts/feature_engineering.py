import pandas as pd
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

def add_technical_indicators(data):
    """Create technical indicators with strict feature control"""
    if 'Date' not in data.columns:
        raise ValueError("Missing Date column in feature engineering")
    
    df = data.copy()  # Create a copy of the input DataFrame to avoid modifying the original
    # Add fallback if Volume is missing
    if 'Volume' not in df.columns:
        df['Volume'] = df['Close'].rolling(7).mean() * 1000  # Synthetic volume
    
    df['Market_Cap_Relative'] = (df['Close'] * df['Volume']) / df['SP500']
    df['Market_Cap_Relative'] = df['Market_Cap_Relative'].fillna(0)


    # Clean column names (preserve macro columns)
    preserved = ['Interest_Rate', 'SP500', 'Interest_Rate_MA30', 'SP500_MA30',
             'Volatility_14', 'Momentum_7', 'Price_Diff']
    new_columns = []   # Initialize a list to hold new column names

    # Loop through existing columns to clean names
    for col in df.columns:
        if col in preserved:
           new_columns.append(col)
        else:
            # If the column name contains an underscore, take the part before it; otherwise, keep the name
            new_columns.append(col.split('_')[0] if '_' in str(col) else col)

    df.columns = new_columns # Update DataFrame with cleaned column names
    
    # Validate essential price columns
    required_price = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required_price if col not in df.columns]
    if missing:
        raise ValueError(f"Missing price columns: {missing}")
    
    # Convert 'Date' column to datetime format and sort the DataFrame by date
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Technical indicators
    try:
        # Calculate existing features using the ta library
        df['MACD'] = MACD(df['Close'], 26, 12, 9).macd()
        df['RSI'] = RSIIndicator(df['Close'], 14).rsi()
        bb = BollingerBands(df['Close'], 20, 2)
        df['BB_Upper'] = bb.bollinger_hband()
        df['MA_7'] = df['Close'].rolling(7, min_periods=1).mean()
        df['Volatility_7'] = df['Close'].rolling(7).std()
        #df['Lag_1'] = df['Close'].shift(1).bfill()
        df['Days'] = (df['Date'] - df['Date'].min()).dt.days
    except Exception as e:
        raise ValueError(f"Error calculating technical indicators: {e}")
        
    except KeyError as e:
        raise ValueError(f"Missing required price column: {str(e)}")
    
    # Final validation for technical indicators
    missing_features = [f for f in ['MACD', 'RSI', 'BB_Upper', 'MA_7', 'Volatility_7', 'Days'] 
                       if f not in df.columns]
    if missing_features:
        raise ValueError(f"Failed to create indicators: {missing_features}")
    
    return df.dropna() # Return the DataFrame after dropping any rows with NaN values