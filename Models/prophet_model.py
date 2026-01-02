import platform
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

# Check if WSL usage is explicitly enabled via environment variable
USE_WSL_BRIDGE = os.environ.get('USE_WSL_PROPHET', 'false').lower() == 'true'

# Always try to import native Prophet first (works on Windows with Prophet 1.1+)
try:
    from prophet import Prophet
    import pandas as pd
    import re
    logger.info("Using native Prophet (direct Windows support)")
    PROPHET_AVAILABLE = True
except (ImportError, AttributeError) as e:
    logger.warning(f"Native Prophet not available (may be NumPy compatibility issue): {e}")
    PROPHET_AVAILABLE = False
    import pandas as pd
    import re

# Try to import WSL bridge as backup for Windows CmdStan issues
WSL_BRIDGE_AVAILABLE = False
wsl_train_prophet_model = None

if platform.system() == 'Windows':
    try:
        # Try relative import first
        from .wsl_prophet_bridge import train_prophet_model as wsl_train_prophet_model
        logger.info("WSL Prophet Bridge loaded as fallback option")
        WSL_BRIDGE_AVAILABLE = True
    except ImportError:
        try:
            # Try absolute import
            import wsl_prophet_bridge
            wsl_train_prophet_model = wsl_prophet_bridge.train_prophet_model
            logger.info("WSL Prophet Bridge loaded as fallback option (absolute import)")
            WSL_BRIDGE_AVAILABLE = True
        except ImportError as e:
            logger.info(f"WSL Prophet Bridge not available: {e}. Will be loaded on demand if needed.")

# Ensure we have at least one Prophet implementation available
if not PROPHET_AVAILABLE and platform.system() != 'Windows':
    # On non-Windows systems, require native Prophet
    raise ImportError("Prophet is not available. Please install: pip install prophet")
elif not PROPHET_AVAILABLE and platform.system() == 'Windows':
    # On Windows, we can use WSL bridge as fallback
    logger.info("Native Prophet unavailable on Windows, will use WSL bridge as needed")


# ------------------ Helper Function ------------------
def parse_time_period(time_period: str) -> int:
    """
    Converts a custom time-period string into a number of days.
    See docstring above.
    """
    time_period = time_period.lower().strip()
    pattern = r"(\d+)([dwmy])"
    match = re.match(pattern, time_period)
    if not match:
        raise ValueError("Invalid time period format. Please use e.g., '15d', '1m', '1y'.")
    value = int(match.group(1))
    unit = match.group(2)
    if unit == 'd':
        return value
    elif unit == 'w':
        return value * 7
    elif unit == 'm':
        return value * 30
    elif unit == 'y':
        return value * 365
    else:
        raise ValueError("Unsupported time unit. Supported: d, w, m, y.")

