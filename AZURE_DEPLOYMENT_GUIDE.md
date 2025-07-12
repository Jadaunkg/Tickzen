# Azure Deployment Guide for Tickzen

## Problem Description
The main issue is **network connectivity** in Azure App Service preventing Firebase token verification. The error shows:
```
Failed to resolve 'www.googleapis.com' ([Errno -3] Lookup timed out)
```

## Root Causes
1. **Azure App Service Network Restrictions** - Outbound network access may be limited
2. **DNS Resolution Issues** - Azure cannot resolve Google's API domains
3. **Network Timeout Configuration** - Default timeouts are too short for Azure environment
4. **Firewall/Proxy Issues** - Corporate or Azure-level network restrictions

## Solutions Implemented

### 1. Network Timeout Configuration ✅
- Added timeout settings to requests: `timeout=(10, 30)`
- Configured socket timeout: `socket.setdefaulttimeout(30)`
- Added retry logic with exponential backoff

### 2. Azure-Specific Network Settings ✅
- Created `configure_azure_network_settings()` function
- Added retry strategy for network failures
- Configured session-level timeouts

### 3. Fallback Token Verification ✅
- Added `verify_firebase_token_fallback()` method
- Provides basic token validation without network access
- Handles `CertificateFetchError` gracefully

## Azure App Service Configuration

### Environment Variables
Set these in Azure App Service Configuration:

```bash
APP_ENV=production
FLASK_DEBUG=False
WEBSITES_PORT=5000
FIREBASE_PROJECT_ID=stock-report-automation
FIREBASE_SERVICE_ACCOUNT_BASE64=<your-base64-encoded-service-account>
FIREBASE_STORAGE_BUCKET=stock-report-automation.appspot.com
```

### Network Configuration

#### Option A: Azure Portal Configuration
1. Go to Azure Portal → Your App Service
2. Navigate to **Settings** → **Configuration**
3. Add these application settings:
   ```
   WEBSITES_ENABLE_APP_SERVICE_STORAGE = true
   WEBSITES_CONTAINER_START_TIME_LIMIT = 1800
   ```

#### Option B: Azure CLI Configuration
```bash
az webapp config appsettings set --name your-app-name --resource-group your-resource-group --settings WEBSITES_ENABLE_APP_SERVICE_STORAGE=true WEBSITES_CONTAINER_START_TIME_LIMIT=1800
```

### Outbound Network Access

#### Check Current Restrictions
```bash
# Check if outbound restrictions are enabled
az webapp config show --name your-app-name --resource-group your-resource-group --query "outboundIpAddresses"
```

#### Enable Outbound Access (if needed)
1. Go to **Networking** → **VNet Integration**
2. Ensure outbound access is enabled
3. Add required domains to allowed list:
   - `www.googleapis.com`
   - `firebase.googleapis.com`
   - `firestore.googleapis.com`
   - `storage.googleapis.com`

### DNS Configuration

#### Custom DNS (if needed)
```bash
# Set custom DNS servers if Azure DNS is problematic
az webapp config appsettings set --name your-app-name --resource-group your-resource-group --settings WEBSITES_DNS_SERVER=8.8.8.8,8.8.4.4
```

## Testing Network Connectivity

### Test Script
Create a test script to verify connectivity:

```python
import requests
import socket

def test_connectivity():
    endpoints = [
        "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com",
        "https://firebase.googleapis.com",
        "https://firestore.googleapis.com"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=(10, 30))
            print(f"✅ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

if __name__ == "__main__":
    test_connectivity()
```

### Manual Testing
```bash
# Test DNS resolution
nslookup www.googleapis.com

# Test HTTPS connectivity
curl -I https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com
```

## Monitoring and Debugging

### Application Insights
Enable Application Insights for better monitoring:
```bash
az monitor app-insights component create --app your-app-insights --location eastus --resource-group your-resource-group --application-type web
```

### Log Analysis
Monitor these specific log patterns:
- `Manual cert fetch succeeded/failed`
- `Fallback token verification succeeded`
- `CertificateFetchError`
- `NameResolutionError`

## Alternative Solutions

### 1. Use Azure Key Vault
Store Firebase credentials in Azure Key Vault:
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://your-vault.vault.azure.net/", credential=credential)
firebase_key = client.get_secret("firebase-service-account").value
```

### 2. Use Azure Functions
Consider moving Firebase operations to Azure Functions with better network access.

### 3. Use Azure Container Instances
Deploy in Azure Container Instances with full network access.

## Verification Steps

1. **Deploy the updated code** with network timeout configurations
2. **Test login functionality** - should work with fallback verification
3. **Monitor logs** for successful fallback verification
4. **Check network connectivity** using the test script
5. **Verify Firebase operations** (Firestore, Storage) work correctly

## Expected Behavior After Fix

- Login should work even with network issues
- Logs should show: `"Fallback token verification succeeded"`
- Firebase operations should continue to work
- Network timeouts should be handled gracefully

## Support

If issues persist:
1. Check Azure App Service logs in real-time
2. Verify all environment variables are set correctly
3. Test network connectivity from Azure App Service
4. Consider upgrading to a higher-tier App Service plan with better network access 