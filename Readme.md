Project Overview

Tickzen is a production Flask-SocketIO web application for AI-powered stock analysis and automated WordPress content publishing. Deployed on Azure App Service with Firebase (Firestore + Storage) backend. Uses Prophet for time-series forecasting, extensive financial APIs (yfinance, FRED), and real-time WebSocket communication.

Critical Architecture Patterns

1. Firebase Integration (Multi-Service)

Initialization: config/firebase_admin_setup.py handles all Firebase services with comprehensive error tracking

Always check availability: Use get_firebase_app_initialized() or FIREBASE_INITIALIZED_SUCCESSFULLY before Firebase operations

Storage pattern: Reports stored in BOTH local filesystem (legacy) AND Firebase Storage (primary)

# Check Firebase availability first
if not get_firebase_app_initialized():
    # Handle gracefully - log error and fallback


Key functions: get_firestore_client(), get_storage_bucket(), verify_firebase_token()

Health monitoring: is_firebase_healthy() and get_firebase_health_status() for diagnostics

2. SocketIO Real-Time Communication

Threading mode: App uses async_mode='threading' (NOT eventlet/gevent) - critical for Azure compatibility

Room-based messaging: User UID or client SID used as room identifier for targeted updates

Event naming convention:

analysis_progress: Stock analysis pipeline updates

automation_update: WordPress publishing progress

ticker_status_persisted: Ticker processing status saved to Firestore

analysis_error, wp_asset_error: Error notifications

Progress emission pattern:

socketio.emit('analysis_progress', {
    'progress': 45, 'message': 'Training model...', 
    'stage': 'Model Training', 'ticker': ticker
}, room=user_room)


3. Lazy Loading & Startup Optimization

Heavy imports are lazy-loaded to reduce Azure cold start time (see startup_optimization.py)

Pattern: Use getter functions like get_pandas(), get_jwt() instead of direct imports

Matplotlib: Pre-configured with Agg backend in optimize_matplotlib()

Environment: startup_optimization.py sets critical env vars before app initialization

4. Stock Analysis Pipeline (automation_scripts/pipeline.py)

Entry point: run_pipeline(ticker, timestamp, app_root, socketio_instance, task_room)

Data caching: Processed data cached in generated_data/data_cache/ with date-based validation

Progress stages:

Data fetching (5-25%)

Preprocessing (25-35%)

Model training (35-60%)

Report generation (60-100%)

Error handling: Emits user-friendly errors via SocketIO (e.g., "No data found for ticker")

Cleanup: cleanup_old_processed_data() removes files older than 7 days

5. WordPress Auto-Publishing (automation_scripts/auto_publisher.py)

State management: Uses Firestore for multi-user persistence (via firestore_state_manager)

Daily limits: ABSOLUTE_MAX_POSTS_PER_DAY_ENV_CAP from env (default 20)

Ticker status persistence:

Stored in Firestore: userSiteProfiles/{user_uid}/profiles/{profile_id}/processedTickers/{ticker}

Use save_processed_ticker_status() callback pattern

File uploads: Ticker lists stored in Firebase Storage, metadata in Firestore

Author rotation: Round-robin via last_author_index_by_profile state tracking

6. User Authentication & Authorization

Firebase Auth: Client-side auth with server-side token verification via verify_firebase_token()

Session management: firebase_user_uid, firebase_user_email, firebase_user_displayName in Flask session

Decorators:

@login_required: Basic authentication

@admin_required: Admin-only routes (checks admin_emails list)

7. Report Storage Dual Strategy

# New reports: Save to BOTH local and Firebase Storage
with open(local_path, 'w') as f:
    f.write(html_content)  # Local (legacy)
storage_path = save_report_to_firebase_storage(uid, ticker, filename, content)  # Firebase

# Reading: Try Firebase first, fallback to local
if storage_path:
    content = get_report_content_from_firebase_storage(storage_path)
else:
    with open(local_path, 'r') as f:
        content = f.read()


Development Workflows

Running Locally (Development)

# Configure Python environment (required)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file)
# Required: FIREBASE_SERVICE_ACCOUNT_BASE64, FIREBASE_PROJECT_ID, etc.

# Run Flask development server
python -m app.main_portal_app  # With SocketIO
# OR
flask run  # Basic Flask only


Azure Deployment

Entry point: wsgi.py → loads app.main_portal_app:app

Server: Gunicorn with config in gunicorn.conf.py

1 worker (SocketIO requires single process)

100 threads for concurrency

600s timeout for long analysis jobs

Startup: startup.cmd (Windows) or startup.sh (Linux)

Environment detection: Checks WEBSITE_SITE_NAME env var to enable production mode

Testing Stock Analysis

