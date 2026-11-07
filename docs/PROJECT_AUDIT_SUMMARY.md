# AWS Cloud Finance Tracker — Project Implementation & Engineering Audit Summary

This engineering audit summary outlines the architecture, cloud infrastructure, containerization, security controls, and operational verification completed for the **AWS Cloud – Finance Tracker** project.

---

## 1. Executive Summary & Implementation Scope

The Finance Tracker project was engineered to demonstrate a production-grade, multi-tier cloud web application deployed on Amazon Web Services (AWS) using Infrastructure as Code (Terraform) and containerization (Docker).

The application provides personal finance management, transaction ingestion with duplicate prevention, budget tracking, portfolio valuation, historical net worth tracking, and monthly exportable reports stored in Amazon S3.

### Implementation Milestones & Metrics
- **Cloud Infrastructure:** 40 Core Resources provisioned via Terraform in region `ap-south-1` (Mumbai).
- **Compute Tier:** Docker containerized Flask 3.0 application running on Amazon EC2 `t3.micro` orchestrated by Gunicorn WSGI.
- **Database Tier:** Managed Amazon RDS MySQL 8.0 instance on `db.t3.micro` air-gapped in private subnets across two Availability Zones.
- **Object Storage:** Private Amazon S3 bucket for monthly financial reports with SSE-S3 AES-256 encryption and 15-minute presigned download URLs.
- **Secrets Management:** AWS Systems Manager Parameter Store with KMS `SecureString` encryption for all database credentials, session keys, and SMTP authentication tokens.
- **Perimeter Security:** Custom VPC (`10.0.0.0/16`) with total elimination of SSH Port 22; remote administration mediated via AWS Systems Manager Session Manager.
- **Observability & Governance:** Centralized CloudWatch container logs (7-day retention), high CPU metric alarm, Amazon SNS alerting with email delivery, and AWS Budgets $20.00 monthly cost guardrail.

---

## 2. AWS Services Deployment & Verification Matrix

The deployment incorporates 9 AWS managed services, Docker containerization, and Terraform Infrastructure as Code. Each component was deployed, configured, and verified live:

| AWS Service | Architectural Role | Deployment Sizing & Configuration | Verification Status |
| :--- | :--- | :--- | :--- |
| **Amazon EC2** | Web Application Compute Host | `t3.micro`, Amazon Linux 2023, 20 GB gp3 encrypted volume, IMDSv2 enforced (`http_tokens = "required"`), Elastic IP attached. | **Deployed & Verified** (2/2 status checks passed) |
| **Amazon VPC** | Network Boundary & Segmentation | `10.0.0.0/16`, 1 Public Subnet (`10.0.1.0/24`), 2 Private DB Subnets (`10.0.10.0/24`, `10.0.11.0/24`), Internet Gateway, Public/Private Route Tables. | **Deployed & Verified** (Air-gapped database isolation) |
| **Amazon RDS MySQL** | Relational Data Store | MySQL 8.0, `db.t3.micro`, 20 GB gp3 storage, KMS encryption (`alias/aws/rds`), Multi-AZ DB subnet group, `PubliclyAccessible = false`. | **Deployed & Verified** (Inbound restricted to App SG port 3306) |
| **Amazon S3** | Report Storage & Pre-signed Delivery | S3 bucket with SSE-S3 AES-256 encryption, all 4 Block Public Access settings `true`, 30-day lifecycle rule, 15-minute presigned URLs. | **Deployed & Verified** (Demonstration report uploaded & verified) |
| **AWS IAM** | Identity & Least-Privilege Access | `finance-tracker-ec2-role`, instance profile, `AmazonSSMManagedInstanceCore`, 3 scoped inline policies for S3, SSM, and CloudWatch. | **Deployed & Verified** (No static credentials, least-privilege ARNs) |
| **AWS Systems Manager** | Secrets & Runtime Configuration | Parameter Store namespace `/finance-tracker/*` (14 parameters). KMS `SecureString` encryption for `DB_PASSWORD`, `SECRET_KEY`, `MAIL_PASSWORD`. | **Deployed & Verified** (Runtime hydration via refresh script) |
| **Amazon CloudWatch** | Logs & Performance Alarms | Log group `/finance-tracker/app` (7-day retention). Metric alarm for EC2 CPU utilization > 80% over 2 consecutive 300s periods. | **Deployed & Verified** (Gunicorn stdout/stderr streaming active) |
| **Amazon SNS** | Notification Fanout Hub | Topic `finance-tracker-alerts`, dual-publishing access policy (CloudWatch + Budgets), verified email subscription. | **Deployed & Verified** (Email alert delivery verified) |
| **AWS Budgets** | Financial Cost Guardrail | $20.00 USD monthly limit with 4 notification triggers (50%, 80%, 100% actual, 100% forecast) routing alerts to SNS. | **Deployed & Verified** (Spend tracking active) |
| **Docker** | Containerization Runtime | `python:3.11-slim`, non-root user `appuser` (UID 1000), Gunicorn WSGI (2 workers, 4 threads), healthcheck, bounded DB retries. | **Deployed & Verified** (Container healthy, automated schema init) |
| **HashiCorp Terraform** | Infrastructure as Code | Terraform v1.5+, AWS Provider ~> 5.0. 11 files in `app/` (40 managed resources), 5 files in `budget/` (4 managed resources). | **Deployed & Verified** (Zero drift, validate passing) |

