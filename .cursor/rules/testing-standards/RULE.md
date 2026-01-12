---
description: "Testing standards and best practices for TickZen - ensures comprehensive test coverage for production readiness"
alwaysApply: false
globs:
  - "**/*test*.py"
  - "**/testing/**"
  - "**/tests/**"
---

# TickZen Testing Standards

## Overview
All production code MUST have corresponding tests. Follow these standards to ensure reliability, maintainability, and confidence in deployments.

## Testing Pyramid

### Unit Tests (70% of tests)
- Test individual functions and methods in isolation
- Mock external dependencies (Firebase, APIs, SocketIO)
- Fast execution (< 100ms per test)
- Coverage target: 80% for business logic

### Integration Tests (20% of tests)
- Test component interactions
- Use test Firebase project (not production)
- Test API integrations with mocked responses
- Coverage target: Key workflows end-to-end

### End-to-End Tests (10% of tests)
- Test complete user flows
- Use staging environment
- Critical paths only (analysis, automation, publishing)

## Required Tests for Each Module

### For Analysis Pipeline (`automation_scripts/pipeline.py`)
```python
# REQUIRED: Test each pipeline stage
def test_data_collection_stage():
    """Test data collection with mocked API responses"""
    # Mock yfinance, Alpha Vantage, FRED
    # Verify data structure and completeness
    
def test_preprocessing_stage():
    """Test data cleaning and validation"""
    # Test outlier detection
    # Test missing data handling
    # Test split adjustments
    
def test_model_training_stage():
    """Test Prophet model training"""
    # Use cached data to avoid API calls
    # Verify model parameters
    # Test forecast generation
    
def test_report_generation_stage():
    """Test HTML report creation"""
    # Verify all 32 sections present
    # Test template rendering
    # Validate output format
    
def test_error_recovery():
    """Test graceful degradation on failures"""
    # Test API failures
    # Test missing data scenarios
    # Verify user-friendly error messages
```

### For Firebase Operations
```python
# REQUIRED: Mock all Firebase calls
from unittest.mock import Mock, patch

def test_firestore_save_with_mock():
    """Test Firestore operations without hitting real database"""
    with patch('config.firebase_admin_setup.get_firestore_client') as mock_db:
        mock_collection = Mock()
        mock_db.return_value.collection.return_value = mock_collection
        
        # Your test code here
        save_user_profile(user_uid, profile_data)
        
        # Verify method called correctly
        mock_collection.document.assert_called_once_with(user_uid)

def test_firebase_unavailable_handling():
    """Test behavior when Firebase is down"""
    with patch('config.firebase_admin_setup.get_firebase_app_initialized', return_value=False):
        # Verify graceful degradation
        result = save_report_to_firebase_storage(uid, ticker, filename, content)
        assert result is None  # Should return None, not crash
```

### For SocketIO Events
```python
# REQUIRED: Test all SocketIO emissions
def test_analysis_progress_emission():
    """Test progress updates via SocketIO"""
    mock_socketio = Mock()
    user_room = f"user_{user_uid}"
    
    # Trigger analysis
    run_pipeline(ticker, timestamp, app_root, mock_socketio, user_room)
    
    # Verify progress events emitted
    calls = mock_socketio.emit.call_args_list
    assert len(calls) > 0
    
    # Verify event structure
    first_call = calls[0]
    assert first_call[0][0] == 'analysis_progress'
    assert 'progress' in first_call[0][1]
    assert 'ticker' in first_call[0][1]

def test_error_emission():
    """Test error events via SocketIO"""
    # Trigger error condition
    # Verify analysis_error event emitted with proper format
```

### For WordPress Publishing (`automation_scripts/auto_publisher.py`)
```python
# REQUIRED: Test publishing logic
def test_trigger_publishing_run():
    """Test complete publishing workflow"""
    # Mock WordPress API
    # Mock Firebase state manager
    # Test profile processing
    # Verify daily limits enforced
    # Check author rotation
    
def test_daily_limit_enforcement():
    """Test that daily posting limits are respected"""
    # Set profile daily limit to 3
    # Attempt to publish 5 articles
    # Verify only 3 published
    # Verify proper status saved to Firestore
    
def test_author_rotation():
    """Test round-robin author assignment"""
    # Configure 3 authors
    # Publish 6 articles
    # Verify each author used twice
    # Verify state persisted correctly

def test_duplicate_prevention():
    """Test that duplicate content is not published"""
    # Attempt to publish same ticker twice
    # Verify second attempt skipped
    # Check contentHash comparison
```

