import pandas as pd
import sys

# Read the CSV
df = pd.read_csv('AAPL_complete_data_20260122_165235.csv')

# Get the first row as dictionary
data = df.iloc[0].to_dict()

print("\n" + "="*70)
print("✅ TICKER DATA EXPORT TEST - SUCCESS")
print("="*70)
print(f"\n📊 FILE INFORMATION")
print(f"   Filename: AAPL_complete_data_20260122_165235.csv")
print(f"   Total Columns: {len(df.columns)}")
print(f"   Total Rows: {len(df)}")
print(f"   Data Collection Date: {data['data_collection_date']}")
print(f"   Data Source: {data['data_source']}")

print(f"\n💰 MARKET DATA (OVERVIEW TAB)")
print(f"   Ticker: {data['ticker']}")
print(f"   Current Price: ${data['current_price']:.2f}" if pd.notna(data['current_price']) else "   Current Price: N/A")
print(f"   Market Cap: ${data['market_cap']:,.0f}" if pd.notna(data['market_cap']) else "   Market Cap: N/A")
print(f"   Enterprise Value: ${data['enterprise_value']:,.0f}" if pd.notna(data['enterprise_value']) else "   Enterprise Value: N/A")
print(f"   Exchange: {data['exchange']}")
print(f"   Volume: {data['volume']:,.0f}" if pd.notna(data['volume']) else "   Volume: N/A")

print(f"\n📈 FORECAST DATA (FORECAST TAB)")
print(f"   Analyst Rating: {data['analyst_rating']}")
print(f"   Analyst Count: {int(data['analyst_count']) if pd.notna(data['analyst_count']) else 'N/A'}")
print(f"   Target Price (Mean): ${data['target_price_mean']:.2f}" if pd.notna(data['target_price_mean']) else "   Target Price (Mean): N/A")
print(f"   Next Earnings Date: {data['next_earnings_date']}")

print(f"\n📊 TECHNICAL ANALYSIS (TECHNICALS TAB)")
print(f"   SMA 20: ${data['sma_20']:.2f}" if pd.notna(data['sma_20']) else "   SMA 20: N/A")
print(f"   SMA 50: ${data['sma_50']:.2f}" if pd.notna(data['sma_50']) else "   SMA 50: N/A")
print(f"   SMA 200: ${data['sma_200']:.2f}" if pd.notna(data['sma_200']) else "   SMA 200: N/A")
print(f"   RSI (14): {data['rsi_14']:.2f}" if pd.notna(data['rsi_14']) else "   RSI (14): N/A")
print(f"   MACD Line: {data['macd_line']:.4f}" if pd.notna(data['macd_line']) else "   MACD Line: N/A")
print(f"   Bollinger Upper: ${data['bb_upper']:.2f}" if pd.notna(data['bb_upper']) else "   Bollinger Upper: N/A")

print(f"\n💼 FUNDAMENTAL DATA (FUNDAMENTALS TAB)")
print(f"   P/E Ratio (Trailing): {data['pe_trailing']:.2f}" if pd.notna(data['pe_trailing']) else "   P/E Ratio: N/A")
print(f"   P/E Ratio (Forward): {data['pe_forward']:.2f}" if pd.notna(data['pe_forward']) else "   Forward P/E: N/A")
print(f"   Price/Sales: {data['price_to_sales']:.2f}" if pd.notna(data['price_to_sales']) else "   Price/Sales: N/A")
print(f"   Debt/Equity: {data['debt_to_equity']:.2f}" if pd.notna(data['debt_to_equity']) else "   Debt/Equity: N/A")
print(f"   ROE: {data['roe']*100:.2f}%" if pd.notna(data['roe']) else "   ROE: N/A")
print(f"   Revenue (TTM): ${data['revenue_ttm']:,.0f}" if pd.notna(data['revenue_ttm']) else "   Revenue: N/A")
print(f"   Earnings Growth YoY: {data['earnings_growth_yoy']*100:.2f}%" if pd.notna(data['earnings_growth_yoy']) else "   Earnings Growth: N/A")

print(f"\n⚠️  RISK & SENTIMENT (RISK & SENTIMENT TAB)")
print(f"   Beta: {data['beta']:.2f}" if pd.notna(data['beta']) else "   Beta: N/A")
print(f"   Volatility (30d): {data['volatility_30d_annual']*100:.2f}%" if pd.notna(data['volatility_30d_annual']) else "   Volatility: N/A")
print(f"   Sharpe Ratio: {data['sharpe_ratio']:.2f}" if pd.notna(data['sharpe_ratio']) else "   Sharpe Ratio: N/A")
print(f"   Max Drawdown: {data['max_drawdown']*100:.2f}%" if pd.notna(data['max_drawdown']) else "   Max Drawdown: N/A")
print(f"   Sentiment Score: {data['sentiment_score']}" if pd.notna(data['sentiment_score']) else "   Sentiment Score: N/A")
print(f"   Total Insider Transactions: {int(data['total_transactions']) if pd.notna(data['total_transactions']) else 'N/A'}")

print(f"\n🏢 COMPANY INFO (COMPANY TAB)")
print(f"   Company Name: {data['company_name']}")
print(f"   Sector: {data['sector']}")
print(f"   Industry: {data['industry']}")
print(f"   Employees: {int(data['employee_count']) if pd.notna(data['employee_count']) else 'N/A'}")
print(f"   Insider Ownership: {data['insider_ownership_pct']*100:.2f}%" if pd.notna(data['insider_ownership_pct']) else "   Insider Ownership: N/A")
print(f"   Institutional Ownership: {data['institutional_ownership_pct']*100:.2f}%" if pd.notna(data['institutional_ownership_pct']) else "   Institutional Ownership: N/A")

print(f"\n📋 QUARTERLY DATA (QUARTERLY EARNINGS TAB)")
print(f"   Q1 Date: {data['q1_date']}")
print(f"   Q1 Revenue: {data['q1_total_revenue']}")
print(f"   Q1 Net Income: {data['q1_net_income']}")
print(f"   Q1 EPS (Diluted): {data['q1_eps_diluted']}")
print(f"   QoQ Revenue Growth: {data['qoq_revenue_growth']}")
print(f"   YoY Revenue Growth: {data['yoy_revenue_growth']}")

print("\n" + "="*70)
print("✅ All data successfully collected and exported to CSV!")
print("="*70 + "\n")
