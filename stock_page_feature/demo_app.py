"""
Standalone Demo Flask Application for Stock Page Feature
This is a minimal Flask app to test the stock page independently
"""

from flask import Flask, render_template, jsonify
import os
import json
from datetime import datetime

# Setup paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(CURRENT_DIR, 'templates')
STATIC_DIR = os.path.join(CURRENT_DIR, 'static')
DEMO_DATA_DIR = os.path.join(CURRENT_DIR, 'demo_data')

# Create Flask app
app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)

app.config['SECRET_KEY'] = 'demo-secret-key-change-in-production'


def load_demo_data(ticker='AAPL'):
    """Load demo data for a specific ticker"""
    demo_file = os.path.join(DEMO_DATA_DIR, f'{ticker}_demo.json')
    
    if os.path.exists(demo_file):
        with open(demo_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Return fallback demo data if file doesn't exist
    return get_fallback_demo_data(ticker)


def get_fallback_demo_data(ticker='AAPL'):
    """Generate fallback demo data"""
    return {
        'ticker': ticker,
        'company_name': 'Apple Inc.' if ticker == 'AAPL' else f'{ticker} Company',
        'current_price': '175.50',
        'price_change': 2.5,
        'price_change_percent': 1.45,
        'market_cap': '$2.75T',
        'volume': '52.3M',
        'pe_ratio': '28.5',
        'dividend_yield': '0.52%',
        'generated_at': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
        'last_updated': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
        
        # Overview section
        'overview_introduction': '''
            <p>Apple Inc. (AAPL) is a global technology leader, known for innovative consumer electronics, 
            software, and services. The company's diverse product portfolio includes the iPhone, iPad, Mac, 
            Apple Watch, and AirPods, complemented by services like Apple Music, iCloud, and the App Store.</p>
            <p>As of the latest analysis, AAPL demonstrates strong financial health with consistent revenue 
            growth and robust profit margins. The stock has shown resilience in various market conditions, 
            making it a popular choice among investors.</p>
        ''',
        'overview_quick_stats': '''
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
                <div style="padding: 1rem; background: #f8fafc; border-radius: 8px;">
                    <strong>52 Week High:</strong> $199.62
                </div>
                <div style="padding: 1rem; background: #f8fafc; border-radius: 8px;">
                    <strong>52 Week Low:</strong> $164.08
                </div>
                <div style="padding: 1rem; background: #f8fafc; border-radius: 8px;">
                    <strong>Beta:</strong> 1.29
                </div>
                <div style="padding: 1rem; background: #f8fafc; border-radius: 8px;">
                    <strong>EPS (TTM):</strong> $6.16
                </div>
            </div>
        ''',
        
        # Forecast section
        'forecast_summary': '''
            <p>Based on advanced AI models and technical analysis, AAPL shows a <strong>bullish trend</strong> 
            for the next 30-90 days. Key factors supporting this outlook include:</p>
            <ul>
                <li>Strong product launch cycle with new iPhone models</li>
                <li>Expanding services revenue contributing to margin improvement</li>
                <li>Positive analyst sentiment with price targets ranging from $180-$220</li>
                <li>Technical indicators showing upward momentum</li>
            </ul>
            <p class="text-success"><strong>Predicted Price Range (30 days):</strong> $178 - $192</p>
        ''',
        'forecast_table': '''
            <table style="width: 100%; border-collapse: collapse; margin-top: 1rem;">
                <thead>
                    <tr style="background: #16a34a; color: white;">
                        <th style="padding: 0.75rem; text-align: left;">Time Period</th>
                        <th style="padding: 0.75rem; text-align: right;">Low</th>
                        <th style="padding: 0.75rem; text-align: right;">Predicted</th>
                        <th style="padding: 0.75rem; text-align: right;">High</th>
                        <th style="padding: 0.75rem; text-align: right;">Change</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background: #f8fafc;">
                        <td style="padding: 0.75rem;">7 Days</td>
                        <td style="padding: 0.75rem; text-align: right;">$174.20</td>
                        <td style="padding: 0.75rem; text-align: right; font-weight: bold;">$178.50</td>
                        <td style="padding: 0.75rem; text-align: right;">$182.80</td>
                        <td style="padding: 0.75rem; text-align: right; color: #16a34a;">+1.7%</td>
                    </tr>
                    <tr>
                        <td style="padding: 0.75rem;">30 Days</td>
                        <td style="padding: 0.75rem; text-align: right;">$178.00</td>
                        <td style="padding: 0.75rem; text-align: right; font-weight: bold;">$185.00</td>
                        <td style="padding: 0.75rem; text-align: right;">$192.00</td>
                        <td style="padding: 0.75rem; text-align: right; color: #16a34a;">+5.4%</td>
                    </tr>
                    <tr style="background: #f8fafc;">
                        <td style="padding: 0.75rem;">90 Days</td>
                        <td style="padding: 0.75rem; text-align: right;">$182.00</td>
                        <td style="padding: 0.75rem; text-align: right; font-weight: bold;">$195.00</td>
                        <td style="padding: 0.75rem; text-align: right;">$208.00</td>
                        <td style="padding: 0.75rem; text-align: right; color: #16a34a;">+11.1%</td>
                    </tr>
                </tbody>
            </table>
        ''',
        'forecast_chart': '<div style="padding: 2rem; text-align: center; background: #f1f5f9; border-radius: 8px;"><i class="fas fa-chart-line" style="font-size: 3rem; color: #64748b;"></i><p style="margin-top: 1rem; color: #64748b;">Interactive chart would be displayed here</p></div>',
        
        # Technical section
        'technical_summary': '''
            <p>Technical analysis indicates <strong>strong buy signals</strong> across multiple timeframes:</p>
            <ul>
                <li><strong>RSI (14):</strong> 58.3 - Neutral zone with bullish momentum</li>
                <li><strong>MACD:</strong> Bullish crossover detected</li>
                <li><strong>Moving Averages:</strong> Price above 50-day and 200-day MA</li>
                <li><strong>Bollinger Bands:</strong> Price in upper band, indicating strength</li>
            </ul>
        ''',
        'technical_indicators': '''
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                <div style="padding: 1rem; background: #dcfce7; border-left: 4px solid #16a34a; border-radius: 4px;">
                    <strong>Trend:</strong> Bullish ↗
                </div>
                <div style="padding: 1rem; background: #dbeafe; border-left: 4px solid #2563eb; border-radius: 4px;">
                    <strong>Momentum:</strong> Strong
                </div>
                <div style="padding: 1rem; background: #dcfce7; border-left: 4px solid #16a34a; border-radius: 4px;">
                    <strong>Volume:</strong> Above Average
                </div>
                <div style="padding: 1rem; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
                    <strong>Volatility:</strong> Moderate
                </div>
            </div>
        ''',
        'technical_charts': '<div style="padding: 2rem; text-align: center; background: #f1f5f9; border-radius: 8px;"><i class="fas fa-chart-area" style="font-size: 3rem; color: #64748b;"></i><p style="margin-top: 1rem; color: #64748b;">Technical charts would be displayed here</p></div>',
        
        # Fundamentals section
        'fundamentals_valuation': '''
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #f8fafc;">
                    <td style="padding: 0.75rem; font-weight: 600;">Market Cap</td>
                    <td style="padding: 0.75rem; text-align: right;">$2.75 Trillion</td>
                </tr>
                <tr>
                    <td style="padding: 0.75rem; font-weight: 600;">Enterprise Value</td>
                    <td style="padding: 0.75rem; text-align: right;">$2.82 Trillion</td>
                </tr>
                <tr style="background: #f8fafc;">
                    <td style="padding: 0.75rem; font-weight: 600;">P/E Ratio (TTM)</td>
                    <td style="padding: 0.75rem; text-align: right;">28.5x</td>
                </tr>
                <tr>
                    <td style="padding: 0.75rem; font-weight: 600;">PEG Ratio</td>
                    <td style="padding: 0.75rem; text-align: right;">2.1</td>
                </tr>
                <tr style="background: #f8fafc;">
                    <td style="padding: 0.75rem; font-weight: 600;">Price/Book</td>
                    <td style="padding: 0.75rem; text-align: right;">45.2</td>
                </tr>
            </table>
        ''',
        'fundamentals_health': '''
            <p><strong>Financial Strength: Excellent</strong></p>
            <ul>
                <li>Debt-to-Equity Ratio: 1.73 (Manageable)</li>
                <li>Current Ratio: 0.93</li>
                <li>Cash & Equivalents: $61.5B</li>
                <li>Free Cash Flow: $99.8B (TTM)</li>
            </ul>
        ''',
        'fundamentals_growth': '''
            <p><strong>Revenue Growth:</strong> 2.1% YoY</p>
            <p><strong>Earnings Growth:</strong> 10.8% YoY</p>
            <p><strong>Profit Margins:</strong></p>
            <ul>
                <li>Gross Margin: 44.1%</li>
                <li>Operating Margin: 29.8%</li>
                <li>Net Margin: 25.3%</li>
            </ul>
        ''',
        'fundamentals_analyst': '''
            <p><strong>Analyst Consensus: Buy</strong></p>
            <ul>
                <li>Strong Buy: 18 analysts</li>
                <li>Buy: 12 analysts</li>
                <li>Hold: 8 analysts</li>
                <li>Sell: 1 analyst</li>
            </ul>
            <p><strong>Average Price Target:</strong> $198.50 (+13% upside)</p>
        ''',
        
        # Company section
        'company_profile': '''
            <p><strong>Founded:</strong> 1976 | <strong>Headquarters:</strong> Cupertino, California</p>
            <p><strong>CEO:</strong> Tim Cook | <strong>Employees:</strong> ~164,000</p>
            <p><strong>Industry:</strong> Consumer Electronics | <strong>Sector:</strong> Technology</p>
        ''',
        'company_business': '''
            <p>Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, 
            and accessories worldwide. The company also sells various related services including AppleCare, 
            cloud services, digital content, and payment services.</p>
            <p><strong>Key Products:</strong></p>
            <ul>
                <li>iPhone (52% of revenue)</li>
                <li>Services (20% of revenue)</li>
                <li>Mac (10% of revenue)</li>
                <li>iPad (8% of revenue)</li>
                <li>Wearables, Home & Accessories (10% of revenue)</li>
            </ul>
        ''',
        'company_industry': '''
            <p><strong>Sector:</strong> Technology</p>
            <p><strong>Industry:</strong> Consumer Electronics</p>
            <p><strong>Competitors:</strong> Samsung, Microsoft, Google, Amazon</p>
            <p><strong>Market Position:</strong> Market leader in premium smartphones and tablets</p>
        ''',
        
        # Trading section
        'trading_strategies': '''
            <h4>Recommended Strategy: Accumulate on Dips</h4>
            <p>Given the strong fundamentals and positive technical indicators, we recommend:</p>
            <ol>
                <li><strong>Long-term investors:</strong> Consider building positions on any pullbacks to $170-$172 support level</li>
                <li><strong>Swing traders:</strong> Look for entries near $175 with targets at $185-$190</li>
                <li><strong>Options traders:</strong> Consider bull call spreads with 30-60 day expiration</li>
            </ol>
        ''',
        'trading_points': '''
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div style="padding: 1rem; background: #dcfce7; border-radius: 8px;">
                    <h4 style="color: #16a34a; margin-bottom: 0.5rem;">Entry Points</h4>
                    <p><strong>Aggressive:</strong> $174-$176</p>
                    <p><strong>Conservative:</strong> $170-$172</p>
                </div>
                <div style="padding: 1rem; background: #fee2e2; border-radius: 8px;">
                    <h4 style="color: #dc2626; margin-bottom: 0.5rem;">Exit/Stop Loss</h4>
                    <p><strong>Target 1:</strong> $185</p>
                    <p><strong>Target 2:</strong> $195</p>
                    <p><strong>Stop Loss:</strong> $168</p>
                </div>
            </div>
        ''',
        'trading_risk': '''
            <p><strong>Risk Level: Moderate</strong></p>
            <ul>
                <li>Position Size: 3-5% of portfolio for new positions</li>
                <li>Risk/Reward Ratio: 1:2.5</li>
                <li>Recommended Stop Loss: 4% below entry</li>
            </ul>
        ''',
        
        # Conclusion section
        'conclusion_outlook': '''
            <p>Apple Inc. presents a <strong>compelling investment opportunity</strong> with strong fundamentals, 
            consistent innovation, and expanding service revenues. The technical setup suggests continued upside 
            potential in the near to medium term.</p>
            <p><strong class="text-success">Overall Rating: BUY</strong></p>
            <p><strong>Investment Horizon:</strong> 6-12 months</p>
        ''',
        'conclusion_risks': '''
            <ul>
                <li>Regulatory challenges in key markets (China, EU)</li>
                <li>Intensifying competition in smartphones and services</li>
                <li>Supply chain disruptions</li>
                <li>Macroeconomic headwinds affecting consumer spending</li>
                <li>Currency fluctuations impacting international sales</li>
            </ul>
        ''',
        'conclusion_recommendation': '''
            <div style="padding: 1.5rem; background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%); border-radius: 12px; border: 2px solid #16a34a;">
                <h3 style="color: #15803d; margin-bottom: 1rem;">Final Recommendation: STRONG BUY</h3>
                <p><strong>Target Price (12 months):</strong> $210</p>
                <p><strong>Expected Return:</strong> +19.7%</p>
                <p><strong>Risk Rating:</strong> Moderate</p>
                <p style="margin-top: 1rem; font-size: 0.875rem; color: #64748b;">
                    This recommendation is based on current market conditions and company fundamentals. 
                    Always conduct your own research and consider your risk tolerance.
                </p>
            </div>
        ''',
        'conclusion_faq': '''
            <div style="margin-top: 1rem;">
                <div style="margin-bottom: 1rem; padding: 1rem; background: #f8fafc; border-radius: 8px;">
                    <h4 style="color: #16a34a;">Is AAPL a good long-term investment?</h4>
                    <p>Yes, Apple's strong brand, loyal customer base, and expanding services ecosystem make it an attractive long-term hold.</p>
                </div>
                <div style="margin-bottom: 1rem; padding: 1rem; background: #f8fafc; border-radius: 8px;">
                    <h4 style="color: #16a34a;">What is the dividend yield?</h4>
                    <p>Apple currently offers a dividend yield of approximately 0.52%, with a history of consistent dividend growth.</p>
                </div>
                <div style="margin-bottom: 1rem; padding: 1rem; background: #f8fafc; border-radius: 8px;">
                    <h4 style="color: #16a34a;">What are the main growth drivers?</h4>
                    <p>Services revenue, wearables, and new product categories like AR/VR headsets are key growth drivers.</p>
                </div>
            </div>
        '''
    }


@app.route('/')
def index():
    """Homepage with list of available demos"""
    available_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    return render_template('index.html', tickers=available_tickers)


@app.route('/stock/<ticker>')
def stock_page(ticker):
    """Main stock page route"""
    ticker = ticker.upper()
    data = load_demo_data(ticker)
    return render_template('stock_page.html', **data)


@app.route('/api/stock/<ticker>')
def api_stock_data(ticker):
    """API endpoint to get stock data as JSON"""
    ticker = ticker.upper()
    data = load_demo_data(ticker)
    return jsonify(data)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  STOCK PAGE FEATURE - STANDALONE DEMO")
    print("="*60)
    print("\n  Starting Flask development server...")
    print(f"  Template folder: {TEMPLATE_DIR}")
    print(f"  Static folder: {STATIC_DIR}")
    print("\n  Open your browser and navigate to:")
    print("  http://127.0.0.1:5000/stock/AAPL")
    print("\n  Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, host='127.0.0.1')
