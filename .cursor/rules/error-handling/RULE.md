---
description: "Error handling patterns and best practices for TickZen - ensures robust error management across all systems"
alwaysApply: true
---

# TickZen Error Handling Standards

## Core Principles

1. **Never fail silently** - Always log errors, even if you handle them gracefully
2. **User-friendly messages** - Never show stack traces or technical errors to users
3. **Graceful degradation** - System should remain functional even if services fail
4. **Comprehensive logging** - Log context, not just error messages
5. **Fast failure** - Fail fast, fail loudly in development; gracefully in production

## Error Handling Hierarchy

### Level 1: Critical Errors (System Down)
**When**: Firebase unavailable, database connection lost, critical service failure
**Action**: Return 503, show maintenance page, alert ops team

```python
@app.errorhandler(503)
def service_unavailable(error):
    app.logger.critical(f"Service unavailable: {error}", exc_info=True)
    # Send alert to ops team
    return render_template('error.html',
        message="System is temporarily unavailable. We're working to restore service.",
        support_email="support@tickzen.app"
    ), 503
```

### Level 2: Feature Errors (Part of System Down)
**When**: Analysis pipeline fails, publishing fails, specific feature broken
**Action**: Disable feature, show fallback UI, log error

```python
try:
    result = run_analysis_pipeline(ticker)
except Exception as e:
    app.logger.error(f"Analysis pipeline failed for {ticker}: {e}", exc_info=True)
    # Emit error to user via SocketIO
    socketio.emit('analysis_error', {
        'ticker': ticker,
        'message': 'Unable to complete analysis at this time. Please try again later.',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room=user_room)
    # Return partial results if available
    return {'status': 'error', 'partial_data': cached_data}
```

### Level 3: User Errors (Invalid Input)
**When**: Invalid ticker, malformed data, user mistake
**Action**: Show helpful error message, guide user to correct input

```python
def analyze_stock(ticker):
    # Validate input
    if not ticker or len(ticker) > 5:
        raise ValueError(f"Invalid ticker symbol: {ticker}")
    
    if not ticker.isalpha():
        raise ValueError("Ticker must contain only letters")
    
    # Check if ticker exists
    if not is_valid_ticker(ticker):
        raise ValueError(f"Ticker '{ticker}' not found. Please verify the symbol.")
```

### Level 4: Expected Failures (No Data, Rate Limits)
**When**: API rate limited, no data available, service temporarily unavailable
**Action**: Use cached data, retry with backoff, inform user of limitation

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_stock_data(ticker):
    """Fetch with automatic retry on transient failures"""
    try:
        data = yf.Ticker(ticker).history(period='1y')
        if data.empty:
            # Expected failure - no data
            app.logger.warning(f"No data available for {ticker}")
            return None
        return data
    except requests.exceptions.RequestException as e:
        # Transient failure - will retry
        app.logger.info(f"Retry {ticker} data fetch: {e}")
        raise
    except Exception as e:
        # Unexpected error - don't retry
        app.logger.error(f"Unexpected error fetching {ticker}: {e}", exc_info=True)
        return None
```

## Firebase Error Handling

### ALWAYS Check Firebase Availability First
```python
# REQUIRED pattern for ALL Firebase operations
if not get_firebase_app_initialized():
    log_firebase_operation_error(
        operation="save_report",
        error="Firebase not initialized",
        context={'user_uid': user_uid, 'ticker': ticker}
    )
    # Fallback to local storage
    save_report_locally(user_uid, ticker, content)
    return None

# Then proceed with Firebase operation
try:
    db = get_firestore_client()
    doc_ref = db.collection('userReports').document(report_id)
    doc_ref.set(report_data)
    return report_id
except Exception as e:
    log_firebase_operation_error(
        operation="firestore_save",
        error=str(e),
        context={'user_uid': user_uid, 'report_id': report_id}
    )
    # Fallback
    save_report_locally(user_uid, ticker, content)
    return None
```

### Firestore Query Error Handling
```python
def get_user_reports(user_uid):
    """Get user reports with comprehensive error handling"""
    if not get_firebase_app_initialized():
        return []  # Return empty list, don't crash
    
    try:
        db = get_firestore_client()
        docs = db.collection('userGeneratedReports') \
                .where('user_uid', '==', user_uid) \
                .order_by('created_at', direction='DESCENDING') \
                .limit(50) \
                .stream()
        
        reports = []
        for doc in docs:
            try:
                data = doc.to_dict()
                reports.append(data)
            except Exception as doc_error:
                # Log but continue processing other docs
                app.logger.warning(f"Failed to parse report {doc.id}: {doc_error}")
                continue
        
        return reports
        
    except Exception as e:
        app.logger.error(f"Failed to get reports for {user_uid}: {e}", exc_info=True)
        log_firebase_operation_error("get_user_reports", str(e), {'user_uid': user_uid})
        return []  # Return empty list to allow UI to render
