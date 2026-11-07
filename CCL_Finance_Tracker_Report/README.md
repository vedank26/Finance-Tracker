# Cloud Computing Laboratory (CCL) Project Deliverables
## AWS Cloud – Finance Tracker

This directory contains the complete academic project documentation, formal reports, architecture diagrams, and operational evidence for the **AWS Cloud – Finance Tracker** project.

---

### Deliverables Directory Structure

```
CCL_Finance_Tracker_Report/
│
├── CCL_Finance_Tracker_Report.docx        # Complete Editable Academic Report (Microsoft Word Format)
├── CCL_Finance_Tracker_Report.pdf         # Final Printable Academic Report (High-Resolution PDF)
├── CCL_Finance_Tracker_Academic_Report.md # Full 41-Chapter Markdown Master Document
├── aws_finance_tracker_architecture.jpg  # High-Resolution Master AWS Architecture Diagram
│
├── diagrams/                              # Editable Mermaid (.mmd) Architecture Source Files
│   ├── 01_main_system_architecture.mmd
│   ├── 02_application_request_response_workflow.mmd
│   ├── 03_database_connectivity_flow.mmd
│   ├── 04_report_generation_s3_storage_flow.mmd
│   ├── 05_parameter_store_secrets_retrieval.mmd
│   ├── 06_cloudwatch_sns_alert_workflow.mmd
│   ├── 07_terraform_infrastructure_provisioning.mmd
│   └── 08_database_er_diagram.mmd
│
└── screenshots/                           # Visual Operational Evidence
    ├── architecture_diagram.jpg           # AWS Architecture Diagram
    └── app_dashboard.png                  # Live Running Web Application Interface (http://PUBLIC_IP_REDACTED)
```

---

### Core Architecture Summary

| Architectural Domain | AWS Service / Technology | Implementation Details |
| :--- | :--- | :--- |
| **Compute Tier** | Amazon EC2 (`t3.micro`) | Amazon Linux 2023, Docker container `finance-tracker-app` |
| **Application Server**| Gunicorn WSGI + Flask 3.0 | 2 workers, 4 threads per worker, port 5000 |
| **Network Boundary** | Amazon VPC (`10.0.0.0/16`) | Custom VPC in Mumbai (`ap-south-1`), IGW, public & private subnets |
| **Database Tier** | Amazon RDS MySQL 8.0 | `db.t3.micro`, isolated in private subnets, KMS encrypted |
| **Report Storage** | Amazon S3 | Bucket `finance-tracker-reports-S3_BUCKET_REDACTED`, SSE-S3 AES-256 |
| **Secret Management**| AWS SSM Parameter Store | Path `/finance-tracker/*` (14 parameters, KMS SecureString) |
| **Identity & Access** | AWS IAM Instance Profile | `finance-tracker-ec2-role` with least privilege policies |
| **Observability** | Amazon CloudWatch | Log group `/finance-tracker/app` (7-day retention), CPU alarm (>80%) |
| **Notification** | Amazon SNS | Topic `finance-tracker-alerts`, verified email subscription |
| **Cost Governance** | AWS Budgets | Monthly $20.00 USD guardrail, 4 alerting thresholds |
| **Infrastructure** | Terraform (IaC) | 11 configuration files, exactly 40 managed resources |

---

### Report Structure (41 Chapters Included)
1. Cover Page & University Metadata
2. College Certificate of Completion
3. Student Declaration
4. Acknowledgement
5. Abstract & Keywords
6. Table of Contents
7. List of Figures (10 Figures)
8. List of Tables (12 Tables)
9. Introduction to Cloud Computing
10. Introduction to the Finance Tracker
11. Problem Statement
12. Objectives
13. Project Scope & Boundaries
14. Existing System Analysis
15. Proposed Cloud-Native Architecture
16. Technologies & Libraries Used
17. AWS Cloud Services Justification Table
18. System Architecture (Master Topology)
19. Detailed Architecture Component Breakdown
20. VPC & Subnet Networking Design
21. Application Tier Architecture (Docker & Gunicorn)
22. Database Tier & MySQL Schema Architecture
23. Security & IAM Identity Governance
24. Financial Report Storage (Amazon S3)
25. Configuration Management (SSM Parameter Store)
26. Observability, Logging & Metric Alarms (CloudWatch)
27. Notification Mechanism (Amazon SNS)
28. Cloud Cost Governance (AWS Budgets)
29. Infrastructure as Code Pipeline (Terraform)
30. Implementation Methodology & Phased Milestones
31. Application Workflows (6 Comprehensive Flows)
32. Data Flow & Communication Trace
33. Testing, Verification & Forensic Audits
34. Results & Discussion (Latency, Throughput, Metrics)
35. Architectural Advantages
36. Architectural Limitations
37. Granular AWS Cost Breakdown (`ap-south-1`)
38. Future Enhancements & High-Availability Roadmap
39. Conclusion
40. References & Bibliography
41. Appendix & Evidence (Inventory, Logs, Screenshots, 25 Viva Questions)
