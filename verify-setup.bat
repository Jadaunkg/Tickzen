@echo off
REM ============================================
REM Pre-Deployment Verification Script
REM Checks all prerequisites before deployment
REM ============================================

setlocal enabledelayedexpansion

echo.
echo ============================================
echo    TickZen Deployment Verification
echo ============================================
echo.

set "ERRORS=0"
set "WARNINGS=0"

REM Check 1: Firebase CLI
echo [1/7] Checking Firebase CLI...
where firebase >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('firebase --version 2^>nul') do set FIREBASE_VERSION=%%i
    echo [OK] Firebase CLI installed: !FIREBASE_VERSION!
) else (
    echo [ERROR] Firebase CLI not found!
    echo        Install: npm install -g firebase-tools
    set /a ERRORS+=1
)
echo.

REM Check 2: Google Cloud SDK
echo [2/7] Checking Google Cloud SDK...
where gcloud >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('gcloud --version 2^>nul ^| findstr /C:"Google Cloud SDK"') do set GCLOUD_VERSION=%%i
    echo [OK] Google Cloud SDK installed: !GCLOUD_VERSION!
) else (
    echo [ERROR] Google Cloud SDK not found!
    echo        Download: https://cloud.google.com/sdk/docs/install
    set /a ERRORS+=1
)
echo.

REM Check 3: Python
echo [3/7] Checking Python...
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('python --version 2^>nul') do set PYTHON_VERSION=%%i
    echo [OK] Python installed: !PYTHON_VERSION!
) else (
    echo [WARNING] Python not found (may not be needed for Cloud Run deployment)
    set /a WARNINGS+=1
)
echo.

REM Check 4: Node.js
echo [4/7] Checking Node.js...
where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('node --version 2^>nul') do set NODE_VERSION=%%i
    echo [OK] Node.js installed: !NODE_VERSION!
) else (
    echo [ERROR] Node.js not found!
    echo        Download: https://nodejs.org/
    set /a ERRORS+=1
)
echo.

REM Check 5: Flask Project Structure
echo [5/7] Checking Flask project files...
set "FLASK_DIR=c:\Users\visha\OneDrive\Desktop\tickzen2\tickzen2"
cd /d "%FLASK_DIR%" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Flask project directory not found!
    set /a ERRORS+=1
) else (
    if exist "app\main_portal_app.py" (
        echo [OK] app\main_portal_app.py found
    ) else (
        echo [ERROR] app\main_portal_app.py not found!
        set /a ERRORS+=1
    )
    
    if exist "wsgi.py" (
        echo [OK] wsgi.py found
    ) else (
        echo [ERROR] wsgi.py not found!
        set /a ERRORS+=1
    )
    
    if exist "Dockerfile" (
        echo [OK] Dockerfile found
    ) else (
        echo [ERROR] Dockerfile not found!
        set /a ERRORS+=1
    )
    
    if exist ".firebaserc" (
        echo [OK] .firebaserc found
    ) else (
        echo [ERROR] .firebaserc not found!
        set /a ERRORS+=1
    )
    
    if exist "firebase.json" (
        echo [OK] firebase.json found
    ) else (
        echo [ERROR] firebase.json not found!
        set /a ERRORS+=1
    )
    
    if exist "config\firebase-service-account-key.json" (
        echo [OK] Firebase service account key found
    ) else (
        echo [WARNING] Firebase service account key not found!
        echo           Path: config\firebase-service-account-key.json
        set /a WARNINGS+=1
    )
)
echo.

