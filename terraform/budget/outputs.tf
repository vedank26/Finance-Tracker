output "budget_name" {
  description = "Name of the provisioned AWS Budgets cost guardrail"
  value       = aws_budgets_budget.monthly_cost.name
}

output "alerts_sns_topic_arn" {
  description = "ARN of the SNS topic receiving cost alert notifications"
  value       = aws_sns_topic.alerts.arn
}

output "budget_limit_usd" {
  description = "Configured monthly limit in USD"
  value       = aws_budgets_budget.monthly_cost.limit_amount
}
