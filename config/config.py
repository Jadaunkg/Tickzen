from datetime import datetime, timedelta
import os

# List of tickers; you can later add more.
TICKERS = ["TSLA"]  # e.g., ["AAPL", "GOOGL", "MSFT"]

# Date range for data collection
START_DATE = "2012-01-01"  # Earliest practical date
END_DATE = datetime.today().strftime("%Y-%m-%d")  # Current date

# --- Forecast Horizon Options ---
# Keys are the display options and values are the corresponding forecast period in days.
FORECAST_OPTIONS = {
    "15 days": 15,
    "1 month": 30,
    "3 month": 90,
    "6 month": 180,
    "1 year": 365,
    "2 year": 730,
    "5 year": 1825
}


FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
