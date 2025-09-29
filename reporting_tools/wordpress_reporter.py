import os
import time
import traceback
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import re
import json
import random

# Assuming your other imports (config, data_collection, etc.) are set up
try:
    from config.config import START_DATE, END_DATE # Using config for defaults if needed
    from data_processing_scripts.data_collection import fetch_stock_data
    from data_processing_scripts.macro_data import fetch_macro_indicators
    from data_processing_scripts.data_preprocessing import preprocess_data
    # from feature_engineering import add_technical_indicators # Usually called by preprocess_data
    from Models.prophet_model import train_prophet_model
    import analysis_scripts.fundamental_analysis as fa
    import app.html_components as hc
    import analysis_scripts.technical_analysis as ta_module # Renamed to avoid conflict if you have a 'ta' variable
except ImportError as e:
    print(f"Error importing project files in wordpress_reporter: {e}")
    raise

# Define all possible sections (keys should match values in report_sections_to_include)
ALL_REPORT_SECTIONS = {
    "introduction": hc.generate_introduction_html,
    "metrics_summary": hc.generate_metrics_summary_html,
    "detailed_forecast_table": hc.generate_detailed_forecast_table_html, # If forecast_df exists
    "company_profile": hc.generate_company_profile_html,
    "valuation_metrics": hc.generate_valuation_metrics_html,
    "total_valuation": hc.generate_total_valuation_html,
    "profitability_growth": hc.generate_profitability_growth_html,
    "analyst_insights": hc.generate_analyst_insights_html,
    "financial_health": hc.generate_financial_health_html,
    "historical_performance": hc.generate_historical_performance_html,
    "technical_analysis_summary": hc.generate_technical_analysis_summary_html,
    "short_selling_info": hc.generate_short_selling_info_html,
    "stock_price_statistics": hc.generate_stock_price_statistics_html,
    "dividends_shareholder_returns": hc.generate_dividends_shareholder_returns_html,
    "peer_comparison": hc.generate_peer_comparison_html,
    "conclusion_outlook": hc.generate_conclusion_outlook_html,
    "risk_factors": hc.generate_risk_factors_html,
    "faq": hc.generate_faq_html,
    "report_info_disclaimer": hc.generate_report_info_disclaimer_html
    # Add more if html_components.py has more generators
}

# Content Library Variation Support
def load_content_library(app_root: str):
    """Load content library variations from JSON file for WordPress posts only."""
    try:
        # Determine the actual project root based on the app_root parameter
        # If app_root ends with 'app', then it's already pointing to the app directory
        # If not, we assume it's the project root and look for app/content_library.json
        
        possible_paths = []
        
        # Case 1: app_root is already pointing to the app directory (from auto_publisher)
        if os.path.basename(app_root) == 'app':
            possible_paths.extend([
                os.path.join(app_root, 'content_library.json'),
                os.path.join(app_root, 'report_assets', 'content_library.json'),
                os.path.join(app_root, 'report_assets', 'TSLA_1751805931', 'content_library.json')
            ])
        
        # Case 2: app_root is the project root (from wordpress_reporter itself or other callers)
        possible_paths.extend([
            os.path.join(app_root, 'app', 'content_library.json'),
            os.path.join(app_root, 'app', 'report_assets', 'content_library.json'),
            os.path.join(app_root, 'content_library.json'),
            os.path.join(app_root, 'app', 'report_assets', 'TSLA_1751805931', 'content_library.json')
        ])
        
        # Case 3: Try going up one directory if we're in a subdirectory like reporting_tools
        project_root = os.path.dirname(app_root)
        possible_paths.extend([
            os.path.join(project_root, 'app', 'content_library.json'),
            os.path.join(project_root, 'app', 'report_assets', 'content_library.json')
        ])
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        print(f"WARNING: content_library.json not found in expected locations. Searched paths:")
        for path in possible_paths[:5]:  # Show first 5 paths for debugging
            print(f"  - {path} {'✓' if os.path.exists(path) else '✗'}")
        print("Using inline variations as fallback.")
        return None
    except Exception as e:
        print(f"WARNING: Error loading content_library.json: {e}. Using inline variations.")
        return None

def get_variation(content_lib, section_path, fallback_list=None):
    """Get a random variation from content library path or fallback to provided list."""
    if not content_lib:
        return random.choice(fallback_list) if fallback_list else ""
    
    try:
        # Navigate through nested dict using dot notation like 'introduction.summary_sentence.intros'
        keys = section_path.split('.')
        current = content_lib
        for key in keys:
            current = current[key]
        return random.choice(current) if isinstance(current, list) else current
    except (KeyError, TypeError):
        return random.choice(fallback_list) if fallback_list else ""