---

## 3. Application Architecture & Integration Flow

### Multi-Tier Data Flow
```
User (Browser) 
  ──[ HTTP Port 80 ]──► Internet Gateway 
  ──► EC2 (Public Subnet A) 
  ──► Docker (Gunicorn / Flask on Port 5000)
        │
        ├──[ TCP Port 3306 ]──► RDS MySQL 8.0 (Air-Gapped Private Subnet)
        │
        ├──[ Boto3 / IAM ]──► Amazon S3 (Monthly Reports / AES-256)
        │
        ├──[ AWS CLI / IAM ]──► SSM Parameter Store (Encrypted Secrets)
        │
        └──[ Stdout/Stderr ]──► CloudWatch Logs (/finance-tracker/app)
                                       │
                                       ▼ (CPU > 80%)
                                 CloudWatch Alarm ──► SNS Topic ──► Admin Email
```

### Key Application Features
1. **User Authentication & Isolation:** Session management with Flask-Login and Werkzeug password hashing. Multi-tenant data isolation enforced across all database queries (`user_id == current_user.id`).
2. **Transaction Deduplication:** Prevents duplicate entries during repeated CSV imports using an MD5 fingerprint hash: `MD5(user_id:date:amount:description:category:type)`.
3. **Password Reset via Gmail SMTP:** Cryptographically secure 32-character tokens generated via `secrets.token_hex(16)` with 1-hour expiration. Constructing reset URLs from explicit `APPLICATION_URL` prevents Host Header Poisoning.
4. **Spreadsheet Formula Injection Defense (CWE-1236):** Report export sanitizes cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` by prepending a single quote (`'`), protecting users opening CSV reports in Microsoft Excel or Google Sheets.
5. **Interactive Visualizations:** High-performance Plotly.js charts for monthly cash flow, net worth trends, and portfolio asset allocation.
6. **Financial Health Analytics:** Composite scoring (0–100) based on savings rate, liquidity, and debt ratios, featuring Google Gemini AI insights with fallback to deterministic heuristic rules.

---

## 4. Security Hardening & Threat Mitigations

| Threat Category | Defensive Control Implemented in Architecture |
| :--- | :--- |
| **Credential Theft in Git** | Zero credentials in codebase. 14 parameters stored in AWS Systems Manager Parameter Store; passwords encrypted with AWS KMS (`SecureString`). `.env` strictly ignored. |
| **SSH Brute-Force & Key Theft** | Port 22 is completely omitted from the security group. Remote administration is mediated through AWS Systems Manager Session Manager. |
| **Database Compromise** | RDS MySQL is deployed in private subnets with no route to the Internet Gateway. Port 3306 ingress is restricted exclusively to the EC2 security group. |
| **SSRF & Credential Exfiltration** | EC2 enforces IMDSv2 (`http_tokens = "required"`, hop limit 1), blocking SSRF attacks seeking to steal instance profile credentials. |
| **Container Privilege Escalation** | Docker container executes under dedicated non-root user `appuser` (UID 1000). |
| **Cross-Site Request Forgery** | Flask-WTF CSRF tokens protect all state-changing POST and DELETE endpoints. |
| **Unbounded Cloud Billing** | AWS Budgets $20.00 monthly cost guardrail with 4 alerting thresholds; S3 30-day lifecycle expiration; CloudWatch 7-day log retention. |

---

## 5. Verification & Testing Summary

1. **Infrastructure Validation:** Executed `terraform validate` across both `terraform/app` and `terraform/budget` modules with zero configuration errors. Verified exactly 40 managed resources in the active state.
2. **Database Connectivity & Schema Migration:** Verified automated startup retries via `entrypoint.sh` against RDS MySQL, followed by automatic execution of `db.create_all()` within Flask application context.
3. **Direct S3 Upload & Pre-signed Retrieval:** Successfully generated, encrypted (SSE-S3), uploaded, and downloaded a demonstration monthly report (`monthly-reports/user-1/2026-11/report-d34b7611bcc94060b843c791c761d5f5.csv`).
4. **Parameter Store Retrieval:** Confirmed that `/opt/finance-tracker/refresh-env.sh` retrieves all 14 parameters and writes `/opt/finance-tracker/.env` with `0600` permissions.
5. **SMTP Password Reset Flow:** Confirmed end-to-end token generation, SSL/TLS handshake with `smtp.gmail.com:587`, and delivery of password-reset emails.
6. **Account Preservation:** The synthetic demonstration account (`synth_user_2eb09d87`, ID: 1, $250 Utilities budget) was preserved untouched for academic evaluation.

All technical evidence artifacts supporting these findings are indexed in [`docs/PUBLIC_EVIDENCE_INDEX.md`](PUBLIC_EVIDENCE_INDEX.md).
