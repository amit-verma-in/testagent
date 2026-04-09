output "lambda_function_name" {
  description = "Name of the intentionally misconfigured Lambda."
  value       = aws_lambda_function.vulnerable.function_name
}

output "lambda_function_url" {
  description = "Public function URL (insecure configuration)."
  value       = aws_lambda_function_url.public.function_url
}

output "warning" {
  description = "Reminder that this stack is for scanner testing only."
  value       = "This configuration is intentionally vulnerable. Do not use in production."
}
