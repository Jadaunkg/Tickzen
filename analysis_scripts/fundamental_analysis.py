# fundamental_analysis.py
import pandas as pd
import numpy as np
import logging
from datetime import datetime # Import datetime

# Import the new analysis modules with proper fallback handling
try:
    # Try relative import first (when imported as part of analysis_scripts package)
    from .risk_analysis import RiskAnalyzer
    from .sentiment_analysis import SentimentAnalyzer
except ImportError:
    try:
        # Try absolute import from analysis_scripts package
        from analysis_scripts.risk_analysis import RiskAnalyzer
        from analysis_scripts.sentiment_analysis import SentimentAnalyzer
    except ImportError:
        # Final fallback for direct execution
        try:
            from risk_analysis import RiskAnalyzer
            from sentiment_analysis import SentimentAnalyzer
        except ImportError:
            # If all imports fail, create dummy classes
            logging.warning("Could not import RiskAnalyzer and SentimentAnalyzer. Using dummy classes.")
            class RiskAnalyzer:
                def __init__(self):
                    pass
                def analyze_risk(self, *args, **kwargs):
                    return {'risk_score': 'N/A', 'risk_factors': []}
            
            class SentimentAnalyzer:
                def __init__(self):
                    pass
                def analyze_sentiment(self, *args, **kwargs):
                    return {'sentiment': 'Neutral', 'score': 0}

# --- Helpers ---

def safe_get(data_dict, key, default="N/A"):
    """Safely get a value from a dictionary, checking for None and NaN."""
    if data_dict is None:
        return default
    value = data_dict.get(key, default)
    # Handle cases where yfinance might return None or NaN-like values
    # Check for pandas NaN specifically
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return default
    # Sometimes yfinance returns strings like 'Infinity' or empty strings
    if isinstance(value, str) and (value.lower() == 'infinity' or value.strip() == ''):
        return default
    return value

def format_value(value, value_type="number", precision=2, ticker=None):
    """Formats values for display, handling 'N/A' and potential errors."""
    if value == "N/A" or value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"

    try:
        # Attempt to convert to float, except for date/string types
        if value_type not in ["date", "string", "factor"]:
            num = float(value)
        else:
            num = value # Keep as original type for date/string

        if value_type == "currency":
            # Import currency function locally to avoid circular imports
            from app.html_components import get_currency_symbol
            currency_symbol = get_currency_symbol(ticker) if ticker else "$"
            return f"{currency_symbol}{num:,.{precision}f}"
        elif value_type == "percent":
            # Assumes input is a fraction (e.g., 0.25 for 25%)
            return f"{num * 100:.{precision}f}%"
        elif value_type == "percent_direct":
            # Assumes input is already a percentage number (e.g., 25 for 25%)
            return f"{num:.{precision}f}%"
        elif value_type == "ratio":
             # Check if number is extremely large or small before formatting
             if abs(num) > 1e6 or (abs(num) < 1e-3 and num != 0):
                 return f"{num:.{precision}e}x" # Use scientific notation for extremes
             return f"{num:.{precision}f}x"
        elif value_type == "large_number":
            # Handles formatting large numbers with B, M, K suffixes
            # Remove currency symbols from large number formatting
            num = float(value) # Ensure it's float for comparison
            if abs(num) >= 1e12: return f"{num / 1e12:.{precision}f} T"
            elif abs(num) >= 1e9: return f"{num / 1e9:.{precision}f} B"
            elif abs(num) >= 1e6: return f"{num / 1e6:.{precision}f} M"
            elif abs(num) >= 1e3: return f"{num / 1e3:.{precision}f} K"
            else: return f"{num:,.0f}" # No decimals for small large numbers
        elif value_type == "integer":
             return f"{int(float(num)):,}" # Convert via float first for safety
        elif value_type == "date":
             # Assuming value might be epoch seconds (common in yfinance)
             try:
                 # Check if it's already a datetime object
                 if isinstance(num, datetime):
                     return num.strftime('%Y-%m-%d')
                 # Otherwise, assume it's a timestamp (integer or float)
                 return pd.to_datetime(num, unit='s').strftime('%Y-%m-%d')
             except (ValueError, TypeError, OverflowError):
                 return str(value) # Fallback if conversion fails
        elif value_type == "factor": # For split factors like '2:1'
             return str(value)
        elif value_type == "string":
            return str(value)
        else: # Default number format
            return f"{num:,.{precision}f}"
    except (ValueError, TypeError):
        # Fallback for values that cannot be converted to float (like split factors)
        return str(value)

# --- Existing Extraction Functions (Refined) ---

def extract_company_profile(fundamentals: dict):
    """Extracts key company profile info."""
    info = fundamentals.get('info', {})
    profile = {
        "Company Name": safe_get(info, 'longName', safe_get(info, 'shortName', 'N/A')), # Fallback to shortName
        "Sector": safe_get(info, 'sector', 'N/A'),
        "Industry": safe_get(info, 'industry', 'N/A'),
        "Website": safe_get(info, 'website', 'N/A'),
        "Market Cap": format_value(safe_get(info, 'marketCap'), 'large_number'),
        "Employees": format_value(safe_get(info, 'fullTimeEmployees'), 'integer'),
        "Summary": safe_get(info, 'longBusinessSummary', 'No summary available.')
    }
    return profile

