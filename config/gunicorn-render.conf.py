# Render-Specific Gunicorn Configuration
# Place this as: tickzen2/config/gunicorn-render.conf.py
# Reference: https://docs.gunicorn.org/en/stable/settings.html

import os
import sys
from multiprocessing import cpu_count

# ===========================
# RENDER ENVIRONMENT SETTINGS
# ===========================

# Port configuration - Render assigns port via PORT env var
PORT = int(os.environ.get('PORT', '10000'))
bind = f'0.0.0.0:{PORT}'

# Process naming
proc_name = 'tickzen-render-app'

# ===========================
# WORKER CONFIGURATION
# ===========================
# Free tier limitation: single worker only
# Render allocates 0.5 GB RAM, so we keep minimal threads

# Number of worker processes
# Free tier: 1 worker (may increase on paid plans)
# Paid tier: 2-4 workers based on plan
workers = int(os.environ.get('WEB_CONCURRENCY', '1'))

# Worker class
# - 'sync': Traditional, best for Flask/SocketIO
# - 'gevent': Async, requires gevent dependency
# - 'asyncio': Python async, requires async app
worker_class = 'sync'

# Threads per worker (for threaded worker class)
# Free tier: limited threads due to memory constraints
threads = int(os.environ.get('GUNICORN_THREADS', '10'))

# Worker connections
# Connections worker will keep open
worker_connections = int(os.environ.get('WORKER_CONNECTIONS', '50'))

# ===========================
# TIMEOUT SETTINGS
# ===========================

# Timeout before restarting worker (seconds)
# Render free tier may timeout if too long
# Set based on environment - shorter for free tier
if os.environ.get('RENDER'):
    timeout = 120  # 2 minutes for free tier
else:
    timeout = 600  # 10 minutes for development

# Server socket keep-alive timeout
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '10'))

# ===========================
# REQUEST HANDLING
# ===========================

# Maximum requests before worker restart
# Helps prevent memory leaks
max_requests = int(os.environ.get('MAX_REQUESTS', '2000'))

# Add randomness to prevent thundering herd
max_requests_jitter = int(os.environ.get('MAX_REQUESTS_JITTER', '200'))

# ===========================
# LOGGING CONFIGURATION
# ===========================

# Access log
# '-' = stdout (Render captures this)
accesslog = '-'

# Error log
# '-' = stderr (Render captures this)
errorlog = '-'

# Log level
# Options: debug, info, warning, error, critical
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# Access log format
# Detailed format for debugging
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" '
    '%(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
)

# Extended format with response time
# access_log_format = (
#     '%(h)s %(l)s %(u)s %(t)s "%(r)s" '
#     '%(s)s %(b)s "%(f)s" "%(a)s" '
#     'rt=%(D)s uct="%(U)s" cs=%(c)s'
# )

# ===========================
# APPLICATION SETTINGS
# ===========================

# Preload application (for faster reloads)
preload_app = True

# Working directory
chdir = os.getcwd()

# Python path
pythonpath = os.path.dirname(os.path.abspath(__file__))

# ===========================
# PERFORMANCE TUNING
# ===========================

# Backlog for pending connections
backlog = 2048

# Don't specify sendfile, let gunicorn decide
sendfile = None

# ===========================
# SECURITY SETTINGS
# ===========================

# Limit request field size (16KB default)
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Strip header whitespace
strip_header_spaces = False

# ===========================
# CALLBACKS - LIFECYCLE EVENTS
# ===========================

def when_ready(server):
    """Called when the server is ready to accept connections."""
    env_info = f"Environment: {os.environ.get('FLASK_ENV', 'unknown')}"
    port_info = f"Port: {PORT}"
    workers_info = f"Workers: {workers}"
    server.log.info(f"✅ Server is ready. {env_info} | {port_info} | {workers_info}")

def on_exit(server):
    """Called when the server is shutting down."""
    server.log.info("🛑 Server shutting down")

def post_worker_init(worker):
    """Called after a worker process has been initialized."""
    worker.log.info(f"👷 Worker spawned (pid: {worker.pid})")

def worker_int(worker):
    """Called when a worker receives INT or QUIT signal."""
    worker.log.info("⚠️  Worker received interrupt signal")

def worker_abort(worker):
    """Called when a worker needs to be aborted."""
    worker.log.warning("⚠️  Worker abort signal received")

# ===========================
# ENVIRONMENT-SPECIFIC SETTINGS
# ===========================

# Production settings
if os.environ.get('RENDER') or os.environ.get('FLASK_ENV') == 'production':
    # Stricter settings for production
    timeout = 120
    workers = 1
    threads = 10
    worker_connections = 50
    max_requests = 1000
    
    # Production logging
    loglevel = 'info'

# Development settings
elif os.environ.get('FLASK_ENV') == 'development':
    # Relaxed settings for development
    timeout = 600
    workers = 1
    reload = True
    loglevel = 'debug'

# ===========================
# MONITORING & HEALTH CHECKS
# ===========================

# Enable request logging for monitoring
capture_output = True

# ===========================
# NOTES FOR RENDER
# ===========================
"""
This configuration is optimized for Render's free tier with these constraints:
- 0.5 GB RAM
- Shared CPU
- Single worker process
- 120-second timeout (2 minutes)

When upgrading to paid plans:
- Increase workers to 2-4
- Increase threads to 20-50
- Increase worker_connections to 100-200
- Increase timeout to 300-600

For monitoring:
- Check Render logs: Service → Logs
- Monitor metrics: Service → Metrics
- Review events: Service → Events
"""
