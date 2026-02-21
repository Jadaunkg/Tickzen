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
import logging

# Assuming your other imports (config, data_collection, etc.) are set up
_pipeline_import_error = None
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
    # from reporting_tools.text_formatter import format_wordpress_content, format_narrative_section  # Module not found
except ImportError as e:
    _pipeline_import_error = str(e)
    print(f"Warning: Some pipeline modules not available in wordpress_reporter: {e}")
    # Define None stubs so the module can still be imported for ALL_REPORT_SECTIONS
    fetch_stock_data = None
    fetch_macro_indicators = None
    preprocess_data = None
    train_prophet_model = None
    fa = None
    hc = None
    ta_module = None
    try:
        from config.config import START_DATE, END_DATE
    except ImportError:
        START_DATE = None
        END_DATE = None

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
        
        # Case 4: Try absolute paths from current working directory
        cwd = os.getcwd()
        possible_paths.extend([
            os.path.join(cwd, 'app', 'content_library.json'),
            os.path.join(cwd, 'content_library.json')
        ])
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        print(f"WARNING: content_library.json not found in expected locations. Searched paths:")
        for path in possible_paths[:8]:  # Show first 8 paths for debugging
            print(f"  - {path} {'✓' if os.path.exists(path) else '✗'}")
        print("Using inline variations as fallback.")
        return None
    except Exception as e:
        print(f"WARNING: Error loading content_library.json: {e}. Using inline variations.")
        return None

def get_variation(content_lib, section_path, fallback_list=None):
    """Get a random variation from content library path or fallback to provided list."""
    if not content_lib:
        return random.choice(fallback_list) if fallback_list else "Content unavailable"
    
    try:
        # Navigate through nested dict using dot notation like 'introduction.summary_sentence.intros'
        keys = section_path.split('.')
        current = content_lib
        for key in keys:
            current = current[key]
        return random.choice(current) if isinstance(current, list) else current
    except (KeyError, TypeError):
        # Better fallback handling
        if fallback_list and len(fallback_list) > 0:
            return random.choice(fallback_list)
        else:
            print(f"Warning: Missing content library path '{section_path}' and no fallback provided")
            return f"[Missing content: {section_path}]"

def safe_format(template_string, **kwargs):
    """Safely format a string, handling missing variables gracefully."""
    try:
        return template_string.format(**kwargs)
    except KeyError as e:
        # Log the missing variable and return the template with placeholder
        print(f"Warning: Missing template variable {e} in: {template_string}")
        return template_string.replace(f"{{{e}}}", f"[{e}]")

def validate_content_library(content_library, required_sections=None):
    """Validate that content library has all required sections."""
    if not content_library:
        print("Warning: Content library is None or empty")
        return False
    
    if required_sections:
        missing_sections = []
        for section in required_sections:
            if section not in content_library:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"Warning: Missing content library sections: {missing_sections}")
            return False
    
    return True

def generate_wordpress_introduction_html(ticker, rdata, content_library=None):
    """
    Generate WordPress introduction using content library variations following market-standard algorithms.
    Falls back to original function if content library is not available.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_introduction_html(ticker, rdata)
        
        # --- 1. Extract and Format All Necessary Data (Following Original Algorithm) ---
        profile_data = rdata.get('profile_data', {})
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        health_data = rdata.get('financial_health_data', {})
        analyst_data = rdata.get('analyst_info_data', {})
        profit_data = rdata.get('profitability_data', {})

        company_name = profile_data.get('Company Name', ticker)
        industry = profile_data.get('Industry', 'its')
        market_cap_fmt = profile_data.get('Market Cap', 'N/A')

        current_price_val = rdata.get('current_price')
        current_price_fmt = hc.format_html_value(current_price_val, 'currency', ticker=ticker)

        last_date_obj = rdata.get('last_date', datetime.now())
        if isinstance(last_date_obj, str):
            try:
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%B %Y', '%m/%d/%Y']:
                    try:
                        last_date_obj = datetime.strptime(last_date_obj, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # If no format works, use current date
                    last_date_obj = datetime.now()
            except (ValueError, TypeError):
                last_date_obj = datetime.now()
        elif not isinstance(last_date_obj, datetime):
            last_date_obj = datetime.now()
        
        last_date_fmt = last_date_obj.strftime('%B %Y')

        # Use yfinance SMA values from rdata instead of calculated ones
        sma50_val = rdata.get('sma_50')
        sma50_fmt = hc.format_html_value(sma50_val, 'currency', ticker=ticker)
        sma200_val = rdata.get('sma_200')
        sma200_fmt = hc.format_html_value(sma200_val, 'currency', ticker=ticker)
        
        analyst_target_val = hc._safe_float(analyst_data.get('Mean Target Price'))
        analyst_target_fmt = hc.format_html_value(analyst_target_val, 'currency', ticker=ticker)
        
        # CRITICAL FIX: Calculate analyst target percentage correctly
        # overall_pct_change is the FORECAST model percentage, NOT analyst target percentage!
        forecast_pct_val = rdata.get('overall_pct_change', 0.0)  # This is forecast vs current price
        
        # Calculate actual analyst target percentage
        analyst_upside_pct_val = 0.0
        if analyst_target_val is not None and current_price_val is not None and current_price_val != 0:
            analyst_upside_pct_val = ((analyst_target_val - current_price_val) / current_price_val) * 100
        analyst_upside_pct_fmt = f"{analyst_upside_pct_val:+.1f}%"
        
        volatility_val = rdata.get('volatility')
        volatility_fmt = hc.format_html_value(volatility_val, 'percent_direct', 1)

        rev_growth_val = hc._safe_float(profit_data.get('Quarterly Revenue Growth (YoY)'))
        rev_growth_fmt = hc.format_html_value(rev_growth_val, 'percent_direct')
        
        debt_equity_val = hc._safe_float(health_data.get('Debt/Equity (MRQ)'))
        debt_equity_fmt = hc.format_html_value(debt_equity_val, 'ratio')
        total_debt_fmt = health_data.get('Total Debt (MRQ)', 'N/A')

        rsi_val = detailed_ta_data.get('RSI_14')
        rsi_fmt = f"{rsi_val:.1f}" if isinstance(rsi_val, (int, float)) else "N/A"
        
        # --- 2. Generate Dynamic Text Snippets based on Data with Content Library Variations ---

        # Dynamic Momentum Text using content library
        trading_verb = get_variation(content_library, 'introduction.momentum.trading_verbs', ['trading'])
        momentum_phrase = ""
        if current_price_val and sma50_val and sma200_val:
            if current_price_val > sma50_val and current_price_val > sma200_val:
                momentum_phrase = get_variation(content_library, 'introduction.momentum.phrases.positive',
                    ['showing strong positive momentum, trading decisively above both its 50-day and 200-day moving averages'])
            elif current_price_val < sma50_val and current_price_val < sma200_val:
                momentum_phrase = get_variation(content_library, 'introduction.momentum.phrases.bearish',
                    ['currently in a bearish trend, trading below both its 50-day and 200-day moving averages'])
            elif current_price_val > sma50_val and current_price_val < sma200_val:
                momentum_phrase = get_variation(content_library, 'introduction.momentum.phrases.mixed_short_strong',
                    ['in a mixed technical state, trading above its short-term 50-day average but still under the long-term 200-day trendline'])
            else: # price < 50-day but > 200-day
                momentum_phrase = get_variation(content_library, 'introduction.momentum.phrases.mixed_long_strong',
                    ['experiencing a short-term pullback within a larger uptrend, as it trades below its 50-day average while holding above the 200-day'])
        else:
            momentum_phrase = get_variation(content_library, 'introduction.momentum.phrases.complex',
                ['exhibiting a complex technical picture'])

        # Dynamic Analyst Outlook Text using content library - FIXED: Use correct analyst percentage
        analyst_outlook_text = ""
        if analyst_target_val:
            source = get_variation(content_library, 'introduction.analyst_outlook.sources', ['Analysts'])
            sentiment_key = 'optimistic' if analyst_upside_pct_val > 5 else 'cautious' if analyst_upside_pct_val < -5 else 'stable'
            sentiment = get_variation(content_library, f'introduction.analyst_outlook.sentiments.{sentiment_key}', ['are positive'])
            connector = get_variation(content_library, 'introduction.analyst_outlook.connectors', ['with a 1-year price target of'])
            result = get_variation(content_library, f'introduction.analyst_outlook.results.{sentiment_key}', 
                [f'implying a potential {analyst_upside_pct_fmt} change'])
            
            result_text = result.format(analyst_upside_pct_fmt=analyst_upside_pct_fmt) if '{analyst_upside_pct_fmt}' in result else result.format(upside_pct_fmt=analyst_upside_pct_fmt) if '{upside_pct_fmt}' in result else result
            analyst_outlook_text = f"{source} {sentiment}, {connector} <strong>{analyst_target_fmt}</strong>, {result_text}"
        else:
            analyst_outlook_text = get_variation(content_library, 'introduction.analyst_outlook.unavailable',
                [f'Analyst price targets are currently unavailable for {ticker}'])
        
        # Dynamic Fundamental "Two Stories" Text using content library
        positive_fundamental = ""
        if rev_growth_val is not None and rev_growth_val > 5:
            positive_fundamental = get_variation(content_library, 'introduction.fundamental_story.positives.revenue_growth',
                [f'solid revenue growth (up {rev_growth_fmt} YoY)']).format(rev_growth_fmt=rev_growth_fmt)
        else:
            profit_margin_val = hc._safe_float(profit_data.get('Profit Margin (TTM)'))
            if profit_margin_val is not None and profit_margin_val > 15:
                profit_margin_fmt = hc.format_html_value(profit_margin_val, 'percent')
                positive_fundamental = get_variation(content_library, 'introduction.fundamental_story.positives.strong_margins',
                    [f'strong profitability with a {profit_margin_fmt} profit margin']).format(profit_margin_fmt=profit_margin_fmt)
            else:
                positive_fundamental = get_variation(content_library, 'introduction.fundamental_story.positives.brand_portfolio',
                    ['a portfolio of established brands'])

        negative_fundamental = ""
        if debt_equity_val is not None and debt_equity_val > 2.0:
            negative_fundamental = get_variation(content_library, 'introduction.fundamental_story.negatives.high_debt',
                [f'a high debt load (Debt/Equity: {debt_equity_fmt})']).format(debt_equity_fmt=debt_equity_fmt)
        else:
            earnings_growth_val = hc._safe_float(profit_data.get('Earnings Growth (YoY)'))
            if earnings_growth_val is not None and earnings_growth_val < 0:
                earnings_growth_fmt = hc.format_html_value(earnings_growth_val, 'percent_direct')
                negative_fundamental = get_variation(content_library, 'introduction.fundamental_story.negatives.earnings_contraction',
                    [f'a recent contraction in earnings (down {earnings_growth_fmt} YoY)']).format(earnings_growth_fmt=earnings_growth_fmt)
            else:
                negative_fundamental = get_variation(content_library, 'introduction.fundamental_story.negatives.intense_competition',
                    ['intense competition in its sector'])

        # Select fundamental story template and verbs using content library
        template = get_variation(content_library, 'introduction.fundamental_story.templates',
            ['On one hand, the company {benefit_verb} from {positive_fundamental}. On the other, it {challenge_verb} with {negative_fundamental}.'])
        benefit_verb = get_variation(content_library, 'introduction.fundamental_story.verbs.benefit', ['benefits'])
        challenge_verb = get_variation(content_library, 'introduction.fundamental_story.verbs.challenge', ['faces challenges'])
        boast_verb = get_variation(content_library, 'introduction.fundamental_story.verbs.boast', ['boasts'])
        held_back_verb = get_variation(content_library, 'introduction.fundamental_story.verbs.held_back', ['held back'])
        
        fundamental_story_text = template.format(
            benefit_verb=benefit_verb, 
            positive_fundamental=positive_fundamental,
            challenge_verb=challenge_verb,
            negative_fundamental=negative_fundamental,
            boast_verb=boast_verb,
            held_back_verb=held_back_verb
        )

        # Dynamic "What's Inside" text using content library
        technical_verdict = "Neutral"
        if "positive" in momentum_phrase or "bullish" in momentum_phrase or "upward" in momentum_phrase:
            technical_verdict = "Bullish"
        elif "bearish" in momentum_phrase or "downward" in momentum_phrase or "weakness" in momentum_phrase:
            technical_verdict = "Bearish"

        rsi_condition = "neutral"
        if isinstance(rsi_val, (int, float)):
            if rsi_val > 70: rsi_condition = "overbought"
            elif rsi_val < 30: rsi_condition = "oversold"

        fundamental_verdict = "be cautious"
        if debt_equity_val is not None and debt_equity_val < 1.0:
            fundamental_verdict = "looking solid"

        # --- 3. Construct the Final, Fully Dynamic HTML using Content Library Variations ---
        
        # Build the summary sentence using content library variations
        intro = get_variation(content_library, 'introduction.summary_sentence.intros', ['This report provides'])
        descriptor = get_variation(content_library, 'introduction.summary_sentence.descriptors', ['a detailed analysis of'])
        
        summary_parts = []
        if company_name not in [None, '', 'N/A']:
            summary_parts.append(f"<strong>{company_name} ({ticker})</strong>")
        else:
            summary_parts.append(f"<strong>{ticker}</strong>")
        if market_cap_fmt not in [None, '', 'N/A']:
            summary_parts.append(f"a {market_cap_fmt} company")
        if industry not in [None, '', 'N/A', 'its']:
            summary_parts.append(f"operating in the {industry} industry")
        
        summary_sentence = f"{intro} {descriptor} " + ", ".join(summary_parts) + "."
        
        # Core question using content library
        question_intro = get_variation(content_library, 'introduction.core_question.intros', ['The core question for investors is'])
        question_topic = get_variation(content_library, 'introduction.core_question.topics', 
            ['whether the current stock price represents a fair value and if the company is well-positioned for future growth'])
        hook = get_variation(content_library, 'introduction.core_question.hooks',
            [f'Is now the right time to invest in {company_name}? Let\'s examine how {ticker} stock is performing.'])
        hook_formatted = hook.format(company_name=company_name, ticker=ticker)
        
        # Headlines using content library
        main_headline = get_variation(content_library, 'introduction.headlines.main',
            ['Here\'s What You Need to Know Right Now']).format(ticker=ticker)
        inside_headline = get_variation(content_library, 'introduction.headlines.what_is_inside',
            ['What\'s Inside This Analysis?']).format(ticker=ticker)
        
        # Momentum base sentence using content library
        momentum_base = content_library.get('introduction', {}).get('momentum', {}).get('base', 
            'The stock is currently {trading_verb} at <strong>{current_price_fmt}</strong> (as of {last_date_fmt}), and it\'s {momentum_phrase}.')
        momentum_sentence = momentum_base.format(
            trading_verb=trading_verb,
            current_price_fmt=current_price_fmt,
            last_date_fmt=last_date_fmt,
            momentum_phrase=momentum_phrase
        )
        
        # Closing differentiator and final hook using content library
        differentiator = get_variation(content_library, 'introduction.closing_paragraphs.differentiator',
            ['Most stock analyses are either filled with hard-to-understand jargon or are overly simplistic. We provide clear, actionable information that is valuable whether you are a long-term investor or a short-term trader.'])
        final_hook = get_variation(content_library, 'introduction.closing_paragraphs.final_hook',
            [f'All in all, is {company_name} the right investment to help your portfolio succeed? Or are there underlying issues to be wary of? Stick around as we dive into the details.'])
        final_hook_formatted = final_hook.format(company_name=company_name, ticker=ticker)

        introduction_html = f"""
        <p>{summary_sentence} {question_intro} {question_topic}. {hook_formatted}</p>
        
        <h2>{main_headline}</h2>
        <p>{momentum_sentence}</p>
        <p>{analyst_outlook_text}. However, there's significant volatility here (<strong>{volatility_fmt} annualized</strong>), suggesting the potential for wide price swings.</p>
        <p>{company_name}'s fundamental story is nuanced. {fundamental_story_text}</p>
        
        <h2>{inside_headline}</h2>
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
        
        <p>{differentiator}</p>
        <p>{final_hook_formatted}</p>
        """

        return introduction_html

    except Exception as e:
        print(f"Warning: Error in WordPress introduction generation: {e}. Using fallback.")
        return hc.generate_introduction_html(ticker, rdata)

def generate_wordpress_metrics_summary_html(ticker, rdata, content_library=None):
    """
    Generate WordPress metrics summary using content library variations following market-standard algorithms.
    Falls back to original function if content library is not available.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_metrics_summary_html(ticker, rdata)
        
        # --- 1. Extract and Format All Necessary Data (Following Original Algorithm) ---
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        analyst_data = rdata.get('analyst_info_data', {})
        share_stats_data = rdata.get('share_statistics_data', {})
        price_stats_data = rdata.get('stock_price_stats_data', {})
        short_data = rdata.get('short_selling_data', {})
        historical_data = rdata.get('historical_data', pd.DataFrame())
        profile_data = rdata.get('profile_data', {})

        # Raw Values (Market Standard Algorithm)
        current_price_val = hc._safe_float(rdata.get('current_price'))
        forecast_1m_val = hc._safe_float(rdata.get('forecast_1m'))
        forecast_1y_val = hc._safe_float(rdata.get('forecast_1y'))
        analyst_target_val = hc._safe_float(analyst_data.get('Mean Target Price'))
        # Use yfinance SMA values from rdata instead of calculated ones
        sma50_val = hc._safe_float(rdata.get('sma_50'))
        sma200_val = hc._safe_float(rdata.get('sma_200'))
        rsi_val = hc._safe_float(detailed_ta_data.get('RSI_14'))
        macd_hist_val = hc._safe_float(detailed_ta_data.get('MACD_Hist'))
        low_52wk_val = hc._safe_float(price_stats_data.get('52 Week Low'))
        high_52wk_val = hc._safe_float(price_stats_data.get('52 Week High'))
        volatility_val = hc._safe_float(rdata.get('volatility'))
        beta_val = hc._safe_float(price_stats_data.get('Beta'))
        inst_own_val = hc._safe_float(share_stats_data.get('Institutional Ownership'))
        short_float_val = hc._safe_float(short_data.get('Short % of Float'))
        
        # **Market Standard: Green Days Calculation**
        green_days_val = 0
        total_days_val = 0
        if not historical_data.empty and len(historical_data) >= 30:
            last_30_days = historical_data.iloc[-30:]
            green_days_val = int((last_30_days['Close'] > last_30_days['Open']).sum())
            total_days_val = len(last_30_days)
        green_days_pct = (green_days_val / total_days_val * 100) if total_days_val > 0 else 0
        
        # Calculated Percentages (Market Standard Algorithm)
        forecast_1m_pct = ((forecast_1m_val - current_price_val) / current_price_val) * 100 if forecast_1m_val and current_price_val else 0.0
        forecast_1y_pct = rdata.get('overall_pct_change', 0.0)
        analyst_target_pct = ((analyst_target_val - current_price_val) / current_price_val) * 100 if analyst_target_val and current_price_val else 0.0
        
        # Formatted Strings for Display with Content Library Variations
        current_price_fmt = hc.format_html_value(current_price_val, 'currency', ticker=ticker)
        forecast_1m_fmt = f"{hc.format_html_value(forecast_1m_val, 'currency', ticker=ticker)} ({'▲' if forecast_1m_pct > 0 else '▼'} {forecast_1m_pct:+.1f}%)"
        forecast_1y_fmt = f"{hc.format_html_value(forecast_1y_val, 'currency', ticker=ticker)} ({'▲' if forecast_1y_pct > 0 else '▼'} {forecast_1y_pct:+.1f}%)"
        analyst_target_fmt = f"{hc.format_html_value(analyst_target_val, 'currency', ticker=ticker)} ({'▲' if analyst_target_pct > 0 else '▼'} {analyst_target_pct:+.1f}%)"
        sma50_fmt = hc.format_html_value(sma50_val, 'currency', ticker=ticker)
        sma200_fmt = hc.format_html_value(sma200_val, 'currency', ticker=ticker)
        rsi_fmt = f"{rsi_val:.1f}" if rsi_val else "N/A"
        macd_hist_fmt = f"({macd_hist_val:.2f})" if macd_hist_val else ""
        range_52wk_fmt = f"{hc.format_html_value(low_52wk_val, 'currency', ticker=ticker)} - {hc.format_html_value(high_52wk_val, 'currency', ticker=ticker)}"
        volatility_fmt = hc.format_html_value(volatility_val, 'percent_direct', 1)
        beta_fmt = f"{hc.format_html_value(beta_val, 'ratio')} (High Sensitivity)" if beta_val and beta_val > 1.2 else f"{hc.format_html_value(beta_val, 'ratio')}"
        green_days_fmt = f"{int(green_days_val)}/{int(total_days_val)} ({green_days_pct:.0f}%)"
        inst_own_fmt = hc.format_html_value(inst_own_val, 'percent_direct')
        short_float_fmt = (f"{hc.format_html_value(short_float_val, 'percent_direct')} (Low Bearish Bets)" if short_float_val and short_float_val < 2.0 else f"{hc.format_html_value(short_float_val, 'percent_direct')}")

        # --- 2. Dynamic Text Generation (Market Standard Algorithm) ---
        
        # Technical Pattern Text using content library
        technical_pattern_text = "mixed pattern"
        momentum_type = "mixed"
        if current_price_val and sma50_val and sma200_val:
            if current_price_val > sma50_val and current_price_val > sma200_val:
                technical_pattern_text = "bullish pattern"
                momentum_type = "bullish"
            elif current_price_val < sma50_val and current_price_val < sma200_val:
                technical_pattern_text = "bearish pattern"
                momentum_type = "bearish"
        
        # Get position verb from content library
        position_verb = get_variation(content_library, 'metrics_summary.paragraph1.technical_pattern.position_verbs', ['positioned'])
        
        # Technical pattern base using content library
        technical_base = content_library.get('metrics_summary', {}).get('paragraph1', {}).get('technical_pattern', {}).get('base', 
            'The technical indicators are showing a <strong>{technical_pattern_text}</strong>, as the price is {position_verb} relative to the {sma50_fmt} (50-day) and {sma200_fmt} (200-day) moving averages.')
        technical_sentence = technical_base.format(
            technical_pattern_text=technical_pattern_text,
            position_verb=position_verb,
            sma50_fmt=sma50_fmt,
            sma200_fmt=sma200_fmt
        )
        
        # Momentum suggestion using content library
        momentum_suggestion = get_variation(content_library, f'metrics_summary.paragraph1.technical_pattern.momentum_suggestion.{momentum_type}',
            ['This suggests the stock is in a period of consolidation.'])

        # RSI and MACD Condition Text using content library
        rsi_condition_text = "neutral"
        rsi_phrase = ""
        if rsi_val:
            if rsi_val > 70: 
                rsi_condition_text = "overbought"
                rsi_phrase = get_variation(content_library, 'metrics_summary.paragraph1.indicators.rsi.overbought',
                    [f'the Relative Strength Index (RSI) at <strong>{rsi_fmt}</strong> is in overbought territory'])
            elif rsi_val < 30: 
                rsi_condition_text = "oversold"
                rsi_phrase = get_variation(content_library, 'metrics_summary.paragraph1.indicators.rsi.oversold',
                    [f'the Relative Strength Index (RSI) at <strong>{rsi_fmt}</strong> is in oversold territory'])
            else:
                rsi_phrase = get_variation(content_library, 'metrics_summary.paragraph1.indicators.rsi.neutral',
                    [f'the Relative Strength Index (RSI) at <strong>{rsi_fmt}</strong> is in a neutral zone'])
        
        rsi_phrase_formatted = rsi_phrase.format(rsi_fmt=rsi_fmt) if '{rsi_fmt}' in rsi_phrase else rsi_phrase
        
        # MACD trend analysis using content library
        macd_trend_text = "neutral trend"
        macd_type = "neutral"
        if macd_hist_val:
            if macd_hist_val > 0.1: 
                macd_trend_text = "bullish short-term trend"
                macd_type = "bullish"
            elif macd_hist_val < -0.1:
                macd_trend_text = "bearish short-term trend"
                macd_type = "bearish"
        
        macd_phrase = get_variation(content_library, f'metrics_summary.paragraph1.indicators.macd.{macd_type}',
            [f'the MACD indicator shows a {macd_trend_text}'])
        macd_phrase_formatted = macd_phrase.format(macd_trend_text=macd_trend_text)
        
        # Implication phrase using content library
        implication_phrase = get_variation(content_library, f'metrics_summary.paragraph1.indicators.implications.{rsi_condition_text}',
            ['suggesting the stock is currently in equilibrium'])

        # 52-Week Range Position Text using content library and market standard algorithm
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

        # Range analysis using content library
        range_intro = get_variation(content_library, 'metrics_summary.paragraph2.range_intro',
            [f'Over the past year, {ticker}\'s stock has traded between <strong>{hc.format_html_value(low_52wk_val, "currency", ticker=ticker)} and {hc.format_html_value(high_52wk_val, "currency", ticker=ticker)}</strong>.'])
        range_intro_formatted = range_intro.format(
            ticker=ticker,
            low_52wk_fmt=hc.format_html_value(low_52wk_val, 'currency', ticker=ticker),
            high_52wk_fmt=hc.format_html_value(high_52wk_val, 'currency', ticker=ticker)
        )
        
        range_analysis_base = content_library.get('metrics_summary', {}).get('paragraph2', {}).get('range_analysis', {}).get('base',
            'This tells us two things: first, {recovery_status_text}, and second, {range_position_text}, {implication_phrase}.')
        implication_phrase_range = get_variation(content_library, 'metrics_summary.paragraph2.range_analysis.implications',
            ['meaning big swings are less likely without a major catalyst'])
        
        range_analysis_text = range_analysis_base.format(
            recovery_status_text=recovery_status_text,
            range_position_text=range_position_text,
            implication_phrase=implication_phrase_range
        )

        # Forecast text using content library
        analyst_verb = get_variation(content_library, 'metrics_summary.paragraph2.forecast.analyst_verbs', ['Analysts expect'])
        growth_desc = get_variation(content_library, 'metrics_summary.paragraph2.forecast.growth_descs', ['modest growth'])
        target_type = get_variation(content_library, 'metrics_summary.paragraph2.forecast.target_types', ['1-year target'])
        
        forecast_base = content_library.get('metrics_summary', {}).get('paragraph2', {}).get('forecast', {}).get('base',
            '{analyst_verb} {growth_desc} ahead, with a {target_type} of <strong>{target_fmt} ({target_pct_fmt})</strong>.')
        forecast_text = forecast_base.format(
            analyst_verb=analyst_verb,
            growth_desc=growth_desc,
            target_type=target_type,
            target_fmt=hc.format_html_value(forecast_1y_val, 'currency', ticker=ticker),
            target_pct_fmt=f"{forecast_1y_pct:+.1f}%"
        )

        # Investor Bets Text using content library
        short_interest_desc = "very low short interest" if short_float_val and short_float_val < 2.0 else "moderate short interest" if short_float_val and short_float_val < 5.0 else "significant short interest"
        short_desc_key = "low" if short_float_val and short_float_val < 2.0 else "moderate" if short_float_val and short_float_val < 5.0 else "high"
        short_interest_desc = get_variation(content_library, f'metrics_summary.paragraph2.ownership.short_interest_descs.{short_desc_key}', [short_interest_desc])
        
        investor_bets_text = "most big investors are betting on the company's long-term success rather than a decline"
        if short_float_val and short_float_val > 5.0:
            investor_bets_text = "a notable number of investors are betting on a price decline"

        ownership_base = content_library.get('metrics_summary', {}).get('paragraph2', {}).get('ownership', {}).get('base',
            'Furthermore, with <strong>{inst_own_fmt} institutional ownership</strong> and {short_interest_desc} ({short_float_fmt}), it seems {investor_bets_text}.')
        ownership_text = ownership_base.format(
            inst_own_fmt=inst_own_fmt,
            short_interest_desc=short_interest_desc,
            short_float_fmt=hc.format_html_value(short_float_val, 'percent_direct'),
            investor_bets_text=investor_bets_text
        )

        # Get dynamic labels from content library
        price_prefix = get_variation(content_library, 'metrics_section_content.metric_descriptions.price_metrics.prefixes', ['Current trading price:'])
        trading_verb = get_variation(content_library, 'metrics_summary.paragraph1.trading_verbs', ['trading'])
        
        # Format the opening text
        opening_template = get_variation(content_library, 'metrics_summary.paragraph1.opening', 
            [f'At present, {ticker}\'s stock is {trading_verb} at <strong>{current_price_fmt}</strong>.'])
        opening_formatted = opening_template.format(ticker=ticker, trading_verb=trading_verb, current_price_fmt=current_price_fmt)
        
        # Enhanced metrics grid with market standard algorithm data
        html_content = f"""
        <div class="metrics-grid-container">
            <div class="metric-card">
                <div class="header">
                    <h3>💰 Current Price</h3>
                    <div style="width: 6px; height: 6px; background-color: #3b82f6; border-radius: 50%; animation: pulse 2s infinite;"></div>
                </div>
                <div class="main-value">{current_price_fmt}</div>
                <div class="sub-value">{price_prefix}</div>
            </div>
            
            <div class="metric-card">
                <div class="header">
                    <h3>🎯 Price Targets & Forecasts</h3>
                </div>
                <div class="metrics-list">
                    <div class="metric-row">
                        <span class="metric-label">1-Month Forecast:</span>
                        <div class="metric-value">
                            <span>{hc.format_html_value(forecast_1m_val, 'currency', ticker=ticker)}</span>
                            <span class="{'positive-value' if forecast_1m_pct > 0 else 'negative-value'}">
                                {'📈' if forecast_1m_pct > 0 else '📉'} {forecast_1m_pct:+.1f}%
                            </span>
                        </div>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">1-Year Forecast:</span>
                        <div class="metric-value">
                            <span>{hc.format_html_value(forecast_1y_val, 'currency', ticker=ticker)}</span>
                            <span class="{'positive-value' if forecast_1y_pct > 0 else 'negative-value'}">
                                {'📈' if forecast_1y_pct > 0 else '📉'} {forecast_1y_pct:+.1f}%
                            </span>
                        </div>
                    </div>
                    <div class="metric-row border-top">
                        <span class="metric-label">Analyst Mean Target:</span>
                        <div class="metric-value">
                            <span>{hc.format_html_value(analyst_target_val, 'currency', ticker=ticker)}</span>
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
                            {'🚀' if technical_pattern_text == 'bullish pattern' else '📉' if technical_pattern_text == 'bearish pattern' else '⚖️'} {technical_pattern_text.title()}
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">RSI (14-day):</span>
                        <span class="rsi-badge {'rsi-overbought' if rsi_condition_text == 'overbought' else 'rsi-oversold' if rsi_condition_text == 'oversold' else 'rsi-neutral'}">
                            {rsi_fmt} ({rsi_condition_text.title()}) {'🔥' if rsi_condition_text == 'overbought' else '❄️' if rsi_condition_text == 'oversold' else '⚖️'}
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
                            {hc.format_html_value(beta_val, 'ratio')}x {'🎢' if beta_val and beta_val > 1.2 else '🛡️' if beta_val and beta_val < 0.8 else '⚖️'}
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
                            {hc.format_html_value(short_float_val, 'percent_direct')} {'😊' if short_float_val and short_float_val < 2 else '😐' if short_float_val and short_float_val < 5 else '😰'}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <div class="metrics-narrative">
            <p>{opening_formatted} {technical_sentence} {momentum_suggestion}</p>
            <p>However, {rsi_phrase_formatted}, while {macd_phrase_formatted}, {implication_phrase}.</p>
            <p>{range_intro_formatted} {range_analysis_text} {forecast_text} {ownership_text}</p>
        </div>
        """
        
        # Format the final HTML content
        html_content = html_content.format(
            opening_formatted=opening_formatted,
            technical_sentence=technical_sentence,
            momentum_suggestion=momentum_suggestion,
            rsi_phrase_formatted=rsi_phrase_formatted,
            macd_phrase_formatted=macd_phrase_formatted,
            implication_phrase=implication_phrase,
            range_intro_formatted=range_intro_formatted,
            range_analysis_text=range_analysis_text,
            forecast_text=forecast_text,
            ownership_text=ownership_text
        )
        
        return html_content

    except Exception as e:
        print(f"Warning: Error in WordPress metrics summary generation: {e}. Using fallback.")
        return hc.generate_metrics_summary_html(ticker, rdata)

