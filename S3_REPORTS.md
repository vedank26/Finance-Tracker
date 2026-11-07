# Amazon S3 Monthly CSV Reports Architecture & Security

## 1. Overview

The Finance Tracker application includes a monthly CSV report generation and archive service backed by Amazon Simple Storage Service (Amazon S3). This feature allows authenticated users to generate a consolidated CSV export of their transactions for any calendar month (`YYYY-MM`), securely archives the report in a private Amazon S3 bucket, and provides a short-lived presigned download URL for direct retrieval.

```
+-----------------------------------------------------------------------------------------+
|                                    User Browser                                         |
+-----------------------------------------------------------------------------------------+
       |                                                                     ^
       | 1. POST /transactions/export-monthly (month=YYYY-MM)                |
       v                                                                     |
+----------------------------------------------------------------------+     |
| Flask Application Server (EC2 / Container)                           |     |
|  - Validates month format (YYYY-MM) and user authentication          |     |
|  - Queries user's transactions within half-open month interval       |     |
|  - Sanitizes user input against CSV formula injection (CWE-1236)     |     |
|  - Formats CSV using Python's standard `csv` library                 |     |
|  - Uploads to Amazon S3 with AES256 server-side encryption           |     |
|  - Generates secure S3 presigned URL (15-min expiration)             |     |
|  - Redirects user to /reports/download?key=<object_key>              |     |
+----------------------------------------------------------------------+     |
       |                                                                     |
       | 2. S3 PutObject (SSE: AES256, ContentType: text/csv)                |
       v                                                                     |
+----------------------------------------------------------------------+     |
| Private Amazon S3 Bucket                                             |     |
|  - Key: monthly-reports/user-<id>/<YYYY-MM>/report-<uuid>.csv         |     |
|  - Server-side encryption: AES256                                    |     |
|  - Public access block: Enabled                                      |     |
+----------------------------------------------------------------------+     |
       ^                                                                     |
       | 3. Direct secure download via presigned S3 URL ---------------------+
```

---

## 2. Security & Compliance Architecture

### 2.1 Private S3 Bucket Policy
- **No Public Access:** The S3 bucket has Amazon S3 Block Public Access enabled on all four settings (`BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`).
- **No Public ACLs:** Objects are uploaded without public ACLs (`private` default).
- **Server-Side Encryption:** All uploads enforce `ServerSideEncryption='AES256'` (SSE-S3) at the API call level, ensuring data at rest is encrypted.

### 2.2 Object Key Hierarchy & User Isolation
Object keys follow a strictly partitioned structure:
```
monthly-reports/user-<user_id>/<YYYY-MM>/report-<uuid>.csv
```
- Reports are segmented by user ID in the key path.
- A cryptographically random UUID (`uuid.uuid4().hex`) prevents key enumeration or predictability.

### 2.3 Strict Authorization on Download
The `/reports/download` endpoint accepts an S3 object key via query parameter (`?key=...`) and validates user ownership before generating or redirecting to a presigned URL:
1. **Authentication:** Requires `@login_required`.
2. **Format Validation:** Uses regex `^monthly-reports/user-(\d+)/(\d{4}-\d{2})/report-([a-f0-9\-]+)\.csv$`.
3. **Traversal Mitigation:** Rejects any keys containing path traversal (`..`) or backslashes (`\`).
4. **User Ownership Verification:** Extracts the user ID from the key and ensures `int(key_user_id) == current_user.id`. Requests for other users' keys or arbitrary S3 keys are rejected with 403 / Access Denied.

### 2.4 Short-Lived Presigned URLs
- Downloads use presigned URLs generated via `s3_client.generate_presigned_url('get_object', ...)`.
- URLs expire after **900 seconds (15 minutes)**.
- URLs grant temporary, read-only access to the specific object without exposing AWS credentials to the client.

### 2.5 Spreadsheet Formula Injection Protection (CWE-1236)
Spreadsheet applications (Excel, Google Sheets, LibreOffice Calc) interpret cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` as formulas or commands. An attacker can craft malicious transaction descriptions or categories (e.g. `=cmd|' /C calc'!A0` or `@SUM(...)`).

Mitigation implemented in `app/reports.py`:
- User-controlled text fields (`description`, `category`) are sanitized by `sanitize_csv_cell(value)`.
- If the trimmed string begins with `=`, `+`, `-`, `@`, `\t`, or `\r`, the string is prepended with a single quote (`'`), instructing spreadsheet software to treat the value purely as text.
- Legitimate numeric amounts (e.g. `-150.00` for an expense) are output directly as formatted numbers (`f"{t.amount:.2f}"`) without prepending quotes, preserving calculation integrity in downstream spreadsheets.

---

## 3. AWS Credentials & IAM Role Policy

The application relies on the **standard AWS SDK credential provider chain**:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) if present.
2. Shared credentials file (`~/.aws/credentials`).
3. **Amazon EC2 Instance Profile / IAM Role** (recommended for production).

No AWS credentials are hard-coded in the application codebase or committed to Git.

### 3.1 Recommended IAM Policy for EC2 Instance Role
For production deployment, attach an IAM role to the EC2 instance running Finance Tracker with the following least-privilege policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowFinanceTrackerMonthlyReports",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::YOUR_REPORT_BUCKET_NAME/monthly-reports/*"
    }
  ]
}
```

---

## 4. Configuration Reference

| Environment Variable | Description | Default | Example |
|---|---|---|---|
| `S3_REPORT_BUCKET` | Name of the private S3 bucket for storing reports | *None (disabled)* | `my-finance-reports-prod` |
| `AWS_REGION` | AWS region where the bucket resides | `us-east-1` | `us-east-1` |

When `S3_REPORT_BUCKET` is unset, report export requests return a graceful informational message directing the administrator to set the environment variable.

---

## 5. Automated Testing Strategy (Mocked S3)

To ensure robust test coverage without requiring active AWS accounts or creating cloud resources during development, all S3 operations are tested via unit tests using `unittest.mock.patch('boto3.client')`.

Test cases in `scratch/test_s3_monthly_reports.py` verify:
1. **CSV Generation & Range:** Half-open interval inclusion (`start_date <= date < next_month_start`) and exclusion of preceding/following months.
2. **Formula Injection Sanitization:** Verification of prefixing on text starting with `=`, `+`, `-`, `@`, `\t`, `\r` and preservation of negative numeric amounts.
3. **Empty Month Reports:** Valid header row generated even when no transactions exist.
4. **User Isolation:** Transactions from User A never appear in User B's report.
5. **S3 PutObject Parameters:** Correct bucket, key, AES256 server-side encryption, and ContentType.
6. **Download Authorization:** Verification of ownership checking, traversal blocking (`..`), and malformed key rejection.
7. **Graceful Error Handling:** Safe messaging when S3 bucket is unconfigured or S3 client raises an error.
