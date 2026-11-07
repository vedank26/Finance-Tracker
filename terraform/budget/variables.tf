variable "aws_region" {
  type        = string
  description = "Target AWS region for cost guardrail alerts"
  default     = "ap-south-1"
}

variable "project_name" {
  type        = string
  description = "Project name prefix used for SNS topics and budget identifiers"
  default     = "finance-tracker"
}

variable "environment" {
  type        = string
  description = "Deployment environment name"
  default     = "prototype"
}

variable "budget_limit_amount" {
  type        = string
  description = "Monthly budget limit in USD. Note: At standard run-rate (~$28.78/mo), a $10 budget acts as an early 10-day prototype tripwire. Set to '30' for 24/7 monthly coverage"
  default     = "10"
}

variable "budget_alert_threshold_1" {
  type        = number
  description = "First alert threshold percentage (default 50% = $5 on a $10 budget)"
  default     = 50
}

variable "budget_alert_threshold_2" {
  type        = number
  description = "Second alert threshold percentage (default 80% = $8 on a $10 budget)"
  default     = 80
}

variable "alert_email" {
  type        = string
  description = "Email address to receive cost threshold alerts from SNS and AWS Budgets"
  default     = ""
}
