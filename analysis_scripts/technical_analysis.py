# technical_analysis.py 
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import timedelta # Import timedelta

# --- NEW: Import Matplotlib ---
import matplotlib
matplotlib.use('Agg') # Use Agg backend for non-interactive plotting
import matplotlib.pyplot as plt
import matplotlib.dates as mdates # For date formatting

# --- Calculation Functions (Keep as before) ---
def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    if data.isnull().all() or len(data) < window + 1: return pd.Series(index=data.index, dtype=float)
    delta = data.diff(); gain = (delta.where(delta > 0, 0)).rolling(window=window).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    # Add small epsilon to prevent division by zero if loss is consistently zero
    loss = loss.replace(0, 1e-10)
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs));
    return rsi

def calculate_macd(data: pd.Series, fast_window: int = 12, slow_window: int = 26, signal_window: int = 9):
    if data.isnull().all() or len(data) < slow_window: empty_series = pd.Series(index=data.index, dtype=float); return empty_series, empty_series, empty_series
    ema_fast = data.ewm(span=fast_window, adjust=False).mean(); ema_slow = data.ewm(span=slow_window, adjust=False).mean(); macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_window, adjust=False).mean(); histogram = macd_line - signal_line; return macd_line, signal_line, histogram

def calculate_bollinger_bands(data: pd.Series, window: int = 20, num_std: int = 2):
    if data.isnull().all() or len(data) < window: empty_series = pd.Series(index=data.index, dtype=float); return empty_series, empty_series, empty_series
    middle_band = data.rolling(window=window).mean(); std_dev = data.rolling(window=window).std(); upper_band = middle_band + (std_dev * num_std)
    lower_band = middle_band - (std_dev * num_std); return upper_band, middle_band, lower_band

def calculate_sma(data: pd.Series, window: int) -> pd.Series:
    if data.isnull().all() or len(data) < window: return pd.Series(index=data.index, dtype=float)
    return data.rolling(window=window).mean()

def calculate_volume_sma(data: pd.DataFrame, window: int) -> pd.Series: # Changed input to DataFrame
    if 'Volume' not in data.columns or data['Volume'].isnull().all() or len(data) < window: return pd.Series(index=data.index, dtype=float)
    return data['Volume'].rolling(window=window).mean()

# --- Conclusion Generation Functions (Keep as before) ---
def get_rsi_conclusion(rsi_value):
    if pd.isna(rsi_value): return "RSI data not available."
    if rsi_value > 70: return f"RSI ({rsi_value:.1f}) is above 70, suggesting potential overbought conditions. This could indicate a higher chance of a price pullback or consolidation."
    elif rsi_value < 30: return f"RSI ({rsi_value:.1f}) is below 30, suggesting potential oversold conditions. This could indicate a higher chance of a price rebound."
    else: return f"RSI ({rsi_value:.1f}) is in the neutral zone (30-70), indicating balanced momentum."

def get_macd_conclusion(macd_line_now, signal_line_now, histogram_now, histogram_prev):
    if pd.isna(macd_line_now) or pd.isna(signal_line_now) or pd.isna(histogram_now) or pd.isna(histogram_prev): return "MACD data not available or insufficient for comparison."
    conclusion = ""
    # Check for crossovers using the sign of the histogram
    if histogram_now > 0 and histogram_prev <= 0:
        conclusion += "A bullish MACD crossover (histogram crossing above zero) may have recently occurred, suggesting potential upward momentum. "
    elif histogram_now < 0 and histogram_prev >= 0:
        conclusion += "A bearish MACD crossover (histogram crossing below zero) may have recently occurred, suggesting potential downward momentum. "

    # Describe current state
    if macd_line_now > signal_line_now:
        conclusion += f"Currently, the MACD line ({macd_line_now:.2f}) is above the signal line ({signal_line_now:.2f}), generally considered a bullish signal. "
    else:
        conclusion += f"Currently, the MACD line ({macd_line_now:.2f}) is below the signal line ({signal_line_now:.2f}), generally considered a bearish signal. "

    # Describe histogram state
    if histogram_now > 0:
        conclusion += f"The positive histogram ({histogram_now:.2f}) indicates strengthening bullish momentum (or weakening bearish momentum)."
    elif histogram_now < 0:
         conclusion += f"The negative histogram ({histogram_now:.2f}) indicates strengthening bearish momentum (or weakening bullish momentum)."
    else: # Histogram is zero
         conclusion += "The histogram is at zero, indicating the MACD and signal lines are currently equal."

    return conclusion.strip()


