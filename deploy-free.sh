#!/bin/bash
# ============================================
# TickZen FREE Deployment Script (Unix/Mac/Git Bash)
# Deploys Flask to Firebase Cloud Run (FREE!)
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   TickZen Flask FREE Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}ERROR: gcloud CLI not found!${NC}"
    echo ""
    echo "Please install Google Cloud SDK:"
    echo "https://cloud.google.com/sdk/docs/install"
    echo ""
    exit 1
fi

# Check if firebase is installed
if ! command -v firebase &> /dev/null; then
    echo -e "${YELLOW}WARNING: Firebase CLI not found!${NC}"
    echo "Installing Firebase CLI..."
    npm install -g firebase-tools
fi

echo "Current directory: $(pwd)"
echo ""

# Configuration
PROJECT_ID="tickzen-a5f89"
SERVICE_NAME="tickzen-flask-portal"
REGION="us-central1"

echo -e "${GREEN}Configuration:${NC}"
echo "  Project: $PROJECT_ID"
echo "  Service: $SERVICE_NAME"
echo "  Region: $REGION"
echo ""

# Confirm deployment
read -p "Deploy Flask to Cloud Run? This is 100% FREE! (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} Step 1: Setting up Firebase project${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

firebase use $PROJECT_ID

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} Step 2: Deploying to Cloud Run (FREE!)${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 3 \
  --min-instances 0 \
  --project $PROJECT_ID \
  --quiet

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} Getting service URL...${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Deployment Complete! (FREE!)${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${GREEN}Service URL: $SERVICE_URL${NC}"
echo ""
echo "Next steps:"
echo "  1. Update Next.js firebase.json with Flask routes"
echo "  2. Deploy Next.js hosting configuration"
echo "  3. Test your application"
echo ""
echo -e "${YELLOW}Your Flask app is now running on Cloud Run's FREE tier!${NC}"
echo "  - 2 million requests/month FREE"
echo "  - No credit card required"
echo ""
echo "View logs:"
echo "  gcloud run services logs tail $SERVICE_NAME --region $REGION"
echo ""
