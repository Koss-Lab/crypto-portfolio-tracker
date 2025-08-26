# 💹 Crypto Portfolio Tracker

## 📌 Overview

Crypto Portfolio Tracker is a Python application that allows users to **track and analyze their cryptocurrency investments**.
The app connects to the **CoinGecko API** to fetch live prices, stores user transactions in a **PostgreSQL database**, and provides tools to view portfolios, manage transactions, and export reports.

This project was built during the **Developers Institute Hackathon** and showcases:

* ✅ Python
* ✅ PostgreSQL (database)
* ✅ psycopg2 (DB connection)
* ✅ Requests (API calls)
* ✅ Faker (generate fake users/transactions)
* ✅ JSON & CSV (export data)
* ✅ CLI Application

---

## ⚡ Features

### Core Features

* Add **BUY/SELL/SEND/RECEIVE** transactions
* Store transactions in PostgreSQL
* Fetch live crypto prices from CoinGecko API
* Calculate current portfolio value
* Show portfolio of a single user or all users
* Export portfolios to **CSV & JSON**
* Export detailed **transactions of a user** (bank statement style)

### Extra Features

* Delete or update a transaction
* Show **Top 5 richest users** by portfolio value
* Search users by username/email
* Interactive **CLI menu** (14 options)

---

## 🛠️ Technologies Used

* **Python 3.10+**
* **PostgreSQL 17**
* **psycopg2**
* **dotenv**
* **requests**
* **Faker**
* **JSON / CSV**

---

## 📂 Project Structure

```
crypto-portfolio-tracker/
│
├── db.py             # Initialize DB with schema.sql
├── schema.sql        # Tables: users, transactions, prices
├── seed.py           # Generate fake users + transactions
├── api.py            # Fetch live crypto prices
├── portfolio.py      # Calculate user portfolios
├── export.py         # Export portfolios + transactions
├── main.py           # CLI menu (14 options)
├── queries.sql       # Useful SQL queries
├── crypto_venv/      # Virtual environment
└── .env              # Environment variables (DB + API key)
```

---

## ⚙️ Step-by-Step Setup

### 1. Clone the repository

```bash
git clone https://github.com/Koss-Lab/crypto-portfolio-tracker.git
cd crypto-portfolio-tracker
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv crypto_venv
source crypto_venv/bin/activate   # Mac/Linux
crypto_venv\Scripts\activate      # Windows PowerShell
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Make sure PostgreSQL is installed and running.
Create a database named `crypto_portfolio`:

```sql
CREATE DATABASE crypto_portfolio;
```

### 5. Create a `.env` file

Inside the folder `crypto_venv/`, create a file named `.env` and add your credentials:

```
DB_NAME=crypto_portfolio
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
COINGECKO_API_KEY=your_api_key
```

👉 You can get a free API key from [CoinGecko](https://www.coingecko.com/).

### 6. Initialize the database schema

```bash
python3 db.py
```

### 7. Seed fake users & transactions

```bash
python3 seed.py
```

---

## 🚀 Usage

Run the main app:

```bash
python3 main.py
```

You will see this menu:

```
=============================
   Crypto Portfolio Tracker
=============================
1. Update prices
2. Show all users
3. Show portfolio of a user
4. Show portfolios of all users
5. Add User
6. Add Transaction (BUY/SELL/SEND/RECEIVE)
7. Show all transactions of a user
8. Delete a transaction
9. Update a transaction
10. Top 5 richest users
11. Search user by username/email
12. Export all portfolios (JSON + CSV)
13. Export transactions of a user (CSV + JSON)
14. Exit
```

---

## 📊 Example Exports

### `portfolios.json`

```json
[
  {
    "user": "john_doe",
    "email": "john@example.com",
    "portfolio": {
      "BTC": {"amount": 0.5, "value_usd": 20000},
      "ETH": {"amount": 2.0, "value_usd": 3000}
    },
    "total_value_usd": 23000
  }
]
```

### `user_1_transactions.csv`

```
id,coin,transaction_type,amount,price,date
1,BTC,BUY,0.5,20000,2025-08-27 12:00:00
2,ETH,SELL,1.0,2500,2025-08-20 15:30:00
3,XRP,RECEIVE,100,0.3,2025-08-19 10:15:00
```

---

## 🏆 Hackathon Criteria

* **Technology**: PostgreSQL, Python, API integration, exports, CLI → ✅
* **Completion**: Fully working app, end-to-end → ✅
* **Learning**: New tools explored (Faker, dotenv, psycopg2, API handling) → ✅
* **Teamwork**: GitHub collaboration, commits, branches → ✅

---

## ✨ Future Improvements

* GUI version with Tkinter (bonus)
* Matplotlib charts (portfolio history, asset allocation)
* Currency conversion (USD/EUR/ILS)
* Price alerts / notifications

---

## 👨‍💻 Authors

* **Ariel Kossmann**
* **David Yarden**

Built with ❤️ during the **Developers Institute Hackathon 2025**.
