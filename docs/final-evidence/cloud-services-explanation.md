# AWS Finance Tracker — Cloud Services Reference Guide

This guide breaks down each of the 9 AWS Cloud Services (plus Docker and Terraform) utilized in the Finance Tracker project, explaining **what it is**, **why we chose it**, **how our application uses it**, and **how it communicates with other components**.

---

## 1. Amazon Elastic Compute Cloud (EC2)

- **What it does:**  
  Amazon EC2 provides resizable virtual compute servers (instances) in the cloud. It allows us to run custom operating systems, software packages, and container runtimes.
- **Why we chose it:**  
  Running the Flask application inside Docker on a dedicated `t3.micro` instance provides full control over our application environment, networking, dependencies, and WSGI web server configurations while staying within the AWS Free Tier.
- **How Finance Tracker uses it:**  
  We run an Amazon Linux 2023 `t3.micro` instance (`EC2_INSTANCE_ID_REDACTED`) with an Elastic IP (`PUBLIC_IP_REDACTED`). It hosts the Docker daemon and executes the `finance-tracker-app` container running Gunicorn on port 5000, mapped to host port 80.
- **Component Interactions:**  
  - Receives HTTP traffic from end-users over the internet via the Internet Gateway.
  - Queries RDS MySQL privately across VPC subnets on port 3306.
  - Interacts with AWS Parameter Store and Amazon S3 using IAM role credentials.
  - Emits CPU metrics to Amazon CloudWatch.

---

## 2. Amazon Virtual Private Cloud (VPC)

- **What it does:**  
  Amazon VPC provisions a logically isolated virtual network dedicated to our AWS account. It gives us complete control over IP address ranges, subnets, route tables, and network gateways.
- **Why we chose it:**  
  Security in the cloud requires defense in depth. A custom VPC allows us to implement a dual-tier network architecture that isolates our database completely from the public internet.
- **How Finance Tracker uses it:**  
  We created `VPC_ID_REDACTED` with CIDR `10.0.0.0/16`. It contains:
  - **1 Public Subnet (`10.0.1.0/24`)**: Hosts the EC2 instance and routes traffic through an Internet Gateway (IGW).
  - **2 Private Subnets (`10.0.10.0/24` & `10.0.11.0/24`)**: Spanning two Availability Zones (`ap-south-1a` and `ap-south-1b`) hosting the RDS MySQL DB Subnet Group. These subnets have no route to the Internet Gateway, making direct internet access physically impossible.
- **Component Interactions:**  
  - Governs all network traffic between the Internet, EC2, and RDS MySQL.
  - Enforces Security Group rules (App SG: port 80 only; DB SG: port 3306 from App SG only).

---

## 3. Amazon Relational Database Service (RDS) MySQL

- **What it does:**  
  Amazon RDS is a managed relational database service that automates provisioning, hardware scaling, patching, automated backups, and failure detection.
- **Why we chose it:**  
  Instead of running MySQL manually on the EC2 instance (which consumes server RAM and risks data loss if the VM crashes), RDS offloads database management, provides automated storage encryption, and guarantees persistence independently of the compute instance.
- **How Finance Tracker uses it:**  
  We run a `db.t3.micro` instance (`finance-tracker-mysql`) running MySQL 8.0.46. It persistently stores our 5 application tables: `user`, `transaction`, `net_worth`, `investment`, and `budget`.
- **Component Interactions:**  
  - Connects strictly to the EC2 container via private endpoint `10.0.10.148:3306`.
  - Blocks all inbound connections from outside the VPC.

---

## 4. Amazon Simple Storage Service (S3)

- **What it does:**  
  Amazon S3 is an object storage service offering industry-leading scalability, data availability, security, and performance.
- **Why we chose it:**  
  Local server disks are ephemeral and vulnerable to data corruption. Storing user monthly financial exports and deployment release archives in S3 guarantees 99.999999999% (11 9s) of data durability at virtually zero cost.
- **How Finance Tracker uses it:**  
  Bucket `finance-tracker-reports-S3_BUCKET_REDACTED` stores monthly financial CSV exports in dedicated user prefixes (`monthly-reports/user-{id}/{YYYY-MM}/report-{uuid}.csv`). All objects are automatically encrypted using SSE-S3 (`AES256`).
- **Component Interactions:**  
  - EC2 uploads generated CSV reports directly via `boto3`.
  - EC2 generates 15-minute expiring pre-signed URLs so authenticated users can download their reports directly from S3 without making the bucket public.

---

## 5. AWS Identity and Access Management (IAM)

- **What it does:**  
  AWS IAM provides fine-grained access control across all AWS resources, defining who or what can be authenticated and authorized.
- **Why we chose it:**  
  Embedding AWS Access Keys or Secret Keys into server files, code, or Docker images is a critical security vulnerability. IAM Roles allow the EC2 instance to assume temporary, auto-rotated credentials without hardcoding a single secret key.
- **How Finance Tracker uses it:**  
  Instance role `finance-tracker-ec2-role` is attached to EC2 via an Instance Profile. It applies the principle of least privilege through scoped inline policies allowing access *only* to our specific S3 bucket prefix, CloudWatch log group, and Parameter Store namespace.
- **Component Interactions:**  
  - Authorizes the EC2 instance to communicate with S3, Systems Manager, and CloudWatch.

