---
description: "Production deployment checklist and Azure-specific requirements for TickZen"
alwaysApply: false
globs:
  - "**/wsgi.py"
  - "**/gunicorn.conf.py"
  - "**/startup.*"
  - "**/.azure/**"
  - "**/azure-*.json"
---

# TickZen Production Deployment Standards

## Overview
Comprehensive checklist for production-ready deployments to Azure App Service. Follow ALL items before deploying to production.

## Pre-Deployment Checklist

### 1. Code Quality ✅
- [ ] All tests passing (pytest)
- [ ] Code coverage ≥ 75%
- [ ] No linting errors (pylint, flake8)
- [ ] Type hints added for public functions
- [ ] Docstrings for all modules/classes/functions
- [ ] Remove all debug print statements
- [ ] Remove all TODO/FIXME comments or convert to issues
- [ ] Code reviewed by at least one other developer

### 2. Security Audit ✅
- [ ] No hardcoded credentials in code
- [ ] All secrets in environment variables
- [ ] Firebase service account key in secure storage (Azure Key Vault or base64 env var)
- [ ] CSRF protection enabled on all forms
- [ ] SQL injection protection (parameterized queries)
- [ ] XSS protection in templates (auto-escaping enabled)
- [ ] Rate limiting on API endpoints
- [ ] Admin routes restricted to authorized emails
- [ ] Session secrets using cryptographically secure random values
- [ ] HTTPS enforced (HTTP redirects to HTTPS)

### 3. Environment Variables ✅
Required environment variables for production:

```bash
# Firebase Configuration
FIREBASE_PROJECT_ID="your-project-id"
FIREBASE_STORAGE_BUCKET="your-bucket.appspot.com"
GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
# OR use base64 encoded key
FIREBASE_SERVICE_ACCOUNT_BASE64="base64_encoded_key_here"

# Flask Configuration
FLASK_SECRET_KEY="use-secure-random-64-character-key"
FLASK_ENV="production"  # CRITICAL: Never use 'development' in production

# API Keys
ALPHA_VANTAGE_API_KEY="your-key"
FINNHUB_API_KEY="your-key"
FRED_API_KEY="your-key"
GEMINI_API_KEY="your-key"
PERPLEXITY_API_KEY="your-key"

# Automation Settings
ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP="20"

# Azure Detection
WEBSITE_SITE_NAME="tickzen-app"  # Auto-set by Azure
```

### 4. Azure App Service Configuration ✅

#### Application Settings (in Azure Portal)
```json
{
  "SCM_DO_BUILD_DURING_DEPLOYMENT": "true",
  "ENABLE_ORYX_BUILD": "true",
  "WEBSITE_HTTPLOGGING_RETENTION_DAYS": "7",
  "WEBSITES_ENABLE_APP_SERVICE_STORAGE": "true"
}
```

#### Startup Command
```bash
gunicorn --config gunicorn.conf.py wsgi:app
```

#### Python Version
- Use Python 3.11 (specified in runtime.txt or Azure config)
- Match local development version exactly

### 5. Gunicorn Configuration ✅

Verify `gunicorn.conf.py`:
```python
# CRITICAL: SocketIO requires single worker
workers = 1
threads = 100  # High thread count for concurrency
timeout = 600  # Long timeout for analysis jobs
worker_class = 'sync'  # NOT 'eventlet' or 'gevent'
bind = '0.0.0.0:8000'
keepalive = 75
max_requests = 1000
max_requests_jitter = 50
```

### 6. Firebase Production Setup ✅
- [ ] Use production Firebase project (not dev/test)
- [ ] Firestore indexes created for queries
- [ ] Storage CORS configured for domain
- [ ] Security rules reviewed and tested
- [ ] Billing alerts configured
- [ ] Daily backup enabled
- [ ] Quota limits appropriate for production traffic

#### Firestore Indexes
```javascript
// Required indexes for performant queries
{
  "indexes": [
    {
      "collectionGroup": "userGeneratedReports",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "user_uid", "order": "ASCENDING"},
        {"fieldPath": "created_at", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "processedTickers",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "status", "order": "ASCENDING"},
        {"fieldPath": "publishedDate", "order": "DESCENDING"}
      ]
    }
  ]
}
```

### 7. Dependencies ✅
- [ ] `requirements.txt` up to date
- [ ] No development dependencies in production requirements
- [ ] All dependencies pinned to specific versions
- [ ] Dependencies scanned for vulnerabilities (pip-audit, safety)
- [ ] License compatibility verified

#### Generate Clean Requirements
```bash
# Production requirements only
pip freeze | grep -v "dev\|test\|debug" > requirements.txt

# Or use pip-tools
pip-compile requirements.in --output-file requirements.txt
```

### 8. Static Files & Assets ✅
- [ ] Static files collected (`flask collect-static` if using)
- [ ] Images optimized (compressed, WebP format)
- [ ] CSS/JS minified
- [ ] CDN configured for static assets (optional but recommended)
- [ ] Cache headers set appropriately

