# AWS Finance Tracker — Production Cloud Architecture

This document provides the definitive architectural blueprint of the AWS Finance Tracker deployment, highlighting security boundaries, service interactions, and data flows.

---

## 1. High-Level Architecture Diagram (Mermaid)

```mermaid
flowchart TD
    %% External Actors
    User([End User / Browser])
    Admin([Project Administrator / Alerts Email])
    DevOps([DevOps Engineer / Terraform CLI])

    %% Infrastructure as Code
    subgraph IaC ["Infrastructure as Code (IaC)"]
        TF["Terraform 1.10<br/>(40 Managed Resources)"]
    end
    DevOps -.->|terraform apply / validate| TF

    %% Cost Governance (Manual / Outside Terraform)
    subgraph CostGovernance ["Cost Governance (Manual Outside Terraform)"]
        Budgets["AWS Budgets ($20.00 USD Limit)<br/>finance-tracker-monthly-cost-guardrail<br/>4 Alerts: 50%, 80%, 100% Actual & 100% Forecast"]
    end

    %% AWS Cloud Boundary
    subgraph AWSCloud ["AWS Cloud (Account: AWS_ACCOUNT_ID_REDACTED | Region: ap-south-1)"]
        
        %% Internet Gateway
        IGW["Internet Gateway<br/>(IGW_ID_REDACTED)"]

        %% Custom VPC
        subgraph VPC ["Amazon VPC (VPC_ID_REDACTED | 10.0.0.0/16)"]
            
            %% Public Subnet
            subgraph PublicSubnet ["Public Subnet A (PUBLIC_SUBNET_ID_REDACTED | 10.0.1.0/24)"]
                direction TB
                EIP["Elastic IP<br/>PUBLIC_IP_REDACTED"]
                
                subgraph AppSG ["Security Group: finance-tracker-app-sg"]
                    EC2["Amazon EC2 Instance (t3.micro)<br/>(EC2_INSTANCE_ID_REDACTED | Private IP: PRIVATE_IP_REDACTED)<br/>Port 22 SSH: CLOSED | Port 80 HTTP: OPEN"]
                    
                    subgraph DockerEnv ["Docker Runtime Environment"]
                        Gunicorn["Gunicorn WSGI (2 Workers)"]
                        Flask["Flask Finance Tracker App<br/>(Port 5000)"]
                        Container["Container: finance-tracker-app<br/>Image: finance-tracker-web"]
                        Container --- Flask
                        Flask --- Gunicorn
                    end
                    EC2 --- Container
                end
                EIP --- EC2
            end

            %% Private Subnets
            subgraph PrivateSubnets ["Private Subnets (Air-Gapped Database Tier - Zero IGW Route)"]
                direction TB
                subgraph DBSG ["Security Group: finance-tracker-db-sg (Port 3306 from App SG Only)"]
                    RDS[("Amazon RDS MySQL 8.0 (db.t3.micro)<br/>finance-tracker-mysql<br/>(Private IP: 10.0.10.148:3306)<br/>Storage: Encrypted via AWS KMS<br/>Publicly Accessible: False")]
                end
                SubnetPrivA["Private Subnet A (10.0.10.0/24)"]
                SubnetPrivB["Private Subnet B (10.0.11.0/24)"]
                SubnetPrivA --- RDS
                SubnetPrivB --- RDS
            end
        end

        %% Managed AWS Auxiliary Services
        subgraph StorageServices ["Secure Storage & Configuration"]
            S3[("Amazon S3 Bucket<br/>finance-tracker-reports-S3_BUCKET_REDACTED<br/>• SSE-S3 (AES256)<br/>• All 4 Public Access Blocks Active<br/>• Pre-signed URLs for Downloads")]
            SSM["AWS Systems Manager Parameter Store<br/>/finance-tracker/* (8 Parameters)<br/>• SecureString: DB_PASSWORD, SECRET_KEY"]
            IAM["AWS IAM Role & Profile<br/>finance-tracker-ec2-role<br/>• Scoped Least-Privilege Policies<br/>• AmazonSSMManagedInstanceCore"]
        end

        subgraph MonitoringServices ["Observability & Alerting"]
            CWL["Amazon CloudWatch Logs<br/>Log Group: /finance-tracker/app<br/>Retention: 7 Days"]
            CWA["CloudWatch Metric Alarm<br/>finance-tracker-ec2-high-cpu (>80% CPU)"]
            SNS["Amazon SNS Topic<br/>finance-tracker-alerts<br/>Dual-Publish Policy (CloudWatch + Budgets)"]
        end
    end

    %% Network & Request Flows
    User -->|1. HTTP GET/POST :80 (Cleartext)| EIP
    EIP -->|Port 80 Forwarded to Container :5000| Container
    Container -->|2. Private SQL Query :3306| RDS
    Container -->|3. Fetch KMS Secrets at Startup| SSM
    Container -->|4. Put / Get Encrypted Reports| S3
    Container -->|5. Stream Gunicorn Logs| CWL
    EC2 -.->|Assumes Attached Role| IAM
    EC2 -->|Metrics: CPUUtilization| CWA
    CWA -->|6. Trigger Alarm State| SNS
    Budgets -->|7. Send Cost Warning Alerts| SNS
    SNS -->|8. Email Notifications| Admin
    TF -.->|Manages 40 Cloud Resources| AWSCloud
```

