"""
Earnings Report Generator Module

Generates comprehensive, attractive HTML earnings reports using all collected data fields.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class EarningsReportGenerator:
    """
    Generates beautiful, comprehensive earnings reports using all collected data.
    """
    
    def __init__(self):
        """Initialize the report generator"""
        self.report_timestamp = datetime.now()
    
    def generate_report(self, processed_data: Dict[str, Any], report_type: str = 'full') -> str:
        """
        Generate a comprehensive earnings report.
        
        Args:
            processed_data: Processed earnings data from EarningsDataProcessor
            report_type: Type of report ('pre_earnings', 'post_earnings', or 'full')
            
        Returns:
            HTML string of the complete report
        """
        ticker = processed_data.get('ticker', 'UNKNOWN')
        earnings_data = processed_data.get('earnings_data', {})
        data_quality = processed_data.get('data_quality', {})
        
        logger.info(f"Generating {report_type} earnings report for {ticker}")
        
        # Build HTML report
        html = self._build_html_structure(
            ticker=ticker,
            earnings_data=earnings_data,
            data_quality=data_quality,
            report_type=report_type
        )
        
        return html
    
    def _build_html_structure(self, ticker: str, earnings_data: Dict[str, Any], 
                             data_quality: Dict[str, Any], report_type: str) -> str:
        """Build the complete HTML structure"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} - Comprehensive Earnings Report</title>
    {self._generate_styles()}
</head>
<body>
    <div class="container">
        {self._generate_header(ticker, earnings_data)}
        {self._generate_data_quality_badge(data_quality)}
        {self._generate_executive_summary(earnings_data)}
        {self._generate_company_overview(earnings_data)}
        {self._generate_earnings_timeline(earnings_data)}
        {self._generate_financial_performance(earnings_data)}
        {self._generate_balance_sheet_section(earnings_data)}
        {self._generate_cash_flow_section(earnings_data)}
        {self._generate_valuation_section(earnings_data)}
        {self._generate_analyst_section(earnings_data)}
        {self._generate_performance_metrics(earnings_data)}
        {self._generate_stock_price_section(earnings_data)}
        {self._generate_guidance_section(earnings_data)}
        {self._generate_key_focus_areas(earnings_data)}
        {self._generate_risk_factors(earnings_data)}
        {self._generate_footer()}
    </div>
