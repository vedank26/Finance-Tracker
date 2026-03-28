import pandas as pd
import yfinance as yf
from datetime import datetime
import hashlib

# FINGERPRINT AND CATEGORY FUNCTIONS
def generate_fingerprint(user_id, date_str, description, amount):
    """
    Generate unique fingerprint for a transaction based on key fields.
    Same transaction will always produce same fingerprint.
    """
    # Normalize inputs to avoid minor formatting differences
    clean_desc = str(description).strip().lower()
    clean_amount = f"{float(amount):.2f}"
    clean_date = str(date_str).strip()
    
    # Combine into unique string
    raw = (
        f"{user_id}_{clean_date}_"
        f"{clean_desc}_{clean_amount}"
    )
    
    # Generate MD5 hash (32 characters)
    fingerprint = hashlib.md5(
        raw.encode('utf-8')
    ).hexdigest()
    
    return fingerprint

def standardize_category(category, amount):
    if not category:
        return 'Other'
    
    cat = str(category).strip().lower()
    
    # Income
    if cat in [
        'income', 'salary', 'wages', 
        'payroll', 'bonus', 'freelance',
        'business income', 'other income'
    ]:
        return 'Income'
    
    # Food
    if cat in [
        'food', 'food & dining', 
        'food and dining', 'groceries',
        'grocery', 'restaurant', 'dining',
        'swiggy', 'zomato', 'supermarket',
        'cafe', 'coffee', 'snacks'
    ]:
        return 'Food'
    
    # Transport
    if cat in [
        'transport', 'transportation',
        'travel', 'uber', 'ola', 'taxi',
        'bus', 'metro', 'fuel', 'petrol',
        'auto', 'cab', 'flight', 'train'
    ]:
        return 'Transport'
    
    # Shopping
    if cat in [
        'shopping', 'clothes', 'clothing',
        'amazon', 'flipkart', 'fashion',
        'accessories', 'electronics',
        'online shopping', 'retail'
    ]:
        return 'Shopping'
    
    # Housing
    if cat in [
        'housing', 'rent', 'mortgage',
        'maintenance', 'home', 'house',
        'repair', 'furniture'
    ]:
        return 'Housing'
    
    # Bills
    if cat in [
        'bills', 'utilities', 'electricity',
        'water', 'gas', 'internet', 'wifi',
        'mobile', 'phone', 'recharge',
        'bill', 'subscription'
    ]:
        return 'Bills'
    
    # Entertainment
    if cat in [
        'entertainment', 'movies', 'netflix',
        'spotify', 'gaming', 'games',
        'streaming', 'shows', 'events',
        'concert', 'sports'
    ]:
        return 'Entertainment'
    
    # Healthcare
    if cat in [
        'healthcare', 'medical', 'doctor',
        'hospital', 'pharmacy', 'medicine',
        'health', 'dental', 'gym',
        'fitness'
    ]:
        return 'Healthcare'
    
    # Education
    if cat in [
        'education', 'college', 'school',
        'course', 'books', 'fees',
        'tuition', 'learning'
    ]:
        return 'Education'
    
    return 'Other'

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
        from app.models import Investment
        from app import db
        
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

# CSV PROCESSING FUNCTIONS
def process_transactions_csv(df, user_id):
    from app.models import Transaction
    from app import db
    
    inserted = 0
    skipped = 0
    errors = 0
    
    try:
        for _, row in df.iterrows():
            try:
                # Extract raw values
                date_str = str(
                    row.get('date') or 
                    row.get('Date') or ''
                ).strip()
                
                description = str(
                    row.get('description') or
                    row.get('Description') or
                    'Unknown'
                ).strip()
                
                amount = float(
                    row.get('amount') or
                    row.get('Amount') or 0
                )
                
                raw_category = str(
                    row.get('category') or
                    row.get('Category') or ''
                ).strip()
                
                trans_type = str(
                    row.get('type') or
                    row.get('Type') or ''
                ).lower().strip()
                
                # Normalize amount sign
                if trans_type == 'expense' and amount > 0:
                    amount = -abs(amount)
                elif trans_type == 'income' and amount < 0:
                    amount = abs(amount)
                elif amount > 0 and not trans_type:
                    # No type given — check category
                    if raw_category.lower() in [
                        'income', 'salary', 
                        'wages', 'bonus',
                        'freelance', 'credit'
                    ]:
                        amount = abs(amount)
                        trans_type = 'income'
                    else:
                        amount = -abs(amount)
                        trans_type = 'expense'
                
                # Set type from amount if still empty
                if not trans_type:
                    trans_type = (
                        'income' if amount > 0
                        else 'expense'
                    )
                
                # Standardize category
                category = standardize_category(
                    raw_category, amount
                )
                
                # Generate fingerprint
                fp = generate_fingerprint(
                    user_id,
                    date_str,
                    description,
                    amount
                )
                
                # Check if already exists
                existing = Transaction.query.filter_by(
                    user_id=user_id,
                    fingerprint=fp
                ).first()
                
                if existing:
                    # Same transaction already in database — skip
                    skipped += 1
                    continue
                
                # New transaction — insert
                transaction = Transaction(
                    user_id=user_id,
                    date=datetime.strptime(
                        date_str,
                        '%Y-%m-%d'
                    ).date(),
                    description=description,
                    amount=amount,
                    category=category,
                    type=trans_type,
                    fingerprint=fp
                )
                db.session.add(transaction)
                inserted += 1
                
            except Exception as row_error:
                print(
                    f"Row error: {row_error}"
                )
                errors += 1
                continue
        
        db.session.commit()
        
        print(
            f"Upload complete: "
            f"{inserted} inserted, "
            f"{skipped} skipped (duplicates), "
            f"{errors} errors"
        )
        
        return inserted, skipped, errors
        
    except Exception as e:
        db.session.rollback()
        print(f"Upload failed: {e}")
        raise
    
def process_net_worth_csv(df, user_id):
    from app.models import NetWorth
    from app import db
    
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
    from app.models import Investment
    from app import db
    
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
