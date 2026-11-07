# AWS Finance Tracker — 5 to 7 Minute College Project Demonstration Script

**Project Title:** Personal Finance Tracker — Multi-Tier Cloud Deployment on AWS  
**Student Presenter:** Cloud Computing Mini-Project Demonstration  
**Target Application URL:** `http://PUBLIC_IP_REDACTED`  
**Target Duration:** 5 to 7 Minutes  

---

## Demonstration Overview Timeline

```
[0:00 - 0:45] Phase 1: Project Introduction & Problem Statement
[0:45 - 2:30] Phase 2: Live Application Walkthrough & User Operations
[2:30 - 4:15] Phase 3: Cloud Infrastructure & Security Architecture
[4:15 - 5:30] Phase 4: Observability, Alerts & Cost Governance
[5:30 - 6:30] Phase 5: Infrastructure as Code (Terraform) & Conclusion
```

---

## Phase 1: Project Introduction (0:00 – 0:45)

> **Speaker:**  
> "Good morning, respected professors and evaluators. Today, I am demonstrating our Cloud Computing mini-project: the **AWS Personal Finance Tracker**.
> 
> Managing personal finances requires tracking cash flows, monitoring category budgets, and archiving monthly statements securely. However, deploying financial software to the cloud demands rigorous engineering: sensitive databases cannot be exposed to the public internet, secrets cannot be hardcoded, operational costs must be bounded, and infrastructure must be reproducible.
> 
> Our project implements a **resilient, secure, multi-tier cloud architecture on Amazon Web Services (AWS)** orchestrated entirely through Terraform Infrastructure as Code, utilizing 9 managed AWS services, Docker containerization, and automated cost guardrails."

---

## Phase 2: Live Application Walkthrough (0:45 – 2:30)

### Step 1: Open Live Homepage
> **Action:** In your web browser, navigate to `http://PUBLIC_IP_REDACTED`.  
> **Speaker:**  
> "Here is our live application running on an AWS EC2 instance in the Mumbai region (`ap-south-1`). The UI is built using Flask, styled responsively with Tailwind CSS. If I attempt to navigate directly to `/dashboard` without authentication, Flask's security filters intercept the request and redirect me to the login page."

### Step 2: Register / Login with Demonstration Account
> **Action:** Click **Register** (or **Login**). Create a test account (e.g., `demo_student` / `demo_student@college.edu`).  
> **Speaker:**  
> "I will register a demo user account. Passwords are never stored in plaintext; they are securely hashed using PBKDF2/SHA-256 before being committed to our Amazon RDS database."

### Step 3: Demonstrate CSV Transaction Import & Metrics
> **Action:** Click **Upload CSV** -> Upload a sample `transactions.csv` containing income and expense items.  
> **Speaker:**  
> "Users can import bank statements via CSV. Our backend validates the schema and protects against **Spreadsheet Formula Injection (CWE-1236)** by escaping malicious formula prefixes like `=SUM(...)`.  
> As you can see, the dashboard immediately calculates our Net Cash Flow, total income, and total expenses in real time."

### Step 4: Category Budget Tracking
> **Action:** Click **Budgets** -> Set a budget of **$250.00** for **Utilities**.  
> **Speaker:**  
> "We also feature category-level budget tracking. Here, I configure a $250 monthly budget for Utilities. As expenses in this category are logged, the progress bar reflects real-time percentage consumption."

### Step 5: Export Monthly Report to Amazon S3
> **Action:** Navigate to **Transactions** -> Click **Export Monthly Report** for current month (`2026-11`).  
> **Speaker:**  
> "When I click 'Export Monthly Report', the application generates a consolidated statement, encrypts it using `AES256`, and uploads it directly to our private **Amazon S3 bucket**.  
> To maintain complete privacy, the bucket has all public access blocked. The application generates a secure, time-limited **pre-signed URL** valid for 15 minutes, allowing me to download the file directly from S3 without exposing the bucket to the public internet."

---

## Phase 3: Cloud Infrastructure & Security Architecture (2:30 – 4:15)

### Step 6: Custom VPC & Network Segmentation
> **Action:** Switch to AWS Console -> **VPC** -> Show Subnets and Route Tables.  
> **Speaker:**  
> "Let us inspect the cloud infrastructure supporting this application.  
> We provisioned a custom **Amazon VPC** (`10.0.0.0/16`) divided into two tiers:
> 1. A **Public Subnet** with an Internet Gateway, hosting our EC2 compute instance.
> 2. Two **Private Subnets** spanning two availability zones, strictly for our database tier. These subnets have no route to the Internet Gateway."

