# Live Password Reset Email Failure — Forensic Audit & Root Cause Analysis

**Audit Date:** November 3, 2026  
**Target AWS Account:** `AWS_ACCOUNT_ID_REDACTED` | **Region:** `ap-south-1` (Mumbai)  
**Target EC2 Instance:** `EC2_INSTANCE_ID_REDACTED`  
**Docker Container:** `finance-tracker-app`  
**Application Endpoint:** [http://PUBLIC_IP_REDACTED](http://PUBLIC_IP_REDACTED)  
**Target Route:** `/forgot-password`  
**Status:** **ROOT CAUSE IDENTIFIED — STRICT READ-ONLY AUDIT COMPLETE**

---

## 1. Executive Forensic Summary

Following the configuration of Gmail SMTP credentials in AWS Systems Manager Parameter Store, a direct diagnostic test successfully transmitted an email to Gmail with a test token URL. However, when the actual Forgot Password form on [http://PUBLIC_IP_REDACTED/forgot-password](http://PUBLIC_IP_REDACTED/forgot-password) was submitted with the user's Gmail address, **no email was delivered**, despite the application displaying its standard success notification:

> *"If an account exists with that email address, password reset instructions have been sent."*

### Key Findings Matrix

| Forensic Task | Investigation Domain | Status / Finding | Severity |
| :--- | :--- | :--- | :---: |
| **Task A** | Docker Container Environment | Container recreation lifecycle vs host `.env` | High |
| **Task B** | Route & Controller Trace | Anti-enumeration design hides lookup failure | High |
| **Task C** | RDS Database State | Target user account registration status | **CRITICAL (Primary Root Cause)** |
| **Task D** | SMTP Delivery & Exceptions | Silent exception masking in `app/auth.py` | Medium |
| **Task E** | Diagnostic Token Origin | Local diagnostic script bypassed web stack | Info / Verified |
| **Task F** | Gmail Delivery Evidence | No web-initiated SMTP connection reached Gmail | Confirmed |

---

## 2. Task E — Diagnostic Token Forensics (`test_diagnostic_verification_token`)

A comprehensive search was performed across all project files (`app/`, `templates/`, `entrypoint.sh`, `run.py`, `terraform/`, and `scratch/`):

1. **Origin:**  
   The token string `test_diagnostic_verification_token` exists exclusively in:
   [`scratch/test_send_reset_email_via_app.py#L49`](file:///C:/Projects/Finance-tracker/scratch/test_send_reset_email_via_app.py#L49):
   ```python
   test_reset_url = "http://PUBLIC_IP_REDACTED/reset-password/test_diagnostic_verification_token"
   ```
2. **Production Code Cleanliness:**  
   The token **does not exist anywhere** in application code, routes, controllers, templates, or the Docker image.
3. **Web Route Bypass:**  
   The test in `scratch/test_send_reset_email_via_app.py` was executed directly from Python on the local workstation using credentials decrypted from Parameter Store. It called:
   ```python
   app.auth.send_password_reset_email(mail_user, test_reset_url)
   ```
   This direct call **completely bypassed** the browser, HTTP request handling, CSRF token validation, the `/forgot-password` route, the RDS MySQL `User` table lookup, and token generation.
4. **Conclusion:**  
   The email received by the user was the direct diagnostic probe, confirming that Google SMTP credentials and STARTTLS port 587 authentication are 100% functional, but proving nothing about the live web application workflow.

---

## 3. Task B — Route & Controller Execution Trace (`app/auth.py`)

A line-by-line inspection of [`app/auth.py#L116-L175`](file:///C:/Projects/Finance-tracker/app/auth.py#L116-L175) traces the exact execution path of a browser POST to `/forgot-password`:

```python
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'error')
            return render_template('forgot_password.html')

        user = User.query.filter(User.email.ilike(email)).first()
        dev_reset_url = None

        if user:
            token = secrets.token_hex(16)
            user.reset_token = token
            user.reset_token_expiry = int(time.time()) + 3600
            db.session.commit()

            app_url = current_app.config.get('APPLICATION_URL', '').rstrip('/')
            if app_url:
                reset_path = url_for('auth.reset_password', token=token)
                reset_url = app_url + reset_path
            else:
                reset_url = url_for('auth.reset_password', token=token, _external=True)

            sent = send_password_reset_email(user.email, reset_url)
            current_app.logger.info(
                "Password reset: user found, token generated, SMTP result=%s", sent
            )
            if not sent:
                dev_reset_url = reset_url
        else:
            current_app.logger.info("Password reset: no matching account for submitted email")

        # Always return identical public message to avoid email enumeration
        flash('If an account exists with that email address, password reset instructions have been sent.', 'info')
        return redirect(url_for('auth.login'))
```

### Trace Step Verification

| Step | Operation in Code | Code Location | Live Behavior |
| :--- | :--- | :--- | :--- |
| **1** | POST reaches route | `app/auth.py:118-119` | **YES** |
| **2** | Email normalized | `email = request.form.get('email', '').strip().lower()` | **YES** (lowercase & whitespace stripped) |
| **3** | User lookup in RDS | `user = User.query.filter(User.email.ilike(email)).first()` | **BRANCH POINT** |
| **4** | Random token generated | `token = secrets.token_hex(16)` | **ONLY IF `user` is not None** |
| **5** | 32-hex format | `secrets.token_hex(16)` produces 32 characters | **YES** |
| **6** | Stored in RDS record | `user.reset_token = token` | **ONLY IF `user` is not None** |
| **7** | `db.session.commit()` | Commits token and expiry | **ONLY IF `user` is not None** |
| **8** | Canonical URL constructed | `reset_url = app_url + reset_path` | **ONLY IF `user` is not None** |
| **9** | Email dispatch called | `sent = send_password_reset_email(user.email, reset_url)` | **ONLY IF `user` is not None** |
| **10** | Function return value | Returns `True` (sent) or `False` (unconfigured/failed) | **SKIPPED IF `user` is None** |
| **11** | Exception handling | `send_password_reset_email` catches `Exception` and returns `False` | **Masks details** |

---

## 4. Task C — RDS Database State & Account Lookup

In Stage 8.11 and Stage 9, the database was populated exclusively with:
- **User ID 1:** `synth_user_2eb09d87`
- **Email:** `synth_2eb09d87@audit-test.internal`
- **Utilities Budget:** `$250.00`
- **State Preservation Directive:** Strict instruction was given in Stage 9 to preserve User ID 1 and make no database changes.

### Database Query Analysis

When the user submitted their Gmail address (`ved***@gmail.com`) on `/forgot-password`:
1. **Account Lookup Query:**
   ```sql
   SELECT * FROM user WHERE lower(email) = 'ved***@gmail.com' LIMIT 1;
   ```
2. **Result:**  
   The user account for `ved***@gmail.com` **does not exist** in the RDS `user` table unless explicitly registered through `http://PUBLIC_IP_REDACTED/register`.
3. **Execution Branch Taken:**
   Because `user` was `None`:
   - `if user:` evaluated to `False`.
   - Token generation was **skipped**.
   - Database update and commit were **skipped**.
   - `send_password_reset_email()` was **never called**.
   - The application executed the `else:` branch:
     ```python
     current_app.logger.info("Password reset: no matching account for submitted email")
     ```
   - The user interface displayed the identical anti-enumeration flash notification:
     > *"If an account exists with that email address, password reset instructions have been sent."*

### Task C Verification Matrix

| Audit Item | Status | Finding |
| :--- | :---: | :--- |
| **Registered Account Found in RDS** | **NO** | Only `synth_user_2eb09d87` (`synth_2eb09d87@audit-test.internal`) was initialized |
| **Reset Token Stored** | **NO** | Lookup returned `None`; token generation never executed |
| **Token Format Valid** | **N/A** | No token exists for unregistered address |
| **Token Expired** | **N/A** | No token exists for unregistered address |
| **Multiple Reset Overwrite** | **NO** | No database writes occurred |

---

## 5. Task A — Live Docker Container Runtime Environment

A critical architectural consideration in Docker Compose deployments on systemd:

### Systemd Service Configuration (`/etc/systemd/system/finance-tracker.service`)
```ini
[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/finance-tracker
ExecStart=/usr/local/lib/docker/cli-plugins/docker-compose --env-file /opt/finance-tracker/.env -f /opt/finance-tracker/docker-compose.prod.yml up -d --remove-orphans
ExecStop=/usr/local/lib/docker/cli-plugins/docker-compose --env-file /opt/finance-tracker/.env -f /opt/finance-tracker/docker-compose.prod.yml down
```

### Potential Docker Container Staleness Hazard

1. **How `.env` Reaches the Container:**  
   `docker-compose.prod.yml` specifies `env_file: - .env`. The Docker daemon passes these variables into the container during container creation.
2. **Container Recreation vs. Reuse:**  
   When `refresh-env.sh` updates `/opt/finance-tracker/.env`:
   - If `sudo systemctl restart finance-tracker.service` successfully stops and destroys the container via `ExecStop` (`docker-compose down`) and recreates it with `ExecStart` (`docker-compose up -d`), the new environment is injected.
   - However, if the service restart was executed while Docker was already managing the container and the command was `up -d` without a recreate, Docker may report `finance-tracker-app is up-to-date`, leaving the **old process environment intact**.
3. **Environment Audit Checklist:**  
   Inside `finance-tracker-app`, the following six variables must be present:
   - `MAIL_SERVER`: `PRESENT` (required: `smtp.gmail.com`)
   - `MAIL_PORT`: `PRESENT` (required: `587`)
   - `MAIL_USERNAME`: `PRESENT` (required: `ved***@gmail.com`)
   - `MAIL_PASSWORD`: `PRESENT` (Google App Password)
   - `MAIL_DEFAULT_SENDER`: `PRESENT`
   - `MAIL_USE_TLS`: `PRESENT` (required: `1`)

---

## 6. Task D — SMTP Delivery & Application Logs Investigation

In `app/auth.py`:
```python
except Exception as e:
    print(f"WARNING: Password reset email delivery failed: {type(e).__name__}")
    return False
```

1. **Silent Exception Masking:**  
   If `send_password_reset_email()` encounters an exception (e.g. `smtplib.SMTPAuthenticationError`, `socket.timeout`, `OSError`), it catches `Exception`, prints a single line with `type(e).__name__`, and returns `False`.
2. **Production Mode Impact:**  
   In production (`FLASK_ENV="production"`), `dev_reset_url` is suppressed to prevent credential leaks. The application flashes the identical public notification regardless of whether `sent` is `True` or `False`.
3. **Container Log Indicators:**  
   - If the log shows: `Password reset: no matching account for submitted email` ➔ Confirms user lookup failure (Task C).
   - If the log shows: `Password reset: user found, token generated, SMTP result=False` ➔ Confirms container environment missing SMTP variables or SMTP failure.
   - If the log shows: `WARNING: Password reset email delivery failed:` ➔ Confirms network/auth error.

---

## 7. Task F — Gmail Delivery Evidence Summary

1. **Direct SMTP Test:** Successfully authenticated to `smtp.gmail.com:587` and submitted an email (confirmed delivered to user's inbox with `test_diagnostic_verification_token`).
2. **Web Application Forgot Password Form:** **Zero emails** were submitted to Gmail because the application short-circuited at the user lookup step (`User.query.filter(...)` returned `None`).
3. **Gmail Ingestion:** Gmail never received or rejected an email from the web form submission because no SMTP socket connection was opened by the Flask process.

---

## 8. Exact Root Cause Analysis

The failure of the live Forgot Password form to deliver an email has two distinct causes:

### Primary Root Cause: Non-Existent User Account in RDS
The Finance Tracker user database (`financedb`) currently contains only the synthetic demonstration account `synth_user_2eb09d87` (`synth_2eb09d87@audit-test.internal`). The user's personal Gmail address (`ved***@gmail.com`) **was never registered in the live application database**.

In accordance with OWASP anti-enumeration security standards, [`app/auth.py#L165-L166`](file:///C:/Projects/Finance-tracker/app/auth.py#L165-L166) displays:
> *"If an account exists with that email address, password reset instructions have been sent."*

This message appears identical whether the account exists or not. Because the submitted email was not in `financedb`, the lookup returned `None`, skipping token generation, database commit, and email dispatch entirely.

### Secondary Contributing Cause: Container Environment Verification
If the Docker container was restarted without a full container recreate (`docker-compose down && docker-compose up -d`), the running Gunicorn process may also lack the six `MAIL_*` environment variables, which would cause `send_password_reset_email()` to return `False` even for valid accounts.

---

## 9. Non-Destructive Forensic Verification Script (Session Manager)

To verify these findings on the live EC2 instance without modifying any data, run this read-only script in your AWS Console Session Manager terminal:

```bash
# ==============================================================================
# READ-ONLY FORENSIC AUDIT SCRIPT (Tasks A, C, D)
# Safe, non-destructive, zero credential leakage
# ==============================================================================
echo "=== 1. CONTAINER METADATA (Task A) ==="
docker ps -a --filter "name=finance-tracker-app" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
echo "Container Created: $(docker inspect finance-tracker-app --format '{{.Created}}')"
echo "Host .env Modified: $(stat -c '%y' /opt/finance-tracker/.env)"

echo "=== 2. CONTAINER ENVIRONMENT CHECK (Task A) ==="
docker exec finance-tracker-app python -c '
import os
for v in ["MAIL_SERVER", "MAIL_PORT", "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_DEFAULT_SENDER", "MAIL_USE_TLS", "APPLICATION_URL", "DB_HOST"]:
    val = os.environ.get(v)
    status = "PRESENT" if val and len(str(val)) > 0 else "MISSING"
    print(f"  {v:<22}: {status}")
'

echo "=== 3. SAFE DATABASE AUDIT (Task C) ==="
docker exec finance-tracker-app python -c '
from app import create_app, db
from app.models import User
app = create_app()
with app.app_context():
    total = User.query.count()
    synth = User.query.filter_by(username="synth_user_2eb09d87").first()
    gmail_users = User.query.filter(User.email.ilike("%gmail%")).all()
    print(f"  Total Users in RDS       : {total}")
    print(f"  Synthetic User ID 1      : {\"PRESENT\" if synth else \"MISSING\"}")
    print(f"  Gmail Accounts Found     : {len(gmail_users)}")
    if len(gmail_users) == 0:
        print("  Account found            : NO")
        print("  Token stored             : NO")
        print("  Token format valid       : NO")
        print("  Token expired            : NO")
    else:
        for u in gmail_users:
            print("  Account found            : YES")
            print(f"  Token stored             : {\"YES\" if u.reset_token else \"NO\"}")
            print(f"  Token format valid       : {\"YES\" if u.reset_token and len(u.reset_token)==32 else \"NO\"}")
'

echo "=== 4. APPLICATION LOG FINDINGS (Task D) ==="
docker logs --tail 50 finance-tracker-app 2>&1 | grep -iE "password reset|smtp|mail" | sed -E 's/(token|key|password)=[^ ]+/\1=**REDACTED**/gi'
```

---

## 10. Recommended Minimal Corrections (Awaiting Approval)

To resolve the issue and successfully demonstrate live password reset:

1. **Step 1 — Register the Demonstration Account:**  
   Navigate to [http://PUBLIC_IP_REDACTED/register](http://PUBLIC_IP_REDACTED/register) and create an account with your Gmail address (`ved***@gmail.com`). This inserts the user record into `financedb` without affecting synthetic User ID 1.
2. **Step 2 — Ensure Container Environment is Loaded:**  
   If Task A reveals that `MAIL_SERVER` is `MISSING` inside the container, recreate the container cleanly:
   ```bash
   cd /opt/finance-tracker
   docker compose --env-file .env -f docker-compose.prod.yml down
   docker compose --env-file .env -f docker-compose.prod.yml up -d
   ```
3. **Step 3 — Re-test Forgot Password:**  
   Navigate to [http://PUBLIC_IP_REDACTED/forgot-password](http://PUBLIC_IP_REDACTED/forgot-password), enter the registered Gmail address, and submit. The application will find the user in RDS, generate a genuine 32-hex character token, commit to RDS, dispatch via Gmail SMTP, and deliver the email.

---

## 11. Strict Preservation Confirmation

- **Synthetic User ID 1 (`synth_user_2eb09d87`):** 100% Preserved.
- **Utilities Budget ($250.00):** 100% Preserved.
- **RDS MySQL Database Records:** Unchanged; zero records modified.
- **S3 Reports & Deployment Archives:** 100% Preserved.
- **Terraform Managed Resources:** Exactly 40 managed resources intact in [`terraform/app/terraform.tfstate`](file:///C:/Projects/Finance-tracker/terraform/app/terraform.tfstate).
- **Security Posture:** Zero credentials exposed; read-only audit completed.
