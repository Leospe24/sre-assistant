# 1. GitHub OIDC Provider
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# 2. IAM Role for GitHub Actions
resource "aws_iam_role" "github_actions_role" {
  name = "github-actions-sre-assistant-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            # Wildcard * at the start and end ensures pushes, PRs, and manual workflow_dispatch runs pass
            "token.actions.githubusercontent.com:sub" = [
              "repo:Leospe24/sre-assistant:*",
              "repo:leospe24/sre-assistant:*"
            ]
          }
        }
      }
    ]
  })
}

# 3. Attach AdministratorAccess or required policies
resource "aws_iam_role_policy_attachment" "github_actions_admin" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "github_actions_role_arn" {
  value       = aws_iam_role.github_actions_role.arn
  description = "The ARN of the IAM Role for GitHub Actions OIDC"
}