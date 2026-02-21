@echo off
REM ============================================
REM Complete FREE Deployment - Both Projects
REM Flask + Next.js on Firebase (100% FREE!)
REM ============================================

echo.
echo ============================================
echo    TickZen COMPLETE FREE Deployment
echo    Flask Portal + Next.js Stock Analysis
echo ============================================
echo.

set PROJECT_ID=tickzen-a5f89
set FLASK_DIR=c:\Users\visha\OneDrive\Desktop\tickzen2\tickzen2
set NEXTJS_DIR=D:\OneDrive\Tickzen ticker specific page\tickzen\frontend

echo Configuration:
echo   Project ID: %PROJECT_ID%
echo   Flask: %FLASK_DIR%
echo   Next.js: %NEXTJS_DIR%
echo.

set /p CONFIRM="Deploy BOTH projects? This is 100%% FREE! (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Deployment cancelled.
    pause
    exit /b 0
)

echo.
echo ============================================
echo  Step 1: Deploy Flask to Cloud Run
echo ============================================
echo.

cd /d "%FLASK_DIR%"
call deploy-free.bat

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Flask deployment failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Step 2: Update Next.js Firebase Config
echo ============================================
echo.

cd /d "%NEXTJS_DIR%"

REM Backup current firebase.json
copy firebase.json firebase.json.backup

REM Copy new configuration with Flask routes
copy firebase-with-flask.json firebase.json

echo Configuration updated!
echo.

echo ============================================
echo  Step 3: Deploy Next.js Hosting
echo ============================================
echo.

firebase deploy --only hosting

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Hosting deployment failed!
    echo Restoring backup...
    copy firebase.json.backup firebase.json
    pause
    exit /b 1
)

echo.
echo ============================================
echo   DEPLOYMENT COMPLETE! (100%% FREE!)
echo ============================================
echo.
echo Your application is now live at:
echo   https://tickzen.app/
echo.
echo Flask routes (Portal):
echo   - https://tickzen.app/login
echo   - https://tickzen.app/dashboard
echo   - https://tickzen.app/automation
echo.
echo Next.js routes (Stock Analysis):
echo   - https://tickzen.app/stocks/aapl/overview
echo   - https://tickzen.app/screener
echo   - https://tickzen.app/marketplace
echo.
echo Running on Firebase FREE tier:
echo   - Cloud Run: 2M requests/month FREE
echo   - Hosting: 10GB storage FREE
echo   - Firestore: 50K reads/day FREE
echo   - No credit card required!
echo.
echo View logs:
echo   gcloud run services logs tail tickzen-flask-portal --region us-central1
echo.
pause