def generate_wordpress_introduction_html(ticker, rdata, content_library=None):
    """
    Generate WordPress introduction using content library variations.
    Falls back to original function if content library is not available.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_introduction_html(ticker, rdata)
        
        # Extract data for template variables
        profile_data = rdata.get('profile_data', {})
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        analyst_data = rdata.get('analyst_info_data', {})
        
        company_name = profile_data.get('Company Name', ticker)
        current_price_val = rdata.get('current_price')
        current_price_fmt = hc.format_html_value(current_price_val, 'currency', ticker=ticker)
        
        last_date_obj = rdata.get('last_date', datetime.now())
        last_date_fmt = last_date_obj.strftime('%B %Y')
        
        sma50_val = detailed_ta_data.get('SMA_50')
        sma50_fmt = hc.format_html_value(sma50_val, 'currency', ticker=ticker)
        sma200_val = detailed_ta_data.get('SMA_200')
        sma200_fmt = hc.format_html_value(sma200_val, 'currency', ticker=ticker)
        
        analyst_target_val = hc._safe_float(analyst_data.get('Mean Target Price'))
        analyst_target_fmt = hc.format_html_value(analyst_target_val, 'currency', ticker=ticker)
        
        upside_pct_val = rdata.get('overall_pct_change', 0.0)
        upside_pct_fmt = f"{upside_pct_val:+.1f}%"
        
        # Build introduction using content library
        html_parts = []
        
        # Summary sentence
        intro = get_variation(content_library, 'introduction.summary_sentence.intros', ['This report provides'])
        descriptor = get_variation(content_library, 'introduction.summary_sentence.descriptors', ['a detailed analysis of'])
        summary_parts = f"{ticker} stock analysis, including technical indicators, fundamental metrics, and market outlook"
        
        html_parts.append(f"<p>{intro} {descriptor} {summary_parts}.</p>")
        
        # Core question
        question_intro = get_variation(content_library, 'introduction.core_question.intros', ['The core question for investors is'])
        question_topic = get_variation(content_library, 'introduction.core_question.topics', ['valuation and future prospects'])
        
        html_parts.append(f"<p>{question_intro} {question_topic}.</p>")
        
        # Momentum analysis
        momentum_base = get_variation(content_library, 'introduction.momentum.base', 
            ['The stock is currently {trading_verb} at <strong>{current_price_fmt}</strong> (as of {last_date_fmt}), and it\'s {momentum_phrase}.'])
        
        trading_verb = get_variation(content_library, 'introduction.momentum.trading_verbs', ['trading'])
        
        # Determine momentum phrase based on technical analysis
        momentum_phrase = "showing mixed signals"
        if current_price_val and sma50_val and sma200_val:
            if current_price_val > sma50_val and current_price_val > sma200_val:
                momentum_phrase = get_variation(content_library, 'introduction.momentum.phrases.positive',
                    ['showing strong positive momentum, trading decisively above both its 50-day and 200-day moving averages'])
            elif current_price_val < sma50_val and current_price_val < sma200_val:
                momentum_phrase = get_variation(content_library, 'introduction.momentum.phrases.bearish',
                    ['currently in a bearish trend, trading below both its 50-day and 200-day moving averages'])
            elif current_price_val > sma50_val:
                momentum_phrase = get_variation(content_library, 'introduction.momentum.phrases.mixed_short_strong',
                    ['in a mixed technical state, trading above its short-term 50-day average but still under the long-term 200-day trendline'])
            else:
                momentum_phrase = get_variation(content_library, 'introduction.momentum.phrases.mixed_long_strong',
                    ['experiencing a short-term pullback within a larger uptrend, as it trades below its 50-day average while holding above the 200-day'])
        
        momentum_text = momentum_base.format(
            trading_verb=trading_verb,
            current_price_fmt=current_price_fmt,
            last_date_fmt=last_date_fmt,
            momentum_phrase=momentum_phrase
        )
        
        html_parts.append(f"<p>{momentum_text}</p>")
        
        # Analyst outlook
        if analyst_target_val and analyst_target_val > 0:
            source = get_variation(content_library, 'introduction.analyst_outlook.sources', ['Analysts'])
            
            sentiment_key = 'optimistic' if upside_pct_val > 5 else 'cautious' if upside_pct_val < -5 else 'stable'
            sentiment = get_variation(content_library, f'introduction.analyst_outlook.sentiments.{sentiment_key}', ['are positive'])
            connector = get_variation(content_library, 'introduction.analyst_outlook.connectors', ['with a 1-year price target of'])
            result = get_variation(content_library, f'introduction.analyst_outlook.results.{sentiment_key}', [f'implying a potential {upside_pct_fmt} change'])
            
            result_text = result.format(upside_pct_fmt=upside_pct_fmt)
            
            analyst_text = f"{source} {sentiment}, {connector} <strong>{analyst_target_fmt}</strong>, {result_text}."
            html_parts.append(f"<p>{analyst_text}</p>")
        else:
            unavailable_text = get_variation(content_library, 'introduction.analyst_outlook.unavailable',
                [f'Analyst price targets are currently unavailable for {ticker}.'])
            html_parts.append(f"<p>{unavailable_text}</p>")
        
        # Final hook
        final_hook = get_variation(content_library, 'introduction.closing_paragraphs.final_hook',
            [f'Ultimately, is {ticker} a stock worth adding to your watchlist? Read on for a deeper analysis.'])
        
        final_hook_text = final_hook.format(ticker=ticker, company_name=company_name)
        html_parts.append(f"<p>{final_hook_text}</p>")
        
        return '\\n'.join(html_parts)
        
    except Exception as e:
        print(f"Warning: Error in WordPress introduction generation: {e}. Using fallback.")
        return hc.generate_introduction_html(ticker, rdata)

def generate_wordpress_metrics_summary_html(ticker, rdata, content_library=None):
    """
    Generate WordPress metrics summary using content library variations.
    Falls back to original function if content library is not available.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_metrics_summary_html(ticker, rdata)
        
        # Extract data for template variables
        current_price_val = rdata.get('current_price')
        current_price_fmt = hc.format_html_value(current_price_val, 'currency', ticker=ticker)
        
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        sma50_fmt = hc.format_html_value(detailed_ta_data.get('SMA_50'), 'currency', ticker=ticker)
        sma200_fmt = hc.format_html_value(detailed_ta_data.get('SMA_200'), 'currency', ticker=ticker)
        
        rsi_val = detailed_ta_data.get('RSI_14')
        rsi_fmt = f"{rsi_val:.1f}" if isinstance(rsi_val, (int, float)) else "N/A"
        
        # Get 52-week range
        high_52wk_fmt = hc.format_html_value(rdata.get('52_week_high'), 'currency', ticker=ticker)
        low_52wk_fmt = hc.format_html_value(rdata.get('52_week_low'), 'currency', ticker=ticker)
        
        html_parts = []
        
        # Paragraph 1: Opening and technical pattern
        opening = get_variation(content_library, 'metrics_summary.paragraph1.opening',
            [f'Currently, {ticker} is priced at <strong>{current_price_fmt}</strong>.'])
        
        # Get trading verb for template substitution
        trading_verb = get_variation(content_library, 'metrics_summary.paragraph1.trading_verbs', ['trading'])
        
        opening_text = opening.format(ticker=ticker, current_price_fmt=current_price_fmt, trading_verb=trading_verb)
        html_parts.append(f"<p>{opening_text}</p>")
        
        # Technical pattern analysis
        position_verb = get_variation(content_library, 'metrics_summary.paragraph1.technical_pattern.position_verbs', ['positioned'])
        
        # Determine technical pattern
        technical_pattern_text = "mixed pattern"
        momentum_key = "mixed"
        
        if current_price_val and detailed_ta_data.get('SMA_50') and detailed_ta_data.get('SMA_200'):
            sma50_val = detailed_ta_data.get('SMA_50')
            sma200_val = detailed_ta_data.get('SMA_200')
            
            if current_price_val > sma50_val and current_price_val > sma200_val:
                technical_pattern_text = "bullish trend"
                momentum_key = "bullish"
            elif current_price_val < sma50_val and current_price_val < sma200_val:
                technical_pattern_text = "bearish trend"
                momentum_key = "bearish"
        
        technical_base = get_variation(content_library, 'metrics_summary.paragraph1.technical_pattern.base',
            'The technical indicators are showing a <strong>{technical_pattern_text}</strong>, as the price is {position_verb} relative to the {sma50_fmt} (50-day) and {sma200_fmt} (200-day) moving averages.')
        
        technical_text = technical_base.format(
            technical_pattern_text=technical_pattern_text,
            position_verb=position_verb,
            sma50_fmt=sma50_fmt,
            sma200_fmt=sma200_fmt
        )
        
        momentum_suggestion = get_variation(content_library, f'metrics_summary.paragraph1.technical_pattern.momentum_suggestion.{momentum_key}',
            ['This suggests the stock is in a period of consolidation.'])
        
        html_parts.append(f"<p>{technical_text} {momentum_suggestion}</p>")
        
        # RSI and MACD indicators
        rsi_key = "neutral"
        if rsi_val:
            if rsi_val > 70:
                rsi_key = "overbought"
            elif rsi_val < 30:
                rsi_key = "oversold"
        
        rsi_phrase = get_variation(content_library, f'metrics_summary.paragraph1.indicators.rsi.{rsi_key}',
            [f'the RSI of <strong>{rsi_fmt}</strong> suggests the stock is neither overbought nor oversold'])
        
        rsi_phrase = rsi_phrase.format(rsi_fmt=rsi_fmt)
        
        macd_phrase = "the MACD shows neutral signals"  # Simplified for now
        implication = get_variation(content_library, f'metrics_summary.paragraph1.indicators.implications.{rsi_key}',
            ['suggesting the stock is currently in equilibrium'])
        
        indicators_base = get_variation(content_library, 'metrics_summary.paragraph1.indicators.base',
            'However, {rsi_phrase}, while {macd_phrase}, {implication_phrase}.')
        
        indicators_text = indicators_base.format(
            rsi_phrase=rsi_phrase,
            macd_phrase=macd_phrase,
            implication_phrase=implication
        )
        
        html_parts.append(f"<p>{indicators_text}</p>")
        
        # Paragraph 2: 52-week range
        if high_52wk_fmt != 'N/A' and low_52wk_fmt != 'N/A':
            range_intro = get_variation(content_library, 'metrics_summary.paragraph2.range_intro',
                [f'Over the past year, {ticker}\'s stock has traded between <strong>{low_52wk_fmt} and {high_52wk_fmt}</strong>.'])
            
            range_text = range_intro.format(ticker=ticker, low_52wk_fmt=low_52wk_fmt, high_52wk_fmt=high_52wk_fmt)
            html_parts.append(f"<p>{range_text}</p>")
        
        return '\\n'.join(html_parts)
        
    except Exception as e:
        print(f"Warning: Error in WordPress metrics summary generation: {e}. Using fallback.")
        return hc.generate_metrics_summary_html(ticker, rdata)

