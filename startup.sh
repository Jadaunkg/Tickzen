#!/bin/bash
# Azure App Service startup script for Tickzen
# This script handles the proper startup of the Flask-SocketIO application

echo "Starting Tickzen Application on Azure App Service..."
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Environment: $APP_ENV"

# Set environment variables
export APP_ENV=production
export FLASK_DEBUG=False
export gunicorn=true

# Check if required files exist
if [ ! -f "wsgi.py" ]; then
    echo "ERROR: wsgi.py not found"
    exit 1
fi

if [ ! -f "gunicorn.conf.py" ]; then
    echo "ERROR: gunicorn.conf.py not found"
    exit 1
fi

# Start the application with optimized settings for Azure
echo "Starting Gunicorn with sync worker and threading..."
exec gunicorn \
    --config gunicorn.conf.py \
    --worker-class sync \
    --threads 100 \
    --workers 1 \
    --worker-connections 1000 \
    --bind 0.0.0.0:${PORT:-5000} \
    --timeout 120 \
    --keepalive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload-app \
    --access-logfile - \
    --error-logfile - \
    --log-level warning \
    wsgi:application
