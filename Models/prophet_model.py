from prophet import Prophet
import pandas as pd
import re


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
        model (Prophet): The fitted model.
        forecast (pd.DataFrame): Forecasted results.
        report_path (str): Path to the generated report.
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

    # Aggregate actual historical prices.
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