import os
import time
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)


def send_password_reset_email(to_email, reset_url):
    """
    Attempts to send password reset email if SMTP is configured.
    Never prints or logs passwords or tokens.
    Returns True if sent, False if SMTP is unconfigured or failed.
    """
    cfg = current_app.config if current_app else {}
    mail_server = (cfg.get('MAIL_SERVER') or os.environ.get('MAIL_SERVER', '')).strip()
    mail_port_str = str(cfg.get('MAIL_PORT') or os.environ.get('MAIL_PORT', '587')).strip()
    mail_username = (cfg.get('MAIL_USERNAME') or os.environ.get('MAIL_USERNAME', '')).strip()
    # App Password may contain spaces copied from Google account page - strip all spaces
    raw_password = cfg.get('MAIL_PASSWORD') or os.environ.get('MAIL_PASSWORD', '')
    mail_password = str(raw_password).replace(' ', '').strip()
    mail_sender = (cfg.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_DEFAULT_SENDER', '')).strip() or mail_username

    if not mail_server or not mail_port_str or not mail_username or not mail_password or not mail_sender or not to_email:
        return False

    try:
        mail_port = int(mail_port_str)
    except ValueError:
        return False

    raw_tls = str(cfg.get('MAIL_USE_TLS') or os.environ.get('MAIL_USE_TLS', '1')).strip().lower()
    mail_use_tls = raw_tls in ('1', 'true', 'yes')

    try:
        msg = EmailMessage()
        msg['Subject'] = 'Password Reset Request - Finance Tracker'
        msg['From'] = mail_sender
        msg['To'] = to_email
        msg.set_content(
            f"Hello,\n\n"
            f"A password reset request was received for your Finance Tracker account.\n"
            f"Click the link below to set a new password:\n\n"
            f"{reset_url}\n\n"
            f"This link is valid for 1 hour. If you made multiple requests, only the link in this latest email is valid.\n\n"
            f"If you did not make this request, you can safely ignore this email.\n"
        )

        with smtplib.SMTP(mail_server, mail_port, timeout=15) as server:
            if mail_use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
            server.login(mail_username, mail_password)
            server.send_message(msg)
        return True
    except Exception as e:
        # Log generic error server-side without leaking credentials or tokens
        print(f"WARNING: Password reset email delivery failed: {type(e).__name__}")
        return False


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return render_template('register.html')
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('main.dashboard'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username']  # Can be username or email
        password = request.form['password']
        
        # Search for user by username OR email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

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
            # Generate secure, unpredictable 32-hex character token
            token = secrets.token_hex(16)
            user.reset_token = token
            user.reset_token_expiry = int(time.time()) + 3600  # 1 hour expiry
            db.session.commit()

            # Construct reset URL from explicitly configured APPLICATION_URL when available.
            # This prevents a spoofed Host header from producing a malicious reset link.
            app_url = current_app.config.get('APPLICATION_URL', '').rstrip('/')
            if app_url:
                # Safe: uses only the explicitly operator-configured origin
                reset_path = url_for('auth.reset_password', token=token)
                reset_url = app_url + reset_path
            else:
                # Fallback for environments without APPLICATION_URL configured.
                # url_for uses the incoming Host header — acceptable only in fully
                # trusted local networks. Log a warning to encourage explicit config.
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                current_app.logger.warning(
                    "APPLICATION_URL is not configured. Reset URL origin is derived "
                    "from the request Host header, which may be spoofed. Set "
                    "APPLICATION_URL in your environment or .env file."
                )

            sent = send_password_reset_email(user.email, reset_url)
            # Safe server-side log: no email address, no token, no URL
            current_app.logger.info(
                "Password reset: user found, token generated, SMTP result=%s", sent
            )
            if not sent:
                dev_reset_url = reset_url
        else:
            # Safe server-side log: confirms lookup ran, no user data disclosed
            current_app.logger.info("Password reset: no matching account for submitted email")

        # Always return identical public message to avoid email enumeration
        flash('If an account exists with that email address, password reset instructions have been sent.', 'info')

        # In development mode only, if SMTP is not configured, display the reset link in the browser
        is_dev = current_app.debug or current_app.config.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_ENV') == 'development'
        has_smtp = bool((current_app.config.get('MAIL_SERVER') or os.environ.get('MAIL_SERVER', '')).strip())
        if is_dev and dev_reset_url and not has_smtp:
            flash(f"[Development Mode — SMTP Not Configured] Test reset link: {dev_reset_url}", 'info')

        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'], strict_slashes=False)
def reset_password(token):
    # Validate token exists and is within expiry window
    user = User.query.filter_by(reset_token=token).first()
    now = int(time.time())

    if not user or not user.reset_token_expiry or user.reset_token_expiry < now:
        flash('Invalid or expired password reset link.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('reset_password.html', token=token)
        
        # Update password and invalidate token immediately (single-use)
        user.password_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Password reset successfully. Please login with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
