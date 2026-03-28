from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date
from app.models import Transaction, NetWorth, Investment, Budget
from app.analytics import calculate_financial_metrics, create_cash_flow_chart, create_net_worth_chart, create_portfolio_chart, generate_ai_insights
from app.services import process_transactions_csv, process_net_worth_csv, process_portfolio_csv, update_portfolio_prices
import pandas as pd

def normalize_category(category):
    """Normalize category names for consistent matching"""
    if not category:
        return "other"
    
    category = str(category).strip().lower()
    
    # Food categories
    if category in ["food", "food & dining", "groceries", "restaurant", "dining", "supermarket", "coffee", "food expense"]:
        return "food"
    
    # Transport categories
    elif category in ["transport", "travel", "uber", "ola", "taxi", "bus", "fuel", "gas", "transportation", "auto"]:
        return "transport"
    
    # Shopping categories
    elif category in ["shopping", "clothes", "amazon", "flipkart", "purchase", "store", "retail", "shopping expense"]:
        return "shopping"
    
    # Entertainment categories
    elif category in ["entertainment", "movies", "netflix", "subscription", "game", "streaming", "entertainment expense"]:
        return "entertainment"
    
    # Housing categories
    elif category in ["housing", "rent", "mortgage", "utilities", "electric", "water", "internet", "bill"]:
        return "housing"
    
    # Healthcare categories
    elif category in ["healthcare", "medical", "doctor", "pharmacy", "hospital", "health", "dental"]:
        return "healthcare"
    
    return category

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        print(f"DEBUG: Dashboard accessed by User {current_user.id} ({current_user.username})")
        
        # Check if user has any financial data
        transactions = Transaction.query.filter_by(user_id=current_user.id).all()
        net_worth_data = NetWorth.query.filter_by(user_id=current_user.id).order_by(NetWorth.date).all()
        investments = Investment.query.filter_by(user_id=current_user.id).all()
        
        has_financial_data = bool(transactions or net_worth_data or investments)
        
        print(f"DEBUG: User {current_user.id} has {len(transactions)} transactions, {len(investments)} investments")
        
        if has_financial_data:
            metrics = calculate_financial_metrics(current_user.id)
            cash_flow_chart = create_cash_flow_chart(transactions)
            net_worth_chart = create_net_worth_chart(net_worth_data)
            portfolio_chart = create_portfolio_chart(investments)
            insights = generate_ai_insights(current_user.id)
        else:
            metrics = None
            cash_flow_chart = None
            net_worth_chart = None
            portfolio_chart = None
            insights = []
        
        recent_transactions = transactions[:5] if transactions else []
        
        # Get budget data for dashboard
        user_budgets = Budget.query.filter_by(user_id=current_user.id).all()
        
        # Add period parameter logic (default to 'all' for dashboard)
        period = 'all'  # Dashboard always shows all transactions
        
        if period == '30days':
            from datetime import timedelta
            start_date = date.today() - timedelta(days=30)
        elif period == 'month':
            start_date = date.today().replace(day=1)
        elif period == '3months':
            from datetime import timedelta
            start_date = date.today() - timedelta(days=90)
        else:  # 'all' — default
            start_date = None
        
        # Filter transactions based on period
        if start_date:
            month_transactions = Transaction.query.filter(
                Transaction.user_id == current_user.id,
                Transaction.date >= start_date
            ).all()
        else:
            month_transactions = Transaction.query.filter(
                Transaction.user_id == current_user.id
            ).all()
        
        print(f"DEBUG: Found {len(month_transactions)} transactions for period '{period}'")
        
        # Get centralized financial summary for consistent calculations
        from app.analytics import get_user_financial_summary
        summary = get_user_financial_summary(current_user.id)
        
        # Filter transactions based on period for budget calculations
        if start_date:
            period_transactions = Transaction.query.filter(
                Transaction.user_id == current_user.id,
                Transaction.date >= start_date
            ).all()
        else:
            period_transactions = Transaction.query.filter(
                Transaction.user_id == current_user.id
            ).all()
        
        # Calculate category spending for the period (using standardized categories)
        period_category_spending = {}
        for t in period_transactions:
            if t.amount < 0:  # Only expenses
                cat = t.category.strip()
                period_category_spending[cat] = period_category_spending.get(cat, 0) + abs(t.amount)
        
        print(f"DEBUG Period Category Spending: {period_category_spending}")
        
        # Prepare budget data using consistent calculations
        budget_data = []
        for budget_item in summary['budget_status']:
            # Check if this budget item applies to the current period
            if budget_item['category'] in period_category_spending:
                period_spent = period_category_spending[budget_item['category']]
                period_percentage = (period_spent / budget_item['limit'] * 100) if budget_item['limit'] > 0 else 0
            else:
                period_spent = 0
                period_percentage = 0
            
            print(f"DEBUG Budget: {budget_item['category']}, Period Spent: ₹{period_spent}")
            
            budget_data.append({
                'category': budget_item['category'],
                'monthly_limit': budget_item['limit'],
                'spent': period_spent,
                'percentage': period_percentage,
                'remaining': budget_item['limit'] - period_spent,
                'over_budget': period_spent > budget_item['limit']
            })
        
        return render_template('dashboard.html',
                             has_financial_data=has_financial_data,
                             metrics=metrics,
                             cash_flow_chart=cash_flow_chart,
                             net_worth_chart=net_worth_chart,
                             portfolio_chart=portfolio_chart,
                             recent_transactions=recent_transactions,
                             insights=insights,
                             budget_data=budget_data)
                             
    except Exception as e:
        print(f"ERROR in dashboard route: {e}")
        return render_template('dashboard.html', 
                             has_financial_data=False,
                             metrics=None,
                             cash_flow_chart=None,
                             net_worth_chart=None, 
                             portfolio_chart=None,
                             recent_transactions=[],
                             insights=[],
                             budget_data=[])

