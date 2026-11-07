#!/usr/bin/env bash
set -euo pipefail

exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1
echo "=== Finance Tracker EC2 Bootstrap Starting ==="

# 0. Configure Idempotent 2 GB Swap File for Memory Burst Headroom on t3.micro
echo "--- Configuring Swap Space ---"
if [ ! -f /swapfile ]; then
  echo "Creating 2 GB swapfile at /swapfile..."
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
else
  echo "Swapfile /swapfile already exists."
fi

# Enforce secure permissions (600) regardless of whether swapfile previously existed
chmod 600 /swapfile

# Activate swap if not currently active
if ! swapon --show | grep -q '/swapfile'; then
  echo "Activating /swapfile..."
  swapon /swapfile
fi

# Ensure /etc/fstab contains swapfile entry for persistence across reboots (prevent duplicate entries)
if ! grep -E -q '^\s*/swapfile\s+' /etc/fstab; then
  echo "Adding /swapfile to /etc/fstab..."
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Verify active swap
echo "Active swap devices and memory summary:"
swapon --show
free -h

# 1. Update OS packages and install Docker, Git, and AWS SDK for Python
dnf update -y
dnf install -y docker git python3-boto3
usermod -aG docker ec2-user

# 2. Configure Docker daemon default logging driver to ship container logs to CloudWatch
# Uses existing IAM permissions (cloudwatch_logs policy) and 7-day log retention
mkdir -p /etc/docker
cat << DOCKER_JSON_EOF > /etc/docker/daemon.json
{
  "log-driver": "awslogs",
  "log-opts": {
    "awslogs-region": "${aws_region}",
    "awslogs-group": "/${project_name}/app",
    "awslogs-stream": "finance-tracker-app",
    "awslogs-create-group": "false"
  }
}
DOCKER_JSON_EOF

systemctl enable --now docker

# 3. Install Docker Compose plugin
DOCKER_CONFIG=/usr/local/lib/docker
mkdir -p "$DOCKER_CONFIG/cli-plugins"
curl -sSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o "$DOCKER_CONFIG/cli-plugins/docker-compose"
chmod +x "$DOCKER_CONFIG/cli-plugins/docker-compose"

# 4. Prepare Application Directory (Restricted permissions)
APP_DIR="/opt/finance-tracker"
mkdir -p "$APP_DIR"
chmod 700 "$APP_DIR"

# 5. Create Reusable Parameter Store Refresh Script
# Authenticates securely via EC2 Instance Profile (IMDSv2); ZERO static AWS keys required
cat << 'REFRESH_EOF' > "$APP_DIR/refresh-env.sh"
#!/usr/bin/env bash
set -euo pipefail

echo "Fetching configuration from Systems Manager Parameter Store..."
python3 - << 'PYEOF'
import boto3

ssm = boto3.client('ssm', region_name='${aws_region}')
paginator = ssm.get_paginator('get_parameters_by_path')
params = {}

for page in paginator.paginate(Path='/${project_name}/', WithDecryption=True):
    for p in page.get('Parameters', []):
        key = p['Name'].replace('/${project_name}/', '').strip()
        params[key] = p['Value']

def serialize_env_val(key, val):
    """
    Serializes an environment variable value for Docker Compose compatibility.
    Uses double quotes with Compose-compliant escaping:
    1. Backslashes are escaped: \\ -> \\\\
    2. Double quotes are escaped: " -> \\"
    3. Dollar signs are escaped for Compose variable interpolation: $ -> $$
    Rejects carriage returns or newlines to prevent silent credential alteration and variable injection.
    """
    if val is None:
        return '""'
    s = str(val)
    if '\r' in s or '\n' in s:
        raise ValueError(f"Value for parameter '{key}' contains carriage return or newline characters")
    escaped = s.replace('\\', '\\\\').replace('"', '\\"').replace('$', '$$')
    return f'"{escaped}"'

