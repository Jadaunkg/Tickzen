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
    if value is None or value == "N/A" or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        # Special case: If already formatted currency string (from sources like Market Cap)
        if isinstance(value, str) and value.startswith(currency) and format_type != "string":
             # Basic validation: Ensure it looks like a currency value (e.g., $1.23M, $1,234.56)
             if re.match(r'^\$[0-9,.]+[ KMBT]?$', value):
                 return value
             else:
                 # If it starts with $ but doesn't look right, try to process it numerically
                 logging.debug(f"Value '{value}' started with currency but failed validation, attempting numeric format.")
                 pass # Fall through to numeric processing

        # Numeric conversion logic for relevant types
        num_value = None
        if format_type not in ["date", "string", "factor"]:
            num_value = _safe_float(value, default=None)
            if num_value is None and format_type != "string": # If float conversion failed and it's not supposed to be a string
                 logging.warning(f"Failed numeric conversion for value {original_value_repr} needed for format '{format_type}'. Falling back.")
                 return str(value) # Fallback to string representation

        # Apply formatting based on type
        if format_type == "currency": return f"{currency}{num_value:,.{precision}f}"
        elif format_type == "percent": return f"{num_value * 100:.{precision}f}%" # Input is 0.xx
        elif format_type == "percent_direct": return f"{num_value:.{precision}f}%" # Input is xx.xx
        elif format_type == "ratio":
            if abs(num_value) > 1e6 or (abs(num_value) < 1e-3 and num_value != 0): return f"{num_value:.{precision}e}x"
            return f"{num_value:.{precision}f}x"
        elif format_type == "large_number":
            if abs(num_value) >= 1e12: return f"{currency}{num_value / 1e12:.{precision}f} T"
            elif abs(num_value) >= 1e9: return f"{currency}{num_value / 1e9:.{precision}f} B"
            elif abs(num_value) >= 1e6: return f"{currency}{num_value / 1e6:.{precision}f} M"
            elif abs(num_value) >= 1e3: return f"{currency}{num_value / 1e3:.{precision}f} K"
            else: return f"{currency}{num_value:,.0f}"
        elif format_type == "integer": return f"{int(num_value):,}"
        elif format_type == "date":
            # Using pandas.to_datetime is more robust for various date formats
            dt = pd.to_datetime(value, errors='coerce')
            return dt.strftime('%Y-%m-%d') if pd.notna(dt) else str(value)
        elif format_type == "factor": return str(value) # Treat as string
        elif format_type == "string": return str(value)
        else: # Default 'number' format
             return f"{num_value:,.{precision}f}"

    except (ValueError, TypeError, OverflowError) as e:
        logging.warning(f"Formatting error for value {original_value_repr} (type: {format_type}): {e}", exc_info=False)
        return str(value) # Fallback if any unexpected formatting error occurs

# --- WRAPPED Component Functions with Site Variations & Deeper Analysis ---

# Wrap EACH generate_..._html function in a try-except block

def generate_introduction_html(ticker, rdata):
    """Generates the Introduction and Overview section with enhanced site variations and context."""
    try:
        profile_data = rdata.get('profile_data', {})
        site_name = rdata.get('site_name', '').lower()
        company_name = profile_data.get('Company Name', ticker)
        current_price = rdata.get('current_price')
        current_price_fmt = format_html_value(current_price, 'currency')
        # Use format_html_value for Market Cap too, assuming it might come as number or string
        market_cap_fmt = format_html_value(profile_data.get('Market Cap'), 'large_number')
        sector = profile_data.get('Sector', 'Unknown Sector')
        industry = profile_data.get('Industry', 'Unknown Industry')
        last_date_obj = rdata.get('last_date', datetime.now()) # Get the datetime object
        last_date_fmt = format_html_value(last_date_obj, 'date') # Format the date

        price = _safe_float(current_price)
        sma50 = _safe_float(rdata.get('sma_50'))
        sma200 = _safe_float(rdata.get('sma_200'))

        # --- Dynamic Text Generation ---
        # Varying ways to introduce the company and its context
        intro_phrase_options = [
            f"This analysis focuses on <strong>{company_name} ({ticker})</strong>, a key player within the {industry} industry ({sector} sector).",
            f"Here, we examine <strong>{company_name} ({ticker})</strong>, operating in the {sector} sector's {industry} space.",
            f"Our report delves into <strong>{company_name} ({ticker})</strong>, a company active in the {industry} field ({sector} sector).",
            f"We turn our attention to <strong>{company_name} ({ticker})</strong>, situated in the {industry} industry within the {sector} sector."
        ]
        intro_phrase = random.choice(intro_phrase_options)

        # Varying ways to introduce the price and date
        price_phrase_options = [
            f"As of {last_date_fmt}, the stock is trading at <strong>{current_price_fmt}</strong>,",
            f"The latest price recorded on {last_date_fmt} stands at <strong>{current_price_fmt}</strong>,",
            f"On {last_date_fmt}, {ticker}'s shares were valued at <strong>{current_price_fmt}</strong>,",
            f"Trading activity on {last_date_fmt} placed the stock price at <strong>{current_price_fmt}</strong>,"
        ]
        price_phrase = random.choice(price_phrase_options)

        # Varying ways to describe the technical picture based on MAs
        dynamic_sentiment_text = "its current market position"
        trend_context = ""
        if price is not None and sma50 is not None and sma200 is not None:
            if price < sma50 and price < sma200:
                dynamic_sentiment_text = random.choice([
                    "a potentially challenging technical posture below key moving averages",
                    "a technically weaker stance, positioned under its main moving averages",
                    "a bearish technical signal, trading beneath significant moving averages"
                ])
                trend_context = random.choice([
                    "This position below both the 50-day and 200-day Simple Moving Averages (SMAs) often signals short-to-medium term weakness.",
                    "Being under both the 50-day and 200-day SMAs typically suggests prevailing downward pressure.",
                    "Trading beneath these key SMAs usually points towards negative momentum in the near to medium term."
                ])
            elif price > sma50 and price > sma200:
                dynamic_sentiment_text = random.choice([
                    "apparent technical strength, trading above its key moving averages",
                    "a robust technical setup, holding above primary moving averages",
                    "a bullish technical indication, positioned over its main moving averages"
                ])
                trend_context = random.choice([
                    "Trading above both the 50-day and 200-day SMAs is typically viewed as a bullish signal, indicating positive short-to-medium term momentum.",
                    "Staying above these critical SMAs generally signifies positive market sentiment and upward momentum.",
                    "A position over both the 50-day and 200-day SMAs often confirms an ongoing uptrend."
                ])
            elif price > sma50 and price < sma200:
                 dynamic_sentiment_text = random.choice([
                     "a mixed technical picture, positioned between its key moving averages",
                     "a conflicted technical stance, caught between major moving averages",
                     "an ambiguous technical signal, trading above the 50-day but below the 200-day SMA"
                 ])
                 trend_context = random.choice([
                     "Being above the 50-day SMA but below the 200-day SMA suggests potential short-term strength conflicting with the longer-term trend, often requiring further confirmation.",
                     "This placement indicates short-term momentum might be positive, but the longer-term downtrend (vs. SMA200) remains a factor.",
                     "Such positioning often points to a period of consolidation or a potential battle between short-term buyers and long-term sellers."
                 ])
            else: # Below 50, Above 200
                 dynamic_sentiment_text = random.choice([
                     "an interesting technical juncture near its key moving averages",
                     "a notable technical position relative to its moving averages",
                     "a potentially pivotal technical spot, interacting with its SMAs"
                 ])
                 trend_context = random.choice([
                     "Positioned below the 50-day SMA but above the 200-day SMA indicates potential short-term consolidation or pullback within a longer-term uptrend.",
                     "This setup might suggest a temporary dip or consolidation phase within an established longer-term positive trend.",
                     "Trading below the short-term average but above the long-term one can signal weakening momentum that needs monitoring."
                 ])

        # Varying ways to introduce market cap
        market_cap_phrase_options = [
            f"With a market capitalization of approximately <strong>{market_cap_fmt}</strong>,",
            f"Boasting a market cap around <strong>{market_cap_fmt}</strong>,",
            f"Valued by the market at roughly <strong>{market_cap_fmt}</strong>,",
            f"Its market capitalization stands near <strong>{market_cap_fmt}</strong>,"
        ]
        market_cap_phrase = random.choice(market_cap_phrase_options)

        # --- Enhanced Site Specific Variations ---
        report_purpose_intro = ""
        if "finances forecast" in site_name:
            report_purpose_intro = random.choice([
                (
                    f"This <strong>Finances Forecast</strong> analysis delves into {company_name}'s ({ticker}) potential financial trajectory through 2025-2026. "
                    f"Our objective is to project future performance by examining quantitative forecasts, underlying financial health (see Financial Health section), key valuation metrics (discussed under Valuation), and potential catalysts derived from its business profile. "
                    f"We aim to balance model-driven predictions with fundamental realities."
                ),
                (
                    f"In this <strong>Finances Forecast</strong> report, we explore the likely financial path for {company_name} ({ticker}) over the next year or two. "
                    f"By analyzing forecasts, financial stability (refer to Financial Health), valuation (see Valuation section), and business drivers, we aim to provide a grounded outlook on its potential performance."
                )
            ])
        elif "radar stocks" in site_name:
             report_purpose_intro = random.choice([
                (
                    f"Welcome to the <strong>Radar Stocks</strong> technical deep dive on {company_name} ({ticker}). "
                    f"This report focuses on identifying actionable trading insights by scrutinizing technical indicators (see Technical Analysis), current price momentum ({trend_context}), market sentiment, and key support/resistance levels. "
                    f"Our goal is to highlight potential short-term opportunities and risks based on price action analysis."
                ),
                (
                    f"This <strong>Radar Stocks</strong> analysis concentrates on the technicals for {company_name} ({ticker}). "
                    f"We're looking for trading signals by examining indicators (view Technical Analysis), price trends ({trend_context}), sentiment, and crucial price levels. The aim is to spot near-term trading possibilities and hazards through chart patterns and data."
                )
             ])
        elif "bernini capital" in site_name:
            report_purpose_intro = random.choice([
                (
                    f"This <strong>Bernini Capital</strong> assessment provides a comprehensive evaluation of {company_name} ({ticker}) from a long-term, value-oriented perspective. "
                    f"We meticulously analyze its fundamental strength, including financial health (debt, liquidity), profitability trends (margins, ROE), cash flow generation (see Financial Health/Efficiency), and valuation attractiveness relative to peers and intrinsic estimates. Dividend sustainability (see Dividends section) is also a key consideration."
                ),
                (
                    f"Our <strong>Bernini Capital</strong> review offers an in-depth look at {company_name} ({ticker}) with a focus on long-term value. "
                    f"We carefully assess its core financial stability, profit generation, cash flow (refer to Financial Health/Efficiency), and how its valuation stacks up against benchmarks. Dividend reliability (check Dividends section) is also examined."
                )
            ])
        else: # Default (Balanced Approach)
            report_purpose_intro = random.choice([
                 (
                     f"This report offers a multi-faceted analysis of {company_name} ({ticker}), integrating technical signals, fundamental data, and forward-looking forecasts. "
                     f"The aim is to provide investors with a balanced perspective on the stock's current market standing, potential risks (see Risk Factors), and future performance outlook."
                 ),
                 (
                    f"Here, we present a combined analysis of {company_name} ({ticker}), blending technical charts, fundamental metrics, and future projections. "
                    f"Our goal is to offer a well-rounded view of its market position, associated risks (review Risk Factors), and what the future might hold."
                 )
            ])

        intro_base = (
            f"<p>{intro_phrase} {price_phrase} reflecting {dynamic_sentiment_text}. "
            f"{trend_context} {market_cap_phrase} {ticker} represents a significant player in its field.</p>"
            f"<p>{report_purpose_intro}</p>"
        )

        summary = profile_data.get('Summary', None)
        # Ensure summary is treated as string
        summary_str = str(summary) if summary is not None else ''
        if summary_str and summary_str != 'No summary available.':
            # Add context based on summary length or keywords if desired
            summary_focus = random.choice([
                "Key aspects of its operations include:",
                "Its business model centers around:",
                "The company primarily focuses on:",
                "Core activities involve:",
                "Operationally, the company is engaged in:"
                ])
            intro_base += f"<h4>Company Snapshot</h4><p><i>{summary_focus}</i> {summary_str[:400]}{'...' if len(summary_str) > 400 else ''}</p>" # Limit length

        return intro_base
    except Exception as e:
        return _generate_error_html("Introduction", str(e))


def generate_metrics_summary_html(ticker, rdata):
    """Generates the key metrics summary box with enhanced site-specific interpretations and context."""
    try:
        site_name = rdata.get('site_name', '').lower()
        current_price = rdata.get('current_price')
        sma50 = rdata.get('sma_50')
        sma200 = rdata.get('sma_200')
        volatility = rdata.get('volatility') # Assumed 30d annualized
        sentiment = rdata.get('sentiment', 'Neutral') # Default to Neutral
        forecast_1y = rdata.get('forecast_1y')
        overall_pct_change_val = _safe_float(rdata.get('overall_pct_change'), default=0.0)
        period_label = rdata.get('period_label', 'Period')
        forecast_1m = rdata.get('forecast_1m') # Get 1-month forecast

        # --- Formatting (With NA handling using format_html_value) ---
        current_price_fmt = format_html_value(current_price, 'currency')
        forecast_1m_fmt = format_html_value(forecast_1m, 'currency')
        forecast_1y_fmt = format_html_value(forecast_1y, 'currency')
        overall_pct_change_fmt = f"{overall_pct_change_val:+.1f}%"
        volatility_fmt = format_html_value(volatility, 'percent_direct', 1)
        sma50_fmt = format_html_value(sma50, 'currency')
        sma200_fmt = format_html_value(sma200, 'currency')

        forecast_1y_icon = get_icon('up' if overall_pct_change_val > 1 else ('down' if overall_pct_change_val < -1 else 'neutral'))

        # Use _safe_float for comparisons
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

        sentiment_str = str(sentiment) # Ensure string for checks
        sentiment_icon = get_icon('up' if 'Bullish' in sentiment_str else ('down' if 'Bearish' in sentiment_str else 'neutral'))

        # --- Base Grid HTML ---
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
        grid_html += "</div>" # Close metrics-summary

        # --- Site Specific Interpretations (with random variations) ---
        narrative = ""
        forecast_direction = "flat potential"
        if overall_pct_change_val > 1: forecast_direction = "potential upside"
        elif overall_pct_change_val < -1: forecast_direction = "potential downside"

        # Random phrasing options for narrative components
        phrase_forecast_intro = random.choice([
            f"The quantitative outlook points towards a 1-year target of {forecast_1y_fmt}, implying",
            f"Our model projects a 1-year average price near {forecast_1y_fmt}, suggesting",
            f"Looking ahead one year, the forecast indicates a target around {forecast_1y_fmt}, representing"
        ])
        phrase_forecast_near = random.choice([
            f"The shorter-term {period_label} forecast of {forecast_1m_fmt} provides a nearer milestone.",
            f"As a closer benchmark, the {period_label} projection is {forecast_1m_fmt}.",
            f"In the near term ({period_label}), the model anticipates a price around {forecast_1m_fmt}."
        ])
        phrase_factors_depend = random.choice([
            "However, achieving these targets depends on factors discussed later, such as sustained growth (see Profitability) and market conditions.",
            "Reaching these projected levels is contingent upon elements examined elsewhere, including ongoing growth (view Profitability) and the broader market environment.",
            "Realization of these forecasts relies on various inputs detailed further, like consistent growth (refer to Profitability) and prevailing market dynamics."
        ])
        phrase_tech_context = random.choice([
             f"The current {sentiment_str} technical stance ({price_vs_sma50_text}, {price_vs_sma200_text}) and recent volatility ({volatility_fmt}) shape the immediate path.",
             f"Presently, the technical picture ({sentiment_str}, {price_vs_sma50_text}, {price_vs_sma200_text}) combined with volatility ({volatility_fmt}) sets the near-term stage.",
             f"The immediate trajectory is influenced by the technical sentiment ({sentiment_str}), price vs MAs ({price_vs_sma50_text}, {price_vs_sma200_text}), and observed volatility ({volatility_fmt})."
        ])
        phrase_trading_focus = random.choice([
            f"From a trading perspective, the technical landscape currently shows a <strong>{sentiment_str}</strong> bias.",
            f"For traders, the immediate technical setup presents a <strong>{sentiment_str}</strong> sentiment.",
            f"Technically speaking, the current market leans towards a <strong>{sentiment_str}</strong> view for traders."
        ])
        phrase_ma_importance = random.choice([
            f"Price ({current_price_fmt}) is {price_vs_sma50_text} ({sma50_fmt}) and {price_vs_sma200_text} ({sma200_fmt}) – critical levels watched by trend followers.",
            f"The stock's position ({current_price_fmt}) relative to its 50-day ({sma50_fmt} - {price_vs_sma50_text}) and 200-day ({sma200_fmt} - {price_vs_sma200_text}) averages is key for trend analysis.",
            f"Observing the price ({current_price_fmt}) versus the SMAs ({sma50_fmt} - {price_vs_sma50_text}; {sma200_fmt} - {price_vs_sma200_text}) is crucial for identifying the prevailing trend."
        ])
        phrase_volatility_note = random.choice([
            f"Recent volatility stands at {volatility_fmt}, suggesting potential for price swings.",
            f"The measured volatility of {volatility_fmt} indicates the recent degree of price fluctuation.",
            f"Price movement intensity, measured by volatility, is currently {volatility_fmt}."
        ])
        phrase_trader_priority = random.choice([
            f"While the model projects a 1-year target of {forecast_1y_fmt}, active traders should prioritize confirming technical signals (see TA section) and managing risk around the near-term ({period_label}) forecast of {forecast_1m_fmt}.",
            f"Although the long-term forecast is {forecast_1y_fmt}, traders must focus on validating technical entries/exits (refer to TA section) and controlling risk, keeping the {period_label} forecast ({forecast_1m_fmt}) in mind.",
            f"The 1-year projection ({forecast_1y_fmt}) offers context, but traders need to emphasize confirming technical setups (view TA section) and risk mitigation, considering the {period_label} outlook ({forecast_1m_fmt})."
        ])
        phrase_valuation_context = random.choice([
            f"Key metrics provide context for {ticker}'s current valuation.",
            f"These summary metrics help frame {ticker}'s present market valuation.",
            f"Understanding {ticker}'s valuation starts with these key data points."
        ])
        phrase_ma_context_long = random.choice([
             f"The price ({current_price_fmt}) relative to its medium-term (SMA50: {sma50_fmt} - {price_vs_sma50_text}) and long-term (SMA200: {sma200_fmt} - {price_vs_sma200_text}) trends is a starting point.",
             f"Comparing the current price ({current_price_fmt}) to its 50-day ({sma50_fmt} - {price_vs_sma50_text}) and 200-day ({sma200_fmt} - {price_vs_sma200_text}) moving averages offers initial trend perspective.",
             f"The relationship between price ({current_price_fmt}) and its key SMAs (50-day: {sma50_fmt} - {price_vs_sma50_text}; 200-day: {sma200_fmt} - {price_vs_sma200_text}) provides basic trend information."
        ])
        phrase_long_term_focus = random.choice([
            f"While models estimate a 1-year average price near {forecast_1y_fmt}, long-term investment decisions hinge more critically on fundamental strength (financial health, profitability) and whether the current price offers an adequate margin of safety relative to intrinsic value.",
            f"Although the 1-year forecast targets {forecast_1y_fmt}, enduring investment choices depend more significantly on core fundamentals (like financial stability and earnings power) and if the price represents good value compared to its estimated worth.",
            f"The model's 1-year outlook ({forecast_1y_fmt}) is one piece of data, but sustainable investing prioritizes fundamental quality (health, profits) and ensuring the purchase price is attractive relative to the company's intrinsic value."
        ])
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


        if "finances forecast" in site_name:
            narrative = f"{phrase_forecast_intro} <strong>{forecast_direction} ({overall_pct_change_fmt})</strong> from the current price, based on our model's inputs. {phrase_forecast_near} {phrase_factors_depend} {phrase_tech_context}"
        elif "radar stocks" in site_name:
            narrative = f"{phrase_trading_focus} {phrase_ma_importance} {phrase_volatility_note} {phrase_trader_priority}"
        elif "bernini capital" in site_name:
             narrative = f"{phrase_valuation_context} {phrase_ma_context_long} Volatility is {volatility_fmt}. {phrase_long_term_focus}"
        else: # Default
            narrative = f"{phrase_default_intro} {phrase_default_forecast} {phrase_default_tech} {phrase_default_vol} {phrase_default_outro}"

        return grid_html + f'<div class="narrative"><p>{narrative}</p></div>'
    except Exception as e:
        return _generate_error_html("Metrics Summary", str(e))

