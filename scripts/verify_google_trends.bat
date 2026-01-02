@echo off
REM Google Trends Integration Setup & Verification Script for Windows
REM Run this script to verify the implementation is correctly integrated

setlocal enabledelayedexpansion

echo.
echo Google Trends Implementation Verification
echo ===========================================
echo.

REM Check if we're in the right directory
if not exist "requirements.txt" (
    echo Error: Not in tickzen2-main directory
    echo Please run this script from the project root
    pause
    exit /b 1
)

echo [OK] Running from correct directory
echo.

REM Check 1: Requirements.txt
echo Checking requirements.txt...
findstr /M "pytrends==4.7.0" requirements.txt > nul
if !errorlevel! equ 0 (
    echo [OK] pytrends==4.7.0 found in requirements.txt
) else (
    echo [ERROR] pytrends not found in requirements.txt
)
echo.

REM Check 2: Google Trends Collector Module
echo Checking Google Trends collector module...
if exist "app\google_trends_collector.py" (
    echo [OK] app\google_trends_collector.py exists
    for %%A in (app\google_trends_collector.py) do set size=%%~zA
    echo     File size: !size! bytes
) else (
    echo [ERROR] app\google_trends_collector.py not found
)
echo.

REM Check 3: Database File
echo Checking database file...
if exist "google_trends_database.json" (
    echo [OK] google_trends_database.json exists
    for %%A in (google_trends_database.json) do set size=%%~zA
    echo     File size: !size! bytes
) else (
    echo [ERROR] google_trends_database.json not found
)
echo.

REM Check 4: Frontend Template
echo Checking frontend template...
if exist "app\templates\google_trends_dashboard.html" (
    echo [OK] google_trends_dashboard.html exists
) else (
    echo [ERROR] google_trends_dashboard.html not found
)
echo.

REM Check 5: Automation Pipeline
echo Checking automation pipeline...
if exist "automation_scripts\google_trends_pipeline.py" (
    echo [OK] google_trends_pipeline.py exists
) else (
    echo [ERROR] google_trends_pipeline.py not found
)
echo.

REM Check 6: API Endpoints in main app
echo Checking API endpoints in main_portal_app.py...
findstr "@app.route('/api/trends/collect'" app\main_portal_app.py > nul
if !errorlevel! equ 0 (
    echo [OK] POST /api/trends/collect endpoint found
) else (
    echo [ERROR] POST /api/trends/collect endpoint not found
)

findstr "@app.route('/api/trends/get'" app\main_portal_app.py > nul
if !errorlevel! equ 0 (
    echo [OK] GET /api/trends/get endpoint found
) else (
    echo [ERROR] GET /api/trends/get endpoint not found
)

findstr "@app.route('/api/trends/related'" app\main_portal_app.py > nul
if !errorlevel! equ 0 (
    echo [OK] GET /api/trends/related endpoint found
) else (
    echo [ERROR] GET /api/trends/related endpoint not found
)

findstr "@app.route('/api/trends/history'" app\main_portal_app.py > nul
if !errorlevel! equ 0 (
    echo [OK] GET /api/trends/history endpoint found
) else (
    echo [ERROR] GET /api/trends/history endpoint not found
)
echo.

REM Check 7: Dashboard Route
echo Checking dashboard route...
findstr "@app.route('/trends-dashboard'" app\main_portal_app.py > nul
if !errorlevel! equ 0 (
    echo [OK] GET /trends-dashboard route found
) else (
    echo [ERROR] GET /trends-dashboard route not found
)
echo.

REM Check 8: Documentation
echo Checking documentation...
if exist "GOOGLE_TRENDS_README.md" (
    echo [OK] GOOGLE_TRENDS_README.md exists
) else (
    echo [ERROR] GOOGLE_TRENDS_README.md not found
)

if exist "IMPLEMENTATION_SUMMARY.md" (
    echo [OK] IMPLEMENTATION_SUMMARY.md exists
) else (
    echo [ERROR] IMPLEMENTATION_SUMMARY.md not found
)
echo.

REM Summary
echo ===========================================
echo Verification Complete!
echo.
echo Next steps:
echo 1. Install dependencies: pip install -r requirements.txt
echo 2. Start the application
echo 3. Navigate to: http://localhost:5000/trends-dashboard
echo 4. Click 'Collect Trends' to start
echo.
echo For detailed documentation, see:
echo - GOOGLE_TRENDS_README.md (comprehensive guide)
echo - IMPLEMENTATION_SUMMARY.md (what was implemented)
echo.

pause