def generate_wordpress_metrics_section_content(metrics, ticker=None, content_library=None):
    """
    Generate WordPress metrics section content using content library variations.
    Falls back to original function if content library is not available.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_metrics_section_content(metrics, ticker)
        
        rows = ""
        
        if isinstance(metrics, dict):
            row_parts = []
            
            for k, v in metrics.items():
                # Determine format type (same logic as original)
                format_type = "string" 
                k_lower = str(k).lower()
                if "date" in k_lower: format_type = "date"
                elif "yield" in k_lower or "payout ratio" in k_lower: format_type = "percent_direct"
                elif "ratio" in k_lower or "beta" in k_lower: format_type = "ratio"
                elif "margin" in k_lower or "ownership" in k_lower or "growth" in k_lower or "%" in k_lower: format_type = "percent_direct"
                elif "price" in k_lower or "value" in k_lower or "dividend rate" in k_lower: format_type = "currency"
                elif "volume" in k_lower or "shares" in k_lower or "employees" in k_lower: format_type = "integer"
                elif "market cap" in k_lower: format_type = "large_number"

                formatted_v = hc.format_html_value(v, format_type, ticker=ticker)
                
                if formatted_v != "N/A":
                    # Add contextual enhancement for WordPress
                    enhanced_key = enhance_metric_key(k, content_library)
                    row_parts.append(f"<tr><td>{enhanced_key}</td><td>{formatted_v}</td></tr>") 

            rows = "".join(row_parts)

        if not rows:
            # Use variation for empty data message
            empty_message = get_variation(content_library, 'metrics_section_content.empty_data_messages.variations',
                ['No displayable data is available for this category.'])
            rows = f"<tr><td colspan='2' style='text-align: center; font-style: italic;'>{empty_message}</td></tr>"

        # Use variation for table structure
        return f"""<div class="table-container">
                       <table class="metrics-table">
                           <tbody>{rows}</tbody>
                       </table>
                   </div>"""
                   
    except Exception as e:
        # Use variation for error message
        error_message = "Error displaying metric data."
        if content_library:
            error_message = get_variation(content_library, 'metrics_section_content.error_messages.variations',
                ['Error displaying metric data.'])
        
        print(f"Warning: Error in WordPress metrics section generation: {e}. Using fallback.")
        return f"""<div class="table-container">
                       <table class="metrics-table">
                           <tbody>
                               <tr><td colspan='2' style='text-align: center; color: red;'>{error_message}</td></tr>
                           </tbody>
                       </table>
                   </div>"""

def enhance_metric_key(key, content_library):
    """
    Enhance metric key names using content library variations.
    """
    try:
        key_lower = str(key).lower()
        
        # Determine metric category and enhance accordingly
        if "price" in key_lower or "value" in key_lower:
            prefix = get_variation(content_library, 'metrics_section_content.metric_descriptions.price_metrics.prefixes',
                ['Current price:'])
            if prefix != key:
                return f"{prefix} {key}"
                
        elif "ratio" in key_lower or "beta" in key_lower:
            descriptor = get_variation(content_library, 'metrics_section_content.metric_descriptions.ratio_metrics.descriptors',
                ['Financial ratio'])
            # Only enhance if it adds value
            if len(key.split()) == 1:  # Single word metrics benefit from description
                return f"{key} ({descriptor})"
                
        elif "growth" in key_lower:
            indicator = get_variation(content_library, 'metrics_section_content.metric_descriptions.growth_metrics.indicators',
                ['Growth rate'])
            if "rate" not in key_lower:
                return f"{key} {indicator}"
                
        elif "volume" in key_lower or "shares" in key_lower:
            descriptor = get_variation(content_library, 'metrics_section_content.metric_descriptions.volume_metrics.descriptors',
                ['Trading volume'])
            if len(key.split()) == 1:
                return f"{key} ({descriptor})"
        
        # Return original key if no enhancement applies
        return str(key)
        
    except Exception:
        # Return original key on any error
        return str(key)

def generate_wordpress_total_valuation_html(ticker, rdata, content_library=None):
    """
    Generate WordPress total valuation content using content library variations.
    Falls back to original function if content library is not available.
    Following market-standard algorithm with comprehensive content library integration.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_total_valuation_html(ticker, rdata)
        
        # --- 1. Data Extraction and Parsing (same as market standard) ---
        profile_data = rdata.get('profile_data', {})
        valuation_data = rdata.get('total_valuation_data', {})
        dividend_data = rdata.get('dividends_data', {})
        health_data = rdata.get('financial_health_data', {})  # For actual cash and debt values

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

        # --- 2. Dynamic Narrative Generation (following market standard structure) ---
        
        # Part 1: Market Cap vs. Enterprise Value (First Paragraph)
        narrative_part1 = ""
        if market_cap_raw is not None and enterprise_value_raw is not None:
            # FIXED: Use actual cash and debt values from balance sheet for accurate net cash calculation
            total_cash_raw = _parse_formatted_value(health_data.get('Total Cash (MRQ)', 'N/A'))
            total_debt_raw = _parse_formatted_value(health_data.get('Total Debt (MRQ)', 'N/A'))
            
            # Calculate net debt using EV - Market Cap as primary method
            net_debt_from_ev = enterprise_value_raw - market_cap_raw
            
            # But use actual cash - debt for more accurate net cash display when available
            if total_cash_raw is not None and total_debt_raw is not None:
                net_cash_actual = total_cash_raw - total_debt_raw
                # Use actual calculation if it shows net cash position
                if net_cash_actual > 0:
                    net_debt = -net_cash_actual  # Negative means net cash
                else:
                    net_debt = net_debt_from_ev  # Use EV calculation
            else:
                net_debt = net_debt_from_ev  # Fallback to EV calculation
            
            if net_debt > 0.01 * market_cap_raw: # Check if debt is more than 1% of market cap
                net_debt_fmt = hc.format_html_value(net_debt, 'large_number')
                
                # Use content library variations for debt scenario
                market_cap_intro = get_variation(content_library, 'total_valuation.introduction_phrases.market_cap_context',
                    [f"Although the market considers {company_name} to be {industry_descriptor} with a {market_cap_fmt} market cap"])
                
                enterprise_higher = get_variation(content_library, 'total_valuation.introduction_phrases.enterprise_value_higher',
                    [f"its enterprise value is much higher at {enterprise_value_fmt}, with {net_debt_fmt} of that value added by debt"])
                
                debt_implication = get_variation(content_library, 'total_valuation.debt_implications.positive_debt',
                    [f"Investors are confident about {company_name}'s future earnings, but keep in mind the risk of that large amount of debt"])
                
                # Format with proper variables
                market_cap_text = market_cap_intro.format(
                    company_name=company_name,
                    industry_descriptor=industry_descriptor,
                    market_cap_fmt=f"<strong>{market_cap_fmt}</strong>"
                )
                
                enterprise_text = enterprise_higher.format(
                    enterprise_value_fmt=f"<strong>{enterprise_value_fmt}</strong>",
                    net_debt_fmt=f"<strong>{net_debt_fmt}</strong>"
                )
                
                debt_text = debt_implication.format(company_name=company_name)
                
                narrative_part1 = f"{market_cap_text}, {enterprise_text}. {debt_text}."
                
            else: # Net cash position or negligible debt
                net_cash_fmt = hc.format_html_value(abs(net_debt), 'large_number')
                
                # Use content library variations for cash scenario
                market_cap_intro = get_variation(content_library, 'total_valuation.introduction_phrases.market_cap_context',
                    [f"While {company_name} commands a {market_cap_fmt} market capitalization as {industry_descriptor}"])
                
                enterprise_lower = get_variation(content_library, 'total_valuation.introduction_phrases.enterprise_value_lower',
                    [f"its enterprise value of {enterprise_value_fmt} is lower, reflecting a strong net cash position of approximately {net_cash_fmt}"])
                
                cash_implication = get_variation(content_library, 'total_valuation.debt_implications.positive_cash',
                    ["This financial strength provides a cushion and flexibility for future investments"])
                
                # Format with proper variables
                market_cap_text = market_cap_intro.format(
                    company_name=company_name,
                    market_cap_fmt=f"<strong>{market_cap_fmt}</strong>",
                    industry_descriptor=industry_descriptor
                )
                
                enterprise_text = enterprise_lower.format(
                    enterprise_value_fmt=f"<strong>{enterprise_value_fmt}</strong>",
                    net_cash_fmt=f"<strong>{net_cash_fmt}</strong>"
                )
                
                narrative_part1 = f"{market_cap_text}, {enterprise_text}. {cash_implication}."
        else:
            # Fallback when data is not available
            fallback_statement = get_variation(content_library, 'total_valuation.fallback_statements.generic_valuation',
                ["The company's total valuation, including both its market capitalization and debt, provides a comprehensive view of its worth"])
            narrative_part1 = fallback_statement

        # Part 2: Valuation Ratios and Outlook (Second Paragraph)
        narrative_parts2_and_3 = []
        if ev_rev_fmt != 'N/A' and ev_ebitda_fmt != 'N/A':
            # Determine premium positioning using market-standard logic
            premium_key = "neutral"
            if ev_rev_raw is not None and ev_ebitda_raw is not None:
                if ev_rev_raw > 4 or ev_ebitda_raw > 15:
                    premium_key = "premium"
                elif ev_rev_raw < 1.5 and ev_ebitda_raw < 8 and ev_rev_raw > 0 and ev_ebitda_raw > 0:
                    premium_key = "attractive"
            
            # Use content library variations
            ratio_intro = get_variation(content_library, 'total_valuation.valuation_analysis.ratio_introduction',
                ['The valuation ratios tell an interesting story'])
            
            premium_text = get_variation(content_library, f'total_valuation.valuation_analysis.premium_positioning.{premium_key}',
                ['trades at a valuation that reflects its market position'])
            
            market_position_desc = get_variation(content_library, 'total_valuation.valuation_analysis.market_position_descriptors',
                ["This reflects the company's strong market position and brand assets"])
            
            risk_statement = get_variation(content_library, 'total_valuation.valuation_analysis.valuation_risk_statements',
                ["But it also means the stock may have little room for error"])
            
            narrative_parts2_and_3.append(
                f"{ratio_intro}: at <strong>{ev_rev_fmt}</strong> revenue and <strong>{ev_ebitda_fmt}</strong> EBITDA, {company_name} {premium_text}. "
                f"{market_position_desc}. {risk_statement}."
            )

        # Future outlook with earnings and dividend dates
        earnings_text = ""
        dividend_text = ""
        
        if next_earn_date != 'N/A':
            earnings_importance = get_variation(content_library, 'total_valuation.future_outlook.earnings_importance',
                [f"The upcoming {next_earn_date} earnings report will be crucial in showing whether {company_name}'s businesses can grow into this valuation"])
            
            earnings_text = earnings_importance.format(
                next_earn_date=f"<strong>{next_earn_date}</strong>",
                company_name=company_name
            )

        if has_dividend and ex_div_date != 'N/A':
            dividend_significance = get_variation(content_library, 'total_valuation.future_outlook.dividend_significance',
                [f"the {ex_div_date} ex-dividend date serves as a reminder that {company_name} still rewards shareholders even as it invests for growth"])
            
            dividend_text = dividend_significance.format(
                ex_div_date=f"<strong>{ex_div_date}</strong>",
                company_name=company_name
            )

        # Combine earnings and dividend text intelligently (market standard logic)
        if earnings_text and dividend_text:
            narrative_parts2_and_3.append(f"{earnings_text}, while {dividend_text}.")
        elif earnings_text:
            narrative_parts2_and_3.append(f"{earnings_text}.")
        elif dividend_text:
            dividend_text_capitalized = dividend_text[0].upper() + dividend_text[1:] if len(dividend_text) > 1 else dividend_text.upper()
            narrative_parts2_and_3.append(f"{dividend_text_capitalized}.")

        # Quality premium statement
        quality_statement = get_variation(content_library, 'total_valuation.future_outlook.quality_premium_statements',
            ["Essentially, you're paying for quality - but quality doesn't come cheap"])
        narrative_parts2_and_3.append(f"{quality_statement}.")

        # --- 3. Assemble Final HTML (following market standard structure) ---
        
        # Create the two paragraphs
        paragraph1_html = f"<p>{narrative_part1}</p>"
        paragraph2_html = f"<p>{' '.join(narrative_parts2_and_3)}</p>" if narrative_parts2_and_3 else ""
        
        full_narrative_html = f'<div class="narrative">{paragraph1_html}{paragraph2_html}</div>'

        # Get the original table content (using WordPress version if available)
        try:
            table_content = generate_wordpress_metrics_section_content(valuation_data, ticker, content_library)
        except:
            table_content = hc.generate_metrics_section_content(valuation_data, ticker)
        
        # Return the new narrative followed by the table
        return full_narrative_html + table_content

    except Exception as e:
        print(f"Warning: Error in WordPress total valuation generation: {e}. Using fallback.")
        return hc.generate_total_valuation_html(ticker, rdata)

def generate_wordpress_conclusion_outlook_html(ticker, rdata, content_library=None):
    """
    Generate WordPress conclusion outlook content using content library variations.
    Follows market-standard algorithm with comprehensive content library integration.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_conclusion_outlook_html(ticker, rdata)

        # --- 1. Data Extraction (same as market standard) ---
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

        # Extract data using market-standard logic
        company_name = profile_data.get('Company Name', ticker)
        sentiment = rdata.get('sentiment', 'Neutral')
        current_price = hc._safe_float(rdata.get('current_price'))
        sma50 = hc._safe_float(rdata.get('sma_50'))
        sma200 = hc._safe_float(rdata.get('sma_200'))
        latest_rsi = hc._safe_float(detailed_ta_data.get('RSI_14'))
        macd_line = hc._safe_float(detailed_ta_data.get('MACD_Line'))
        macd_signal = hc._safe_float(detailed_ta_data.get('MACD_Signal'))
        support = hc._safe_float(detailed_ta_data.get('Support_30D'))
        resistance = hc._safe_float(detailed_ta_data.get('Resistance_30D'))
        forecast_1y = hc._safe_float(rdata.get('forecast_1y'))
        overall_pct_change = hc._safe_float(rdata.get('overall_pct_change'), default=0.0)
        roe = hc._safe_float(health_data.get('Return on Equity (ROE TTM)'))
        debt_equity = hc._safe_float(health_data.get('Debt/Equity (MRQ)'))
        op_cash_flow = hc._safe_float(health_data.get('Operating Cash Flow (TTM)'))
        fwd_pe = hc._safe_float(valuation_data.get('Forward P/E'))
        peg_ratio = hc._safe_float(valuation_data.get('PEG Ratio'))
        pfcf_ratio = hc._safe_float(valuation_data.get('Price/FCF (TTM)'))
        analyst_rec = analyst_data.get('Recommendation', 'N/A')
        mean_target = hc._safe_float(analyst_data.get('Mean Target Price'))
        fwd_yield = hc._safe_float(dividend_data.get('Dividend Yield (Fwd)'))
        payout_ratio = hc._safe_float(dividend_data.get('Payout Ratio'))
        rev_growth = hc._safe_float(profit_data.get('Quarterly Revenue Growth (YoY)'))
        earn_growth = hc._safe_float(profit_data.get('Earnings Growth (YoY)'))

        # Fundamental strength assessment (market standard logic)
        fundamental_strength_summary = "Moderate"  # Default
        if roe is not None and debt_equity is not None and op_cash_flow is not None:
            op_cf_pos = op_cash_flow > 0
            if roe > 15 and debt_equity < 1.5 and op_cf_pos:
                fundamental_strength_summary = "Strong"
            elif roe < 5 or debt_equity > 2.5 or not op_cf_pos:
                fundamental_strength_summary = "Weak"

        # --- 2. Technical Snapshot Section (enhanced with content library) ---
        tech_intro = get_variation(content_library, 'conclusion_outlook.technical_snapshot.section_introductions',
            ['Short-Term Technical Snapshot'])

        # Determine sentiment category for content library
        sentiment_str = str(sentiment)
        if 'Bullish' in sentiment_str:
            sentiment_category = 'bullish'
        elif 'Bearish' in sentiment_str:
            sentiment_category = 'bearish'
        else:
            sentiment_category = 'neutral'

        # Technical analysis narrative with content library variations
        sentiment_phrase = get_variation(content_library, f'conclusion_outlook.technical_snapshot.sentiment_descriptors.{sentiment_category}',
            [f'exhibits {sentiment_category} technical sentiment'])

        emphasis_word = get_variation(content_library, 'conclusion_outlook.transition_words.emphasis', ['importantly'])
        tech_intro_sentence = f"{emphasis_word.capitalize()}, {company_name} {sentiment_phrase}"

        # Add technical details with market-standard data processing
        causation_word = get_variation(content_library, 'conclusion_outlook.transition_words.causation', ['consequently'])
        performance_desc = get_variation(content_library, 'conclusion_outlook.performance_descriptors.neutral', ['balanced'])

        tech_details = []
        
        # RSI analysis
        if latest_rsi is not None:
            if latest_rsi < 30:
                rsi_desc = f"oversold conditions at {latest_rsi:.1f}"
            elif latest_rsi > 70:
                rsi_desc = f"overbought territory at {latest_rsi:.1f}"
            else:
                rsi_desc = f"neutral momentum at {latest_rsi:.1f}"
            tech_details.append(f"RSI indicating {rsi_desc}")

        # Moving average analysis
        if current_price is not None and sma50 is not None and sma200 is not None:
            if current_price > sma50 and current_price > sma200:
                ma_desc = "above both key moving averages"
            elif current_price < sma50 and current_price < sma200:
                ma_desc = "below both key moving averages"
            else:
                ma_desc = "between key moving averages"
            tech_details.append(f"price positioned {ma_desc}")

        # Support/resistance analysis
        if support is not None and resistance is not None:
            support_fmt = hc.format_html_value(support, 'currency', ticker=ticker)
            resistance_fmt = hc.format_html_value(resistance, 'currency', ticker=ticker)
            tech_details.append(f"trading within {support_fmt} support and {resistance_fmt} resistance levels")

        tech_detail_text = ", with " + " and ".join(tech_details) if tech_details else ""
        tech_analysis = f"{causation_word}, the technical framework provides {performance_desc} momentum indicators{tech_detail_text}"

        continuation_word = get_variation(content_library, 'conclusion_outlook.transition_words.continuation', ['furthermore'])
        contrast_word = get_variation(content_library, 'conclusion_outlook.transition_words.contrast', ['however'])
        
        tech_outlook = f"{continuation_word}, while short-term signals show {sentiment_category} characteristics, {contrast_word}, investors should consider broader market dynamics and individual risk tolerance when evaluating technical positioning"

        tech_narrative = f"{tech_intro_sentence}. {tech_analysis}. {tech_outlook}."

        # --- 3. Fundamental Outlook Section (enhanced with content library) ---
        fund_intro = get_variation(content_library, 'conclusion_outlook.fundamental_outlook.section_introductions',
            ['Longer-Term Fundamental & Forecast Outlook'])

        # Determine health category for content library
        if fundamental_strength_summary == "Strong":
            health_category = 'strong'
        elif fundamental_strength_summary == "Weak":
            health_category = 'weak'
        else:
            health_category = 'moderate'

        health_phrase = get_variation(content_library, f'conclusion_outlook.fundamental_outlook.health_assessments.{health_category}',
            [f'demonstrates {health_category} fundamental health'])

        emphasis_word2 = get_variation(content_library, 'conclusion_outlook.transition_words.emphasis', ['significantly'])
        fund_intro_sentence = f"{emphasis_word2.capitalize()}, {company_name} {health_phrase}"

        # Financial metrics analysis
        causation_word2 = get_variation(content_library, 'conclusion_outlook.transition_words.causation', ['therefore'])
        performance_desc2 = get_variation(content_library, 'conclusion_outlook.performance_descriptors.neutral', ['adequate'])

        financial_details = []
        if roe is not None:
            roe_fmt = hc.format_html_value(roe, 'percentage')
            if roe > 15:
                financial_details.append(f"strong return on equity of {roe_fmt}")
            elif roe < 5:
                financial_details.append(f"concerning return on equity of {roe_fmt}")
            else:
                financial_details.append(f"moderate return on equity of {roe_fmt}")

        if debt_equity is not None:
            de_fmt = hc.format_html_value(debt_equity, 'ratio')
            if debt_equity < 1.5:
                financial_details.append(f"conservative debt-to-equity ratio of {de_fmt}")
            elif debt_equity > 2.5:
                financial_details.append(f"elevated debt-to-equity ratio of {de_fmt}")
            else:
                financial_details.append(f"moderate debt-to-equity ratio of {de_fmt}")

        if op_cash_flow is not None:
            ocf_fmt = hc.format_html_value(op_cash_flow, 'large_number')
            if op_cash_flow > 0:
                financial_details.append(f"positive operating cash flow of {ocf_fmt}")
            else:
                financial_details.append(f"negative operating cash flow of {ocf_fmt}")

        if financial_details:
            metrics_text = ", ".join(financial_details[:3])  # Limit for readability
            financial_analysis = f"{causation_word2}, the company exhibits {metrics_text}, reflecting {performance_desc2} operational execution"
        else:
            financial_analysis = f"{causation_word2}, while detailed financial metrics are limited, the company maintains {performance_desc2} operational positioning"

        # Growth and valuation context
        continuation_word2 = get_variation(content_library, 'conclusion_outlook.transition_words.continuation', ['moreover'])
        
        growth_context = ""
        if rev_growth is not None and earn_growth is not None:
            rev_fmt = f"{rev_growth:+.1f}%" if rev_growth else "N/A"
            earn_fmt = f"{earn_growth:+.1f}%" if earn_growth else "N/A"
            if rev_growth > 10 and earn_growth > 10:
                growth_context = f"demonstrates robust growth momentum with revenue expansion of {rev_fmt} and earnings growth of {earn_fmt}"
            elif rev_growth < 0 or earn_growth < 0:
                growth_context = f"faces growth challenges with revenue change of {rev_fmt} and earnings evolution of {earn_fmt}"
            else:
                growth_context = f"maintains measured growth trajectory with revenue development of {rev_fmt} and earnings progression of {earn_fmt}"
        else:
            growth_context = "continues to develop its operational growth trajectory"

        contrast_word2 = get_variation(content_library, 'conclusion_outlook.transition_words.contrast', ['however'])
        
        valuation_context = ""
        if fwd_pe is not None:
            pe_fmt = hc.format_html_value(fwd_pe, 'ratio')
            if fwd_pe < 15:
                valuation_context = f"trades at an attractive forward P/E of {pe_fmt}"
            elif fwd_pe > 30:
                valuation_context = f"commands a premium forward P/E of {pe_fmt}"
            else:
                valuation_context = f"maintains a moderate forward P/E of {pe_fmt}"
        else:
            valuation_context = "maintains its market valuation positioning"

        analyst_context = ""
        if analyst_rec != 'N/A' and mean_target is not None:
            target_fmt = hc.format_html_value(mean_target, 'currency', ticker=ticker)
            analyst_context = f", with analyst consensus of '{analyst_rec}' and mean price target of {target_fmt}"
        elif analyst_rec != 'N/A':
            analyst_context = f", with analyst consensus of '{analyst_rec}'"

        investment_outlook = f"{contrast_word2}, from a valuation perspective, the stock {valuation_context}{analyst_context}"

        fund_narrative = f"{fund_intro_sentence}. {financial_analysis}. {continuation_word2}, the company {growth_context}. {investment_outlook}."

        # --- 4. Data-Driven Observations Section ---
        observations_intro = get_variation(content_library, 'conclusion_outlook.data_observations.section_introductions',
            ['Data-Driven Observations & Potential Tactics'])

        # Generate observations using actual data (market standard approach)
        observations = []
        data_driven_observations = rdata.get('data_driven_observations', [])
        
        if data_driven_observations:
            observations.extend(data_driven_observations[:5])  # Limit to 5
        else:
            # Generate default observations based on actual data
            if latest_rsi is not None:
                if latest_rsi < 30:
                    observations.append(f"RSI at {latest_rsi:.1f} suggests potential oversold conditions, possibly offering tactical entry opportunities for momentum traders")
                elif latest_rsi > 70:
                    observations.append(f"RSI at {latest_rsi:.1f} indicates potential overbought conditions, suggesting caution for new position initiation")

            if current_price is not None and sma50 is not None and sma200 is not None:
                current_fmt = hc.format_html_value(current_price, 'currency', ticker=ticker)
                if current_price > sma50 and current_price > sma200:
                    observations.append(f"Price at {current_fmt} above both moving averages indicates sustained upward trend momentum")
                elif current_price < sma50 and current_price < sma200:
                    observations.append(f"Price at {current_fmt} below both moving averages suggests downward trend persistence")

            if roe is not None and debt_equity is not None:
                roe_fmt = hc.format_html_value(roe, 'percentage')
                de_fmt = hc.format_html_value(debt_equity, 'ratio')
                if roe > 15 and debt_equity < 1.0:
                    observations.append(f"Strong ROE of {roe_fmt} combined with conservative debt-to-equity of {de_fmt} suggests robust capital efficiency")
                elif roe < 5 or debt_equity > 3.0:
                    observations.append(f"ROE of {roe_fmt} and debt-to-equity of {de_fmt} indicate potential fundamental challenges requiring monitoring")

        # --- 5. Overall Assessment Synthesis (enhanced with content library) ---
        link_phrase = get_variation(content_library, 'conclusion_outlook.overall_assessment.synthesis_phrases.technical_fundamental_link',
            ['Bridging the technical picture with the fundamental outlook'])

        # Valuation assessment with content library
        valuation_narrative = "moderate"
        valuation_context_detail = ""
        
        if fwd_pe is not None:
            pe_fmt = hc.format_html_value(fwd_pe, 'ratio')
            if fwd_pe < 15 and fwd_pe > 0:
                valuation_narrative = "potentially attractive"
                valuation_context_detail = f" with a forward P/E of {pe_fmt} below historical market averages"
            elif fwd_pe > 30:
                valuation_narrative = "potentially elevated"
                valuation_context_detail = f" reflecting a premium forward P/E of {pe_fmt} requiring growth justification"
            else:
                valuation_narrative = "moderate"
                valuation_context_detail = f" with a forward P/E of {pe_fmt} within reasonable market ranges"

        valuation_phrase = get_variation(content_library, 'conclusion_outlook.overall_assessment.synthesis_phrases.valuation_assessments',
            ['Valuation appears {valuation_narrative}'])
        valuation_phrase = valuation_phrase.format(valuation_narrative=valuation_narrative) + valuation_context_detail

        # Forecast summary with content library
        forecast_direction = "relatively flat"
        forecast_confidence = ""
        
        if overall_pct_change > 5:
            forecast_direction = f"potential upside ({overall_pct_change:+.1f}%)"
            forecast_confidence = ", suggesting measured appreciation potential"
        elif overall_pct_change < -5:
            forecast_direction = f"potential downside ({overall_pct_change:+.1f}%)"
            forecast_confidence = ", indicating measured decline potential"
        else:
            forecast_confidence = ", indicating stable near-term price evolution"

        forecast_1y_fmt = hc.format_html_value(forecast_1y, 'currency', ticker=ticker) if forecast_1y else 'N/A'
        forecast_phrase = get_variation(content_library, 'conclusion_outlook.overall_assessment.synthesis_phrases.forecast_summaries',
            ['The 1-year forecast model suggests {forecast_direction} towards ≈{forecast_1y_fmt}'])
        forecast_phrase = forecast_phrase.format(forecast_direction=forecast_direction, forecast_1y_fmt=forecast_1y_fmt) + forecast_confidence

        # Investor considerations with content library
        investor_phrase = get_variation(content_library, 'conclusion_outlook.overall_assessment.investor_considerations',
            ['Investors should weigh these factors against'])
        risk_phrase = get_variation(content_library, 'conclusion_outlook.overall_assessment.risk_horizon_phrases',
            ['identified risks and their individual investment horizon'])

        # Create comprehensive assessment
        emphasis_word3 = get_variation(content_library, 'conclusion_outlook.transition_words.emphasis', ['fundamentally'])
        causation_word3 = get_variation(content_library, 'conclusion_outlook.transition_words.causation', ['ultimately'])
        continuation_word3 = get_variation(content_library, 'conclusion_outlook.transition_words.continuation', ['additionally'])

        synthesis_intro = f"{link_phrase}, {company_name} exhibits <strong>{sentiment_str}</strong> technical sentiment alongside <strong>{fundamental_strength_summary.lower()}</strong> fundamental health"
        valuation_sentence = f"{emphasis_word3}, {valuation_phrase}"
        forecast_sentence = f"{causation_word3}, {forecast_phrase}"
        investor_sentence = f"{continuation_word3}, {investor_phrase} {risk_phrase}"

        overall_narrative = f"{synthesis_intro}. {valuation_sentence}. {forecast_sentence}. {investor_sentence}."

        # --- 6. Disclaimer (enhanced with content library) ---
        disclaimer_intro = get_variation(content_library, 'conclusion_outlook.disclaimers.introductions',
            ['<strong>Important:</strong> This analysis synthesizes model outputs and publicly available data for informational purposes only'])
        disclaimer_main = get_variation(content_library, 'conclusion_outlook.disclaimers.main_disclaimer',
            ['It is not investment advice. Market conditions change rapidly. Always conduct thorough independent research and consult a qualified financial advisor before making investment decisions'])

        disclaimer_html = f"<p class='disclaimer'>{disclaimer_intro}. {disclaimer_main}</p>"

        # --- 7. Assemble Final HTML (following market standard structure) ---
        html_parts = []

        # Technical snapshot and fundamental outlook columns
        html_parts.append(f"""
        <div class="conclusion-columns">
            <div class="conclusion-column">
                <h3>{tech_intro}</h3>
                <div class="narrative">
                    <p>{tech_narrative}</p>
                </div>
            </div>
            <div class="conclusion-column">
                <h3>{fund_intro}</h3>
                <div class="narrative">
                    <p>{fund_narrative}</p>
                </div>
            </div>
        </div>
        """)

        # Data-driven observations section (if available)
        if observations:
            observations_html = f"""
            <div class="data-driven-observations">
                <h4>{observations_intro}</h4>
                <ul>
            """
            for obs in observations:
                observations_html += f"<li>{obs}</li>\n"
            observations_html += """
                </ul>
            </div>
            """
            html_parts.append(observations_html)

        # Overall assessment
        html_parts.append(f"""
        <div class="narrative">
            <h4>Overall Assessment & Outlook</h4>
            <p>{overall_narrative}</p>
        </div>
        """)

        # Disclaimer
        html_parts.append(disclaimer_html)

        return ''.join(html_parts)

    except Exception as e:
        print(f"Warning: Error in WordPress conclusion outlook generation: {e}. Using fallback.")
        return hc.generate_conclusion_outlook_html(ticker, rdata)

def generate_wordpress_company_profile_html(ticker, rdata, content_library=None):
    """
    Enhanced WordPress-specific company profile section generator using content library variations.
    Implements market-standard algorithms with comprehensive content library integration.
    Falls back to original function if content library is not available.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_company_profile_html(ticker, rdata)
        
        # --- 1. Data Extraction and Processing (Market Standard Algorithm) ---
        profile_data = rdata.get('profile_data', {})
        if not isinstance(profile_data, dict): 
            profile_data = {}
            
        # Extract core company data
        company_name = profile_data.get('Company Name', ticker)
        sector = profile_data.get('Sector', '')
        industry = profile_data.get('Industry', '')
        market_cap = profile_data.get('Market Cap', '')
        employees = profile_data.get('Employees', '')
        summary_text = str(profile_data.get('Summary', ''))
        
        # Clean and validate data (market standard approach)
        sector = sector.strip() if sector else 'N/A'
        industry = industry.strip() if industry else 'N/A'
        market_cap = market_cap.strip() if market_cap else 'N/A'
        employees = str(employees).strip() if employees else 'N/A'
        
        # Website processing with enhanced validation
        website_link = profile_data.get('Website', '#')
        if website_link and isinstance(website_link, str) and not website_link.startswith(('http://', 'https://')) and website_link != '#':
             website_link = f"https://{website_link}" 
        elif not website_link or website_link == '#':
             website_link = '#' 

        # --- 2. Profile Grid Generation (Enhanced Structure) ---
        profile_items = []
        if sector != 'N/A': 
            profile_items.append(f"<div class='profile-item'><span>Sector: </span> {hc.format_html_value(sector, 'string')}</div>")
        if industry != 'N/A': 
            profile_items.append(f"<div class='profile-item'><span>Industry: </span>{hc.format_html_value(industry, 'string')}</div>")
        if market_cap != 'N/A': 
            profile_items.append(f"<div class='profile-item'><span>Market Cap: </span>{hc.format_html_value(market_cap, 'large_number')}</div>")
        if employees != 'N/A': 
            profile_items.append(f"<div class='profile-item'><span>Employees: </span>{hc.format_html_value(employees, 'integer')}</div>")

        if website_link != '#':
             profile_items.append(f"<div class='profile-item'><span>Website:</span><a href='{website_link}' target='_blank' rel='noopener noreferrer'>{hc.format_html_value(profile_data.get('Website','N/A'), 'string')}</a></div>")
        elif 'Website' in profile_data: 
             profile_items.append(f"<div class='profile-item'><span>Website:</span>{hc.format_html_value(profile_data.get('Website'), 'string')} (Link invalid/missing)</div>")

        # Location assembly
        location_parts = [profile_data.get('City'), profile_data.get('State'), profile_data.get('Country')]
        location_str = ', '.join(filter(None, [str(p) if p is not None else None for p in location_parts])) 
        if location_str: 
            profile_items.append(f"<div class='profile-item'><span>Headquarters:</span>{location_str}</div>")

        profile_grid = f'<div class="profile-grid">{"".join(profile_items)}</div>' if profile_items else "<p>Basic company identification data is limited.</p>"

        # --- 3. Content Library Integration (Using Exact Key Paths) ---
        
        # Get section title using exact content library path
        summary_title = get_variation(content_library, 'company_profile.titles', ["Business Overview"])
        
        # Get narrative introduction using exact content library path
        narrative_focus = get_variation(content_library, 'company_profile.introductions', 
            ["A brief overview of the company's business activities provides context for the following analysis."])

        # --- 4. Market-Standard Algorithm for Content Generation ---
        
        # Assess data availability for strategic narrative approach
        has_sector_industry = (sector != 'N/A' and industry != 'N/A')
        has_scale_metrics = (market_cap != 'N/A' or employees != 'N/A')
        has_detailed_summary = bool(summary_text and 
                               summary_text != 'No detailed business summary available.' and 
                               len(summary_text.strip()) > 50)
        
        # Calculate business context score for dynamic content approach (ensure all are booleans)
        business_context_score = int(has_sector_industry) + int(has_scale_metrics) + int(has_detailed_summary)
        
        html_parts = []
        
        # --- 5. Dynamic Paragraph Generation (Market Standard Structure) ---
        
        # PARAGRAPH 1: Industry Context and Company Positioning (4 sentences)
        
        # Get transition words from other content library sections for variety
        emphasis_word = get_variation(content_library, 'profitability_growth.transition_words.emphasis', 
            ['significantly', 'importantly', 'notably'])
        performance_desc = get_variation(content_library, 'profitability_growth.performance_descriptors.positive', 
            ['distinguished', 'robust', 'formidable'])
        
        # Sentence 1: Opening with narrative focus and industry positioning
        if has_sector_industry:
            sector_context = f"{company_name} operates as a {performance_desc} entity within the {sector.lower()} sector, specifically positioned in the {industry.lower()} industry"
        else:
            sector_context = f"{company_name} operates within the broader market landscape as a {performance_desc} business entity"
        
        opening_sentence = f"{narrative_focus} {emphasis_word.capitalize()}, {sector_context}."
        
        # Sentence 2: Business analysis importance with causation
        causation_word = get_variation(content_library, 'profitability_growth.transition_words.causation', 
            ['consequently', 'therefore', 'thus'])
        
        analysis_importance = f"{causation_word}, comprehensive understanding of the company's operational framework and competitive positioning serves as the foundation for informed investment analysis."
        
        # Sentence 3: Scale and market presence context
        continuation_word = get_variation(content_library, 'profitability_growth.transition_words.continuation', 
            ['furthermore', 'additionally', 'moreover'])
        
        if market_cap != 'N/A' and employees != 'N/A':
            scale_context = f"{continuation_word}, with a market capitalization of <strong>{market_cap}</strong> and <strong>{employees}</strong> employees, the company demonstrates substantial operational scale and market presence."
        elif market_cap != 'N/A':
            scale_context = f"{continuation_word}, with a market capitalization of <strong>{market_cap}</strong>, the company maintains significant market presence and financial standing."
        elif employees != 'N/A':
            scale_context = f"{continuation_word}, with <strong>{employees}</strong> employees, the company maintains meaningful operational infrastructure and workforce capabilities."
        else:
            scale_context = f"{continuation_word}, the company maintains its competitive market position through strategic operational focus and business development."
        
        # Sentence 4: Investment context establishment
        emphasis_word2 = get_variation(content_library, 'profitability_growth.transition_words.emphasis',
            ['fundamentally', 'essentially', 'critically'])
        
        investment_context = f"{emphasis_word2.capitalize()}, this business profile provides essential context for evaluating financial performance, competitive advantages, and long-term value creation potential."
        
        paragraph1 = f"{opening_sentence} {analysis_importance} {scale_context} {investment_context}"
        html_parts.append(f"<p>{paragraph1}</p>")
        
        # PARAGRAPH 2: Business Operations and Strategic Positioning (4 sentences)
        
        if has_detailed_summary:
            # Process summary text with intelligent parsing
            sentences = summary_text.replace('. The ', '. |SPLIT| The ').replace('; ', '; |SPLIT| ').split('|SPLIT|')
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]
            
            if len(sentences) >= 2:
                # Sentence 1: Operations introduction with summary content
                emphasis_word3 = get_variation(content_library, 'profitability_growth.transition_words.emphasis',
                    ['specifically', 'particularly', 'notably'])
                
                # Clean first sentence for integration
                first_sentence = sentences[0].strip()
                if not first_sentence.endswith('.'):
                    first_sentence += '.'
                    
                operations_intro = f"{emphasis_word3.capitalize()}, examining the company's business operations reveals that {first_sentence.lower()}"
                
                # Sentence 2: Strategic positioning with second summary sentence
                causation_word2 = get_variation(content_library, 'profitability_growth.transition_words.causation',
                    ['therefore', 'consequently', 'accordingly'])
                
                if len(sentences) > 1:
                    second_sentence = sentences[1].strip()
                    if not second_sentence.endswith('.'):
                        second_sentence += '.'
                    strategic_detail = f"{causation_word2}, {second_sentence.lower()}"
                else:
                    strategic_detail = f"{causation_word2}, this operational approach enables the company to maintain competitive differentiation and market positioning."
                
                # Sentence 3: Competitive context with performance descriptors
                continuation_word2 = get_variation(content_library, 'profitability_growth.transition_words.continuation',
                    ['additionally', 'furthermore', 'moreover'])
                performance_desc2 = get_variation(content_library, 'profitability_growth.performance_descriptors.positive',
                    ['strategic', 'comprehensive', 'sophisticated'])
                
                if len(sentences) > 2:
                    third_sentence = sentences[2].strip()
                    if not third_sentence.endswith('.'):
                        third_sentence += '.'
                    competitive_context = f"{continuation_word2}, {third_sentence.lower()}"
                else:
                    competitive_context = f"{continuation_word2}, this {performance_desc2} business approach supports sustainable competitive advantages and operational excellence."
                
                # Sentence 4: Market adaptation and growth potential
                contrast_word = get_variation(content_library, 'profitability_growth.transition_words.contrast',
                    ['however', 'nevertheless', 'nonetheless'])
                performance_desc3 = get_variation(content_library, 'profitability_growth.performance_descriptors.neutral',
                    ['adaptive', 'resilient', 'flexible'])
                
                market_adaptation = f"{contrast_word}, beyond current operations, the company's {performance_desc3} strategic framework positions it to capitalize on emerging market opportunities and navigate industry evolution."
                
                paragraph2 = f"{operations_intro} {strategic_detail} {competitive_context} {market_adaptation}"
                html_parts.append(f"<p>{paragraph2}</p>")
            
            else:
                # Fallback for limited but available summary
                emphasis_word_fb = get_variation(content_library, 'company_profile.titles', 
                    ['notably', 'importantly'])
                performance_desc_fb = get_variation(content_library, 'financial_efficiency.performance_descriptors.neutral',
                    ['focused', 'targeted', 'disciplined'])
                
                summary_analysis = f"{emphasis_word_fb.capitalize()}, while operational details are constrained, available information indicates that {company_name} maintains a {performance_desc_fb} business strategy within its market segment."
                
                causation_word_fb = get_variation(content_library, 'dividends_shareholders.transition_words.causation',
                    ['consequently', 'therefore', 'thus'])
                
                strategic_approach = f"{causation_word_fb}, this strategic approach enables operational stability and positions the company for measured growth within its competitive environment."
                
                continuation_word_fb = get_variation(content_library, 'stock_price_statistics.transition_words.continuation',
                    ['furthermore', 'additionally', 'moreover'])
                performance_desc_fb2 = get_variation(content_library, 'technical_analysis_summary.performance_descriptors.positive',
                    ['effective', 'prudent', 'methodical'])
                
                execution_context = f"{continuation_word_fb}, this {performance_desc_fb2} execution framework supports sustainable business development and competitive positioning."
                
                investment_alignment = f"Ultimately, understanding these operational characteristics provides valuable context for assessing the company's alignment with various investment strategies and risk profiles."
                
                paragraph2_fb = f"{summary_analysis} {strategic_approach} {execution_context} {investment_alignment}"
                html_parts.append(f"<p>{paragraph2_fb}</p>")
        
        else:
            # Comprehensive fallback when summary is not available (4 sentences)
            emphasis_word_alt = get_variation(content_library, 'financial_health.transition_words.emphasis',
                ['importantly', 'significantly', 'critically'])
            performance_desc_alt = get_variation(content_library, 'profitability_growth.performance_descriptors.neutral',
                ['structured', 'systematic', 'organized'])
            
            # Sentence 1: Business framework establishment
            framework_intro = f"{emphasis_word_alt.capitalize()}, while comprehensive operational details are not immediately available, {company_name} operates within a {performance_desc_alt} business framework designed to address market demands and stakeholder objectives."
            
            # Sentence 2: Strategic development context
            causation_word_alt = get_variation(content_library, 'share_statistics.transition_words.causation',
                ['consequently', 'accordingly', 'therefore'])
            
            strategic_development = f"{causation_word_alt}, the company's strategic development priorities focus on operational efficiency, market positioning, and sustainable value creation within its chosen business segments."
            
            # Sentence 3: Competitive positioning
            continuation_word_alt = get_variation(content_library, 'dividends_shareholders.transition_words.continuation',
                ['furthermore', 'additionally', 'moreover'])
            performance_desc_alt2 = get_variation(content_library, 'stock_price_statistics.performance_descriptors.positive',
                ['deliberate', 'calculated', 'purposeful'])
            
            competitive_positioning = f"{continuation_word_alt}, this {performance_desc_alt2} approach enables the company to maintain operational focus while adapting to evolving market conditions and competitive dynamics."
            
            # Sentence 4: Investment perspective
            contrast_word_alt = get_variation(content_library, 'technical_analysis_summary.transition_words.contrast',
                ['however', 'nevertheless', 'nonetheless'])
            
            investment_perspective = f"{contrast_word_alt}, from an investment perspective, understanding the company's business foundation remains essential for evaluating financial performance, growth potential, and strategic execution capabilities."
            
            paragraph2_alt = f"{framework_intro} {strategic_development} {competitive_positioning} {investment_perspective}"
            html_parts.append(f"<p>{paragraph2_alt}</p>")
        
        # PARAGRAPH 3: Investment Analysis and Strategic Outlook (4 sentences)
        
        # Sentence 1: Transition to investment analysis
        contrast_word2 = get_variation(content_library, 'financial_efficiency.transition_words.contrast',
            ['however', 'nevertheless', 'beyond'])
        emphasis_word4 = get_variation(content_library, 'profitability_growth.transition_words.emphasis',
            ['fundamentally', 'essentially', 'ultimately'])
        performance_desc4 = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive',
            ['comprehensive', 'thorough', 'sophisticated'])
        
        investment_transition = f"{contrast_word2.capitalize()} operational specifics, {emphasis_word4} evaluating {company_name}'s investment potential requires {performance_desc4} analysis of its market positioning, competitive advantages, and strategic execution capabilities."
        
        # Sentence 2: Financial performance correlation
        causation_word3 = get_variation(content_library, 'share_statistics.transition_words.causation',
            ['consequently', 'therefore', 'accordingly'])
        
        financial_correlation = f"{causation_word3}, investors should assess how the company's business model, operational efficiency, and strategic initiatives translate into sustainable financial performance and long-term shareholder value creation."
        
        # Sentence 3: Valuation framework
        continuation_word3 = get_variation(content_library, 'stock_price_statistics.transition_words.continuation',
            ['furthermore', 'additionally', 'importantly'])
        performance_desc5 = get_variation(content_library, 'technical_analysis_summary.performance_descriptors.neutral',
            ['balanced', 'measured', 'prudent'])
        
        valuation_framework = f"{continuation_word3}, this business foundation supports {performance_desc5} valuation assessment, risk evaluation, and strategic investment decision-making within the broader market context."
        
        # Sentence 4: Growth potential and outlook
        emphasis_word5 = get_variation(content_library, 'financial_health.transition_words.emphasis',
            ['ultimately', 'fundamentally', 'essentially'])
        performance_desc6 = get_variation(content_library, 'profitability_growth.performance_descriptors.positive',
            ['dynamic', 'adaptive', 'progressive'])
        
        growth_outlook = f"{emphasis_word5.capitalize()}, understanding these business characteristics enables investors to evaluate growth potential, competitive resilience, and the company's capacity to generate returns across various market conditions and investment horizons."
        
        paragraph3 = f"{investment_transition} {financial_correlation} {valuation_framework} {growth_outlook}"
        html_parts.append(f"<p>{paragraph3}</p>")
        
        # --- 6. Final HTML Assembly ---
        narrative_html = '\n'.join(html_parts)
        summary_html = f"<h4>{summary_title}</h4>\n{narrative_html}"

        return profile_grid + summary_html

    except Exception as e:
        print(f"Warning: Error in WordPress company profile generation: {e}. Using fallback.")
        return hc.generate_company_profile_html(ticker, rdata)
    

