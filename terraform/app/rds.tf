# --- DB Subnet Group across 2 Private AZs ---
resource "aws_db_subnet_group" "rds" {
  name        = "${var.project_name}-rds-subnet-group"
  description = "Private database subnet group for MySQL across 2 AZs"
  subnet_ids  = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = {
    Name = "${var.project_name}-rds-subnet-group"
  }
}

# --- Single-AZ MySQL 8.0 RDS Instance ---
# STATE FILE SECURITY NOTICE:
# In standard Terraform, passing a password or using random_password stores the
# plaintext database secret directly in terraform.tfstate.
#
# To prevent password exposure in state:
# 1. Terraform 1.11+ ephemeral variable `var.db_password` is used.
# 2. AWS Provider 5.88+ write-only argument `password_wo` sends the password to
#    the RDS API without persisting it in terraform.tfstate.
# 3. Rotating the password is done cleanly by incrementing `var.db_password_version`.
# 4. Standard random_password resources are eliminated because they leak plaintext in state.

resource "aws_db_instance" "default" {
  identifier = "${var.project_name}-mysql"

  engine         = "mysql"
  engine_version = var.rds_engine_version
  instance_class = var.rds_instance_class

  allocated_storage = var.rds_allocated_storage
  storage_type      = "gp3"

  # SECURITY CONTROL: Enforce storage encryption at rest
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username

  # WRITE-ONLY PASSWORD: Never persisted to Terraform state or plan files
  password_wo         = var.db_password
  password_wo_version = var.db_password_version

  db_subnet_group_name   = aws_db_subnet_group.rds.name
  vpc_security_group_ids = [aws_security_group.db.id]

  # CRITICAL COST CONTROL: Single-AZ only. Multi-AZ doubles cost and is not Free Tier eligible.
  multi_az = false

  # CRITICAL SECURITY CONTROL: No public endpoint; access is restricted to private VPC.
  publicly_accessible = false

  # Cost control for prototypes: avoid retaining expensive final snapshots upon destroy
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.project_name}-final-snapshot-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  # Daily backup retention (1 day keeps automated backup within free tier limits)
  backup_retention_period = var.backup_retention_period

  auto_minor_version_upgrade = true
  deletion_protection        = var.rds_deletion_protection
  apply_immediately          = true

  tags = {
    Name        = "${var.project_name}-mysql"
    Environment = var.environment
  }
}
