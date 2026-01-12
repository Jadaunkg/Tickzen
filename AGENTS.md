# AI Agent Instructions for TickZen Development

> **Quick Reference:** For comprehensive project details, see [.cursorrules](.cursorrules)  
> **Detailed Rules:** For specialized guidance, see [.cursor/rules/](.cursor/rules/)

## Project Context

TickZen is a financial analysis platform with three automation pipelines:
1. **Stock Analysis** - Prophet ML forecasting + WordPress publishing
2. **Earnings Reports** - Quarterly analysis with Gemini AI
3. **Sports Articles** - AI-generated trending sports content

**Tech Stack:** Flask-SocketIO, Firebase (Firestore/Storage/Auth), Azure App Service, Python 3.10+

## Development Principles

### 1. Always Check Firebase Availability
```python
if not get_firebase_app_initialized():
    # Handle gracefully - log, return None, use fallback
    return None
```

### 2. Emit Progress via SocketIO
```python
# For any long-running automation
socketio.emit('automation_progress', {
    'stage': 'processing',
    'message': f'Analyzing {ticker}...',
    'percent': 45
}, room=f"user_{user_id}")
```

### 3. Dual Storage Strategy
- Save locally FIRST (always works)
- Then upload to Firebase Storage (if available)
- Store metadata in Firestore

### 4. API Error Handling
```python
# Always use retry logic with exponential backoff
@retry_with_backoff(max_attempts=3)
def call_external_api():
    # API call here
    pass
```

## Agent Roles

### Testing Agent
**Trigger:** Working with `**/test*.py`, `testing/**` files  
**Focus:**
- Write pytest tests with proper fixtures
- Mock Firebase/SocketIO/APIs
- Target 80% coverage for business logic
- Use `testing-standards` rule

### Deployment Agent
**Trigger:** Working with `wsgi.py`, `gunicorn.conf.py`, deployment files  
**Focus:**
- Verify Gunicorn config (1 worker, 100 threads for SocketIO)
- Check Azure App Service settings
- Review pre-deployment checklist (20 items)
- Use `production-deployment` rule

### Firebase Agent
**Trigger:** Working with Firebase/Firestore operations  
**Focus:**
- Always check `get_firebase_app_initialized()` first
- Use batch operations for multiple writes
- Implement proper error handling
- Use `firebase-operations` rule

### SocketIO Agent
**Trigger:** Working with automation, real-time features  
**Focus:**
- Emit to user-specific rooms (never broadcast)
- Use structured progress events
- Implement pause/resume functionality
- Use `socketio-patterns` rule

### API Integration Agent
**Trigger:** Working with external APIs (yfinance, Gemini, etc.)  
**Focus:**
- Implement rate limiting
- Add retry logic with exponential backoff
- Cache responses when appropriate
- Provide fallback chains
- Use `api-integration` rule

### Code Quality Agent
**Trigger:** All code (always active)  
**Focus:**
- PEP 8 compliance
- Type hints for all functions
- Google-style docstrings
- Specific exception handling
- Use `code-quality` rule

## Common Tasks

### Task: Add New Automation Feature
1. Create automation function in `automation_scripts/`
2. Add SocketIO progress emissions
3. Create route in `main_portal_app.py`
4. Create template in `templates/`
5. Add Firebase state management
6. Write tests in `testing/`
7. Update documentation

### Task: Integrate New API
1. Add API key to environment variables
2. Create wrapper function with retry logic
3. Implement rate limiting if needed
4. Add error handling and logging
5. Create fallback strategy
6. Mock API in tests
7. Document usage in module docstring

### Task: Fix Production Bug
1. Check logs in Azure App Service
2. Review Firestore error logs
3. Check SocketIO connection logs
4. Verify API rate limits not exceeded
5. Test locally with production data
6. Deploy fix via blue-green deployment

### Task: Add Tests
1. Create `test_<module>.py` in `testing/`
2. Mock Firebase with `patch('config.firebase_admin_setup.get_firebase_app_initialized')`
3. Mock SocketIO with `patch('main_portal_app.socketio')`
4. Mock external APIs (yfinance, Gemini, etc.)
5. Run `pytest` to verify
6. Check coverage with `pytest --cov`

## File Organization

```
Key Directories:
├── app/                    # Main application (routes, templates)
├── automation_scripts/     # Automation pipelines
├── analysis_scripts/       # Stock analysis modules
├── config/                 # Configuration, Firebase setup
├── data_processing_scripts/# Data collection, preprocessing
├── earnings_reports/       # Earnings automation
├── testing/               # Test files
└── .cursor/rules/         # AI agent rules
```

## Critical Files

- `main_portal_app.py` - Main Flask app (8324 lines)
- `config/firebase_admin_setup.py` - Firebase initialization
- `automation_scripts/pipeline.py` - Stock automation
- `earnings_reports/pipeline.py` - Earnings automation
- `wsgi.py` - Production entry point
- `gunicorn.conf.py` - Server configuration

## Routes Structure

### Current (Mixed Navigation)
- `/automation-runner` - Stock automation
- `/automation-earnings-runner` - Earnings automation
- `/automation-sports-runner` - Sports automation
- `/stock/<ticker>` - Stock analysis page

### Planned (Separated Navigation)
See [NAVIGATION_REDESIGN_ROADMAP.md](NAVIGATION_REDESIGN_ROADMAP.md)

## Firebase Collections

```
userProfiles/{user_uid}                    # User profiles
userGeneratedReports/{report_id}           # Report metadata
userSiteProfiles/{user_uid}/profiles/{id}  # WordPress profiles
  └── processedTickers/{ticker}            # Ticker publishing status
```

## Environment Variables Required

```bash
# Firebase
FIREBASE_ADMIN_SDK_KEY=<service-account-json>

# Financial APIs
ALPHA_VANTAGE_API_KEY=<key>
FINNHUB_API_KEY=<key>
FRED_API_KEY=<key>

# AI APIs
GEMINI_API_KEY=<key>
PERPLEXITY_API_KEY=<key>

# WordPress (user-specific, stored in Firestore)
```

## Testing Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest testing/test_automation.py

# Run with verbose output
pytest -v

# Run specific test
pytest testing/test_automation.py::test_function_name
```

## Deployment Commands

```bash
# Local development
python wsgi.py

# Production (Azure handles this)
gunicorn --config gunicorn.conf.py wsgi:app
```

## Debugging Tips

1. **Firebase not working?** Check `get_firebase_app_initialized()` returns True
2. **SocketIO not updating?** Verify `async_mode='threading'` and user in correct room
3. **API rate limits?** Check rate limiter implementation and logs
4. **Tests failing?** Ensure all external services are mocked
5. **Deployment issues?** Review Azure App Service logs and health check endpoint

## Quick Checklist

Before committing code:
- [ ] Type hints on all functions
- [ ] Docstrings on public functions
- [ ] Error handling with specific exceptions
- [ ] Logging with context
- [ ] Tests written and passing
- [ ] No hardcoded credentials
- [ ] Firebase availability checks
- [ ] SocketIO emits to correct room
- [ ] Code formatted (Black)
- [ ] Imports organized

## When in Doubt

1. Check [.cursorrules](.cursorrules) for patterns
2. Review relevant [.cursor/rules/](.cursor/rules/) file
3. Look for similar code in the project
4. Check [MASTER_DOCUMENTATION.md](MASTER_DOCUMENTATION.md)
5. Review Azure App Service logs

---

**Remember:** This is production code with real users. Test thoroughly, handle errors gracefully, and maintain backward compatibility.