def generate_wordpress_report(site_name: str, ticker: str, app_root: str, report_sections_to_include: list):
    """
    Generates a site-specific HTML report and CSS for a given stock ticker.
    Args:
        site_name (str): Display name of the site.
        ticker (str): Stock ticker symbol.
        app_root (str): Root path of the application (for accessing static files if needed).
        report_sections_to_include (list): A list of section keys (strings) to include in the report.
    Returns:
        tuple: (rdata_dict, html_content, css_content)
    """
    print(f"--- Generating WordPress Report for {ticker} on {site_name} with sections: {report_sections_to_include} ---")
    # ... (initial setup: ts, static_dir_path, site_slug, html_report_parts, rdata initialization) ...
    # Keep the existing data fetching and preparation logic for rdata
    # (fetch_stock_data, macro_data, preprocess_data, train_prophet_model, fundamentals, rdata population)

    ts = str(int(time.time()))
    static_dir_path = os.path.join(app_root, 'static')
    os.makedirs(static_dir_path, exist_ok=True)
    site_slug = site_name.lower().replace(" ", "-")
    html_report_parts = []
    rdata = {}

    try:
        # --- 0. Load Content Library for WordPress Variations ---
        print("Step 0: Loading content library for WordPress variations...")
        content_library = load_content_library(app_root)
        if content_library:
            print("✅ Content library loaded successfully")
        else:
            print("⚠️  Using fallback inline variations")
        
        # --- 1. Data Collection (Same as before) ---
        print("Step 1: Fetching data...")
        stock_data = fetch_stock_data(ticker, app_root=app_root, start_date=START_DATE, end_date=END_DATE, timeout=30)
        macro_data = fetch_macro_indicators(app_root=app_root, start_date=START_DATE, end_date=END_DATE)
        if stock_data is None or stock_data.empty: raise ValueError(f"Could not fetch stock data for {ticker}")
        # Handle macro_data fallback if necessary (as in your existing script)
        if macro_data is None or macro_data.empty:
            print(f"Warning: Could not fetch macro data. Proceeding with fallback.")
            date_range_stock = pd.date_range(start=stock_data['Date'].min(), end=stock_data['Date'].max(), freq='D')
            macro_data = pd.DataFrame({'Date': date_range_stock})
            for col_macro in ['Interest_Rate', 'SP500', 'Interest_Rate_MA30', 'SP500_MA30']:
                 macro_data[col_macro] = 0.0

        # --- 2. Data Preprocessing (Same as before) ---
        print("Step 2: Preprocessing data...")
        processed_data = preprocess_data(stock_data, macro_data)
        if processed_data is None or processed_data.empty: raise ValueError("Preprocessing resulted in empty data.")

        # --- 3. Prophet Model Training (Same as before) ---
        print("Step 3: Training model...")
        model, forecast_raw, actual_df, forecast_df = train_prophet_model(
            processed_data.copy(), ticker, forecast_horizon='1y', timestamp=ts
        )
        # Note: model can be None when using WSL bridge, which is normal
        if forecast_raw is None or actual_df is None or forecast_df is None:
            raise ValueError("Prophet model training or forecasting failed.")


        # --- 4. Fetch Fundamentals (Same as before) ---
        print("Step 4: Fetching fundamentals...")
        fundamentals = {}
        try:
            yf_ticker_obj = yf.Ticker(ticker)
            fundamentals = {
                'info': yf_ticker_obj.info or {},
                'recommendations': yf_ticker_obj.recommendations if hasattr(yf_ticker_obj, 'recommendations') and yf_ticker_obj.recommendations is not None else pd.DataFrame(),
                'news': yf_ticker_obj.news if hasattr(yf_ticker_obj, 'news') and yf_ticker_obj.news is not None else []
            }
            if not fundamentals['info']: print(f"Warning: yfinance info data for {ticker} is empty.")
        except Exception as e_fund:
            print(f"Warning: Failed to fetch yfinance fundamentals for {ticker}: {e_fund}")
            fundamentals = {'info': {}, 'recommendations': pd.DataFrame(), 'news': []}

        

        # --- 5. Prepare Data Dictionary (rdata) (Same as before) ---
        print("Step 5: Preparing data for report components...")
        rdata['ticker'] = ticker
        rdata['site_name'] = site_name
        rdata['current_price'] = processed_data['Close'].iloc[-1] if not processed_data.empty else None
        rdata['last_date'] = processed_data['Date'].iloc[-1] if not processed_data.empty else datetime.now()
        rdata['historical_data'] = processed_data
        rdata['actual_data'] = actual_df
        rdata['monthly_forecast_table_data'] = forecast_df
        # ... (rest of rdata population as in your existing script, including period_label, forecast_1m/1y, TA calculations, sentiment, risk etc.)
        if not forecast_df.empty and isinstance(forecast_df['Period'].iloc[0], str):
             period_str = forecast_df['Period'].iloc[0]
             if re.match(r'\d{4}-\d{2}-\d{2}', period_str): rdata['period_label'] = 'Day'; rdata['time_col']='Period'
             elif re.match(r'\d{4}-\d{2}', period_str): rdata['period_label'] = 'Month'; rdata['time_col']='Period'
             else: rdata['period_label'] = 'Period'; rdata['time_col']='Period'
        else:
             rdata['period_label'] = 'Period'; rdata['time_col']='Period'

        if not forecast_df.empty:
            try:
                # Ensure 'ds' is datetime for proper comparison
                if rdata['period_label']=='Month':
                    forecast_df['ds'] = pd.to_datetime(forecast_df['Period'].astype(str) + '-01')
                else: # Assuming 'Day' or other directly convertible format
                    forecast_df['ds'] = pd.to_datetime(forecast_df['Period'].astype(str))

                one_month_target_date = pd.to_datetime(rdata['last_date']) + timedelta(days=30)
                one_year_target_date = pd.to_datetime(rdata['last_date']) + timedelta(days=365)
                
                forecast_df_sorted = forecast_df.sort_values('ds')
                
                month_row_idx = (forecast_df_sorted['ds'] - one_month_target_date).abs().argsort()[:1]
                year_row_idx = (forecast_df_sorted['ds'] - one_year_target_date).abs().argsort()[:1]

                month_row = forecast_df_sorted.iloc[month_row_idx]
                year_row = forecast_df_sorted.iloc[year_row_idx]
                
                rdata['forecast_1m'] = month_row['Average'].iloc[0] if not month_row.empty else None
                rdata['forecast_1y'] = year_row['Average'].iloc[0] if not year_row.empty else None
                
                if rdata['forecast_1y'] and rdata['current_price'] and rdata['current_price'] > 0:
                     rdata['overall_pct_change'] = ((rdata['forecast_1y'] - rdata['current_price']) / rdata['current_price']) * 100
                else: rdata['overall_pct_change'] = 0.0
            except Exception as fc_err:
                 print(f"Warning: Could not extract 1m/1y forecasts accurately for {ticker}: {fc_err}")
                 rdata['forecast_1m'] = None; rdata['forecast_1y'] = None; rdata['overall_pct_change'] = 0.0
        else:
             rdata['forecast_1m'] = None; rdata['forecast_1y'] = None; rdata['overall_pct_change'] = 0.0

        current_price_for_fa = rdata.get('current_price')
        rdata['profile_data'] = fa.extract_company_profile(fundamentals)
        rdata['valuation_data'] = fa.extract_valuation_metrics(fundamentals)
        rdata['total_valuation_data'] = fa.extract_total_valuation_data(fundamentals, current_price_for_fa)
        rdata['share_statistics_data'] = fa.extract_share_statistics_data(fundamentals, current_price_for_fa)
        rdata['financial_health_data'] = fa.extract_financial_health(fundamentals)
        rdata['financial_efficiency_data'] = fa.extract_financial_efficiency_data(fundamentals)
        rdata['profitability_data'] = fa.extract_profitability(fundamentals)
        rdata['dividends_data'] = fa.extract_dividends_splits(fundamentals)
        rdata['analyst_info_data'] = fa.extract_analyst_info(fundamentals)
        rdata['stock_price_stats_data'] = fa.extract_stock_price_stats_data(fundamentals)
        rdata['short_selling_data'] = fa.extract_short_selling_data(fundamentals)
        rdata['peer_comparison_data'] = fa.extract_peer_comparison_data(ticker)
        rdata['industry'] = fundamentals.get('info', {}).get('industry', 'N/A')
        rdata['sector'] = fundamentals.get('info', {}).get('sector', 'N/A')

        rdata['detailed_ta_data'] = ta_module.calculate_detailed_ta(processed_data) # Use renamed import
        rdata['sma_50'] = rdata['detailed_ta_data'].get('SMA_50')
        rdata['sma_200'] = rdata['detailed_ta_data'].get('SMA_200')
        rdata['latest_rsi'] = rdata['detailed_ta_data'].get('RSI_14')

        # Volatility, green days, sentiment, risk_items (same as before)
        if 'Close' in processed_data.columns and len(processed_data) > 30:
            log_returns = np.log(processed_data['Close'] / processed_data['Close'].shift(1))
            rdata['volatility'] = log_returns.iloc[-30:].std() * np.sqrt(252) * 100
        else: rdata['volatility'] = None

        if 'Close' in processed_data.columns and 'Open' in processed_data.columns and len(processed_data) >= 30:
             last_30_days = processed_data.iloc[-30:]
             rdata['green_days'] = (last_30_days['Close'] > last_30_days['Open']).sum()
             rdata['total_days'] = 30
        else: rdata['green_days'] = None; rdata['total_days'] = None
        
        sentiment_score = 0
        if rdata.get('current_price') and rdata.get('sma_50') and rdata['current_price'] > rdata['sma_50']: sentiment_score += 1
        if rdata.get('current_price') and rdata.get('sma_200') and rdata['current_price'] > rdata['sma_200']: sentiment_score += 2
        if rdata.get('latest_rsi') and rdata['latest_rsi'] < 70: sentiment_score += 0.5
        if rdata.get('latest_rsi') and rdata['latest_rsi'] < 30: sentiment_score += 1 # Stronger bullish signal if oversold
        
        macd_hist = rdata.get('detailed_ta_data', {}).get('MACD_Hist')
        macd_line = rdata.get('detailed_ta_data', {}).get('MACD_Line')
        macd_signal = rdata.get('detailed_ta_data', {}).get('MACD_Signal')

        if macd_hist is not None and macd_line is not None and macd_signal is not None:
             if macd_line > macd_signal and macd_hist > 0: sentiment_score += 1.5
        
        if sentiment_score >= 4: rdata['sentiment'] = 'Bullish'
        elif sentiment_score >= 2: rdata['sentiment'] = 'Neutral-Bullish'
        elif sentiment_score >= 0: rdata['sentiment'] = 'Neutral' # Adjusted to make Neutral less sensitive
        else: rdata['sentiment'] = 'Bearish' # Simplified bearish side

        risk_items_list = []
        if rdata.get('volatility') and rdata['volatility'] > 40: risk_items_list.append(f"High Volatility: Recent annualized volatility ({rdata['volatility']:.1f}%) suggests significant price swings.")
        risk_items_list.append("Market Risk: Overall market fluctuations can impact the stock.")
        risk_items_list.append(f"Sector/Industry Risk: Factors specific to the {rdata.get('industry', 'N/A')} industry or {rdata.get('sector', 'N/A')} sector can affect performance.")
        risk_items_list.append("Economic Risk: Changes in macroeconomic conditions (interest rates, inflation) pose risks.")
        risk_items_list.append("Company-Specific Risk: Unforeseen company events or news can impact the price.")
        rdata['risk_items'] = risk_items_list


        # --- 6. Generate HTML Report Parts (CONDITIONAL ASSEMBLY) ---
        print("Step 6: Generating HTML content based on selected sections...")
        for section_key in report_sections_to_include:
            generator_func = ALL_REPORT_SECTIONS.get(section_key)
            if generator_func:
                # Handle sections that depend on data existence (e.g., forecast table)
                if section_key == "detailed_forecast_table" and (forecast_df is None or forecast_df.empty):
                    print(f"Skipping section '{section_key}' as forecast data is not available.")
                    continue
                
                # Special handling for introduction - no h2 header, use content library
                if section_key == "introduction":
                    html_report_parts.append(f"<section id='{section_key}'>")
                    html_report_parts.append(generate_wordpress_introduction_html(ticker, rdata, content_library))
                    html_report_parts.append("</section>")
                # Special handling for metrics_summary - use content library
                elif section_key == "metrics_summary":
                    html_report_parts.append(f"<section id='{section_key}'>")
                    html_report_parts.append("<h2>Key Metrics Summary</h2>")
                    html_report_parts.append(generate_wordpress_metrics_summary_html(ticker, rdata, content_library))
                    html_report_parts.append("</section>")
                # Special handling for report_info_disclaimer - requires generation_time parameter
                elif section_key == "report_info_disclaimer":
                    from datetime import datetime
                    section_title = "Report Information and Disclaimer"
                    html_report_parts.append(f"<section id='{section_key}'><h2>{section_title}</h2>")
                    html_report_parts.append(generator_func(datetime.now())) # Pass generation time
                    html_report_parts.append("</section>")
                else:
                    section_title = section_key.replace("_", " ").title()
                    html_report_parts.append(f"<section id='{section_key}'><h2>{section_title}</h2>")
                    html_report_parts.append(generator_func(ticker, rdata)) # Call the function from html_components
                    html_report_parts.append("</section>")
            else:
                print(f"Warning: Unknown report section key '{section_key}'. Skipping.")
        
        # --- 7. Assemble Final HTML (Same as before) ---
        print("Step 7: Assembling final HTML...")
        final_html_body = "\n".join(html_report_parts)

        # --- 8. Define CSS (Same as before, with site-specific theming) ---
        print("Step 8: Defining CSS...")
        # ... (Keep your existing base_css and site_specific_css logic) ...
        base_css = """/* Enhanced WordPress Stock Report CSS */
.stock-report-container { 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen-Sans, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif; 
    line-height: 1.65;
    color: #333;
    max-width: 100%;
    margin: 0;
    padding: 0;
    background-color: transparent;
    box-shadow: none;
    border: none;
    border-radius: 0; 
}

/* Typography - WordPress Theme Compatible */
.stock-report-container h2 {
    font-size: 1.5em;
    font-weight: 600;
    color: #2c3e50;
    margin: 2em 0 1em 0;
    padding-bottom: 0.5em;
    border-bottom: 2px solid #e1e8ed;
    line-height: 1.3;
}

.stock-report-container h3 {
    font-size: 1.25em;
    font-weight: 600;
    color: #34495e;
    margin: 1.5em 0 0.8em 0;
    padding-bottom: 0.3em;
    border-bottom: 1px solid #ecf0f1;
    line-height: 1.4;
}

.stock-report-container h4 {
    font-size: 1.1em;
    font-weight: 600;
    color: #34495e;
    margin: 1.2em 0 0.6em 0;
    line-height: 1.4;
}

.stock-report-container section {
    margin-bottom: 2.5em;
}

/* Paragraph Styling - WordPress Theme Compatible */
.stock-report-container p {
    margin: 0 0 1.2em 0;
    font-size: 1em;
    line-height: 1.65;
    color: #444;
    text-align: justify;
}

.stock-report-container ul,
.stock-report-container ol {
    margin: 0 0 1.2em 1.5em;
    padding: 0;
}

.stock-report-container li {
    margin-bottom: 0.6em;
    line-height: 1.6;
}

.stock-report-container strong {
    font-weight: 600;
    color: #2c3e50;
}

.stock-report-container a {
    color: #3498db;
    text-decoration: none;
}

.stock-report-container a:hover {
    text-decoration: underline;
    color: #2980b9;
}

/* Metrics Summary - Small Horizontal Boxes */
.metrics-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin: 1.5em 0;
    padding: 0;
    background-color: transparent;
}

.metric-item {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 12px 10px;
    text-align: center;
    transition: box-shadow 0.2s ease;
    min-height: 70px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.metric-item:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.metric-label {
    font-size: 0.75em;
    color: #6c757d;
    margin-bottom: 4px;
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.metric-value {
    font-size: 1.1em;
    font-weight: 700;
    color: #2c3e50;
    line-height: 1.2;
    word-wrap: break-word;
}

.metric-change {
    margin-left: 4px;
    font-size: 0.85em;
    font-weight: 600;
}

/* Color Coding */
.trend-up, .sentiment-bullish, .action-buy {
    color: #27ae60;
}

.trend-down, .sentiment-bearish, .action-short {
    color: #e74c3c;
}

.trend-neutral, .sentiment-neutral, .action-hold {
    color: #f39c12;
}

/* Icon Styling */
.icon {
    display: inline-block;
    margin-right: 6px;
    font-size: 1em;
    width: 1.2em;
    text-align: center;
}

.icon-up { color: #27ae60; }
.icon-down { color: #e74c3c; }
.icon-neutral { color: #f39c12; }
.icon-warning { color: #f39c12; }

/* Tables */
.stock-report-container .table-container {
    overflow-x: auto;
    margin: 1.5em 0;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    background-color: #fff;
}

.stock-report-container table {
    width: 100%;
    border-collapse: collapse;
    margin: 0;
    font-size: 0.95em;
}

.stock-report-container th,
.stock-report-container td {
    border: none;
    border-bottom: 1px solid #e9ecef;
    padding: 12px 16px;
    text-align: left;
    vertical-align: top;
}

.stock-report-container th {
    background-color: #f8f9fa;
    font-weight: 600;
    color: #495057;
    font-size: 0.9em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stock-report-container tbody tr:nth-child(even) {
    background-color: #f8f9fa;
}

.stock-report-container tbody tr:hover {
    background-color: #e9ecef;
}

.stock-report-container td:first-child {
    font-weight: 600;
    color: #495057;
    width: 40%;
}

.stock-report-container td:last-child {
    text-align: right;
    font-weight: 600;
    color: #2c3e50;
}

/* Grid Layouts */
.profile-grid,
.analyst-grid,
.ma-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin: 1.5em 0;
}

.profile-item,
.analyst-item,
.ma-item {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 12px 15px;
    font-size: 0.95em;
    line-height: 1.5;
}

.profile-item span:first-child,
.analyst-item span:first-child,
.ma-item .label {
    font-weight: 600;
    color: #495057;
    margin-right: 8px;
}

/* Conclusion & Outlook - Separate Cards */
.conclusion-columns {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    margin: 1.5em 0;
}

.conclusion-column {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.conclusion-column h3 {
    margin-top: 0;
    margin-bottom: 1em;
    font-size: 1.2em;
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.5em;
}

.conclusion-column ul {
    padding-left: 0;
    list-style: none;
    margin: 0;
}

.conclusion-column li {
    margin-bottom: 0.8em;
    display: flex;
    align-items: flex-start;
    font-size: 0.95em;
    line-height: 1.6;
}

.conclusion-column li .icon {
    margin-right: 10px;
    margin-top: 2px;
    flex-shrink: 0;
}

/* News Section */
.news-container {
    margin-top: 1.5em;
}

.news-item {
    border-bottom: 1px solid #e9ecef;
    padding-bottom: 1.2em;
    margin-bottom: 1.2em;
}

.news-item:last-child {
    border-bottom: none;
    margin-bottom: 0;
}

.news-item h4 {
    margin: 0 0 0.5em 0;
    font-size: 1.1em;
    line-height: 1.4;
}

.news-item h4 a {
    color: #2c3e50;
    text-decoration: none;
}

.news-item h4 a:hover {
    color: #3498db;
    text-decoration: underline;
}

.news-meta {
    font-size: 0.85em;
    color: #6c757d;
    margin-top: 0.5em;
}

.news-meta span {
    margin-right: 15px;
    background-color: #e9ecef;
    padding: 2px 8px;
    border-radius: 4px;
}

/* FAQ Section - Enhanced */
#faq details {
    background: #fff;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    margin-bottom: 12px;
    overflow: hidden;
    transition: box-shadow 0.2s ease;
}

#faq details:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

#faq summary {
    padding: 15px 20px;
    font-weight: 600;
    cursor: pointer;
    outline: none;
    background-color: #f8f9fa;
    border-bottom: 1px solid #e9ecef;
    position: relative;
    transition: background-color 0.2s ease;
}

#faq summary:hover {
    background-color: #e9ecef;
}

#faq summary::marker {
    content: none;
}

#faq summary::after {
    content: '+';
    position: absolute;
    right: 20px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 1.5em;
    color: #6c757d;
    transition: transform 0.2s ease;
}

#faq details[open] summary::after {
    content: '−';
    transform: translateY(-50%) rotate(180deg);
    color: #3498db;
}

#faq details[open] summary {
    background-color: #e9ecef;
}

#faq details p {
    padding: 20px;
    margin: 0;
    background-color: #fff;
    line-height: 1.6;
    color: #444;
}

/* Narrative Boxes */
.narrative {
    background-color: #f8f9fa;
    border-left: 4px solid #3498db;
    border-radius: 0 4px 4px 0;
    padding: 15px 20px;
    margin: 1.5em 0;
    font-size: 0.95em;
}

.narrative p:last-child {
    margin-bottom: 0;
}

.narrative ul {
    list-style-type: disc;
    padding-left: 20px;
    margin: 0.8em 0;
}

/* Risk Factors */
.risk-factors ul {
    list-style: none;
    padding-left: 0;
    margin: 1.5em 0;
}

.risk-factors li {
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 12px 15px;
    margin-bottom: 10px;
    border-radius: 0 4px 4px 0;
    display: flex;
    align-items: flex-start;
    font-size: 0.95em;
    line-height: 1.6;
}

.risk-factors li .icon {
    color: #ffc107;
    margin-right: 10px;
    margin-top: 2px;
    flex-shrink: 0;
}

/* Disclaimer */
.disclaimer,
.general-info p {
    font-size: 0.9em;
    color: #6c757d;
    margin-top: 2em;
    padding: 15px;
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    line-height: 1.6;
}

.disclaimer strong {
    color: #e74c3c;
    font-weight: 600;
}

/* Responsive Design */
@media (max-width: 768px) {
    .metrics-summary {
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
    }
    
    .metric-item {
        padding: 10px 8px;
        min-height: 60px;
    }
    
    .metric-value {
        font-size: 1em;
    }
    
    .conclusion-columns {
        grid-template-columns: 1fr;
        gap: 15px;
    }
    
    .profile-grid,
    .analyst-grid,
    .ma-summary {
        grid-template-columns: 1fr;
        gap: 12px;
    }
    
    .stock-report-container th,
    .stock-report-container td {
        padding: 10px 12px;
        font-size: 0.9em;
    }
    
    #faq summary,
    #faq details p {
        padding: 12px 15px;
    }
}

@media (max-width: 480px) {
    .stock-report-container h2 {
        font-size: 1.3em;
    }
    
    .stock-report-container h3 {
        font-size: 1.15em;
    }
    
    .metrics-summary {
        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 8px;
    }
    
    .metric-item {
        padding: 8px 6px;
        min-height: 55px;
    }
    
    .metric-label {
        font-size: 0.7em;
    }
    
    .metric-value {
        font-size: 0.95em;
    }
    
    .stock-report-container th,
    .stock-report-container td {
        padding: 8px 10px;
        font-size: 0.85em;
    }
    
    .conclusion-column,
    .narrative,
    .risk-factors li {
        padding: 12px 15px;
    }
}
"""
      
        final_css = base_css 
        
        # WordPress-safe implementation: Use only inline styles, no <style> tags
        # WordPress often strips <style> tags for security, so we convert everything to inline styles
        container_style = """font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen-Sans, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif; line-height: 1.65; color: #333; max-width: 100%; margin: 0; padding: 0; background-color: transparent; box-shadow: none; border: none; border-radius: 0;"""
        
        # Apply inline styles to the HTML content
        def apply_inline_styles(html_content):
            import re
            
            # First, remove any <style> blocks that may come from HTML components
            # This is critical for WordPress compatibility
            style_pattern = r'<style[^>]*>.*?</style>'
            html_content = re.sub(style_pattern, '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Define comprehensive inline styles for WordPress compatibility - COMPLETE CSS RULESET
            styles_map = {
                # Main Container - Complete styling from user's CSS
                'stock-report-container': 'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif; line-height: 1.65; color: #333; max-width: 100%; margin: 0; padding: 0; background-color: transparent; box-shadow: none; border: none; border-radius: 0;',
                
                # Metrics Summary - Complete horizontal card styling
                'metrics-summary': 'display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 1.5em 0; padding: 0; background-color: transparent;',
                'metric-item': 'background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 12px 10px; text-align: center; transition: box-shadow 0.2s ease; min-height: 70px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1);',
                'metric-label': 'font-size: 0.75em; color: #6c757d; margin-bottom: 4px; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;',
                'metric-value': 'font-size: 1.1em; font-weight: 700; color: #2c3e50; line-height: 1.2; word-wrap: break-word;',
                'metric-change': 'margin-left: 4px; font-size: 0.85em; font-weight: 600;',
                
                # Color Coding - Complete from user's CSS
                'trend-up': 'color: #27ae60; font-weight: 600;',
                'trend-down': 'color: #e74c3c; font-weight: 600;',
                'trend-neutral': 'color: #f39c12; font-weight: 600;',
                'sentiment-bullish': 'color: #27ae60; font-weight: 600;',
                'sentiment-bearish': 'color: #e74c3c; font-weight: 600;',
                'sentiment-neutral': 'color: #f39c12; font-weight: 600;',
                'action-buy': 'color: #27ae60; font-weight: bold;',
                'action-short': 'color: #e74c3c; font-weight: bold;',
                'action-hold': 'color: #f39c12; font-weight: bold;',
                
                # Icon Styling - Complete from user's CSS
                'icon': 'display: inline-block; margin-right: 6px; font-size: 1em; width: 1.2em; text-align: center;',
                'icon-up': 'color: #27ae60;',
                'icon-down': 'color: #e74c3c;',
                'icon-neutral': 'color: #f39c12;',
                'icon-warning': 'color: #f39c12;',
                
                # Tables - Complete styling from user's CSS
                'table-container': 'overflow-x: auto; margin: 1.5em 0; border: 1px solid #e9ecef; border-radius: 8px; background-color: #fff;',
                
                # Grid Layouts - Complete from user's CSS
                'profile-grid': 'display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 1.5em 0;',
                'analyst-grid': 'display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 1.5em 0;',
                'ma-summary': 'display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 1.5em 0;',
                'profile-item': 'background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 12px 15px; font-size: 0.95em; line-height: 1.5;',
                'analyst-item': 'background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 12px 15px; font-size: 0.95em; line-height: 1.5;',
                'ma-item': 'background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 12px 15px; font-size: 0.95em; line-height: 1.5;',
                
                # Conclusion & Outlook - Complete card styling from user's CSS
                'conclusion-columns': 'display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin: 1.5em 0;',
                'conclusion-column': 'background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);',
                
                # News Section - Complete from user's CSS
                'news-container': 'margin-top: 1.5em;',
                'news-item': 'border-bottom: 1px solid #e9ecef; padding-bottom: 1.2em; margin-bottom: 1.2em;',
                'news-meta': 'font-size: 0.85em; color: #6c757d; margin-top: 0.5em;',
                
                # FAQ Section - Complete styling from user's CSS
                'faq': 'margin: 1.5em 0;',
                
                # Narrative Boxes - Complete from user's CSS
                'narrative': 'background-color: #f8f9fa; border-left: 4px solid #3498db; border-radius: 0 4px 4px 0; padding: 15px 20px; margin: 1.5em 0; font-size: 0.95em; line-height: 1.6;',
                
                # Risk Factors - Complete styling from user's CSS
                'risk-factors': 'margin: 1.5em 0;',
                
                # Disclaimer - Complete from user's CSS
                'disclaimer': 'font-size: 0.9em; color: #6c757d; margin-top: 2em; padding: 15px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; line-height: 1.6;',
                'general-info': 'font-size: 0.9em; color: #6c757d; margin-top: 2em; padding: 15px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; line-height: 1.6;'
            }
            
            # Apply styles to elements with these classes
            for class_name, style in styles_map.items():
                # Match class attributes and add inline styles
                pattern = f'class="[^"]*{class_name}[^"]*"'
                matches = list(re.finditer(pattern, html_content))
                
                # Process matches in reverse order to maintain string positions
                for match in reversed(matches):
                    original = match.group()
                    # Check if style attribute already exists
                    if 'style=' in original:
                        # Find the style attribute and append
                        style_match = re.search(r'style="([^"]*)"', original)
                        if style_match:
                            existing_style = style_match.group(1)
                            new_style = original.replace(f'style="{existing_style}"', f'style="{existing_style}; {style}"')
                        else:
                            new_style = original[:-1] + f' style="{style}"'
                    else:
                        # Add new style attribute
                        new_style = original[:-1] + f' style="{style}"'
                    
                    # Replace in content
                    html_content = html_content[:match.start()] + new_style + html_content[match.end():]
            
            # Enhanced HTML element styling - Complete WordPress-compatible inline styles
            element_styles = {
                # Typography - Comprehensive styling matching your CSS
                '<h2>': '<h2 style="font-size: 1.5em; font-weight: 600; color: #2c3e50; margin: 2em 0 1em 0; padding-bottom: 0.5em; border-bottom: 2px solid #e1e8ed; line-height: 1.3;">',
                '<h3>': '<h3 style="font-size: 1.25em; font-weight: 600; color: #34495e; margin: 1.5em 0 0.8em 0; padding-bottom: 0.3em; border-bottom: 1px solid #ecf0f1; line-height: 1.4;">',
                '<h4>': '<h4 style="font-size: 1.1em; font-weight: 600; color: #34495e; margin: 1.2em 0 0.6em 0; line-height: 1.4;">',
                
                # Paragraphs and text
                '<p>': '<p style="margin: 0 0 1.2em 0; font-size: 1em; line-height: 1.65; color: #444; text-align: justify;">',
                '<strong>': '<strong style="font-weight: 600; color: #2c3e50;">',
                '<a ': '<a style="color: #3498db; text-decoration: none;" ',
                
                # Lists
                '<ul>': '<ul style="margin: 0 0 1.2em 1.5em; padding: 0; list-style: none;">',
                '<ol>': '<ol style="margin: 0 0 1.2em 1.5em; padding: 0;">',
                '<li>': '<li style="margin-bottom: 0.6em; line-height: 1.6;">',
                
                # Sections
                '<section>': '<section style="margin-bottom: 2.5em;">',
                
                # Tables - Complete styling from your CSS
                '<table>': '<table style="width: 100%; border-collapse: collapse; margin: 0; font-size: 0.95em;">',
                '<th>': '<th style="background-color: #f8f9fa; font-weight: 600; color: #495057; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; border: none; border-bottom: 1px solid #e9ecef; padding: 12px 16px; text-align: left; vertical-align: top;">',
                '<td>': '<td style="border: none; border-bottom: 1px solid #e9ecef; padding: 12px 16px; text-align: left; vertical-align: top;">',
                
                # Divs and containers - Enhanced card styling
                '<div class="conclusion-column">': '<div class="conclusion-column" style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">',
                '<div class="risk-factors">': '<div class="risk-factors" style="margin: 1.5em 0;"><ul style="list-style: none; padding-left: 0; margin: 1.5em 0;">',
                '<div class="narrative">': '<div class="narrative" style="background-color: #f8f9fa; border-left: 4px solid #3498db; border-radius: 0 4px 4px 0; padding: 15px 20px; margin: 1.5em 0; font-size: 0.95em;">',
                
                # Enhanced table styling for proper appearance
                '<tbody>': '<tbody style="">',
                '<tr>': '<tr style="">',
                '<thead>': '<thead style="">',
                
                # FAQ and details elements
                '<details>': '<details style="background: #fff; border: 1px solid #e9ecef; border-radius: 8px; margin-bottom: 12px; overflow: hidden;">',
                '<summary>': '<summary style="padding: 15px 20px; font-weight: 600; cursor: pointer; outline: none; background-color: #f8f9fa; border-bottom: 1px solid #e9ecef;">',
                
                # Special risk factor list items
                '<li style="background-color: #fff3cd;': '<li style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 15px; margin-bottom: 10px; border-radius: 0 4px 4px 0; display: flex; align-items: flex-start; font-size: 0.95em; line-height: 1.6;'
            }
            
            for element, styled_element in element_styles.items():
                html_content = html_content.replace(element, styled_element)
                
            # Special handling for metric cards to ensure proper horizontal card display
            # Replace any remaining metric-related divs that might not have been caught
            html_content = html_content.replace(
                '<div class="metrics-summary">', 
                '<div class="metrics-summary" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 1.5em 0; padding: 0; background-color: transparent;">'
            )
            html_content = html_content.replace(
                '<div class="metric-item">', 
                '<div class="metric-item" style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 12px 10px; text-align: center; transition: box-shadow 0.2s ease; min-height: 70px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">'
            )
                    
            return html_content
        
        # Apply inline styles and wrap in container
        styled_html_body = apply_inline_styles(final_html_body)
        # WordPress-safe: No <style> tags, only inline styles
        final_html_wrapped = f'<div style="{container_style}">{styled_html_body}</div>'


        print(f"--- Report Generation Complete for {ticker} ({site_name}) ---")
        return rdata, final_html_wrapped, final_css

    except ImportError as imp_err:
         print(f"!!! WORDPRESS_REPORTER IMPORT ERROR: {imp_err}. Report generation aborted. !!!")
         traceback.print_exc()
         error_html = f'<div class="stock-report-container error"><p><strong>Critical Error: Failed to load required analysis modules. Report cannot be generated. Check server logs. ({imp_err})</strong></p></div>'
         error_css = ".stock-report-container.error { border: 2px solid red; background-color: #ffebee; color: #c00; }"
         return {}, error_html, error_css
    except (ValueError, RuntimeError, Exception) as e:
        print(f"!!! ERROR generating report for {ticker} in wordpress_reporter: {e} !!!")
        traceback.print_exc()
        current_site_slug = site_slug if 'site_slug' in locals() else 'general'
        error_html = f'<div class="stock-report-container report-{current_site_slug} error"><p><strong>Error generating report for {ticker} on {site_name}.</strong></p><p>Reason: {str(e)}</p></div>'
        error_css = ".stock-report-container.error { border: 2px solid #dc3545; /* ... */ }"
        return {}, error_html, error_css

# Example Usage (if run directly) - Update to pass sections
if __name__ == '__main__':
    APP_ROOT_EXAMPLE = os.path.dirname(os.path.abspath(__file__))
    example_sections = [
        "introduction", "metrics_summary", "detailed_forecast_table",
        "technical_analysis_summary", "conclusion_outlook", "risk_factors"
        # Note: "report_info_disclaimer" is excluded from WordPress posts
    ]
    r_data_ex, html_code_ex, css_code_ex = generate_wordpress_report(
        "Finances Forecast", "AAPL", APP_ROOT_EXAMPLE, example_sections
    )
    if "Error generating report" not in html_code_ex:
        print("\n--- Example Report Generated Successfully ---")
        # print(html_code_ex) # Optionally print HTML
    else:
        print("\n--- Example Report Generation Failed ---")
        print(html_code_ex)