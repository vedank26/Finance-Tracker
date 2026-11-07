#!/bin/sh
set -e

# -----------------------------------------------------------------------------
# Bounded Database Readiness & Initialization (max ~30 seconds)
# Retries failed connections up to 15 times with a 2-second backoff.
# Provides safe diagnostics without ever exposing passwords or credentials.
# -----------------------------------------------------------------------------
echo "Checking database readiness and initializing tables..."

python -c "
import sys
import time

max_attempts = 15
delay = 2
last_diag = 'unknown'

def classify_error(exc):
    exc_type = type(exc).__name__
    orig = getattr(exc, 'orig', None)
    err_code = None
    if orig and hasattr(orig, 'args') and len(orig.args) > 0 and isinstance(orig.args[0], int):
        err_code = orig.args[0]
    elif hasattr(exc, 'args') and len(exc.args) > 0 and isinstance(exc.args[0], int):
        err_code = exc.args[0]

    err_str = str(exc)
    if err_code == 2003 or 'Connection refused' in err_str or \"Can't connect to MySQL server\" in err_str:
        return 'connection refused / database server unreachable'
    elif err_code == 1045 or 'Access denied' in err_str:
        return 'authentication failed (invalid database credentials)'
    elif err_code == 1049 or 'Unknown database' in err_str:
        return 'database not found (catalog does not exist)'
    elif 'OperationalError' in exc_type:
        return f'database operational error (code {err_code})' if err_code else 'database operational error'
    else:
        return f'startup error ({exc_type})'

for attempt in range(1, max_attempts + 1):
    try:
        from app import create_app, db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            # Test live connection
            with db.engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            
            # Connection successful — ensure tables are created
            db.create_all()
            print('Database connection verified and tables initialized successfully.')
            sys.exit(0)
    except Exception as e:
        last_diag = classify_error(e)
        print(f'Database not ready yet (attempt {attempt}/{max_attempts}): {last_diag}. Retrying in {delay}s...')
        time.sleep(delay)

print(f'ERROR: Database connection timed out after {max_attempts * delay} seconds. Last status: {last_diag}.', file=sys.stderr)
sys.exit(1)
"

# Execute the main container command (Gunicorn)
exec "$@"
