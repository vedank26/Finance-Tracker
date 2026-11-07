# AWS Cloud Finance Tracker — Public Evidence Index & Screenshot Guide

This document indexes all verified technical evidence, AWS API outputs, and screenshot guides preserved in the `docs/final-evidence/` and `CCL_Finance_Tracker_Report/` directories.

**Target AWS Region:** `ap-south-1` (Asia Pacific - Mumbai)  
**Architecture:** Multi-Tier Web Application (Docker, EC2, RDS MySQL, S3, IAM, SSM, CloudWatch, SNS, Budgets, Terraform)  
**Infrastructure Management:** 100% Codified via HashiCorp Terraform (40 Managed Resources)  

---

## 1. Directory Structure of Verified Technical Artifacts

The technical evidence is organized into numbered service directories corresponding to each layer of the cloud architecture:

```
docs/final-evidence/
├── 01-ec2/                          # Elastic Compute Cloud (Compute & Container Host)
│   ├── ec2-instance-description.json# Direct AWS API describe-instances payload
│   ├── ec2-instance-status.json     # 2/2 status checks passed (system + instance checks ok)
│   └── ec2-verification-summary.txt # Host specifications, Docker runtime & uptime verification
│
├── 02-vpc/                          # Virtual Private Cloud (Network Isolation)
│   ├── vpc-description.json         # VPC CIDR (10.0.0.0/16) and DNS configuration
│   ├── subnets.json                 # 1 Public (AZ-a) + 2 Private DB subnets (AZ-a & AZ-b)
│   ├── route-tables.json            # Public IGW routing vs isolated private routing
│   ├── security-groups.json         # Port 80 ingress, Port 22 CLOSED, Port 3306 restricted
│   └── vpc-networking-summary.txt   # Topology, CIDR blocks, and air-gap network analysis
│
├── 03-rds-mysql/                    # Managed Database Tier
│   ├── rds-instance-description.json# MySQL 8.0, db.t3.micro, KMS storage encryption
│   └── rds-verification-summary.txt # Verification of private subnet placement & accessibility
│
├── 04-s3/                           # Object Storage & Monthly Report Exports
│   ├── s3-public-access-block.json  # Proof that all 4 Block Public Access settings are ON
│   ├── s3-encryption.json           # Default SSE-S3 AES-256 server-side encryption
│   ├── s3-objects-list.json         # Verified demonstration report & object key structure
│   └── s3-verification-summary.txt  # Proof of 15-minute presigned URLs & 30-day lifecycle rule
│
├── 05-iam/                          # Identity & Least-Privilege Authorization
│   ├── ec2-role.json                # IAM Role trust policy granting sts:AssumeRole to EC2
│   ├── ec2-inline-policies.json     # Scoped inline policies for S3, SSM, and CloudWatch
│   └── iam-verification-summary.txt # Least-privilege verification (no wildcard permissions)
│
├── 06-ssm-parameter-store/          # Centralized Secrets & Runtime Configuration
│   ├── parameters-description.json  # Catalog of managed parameters under /finance-tracker/*
│   └── ssm-verification-summary.txt # Proof of KMS SecureString encryption for sensitive keys
│
├── 07-cloudwatch/                   # Observability & Metric Alarms
│   ├── cloudwatch-log-group.json    # Log group /finance-tracker/app with 7-day retention
│   ├── cloudwatch-alarm.json        # CPU utilization metric alarm (>80% over 2x 300s periods)
│   └── cloudwatch-verification-summary.txt # Container logging & telemetry summary
│
├── 08-sns/                          # Alerting & Fanout Hub
│   ├── sns-topic-attributes.json    # Topic attributes for finance-tracker-alerts
│   ├── sns-subscriptions.json       # Confirmed email subscription record
│   ├── sns-topic-policy.json        # Dual-publishing resource policy (CloudWatch + Budgets)
│   └── sns-verification-summary.txt # Notification hub implementation proof
│
├── 09-aws-budgets/                  # Cost Governance & Spend Guardrail
│   ├── budget-description.json      # $20.00 USD monthly cost limit specification
│   ├── budget-notifications.json    # 4 alert thresholds (50%, 80%, 100% actual, 100% forecast)
│   └── budgets-verification-summary.txt # Cost guardrail implementation summary
│
├── 10-docker/                       # Container Runtime & Packaging
│   ├── Dockerfile.txt               # Production multi-stage Dockerfile (non-root appuser)
│   ├── dockerignore.txt             # Build context exclusion rules
│   └── docker-verification-summary.txt # Container runtime healthcheck verification
│
└── 11-terraform/                    # Infrastructure as Code (IaC) State
    ├── terraform-resources-inventory.txt # Inventory of all 40 managed resources
    └── terraform-validate-output.txt# Clean output of terraform validate
```

---

## 2. Technical Demonstration Proof & Viva Screenshot Guide

When presenting or reviewing the AWS implementation, the following genuine console captures provide conclusive proof of live cloud operations:

