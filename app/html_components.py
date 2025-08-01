import pandas as pd
import numpy as np
import re
from datetime import datetime
import random # Used for random selection in risk factors
import logging # Import logging for better error tracking
import json
import os

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')

# --- HELPER FUNCTIONS (Added Robustness) ---

def _generate_error_html(section_name, error_message="Error generating section content."):
    """Generates a standard error message HTML block."""
    logging.error(f"Error in section '{section_name}': {error_message}")
    # Simple HTML structure for the error message
    return f"""
    <div class='error-section' style='border: 1px solid red; padding: 10px; margin: 10px 0; background-color: #ffeeee;'>
        <p><strong>{get_icon('warning')} Error generating {section_name}:</strong></p>
        <p style='font-family: monospace; font-size: 0.9em;'>{error_message}</p>
        <p><i>Section content could not be generated due to the error above.</i></p>
    </div>"""

def get_icon(type_input):
    """Returns an HTML span element for common icons. Handles None input."""
    icon_type = str(type_input).lower() if type_input is not None else ''
    try:
        icons = {
            'up': ('icon-up', '▲'), 'down': ('icon-down', '▼'), 'neutral': ('icon-neutral', '●'),
            'warning': ('icon-warning', '⚠️'), 'positive': ('icon-positive', '➕'), 'negative': ('icon-negative', '➖'),
            'info': ('icon-info', 'ℹ️'), 'money': ('icon-money', '💰'), 'chart': ('icon-chart', '📊'),
            'health': ('icon-health', '⚕️'), 'efficiency': ('icon-efficiency', '⚙️'), 'growth': ('icon-growth', '📈'),
            'tax': ('icon-tax', '🧾'), 'dividend': ('icon-dividend', '💸'), 'stats': ('icon-stats', '📉'),
            'news': ('icon-news', '📰'), 'faq': ('icon-faq', '❓'), 'peer': ('icon-peer', '👥'),
            'history': ('icon-history', '📜'), 'cash': ('icon-cash', '💵'), 'volume': ('icon-volume', '🔊'),
            'divergence': ('icon-divergence', '↔️')
        }
        css_class, symbol = icons.get(icon_type, ('', ''))
        if css_class:
            return f'<span class="icon {css_class}" title="{icon_type.capitalize()}">{symbol}</span>'
        return '' # Return empty string if type not found
    except Exception as e:
        logging.error(f"Error in get_icon for type '{type_input}': {e}")
        return '' # Return empty string on error

def _safe_float(value, default=None):
    """Helper to safely convert value to float, handling common string formats."""
    if value is None or pd.isna(value):
        return default
    try:
        # Clean common non-numeric chars before conversion
        str_val = str(value).replace('$','').replace(',','').replace('%','').replace('x','').strip()
        if str_val == '' or str_val.lower() == 'n/a':
             return default
        return float(str_val)
    except (ValueError, TypeError):
        logging.debug(f"Could not convert '{value}' to float.", exc_info=False) # Log as debug, not warning
        return default

def get_currency_symbol(ticker):
    """Determine the appropriate currency symbol based on ticker suffix."""
    if not ticker:
        return "$"  # Default to USD
    
    ticker = ticker.upper()
    
    # Indian exchanges (.NS, .BO)
    if ticker.endswith('.NS') or ticker.endswith('.BO'):
        return "₹"
    
    # European exchanges
    elif ticker.endswith('.PA') or ticker.endswith('.F') or ticker.endswith('.DE') or \
         ticker.endswith('.BE') or ticker.endswith('.DU') or ticker.endswith('.HM') or \
         ticker.endswith('.HA') or ticker.endswith('.MU'):
        return "€"
    
    # UK exchanges
    elif ticker.endswith('.L'):
        return "£"
    
    # Canadian exchanges
    elif ticker.endswith('.TO') or ticker.endswith('.V'):
        return "C$"
    
    # Australian exchanges
    elif ticker.endswith('.AX'):
        return "A$"
    
    # Singapore exchanges
    elif ticker.endswith('.SI'):
        return "S$"
    
    # Nordic exchanges (using local currencies)
    elif ticker.endswith('.ST'):  # Stockholm
        return "kr"  # Swedish Krona
    elif ticker.endswith('.CO'):  # Copenhagen
        return "kr"  # Danish Krone
    elif ticker.endswith('.HE'):  # Helsinki
        return "€"   # Euro
    elif ticker.endswith('.OL'):  # Oslo
        return "kr"  # Norwegian Krone
    elif ticker.endswith('.IC'):  # Iceland
        return "kr"  # Icelandic Krona
    
    # New Zealand
    elif ticker.endswith('.NZ'):
        return "NZ$"
    
    # Default to USD for US stocks and others
    else:
        return "$"

def format_html_value(value, format_type="number", precision=2, ticker=None):
    """Safely formats values for HTML display with enhanced error handling and currency support."""
    original_value_repr = repr(value) # For logging
    # print(f"DEBUG: format_html_value called with format_type={format_type}, value={original_value_repr}") # Kept for your debugging if needed
    
    if value is None or value == "N/A" or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        if isinstance(value, str) and ('$' in value or '₹' in value or '€' in value or '£' in value) and format_type != "string":
             if re.match(r'^[₹$€£C\w]*[0-9,.]+[ KMBT]?$', value):
                 # print(f"DEBUG: Value already formatted with currency: {value}")
                 return value
             else:
                 # print(f"DEBUG: Value '{value}' started with currency but failed validation, attempting numeric format.")
                 pass 

        num_value = None
        if format_type not in ["date", "string", "factor"]:
            num_value = _safe_float(value, default=None)
            if num_value is None and format_type != "string": 
                 # print(f"DEBUG: Failed numeric conversion for value {original_value_repr}")
                 return str(value)

        if format_type == "currency": 
            # Format with appropriate currency symbol
            currency_symbol = get_currency_symbol(ticker)
            result = f"{currency_symbol}{num_value:,.{precision}f}"
            # print(f"DEBUG: Formatted currency value: {result}")
            return result
        elif format_type == "percent": return f"{num_value * 100:.{precision}f}%"
        elif format_type == "percent_direct": return f"{num_value:.{precision}f}%"
        elif format_type == "ratio": return f"{num_value:.{precision}f}x"
        elif format_type == "large_number":
            if abs(num_value) >= 1e12: return f"{num_value/1e12:.{precision}f}T"
            elif abs(num_value) >= 1e9: return f"{num_value/1e9:.{precision}f}B"
            elif abs(num_value) >= 1e6: return f"{num_value/1e6:.{precision}f}M"
            elif abs(num_value) >= 1e3: return f"{num_value/1e3:.{precision}f}K"
            else: return f"{num_value:,.{precision}f}"
        elif format_type == "integer": return f"{int(num_value):,}"
        elif format_type == "date": return str(value) 
        elif format_type == "string": return str(value) 
        elif format_type == "factor": return str(value) 
        else: return f"{num_value:,.{precision}f}" 
    except Exception as e:
        # print(f"DEBUG: Error formatting value {original_value_repr}: {str(e)}")
        return str(value)

# --- WRAPPED Component Functions with Site Variations & Deeper Analysis ---
def generate_introduction_html(ticker, rdata):
    """
    Generates a fully dynamic and data-driven introduction for the stock report.
    The language and narrative adapt based on the analyzed data.
    """
    try:
        # --- 1. Extract and Format All Necessary Data ---
        # This part remains the same, as it correctly pulls the dynamic data.
        profile_data = rdata.get('profile_data', {})
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        health_data = rdata.get('financial_health_data', {})
        analyst_data = rdata.get('analyst_info_data', {})
        profit_data = rdata.get('profitability_data', {})

        company_name = profile_data.get('Company Name', ticker)
        industry = profile_data.get('Industry', 'its')
        market_cap_fmt = profile_data.get('Market Cap', 'N/A')

        current_price_val = rdata.get('current_price')
        current_price_fmt = format_html_value(current_price_val, 'currency', ticker=ticker)

        last_date_obj = rdata.get('last_date', datetime.now())
        last_date_fmt = last_date_obj.strftime('%B %Y')

        sma50_val = detailed_ta_data.get('SMA_50')
        sma50_fmt = format_html_value(sma50_val, 'currency', ticker=ticker)
        sma200_val = detailed_ta_data.get('SMA_200')
        sma200_fmt = format_html_value(sma200_val, 'currency', ticker=ticker)
        
        analyst_target_val = _safe_float(analyst_data.get('Mean Target Price')) # Use _safe_float for calculations
        analyst_target_fmt = format_html_value(analyst_target_val, 'currency', ticker=ticker)
        
        upside_pct_val = rdata.get('overall_pct_change', 0.0)
        upside_pct_fmt = f"{upside_pct_val:+.1f}%"
        
        volatility_val = rdata.get('volatility')
        volatility_fmt = format_html_value(volatility_val, 'percent_direct', 1)

        rev_growth_val = _safe_float(profit_data.get('Revenue Growth (YoY)'))
        rev_growth_fmt = format_html_value(rev_growth_val, 'percent_direct')
        
        debt_equity_val = _safe_float(health_data.get('Debt/Equity (MRQ)'))
        debt_equity_fmt = format_html_value(debt_equity_val, 'ratio')
        total_debt_fmt = health_data.get('Total Debt (MRQ)', 'N/A')

        rsi_val = detailed_ta_data.get('RSI_14')
        rsi_fmt = f"{rsi_val:.1f}" if isinstance(rsi_val, (int, float)) else "N/A"
        
        # --- 2. Generate Dynamic Text Snippets based on Data ---

        # Dynamic Momentum Text
        momentum_text = ""
        if current_price_val and sma50_val and sma200_val:
            if current_price_val > sma50_val and current_price_val > sma200_val:
                momentum_text = "showing positive momentum, trading above both its 50-day and 200-day moving averages"
            elif current_price_val < sma50_val and current_price_val < sma200_val:
                momentum_text = "currently in a bearish trend, trading below both its 50-day and 200-day moving averages"
            elif current_price_val > sma50_val and current_price_val < sma200_val:
                momentum_text = "in a mixed technical state, trading above its short-term 50-day average but still under the long-term 200-day trendline"
            else: # price < 50-day but > 200-day
                momentum_text = "experiencing a short-term pullback within a larger uptrend, as it trades below its 50-day average while holding above the 200-day"
        else:
            momentum_text = "exhibiting a complex technical picture"

        # Dynamic Analyst Outlook Text
        analyst_outlook_text = ""
        if analyst_target_val:
            if upside_pct_val > 5:
                analyst_outlook_text = f"Analysts appear optimistic, with a 1-year price target of <strong>{analyst_target_fmt}</strong> (a potential {upside_pct_fmt} upside)"
            elif upside_pct_val < -5:
                analyst_outlook_text = f"Analysts are cautious, with a 1-year price target of <strong>{analyst_target_fmt}</strong> (a potential {upside_pct_fmt} downside)"
            else:
                analyst_outlook_text = f"Analysts project a relatively stable outlook, with a 1-year price target of <strong>{analyst_target_fmt}</strong> (a potential {upside_pct_fmt} change)"
        else:
            analyst_outlook_text = "Analyst price targets are currently unavailable"
        
        # Dynamic Fundamental "Two Stories" Text
        positive_fundamental = ""
        if rev_growth_val is not None and rev_growth_val > 5:
            positive_fundamental = f"solid revenue growth (up {rev_growth_fmt} YoY)"
        else:
            profit_margin_val = _safe_float(profit_data.get('Profit Margin (TTM)'))
            if profit_margin_val is not None and profit_margin_val > 15:
                positive_fundamental = f"strong profitability with a {format_html_value(profit_margin_val, 'percent')} profit margin"
            else:
                positive_fundamental = "a portfolio of established brands"

        negative_fundamental = ""
        if debt_equity_val is not None and debt_equity_val > 2.0:
            negative_fundamental = f"a high debt load (Debt/Equity: {debt_equity_fmt})"
        else:
            earnings_growth_val = _safe_float(profit_data.get('Earnings Growth (YoY)'))
            if earnings_growth_val is not None and earnings_growth_val < 0:
                negative_fundamental = f"a recent contraction in earnings (down {format_html_value(earnings_growth_val, 'percent_direct')} YoY)"
            else:
                negative_fundamental = "intense competition in its sector"

        fundamental_story_text = f"On one hand, the company benefits from {positive_fundamental}. On the other, it faces challenges with {negative_fundamental}."

        # Dynamic "What's Inside" text
        technical_verdict = "Neutral"
        if "bullish" in momentum_text:
            technical_verdict = "Bullish"
        elif "bearish" in momentum_text:
            technical_verdict = "Bearish"

        rsi_condition = "neutral"
        if isinstance(rsi_val, (int, float)):
            if rsi_val > 70: rsi_condition = "overbought"
            elif rsi_val < 30: rsi_condition = "oversold"

        fundamental_verdict = "be cautious"
        if debt_equity_val is not None and debt_equity_val < 1.0:
            fundamental_verdict = "looking solid"

        # --- 3. Construct the Final, Fully Dynamic HTML ---
        # Build the summary sentence only with available data
        summary_parts = []
        if company_name not in [None, '', 'N/A']:
            summary_parts.append(f"<strong>{company_name} ({ticker})</strong>")
        else:
            summary_parts.append(f"<strong>{ticker}</strong>")
        if market_cap_fmt not in [None, '', 'N/A']:
            summary_parts.append(f"a {market_cap_fmt} company")
        if industry not in [None, '', 'N/A', 'its']:
            summary_parts.append(f"operating in the {industry} industry")
        summary_sentence = "This report provides a detailed analysis of " + ", ".join(summary_parts) + "."

        introduction_html = f"""
        <p>{summary_sentence} The core questions for investors is whether the current stock price represents a fair value and if the company is well-positioned for future growth. Would it be wise to invest in {company_name} at this moment? Let's see how well {ticker} stock performs in the current market. </p>
        
        <h2>Here's What You Need to Know Right Now</h2>
        <p>The stock is currently trading at <strong>{current_price_fmt}</strong> (as of {last_date_fmt}), and it's {momentum_text}.</p>
        <p>{analyst_outlook_text}. However, there's significant volatility here (<strong>{volatility_fmt} annualized</strong>), suggesting the potential for wide price swings.</p>
        <p>{company_name}'s fundamental story is nuanced. {fundamental_story_text}</p>
        
        <h2>What's Inside This Analysis?</h2>
        <p>We're not just throwing numbers at you—we're breaking down {ticker}'s stock from every angle so you can make an informed decision:</p>
        <ul>
            <li>✅ <strong>Is now a good time to buy?</strong><br>
            Technicals say, "{technical_verdict}" (but RSI is {rsi_condition} at {rsi_fmt}).<br>
            Fundamentals say, "{fundamental_verdict}" (driven by debt levels and growth metrics).</li>
            
            <li>✅ <strong>Can its core operations drive future growth?</strong><br>
            Future growth will likely depend on performance in its core {industry} operations and ability to manage competitive pressures.</li>
            
            <li>✅ <strong>What are the biggest risks?</strong><br>
            The company carries {total_debt_fmt} in debt, which could be a headwind in a high-interest-rate environment.<br>
            Competition is fierce from both established players and new entrants.</li>
        </ul>
        
        <p>Most stock analyses either use hard-to-understand jargon or say something too simple like "just buy" and trust the outcome. This is not what's happening. We're here with clear information that benefits you, no matter if you invest for long-term results or try for fast profits.</p>
        <p>All in all, is {company_name} the right investment to make sure your money tells a story of success and satisfaction? Or is there underlying issues to be wary of? Stick around as we get to the details in the data.</p>
        """

        return introduction_html

    except Exception as e:
        # Fallback to generate a standard error message
        return _generate_error_html("Introduction", str(e))


