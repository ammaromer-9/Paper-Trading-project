#!/bin/bash
# Runs ON the EC2 instance (via SSM Run Command) to deploy the backend.
# Pulls the latest code, fetches secrets from SSM Parameter Store into a
# root-only env file, builds the Docker image, and (re)starts the container.
set -euo pipefail

APP_DIR="/opt/paper-trading"
REPO_URL="https://github.com/ammaromer-9/Paper-Trading-project.git"
BRANCH="paper-trading-app"
ENV_FILE="/opt/paper-trading/backend/.env.prod"
REGION="us-east-1"

echo "==> Syncing code into $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  cd "$APP_DIR"
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
  git reset --hard "origin/$BRANCH"
else
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

echo "==> Fetching secrets from SSM Parameter Store into a root-only env file"
umask 077
: > "$ENV_FILE"
for name in DATABASE_URL JWT_SECRET FINNHUB_API_KEY; do
  value=$(aws ssm get-parameter --name "/paper-trading/prod/$name" --with-decryption --region "$REGION" --query "Parameter.Value" --output text)
  echo "${name}=${value}" >> "$ENV_FILE"
done
chmod 600 "$ENV_FILE"
chown root:root "$ENV_FILE"
unset value

echo "==> Building Docker image"
cd "$APP_DIR/backend"
docker build -t paper-trading-backend .

echo "==> (Re)starting container"
docker rm -f paper-trading-backend >/dev/null 2>&1 || true
docker run -d \
  --name paper-trading-backend \
  --restart unless-stopped \
  --env-file "$ENV_FILE" \
  -p 80:8000 \
  paper-trading-backend

echo "==> Waiting for the container to start"
sleep 3
docker ps --filter "name=paper-trading-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo "==> Deploy finished"
