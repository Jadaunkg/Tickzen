#!/usr/bin/env python3
"""
WSGI entry point for Azure App Service with startup optimizations
This file is used by Gunicorn to start the application
"""

import os
import sys
import time

# Add the project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set production environment
os.environ.setdefault('APP_ENV', 'production')
os.environ.setdefault('FLASK_DEBUG', 'False')

print(f"🚀 Starting application initialization at {time.strftime('%Y-%m-%d %H:%M:%S')}")
start_time = time.time()

# Apply startup optimizations
try:
    from startup_optimization import optimize_startup_environment
    optimize_startup_environment()
    print("✅ Startup environment optimized")
except ImportError as e:
    print(f"⚠️  Warning: Could not import startup optimizations: {e}")

# Import and configure the application
from app.main_portal_app import app, socketio

# Apply production configuration
try:
    from production_config import apply_prod_config
    apply_prod_config()
    print("✅ Production configuration applied successfully")
except ImportError as e:
    print(f"⚠️  Warning: Could not import production config: {e}")

# For Azure App Service and Gunicorn
application = app

elapsed_time = time.time() - start_time
print(f"🎯 Application initialization completed in {elapsed_time:.2f} seconds")

# Expose socketio for potential use
socketio_app = socketio

if __name__ == "__main__":
    # This won't be called when using Gunicorn, but kept for testing
    print("Warning: Running app directly. Use Gunicorn for production.")
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
