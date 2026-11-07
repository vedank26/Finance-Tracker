# --- EC2 Instance Role & Trust Policy ---
resource "aws_iam_role" "ec2_role" {
  name                 = "${var.project_name}-ec2-role"
  description          = "IAM execution role for Finance Tracker EC2 container host"
  permissions_boundary = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/FinanceTracker-EC2-Role-Permissions-Boundary"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ec2-role"
  }
}

# --- Instance Profile (attached to EC2 instance) ---
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# --- 1. AWS Systems Manager (SSM) Managed Policy for Keyless Terminal Access ---
# Enables AWS Systems Manager Session Manager, eliminating the need for open SSH ports
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# --- 2. Scoped S3 Monthly Reports Access Policy ---
# Least-privilege access restricted strictly to project's bucket and monthly-reports prefix
resource "aws_iam_role_policy" "s3_reports" {
  name = "${var.project_name}-s3-reports-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListReportsBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = aws_s3_bucket.reports.arn
      },
      {
        Sid    = "ManageMonthlyReportsObjects"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.reports.arn}/monthly-reports/*"
      }
    ]
  })
}

# --- 3. Scoped Parameter Store Read Access Policy ---
# Restricted strictly to project namespace (/finance-tracker/*)
resource "aws_iam_role_policy" "ssm_parameters" {
  name = "${var.project_name}-ssm-parameters-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadProjectParameters"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*"
      }
    ]
  })
}

# --- 4. Scoped CloudWatch Logs Policy ---
# Restricted strictly to application log group (/finance-tracker/app)
resource "aws_iam_role_policy" "cloudwatch_logs" {
  name = "${var.project_name}-cloudwatch-logs-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "StreamApplicationLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "${aws_cloudwatch_log_group.app_logs.arn}:*"
      }
    ]
  })
}