# ... (generate_detailed_forecast_table_html, generate_company_profile_html, generate_technical_analysis_summary_html remain largely the same as they are heavily data-driven, but minor phrasing variations could be added if needed)

# --- Metrics Sections (Valuation, Shares, Health, Efficiency, Profit, Dividends, Price Stats, Short Selling, Analyst) ---
# These primarily display data tables with a narrative intro. We can vary the narrative intros.

def generate_metrics_section_content(metrics):
    """Helper to generate table body content for metrics sections (Robust NA handling)."""
    # (Code remains the same as V3)
    rows = ""
    try:
        if isinstance(metrics, dict):
            # Iterate safely, format each value, skip if format result is "N/A"
            row_parts = []
            for k, v in metrics.items():
                # Decide format type based on key name heuristics (can be expanded)
                format_type = "string" # Default
                k_lower = str(k).lower()
                if "date" in k_lower: format_type = "date"
                elif "yield" in k_lower or "ratio" in k_lower or "beta" in k_lower: format_type = "ratio"
                elif "margin" in k_lower or "ownership" in k_lower or "growth" in k_lower or "%" in k_lower: format_type = "percent_direct"
                elif "price" in k_lower or "value" in k_lower or "dividend rate" in k_lower: format_type = "currency"
                elif "volume" in k_lower or "shares" in k_lower or "employees" in k_lower: format_type = "integer"
                elif "market cap" in k_lower: format_type = "large_number"

                formatted_v = format_html_value(v, format_type)
                if formatted_v != "N/A":
                    row_parts.append(f"<tr><td>{str(k)}</td><td>{formatted_v}</td></tr>") # Ensure key is string

            rows = "".join(row_parts)

        if not rows:
            # Provide a more informative message if no valid data was found
            rows = "<tr><td colspan='2' style='text-align: center; font-style: italic;'>No displayable data available for this category.</td></tr>"

        return f"""<div class="table-container">
                       <table class="metrics-table">
                           <tbody>{rows}</tbody>
                       </table>
                   </div>"""
    except Exception as e:
        logging.error(f"Error generating metrics table content: {e}")
        # Return an error message within the table structure
        return f"""<div class="table-container">
                       <table class="metrics-table">
                           <tbody>
                               <tr><td colspan='2' style='text-align: center; color: red;'>Error displaying metric data.</td></tr>
                           </tbody>
                       </table>
                   </div>"""

