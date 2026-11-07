# --- AWS Budgets Monthly Cost Guardrail ---
# NOTE: AWS Budgets is an advisory alerting tool and NOT a hard spending cap.
# It does NOT automatically terminate or modify resources.

resource "aws_budgets_budget" "monthly_cost" {
  name         = "${var.project_name}-monthly-cost-guardrail"
  budget_type  = "COST"
  limit_amount = var.budget_limit_amount
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Alert Threshold 1 (e.g. 50% = $5.00 on $10 budget)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.budget_alert_threshold_1
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_sns_topic_arns  = [aws_sns_topic.alerts.arn]
    subscriber_email_addresses = []
  }

  # Alert Threshold 2 (e.g. 80% = $8.00 on $10 budget)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.budget_alert_threshold_2
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_sns_topic_arns  = [aws_sns_topic.alerts.arn]
    subscriber_email_addresses = []
  }
}