@main_bp.route('/update-prices')
@login_required
def update_prices_route():
    """Manual trigger to update portfolio prices"""
    updated_count = update_portfolio_prices(current_user.id)
    
    if updated_count > 0:
        flash(f'Successfully updated {updated_count} investment prices with current market data!')
    else:
        flash('No investments updated. Please check your portfolio data.')
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/upload', methods=['POST'])
@login_required
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    data_type = request.form.get('data_type')
    
    print(f"DEBUG: Upload request - User: {current_user.id}, Type: {data_type}")
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        df = pd.read_csv(file)
        
        if data_type == 'transactions':
            inserted, skipped, errors = process_transactions_csv(df, current_user.id)
            message = f'Successfully processed {len(df)} transactions'
            
            if skipped > 0:
                message += f', {skipped} duplicates skipped automatically'
            if errors > 0:
                message += f', {errors} rows had errors'
        elif data_type == 'net_worth':
            process_net_worth_csv(df, current_user.id)
            message = f'Successfully processed {len(df)} net worth entries'
        elif data_type == 'portfolio':
            process_portfolio_csv(df, current_user.id)
            message = f'Successfully processed {len(df)} investment positions'
        else:
            return jsonify({'error': 'Invalid data type'}), 400
        
        print(f"DEBUG: Upload success - {message}")
        
        # Return JSON response for JavaScript to handle
        # The frontend will handle the refresh automatically
        return jsonify({
            'success': message, 
            'refresh': True,
            'inserted': inserted,
            'skipped': skipped,
            'errors': errors
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/transactions')
@login_required
def transactions():
    print(f"DEBUG: Transactions page accessed by User {current_user.id}")
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
    
@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        monthly_goal = float(request.form.get('monthly_goal', 0))
        current_user.monthly_goal = monthly_goal
        from app import db
        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('main.profile'))
    
    metrics = calculate_financial_metrics(current_user.id)
    return render_template('profile.html', metrics=metrics)

@main_bp.route('/api/financial-data')
@login_required
def api_financial_data():
    metrics = calculate_financial_metrics(current_user.id)
    return jsonify(metrics)

@main_bp.route('/debug-data')
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

# Budget Management Routes
@main_bp.route('/budgets', methods=['GET', 'POST'])
@login_required
def budgets():
    from app import db
    print(f"DEBUG: Budgets page accessed by User {current_user.id}")
    
    if request.method == 'POST':
        category = request.form['category']
        monthly_limit = float(request.form['monthly_limit'])
        print(f"DEBUG: User {current_user.id} creating/updating budget for {category}")
        
        # Check if budget already exists for this category
        existing_budget = Budget.query.filter_by(user_id=current_user.id, category=category).first()
        if existing_budget:
            existing_budget.monthly_limit = monthly_limit
            flash(f'Budget for {category} updated successfully!')
        else:
            new_budget = Budget(user_id=current_user.id, category=category, monthly_limit=monthly_limit)
            db.session.add(new_budget)
            flash(f'Budget for {category} created successfully!')
        
        db.session.commit()
        return redirect(url_for('main.budgets'))
    
    # Get all budgets for current user
    user_budgets = Budget.query.filter_by(user_id=current_user.id).all()
    
    # Add period parameter logic
    period = request.args.get('period', 'all')
    
    if period == '30days':
        from datetime import timedelta
        start_date = date.today() - timedelta(days=30)
    elif period == 'month':
        start_date = date.today().replace(day=1)
    elif period == '3months':
        from datetime import timedelta
        start_date = date.today() - timedelta(days=90)
    else:  # 'all' — default
        start_date = None
    
    # Filter transactions based on period
    if start_date:
        transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.date >= start_date
        ).all()
    else:
        transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id
        ).all()
    
    print(f"DEBUG: Budgets route - Found {len(transactions)} transactions for period '{period}'")
    
    # Get centralized financial summary for consistent calculations
    from app.analytics import get_user_financial_summary
    summary = get_user_financial_summary(current_user.id)
    
    # Calculate category spending for the period (using standardized categories)
    period_category_spending = {}
    for t in transactions:
        if t.amount < 0:  # Only expenses
            cat = t.category.strip()
            period_category_spending[cat] = period_category_spending.get(cat, 0) + abs(t.amount)
    
    print(f"DEBUG Period Category Spending (Budgets): {period_category_spending}")
    
    # Prepare budget data using consistent calculations
    budget_data = []
    for budget_item in summary['budget_status']:
        # Check if this budget item applies to the current period
        if budget_item['category'] in period_category_spending:
            period_spent = period_category_spending[budget_item['category']]
            period_percentage = (period_spent / budget_item['limit'] * 100) if budget_item['limit'] > 0 else 0
        else:
            period_spent = 0
            period_percentage = 0
        
        print(f"DEBUG Budget (Budgets): {budget_item['category']}, Period Spent: ₹{period_spent}")
        
        # Find the budget ID for this category
        budget_id = None
        for budget in user_budgets:
            if budget.category == budget_item['category']:
                budget_id = budget.id
                break
        
        budget_data.append({
            'category': budget_item['category'],
            'monthly_limit': budget_item['limit'],
            'spent': period_spent,
            'percentage': period_percentage,
            'remaining': budget_item['limit'] - period_spent,
            'over_budget': period_spent > budget_item['limit'],
            'id': budget_id
        })
    
    # Available categories for new budgets
    available_categories = ['Food', 'Shopping', 'Transport', 'Entertainment', 'Housing', 'Healthcare', 'Other']
    existing_categories = [b.category for b in user_budgets]
    remaining_categories = [cat for cat in available_categories if cat not in existing_categories]
    
    return render_template('budgets.html', 
                         budget_data=budget_data,
                         remaining_categories=remaining_categories,
                         current_period=period)

