import pandas as pd
import numpy as np
import re
from datetime import datetime
import random # Used for slight text variations to ensure uniqueness
import logging # Import logging for better error tracking

# Setup basic logging - logs errors and warnings
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

def format_html_value(value, format_type="number", precision=2, currency='$'):
    """Safely formats values for HTML display with enhanced error handling."""
    original_value_repr = repr(value) # For logging
    # print(f"DEBUG: format_html_value called with currency={currency}, format_type={format_type}, value={original_value_repr}") # Kept for your debugging if needed
    
    if value is None or value == "N/A" or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        if isinstance(value, str) and value.startswith(currency) and format_type != "string":
             if re.match(r'^[$₹€£¥][0-9,.]+[ KMBT]?$', value):
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
            if currency == '₹':
                formatted = f"{num_value:,.{precision}f}"
                parts = formatted.split('.')
                whole = parts[0].replace(',', '')
                whole_formatted_indian = ','.join([whole[-3:]] + [whole[i:i+2] for i in range(len(whole)-3, 0, -2)][::-1])
                result = f"{currency}{whole_formatted_indian}{'.' + parts[1] if len(parts) > 1 else ''}"
                # print(f"DEBUG: Formatted Indian currency value: {result}")
                return result
            result = f"{currency}{num_value:,.{precision}f}"
            # print(f"DEBUG: Formatted currency value: {result}")
            return result
        elif format_type == "percent": return f"{num_value * 100:.{precision}f}%"
        elif format_type == "percent_direct": return f"{num_value:.{precision}f}%"
        elif format_type == "ratio": return f"{num_value:.{precision}f}x"
        elif format_type == "large_number":
            if abs(num_value) >= 1e12: return f"{currency}{num_value/1e12:.{precision}f}T"
            elif abs(num_value) >= 1e9: return f"{currency}{num_value/1e9:.{precision}f}B"
            elif abs(num_value) >= 1e6: return f"{currency}{num_value/1e6:.{precision}f}M"
            elif abs(num_value) >= 1e3: return f"{currency}{num_value/1e3:.{precision}f}K"
            else: return f"{currency}{num_value:,.{precision}f}"
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
        currency_symbol = rdata.get('currency_symbol', '$')

        company_name = profile_data.get('Company Name', ticker)
        industry = profile_data.get('Industry', 'its')
        market_cap_fmt = profile_data.get('Market Cap', 'N/A')

        current_price_val = rdata.get('current_price')
        current_price_fmt = format_html_value(current_price_val, 'currency', currency=currency_symbol)

        last_date_obj = rdata.get('last_date', datetime.now())
        last_date_fmt = last_date_obj.strftime('%B %Y')

        sma50_val = detailed_ta_data.get('SMA_50')
        sma50_fmt = format_html_value(sma50_val, 'currency', currency=currency_symbol)
        sma200_val = detailed_ta_data.get('SMA_200')
        sma200_fmt = format_html_value(sma200_val, 'currency', currency=currency_symbol)
        
        analyst_target_val = _safe_float(analyst_data.get('Mean Target Price')) # Use _safe_float for calculations
        analyst_target_fmt = format_html_value(analyst_target_val, 'currency', currency=currency_symbol)
        
        upside_pct_val = rdata.get('overall_pct_change', 0.0)
        upside_pct_fmt = f"{upside_pct_val:+.1f}%"
        
        volatility_val = rdata.get('volatility')
        volatility_fmt = format_html_value(volatility_val, 'percent_direct', 1)

        rev_growth_val = _safe_float(profit_data.get('Revenue Growth (YoY)'))
        rev_growth_fmt = format_html_value(rev_growth_val, 'percent')
        
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
                negative_fundamental = f"a recent contraction in earnings (down {format_html_value(earnings_growth_val, 'percent')} YoY)"
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
        introduction_html = f"""
        <p>This report provides a detailed analysis of <strong>{company_name} ({ticker})</strong>, a {market_cap_fmt} company operating in the {industry} industry. The core question for investors is whether the current stock price represents a fair value and if the company is positioned for future growth.</p>
        
        <h3>Here’s What You Need to Know Right Now</h3>
        <p>The stock is sitting at <strong>{current_price_fmt}</strong> (as of {last_date_fmt}), and it’s {momentum_text}.</p>
        <p>{analyst_outlook_text}. However, there’s significant volatility here (<strong>{volatility_fmt} annualized</strong>), suggesting the potential for wide price swings.</p>
        <p>{company_name}’s fundamental story is nuanced. {fundamental_story_text}</p>
        
        <h3>What’s Inside This Analysis?</h3>
        <p>We’re not just throwing numbers at you—we’re breaking down {ticker}’s stock from every angle so you can make an informed decision:</p>
        <ul>
            <li>✅ <strong>Is now a good time to buy?</strong><br>
            Technicals say "{technical_verdict}" (but RSI is {rsi_condition} at {rsi_fmt}).<br>
            Fundamentals say "{fundamental_verdict}" (driven by debt levels and growth metrics).</li>
            
            <li>✅ <strong>Can its core operations drive future growth?</strong><br>
            Future growth will likely depend on performance in its core {industry} operations and ability to manage competitive pressures.</li>
            
            <li>✅ <strong>What are the biggest risks?</strong><br>
            The company carries {total_debt_fmt} in debt, which could be a headwind in a high-interest-rate environment.<br>
            Competition is fierce from both established players and new entrants.</li>
        </ul>
        
        <p>Most stock analyses either use hard-to-understand jargon or say something too simple like “just buy” and trust the outcome. This is not what’s happening. We’re here with clear information that benefits you, no matter if you invest for long-term results or try for fast profits.</p>
        <p>All in all, is {company_name} the right investment to make sure your money tells a story of success and satisfaction? Or are there underlying issues to be wary of? Stick around as we get to the details in the data.</p>
        """

        return introduction_html

    except Exception as e:
        # Fallback to generate a standard error message
        return _generate_error_html("Introduction", str(e))


