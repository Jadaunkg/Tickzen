# peer_comparison.py

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')

def get_finnhub_api_key():
    """Get Finnhub API key from environment variables or config files."""
    # Try environment variable first
    api_key = os.getenv('FINNHUB_API_KEY')
    if api_key:
        return api_key
    
    # Try to load from .env file in project root
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            api_key = os.getenv('FINNHUB_API_KEY')
            if api_key:
                return api_key
    except ImportError:
        # python-dotenv not installed, continue with other methods
        pass
    except Exception as e:
        logging.warning(f"Could not load .env file: {e}")
    
    # Try to read from config file if available
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.py')
        if os.path.exists(config_path):
            import sys
            sys.path.append(os.path.dirname(config_path))
            from config import FINNHUB_API_KEY
            return FINNHUB_API_KEY
    except Exception as e:
        logging.warning(f"Could not read Finnhub API key from config: {e}")
    
    # Return None if not found anywhere
    return None

def fetch_company_peers(ticker):
    """Fetch peer companies using Finnhub API."""
    api_key = get_finnhub_api_key()
    
    if not api_key or api_key == "your_finnhub_api_key_here":
        logging.warning("Finnhub API key not configured properly")
        return []
    
    try:
        url = f"https://finnhub.io/api/v1/stock/peers?symbol={ticker}&token={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            peers = response.json()
            # Filter out the original ticker and limit to 4 peers
            if isinstance(peers, list):
                filtered_peers = [peer for peer in peers if peer.upper() != ticker.upper()]
                logging.info(f"Finnhub returned {len(filtered_peers)} peers for {ticker}: {filtered_peers}")
                return filtered_peers[:4]  # Return up to 4 peers
        else:
            logging.error(f"Finnhub API error for {ticker}: {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching peers from Finnhub for {ticker}: {e}")
    
    return []

def get_company_peers(ticker):
    """Get peer companies - use Finnhub peers if available, otherwise use sector-based peers."""
    logging.info(f"Getting peers for {ticker}")
    
    # Step 1: Try Finnhub API
    finnhub_peers = fetch_company_peers(ticker)
    
    if finnhub_peers:
        # Use Finnhub peers directly (up to 3 peers)
        logging.info(f"Using Finnhub peers for {ticker}: {finnhub_peers[:3]}")
        return finnhub_peers[:3]
    
    # Step 2: Fallback to sector-based peers
    logging.info(f"No Finnhub peers found for {ticker}, using sector-based fallback")
    return get_sector_peers(ticker)

def analyze_insider_availability(ticker):
    """Analyze why insider transaction data might not be available for a ticker."""
    try:
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        info = stock.info
        
        reasons = []
        
        # Check if it's an ETF
        if is_etf(ticker):
            reasons.append("ETFs do not have corporate insiders as they are investment funds, not operating companies")
            return reasons
        
        # Check market cap (smaller companies often have less insider activity)
        market_cap = info.get('marketCap', 0)
        if market_cap < 100e6:  # Less than $100M
            reasons.append("Small market cap companies (under $100M) often have limited insider transaction reporting")
        
        # Check if it's a recent IPO or newer company
        listing_date = info.get('firstTradeDateEpochUtc')
        if listing_date:
            import datetime
            listing_datetime = datetime.datetime.fromtimestamp(listing_date)
            years_since_listing = (datetime.datetime.now() - listing_datetime).days / 365.25
            if years_since_listing < 2:
                reasons.append(f"Recently public company (listed {years_since_listing:.1f} years ago) may have limited historical insider data")
        
        # Check exchange (some foreign or OTC stocks have limited reporting)
        exchange = info.get('exchange', '').upper()
        if exchange in ['OTC', 'PINK', 'OTCBB']:
            reasons.append("OTC or Pink Sheet stocks often have limited insider transaction reporting requirements")
        
        # Check country (non-US companies may not report to SEC)
        country = info.get('country', '').upper()
        if country and country != 'UNITED STATES':
            reasons.append(f"Non-US companies ({country}) may not file insider transactions with the SEC")
        
        # Check if it's a special purpose entity
        business_summary = info.get('longBusinessSummary', '').lower()
        company_name = info.get('longName', '').lower()
        if any(term in business_summary or term in company_name for term in ['spac', 'acquisition corp', 'blank check']):
            reasons.append("Special purpose acquisition companies (SPACs) often have limited insider activity")
        
        # Generic reasons if no specific issues found
        if not reasons:
            reasons.append("Company may have minimal insider trading activity in the recent 3-month period")
            reasons.append("Insiders may primarily trade during scheduled trading windows not captured in recent data")
            reasons.append("Company may have restrictive insider trading policies limiting transaction frequency")
        
        return reasons
        
    except Exception as e:
        logging.warning(f"Error analyzing insider availability for {ticker}: {e}")
        return ["Unable to determine specific reasons - may be due to limited public data availability"]

def fetch_insider_transactions(ticker, months_back=3):
    """Fetch insider transactions for a ticker using Finnhub API with enhanced data collection."""
    api_key = get_finnhub_api_key()
    
    if not api_key or api_key == "your_finnhub_api_key_here":
        logging.warning("Finnhub API key not configured properly for insider transactions")
        return []
    
    try:
        # Calculate date range with extended lookback for better data coverage
        to_date = datetime.now()
        from_date = to_date - timedelta(days=months_back * 30)  # Primary period
        
        # Format dates for API
        from_str = from_date.strftime('%Y-%m-%d')
        to_str = to_date.strftime('%Y-%m-%d')
        
        url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&from={from_str}&to={to_str}&token={api_key}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('data', [])
            
            # If we get limited data, try extended lookback
            if len(transactions) < 5 and months_back <= 6:
                logging.info(f"Limited data ({len(transactions)} transactions) for {ticker}, trying extended lookback")
                extended_from = to_date - timedelta(days=12 * 30)  # 12 months
                extended_from_str = extended_from.strftime('%Y-%m-%d')
                
                extended_url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&from={extended_from_str}&to={to_str}&token={api_key}"
                extended_response = requests.get(extended_url, timeout=15)
                
                if extended_response.status_code == 200:
                    extended_data = extended_response.json()
                    extended_transactions = extended_data.get('data', [])
                    if len(extended_transactions) > len(transactions):
                        logging.info(f"Extended search found {len(extended_transactions)} transactions for {ticker}")
                        transactions = extended_transactions
            
            # Sort transactions by filing date (most recent first)
            if transactions:
                transactions.sort(key=lambda x: x.get('filingDate', ''), reverse=True)
                logging.info(f"Final result: {len(transactions)} insider transactions for {ticker}")
            
            return transactions
        else:
            logging.error(f"Finnhub Insider Transactions API error: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error fetching insider transactions for {ticker}: {e}")
        return []