def extract_valuation_metrics(fundamentals: dict):
    """Extracts key valuation metrics."""
    info = fundamentals.get('info', {})

    # Try to get Levered FCF for P/FCF calculation
    total_cash = safe_get(info, 'totalCash')
    market_cap = safe_get(info, 'marketCap')
    levered_fcf = safe_get(info, 'freeCashflow') # Often represents levered FCF in yfinance
    p_fcf = "N/A"

    if market_cap != "N/A" and levered_fcf != "N/A":
        try:
            mcap_f = float(market_cap)
            fcf_f = float(levered_fcf)
            if fcf_f != 0:
                p_fcf_val = mcap_f / fcf_f
                p_fcf = format_value(p_fcf_val, 'ratio')
            else:
                p_fcf = "N/A (Zero FCF)"
        except (ValueError, TypeError):
            p_fcf = "N/A (Calc Error)"

    metrics = {
        "Trailing P/E": format_value(safe_get(info, 'trailingPE'), 'ratio'),
        "Forward P/E": format_value(safe_get(info, 'forwardPE'), 'ratio'),
        "Price/Sales (TTM)": format_value(safe_get(info, 'priceToSalesTrailing12Months'), 'ratio'),
        "Price/Book (MRQ)": format_value(safe_get(info, 'priceToBook'), 'ratio'),
        "PEG Ratio": format_value(safe_get(info, 'pegRatio'), 'ratio'),
        "EV/Revenue (TTM)": format_value(safe_get(info, 'enterpriseToRevenue'), 'ratio'),
        "EV/EBITDA (TTM)": format_value(safe_get(info, 'enterpriseToEbitda'), 'ratio'),
        "Price/FCF (TTM)": format_value(safe_get(info, 'priceToFreeCashFlow'), 'ratio')
    }
    return metrics

def extract_financial_health(fundamentals: dict):
    """Extracts key financial health metrics."""
    info = fundamentals.get('info', {})

    # FIX: Correct for potential percentage-based Debt/Equity from yfinance
    debt_equity_raw = safe_get(info, 'debtToEquity')
    debt_equity_corrected = debt_equity_raw
    try:
        # Heuristic: If D/E ratio is unusually high, assume it was given as a percentage
        if debt_equity_raw != "N/A" and float(debt_equity_raw) > 10.0:
            debt_equity_corrected = float(debt_equity_raw) / 100.0
    except (ValueError, TypeError):
        # If conversion fails, keep the original value
        debt_equity_corrected = debt_equity_raw

    metrics = {
        "Return on Equity (ROE TTM)": format_value(safe_get(info, 'returnOnEquity'), 'percent'),
        "Return on Assets (ROA TTM)": format_value(safe_get(info, 'returnOnAssets'), 'percent'),
        "Debt/Equity (MRQ)": format_value(debt_equity_corrected, 'ratio'),
        "Total Cash (MRQ)": format_value(safe_get(info, 'totalCash'), 'large_number'),
        "Total Debt (MRQ)": format_value(safe_get(info, 'totalDebt'), 'large_number'),
        "Current Ratio (MRQ)": format_value(safe_get(info, 'currentRatio'), 'ratio'),
        "Quick Ratio (MRQ)": format_value(safe_get(info, 'quickRatio'), 'ratio'),
        "Operating Cash Flow (TTM)": format_value(safe_get(info, 'operatingCashflow'), 'large_number'),
        "Levered Free Cash Flow (TTM)": format_value(safe_get(info, 'freeCashflow'), 'large_number'),
    }
    return metrics

def extract_profitability(fundamentals: dict):
    """Extracts key profitability and growth metrics."""
    info = fundamentals.get('info', {})
    metrics = {
        "Profit Margin (TTM)": format_value(safe_get(info, 'profitMargins'), 'percent'),
        "Operating Margin (TTM)": format_value(safe_get(info, 'operatingMargins'), 'percent'),
        "Gross Margin (TTM)": format_value(safe_get(info, 'grossMargins'), 'percent'),
        "EBITDA Margin (TTM)": format_value(safe_get(info, 'ebitdaMargins'), 'percent'),
        "Revenue (TTM)": format_value(safe_get(info, 'totalRevenue'), 'large_number'),
        "Quarterly Revenue Growth (YoY)": format_value(safe_get(info, 'revenueGrowth'), 'percent'), # Quarterly YoY growth
        "Gross Profit (TTM)": format_value(safe_get(info, 'grossProfits'), 'large_number'),
        "EBITDA (TTM)": format_value(safe_get(info, 'ebitda'), 'large_number'),
        "Net Income (TTM)": format_value(safe_get(info, 'netIncomeToCommon'), 'large_number'),
        "Earnings Growth (YoY)": format_value(safe_get(info, 'earningsGrowth'), 'percent'), # Quarterly YoY usually
    }
    return metrics

