#!/bin/bash

# Complete Azure Configuration Script
# This script will prompt for Firebase credentials and configure everything

set -e

echo "🚀 Azure Configuration Script for TempAutomate"
echo "=============================================="

# Configuration variables
RESOURCE_GROUP="tempautomate-rg"
APP_NAME="tempautomate-app"
FUNCTION_APP="tempautomate-functions"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first:"
    echo "   Windows: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows"
    echo "   macOS: brew install azure-cli"
    echo "   Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi

echo "✅ Azure CLI is installed and logged in"

# Prompt for Firebase configuration
echo ""
echo "📋 Firebase Configuration"
echo "========================"
echo "Please provide your Firebase service account credentials."
echo "You can get these from: https://console.firebase.google.com/"
echo "Go to Project Settings → Service accounts → Generate new private key"
echo ""

read -p "Enter your Firebase API Key: " FIREBASE_API_KEY
read -p "Enter your Firebase Project ID: " FIREBASE_PROJECT_ID
read -p "Enter your Firebase Private Key ID: " FIREBASE_PRIVATE_KEY_ID
read -p "Enter your Firebase Client Email: " FIREBASE_CLIENT_EMAIL
read -p "Enter your Firebase Client ID: " FIREBASE_CLIENT_ID
read -p "Enter your Firebase Client X509 Cert URL: " FIREBASE_CLIENT_X509_CERT_URL

echo ""
echo "Enter your Firebase Private Key (paste the entire key including BEGIN and END lines):"
echo "Press Enter when done:"
FIREBASE_PRIVATE_KEY=""
while IFS= read -r line; do
    if [[ $line == "-----END PRIVATE KEY-----" ]]; then
        FIREBASE_PRIVATE_KEY+="$line"
        break
    fi
    FIREBASE_PRIVATE_KEY+="$line"$'\n'
done

# Escape newlines in private key for Azure
FIREBASE_PRIVATE_KEY_ESCAPED=$(echo "$FIREBASE_PRIVATE_KEY" | sed 's/$/\\n/g' | tr -d '\n')

# Generate Flask secret key
echo ""
echo "🔐 Generating Flask Secret Key..."
FLASK_SECRET_KEY=$(openssl rand -hex 32)
echo "Generated Secret Key: $FLASK_SECRET_KEY"

# Get Azure resource details
echo ""
echo "📦 Getting Azure resource details..."
REDIS_HOST=$(az redis show --name "tempautomate-redis" --resource-group $RESOURCE_GROUP --query "hostName" -o tsv)
REDIS_KEY=$(az redis list-keys --name "tempautomate-redis" --resource-group $RESOURCE_GROUP --query "primaryKey" -o tsv)
STORAGE_ACCOUNT="tempautomatestorage"
STORAGE_KEY=$(az storage account keys list --account-name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --query "[0].value" -o tsv)
KEY_VAULT_NAME="tempautomate-kv"

echo "✅ Retrieved Azure resource details"

# Configure Web App settings
echo ""
echo "⚙️ Configuring Web App settings..."
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    FLASK_SECRET_KEY="$FLASK_SECRET_KEY" \
    APP_ENV="production" \
    FLASK_DEBUG="False" \
    REDIS_URL="redis://:$REDIS_KEY@$REDIS_HOST:6380/0" \
    CELERY_BROKER_URL="redis://:$REDIS_KEY@$REDIS_HOST:6380/0" \
    CELERY_RESULT_BACKEND="redis://:$REDIS_KEY@$REDIS_HOST:6380/0" \
    AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=$STORAGE_ACCOUNT;AccountKey=$STORAGE_KEY;EndpointSuffix=core.windows.net" \
    AZURE_KEY_VAULT_URL="https://$KEY_VAULT_NAME.vault.azure.net/" \
    ALLOWED_ORIGINS="https://$APP_NAME.azurewebsites.net" \
    ENABLE_MONITORING="true" \
    CELERY_WORKER_CONCURRENCY="8" \
    CELERY_TASK_TIME_LIMIT="1800" \
    WEBSITES_PORT="5000" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true" \
    PYTHON_VERSION="3.9" \
    FIREBASE_API_KEY="$FIREBASE_API_KEY" \
    FIREBASE_PROJECT_ID="$FIREBASE_PROJECT_ID" \
    FIREBASE_PRIVATE_KEY_ID="$FIREBASE_PRIVATE_KEY_ID" \
    FIREBASE_PRIVATE_KEY="$FIREBASE_PRIVATE_KEY_ESCAPED" \
    FIREBASE_CLIENT_EMAIL="$FIREBASE_CLIENT_EMAIL" \
    FIREBASE_CLIENT_ID="$FIREBASE_CLIENT_ID" \
    FIREBASE_AUTH_URI="https://accounts.google.com/o/oauth2/auth" \
    FIREBASE_TOKEN_URI="https://oauth2.googleapis.com/token" \
    FIREBASE_AUTH_PROVIDER_X509_CERT_URL="https://www.googleapis.com/oauth2/v1/certs" \
    FIREBASE_CLIENT_X509_CERT_URL="$FIREBASE_CLIENT_X509_CERT_URL"