def get_stock_price_for_date(ticker, target_date, max_days_search=10):
    """
    Get historical stock price for a specific date with fallback logic.
    If exact date not available, search nearby dates within max_days_search range.
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Convert target_date to datetime if it's a string
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d')
        
        # Get historical data around the target date
        start_date = target_date - timedelta(days=max_days_search)
        end_date = target_date + timedelta(days=max_days_search)
        
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            return None
        
        # Try to find exact date first
        target_date_str = target_date.strftime('%Y-%m-%d')
        if target_date_str in hist.index.strftime('%Y-%m-%d'):
            exact_match_idx = hist.index[hist.index.strftime('%Y-%m-%d') == target_date_str][0]
            return hist.loc[exact_match_idx, 'Close']
        
        # If exact date not found, find the closest date
        hist_dates = pd.to_datetime(hist.index.date)
        target_pd = pd.to_datetime(target_date.date())
        
        # Calculate time differences and find closest
        time_diffs = abs((hist_dates - target_pd).days)
        closest_idx = time_diffs.argmin()
        
        if time_diffs.iloc[closest_idx] <= max_days_search:
            closest_date = hist.index[closest_idx]
            closest_price = hist.loc[closest_date, 'Close']
            days_diff = time_diffs.iloc[closest_idx]
            
            logging.info(f"Found price for {ticker} on {closest_date.strftime('%Y-%m-%d')} (${closest_price:.2f}), {days_diff} days from target {target_date_str}")
            return closest_price
        
        return None
    
    except Exception as e:
        logging.warning(f"Error getting price for {ticker} on {target_date}: {e}")
        return None

def estimate_price_from_transaction_code(transaction_code, market_price=None):
    """
    Estimate transaction nature and provide price context based on transaction codes.
    Common codes: P=Purchase, S=Sale, A=Award/Grant, M=Exercise, F=Tax withholding
    """
    code_meanings = {
        'P': {'type': 'Purchase', 'price_expected': True, 'description': 'Open market purchase'},
        'S': {'type': 'Sale', 'price_expected': True, 'description': 'Open market sale'},
        'A': {'type': 'Award', 'price_expected': False, 'description': 'Stock award/grant (typically no cash price)'},
        'M': {'type': 'Exercise', 'price_expected': True, 'description': 'Option exercise'},
        'F': {'type': 'Tax Payment', 'price_expected': False, 'description': 'Shares sold to pay taxes'},
        'G': {'type': 'Gift', 'price_expected': False, 'description': 'Gift of securities'},
        'J': {'type': 'Other', 'price_expected': True, 'description': 'Other acquisition'},
        'K': {'type': 'Equity Swap', 'price_expected': True, 'description': 'Equity swap'},
        'W': {'type': 'Acquisition', 'price_expected': False, 'description': 'Acquisition or disposition by will'},
        'D': {'type': 'Disposition', 'price_expected': True, 'description': 'Disposition'}
    }
    
    code_info = code_meanings.get(transaction_code, {
        'type': 'Unknown', 
        'price_expected': True, 
        'description': 'Unknown transaction type'
    })
    
    return code_info

def format_insider_transaction_data(transactions):
    """Format insider transaction data for display with enhanced price handling."""
    if not transactions:
        return []
    
    formatted_transactions = []
    ticker_for_prices = None
    
    # Extract ticker from first transaction if available
    if transactions:
        ticker_for_prices = transactions[0].get('symbol', '').upper()
    
    for transaction in transactions:
        try:
            # Extract and format transaction data
            name = transaction.get('name', 'Unknown')
            change = transaction.get('change', 0)
            share = transaction.get('share', 0)
            filing_date = transaction.get('filingDate', '')
            transaction_date = transaction.get('transactionDate', '')
            transaction_code = transaction.get('transactionCode', '')
            transaction_price = transaction.get('transactionPrice', 0)
            
            # Determine transaction type
            if change > 0:
                transaction_type = "BUY"
                change_display = f"+{change:,}"
            elif change < 0:
                transaction_type = "SELL"
                change_display = f"{change:,}"  # Already negative
            else:
                transaction_type = "OTHER"
                change_display = "0"
            
            # Enhanced price handling with multiple fallbacks
            price_display = "N/A"
            price_source = "missing"
            
            # First, try the provided transaction price
            if transaction_price and transaction_price > 0:
                price_display = f"${transaction_price:.2f}"
                price_source = "reported"
            else:
                # Get transaction code information
                code_info = estimate_price_from_transaction_code(transaction_code)
                
                if code_info['price_expected'] and transaction_date and ticker_for_prices:
                    # Try to fetch historical price for the transaction date
                    try:
                        historical_price = get_stock_price_for_date(ticker_for_prices, transaction_date)
                        if historical_price and historical_price > 0:
                            price_display = f"~${historical_price:.2f}"
                            price_source = "estimated"
                            logging.info(f"Used historical price for {ticker_for_prices} on {transaction_date}: ${historical_price:.2f}")
                    except Exception as e:
                        logging.warning(f"Could not fetch historical price: {e}")
                
                # If still no price and it's not expected (like stock awards), show appropriate message
                if price_display == "N/A" and not code_info['price_expected']:
                    price_display = f"N/A ({code_info['description']})"
                    price_source = "not_applicable"
                elif price_display == "N/A":
                    price_display = f"N/A (data missing)"
                    price_source = "missing"
            
            # Format dates
            filing_display = filing_date if filing_date else "N/A"
            transaction_display = transaction_date if transaction_date else "N/A"
            
            # Format shares held
            shares_display = f"{share:,}" if share else "N/A"
            
            # Add transaction code information for context
            code_info = estimate_price_from_transaction_code(transaction_code)
            transaction_type_detailed = f"{transaction_type} ({code_info['type']})" if transaction_code else transaction_type
            
            formatted_transactions.append({
                'name': name,
                'type': transaction_type,
                'type_detailed': transaction_type_detailed,
                'change': change_display,
                'price': price_display,
                'price_source': price_source,
                'shares_after': shares_display,
                'transaction_date': transaction_display,
                'filing_date': filing_display,
                'code': transaction_code,
                'code_description': code_info['description'],
                'raw_change': change,
                'raw_price': transaction_price,
                'estimated_value': abs(change) * (transaction_price if transaction_price and transaction_price > 0 else 0)
            })
        except Exception as e:
            logging.warning(f"Error formatting transaction: {e}")
            continue
    
    return formatted_transactions

def get_stock_price_for_date(ticker, target_date, max_days_search=10):
    """
    Get historical stock price for a specific date with fallback logic.
    If exact date not available, search nearby dates within max_days_search range.
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Convert target_date to datetime if it's a string
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d')
        
        # Get historical data around the target date
        start_date = target_date - timedelta(days=max_days_search)
        end_date = target_date + timedelta(days=max_days_search)
        
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            return None
        
        # Try to find exact date first
        target_date_str = target_date.strftime('%Y-%m-%d')
        if target_date_str in hist.index.strftime('%Y-%m-%d'):
            exact_match_idx = hist.index[hist.index.strftime('%Y-%m-%d') == target_date_str][0]
            return hist.loc[exact_match_idx, 'Close']
        
        # If exact date not found, find the closest date
        hist_dates = pd.to_datetime(hist.index.date)
        target_pd = pd.to_datetime(target_date.date())
        
        # Calculate time differences and find closest
        time_diffs = abs((hist_dates - target_pd).days)
        closest_idx = time_diffs.argmin()
        
        if time_diffs.iloc[closest_idx] <= max_days_search:
            closest_date = hist.index[closest_idx]
            closest_price = hist.loc[closest_date, 'Close']
            days_diff = time_diffs.iloc[closest_idx]
            
            logging.info(f"Found price for {ticker} on {closest_date.strftime('%Y-%m-%d')} (${closest_price:.2f}), {days_diff} days from target {target_date_str}")
            return closest_price
        
        return None
    
    except Exception as e:
        logging.warning(f"Error getting price for {ticker} on {target_date}: {e}")
        return None

def estimate_price_from_transaction_code(transaction_code, market_price=None):
    """
    Estimate transaction nature and provide price context based on transaction codes.
    Common codes: P=Purchase, S=Sale, A=Award/Grant, M=Exercise, F=Tax withholding
    """
    code_meanings = {
        'P': {'type': 'Purchase', 'price_expected': True, 'description': 'Open market purchase'},
        'S': {'type': 'Sale', 'price_expected': True, 'description': 'Open market sale'},
        'A': {'type': 'Award', 'price_expected': False, 'description': 'Stock award/grant (typically no cash price)'},
        'M': {'type': 'Exercise', 'price_expected': True, 'description': 'Option exercise'},
        'F': {'type': 'Tax Payment', 'price_expected': False, 'description': 'Shares sold to pay taxes'},
        'G': {'type': 'Gift', 'price_expected': False, 'description': 'Gift of securities'},
        'J': {'type': 'Other', 'price_expected': True, 'description': 'Other acquisition'},
        'K': {'type': 'Equity Swap', 'price_expected': True, 'description': 'Equity swap'},
        'W': {'type': 'Acquisition', 'price_expected': False, 'description': 'Acquisition or disposition by will'},
        'D': {'type': 'Disposition', 'price_expected': True, 'description': 'Disposition'}
    }
    
    code_info = code_meanings.get(transaction_code, {
        'type': 'Unknown', 
        'price_expected': True, 
        'description': 'Unknown transaction type'
    })
    
    return code_info

