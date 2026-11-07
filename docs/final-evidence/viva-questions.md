# AWS Finance Tracker — Viva Voce Examination Questions & Model Answers

This guide contains 25 high-yield viva questions with model answers grounded in the real, deployed AWS Finance Tracker architecture.

---

### Q1: Why did you choose EC2 instead of a fully serverless architecture (like AWS Lambda)?
**Answer:**  
"While AWS Lambda is excellent for short-lived, event-driven functions, our Finance Tracker is a full-stack Flask application running a persistent Gunicorn WSGI server. EC2 (`t3.micro`) was selected because:
1. It eliminates Lambda cold starts, ensuring sub-second response times for dashboard charts and metrics.
2. It supports persistent background processing (e.g. running multiple WSGI workers).
3. It fits cleanly into the AWS Free Tier (750 hours/month of `t3.micro`).
4. It allows us to deploy standard Docker containers without complex API Gateway / Lambda adapter layers."

---

### Q2: Why did you create a custom VPC instead of using the Default VPC?
**Answer:**  
"The Default VPC provisions only public subnets where every attached resource receives a public IP address and default internet routing. For a financial application, this violates core security principles. By designing a custom VPC (`10.0.0.0/16`), we were able to create an isolated, air-gapped private database tier that has no route to the Internet Gateway, ensuring our database is unreachable from the internet."

---

### Q3: Why are RDS instances kept in private subnets?
**Answer:**  
"Keeping RDS in private subnets ensures defense in depth. Even if an attacker discovers or brute-forces the database master credentials, they cannot reach the database endpoint because the private subnets have no route to the Internet Gateway and `PubliclyAccessible` is set to `False`. The database can only be reached over internal private IPs (`10.0.10.148:3306`) by instances inside the authorized application security group."

---

### Q4: How does the EC2 instance connect to RDS?
**Answer:**  
"EC2 connects to RDS using MySQL TCP port 3306 across the internal VPC network. The connection is mediated by security group chaining: Database Security Group `finance-tracker-db-sg` contains an inbound rule permitting port 3306 only from Application Security Group `finance-tracker-app-sg`. The traffic travels privately across subnets without ever entering the public internet."

---

### Q5: Why is SSH port 22 closed on the EC2 instance?
**Answer:**  
"Closing port 22 eliminates the primary attack vector for Linux servers (brute-force attacks, port scanning, and stolen SSH private keys). Instead of SSH, we manage the server using **AWS Systems Manager Session Manager**. Session Manager operates via an outbound HTTPS agent over TLS, authenticating users via AWS IAM and logging all interactive terminal sessions in AWS CloudTrail for audit compliance."

---

### Q6: What is the purpose of an IAM Role, and why is it preferred over IAM User Access Keys?
**Answer:**  
"An IAM Role provides temporary, automatically rotated security credentials to AWS services (like our EC2 instance) without storing long-term secret access keys on disk. If we used static access keys in a `.env` file or config, they could be leaked via Git, compromised during an instance breach, or forgotten. IAM Roles eliminate credential management risks entirely."

---

### Q7: How does Least-Privilege IAM work in this project?
**Answer:**  
"Least privilege ensures a resource has only the minimum permissions required to perform its function. In our project:
- The EC2 role cannot delete S3 buckets; it can only `s3:PutObject` and `s3:GetObject` inside the specific `monthly-reports/*` prefix.
- It cannot access other SSM parameters; it can only read parameters prefixed with `/finance-tracker/*`.
- It cannot create IAM users or modify security groups.
- A **Permissions Boundary** is attached to ensure even if policies are altered, maximum permissions cannot exceed safe limits."

---

### Q8: Why use AWS Systems Manager Parameter Store instead of an `.env` file in the Git repository?
**Answer:**  
"Hardcoding secrets in Git repositories is the leading cause of cloud data breaches. Parameter Store centralizes configuration outside the codebase, allows fine-grained IAM access control, versions configuration changes, and encrypts sensitive credentials at rest using AWS KMS."

---

### Q9: What is a `SecureString` in Parameter Store, and how does it differ from a standard `String`?
**Answer:**  
"A standard `String` stores plaintext data (such as database hosts or port numbers). A `SecureString` automatically encrypts the data using an AWS Key Management Service (AWS KMS) customer master key upon storage. When retrieved, the client must possess `kms:Decrypt` permission to view the value. In our project, `DB_PASSWORD` and `SECRET_KEY` are stored as `SecureString`."

---

### Q10: Why use Docker for containerization on EC2?
**Answer:**  
"Docker encapsulates the Flask application, Gunicorn WSGI server, Python 3.10 runtime, and dependencies into an immutable image. This guarantees consistent behavior across development and production, isolates dependencies from the host OS, simplifies application deployment, and allows rapid restarts via systemd without dependency conflicts."

---

### Q11: How did you ensure sensitive files were not baked into the Docker image?
**Answer:**  
"We created a strict `.dockerignore` file in the build directory. It explicitly excludes `.env`, `refresh-env.sh`, `*.pem`, `*.key`, `terraform/`, and `.git/`. This guarantees that image layers contain only clean application source code. Credentials are dynamically injected into the container at runtime from Parameter Store."

---

### Q12: What is Infrastructure as Code (IaC), and why use Terraform?
**Answer:**  
"Infrastructure as Code is the practice of managing and provisioning cloud resources through machine-readable definition files rather than manual web console clicks. Terraform was chosen because:
1. It is declarative: we describe the desired end-state, and Terraform plans the transitions.
2. It tracks resource state: Terraform knows exactly which 40 resources belong to the project.
3. It guarantees repeatability: our entire AWS environment can be validated, audited, or redeployed reliably."

