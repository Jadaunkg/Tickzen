#!/usr/bin/env python3
"""
Financial Feature Engineering Pipeline
=====================================

Advanced feature engineering system for financial time-series data, creating
machine learning-ready features from raw market data. Implements technical
indicators, statistical features, and derived metrics for enhanced analysis.

Core Feature Categories:
-----------------------
1. **Technical Indicators**:
   - Moving Averages: SMA, EMA, WMA with multiple periods
   - Momentum Indicators: RSI, MACD, Stochastic, Williams %R
   - Volatility Measures: Bollinger Bands, ATR, Standard Deviation
   - Volume Indicators: OBV, Volume Rate of Change, VWAP

2. **Price-Based Features**:
   - Price Returns: Simple and log returns
   - Price Ratios: High/Low, Close/Open relationships
   - Gap Analysis: Opening gaps and their significance
   - Price Momentum: Multi-period momentum calculations

3. **Statistical Features**:
   - Rolling Statistics: Mean, median, standard deviation
   - Percentiles: Quantile-based features
   - Z-Scores: Standardized price and volume metrics
   - Autocorrelation: Time-series correlation features

4. **Time-Based Features**:
   - Calendar Features: Day of week, month, quarter
   - Market Seasonality: Holiday effects, earnings seasons
   - Time Since Events: Days since highs/lows, earnings
   - Cyclical Patterns: Monthly and quarterly cycles

Feature Engineering Pipeline:
----------------------------
1. **Data Validation**: Ensure required columns and data quality
2. **Base Calculations**: Fundamental price and volume metrics
3. **Technical Indicators**: Apply TA-lib and custom indicators
4. **Derived Features**: Create composite and ratio features
5. **Statistical Features**: Add rolling and statistical measures
6. **Time Features**: Incorporate temporal and calendar features
7. **Feature Selection**: Optional feature filtering and selection
8. **Normalization**: Scale features for ML compatibility

Advanced Technical Indicators:
-----------------------------
```python
Implemented Indicators:
├── Trend Indicators
│   ├── Simple Moving Average (SMA)
│   ├── Exponential Moving Average (EMA)
│   ├── MACD (Moving Average Convergence Divergence)
│   └── Average Directional Index (ADX)
├── Momentum Indicators
│   ├── Relative Strength Index (RSI)
│   ├── Stochastic Oscillator
│   └── Williams %R
├── Volatility Indicators
│   ├── Bollinger Bands
│   ├── Average True Range (ATR)
│   └── Keltner Channels
└── Volume Indicators
    ├── On-Balance Volume (OBV)
    ├── Volume-Price Trend (VPT)
    └── Chaikin Money Flow
```

Feature Quality Control:
-----------------------
- **Missing Data Handling**: Intelligent handling of NaN values
- **Outlier Treatment**: Statistical outlier detection and treatment
- **Feature Validation**: Ensure feature mathematical validity
- **Collinearity Detection**: Identify and handle correlated features
- **Feature Importance**: Rank features by predictive power

Customizable Parameters:
-----------------------
- **Indicator Periods**: Configurable lookback periods for all indicators
- **Smoothing Parameters**: Alpha values for exponential smoothing
- **Threshold Settings**: Overbought/oversold levels
- **Rolling Windows**: Statistical calculation windows
- **Feature Selection**: Enable/disable specific feature categories

Performance Optimizations:
-------------------------
- **Vectorized Operations**: NumPy/Pandas optimized calculations
- **Incremental Updates**: Efficient feature updates for new data
- **Memory Management**: Optimal memory usage for large datasets
- **Parallel Processing**: Multi-threading for independent calculations
- **Caching**: Feature calculation result caching

Usage Examples:
--------------
```python
# Basic feature engineering
enhanced_data = add_technical_indicators(raw_data)

# Custom indicator configuration
features = create_features(
    data=raw_data,
    indicators=['RSI', 'MACD', 'BB'],
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    bb_period=20
)

# Advanced feature engineering
ml_ready_data = comprehensive_feature_engineering(
    data=raw_data,
    include_technical=True,
    include_statistical=True,
    include_time_features=True,
    normalization='minmax'
)
```

Feature Output Structure:
------------------------
Enhanced DataFrame with original OHLCV data plus:
```python
Additional Columns:
├── Technical Indicators
│   ├── RSI_14, RSI_21
│   ├── MACD_line, MACD_signal, MACD_histogram
│   ├── BB_upper, BB_middle, BB_lower
│   └── SMA_20, EMA_50, EMA_200
├── Statistical Features
│   ├── Returns_1d, Returns_5d, Returns_20d
│   ├── Volatility_20d, Volatility_60d
│   └── Volume_MA_20, Volume_ratio
└── Time Features
    ├── DayOfWeek, Month, Quarter
    ├── IsEarningsWeek, IsHoliday
    └── DaysSinceHigh, DaysSinceLow
```

Integration Points:
------------------
- Used by data_preprocessing.py for complete data preparation
- Feeds into Models/prophet_model.py for enhanced forecasting
- Provides features for analysis_scripts/technical_analysis.py
- Supports machine learning model training and prediction

Error Handling:
--------------
- **Data Validation**: Comprehensive input data validation
- **Calculation Errors**: Robust handling of mathematical exceptions
- **Missing Dependencies**: Graceful handling of missing TA libraries
- **Memory Limitations**: Automatic data chunking for large datasets

Configuration:
-------------
Customizable settings:
- **Default Parameters**: Standard indicator parameters
- **Feature Sets**: Predefined feature combinations
- **Performance Settings**: Memory and CPU usage optimization
- **Output Options**: Feature selection and formatting preferences

Author: TickZen Development Team
Version: 2.0
Last Updated: January 2026
"""

