# report_generator.py (MODIFIED FOR BASE64 EMBEDDING AND KALEIDO ROBUSTNESS)
import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html, write_image
import os
import numpy as np
from datetime import datetime, timedelta
import pytz
import json
import time
import plotly.io as pio # pio is already imported
from threading import Thread
import tempfile
import matplotlib
matplotlib.use('Agg') # Ensure Agg backend is used
import matplotlib.pyplot as plt
# --- NEW: Imports for Base64 encoding ---
import base64
from io import BytesIO
# --- End New Imports ---

# Import currency symbol function
from app.html_components import get_currency_symbol

try:
    import psutil
except ImportError:
    psutil = None

# --- MODIFIED KALEIDO SETUP ---
try:
    if pio.kaleido.scope is not None:
        pio.kaleido.scope.default_format = "png"
        # You might also want to set other Kaleido scope properties here if needed
        # pio.kaleido.scope.scale = 1.5 # Example: default scale for saved images
        # pio.kaleido.scope.width = 1000 # Example: default width
        # pio.kaleido.scope.height = 600 # Example: default height
        print("INFO: report_generator.py - Kaleido default format set to 'png'.")
    else:
        # Use a logger if available, otherwise print
        print("WARNING: report_generator.py - Kaleido scope is None. Static image export via Kaleido may not work or may use Plotly's default settings/engine.")
except AttributeError:
    print("WARNING: report_generator.py - Could not set Kaleido default format due to AttributeError. Kaleido might not be available or configured correctly for Plotly.")
except Exception as e:
    print(f"WARNING: report_generator.py - An unexpected error occurred while configuring Plotly/Kaleido defaults: {e}")
# --- END MODIFIED KALEIDO SETUP ---

# Import functions from helper modules (ensure evaluation imports are present if needed)
from analysis_scripts.technical_analysis import (
    plot_historical_line_chart, plot_price_bollinger, plot_rsi,
    plot_macd_lines, plot_macd_histogram, calculate_detailed_ta,
    get_macd_conclusion, get_rsi_conclusion, get_bb_conclusion,
    plot_historical_mpl, plot_bollinger_mpl, plot_rsi_mpl,
    plot_macd_lines_mpl, plot_macd_hist_mpl, plot_forecast_mpl
)


from app.html_components import (
    generate_introduction_html, generate_metrics_summary_html,
    generate_detailed_forecast_table_html, generate_company_profile_html,
    generate_total_valuation_html, generate_share_statistics_html,
    generate_valuation_metrics_html, generate_financial_health_html,
    generate_financial_efficiency_html, generate_profitability_growth_html,
    generate_dividends_shareholder_returns_html,
    generate_technical_analysis_summary_html, generate_stock_price_statistics_html,
    generate_short_selling_info_html, generate_risk_factors_html,
    generate_analyst_insights_html, generate_recent_news_html,
    generate_historical_performance_html,
    generate_conclusion_outlook_html, generate_faq_html,
    generate_report_info_disclaimer_html
)
from analysis_scripts.fundamental_analysis import (
    extract_company_profile, extract_valuation_metrics, extract_financial_health,
    extract_profitability, extract_dividends_splits, extract_analyst_info,
    extract_news, safe_get, extract_total_valuation_data,
    extract_share_statistics_data, extract_financial_efficiency_data,
    extract_stock_price_stats_data,
    extract_short_selling_data
)