def generate_wordpress_valuation_metrics_html(ticker, rdata, content_library=None):
    """
    Enhanced WordPress-specific valuation metrics section using market-standard algorithms
    and comprehensive content library integration with exact key paths.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_valuation_metrics_html(ticker, rdata)
        
        # --- 1. Comprehensive Data Extraction & Assessment ---
        valuation_data = rdata.get('valuation_data', {})
        total_valuation_data = rdata.get('total_valuation_data', {})
        financial_data = rdata.get('financial_data', {})
        if not isinstance(valuation_data, dict): valuation_data = {}
        if not isinstance(total_valuation_data, dict): total_valuation_data = {}
        if not isinstance(financial_data, dict): financial_data = {}
        
        def _parse_value(value_str):
            if value_str is None or not isinstance(value_str, str) or value_str.lower() == 'n/a': return None
            try: return float(value_str.replace('x', '').strip())
            except (ValueError, TypeError): return None
        
        def _parse_percentage(value_str):
            if value_str is None or not isinstance(value_str, str) or value_str.lower() == 'n/a': return None
            try: 
                # Remove % sign and convert to decimal
                cleaned = value_str.replace('%', '').strip()
                return float(cleaned) / 100.0
            except (ValueError, TypeError): return None
                
        # Core valuation metrics
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

        # Enhanced margin data for comprehensive analysis
        gross_margin_raw = _parse_percentage(financial_data.get('Gross Margin', 'N/A'))
        op_margin_raw = _parse_percentage(financial_data.get('Operating Margin', 'N/A'))
        ebitda_margin_raw = _parse_percentage(financial_data.get('EBITDA Margin', 'N/A'))
        net_margin_raw = _parse_percentage(financial_data.get('Net Margin', 'N/A'))
        
        # Format margin data for display
        gross_margin_fmt = f"{gross_margin_raw*100:.2f}%" if gross_margin_raw is not None else 'N/A'
        op_margin_fmt = f"{op_margin_raw*100:.2f}%" if op_margin_raw is not None else 'N/A'
        ebitda_margin_fmt = f"{ebitda_margin_raw*100:.2f}%" if ebitda_margin_raw is not None else 'N/A'
        
        # Calculate net profit per dollar for enhanced narrative
        currency_symbol = hc.get_currency_symbol(ticker)
        net_profit_cents = f"{net_margin_raw*100:.2f}" if net_margin_raw is not None else 'N/A'

        # --- 2. Market-Standard Data Availability Assessment ---
        data_availability_score = 0
        has_pe_data = trailing_pe_raw is not None or forward_pe_raw is not None
        has_multiple_ratios = ps_ratio_raw is not None and pb_ratio_raw is not None
        has_ev_data = ev_rev_raw is not None or ev_ebitda_raw is not None
        has_margin_data = any([gross_margin_raw, op_margin_raw, ebitda_margin_raw, net_margin_raw])
        
        if has_pe_data: data_availability_score += 30
        if has_multiple_ratios: data_availability_score += 25  
        if has_ev_data: data_availability_score += 25
        if has_margin_data: data_availability_score += 20
        
        # Business context scoring for narrative adaptation
        business_context_score = 0
        if trailing_pe_raw and forward_pe_raw and trailing_pe_raw > 0 and forward_pe_raw > 0:
            business_context_score += 25  # Has earnings trend data
        if ps_ratio_raw and ps_ratio_raw > 0: business_context_score += 20
        if pb_ratio_raw and pb_ratio_raw > 0: business_context_score += 20  
        if ev_ebitda_raw and ev_ebitda_raw > 0: business_context_score += 35  # Most comprehensive metric
        
        # --- 3. Enhanced Dynamic Narrative Generation with Exact Library Keys ---
        
        # Section introduction using exact key path
        section_intro = get_variation(content_library, 'valuation_metrics.section_introductions', 
            ['Valuation Metrics Analysis'])
        
        html_parts = []
        
        # --- Paragraph 1: Market-Standard P/E Analysis with Enhanced Context ---
        if has_pe_data:
            pe_level_raw = forward_pe_raw if forward_pe_raw is not None else trailing_pe_raw
            
            # Market-standard P/E categorization with exact library keys
            if pe_level_raw <= 0: 
                interp_key = "negative"
                performance_category = "negative"
            elif pe_level_raw < 15: 
                interp_key = "attractive"
                performance_category = "positive"
            elif pe_level_raw < 25: 
                interp_key = "moderate"
                performance_category = "neutral"
            else: 
                interp_key = "high"
                performance_category = "negative"
            
            # Enhanced introduction using exact content library paths
            emphasis_word = get_variation(content_library, 'valuation_metrics.transition_words.emphasis', 
                ['significantly'])
            intro_component = get_variation(content_library, 'valuation_metrics.pe_analysis.introductions', 
                [f"{ticker} demonstrates"])
            valuation_desc = get_variation(content_library, f'valuation_metrics.performance_descriptors.{performance_category}', 
                ['notable'])
            interp_component = get_variation(content_library, f'valuation_metrics.pe_analysis.pe_interpretations.{interp_key}', 
                ["indicates a reasonably valued position"])
            
            # Format P/E introduction with proper ticker substitution
            intro_formatted = intro_component.format(ticker=ticker) if '{ticker}' in intro_component else intro_component
            
            pe_intro = f"{emphasis_word.capitalize()}, {intro_formatted} {valuation_desc} characteristics, with its Trailing P/E at <strong>{trailing_pe_fmt}</strong> and Forward P/E at <strong>{forward_pe_fmt}</strong>, which {interp_component}"
            
            # Enhanced P/E trend analysis with market-standard algorithm
            causation_word = get_variation(content_library, 'valuation_metrics.transition_words.causation', 
                ['consequently'])
            
            if trailing_pe_raw is not None and forward_pe_raw is not None and forward_pe_raw > 0:
                pe_change = ((forward_pe_raw - trailing_pe_raw) / trailing_pe_raw) * 100
                
                # Market-standard trend categorization  
                if pe_change < -10:
                    trend_key = "improving"
                    trend_desc = "suggesting improving earnings expectations and potential valuation compression"
                elif abs(pe_change) <= 10:
                    trend_key = "stable"  
                    trend_desc = "reflecting stable earnings outlook and consistent market expectations"
                else:
                    trend_key = "stable"  # Fallback to stable for deteriorating case
                    trend_desc = "indicating potential earnings pressure and valuation expansion concerns"
                    
                trend_component = get_variation(content_library, f'valuation_metrics.pe_analysis.trend_descriptions.{trend_key}', 
                    ["this reflects stable earnings outlook"])
                pe_trend = f"{causation_word}, the {pe_change:+.1f}% change from trailing to forward P/E suggests {trend_desc}, where {trend_component}"
            else:
                pe_trend = f"{causation_word}, while trend analysis is limited by available data, the current P/E positioning provides valuable market sentiment indicators for investment evaluation"
            
            # Market context with investment implications
            continuation_word = get_variation(content_library, 'valuation_metrics.transition_words.continuation', 
                ['furthermore'])
            
            if pe_level_raw < 15:
                market_context = "this valuation level relative to market standards may present tactical opportunities for value-oriented investors seeking undervalued positions"
            elif pe_level_raw > 30:
                market_context = "this premium positioning relative to market standards requires careful growth justification and comprehensive risk assessment"
            else:
                market_context = "this valuation range relative to market standards suggests reasonable pricing that aligns with sector expectations"
            
            paragraph1 = f"{pe_intro}. {pe_trend}. {continuation_word}, {market_context}."
            html_parts.append(f"<p>{paragraph1}</p>")
        
        # --- Paragraph 2: Enhanced P/S and P/B Analysis with Market Positioning ---
        if has_multiple_ratios:
            # Use exact content library key for P/S and P/B analysis
            ps_pb_statement = get_variation(content_library, 'valuation_metrics.ps_pb_analysis.statements',
                ["Meanwhile, its Price/Sales ratio of <strong>{ps_ratio_fmt}</strong> and Price/Book of <strong>{pb_ratio_fmt}</strong> show that {analysis_phrase}. {implication_phrase}"])
            analysis_phrase = get_variation(content_library, 'valuation_metrics.ps_pb_analysis.analysis_phrases',
                ["the company trades at multiples that warrant attention"])
            implication_phrase = get_variation(content_library, 'valuation_metrics.ps_pb_analysis.implication_phrases',
                ["These metrics provide insight into market positioning."])
            
            # Format the statement with actual values
            ps_pb_intro = ps_pb_statement.format(
                ps_ratio_fmt=ps_ratio_fmt,
                pb_ratio_fmt=pb_ratio_fmt,
                analysis_phrase=analysis_phrase,
                implication_phrase=implication_phrase
            )
            
            # Enhanced market-standard assessment
            causation_word2 = get_variation(content_library, 'valuation_metrics.transition_words.causation', 
                ['therefore'])
            
            # Market-standard P/S categorization
            if ps_ratio_raw and ps_ratio_raw < 2:
                ps_assessment = "conservative Price/Sales positioning that may indicate value opportunities or revenue quality considerations"
            elif ps_ratio_raw and ps_ratio_raw > 5:
                ps_assessment = "premium Price/Sales valuation that suggests high growth expectations or market leadership positioning"
            else:
                ps_assessment = "moderate Price/Sales metrics that reflect balanced market expectations and operational stability"
            
            # Market-standard P/B categorization  
            if pb_ratio_raw and pb_ratio_raw < 1:
                pb_assessment = "trading below book value, potentially indicating undervaluation opportunities or asset quality considerations requiring detailed analysis"
            elif pb_ratio_raw and pb_ratio_raw > 3:
                pb_assessment = "commanding significant book value premium, reflecting strong growth expectations, intangible asset value, or market leadership position"
            else:
                pb_assessment = "maintaining reasonable book value multiples within typical market ranges, suggesting balanced risk-reward characteristics"
            
            investment_context = f"{causation_word2}, this {ps_assessment}, while its {pb_assessment}"
            
            # Strategic positioning context using exact library keys
            continuation_word2 = get_variation(content_library, 'valuation_metrics.transition_words.continuation', 
                ['moreover'])
            
            strategic_context = f"{continuation_word2}, these valuation multiples compared to sector peers provide essential context for assessing the company's competitive positioning, market expectations, and potential investment attractiveness"
            
            paragraph2 = f"{ps_pb_intro} {investment_context}. {strategic_context}."
            html_parts.append(f"<p>{paragraph2}</p>")
        
        # --- Paragraph 3: Market-Standard Enterprise Value Analysis ---
        if has_ev_data:
            # Enhanced EV analysis using exact content library paths
            emphasis_word3 = get_variation(content_library, 'valuation_metrics.transition_words.emphasis', 
                ['critically'])
            intro = get_variation(content_library, 'valuation_metrics.valuation_analysis.introductions', 
                ["The valuation ratios tell an interesting story"])
            
            ev_components = []
            
            # Enhanced EV/Revenue analysis using exact library keys
            if ev_rev_raw is not None:
                ev_rev_statement = get_variation(content_library, 'valuation_metrics.valuation_analysis.enterprise_value_statements',
                    ["The enterprise value to revenue ratio of <strong>{ev_rev_fmt}</strong> {verb} {observation}."])
                verb = get_variation(content_library, 'valuation_metrics.valuation_analysis.verbs', ['indicates'])
                observation = get_variation(content_library, 'valuation_metrics.valuation_analysis.observations',
                    ["reasonable revenue-based valuation"])
                
                ev_rev_formatted = ev_rev_statement.format(
                    ev_rev_fmt=ev_rev_fmt,
                    verb=verb,
                    observation=observation
                )
                ev_components.append(ev_rev_formatted.rstrip('.'))  # Remove period for proper conjunction
            
            # Enhanced EV/EBITDA analysis using exact library keys  
            if ev_ebitda_raw is not None:
                ebitda_statement = get_variation(content_library, 'valuation_metrics.valuation_analysis.ebitda_statements',
                    ["and its {subject} of <strong>{ev_ebitda_fmt}</strong> {verb} {observation}."])
                subject = get_variation(content_library, 'valuation_metrics.valuation_analysis.subjects',
                    ["EV/EBITDA multiple"])
                verb2 = get_variation(content_library, 'valuation_metrics.valuation_analysis.verbs', ['suggests'])
                observation2 = get_variation(content_library, 'valuation_metrics.valuation_analysis.ebitda_observations',
                    ["reasonable earnings-based valuation"])
                
                ebitda_formatted = ebitda_statement.format(
                    subject=subject,
                    ev_ebitda_fmt=ev_ebitda_fmt,
                    verb=verb2,
                    observation=observation2
                )
                ev_components.append(ebitda_formatted.rstrip('.'))  # Remove period for proper conjunction
            
            ev_synthesis = f"{emphasis_word3}, {intro}, as {', '.join(ev_components)}"
            
            # Strategic investment implications
            causation_word3 = get_variation(content_library, 'valuation_metrics.transition_words.causation', 
                ['ultimately'])
            
            investment_implications = f"{causation_word3}, over the investment horizon, these enterprise value metrics provide crucial insights into the company's operational efficiency, capital allocation effectiveness, and relative market positioning within its sector"
            
            # Comprehensive conclusion using exact library keys
            continuation_word3 = get_variation(content_library, 'valuation_metrics.transition_words.continuation', 
                ['additionally'])
            performance_desc3 = get_variation(content_library, 'valuation_metrics.performance_descriptors.positive', 
                ['sophisticated'])
            
            comprehensive_conclusion = f"{continuation_word3}, {performance_desc3} investors should integrate these valuation indicators with fundamental analysis, competitive positioning, industry comparisons, and macroeconomic considerations to develop well-informed investment strategies"
            
            paragraph3 = f"{ev_synthesis}. {investment_implications}. {comprehensive_conclusion}."
            html_parts.append(f"<p>{paragraph3}</p>")
        
        # --- Adaptive Fallback Paragraph for Limited Data ---
        else:
            # Enhanced fallback when EV data or margin data is limited
            emphasis_word_alt = get_variation(content_library, 'valuation_metrics.transition_words.emphasis', 
                ['importantly'])
            performance_desc_alt = get_variation(content_library, 'valuation_metrics.performance_descriptors.neutral', 
                ['thorough'])
            
            # Create adaptive narrative based on available data
            if data_availability_score < 50:
                data_context = "while comprehensive valuation metrics are limited"
                recommendation = "investors should focus on available indicators while seeking additional fundamental and technical data points"
            else:
                data_context = "while certain valuation metrics may be limited"  
                recommendation = "investors should leverage available data points while considering broader market and fundamental factors"
            
            fallback_analysis = f"{emphasis_word_alt}, {data_context}, {performance_desc_alt} valuation assessment requires systematic analysis of available pricing indicators, operational metrics, and competitive positioning"
            
            causation_word_alt = get_variation(content_library, 'valuation_metrics.transition_words.causation', 
                ['consequently'])
            
            strategic_guidance = f"{causation_word_alt}, in the current investment landscape, {recommendation} to develop well-informed investment perspectives"
            
            paragraph_alt = f"{fallback_analysis} {strategic_guidance}."
            html_parts.append(f"<p>{paragraph_alt}</p>")

        # --- 4. Assemble Enhanced Final HTML with Market-Standard Structure ---
        narrative_html = '\n'.join(html_parts)
        full_narrative_html = f'<h3>{section_intro}</h3>\n<div class="narrative">{narrative_html}</div>'

        # Enhanced table generation with content library integration
        combined_data_for_table = {**valuation_data, **total_valuation_data}
        keys_to_exclude = ['Market Cap', 'Enterprise Value', 'Next Earnings Date', 'Ex-Dividend Date']
        filtered_table_data = {k: v for k, v in combined_data_for_table.items() if k not in keys_to_exclude}
        table_html = generate_wordpress_metrics_section_content(filtered_table_data, ticker, content_library)
        
        return full_narrative_html + table_html

    except Exception as e:
        print(f"Warning: Error in enhanced WordPress valuation metrics generation: {e}. Using fallback.")
        import traceback
        traceback.print_exc()
        return hc.generate_valuation_metrics_html(ticker, rdata)

def generate_wordpress_detailed_forecast_table_html(ticker, rdata, content_library=None):
    """
    Enhanced market-standard WordPress-specific detailed forecast table generator.
    Implements comprehensive content library utilization with sophisticated narrative flow.
    """
    try:
        if content_library is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            app_root = os.path.dirname(current_dir)
            content_library = load_content_library(app_root)

        # --- Data Extraction & Initialization ---
        monthly_forecast_table_data = rdata.get('monthly_forecast_table_data', pd.DataFrame())
        current_price = hc._safe_float(rdata.get('current_price'))
        current_price_fmt = hc.format_html_value(current_price, 'currency', ticker=ticker)
        forecast_time_col = rdata.get('time_col', 'Period')
        period_label = rdata.get('period_label', 'Period')
        
        table_rows = ""
        min_price_overall = None
        max_price_overall = None
        range_trend_comment = ""
        section_intro = ""
        enhanced_narrative = ""

        # --- Section Introduction Selection ---
        section_intro = get_variation(content_library, 'forecast_table.section_introductions',
            ['Detailed Forecast Analysis'])

        # --- Data Processing & Analysis ---
        if isinstance(monthly_forecast_table_data, pd.DataFrame) and \
           not monthly_forecast_table_data.empty and \
           'Low' in monthly_forecast_table_data.columns and \
           'High' in monthly_forecast_table_data.columns:

            forecast_df = monthly_forecast_table_data.copy()
            
            # Data cleaning and preparation
            if forecast_time_col in forecast_df.columns:
                forecast_df[forecast_time_col] = forecast_df[forecast_time_col].astype(str)

            forecast_df['Low'] = pd.to_numeric(forecast_df['Low'], errors='coerce')
            forecast_df['High'] = pd.to_numeric(forecast_df['High'], errors='coerce')
            forecast_df.dropna(subset=['Low', 'High'], inplace=True)

            if not forecast_df.empty:
                min_price_overall = forecast_df['Low'].min()
                max_price_overall = forecast_df['High'].max()

                # --- Market-Standard Range Analysis ---
                forecast_df['RangeWidth'] = forecast_df['High'] - forecast_df['Low']
                first_range_width = forecast_df['RangeWidth'].iloc[0]
                last_range_width = forecast_df['RangeWidth'].iloc[-1]

                # Calculate average ROI across periods for performance assessment
                if 'Average' not in forecast_df.columns:
                    forecast_df['Average'] = (forecast_df['Low'] + forecast_df['High']) / 2
                else:
                    forecast_df['Average'] = pd.to_numeric(forecast_df['Average'], errors='coerce')
                forecast_df.dropna(subset=['Average'], inplace=True)

                # Calculate ROI metrics
                if current_price is not None and current_price > 0:
                    forecast_df['Potential ROI'] = ((forecast_df['Average'] - current_price) / current_price) * 100
                    avg_roi = forecast_df['Potential ROI'].mean()
                else:
                    forecast_df['Potential ROI'] = np.nan
                    avg_roi = 0

                # --- Enhanced Range Trend Analysis with Performance Descriptors ---
                first_row = forecast_df.iloc[0]
                last_row = forecast_df.iloc[-1]
                first_range_str = f"{hc.format_html_value(first_row['Low'], 'currency', ticker=ticker)} – {hc.format_html_value(first_row['High'], 'currency', ticker=ticker)}"
                last_range_str = f"{hc.format_html_value(last_row['Low'], 'currency', ticker=ticker)} – {hc.format_html_value(last_row['High'], 'currency', ticker=ticker)}"

                width_change_ratio = last_range_width / first_range_width if first_range_width and first_range_width != 0 else 1

                # Select performance descriptor based on forecast data
                performance_category = 'positive' if avg_roi > 5 else ('negative' if avg_roi < -5 else 'neutral')
                performance_descriptor = get_variation(content_library, 
                    f'forecast_table.performance_descriptors.{performance_category}',
                    ['substantial'])

                # Enhanced range trend analysis with transition words
                transition_word = get_variation(content_library, 'forecast_table.transition_words.emphasis',
                    ['notably'])

                if width_change_ratio > 1.2:
                    range_trend_comment = get_variation(content_library, 'forecast_table.range_trend_comments.widening',
                        ['Note the significant widening in the projected price range (from {first_range_str} to {last_range_str}), suggesting increasing forecast uncertainty over time.'])
                    trend_descriptor = 'expanding'
                elif width_change_ratio < 0.8:
                    range_trend_comment = get_variation(content_library, 'forecast_table.range_trend_comments.narrowing',
                        ['Observe the narrowing projected price range (from {first_range_str} to {last_range_str}), indicating potentially stabilizing expectations or higher model confidence further out.'])
                    trend_descriptor = 'contracting'
                else:
                    range_trend_comment = get_variation(content_library, 'forecast_table.range_trend_comments.stable',
                        ['The projected price range remains relatively consistent (from {first_range_str} to {last_range_str}), implying stable forecast uncertainty.'])
                    trend_descriptor = 'stable'

                range_trend_comment = range_trend_comment.format(
                    first_range_str=first_range_str, 
                    last_range_str=last_range_str
                )

                # --- Enhanced Action Signal Generation ---
                roi_threshold_buy = 2.5
                roi_threshold_short = -2.5
                forecast_df['Action'] = np.select(
                    [forecast_df['Potential ROI'] > roi_threshold_buy, 
                     forecast_df['Potential ROI'] < roi_threshold_short],
                    ['Consider Buy', 'Consider Short'], 
                    default='Hold/Neutral'
                )
                forecast_df.loc[forecast_df['Potential ROI'].isna(), 'Action'] = 'N/A'

                # --- Dynamic Table Header Generation ---
                period_header = get_variation(content_library, 'forecast_table.table_headers.period',
                    ['Period ({time_col})'])
                min_price_header = get_variation(content_library, 'forecast_table.table_headers.min_price',
                    ['Min. Price'])
                avg_price_header = get_variation(content_library, 'forecast_table.table_headers.avg_price',
                    ['Avg. Price'])
                max_price_header = get_variation(content_library, 'forecast_table.table_headers.max_price',
                    ['Max. Price'])
                roi_header = get_variation(content_library, 'forecast_table.table_headers.roi',
                    ['Potential ROI vs Current ({current_price_fmt})'])
                signal_header = get_variation(content_library, 'forecast_table.table_headers.signal',
                    ['Model Signal'])

                # Format headers with proper substitutions
                period_header = period_header.format(time_col=forecast_time_col)
                roi_header = roi_header.format(current_price_fmt=current_price_fmt)

                # --- Table Row Generation ---
                required_cols = [forecast_time_col, 'Low', 'Average', 'High', 'Potential ROI', 'Action']
                if all(col in forecast_df.columns for col in required_cols):
                    for _, row in forecast_df.iterrows():
                        action_class = str(row.get('Action', 'N/A')).lower().split(" ")[-1].split("/")[0]
                        roi_val = row.get('Potential ROI', np.nan)
                        roi_icon = hc.get_icon('neutral')
                        roi_fmt = "N/A"
                        
                        if not pd.isna(roi_val):
                            roi_icon = hc.get_icon('up' if roi_val > 1 else ('down' if roi_val < -1 else 'neutral'))
                            roi_fmt = hc.format_html_value(roi_val, 'percent_direct', 1)

                        low_fmt = hc.format_html_value(row.get('Low'), 'currency', ticker=ticker)
                        avg_fmt = hc.format_html_value(row.get('Average'), 'currency', ticker=ticker)
                        high_fmt = hc.format_html_value(row.get('High'), 'currency', ticker=ticker)
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

                # --- Enhanced Min/Max Summary Generation ---
                first_period = forecast_df[forecast_time_col].iloc[0] if not forecast_df.empty else 'N/A'
                last_period = forecast_df[forecast_time_col].iloc[-1] if not forecast_df.empty else 'N/A'
                min_price_fmt = hc.format_html_value(min_price_overall, 'currency', ticker=ticker)
                max_price_fmt = hc.format_html_value(max_price_overall, 'currency', ticker=ticker)

                min_max_summary = get_variation(content_library, 'forecast_table.min_max_summaries',
                    ["Over the forecast horizon ({first_period} to {last_period}), {ticker}'s price is projected by the model to fluctuate between approximately <strong>{min_price_fmt}</strong> and <strong>{max_price_fmt}</strong>."])
                min_max_summary = min_max_summary.format(
                    first_period=first_period, 
                    last_period=last_period,
                    ticker=ticker, 
                    min_price_fmt=min_price_fmt, 
                    max_price_fmt=max_price_fmt
                )

                # --- Enhanced Narrative with Contextual Analysis ---
                continuity_word = get_variation(content_library, 'forecast_table.transition_words.continuation',
                    ['furthermore'])
                
                enhanced_narrative = f"<p>{transition_word.capitalize()}, the forecast exhibits {performance_descriptor} {trend_descriptor} characteristics. {continuity_word.capitalize()}, this {trend_descriptor} pattern provides valuable insights into the model's confidence levels across the projection timeline.</p>"

                table_html = f"""<div class="table-container"><table><thead><tr><th>{period_header}</th><th>{min_price_header}</th><th>{avg_price_header}</th><th>{max_price_header}</th><th>{roi_header}</th><th>{signal_header}</th></tr></thead><tbody>{table_rows}</tbody></table></div>"""
            else:
                min_max_summary = f"<p>Insufficient forecast data available for {ticker} analysis.</p>"
                table_html = ""
                range_trend_comment = ""
                enhanced_narrative = ""
        else:
            min_max_summary = f"<p>No detailed {period_label.lower()}-by-{period_label.lower()} forecast data is currently available for {ticker}.</p>"
            table_html = ""
            range_trend_comment = ""
            enhanced_narrative = ""

        # --- Dynamic Narrative Introduction Generation ---
        min_fmt = hc.format_html_value(min_price_overall, 'currency', ticker=ticker)
        max_fmt = hc.format_html_value(max_price_overall, 'currency', ticker=ticker)
        range_narrative = f"{min_fmt} to {max_fmt}" if min_price_overall is not None else "an undetermined range"

        # Determine period type with enhanced detection
        period_type = 'monthly' if any(term in period_label.lower() for term in ['month', 'monthly']) else 'quarterly'
        
        narrative_intro = get_variation(content_library, f'forecast_table.narrative_introductions.{period_type}',
            [f"The detailed {period_label.lower()} forecast below outlines the model's expectations for {ticker}'s price evolution ({range_narrative}). It includes projected ranges (Min, Avg, Max), potential ROI based on the average projection versus the current price, and a derived model signal for each period."])
        narrative_intro = narrative_intro.format(ticker=ticker, range_narrative=range_narrative)

        # --- Enhanced Disclaimer with Market Context ---
        disclaimer_forecast = get_variation(content_library, 'forecast_table.disclaimers',
            ["Forecasts are model-based estimates, inherently uncertain, and subject to change based on evolving data and market conditions. They do not guarantee future prices."])

        # --- Final HTML Assembly with Enhanced Structure ---
        return f"""
            <div class="forecast-analysis-section">
                <h3>{section_intro}</h3>
                <div class="narrative">
                    <p>{narrative_intro}</p>
                    {min_max_summary}
                    <p>{range_trend_comment}</p>
                    {enhanced_narrative}
                </div>
                {table_html}
                <div class="forecast-disclaimer">
                    <p class="disclaimer"><strong>Important:</strong> {disclaimer_forecast}</p>
                </div>
            </div>
            """
    except Exception as e:
        logging.error(f"Error in WordPress forecast table generation: {e}")
        print(f"Warning: Error in WordPress forecast table generation: {e}. Using fallback.")
        return hc.generate_detailed_forecast_table_html(ticker, rdata)

def generate_wordpress_financial_health_html(ticker, rdata, content_library=None):
    """
    Enhanced WordPress-specific financial health section using market-standard algorithms
    and comprehensive content library integration with exact key paths.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_financial_health_html(ticker, rdata)

        # --- 1. Comprehensive Data Extraction & Market-Standard Parsing ---
        profile_data = rdata.get('profile_data', {})
        health_data = rdata.get('financial_health_data', {})
        
        if not isinstance(health_data, dict) or not health_data:
            return hc._generate_error_html("Financial Health", "No financial health data available.")

        company_name = profile_data.get('Company Name', ticker)

        def _parse_financial_value(value_str):
            """Enhanced parser for financial health metrics including currency, percentages, and ratios."""
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
            elif cleaned_str.endswith('X'):
                cleaned_str = cleaned_str[:-1]

            try:
                return float(cleaned_str) * multiplier
            except (ValueError, TypeError):
                return None

        # Core financial health metrics extraction
        debt_equity_raw = _parse_financial_value(health_data.get('Debt/Equity (MRQ)'))
        op_cash_flow_raw = _parse_financial_value(health_data.get('Operating Cash Flow (TTM)'))
        roe_raw = _parse_financial_value(health_data.get('Return on Equity (ROE TTM)'))
        roa_raw = _parse_financial_value(health_data.get('Return on Assets (ROA TTM)'))
        current_ratio_raw = _parse_financial_value(health_data.get('Current Ratio (MRQ)'))
        quick_ratio_raw = _parse_financial_value(health_data.get('Quick Ratio (MRQ)'))
        total_debt_raw = _parse_financial_value(health_data.get('Total Debt (MRQ)'))
        total_cash_raw = _parse_financial_value(health_data.get('Total Cash (MRQ)'))
        levered_fcf_raw = _parse_financial_value(health_data.get('Levered Free Cash Flow (TTM)'))

        # Format values for display using exact data
        debt_equity_fmt = health_data.get('Debt/Equity (MRQ)', 'N/A')
        op_cash_flow_fmt = health_data.get('Operating Cash Flow (TTM)', 'N/A')
        roe_fmt = health_data.get('Return on Equity (ROE TTM)', 'N/A')
        roa_fmt = health_data.get('Return on Assets (ROA TTM)', 'N/A')
        current_ratio_fmt = health_data.get('Current Ratio (MRQ)', 'N/A')
        quick_ratio_fmt = health_data.get('Quick Ratio (MRQ)', 'N/A')
        total_debt_fmt = health_data.get('Total Debt (MRQ)', 'N/A')
        total_cash_fmt = health_data.get('Total Cash (MRQ)', 'N/A')

        # --- 2. Market-Standard Financial Health Scoring Algorithm ---
        
        # Leverage Assessment (25% weight)
        leverage_score = 0
        leverage_category = "moderate_leverage"
        if debt_equity_raw is not None:
            if debt_equity_raw < 0.25:
                leverage_score = 25; leverage_category = "low_leverage"
            elif debt_equity_raw < 0.5:
                leverage_score = 20; leverage_category = "low_leverage"
            elif debt_equity_raw < 1.0:
                leverage_score = 15; leverage_category = "moderate_leverage"
            elif debt_equity_raw < 2.0:
                leverage_score = 10; leverage_category = "moderate_leverage"
            elif debt_equity_raw < 3.0:
                leverage_score = 5; leverage_category = "high_leverage"
            else:
                leverage_score = 0; leverage_category = "high_leverage"
        
        # Liquidity Assessment (25% weight)
        liquidity_score = 0
        if current_ratio_raw is not None:
            if current_ratio_raw >= 2.0:
                liquidity_score += 15
            elif current_ratio_raw >= 1.5:
                liquidity_score += 12
            elif current_ratio_raw >= 1.2:
                liquidity_score += 8
            elif current_ratio_raw >= 1.0:
                liquidity_score += 5
            else:
                liquidity_score += 0
        
        if quick_ratio_raw is not None:
            if quick_ratio_raw >= 1.5:
                liquidity_score += 10
            elif quick_ratio_raw >= 1.0:
                liquidity_score += 8
            elif quick_ratio_raw >= 0.8:
                liquidity_score += 5
            else:
                liquidity_score += 2
        
        # Cash Flow Quality Assessment (25% weight)
        cash_flow_score = 0
        cash_flow_category = "positive_cash_flow"
        if op_cash_flow_raw is not None:
            if op_cash_flow_raw > 0:
                cash_flow_category = "positive_cash_flow"
                if op_cash_flow_raw >= 1e9:  # $1B+
                    cash_flow_score = 25
                elif op_cash_flow_raw >= 1e8:  # $100M+
                    cash_flow_score = 20
                elif op_cash_flow_raw >= 1e7:  # $10M+
                    cash_flow_score = 15
                else:
                    cash_flow_score = 10
            else:
                cash_flow_category = "negative_cash_flow"
                cash_flow_score = 0
        
        # Profitability Assessment (25% weight)
        profitability_score = 0
        roe_category = "moderate_roe"
        if roe_raw is not None:
            if roe_raw >= 25:
                profitability_score = 25; roe_category = "high_roe"
            elif roe_raw >= 20:
                profitability_score = 22; roe_category = "high_roe"
            elif roe_raw >= 15:
                profitability_score = 18; roe_category = "high_roe"
            elif roe_raw >= 10:
                profitability_score = 15; roe_category = "moderate_roe"
            elif roe_raw >= 5:
                profitability_score = 10; roe_category = "moderate_roe"
            elif roe_raw > 0:
                profitability_score = 5; roe_category = "low_roe"
            else:
                profitability_score = 0; roe_category = "low_roe"
        
        # Overall Financial Health Score (0-100)
        overall_health_score = leverage_score + liquidity_score + cash_flow_score + profitability_score
        
        # Determine overall financial strength category
        if overall_health_score >= 80:
            strength_category = "strong"
        elif overall_health_score >= 60:
            strength_category = "moderate"
        else:
            strength_category = "weak"
        
        # Data availability assessment
        data_availability_score = sum([
            1 for val in [debt_equity_raw, op_cash_flow_raw, roe_raw, current_ratio_raw, quick_ratio_raw]
            if val is not None
        ]) / 5.0 * 100
        
        # --- 3. Enhanced Dynamic Narrative Generation with Exact Library Keys ---
        
        # Section introduction using exact key path
        section_intro = get_variation(content_library, 'financial_health.section_introductions',
            ['Financial Health Overview'])
        
        html_parts = []
        
        # --- Paragraph 1: Comprehensive Leverage and Capital Structure Analysis (4 sentences) ---
        emphasis_word = get_variation(content_library, 'financial_health.transition_words.emphasis', ['significantly'])
        strength_assessment = get_variation(content_library, f'financial_health.strength_assessments.{strength_category}',
            [f'demonstrates {strength_category} financial health'])
        
        # Enhanced leverage analysis with risk context
        leverage_analysis = get_variation(content_library, f'financial_health.leverage_analysis.{leverage_category}',
            [f'maintains {leverage_category} with a debt-to-equity ratio of {debt_equity_fmt}']).format(debt_equity_fmt=debt_equity_fmt)
        
        # Capital structure assessment
        financial_intro = f"{emphasis_word.capitalize()}, {company_name} {strength_assessment}, characterized by {leverage_analysis}"
        
        # Interest coverage and debt sustainability
        causation_word = get_variation(content_library, 'financial_health.transition_words.causation', ['consequently'])
        liquidity_context = ""
        if current_ratio_raw is not None and current_ratio_raw >= 1.5:
            liquidity_context = "with strong liquidity buffers supporting debt obligations"
        elif current_ratio_raw is not None and current_ratio_raw < 1.0:
            liquidity_context = "requiring careful working capital management to meet obligations"
        else:
            liquidity_context = "with standard liquidity positioning"
        
        debt_sustainability = f"{causation_word}, this capital structure {liquidity_context} provides insight into financial sustainability and credit quality"
        
        # Industry context and competitive positioning
        continuation_word = get_variation(content_library, 'financial_health.transition_words.continuation', ['furthermore'])
        comparative_phrase = get_variation(content_library, 'contextual_phrases.comparative', ['relative to industry benchmarks'])
        
        industry_context = f"{continuation_word}, {comparative_phrase}, this leverage profile influences strategic flexibility and competitive positioning in market cycles"
        
        # Financial flexibility assessment
        contrast_word = get_variation(content_library, 'financial_health.transition_words.contrast', ['however'])
        temporal_phrase = get_variation(content_library, 'contextual_phrases.temporal', ['in current market conditions'])
        
        flexibility_assessment = f"{contrast_word}, {temporal_phrase}, comprehensive evaluation requires analysis of credit facilities, covenant compliance, and refinancing schedules"
        
        paragraph1 = f"{financial_intro}. {debt_sustainability}. {industry_context}. {flexibility_assessment}."
        html_parts.append(f"<p>{paragraph1}</p>")
        
        # --- Paragraph 2: Cash Flow Quality and Operational Efficiency Analysis (4 sentences) ---
        transitional_word = get_variation(content_library, 'financial_health.transition_words.transitional', ['examining'])
        cash_flow_analysis = get_variation(content_library, f'financial_health.cash_flow_analysis.{cash_flow_category}',
            [f'reports {cash_flow_category} of {op_cash_flow_fmt}']).format(op_cash_flow_fmt=op_cash_flow_fmt)
        
        # Cash flow quality introduction
        cash_flow_intro = f"{transitional_word.capitalize()} operational cash generation, {company_name} {cash_flow_analysis}, providing fundamental insight into business model sustainability"
        
        # Cash conversion and working capital efficiency
        analytical_word = get_variation(content_library, 'financial_health.transition_words.analytical', ['specifically'])
        liquidity_assessment = ""
        if current_ratio_raw is not None and quick_ratio_raw is not None:
            if current_ratio_raw >= 2.0 and quick_ratio_raw >= 1.0:
                liquidity_assessment = f"with current ratio of {current_ratio_fmt} and quick ratio of {quick_ratio_fmt}, demonstrating robust short-term liquidity management"
            elif current_ratio_raw < 1.2 or quick_ratio_raw < 0.8:
                liquidity_assessment = f"with current ratio of {current_ratio_fmt} and quick ratio of {quick_ratio_fmt}, indicating potential working capital constraints"
            else:
                liquidity_assessment = f"with current ratio of {current_ratio_fmt} and quick ratio of {quick_ratio_fmt}, reflecting adequate liquidity positioning"
        else:
            liquidity_assessment = f"with liquidity metrics requiring comprehensive working capital analysis"
        
        liquidity_context = f"{analytical_word}, {liquidity_assessment} for operational obligations and growth financing"
        
        # Free cash flow and capital allocation efficiency
        evaluative_word = get_variation(content_library, 'financial_health.transition_words.evaluative', ['additionally'])
        cash_quality_desc = get_variation(content_library, 'financial_health.performance_descriptors.positive', ['strong'])
        
        if op_cash_flow_raw is not None and op_cash_flow_raw > 0:
            fcf_context = f"this positive operating cash flow supports {cash_quality_desc} free cash flow generation and enables strategic capital allocation for shareholder value creation"
        elif op_cash_flow_raw is not None and op_cash_flow_raw < 0:
            fcf_context = f"negative operating cash flow raises concerns about free cash flow sustainability and may require additional financing for operations"
        else:
            fcf_context = f"cash flow analysis requires comprehensive review of operating, investing, and financing activities"
        
        cash_allocation = f"{evaluative_word}, {fcf_context}"
        
        # Cash flow predictability and cycle sensitivity
        conclusive_word = get_variation(content_library, 'financial_health.transition_words.conclusive', ['ultimately'])
        market_phrase = get_variation(content_library, 'contextual_phrases.market', ['during market volatility'])
        
        cash_predictability = f"{conclusive_word}, {market_phrase}, consistent cash flow generation indicates operational resilience and provides foundation for dividend sustainability and debt service coverage"
        
        paragraph2 = f"{cash_flow_intro}. {liquidity_context}. {cash_allocation}. {cash_predictability}."
        html_parts.append(f"<p>{paragraph2}</p>")
        
        # --- Paragraph 3: Profitability and Return Analysis with Investment Implications (4 sentences) ---
        analytical_intro = get_variation(content_library, 'financial_health.transition_words.analytical', ['analyzing'])
        roe_analysis = get_variation(content_library, f'financial_health.roe_analysis.{roe_category}',
            [f'achieves {roe_category} of {roe_fmt}']).format(roe_fmt=roe_fmt)
        
        # ROE and capital efficiency introduction
        profitability_intro = f"{analytical_intro.capitalize()} return on equity metrics, {company_name} {roe_analysis}, reflecting management's effectiveness in generating shareholder returns from invested capital"
        
        # Asset utilization and operational efficiency
        furthermore_word = get_variation(content_library, 'financial_health.transition_words.continuation', ['furthermore'])
        efficiency_context = ""
        if roa_raw is not None:
            if roa_raw >= 10:
                efficiency_context = f"with return on assets of {roa_fmt}, demonstrating superior asset utilization and operational efficiency"
            elif roa_raw >= 5:
                efficiency_context = f"with return on assets of {roa_fmt}, indicating adequate asset productivity and management effectiveness"
            elif roa_raw > 0:
                efficiency_context = f"with return on assets of {roa_fmt}, reflecting moderate asset efficiency requiring operational improvements"
            else:
                efficiency_context = f"with return on assets of {roa_fmt}, highlighting challenges in asset utilization and profit generation"
        else:
            efficiency_context = f"with asset efficiency metrics requiring comprehensive operational analysis"
        
        asset_efficiency = f"{furthermore_word}, {efficiency_context} relative to industry benchmarks"
        
        # Capital structure impact on returns
        importantly_word = get_variation(content_library, 'financial_health.transition_words.importance', ['importantly'])
        leverage_impact = ""
        if debt_equity_raw is not None and roe_raw is not None:
            if debt_equity_raw > 1.0 and roe_raw > 15:
                leverage_impact = f"the {debt_equity_fmt} debt-to-equity ratio amplifies returns through financial leverage, though this strategy increases financial risk during economic downturns"
            elif debt_equity_raw < 0.5:
                leverage_impact = f"the conservative {debt_equity_fmt} debt-to-equity ratio suggests potential for return enhancement through strategic leverage optimization"
            else:
                leverage_impact = f"the {debt_equity_fmt} debt-to-equity ratio provides balanced capital structure supporting sustainable return generation"
        else:
            leverage_impact = f"comprehensive return analysis requires evaluation of capital structure optimization opportunities"
        
        return_sustainability = f"{importantly_word}, {leverage_impact}"
        
        # Investment thesis and forward-looking assessment
        conclusion_word = get_variation(content_library, 'financial_health.transition_words.conclusive', ['consequently'])
        
        # Get conclusion template from content library
        conclusion_template = get_variation(content_library, 'financial_health.conclusion_statements',
            ['On balance, {company_name} {strength_summary}, {leverage_summary}, {cash_flow_summary}, and {roe_summary}'])
        
        # Format the conclusion with actual values
        try:
            # Map variable names: template expects _summary but we have _assessment and _analysis
            conclusion_statement = conclusion_template.format(
                company_name=company_name,
                strength_summary=strength_assessment,
                leverage_summary=leverage_analysis, 
                cash_flow_summary=cash_flow_analysis,
                roe_summary=roe_analysis
            )
        except (KeyError, AttributeError) as e:
            # If formatting fails, use a simple default
            conclusion_statement = f"provides valuable insight for investment decisions"
        
        investment_context = f"{conclusion_word}, this financial health profile {conclusion_statement}, requiring continuous monitoring of leverage trends, cash flow sustainability, and return consistency for comprehensive investment thesis evaluation"
        
        paragraph3 = f"{profitability_intro}. {asset_efficiency}. {return_sustainability}. {investment_context}."
        html_parts.append(f"<p>{paragraph3}</p>")
        
        # --- 4. Enhanced HTML Assembly with Professional Formatting ---
        html_content = f"""
<div class="financial-health-section">
    <h3>Financial Health Analysis</h3>
    <div class="financial-health-intro">
        <p>{section_intro.format(company_name=company_name)}</p>
    </div>
    <div class="financial-health-content">
        {"".join(html_parts)}
    </div>
    <div class="financial-health-metrics">
        <div class="metrics-grid">
            <div class="metric-item">
                <span class="metric-label">Debt-to-Equity Ratio:</span>
                <span class="metric-value">{debt_equity_fmt}</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">Operating Cash Flow (TTM):</span>
                <span class="metric-value">{op_cash_flow_fmt}</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">Return on Equity (TTM):</span>
                <span class="metric-value">{roe_fmt}</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">Current Ratio:</span>
                <span class="metric-value">{current_ratio_fmt}</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">Quick Ratio:</span>
                <span class="metric-value">{quick_ratio_fmt}</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">Financial Health Score:</span>
                <span class="metric-value score-{strength_category}">{overall_health_score:.0f}/100</span>
            </div>
        </div>
    </div>
</div>
"""
        
        return html_content.strip()

    except Exception as e:
        error_msg = f"Error generating WordPress financial health content: {str(e)}"
        print(error_msg)
        return hc._generate_error_html("Financial Health", error_msg)
        html_parts.append(f"<p>{paragraph2}</p>")
        
        # --- Paragraph 3: Comprehensive ROE Analysis and Strategic Financial Positioning (4 sentences) ---
        
        # Enhanced ROE analysis with profitability context
        emphasis_word3 = get_variation(content_library, 'financial_health.transition_words.emphasis', ['fundamentally'])
        
        roe_key = "moderate_roe"
        roe_strategic_context = ""
        if roe is not None:
            if roe > 25:
                roe_key = "high_roe"
                roe_strategic_context = "indicating exceptional capital efficiency and potentially sustainable competitive advantages"
            elif roe > 15:
                roe_key = "high_roe"
                roe_strategic_context = "reflecting solid capital efficiency and effective management execution"
            elif roe > 8:
                roe_key = "moderate_roe"
                roe_strategic_context = "demonstrating reasonable capital efficiency within industry norms"
            elif roe > 0:
                roe_key = "low_roe"
                roe_strategic_context = "suggesting potential operational challenges or capital allocation inefficiencies"
            else:
                roe_key = "low_roe"
                roe_strategic_context = "indicating concerning profitability issues requiring strategic intervention"
        else:
            roe_strategic_context = "with profitability assessment limited by available data"
        
        roe_analysis = get_variation(content_library, f'financial_health.roe_analysis.{roe_key}',
            [f'delivers excellent return on equity of {roe_fmt}']).format(roe_fmt=roe_fmt)
        
        roe_intro = f"{emphasis_word3}, {company_name} {roe_analysis}, {roe_strategic_context}"
        
        # ROE decomposition and quality analysis
        causation_word3 = get_variation(content_library, 'financial_health.transition_words.causation', ['accordingly'])
        performance_desc3 = get_variation(content_library, 'financial_health.performance_descriptors.positive', ['sophisticated'])
        
        # ROE sustainability and business model strength
        if roe is not None:
            if roe > 15:
                roe_sustainability = f"this {performance_desc3} return level suggests strong competitive positioning, effective capital allocation, and potential for sustained value creation"
            elif roe < 5:
                roe_sustainability = f"this modest return profile indicates potential need for operational improvements, asset optimization, or strategic repositioning"
            else:
                roe_sustainability = f"this moderate return level reflects {performance_desc3} but not exceptional capital efficiency, requiring evaluation of improvement opportunities"
        else:
            roe_sustainability = f"comprehensive ROE assessment requires additional profitability and capital efficiency metrics"
        
        sustainability_analysis = f"{causation_word3}, {roe_sustainability}"
        
        # Financial health synthesis and investment implications
        continuation_word3 = get_variation(content_library, 'financial_health.transition_words.continuation', ['ultimately'])
        comparative_phrase3 = get_variation(content_library, 'contextual_phrases.comparative', ['relative to sector standards'])
        
        # Comprehensive financial health synthesis
        health_synthesis = f"{continuation_word3}, {comparative_phrase3}, these financial health indicators collectively assess the company's ability to generate returns, manage risk, and fund strategic growth initiatives"
        
        # Investment decision context and risk assessment
        contrast_word3 = get_variation(content_library, 'financial_health.transition_words.contrast', ['however'])
        temporal_phrase3 = get_variation(content_library, 'contextual_phrases.temporal', ['in the evolving market environment'])
        
        # Get conclusion template - check if it has placeholders or is already formatted
        conclusion_template = get_variation(content_library, 'financial_health.conclusion_statements',
            [f'On balance, {{company_name}} {{strength_summary}}, {{leverage_summary}}, {{cash_flow_summary}}, and {{roe_summary}}'])
        
        print(f"DEBUG: conclusion_template = '{conclusion_template}'")
        print(f"DEBUG: strength_assessment = '{strength_assessment}'")
        print(f"DEBUG: leverage_analysis = '{leverage_analysis}'")
        print(f"DEBUG: cash_flow_analysis = '{cash_flow_analysis}'")
        print(f"DEBUG: roe_analysis = '{roe_analysis}'")
        
        # Only format if the template actually has placeholders
        if '{' in conclusion_template and '}' in conclusion_template:
            try:
                conclusion = conclusion_template.format(
                    company_name=company_name,
                    strength_summary=strength_assessment,  # NOTE: template uses _summary but variable is _assessment
                    leverage_summary=leverage_analysis,     # NOTE: template uses _summary but variable is _analysis
                    cash_flow_summary=cash_flow_analysis,   # NOTE: template uses _summary but variable is _analysis
                    roe_summary=roe_analysis                # NOTE: template uses _summary but variable is _analysis
                )
                print(f"DEBUG: conclusion after format = '{conclusion}'")
            except KeyError as e:
                # If template has different placeholders, use a simple default
                print(f"Warning: Template placeholder mismatch: {e}. Using default.")
                conclusion = f"On balance, {company_name} demonstrates solid financial health that supports sustainable operations"
            except Exception as e:
                print(f"Warning: Unexpected error formatting conclusion: {e}. Using default.")
                conclusion = f"On balance, {company_name} demonstrates solid financial health that supports sustainable operations"
        else:
            # Template is already formatted, use as-is
            conclusion = conclusion_template
            print(f"DEBUG: Using template as-is (no placeholders): '{conclusion}'")
        
        investment_context = f"{contrast_word3}, {temporal_phrase3}, {conclusion.lower()}, requiring ongoing monitoring of leverage trends, cash flow consistency, and profitability sustainability"
        
        paragraph3 = f"{roe_intro}. {sustainability_analysis}. {health_synthesis}. {investment_context}."
        html_parts.append(f"<p>{paragraph3}</p>")

        # --- 3. Assemble Enhanced Final HTML ---
        narrative_html = '\n'.join(html_parts)
        full_html = f"<h3>{section_intro}</h3>\n<div class='narrative'>{narrative_html}</div>"

        # Use WordPress version of metrics table
        table_content = generate_wordpress_metrics_section_content(health_data, ticker, content_library)

        return full_html + table_content

    except Exception as e:
        print(f"Warning: Error in WordPress financial health generation: {e}. Using fallback.")
        return hc.generate_financial_health_html(ticker, rdata)

