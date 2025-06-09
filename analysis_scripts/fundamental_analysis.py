# fundamental_analysis.py
import pandas as pd
import numpy as np
from datetime import datetime # Import datetime

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

def format_value(value, value_type="number", precision=2, currency='$'):
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
            return f"{currency}{num:,.{precision}f}"
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
            # If currency symbol needed, apply it here or pass formatted string
            num = float(value) # Ensure it's float for comparison
            if abs(num) >= 1e12: return f"{currency}{num / 1e12:.{precision}f} T"
            elif abs(num) >= 1e9: return f"{currency}{num / 1e9:.{precision}f} B"
            elif abs(num) >= 1e6: return f"{currency}{num / 1e6:.{precision}f} M"
            elif abs(num) >= 1e3: return f"{currency}{num / 1e3:.{precision}f} K"
            else: return f"{currency}{num:,.0f}" # No decimals for small large numbers
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

def extract_valuation_metrics(fundamentals: dict, currency='$'):
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
        "Revenue Growth (YoY)": format_value(safe_get(info, 'revenueGrowth'), 'percent'), # Quarterly YoY usually
        "Gross Profit (TTM)": format_value(safe_get(info, 'grossProfits'), 'large_number'),
        "EBITDA (TTM)": format_value(safe_get(info, 'ebitda'), 'large_number'),
        "Net Income (TTM)": format_value(safe_get(info, 'netIncomeToCommon'), 'large_number'),
        "Earnings Growth (YoY)": format_value(safe_get(info, 'earningsGrowth'), 'percent'), # Quarterly YoY usually
    }
    return metrics

def extract_dividends_splits(fundamentals: dict, currency='$'):
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
        "Dividend Rate": format_value(safe_get(info, 'dividendRate'), 'currency', currency=currency),
        "Dividend Yield": format_value(safe_get(info, 'dividendYield'), 'percent_direct'),
        "Payout Ratio": format_value(safe_get(info, 'payoutRatio'), 'percent'),
        "5 Year Average Dividend Yield": format_value(safe_get(info, 'fiveYearAvgDividendYield'), 'percent_direct'), # This one is often a direct percentage
        "Forward Annual Dividend Rate": format_value(safe_get(info, 'forwardDividendRate'), 'currency', currency=currency),
        "Forward Annual Dividend Yield": format_value(safe_get(info, 'forwardDividendYield'), 'percent_direct'), 
        "Trailing Dividend Rate": format_value(safe_get(info, 'trailingAnnualDividendRate'), 'currency', currency=currency),
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

def extract_news(fundamentals: dict):
    """Extracts recent news headlines."""
    # --- This function remains the same as before ---
    news_data = fundamentals.get('news')
    headlines = []
    if isinstance(news_data, list) and news_data:
        for item in news_data[:5]: # Get top 5 headlines
             if isinstance(item, dict):
                 headlines.append({
                     'title': item.get('title', 'N/A'),
                     'publisher': item.get('publisher', 'N/A'),
                     'link': item.get('link', '#'),
                     'published': format_value(item.get('providerPublishTime'), 'date') # Use formatter
                 })
    return headlines


# --- NEW Extraction Functions ---

def extract_total_valuation_data(fundamentals: dict, current_price=None, currency='$'):
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
            enterprise_value = format_value(ev, 'large_number', currency=currency)
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


    metrics = {
        "Market Cap": format_value(market_cap, 'large_number', currency=currency),
        "Enterprise Value": format_value(enterprise_value, 'large_number', currency=currency),
        "EV/Revenue (TTM)": format_value(ev_revenue, 'ratio') if ev_revenue != "N/A" else "N/A",
        "EV/EBITDA (TTM)": format_value(ev_ebitda, 'ratio') if ev_ebitda != "N/A" else "N/A",
        "Next Earnings Date": format_value(safe_get(info, 'earningsTimestamp'), 'date'), # Approximation
        "Ex-Dividend Date": format_value(safe_get(info, 'exDividendDate'), 'date'),
    }
    return metrics

def extract_share_statistics_data(fundamentals: dict, current_price=None, currency='$'):
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
    total_revenue = safe_get(info, 'totalRevenue')
    total_assets = safe_get(info, 'totalAssets') # Not always available in 'info'
    asset_turnover = "N/A"

    # Calculate Asset Turnover if possible
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

    metrics = {
        "Asset Turnover (TTM)": asset_turnover,
        "Inventory Turnover (TTM)": format_value(safe_get(info, 'inventoryTurnover'), 'ratio'), # Often N/A
        "Receivables Turnover (TTM)": format_value(safe_get(info, 'receivablesTurnover'), 'ratio'), # Often N/A
        "Return on Invested Capital (ROIC TTM)": "N/A", # Requires calculation from financials (NOPAT / Invested Capital)
    }
    return metrics


def extract_stock_price_stats_data(fundamentals: dict, currency='$'):
    """Extracts data for the Stock Price Statistics section."""
    info = fundamentals.get('info', {})
    metrics = {
        "52 Week High": format_value(safe_get(info, 'fiftyTwoWeekHigh'), 'currency', currency=currency),
        "52 Week Low": format_value(safe_get(info, 'fiftyTwoWeekLow'), 'currency', currency=currency),
        "50 Day MA": format_value(safe_get(info, 'fiftyDayAverage'), 'currency', currency=currency),
        "200 Day MA": format_value(safe_get(info, 'twoHundredDayAverage'), 'currency', currency=currency),
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
        "Short % of Float": format_value(safe_get(info, 'shortPercentOfFloat'), 'percent_direct'),
        "Shares Short (Prior Month)": format_value(safe_get(info, 'sharesShortPriorMonth'), 'large_number', 0),
        "Short Date": format_value(safe_get(info, 'dateShortInterest'), 'date'), # Date of last short interest report
    }
    return metrics