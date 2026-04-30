#!/usr/bin/env bash
# Ensures the three Secrets Manager secrets used by the prod stack exist.
# Creates them with placeholder values if missing, leaves them alone if present.
# Run this before the first `cdk deploy` of the prod stack in a fresh account.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"

ensure_secret() {
  local name="$1"
  local description="$2"
  if aws secretsmanager describe-secret --secret-id "$name" --region "$REGION" \
      >/dev/null 2>&1; then
    echo "  ok        $name"
  else
    aws secretsmanager create-secret \
      --name "$name" \
      --description "$description" \
      --secret-string "placeholder-set-via-make-set-secrets" \
      --region "$REGION" \
      >/dev/null
    echo "  created   $name (placeholder)"
  fi
}

echo "Ensuring prod secrets in $REGION:"
ensure_secret "achievement-intercom/anthropic-api-key" "Anthropic API key for Crawl Log"
ensure_secret "achievement-intercom/elevenlabs-api-key" "ElevenLabs API key for Crawl Log"
ensure_secret "achievement-intercom/elevenlabs-voice-id" "ElevenLabs voice ID for Crawl Log"

echo ""
echo "If any were just created with placeholders, run: make set-secrets"
