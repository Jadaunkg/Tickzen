Write-Host "Starting TickZen Separated Services..." -ForegroundColor Cyan

# Ensure session directory exists for local testing
New-Item -ItemType Directory -Force -Path "flask_session" | Out-Null
Write-Host "Created 'flask_session' directory for shared session storage." -ForegroundColor Green

# Start Stock Service (Port 8080)
Write-Host "Launching STOCK SERVICE (port 8080)..." -ForegroundColor Yellow
# Using full paths and error handling wrapper
$scriptPath = $PSScriptRoot
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath'; $env:PYTHONPATH='$scriptPath'; python wsgi_stock.py; if (`$LASTEXITCODE -ne 0) { Read-Host 'Error occurred. Press Enter to close...' }"

# Start Automation Service (Port 8081)
Write-Host "Launching AUTOMATION SERVICE (port 8081)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath'; $env:PYTHONPATH='$scriptPath'; python wsgi_automation.py; if (`$LASTEXITCODE -ne 0) { Read-Host 'Error occurred. Press Enter to close...' }"

Write-Host "Services started!" -ForegroundColor Green
Write-Host "---------------------------------------------------"
Write-Host "Stock Dashboard:      http://localhost:8080"
Write-Host "Automation Dashboard: http://localhost:8081"
Write-Host "---------------------------------------------------"
Write-Host "Press Enter to exit this launcher (services will remain running)..."
Read-Host
