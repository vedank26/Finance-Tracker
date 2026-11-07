# AWS Finance Tracker — Project Evidence Index & Screenshot Guide

This index documents all verified technical evidence collected directly from the live AWS deployment for the Finance Tracker Cloud Computing mini-project.

**Target AWS Account:** `AWS_ACCOUNT_ID_REDACTED`  
**Target Region:** `ap-south-1` (Asia Pacific - Mumbai)  
**Public Application Endpoint:** `http://PUBLIC_IP_REDACTED`  
**Total Managed Terraform Resources:** 40  

---

## 1. Directory Structure of Evidence Files

```
docs/final-evidence/
├── 01-ec2/
│   ├── ec2-instance-description.json   # Full AWS API describe-instances payload
│   ├── ec2-instance-status.json        # 2/2 status checks passed (system + instance)
│   └── ec2-verification-summary.txt    # Human-readable summary of EC2 instance & Docker
├── 02-vpc/
│   ├── vpc-description.json            # VPC VPC_ID_REDACTED (10.0.0.0/16)
│   ├── subnets.json                    # 1 Public (A) + 2 Private (A & B) subnets
│   ├── route-tables.json               # Public (with IGW) & Private (local only) tables
│   ├── security-groups.json            # App SG (port 80 open, 22 closed) & DB SG (3306 restricted)
│   └── vpc-networking-summary.txt      # Network topology, routing, and isolation proof
├── 03-rds-mysql/
│   ├── rds-instance-description.json   # MySQL 8.0 instance configuration & specs
│   └── rds-verification-summary.txt    # Proof of private isolation and KMS encryption
├── 04-s3/
│   ├── s3-public-access-block.json     # All 4 public access blocks active (True)
│   ├── s3-encryption.json              # Default AES256 server-side encryption
│   ├── s3-objects-list.json            # Verified release archive & demonstration report
│   └── s3-verification-summary.txt     # Proof of S3 report generation and pre-signed retrieval
├── 05-iam/
│   ├── ec2-role.json                   # IAM Role finance-tracker-ec2-role & trust policy
│   ├── ec2-inline-policies.json        # Scoped inline policies for S3, SSM, and CloudWatch
│   └── iam-verification-summary.txt    # Least-privilege architecture & permission boundary
├── 06-ssm-parameter-store/
│   ├── parameters-description.json     # Catalog of all 8 application parameters
│   └── ssm-verification-summary.txt    # Zero plaintext leak proof (SecureString for secrets)
├── 07-cloudwatch/
│   ├── cloudwatch-log-group.json       # Log group /finance-tracker/app (7-day retention)
│   ├── cloudwatch-alarm.json           # Metric alarm finance-tracker-ec2-high-cpu (>80%)
│   └── cloudwatch-verification-summary.txt # Observability and alarming configuration
├── 08-sns/
│   ├── sns-topic-attributes.json       # Topic finance-tracker-alerts attributes
│   ├── sns-subscriptions.json          # Confirmed email subscriber (masked)
│   ├── sns-topic-policy.json           # Dual-publishing policy (CloudWatch + AWS Budgets)
│   └── sns-verification-summary.txt    # Central alerting integration
├── 09-aws-budgets/
│   ├── budget-description.json         # Monthly $20.00 USD cost guardrail
│   ├── budget-notifications.json       # 4 Alert thresholds (50%, 80%, 100% actual, 100% forecast)
│   └── budgets-verification-summary.txt # Cost guardrail and warning-only governance
├── 10-docker/
│   ├── Dockerfile.txt                  # Production Dockerfile configuration
│   ├── dockerignore.txt                # .dockerignore rules excluding .env and secrets
│   └── docker-verification-summary.txt # Containerization runtime and security verification
├── 11-terraform/
│   ├── terraform-validate-output.txt   # Output of terraform validate (Success!)
│   └── terraform-resources-inventory.txt # 40 Managed resources inventory from state
```

---

## 2. AWS Console Screenshot Navigation Guide

For your viva presentation or project report, capture genuine screenshots from the AWS Console using the exact steps below:

### Screenshot 1: EC2 Running Instance & Status Checks
1. Log into AWS Console -> Set Region to **Asia Pacific (Mumbai) `ap-south-1`**.
2. Navigate to **EC2** -> Click **Instances**.
3. Select instance `EC2_INSTANCE_ID_REDACTED`.
4. Capture the top summary showing: **Instance state: Running**, **Public IPv4 address: PUBLIC_IP_REDACTED**, **Instance type: t3.micro**.
5. Switch to the **Status checks** tab below -> Capture **2/2 checks passed**.