# --- Shared CSS (Keep Unchanged) ---
custom_style = """
<style>
  /* --- Base & General --- */
  html { scroll-behavior: smooth; }
  body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      color: #333;
      line-height: 1.6;
      background-color: #ffffff;
      margin: 0;
      padding: 0;
      font-size: 15px;
      -webkit-text-size-adjust: 100%;
      text-size-adjust: 100%;
      overflow-x: hidden;
  }
  /* Report Container */
  .report-container {
      max-width: 1200px;
      margin: 1rem auto;
      padding: 1rem 2rem;
      background: #ffffff;
      overflow-x: hidden;
      padding-bottom: 3rem;
    }
  /* Use H2 for main section titles as per WP request */
  .report-container h2 {
    font-size: 1.6rem; /* Size for section titles */
    font-weight: 600;
    color: #34495e;
    border-bottom: 2px solid #e9ecef;
    padding-bottom: 0.6rem;
    margin: 2rem 0 1.5rem 0; /* Added top margin */
   }
  .report-container h1.report-title { /* Keep H1 style for the main title (if used in full report) */
      text-align: center; color: #2c3e50; margin: 0 0 2rem 0; font-size: 2.4rem; font-weight: 700; border-bottom: 1px solid #dee2e6; padding-bottom: 1rem;
   }
  .section { margin-bottom: 0; /* Reduced default margin, control spacing via H2 margin */ padding: 0; background-color: #fff; border-radius: 8px; }
  .section h3 { font-size: 1.2rem; color: #34495e; margin: 1.5rem 0 1rem 0; padding-bottom: 0.4rem; border-bottom: 1px solid #ecf0f1; }
  .section h4 { font-size: 1.1rem; color: #495057; margin: 1rem 0 0.5rem 0; }
  .report-container p { font-size: 1rem; line-height: 1.7; color: #495057; margin: 0 0 1rem 0; }
  .report-container a { color: #3498db; text-decoration: none; } .report-container a:hover { text-decoration: underline; }
  .report-container strong { font-weight: 600; color: #2c3e50; }
  .report-container ul { margin-bottom: 1rem; padding-left: 25px;} /* Default list styling */
  .report-container li { margin-bottom: 0.5rem; }
  .disclaimer { font-size: 0.9rem; color: #6c757d; font-style: italic; margin-top: 1.5rem; padding: 1rem; background-color: #f8f9fa; border-left: 4px solid #adb5bd; border-radius: 4px;}
  .narrative { margin-bottom: 1.5rem; padding: 1rem 1.2rem; background-color: #eef5f9; border-left: 4px solid #5dade2; border-radius: 4px; font-size: 0.95rem; }
  .narrative ul { margin-top: 0.5rem; margin-bottom: 0.5rem; padding-left: 20px;} .narrative li { margin-bottom: 0.5rem;}
  .icon { margin-right: 0.6em; font-size: 1em; display: inline-block; width: 1.2em; text-align: center; vertical-align: middle; }
  .icon-up { color: #28a745; } .icon-down { color: #dc3545; } .icon-neutral { color: #6c757d; }
  .icon-warning { color: #ffc107; } .icon-positive { color: #28a745; } .icon-negative { color: #dc3545; }
  .icon-info { color: #17a2b8; }
  .metrics-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .metric-item { background-color: #f8f9fa; padding: 0.8rem 1rem; border-radius: 6px; text-align: center; border: 1px solid #dee2e6; }
  .metric-label { display: block; font-size: 0.75rem; color: #6c757d; margin-bottom: 0.4rem; text-transform: uppercase; font-weight: 500; }
  .metric-value { display: block; font-size: 1.2rem; font-weight: 600; color: #343a40; line-height: 1.2; word-wrap: break-word; }
  .metric-change { font-size: 0.85rem; font-weight: normal; margin-left: 0.2rem; display: inline-block; }
  .sentiment-bullish, .action-buy, .trend-up { color: #28a745 !important; } .sentiment-strong-bullish { color: #208a38 !important; font-weight: bold; }
  .sentiment-bearish, .action-short, .trend-down { color: #dc3545 !important; } .sentiment-strong-bearish { color: #c82333 !important; font-weight: bold; }
  .sentiment-neutral, .action-hold, .trend-neutral { color: #6c757d !important; }
  .profile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem 1.5rem; margin-bottom: 1.5rem; }
  .profile-item { word-wrap: break-word; }
  .profile-item span { font-weight: 600; margin-right: 0.5rem; color: #495057; }
  .business-summary { margin-top: 1rem; } .business-summary h4 { margin-bottom: 0.5rem; color: #34495e; }
  .metrics-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
  .metrics-table td { padding: 0.9rem 0.5rem; border-bottom: 1px solid #dee2e6; font-size: 0.95rem; vertical-align: top;}
  .metrics-table tr:last-child td { border-bottom: none; } .metrics-table td:first-child { font-weight: 500; color: #495057; width: 40%; word-break: break-word; white-space: normal; }
  .metrics-table td:last-child { text-align: right; font-weight: 600; color: #343a40; white-space: nowrap;}
  .analyst-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem; }
  .analyst-item { background-color: #f8f9fa; padding: 0.8rem 1rem; border-radius: 4px; border: 1px solid #dee2e6; font-size: 0.9rem;}
  .analyst-item span { font-weight: 600; margin-right: 0.3rem; color: #495057; }
  .table-container { overflow-x: auto; margin-top: 1rem; border: 1px solid #dee2e6; border-radius: 6px; -webkit-overflow-scrolling: touch; }
  .report-container table { width: 100%; border-collapse: collapse; }
  .report-container th, .report-container td { padding: 0.9rem 1.1rem; text-align: left; border-bottom: 1px solid #dee2e6; font-size: 0.95rem; white-space: nowrap; }
  .report-container th { background-color: #e9ecef; color: #495057; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; border-bottom-width: 2px; }
  .report-container tbody tr:nth-child(even) { background-color: #f8f9fa; } .report-container tbody tr:hover { background-color: #e9ecef; }
  .report-container td:nth-child(n+2):not(:last-child) { text-align: right; } .report-container td:last-child { text-align: center; } .report-container td[class^='action-'] { font-weight: bold; }
  .risk-factors ul { list-style: none; padding-left: 0; margin-top: 1rem; } /* Updated class name */
  .risk-factors li { background-color: #fff3cd; border-left: 5px solid #ffc107; color: #856404; padding: 0.9rem 1.2rem; margin-bottom: 0.8rem; border-radius: 4px; font-size: 0.95rem; display: flex; align-items: flex-start; }
  .risk-factors li .icon { font-size: 1.1em; margin-right: 0.8em; margin-top: 0.1em; color: #ffc107; flex-shrink: 0; }
  .technical-analysis-summary h4 { margin-top: 1.5rem; margin-bottom: 0.8rem; color: #34495e; font-size: 1.1rem; padding-bottom: 0.3rem; border-bottom: 1px solid #dee2e6; } /* Updated class name */
  .sentiment-indicator { margin-bottom: 1.5rem; font-size: 1.1rem; padding: 1rem; background-color:#f8f9fa; border-radius: 6px; border: 1px solid #dee2e6; text-align: center;}
  .sentiment-indicator span:first-child { margin-right: 0.5rem; font-weight: 500;}
  .ma-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .ma-item { background: #f8f9fa; padding: 0.8rem 1rem; border-radius: 6px; font-size: 0.95rem; border: 1px solid #dee2e6;}
  .ma-item .label { font-weight: 600; margin-right: 0.5rem;} .ma-item .value { font-weight: 500; } .ma-item .status { font-size: 0.85rem; margin-left: 0.4rem; font-style: italic;}
  /* Styles for embedded Plotly charts - Keep for full report */
  .indicator-chart-container { background-color: #ffffff; padding: 0; margin-bottom: 0.5rem; border-radius: 8px; border: 1px solid #dee2e6; width: 100%; max-width: 100%; position: relative; overflow: hidden; }
  .plotly-graph-div { margin: 0 auto !important; width: 100% !important; height: 100% !important; position: relative; }
  .modebar { position: absolute !important; top: 2px !important; left: 50% !important; transform: translateX(-50%) !important; width: auto !important; max-width: calc(100% - 10px) !important; display: flex !important; flex-wrap: wrap !important; justify-content: center !important; background-color: rgba(245, 245, 245, 0.9) !important; border: 1px solid #ccc !important; border-radius: 4px !important; padding: 3px 5px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important; opacity: 1 !important; z-index: 1001 !important; transition: none !important; }
  /* Styles for static/embedded images */
  .static-chart-image, .embedded-chart-image { display: block; max-width: 100%; height: auto; margin: 1rem auto; border: 1px solid #dee2e6; border-radius: 4px; }
  .indicator-conclusion { padding: 1.2rem 1.5rem; margin-top: 0; border-top: 1px solid #dee2e6; font-size: 0.95rem; line-height: 1.6; color: #495057; background-color: #f8f9fa; border-radius: 0 0 8px 8px; margin-bottom: 1.5rem; }
  .conclusion-outlook .conclusion-columns { display: flex; flex-wrap: wrap; gap: 2.5rem; margin: 1.5rem 0; padding: 1.5rem; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;} /* Updated class name */
  .conclusion-outlook .conclusion-column { flex: 1; min-width: 300px; }
  .conclusion-outlook h3 { font-size: 1.2rem; color: #34495e; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 1px solid #ced4da; }
  .conclusion-outlook ul { list-style: none; padding-left: 0; margin-top: 0; }
  .conclusion-outlook li { margin-bottom: 1rem; font-size: 0.95rem; line-height: 1.6; display: flex; align-items: flex-start; padding-left: 0; }
  .conclusion-outlook li .icon { margin-right: 0.8em; margin-top: 0.15em; flex-shrink: 0; width: 1.2em; text-align: center; font-size: 1.1em; }
  .conclusion-outlook li > span:last-child { flex-grow: 1; }
  .recent-news .news-container { margin-top: 1rem; } /* Updated class name */
  .recent-news .news-item { padding: 1rem 0; border-bottom: 1px solid #e9ecef; margin-bottom: 0; background-color: transparent;}
  .recent-news .news-item:last-child { border-bottom: none; }
  .recent-news .news-item h4 { margin: 0 0 0.3rem 0; font-size: 1.05rem; font-weight: 600;}
  .recent-news .news-item h4 a { color: #0056b3; } .recent-news .news-item h4 a:hover { color: #003d7a; }
  .recent-news .news-meta { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; color: #6c757d; font-size: 0.85rem; margin: 0.5rem 0 0 0; }
  .recent-news .news-meta span { background-color: #e9ecef; padding: 0.1rem 0.5rem; border-radius: 3px; }
  .frequently-asked-questions details { border: 1px solid #dee2e6; border-radius: 6px; margin-bottom: 1rem; background: #fff; transition: background-color 0.2s ease;} /* Updated class name */
  .frequently-asked-questions details[open] { background-color: #f8f9fa; }
  .frequently-asked-questions summary { padding: 1rem 1.2rem; font-weight: 600; cursor: pointer; background-color: transparent; border-radius: 6px; outline: none; position: relative; color: #34495e; display: block; transition: background-color 0.2s ease;}
  .frequently-asked-questions details[open] summary { background-color: #e9ecef; border-bottom: 1px solid #dee2e6; border-radius: 6px 6px 0 0; }
  .frequently-asked-questions summary::marker { content: ""; } /* Hide default marker */
  .frequently-asked-questions summary::after { content: '+'; position: absolute; right: 1.2rem; top: 50%; transform: translateY(-50%); font-size: 1.5rem; color: #adb5bd; transition: transform 0.2s ease-in-out, color 0.2s ease;}
  .frequently-asked_questions details[open] summary::after { content: '−'; transform: translateY(-50%) rotate(180deg); color: #3498db;}
  .frequently-asked_questions details p { padding: 1.5rem 1.2rem; margin: 0; border-top: 1px solid #dee2e6; border-radius: 0 0 6px 6px; background-color: #fff;}
  .frequently-asked_questions details[open] p { border-top: none; }
  .report-information-disclaimer .general-info { padding: 1.5rem; background-color: #f8f9fa; border-radius: 8px; border-top: 1px solid #dee2e6; margin-top: 2rem;} /* Updated class name */
  .report-information-disclaimer .general-info p { margin-bottom: 0.5rem; font-size: 0.9rem; color: #6c757d; }
  .report-information-disclaimer .general-info .disclaimer { margin-top: 1rem; padding: 1rem; background-color: #e9ecef; border-left-color: #6c757d; font-size: 0.85rem; }
  /* Add styles for new sections if needed */
  .total-valuation table, .share-statistics table, .financial-efficiency table,
  .stock-price-statistics table, .short-selling-information table { /* Apply metric table style to new tables */
      width: 100%; border-collapse: collapse; margin-top: 1rem;
  }
   .total-valuation td, .share-statistics td, .financial-efficiency td,
   .stock-price-statistics td, .short-selling-information td {
      padding: 0.9rem 0.5rem; border-bottom: 1px solid #dee2e6; font-size: 0.95rem; vertical-align: top;
  }
   .total-valuation tr:last-child td, .share-statistics tr:last-child td, .financial-efficiency tr:last-child td,
   .stock-price-statistics tr:last-child td, .short-selling-information tr:last-child td { border-bottom: none; }
   .total-valuation td:first-child, .share-statistics td:first-child, .financial-efficiency td:first-child,
   .stock-price-statistics td:first-child, .short-selling-information td:first-child { font-weight: 500; color: #495057; width: 40%; word-break: break-word; white-space: normal; }
   .total-valuation td:last-child, .share-statistics td:last-child, .financial-efficiency td:last-child,
   .stock-price-statistics td:last-child, .short-selling-information td:last-child { text-align: right; font-weight: 600; color: #343a40; white-space: nowrap;}

  /* Responsive Adjustments (Consolidated) */
  @media (max-width: 992px) {
      body { font-size: 14px; }
      .report-container { padding: 1rem 1.5rem; padding-bottom: 2rem; }
      .report-container h1.report-title { font-size: 2rem; }
      .report-container h2 { font-size: 1.4rem; }
      .report-container p { font-size: 0.95rem; }
      .metric-item { padding: 0.7rem 0.9rem; }
      .metric-value { font-size: 1.1rem; }
      .report-container th, .report-container td { padding: 0.8rem 0.9rem; font-size: 0.9rem; }
      .conclusion-outlook .conclusion-columns { gap: 1.5rem; }
      .conclusion-outlook .conclusion-column { min-width: unset; }
      .plotly-graph-div { min-height: 280px; }
  }
  @media (max-width: 768px) {
      body { font-size: 14px; }
      .report-container { padding: 1rem 1rem; padding-bottom: 2rem; margin: 0.5rem auto; }
      .report-container h1.report-title { font-size: 1.8rem; margin-bottom: 1.5rem; }
      .report-container h2 { font-size: 1.3rem; margin-bottom: 1rem; margin-top: 1.5rem;}
      .report-container h3 { font-size: 1.1rem; }
      .report-container h4 { font-size: 1rem; }
      .report-container p { font-size: 0.9rem; line-height: 1.6; }
      .metrics-summary { grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.8rem; }
      .metric-item { padding: 0.6rem 0.8rem; }
      .metric-value { font-size: 1rem; }
      .metric-label { font-size: 0.7rem; }
      .profile-grid { grid-template-columns: 1fr; }
      .metrics-table td:first-child, .total-valuation td:first-child, .share-statistics td:first-child,
      .financial-efficiency td:first-child, .stock-price-statistics td:first-child,
      .short-selling-information td:first-child { width: 35%; }
      .table-container { margin-top: 0.8rem; }
      .report-container th, .report-container td { font-size: 0.85rem; padding: 0.7rem 0.8rem; }
      .risk-factors li { font-size: 0.9rem; padding: 0.7rem 1rem; }
      .conclusion-outlook .conclusion-columns { flex-direction: column; gap: 1.5rem; padding: 1rem; }
      .conclusion-outlook h3 { font-size: 1.1rem; }
      .conclusion-outlook li { font-size: 0.9rem; }
      .frequently-asked-questions summary { padding: 0.8rem 1rem; font-size: 0.95rem; }
      .frequently-asked-questions details p { padding: 1rem; font-size: 0.9rem; }
      .disclaimer { font-size: 0.85rem; padding: 0.8rem; }
      .narrative { font-size: 0.9rem; padding: 0.8rem 1rem; }
      .analyst-grid { grid-template-columns: 1fr; }
      .ma-summary { grid-template-columns: 1fr; }
      .plotly-graph-div { min-height: 280px; padding-bottom: 50px; /* Padding for legend */ }
  }
  @media (max-width: 480px) {
      body { font-size: 13px; }
      .report-container { padding: 0.5rem; padding-bottom: 1.5rem; }
      .report-container h1.report-title { font-size: 1.5rem; }
      .report-container h2 { font-size: 1.2rem; }
      .report-container p { font-size: 0.85rem; }
      .report-container th, .report-container td { font-size: 0.75rem; padding: 0.5rem 0.6rem; white-space: normal; /* Allow wrapping */ }
      .report-container td:last-child { text-align: left; }
      .metrics-summary { grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 0.4rem; }
      .metric-item { padding: 0.4rem 0.5rem; }
      .metric-value { font-size: 0.85rem; }
      .metric-label { font-size: 0.6rem; }
      .risk-factors li { font-size: 0.85rem; padding: 0.6rem 0.9rem; }
      .conclusion-outlook li { font-size: 0.85rem; }
      .frequently-asked-questions summary { font-size: 0.9rem; }
      .frequently-asked-questions details p { font-size: 0.85rem; }
      .disclaimer { font-size: 0.8rem; }
      .narrative { font-size: 0.85rem; }
      .modebar { padding: 2px; }
      .modebar-btn { min-width: 20px; height: 20px; line-height: 16px; }
      .modebar-btn svg { width: 11px; height: 11px; }
      .plotly-graph-div { min-height: 230px; padding-bottom: 60px; /* More padding for legend */ }
      .plotly-graph-div .legend { font-size: 0.8em; }
      .indicator-conclusion { font-size: 0.85rem; }
  }
</style>
"""

