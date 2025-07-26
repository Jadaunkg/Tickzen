# Gunicorn configuration file for Tickzen production deployment
import os
import multiprocessing

# Basic configuration
bind = "0.0.0.0:8000"  # Azure expects port 8000
workers = 1  # Single worker for SocketIO applications
worker_class = "sync"  # Use sync worker class with threading for better compatibility
threads = 50  # Reduced threads for faster startup
worker_connections = 1000
worker_connections = 1000

# Performance settings - Optimized for faster startup
max_requests = 1000
max_requests_jitter = 100
timeout = 300  # Increased timeout for Azure startup
keepalive = 5
preload_app = False  # Disable preloading for faster startup

# Process naming
proc_name = "tickzen-app"

# Logging
accesslog = "-"  # Log to stdout (Azure captures this)
errorlog = "-"   # Log to stderr (Azure captures this)
loglevel = "warning"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Application settings
pythonpath = "/home/site/wwwroot"
chdir = "/home/site/wwwroot"

# Worker lifecycle
def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def on_exit(server):
    server.log.info("Server shutting down")

def post_worker_init(worker):
    worker.log.info("Worker spawned (pid: %s)", worker.pid)

# Error handling
def worker_abort(worker):
    worker.log.info("Worker abort signal received")