```

### Firebase Storage Error Handling
```python
def save_report_to_firebase_storage(user_uid, ticker, filename, content):
    """Save report with fallback to local storage"""
    if not get_firebase_app_initialized():
        return save_report_locally(user_uid, ticker, filename, content)
    
    try:
        bucket = get_storage_bucket()
        blob_path = f"user_reports/{user_uid}/{filename}"
        blob = bucket.blob(blob_path)
        
        # Upload with retry
        blob.upload_from_string(
            content,
            content_type='text/html',
            timeout=60,
            retry=google.api_core.retry.Retry(
                initial=1.0,
                maximum=10.0,
                multiplier=2.0,
                deadline=60.0
            )
        )
        
        return blob_path
        
    except google.api_core.exceptions.GoogleAPIError as e:
        app.logger.error(f"Firebase Storage API error: {e}", exc_info=True)
        log_firebase_operation_error("storage_upload", str(e), 
                                    {'user_uid': user_uid, 'filename': filename})
        # Fallback
        return save_report_locally(user_uid, ticker, filename, content)
        
    except Exception as e:
        app.logger.error(f"Unexpected storage error: {e}", exc_info=True)
        return save_report_locally(user_uid, ticker, filename, content)
```

## SocketIO Error Handling

### Always Wrap SocketIO Handlers in Try-Except
```python
@socketio.on('analysis_request')
def handle_analysis_request(data):
    """Handle analysis request with comprehensive error handling"""
    user_room = None
    ticker = None
    
    try:
        # Extract and validate data
        ticker = data.get('ticker', '').upper().strip()
        if not ticker:
            raise ValueError("Ticker symbol is required")
        
        user_uid = session.get('firebase_user_uid')
        if not user_uid:
            raise ValueError("User not authenticated")
        
        user_room = f"user_{user_uid}"
        join_room(user_room)
        
        # Emit start event
        emit('analysis_progress', {
            'progress': 0,
            'message': f'Starting analysis for {ticker}...',
            'ticker': ticker,
            'stage': 'Initialization'
        }, room=user_room)
        
        # Run pipeline
        model, forecast, report_path, html = run_pipeline(
            ticker, 
            str(time.time()), 
            app.root_path, 
            socketio, 
            user_room
        )
        
        # Emit completion
        emit('ticker_status_persisted', {
            'ticker': ticker,
            'status': 'completed',
            'report_path': report_path
        }, room=user_room)
        
    except ValueError as ve:
        # User input error
        app.logger.warning(f"Invalid analysis request: {ve}")
        if user_room:
            emit('analysis_error', {
                'ticker': ticker,
                'message': str(ve),
                'type': 'validation_error'
            }, room=user_room)
            
    except Exception as e:
        # System error
        app.logger.error(f"Analysis failed for {ticker}: {e}", exc_info=True)
        if user_room:
            emit('analysis_error', {
                'ticker': ticker,
                'message': 'Analysis failed due to an unexpected error. Please try again.',
                'type': 'system_error'
            }, room=user_room)
```

### SocketIO Connection Error Handling
```python
@socketio.on_error_default
def default_error_handler(e):
    """Handle all uncaught SocketIO errors"""
    app.logger.error(f"SocketIO error: {e}", exc_info=True)
    return {'error': 'An unexpected error occurred'}

@socketio.on('connect')
def handle_connect():
    """Handle connection with error handling"""
    try:
        user_uid = session.get('firebase_user_uid')
        if not user_uid:
            app.logger.warning("Unauthenticated SocketIO connection attempt")
            return False  # Reject connection
        
        user_room = f"user_{user_uid}"
        join_room(user_room)
        app.logger.info(f"User {user_uid} connected to SocketIO")
        
    except Exception as e:
        app.logger.error(f"Connection error: {e}", exc_info=True)
        return False

@socketio.on('disconnect')
def handle_disconnect():
    """Clean disconnect with error handling"""
    try:
        user_uid = session.get('firebase_user_uid')
        if user_uid:
            user_room = f"user_{user_uid}"
            leave_room(user_room)
            app.logger.info(f"User {user_uid} disconnected from SocketIO")
    except Exception as e:
        app.logger.error(f"Disconnect error: {e}", exc_info=True)
```

## API Integration Error Handling

### External API Calls (yfinance, Alpha Vantage, etc.)
```python
from requests.exceptions import RequestException, Timeout, ConnectionError