# ------------------ Main Training Function ------------------
def train_prophet_model(data, ticker='STOCK', forecast_horizon='1y', timestamp=None, macro_data=None):
    """
    Train a Prophet model for stock price forecasting with a custom forecast horizon.

    Args:
        data (pd.DataFrame): Data containing at least the ['Date', 'Close'] columns.
        ticker (str): Stock ticker for applying ticker-specific parameter tuning.
        forecast_horizon (str): Forecast period as a string (e.g. '15d', '1m', '3m', '6m', '1y', '2y', '5y').
        timestamp (optional): Used for report generation.

    Returns:
        model (Prophet or None): The fitted model (None if using WSL bridge).
        forecast (pd.DataFrame): Forecasted results.
        agg_actual (pd.DataFrame): Aggregated actual data.
        agg_forecast (pd.DataFrame): Aggregated forecast data.
    """
    # Try native Prophet first, fall back to WSL on Windows CmdStan errors or NumPy issues
    if PROPHET_AVAILABLE:
        try:
            # Use native Prophet (default)
            return _train_prophet_model_native(data, ticker, forecast_horizon, timestamp, macro_data)
        except RuntimeError as e:
            # Check if this is a Windows CmdStan error (signal 3221225657 or optimization error)
            error_msg = str(e).lower()
            if (platform.system() == 'Windows' and 
                ('terminated by signal' in error_msg or 'error during optimization' in error_msg)):
                logger.warning(f"Native Prophet failed on Windows (CmdStan error): {e}")
                logger.info("Attempting fallback to WSL Prophet Bridge...")
                # Try WSL bridge as fallback
                return _train_prophet_model_wsl(data, ticker, forecast_horizon, timestamp, macro_data)
            else:
                # Re-raise other types of errors
                raise
        except (AttributeError, ImportError) as e:
            # Handle NumPy compatibility or other import errors
            if platform.system() == 'Windows':
                logger.warning(f"Native Prophet failed (compatibility issue): {e}. Trying WSL fallback...")
                return _train_prophet_model_wsl(data, ticker, forecast_horizon, timestamp, macro_data)
            else:
                raise
        except Exception as e:
            # Log other exceptions but still try WSL fallback on Windows
            if platform.system() == 'Windows':
                logger.warning(f"Native Prophet failed: {e}. Trying WSL fallback...")
                return _train_prophet_model_wsl(data, ticker, forecast_horizon, timestamp, macro_data)
            else:
                raise
    else:
        # Use WSL bridge if native Prophet not available (NumPy 2.0 compatibility issue)
        logger.info("Native Prophet unavailable, using WSL bridge")
        return _train_prophet_model_wsl(data, ticker, forecast_horizon, timestamp, macro_data)

