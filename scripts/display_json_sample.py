import json

# Read the JSON file
with open('AAPL_complete_data_20260122_170046.json') as f:
    data = json.load(f)

print("\n" + "="*70)
print("✅ JSON FILE STRUCTURE")
print("="*70)

# Display metadata
print("\n📋 METADATA:")
for key, value in data['metadata'].items():
    if isinstance(value, list):
        print(f"  {key}: {', '.join(map(str, value))}")
    else:
        print(f"  {key}: {value}")

# Display sample data
print(f"\n📊 SAMPLE DATA (First Ticker):")
if data['data']:
    ticker_data = data['data'][0]
    print(f"  Ticker: {ticker_data['ticker']}")
    print(f"  Current Price: ${ticker_data['current_price']}")
    print(f"  Market Cap: ${ticker_data['market_cap']:,.0f}")
    print(f"  P/E Ratio (Trailing): {ticker_data['pe_trailing']}")
    print(f"  RSI (14): {ticker_data['rsi_14']}")
    print(f"  MACD Line: {ticker_data['macd_line']}")
    print(f"  Beta: {ticker_data['beta']}")
    print(f"  Sharpe Ratio: {ticker_data['sharpe_ratio']}")
    print(f"  Total Variables in Record: {len(ticker_data)}")

print("\n" + "="*70)
print("File Details:")
print("="*70)
print(f"  Total Tickers: {data['metadata']['total_tickers']}")
print(f"  Total Variables per Ticker: {data['metadata']['total_variables']}")
print(f"  JSON File Location: AAPL_complete_data_20260122_170046.json")
print(f"  CSV File Location: AAPL_complete_data_20260122_170046.csv")
print("="*70 + "\n")
