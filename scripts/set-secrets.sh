#!/usr/bin/env bash
# Interactively set values for the three Crawl Log secrets.
# Default targets the prod secret names. For ephemeral, pass the stack name:
#   ./scripts/set-secrets.sh AchievementIntercomStackEphemeral
# It will resolve the secret ARNs from the stack outputs.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
STACK="${1:-}"

resolve_secret_id() {
  local prod_name="$1"
  local output_key="$2"
  if [[ -z "$STACK" ]]; then
    echo "$prod_name"
    return
  fi
  aws cloudformation describe-stacks \
    --stack-name "$STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
    --output text
}

ANTHROPIC_ID=$(resolve_secret_id "achievement-intercom/anthropic-api-key" "AnthropicSecretArn")
ELEVENLABS_ID=$(resolve_secret_id "achievement-intercom/elevenlabs-api-key" "ElevenLabsSecretArn")
VOICE_ID=$(resolve_secret_id "achievement-intercom/elevenlabs-voice-id" "ElevenLabsVoiceSecretArn")

prompt_and_update() {
  local label="$1"
  local secret_id="$2"
  local current_first
  current_first=$(aws secretsmanager get-secret-value \
    --secret-id "$secret_id" --region "$REGION" \
    --query 'SecretString' --output text 2>/dev/null | head -c 12 || echo "(unreadable)")
  echo ""
  echo "$label"
  echo "  secret:   $secret_id"
  echo "  current:  ${current_first}..."
  read -r -p "  new value (blank to skip): " -s value
  echo ""
  if [[ -z "$value" ]]; then
    echo "  skipped"
    return
  fi
  aws secretsmanager update-secret \
    --secret-id "$secret_id" \
    --secret-string "$value" \
    --region "$REGION" \
    >/dev/null
  echo "  updated"
}

prompt_and_update "Anthropic API key" "$ANTHROPIC_ID"
prompt_and_update "ElevenLabs API key" "$ELEVENLABS_ID"
prompt_and_update "ElevenLabs voice ID" "$VOICE_ID"

echo ""
echo "Secrets updated. ECS only reads secrets at task start —"
echo "force a new task to pick up changes:"
if [[ -n "$STACK" ]]; then
  CLUSTER=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" --output text)
  SERVICE=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='ServiceName'].OutputValue" --output text)
  echo "  aws ecs update-service --cluster $CLUSTER --service $SERVICE --force-new-deployment --region $REGION"
else
  echo "  make redeploy-task"
fi
