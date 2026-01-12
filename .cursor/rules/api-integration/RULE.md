---
description: "API integration patterns with retry logic and error handling for financial/AI APIs"
alwaysApply: false
globs:
  - "**/data_processing_scripts/*.py"
  - "**/analysis_scripts/*.py"
  - "**/*gemini*.py"
  - "**/*perplexity*.py"
  - "**/market_news.py"
---

# TickZen API Integration Standards

## Core APIs

TickZen integrates with multiple external APIs:
1. **Financial Data**: yfinance, Alpha Vantage, Finnhub, FRED
2. **AI/LLM**: Google Gemini, Perplexity
3. **WordPress**: REST API for publishing
4. **News**: NewsAPI, web scraping

## Golden Rules

1. **Always use retry logic** - APIs are unreliable
2. **Rate limit awareness** - Respect API quotas
3. **Graceful degradation** - Continue with partial data
4. **Cache responses** - Reduce API calls
5. **Log all API calls** - Track usage and errors

## yfinance (Stock Data)

### Basic Usage with Retry
```python
import yfinance as yf
from functools import wraps
import time

def retry_yfinance(max_attempts=3, delay=2):
    """Retry decorator for yfinance calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_attempts - 1:
                        app.logger.warning(f"yfinance attempt {attempt + 1} failed: {e}")
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        app.logger.error(f"yfinance failed after {max_attempts} attempts: {e}")
                        raise
        return wrapper
    return decorator

@retry_yfinance(max_attempts=3, delay=2)
def get_stock_data(ticker, period='1y'):
    """Get stock data with retry logic"""
    try:
        stock = yf.Ticker(ticker)
        
        # Get historical data
        hist = stock.history(period=period)
        
        if hist.empty:
            raise ValueError(f"No data returned for {ticker}")
        
        # Get additional info
        info = stock.info
        
        return {
            'ticker': ticker,
            'history': hist,
            'info': info,
            'current_price': info.get('currentPrice'),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE')
        }
        
    except Exception as e:
        app.logger.error(f"Error fetching {ticker}: {e}", exc_info=True)
        raise

# Usage
try:
    data = get_stock_data('AAPL', period='1mo')
    print(f"Current price: ${data['current_price']}")
except Exception as e:
    # Handle error - maybe use cached data
    data = get_cached_stock_data('AAPL')
```

### Batch Download with Error Handling
```python
def download_multiple_tickers(tickers, period='1y'):
    """Download data for multiple tickers"""
    results = {}
    failed = []
    
    # yfinance batch download
    try:
        data = yf.download(
            tickers=' '.join(tickers),
            period=period,
            group_by='ticker',
            threads=True,
            progress=False
        )
        
        for ticker in tickers:
            try:
                if ticker in data:
                    ticker_data = data[ticker]
                    if not ticker_data.empty:
                        results[ticker] = ticker_data
                    else:
                        failed.append(ticker)
                else:
                    failed.append(ticker)
            except Exception as e:
                app.logger.warning(f"Failed to extract {ticker}: {e}")
                failed.append(ticker)
        
        if failed:
            app.logger.warning(f"Failed to download: {failed}")
        
        return results, failed
        
    except Exception as e:
        app.logger.error(f"Batch download error: {e}", exc_info=True)
        return {}, tickers
```

## Alpha Vantage (Financial Data)

### API Key Management
```python
import os
import requests

ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
ALPHA_VANTAGE_BASE_URL = 'https://www.alphavantage.co/query'

class AlphaVantageRateLimiter:
    """Rate limiter for Alpha Vantage (5 calls/min for free tier)"""
    def __init__(self, calls_per_minute=5):
        self.calls_per_minute = calls_per_minute
        self.call_times = []
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Remove calls older than 1 minute
        self.call_times = [t for t in self.call_times if now - t < 60]
        
        # If at limit, wait
        if len(self.call_times) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.call_times[0])
            if sleep_time > 0:
                app.logger.info(f"Rate limit: waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)
        
        # Record this call
        self.call_times.append(now)

av_limiter = AlphaVantageRateLimiter(calls_per_minute=5)
```

### API Call with Retry
```python
def get_alpha_vantage_data(function, symbol, **params):
    """Generic Alpha Vantage API call"""
    av_limiter.wait_if_needed()
    
    url_params = {
        'function': function,
        'symbol': symbol,
        'apikey': ALPHA_VANTAGE_API_KEY,
        **params
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(
                ALPHA_VANTAGE_BASE_URL,
                params=url_params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API error messages
            if 'Error Message' in data:
                raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
            
            if 'Note' in data:
                # Rate limit message
                app.logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                if attempt < max_retries - 1:
                    time.sleep(60)  # Wait 1 minute
                    continue
                else:
                    raise Exception("Rate limit exceeded")
            
            return data
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                app.logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                app.logger.error(f"Alpha Vantage request failed: {e}", exc_info=True)
                raise
    
    return None

# Usage
try:
    income_statement = get_alpha_vantage_data(
        function='INCOME_STATEMENT',
        symbol='AAPL'
    )
except Exception as e:
    app.logger.error(f"Failed to get income statement: {e}")
    income_statement = None
```