echo "✅ Web App settings configured"

# Configure Function App settings
echo ""
echo "⚙️ Configuring Function App settings..."
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    REDIS_URL="redis://:$REDIS_KEY@$REDIS_HOST:6380/0" \
    CELERY_BROKER_URL="redis://:$REDIS_KEY@$REDIS_HOST:6380/0" \
    CELERY_RESULT_BACKEND="redis://:$REDIS_KEY@$REDIS_HOST:6380/0" \
    AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=$STORAGE_ACCOUNT;AccountKey=$STORAGE_KEY;EndpointSuffix=core.windows.net" \
    APP_ENV="production" \
    FIREBASE_API_KEY="$FIREBASE_API_KEY" \
    FIREBASE_PROJECT_ID="$FIREBASE_PROJECT_ID" \
    FIREBASE_PRIVATE_KEY_ID="$FIREBASE_PRIVATE_KEY_ID" \
    FIREBASE_PRIVATE_KEY="$FIREBASE_PRIVATE_KEY_ESCAPED" \
    FIREBASE_CLIENT_EMAIL="$FIREBASE_CLIENT_EMAIL" \
    FIREBASE_CLIENT_ID="$FIREBASE_CLIENT_ID" \
    FIREBASE_AUTH_URI="https://accounts.google.com/o/oauth2/auth" \
    FIREBASE_TOKEN_URI="https://oauth2.googleapis.com/token" \
    FIREBASE_AUTH_PROVIDER_X509_CERT_URL="https://www.googleapis.com/oauth2/v1/certs" \
    FIREBASE_CLIENT_X509_CERT_URL="$FIREBASE_CLIENT_X509_CERT_URL"

echo "✅ Function App settings configured"

# Store secrets in Key Vault
echo ""
echo "🔐 Storing secrets in Key Vault..."
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "redis-connection-string" --value "redis://:$REDIS_KEY@$REDIS_HOST:6380/0"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "storage-connection-string" --value "DefaultEndpointsProtocol=https;AccountName=$STORAGE_ACCOUNT;AccountKey=$STORAGE_KEY;EndpointSuffix=core.windows.net"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "flask-secret-key" --value "$FLASK_SECRET_KEY"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "firebase-api-key" --value "$FIREBASE_API_KEY"

echo "✅ Secrets stored in Key Vault"

# Enable managed identity for Key Vault access
echo ""
echo "🔑 Enabling managed identity..."
az webapp identity assign \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP

WEBAPP_PRINCIPAL_ID=$(az webapp identity show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "principalId" -o tsv)

az keyvault set-policy \
  --name $KEY_VAULT_NAME \
  --object-id $WEBAPP_PRINCIPAL_ID \
  --secret-permissions get list

echo "✅ Managed identity configured"

# Test the configuration
echo ""
echo "🧪 Testing configuration..."
sleep 10

echo "Testing web app..."
if curl -f https://$APP_NAME.azurewebsites.net/ > /dev/null 2>&1; then
    echo "✅ Web app is responding"
else
    echo "❌ Web app test failed - this is normal if the app hasn't been deployed yet"
fi

echo "Testing function app..."
if curl -f https://$FUNCTION_APP.azurewebsites.net/ > /dev/null 2>&1; then
    echo "✅ Function app is responding"
else
    echo "❌ Function app test failed - this is normal if the app hasn't been deployed yet"
fi

echo ""
echo "🎉 Configuration complete!"
echo "========================="
echo "🌐 Web App URL: https://$APP_NAME.azurewebsites.net"
echo "⚡ Function App URL: https://$FUNCTION_APP.azurewebsites.net"
echo "📦 Redis Host: $REDIS_HOST"
echo "💾 Storage Account: $STORAGE_ACCOUNT"
echo "🔐 Key Vault: $KEY_VAULT_NAME"
echo ""
echo "📋 Next steps:"
echo "1. Deploy your application code using: ./deploy-app.sh"
echo "2. Test all functionality"
echo "3. Configure custom domain (optional)"
echo "4. Set up monitoring and alerts"
echo ""
echo "💡 Your Flask Secret Key: $FLASK_SECRET_KEY"
echo "   (This has been stored in Azure Key Vault for security)" 