### Screenshot 2: VPC Topology & Route Tables
1. Navigate to **VPC** -> Click **Your VPCs**.
2. Select `VPC_ID_REDACTED` -> Capture IPv4 CIDR `10.0.0.0/16`.
3. Click **Subnets** -> Filter by VPC `VPC_ID_REDACTED`.
4. Capture the 3 subnets (`PUBLIC_SUBNET_ID_REDACTED` Public A, `subnet-08ffebdb5b8bbec1d` Private A, `subnet-0c868019b16521566` Private B).
5. Click **Route tables** -> Capture `PUBLIC_RTB_ID_REDACTED` showing `0.0.0.0/0 -> IGW_ID_REDACTED`.

### Screenshot 3: Security Groups (Port 22 Closed & Port 3306 Restricted)
1. In EC2/VPC console -> Click **Security groups**.
2. Select `finance-tracker-app-sg` (`APP_SG_ID_REDACTED`).
3. Capture the Inbound rules: Only HTTP (port 80) is open; SSH port 22 is completely absent!
4. Select `finance-tracker-db-sg` (`DB_SG_ID_REDACTED`).
5. Capture the Inbound rules: Port 3306 is allowed ONLY from `APP_SG_ID_REDACTED` (zero public access).

### Screenshot 4: RDS MySQL Private Database
1. Navigate to **RDS** -> Click **Databases**.
2. Select `finance-tracker-mysql`.
3. Capture the **Connectivity & security** tab:
   - Endpoint: `RDS_ENDPOINT_REDACTED`
   - Publicly accessible: **No**
4. Capture the **Configuration** tab:
   - Engine version: **MySQL 8.0.46**
   - DB instance class: **db.t3.micro**
   - Storage encryption: **Enabled**

### Screenshot 5: S3 Bucket Security & Demonstration Report
1. Navigate to **Amazon S3** -> Click bucket `finance-tracker-reports-S3_BUCKET_REDACTED`.
2. Click **Permissions** tab -> Capture **Block public access (bucket settings)**: all 4 settings are **On**.
3. Click **Properties** tab -> Capture **Default encryption: Server-side encryption with Amazon S3 managed keys (SSE-S3 / AES256)**.
4. Click **Objects** tab -> Navigate into `monthly-reports/user-1/2026-11/`.
5. Capture the demonstration report: `report-d34b7611bcc94060b843c791c761d5f5.csv` (218 B).

### Screenshot 6: IAM EC2 Role & Least-Privilege Policies
1. Navigate to **IAM** -> Click **Roles**.
2. Select `finance-tracker-ec2-role`.
3. Capture the attached policies: `AmazonSSMManagedInstanceCore` and the 3 inline policies (`finance-tracker-s3-reports`, `finance-tracker-cloudwatch-logs`, `finance-tracker-ssm-parameters`).
4. Expand one inline policy to show scoped ARNs (e.g. `arn:aws:s3:::finance-tracker-reports-S3_BUCKET_REDACTED/monthly-reports/*`).

### Screenshot 7: SSM Parameter Store
1. Navigate to **Systems Manager** -> Click **Parameter Store**.
2. Capture the list of 8 parameters under `/finance-tracker/`.
3. Highlight that `DB_PASSWORD` and `SECRET_KEY` have Type **SecureString** and values are obscured.

### Screenshot 8: CloudWatch Logs & CPU Alarm
1. Navigate to **CloudWatch** -> Click **Log groups**.
2. Select `/finance-tracker/app` -> Capture Retention: **7 days** and Log streams: `finance-tracker-app`.
3. Click **Alarms** in the left menu -> Click `finance-tracker-ec2-high-cpu`.
4. Capture the graph showing threshold at **80%**, status **OK**, and Action pointing to `finance-tracker-alerts`.

### Screenshot 9: SNS Topic & Confirmed Email Subscription
1. Navigate to **Amazon SNS** -> Click **Topics**.
2. Select `finance-tracker-alerts`.
3. Capture the **Subscriptions** table showing Protocol: **Email**, Status: **Confirmed** (mask the username part if presenting).
4. Click **Access policy** -> Highlight statements `AllowCloudWatchAlarmsToPublish` and `AllowBudgetsToPublish`.

### Screenshot 10: AWS Budgets $20 Guardrail
1. Navigate to **AWS Budgets** (via Billing and Cost Management).
2. Select budget `finance-tracker-monthly-cost-guardrail`.
3. Capture the budget overview:
   - Budgeted amount: **$20.00**
   - Current actual spend: **$0.00**
   - Current forecasted spend: **$0.79**
4. Click **Alerts** tab -> Capture the 4 configured alerts (50%, 80%, 100% actual, 100% forecast).

### Screenshot 11: Live Web Application
1. Open a browser to `http://PUBLIC_IP_REDACTED`.
2. Capture the clean, styled Homepage with login/register links.
3. Capture the Dashboard after logging in, showing metrics, budget progress, and transaction tables.
