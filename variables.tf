variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region for deployment"
}

variable "bedrock_model_id" {
  type        = string
  default     = "us.amazon.nova-micro-v1:0"
  description = "Bedrock Model ID or Cross-Region Inference Profile ARN"
}