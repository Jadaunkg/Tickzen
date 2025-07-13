#!/bin/bash

# Application Deployment Script for Azure
# This script deploys the Flask app and Azure Functions

set -e

RESOURCE_GROUP="tempautomate-rg"
APP_NAME="tempautomate-app"
FUNCTION_APP="tempautomate-functions"

echo "🚀 Deploying application to Azure..."

# 1. Deploy Flask Web App
echo "📦 Deploying Flask Web App..."

# Create deployment package
echo "📦 Creating deployment package..."
zip -r tempautomate-web.zip . \
  -x "*.git*" \
  -x "*.env*" \
  -x "__pycache__/*" \
  -x "*.pyc" \
  -x "azure-functions/*" \
  -x "logs/*" \
  -x "generated_data/*" \
  -x "*.log" \
  -x "node_modules/*" \
  -x ".vscode/*"

# Deploy to Azure App Service
echo "🌐 Deploying to Azure App Service..."
az webapp deployment source config-zip \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --src tempautomate-web.zip

# 2. Deploy Azure Functions
echo "⚡ Deploying Azure Functions..."

# Create functions deployment package
echo "📦 Creating functions package..."
cd azure-functions
zip -r ../tempautomate-functions.zip . \
  -x "*.git*" \
  -x "__pycache__/*" \
  -x "*.pyc"

cd ..

# Deploy to Azure Functions
echo "⚡ Deploying to Azure Functions..."
az functionapp deployment source config-zip \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --src tempautomate-functions.zip

# 3. Configure Firebase environment variables
echo "🔥 Configuring Firebase environment variables..."

# You'll need to manually add these via Azure Portal or CLI
echo "⚠️  IMPORTANT: Add Firebase environment variables manually:"
echo "   - FIREBASE_API_KEY"
echo "   - FIREBASE_PROJECT_ID"
echo "   - FIREBASE_PRIVATE_KEY_ID"
echo "   - FIREBASE_PRIVATE_KEY"
echo "   - FIREBASE_CLIENT_EMAIL"
echo "   - FIREBASE_CLIENT_ID"
echo "   - FIREBASE_AUTH_URI"
echo "   - FIREBASE_TOKEN_URI"
echo "   - FIREBASE_AUTH_PROVIDER_X509_CERT_URL"
echo "   - FIREBASE_CLIENT_X509_CERT_URL"

# 4. Test deployment
echo "🧪 Testing deployment..."

# Wait for deployment to complete
sleep 30

# Test web app
echo "🌐 Testing web app..."
curl -f https://$APP_NAME.azurewebsites.net/ || echo "❌ Web app test failed"

# Test function app
echo "⚡ Testing function app..."
curl -f https://$FUNCTION_APP.azurewebsites.net/ || echo "❌ Function app test failed"

# 5. Cleanup
echo "🧹 Cleaning up..."
rm -f tempautomate-web.zip tempautomate-functions.zip

echo "✅ Application deployment complete!"
echo "🌐 Web App: https://$APP_NAME.azurewebsites.net"
echo "⚡ Function App: https://$FUNCTION_APP.azurewebsites.net"
echo ""
echo "📋 Next steps:"
echo "1. Add Firebase environment variables in Azure Portal"
echo "2. Configure custom domain (optional)"
echo "3. Set up monitoring and alerts"
echo "4. Test all functionality" 