</body>
</html>"""
    
    def _generate_styles(self) -> str:
        """Generate CSS styles for the report"""
        return """<style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header .company-name {
            font-size: 1.3em;
            opacity: 0.95;
            margin-bottom: 15px;
        }
        
        .header .timestamp {
            font-size: 0.9em;
            opacity: 0.8;
            margin-top: 10px;
        }
        
        .quality-badge {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .quality-score {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.95em;
        }
        
        .quality-high {
            background: #d4edda;
            color: #155724;
        }
        
        .quality-medium {
            background: #fff3cd;
            color: #856404;
        }
        
        .quality-low {
            background: #f8d7da;
            color: #721c24;
        }
        
        .section {
            padding: 35px 40px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .section:last-child {
            border-bottom: none;
        }
        
        .section-title {
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 25px;
            font-weight: 700;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        
        .subsection-title {
            font-size: 1.3em;
            color: #555;
            margin: 25px 0 15px 0;
            font-weight: 600;
            padding-left: 10px;
            border-left: 4px solid #764ba2;
        }
        
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }
        
        .metric-label {
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 1.6em;
            font-weight: 700;
            color: #333;
        }
        
        .metric-value.positive {
            color: #28a745;
        }
        
        .metric-value.negative {
            color: #dc3545;
        }
        
        .metric-value.neutral {
            color: #6c757d;
        }
        
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .info-table th,
        .info-table td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .info-table th {
            background: #667eea;
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }
        
        .info-table tr:last-child td {
            border-bottom: none;
        }
        
        .info-table tr:hover {
            background: #f8f9fa;
        }
        
        .highlight-box {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            padding: 25px;
            border-radius: 12px;
            margin: 20px 0;
            border: 2px solid #667eea30;
        }
        
        .analyst-ratings {
            display: flex;
            justify-content: space-around;
            margin: 25px 0;
            flex-wrap: wrap;
            gap: 20px;
        }
        
        .rating-item {
            text-align: center;
            flex: 1;
            min-width: 150px;
        }
        
        .rating-count {
            font-size: 2.5em;
            font-weight: 700;
            margin: 10px 0;
        }
        
        .rating-buy {
            color: #28a745;
        }
        
        .rating-hold {
            color: #ffc107;
        }
        
        .rating-sell {
            color: #dc3545;
        }
        
        .rating-label {
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .focus-area, .risk-item {
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-radius: 10px;
            border-left: 5px solid #764ba2;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .focus-area h4, .risk-item h4 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        
        .focus-area p, .risk-item p {
            color: #555;
            line-height: 1.7;
        }
        
        .footer {
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 30px;
            font-size: 0.9em;
        }
        
        .footer p {
            margin: 5px 0;
            opacity: 0.8;
        }
        
        .stat-comparison {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        .stat-label {
            font-weight: 600;
            color: #555;
        }
        
        .stat-value {
            font-size: 1.2em;
            font-weight: 700;
        }
        
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: 600;
            margin: 5px;
        }
        
        .badge-success {
            background: #d4edda;
            color: #155724;
        }
        
        .badge-warning {
            background: #fff3cd;
            color: #856404;
        }
        
        .badge-danger {
            background: #f8d7da;
            color: #721c24;
        }
        
        .badge-info {
            background: #d1ecf1;
            color: #0c5460;
        }
        
        @media (max-width: 768px) {
            .container {
                border-radius: 0;
            }
            
            .header {
                padding: 25px;
            }
            
            .header h1 {
                font-size: 1.8em;
            }
            
            .section {
                padding: 20px;
            }
            
            .metric-grid {
                grid-template-columns: 1fr;
            }
            
            .analyst-ratings {
                flex-direction: column;
            }
        }
    </style>"""
    
    def _generate_header(self, ticker: str, earnings_data: Dict[str, Any]) -> str:
        """Generate report header"""
        company_id = earnings_data.get('company_identification', {})
        company_name = company_id.get('company_name', 'N/A')
        sector = company_id.get('sector', 'N/A')
        
        return f"""<div class="header">
        <h1>{ticker}</h1>
        <div class="company-name">{company_name}</div>
        <div class="badge badge-info">{sector}</div>
        <div class="timestamp">Generated: {self.report_timestamp.strftime('%B %d, %Y at %I:%M %p')}</div>
    </div>"""
    
    def _generate_data_quality_badge(self, data_quality: Dict[str, Any]) -> str:
        """Generate data quality indicator"""
        completeness = data_quality.get('completeness_score', 0)
        
        if completeness >= 80:
            quality_class = 'quality-high'
            quality_text = 'High Quality Data'
        elif completeness >= 50:
            quality_class = 'quality-medium'
            quality_text = 'Moderate Quality Data'
        else:
            quality_class = 'quality-low'
            quality_text = 'Limited Data Available'
        
        return f"""<div class="quality-badge">
        <span class="quality-score {quality_class}">
            📊 {quality_text} - {completeness:.0f}% Complete
        </span>
    </div>"""
    
    def _generate_executive_summary(self, earnings_data: Dict[str, Any]) -> str:
        """Generate executive summary section"""
        company_id = earnings_data.get('company_identification', {})
        income = earnings_data.get('income_statement', {})
        valuation = earnings_data.get('valuation_metrics', {})
        stock = earnings_data.get('stock_price', {})
        
        market_cap = self._format_number(company_id.get('market_cap'), prefix='$', suffix='')
        revenue = self._format_number(income.get('total_revenue'), prefix='$', suffix='')
        net_income = self._format_number(income.get('net_income'), prefix='$', suffix='')
        eps = self._format_number(income.get('earnings_per_share_diluted'), prefix='$', decimals=2)
        pe_ratio = self._format_number(valuation.get('trailing_pe'), decimals=2)
        current_price = self._format_number(stock.get('current_price'), prefix='$', decimals=2)
        
        return f"""<div class="section">
        <h2 class="section-title">📈 Executive Summary</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Market Capitalization</div>
                <div class="metric-value">{market_cap}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Current Stock Price</div>
                <div class="metric-value">{current_price}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Revenue</div>
                <div class="metric-value">{revenue}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Net Income</div>
                <div class="metric-value {self._get_value_class(income.get('net_income'))}">{net_income}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Earnings Per Share (Diluted)</div>
                <div class="metric-value">{eps}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">P/E Ratio (Trailing)</div>
                <div class="metric-value">{pe_ratio}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_company_overview(self, earnings_data: Dict[str, Any]) -> str:
        """Generate company overview section"""
        company_id = earnings_data.get('company_identification', {})
        
        return f"""<div class="section">
        <h2 class="section-title">🏢 Company Overview</h2>
        <table class="info-table">
            <tr>
                <th>Attribute</th>
                <th>Value</th>
            </tr>
            <tr>
                <td><strong>Ticker Symbol</strong></td>
                <td>{company_id.get('ticker', 'N/A')}</td>
            </tr>
            <tr>
                <td><strong>Company Name</strong></td>
                <td>{company_id.get('company_name', 'N/A')}</td>
            </tr>
            <tr>
                <td><strong>CIK Number</strong></td>
                <td>{company_id.get('cik', 'N/A')}</td>
            </tr>
            <tr>
                <td><strong>Exchange</strong></td>
                <td>{company_id.get('exchange', 'N/A')}</td>
            </tr>
            <tr>
                <td><strong>Sector</strong></td>
                <td>{company_id.get('sector', 'N/A')}</td>
            </tr>
            <tr>
                <td><strong>Industry</strong></td>
                <td>{company_id.get('industry', 'N/A')}</td>
            </tr>
            <tr>
                <td><strong>Website</strong></td>
                <td>{company_id.get('website', 'N/A')}</td>
            </tr>
            <tr>
                <td><strong>Headquarters</strong></td>
                <td>{company_id.get('headquarters', 'N/A')}</td>
            </tr>
            <tr>
                <td><strong>CEO</strong></td>
                <td>{company_id.get('ceo_name', 'N/A')}</td>
            </tr>
        </table>
        
        <div class="highlight-box">
            <h4>Company Description</h4>
            <p>{company_id.get('description', 'No description available.')}</p>
        </div>
    </div>"""
    
    def _generate_earnings_timeline(self, earnings_data: Dict[str, Any]) -> str:
        """Generate earnings timeline section"""
        timeline = earnings_data.get('earnings_timeline', {})
        
        return f"""<div class="section">
        <h2 class="section-title">📅 Earnings Timeline</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Earnings Date</div>
                <div class="metric-value">{timeline.get('earnings_date', 'N/A')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Fiscal Quarter</div>
                <div class="metric-value">{timeline.get('fiscal_quarter', 'N/A')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Fiscal Year</div>
                <div class="metric-value">{timeline.get('fiscal_year', 'N/A')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Filing Date</div>
                <div class="metric-value">{timeline.get('filing_date', 'N/A')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Period End Date</div>
                <div class="metric-value">{timeline.get('period_end_date', 'N/A')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Filing Type</div>
                <div class="metric-value">{timeline.get('filing_type', 'N/A')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Reporting Time</div>
                <div class="metric-value">{timeline.get('reporting_type', 'N/A')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Days Until Earnings</div>
                <div class="metric-value">{timeline.get('days_until_earnings', 'N/A')}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_financial_performance(self, earnings_data: Dict[str, Any]) -> str:
        """Generate comprehensive financial performance section"""
        income = earnings_data.get('income_statement', {})
        ratios = earnings_data.get('calculated_ratios', {})
        
        return f"""<div class="section">
        <h2 class="section-title">💰 Financial Performance - Income Statement</h2>
        
        <h3 class="subsection-title">Revenue & Profitability</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Revenue</div>
                <div class="metric-value">{self._format_number(income.get('total_revenue'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Cost of Revenue</div>
                <div class="metric-value">{self._format_number(income.get('cost_of_revenue'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Gross Profit</div>
                <div class="metric-value {self._get_value_class(income.get('gross_profit'))}">{self._format_number(income.get('gross_profit'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Gross Margin</div>
                <div class="metric-value">{self._format_number(income.get('gross_margin'), suffix='%', decimals=2)}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Operating Expenses</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Operating Expenses</div>
                <div class="metric-value">{self._format_number(income.get('operating_expenses'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Research & Development</div>
                <div class="metric-value">{self._format_number(income.get('research_and_development'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Sales & Marketing</div>
                <div class="metric-value">{self._format_number(income.get('sales_and_marketing'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">General & Administrative</div>
                <div class="metric-value">{self._format_number(income.get('general_and_administrative'), prefix='$')}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Bottom Line Performance</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Operating Income</div>
                <div class="metric-value {self._get_value_class(income.get('operating_income'))}">{self._format_number(income.get('operating_income'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Operating Margin</div>
                <div class="metric-value">{self._format_number(income.get('operating_margin'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">EBITDA</div>
                <div class="metric-value">{self._format_number(income.get('ebitda'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Net Income</div>
                <div class="metric-value {self._get_value_class(income.get('net_income'))}">{self._format_number(income.get('net_income'), prefix='$')}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Per Share Metrics & Other Items</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">EPS (Basic)</div>
                <div class="metric-value">{self._format_number(income.get('earnings_per_share_basic'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">EPS (Diluted)</div>
                <div class="metric-value">{self._format_number(income.get('earnings_per_share_diluted'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Shares Outstanding (Basic)</div>
                <div class="metric-value">{self._format_number(income.get('weighted_average_shares_basic'))}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Shares Outstanding (Diluted)</div>
                <div class="metric-value">{self._format_number(income.get('weighted_average_shares_diluted'))}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Depreciation & Amortization</div>
                <div class="metric-value">{self._format_number(income.get('depreciation_and_amortization'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Tax Provision</div>
                <div class="metric-value">{self._format_number(income.get('tax_provision'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Revenue Growth YoY</div>
                <div class="metric-value {self._get_value_class(income.get('revenue_growth_yoy'))}">{self._format_number(income.get('revenue_growth_yoy'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Stock-Based Compensation</div>
                <div class="metric-value">{self._format_number(income.get('stock_based_compensation'), prefix='$')}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Profitability Ratios</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Profit Margin</div>
                <div class="metric-value">{self._format_number(ratios.get('profit_margin'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Operating Margin</div>
                <div class="metric-value">{self._format_number(ratios.get('operating_margin'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Gross Margin</div>
                <div class="metric-value">{self._format_number(ratios.get('gross_margin'), suffix='%', decimals=2)}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_balance_sheet_section(self, earnings_data: Dict[str, Any]) -> str:
        """Generate balance sheet section"""
        balance_sheet = earnings_data.get('balance_sheet', {})
        ratios = earnings_data.get('calculated_ratios', {})
        
        return f"""<div class="section">
        <h2 class="section-title">📊 Balance Sheet</h2>
        
        <h3 class="subsection-title">Assets</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Assets</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('total_assets'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Current Assets</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('current_assets'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Cash & Equivalents</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('cash_and_equivalents'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Accounts Receivable</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('accounts_receivable'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Inventory</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('inventory'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Property, Plant & Equipment</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('property_plant_equipment'), prefix='$')}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Liabilities</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Liabilities</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('total_liabilities'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Current Liabilities</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('current_liabilities'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Accounts Payable</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('accounts_payable'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Long-term Debt</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('long_term_debt'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Debt</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('total_debt'), prefix='$')}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Equity & Health Metrics</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Stockholders' Equity</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('stockholders_equity'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Retained Earnings</div>
                <div class="metric-value">{self._format_number(balance_sheet.get('retained_earnings'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Working Capital</div>
                <div class="metric-value {self._get_value_class(balance_sheet.get('working_capital'))}">{self._format_number(balance_sheet.get('working_capital'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Current Ratio</div>
                <div class="metric-value">{self._format_number(ratios.get('current_ratio'), decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Debt-to-Equity Ratio</div>
                <div class="metric-value">{self._format_number(ratios.get('debt_to_equity'), decimals=2)}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_cash_flow_section(self, earnings_data: Dict[str, Any]) -> str:
        """Generate cash flow section"""
        cash_flow = earnings_data.get('cash_flow', {})
        
        return f"""<div class="section">
        <h2 class="section-title">💵 Cash Flow Statement</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Operating Cash Flow</div>
                <div class="metric-value {self._get_value_class(cash_flow.get('operating_cash_flow'))}">{self._format_number(cash_flow.get('operating_cash_flow'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Free Cash Flow</div>
                <div class="metric-value {self._get_value_class(cash_flow.get('free_cash_flow'))}">{self._format_number(cash_flow.get('free_cash_flow'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Capital Expenditures</div>
                <div class="metric-value">{self._format_number(cash_flow.get('capital_expenditures'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Investing Cash Flow</div>
                <div class="metric-value">{self._format_number(cash_flow.get('net_cash_investing'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Financing Cash Flow</div>
                <div class="metric-value">{self._format_number(cash_flow.get('net_cash_financing'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Dividends Paid</div>
                <div class="metric-value">{self._format_number(cash_flow.get('dividends_paid'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Share Repurchases</div>
                <div class="metric-value">{self._format_number(cash_flow.get('share_repurchases'), prefix='$')}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_valuation_section(self, earnings_data: Dict[str, Any]) -> str:
        """Generate valuation metrics section"""
        valuation = earnings_data.get('valuation_metrics', {})
        ratios = earnings_data.get('calculated_ratios', {})
        
        return f"""<div class="section">
        <h2 class="section-title">💎 Valuation Metrics</h2>
        
        <h3 class="subsection-title">Market Valuation</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Market Capitalization</div>
                <div class="metric-value">{self._format_number(valuation.get('market_cap'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Enterprise Value</div>
                <div class="metric-value">{self._format_number(valuation.get('enterprise_value'), prefix='$')}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Price Ratios</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">P/E Ratio (Trailing)</div>
                <div class="metric-value">{self._format_number(valuation.get('trailing_pe'), decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">P/E Ratio (Forward)</div>
                <div class="metric-value">{self._format_number(valuation.get('forward_pe'), decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">PEG Ratio</div>
                <div class="metric-value">{self._format_number(valuation.get('peg_ratio'), decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Price-to-Sales</div>
                <div class="metric-value">{self._format_number(valuation.get('price_to_sales'), decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Price-to-Book</div>
                <div class="metric-value">{self._format_number(valuation.get('price_to_book'), decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">EV/Revenue</div>
                <div class="metric-value">{self._format_number(valuation.get('ev_to_revenue'), decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">EV/EBITDA</div>
                <div class="metric-value">{self._format_number(valuation.get('ev_to_ebitda'), decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Dividend Yield</div>
                <div class="metric-value">{self._format_number(valuation.get('dividend_yield'), suffix='%', decimals=2)}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Return Metrics</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Return on Equity (ROE)</div>
                <div class="metric-value">{self._format_number(ratios.get('return_on_equity'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Return on Assets (ROA)</div>
                <div class="metric-value">{self._format_number(ratios.get('return_on_assets'), suffix='%', decimals=2)}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_analyst_section(self, earnings_data: Dict[str, Any]) -> str:
        """Generate analyst estimates and sentiment section"""
        estimates = earnings_data.get('analyst_estimates', {})
        sentiment = earnings_data.get('analyst_sentiment', {})
        actual_vs_est = earnings_data.get('actual_vs_estimate', {})
        
        return f"""<div class="section">
        <h2 class="section-title">👔 Analyst Coverage & Estimates</h2>
        
        <h3 class="subsection-title">Analyst Ratings</h3>
        <div class="analyst-ratings">
            <div class="rating-item">
                <div class="rating-label">Buy Ratings</div>
                <div class="rating-count rating-buy">{estimates.get('analysts_recommending_buy', 'N/A')}</div>
            </div>
            <div class="rating-item">
                <div class="rating-label">Hold Ratings</div>
                <div class="rating-count rating-hold">{estimates.get('analysts_recommending_hold', 'N/A')}</div>
            </div>
            <div class="rating-item">
                <div class="rating-label">Sell Ratings</div>
                <div class="rating-count rating-sell">{estimates.get('analysts_recommending_sell', 'N/A')}</div>
            </div>
            <div class="rating-item">
                <div class="rating-label">Total Analysts</div>
                <div class="rating-count">{estimates.get('number_of_analysts', 'N/A')}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Price Targets</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Mean Price Target</div>
                <div class="metric-value">{self._format_number(sentiment.get('target_mean_price'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Median Price Target</div>
                <div class="metric-value">{self._format_number(sentiment.get('target_median_price'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">High Price Target</div>
                <div class="metric-value">{self._format_number(sentiment.get('target_high_price'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Low Price Target</div>
                <div class="metric-value">{self._format_number(sentiment.get('target_low_price'), prefix='$', decimals=2)}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Earnings Estimates</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Estimated EPS</div>
                <div class="metric-value">{self._format_number(estimates.get('estimated_eps'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Estimated EPS (High)</div>
                <div class="metric-value">{self._format_number(estimates.get('estimated_eps_high'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Estimated EPS (Low)</div>
                <div class="metric-value">{self._format_number(estimates.get('estimated_eps_low'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Estimated Revenue</div>
                <div class="metric-value">{self._format_number(estimates.get('estimated_revenue'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Consensus Recommendation</div>
                <div class="metric-value">{estimates.get('recommendation', 'N/A').upper() if estimates.get('recommendation') != 'N/A' else 'N/A'}</div>
            </div>
        </div>
        
        <h3 class="subsection-title">Actual vs Estimate (Latest)</h3>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Actual EPS</div>
                <div class="metric-value">{self._format_number(actual_vs_est.get('eps_actual'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">EPS Surprise</div>
                <div class="metric-value {self._get_value_class(actual_vs_est.get('eps_surprise'))}">{self._format_number(actual_vs_est.get('eps_surprise'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">EPS Surprise %</div>
                <div class="metric-value {self._get_value_class(actual_vs_est.get('eps_surprise_percent'))}">{self._format_number(actual_vs_est.get('eps_surprise_percent'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Actual Revenue</div>
                <div class="metric-value">{self._format_number(actual_vs_est.get('revenue_actual'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Revenue Surprise</div>
                <div class="metric-value {self._get_value_class(actual_vs_est.get('revenue_surprise'))}">{self._format_number(actual_vs_est.get('revenue_surprise'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Revenue Surprise %</div>
                <div class="metric-value {self._get_value_class(actual_vs_est.get('revenue_surprise_percent'))}">{self._format_number(actual_vs_est.get('revenue_surprise_percent'), suffix='%', decimals=2)}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_performance_metrics(self, earnings_data: Dict[str, Any]) -> str:
        """Generate performance metrics section"""
        performance = earnings_data.get('performance_metrics', {})
        
        return f"""<div class="section">
        <h2 class="section-title">📊 Stock Performance Metrics</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">1-Month Return</div>
                <div class="metric-value {self._get_value_class(performance.get('1_month_return'))}">{self._format_number(performance.get('1_month_return'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">3-Month Return</div>
                <div class="metric-value {self._get_value_class(performance.get('3_month_return'))}">{self._format_number(performance.get('3_month_return'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">YTD Return</div>
                <div class="metric-value {self._get_value_class(performance.get('ytd_return'))}">{self._format_number(performance.get('ytd_return'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">1-Year Return</div>
                <div class="metric-value {self._get_value_class(performance.get('1_year_return'))}">{self._format_number(performance.get('1_year_return'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Volatility (1Y)</div>
                <div class="metric-value">{self._format_number(performance.get('volatility_1y'), suffix='%', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Beta</div>
                <div class="metric-value">{self._format_number(performance.get('beta'), decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Average Volume (3M)</div>
                <div class="metric-value">{self._format_number(performance.get('avg_volume_3m'))}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Volume Trend</div>
                <div class="metric-value">{performance.get('volume_trend', 'N/A')}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_stock_price_section(self, earnings_data: Dict[str, Any]) -> str:
        """Generate stock price and market data section"""
        stock = earnings_data.get('stock_price', {})
        
        return f"""<div class="section">
        <h2 class="section-title">💹 Stock Price & Market Data</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Current Price</div>
                <div class="metric-value">{self._format_number(stock.get('current_price'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Previous Close</div>
                <div class="metric-value">{self._format_number(stock.get('previous_close'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Open Price</div>
                <div class="metric-value">{self._format_number(stock.get('open_price'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Day High</div>
                <div class="metric-value">{self._format_number(stock.get('day_high'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Day Low</div>
                <div class="metric-value">{self._format_number(stock.get('day_low'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">52-Week High</div>
                <div class="metric-value">{self._format_number(stock.get('52_week_high'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">52-Week Low</div>
                <div class="metric-value">{self._format_number(stock.get('52_week_low'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Volume</div>
                <div class="metric-value">{self._format_number(stock.get('volume'))}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Average Volume</div>
                <div class="metric-value">{self._format_number(stock.get('average_volume'))}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Price Change (1D)</div>
                <div class="metric-value {self._get_value_class(stock.get('price_change_1d'))}">{self._format_number(stock.get('price_change_1d'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Price Change % (1D)</div>
                <div class="metric-value {self._get_value_class(stock.get('price_change_percent_1d'))}">{self._format_number(stock.get('price_change_percent_1d'), suffix='%', decimals=2)}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_guidance_section(self, earnings_data: Dict[str, Any]) -> str:
        """Generate guidance and forward-looking section"""
        guidance = earnings_data.get('guidance', {})
        
        return f"""<div class="section">
        <h2 class="section-title">🔮 Forward Guidance</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">EPS Guidance (Low)</div>
                <div class="metric-value">{self._format_number(guidance.get('guidance_eps_low'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">EPS Guidance (High)</div>
                <div class="metric-value">{self._format_number(guidance.get('guidance_eps_high'), prefix='$', decimals=2)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Revenue Guidance (Low)</div>
                <div class="metric-value">{self._format_number(guidance.get('guidance_revenue_low'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Revenue Guidance (High)</div>
                <div class="metric-value">{self._format_number(guidance.get('guidance_revenue_high'), prefix='$')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Next Year Estimate</div>
                <div class="metric-value">{self._format_number(guidance.get('next_year_estimate'), prefix='$', decimals=2)}</div>
            </div>
        </div>
    </div>"""
    
    def _generate_key_focus_areas(self, earnings_data: Dict[str, Any]) -> str:
        """Generate key focus areas section"""
        focus_areas = earnings_data.get('key_focus_areas', [])
        
        if not focus_areas:
            return ""
        
        focus_html = ""
        for i, area in enumerate(focus_areas, 1):
            # Handle both string and dict formats
            if isinstance(area, dict):
                title = area.get('title', f'Focus Area {i}')
                description = area.get('description', 'No description available.')
            else:
                # If it's a string, use it as the title
                title = str(area)
                description = 'Monitor this metric closely in the earnings call and financial reports.'
            
            focus_html += f"""
            <div class="focus-area">
                <h4>🎯 {title}</h4>
                <p>{description}</p>
            </div>
            """
        
        return f"""<div class="section">
        <h2 class="section-title">🎯 Key Focus Areas</h2>
        {focus_html}
    </div>"""
    
    def _generate_risk_factors(self, earnings_data: Dict[str, Any]) -> str:
        """Generate risk factors section"""
        risk_factors = earnings_data.get('risk_factors', [])
        
        if not risk_factors:
            return ""
        
        risk_html = ""
        for i, risk in enumerate(risk_factors, 1):
            # Handle both string and dict formats
            if isinstance(risk, dict):
                title = risk.get('title', f'Risk Factor {i}')
                description = risk.get('description', 'No description available.')
            else:
                # If it's a string, use it as the title
                title = str(risk)
                description = 'This risk factor should be carefully considered when evaluating the company.'
            
            risk_html += f"""
            <div class="risk-item">
                <h4>⚠️ {title}</h4>
                <p>{description}</p>
            </div>
            """
        
        return f"""<div class="section">
        <h2 class="section-title">⚠️ Risk Factors</h2>
        {risk_html}
    </div>"""
    
    def _generate_footer(self) -> str:
        """Generate report footer"""
        return f"""<div class="footer">
        <p><strong>Tickzen Earnings Report</strong></p>
        <p>Generated on {self.report_timestamp.strftime('%B %d, %Y at %I:%M %p')}</p>
        <p>Data Source: yfinance</p>
        <p style="margin-top: 15px; font-size: 0.85em;">
            This report is for informational purposes only and should not be considered as investment advice.
            Please consult with a qualified financial advisor before making investment decisions.
        </p>
    </div>"""
    
    def _format_number(self, value: Any, prefix: str = '', suffix: str = '', decimals: int = 0) -> str:
        """Format numbers with proper prefixes and suffixes"""
        if value is None or value == 'N/A':
            return 'N/A'
        
        try:
            num = float(value)
            
            # For large numbers, use B/M/K abbreviations
            if decimals == 0 and abs(num) >= 1_000_000_000:
                formatted = f"{num / 1_000_000_000:.2f}B"
            elif decimals == 0 and abs(num) >= 1_000_000:
                formatted = f"{num / 1_000_000:.2f}M"
            elif decimals == 0 and abs(num) >= 1_000:
                formatted = f"{num / 1_000:.2f}K"
            else:
                formatted = f"{num:,.{decimals}f}"
            
            return f"{prefix}{formatted}{suffix}"
        except (ValueError, TypeError):
            return 'N/A'
    
    def _get_value_class(self, value: Any) -> str:
        """Get CSS class based on value (positive/negative/neutral)"""
        if value is None or value == 'N/A':
            return 'neutral'
        
        try:
            num = float(value)
            if num > 0:
                return 'positive'
            elif num < 0:
                return 'negative'
            else:
                return 'neutral'
        except (ValueError, TypeError):
            return 'neutral'
    
    def _has_value(self, value: Any) -> bool:
        """Check if a value is not N/A or None"""
        return value is not None and value != 'N/A' and value != 0
    
    def _render_metric_card(self, label: str, value: Any, prefix: str = '', suffix: str = '', decimals: int = 0, value_class: str = '') -> str:
        """Render a metric card only if value exists"""
        if not self._has_value(value):
            return ''
        
        formatted_value = self._format_number(value, prefix=prefix, suffix=suffix, decimals=decimals)
        class_attr = f'class="{value_class}"' if value_class else ''
        
        return f"""<div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" {class_attr}>{formatted_value}</div>
            </div>"""
    
    def save_report(self, html: str, output_path: str) -> str:
        """
        Save the generated report to a file.
        
        Args:
            html: HTML content to save
            output_path: Path to save the file
            
        Returns:
            Path to the saved file
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Report saved to {output_path}")
        return output_path