@main_bp.route('/budgets/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_budget(budget_id):
    from app import db
    
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
    if budget:
        db.session.delete(budget)
        db.session.commit()
        flash('Budget deleted successfully!')
    return redirect(url_for('main.budgets'))

# Clear Data Routes
@main_bp.route('/clear/transactions', methods=['POST'])
@login_required
def clear_transactions():
    from app import db
    from app.models import Transaction
    
    Transaction.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All transactions cleared successfully!')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/clear/networth', methods=['POST'])
@login_required
def clear_networth():
    from app import db
    from app.models import NetWorth
    
    NetWorth.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All net worth data cleared successfully!')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/clear/portfolio', methods=['POST'])
@login_required
def clear_portfolio():
    from app import db
    from app.models import Investment
    
    Investment.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All portfolio data cleared successfully!')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/clear/all', methods=['POST'])
@login_required
def clear_all_data():
    from app import db
    from app.models import Transaction, NetWorth, Investment, Budget
    
    # Clear all user data
    Transaction.query.filter_by(user_id=current_user.id).delete()
    NetWorth.query.filter_by(user_id=current_user.id).delete()
    Investment.query.filter_by(user_id=current_user.id).delete()
    Budget.query.filter_by(user_id=current_user.id).delete()
    
    db.session.commit()
    flash('All your financial data has been cleared successfully!')
    return redirect(url_for('main.profile'))
