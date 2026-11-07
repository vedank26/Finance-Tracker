# --- Application Log Group with Short Retention ---
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/${var.project_name}/app"
  retention_in_days = var.log_retention_days # MANDATORY: 7-day retention prevents perpetual storage fees

  tags = {
    Name        = "${var.project_name}-log-group"
    Environment = var.environment
  }
}

# --- CloudWatch Metric Alarm for EC2 CPU Utilization ---
resource "aws_cloudwatch_metric_alarm" "ec2_high_cpu" {
  alarm_name          = "${var.project_name}-ec2-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Triggers when EC2 instance CPU exceeds 80% for 10 minutes"

  dimensions = {
    InstanceId = aws_instance.app.id
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : [aws_sns_topic.alerts.arn]
  ok_actions    = var.sns_topic_arn != null ? [var.sns_topic_arn] : [aws_sns_topic.alerts.arn]

  tags = {
    Name = "${var.project_name}-cpu-alarm"
  }
}
