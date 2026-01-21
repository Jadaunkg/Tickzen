# Comprehensive Stock Analysis Report Keys

This document lists all the metrics, indicators, and data points ("keys") used in the automated stock analysis and report generation system. These keys form the calculation base for the comprehensive stock reports.

## 1. Fundamental Analysis

These metrics are extracted from financial statements detailed company information.

### Company Profile
- `Company Name`: Full legal name or short name.
- `Sector`: The economic sector the company operates in.
- `Industry`: The specific industry classification.
- `Website`: Corporate website URL.
- `Market Cap`: Total market value of shares (formatted 'B'/'T').
- `Employees`: Full-time employee count.
- `Summary`: Business description.

### Valuation Metrics
- `Trailing P/E`: Trailing Price-to-Earnings ratio.
- `Forward P/E`: Forward Price-to-Earnings ratio.
- `Price/Sales (TTM)`: Price-to-Sales ratio (Trailing 12 Months).
- `Price/Book (MRQ)`: Price-to-Book ratio (Most Recent Quarter).
- `PEG Ratio`: Price/Earnings-to-Growth ratio.
- `EV/Revenue (TTM)`: Enterprise Value to Revenue.
- `EV/EBITDA (TTM)`: Enterprise Value to EBITDA.
- `Price/FCF (TTM)`: Price to Free Cash Flow.

### Financial Health
- `Return on Equity (ROE TTM)`: Return on Equity.
- `Return on Assets (ROA TTM)`: Return on Assets.
- `Debt/Equity (MRQ)`: Total Debt to Total Equity ratio.
- `Total Cash (MRQ)`: Cash and cash equivalents.
- `Total Debt (MRQ)`: Total debt outstanding.
- `Current Ratio (MRQ)`: Current Assets / Current Liabilities.
- `Quick Ratio (MRQ)`: (Current Assets - Inventory) / Current Liabilities.
- `Operating Cash Flow (TTM)`: Net cash from operating activities.
- `Levered Free Cash Flow (TTM)`: Free cash flow available to equity/debt holders.

### Profitability & Growth
- `Profit Margin (TTM)`: Net Profit Margin.
- `Operating Margin (TTM)`: Operating Income Margin.
- `Gross Margin (TTM)`: Gross Profit Margin.
- `EBITDA Margin (TTM)`: EBITDA Margin.
- `Revenue (TTM)`: Total Revenue over last 12 months.
- `Quarterly Revenue Growth (YoY)`: Growth in revenue vs same quarter last year.
- `Gross Profit (TTM)`: Total Gross Profit.
- `EBITDA (TTM)`: Earnings Before Interest, Taxes, Depreciation, and Amortization.
- `Net Income (TTM)`: Net Income to Common Shareholders.
- `Earnings Growth (YoY)`: Growth in earnings vs same quarter last year.

### Financial Efficiency
- `Asset Turnover (TTM)`: Revenue / Total Assets.
- `Inventory Turnover (TTM)`: Cost of Revenue / Inventory.
- `Receivables Turnover (TTM)`: Revenue / Net Receivables.
- `Working Capital Turnover (TTM)`: Revenue / Working Capital.
- `Current Ratio (MRQ)`: Current Assets / Current Liabilities (Repeated for context).
- `Days Sales Outstanding`: Average days to collect receivables (DSO).
- `Days Inventory Outstanding`: Average days to sell inventory (DIO).
- `Cash Conversion Cycle`: (DIO + DSO) - DPO (Partial calculation).
- `Return on Invested Capital (ROIC TTM)`: Net Income / Invested Capital.

### Share Statistics
- `Shares Outstanding`: Total shares issued and currently held by investors.
- `Implied Shares Outstanding`: Total shares assuming conversion of convertibles.
- `Shares Float`: Shares available for trading.
- `Insider Ownership`: Percentage of shares held by insiders.
- `Institutional Ownership`: Percentage of shares held by institutions.
- `Shares Short`: Number of shares sold short.
- `Shares Change (YoY)`: Change in shares outstanding (if available).

### Dividends & Splits
- `Dividend Rate`: Annual dividend per share.
- `Dividend Yield`: Annual dividend yield percentage.
- `Payout Ratio`: Percentage of earnings paid as dividends.
- `5 Year Average Dividend Yield`: Historical average yield.
- `Forward Annual Dividend Rate`: Projected annual dividend.
- `Forward Annual Dividend Yield`: Projected yield.
- `Trailing Dividend Rate`: Trailing annual dividend.
- `Trailing Dividend Yield`: Trailing yield.
- `Ex-Dividend Date`: Date of last ex-dividend.
- `Last Split Date`: Date of last stock split.
- `Last Split Factor`: Ratio of the last split.

### Total Valuation
- `Market Cap`: (Repeated)
- `Enterprise Value`: Market Cap + Total Debt - Total Cash.
- `EV/Revenue (TTM)`: (Repeated)
- `EV/EBITDA (TTM)`: (Repeated)
- `Next Earnings Date`: Estimated date of next earnings report.
- `Ex-Dividend Date`: (Repeated)