# Example: Adding variation to generate_total_valuation_html narrative
def generate_total_valuation_html(ticker, rdata):
    """Generates Total Valuation section with enhanced site-specific narrative focus."""
    try:
        site_name = rdata.get('site_name', '').lower()
        valuation_data = rdata.get('total_valuation_data')
        if not isinstance(valuation_data, dict):
            valuation_data = {}
            logging.warning("total_valuation_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(valuation_data)

        # --- Enhanced Site Specific Narrative ---
        narrative = ""
        ev_ttm = format_html_value(valuation_data.get('Enterprise Value (EV TTM)'), 'large_number')
        ev_rev = format_html_value(valuation_data.get('EV/Revenue (TTM)'), 'ratio')
        ev_ebitda = format_html_value(valuation_data.get('EV/EBITDA (TTM)'), 'ratio')
        next_earn_date = format_html_value(valuation_data.get('Next Earnings Date'), 'date')
        ex_div_date = format_html_value(valuation_data.get('Ex-Dividend Date'), 'date')

        # Shared context (with variations)
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

        if "finances forecast" in site_name:
            narrative_options = [
                (
                    f"{ev_explanation} {ratio_explanation} These metrics are crucial inputs for assessing valuation relative to operational scale and projecting potential future enterprise value based on growth forecasts. "
                    f"Upcoming events like earnings (next estimated: {next_earn_date}) can significantly impact these ratios and the underlying forecast assumptions."
                ),
                (
                    f"{ev_explanation} {ratio_explanation} Understanding these total valuation figures is vital for comparing {ticker} to its potential and for building reliable forecasts. "
                    f"Keep an eye on the next earnings date ({next_earn_date}), as results can shift these valuation metrics and forecast inputs."
                )
            ]
            narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
            narrative_options = [
                (
                    f"While market cap drives price, understanding {ticker}'s total valuation context ({ev_explanation}) is useful. {ratio_explanation} "
                    f"While not primary short-term trading signals, extreme levels in EV/Revenue or EV/EBITDA compared to peers might indicate broader sentiment shifts. "
                    f"Traders should also note potential price adjustments around the Ex-Dividend Date ({ex_div_date})."
                ),
                (
                     f"{ev_explanation} {ratio_explanation} Though less critical for immediate trades, these EV-based ratios offer background sentiment context. Significant deviations from norms could hint at underlying shifts. "
                     f"Also, be aware of the Ex-Dividend Date ({ex_div_date}) for potential price impacts."
                )
            ]
            narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
            narrative_options = [
                (
                    f"Assessing total valuation is fundamental to value investing. {ev_explanation} {ratio_explanation} "
                    f"Comparing {ticker}'s EV/Revenue and EV/EBITDA ratios against its historical range {get_icon('history')} and industry peers {get_icon('peer')} is essential for determining if the market currently offers an attractive entry point based on the company's overall operational size and profitability."
                ),
                (
                    f"For value investors, understanding the complete picture via EV is key. {ev_explanation} {ratio_explanation} "
                    f"Benchmarking these EV multiples against past performance {get_icon('history')} and competitors {get_icon('peer')} helps gauge if {ticker} is currently priced attractively relative to its operational footprint and earnings power."
                )
            ]
            narrative = random.choice(narrative_options)
        else: # Default
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

# --- Apply similar narrative variation logic to other metric sections ---
# generate_share_statistics_html
# generate_valuation_metrics_html
# generate_financial_health_html
# generate_financial_efficiency_html
# generate_profitability_growth_html
# generate_dividends_shareholder_returns_html
# generate_stock_price_statistics_html
# generate_short_selling_info_html
# generate_analyst_insights_html
# (Implementation omitted for brevity, but follow the pattern above:
#  1. Define multiple phrasing options for sentences/concepts.
#  2. Use random.choice() to select one.
#  3. Integrate these choices into the site-specific narrative logic.)


# --- Conclusion, FAQ, Disclaimer (Enhanced & Wrapped) ---

def generate_conclusion_outlook_html(ticker, rdata):
    """Generates the Conclusion and Outlook section with enhanced synthesis and site variations."""
    try:
        site_name = rdata.get('site_name', '').lower()

        # --- Gather Data (with safe access and type checks) ---
        # (Data gathering remains the same as V3)
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
        macd_hist = _safe_float(detailed_ta_data.get('MACD_Hist'))
        bb_lower = _safe_float(detailed_ta_data.get('BB_Lower')); bb_upper = _safe_float(detailed_ta_data.get('BB_Upper'))
        support = _safe_float(detailed_ta_data.get('Support_30D')); resistance = _safe_float(detailed_ta_data.get('Resistance_30D'))
        forecast_1y = _safe_float(rdata.get('forecast_1y'))
        overall_pct_change = _safe_float(rdata.get('overall_pct_change'), default=0.0)
        roe = _safe_float(health_data.get('Return on Equity (ROE TTM)'))
        debt_equity = _safe_float(health_data.get('Debt/Equity (MRQ)'))
        op_cash_flow = _safe_float(health_data.get('Operating Cash Flow (TTM)')) # Convert to float for +/- check
        fwd_pe = _safe_float(valuation_data.get('Forward P/E'))
        peg_ratio = _safe_float(valuation_data.get('PEG Ratio'))
        pfcf_ratio = _safe_float(valuation_data.get('Price/FCF (TTM)'))
        analyst_rec = analyst_data.get('Recommendation', 'N/A') # Keep as string
        mean_target = _safe_float(analyst_data.get('Mean Target Price'))
        fwd_yield = _safe_float(dividend_data.get('Dividend Yield (Fwd)'))
        payout_ratio = _safe_float(dividend_data.get('Payout Ratio'))
        rev_growth = _safe_float(profit_data.get('Revenue Growth (YoY)'))
        earn_growth = _safe_float(profit_data.get('Earnings Growth (YoY)'))
        rsi_divergence_bearish = rdata.get('rsi_divergence_bearish', False)
        rsi_divergence_bullish = rdata.get('rsi_divergence_bullish', False)
        roe_trend = rdata.get('roe_trend', None)
        debt_equity_trend = rdata.get('debt_equity_trend', None)
        margin_trend = rdata.get('margin_trend', None)
        growth_trend = rdata.get('growth_trend', None)

        # --- Intermediate Calculations/Interpretations for Summary Points ---
        # (Calculations remain the same as V3)
        st_points_data = {} # Short-Term / Technical
        lt_points_data = {} # Longer-Term / Fundamental & Forecast

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

        macd_text = "Mixed/Crossing"; macd_icon = get_icon('neutral')
        if macd_line is not None and macd_signal is not None:
             if macd_line > macd_signal: macd_text = "Bullish Crossover"; macd_icon = get_icon('up')
             elif macd_line < macd_signal: macd_text = "Bearish Crossover"; macd_icon = get_icon('down')
        else: macd_text = "N/A"
        st_points_data['macd'] = {'label': 'Momentum (MACD)', 'value': macd_text, 'icon': macd_icon}

        bb_text = "Within Bands"; bb_icon = get_icon('neutral')
        if current_price is not None and bb_lower is not None and bb_upper is not None:
            if current_price > bb_upper: bb_text = "Above Upper Band"; bb_icon = get_icon('warning')
            elif current_price < bb_lower: bb_text = "Below Lower Band"; bb_icon = get_icon('positive')
        else: bb_text = "N/A"
        st_points_data['bbands'] = {'label': 'Volatility (BBands)', 'value': bb_text, 'icon': bb_icon}

        sr_text = "N/A"
        if support is not None and resistance is not None:
            sr_text = f"~{format_html_value(support,'currency')} / ~{format_html_value(resistance,'currency')}"
        st_points_data['sr'] = {'label': 'Support / Resistance (30d)', 'value': sr_text, 'icon': get_icon('chart')}

        forecast_icon = get_icon('neutral'); forecast_text = "N/A"
        if forecast_1y is not None:
            forecast_icon = get_icon('up' if overall_pct_change > 1 else ('down' if overall_pct_change < -1 else 'neutral'))
            forecast_text = f"~{overall_pct_change:+.1f}% avg. change to ≈{format_html_value(forecast_1y, 'currency')}"
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

        health_text = "Moderate"; health_icon = get_icon('neutral'); fundamental_strength_summary = "Moderate"
        op_cf_pos = op_cash_flow is not None and op_cash_flow > 0
        roe_fmt = format_html_value(roe, 'percent_direct'); de_fmt = format_html_value(debt_equity, 'ratio'); ocf_fmt = format_html_value(op_cash_flow, 'large_number')

        if roe is not None and debt_equity is not None and op_cash_flow is not None:
            if roe > 15 and debt_equity < 1.5 and op_cf_pos: fundamental_strength_summary = "Strong"; health_icon = get_icon('up'); health_text = f"Strong (ROE: {roe_fmt}, D/E: {de_fmt}, +OCF)"
            elif roe < 5 or debt_equity > 2.5 or not op_cf_pos: fundamental_strength_summary = "Weak"; health_icon = get_icon('down'); health_text = f"Potential Weakness (ROE: {roe_fmt}, D/E: {de_fmt}, OCF: {ocf_fmt})"
            else: health_text = f"Moderate (ROE: {roe_fmt}, D/E: {de_fmt}, +OCF)"
        elif not op_cf_pos and op_cash_flow is not None: # Highlight negative cash flow
             fundamental_strength_summary = "Weak"; health_icon = get_icon('down'); health_text = f"Concern: Negative Op Cash Flow ({ocf_fmt})"
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
             if growth_trend: growth_text += f", Trend: {str(growth_trend).lower()}"
        else: growth_text = f"N/A (Rev: {rg_fmt}, Earn: {eg_fmt})"
        lt_points_data['growth'] = {'label': 'Recent Growth (YoY)', 'value': growth_text, 'icon': growth_icon}

        analyst_text = "N/A"; analyst_icon = get_icon('neutral')
        if analyst_rec != 'N/A':
             analyst_icon = get_icon('up' if 'Buy' in analyst_rec else ('down' if 'Sell' in analyst_rec or 'Underperform' in analyst_rec else 'neutral'))
             mean_target_fmt = format_html_value(mean_target, 'currency')
             analyst_text = f"{analyst_rec} (Target: {mean_target_fmt})"
        lt_points_data['analyst'] = {'label': 'Analyst Consensus', 'value': analyst_text, 'icon': analyst_icon}

        if fwd_yield is not None and fwd_yield > 0.01:
            payout_fmt = format_html_value(payout_ratio, 'percent_direct')
            payout_context = f"(Payout: {payout_fmt})" if payout_fmt != 'N/A' else ""
            dividend_text = f"{format_html_value(fwd_yield, 'percent_direct')} Yield {payout_context}"; dividend_icon = get_icon('dividend')
            lt_points_data['dividend'] = {'label': 'Dividend', 'value': dividend_text, 'icon': dividend_icon}

        # --- Site Specific Point Selection and Ordering ---
        # (Logic remains the same as V3)
        st_keys_default = ['sentiment', 'trend', 'rsi', 'macd', 'bbands', 'sr']
        lt_keys_default = ['forecast', 'health', 'valuation', 'growth', 'analyst']
        if 'dividend' in lt_points_data: lt_keys_default.append('dividend')

        st_keys = st_keys_default; lt_keys = lt_keys_default

        if "finances forecast" in site_name:
            st_keys = ['sentiment', 'trend', 'rsi', 'macd', 'sr']
            lt_keys = ['forecast', 'growth', 'valuation', 'health', 'analyst']
            if 'dividend' in lt_points_data: lt_keys.append('dividend')
        elif "radar stocks" in site_name:
            st_keys = ['sentiment', 'trend', 'rsi', 'macd', 'bbands', 'sr', 'volume'] # Add volume if available later
            if 'volume' not in st_points_data: # Placeholder check if volume added
                 st_keys = [k for k in st_keys if k != 'volume']
            lt_keys = ['forecast', 'analyst', 'valuation']
        elif "bernini capital" in site_name:
            st_keys = ['trend', 'sentiment', 'rsi', 'sr']
            lt_keys = ['health', 'valuation', 'dividend', 'growth', 'forecast', 'analyst']
            if 'dividend' not in lt_points_data: # Ensure dividend is removed if not present
                 lt_keys = [k for k in lt_keys if k != 'dividend']


        st_keys = [k for k in st_keys if k in st_points_data and st_points_data[k]['value'] != 'N/A']
        lt_keys = [k for k in lt_keys if k in lt_points_data and lt_points_data[k]['value'] != 'N/A']


        # --- Generate HTML Lists ---
        def generate_list_items(keys, data_dict):
            # (Function remains the same as V3)
            html = ""
            for key in keys:
                item = data_dict.get(key)
                if item: # Should exist based on filtering above
                     value_str = str(item['value']) # Ensure string
                     # Prevent excessive length in summary points
                     if len(value_str) > 150: value_str = value_str[:147] + "..."
                     html += f"<li><span class='icon'>{item['icon']}</span><span>{item['label']}: <strong>{value_str}</strong></span></li>"
            if not html:
                 html = "<li>No specific data points available for this perspective.</li>"
            return html

        short_term_html = generate_list_items(st_keys, st_points_data)
        long_term_html = generate_list_items(lt_keys, lt_points_data)

        # --- Final HTML Structure (columns) ---
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

        # --- Enhanced Overall Assessment (Varies significantly by site focus with more random choices) ---
        overall_assessment = ""
        forecast_direction_summary = "relatively flat"
        forecast_1y_fmt = format_html_value(forecast_1y, 'currency')
        if overall_pct_change > 5: forecast_direction_summary = f"potential upside ({overall_pct_change:+.1f}%)"
        elif overall_pct_change < -5: forecast_direction_summary = f"potential downside ({overall_pct_change:+.1f}%)"

        growth_narrative = lt_points_data.get('growth',{}).get('value','N/A growth')
        valuation_narrative = lt_points_data.get('valuation',{}).get('value','N/A valuation')
        sentiment_narrative = st_points_data.get('sentiment',{}).get('value','N/A sentiment')
        trend_narrative = st_points_data.get('trend',{}).get('value','N/A trend')
        health_narrative = lt_points_data.get('health',{}).get('value','N/A health')
        analyst_narrative = lt_points_data.get('analyst',{}).get('value','N/A Analyst')
        dividend_narrative = lt_points_data.get('dividend',{}).get('value','N/A')

        # Random phrasing variations (Expanded)
        phrase_link_tech_fund_options = [
            "Bridging the technical picture with the fundamental outlook,",
            "Synthesizing the short-term signals with the longer-term view,",
            "Considering both technical momentum and fundamental drivers,",
            "Integrating the near-term chart patterns with the underlying business health,",
            "Balancing the current technical stance against the fundamental prospects,"
        ]
        phrase_investor_consider_options = [
            "Investors should weigh these factors against",
            "Careful consideration of these points relative to",
            "Decision-making should factor in these elements against",
            "It's crucial to evaluate these findings in the context of",
            "These observations should be assessed alongside"
        ]
        phrase_risks_horizon_options = [
            "identified risks and their individual investment horizon.",
            "their personal risk tolerance and investment timeline.",
            "the potential risks outlined earlier and their strategic goals.",
            "specific risk factors mentioned previously and their own financial objectives.",
            "the inherent market risks and their long-term investment strategy."
        ]
        phrase_forecast_intro_options = [
            f"The analysis suggests a 1-year forecast indicating",
            f"Looking ahead, the model points towards",
            f"Our 1-year projection anticipates",
            f"The forward-looking model estimates"
        ]
        phrase_supported_by_options = [ "supported", "underpinned", "bolstered", "reinforced", "justified" ]
        phrase_recent_options = [ "recent", "observed", "current", "latest", "present" ]
        phrase_however_options = [ "However,", "Nevertheless,", "Despite this,", "On the other hand,", "Conversely," ]
        phrase_near_term_hurdles_options = [ "potential near-term hurdles", "near-term uncertainty", "a complex short-term path", "some immediate challenges", "a period of consolidation" ]
        phrase_achieving_forecast_options = [
            f"Achieving the forecast likely hinges on maintaining {fundamental_strength_summary.lower()} financial health and executing on growth initiatives.",
            f"Realizing this projection probably depends on sustaining {fundamental_strength_summary.lower()} fundamentals and delivering on growth plans.",
            f"Meeting the forecast target requires continued {fundamental_strength_summary.lower()} financial stability and successful growth execution."
        ]
        phrase_trading_standpoint_options = [
            "From a trading standpoint,", "For active traders,", "From a short-term perspective,", "Technically focused traders might note,"
        ]
        phrase_technicals_lean_options = [ "technicals currently lean", "short-term setup appears", "immediate chart picture suggests", "current technical bias is" ]
        phrase_momentum_vol_suggest_options = [ "suggest", "point towards", "indicate", "imply" ]
        phrase_potential_for_options = [ "potential for continued choppiness", "opportunities for range trading", "a need for confirmation signals", "the possibility of further consolidation", "a requirement for clear directional signals" ]
        phrase_key_levels_options = [ "Key levels to watch are", "Crucial price zones include", "Monitor support/resistance near", "Important areas on the chart are around" ]
        phrase_trader_focus_options = [
             "traders must prioritize real-time price action, volume confirmation, and risk management.",
             "the focus for traders remains on live price movements, validating volume, and strict risk control.",
             "active trading demands attention to actual price behavior, volume signals, and disciplined risk strategies."
        ]
        phrase_fundamental_perspective_options = [
            "From a fundamental value perspective,", "For long-term value investors,", "Assessing the underlying business value,", "From an intrinsic value standpoint,"
        ]
        phrase_presents_profile_options = [ "presents a", "shows a", "exhibits a", "demonstrates a" ]
        phrase_dividend_mention_options = [ f"The dividend yield is currently {dividend_narrative}.", f"Regarding dividends, the yield stands at {dividend_narrative}.", f"{ticker}'s dividend offers a {dividend_narrative} yield." ] if 'dividend' in lt_points_data else [ "Dividends are not a major factor currently.", "The company does not offer a significant dividend.", "Shareholder returns primarily rely on factors other than dividends." ]
        phrase_long_term_case_options = [
            "The long-term investment case rests on the sustainability of its fundamentals, competitive advantages, and whether the current price offers an adequate margin of safety relative to intrinsic value.",
            "A durable investment thesis depends on the resilience of its core business, its edge over competitors, and an attractive entry price compared to its true worth.",
            "Building a long-term position requires confidence in the company's fundamentals, its market position, and buying at a price that provides sufficient margin for error."
        ]
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


        if "finances forecast" in site_name:
            overall_assessment = (
                f"{random.choice(phrase_forecast_intro_options)} <strong>{forecast_direction_summary}</strong> towards ≈{forecast_1y_fmt}. "
                f"This projection appears {random.choice(phrase_supported_by_options)} by {random.choice(phrase_recent_options)} {growth_narrative} and a valuation considered {valuation_narrative}. "
                f"{random.choice(phrase_however_options)} the {sentiment_narrative} technical sentiment and {trend_narrative} indicate {random.choice(phrase_near_term_hurdles_options)}. "
                f"{random.choice(phrase_achieving_forecast_options)} {random.choice(phrase_investor_consider_options)} {random.choice(phrase_risks_horizon_options)}"
            )
        elif "radar stocks" in site_name:
             macd_narrative = st_points_data.get('macd',{}).get('value','N/A MACD')
             rsi_narrative = st_points_data.get('rsi',{}).get('value','N/A RSI')
             bbands_narrative = st_points_data.get('bbands',{}).get('value','N/A BBands')
             sr_narrative = st_points_data.get('sr',{}).get('value','N/A')
             overall_assessment = (
                 f"{random.choice(phrase_trading_standpoint_options)} {ticker}'s {random.choice(phrase_technicals_lean_options)} <strong>{sentiment_narrative}</strong>, primarily driven by {trend_narrative} and {macd_narrative}. "
                 f"Momentum ({rsi_narrative}) and volatility ({bbands_narrative}) {random.choice(phrase_momentum_vol_suggest_options)} {random.choice(phrase_potential_for_options)}. "
                 f"{random.choice(phrase_key_levels_options)} {sr_narrative}. While the longer-term forecast ({forecast_direction_summary}) and analyst views ({analyst_narrative}) provide context, {random.choice(phrase_trader_focus_options)}"
             )
        elif "bernini capital" in site_name:
            overall_assessment = (
                f"{random.choice(phrase_fundamental_perspective_options)} {ticker} {random.choice(phrase_presents_profile_options)} a <strong>{fundamental_strength_summary.lower()}</strong> financial health profile ({health_narrative}) and a valuation currently assessed as {valuation_narrative}. "
                f"{random.choice(phrase_dividend_mention_options)} {random.choice(phrase_recent_options)} growth stands at {growth_narrative}. {random.choice(phrase_link_tech_fund_options)} the {sentiment_narrative} technicals offer context on current market perception. "
                f"{random.choice(phrase_long_term_case_options)} {random.choice(phrase_investor_consider_options)} {random.choice(phrase_risks_horizon_options)}"
             )
        else: # Default
            overall_assessment = (
                f"{random.choice(phrase_default_synthesis_options)} "
                f"{random.choice(phrase_default_valuation_options)} {random.choice(phrase_default_forecast_summary_options)} "
                f"{random.choice(phrase_investor_consider_options)} {random.choice(phrase_risks_horizon_options)}"
            )

        # Add the disclaimer with slight variation possibility
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


# --- START: Code for Missing HTML Component Functions ---

def generate_detailed_forecast_table_html(ticker, rdata):
    """Generates the detailed forecast table with enhanced site-specific commentary and insights."""
    try:
        site_name = rdata.get('site_name', '').lower()
        monthly_forecast_table_data = rdata.get('monthly_forecast_table_data', pd.DataFrame())
        current_price = _safe_float(rdata.get('current_price'))
        current_price_fmt = format_html_value(current_price, 'currency')
        forecast_time_col = rdata.get('time_col', 'Period') # Should be Period (e.g., YYYY-MM)
        period_label = rdata.get('period_label', 'Period') # e.g., 'Monthly', 'Quarterly'
        table_rows = ""
        min_price_overall = None; max_price_overall = None
        first_range_str = "N/A"; last_range_str = "N/A"
        range_trend_comment = ""
        narrative_intro = "" # Site specific intro paragraph

        # --- Calculations (Improved safety and ROI/Action logic) ---
        # Ensure data is DataFrame and not empty
        if isinstance(monthly_forecast_table_data, pd.DataFrame) and \
           not monthly_forecast_table_data.empty and \
           'Low' in monthly_forecast_table_data.columns and \
           'High' in monthly_forecast_table_data.columns:

            # Ensure numeric types before calculation, making a copy to avoid SettingWithCopyWarning
            forecast_df = monthly_forecast_table_data.copy()
            # Ensure the Period column is treated as string for display
            if forecast_time_col in forecast_df.columns:
                forecast_df[forecast_time_col] = forecast_df[forecast_time_col].astype(str)

            forecast_df['Low'] = pd.to_numeric(forecast_df['Low'], errors='coerce')
            forecast_df['High'] = pd.to_numeric(forecast_df['High'], errors='coerce')
            forecast_df.dropna(subset=['Low', 'High'], inplace=True)

            if not forecast_df.empty:
                min_price_overall = forecast_df['Low'].min()
                max_price_overall = forecast_df['High'].max()
                forecast_df['RangeWidth'] = forecast_df['High'] - forecast_df['Low']
                first_range_width = forecast_df['RangeWidth'].iloc[0]
                last_range_width = forecast_df['RangeWidth'].iloc[-1]

                first_row = forecast_df.iloc[0]; last_row = forecast_df.iloc[-1]
                first_range_str = f"{format_html_value(first_row['Low'], 'currency')} – {format_html_value(first_row['High'], 'currency')}"
                last_range_str = f"{format_html_value(last_row['Low'], 'currency')} – {format_html_value(last_row['High'], 'currency')}"

                # More nuanced range trend comment
                width_change_ratio = last_range_width / first_range_width if first_range_width and first_range_width != 0 else 1

                range_trend_options = {
                    'widening': [
                        f"Note the significant widening in the projected price range (from {first_range_str} to {last_range_str}), suggesting increasing forecast uncertainty over time.",
                        f"Observe how the forecast range expands considerably (from {first_range_str} to {last_range_str}), indicating greater potential price variability further out.",
                        f"The model's confidence band widens notably ({first_range_str} initially vs. {last_range_str} finally), pointing to higher long-term uncertainty."
                        ],
                    'narrowing': [
                        f"Observe the narrowing projected price range (from {first_range_str} to {last_range_str}), indicating potentially stabilizing expectations or higher model confidence further out.",
                        f"The forecast uncertainty appears to decrease over time, as seen by the tightening price range ({first_range_str} vs. {last_range_str}).",
                        f"A narrowing forecast band ({first_range_str} to {last_range_str}) might suggest the model anticipates more predictable conditions later."
                        ],
                    'stable': [
                        f"The projected price range remains relatively consistent (from {first_range_str} to {last_range_str}), implying stable forecast uncertainty.",
                        f"Forecast uncertainty appears steady, with the price range ({first_range_str} to {last_range_str}) showing little change over the horizon.",
                        f"The model maintains a consistent level of confidence, reflected in the stable forecast range ({first_range_str} to {last_range_str})."
                        ]
                }

                if width_change_ratio > 1.2: range_trend_comment = random.choice(range_trend_options['widening'])
                elif width_change_ratio < 0.8: range_trend_comment = random.choice(range_trend_options['narrowing'])
                else: range_trend_comment = random.choice(range_trend_options['stable'])


                # Calculate Average if missing or ensure numeric
                if 'Average' not in forecast_df.columns:
                     forecast_df['Average'] = (forecast_df['Low'] + forecast_df['High']) / 2
                else:
                    forecast_df['Average'] = pd.to_numeric(forecast_df['Average'], errors='coerce')

                forecast_df.dropna(subset=['Average'], inplace=True) # Drop if average is invalid

                # Calculate Potential ROI if possible
                if current_price is not None and current_price > 0:
                    forecast_df['Potential ROI'] = ((forecast_df['Average'] - current_price) / current_price) * 100
                else:
                    forecast_df['Potential ROI'] = np.nan # Set to NaN if current price is invalid

                # Define Action Signal based on ROI thresholds
                roi_threshold_buy = 2.5; roi_threshold_short = -2.5
                forecast_df['Action'] = np.select(
                    [forecast_df['Potential ROI'] > roi_threshold_buy, forecast_df['Potential ROI'] < roi_threshold_short],
                    ['Consider Buy', 'Consider Short'], default='Hold/Neutral'
                )
                forecast_df.loc[forecast_df['Potential ROI'].isna(), 'Action'] = 'N/A'


                # Generate table rows (Safely access columns)
                required_cols = [forecast_time_col, 'Low', 'Average', 'High', 'Potential ROI', 'Action']
                if all(col in forecast_df.columns for col in required_cols):
                    for _, row in forecast_df.iterrows():
                        action_class = str(row.get('Action', 'N/A')).lower().split(" ")[-1].split("/")[0] # e.g., buy, short, neutral
                        roi_val = row.get('Potential ROI', np.nan)
                        roi_icon = get_icon('neutral')
                        roi_fmt = "N/A"
                        if not pd.isna(roi_val):
                           roi_icon = get_icon('up' if roi_val > 1 else ('down' if roi_val < -1 else 'neutral'))
                           roi_fmt = format_html_value(roi_val, 'percent_direct', 1)

                        low_fmt = format_html_value(row.get('Low'), 'currency')
                        avg_fmt = format_html_value(row.get('Average'), 'currency')
                        high_fmt = format_html_value(row.get('High'), 'currency')
                        action_display = row.get('Action', 'N/A')
                        time_period_fmt = str(row.get(forecast_time_col, 'N/A')) # Ensure time period is string

                        table_rows += (
                            f"<tr><td>{time_period_fmt}</td><td>{low_fmt}</td><td>{avg_fmt}</td><td>{high_fmt}</td>"
                            f"<td>{roi_icon} {roi_fmt}</td><td class='action-{action_class}'>{action_display}</td></tr>\n"
                        )
                else:
                     missing_cols = [col for col in required_cols if col not in forecast_df.columns]
                     logging.warning(f"Missing required columns in forecast data: {missing_cols}")
                     table_rows = f"<tr><td colspan='6' style='text-align:center;'>Detailed forecast data incomplete.</td></tr>"

            # Define HTML after processing
            min_max_summary = f"""<p>Over the forecast horizon ({forecast_df[forecast_time_col].iloc[0]} to {forecast_df[forecast_time_col].iloc[-1]}), {ticker}'s price is projected by the model to fluctuate between approximately <strong>{format_html_value(min_price_overall, 'currency')}</strong> and <strong>{format_html_value(max_price_overall, 'currency')}</strong>.</p>""" if min_price_overall is not None else "<p>Overall forecast range could not be determined.</p>"
            table_html = f"""<div class="table-container"><table><thead><tr><th>{period_label} ({forecast_time_col})</th><th>Min. Price</th><th>Avg. Price</th><th>Max. Price</th><th>Potential ROI vs Current ({current_price_fmt})</th><th>Model Signal</th></tr></thead><tbody>{table_rows}</tbody></table></div>"""

        else: # Case where input data is empty or lacks columns
            min_max_summary = f"<p>No detailed {period_label.lower()}-by-{period_label.lower()} forecast data is currently available for {ticker}.</p>"
            table_html = ""
            range_trend_comment = ""


        # --- Enhanced Site Specific Narrative ---
        min_fmt = format_html_value(min_price_overall, 'currency')
        max_fmt = format_html_value(max_price_overall, 'currency')
        range_narrative = f"{min_fmt} to {max_fmt}" if min_price_overall is not None else "an undetermined range"

        if "finances forecast" in site_name:
            narrative_options = [
                (
                 f"The following table presents the {period_label.lower()} price forecast evolution for {ticker}. It details the model's projected minimum, average, and maximum price levels (overall: {range_narrative}) for each period, alongside the potential Return on Investment (ROI) relative to the current price ({current_price_fmt}). "
                 f"These projections serve as quantitative guideposts, influenced by underlying assumptions about growth, margins, and market conditions."
                ),
                (
                 f"This table breaks down the {period_label.lower()} forecast trajectory for {ticker}. Shown are the estimated low, average, and high price points (spanning {range_narrative} overall) per period, plus potential ROI compared to today's price ({current_price_fmt}). "
                 f"These figures offer a model-based guide, reflecting assumptions on growth and financial performance."
                )
            ]
            narrative_intro = random.choice(narrative_options)
        elif "radar stocks" in site_name:
             narrative_options = [
                (
                 f"This table outlines potential {period_label.lower()} price trajectories and model-derived action signals for {ticker}. "
                 f"Traders can utilize these projected ranges ({range_narrative}) as reference points for potential support/resistance zones or targets, always confirming with real-time technical indicators and volume analysis. Note that 'Model Signal' reflects ROI potential, not a trade recommendation."
                ),
                (
                 f"Below are the {period_label.lower()} price path estimates and associated model signals for {ticker}. "
                 f"These forecast bands ({range_narrative}) can inform traders about potential price zones, but should be used with confirmation from live technicals and volume. The 'Model Signal' is ROI-based, not direct trading advice."
                )
             ]
             narrative_intro = random.choice(narrative_options)
        elif "bernini capital" in site_name:
            narrative_options = [
                (
                f"Below is the model-generated forecast detailing {ticker}'s potential price path over the coming {period_label.lower()}s. "
                f"While these projections ({range_narrative}) offer insight into possible future valuations, long-term investors should prioritize fundamental analysis, assessing intrinsic value against these price levels and considering the inherent uncertainties in any forecast."
                ),
                (
                 f"The model's {period_label.lower()} forecast for {ticker} is presented here. "
                 f"Although these price estimates ({range_narrative}) provide a quantitative outlook, value investors must rely primarily on fundamental assessment, comparing intrinsic value calculations to these levels and acknowledging forecast limitations."
                )
            ]
            narrative_intro = random.choice(narrative_options)
        else: # Default
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
    """Generates the Company Profile section with enhanced detail and site variations."""
    try:
        site_name = rdata.get('site_name', '').lower()
        profile_data = rdata.get('profile_data', {})
        if not isinstance(profile_data, dict):
            profile_data = {}
            logging.warning("profile_data not found or not a dict, using empty.")

        website_link = profile_data.get('Website', '#')
        if website_link and isinstance(website_link, str) and not website_link.startswith(('http://', 'https://')) and website_link != '#':
             website_link = f"https://{website_link}" # Default to https for safety
        elif not website_link or website_link == '#':
             website_link = '#' # Ensure it's '#' if None or empty or placeholder

        # Enhanced Base structure with better NA handling and formatting
        profile_items = []
        if profile_data.get('Sector'): profile_items.append(f"<div class='profile-item'><span>Sector:</span>{format_html_value(profile_data['Sector'], 'string')}</div>")
        if profile_data.get('Industry'): profile_items.append(f"<div class='profile-item'><span>Industry:</span>{format_html_value(profile_data['Industry'], 'string')}</div>")
        if profile_data.get('Market Cap'): profile_items.append(f"<div class='profile-item'><span>Market Cap:</span>{format_html_value(profile_data['Market Cap'], 'large_number')}</div>")
        if profile_data.get('Employees'): profile_items.append(f"<div class='profile-item'><span>Employees:</span>{format_html_value(profile_data.get('Employees'), 'integer')}</div>")

        # Make website link conditional on being a valid URL structure (simple check)
        if website_link != '#':
             profile_items.append(f"<div class='profile-item'><span>Website:</span><a href='{website_link}' target='_blank' rel='noopener noreferrer'>{format_html_value(profile_data.get('Website','N/A'), 'string')}</a></div>")
        elif 'Website' in profile_data: # If website was provided but deemed invalid link
             profile_items.append(f"<div class='profile-item'><span>Website:</span>{format_html_value(profile_data.get('Website'), 'string')} (Link invalid/missing)</div>")


        # Add Location if available
        location_parts = [profile_data.get('City'), profile_data.get('State'), profile_data.get('Country')]
        location_str = ', '.join(filter(None, [str(p) if p is not None else None for p in location_parts])) # Ensure string parts
        if location_str: profile_items.append(f"<div class='profile-item'><span>Headquarters:</span>{location_str}</div>")

        profile_grid = f'<div class="profile-grid">{"".join(profile_items)}</div>' if profile_items else "<p>Basic company identification data is limited.</p>"

        # Enhanced Summary Section
        summary_title_options = {
            'finances forecast': ["Company Strategy & Market Position", "Business Model & Strategic Outlook"],
            'radar stocks': ["Core Business & Operational Focus", "Company Activities & News Context"],
            'bernini capital': ["Fundamental Business Profile & Industry Standing", "Core Operations & Competitive Landscape"],
            'default': ["Business Overview", "Company Description"]
        }
        summary_title = random.choice(summary_title_options.get(site_name, summary_title_options['default']))


        narrative_focus_options = {
            'finances forecast': [
                " Understanding its core business model, competitive advantages, and strategic initiatives is crucial for evaluating future growth prospects and forecast reliability.",
                " Grasping the company's main operations, market strengths, and strategic direction helps in assessing future potential and the validity of forecasts."
                ],
            'radar stocks': [
                " Familiarity with the company's primary activities helps contextualize news flow and potential catalysts that could impact short-term price movements.",
                " Knowing what the company does provides background for interpreting news and identifying events that might affect near-term trading."
                ],
            'bernini capital': [
                " Assessing the company's role within its industry, its operational scale, and its long-term strategy provides a foundation for fundamental valuation.",
                " Evaluating the firm's industry position, size, and strategic plan is fundamental to estimating its intrinsic value."
                ],
            'default': [
                " A brief overview of the company's business activities.",
                " Understanding the core business provides context for the following analysis."
                ]
        }
        narrative_focus = random.choice(narrative_focus_options.get(site_name, narrative_focus_options['default']))


        summary_text = str(profile_data.get('Summary', 'No detailed business summary available.')) # Ensure string
        summary_html = f"<h4>{summary_title}</h4><p>{narrative_focus} {summary_text}</p>"

        return profile_grid + summary_html
    except Exception as e:
        return _generate_error_html("Company Profile", str(e))

def generate_valuation_metrics_html(ticker, rdata):
    """Generates Valuation Metrics with enhanced site-specific narrative focus and comparative context."""
    try:
        site_name = rdata.get('site_name', '').lower()
        valuation_data = rdata.get('valuation_data')
        if not isinstance(valuation_data, dict):
             valuation_data = {}
             logging.warning("valuation_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(valuation_data)

        # --- Enhanced Site Specific Narrative ---
        narrative = ""
        # Use format_html_value for display
        trailing_pe_fmt = format_html_value(valuation_data.get('Trailing P/E'), 'ratio')
        forward_pe_fmt = format_html_value(valuation_data.get('Forward P/E'), 'ratio')
        peg_ratio_fmt = format_html_value(valuation_data.get('PEG Ratio'), 'ratio')
        ps_ratio_fmt = format_html_value(valuation_data.get('Price/Sales (TTM)'), 'ratio')
        pb_ratio_fmt = format_html_value(valuation_data.get('Price/Book (MRQ)'), 'ratio')
        pfcf_ratio_fmt = format_html_value(valuation_data.get('Price/FCF (TTM)'), 'ratio')

        # Use _safe_float for interpretation logic
        forward_pe_val = _safe_float(valuation_data.get('Forward P/E'))
        trailing_pe_val = _safe_float(valuation_data.get('Trailing P/E'))

        # Valuation interpretation helper
        def interpret_pe(pe_val, pe_fmt):
            if pe_val is None: return pe_fmt, random.choice(["cannot be determined", "is unavailable", "is not applicable"])
            if pe_val <= 0: return pe_fmt, random.choice(["negative (indicating loss or requires context)", "below zero (suggesting no profit or data anomaly)", "negative (check earnings details)"])
            if pe_val < 15: return pe_fmt, random.choice(["relatively low (potentially undervalued or low growth expectations)", "quite low (possibly undervalued or facing slow growth)", "modest (could be value or low expectations)"])
            if pe_val < 25: return pe_fmt, random.choice(["moderate", "average", "in a typical range"])
            if pe_val < 40: return pe_fmt, random.choice(["elevated (suggesting growth expectations)", "somewhat high (implying growth is priced in)", "above average (reflecting positive outlook)"])
            return pe_fmt, random.choice(["high (implying significant growth expectations or potential overvaluation)", "very high (indicating strong growth needed or possible richness)", "significantly elevated (suggesting premium valuation or high growth assumptions)"])

        fwd_pe_disp, fwd_pe_interp = interpret_pe(forward_pe_val, forward_pe_fmt)
        trail_pe_disp, trail_pe_interp = interpret_pe(trailing_pe_val, trailing_pe_fmt)

        peer_hist_prompt_options = [
            f"Crucially, these ratios should be benchmarked against {ticker}'s own historical averages {get_icon('history')} and its industry peer group {get_icon('peer')} to determine relative attractiveness.",
            f"Comparing these multiples to {ticker}'s past levels {get_icon('history')} and industry competitors {get_icon('peer')} is essential for proper valuation context.",
            f"For meaningful assessment, these valuation metrics need comparison with {ticker}'s historical data {get_icon('history')} and relevant industry peers {get_icon('peer')}."
            ]
        peer_hist_prompt = random.choice(peer_hist_prompt_options)

        if "finances forecast" in site_name:
            narrative_options = [
                (
                f"Assessing {ticker}'s valuation is critical for gauging if the current market price aligns with future earnings potential. The Forward P/E of <strong>{fwd_pe_disp}</strong> ({fwd_pe_interp}) reflects market expectations for next year's earnings. "
                f"The PEG Ratio ({peg_ratio_fmt}) further contextualizes this by factoring in expected growth. A PEG near 1 might suggest fair valuation relative to growth. Price/Sales ({ps_ratio_fmt}) offers a perspective based on revenue. {peer_hist_prompt}"
                ),
                (
                f"Understanding {ticker}'s valuation helps determine if its price matches earnings outlook. The Forward P/E ({fwd_pe_disp}) indicates {fwd_pe_interp} based on future estimates. "
                f"The PEG ratio ({peg_ratio_fmt}) relates this to growth; around 1 can imply fair value. The Price/Sales ratio ({ps_ratio_fmt}) provides a revenue-based comparison. {peer_hist_prompt}"
                )
             ]
            narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
             narrative_options = [
                (
                f"While secondary to price action for short-term trading, valuation metrics provide important context. Extreme readings in Trailing P/E ({trail_pe_disp} - {trail_pe_interp}) or Forward P/E ({fwd_pe_disp} - {fwd_pe_interp}) can sometimes signal potential exhaustion points or reversals. "
                f"Metrics like Price/Sales ({ps_ratio_fmt}) and Price/Book ({pb_ratio_fmt}) act as broader benchmarks. Focus remains on how price reacts relative to these levels, rather than the levels themselves."
                ),
                (
                f"Valuation ratios offer background for traders but aren't primary signals. Significant extremes in P/E (Trailing: {trail_pe_disp}, {trail_pe_interp}; Forward: {fwd_pe_disp}, {fwd_pe_interp}) might hint at turning points. "
                f"P/S ({ps_ratio_fmt}) and P/B ({pb_ratio_fmt}) offer wider context. The key is price behavior around these valuation levels, not just the absolute numbers."
                )
             ]
             narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
            narrative_options = [
                (
                f"Fundamental valuation analysis is central to our process. We scrutinize P/E ratios (Trailing: {trail_pe_disp} - {trail_pe_interp}; Forward: {fwd_pe_disp} - {fwd_pe_interp}), Price/Book ({pb_ratio_fmt}), and Price/Sales ({ps_ratio_fmt}). "
                f"The Price/Free Cash Flow (P/FCF: {pfcf_ratio_fmt}) {get_icon('cash')} is particularly vital, assessing value based on actual cash generation available to investors. {peer_hist_prompt} A significant discount to historical/peer averages might indicate a value opportunity, provided fundamentals are sound (see Financial Health)."
                ),
                (
                f"Our value investing approach prioritizes valuation. Key metrics include P/E (Past: {trail_pe_disp}, {trail_pe_interp}; Future Est: {fwd_pe_disp}, {fwd_pe_interp}), P/B ({pb_ratio_fmt}), and P/S ({ps_ratio_fmt}). "
                f"We emphasize Price/Free Cash Flow ({pfcf_ratio_fmt}) {get_icon('cash')} as it reflects true cash earnings power. {peer_hist_prompt} A notable discount relative to benchmarks could signal value, assuming solid fundamentals (refer to Financial Health)."
                )
            ]
            narrative = random.choice(narrative_options)
        else: # Default
             narrative_options = [
                (
                 f"Valuation metrics help assess whether {ticker}'s stock price is justified relative to its earnings, sales, book value, or growth prospects. Key ratios include Trailing P/E ({trail_pe_disp}), Forward P/E ({fwd_pe_disp}), Price/Sales ({ps_ratio_fmt}), Price/Book ({pb_ratio_fmt}), and PEG Ratio ({peg_ratio_fmt}). "
                 f"{peer_hist_prompt}"
                ),
                (
                f"These ratios gauge {ticker}'s market price against its financial performance and assets. Notable figures are Trailing P/E ({trail_pe_disp}), Forward P/E ({fwd_pe_disp}), P/S ({ps_ratio_fmt}), P/B ({pb_ratio_fmt}), and PEG ({peg_ratio_fmt}). "
                f"{peer_hist_prompt}"
                )
             ]
             narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Valuation Metrics", str(e))


def generate_financial_health_html(ticker, rdata):
    """Generates Financial Health section with enhanced site-specific narratives and trend context."""
    try:
        site_name = rdata.get('site_name', '').lower()
        health_data = rdata.get('financial_health_data')
        if not isinstance(health_data, dict):
             health_data = {}
             logging.warning("financial_health_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(health_data)

        # --- Extract data ---
        roe_fmt = format_html_value(health_data.get('Return on Equity (ROE TTM)'), 'percent_direct')
        debt_equity_fmt = format_html_value(health_data.get('Debt/Equity (MRQ)'), 'ratio')
        current_ratio_fmt = format_html_value(health_data.get('Current Ratio (MRQ)'), 'ratio')
        quick_ratio_fmt = format_html_value(health_data.get('Quick Ratio (MRQ)'), 'ratio')
        op_cash_flow_fmt = format_html_value(health_data.get('Operating Cash Flow (TTM)'), 'large_number')
        # Optional trend data
        roe_trend = rdata.get('roe_trend', None) # e.g., 'Improving', 'Stable', 'Declining'
        debt_equity_trend = rdata.get('debt_equity_trend', None)

        # --- Enhanced Narrative ---
        narrative = ""
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

        # Link to Risks (Example: High Debt)
        risk_link = ""
        debt_equity_val = _safe_float(health_data.get('Debt/Equity (MRQ)'))
        if debt_equity_val is not None and debt_equity_val > 1.5:
            risk_items = rdata.get('risk_items', [])
            if isinstance(risk_items, list) and any("Debt" in str(item) or "Interest Rate" in str(item) for item in risk_items):
                risk_link_options = [
                    f" {get_icon('warning')} Note: The relatively high Debt/Equity ({debt_equity_fmt}) aligns with identified risks related to leverage or interest rates (see Risk Factors).",
                    f" {get_icon('warning')} Caution: Elevated Debt/Equity ({debt_equity_fmt}) connects to potential leverage/rate risks mentioned elsewhere (view Risk Factors)."
                    ]
                risk_link = random.choice(risk_link_options)


        # Liquidity Interpretation
        current_ratio_val = _safe_float(health_data.get('Current Ratio (MRQ)'))
        liquidity_desc_options = {
            'high': ["well-covered", "comfortably covered", "amply covered"],
            'medium': ["adequately covered", "sufficiently covered", "reasonably covered"],
            'low': ["tightly covered", "barely covered", "minimally covered"]
            }
        liquidity_desc = random.choice(liquidity_desc_options['low']) # Default
        if current_ratio_val is not None:
            if current_ratio_val > 1.5: liquidity_desc = random.choice(liquidity_desc_options['high'])
            elif current_ratio_val > 1.0: liquidity_desc = random.choice(liquidity_desc_options['medium'])


        if "finances forecast" in site_name:
            narrative_options = [
                (
                f"A sound financial footing is essential for realizing growth forecasts. {ticker}'s ability to generate returns on shareholder investments (ROE: {roe_fmt}) and manage its leverage (Debt/Equity: {debt_equity_fmt}) influences its capacity for future expansion. "
                f"Short-term obligations appear {liquidity_desc} by current assets (Current Ratio: {current_ratio_fmt}). Strong Operating Cash Flow ({op_cash_flow_fmt}) is crucial for funding operations and potential future dividends/buybacks. {trend_context}{risk_link}"
                ),
                (
                f"Financial stability underpins forecast reliability. {ticker}'s ROE ({roe_fmt}) reflects profitability relative to equity, while its D/E ratio ({debt_equity_fmt}) shows leverage. "
                f"Liquidity seems {liquidity_desc} (Current Ratio: {current_ratio_fmt}). Robust Operating Cash Flow ({op_cash_flow_fmt}) is vital for operations and shareholder returns. {trend_context}{risk_link}"
                )
            ]
            narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
            narrative_options = [
                (
                f"While not primary trading drivers, underlying financial health metrics provide crucial risk context. High leverage (Debt/Equity: {debt_equity_fmt}) or weak short-term liquidity (Current Ratio: {current_ratio_fmt}, Quick Ratio: {quick_ratio_fmt}) can exacerbate downside moves during market stress. "
                f"Conversely, strong Operating Cash Flow ({op_cash_flow_fmt}) {get_icon('cash')} offers resilience. Significant negative trends ({trend_context}) could eventually weigh on sentiment.{risk_link}"
                ),
                (
                 f"Financial health acts as a backdrop risk factor for traders. Excessive debt ({debt_equity_fmt}) or poor liquidity ({current_ratio_fmt}, {quick_ratio_fmt}) increases vulnerability during sell-offs. "
                 f"Positive cash flow ({op_cash_flow_fmt}) {get_icon('cash')} adds a layer of safety. Deteriorating trends ({trend_context}) might eventually pressure the stock.{risk_link}"
                )
             ]
            narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
            narrative_options = [
                (
                f"Assessing financial resilience is paramount for long-term investment. We focus on sustainable profitability (ROE: {roe_fmt}), prudent capital structure (Debt/Equity: {debt_equity_fmt}), and robust liquidity (Current Ratio: {current_ratio_fmt}, Quick Ratio: {quick_ratio_fmt}). {trend_context} "
                f"Consistent positive Operating Cash Flow ({op_cash_flow_fmt}) is a non-negotiable sign of a healthy business capable of weathering cycles and returning value. {risk_link} Compare these ratios to industry peers {get_icon('peer')}."
                ),
                (
                 f"For long-term investors, financial strength is key. We analyze profitability (ROE: {roe_fmt}), leverage ({debt_equity_fmt}), and liquidity ({current_ratio_fmt}, {quick_ratio_fmt}). {trend_context} "
                 f"Reliable positive cash flow from operations ({op_cash_flow_fmt}) is essential for business health and shareholder returns. {risk_link} Benchmarking against peers {get_icon('peer')} is vital."
                )
            ]
            narrative = random.choice(narrative_options)
        else: # Default
             narrative_options = [
                (
                 f"Financial health metrics provide insights into {ticker}'s stability, efficiency, and ability to meet its obligations. {health_summary} {trend_context} "
                 f"These figures indicate the company's leverage, short-term solvency, and profitability relative to shareholder equity. Robust cash flow is generally a positive sign.{risk_link}"
                ),
                (
                f"This section gauges {ticker}'s financial stability and operational effectiveness. {health_summary} {trend_context} "
                f"The data reflects leverage, liquidity, and returns on equity. Strong cash flow is typically viewed favorably.{risk_link}"
                )
             ]
             narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Financial Health", str(e))

def generate_financial_efficiency_html(ticker, rdata):
    """Generates Financial Efficiency section with enhanced site-specific narratives."""
    try:
        site_name = rdata.get('site_name', '').lower()
        efficiency_data = rdata.get('financial_efficiency_data')
        if not isinstance(efficiency_data, dict):
             efficiency_data = {}
             logging.warning("financial_efficiency_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(efficiency_data)

        # --- Extract data ---
        asset_turnover_fmt = format_html_value(efficiency_data.get('Asset Turnover (TTM)'), 'ratio')
        inventory_turnover_fmt = format_html_value(efficiency_data.get('Inventory Turnover (TTM)'), 'ratio')
        receivables_turnover_fmt = format_html_value(efficiency_data.get('Receivables Turnover (TTM)'), 'ratio')

        # --- Enhanced Narrative ---
        narrative = ""
        efficiency_summary_options = [
            f"Efficiency is gauged by how effectively {ticker} utilizes assets (Asset Turnover: {asset_turnover_fmt})",
            f"Operational effectiveness can be seen in asset utilization (Asset Turnover: {asset_turnover_fmt})",
            f"{ticker}'s efficiency in using its assets to generate sales is measured by Asset Turnover ({asset_turnover_fmt})"
            ]
        efficiency_summary = random.choice(efficiency_summary_options)

        if inventory_turnover_fmt != 'N/A': efficiency_summary += f", manages inventory (Inventory Turnover: {inventory_turnover_fmt})"
        if receivables_turnover_fmt != 'N/A': efficiency_summary += f", and collects payments (Receivables Turnover: {receivables_turnover_fmt})."
        else: efficiency_summary += "." # Add period if no receivables

        comparison_prompt_options = [
            f"Comparing these turnover ratios against industry benchmarks {get_icon('peer')} and historical trends {get_icon('history')} reveals operational effectiveness.",
            f"Benchmarking these efficiency metrics with industry peers {get_icon('peer')} and the company's own history {get_icon('history')} provides valuable context.",
            f"Relative performance in these turnover figures, compared to peers {get_icon('peer')} and past results {get_icon('history')}, indicates efficiency levels."
            ]
        comparison_prompt = random.choice(comparison_prompt_options)


        # Inventory/Receivables Text Snippets
        inv_text = f"Efficient inventory management ({inventory_turnover_fmt}) minimizes capital tied up in stock." if inventory_turnover_fmt != 'N/A' else ""
        rec_text = f"Rapid receivables collection ({receivables_turnover_fmt}) improves cash flow." if receivables_turnover_fmt != 'N/A' else ""

        if "finances forecast" in site_name:
            narrative_options = [
                (
                f"Operational efficiency directly impacts future profitability and return on investment, influencing forecast accuracy. High Asset Turnover ({asset_turnover_fmt}) suggests strong revenue generation from the asset base. "
                f"{inv_text} {rec_text} Improvements here can boost future ROE. {comparison_prompt}"
                ),
                (
                f"How efficiently {ticker} operates affects its profit potential and forecast outcomes. Strong Asset Turnover ({asset_turnover_fmt}) indicates good sales generation per asset dollar. "
                f"{inv_text} {rec_text} Better efficiency can lead to higher returns. {comparison_prompt}"
                )
             ]
            narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
            narrative_options = [
                (
                f"Efficiency ratios provide background on operational performance but are not typically primary trading indicators. {efficiency_summary} "
                f"However, significant deterioration in these metrics, particularly if announced unexpectedly (e.g., inventory build-up), could negatively impact sentiment and trigger price adjustments. {comparison_prompt}"
                ),
                (
                f"These efficiency figures offer operational context, though they aren't key trading signals. {efficiency_summary} "
                f"Sudden negative shifts, like slow inventory turnover, can sometimes affect market sentiment and price. {comparison_prompt}"
                )
            ]
            narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
            narrative_options = [
                (
                f"Analyzing financial efficiency reveals insights into management's operational prowess, a key factor for long-term value creation. {efficiency_summary} "
                f"Strong and improving turnover ratios often indicate a competitive advantage and efficient capital deployment. {comparison_prompt} Consistent underperformance relative to peers might signal operational weaknesses."
                ),
                (
                f"Efficiency analysis highlights management skill, vital for sustained value. {efficiency_summary} "
                f"High turnover generally points to competitive strength and smart capital use. {comparison_prompt} Lagging peers could indicate operational issues."
                )
            ]
            narrative = random.choice(narrative_options)
        else: # Default
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
    """Generates Profitability & Growth section with enhanced narratives and context."""
    try:
        site_name = rdata.get('site_name', '').lower()
        profit_data = rdata.get('profitability_data')
        if not isinstance(profit_data, dict):
             profit_data = {}
             logging.warning("profitability_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(profit_data)

        # --- Extract data ---
        gross_margin_fmt = format_html_value(profit_data.get('Gross Margin (TTM)'), 'percent_direct')
        op_margin_fmt = format_html_value(profit_data.get('Operating Margin (TTM)'), 'percent_direct')
        # Handle Net Profit Margin key variation
        net_margin_key = 'Net Profit Margin (TTM)'
        if net_margin_key not in profit_data:
            net_margin_key = 'Profit Margin (TTM)' # Fallback key
        net_margin_fmt = format_html_value(profit_data.get(net_margin_key), 'percent_direct')

        rev_growth_fmt = format_html_value(profit_data.get('Revenue Growth (YoY)'), 'percent_direct')
        earn_growth_fmt = format_html_value(profit_data.get('Earnings Growth (YoY)'), 'percent_direct')
        # Optional trend data
        margin_trend = rdata.get('margin_trend', None) # e.g., 'Expanding', 'Stable', 'Contracting'
        growth_trend = rdata.get('growth_trend', None) # e.g., 'Accelerating', 'Stable', 'Decelerating'

        # --- Enhanced Narrative ---
        narrative = ""
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

        # Link to Risks (Example: Competition impacting margins)
        risk_link = ""
        op_margin_val = _safe_float(profit_data.get('Operating Margin (TTM)'))
        if margin_trend == 'Contracting' or (op_margin_val is not None and op_margin_val < 10): # Example threshold
             risk_items = rdata.get('risk_items', [])
             if isinstance(risk_items, list) and any("Competition" in str(item) or "Pricing Power" in str(item) for item in risk_items):
                 risk_link_options = [
                     f" {get_icon('warning')} Observed margin pressure may relate to identified competitive risks (see Risk Factors).",
                     f" {get_icon('warning')} Note: Contracting margins could be linked to competitive pressures mentioned in the Risk Factors.",
                     f" {get_icon('warning')} Declining margins might reflect competitive challenges highlighted under Risk Factors."
                     ]
                 risk_link = random.choice(risk_link_options)


        if "finances forecast" in site_name:
             narrative_options = [
                (
                f"Profitability and growth are the primary engines driving {ticker}'s future value and forecast potential. {profit_summary} {growth_summary} "
                f"Sustainable margins indicate pricing power and operational control, while positive growth fuels expansion. {trend_context} Future forecasts heavily depend on the continuation (or improvement) of these trends. {comparison_prompt}{risk_link}"
                ),
                (
                f"Earnings power and expansion drive {ticker}'s forecast outlook. {profit_summary} {growth_summary} "
                f"Healthy margins suggest efficiency, while growth indicates market traction. {trend_context} Maintaining these positive trends is key for forecast achievement. {comparison_prompt}{risk_link}"
                )
             ]
             narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
             narrative_options = [
                (
                f"Margin ({gross_margin_fmt}, {op_margin_fmt}) and growth ({rev_growth_fmt}, {earn_growth_fmt}) figures shape the fundamental backdrop influencing market sentiment. "
                f"Strong earnings growth often fuels bullish momentum, while unexpected margin contraction can trigger sell-offs, acting as catalysts that complement technical signals. {trend_context} {comparison_prompt}{risk_link}"
                ),
                (
                f"Profitability ({gross_margin_fmt}, {op_margin_fmt}) and growth ({rev_growth_fmt}, {earn_growth_fmt}) provide fundamental context for traders. "
                f"Positive earnings surprises can boost momentum; margin misses can cause dips. These act as catalysts alongside technicals. {trend_context} {comparison_prompt}{risk_link}"
                )
             ]
             narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
             narrative_options = [
                 (
                f"Consistent profitability and sustainable growth are cornerstones of long-term investment quality. We analyze Gross ({gross_margin_fmt}), Operating ({op_margin_fmt}), and Net Margins ({net_margin_fmt}) for efficiency and competitive positioning. {growth_summary} "
                f"{trend_context} Demonstrating resilient margins and the ability to grow earnings consistently, especially compared to peers {get_icon('peer')}, strengthens the investment case.{risk_link}"
                 ),
                 (
                 f"For value investors, reliable profit generation and growth are essential. We examine margins (Gross: {gross_margin_fmt}, Op: {op_margin_fmt}, Net: {net_margin_fmt}) for operational strength. {growth_summary} "
                 f"{trend_context} Steady margins and consistent earnings growth, particularly versus competitors {get_icon('peer')}, support a positive long-term view.{risk_link}"
                 )
             ]
             narrative = random.choice(narrative_options)
        else: # Default
             narrative_options = [
                (
                 f"This section examines {ticker}'s ability to generate profit and expand its business. {profit_summary} {growth_summary} {trend_context} {comparison_prompt} These are key indicators of financial performance and future potential.{risk_link}"
                ),
                (
                f"Here we look at {ticker}'s profit generation and growth trajectory. {profit_summary} {growth_summary} {trend_context} {comparison_prompt} These metrics reflect financial success and expansion capacity.{risk_link}"
                )
             ]
             narrative = random.choice(narrative_options)

        return f'<div class="narrative"><p>{narrative}</p></div>' + content
    except Exception as e:
        return _generate_error_html("Profitability & Growth", str(e))


def generate_dividends_shareholder_returns_html(ticker, rdata):
    """Generates Dividends & Shareholder Returns section with enhanced context and sustainability focus."""
    try:
        site_name = rdata.get('site_name', '').lower()
        dividend_data = rdata.get('dividends_data')
        if not isinstance(dividend_data, dict):
             dividend_data = {}
             logging.warning("dividends_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(dividend_data)

        # --- Extract data ---
        fwd_yield_fmt = format_html_value(dividend_data.get('Dividend Yield (Fwd)'), 'percent_direct')
        fwd_dividend_fmt = format_html_value(dividend_data.get('Forward Annual Dividend Rate'), 'currency')
        payout_ratio_fmt = format_html_value(dividend_data.get('Payout Ratio'), 'percent_direct')
        # Find a valid date key - prioritize Ex-Dividend, fallback to Last Split? (Needs review)
        dividend_date_key = 'Ex-Dividend Date' if dividend_data.get('Ex-Dividend Date') else 'Last Split Date' # Example fallback
        dividend_date_label = "Ex-Dividend Date" if dividend_date_key == 'Ex-Dividend Date' else "Last Event Date"
        dividend_date_fmt = format_html_value(dividend_data.get(dividend_date_key), 'date')

        buyback_yield_fmt = format_html_value(dividend_data.get('Buyback Yield (Est.)'), 'percent_direct')


        # --- Enhanced Narrative ---
        narrative = ""
        fwd_yield_val = _safe_float(dividend_data.get('Dividend Yield (Fwd)'))
        has_dividend = fwd_yield_val is not None and fwd_yield_val > 0.01 # Check if yield > 0.01%

        dividend_summary = ""
        if has_dividend:
            payout_level_options = {
                'high': ["high (monitor sustainability)", "elevated (check cash flow coverage)", "high (may limit growth reinvestment)"],
                'neg': ["negative (requires investigation, funded by non-earnings?)", "negative (dividend exceeds earnings)", "negative (unsustainable without other cash sources)"],
                'low': ["low (potential for growth)", "conservative (room for increases)", "low (prioritizing reinvestment?)"],
                'mid': ["moderate", "reasonable", "sustainable based on current earnings"]
                }
            payout_level = random.choice(payout_level_options['mid']) # Default assumption
            payout_ratio_val = _safe_float(dividend_data.get('Payout Ratio'))
            if payout_ratio_val is not None:
                 if payout_ratio_val > 80: payout_level = random.choice(payout_level_options['high'])
                 elif payout_ratio_val < 0: payout_level = random.choice(payout_level_options['neg'])
                 elif payout_ratio_val < 30: payout_level = random.choice(payout_level_options['low'])

            dividend_summary_options = [
                f"{ticker} currently offers a forward dividend yield of <strong>{fwd_yield_fmt}</strong> (representing {fwd_dividend_fmt} annually per share). The Payout Ratio of {payout_ratio_fmt} suggests the dividend is currently {payout_level}. Last relevant date ({dividend_date_label}): {dividend_date_fmt}.",
                f"Shareholders receive a dividend yielding <strong>{fwd_yield_fmt}</strong> (equivalent to {fwd_dividend_fmt} per year). With a Payout Ratio of {payout_ratio_fmt}, its coverage appears {payout_level}. Last key date ({dividend_date_label}): {dividend_date_fmt}.",
                f"The current forward dividend yield is <strong>{fwd_yield_fmt}</strong> ({fwd_dividend_fmt}/year). The payout ratio ({payout_ratio_fmt}) indicates {payout_level} coverage. Most recent event date ({dividend_date_label}) was {dividend_date_fmt}."
            ]
            dividend_summary = random.choice(dividend_summary_options)
        else:
            dividend_summary_options = [
                f"{ticker} does not currently pay a significant regular dividend or data is unavailable.",
                f"No substantial regular dividend payment is indicated for {ticker} based on available data.",
                f"Regular dividend distributions do not appear to be a current practice for {ticker}."
            ]
            dividend_summary = random.choice(dividend_summary_options)

        buyback_summary = ""
        buyback_yield_val = _safe_float(dividend_data.get('Buyback Yield (Est.)'))
        # Check both estimated yield and actual share reduction
        shares_change_val = _safe_float(rdata.get('share_statistics_data', {}).get('Shares Change (YoY)'))
        buyback_indication = (buyback_yield_val is not None and buyback_yield_val != 0) or (shares_change_val is not None and shares_change_val < 0)

        if buyback_indication:
            buyback_summary_options = []
            if buyback_yield_fmt != 'N/A' and buyback_yield_fmt != '0.00%':
                buyback_summary_options.extend([
                    f" Additionally, the company returns value via share repurchases, estimated at a {buyback_yield_fmt} buyback yield.",
                    f" Share buybacks supplement returns, contributing an estimated {buyback_yield_fmt} yield.",
                    f" Beyond dividends, share repurchases add roughly {buyback_yield_fmt} to shareholder yield."
                    ])
            elif shares_change_val is not None and shares_change_val < 0: # Infer from share count change if yield N/A
                buyback_summary_options.extend([
                     f" Share repurchases also appear to be part of the capital return strategy, as indicated by a reduction in shares outstanding (see Share Statistics).",
                     f" Although buyback yield isn't specified, a decrease in outstanding shares suggests repurchases are occurring.",
                     f" Capital is also returned via buybacks, evidenced by a falling share count (refer to Share Statistics)."
                    ])
            if buyback_summary_options: # Ensure we have options before choosing
                 buyback_summary = random.choice(buyback_summary_options)
        else:
             buyback_summary = random.choice([
                 " Significant share repurchases are not indicated by available data.",
                 " Share buybacks do not appear to be a major component of current capital returns.",
                 " Focus seems to be primarily on dividends (if any) rather than buybacks."
             ])


        if "finances forecast" in site_name:
            narrative_options = [
                (
                f"Capital returns to shareholders contribute significantly to total return forecasts. {dividend_summary}{buyback_summary} "
                f"The sustainability of the dividend (indicated by Payout Ratio: {payout_ratio_fmt}) and the continuation of buybacks depend on future earnings and cash flow (see Financial Health), impacting overall forecast reliability."
                ),
                (
                f"Shareholder returns are an important component of forecast value. {dividend_summary}{buyback_summary} "
                f"Dividend safety ({payout_ratio_fmt} Payout Ratio) and buyback potential rely on future financial performance (view Financial Health), affecting forecast achievement."
                )
            ]
            narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
            narrative_options = [
                (
                f"While dividends ({fwd_yield_fmt}) are less critical for short-term trading strategies, the Ex-Dividend Date ({dividend_date_fmt}) is important as it often causes a predictable (though usually small) price drop. "
                f"A very high Payout Ratio ({payout_ratio_fmt}) could signal financial stress if earnings falter, potentially impacting sentiment. {buyback_summary}"
                ),
                (
                f"Dividends ({fwd_yield_fmt}) matter less for traders than the Ex-Dividend Date ({dividend_date_fmt}), which typically sees a price adjustment. "
                f"An excessive Payout Ratio ({payout_ratio_fmt}) might hint at risk if fundamentals weaken, affecting sentiment. {buyback_summary}"
                )
            ]
            narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
            narrative_options = [
                (
                f"For income-oriented value investors, analyzing shareholder returns is crucial. {dividend_summary} We assess the yield's attractiveness relative to risk, the safety implied by the Payout Ratio ({payout_ratio_fmt}), and the history of dividend growth (data not shown here, requires further research {get_icon('history')}). {buyback_summary} Total shareholder yield (Dividend Yield + Buyback Yield) provides a complete picture of capital return."
                ),
                (
                f"Evaluating shareholder returns is key for income investors. {dividend_summary} Yield, safety (Payout Ratio: {payout_ratio_fmt}), and growth history {get_icon('history')} are important dividend aspects. {buyback_summary} The combination of dividends and buybacks constitutes the total yield."
                )
            ]
            narrative = random.choice(narrative_options)
        else: # Default
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
    """Generates Share Statistics with enhanced site-specific narrative focus and ownership insights."""
    try:
        site_name = rdata.get('site_name', '').lower()
        share_data = rdata.get('share_statistics_data')
        if not isinstance(share_data, dict):
             share_data = {}
             logging.warning("share_statistics_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(share_data)

        # --- Enhanced Site Specific Narrative ---
        narrative = ""
        float_shares = format_html_value(share_data.get('Float'), 'large_number')
        shares_outstanding = format_html_value(share_data.get('Shares Outstanding'), 'large_number')
        insider_own_fmt = format_html_value(share_data.get('Insider Ownership'), 'percent_direct') # Percentage
        inst_own_fmt = format_html_value(share_data.get('Institutional Ownership'), 'percent_direct') # Percentage
        shares_short_fmt = format_html_value(share_data.get('Shares Short'), 'integer') # Number of shares
        shares_change_yoy_fmt = format_html_value(share_data.get('Shares Change (YoY)'), 'percent_direct') # Percentage change

        # Ownership Context
        ownership_implication = ""
        insider_val = _safe_float(share_data.get('Insider Ownership'))
        inst_val = _safe_float(share_data.get('Institutional Ownership'))

        insider_options = {
            'high': ["significant", "substantial", "notable"],
            'mid': ["moderate", "meaningful", "some"],
            'low': ["low", "limited", "minor"]
            }
        insider_alignment_options = {
            'high': ["suggests strong alignment with shareholders.", "indicates significant 'skin in the game'.", "points to strong management conviction."],
            'mid': ["suggests some alignment with shareholders.", "shows moderate insider commitment.", "implies reasonable management ownership."],
            'low': ["suggests limited direct management skin-in-the-game.", "indicates low insider stakes.", "shows minimal ownership by executives/directors."]
            }

        if insider_val is not None:
            insider_level = random.choice(insider_options['high']) if insider_val > 10 else random.choice(insider_options['mid']) if insider_val > 2 else random.choice(insider_options['low'])
            ownership_implication += f"The {insider_level} insider ownership ({insider_own_fmt}) {random.choice(insider_alignment_options[insider_level if insider_val > 10 else ('mid' if insider_val > 2 else 'low')])}"

        inst_options = {
             'high': ["very high", "dominant", "substantial"],
             'mid': ["high", "significant", "strong"],
             'low': ["moderate", "reasonable", "modest"]
            }
        inst_conviction_options = {
             'high': ["indicating strong conviction from large investors, potentially leading to lower volatility.", "showing significant interest from major funds, which could imply stability.", "reflecting widespread institutional backing, possibly reducing float-driven swings."],
             'mid': ["indicating moderate interest from large funds.", "showing solid institutional presence.", "reflecting decent ownership by money managers."],
             'low': ["reflecting limited institutional focus currently.", "suggesting lower interest from large investors.", "showing modest institutional involvement."]
            }

        if inst_val is not None:
            inst_level = random.choice(inst_options['high']) if inst_val > 75 else random.choice(inst_options['mid']) if inst_val > 50 else random.choice(inst_options['low'])
            # Added space if insider text exists
            if ownership_implication: ownership_implication += " "
            ownership_implication += f"Institutional ownership stands at a {inst_level} level ({inst_own_fmt}), {random.choice(inst_conviction_options[inst_level if inst_val > 75 else ('mid' if inst_val > 50 else 'low')])}"

        # Float Context
        float_context_options = [
            f"The public float of <strong>{float_shares}</strong> (out of {shares_outstanding} outstanding shares) represents the shares readily available for trading, influencing liquidity and potential price impact from large trades.",
            f"With <strong>{float_shares}</strong> shares floating (vs. {shares_outstanding} total), this portion is actively traded, affecting liquidity and susceptibility to large order impacts.",
            f"Trading liquidity is influenced by the <strong>{float_shares}</strong> shares in the public float (compared to {shares_outstanding} total outstanding), which impacts how easily large blocks can be traded."
            ]
        float_context = random.choice(float_context_options)

        # Shares Change Context
        shares_change_context = ""
        shares_change_val = _safe_float(share_data.get('Shares Change (YoY)'))
        if shares_change_val is not None:
            change_desc = "reduction" if shares_change_val < 0 else "increase" if shares_change_val > 0 else "stability"
            change_impact = "accretive to EPS (buybacks)" if shares_change_val < 0 else "potentially dilutive (issuance)" if shares_change_val > 0 else "neutral for EPS"
            shares_change_context_options = [
                 f"Changes in outstanding shares (YoY: {shares_change_yoy_fmt}), often due to buybacks or issuances, directly impact per-share metrics and should be factored into future EPS projections.",
                 f"The {shares_change_yoy_fmt} YoY change in share count ({change_desc}) has implications for EPS ({change_impact}) and needs consideration in forecasts.",
                 f"Variations in share count ({shares_change_yoy_fmt} YoY) affect per-share calculations and future estimates, whether through {change_desc}."
                ]
            shares_change_context = random.choice(shares_change_context_options)


        if "finances forecast" in site_name:
            narrative_options = [
                (
                f"Understanding the share structure is relevant for forecasting earnings per share (EPS) and potential dilution/accretion. {float_context} {ownership_implication} "
                f"{shares_change_context}"
                ),
                (
                f"Share data impacts EPS forecasts and dilution/buyback effects. {float_context} {ownership_implication} "
                f"{shares_change_context}"
                )
             ]
            narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
            narrative_options = [
                (
                f"Share dynamics influence trading characteristics. {float_context} {ownership_implication} "
                f"High institutional ownership might dampen retail-driven swings, while significant insider selling (not shown here, requires separate data) could be a bearish flag. The number of shares short ({shares_short_fmt}) also impacts potential volatility (see Short Selling section)."
                ),
                (
                 f"Trading behavior is affected by share details. {float_context} {ownership_implication} "
                 f"Heavy institutional presence can reduce volatility; insider activity (check external sources) provides sentiment clues. Short interest ({shares_short_fmt}) contributes to volatility potential (view Short Selling info)."
                )
            ]
            narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
            # Determine buyback info string outside the f-string
            buyback_info = "N/A" # Default
            if shares_change_val is not None and shares_change_val < 0:
                 buyback_info = f"{shares_change_yoy_fmt} reduction"

            narrative_options = [
                (
                 f"Analyzing the ownership structure provides insights into shareholder base stability and alignment. {float_context} {ownership_implication} "
                 f"Strong insider commitment and significant institutional backing are often viewed favorably by long-term investors seeking stability and management confidence. Share buybacks ({buyback_info}) can enhance per-share value."
                ),
                (
                f"Ownership details reveal shareholder stability and management alignment. {float_context} {ownership_implication} "
                f"Long-term investors typically prefer high insider/institutional presence. Buybacks resulting in share reduction ({buyback_info}) boost per-share metrics."
                )
             ]
            narrative = random.choice(narrative_options)
        else: # Default
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
    """Generates Stock Price Statistics section with enhanced narrative and volatility context."""
    try:
        site_name = rdata.get('site_name', '').lower()
        stats_data = rdata.get('stock_price_stats_data')
        if not isinstance(stats_data, dict):
             stats_data = {}
             logging.warning("stock_price_stats_data not found or not a dict, using empty.")

        # --- Ensure calculated volatility is added & formatted ---
        volatility = _safe_float(rdata.get('volatility')) # Get calculated volatility
        volatility_fmt = format_html_value(volatility, 'percent_direct', 1)
        # Add/update volatility in the dict for display *before* generating table
        if volatility is not None: # Only add if calculated
             stats_data['Volatility (30d Ann.)'] = f"{volatility_fmt} {get_icon('stats')}"
        else:
             stats_data['Volatility (30d Ann.)'] = "N/A" # Explicitly state N/A if not calculated


        content = generate_metrics_section_content(stats_data) # Generate table *after* updating dict

        # --- Extract data for narrative ---
        beta_fmt = format_html_value(stats_data.get('Beta'), 'ratio')
        fifty_two_wk_high_fmt = format_html_value(stats_data.get('52 Week High'), 'currency')
        fifty_two_wk_low_fmt = format_html_value(stats_data.get('52 Week Low'), 'currency')
        avg_vol_3m_fmt = format_html_value(stats_data.get('Average Volume (3 month)'), 'integer')
        fifty_two_wk_change_fmt = format_html_value(stats_data.get('52 Week Change'), 'percent_direct')


        # --- Enhanced Narrative ---
        narrative = ""
        stats_summary_options = [
            f"Key price behavior metrics include Beta ({beta_fmt}), the 52-week trading range ({fifty_two_wk_low_fmt} - {fifty_two_wk_high_fmt}), recent short-term volatility ({volatility_fmt}), and average trading liquidity (3m Avg Vol: {avg_vol_3m_fmt}).",
            f"Price characteristics are summarized by Beta ({beta_fmt}), the annual range ({fifty_two_wk_low_fmt} to {fifty_two_wk_high_fmt}), recent volatility ({volatility_fmt}), and typical volume ({avg_vol_3m_fmt} avg over 3m).",
            f"Understanding price action involves Beta ({beta_fmt}), the 52-week span ({fifty_two_wk_low_fmt} - {fifty_two_wk_high_fmt}), current volatility ({volatility_fmt}), and trading volume (3m Avg: {avg_vol_3m_fmt})."
            ]
        stats_summary = random.choice(stats_summary_options)


        # Volatility Interpretation
        vol_interp = ""
        if volatility is not None:
            if volatility > 40: vol_interp = f"The recent volatility ({volatility_fmt}) is high, indicating significant price swings."
            elif volatility > 20: vol_interp = f"Recent volatility ({volatility_fmt}) is moderate, suggesting average price fluctuations."
            else: vol_interp = f"Volatility ({volatility_fmt}) is relatively low, implying more stable price action recently."

        # Beta Interpretation
        beta_interp = ""
        beta_val = _safe_float(stats_data.get('Beta'))
        if beta_val is not None:
            if beta_val > 1.2: beta_interp = f"Beta ({beta_fmt}) suggests the stock is more volatile than the overall market."
            elif beta_val < 0.8: beta_interp = f"Beta ({beta_fmt}) indicates lower volatility relative to the market."
            else: beta_interp = f"Beta ({beta_fmt}) implies the stock's volatility generally tracks the broader market."


        if "finances forecast" in site_name:
            narrative_options = [
                (
                f"Understanding {ticker}'s historical price behavior provides context for future projections. {beta_interp} {vol_interp} "
                f"The 52-week range ({fifty_two_wk_low_fmt} - {fifty_two_wk_high_fmt}) highlights historical extremes, useful for assessing potential boundaries. Forecasts should consider this inherent volatility."
                ),
                (
                f"Past price action informs future expectations. {beta_interp} {vol_interp} "
                f"The annual trading range ({fifty_two_wk_low_fmt} - {fifty_two_wk_high_fmt}) defines historical price boundaries. This volatility profile is relevant for forecast modeling."
                )
             ]
            narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
            narrative_options = [
                (
                f"Price statistics are critical inputs for active traders. {beta_interp} {vol_interp} Volatility directly impacts option pricing and risk management (stop-loss placement). "
                f"The 52-week high/low ({fifty_two_wk_high_fmt} / {fifty_two_wk_low_fmt}) often act as significant psychological support/resistance levels. Robust average volume ({avg_vol_3m_fmt}) ensures reasonable trade execution liquidity."
                ),
                (
                f"Traders rely heavily on price stats. {beta_interp} {vol_interp} Volatility affects options and risk settings. "
                f"Yearly highs/lows ({fifty_two_wk_high_fmt}, {fifty_two_wk_low_fmt}) are key psychological levels. Good volume ({avg_vol_3m_fmt}) facilitates easier trading."
                )
            ]
            narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
             narrative_options = [
                (
                f"Analyzing price history offers perspective on risk and market perception. {beta_interp} A lower beta might be preferred by conservative investors. {vol_interp} Lower volatility can indicate stability. "
                f"The 52-week range ({fifty_two_wk_low_fmt} - {fifty_two_wk_high_fmt}) helps assess the current price relative to past sentiment extremes, aiding in identifying potential over/undervaluation from a historical perspective."
                ),
                (
                f"Price history provides risk and sentiment context. {beta_interp} Lower beta can appeal to risk-averse investors. {vol_interp} Stability is often linked to lower volatility. "
                f"The annual range ({fifty_two_wk_low_fmt} - {fifty_two_wk_high_fmt}) shows historical extremes, useful for judging current price levels against past sentiment."
                )
            ]
             narrative = random.choice(narrative_options)
        else: # Default
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
    """Generates Short Selling Info section with enhanced narrative on sentiment and squeeze potential."""
    try:
        site_name = rdata.get('site_name', '').lower()
        short_data = rdata.get('short_selling_data')
        if not isinstance(short_data, dict):
             short_data = {}
             logging.warning("short_selling_data not found or not a dict, using empty.")

        content = generate_metrics_section_content(short_data)

        # --- Extract data ---
        short_percent_float_fmt = format_html_value(short_data.get('Short % of Float'), 'percent_direct')
        short_ratio_fmt = format_html_value(short_data.get('Short Ratio (Days To Cover)'), 'ratio')
        shares_short_fmt = format_html_value(short_data.get('Shares Short'), 'integer')
        # Optional: Calculate Short % of Outstanding if possible
        short_percent_outstanding_fmt = "N/A"
        shares_short_val = _safe_float(short_data.get('Shares Short'))
        shares_outstanding_val = _safe_float(rdata.get('share_statistics_data', {}).get('Shares Outstanding'))
        if shares_short_val is not None and shares_outstanding_val is not None and shares_outstanding_val > 0:
             short_percent_outstanding_val = (shares_short_val / shares_outstanding_val) * 100
             short_percent_outstanding_fmt = format_html_value(short_percent_outstanding_val, 'percent_direct')


        # --- Enhanced Narrative ---
        narrative = ""
        short_summary_options = [
            f"Key short interest indicators include Short % of Float ({short_percent_float_fmt}) and the Short Ratio ({short_ratio_fmt}).",
            f"Short selling activity is measured by Short % of Float ({short_percent_float_fmt}) and Days to Cover ({short_ratio_fmt}).",
            f"Relevant short data includes Short % of Float ({short_percent_float_fmt}) and the Short Ratio ({short_ratio_fmt})."
            ]
        short_summary = random.choice(short_summary_options)

        level_interp_options = {'high': ["very high", "extremely high", "significant"], 'mid_high':["high", "elevated", "notable"], 'mid_low':["moderate", "medium", "reasonable"], 'low':["low", "minimal", "limited"]}
        sentiment_interp_options = {'high': ["significant bearish sentiment", "strong negative bets", "widespread bearish positioning"], 'mid_high': ["notable bearish sentiment", "meaningful negative speculation", "considerable short interest"], 'mid_low': ["moderate bearish sentiment", "some negative expectations", "a degree of short positioning"], 'low': ["low bearish sentiment", "minimal shorting activity", "little negative pressure from shorts"]}
        squeeze_interp_options = {'high': ["high", "significant", "strong"], 'mid_high':["elevated", "increased", "meaningful"], 'mid_low':["moderate", "some", "potential"], 'low':["low", "limited", "minimal"]}

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
                 short_ratio_interp_options = [
                    f"The high Days to Cover ({short_ratio_fmt}) implies it would take significant time for shorts to cover, amplifying potential short squeeze intensity.",
                    f"With {short_ratio_fmt} Days to Cover, shorts face a lengthy exit, potentially fueling a stronger squeeze.",
                    f"A high Short Ratio ({short_ratio_fmt}) suggests covering would take many days, increasing squeeze risk/potential."
                 ]
                 short_ratio_interp = random.choice(short_ratio_interp_options)
             elif sr_val > 5:
                 short_ratio_interp_options = [
                    f"The moderate Days to Cover ({short_ratio_fmt}) suggests a reasonable time needed for shorts to exit, contributing to {squeeze_potential} squeeze potential.",
                    f"{short_ratio_fmt} Days to Cover indicates shorts need some time to cover, supporting {squeeze_potential} squeeze possibilities.",
                    f"A medium Short Ratio ({short_ratio_fmt}) implies covering takes multiple days, adding to the {squeeze_potential} squeeze outlook."
                 ]
                 short_ratio_interp = random.choice(short_ratio_interp_options)

             else:
                 short_ratio_interp_options = [
                    f"The low Days to Cover ({short_ratio_fmt}) indicates shorts could cover relatively quickly, potentially limiting squeeze duration.",
                    f"With only {short_ratio_fmt} Days to Cover, shorts can exit rapidly, possibly capping squeeze momentum.",
                    f"A low Short Ratio ({short_ratio_fmt}) means covering is fast, which might reduce the impact of any squeeze."
                 ]
                 short_ratio_interp = random.choice(short_ratio_interp_options)


        if "finances forecast" in site_name:
             narrative_options = [
                (
                f"Short interest reflects market sentiment that could impact future price realization against forecasts. The current Short % of Float is {level_interp} ({short_percent_float_fmt}), indicating {sentiment_implication}. "
                f"{short_ratio_interp} While high short interest can act as overhead resistance, it also represents latent buying demand if sentiment reverses (a 'short squeeze'), potentially accelerating moves towards positive forecast targets."
                ),
                (
                 f"Market bets against the stock (short interest) can affect its path towards forecasts. The {level_interp} Short % of Float ({short_percent_float_fmt}) signals {sentiment_implication}. "
                 f"{short_ratio_interp} High short interest creates resistance but also fuels potential squeezes if the outlook improves, possibly speeding up price gains."
                )
             ]
             narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
             narrative_options = [
                (
                f"Short interest data is a crucial sentiment gauge for traders. The {level_interp} Short % of Float ({short_percent_float_fmt}) signals {sentiment_implication} and creates {squeeze_potential} short squeeze potential. "
                f"{short_ratio_interp} Traders often monitor significant changes in short interest ({shares_short_fmt} shares short) for shifts in sentiment or catalysts for volatility. High short interest combined with a technical breakout can lead to explosive moves."
                ),
                (
                 f"Traders watch short interest closely for sentiment clues. A {level_interp} Short % of Float ({short_percent_float_fmt}) indicates {sentiment_implication} and implies {squeeze_potential} squeeze risk. "
                 f"{short_ratio_interp} Changes in short levels ({shares_short_fmt} shares) can signal sentiment shifts or volatility triggers. A technical breakout on high short interest is a classic squeeze setup."
                )
            ]
             narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
            narrative_options = [
                (
                f"While not a primary driver of intrinsic value, understanding short interest provides insights into market perception. A {level_interp} Short % of Float ({short_percent_float_fmt}) suggests {sentiment_implication}. "
                f"This warrants investigating the reasons behind the bearish bets – does it point to perceived fundamental weaknesses or simply overvaluation? {short_ratio_interp} Persistently high short interest might be a red flag requiring deeper due diligence."
                ),
                (
                 f"Short interest offers a view on market sentiment, though it doesn't define value. The {level_interp} level ({short_percent_float_fmt}) implies {sentiment_implication}. "
                 f"It's important to understand *why* shorts are present - are there fundamental concerns or just valuation disagreements? {short_ratio_interp} Ongoing high short interest could signal underlying issues needing investigation."
                )
            ]
            narrative = random.choice(narrative_options)
        else: # Default
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
    """Helper specifically for the analyst grid layout (Robust NA handling)"""
    try:
        if not isinstance(analyst_data, dict):
             logging.warning("Analyst data is not a dict, cannot generate grid.")
             return "<p>Analyst consensus data could not be processed.</p>"

        # Filter valid data using format_html_value check
        valid_data_formatted = {}
        for k, v in analyst_data.items():
             # Guess format type for display
             format_type = 'string'
             # More specific key checks
             k_lower = str(k).lower()
             if 'price' in k_lower: format_type = 'currency'
             elif 'opinions' in k_lower or 'number' in k_lower: format_type = 'integer'
             elif 'recommendation' in k_lower: format_type = 'factor' # Treat recommendation as string factor

             formatted_v = format_html_value(v, format_type)
             if formatted_v != "N/A":
                 valid_data_formatted[str(k)] = formatted_v # Ensure key is string

        if not valid_data_formatted:
            return "<p>No specific analyst consensus data is currently available or displayable.</p>"

        html = '<div class="analyst-grid">'
        # Define preferred order robustly checking if keys exist in formatted data
        key_order = ["Recommendation", "Mean Target Price", "High Target Price", "Low Target Price", "Number of Analyst Opinions"]
        displayed_keys = set()

        # Display in preferred order
        for key in key_order:
            if key in valid_data_formatted:
                 html += f'<div class="analyst-item"><span>{key}:</span> {valid_data_formatted[key]}</div>'
                 displayed_keys.add(key)

        # Display any other valid data found (handles potential extra fields)
        for key, value in valid_data_formatted.items():
            if key not in displayed_keys:
                html += f'<div class="analyst-item"><span>{key}:</span> {value}</div>'

        html += '</div>'
        return html
    except Exception as e:
         logging.error(f"Error generating analyst grid: {e}")
         return "<p>Error displaying analyst consensus data.</p>"


def generate_analyst_insights_html(ticker, rdata):
    """Generates Analyst Insights with enhanced narrative focus and potential calculation."""
    try:
        site_name = rdata.get('site_name', '').lower()
        analyst_data = rdata.get('analyst_info_data')
        if not isinstance(analyst_data, dict):
             analyst_data = {}
             logging.warning("analyst_info_data not found or not a dict, using empty.")

        grid_html = generate_analyst_grid_html(analyst_data) # Use the improved grid generator

        # --- Extract data for narrative ---
        recommendation = format_html_value(analyst_data.get('Recommendation'), 'factor') # Keep as string
        mean_target_fmt = format_html_value(analyst_data.get('Mean Target Price'), 'currency')
        high_target_fmt = format_html_value(analyst_data.get('High Target Price'), 'currency')
        low_target_fmt = format_html_value(analyst_data.get('Low Target Price'), 'currency')
        num_analysts_fmt = format_html_value(analyst_data.get('Number of Analyst Opinions'), 'integer')
        current_price = _safe_float(rdata.get('current_price'))
        current_price_fmt = format_html_value(current_price, 'currency')

        # --- Calculate & Format Potential Upside/Downside ---
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
                f" The average target ({mean_target_fmt}) suggests roughly <strong>{mean_potential_fmt} potential {potential_direction}</strong> compared to the current price ({current_price_fmt}).",
                f" Relative to the current price ({current_price_fmt}), the mean analyst target ({mean_target_fmt}) points to approximately <strong>{mean_potential_fmt} {potential_direction}</strong>."
             ]
             potential_summary = random.choice(potential_summary_options)


        # --- Enhanced Narrative ---
        narrative = ""
        analyst_count_context_options = [
             f"This consensus is based on opinions from {num_analysts_fmt} analyst(s)." if num_analysts_fmt != 'N/A' else "The number of contributing analysts is unspecified.",
             f"{num_analysts_fmt} analyst(s) contributed to this consensus view." if num_analysts_fmt != 'N/A' else "The analyst count for this consensus is not available.",
             f"Data reflects input from {num_analysts_fmt} analyst(s)." if num_analysts_fmt != 'N/A' else "Analyst participation count is unknown."
            ]
        analyst_count_context = random.choice(analyst_count_context_options)


        if "finances forecast" in site_name:
            narrative_options = [
                (
                f"Analyst consensus provides an external perspective that can corroborate or challenge internal forecasts. The current Wall Street recommendation for {ticker} is <strong>'{recommendation}'</strong>. {analyst_count_context} "
                f"The average price target stands at {mean_target_fmt} (ranging from {target_range_fmt}).{potential_summary} Significant shifts in analyst ratings or targets often act as catalysts influencing market price towards forecast levels."
                ),
                (
                 f"External analyst views offer a check on internal forecasts. Wall Street's current rating for {ticker} is <strong>'{recommendation}'</strong>. {analyst_count_context} "
                 f"Their average target is {mean_target_fmt} (range: {target_range_fmt}).{potential_summary} Changes in ratings or targets can act as market movers, potentially validating or contradicting forecasts."
                )
             ]
            narrative = random.choice(narrative_options)
        elif "radar stocks" in site_name:
             narrative_options = [
                (
                f"Analyst actions can be significant short-term catalysts for traders. The consensus rating is <strong>'{recommendation}'</strong> ({num_analysts_fmt} analysts). "
                f"Price targets (Mean: {mean_target_fmt}, Range: {target_range_fmt}) can act as psychological support/resistance or trigger algorithmic trading.{potential_summary} Watch for upgrades/downgrades or target revisions, as these often cause immediate price reactions."
                ),
                (
                 f"Traders should note analyst actions as potential catalysts. The consensus view is <strong>'{recommendation}'</strong> ({num_analysts_fmt} analysts). "
                 f"Targets (Avg: {mean_target_fmt}, Range: {target_range_fmt}) can influence trading algorithms and sentiment.{potential_summary} Upgrades, downgrades, or target changes frequently spark price volatility."
                )
            ]
             narrative = random.choice(narrative_options)
        elif "bernini capital" in site_name:
             narrative_options = [
                (
                f"While analyst opinions are considered, they supplement rather than replace independent fundamental research. The current consensus is <strong>'{recommendation}'</strong> ({num_analysts_fmt} analysts), with a mean target of {mean_target_fmt} (Range: {target_range_fmt}).{potential_summary} "
                f"Value investors should critically assess if the market price and analyst targets align with their own calculated intrinsic value and margin of safety requirements. Suggest reviewing analyst rationale if possible."
                ),
                (
                 f"Analyst views provide context but don't substitute for independent analysis. The Street's consensus is <strong>'{recommendation}'</strong> ({num_analysts_fmt} analysts), targeting {mean_target_fmt} on average (Range: {target_range_fmt}).{potential_summary} "
                 f"Value investors must compare these targets against their own intrinsic value estimates and required safety margin. Understanding the analysts' reasoning is beneficial."
                )
             ]
             narrative = random.choice(narrative_options)
        else: # Default
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
    """Generates the TECHNICAL ANALYSIS summary section (Enhanced with interpretations)."""
    try:
        site_name = rdata.get('site_name', '').lower()
        sentiment = rdata.get('sentiment', 'Neutral')
        current_price = rdata.get('current_price')
        last_date_obj = rdata.get('last_date', datetime.now())
        last_date_fmt = format_html_value(last_date_obj, 'date')
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        if not isinstance(detailed_ta_data, dict):
            detailed_ta_data = {}
            logging.warning("detailed_ta_data not found or not a dict, using empty.")


        # --- Extract TA data with safe defaults using _safe_float ---
        price_f = _safe_float(current_price)
        sma20 = _safe_float(detailed_ta_data.get('SMA_20')); sma50 = _safe_float(detailed_ta_data.get('SMA_50'))
        sma100 = _safe_float(detailed_ta_data.get('SMA_100')); sma200 = _safe_float(detailed_ta_data.get('SMA_200'))
        support = _safe_float(detailed_ta_data.get('Support_30D')); resistance = _safe_float(detailed_ta_data.get('Resistance_30D'))
        latest_rsi = _safe_float(detailed_ta_data.get('RSI_14'))
        macd_line = _safe_float(detailed_ta_data.get('MACD_Line')); macd_signal = _safe_float(detailed_ta_data.get('MACD_Signal'))
        macd_hist = _safe_float(detailed_ta_data.get('MACD_Hist'))
        bb_lower = _safe_float(detailed_ta_data.get('BB_Lower')); bb_upper = _safe_float(detailed_ta_data.get('BB_Upper'))
        # Optional data (Example: Extract Volume - needs to be added to rdata in reporter)
        # current_volume = _safe_float(detailed_ta_data.get('Volume')) # Assuming latest volume is here
        # avg_volume = _safe_float(detailed_ta_data.get('Volume_SMA20')) # Assuming SMA20 volume is here
        rsi_divergence_bearish = rdata.get('rsi_divergence_bearish', False) # Assuming these are pre-calculated
        rsi_divergence_bullish = rdata.get('rsi_divergence_bullish', False)

        # --- Helper for MA status with tolerance ---
        def price_vs_ma(price_val, ma_val):
            if price_val is None or ma_val is None: return ('trend-neutral', '', 'Neutral')
            if price_val > ma_val * 1.001: return ('trend-up', f'{get_icon("up")} (Above)', 'Above')
            if price_val < ma_val * 0.999: return ('trend-down', f'{get_icon("down")} (Below)', 'Below')
            return ('trend-neutral', f'{get_icon("neutral")} (At)', 'At')

        sma20_status, sma20_label, sma20_pos = price_vs_ma(price_f, sma20)
        sma50_status, sma50_label, sma50_pos = price_vs_ma(price_f, sma50)
        sma100_status, sma100_label, sma100_pos = price_vs_ma(price_f, sma100)
        sma200_status, sma200_label, sma200_pos = price_vs_ma(price_f, sma200)

        # --- Enhanced Technical Summary Points ---
        summary_points = []
        price_fmt = format_html_value(current_price, 'currency')

        # 1. Trend Analysis (Price vs MAs) - Using random choice for phrasing
        trend_desc = random.choice(["Mixed Trend Signals.", "Unclear Trend Direction.", "Conflicting Trend Indicators."])
        trend_implication = random.choice([
            "suggesting conflicting short-term and long-term momentum requiring careful monitoring.",
            "indicating a battle between short-term and long-term forces.",
            "pointing to indecision in the trend across different timeframes."
            ])
        if sma50_pos == 'Above' and sma200_pos == 'Above':
            trend_desc = random.choice(["Bullish Trend Confirmation", "Positive Trend Alignment", "Uptrend Intact"])
            trend_implication = random.choice([
                f"as price ({price_fmt}) holds above both the key 50-day and 200-day SMAs, indicating positive momentum across timeframes.",
                f"with price ({price_fmt}) over the crucial 50d and 200d averages, signaling broad positive momentum.",
                f"since the price ({price_fmt}) remains above both primary SMAs, confirming bullish sentiment."
            ])
        elif sma50_pos == 'Below' and sma200_pos == 'Below':
            trend_desc = random.choice(["Bearish Trend Confirmation", "Negative Trend Alignment", "Downtrend Intact"])
            trend_implication = random.choice([
                f"with price ({price_fmt}) below both the 50-day and 200-day SMAs, signaling prevailing weakness.",
                f"as the price ({price_fmt}) trades under the key 50d and 200d averages, indicating bearish control.",
                f"since the price ({price_fmt}) is beneath both major SMAs, confirming negative momentum."
            ])
        elif sma50_pos == 'Above' and sma200_pos == 'Below':
             trend_desc = random.choice(["Potential Trend Reversal / Short-term Strength", "Possible Bottoming / Near-term Upside", "Short-term Bullish vs Long-term Bearish"])
             trend_implication = random.choice([
                 f"showing price ({price_fmt}) above the 50-day SMA but still below the 200-day SMA, possibly indicating early signs of a turnaround or a rally within a longer downtrend.",
                 f"with price ({price_fmt}) over the 50d but under the 200d average, suggesting a potential shift or temporary strength against the main trend.",
                 f"as the price ({price_fmt}) crosses the 50d SMA but faces resistance near the 200d, hinting at a possible reversal attempt."
             ])
        elif sma50_pos == 'Below' and sma200_pos == 'Above':
             trend_desc = random.choice(["Potential Pullback / Short-term Weakness", "Possible Consolidation in Uptrend", "Short-term Bearish vs Long-term Bullish"])
             trend_implication = random.choice([
                 f"as price ({price_fmt}) dips below the 50-day SMA while remaining above the 200-day SMA, suggesting a possible consolidation or pullback within a longer uptrend.",
                 f"with price ({price_fmt}) under the 50d but over the 200d average, indicating a potential pause or dip within the primary uptrend.",
                 f"since the price ({price_fmt}) breaks the 50d SMA support but holds above the 200d, pointing to short-term weakness in a longer bull phase."
             ])
        summary_points.append(f"<strong>Trend:</strong> {trend_desc}, {trend_implication}")

        # 2. Momentum (RSI) + Divergence Check
        rsi_text = "Momentum (RSI): Data N/A."
        if latest_rsi is not None:
            rsi_level = random.choice(["Neutral", "Balanced", "Inconclusive"])
            rsi_icon = get_icon('neutral')
            rsi_implication = random.choice([
                "indicating balanced momentum with no immediate overbought/oversold pressure.",
                "suggesting neither excessive buying nor selling force currently.",
                "showing momentum is not at an extreme, offering few immediate reversal signals."
                ])
            if latest_rsi > 70:
                rsi_level = random.choice(["Overbought", "Extended", "Stretched"]); rsi_icon = get_icon('warning')
                rsi_implication = random.choice([
                    f"suggesting the rally might be overextended and vulnerable to a pullback.",
                    f"indicating buying pressure may be excessive, raising pullback risks.",
                    f"warning that the recent gains could be unsustainable short-term."
                    ])
            elif latest_rsi < 30:
                rsi_level = random.choice(["Oversold", "Depressed", "Washed Out"]); rsi_icon = get_icon('positive')
                rsi_implication = random.choice([
                    f"potentially indicating the sell-off is exhausted and ripe for a rebound.",
                    f"suggesting selling pressure might be depleted, hinting at a possible bounce.",
                    f"potentially signaling that the downside is overdone, setting up for a recovery."
                    ])

            divergence_text = ""
            if rsi_divergence_bearish: divergence_text = f" {get_icon('divergence')} <strong>Warning: Potential Bearish Divergence detected.</strong>"
            if rsi_divergence_bullish: divergence_text = f" {get_icon('divergence')} <strong>Note: Potential Bullish Divergence detected.</strong>"

            rsi_text = f"<strong>Momentum (RSI):</strong> {rsi_icon} {latest_rsi:.1f} ({rsi_level}), {rsi_implication}{divergence_text}"
        summary_points.append(rsi_text)

        # 3. Momentum (MACD)
        macd_text = "Momentum (MACD): Data N/A."
        if macd_line is not None and macd_signal is not None and macd_hist is not None:
             macd_pos_desc = ""
             macd_icon = get_icon('neutral')
             macd_implication = ""
             line_fmt = format_html_value(macd_line, precision=3) # More precision for MACD
             sig_fmt = format_html_value(macd_signal, precision=3)

             if macd_line > macd_signal:
                 macd_pos_desc = random.choice([
                     f"Line ({line_fmt}) above Signal ({sig_fmt}) (Bullish Crossover)",
                     f"Bullish Stance (Line: {line_fmt} > Signal: {sig_fmt})",
                     f"Positive MACD (Line above Signal: {line_fmt} vs {sig_fmt})"
                     ])
                 macd_icon = get_icon('up')
                 if macd_hist > 0:
                     macd_implication = random.choice([
                         "with positive Histogram, confirming strengthening bullish momentum.",
                         "and positive Histogram reinforces the upward momentum.",
                         "supported by a positive Histogram, signaling growing bullish strength."
                         ])
                 else:
                     macd_implication = random.choice([
                         "though Histogram is negative, suggesting weakening bullish momentum or potential bearish crossover soon.",
                         "but negative Histogram hints bullish strength may be fading or a reversal looms.",
                         "yet negative Histogram warns the bullish signal might weaken or reverse shortly."
                         ])
             else:
                 macd_pos_desc = random.choice([
                     f"Line ({line_fmt}) below Signal ({sig_fmt}) (Bearish Crossover)",
                     f"Bearish Stance (Line: {line_fmt} < Signal: {sig_fmt})",
                     f"Negative MACD (Line below Signal: {line_fmt} vs {sig_fmt})"
                     ])
                 macd_icon = get_icon('down')
                 if macd_hist < 0:
                     macd_implication = random.choice([
                         "with negative Histogram, confirming strengthening bearish momentum.",
                         "and negative Histogram reinforces the downward momentum.",
                         "supported by a negative Histogram, signaling growing bearish strength."
                         ])
                 else:
                     macd_implication = random.choice([
                         "though Histogram is positive, suggesting weakening bearish momentum or potential bullish crossover soon.",
                         "but positive Histogram hints bearish strength may be fading or a reversal looms.",
                         "yet positive Histogram warns the bearish signal might weaken or reverse shortly."
                         ])
             macd_text = f"<strong>Momentum (MACD):</strong> {macd_icon} {macd_pos_desc}, {macd_implication}"
        summary_points.append(macd_text)

        # 4. Volatility (Bollinger Bands)
        bb_text = "Volatility (BBands): Data N/A."
        if price_f is not None and bb_lower is not None and bb_upper is not None:
             bb_pos = random.choice(["within Bands", "inside the Bands", "between the Bands"])
             bb_icon = get_icon('neutral')
             bb_implication = random.choice([
                 "currently operating within its typical volatility range.",
                 "suggesting price is within its recent statistical boundaries.",
                 "indicating normal volatility conditions prevail."
                 ])
             bb_action = random.choice([
                 "Monitor for potential breakouts or reversions towards the mean.",
                 "Watch for moves towards the band edges or potential mean reversion.",
                 "Keep an eye on potential breakouts or pullbacks to the middle band."
                 ])
             if price_f > bb_upper:
                 bb_pos = random.choice([
                     f"above Upper Band ({format_html_value(bb_upper, 'currency')})",
                     f"piercing the Upper Band ({format_html_value(bb_upper, 'currency')})",
                     f"outside the Upper Band ({format_html_value(bb_upper, 'currency')})"
                     ])
                 bb_icon = get_icon('warning')
                 bb_implication = random.choice([
                     "signaling high volatility and a potential short-term overbought condition.",
                     "indicating a volatility spike and possible temporary overextension.",
                     "suggesting increased volatility and raising chances of a near-term pullback."
                     ])
                 bb_action = random.choice([
                     "Watch for potential pullback or consolidation.",
                     "Monitor for signs of reversal or sideways movement.",
                     "Look for confirmation signals before assuming trend continuation."
                     ])
             elif price_f < bb_lower:
                 bb_pos = random.choice([
                     f"below Lower Band ({format_html_value(bb_lower, 'currency')})",
                     f"piercing the Lower Band ({format_html_value(bb_lower, 'currency')})",
                     f"outside the Lower Band ({format_html_value(bb_lower, 'currency')})"
                     ])
                 bb_icon = get_icon('positive')
                 bb_implication = random.choice([
                     "indicating high volatility and a potential short-term oversold state.",
                     "signaling a volatility surge and possible temporary overselling.",
                     "suggesting increased volatility and raising chances of a near-term rebound."
                     ])
                 bb_action = random.choice([
                     "Look for signs of potential rebound or stabilization.",
                     "Monitor for reversal patterns or consolidation near the lows.",
                     "Watch for confirmation signals indicating a potential bottom."
                     ])
             bb_text = f"<strong>Volatility (BBands):</strong> {bb_icon} Price {bb_pos}, {bb_implication} {bb_action}"
        summary_points.append(bb_text)

        # 5. Support & Resistance
        sr_text = "Support/Resistance (30d): Levels N/A."
        if support is not None and resistance is not None:
            support_fmt = format_html_value(support, 'currency'); resistance_fmt = format_html_value(resistance, 'currency')
            sr_options = [
                f"Key near-term levels identified around <strong>{support_fmt}</strong> (support) and <strong>{resistance_fmt}</strong> (resistance). Price action near these zones often dictates the next directional move.",
                f"Immediate support is estimated near <strong>{support_fmt}</strong>, with resistance around <strong>{resistance_fmt}</strong>. Behavior at these 30-day levels is critical for near-term direction.",
                f"Potential near-term floor seen at <strong>{support_fmt}</strong>, ceiling near <strong>{resistance_fmt}</strong>. Reactions to these support/resistance levels are key technical events."
                ]
            sr_text = f"<strong>Support/Resistance (30d):</strong> {random.choice(sr_options)}"
        summary_points.append(sr_text)

        # --- Assemble HTML ---
        sentiment_str = str(sentiment) # Ensure string
        sentiment_icon = get_icon('up' if 'Bullish' in sentiment_str else ('down' if 'Bearish' in sentiment_str else 'neutral'))

        summary_list_html = "".join([f"<li>{point}</li>" for point in summary_points if point and 'N/A' not in point]) # Filter out empty points and N/A placeholders

        # --- Site-Specific Narrative Introduction ---
        narrative_intro_options = {
            'finances forecast': [
                f"Current technical signals provide context for {ticker}'s near-term price potential and may influence the path towards longer-term forecasts. Understanding the prevailing trend and momentum is key to assessing forecast feasibility.",
                f"The technical setup for {ticker} offers insight into short-term possibilities and affects how likely long-term forecasts are. Trend and momentum analysis helps gauge the immediate outlook."
                ],
            'radar stocks': [
                f"This technical snapshot for {ticker} as of {last_date_fmt} highlights key signals for traders. Focus on the interplay between trend, momentum (RSI/MACD), volatility (BBands), and volume to identify potential entry/exit points and manage risk.",
                f"Traders should note these technical highlights for {ticker} (data up to {last_date_fmt}). Analyzing trend, momentum, volatility, and volume is crucial for spotting trade setups and controlling risk."
                ],
            'bernini capital': [
                f"While fundamental analysis is paramount for long-term value investing, technical indicators offer insights into current market sentiment and potential entry/exit timing for {ticker}. This summary outlines the prevailing technical picture.",
                f"Though fundamentals drive long-term value, technicals reveal market sentiment and timing clues for {ticker}. Here's a summary of the current technical landscape."
                ],
            'default': [
                f"The following technical analysis summary for {ticker}, based on data up to {last_date_fmt}, outlines key indicators related to trend, momentum, and volatility. Detailed charts typically provide visual confirmation of these signals.",
                f"This technical overview for {ticker} (as of {last_date_fmt}) covers essential trend, momentum, and volatility indicators. Charts offer more detail, but this summarizes the key signals."
                ]
            }
        narrative_intro = random.choice(narrative_intro_options.get(site_name, narrative_intro_options['default']))

        disclaimer_tech = random.choice([
            "Technical analysis uses past price and volume data to identify potential future trends but offers no guarantees. Combine with fundamental analysis and risk management.",
            "Remember, technical analysis looks at past data to find potential patterns; it doesn't predict the future with certainty. Always use it alongside fundamentals and risk control.",
            "Technical signals are based on historical data and aren't foolproof predictors. Integrate technical views with fundamental research and sound risk management."
        ])


        return f"""
            <div class="sentiment-indicator">
                <span>Overall Technical Sentiment:</span><span class="sentiment-{sentiment_str.lower().replace(' ', '-')}">{sentiment_icon} {sentiment_str}</span>
            </div>
            <div class="narrative">
                <p>{narrative_intro}</p>
                <ul>{summary_list_html}</ul>
            </div>
            <h4>Moving Average Details</h4>
            <div class="ma-summary">
                <div class="ma-item"><span class="label">SMA 20:</span> <span class="value">{format_html_value(sma20, 'currency')}</span> <span class="status {sma20_status}">{sma20_label}</span></div>
                <div class="ma-item"><span class="label">SMA 50:</span> <span class="value">{format_html_value(sma50, 'currency')}</span> <span class="status {sma50_status}">{sma50_label}</span></div>
                <div class="ma-item"><span class="label">SMA 100:</span> <span class="value">{format_html_value(sma100, 'currency')}</span> <span class="status {sma100_status}">{sma100_label}</span></div>
                <div class="ma-item"><span class="label">SMA 200:</span> <span class="value">{format_html_value(sma200, 'currency')}</span> <span class="status {sma200_status}">{sma200_label}</span></div>
            </div>
            <p class="disclaimer">{disclaimer_tech}</p>
            """
    except Exception as e:
        return _generate_error_html("Technical Analysis Summary", str(e))


def generate_recent_news_html(ticker, rdata):
    """Generates the Recent News section."""
    # NOTE: This function was commented out in wordpress_reporter.py
    # It depends on 'news_list' being populated in rdata, which currently doesn't happen.
    # You would need to uncomment the line `rdata['news_list'] = fa.extract_news(fundamentals)`
    # in `wordpress_reporter.py` for this to work.
    try:
        site_name = rdata.get('site_name', '').lower()
        news_list = rdata.get('news_list', []) # Expecting a list of dicts
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
                # Use safe formatting for date
                published_fmt = format_html_value(item.get('published'), 'date') # Assumes 'published' holds date info

                items_html += f"""
                <div class="news-item">
                    <h4><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h4>
                    <div class="news-meta">
                        <span>Publisher: {publisher}</span>
                        <span>Published: {published_fmt}</span>
                    </div>
                </div>
                """

        # Site-specific intro (optional, could be simple)
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
    """Generates the FAQ section with enhanced, nuanced, and site-specific answers."""
    try:
        site_name = rdata.get('site_name', '').lower()
        # --- Gather data safely ---
        current_price = _safe_float(rdata.get('current_price'))
        forecast_1y = _safe_float(rdata.get('forecast_1y'))
        overall_pct_change = _safe_float(rdata.get('overall_pct_change'), default=0.0)
        sentiment = rdata.get('sentiment', 'Neutral')
        volatility = _safe_float(rdata.get('volatility'))
        valuation_data = rdata.get('valuation_data', {})
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        health_data = rdata.get('financial_health_data', {})
        risk_items = rdata.get('risk_items', [])

        if not isinstance(valuation_data, dict): valuation_data = {}
        if not isinstance(detailed_ta_data, dict): detailed_ta_data = {}
        if not isinstance(health_data, dict): health_data = {}

        latest_rsi = _safe_float(detailed_ta_data.get('RSI_14'))
        debt_equity_fmt = format_html_value(health_data.get('Debt/Equity (MRQ)'), 'ratio')
        current_price_fmt = format_html_value(current_price, 'currency')
        forecast_1y_fmt = format_html_value(forecast_1y, 'currency')

        faq_items = []
        # Determine forecast direction description
        up_down_neutral_options = {
            'up_strong': ["increase significantly", "show strong gains", "trend sharply higher"],
            'up_mod': ["increase moderately", "see modest gains", "trend gently higher"],
            'down_strong': ["decrease significantly", "experience sharp losses", "trend sharply lower"],
            'down_mod': ["decrease moderately", "see modest losses", "trend gently lower"],
            'flat': ["remain relatively stable", "trade sideways", "show minimal change"]
        }
        if overall_pct_change > 10: up_down_neutral = random.choice(up_down_neutral_options['up_strong'])
        elif overall_pct_change > 1: up_down_neutral = random.choice(up_down_neutral_options['up_mod'])
        elif overall_pct_change < -10: up_down_neutral = random.choice(up_down_neutral_options['down_strong'])
        elif overall_pct_change < -1: up_down_neutral = random.choice(up_down_neutral_options['down_mod'])
        else: up_down_neutral = random.choice(up_down_neutral_options['flat'])

        # Determine risk mention
        risk_count = 0
        if isinstance(risk_items, list):
             risk_count = len([r for r in risk_items if isinstance(r, str) and not any(keyword in r for keyword in ['Market Risk', 'Sector/Industry', 'Economic Risk', 'Company-Specific'])])

        risk_mention_options = [
             f"However, note that {risk_count} potentially significant risk factor(s) specific to {ticker} were identified (see Risk Factors section)." if risk_count > 0 else "Standard market and sector risks always apply.",
             f"Be aware that {risk_count} specific risks for {ticker} were highlighted (view Risk Factors)." if risk_count > 0 else "Remember that general market risks are always present.",
             f"It's important to consider the {risk_count} unique risks mentioned for {ticker} (check Risk Factors)." if risk_count > 0 else "Factor in the usual market and industry risks."
        ]
        risk_mention = random.choice(risk_mention_options)

        # --- Q1: Forecast ---
        q1_ans_options = [
            f"Based on current models, the average 1-year price forecast for {ticker} is ≈<strong>{forecast_1y_fmt}</strong>. This represents a potential {overall_pct_change:+.1f}% change from the recent price of {current_price_fmt}. Remember, this is a model-driven estimate, not a guarantee, and actual prices will fluctuate based on numerous factors.",
            f"Our models currently project an average 1-year target price of ≈<strong>{forecast_1y_fmt}</strong> for {ticker}, suggesting a potential {overall_pct_change:+.1f}% move from {current_price_fmt}. Keep in mind that forecasts are probabilistic and subject to change.",
            f"The 1-year forecast average for {ticker} stands at ≈<strong>{forecast_1y_fmt}</strong>, implying a {overall_pct_change:+.1f}% potential change relative to the current {current_price_fmt}. This is an estimate; real-world factors will influence the actual price."
        ]
        faq_items.append((f"What is the {ticker} stock price prediction for the next year (2025-2026)?", random.choice(q1_ans_options)))

        # --- Q2: Rise/Fall ---
        sentiment_str = str(sentiment)
        q2_ans_options = [
            f"The 1-year forecast model suggests the price might <strong>{up_down_neutral}</strong> on average ({overall_pct_change:+.1f}% potential). However, short-term direction is highly uncertain and heavily influenced by prevailing market sentiment (currently '{sentiment_str}'), breaking news, and overall economic conditions. Technical indicators (see TA Summary) provide clues for near-term direction.",
            f"While the long-term model anticipates the price could <strong>{up_down_neutral}</strong> ({overall_pct_change:+.1f}% potential), the immediate path is less clear. Market sentiment ('{sentiment_str}'), news events, and economic shifts play a major role. Check the Technical Analysis section for short-term signals.",
            f"Models indicate a potential to <strong>{up_down_neutral}</strong> over the next year ({overall_pct_change:+.1f}% average). But short-term moves are unpredictable, driven by sentiment ('{sentiment_str}'), news flow, and economic factors. Technicals (view TA Summary) offer hints for the near term."
        ]
        faq_items.append((f"Will {ticker} stock go up or down?", random.choice(q2_ans_options)))

        # --- Q3: Good Buy? (Enhanced Site Variations) ---
        q3_ans = ""; rsi_condition = ""; rsi_level = "neutral"; rsi_suggestion = ""
        if latest_rsi is not None:
             rsi_level_text = f"RSI: {latest_rsi:.1f}"
             if latest_rsi < 30: rsi_level = "oversold"; rsi_suggestion = random.choice(["potentially indicating a rebound opportunity", "suggesting it might be due for a bounce", "hinting the sell-off might be overdone"])
             elif latest_rsi > 70: rsi_level = "overbought"; rsi_suggestion = random.choice(["suggesting caution or potential for a pullback", "indicating it might be extended", "warning of possible consolidation"])
             else: rsi_level = "neutral"; rsi_suggestion = random.choice(["indicating balanced momentum", "showing neither strong buying nor selling pressure", "suggesting a lack of immediate directional bias from this indicator"])
             rsi_condition_options = [
                 f"Technically, the RSI indicates {rsi_level} conditions ({rsi_level_text}), {rsi_suggestion}.",
                 f"From a momentum perspective (RSI), the stock is currently {rsi_level} ({rsi_level_text}), {rsi_suggestion}.",
                 f"The RSI reading ({rsi_level_text}) places the stock in {rsi_level} territory, {rsi_suggestion}."
             ]
             rsi_condition = random.choice(rsi_condition_options)

        disclaimer_options = [
            "This report is informational; consult a financial advisor before investing.",
            "Remember, this analysis is for information only; seek professional advice before making investment decisions.",
            "This content does not constitute investment advice; always consult with a qualified advisor."
        ]
        disclaimer = random.choice(disclaimer_options)

        if "finances forecast" in site_name:
            q3_ans_options = [
                (f"Whether {ticker} is a 'good buy' depends on alignment with forecast potential and risk tolerance. The model shows {overall_pct_change:+.1f}% potential over one year. "
                 f"Consider if recent growth and fundamental health trends support this outlook. Current technical sentiment is '{sentiment_str}'. {risk_mention} {disclaimer}"),
                (f"A 'good buy' decision for {ticker} should weigh the forecast ({overall_pct_change:+.1f}% potential) against your risk appetite. Evaluate if the company's growth and financial stability justify the outlook. "
                 f"Technicals are currently '{sentiment_str}'. {risk_mention} {disclaimer}")
            ]
            q3_ans = random.choice(q3_ans_options)
        elif "radar stocks" in site_name:
            q3_ans_options = [
                (f"For traders, 'good buy' depends on technical signals aligning with strategy. Current sentiment is '{sentiment_str}'. {rsi_condition} Look for confirmation from price action, volume, and other indicators discussed in the TA section near identified support/resistance. "
                 f"The forecast ({overall_pct_change:+.1f}% potential) provides context, but short-term trades require precise timing and risk management. {risk_mention} This is not trading advice."),
                (f"Traders define a 'good buy' based on technical setups. Sentiment is '{sentiment_str}'. {rsi_condition} Confirm signals with price, volume, and key levels (see TA). "
                 f"While the forecast ({overall_pct_change:+.1f}% potential) exists, timing and risk control are paramount for trades. {risk_mention} This isn't a trade recommendation.")
            ]
            q3_ans = random.choice(q3_ans_options)
        elif "bernini capital" in site_name:
            fwd_pe_fmt = format_html_value(valuation_data.get('Forward P/E'), 'ratio')
            q3_ans_options = [
                (f"From a value perspective, 'good buy' means acquiring {ticker} at a price offering a margin of safety relative to its intrinsic value. Assess the fundamental health (e.g., Debt/Equity: {debt_equity_fmt}), profitability, and valuation ({fwd_pe_fmt} Fwd P/E). "
                 f"Does the current price ({current_price_fmt}) adequately compensate for the risks involved? {risk_mention} The forecast ({overall_pct_change:+.1f}% potential) is one input, but long-term fundamentals are key. {disclaimer}"),
                (f"Value investors determine a 'good buy' by comparing price ({current_price_fmt}) to intrinsic worth, seeking a safety margin. Examine fundamentals like debt ({debt_equity_fmt}), earnings power, and valuation (e.g., {fwd_pe_fmt} Fwd P/E). "
                 f"Is the potential reward worth the risk? {risk_mention} Fundamentals, not just forecasts ({overall_pct_change:+.1f}% potential), drive long-term value. {disclaimer}")
            ]
            q3_ans = random.choice(q3_ans_options)
        else: # Default
            q3_ans_options = [
                (f"Determining if {ticker} is a 'good buy' requires evaluating multiple factors. Technical sentiment is '{sentiment_str}', while the 1-year forecast suggests {overall_pct_change:+.1f}% potential. {rsi_condition} "
                 f"Consider the valuation, financial health, growth prospects, and {risk_mention} Align these factors with your personal investment strategy and risk tolerance. {disclaimer}"),
                (f"Whether {ticker} is a 'good buy' now involves balancing various elements: '{sentiment_str}' technicals, a {overall_pct_change:+.1f}% forecast potential, and {rsi_condition} "
                 f"Weigh the company's valuation, stability, growth, and {risk_mention} against your own investment goals and risk profile. {disclaimer}")
            ]
            q3_ans = random.choice(q3_ans_options)
        faq_items.append((f"Is {ticker} stock a good investment right now?", q3_ans))

        # --- Q4: Volatility ---
        vol_level = "N/A"; vol_comp = ""
        volatility_fmt = format_html_value(volatility, 'percent_direct', 1)
        if volatility is not None:
            if volatility > 40: vol_level = random.choice(["high", "elevated", "significant"])
            elif volatility > 20: vol_level = random.choice(["moderate", "average", "typical"])
            else: vol_level = random.choice(["low", "subdued", "relatively stable"])
            beta_fmt = format_html_value(rdata.get('stock_price_stats_data',{}).get('Beta'), 'ratio')
            if beta_fmt != 'N/A':
                vol_comp_options = [
                    f"This aligns with its Beta of {beta_fmt} (see Stock Price Statistics).",
                    f"This is consistent with its market sensitivity (Beta: {beta_fmt}).",
                    f"Its Beta ({beta_fmt}) reflects a similar level of market correlation."
                ]
                vol_comp = random.choice(vol_comp_options)

        q4_ans_options = [
            f"Based on recent 30-day price action, {ticker}'s annualized volatility is ≈<strong>{volatility_fmt}</strong>. This level is currently considered {vol_level}, indicating the degree of recent price fluctuation. {vol_comp} Higher volatility means larger potential price swings (both up and down).",
            f"{ticker}'s recent price swing intensity (annualized 30-day volatility) is measured at ≈<strong>{volatility_fmt}</strong>. This is currently viewed as {vol_level}. {vol_comp} Greater volatility implies wider potential price movements.",
            f"The stock's recent volatility (30d annualized) is approximately <strong>{volatility_fmt}</strong>, considered {vol_level}. {vol_comp} Volatility reflects the potential range of price changes."
        ]
        faq_items.append((f"How volatile is {ticker} stock?", random.choice(q4_ans_options)))

        # --- Q5: P/E Ratio ---
        pe_ratio_fmt = format_html_value(valuation_data.get('Trailing P/E'), 'ratio')
        fwd_pe_fmt = format_html_value(valuation_data.get('Forward P/E'), 'ratio')
        pe_comment = "unavailable"; pe_context = random.choice(["Compare to industry peers and historical levels.", "Benchmark against competitors and its own past ratios.", "Contextualize using industry averages and historical data."])
        pe_ratio_val = _safe_float(valuation_data.get('Trailing P/E'))
        if pe_ratio_val is not None:
             if pe_ratio_val <= 0: pe_comment = random.choice(["negative (indicating loss or requires context)", "below zero (suggesting no profit or data anomaly)", "negative (check earnings details)"])
             elif pe_ratio_val < 15: pe_comment = random.choice(["relatively low (suggesting potential value or low growth expectations)", "quite low (possibly undervalued or facing slow growth)", "modest (could be value or low expectations)"])
             elif pe_ratio_val < 25: pe_comment = random.choice(["moderate", "average", "in a typical range"])
             else: pe_comment = random.choice(["relatively high (implying market expects strong growth or potential overvaluation)", "elevated (suggesting high growth hopes or richness)", "high (indicating significant growth factored in or potential premium pricing)"])

        q5_ans_options = [
            (f"{ticker}'s Trailing P/E ratio (based on past earnings) is <strong>{pe_ratio_fmt}</strong>, which is considered {pe_comment}. The Forward P/E (based on expected earnings) is {fwd_pe_fmt}. "
             f"A P/E ratio indicates how much investors are paying per dollar of earnings. {pe_context} A high P/E isn't necessarily bad if strong growth justifies it (check PEG ratio in Valuation Metrics)."),
            (f"The Trailing P/E for {ticker} (using historical earnings) stands at <strong>{pe_ratio_fmt}</strong> ({pe_comment}). Looking forward, the P/E based on estimates is {fwd_pe_fmt}. "
             f"P/E reflects the price paid for each dollar of profit. {pe_context} High P/Es need strong growth to be sustainable (see PEG)."),
            (f"Currently, {ticker}'s Trailing P/E is <strong>{pe_ratio_fmt}</strong>, assessed as {pe_comment}. The Forward P/E multiple is {fwd_pe_fmt}. "
             f"This ratio shows the market price relative to earnings per share. {pe_context} A high P/E might be justified by rapid growth (refer to PEG).")
        ]
        faq_items.append((f"What is {ticker}'s P/E ratio and what does it mean?", random.choice(q5_ans_options)))

        # --- Generate HTML ---
        details_html = "".join([f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq_items])
        return details_html
    except Exception as e:
        return _generate_error_html("FAQ", str(e))

def generate_risk_factors_html(ticker, rdata):
    """Generates the enhanced Risk Factors section."""
    try:
        risk_items = rdata.get('risk_items', []) # Get pre-calculated risks from helper
        industry = rdata.get('industry', 'the company\'s specific')
        sector = rdata.get('sector', 'its')

        # Add variations for generic risks if they exist
        generic_risks_map = {
            "Market Risk": [
                "Overall market fluctuations can impact the stock.",
                "Broad market volatility affects all stocks, including this one.",
                "General market downturns pose a risk to the share price."
            ],
            "Sector/Industry Risk": [
                f"Factors specific to the {industry} industry or {sector} sector can affect performance.",
                f"Performance is subject to risks inherent in the {industry} industry and {sector} sector.",
                f"Headwinds within the {industry}/{sector} space could negatively impact the company."
            ],
            "Economic Risk": [
                "Changes in macroeconomic conditions (interest rates, inflation) pose risks.",
                "The company is exposed to broader economic shifts (e.g., interest rates, inflation).",
                "Macroeconomic factors like inflation and interest rate changes present potential risks."
            ],
            "Company-Specific Risk": [
                "Unforeseen company events or news can impact the price.",
                "Specific news or developments related to the company could affect its stock.",
                "Idiosyncratic risks tied to the company's operations or announcements exist."
            ]
        }

        processed_risk_items = []
        if isinstance(risk_items, list):
            for item in risk_items:
                item_str = str(item)
                processed = False
                for generic_key, variations in generic_risks_map.items():
                    # Check if the item *starts* with the generic key phrase (or similar)
                    # This is a basic check, might need refinement based on how risk_items are generated
                    if item_str.startswith(generic_key) or generic_key in item_str:
                        processed_risk_items.append(random.choice(variations))
                        processed = True
                        break
                if not processed:
                    # If it's not a recognized generic risk, add it as is (likely a specific calculated risk)
                    processed_risk_items.append(item_str)
        else:
             logging.warning("risk_items is not a list, cannot process risks.")


        risk_list_html = "".join([f"<li>{get_icon('warning')} {item}</li>" for item in processed_risk_items])

        # Vary the introductory paragraph
        narrative_options = [
            f"<p>Investing in {ticker} involves various risks. This section outlines potential factors identified through data analysis and general market considerations. It is not exhaustive.</p>",
            f"<p>Potential investors in {ticker} should be aware of several risk factors. The following list highlights key considerations based on data and market dynamics, but may not include all possible risks.</p>",
            f"<p>Understanding the risks associated with {ticker} is crucial. Below are potential risks derived from analysis and market awareness; this overview is not fully comprehensive.</p>"
        ]
        narrative = f'<div class="narrative">{random.choice(narrative_options)}</div>'

        return narrative + f"<ul>{risk_list_html}</ul>"
    except Exception as e:
        return _generate_error_html("Risk Factors", str(e))


def generate_report_info_disclaimer_html(generation_time):
    """Generates the final disclaimer and timestamp section (Minor wording tweaks)."""
    try:
        # Ensure generation_time is a datetime object
        if not isinstance(generation_time, datetime):
            logging.warning(f"Invalid generation_time type: {type(generation_time)}. Using current time.")
            generation_time = datetime.now()

        time_str = f"{generation_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    except ValueError: # Handle potential %Z error on some systems
         time_str = f"{generation_time.strftime('%Y-%m-%d %H:%M:%S')} (Timezone N/A)"
    except Exception as e: # Catch other potential strftime errors
         logging.error(f"Error formatting generation_time: {e}")
         time_str = "Error retrieving generation time."


    # Add Current Date based on system clock for context
    current_date_str = datetime.now().strftime('%Y-%m-%d')

    # Slight variations for intro sentences
    gen_on = random.choice(["Report Generated On:", "Analysis Compiled:", "Data As Of (Generation Time):"])
    curr_date = random.choice(["Current Date Context:", "Report Date:", "Date of Viewing:"])
    sources = random.choice(["Primary Data Sources:", "Data Primarily Sourced From:", "Key Data Inputs:"])
    limits = random.choice(["Known Limitations:", "Important Caveats:", "Data Constraints:"])
    disclaimer_title = random.choice(["IMPORTANT DISCLAIMER:", "CRITICAL NOTICE:", "ESSENTIAL DISCLAIMER:"])
    disclaimer_body1 = random.choice([
        "This report is automatically generated for informational and educational purposes ONLY. It does NOT constitute financial, investment, trading, legal, or tax advice, nor should it be interpreted as a recommendation or solicitation to buy, sell, hold, or otherwise transact in any security mentioned.",
        "Generated automatically, this document serves informational and educational roles exclusively. It is NOT financial, investment, trading, legal, or tax advice, and should not be seen as a suggestion or request to trade any mentioned security.",
        "This automated report is purely for information and education. It provides NO financial, investment, trading, legal, or tax recommendations, nor does it solicit any transactions in the securities discussed."
    ])
    disclaimer_body2 = random.choice([
        "All investments carry risk, including the potential loss of principal. Past performance is not indicative or predictive of future results. Market conditions are dynamic and can change rapidly. Financial models and data sources may contain errors or inaccuracies.",
        "Investing involves risk; principal loss is possible. Past results don't predict future outcomes. Markets change quickly. Models and data might have errors.",
        "Risk is inherent in all investments; you could lose money. Past performance doesn't guarantee future results. Markets are volatile. Data and models aren't perfect."
    ])
    disclaimer_body3 = random.choice([
        "Readers are strongly urged to conduct their own thorough and independent due diligence. Consult with one or more qualified, licensed financial professionals, investment advisors, and/or tax advisors before making any investment decisions. Understand your own risk tolerance, financial situation, and investment objectives.",
        "Perform your own detailed research. Speak with qualified financial, investment, and tax advisors before investing. Know your risk tolerance, finances, and goals.",
        "Independent due diligence is essential. Consult licensed professionals (financial, investment, tax) prior to any investment action. Assess your personal risk profile, financial status, and objectives."
    ])
    disclaimer_body4 = random.choice([
        "The creators, generators, and distributors of this report assume NO liability whatsoever for any actions taken, decisions made, or interpretations drawn based on the information provided herein. Use this information entirely at your own risk.",
        "No liability is accepted by the creators or distributors for any actions or decisions based on this report's content. Use this information at your sole discretion and risk.",
        "Responsibility for any use of this information rests solely with the reader. The report's authors and distributors bear no liability for outcomes resulting from its use."
    ])


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
    