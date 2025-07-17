# Azure Deployment Troubleshooting Guide

## Error: Failed to deploy web package to App Service (409 Conflict)

### Problem Description
```
Error: Failed to deploy web package to App Service.
Error: Deployment Failed, Error: Failed to deploy web package using OneDeploy to App Service.
Conflict (CODE: 409)
```

### Root Causes
1. **Concurrent Deployments** - Multiple deployments running simultaneously
2. **File Lock Conflicts** - Files locked by running application
3. **Missing Startup Configuration** - No proper startup command for Python app
4. **Incorrect Package Structure** - Missing required Azure configuration files
5. **Azure App Service Configuration Issues** - Runtime or environment misconfiguration

### Immediate Solutions

#### 1. Stop Concurrent Deployments
```bash
# Check for running deployments in Azure Portal
# Go to: Azure Portal → App Service → Deployment Center → Logs
# Stop any running deployments before retrying
```

#### 2. Verify Azure App Service Configuration
In Azure Portal:
1. Go to **Configuration** → **General settings**
2. Ensure **Stack** is set to **Python 3.11**
3. Set **Startup Command** to: `python app/main_portal_app.py`
4. Set **Platform** to **64 Bit**
5. Set **FTP state** to **FTPS only**

#### 3. Check Required Files
Ensure these files exist in your repository root:
- ✅ `web.config` - Azure IIS configuration
- ✅ `startup.txt` - Startup command file
- ✅ `requirements.txt` - Python dependencies
- ✅ `app/main_portal_app.py` - Main application file

#### 4. Azure App Service Environment Variables
Set these in **Configuration** → **Application settings**:
```
APP_ENV=production
FLASK_DEBUG=False
WEBSITES_PORT=5000
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
WEBSITES_CONTAINER_START_TIME_LIMIT=1800
```

### Advanced Troubleshooting

#### 1. Check Azure App Service Logs
```bash
# Enable detailed logging
# Go to: Monitoring → Log stream
# Look for specific error messages during deployment
```

#### 2. Verify Network Access
```bash
# Test outbound connectivity from Azure App Service
# Go to: Development Tools → Console
# Run: curl -I https://www.googleapis.com
```

#### 3. Check File Permissions
```bash
# Ensure proper file permissions
# Azure App Service requires read access to all files
```

### Deployment Best Practices

#### 1. Pre-deployment Checklist
- [ ] Stop any running deployments
- [ ] Verify all required files are present
- [ ] Check Azure App Service configuration
- [ ] Ensure environment variables are set
- [ ] Test locally with production settings

#### 2. GitHub Actions Workflow
```yaml
# Ensure proper deployment configuration
- name: 'Deploy to Azure Web App'
  uses: azure/webapps-deploy@v3
  with:
    app-name: 'tickzen1'
    slot-name: 'Production'
    publish-profile: ${{ secrets.AZUREAPPSERVICE_PUBLISHPROFILE_xxx }}
    package: .
    startup-command: 'python app/main_portal_app.py'
```

#### 3. Package Structure
```
repository/
├── web.config              # Azure IIS configuration
├── startup.txt             # Startup command
├── requirements.txt        # Python dependencies
├── app/
│   ├── main_portal_app.py  # Main application
│   ├── static/             # Static files
│   └── templates/          # Templates
└── .github/workflows/      # GitHub Actions
```

### Alternative Solutions

#### 1. Use Azure CLI for Deployment
```bash
# Deploy using Azure CLI instead of GitHub Actions
az webapp deployment source config-zip \
  --resource-group your-resource-group \
  --name tickzen1 \
  --src release.zip
```

#### 2. Use Azure Container Registry
```dockerfile
# Create Dockerfile for containerized deployment
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app/main_portal_app.py"]
```

#### 3. Use Azure Functions
Consider migrating to Azure Functions for better scalability and deployment reliability.

### Monitoring and Prevention

#### 1. Enable Application Insights
```bash
# Enable monitoring for better error tracking
az monitor app-insights component create \
  --app tickzen-insights \
  --location eastus \
  --resource-group your-resource-group \
  --application-type web
```

#### 2. Set Up Alerts
- Configure alerts for deployment failures
- Monitor application health
- Set up error rate alerts

#### 3. Regular Maintenance
- Update dependencies regularly
- Monitor Azure App Service quotas
- Review and optimize startup time

### Support Resources
- [Azure App Service Documentation](https://docs.microsoft.com/en-us/azure/app-service/)
- [Python on Azure](https://docs.microsoft.com/en-us/azure/developer/python/)
- [GitHub Actions for Azure](https://github.com/Azure/actions)
- [Azure Support](https://azure.microsoft.com/en-us/support/)

### Contact Information
If issues persist after trying all solutions:
1. Check Azure App Service logs in real-time
2. Verify all configuration settings
3. Test deployment with minimal changes
4. Consider upgrading to a higher-tier App Service plan 