---

### Q13: Why did you choose Amazon S3 for storing monthly financial reports?
**Answer:**  
"Storing generated reports on the EC2 instance's local EBS volume risks data loss if the volume is terminated, corrupted, or re-created. Amazon S3 provides 99.999999999% (11 9s) of durability, built-in server-side encryption (`AES256`), lifecycle management, and enables secure, direct downloads via pre-signed URLs without routing heavy file downloads through the application server."

---

### Q14: How do Pre-Signed S3 URLs work, and why are they secure?
**Answer:**  
"A pre-signed URL grants temporary read access to a specific private S3 object using cryptographic signatures generated by the application's IAM credentials. The URL is valid for a limited time (we configured 900 seconds / 15 minutes). The bucket remains 100% private, and the user can download their file without the bucket having any public read permissions."

---

### Q15: How does CloudWatch logging work in your deployment?
**Answer:**  
"Gunicorn outputs access and error logs to standard output/error inside the container. Docker forwards these streams to Amazon CloudWatch Log Group `/finance-tracker/app`. We set a **7-day retention period** so logs automatically expire after one week, preventing unbounded storage costs."

---

### Q16: What does the CloudWatch CPU Alarm do?
**Answer:**  
"Alarm `finance-tracker-ec2-high-cpu` monitors the `CPUUtilization` metric of our EC2 instance. It evaluates 2 consecutive 5-minute periods (10 minutes total). If average CPU usage exceeds **80%**, the alarm state transitions from `OK` to `ALARM` and publishes an alert to Amazon SNS."

---

### Q17: What is Amazon SNS, and how is it used here?
**Answer:**  
"Amazon SNS (Simple Notification Service) is a managed pub/sub messaging service. In our architecture, topic `finance-tracker-alerts` acts as a centralized notification bus. When CloudWatch Alarms or AWS Budgets detect anomalies, they publish messages to this topic, which fans out real-time email notifications to the verified administrator email."

---

### Q18: What is the dual-publishing policy on your SNS topic?
**Answer:**  
"By default, an SNS topic accepts messages only from its owner. We wrote a custom resource policy with two explicit statements:
1. `AllowCloudWatchAlarmsToPublish`: allows `cloudwatch.amazonaws.com` to publish when the CPU alarm triggers.
2. `AllowBudgetsToPublish`: allows `budgets.amazonaws.com` restricted by `aws:SourceAccount = AWS_ACCOUNT_ID_REDACTED` and `aws:SourceArn` to publish cost guardrail alerts."

---

### Q19: How does the AWS Monthly Budget guardrail work?
**Answer:**  
"We created a monthly cost budget `finance-tracker-monthly-cost-guardrail` with a **$20.00 USD limit**. It monitors accrued and projected spending across all AWS services in our account and triggers 4 threshold alerts:
1. Actual spend > 50% ($10)
2. Actual spend > 80% ($16)
3. Actual spend > 100% ($20)
4. Forecasted spend > 100% ($20)"

---

### Q20: Does AWS Budgets automatically stop or shut down the EC2 instance?
**Answer:**  
"**No**. Our budget is configured as an **early warning system only**, without automatic shutdown actions. In production environments, automatically terminating servers can cause catastrophic data corruption, uncompleted transactions, or broken state. Instead, it sends immediate email alerts through SNS so engineers can investigate and intervene safely."

---

### Q21: What happens if the 100% forecast threshold is exceeded?
**Answer:**  
"AWS Budgets uses historical consumption trends and current run rates to project month-end spend. If the algorithm forecasts that total spend will reach or exceed $20.00 by the end of the month, it triggers an alert immediately—even if current actual spend is only $5.00—providing advance warning before any budget breach occurs."

---

### Q22: Why is the AWS Budget managed manually outside of Terraform?
**Answer:**  
"This is a deliberate governance decision. If the budget were defined inside Terraform, executing `terraform destroy` during infrastructure teardown or state updates would destroy the budget guardrail itself. Keeping the budget managed independently in the AWS Console guarantees that our financial guardrail remains permanently active regardless of IaC pipeline state."

---

### Q23: What is Spreadsheet Formula Injection (CWE-1236), and how did you prevent it?
**Answer:**  
"Formula injection occurs when untrusted user input (e.g. a transaction description like `=SUM(A1:A10)`) is exported into a CSV file. When opened in spreadsheet software like Microsoft Excel or Google Sheets, the application executes the formula, potentially executing malicious macros or exfiltrating data.  
We prevented this in `app/reports.py` by implementing function `sanitize_csv_cell()`: any text cell starting with `=`, `+`, `-`, `@`, `\t`, or `\r` is escaped with a leading single quotation mark (`'`), neutralizing formula execution."

---

### Q24: What is the current HTTPS status of the application, and what is your plan for it?
**Answer:**  
"The current academic prototype operates over unencrypted HTTP on port 80. While suitable for synthetic testing and grading, it is not secure for real financial credentials.  
Our proposal to achieve HTTPS with **zero recurring AWS cost** is to install an Nginx reverse proxy and Let's Encrypt Certbot directly on the EC2 instance once a custom domain is mapped to Elastic IP `PUBLIC_IP_REDACTED`. Nginx will handle TLS termination and redirect port 80 to 443, proxying traffic locally to Docker on port 5000."

---

### Q25: How many managed resources are in your Terraform state, and how do you ensure zero drift?
**Answer:**  
"There are **exactly 40 managed resources** in our Terraform state. We ensure zero configuration drift by validating all Terraform manifests (`terraform validate`), avoiding manual out-of-band modifications to managed resources, and isolating out-of-band resources (like our manual AWS budget) outside Terraform's state file."