### 1. EC2 Virtual Machine & Container Runtime
- **Evidence Artifacts:** `01-ec2/ec2-instance-description.json`, `01-ec2/ec2-instance-status.json`
- **What it Proves:** Demonstrates that the application was hosted on a live `t3.micro` EC2 instance running Amazon Linux 2023. Confirms that `2/2 status checks passed`, the public Elastic IP was mapped, and IMDSv2 was strictly enforced (`http_tokens = "required"`).

### 2. Multi-AZ VPC Network Topology & Security Groups
- **Evidence Artifacts:** `02-vpc/subnets.json`, `02-vpc/security-groups.json`, `02-vpc/route-tables.json`
- **What it Proves:** Proves complete network segregation. The public subnet routes to the Internet Gateway, while private subnets have zero internet routing. Proves **Port 22 (SSH) is completely closed** on the public security group, and MySQL Port 3306 is restricted exclusively to the application security group.

### 3. Air-Gapped Amazon RDS MySQL Database
- **Evidence Artifacts:** `03-rds-mysql/rds-instance-description.json`, `03-rds-mysql/rds-verification-summary.txt`
- **What it Proves:** Proves that financial data was stored in a managed MySQL 8.0 engine on `db.t3.micro`. Confirms `PubliclyAccessible = false`, storage encryption is enabled via AWS KMS (`alias/aws/rds`), and the instance spans a multi-AZ DB subnet group.

### 4. Amazon S3 Reports Bucket & Defense-in-Depth
- **Evidence Artifacts:** `04-s3/s3-public-access-block.json`, `04-s3/s3-encryption.json`, `04-s3/s3-objects-list.json`
- **What it Proves:** Proves all 4 S3 Block Public Access settings are active, default SSE-S3 AES-256 encryption is enforced, and reports are private. Confirms time-limited pre-signed URLs (15 minutes) and 30-day automatic object expiration lifecycle rules.

### 5. IAM Least-Privilege Role & Policy Architecture
- **Evidence Artifacts:** `05-iam/ec2-role.json`, `05-iam/ec2-inline-policies.json`
- **What it Proves:** Demonstrates role delegation via `finance-tracker-ec2-role`. Confirms three scoped inline policies for S3, SSM, and CloudWatch Logs with zero wildcard resource permissions, combined with `AmazonSSMManagedInstanceCore` for secure Session Manager administration.

### 6. AWS Systems Manager Parameter Store
- **Evidence Artifacts:** `06-ssm-parameter-store/parameters-description.json`, `06-ssm-parameter-store/ssm-verification-summary.txt`
- **What it Proves:** Confirms that application secrets (`DB_PASSWORD`, `SECRET_KEY`, `MAIL_PASSWORD`) were stored as KMS-encrypted `SecureString` parameters under `/finance-tracker/*`, ensuring zero hardcoded secrets in Git.

### 7. CloudWatch Centralized Observability & Metric Alarms
- **Evidence Artifacts:** `07-cloudwatch/cloudwatch-log-group.json`, `07-cloudwatch/cloudwatch-alarm.json`
- **What it Proves:** Proves that container stdout/stderr logs were aggregated in `/finance-tracker/app` with a 7-day retention period. Confirms an automated metric alarm monitoring EC2 CPU utilization (>80% over two 5-minute evaluation periods).

### 8. Amazon SNS Notification Fanout
- **Evidence Artifacts:** `08-sns/sns-topic-attributes.json`, `08-sns/sns-topic-policy.json`, `08-sns/sns-subscriptions.json`
- **What it Proves:** Confirms topic `finance-tracker-alerts` with verified email delivery. Proves the dual-publishing topic policy authorizing both CloudWatch Alarms and AWS Budgets to dispatch notifications.

### 9. AWS Budgets Cost Guardrail
- **Evidence Artifacts:** `09-aws-budgets/budget-description.json`, `09-aws-budgets/budget-notifications.json`
- **What it Proves:** Proves proactive cost governance with a $20.00 USD monthly limit and 4 alerting triggers (50%, 80%, 100% actual spend, and 100% forecasted spend).

### 10. HashiCorp Terraform 40-Resource Inventory
- **Evidence Artifacts:** `11-terraform/terraform-resources-inventory.txt`, `11-terraform/terraform-validate-output.txt`
- **What it Proves:** Demonstrates that all 40 AWS infrastructure resources were codified and managed through Terraform without manual drift.

---

## 3. Academic Presentation & Report Deliverables

The accompanying college academic project documentation is preserved in the `CCL_Finance_Tracker_Report/` directory:
- **`CCL_Finance_Tracker_Report.pdf`**: Formatted college academic project report.
- **`CCL_Finance_Tracker_Report.docx`**: Editable Microsoft Word project report.
- **`CCL_Finance_Tracker_Academic_Report.md`**: Complete markdown report text.
- **`aws_finance_tracker_architecture.jpg`**: High-resolution system architecture diagram.
- **`diagrams/`**: 8 editable Mermaid source diagrams (`.mmd`) detailing request lifecycles, database connectivity, and alert workflows.
- **`screenshots/`**: Genuine application and dashboard screenshots.