def generate_wordpress_financial_efficiency_html(ticker, rdata, content_library=None):
    """
    Generate WordPress financial efficiency content using market-standard algorithms
    and proper content library variations for enhanced narrative generation.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_financial_efficiency_html(ticker, rdata)

        # --- 1. Enhanced Data Extraction ---
        profile_data = rdata.get('profile_data', {})
        efficiency_data = rdata.get('financial_efficiency_data', {})

        company_name = profile_data.get('Company Name', ticker)

        # Extract comprehensive financial efficiency metrics
        gross_margin = hc._safe_float(efficiency_data.get('Gross Margin (TTM)'))
        op_margin = hc._safe_float(efficiency_data.get('Operating Margin (TTM)'))
        net_margin = hc._safe_float(efficiency_data.get('Net Margin (TTM)'))
        asset_turnover = hc._safe_float(efficiency_data.get('Asset Turnover (TTM)'))
        
        # Additional efficiency metrics for comprehensive analysis
        inventory_turnover = hc._safe_float(efficiency_data.get('Inventory Turnover (TTM)'))
        receivables_turnover = hc._safe_float(efficiency_data.get('Receivables Turnover (TTM)'))
        working_capital_turnover = hc._safe_float(efficiency_data.get('Working Capital Turnover (TTM)'))
        roic = hc._safe_float(efficiency_data.get('Return on Invested Capital (ROIC TTM)'))

        # Format values for display
        gross_margin_fmt = hc.format_html_value(gross_margin, 'percent_direct', ticker=ticker)
        op_margin_fmt = hc.format_html_value(op_margin, 'percent_direct', ticker=ticker)
        net_margin_fmt = hc.format_html_value(net_margin, 'percent_direct', ticker=ticker)
        asset_turnover_fmt = hc.format_html_value(asset_turnover, 'ratio', ticker=ticker)

        # --- 2. Market-Standard Categorization Logic ---

        # Industry-standard margin thresholds for comprehensive analysis
        gross_margin_key = "moderate_margin"
        if gross_margin is not None:
            if gross_margin >= 0.50:  # 50%+ excellent
                gross_margin_key = "high_margin"
            elif gross_margin <= 0.25:  # 25%- constrained
                gross_margin_key = "low_margin"

        op_margin_key = "moderate_margin"
        if op_margin is not None:
            if op_margin >= 0.20:  # 20%+ strong operational control
                op_margin_key = "high_margin"
            elif op_margin <= 0.08:  # 8%- operational challenges
                op_margin_key = "low_margin"

        net_margin_key = "moderate_margin"
        if net_margin is not None:
            if net_margin >= 0.15:  # 15%+ excellent bottom-line efficiency
                net_margin_key = "high_margin"
            elif net_margin <= 0.05:  # 5%- profitability concerns
                net_margin_key = "low_margin"

        # Asset turnover analysis with industry benchmarks
        turnover_key = "moderate_turnover"
        if asset_turnover is not None:
            if asset_turnover >= 1.8:  # High efficiency threshold
                turnover_key = "high_turnover"
            elif asset_turnover <= 0.6:  # Low efficiency threshold
                turnover_key = "low_turnover"

        # Comprehensive efficiency assessment using multiple metrics
        efficiency_key = "moderate_efficiency"
        efficiency_score = 0
        metric_count = 0
        
        if gross_margin is not None:
            efficiency_score += (1 if gross_margin >= 0.50 else 0.5 if gross_margin >= 0.25 else 0)
            metric_count += 1
        if op_margin is not None:
            efficiency_score += (1 if op_margin >= 0.20 else 0.5 if op_margin >= 0.08 else 0)
            metric_count += 1
        if net_margin is not None:
            efficiency_score += (1 if net_margin >= 0.15 else 0.5 if net_margin >= 0.05 else 0)
            metric_count += 1
        if asset_turnover is not None:
            efficiency_score += (1 if asset_turnover >= 1.8 else 0.5 if asset_turnover >= 0.6 else 0)
            metric_count += 1
        
        if metric_count > 0:
            avg_efficiency = efficiency_score / metric_count
            if avg_efficiency >= 0.75:
                efficiency_key = "strong_efficiency"
            elif avg_efficiency <= 0.35:
                efficiency_key = "weak_efficiency"

        # --- 3. Content Library Variations Extraction ---

        # Get section introduction
        section_intro = get_variation(content_library, 'financial_efficiency.section_introductions',
            ['Financial Efficiency Analysis'])

        # Extract margin analysis variations - ONLY if data exists
        if gross_margin is not None:
            gross_margin_analysis = get_variation(content_library, f'financial_efficiency.margin_analysis.gross_margin.{gross_margin_key}',
                [f'achieves reasonable gross margin of <strong>{gross_margin_fmt}</strong>']).format(gross_margin_fmt=gross_margin_fmt)
        else:
            gross_margin_analysis = None

        if op_margin is not None:
            op_margin_analysis = get_variation(content_library, f'financial_efficiency.margin_analysis.operating_margin.{op_margin_key}',
                [f'maintains reasonable operating margin of <strong>{op_margin_fmt}</strong>']).format(op_margin_fmt=op_margin_fmt)
        else:
            op_margin_analysis = None

        if net_margin is not None:
            net_margin_analysis = get_variation(content_library, f'financial_efficiency.margin_analysis.net_margin.{net_margin_key}',
                [f'delivers reasonable net margin of <strong>{net_margin_fmt}</strong>']).format(net_margin_fmt=net_margin_fmt)
        else:
            net_margin_analysis = None

        # Asset turnover analysis
        asset_turnover_analysis = get_variation(content_library, f'financial_efficiency.asset_turnover_analysis.{turnover_key}',
            [f'maintains reasonable asset utilization'])

        # Overall efficiency assessment
        efficiency_assessment = get_variation(content_library, f'financial_efficiency.efficiency_assessment.{efficiency_key}',
            [f'demonstrates reasonable operational efficiency'])

        # Transition words for natural flow
        transition_emphasis = get_variation(content_library, 'financial_efficiency.transition_words.emphasis', ['Importantly'])
        transition_continuation = get_variation(content_library, 'financial_efficiency.transition_words.continuation', ['Furthermore'])
        transition_contrast = get_variation(content_library, 'financial_efficiency.transition_words.contrast', ['However'])
        transition_causation = get_variation(content_library, 'financial_efficiency.transition_words.causation', ['Consequently'])

        # Performance descriptors for enhanced language
        positive_descriptor = get_variation(content_library, 'financial_efficiency.performance_descriptors.positive', ['robust'])
        neutral_descriptor = get_variation(content_library, 'financial_efficiency.performance_descriptors.neutral', ['solid'])
        
        # Choose appropriate descriptor based on efficiency
        performance_descriptor = positive_descriptor if efficiency_key == "strong_efficiency" else neutral_descriptor

        # --- 4. Enhanced Narrative Generation ---

        # Paragraph 1: Comprehensive Margin Analysis with Market Context - ONLY include available metrics
        paragraph1_parts = []
        paragraph1_parts.append(f"{company_name} {efficiency_assessment} through {performance_descriptor} margin management across operational levels.")
        
        # Only add margin analyses if data exists
        if gross_margin_analysis:
            paragraph1_parts.append(f"At the gross profit level, the company {gross_margin_analysis}, which reflects direct cost control effectiveness and pricing power in its core market segments.")
        
        if op_margin_analysis:
            paragraph1_parts.append(f"{transition_emphasis}, {ticker} {op_margin_analysis}, demonstrating management's ability to control operational expenses while maintaining competitive positioning.")
        
        if net_margin_analysis:
            paragraph1_parts.append(f"When examining bottom-line performance, the organization {net_margin_analysis}, indicating comprehensive profitability management after accounting for all operational, financial, and tax considerations.")
        
        # If no margin data at all, add generic statement
        if not gross_margin_analysis and not op_margin_analysis and not net_margin_analysis:
            paragraph1_parts.append(f"The company maintains focus on operational efficiency and margin management, though detailed margin metrics require further analysis with updated financial disclosures.")

        # Paragraph 2: Asset Utilization and Capital Deployment Strategy
        paragraph2_parts = []
        paragraph2_parts.append(f"{transition_continuation}, {company_name}'s capital deployment strategy reveals critical insights about asset productivity and management's resource allocation effectiveness.")
        
        if asset_turnover is not None:
            paragraph2_parts.append(f"The company {asset_turnover_analysis} with an Asset Turnover of <strong>{asset_turnover_fmt}</strong>, measuring how efficiently management converts invested capital into revenue generation.")
            
            if turnover_key == "high_turnover":
                paragraph2_parts.append(f"This {performance_descriptor} asset utilization indicates management's exceptional ability to maximize revenue from the existing asset base, suggesting efficient operational execution and strategic resource deployment.")
            elif turnover_key == "low_turnover":
                paragraph2_parts.append(f"{transition_contrast}, this asset utilization level suggests potential opportunities for enhanced operational efficiency and capital optimization initiatives.")
            else:
                paragraph2_parts.append(f"This represents a {neutral_descriptor} approach to asset deployment, aligning with industry operational patterns while maintaining opportunities for efficiency improvements.")
        else:
            paragraph2_parts.append(f"Asset turnover metrics indicate the company maintains balanced capital utilization relative to revenue generation capabilities.")
            
        # Add additional context based on other efficiency metrics
        if working_capital_turnover is not None or inventory_turnover is not None:
            paragraph2_parts.append(f"Complementary efficiency indicators provide additional insights into operational effectiveness and working capital management strategies.")

        # Paragraph 3: Strategic Assessment and Investment Implications
        paragraph3_parts = []
        
        # Build conclusion statement with only available metrics
        conclusion_parts = [f"{company_name} {efficiency_assessment}"]
        
        metric_descriptions = []
        if gross_margin_analysis:
            metric_descriptions.append(gross_margin_analysis)
        if op_margin_analysis:
            metric_descriptions.append(op_margin_analysis)
        if net_margin_analysis:
            metric_descriptions.append(net_margin_analysis)
        if asset_turnover_analysis and asset_turnover is not None:
            metric_descriptions.append(asset_turnover_analysis)
        
        if metric_descriptions:
            conclusion_parts.append("through " + ", ".join(metric_descriptions))
        
        conclusion_statement = ". ".join(conclusion_parts) + "."
        
        paragraph3_parts.append(conclusion_statement)
        
        # Strategic implications based on efficiency assessment
        if efficiency_key == "strong_efficiency":
            paragraph3_parts.append(f"{transition_causation}, this combination of {performance_descriptor} margin control and effective asset utilization positions {ticker} favorably for sustained competitive advantage and market leadership.")
            paragraph3_parts.append(f"Investors should recognize that such operational excellence typically translates into consistent cash flow generation, enhanced shareholder returns, and resilience during market volatility.")
        elif efficiency_key == "weak_efficiency":
            paragraph3_parts.append(f"{transition_contrast}, current efficiency metrics suggest room for improvement, though focused operational initiatives could unlock significant value creation opportunities.")
            paragraph3_parts.append(f"Market participants should monitor management's strategic responses to address these efficiency challenges and their potential impact on future profitability trajectories and competitive positioning.")
        else:
            paragraph3_parts.append(f"This balanced efficiency profile suggests steady operational execution while maintaining clear opportunities for margin expansion through strategic optimization initiatives.")
            paragraph3_parts.append(f"For investment consideration, these metrics indicate a {neutral_descriptor} foundation for sustainable business operations with potential upside from enhanced operational efficiency and capital allocation strategies.")

        # --- 5. Assemble Final HTML with Enhanced Structure ---
        html_parts = []

        # Section header
        html_parts.append(f"<h3>{section_intro}</h3>")

        # Enhanced narrative content with comprehensive 3-paragraph structure
        html_parts.append(f"""
        <div class="narrative">
            <p>{' '.join(paragraph1_parts)}</p>
            <p>{' '.join(paragraph2_parts)}</p>
            <p>{' '.join(paragraph3_parts)}</p>
        </div>
        """)

        # Use WordPress version of metrics table
        table_content = generate_wordpress_metrics_section_content(efficiency_data, ticker, content_library)

        return ''.join(html_parts) + table_content

    except Exception as e:
        print(f"Warning: Error in WordPress financial efficiency generation: {e}. Using fallback.")
        return hc.generate_financial_efficiency_html(ticker, rdata)

def generate_wordpress_profitability_growth_html(ticker, rdata, content_library=None):
    """
    Generate WordPress profitability and growth content using content library variations.
    Follows market standard algorithms for comprehensive margin and growth analysis.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_profitability_growth_html(ticker, rdata)

        # --- 1. Data Extraction and Parsing (Following Market Standard Algorithm) ---
        profile_data = rdata.get('profile_data', {})
        profitability_data = rdata.get('profitability_data', {})

        if not isinstance(profitability_data, dict) or not profitability_data:
            return hc._generate_error_html("Profitability & Growth", "No profitability data available.")

        company_name = profile_data.get('Company Name', ticker)

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
                return float(cleaned_str.replace('X','')) * multiplier
            except (ValueError, TypeError):
                return None

        # Parse all necessary raw values for logic (following market standard parsing)
        gross_margin_raw = _parse_value(profitability_data.get('Gross Margin (TTM)'))
        op_margin_raw = _parse_value(profitability_data.get('Operating Margin (TTM)'))
        ebitda_margin_raw = _parse_value(profitability_data.get('EBITDA Margin (TTM)'))
        net_margin_raw = _parse_value(profitability_data.get('Profit Margin (TTM)'))
        rev_growth_raw = _parse_value(profitability_data.get('Quarterly Revenue Growth (YoY)'))
        earnings_growth_raw = _parse_value(profitability_data.get('Earnings Growth (YoY)'))
        
        # Get formatted values for display
        gross_margin_fmt = profitability_data.get('Gross Margin (TTM)', 'N/A')
        op_margin_fmt = profitability_data.get('Operating Margin (TTM)', 'N/A')
        ebitda_margin_fmt = profitability_data.get('EBITDA Margin (TTM)', 'N/A')
        net_margin_fmt = profitability_data.get('Profit Margin (TTM)', 'N/A')
        rev_growth_fmt = profitability_data.get('Quarterly Revenue Growth (YoY)', 'N/A')
        earnings_growth_fmt = profitability_data.get('Earnings Growth (YoY)', 'N/A')
        ebitda_fmt = profitability_data.get('EBITDA (TTM)', 'N/A')
        gross_profit_fmt = profitability_data.get('Gross Profit (TTM)', 'N/A')
        net_income_fmt = profitability_data.get('Net Income (TTM)', 'N/A')

        # --- 2. Content Library-Based Analysis (Market Standard Categorization) ---

        # Get section introduction
        section_intro = get_variation(content_library, 'profitability_growth.section_introductions',
            ['Profitability and Growth Analysis'])

        # Determine growth categories using market standard thresholds
        revenue_growth_key = "moderate_revenue"
        if rev_growth_raw is not None:
            if rev_growth_raw > 0.15:
                revenue_growth_key = "strong_revenue"
            elif rev_growth_raw < 0.03:
                revenue_growth_key = "weak_revenue"

        earnings_growth_key = "moderate_earnings"
        if earnings_growth_raw is not None:
            if earnings_growth_raw > 0.20:
                earnings_growth_key = "strong_earnings"
            elif earnings_growth_raw < 0.05:
                earnings_growth_key = "weak_earnings"

        # Determine overall growth assessment (following market algorithm)
        growth_assessment_key = "moderate_growth"
        if rev_growth_raw is not None and earnings_growth_raw is not None:
            avg_growth = (rev_growth_raw + earnings_growth_raw) / 2
            if avg_growth > 0.18:
                growth_assessment_key = "strong_growth"
            elif avg_growth < 0.04:
                growth_assessment_key = "weak_growth"
        elif rev_growth_raw is not None:
            if rev_growth_raw > 0.15:
                growth_assessment_key = "strong_growth"
            elif rev_growth_raw < 0.05:
                growth_assessment_key = "weak_growth"

        # Determine margin trends (following market standard margin analysis)
        margin_trend_key = "stable_margins"
        if op_margin_raw is not None and net_margin_raw is not None:
            if op_margin_raw > 0.15 and net_margin_raw > 0.10:
                margin_trend_key = "improving_margins"
            elif op_margin_raw < 0.05 or net_margin_raw < 0.02:
                margin_trend_key = "declining_margins"

        # Get content library variations with proper formatting
        growth_assessment = get_variation(content_library, f'profitability_growth.growth_assessments.{growth_assessment_key}',
            ['demonstrates balanced growth performance'])

        revenue_analysis = get_variation(content_library, f'profitability_growth.revenue_analysis.{revenue_growth_key}',
            [f'maintains reasonable revenue growth of <strong>{rev_growth_fmt}</strong>']).format(revenue_growth_fmt=rev_growth_fmt)

        earnings_analysis = get_variation(content_library, f'profitability_growth.earnings_analysis.{earnings_growth_key}',
            [f'maintains reasonable earnings growth of <strong>{earnings_growth_fmt}</strong>']).format(earnings_growth_fmt=earnings_growth_fmt)

        margin_trends = get_variation(content_library, f'profitability_growth.margin_trends.{margin_trend_key}',
            ['maintains stable margin performance'])

        # Get transition words from content library
        transition_emphasis = get_variation(content_library, 'profitability_growth.transition_words.emphasis', ['Furthermore'])
        transition_contrast = get_variation(content_library, 'profitability_growth.transition_words.contrast', ['However'])
        transition_causation = get_variation(content_library, 'profitability_growth.transition_words.causation', ['Consequently'])
        transition_continuation = get_variation(content_library, 'profitability_growth.transition_words.continuation', ['Additionally'])

        # --- 3. Dynamic Narrative Generation (Following Market Standard Structure) ---

        # --- Paragraph 1: Margin Performance and Revenue Context (Market Algorithm Logic) ---
        paragraph1_parts = []
        
        # Margin assessment using market standard logic
        margin_assessment = "shows the company has solid control over its costs and prices"
        if op_margin_raw is not None and op_margin_raw < 0.05:
            margin_assessment = "suggests the company faces significant margin pressure"
        elif op_margin_raw is not None and op_margin_raw < 0.10:
            margin_assessment = "indicates a moderately profitable operation, though with room for improvement"
        
        paragraph1_parts.append(f"An analysis of the key metrics in {ticker}'s margin performance {margin_assessment}.")
        paragraph1_parts.append(f"The company {revenue_analysis}, which provides insight into market demand, competitive positioning, and management's execution of growth strategies.")

        # Market standard margin analysis with content library integration
        if gross_margin_raw is not None and op_margin_raw is not None:
            paragraph1_parts.append(f"The company is successful in controlling its production costs, as shown by the gross margin of <strong>{gross_margin_fmt}</strong>, and it also profits well from its core operations, reflected in the <strong>{op_margin_fmt}</strong> operating margin.")
        
        if ebitda_margin_raw is not None:
            paragraph1_parts.append(f"A <strong>{ebitda_margin_fmt}</strong> EBITDA margin indicates {ticker} is capable of generating strong cash flow from its operations before accounting for financing and tax strategies.")

        # --- Paragraph 2: Earnings Performance and Growth Dynamics ---
        paragraph2_parts = []
        paragraph2_parts.append(f"From a bottom-line perspective, {ticker} {earnings_analysis}, revealing the organization's ability to convert revenue expansion into actual profit generation.")
        
        # Market standard profit analysis
        if net_margin_raw is not None:
            currency_symbol = hc.get_currency_symbol(ticker)
            net_profit_cents = f"{net_margin_raw:.3f}"
            paragraph2_parts.append(f"All things considered, {ticker} can hold onto around <strong>{currency_symbol}{net_profit_cents}</strong> in net profit for every {currency_symbol}1 of its revenue over the last twelve months.")

        # Growth comparison analysis (market standard)
        if earnings_growth_raw is not None and rev_growth_raw is not None:
            if earnings_growth_raw > rev_growth_raw:
                paragraph2_parts.append(f"{transition_emphasis}, earnings growth exceeds revenue growth, indicating improving operational leverage and enhanced margin efficiency throughout the business cycle.")
            elif earnings_growth_raw < rev_growth_raw * 0.8:
                paragraph2_parts.append(f"{transition_contrast}, the earnings growth rate trails revenue expansion, suggesting potential margin pressures or increased investment spending that may benefit future periods.")
            else:
                paragraph2_parts.append(f"The relationship between earnings and revenue growth demonstrates balanced operational execution with sustainable profitability trends.")

        paragraph2_parts.append(f"{transition_causation}, the company {margin_trends}, providing investors with confidence in sustainable profit generation capabilities.")

        # --- Paragraph 3: Investment Implications and Future Outlook ---
        paragraph3_parts = []
        
        # Use content library conclusion with proper formatting
        conclusion_statement = get_variation(content_library, 'profitability_growth.conclusion_statements',
            [f'Overall, {company_name} demonstrates solid growth momentum with consistent revenue and earnings expansion.']).format(
                company_name=company_name, 
                growth_summary=growth_assessment, 
                revenue_summary=revenue_analysis, 
                earnings_summary=earnings_analysis, 
                margin_summary=margin_trends
            )
        paragraph3_parts.append(conclusion_statement)

        # Market standard future outlook analysis
        if rev_growth_raw is not None:
            growth_rate_text = "an aggressive" if rev_growth_raw > 0.20 else "a moderate and healthy" if rev_growth_raw > 0.05 else "a slow"
            paragraph3_parts.append(f"While the business's revenue is increasing at {growth_rate_text} rate, investors should monitor if this pace can be sustained without eroding profit margins.")

        # Investment implications based on growth profile
        if growth_assessment_key == "strong_growth":
            paragraph3_parts.append(f"This robust growth profile positions {ticker} as an attractive investment opportunity for growth-oriented portfolios seeking companies with demonstrated expansion capabilities.")
        elif growth_assessment_key == "weak_growth":
            paragraph3_parts.append(f"While current growth metrics appear modest, potential catalysts for acceleration may include operational improvements, market expansion initiatives, or strategic repositioning efforts.")
        else:
            paragraph3_parts.append(f"This balanced growth approach suggests a mature business model with steady value creation potential, appealing to investors seeking reliable performance over aggressive expansion.")

        paragraph3_parts.append(f"In the future, maintaining steady or improving margins will be critical. {ticker} needs to defend its pricing power and control operating costs, as this will help sustain profitability, especially if revenue growth moderates.")

        # --- 4. Assemble Final HTML ---
        html_parts = []

        # Section header
        html_parts.append(f"<h3>{section_intro}</h3>")

        # Narrative content following market standard structure
        html_parts.append(f"""
        <div class="narrative">
            <p>{' '.join(paragraph1_parts)}</p>
            <p>{' '.join(paragraph2_parts)}</p>
            <p>{' '.join(paragraph3_parts)}</p>
        </div>
        """)

        # Generate the data table using WordPress version
        table_content = generate_wordpress_metrics_section_content(profitability_data, ticker, content_library)

        return ''.join(html_parts) + table_content

    except Exception as e:
        print(f"Warning: Error in WordPress profitability growth generation: {e}. Using fallback.")
        return hc.generate_profitability_growth_html(ticker, rdata)