# Database URL is intentionally empty so Flask's app/__init__.py falls through
# to discrete DB parameters and invokes SQLAlchemy URL.create() with auto percent-encoding.
# AWS_REGION ensures boto3 S3 client connects directly to ap-south-1.
# HOST_PORT=80 maps EC2 public HTTP port 80 to Gunicorn container port 5000.
# APPLICATION_URL provides canonical base URL for password reset links (populated in Stage 5).
env_lines = [
    f"SECRET_KEY={serialize_env_val('SECRET_KEY', params.get('SECRET_KEY', ''))}",
    'DATABASE_URL=""',
    f"DB_HOST={serialize_env_val('DB_HOST', params.get('DB_HOST', ''))}",
    f"DB_PORT={serialize_env_val('DB_PORT', params.get('DB_PORT', '3306'))}",
    f"DB_USER={serialize_env_val('DB_USER', params.get('DB_USER', 'financeuser'))}",
    f"DB_PASSWORD={serialize_env_val('DB_PASSWORD', params.get('DB_PASSWORD', ''))}",
    f"DB_NAME={serialize_env_val('DB_NAME', params.get('DB_NAME', 'financedb'))}",
    f"S3_REPORT_BUCKET={serialize_env_val('S3_REPORT_BUCKET', params.get('S3_REPORT_BUCKET', ''))}",
    f"GEMINI_API_KEY={serialize_env_val('GEMINI_API_KEY', params.get('GEMINI_API_KEY', ''))}",
    f"AWS_REGION={serialize_env_val('AWS_REGION', params.get('AWS_REGION', '${aws_region}'))}",
    f"AWS_DEFAULT_REGION={serialize_env_val('AWS_DEFAULT_REGION', params.get('AWS_DEFAULT_REGION', '${aws_region}'))}",
    'HOST_PORT="80"',
    'FLASK_ENV="production"',
    'FLASK_DEBUG="0"',
    f"APPLICATION_URL={serialize_env_val('APPLICATION_URL', params.get('APPLICATION_URL', ''))}",
    f"MAIL_SERVER={serialize_env_val('MAIL_SERVER', params.get('MAIL_SERVER', ''))}",
    f"MAIL_PORT={serialize_env_val('MAIL_PORT', params.get('MAIL_PORT', '587'))}",
    f"MAIL_USERNAME={serialize_env_val('MAIL_USERNAME', params.get('MAIL_USERNAME', ''))}",
    f"MAIL_PASSWORD={serialize_env_val('MAIL_PASSWORD', params.get('MAIL_PASSWORD', ''))}",
    f"MAIL_DEFAULT_SENDER={serialize_env_val('MAIL_DEFAULT_SENDER', params.get('MAIL_DEFAULT_SENDER', ''))}",
    f"MAIL_USE_TLS={serialize_env_val('MAIL_USE_TLS', params.get('MAIL_USE_TLS', '1'))}"
]

with open('/opt/finance-tracker/.env', 'w') as f:
    f.write('\n'.join(env_lines) + '\n')
print("Configuration successfully written to /opt/finance-tracker/.env")
PYEOF

chmod 600 "/opt/finance-tracker/.env"
REFRESH_EOF

chmod 700 "$APP_DIR/refresh-env.sh"

# Execute initial configuration pull
bash "$APP_DIR/refresh-env.sh"
chown -R ec2-user:ec2-user "$APP_DIR"

# 6. Application Source Retrieval (Optional Git Clone without hardcoded secrets)
REPO_URL="${app_repo_url}"
if [ -n "$REPO_URL" ]; then
  echo "Cloning application source from $REPO_URL..."
  TEMP_CLONE=$(mktemp -d)
  git clone "$REPO_URL" "$TEMP_CLONE"
  cp -rn "$TEMP_CLONE"/* "$APP_DIR/" || true
  cp -rn "$TEMP_CLONE"/.[!.]* "$APP_DIR/" || true
  rm -rf "$TEMP_CLONE"
  chown -R ec2-user:ec2-user "$APP_DIR"
else
  echo "NOTE: No app_repo_url specified. Runtime environment and .env are ready."
  echo "Deploy application files to $APP_DIR via AWS Systems Manager Session Manager or CI/CD."
fi

# 7. Configure Systemd Service for Container Lifecycle Management
# Decoupled via ConditionPathExists: skips cleanly without failing if docker-compose.prod.yml is not yet transferred
cat << 'SERVICE_EOF' > /etc/systemd/system/finance-tracker.service
[Unit]
Description=Finance Tracker Docker Compose Application
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target
ConditionPathExists=/opt/finance-tracker/docker-compose.prod.yml

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/finance-tracker
ExecStart=/usr/local/lib/docker/cli-plugins/docker-compose --env-file /opt/finance-tracker/.env -f /opt/finance-tracker/docker-compose.prod.yml up -d --remove-orphans
ExecStop=/usr/local/lib/docker/cli-plugins/docker-compose --env-file /opt/finance-tracker/.env -f /opt/finance-tracker/docker-compose.prod.yml down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable finance-tracker.service

# Attempt startup only if docker-compose.prod.yml is already present
if [ -f "$APP_DIR/docker-compose.prod.yml" ]; then
  echo "docker-compose.prod.yml found; starting application service..."
  systemctl start finance-tracker.service || true
fi

echo "=== Finance Tracker EC2 Bootstrap Completed ==="