def generate_metrics_summary_html(ticker, rdata):
    """Generates the key metrics summary box with context."""
    try:
        current_price = rdata.get('current_price')
        sma50 = rdata.get('sma_50')
        sma200 = rdata.get('sma_200')
        volatility = rdata.get('volatility') 
        sentiment = rdata.get('sentiment', 'Neutral') 
        forecast_1y = rdata.get('forecast_1y')
        overall_pct_change_val = _safe_float(rdata.get('overall_pct_change'), default=0.0)
        period_label = rdata.get('period_label', 'Period')
        forecast_1m = rdata.get('forecast_1m') 
        currency_symbol = rdata.get('currency_symbol', '$')

        current_price_fmt = format_html_value(current_price, 'currency', currency=currency_symbol)
        forecast_1m_fmt = format_html_value(forecast_1m, 'currency', currency=currency_symbol)
        forecast_1y_fmt = format_html_value(forecast_1y, 'currency', currency=currency_symbol)
        overall_pct_change_fmt = f"{overall_pct_change_val:+.1f}%"
        volatility_fmt = format_html_value(volatility, 'percent_direct', 1)
        sma50_fmt = format_html_value(sma50, 'currency', currency=currency_symbol)
        sma200_fmt = format_html_value(sma200, 'currency', currency=currency_symbol)

        forecast_1y_icon = get_icon('up' if overall_pct_change_val > 1 else ('down' if overall_pct_change_val < -1 else 'neutral'))

        price_f = _safe_float(current_price)
        sma50_f = _safe_float(sma50)
        sma200_f = _safe_float(sma200)

        sma50_comp_icon = get_icon('neutral')
        price_vs_sma50_text = "vs SMA 50"
        if price_f is not None and sma50_f is not None:
            if price_f > sma50_f * 1.001: sma50_comp_icon = get_icon('up'); price_vs_sma50_text = "Above SMA 50"
            elif price_f < sma50_f * 0.999: sma50_comp_icon = get_icon('down'); price_vs_sma50_text = "Below SMA 50"
            else: price_vs_sma50_text = "At SMA 50"

        sma200_comp_icon = get_icon('neutral')
        price_vs_sma200_text = "vs SMA 200"
        if price_f is not None and sma200_f is not None:
            if price_f > sma200_f * 1.001: sma200_comp_icon = get_icon('up'); price_vs_sma200_text = "Above SMA 200"
            elif price_f < sma200_f * 0.999: sma200_comp_icon = get_icon('down'); price_vs_sma200_text = "Below SMA 200"
            else: price_vs_sma200_text = "At SMA 200"

        sentiment_str = str(sentiment) 
        sentiment_icon = get_icon('up' if 'Bullish' in sentiment_str else ('down' if 'Bearish' in sentiment_str else 'neutral'))

        grid_html = f"""
        <div class="metrics-summary">
            <div class="metric-item"><span class="metric-label">Current Price</span><span class="metric-value">{current_price_fmt}</span></div>
            <div class="metric-item"><span class="metric-label">1-{period_label} Forecast</span><span class="metric-value">{forecast_1m_fmt}</span></div>
            <div class="metric-item"><span class="metric-label">1-Year Forecast</span><span class="metric-value">{forecast_1y_fmt} <span class="metric-change {('trend-up' if overall_pct_change_val > 0 else 'trend-down' if overall_pct_change_val < 0 else 'trend-neutral')}">({overall_pct_change_fmt})</span> {forecast_1y_icon}</span></div>
            <div class="metric-item"><span class="metric-label">Technical Sentiment</span><span class="metric-value sentiment-{sentiment_str.lower().replace(' ', '-')}">{sentiment_icon} {sentiment_str}</span></div>
            <div class="metric-item"><span class="metric-label">Volatility (30d Ann.)</span><span class="metric-value">{volatility_fmt} {get_icon('stats')}</span></div>
            <div class="metric-item"><span class="metric-label">{price_vs_sma50_text}</span><span class="metric-value">{sma50_fmt} {sma50_comp_icon}</span></div>
            <div class="metric-item"><span class="metric-label">{price_vs_sma200_text}</span><span class="metric-value">{sma200_fmt} {sma200_comp_icon}</span></div>
            """
        green_days = _safe_float(rdata.get('green_days')); total_days = _safe_float(rdata.get('total_days'))
        if green_days is not None and total_days is not None and total_days > 0:
             green_days_pct = green_days / total_days * 100
             green_icon = get_icon('up' if green_days_pct > 55 else ('down' if green_days_pct < 45 else 'neutral'))
             green_days_fmt = f"{int(green_days)}/{int(total_days)} ({green_days_pct:.0f}%)"
             grid_html += f'<div class="metric-item"><span class="metric-label">Green Days (30d)</span><span class="metric-value">{green_days_fmt} {green_icon}</span></div>'
        grid_html += "</div>"

        # Default Narrative
        phrase_default_intro = random.choice([
            f"This snapshot summarizes {ticker}'s current position.",
            f"Here's a quick overview of {ticker}'s key metrics.",
            f"The following data points provide a summary of {ticker}'s current status."
        ])
        phrase_default_forecast = random.choice([
             f"The stock trades at {current_price_fmt}, with models forecasting a 1-year average target near {forecast_1y_fmt} ({overall_pct_change_fmt}).",
             f"Currently priced at {current_price_fmt}, {ticker} has a model-based 1-year forecast around {forecast_1y_fmt} (a {overall_pct_change_fmt} potential change).",
             f"With a price of {current_price_fmt}, the 1-year projection aims for approximately {forecast_1y_fmt} ({overall_pct_change_fmt})."
        ])
        phrase_default_tech = random.choice([
            f"Technical indicators currently reflect a {sentiment_str} sentiment ({price_vs_sma50_text} / {price_vs_sma200_text}).",
            f"The technical picture shows a {sentiment_str} bias ({price_vs_sma50_text}, {price_vs_sma200_text}).",
            f"Sentiment derived from technicals is {sentiment_str} ({price_vs_sma50_text} / {price_vs_sma200_text})."
        ])
        phrase_default_vol = random.choice([
            f"Recent volatility ({volatility_fmt}) quantifies price fluctuations.",
            f"Price swing intensity is measured by volatility at {volatility_fmt}.",
            f"The stock's recent volatility stands at {volatility_fmt}."
        ])
        phrase_default_outro = random.choice([
            "The following sections provide deeper analysis into the underlying technicals and fundamentals.",
            "Further details on the technical and fundamental aspects are explored below.",
            "We delve into more specific technical and fundamental analysis in the subsequent sections."
        ])
        narrative = f"{phrase_default_intro} {phrase_default_forecast} {phrase_default_tech} {phrase_default_vol} {phrase_default_outro}"

        return grid_html + f'<div class="narrative"><p>{narrative}</p></div>'
    except Exception as e:
        return _generate_error_html("Metrics Summary", str(e))