def _train_prophet_model_wsl(data, ticker='STOCK', forecast_horizon='1y', timestamp=None, macro_data=None):
    """
    Train Prophet model using WSL bridge
    """
    global wsl_train_prophet_model, WSL_BRIDGE_AVAILABLE
    
    # Load WSL bridge if not already loaded
    if not WSL_BRIDGE_AVAILABLE or wsl_train_prophet_model is None:
        try:
            # Try relative import first
            from .wsl_prophet_bridge import train_prophet_model as wsl_train_prophet_model
            logger.info("Loaded WSL Prophet Bridge on demand")
            WSL_BRIDGE_AVAILABLE = True
        except ImportError:
            try:
                # Try absolute import
                import wsl_prophet_bridge
                wsl_train_prophet_model = wsl_prophet_bridge.train_prophet_model
                logger.info("Loaded WSL Prophet Bridge on demand (absolute import)")
                WSL_BRIDGE_AVAILABLE = True
            except ImportError as e:
                raise RuntimeError(f"WSL Prophet Bridge is required but not available: {e}")
    
    # ----- Preliminary Check and Basic Preprocessing -----
    required_columns = ['Date', 'Close']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    # Ensure date is in proper format.
    data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
    data = data.dropna(subset=['Date'])

    # ----- Parameter Tuning for Different Tickers -----
    ticker_params = {
        'TSLA': {
            'cap_multiplier': 2.5,
            'changepoint_prior_scale': 0.05,
            'seasonality_mode': 'multiplicative'
        },
        'AAPL': {
            'cap_multiplier': 2.0,
            'changepoint_prior_scale': 0.1,
            'seasonality_mode': 'multiplicative'
        }
    }
    params = ticker_params.get(ticker, {
        'cap_multiplier': 2.0,
        'changepoint_prior_scale': 0.08,
        'seasonality_mode': 'multiplicative'
    })
    cap_multiplier = params['cap_multiplier']
    changepoint_prior_scale = params['changepoint_prior_scale']
    seasonality_mode = params['seasonality_mode']

    # ----- Special Handling (e.g., TSLA stock split adjustment) -----
    if ticker == 'TSLA':
        split_date = pd.to_datetime('2020-08-31')
        data.loc[data['Date'] < split_date, 'Close'] *= 5

    # ----- Dynamic Cap Calculation -----
    max_price = data['Close'].max() * cap_multiplier
    data['cap'] = max_price
    data['floor'] = 0

    # ----- Prepare Data for Prophet -----
    df = data.rename(columns={'Date': 'ds', 'Close': 'y'})
    df['ds'] = pd.to_datetime(df['ds'])
    df['cap'] = max_price
    df['floor'] = 0

    # ----- Model Parameters for WSL -----
    model_params = {
        'growth': 'logistic',
        'yearly_seasonality': True,
        'weekly_seasonality': True,
        'changepoint_prior_scale': changepoint_prior_scale,
        'seasonality_mode': seasonality_mode,
        'uncertainty_samples': 5
    }

    # ----- Add Regressors if Present -----
    regressor_features = ['RSI', 'MACD', 'Interest_Rate']
    available_regressors = [feature for feature in regressor_features if feature in df.columns]

    # ----- Convert Forecast Horizon (String) to Days -----
    forecast_days = parse_time_period(forecast_horizon)

    # ----- Use WSL Bridge -----
    try:
        model, forecast, actual_df = wsl_train_prophet_model(df, model_params, forecast_days, available_regressors)
        logger.info("Successfully trained Prophet model using WSL bridge")
    except Exception as e:
        logger.error(f"WSL Prophet training failed: {e}")
        raise

    # ----- Post-process Predictions -----
    forecast['yhat'] = forecast['yhat'].clip(lower=0)
    forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=0)
    forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=0)

    # ----- Aggregate Data for Reporting -----
    last_date = df['ds'].max()
    current_date = pd.Timestamp.now()

    # Choose aggregation frequency based on forecast period
    if forecast_days <= 30:
        start_date = last_date - pd.Timedelta(days=15)
        agg_format = 'daily'
        df_recent = df[df['ds'] >= start_date].copy()
        df_recent['Period'] = df_recent['ds'].dt.strftime('%Y-%m-%d')
    elif forecast_days <= 90:
        start_date = last_date - pd.DateOffset(months=3)
        agg_format = 'weekly'
        df_recent = df[df['ds'] >= start_date].copy()
        df_recent = df_recent.set_index('ds').resample('W').mean().reset_index()
        df_recent['Period'] = df_recent['ds'].dt.strftime('%Y-%m-%d')
    else:
        start_date = last_date - pd.DateOffset(months=8)
        agg_format = 'monthly'
        df_recent = df[df['ds'] >= start_date].copy()
        df_recent['Period'] = df_recent['ds'].dt.to_period('M').dt.strftime('%Y-%m')

    # Aggregate actual historical prices with special handling for current month
    if agg_format == 'monthly':
        # For monthly aggregation, handle current month specially
        current_month = current_date.to_period('M').strftime('%Y-%m')

        # Group by period and calculate aggregates
        period_groups = df_recent.groupby('Period')

        agg_data = []
        for period, group in period_groups:
            if period == current_month:
                # For current month, use the most recent price instead of average
                latest_price = group['y'].iloc[-1]  # Most recent price in current month
                agg_data.append({'Period': period, 'Average': latest_price})
            else:
                # For past months, use average
                avg_price = group['y'].mean()
                agg_data.append({'Period': period, 'Average': avg_price})

        agg_actual = pd.DataFrame(agg_data)
    else:
        # For daily/weekly, use regular aggregation
        agg_actual = df_recent.groupby('Period').agg({'y': 'mean'}).reset_index()
        agg_actual.rename(columns={'y': 'Average'}, inplace=True)

    # Aggregate the forecasted data.
    forecast_future = forecast[forecast['ds'] >= last_date].copy()
    if agg_format == 'daily':
        forecast_future['Period'] = forecast_future['ds'].dt.strftime('%Y-%m-%d')
    elif agg_format == 'weekly':
        forecast_future = forecast_future.set_index('ds').resample('W').mean().reset_index()
        forecast_future['Period'] = forecast_future['ds'].dt.strftime('%Y-%m-%d')
    else:  # monthly
        forecast_future['Period'] = forecast_future['ds'].dt.to_period('M').dt.strftime('%Y-%m')

    agg_forecast = forecast_future.groupby('Period').agg({
        'yhat_lower': 'min',
        'yhat': 'mean',
        'yhat_upper': 'max'
    }).reset_index()
    agg_forecast.rename(columns={
        'yhat_lower': 'Low',
        'yhat': 'Average',
        'yhat_upper': 'High'
    }, inplace=True)

    # Smooth the transition: set the first forecast period equal to last actual average.
    if not agg_actual.empty and not agg_forecast.empty:
        last_actual_value = agg_actual['Average'].iloc[-1]
        agg_forecast.loc[agg_forecast.index[0], ['Low', 'Average', 'High']] = last_actual_value

    return model, forecast, agg_actual, agg_forecast

