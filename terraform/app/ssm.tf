# --- Systems Manager Parameter Store (Standard Tier — 100% Free) ---
#
# STATE FILE SECURITY & SECRETS ARCHITECTURE:
# 1. Unsafe placeholder defaults are completely eliminated.
# 2. Sensitive values are supplied via required ephemeral inputs (var.db_password, var.flask_secret_key).
# 3. AWS Provider 5.88+ write-only arguments (`value_wo` and `value_wo_version`) ensure that
#    real secrets are transmitted directly to the AWS SSM API without ever being persisted
#    in plaintext inside `terraform.tfstate` or plan files.
# 4. Standard Tier is enforced for all parameters (10,000 parameters free; zero storage cost).
# 5. Discrete database parameters (DB_HOST, DB_PORT, DB_USER, DB_NAME, DB_PASSWORD) are stored
#    exclusively in SSM. A consolidated raw DATABASE_URL is intentionally omitted to avoid unencoded
#    passwords with special characters; this allows Flask's app/__init__.py to activate its discrete
#    database resolution using SQLAlchemy's URL.create() to automatically percent-encode credentials.

# 1. Flask Secret Key (SecureString) — Required at startup in production
resource "aws_ssm_parameter" "secret_key" {
  name        = "/${var.project_name}/SECRET_KEY"
  description = "Flask session and CSRF secret key"
  type        = "SecureString"
  tier        = "Standard"

  # WRITE-ONLY ARGUMENT: Transmitted write-only; never persisted to state file
  value_wo         = var.flask_secret_key
  value_wo_version = var.flask_secret_key_version

  tags = {
    Name = "${var.project_name}-secret-key"
  }
}

# 2. Discrete Database Parameters (Activating Flask app/__init__.py discrete resolution with URL.create)
resource "aws_ssm_parameter" "db_host" {
  name        = "/${var.project_name}/DB_HOST"
  description = "RDS MySQL instance private hostname"
  type        = "String"
  tier        = "Standard"
  value       = aws_db_instance.default.address

  tags = {
    Name = "${var.project_name}-db-host"
  }
}

resource "aws_ssm_parameter" "db_port" {
  name        = "/${var.project_name}/DB_PORT"
  description = "RDS MySQL port"
  type        = "String"
  tier        = "Standard"
  value       = tostring(aws_db_instance.default.port)

  tags = {
    Name = "${var.project_name}-db-port"
  }
}

resource "aws_ssm_parameter" "db_user" {
  name        = "/${var.project_name}/DB_USER"
  description = "RDS MySQL master database user"
  type        = "String"
  tier        = "Standard"
  value       = var.db_username

  tags = {
    Name = "${var.project_name}-db-user"
  }
}

resource "aws_ssm_parameter" "db_name" {
  name        = "/${var.project_name}/DB_NAME"
  description = "RDS MySQL database schema name"
  type        = "String"
  tier        = "Standard"
  value       = var.db_name

  tags = {
    Name = "${var.project_name}-db-name"
  }
}

resource "aws_ssm_parameter" "db_password" {
  name        = "/${var.project_name}/DB_PASSWORD"
  description = "RDS MySQL master database password"
  type        = "SecureString"
  tier        = "Standard"

  # WRITE-ONLY ARGUMENT: Never persisted in state file
  value_wo         = var.db_password
  value_wo_version = var.db_password_version

  tags = {
    Name = "${var.project_name}-db-password"
  }
}

# 3. Gemini API Key (SecureString — Optional)
resource "aws_ssm_parameter" "gemini_api_key" {
  count = var.gemini_api_key != "" ? 1 : 0

  name        = "/${var.project_name}/GEMINI_API_KEY"
  description = "Google Gemini Flash API key for financial AI insights"
  type        = "SecureString"
  tier        = "Standard"

  # WRITE-ONLY ARGUMENT: Transmitted write-only; never persisted to state file
  value_wo         = var.gemini_api_key
  value_wo_version = var.gemini_api_key_version

  tags = {
    Name = "${var.project_name}-gemini-api-key"
  }
}

# 4. S3 Reports Bucket Name (String — Non-sensitive Metadata)
resource "aws_ssm_parameter" "s3_report_bucket" {
  name        = "/${var.project_name}/S3_REPORT_BUCKET"
  description = "Name of private S3 bucket for monthly financial CSV reports"
  type        = "String"
  tier        = "Standard"
  value       = aws_s3_bucket.reports.id

  tags = {
    Name = "${var.project_name}-s3-report-bucket"
  }
}

# 5. Canonical Application Base URL for absolute password reset links
resource "aws_ssm_parameter" "application_url" {
  name        = "/${var.project_name}/APPLICATION_URL"
  description = "Canonical public base URL for password reset links"
  type        = "String"
  tier        = "Standard"
  value       = var.application_url != null ? var.application_url : (var.assign_elastic_ip ? "http://${aws_eip.app[0].public_ip}" : "http://${aws_instance.app.public_ip}")

  tags = {
    Name = "${var.project_name}-application-url"
  }
}
