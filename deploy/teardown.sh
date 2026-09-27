#!/bin/bash
# Deletes every paper-trading AWS resource, in dependency order. Destructive
# and irreversible except where a final RDS snapshot is taken. Run this from
# your own machine (needs AWS CLI configured).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="$SCRIPT_DIR/.deploy-state"

if [ ! -f "$STATE_FILE" ]; then
  echo "Missing $STATE_FILE - nothing to tear down, or it was already removed."
  exit 1
fi
# shellcheck source=/dev/null
source "$STATE_FILE"

echo "This will permanently delete every paper-trading AWS resource:"
echo "  - CloudFront distribution $CLOUDFRONT_DISTRIBUTION_ID and its function"
echo "  - S3 bucket $S3_BUCKET_NAME (and everything in it)"
echo "  - EC2 instance $EC2_INSTANCE_ID and Elastic IP $EIP_PUBLIC_IP"
echo "  - RDS instance $RDS_INSTANCE_ID"
echo "  - Security groups, IAM role/instance profile"
echo "  - All SSM parameters under /paper-trading/prod/"
echo ""
read -r -p "Type the project name (paper-trading) to confirm: " CONFIRM
if [ "$CONFIRM" != "paper-trading" ]; then
  echo "Confirmation did not match. Aborting - nothing was deleted."
  exit 1
fi

read -r -p "Take a final RDS snapshot before deleting the database? [y/N] " SNAPSHOT_ANSWER

echo ""
echo "==> 1/9 Disabling and deleting CloudFront distribution (this is the slow step, ~15 min)"
ETAG=$(aws cloudfront get-distribution-config --id "$CLOUDFRONT_DISTRIBUTION_ID" --region "$AWS_REGION" --query "ETag" --output text)
CONFIG=$(aws cloudfront get-distribution-config --id "$CLOUDFRONT_DISTRIBUTION_ID" --region "$AWS_REGION" --query "DistributionConfig" --output json)
echo "$CONFIG" | python3 -c "import json,sys; c=json.load(sys.stdin); c['Enabled']=False; print(json.dumps(c))" > /tmp/paper-trading-disable-config.json
aws cloudfront update-distribution \
  --id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --distribution-config file:///tmp/paper-trading-disable-config.json \
  --if-match "$ETAG" \
  --region "$AWS_REGION" > /dev/null
rm -f /tmp/paper-trading-disable-config.json

aws cloudfront wait distribution-deployed --id "$CLOUDFRONT_DISTRIBUTION_ID" --region "$AWS_REGION"

NEW_ETAG=$(aws cloudfront get-distribution-config --id "$CLOUDFRONT_DISTRIBUTION_ID" --region "$AWS_REGION" --query "ETag" --output text)
aws cloudfront delete-distribution --id "$CLOUDFRONT_DISTRIBUTION_ID" --if-match "$NEW_ETAG" --region "$AWS_REGION"

echo "==> 2/9 Deleting CloudFront Function"
FUNC_ETAG=$(aws cloudfront describe-function --name "$CLOUDFRONT_FUNCTION_NAME" --stage LIVE --region "$AWS_REGION" --query "ETag" --output text)
aws cloudfront delete-function --name "$CLOUDFRONT_FUNCTION_NAME" --if-match "$FUNC_ETAG" --region "$AWS_REGION"

echo "==> 3/9 Deleting Origin Access Control"
aws cloudfront delete-origin-access-control --id "$CLOUDFRONT_OAC_ID" --region "$AWS_REGION" || echo "    (already gone or still referenced - check manually if this failed)"

echo "==> 4/9 Emptying and deleting S3 bucket"
aws s3 rm "s3://$S3_BUCKET_NAME" --recursive --region "$AWS_REGION"
aws s3api delete-bucket --bucket "$S3_BUCKET_NAME" --region "$AWS_REGION"

echo "==> 5/9 Terminating EC2 instance and releasing Elastic IP"
aws ec2 disassociate-address --allocation-id "$EIP_ALLOCATION_ID" --region "$AWS_REGION" || true
aws ec2 terminate-instances --instance-ids "$EC2_INSTANCE_ID" --region "$AWS_REGION" > /dev/null
aws ec2 wait instance-terminated --instance-ids "$EC2_INSTANCE_ID" --region "$AWS_REGION"
aws ec2 release-address --allocation-id "$EIP_ALLOCATION_ID" --region "$AWS_REGION"

echo "==> 6/9 Deleting RDS instance"
if [[ "$SNAPSHOT_ANSWER" =~ ^[Yy]$ ]]; then
  SNAPSHOT_ID="paper-trading-db-final-$(date +%Y%m%d%H%M%S)"
  echo "    Taking final snapshot: $SNAPSHOT_ID"
  aws rds delete-db-instance \
    --db-instance-identifier "$RDS_INSTANCE_ID" \
    --final-db-snapshot-identifier "$SNAPSHOT_ID" \
    --region "$AWS_REGION" > /dev/null
else
  aws rds delete-db-instance \
    --db-instance-identifier "$RDS_INSTANCE_ID" \
    --skip-final-snapshot \
    --region "$AWS_REGION" > /dev/null
fi
aws rds wait db-instance-deleted --db-instance-identifier "$RDS_INSTANCE_ID" --region "$AWS_REGION"
aws rds delete-db-subnet-group --db-subnet-group-name "$DB_SUBNET_GROUP_NAME" --region "$AWS_REGION"

echo "==> 7/9 Deleting security groups"
aws ec2 delete-security-group --group-id "$DB_SG_ID" --region "$AWS_REGION"
aws ec2 delete-security-group --group-id "$EC2_SG_ID" --region "$AWS_REGION"

echo "==> 8/9 Deleting IAM role and instance profile"
aws iam remove-role-from-instance-profile --instance-profile-name "$IAM_INSTANCE_PROFILE_NAME" --role-name "$IAM_ROLE_NAME"
aws iam delete-instance-profile --instance-profile-name "$IAM_INSTANCE_PROFILE_NAME"
aws iam delete-role-policy --role-name "$IAM_ROLE_NAME" --policy-name paper-trading-read-secrets
aws iam detach-role-policy --role-name "$IAM_ROLE_NAME" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam delete-role --role-name "$IAM_ROLE_NAME"

echo "==> 9/9 Deleting SSM parameters"
aws ssm delete-parameters \
  --names "/paper-trading/prod/DATABASE_URL" "/paper-trading/prod/JWT_SECRET" "/paper-trading/prod/FINNHUB_API_KEY" "/paper-trading/prod/DEMO_PASSWORD" \
  --region "$AWS_REGION"

echo ""
echo "Teardown complete. You may want to remove deploy/.deploy-state now (it refers to deleted resources)."