### For AI Content Generation
```python
# REQUIRED: Test AI integrations
def test_gemini_article_generation():
    """Test Gemini AI content generation"""
    # Mock Gemini API response
    # Test prompt construction
    # Verify output format
    # Test error handling for API failures
    
def test_perplexity_research():
    """Test Perplexity AI research collection"""
    # Mock Perplexity API
    # Test research query construction
    # Verify data extraction
    # Test source validation
```

## Test File Organization

```
tickzen2/
├── tests/
│   ├── unit/
│   │   ├── test_analysis_pipeline.py
│   │   ├── test_technical_analysis.py
│   │   ├── test_fundamental_analysis.py
│   │   ├── test_sentiment_analysis.py
│   │   ├── test_risk_analysis.py
│   │   ├── test_auto_publisher.py
│   │   ├── test_earnings_pipeline.py
│   │   └── test_sports_automation.py
│   ├── integration/
│   │   ├── test_firebase_integration.py
│   │   ├── test_wordpress_integration.py
│   │   ├── test_api_integration.py
│   │   └── test_socketio_integration.py
│   ├── e2e/
│   │   ├── test_stock_analysis_flow.py
│   │   ├── test_automation_flow.py
│   │   └── test_user_authentication.py
│   ├── fixtures/
│   │   ├── sample_stock_data.json
│   │   ├── sample_earnings_data.json
│   │   └── sample_wordpress_response.json
│   └── conftest.py  # Pytest configuration and fixtures
```

## Test Fixtures and Mocks

### Common Fixtures (in `conftest.py`)
```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_firebase():
    """Mock Firebase services"""
    with patch('config.firebase_admin_setup.get_firebase_app_initialized', return_value=True):
        mock_db = Mock()
        mock_storage = Mock()
        yield {'db': mock_db, 'storage': mock_storage}

@pytest.fixture
def sample_stock_data():
    """Load sample stock data for testing"""
    import json
    with open('tests/fixtures/sample_stock_data.json') as f:
        return json.load(f)

@pytest.fixture
def mock_socketio():
    """Mock SocketIO instance"""
    return Mock()

@pytest.fixture
def test_user():
    """Test user data"""
    return {
        'uid': 'test_user_123',
        'email': 'test@example.com',
        'displayName': 'Test User'
    }
```

## Running Tests

### Local Development
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_analysis_pipeline.py

# Run tests matching pattern
pytest -k "test_firebase"

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Continuous Integration
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Test Data Management

### Use Fixtures, Never Production Data
```python
# GOOD: Use fixtures
def test_analysis_with_fixture(sample_stock_data):
    result = analyze_stock(sample_stock_data)
    assert result['status'] == 'completed'

# BAD: Call real APIs or use production data
def test_analysis_live():  # ❌ NEVER DO THIS
    result = analyze_stock('AAPL')  # Calls real APIs!
```

### Mock External Dependencies
```python
# GOOD: Mock all external services
@patch('yfinance.Ticker')
@patch('requests.get')
def test_data_collection(mock_requests, mock_yfinance):
    mock_yfinance.return_value.history.return_value = sample_data
    result = collect_stock_data('AAPL')
    assert result is not None

# BAD: Allow real API calls
def test_data_collection():  # ❌ Hits real APIs
    result = collect_stock_data('AAPL')
```

## Assertion Best Practices

### Be Specific and Meaningful
```python
# GOOD: Specific assertions
def test_technical_analysis():
    result = calculate_rsi(sample_data, period=14)
    assert 0 <= result <= 100, "RSI must be between 0 and 100"
    assert isinstance(result, float), "RSI must be a float"
    assert result == pytest.approx(65.3, abs=0.1), "RSI calculation incorrect"

# BAD: Vague assertions
def test_technical_analysis():  # ❌ Not specific enough
    result = calculate_rsi(sample_data)
    assert result  # What are we testing?
```

## Error Testing