REM Check 6: Next.js Project Structure
echo [6/7] Checking Next.js project files...
set "NEXTJS_DIR=D:\OneDrive\Tickzen ticker specific page\tickzen\frontend"
if exist "%NEXTJS_DIR%" (
    cd /d "%NEXTJS_DIR%"
    
    if exist "firebase.json" (
        echo [OK] firebase.json found
        
        REM Check if firebase.json has Flask routes
        findstr /C:"tickzen-flask-portal" firebase.json >nul 2>nul
        if %ERRORLEVEL% EQU 0 (
            echo [OK] Flask routes configured in firebase.json
        ) else (
            echo [WARNING] Flask routes not found in firebase.json
            set /a WARNINGS+=1
        )
    ) else (
        echo [ERROR] firebase.json not found!
        set /a ERRORS+=1
    )
    
    if exist ".firebaserc" (
        echo [OK] .firebaserc found
    ) else (
        echo [ERROR] .firebaserc not found!
        set /a ERRORS+=1
    )
    
    if exist "package.json" (
        echo [OK] package.json found
    ) else (
        echo [ERROR] package.json not found!
        set /a ERRORS+=1
    )
) else (
    echo [ERROR] Next.js project directory not found!
    set /a ERRORS+=1
)
echo.

REM Check 7: Authentication Status
echo [7/7] Checking authentication...
where gcloud >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>nul | findstr "@" >nul
    if %ERRORLEVEL% EQU 0 (
        for /f "tokens=*" %%i in ('gcloud auth list --filter^=status:ACTIVE --format^="value(account)" 2^>nul') do set GCLOUD_ACCOUNT=%%i
        echo [OK] gcloud authenticated: !GCLOUD_ACCOUNT!
        
        REM Check project
        for /f "tokens=*" %%i in ('gcloud config get-value project 2^>nul') do set GCLOUD_PROJECT=%%i
        if "!GCLOUD_PROJECT!"=="tickzen-a5f89" (
            echo [OK] gcloud project set to: tickzen-a5f89
        ) else (
            echo [WARNING] gcloud project is: !GCLOUD_PROJECT!
            echo           Expected: tickzen-a5f89
            echo           Run: gcloud config set project tickzen-a5f89
            set /a WARNINGS+=1
        )
    ) else (
        echo [ERROR] gcloud not authenticated!
        echo        Run: gcloud auth login
        set /a ERRORS+=1
    )
) else (
    echo [SKIP] gcloud not installed
)
echo.

where firebase >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    firebase projects:list >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Firebase CLI authenticated
    ) else (
        echo [ERROR] Firebase CLI not authenticated!
        echo        Run: firebase login
        set /a ERRORS+=1
    )
) else (
    echo [SKIP] Firebase CLI not installed
)
echo.

REM Summary
echo ============================================
echo    Verification Summary
echo ============================================
echo.

if %ERRORS% EQU 0 (
    if %WARNINGS% EQU 0 (
        echo [SUCCESS] All checks passed! Ready to deploy!
        echo.
        echo Next step: Run deploy-complete-free.bat
        echo.
        set EXITCODE=0
    ) else (
        echo [READY] Ready to deploy with !WARNINGS! warning(s)
        echo.
        echo You can proceed, but review the warnings above.
        echo.
        echo Next step: Run deploy-complete-free.bat
        echo.
        set EXITCODE=0
    )
) else (
    echo [NOT READY] Found !ERRORS! error(s) and !WARNINGS! warning(s)
    echo.
    echo Please fix the errors above before deploying.
    echo.
    
    if %ERRORS% GTR 0 (
        echo Common fixes:
        echo.
        
        where gcloud >nul 2>nul
        if %ERRORLEVEL% NEQ 0 (
            echo 1. Install Google Cloud SDK:
            echo    https://cloud.google.com/sdk/docs/install
            echo.
        )
        
        where firebase >nul 2>nul
        if %ERRORLEVEL% NEQ 0 (
            echo 2. Install Firebase CLI:
            echo    npm install -g firebase-tools
            echo.
        )
        
        echo 3. Authenticate:
        echo    gcloud auth login
        echo    gcloud config set project tickzen-a5f89
        echo    firebase login
        echo.
    )
    
    set EXITCODE=1
)

echo ============================================
echo.

pause
exit /b %EXITCODE%