def extract_dividends_splits(fundamentals: dict):
    """
    FIX: Extracts dividend and stock split information.
    This version now passes raw values for formatting downstream and removes
    the problematic standardization function that was causing errors.
    """
    info = fundamentals.get('info', {})
    
    # The problematic _standardize_percent_value function has been removed.
    # We now pass the raw values directly, assuming that values like 'dividendYield'
    # are provided as fractions (e.g., 0.0088 for 0.88%) by the API.
    # The formatting is handled correctly by the `format_value` helper later on.
    
    metrics = {
        "Dividend Rate": format_value(safe_get(info, 'dividendRate'), 'currency'),
        "Dividend Yield": format_value(safe_get(info, 'dividendYield'), 'percent_direct'),
        "Payout Ratio": format_value(safe_get(info, 'payoutRatio'), 'percent'),
        "5 Year Average Dividend Yield": format_value(safe_get(info, 'fiveYearAvgDividendYield'), 'percent_direct'), # This one is often a direct percentage
        "Forward Annual Dividend Rate": format_value(safe_get(info, 'forwardDividendRate'), 'currency'),
        "Forward Annual Dividend Yield": format_value(safe_get(info, 'forwardDividendYield'), 'percent_direct'), 
        "Trailing Dividend Rate": format_value(safe_get(info, 'trailingAnnualDividendRate'), 'currency'),
        "Trailing Dividend Yield": format_value(safe_get(info, 'trailingAnnualDividendYield'), 'percent_direct'),
        "Ex-Dividend Date": format_value(safe_get(info, 'exDividendDate'), 'date'),
        "Last Split Date": format_value(safe_get(info, 'lastSplitDate'), 'date'),
        "Last Split Factor": safe_get(info, 'lastSplitFactor', 'N/A'),
    }
    return metrics


def extract_analyst_info(fundamentals: dict):
    """Extracts analyst recommendation and target price info."""
    
    info = fundamentals.get('info', {})
    recommendations_data = fundamentals.get('recommendations')
    recommendation_summary = "N/A"
    strong_buy, buy, hold, sell, strong_sell = 0, 0, 0, 0, 0
    total_ratings = 0

    # Process List format (less common now?)
    if isinstance(recommendations_data, list) and recommendations_data:
        grades = [rec.get('toGrade', '').lower() for rec in recommendations_data if isinstance(rec, dict) and rec.get('toGrade')]
        for grade in grades:
             if any(term in grade for term in ['strong buy', 'buy', 'outperform', 'overweight', 'accumulate']): strong_buy += 1
             elif any(term in grade for term in ['hold', 'neutral', 'peer perform', 'equal-weight', 'market perform']): hold += 1
             elif any(term in grade for term in ['sell', 'strong sell', 'underperform', 'underweight', 'reduce']): strong_sell += 1
        total_ratings = strong_buy + hold + strong_sell

    # Process DataFrame format
    elif isinstance(recommendations_data, pd.DataFrame) and not recommendations_data.empty:
        if 'To Grade' in recommendations_data.columns:
            grades = recommendations_data['To Grade'].astype(str).str.lower().tolist()
            for grade in grades:
                 if any(term in grade for term in ['strong buy', 'buy', 'outperform', 'overweight', 'accumulate']): strong_buy += 1
                 elif any(term in grade for term in ['hold', 'neutral', 'peer perform', 'equal-weight', 'market perform']): hold += 1
                 elif any(term in grade for term in ['sell', 'strong sell', 'underperform', 'underweight', 'reduce']): strong_sell += 1
            total_ratings = strong_buy + hold + strong_sell

    # Determine consensus string
    if total_ratings > 0:
        if strong_buy / total_ratings >= 0.6: recommendation_summary = f"Strong Buy ({total_ratings} Ratings)"
        elif (strong_buy + hold) / total_ratings >= 0.7 and strong_buy > strong_sell: recommendation_summary = f"Buy ({total_ratings} Ratings)"
        elif strong_sell / total_ratings >= 0.6: recommendation_summary = f"Sell ({total_ratings} Ratings)"
        elif (strong_sell + hold) / total_ratings >= 0.7 and strong_sell > strong_buy: recommendation_summary = f"Underperform ({total_ratings} Ratings)"
        else: recommendation_summary = f"Hold ({total_ratings} Ratings)"
    elif 'recommendationKey' in info: # Fallback to simple key if no detailed ratings
         recommendation_summary = safe_get(info, 'recommendationKey', 'N/A').replace('_', ' ').title()
    else: # If still N/A
        recommendation_summary = "N/A"


    metrics = {
        "Recommendation": recommendation_summary,
        "Mean Target Price": format_value(safe_get(info, 'targetMeanPrice'), 'currency'),
        "High Target Price": format_value(safe_get(info, 'targetHighPrice'), 'currency'),
        "Low Target Price": format_value(safe_get(info, 'targetLowPrice'), 'currency'),
        "Number of Analyst Opinions": format_value(safe_get(info, 'numberOfAnalystOpinions'), 'integer'),
    }
    return metrics

