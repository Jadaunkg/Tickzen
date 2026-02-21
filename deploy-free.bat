@echo off
REM ============================================
REM TickZen FREE Deployment Script (Windows)
REM Deploys Flask to Firebase Cloud Run (FREE!)
REM ============================================

echo.
echo ============================================
echo    TickZen Flask FREE Deployment
echo ============================================
echo.

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: gcloud CLI not found!
    echo.
    echo Please install Google Cloud SDK:
    echo https://cloud.google.com/sdk/docs/install
    echo.
    pause
    exit /b 1
)

REM Check if firebase is installed
where firebase >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Firebase CLI not found!
    echo.
    echo Installing Firebase CLI...
    npm install -g firebase-tools
)

echo Current directory: %CD%
echo.

REM Set project ID
set PROJECT_ID=tickzen-a5f89
set SERVICE_NAME=tickzen-flask-portal
set REGION=us-central1

echo Configuration:
echo   Project: %PROJECT_ID%
echo   Service: %SERVICE_NAME%
echo   Region: %REGION%
echo.

REM Confirm deployment
set /p CONFIRM="Deploy Flask to Cloud Run? This is 100%% FREE! (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Deployment cancelled.
    pause
    exit /b 0
)

echo.
echo ============================================
echo  Step 1: Setting up Firebase project
echo ============================================
echo.

firebase use %PROJECT_ID%

echo.
echo ============================================
echo  Step 2: Deploying to Cloud Run (FREE!)
echo ============================================
echo.

gcloud run deploy %SERVICE_NAME% ^
  --source . ^
  --region %REGION% ^
  --platform managed ^
  --allow-unauthenticated ^
  --memory 1Gi ^
  --cpu 1 ^
  --timeout 300 ^
  --max-instances 3 ^
  --min-instances 0 ^
  --project %PROJECT_ID% ^
  --quiet

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Deployment failed!
    echo Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Getting service URL...
echo ============================================
echo.

for /f "tokens=*" %%i in ('gcloud run services describe %SERVICE_NAME% --region %REGION% --format "value(status.url)"') do set SERVICE_URL=%%i

echo.
echo ============================================
echo   Deployment Complete! (FREE!)
echo ============================================
echo.
echo Service URL: %SERVICE_URL%
echo.
echo Next steps:
echo   1. Update Next.js firebase.json with Flask routes
echo   2. Deploy Next.js hosting configuration
echo   3. Test your application
echo.
echo Your Flask app is now running on Cloud Run's FREE tier!
echo   - 2 million requests/month FREE
echo   - No credit card required
echo.
echo View logs:
echo   gcloud run services logs tail %SERVICE_NAME% --region %REGION%
echo.
pause
