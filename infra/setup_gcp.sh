#!/bin/bash
# ============================================================
# CampaignOS — GCP Setup Script
# Run this ONCE to configure your GCP project
# Usage: chmod +x setup_gcp.sh && ./setup_gcp.sh
# ============================================================

set -e  # Exit on any error

# ── CONFIG — edit these ─────────────────────────────────────
PROJECT_ID="your-gcp-project-id"          # <-- change this
REGION="us-central1"
SERVICE_ACCOUNT_NAME="campaignos-sa"
GCS_BUCKET="${PROJECT_ID}-campaignos"
BIGQUERY_DATASET="campaignos"
# ────────────────────────────────────────────────────────────

echo "🚀 Setting up CampaignOS on GCP project: $PROJECT_ID"

# 1. Set active project
gcloud config set project $PROJECT_ID
gcloud config set compute/region $REGION

# 2. Enable required APIs
echo "📡 Enabling APIs..."
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  analyticsdata.googleapis.com \
  firestore.googleapis.com

# 3. Create service account
echo "👤 Creating service account..."
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --display-name="CampaignOS Service Account" \
  --description="Runs all CampaignOS ADK agents"

SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# 4. Grant IAM roles
echo "🔐 Granting IAM roles..."
ROLES=(
  "roles/aiplatform.user"
  "roles/bigquery.dataEditor"
  "roles/bigquery.jobUser"
  "roles/storage.objectAdmin"
  "roles/secretmanager.secretAccessor"
  "roles/datastore.user"
  "roles/run.invoker"
)
for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE" --quiet
  echo "  ✓ $ROLE"
done

# 5. Create GCS bucket
echo "🪣 Creating GCS bucket: $GCS_BUCKET"
gcloud storage buckets create gs://$GCS_BUCKET \
  --location=$REGION \
  --uniform-bucket-level-access

# Create folder structure in bucket
echo "placeholder" | gcloud storage cp - gs://$GCS_BUCKET/brand/brand_guidelines.md
echo "placeholder" | gcloud storage cp - gs://$GCS_BUCKET/briefs/.keep
echo "placeholder" | gcloud storage cp - gs://$GCS_BUCKET/assets/.keep

# 6. Create BigQuery dataset + tables
echo "📊 Creating BigQuery dataset and tables..."
bq mk --dataset \
  --location=$REGION \
  --description="CampaignOS campaign data" \
  ${PROJECT_ID}:${BIGQUERY_DATASET}

# Campaigns table
bq mk --table ${BIGQUERY_DATASET}.campaigns \
  schemas/bq_campaigns.json

# Channel benchmarks table
bq mk --table ${BIGQUERY_DATASET}.channel_benchmarks \
  schemas/bq_channel_benchmarks.json

# Fan truths table
bq mk --table ${BIGQUERY_DATASET}.fan_truths \
  schemas/bq_fan_truths.json

# Audit log table
bq mk --table ${BIGQUERY_DATASET}.audit_log \
  schemas/bq_audit_log.json

# 7. Create Firestore database (for pipeline session state)
echo "🔥 Creating Firestore database..."
gcloud firestore databases create \
  --location=$REGION \
  --type=firestore-native 2>/dev/null || echo "  Firestore already exists"

# 8. Create service account key for local dev
echo "🔑 Creating local dev credentials..."
gcloud iam service-accounts keys create \
  ./campaignos-sa-key.json \
  --iam-account=$SA_EMAIL
echo "  Key saved to: campaignos-sa-key.json"
echo "  ⚠️  Add this to .gitignore — never commit it!"

# 9. Store secrets in Secret Manager
echo "🔒 Creating Secret Manager secrets (empty — fill these in)..."
SECRET_NAMES=(
  "ga4-property-id"
  "google-ads-developer-token"
  "google-ads-client-id"
  "google-ads-client-secret"
  "google-ads-refresh-token"
  "google-ads-customer-id"
  "meta-access-token"
)
for SECRET in "${SECRET_NAMES[@]}"; do
  echo -n "placeholder" | gcloud secrets create $SECRET \
    --data-file=- 2>/dev/null || echo "  Secret $SECRET already exists"
done

echo ""
echo "✅ GCP setup complete!"
echo ""
echo "Next steps:"
echo "  1. Upload your brand_guidelines.md to:"
echo "     gs://$GCS_BUCKET/brand/brand_guidelines.md"
echo "  2. Fill in real values for secrets:"
echo "     gcloud secrets versions add ga4-property-id --data-file=-"
echo "  3. Set GOOGLE_APPLICATION_CREDENTIALS in your .env:"
echo "     GOOGLE_APPLICATION_CREDENTIALS=./campaignos-sa-key.json"
echo "  4. Run: cd backend && pip install -r requirements.txt"
echo ""
echo "Project: $PROJECT_ID"
echo "Bucket:  gs://$GCS_BUCKET"
echo "SA:      $SA_EMAIL"