def generate_wordpress_dividends_shareholder_returns_html(ticker, rdata, content_library=None):
    """
    Generate WordPress dividends and shareholder returns content using content library variations.
    Uses the actual algorithms from html_components.py with enhanced content library integration.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_dividends_shareholder_returns_html(ticker, rdata)

        # --- 1. Data Extraction (same as html_components) ---
        dividend_data = rdata.get('dividends_data', {})
        if not isinstance(dividend_data, dict):
            dividend_data = {}

        profile_data = rdata.get('profile_data', {})
        company_name = profile_data.get('Company Name', ticker)

        # Extract dividend metrics using html_components approach
        rate = hc._safe_float(dividend_data.get('Dividend Rate'))
        div_yield = hc._safe_float(dividend_data.get('Dividend Yield'))
        payout_ratio = hc._safe_float(dividend_data.get('Payout Ratio'))
        five_year_avg_yield = hc._safe_float(dividend_data.get('5 Year Average Dividend Yield'))
        trailing_yield = hc._safe_float(dividend_data.get('Trailing Dividend Yield'))
        ex_div_date = dividend_data.get('Ex-Dividend Date')
        last_split_date_str = dividend_data.get('Last Split Date')
        last_split_factor = dividend_data.get('Last Split Factor')

        # Same dividend check logic as html_components
        has_dividend = div_yield is not None and div_yield > 0 and payout_ratio is not None and payout_ratio > 0

        # Get section introduction with variations
        section_intro = get_variation(content_library, 'dividends_shareholders.section_introductions',
            ['Dividend Summary & Investor Implications'])

        # --- Handle the "No Dividend" Case with content library variations ---
        if not has_dividend:
            no_dividend_explanation = get_variation(content_library, 'dividends_shareholders.no_dividend_analysis',
                [f'{ticker} does not currently pay a regular dividend'])
            
            growth_focus_explanation = get_variation(content_library, 'dividends_shareholders.growth_reinvestment_focus',
                ['This suggests the company may be prioritizing reinvesting its earnings back into the business for growth'])

            html_parts = []
            html_parts.append(f"<h3>{section_intro}</h3>")
            html_parts.append(f"""
            <div class="narrative">
                <p>Based on available data, <strong>{no_dividend_explanation}</strong>. {growth_focus_explanation}.</p>
            </div>
            """)

            table_content = generate_wordpress_metrics_section_content(dividend_data, ticker, content_library)
            return ''.join(html_parts) + table_content

        # --- Build Enhanced Narrative for Dividend-Paying Companies ---
        
        # Format values using html_components approach
        rate_fmt = hc.format_html_value(rate, 'currency', ticker=ticker)
        yield_fmt = hc.format_html_value(div_yield, "percent_direct")
        payout_ratio_fmt = hc.format_html_value(payout_ratio, "percent_direct")
        five_year_avg_yield_fmt = hc.format_html_value(five_year_avg_yield, 'percent_direct')

        # Determine dividend characteristics for content library selection
        # Note: div_yield values are in percentage form (e.g., 2.0 for 2%), not decimals
        dividend_level_key = "moderate_dividend"
        if div_yield is not None:
            if div_yield > 4:
                dividend_level_key = "high_dividend"
            elif div_yield < 2:
                dividend_level_key = "low_dividend"

        payout_sustainability_key = "healthy_payout"
        # Note: payout_ratio values are in percentage form (e.g., 75 for 75%), not decimals
        if payout_ratio is not None:
            if payout_ratio > 75:
                payout_sustainability_key = "high_payout"
            elif payout_ratio < 30:
                payout_sustainability_key = "conservative_payout"

        yield_trend_key = "stable_yield"
        if five_year_avg_yield is not None and div_yield is not None:
            if div_yield < five_year_avg_yield * 0.9:
                yield_trend_key = "declining_yield"
            elif div_yield > five_year_avg_yield * 1.1:
                yield_trend_key = "improving_yield"

        # Get content library variations
        currency_symbol = hc.get_currency_symbol(ticker)
        dividend_overview = get_variation(content_library, f'dividends_shareholders.dividend_overview.{dividend_level_key}',
            [f'The company currently offers a {rate_fmt} annual dividend per share'])

        yield_analysis = get_variation(content_library, f'dividends_shareholders.yield_analysis.{yield_trend_key}',
            [f'translating to a dividend yield of {yield_fmt}'])

        payout_assessment = get_variation(content_library, f'dividends_shareholders.payout_analysis.{payout_sustainability_key}',
            [f'The payout ratio of {payout_ratio_fmt} indicates balanced dividend sustainability'])

        transition_emphasis = get_variation(content_library, 'transition_words.emphasis', ['Furthermore'])
        transition_continuation = get_variation(content_library, 'transition_words.continuation', ['Additionally'])
        transition_contrast = get_variation(content_library, 'transition_words.contrast', ['However'])

        # --- Paragraph 1: Dividend Overview and Yield Context ---
        paragraph1_parts = []
        paragraph1_parts.append(f"{company_name} {dividend_overview}, {yield_analysis}.")
        # div_yield is already in percentage form (e.g., 0.02 for 0.02%), so no *100 needed
        paragraph1_parts.append(f"This means for every {currency_symbol}100 invested, shareholders receive approximately <strong>{currency_symbol}{div_yield:.2f}</strong> in annual dividend payments.")
        
        if five_year_avg_yield is not None and div_yield is not None:
            if div_yield < five_year_avg_yield:
                yield_comparison = get_variation(content_library, 'dividends_shareholders.yield_comparison.below_average',
                    [f'This yield is below the 5-year average of {five_year_avg_yield_fmt}'])
                paragraph1_parts.append(f"{yield_comparison}, suggesting either stock price appreciation has reduced the yield or dividend growth has moderated relative to historical patterns.")
            else:
                yield_comparison = get_variation(content_library, 'dividends_shareholders.yield_comparison.above_average',
                    [f'This yield exceeds the 5-year average of {five_year_avg_yield_fmt}'])
                paragraph1_parts.append(f"{yield_comparison}, making the current dividend more attractive to income-focused investors compared to recent historical levels.")
        
        paragraph1_parts.append(f"Such dividend characteristics position {ticker} within the income-generating investment category for portfolio construction considerations.")

        # --- Paragraph 2: Payout Analysis and Sustainability Assessment ---
        paragraph2_parts = []
        # payout_ratio is already in percentage form (e.g., 0.99 for 0.99%), so no *100 needed
        paragraph2_parts.append(f"{transition_emphasis}, {company_name} {payout_assessment}, demonstrating that the organization allocates approximately <strong>{payout_ratio:.0f}%</strong> of its earnings toward dividend distributions.")
        
        # payout_ratio values are in percentage form (e.g., 75 for 75%)
        if payout_ratio is not None:
            if payout_ratio > 75:
                sustainability_concern = get_variation(content_library, 'dividends_shareholders.sustainability_analysis.high_risk',
                    ['This elevated payout level warrants careful monitoring of cash flow sustainability'])
                paragraph2_parts.append(f"{sustainability_concern}, as limited earnings retention may constrain future growth investments or dividend increases during challenging periods.")
            elif payout_ratio < 30:
                sustainability_strength = get_variation(content_library, 'dividends_shareholders.sustainability_analysis.conservative',
                    ['This conservative payout approach provides substantial financial flexibility'])
                paragraph2_parts.append(f"{sustainability_strength}, leaving significant earnings available for reinvestment, debt reduction, or future dividend enhancement as business conditions permit.")
            else:
                sustainability_balance = get_variation(content_library, 'dividends_shareholders.sustainability_analysis.balanced',
                    ['This balanced payout strategy maintains adequate earnings retention'])
                paragraph2_parts.append(f"{sustainability_balance} while providing meaningful shareholder returns, suggesting management's commitment to both income distribution and long-term value creation.")

        if ex_div_date and ex_div_date != 'N/A':
            ex_dividend_timing = get_variation(content_library, 'dividends_shareholders.timing_considerations',
                [f'Prospective investors must establish positions before the ex-dividend date of {hc.format_html_value(ex_div_date, "date")}'])
            paragraph2_parts.append(f"{transition_continuation}, {ex_dividend_timing} to qualify for the upcoming dividend payment.")

        # --- Paragraph 3: Investment Implications and Strategic Positioning ---
        paragraph3_parts = []
        
        # div_yield and payout_ratio values are in percentage form (e.g., 3 for 3%, 40 for 40%)
        if payout_ratio is not None and div_yield is not None:
            if payout_ratio < 40 and div_yield < 3:
                investment_profile = get_variation(content_library, 'dividends_shareholders.investment_profile.growth_focused',
                    [f'The combination of modest yield and conservative payout suggests {ticker} prioritizes reinvestment over immediate income'])
                paragraph3_parts.append(f"{investment_profile}, appealing to growth-oriented investors who value dividend safety and potential for future increases over current yield maximization.")
                paragraph3_parts.append(f"Income-focused investors should recognize that while the dividend appears highly sustainable, the current yield may not satisfy portfolios requiring substantial immediate cash flow generation.")
            elif payout_ratio > 60 or div_yield > 4:
                investment_profile = get_variation(content_library, 'dividends_shareholders.investment_profile.income_focused',
                    [f'The substantial yield and meaningful payout ratio position {ticker} as an income-generating investment'])
                paragraph3_parts.append(f"{investment_profile}, though investors should monitor earnings trends and cash flow sustainability to ensure dividend security during economic uncertainties.")
                paragraph3_parts.append(f"Growth investors may find limited appeal unless the company demonstrates ability to maintain dividend growth while preserving competitive positioning and market share expansion.")
            else:
                investment_profile = get_variation(content_library, 'dividends_shareholders.investment_profile.balanced',
                    [f'The balanced dividend characteristics suggest {ticker} appeals to both income and growth investment strategies'])
                paragraph3_parts.append(f"{investment_profile}, providing reasonable current income while maintaining financial flexibility for business development and strategic initiatives.")
                paragraph3_parts.append(f"This dividend profile typically supports portfolio diversification objectives and may appeal to investors seeking steady income with potential for capital appreciation.")

        monitoring_considerations = get_variation(content_library, 'dividends_shareholders.monitoring_considerations',
            ['Key factors to monitor include earnings stability, cash flow trends, and management commentary regarding future dividend policy'])
        paragraph3_parts.append(f"{monitoring_considerations}, as these elements directly influence dividend sustainability and potential enhancement opportunities.")

        # --- 3. Assemble Final HTML ---
        html_parts = []
        html_parts.append(f"<h3>{section_intro}</h3>")
        html_parts.append(f"""
        <div class="narrative">
            <p>{' '.join(paragraph1_parts)}</p>
            <p>{' '.join(paragraph2_parts)}</p>
            <p>{' '.join(paragraph3_parts)}</p>
        </div>
        """)

        table_content = generate_wordpress_metrics_section_content(dividend_data, ticker, content_library)
        return ''.join(html_parts) + table_content

    except Exception as e:
        print(f"Warning: Error in WordPress dividends generation: {e}. Using fallback.")
        return hc.generate_dividends_shareholder_returns_html(ticker, rdata)

def generate_wordpress_share_statistics_html(ticker, rdata, content_library=None):
    """
    Generate WordPress share statistics content using content library variations.
    Uses the actual algorithms from html_components.py with enhanced content library integration.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_share_statistics_html(ticker, rdata)

        # --- 1. Data Extraction (same as html_components) ---
        share_data = rdata.get('share_statistics_data', {})
        short_data = rdata.get('short_selling_data', {})
        profile_data = rdata.get('profile_data', {})
        company_name = profile_data.get('Company Name', ticker)

        # Helper function from html_components (same parsing logic)
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

        # Parse raw values using same logic as html_components
        shares_out_raw = _parse_value(share_data.get('Shares Outstanding'))
        shares_float_raw = _parse_value(share_data.get('Shares Float'))
        insider_own_raw = _parse_value(share_data.get('Insider Ownership'))
        inst_own_raw = _parse_value(share_data.get('Institutional Ownership'))
        shares_short_raw = _parse_value(short_data.get('Shares Short'))
        short_float_raw = _parse_value(short_data.get('Short % of Float'))

        # Get section introduction with variations
        section_intro = get_variation(content_library, 'share_statistics.section_introductions',
            ['Share Statistics and Ownership Analysis'])

        # Determine ownership and liquidity characteristics for content library selection
        float_level_key = "moderate_float"
        if shares_float_raw is not None:
            if shares_float_raw > 100_000_000:
                float_level_key = "large_float"
            elif shares_float_raw < 25_000_000:
                float_level_key = "tight_float"

        institutional_ownership_key = "moderate_institutional"
        if inst_own_raw is not None:
            if inst_own_raw > 0.70:
                institutional_ownership_key = "high_institutional"
            elif inst_own_raw < 0.30:
                institutional_ownership_key = "low_institutional"

        # Get content library variations
        transition_emphasis = get_variation(content_library, 'transition_words.emphasis', ['Moreover'])
        transition_contrast = get_variation(content_library, 'transition_words.contrast', ['However'])
        transition_causation = get_variation(content_library, 'transition_words.causation', ['Consequently'])

        # --- Paragraph 1: Float Structure and Liquidity Analysis ---
        paragraph1_parts = []
        
        if shares_out_raw is not None and shares_float_raw is not None:
            float_percentage = (shares_out_raw - shares_float_raw) / shares_out_raw * 100 if shares_out_raw > 0 else 0
            
            float_analysis = get_variation(content_library, f'share_statistics.float_analysis.{float_level_key}',
                [f'{company_name} maintains a balanced trading float structure'])
            
            if float_percentage < 5:
                paragraph1_parts.append(f"{float_analysis} with nearly all of the company's <strong>{share_data.get('Shares Outstanding', 'N/A')}</strong> shares available as public float, indicating minimal restricted ownership.")
            else:
                paragraph1_parts.append(f"{float_analysis} with approximately <strong>{float_percentage:.1f}%</strong> of total shares held by insiders or strategic investors, leaving <strong>{share_data.get('Shares Float', 'N/A')}</strong> shares available for public trading.")
            
            if shares_float_raw > 50_000_000:
                paragraph1_parts.append(f"This substantial float structure supports strong trading liquidity, allowing institutional and retail investors to establish meaningful positions without significant market impact.")
            else:
                paragraph1_parts.append(f"This more limited float structure may experience increased price sensitivity during larger institutional transactions due to the constrained share availability.")
                
            paragraph1_parts.append(f"{transition_contrast}, investors should monitor potential future share issuances that could expand the float and potentially dilute existing ownership interests.")
        else:
            paragraph1_parts.append(f"Limited information regarding share structure and float composition constrains comprehensive liquidity assessment, requiring investors to rely on trading volume patterns and market depth analysis.")

        # --- Paragraph 2: Ownership Structure and Institutional Analysis ---
        paragraph2_parts = []
        
        paragraph2_parts.append(f"{company_name} demonstrates a specific ownership composition that provides insight into management alignment and institutional confidence levels.")
        
        if insider_own_raw is not None:            
            if insider_own_raw < 0.01:
                paragraph2_parts.append(f"Executive and insider ownership levels at <strong>{share_data.get('Insider Ownership', 'N/A')}</strong> suggest minimal management skin in the game, potentially creating misaligned incentives during challenging business periods.")
            elif insider_own_raw > 0.10:
                paragraph2_parts.append(f"Executive and insider ownership levels at <strong>{share_data.get('Insider Ownership', 'N/A')}</strong> indicate substantial management commitment, aligning leadership interests with shareholder value creation objectives.")
            else:
                paragraph2_parts.append(f"Executive and insider ownership levels at <strong>{share_data.get('Insider Ownership', 'N/A')}</strong> reflect reasonable management alignment without creating excessive concentration or control concerns.")

        if inst_own_raw is not None:
            institutional_analysis = get_variation(content_library, f'share_statistics.institutional_ownership.{institutional_ownership_key}',
                [f'Institutional ownership patterns'])
            
            if inst_own_raw < 0.30:
                paragraph2_parts.append(f"{transition_emphasis}, {institutional_analysis} at <strong>{share_data.get('Institutional Ownership', 'N/A')}</strong> suggest limited institutional participation may indicate professional investor skepticism or insufficient analyst coverage to attract large-scale professional investment.")
            else:
                paragraph2_parts.append(f"{transition_emphasis}, {institutional_analysis} at <strong>{share_data.get('Institutional Ownership', 'N/A')}</strong> demonstrate strong institutional ownership providing stability and professional validation, supporting share price stability and market credibility.")

        # --- Paragraph 3: Short Interest Analysis and Strategic Implications ---
        paragraph3_parts = []
        
        if shares_short_raw is not None and short_float_raw is not None:            
            if short_float_raw > 0.10:
                paragraph3_parts.append(f"Current short interest patterns with <strong>{short_data.get('Shares Short', 'N/A')}</strong> shares sold short (<strong>{short_data.get('Short % of Float', 'N/A')}</strong> of float) suggest elevated short interest indicates significant market skepticism, requiring careful evaluation of underlying business fundamentals.")
                paragraph3_parts.append(f"While high short interest can create potential short squeeze opportunities during positive developments, it also signals meaningful professional concern about the company's prospects.")
            elif short_float_raw < 0.03:
                paragraph3_parts.append(f"Current short interest patterns with <strong>{short_data.get('Shares Short', 'N/A')}</strong> shares sold short (<strong>{short_data.get('Short % of Float', 'N/A')}</strong> of float) indicate minimal short interest reflects limited bearish sentiment, suggesting broad market confidence in the company's strategic direction.")
                paragraph3_parts.append(f"This low short interest environment may limit short squeeze potential but provides a more stable foundation for upward price movement during positive catalysts.")
            else:
                paragraph3_parts.append(f"Current short interest patterns with <strong>{short_data.get('Shares Short', 'N/A')}</strong> shares sold short (<strong>{short_data.get('Short % of Float', 'N/A')}</strong> of float) reflect moderate short interest suggests measured market skepticism without extreme positioning in either direction.")

        # Strategic synthesis based on combined factors
        if shares_float_raw is not None and inst_own_raw is not None:
            if shares_float_raw > 50_000_000 and inst_own_raw < 0.30:
                paragraph3_parts.append(f"{transition_causation}, the combination of high liquidity and limited institutional ownership suggests the stock remains accessible for trading but may require stronger fundamental performance or enhanced analyst coverage to attract significant professional investment.")
            elif insider_own_raw is not None and insider_own_raw > 0.10 and inst_own_raw > 0.70:
                paragraph3_parts.append(f"{transition_causation}, the alignment of strong insider and institutional ownership creates a solid foundation for share price stability and strategic execution, though may limit float availability during periods of increased demand.")

        # --- 3. Assemble Final HTML ---
        html_parts = []
        html_parts.append(f"<h3>{section_intro}</h3>")
        html_parts.append(f"""
        <div class="narrative">
            <p>{' '.join(paragraph1_parts)}</p>
            <p>{' '.join(paragraph2_parts)}</p>
            <p>{' '.join(paragraph3_parts)}</p>
        </div>
        """)

        # Combine data for table view (same as html_components)
        combined_data_for_table = {**share_data, **short_data}
        table_content = generate_wordpress_metrics_section_content(combined_data_for_table, ticker, content_library)
        
        return ''.join(html_parts) + table_content

    except Exception as e:
        print(f"Warning: Error in WordPress share statistics generation: {e}. Using fallback.")
        return hc.generate_share_statistics_html(ticker, rdata)

