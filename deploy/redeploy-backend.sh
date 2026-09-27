#!/bin/bash
# Run this from your own machine (needs AWS CLI configured). Redeploys the
# latest code already pushed to GitHub onto the running EC2 instance, via
# SSM Run Command - no SSH involved.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="$SCRIPT_DIR/.deploy-state"

if [ ! -f "$STATE_FILE" ]; then
  echo "Missing $STATE_FILE - run this from a checkout that still has it, or recreate it from the AWS console."
  exit 1
fi
# shellcheck source=/dev/null
source "$STATE_FILE"

echo "==> Sending server-deploy.sh to run on $EC2_INSTANCE_ID via SSM"
CMD_ID=$(aws ssm send-command \
  --instance-ids "$EC2_INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["curl -fsSL https://raw.githubusercontent.com/ammaromer-9/Paper-Trading-project/paper-trading-app/deploy/server-deploy.sh -o /tmp/server-deploy.sh", "chmod +x /tmp/server-deploy.sh", "/tmp/server-deploy.sh"]' \
  --comment "Redeploy paper-trading backend" \
  --region "$AWS_REGION" \
  --query "Command.CommandId" --output text)
echo "    Command ID: $CMD_ID"

echo "==> Waiting for it to finish"
aws ssm wait command-executed --command-id "$CMD_ID" --instance-id "$EC2_INSTANCE_ID" --region "$AWS_REGION"

aws ssm get-command-invocation \
  --command-id "$CMD_ID" \
  --instance-id "$EC2_INSTANCE_ID" \
  --region "$AWS_REGION" \
  --query "{Status:Status,StdOut:StandardOutputContent}" --output json

echo "==> Verifying /api/health"
curl -s "https://$CLOUDFRONT_DOMAIN_NAME/api/health"
echo ""
