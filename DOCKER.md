# Finance Tracker — Docker Deployment Guide

This guide covers building, running, and managing the Finance Tracker application using Docker and Docker Compose.

---

## 1. Prerequisites & Environment Configuration

Before running containers, create a `.env` file from the provided template:

```bash
# Copy template to .env
cp .env.example .env
```

Ensure the following variables are defined in your `.env` file:

```env
SECRET_KEY=generate_a_random_32_byte_hex_string
FLASK_ENV=development
FLASK_DEBUG=0
MYSQL_DATABASE=financedb
MYSQL_USER=financeuser
MYSQL_PASSWORD=your_secure_db_password
MYSQL_ROOT_PASSWORD=your_secure_root_password
```

> **Note:** `.env` is ignored by both `.gitignore` and `.dockerignore`. It will never be committed to Git or baked into Docker images.

---

## 2. Docker Compose (Application + MySQL)

Docker Compose starts the Flask application alongside a local MySQL 8.0 database with persistent storage and health monitoring.

### 2.1 Build and Start

```bash
# Build the images and start services in the background
docker compose up --build -d
```

### 2.2 Verify Status & Health Checks

```bash
# View running services and their health status
docker compose ps

# View live application logs
docker compose logs -f web

# View database logs
docker compose logs -f db
```

The `web` application container automatically waits until the `db` container is fully healthy before starting and initializing database tables.

### 2.3 Access the Application

Once running, access the dashboard at:
```
http://localhost:5000
```

### 2.4 Stop & Teardown

```bash
# Stop containers (preserves MySQL data in the named volume)
docker compose down

# Stop containers and remove volumes (destroys local database data)
docker compose down -v
```

---

## 3. Standalone Docker Image (Production / Cloud)

To build and run only the Flask application container (e.g., connecting to an external SQLite or cloud RDS MySQL database):

### 3.1 Build Image

```bash
docker build -t finance-tracker:latest .
```

### 3.2 Run Container with SQLite (Local testing)

```bash
docker run -d \
  --name finance-tracker-app \
  -p 5000:5000 \
  -e SECRET_KEY="your-production-secret-key" \
  -e FLASK_ENV="production" \
  finance-tracker:latest
```

### 3.3 Run Container with External / RDS MySQL

```bash
docker run -d \
  --name finance-tracker-app \
  -p 5000:5000 \
  -e SECRET_KEY="your-production-secret-key" \
  -e DATABASE_URL="mysql+pymysql://username:password@rds-host:3306/financedb" \
  -e FLASK_ENV="production" \
  finance-tracker:latest
```

### 3.4 Check Container Health

```bash
# Inspect container health status
docker inspect --format='{{json .State.Health}}' finance-tracker-app
```

### 3.5 Stop Container

```bash
docker stop finance-tracker-app
docker rm finance-tracker-app
```

---

## 4. Database Architecture & Schema Evolution

### 4.1 Prototype Initialization with `db.create_all()`
During container startup, `entrypoint.sh` executes `db.create_all()`.
- **Appropriateness for Prototype:** Creates all required tables (`user`, `transaction`, `net_worth`, `investment`, `budget`) automatically on a fresh database. It is idempotent and safe against overwriting existing data.
- **Limitations:** `db.create_all()` does **not** perform schema migrations. If models are changed later (e.g., adding, modifying, or dropping columns, or altering constraints), `db.create_all()` silently ignores changes on pre-existing tables.
- **Production Migration Plan:** For future iterative schema changes with live data, a formal migration tool (such as **Flask-Migrate / Alembic**) should be integrated to manage versioned migration scripts (`upgrade()` / `downgrade()`).

### 4.2 Safe Database URL Construction
The application supports both discrete connection parameters and full database URLs:
- **Discrete Parameters (Preferred in Docker Compose):** `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_DRIVER`. The application uses SQLAlchemy's `URL.create()`, which automatically percent-encodes passwords with reserved characters (`@`, `:`, `/`, `?`, `#`, `%`).
- **Unified Parameter (Cloud / RDS):** `DATABASE_URL` (e.g., `mysql+pymysql://user:password@rds-host:3306/financedb`). If passwords contain reserved URL characters, they must be percent-encoded.
- **Production Safety:** In `production` mode (`FLASK_ENV=production`), the application strictly requires database configuration and refuses to silently fall back to an ephemeral SQLite database. In `development` mode, it seamlessly defaults to local SQLite (`instance/finance.db`).

