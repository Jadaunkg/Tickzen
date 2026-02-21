# Gunicorn configuration file for Tickzen production deployment
import os
import multiprocessing

# Basic configuration
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = 1  # Single worker for SocketIO applications
worker_class = "gthread"  # Threaded worker for stable SocketIO long-polling
worker_connections = 2000

# Performance settings
max_requests = 2000
max_requests_jitter = 200
# 120 s is ample for web requests; long-running analysis runs in background
# threads / SocketIO events and does NOT block the worker, so 600 s was
# unnecessarily risky (zombie workers, memory leaks).
timeout = 120
keepalive = 30
preload_app = True  # Enable preloading for better performance
threads = 50

# Process naming
proc_name = "tickzen-app"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"  # Changed to info for better debugging
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Application settings
pythonpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
chdir = pythonpath

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
