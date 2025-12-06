@echo off
echo =========================================================
echo Enhanced Sports News Pipeline with Deduplication  
echo =========================================================
echo.

cd /d "%~dp0"

echo [1/3] Running Enhanced News Pipeline with Deduplication...
echo      - Collecting RSS feeds from multiple sources
echo      - Applying importance scoring and hybrid ranking
echo      - Removing articles older than 24 hours
echo      - Removing duplicate articles across sources
echo.

C:/Users/VishalJadaunMAQSoftw/AppData/Local/Programs/Python/Python311/python.exe enhanced_news_pipeline.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Pipeline failed with error code %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] ✅ Pipeline completed successfully!
echo      - Duplicates removed automatically
echo      - Articles ranked by latest + importance
echo      - Database optimized and ready
echo.

echo [3/3] Starting web viewer...
echo      📱 Web interface will be available at: http://localhost:5000
echo      🔍 Features: Hybrid ranking, deduplication, advanced filters
echo.

start C:/Users/VishalJadaunMAQSoftw/AppData/Local/Programs/Python/Python311/python.exe web_server.py

echo.
echo 🌐 Opening web browser...
timeout /t 3 > nul
start http://localhost:5000

echo.
echo ✅ Complete! Your deduplicated sports news is ready.
echo    Press any key to exit...
pause > nul