def get_bb_conclusion(close_price, upper_band, lower_band, middle_band):
    if pd.isna(close_price) or pd.isna(upper_band) or pd.isna(lower_band) or pd.isna(middle_band): return "Bollinger Band data not available."
    if close_price > upper_band: return f"The price (${close_price:.2f}) is currently above the upper Bollinger Band (${upper_band:.2f}), which can sometimes indicate an overbought condition or a strong breakout. Caution is advised as prices may revert towards the middle band (${middle_band:.2f})."
    elif close_price < lower_band: return f"The price (${close_price:.2f}) is currently below the lower Bollinger Band (${lower_band:.2f}), which can sometimes indicate an oversold condition or a strong breakdown. Prices may revert towards the middle band (${middle_band:.2f})."
    else: return f"The price (${close_price:.2f}) is currently trading within the Bollinger Bands (Lower: ${lower_band:.2f}, Upper: ${upper_band:.2f}), around the middle band (SMA20: ${middle_band:.2f})."

# --- Helper function to get plot data range (Keep as before) ---
def _get_plot_data(df, plot_period_years=3):
    """Slices the DataFrame to the specified number of recent years."""
    if df.empty or 'Date' not in df.columns:
        return df

    # Ensure 'Date' is datetime and sorted
    try:
        if not pd.api.types.is_datetime64_any_dtype(df['Date']):
            df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
    except Exception as e:
        print(f"Error processing Date column: {e}")
        return pd.DataFrame() # Return empty if Date is unusable

    last_date = df['Date'].iloc[-1]
    start_date = last_date - pd.DateOffset(years=plot_period_years)

    # Ensure start_date doesn't go before the first date in the data
    first_date = df['Date'].iloc[0]
    start_date = max(start_date, first_date)

    return df[df['Date'] >= start_date].copy()


# --- Plotly Helper for common layout elements (Keep as before - Used by Plotly functions) ---
def _configure_indicator_layout(fig, title):
    fig.update_layout(
        title=dict(
            text=title, y=0.98, x=0.5, xanchor='center', yanchor='top', font=dict(size=14)
        ),
        legend=dict(
            orientation="h", yanchor="top", y=0.92, xanchor="center", x=0.5, font=dict(size=10)
        ),
        margin=dict(l=35, r=25, t=100, b=40),
        yaxis=dict(domain=[0, 0.78]), # Adjusted domain to leave space for range selector
        template="plotly_white",
        autosize=True,
        xaxis_rangeslider_visible=False,
        xaxis_automargin=True,
        yaxis_automargin=True
    )
    fig.update_xaxes(
        domain=[0, 1],
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=3, label="3Y", step="year", stepmode="backward"),
                dict(step="all", label="All") # Add 'All' button back
            ]),
            yanchor='top',
            y=0.84, # Position below legend
            xanchor='left',
            x=0.01,
            font_size=10
        ),
        tickfont=dict(size=10)
    )
    fig.update_yaxes(tickfont=dict(size=10))

    # Set initial visible range (last 1 year) - Keep this logic for initial zoom
    if fig.data and len(fig.data[0].x) > 0:
         last_date_in_data = fig.data[0].x[-1]
         first_date_in_data = fig.data[0].x[0]
         # Ensure last_date is a Timestamp for comparison/offset
         if not isinstance(last_date_in_data, pd.Timestamp):
             try: last_date_in_data = pd.to_datetime(last_date_in_data)
             except: pass # Keep original if conversion fails

         default_start = first_date_in_data # Default to start of data
         if isinstance(last_date_in_data, pd.Timestamp):
             one_year_back = last_date_in_data - pd.DateOffset(years=1)
             # Make sure one_year_back is not before first_date
             default_start = max(first_date_in_data, one_year_back)

         # Ensure start date is not after end date
         if default_start > last_date_in_data:
             default_start = first_date_in_data

         fig.update_xaxes(range=[default_start, last_date_in_data])

    return fig


# --- Plotly Plotting Functions (Keep as before - Used by Full Report) ---