def extract_news(fundamentals: dict, ticker=None):
    """Extracts recent news headlines using Finnhub API."""
    headlines = []
    
    # First try to get news from yfinance (fallback)
    news_data = fundamentals.get('news')
    if isinstance(news_data, list) and news_data:
        for item in news_data[:5]: # Get top 5 headlines
             if isinstance(item, dict):
                 # Handle new yfinance structure where news is nested under 'content'
                 if 'content' in item:
                     content = item['content']
                     # Extract provider info
                     provider_info = content.get('provider', {})
                     provider_name = provider_info.get('displayName', 'N/A') if isinstance(provider_info, dict) else str(provider_info)
                     
                     headlines.append({
                         'title': content.get('title', 'N/A'),
                         'publisher': provider_name,
                         'link': content.get('canonicalUrl', content.get('clickThroughUrl', '#')),
                         'published': format_value(content.get('pubDate'), 'date') # Use pubDate for new structure
                     })
                 else:
                     # Handle old yfinance structure (fallback)
                     headlines.append({
                         'title': item.get('title', 'N/A'),
                         'publisher': item.get('publisher', 'N/A'),
                         'link': item.get('link', '#'),
                         'published': format_value(item.get('providerPublishTime'), 'date')
                     })
        if headlines:  # If we got news from yfinance, return it
            return headlines
    
    # If no news from yfinance or empty, try Finnhub
    if ticker:
        try:
            import finnhub
            from config.config import FINNHUB_API_KEY
            
            if not FINNHUB_API_KEY:
                print("Warning: FINNHUB_API_KEY not found. Please set the environment variable.")
                return headlines
            
            # Initialize Finnhub client
            finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
            
            # Get company news from Finnhub
            from datetime import datetime, timedelta
            to_date = datetime.now()
            from_date = to_date - timedelta(days=30)  # Get news from last 30 days
            
            # Format dates for Finnhub API (YYYY-MM-DD)
            from_str = from_date.strftime('%Y-%m-%d')
            to_str = to_date.strftime('%Y-%m-%d')
            
            # Fetch news
            news_response = finnhub_client.company_news(ticker, _from=from_str, to=to_str)
            
            if isinstance(news_response, list) and news_response:
                for item in news_response[:5]:  # Get top 5 headlines
                    if isinstance(item, dict):
                        # Convert Unix timestamp to readable date
                        published_time = item.get('datetime', 0)
                        if published_time:
                            published_date = datetime.fromtimestamp(published_time).strftime('%Y-%m-%d')
                        else:
                            published_date = 'N/A'
                            
                        headlines.append({
                            'title': item.get('headline', 'N/A'),
                            'publisher': item.get('source', 'N/A'),
                            'link': item.get('url', '#'),
                            'published': published_date
                        })
            
        except Exception as e:
            print(f"Error fetching news from Finnhub for {ticker}: {str(e)}")
            # If Finnhub fails, return any yfinance headlines we might have
            pass
    
    return headlines


# --- NEW Extraction Functions ---

def extract_total_valuation_data(fundamentals: dict, current_price=None):
    """Extracts/Calculates data for the Total Valuation section."""
    info = fundamentals.get('info', {})
    market_cap = safe_get(info, 'marketCap')
    total_debt = safe_get(info, 'totalDebt')
    total_cash = safe_get(info, 'totalCash')
    enterprise_value = safe_get(info, 'enterpriseValue')
    ev_revenue = safe_get(info, 'enterpriseToRevenue', "N/A") # Check if direct value exists
    ev_ebitda = safe_get(info, 'enterpriseToEbitda', "N/A") # Check if direct value exists

    # Calculate Enterprise Value if possible
    if market_cap != "N/A" and total_debt != "N/A" and total_cash != "N/A":
        try:
            ev = float(market_cap) + float(total_debt) - float(total_cash)
            enterprise_value = format_value(ev, 'large_number')
        except (ValueError, TypeError):
            enterprise_value = "N/A (Calc Error)"

    # Use formatted values where available, otherwise calculate
    if enterprise_value != "N/A" and ev_revenue == "N/A":
        total_revenue = safe_get(info, 'totalRevenue')
        if total_revenue != "N/A":
            try:
                ev_f = float(market_cap) + float(total_debt) - float(total_cash)
                rev_f = float(total_revenue)
                if rev_f != 0: ev_revenue = format_value(ev_f / rev_f, 'ratio')
            except: pass # Keep N/A if calc fails

    if enterprise_value != "N/A" and ev_ebitda == "N/A":
        ebitda = safe_get(info, 'ebitda')
        if ebitda != "N/A":
             try:
                 ev_f = float(market_cap) + float(total_debt) - float(total_cash)
                 ebitda_f = float(ebitda)
                 if ebitda_f != 0: ev_ebitda = format_value(ev_f / ebitda_f, 'ratio')
             except: pass # Keep N/A if calc fails


    # Filter earnings timestamp to only future dates
    earnings_ts = safe_get(info, 'earningsTimestamp')
    if earnings_ts != "N/A":
        from datetime import datetime, timezone
        try:
            earnings_date = datetime.fromtimestamp(earnings_ts)
            today = datetime.now(timezone.utc)
            if earnings_date.date() < today.date():
                earnings_ts = "N/A"  # Past date, don't show
        except (ValueError, TypeError, OSError):
            earnings_ts = "N/A"
    
    metrics = {
        "Market Cap": format_value(market_cap, 'large_number'),
        "Enterprise Value": format_value(enterprise_value, 'large_number'),
        "EV/Revenue (TTM)": format_value(ev_revenue, 'ratio') if ev_revenue != "N/A" else "N/A",
        "EV/EBITDA (TTM)": format_value(ev_ebitda, 'ratio') if ev_ebitda != "N/A" else "N/A",
        "Next Earnings Date": format_value(earnings_ts, 'date'),
        "Ex-Dividend Date": format_value(safe_get(info, 'exDividendDate'), 'date'),
    }
    return metrics

def extract_share_statistics_data(fundamentals: dict, current_price=None):
    """Extracts/Calculates data for the Share Statistics section."""
    info = fundamentals.get('info', {})
    shares_outstanding = safe_get(info, 'sharesOutstanding')
    market_cap = safe_get(info, 'marketCap')

    # Calculate Shares Outstanding if not directly available
    if shares_outstanding == "N/A" and market_cap != "N/A" and current_price is not None:
        try:
            shares_outstanding = float(market_cap) / float(current_price)
        except (ValueError, TypeError, ZeroDivisionError):
            shares_outstanding = "N/A (Calc Error)"

    metrics = {
        "Shares Outstanding": format_value(shares_outstanding, 'large_number', 0),
        "Implied Shares Outstanding": format_value(safe_get(info, 'impliedSharesOutstanding'), 'large_number', 0),
        "Shares Float": format_value(safe_get(info, 'floatShares'), 'large_number', 0),
        "Insider Ownership": format_value(safe_get(info, 'heldPercentInsiders'), 'percent'),
        "Institutional Ownership": format_value(safe_get(info, 'heldPercentInstitutions'), 'percent'),  
        "Shares Short": format_value(safe_get(info, 'sharesShort'), 'large_number', 0),
        "Shares Change (YoY)": "N/A",
    }
    return metrics


