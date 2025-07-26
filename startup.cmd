@echo off
REM Azure App Service startup script for Tickzen (Windows)
REM This script handles the proper startup of the Flask-SocketIO application

echo Starting Tickzen Application on Azure App Service...
echo Python version:
python --version
echo Working directory: %cd%
echo Environment: %APP_ENV%

REM Set environment variables
set APP_ENV=production
set FLASK_DEBUG=False
set gunicorn=true

REM Check if required files exist
if not exist "wsgi.py" (
    echo ERROR: wsgi.py not found
    exit /b 1
)

if not exist "gunicorn.conf.py" (
    echo ERROR: gunicorn.conf.py not found
    exit /b 1
)

REM Start the application with optimized settings for Azure
echo Starting Gunicorn with sync worker and threading...
gunicorn --config gunicorn.conf.py --worker-class sync --threads 100 --workers 1 --worker-connections 1000 --bind 0.0.0.0:%PORT% --timeout 120 --keepalive 5 --max-requests 1000 --max-requests-jitter 100 --preload-app --access-logfile - --error-logfile - --log-level warning wsgi:application