def plot_price_bollinger(df, ticker, plot_period_years=3):
    """Plots Price and Bollinger Bands for the specified period."""
    if len(df) < 20: return None, "Insufficient data for Bollinger Bands."
    # Calculate on full df first
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])
    # Get data for the plotting period
    df_plot_range = _get_plot_data(df, plot_period_years)
    df_plot = df_plot_range.dropna(subset=['BB_Upper', 'BB_Middle', 'BB_Lower', 'Close']) # Ensure all needed cols are present

    if df_plot.empty: return None, "Bollinger Bands could not be calculated for the selected period."

    fig = go.Figure()
    # Plot using df_plot (limited range)
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Upper'], line=dict(color='rgba(211, 211, 211, 0.8)', width=1.5), name='Upper Band'))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Lower'], line=dict(color='rgba(211, 211, 211, 0.8)', width=1.5), fill='tonexty', fillcolor='rgba(211, 211, 211, 0.1)', name='Lower Band'))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Middle'], name='SMA20', line=dict(color='#ff7f0e', width=1.5, dash='dash')))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Close'], name='Close', line=dict(color='#00008B', width=2)))

    fig = _configure_indicator_layout(fig, f'{ticker} Price & Bollinger Bands ({plot_period_years}Y)')
    fig.update_yaxes(title_text="Price")

    # Conclusion based on the LATEST value from the original df
    latest_valid_data = df.dropna(subset=['Close', 'BB_Upper', 'BB_Lower', 'BB_Middle']).iloc[-1] if not df.dropna(subset=['Close', 'BB_Upper', 'BB_Lower', 'BB_Middle']).empty else None
    conclusion = get_bb_conclusion(
        latest_valid_data['Close'] if latest_valid_data is not None else None,
        latest_valid_data['BB_Upper'] if latest_valid_data is not None else None,
        latest_valid_data['BB_Lower'] if latest_valid_data is not None else None,
        latest_valid_data['BB_Middle'] if latest_valid_data is not None else None
    ) if latest_valid_data is not None else "Bollinger Band conclusion requires more data."

    return fig, conclusion

def plot_rsi(df, ticker, plot_period_years=3):
    """Plots RSI for the specified period."""
    if len(df) < 15: return None, "Insufficient data for RSI (14)."
    # Calculate on full df
    df['RSI'] = calculate_rsi(df['Close'])
     # Get data for the plotting period
    df_plot_range = _get_plot_data(df, plot_period_years)
    df_plot = df_plot_range.dropna(subset=['RSI']) # Ensure RSI is present

    if df_plot.empty: return None, "RSI could not be calculated for the selected period."

    fig = go.Figure()
    # Plot using df_plot
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['RSI'], name='RSI', line=dict(color='#8A2BE2', width=2)))
    fig.add_hline(y=70, line_dash="dash", line_color="#DC143C", opacity=0.8, annotation_text="Overbought (70)", annotation_position="bottom right")
    fig.add_hline(y=30, line_dash="dash", line_color="#228B22", opacity=0.8, annotation_text="Oversold (30)", annotation_position="bottom right")

    fig = _configure_indicator_layout(fig, f'Relative Strength Index (RSI 14) ({plot_period_years}Y)')
    fig.update_yaxes(title_text="RSI", range=[0, 100])

    # Conclusion based on LATEST value from original df
    latest_valid_data = df.dropna(subset=['RSI']).iloc[-1] if not df.dropna(subset=['RSI']).empty else None
    conclusion = get_rsi_conclusion(latest_valid_data['RSI'] if latest_valid_data is not None else None) if latest_valid_data is not None else "RSI conclusion requires more data."

    return fig, conclusion

def plot_macd_lines(df, ticker, plot_period_years=3):
    """Plots MACD Line vs Signal Line for the specified period."""
    if len(df) < 35: return None, "Insufficient data for MACD (12, 26, 9)."
    # Calculate on full df
    df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df['Close'])
    # Get data for plotting period
    df_plot_range = _get_plot_data(df, plot_period_years)
    df_plot = df_plot_range.dropna(subset=['MACD_Line', 'MACD_Signal']) # Ensure lines are present

    if len(df_plot) < 2: return None, "Insufficient valid MACD Line/Signal data for the selected period."

    fig = go.Figure()
    # Plot using df_plot
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MACD_Line'], name='MACD Line', line=dict(color='#191970', width=2)))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MACD_Signal'], name='Signal Line', line=dict(color='#FF4500', width=2)))
    fig.add_hline(y=0, line_dash="dash", line_color="grey", opacity=0.5)

    fig = _configure_indicator_layout(fig, f'MACD Line vs Signal Line ({plot_period_years}Y)')
    fig.update_yaxes(title_text="MACD Value")

    # Conclusion based on LATEST values from original df
    df_full_hist = df.dropna(subset=['MACD_Line', 'MACD_Signal', 'MACD_Hist'])
    if len(df_full_hist) < 2: conclusion = "MACD conclusion requires more data."
    else:
        latest = df_full_hist.iloc[-1]; prev = df_full_hist.iloc[-2]
        conclusion = get_macd_conclusion(latest.get('MACD_Line'), latest.get('MACD_Signal'), latest.get('MACD_Hist'), prev.get('MACD_Hist'))

    return fig, conclusion

