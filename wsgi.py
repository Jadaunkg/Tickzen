import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables for Azure App Service
os.environ.setdefault('APP_ENV', 'production')
os.environ.setdefault('FLASK_ENV', 'production')

try:
    from app.main_portal_app import app
    print("Successfully imported Flask app from app.main_portal_app")
except ImportError as e:
    print(f"Error importing app: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Available files in current directory: {os.listdir('.')}")
    if os.path.exists('app'):
        print(f"Available files in app directory: {os.listdir('app')}")
    raise

# Ensure the app is properly configured
if not hasattr(app, 'config'):
    print("Warning: Flask app does not have config attribute")
    
print(f"Flask app imported successfully. App name: {app.name}")
print(f"App config: {app.config.get('ENV', 'Not set')}") 