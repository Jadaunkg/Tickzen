# Complete Variables List - Tickzen Report Generation System

**Generated from:** `html_components.py` and `report_generator.py`

---

## 1. IMPORTS & EXTERNAL DEPENDENCIES

### Standard Library Imports
```python
datetime, timedelta
random
logging
os
sys
time
tempfile
base64
json
threading (Thread)
io (BytesIO)
```

### Data Processing
```python
pandas as pd
numpy as np
pytz
```

### Visualization Libraries
```python
plotly.graph_objects as go
plotly.io (to_html, write_image, pio)
matplotlib
matplotlib.pyplot as plt
```

### Utilities
```python
psutil (optional)
```

---

## 2. CONFIGURATION VARIABLES

### Matplotlib Configuration
```python
matplotlib.use('Agg')  # Backend setting
```

### Kaleido Configuration
```python
pio.kaleido.scope.default_format = "png"
# pio.kaleido.scope.scale = 1.5
# pio.kaleido.scope.width = 1000
# pio.kaleido.scope.height = 600
```

### Logging Configuration
```python
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
```

---

## 3. GLOBAL VARIABLES & CONSTANTS

### Report Generator Globals
```python
_pandas_module = None
_jwt_module = None
custom_style = """<style>...</style>"""  # CSS string
```

---

## 4. CURRENCY & LOCALIZATION

### Currency Symbols by Exchange
```python
# Exchange suffixes mapped to symbols
'.NS', '.BO' → '₹' (Indian Rupee)
'.PA', '.F', '.DE', '.BE', '.DU', '.HM', '.HA', '.MU' → '€' (Euro)
'.L' → '£' (British Pound)
'.TO', '.V' → 'C$' (Canadian Dollar)
'.AX' → 'A$' (Australian Dollar)
'.SI' → 'S$' (Singapore Dollar)
'.ST', '.CO', '.OL', '.IC' → 'kr' (Nordic Krona)
'.HE' → '€' (Euro - Finland)
'.NZ' → 'NZ$' (New Zealand Dollar)
Default → '$' (US Dollar)
```

---

## 5. ICON MAPPING

### Icon Types & Symbols
```python
icons = {
    'up': ('icon-up', '▲'),
    'down': ('icon-down', '▼'),
    'neutral': ('icon-neutral', '●'),
    'warning': ('icon-warning', '⚠️'),
    'positive': ('icon-positive', '➕'),
    'negative': ('icon-negative', '➖'),
    'info': ('icon-info', 'ℹ️'),
    'money': ('icon-money', '💰'),
    'chart': ('icon-chart', '📊'),
    'health': ('icon-health', '⚕️'),
    'efficiency': ('icon-efficiency', '⚙️'),
    'growth': ('icon-growth', '📈'),
    'tax': ('icon-tax', '🧾'),
    'dividend': ('icon-dividend', '💸'),
    'stats': ('icon-stats', '📉'),
    'news': ('icon-news', '📰'),
    'faq': ('icon-faq', '❓'),
    'peer': ('icon-peer', '👥'),
    'history': ('icon-history', '📜'),
    'cash': ('icon-cash', '💵'),
    'volume': ('icon-volume', '🔊'),
    'divergence': ('icon-divergence', '↔️')
}
```

---

## 6. FORMATTING TYPES

### Format Type Options
```python
format_types = [
    "currency",      # e.g., $1,234.56
    "percent",       # e.g., 15.5%
    "percent_direct",# Direct percentage value
    "ratio",         # e.g., 1.5x
    "large_number",  # e.g., 1.5M, 2.3B
    "integer",       # e.g., 1234
    "date",          # Date formatting
    "string",        # Plain string
    "factor",        # Factor/multiplier
    "number"         # Default number format
]
```

---

## 7. DATA EXTRACTION KEYS

### Company Profile Data Keys
```python
profile_keys = [
    'Company Name',
    'Ticker Symbol',
    'Exchange',
    'Sector',
    'Industry',
    'Country',
    'Website',
    'Business Summary',
    'CEO',
    'Employees',
    'Founded',
    'Headquarters',
    'Market Cap',
    'Enterprise Value'
]
```

### Valuation Metrics Keys
```python
valuation_keys = [
    'Trailing P/E',
    'Forward P/E',
    'PEG Ratio',
    'Price/Sales (TTM)',
    'Price/Book (MRQ)',
    'Enterprise Value/Revenue',
    'Enterprise Value/EBITDA',
    'Market Cap',
    'Enterprise Value',
    'Book Value per Share',
    'Price/Cash Flow'
]
```