def extract_financial_efficiency_data(fundamentals: dict):
    """Extracts/Calculates data for the Financial Efficiency section."""
    info = fundamentals.get('info', {})
    
    # Get basic financial data
    total_revenue = safe_get(info, 'totalRevenue')
    total_assets = "N/A"
    inventory = "N/A"
    receivables = "N/A"
    current_assets = "N/A"
    working_capital = "N/A"
    
    # Try to get data from balance sheet if available
    try:
        balance_sheet = fundamentals.get('balance_sheet')
        if balance_sheet is not None and not balance_sheet.empty:
            # Get most recent period (first column)
            recent_period = balance_sheet.columns[0] if len(balance_sheet.columns) > 0 else None
            
            if recent_period is not None:
                if 'Total Assets' in balance_sheet.index:
                    total_assets = balance_sheet.loc['Total Assets', recent_period]
                if 'Inventory' in balance_sheet.index:
                    inventory = balance_sheet.loc['Inventory', recent_period]
                if 'Net Receivables' in balance_sheet.index:
                    receivables = balance_sheet.loc['Net Receivables', recent_period]
                elif 'Accounts Receivable' in balance_sheet.index:
                    receivables = balance_sheet.loc['Accounts Receivable', recent_period]
                if 'Current Assets' in balance_sheet.index:
                    current_assets = balance_sheet.loc['Current Assets', recent_period]
                if 'Working Capital' in balance_sheet.index:
                    working_capital = balance_sheet.loc['Working Capital', recent_period]
    except Exception as e:
        logging.warning(f"Error accessing balance sheet data: {e}")
    
    # Try to get Cost of Revenue from income statement
    cost_of_revenue = "N/A"
    try:
        financials = fundamentals.get('financials')
        if financials is not None and not financials.empty:
            recent_period = financials.columns[0] if len(financials.columns) > 0 else None
            if recent_period is not None:
                if 'Cost Of Revenue' in financials.index:
                    cost_of_revenue = financials.loc['Cost Of Revenue', recent_period]
                elif 'Total Revenue' in financials.index and total_revenue == "N/A":
                    total_revenue = financials.loc['Total Revenue', recent_period]
    except Exception as e:
        logging.warning(f"Error accessing income statement data: {e}")
    
    # Calculate efficiency ratios
    asset_turnover = "N/A"
    inventory_turnover = "N/A"
    receivables_turnover = "N/A"
    current_ratio = safe_get(info, 'currentRatio')  # Available directly
    working_capital_turnover = "N/A"
    
    # Asset Turnover = Revenue / Total Assets
    if total_revenue != "N/A" and total_assets != "N/A":
        try:
            rev = float(total_revenue)
            assets = float(total_assets)
            if assets != 0:
                asset_turnover = format_value(rev / assets, 'ratio')
            else:
                asset_turnover = "N/A (Zero Assets)"
        except (ValueError, TypeError):
            asset_turnover = "N/A (Calc Error)"
    
    # Inventory Turnover = Cost of Revenue / Inventory
    if cost_of_revenue != "N/A" and inventory != "N/A":
        try:
            cogs = float(cost_of_revenue)
            inv = float(inventory)
            if inv != 0:
                inventory_turnover = format_value(cogs / inv, 'ratio')
            else:
                inventory_turnover = "N/A (Zero Inventory)"
        except (ValueError, TypeError):
            inventory_turnover = "N/A (Calc Error)"
    
    # Receivables Turnover = Revenue / Net Receivables
    if total_revenue != "N/A" and receivables != "N/A":
        try:
            rev = float(total_revenue)
            rec = float(receivables)
            if rec != 0:
                receivables_turnover = format_value(rev / rec, 'ratio')
            else:
                receivables_turnover = "N/A (Zero Receivables)"
        except (ValueError, TypeError):
            receivables_turnover = "N/A (Calc Error)"
    
    # Working Capital Turnover = Revenue / Working Capital
    if total_revenue != "N/A" and working_capital != "N/A":
        try:
            rev = float(total_revenue)
            wc = float(working_capital)
            if wc != 0:
                working_capital_turnover = format_value(rev / wc, 'ratio')
            else:
                working_capital_turnover = "N/A (Zero WC)"
        except (ValueError, TypeError):
            working_capital_turnover = "N/A (Calc Error)"
    
    # Calculate Days Sales Outstanding (DSO) = 365 / Receivables Turnover
    days_sales_outstanding = "N/A"
    if receivables_turnover != "N/A" and "N/A" not in str(receivables_turnover):
        try:
            rt_val = float(str(receivables_turnover).replace('x', ''))
            if rt_val != 0:
                days_sales_outstanding = format_value(365 / rt_val, 'number', 1)
        except (ValueError, TypeError):
            pass
    
    # Calculate Days Inventory Outstanding (DIO) = 365 / Inventory Turnover
    days_inventory_outstanding = "N/A"
    if inventory_turnover != "N/A" and "N/A" not in str(inventory_turnover):
        try:
            it_val = float(str(inventory_turnover).replace('x', ''))
            if it_val != 0:
                days_inventory_outstanding = format_value(365 / it_val, 'number', 1)
        except (ValueError, TypeError):
            pass
    
    # Return on Invested Capital (ROIC) - use available data
    roic = "N/A"
    try:
        # Try to get it from info first
        roic_raw = safe_get(info, 'returnOnInvestedCapital')
        if roic_raw != "N/A":
            roic = format_value(roic_raw, 'percent')
        else:
            # Calculate approximate ROIC using available data
            net_income = safe_get(info, 'netIncomeToCommon')
            invested_capital = "N/A"
            
            # Try to get invested capital from balance sheet
            try:
                balance_sheet = fundamentals.get('balance_sheet')
                if balance_sheet is not None and not balance_sheet.empty:
                    recent_period = balance_sheet.columns[0]
                    if 'Invested Capital' in balance_sheet.index:
                        invested_capital = balance_sheet.loc['Invested Capital', recent_period]
            except:
                pass
            
            if net_income != "N/A" and invested_capital != "N/A":
                ni = float(net_income)
                ic = float(invested_capital)
                if ic != 0:
                    roic = format_value(ni / ic, 'percent')
    except (ValueError, TypeError):
        pass
    
    # Cash Conversion Cycle (CCC) = DIO + DSO - DPO (Days Payable Outstanding)
    # For now, we'll calculate what we can with DIO + DSO
    cash_conversion_cycle = "N/A"
    if (days_inventory_outstanding != "N/A" and days_sales_outstanding != "N/A" and 
        "N/A" not in str(days_inventory_outstanding) and "N/A" not in str(days_sales_outstanding)):
        try:
            dio_val = float(str(days_inventory_outstanding))
            dso_val = float(str(days_sales_outstanding))
            # Note: This is incomplete without DPO, but provides partial insight
            partial_ccc = dio_val + dso_val
            cash_conversion_cycle = f"~{partial_ccc:.1f} days (partial)"
        except (ValueError, TypeError):
            pass

    metrics = {
        "Asset Turnover (TTM)": asset_turnover,
        "Inventory Turnover (TTM)": inventory_turnover,
        "Receivables Turnover (TTM)": receivables_turnover,
        "Working Capital Turnover (TTM)": working_capital_turnover,
        "Current Ratio (MRQ)": format_value(current_ratio, 'ratio'),
        "Days Sales Outstanding": days_sales_outstanding,
        "Days Inventory Outstanding": days_inventory_outstanding,
        "Cash Conversion Cycle": cash_conversion_cycle,
        "Return on Invested Capital (ROIC TTM)": roic,
    }
    return metrics


