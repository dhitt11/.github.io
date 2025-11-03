#!/bin/bash

# Google Cloud Platform Setup Script
# This script sets up the necessary GCP resources for the AI Ops Cloud Builder

set -e

echo "🚀 Starting GCP setup..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    echo "   Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID from user or .env
if [ -f .env ]; then
    source .env
    PROJECT_ID=$GOOGLE_CLOUD_PROJECT
else
    read -p "Enter your GCP Project ID: " PROJECT_ID
fi

echo "📦 Setting up project: $PROJECT_ID"

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    firestore.googleapis.com \
    storage-api.googleapis.com \
    cloudscheduler.googleapis.com

# Create Firestore database (if not exists)
echo "💾 Setting up Firestore..."
gcloud firestore databases create --location=us-central1 || echo "Firestore already exists"

# Create Cloud Storage buckets
echo "📦 Creating Cloud Storage buckets..."
gsutil mb -l us-central1 gs://${GCS_BUCKET_RAW:-ai-ops-raw-videos} || echo "Raw bucket already exists"
gsutil mb -l us-central1 gs://${GCS_BUCKET_PROCESSED:-ai-ops-processed-videos} || echo "Processed bucket already exists"

# Set bucket permissions
echo "🔐 Setting bucket permissions..."
gsutil iam ch allUsers:objectViewer gs://${GCS_BUCKET_PROCESSED:-ai-ops-processed-videos}

echo "✅ GCP setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Fill in your API keys and credentials"
echo "3. Run ./scripts/deploy.sh to deploy the application"
