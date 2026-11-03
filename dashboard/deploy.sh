#!/usr/bin/env bash
# Builds the dashboard image (with its data snapshot) in Cloud Build and deploys it to Cloud Run.
# Export a fresh snapshot first: python dashboard/snapshot.py
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DASHBOARD_DIR="$REPO_ROOT/dashboard"
SNAPSHOT_DIR="$DASHBOARD_DIR/snapshot"
# Read only the one setting deploy needs, so .env secrets never reach gcloud's environment
CLOUD_SQL_INSTANCE="$(source "$REPO_ROOT/.env" && echo "$CLOUD_SQL_INSTANCE")"

if ! compgen -G "$SNAPSHOT_DIR/*.parquet" > /dev/null; then
  echo "No snapshot in $SNAPSHOT_DIR. Run python dashboard/snapshot.py first." >&2
  exit 1
fi

SERVICE=dashboard
PROJECT="${CLOUD_SQL_INSTANCE%%:*}"
REGION="$(cut -d: -f2 <<< "$CLOUD_SQL_INSTANCE")"
SERVICE_ACCOUNT_DOMAIN="$PROJECT.iam.gserviceaccount.com"
BUILD_SERVICE_ACCOUNT="projects/$PROJECT/serviceAccounts/dashboard-builder@$SERVICE_ACCOUNT_DOMAIN"
# Runtime identity with no roles: the dashboard only serves files baked into its image
RUNTIME_SERVICE_ACCOUNT="dashboard-runtime@$SERVICE_ACCOUNT_DOMAIN"
MEMORY=512Mi
CPU=1
MIN_INSTANCES=0
MAX_INSTANCES=2
# Matches gunicorn --threads in the Dockerfile
CONCURRENCY=8

gcloud run deploy "$SERVICE" \
  --project "$PROJECT" \
  --source "$DASHBOARD_DIR" \
  --build-service-account "$BUILD_SERVICE_ACCOUNT" \
  --service-account "$RUNTIME_SERVICE_ACCOUNT" \
  --region "$REGION" \
  --memory "$MEMORY" \
  --cpu "$CPU" \
  --cpu-boost \
  --min-instances "$MIN_INSTANCES" \
  --max-instances "$MAX_INSTANCES" \
  --concurrency "$CONCURRENCY" \
  --allow-unauthenticated