def plot_macd_histogram(df, ticker, plot_period_years=3):
    """Plots MACD Histogram for the specified period."""
    if len(df) < 35: return None, "Insufficient data for MACD (12, 26, 9)."
    # Ensure MACD is calculated on full df
    if 'MACD_Hist' not in df.columns:
        df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df['Close'])

    # Get data for plotting period
    df_plot_range = _get_plot_data(df, plot_period_years)
    df_plot = df_plot_range.dropna(subset=['MACD_Hist']) # Ensure histogram is present

    if len(df_plot) < 2: return None, "Insufficient valid MACD Histogram data for the selected period."

    fig = go.Figure()
    # Plot using df_plot
    colors = np.where(df_plot['MACD_Hist'] < 0, '#DC143C', '#228B22') # Red / Green
    fig.add_trace(go.Bar(x=df_plot['Date'], y=df_plot['MACD_Hist'], name='MACD Hist', marker_color=colors))

    fig = _configure_indicator_layout(fig, f'MACD Histogram ({plot_period_years}Y)')
    fig.update_yaxes(title_text="Histogram Value")

    # Conclusion based on LATEST values from original df (same as plot_macd_lines)
    df_full_hist = df.dropna(subset=['MACD_Line', 'MACD_Signal', 'MACD_Hist'])
    if len(df_full_hist) < 2: conclusion = "MACD conclusion requires more data."
    else:
        latest = df_full_hist.iloc[-1]; prev = df_full_hist.iloc[-2]
        conclusion = get_macd_conclusion(latest.get('MACD_Line'), latest.get('MACD_Signal'), latest.get('MACD_Hist'), prev.get('MACD_Hist'))

    return fig, conclusion

def plot_historical_line_chart(df, ticker):
    """Plots Historical Price and Volume."""
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Close', line=dict(color='#00008B', width=2)), secondary_y=False)

    # Calculate Volume SMA on the full df
    if 'Volume' in df.columns and not df['Volume'].isnull().all():
        df['Volume_SMA20'] = calculate_volume_sma(df, 20) # Calculate on full df
        fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name='Volume', marker_color='#FF8C00', opacity=0.35), secondary_y=True)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Volume_SMA20'], name='Volume SMA20', line=dict(color='#8B4513', width=1.5, dash='dot')), secondary_y=True)
        fig.update_yaxes(title_text="Volume", secondary_y=True, domain=[0, 0.78], showgrid=False, title_font_size=10, tickfont_size=10, automargin=True)

    fig.update_yaxes(title_text="Price ($)", secondary_y=False, domain=[0, 0.78], title_font_size=10, tickfont_size=10, automargin=True)

    # Apply REVISED layout structure (uses _configure_indicator_layout which handles range selector etc.)
    fig = _configure_indicator_layout(fig, f'{ticker} Historical Price & Volume')
    # No specific period in title as range selector handles it

    return fig

