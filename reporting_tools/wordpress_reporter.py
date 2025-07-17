import os
import time
import traceback
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import re

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
    "conclusion_outlook": hc.generate_conclusion_outlook_html,
    
    "risk_factors": hc.generate_risk_factors_html,
    "faq": hc.generate_faq_html
    # Add more if html_components.py has more generators
}


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
        if model is None or forecast_raw is None or actual_df is None or forecast_df is None:
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
                
                section_title = section_key.replace("_", " ").title()
                html_report_parts.append(f"<section id='{section_key}'><h3>{section_title}</h3>")
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
        base_css = """/* Your base CSS here */
* Basic WordPress Embed CSS */
.stock-report-container { /* Base styles for all reports */
    font-family: sans-serif; 
    line-height: 1.6;
    color: #333;
    max-width: 800px;
    margin: 1em auto;
    padding: 15px;
    border: 1px solid #ddd;
    background-color: #fff;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    border-radius: 5px; 
}
.stock-report-container h2,
.stock-report-container h3,
.stock-report-container h4 {
    margin-top: 1.5em;
    margin-bottom: 0.8em;
    padding-bottom: 0.3em;
    border-bottom: 1px solid #eee;
}
.stock-report-container h2.report-title { text-align: center; border-bottom-width: 2px; padding-bottom: 10px; margin-bottom: 1.5em; }
.stock-report-container h3 { font-size: 1.4em; }
.stock-report-container h4 { font-size: 1.2em; }
.stock-report-container section { margin-bottom: 2em; }
.stock-report-container p { margin-bottom: 1em; }
.stock-report-container ul, .stock-report-container ol { margin-left: 20px; margin-bottom: 1em; }
.stock-report-container li { margin-bottom: 0.5em; }
.stock-report-container strong { font-weight: bold; }
.stock-report-container a { text-decoration: none; }
.stock-report-container a:hover { text-decoration: underline; }
.stock-report-container .table-container { overflow-x: auto; margin-bottom: 1em; }
.stock-report-container table { width: 100%; border-collapse: collapse; margin-bottom: 1em; font-size: 0.95em; }
.stock-report-container th, .stock-report-container td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; vertical-align: top; }
.stock-report-container th { background-color: #f4f4f4; font-weight: bold; white-space: nowrap; }
.stock-report-container tr:nth-child(even) { background-color: #f9f9f9; }
.stock-report-container td:first-child { font-weight: bold; background-color: #fdfdfd; width: 35%; }
.metrics-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 1em; }
.metric-item { display: flex; flex-direction: column; padding: 10px; background-color: #fff; border: 1px solid #eee; border-radius: 3px; }
.metric-label { font-size: 0.9em; color: #555; margin-bottom: 5px; }
.metric-value { font-size: 1.1em; font-weight: bold; }
.metric-change { margin-left: 5px; font-size: 0.9em; }
.trend-up, .sentiment-bullish, .action-buy { color: #28a745; } 
.trend-down, .sentiment-bearish, .action-short { color: #dc3545; } 
.trend-neutral, .sentiment-neutral, .sentiment-neutral-bullish, .sentiment-neutral-bearish, .action-hold { color: #ffc107; } 
.icon { display: inline-block; margin-right: 5px; }
.icon-up { color: #28a745; } .icon-down { color: #dc3545; } .icon-neutral { color: #ffc107; } .icon-warning { color: #ffc107; } 
.profile-grid, .analyst-grid, .ma-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 1em; }
.profile-item span:first-child, .analyst-item span:first-child, .ma-item .label { font-weight: bold; margin-right: 5px; color: #333; }
.profile-item, .analyst-item, .ma-item { padding: 8px; background-color: #f9f9f9; border: 1px solid #eee; border-radius: 3px; font-size: 0.95em; }
.news-container { margin-top: 1em; }
.news-item { border-bottom: 1px dashed #eee; padding-bottom: 1em; margin-bottom: 1em; }
.news-item:last-child { border-bottom: none; margin-bottom: 0; }
.news-item h4 { margin-bottom: 0.3em; font-size: 1.1em;}
.news-meta { font-size: 0.85em; color: #666; } .news-meta span { margin-right: 15px; }
.narrative { padding: 15px; border-radius: 4px; margin-bottom: 1.5em; font-size: 0.95em; border-left-width: 4px; border-left-style: solid; }
.narrative p:last-child { margin-bottom: 0; } .narrative ul { list-style-type: disc; padding-left: 20px; }
.conclusion-columns { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 1.5em; }
.conclusion-column { flex: 1; min-width: 250px; padding: 15px; border-radius: 5px; border: 1px solid #eee; }
.conclusion-column h3 { margin-top: 0; font-size: 1.2em; border-bottom: 1px solid #ddd; padding-bottom: 0.4em; }
.conclusion-column ul { padding-left: 0; list-style: none; }
.conclusion-column li { margin-bottom: 0.7em; display: flex; align-items: flex-start; font-size: 0.95em; }
.conclusion-column li .icon { margin-right: 8px; margin-top: 2px; }
#faq details { background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px; }
#faq summary { padding: 10px; font-weight: bold; cursor: pointer; outline: none; }
#faq details[open] summary { border-bottom: 1px solid #ddd; }
#faq details p { padding: 10px; margin: 0; border-top: 1px solid #eee; }
.disclaimer, .general-info p { font-size: 0.85em; color: #555; margin-top: 1.5em; padding-top: 1em; border-top: 1px dashed #ccc; }
.disclaimer strong { color: #c00; }
"""
      
        final_css = base_css 
        final_html_wrapped = f'<div class="stock-report-container report-{site_slug}">{final_html_body}</div>'


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