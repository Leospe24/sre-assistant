terraform {
  backend "s3" {
    bucket         = "sre-assistant-tf-state-308916794074"
    key            = "sre-assistant/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "sre-assistant-tf-locks"
    encrypt        = true
  }
}