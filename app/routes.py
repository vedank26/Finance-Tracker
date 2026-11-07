from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date
from app.models import Transaction, NetWorth, Investment, Budget
from app.analytics import calculate_financial_metrics, create_cash_flow_chart, create_net_worth_chart, create_portfolio_chart, generate_ai_insights, calculate_monthly_budget_status, get_month_date_range
from app.services import _safe_float, process_transactions_csv, process_net_worth_csv, process_portfolio_csv, update_portfolio_prices
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
        
        # Monthly Budget Tracking: compute spending strictly for the current calendar month
        budget_data = calculate_monthly_budget_status(current_user.id)
        
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

    # -----------------------------------------------------------------
    # Security: enforce .csv extension and a 5 MB size limit
    # -----------------------------------------------------------------
    filename = file.filename or ''
    if not filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only .csv files are accepted'}), 400

    # Read into memory so we can check size before parsing
    file_bytes = file.read()
    MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MB
    if len(file_bytes) > MAX_CSV_BYTES:
        return jsonify({'error': 'File exceeds the 5 MB size limit'}), 400

    # Re-wrap bytes as a file-like object for pandas
    import io
    file_obj = io.BytesIO(file_bytes)

    try:
        df = pd.read_csv(file_obj)

        if data_type == 'transactions':
            inserted, skipped, errors = process_transactions_csv(df, current_user.id)
            message = f'Successfully processed {len(df)} transactions'
            if skipped > 0:
                message += f', {skipped} duplicates skipped automatically'
            if errors > 0:
                message += f', {errors} rows had errors'
        elif data_type == 'net_worth':
            process_net_worth_csv(df, current_user.id)
            inserted, skipped, errors = len(df), 0, 0
            message = f'Successfully processed {len(df)} net worth entries'
        elif data_type == 'portfolio':
            process_portfolio_csv(df, current_user.id)
            inserted, skipped, errors = len(df), 0, 0
            message = f'Successfully processed {len(df)} investment positions'
        else:
            return jsonify({'error': 'Invalid data type'}), 400

        print(f"DEBUG: Upload success - {message}")

        return jsonify({
            'success': message,
            'refresh': True,
            'inserted': inserted,
            'skipped': skipped,
            'errors': errors
        })

    except pd.errors.EmptyDataError:
        return jsonify({'error': 'The CSV file is empty or has no data rows'}), 400
    except pd.errors.ParserError:
        return jsonify({'error': 'Could not parse the CSV file. Check the format and try again'}), 400
    except Exception as e:
        # Log full error server-side; return a safe message to the browser
        print(f"ERROR in upload_csv: {e}")
        return jsonify({'error': 'Upload failed. Please check your file format and try again'}), 500


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
    
    current_month = date.today().strftime('%Y-%m')

    return render_template('transactions.html', 
                         transactions=transactions_data,
                         categories=categories,
                         metrics=metrics,
                         current_month=current_month)


@main_bp.route('/transactions/export-monthly', methods=['POST'])
@login_required
def export_monthly_report():
    from app.reports import parse_and_validate_month, generate_monthly_csv, upload_report_to_s3
    month_str = request.form.get('month', '').strip()
    try:
        year, month = parse_and_validate_month(month_str)
    except ValueError as e:
        flash(f"Invalid month selected: {e}", 'error')
        return redirect(url_for('main.transactions'))

    csv_content = generate_monthly_csv(current_user.id, year, month)
    success, result, presigned_url = upload_report_to_s3(current_user.id, year, month, csv_content)

    if not success:
        flash(result, 'error')
        return redirect(url_for('main.transactions'))

    flash(f"Monthly report for {year:04d}-{month:02d} successfully exported and archived to Amazon S3.", 'success')
    return redirect(url_for('main.download_report', key=result))


