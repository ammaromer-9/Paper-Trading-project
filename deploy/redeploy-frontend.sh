#!/bin/bash
# Run this from your own machine (needs Node/npm and AWS CLI configured).
# Builds the frontend for production, syncs it to S3 with the right cache
# headers, and invalidates CloudFront so the new build is served immediately.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_FILE="$SCRIPT_DIR/.deploy-state"

if [ ! -f "$STATE_FILE" ]; then
  echo "Missing $STATE_FILE - run this from a checkout that still has it, or recreate it from the AWS console."
  exit 1
fi
# shellcheck source=/dev/null
source "$STATE_FILE"

echo "==> Building frontend (VITE_API_URL=/api)"
cd "$REPO_ROOT/frontend"
VITE_API_URL=/api npm run build

echo "==> Syncing hashed assets (long cache)"
aws s3 sync dist/assets "s3://$S3_BUCKET_NAME/assets" \
  --cache-control "public, max-age=31536000, immutable" \
  --region "$AWS_REGION" \
  --delete

echo "==> Syncing favicon.svg (short cache)"
aws s3 cp dist/favicon.svg "s3://$S3_BUCKET_NAME/favicon.svg" \
  --cache-control "public, max-age=86400" \
  --content-type "image/svg+xml" \
  --region "$AWS_REGION"

echo "==> Syncing index.html (no-cache, so the app shell is never stale)"
aws s3 cp dist/index.html "s3://$S3_BUCKET_NAME/index.html" \
  --cache-control "no-cache" \
  --content-type "text/html" \
  --region "$AWS_REGION"

echo "==> Invalidating CloudFront cache"
aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --paths "/*" \
  --region "$AWS_REGION" \
  --query "Invalidation.{Id:Id,Status:Status}" --output json

rm -rf dist
echo "==> Done. Live at https://$CLOUDFRONT_DOMAIN_NAME/"
