import pandas as pd
from datetime import datetime, timedelta
import random
import os

def generate_sample_data():
    """Generate sample financial data for demonstration"""
    
    # Sample transactions
    transactions = []
    categories = ['Food & Dining', 'Transportation', 'Housing', 'Shopping', 'Entertainment', 'Healthcare']
    
    for i in range(100):
        date = datetime.now() - timedelta(days=random.randint(1, 90))
        is_income = random.random() < 0.2  # 20% chance of income
        
        if is_income:
            amount = random.randint(10000, 50000)
            description = random.choice(['Salary', 'Freelance Payment', 'Investment Return', 'Bonus'])
            category = 'Income'
            trans_type = 'income'
        else:
            amount = random.randint(100, 5000)
            category = random.choice(categories)
            descriptions = {
                'Food & Dining': ['Grocery Store', 'Restaurant', 'Coffee Shop', 'Supermarket'],
                'Transportation': ['Gas Station', 'Uber Ride', 'Public Transport', 'Car Maintenance'],
                'Housing': ['Rent Payment', 'Electric Bill', 'Internet Bill', 'Water Bill'],
                'Shopping': ['Amazon Purchase', 'Clothing Store', 'Electronics', 'Online Shopping'],
                'Entertainment': ['Netflix', 'Movie Theater', 'Concert', 'Sports Event'],
                'Healthcare': ['Doctor Visit', 'Pharmacy', 'Dental Checkup', 'Health Insurance']
            }
            description = random.choice(descriptions[category])
            trans_type = 'expense'
        
        transactions.append({
            'date': date.strftime('%Y-%m-%d'),
            'description': description,
            'amount': amount,
            'category': category,
            'type': trans_type
        })
    
    # Sample net worth data
    net_worth_data = []
    base_net_worth = 500000
    for i in range(12):
        date = datetime.now() - timedelta(days=30*(11-i))
        growth = random.randint(5000, 20000)
        base_net_worth += growth
        
        net_worth_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'assets': base_net_worth + random.randint(100000, 200000),
            'liabilities': random.randint(50000, 100000),
            'net_worth': base_net_worth
        })
    
    # Sample portfolio data
    portfolio_data = [
        {'symbol': 'AAPL', 'name': 'Apple Inc.', 'shares': 10, 'current_price': 150, 'cost_basis': 130},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'shares': 5, 'current_price': 2800, 'cost_basis': 2500},
        {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'shares': 20, 'current_price': 200, 'cost_basis': 180},
        {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'shares': 8, 'current_price': 300, 'cost_basis': 280}
    ]
    
    return transactions, net_worth_data, portfolio_data

def create_sample_files():
    """Save sample data to CSV files"""
    transactions, net_worth, portfolio = generate_sample_data()
    
    pd.DataFrame(transactions).to_csv('sample_transactions.csv', index=False)
    pd.DataFrame(net_worth).to_csv('sample_net_worth.csv', index=False)
    pd.DataFrame(portfolio).to_csv('sample_portfolio.csv', index=False)
    
    print("Sample files created:")
    print("- sample_transactions.csv")
    print("- sample_net_worth.csv") 
    print("- sample_portfolio.csv")

def ask_user_preference():
    """Ask user whether they want to use sample data or real data"""
    print("\n" + "="*50)
    print("FINANCIAL DASHBOARD DATA SETUP")
    print("="*50)
    
    while True:
        choice = input("Do you want to generate sample data? (y/n): ").lower().strip()
        if choice in ['y', 'yes']:
            create_sample_files()
            print("\nSample data generated successfully!")
            break
        elif choice in ['n', 'no']:
            print("\nUsing existing data files (if available).")
            break
        else:
            print("Please enter 'y' or 'n'")

# === ADD THIS SECTION AT THE END ===
if __name__ == "__main__":
    ask_user_preference()