# --- Function to calculate additional indicators for summary (Keep as before) ---
def calculate_detailed_ta(df):
    """Calculates additional indicators for the summary report."""
    if df is None or df.empty: return {}
    ta_summary = {}; df = df.copy(); df['Date'] = pd.to_datetime(df['Date']); df = df.sort_values('Date')
    last_row = None
    if not df.empty:
        last_row = df.iloc[-1]

    # SMAs
    for period in [20, 50, 100, 200]:
        sma_col = f'SMA_{period}'
        if len(df) >= period:
            df[sma_col] = calculate_sma(df['Close'], period);
            sma_val = df[sma_col].iloc[-1] # Get latest SMA
            ta_summary[sma_col] = sma_val if not pd.isna(sma_val) else None
        else: ta_summary[sma_col] = None

    # Volume Analysis
    if 'Volume' in df.columns:
        latest_volume = df['Volume'].iloc[-1] if not df.empty else None
        if len(df) >= 20:
             df['Volume_SMA20'] = calculate_volume_sma(df, 20);
             latest_vol_sma = df['Volume_SMA20'].iloc[-1]
             ta_summary['Volume_SMA20'] = latest_vol_sma if not pd.isna(latest_vol_sma) else None
             if not pd.isna(latest_volume) and not pd.isna(latest_vol_sma) and latest_vol_sma > 0:
                 ta_summary['Volume_vs_SMA20_Ratio'] = latest_volume / latest_vol_sma
             else: ta_summary['Volume_vs_SMA20_Ratio'] = None
        else:
             ta_summary['Volume_vs_SMA20_Ratio'] = None; ta_summary['Volume_SMA20'] = None

        if len(df) >= 6: # Need at least 6 days for a 5-day lookback plus the current day
            vol_slice = df['Volume'].iloc[-5:] # Last 5 days volume
            if not vol_slice.empty and not pd.isna(latest_volume):
                mean_vol_5d = vol_slice.mean()
                if not pd.isna(mean_vol_5d) and mean_vol_5d > 0:
                    if latest_volume > mean_vol_5d * 1.1: ta_summary['Volume_Trend_5D'] = "Increasing"
                    elif latest_volume < mean_vol_5d * 0.9: ta_summary['Volume_Trend_5D'] = "Decreasing"
                    else: ta_summary['Volume_Trend_5D'] = "Mixed"
                else: ta_summary['Volume_Trend_5D'] = None
            else: ta_summary['Volume_Trend_5D'] = None
        else: ta_summary['Volume_Trend_5D'] = None
    else:
         ta_summary['Volume_vs_SMA20_Ratio'] = None; ta_summary['Volume_SMA20'] = None
         ta_summary['Volume_Trend_5D'] = None

    # Support & Resistance
    lookback = 30
    if len(df) >= lookback:
        recent_data = df.iloc[-lookback:]
        support = recent_data['Low'].min()
        resistance = recent_data['High'].max()
        ta_summary['Support_30D'] = support if not pd.isna(support) else None
        ta_summary['Resistance_30D'] = resistance if not pd.isna(resistance) else None
    else: ta_summary['Support_30D'] = None; ta_summary['Resistance_30D'] = None

    # RSI
    if len(df) >= 15:
         df['RSI_14'] = calculate_rsi(df['Close'], 14)
         rsi_val = df['RSI_14'].iloc[-1]
         ta_summary['RSI_14'] = rsi_val if not pd.isna(rsi_val) else None
    else:
         ta_summary['RSI_14'] = None

    # MACD (needed for conclusion later)
    if len(df) >= 35:
        df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df['Close'])
        df_macd_valid = df.dropna(subset=['MACD_Line', 'MACD_Signal', 'MACD_Hist'])
        if len(df_macd_valid) >= 2:
            latest_macd = df_macd_valid.iloc[-1]
            prev_macd = df_macd_valid.iloc[-2]
            ta_summary['MACD_Line'] = latest_macd['MACD_Line']
            ta_summary['MACD_Signal'] = latest_macd['MACD_Signal']
            ta_summary['MACD_Hist'] = latest_macd['MACD_Hist']
            ta_summary['MACD_Hist_Prev'] = prev_macd['MACD_Hist']
        else:
            ta_summary['MACD_Line'] = ta_summary['MACD_Signal'] = ta_summary['MACD_Hist'] = ta_summary['MACD_Hist_Prev'] = None
    else:
        ta_summary['MACD_Line'] = ta_summary['MACD_Signal'] = ta_summary['MACD_Hist'] = ta_summary['MACD_Hist_Prev'] = None


    # BB (needed for conclusion later)
    if len(df) >= 20:
        df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])
        df_bb_valid = df.dropna(subset=['Close', 'BB_Upper', 'BB_Middle', 'BB_Lower'])
        if not df_bb_valid.empty:
            latest_bb = df_bb_valid.iloc[-1]
            ta_summary['BB_Upper'] = latest_bb['BB_Upper']
            ta_summary['BB_Middle'] = latest_bb['BB_Middle']
            ta_summary['BB_Lower'] = latest_bb['BB_Lower']
        else:
            ta_summary['BB_Upper'] = ta_summary['BB_Middle'] = ta_summary['BB_Lower'] = None
    else:
        ta_summary['BB_Upper'] = ta_summary['BB_Middle'] = ta_summary['BB_Lower'] = None

    # Add current price for convenience
    ta_summary['Current_Price'] = df['Close'].iloc[-1] if not df.empty else None

    return ta_summary

