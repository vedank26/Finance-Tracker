from app import create_app, db
from app.models import User, Transaction, Budget
from datetime import datetime, date, timedelta
import random

def create_test_data():
    app = create_app()
    with app.app_context():
        # Get or create a test user
        user = User.query.filter_by(username='testuser').first()
        if not user:
            user = User(username='testuser', email='test@example.com', password_hash='test')
            db.session.add(user)
            db.session.commit()
        
        # Create sample budgets
        budgets_data = [
            {'category': 'Food', 'monthly_limit': 10000},
            {'category': 'Shopping', 'monthly_limit': 8000},
            {'category': 'Transport', 'monthly_limit': 5000},
            {'category': 'Entertainment', 'monthly_limit': 3000},
        ]
        
        for budget_data in budgets_data:
            existing = Budget.query.filter_by(user_id=user.id, category=budget_data['category']).first()
            if not existing:
                budget = Budget(
                    user_id=user.id,
                    category=budget_data['category'],
                    monthly_limit=budget_data['monthly_limit']
                )
                db.session.add(budget)
        
        # Create sample transactions for current month
        current_month = date.today().replace(day=1)
        categories_spending = {
            'Food': 8500,
            'Shopping': 6500,
            'Transport': 3200,
            'Entertainment': 2800,
        }
        
        for category, amount in categories_spending.items():
            # Create multiple transactions per category
            num_transactions = random.randint(3, 8)
            per_transaction = amount // num_transactions
            
            for i in range(num_transactions):
                transaction_date = current_month + timedelta(days=random.randint(0, 25))
                transaction_amount = per_transaction + random.randint(-200, 200)
                
                transaction = Transaction(
                    user_id=user.id,
                    date=transaction_date,
                    description=f'{category} expense #{i+1}',
                    amount=-abs(transaction_amount),  # Negative for expenses
                    category=category,
                    type='expense'
                )
                db.session.add(transaction)
        
        db.session.commit()
        print("Test data created successfully!")
        
        # Test the budget calculation logic
        print("\n--- Testing Budget Calculation Logic ---")
        
        # Get budget data
        user_budgets = Budget.query.filter_by(user_id=user.id).all()
        month_transactions = Transaction.query.filter(
            Transaction.user_id == user.id,
            Transaction.date >= current_month,
            Transaction.type == 'expense'
        ).all()
        
        print(f"Found {len(user_budgets)} budgets")
        print(f"Found {len(month_transactions)} transactions this month")
        
        # Calculate spending by category
        category_spending = {}
        for t in month_transactions:
            category_spending[t.category] = category_spending.get(t.category, 0) + abs(t.amount)
        
        print("Category spending:")
        for category, amount in category_spending.items():
            print(f"  {category}: ₹{amount}")
        
        # Prepare budget data
        budget_data = []
        for budget in user_budgets:
            spent = category_spending.get(budget.category, 0)
            percentage = (spent / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0
            budget_data.append({
                'category': budget.category,
                'monthly_limit': budget.monthly_limit,
                'spent': spent,
                'percentage': percentage,
                'remaining': budget.monthly_limit - spent,
                'over_budget': spent > budget.monthly_limit
            })
        
        print("\nBudget data:")
        for data in budget_data:
            print(f"  {data['category']}: ₹{data['spent']}/₹{data['monthly_limit']} ({data['percentage']:.1f}%)")

if __name__ == '__main__':
    create_test_data()
