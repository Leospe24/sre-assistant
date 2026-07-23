import base64
import gzip
import json
import os
import urllib.request
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Load environment variables (locally from .env, in Lambda from environment configuration)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # In AWS Lambda, environment variables are injected natively by the runtime


def get_bedrock_client():
    """Initializes and returns the boto3 bedrock-runtime client using AWS Default Credentials."""
    # Check TARGET_REGION first, then reserved AWS_REGION, default to us-east-1
    region = os.getenv("TARGET_REGION") or os.getenv("AWS_REGION", "us-east-1")
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
    )


def send_slack_alert(diagnosis: str, raw_log: str) -> bool:
    """Formats and posts the AI diagnostic report to Slack via Incoming Webhook."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url or "hooks.slack.com" not in webhook_url:
        print("[Slack Alert Warning]: SLACK_WEBHOOK_URL not set or invalid")
        return False

    # Build Slack Block Kit Payload
    slack_payload = {
        "text": "🚨 *SRE Assistant Incident Report*",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 SRE Assistant Incident Diagnostic",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Raw Log Payload:*\n```\n{raw_log.strip()}\n```",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Diagnosis & Remediation Plan:*\n{diagnosis}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🤖 *Powered by Amazon Bedrock Converse API* | AWS AIOps Pipeline",
                    }
                ],
            },
        ],
    }

    data = json.dumps(slack_payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("✅ [Slack Alert]: Diagnostic report sent successfully to Slack!")
                return True
            else:
                print(f"⚠️ [Slack Alert Failed]: HTTP Status {response.status}")
                return False
    except Exception as e:
        print(f"❌ [Slack Alert Error]: {str(e)}")
        return False


def diagnose_log(raw_log: str) -> str:
    """Analyzes a raw CloudWatch log using Amazon Bedrock's Converse API."""
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-micro-v1:0")

    try:
        client = get_bedrock_client()
    except Exception as e:
        return f"[sre-assistant Error]: Failed to initialize AWS Bedrock Client: {str(e)}"

    system_prompts = [
        {
            "text": (
                "You are an expert SRE Assistant specializing in AWS cloud infrastructure. "
                "Analyze raw CloudWatch log errors and return a structured Markdown response containing:\n"
                "1. **Root Cause**: Concise explanation (max 2 sentences).\n"
                "2. **Severity**: Classify as [LOW, MEDIUM, HIGH, CRITICAL].\n"
                "3. **Remediation**: Copy-pasteable AWS CLI or Linux bash commands to resolve the issue."
            )
        }
    ]

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": f"Analyze the following CloudWatch log error:\n\n```text\n{raw_log}\n```"
                }
            ],
        }
    ]

    try:
        response = client.converse(
            modelId=model_id,
            messages=messages,
            system=system_prompts,
            inferenceConfig={"temperature": 0.1, "maxTokens": 1000},
        )

        output_message = response["output"]["message"]
        return output_message["content"][0]["text"]

    except ClientError as error:
        error_code = error.response["Error"]["Code"]
        error_msg = error.response["Error"]["Message"]
        return f"[AWS ClientError - {error_code}]: {error_msg}"
    except BotoCoreError as error:
        return f"[BotoCoreError]: {str(error)}"


def lambda_handler(event, context):
    """
    AWS Lambda Execution Handler.
    
    Extracts log payload from incoming CloudWatch Logs (base64/gzipped)
    or standard JSON event trigger, runs Bedrock diagnosis, and sends Slack alert.
    """
    print(f"📥 Received Lambda Event: {json.dumps(event)}")

    if not isinstance(event, dict):
        event = {"raw_log": str(event)}

    raw_log = ""

    # Case 1: Triggered directly by CloudWatch Logs Subscription Filter (Gzipped + Base64)
    if "awslogs" in event and "data" in event["awslogs"]:
        try:
            compressed_payload = base64.b64decode(event["awslogs"]["data"])
            uncompressed_payload = gzip.decompress(compressed_payload)
            log_data = json.loads(uncompressed_payload)

            log_events = log_data.get("logEvents", [])
            extracted_messages = [e.get("message", "") for e in log_events]
            raw_log = "\n".join(extracted_messages)
        except Exception as e:
            raw_log = f"Error decompressing CloudWatch logs payload: {str(e)}"

    # Case 2: Custom JSON payload or direct string input
    elif "raw_log" in event:
        raw_log = event["raw_log"]
    else:
        raw_log = str(event)

    # Safety truncation cap (max 4,000 chars) to prevent prompt token limit overflow
    MAX_LOG_LENGTH = 4000
    if len(raw_log) > MAX_LOG_LENGTH:
        raw_log = raw_log[:MAX_LOG_LENGTH] + "\n... [Truncated remaining log payload for analysis]"

    print(f"🔍 Extracted Raw Log Payload:\n{raw_log}")

    # 1. Run AI Diagnosis
    diagnosis = diagnose_log(raw_log)

    # 2. Dispatch Slack Alert
    slack_sent = send_slack_alert(diagnosis, raw_log)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "SRE Assistant processing complete",
                "slack_sent": slack_sent,
                "diagnosis": diagnosis,
            }
        ),
    }


if __name__ == "__main__":
    # Local Test Execution simulating a Lambda Event Call
    sample_event = {
        "raw_log": """
2026-07-22 19:30:12 [ERROR] AWS_RDS_CONN_REFUSED: Failed to connect to PostgreSQL database at db.prod.internal:5432.
Traceback (most recent call last):
  File "/app/backend/db.py", line 42, in connect
    self.pool = psycopg2.connect(dsn)
psycopg2.OperationalError: fatal: password authentication failed for user "app_admin"
        """
    }

    print("=" * 60)
    print(" 🛠️  [sre-assistant] Running Phase 3 Lambda Handler Local Test ")
    print("=" * 60)

    # Simulate Lambda execution
    result = lambda_handler(sample_event, None)

    print("\n" + "=" * 60)
    print(" 📤 Lambda Handler Output Payload:")
    print("=" * 60)
    print(json.dumps(result, indent=2))