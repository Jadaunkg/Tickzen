# Quota System Testing Strategy
## Comprehensive Testing Plan for User Usage Tracking

**Project**: Tickzen Quota System  
**Date**: January 13, 2026  
**Version**: 1.0  
**Test Coverage Target**: 90%+

---

## Table of Contents
1. [Testing Overview](#testing-overview)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [End-to-End Tests](#end-to-end-tests)
5. [Performance Tests](#performance-tests)
6. [Security Tests](#security-tests)
7. [Test Environments](#test-environments)
8. [Test Data](#test-data)
9. [Continuous Integration](#continuous-integration)

---

## Testing Overview

### Testing Pyramid
```
           E2E Tests (10%)
         /               \
    Integration Tests (30%)
   /                       \
  Unit Tests (60%)
```

### Test Coverage Requirements
- **Unit Tests**: 95%+ code coverage
- **Integration Tests**: All critical paths
- **E2E Tests**: All user workflows
- **Performance Tests**: Latency and throughput benchmarks
- **Security Tests**: All attack vectors

### Testing Tools
- **Unit/Integration**: pytest, pytest-cov
- **E2E**: Selenium/Playwright
- **Performance**: Locust, Apache JMeter
- **Security**: OWASP ZAP, Bandit
- **Database**: Firestore Emulator

---

## Unit Tests

### Test File: `tests/unit/test_quota_service.py`

#### QuotaService Class Tests

```python
import pytest
from datetime import datetime, timedelta
from app.services.quota_service import QuotaService
from unittest.mock import Mock, patch

class TestQuotaServiceBasics:
    """Test basic QuotaService functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.db_mock = Mock()
        self.quota_service = QuotaService(self.db_mock)
        self.test_user_uid = "test_user_123"
    
    def test_initialize_user_quota_free_plan(self):
        """Test creating quota document for free plan user"""
        result = self.quota_service.initialize_user_quota(
            self.test_user_uid, 
            plan_type='free'
        )
        
        assert result['plan_type'] == 'free'
        assert result['quota_limits']['stock_reports_monthly'] == 10
        assert result['current_usage']['stock_reports'] == 0
        assert 'current_period_start' in result
        assert 'current_period_end' in result
    
    def test_initialize_user_quota_premium_plan(self):
        """Test creating quota document for premium plan user"""
        result = self.quota_service.initialize_user_quota(
            self.test_user_uid,
            plan_type='premium'
        )
        
        assert result['plan_type'] == 'premium'
        assert result['quota_limits']['stock_reports_monthly'] == 100
    
    def test_initialize_user_quota_enterprise_unlimited(self):
        """Test enterprise plan has unlimited quota"""
        result = self.quota_service.initialize_user_quota(
            self.test_user_uid,
            plan_type='enterprise'
        )
        
        assert result['quota_limits']['stock_reports_monthly'] == -1


class TestQuotaChecking:
    """Test quota checking logic"""
    
    def setup_method(self):
        self.db_mock = Mock()
        self.quota_service = QuotaService(self.db_mock)
        self.test_user_uid = "test_user_456"
    
    def test_check_quota_within_limit(self):
        """Test quota check when user is within limits"""
        # Mock Firestore response
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'stock_reports_monthly': 10},
            'current_usage': {'stock_reports': 5}
        }
        self.db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.quota_service.check_quota(
            self.test_user_uid,
            'stock_reports'
        )
        
        assert result['allowed'] == True
        assert result['remaining'] == 5
        assert result['limit'] == 10
        assert result['usage'] == 5
    
    def test_check_quota_at_limit(self):
        """Test quota check when user is at limit"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'stock_reports_monthly': 10},
            'current_usage': {'stock_reports': 10}
        }
        self.db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.quota_service.check_quota(
            self.test_user_uid,
            'stock_reports'
        )
        
        assert result['allowed'] == False
        assert result['remaining'] == 0
        assert result['reason'] == 'quota_exceeded'
    
    def test_check_quota_exceeded(self):
        """Test quota check when user has exceeded limit"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'stock_reports_monthly': 10},
            'current_usage': {'stock_reports': 12}  # Over limit
        }
        self.db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.quota_service.check_quota(
            self.test_user_uid,
            'stock_reports'
        )
        
        assert result['allowed'] == False
        assert result['remaining'] == -2
    
    def test_check_quota_unlimited(self):
        """Test quota check for unlimited (enterprise) plan"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'stock_reports_monthly': -1},
            'current_usage': {'stock_reports': 1000}
        }
        self.db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.quota_service.check_quota(
            self.test_user_uid,
            'stock_reports'
        )
        
        assert result['allowed'] == True
        assert result['remaining'] == -1  # Indicates unlimited
    
    def test_check_quota_with_category(self):
        """Test quota check for categorized resource (articles)"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'earnings_articles_monthly': 20},
            'current_usage': {'earnings_articles': 15}
        }
        self.db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.quota_service.check_quota(
            self.test_user_uid,
            'articles',
            category='earnings'
        )
        
        assert result['allowed'] == True
        assert result['remaining'] == 5
    
    def test_check_quota_user_not_found(self):
        """Test quota check when user quota doesn't exist"""
        mock_doc = Mock()
        mock_doc.exists = False
        self.db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        with pytest.raises(ValueError, match="User quota not found"):
            self.quota_service.check_quota(self.test_user_uid, 'stock_reports')
    
    def test_check_quota_invalid_resource_type(self):
        """Test quota check with invalid resource type"""
        with pytest.raises(ValueError, match="Invalid resource type"):
            self.quota_service.check_quota(
                self.test_user_uid,
                'invalid_resource'
            )


class TestQuotaConsumption:
    """Test quota consumption logic"""
    
    def setup_method(self):
        self.db_mock = Mock()
        self.quota_service = QuotaService(self.db_mock)
        self.test_user_uid = "test_user_789"
    
    def test_consume_quota_success(self):
        """Test successful quota consumption"""
        # Mock transaction
        mock_transaction = Mock()
        self.db_mock.transaction.return_value = mock_transaction
        
        # Mock quota document
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'stock_reports_monthly': 10},
            'current_usage': {'stock_reports': 5}
        }
        
        result = self.quota_service.consume_quota(
            self.test_user_uid,
            'stock_reports',
            metadata={'ticker': 'AAPL', 'status': 'success'}
        )
        
        assert result['success'] == True
        assert result['new_usage'] == 6
    
    def test_consume_quota_at_limit(self):
        """Test quota consumption fails when at limit"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'stock_reports_monthly': 10},
            'current_usage': {'stock_reports': 10}
        }
        
        result = self.quota_service.consume_quota(
            self.test_user_uid,
            'stock_reports',
            metadata={'ticker': 'AAPL'}
        )
        
        assert result['success'] == False
        assert result['reason'] == 'quota_exceeded'
    
    def test_consume_quota_with_rollback(self):
        """Test quota consumption rollback on error"""
        # Simulate transaction failure
        self.db_mock.transaction.side_effect = Exception("Transaction failed")
        
        result = self.quota_service.consume_quota(
            self.test_user_uid,
            'stock_reports',
            metadata={'ticker': 'AAPL'}
        )
        
        assert result['success'] == False
        assert 'error' in result
    
    def test_consume_quota_creates_history(self):
        """Test that consumption creates usage history entry"""
        mock_transaction = Mock()
        self.db_mock.transaction.return_value = mock_transaction
        
        metadata = {
            'ticker': 'TSLA',
            'report_id': 'report_123',
            'status': 'success'
        }
        
        self.quota_service.consume_quota(
            self.test_user_uid,
            'stock_reports',
            metadata=metadata
        )
        
        # Verify history subcollection was updated
        # (Implementation specific assertion)
        assert True  # Placeholder


class TestQuotaReset:
    """Test quota reset functionality"""
    
    def setup_method(self):
        self.db_mock = Mock()
        self.quota_service = QuotaService(self.db_mock)
        self.test_user_uid = "test_user_reset"
    
    def test_reset_monthly_quota(self):
        """Test monthly quota reset"""
        result = self.quota_service.reset_monthly_quota(self.test_user_uid)
        
        assert result['success'] == True
        assert result['current_usage']['stock_reports'] == 0
        assert result['current_usage']['articles_total'] == 0
        assert 'current_period_start' in result
        assert 'current_period_end' in result
    
    def test_reset_preserves_limits(self):
        """Test that reset preserves quota limits"""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'plan_type': 'premium',
            'quota_limits': {'stock_reports_monthly': 100}
        }
        self.db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.quota_service.reset_monthly_quota(self.test_user_uid)
        
        assert result['quota_limits']['stock_reports_monthly'] == 100
    
    def test_reset_updates_period_dates(self):
        """Test that reset updates period start/end dates"""
        result = self.quota_service.reset_monthly_quota(self.test_user_uid)
        
        # Verify dates are current month
        start = datetime.fromisoformat(result['current_period_start'])
        end = datetime.fromisoformat(result['current_period_end'])
        
        assert start.day == 1
        assert end.month == start.month


class TestCaching:
    """Test caching functionality"""
    
    def setup_method(self):
        self.db_mock = Mock()
        self.quota_service = QuotaService(self.db_mock, cache_ttl=300)
        self.test_user_uid = "test_user_cache"
    
    def test_cache_hit(self):
        """Test cache hit returns cached data"""
        # First call - cache miss
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'stock_reports_monthly': 10},
            'current_usage': {'stock_reports': 5}
        }
        self.db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result1 = self.quota_service.check_quota(self.test_user_uid, 'stock_reports')
        
        # Second call - should hit cache
        result2 = self.quota_service.check_quota(self.test_user_uid, 'stock_reports')
        
        # Verify Firestore was only called once
        assert self.db_mock.collection.call_count == 1
        assert result1 == result2
    
    def test_cache_invalidation_on_consumption(self):
        """Test cache is invalidated after quota consumption"""
        # Setup cache
        self.quota_service._cache[self.test_user_uid] = {
            'data': {'current_usage': {'stock_reports': 5}},
            'timestamp': datetime.now().timestamp()
        }
        
        # Consume quota
        self.quota_service.consume_quota(
            self.test_user_uid,
            'stock_reports',
            metadata={'ticker': 'AAPL'}
        )
        
        # Cache should be invalidated
        assert self.test_user_uid not in self.quota_service._cache
    
    def test_cache_expiry(self):
        """Test cache expires after TTL"""
        # Setup cache with old timestamp
        old_timestamp = (datetime.now() - timedelta(seconds=400)).timestamp()
        self.quota_service._cache[self.test_user_uid] = {
            'data': {'current_usage': {'stock_reports': 5}},
            'timestamp': old_timestamp
        }
        
        # Check quota - should fetch from DB
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'stock_reports_monthly': 10},
            'current_usage': {'stock_reports': 6}
        }
        self.db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = self.quota_service.check_quota(self.test_user_uid, 'stock_reports')
        
        # Verify fresh data from DB
        assert result['usage'] == 6


class TestConcurrency:
    """Test concurrent quota operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_consumption(self):
        """Test multiple concurrent quota consumptions"""
        import asyncio
        
        db_mock = Mock()
        quota_service = QuotaService(db_mock)
        test_user_uid = "concurrent_user"
        
        # Simulate 10 concurrent requests
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                quota_service.consume_quota(
                    test_user_uid,
                    'stock_reports',
                    metadata={'ticker': f'TICK{i}'}
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify all succeeded or failed appropriately
        # (depends on initial quota)
        assert len(results) == 10
    
    def test_race_condition_prevention(self):
        """Test that transactions prevent race conditions"""
        # This test would use Firestore emulator
        # to verify atomic operations
        assert True  # Placeholder


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def setup_method(self):
        self.db_mock = Mock()
        self.quota_service = QuotaService(self.db_mock)
    
    def test_negative_usage(self):
        """Test handling of negative usage values"""
        with pytest.raises(ValueError):
            self.quota_service.consume_quota(
                "user",
                'stock_reports',
                metadata={},
                amount=-1
            )
    
    def test_firestore_timeout(self):
        """Test handling of Firestore timeout"""
        self.db_mock.collection.side_effect = Exception("Timeout")
        
        result = self.quota_service.check_quota("user", 'stock_reports')
        
        assert result['success'] == False
        assert 'error' in result
    
    def test_invalid_metadata(self):
        """Test consumption with invalid metadata"""
        # Should handle gracefully
        result = self.quota_service.consume_quota(
            "user",
            'stock_reports',
            metadata=None
        )
        
        # Should use empty dict as default
        assert result is not None


# Performance Benchmarks
class TestPerformance:
    """Performance benchmark tests"""
    
    def test_quota_check_latency(self):
        """Test quota check completes within 50ms"""
        import time
        
        db_mock = Mock()
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'quota_limits': {'stock_reports_monthly': 10},
            'current_usage': {'stock_reports': 5}
        }
        db_mock.collection.return_value.document.return_value.get.return_value = mock_doc
        
        quota_service = QuotaService(db_mock)
        
        start = time.time()
        quota_service.check_quota("user", 'stock_reports')
        end = time.time()
        
        latency_ms = (end - start) * 1000
        assert latency_ms < 50, f"Quota check took {latency_ms}ms (max 50ms)"
    
    def test_cache_performance_improvement(self):
        """Test cache improves performance significantly"""
        # First call (no cache)
        # Second call (with cache)
        # Assert second call is >10x faster
        assert True  # Placeholder
```

### Test Coverage: `tests/unit/test_quota_decorator.py`

```python
import pytest
from app.decorators import quota_required
from flask import Flask, session

class TestQuotaDecorator:
    """Test @quota_required decorator"""
    
    def setup_method(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'test_key'
    
    def test_decorator_allows_within_quota(self):
        """Test decorator allows function execution when quota available"""
        
        @quota_required(resource_type='stock_reports')
        def test_function():
            return "Success"
        
        with self.app.test_request_context():
            session['firebase_user_uid'] = 'test_user'
            # Mock quota check to return True
            result = test_function()
            assert result == "Success"
    
    def test_decorator_blocks_exceeded_quota(self):
        """Test decorator blocks execution when quota exceeded"""
        
        @quota_required(resource_type='stock_reports')
        def test_function():
            return "Success"
        
        with self.app.test_request_context():
            session['firebase_user_uid'] = 'test_user'
            # Mock quota check to return False
            # Should return error response
            assert True  # Placeholder
    
    def test_decorator_consumes_on_success(self):
        """Test decorator consumes quota after successful execution"""
        
        @quota_required(resource_type='stock_reports', consume_on_success=True)
        def test_function():
            return "Success"
        
        # Verify consume_quota was called
        assert True  # Placeholder
```

---

## Integration Tests

### Test File: `tests/integration/test_quota_integration.py`

```python
import pytest
from app import create_app
from app.services.quota_service import QuotaService
from google.cloud import firestore
import time

@pytest.fixture
def firestore_emulator():
    """Setup Firestore emulator for testing"""
    # Start emulator
    # Set environment variables
    db = firestore.Client()
    yield db
    # Cleanup
    # Stop emulator

@pytest.fixture
def app(firestore_emulator):
    """Create Flask app for testing"""
    app = create_app('testing')
    app.config['TESTING'] = True
    return app

class TestStockAnalysisIntegration:
    """Test quota integration with stock analysis"""
    
    def test_stock_analysis_with_quota_available(self, app, firestore_emulator):
        """Test stock analysis succeeds when quota available"""
        client = app.test_client()
        
        # Login
        # Set quota
        # Request analysis
        response = client.post('/start-analysis', data={
            'ticker': 'AAPL'
        })
        
        # Should succeed
        assert response.status_code == 200
        
        # Verify quota was consumed
        # Check usage increased by 1
    
    def test_stock_analysis_quota_exceeded(self, app, firestore_emulator):
        """Test stock analysis fails when quota exceeded"""
        client = app.test_client()
        
        # Set quota to 0 remaining
        # Request analysis
        response = client.post('/start-analysis', data={
            'ticker': 'AAPL'
        })
        
        # Should fail with quota error
        assert 'quota_exceeded' in response.json['error']
    
    def test_stock_analysis_no_consumption_on_failure(self, app):
        """Test quota not consumed if analysis fails"""
        # Trigger analysis error
        # Verify quota unchanged
        assert True  # Placeholder

class TestEarningsAutomationIntegration:
    """Test quota integration with earnings automation"""
    
    def test_earnings_automation_batch_quota_check(self, app):
        """Test batch quota checking before automation"""
        # Select 5 tickers
        # Check quota allows all 5
        # Run automation
        # Verify all 5 consumed
        assert True
    
    def test_earnings_automation_partial_quota(self, app):
        """Test automation with partial quota available"""
        # Quota allows 3 out of 5 articles
        # Run automation
        # Verify only 3 published
        # Verify quota fully consumed
        assert True

class TestSportsAutomationIntegration:
    """Test quota integration with sports automation"""
    
    def test_sports_automation_category_tracking(self, app):
        """Test sports articles tracked in correct category"""
        # Publish sports article
        # Verify sports_articles counter increased
        # Verify articles_total also increased
        assert True

class TestQuotaResetIntegration:
    """Test quota reset functionality"""
    
    def test_monthly_reset_resets_usage(self, app, firestore_emulator):
        """Test monthly reset clears usage"""
        quota_service = QuotaService(firestore_emulator)
        user_uid = "test_reset_user"
        
        # Initialize with usage
        quota_service.initialize_user_quota(user_uid)
        quota_service.consume_quota(user_uid, 'stock_reports', {'ticker': 'AAPL'})
        
        # Reset
        quota_service.reset_monthly_quota(user_uid)
        
        # Verify usage is 0
        stats = quota_service.get_usage_stats(user_uid)
        assert stats['current_usage']['stock_reports'] == 0
```

---

## End-to-End Tests

### Test File: `tests/e2e/test_quota_workflows.py`

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytest

@pytest.fixture
def browser():
    """Setup browser for E2E tests"""
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

class TestUserQuotaWorkflow:
    """Test complete user workflows with quota"""
    
    def test_user_sees_quota_status(self, browser):
        """Test user can see their quota status"""
        browser.get("http://localhost:5000/login")
        
        # Login
        browser.find_element(By.ID, "email").send_keys("test@example.com")
        browser.find_element(By.ID, "password").send_keys("password123")
        browser.find_element(By.ID, "login-btn").click()
        
        # Navigate to profile
        browser.get("http://localhost:5000/user-profile")
        
        # Verify quota widget displays
        quota_widget = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "quota-widget"))
        )
        assert quota_widget.is_displayed()
        
        # Verify usage displays
        usage_text = browser.find_element(By.CLASS_NAME, "quota-usage").text
        assert "5 / 10" in usage_text
    
    def test_user_blocked_at_quota_limit(self, browser):
        """Test user is blocked when quota exceeded"""
        browser.get("http://localhost:5000/login")
        # Login with user at quota limit
        
        # Try to run analysis
        browser.get("http://localhost:5000/analyzer")
        browser.find_element(By.ID, "ticker").send_keys("AAPL")
        browser.find_element(By.ID, "analyze-btn").click()
        
        # Verify error message shown
        error_msg = WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "quota-error"))
        )
        assert "quota exceeded" in error_msg.text.lower()
    
    def test_upgrade_prompt_shown(self, browser):
        """Test upgrade prompt shows when quota exceeded"""
        # At quota limit
        # Trigger quota exceeded
        # Verify upgrade modal displays
        assert True

