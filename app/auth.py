from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)

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
        email = request.form['email']
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token (simple implementation using timestamp)
            import time
            import secrets
            reset_token = secrets.token_hex(16)
            
            # Store token and timestamp (in real app, you'd store this in database)
            # For demo purposes, we'll use a simple approach
            user.reset_token = reset_token
            user.reset_token_expiry = int(time.time()) + 3600  # 1 hour expiry
            db.session.commit()
            
            flash('Password reset instructions sent to your email')
            return redirect(url_for('auth.login'))
        else:
            flash('No account found with this email')
            return render_template('forgot_password.html')
    
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('reset_password.html', token=token)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long')
            return render_template('reset_password.html', token=token)
        
        # Find user by reset token
        user = User.query.filter_by(reset_token=token).first()
        
        if user and user.reset_token_expiry > int(time.time()):
            # Update password
            user.password_hash = generate_password_hash(password)
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()
            
            flash('Password reset successfully. Please login with your new password.')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid or expired reset token')
            return render_template('reset_password.html', token=token)
    
    return render_template('reset_password.html', token=token)

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