def _train_prophet_model_native(data, ticker='STOCK', forecast_horizon='1y', timestamp=None, macro_data=None):
    """
    Train Prophet model using native implementation (original code)
    """
    # ----- Preliminary Check and Basic Preprocessing -----
    required_columns = ['Date', 'Close']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Ensure date is in proper format.
    data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
    data = data.dropna(subset=['Date'])

    # ----- Parameter Tuning for Different Tickers -----
    ticker_params = {
        'TSLA': {
            'cap_multiplier': 2.5,
            'changepoint_prior_scale': 0.05,
            'seasonality_mode': 'multiplicative'
        },
        'AAPL': {
            'cap_multiplier': 2.0,
            'changepoint_prior_scale': 0.1,
            'seasonality_mode': 'multiplicative'
        }
    }
    params = ticker_params.get(ticker, {
        'cap_multiplier': 2.0,
        'changepoint_prior_scale': 0.08,
        'seasonality_mode': 'multiplicative'
    })
    cap_multiplier = params['cap_multiplier']
    changepoint_prior_scale = params['changepoint_prior_scale']
    seasonality_mode = params['seasonality_mode']

    # ----- Special Handling (e.g., TSLA stock split adjustment) -----
    if ticker == 'TSLA':
        split_date = pd.to_datetime('2020-08-31')
        data.loc[data['Date'] < split_date, 'Close'] *= 5

    # ----- Dynamic Cap Calculation -----
    max_price = data['Close'].max() * cap_multiplier
    data['cap'] = max_price
    data['floor'] = 0

    # ----- Prepare Data for Prophet -----
    df = data.rename(columns={'Date': 'ds', 'Close': 'y'})
    df['ds'] = pd.to_datetime(df['ds'])
    df['cap'] = max_price
    df['floor'] = 0

    # ----- Initialize Prophet Model -----
    model = Prophet(
        growth='logistic',
        yearly_seasonality=True,
        weekly_seasonality=True,
        changepoint_prior_scale=changepoint_prior_scale,
        seasonality_mode=seasonality_mode,
        uncertainty_samples=5
    )

    # ----- Add Regressors if Present -----
    regressor_features = ['RSI', 'MACD', 'Interest_Rate']
    for feature in regressor_features:
        if feature in df.columns:
            model.add_regressor(feature)

    # ----- Fit the Model on Historical Data -----
    model.fit(df)

    # ----- Convert Forecast Horizon (String) to Days -----
    forecast_days = parse_time_period(forecast_horizon)
    
    # ----- Create Future DataFrame -----
    future = model.make_future_dataframe(periods=forecast_days)
    future['cap'] = max_price
    future['floor'] = 0

    # ----- Set Future Regressor Values -----
    for feature in regressor_features:
        if feature in df.columns:
            if len(df) >= 7:
                future[feature] = df[feature].iloc[-7:].mean()
            else:
                future[feature] = df[feature].iloc[-1]

    # ----- Forecast and Post-process Predictions -----
    forecast = model.predict(future)
    forecast['yhat'] = forecast['yhat'].clip(lower=0)
    forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=0)
    forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=0)

    # ----- Aggregate Data for Reporting with Custom Grouping -----
    last_date = df['ds'].max()
    current_date = pd.Timestamp.now()
    
    # Choose aggregation frequency based on forecast period
    if forecast_days <= 30:
        # Daily grouping: use last 15 days (for example) from historical data
        start_date = last_date - pd.Timedelta(days=15)
        agg_format = 'daily'
        df_recent = df[df['ds'] >= start_date].copy()
        df_recent['Period'] = df_recent['ds'].dt.strftime('%Y-%m-%d')
    elif forecast_days <= 90:
        # Weekly grouping: use roughly last 3 months
        start_date = last_date - pd.DateOffset(months=3)
        agg_format = 'weekly'
        df_recent = df[df['ds'] >= start_date].copy()
        df_recent = df_recent.set_index('ds').resample('W').mean().reset_index()
        df_recent['Period'] = df_recent['ds'].dt.strftime('%Y-%m-%d')
    else:
        # Monthly grouping: use roughly last 8 months
        start_date = last_date - pd.DateOffset(months=8)
        agg_format = 'monthly'
        df_recent = df[df['ds'] >= start_date].copy()
        df_recent['Period'] = df_recent['ds'].dt.to_period('M').dt.strftime('%Y-%m')

    # Aggregate actual historical prices with special handling for current month
    if agg_format == 'monthly':
        # For monthly aggregation, handle current month specially
        current_month = current_date.to_period('M').strftime('%Y-%m')

        # Group by period and calculate aggregates
        period_groups = df_recent.groupby('Period')

        agg_data = []
        for period, group in period_groups:
            if period == current_month:
                # For current month, use the most recent price instead of average
                latest_price = group['y'].iloc[-1]  # Most recent price in current month
                agg_data.append({'Period': period, 'Average': latest_price})
            else:
                # For past months, use average
                avg_price = group['y'].mean()
                agg_data.append({'Period': period, 'Average': avg_price})

        agg_actual = pd.DataFrame(agg_data)
    else:
        # For daily/weekly, use regular aggregation
        agg_actual = df_recent.groupby('Period').agg({'y': 'mean'}).reset_index()
        agg_actual.rename(columns={'y': 'Average'}, inplace=True)

    # Similarly, aggregate the forecasted data.
    forecast_future = forecast[forecast['ds'] >= last_date].copy()
    if agg_format == 'daily':
        forecast_future['Period'] = forecast_future['ds'].dt.strftime('%Y-%m-%d')
    elif agg_format == 'weekly':
        forecast_future = forecast_future.set_index('ds').resample('W').mean().reset_index()
        forecast_future['Period'] = forecast_future['ds'].dt.strftime('%Y-%m-%d')
    else:  # monthly
        forecast_future['Period'] = forecast_future['ds'].dt.to_period('M').dt.strftime('%Y-%m')
    
    agg_forecast = forecast_future.groupby('Period').agg({
        'yhat_lower': 'min',
        'yhat': 'mean',
        'yhat_upper': 'max'
    }).reset_index()
    agg_forecast.rename(columns={
        'yhat_lower': 'Low',
        'yhat': 'Average',
        'yhat_upper': 'High'
    }, inplace=True)
    
    # Smooth the transition: set the first forecast period equal to last actual average.
    if not agg_actual.empty and not agg_forecast.empty:
        last_actual_value = agg_actual['Average'].iloc[-1]
        agg_forecast.loc[agg_forecast.index[0], ['Low', 'Average', 'High']] = last_actual_value

    # ----- Prepare Historical Data for Report Generation -----
    historical_data = data.copy()
    historical_data['Date'] = pd.to_datetime(historical_data['Date'])


    return model, forecast, agg_actual, agg_forecast