## Finnhub (Real-time Market Data)

### API Setup
```python
import finnhub

FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
```

### Get Earnings Calendar
```python
def get_weekly_earnings(from_date, to_date):
    """Get earnings calendar for date range"""
    try:
        earnings = finnhub_client.earnings_calendar(
            _from=from_date,
            to=to_date,
            symbol='',
            international=False
        )
        
        if 'earningsCalendar' in earnings:
            return earnings['earningsCalendar']
        else:
            app.logger.warning("No earnings calendar data returned")
            return []
            
    except Exception as e:
        app.logger.error(f"Finnhub earnings error: {e}", exc_info=True)
        return []

# Get company profile
def get_company_profile(ticker):
    """Get company information"""
    try:
        profile = finnhub_client.company_profile2(symbol=ticker)
        
        if not profile:
            raise ValueError(f"No profile data for {ticker}")
        
        return {
            'name': profile.get('name'),
            'industry': profile.get('finnhubIndustry'),
            'logo': profile.get('logo'),
            'marketCap': profile.get('marketCapitalization'),
            'weburl': profile.get('weburl')
        }
        
    except Exception as e:
        app.logger.error(f"Finnhub profile error for {ticker}: {e}")
        return None
```

## FRED (Economic Data)

### API Setup
```python
from fredapi import Fred

FRED_API_KEY = os.getenv('FRED_API_KEY')
fred = Fred(api_key=FRED_API_KEY)
```

### Get Economic Indicators
```python
def get_economic_indicator(series_id, start_date=None):
    """Get FRED economic data"""
    try:
        data = fred.get_series(
            series_id,
            observation_start=start_date
        )
        
        if data.empty:
            raise ValueError(f"No data for {series_id}")
        
        return data
        
    except Exception as e:
        app.logger.error(f"FRED API error for {series_id}: {e}", exc_info=True)
        return None

# Common indicators
def get_macro_data():
    """Get key macro indicators"""
    indicators = {
        'gdp': 'GDP',
        'unemployment': 'UNRATE',
        'inflation': 'CPIAUCSL',
        'fed_funds': 'DFF',
        'treasury_10y': 'DGS10'
    }
    
    results = {}
    for name, series_id in indicators.items():
        try:
            data = get_economic_indicator(series_id)
            if data is not None:
                results[name] = {
                    'latest_value': data.iloc[-1],
                    'latest_date': data.index[-1],
                    'data': data
                }
        except Exception as e:
            app.logger.warning(f"Failed to get {name}: {e}")
            results[name] = None
    
    return results
```

## Google Gemini (AI Content Generation)

### API Setup
```python
import google.generativeai as genai

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Model configuration
model = genai.GenerativeModel(
    model_name='gemini-1.5-pro',
    generation_config={
        'temperature': 0.7,
        'top_p': 0.95,
        'top_k': 40,
        'max_output_tokens': 8192
    }
)
```

### Generate Content with Retry
```python
def generate_gemini_content(prompt, max_retries=3):
    """Generate content with Gemini API"""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            
            # Check for blocked content
            if response.prompt_feedback.block_reason:
                raise ValueError(f"Content blocked: {response.prompt_feedback.block_reason}")
            
            # Extract text
            if response.candidates:
                text = response.candidates[0].content.parts[0].text
                return text
            else:
                raise ValueError("No content generated")
                
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                app.logger.warning(f"Gemini retry {attempt + 1}/{max_retries}: {e}")
                time.sleep(wait_time)
            else:
                app.logger.error(f"Gemini generation failed: {e}", exc_info=True)
                raise
    
    return None

# Usage
try:
    article = generate_gemini_content(f"""
    Write a stock analysis article for {ticker}.
    
    Include:
    - Company overview
    - Recent performance
    - Key metrics
    - Investment outlook
    """)
except Exception as e:
    app.logger.error(f"Failed to generate article: {e}")
    article = None
```

### Streaming Response
```python
def generate_gemini_streaming(prompt, progress_callback=None):
    """Generate content with streaming for real-time updates"""
    try:
        response = model.generate_content(prompt, stream=True)
        
        full_text = ""
        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(chunk.text)
        
        return full_text
        
    except Exception as e:
        app.logger.error(f"Gemini streaming error: {e}", exc_info=True)
        raise
```

## Perplexity (AI Research)

### API Setup
```python
import openai

PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

# Perplexity uses OpenAI-compatible API
perplexity_client = openai.OpenAI(
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai"
)
```

### Research Query
```python
def perplexity_research(query, model='llama-3.1-sonar-large-128k-online'):
    """Use Perplexity for web-grounded research"""
    try:
        response = perplexity_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial research assistant. Provide accurate, up-to-date information with sources."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.2,
            max_tokens=2000
        )
        
        if response.choices:
            content = response.choices[0].message.content
            
            # Extract citations if available
            citations = getattr(response, 'citations', [])
            
            return {
                'content': content,
                'citations': citations,
                'model': model
            }
        else:
            raise ValueError("No response from Perplexity")
            
    except Exception as e:
        app.logger.error(f"Perplexity API error: {e}", exc_info=True)
        return None

# Usage
research = perplexity_research(f"What are the latest developments for {ticker}?")
if research:
    print(research['content'])
    print("Sources:", research.get('citations', []))
```