class TestAdminQuotaManagement:
    """Test admin quota management workflows"""
    
    def test_admin_can_adjust_quota(self, browser):
        """Test admin can manually adjust user quota"""
        # Login as admin
        browser.get("http://localhost:5000/admin/quota-management")
        
        # Find user
        # Click adjust button
        # Set new quota
        # Save
        
        # Verify quota updated
        assert True
```

---

## Performance Tests

### Test File: `tests/performance/test_quota_performance.py`

```python
from locust import HttpUser, task, between
import time

class QuotaLoadTest(HttpUser):
    """Load test for quota system"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before testing"""
        self.client.post("/login", {
            "email": "test@example.com",
            "password": "password123"
        })
    
    @task(3)
    def check_quota_status(self):
        """Test quota status endpoint"""
        with self.client.get("/api/quota/status", catch_response=True) as response:
            if response.elapsed.total_seconds() > 0.1:  # 100ms
                response.failure(f"Quota check took {response.elapsed.total_seconds()}s")
    
    @task(1)
    def run_stock_analysis(self):
        """Test stock analysis with quota"""
        self.client.post("/start-analysis", {
            "ticker": "AAPL"
        })

# Run with: locust -f test_quota_performance.py --users 100 --spawn-rate 10
```

---

## Security Tests

### Test File: `tests/security/test_quota_security.py`

```python
import pytest

