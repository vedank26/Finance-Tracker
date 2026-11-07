# --- Lookup Latest Official Amazon Linux 2023 AMI ---
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["137112412989"] # Official Amazon AMI owner ID (avoids Marketplace AMI fees)

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-6.1-x86_64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# --- Application Container Host (EC2) ---
resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]

  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.ec2_volume_size
    encrypted             = true
    delete_on_termination = true

    tags = {
      Name = "${var.project_name}-ec2-root-volume"
    }
  }

  user_data = templatefile("${path.module}/scripts/user_data.sh", {
    project_name = var.project_name
    aws_region   = var.aws_region
    app_repo_url = var.app_repo_url != null ? var.app_repo_url : ""
  })

  # MANDATORY SECURITY CONTROL: Enforce IMDSv2 (disables insecure IMDSv1)
  # Hop limit 2 is required for containerized applications on Docker bridge networks to reach IMDSv2
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # Enforce IMDSv2 session tokens
    http_put_response_hop_limit = 2          # Enables container bridge network traversal for S3 boto3 client
  }

  tags = {
    Name        = "${var.project_name}-app-host"
    Environment = var.environment
  }
}

# --- Optional Elastic IP for Stable Public Access ---
resource "aws_eip" "app" {
  count    = var.assign_elastic_ip ? 1 : 0
  domain   = "vpc"
  instance = aws_instance.app.id

  depends_on = [aws_internet_gateway.gw]

  tags = {
    Name = "${var.project_name}-eip"
  }
}
