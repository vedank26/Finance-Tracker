# --- Amazon SNS Topic for Finance Tracker Alerts ---
resource "aws_sns_topic" "alerts" {
  name         = "${var.project_name}-alerts"
  display_name = "Finance Tracker Alerts"

  tags = {
    Name = "${var.project_name}-alerts"
  }
}

# --- Optional Email Subscription for Notifications ---
resource "aws_sns_topic_subscription" "email" {
  count     = var.sns_notification_email != null && var.sns_notification_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.sns_notification_email
}

# --- SNS Topic Policy Restricting Publish to CloudWatch Alarm and Account ---
resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchAlarmsToPublish"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.alerts.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
            "aws:SourceArn"     = "arn:aws:cloudwatch:${var.aws_region}:${data.aws_caller_identity.current.account_id}:alarm:${var.project_name}-ec2-high-cpu"
          }
        }
      },
      {
        Sid    = "AllowBudgetsToPublish"
        Effect = "Allow"
        Principal = {
          Service = "budgets.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.alerts.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnEquals = {
            "aws:SourceArn" = "arn:aws:budgets::${data.aws_caller_identity.current.account_id}:budget/${var.project_name}-monthly-cost-guardrail"
          }
        }
      }
    ]
  })
}