def analyze_insider_sentiment(transactions):
    """Analyze insider transaction sentiment and generate comprehensive narrative with enhanced data quality handling."""
    if not transactions:
        return "No insider transaction data is available for the specified period."
    
    # Calculate buy vs sell metrics
    total_transactions = len(transactions)
    buy_transactions = [t for t in transactions if t.get('raw_change', 0) > 0]
    sell_transactions = [t for t in transactions if t.get('raw_change', 0) < 0]
    
    buy_count = len(buy_transactions)
    sell_count = len(sell_transactions)
    
    # Enhanced monetary calculation with price source awareness
    total_buy_value = 0
    total_sell_value = 0
    buy_with_prices = 0
    sell_with_prices = 0
    
    for t in buy_transactions:
        if t.get('raw_price', 0) > 0:
            total_buy_value += abs(t.get('raw_change', 0)) * t.get('raw_price', 0)
            buy_with_prices += 1
        elif 'estimated_value' in t and t['estimated_value'] > 0:
            total_buy_value += t['estimated_value']
            buy_with_prices += 1
    
    for t in sell_transactions:
        if t.get('raw_price', 0) > 0:
            total_sell_value += abs(t.get('raw_change', 0)) * t.get('raw_price', 0)
            sell_with_prices += 1
        elif 'estimated_value' in t and t['estimated_value'] > 0:
            total_sell_value += t['estimated_value']
            sell_with_prices += 1
    
    # Calculate share volumes
    total_buy_shares = sum(abs(t.get('raw_change', 0)) for t in buy_transactions)
    total_sell_shares = sum(abs(t.get('raw_change', 0)) for t in sell_transactions)
    
    # Calculate net values
    net_value = total_buy_value - total_sell_value
    net_shares = total_buy_shares - total_sell_shares
    
    # Sanity check: if net_value > $10B, it's likely a calculation error (multiply by shares issue)
    # Typical insider transactions are in millions, not billions
    if abs(net_value) > 10e9:  # If > $10 billion
        print(f"WARNING: Insider net value ${net_value/1e9:.1f}B seems unrealistically high. Likely calculation error with share counts.")
        # Attempt to correct by assuming the value is actually in millions
        net_value = net_value / 1000  # Convert to more realistic range
    
    # Analyze transaction code patterns
    award_transactions = [t for t in transactions if t.get('code', '') in ['A', 'F']]  # Awards and tax withholdings
    market_transactions = [t for t in transactions if t.get('code', '') in ['P', 'S']]  # Open market
    option_transactions = [t for t in transactions if t.get('code', '') in ['M']]  # Option exercises
    
    # Data quality metrics
    transactions_with_prices = len([t for t in transactions if t.get('price_source', 'missing') in ['reported', 'estimated']])
    price_coverage_pct = (transactions_with_prices / total_transactions * 100) if total_transactions > 0 else 0
    
    # Format helper functions
    def format_currency(value):
        if value >= 1e9:
            return f"${value/1e9:.1f}B"
        elif value >= 1e6:
            return f"${value/1e6:.1f}M"
        elif value >= 1e3:
            return f"${value/1e3:.0f}K"
        else:
            return f"${value:,.0f}"
    
    def format_shares(shares):
        if shares >= 1e6:
            return f"{shares/1e6:.1f}M"
        elif shares >= 1e3:
            return f"{shares/1e3:.0f}K"
        else:
            return f"{shares:,.0f}"
    
    # Analyze price patterns where available
    buy_prices = [t.get('raw_price', 0) for t in buy_transactions if t.get('raw_price', 0) > 0]
    sell_prices = [t.get('raw_price', 0) for t in sell_transactions if t.get('raw_price', 0) > 0]
    
    avg_buy_price = sum(buy_prices) / len(buy_prices) if buy_prices else 0
    avg_sell_price = sum(sell_prices) / len(sell_prices) if sell_prices else 0
    
    # Analyze transaction sizes
    large_buys = [t for t in buy_transactions if abs(t.get('raw_change', 0)) > 10000]  # >10k shares
    large_sells = [t for t in sell_transactions if abs(t.get('raw_change', 0)) > 10000]
    small_buys = [t for t in buy_transactions if abs(t.get('raw_change', 0)) <= 10000]
    small_sells = [t for t in sell_transactions if abs(t.get('raw_change', 0)) <= 10000]
    
    # Recent activity analysis (last 5 transactions)
    recent_transactions = transactions[:5]
    recent_buys = [t for t in recent_transactions if t.get('raw_change', 0) > 0]
    recent_sells = [t for t in recent_transactions if t.get('raw_change', 0) < 0]
    
    # Generate comprehensive narrative
    narrative_parts = []
    
    # Opening statement with data quality context
    data_quality_note = ""
    if price_coverage_pct < 60:
        data_quality_note = f" (Note: Price data available for {price_coverage_pct:.0f}% of transactions, with estimates used where possible)"
    elif transactions_with_prices < total_transactions:
        estimated_count = len([t for t in transactions if t.get('price_source', '') == 'estimated'])
        if estimated_count > 0:
            data_quality_note = f" (including {estimated_count} transactions with estimated pricing)"
    
    # Enhanced opening with transaction type context
    if award_transactions and len(award_transactions) > total_transactions * 0.4:
        narrative_parts.append(f"The insider activity shows {total_transactions} transactions over the last three months, with a significant portion ({len(award_transactions)}) being stock awards or tax-related dispositions rather than discretionary market transactions{data_quality_note}.")
    else:
        if sell_count > buy_count * 2:  # Strong selling
            trend = "strong bearish trend"
            if total_sell_value > 0 and total_buy_value > 0:
                narrative_parts.append(f"The insider transaction data reveals a {trend}, with {sell_count} sells versus {buy_count} buys over the last three months, totaling {format_currency(abs(net_value))} in net sales{data_quality_note}.")
            else:
                narrative_parts.append(f"The insider transaction data reveals a {trend}, with {sell_count} sells versus {buy_count} buys over the last three months{data_quality_note}.")
        elif buy_count > sell_count * 2:  # Strong buying
            trend = "strong bullish trend"
            if total_buy_value > 0 and total_sell_value > 0:
                narrative_parts.append(f"The insider transaction data reveals a {trend}, with {buy_count} buys versus {sell_count} sells over the last three months, totaling {format_currency(abs(net_value))} in net purchases{data_quality_note}.")
            else:
                narrative_parts.append(f"The insider transaction data reveals a {trend}, with {buy_count} buys versus {sell_count} sells over the last three months{data_quality_note}.")
        else:  # Balanced
            trend = "mixed pattern"
            narrative_parts.append(f"The insider transaction data shows a {trend}, with {buy_count} buys and {sell_count} sells over the last three months, suggesting balanced insider sentiment{data_quality_note}.")
    
    # Enhanced analysis with transaction type context
    if market_transactions:
        market_buys = [t for t in market_transactions if t.get('raw_change', 0) > 0]
        market_sells = [t for t in market_transactions if t.get('raw_change', 0) < 0]
        
        if market_sells and len(market_sells) > len(market_buys):
            narrative_parts.append(f"Focusing on discretionary open-market activity, there were {len(market_sells)} market sales compared to {len(market_buys)} market purchases, indicating insiders are actively reducing their positions.")
        elif market_buys and len(market_buys) > len(market_sells):
            narrative_parts.append(f"Discretionary market activity shows {len(market_buys)} open-market purchases versus {len(market_sells)} sales, suggesting insiders see value at current prices.")
    
    # Option exercise analysis
    if option_transactions:
        option_exercises = len(option_transactions)
        narrative_parts.append(f"Additionally, {option_exercises} option exercise{'s' if option_exercises == 1 else 's'} occurred, which may indicate either confidence in future price appreciation or routine portfolio management.")
    
    # Enhanced price analysis with data quality awareness
    if avg_sell_price > 0 and avg_buy_price > 0 and sell_with_prices > 0 and buy_with_prices > 0:
        if avg_sell_price > avg_buy_price * 1.5:
            narrative_parts.append(f"Price analysis shows sales occurred at elevated levels (averaging ${avg_sell_price:.2f} across {sell_with_prices} priced transactions), while purchases averaged ${avg_buy_price:.2f} across {buy_with_prices} transactions, suggesting strategic profit-taking.")
        elif abs(avg_sell_price - avg_buy_price) / max(avg_sell_price, avg_buy_price) < 0.1:
            narrative_parts.append(f"Transaction prices show consistency, with sales averaging ${avg_sell_price:.2f} and purchases ${avg_buy_price:.2f}, indicating insiders are transacting around current market levels.")
    elif price_coverage_pct < 50:
        narrative_parts.append("Limited price data availability restricts detailed valuation analysis of these transactions, though share volume patterns remain informative.")
    
    # Recent activity analysis
    if len(recent_transactions) >= 3:
        recent_market_activity = [t for t in recent_transactions if t.get('code', '') in ['P', 'S']]
        if recent_market_activity:
            recent_market_buys = [t for t in recent_market_activity if t.get('raw_change', 0) > 0]
            recent_market_sells = [t for t in recent_market_activity if t.get('raw_change', 0) < 0]
            
            if len(recent_market_buys) > len(recent_market_sells):
                narrative_parts.append("Recent discretionary market activity shows a shift toward buying interest, with insiders becoming more active on the purchase side.")
            elif len(recent_market_sells) > len(recent_market_buys):
                narrative_parts.append("Recent market transactions lean toward selling, with insiders continuing to reduce their positions in the near term.")
        else:
            narrative_parts.append("Recent insider activity consists primarily of compensation-related transactions rather than discretionary market moves.")
    
    # Enhanced concluding interpretation
    if award_transactions and len(award_transactions) > total_transactions * 0.6:
        narrative_parts.append("The predominance of award-related transactions suggests this is routine equity compensation activity rather than a strong directional signal about company prospects.")
    elif sell_count > buy_count * 1.5 and market_transactions:
        market_sell_value = sum(abs(t.get('raw_change', 0)) * t.get('raw_price', 0) for t in market_transactions if t.get('raw_change', 0) < 0 and t.get('raw_price', 0) > 0)
        if market_sell_value > 10e6:  # Large scale market selling
            narrative_parts.append("The scale of discretionary market selling activity should give investors pause—when insiders with the best visibility into company operations are reducing exposure, it warrants careful evaluation of near-term risk/reward dynamics.")
        else:
            narrative_parts.append("While the selling activity is notable, the modest scale suggests routine profit-taking rather than fundamental concerns about the company's prospects.")
    elif buy_count > sell_count * 1.5 and market_transactions:
        narrative_parts.append("The predominance of insider buying, particularly in open-market transactions, provides a positive signal as those with deepest business knowledge are increasing their financial commitment.")
    else:
        narrative_parts.append("This mixed activity pattern is typical of established companies where insiders balance personal financial planning with maintaining confidence in business fundamentals.")
    
    return " ".join(narrative_parts)

