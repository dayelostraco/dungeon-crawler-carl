#!/usr/bin/env bash
# Captures orphan resource identifiers before destroying the prod stack.
# Writes .cdk-orphans.json which `make revive` reads to re-attach the
# RETAIN'd DynamoDB table + S3 bucket via `cdk import`.
#
# Run automatically by `make destroy-prod`. Safe to re-run while the
# stack is still up — it overwrites the file with current values.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
STACK="${STACK:-AchievementIntercomStack}"
OUT="${OUT:-.cdk-orphans.json}"

if ! aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
    >/dev/null 2>&1; then
  echo "Stack $STACK not found in $REGION."
  if [[ -f "$OUT" ]]; then
    echo "Existing $OUT preserved (last known orphan identifiers)."
    exit 0
  fi
  echo "No existing $OUT either. Cannot capture orphan identifiers."
  exit 1
fi

TABLE_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='TableName'].OutputValue" --output text)
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)

if [[ -z "$TABLE_NAME" || "$TABLE_NAME" == "None" ]] || \
   [[ -z "$BUCKET_NAME" || "$BUCKET_NAME" == "None" ]]; then
  echo "Could not resolve TableName/BucketName from stack outputs."
  echo "  TableName=$TABLE_NAME"
  echo "  BucketName=$BUCKET_NAME"
  exit 1
fi

# Synthesize the prod template to find current CFN logical IDs.
# These stay stable across deploys as long as the construct paths don't change.
( cd cdk && JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 \
  cdk synth "$STACK" --context mode=prod --context account="${AWS_ACCOUNT:-302654592899}" \
    --context region="$REGION" --quiet ) >/dev/null

TEMPLATE="cdk/cdk.out/$STACK.template.json"
TABLE_LID=$(jq -r '.Resources | to_entries
  | map(select(.value.Type == "AWS::DynamoDB::Table"))
  | .[0].key' "$TEMPLATE")
BUCKET_LID=$(jq -r '.Resources | to_entries
  | map(select(.value.Type == "AWS::S3::Bucket"))
  | .[0].key' "$TEMPLATE")

if [[ -z "$TABLE_LID" || "$TABLE_LID" == "null" ]] || \
   [[ -z "$BUCKET_LID" || "$BUCKET_LID" == "null" ]]; then
  echo "Could not resolve logical IDs from synthesized template."
  echo "  TABLE_LID=$TABLE_LID"
  echo "  BUCKET_LID=$BUCKET_LID"
  exit 1
fi

cat > "$OUT" <<EOF
{
  "$TABLE_LID": { "TableName": "$TABLE_NAME" },
  "$BUCKET_LID": { "BucketName": "$BUCKET_NAME" }
}
EOF

echo "Saved $OUT:"
cat "$OUT"
echo ""
echo "Commit this file so 'make revive' has the identifiers after a fresh clone."