def extract_stock_price_stats_data(fundamentals: dict):
    """Extracts data for the Stock Price Statistics section."""
    info = fundamentals.get('info', {})
    metrics = {
        "52 Week High": format_value(safe_get(info, 'fiftyTwoWeekHigh'), 'currency'),
        "52 Week Low": format_value(safe_get(info, 'fiftyTwoWeekLow'), 'currency'),
        "50 Day MA": format_value(safe_get(info, 'fiftyDayAverage'), 'currency'),
        "200 Day MA": format_value(safe_get(info, 'twoHundredDayAverage'), 'currency'),
        "52 Week Change": format_value(safe_get(info, 'fiftyTwoWeekChange'), 'percent_direct'),
        "Beta": format_value(safe_get(info, 'beta'), 'ratio'),
        "Average Volume (3 month)": format_value(safe_get(info, 'averageVolume3Month'), 'integer')
    }
    return metrics

def extract_short_selling_data(fundamentals: dict):
    """Extracts data for the Short Selling Information section."""
    info = fundamentals.get('info', {})
    metrics = {
        "Shares Short": format_value(safe_get(info, 'sharesShort'), 'large_number', 0),
        "Short Ratio (Days To Cover)": format_value(safe_get(info, 'shortRatio'), 'ratio', 1),
        "Short % of Float": format_value(safe_get(info, 'shortPercentOfFloat'), 'percent'),
        "Shares Short (Prior Month)": format_value(safe_get(info, 'sharesShortPriorMonth'), 'large_number', 0),
        "Short Date": format_value(safe_get(info, 'dateShortInterest'), 'date'), # Date of last short interest report
    }
    return metrics

def extract_peer_comparison_data(ticker):
    """Extracts peer comparison data using the peer_comparison module."""
    try:
        from analysis_scripts.peer_comparison import get_peer_comparison_data
        return get_peer_comparison_data(ticker)
    except Exception as e:
        logging.warning(f"Error extracting peer comparison data: {e}")
        return {}