# Helper function to get Base64 encoded image string from Matplotlib figure
def get_mpl_base64(fig):
    """Converts a Matplotlib figure to a Base64 encoded PNG image string."""
    if fig is None:
        return None
    try:
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100) # Save to buffer
        plt.close(fig) # Close the figure to free memory
        buf.seek(0)
        img_bytes = buf.getvalue()
        base64_string = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/png;base64,{base64_string}"
    except Exception as e:
        print(f"Error converting Matplotlib figure to Base64: {e}")
        if fig:
            plt.close(fig) # Ensure figure is closed on error
        return None

def get_mpl_base64_from_file(image_path): # Helper to get base64 if needed for HTML body
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as img_file:
            img_bytes = img_file.read()
        base64_string = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/png;base64,{base64_string}"
    except Exception as e:
        print(f"Error converting image file {image_path} to Base64: {e}") # Use logger
        return None


# Helper function to determine sentiment (Keep Unchanged)
def determine_sentiment(detailed_ta_data, overall_pct_change):
    # ... (implementation unchanged) ...
    current_price = detailed_ta_data.get('Current_Price')
    sma_50 = detailed_ta_data.get('SMA_50')
    sma_200 = detailed_ta_data.get('SMA_200')
    rsi = detailed_ta_data.get('RSI_14') # Use RSI_14 from detailed data
    macd_hist = detailed_ta_data.get('MACD_Hist')

    if current_price is None: return "N/A"

    score = 0
    # Forecast Trend
    if overall_pct_change > 5: score += 1.5
    elif overall_pct_change > 1: score += 0.5
    elif overall_pct_change < -5: score -= 1.5
    elif overall_pct_change < -1: score -= 0.5

    # Price vs SMAs
    if sma_50 is not None and current_price > sma_50: score += 0.5
    elif sma_50 is not None and current_price < sma_50: score -= 0.5
    if sma_200 is not None and current_price > sma_200: score += 1.0
    elif sma_200 is not None and current_price < sma_200: score -= 1.0

    # SMA Crossover (Golden/Death Cross approximation)
    if sma_50 is not None and sma_200 is not None:
        if sma_50 > sma_200 * 1.005 : score += 0.5 # 50 above 200 is bullish (added small buffer)
        elif sma_50 < sma_200 * 0.995: score -= 0.5 # 50 below 200 is bearish (added small buffer)

    # RSI Level
    if rsi is not None and not pd.isna(rsi):
        if rsi > 68: score -= 0.25 # Slightly bearish if high RSI
        elif rsi < 32: score += 0.25 # Slightly bullish if low RSI

    # MACD Histogram
    if macd_hist is not None and not pd.isna(macd_hist):
        if macd_hist > 0: score += 0.25 # Positive histogram is bullish
        else: score -= 0.25 # Negative histogram is bearish

    # Determine Sentiment String
    if score >= 2.5: return "Strong Bullish"
    elif score >= 1.0: return "Bullish"
    elif score <= -2.5: return "Strong Bearish"
    elif score <= -1.0: return "Bearish"
    else: return "Neutral"

# Helper function to safely write Plotly images (Keep Unchanged)
def _write_plotly_image(fig, path, fallback_msg="Chart could not be generated.", timeout_seconds=60):
    # ... (implementation unchanged) ...
    if fig is None:
        print(f"Warning: Figure is None, cannot save image to {path}.")
        return None

    output_dir = os.path.dirname(path)
    temp_path = None

    try:
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                print(f"Error creating directory {output_dir}: {e}")
                return None
        if not os.access(output_dir, os.W_OK):
            print(f"Error: No write permission for directory {output_dir}")
            return None

        _, final_ext = os.path.splitext(path)
        if not final_ext:
            final_ext = '.png'
            path += final_ext

        # Use tempfile context manager properly
        with tempfile.NamedTemporaryFile(suffix=final_ext, delete=False) as temp_file_obj:
            temp_path = temp_file_obj.name
            # No need to close explicitly, context manager handles it

        start_time = time.time()

        def write_with_timeout():
            # Ensure fig dimensions are reasonable before writing
            fig_width = fig.layout.width if fig.layout.width else 1200
            fig_height = fig.layout.height if fig.layout.height else 600
            write_image(fig, temp_path, engine='kaleido', scale=1.0, width=fig_width, height=fig_height)
            return temp_path

        result = [None]
        def target_wrapper():
            try:
                result[0] = write_with_timeout()
            except Exception as e:
                print(f"[Thread Error] Image write failed for {os.path.basename(temp_path)}: {e}")
                result[0] = None # Signal failure

        thread = Thread(target=target_wrapper)
        thread.daemon = True
        thread.start()
        thread.join(timeout_seconds)

        if thread.is_alive():
            print(f"Error: Image generation timed out after {timeout_seconds}s for {os.path.basename(path)}")
            # Attempt to kill lingering processes (optional, might need adjustment)
            if psutil:
                 current_pid = os.getpid()
                 parent = psutil.Process(current_pid)
                 children = parent.children(recursive=True)
                 for proc in children:
                     if proc.name() in ['kaleido', 'chrome', 'chromium']:
                         try: proc.terminate()
                         except psutil.Error: pass
            if os.path.exists(temp_path):
                 try: os.remove(temp_path)
                 except OSError: pass
            return None

        if result[0] is None:
             print(f"Error: Image generation failed for {os.path.basename(path)} (Check [Thread Error] above if any).")
             # No need to delete temp_path here as result[0] being None implies it wasn't created or was handled in target_wrapper
             return None

        # Move the successfully created temp file to the final path
        os.rename(temp_path, path)
        print(f"Saved chart image to: {os.path.basename(path)}")
        temp_path = None # Prevent deletion in finally block
        return path

    except Exception as img_err:
        print(f"Error saving chart image to {os.path.basename(path)}: {img_err}")
        # temp_path might not be defined if error occurred before its assignment
        if 'temp_path' in locals() and temp_path and os.path.exists(temp_path):
             try: os.remove(temp_path)
             except OSError: pass
        return None
    finally:
        # Clean up temp file only if it still exists and wasn't renamed
        if 'temp_path' in locals() and temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# Helper function to prepare common data (Keep Unchanged)
