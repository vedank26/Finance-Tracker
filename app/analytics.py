import pandas as pd
from datetime import datetime
import json

# Optional AI import - will only be used if available
try:
    import google.generativeai as genai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

def get_user_financial_summary(user_id):
    from app.models import Transaction, Investment, Budget
    
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    investments = Investment.query.filter_by(user_id=user_id).all()
    budgets = Budget.query.filter_by(user_id=user_id).all()
    
    # Income and expenses
    total_income = sum(
        t.amount for t in transactions
        if t.amount > 0
    )
    total_expenses = sum(
        abs(t.amount) for t in transactions
        if t.amount < 0
    )
    
    # Rates (always positive)
    savings_rate = (
        (total_income - total_expenses) /
        total_income * 100
    ) if total_income > 0 else 0
    savings_rate = max(0, savings_rate)
    
    expense_ratio = (
        total_expenses / total_income * 100
    ) if total_income > 0 else 0
    
    # Category spending
    # Using standardized categories
    category_spending = {}
    for t in transactions:
        if t.amount < 0:
            cat = t.category.strip()
            category_spending[cat] = (
                category_spending.get(cat, 0) +
                abs(t.amount)
            )
    
    top_categories = sorted(
        category_spending.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Portfolio
    portfolio_value = sum(
        inv.total_value for inv in investments
    )
    total_gain = sum(
        inv.gain_loss for inv in investments
    )
    
    # Budget vs actual
    budget_status = []
    for b in budgets:
        spent = category_spending.get(
            b.category, 0
        )
        budget_status.append({
            'category': b.category,
            'limit': b.monthly_limit,
            'spent': spent,
            'remaining': b.monthly_limit - spent,
            'percentage': (
                spent / b.monthly_limit * 100
            ) if b.monthly_limit > 0 else 0,
            'over_budget': spent > b.monthly_limit,
            'over_by': max(
                0, spent - b.monthly_limit
            )
        })
    
    return {
        'transactions': transactions,
        'investments': investments,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'savings_rate': savings_rate,
        'expense_ratio': expense_ratio,
        'category_spending': category_spending,
        'top_categories': top_categories,
        'portfolio_value': portfolio_value,
        'total_gain': total_gain,
        'budget_status': budget_status
    }

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
        from app.models import NetWorth
        from app import db
        
        # Get centralized financial summary
        summary = get_user_financial_summary(user_id)
        
        # Get net worth data (not in summary)
        net_worth_data = NetWorth.query.filter_by(user_id=user_id).order_by(NetWorth.date).all()
        current_net_worth = net_worth_data[-1].net_worth if net_worth_data else 0
        
        # Debug output
        print(f"DEBUG - Income: {summary['total_income']}, Expenses: {summary['total_expenses']}")
        
        # Create a simple class for dot notation access
        class FinancialMetrics:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        # Return ALL required metrics for template
        metrics = FinancialMetrics(
            net_cash_flow=summary['total_income'] - summary['total_expenses'],
            savings_rate=round(summary['savings_rate'], 1),
            current_net_worth=current_net_worth,
            portfolio_value=summary['portfolio_value'],
            total_gain_loss=summary['total_gain'],
            top_categories=summary['top_categories'],
            total_expenses=summary['total_expenses'],
            total_income=summary['total_income'],
            transaction_count=len(summary['transactions']),
            investment_count=len(summary['investments'])
        )
        
        print("DEBUG - Final metrics:", vars(metrics))
        return metrics
        
    except Exception as e:
        print(f"ERROR in calculate_financial_metrics: {e}")
        import traceback
        traceback.print_exc()
        
        # Return default metrics with ALL required fields
        class FinancialMetrics:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        return FinancialMetrics(
            net_cash_flow=0,
            savings_rate=0,
            current_net_worth=0,
            portfolio_value=0,
            total_gain_loss=0,
            top_categories=[],
            total_expenses=0,
            total_income=0,
            transaction_count=0,
            investment_count=0
        )

# HEALTH SCORE FUNCTIONS
def calculate_health_score(metrics):
    """Calculate financial health score (0-100)"""
    score = 0
    
    # Savings rate (max 30 points)
    if metrics.savings_rate >= 20:
        score += 30
    elif metrics.savings_rate >= 15:
        score += 25
    elif metrics.savings_rate >= 10:
        score += 20
    elif metrics.savings_rate >= 5:
        score += 15
    elif metrics.savings_rate > 0:
        score += 10
    
    # Cash flow (max 25 points)
    if metrics.net_cash_flow > 0:
        score += 25
    elif metrics.net_cash_flow >= -1000:
        score += 15
    else:
        score += 5
    
    # Net worth growth (max 25 points) - simplified for now
    if metrics.current_net_worth > 0:
        score += 20
    
    # Portfolio performance (max 20 points)
    if metrics.total_gain_loss > 0:
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

# Chart Functions
def create_cash_flow_chart(transactions):
    if not transactions:
        return []
    
    try:
        import pandas as pd
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
        return []
    
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
        return []
    
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

def generate_financial_insights(user_id):
    """Generate personalized financial insights based on user data"""
    from app.models import Transaction, NetWorth, Investment
    from sqlalchemy import desc
    
    insights = []
    
    try:
        # Get financial metrics
        metrics = calculate_financial_metrics(user_id)
        
        # Check if we have meaningful data
        has_transaction_data = metrics.total_income > 0 or metrics.total_expenses > 0
        has_investment_data = metrics.portfolio_value > 0
        has_net_worth_data = metrics.current_net_worth > 0
        
        # Always generate at least one insight if we have data
        insights_generated = False
        
        # Savings Rate Insights (always check if we have income/expenses)
        if has_transaction_data:
            insights_generated = True
            if metrics.savings_rate > 50:
                insights.append({
                    'type': 'success',
                    'title': 'Excellent Savings Discipline',
                    'message': f'Your savings rate is {metrics.savings_rate:.1f}%, which is very strong. You\'re building wealth rapidly!',
                    'icon': 'fa-piggy-bank'
                })
            elif metrics.savings_rate >= 20:
                insights.append({
                    'type': 'success',
                    'title': 'Healthy Savings Rate',
                    'message': f'Your savings rate of {metrics.savings_rate:.1f}% is good. Consider increasing it slightly to accelerate wealth growth.',
                    'icon': 'fa-chart-line'
                })
            elif metrics.savings_rate >= 10:
                insights.append({
                    'type': 'warning',
                    'title': 'Moderate Savings Rate',
                    'message': f'Your savings rate is {metrics.savings_rate:.1f}%. Try reducing discretionary expenses to improve financial stability.',
                    'icon': 'fa-exclamation-triangle'
                })
            else:
                insights.append({
                    'type': 'danger',
                    'title': 'Low Savings Rate',
                    'message': f'Your savings rate is only {metrics.savings_rate:.1f}%. Focus on increasing income or reducing expenses to build wealth.',
                    'icon': 'fa-exclamation-circle'
                })
        
        # Spending Category Analysis
        if metrics.top_categories and has_transaction_data:
            insights_generated = True
            top_category = metrics.top_categories[0]
            category_percentage = (top_category[1] / metrics.total_expenses) * 100 if metrics.total_expenses > 0 else 0
            
            if category_percentage > 40:
                insights.append({
                    'type': 'danger',
                    'title': 'High Spending Concentration',
                    'message': f'{top_category[0]} accounts for {category_percentage:.1f}% of your expenses. This concentration may impact financial flexibility.',
                    'icon': 'fa-chart-pie'
                })
            elif category_percentage > 30:
                insights.append({
                    'type': 'warning',
                    'title': 'Spending Concentration Alert',
                    'message': f'{top_category[0]} is your highest expense at {category_percentage:.1f}% of total spending. Consider optimizing this area.',
                    'icon': 'fa-chart-pie'
                })
            else:
                insights.append({
                    'type': 'info',
                    'title': 'Spending Distribution',
                    'message': f'Your highest expense category is {top_category[0]} at {category_percentage:.1f}% of total spending.',
                    'icon': 'fa-info-circle'
                })
        
        # Expense vs Income Analysis
        if has_transaction_data and metrics.total_income > 0:
            expense_ratio = (metrics.total_expenses / metrics.total_income) * 100
            insights_generated = True
            
            if expense_ratio > 90:
                insights.append({
                    'type': 'danger',
                    'title': 'Critical Expense Level',
                    'message': f'Your expenses are {expense_ratio:.1f}% of your income. This leaves very little room for savings and emergencies.',
                    'icon': 'fa-exclamation-triangle'
                })
            elif expense_ratio > 70:
                insights.append({
                    'type': 'warning',
                    'title': 'High Expense Ratio',
                    'message': f'Your expenses are {expense_ratio:.1f}% of your income. Try setting monthly budgets to control spending.',
                    'icon': 'fa-balance-scale'
                })
            elif expense_ratio < 50:
                insights.append({
                    'type': 'success',
                    'title': 'Excellent Expense Control',
                    'message': f'Your expenses are only {expense_ratio:.1f}% of your income. You have great financial discipline!',
                    'icon': 'fa-trophy'
                })
        
        # Investment Insights
        if has_investment_data:
            insights_generated = True
            if metrics.total_gain_loss is not None:
                if metrics.total_gain_loss > 0:
                    gain_percentage = (metrics.total_gain_loss / (metrics.portfolio_value - metrics.total_gain_loss)) * 100 if (metrics.portfolio_value - metrics.total_gain_loss) > 0 else 0
                    insights.append({
                        'type': 'success',
                        'title': 'Investment Growth',
                        'message': f'Your investments have gained ₹{metrics.total_gain_loss:,.2f} ({gain_percentage:+.1f}%). Continue diversifying to reduce risk.',
                        'icon': 'fa-chart-line'
                    })
                elif metrics.total_gain_loss < 0:
                    loss_percentage = abs(metrics.total_gain_loss / (metrics.portfolio_value - metrics.total_gain_loss)) * 100 if (metrics.portfolio_value - metrics.total_gain_loss) > 0 else 0
                    insights.append({
                        'type': 'warning',
                        'title': 'Investment Loss',
                        'message': f'Your investments are down ₹{abs(metrics.total_gain_loss):,.2f} ({loss_percentage:.1f}%). Review your investment strategy.',
                        'icon': 'fa-chart-line'
                    })
                else:
                    insights.append({
                        'type': 'info',
                        'title': 'Investment Stability',
                        'message': 'Your investments are stable. Consider regular contributions for long-term growth.',
                        'icon': 'fa-balance-scale'
                    })
            else:
                insights.append({
                    'type': 'success',
                    'title': 'Investment Portfolio Active',
                    'message': f'You have ₹{metrics.portfolio_value:,.2f} in investments. Continue diversifying your portfolio to reduce risk.',
                    'icon': 'fa-briefcase'
                })
        elif has_transaction_data:  # Has transactions but no investments
            insights.append({
                'type': 'info',
                'title': 'Investment Opportunity',
                'message': 'You currently have no investments recorded. Consider investing to grow your wealth beyond savings.',
                'icon': 'fa-lightbulb'
            })
        
        # Net Worth Trend Analysis
        net_worth_data = NetWorth.query.filter_by(user_id=user_id).order_by(desc(NetWorth.date)).limit(2).all()
        if len(net_worth_data) >= 2:
            insights_generated = True
            current_net_worth = net_worth_data[0].net_worth
            previous_net_worth = net_worth_data[1].net_worth
            net_worth_change = current_net_worth - previous_net_worth
            net_worth_change_pct = (net_worth_change / previous_net_worth) * 100 if previous_net_worth != 0 else 0
            
            if net_worth_change > 0:
                insights.append({
                    'type': 'success',
                    'title': 'Net Worth Growing',
                    'message': f'Your net worth increased by ₹{net_worth_change:,.2f} ({net_worth_change_pct:+.1f}%). Keep maintaining your current financial habits!',
                    'icon': 'fa-trending-up'
                })
            elif net_worth_change < 0:
                insights.append({
                    'type': 'warning',
                    'title': 'Net Worth Decline',
                    'message': f'Your net worth decreased by ₹{abs(net_worth_change):,.2f} ({net_worth_change_pct:+.1f}%). Review expenses and liabilities.',
                    'icon': 'fa-trending-down'
                })
            else:
                insights.append({
                    'type': 'info',
                    'title': 'Net Worth Stable',
                    'message': 'Your net worth remained stable. Focus on increasing savings and reducing debt for growth.',
                    'icon': 'fa-minus'
                })
        elif has_net_worth_data:  # Has net worth but no historical data
            insights.append({
                'type': 'info',
                'title': 'Net Worth Baseline',
                'message': f'Your current net worth is ₹{metrics.current_net_worth:,.2f}. Regular tracking will show your progress over time.',
                'icon': 'fa-flag'
            })
        
        # Ensure at least one insight if we have any data
        if not insights_generated and (has_transaction_data or has_investment_data or has_net_worth_data):
            insights.append({
                'type': 'info',
                'title': 'Financial Data Available',
                'message': 'Your financial data is loaded. More insights will appear as you add transactions and track your progress.',
                'icon': 'fa-database'
            })
        
        # If still no insights, provide guidance
        if not insights:
            insights.append({
                'type': 'info',
                'title': 'Start Your Financial Journey',
                'message': 'Upload your transaction data to begin receiving personalized financial insights and recommendations.',
                'icon': 'fa-rocket'
            })
            
    except Exception as e:
        print(f"Error generating insights: {e}")
        insights.append({
            'type': 'info',
            'title': 'Financial Insights',
            'message': 'Continue uploading your financial data to receive personalized insights about your spending habits and savings.',
            'icon': 'fa-info-circle'
        })
    
    return insights

# AI-POWERED FINANCIAL INSIGHTS
def generate_ai_insights(user_id):
    """Generate AI-powered financial insights using Google Gemini"""
    from flask import current_app
    
    # Get centralized financial summary
    summary = get_user_financial_summary(user_id)
    
    if not summary['transactions']:
        return []
    
    # Extract data from summary
    total_income = summary['total_income']
    total_expenses = summary['total_expenses']
    savings_rate = summary['savings_rate']
    top_categories = summary['top_categories'][:3]  # Top 3 for insights
    
    # Budget alerts from summary
    budget_alerts = []
    for budget_item in summary['budget_status']:
        if budget_item['over_budget']:
            budget_alerts.append(
                f"{budget_item['category']}: spent ₹{budget_item['spent']:,.0f} vs ₹{budget_item['limit']:,.0f} limit"
            )
    
    portfolio_value = summary['portfolio_value']
    total_gain = summary['total_gain']
    best = max(summary['investments'], key=lambda x: x.gain_loss_percent, default=None) if summary['investments'] else None
    
    # Build summary for Gemini
    summary_text = f"""
    Indian User Financial Data:
    
    Income & Expenses:
    - Total Income: ₹{total_income:,.0f}
    - Total Expenses: ₹{total_expenses:,.0f}
    - Savings Rate: {savings_rate:.1f}%
    - Expense Ratio: {(total_expenses/total_income*100 if total_income > 0 else 0):.1f}%
    
    Top Spending Categories:
    {chr(10).join([f"- {cat}: ₹{amt:,.0f} ({amt/total_expenses*100:.1f}%)" for cat, amt in top_categories]) if top_categories else "- No expense data"}
    
    Budget Alerts:
    {chr(10).join(budget_alerts) if budget_alerts else "- All within budget"}
    
    Portfolio:
    - Value: ₹{portfolio_value:,.0f}
    - Gain/Loss: ₹{total_gain:,.0f}
    - Best Stock: {best.symbol + ' +' + str(round(best.gain_loss_percent,1)) + '%' if best else 'None'}
    """
    
    try:
        # Check if AI is available
        if not AI_AVAILABLE:
            print("Google Generative AI library not installed - using fallback insights")
            return generate_fallback_insights(
                total_income,
                total_expenses,
                savings_rate,
                top_categories,
                budget_alerts,
                portfolio_value,
                total_gain,
                best
            )
        
        # Configure Gemini
        key = current_app.config['GEMINI_API_KEY']
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Generate insights
        response = model.generate_content(summary_text + """
        
        Provide 3-4 specific, actionable financial insights for this Indian user. 
        Focus on:
        1. Spending patterns (too high in any category?)
        2. Savings rate (good or needs improvement?)
        3. Budget performance (any overspending?)
        4. Investment suggestions (if any data available)
        
        Format each insight as a separate paragraph with practical advice.
        """)
        
        # Parse response into insights
        insights_text = response.text
        insights = []
        
        # Split by paragraphs and create insight objects
        paragraphs = [p.strip() for p in insights_text.split('\n\n') if p.strip()]
        
        for i, paragraph in enumerate(paragraphs[:4]):  # Max 4 insights
            # Determine insight type based on content
            insight_type = 'info'
            icon = 'fa-info-circle'
            title = f'Financial Insight {i+1}'
            
            if 'spending' in paragraph.lower() or 'expense' in paragraph.lower():
                if 'high' in paragraph.lower() or 'too much' in paragraph.lower():
                    insight_type = 'danger'
                    icon = 'fa-exclamation-triangle'
                    title = 'High Spending Alert'
                else:
                    insight_type = 'warning'
                    icon = 'fa-chart-pie'
                    title = 'Spending Analysis'
            elif 'saving' in paragraph.lower() or 'savings' in paragraph.lower():
                if 'good' in paragraph.lower() or 'excellent' in paragraph.lower():
                    insight_type = 'success'
                    icon = 'fa-piggy-bank'
                    title = 'Savings Performance'
                else:
                    insight_type = 'warning'
                    icon = 'fa-chart-line'
                    title = 'Savings Recommendation'
            elif 'budget' in paragraph.lower():
                if 'over' in paragraph.lower() or 'exceed' in paragraph.lower():
                    insight_type = 'danger'
                    icon = 'fa-exclamation-circle'
                    title = 'Budget Alert'
                else:
                    insight_type = 'success'
                    icon = 'fa-bullseye'
                    title = 'Budget Performance'
            elif 'investment' in paragraph.lower() or 'portfolio' in paragraph.lower():
                insight_type = 'success'
                icon = 'fa-chart-line'
                title = 'Investment Insight'
            
            insights.append({
                'type': insight_type,
                'icon': icon,
                'title': title,
                'message': paragraph,
                'advice': paragraph.split('Advice:')[-1].strip() if 'Advice:' in paragraph else ''
            })
        
        return insights
        
    except Exception as e:
        print(f"Gemini API error: {e}")
        return generate_fallback_insights(
            total_income,
            total_expenses,
            savings_rate,
            top_categories,
            budget_alerts,
            portfolio_value,
            total_gain,
            best
        )

def generate_fallback_insights(
    total_income, total_expenses,
    savings_rate, top_categories,
    budget_alerts, portfolio_value,
    total_gain, best
):
    """Generate fallback insights when AI API fails"""
    insights = []
    
    if budget_alerts:
        insights.append({
            "type": "danger",
            "icon": "fa-exclamation-triangle",
            "title": "Budget Exceeded",
            "message": budget_alerts[0],
            "advice": "Set a weekly spending limit to control this category."
        })
    
    if top_categories:
        cat, amt = top_categories[0]
        save = amt * 0.2
        insights.append({
            "type": "warning",
            "icon": "fa-chart-pie",
            "title": f"High {cat} Spending",
            "message": f"{cat} is your biggest expense at ₹{amt:,.0f}.",
            "advice": f"Cutting 20% saves ₹{save:,.0f}/month — ₹{save*12:,.0f}/year."
        })
    
    if savings_rate >= 50:
        sip = round(total_income * 0.05 / 12)
        insights.append({
            "type": "success",
            "icon": "fa-piggy-bank",
            "title": "Excellent Savings",
            "message": f"Saving {savings_rate:.1f}% of income.",
            "advice": f"Put ₹{sip:,.0f}/month into Nifty 50 SIP to grow wealth."
        })
    
    return insights

# Template context processor
def utility_processor():
    def get_last_price_update():
        return "Click 'Update Prices' to get live data"
    
    return {
        'calculate_health_score': calculate_health_score,
        'get_health_info': get_health_info,
        'get_last_price_update': get_last_price_update
    }