---

## 2. Core Service Components & Roles

| Service | Identifier | Project Role | Security Control |
| :--- | :--- | :--- | :--- |
| **1. Amazon EC2** | `EC2_INSTANCE_ID_REDACTED` | Computes application logic, hosts Docker engine | Ingress restricted to port 80; SSH port 22 closed; IAM role attached |
| **2. Amazon VPC** | `VPC_ID_REDACTED` | Network isolation (`10.0.0.0/16`) | Dual-tier subnet segregation: 1 public subnet with IGW, 2 private subnets without IGW |
| **3. Amazon RDS** | `finance-tracker-mysql` | Relational data persistence (MySQL 8.0) | `PubliclyAccessible=False`; DB SG restricts port 3306 to EC2 SG; KMS encryption at rest |
| **4. Amazon S3** | `finance-tracker-reports-S3_BUCKET_REDACTED` | Secure archive for monthly financial CSV reports | 100% private; all 4 Public Access Blocks enabled; default `AES256` encryption |
| **5. AWS IAM** | `finance-tracker-ec2-role` | Grants temporary credentials to EC2 without keys | Scoped least-privilege inline policies for S3, CloudWatch Logs, and SSM Parameter Store |
| **6. AWS SSM Parameter Store** | `/finance-tracker/*` | Centralized runtime configuration & credentials | DB password & Flask secret key stored as `SecureString` (KMS encrypted); no hardcoded secrets |
| **7. Amazon CloudWatch** | `/finance-tracker/app` | Application logging and infrastructure alarms | Gunicorn access/error logs retained for 7 days; CPU alarm evaluates `CPUUtilization > 80%` |
| **8. Amazon SNS** | `finance-tracker-alerts` | Central pub/sub notification hub | Resource policy allows publishing strictly from CloudWatch Alarm and AWS Budgets; verified email subscriber |
| **9. AWS Budgets** | `finance-tracker-monthly-cost-guardrail` | Cost governance warning system ($20.00/mo) | 4 Alert thresholds (50%, 80%, 100% actual, 100% forecast); manually managed outside Terraform |
| **Docker** | `finance-tracker-app` | Containerized application runtime | Isolated Python 3.10 environment; secrets excluded at build-time via `.dockerignore` |
| **Terraform** | `terraform/app` | Infrastructure as Code orchestration | Exactly 40 managed resources; tracks infrastructure state with zero configuration drift |

---

## 3. End-to-End Data and Traffic Flow

1. **User Ingress:**  
   The user navigates to `http://PUBLIC_IP_REDACTED`. The request hits the Elastic IP attached to the EC2 instance in Public Subnet A. Security Group `finance-tracker-app-sg` admits incoming traffic on TCP port 80.
   *(Note: The current academic prototype terminates traffic on HTTP port 80; HTTPS with TLS certificate is recommended prior to handling real personal financial data).*
2. **Container Processing:**  
   Docker maps host port 80 to container port 5000. Inside the container, Gunicorn WSGI spawns 2 worker processes running the Flask application.
3. **Database Access:**  
   When querying transactions, budgets, or user profiles, Flask communicates directly with RDS MySQL (`RDS_ENDPOINT_REDACTED:3306`) over the internal VPC network. Traffic never touches the public internet.
4. **Configuration Retrieval:**  
   At container launch, `refresh-env.sh` uses the AWS CLI to query AWS Systems Manager Parameter Store. The attached IAM Instance Profile provides credentials automatically. Parameter Store decrypts `DB_PASSWORD` and `SECRET_KEY` on the fly.
5. **Report Export & Storage:**  
   When a user clicks "Export Monthly Report", Flask generates a sanitized CSV (neutralizing formula injection attempts like `=SUM(...)`), calls `boto3.client('s3').put_object()` with `ServerSideEncryption='AES256'`, and generates a time-limited pre-signed S3 download URL (15-minute TTL).
6. **Logging & Observability:**  
   Gunicorn outputs all access and error logs to `stdout`/`stderr`. The Docker logging driver forwards these logs to Amazon CloudWatch Log Group `/finance-tracker/app`.
7. **Infrastructure Monitoring & Alarms:**  
   CloudWatch monitors EC2 hypervisor metrics. If CPU utilization exceeds 80% for two consecutive 5-minute periods, CloudWatch Alarm `finance-tracker-ec2-high-cpu` fires, publishing a message to SNS topic `finance-tracker-alerts`.
8. **Cost Governance:**  
   AWS Budgets tracks monthly accrued spend and projected end-of-month spend. When spending reaches 50%, 80%, or 100% (or forecasted 100%), AWS Budgets publishes an alert to the same SNS topic, which notifies the verified subscriber email.