@main_bp.route('/reports/download', methods=['GET'])
@login_required
def download_report():
    from app.reports import generate_report_presigned_url
    object_key = request.args.get('key', '').strip()
    if not object_key:
        flash("No report key specified.", 'error')
        return redirect(url_for('main.transactions'))

    try:
        presigned_url = generate_report_presigned_url(current_user.id, object_key)
        return redirect(presigned_url)
    except PermissionError:
        flash("Access denied: You are not authorized to access this report.", 'error')
        return redirect(url_for('main.transactions'))
    except Exception as e:
        flash(f"Unable to generate download link: {e}", 'error')
        return redirect(url_for('main.transactions'))

    
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
    """Debug route — only available when the application is running in debug mode."""
    from flask import current_app, abort
    if not current_app.debug:
        abort(404)

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
        category = request.form.get('category', '').strip()
        if not category:
            flash('Category is required.')
            return redirect(url_for('main.budgets'))

        raw_limit = request.form.get('monthly_limit')
        try:
            monthly_limit = _safe_float(raw_limit, 'monthly_limit')
            if monthly_limit < 0:
                raise ValueError("Monthly limit cannot be negative")
        except (ValueError, TypeError) as e:
            flash(f"Invalid budget limit: {e}")
            return redirect(url_for('main.budgets'))

        print(f"DEBUG: User {current_user.id} creating/updating budget for {category}")
        
        # Check if budget already exists for this category for the current user
        existing_budget = Budget.query.filter(
            Budget.user_id == current_user.id,
            db.func.lower(Budget.category) == category.lower()
        ).first()

        if existing_budget:
            existing_budget.monthly_limit = monthly_limit
            flash(f'Budget for {existing_budget.category} updated successfully!')
        else:
            new_budget = Budget(user_id=current_user.id, category=category, monthly_limit=monthly_limit)
            db.session.add(new_budget)
            flash(f'Budget for {category} created successfully!')
        
        db.session.commit()
        return redirect(url_for('main.budgets'))
    
    # Get all budgets for current user (strictly isolated)
    user_budgets = Budget.query.filter_by(user_id=current_user.id).all()
    
    # Period parameter logic - default to 'month' ("This Month")
    period = request.args.get('period', '').strip().lower()
    month_param = request.args.get('month', '').strip()

    target_year = None
    target_month = None

    if month_param:
        try:
            parts = month_param.split('-')
            if len(parts) == 2:
                y = int(parts[0])
                m = int(parts[1])
                if 1 <= m <= 12 and 1900 <= y <= 9999:
                    target_year = y
                    target_month = m
                    period = 'month'
                else:
                    flash('Invalid month specified. Showing current month instead.')
                    period = 'month'
            else:
                flash('Invalid month format. Expected YYYY-MM. Showing current month instead.')
                period = 'month'
        except (ValueError, TypeError):
            flash('Invalid month format. Expected YYYY-MM. Showing current month instead.')
            period = 'month'

    if not period:
        period = 'month'

    if period == 'month':
        budget_data = calculate_monthly_budget_status(
            current_user.id, year=target_year, month=target_month
        )
    elif period == '30days':
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        budget_data = calculate_monthly_budget_status(
            current_user.id, start_date=start_date, end_date=end_date
        )
    elif period == '3months':
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        budget_data = calculate_monthly_budget_status(
            current_user.id, start_date=start_date, end_date=end_date
        )
    elif period == 'all':
        budget_data = calculate_monthly_budget_status(
            current_user.id, start_date=date.min, end_date=date.max
        )
    else:
        period = 'month'
        budget_data = calculate_monthly_budget_status(current_user.id)

    # Available categories for new budgets (preserving existing + adding Bills and Education)
    available_categories = ['Food', 'Shopping', 'Transport', 'Entertainment', 'Housing', 'Healthcare', 'Bills', 'Education', 'Other']
    existing_categories = [b.category.strip().lower() for b in user_budgets]
    remaining_categories = [cat for cat in available_categories if cat.lower() not in existing_categories]
    
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
    else:
        flash('Budget not found.')
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
