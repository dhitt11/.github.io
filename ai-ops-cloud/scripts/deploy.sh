#!/bin/bash

# Deployment Script for AI Ops Cloud Builder
# Deploys the application to Google Cloud Run

set -e

echo "🚀 Starting deployment to Cloud Run..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "❌ GOOGLE_CLOUD_PROJECT not set in .env"
    exit 1
fi

echo "📦 Building container image..."

# Build the container image
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/ai-ops-builder

echo "🚢 Deploying to Cloud Run..."

# Deploy to Cloud Run
gcloud run deploy ai-ops-builder \
    --image gcr.io/$GOOGLE_CLOUD_PROJECT/ai-ops-builder \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --set-env-vars="$(cat .env | grep -v '^#' | grep -v '^$' | tr '\n' ',' | sed 's/,$//')"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ai-ops-builder --platform managed --region us-central1 --format 'value(status.url)')

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📋 Setup Cloud Scheduler jobs:"
echo "1. Overnight prep (2 AM daily):"
echo "   gcloud scheduler jobs create http overnight-prep \\"
echo "     --location=us-central1 \\"
echo "     --schedule='0 2 * * *' \\"
echo "     --uri='$SERVICE_URL/workflows/overnight-prep' \\"
echo "     --http-method=POST"
echo ""
echo "2. Engagement monitoring (every 5 minutes):"
echo "   gcloud scheduler jobs create http engagement-monitor \\"
echo "     --location=us-central1 \\"
echo "     --schedule='*/5 * * * *' \\"
echo "     --uri='$SERVICE_URL/workflows/monitor-engagement' \\"
echo "     --http-method=POST"