def generate_metrics_summary_html(ticker, rdata):
    """
    Generates the new, enhanced Key Metrics & Forecast Summary section with a
    tactical grid and a fully dynamic, data-driven narrative.
    """
    try:
        #data dictionary extraction
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        analyst_data = rdata.get('analyst_info_data', {})
        share_stats_data = rdata.get('share_statistics_data', {})
        price_stats_data = rdata.get('stock_price_stats_data', {})
        short_data = rdata.get('short_selling_data', {})
        historical_data = rdata.get('historical_data', pd.DataFrame())

        # Raw Values
        current_price_val = _safe_float(rdata.get('current_price'))
        forecast_1m_val = _safe_float(rdata.get('forecast_1m'))
        forecast_1y_val = _safe_float(rdata.get('forecast_1y'))
        analyst_target_val = _safe_float(analyst_data.get('Mean Target Price'))
        sma50_val = _safe_float(detailed_ta_data.get('SMA_50'))
        sma200_val = _safe_float(detailed_ta_data.get('SMA_200'))
        rsi_val = _safe_float(detailed_ta_data.get('RSI_14'))
        macd_hist_val = _safe_float(detailed_ta_data.get('MACD_Hist'))
        low_52wk_val = _safe_float(price_stats_data.get('52 Week Low'))
        high_52wk_val = _safe_float(price_stats_data.get('52 Week High'))
        volatility_val = _safe_float(rdata.get('volatility'))
        beta_val = _safe_float(price_stats_data.get('Beta'))
        inst_own_val = _safe_float(share_stats_data.get('Institutional Ownership'))
        short_float_val = _safe_float(short_data.get('Short % of Float'))
        
        # **FIX for Green Days Calculation**
        green_days_val = 0
        total_days_val = 0
        if not historical_data.empty and len(historical_data) >= 30:
            last_30_days = historical_data.iloc[-30:]
            green_days_val = int((last_30_days['Close'] > last_30_days['Open']).sum())
            total_days_val = len(last_30_days)
        green_days_pct = (green_days_val / total_days_val * 100) if total_days_val > 0 else 0
        
        # Calculated Percentages
        forecast_1m_pct = ((forecast_1m_val - current_price_val) / current_price_val) * 100 if forecast_1m_val and current_price_val else 0.0
        forecast_1y_pct = rdata.get('overall_pct_change', 0.0)
        analyst_target_pct = ((analyst_target_val - current_price_val) / current_price_val) * 100 if analyst_target_val and current_price_val else 0.0
        # Formatted Strings for Display
        current_price_fmt = format_html_value(current_price_val, 'currency', ticker=ticker)
        forecast_1m_fmt = f"{format_html_value(forecast_1m_val, 'currency', ticker=ticker)} ({'▲' if forecast_1m_pct > 0 else '▼'} {forecast_1m_pct:+.1f}%)"
        forecast_1y_fmt = f"{format_html_value(forecast_1y_val, 'currency', ticker=ticker)} ({'▲' if forecast_1y_pct > 0 else '▼'} {forecast_1y_pct:+.1f}%)"
        analyst_target_fmt = f"{format_html_value(analyst_target_val, 'currency', ticker=ticker)} ({'▲' if analyst_target_pct > 0 else '▼'} {analyst_target_pct:+.1f}%)"
        sma50_fmt = format_html_value(sma50_val, 'currency', ticker=ticker)
        sma200_fmt = format_html_value(sma200_val, 'currency', ticker=ticker)
        rsi_fmt = f"{rsi_val:.1f}" if rsi_val else "N/A"
        macd_hist_fmt = f"({macd_hist_val:.2f})" if macd_hist_val else ""
        range_52wk_fmt = f"{format_html_value(low_52wk_val, 'currency', ticker=ticker)} - {format_html_value(high_52wk_val, 'currency', ticker=ticker)}"
        volatility_fmt = format_html_value(volatility_val, 'percent_direct', 1)
        beta_fmt = f"{format_html_value(beta_val, 'ratio')} (High Sensitivity)" if beta_val and beta_val > 1.2 else f"{format_html_value(beta_val, 'ratio')}"
        green_days_fmt = f"{int(green_days_val)}/{int(total_days_val)} ({green_days_pct:.0f}%)"
        inst_own_fmt = format_html_value(inst_own_val, 'percent_direct')
        short_float_fmt = (f"{format_html_value(short_float_val, 'percent_direct')} (Low Bearish Bets)" if short_float_val and short_float_val < 2.0 else f"{format_html_value(short_float_val, 'percent_direct')}"
)

        
        # --- 2. Dynamic Text Generation ---
        
        # Technical Pattern Text
        technical_pattern_text = "mixed pattern"
        price_vs_sma50_icon = "▲"
        price_vs_sma200_icon = "▲"
        if current_price_val and sma50_val and sma200_val:
            if current_price_val > sma50_val and current_price_val > sma200_val:
                technical_pattern_text = "bullish pattern"
            elif current_price_val < sma50_val and current_price_val < sma200_val:
                technical_pattern_text = "bearish pattern"
                price_vs_sma50_icon = "▼"
                price_vs_sma200_icon = "▼"
            else:
                price_vs_sma50_icon = "▲" if current_price_val > sma50_val else "▼"
                price_vs_sma200_icon = "▲" if current_price_val > sma200_val else "▼"
        trend_summary_text = f"▲ Bullish (Price > SMA 50/200)" if technical_pattern_text == "bullish pattern" else f"▼ Bearish (Price < SMA 50/200)" if technical_pattern_text == "bearish pattern" else f"● Mixed Trend"

        # RSI and MACD Condition Text
        rsi_condition_text = "Neutral"
        if rsi_val:
            if rsi_val > 70: rsi_condition_text = "Overbought"
            elif rsi_val < 30: rsi_condition_text = "Oversold"
        
        macd_trend_text = "neutral trend"
        macd_icon = "●"
        if macd_hist_val:
            if macd_hist_val > 0.1: 
                macd_trend_text = "bullish short-term trend"
                macd_icon = "▲"
            elif macd_hist_val < -0.1:
                macd_trend_text = "bearish short-term trend"
                macd_icon = "▼"
        
        # 52-Week Range Position Text
        recovery_status_text = ""
        range_position_text = ""
        if current_price_val and low_52wk_val and high_52wk_val:
            range_pct = (current_price_val - low_52wk_val) / (high_52wk_val - low_52wk_val)
            if range_pct > 0.75:
                range_position_text = "the current price is near the higher end of that range"
                recovery_status_text = "the stock has recovered significantly from its lows"
            elif range_pct < 0.25:
                range_position_text = "the current price is near the lower end of that range"
                recovery_status_text = "the stock has pulled back significantly from its highs"
            else:
                range_position_text = "the current price is trading mid-range"
                recovery_status_text = "investor sentiment has been mixed"

        # Investor Bets Text
        investor_bets_text = "most big investors are betting on the company's long-term success rather than a decline"
        if short_float_val and short_float_val > 5.0:
            investor_bets_text = "a notable number of investors are betting on a price decline"

        # --- 3. Assemble Final HTML with Enhanced CSS and Dynamic Content ---
        
        # Enhanced CSS with reduced sizes for more compact display
        style_block = """
        <style>
            .metrics-grid-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 0.75rem;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                margin-bottom: 1.5rem;
                max-width: 1400px;
                margin: 0 auto;
                padding: 0.75rem;
            }
            
            .metric-card {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 0.5rem;
                padding: 0.75rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                transition: all 0.2s ease;
                position: relative;
            }
            
            .metric-card:hover {
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            }
            
            .metric-card .header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 0.5rem;
            }
            
            .metric-card .header h3 {
                font-size: 0.75rem;
                font-weight: 600;
                color: #4b5563;
                text-transform: uppercase;
                letter-spacing: 0.025em;
                margin: 0;
                display: flex;
                align-items: center;
                gap: 0.25rem;
            }
            
            .metric-card .main-value {
                font-size: 1.5rem;
                font-weight: 700;
                color: #111827;
                margin-bottom: 0.25rem;
                line-height: 1.2;
            }
            
            .metric-card .sub-value {
                font-size: 0.75rem;
                color: #6b7280;
                margin-bottom: 0.5rem;
            }
            
            .metric-card .metrics-list {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            
            .metric-card .metric-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.25rem 0;
                font-size: 0.875rem;
            }
            
            .metric-card .metric-row:not(:last-child) {
                border-bottom: 1px solid #f3f4f6;
            }
            
            .metric-card .metric-row.border-top {
                border-top: 1px solid #f3f4f6;
                padding-top: 0.5rem;
                margin-top: 0.125rem;
            }
            
            .metric-card .metric-label {
                font-size: 0.8125rem;
                color: #4b5563;
                font-weight: 500;
            }
            
            .metric-card .metric-value {
                font-weight: 600;
                color: #111827;
                text-align: right;
                display: flex;
                align-items: center;
                gap: 0.25rem;
                font-size: 0.875rem;
            }
            
            /* Color coding for positive/negative values */
            .positive-value {
                color: #059669 !important;
            }
            
            .negative-value {
                color: #dc2626 !important;
            }
            
            .neutral-value {
                color: #d97706 !important;
            }
            
            /* Trend badges */
            .trend-badge {
                padding: 0.125rem 0.375rem;
                border-radius: 9999px;
                font-size: 0.6875rem;
                font-weight: 600;
                border: 1px solid;
                display: inline-flex;
                align-items: center;
                gap: 0.125rem;
            }
            
            .trend-bullish {
                color: #059669;
                background-color: #ecfdf5;
                border-color: #a7f3d0;
            }
            
            .trend-bearish {
                color: #dc2626;
                background-color: #fef2f2;
                border-color: #fca5a5;
            }
            
            .trend-mixed {
                color: #d97706;
                background-color: #fffbeb;
                border-color: #fde68a;
            }
            
            /* RSI status badges */
            .rsi-badge {
                padding: 0.125rem 0.25rem;
                border-radius: 0.25rem;
                font-size: 0.6875rem;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 0.125rem;
            }
            
            .rsi-overbought {
                color: #dc2626;
                background-color: #fef2f2;
            }
            
            .rsi-oversold {
                color: #059669;
                background-color: #ecfdf5;
            }
            
            .rsi-neutral {
                color: #2563eb;
                background-color: #dbeafe;
            }
            
            /* Volatility indicators */
            .volatility-high {
                color: #dc2626;
                font-weight: 600;
            }
            
            .volatility-medium {
                color: #d97706;
                font-weight: 600;
            }
            
            .volatility-low {
                color: #059669;
                font-weight: 600;
            }
            
            /* Beta sensitivity indicators */
            .beta-high {
                color: #dc2626;
                font-weight: 600;
            }
            
            .beta-low {
                color: #2563eb;
                font-weight: 600;
            }
            
            .beta-moderate {
                color: #059669;
                font-weight: 600;
            }
            
            /* Ownership indicators */
            .ownership-high {
                color: #059669;
                font-weight: 600;
            }
            
            .ownership-medium {
                color: #d97706;
                font-weight: 600;
            }
            
            .ownership-low {
                color: #dc2626;
                font-weight: 600;
            }
            
            /* Responsive design */
            @media (max-width: 768px) {
                .metrics-grid-container {
                    grid-template-columns: 1fr;
                    gap: 0.5rem;
                    padding: 0.5rem;
                }
                
                .metric-card {
                    padding: 0.75rem;
                }
                
                .metric-card .main-value {
                    font-size: 1.25rem;
                }
            }
            
            /* Animation for the pulse dot */
            @keyframes pulse {
                0% { opacity: 0.6; }
                50% { opacity: 1; }
                100% { opacity: 0.6; }
            }
        </style>
        """

        # HTML structure with enhanced styling matching the React component
        html_content = f"""
        <div class="metrics-grid-container">
            <div class="metric-card">
                <div class="header">
                    <h3>💰 Current Price</h3>
                    <div style="width: 6px; height: 6px; background-color: #3b82f6; border-radius: 50%; animation: pulse 2s infinite;"></div>
                </div>
                <div class="main-value">{current_price_fmt}</div>
                <div class="sub-value">Live Market Price</div>
            </div>
            
            <div class="metric-card">
                <div class="header">
                    <h3>🎯 Price Targets & Forecasts</h3>
                </div>
                <div class="metrics-list">
                    <div class="metric-row">
                        <span class="metric-label">1-Month Forecast:</span>
                        <div class="metric-value">
                            <span>{format_html_value(forecast_1m_val, 'currency', ticker=ticker)}</span>
                            <span class="{'positive-value' if forecast_1m_pct > 0 else 'negative-value'}">
                                {'📈' if forecast_1m_pct > 0 else '📉'} {forecast_1m_pct:+.1f}%
                            </span>
                        </div>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">1-Year Forecast:</span>
                        <div class="metric-value">
                            <span>{format_html_value(forecast_1y_val, 'currency', ticker=ticker)}</span>
                            <span class="{'positive-value' if forecast_1y_pct > 0 else 'negative-value'}">
                                {'📈' if forecast_1y_pct > 0 else '📉'} {forecast_1y_pct:+.1f}%
                            </span>
                        </div>
                    </div>
                    <div class="metric-row border-top">
                        <span class="metric-label">Analyst Mean Target:</span>
                        <div class="metric-value">
                            <span>{format_html_value(analyst_target_val, 'currency', ticker=ticker)}</span>
                            <span class="{'positive-value' if analyst_target_pct > 0 else 'negative-value'}">
                                {'📈' if analyst_target_pct > 0 else '📉'} {analyst_target_pct:+.1f}%
                            </span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="header">
                    <h3>📈 Trend & Momentum</h3>
                </div>
                <div class="metrics-list">
                    <div class="metric-row">
                        <span class="metric-label">Trend:</span>
                        <span class="trend-badge {'trend-bullish' if technical_pattern_text == 'bullish pattern' else 'trend-bearish' if technical_pattern_text == 'bearish pattern' else 'trend-mixed'}">
                            {'🚀' if technical_pattern_text == 'bullish pattern' else '📉' if technical_pattern_text == 'bearish pattern' else '⚖️'} {trend_summary_text}
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">RSI (14-day):</span>
                        <span class="rsi-badge {'rsi-overbought' if rsi_condition_text == 'Overbought' else 'rsi-oversold' if rsi_condition_text == 'Oversold' else 'rsi-neutral'}">
                            {rsi_fmt} ({rsi_condition_text}) {'🔥' if rsi_condition_text == 'Overbought' else '❄️' if rsi_condition_text == 'Oversold' else '⚖️'}
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">MACD:</span>
                        <span class="metric-value {'positive-value' if macd_hist_val and macd_hist_val > 0.1 else 'negative-value' if macd_hist_val and macd_hist_val < -0.1 else 'neutral-value'}">
                            {'📈' if macd_hist_val and macd_hist_val > 0.1 else '📉' if macd_hist_val and macd_hist_val < -0.1 else '➡️'} {macd_trend_text.title()} {macd_hist_fmt}
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="header">
                    <h3>📊 Key Technical Levels</h3>
                </div>
                <div class="metrics-list">
                    <div class="metric-row">
                        <span class="metric-label">Above SMA 50:</span>
                        <span class="metric-value {'positive-value' if current_price_val and sma50_val and current_price_val > sma50_val else 'negative-value'}">
                            {'✅' if current_price_val and sma50_val and current_price_val > sma50_val else '❌'} {sma50_fmt}
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Above SMA 200:</span>
                        <span class="metric-value {'positive-value' if current_price_val and sma200_val and current_price_val > sma200_val else 'negative-value'}">
                            {'✅' if current_price_val and sma200_val and current_price_val > sma200_val else '❌'} {sma200_fmt}
                        </span>
                    </div>
                    <div class="metric-row border-top">
                        <span class="metric-label">52-Week Range:</span>
                        <span class="metric-value">
                            📏 {range_52wk_fmt}
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="header">
                    <h3>⚡ Volatility</h3>
                </div>
                <div class="metrics-list">
                    <div class="metric-row">
                        <span class="metric-label">Volatility (30d Ann.):</span>
                        <span class="metric-value {'volatility-high' if volatility_val and volatility_val > 30 else 'volatility-medium' if volatility_val and volatility_val > 20 else 'volatility-low'}">
                            {volatility_fmt} {'🌪️' if volatility_val and volatility_val > 30 else '🌊' if volatility_val and volatility_val > 20 else '🏞️'}
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Beta (vs. Market):</span>
                        <span class="metric-value {'beta-high' if beta_val and beta_val > 1.2 else 'beta-low' if beta_val and beta_val < 0.8 else 'beta-moderate'}">
                            {format_html_value(beta_val, 'ratio')}x {'🎢' if beta_val and beta_val > 1.2 else '🛡️' if beta_val and beta_val < 0.8 else '⚖️'}
                            {' (High Sensitivity)' if beta_val and beta_val > 1.2 else ' (Low Sensitivity)' if beta_val and beta_val < 0.8 else ' (Moderate)'}
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Green Days (30d):</span>
                        <span class="metric-value {'positive-value' if green_days_pct >= 60 else 'neutral-value' if green_days_pct >= 40 else 'negative-value'}">
                            {green_days_fmt} {'🟢' if green_days_pct >= 60 else '🟡' if green_days_pct >= 40 else '🔴'}
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="header">
                    <h3>🏢 Ownership</h3>
                </div>
                <div class="metrics-list">
                    <div class="metric-row">
                        <span class="metric-label">Institutional Ownership:</span>
                        <span class="metric-value {'ownership-high' if inst_own_val and inst_own_val > 60 else 'ownership-medium' if inst_own_val and inst_own_val > 40 else 'ownership-low'}">
                            {inst_own_fmt} {'🏛️' if inst_own_val and inst_own_val > 60 else '🏢' if inst_own_val and inst_own_val > 40 else '🏠'}
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Short % of Float:</span>
                        <span class="metric-value {'positive-value' if short_float_val and short_float_val < 2 else 'neutral-value' if short_float_val and short_float_val < 5 else 'negative-value'}">
                            {format_html_value(short_float_val, 'percent_direct')} {'😊' if short_float_val and short_float_val < 2 else '😐' if short_float_val and short_float_val < 5 else '😰'}
                            {' (Low Bearish Bets)' if short_float_val and short_float_val < 2 else ' (Moderate Bets)' if short_float_val and short_float_val < 5 else ' (High Bearish Bets)'}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <div class="metrics-narrative">
            <p>Right now, {ticker}'s stock is trading at <strong>{current_price_fmt}</strong>. The technical indicators are showing a <strong>{technical_pattern_text}</strong> because the price is holding relative to both the 50-day ({sma50_fmt}) and 200-day ({sma200_fmt}) moving averages. This suggests the stock has been gaining momentum recently. However, the Relative Strength Index (RSI) at <strong>{rsi_fmt}</strong> is {rsi_condition_text}—neither overbought nor oversold—while the MACD indicator shows a {macd_trend_text}, meaning there could be some minor pullbacks before the next upward move.</p>
            <p>Over the past year, {ticker}'s stock has traded between <strong>{format_html_value(low_52wk_val, 'currency', ticker=ticker)} and {format_html_value(high_52wk_val, 'currency', ticker=ticker)}</strong>, which tells us two things: First, {recovery_status_text}. Second, {range_position_text}, meaning big swings are less likely unless something major happens. Analysts expect modest growth ahead, with a <strong>1-year target of {format_html_value(forecast_1y_val, 'currency', ticker=ticker)} ({forecast_1y_pct:+.1f}%)</strong> and an average consensus target of <strong>{format_html_value(analyst_target_val, 'currency', ticker=ticker)} ({analyst_target_pct:+.1f}%)</strong>. Plus, with <strong>{inst_own_fmt} institutional ownership</strong> and very low short interest ({short_float_fmt}), it seems {investor_bets_text}.</p>
        </div>
        """
        
        return style_block + html_content

    except Exception as e:
        return f"<div style='color: red; padding: 1rem; border: 1px solid red; border-radius: 4px;'>Error generating metrics summary: {str(e)}</div>"
        
def generate_metrics_section_content(metrics, ticker=None):
    """Helper to generate table body content for metrics sections (Robust NA handling)."""
    rows = ""
    try:
        if isinstance(metrics, dict):
            row_parts = []
            for k, v in metrics.items():
                format_type = "string" 
                k_lower = str(k).lower()
                if "date" in k_lower: format_type = "date"
                elif "yield" in k_lower or "payout ratio" in k_lower: format_type = "percent_direct"
                elif "ratio" in k_lower or "beta" in k_lower: format_type = "ratio"
                elif "margin" in k_lower or "ownership" in k_lower or "growth" in k_lower or "%" in k_lower: format_type = "percent_direct"
                elif "price" in k_lower or "value" in k_lower or "dividend rate" in k_lower: format_type = "currency"
                elif "volume" in k_lower or "shares" in k_lower or "employees" in k_lower: format_type = "integer"
                elif "market cap" in k_lower: format_type = "large_number"

                formatted_v = format_html_value(v, format_type, ticker=ticker)
                if formatted_v != "N/A":
                    row_parts.append(f"<tr><td>{str(k)}</td><td>{formatted_v}</td></tr>") 

            rows = "".join(row_parts)

        if not rows:
            rows = "<tr><td colspan='2' style='text-align: center; font-style: italic;'>No displayable data is available for this category.</td></tr>"

        return f"""<div class="table-container">
                       <table class="metrics-table">
                           <tbody>{rows}</tbody>
                       </table>
                   </div>"""
    except Exception as e:
        logging.error(f"Error generating metrics table content: {e}")
        return f"""<div class="table-container">
                       <table class="metrics-table">
                           <tbody>
                               <tr><td colspan='2' style='text-align: center; color: red;'>Error displaying metric data.</td></tr>
                           </tbody>
                       </table>
                   </div>"""