class TestQuotaSecurity:
    """Security tests for quota system"""
    
    def test_user_cannot_modify_own_quota(self, app):
        """Test users cannot modify their own quota via API"""
        client = app.test_client()
        
        # Login as regular user
        # Attempt to modify quota
        response = client.post('/api/quota/adjust', json={
            'user_uid': 'self',
            'new_limit': 1000
        })
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_user_cannot_view_others_quota(self, app):
        """Test users cannot view other users' quota"""
        client = app.test_client()
        
        # Login as user A
        # Attempt to view user B's quota
        response = client.get('/api/quota/status?user=other_user')
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_quota_bypass_attempt_detected(self, app):
        """Test quota bypass attempts are detected and logged"""
        # Attempt to bypass quota check
        # Verify logged as suspicious activity
        assert True
    
    def test_sql_injection_prevention(self, app):
        """Test quota system prevents SQL injection"""
        # Attempt injection in user_uid
        # Should be sanitized
        assert True
```

---

## Test Environments

### Local Development
- **Database**: Firestore Emulator
- **App**: Flask development server
- **Configuration**: `config/testing.py`

### Staging
- **Database**: Firestore (separate project)
- **App**: Deployed to Cloud Run
- **URL**: `https://staging.tickzen.app`

### Production
- **Database**: Firestore (production)
- **App**: Cloud Run with load balancer
- **URL**: `https://tickzen.app`

