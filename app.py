from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from sqlalchemy import func
import requests
import yfinance as yf
from threading import Thread
import time


app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    monthly_goal = db.Column(db.Float, default=0)
    
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    net_worth_entries = db.relationship('NetWorth', backref='user', lazy=True)
    investments = db.relationship('Investment', backref='user', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Utility Functions
def categorize_transaction(description, amount):
    desc = description.lower()
    
    # Income patterns - if amount is positive OR description indicates income
    if any(word in desc for word in ['salary', 'payroll', 'wages', 'deposit', 'refund', 'income']) or amount > 0:
        return 'Income', 'income'
    
    # Expense categories - if amount is negative OR description indicates expense
    expense_categories = {
        'Food & Dining': ['grocery', 'food', 'restaurant', 'dining', 'supermarket', 'coffee'],
        'Transportation': ['gas', 'fuel', 'uber', 'lyft', 'transport', 'taxi', 'bus'],
        'Housing': ['rent', 'mortgage', 'utilities', 'electric', 'water', 'internet', 'bill'],
        'Healthcare': ['medical', 'doctor', 'pharmacy', 'hospital', 'health', 'dental'],
        'Shopping': ['shopping', 'amazon', 'target', 'walmart', 'store', 'purchase'],
        'Entertainment': ['movie', 'netflix', 'spotify', 'entertainment', 'subscription', 'game']
    }
    
    for category, keywords in expense_categories.items():
        if any(keyword in desc for keyword in keywords):
            return category, 'expense'
    
    # Default based on amount
    if amount < 0:
        return 'Other Expense', 'expense'
    else:
        return 'Other Income', 'income'

def calculate_financial_metrics(user_id):
    try:
        transactions = Transaction.query.filter_by(user_id=user_id).all()
        net_worth_data = NetWorth.query.filter_by(user_id=user_id).order_by(NetWorth.date).all()
        investments = Investment.query.filter_by(user_id=user_id).all()
        
        # Debug: Print transaction details
        print(f"DEBUG - Total transactions: {len(transactions)}")
        
        # Transaction metrics - use actual amounts (positive/negative)
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        net_cash_flow = total_income + total_expenses  # Expenses are negative, so we add
        
        # Ensure savings rate calculation is safe
        savings_rate = 0
        if total_income > 0:
            savings_rate = (net_cash_flow / total_income) * 100
        
        # Category spending (only expenses)
        category_spending = {}
        for t in transactions:
            if t.type == 'expense':
                category_spending[t.category] = category_spending.get(t.category, 0) + abs(t.amount)
        
        top_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Net worth metrics
        current_net_worth = net_worth_data[-1].net_worth if net_worth_data else 0
        
        # Investment metrics
        portfolio_value = sum(inv.total_value for inv in investments)
        total_gain_loss = sum(inv.gain_loss for inv in investments)
        
        # Debug output
        print(f"DEBUG - Income: {total_income}, Expenses: {total_expenses}, Net Flow: {net_cash_flow}")
        
        # Return ALL required metrics for the template
        metrics = {
            'net_cash_flow': net_cash_flow,
            'savings_rate': round(savings_rate, 1),
            'current_net_worth': current_net_worth,
            'portfolio_value': portfolio_value,
            'total_gain_loss': total_gain_loss,
            'top_categories': top_categories,
            'total_expenses': total_expenses,
            'total_income': total_income,
            'transaction_count': len(transactions),
            'investment_count': len(investments)
        }
        
        print("DEBUG - Final metrics:", metrics)
        return metrics
        
    except Exception as e:
        print(f"ERROR in calculate_financial_metrics: {e}")
        import traceback
        traceback.print_exc()
        
        # Return default metrics with ALL required fields
        return {
            'net_cash_flow': 0,
            'savings_rate': 0,
            'current_net_worth': 0,
            'portfolio_value': 0,
            'total_gain_loss': 0,
            'top_categories': [],
            'total_expenses': 0,
            'total_income': 0,
            'transaction_count': 0,
            'investment_count': 0
        }

# HEALTH SCORE FUNCTIONS
def calculate_health_score(metrics):
    """Calculate financial health score (0-100)"""
    score = 0
    
    # Savings rate (max 30 points)
    if metrics['savings_rate'] >= 20:
        score += 30
    elif metrics['savings_rate'] >= 15:
        score += 25
    elif metrics['savings_rate'] >= 10:
        score += 20
    elif metrics['savings_rate'] >= 5:
        score += 15
    elif metrics['savings_rate'] > 0:
        score += 10
    
    # Cash flow (max 25 points)
    if metrics['net_cash_flow'] > 0:
        score += 25
    elif metrics['net_cash_flow'] >= -1000:
        score += 15
    else:
        score += 5
    
    # Net worth growth (max 25 points) - simplified for now
    if metrics['current_net_worth'] > 0:
        score += 20
    
    # Portfolio performance (max 20 points)
    if metrics['total_gain_loss'] > 0:
        score += 15
    
    return min(score, 100)

def get_health_info(score):
    """Get health score information"""
    if score >= 80:
        return {
            'message': 'Excellent Financial Health!',
            'description': 'You\'re doing great! Keep up the good financial habits.',
            'color': '#10B981',
            'text_color': 'text-green-600'
        }
    elif score >= 60:
        return {
            'message': 'Good Financial Health',
            'description': 'You\'re on the right track. Some areas could use improvement.',
            'color': '#F59E0B',
            'text_color': 'text-yellow-600'
        }
    elif score >= 40:
        return {
            'message': 'Fair Financial Health',
            'description': 'There are several areas that need attention.',
            'color': '#F97316',
            'text_color': 'text-orange-600'
        }
    else:
        return {
            'message': 'Needs Improvement',
            'description': 'Focus on building better financial habits.',
            'color': '#EF4444',
            'text_color': 'text-red-600'
        }

# PRICE FETCHING FUNCTIONS
def fetch_current_prices(symbols):
    """
    Fetch current market prices for given stock symbols
    Returns: Dictionary of {symbol: current_price}
    """
    current_prices = {}
    
    for symbol in symbols:
        try:
            # For Indian stocks, add .NS suffix for NSE
            if not any(ext in symbol.upper() for ext in ['.NS', '.BO', '.BA']):
                symbol_with_suffix = f"{symbol}.NS"  # Default to NSE
            else:
                symbol_with_suffix = symbol
            
            # Using yfinance to get current price
            stock = yf.Ticker(symbol_with_suffix)
            info = stock.info
            
            # Try different price fields
            current_price = (info.get('currentPrice') or 
                           info.get('regularMarketPrice') or 
                           info.get('previousClose'))
            
            if current_price:
                current_prices[symbol] = current_price
                print(f"Fetched {symbol}: ₹{current_price}")
            else:
                print(f"Could not fetch price for {symbol}")
                
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            # Fallback to previous price
            current_prices[symbol] = None
    
    return current_prices

def update_portfolio_prices(user_id):
    """
    Update all investment prices for a user with current market data
    """
    try:
        investments = Investment.query.filter_by(user_id=user_id).all()
        
        if not investments:
            print("No investments found to update")
            return 0
        
        symbols = list(set([inv.symbol for inv in investments]))
        print(f"Fetching prices for symbols: {symbols}")
        
        current_prices = fetch_current_prices(symbols)
        
        updated_count = 0
        for investment in investments:
            if investment.symbol in current_prices and current_prices[investment.symbol]:
                new_price = current_prices[investment.symbol]
                
                # Update investment details
                investment.current_price = new_price
                investment.total_value = investment.shares * new_price
                investment.gain_loss = investment.total_value - (investment.shares * investment.cost_basis)
                
                if investment.shares * investment.cost_basis > 0:
                    investment.gain_loss_percent = (investment.gain_loss / 
                                                  (investment.shares * investment.cost_basis)) * 100
                else:
                    investment.gain_loss_percent = 0
                
                updated_count += 1
        
        db.session.commit()
        print(f"Successfully updated {updated_count} investments")
        return updated_count
        
    except Exception as e:
        print(f"Error updating portfolio prices: {e}")
        db.session.rollback()
        return 0

# Add template filters
@app.template_filter('clamp')
def clamp_filter(value, min_val, max_val):
    return max(min_val, min(value, max_val))

# Register template context processors
@app.context_processor
def utility_processor():
    def get_last_price_update():
        return "Click 'Update Prices' to get live data"
    
    return {
        'calculate_health_score': calculate_health_score,
        'get_health_info': get_health_info,
        'get_last_price_update': get_last_price_update
    }

# Chart Functions
def create_cash_flow_chart(transactions):
    if not transactions:
        return [
            {
                'x': ['Jan', 'Feb', 'Mar'],
                'y': [50000, 50000, 50000],
                'type': 'bar',
                'name': 'Income',
                'marker': {'color': 'green'}
            },
            {
                'x': ['Jan', 'Feb', 'Mar'],
                'y': [8000, 4000, 10000],
                'type': 'bar',
                'name': 'Expenses',
                'marker': {'color': 'red'}
            }
        ]
    
    try:
        df_data = []
        for t in transactions:
            df_data.append({
                'date': t.date,
                'amount': t.amount,
                'type': t.type,
                'category': t.category
            })
        
        df = pd.DataFrame(df_data)
        
        # Convert to datetime and extract month
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M').astype(str)
        
        # Group by month and type, sum amounts
        monthly_data = df.groupby(['month', 'type'])['amount'].sum().unstack(fill_value=0)
        
        # Reset index to make month a column
        monthly_data = monthly_data.reset_index()
        
        # Ensure required columns exist
        required_columns = ['income', 'expense']
        for col in required_columns:
            if col not in monthly_data.columns:
                monthly_data[col] = 0
        
        # Calculate net flow
        monthly_data['net_flow'] = monthly_data['income'] + monthly_data['expense']
        
        # Sort by month
        monthly_data = monthly_data.sort_values('month')
        
        # Create chart data
        chart_data = [
            {
                'x': monthly_data['month'].tolist(),
                'y': monthly_data['income'].tolist(),
                'type': 'bar',
                'name': 'Income',
                'marker': {'color': 'green'}
            },
            {
                'x': monthly_data['month'].tolist(),
                'y': abs(monthly_data['expense']).tolist(),
                'type': 'bar',
                'name': 'Expenses',
                'marker': {'color': 'red'}
            },
            {
                'x': monthly_data['month'].tolist(),
                'y': monthly_data['net_flow'].tolist(),
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': 'Net Flow',
                'line': {'color': 'blue', 'width': 3}
            }
        ]
        
        return chart_data
        
    except Exception as e:
        print(f"Error creating cash flow chart: {e}")
        return None

def create_net_worth_chart(net_worth_data):
    if not net_worth_data:
        return [
            {
                'x': ['Jan', 'Feb', 'Mar'],
                'y': [400000, 430000, 470000],
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': 'Net Worth',
                'line': {'color': 'blue', 'width': 3}
            }
        ]
    
    try:
        dates = [nw.date.strftime('%Y-%m-%d') for nw in net_worth_data]
        net_worth = [nw.net_worth for nw in net_worth_data]
        
        chart_data = [
            {
                'x': dates,
                'y': net_worth,
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': 'Net Worth',
                'line': {'color': 'blue', 'width': 3}
            }
        ]
        
        return chart_data
    
    except Exception as e:
        print(f"Error creating net worth chart: {e}")
        return None

def create_portfolio_chart(investments):
    if not investments:
        return [
            {
                'labels': ['AAPL', 'GOOGL', 'TSLA'],
                'values': [1500, 14000, 4000],
                'type': 'pie',
                'name': 'Portfolio Allocation'
            }
        ]
    
    try:
        symbols = [inv.symbol for inv in investments]
        values = [inv.total_value for inv in investments]
        
        chart_data = [
            {
                'labels': symbols,
                'values': values,
                'type': 'pie',
                'name': 'Portfolio Allocation'
            }
        ]
        
        return chart_data
    
    except Exception as e:
        print(f"Error creating portfolio chart: {e}")
        return None

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
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
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        metrics = calculate_financial_metrics(current_user.id)
        transactions = Transaction.query.filter_by(user_id=current_user.id).all()
        net_worth_data = NetWorth.query.filter_by(user_id=current_user.id).order_by(NetWorth.date).all()
        investments = Investment.query.filter_by(user_id=current_user.id).all()
        
        cash_flow_chart = create_cash_flow_chart(transactions)
        net_worth_chart = create_net_worth_chart(net_worth_data)
        portfolio_chart = create_portfolio_chart(investments)
        
        recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
                                .order_by(Transaction.date.desc())\
                                .limit(5)\
                                .all()
        
        return render_template('dashboard.html',
                             metrics=metrics,
                             cash_flow_chart=cash_flow_chart,
                             net_worth_chart=net_worth_chart,
                             portfolio_chart=portfolio_chart,
                             recent_transactions=recent_transactions)
                             
    except Exception as e:
        print(f"ERROR in dashboard route: {e}")
        default_metrics = calculate_financial_metrics(current_user.id)
        
        return render_template('dashboard.html', 
                             metrics=default_metrics,
                             cash_flow_chart=None,
                             net_worth_chart=None, 
                             portfolio_chart=None,
                             recent_transactions=[])

@app.route('/generate-sample-data')
@login_required
def generate_sample_data():
    """Generate sample data for testing"""
    try:
        Transaction.query.filter_by(user_id=current_user.id).delete()
        NetWorth.query.filter_by(user_id=current_user.id).delete()
        Investment.query.filter_by(user_id=current_user.id).delete()
        
        sample_transactions = [
            {'date': '2024-01-15', 'description': 'Salary', 'amount': 50000, 'type': 'income', 'category': 'Income'},
            {'date': '2024-02-15', 'description': 'Salary', 'amount': 50000, 'type': 'income', 'category': 'Income'},
            {'date': '2024-03-15', 'description': 'Salary', 'amount': 50000, 'type': 'income', 'category': 'Income'},
            {'date': '2024-01-05', 'description': 'Grocery Shopping', 'amount': -5000, 'type': 'expense', 'category': 'Food & Dining'},
            {'date': '2024-01-10', 'description': 'Electricity Bill', 'amount': -3000, 'type': 'expense', 'category': 'Housing'},
            {'date': '2024-02-03', 'description': 'Restaurant', 'amount': -2500, 'type': 'expense', 'category': 'Food & Dining'},
            {'date': '2024-02-12', 'description': 'Internet Bill', 'amount': -1500, 'type': 'expense', 'category': 'Housing'},
            {'date': '2024-03-08', 'description': 'Shopping', 'amount': -8000, 'type': 'expense', 'category': 'Shopping'},
            {'date': '2024-03-20', 'description': 'Gas Station', 'amount': -2000, 'type': 'expense', 'category': 'Transportation'},
        ]
        
        for data in sample_transactions:
            transaction = Transaction(
                user_id=current_user.id,
                date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
                description=data['description'],
                amount=data['amount'],
                category=data['category'],
                type=data['type']
            )
            db.session.add(transaction)
        
        sample_net_worth = [
            {'date': '2024-01-31', 'assets': 600000, 'liabilities': 200000, 'net_worth': 400000},
            {'date': '2024-02-29', 'assets': 620000, 'liabilities': 190000, 'net_worth': 430000},
            {'date': '2024-03-31', 'assets': 650000, 'liabilities': 180000, 'net_worth': 470000},
        ]
        
        for data in sample_net_worth:
            net_worth = NetWorth(
                user_id=current_user.id,
                date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
                assets=data['assets'],
                liabilities=data['liabilities'],
                net_worth=data['net_worth']
            )
            db.session.add(net_worth)
        
        sample_investments = [
            {'symbol': 'RELIANCE.NS', 'name': 'Reliance Industries', 'shares': 10, 'current_price': 2500},
            {'symbol': 'TCS.NS', 'name': 'Tata Consultancy', 'shares': 5, 'current_price': 3800},
            {'symbol': 'INFY.NS', 'name': 'Infosys Ltd', 'shares': 15, 'current_price': 1700},
        ]
        
        for data in sample_investments:
            total_value = data['shares'] * data['current_price']
            investment = Investment(
                user_id=current_user.id,
                symbol=data['symbol'],
                name=data['name'],
                shares=data['shares'],
                current_price=data['current_price'],
                cost_basis=data['current_price'] * 0.9,
                total_value=total_value,
                gain_loss=total_value * 0.1,
                gain_loss_percent=10.0
            )
            db.session.add(investment)
        
        db.session.commit()
        flash('Sample data generated successfully!')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error generating sample data: {str(e)}')
    
    return redirect(url_for('dashboard'))

@app.route('/update-prices')
@login_required
def update_prices_route():
    """Manual trigger to update portfolio prices"""
    updated_count = update_portfolio_prices(current_user.id)
    
    if updated_count > 0:
        flash(f'Successfully updated {updated_count} investment prices with current market data!')
    else:
        flash('No investments updated. Please check your portfolio data.')
    
    return redirect(url_for('dashboard'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    data_type = request.form.get('data_type')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        df = pd.read_csv(file)
        
        if data_type == 'transactions':
            process_transactions_csv(df, current_user.id)
            message = f'Successfully processed {len(df)} transactions'
        elif data_type == 'net_worth':
            process_net_worth_csv(df, current_user.id)
            message = f'Successfully processed {len(df)} net worth entries'
        elif data_type == 'portfolio':
            process_portfolio_csv(df, current_user.id)
            message = f'Successfully processed {len(df)} investment positions'
        else:
            return jsonify({'error': 'Invalid data type'}), 400
        
        return jsonify({'success': message})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_transactions_csv(df, user_id):
    for _, row in df.iterrows():
        date_str = row.get('date') or row.get('Date')
        description = row.get('description') or row.get('Description')
        amount = float(row.get('amount') or row.get('Amount') or 0)
        
        category = row.get('category') or row.get('Category')
        trans_type = row.get('type') or row.get('Type')
        
        if not category or not trans_type:
            category, trans_type = categorize_transaction(description, amount)
        
        transaction = Transaction(
            user_id=user_id,
            date=datetime.strptime(date_str, '%Y-%m-%d').date(),
            description=description,
            amount=amount,
            category=category,
            type=trans_type
        )
        db.session.add(transaction)
    
    db.session.commit()
    
def process_net_worth_csv(df, user_id):
    for _, row in df.iterrows():
        date_str = row.get('date') or row.get('Date')
        assets = float(row.get('assets') or row.get('Assets') or 0)
        liabilities = float(row.get('liabilities') or row.get('Liabilities') or 0)
        net_worth = float(row.get('netWorth') or row.get('net_worth') or row.get('Net Worth') or 0)
        
        if net_worth and not assets and not liabilities:
            assets = net_worth if net_worth > 0 else 0
            liabilities = abs(net_worth) if net_worth < 0 else 0
        elif assets and liabilities:
            net_worth = assets - liabilities
        
        net_worth_entry = NetWorth(
            user_id=user_id,
            date=datetime.strptime(date_str, '%Y-%m-%d').date(),
            assets=assets,
            liabilities=liabilities,
            net_worth=net_worth
        )
        db.session.add(net_worth_entry)
    
    db.session.commit()

def process_portfolio_csv(df, user_id):
    for _, row in df.iterrows():
        symbol = row.get('symbol') or row.get('Symbol')
        name = row.get('name') or row.get('Name') or symbol
        shares = float(row.get('shares') or row.get('Shares') or 0)
        current_price = float(row.get('currentPrice') or row.get('Current Price') or 0)
        cost_basis = float(row.get('costBasis') or row.get('Cost Basis') or current_price)
        
        total_value = shares * current_price
        gain_loss = total_value - (shares * cost_basis)
        gain_loss_percent = (gain_loss / (shares * cost_basis)) * 100 if (shares * cost_basis) != 0 else 0
        
        investment = Investment(
            user_id=user_id,
            symbol=symbol,
            name=name,
            shares=shares,
            current_price=current_price,
            cost_basis=cost_basis,
            total_value=total_value,
            gain_loss=gain_loss,
            gain_loss_percent=gain_loss_percent
        )
        db.session.add(investment)
    
    db.session.commit()

@app.route('/transactions')
@login_required
def transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
    metrics = calculate_financial_metrics(current_user.id)
    categories = list(set(t.category for t in transactions))
    
    transactions_data = []
    for t in transactions:
        transactions_data.append({
            'id': t.id,
            'date': t.date.strftime('%Y-%m-%d'),
            'description': t.description,
            'amount': t.amount,
            'category': t.category,
            'type': t.type
        })
    
    return render_template('transactions.html', 
                         transactions=transactions_data,
                         categories=categories,
                         metrics=metrics)
    
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        monthly_goal = float(request.form.get('monthly_goal', 0))
        current_user.monthly_goal = monthly_goal
        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('profile'))
    
    metrics = calculate_financial_metrics(current_user.id)
    return render_template('profile.html', metrics=metrics)

@app.route('/api/financial-data')
@login_required
def api_financial_data():
    metrics = calculate_financial_metrics(current_user.id)
    return jsonify(metrics)

@app.route('/debug-data')
@login_required
def debug_data():
    """Debug route to check what data is stored"""
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    net_worth = NetWorth.query.filter_by(user_id=current_user.id).all()
    investments = Investment.query.filter_by(user_id=current_user.id).all()
    
    debug_info = {
        'transaction_count': len(transactions),
        'transactions': [{
            'id': t.id,
            'date': str(t.date),
            'description': t.description,
            'amount': t.amount,
            'type': t.type,
            'category': t.category
        } for t in transactions[:10]],
        'net_worth_count': len(net_worth),
        'investment_count': len(investments),
    }
    
    return jsonify(debug_info)

# MAIN APPLICATION RUNNER
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)