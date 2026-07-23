terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. Fetch Slack Webhook URL securely from AWS SSM Parameter Store
data "aws_ssm_parameter" "slack_webhook" {
  name            = "/sre-assistant/slack_webhook_url"
  with_decryption = true
}

# 2. AWS Lambda Function Definition
resource "aws_lambda_function" "sre_assistant" {
  filename         = "lambda_payload.zip"
  function_name    = "sre-assistant"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256
  source_code_hash = filebase64sha256("lambda_payload.zip")

  environment {
    variables = {
      BEDROCK_MODEL_ID  = var.bedrock_model_id
      SLACK_WEBHOOK_URL = data.aws_ssm_parameter.slack_webhook.value
    }
  }
}

output "lambda_function_arn" {
  value       = aws_lambda_function.sre_assistant.arn
  description = "The ARN of the deployed SRE Assistant Lambda function"
}