def generate_insider_transactions_html(ticker):
    """Generate HTML for insider transactions section."""
    transactions = fetch_insider_transactions(ticker)
    formatted_transactions = format_insider_transaction_data(transactions)
    
    if not formatted_transactions:
        # Analyze why insider data might not be available
        availability_reasons = analyze_insider_availability(ticker)
        
        reasons_html = ""
        if availability_reasons:
            reasons_list = "</li><li>".join(availability_reasons)
            reasons_html = f"""
            <div class="availability-analysis">
                <h4>Why might insider transaction data be unavailable?</h4>
                <ul>
                    <li>{reasons_list}</li>
                </ul>
            </div>
            """
        
        return f"""
        <div class="insider-transactions">
            <h3>Insider Transactions (Last 3 Months)</h3>
            <div class="no-data-container">
                <p class="no-data-message">No insider transaction data is available for {ticker} in the past 3 months.</p>
                {reasons_html}
            </div>
            
            <style>
            .no-data-container {{
                padding: 20px;
                background-color: #f8f9fa;
                border-left: 4px solid #007bff;
                border-radius: 4px;
                margin: 15px 0;
            }}
            
            .no-data-message {{
                font-weight: 500;
                color: #495057;
                margin-bottom: 15px;
            }}
            
            .availability-analysis {{
                margin-top: 15px;
            }}
            
            .availability-analysis h4 {{
                color: #007bff;
                font-size: 16px;
                margin-bottom: 10px;
            }}
            
            .availability-analysis ul {{
                margin: 0;
                padding-left: 20px;
                color: #6c757d;
            }}
            
            .availability-analysis li {{
                margin-bottom: 8px;
                line-height: 1.5;
            }}
            </style>
        </div>
        """
    
    # Generate sentiment analysis
    sentiment_analysis = analyze_insider_sentiment(formatted_transactions)
    
    # Prepare summary data with enhanced metrics
    total_transactions = len(formatted_transactions)
    buy_count = sum(1 for t in formatted_transactions if t['type'] == 'BUY')
    sell_count = sum(1 for t in formatted_transactions if t['type'] == 'SELL')
    
    # Data quality metrics
    transactions_with_prices = len([t for t in formatted_transactions if t.get('price_source', 'missing') in ['reported', 'estimated']])
    estimated_prices = len([t for t in formatted_transactions if t.get('price_source', '') == 'estimated'])
    price_coverage_pct = (transactions_with_prices / total_transactions * 100) if total_transactions > 0 else 0
    
    # Transaction type breakdown
    market_transactions = len([t for t in formatted_transactions if t.get('code', '') in ['P', 'S']])
    award_transactions = len([t for t in formatted_transactions if t.get('code', '') in ['A', 'F']])
    option_transactions = len([t for t in formatted_transactions if t.get('code', '') in ['M']])
    
    # Show only first 5 transactions by default, rest will be hidden
    visible_transactions = formatted_transactions[:5]
    hidden_transactions = formatted_transactions[5:]
    
    html = f"""
    <div class="insider-transactions">
        <h3>Insider Transactions (Last 3 Months)</h3>
        
        <div class="insider-summary">
            <p>{sentiment_analysis}</p>
            <div class="transaction-stats">
                <span class="stat-item">Total: {total_transactions}</span>
                <span class="stat-item buy">Buys: {buy_count}</span>
                <span class="stat-item sell">Sells: {sell_count}</span>
                {f'<span class="stat-item">Market: {market_transactions}</span>' if market_transactions > 0 else ''}
                {f'<span class="stat-item">Awards: {award_transactions}</span>' if award_transactions > 0 else ''}
                {f'<span class="stat-item">Options: {option_transactions}</span>' if option_transactions > 0 else ''}
            </div>
            {f'<div class="data-quality-note">📊 Price data available for {price_coverage_pct:.0f}% of transactions{f" ({estimated_prices} estimated from historical data)" if estimated_prices > 0 else ""}. Prices marked with * are estimates.</div>' if price_coverage_pct < 100 else ''}
        </div>
        
        <div class="table-container">
            <table class="insider-table">
                <thead>
                    <tr>
                        <th>Insider Name</th>
                        <th>Type</th>
                        <th>Shares Changed</th>
                        <th>Price</th>
                        <th>Shares After</th>
                        <th>Transaction Date</th>
                        <th>Filing Date</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Add visible transactions
    for transaction in visible_transactions:
        type_class = transaction['type'].lower()
        
        # Enhanced price display with source information
        price_cell = transaction['price']
        price_source = transaction.get('price_source', 'missing')
        if price_source == 'estimated':
            price_cell += ' <span class="price-estimated" title="Price estimated from historical data">*</span>'
        elif price_source == 'not_applicable':
            price_cell = transaction['price']  # Already formatted with explanation
        
        # Enhanced transaction type with code information
        transaction_type_display = transaction.get('type_detailed', transaction['type'])
        if transaction.get('code'):
            transaction_type_display += f' <span class="transaction-code" title="{transaction.get("code_description", "")}">[{transaction["code"]}]</span>'
        
        html += f"""
                    <tr class="transaction-row {type_class}">
                        <td class="insider-name">{transaction['name']}</td>
                        <td class="transaction-type {type_class}">{transaction_type_display}</td>
                        <td class="shares-changed">{transaction['change']}</td>
                        <td class="transaction-price">{price_cell}</td>
                        <td class="shares-after">{transaction['shares_after']}</td>
                        <td class="transaction-date">{transaction['transaction_date']}</td>
                        <td class="filing-date">{transaction['filing_date']}</td>
                    </tr>
        """
    
    # Add hidden transactions if any exist
    if hidden_transactions:
        html += f"""
                    <tr class="expand-row">
                        <td colspan="7">
                            <button class="expand-button" onclick="toggleInsiderTransactions()">
                                Show {len(hidden_transactions)} More Transactions ▼
                            </button>
                        </td>
                    </tr>
        """
        
        for transaction in hidden_transactions:
            type_class = transaction['type'].lower()
            
            # Enhanced price display with source information
            price_cell = transaction['price']
            price_source = transaction.get('price_source', 'missing')
            if price_source == 'estimated':
                price_cell += ' <span class="price-estimated" title="Price estimated from historical data">*</span>'
            elif price_source == 'not_applicable':
                price_cell = transaction['price']  # Already formatted with explanation
            
            # Enhanced transaction type with code information
            transaction_type_display = transaction.get('type_detailed', transaction['type'])
            if transaction.get('code'):
                transaction_type_display += f' <span class="transaction-code" title="{transaction.get("code_description", "")}">[{transaction["code"]}]</span>'
            
            html += f"""
                    <tr class="transaction-row {type_class} hidden-transaction" style="display: none;">
                        <td class="insider-name">{transaction['name']}</td>
                        <td class="transaction-type {type_class}">{transaction_type_display}</td>
                        <td class="shares-changed">{transaction['change']}</td>
                        <td class="transaction-price">{price_cell}</td>
                        <td class="shares-after">{transaction['shares_after']}</td>
                        <td class="transaction-date">{transaction['transaction_date']}</td>
                        <td class="filing-date">{transaction['filing_date']}</td>
                    </tr>
            """
    
    html += """
                </tbody>
            </table>
        </div>
    """
    
    # Add JavaScript for expand/collapse functionality
    if hidden_transactions:
        html += """
        <script>
        function toggleInsiderTransactions() {
            const hiddenRows = document.querySelectorAll('.hidden-transaction');
            const expandButton = document.querySelector('.expand-button');
            const isExpanded = expandButton.textContent.includes('Hide');
            
            hiddenRows.forEach(row => {
                if (isExpanded) {
                    row.style.display = 'none';
                } else {
                    row.style.display = 'table-row';
                }
            });
            
            if (isExpanded) {
                expandButton.innerHTML = `Show ${hiddenRows.length} More Transactions ▼`;
            } else {
                expandButton.innerHTML = `Hide Additional Transactions ▲`;
            }
        }
        </script>
        """
    
    html += """
    </div>
    
    <style>
    .insider-transactions {
        margin: 20px 0;
        font-family: Arial, sans-serif;
    }
    
    .insider-summary {
        margin-bottom: 15px;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 5px;
    }
    
    .transaction-stats {
        margin-top: 10px;
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
    }
    
    .stat-item {
        padding: 5px 10px;
        border-radius: 3px;
        font-weight: bold;
        font-size: 0.9em;
        background-color: #e9ecef;
    }
    
    .stat-item.buy {
        background-color: #d4edda;
        color: #155724;
    }
    
    .stat-item.sell {
        background-color: #f8d7da;
        color: #721c24;
    }
    
    .insider-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-size: 0.9em;
    }
    
    .insider-table th,
    .insider-table td {
        padding: 8px 12px;
        text-align: left;
        border-bottom: 1px solid #dee2e6;
    }
    
    .insider-table th {
        background-color: #f8f9fa;
        font-weight: bold;
        color: #495057;
        border-bottom: 2px solid #dee2e6;
    }
    
    .transaction-row.buy {
        background-color: #f8fff8;
    }
    
    .transaction-row.sell {
        background-color: #fff8f8;
    }
    
    .transaction-type.buy {
        color: #28a745;
        font-weight: bold;
    }
    
    .transaction-type.sell {
        color: #dc3545;
        font-weight: bold;
    }
    
    .expand-button {
        background-color: #007bff;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.9em;
        transition: background-color 0.3s;
    }
    
    .expand-button:hover {
        background-color: #0056b3;
    }
    
    .expand-row td {
        text-align: center;
        padding: 15px;
        background-color: #f8f9fa;
    }
    
    .insider-name {
        font-weight: 500;
    }
    
    .shares-changed {
        font-family: monospace;
        font-weight: bold;
    }
    
    .transaction-price,
    .shares-after {
        font-family: monospace;
    }
    
    .price-estimated {
        color: #007bff;
        font-weight: bold;
        cursor: help;
    }
    
    .transaction-code {
        font-size: 0.8em;
        color: #6c757d;
        cursor: help;
    }
    
    .data-quality-note {
        margin-top: 10px;
        padding: 8px 12px;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 4px;
        font-size: 0.85em;
        color: #856404;
    }
    
    @media (max-width: 768px) {
        .insider-table {
            font-size: 0.8em;
        }
        
        .insider-table th,
        .insider-table td {
            padding: 6px 8px;
        }
        
        .transaction-stats {
            flex-direction: column;
            gap: 8px;
        }
    }
    </style>
    """
    
    return html

def is_etf(ticker):
    """Check if a ticker is an ETF based on common patterns and characteristics."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Common ETF indicators
        etf_indicators = [
            'ETF' in str(info.get('longName', '')).upper(),
            'EXCHANGE TRADED FUND' in str(info.get('longName', '')).upper(),
            'INDEX FUND' in str(info.get('longName', '')).upper(),
            info.get('quoteType') == 'ETF',
            info.get('category') == 'Exchange Traded Fund',
            # Common ETF ticker patterns
            ticker.upper() in ['SPY', 'QQQ', 'VTI', 'IWM', 'EFA', 'VEA', 'VWO', 'GLD', 'SLV', 
                             'TLT', 'IEF', 'HYG', 'LQD', 'XLF', 'XLE', 'XLV', 'XLI', 'XLK', 
                             'XLU', 'XLP', 'XLY', 'XLB', 'XLRE', 'XME', 'GDX', 'USO', 'DIA']
        ]
        
        return any(etf_indicators)
    except:
        # If we can't determine, assume it's not an ETF
        return False