def extract_risk_analysis_data(historical_data, market_data=None, ticker=None):
    """Extract risk analysis metrics using the RiskAnalyzer module."""
    try:
        logging.info(f"Starting risk analysis for {ticker}")
        
        # Check if RiskAnalyzer is available (might be dummy class)
        if not hasattr(RiskAnalyzer, 'comprehensive_risk_profile'):
            logging.warning(f"RiskAnalyzer not fully available for {ticker}, using dummy class")
            return {}
        
        risk_analyzer = RiskAnalyzer()
        
        if historical_data is None or historical_data.empty:
            logging.warning(f"No historical data available for risk analysis: {ticker}")
            return {}
        
        # Try to find Close column - might be named differently
        close_col = None
        for col in ['Close', 'close', 'Close Price', 'Adj Close']:
            if col in historical_data.columns:
                close_col = col
                break
        
        if close_col is None:
            # If no Close column, check if there's a 'y' column from Prophet data
            if 'y' in historical_data.columns:
                close_col = 'y'
                logging.info(f"Using 'y' column as price data for {ticker}")
            else:
                logging.warning(f"No price column found in historical data for {ticker}. Columns: {historical_data.columns.tolist()}")
                return {}
        
        price_data = historical_data[close_col].dropna()
        
        if len(price_data) < 30:  # Need sufficient data for meaningful risk analysis
            logging.warning(f"Insufficient price data for risk analysis: {ticker} (only {len(price_data)} data points)")
            return {}
        
        logging.info(f"Calculating risk metrics for {ticker} with {len(price_data)} data points using column '{close_col}'")
        
        # Calculate comprehensive risk profile
        risk_metrics = risk_analyzer.comprehensive_risk_profile(price_data, market_data)
        
        # Format the metrics for display
        formatted_metrics = {
            "Volatility (Annualized)": format_value(risk_metrics.get('volatility_annualized') * 100, 'percent_direct', 1),  # Convert decimal to percentage
            "Value at Risk (5%)": format_value(risk_metrics.get('var_5') * 100, 'percent_direct', 2),  # Convert decimal to percentage
            "Value at Risk (1%)": format_value(risk_metrics.get('var_1') * 100, 'percent_direct', 2),  # Convert decimal to percentage
            "Sharpe Ratio": format_value(risk_metrics.get('sharpe_ratio'), 'ratio', 2),
            "Sortino Ratio": format_value(risk_metrics.get('sortino_ratio'), 'ratio', 2),
            "Maximum Drawdown": format_value(risk_metrics.get('max_drawdown') * 100, 'percent_direct', 2),  # Convert decimal to percentage
            "Skewness": format_value(risk_metrics.get('skewness'), 'ratio', 2),
            "Kurtosis": format_value(risk_metrics.get('kurtosis'), 'ratio', 2),
        }
        
        # Add beta and correlation if market data is available
        if market_data is not None:
            formatted_metrics["Beta"] = format_value(risk_metrics.get('beta'), 'ratio', 2)
            formatted_metrics["Market Correlation"] = format_value(risk_metrics.get('correlation_market'), 'ratio', 2)
        
        logging.info(f"Successfully calculated {len(formatted_metrics)} risk metrics for {ticker}")
        return formatted_metrics
        
    except Exception as e:
        logging.error(f"Error in risk analysis for {ticker}: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return {}

def extract_sentiment_analysis_data(fundamentals: dict, ticker=None):
    """Extract sentiment analysis metrics using the SentimentAnalyzer module."""
    try:
        logging.info(f"Starting sentiment analysis for {ticker}")
        
        # Check if SentimentAnalyzer is available (might be dummy class)
        if not hasattr(SentimentAnalyzer, 'analyze_news_sentiment'):
            logging.warning(f"SentimentAnalyzer not fully available for {ticker}, using dummy class")
            return {}
        
        sentiment_analyzer = SentimentAnalyzer()
        
        # Extract news data
        news_data = fundamentals.get('news', [])
        logging.info(f"Found {len(news_data) if news_data else 0} news items for {ticker}")
        
        # Extract analyst data
        analyst_data = extract_analyst_info(fundamentals)
        logging.info(f"Extracted analyst data for {ticker}")
        
        # Analyze different sentiment components
        news_sentiment = sentiment_analyzer.analyze_news_sentiment(news_data)
        logging.info(f"News sentiment for {ticker}: {news_sentiment}")
        
        analyst_sentiment = sentiment_analyzer.analyze_analyst_sentiment(analyst_data)
        logging.info(f"Analyst sentiment for {ticker}: {analyst_sentiment}")
        
        options_sentiment = sentiment_analyzer.analyze_options_sentiment(ticker) if ticker else {'score': 0, 'classification': 'neutral', 'confidence': 0}
        logging.info(f"Options sentiment for {ticker}: {options_sentiment}")
        
        # Calculate composite sentiment
        composite_sentiment = sentiment_analyzer.calculate_composite_sentiment(
            news_sentiment, analyst_sentiment, options_sentiment
        )
        
        logging.info(f"Composite sentiment for {ticker}: {composite_sentiment}")
        
        # Format the metrics for display
        formatted_metrics = {
            "Composite Sentiment Score": format_value(composite_sentiment.get('score'), 'ratio', 2),
            "Sentiment Classification": composite_sentiment.get('classification', 'neutral').title(),
            "Sentiment Confidence": format_value(composite_sentiment.get('confidence') * 100, 'percent_direct', 1),  # Convert decimal to percentage
            "News Sentiment": f"{news_sentiment.get('classification', 'neutral').title()} ({format_value(news_sentiment.get('score'), 'ratio', 2)})",
            "Analyst Sentiment": f"{analyst_sentiment.get('classification', 'neutral').title()} ({format_value(analyst_sentiment.get('score'), 'ratio', 2)})",
            "Options Sentiment": f"{options_sentiment.get('classification', 'neutral').title()} ({format_value(options_sentiment.get('score'), 'ratio', 2)})",
        }
        
        # Add put/call ratio if available
        if 'put_call_ratio' in options_sentiment:
            formatted_metrics["Put/Call Ratio"] = format_value(options_sentiment.get('put_call_ratio'), 'ratio', 2)
        
        logging.info(f"Successfully calculated sentiment metrics for {ticker}")
        return formatted_metrics
        
    except Exception as e:
        logging.error(f"Error in sentiment analysis for {ticker}: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return {}

def extract_quarterly_earnings_data(fundamentals: dict, ticker=None):
    """Extract quarterly earnings performance data."""
    try:
        import yfinance as yf
        
        # Get ticker object to access quarterly data
        ticker_obj = yf.Ticker(ticker) if ticker else None
        if not ticker_obj:
            return {}
        
        # Get quarterly financials
        quarterly_financials = ticker_obj.quarterly_financials
        if quarterly_financials.empty:
            return {}
        
        # Extract key quarterly metrics for last 4 quarters
        quarterly_data = {}
        quarters = quarterly_financials.columns[:4]  # Most recent 4 quarters
        
        key_metrics = ['Total Revenue', 'Net Income', 'Gross Profit', 'Operating Income', 'Diluted EPS', 'Basic EPS']
        
        for i, quarter in enumerate(quarters):
            quarter_key = f"Q{i+1}"
            # Fix quarter name formatting
            if hasattr(quarter, 'strftime'):
                quarter_num = (quarter.month - 1) // 3 + 1  # Calculate quarter number
                quarter_name = f"{quarter.year}-Q{quarter_num}"
            else:
                quarter_name = str(quarter)[:10]
            
            quarterly_data[quarter_key] = {
                'date': quarter_name,
                'quarter_end': quarter
            }
            
            # Extract financial metrics
            for metric in key_metrics:
                if metric in quarterly_financials.index:
                    value = quarterly_financials.loc[metric, quarter]
                    if pd.notna(value):
                        if metric in ['Total Revenue', 'Net Income', 'Gross Profit', 'Operating Income']:
                            # Format large numbers
                            formatted_value = format_value(value, 'large_number')
                        else:
                            # EPS metrics
                            formatted_value = format_value(value, 'ratio', 2)
                        quarterly_data[quarter_key][metric] = formatted_value
                        quarterly_data[quarter_key][f"{metric}_raw"] = value
            
            # Calculate gross margin if possible
            if 'Gross Profit' in quarterly_financials.index and 'Total Revenue' in quarterly_financials.index:
                gross_profit = quarterly_financials.loc['Gross Profit', quarter]
                total_revenue = quarterly_financials.loc['Total Revenue', quarter]
                if pd.notna(gross_profit) and pd.notna(total_revenue) and total_revenue != 0:
                    gross_margin = (gross_profit / total_revenue) * 100
                    quarterly_data[quarter_key]['Gross Margin'] = f"{gross_margin:.1f}%"
                    quarterly_data[quarter_key]['Gross Margin_raw'] = gross_margin
        
        # Calculate growth metrics
        growth_metrics = {}
        if len(quarters) >= 2:
            # Quarter-over-quarter growth (Q1 vs Q2)
            q1_revenue = quarterly_data.get('Q1', {}).get('Total Revenue_raw')
            q2_revenue = quarterly_data.get('Q2', {}).get('Total Revenue_raw')
            if q1_revenue and q2_revenue:
                qoq_revenue_growth = ((q1_revenue - q2_revenue) / q2_revenue) * 100
                growth_metrics['QoQ Revenue Growth'] = f"{qoq_revenue_growth:+.1f}%"
            
            q1_income = quarterly_data.get('Q1', {}).get('Net Income_raw')
            q2_income = quarterly_data.get('Q2', {}).get('Net Income_raw')
            if q1_income and q2_income and q2_income != 0:
                qoq_income_growth = ((q1_income - q2_income) / q2_income) * 100
                growth_metrics['QoQ Net Income Growth'] = f"{qoq_income_growth:+.1f}%"
        
        if len(quarters) >= 4:
            # Use the same yfinance revenueGrowth data for consistency instead of manual calculation
            info = fundamentals.get('info', {})
            yf_revenue_growth = info.get('revenueGrowth')
            if yf_revenue_growth is not None:
                growth_metrics['YoY Revenue Growth'] = f"{yf_revenue_growth * 100:+.1f}%"
            else:
                # Fallback to manual calculation if yfinance data unavailable
                q1_revenue = quarterly_data.get('Q1', {}).get('Total Revenue_raw')
                q4_revenue = quarterly_data.get('Q4', {}).get('Total Revenue_raw')
                if q1_revenue and q4_revenue:
                    yoy_revenue_growth = ((q1_revenue - q4_revenue) / q4_revenue) * 100
                    growth_metrics['YoY Revenue Growth'] = f"{yoy_revenue_growth:+.1f}%"
        
        # Get next earnings date from fundamentals (ONLY future dates)
        info = fundamentals.get('info', {})
        next_earnings = info.get('earningsTimestamp')
        if next_earnings:
            from datetime import datetime, timezone
            earnings_date = datetime.fromtimestamp(next_earnings)
            today = datetime.now(timezone.utc)
            
            # Only set if earnings date is in the future
            if earnings_date.date() >= today.date():
                growth_metrics['Next Earnings Date'] = earnings_date.strftime('%B %d, %Y')
                
                earnings_call_start = info.get('earningsCallTimestampStart')
                if earnings_call_start:
                    call_time = datetime.fromtimestamp(earnings_call_start)
                    growth_metrics['Earnings Call Time'] = call_time.strftime('%B %d, %Y at %I:%M %p ET')
        
        return {
            'quarterly_data': quarterly_data,
            'growth_metrics': growth_metrics,
            'ticker': ticker
        }
        
    except Exception as e:
        logging.error(f"Error extracting quarterly earnings data for {ticker}: {e}")
        return {}