def generate_wordpress_dividends_shareholder_returns_html(ticker, rdata, content_library=None):
    """
    Generate WordPress dividends and shareholder returns content using market standard algorithms
    with comprehensive content library integration following exact JSON structure.
    """
    try:
        if not content_library:
            return hc.generate_dividends_shareholder_returns_html(ticker, rdata)

        # --- 1. Data Extraction (Following Market Standard Algorithm) ---
        dividend_data = rdata.get('dividends_data', {})
        if not isinstance(dividend_data, dict):
            dividend_data = {}
            print("Warning: dividends_data not found or not a dict, using empty.")

        profile_data = rdata.get('profile_data', {})
        company_name = profile_data.get('Company Name', ticker)

        # Extract dividend metrics using exact html_components approach
        rate = hc._safe_float(dividend_data.get('Dividend Rate'))
        div_yield = hc._safe_float(dividend_data.get('Dividend Yield'))
        payout_ratio = hc._safe_float(dividend_data.get('Payout Ratio'))
        five_year_avg_yield = hc._safe_float(dividend_data.get('5 Year Average Dividend Yield'))
        trailing_yield = hc._safe_float(dividend_data.get('Trailing Dividend Yield'))
        ex_div_date = dividend_data.get('Ex-Dividend Date')
        last_split_date_str = dividend_data.get('Last Split Date')
        last_split_factor = dividend_data.get('Last Split Factor')

        # Market standard dividend check logic
        has_dividend = div_yield is not None and div_yield > 0 and payout_ratio is not None and payout_ratio > 0

        # Get section introduction with content library
        section_intro = get_variation(content_library, 'dividends_shareholders.section_introductions',
            ['Dividends and Shareholder Returns'])

        # --- Handle the "No Dividend" Case with content library variations ---
        if not has_dividend:
            conservative_policy = get_variation(content_library, 'dividends_shareholders.dividend_policy.conservative_policy',
                ['maintains a conservative dividend policy'])
            
            weak_returns = get_variation(content_library, 'dividends_shareholders.shareholder_returns.weak_returns',
                ['shows limited shareholder returns'])

            html_parts = []
            html_parts.append(f"<h3>{section_intro}</h3>")
            html_parts.append(f"""
            <div class="narrative">
                <p>Based on available data, <strong>{ticker} does not currently pay a regular dividend</strong>. The company {conservative_policy}, which {weak_returns} through dividend distributions but may prioritize reinvesting earnings for business growth and expansion opportunities.</p>
            </div>
            """)
            
            table_content = generate_wordpress_metrics_section_content(dividend_data, ticker, content_library)
            return ''.join(html_parts) + table_content

        # --- 2. Market Standard Categorization for Content Library Selection ---
        
        # Format values using html_components approach
        rate_fmt = hc.format_html_value(rate, 'currency', ticker=ticker)
        yield_fmt = hc.format_html_value(div_yield, "percent_direct")
        payout_ratio_fmt = hc.format_html_value(payout_ratio, "percent_direct")
        five_year_avg_yield_fmt = hc.format_html_value(five_year_avg_yield, 'percent_direct')

        # Determine dividend policy category (Market Standard Thresholds)
        # Note: div_yield and payout_ratio are in percentage form (e.g., 4.0 for 4%, 60.0 for 60%)
        dividend_policy_key = "moderate_policy"
        if div_yield is not None and payout_ratio is not None:
            if div_yield > 4.0 or payout_ratio > 60.0:
                dividend_policy_key = "generous_policy"
            elif div_yield < 2.0 or payout_ratio < 30.0:
                dividend_policy_key = "conservative_policy"

        # Determine shareholder returns category
        # Note: div_yield is in percentage form (e.g., 5.0 for 5%)
        shareholder_returns_key = "moderate_returns"
        if div_yield is not None:
            if div_yield > 5.0:
                shareholder_returns_key = "strong_returns"
            elif div_yield < 1.5:
                shareholder_returns_key = "weak_returns"

        # Determine payout sustainability (Market Standard Analysis)
        # Note: payout_ratio is in percentage form (e.g., 75.0 for 75%)
        payout_analysis_key = "sustainable_payout"
        if payout_ratio is not None:
            if payout_ratio > 75.0:
                payout_analysis_key = "high_payout"
            elif payout_ratio < 30.0:
                payout_analysis_key = "low_payout"

        # Determine yield attractiveness
        # Note: div_yield is in percentage form (e.g., 4.0 for 4%)
        yield_assessment_key = "moderate_yield"
        if div_yield is not None:
            if div_yield > 4.0:
                yield_assessment_key = "attractive_yield"
            elif div_yield < 2.0:
                yield_assessment_key = "low_yield"

        # Get content library variations with proper formatting
        dividend_policy = get_variation(content_library, f'dividends_shareholders.dividend_policy.{dividend_policy_key}',
            ['maintains a moderate dividend policy'])

        shareholder_returns = get_variation(content_library, f'dividends_shareholders.shareholder_returns.{shareholder_returns_key}',
            ['maintains reasonable shareholder returns'])

        payout_analysis = get_variation(content_library, f'dividends_shareholders.payout_analysis.{payout_analysis_key}',
            [f'maintains sustainable payout ratio of <strong>{payout_ratio_fmt}</strong>']).format(payout_ratio_fmt=payout_ratio_fmt)

        yield_assessment = get_variation(content_library, f'dividends_shareholders.yield_assessment.{yield_assessment_key}',
            [f'offers moderate dividend yield of <strong>{yield_fmt}</strong>']).format(yield_fmt=yield_fmt)

        # Get transition words from content library
        transition_emphasis = get_variation(content_library, 'dividends_shareholders.transition_words.emphasis', ['Furthermore'])
        transition_contrast = get_variation(content_library, 'dividends_shareholders.transition_words.contrast', ['However'])
        transition_causation = get_variation(content_library, 'dividends_shareholders.transition_words.causation', ['Consequently'])
        transition_continuation = get_variation(content_library, 'dividends_shareholders.transition_words.continuation', ['Additionally'])

        # --- 3. Dynamic Narrative Generation (Following Market Standard Structure) ---

        # --- Paragraph 1: Dividend Overview and Yield Context (Market Algorithm) ---
        paragraph1_parts = []
        currency_symbol = hc.get_currency_symbol(ticker)
        
        paragraph1_parts.append(f"{company_name} {dividend_policy} and {yield_assessment}, providing shareholders with <strong>{rate_fmt} annual dividend per share</strong>.")
        # div_yield is already in percentage form (e.g., 0.02 for 0.02%), so no *100 needed
        paragraph1_parts.append(f"This translates to approximately <strong>{currency_symbol}{div_yield:.2f}</strong> in annual dividend income for every {currency_symbol}100 invested in the company.")
        
        # Market standard yield comparison analysis
        if five_year_avg_yield is not None and div_yield is not None:
            if div_yield < five_year_avg_yield:
                paragraph1_parts.append(f"{transition_contrast}, this current yield is <strong>below the 5-year average of {five_year_avg_yield_fmt}</strong>, suggesting either stock price appreciation has reduced the yield or dividend growth has moderated relative to historical patterns.")
            else:
                paragraph1_parts.append(f"{transition_emphasis}, this yield <strong>exceeds the 5-year average of {five_year_avg_yield_fmt}</strong>, making the current dividend more attractive to income-focused investors compared to recent historical levels.")
        
        paragraph1_parts.append(f"Such dividend characteristics position {ticker} within specific investment categories for portfolio construction and income generation strategies.")

        # --- Paragraph 2: Payout Analysis and Sustainability Assessment (Market Standard) ---
        paragraph2_parts = []
        paragraph2_parts.append(f"From a payout sustainability perspective, {ticker} {payout_analysis}, indicating the organization allocates approximately <strong>{payout_ratio:.0f}%</strong> of its earnings toward dividend distributions.")
        
        # Market standard payout ratio analysis
        if payout_ratio is not None:
            payout_level = "healthy and sustainable"
            if payout_ratio > 75.0:
                payout_level = "elevated (warranting careful cash flow monitoring)"
                sustainability_note = f"{transition_emphasis}, this high payout level requires careful monitoring of cash flow sustainability, as limited earnings retention may constrain future growth investments or dividend increases during challenging periods."
            elif payout_ratio < 30.0:
                payout_level = "conservative and prudent"
                sustainability_note = f"This conservative approach provides substantial financial flexibility, leaving significant earnings available for reinvestment, debt reduction, or future dividend enhancement as business conditions permit."
            else:
                sustainability_note = f"This balanced payout strategy maintains adequate earnings retention while providing meaningful shareholder returns, suggesting management's commitment to both income distribution and long-term value creation."
            
            paragraph2_parts.append(sustainability_note)

        # Market standard timing considerations
        if ex_div_date and ex_div_date != 'N/A':
            paragraph2_parts.append(f"{transition_continuation}, prospective investors must establish positions before the ex-dividend date of <strong>{hc.format_html_value(ex_div_date, 'date')}</strong> to qualify for the upcoming dividend payment.")

        # Market standard split analysis
        if last_split_date_str and last_split_date_str != 'N/A':
            try:
                split_year = int(last_split_date_str.split('-')[0])
                if datetime.now().year - split_year > 15:
                    paragraph2_parts.append(f"The last stock split ({last_split_factor} in {split_year}) occurred over 15 years ago and has limited relevance to current valuation assessments.")
            except (ValueError, IndexError):
                pass

        # --- Paragraph 3: Investment Implications and Strategic Positioning ---
        paragraph3_parts = []
        
        # Use content library conclusion with proper formatting
        conclusion_statement = get_variation(content_library, 'dividends_shareholders.conclusion_statements',
            [f'Overall, {company_name} maintains balanced dividend characteristics with reasonable shareholder returns.']).format(
                company_name=company_name,
                policy_summary=dividend_policy,
                returns_summary=shareholder_returns,
                payout_summary=payout_analysis,
                yield_summary=yield_assessment
            )
        paragraph3_parts.append(conclusion_statement)

        # Market standard investment profile analysis
        if payout_ratio is not None and div_yield is not None:
            if payout_ratio < 40.0 and div_yield < 3.0:
                investment_profile = "The combination of modest yield and conservative payout suggests the company prioritizes reinvestment over immediate income distribution"
                paragraph3_parts.append(f"{investment_profile}, appealing to growth-oriented investors who value dividend safety and potential for future increases over current yield maximization.")
                paragraph3_parts.append(f"Income-focused investors should recognize that while the dividend appears highly sustainable, the current yield may not satisfy portfolios requiring substantial immediate cash flow generation.")
            elif payout_ratio > 60.0 or div_yield > 4.0:
                investment_profile = f"The substantial yield and meaningful payout ratio position {ticker} as an income-generating investment"
                paragraph3_parts.append(f"{investment_profile}, though investors should monitor earnings trends and cash flow sustainability to ensure dividend security during economic uncertainties.")
                paragraph3_parts.append(f"Growth investors may find limited appeal unless the company demonstrates ability to maintain dividend growth while preserving competitive positioning and market share expansion.")
            else:
                investment_profile = f"The balanced dividend characteristics suggest {ticker} appeals to both income and growth investment strategies"
                paragraph3_parts.append(f"{investment_profile}, providing reasonable current income while maintaining financial flexibility for business development and strategic initiatives.")
                paragraph3_parts.append(f"This dividend profile typically supports portfolio diversification objectives and may appeal to investors seeking steady income with potential for capital appreciation.")

        paragraph3_parts.append(f"Key monitoring factors include earnings stability, cash flow trends, and management commentary regarding future dividend policy, as these elements directly influence dividend sustainability and potential enhancement opportunities.")

        # --- 4. Assemble Final HTML ---
        html_parts = []
        html_parts.append(f"<h3>{section_intro}</h3>")
        html_parts.append(f"""
        <div class="narrative">
            <p>{' '.join(paragraph1_parts)}</p>
            <p>{' '.join(paragraph2_parts)}</p>
            <p>{' '.join(paragraph3_parts)}</p>
        </div>
        """)

        # Generate the data table using WordPress version
        table_content = generate_wordpress_metrics_section_content(dividend_data, ticker, content_library)
        return ''.join(html_parts) + table_content

    except Exception as e:
        print(f"Warning: Error in WordPress dividends generation: {e}. Using fallback.")
        return hc.generate_dividends_shareholder_returns_html(ticker, rdata)

        if ex_div_date:
            analysis_points.append(f"Investors must own the stock before the upcoming <strong>ex-dividend date of {hc.format_html_value(ex_div_date, 'date')}</strong> to receive the next dividend.")
        
        if last_split_date_str and last_split_date_str != 'N/A':
            try:
                split_year = int(last_split_date_str.split('-')[0])
                if datetime.now().year - split_year > 15:
                    analysis_points.append(f"The last stock split ({last_split_factor} in {split_year}) is outdated and likely irrelevant to the current valuation.")
            except (ValueError, IndexError):
                pass

        para2 = f"{emphasis_word}, analysis reveals key dividend sustainability factors: " + " ".join(analysis_points)

        # --- Paragraph 3: Investment Implications with content library variations ---
        takeaway_income = ""
        takeaway_growth = ""
        conclusion_word = get_variation(content_library, 'dividends_shareholders.transition_words.causation',
            ['Therefore'])
        
        if payout_ratio is not None and payout_ratio < 40:
            income_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.neutral',
                ['adequate'])
            growth_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive',
                ['robust'])
            takeaway_income = f"<strong>Income Investors:</strong> The modest yield and low payout ratio suggest dividends are {income_descriptor} but not a primary reason to invest. The focus may be on future dividend growth. "
            takeaway_growth = f"<strong>Growth Investors:</strong> The low payout ratio is a {growth_descriptor} signal that a majority of earnings are being reinvested, which could drive future price appreciation. "
        else:
            sustainability_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.neutral',
                ['stable'])
            balance_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.neutral',
                ['balanced'])
            takeaway_income = f"<strong>Income Investors:</strong> The dividend appears {sustainability_descriptor}, but investors should monitor earnings and cash flow to ensure the payout remains well-supported. "
            takeaway_growth = f"<strong>Growth Investors:</strong> The company maintains a {balance_descriptor} approach between shareholder returns and reinvestment, appealing to a 'growth and income' strategy. "

        monitoring_phrase = get_variation(content_library, 'dividends_shareholders.transition_words.continuation',
            ['Additionally'])
        para3 = f"{conclusion_word}, investment implications vary by strategy: {takeaway_income}{takeaway_growth}{monitoring_phrase}, watch for announcements of dividend hikes or significant stock price changes that would alter the yield."

        # --- Assemble Final HTML ---
        html_parts = []
        html_parts.append(f"<h3>{section_intro}</h3>")
        html_parts.append(f"""
        <div class="narrative">
            <p>{para1}</p>
            <p>{para2}</p>
            <p>{para3}</p>
        </div>
        """)
        
        # Add table content
        table_content = generate_wordpress_metrics_section_content(dividend_data, ticker, content_library)
        return ''.join(html_parts) + table_content

    except Exception as e:
        print(f"Warning: Error in WordPress dividends shareholder returns generation: {e}. Using fallback.")
        return hc.generate_dividends_shareholder_returns_html(ticker, rdata)