# Direct pipeline test (no Flask)
from automation_scripts.pipeline import run_pipeline
model, forecast, path, html = run_pipeline('AAPL', str(time.time()), '/path/to/app')

# With SocketIO (in Flask context)
socketio_instance.emit('analysis_progress', {'progress': 10, ...}, room=user_room)


Firebase Operations

# Always check initialization
if not get_firebase_app_initialized():
    log_firebase_operation_error("operation_name", "Firebase unavailable", context)
    return None

# Firestore query pattern
db = get_firestore_client()
docs = db.collection('userProfiles').where('email', '==', email).limit(1).stream()

# Storage upload pattern
bucket = get_storage_bucket()
blob = bucket.blob(f'user_reports/{uid}/{filename}')
blob.upload_from_string(html_content, content_type='text/html')


Project-Specific Conventions

Error Handling Philosophy

User-facing errors: Via SocketIO events (e.g., analysis_error) for seamless UX

No flash() after analysis starts: WebSocket handles all feedback

Graceful degradation: Mock objects when imports fail (see MockAutoPublisher)

Firebase errors: Logged via log_firebase_operation_error() with context

File Organization

Routes: app/main_portal_app.py (5000+ lines - monolithic Flask app)

Blueprints: app/info_routes.py, app/market_news.py

Templates: app/templates/ (Jinja2 with _base.html inheritance)

Static assets: app/static/ (CSS, JS, images, chatbot)

Generated content: generated_data/ (reports, cache, uploads)

State: state/ (pickle files for legacy state management)

Naming Conventions

Route functions: snake_case with _route suffix (e.g., dashboard_page())

SocketIO events: snake_case with descriptive names (e.g., analysis_complete)

Firebase collections: camelCase (e.g., userGeneratedReports, userSiteProfiles)

Config files: Environment-specific (e.g., development_config.py, production_config.py)

Data Flow Examples

Stock Analysis Flow:

User submits ticker → @app.route('/start-analysis') → run_pipeline()

Pipeline emits progress via SocketIO → Client updates progress bar

Report HTML saved locally + Firebase Storage

Firestore document created in userGeneratedReports collection

Client redirected to /display-report/<ticker>/<filename>

WordPress Publishing Flow:

User configures profile → Saved to userSiteProfiles/{uid}/profiles/{profile_id}

User uploads ticker file → Firebase Storage + metadata in Firestore

Trigger automation → auto_publisher.trigger_publishing_run()

For each ticker: run_wp_pipeline() → Generate report → Publish to WordPress

Status saved via save_processed_ticker_status() callback

SocketIO emits ticker_processed_update for progress bar

Critical Dependencies

Flask + Flask-SocketIO: Web framework with real-time communication

firebase-admin: Server-side Firebase SDK (Auth, Firestore, Storage)

Prophet: Time-series forecasting (Facebook's library)

yfinance: Stock data retrieval

pandas/numpy: Data processing

gunicorn: Production WSGI server

reportlab: PDF generation (used in some report paths)

Common Pitfalls & Solutions

Issue: SocketIO Connection Failures

Cause: Using wrong async_mode or CORS settings

Solution: Always use async_mode='threading' and cors_allowed_origins="*" for development

Issue: Firebase "App already exists"

Cause: Attempting to initialize Firebase multiple times

Solution: Check _firebase_app_initialized flag before calling initialize_firebase_admin()

Issue: Report Not Found After Generation

Cause: File path construction mismatch between save and retrieve

Solution: Use os.path.join(STOCK_REPORTS_PATH, filename) consistently

Issue: Azure Timeout on Analysis

Cause: Default timeout too short for complex analysis

Solution: Increase gunicorn timeout (currently 600s) or optimize pipeline caching

Issue: Lazy Import Not Working

Cause: Direct import statement instead of getter function

Solution: Replace import pandas as pd with pd = get_pandas() in functions

Key Files to Read

app/main_portal_app.py: Main Flask app, routes, SocketIO handlers

automation_scripts/pipeline.py: Stock analysis orchestration

automation_scripts/auto_publisher.py: WordPress publishing automation

config/firebase_admin_setup.py: Firebase initialization and health checks

reporting_tools/wordpress_reporter.py: Report HTML generation

gunicorn.conf.py: Production server configuration

startup_optimization.py: Performance improvements for Azure

Testing & Debugging

Health check: /health (simple) or /api/health (detailed Firebase status)

Admin panel: /admin (requires admin email in admin_emails list)

Firebase diagnostics: /api/firebase-diagnostics (admin-only)

Logs: Azure captures stdout/stderr from Gunicorn

Local debugging: Set FLASK_DEBUG=True and use Flask dev server

Last updated: 2025-01-15. For questions, see docs/ or contact the development team.