# ==============================================================================
# --- NEW Matplotlib Plotting Functions (For WordPress Static Images) ---
# ==============================================================================

def plot_historical_mpl(df, ticker, plot_period_years=3):
    """Plots Historical Price and Volume using Matplotlib."""
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')

    # Get data for the plotting period
    df_plot = _get_plot_data(df.copy(), plot_period_years) # Operate on a copy

    if df_plot.empty:
        print(f"Warning: No data available for {ticker} in the last {plot_period_years} years.")
        return None # Return None if no data

    fig, ax1 = plt.subplots(figsize=(12, 6)) # Create figure and primary axes

    # Plot Close Price on primary axis
    color_price = 'navy' # Dark blue
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price ($)', color=color_price)
    ax1.plot(df_plot['Date'], df_plot['Close'], color=color_price, linewidth=1.5, label='Close Price')
    ax1.tick_params(axis='y', labelcolor=color_price)
    ax1.grid(True, axis='y', linestyle='--', alpha=0.6)

    # Create secondary axis for Volume
    ax2 = ax1.twinx()
    color_volume = 'darkorange'
    ax2.set_ylabel('Volume', color=color_volume)

    # Calculate Volume SMA on the plotted data range
    if 'Volume' in df_plot.columns and not df_plot['Volume'].isnull().all():
        df_plot['Volume_SMA20'] = calculate_volume_sma(df_plot, 20) # Calculate on plot data
        ax2.bar(df_plot['Date'], df_plot['Volume'], color=color_volume, alpha=0.3, width=1.0, label='Volume') # Adjust width as needed
        # Plot Volume SMA only if calculated
        if not df_plot['Volume_SMA20'].isnull().all():
             ax2.plot(df_plot['Date'], df_plot['Volume_SMA20'], color='saddlebrown', linewidth=1, linestyle='dotted', label='Volume SMA20')
    ax2.tick_params(axis='y', labelcolor=color_volume)
    ax2.set_ylim(bottom=0) # Volume starts at 0

    # Formatting
    fig.suptitle(f'{ticker} Historical Price & Volume ({plot_period_years}Y)', fontsize=14)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y')) # Format date axis
    fig.autofmt_xdate() # Auto-rotate date labels

    # Combine legends
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='upper left', fontsize='small')

    fig.tight_layout(rect=[0, 0, 1, 0.96]) # Adjust layout to prevent title overlap

    return fig # Return the Matplotlib figure object

def plot_bollinger_mpl(df, ticker, plot_period_years=3):
    """Plots Price and Bollinger Bands using Matplotlib."""
    if len(df) < 20: return None
    # Calculate on full df first
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])
    # Get data for the plotting period
    df_plot = _get_plot_data(df.copy(), plot_period_years)
    df_plot = df_plot.dropna(subset=['BB_Upper', 'BB_Middle', 'BB_Lower', 'Close'])

    if df_plot.empty: return None

    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot Bands and Fill
    ax.plot(df_plot['Date'], df_plot['BB_Upper'], color='darkgrey', linewidth=1, label='Upper Band')
    ax.plot(df_plot['Date'], df_plot['BB_Lower'], color='darkgrey', linewidth=1, label='Lower Band')
    ax.fill_between(df_plot['Date'], df_plot['BB_Lower'], df_plot['BB_Upper'], color='lightgrey', alpha=0.3)

    # Plot Middle Band (SMA20) and Close Price
    ax.plot(df_plot['Date'], df_plot['BB_Middle'], color='darkorange', linewidth=1, linestyle='--', label='SMA20')
    ax.plot(df_plot['Date'], df_plot['Close'], color='navy', linewidth=1.5, label='Close Price')

    # Formatting
    ax.set_title(f'{ticker} Price & Bollinger Bands ({plot_period_years}Y)', fontsize=14)
    ax.set_ylabel('Price ($)')
    ax.legend(loc='upper left', fontsize='small')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate()
    fig.tight_layout()

    return fig