def fetch_with_error_handling(api_name, fetch_function, *args, **kwargs):
    """Generic API fetch with standardized error handling"""
    try:
        result = fetch_function(*args, **kwargs)
        if result is None or (hasattr(result, 'empty') and result.empty):
            app.logger.warning(f"{api_name} returned no data")
            return None
        return result
        
    except Timeout as e:
        app.logger.warning(f"{api_name} timeout: {e}")
        return None
        
    except ConnectionError as e:
        app.logger.error(f"{api_name} connection failed: {e}")
        return None
        
    except RequestException as e:
        app.logger.error(f"{api_name} request failed: {e}", exc_info=True)
        return None
        
    except Exception as e:
        app.logger.error(f"{api_name} unexpected error: {e}", exc_info=True)
        return None

# Usage
stock_data = fetch_with_error_handling(
    "yfinance", 
    lambda: yf.Ticker(ticker).history(period='1y')
)

earnings_data = fetch_with_error_handling(
    "AlphaVantage",
    lambda: av_client.get_earnings(ticker)
)
```

### Rate Limit Handling
```python
import time
from datetime import datetime, timedelta

class RateLimiter:
    """Simple rate limiter with error handling"""
    def __init__(self, max_calls, period_seconds):
        self.max_calls = max_calls
        self.period = timedelta(seconds=period_seconds)
        self.calls = []
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            now = datetime.now()
            # Remove old calls
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < self.period]
            
            if len(self.calls) >= self.max_calls:
                wait_time = (self.calls[0] + self.period - now).total_seconds()
                app.logger.warning(f"Rate limit reached, waiting {wait_time}s")
                time.sleep(wait_time)
                self.calls = []
            
            self.calls.append(now)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                app.logger.error(f"Rate-limited function error: {e}", exc_info=True)
                raise
        
        return wrapper

# Usage
@RateLimiter(max_calls=5, period_seconds=60)
def fetch_alpha_vantage_data(ticker):
    return av_client.get_data(ticker)
```

## WordPress Publishing Error Handling

### WordPress API Errors
```python
def publish_to_wordpress(profile, article_data):
    """Publish with comprehensive error handling"""
    try:
        # Validate profile
        if not profile.get('site_url') or not profile.get('username'):
            raise ValueError(f"Invalid profile configuration: {profile.get('profile_id')}")
        
        # Create WordPress client
        wp = WordPressClient(
            url=profile['site_url'],
            username=profile['username'],
            password=profile['password']
        )
        
        # Test connection first
        if not wp.test_connection():
            raise ConnectionError(f"Cannot connect to {profile['site_url']}")
        
        # Create post
        post_id = wp.create_post(
            title=article_data['title'],
            content=article_data['content'],
            status='publish',
            featured_media=article_data.get('featured_image_id')
        )
        
        app.logger.info(f"Published to WordPress: post_id={post_id}, site={profile['site_url']}")
        return {
            'status': 'success',
            'post_id': post_id,
            'post_url': f"{profile['site_url']}/?p={post_id}"
        }
        
    except ValueError as ve:
        # Configuration error
        app.logger.error(f"WordPress config error: {ve}")
        return {'status': 'error', 'message': str(ve), 'type': 'config_error'}
        
    except ConnectionError as ce:
        # Network/auth error
        app.logger.error(f"WordPress connection error: {ce}")
        return {'status': 'error', 'message': 'Cannot connect to WordPress site', 'type': 'connection_error'}
        
    except requests.exceptions.HTTPError as he:
        # WordPress API error
        status_code = he.response.status_code
        if status_code == 401:
            msg = "Authentication failed - check username/password"
        elif status_code == 403:
            msg = "Permission denied - check user role"
        elif status_code == 404:
            msg = "WordPress REST API not found - enable it in WordPress"
        else:
            msg = f"WordPress API error: {status_code}"
        
        app.logger.error(f"WordPress HTTP error {status_code}: {he}")
        return {'status': 'error', 'message': msg, 'type': 'api_error'}
        
    except Exception as e:
        # Unexpected error
        app.logger.error(f"Unexpected WordPress error: {e}", exc_info=True)
        return {'status': 'error', 'message': 'Unexpected publishing error', 'type': 'system_error'}
```

## Logging Best Practices

### Structured Logging
```python
import json
from datetime import datetime, timezone

def log_structured(level, event, **context):
    """Structured logging for better analysis"""
    log_entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'level': level,
        'event': event,
        **context
    }
    
    log_message = json.dumps(log_entry)
    
    if level == 'error':
        app.logger.error(log_message)
    elif level == 'warning':
        app.logger.warning(log_message)
    elif level == 'info':
        app.logger.info(log_message)
    else:
        app.logger.debug(log_message)

# Usage
log_structured('info', 'analysis_started',
    ticker='AAPL',
    user_uid='user123',
    timestamp_id='1234567890'
)

