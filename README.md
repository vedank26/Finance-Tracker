# 💰 Finance Tracker

A personal finance dashboard built with Flask 
that helps you track income, expenses, 
investments, and financial goals.

## 🚀 Features

- 📊 Dashboard — Visual overview of finances
- 💳 Transaction Tracking — Upload bank CSV
- 📈 Portfolio Management — Track Indian stocks
- 💡 AI Financial Insights — Smart spending advice
- 🎯 Budget Tracking — Set and monitor budgets
- 📉 Net Worth Timeline — Track wealth growth
- 🔒 Multi-user Support — Secure data isolation
- 🔄 Smart Upload — No duplicate transactions

## 🛠 Tech Stack

- Backend — Python, Flask, SQLAlchemy
- Frontend — HTML, Tailwind CSS, Bootstrap
- Database — SQLite
- Charts — Plotly
- Stock Data — yfinance (Indian NSE stocks)
- Authentication — Flask-Login

## 📦 Installation

Clone the repository
git clone https://github.com/vedank26/Finance-Tracker.git

Install dependencies
pip install -r requirements.txt

Run the application
python run.py

Open in browser
http://127.0.0.1:5000

## 📊 CSV Format

Transactions CSV
date,description,amount,category,type
2026-01-01,Salary,60000,Income,income
2026-01-02,Swiggy,450,Food,expense

Portfolio CSV
symbol,name,shares,currentPrice,costBasis
RELIANCE,Reliance Industries,10,2900,2500

Net Worth CSV
date,assets,liabilities
2026-01-01,500000,50000

## 👨‍💻 Developer

Vedank
GitHub: @vedank26
```

**Step 3 — Save file**
```
Ctrl + S
```

**Step 4 — Push to GitHub**
```
git add README.md
git commit -m "Added README content"
git push