def plot_rsi_mpl(df, ticker, plot_period_years=3):
    """Plots RSI using Matplotlib."""
    if len(df) < 15: return None
    # Calculate on full df
    df['RSI'] = calculate_rsi(df['Close'])
    # Get data for the plotting period
    df_plot = _get_plot_data(df.copy(), plot_period_years)
    df_plot = df_plot.dropna(subset=['RSI'])

    if df_plot.empty: return None

    fig, ax = plt.subplots(figsize=(12, 4)) # Smaller height for indicator

    # Plot RSI line
    ax.plot(df_plot['Date'], df_plot['RSI'], color='purple', linewidth=1.5, label='RSI (14)')

    # Plot Overbought/Oversold lines
    ax.axhline(70, color='red', linestyle='--', linewidth=1, alpha=0.8, label='Overbought (70)')
    ax.axhline(30, color='green', linestyle='--', linewidth=1, alpha=0.8, label='Oversold (30)')

    # Formatting
    ax.set_title(f'{ticker} Relative Strength Index (RSI 14) ({plot_period_years}Y)', fontsize=14)
    ax.set_ylabel('RSI')
    ax.set_ylim(0, 100) # RSI range is 0-100
    ax.legend(loc='upper left', fontsize='small')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate()
    fig.tight_layout()

    return fig

def plot_macd_lines_mpl(df, ticker, plot_period_years=3):
    """Plots MACD Line vs Signal Line using Matplotlib."""
    if len(df) < 35: return None
    # Calculate on full df
    df['MACD_Line'], df['MACD_Signal'], _ = calculate_macd(df['Close'])
    # Get data for plotting period
    df_plot = _get_plot_data(df.copy(), plot_period_years)
    df_plot = df_plot.dropna(subset=['MACD_Line', 'MACD_Signal'])

    if len(df_plot) < 2: return None

    fig, ax = plt.subplots(figsize=(12, 4)) # Smaller height

    # Plot MACD and Signal lines
    ax.plot(df_plot['Date'], df_plot['MACD_Line'], color='navy', linewidth=1.5, label='MACD Line')
    ax.plot(df_plot['Date'], df_plot['MACD_Signal'], color='orangered', linewidth=1.5, label='Signal Line')

    # Plot Zero line
    ax.axhline(0, color='grey', linestyle='--', linewidth=1, alpha=0.5)

    # Formatting
    ax.set_title(f'{ticker} MACD Line vs Signal Line ({plot_period_years}Y)', fontsize=14)
    ax.set_ylabel('MACD Value')
    ax.legend(loc='upper left', fontsize='small')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate()
    fig.tight_layout()

    return fig

def plot_macd_hist_mpl(df, ticker, plot_period_years=3):
    """Plots MACD Histogram using Matplotlib."""
    if len(df) < 35: return None
    # Ensure MACD is calculated on full df
    if 'MACD_Hist' not in df.columns:
        _, _, df['MACD_Hist'] = calculate_macd(df['Close'])

    # Get data for plotting period
    df_plot = _get_plot_data(df.copy(), plot_period_years)
    df_plot = df_plot.dropna(subset=['MACD_Hist'])

    if len(df_plot) < 2: return None

    fig, ax = plt.subplots(figsize=(12, 4)) # Smaller height

    # Plot MACD Histogram bars
    colors = ['green' if val >= 0 else 'red' for val in df_plot['MACD_Hist']]
    # Use date index directly for bars if 'Date' is datetime
    if pd.api.types.is_datetime64_any_dtype(df_plot['Date']):
        # Estimate bar width based on date frequency (might need adjustment)
        date_diffs = df_plot['Date'].diff().median()
        bar_width = date_diffs.days * 0.8 if date_diffs else 0.8 # Adjust factor as needed
        ax.bar(df_plot['Date'], df_plot['MACD_Hist'], color=colors, width=bar_width, label='MACD Histogram')
    else: # Fallback if 'Date' is not datetime
        ax.bar(range(len(df_plot)), df_plot['MACD_Hist'], color=colors, label='MACD Histogram')

    # Plot Zero line
    ax.axhline(0, color='grey', linestyle='--', linewidth=1, alpha=0.5)

    # Formatting
    ax.set_title(f'{ticker} MACD Histogram ({plot_period_years}Y)', fontsize=14)
    ax.set_ylabel('Histogram Value')
    ax.legend(loc='upper left', fontsize='small')
    ax.grid(True, axis='y', linestyle='--', alpha=0.6) # Grid only on y-axis for bars

    # Format X axis only if 'Date' is datetime
    if pd.api.types.is_datetime64_any_dtype(df_plot['Date']):
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        fig.autofmt_xdate()
    else:
        ax.set_xlabel('Index') # Label index if not dates

    fig.tight_layout()

    return fig