### Financial Health Keys
```python
financial_health_keys = [
    'Current Ratio (MRQ)',
    'Quick Ratio (MRQ)',
    'Debt/Equity (MRQ)',
    'Total Debt (MRQ)',
    'Total Cash (MRQ)',
    'Operating Cash Flow (TTM)',
    'Free Cash Flow (TTM)',
    'Return on Assets (TTM)',
    'Return on Equity (TTM)',
    'Interest Coverage',
    'Net Debt',
    'Cash per Share'
]
```

### Financial Efficiency Keys
```python
efficiency_keys = [
    'Asset Turnover (TTM)',
    'Inventory Turnover (TTM)',
    'Receivables Turnover (TTM)',
    'Working Capital Turnover (TTM)',
    'Current Ratio (MRQ)',
    'Days Sales Outstanding',
    'Days Inventory Outstanding',
    'Cash Conversion Cycle',
    'Return on Invested Capital (ROIC TTM)'
]
```

### Profitability & Growth Keys
```python
profitability_keys = [
    'Profit Margin (TTM)',
    'Operating Margin (TTM)',
    'EBITDA Margin (TTM)',
    'Gross Margin (TTM)',
    'Net Income (TTM)',
    'EBITDA (TTM)',
    'Revenue (TTM)',
    'Revenue per Share (TTM)',
    'Quarterly Revenue Growth (YoY)',
    'Quarterly Earnings Growth (YoY)',
    'Earnings Growth (YoY)',
    'EPS (TTM)',
    'Diluted EPS (TTM)'
]
```

### Dividends & Shareholder Returns Keys
```python
dividends_keys = [
    'Dividend Rate (Annual)',
    'Dividend Yield',
    'Payout Ratio',
    'Ex-Dividend Date',
    'Forward Annual Dividend Rate',
    'Forward Annual Dividend Yield',
    'Trailing Annual Dividend Rate',
    'Trailing Annual Dividend Yield',
    '5-Year Average Dividend Yield',
    'Dividend Date',
    'Last Split Factor',
    'Last Split Date',
    'Total Cash from Financing Activities',
    'Stock Repurchase Activity'
]
```

### Share Statistics Keys
```python
share_stats_keys = [
    'Shares Outstanding',
    'Float',
    'Shares Short',
    'Short Ratio',
    'Short % of Float',
    'Short % of Shares Outstanding',
    'Shares Short Prior Month',
    'Insider Ownership %',
    'Institutional Ownership %',
    'Avg Volume (10-day)',
    'Avg Volume (3-month)',
    'Implied Shares Outstanding'
]
```

### Stock Price Statistics Keys
```python
price_stats_keys = [
    '52-Week High',
    '52-Week Low',
    '52-Week Change %',
    '50-Day Moving Average',
    '200-Day Moving Average',
    'Beta (5Y Monthly)',
    'Price (Regular Market)',
    'Previous Close',
    'Open',
    'Day High',
    'Day Low',
    'Volume',
    'Average Volume',
    'Bid',
    'Ask',
    'Bid Size',
    'Ask Size'
]
```

### Short Selling Information Keys
```python
short_selling_keys = [
    'Shares Short',
    'Short Ratio (Days to Cover)',
    'Short % of Float',
    'Short % of Shares Outstanding',
    'Shares Short Prior Month',
    'Short Interest Change',
    'Average Volume (for Short Coverage)',
    'Float',
    'Shares Outstanding'
]
```

### Total Valuation Keys
```python
total_valuation_keys = [
    'Market Cap',
    'Enterprise Value',
    'Trailing P/E',
    'Forward P/E',
    'PEG Ratio',
    'Price/Sales (TTM)',
    'Price/Book (MRQ)',
    'Enterprise Value/Revenue',
    'Enterprise Value/EBITDA',
    'Book Value',
    'Price/Cash Flow'
]
```

### Analyst Information Keys
```python
analyst_keys = [
    'Target Price (Mean)',
    'Target Price (Median)',
    'Target Price (High)',
    'Target Price (Low)',
    'Number of Analysts',
    'Recommendation',
    'Recommendation Key',
    'Buy Ratings',
    'Hold Ratings',
    'Sell Ratings',
    'Strong Buy Ratings',
    'Strong Sell Ratings'
]
```

### Technical Analysis Keys
```python
technical_keys = [
    'Current_Price',
    'SMA_50',
    'SMA_200',
    'EMA_12',
    'EMA_26',
    'RSI_14',
    'MACD_Line',
    'MACD_Signal',
    'MACD_Hist',
    'MACD_Hist_Prev',
    'BB_Upper',
    'BB_Middle',
    'BB_Lower',
    'BB_Width',
    'Recent_High',
    'Recent_Low',
    'Volume_SMA_20'
]
```

