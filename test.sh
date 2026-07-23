#!/usr/bin/env bash
set -e

# ==============================================================================
# SRE Assistant Test Runner Script
# Usage:
#   ./test.sh local    - Run Lambda handler locally using virtualenv & .env
#   ./test.sh cloud    - Invoke deployed AWS Lambda function using test-event.json
#   ./test.sh check-ssm - Check if SSM parameter exists in AWS
# ==============================================================================

PROFILE="devops-admin"
REGION="us-east-1"
FUNCTION_NAME="sre-assistant"
SSM_PARAM_NAME="/sre-assistant/slack_webhook_url"

MODE=${1:-local}

case "$MODE" in
  local)
    echo "🚀 Running SRE Assistant local test..."
    if [ -f ".venv/bin/python" ]; then
        .venv/bin/python app.py
    else
        python3 app.py
    fi
    ;;

  cloud)
    echo "☁️ Invoking AWS Lambda function ($FUNCTION_NAME)..."
    AWS_PROFILE=$PROFILE aws lambda invoke \
      --function-name "$FUNCTION_NAME" \
      --payload fileb://test-event.json \
      --region "$REGION" \
      response.json

    echo -e "\n📩 Response from AWS Lambda:"
    cat response.json
    echo ""
    ;;

  check-ssm)
    echo "🔍 Checking SSM Parameter Store for $SSM_PARAM_NAME..."
    if AWS_PROFILE=$PROFILE aws ssm get-parameter --name "$SSM_PARAM_NAME" --region "$REGION" >/dev/null 2>&1; then
        echo "✅ SSM Parameter '$SSM_PARAM_NAME' exists in AWS!"
    else
        echo "❌ SSM Parameter '$SSM_PARAM_NAME' does NOT exist."
    fi
    ;;

  *)
    echo "Usage: ./test.sh [local|cloud|check-ssm]"
    exit 1
    ;;
esac