## WordPress REST API

### Authentication
```python
import requests
from requests.auth import HTTPBasicAuth

def publish_to_wordpress(site_url, username, password, title, content):
    """Publish article to WordPress"""
    api_url = f"{site_url}/wp-json/wp/v2/posts"
    
    auth = HTTPBasicAuth(username, password)
    
    post_data = {
        'title': title,
        'content': content,
        'status': 'publish',
        'author': 1
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                api_url,
                json=post_data,
                auth=auth,
                timeout=60
            )
            response.raise_for_status()
            
            post = response.json()
            post_id = post.get('id')
            
            app.logger.info(f"Published to WordPress: Post ID {post_id}")
            return post_id
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                app.logger.error("WordPress authentication failed")
                raise  # Don't retry auth errors
            elif attempt < max_retries - 1:
                wait_time = 2 ** attempt
                app.logger.warning(f"WordPress retry {attempt + 1}/{max_retries}: {e}")
                time.sleep(wait_time)
            else:
                app.logger.error(f"WordPress publishing failed: {e}", exc_info=True)
                raise
                
        except Exception as e:
            app.logger.error(f"WordPress error: {e}", exc_info=True)
            raise
    
    return None
```

## Caching Strategy

### Cache Decorator
```python
from functools import lru_cache
from datetime import datetime, timedelta
import json
import os

def timed_cache(hours=24):
    """Cache with time-based invalidation"""
    def decorator(func):
        cache_file = f"cache/{func.__name__}_cache.json"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache directory
            os.makedirs('cache', exist_ok=True)
            
            # Generate cache key
            cache_key = f"{args}_{kwargs}"
            
            # Check cache file
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    if cache_key in cache_data:
                        cached = cache_data[cache_key]
                        cached_time = datetime.fromisoformat(cached['timestamp'])
                        
                        # Check if cache is still valid
                        if datetime.now() - cached_time < timedelta(hours=hours):
                            app.logger.info(f"Using cached data for {func.__name__}")
                            return cached['data']
                except Exception as e:
                    app.logger.warning(f"Cache read error: {e}")
            
            # Call function
            result = func(*args, **kwargs)
            
            # Save to cache
            try:
                cache_data = {}
                if os.path.exists(cache_file):
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                
                cache_data[cache_key] = {
                    'data': result,
                    'timestamp': datetime.now().isoformat()
                }
                
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f)
                    
            except Exception as e:
                app.logger.warning(f"Cache write error: {e}")
            
            return result
        
        return wrapper
    return decorator

# Usage
@timed_cache(hours=1)
def get_stock_fundamentals(ticker):
    """Cached stock fundamentals (1 hour)"""
    return get_alpha_vantage_data('OVERVIEW', ticker)
```

## Error Recovery Patterns

### Fallback Chain
```python
def get_stock_price(ticker):
    """Get stock price with multiple fallbacks"""
    
    # Try yfinance first (fastest, free)
    try:
        stock = yf.Ticker(ticker)
        price = stock.info.get('currentPrice')
        if price:
            return price
    except Exception as e:
        app.logger.warning(f"yfinance failed for {ticker}: {e}")
    
    # Fallback to Alpha Vantage
    try:
        data = get_alpha_vantage_data('GLOBAL_QUOTE', ticker)
        if data and 'Global Quote' in data:
            price = float(data['Global Quote'].get('05. price', 0))
            if price:
                return price
    except Exception as e:
        app.logger.warning(f"Alpha Vantage failed for {ticker}: {e}")
    
    # Fallback to Finnhub
    try:
        quote = finnhub_client.quote(ticker)
        price = quote.get('c')  # Current price
        if price:
            return price
    except Exception as e:
        app.logger.warning(f"Finnhub failed for {ticker}: {e}")
    
    # All sources failed
    app.logger.error(f"Could not get price for {ticker} from any source")
    return None
```

## Testing API Integrations

### Mock External APIs
```python
from unittest.mock import Mock, patch

def test_stock_data_retrieval():
    """Test with mocked yfinance"""
    with patch('yfinance.Ticker') as mock_ticker:
        # Configure mock
        mock_ticker.return_value.info = {
            'currentPrice': 150.0,
            'marketCap': 2500000000000
        }
        mock_ticker.return_value.history.return_value = Mock()
        
        # Call function
        data = get_stock_data('AAPL')
        
        # Verify
        assert data['current_price'] == 150.0
        assert data['ticker'] == 'AAPL'
```

## Deployment Checklist

- [ ] All API keys stored in environment variables
- [ ] Rate limiting implemented for all APIs
- [ ] Retry logic with exponential backoff
- [ ] Error logging for all API calls
- [ ] Fallback strategies for critical data
- [ ] Caching configured to reduce API usage
- [ ] API usage monitoring/tracking
- [ ] Graceful degradation when APIs fail
- [ ] Timeout configured for all requests
- [ ] Tests mock external APIs (don't call real APIs)
