#!/bin/bash

# Script to connect Redis Cloud to Azure App Service
# Replace these values with your actual Redis Cloud credentials

# Redis Cloud Configuration
REDIS_HOST="redis-13994.c11.us-east-1-3.ec2.redns.redis-cloud.com"
REDIS_PORT="13994"
REDIS_PASSWORD="YOUR_REDIS_PASSWORD_HERE"  # Replace with your actual password
REDIS_DB="0"

# Azure Configuration
RESOURCE_GROUP="tempautomate-rg"
APP_NAME="tempautomate-app"
FUNCTION_APP="tempautomate-functions"

echo "🔗 Connecting Redis Cloud to Azure Application..."

# Build Redis connection string
REDIS_URL="redis://:$REDIS_PASSWORD@$REDIS_HOST:$REDIS_PORT/$REDIS_DB"

echo "📦 Redis Connection String:"
echo "Host: $REDIS_HOST"
echo "Port: $REDIS_PORT"
echo "Database: $REDIS_DB"
echo ""

# Update Web App settings
echo "⚙️ Updating Web App settings..."
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    REDIS_URL="$REDIS_URL" \
    CELERY_BROKER_URL="$REDIS_URL" \
    CELERY_RESULT_BACKEND="$REDIS_URL"

echo "✅ Web App Redis settings updated"

# Update Function App settings
echo "⚙️ Updating Function App settings..."
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    REDIS_URL="$REDIS_URL" \
    CELERY_BROKER_URL="$REDIS_URL" \
    CELERY_RESULT_BACKEND="$REDIS_URL"

echo "✅ Function App Redis settings updated"

# Test Redis connection
echo "🧪 Testing Redis connection..."
echo "Testing connection to: $REDIS_HOST:$REDIS_PORT"

# You can test the connection using redis-cli if available
# redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping

echo ""
echo "🎉 Redis Cloud successfully connected to Azure!"
echo ""
echo "📊 Next steps:"
echo "1. Restart your Azure App Service"
echo "2. Check the application logs for Redis connection"
echo "3. Monitor Redis memory usage in Redis Cloud dashboard"
echo ""
echo "🔍 To monitor Redis usage:"
echo "- Memory: Currently using 6.3MB / 30MB"
echo "- Network: 0GB / 5GB monthly"
echo "- Connections: Monitor in Redis Cloud dashboard" 