### Stock Price Statistics
- `52 Week High`: Highest price in last 52 weeks.
- `52 Week Low`: Lowest price in last 52 weeks.
- `50 Day MA`: 50-Day Moving Average price.
- `200 Day MA`: 200-Day Moving Average price.
- `52 Week Change`: Percentage change over 52 weeks.
- `Beta`: Measure of stock volatility relative to the market.
- `Average Volume (3 month)`: Average trading volume over 3 months.

### Short Selling Information
- `Shares Short`: (Repeated)
- `Short Ratio (Days To Cover)`: Days required to cover all short positions.
- `Short % of Float`: Percentage of float that is shorted.
- `Shares Short (Prior Month)`: Previous month's short interest.
- `Short Date`: Date of the short interest report.

## 2. Analyst & Sentiment Analysis

### Analyst Info
- `Recommendation`: Consensus rating (Buy, Sell, Hold, etc.).
- `Mean Target Price`: Average price target.
- `Median Target Price`: Median price target.
- `High Target Price`: Highest analyst price target.
- `Low Target Price`: Lowest analyst price target.
- `Number of Analyst Opinions`: Count of analysts covering the stock.

### Sentiment Analysis
- `Composite Sentiment Score`: Aggregate score from News, Analyst, and Options.
- `Sentiment Classification`: Textual classification (e.g., "Bullish").
- `Sentiment Confidence`: Confidence level in the sentiment score.
- `News Sentiment`: Individual score and class for News.
- `Analyst Sentiment`: Individual score and class for Analysts.
- `Options Sentiment`: Individual score and class for Options activity.
- `Put/Call Ratio`: Ratio of Put options to Call options volumes.

## 3. Technical Analysis (TA)

Calculated based on historical price and volume data.

### Price & Volume
- `Current_Price`: Latest closing price.
- `change_15d_pct`: 15-day price change percentage.
- `Volume_SMA20`: 20-day Simple Moving Average of Volume.
- `Volume_vs_SMA20_Ratio`: Ratio of current volume to 20-day average.
- `Volume_Trend_5D`: 5-day volume trend description ("Increasing", "Decreasing", "Mixed").

### Trend Indicators
- `SMA_20`: 20-day Simple Moving Average of Price.
- `SMA_50`: 50-day Simple Moving Average of Price.
- `SMA_100`: 100-day Simple Moving Average of Price.
- `SMA_200`: 200-day Simple Moving Average of Price.

### Momentum Indicators
- `RSI_14`: 14-day Relative Strength Index.
    - *Interpretation*: >70 Overbought, <30 Oversold.
- `MACD_Line`: MACD Line value.
- `MACD_Signal`: Signal Line value.
- `MACD_Hist`: MACD Histogram value.
- `MACD_Hist_Prev`: Previous day's MACD Histogram value (for crossover detection).

### Volatility Indicators
- `BB_Upper`: Bollinger Band Upper.
- `BB_Middle`: Bollinger Band Middle (20-day SMA).
- `BB_Lower`: Bollinger Band Lower.

### Support & Resistance
- `Support_30D`: Lowest low in the last 30 days.
- `Resistance_30D`: Highest high in the last 30 days.

## 4. Risk Analysis

Metrics derived from historical price volatility and statistical modeling.

- `Volatility (30d Ann.)`: Annualized volatility based on last 30 days.
- `Volatility (Historical Ann.)`: Annualized volatility over full history.
- `Value at Risk (5%)`: Max expected loss with 95% confidence.
- `Value at Risk (1%)`: Max expected loss with 99% confidence.
- `Sharpe Ratio`: Risk-adjusted return metric.
- `Sortino Ratio`: Risk-adjusted return using downside deviation.
- `Maximum Drawdown`: Maximum observed loss from peak to trough.
- `Skewness`: Measure of asymmetry in return distribution.
- `Kurtosis`: Measure of "tailedness" in return distribution.
- `Beta`: (Repeated) Sensitivity to market movements.
- `Market Correlation`: Correlation co-efficient with market index.

## 5. Peer Comparison

Comparative metrics against industry peers.

- `Peers`: List of peer ticker symbols.
- `Market Cap Rank`: Rank among peers by market cap.
- `P/E Rank`: Rank among peers by P/E ratio.
- `Performance Rank (1Y)`: Rank among peers by 1-year return.
- `Peer Valuation`: Average valuation metrics of peers.
- `Peer Performance`: Average performance metrics of peers.

## 6. Quarterly Earnings

Recent quarterly performance data.

- `Q1` - `Q4`: Keys for the last 4 quarters.
  - `Total Revenue`: Revenue for the quarter.
  - `Net Income`: Net income for the quarter.
  - `Gross Profit`: Gross profit for the quarter.
  - `Operating Income`: Operating income.
  - `Diluted EPS`: Diluted earnings per share.
  - `Basic EPS`: Basic earnings per share.
  - `Gross Margin`: Gross profit margin percentage.
- `QoQ Revenue Growth`: Quarter-over-Quarter revenue growth.
- `QoQ Net Income Growth`: Quarter-over-Quarter net income growth.
- `YoY Revenue Growth`: Year-over-Year revenue growth.
- `Next Earnings Date`: Upcoming earnings announcement date.
- `Earnings Call Time`: Time of the earnings call.