### 9. Logging Configuration ✅

#### Application Logging
```python
import logging
from logging.handlers import RotatingFileHandler

# Production logging setup
if app.config['ENV'] == 'production':
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/tickzen.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    app.logger.addHandler(file_handler)
    
    # Azure Application Insights (optional)
    from applicationinsights.flask.ext import AppInsights
    appinsights = AppInsights(app)
```

#### What to Log
- ✅ User authentication events
- ✅ Analysis pipeline start/completion
- ✅ WordPress publishing events
- ✅ API errors and retries
- ✅ Firebase operation failures
- ✅ Performance metrics (slow queries > 1s)

#### What NOT to Log
- ❌ User passwords or auth tokens
- ❌ API keys or secrets
- ❌ Complete user data (PII)
- ❌ Firebase service account keys

### 10. Database & State Management ✅
- [ ] Firestore backup strategy in place
- [ ] Test restore from backup
- [ ] State cleanup jobs scheduled (old reports, cache)
- [ ] Migration scripts tested
- [ ] Connection pooling configured
- [ ] Transactions used for critical operations

### 11. Performance Optimization ✅

#### Caching Strategy
```python
# Redis cache for frequent queries (production)
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL'),
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Cache expensive operations
@cache.memoize(timeout=600)
def get_market_overview():
    # Expensive market data aggregation
    return aggregate_market_data()
```

#### Lazy Loading Verified
- [ ] Heavy imports lazy-loaded (pandas, numpy, prophet)
- [ ] Matplotlib configured with Agg backend
- [ ] startup_optimization.py applied

#### Database Query Optimization
- [ ] N+1 queries eliminated
- [ ] Indexes on frequently queried fields
- [ ] Query results cached appropriately
- [ ] Batch operations used where possible

### 12. Monitoring & Alerting ✅

#### Azure Application Insights Setup
```python
# In production, enable Application Insights
APPINSIGHTS_INSTRUMENTATIONKEY = os.environ.get('APPINSIGHTS_KEY')

# Track custom metrics
from applicationinsights import TelemetryClient
tc = TelemetryClient(APPINSIGHTS_INSTRUMENTATIONKEY)
tc.track_metric('analysis_duration', duration)
tc.track_event('publishing_completed', properties)
```

#### Alerts to Configure
- [ ] Error rate > 5% in 5 minutes
- [ ] Response time > 10s for 5 minutes
- [ ] CPU usage > 80% for 10 minutes
- [ ] Memory usage > 90% for 5 minutes
- [ ] Firebase quota approaching limit
- [ ] API quota approaching limit
- [ ] Storage approaching quota

### 13. Error Handling ✅

#### Global Error Handlers
```python
@app.errorhandler(500)
def internal_error(error):
    """Log error and show user-friendly message"""
    app.logger.error(f'Server Error: {error}', exc_info=True)
    
    # In production, hide details
    if app.config['ENV'] == 'production':
        return render_template('error.html',
            message="An unexpected error occurred. Our team has been notified."
        ), 500
    else:
        # Show details in development
        return render_template('error.html',
            message=str(error), traceback=traceback.format_exc()
        ), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message="Page not found"), 404
```

#### Graceful Degradation
```python
# ALWAYS check Firebase availability
if not get_firebase_app_initialized():
    app.logger.error("Firebase unavailable - using fallback")
    # Provide degraded functionality
    flash("Some features may be unavailable. Please try again later.", "warning")
    # Continue with local storage or cached data
```

### 14. SocketIO Production Configuration ✅

#### Verify Configuration
```python
# In main_portal_app.py
socketio = SocketIO(
    app,
    async_mode='threading',  # CRITICAL: Use threading, not eventlet
    cors_allowed_origins="*",  # Restrict in production to your domain
    logger=True,  # Production logging
    engineio_logger=False,  # Disable engine.io debug logs
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6
)
```

#### WebSocket Support in Azure
- [ ] WebSockets enabled in Azure App Service Configuration
- [ ] ARR Affinity enabled (sticky sessions for SocketIO)
- [ ] Test WebSocket connectivity after deployment

### 15. Rate Limiting ✅

#### Implement Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"  # Use Redis in production
)

# Apply to sensitive endpoints
@app.route('/api/analyze', methods=['POST'])
@limiter.limit("10 per hour")
@login_required
def analyze_endpoint():
    pass

@app.route('/run-automation-now', methods=['POST'])
@limiter.limit("20 per day")
@login_required
def automation_endpoint():
    pass