def _prepare_report_data(ticker, actual_data, forecast_data, historical_data, fundamentals, plot_period_years):
    # ... (implementation unchanged) ...
    data_out = {}

    # --- Data Validation ---
    required_hist_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    if historical_data is None or historical_data.empty:
        raise ValueError("Historical data is missing or empty.")
    if not all(col in historical_data.columns for col in required_hist_cols):
        missing_cols_str = ', '.join([col for col in required_hist_cols if col not in historical_data.columns])
        raise ValueError(f"Historical data missing required columns: {missing_cols_str}")
    try:
        if not pd.api.types.is_datetime64_any_dtype(historical_data['Date']):
            historical_data['Date'] = pd.to_datetime(historical_data['Date'])
    except Exception as e:
            raise ValueError(f"Historical data 'Date' column error: {e}")

    historical_data = historical_data.sort_values('Date').reset_index(drop=True)
    data_out['historical_data'] = historical_data
    hist_data_for_ta = historical_data.copy()

    # --- Determine time column and label ---
    time_col = "Period"; period_label = "Period"
    if forecast_data is not None and not forecast_data.empty and "Period" in forecast_data.columns:
        first_period = str(forecast_data['Period'].iloc[0])
        if '-' in first_period:
             parts = first_period.split('-')
             if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 2: period_label = "Month" #YYYY-MM
             elif len(parts) == 3 and len(parts[0]) == 4 and len(parts[1]) == 2 and len(parts[2]) == 2: period_label = "Day" #YYYY-MM-DD
             elif len(parts) == 2 and len(parts[0]) == 4 and len(parts[1].upper().startswith('W')): period_label = "Week" #YYYY-Www
    elif actual_data is not None and not actual_data.empty and "Period" in actual_data.columns:
        first_period = str(actual_data['Period'].iloc[0])
        if '-' in first_period:
             parts = first_period.split('-')
             if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 2: period_label = "Month" #YYYY-MM
             elif len(parts) == 3 and len(parts[0]) == 4 and len(parts[1]) == 2 and len(parts[2]) == 2: period_label = "Day" #YYYY-MM-DD
             elif len(parts) == 2 and len(parts[0]) == 4 and len(parts[1].upper().startswith('W')): period_label = "Week" #YYYY-Www

    data_out['time_col'] = time_col
    data_out['period_label'] = period_label

    # --- Calculate Detailed TA Data ---
    print("Calculating detailed technical analysis data...")
    detailed_ta_data = calculate_detailed_ta(hist_data_for_ta)
    data_out['detailed_ta_data'] = detailed_ta_data # Store detailed TA data

    # --- Calculate Key Metrics ---
    print("Calculating key metrics...")
    current_price = detailed_ta_data.get('Current_Price')
    last_date = historical_data['Date'].iloc[-1] if not historical_data.empty else datetime.now(pytz.utc)
    volatility = None; green_days = None; total_days = 0
    if len(historical_data) > 1:
        last_30_days_df = historical_data.iloc[-min(30, len(historical_data)):]
        if len(last_30_days_df) > 1:
            daily_returns = last_30_days_df['Close'].pct_change().dropna()
            if not daily_returns.empty:
                volatility_std_dev = daily_returns.std()
                # Ensure volatility_std_dev is not NaN before calculation
                if not pd.isna(volatility_std_dev):
                    volatility = volatility_std_dev * np.sqrt(252) * 100
                else:
                    volatility = 0.0 # Or handle as None if preferred
            else: volatility = 0.0
            price_diff = last_30_days_df['Close'].diff().dropna()
            green_days = (price_diff > 0).sum(); total_days = len(price_diff)
    if volatility is None or pd.isna(volatility): volatility = None
    else: volatility = float(volatility)

    sma50 = detailed_ta_data.get('SMA_50'); sma200 = detailed_ta_data.get('SMA_200')
    latest_rsi = detailed_ta_data.get('RSI_14')

    forecast_horizon_periods = 0; forecast_12m = pd.DataFrame(); final_forecast_average = None; forecast_1m = None
    if forecast_data is not None and not forecast_data.empty and 'Average' in forecast_data.columns:
        # Determine the number of periods equivalent to 1 year based on the label
        periods_in_year = 12 if period_label == "Month" else 52 if period_label == "Week" else 252 if period_label == "Day" else len(forecast_data)
        periods_in_month = 4 if period_label == "Week" else 21 if period_label == "Day" else 1 if period_label == "Month" else 1

        idx_1m = min(periods_in_month - 1, len(forecast_data)-1)
        idx_1y = min(periods_in_year - 1, len(forecast_data)-1)

        if len(forecast_data) > 0:
             forecast_1m = forecast_data['Average'].iloc[idx_1m]
             final_forecast_average = forecast_data['Average'].iloc[idx_1y]

        # Show up to 24 months, 52 weeks, or ~252 days in the table
        max_table_periods = 24 if period_label=="Month" else 52 if period_label=="Week" else 252 if period_label=="Day" else len(forecast_data)
        forecast_table_periods = min(len(forecast_data), max_table_periods)
        forecast_12m = forecast_data.head(forecast_table_periods)
        forecast_horizon_periods = len(forecast_data) # Total number of forecast periods

    overall_pct_change = 0.0
    if current_price is not None and final_forecast_average is not None and current_price != 0:
        overall_pct_change = ((final_forecast_average - current_price) / current_price) * 100

    sentiment = determine_sentiment(detailed_ta_data, overall_pct_change)

    data_out['current_price'] = current_price
    data_out['last_date'] = last_date
    data_out['volatility'] = volatility
    data_out['green_days'] = green_days
    data_out['total_days'] = total_days
    data_out['sma_50'] = sma50
    data_out['sma_200'] = sma200
    data_out['latest_rsi'] = latest_rsi
    data_out['forecast_1m'] = forecast_1m
    data_out['forecast_1y'] = final_forecast_average
    data_out['overall_pct_change'] = overall_pct_change
    data_out['sentiment'] = sentiment
    data_out['forecast_horizon_periods'] = forecast_horizon_periods
    data_out['actual_data'] = actual_data
    data_out['forecast_data'] = forecast_data

    # --- Prepare Data for Forecast Table ---
    print("Preparing forecast table data...")
    monthly_forecast_table_data = forecast_12m.copy()
    if not monthly_forecast_table_data.empty:
         if 'Average' in monthly_forecast_table_data.columns and current_price is not None and current_price != 0:
             monthly_forecast_table_data['Potential ROI'] = ((monthly_forecast_table_data['Average'] - current_price) / current_price) * 100
             monthly_forecast_table_data['Action'] = monthly_forecast_table_data['Potential ROI'].apply( lambda x: 'Buy' if x > 2 else ('Short' if x < -2 else 'Hold'))
         else:
             monthly_forecast_table_data['Potential ROI'] = 0.0
             monthly_forecast_table_data['Action'] = 'N/A'
             # Ensure Low/High columns exist even if only Average was present
             if 'Average' in monthly_forecast_table_data.columns:
                 if 'Low' not in monthly_forecast_table_data.columns: monthly_forecast_table_data['Low'] = monthly_forecast_table_data['Average']
                 if 'High' not in monthly_forecast_table_data.columns: monthly_forecast_table_data['High'] = monthly_forecast_table_data['Average']
    data_out['monthly_forecast_table_data'] = monthly_forecast_table_data


    # --- Extract Fundamental Data ---
    print("Extracting fundamental data sections...")
    data_out['profile_data'] = extract_company_profile(fundamentals)
    data_out['valuation_data'] = extract_valuation_metrics(fundamentals)
    data_out['financial_health_data'] = extract_financial_health(fundamentals)
    data_out['profitability_data'] = extract_profitability(fundamentals)
    data_out['dividends_data'] = extract_dividends_splits(fundamentals)
    data_out['analyst_info_data'] = extract_analyst_info(fundamentals)
    data_out['news_list'] = extract_news(fundamentals)
    data_out['total_valuation_data'] = extract_total_valuation_data(fundamentals, current_price)
    data_out['share_statistics_data'] = extract_share_statistics_data(fundamentals, current_price)
    data_out['financial_efficiency_data'] = extract_financial_efficiency_data(fundamentals)
    data_out['stock_price_stats_data'] = extract_stock_price_stats_data(fundamentals)
    data_out['short_selling_data'] = extract_short_selling_data(fundamentals)

    # --- Calculate Risk Items ---
    print("Calculating risk factors...")
    risk_items = []
    currency_symbol = get_currency_symbol(ticker)
    # --- (Risk calculation logic remains the same) ---
    if sentiment.lower().find('bearish') != -1: risk_items.append(f"Overall technical sentiment is {sentiment}, suggesting caution.")
    if current_price is not None:
        if sma50 is not None and current_price < sma50: risk_items.append(f"Price ({currency_symbol}{current_price:,.2f}) is below the 50-Day SMA ({currency_symbol}{sma50:,.2f}), indicating potential short-term weakness.")
        if sma200 is not None and current_price < sma200: risk_items.append(f"Price ({currency_symbol}{current_price:,.2f}) is below the 200-Day SMA ({currency_symbol}{sma200:,.2f}), indicating potential long-term weakness.")
    if latest_rsi is not None and not pd.isna(latest_rsi) and latest_rsi > 70: risk_items.append(f"RSI ({latest_rsi:.1f}) is high (>70), suggesting potential overbought conditions.")
    # Only add oversold as a risk if sentiment isn't already strongly bullish
    if latest_rsi is not None and not pd.isna(latest_rsi) and latest_rsi < 30 and "Strong Bullish" not in sentiment:
         risk_items.append(f"RSI ({latest_rsi:.1f}) is low (<30), suggesting potential oversold conditions (which could precede further downside or a rebound).")

    # Check Debt/Equity from extracted data
    debt_equity_str = data_out['financial_health_data'].get('Debt/Equity (MRQ)', 'N/A')
    if debt_equity_str != 'N/A' and isinstance(debt_equity_str, str) and 'x' in debt_equity_str :
        try: debt_equity_val = float(debt_equity_str.replace('x',''))
        except (ValueError, TypeError): debt_equity_val = None
        if debt_equity_val is not None and debt_equity_val > 2.0 :
              risk_items.append(f"High Debt-to-Equity ratio ({debt_equity_str}) indicates significant financial leverage risk.")

    # Check Current Ratio from extracted data
    current_ratio_str = data_out['financial_health_data'].get('Current Ratio (MRQ)', 'N/A')
    if current_ratio_str != 'N/A' and isinstance(current_ratio_str, str) and 'x' in current_ratio_str :
        try: current_ratio_val = float(current_ratio_str.replace('x',''))
        except (ValueError, TypeError): current_ratio_val = None
        if current_ratio_val is not None and current_ratio_val < 1.0 :
              risk_items.append(f"Current Ratio ({current_ratio_str}) is below 1.0, suggesting potential short-term liquidity challenges.")

    # Check Revenue Growth from extracted data
    revenue_growth_str = data_out['profitability_data'].get('Revenue Growth (YoY)', 'N/A')
    if revenue_growth_str != 'N/A' and isinstance(revenue_growth_str, str) and '%' in revenue_growth_str:
        try: rev_growth = float(revenue_growth_str.replace('%',''))
        except (ValueError, TypeError): rev_growth = None
        if rev_growth is not None and rev_growth < 0:
            risk_items.append(f"Negative year-over-year revenue growth ({revenue_growth_str}) poses a risk to future performance.")

    # Check Earnings Growth from extracted data
    earnings_growth_str = data_out['profitability_data'].get('Earnings Growth (YoY)', 'N/A')
    if earnings_growth_str != 'N/A' and isinstance(earnings_growth_str, str) and '%' in earnings_growth_str:
        try: earn_growth = float(earnings_growth_str.replace('%',''))
        except (ValueError, TypeError): earn_growth = None
        if earn_growth is not None and earn_growth < 0:
            risk_items.append(f"Negative year-over-year earnings growth ({earnings_growth_str}) raises concerns about profitability trends.")

    sector = data_out['profile_data'].get('Sector', 'N/A')
    if sector != 'N/A':
        risk_items.append(f"General market fluctuations and economic conditions can impact stocks in the {sector} sector.")


    data_out['risk_items'] = risk_items
    data_out['sector'] = data_out['profile_data'].get('Sector', 'N/A')
    data_out['industry'] = data_out['profile_data'].get('Industry', 'N/A')

    # --- Generate Data-Driven Observations / "Best Possible Tactics" ---
    print("Generating data-driven observations...")
    observations = []
    
    # Heuristic 1: Undervalued based on P/E, Earnings Growth, and Debt/Equity
    try:
        valuation_metrics = data_out.get('valuation_data', {})
        profitability_metrics = data_out.get('profitability_data', {})
        health_metrics = data_out.get('financial_health_data', {})

        # Get P/E (Forward or Trailing, prefer Forward)
        pe_value_str = valuation_metrics.get('Forward P/E')
        if pe_value_str is None or pe_value_str == "N/A":
            pe_value_str = valuation_metrics.get('Trailing P/E')
        
        pe_value = None
        if pe_value_str and pe_value_str != "N/A":
            pe_value = float(str(pe_value_str).replace('x', ''))

        earnings_growth_str = profitability_metrics.get('Earnings Growth (YoY)')
        earnings_growth_value = None
        if earnings_growth_str and earnings_growth_str != "N/A":
            earnings_growth_value = float(str(earnings_growth_str).replace('%', ''))

        debt_equity_str = health_metrics.get('Debt/Equity (MRQ)')
        debt_equity_value = None
        if debt_equity_str and debt_equity_str != "N/A":
            debt_equity_value = float(str(debt_equity_str).replace('x', ''))

        # Define thresholds for the heuristic (these can be fine-tuned)
        pe_threshold_low = 15  # Example: P/E below 15 is considered low
        earnings_growth_threshold_strong = 10  # Example: YoY Earnings growth above 10% is strong
        debt_equity_threshold_manageable = 1.5  # Example: D/E below 1.5 is manageable

        if pe_value is not None and earnings_growth_value is not None and debt_equity_value is not None:
            if (pe_value < pe_threshold_low and 
                earnings_growth_value > earnings_growth_threshold_strong and 
                debt_equity_value < debt_equity_threshold_manageable):
                observation = (
                    f"Data-Driven Observation: The combination of a relatively low P/E ratio ({pe_value_str}), "
                    f"strong recent earnings growth ({earnings_growth_str} YoY), and manageable debt levels "
                    f"(Debt/Equity: {debt_equity_str}) suggests the company might be currently undervalued "
                    f"relative to its performance and financial stability. This pattern often interests value-oriented "
                    f"investors looking for growth potential."
                )
                observations.append(observation)
    except Exception as e:
        print(f"Warning: Could not generate heuristic 1 for data-driven observations: {e}")

    # Heuristic 2: Technical Pattern - Approaching Resistance + Overbought RSI (Example)
    try:
        detailed_ta = data_out.get('detailed_ta_data', {})
        current_price = data_out.get('current_price')
        rsi_value = detailed_ta.get('RSI_14')
        # Note: 'resistance_price' would need to be calculated and added to rdata, perhaps in calculate_detailed_ta
        # For this example, let's assume it could be fetched or is a placeholder concept
        resistance_price = detailed_ta.get('Recent_High') # Using Recent_High as a proxy for a resistance level

        if current_price is not None and rsi_value is not None and resistance_price is not None:
            if (abs(current_price - resistance_price) / resistance_price < 0.05 and # Within 5% of resistance
                rsi_value > 70): # RSI is overbought
                observation = (
                            f"Technical Pattern to Watch: The stock price (${current_price:.2f}) is currently approaching a significant short-term resistance level "
        f"(around ${resistance_price:.2f}) while the RSI ({rsi_value:.1f}) is nearing overbought territory. "
                    f"This convergence warrants attention, as it could signal a potential pause or pullback in the uptrend unless a decisive breakout occurs on strong volume."
                )
                observations.append(observation)
    except Exception as e:
        print(f"Warning: Could not generate heuristic 2 for data-driven observations: {e}")


    data_out['data_driven_observations'] = observations

    return data_out


