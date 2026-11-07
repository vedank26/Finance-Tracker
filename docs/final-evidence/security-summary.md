# AWS Finance Tracker — Security Architecture & Threat Model Summary

This document summarizes the defensive controls, architectural boundaries, and security mechanisms implemented in the AWS Finance Tracker deployment.

---

## 1. Multi-Layered Defense Architecture

```
Layer 1: Perimeter & Network Security (Amazon VPC, Route Tables, Security Groups)
  │
Layer 2: Compute & Container Isolation (EC2 t3.micro, Docker, .dockerignore)
  │
Layer 3: Identity & Credential Governance (AWS IAM Role, Permissions Boundary, SSM)
  │
Layer 4: Data at Rest & in Transit (AWS KMS, RDS Encryption, S3 SSE-S3 AES256)
  │
Layer 5: Application Application Security (CSRF Tokens, Password Hashing, CWE-1236 Defense)
```

---

## 2. Detailed Security Controls Inventory

### A. Network & Perimeter Security
1. **Network Segmentation via Custom VPC (`10.0.0.0/16`):**
   - Public subnet (`10.0.1.0/24`) is strictly segregated from private database subnets (`10.0.10.0/24` & `10.0.11.0/24`).
   - The private database subnets have **no route table entry to the Internet Gateway** and no NAT Gateway, creating an air-gapped data tier.
2. **Elimination of SSH Attack Surface (Port 22 Closed):**
   - Security Group `finance-tracker-app-sg` has **no inbound rule for port 22**.
   - Traditional SSH private keys (`.pem` / `.id_rsa`) are completely absent, mitigating credential theft, credential stuffing, and SSH brute-force attacks.
   - Remote administration is mediated through **AWS Systems Manager Session Manager** using IAM-authenticated web sessions with full audit trails in AWS CloudTrail.
3. **Database Firewall Rules (Principle of Least Privilege Networking):**
   - RDS Security Group `finance-tracker-db-sg` accepts incoming connections on port 3306 **exclusively** from the application security group `finance-tracker-app-sg`.
   - Direct inbound connections from any public IP (`0.0.0.0/0`) are rejected at the hypervisor level.

---

### B. Database & Storage Security
1. **Air-Gapped RDS MySQL:**
   - Parameter `PubliclyAccessible` is set to `False`. The database endpoint resolves to an internal private IP (`10.0.10.148`) unreachable outside the VPC.
   - Database storage is encrypted at rest using AWS KMS managed encryption keys.
2. **Private Amazon S3 Bucket Architecture:**
   - S3 bucket `finance-tracker-reports-S3_BUCKET_REDACTED` has **all four Amazon S3 Public Access Block controls activated**:
     - `BlockPublicAcls = True`
     - `IgnorePublicAcls = True`
     - `BlockPublicPolicy = True`
     - `RestrictPublicBuckets = True`
   - Default Server-Side Encryption (`SSE-S3` / `AES256`) is enforced on all stored objects.
3. **Time-Limited Pre-signed URLs for Downloads:**
   - End-users never access S3 objects via public URLs.
   - When an authenticated user downloads a monthly report, Flask verifies user ownership of the file path, generates a cryptographically signed pre-signed S3 URL with a 15-minute (900s) time-to-live (TTL), and redirects the browser. After 15 minutes, the link expires automatically.

---

### C. Identity & Secrets Management
1. **Zero Hardcoded Secrets in Source Code or Images:**
   - No database passwords, secret keys, or AWS access tokens are committed to Git or baked into the Docker image.
   - `.dockerignore` explicitly excludes `.env`, `refresh-env.sh`, `*.pem`, `*.key`, and `terraform/` from the build context.
2. **AWS Systems Manager (SSM) Parameter Store:**
   - `DB_PASSWORD` and `SECRET_KEY` are stored as encrypted **SecureString** parameters in AWS Parameter Store using AWS KMS.
   - Environment variables are dynamically fetched and decrypted into memory/runtime files at container initialization via `refresh-env.sh`.
3. **IAM Role with Least Privilege & Permissions Boundary:**
   - EC2 assumes `finance-tracker-ec2-role` via an IAM Instance Profile.
   - Inline policies grant scoped actions only on required resources (e.g., `s3:PutObject` on `arn:aws:s3:::finance-tracker-reports-S3_BUCKET_REDACTED/monthly-reports/*`).
   - The role is bounded by `FinanceTracker-PermissionsBoundary`, preventing unauthorized privilege escalation.

---

### D. Application-Level Security Defenses
1. **Cross-Site Request Forgery (CSRF) Protection:**
   - Flask-WTF CSRF protection is initialized globally (`CSRFProtect(app)`).
   - Every state-modifying POST request (`/register`, `/login`, `/upload`, `/budgets`, `/transactions/export-monthly`) requires a valid CSRF token in the request header (`X-CSRFToken`) or form body.
2. **Cryptographic Password Hashing:**
   - Passwords are never stored in plaintext or reversible formats.
   - Werkzeug's `generate_password_hash` hashes passwords using PBKDF2 with SHA-256 and unique per-user cryptographic salts.
3. **Spreadsheet Formula Injection Defense (CWE-1236):**
   - Financial statement exports sanitize all text cells. If a transaction description or category begins with formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`), function `sanitize_csv_cell()` prepends a single quotation mark (`'`), neutralizing formula execution in Microsoft Excel, Google Sheets, or LibreOffice Calc.
4. **Session Cookie Hardening:**
   - Session cookies are issued with the `HttpOnly` flag, preventing client-side JavaScript access via Cross-Site Scripting (XSS).

---

### E. HTTPS Readiness & Current Posture
- **Current Academic Prototype:** The application is currently served over unencrypted HTTP on TCP port 80 (`http://PUBLIC_IP_REDACTED`).
- **Limitation:** Cleartext HTTP is acceptable for synthetic data demonstration but insecure for real financial credentials.
- **Recommended Remediation (Option A):** Deploy an Nginx reverse proxy on the EC2 host with a free automated Let's Encrypt TLS certificate (using Certbot), binding the Docker container to `127.0.0.1:5000` and redirecting port 80 to port 443 with zero extra AWS recurring cost.
