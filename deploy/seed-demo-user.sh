#!/bin/bash
# Runs ON the EC2 instance (via SSM Run Command). Creates a demo account
# via the running API so there's something to log into for interviews.
# Safe to run more than once - a 409 (already exists) is not an error.
set -euo pipefail

REGION="us-east-1"
DEMO_EMAIL="demo@papertrading.app"

export DEMO_EMAIL
export DEMO_PASSWORD
DEMO_PASSWORD=$(aws ssm get-parameter --name "/paper-trading/prod/DEMO_PASSWORD" --with-decryption --region "$REGION" --query "Parameter.Value" --output text)

PAYLOAD_FILE=$(mktemp)
chmod 600 "$PAYLOAD_FILE"
python3 -c "import json, os; print(json.dumps({'email': os.environ['DEMO_EMAIL'], 'password': os.environ['DEMO_PASSWORD']}))" > "$PAYLOAD_FILE"

status=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost/api/signup \
  -H "Content-Type: application/json" \
  --data-binary "@$PAYLOAD_FILE")

rm -f "$PAYLOAD_FILE"
unset DEMO_PASSWORD

if [ "$status" == "201" ]; then
  echo "Demo user created."
elif [ "$status" == "409" ]; then
  echo "Demo user already exists - nothing to do."
else
  echo "Unexpected response code from /api/signup: $status"
  exit 1
fi
