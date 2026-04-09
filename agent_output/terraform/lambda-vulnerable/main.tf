# -----------------------------------------------------------------------------
# INTENTIONALLY VULNERABLE Terraform — for security / IaC scanner testing only.
# Do not deploy to production. Contains misconfigurations by design.
# -----------------------------------------------------------------------------

terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 7.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4.0, < 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  name = var.project_name
}

# Overly permissive trust policy is acceptable for Lambda execution role,
# but the inline policy below is dangerously broad.
resource "aws_iam_role" "lambda_exec" {
  name = "${local.name}-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Misconfiguration: full admin-equivalent access (wildcard action + resource).
resource "aws_iam_role_policy" "overprivileged" {
  name = "${local.name}-wildcard-admin"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "InsecureFullAccess"
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = 0 # Misconfiguration: infinite retention / cost & compliance risk
}

resource "aws_lambda_function" "vulnerable" {
  function_name = local.name
  role            = aws_iam_role.lambda_exec.arn
  handler         = "index.handler"
  # Misconfiguration: end-of-life / deprecated runtime (scanners flag this).
  runtime     = "nodejs16.x"
  memory_size = 128
  timeout     = 900

  filename = data.archive_file.placeholder.output_path

  environment {
    variables = {
      # Misconfiguration: secrets and credentials in plain environment variables.
      API_KEY              = ""
      DATABASE_PASSWORD    = ""
      AWS_ACCESS_KEY_ID     = ""
      AWS_SECRET_ACCESS_KEY = ""
      DEBUG                 = "true"
    }
  }

  depends_on = [aws_iam_role_policy.overprivileged, aws_cloudwatch_log_group.lambda]
}

data "archive_file" "placeholder" {
  type        = "zip"
  output_path = "${path.module}/.build/placeholder.zip"

  source {
    content  = <<-EOT
      exports.handler = async () => ({ statusCode: 200, body: 'ok' });
    EOT
    filename = "index.js"
  }
}

# Misconfiguration: public Function URL with no IAM auth (anonymous invoke).
resource "aws_lambda_function_url" "public" {
  function_name      = aws_lambda_function.vulnerable.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = true
    allow_origins     = ["*"]
    allow_methods     = ["*"]
    allow_headers     = ["*"]
  }
}

resource "aws_lambda_permission" "url_public_invoke" {
  statement_id  = "AllowPublicUrlInvoke"
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.vulnerable.function_name
  principal     = "*"
}
