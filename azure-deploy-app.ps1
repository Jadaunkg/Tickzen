# Azure App Service Deployment Script for TempAutomate
# This script deploys the Flask application to Azure App Service

param(
    [string]$ResourceGroup = "tempautomate-rg",
    [string]$AppName = "tempautomate-app",
    [string]$Location = "eastus"
)

Write-Host "🚀 Starting Azure App Service deployment..." -ForegroundColor Green

# Check if Azure CLI is logged in
try {
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        Write-Host "❌ Not logged in to Azure. Please run: az login" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Logged in to Azure as: $($account.user.name)" -ForegroundColor Green
} catch {
    Write-Host "❌ Azure CLI not available or not logged in" -ForegroundColor Red
    exit 1
}

# Check if resource group exists
$rgExists = az group show --name $ResourceGroup 2>$null
if (-not $rgExists) {
    Write-Host "❌ Resource group '$ResourceGroup' not found. Please create it first." -ForegroundColor Red
    exit 1
}

# Check if web app exists
$appExists = az webapp show --name $AppName --resource-group $ResourceGroup 2>$null
if (-not $appExists) {
    Write-Host "❌ Web app '$AppName' not found. Please create it first." -ForegroundColor Red
    exit 1
}

Write-Host "📦 Preparing deployment files..." -ForegroundColor Yellow

# Create .deployment file for Azure
@"
[config]
command = pip install -r requirements.txt && gunicorn --bind=0.0.0.0 --timeout 600 app.main_portal_app:app
"@ | Out-File -FilePath ".deployment" -Encoding UTF8

# Create startup command file
"gunicorn --bind=0.0.0.0 --timeout 600 app.main_portal_app:app" | Out-File -FilePath "startup.txt" -Encoding UTF8

# Add gunicorn to requirements if not present
$requirements = Get-Content "requirements.txt" -Raw
if ($requirements -notmatch "gunicorn") {
    Add-Content "requirements.txt" "`ngunicorn==21.2.0"
    Write-Host "✅ Added gunicorn to requirements.txt" -ForegroundColor Green
}

Write-Host "🌐 Deploying to Azure App Service..." -ForegroundColor Yellow

# Deploy using Azure CLI
try {
    az webapp deployment source config-local-git --name $AppName --resource-group $ResourceGroup
    $gitUrl = az webapp deployment source config-local-git --name $AppName --resource-group $ResourceGroup --query url -o tsv
    
    Write-Host "📤 Pushing code to Azure..." -ForegroundColor Yellow
    
    # Initialize git if not already done
    if (-not (Test-Path ".git")) {
        git init
        git add .
        git commit -m "Initial commit for Azure deployment"
    }
    
    # Add Azure remote
    git remote add azure $gitUrl 2>$null
    git remote set-url azure $gitUrl
    
    # Push to Azure
    git push azure master --force
    
    Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
    Write-Host "🌐 Your app is available at: https://$AppName.azurewebsites.net" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Configure Firebase credentials in Azure App Settings" -ForegroundColor White
Write-Host "2. Set up Redis (if needed) or use alternative session storage" -ForegroundColor White
Write-Host "3. Test your application functionality" -ForegroundColor White
Write-Host "4. Configure custom domain (optional)" -ForegroundColor White

Write-Host "`n🔗 Useful Azure CLI commands:" -ForegroundColor Yellow
Write-Host "  View logs: az webapp log tail --name $AppName --resource-group $ResourceGroup" -ForegroundColor White
Write-Host "  View app settings: az webapp config appsettings list --name $AppName --resource-group $ResourceGroup" -ForegroundColor White
Write-Host "  Restart app: az webapp restart --name $AppName --resource-group $ResourceGroup" -ForegroundColor White 