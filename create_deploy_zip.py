import zipfile
import os

# List of folders to include
folders = [
    'app', 'config', 'Models', 'state', 'analysis_scripts', 'automation_scripts',
    'data_processing_scripts', 'reporting_tools', 'generated_data', 'logs', 'tests'
]

# List of files to include
files = [
    'requirements.txt', 'wsgi.py', 'startup.py', 'celery_worker.py', 'start_production.py',
    'azure-web.config', 'azure-startup.txt', 'connect-redis-to-azure.sh', 'pytest.ini',
    'all-us-tickers.json', 'firebase_service_account_base64.txt'
]

def should_include(file_path):
    # Exclude __pycache__ and .pyc files
    if '__pycache__' in file_path or file_path.endswith('.pyc'):
        return False
    return True

with zipfile.ZipFile('deploy_clean.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for folder in folders:
        if not os.path.exists(folder):
            continue
        for root, dirs, file_list in os.walk(folder):
            # Exclude __pycache__ folders
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in file_list:
                full_path = os.path.join(root, file)
                if should_include(full_path):
                    arcname = full_path.replace('\\', '/').replace('\\', '/')
                    zf.write(full_path, arcname)
    for file in files:
        if os.path.exists(file):
            zf.write(file)

print('deploy_clean.zip created successfully!')