def generate_wordpress_share_statistics_html(ticker, rdata, content_library=None):
    """
    Generate WordPress share statistics content using exact html_components algorithms
    with comprehensive content library variations for professional ownership analysis.
    """
    try:
        if not content_library:
            return hc.generate_share_statistics_html(ticker, rdata)

        # --- 1. Data Extraction (exact html_components approach) ---
        share_data = rdata.get('share_statistics_data', {})
        short_data = rdata.get('short_selling_data', {})
        
        # Helper to parse formatted values like '$2B' or '1.1%' into numbers (exact html_components logic)
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

        # --- 2. Parse Raw Values for Logic (exact html_components approach) ---
        shares_out_raw = _parse_value(share_data.get('Shares Outstanding'))
        shares_float_raw = _parse_value(share_data.get('Shares Float'))
        insider_own_raw = _parse_value(share_data.get('Insider Ownership'))
        inst_own_raw = _parse_value(share_data.get('Institutional Ownership'))
        shares_short_raw = _parse_value(short_data.get('Shares Short'))
        short_float_raw = _parse_value(short_data.get('Short % of Float'))
        
        # Get section introduction with variations
        section_intro = get_variation(content_library, 'share_statistics.section_introductions',
            ['Share Statistics Overview'])

        # --- 3. Paragraph 1: Float Analysis and Liquidity (with content library variations) ---
        p1_parts = []
        
        intro_phrase = get_variation(content_library, 'dividends_shareholders.transition_words.emphasis',
            ['Examining']) + " the ownership structure reveals important liquidity insights."
        p1_parts.append(intro_phrase)
        
        if shares_out_raw is not None and shares_float_raw is not None:
            float_percentage = (shares_float_raw / shares_out_raw) * 100 if shares_out_raw > 0 else 0
            if float_percentage > 95:
                availability_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive',
                    ['substantial'])
                p1_parts.append(f"Nearly all of the company's <strong>{share_data.get('Shares Outstanding', 'N/A')}</strong> shares are publicly available as float, indicating {availability_descriptor} liquidity with no major amount locked up.")
            else:
                locked_up_pct = 100 - float_percentage
                control_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.neutral',
                    ['closely'])
                p1_parts.append(f"About <strong>{locked_up_pct:.1f}%</strong> of the company's shares are {control_descriptor} held by insiders or strategic investors, with the remaining <strong>{share_data.get('Shares Float', 'N/A')}</strong> available for public trading.")
            
            if shares_float_raw > 50_000_000:
                liquidity_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive',
                    ['excellent'])
                p1_parts.append(f"Because the float is high, investors can typically trade this stock without causing significant price shifts, providing {liquidity_descriptor} market liquidity.")
            
            caution_phrase = get_variation(content_library, 'dividends_shareholders.transition_words.contrast',
                ['However'])
            p1_parts.append(f"{caution_phrase}, investors should be aware that the company could issue more shares, potentially diluting the value of existing stock.")
        else:
            limitation_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.negative',
                ['limited'])
            p1_parts.append(f"Information on the total number of shares and the publicly traded float was not available, which creates {limitation_descriptor} understanding of the stock's liquidity and ownership structure.")

        # --- 4. Paragraph 2: Ownership Structure Analysis (with content library variations) ---
        p2_parts = []
        
        ownership_intro = get_variation(content_library, 'dividends_shareholders.transition_words.continuation',
            ['Furthermore']) + ", ownership distribution patterns reveal strategic positioning."
        p2_parts.append(ownership_intro)
        
        ownership_narrative = ""
        if insider_own_raw is not None:
            ownership_level = "very little" if insider_own_raw < 0.01 else "a small amount" if insider_own_raw < 0.05 else "a significant stake"
            implication = "meaning they may not have substantial 'skin in the game' if the company struggles" if insider_own_raw < 0.01 else "which helps align their interests with shareholders"
            alignment_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive' if insider_own_raw >= 0.01 else 'dividends_shareholders.performance_descriptors.negative',
                ['strong' if insider_own_raw >= 0.01 else 'limited'])
            ownership_narrative += f"Executives and major shareholders own <strong>{ownership_level}</strong> of the company ({share_data.get('Insider Ownership', 'N/A')}), {implication}, indicating {alignment_descriptor} management alignment. "
        
        if inst_own_raw is not None:
            inst_level = "also small" if inst_own_raw < 0.30 else "significant" if inst_own_raw > 0.7 else "healthy"
            if inst_own_raw < 0.30:
                confidence_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.negative',
                    ['limited'])
                inst_implication = f"This {confidence_descriptor} institutional presence is much less than the averages found in widely held stocks. If big-money investors are avoiding the stock, it could be due to concerns about performance or simply a lack of focus on the company."
            else:
                confidence_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive',
                    ['robust'])
                inst_implication = f"This level of institutional backing provides a {confidence_descriptor} degree of stability and confidence in the stock."
            ownership_narrative += f"The level of ownership by institutions is <strong>{inst_level}</strong>, coming in at <strong>{share_data.get('Institutional Ownership', 'N/A')}</strong>. {inst_implication}"
        
        if ownership_narrative:
            p2_parts.append(ownership_narrative)

        # --- 5. Paragraph 3: Short Interest and Strategic Synthesis (with content library variations) ---
        p3_parts = []
        
        short_intro = get_variation(content_library, 'dividends_shareholders.transition_words.causation',
            ['Additionally']) + ", short interest analysis provides market sentiment insights."
        p3_parts.append(short_intro)
        
        short_narrative = ""
        if shares_short_raw is not None and short_float_raw is not None:
            if short_float_raw > 0.10:
                sentiment_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.negative',
                    ['significant'])
                short_level_text = f"a {sentiment_descriptor} portion of the market is betting against the stock, indicating high perceived risk"
            elif short_float_raw > 0.03:
                sentiment_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.neutral',
                    ['notable'])
                short_level_text = f"there is a {sentiment_descriptor} level of bearish sentiment"
            else:
                sentiment_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive',
                    ['minimal'])
                short_level_text = f"bears show {sentiment_descriptor} concern for the company"

            monitoring_phrase = get_variation(content_library, 'dividends_shareholders.transition_words.emphasis',
                ['Importantly'])
            short_narrative = f"At the current level of <strong>{short_data.get('Shares Short', 'N/A')}</strong> shorted shares ({short_data.get('Short % of Float', 'N/A')} of the float), market sentiment suggests that {short_level_text}. {monitoring_phrase}, watch for changes in short interest, as a sharp increase may indicate that more investors are becoming doubtful. Conversely, very low short interest during positive news can sometimes discourage a 'short squeeze'."
            p3_parts.append(short_narrative)
        
        # Strategic synthesis with content library variations
        synthesis = ""
        if (shares_float_raw is not None and shares_float_raw > 50_000_000) and (inst_own_raw is not None and inst_own_raw < 0.30):
            liquidity_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive',
                ['excellent'])
            growth_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.negative',
                ['limited'])
            synthesis = f"When we look at all of these factors, we can see that while the stock has {liquidity_descriptor} liquidity and is easy to trade, its price may see {growth_descriptor} sustained growth unless it gains stronger support from large institutional traders or company insiders."
        elif (insider_own_raw is not None and insider_own_raw > 0.10) and (inst_own_raw is not None and inst_own_raw > 0.70):
            confidence_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive',
                ['strong'])
            foundation_descriptor = get_variation(content_library, 'dividends_shareholders.performance_descriptors.positive',
                ['solid'])
            synthesis = f"Overall, the combination of high insider and institutional ownership suggests {confidence_descriptor} internal and external confidence, creating a {foundation_descriptor} foundation for the stock's stability and potential growth."
        
        if synthesis:
            p3_parts.append(synthesis)

        # --- 6. Assemble Final HTML ---
        paragraph1_html = '<p>' + ' '.join(p1_parts) + '</p>' if p1_parts else ''
        paragraph2_html = '<p>' + ' '.join(p2_parts) + '</p>' if p2_parts else ''
        paragraph3_html = '<p>' + ' '.join(p3_parts) + '</p>' if p3_parts else ''
        full_narrative_html = f'<div class="narrative">{paragraph1_html}{paragraph2_html}{paragraph3_html}</div>'
        
        # Combine data for the table view (exact html_components approach)
        combined_data_for_table = {**share_data, **short_data}
        table_content = generate_wordpress_metrics_section_content(combined_data_for_table, ticker, content_library)
        
        html_parts = []
        html_parts.append(f"<h3>{section_intro}</h3>")
        html_parts.append(full_narrative_html)
        
        return ''.join(html_parts) + table_content

    except Exception as e:
        print(f"Warning: Error in WordPress share statistics generation: {e}. Using fallback.")
        return hc.generate_share_statistics_html(ticker, rdata)

def generate_wordpress_stock_price_statistics_html(ticker, rdata, content_library=None):
    """
    Generate WordPress stock price statistics content using exact html_components algorithms
    with comprehensive content library variations for professional price analysis.
    """
    try:
        if not content_library:
            return hc.generate_stock_price_statistics_html(ticker, rdata)

        # --- 1. Data Extraction and Parsing (exact html_components approach) ---
        stats_data = rdata.get('stock_price_stats_data', {})

        # Get raw values for logic (exact variable names from algorithm)
        high_52wk = hc._safe_float(stats_data.get('52 Week High'), default=None)
        low_52wk = hc._safe_float(stats_data.get('52 Week Low'), default=None)
        sma_50 = hc._safe_float(rdata.get('sma_50'), default=None)
        sma_200 = hc._safe_float(rdata.get('sma_200'), default=None)
        beta = hc._safe_float(stats_data.get('Beta'), default=None)
        volatility = hc._safe_float(rdata.get('volatility'), default=None)

        # Get formatted values for display (exact formatting from algorithm)
        high_52wk_fmt = hc.format_html_value(high_52wk, 'currency', ticker=ticker)
        low_52wk_fmt = hc.format_html_value(low_52wk, 'currency', ticker=ticker)
        sma_50_fmt = hc.format_html_value(sma_50, 'currency', ticker=ticker)
        sma_200_fmt = hc.format_html_value(sma_200, 'currency', ticker=ticker)
        beta_fmt = hc.format_html_value(beta, 'ratio')
        volatility_fmt = hc.format_html_value(volatility, 'percent_direct', 1)

        # Add volatility to stats_data for table display if not present (exact algorithm logic)
        if 'Volatility (30d Ann.)' not in stats_data and volatility_fmt != "N/A":
            stats_data['Volatility (30d Ann.)'] = f"{volatility_fmt} {hc.get_icon('stats')}"

        # Get section introduction with content library variations
        section_intro = get_variation(content_library, 'stock_price_statistics.section_introductions',
            ['Stock Price Statistics Overview'])

        p1_parts = []
        p2_parts = []

        # --- 2. Narrative Generation: Paragraph 1 (Range & MAs) with content library variations ---
        if high_52wk is not None and low_52wk is not None:
            # Use original algorithm text with small variations
            p1_parts.append(f"When looking at the price range over the past year, the stock has seen a high of <strong>{high_52wk_fmt}</strong> and a low of <strong>{low_52wk_fmt}</strong>.")
            
            range_pct = (high_52wk - low_52wk) / low_52wk if low_52wk > 0 else 0
            if range_pct > 0.5:
                range_assessment = get_variation(content_library, 'stock_price_statistics.price_range.wide_range',
                    ['This wide gap tells us the stock has been through significant fluctuations, likely influenced by market sentiment or company-specific news.'])
            elif range_pct > 0.25:
                range_assessment = get_variation(content_library, 'stock_price_statistics.price_range.moderate_range',
                    ['This moderate gap indicates the stock has experienced notable price swings over the year.'])
            else:
                range_assessment = get_variation(content_library, 'stock_price_statistics.price_range.narrow_range',
                    ['This relatively narrow gap suggests the stock has traded within a more stable range over the past year.'])
            # Extract just the descriptive part from variations that have different structure
            if '{low_52wk_fmt}' in range_assessment:
                range_assessment = "This gap suggests the stock has experienced notable price movements during the period."
            p1_parts.append(range_assessment)

        if sma_50 is not None and sma_200 is not None:
            diff_pct = abs(sma_50 - sma_200) / sma_200 if sma_200 > 0 else 0
            proximity = "slightly" if diff_pct < 0.05 else ""
            
            if sma_50 < sma_200:
                p1_parts.append(f"Currently, the 50-day moving average stands at <strong>{sma_50_fmt}</strong>, which is {proximity} below the 200-day moving average of <strong>{sma_200_fmt}</strong>.")
                p1_parts.append("This setup may signal a short-term pullback or consolidation phase, especially for technical traders tracking momentum and trend direction.")
            else:
                p1_parts.append(f"Currently, the 50-day moving average at <strong>{sma_50_fmt}</strong> is {proximity} above the 200-day moving average of <strong>{sma_200_fmt}</strong>.")
                p1_parts.append("This 'golden cross' setup is often viewed as a bullish signal, indicating positive long-term momentum.")
        
        # --- 3. Narrative Generation: Paragraph 2 (Volatility & Beta) with content library variations ---
        if beta is not None:
            beta_move_pct = abs(beta - 1) * 100
            if beta > 1.2:
                beta_assessment = get_variation(content_library, 'stock_price_statistics.beta_analysis.high_beta',
                    [f'The stock carries a beta of <strong>{beta_fmt}</strong>, which means it tends to move more sharply than the broader market—about {beta_move_pct:.0f}% more volatile.'])
            elif beta < 0.8 and beta > 0:
                beta_assessment = get_variation(content_library, 'stock_price_statistics.beta_analysis.low_beta',
                    [f'With a beta of <strong>{beta_fmt}</strong>, the stock tends to be less volatile than the broader market, moving about {beta_move_pct:.0f}% less.'])
            else:
                beta_assessment = get_variation(content_library, 'stock_price_statistics.beta_analysis.moderate_beta',
                    [f'A beta of <strong>{beta_fmt}</strong> suggests the stock\'s movement is generally in line with the broader market.'])
            
            # Extract just the beta value and use original algorithm text
            if '{beta_fmt}' in beta_assessment:
                if beta > 1.2:
                    beta_assessment = f"The stock carries a beta of <strong>{beta_fmt}</strong>, which means it tends to move more sharply than the broader market—about {beta_move_pct:.0f}% more volatile."
                elif beta < 0.8 and beta > 0:
                    beta_assessment = f"With a beta of <strong>{beta_fmt}</strong>, the stock tends to be less volatile than the broader market, moving about {beta_move_pct:.0f}% less."
                else:
                    beta_assessment = f"A beta of <strong>{beta_fmt}</strong> suggests the stock's movement is generally in line with the broader market."
            p2_parts.append(beta_assessment)
        
        if volatility is not None:
            volatility_desc = "high" if volatility > 40 else "moderate" if volatility > 20 else "low"
            if beta is not None:
                vol_combination = f"Combined with a {volatility_desc} 30-day annualized volatility of <strong>{volatility_fmt}</strong>, it's clear this stock sees frequent price swings."
            else:
                vol_combination = f"A 30-day annualized volatility of <strong>{volatility_fmt}</strong> indicates the stock experiences {volatility_desc} price swings."
            
            p2_parts.append(vol_combination)

        if beta is not None or volatility is not None:
            risk_conclusion = "For investors, this means potential for gains, but also higher downside risk. These indicators matter when deciding position sizing or entry timing, especially if you're managing a portfolio that balances stability with growth exposure."
            p2_parts.append(risk_conclusion)

        # --- 4. Assemble Final HTML ---
        paragraph1 = '<p>' + ' '.join(p1_parts) + '</p>' if p1_parts else ''
        paragraph2 = '<p>' + ' '.join(p2_parts) + '</p>' if p2_parts else ''
        narrative_html = f'<div class="narrative">{paragraph1}{paragraph2}</div>' if (p1_parts or p2_parts) else ''
        
        table_html = generate_wordpress_metrics_section_content(stats_data, ticker, content_library)

        html_parts = []
        html_parts.append(f"<h3>{section_intro}</h3>")
        html_parts.append(narrative_html)
        
        return ''.join(html_parts) + table_html

    except Exception as e:
        print(f"Warning: Error in WordPress stock price statistics generation: {e}. Using fallback.")
        return hc.generate_stock_price_statistics_html(ticker, rdata)

def generate_wordpress_short_selling_info_html(ticker, rdata, content_library=None):
    """
    Generate WordPress short selling info content using exact html_components algorithms
    with comprehensive content library variations for professional short interest analysis.
    """
    try:
        if not content_library:
            return hc.generate_short_selling_info_html(ticker, rdata)

        # --- 1. Data Extraction and Parsing (exact html_components approach) ---
        short_data = rdata.get('short_selling_data', {})
        if not isinstance(short_data, dict) or not short_data:
            return hc._generate_error_html("Short Selling Information", "No short selling data available.")

        # Helper to parse formatted values like '$22M' or '1.20%' into numbers (exact algorithm)
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
                # Handle 'x' in ratios (exact algorithm logic)
                return float(cleaned_str.replace('X', '')) * multiplier
            except (ValueError, TypeError):
                return None

        # Parse raw values for logic (exact variable names from algorithm)
        shares_short_val = _parse_short_value(short_data.get('Shares Short'))
        short_ratio_val = _parse_short_value(short_data.get('Short Ratio (Days To Cover)'))
        short_float_pct_val = _parse_short_value(short_data.get('Short % of Float'))
        shares_short_prior_val = _parse_short_value(short_data.get('Shares Short (Prior Month)'))
        
        # Get formatted values for display (exact algorithm approach)
        shares_short_fmt = short_data.get('Shares Short', 'N/A')
        short_ratio_fmt = short_data.get('Short Ratio (Days To Cover)', 'N/A')
        short_float_pct_fmt = short_data.get('Short % of Float', 'N/A')
        shares_short_prior_fmt = short_data.get('Shares Short (Prior Month)', 'N/A')

        # Get section introduction with content library variations
        section_intro = get_variation(content_library, 'short_selling_info.section_introductions',
            ['Short Selling Information'])

        # --- 2. Dynamic Narrative Generation (exact algorithm with variations) ---
        p1_parts = []
        p2_parts = []

        # Paragraph 1: Short Interest and Days to Cover (exact algorithm logic)
        if shares_short_val is not None and short_ratio_val is not None:
            # Short interest opening with variations - format the template variables
            short_intro = get_variation(content_library, 'short_selling_info.short_interest_openings',
                [f'There is currently <strong>{shares_short_fmt}</strong> worth of short interest in {ticker}'])
            # Replace template variables if they exist
            short_intro = short_intro.replace('{shares_short_fmt}', shares_short_fmt).replace('{ticker}', ticker)
            p1_parts.append(f"{short_intro}, and the short ratio (or days to cover) is <strong>{short_ratio_fmt}</strong>.")
            
            days_to_cover = round(short_ratio_val)
            if days_to_cover <= 1:
                days_text = "about one day"
            elif days_to_cover <= 3:
                days_text = f"around {days_to_cover} days"
            else:
                days_text = f"several days"
            
            p1_parts.append(f"This means that at the stock's recent average trading volume, it would take {days_text} for all short positions to be covered.")
            
            if short_ratio_val < 3:
                squeeze_assessment = get_variation(content_library, 'short_selling_info.days_to_cover_analysis.low_coverage',
                    ['This low level suggests that short sellers do not currently have significant control over the stock\'s price, and the risk of a prolonged \'short squeeze\' is relatively low.'])
            elif short_ratio_val > 10:
                squeeze_assessment = get_variation(content_library, 'short_selling_info.days_to_cover_analysis.high_coverage',
                    ['This high level indicates it would take a long time for short sellers to buy back their shares, which could lead to extreme volatility or a powerful \'short squeeze\' if the stock\'s price starts to rise unexpectedly.'])
            else:
                squeeze_assessment = get_variation(content_library, 'short_selling_info.days_to_cover_analysis.moderate_coverage',
                    ['This moderate level indicates a balance between bearish bets and the market\'s ability to absorb them without extreme volatility.'])
            p1_parts.append(squeeze_assessment)
        else:
            p1_parts.append("Data on the current short interest and days to cover is not fully available, making it difficult to assess the immediate influence of short sellers.")

        # Paragraph 2: Short % of Float and Trend (exact algorithm logic)
        if short_float_pct_val is not None:
            if short_float_pct_val < 0.02:  # < 2%
                float_interp_key = "low_percentage"
                float_interp = "a very low percentage of the available shares are being shorted, indicating a general lack of bearish sentiment among investors."
            elif short_float_pct_val < 0.10:  # < 10%
                float_interp_key = "moderate_percentage"
                float_interp = "a moderate percentage of the stock is being shorted, showing some bearish sentiment but not an extreme level."
            else:  # > 10%
                float_interp_key = "high_percentage"
                float_interp = "a high percentage of the float is being shorted, signaling significant bearish conviction from a portion of the market."

            float_analysis = get_variation(content_library, f'short_selling_info.float_percentage_analysis.{float_interp_key}',
                [float_interp])
            # Extract meaningful part if it contains template variables
            if '{short_float_pct_fmt}' in float_analysis:
                float_analysis = float_interp
            else:
                # Replace template variables if they exist
                float_analysis = float_analysis.replace('{short_float_pct_fmt}', short_float_pct_fmt)
            p2_parts.append(f"With <strong>{short_float_pct_fmt}</strong> of the public float sold short, {float_analysis}")
        
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
                market_confidence = "Because the amount of investors shorting is generally low, the market tends to feel more confident and the risks of price swings from sudden short-covering activities are reduced."
            else:
                market_confidence = "With notable short interest, investors should be aware of potential volatility spikes, which could be triggered by news events that force short sellers to cover their positions."
            p2_parts.append(market_confidence)

        # --- 3. Assemble Final HTML ---
        paragraph1 = '<p>' + ' '.join(p1_parts) + '</p>' if p1_parts else ''
        paragraph2 = '<p>' + ' '.join(p2_parts) + '</p>' if p2_parts else ''
        narrative_html = f'<div class="narrative">{paragraph1}{paragraph2}</div>' if (p1_parts or p2_parts) else ''
        
        table_html = generate_wordpress_metrics_section_content(short_data, ticker, content_library)

        html_parts = []
        html_parts.append(f"<h3>{section_intro}</h3>")
        html_parts.append(narrative_html)
        
        return ''.join(html_parts) + table_html

    except Exception as e:
        print(f"Warning: Error in WordPress short selling info generation: {e}. Using fallback.")
        return hc.generate_short_selling_info_html(ticker, rdata)

def generate_wordpress_analyst_insights_html(ticker, rdata, content_library=None):
    """
    Generate WordPress analyst insights content using content library variations.
    Falls back to original function if content library is not available.
    """
    try:
        if not content_library:
            # Fallback to original function if no content library
            return hc.generate_analyst_insights_html(ticker, rdata)

        # --- 1. Data Extraction ---
        analyst_data = rdata.get('analyst_info_data', {})
        if not isinstance(analyst_data, dict):
            analyst_data = {}

        # Get formatted values
        recommendation = hc.format_html_value(analyst_data.get('Recommendation'), 'factor')
        mean_target_fmt = hc.format_html_value(analyst_data.get('Mean Target Price'), 'currency', ticker=ticker)
        high_target_fmt = hc.format_html_value(analyst_data.get('High Target Price'), 'currency', ticker=ticker)
        low_target_fmt = hc.format_html_value(analyst_data.get('Low Target Price'), 'currency', ticker=ticker)
        num_analysts_fmt = hc.format_html_value(analyst_data.get('Number of Analyst Opinions'), 'integer')
        current_price = hc._safe_float(rdata.get('current_price'))
        current_price_fmt = hc.format_html_value(current_price, 'currency', ticker=ticker)

        # Calculate potential
        potential_summary = ""
        mean_potential_fmt = "N/A"
        target_range_fmt = f"{low_target_fmt} - {high_target_fmt}" if low_target_fmt != 'N/A' and high_target_fmt != 'N/A' else "N/A"

        mean_target_val = hc._safe_float(analyst_data.get('Mean Target Price'))
        if mean_target_val is not None and current_price is not None and current_price > 0:
            potential = ((mean_target_val - current_price) / current_price) * 100
            mean_potential_fmt = hc.format_html_value(potential, 'percent_direct', 1)
            potential_direction = "upside" if potential > 0 else "downside" if potential < 0 else "change"

        # --- 2. Dynamic Narrative Generation with Variations ---

        # Section introduction
        section_intro = get_variation(content_library, 'analysts_insights.section_introductions',
            ['Analyst Insights & Consensus'])

        # Consensus introduction
        consensus_intro = get_variation(content_library, 'analysts_insights.consensus_introductions',
            [f'Wall Street analysts provide valuable insights into {ticker}\'s investment potential'])

        # Recommendation analysis
        rec_key = "buy"  # default
        if recommendation.lower() in ['strong buy', 'buy']:
            rec_key = "strong_buy" if 'strong' in recommendation.lower() else "buy"
        elif recommendation.lower() in ['hold', 'neutral']:
            rec_key = "hold"
        elif recommendation.lower() in ['sell', 'underperform']:
            rec_key = "sell"

        recommendation_analysis = safe_format(get_variation(content_library, f'analysts_insights.recommendation_analysis.{rec_key}',
            [f'The consensus recommendation reflects confidence in {ticker}\'s prospects']), ticker=ticker, recommendation=recommendation)

        # Analyst count context
        analyst_count_context = safe_format(get_variation(content_library, 'analysts_insights.analyst_count_context',
            [f'This consensus is based on input from {num_analysts_fmt} analysts']), num_analysts_fmt=num_analysts_fmt)

        # Target price analysis
        target_key = "near_current"
        if mean_target_val is not None and current_price is not None:
            diff_pct = abs((mean_target_val - current_price) / current_price) * 100
            if diff_pct > 15:
                target_key = "above_current" if mean_target_val > current_price else "below_current"

        target_analysis = get_variation(content_library, f'analysts_insights.target_price_analysis.{target_key}',
            [f'with an average target price of <strong>{mean_target_fmt}</strong>'])

        # Range analysis
        range_analysis = get_variation(content_library, 'analysts_insights.range_analysis',
            [f'Individual targets range from <strong>{low_target_fmt}</strong> to <strong>{high_target_fmt}</strong>'])

        # Valuation context
        valuation_context = get_variation(content_library, 'analysts_insights.valuation_context',
            [f'This consensus provides important context for evaluating {ticker}\'s current market valuation']).format(ticker=ticker, recommendation=recommendation)

        # Cautionary note
        cautionary_note = get_variation(content_library, 'analysts_insights.cautionary_notes',
            [f'Remember that analyst recommendations can change rapidly with new information or market conditions'])

        # --- 3. Generate Grid HTML ---
        grid_html = hc.generate_analyst_grid_html(analyst_data)

        # --- 4. Assemble Final HTML ---
        html_parts = []

        # Section header
        html_parts.append(f"<h3>{section_intro}</h3>")

        # Narrative content
        narrative_parts = []
        narrative_parts.append(consensus_intro)
        narrative_parts.append(recommendation_analysis)
        narrative_parts.append(analyst_count_context)

        if mean_target_fmt != 'N/A':
            narrative_parts.append(target_analysis.format(
                mean_target_fmt=mean_target_fmt,
                potential_direction="upside" if mean_target_val and mean_target_val > current_price else "downside",
                mean_potential_fmt=mean_potential_fmt
            ))

        if target_range_fmt != 'N/A':
            narrative_parts.append(range_analysis.format(
                low_target_fmt=low_target_fmt,
                high_target_fmt=high_target_fmt
            ))

        narrative_parts.append(valuation_context.format(ticker=ticker))
        narrative_parts.append(cautionary_note)

        html_parts.append(f"""
        <div class="narrative">
            <p>{" ".join(narrative_parts)}</p>
        </div>
        """)

        return ''.join(html_parts) + grid_html

    except Exception as e:
        print(f"Warning: Error in WordPress analyst insights generation: {e}. Using fallback.")
        return hc.generate_analyst_insights_html(ticker, rdata)