def generate_total_valuation_html(ticker, rdata):
    """
    Generates the Total Valuation section with a custom, dynamic narrative summary
    split into two paragraphs, followed by the original data table.
    """
    try:
        # --- 1. Data Extraction and Parsing ---
        profile_data = rdata.get('profile_data', {})
        valuation_data = rdata.get('total_valuation_data', {})
        dividend_data = rdata.get('dividends_data', {})

        # Helper to parse formatted numbers like '$204.76B' back to a float
        def _parse_formatted_value(value_str):
            if value_str is None or not isinstance(value_str, (str, int, float)) or (isinstance(value_str, str) and value_str.lower() in ["n/a", ""]):
                return None
            
            value_str = str(value_str) # Convert non-string to string for processing
            
            # Clean the string
            value_str = value_str.strip().upper().replace('$', '').replace(',', '').replace('X', '')
            
            multiplier = 1
            if value_str.endswith('T'):
                multiplier = 1e12
                value_str = value_str[:-1]
            elif value_str.endswith('B'):
                multiplier = 1e9
                value_str = value_str[:-1]
            elif value_str.endswith('M'):
                multiplier = 1e6
                value_str = value_str[:-1]
            elif value_str.endswith('K'):
                multiplier = 1e3
                value_str = value_str[:-1]
            
            try:
                return float(value_str) * multiplier
            except (ValueError, TypeError):
                return None

        # Get formatted values for display
        market_cap_fmt = valuation_data.get('Market Cap', 'N/A')
        enterprise_value_fmt = valuation_data.get('Enterprise Value', 'N/A')
        ev_rev_fmt = valuation_data.get('EV/Revenue (TTM)', 'N/A')
        ev_ebitda_fmt = valuation_data.get('EV/EBITDA (TTM)', 'N/A')
        next_earn_date = valuation_data.get('Next Earnings Date', 'N/A')
        ex_div_date = valuation_data.get('Ex-Dividend Date', 'N/A')
        
        # Get raw values for calculations
        market_cap_raw = _parse_formatted_value(market_cap_fmt)
        enterprise_value_raw = _parse_formatted_value(enterprise_value_fmt)
        ev_rev_raw = _parse_formatted_value(ev_rev_fmt)
        ev_ebitda_raw = _parse_formatted_value(ev_ebitda_fmt)

        # Get other necessary data
        company_name = profile_data.get('Company Name', ticker)
        industry_descriptor = f"a key player in the {profile_data.get('Industry', 'its')} industry"
        
        # Check for dividend payment
        fwd_rate_raw = _parse_formatted_value(dividend_data.get('Forward Annual Dividend Rate'))
        yield_raw = _parse_formatted_value(str(dividend_data.get('Dividend Yield', '0')).replace('%',''))
        trailing_rate_raw = _parse_formatted_value(dividend_data.get('Trailing Annual Dividend Rate'))
        has_dividend = (fwd_rate_raw is not None and fwd_rate_raw > 0) or \
                       (yield_raw is not None and yield_raw > 0) or \
                       (trailing_rate_raw is not None and trailing_rate_raw > 0)

        # --- 2. Dynamic Narrative Generation ---
        
        # Part 1: Market Cap vs. Enterprise Value (First Paragraph)
        narrative_part1 = ""
        if market_cap_raw is not None and enterprise_value_raw is not None:
            net_debt = enterprise_value_raw - market_cap_raw
            if net_debt > 0.01 * market_cap_raw: # Check if debt is more than 1% of market cap
                net_debt_fmt = format_html_value(net_debt, 'large_number')
                narrative_part1 = (
                    f"Although the market considers {company_name} to be {industry_descriptor} with a <strong>{market_cap_fmt}</strong> market cap, "
                    f"its enterprise value is much higher at <strong>{enterprise_value_fmt}</strong>, with <strong>{net_debt_fmt}</strong> of that value added by debt. "
                    f"Investors are confident about {company_name}'s future earnings, but keep in mind the risk of that large amount of debt."
                )
            else: # Net cash position or negligible debt
                net_cash_fmt = format_html_value(abs(net_debt), 'large_number')
                narrative_part1 = (
                    f"While {company_name} has a market cap of <strong>{market_cap_fmt}</strong>, its enterprise value of <strong>{enterprise_value_fmt}</strong> is lower, "
                    f"reflecting a strong net cash position of approximately {net_cash_fmt}. This financial strength provides a cushion and flexibility for future investments."
                )
        else:
            narrative_part1 = f"The company's total valuation, including both its market capitalization and debt, provides a comprehensive view of its worth."

        # Part 2: Valuation Ratios and Outlook (Second Paragraph)
        narrative_parts2_and_3 = []
        if ev_rev_fmt != 'N/A' and ev_ebitda_fmt != 'N/A':
            premium_text = "trades at a valuation that reflects its market position"
            if ev_rev_raw is not None and ev_ebitda_raw is not None:
                if ev_rev_raw > 4 or ev_ebitda_raw > 15:
                    premium_text = "trades at a premium to many peers"
                elif ev_rev_raw < 1.5 and ev_ebitda_raw < 8 and ev_rev_raw > 0 and ev_ebitda_raw > 0:
                     premium_text = "appears attractively valued compared to many peers"
            
            narrative_parts2_and_3.append(
                f"The valuation ratios tell an interesting story: at <strong>{ev_rev_fmt}</strong> revenue and <strong>{ev_ebitda_fmt}</strong> EBITDA, {company_name} {premium_text}. "
                f"This reflects the company's strong market position and brand assets. But it also means the stock may have little room for error."
            )

        earnings_text = ""
        dividend_text = ""
        if next_earn_date != 'N/A':
            earnings_text = (
                f"The upcoming <strong>{next_earn_date}</strong> earnings report will be crucial in showing whether {company_name}'s businesses can grow into this valuation"
            )

        if has_dividend and ex_div_date != 'N/A':
            dividend_text = (
                f"the {ex_div_date} ex-dividend date serves as a reminder that {company_name} still rewards shareholders even as it invests for growth"
            )

        # Combine earnings and dividend text intelligently
        if earnings_text and dividend_text:
            narrative_parts2_and_3.append(f"{earnings_text}, while {dividend_text}.")
        elif earnings_text:
            narrative_parts2_and_3.append(f"{earnings_text}.")
        elif dividend_text:
            narrative_parts2_and_3.append(f"The {dividend_text[4:]}.")

        narrative_parts2_and_3.append("Essentially, you're paying for quality - but quality doesn't come cheap.")

        # --- 3. Assemble Final HTML ---
        
        # Create the two paragraphs
        paragraph1_html = f"<p>{narrative_part1}</p>"
        paragraph2_html = f"<p>{' '.join(narrative_parts2_and_3)}</p>" if narrative_parts2_and_3 else ""
        
        full_narrative_html = f'<div class="narrative">{paragraph1_html}{paragraph2_html}</div>'

        # Get the original table content
        table_content = generate_metrics_section_content(valuation_data, ticker)
        
        # Return the new narrative followed by the table
        return full_narrative_html + table_content

    except Exception as e:
        # Fallback to the standard error HTML generator on any failure
        logging.error(f"Error in generate_total_valuation_html for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Total Valuation", str(e))
        # --- 3. Assemble Final HTML ---
        
        # Get the original table content
        table_content = generate_metrics_section_content(valuation_data, ticker)
        
        # Return the new narrative followed by the table
        return f'<div class="narrative">{full_narrative}</div>' + table_content

    except Exception as e:
        # Fallback to the standard error HTML generator on any failure
        logging.error(f"Error in generate_total_valuation_html for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Total Valuation", str(e))

def generate_conclusion_outlook_html(ticker, rdata):
    """Generates the Conclusion and Outlook section with synthesized analysis."""
    try:
        profile_data = rdata.get('profile_data', {})
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        health_data = rdata.get('financial_health_data', {})
        valuation_data = rdata.get('valuation_data', {})
        analyst_data = rdata.get('analyst_info_data', {})
        dividend_data = rdata.get('dividends_data', {})
        profit_data = rdata.get('profitability_data', {})

        if not isinstance(profile_data, dict): profile_data = {}
        if not isinstance(detailed_ta_data, dict): detailed_ta_data = {}
        if not isinstance(health_data, dict): health_data = {}
        if not isinstance(valuation_data, dict): valuation_data = {}
        if not isinstance(analyst_data, dict): analyst_data = {}
        if not isinstance(dividend_data, dict): dividend_data = {}
        if not isinstance(profit_data, dict): profit_data = {}

        sentiment = rdata.get('sentiment', 'Neutral')
        current_price = _safe_float(rdata.get('current_price'))
        sma50 = _safe_float(rdata.get('sma_50')); sma200 = _safe_float(rdata.get('sma_200'))
        latest_rsi = _safe_float(detailed_ta_data.get('RSI_14'))
        macd_line = _safe_float(detailed_ta_data.get('MACD_Line')); macd_signal = _safe_float(detailed_ta_data.get('MACD_Signal'))
        support = _safe_float(detailed_ta_data.get('Support_30D')); resistance = _safe_float(detailed_ta_data.get('Resistance_30D'))
        forecast_1y = _safe_float(rdata.get('forecast_1y'))
        overall_pct_change = _safe_float(rdata.get('overall_pct_change'), default=0.0)
        roe = _safe_float(health_data.get('Return on Equity (ROE TTM)'))
        debt_equity = _safe_float(health_data.get('Debt/Equity (MRQ)'))
        op_cash_flow = _safe_float(health_data.get('Operating Cash Flow (TTM)')) 
        fwd_pe = _safe_float(valuation_data.get('Forward P/E'))
        peg_ratio = _safe_float(valuation_data.get('PEG Ratio'))
        pfcf_ratio = _safe_float(valuation_data.get('Price/FCF (TTM)'))
        analyst_rec = analyst_data.get('Recommendation', 'N/A') 
        mean_target = _safe_float(analyst_data.get('Mean Target Price'))
        fwd_yield = _safe_float(dividend_data.get('Dividend Yield (Fwd)'))
        payout_ratio = _safe_float(dividend_data.get('Payout Ratio'))
        rev_growth = _safe_float(profit_data.get('Revenue Growth (YoY)'))
        earn_growth = _safe_float(profit_data.get('Earnings Growth (YoY)'))
        rsi_divergence_bearish = rdata.get('rsi_divergence_bearish', False)
        rsi_divergence_bullish = rdata.get('rsi_divergence_bullish', False)
        roe_trend = rdata.get('roe_trend', None)
        debt_equity_trend = rdata.get('debt_equity_trend', None)
        # Added for default narrative logic:
        fundamental_strength_summary = "Moderate" # Default
        if roe is not None and debt_equity is not None and op_cash_flow is not None:
            op_cf_pos = op_cash_flow > 0
            if roe > 15 and debt_equity < 1.5 and op_cf_pos: fundamental_strength_summary = "Strong"
            elif roe < 5 or debt_equity > 2.5 or not op_cf_pos: fundamental_strength_summary = "Weak"

        st_points_data = {} 
        lt_points_data = {} 

        sentiment_str = str(sentiment)
        sentiment_icon = get_icon('up' if 'Bullish' in sentiment_str else ('down' if 'Bearish' in sentiment_str else 'neutral'))
        st_points_data['sentiment'] = {'label': 'Overall Technical Sentiment', 'value': sentiment_str, 'icon': sentiment_icon}

        trend_text = "mixed (between SMAs)"; trend_icon = get_icon('neutral')
        if current_price is not None and sma50 is not None and sma200 is not None:
            if current_price > sma50 and current_price > sma200: trend_text = "bullish (above SMA50/200)"; trend_icon = get_icon('up')
            elif current_price < sma50 and current_price < sma200: trend_text = "bearish (below SMA50/200)"; trend_icon = get_icon('down')
            elif current_price > sma50 and current_price < sma200: trend_text = "mixed (above SMA50, below SMA200)"
            else: trend_text = "mixed (below SMA50, above SMA200)"
        st_points_data['trend'] = {'label': 'Price Trend vs MAs', 'value': trend_text, 'icon': trend_icon}

        rsi_text = "Neutral"; rsi_icon = get_icon('neutral'); rsi_extra = ""
        if latest_rsi is not None:
            if latest_rsi < 30: rsi_text = f"Oversold ({latest_rsi:.1f})"; rsi_icon = get_icon('positive')
            elif latest_rsi > 70: rsi_text = f"Overbought ({latest_rsi:.1f})"; rsi_icon = get_icon('warning')
            else: rsi_text = f"Neutral ({latest_rsi:.1f})"
            if rsi_divergence_bearish: rsi_extra = f" {get_icon('divergence')}(Bearish Divergence?)"
            if rsi_divergence_bullish: rsi_extra = f" {get_icon('divergence')}(Bullish Divergence?)"
        else: rsi_text = "N/A"
        st_points_data['rsi'] = {'label': 'Momentum (RSI)', 'value': f"{rsi_text}{rsi_extra}", 'icon': rsi_icon}
        
        sr_text = "N/A"
        if support is not None and resistance is not None:
            sr_text = f"~{format_html_value(support,'currency', ticker=ticker)} / ~{format_html_value(resistance,'currency', ticker=ticker)}"
        st_points_data['sr'] = {'label': 'Support / Resistance (30d)', 'value': sr_text, 'icon': get_icon('chart')}


        forecast_icon = get_icon('neutral'); forecast_text = "N/A"
        if forecast_1y is not None:
            forecast_icon = get_icon('up' if overall_pct_change > 1 else ('down' if overall_pct_change < -1 else 'neutral'))
            forecast_text = f"~{overall_pct_change:+.1f}% avg. change to ≈{format_html_value(forecast_1y, 'currency', ticker=ticker)}"
        lt_points_data['forecast'] = {'label': '1-Year Avg. Forecast', 'value': forecast_text, 'icon': forecast_icon}

        val_text = "Moderate"; val_icon = get_icon('neutral')
        if fwd_pe is not None:
            if fwd_pe < 15 and fwd_pe > 0: val_text = f"Potentially Attractive (Fwd P/E: {format_html_value(fwd_pe,'ratio')})"; val_icon = get_icon('positive')
            elif fwd_pe > 30: val_text = f"Appears Elevated (Fwd P/E: {format_html_value(fwd_pe,'ratio')})"; val_icon = get_icon('warning')
            else: val_text = f"Appears Moderate (Fwd P/E: {format_html_value(fwd_pe,'ratio')})"
        else: val_text = "N/A (Fwd P/E)"
        peg_fmt = format_html_value(peg_ratio, 'ratio'); pfcf_fmt = format_html_value(pfcf_ratio, 'ratio')
        if peg_fmt != 'N/A': val_text += f", PEG: {peg_fmt}"
        if pfcf_fmt != 'N/A': val_text += f", P/FCF: {pfcf_fmt} {get_icon('cash')}"
        lt_points_data['valuation'] = {'label': 'Valuation Snapshot', 'value': val_text, 'icon': val_icon}

        health_text = "Moderate"; health_icon = get_icon('neutral')
        op_cf_pos = op_cash_flow is not None and op_cash_flow > 0
        roe_fmt = format_html_value(roe, 'percent_direct'); de_fmt = format_html_value(debt_equity, 'ratio'); ocf_fmt = format_html_value(op_cash_flow, 'large_number')
        if roe is not None and debt_equity is not None and op_cash_flow is not None:
            if roe > 15 and debt_equity < 1.5 and op_cf_pos: health_icon = get_icon('up'); health_text = f"Strong (ROE: {roe_fmt}, D/E: {de_fmt}, +OCF)"
            elif roe < 5 or debt_equity > 2.5 or not op_cf_pos: health_icon = get_icon('down'); health_text = f"Potential Weakness (ROE: {roe_fmt}, D/E: {de_fmt}, OCF: {ocf_fmt})"
            else: health_text = f"Moderate (ROE: {roe_fmt}, D/E: {de_fmt}, +OCF)"
        elif not op_cf_pos and op_cash_flow is not None: 
             health_icon = get_icon('down'); health_text = f"Concern: Negative Op Cash Flow ({ocf_fmt})"
        else: health_text = f"Assessment Incomplete (ROE: {roe_fmt}, D/E: {de_fmt})"
        if roe_trend: health_text += f", ROE Trend: {str(roe_trend).lower()}"
        if debt_equity_trend: health_text += f", D/E Trend: {str(debt_equity_trend).lower()}"
        lt_points_data['health'] = {'label': 'Fundamental Health', 'value': health_text, 'icon': health_icon}

        growth_text = "Mixed/Unclear"; growth_icon = get_icon('neutral')
        rg_fmt = format_html_value(rev_growth, 'percent_direct'); eg_fmt = format_html_value(earn_growth, 'percent_direct')
        if rev_growth is not None and earn_growth is not None:
             if rev_growth > 5 and earn_growth > 10: growth_text = f"Positive (Rev: {rg_fmt}, Earn: {eg_fmt})"; growth_icon = get_icon('growth')
             elif rev_growth < 0 or earn_growth < 0: growth_text = f"Negative (Rev: {rg_fmt}, Earn: {eg_fmt})"; growth_icon = get_icon('negative')
             else: growth_text = f"Moderate (Rev: {rg_fmt}, Earn: {eg_fmt})"
             # Removed growth_trend from here to simplify default narrative
        else: growth_text = f"N/A (Rev: {rg_fmt}, Earn: {eg_fmt})"
        lt_points_data['growth'] = {'label': 'Recent Growth (YoY)', 'value': growth_text, 'icon': growth_icon}

        analyst_text = "N/A"; analyst_icon = get_icon('neutral')
        if analyst_rec != 'N/A':
             analyst_icon = get_icon('up' if 'Buy' in analyst_rec else ('down' if 'Sell' in analyst_rec or 'Underperform' in analyst_rec else 'neutral'))
             mean_target_fmt = format_html_value(mean_target, 'currency', ticker=ticker)
             analyst_text = f"{analyst_rec} (Target: {mean_target_fmt})"
        lt_points_data['analyst'] = {'label': 'Analyst Consensus', 'value': analyst_text, 'icon': analyst_icon}

        if fwd_yield is not None and fwd_yield > 0.01:
            payout_fmt = format_html_value(payout_ratio, 'percent_direct')
            payout_context = f"(Payout: {payout_fmt})" if payout_fmt != 'N/A' else ""
            dividend_text = f"{format_html_value(fwd_yield, 'percent_direct')} Yield {payout_context}"; dividend_icon = get_icon('dividend')
            lt_points_data['dividend'] = {'label': 'Dividend', 'value': dividend_text, 'icon': dividend_icon}

        # Default keys for summary points
        st_keys_default = ['sentiment', 'trend', 'rsi', 'sr'] # Simplified MACD/BB from here for default
        lt_keys_default = ['forecast', 'health', 'valuation', 'growth', 'analyst']
        if 'dividend' in lt_points_data: lt_keys_default.append('dividend')

        st_keys = [k for k in st_keys_default if k in st_points_data and st_points_data[k]['value'] != 'N/A']
        lt_keys = [k for k in lt_keys_default if k in lt_points_data and lt_points_data[k]['value'] != 'N/A']

        def generate_list_items(keys, data_dict):
            html = ""
            for key in keys:
                item = data_dict.get(key)
                if item: 
                     value_str = str(item['value']) 
                     if len(value_str) > 150: value_str = value_str[:147] + "..."
                     html += f"<li><span class='icon'>{item['icon']}</span><span>{item['label']}: <strong>{value_str}</strong></span></li>"
            if not html:
                 html = "<li>No specific data points available for this perspective.</li>"
            return html

        short_term_html = generate_list_items(st_keys, st_points_data)
        long_term_html = generate_list_items(lt_keys, lt_points_data)

        outlook_summary = f"""
            <div class="conclusion-columns">
                <div class="conclusion-column">
                    <h3>Short-Term Technical Snapshot</h3>
                    <ul>{short_term_html}</ul>
                </div>
                <div class="conclusion-column">
                    <h3>Longer-Term Fundamental & Forecast Outlook</h3>
                    <ul>{long_term_html}</ul>
                </div>
            </div>
             """

        # --- Add Data-Driven Observations --- 
        observations_html = ""
        data_driven_observations = rdata.get('data_driven_observations', [])
        if data_driven_observations:
            observations_html += "<div class=\"data-driven-observations\">"
            observations_html += "<h4>Data-Driven Observations & Potential Tactics:</h4><ul>"
            for obs in data_driven_observations:
                observations_html += f"<li>{get_icon('info')} {obs}</li>"
            observations_html += "</ul></div>"
        
        outlook_summary += observations_html # Append observations to the outlook summary

        # Default Overall Assessment
        phrase_link_tech_fund_options = [
            "Bridging the technical picture with the fundamental outlook,",
            "Synthesizing the short-term signals with the longer-term view,",
            "Considering both technical momentum and fundamental drivers,"
        ]
        phrase_investor_consider_options = [
            "Investors should weigh these factors against",
            "Careful consideration of these points relative to",
            "Decision-making should factor in these elements against"
        ]
        phrase_risks_horizon_options = [
            "identified risks and their individual investment horizon.",
            "their personal risk tolerance and investment timeline.",
            "the potential risks outlined earlier and their strategic goals."
        ]
        forecast_direction_summary = "relatively flat"
        forecast_1y_fmt = format_html_value(forecast_1y, 'currency', ticker=ticker)
        if overall_pct_change > 5: forecast_direction_summary = f"potential upside ({overall_pct_change:+.1f}%)"
        elif overall_pct_change < -5: forecast_direction_summary = f"potential downside ({overall_pct_change:+.1f}%)"
        
        sentiment_narrative = st_points_data.get('sentiment',{}).get('value','N/A sentiment')
        valuation_narrative = lt_points_data.get('valuation',{}).get('value','N/A valuation')

        phrase_default_synthesis_options = [
            f"{random.choice(phrase_link_tech_fund_options)} {ticker} exhibits <strong>{sentiment_narrative}</strong> technical sentiment alongside <strong>{fundamental_strength_summary.lower()}</strong> fundamental health.",
            f"Overall, {ticker} combines a technical picture of learning {sentiment_narrative} with a fundamental health assessment of {fundamental_strength_summary.lower()}.",
            f"Synthesizing the data, {ticker} currently shows {sentiment_narrative} technicals coupled with {fundamental_strength_summary.lower()} fundamentals."
        ]
        phrase_default_valuation_options = [ f"Valuation appears {valuation_narrative}.", f"The current valuation is assessed as {valuation_narrative}.", f"From a valuation standpoint, it looks {valuation_narrative}." ]
        phrase_default_forecast_summary_options = [
            f"The 1-year forecast model suggests {forecast_direction_summary} towards ≈{forecast_1y_fmt}.",
            f"Models project a 1-year path indicating {forecast_direction_summary}, targeting ≈{forecast_1y_fmt}.",
            f"Looking out one year, the forecast implies a {forecast_direction_summary} with an average target near ≈{forecast_1y_fmt}."
        ]
        overall_assessment = (
            f"{random.choice(phrase_default_synthesis_options)} "
            f"{random.choice(phrase_default_valuation_options)} {random.choice(phrase_default_forecast_summary_options)} "
            f"{random.choice(phrase_investor_consider_options)} {random.choice(phrase_risks_horizon_options)}"
        )

        disclaimer_intro = random.choice([
            "<strong>Important:</strong> This analysis synthesizes model outputs and publicly available data for informational purposes only.",
            "<strong>Note:</strong> This report combines model projections and public data for educational use.",
            "<strong>Reminder:</strong> The following assessment is based on model data and public information, intended for informational use."
        ])
        disclaimer_text = (f"<p class='disclaimer'>{disclaimer_intro} It is not investment advice. Market conditions change rapidly. "
                           "Always conduct thorough independent research and consult a qualified financial advisor before making investment decisions.</p>")

        return outlook_summary + f"<div class='narrative'><h4>Overall Assessment & Outlook</h4><p>{overall_assessment}</p></div>" + disclaimer_text
    except Exception as e:
        return _generate_error_html("Conclusion & Outlook", str(e))