# --- NEW: Matplotlib Forecast Plot ---
def plot_forecast_mpl(rdata, ticker):
    """
    Plots Actual vs Forecast data using Matplotlib.
    Accepts the prepared report data dictionary (rdata).
    """
    print(f"  Generating Matplotlib forecast chart for {ticker}...")

    actual_data = rdata.get('actual_data')
    forecast_data = rdata.get('monthly_forecast_table_data') # Use the table data for consistency
    period_label = rdata.get('period_label', 'Period')
    time_col = rdata.get('time_col', 'Period')
    overall_pct_change = rdata.get('overall_pct_change', 0.0)
    forecast_1y = rdata.get('forecast_1y')


    # Validate data
    if forecast_data is None or forecast_data.empty or time_col not in forecast_data.columns:
        print(f"    Warning: Forecast data for {ticker} is missing or invalid for plotting.")
        return None

    fig, ax = plt.subplots(figsize=(12, 6))

    try:
        # Prepare x-axis labels (treat 'Period' as categorical for now)
        x_labels_actual = []
        y_values_actual = []
        if actual_data is not None and not actual_data.empty and 'Average' in actual_data.columns and time_col in actual_data.columns:
            plot_actual = actual_data.tail(6) # Show last 6 actual periods
            x_labels_actual = plot_actual[time_col].tolist()
            y_values_actual = plot_actual['Average'].tolist()
            ax.plot(x_labels_actual, y_values_actual, marker='o', linestyle='-', color='blue', linewidth=1.5, label='Actual Avg')

        x_labels_forecast = forecast_data[time_col].tolist()
        y_values_forecast_avg = forecast_data['Average'].tolist()

        # Combine labels for the axis, ensuring order and uniqueness
        all_x_labels = sorted(list(set(x_labels_actual + x_labels_forecast)))
        ax.set_xticks(range(len(all_x_labels))) # Set ticks based on combined length
        ax.set_xticklabels(all_x_labels, rotation=45, ha='right') # Rotate labels

        # Plot forecast average
        ax.plot(x_labels_forecast, y_values_forecast_avg, marker='.', linestyle='--', color='green', linewidth=1.5, label='Forecast Avg')

        # Plot forecast range (Low/High) if available
        if 'Low' in forecast_data.columns and 'High' in forecast_data.columns:
            y_values_forecast_low = forecast_data['Low'].tolist()
            y_values_forecast_high = forecast_data['High'].tolist()
            ax.fill_between(x_labels_forecast, y_values_forecast_low, y_values_forecast_high,
                            color='palegreen', alpha=0.4, label='Forecast Range (Low-High)')

        # Add annotation for the 1-year forecast point
        if forecast_1y is not None and x_labels_forecast:
            last_period_label = x_labels_forecast[-1]
            annotation_text = f"{forecast_1y:.2f}\n({overall_pct_change:+.1f}% 1Y)"
            # Find index of last period label in the combined axis
            try:
                 last_period_index = all_x_labels.index(last_period_label)
                 ax.annotate(annotation_text,
                           xy=(last_period_index, forecast_1y), # Use index for position
                           xytext=(15, -15), # Offset text
                           textcoords='offset points',
                           ha='center', va='top',
                           fontsize=9, color='darkgreen',
                           bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                           arrowprops=dict(arrowstyle='->', color='darkgreen'))
            except ValueError:
                 print(f"Warning: Could not find last forecast period '{last_period_label}' in combined axis for annotation.")

        # Formatting
        num_forecast_periods = len(forecast_data)
        ax.set_title(f'{ticker} Price Forecast ({num_forecast_periods} {period_label}s)', fontsize=14)
        ax.set_ylabel('Price ($)')
        ax.set_xlabel(period_label)
        ax.legend(loc='upper left', fontsize='small')
        ax.grid(True, linestyle='--', alpha=0.6)

        # Adjust x-axis tick frequency if too many labels
        if len(all_x_labels) > 20:
            step = max(1, len(all_x_labels) // 15) # Show ~15 labels max
            ax.set_xticks(np.arange(0, len(all_x_labels), step))

        fig.tight_layout()
        print(f"  Successfully generated Matplotlib forecast figure for {ticker}")
        return fig

    except Exception as e:
        print(f"  ERROR generating Matplotlib forecast chart for {ticker}: {e}")
        import traceback
        traceback.print_exc() # Print detailed error
        plt.close(fig) # Ensure figure is closed
        return None # Return None on error