---

## 6. AWS Systems Manager (SSM) Parameter Store

- **What it does:**  
  AWS Systems Manager Parameter Store provides secure, hierarchical storage for configuration data management and secrets management.
- **Why we chose it:**  
  It separates application configuration and sensitive passwords from source code and Docker container images. Sensitive parameters are encrypted at rest using AWS KMS keys.
- **How Finance Tracker uses it:**  
  We maintain 8 parameters under `/finance-tracker/`:
  - `DB_HOST`, `DB_NAME`, `DB_PORT`, `DB_USER`, `APPLICATION_URL`, `S3_REPORT_BUCKET` (Type: `String`)
  - `DB_PASSWORD`, `SECRET_KEY` (Type: `SecureString` — encrypted with KMS)
- **Component Interactions:**  
  - At system startup, `refresh-env.sh` on EC2 fetches and decrypts these parameters into `/etc/finance-tracker/finance-tracker.env`, which is injected into the Docker container.

---

## 7. Amazon CloudWatch

- **What it does:**  
  Amazon CloudWatch provides real-time monitoring, metrics collection, log aggregation, and alarming for AWS resources and applications.
- **Why we chose it:**  
  In cloud deployments, accessing server logs through interactive SSH is neither scalable nor secure. CloudWatch centralizes operational logging and provides automated alerts if the server experiences abnormal CPU load.
- **How Finance Tracker uses it:**  
  - **CloudWatch Logs:** Log Group `/finance-tracker/app` captures live Gunicorn web server access and error logs with a 7-day retention policy to eliminate unnecessary log storage costs.
  - **CloudWatch Alarms:** Metric Alarm `finance-tracker-ec2-high-cpu` monitors `CPUUtilization` on our EC2 instance. If CPU exceeds 80% for two consecutive 5-minute periods, the alarm state transitions to `ALARM`.
- **Component Interactions:**  
  - Ingests application logs from Docker on EC2.
  - Triggers Amazon SNS notifications when alarm thresholds are breached.

---

## 8. Amazon Simple Notification Service (SNS)

- **What it does:**  
  Amazon SNS is a fully managed pub/sub messaging service for application-to-application (A2A) and application-to-person (A2P) communication.
- **Why we chose it:**  
  It decouples alerting systems from email infrastructure. Rather than configuring complex SMTP servers for operations, multiple AWS services can publish events to a single SNS topic that reliably fans out notifications to administrators.
- **How Finance Tracker uses it:**  
  Topic `finance-tracker-alerts` acts as our central notification hub. It maintains a verified email subscription (`ved***@gmail.com`). Its resource policy permits publishing from both CloudWatch Alarms and AWS Budgets.
- **Component Interactions:**  
  - Receives alerts from CloudWatch Alarms (infrastructure events).
  - Receives alerts from AWS Budgets (financial threshold events).
  - Delivers real-time email alerts to the administrator's inbox.

---

## 9. AWS Budgets

- **What it does:**  
  AWS Budgets enables cost tracking and governance, allowing organizations to set custom spending limits and receive proactive notifications before unintended cloud charges occur.
- **Why we chose it:**  
  For students and mini-projects, accidental runaway cloud costs (e.g., from unclosed resources or traffic spikes) are a major risk. A budget acts as an automated financial guardrail.
- **How Finance Tracker uses it:**  
  We maintain a monthly cost budget `finance-tracker-monthly-cost-guardrail` with a strict **$20.00 USD limit**. It configures 4 distinct alert thresholds:
  1. **50% of Actual Spend ($10.00)**
  2. **80% of Actual Spend ($16.00)**
  3. **100% of Actual Spend ($20.00)**
  4. **100% of Forecasted Spend ($20.00)** (fires proactively if month-end forecast projects exceeding $20)
- **Component Interactions:**  
  - Analyzes daily AWS Billing metrics.
  - Dispatches warning messages to SNS topic `finance-tracker-alerts`.

---

## 10. Docker (Container Runtime)

- **What it does:**  
  Docker packages software into standardized, portable units called containers, bundling code, system libraries, and runtime dependencies together.
- **Why we chose it:**  
  Docker eliminates "it works on my machine" issues. It guarantees that our Flask application, Gunicorn WSGI server, and dependencies run identically in local development and production AWS EC2.
- **How Finance Tracker uses it:**  
  Container `finance-tracker-app` runs image `finance-tracker-web`. The build process uses `.dockerignore` to ensure sensitive files (`.env`, secrets, git history) are completely excluded from image layers.

---

## 11. Terraform (Infrastructure as Code)

- **What it does:**  
  Terraform is an open-source Infrastructure as Code (IaC) tool that allows developers to define, provision, and version cloud infrastructure using declarative configuration files.
- **Why we chose it:**  
  Manual cloud setup via the AWS Console is error-prone, untracked, and difficult to reproduce. Terraform documents every subnet, security group, and policy in version-controlled code, allowing exact architectural validation and zero configuration drift.
- **How Finance Tracker uses it:**  
  The `terraform/app` root module manages **40 distinct AWS resources** (VPC, subnets, route tables, security groups, RDS instance, S3 bucket, IAM roles/policies, Parameter Store keys, CloudWatch alarms, and SNS topics).