def generate_wordpress_technical_analysis_summary_html(ticker, rdata, content_library=None):
    """
    Generate DETAILED WordPress technical analysis with comprehensive sections.
    Provides in-depth analysis similar to professional trading reports.
    """
    try:
        if not content_library:
            return hc.generate_technical_analysis_summary_html(ticker, rdata)

        # --- 1. Data Extraction ---
        profile_data = rdata.get('profile_data', {})
        detailed_ta_data = rdata.get('detailed_ta_data', {})
        
        # Get technical indicators
        current_price = hc._safe_float(rdata.get('current_price'))
        sma20 = hc._safe_float(detailed_ta_data.get('SMA_20'))
        # Use yfinance SMA values from rdata instead of calculated ones
        sma50 = hc._safe_float(rdata.get('sma_50'))
        sma200 = hc._safe_float(rdata.get('sma_200'))
        rsi = hc._safe_float(detailed_ta_data.get('RSI_14'))
        macd_hist = hc._safe_float(detailed_ta_data.get('MACD_Hist'))
        macd_line = hc._safe_float(detailed_ta_data.get('MACD_Line'))
        macd_signal = hc._safe_float(detailed_ta_data.get('MACD_Signal'))
        bb_upper = hc._safe_float(detailed_ta_data.get('BB_Upper'))
        bb_lower = hc._safe_float(detailed_ta_data.get('BB_Lower'))
        volume_current = hc._safe_float(detailed_ta_data.get('Volume'))
        volume_avg = hc._safe_float(detailed_ta_data.get('Volume_Avg'))
        
        # Get 52-week high/low from profile
        week_52_high = hc._safe_float(profile_data.get('52 Week High'))
        week_52_low = hc._safe_float(profile_data.get('52 Week Low'))
        
        # Format values
        current_price_fmt = hc.format_html_value(current_price, 'currency', ticker=ticker)
        sma20_fmt = hc.format_html_value(sma20, 'currency', ticker=ticker)
        sma50_fmt = hc.format_html_value(sma50, 'currency', ticker=ticker)
        sma200_fmt = hc.format_html_value(sma200, 'currency', ticker=ticker)
        bb_upper_fmt = hc.format_html_value(bb_upper, 'currency', ticker=ticker)
        bb_lower_fmt = hc.format_html_value(bb_lower, 'currency', ticker=ticker)
        week_52_high_fmt = hc.format_html_value(week_52_high, 'currency', ticker=ticker)
        week_52_low_fmt = hc.format_html_value(week_52_low, 'currency', ticker=ticker)
        
        rsi_fmt = f"{rsi:.1f}" if rsi is not None else "N/A"
        
        # Get 15-day change
        change_15d = rdata.get('change_15d', 0)
        change_15d_fmt = hc.format_html_value(change_15d, 'percent_direct', ticker=ticker)
        
        # Determine trend status - FIXED: Check multiple moving averages
        trend_status = "SIDEWAYS"
        trend_desc = "BUT SHOWS MIXED SIGNALS"
        
        if current_price and sma20 and sma50 and sma200:
            above_20 = current_price > sma20
            above_50 = current_price > sma50
            above_200 = current_price > sma200
            
            if above_20 and above_50 and above_200:
                trend_status = "BULLISH"
                if rsi and rsi > 70:
                    trend_desc = "BUT SHOWS SIGNS OF SLOWING"
                else:
                    trend_desc = "WITH STRONG MOMENTUM"
            elif not above_20 and not above_50 and not above_200:
                trend_status = "BEARISH"
                trend_desc = "UNDER PRESSURE"
            elif above_200 and not above_20:
                trend_status = "MIXED"
                trend_desc = "WITH CONFLICTING SIGNALS"
        
        # Determine RSI state
        rsi_state = "neutral"
        rsi_interpretation = "balanced momentum conditions"
        if rsi:
            if rsi > 70:
                rsi_state = "overbought"
                rsi_interpretation = f"flashing a strong overbought signal"
            elif rsi < 30:
                rsi_state = "oversold"
                rsi_interpretation = "showing oversold conditions"
        
        # Determine MACD state
        macd_state = "neutral"
        macd_interpretation = "showing mixed signals"
        if macd_hist is not None:
            if macd_hist > 0:
                macd_state = "bullish"
                macd_interpretation = "confirming bullish momentum"
            else:
                macd_state = "bearish"
                macd_interpretation = "suggesting that the upward momentum is beginning to fade"
        
        # Volume analysis
        volume_state = "declining"
        volume_concern = "which is a red flag for trend sustainability"
        if volume_current and volume_avg:
            if volume_current > volume_avg:
                volume_state = "increasing"
                volume_concern = "which confirms buying interest"
            else:
                volume_concern = "which is a red flag for trend sustainability"
        
        # --- 2. Generate Detailed Narrative Sections ---
        html_parts = []
        
        # Header
        html_parts.append(f"<h3>Technical Analysis</h3>")
        
        # Headline
        html_parts.append(f'<p><strong>CURRENT PRICE: {current_price_fmt} | TREND: {trend_status} {trend_desc}</strong></p>')
        
        html_parts.append('<div class="narrative">')
        
        # Introduction - determine context based on 15-day performance
        if change_15d > 5:
            # Bullish run - use content library
            intro_text = get_variation(content_library, 'technical_analysis_summary.intro_paragraphs.bullish_run',
                [f"The stock has been on a notable run, gaining {change_15d_fmt} in just 15 days, but several technical signs suggest we should be cautious about chasing this momentum. Let's break down what the charts are telling us and how we can position ourselves."])
        elif change_15d < -5:
            # Bearish pressure - use content library
            intro_text = get_variation(content_library, 'technical_analysis_summary.intro_paragraphs.bearish_pressure',
                [f"The stock has faced downward pressure, losing {change_15d_fmt} in the last 15 days. We need to analyze the technicals to see if this is a buying opportunity or a warning of further declines. Let's break down the key levels."])
        else:
            # Sideways - use content library
            intro_text = get_variation(content_library, 'technical_analysis_summary.intro_paragraphs.sideways_movement',
                [f"The stock has been trading sideways recently. Let's dive into the technical indicators to identify the next potential move and key trading levels."])
        
        html_parts.append(f"<p>{intro_text}</p>")
        
        # Section 1: Trend Strength - FIXED: Dynamic section title and accurate narratives
        # Determine if price is above 20-day SMA for support/resistance identification
        above_20_sma = current_price and sma20 and current_price > sma20
        
        if trend_status == "BULLISH":
            section_title = "Trend Strength – Still Bullish"
        elif trend_status == "BEARISH":
            section_title = "Trend Strength – Bearish Pressure"
        else:
            section_title = "Trend Strength – Mixed Signals"
        
        html_parts.append(f"<p><strong>{section_title}</strong></p>")
        
        if trend_status == "BULLISH":
            trend_text = get_variation(content_library, 'technical_analysis_summary.trend_analysis.bullish',
                [f"{ticker} is trading above its key moving averages, which confirms the uptrend remains intact."])
        elif trend_status == "MIXED":
            trend_text = get_variation(content_library, 'technical_analysis_summary.trend_analysis.mixed',
                [f"{ticker} is in a mixed technical state, holding above the long-term 200-day average but trading below shorter-term averages, signaling a potential pullback within an uptrend."])
        else:
            trend_text = get_variation(content_library, 'technical_analysis_summary.trend_analysis.bearish',
                [f"{ticker} is in a bearish trend, trading below its key moving averages, which signals caution."])
        
        # FIXED: Correctly identify support vs resistance based on price position
        sma_role = "acting as immediate dynamic support" if above_20_sma else "acting as immediate overhead resistance"
        html_parts.append(f"<p>{trend_text} The 20-day SMA at {sma20_fmt} is {sma_role}.</p>")
        
        # What This Means for Traders
        html_parts.append("<p><strong>What This Means for Traders?</strong></p>")
        if trend_status == "BULLISH":
            trader_text = get_variation(content_library, 'technical_analysis_summary.trader_takeaways.bullish',
                [f"As long as {ticker} holds above the 20-day SMA ({sma20_fmt}), the bullish momentum could continue. However, a rapid rise can push the stock far from its averages, increasing the risk of a pullback."])
        elif trend_status == "MIXED":
            if above_20_sma:
                trader_text = get_variation(content_library, 'technical_analysis_summary.trader_takeaways.mixed_above',
                    [f"While {ticker} holds above the 20-day SMA ({sma20_fmt}), watch for a break above the 50-day average to confirm renewed bullish momentum."])
            else:
                trader_text = get_variation(content_library, 'technical_analysis_summary.trader_takeaways.mixed_below',
                    [f"The 20-day SMA ({sma20_fmt}) is acting as resistance. A break above this level would signal short-term strength, while failure could lead to further consolidation or decline."])
        else:
            trader_text = get_variation(content_library, 'technical_analysis_summary.trader_takeaways.bearish',
                [f"The 20-day SMA ({sma20_fmt}) is now acting as overhead resistance. As long as the price stays below this level, the bearish trend is likely to continue."])
        html_parts.append(f"<p>{trader_text}</p>")
        
        # Section 2: Momentum Check
        html_parts.append("<p><strong>Momentum Check – Time to Be Cautious</strong></p>")
        
        # RSI analysis - use content library
        if rsi_state == "overbought":
            rsi_text = get_variation(content_library, 'technical_analysis_summary.momentum_analysis.overbought',
                [f"The RSI at {rsi_fmt} is {rsi_interpretation}"])
        elif rsi_state == "oversold":
            rsi_text = get_variation(content_library, 'technical_analysis_summary.momentum_analysis.oversold',
                [f"The RSI at {rsi_fmt} shows {rsi_interpretation}"])
        else:
            rsi_text = get_variation(content_library, 'technical_analysis_summary.momentum_analysis.neutral',
                [f"The RSI at {rsi_fmt} is {rsi_interpretation}"])
        
        # MACD analysis - use content library
        if macd_state == "bullish":
            macd_text = get_variation(content_library, 'technical_analysis_summary.macd_signals.bullish',
                ["the MACD histogram is positive, confirming the upward momentum is still in play"])
        else:
            macd_text = get_variation(content_library, 'technical_analysis_summary.macd_signals.bearish',
                ["the MACD histogram is negative, suggesting that the upward momentum is beginning to fade"])
        
        html_parts.append(f"<p>{rsi_text}. At the same time, {macd_text}.</p>")
        
        # Trading Strategy
        html_parts.append("<p><strong>Trading Strategy:</strong></p>")
        if rsi_state == "overbought":
            strategy_text = get_variation(content_library, 'technical_analysis_summary.trading_strategies.overbought',
                ["Aggressive traders might consider taking partial profits. Conservative traders should wait for the RSI to cool below 70 before considering new positions."])
        elif rsi_state == "oversold":
            strategy_text = get_variation(content_library, 'technical_analysis_summary.trading_strategies.oversold',
                ["This oversold reading suggests a potential bounce. Aggressive traders might look for a short-term buy signal, while conservative traders should wait for the RSI to cross back above 30 to confirm a reversal."])
        else:
            strategy_text = get_variation(content_library, 'technical_analysis_summary.trading_strategies.neutral',
                ["Current momentum levels provide flexibility for both entry and exit strategies. Watch for confirmation signals before making moves."])
        html_parts.append(f"<p>{strategy_text}</p>")
        
        # Section 3: Bollinger Bands
        html_parts.append("<p><strong>Bollinger Bands – Testing Key Levels</strong></p>")
        bb_position = "middle"
        if current_price and bb_upper and bb_lower:
            bb_mid = (bb_upper + bb_lower) / 2
            if current_price > bb_upper:
                bb_text = get_variation(content_library, 'technical_analysis_summary.bollinger_bands_analysis.above_upper',
                    [f"The price is 'walking the band,' trading above the upper Bollinger Band ({bb_upper_fmt}). This is a sign of a very strong trend, but also increases the risk of a sharp snap-back if momentum stalls."])
            elif current_price < bb_lower:
                bb_text = get_variation(content_library, 'technical_analysis_summary.bollinger_bands_analysis.below_lower',
                    [f"The price has broken below the lower Bollinger Band ({bb_lower_fmt}), indicating strong selling pressure and a potential breakdown. Watch for signs of capitulation or reversal."])
            elif current_price > bb_mid:
                bb_text = get_variation(content_library, 'technical_analysis_summary.bollinger_bands_analysis.middle_range',
                    ["The stock is trading comfortably in the upper half of its Bollinger Bands (between the 20-day SMA and the upper band), which is a sign of underlying strength."])
            else:
                bb_text = f"The stock is trading in the lower half of its Bollinger Bands, indicating potential support testing."
        else:
            bb_text = "Bollinger Band analysis is not available due to insufficient data."
        
        html_parts.append(f"<p>{bb_text}</p>")
        
        # Key Levels to Watch
        html_parts.append("<p><strong>Key Levels to Watch:</strong></p>")
        resistance_level = week_52_high_fmt if week_52_high else bb_upper_fmt
        html_parts.append(f"<p>Resistance: {resistance_level} (Recent High) &rarr; A breakout could push {ticker} higher.<br>")
        html_parts.append(f"Support: {sma20_fmt} (20-day SMA) &rarr; If this breaks, expect a test of {sma50_fmt}.</p>")
        
        # Section 4: Volume Trends
        html_parts.append("<p><strong>Volume Trends – Checking for Conviction</strong></p>")
        if volume_state == "declining":
            volume_text = get_variation(content_library, 'technical_analysis_summary.volume_analysis.weak_volume',
                ["While the stock has been rising, trading volume has been declining (below its 20-day average), which is a red flag for trend sustainability."])
        else:
            volume_text = get_variation(content_library, 'technical_analysis_summary.volume_analysis.neutral_volume',
                ["Trading volume is near its recent average, providing neutral confirmation of the current price action."])
        html_parts.append(f"<p>{volume_text}</p>")
        
        # Volume Concern
        html_parts.append("<p><strong>What's the Concern?</strong></p>")
        concern_text = get_variation(content_library, 'technical_analysis_summary.volume_concerns',
            ["Low volume rallies are prone to sharp reversals. If we don't see a surge in buying interest to confirm the move, a pullback becomes more likely."])
        html_parts.append(f"<p>{concern_text}</p>")
        
        # Section 5: Support & Resistance – Trading Plan
        html_parts.append("<p><strong>Support & Resistance – The Trading Plan</strong></p>")
        html_parts.append("<p><strong>Trading Plan:</strong></p>")
        html_parts.append(f"<p>✅&nbsp; <strong>If {ticker} holds above {sma20_fmt}</strong> &rarr; Bullish trend continues, next target {resistance_level}.<br>")
        html_parts.append(f"⚠️&nbsp; <strong>If it breaks below {sma20_fmt}</strong> &rarr; Expect a dip toward {sma50_fmt}.<br>")
        html_parts.append(f"🛑&nbsp; <strong>A drop below {sma50_fmt}</strong> &rarr; Could trigger a deeper correction to the 200-day SMA ({sma200_fmt}).</p>")
        
        # Section 6: Final Verdict
        html_parts.append("<p><strong>Final Verdict – Should You Buy, Hold, or Sell?</strong></p>")
        verdict_texts = [
            f"<strong>Short-Term Traders:</strong> Be cautious—RSI is {rsi_state} at {rsi_fmt}, and volume is weak. Consider locking in partial profits near {resistance_level} and waiting for a better entry near the 20-day SMA ({sma20_fmt}).",
            f"<strong>Short-Term Traders:</strong> With RSI at {rsi_fmt} ({rsi_state}) and weak volume, profit-taking is prudent. Look for re-entry opportunities around {sma20_fmt} support.",
            f"<strong>Short-Term Traders:</strong> The {rsi_state} RSI reading of {rsi_fmt} combined with declining volume suggests taking some chips off the table. Wait for {sma20_fmt} support test for better risk/reward."
        ]
        html_parts.append(f"<p>{get_variation(content_library, 'technical_analysis.verdict_short', verdict_texts)}</p>")
        
        longterm_texts = [
            f"<strong>Long-Term Investors:</strong> The long-term uptrend is valid as long as the price holds above the 200-day SMA ({sma200_fmt}). A pullback to the 50-day SMA ({sma50_fmt}) area could present a safer buying opportunity.",
            f"<strong>Long-Term Investors:</strong> Uptrend remains intact above {sma200_fmt} (200-day SMA). Patience for a {sma50_fmt} retest offers better entry points.",
            f"<strong>Long-Term Investors:</strong> As long as {sma200_fmt} support holds, the bullish structure persists. Consider accumulating near the {sma50_fmt} level on any pullback."
        ]
        html_parts.append(f"<p>{get_variation(content_library, 'technical_analysis.verdict_long', longterm_texts)}</p>")
        
        newbuyer_texts = [
            f"<strong>New Buyers:</strong> Avoid chasing the rally here. Wait for either a confirmed breakout above {resistance_level} with strong volume, or a pullback to the {sma20_fmt} area, which offers a better risk/reward entry.",
            f"<strong>New Buyers:</strong> Don't chase here. Either wait for {resistance_level} breakout on volume, or let it pull back to {sma20_fmt} for optimal entry.",
            f"<strong>New Buyers:</strong> Patience pays—wait for either volume-confirmed breakout above {resistance_level} or retracement to {sma20_fmt} support zone."
        ]
        html_parts.append(f"<p>{get_variation(content_library, 'technical_analysis.verdict_new', newbuyer_texts)}</p>")
        
        # Bottom Line
        html_parts.append("<p><strong>Bottom Line:</strong> The technicals suggest the rally may be running out of steam short-term. While the long-term trend remains bullish, a correction seems plausible before the next major move. Trade carefully and wait for confirmation at key levels.</p>")
        
        html_parts.append('</div>')
        
        return ''.join(html_parts)

    except Exception as e:
        print(f"Warning: Error in WordPress technical analysis summary generation: {e}. Using fallback.")
        import traceback
        traceback.print_exc()
        return hc.generate_technical_analysis_summary_html(ticker, rdata)

def generate_wordpress_historical_performance_html(ticker, rdata, content_library=None):
    """
    Generate SHORTER WordPress historical performance content with monthly data table.
    Provides concise analysis with tabular data presentation.
    """
    try:
        if not content_library:
            return hc.generate_historical_performance_html(ticker, rdata)

        # --- 1. Data Extraction ---
        profile_data = rdata.get('profile_data', {})
        historical_data = rdata.get('historical_data')

        company_name = profile_data.get('Company Name', ticker)

        # Calculate performance metrics
        performance_1y = None
        performance_3y = None
        performance_5y = None
        volatility_measure = None
        monthly_data = []

        if historical_data is not None and not historical_data.empty:
            try:
                # Calculate returns
                historical_data = historical_data.sort_values('Date')
                historical_data['Daily_Return'] = historical_data['Close'].pct_change()

                # 1-year performance
                one_year_ago = datetime.now() - timedelta(days=365)
                data_1y = historical_data[historical_data['Date'] >= one_year_ago]
                if not data_1y.empty:
                    performance_1y = ((data_1y['Close'].iloc[-1] / data_1y['Close'].iloc[0]) - 1) * 100
                    
                    # Generate monthly data for last 12 months
                    data_1y['YearMonth'] = data_1y['Date'].dt.to_period('M')
                    monthly_grouped = data_1y.groupby('YearMonth').agg({
                        'Open': 'first',
                        'Close': 'last',
                        'High': 'max',
                        'Low': 'min',
                        'Volume': 'sum'
                    }).reset_index()
                    
                    for _, row in monthly_grouped.iterrows():
                        month_return = ((row['Close'] - row['Open']) / row['Open']) * 100 if row['Open'] > 0 else 0
                        monthly_data.append({
                            'month': row['YearMonth'].strftime('%b %Y'),
                            'open': row['Open'],
                            'close': row['Close'],
                            'high': row['High'],
                            'low': row['Low'],
                            'return': month_return
                        })

                # 3-year performance
                three_years_ago = datetime.now() - timedelta(days=1095)
                data_3y = historical_data[historical_data['Date'] >= three_years_ago]
                if not data_3y.empty:
                    performance_3y = ((data_3y['Close'].iloc[-1] / data_3y['Close'].iloc[0]) - 1) * 100

                # 5-year performance
                five_years_ago = datetime.now() - timedelta(days=1825)
                data_5y = historical_data[historical_data['Date'] >= five_years_ago]
                if not data_5y.empty:
                    performance_5y = ((data_5y['Close'].iloc[-1] / data_5y['Close'].iloc[0]) - 1) * 100

                # Volatility
                if len(historical_data) > 30:
                    volatility_measure = historical_data['Daily_Return'].std() * np.sqrt(252) * 100

            except Exception as calc_error:
                print(f"Warning: Could not calculate historical performance metrics: {calc_error}")

        # Format values
        perf_1y_fmt = hc.format_html_value(performance_1y, 'percent_direct', ticker=ticker) if performance_1y is not None else "N/A"
        perf_3y_fmt = hc.format_html_value(performance_3y, 'percent_direct', ticker=ticker) if performance_3y is not None else "N/A"
        perf_5y_fmt = hc.format_html_value(performance_5y, 'percent_direct', ticker=ticker) if performance_5y is not None else "N/A"
        volatility_fmt = f"{volatility_measure:.1f}%" if volatility_measure is not None else "N/A"

        # Determine performance strength
        performance_strength = "strong" if (performance_1y and performance_1y > 20) else "moderate"

        # --- 2. Generate CONCISE Narrative ---
        html_parts = []

        # Section header
        html_parts.append("<h3>Historical Performance Analysis</h3>")

        # SHORT narrative content
        html_parts.append('<div class="narrative">')
        
        # Summary paragraph (ONE PARAGRAPH ONLY)
        summary_texts = [
            f"{ticker} has delivered {perf_1y_fmt} returns over the past year, {perf_3y_fmt} over three years, and {perf_5y_fmt} over five years, demonstrating {performance_strength} long-term performance with {volatility_fmt} annualized volatility.",
            f"Over the trailing periods, {ticker} generated returns of {perf_1y_fmt} (1-year), {perf_3y_fmt} (3-year), and {perf_5y_fmt} (5-year), showing {performance_strength} growth momentum with {volatility_fmt} price volatility.",
            f"Historical returns show {ticker} posted {perf_1y_fmt} in the past year, {perf_3y_fmt} over three years, and {perf_5y_fmt} over five years, reflecting {performance_strength} performance characteristics with {volatility_fmt} volatility."
        ]
        html_parts.append(f"<p>{get_variation(content_library, 'historical_performance.summary', summary_texts)}</p>")
        
        html_parts.append('</div>')

        # --- 3. Add Monthly Performance Table ---
        if monthly_data:
            html_parts.append('<h4>Monthly Performance Data (Last 12 Months)</h4>')
            html_parts.append('<div class="table-container">')
            html_parts.append('<table class="metrics-table">')
            html_parts.append('<thead><tr>')
            html_parts.append('<th>Month</th>')
            html_parts.append('<th>Open</th>')
            html_parts.append('<th>Close</th>')
            html_parts.append('<th>High</th>')
            html_parts.append('<th>Low</th>')
            html_parts.append('<th>Return</th>')
            html_parts.append('</tr></thead>')
            html_parts.append('<tbody>')
            
            for month_data in monthly_data:
                return_class = 'positive-value' if month_data['return'] >= 0 else 'negative-value'
                html_parts.append('<tr>')
                html_parts.append(f"<td>{month_data['month']}</td>")
                html_parts.append(f"<td>{hc.format_html_value(month_data['open'], 'currency', ticker=ticker)}</td>")
                html_parts.append(f"<td>{hc.format_html_value(month_data['close'], 'currency', ticker=ticker)}</td>")
                html_parts.append(f"<td>{hc.format_html_value(month_data['high'], 'currency', ticker=ticker)}</td>")
                html_parts.append(f"<td>{hc.format_html_value(month_data['low'], 'currency', ticker=ticker)}</td>")
                html_parts.append(f"<td class='{return_class}'>{month_data['return']:+.2f}%</td>")
                html_parts.append('</tr>')
            
            html_parts.append('</tbody></table>')
            html_parts.append('</div>')

        return ''.join(html_parts)

    except Exception as e:
        print(f"Warning: Error in WordPress historical performance generation: {e}. Using fallback.")
        import traceback
        traceback.print_exc()
        return hc.generate_historical_performance_html(ticker, rdata)

def generate_wordpress_peer_comparison_html(peer_data, ticker, content_library=None):
    """
    Generate WordPress peer comparison content.
    Falls back to original function if content library is not available or peer_data is empty.
    """
    try:
        if not peer_data or not isinstance(peer_data, dict):
            # Return a simple message if no peer data available
            return """
            <div class="narrative">
                <p>Peer comparison data is currently unavailable for this analysis.</p>
            </div>
            """
        
        # Use the html_components function as fallback
        return hc.generate_peer_comparison_html(peer_data, ticker)
    except Exception as e:
        print(f"Warning: Error in WordPress peer comparison generation: {e}. Using fallback.")
        return f"""
        <div class="narrative">
            <p>Unable to generate peer comparison analysis at this time.</p>
        </div>
        """

def generate_wordpress_risk_factors_html(ticker, rdata, content_library=None):
    """
    Generate WordPress risk factors content.
    Falls back to original function if content library is not available.
    """
    try:
        # Use the html_components function if available
        if hasattr(hc, 'generate_risk_factors_html'):
            return hc.generate_risk_factors_html(ticker, rdata)
        
        # Otherwise generate a basic risk factors section
        profile_data = rdata.get('profile_data', {})
        company_name = profile_data.get('Company Name', ticker)
        sector = profile_data.get('Sector', 'the market')
        
        html_parts = []
        html_parts.append("""
        <div class="narrative">
            <p>Investment in {company} carries various risks that investors should carefully consider:</p>
            <h4>Market Risk</h4>
            <p>Stock price volatility and broader market conditions can significantly impact {ticker}'s performance.</p>
            <h4>Sector-Specific Risk</h4>
            <p>As a company in {sector}, {ticker} is subject to industry-specific challenges and regulatory changes.</p>
            <h4>Economic Risk</h4>
            <p>Changes in economic conditions, interest rates, and inflation can affect the company's operations and profitability.</p>
            <h4>Company-Specific Risk</h4>
            <p>Operational challenges, management decisions, and competitive pressures may impact {ticker}'s financial performance.</p>
            <p><strong>Disclaimer:</strong> This analysis is for informational purposes only and does not constitute investment advice. Investors should conduct their own due diligence and consult with financial advisors.</p>
        </div>
        """.format(company=company_name, ticker=ticker, sector=sector))
        
        return ''.join(html_parts)
    except Exception as e:
        print(f"Warning: Error in WordPress risk factors generation: {e}. Using fallback.")
        return """
        <div class="narrative">
            <p>All investments carry risk. Please consult with a financial advisor before making investment decisions.</p>
        </div>
        """

def generate_wordpress_faq_html(ticker, rdata, content_library=None):
    """
    Generate WordPress FAQ content.
    Falls back to original function if content library is not available.
    """
    try:
        # Use the html_components function if available
        if hasattr(hc, 'generate_faq_html'):
            return hc.generate_faq_html(ticker, rdata)
        
        # Otherwise generate a basic FAQ section
        profile_data = rdata.get('profile_data', {})
        company_name = profile_data.get('Company Name', ticker)
        current_price = rdata.get('current_price')
        forecast_price = rdata.get('forecast_price')
        
        html_parts = []
        html_parts.append("""
        <div class="faq-section">
            <div class="faq-item">
                <h4>What is {ticker}?</h4>
                <p>{company} is a publicly traded company. This report provides comprehensive analysis of its stock performance and outlook.</p>
            </div>
            <div class="faq-item">
                <h4>Is {ticker} a good investment?</h4>
                <p>Investment suitability depends on individual risk tolerance, investment goals, and market conditions. This report provides analysis to help inform investment decisions, but should not be considered investment advice.</p>
            </div>
            <div class="faq-item">
                <h4>What is the forecast for {ticker}?</h4>
                <p>Based on our Prophet forecasting model and technical analysis, we provide price projections. However, actual future performance may vary significantly from forecasts.</p>
            </div>
            <div class="faq-item">
                <h4>How often should I review this analysis?</h4>
                <p>Market conditions change rapidly. We recommend reviewing updated analysis regularly and staying informed about company news and market developments.</p>
            </div>
            <div class="faq-item">
                <h4>Where can I find more information about {ticker}?</h4>
                <p>Additional information can be found through financial news sources, the company's investor relations website, and regulatory filings (such as SEC filings for US companies).</p>
            </div>
        </div>
        """.format(ticker=ticker, company=company_name))
        
        return ''.join(html_parts)
    except Exception as e:
        print(f"Warning: Error in WordPress FAQ generation: {e}. Using fallback.")
        return """
        <div class="narrative">
            <p>For frequently asked questions about this analysis, please refer to our methodology documentation.</p>
        </div>
        """

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


        # --- 4. Fetch Fundamentals (with retry logic) ---
        print("Step 4: Fetching fundamentals...")
        fundamentals = {}
        max_retries = 3
        base_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                print(f"Attempting to fetch yfinance data for {ticker} (attempt {attempt + 1}/{max_retries})...")
                yf_ticker_obj = yf.Ticker(ticker)

                # Set a timeout for the ticker operations
                start_time = time.time()

                fundamentals = {
                    'info': yf_ticker_obj.info or {},
                    'recommendations': yf_ticker_obj.recommendations if hasattr(yf_ticker_obj, 'recommendations') and yf_ticker_obj.recommendations is not None else pd.DataFrame(),
                    'news': yf_ticker_obj.news if hasattr(yf_ticker_obj, 'news') and yf_ticker_obj.news is not None else []
                }

                fetch_time = time.time() - start_time
                print(f"Successfully fetched yfinance data for {ticker} in {fetch_time:.2f} seconds")

                if not fundamentals['info']:
                    print(f"Warning: yfinance info data for {ticker} is empty.")
                else:
                    print(f"Successfully retrieved {len(fundamentals['info'])} info fields for {ticker}")
                break  # Success, exit retry loop

            except Exception as e_fund:
                print(f"Warning: Failed to fetch yfinance fundamentals for {ticker} (attempt {attempt + 1}/{max_retries}): {e_fund}")

                if attempt < max_retries - 1:  # Not the last attempt
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    # Last attempt failed, use empty data
                    print(f"All {max_retries} attempts failed. Using empty fundamentals data for {ticker}.")
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
        
        # Temporarily replace the metrics section content function with WordPress version
        original_generate_metrics_section_content = hc.generate_metrics_section_content
        if content_library:
            hc.generate_metrics_section_content = lambda metrics, ticker=None: generate_wordpress_metrics_section_content(metrics, ticker, content_library)
        
        try:
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
                    # Special handling for total_valuation - use content library
                    elif section_key == "total_valuation":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Total Valuation</h2>")
                        html_report_parts.append(generate_wordpress_total_valuation_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for conclusion_outlook - use content library
                    elif section_key == "conclusion_outlook":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Conclusion and Outlook</h2>")
                        html_report_parts.append(generate_wordpress_conclusion_outlook_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for detailed_forecast_table - use content library
                    elif section_key == "detailed_forecast_table":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Detailed Forecast Table</h2>")
                        html_report_parts.append(generate_wordpress_detailed_forecast_table_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for company_profile - use content library
                    elif section_key == "company_profile":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append(generate_wordpress_company_profile_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for valuation_metrics - use content library
                    elif section_key == "valuation_metrics":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Valuation Metrics</h2>")
                        html_report_parts.append(generate_wordpress_valuation_metrics_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for analyst_insights - use content library
                    elif section_key == "analyst_insights":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Analyst Insights</h2>")
                        html_report_parts.append(generate_wordpress_analyst_insights_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for analyst_insights - use content library
                    elif section_key == "analyst_insights":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Analyst Insights</h2>")
                        html_report_parts.append(generate_wordpress_analyst_insights_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for financial_health - use content library
                    elif section_key == "financial_health":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Financial Health</h2>")
                        html_report_parts.append(generate_wordpress_financial_health_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for financial_efficiency - use content library
                    elif section_key == "financial_efficiency":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Financial Efficiency</h2>")
                        html_report_parts.append(generate_wordpress_financial_efficiency_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for profitability_growth - use content library
                    elif section_key == "profitability_growth":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Profitability and Growth</h2>")
                        html_report_parts.append(generate_wordpress_profitability_growth_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for dividends_shareholder_returns - use content library
                    elif section_key == "dividends_shareholder_returns":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Dividends and Shareholder Returns</h2>")
                        html_report_parts.append(generate_wordpress_dividends_shareholder_returns_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for share_statistics - use content library
                    elif section_key == "share_statistics":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Share Statistics</h2>")
                        html_report_parts.append(generate_wordpress_share_statistics_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for stock_price_statistics - use content library
                    elif section_key == "stock_price_statistics":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Stock Price Statistics</h2>")
                        html_report_parts.append(generate_wordpress_stock_price_statistics_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for short_selling_info - use content library
                    elif section_key == "short_selling_info":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Short Selling Information</h2>")
                        html_report_parts.append(generate_wordpress_short_selling_info_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for technical_analysis_summary - use content library
                    elif section_key == "technical_analysis_summary":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Technical Analysis Summary</h2>")
                        html_report_parts.append(generate_wordpress_technical_analysis_summary_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for historical_performance - use content library
                    elif section_key == "historical_performance":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Historical Performance</h2>")
                        html_report_parts.append(generate_wordpress_historical_performance_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for peer_comparison - use content library
                    elif section_key == "peer_comparison":
                        peer_data = rdata.get('peer_comparison_data', {})
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Peer Comparison</h2>")
                        html_report_parts.append(generate_wordpress_peer_comparison_html(peer_data, ticker, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for risk_factors - use content library
                    elif section_key == "risk_factors":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Risk Factors</h2>")
                        html_report_parts.append(generate_wordpress_risk_factors_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for faq - use content library
                    elif section_key == "faq":
                        html_report_parts.append(f"<section id='{section_key}'>")
                        html_report_parts.append("<h2>Frequently Asked Questions</h2>")
                        html_report_parts.append(generate_wordpress_faq_html(ticker, rdata, content_library))
                        html_report_parts.append("</section>")
                    # Special handling for report_info_disclaimer - requires generation_time parameter
                    elif section_key == "report_info_disclaimer":
                        from datetime import datetime
                        section_title = "Report Information and Disclaimer"
                        html_report_parts.append(f"<section id='{section_key}'><h2>{section_title}</h2>")
                        html_report_parts.append(generator_func(datetime.now())) # Pass generation time
                        html_report_parts.append("</section>")
                    else:
                        # Generic fallback for any remaining sections
                        section_title = section_key.replace("_", " ").title()
                        html_report_parts.append(f"<section id='{section_key}'><h2>{section_title}</h2>")
                        try:
                            html_report_parts.append(generator_func(ticker, rdata)) # Call the function from html_components
                        except Exception as e:
                            print(f"Error generating section '{section_key}': {e}")
                            html_report_parts.append(f"<p>Section temporarily unavailable.</p>")
                        html_report_parts.append("</section>")
                else:
                    print(f"Warning: Unknown report section key '{section_key}'. Skipping.")
        
        finally:
            # Restore the original function
            hc.generate_metrics_section_content = original_generate_metrics_section_content
        
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
.stock-report_container ol {
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

# Define all possible sections (keys should match values in report_sections_to_include)
if hc is None:
    ALL_REPORT_SECTIONS = {}
else:
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
        "financial_efficiency": hc.generate_financial_efficiency_html,
        "historical_performance": hc.generate_historical_performance_html,
        "technical_analysis_summary": hc.generate_technical_analysis_summary_html,
        "short_selling_info": hc.generate_short_selling_info_html,
        "stock_price_statistics": hc.generate_stock_price_statistics_html,
        "share_statistics": hc.generate_share_statistics_html,
        "dividends_shareholder_returns": hc.generate_dividends_shareholder_returns_html,
        "peer_comparison": hc.generate_peer_comparison_html,
        "conclusion_outlook": hc.generate_conclusion_outlook_html,
        "risk_factors": hc.generate_risk_factors_html,
        "faq": hc.generate_faq_html,
        "report_info_disclaimer": hc.generate_report_info_disclaimer_html
        # Add more if html_components.py has more generators
    }

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