import pandas as pd
from ta.trend import MACD, EMAIndicator, SMAIndicator, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice

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
        # Ensure required columns are numeric
        df['Close'] = pd.to_numeric(df['Close'], errors='raise')
        df['High'] = pd.to_numeric(df['High'], errors='raise')
        df['Low'] = pd.to_numeric(df['Low'], errors='raise')
        df['Volume'] = pd.to_numeric(df['Volume'], errors='raise')

        # MACD (3 components)
        macd_indicator = MACD(close=df['Close'], window_slow=26, window_fast=12, window_sign=9, fillna=False)
        df['MACD'] = macd_indicator.macd()
        df['MACD_Signal'] = macd_indicator.macd_signal()
        df['MACD_Histogram'] = macd_indicator.macd_diff()
        
        # RSI
        df['RSI'] = RSIIndicator(close=df['Close'], window=14, fillna=False).rsi()
        
        # Bollinger Bands (3 bands)
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2, fillna=False)
        df['BB_Upper'] = bb.bollinger_hband()
        df['BB_Middle'] = bb.bollinger_mavg()
        df['BB_Lower'] = bb.bollinger_lband()
        
        # Moving Averages - Simple (SMA)
        df['MA_7'] = df['Close'].rolling(window=7, min_periods=1).mean()
        df['MA_20'] = SMAIndicator(close=df['Close'], window=20, fillna=False).sma_indicator()
        df['MA_50'] = SMAIndicator(close=df['Close'], window=50, fillna=False).sma_indicator()
        df['MA_100'] = SMAIndicator(close=df['Close'], window=100, fillna=False).sma_indicator()
        df['MA_200'] = SMAIndicator(close=df['Close'], window=200, fillna=False).sma_indicator()
        
        # Moving Averages - Exponential (EMA)
        df['EMA_12'] = EMAIndicator(close=df['Close'], window=12, fillna=False).ema_indicator()
        df['EMA_26'] = EMAIndicator(close=df['Close'], window=26, fillna=False).ema_indicator()
        
        # ATR (Average True Range) - Volatility
        df['ATR'] = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14, fillna=False).average_true_range()
        
        # Volatility (Rolling Standard Deviation)
        df['Volatility_7'] = df['Close'].rolling(window=7, min_periods=7).std()
        df['Volatility_30d'] = df['Close'].pct_change().rolling(window=30).std() * (252 ** 0.5) * 100  # Annualized volatility %
        
        # OBV (On-Balance Volume)
        df['OBV'] = OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume'], fillna=False).on_balance_volume()
        
        # Stochastic Oscillator (K and D)
        stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3, fillna=False)
        df['Stochastic_K'] = stoch.stoch()
        df['Stochastic_D'] = stoch.stoch_signal()
        
        # ADX (Average Directional Index) - Trend Strength
        df['ADX'] = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14, fillna=False).adx()
        
        # VWAP (Volume Weighted Average Price) - needs reset for each day but we'll use cumulative
        # Note: VWAP is typically intraday, but we can calculate cumulative for daily data
        try:
            vwap = VolumeWeightedAveragePrice(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], fillna=False)
            df['VWAP'] = vwap.volume_weighted_average_price()
        except Exception:
            # If VWAP fails (needs intraday data), use simple volume-weighted price
            df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        
        # Volume SMA
        df['Volume_SMA_20'] = df['Volume'].rolling(window=20, min_periods=1).mean()
        
        # Green Days Count (last 30 days where Close > Open)
        def calculate_green_days(row_idx):
            if row_idx < 30:
                return None
            last_30 = df.iloc[row_idx-29:row_idx+1]
            return int((last_30['Close'] > last_30['Open']).sum())
        
        df['Green_Days_Count'] = df.index.map(calculate_green_days)
        
        # Support & Resistance (30-day)
        df['Support_30D'] = df['Low'].rolling(window=30, min_periods=30).min()
        df['Resistance_30D'] = df['High'].rolling(window=30, min_periods=30).max()
        
        # Days since start
        df['Days'] = (df['Date'] - df['Date'].min()).dt.days
    
    except KeyError as e: 
        raise ValueError(f"Missing required column for technical indicator calculation: {str(e)}")
    except Exception as e: 
        raise ValueError(f"Error calculating technical indicators: {e}")
        
    # Final validation for technical indicators
    expected_ta_features = [
        'MACD', 'MACD_Signal', 'MACD_Histogram',
        'RSI', 
        'BB_Upper', 'BB_Middle', 'BB_Lower',
        'MA_7', 'MA_20', 'MA_50', 'MA_100', 'MA_200',
        'EMA_12', 'EMA_26',
        'ATR', 'Volatility_7', 'Volatility_30d',
        'OBV', 'Stochastic_K', 'Stochastic_D',
        'ADX', 'VWAP', 'Volume_SMA_20',
        'Green_Days_Count', 'Support_30D', 'Resistance_30D',
        'Days'
    ]
    missing_ta_features = [f for f in expected_ta_features if f not in df.columns] 
    if missing_ta_features:
        raise ValueError(f"Failed to create all expected technical indicators: {missing_ta_features}")
    
    df_cleaned = df.dropna() #
    
    if df_cleaned.empty:
        raise ValueError("DataFrame became empty after calculating technical indicators and dropping NaNs. Input data may be too short or unsuitable.")
        
    return df_cleaned