def generate_detailed_forecast_table_html(ticker, rdata):
    """Generates the detailed forecast table with commentary and insights."""
    try:
        monthly_forecast_table_data = rdata.get('monthly_forecast_table_data', pd.DataFrame())
        current_price = _safe_float(rdata.get('current_price'))
        current_price_fmt = format_html_value(current_price, 'currency', ticker=ticker)
        forecast_time_col = rdata.get('time_col', 'Period') 
        period_label = rdata.get('period_label', 'Period') 
        table_rows = ""
        min_price_overall = None; max_price_overall = None
        range_trend_comment = ""
        
        if isinstance(monthly_forecast_table_data, pd.DataFrame) and \
           not monthly_forecast_table_data.empty and \
           'Low' in monthly_forecast_table_data.columns and \
           'High' in monthly_forecast_table_data.columns:

            forecast_df = monthly_forecast_table_data.copy()
            if forecast_time_col in forecast_df.columns:
                forecast_df[forecast_time_col] = forecast_df[forecast_time_col].astype(str)

            forecast_df['Low'] = pd.to_numeric(forecast_df['Low'], errors='coerce')
            forecast_df['High'] = pd.to_numeric(forecast_df['High'], errors='coerce')
            forecast_df.dropna(subset=['Low', 'High'], inplace=True)

            if not forecast_df.empty:
                min_price_overall = forecast_df['Low'].min()
                max_price_overall = forecast_df['High'].max()
                # ... (rest of calculations: RangeWidth, Action, ROI as before) ...
                forecast_df['RangeWidth'] = forecast_df['High'] - forecast_df['Low']
                first_range_width = forecast_df['RangeWidth'].iloc[0]
                last_range_width = forecast_df['RangeWidth'].iloc[-1]

                first_row = forecast_df.iloc[0]
                last_row = forecast_df.iloc[-1]
                first_range_str = f"{format_html_value(first_row['Low'], 'currency', ticker=ticker)} – {format_html_value(first_row['High'], 'currency', ticker=ticker)}"
                last_range_str = f"{format_html_value(last_row['Low'], 'currency', ticker=ticker)} – {format_html_value(last_row['High'], 'currency', ticker=ticker)}"
                
                width_change_ratio = last_range_width / first_range_width if first_range_width and first_range_width != 0 else 1
                range_trend_options = {
                    'widening': [
                        f"Note the significant widening in the projected price range (from {first_range_str} to {last_range_str}), suggesting increasing forecast uncertainty over time.",
                        f"Observe how the forecast range expands considerably (from {first_range_str} to {last_range_str}), indicating greater potential price variability further out." ],
                    'narrowing': [
                        f"Observe the narrowing projected price range (from {first_range_str} to {last_range_str}), indicating potentially stabilizing expectations or higher model confidence further out.",
                        f"The forecast uncertainty appears to decrease over time, as seen by the tightening price range ({first_range_str} vs. {last_range_str})."],
                    'stable': [
                        f"The projected price range remains relatively consistent (from {first_range_str} to {last_range_str}), implying stable forecast uncertainty.",
                        f"Forecast uncertainty appears steady, with the price range ({first_range_str} to {last_range_str}) showing little change over the horizon."]
                }
                if width_change_ratio > 1.2: range_trend_comment = random.choice(range_trend_options['widening'])
                elif width_change_ratio < 0.8: range_trend_comment = random.choice(range_trend_options['narrowing'])
                else: range_trend_comment = random.choice(range_trend_options['stable'])

                if 'Average' not in forecast_df.columns:
                     forecast_df['Average'] = (forecast_df['Low'] + forecast_df['High']) / 2
                else:
                    forecast_df['Average'] = pd.to_numeric(forecast_df['Average'], errors='coerce')
                forecast_df.dropna(subset=['Average'], inplace=True)

                if current_price is not None and current_price > 0:
                    forecast_df['Potential ROI'] = ((forecast_df['Average'] - current_price) / current_price) * 100
                else:
                    forecast_df['Potential ROI'] = np.nan

                roi_threshold_buy = 2.5; roi_threshold_short = -2.5
                forecast_df['Action'] = np.select(
                    [forecast_df['Potential ROI'] > roi_threshold_buy, forecast_df['Potential ROI'] < roi_threshold_short],
                    ['Consider Buy', 'Consider Short'], default='Hold/Neutral'
                )
                forecast_df.loc[forecast_df['Potential ROI'].isna(), 'Action'] = 'N/A'

                required_cols = [forecast_time_col, 'Low', 'Average', 'High', 'Potential ROI', 'Action']
                if all(col in forecast_df.columns for col in required_cols):
                    for _, row in forecast_df.iterrows():
                        action_class = str(row.get('Action', 'N/A')).lower().split(" ")[-1].split("/")[0]
                        roi_val = row.get('Potential ROI', np.nan)
                        roi_icon = get_icon('neutral')
                        roi_fmt = "N/A"
                        if not pd.isna(roi_val):
                           roi_icon = get_icon('up' if roi_val > 1 else ('down' if roi_val < -1 else 'neutral'))
                           roi_fmt = format_html_value(roi_val, 'percent_direct', 1)

                        low_fmt = format_html_value(row.get('Low'), 'currency', ticker=ticker)
                        avg_fmt = format_html_value(row.get('Average'), 'currency', ticker=ticker)
                        high_fmt = format_html_value(row.get('High'), 'currency', ticker=ticker)
                        action_display = row.get('Action', 'N/A')
                        time_period_fmt = str(row.get(forecast_time_col, 'N/A')) 

                        table_rows += (
                            f"<tr><td>{time_period_fmt}</td><td>{low_fmt}</td><td>{avg_fmt}</td><td>{high_fmt}</td>"
                            f"<td>{roi_icon} {roi_fmt}</td><td class='action-{action_class}'>{action_display}</td></tr>\n"
                        )
                else:
                     missing_cols = [col for col in required_cols if col not in forecast_df.columns]
                     logging.warning(f"Missing required columns in forecast data: {missing_cols}")
                     table_rows = f"<tr><td colspan='6' style='text-align:center;'>Detailed forecast data incomplete.</td></tr>"
            
            min_max_summary = f"""<p>Over the forecast horizon ({forecast_df[forecast_time_col].iloc[0]} to {forecast_df[forecast_time_col].iloc[-1]}), {ticker}'s price is projected by the model to fluctuate between approximately <strong>{format_html_value(min_price_overall, 'currency', ticker=ticker)}</strong> and <strong>{format_html_value(max_price_overall, 'currency', ticker=ticker)}</strong>.</p>""" if min_price_overall is not None else "<p>Overall forecast range could not be determined.</p>"
            table_html = f"""<div class="table-container"><table><thead><tr><th>{period_label} ({forecast_time_col})</th><th>Min. Price</th><th>Avg. Price</th><th>Max. Price</th><th>Potential ROI vs Current ({current_price_fmt})</th><th>Model Signal</th></tr></thead><tbody>{table_rows}</tbody></table></div>"""
        else:
            min_max_summary = f"<p>No detailed {period_label.lower()}-by-{period_label.lower()} forecast data is currently available for {ticker}.</p>"
            table_html = ""
            range_trend_comment = ""

        # Default Narrative
        min_fmt = format_html_value(min_price_overall, 'currency', ticker=ticker)
        max_fmt = format_html_value(max_price_overall, 'currency', ticker=ticker)
        range_narrative = f"{min_fmt} to {max_fmt}" if min_price_overall is not None else "an undetermined range"
        narrative_options = [
            (f"The detailed {period_label.lower()}y forecast below outlines the model's expectations for {ticker}'s price evolution ({range_narrative}). It includes projected ranges (Min, Avg, Max), potential ROI based on the average projection versus the current price, and a derived model signal for each period."),
            (f"Here's the breakdown of the {period_label.lower()} forecast for {ticker} ({range_narrative} overall range). The table shows projected price bands, potential ROI against the current price, and the resulting model signal per period.")
        ]
        narrative_intro = random.choice(narrative_options)

        disclaimer_forecast = random.choice([
            "Forecasts are model-based estimates, inherently uncertain, and subject to change based on evolving data and market conditions. They do not guarantee future prices.",
            "Remember that these forecasts are generated by models, carry inherent uncertainty, and can change with new data or market shifts. Future prices are not guaranteed.",
            "Model forecasts like these are estimates with built-in uncertainty. They depend on current data and assumptions, which can change. Actual prices are not guaranteed."
        ])

        return f"""
            <div class="narrative">
                <p>{narrative_intro}</p>
                {min_max_summary}
                <p>{range_trend_comment}</p>
            </div>
            {table_html}
            <p class="disclaimer">{disclaimer_forecast}</p>
            """
    except Exception as e:
        return _generate_error_html("Detailed Forecast Table", str(e))

def generate_company_profile_html(ticker, rdata):
    """Generates the Company Profile section with default detail."""
    try:
        profile_data = rdata.get('profile_data', {})
        if not isinstance(profile_data, dict):
            profile_data = {}
            logging.warning("profile_data not found or not a dict, using empty.")

        website_link = profile_data.get('Website', '#')
        if website_link and isinstance(website_link, str) and not website_link.startswith(('http://', 'https://')) and website_link != '#':
             website_link = f"https://{website_link}" 
        elif not website_link or website_link == '#':
             website_link = '#' 

        profile_items = []
        if profile_data.get('Sector'): profile_items.append(f"<div class='profile-item'><span>Sector: </span> {format_html_value(profile_data['Sector'], 'string')}</div>")
        if profile_data.get('Industry'): profile_items.append(f"<div class='profile-item'><span>Industry: </span>{format_html_value(profile_data['Industry'], 'string')}</div>")
        if profile_data.get('Market Cap'): profile_items.append(f"<div class='profile-item'><span>Market Cap: </span>{format_html_value(profile_data['Market Cap'], 'large_number')}</div>")
        if profile_data.get('Employees'): profile_items.append(f"<div class='profile-item'><span>Employees: </span>{format_html_value(profile_data.get('Employees'), 'integer')}</div>")

        if website_link != '#':
             profile_items.append(f"<div class='profile-item'><span>Website:</span><a href='{website_link}' target='_blank' rel='noopener noreferrer'>{format_html_value(profile_data.get('Website','N/A'), 'string')}</a></div>")
        elif 'Website' in profile_data: 
             profile_items.append(f"<div class='profile-item'><span>Website:</span>{format_html_value(profile_data.get('Website'), 'string')} (Link invalid/missing)</div>")

        location_parts = [profile_data.get('City'), profile_data.get('State'), profile_data.get('Country')]
        location_str = ', '.join(filter(None, [str(p) if p is not None else None for p in location_parts])) 
        if location_str: profile_items.append(f"<div class='profile-item'><span>Headquarters:</span>{location_str}</div>")

        profile_grid = f'<div class="profile-grid">{"".join(profile_items)}</div>' if profile_items else "<p>Basic company identification data is limited.</p>"

        # Default summary title and narrative
        summary_title_options = ["Business Overview", "Company Description"]
        summary_title = random.choice(summary_title_options)
        narrative_focus_options = [
                " A brief overview of the company's business activities.",
                " Understanding the core business provides context for the following analysis."
        ]
        narrative_focus = random.choice(narrative_focus_options)

        summary_text = str(profile_data.get('Summary', 'No detailed business summary available.')) 
        summary_html = f"<h4>{summary_title}</h4><p>{narrative_focus} {summary_text}</p>"

        return profile_grid + summary_html
    except Exception as e:
        return _generate_error_html("Company Profile", str(e))

def generate_valuation_metrics_html(ticker, rdata):
    """
    Generates a human-centric summary by assembling random, pre-generated sentence
    components and formatting them with live data.
    """
    try:
        # --- 1. Data Extraction ---
        valuation_data = rdata.get('valuation_data', {})
        total_valuation_data = rdata.get('total_valuation_data', {})
        if not isinstance(valuation_data, dict): valuation_data = {}
        if not isinstance(total_valuation_data, dict): total_valuation_data = {}
        
        def _parse_value(value_str):
            if value_str is None or not isinstance(value_str, str) or value_str.lower() == 'n/a': return None
            try: return float(value_str.replace('x', '').strip())
            except (ValueError, TypeError): return None
            
        trailing_pe_fmt = valuation_data.get('Trailing P/E', 'N/A')
        forward_pe_fmt = valuation_data.get('Forward P/E', 'N/A')
        ps_ratio_fmt = valuation_data.get('Price/Sales (TTM)', 'N/A')
        pb_ratio_fmt = valuation_data.get('Price/Book (MRQ)', 'N/A')
        ev_rev_fmt = total_valuation_data.get('EV/Revenue (TTM)', 'N/A')
        ev_ebitda_fmt = total_valuation_data.get('EV/EBITDA (TTM)', 'N/A')
        
        trailing_pe_raw = _parse_value(trailing_pe_fmt)
        forward_pe_raw = _parse_value(forward_pe_fmt)
        ps_ratio_raw = _parse_value(ps_ratio_fmt)
        pb_ratio_raw = _parse_value(pb_ratio_fmt)
        ev_rev_raw = _parse_value(ev_rev_fmt)
        ev_ebitda_raw = _parse_value(ev_ebitda_fmt)

        # --- 2. Assemble Dynamic Narrative from Library Components ---
        p1_parts = []
        p2_parts = []

        # --- Paragraph 1: P/E, P/S, and P/B Ratios ---
        if trailing_pe_raw is not None or forward_pe_raw is not None:
            pe_level_raw = forward_pe_raw if forward_pe_raw is not None else trailing_pe_raw
            
            if pe_level_raw <= 0: interp_key = "pe_interp_negative"
            elif pe_level_raw < 15: interp_key = "pe_interp_attractive"
            elif pe_level_raw < 25: interp_key = "pe_interp_moderate"
            else: interp_key = "pe_interp_high"
            
            intro_component = f"{ticker} demonstrates"
            if interp_key == "pe_interp_negative":
                interp_component = "presents unusual P/E dynamics that require careful interpretation"
            elif interp_key == "pe_interp_attractive":
                interp_component = "suggests an attractive valuation opportunity"
            elif interp_key == "pe_interp_moderate":
                interp_component = "indicates a reasonably valued position"
            else:  # pe_interp_high
                interp_component = "reflects a premium valuation that warrants careful consideration"
            p1_parts.append(f"{intro_component}, with its Trailing P/E at <strong>{trailing_pe_fmt}</strong> and Forward P/E at <strong>{forward_pe_fmt}</strong>, {interp_component}.")

            if trailing_pe_raw is not None and forward_pe_raw is not None and forward_pe_raw > 0:
                trend_component = ""
                if forward_pe_raw < trailing_pe_raw * 0.9: 
                    trend_component = "this suggests potential earnings growth expectations"
                elif forward_pe_raw < trailing_pe_raw: 
                    trend_component = "this indicates modest improvement expectations"
                else: 
                    trend_component = "this reflects stable earnings outlook"
                # Capitalize the first letter of the trend component
                trend_component = trend_component[0].upper() + trend_component[1:]
                p1_parts.append(trend_component)

        if ps_ratio_raw is not None and pb_ratio_raw is not None:
            analysis_component = "the company trades at multiples that warrant attention"
            implication_component = "These metrics provide insight into market positioning."
            p1_parts.append(f"Meanwhile, its Price/Sales ratio of <strong>{ps_ratio_fmt}</strong> and Price/Book of <strong>{pb_ratio_fmt}</strong> show that {analysis_component}. {implication_component}")
        
        # --- Paragraph 2: Enterprise Value Ratios and Synthesis ---
        ev_sentences = []
        if ev_rev_raw is not None:
            # Determine which observation to use based on data
            if ev_rev_raw <= 1.5: ev_rev_obs_key = "ev_observation_rev_fair"
            else: ev_rev_obs_key = "ev_observation_rev_fair"
            
            # Assemble the sentence from static components
            subject = "The enterprise value to revenue ratio"
            verb = "indicates"
            if ev_rev_obs_key == "ev_observation_rev_fair":
                observation = "reasonable revenue-based valuation"
            else:
                observation = "reasonable revenue-based valuation"
            ev_sentences.append(f"{subject} of <strong>{ev_rev_fmt}</strong> {verb} {observation}")

        if ev_ebitda_raw is not None:
            if ev_ebitda_raw > 12: ev_ebitda_obs_key = "ev_observation_ebitda_stretched"
            else: ev_ebitda_obs_key = "ev_observation_ebitda_reasonable"
            
            subject = "the EV/EBITDA multiple"
            verb = "suggests"
            if ev_ebitda_obs_key == "ev_observation_ebitda_stretched":
                observation = "a potentially stretched valuation"
            else:
                observation = "reasonable earnings-based valuation"
            # Use lowercase subject if it's not the start of the sentence
            ev_sentences.append(f"and its {subject} of <strong>{ev_ebitda_fmt}</strong> {verb} {observation}")
        
        if ev_sentences:
             full_ev_narrative = ", ".join(ev_sentences)
             intro = "From an enterprise value perspective,"
             p2_parts.append(f"{intro} {full_ev_narrative}.")

        p2_parts.append("These valuation metrics provide a comprehensive view of the company's current market positioning.")

        # --- 3. Assemble Final HTML ---
        paragraph1_html = '<p>' + ' '.join(p1_parts) + '</p>' if p1_parts else ''
        paragraph2_html = '<p>' + ' '.join(p2_parts) + '</p>' if p2_parts else ''
        full_narrative_html = f'<div class="narrative">{paragraph1_html}{paragraph2_html}</div>'

        combined_data_for_table = {**valuation_data, **total_valuation_data}
        keys_to_exclude = ['Market Cap', 'Enterprise Value', 'Next Earnings Date', 'Ex-Dividend Date']
        filtered_table_data = {k: v for k, v in combined_data_for_table.items() if k not in keys_to_exclude}
        table_html = generate_metrics_section_content(filtered_table_data, ticker)
        
        return full_narrative_html + table_html

    except Exception as e:
        logging.error(f"Error in generate_valuation_metrics_html for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Valuation Metrics", str(e))