### Risk Analysis Keys
```python
risk_keys = [
    'volatility',
    'beta',
    'max_drawdown',
    'value_at_risk',
    'sharpe_ratio',
    'sortino_ratio',
    'var_95',
    'var_99',
    'downside_deviation',
    'risk_level'
]
```

### Sentiment Analysis Keys
```python
sentiment_keys = [
    'news_sentiment',
    'social_sentiment',
    'analyst_sentiment',
    'overall_sentiment',
    'sentiment_score',
    'bullish_signals',
    'bearish_signals',
    'neutral_signals'
]
```

### Quarterly Earnings Keys
```python
quarterly_earnings_keys = [
    'earnings_dates',
    'earnings_estimates',
    'earnings_actuals',
    'surprise_percentage',
    'revenue_estimates',
    'revenue_actuals'
]
```

---

## 8. CALCULATED METRICS & DERIVED VALUES

### Price Metrics
```python
current_price
last_date
forecast_1m (1-month forecast)
forecast_1y (1-year forecast)
overall_pct_change
```

### Statistical Metrics
```python
volatility (annualized)
green_days (positive price days)
total_days
```

### Technical Indicators
```python
sma_50 (50-day Simple Moving Average)
sma_200 (200-day Simple Moving Average)
latest_rsi (14-period RSI)
```

### Sentiment & Conclusions
```python
sentiment (Strong Bullish, Bullish, Neutral, Bearish, Strong Bearish)
bb_conclusion (Bollinger Bands analysis)
rsi_conclusion (RSI analysis)
macd_conclusion (MACD analysis)
```

### Forecast Data
```python
forecast_horizon_periods
forecast_12m (forecast table data)
monthly_forecast_table_data
actual_data
forecast_data
```

### Risk Assessment
```python
risk_items (list of identified risks)
risk_factors (detailed risk analysis)
```

---

## 9. CHART & VISUALIZATION VARIABLES

### Chart Types
```python
# Plotly Charts
forecast_chart_fig
historical_line_fig
bb_fig (Bollinger Bands)
rsi_fig (RSI)
macd_lines_fig
macd_hist_fig

# Matplotlib Charts (for WordPress)
mpl_fig (generic)
chart_image_base64 (dict of base64 encoded images)
saved_forecast_chart_path
```

### Chart Configuration
```python
time_col = "Period"
period_label = "Period" | "Month" | "Week" | "Day"
combined_time_axis
```

### Image Assets
```python
report_assets_dir
chart_image_base64 = {
    'forecast': base64_string,
    'historical_price_volume': base64_string,
    'bollinger_bands': base64_string,
    'rsi': base64_string,
    'macd_lines': base64_string,
    'macd_histogram': base64_string
}
```

---

## 10. HTML GENERATION VARIABLES

### HTML Components
```python
intro_html
metrics_summary_html
detailed_forecast_table_html
company_profile_html
total_valuation_html
share_statistics_html
valuation_metrics_html
financial_health_html
financial_efficiency_html
profitability_growth_html
dividends_shareholder_returns_html
technical_analysis_summary_html
stock_price_statistics_html
short_selling_info_html
peer_comparison_html
risk_factors_html
analyst_insights_html
recent_news_html
historical_performance_html
risk_analysis_html
sentiment_analysis_html
quarterly_earnings_html
conclusion_outlook_html
faq_html
report_info_disclaimer_html
```

### HTML Structure
```python
report_body_content
full_html
final_html_fragment
custom_style (CSS)
```

---

## 11. DATA CONTAINERS (RDATA STRUCTURE)