# --- Full Report Generation Function (Keep Unchanged) ---
def create_full_report(
    ticker,
    actual_data,
    forecast_data,
    historical_data,
    fundamentals,
    ts,
    aggregation=None, 
    app_root=None,
    plot_period_years=3
    # removed evaluation_metrics - handled internally now
):
    global custom_style
    print(f"[Full Report] Starting generation for {ticker}...")

    # Define the directory for full reports as static/stock_reports
    reports_dir = os.path.join(app_root, 'static', 'stock_reports') if app_root else os.path.join('static', 'stock_reports')
    os.makedirs(reports_dir, exist_ok=True)
    print(f"[Full Report] Reports directory: {reports_dir}")

    try:
        rdata = _prepare_report_data(ticker, actual_data, forecast_data, historical_data, fundamentals, plot_period_years)
        print("[Full Report] Generating plots...")
        def fig_to_html(fig, include_plotlyjs=True, full_html=False, div_id=None, config=None):
            # ... (fig_to_html implementation unchanged) ...
            if fig is None: return ""
            default_config = {'displayModeBar': True, 'displaylogo': False, 'responsive': True}
            merged_config = default_config.copy()
            if config: merged_config.update(config)
            try:
                 # Add error handling for large figures
                 if fig.to_dict().__sizeof__() > 5 * 1024 * 1024: # Example limit: 5MB
                     print(f"Warning: Plotly figure '{div_id}' is large, might impact performance.")
                 return to_html(fig, include_plotlyjs='cdn', full_html=full_html, div_id=div_id, config=merged_config)
            except Exception as e:
                 print(f"[Full Report] Error rendering plot '{div_id}' to HTML: {e}")
                 return f'<p style="color:red;">Error rendering plot: {e}</p>'


        # --- Forecast Chart (Plotly - logic unchanged) ---
        forecast_chart_fig = go.Figure()
        display_actual = rdata.get('actual_data')
        forecast_table = rdata.get('monthly_forecast_table_data')
        period_label = rdata.get('period_label', 'Period')
        time_col = rdata.get('time_col', 'Period')
        forecast_1y = rdata.get('forecast_1y')
        overall_pct_change = rdata.get('overall_pct_change', 0.0)
        display_actual_plot = display_actual.tail(6) if display_actual is not None else pd.DataFrame()
        time_axis_parts = []
        if not display_actual_plot.empty and time_col in display_actual_plot.columns: time_axis_parts.append(display_actual_plot[time_col])
        if forecast_table is not None and not forecast_table.empty and time_col in forecast_table.columns: time_axis_parts.append(forecast_table[time_col])
        try:
            if time_axis_parts: combined_time_axis = sorted(list(pd.concat(time_axis_parts).unique()))
            else: combined_time_axis = []
        except TypeError: combined_time_axis = list(pd.concat(time_axis_parts).unique()) if time_axis_parts else []

        if not display_actual_plot.empty and 'Average' in display_actual_plot.columns:
             forecast_chart_fig.add_trace( go.Scatter(x=display_actual_plot[time_col], y=display_actual_plot['Average'], mode='lines+markers', name='Actual', line=dict(color='#1f77b4', width=2), marker=dict(size=6), hovertemplate=f"<b>%{{x}} ({period_label})</b><br><b>Actual Avg</b>: %{{y:.2f}}<extra></extra>"))
        if forecast_table is not None and not forecast_table.empty:
            colors = {'Low': '#d62728', 'Average': '#2ca02c', 'High': '#9467bd'}
            plot_cols = ['Low', 'Average', 'High'] if all(c in forecast_table for c in ['Low', 'Average', 'High']) else ['Average']
            for col in plot_cols:
                 forecast_chart_fig.add_trace(go.Scatter(x=forecast_table[time_col], y=forecast_table[col], mode='lines+markers', name=f'Fcst {col}', line=dict(color=colors[col], width=2), marker=dict(size=6, line=dict(width=1, color='#ffffff')), hovertemplate=f"<b>%{{x}} ({period_label})</b><br><b>{col}</b>: %{{y:.2f}}<extra></extra>"))
            if forecast_1y is not None and 'Average' in forecast_table.columns and time_col in forecast_table.columns:
                 annotation_text = (f"<b>{forecast_1y:.2f}</b><br><span style='color:{colors['Average']};'>{overall_pct_change:+.1f}% (1Y)</span>")
                 last_time_period = forecast_table[time_col].iloc[-1]
                 ax_val = 30; ay_val = -30
                 if len(forecast_table) > 1:
                     try: # Handle potential non-numeric comparison errors
                         y_second_last = forecast_table['Average'].iloc[-2]
                         if pd.to_numeric(forecast_1y, errors='coerce') < pd.to_numeric(y_second_last, errors='coerce'): ay_val = 30
                     except (TypeError, IndexError): pass # Keep default annotation position on error
                 forecast_chart_fig.add_annotation(x=last_time_period, y=forecast_1y, text=annotation_text, showarrow=True, arrowhead=2, ax=ax_val, ay=ay_val, bgcolor='rgba(255,255,255,0.8)', font=dict(color=colors['Average'], size=10), bordercolor='black', borderwidth=1)

        forecast_chart_fig.update_layout(
            title=dict(text=f"{ticker} Price Forecast ({rdata.get('forecast_horizon_periods', 0)} {period_label}s)", y=0.98, x=0.5, xanchor='center', yanchor='top', font_size=14),
            legend=dict(orientation="h", yanchor="top", y=0.92, xanchor="center", x=0.5, font_size=10),
            xaxis=dict(title=period_label, type="category", categoryorder='array', categoryarray=combined_time_axis, tickangle=-45, tickformat="%b %Y", tickfont_size=10, domain=[0, 1], automargin=True),
            yaxis_title="Price ($)", yaxis=dict(domain=[0, 0.85], tickfont_size=10, automargin=True),
            margin=dict(l=35, r=25, t=80, b=40), autosize=True, template="plotly_white", showlegend=True
        )
        forecast_chart_html = fig_to_html(forecast_chart_fig, div_id='forecast-chart-div')


        # --- Technical Analysis Charts HTML (Plotly - logic unchanged) ---
        hist_data_for_ta = rdata['historical_data'].copy()
        historical_line_fig = plot_historical_line_chart(hist_data_for_ta, ticker)
        historical_chart_html = fig_to_html(historical_line_fig, div_id='hist-chart-div', include_plotlyjs=False)
        bb_fig, bb_conclusion = plot_price_bollinger(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
        bb_chart_html = fig_to_html(bb_fig, div_id='bb-chart-div', include_plotlyjs=False)
        rsi_fig, rsi_conclusion = plot_rsi(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
        rsi_chart_html = fig_to_html(rsi_fig, div_id='rsi-chart-div', include_plotlyjs=False)
        macd_conclusion = get_macd_conclusion(rdata['detailed_ta_data'].get('MACD_Line'), rdata['detailed_ta_data'].get('MACD_Signal'), rdata['detailed_ta_data'].get('MACD_Hist'), rdata['detailed_ta_data'].get('MACD_Hist_Prev')) if rdata['detailed_ta_data'].get('MACD_Hist') is not None else "MACD conclusion requires more data."
        macd_lines_fig, _ = plot_macd_lines(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
        macd_lines_chart_html = fig_to_html(macd_lines_fig, div_id='macd-lines-chart-div', include_plotlyjs=False)
        macd_hist_fig, _ = plot_macd_histogram(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
        macd_hist_chart_html = fig_to_html(macd_hist_fig, div_id='macd-hist-chart-div', include_plotlyjs=False)

        # --- Generate HTML Components (logic unchanged) ---
        print("[Full Report] Generating HTML components...")
        intro_html = generate_introduction_html(ticker, rdata)
        metrics_summary_html = generate_metrics_summary_html(ticker, rdata)
        detailed_forecast_table_html = generate_detailed_forecast_table_html(ticker, rdata)
        company_profile_html = generate_company_profile_html(ticker, rdata)
        total_valuation_html = generate_total_valuation_html(ticker, rdata)
        share_statistics_html = generate_share_statistics_html(ticker, rdata)
        valuation_metrics_html = generate_valuation_metrics_html(ticker, rdata)
        financial_health_html = generate_financial_health_html(ticker, rdata)
        financial_efficiency_html = generate_financial_efficiency_html(ticker, rdata)
        profitability_growth_html = generate_profitability_growth_html(ticker, rdata)
        dividends_shareholder_returns_html = generate_dividends_shareholder_returns_html(ticker, rdata)
        technical_analysis_summary_html = generate_technical_analysis_summary_html(ticker, rdata) 
        stock_price_statistics_html = generate_stock_price_statistics_html(ticker, rdata)
        short_selling_info_html = generate_short_selling_info_html(ticker, rdata)
        risk_factors_html = generate_risk_factors_html(ticker, rdata)
        analyst_insights_html = generate_analyst_insights_html(ticker, rdata)
        recent_news_html = generate_recent_news_html(ticker, rdata)
        
        conclusion_outlook_html = generate_conclusion_outlook_html(ticker, rdata)
        faq_html = generate_faq_html(ticker, rdata)
        report_info_disclaimer_html = generate_report_info_disclaimer_html(datetime.now(pytz.utc))

        # --- Assemble Final HTML Structure (structure unchanged) ---
        print("[Full Report] Assembling final HTML structure...")
        report_body_content = f'<h1 class="report-title">{ticker} Stock Analysis & Price Forecast ({datetime.now(pytz.utc):%Y-%m-%d})</h1>\n'
        html_sections = [
            ("Introduction and Overview", intro_html, "introduction-overview"),
            ("Key Metrics and Forecast Summary", metrics_summary_html, "key-metrics-forecast"),
            ("Price Forecast Chart", forecast_chart_html, "forecast-chart", "<div class=\"narrative\"><p>The chart below shows recent actual average prices and the forecasted price range (Low, Average, High) based on the Prophet model.</p></div>"),
            ("Detailed Forecast Table", detailed_forecast_table_html, "detailed-forecast-table"),
            ("Company Profile", company_profile_html, "company-profile"),
            ("Total Valuation", total_valuation_html, "total-valuation"),
            ("Share Statistics", share_statistics_html, "share-statistics"),
            ("Valuation Metrics", valuation_metrics_html, "valuation-metrics"),
            ("Financial Health", financial_health_html, "financial-health"),
            ("Financial Efficiency", financial_efficiency_html, "financial-efficiency"),
            ("Profitability and Growth", profitability_growth_html, "profitability-growth"),
            ("Dividends and Shareholder Returns", dividends_shareholder_returns_html, "dividends-shareholder-returns"),
            ("Technical Analysis", technical_analysis_summary_html, "technical-analysis-summary"),
            ("Bollinger Bands Chart", bb_chart_html, "tech-chart-bb"),
            ("RSI Chart", rsi_chart_html, "tech-chart-rsi"),
            ("MACD Charts",
             f'<div class="indicator-chart-container">{macd_lines_chart_html or ""}</div>' +
             f'<div class="indicator-chart-container">{macd_hist_chart_html or ""}</div>',
             "tech-chart-macd-combined"),
            ("Historical Price & Volume Chart", historical_chart_html, "historical-chart", "<div class=\"narrative\"><p>Historical closing price and volume (with 20d avg). Use buttons above chart to change range.</p></div>"),
            ("Historical Performance", generate_historical_performance_html(ticker, rdata), "historical-performance"),
            ("Stock Price Statistics", stock_price_statistics_html, "stock-price-statistics"),
            ("Short Selling Information", short_selling_info_html, "short-selling-information"),
            ("Risk Factors", risk_factors_html, "risk-factors"),
            ("Analyst Insights and Consensus", analyst_insights_html, "analyst-insights"),
            ("Recent News and Developments", recent_news_html, "recent-news"),
            ("Conclusion and Outlook", conclusion_outlook_html, "conclusion-outlook"),
            ("Frequently Asked Questions", faq_html, "frequently-asked-questions"),
            ("Report Information and Disclaimer", report_info_disclaimer_html, "report-information-disclaimer")
        ]
        # --- (Loop to build report body remains the same) ---
        for item in html_sections:
            title, html_content = item[0], item[1]
            section_class = item[2] if len(item) > 2 else title.lower().replace(" ", "-").replace("&", "and")
            narrative = item[3] if len(item) > 3 else None
            conclusion = item[4] if len(item) > 4 else None
            has_content = bool(html_content and str(html_content).strip() and not str(html_content).startswith(("<p>No data",'<p style="color:red;">Error')))
            is_chart_section = section_class.startswith("tech-chart-") or section_class in ["historical-chart", "forecast-chart"]
            if has_content or (is_chart_section and (html_content or conclusion)):
                 report_body_content += f'<div class="section {section_class}">\n  <h2>{title}</h2>\n'
                 if narrative: report_body_content += f"  {narrative}\n"
                 chart_fallback_message = f'<p style="text-align:center; color:red; padding: 2rem 1rem;">Chart for {title} could not be generated.</p>'
                 if section_class == "tech-chart-macd-combined":
                     # Handles potentially multiple charts + conclusion
                     report_body_content += f"  {html_content or chart_fallback_message}\n"
                 elif is_chart_section:
                     # Standard single chart + conclusion structure
                     chart_html = html_content or chart_fallback_message
                     report_body_content += f'  <div class="indicator-chart-container">{chart_html}</div>\n'
                     if conclusion: report_body_content += f'  <div class="indicator-conclusion">{conclusion}</div>\n'
                 elif has_content:
                     # Non-chart sections
                     report_body_content += f"  {html_content}\n"
                 report_body_content += f'</div>\n'
            else:
                 print(f"[Full Report] Skipping empty or failed section: {title}")


        # --- Assemble Final HTML Document (unchanged) ---
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} Stock Analysis Report</title>
    {custom_style}
    <script src='https://cdn.plot.ly/plotly-latest.min.js'></script>
</head>
<body>
    <div class="report-container">
        {report_body_content}
    </div>
    <script>
       window.addEventListener('load', function() {{
           setTimeout(function() {{
               var allPlotlyDivs = document.querySelectorAll('.plotly-graph-div');
               allPlotlyDivs.forEach(function(div) {{
                   try {{ Plotly.Plots.resize(div); }} catch(e) {{ console.warn("Plotly resize failed for div:", div.id, e); }}
               }});
               console.log("Attempted Plotly resize on load for full report.");
           }}, 500);
       }});
    </script>
</body>
</html>"""

        # Save Report
        report_filename = f"{ticker}_detailed_report_{ts}.html"
        report_path = os.path.join(reports_dir, report_filename) # Use reports_dir (static/stock_reports)
        try:
            with open(report_path, 'w', encoding='utf-8') as f: f.write(full_html)
            print(f"[Full Report] Successfully generated and saved report: {report_path}")
        except Exception as e:
            print(f"[Full Report] Error writing report file to {report_path}: {e}")
            return None, full_html # Return HTML even if saving failed

        return report_path, full_html

    except ValueError as ve:
        print(f"[Full Report] Value Error during report generation for {ticker}: {ve}")
        return None, f"<html><body><h2>Error Generating Report for {ticker}</h2><p>{ve}</p></body></html>"
    except Exception as e:
        print(f"[Full Report] Unexpected Error during report generation for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return None, f"<html><body><h2>Unexpected Error Generating Report for {ticker}</h2><p>{e}</p></body></html>"


# --- WordPress Report Assets Generation Function (MODIFIED FOR BASE64) ---
def create_wordpress_report_assets(
    ticker,
    actual_data,
    forecast_data,
    historical_data,
    fundamentals,
    ts,
    aggregation=None,
    app_root=None,
    plot_period_years=3
):
    global custom_style
    print(f"[WP Assets] Starting generation for {ticker}...") # Use logger

    if not app_root:
        app_root = os.path.dirname(os.path.abspath(__file__)) # Fallback
        print(f"[WP Assets] Warning: app_root not provided, defaulting to script directory: {app_root}") # Use logger

    # Define a new directory for temporary image assets, ensuring it's unique per run or cleaned
    report_assets_dir = os.path.join(app_root, 'report_assets', f"{ticker}_{ts}") # This remains separate for temporary assets
    os.makedirs(report_assets_dir, exist_ok=True)
    print(f"[WP Assets] Report assets directory: {report_assets_dir}") # Use logger

    chart_image_base64 = {}
    saved_forecast_chart_path = None # To store the path of the saved forecast chart

    try:
        rdata = _prepare_report_data(ticker, actual_data, forecast_data, historical_data, fundamentals, plot_period_years)
        hist_data_for_images = rdata['historical_data'].copy()

        image_configs = [
            ('forecast', plot_forecast_mpl, rdata),
            ('historical_price_volume', plot_historical_mpl, hist_data_for_images.copy()),
            ('bollinger_bands', plot_bollinger_mpl, hist_data_for_images.copy()),
            ('rsi', plot_rsi_mpl, hist_data_for_images.copy()),
            ('macd_lines', plot_macd_lines_mpl, hist_data_for_images.copy()),
            ('macd_histogram', plot_macd_hist_mpl, hist_data_for_images.copy())
        ]

        print("[WP Assets] Generating Matplotlib charts...") # Use logger
        chart_conclusions = {}
        for config_item in image_configs:
            chart_key = config_item[0]
            mpl_func = config_item[1]
            data_arg = config_item[2]

            print(f"  Generating {chart_key} for {ticker}...") # Use logger
            if mpl_func is None: continue

            mpl_fig = None
            try:
                if chart_key == 'forecast':
                    mpl_fig = mpl_func(data_arg, ticker)
                else:
                    mpl_fig = mpl_func(data_arg, ticker, plot_period_years=plot_period_years)

                if mpl_fig is None:
                    print(f"    FAILED (Plot Generation): Function '{mpl_func.__name__}' returned None for '{chart_key}'.") # Use logger
                    continue

                # --- MODIFICATION FOR FORECAST CHART ---
                if chart_key == 'forecast':
                    forecast_chart_filename = f"{ticker}_forecast_featured_{ts}.png"
                    # Save in the unique temp_images_dir for this ticker and timestamp
                    saved_forecast_chart_path = os.path.join(report_assets_dir, forecast_chart_filename) # Use report_assets_dir
                    mpl_fig.savefig(saved_forecast_chart_path, bbox_inches='tight', dpi=150) # Save with decent DPI
                    print(f"    Successfully saved '{chart_key}' chart to: {saved_forecast_chart_path}") # Use logger
                    # Optionally, still generate Base64 for embedding in HTML body if needed
                    # base64_str = get_mpl_base64_from_file(saved_forecast_chart_path)
                    # For simplicity, we'll assume if it's a featured image, it might not also be in the body,
                    # or if it is, your existing get_img_tag will use the base64 version if populated.
                    # If you want the saved forecast chart also as base64 in the HTML:
                    base64_str_forecast = get_mpl_base64_from_file(saved_forecast_chart_path)
                    if base64_str_forecast:
                        chart_image_base64[chart_key] = base64_str_forecast
                    plt.close(mpl_fig) # Close the figure
                else:
                    # For other charts, convert to Base64 as before for HTML embedding
                    print(f"    Encoding {chart_key} to Base64...") # Use logger
                    base64_str = get_mpl_base64(mpl_fig) # This function already closes the fig
                    if base64_str:
                        chart_image_base64[chart_key] = base64_str
                        print(f"    Successfully encoded '{chart_key}'.") # Use logger
                    else:
                        print(f"    FAILED (Base64 Encoding) for '{chart_key}'.") # Use logger
                        chart_image_base64[chart_key] = None
                # --- END MODIFICATION ---

                conclusion_data = rdata['detailed_ta_data']
                if chart_key == 'bollinger_bands':
                    chart_conclusions['bollinger_bands'] = get_bb_conclusion(
                        conclusion_data.get('Current_Price'),
                        conclusion_data.get('BB_Upper'),
                        conclusion_data.get('BB_Lower'),
                        conclusion_data.get('BB_Middle')
                    )
                elif chart_key == 'rsi':
                    chart_conclusions['rsi'] = get_rsi_conclusion(conclusion_data.get('RSI_14'))
                elif chart_key == 'macd_lines' or chart_key == 'macd_histogram': # Combined conclusion
                     chart_conclusions['macd'] = get_macd_conclusion(
                         conclusion_data.get('MACD_Line'),
                         conclusion_data.get('MACD_Signal'),
                         conclusion_data.get('MACD_Hist'),
                         conclusion_data.get('MACD_Hist_Prev')
                     )


            except Exception as e_chart:
                print(f"    FAILED (Generation/Encoding/Saving) for '{chart_key}': {e_chart}") # Use logger
                import traceback
                traceback.print_exc()
                if mpl_fig and plt.fignum_exists(mpl_fig.number): # Check if fig exists and is open
                     plt.close(mpl_fig)
                chart_image_base64[chart_key] = None
                if chart_key == 'forecast': # Ensure path is None if saving failed
                    saved_forecast_chart_path = None


        # --- Generate HTML Components (Same as before, using chart_image_base64 for embedded ones) ---
        print("[WP Assets] Generating text/table HTML components...") # Use logger
        # ... (all your intro_html, metrics_summary_html, etc. generation - unchanged) ...
        intro_html = generate_introduction_html(ticker, rdata)
        metrics_summary_html = generate_metrics_summary_html(ticker, rdata)
        detailed_forecast_table_html = generate_detailed_forecast_table_html(ticker, rdata)
        company_profile_html = generate_company_profile_html(ticker, rdata)
        total_valuation_html = generate_total_valuation_html(ticker, rdata)
        share_statistics_html = generate_share_statistics_html(ticker, rdata)
        valuation_metrics_html = generate_valuation_metrics_html(ticker, rdata)
        financial_health_html = generate_financial_health_html(ticker, rdata)
        financial_efficiency_html = generate_financial_efficiency_html(ticker, rdata)
        profitability_growth_html = generate_profitability_growth_html(ticker, rdata)
        dividends_shareholder_returns_html = generate_dividends_shareholder_returns_html(ticker, rdata)
        technical_analysis_summary_html = generate_technical_analysis_summary_html(ticker, rdata)
        stock_price_statistics_html = generate_stock_price_statistics_html(ticker, rdata)
        short_selling_info_html = generate_short_selling_info_html(ticker, rdata)
        risk_factors_html = generate_risk_factors_html(ticker, rdata)
        analyst_insights_html = generate_analyst_insights_html(ticker, rdata)
        # recent_news_html = generate_recent_news_html(ticker, rdata) # USER REQUEST: Comment out news
        conclusion_outlook_html = generate_conclusion_outlook_html(ticker, rdata)
        faq_html = generate_faq_html(ticker, rdata)


        # --- Assemble Report Body Content using Base64 Images ---
        print("[WP Assets] Assembling report body HTML with embedded images...") # Use logger
        report_body_content = ""
        def get_img_tag(key, alt_text): # This helper remains useful for body images
            base64_data = chart_image_base64.get(key)
            if base64_data:
                return f'<img src="{base64_data}" alt="{alt_text}" class="embedded-chart-image">'
            else:
                return f"<p><i>{alt_text} chart could not be generated for embedding.</i></p>"

        # --- Define sections (your existing html_sections list - unchanged) ---
        html_sections = [
            ("Introduction and Overview", intro_html, "introduction-overview"),
            ("Key Metrics and Forecast Summary", metrics_summary_html, "key-metrics-forecast"),
            ("Price Forecast Chart", # This will use the Base64 version if generated
             get_img_tag('forecast', f'{ticker} Price Forecast Chart (Embedded)') +
             "<div class='narrative'><p>Recent actual average prices vs. forecasted price range (Low, Average, High).</p></div>",
             "forecast-chart-embedded"),
            # ... (rest of your html_sections - unchanged) ...
            ("Detailed Forecast Table", detailed_forecast_table_html, "detailed-forecast-table"),
            ("Company Profile", company_profile_html, "company-profile"),
            ("Total Valuation", total_valuation_html, "total-valuation"),
            ("Share Statistics", share_statistics_html, "share-statistics"),
            ("Valuation Metrics", valuation_metrics_html, "valuation-metrics"),
            ("Financial Health", financial_health_html, "financial-health"),
            ("Financial Efficiency", financial_efficiency_html, "financial-efficiency"),
            ("Profitability and Growth", profitability_growth_html, "profitability-growth"),
            ("Dividends and Shareholder Returns", dividends_shareholder_returns_html, "dividends-shareholder-returns"),
            ("Technical Analysis", technical_analysis_summary_html, "technical-analysis-summary"),
            ("Bollinger Bands Analysis",
             get_img_tag('bollinger_bands', f'{ticker} Bollinger Bands Chart') +
             f"<div class='indicator-conclusion'>{chart_conclusions.get('bollinger_bands', 'Bollinger Bands conclusion not available.')}</div>",
             "tech-analysis-bb"),
            ("RSI Analysis",
             get_img_tag('rsi', f'{ticker} RSI Chart') +
             f"<div class='indicator-conclusion'>{chart_conclusions.get('rsi', 'RSI conclusion not available.')}</div>",
             "tech-analysis-rsi"),
            ("MACD Analysis",
             get_img_tag('macd_lines', f'{ticker} MACD Lines Chart') +
             get_img_tag('macd_histogram', f'{ticker} MACD Histogram Chart') +
             f"<div class='indicator-conclusion'>{chart_conclusions.get('macd', 'MACD conclusion not available.')}</div>",
             "tech-analysis-macd"),
            ("Historical Price & Volume",
             get_img_tag('historical_price_volume', f'{ticker} Historical Price Chart') +
             "<div class='narrative'><p>Historical closing price and volume. Range typically shows last 3 years.</p></div>",
             "historical-price-volume"),
            ("Stock Price Statistics", stock_price_statistics_html, "stock-price-statistics"),
            ("Short Selling Information", short_selling_info_html, "short-selling-information"),
            ("Risk Factors", risk_factors_html, "risk-factors"),
            ("Analyst Insights and Consensus", analyst_insights_html, "analyst-insights"),
            # ("Recent News and Developments", recent_news_html, "recent-news"), # USER REQUEST: Comment out news
            ("Conclusion and Outlook", conclusion_outlook_html, "conclusion-outlook"),
            ("Frequently Asked Questions", faq_html, "frequently-asked-questions")
        ]
        # ... (your existing loop to build report_body_content - unchanged) ...
        for item in html_sections:
            title, html_c, section_class_name = item[0], item[1], item[2]
            has_content = bool(html_c and str(html_c).strip() and not str(html_c).startswith(("<p>No data", "<p><i>")))
            if has_content:
                report_body_content += f'<div class="section {section_class_name}">\n  <h2>{title}</h2>\n'
                report_body_content += f"  {html_c}\n"
                report_body_content += f'</div>\n'
            else:
                print(f"[WP Assets] Skipping empty or failed section: {title}") # Use logger


        final_html_fragment = f"{custom_style}\n<div class=\"report-container\">\n{report_body_content}\n</div>"
        print(f"[WP Assets] HTML fragment generation complete for {ticker}.")

        # Return the HTML fragment AND the path to the saved forecast chart
        return final_html_fragment, saved_forecast_chart_path

    except ValueError as ve:
        print(f"[WP Assets] Value Error for {ticker}: {ve}") # Use logger
        return f"<h2>Error Generating Report for {ticker}</h2><p>{ve}</p>", None # Path is None on error
    except Exception as e:
        print(f"[WP Assets] Unexpected Error for {ticker}: {e}") # Use logger
        import traceback
        traceback.print_exc()
        return f"<h2>Unexpected Error Generating Report for {ticker}</h2><p>{e}</p>", None # Path is None on error