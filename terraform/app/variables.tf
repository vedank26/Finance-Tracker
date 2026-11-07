variable "aws_region" {
  type        = string
  description = "Target AWS region for Finance Tracker deployment"
  default     = "ap-south-1"
}

variable "project_name" {
  type        = string
  description = "Base project name used in resource names and tags"
  default     = "finance-tracker"
}

variable "environment" {
  type        = string
  description = "Deployment environment name (e.g., prototype, staging, production)"
  default     = "prototype"
}

# --- VPC & Networking Variables ---

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the dedicated application VPC"
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  type        = string
  description = "CIDR block for the single public subnet (EC2 application host)"
  default     = "10.0.1.0/24"
}

variable "private_subnet_a_cidr" {
  type        = string
  description = "CIDR block for the first private subnet (RDS MySQL subnet group, AZ a)"
  default     = "10.0.10.0/24"
}

variable "private_subnet_b_cidr" {
  type        = string
  description = "CIDR block for the second private subnet (RDS MySQL subnet group, AZ b)"
  default     = "10.0.11.0/24"
}

variable "allowed_http_cidr_blocks" {
  type        = list(string)
  description = "CIDR blocks permitted to access HTTP (port 80)"
  default     = ["0.0.0.0/0"]
}

variable "enable_https_ingress" {
  type        = bool
  description = "Whether to open port 443 in the security group. NOTE: Enabling port 443 does NOT enable HTTPS automatically; an SSL/TLS certificate and custom domain are required"
  default     = false
}

variable "admin_ssh_cidr_blocks" {
  type        = list(string)
  description = "CIDR blocks permitted for direct SSH ingress. Kept empty by default; SSM Session Manager is preferred for keyless terminal access"
  default     = []
}

# --- Compute (EC2) Variables ---

variable "ec2_instance_type" {
  type        = string
  description = "EC2 instance type for the application container host"
  default     = "t3.micro"
}

variable "ec2_volume_size" {
  type        = number
  description = "Root GP3 EBS volume size in GB"
  default     = 20
}

variable "assign_elastic_ip" {
  type        = bool
  description = "Whether to allocate and attach an Elastic IP to the EC2 host for stable access"
  default     = true
}

# --- Database (RDS MySQL) Variables ---

variable "rds_instance_class" {
  type        = string
  description = "RDS DB instance class. Single-AZ db.t3.micro is default for cost control"
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  type        = number
  description = "Allocated storage in GB for MySQL database (GP3)"
  default     = 20
}

variable "rds_engine_version" {
  type        = string
  description = "MySQL engine major/minor version"
  default     = "8.0"
}

variable "db_name" {
  type        = string
  description = "Initial MySQL database name"
  default     = "financedb"
}

variable "db_username" {
  type        = string
  description = "Master MySQL database username"
  default     = "financeuser"
}

# REQUIRED EPHEMERAL SECRET: No default is permitted.
# Must be supplied at runtime (e.g., via TF_VAR_db_password or interactive prompt).
# Marked ephemeral so Terraform 1.11+ never persists it in state or plan files.
variable "db_password" {
  type        = string
  description = "Master database password. Marked ephemeral so it is never persisted to Terraform state or plan files. Required input (minimum 12 characters)"
  sensitive   = true
  ephemeral   = true

  validation {
    condition     = length(var.db_password) >= 12
    error_message = "The db_password must be at least 12 characters long and cannot be empty or null."
  }
}

variable "db_password_version" {
  type        = number
  description = "Version integer for password_wo. Increment to rotate the database password in AWS without state persistence"
  default     = 1
}

variable "rds_deletion_protection" {
  type        = bool
  description = "Enforces deletion protection on the RDS MySQL instance to prevent accidental loss of financial transaction data. Defaults to true (safer). NOTE: To destroy the infrastructure during prototype teardown, set this variable to false before running terraform destroy"
  default     = true
}

variable "skip_final_snapshot" {
  type        = bool
  description = "Whether to skip creating a final snapshot when destroying RDS (cost control for prototypes)"
  default     = true
}

variable "backup_retention_period" {
  type        = number
  description = "Automated backup retention in days (1 day retains daily backup within low/free tier)"
  default     = 1
}

# --- Storage (S3) Variables ---

variable "s3_bucket_name" {
  type        = string
  description = "Explicit S3 bucket name for monthly reports. If null, a globally unique name using account ID will be generated"
  default     = null
}

# --- Monitoring & Observability Variables ---

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention period in days (7 days standard to limit storage costs)"
  default     = 7
}

variable "sns_topic_arn" {
  type        = string
  description = "ARN of the budget alerts SNS topic created by the separate budget root module (terraform/budget). Links CloudWatch CPU alarms to the shared SNS notification topic"
  default     = null
}

variable "sns_notification_email" {
  type        = string
  description = "Email address for Finance Tracker CloudWatch alarm notifications (requires confirmation)"
  default     = null
}

# --- REQUIRED EPHEMERAL APPLICATION SECRETS ---

# REQUIRED EPHEMERAL SECRET: No unsafe default is permitted.
# Must be supplied at runtime (e.g., via TF_VAR_flask_secret_key).
# Prevents the application from starting publicly with a predictable known key.
variable "flask_secret_key" {
  type        = string
  description = "Flask session and CSRF secret key. Marked ephemeral to prevent state persistence. Required input (minimum 32 characters)"
  sensitive   = true
  ephemeral   = true

  validation {
    condition     = length(var.flask_secret_key) >= 32
    error_message = "The flask_secret_key must be at least 32 characters long to ensure session and CSRF cryptographic security."
  }
}

variable "flask_secret_key_version" {
  type        = number
  description = "Version integer for secret_key value_wo in SSM Parameter Store"
  default     = 1
}

variable "gemini_api_key" {
  type        = string
  description = "Google Gemini Flash API key. Optional variable; if empty string, AI insights fall back safely to rule-based analysis"
  sensitive   = true
  default     = ""
}

variable "gemini_api_key_version" {
  type        = number
  description = "Version integer for gemini_api_key value_wo in SSM Parameter Store"
  default     = 1
}

# --- Application Runtime & URL Variables ---

variable "application_url" {
  type        = string
  description = "Canonical public base URL of the Finance Tracker application (e.g., http://<public-ip> or https://yourdomain.com). Used by Flask to construct absolute password reset links. Leave null for prototype auto-generation using the EC2 Elastic IP over HTTP (http://<public-ip>). NOTE: Do not specify https:// unless a custom domain and valid SSL/TLS certificate are configured"
  default     = null
}

variable "app_repo_url" {
  type        = string
  description = "Optional public Git repository URL to clone during EC2 user_data bootstrap (e.g. https://github.com/your-org/Finance-tracker.git). If null, the instance prepares the runtime and arms a systemd service, awaiting code deployment via AWS SSM Session Manager"
  default     = null
}