def generate_metrics_section_content(metrics):
    """Helper to generate table body content for metrics sections (Robust NA handling)."""
    rows = ""
    try:
        if isinstance(metrics, dict):
            row_parts = []
            for k, v in metrics.items():
                format_type = "string" 
                k_lower = str(k).lower()
                if "date" in k_lower: format_type = "date"
                elif "yield" in k_lower or "ratio" in k_lower or "beta" in k_lower: format_type = "ratio"
                elif "margin" in k_lower or "ownership" in k_lower or "growth" in k_lower or "%" in k_lower: format_type = "percent_direct"
                elif "price" in k_lower or "value" in k_lower or "dividend rate" in k_lower: format_type = "currency"
                elif "volume" in k_lower or "shares" in k_lower or "employees" in k_lower: format_type = "integer"
                elif "market cap" in k_lower: format_type = "large_number"

                formatted_v = format_html_value(v, format_type)
                if formatted_v != "N/A":
                    row_parts.append(f"<tr><td>{str(k)}</td><td>{formatted_v}</td></tr>") 

            rows = "".join(row_parts)

        if not rows:
            rows = "<tr><td colspan='2' style='text-align: center; font-style: italic;'>No displayable data available for this category.</td></tr>"

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
    """Generates Total Valuation section with a default narrative focus."""
    try:
        valuation_data = rdata.get('total_valuation_data')
        if not isinstance(valuation_data, dict):
            valuation_data = {}
            logging.warning("total_valuation_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(valuation_data)

        ev_ttm = format_html_value(valuation_data.get('Enterprise Value (EV TTM)'), 'large_number', currency=rdata.get('currency_symbol', '$'))
        ev_rev = format_html_value(valuation_data.get('EV/Revenue (TTM)'), 'ratio')
        ev_ebitda = format_html_value(valuation_data.get('EV/EBITDA (TTM)'), 'ratio')
        next_earn_date = format_html_value(valuation_data.get('Next Earnings Date'), 'date')
        ex_div_date = format_html_value(valuation_data.get('Ex-Dividend Date'), 'date')

        ev_explanation_options = [
            f"Enterprise Value (EV) of <strong>{ev_ttm}</strong> provides a more comprehensive measure of {ticker}'s total worth than market cap alone, as it incorporates debt and cash.",
            f"Looking beyond market cap, the Enterprise Value (EV), currently <strong>{ev_ttm}</strong>, offers a broader view of {ticker}'s value by including debt and cash.",
            f"At <strong>{ev_ttm}</strong>, the Enterprise Value (EV) presents a fuller picture of {ticker}'s aggregate value, accounting for both equity and net debt."
        ]
        ev_explanation = random.choice(ev_explanation_options)

        ratio_explanation_options = [
            f"The EV/Revenue ratio ({ev_rev}) compares this total value to sales, while EV/EBITDA ({ev_ebitda}) relates it to operating profitability before interest, taxes, depreciation, and amortization.",
            f"Relating this EV to performance, the EV/Revenue multiple stands at {ev_rev}, and the EV/EBITDA multiple is {ev_ebitda}, gauging value against sales and core operational earnings respectively.",
            f"Key ratios derived from EV include EV/Revenue ({ev_rev}) and EV/EBITDA ({ev_ebitda}), which assess valuation relative to top-line revenue and operating profit (pre-deductions)."
        ]
        ratio_explanation = random.choice(ratio_explanation_options)
        
        # Default Narrative
        narrative_options = [
             (
                 f"Total valuation metrics offer a broader perspective beyond market capitalization. {ev_explanation} {ratio_explanation} "
                 f"These ratios help assess the company's valuation relative to its sales and operating earnings. Key upcoming dates include the next earnings announcement (Est: {next_earn_date}) and the ex-dividend date ({ex_div_date})."
             ),
             (
                f"Moving beyond simple market cap, total valuation metrics provide deeper insight. {ev_explanation} {ratio_explanation} "
                f"These figures help evaluate {ticker}'s price relative to its business scale and operational results. Note the upcoming earnings (Est: {next_earn_date}) and ex-dividend ({ex_div_date}) dates."
             )
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
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
        currency_symbol = rdata.get('currency_symbol', '$')
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
            sr_text = f"~{format_html_value(support,'currency', currency=currency_symbol)} / ~{format_html_value(resistance,'currency', currency=currency_symbol)}"
        st_points_data['sr'] = {'label': 'Support / Resistance (30d)', 'value': sr_text, 'icon': get_icon('chart')}


        forecast_icon = get_icon('neutral'); forecast_text = "N/A"
        if forecast_1y is not None:
            forecast_icon = get_icon('up' if overall_pct_change > 1 else ('down' if overall_pct_change < -1 else 'neutral'))
            forecast_text = f"~{overall_pct_change:+.1f}% avg. change to ≈{format_html_value(forecast_1y, 'currency', currency=currency_symbol)}"
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
        roe_fmt = format_html_value(roe, 'percent_direct'); de_fmt = format_html_value(debt_equity, 'ratio'); ocf_fmt = format_html_value(op_cash_flow, 'large_number', currency=currency_symbol)
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
             mean_target_fmt = format_html_value(mean_target, 'currency', currency=currency_symbol)
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
        forecast_1y_fmt = format_html_value(forecast_1y, 'currency', currency=currency_symbol)
        if overall_pct_change > 5: forecast_direction_summary = f"potential upside ({overall_pct_change:+.1f}%)"
        elif overall_pct_change < -5: forecast_direction_summary = f"potential downside ({overall_pct_change:+.1f}%)"
        
        sentiment_narrative = st_points_data.get('sentiment',{}).get('value','N/A sentiment')
        valuation_narrative = lt_points_data.get('valuation',{}).get('value','N/A valuation')

        phrase_default_synthesis_options = [
            f"{random.choice(phrase_link_tech_fund_options)} {ticker} exhibits <strong>{sentiment_narrative}</strong> technical sentiment alongside <strong>{fundamental_strength_summary.lower()}</strong> fundamental health.",
            f"Overall, {ticker} combines a technical picture leaning {sentiment_narrative} with a fundamental health assessment of {fundamental_strength_summary.lower()}.",
            f"Synthesizing the data, {ticker} currently shows {sentiment_narrative} technicals coupled with {fundamental_strength_summary.lower()} fundamentals."
        ]
        phrase_default_valuation_options = [ f"Valuation appears {valuation_narrative}.", f"The current valuation is assessed as {valuation_narrative}.", f"From a valuation standpoint, it looks {valuation_narrative}." ]
        phrase_default_forecast_summary_options = [
            f"The 1-year forecast model suggests {forecast_direction_summary} towards ≈{forecast_1y_fmt}.",
            f"Models project a 1-year path indicating {forecast_direction_summary}, targeting ≈{forecast_1y_fmt}.",
            f"Looking out one year, the forecast implies {forecast_direction_summary} with an average target near ≈{forecast_1y_fmt}."
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
        currency_symbol = rdata.get('currency_symbol', '$')
        current_price_fmt = format_html_value(current_price, 'currency', currency=currency_symbol)
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

                first_row = forecast_df.iloc[0]; last_row = forecast_df.iloc[-1]
                first_range_str = f"{format_html_value(first_row['Low'], 'currency', currency=currency_symbol)} – {format_html_value(first_row['High'], 'currency', currency=currency_symbol)}"
                last_range_str = f"{format_html_value(last_row['Low'], 'currency', currency=currency_symbol)} – {format_html_value(last_row['High'], 'currency', currency=currency_symbol)}"
                
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

                        low_fmt = format_html_value(row.get('Low'), 'currency', currency=currency_symbol)
                        avg_fmt = format_html_value(row.get('Average'), 'currency', currency=currency_symbol)
                        high_fmt = format_html_value(row.get('High'), 'currency', currency=currency_symbol)
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
            
            min_max_summary = f"""<p>Over the forecast horizon ({forecast_df[forecast_time_col].iloc[0]} to {forecast_df[forecast_time_col].iloc[-1]}), {ticker}'s price is projected by the model to fluctuate between approximately <strong>{format_html_value(min_price_overall, 'currency', currency=currency_symbol)}</strong> and <strong>{format_html_value(max_price_overall, 'currency', currency=currency_symbol)}</strong>.</p>""" if min_price_overall is not None else "<p>Overall forecast range could not be determined.</p>"
            table_html = f"""<div class="table-container"><table><thead><tr><th>{period_label} ({forecast_time_col})</th><th>Min. Price</th><th>Avg. Price</th><th>Max. Price</th><th>Potential ROI vs Current ({current_price_fmt})</th><th>Model Signal</th></tr></thead><tbody>{table_rows}</tbody></table></div>"""
        else:
            min_max_summary = f"<p>No detailed {period_label.lower()}-by-{period_label.lower()} forecast data is currently available for {ticker}.</p>"
            table_html = ""
            range_trend_comment = ""

        # Default Narrative
        min_fmt = format_html_value(min_price_overall, 'currency', currency=currency_symbol)
        max_fmt = format_html_value(max_price_overall, 'currency', currency=currency_symbol)
        range_narrative = f"{min_fmt} to {max_fmt}" if min_price_overall is not None else "an undetermined range"
        narrative_options = [
            (f"The detailed {period_label.lower()} forecast below outlines the model's expectations for {ticker}'s price evolution ({range_narrative}). It includes projected ranges (Min, Avg, Max), potential ROI based on the average projection versus the current price, and a derived model signal for each period."),
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
        if profile_data.get('Sector'): profile_items.append(f"<div class='profile-item'><span>Sector:</span>{format_html_value(profile_data['Sector'], 'string')}</div>")
        if profile_data.get('Industry'): profile_items.append(f"<div class='profile-item'><span>Industry:</span>{format_html_value(profile_data['Industry'], 'string')}</div>")
        if profile_data.get('Market Cap'): profile_items.append(f"<div class='profile-item'><span>Market Cap:</span>{format_html_value(profile_data['Market Cap'], 'large_number', currency=rdata.get('currency_symbol', '$'))}</div>")
        if profile_data.get('Employees'): profile_items.append(f"<div class='profile-item'><span>Employees:</span>{format_html_value(profile_data.get('Employees'), 'integer')}</div>")

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
    """Generates Valuation Metrics with enhanced narrative and explanations."""
    try:
        valuation_data = rdata.get('valuation_data')
        if not isinstance(valuation_data, dict):
             valuation_data = {}
             logging.warning("valuation_data not found or not a dict, using empty.")

        currency_symbol = rdata.get('currency_symbol', '$')

        # Extract and format specific valuation metrics
        forward_pe_fmt = format_html_value(valuation_data.get('Forward P/E'), 'ratio')
        forward_pe_val = _safe_float(valuation_data.get('Forward P/E'))
        peg_ratio_fmt = format_html_value(valuation_data.get('PEG Ratio'), 'ratio')
        peg_ratio_val = _safe_float(valuation_data.get('PEG Ratio'))
        trailing_pe_fmt = format_html_value(valuation_data.get('Trailing P/E'), 'ratio')
        ps_ratio_fmt = format_html_value(valuation_data.get('Price/Sales (TTM)'), 'ratio')
        pb_ratio_fmt = format_html_value(valuation_data.get('Price/Book (MRQ)'), 'ratio')
        
        # Attempt to get industry average P/E from rdata (needs to be added in report_generator.py)
        industry_avg_pe = rdata.get('industry_avg_pe') 
        industry_avg_pe_fmt = format_html_value(industry_avg_pe, 'ratio')

        # Expanded Narrative Introduction
        narrative_intro_options = [
            (
                f"<p>Understanding {ticker}'s valuation is a cornerstone of investment analysis. This section delves into key ratios "
                f"that analysts and investors use to assess whether the stock price is justified relative to its earnings, "
                f"sales, book value, or growth prospects. It's important to remember that these metrics provide a snapshot "
                f"and should ideally be compared against the company's historical levels {get_icon('history')}, its industry peers {get_icon('peer')}, and the broader market context "
                f"to derive meaningful insights. No single ratio tells the whole story, but together they can paint a compelling picture "
                f"of market perception and potential investment appeal.</p>"
            ),
            (
                f"<p>To gauge if {ticker}'s stock is fairly priced, investors often turn to valuation metrics. These ratios compare the company's stock price "
                f"to its financial performance (like earnings or sales) or its intrinsic value (like book value). This section explores these critical indicators. "
                f"Remember, a thorough analysis involves looking at these ratios in the context of {ticker}'s own past performance {get_icon('history')}, how it stacks up against competitors {get_icon('peer')}, "
                f"and the overall market sentiment. One metric alone is rarely definitive, but collectively they offer valuable clues.</p>"
            )
        ]
        html_content = f'<div class="narrative">{random.choice(narrative_intro_options)}</div>'

        # Detailed explanation for Forward P/E
        if forward_pe_fmt != "N/A":
            pe_explanation_html = f"<h4>Forward P/E Ratio: {forward_pe_fmt}</h4>"
            pe_para_options = [
                (f"<p>The Forward Price-to-Earnings (P/E) ratio of <strong>{forward_pe_fmt}</strong> indicates how much investors are "
                 f"willing to pay for each dollar of {ticker}'s anticipated earnings over the next fiscal period. "
                 f"A lower Forward P/E can sometimes suggest that the stock is undervalued relative to its future earnings potential, "
                 f"or it might reflect market expectations of slower growth. Conversely, a higher Forward P/E often implies that "
                 f"investors have high growth expectations, or that the stock is perceived as a premium quality name. ")
            ]
            pe_paragraph = random.choice(pe_para_options)
            
            if forward_pe_val is not None and industry_avg_pe is not None and industry_avg_pe_fmt != "N/A": # Check if industry_avg_pe_fmt is not N/A
                if forward_pe_val < industry_avg_pe:
                    pe_paragraph += (f"Compared to an industry average P/E of {industry_avg_pe_fmt}, {ticker}'s Forward P/E suggests it might be relatively cheaper than its peers. ")
                elif forward_pe_val > industry_avg_pe:
                    pe_paragraph += (f"When seen against an industry average P/E of {industry_avg_pe_fmt}, {ticker}'s Forward P/E indicates it might be trading at a premium. ")
            pe_paragraph += "It's a forward-looking measure, so the accuracy of the underlying earnings estimates is crucial.</p>"
            pe_explanation_html += pe_paragraph
            html_content += pe_explanation_html

        # Detailed explanation for PEG Ratio
        if peg_ratio_fmt != "N/A":
            peg_explanation_html = f"<h4>PEG Ratio: {peg_ratio_fmt}</h4>"
            peg_para_options = [
                (f"<p>The Price/Earnings-to-Growth (PEG) ratio of <strong>{peg_ratio_fmt}</strong> offers a more nuanced view by "
                 f"relating the P/E ratio to earnings growth expectations. It helps assess if the stock's P/E is justified by its anticipated growth. A common rule of thumb is that a PEG ratio around 1.0 "
                 f"suggests a fair valuation relative to expected growth. ")
            ]
            peg_paragraph = random.choice(peg_para_options)

            if peg_ratio_val is not None:
                if peg_ratio_val < 0:
                    peg_paragraph += ("A negative PEG ratio, like this one, typically arises when a company has negative earnings (a net loss) or if earnings growth expectations are negative. "
                                      "In such cases, the PEG ratio is generally not considered a meaningful indicator for valuation and other metrics should be prioritized. ")
                elif peg_ratio_val < 1.0 and peg_ratio_val >= 0:
                    peg_paragraph += (f"A PEG below 1.0, like {ticker}'s current ratio, can indicate that the stock might be undervalued given its "
                                      "earnings growth forecast. This can be particularly attractive for investors looking for growth at a reasonable price (GARP). ")
                elif peg_ratio_val >= 1.0 and peg_ratio_val <= 1.5: # Adjusted to be inclusive of 1.0
                    peg_paragraph += (f"This PEG ratio of {peg_ratio_fmt} suggests a reasonable balance between the stock's P/E and its expected growth. "
                                      "It doesn't strongly signal over or undervaluation based on this metric alone. ")
                elif peg_ratio_val > 1.5:
                    peg_paragraph += (f"A PEG significantly above 1.0, such as {peg_ratio_fmt}, could suggest that the stock's price has outpaced its expected earnings growth, "
                                      "or that investors are paying a premium for that growth. This warrants closer scrutiny of the growth assumptions and sustainability. ")
                
            peg_paragraph += "However, like all ratios, the PEG is best used in conjunction with other valuation metrics and a thorough understanding of the company's prospects and the industry it operates in.</p>"
            peg_explanation_html += peg_paragraph
            html_content += peg_explanation_html
        
        # You can add similar detailed explanations for Trailing P/E, P/S, P/B here
        # For brevity in this example, I'm focusing on Forward P/E and PEG

        # Displaying other key valuation metrics in a slightly more descriptive way
        # This can be expanded similarly to P/E and PEG or use a condensed table.
        
        other_metrics_html = "<h4>Other Key Valuation Ratios:</h4><ul>"
        if trailing_pe_fmt != "N/A":
            other_metrics_html += f"<li><strong>Trailing P/E: {trailing_pe_fmt}</strong> - Reflects the company's stock price relative to its earnings per share over the past 12 months (TTM). It's a historical measure often used as a starting point for valuation.</li>"
        if ps_ratio_fmt != "N/A":
            other_metrics_html += f"<li><strong>Price/Sales (TTM): {ps_ratio_fmt}</strong> - Compares the company's stock price to its total sales per share over the past 12 months. This can be particularly useful for valuing companies that are not yet profitable or are in cyclical industries where earnings can be volatile.</li>"
        if pb_ratio_fmt != "N/A":
            other_metrics_html += f"<li><strong>Price/Book (MRQ): {pb_ratio_fmt}</strong> - Measures the market's valuation of a company compared to its book value (assets minus liabilities) on its most recent quarterly balance sheet. A lower P/B ratio could mean the stock is undervalued. It's often used for valuing financial institutions or capital-intensive businesses.</li>"
        other_metrics_html += "</ul>"
        
        if other_metrics_html != "<h4>Other Key Valuation Ratios:</h4><ul></ul>": # Only add if there's content
            html_content += other_metrics_html

        # Optionally, add back the original table if you want a compact summary as well
        # html_content += generate_metrics_section_content(valuation_data) 

        return html_content
    except Exception as e:
        logging.error(f"Error in generate_valuation_metrics_html for {ticker}: {e}", exc_info=True)
        return _generate_error_html("Valuation Metrics", str(e))

def generate_financial_health_html(ticker, rdata):
    """Generates Financial Health section with a default narrative focus."""
    try:
        health_data = rdata.get('financial_health_data')
        if not isinstance(health_data, dict):
             health_data = {}
             logging.warning("financial_health_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(health_data)
        currency_symbol = rdata.get('currency_symbol', '$')

        roe_fmt = format_html_value(health_data.get('Return on Equity (ROE TTM)'), 'percent_direct')
        debt_equity_fmt = format_html_value(health_data.get('Debt/Equity (MRQ)'), 'ratio')
        current_ratio_fmt = format_html_value(health_data.get('Current Ratio (MRQ)'), 'ratio')
        quick_ratio_fmt = format_html_value(health_data.get('Quick Ratio (MRQ)'), 'ratio')
        op_cash_flow_fmt = format_html_value(health_data.get('Operating Cash Flow (TTM)'), 'large_number', currency=currency_symbol)
        roe_trend = rdata.get('roe_trend', None) 
        debt_equity_trend = rdata.get('debt_equity_trend', None)
        
        health_summary_options = [
            f"Key indicators include ROE ({roe_fmt}), Debt/Equity ({debt_equity_fmt}), Current Ratio ({current_ratio_fmt}), Quick Ratio ({quick_ratio_fmt}), and Operating Cash Flow ({op_cash_flow_fmt}).",
            f"Financial stability is gauged by ROE ({roe_fmt}), leverage ({debt_equity_fmt}), liquidity (Current: {current_ratio_fmt}, Quick: {quick_ratio_fmt}), and cash generation (Op Cash Flow: {op_cash_flow_fmt}).",
            f"We assess health via ROE ({roe_fmt}), D/E ratio ({debt_equity_fmt}), liquidity measures (Current: {current_ratio_fmt}, Quick: {quick_ratio_fmt}), and operating cash flow ({op_cash_flow_fmt})."
        ]
        health_summary = random.choice(health_summary_options)

        trend_comments = []
        if roe_trend: trend_comments.append(f"ROE trend appears {str(roe_trend).lower()}.")
        if debt_equity_trend: trend_comments.append(f"Debt/Equity trend seems {str(debt_equity_trend).lower()}.")
        trend_context = " ".join(trend_comments)
        
        # Default Narrative
        narrative_options = [
            (
                 f"Financial health metrics provide insights into {ticker}'s stability, efficiency, and ability to meet its obligations. {health_summary} {trend_context} "
                 f"These figures indicate the company's leverage, short-term solvency, and profitability relative to shareholder equity. Robust cash flow is generally a positive sign."
            ),
            (
            f"This section gauges {ticker}'s financial stability and operational effectiveness. {health_summary} {trend_context} "
            f"The data reflects leverage, liquidity, and returns on equity. Strong cash flow is typically viewed favorably."
            )
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Financial Health", str(e))

def generate_financial_efficiency_html(ticker, rdata):
    """Generates Financial Efficiency section with a default narrative focus."""
    try:
        efficiency_data = rdata.get('financial_efficiency_data')
        if not isinstance(efficiency_data, dict):
             efficiency_data = {}
             logging.warning("financial_efficiency_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(efficiency_data)

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
            f"Benchmarking these efficiency metrics with industry peers {get_icon('peer')} and the company's own history {get_icon('history')} provides valuable context.",
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
    """Generates Profitability & Growth section with a default narrative focus."""
    try:
        profit_data = rdata.get('profitability_data')
        if not isinstance(profit_data, dict):
             profit_data = {}
             logging.warning("profitability_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(profit_data)
        currency_symbol = rdata.get('currency_symbol', '$')

        gross_margin_fmt = format_html_value(profit_data.get('Gross Margin (TTM)'), 'percent_direct')
        op_margin_fmt = format_html_value(profit_data.get('Operating Margin (TTM)'), 'percent_direct')
        net_margin_key = 'Net Profit Margin (TTM)'
        if net_margin_key not in profit_data: net_margin_key = 'Profit Margin (TTM)'
        net_margin_fmt = format_html_value(profit_data.get(net_margin_key), 'percent_direct')
        rev_growth_fmt = format_html_value(profit_data.get('Revenue Growth (YoY)'), 'percent_direct')
        earn_growth_fmt = format_html_value(profit_data.get('Earnings Growth (YoY)'), 'percent_direct')
        margin_trend = rdata.get('margin_trend', None) 
        growth_trend = rdata.get('growth_trend', None) 
        
        profit_summary_options = [
            f"Key profitability metrics include Gross Margin ({gross_margin_fmt}), Operating Margin ({op_margin_fmt}), and Net Profit Margin ({net_margin_fmt}).",
            f"Profitability is reflected in margins: Gross ({gross_margin_fmt}), Operating ({op_margin_fmt}), and Net ({net_margin_fmt}).",
            f"Core profitability measures are Gross Margin ({gross_margin_fmt}), Operating Margin ({op_margin_fmt}), and Net Margin ({net_margin_fmt})."
        ]
        profit_summary = random.choice(profit_summary_options)

        growth_summary_options = [
             f"Recent expansion is reflected in Year-over-Year Revenue Growth ({rev_growth_fmt}) and Earnings Growth ({earn_growth_fmt}).",
             f"Growth trends are indicated by YoY Revenue ({rev_growth_fmt}) and Earnings ({earn_growth_fmt}) increases.",
             f"The company's recent growth trajectory shows Revenue up {rev_growth_fmt} and Earnings up {earn_growth_fmt} YoY."
        ]
        growth_summary = random.choice(growth_summary_options)

        comparison_prompt_options = [
            f"Evaluating these margins and growth rates against historical performance {get_icon('history')} and industry competitors {get_icon('peer')} provides crucial context.",
            f"Benchmarking these profit and growth figures against the past {get_icon('history')} and peers {get_icon('peer')} is vital for interpretation.",
            f"Context for these margin and growth numbers comes from comparing them to historical data {get_icon('history')} and industry rivals {get_icon('peer')}."
        ]
        comparison_prompt = random.choice(comparison_prompt_options)

        trend_comments = []
        if margin_trend: trend_comments.append(f"Margin trend appears {str(margin_trend).lower()}.")
        if growth_trend: trend_comments.append(f"Growth trend seems {str(growth_trend).lower()}.")
        trend_context = " ".join(trend_comments)

        # Default Narrative
        narrative_options = [
            (
                 f"This section examines {ticker}'s ability to generate profit and expand its business. {profit_summary} {growth_summary} {trend_context} {comparison_prompt} These are key indicators of financial performance and future potential."
            ),
            (
            f"Here we look at {ticker}'s profit generation and growth trajectory. {profit_summary} {growth_summary} {trend_context} {comparison_prompt} These metrics reflect financial success and expansion capacity."
            )
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Profitability & Growth", str(e))

def generate_dividends_shareholder_returns_html(ticker, rdata):
    """Generates Dividends & Shareholder Returns section with a default narrative focus."""
    try:
        dividend_data = rdata.get('dividends_data')
        if not isinstance(dividend_data, dict):
             dividend_data = {}
             logging.warning("dividends_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(dividend_data)
        currency_symbol = rdata.get('currency_symbol', '$')

        fwd_yield_fmt = format_html_value(dividend_data.get('Dividend Yield (Fwd)'), 'percent_direct')
        fwd_dividend_fmt = format_html_value(dividend_data.get('Forward Annual Dividend Rate'), 'currency', currency=currency_symbol)
        payout_ratio_fmt = format_html_value(dividend_data.get('Payout Ratio'), 'percent_direct')
        dividend_date_key = 'Ex-Dividend Date' if dividend_data.get('Ex-Dividend Date') else 'Last Split Date' 
        dividend_date_label = "Ex-Dividend Date" if dividend_date_key == 'Ex-Dividend Date' else "Last Event Date"
        dividend_date_fmt = format_html_value(dividend_data.get(dividend_date_key), 'date')
        buyback_yield_fmt = format_html_value(dividend_data.get('Buyback Yield (Est.)'), 'percent_direct')
        
        fwd_yield_val = _safe_float(dividend_data.get('Dividend Yield (Fwd)'))
        has_dividend = fwd_yield_val is not None and fwd_yield_val > 0.01 

        dividend_summary = ""
        if has_dividend:
            payout_level_options = {
                'high': ["high (monitor sustainability)", "elevated (check cash flow coverage)", "high (may limit growth reinvestment)"],
                'neg': ["negative (requires investigation, funded by non-earnings?)", "negative (dividend exceeds earnings)", "negative (unsustainable without other cash sources)"],
                'low': ["low (potential for growth)", "conservative (room for increases)", "low (prioritizing reinvestment?)"],
                'mid': ["moderate", "reasonable", "sustainable based on current earnings"]
            }
            payout_level = random.choice(payout_level_options['mid']) 
            payout_ratio_val = _safe_float(dividend_data.get('Payout Ratio'))
            if payout_ratio_val is not None:
                 if payout_ratio_val > 80: payout_level = random.choice(payout_level_options['high'])
                 elif payout_ratio_val < 0: payout_level = random.choice(payout_level_options['neg'])
                 elif payout_ratio_val < 30: payout_level = random.choice(payout_level_options['low'])

            dividend_summary_options = [
                f"{ticker} currently offers a forward dividend yield of <strong>{fwd_yield_fmt}</strong> (representing {fwd_dividend_fmt} annually per share). The Payout Ratio of {payout_ratio_fmt} suggests the dividend is currently {payout_level}. Last relevant date ({dividend_date_label}): {dividend_date_fmt}.",
                f"Shareholders receive a dividend yielding <strong>{fwd_yield_fmt}</strong> (equivalent to {fwd_dividend_fmt} per year). With a Payout Ratio of {payout_ratio_fmt}, its coverage appears {payout_level}. Last key date ({dividend_date_label}): {dividend_date_fmt}."
            ]
            dividend_summary = random.choice(dividend_summary_options)
        else:
            dividend_summary_options = [
                f"{ticker} does not currently pay a significant regular dividend or data is unavailable.",
                f"No substantial regular dividend payment is indicated for {ticker} based on available data."
            ]
            dividend_summary = random.choice(dividend_summary_options)

        buyback_summary = ""
        buyback_yield_val = _safe_float(dividend_data.get('Buyback Yield (Est.)'))
        shares_change_val = _safe_float(rdata.get('share_statistics_data', {}).get('Shares Change (YoY)'))
        buyback_indication = (buyback_yield_val is not None and buyback_yield_val != 0) or (shares_change_val is not None and shares_change_val < 0)

        if buyback_indication:
            buyback_summary_options = []
            if buyback_yield_fmt != 'N/A' and buyback_yield_fmt != '0.00%':
                buyback_summary_options.extend([
                    f" Additionally, the company returns value via share repurchases, estimated at a {buyback_yield_fmt} buyback yield.",
                    f" Share buybacks supplement returns, contributing an estimated {buyback_yield_fmt} yield."])
            elif shares_change_val is not None and shares_change_val < 0: 
                buyback_summary_options.extend([
                     f" Share repurchases also appear to be part of the capital return strategy, as indicated by a reduction in shares outstanding (see Share Statistics).",
                     f" Capital is also returned via buybacks, evidenced by a falling share count (refer to Share Statistics)."])
            if buyback_summary_options: 
                 buyback_summary = random.choice(buyback_summary_options)
        else:
             buyback_summary = random.choice([
                 " Significant share repurchases are not indicated by available data.",
                 " Share buybacks do not appear to be a major component of current capital returns."])
        
        # Default Narrative
        narrative_options = [
             (
                 f"This section outlines how {ticker} returns value to its shareholders through dividends and potentially share buybacks. {dividend_summary}{buyback_summary}"
             ),
             (
             f"Here we examine {ticker}'s capital return policy via dividends and share repurchases. {dividend_summary}{buyback_summary}"
             )
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Dividends & Shareholder Returns", str(e))

def generate_share_statistics_html(ticker, rdata):
    """Generates Share Statistics with a default narrative focus."""
    try:
        share_data = rdata.get('share_statistics_data')
        if not isinstance(share_data, dict):
             share_data = {}
             logging.warning("share_statistics_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(share_data)
        currency_symbol = rdata.get('currency_symbol', '$')

        float_shares = format_html_value(share_data.get('Float'), 'large_number', currency=currency_symbol) # No currency for shares count
        shares_outstanding = format_html_value(share_data.get('Shares Outstanding'), 'large_number', currency=currency_symbol) # No currency for shares count
        insider_own_fmt = format_html_value(share_data.get('Insider Ownership'), 'percent_direct') 
        inst_own_fmt = format_html_value(share_data.get('Institutional Ownership'), 'percent_direct') 
        shares_change_yoy_fmt = format_html_value(share_data.get('Shares Change (YoY)'), 'percent_direct') 

        ownership_implication = ""
        insider_val = _safe_float(share_data.get('Insider Ownership'))
        inst_val = _safe_float(share_data.get('Institutional Ownership'))
        insider_options = {'high': ["significant", "substantial"], 'mid': ["moderate", "meaningful"], 'low': ["low", "limited"]}
        insider_alignment_options = {'high': ["suggests strong alignment with shareholders."], 'mid': ["suggests some alignment with shareholders."], 'low': ["suggests limited direct management skin-in-the-game."]}

        if insider_val is not None:
            insider_level = random.choice(insider_options['high']) if insider_val > 10 else random.choice(insider_options['mid']) if insider_val > 2 else random.choice(insider_options['low'])
            ownership_implication += f"The {insider_level} insider ownership ({insider_own_fmt}) {random.choice(insider_alignment_options[insider_level if insider_val > 10 else ('mid' if insider_val > 2 else 'low')])}"

        inst_options = {'high': ["very high", "dominant"], 'mid': ["high", "significant"], 'low': ["moderate", "reasonable"]}
        inst_conviction_options = {'high': ["indicating strong conviction from large investors, potentially leading to lower volatility."], 'mid': ["indicating moderate interest from large funds."], 'low': ["reflecting limited institutional focus currently."]}

        if inst_val is not None:
            inst_level = random.choice(inst_options['high']) if inst_val > 75 else random.choice(inst_options['mid']) if inst_val > 50 else random.choice(inst_options['low'])
            if ownership_implication: ownership_implication += " "
            ownership_implication += f"Institutional ownership stands at a {inst_level} level ({inst_own_fmt}), {random.choice(inst_conviction_options[inst_level if inst_val > 75 else ('mid' if inst_val > 50 else 'low')])}"

        float_context_options = [
            f"The public float of <strong>{float_shares}</strong> (out of {shares_outstanding} outstanding shares) represents the shares readily available for trading, influencing liquidity and potential price impact from large trades.",
            f"With <strong>{float_shares}</strong> shares floating (vs. {shares_outstanding} total), this portion is actively traded, affecting liquidity and susceptibility to large order impacts."
        ]
        float_context = random.choice(float_context_options)
        
        # Default Narrative
        narrative_options = [
             (
                 f"These statistics detail {ticker}'s equity landscape. {float_context} {ownership_implication} "
                 f"Monitoring changes in share count ({shares_change_yoy_fmt}) and ownership can offer clues about company strategy and investor sentiment."
             ),
             (
             f"Here's a look at {ticker}'s share structure. {float_context} {ownership_implication} "
             f"Tracking share count ({shares_change_yoy_fmt}) and ownership shifts provides insight into corporate actions and market sentiment."
             )
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Share Statistics", str(e))

def generate_stock_price_statistics_html(ticker, rdata):
    """Generates Stock Price Statistics section with a default narrative focus."""
    try:
        stats_data = rdata.get('stock_price_stats_data', {})
        if not isinstance(stats_data, dict):
            stats_data = {}
            logging.warning("stock_price_stats_data not found or not a dict, using empty.")
        currency_symbol = rdata.get('currency_symbol', '$')

        volatility = _safe_float(rdata.get('volatility'))
        volatility_fmt = format_html_value(volatility, 'percent_direct', 1)
        
        if volatility is not None:
            stats_data['Volatility (30d Ann.)'] = f"{volatility_fmt} {get_icon('stats')}"
        else:
            stats_data['Volatility (30d Ann.)'] = "N/A"

        content = generate_metrics_section_content(stats_data)

        beta_fmt = format_html_value(stats_data.get('Beta'), 'ratio')
        fifty_two_wk_high_fmt = format_html_value(stats_data.get('52 Week High'), 'currency', currency=currency_symbol)
        fifty_two_wk_low_fmt = format_html_value(stats_data.get('52 Week Low'), 'currency', currency=currency_symbol)
        avg_vol_3m_fmt = format_html_value(stats_data.get('Average Volume (3 month)'), 'integer')
        
        stats_summary_options = [
            f"Key price behavior metrics include Beta ({beta_fmt}), the 52-week trading range ({fifty_two_wk_low_fmt} - {fifty_two_wk_high_fmt}), recent short-term volatility ({volatility_fmt}), and average trading liquidity (3m Avg Vol: {avg_vol_3m_fmt}).",
            f"Price characteristics are summarized by Beta ({beta_fmt}), the annual range ({fifty_two_wk_low_fmt} to {fifty_two_wk_high_fmt}), recent volatility ({volatility_fmt}), and typical volume ({avg_vol_3m_fmt})."
        ]
        stats_summary = random.choice(stats_summary_options)

        vol_interp = ""
        if volatility is not None:
            if volatility > 40: vol_interp = f"The recent volatility ({volatility_fmt}) is high, indicating significant price swings."
            elif volatility > 20: vol_interp = f"Recent volatility ({volatility_fmt}) is moderate, suggesting average price fluctuations."
            else: vol_interp = f"Volatility ({volatility_fmt}) is relatively low, implying more stable price action recently."

        beta_interp = ""
        beta_val = _safe_float(stats_data.get('Beta'))
        if beta_val is not None:
            if beta_val > 1.2: beta_interp = f"Beta ({beta_fmt}) suggests the stock is more volatile than the overall market."
            elif beta_val < 0.8: beta_interp = f"Beta ({beta_fmt}) indicates lower volatility relative to the market."
            else: beta_interp = f"Beta ({beta_fmt}) implies the stock's volatility generally tracks the broader market."
        
        # Default Narrative
        narrative_options = [
             (
                 f"This section summarizes {ticker}'s stock price characteristics, including its sensitivity to market movements, historical trading range, recent price fluctuation intensity, and typical trading volume. {stats_summary} {beta_interp} {vol_interp}"
             ),
             (
             f"Here we detail {ticker}'s price behavior: market sensitivity, historical range, recent volatility, and volume. {stats_summary} {beta_interp} {vol_interp}"
             )
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Stock Price Statistics", str(e))

def generate_short_selling_info_html(ticker, rdata):
    """Generates Short Selling Info section with a default narrative focus."""
    try:
        short_data = rdata.get('short_selling_data')
        if not isinstance(short_data, dict):
             short_data = {}
             logging.warning("short_selling_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(short_data)

        short_percent_float_fmt = format_html_value(short_data.get('Short % of Float'), 'percent_direct')
        short_ratio_fmt = format_html_value(short_data.get('Short Ratio (Days To Cover)'), 'ratio')
        
        short_summary_options = [
            f"Key short interest indicators include Short % of Float ({short_percent_float_fmt}) and the Short Ratio ({short_ratio_fmt}).",
            f"Short selling activity is measured by Short % of Float ({short_percent_float_fmt}) and Days to Cover ({short_ratio_fmt})."
        ]
        short_summary = random.choice(short_summary_options)

        level_interp_options = {'high': ["very high", "significant"], 'mid_high':["high", "elevated"], 'mid_low':["moderate", "medium"], 'low':["low", "minimal"]}
        sentiment_interp_options = {'high': ["significant bearish sentiment"], 'mid_high': ["notable bearish sentiment"], 'mid_low': ["moderate bearish sentiment"], 'low': ["low bearish sentiment"]}
        squeeze_interp_options = {'high': ["high", "significant"], 'mid_high':["elevated", "increased"], 'mid_low':["moderate", "some"], 'low':["low", "limited"]}

        level_interp = "unavailable"; squeeze_potential = "limited"; sentiment_implication = "neutral bearish sentiment"
        spf_val = _safe_float(short_data.get('Short % of Float'))
        if spf_val is not None:
            if spf_val > 20:
                level_interp = random.choice(level_interp_options['high']); sentiment_implication = random.choice(sentiment_interp_options['high']); squeeze_potential = random.choice(squeeze_interp_options['high'])
            elif spf_val > 10:
                level_interp = random.choice(level_interp_options['mid_high']); sentiment_implication = random.choice(sentiment_interp_options['mid_high']); squeeze_potential = random.choice(squeeze_interp_options['mid_high'])
            elif spf_val > 5:
                level_interp = random.choice(level_interp_options['mid_low']); sentiment_implication = random.choice(sentiment_interp_options['mid_low']); squeeze_potential = random.choice(squeeze_interp_options['mid_low'])
            else:
                level_interp = random.choice(level_interp_options['low']); sentiment_implication = random.choice(sentiment_interp_options['low']); squeeze_potential = random.choice(squeeze_interp_options['low'])

        short_ratio_interp = ""
        sr_val = _safe_float(short_data.get('Short Ratio (Days To Cover)'))
        if sr_val is not None:
             if sr_val > 10:
                 short_ratio_interp_options = [ f"The high Days to Cover ({short_ratio_fmt}) implies it would take significant time for shorts to cover, amplifying potential short squeeze intensity." ]
                 short_ratio_interp = random.choice(short_ratio_interp_options)
             elif sr_val > 5:
                 short_ratio_interp_options = [ f"The moderate Days to Cover ({short_ratio_fmt}) suggests a reasonable time needed for shorts to exit, contributing to {squeeze_potential} squeeze potential." ]
                 short_ratio_interp = random.choice(short_ratio_interp_options)
             else:
                 short_ratio_interp_options = [ f"The low Days to Cover ({short_ratio_fmt}) indicates shorts could cover relatively quickly, potentially limiting squeeze duration." ]
                 short_ratio_interp = random.choice(short_ratio_interp_options)
        
        # Default Narrative
        narrative_options = [
             (
                 f"Short selling data provides a measure of negative sentiment or bets against {ticker}. {short_summary} The current level is considered {level_interp}. "
                 f"This implies {sentiment_implication} and suggests {squeeze_potential} short squeeze potential. {short_ratio_interp}"
             ),
             (
             f"This data shows bets against {ticker}. {short_summary} The short interest level is {level_interp}. "
             f"This indicates {sentiment_implication} and carries {squeeze_potential} potential for a short squeeze. {short_ratio_interp}"
             )
        ]
        narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Short Selling Info", str(e))

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
        currency_symbol = rdata.get('currency_symbol', '$')

        recommendation = format_html_value(analyst_data.get('Recommendation'), 'factor') 
        mean_target_fmt = format_html_value(analyst_data.get('Mean Target Price'), 'currency', currency=currency_symbol)
        high_target_fmt = format_html_value(analyst_data.get('High Target Price'), 'currency', currency=currency_symbol)
        low_target_fmt = format_html_value(analyst_data.get('Low Target Price'), 'currency', currency=currency_symbol)
        num_analysts_fmt = format_html_value(analyst_data.get('Number of Analyst Opinions'), 'integer')
        current_price = _safe_float(rdata.get('current_price'))
        current_price_fmt = format_html_value(current_price, 'currency', currency=currency_symbol)

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
             f"This consensus is based on opinions from {num_analysts_fmt} analyst(s)." if num_analysts_fmt != 'N/A' else "The number of contributing analysts is unspecified.",
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
    """Generates the TECHNICAL ANALYSIS summary section (default interpretations)."""
    try:
        sentiment = rdata.get('sentiment', 'Neutral')
        current_price = rdata.get('current_price')
        last_date_obj = rdata.get('last_date', datetime.now())
        last_date_fmt = format_html_value(last_date_obj, 'date')
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        if not isinstance(detailed_ta_data, dict):
            detailed_ta_data = {}
            logging.warning("detailed_ta_data not found or not a dict, using empty.")
        currency_symbol = rdata.get('currency_symbol', '$')

        price_f = _safe_float(current_price)
        sma20 = _safe_float(detailed_ta_data.get('SMA_20')); sma50 = _safe_float(detailed_ta_data.get('SMA_50'))
        sma100 = _safe_float(detailed_ta_data.get('SMA_100')); sma200 = _safe_float(detailed_ta_data.get('SMA_200'))
        latest_rsi = _safe_float(detailed_ta_data.get('RSI_14'))
        rsi_divergence_bearish = rdata.get('rsi_divergence_bearish', False) 
        rsi_divergence_bullish = rdata.get('rsi_divergence_bullish', False)

        def price_vs_ma(price_val, ma_val):
            if price_val is None or ma_val is None: return ('trend-neutral', '', 'Neutral')
            if price_val > ma_val * 1.001: return ('trend-up', f'{get_icon("up")} (Above)', 'Above')
            if price_val < ma_val * 0.999: return ('trend-down', f'{get_icon("down")} (Below)', 'Below')
            return ('trend-neutral', f'{get_icon("neutral")} (At)', 'At')

        sma20_status, sma20_label, sma20_pos = price_vs_ma(price_f, sma20)
        sma50_status, sma50_label, sma50_pos = price_vs_ma(price_f, sma50)
        sma100_status, sma100_label, sma100_pos = price_vs_ma(price_f, sma100)
        sma200_status, sma200_label, sma200_pos = price_vs_ma(price_f, sma200)

        summary_points = []
        price_fmt = format_html_value(current_price, 'currency', currency=currency_symbol)

        trend_desc = random.choice(["Mixed Trend Signals.", "Unclear Trend Direction."])
        trend_implication = random.choice(["suggesting conflicting short-term and long-term momentum requiring careful monitoring."])
        if sma50_pos == 'Above' and sma200_pos == 'Above':
            trend_desc = random.choice(["Bullish Trend Confirmation", "Positive Trend Alignment"])
            trend_implication = random.choice([f"as price ({price_fmt}) holds above both the key 50-day and 200-day SMAs, indicating positive momentum across timeframes."])
        elif sma50_pos == 'Below' and sma200_pos == 'Below':
            trend_desc = random.choice(["Bearish Trend Confirmation", "Negative Trend Alignment"])
            trend_implication = random.choice([f"with price ({price_fmt}) below both the 50-day and 200-day SMAs, signaling prevailing weakness."])
        # ... (other trend conditions simplified for brevity, original had more)
        summary_points.append(f"<strong>Trend:</strong> {trend_desc}, {trend_implication}")

        rsi_text = "Momentum (RSI): Data N/A."
        if latest_rsi is not None:
            rsi_level = random.choice(["Neutral", "Balanced"])
            rsi_icon = get_icon('neutral')
            rsi_implication = random.choice(["indicating balanced momentum."])
            if latest_rsi > 70: rsi_level = random.choice(["Overbought", "Extended"]); rsi_icon = get_icon('warning'); rsi_implication = random.choice(["suggesting the rally might be overextended."])
            elif latest_rsi < 30: rsi_level = random.choice(["Oversold", "Depressed"]); rsi_icon = get_icon('positive'); rsi_implication = random.choice(["potentially indicating the sell-off is exhausted."])
            divergence_text = ""
            if rsi_divergence_bearish: divergence_text = f" {get_icon('divergence')} <strong>Warning: Potential Bearish Divergence detected.</strong>"
            if rsi_divergence_bullish: divergence_text = f" {get_icon('divergence')} <strong>Note: Potential Bullish Divergence detected.</strong>"
            rsi_text = f"<strong>Momentum (RSI):</strong> {rsi_icon} {latest_rsi:.1f} ({rsi_level}), {rsi_implication}{divergence_text}"
        summary_points.append(rsi_text)
        # ... (MACD, BBands, Support/Resistance points would be similarly genericized if they had site-specific logic)

        summary_list_html = "".join([f"<li>{point}</li>" for point in summary_points if point and 'N/A' not in point])

        # Default Narrative Intro
        narrative_intro_options = [
            f"The following technical analysis summary for {ticker}, based on data up to {last_date_fmt}, outlines key indicators related to trend, momentum, and volatility. Detailed charts typically provide visual confirmation of these signals.",
            f"This technical overview for {ticker} (as of {last_date_fmt}) covers essential trend, momentum, and volatility indicators. Charts offer more detail, but this summarizes the key signals."
        ]
        narrative_intro = random.choice(narrative_intro_options)

        disclaimer_tech = random.choice([
            "Technical analysis uses past price and volume data to identify potential future trends but offers no guarantees. Combine with fundamental analysis and risk management.",
            "Remember, technical analysis looks at past data to find potential patterns; it doesn't predict the future with certainty. Always use it alongside fundamentals and risk control."
        ])

        return f"""
            <div class="sentiment-indicator">
                <span>Overall Technical Sentiment:</span><span class="sentiment-{str(sentiment).lower().replace(' ', '-')}">{get_icon('up' if 'Bullish' in str(sentiment) else ('down' if 'Bearish' in str(sentiment) else 'neutral'))} {str(sentiment)}</span>
            </div>
            <div class="narrative">
                <p>{narrative_intro}</p>
                <ul>{summary_list_html}</ul>
            </div>
            <h4>Moving Average Details</h4>
            <div class="ma-summary">
                <div class="ma-item"><span class="label">SMA 20:</span> <span class="value">{format_html_value(sma20, 'currency', currency=currency_symbol)}</span> <span class="status {sma20_status}">{sma20_label}</span></div>
                <div class="ma-item"><span class="label">SMA 50:</span> <span class="value">{format_html_value(sma50, 'currency', currency=currency_symbol)}</span> <span class="status {sma50_status}">{sma50_label}</span></div>
                <div class="ma-item"><span class="label">SMA 100:</span> <span class="value">{format_html_value(sma100, 'currency', currency=currency_symbol)}</span> <span class="status {sma100_status}">{sma100_label}</span></div>
                <div class="ma-item"><span class="label">SMA 200:</span> <span class="value">{format_html_value(sma200, 'currency', currency=currency_symbol)}</span> <span class="status {sma200_status}">{sma200_label}</span></div>
            </div>
            <p class="disclaimer">{disclaimer_tech}</p>
            """
    except Exception as e:
        return _generate_error_html("Technical Analysis Summary", str(e))

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
    """Generates the FAQ section with default, nuanced answers."""
    try:
        current_price = _safe_float(rdata.get('current_price'))
        forecast_1y = _safe_float(rdata.get('forecast_1y'))
        overall_pct_change = _safe_float(rdata.get('overall_pct_change'), default=0.0)
        sentiment = rdata.get('sentiment', 'Neutral')
        volatility = _safe_float(rdata.get('volatility'))
        valuation_data = rdata.get('valuation_data', {})
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        risk_items = rdata.get('risk_items', [])
        currency_symbol = rdata.get('currency_symbol', '$')

        if not isinstance(valuation_data, dict): valuation_data = {}
        if not isinstance(detailed_ta_data, dict): detailed_ta_data = {}

        latest_rsi = _safe_float(detailed_ta_data.get('RSI_14'))
        current_price_fmt = format_html_value(current_price, 'currency', currency=currency_symbol)
        forecast_1y_fmt = format_html_value(forecast_1y, 'currency', currency=currency_symbol)

        faq_items = []
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
        q2_ans_options = [f"The 1-year forecast model suggests the price might <strong>{up_down_neutral}</strong> on average ({overall_pct_change:+.1f}% potential). However, short-term direction is highly uncertain and heavily influenced by prevailing market sentiment (currently '{sentiment_str}'), breaking news, and overall economic conditions. Technical indicators (see TA Summary) provide clues for near-term direction."]
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
        
        # Default "Good Buy?" answer
        q3_ans_options = [
            (f"Determining if {ticker} is a 'good buy' requires evaluating multiple factors. Technical sentiment is '{sentiment_str}', while the 1-year forecast suggests {overall_pct_change:+.1f}% potential. {rsi_condition} "
             f"Consider the valuation, financial health, growth prospects, and {risk_mention} Align these factors with your personal investment strategy and risk tolerance. {disclaimer}"),
            (f"Whether {ticker} is a 'good buy' now involves balancing various elements: '{sentiment_str}' technicals, a {overall_pct_change:+.1f}% forecast potential, and {rsi_condition} "
             f"Weigh the company's valuation, stability, growth, and {risk_mention} against your own investment goals and risk profile. {disclaimer}")
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
        q4_ans_options = [f"Based on recent 30-day price action, {ticker}'s annualized volatility is ≈<strong>{volatility_fmt}</strong>. This level is currently considered {vol_level}, indicating the degree of recent price fluctuation. {vol_comp} Higher volatility means larger potential price swings (both up and down)."]
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
        q5_ans_options = [f"{ticker}'s Trailing P/E ratio (based on past earnings) is <strong>{pe_ratio_fmt}</strong>, which is considered {pe_comment}. The Forward P/E (based on expected earnings) is {fwd_pe_fmt}. A P/E ratio indicates how much investors are paying per dollar of earnings. {pe_context} A high P/E isn't necessarily bad if strong growth justifies it (check PEG ratio in Valuation Metrics)."]
        faq_items.append((f"What is {ticker}'s P/E ratio and what does it mean?", random.choice(q5_ans_options)))

        details_html = "".join([f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq_items])
        return details_html
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
                for generic_key, variations in generic_risks_map.items():
                    if item_str.startswith(generic_key) or generic_key in item_str:
                        processed_risk_items.append(random.choice(variations))
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