def generate_financial_health_html(ticker, rdata):
    """
    Generates a dynamic, two-paragraph narrative analyzing financial health,
    followed by the detailed data table.
    """
    try:
        # --- 1. Data Extraction and Parsing ---
        health_data = rdata.get('financial_health_data', {})
        if not isinstance(health_data, dict) or not health_data:
            return _generate_error_html("Financial Health", "No financial health data available.")

        # Helper to parse formatted values like '8.89%' or '$42.89B' into numbers
        def _parse_value(value_str):
            if value_str is None or not isinstance(value_str, str) or value_str.lower() == 'n/a':
                return None
            
            cleaned_str = value_str.strip().upper().replace('$', '').replace(',', '')
            multiplier = 1
            
            if cleaned_str.endswith('%'):
                multiplier = 0.01
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('T'):
                multiplier = 1e12
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('B'):
                multiplier = 1e9
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('M'):
                multiplier = 1e6
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('K'):
                multiplier = 1e3
                cleaned_str = cleaned_str[:-1]

            try:
                return float(cleaned_str.replace('X',''))
            except (ValueError, TypeError):
                return None

        # Parse all necessary raw values for logic
        roe_raw = _parse_value(health_data.get('Return on Equity (ROE TTM)'))
        roa_raw = _parse_value(health_data.get('Return on Assets (ROA TTM)'))
        de_raw = _parse_value(health_data.get('Debt/Equity (MRQ)'))
        current_ratio_raw = _parse_value(health_data.get('Current Ratio (MRQ)'))
        quick_ratio_raw = _parse_value(health_data.get('Quick Ratio (MRQ)'))
        op_cash_flow_raw = _parse_value(health_data.get('Operating Cash Flow (TTM)'))
        lfcf_raw = _parse_value(health_data.get('Levered Free Cash Flow (TTM)'))

        # Get formatted values for display
        roe_fmt = health_data.get('Return on Equity (ROE TTM)', 'N/A')
        roa_fmt = health_data.get('Return on Assets (ROA TTM)', 'N/A')
        de_fmt = health_data.get('Debt/Equity (MRQ)', 'N/A')
        debt_fmt = health_data.get('Total Debt (MRQ)', 'N/A')
        cash_fmt = health_data.get('Total Cash (MRQ)', 'N/A')
        op_cash_flow_fmt = health_data.get('Operating Cash Flow (TTM)', 'N/A')
        current_ratio_fmt = health_data.get('Current Ratio (MRQ)', 'N/A')
        quick_ratio_fmt = health_data.get('Quick Ratio (MRQ)', 'N/A')
        lfcf_fmt = health_data.get('Levered Free Cash Flow (TTM)', 'N/A')

        # --- 2. Determine Overall Theme (Strength, Weakness, or Mixed) ---
        score = 0
        if roe_raw is not None: score += 1 if roe_raw > 0.15 else -1 if roe_raw < 0.05 else 0
        if de_raw is not None: score += 1 if de_raw < 1.0 else -1 if de_raw > 2.0 else 0
        if current_ratio_raw is not None: score += 1 if current_ratio_raw > 1.5 else -1 if current_ratio_raw < 1.0 else 0
        if op_cash_flow_raw is not None and op_cash_flow_raw > 0: score += 1
        if op_cash_flow_raw is not None and op_cash_flow_raw <= 0: score -= 2
        
        # --- 3. Build Narrative Paragraphs ---
        p1_parts = []
        p2_parts = []

        # Paragraph 1: Intro, ROE/ROA, and Debt vs. Operating Cash
        if score > 2:
            p1_parts.append(f"{ticker}'s financial health appears robust, showcasing several key strengths.")
        elif score < -1:
            p1_parts.append(f"{ticker}'s financial data reveals several areas of concern that warrant caution.")
        else:
            p1_parts.append(f"{ticker}s financial data clearly shows that strengths and weaknesses can appear together.")
        
        if roe_raw is not None and roa_raw is not None:
            efficiency_text = "reflect a highly efficient use of capital, often seen in fast-growing firms" if roe_raw > 0.15 else "reflects that the company is not very efficient with its capital, and such numbers are usually found in established, stable firms"
            p1_parts.append(f"The ROE and ROA of <strong>{roe_fmt}</strong> and <strong>{roa_fmt}</strong>, respectively, {efficiency_text}.")

        if de_raw is not None:
            debt_level_text = "a very high level of debt" if de_raw > 2.5 else "a considerable amount of debt" if de_raw > 1.5 else "a manageable debt load"
            p1_parts.append(f"The <strong>{de_fmt}</strong> Debt/Equity ratio (with {debt_fmt} in debt and {cash_fmt} in cash) points to the fact that {ticker} has taken on {debt_level_text} to fuel its operations and growth.")

        if op_cash_flow_raw is not None:
            if op_cash_flow_raw > 0:
                p1_parts.append(f"Even with its debt, the company's ability to bring in <strong>{op_cash_flow_fmt}</strong> in operating cash flow (TTM) proves that its core business can steadily produce cash, which is a significant strength.")
            else:
                p1_parts.append(f"A major concern is the negative operating cash flow of <strong>{op_cash_flow_fmt}</strong> (TTM), indicating the core business is currently using more cash than it generates.")

        # Paragraph 2: Liquidity, Free Cash Flow, and Synthesis
        if current_ratio_raw is not None and quick_ratio_raw is not None:
            liquidity_text = "potential liquidity issues that might cause trouble if the company's cash cycle lengthens" if current_ratio_raw < 1.0 else "a solid liquidity position, able to cover its short-term liabilities"
            p2_parts.append(f"The Current Ratio of <strong>{current_ratio_fmt}</strong> and Quick Ratio of <strong>{quick_ratio_fmt}</strong> show {liquidity_text}.")

        if lfcf_raw is not None and lfcf_raw > 0:
            p2_parts.append(f"Furthermore, {ticker}'s <strong>{lfcf_fmt}</strong> in levered free cash flow suggests it can still generate significant cash for shareholders even after meeting its financial obligations.")

        # Synthesis based on the combined data
        synthesis = ""
        if de_raw is not None and de_raw > 1.5 and current_ratio_raw is not None and current_ratio_raw < 1.2 and op_cash_flow_raw is not None and op_cash_flow_raw > 0:
            synthesis = "For investors, this means that while cash flows appear to cover its debts for now, there is not much space for mistakes. If business results fall or interest rates are high when it tries to refinance, the company could be put under increased financial stress."
        elif de_raw is not None and de_raw < 1.0 and current_ratio_raw is not None and current_ratio_raw > 1.5 and op_cash_flow_raw is not None and op_cash_flow_raw > 0:
            synthesis = "For investors, this financial profile suggests a resilient and well-managed company. The low debt and strong liquidity provide a solid safety net and the flexibility to invest in growth, weather economic downturns, or increase returns to shareholders."
        elif de_raw is not None and de_raw > 2.0 and (op_cash_flow_raw is None or op_cash_flow_raw <= 0):
             synthesis = "This combination of high debt and negative operating cash flow is a significant red flag. It indicates the company is burning through cash while servicing a large debt load, a high-risk situation that could lead to financial distress if not reversed quickly."
        
        if synthesis:
            p2_parts.append(synthesis)

        # --- 4. Assemble Final HTML ---
        paragraph1_html = '<p>' + ' '.join(p1_parts) + '</p>' if p1_parts else ''
        paragraph2_html = '<p>' + ' '.join(p2_parts) + '</p>' if p2_parts else ''
        full_narrative_html = f'<div class="narrative">{paragraph1_html}{paragraph2_html}</div>'

        # Get the table content
        table_html = generate_metrics_section_content(health_data, ticker)

        return full_narrative_html + table_html

    except Exception as e:
        logging.error(f"Error in generate_financial_health_html for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Financial Health", str(e))