### Core Data Object
```python
rdata = {
    # Historical & Forecast
    'historical_data': DataFrame,
    'actual_data': DataFrame,
    'forecast_data': DataFrame,
    
    # Time Configuration
    'time_col': str,
    'period_label': str,
    
    # Technical Analysis
    'detailed_ta_data': dict,
    
    # Price Metrics
    'current_price': float,
    'last_date': datetime,
    'forecast_1m': float,
    'forecast_1y': float,
    'overall_pct_change': float,
    
    # Statistics
    'volatility': float,
    'green_days': int,
    'total_days': int,
    'sma_50': float,
    'sma_200': float,
    'latest_rsi': float,
    
    # Sentiment
    'sentiment': str,
    
    # Forecast Details
    'forecast_horizon_periods': int,
    'monthly_forecast_table_data': DataFrame,
    
    # Fundamental Data
    'profile_data': dict,
    'valuation_data': dict,
    'financial_health_data': dict,
    'financial_efficiency_data': dict,
    'profitability_data': dict,
    'dividends_data': dict,
    'analyst_info_data': dict,
    'total_valuation_data': dict,
    'share_statistics_data': dict,
    'stock_price_stats_data': dict,
    'short_selling_data': dict,
    
    # Advanced Analysis
    'peer_comparison_data': dict,
    'risk_analysis_data': dict,
    'sentiment_analysis_data': dict,
    'quarterly_earnings_data': dict,
    
    # News & Content
    'news_list': list,
    
    # Risk Assessment
    'risk_items': list,
    'sector': str,
    'industry': str,
    
    # Observations
    'data_driven_observations': list
}
```

---

## 12. FUNCTION PARAMETERS

### Main Report Generation Functions
```python
# create_full_report() parameters
ticker: str
actual_data: DataFrame
forecast_data: DataFrame
historical_data: DataFrame
fundamentals: dict
ts: str (timestamp)
aggregation: str (optional)
app_root: str (path)
plot_period_years: int (default=3)
current_price_info: dict (optional)

# create_wordpress_report_assets() parameters
# (same as above)
```

### Helper Function Parameters
```python
# format_html_value()
value: any
format_type: str (default="number")
precision: int (default=2)
ticker: str (optional)

# get_currency_symbol()
ticker: str

# get_icon()
type_input: str

# _safe_float()
value: any
default: any (default=None)

# _generate_error_html()
section_name: str
error_message: str (default="Error generating section content.")
```

---

## 13. THRESHOLDS & HEURISTICS

### Valuation Thresholds
```python
pe_threshold_low = 15
earnings_growth_threshold_strong = 10
debt_equity_threshold_manageable = 1.5
```

### Technical Thresholds
```python
rsi_overbought = 70
rsi_oversold = 30
current_ratio_threshold = 1.0
debt_equity_high = 2.0
```

### Sentiment Scoring
```python
score_thresholds = {
    'Strong Bullish': >= 2.5,
    'Bullish': >= 1.0,
    'Neutral': between -1.0 and 1.0,
    'Bearish': <= -1.0,
    'Strong Bearish': <= -2.5
}
```

---

## 14. FILE PATHS & DIRECTORIES

### Report Directories
```python
reports_dir = 'static/stock_reports'
report_assets_dir = 'report_assets/{ticker}_{ts}'
```

### File Naming Patterns
```python
report_filename = f"{ticker}_detailed_report_{ts}.html"
forecast_chart_filename = f"{ticker}_forecast_featured_{ts}.png"
```

---

## 15. CONFIGURATION DICTIONARIES

### Chart Configurations
```python
image_configs = [
    ('forecast', plot_forecast_mpl, rdata),
    ('historical_price_volume', plot_historical_mpl, hist_data_for_images),
    ('bollinger_bands', plot_bollinger_mpl, hist_data_for_images),
    ('rsi', plot_rsi_mpl, hist_data_for_images),
    ('macd_lines', plot_macd_lines_mpl, hist_data_for_images),
    ('macd_histogram', plot_macd_hist_mpl, hist_data_for_images)
]
```

### Plot Configuration
```python
default_config = {
    'displayModeBar': True,
    'displaylogo': False,
    'responsive': True
}
```

---

## 16. TIME & DATE VARIABLES

### Time Configuration
```python
periods_in_year = 12 | 52 | 252  # Month | Week | Day
periods_in_month = 1 | 4 | 21     # Month | Week | Day
```

### Date Formatting
```python
datetime.now(pytz.utc)
last_date
generation_time
current_date_str
time_str
```

---

## 17. RANDOMIZATION VARIABLES

### Random Text Variations
```python
gen_on = random.choice(["Report Generated On:", "Analysis Compiled:", ...])
curr_date = random.choice(["Current Date Context:", "Report Date:", ...])
sources = random.choice(["Primary Data Sources:", ...])
limits = random.choice(["Known Limitations:", ...])
disclaimer_title = random.choice(["IMPORTANT DISCLAIMER:", ...])
disclaimer_body1/2/3/4 = random.choice([...])
```

---

## 18. DATAFRAME COLUMNS

### Historical Data Columns (Required)
```python
required_hist_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
```

### Forecast Data Columns
```python
forecast_columns = ['Period', 'Low', 'Average', 'High', 'Potential ROI', 'Action']
```