log_structured('error', 'publishing_failed',
    ticker='AAPL',
    profile_id='profile456',
    error_type='connection_error',
    site_url='https://example.com'
)
```

### Context Managers for Error Handling
```python
from contextlib import contextmanager

@contextmanager
def error_context(operation, **context):
    """Context manager for consistent error handling"""
    try:
        log_structured('info', f'{operation}_started', **context)
        yield
        log_structured('info', f'{operation}_completed', **context)
    except Exception as e:
        log_structured('error', f'{operation}_failed',
            error=str(e),
            error_type=type(e).__name__,
            **context
        )
        raise

# Usage
with error_context('analysis', ticker='AAPL', user_uid='user123'):
    result = run_analysis_pipeline('AAPL')
```

## User-Facing Error Messages

### Error Message Guidelines
✅ **DO**: "Unable to analyze AAPL. The data provider is temporarily unavailable. Please try again in a few minutes."

❌ **DON'T**: "KeyError: 'Close' at line 245 in technical_analysis.py"

### Error Message Templates
```python
ERROR_MESSAGES = {
    'invalid_ticker': "The ticker symbol '{ticker}' is not valid. Please check the spelling and try again.",
    'no_data': "We couldn't find any data for {ticker}. This stock may be delisted or the symbol may be incorrect.",
    'api_error': "We're experiencing technical difficulties. Please try again in a few moments.",
    'rate_limit': "You've reached the maximum number of analyses per hour. Please try again later.",
    'firebase_error': "We're having trouble saving your data. Your analysis was completed, but we couldn't save it to your account.",
    'publishing_limit': "You've reached your daily publishing limit of {limit} posts. Try again tomorrow.",
    'wordpress_auth': "Cannot connect to your WordPress site. Please check your username and password in profile settings.",
}

def get_user_friendly_error(error_key, **kwargs):
    """Get formatted user-friendly error message"""
    template = ERROR_MESSAGES.get(error_key, "An unexpected error occurred. Please try again.")
    return template.format(**kwargs)
```

## Error Recovery Strategies

### Automatic Retry with Exponential Backoff
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((ConnectionError, Timeout)),
    reraise=True
)
def fetch_with_retry(url):
    """Fetch with automatic retry on transient failures"""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
```

### Circuit Breaker Pattern
```python
from datetime import datetime, timedelta

class CircuitBreaker:
    """Prevent cascading failures by stopping calls to failing services"""
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout)
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
    
    def call(self, func, *args, **kwargs):
        if self.state == 'open':
            if datetime.now() - self.last_failure_time > self.timeout:
                self.state = 'half-open'
            else:
                raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'half-open':
                self.state = 'closed'
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()
            
            if self.failures >= self.failure_threshold:
                self.state = 'open'
                app.logger.error(f"Circuit breaker OPENED for {func.__name__}")
            
            raise

# Usage
alpha_vantage_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

def fetch_alpha_vantage_safe(ticker):
    try:
        return alpha_vantage_breaker.call(fetch_alpha_vantage_data, ticker)
    except Exception as e:
        app.logger.warning(f"Circuit breaker prevented call or call failed: {e}")
        return None
```

## Testing Error Handling

### Test All Error Paths
```python
def test_invalid_ticker_error():
    """Test that invalid tickers raise proper errors"""
    with pytest.raises(ValueError, match="Invalid ticker"):
        analyze_stock("INVALID_TICKER_12345")

def test_firebase_unavailable_graceful_degradation():
    """Test graceful degradation when Firebase is down"""
    with patch('config.firebase_admin_setup.get_firebase_app_initialized', return_value=False):
        result = save_report_to_firebase_storage(uid, ticker, filename, content)
        # Should not crash, should return None
        assert result is None

def test_api_timeout_handling():
    """Test handling of API timeouts"""
    with patch('yfinance.Ticker', side_effect=Timeout("Connection timeout")):
        result = fetch_stock_data('AAPL')
        assert result is None  # Should return None, not crash
```

## Production Error Monitoring

### Set up Error Tracking
```python
# Use Sentry or similar for production error tracking
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

if app.config['ENV'] == 'production':
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,  # 10% of transactions
        environment='production'
    )
```

## Error Handling Checklist

Before deploying code, ensure:
- [ ] All external API calls wrapped in try-except
- [ ] Firebase operations check availability first
- [ ] SocketIO handlers have error handling
- [ ] User-facing errors are friendly and actionable
- [ ] All errors logged with context
- [ ] Critical errors trigger alerts
- [ ] Graceful degradation implemented
- [ ] Error recovery strategies in place
- [ ] All error paths tested
- [ ] Error monitoring configured