def generate_financial_efficiency_html(ticker, rdata):
    """Generates Financial Efficiency section with a default narrative focus."""
    try:
        efficiency_data = rdata.get('financial_efficiency_data')
        if not isinstance(efficiency_data, dict):
             efficiency_data = {}
             logging.warning("financial_efficiency_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(efficiency_data, ticker)

        asset_turnover_fmt = format_html_value(efficiency_data.get('Asset Turnover (TTM)'), 'ratio')
        inventory_turnover_fmt = format_html_value(efficiency_data.get('Inventory Turnover (TTM)'), 'ratio')
        receivables_turnover_fmt = format_html_value(efficiency_data.get('Receivables Turnover (TTM)'), 'ratio')

        efficiency_summary_options = [
            f"Efficiency is gauged by how effectively {ticker} utilizes assets (Asset Turnover: {asset_turnover_fmt})",
            f"Operational effectiveness can be seen in asset utilization (Asset Turnover: {asset_turnover_fmt})",
            f"{ticker}'s efficiency in using its assets to generate sales is measured by Asset Turnover ({asset_turnover_fmt})"
        ]
        efficiency_summary = random.choice(efficiency_summary_options)

        if inventory_turnover_fmt != 'N/A': efficiency_summary += f", manages inventory (Inventory Turnover: {inventory_turnover_fmt})"
        if receivables_turnover_fmt != 'N/A': efficiency_summary += f", and collects payments (Receivables Turnover: {receivables_turnover_fmt})."
        else: efficiency_summary += "." 
        
        comparison_prompt_options = [
            f"Comparing these turnover ratios against industry benchmarks {get_icon('peer')} and historical trends {get_icon('history')} reveals operational effectiveness.",
            f"Benchmarking these efficiency metrics with industry peers {get_icon('peer')} and the company's history {get_icon('history')} provides valuable context.",
            f"Relative performance in these turnover figures, compared to peers {get_icon('peer')} and past results {get_icon('history')}, indicates efficiency levels."
        ]
        comparison_prompt = random.choice(comparison_prompt_options)

        # Default Narrative
        narrative_options = [
            (
                 f"Financial efficiency ratios measure how effectively {ticker} converts its assets into revenue and manages working capital. {efficiency_summary} {comparison_prompt}"
            ),
            (
            f"This section examines {ticker}'s operational efficiency in asset usage and working capital management. {efficiency_summary} {comparison_prompt}"
            )
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Financial Efficiency", str(e))

def generate_profitability_growth_html(ticker, rdata):
    """
    Generates a dynamic, two-paragraph narrative for the Profitability & Growth
    section, followed by the detailed data table.
    """
    try:
        # --- 1. Data Extraction and Parsing ---
        profit_data = rdata.get('profitability_data', {})
        if not isinstance(profit_data, dict) or not profit_data:
            return _generate_error_html("Profitability & Growth", "No profitability data available.")

        # Helper to parse formatted values like '37.10%' or '$18.08B' into numbers
        def _parse_value(value_str):
            if value_str is None or not isinstance(value_str, str) or value_str.lower() == 'n/a':
                return None
            
            cleaned_str = value_str.strip().upper().replace('$', '').replace(',', '')
            multiplier = 1
            
            if cleaned_str.endswith('%'):
                multiplier = 0.01
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('T'):
                multiplier = 1e12
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('B'):
                multiplier = 1e9
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('M'):
                multiplier = 1e6
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('K'):
                multiplier = 1e3
                cleaned_str = cleaned_str[:-1]
            try:
                return float(cleaned_str.replace('X',''))
            except (ValueError, TypeError):
                return None

        # Parse all necessary raw values for logic
        gross_margin_raw = _parse_value(profit_data.get('Gross Margin (TTM)'))
        op_margin_raw = _parse_value(profit_data.get('Operating Margin (TTM)'))
        ebitda_margin_raw = _parse_value(profit_data.get('EBITDA Margin (TTM)'))
        net_margin_raw = _parse_value(profit_data.get('Profit Margin (TTM)'))
        rev_growth_raw = _parse_value(profit_data.get('Revenue Growth (YoY)'))
        
        # Get formatted values for display
        gross_margin_fmt = profit_data.get('Gross Margin (TTM)', 'N/A')
        op_margin_fmt = profit_data.get('Operating Margin (TTM)', 'N/A')
        ebitda_margin_fmt = profit_data.get('EBITDA Margin (TTM)', 'N/A')
        net_margin_fmt = profit_data.get('Profit Margin (TTM)', 'N/A')
        rev_growth_fmt = profit_data.get('Revenue Growth (YoY)', 'N/A')
        ebitda_fmt = profit_data.get('EBITDA (TTM)', 'N/A')
        gross_profit_fmt = profit_data.get('Gross Profit (TTM)', 'N/A')
        net_income_fmt = profit_data.get('Net Income (TTM)', 'N/A')
        
        # --- 2. Dynamic Narrative Generation ---
        p1_parts = []
        p2_parts = []

        # --- Paragraph 1: Margin Performance and Revenue Context ---
        margin_assessment = "shows the company has solid control over its costs and prices"
        if op_margin_raw is not None and op_margin_raw < 0.05:
            margin_assessment = "suggests the company faces significant margin pressure"
        elif op_margin_raw is not None and op_margin_raw < 0.10:
            margin_assessment = "indicates a moderately profitable operation, though with room for improvement"
        
        p1_parts.append(f"An analysis of the key metrics in {ticker}'s margin performance {margin_assessment}.")

        if gross_margin_raw is not None and op_margin_raw is not None:
            p1_parts.append(f"The company is successful in controlling its production costs, as shown by the gross margin of <strong>{gross_margin_fmt}</strong>, and it also profits well from its core operations, reflected in the <strong>{op_margin_fmt}</strong> operating margin.")
        
        if ebitda_margin_raw is not None:
             p1_parts.append(f"A <strong>{ebitda_margin_fmt}</strong> EBITDA margin indicates {ticker} is capable of generating strong cash flow from its operations before accounting for financing and tax strategies.")
        
        if net_margin_raw is not None:
            net_profit_cents = f"{net_margin_raw:.3f}"
            currency_symbol = get_currency_symbol(ticker)
            p1_parts.append(f"All things considered, {ticker} can hold onto around <strong>{currency_symbol}{net_profit_cents}</strong> in net profit for every {currency_symbol}1 of its revenue over the last twelve months.")
        
        if rev_growth_raw is not None:
            growth_rate_text = "an aggressive" if rev_growth_raw > 0.20 else "a moderate and healthy" if rev_growth_raw > 0.05 else "a slow"
            p1_parts.append(f"While the business's revenue is increasing at {growth_rate_text} rate (<strong>{rev_growth_fmt}</strong>), investors should monitor if this pace can be sustained without eroding profit margins.")

        # --- Paragraph 2: Profit vs. Growth and Synthesis ---
        p2_parts.append(f"{ticker}'s <strong>{ebitda_fmt}</strong> in EBITDA and <strong>{gross_profit_fmt}</strong> in gross profit indicate its raw earning power, while the <strong>{net_income_fmt}</strong> in net income reveals how effectively it converts that power into bottom-line results.")

        if op_margin_raw is not None and rev_growth_raw is not None:
            if op_margin_raw > 0.15 and rev_growth_raw < 0.10:
                p2_parts.append("From these indicators, it becomes clear that the company is currently prioritizing strong profitability over rapid, top-line growth.")
            elif op_margin_raw < 0.05 and rev_growth_raw > 0.15:
                p2_parts.append("This financial profile suggests the company is focused on aggressive growth and market capture, even at the expense of short-term profitability.")
            else:
                 p2_parts.append("The company appears to be balancing its pursuit of growth with the need to maintain profitability.")

        if gross_margin_raw is not None and net_margin_raw is not None:
            margin_spread = (gross_margin_raw - net_margin_raw) * 100
            if margin_spread > 20:
                p2_parts.append(f"Despite healthy gross margins, there is a significant difference between the company's gross and net margins ({gross_margin_fmt} vs. {net_margin_fmt}). This is likely due to high operating expenses, interest costs, or taxes, which are key areas for investors to watch.")

        p2_parts.append(f"In the future, maintaining steady or improving margins will be critical. {ticker} needs to defend its pricing power and control operating costs, as this will help sustain profitability, especially if revenue growth moderates.")
        
        # --- 3. Assemble Final HTML ---
        paragraph1_html = '<p>' + ' '.join(p1_parts) + '</p>' if p1_parts else ''
        paragraph2_html = '<p>' + ' '.join(p2_parts) + '</p>' if p2_parts else ''
        full_narrative_html = f'<div class="narrative">{paragraph1_html}{paragraph2_html}</div>'
        
        # Generate the data table
        table_html = generate_metrics_section_content(profit_data, ticker)
        
        return full_narrative_html + table_html

    except Exception as e:
        logging.error(f"Error in generate_profitability_growth_html for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Profitability & Growth", str(e))


def generate_dividends_shareholder_returns_html(ticker, rdata):
    """
    Generates a comprehensive "Dividends & Shareholder Returns" section
    aligned with the data keys from the provided report.
    """
    try:
        dividend_data = rdata.get('dividends_data', {})
        if not isinstance(dividend_data, dict):
            dividend_data = {}
            logging.warning("dividends_data not found or not a dict, using empty.")

        # 1. PRESERVED: Generate the original metrics table first
        # This uses the raw data as it appears in your file
        metrics_table_html = generate_metrics_section_content(dividend_data, ticker)

        # 2. ENHANCED & ALIGNED: Generate the detailed dividend analysis
        # --- Data Extraction using keys from your file ---
        rate = _safe_float(dividend_data.get('Dividend Rate'))
        div_yield = _safe_float(dividend_data.get('Dividend Yield'))
        payout_ratio = _safe_float(dividend_data.get('Payout Ratio'))
        five_year_avg_yield = _safe_float(dividend_data.get('5 Year Average Dividend Yield'))
        trailing_yield = _safe_float(dividend_data.get('Trailing Dividend Yield'))
        ex_div_date = dividend_data.get('Ex-Dividend Date')
        last_split_date_str = dividend_data.get('Last Split Date')
        last_split_factor = dividend_data.get('Last Split Factor')

        # --- Updated has_dividend check based on available data ---
        has_dividend = div_yield is not None and div_yield > 0 and payout_ratio is not None and payout_ratio > 0

        # --- Handle the "No Dividend" Case First ---
        if not has_dividend:
            narrative = f"""
                <div class="dividend-summary">
                    <h3>Dividend Summary & Investor Implications</h3>
                    <p>Based on available data, <strong>{ticker} does not currently pay a regular dividend</strong>. This suggests the company may be prioritizing reinvesting its earnings back into the business for growth.</p>
                </div>
            """
            return f'<div class="narrative">{narrative}</div>' + metrics_table_html

        # --- Build the Narrative for Companies with Dividends ---
        rate_fmt = format_html_value(rate, 'currency', ticker=ticker)
        yield_fmt = f'<strong>{format_html_value(div_yield, "percent_direct")}</strong>'
        payout_ratio_fmt = f'<strong>{format_html_value(payout_ratio, "percent_direct")}</strong>'
        five_year_avg_yield_fmt = format_html_value(five_year_avg_yield, 'percent_direct')

        # --- Paragraph 1: The Overview ---
        currency_symbol = get_currency_symbol(ticker)
        para1 = f"The company currently offers a <strong>{rate_fmt} annual dividend per share</strong>, translating to a dividend yield of {yield_fmt}—meaning for every {currency_symbol}100 invested, shareholders receive {rate_fmt} in dividends annually. "
        if five_year_avg_yield is not None and div_yield is not None:
            if div_yield < five_year_avg_yield:
                para1 += f"This yield is <strong>below the 5-year average of {five_year_avg_yield_fmt}</strong>, suggesting that either the stock price has risen (reducing the yield) or dividend growth hasn't kept pace with historical trends."
            else:
                para1 += f"This yield is <strong>above its 5-year average of {five_year_avg_yield_fmt}</strong>, making it more attractive to income investors today compared to its recent history."

        # --- Paragraph 2: Key Observations & Analysis ---
        analysis_points = []
        if payout_ratio is not None:
            payout_level = "healthy"
            if payout_ratio > 75: payout_level = "high (warranting a check on cash flow sustainability)"
            elif payout_ratio < 30: payout_level = "low and conservative"
            analysis_points.append(f"The <strong>payout ratio of {payout_ratio_fmt}</strong> is {payout_level}, indicating the company uses only ~{payout_ratio:.0f}% of its earnings to fund dividends. This leaves ample room for future increases or reinvestment in growth.")
        
        if trailing_yield is not None and trailing_yield < 0.1:
            analysis_points.append(f"The very low <strong>trailing yield of {format_html_value(trailing_yield, 'percent')}</strong> hints at a recent dividend initiation or a special, non-recurring payout, warranting further checks for consistency.")

        if ex_div_date:
            analysis_points.append(f"Investors must own the stock before the upcoming <strong>ex-dividend date of {format_html_value(ex_div_date, 'date')}</strong> to receive the next dividend.")
        
        if last_split_date_str:
            split_year = int(last_split_date_str.split('-')[0])
            if datetime.now().year - split_year > 15:
                analysis_points.append(f"The last stock split ({last_split_factor} in {split_year}) is outdated and likely irrelevant to the current valuation.")

        para2 = "<h4>Key Observations & Analysis:</h4><ul>" + "".join([f"<li>{point}</li>" for point in analysis_points]) + "</ul>"

        # --- Build the Conclusion / Investor Takeaway ---
        takeaway_income = ""
        takeaway_growth = ""
        if payout_ratio is not None and payout_ratio < 40:
            takeaway_income = "<li><strong>Income Investors:</strong> The modest yield and low payout ratio suggest dividends are safe but not a primary reason to invest. The focus may be on future dividend growth.</li>"
            takeaway_growth = "<li><strong>Growth Investors:</strong> The low payout ratio is a strong signal that a majority of earnings are being reinvested, which could drive future price appreciation.</li>"
        else:
            takeaway_income = "<li><strong>Income Investors:</strong> The dividend appears sustainable, but investors should monitor earnings and cash flow to ensure the payout remains well-supported.</li>"
            takeaway_growth = "<li><strong>Growth Investors:</strong> The company maintains a balance between shareholder returns and reinvestment, appealing to a 'growth and income' strategy.</li>"

        # --- Assemble the Final HTML ---
        dividend_summary_html = f"""
        <div class="dividend-summary">
            <h3>Dividend Summary & Investor Implications</h3>
            <p>{para1}</p>
            <div>{para2}</div>
            <div class="investor-takeaway">
                <h4>Investor Takeaway:</h4>
                <ul>
                    {takeaway_income}
                    {takeaway_growth}
                    <li><strong>Watch For:</strong> Announcements of dividend hikes (which could bring the yield closer to its historical average) or significant stock price changes that would alter the yield.</li>
                </ul>
            </div>
        </div>
        """
        
        # This section is preserved for universality but won't trigger for DIS as it has no buyback data
        buyback_summary_html = ""
        # ... (buyback logic from previous function would go here)
        
        return f'<div class="narrative">{dividend_summary_html}{buyback_summary_html}</div>{metrics_table_html}'

    except Exception as e:
        logging.error(f"Error in generating dividend summary for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Dividends & Shareholder Returns", str(e))


def generate_share_statistics_html(ticker, rdata):
    """
    Generates the Share Statistics and Short Interest summary with a dynamically
    generated narrative split into two paragraphs for better readability.
    """
    try:
        # --- 1. Data Extraction and Helper Function ---
        share_data = rdata.get('share_statistics_data', {})
        short_data = rdata.get('short_selling_data', {})
        # Helper to parse formatted values like '$2B' or '1.1%' into numbers
        def _parse_value(value_str):
            if value_str is None or not isinstance(value_str, str) or value_str.lower() == 'n/a':
                return None
            
            cleaned_str = value_str.strip().upper().replace('$', '').replace(',', '')
            multiplier = 1
            
            if cleaned_str.endswith('%'):
                multiplier = 0.01
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('T'):
                multiplier = 1e12
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('B'):
                multiplier = 1e9
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('M'):
                multiplier = 1e6
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('K'):
                multiplier = 1e3
                cleaned_str = cleaned_str[:-1]

            try:
                return float(cleaned_str.replace('X','')) * multiplier
            except (ValueError, TypeError):
                return None

        # --- 2. Parse Raw Values for Logic ---
        shares_out_raw = _parse_value(share_data.get('Shares Outstanding'))
        shares_float_raw = _parse_value(share_data.get('Shares Float'))
        insider_own_raw = _parse_value(share_data.get('Insider Ownership'))
        inst_own_raw = _parse_value(share_data.get('Institutional Ownership'))
        shares_short_raw = _parse_value(short_data.get('Shares Short'))
        short_float_raw = _parse_value(short_data.get('Short % of Float'))
        
        # --- 3. Dynamic Narrative Generation (in two paragraphs) ---
        p1_parts = []
        p2_parts = []
        
        # Paragraph 1: Float, Liquidity, and Ownership
        if shares_out_raw is not None and shares_float_raw is not None:
            float_percentage = (shares_float_raw / shares_out_raw) * 100 if shares_out_raw > 0 else 0
            if float_percentage > 95:
                p1_parts.append(f"Nearly all of the company's <strong>{share_data.get('Shares Outstanding', 'N/A')}</strong> shares are publicly available as float, so no major amount is locked up.")
            else:
                locked_up_pct = 100 - float_percentage
                p1_parts.append(f"About <strong>{locked_up_pct:.1f}%</strong> of the company's shares are closely held by insiders or strategic investors, with the remaining <strong>{share_data.get('Shares Float', 'N/A')}</strong> available for public trading.")
            
            if shares_float_raw > 50_000_000:
                 p1_parts.append("Because the float is high, investors can typically trade this stock without causing significant price shifts.")
            
            p1_parts.append("However, investors should be aware that the company could issue more shares, potentially diluting the value of existing stock.")
        else:
            p1_parts.append("Information on the total number of shares and the publicly traded float was not available, which can impact understanding of the stock's liquidity and ownership structure.")

        ownership_narrative = ""
        if insider_own_raw is not None:
            ownership_level = "very little" if insider_own_raw < 0.01 else "a small amount" if insider_own_raw < 0.05 else "a significant stake"
            implication = "meaning they may not have substantial 'skin in the game' if the company struggles" if insider_own_raw < 0.01 else "which helps align their interests with shareholders"
            ownership_narrative += (f"Executives and major shareholders own <strong>{ownership_level}</strong> of the company ({share_data.get('Insider Ownership', 'N/A')}), {implication}. ")
        
        if inst_own_raw is not None:
            inst_level = "also small" if inst_own_raw < 0.30 else "significant" if inst_own_raw > 0.7 else "healthy"
            inst_implication = "This is much less than the averages found in widely held stocks. If big-money investors are avoiding the stock, it could be due to concerns about performance or simply a lack of focus on the company." if inst_own_raw < 0.30 else "This level of institutional backing provides a degree of stability and confidence in the stock."
            ownership_narrative += (f"The level of ownership by institutions is <strong>{inst_level}</strong>, coming in at <strong>{share_data.get('Institutional Ownership', 'N/A')}</strong>. {inst_implication}")
        
        if ownership_narrative:
            p1_parts.append(ownership_narrative)

        # Paragraph 2: Short Interest and Synthesis
        short_narrative = ""
        if shares_short_raw is not None and short_float_raw is not None:
            short_level_text = "bears are not expressing much concern for the company"
            if short_float_raw > 0.10:
                short_level_text = "a significant portion of the market is betting against the stock, indicating high perceived risk"
            elif short_float_raw > 0.03:
                short_level_text = "there is a notable level of bearish sentiment"

            short_narrative = (
                f"We will now look into the impact of short interest on the market. At the current level of <strong>{short_data.get('Shares Short', 'N/A')}</strong> shorted shares ({short_data.get('Short % of Float', 'N/A')} of the float), it suggests that {short_level_text}. "
                "Watch for changes in short interest, as a sharp increase may indicate that more investors are becoming doubtful. Conversely, very low short interest during positive news can sometimes discourage a 'short squeeze'."
            )
            p2_parts.append(short_narrative)
        
        synthesis = ""
        if (shares_float_raw is not None and shares_float_raw > 50_000_000) and (inst_own_raw is not None and inst_own_raw < 0.30):
            synthesis = "When we look at all of these factors, we can see that while the stock is liquid and easy to trade, its price may not see sustained growth unless it gains stronger support from large institutional traders or company insiders."
        elif (insider_own_raw is not None and insider_own_raw > 0.10) and (inst_own_raw is not None and inst_own_raw > 0.70):
            synthesis = "Overall, the combination of high insider and institutional ownership suggests strong internal and external confidence, creating a solid foundation for the stock's stability and potential growth."
        
        if synthesis:
            p2_parts.append(synthesis)

        # --- 4. Assemble Final HTML ---
        paragraph1_html = '<p>' + ' '.join(p1_parts) + '</p>' if p1_parts else ''
        paragraph2_html = '<p>' + ' '.join(p2_parts) + '</p>' if p2_parts else ''
        full_narrative_html = f'<div class="narrative">{paragraph1_html}{paragraph2_html}</div>'
        
        # Combine data for the table view
        combined_data_for_table = {**share_data, **short_data}
        table_html = generate_metrics_section_content(combined_data_for_table, ticker)
        
        return full_narrative_html + table_html

    except Exception as e:
        logging.error(f"Error in generate_share_statistics_html for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Share Statistics", str(e))
    

def generate_stock_price_statistics_html(ticker, rdata):
    """Generates Stock Price Statistics section with a dynamic, two-paragraph narrative."""
    try:
        # --- 1. Data Extraction and Parsing ---
        stats_data = rdata.get('stock_price_stats_data', {})

        # Get raw values for logic
        high_52wk = _safe_float(stats_data.get('52 Week High'), default=None)
        low_52wk = _safe_float(stats_data.get('52 Week Low'), default=None)
        sma_50 = _safe_float(rdata.get('sma_50'), default=None)
        sma_200 = _safe_float(rdata.get('sma_200'), default=None)
        beta = _safe_float(stats_data.get('Beta'), default=None)
        volatility = _safe_float(rdata.get('volatility'), default=None)

        # Get formatted values for display
        high_52wk_fmt = format_html_value(high_52wk, 'currency', ticker=ticker)
        low_52wk_fmt = format_html_value(low_52wk, 'currency', ticker=ticker)
        sma_50_fmt = format_html_value(sma_50, 'currency', ticker=ticker)
        sma_200_fmt = format_html_value(sma_200, 'currency', ticker=ticker)
        beta_fmt = format_html_value(beta, 'ratio')
        volatility_fmt = format_html_value(volatility, 'percent_direct', 1)

        # Add volatility to stats_data for table display if not present
        if 'Volatility (30d Ann.)' not in stats_data and volatility_fmt != "N/A":
            stats_data['Volatility (30d Ann.)'] = f"{volatility_fmt} {get_icon('stats')}"

        p1_parts = []
        p2_parts = []

        # --- 2. Narrative Generation: Paragraph 1 (Range & MAs) ---
        if high_52wk is not None and low_52wk is not None:
            p1_parts.append(f"When looking at the price range over the past year, the stock has seen a high of <strong>{high_52wk_fmt}</strong> and a low of <strong>{low_52wk_fmt}</strong>.")
            
            range_pct = (high_52wk - low_52wk) / low_52wk if low_52wk > 0 else 0
            if range_pct > 0.5:
                p1_parts.append("This wide gap tells us the stock has been through significant fluctuations, likely influenced by market sentiment or company-specific news.")
            elif range_pct > 0.25:
                p1_parts.append("This moderate gap indicates the stock has experienced notable price swings over the year.")
            else:
                p1_parts.append("This relatively narrow gap suggests the stock has traded within a more stable range over the past year.")

        if sma_50 is not None and sma_200 is not None:
            diff_pct = abs(sma_50 - sma_200) / sma_200 if sma_200 > 0 else 0
            proximity = "slightly" if diff_pct < 0.05 else ""
            
            if sma_50 < sma_200:
                p1_parts.append(f"Currently, the 50-day moving average stands at <strong>{sma_50_fmt}</strong>, which is {proximity} below the 200-day moving average of <strong>{sma_200_fmt}</strong>.")
                p1_parts.append("This setup may signal a short-term pullback or consolidation phase, especially for technical traders tracking momentum and trend direction.")
            else:
                p1_parts.append(f"Currently, the 50-day moving average at <strong>{sma_50_fmt}</strong> is {proximity} above the 200-day moving average of <strong>{sma_200_fmt}</strong>.")
                p1_parts.append("This 'golden cross' setup is often viewed as a bullish signal, indicating positive long-term momentum.")
        
        # --- 3. Narrative Generation: Paragraph 2 (Volatility & Beta) ---
        if beta is not None:
            beta_move_pct = abs(beta - 1) * 100
            if beta > 1.2:
                p2_parts.append(f"The stock carries a beta of <strong>{beta_fmt}</strong>, which means it tends to move more sharply than the broader market—about {beta_move_pct:.0f}% more volatile.")
            elif beta < 0.8 and beta > 0:
                p2_parts.append(f"With a beta of <strong>{beta_fmt}</strong>, the stock tends to be less volatile than the broader market, moving about {beta_move_pct:.0f}% less.")
            else:
                 p2_parts.append(f"A beta of <strong>{beta_fmt}</strong> suggests the stock's movement is generally in line with the broader market.")
        
        if volatility is not None:
            volatility_desc = "high" if volatility > 40 else "moderate" if volatility > 20 else "low"
            if beta is not None:
                p2_parts.append(f"Combined with a {volatility_desc} 30-day annualized volatility of <strong>{volatility_fmt}</strong>, it's clear this stock sees frequent price swings.")
            else:
                p2_parts.append(f"A 30-day annualized volatility of <strong>{volatility_fmt}</strong> indicates the stock experiences {volatility_desc} price swings.")

        if beta is not None or volatility is not None:
             p2_parts.append("For investors, this means potential for gains, but also higher downside risk. These indicators matter when deciding position sizing or entry timing, especially if you're managing a portfolio that balances stability with growth exposure.")

        # --- 4. Assemble Final HTML ---
        paragraph1 = '<p>' + ' '.join(p1_parts) + '</p>' if p1_parts else ''
        paragraph2 = '<p>' + ' '.join(p2_parts) + '</p>' if p2_parts else ''
        narrative_html = f'<div class="narrative">{paragraph1}{paragraph2}</div>' if (p1_parts or p2_parts) else ''
        
        table_html = generate_metrics_section_content(stats_data, ticker)

        return narrative_html + table_html

    except Exception as e:
        logging.error(f"Error in generate_stock_price_statistics_html for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Stock Price Statistics", str(e))



def generate_short_selling_info_html(ticker, rdata):
    """Generates a dynamic narrative and data table for the Short Selling Info section."""
    try:
        # --- 1. Data Extraction and Parsing ---
        short_data = rdata.get('short_selling_data', {})
        if not isinstance(short_data, dict) or not short_data:
            return _generate_error_html("Short Selling Information", "No short selling data available.")

        # Helper to parse formatted values like '$22M' or '1.20%' into numbers
        def _parse_short_value(value_str):
            if value_str is None or not isinstance(value_str, str) or value_str.lower() == 'n/a':
                return None
            
            cleaned_str = value_str.strip().upper().replace('$', '').replace(',', '')
            multiplier = 1
            
            if cleaned_str.endswith('%'):
                multiplier = 0.01
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('T'):
                multiplier = 1e12
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('B'):
                multiplier = 1e9
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('M'):
                multiplier = 1e6
                cleaned_str = cleaned_str[:-1]
            elif cleaned_str.endswith('K'):
                multiplier = 1e3
                cleaned_str = cleaned_str[:-1]
            
            try:
                # Handle 'x' in ratios
                return float(cleaned_str.replace('X', '')) * multiplier
            except (ValueError, TypeError):
                return None

        # Parse raw values for logic
        shares_short_val = _parse_short_value(short_data.get('Shares Short'))
        short_ratio_val = _parse_short_value(short_data.get('Short Ratio (Days To Cover)'))
        short_float_pct_val = _parse_short_value(short_data.get('Short % of Float'))
        shares_short_prior_val = _parse_short_value(short_data.get('Shares Short (Prior Month)'))
        
        # Get formatted values for display
        shares_short_fmt = short_data.get('Shares Short', 'N/A')
        short_ratio_fmt = short_data.get('Short Ratio (Days To Cover)', 'N/A')
        short_float_pct_fmt = short_data.get('Short % of Float', 'N/A')
        shares_short_prior_fmt = short_data.get('Shares Short (Prior Month)', 'N/A')

        # --- 2. Dynamic Narrative Generation ---
        p1_parts = []
        p2_parts = []

        # Paragraph 1: Short Interest and Days to Cover
        if shares_short_val is not None and short_ratio_val is not None:
            p1_parts.append(f"There is currently <strong>{shares_short_fmt}</strong> worth of short interest in {ticker}, and the short ratio (or days to cover) is <strong>{short_ratio_fmt}</strong>.")
            
            days_to_cover = round(short_ratio_val)
            if days_to_cover <= 1:
                days_text = "about one day"
            elif days_to_cover <= 3:
                days_text = f"around {days_to_cover} days"
            else:
                 days_text = f"several days"
            p1_parts.append(f"This means that at the stock's recent average trading volume, it would take {days_text} for all short positions to be covered.")
            
            if short_ratio_val < 3:
                p1_parts.append("This low level suggests that short sellers do not currently have significant control over the stock's price, and the risk of a prolonged 'short squeeze' is relatively low.")
            elif short_ratio_val > 10:
                 p1_parts.append("This high level indicates it would take a long time for short sellers to buy back their shares, which could lead to extreme volatility or a powerful 'short squeeze' if the stock's price starts to rise unexpectedly.")
            else:
                 p1_parts.append("This moderate level indicates a balance between bearish bets and the market's ability to absorb them without extreme volatility.")
        else:
             p1_parts.append("Data on the current short interest and days to cover is not fully available, making it difficult to assess the immediate influence of short sellers.")

        # Paragraph 2: Short % of Float and Trend
        if short_float_pct_val is not None:
            if short_float_pct_val < 0.02: # < 2%
                float_interp = "a very low percentage of the available shares are being shorted, indicating a general lack of bearish sentiment among investors."
            elif short_float_pct_val < 0.10: # < 10%
                float_interp = "a moderate percentage of the stock is being shorted, showing some bearish sentiment but not an extreme level."
            else: # > 10%
                float_interp = "a high percentage of the float is being shorted, signaling significant bearish conviction from a portion of the market."

            p2_parts.append(f"With <strong>{short_float_pct_fmt}</strong> of the public float sold short, {float_interp}")
        
        if shares_short_val is not None and shares_short_prior_val is not None:
            change_pct = ((shares_short_val - shares_short_prior_val) / shares_short_prior_val) * 100 if shares_short_prior_val > 0 else 0
            if change_pct < -5:
                trend_text = f"has decreased recently from {shares_short_prior_fmt}"
            elif change_pct > 5:
                trend_text = f"has increased recently from {shares_short_prior_fmt}"
            else:
                trend_text = f"has remained relatively stable compared to last month's value of {shares_short_prior_fmt}"
            
            p2_parts.append(f"This level {trend_text}, suggesting a shift in bearish sentiment.")

        if short_float_pct_val is not None:
            if short_float_pct_val < 0.05:
                p2_parts.append("Because the amount of investors shorting is generally low, the market tends to feel more confident and the risks of price swings from sudden short-covering activities are reduced.")
            else:
                p2_parts.append("With notable short interest, investors should be aware of potential volatility spikes, which could be triggered by news events that force short sellers to cover their positions.")


        # --- 3. Assemble Final HTML ---
        paragraph1 = '<p>' + ' '.join(p1_parts) + '</p>' if p1_parts else ''
        paragraph2 = '<p>' + ' '.join(p2_parts) + '</p>' if p2_parts else ''
        narrative_html = f'<div class="narrative">{paragraph1}{paragraph2}</div>' if (p1_parts or p2_parts) else ''
        
        table_html = generate_metrics_section_content(short_data, ticker)

        return narrative_html + table_html

    except Exception as e:
        logging.error(f"Error in generate_short_selling_info_html for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Short Selling Information", str(e))
    

def generate_analyst_grid_html(analyst_data):
    """Helper specifically for the analyst grid layout (Robust NA handling)."""
    try:
        if not isinstance(analyst_data, dict):
             logging.warning("Analyst data is not a dict, cannot generate grid.")
             return "<p>Analyst consensus data could not be processed.</p>"

        valid_data_formatted = {}
        for k, v in analyst_data.items():
             format_type = 'string'
             k_lower = str(k).lower()
             if 'price' in k_lower: format_type = 'currency'
             elif 'opinions' in k_lower or 'number' in k_lower: format_type = 'integer'
             elif 'recommendation' in k_lower: format_type = 'factor' 

             formatted_v = format_html_value(v, format_type)
             if formatted_v != "N/A":
                 valid_data_formatted[str(k)] = formatted_v 

        if not valid_data_formatted:
            return "<p>No specific analyst consensus data is currently available or displayable.</p>"

        html = '<div class="analyst-grid">'
        key_order = ["Recommendation", "Mean Target Price", "High Target Price", "Low Target Price", "Number of Analyst Opinions"]
        displayed_keys = set()

        for key in key_order:
            if key in valid_data_formatted:
                 html += f'<div class="analyst-item"><span>{key}:</span> {valid_data_formatted[key]}</div>'
                 displayed_keys.add(key)

        for key, value in valid_data_formatted.items():
            if key not in displayed_keys:
                html += f'<div class="analyst-item"><span>{key}:</span> {value}</div>'

        html += '</div>'
        return html
    except Exception as e:
         logging.error(f"Error generating analyst grid: {e}")
         return "<p>Error displaying analyst consensus data.</p>"


def generate_analyst_insights_html(ticker, rdata):
    """Generates Analyst Insights with a default narrative focus."""
    try:
        analyst_data = rdata.get('analyst_info_data')
        if not isinstance(analyst_data, dict):
             analyst_data = {}
             logging.warning("analyst_info_data not found or not a dict, using empty.")

        grid_html = generate_analyst_grid_html(analyst_data) 

        recommendation = format_html_value(analyst_data.get('Recommendation'), 'factor') 
        mean_target_fmt = format_html_value(analyst_data.get('Mean Target Price'), 'currency', ticker=ticker)
        high_target_fmt = format_html_value(analyst_data.get('High Target Price'), 'currency', ticker=ticker)
        low_target_fmt = format_html_value(analyst_data.get('Low Target Price'), 'currency', ticker=ticker)
        num_analysts_fmt = format_html_value(analyst_data.get('Number of Analyst Opinions'), 'integer')
        current_price = _safe_float(rdata.get('current_price'))
        current_price_fmt = format_html_value(current_price, 'currency', ticker=ticker)

        potential_summary = ""
        mean_potential_fmt = "N/A"
        target_range_fmt = f"{low_target_fmt} - {high_target_fmt}" if low_target_fmt != 'N/A' and high_target_fmt != 'N/A' else "N/A"

        mean_target_val = _safe_float(analyst_data.get('Mean Target Price'))
        if mean_target_val is not None and current_price is not None and current_price > 0:
             potential = ((mean_target_val - current_price) / current_price) * 100
             mean_potential_fmt = format_html_value(potential, 'percent_direct', 1)
             potential_direction = "upside" if potential > 0 else "downside" if potential < 0 else "change"
             potential_summary_options = [
                f" Based on the mean target ({mean_target_fmt}), this implies a potential <strong>{potential_direction} of ~{mean_potential_fmt}</strong> from the current price ({current_price_fmt}).",
                f" The average target ({mean_target_fmt}) suggests roughly <strong>{mean_potential_fmt} potential {potential_direction}</strong> compared to the current price ({current_price_fmt})."
             ]
             potential_summary = random.choice(potential_summary_options)
        
        analyst_count_context_options = [
             f"This consensus is based on opinions from {num_analysts_fmt} analysts(s)." if num_analysts_fmt != 'N/A' else "The number of contributing analysts is unspecified.",
             f"{num_analysts_fmt} analyst(s) contributed to this consensus view." if num_analysts_fmt != 'N/A' else "The analyst count for this consensus is not available."
        ]
        analyst_count_context = random.choice(analyst_count_context_options)

        # Default Narrative
        narrative_options = [
            (
                 f"This section summarizes the collective view of professional analysts covering {ticker}. The consensus recommendation is <strong>'{recommendation}'</strong>. {analyst_count_context} "
                 f"The mean price target is {mean_target_fmt}, with individual targets ranging from {target_range_fmt}.{potential_summary} This provides a gauge of Wall Street sentiment regarding the stock's potential."
            ),
            (
                 f"Here's the consensus from Wall Street analysts on {ticker}. The average recommendation is <strong>'{recommendation}'</strong>. {analyst_count_context} "
                 f"Targets average {mean_target_fmt} (within a range of {target_range_fmt}).{potential_summary} This reflects overall analyst sentiment on the stock's outlook."
            )
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + grid_html
    except Exception as e:
        return _generate_error_html("Analyst Insights", str(e))

def generate_technical_analysis_summary_html(ticker, rdata):
    """
    Generates the new, detailed, and narrative-driven technical analysis summary.
    This version provides actionable insights and a structured trading plan with enhanced dynamic text.
    """
    try:
        # --- 1. Data Extraction (No Changes Here) ---
        detailed_ta = rdata.get('detailed_ta_data', {})
        
        # Helper function to safely convert to float
        def _safe_float(value):
            if value is None: return None
            try: return float(value)
            except (ValueError, TypeError): return None

        price = _safe_float(detailed_ta.get('Current_Price'))
        change_15d = _safe_float(detailed_ta.get('change_15d_pct'))
        sma20 = _safe_float(detailed_ta.get('SMA_20'))
        sma50 = _safe_float(detailed_ta.get('SMA_50'))
        sma200 = _safe_float(detailed_ta.get('SMA_200'))
        rsi = _safe_float(detailed_ta.get('RSI_14'))
        macd_hist = _safe_float(detailed_ta.get('MACD_Hist'))
        bb_upper = _safe_float(detailed_ta.get('BB_Upper'))
        bb_lower = _safe_float(detailed_ta.get('BB_Lower'))
        support = _safe_float(detailed_ta.get('Support_30D'))
        resistance = _safe_float(detailed_ta.get('Resistance_30D'))
        volume_vs_sma = _safe_float(detailed_ta.get('Volume_vs_SMA20_Ratio'))

        # --- 2. Build Enhanced Dynamic Narrative Components ---

        # Headline (Updated to be bold text instead of h4)
        trend_status = "Bullish" if price and sma200 and price > sma200 else "Bearish"
        qualitative_assessment = "but Overheated" if rsi and rsi > 75 else "but shows signs of slowing" if macd_hist is not None and macd_hist < 0 else ""
        if trend_status == "Bearish":
            qualitative_assessment = "but looks Oversold" if rsi and rsi < 30 else "and continues to weaken"
        headline = f"<p><strong>CURRENT PRICE: {format_html_value(price, 'currency', ticker=ticker).upper()}&nbsp;|&nbsp;TREND: {trend_status.upper()} {qualitative_assessment.upper()}</strong></p>"

        # UPDATED: Context-Aware Intro Paragraph
        if change_15d is not None and change_15d > 0:
            intro_para = f"The stock has been on a notable run, gaining <strong>{change_15d:+.2f}% in just 15 days</strong>, but several technical signs suggest we should be cautious about chasing this momentum. Let's break down what the charts are telling us and how we can position ourselves."
        elif change_15d is not None and change_15d < 0:
            intro_para = f"The stock has faced downward pressure, losing <strong>{change_15d:+.2f}% in the last 15 days</strong>. We need to analyze the technicals to see if this is a buying opportunity or a warning of further declines. Let's break down the key levels."
        else:
            intro_para = f"The stock has been trading sideways recently. Let's dive into the technical indicators to identify the next potential move and key trading levels."

        # Section 1: Trend Strength (with UPDATED trader takeaway)
        trend_narrative = f"{ticker} is trading above its key moving averages, which confirms the uptrend remains intact." if trend_status == "Bullish" else f"{ticker} is in a bearish trend, trading below its key moving averages, which signals caution."
        support_20sma = f"The <strong>20-day SMA at {format_html_value(sma20, 'currency', ticker=ticker)}</strong> is acting as immediate dynamic support."
        floor_200sma = f"The <strong>200-day SMA at {format_html_value(sma200, 'currency', ticker=ticker)}</strong> serves as a major long-term floor for the bullish trend."
        
        # --- THIS IS THE NEW DYNAMIC LOGIC ---
        if trend_status == "Bullish":
            trader_takeaway_trend = f"As long as {ticker} holds above the <strong>20-day SMA ({format_html_value(sma20, 'currency', ticker=ticker)})</strong>, the bullish momentum could continue. However, a rapid rise can push the stock far from its averages, increasing the risk of a pullback."
        else: # Bearish
            trader_takeaway_trend = f"The <strong>20-day SMA ({format_html_value(sma20, 'currency', ticker=ticker)})</strong> is now acting as overhead resistance. As long as the price stays below this level, the bearish trend is likely to continue. A rejection from this average could lead to a test of recent lows."
        # --- END OF NEW DYNAMIC LOGIC ---

        # Section 2: Momentum (with UPDATED trading strategy)
        rsi_signal = "flashing a strong overbought signal" if rsi and rsi > 70 else "in a neutral zone, indicating balanced momentum" if rsi and 30 <= rsi <= 70 else "showing oversold conditions, hinting at a potential bounce"
        rsi_pullback_chance = "Historically, when the RSI crosses above 70-75, we often see a pullback before the next leg up." if rsi and rsi > 70 else ""
        macd_signal_text = "the MACD histogram is negative, suggesting that the upward momentum is beginning to fade." if macd_hist is not None and macd_hist < 0 else "the MACD histogram is positive, confirming the upward momentum is still in play."

        # --- THIS IS THE NEW DYNAMIC LOGIC ---
        if rsi and rsi > 70:
            trader_strategy_momentum = "Aggressive traders might consider taking partial profits. Conservative traders should wait for the RSI to cool below 70 before considering new positions."
        elif rsi and rsi < 30:
            trader_strategy_momentum = "This oversold reading suggests a potential bounce. Aggressive traders might look for a short-term buy signal, while conservative traders should wait for the RSI to cross back above 30 to confirm a reversal."
        else: # Neutral RSI
            trader_strategy_momentum = "This neutral RSI reading provides flexibility. Watch for a decisive MACD crossover or a break of a key support/resistance level for the next directional clue."
        # --- END OF NEW DYNAMIC LOGIC ---

        # Section 3: Bollinger Bands (with FULLY REWRITTEN dynamic logic)
        # --- THIS IS THE NEW DYNAMIC LOGIC ---
        if price and bb_upper and price > bb_upper:
            bb_narrative = f"The price is 'walking the band,' trading <strong>above the upper Bollinger Band ({format_html_value(bb_upper, 'currency', ticker=ticker)})</strong>. This is a sign of a very strong trend, but also increases the risk of a sharp snap-back if momentum stalls."
        elif price and bb_lower and price < bb_lower:
            bb_narrative = f"The price has broken <strong>below the lower Bollinger Band ({format_html_value(bb_lower, 'currency', ticker=ticker)})</strong>, indicating strong selling pressure and a potential breakdown. Watch for signs of capitulation or reversal."
        elif price and bb_upper and price >= bb_upper * 0.98:
            bb_narrative = f"The stock is currently pressing against the <strong>upper Bollinger Band at {format_html_value(bb_upper, 'currency', ticker=ticker)}</strong>, which often acts as short-term resistance."
        elif price and bb_lower and price <= bb_lower * 1.02:
            bb_narrative = f"The stock is testing support near the <strong>lower Bollinger Band at {format_html_value(bb_lower, 'currency', ticker=ticker)}</strong>. A bounce from this level would be bullish, while a break below would be a bearish signal."
        elif price and sma20 and price > sma20:
             bb_narrative = f"The stock is trading comfortably in the upper half of its Bollinger Bands (between the 20-day SMA and the upper band), which is a sign of underlying strength."
        else: # Fallback for trading in the lower half or near the middle
            bb_narrative = f"The stock is trading near the middle of its Bollinger Bands (SMA20: {format_html_value(sma20, 'currency', ticker=ticker)}), with the lower band at <strong>{format_html_value(bb_lower, 'currency', ticker=ticker)}</strong> offering the next level of support."
        # --- END OF NEW DYNAMIC LOGIC ---
        
        # ... (Rest of the function remains the same as the robust version from the previous turn) ...
        # Section 4: Volume (No changes needed)
        volume_narrative = "While the stock has been rising, <strong>trading volume has been declining</strong> (below its 20-day average), which is a red flag for trend sustainability." if volume_vs_sma and volume_vs_sma < 0.9 and change_15d and change_15d > 0 else "Trading volume is near its recent average, providing neutral confirmation of the current price action."
        volume_concern = "Low volume rallies are prone to sharp reversals. If we don't see a surge in buying interest to confirm the move, a pullback becomes more likely." if volume_vs_sma and volume_vs_sma < 0.9 else ""

        # Final Verdict and Bottom Line (Can remain as is, they synthesize the above points)
        short_term_verdict = f"Be cautious—RSI is overbought at {rsi:.1f}, and volume is weak. Consider locking in partial profits near {format_html_value(resistance, 'currency', )} and waiting for a better entry near the 20-day SMA ({format_html_value(sma20, 'currency', )})." if rsi and rsi > 70 else "The trend is positive but monitor for signs of exhaustion. A neutral stance may be best until a clearer signal emerges from the MACD or volume."
        long_term_verdict = f"The long-term uptrend is valid as long as the price holds above the 200-day SMA ({format_html_value(sma200, 'currency', )}). A pullback to the 50-day SMA ({format_html_value(sma50, 'currency', )}) area could present a safer buying opportunity."
        new_buyers_verdict = f"Avoid chasing the rally here. Wait for either a confirmed breakout above <strong>{format_html_value(resistance, 'currency', )} with strong volume</strong>, or a pullback to the <strong>{format_html_value(sma20, 'currency', )}</strong> area, which offers a better risk/reward entry."
        bottom_line = "The technicals suggest the rally may be running out of steam short-term. While the long-term trend remains bullish, a correction seems plausible before the next major move. Trade carefully and wait for confirmation at key levels."


        # --- 3. Assemble the HTML (No changes here) ---
        html_output = f"""
        <div class="technical-analysis-summary-pro">
            {headline}
            <p>{intro_para}</p>

            <h3>Trend Strength – Still {trend_status}</h3>
            <p>{trend_narrative} {support_20sma if trend_status == "Bullish" else ""}</p>
            <div class="takeaway">
                <p><strong><i class="fas fa-chart-line"></i> What This Means for Traders?</strong></p>
                <p>{trader_takeaway_trend}</p>
            </div>

            <h3>Momentum Check – { "Time to Be Cautious" if rsi and rsi > 70 else "Potential Bounce Ahead?" if rsi and rsi < 30 else "Is Momentum Fading?"}</h3>
            <p>The <strong>RSI at {rsi:.1f}</strong> is {rsi_signal}. {rsi_pullback_chance} At the same time, {macd_signal_text}</p>
            <div class="takeaway">
                <p><strong><i class="fas fa-chess-knight"></i> Trading Strategy:</strong></p>
                <p>{trader_strategy_momentum}</p>
            </div>

            <h3>Bollinger Bands – Testing Key Levels</h3>
            <p>{bb_narrative}</p>
            <div class="takeaway">
                <p><strong><i class="fas fa-bullseye"></i> Key Levels to Watch:</strong></p>
                <ul>
                    <li>Resistance: <strong>{format_html_value(resistance, 'currency', ticker=ticker)}</strong> (Recent High) &rarr; A breakout could push {ticker} higher.</li>
                    <li>Support: <strong>{format_html_value(sma20, 'currency', ticker=ticker)}</strong> (20-day SMA) &rarr; If this breaks, expect a test of <strong>{format_html_value(bb_lower, 'currency', ticker=ticker)}</strong>.</li>
                </ul>
            </div>

            <h3>Volume Trends – Checking for Conviction</h3>
            <p>{volume_narrative}</p>
              {f"<div class='takeaway'><p><strong><i class='fas fa-exclamation-triangle'></i> What's the Concern?</strong></p><p>{volume_concern}</p></div>" if volume_concern else ''}
            <h3>Support & Resistance – The Trading Plan</h3>
            <div class="takeaway">
                <p><strong><i class="fas fa-map-signs"></i> Trading Plan:</strong></p>
                <ul>
                    <li>✅&nbsp; <strong>If {ticker} holds above {format_html_value(sma20, 'currency', ticker=ticker)}</strong> &rarr; Bullish trend continues, next target {format_html_value(resistance, 'currency', ticker=ticker)}.</li>
                    <li>⚠️&nbsp; <strong>If it breaks below {format_html_value(sma20, 'currency', ticker=ticker)}</strong> &rarr; Expect a dip toward {format_html_value(bb_lower, 'currency', ticker=ticker)}.</li>
                    <li>🛑&nbsp; <strong>A drop below {format_html_value(bb_lower, 'currency', ticker=ticker)}</strong> &rarr; Could trigger a deeper correction to the 200-day SMA ({format_html_value(sma200, 'currency', ticker=ticker)}).</li>
                </ul>
            </div>
            
            <h3>Final Verdict – Should You Buy, Hold, or Sell?</h3>
            <div class="verdict-grid">
                <div class="verdict-item"><strong>Short-Term Traders:</strong> {short_term_verdict}</div>
                <div class="verdict-item"><strong>Long-Term Investors:</strong> {long_term_verdict}</div>
                <div class="verdict-item"><strong>New Buyers:</strong> {new_buyers_verdict}</div>
            </div>
            
            <p class="bottom-line"><strong>Bottom Line:</strong> {bottom_line}</p>
        </div>
        """
        style = """
        <style>
            <style>
            .technical-analysis-summary-pro { font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #495057; }
            .technical-analysis-summary-pro h3 { font-size: 1.1em; color: #34495e; margin-top: 1.25em; margin-bottom: 0.5em; padding-bottom: 0.25em; border-bottom: 1px solid #ecf0f1; font-weight: 600;}
            .technical-analysis-summary-pro p { margin-bottom: 1em; font-size: 0.95rem; }
            .technical-analysis-summary-pro .takeaway { background-color: #f8f9fa; border-left: 4px solid #10ac84; padding: 0.8em 1.2em; margin: 1em 0; border-radius: 4px; }
            .technical-analysis-summary-pro .takeaway p, .technical-analysis-summary-pro .takeaway ul { margin-bottom: 0.5em; font-size: 0.9rem;}
            .technical-analysis-summary-pro .takeaway strong { color: #34495e; }
            .technical-analysis-summary-pro .takeaway i { margin-right: 8px; color: #10ac84; width: 1.2em; text-align: center;}
            .technical-analysis-summary-pro .verdict-grid { display: grid; gap: 0.75em; margin: 1em 0; }
            .technical-analysis-summary-pro .verdict-item { background-color: #eef5f9; padding: 0.8em 1.2em; border-radius: 4px; border-left: 4px solid #5dade2; font-size: 0.9rem;}
            .technical-analysis-summary-pro .bottom-line { font-weight: 500; background-color: #fdf2f2; border-left: 4px solid #e74c3c; padding: 1em; margin-top: 1.5em; border-radius: 4px;}
        </style>
        </style>
        """
        return style + html_output
    except Exception as e:
        # Using your existing error handler for consistency
        return _generate_error_html("Technical Analysis Summary", str(e))

def generate_historical_performance_html(ticker, rdata):
    """
    Generates the Historical Performance section, ensuring the narrative and table
    both reflect the same recent time period (last 15 days).
    """
    try:
        historical_df = rdata.get('historical_data')
        if historical_df is None or historical_df.empty:
            return _generate_error_html("Historical Performance", "Historical data is not available.")

        # --- FIX: All calculations are now done on the RECENT data ---
        # First, select the last 15 days of data
        recent_data = historical_df.tail(15).copy()

        # Ensure the date column is in datetime format for calculations
        if 'Date' not in recent_data.columns:
            recent_data['Date'] = pd.to_datetime(recent_data.index)
        else:
            recent_data['Date'] = pd.to_datetime(recent_data['Date'])

        # Calculate key metrics ONLY on the recent_data DataFrame
        end_price = recent_data['Close'].iloc[-1]
        start_price = recent_data['Close'].iloc[0]
        period_return = ((end_price - start_price) / start_price) if start_price != 0 else 0
        max_price = recent_data['High'].max()
        min_price = recent_data['Low'].min()
        avg_volume = recent_data['Volume'].mean()
        start_date = recent_data['Date'].min()
        end_date = recent_data['Date'].max()
        # --- END OF FIX ---

        # HTML Table Generation (uses the same recent_data)
        table_html = ""
        table_html += '<div class="table-container"><h4>Recent Trading Data</h4><table class="metrics-table"><thead>'
        table_html += '<tr><th>Date</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume</th></tr></thead><tbody>'

        for index, row in recent_data.iloc[::-1].iterrows():
            date_fmt = row['Date'].strftime('%Y-%m-%d')
            open_fmt = format_html_value(row.get('Open'), 'currency', ticker=ticker)
            high_fmt = format_html_value(row.get('High'), 'currency', ticker=ticker)
            low_fmt = format_html_value(row.get('Low'), 'currency', ticker=ticker)
            close_fmt = format_html_value(row.get('Close'), 'currency', ticker=ticker)
            volume_fmt = f"{int(row.get('Volume', 0)):,}"
            table_html += f'<tr><td>{date_fmt}</td><td>{open_fmt}</td><td>{high_fmt}</td><td>{low_fmt}</td><td>{close_fmt}</td><td>{volume_fmt}</td></tr>'

        table_html += '</tbody></table></div>'

        # Narrative Generation (now uses the corrected, recent metrics)
        date_range_str = f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"
        narrative_options = [
            (f"In the recent trading period from {date_range_str}, {ticker}'s stock price achieved a total return of <strong>{period_return:+.2%}</strong>. "
             f"The price fluctuated between a high of {format_html_value(max_price, 'currency', ticker=ticker)} and a low of {format_html_value(min_price, 'currency', ticker=ticker)}. "
             f"Average daily trading volume was approximately {avg_volume:,.0f} shares."),
            (f"Analyzing the last 15 trading days from {date_range_str}, {ticker} saw its stock post a return of <strong>{period_return:+.2%}</strong>. "
             f"The recent trading range was between {format_html_value(min_price, 'currency', ticker=ticker)} and {format_html_value(max_price, 'currency', ticker=ticker)}, with "
             f"an average volume of {avg_volume:,.0f} shares traded daily.")
        ]
        narrative = f'<div class="narrative"><p>{random.choice(narrative_options)}</p></div>'


        # Final Assembly: Narrative, then Table, then Chart
        return f'{narrative}{table_html}'

    except Exception as e:
        logging.error(f"Error in generating historical performance for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Historical Performance", str(e))

def generate_recent_news_html(ticker, rdata):
    """Generates the Recent News section."""
    try:
        news_list = rdata.get('news_list', []) 
        if not isinstance(news_list, list):
             news_list = []
             logging.warning("news_list data is not a list, cannot display news.")

        if not news_list:
            return "<p>No recent news headlines available for this stock.</p>"

        items_html = ""
        for item in news_list:
            if isinstance(item, dict):
                title = item.get('title', 'N/A')
                publisher = item.get('publisher', 'N/A')
                link = item.get('link', '#')
                published_fmt = format_html_value(item.get('published'), 'date') 

                items_html += f"""
                <div class="news-item">
                    <h4><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h4>
                    <div class="news-meta">
                        <span>Publisher: {publisher}</span>
                        <span>Published: {published_fmt}</span>
                    </div>
                </div>
                """
        
        narrative_options = [
            f"Staying updated on recent news is important for understanding potential catalysts affecting {ticker}.",
            f"Recent headlines related to {ticker} can offer insights into current events and sentiment.",
            f"Below are some recent news items concerning {ticker}."
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div><div class="news-container">{items_html}</div>'
    except Exception as e:
        return _generate_error_html("Recent News", str(e))

def generate_faq_html(ticker, rdata):
    """
    Generates an expanded FAQ section, preserving original questions
    and adding new, data-driven ones.
    """
    try:
        # --- START: ORIGINAL DATA EXTRACTION (UNCHANGED) ---
        current_price = _safe_float(rdata.get('current_price'))
        forecast_1y = _safe_float(rdata.get('forecast_1y'))
        overall_pct_change = _safe_float(rdata.get('overall_pct_change'), default=0.0)
        sentiment = rdata.get('sentiment', 'Neutral')
        volatility = _safe_float(rdata.get('volatility'))
        valuation_data = rdata.get('valuation_data', {})
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        risk_items = rdata.get('risk_items', [])
        if not isinstance(valuation_data, dict): valuation_data = {}
        if not isinstance(detailed_ta_data, dict): detailed_ta_data = {}
        # --- END: ORIGINAL DATA EXTRACTION ---

        # --- START: NEW DATA EXTRACTION FOR ADDITIONAL FAQS ---
        financial_data = rdata.get('financial_health_data', {})
        share_stats_data = rdata.get('share_statistics_data', {})
        dividend_data = rdata.get('dividends_data', {})
        tech_summary_data = rdata.get('technical_analysis_data', {}) # Using the more detailed tech summary
        
        earnings_date = valuation_data.get('Next Earnings Date')
        ex_div_date = dividend_data.get('Ex-Dividend Date')
        current_ratio = _safe_float(financial_data.get('Current Ratio (MRQ)'))
        op_cash_flow = financial_data.get('Operating Cash Flow (TTM)')
        levered_fcf = financial_data.get('Levered Free Cash Flow (TTM)')
        institutional_ownership = _safe_float(share_stats_data.get('Institutional Ownership'))
        short_percent_float = _safe_float(share_stats_data.get('Short % of Float'))
        # --- END: NEW DATA EXTRACTION ---

        latest_rsi = _safe_float(detailed_ta_data.get('RSI_14'))
        current_price_fmt = format_html_value(current_price, 'currency')
        forecast_1y_fmt = format_html_value(forecast_1y, 'currency')

        faq_items = []
        
        # --- START: ORIGINAL FAQ LOGIC (QUESTIONS 1-5, UNCHANGED) ---
        up_down_neutral_options = {
             'up_strong': ["increase significantly", "show strong gains"], 'up_mod': ["increase moderately", "see modest gains"],
             'down_strong': ["decrease significantly", "experience sharp losses"], 'down_mod': ["decrease moderately", "see modest losses"],
             'flat': ["remain relatively stable", "trade sideways"]
        }
        if overall_pct_change > 10: up_down_neutral = random.choice(up_down_neutral_options['up_strong'])
        elif overall_pct_change > 1: up_down_neutral = random.choice(up_down_neutral_options['up_mod'])
        elif overall_pct_change < -10: up_down_neutral = random.choice(up_down_neutral_options['down_strong'])
        elif overall_pct_change < -1: up_down_neutral = random.choice(up_down_neutral_options['down_mod'])
        else: up_down_neutral = random.choice(up_down_neutral_options['flat'])

        risk_count = 0
        if isinstance(risk_items, list):
              risk_count = len([r for r in risk_items if isinstance(r, str) and not any(keyword in r for keyword in ['Market Risk', 'Sector/Industry', 'Economic Risk', 'Company-Specific'])])
        risk_mention_options = [f"However, note that {risk_count} potentially significant risk factor(s) specific to {ticker} were identified (see Risk Factors section)." if risk_count > 0 else "Standard market and sector risks always apply."]
        risk_mention = random.choice(risk_mention_options)

        q1_ans_options = [f"Based on current models, the average 1-year price forecast for {ticker} is ≈<strong>{forecast_1y_fmt}</strong>. This represents a potential {overall_pct_change:+.1f}% change from the recent price of {current_price_fmt}. Remember, this is a model-driven estimate, not a guarantee, and actual prices will fluctuate based on numerous factors."]
        faq_items.append((f"What is the {ticker} stock price prediction for the next year (2025-2026)?", random.choice(q1_ans_options)))

        sentiment_str = str(sentiment)
        q2_ans_options = [f"The 1-year forecast model suggests the price might <strong>{up_down_neutral}</strong> on average ({overall_pct_change:+.1f}% potential). However, the short-term direction is highly uncertain and heavily influenced by prevailing market sentiment (currently '{sentiment_str}'), breaking news, and overall economic conditions. Technical indicators (see TA Summary) provide clues for near-term direction."]
        faq_items.append((f"Will {ticker} stock go up or down?", random.choice(q2_ans_options)))

        rsi_condition = ""; rsi_level = "neutral"; rsi_suggestion = ""
        if latest_rsi is not None:
              rsi_level_text = f"RSI: {latest_rsi:.1f}"
              if latest_rsi < 30: rsi_level = "oversold"; rsi_suggestion = random.choice(["potentially indicating a rebound opportunity"])
              elif latest_rsi > 70: rsi_level = "overbought"; rsi_suggestion = random.choice(["suggesting caution or potential for a pullback"])
              else: rsi_level = "neutral"; rsi_suggestion = random.choice(["indicating balanced momentum"])
              rsi_condition_options = [f"Technically, the RSI indicates {rsi_level} conditions ({rsi_level_text}), {rsi_suggestion}."]
              rsi_condition = random.choice(rsi_condition_options)
        disclaimer_options = ["This report is informational; consult a financial advisor before investing."]
        disclaimer = random.choice(disclaimer_options)
        
        q3_ans_options = [
            (f"Determining if {ticker} is a 'good buy' requires evaluating multiple factors. Technical sentiment is '{sentiment_str}', while the 1-year forecast suggests {overall_pct_change:+.1f}% potential. {rsi_condition} "
             f"Consider the valuation, financial health, growth prospects, and {risk_mention} Align these factors with your personal investment strategy and risk tolerance. {disclaimer}"),
            (f"Whether {ticker} is a 'good buy' now involves balancing various elements: '{sentiment_str}' technicals, a {overall_pct_change:+.1f}% forecast potential, and {rsi_condition} "
             f"Weigh the company's valuation, stability, growth, and {risk_mention} Against your own investment goals and risk profile. {disclaimer}")
        ]
        q3_ans = random.choice(q3_ans_options)
        faq_items.append((f"Is {ticker} stock a good investment right now?", q3_ans))

        vol_level = "N/A"; vol_comp = ""
        volatility_fmt = format_html_value(volatility, 'percent_direct', 1)
        if volatility is not None:
            if volatility > 40: vol_level = random.choice(["high", "elevated"])
            elif volatility > 20: vol_level = random.choice(["moderate", "average"])
            else: vol_level = random.choice(["low", "subdued"])
            beta_fmt = format_html_value(rdata.get('stock_price_stats_data',{}).get('Beta'), 'ratio')
            if beta_fmt != 'N/A': vol_comp_options = [f"This aligns with its Beta of {beta_fmt} (see Stock Price Statistics)."]; vol_comp = random.choice(vol_comp_options)
        q4_ans_options = [f"Based on the recent 30-day price action, {ticker}'s annualized volatility is ≈<strong>{volatility_fmt}</strong>. This level is currently considered {vol_level}, indicating the degree of recent price fluctuation. {vol_comp} Higher volatility means larger potential price swings (both up and down)."]
        faq_items.append((f"How volatile is {ticker} stock?", random.choice(q4_ans_options)))

        pe_ratio_fmt = format_html_value(valuation_data.get('Trailing P/E'), 'ratio')
        fwd_pe_fmt = format_html_value(valuation_data.get('Forward P/E'), 'ratio')
        pe_comment = "unavailable"; pe_context = random.choice(["Compare to industry peers and historical levels."])
        pe_ratio_val = _safe_float(valuation_data.get('Trailing P/E'))
        if pe_ratio_val is not None:
              if pe_ratio_val <= 0: pe_comment = random.choice(["negative (indicating loss or requires context)"])
              elif pe_ratio_val < 15: pe_comment = random.choice(["relatively low (suggesting potential value or low growth expectations)"])
              elif pe_ratio_val < 25: pe_comment = random.choice(["moderate"])
              else: pe_comment = random.choice(["relatively high (implying market expects strong growth or potential overvaluation)"])
        q5_ans_options = [f"{ticker}'s Trailing P/E ratio (based on past earnings) is <strong>{pe_ratio_fmt}</strong>, which is considered {pe_comment}. The Forward P/E (based on expected earnings) is {fwd_pe_fmt}. A P/E ratio indicates how much investors are paying per dollar of earnings. {pe_context} A high P/E isn't necessarily bad if strong growth justifies it (check the PEG ratio in Valuation Metrics)."]
        faq_items.append((f"What is {ticker}'s P/E ratio and what does it mean?", random.choice(q5_ans_options)))
        # --- END: ORIGINAL FAQ LOGIC ---

        # --- START: NEW ADDITIONAL FAQS ---
        # FAQ 6: Key Events
        q6_answer = "Key upcoming events include "
        events = []
        if earnings_date and earnings_date != 'N/A':
            events.append(f"the next earnings report on <strong>{format_html_value(earnings_date, 'date')}</strong>")
        if ex_div_date and ex_div_date != 'N/A':
            events.append(f"the ex-dividend date on <strong>{format_html_value(ex_div_date, 'date')}</strong> for income investors")
        
        if events:
            q6_answer += ", ".join(events) + ". "
        q6_answer += "Beyond these, analysts should monitor macroeconomic shifts, competitive actions, and major corporate announcements."
        faq_items.append((f"What are the key upcoming events for {ticker}?", q6_answer))

        # FAQ 7: Liquidity Position
        if current_ratio is not None and op_cash_flow is not None:
            liquidity_analysis = f"an adequate Current Ratio of <strong>{current_ratio:.2f}x</strong>."
            if current_ratio < 1.0:
                liquidity_analysis = f"a Current Ratio of <strong>{current_ratio:.2f}x</strong>, which is below 1.0 and suggests potential short-term liquidity challenges."
            elif current_ratio > 1.5:
                liquidity_analysis = f"a strong Current Ratio of <strong>{current_ratio:.2f}x</strong>, suggesting it can comfortably cover its short-term liabilities."
            
            q7_answer = f"{ticker}'s financial health includes {liquidity_analysis} However, its robust operating cash flow (<strong>{op_cash_flow}</strong>) and levered free cash flow (<strong>{levered_fcf}</strong>) provide a significant buffer and are critical factors in its ability to fund operations and debt."
            faq_items.append((f"What does {ticker}'s liquidity position reveal about its financial health?", q7_answer))

        # FAQ 8: Institutional Ownership
        if institutional_ownership is not None and short_percent_float is not None:
            ownership_level = "moderate"
            if institutional_ownership > 70: ownership_level = "high"
            elif institutional_ownership < 40: ownership_level = "low"
            
            short_sentiment = "minimal bearish sentiment"
            if short_percent_float > 10: short_sentiment = "significant bearish sentiment"
            elif short_percent_float > 3: short_sentiment = "notable bearish sentiment"
            
            q8_answer = f"Institutional ownership is <strong>{ownership_level} at {institutional_ownership:.2f}%</strong>. This level of ownership by large funds can provide price stability and implies professional confidence in the company. The short interest is <strong>{short_percent_float:.2f}%</strong> of float, suggesting {short_sentiment} from market participants."
            faq_items.append((f"How does {ticker}'s institutional ownership impact its stock?", q8_answer))
        
        # --- END: NEW ADDITIONAL FAQS ---
        
        # This final part remains unchanged, it just processes a longer list now
        details_html = "".join([f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq_items])
        return f'<div class="faq-section">{details_html}</div>' # Added a wrapper div
    except Exception as e:
        return _generate_error_html("FAQ", str(e))


def generate_risk_factors_html(ticker, rdata):
    """Generates the enhanced Risk Factors section."""
    try:
        risk_items = rdata.get('risk_items', []) 
        industry = rdata.get('industry', 'the company\'s specific')
        sector = rdata.get('sector', 'its')

        generic_risks_map = {
            "Market Risk": ["Overall market fluctuations can impact the stock."],
            "Sector/Industry Risk": [f"Factors specific to the {industry} industry or {sector} sector can affect performance."],
            "Economic Risk": ["Changes in macroeconomic conditions (interest rates, inflation) pose risks."],
            "Company-Specific Risk": ["Unforeseen company events or news can impact the price."]
        }
        processed_risk_items = []
        if isinstance(risk_items, list):
            for item in risk_items:
                item_str = str(item)
                processed = False
                for generic_key, risk_variations in generic_risks_map.items():
                    if item_str.startswith(generic_key) or generic_key in item_str:
                        processed_risk_items.append(random.choice(risk_variations))
                        processed = True
                        break
                if not processed:
                    processed_risk_items.append(item_str)
        else:
             logging.warning("risk_items is not a list, cannot process risks.")

        risk_list_html = "".join([f"<li>{get_icon('warning')} {item}</li>" for item in processed_risk_items])
        
        narrative_options = [
            f"<p>Investing in {ticker} involves various risks. This section outlines potential factors identified through data analysis and general market considerations. It is not exhaustive.</p>",
            f"<p>Potential investors in {ticker} should be aware of several risk factors. The following list highlights key considerations based on data and market dynamics, but may not include all possible risks.</p>"
        ]
        narrative = f'<div class="narrative">{random.choice(narrative_options)}</div>'
        return narrative + f"<ul>{risk_list_html}</ul>"
    except Exception as e:
        return _generate_error_html("Risk Factors", str(e))

def generate_report_info_disclaimer_html(generation_time):
    """Generates the final disclaimer and timestamp section."""
    try:
        if not isinstance(generation_time, datetime):
            logging.warning(f"Invalid generation_time type: {type(generation_time)}. Using current time.")
            generation_time = datetime.now()
        time_str = f"{generation_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    except ValueError: 
         time_str = f"{generation_time.strftime('%Y-%m-%d %H:%M:%S')} (Timezone N/A)"
    except Exception as e: 
         logging.error(f"Error formatting generation_time: {e}")
         time_str = "Error retrieving generation time."

    current_date_str = datetime.now().strftime('%Y-%m-%d')

    gen_on = random.choice(["Report Generated On:", "Analysis Compiled:", "Data As Of (Generation Time):"])
    curr_date = random.choice(["Current Date Context:", "Report Date:", "Date of Viewing:"])
    sources = random.choice(["Primary Data Sources:", "Data Primarily Sourced From:", "Key Data Inputs:"])
    limits = random.choice(["Known Limitations:", "Important Caveats:", "Data Constraints:"])
    disclaimer_title = random.choice(["IMPORTANT DISCLAIMER:", "CRITICAL NOTICE:", "ESSENTIAL DISCLAIMER:"])
    disclaimer_body1 = random.choice(["This report is automatically generated for informational and educational purposes ONLY. It does NOT constitute financial, investment, trading, legal, or tax advice, nor should it be interpreted as a recommendation or solicitation to buy, sell, hold, or otherwise transact in any security mentioned."])
    disclaimer_body2 = random.choice(["All investments carry risk, including the potential loss of principal. Past performance is not indicative or predictive of future results. Market conditions are dynamic and can change rapidly. Financial models and data sources may contain errors or inaccuracies."])
    disclaimer_body3 = random.choice(["Readers are strongly urged to conduct their own thorough and independent due diligence. Consult with one or more qualified, licensed financial professionals, investment advisors, and/or tax advisors before making any investment decisions. Understand your own risk tolerance, financial situation, and investment objectives."])
    disclaimer_body4 = random.choice(["The creators, generators, and distributors of this report assume NO liability whatsoever for any actions taken, decisions made, or interpretations drawn based on the information provided herein. Use this information entirely at your own risk."])

    return f"""
         <div class="general-info">
             <p><strong>{gen_on}</strong> {time_str}</p>
             <p><strong>{curr_date}</strong> {current_date_str}</p>
             <p><strong>{sources}</strong> Yahoo Finance API (via yfinance), potentially supplemented by FRED Economic Data.</p>
             <p><strong>{limits}</strong> Financial data may have reporting lags. Technical indicators are inherently backward-looking. Forecasts are probabilistic model outputs, not certainties, and subject to significant error ranges and changing assumptions.</p>
         </div>
         <div class="disclaimer">
             <p><strong>{disclaimer_title}</strong> {disclaimer_body1}</p>
             <p>{disclaimer_body2}</p>
             <p>{disclaimer_body3}</p>
             <p>{disclaimer_body4}</p>
         </div>
    """