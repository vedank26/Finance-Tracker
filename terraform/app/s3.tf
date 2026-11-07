# --- Private S3 Bucket for Monthly Financial CSV Reports ---
resource "aws_s3_bucket" "reports" {
  bucket = var.s3_bucket_name != null ? var.s3_bucket_name : "${var.project_name}-reports-${data.aws_caller_identity.current.account_id}"

  # Protect against accidental deletion of the reports bucket
  force_destroy = false

  tags = {
    Name        = "${var.project_name}-reports"
    Purpose     = "Private Monthly Financial CSV Reports"
    Sensitivity = "Confidential"
  }
}

# --- Enforce Bucket Owner Object Ownership (Disables ACLs entirely) ---
resource "aws_s3_bucket_ownership_controls" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# --- Strict S3 Block Public Access (All 4 settings enabled) ---
resource "aws_s3_bucket_public_access_block" "reports" {
  bucket = aws_s3_bucket.reports.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# --- Server-Side Encryption (AES256 standard; zero KMS request fees) ---
resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = false
  }
}

# --- Lifecycle Management (Prevents perpetual storage cost accumulation) ---
resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    id     = "archive-or-expire-old-reports"
    status = "Enabled"

    filter {
      prefix = "monthly-reports/"
    }

    # Automatically clean up generated CSV reports after 90 days
    expiration {
      days = 90
    }
  }
}