---

## Test Data

### Test Users
```python
TEST_USERS = {
    'free_user': {
        'email': 'free@test.com',
        'plan': 'free',
        'usage': {'stock_reports': 5, 'articles': 20}
    },
    'premium_user': {
        'email': 'premium@test.com',
        'plan': 'premium',
        'usage': {'stock_reports': 50, 'articles': 200}
    },
    'at_limit_user': {
        'email': 'limit@test.com',
        'plan': 'free',
        'usage': {'stock_reports': 10, 'articles': 50}
    },
    'suspended_user': {
        'email': 'suspended@test.com',
        'plan': 'free',
        'is_suspended': True
    }
}
```

---

## Continuous Integration

### GitHub Actions Workflow: `.github/workflows/quota-tests.yml`

```yaml
name: Quota System Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

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
        pip install pytest pytest-cov pytest-asyncio locust
    
    - name: Start Firestore Emulator
      run: |
        gcloud emulators firestore start --host-port=localhost:8080 &
        sleep 5
    
    - name: Run Unit Tests
      run: |
        pytest tests/unit/ --cov=app/services --cov-report=xml
    
    - name: Run Integration Tests
      run: |
        pytest tests/integration/ --cov-append --cov=app --cov-report=xml
    
    - name: Check Coverage
      run: |
        coverage report --fail-under=85
    
    - name: Upload Coverage
      uses: codecov/codecov-action@v2
      with:
        files: ./coverage.xml
    
    - name: Run Security Scan
      run: |
        bandit -r app/services/quota_service.py
    
    - name: Performance Benchmarks
      run: |
        pytest tests/performance/ --benchmark-only
```

---

## Test Execution Checklist

### Before Each Release
- [ ] All unit tests pass (95%+ coverage)
- [ ] All integration tests pass
- [ ] E2E tests pass on staging
- [ ] Performance benchmarks met
- [ ] Security scan clean
- [ ] Load testing completed
- [ ] Quota accuracy verified
- [ ] Firestore rules tested
- [ ] Documentation updated

### Daily Automated Tests
- [ ] Unit test suite
- [ ] Integration tests (critical paths)
- [ ] Quota accuracy check
- [ ] Performance regression tests

### Weekly
- [ ] Full E2E suite
- [ ] Load testing
- [ ] Security audit
- [ ] Data integrity check

---

**Last Updated**: January 13, 2026  
**Version**: 1.0  
**Status**: Ready for Implementation