### Test All Error Paths
```python
# REQUIRED: Test error conditions
def test_invalid_ticker():
    """Test handling of invalid ticker symbols"""
    with pytest.raises(ValueError, match="Invalid ticker"):
        analyze_stock("INVALID_TICKER_12345")

def test_api_failure_handling():
    """Test graceful handling of API failures"""
    with patch('yfinance.Ticker', side_effect=Exception("API Down")):
        result = collect_stock_data('AAPL')
        assert result['status'] == 'error'
        assert 'API Down' in result['message']

def test_firebase_connection_loss():
    """Test behavior when Firebase connection is lost mid-operation"""
    # Simulate connection loss
    # Verify state consistency
    # Check retry logic
```

## Performance Testing

### Test Performance Constraints
```python
import time

def test_analysis_performance():
    """Ensure analysis completes within time limit"""
    start = time.time()
    result = run_pipeline('AAPL', timestamp, app_root)
    duration = time.time() - start
    
    assert duration < 60, f"Analysis took {duration}s, should be < 60s"
    assert result['status'] == 'completed'

def test_concurrent_analyses():
    """Test handling of concurrent analysis requests"""
    # Simulate 10 concurrent users
    # Verify no race conditions
    # Check SocketIO room isolation
```

## Coverage Requirements

### Minimum Coverage Thresholds
- **Overall**: 75% code coverage
- **Business Logic**: 85% coverage
- **Critical Paths**: 95% coverage (analysis, publishing, authentication)
- **Error Handling**: 80% coverage

### Coverage Exclusions
```python
# In .coveragerc or pyproject.toml
[tool.coverage.run]
omit = [
    "tests/*",
    "*/migrations/*",
    "*/venv/*",
    "scripts/legacy/*"
]
```

## Pre-Commit Hooks

### Run Tests Before Commit
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

## Documentation in Tests

### Every Test Must Have a Docstring
```python
def test_earnings_data_collection():
    """
    Test earnings data collection from multiple sources.
    
    Verifies:
    - Data collected from yfinance, Alpha Vantage, Finnhub
    - Data normalized to common format
    - Missing data handled gracefully
    - API failures don't crash the pipeline
    
    Mocks:
    - All external API calls
    - Firebase operations
    """
    # Test implementation
```

## Test Naming Convention

### Clear, Descriptive Names
```python
# GOOD: Descriptive test names
def test_save_report_to_firebase_storage_creates_blob_with_correct_path():
    """Test that report is saved to Firebase Storage with user-scoped path"""

def test_trigger_publishing_run_respects_daily_limit_per_profile():
    """Test that daily posting limit is enforced per WordPress profile"""

# BAD: Unclear names
def test_save():  # ❌ What is being saved? Where?
def test_publish():  # ❌ What's being published? How?
```

## When to Write Tests

### Test-Driven Development (Preferred)
1. Write failing test first
2. Implement minimum code to pass
3. Refactor while keeping tests green

### At Minimum
- Write tests BEFORE merging to main
- Write tests for ANY bug fix
- Write tests for ALL new features
- Update tests when changing logic

## Test Execution Strategy

### Local Development
- Run affected tests on every save
- Run full test suite before commit
- Run integration tests before push

### CI/CD Pipeline
- Run all tests on every PR
- Block merge if tests fail
- Track coverage trends over time
- Require coverage increase for new code

## Common Testing Anti-Patterns to Avoid

### ❌ DON'T
- Test implementation details (test behavior, not code)
- Write tests that depend on execution order
- Use real API keys or production credentials
- Skip cleanup after tests
- Write tests that only work on your machine
- Ignore flaky tests (fix them!)
- Test third-party library code

### ✅ DO
- Test public interfaces and contracts
- Make tests independent and isolated
- Mock all external dependencies
- Clean up test data and resources
- Use environment-agnostic test data
- Fix flaky tests immediately
- Focus on your application logic

## Success Criteria

A test suite is production-ready when:
- ✅ All tests pass consistently
- ✅ Coverage meets minimum thresholds
- ✅ Tests run in < 5 minutes
- ✅ No flaky tests (fail randomly)
- ✅ All critical paths covered
- ✅ Error scenarios tested
- ✅ Performance validated
- ✅ Integration points verified