```

### 16. Health Checks ✅

#### Comprehensive Health Endpoint
```python
@app.route('/health')
def health_check():
    """Comprehensive health check for monitoring"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'checks': {}
    }
    
    # Check Firebase
    health_status['checks']['firebase'] = is_firebase_healthy()
    
    # Check external APIs (with timeout)
    health_status['checks']['apis'] = check_api_connectivity()
    
    # Check disk space
    import shutil
    disk = shutil.disk_usage('/')
    health_status['checks']['disk_space'] = {
        'free_gb': disk.free / (1024**3),
        'percent_used': (disk.used / disk.total) * 100
    }
    
    # Overall status
    all_healthy = all(check.get('status') == 'healthy' 
                     for check in health_status['checks'].values())
    health_status['status'] = 'healthy' if all_healthy else 'degraded'
    
    status_code = 200 if all_healthy else 503
    return jsonify(health_status), status_code
```

### 17. Backup & Recovery ✅
- [ ] Automated daily backups of Firestore
- [ ] Backup retention policy (30 days minimum)
- [ ] Tested recovery procedure documented
- [ ] Critical data exported to secondary location
- [ ] Code repository backed up (GitHub/Azure Repos)
- [ ] Configuration backup (environment variables documented)

### 18. Documentation ✅
- [ ] API documentation up to date
- [ ] Deployment runbook created
- [ ] Rollback procedure documented
- [ ] Incident response plan documented
- [ ] Architecture diagrams current
- [ ] Environment variables documented
- [ ] Monitoring dashboard created

### 19. Testing in Production-Like Environment ✅
- [ ] Staging environment matches production
- [ ] End-to-end tests run in staging
- [ ] Load testing performed (expected + 2x traffic)
- [ ] Failover testing completed
- [ ] Backup restore tested
- [ ] Security scan performed (OWASP ZAP, etc.)

### 20. Deployment Strategy ✅

#### Blue-Green Deployment (Recommended)
1. Deploy new version to slot (staging)
2. Run smoke tests on staging slot
3. Warm up staging slot
4. Swap staging to production
5. Monitor for errors
6. Rollback if needed (swap back)

#### Deployment Steps
```bash
# 1. Final checks
pytest
flake8 .
pip-audit

# 2. Build and test
git checkout main
git pull origin main
python -m pip install -r requirements.txt
pytest

# 3. Deploy to Azure
az webapp deployment source config-zip \
  --resource-group tickzen-rg \
  --name tickzen-app \
  --src ./deployment.zip

# 4. Verify health
curl https://tickzen.app/health

# 5. Monitor logs
az webapp log tail \
  --resource-group tickzen-rg \
  --name tickzen-app
```

## Post-Deployment Checklist

### Immediate (First 30 minutes)
- [ ] Health check endpoint returns 200
- [ ] Login/authentication working
- [ ] Stock analysis can be triggered
- [ ] WordPress automation functional
- [ ] SocketIO real-time updates working
- [ ] Firebase operations successful
- [ ] No critical errors in logs
- [ ] Response times acceptable (< 2s avg)

### First 24 Hours
- [ ] Monitor error rates (should be < 1%)
- [ ] Check performance metrics
- [ ] Review user feedback/issues
- [ ] Verify scheduled jobs running
- [ ] Check resource usage (CPU, memory, storage)
- [ ] Review security logs
- [ ] Verify backups completed

### First Week
- [ ] Analyze usage patterns
- [ ] Review performance trends
- [ ] Optimize slow queries
- [ ] Address user-reported issues
- [ ] Update monitoring thresholds if needed

## Rollback Procedure

### When to Rollback
- Critical bugs affecting all users
- Security vulnerability discovered
- Data corruption detected
- Performance degradation > 50%
- Error rate > 10%

### How to Rollback
```bash
# Azure App Service - Swap slots back
az webapp deployment slot swap \
  --resource-group tickzen-rg \
  --name tickzen-app \
  --slot staging \
  --action swap

# Or use Azure Portal
# 1. Go to Deployment Slots
# 2. Click "Swap"
# 3. Swap production with staging
```

## Production Environment Variables Security

### Never Commit to Git
```bash
# .gitignore MUST include:
.env
.env.production
firebase-service-account-key.json
*.pem
*.key
secrets/
```

### Use Azure Key Vault (Recommended)
```python
# Reference secrets from Key Vault
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://tickzen-vault.vault.azure.net", 
                     credential=credential)

# Retrieve secrets
firebase_key = client.get_secret("firebase-service-account").value
api_key = client.get_secret("alpha-vantage-key").value
```

## Compliance & Legal

### GDPR Compliance (if applicable)
- [ ] User data deletion endpoint implemented
- [ ] Data export functionality available
- [ ] Privacy policy updated
- [ ] Cookie consent implemented
- [ ] Data processing documented

### Terms of Service
- [ ] Terms of service page created
- [ ] Acceptable use policy defined
- [ ] Liability disclaimers in place
- [ ] User agreement on signup

## Success Metrics

### Performance
- 99.9% uptime
- < 2s average response time
- < 1% error rate
- < 10s analysis completion

### Security
- Zero security incidents
- All dependencies up to date
- Security scans passing
- No exposed secrets

### Reliability
- Successful backups daily
- Recovery tested monthly
- No data loss
- Graceful degradation working
