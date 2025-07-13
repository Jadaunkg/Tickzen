#!/bin/bash

# Azure Deployment Script for Sponsorship Account
# Optimized for large userbase and cost efficiency

set -e

# Configuration
RESOURCE_GROUP="tempautomate-rg"
LOCATION="East US"  # Choose closest to your users
APP_NAME="tempautomate-app"
REDIS_NAME="tempautomate-redis"
STORAGE_ACCOUNT="tempautomatestorage"
KEY_VAULT_NAME="tempautomate-kv"
FUNCTION_APP="tempautomate-functions"

echo "🚀 Starting Azure deployment for sponsorship account..."

# 1. Create Resource Group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# 2. Create Storage Account (for file uploads and static assets)
echo "💾 Creating storage account..."
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2

# 3. Create Key Vault for secrets
echo "🔐 Creating Key Vault..."
az keyvault create \
  --name $KEY_VAULT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku standard

# 4. Create Redis Cache (Basic tier for cost efficiency)
echo "📦 Creating Redis Cache..."
az redis create \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku "Basic" \
  --vm-size "C0" \
  --enable-non-ssl-port false

# 5. Create App Service Plan (P1v2 for good performance/cost ratio)
echo "📋 Creating App Service Plan..."
az appservice plan create \
  --name "${APP_NAME}-plan" \
  --resource-group $RESOURCE_GROUP \
  --sku "P1v2" \
  --is-linux \
  --number-of-workers 2

# 6. Create Web App
echo "🌐 Creating Web App..."
az webapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan "${APP_NAME}-plan" \
  --runtime "PYTHON:3.9"

# 7. Create Function App for background tasks
echo "⚡ Creating Function App..."
az functionapp create \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --plan "${APP_NAME}-plan" \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4

# 8. Get connection strings and keys
echo "🔑 Getting connection details..."
REDIS_HOST=$(az redis show --name $REDIS_NAME --resource-group $RESOURCE_GROUP --query "hostName" -o tsv)
REDIS_KEY=$(az redis list-keys --name $REDIS_NAME --resource-group $RESOURCE_GROUP --query "primaryKey" -o tsv)
STORAGE_KEY=$(az storage account keys list --account-name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --query "[0].value" -o tsv)

# 9. Store secrets in Key Vault
echo "🔐 Storing secrets in Key Vault..."
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "redis-connection-string" --value "redis://:$REDIS_KEY@$REDIS_HOST:6380/0"
az keyvault secret set --vault-name $KEY_VAULT_NAME --name "storage-connection-string" --value "DefaultEndpointsProtocol=https;AccountName=$STORAGE_ACCOUNT;AccountKey=$STORAGE_KEY;EndpointSuffix=core.windows.net"

# 10. Configure Web App settings
echo "⚙️ Configuring Web App settings..."
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    FLASK_SECRET_KEY="$(openssl rand -hex 32)" \
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
    PYTHON_VERSION="3.9"

# 11. Configure Function App settings
echo "⚙️ Configuring Function App settings..."
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    REDIS_URL="redis://:$REDIS_KEY@$REDIS_HOST:6380/0" \
    CELERY_BROKER_URL="redis://:$REDIS_KEY@$REDIS_HOST:6380/0" \
    CELERY_RESULT_BACKEND="redis://:$REDIS_KEY@$REDIS_HOST:6380/0" \
    AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=$STORAGE_ACCOUNT;AccountKey=$STORAGE_KEY;EndpointSuffix=core.windows.net" \
    APP_ENV="production"

# 12. Enable managed identity for Key Vault access
echo "🔑 Enabling managed identity..."
az webapp identity assign \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP

WEBAPP_PRINCIPAL_ID=$(az webapp identity show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "principalId" -o tsv)

az keyvault set-policy \
  --name $KEY_VAULT_NAME \
  --object-id $WEBAPP_PRINCIPAL_ID \
  --secret-permissions get list

# 13. Configure scaling rules
echo "📈 Configuring auto-scaling..."
az monitor autoscale create \
  --resource-group $RESOURCE_GROUP \
  --resource "${APP_NAME}-plan" \
  --resource-type "Microsoft.Web/serverfarms" \
  --name "${APP_NAME}-autoscale" \
  --min-count 1 \
  --max-count 10 \
  --count 2

az monitor autoscale rule create \
  --resource-group $RESOURCE_GROUP \
  --autoscale-name "${APP_NAME}-autoscale" \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 1

az monitor autoscale rule create \
  --resource-group $RESOURCE_GROUP \
  --autoscale-name "${APP_NAME}-autoscale" \
  --condition "Percentage CPU < 30 avg 5m" \
  --scale in 1

echo "✅ Infrastructure deployment complete!"
echo "🌐 Web App URL: https://$APP_NAME.azurewebsites.net"
echo "⚡ Function App URL: https://$FUNCTION_APP.azurewebsites.net"
echo "📦 Redis Host: $REDIS_HOST"
echo "💾 Storage Account: $STORAGE_ACCOUNT"
echo "🔐 Key Vault: $KEY_VAULT_NAME" 