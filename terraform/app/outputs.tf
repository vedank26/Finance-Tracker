# --- Terraform Outputs ---

output "ec2_public_ip" {
  description = "Public IP address of the Finance Tracker application host"
  value       = var.assign_elastic_ip ? aws_eip.app[0].public_ip : aws_instance.app.public_ip
}

output "ec2_instance_id" {
  description = "EC2 instance ID (use for AWS Systems Manager Session Manager access)"
  value       = aws_instance.app.id
}

output "ssm_connect_command" {
  description = "Command to securely connect to the EC2 host terminal without opening SSH ports"
  value       = "aws ssm start-session --target ${aws_instance.app.id} --region ${var.aws_region}"
}

output "rds_address" {
  description = "Private hostname of the RDS MySQL instance"
  value       = aws_db_instance.default.address
}

output "rds_port" {
  description = "Port of the RDS MySQL instance"
  value       = aws_db_instance.default.port
}

output "s3_reports_bucket_name" {
  description = "Private S3 bucket name for monthly reports"
  value       = aws_s3_bucket.reports.id
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for application logs"
  value       = aws_cloudwatch_log_group.app_logs.name
}

output "vpc_id" {
  description = "ID of the dedicated application VPC"
  value       = aws_vpc.main.id
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic receiving Finance Tracker alert notifications"
  value       = aws_sns_topic.alerts.arn
}
