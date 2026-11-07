data "aws_availability_zones" "available" {
  state = "available"
}

# --- Application VPC ---
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# --- Internet Gateway (for public subnet egress/ingress) ---
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# --- Public Subnet (EC2 Application Host) ---
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet"
    Tier = "Public"
  }
}

# --- Private Subnets across 2 AZs (Required for RDS DB Subnet Group) ---
resource "aws_subnet" "private_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet_a_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.project_name}-private-subnet-a"
    Tier = "Private"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet_b_cidr
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = false

  tags = {
    Name = "${var.project_name}-private-subnet-b"
    Tier = "Private"
  }
}

# --- Public Routing Table ---
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# --- Private Routing Table (Local-only routing; strictly NO NAT Gateway) ---
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

# --- Application Host Security Group ---
resource "aws_security_group" "app" {
  name        = "${var.project_name}-app-sg"
  description = "Security group for Finance Tracker application host"
  vpc_id      = aws_vpc.main.id

  # Inbound HTTP (port 80)
  ingress {
    description = "Allow inbound HTTP traffic"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_cidr_blocks
  }

  # Inbound HTTPS (port 443) - Disabled by default; opening port 443 does NOT enable HTTPS without certificates
  dynamic "ingress" {
    for_each = var.enable_https_ingress ? [1] : []
    content {
      description = "Allow inbound HTTPS traffic (requires custom domain and SSL/TLS certificate)"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = var.allowed_http_cidr_blocks
    }
  }

  # Inbound SSH (port 22) - Restricted by variable; empty list by default (SSM Session Manager preferred)
  dynamic "ingress" {
    for_each = length(var.admin_ssh_cidr_blocks) > 0 ? [1] : []
    content {
      description = "Restricted administrator SSH access"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.admin_ssh_cidr_blocks
    }
  }

  # Outbound access (package updates, Docker images, SSM Session Manager, S3, SMTP)
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-app-sg"
  }
}

# --- Database Security Group ---
resource "aws_security_group" "db" {
  name        = "${var.project_name}-db-sg"
  description = "Security group for private MySQL RDS instance"
  vpc_id      = aws_vpc.main.id

  # Inbound MySQL (port 3306) strictly from the application security group only
  ingress {
    description     = "Allow MySQL traffic strictly from application security group"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  tags = {
    Name = "${var.project_name}-db-sg"
  }
}
