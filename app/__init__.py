from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os

# Load .env file if present (local development)
load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name='development'):
    # Get the project root directory (one level above app folder)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(project_root, 'templates')

    app = Flask(__name__, template_folder=template_dir)

    # ------------------------------------------------------------------ #
    # Secrets — never hard-coded.  Required values must be in the         #
    # environment (or in a .env file for local development).              #
    # ------------------------------------------------------------------ #
    secret_key = os.environ.get('SECRET_KEY', '')
    flask_env = os.environ.get('FLASK_ENV', 'development')

    if not secret_key:
        if flask_env == 'production':
            raise RuntimeError(
                "SECRET_KEY environment variable is not set. "
                "Set it before starting the application in production."
            )
        else:
            # Development fallback — loud warning so it is never missed
            import warnings
            secret_key = 'dev-only-insecure-key-do-not-use-in-production'
            warnings.warn(
                "SECRET_KEY is not set. Using an insecure development key. "
                "Set SECRET_KEY in your environment or .env file.",
                stacklevel=2,
            )

    app.config['SECRET_KEY'] = secret_key

    # ------------------------------------------------------------------ #
    # Database Configuration & Safe URL Resolution                       #
    # ------------------------------------------------------------------ #
    from sqlalchemy.engine import URL

    db_url = os.environ.get('DATABASE_URL', '').strip()
    db_host = os.environ.get('DB_HOST', '').strip()

    if db_url:
        # Full URL provided directly
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    elif db_host:
        # Construct safely via SQLAlchemy URL.create (handles special characters in passwords)
        app.config['SQLALCHEMY_DATABASE_URI'] = URL.create(
            drivername=os.environ.get('DB_DRIVER', 'mysql+pymysql'),
            username=os.environ.get('DB_USER') or os.environ.get('MYSQL_USER', 'financeuser'),
            password=os.environ.get('DB_PASSWORD') or os.environ.get('MYSQL_PASSWORD', ''),
            host=db_host,
            port=int(os.environ.get('DB_PORT', 3306)),
            database=os.environ.get('DB_NAME') or os.environ.get('MYSQL_DATABASE', 'financedb')
        )
    elif flask_env == 'production':
        # In production/container mode, require explicit database configuration
        raise RuntimeError(
            "Database configuration is required in production mode. "
            "Set DATABASE_URL or DB_HOST/DB_USER/DB_PASSWORD in your environment. "
            "Refusing to fall back to an ephemeral SQLite database."
        )
    else:
        # Local non-Docker development fallback
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'

    # Gemini API key — optional; AI insights fall back to rule-based if absent
    # NEVER hard-code this value here.
    app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '')

    # ------------------------------------------------------------------ #
    # Application base URL — used for security-sensitive absolute links   #
    # (e.g. password reset URLs) so that the Host header is never trusted #
    # to construct links that are emailed to users.                       #
    #                                                                     #
    # Local dev example :  APPLICATION_URL=http://127.0.0.1:5000         #
    # Production example:  APPLICATION_URL=https://financetracker.example.com
    # ------------------------------------------------------------------ #
    app.config['APPLICATION_URL'] = os.environ.get('APPLICATION_URL', '').rstrip('/')
    app.config['FLASK_ENV'] = flask_env

    # ------------------------------------------------------------------ #
    # Email / SMTP Configuration (for password reset delivery)           #
    # ------------------------------------------------------------------ #
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', '').strip()
    app.config['MAIL_PORT'] = os.environ.get('MAIL_PORT', '587').strip()
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '').strip()
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '').strip()
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', '').strip()
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', '1').strip()

    # Amazon S3 Monthly Reports configuration
    app.config['S3_REPORT_BUCKET'] = os.environ.get('S3_REPORT_BUCKET', '').strip()
    app.config['AWS_REGION'] = os.environ.get('AWS_REGION', os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')).strip()

    # Create uploads directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Register template filters and context processors
    from app.analytics import utility_processor
    app.context_processor(utility_processor)

    @app.template_filter('clamp')
    def clamp_filter(value, min_val, max_val):
        return max(min_val, min(value, max_val))

    # Register blueprints
    from app.routes import main_bp
    from app.auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    return app
