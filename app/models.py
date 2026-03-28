from flask_login import UserMixin
from datetime import datetime
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    monthly_goal = db.Column(db.Float, default=0)
    reset_token = db.Column(db.String(32), nullable=True)
    reset_token_expiry = db.Column(db.Integer, nullable=True)
    
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    net_worth_entries = db.relationship('NetWorth', backref='user', lazy=True)
    investments = db.relationship('Investment', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    
    # ADD THIS NEW FIELD:
    fingerprint = db.Column(
        db.String(32), 
        nullable=True,
        index=True
    )
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NetWorth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    assets = db.Column(db.Float, nullable=False)
    liabilities = db.Column(db.Float, nullable=False)
    net_worth = db.Column(db.Float, nullable=False)

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    shares = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    cost_basis = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    gain_loss = db.Column(db.Float, nullable=False)
    gain_loss_percent = db.Column(db.Float, nullable=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    monthly_limit = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'category'),)