### Step 7: EC2, Docker & Closed Port 22
> **Action:** Open **EC2 Console** -> Select `EC2_INSTANCE_ID_REDACTED` -> Show Security Group.  
> **Speaker:**  
> "Our EC2 instance runs inside Docker. Notice our Security Group: **SSH port 22 is completely closed**. We do not use SSH keys that could be leaked or brute-forced. Instead, administrative access is conducted via AWS Systems Manager Session Manager. Only HTTP port 80 is admitted for web traffic."

### Step 8: RDS MySQL Private Isolation
> **Action:** Open **RDS Console** -> Show `finance-tracker-mysql` -> Connectivity tab.  
> **Speaker:**  
> "Our relational database is **Amazon RDS MySQL 8.0**. Notice that **Publicly Accessible is set to NO**. Its Security Group permits inbound traffic on port 3306 **only from the EC2 instance's Security Group**. Even if an attacker knew the database credentials, they cannot connect from the outside world."

### Step 9: IAM Least-Privilege & Parameter Store
> **Action:** Open **Systems Manager** -> **Parameter Store** -> Show `/finance-tracker/` parameters.  
> **Speaker:**  
> "We practice zero-trust secrets management. The application code and Docker image contain zero hardcoded passwords. Database credentials and Flask secret keys are stored in **AWS Systems Manager Parameter Store** as encrypted **SecureString** parameters managed by AWS KMS.  
> The EC2 instance retrieves them at startup via an attached **IAM Role** governed by a strict permissions boundary and least-privilege inline policies."

---

## Phase 4: Observability, Alerts & Cost Governance (4:15 – 5:30)

### Step 10: Amazon CloudWatch Logs & CPU Alarm
> **Action:** Open **CloudWatch Console** -> Show `/finance-tracker/app` log group and Alarm.  
> **Speaker:**  
> "For operational visibility, we configured **Amazon CloudWatch**:
> 1. **CloudWatch Logs:** Live Gunicorn web server logs are streamed to `/finance-tracker/app` with a 7-day retention policy to avoid unnecessary storage costs.
> 2. **CloudWatch Alarms:** Alarm `finance-tracker-ec2-high-cpu` monitors EC2 CPU utilization. If CPU exceeds 80% for 10 minutes, it automatically triggers an alert."

### Step 11: Amazon SNS Centralized Alerting
> **Action:** Open **SNS Console** -> Show topic `finance-tracker-alerts` and Confirmed subscription.  
> **Speaker:**  
> "All alerts route through **Amazon SNS**. Our topic has a verified email subscriber. Its access policy authorizes both CloudWatch Alarms and AWS Budgets to publish notifications."

### Step 12: AWS Budgets ($20 Monthly Cost Guardrail)
> **Action:** Open **AWS Budgets Console** -> Show `finance-tracker-monthly-cost-guardrail`.  
> **Speaker:**  
> "A major challenge in cloud computing is avoiding unexpected bills. We implemented a strict **$20.00 USD monthly cost guardrail** in AWS Budgets with 4 proactive alerts:
> - 50% of actual spend ($10)
> - 80% of actual spend ($16)
> - 100% of actual spend ($20)
> - 100% of forecasted month-end spend ($20)
> When triggered, an email warning is dispatched via SNS, giving us ample time to intervene."

---

## Phase 5: Infrastructure as Code & Conclusion (5:30 – 6:30)

### Step 13: Terraform Orchestration
> **Action:** Switch to terminal -> Show `terraform validate` and state list.  
> **Speaker:**  
> "Every piece of infrastructure shown today—VPC, subnets, route tables, security groups, EC2 instance profile, RDS database, S3 bucket, CloudWatch alarms, and SNS topics—is defined in **Terraform**.  
> Our Terraform state manages **exactly 40 cloud resources**, validated and version-controlled with zero configuration drift."

### Step 14: Conclusion & Viva Readiness
> **Speaker:**  
> "In conclusion, the AWS Personal Finance Tracker demonstrates how a modern web application can be built, containerized, securely hosted, monitored, and financially governed using industry-standard AWS best practices.  
> 
> Thank you, and I am now ready for your questions."