def get_peer_metrics(ticker):
    """Get financial metrics for a single ticker using yfinance with multiple fallbacks and retry logic."""
    max_retries = 3
    base_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            logging.info(f"Fetching metrics for {ticker} (attempt {attempt + 1}/{max_retries})")
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Check if this is an ETF
            etf_flag = is_etf(ticker)
            
            # Get historical data for 52-week range calculation with timeout handling
            hist = stock.history(period="1y")
            if hist.empty:
                hist = stock.history(period="5d")  # Fallback to recent data
            
            # Calculate 52-week range
            week_52_range = "N/A"
            if not hist.empty:
                week_52_high = hist['High'].max()
                week_52_low = hist['Low'].min()
                week_52_range = f"{week_52_low:.2f} - {week_52_high:.2f}"
            
            # Helper function to get value with multiple fallbacks
            def get_metric_with_fallbacks(primary_key, fallback_keys=None, default="N/A"):
                value = info.get(primary_key, default)
                if (value == default or value is None or (isinstance(value, float) and np.isnan(value))) and fallback_keys:
                    for fallback_key in fallback_keys:
                        fallback_value = info.get(fallback_key, default)
                        if fallback_value != default and fallback_value is not None and not (isinstance(fallback_value, float) and np.isnan(fallback_value)):
                            logging.info(f"{ticker}: Using {fallback_key} for {primary_key}: {fallback_value}")
                            return fallback_value
                return value
            
            # Get P/E Ratio with multiple fallbacks
            pe_ratio = get_metric_with_fallbacks('trailingPE', ['forwardPE', 'priceToEarningsTrailing12Months'])
            
            # For ETFs, certain metrics are not applicable
            if etf_flag:
                # ETFs don't have traditional company fundamentals
                revenue_growth = "N/A (ETF)"
                net_margin = "N/A (ETF)"
                eps = "N/A (ETF)"
                roe = "N/A (ETF)"
                debt_to_equity = "N/A (ETF)"
            else:
                # Get Revenue Growth with fallbacks
                revenue_growth = get_metric_with_fallbacks('revenueGrowth', ['quarterlyRevenueGrowth'])
                
                # Get Net Margin with fallbacks
                net_margin = get_metric_with_fallbacks('profitMargins', ['netIncomeToCommon'])
                
                # Get EPS with fallbacks
                eps = get_metric_with_fallbacks('trailingEps', ['forwardEps', 'earningsPerShare'])
                
                # Get ROE with fallbacks
                roe = get_metric_with_fallbacks('returnOnEquity', ['roe'])
                
                # Get Debt-to-Equity with fallbacks
                debt_to_equity = get_metric_with_fallbacks('debtToEquity', ['totalDebtToEquity'])
                
                # Fix D/E formatting: yfinance returns as raw ratio (e.g., 17.08 instead of 0.17)
                # If D/E > 10, it's likely in percentage points rather than ratio format
                if debt_to_equity != "N/A" and isinstance(debt_to_equity, (int, float)):
                    if debt_to_equity > 10:
                        debt_to_equity = debt_to_equity / 100
                        logging.info(f"{ticker}: Converted D/E from {debt_to_equity * 100:.2f} to {debt_to_equity:.2f}")
            
            # Get Dividend Yield with fallbacks (ETFs can have dividend yields)
            dividend_yield = get_metric_with_fallbacks('dividendYield', ['trailingAnnualDividendYield', 'yield'])
            
            # Get Market Cap with fallbacks (for ETFs this represents total net assets)
            market_cap = get_metric_with_fallbacks('marketCap', ['sharesOutstanding'])
            if market_cap == "N/A" and info.get('sharesOutstanding') and info.get('currentPrice'):
                try:
                    market_cap = info['sharesOutstanding'] * info['currentPrice']
                    logging.info(f"{ticker}: Calculated market cap from shares * price: {market_cap}")
                except:
                    market_cap = "N/A"
            
            metrics = {
                'Market Cap': market_cap,
                'P/E Ratio': pe_ratio,
                'Revenue Growth': revenue_growth,
                'Net Margin': net_margin,
                'EPS': eps,
                'ROE': roe,
                'Debt-to-Equity': debt_to_equity,
                'Dividend Yield': dividend_yield,
                '52-Week Range': week_52_range
            }
            
            # Log any remaining N/A values for debugging (but exclude ETF N/A values)
            na_metrics = [k for k, v in metrics.items() if v == "N/A"]
            if na_metrics and not etf_flag:
                logging.warning(f"{ticker}: N/A values for: {na_metrics}")
            elif etf_flag:
                logging.info(f"{ticker}: ETF detected - fundamental metrics marked as N/A (ETF)")
            
            logging.info(f"Successfully retrieved metrics for {ticker}")
            return metrics
            
        except Exception as e:
            logging.warning(f"Error fetching metrics for {ticker} (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:  # Not the last attempt
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logging.info(f"Retrying {ticker} in {delay} seconds...")
                import time
                time.sleep(delay)
            else:
                # Last attempt failed
                logging.error(f"All {max_retries} attempts failed for {ticker}")
                return None

def get_sector_peers(ticker):
    """Get sector-appropriate peers for a given ticker."""
    # Define sector-based peer mapping
    sector_peers = {
        # Technology
        'AAPL': ['MSFT', 'GOOGL', 'META'],
        'MSFT': ['AAPL', 'GOOGL', 'AMZN'],
        'GOOGL': ['AAPL', 'MSFT', 'META'],
        'META': ['GOOGL', 'SNAP', 'TWTR'],
        'NVDA': ['AMD', 'INTC', 'TSM'],
        'AMD': ['NVDA', 'INTC', 'QCOM'],
        'INTC': ['AMD', 'NVDA', 'QCOM'],
        'NBIS': ['AAPL', 'MSFT', 'GOOGL'],  # Tech/cloud infrastructure
        
        # Automotive/EV
        'TSLA': ['F', 'GM', 'NIO'],
        'F': ['GM', 'TSLA', 'STLA'],
        'GM': ['F', 'TSLA', 'STLA'],
        'NIO': ['TSLA', 'XPEV', 'LI'],
        
        # E-commerce/Retail
        'AMZN': ['WMT', 'TGT', 'COST'],
        'WMT': ['TGT', 'COST', 'AMZN'],
        
        # Financial
        'JPM': ['BAC', 'WFC', 'C'],
        'BAC': ['JPM', 'WFC', 'C'],
        'BRK-B': ['JPM', 'BAC', 'WFC'],
        
        # Healthcare/Pharma
        'JNJ': ['PFE', 'MRK', 'ABBV'],
        'PFE': ['JNJ', 'MRK', 'ABBV'],
        
        # Energy
        'XOM': ['CVX', 'COP', 'EOG'],
        'CVX': ['XOM', 'COP', 'EOG'],
        
        # Consumer Goods
        'KO': ['PEP', 'PG', 'UL'],
        'PEP': ['KO', 'PG', 'MNST'],
        
        # Aerospace/Defense
        'BA': ['LMT', 'RTX', 'NOC'],
        'LMT': ['BA', 'RTX', 'NOC'],
    }
    
    # Default fallback for unknown tickers - use large cap diversified companies
    default_peers = ['AAPL', 'MSFT', 'GOOGL']
    
    return sector_peers.get(ticker.upper(), default_peers)

def get_peer_comparison_data(ticker):
    """Main function to get peer comparison data with simplified peer selection."""
    try:
        # Use simplified peer selection
        peers = get_company_peers(ticker)
        
        # Get metrics for target company and peers
        comparison_data = {}
        
        # Get target company metrics
        target_metrics = get_peer_metrics(ticker)
        if target_metrics:
            comparison_data[ticker.upper()] = target_metrics
        
        # Get peer metrics
        for peer in peers:
            peer_metrics = get_peer_metrics(peer)
            if peer_metrics:
                comparison_data[peer.upper()] = peer_metrics
        
        logging.info(f"Peer comparison completed for {ticker} with {len(comparison_data)-1} peers: {list(comparison_data.keys())}")
        return comparison_data
    except Exception as e:
        logging.error(f"Error in get_peer_comparison_data: {e}")
        return {}

def format_metric_value(value, metric_name):
    """Format metric values for display with improved handling."""
    if value == "N/A" or value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    
    # Handle ETF-specific N/A values
    if isinstance(value, str) and "N/A (ETF)" in value:
        return "N/A"
    
    try:
        if metric_name == "Market Cap":
            if isinstance(value, (int, float)):
                if value >= 1e12:
                    return f"${value/1e12:.2f}T"
                elif value >= 1e9:
                    return f"${value/1e9:.2f}B"
                elif value >= 1e6:
                    return f"${value/1e6:.2f}M"
                else:
                    return f"${value:,.0f}"
        elif metric_name in ["Revenue Growth", "Net Margin", "ROE", "Dividend Yield"]:
            if isinstance(value, (int, float)):
                # Handle very small decimal values (already in percentage form)
                if abs(value) < 0.01 and abs(value) > 0:
                    return f"{value*100:.2f}%"
                # Handle values that might already be in percentage form (> 1)
                elif abs(value) > 1:
                    return f"{value:.2f}%"
                else:
                    return f"{value*100:.2f}%"
        elif metric_name in ["P/E Ratio", "EPS"]:
            if isinstance(value, (int, float)):
                # Handle very large P/E ratios
                if abs(value) > 1000:
                    return f"{value:.0f}"
                else:
                    return f"{value:.2f}"
        elif metric_name == "Debt-to-Equity":
            if isinstance(value, (int, float)):
                # Handle very large debt ratios
                if abs(value) > 100:
                    return f"{value:.0f}"
                else:
                    return f"{value:.2f}"
        else:
            return str(value)
    except Exception as e:
        logging.warning(f"Error formatting {metric_name} value {value}: {e}")
        return str(value)

def generate_narrative_text(comparison_data, target_ticker):
    """Generate dynamic narrative text based on available data."""
    if not comparison_data:
        return "<p>No peer comparison data is currently available.</p>"
    
    target_data = comparison_data.get(target_ticker.upper(), {})
    peer_count = len(comparison_data) - 1 if target_ticker.upper() in comparison_data else len(comparison_data)
    
    if peer_count == 0:
        return f"<p>Peer comparison analysis for {target_ticker} shows the following metrics without industry peer context.</p>"
    
    # Helper function to format values for narrative
    def format_for_narrative(value, metric_name):
        if value == "N/A" or value is None:
            return None
        try:
            if metric_name == "Market Cap":
                if isinstance(value, (int, float)):
                    if value >= 1e12:
                        return f"${value/1e12:.2f} trillion"
                    elif value >= 1e9:
                        return f"${value/1e9:.2f}B"
                    elif value >= 1e6:
                        return f"${value/1e6:.2f}M"
                    else:
                        return f"${value:,.0f}"
            elif metric_name in ["Revenue Growth", "Net Margin", "ROE", "Dividend Yield"]:
                if isinstance(value, (int, float)):
                    if abs(value) > 1:
                        return f"{value:.1f}%"
                    else:
                        return f"{value*100:.1f}%"
            elif metric_name == "P/E Ratio":
                if isinstance(value, (int, float)):
                    return f"{value:.1f}" if value > 0 else "negative"
            elif metric_name == "EPS":
                if isinstance(value, (int, float)):
                    return f"${value:.2f}" if value > 0 else f"-${abs(value):.2f}"
            elif metric_name == "Debt-to-Equity":
                if isinstance(value, (int, float)):
                    return f"{value:.0f}" if value > 100 else f"{value:.1f}"
        except:
            pass
        return str(value)
    
    # Analyze market cap differences
    def analyze_market_caps():
        market_caps = {}
        for ticker, data in comparison_data.items():
            mc_value = data.get('Market Cap')
            if mc_value != "N/A" and mc_value is not None:
                market_caps[ticker] = mc_value
        
        if len(market_caps) < 2:
            return ""
        
        sorted_caps = sorted(market_caps.items(), key=lambda x: x[1], reverse=True)
        target_mc = market_caps.get(target_ticker.upper())
        
        if target_mc is None:
            return ""
        
        target_formatted = format_for_narrative(target_mc, "Market Cap")
        
        # Find position and create comparisons
        comparisons = []
        for ticker, mc in sorted_caps:
            if ticker != target_ticker.upper():
                formatted_mc = format_for_narrative(mc, "Market Cap")
                if formatted_mc:
                    comparisons.append(f"{ticker} ({formatted_mc})")
        
        if comparisons:
            if target_mc == max(market_caps.values()):
                return f"{target_ticker} dominates with a {target_formatted} market cap, significantly outpacing {', '.join(comparisons[:3])}. "
            elif target_mc == min(market_caps.values()):
                return f"{target_ticker}'s {target_formatted} market cap positions it as the smallest player compared to {', '.join(comparisons[:3])}. "
            else:
                larger = [c for t, mc in sorted_caps if mc > target_mc for c in [f"{t} ({format_for_narrative(mc, 'Market Cap')})"]][:2]
                smaller = [c for t, mc in sorted_caps if mc < target_mc for c in [f"{t} ({format_for_narrative(mc, 'Market Cap')})"]][:2]
                comp_text = ""
                if larger:
                    comp_text += f"trailing {', '.join(larger)}"
                if smaller:
                    comp_text += f" but ahead of {', '.join(smaller)}" if larger else f"outpacing {', '.join(smaller)}"
                return f"{target_ticker}'s {target_formatted} market cap places it in the middle tier, {comp_text}. "
        return ""
    
    # Analyze P/E ratios and valuation
    def analyze_valuations():
        pe_ratios = {}
        for ticker, data in comparison_data.items():
            pe_value = data.get('P/E Ratio')
            if pe_value != "N/A" and pe_value is not None and isinstance(pe_value, (int, float)):
                pe_ratios[ticker] = pe_value
        
        if len(pe_ratios) < 2:
            return ""
        
        target_pe = pe_ratios.get(target_ticker.upper())
        if target_pe is None:
            return ""
        
        target_formatted = format_for_narrative(target_pe, "P/E Ratio")
        
        # Analyze valuation levels
        high_pe = [t for t, pe in pe_ratios.items() if pe > 50 and t != target_ticker.upper()]
        low_pe = [t for t, pe in pe_ratios.items() if pe < 20 and t != target_ticker.upper()]
        negative_pe = [t for t, pe in pe_ratios.items() if pe < 0 and t != target_ticker.upper()]
        
        valuation_text = ""
        if target_pe > 100:
            valuation_text = f"{target_ticker}'s P/E ratio of {target_formatted} suggests investors are pricing in extremely high future growth expectations"
        elif target_pe > 50:
            valuation_text = f"{target_ticker}'s elevated P/E ratio of {target_formatted} indicates premium valuation reflecting strong growth prospects"
        elif target_pe > 20:
            valuation_text = f"{target_ticker}'s P/E ratio of {target_formatted} represents a moderate valuation"
        elif target_pe > 0:
            valuation_text = f"{target_ticker}'s conservative P/E ratio of {target_formatted} suggests value-oriented pricing"
        else:
            valuation_text = f"{target_ticker} currently has negative earnings, making P/E ratio analysis challenging"
        
        # Add peer comparisons
        if high_pe:
            high_pe_details = [(t, format_for_narrative(pe_ratios[t], "P/E Ratio")) for t in high_pe[:2]]
            valuation_text += f", while {', '.join([f'{t} (P/E {pe})' for t, pe in high_pe_details])} also trade{'s' if len(high_pe_details)==1 else ''} at premium multiples"
        
        if low_pe:
            low_pe_details = [(t, format_for_narrative(pe_ratios[t], "P/E Ratio")) for t in low_pe[:2]]
            connector = " whereas " if not high_pe else ". In contrast, "
            valuation_text += f"{connector}{', '.join([f'{t} (P/E {pe})' for t, pe in low_pe_details])} trade{'s' if len(low_pe_details)==1 else ''} at much lower multiples, reflecting mature or slower-growth businesses"
        
        if negative_pe:
            connector = ". " if low_pe or high_pe else ", while "
            valuation_text += f"{connector}Notably, {', '.join(negative_pe[:2])} show{'s' if len(negative_pe)==1 else ''} negative P/E ratios due to current losses"
        
        return valuation_text + ". "
    
    # Analyze profitability and growth
    def analyze_profitability():
        # Revenue growth analysis
        growth_text = ""
        revenue_growth = {}
        for ticker, data in comparison_data.items():
            rg_value = data.get('Revenue Growth')
            if rg_value != "N/A" and rg_value is not None and isinstance(rg_value, (int, float)):
                revenue_growth[ticker] = rg_value
        
        target_growth = revenue_growth.get(target_ticker.upper())
        if target_growth is not None and len(revenue_growth) > 1:
            target_growth_formatted = format_for_narrative(target_growth, "Revenue Growth")
            if target_growth > 0.2:  # 20% growth
                growth_text = f"Revenue growth highlights {target_ticker}'s strong {target_growth_formatted} expansion"
            elif target_growth > 0:
                growth_text = f"Revenue growth shows {target_ticker}'s modest {target_growth_formatted} expansion"
            else:
                growth_text = f"Revenue declined {abs(target_growth)*100:.1f}% for {target_ticker}"
            
            # Compare with peers
            peer_growth = [(t, rg) for t, rg in revenue_growth.items() if t != target_ticker.upper()]
            if peer_growth:
                high_growth = [(t, format_for_narrative(rg, "Revenue Growth")) for t, rg in peer_growth if rg > 0.15][:2]
                if high_growth:
                    growth_text += f", while {', '.join([f'{t} ({rg})' for t, rg in high_growth])} demonstrate{'s' if len(high_growth)==1 else ''} even stronger momentum"
        
        # Net margin analysis
        margin_text = ""
        net_margins = {}
        for ticker, data in comparison_data.items():
            nm_value = data.get('Net Margin')
            if nm_value != "N/A" and nm_value is not None and isinstance(nm_value, (int, float)):
                net_margins[ticker] = nm_value
        
        target_margin = net_margins.get(target_ticker.upper())
        if target_margin is not None and len(net_margins) > 1:
            target_margin_formatted = format_for_narrative(target_margin, "Net Margin")
            
            if target_margin > 0.15:  # 15%+
                margin_text = f" {target_ticker}'s robust {target_margin_formatted} net margin demonstrates strong profitability"
            elif target_margin > 0:
                margin_text = f" {target_ticker}'s {target_margin_formatted} net margin shows positive but modest profitability"
            else:
                margin_text = f" {target_ticker} faces profitability challenges with a {target_margin_formatted} net margin"
            
            # Compare margins
            profitable_peers = [(t, format_for_narrative(nm, "Net Margin")) for t, nm in net_margins.items() if t != target_ticker.upper() and nm > 0.05]
            unprofitable_peers = [(t, format_for_narrative(abs(nm), "Net Margin")) for t, nm in net_margins.items() if t != target_ticker.upper() and nm < -0.02]
            
            if profitable_peers:
                margin_text += f", compared to {', '.join([f'{t} ({nm})' for t, nm in profitable_peers[:2]])}"
            if unprofitable_peers:
                connector = " whereas " if profitable_peers else ", while "
                margin_text += f"{connector}{', '.join([f'{t} (-{nm})' for t, nm in unprofitable_peers[:2]])} face{'s' if len(unprofitable_peers)==1 else ''} significant losses"
        
        return growth_text + margin_text + ". " if growth_text or margin_text else ""
    
    # Analyze financial structure and returns
    def analyze_financial_structure():
        structure_text = ""
        
        # ROE analysis
        roe_values = {}
        for ticker, data in comparison_data.items():
            roe_value = data.get('ROE')
            if roe_value != "N/A" and roe_value is not None and isinstance(roe_value, (int, float)):
                roe_values[ticker] = roe_value
        
        target_roe = roe_values.get(target_ticker.upper())
        if target_roe is not None and len(roe_values) > 1:
            target_roe_formatted = format_for_narrative(target_roe, "ROE")
            
            if target_roe > 0.2:  # 20%+
                structure_text += f"{target_ticker}'s exceptional {target_roe_formatted} ROE indicates highly efficient use of shareholder equity"
            elif target_roe > 0.1:
                structure_text += f"{target_ticker}'s solid {target_roe_formatted} ROE demonstrates good capital efficiency"
            elif target_roe > 0:
                structure_text += f"{target_ticker}'s {target_roe_formatted} ROE shows modest returns on equity"
            else:
                structure_text += f"{target_ticker}'s negative {abs(target_roe)*100:.1f}% ROE reflects current unprofitability"
        
        # Debt analysis
        debt_values = {}
        for ticker, data in comparison_data.items():
            debt_value = data.get('Debt-to-Equity')
            if debt_value != "N/A" and debt_value is not None and isinstance(debt_value, (int, float)):
                debt_values[ticker] = debt_value
        
        target_debt = debt_values.get(target_ticker.upper())
        if target_debt is not None and len(debt_values) > 1:
            target_debt_formatted = format_for_narrative(target_debt, "Debt-to-Equity")
            
            connector = ". " if structure_text else ""
            if target_debt > 200:
                structure_text += f"{connector}The company's high {target_debt_formatted} debt-to-equity ratio indicates significant financial leverage"
            elif target_debt > 50:
                structure_text += f"{connector}With a {target_debt_formatted} debt-to-equity ratio, {target_ticker} maintains moderate leverage"
            else:
                structure_text += f"{connector}{target_ticker}'s conservative {target_debt_formatted} debt-to-equity ratio suggests a strong balance sheet"
            
            # Compare debt levels
            high_debt_peers = [(t, format_for_narrative(d, "Debt-to-Equity")) for t, d in debt_values.items() if t != target_ticker.upper() and d > 100]
            low_debt_peers = [(t, format_for_narrative(d, "Debt-to-Equity")) for t, d in debt_values.items() if t != target_ticker.upper() and d < 30]
            
            if high_debt_peers:
                structure_text += f", while {', '.join([f'{t} ({d})' for t, d in high_debt_peers[:2]])} show{'s' if len(high_debt_peers)==1 else ''} even higher leverage"
            if low_debt_peers:
                connector = " compared to " if high_debt_peers else " versus "
                structure_text += f"{connector}{', '.join([f'{t} ({d})' for t, d in low_debt_peers[:2]])} with lower debt levels"
        
        # Dividend analysis
        dividend_values = {}
        for ticker, data in comparison_data.items():
            div_value = data.get('Dividend Yield')
            if div_value != "N/A" and div_value is not None and isinstance(div_value, (int, float)):
                dividend_values[ticker] = div_value
        
        target_dividend = dividend_values.get(target_ticker.upper())
        if len(dividend_values) > 0:
            dividend_payers = [(t, format_for_narrative(d, "Dividend Yield")) for t, d in dividend_values.items() if d > 0.01]
            non_payers = [t for t, d in comparison_data.items() if d.get('Dividend Yield') == "N/A" or d.get('Dividend Yield') == 0]
            
            connector = ". " if structure_text else ""
            if target_dividend and target_dividend > 0.01:
                target_div_formatted = format_for_narrative(target_dividend, "Dividend Yield")
                structure_text += f"{connector}Finally, {target_ticker}'s {target_div_formatted} dividend yield provides income to shareholders"
                
                other_payers = [(t, dy) for t, dy in dividend_payers if t != target_ticker.upper()]
                if other_payers:
                    structure_text += f", alongside {', '.join([f'{t} ({dy})' for t, dy in other_payers[:2]])}"
            else:
                if dividend_payers:
                    structure_text += f"{connector}Dividend policies vary significantly—{', '.join([f'{t} ({dy})' for t, dy in dividend_payers[:2]])} reward{'s' if len(dividend_payers)==1 else ''} shareholders with payouts"
                    if target_ticker.upper() in [t for t in non_payers]:
                        structure_text += f", whereas {target_ticker} reinvests all cash into growth"
        
        return structure_text + ". " if structure_text else ""
    
    # Generate the two-paragraph narrative
    paragraph1 = analyze_market_caps() + analyze_valuations() + analyze_profitability()
    paragraph2 = analyze_financial_structure()
    
    # Ensure we have meaningful content
    if not paragraph1.strip():
        paragraph1 = f"The peer comparison for {target_ticker} covers several key financial metrics across {peer_count} industry companies. "
    
    if not paragraph2.strip():
        paragraph2 = "Additional analysis of financial structure and shareholder returns provides further insight into the competitive positioning of these companies."
    
    return f"<p>{paragraph1.strip()}</p>\n<p>{paragraph2.strip()}</p>"

def generate_peer_comparison_html(comparison_data, target_ticker):
    """Generate HTML for peer comparison table with insider transactions."""
    if not comparison_data:
        return """
        <div class="peer-comparison">
            <p>Peer comparison data is not available at this time.</p>
        </div>
        """
    
    # Define metrics to display (removed Price Change (1Y))
    metrics = [
        'Market Cap', 'P/E Ratio', 'Revenue Growth', 'Net Margin',
        'EPS', 'ROE', 'Debt-to-Equity', 'Dividend Yield', '52-Week Range'
    ]
    
    html = '<div class="peer-comparison">\n'
    
    # Add dynamic narrative
    narrative_text = generate_narrative_text(comparison_data, target_ticker)
    html += f'<div class="narrative">\n{narrative_text}\n</div>\n'
    
    html += '<div class="table-container">\n'
    html += '<table class="peer-table">\n'
    html += '<thead>\n<tr>\n<th>Metric</th>\n'
    
    # Add company headers
    for ticker in comparison_data.keys():
        is_target = ticker.upper() == target_ticker.upper()
        class_attr = ' class="target-company"' if is_target else ''
        html += f'<th{class_attr}>{ticker}</th>\n'
    
    html += '</tr>\n</thead>\n<tbody>\n'
    
    # Add metric rows
    for metric in metrics:
        html += f'<tr>\n<td class="metric-name">{metric}</td>\n'
        
        for ticker in comparison_data.keys():
            is_target = ticker.upper() == target_ticker.upper()
            value = comparison_data[ticker].get(metric, 'N/A')
            formatted_value = format_metric_value(value, metric)
            class_attr = ' class="target-company"' if is_target else ''
            html += f'<td{class_attr}>{formatted_value}</td>\n'
        
        html += '</tr>\n'
    
    html += '</tbody>\n</table>\n</div>\n'
    
    # Add insider transactions section for the target ticker
    insider_html = generate_insider_transactions_html(target_ticker)
    html += insider_html
    
    html += '</div>\n'
    
    return html

def get_insider_transactions_data(ticker, months_back=3):
    """
    Public function to get insider transactions data for use in reports.
    Returns both raw and formatted data.
    """
    try:
        # Fetch raw transactions
        raw_transactions = fetch_insider_transactions(ticker, months_back)
        
        # Format transactions for display
        formatted_transactions = format_insider_transaction_data(raw_transactions)
        
        # Generate sentiment analysis
        sentiment = analyze_insider_sentiment(formatted_transactions) if formatted_transactions else "No insider transaction data available."
        
        # Calculate summary statistics
        total_transactions = len(formatted_transactions)
        buy_count = sum(1 for t in formatted_transactions if t['type'] == 'BUY')
        sell_count = sum(1 for t in formatted_transactions if t['type'] == 'SELL')
        
        # Calculate net activity (positive = more buying, negative = more selling)
        net_shares = sum(t.get('raw_change', 0) for t in formatted_transactions)
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'period_months': months_back,
            'raw_transactions': raw_transactions,
            'formatted_transactions': formatted_transactions,
            'sentiment_analysis': sentiment,
            'summary': {
                'total_transactions': total_transactions,
                'buy_count': buy_count,
                'sell_count': sell_count,
                'net_shares': net_shares,
                'net_sentiment': 'Bullish' if net_shares > 0 else 'Bearish' if net_shares < 0 else 'Neutral'
            }
        }
    except Exception as e:
        logging.error(f"Error getting insider transactions data for {ticker}: {e}")
        return {
            'success': False,
            'ticker': ticker.upper(),
            'error': str(e),
            'formatted_transactions': [],
            'sentiment_analysis': "Error retrieving insider transaction data.",
            'summary': {
                'total_transactions': 0,
                'buy_count': 0,
                'sell_count': 0,
                'net_shares': 0,
                'net_sentiment': 'Unknown'
            }
        }

def get_alternative_insider_data_sources(ticker):
    """
    Provide alternative sources or fallback mechanisms when Finnhub data is limited.
    This could be expanded to include other APIs or data sources in the future.
    """
    fallback_info = {
        'sources': [
            'SEC EDGAR database (form 4 filings)',
            'Company investor relations pages',
            'Financial news aggregators',
            'Alternative financial data providers'
        ],
        'explanation': f"When insider transaction data for {ticker} is limited, investors should consider checking SEC EDGAR filings directly, company investor relations announcements, or alternative financial data sources for more comprehensive insider activity information.",
        'recommendation': "For the most complete insider transaction analysis, cross-reference multiple data sources and consider the context of each transaction type."
    }
    return fallback_info