### Technical Analysis DataFrame
```python
ta_columns = [
    'Date', 'Close', 'SMA_50', 'SMA_200', 'EMA_12', 'EMA_26',
    'RSI_14', 'MACD', 'MACD_Signal', 'MACD_Hist',
    'BB_Upper', 'BB_Middle', 'BB_Lower'
]
```

---

## 19. ERROR HANDLING VARIABLES

### Error Messages
```python
fallback_msg = "Chart could not be generated."
chart_fallback_message = '<p>Chart for {title} could not be generated.</p>'
error_message = "Error generating section content."
```

### Status Variables
```python
has_content: bool
is_chart_section: bool
result = [None]  # Thread result container
```

---

## 20. PERFORMANCE & OPTIMIZATION

### Timeout Settings
```python
timeout_seconds = 60
```

### Image Settings
```python
dpi = 100 | 150
scale = 1.0 | 1.5
width = 1000 | 1200
height = 600
```

### Size Limits
```python
max_figure_size = 5 * 1024 * 1024  # 5MB
MAX_TICKERS_TO_STORE_IN_FIRESTORE = 500
```

---

## 21. LOOP VARIABLES & ITERATORS

```python
for item in html_sections:
    title, html_content, section_class = item[0], item[1], item[2]
    narrative = item[3] if len(item) > 3 else None
    conclusion = item[4] if len(item) > 4 else None

for config_item in image_configs:
    chart_key = config_item[0]
    mpl_func = config_item[1]
    data_arg = config_item[2]

for col in plot_cols:
    # plotting loop

for chart_key in chart_image_base64.keys():
    # image processing loop
```

---

## 22. CONDITIONAL FLAGS

```python
FIREBASE_INITIALIZED_SUCCESSFULLY: bool
AUTO_PUBLISHER_IMPORTED_SUCCESSFULLY: bool
PIPELINE_IMPORTED_SUCCESSFULLY: bool
include_plotlyjs: bool | 'cdn'
full_html: bool
```

---

## 23. SPECIALTY VARIABLES

### Peer Comparison
```python
peer_companies: list
comparison_metrics: dict
target_company: str
```

### News Data
```python
news_list = [{
    'title': str,
    'link': str,
    'publisher': str,
    'published_date': datetime,
    'type': str
}]
```

### FAQ Data
```python
faq_items = [{
    'question': str,
    'answer': str
}]
```

---

## 24. CSS CLASS NAMES

### Section Classes
```python
section_classes = [
    'introduction-overview',
    'key-metrics-forecast',
    'forecast-chart',
    'detailed-forecast-table',
    'company-profile',
    'total-valuation',
    'share-statistics',
    'valuation-metrics',
    'financial-health',
    'financial-efficiency',
    'profitability-growth',
    'dividends-shareholder-returns',
    'technical-analysis-summary',
    'stock-price-statistics',
    'quarterly-earnings',
    'short-selling-information',
    'risk-analysis',
    'sentiment-analysis',
    'peer-comparison',
    'risk-factors',
    'analyst-insights',
    'recent-news',
    'conclusion-outlook',
    'frequently-asked-questions',
    'report-information-disclaimer'
]
```

### Component Classes
```python
component_classes = [
    'report-container',
    'section',
    'narrative',
    'metrics-summary',
    'metric-item',
    'metric-label',
    'metric-value',
    'metric-change',
    'profile-grid',
    'profile-item',
    'metrics-table',
    'analyst-grid',
    'analyst-item',
    'table-container',
    'indicator-chart-container',
    'indicator-conclusion',
    'conclusion-columns',
    'conclusion-column',
    'news-container',
    'news-item',
    'news-meta',
    'disclaimer',
    'general-info',
    'embedded-chart-image',
    'static-chart-image'
]
```

---

## 25. ACTION CLASSIFICATION

### Trading Actions
```python
actions = {
    'Buy': 'ROI > 2%',
    'Hold': '-2% <= ROI <= 2%',
    'Short': 'ROI < -2%'
}
```

### Action CSS Classes
```python
action_classes = [
    'action-buy',
    'action-hold',
    'action-short'
]
```

---

## SUMMARY STATISTICS

- **Total Icon Types**: 22
- **Total Format Types**: 10
- **Total Data Extraction Keys**: 150+
- **Total CSS Classes**: 50+
- **Total Functions**: 40+
- **Total Chart Types**: 12+
- **Total HTML Sections**: 25+

---

**Last Updated**: November 15, 2025
**Files Analyzed**: 
- `html_components.py` (3463 lines)
- `report_generator.py` (1145 lines)

**Total Coverage**: ~4600 lines of code analyzed



