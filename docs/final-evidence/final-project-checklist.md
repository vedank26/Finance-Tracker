# AWS Finance Tracker — Final College Project Submission Checklist

Use this checklist to ensure all technical deliverables, cloud components, and demonstration assets are verified and ready for project evaluation and viva.

---

## 1. Cloud Infrastructure & Service Verification Checklist

| # | Cloud Deliverable / Component | Specification | Verification Status | Proof Location |
| :-: | :--- | :--- | :---: | :--- |
| **1** | **EC2 Compute Instance** | `t3.micro`, Amazon Linux 2023, Public IP `PUBLIC_IP_REDACTED` | **VERIFIED** | `docs/final-evidence/01-ec2/` |
| **2** | **EC2 Status Checks** | System Status & Instance Status: 2/2 passed | **VERIFIED** | `01-ec2/ec2-instance-status.json` |
| **3** | **Docker Application** | Container `finance-tracker-app` healthy; port 80 -> 5000 | **VERIFIED** | `10-docker/docker-verification-summary.txt` |
| **4** | **Custom VPC Topology** | `10.0.0.0/16`; 1 Public Subnet, 2 Private Subnets, IGW | **VERIFIED** | `02-vpc/vpc-networking-summary.txt` |
| **5** | **Closed Port 22 SSH** | Inbound port 22 closed; admin access via SSM Session Manager | **VERIFIED** | `02-vpc/security-groups.json` |
| **6** | **RDS MySQL 8.0 Database** | `db.t3.micro`, private endpoint `10.0.10.148:3306`, encrypted | **VERIFIED** | `03-rds-mysql/rds-verification-summary.txt` |
| **7** | **Database Schema** | 5 Tables: `user`, `transaction`, `net_worth`, `investment`, `budget` | **VERIFIED** | Live DB initialization confirmed |
| **8** | **Amazon S3 Report Bucket** | Bucket `finance-tracker-reports-S3_BUCKET_REDACTED`, private, SSE AES256 | **VERIFIED** | `04-s3/s3-verification-summary.txt` |
| **9** | **S3 Demonstration Report** | `monthly-reports/user-1/2026-11/report-d34b7611bcc94060b843c791c761d5f5.csv` | **VERIFIED** | `04-s3/s3-objects-list.json` |
| **10**| **IAM Instance Role** | `finance-tracker-ec2-role` with scoped least privilege | **VERIFIED** | `05-iam/iam-verification-summary.txt` |
| **11**| **SSM Parameter Store** | 8 Parameters under `/finance-tracker/` (SecureString for secrets) | **VERIFIED** | `06-ssm-parameter-store/` |
| **12**| **CloudWatch Log Group** | `/finance-tracker/app` with 7-day retention & Gunicorn stream | **VERIFIED** | `07-cloudwatch/cloudwatch-log-group.json` |
| **13**| **CloudWatch CPU Alarm** | `finance-tracker-ec2-high-cpu` (80% threshold, 2x300s, state `OK`) | **VERIFIED** | `07-cloudwatch/cloudwatch-alarm.json` |
| **14**| **Amazon SNS Alert Topic** | `finance-tracker-alerts` with 1 confirmed email subscriber | **VERIFIED** | `08-sns/sns-verification-summary.txt` |
| **15**| **AWS Budgets Cost Guardrail** | $20.00 USD monthly limit with 4 notification thresholds | **VERIFIED** | `09-aws-budgets/budgets-verification-summary.txt` |
| **16**| **Terraform IaC State** | Exactly 40 managed resources in state; `terraform validate` passed | **VERIFIED** | `11-terraform/` |
| **17**| **Live Application Access** | Homepage [http://PUBLIC_IP_REDACTED](http://PUBLIC_IP_REDACTED) loads with HTTP 200 | **VERIFIED** | Live web requests passed |

---

## 2. Project Documentation Deliverables

- [x] **Project Architecture Blueprint:** [`project-architecture.md`](file:///C:/Projects/Finance-tracker/docs/final-evidence/project-architecture.md)
- [x] **Cloud Services Reference Guide:** [`cloud-services-explanation.md`](file:///C:/Projects/Finance-tracker/docs/final-evidence/cloud-services-explanation.md)
- [x] **5–7 Minute Demonstration Script:** [`demo-script.md`](file:///C:/Projects/Finance-tracker/docs/final-evidence/demo-script.md)
- [x] **Evidence & Screenshot Guide:** [`evidence-index.md`](file:///C:/Projects/Finance-tracker/docs/final-evidence/evidence-index.md)
- [x] **Security Architecture & Threat Model:** [`security-summary.md`](file:///C:/Projects/Finance-tracker/docs/final-evidence/security-summary.md)
- [x] **Viva Questions & Model Answers:** Included in Final Audit Report & Documentation

---

## 3. Demonstration Pre-Flight Checklist

Before presenting to evaluators:

1. **Verify Live Web Connectivity:**  
   Open browser to `http://PUBLIC_IP_REDACTED`. Confirm homepage loads cleanly with Tailwind CSS styling.
2. **Confirm AWS Console Access:**  
   Log into AWS Console in `ap-south-1` region. Have the tabs ready for:
   - EC2 Instances
   - VPC Subnets & Route Tables
   - RDS Databases
   - S3 Bucket Objects
   - Systems Manager Parameter Store
   - CloudWatch Alarms
   - AWS Budgets
3. **Have Demonstration CSV Ready:**  
   Ensure a sample `transactions.csv` is saved on your desktop for demonstrating file upload.
4. **Follow 5–7 Minute Script:**  
   Adhere to the timing in [`demo-script.md`](file:///C:/Projects/Finance-tracker/docs/final-evidence/demo-script.md) to showcase live functionality, cloud infrastructure, and security controls within allotted presentation time.
