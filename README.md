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

### Core Features (CLI)

* Add **BUY/SELL/SEND/RECEIVE** transactions
* Store transactions in PostgreSQL
* Fetch crypto prices from CoinGecko
* Calculate current portfolio value
* Show portfolio for a user or for **all** users
* Export portfolios to **CSV & JSON**
* Export detailed **transactions of a user** (bank statement style)
* Delete or update a transaction
* Show **Top 5 richest users** by portfolio value
* Search users by username/email
* Interactive **CLI menu (14 options)**.&#x20;

### Bonus Features (GUI)

* **Tkinter GUI** mirroring the CLI actions most people need (users, transactions, quick exports)
* **Charts** with Matplotlib:

  * **Pie** = portfolio allocation (USD snapshot)
  * **Line** = historical portfolio value (30 / 90 / 180 / **365** days, default 365)
  * Smart caching + fallbacks to reduce API limits; stables shown as flat \~\$1
* **Export Chart (PDF)**: saves the currently displayed chart (Pie/Line)
* **Portfolio Report (PDF)**: title + holdings table + Pie + Line (USD)
* **Alerts tab** (DB-backed):

  * Add an alert: *user id, coin, operator (`>` or `<`), threshold (USD)*
  * List alerts
  * **Check Alerts Now**: evaluates alerts against latest prices and deactivates those triggered

---

## 🛠️ Technologies Used

* **Python 3.10+**
* **PostgreSQL 17**
* **psycopg2**, **requests**
* **dotenv**, **python-dotenv**
* **requests**
* **Faker** (seed demo data)
* **JSON / CSV**
* **Matplotlib** (charts), **ReportLab** (PDF)
* **Tkinter** (GUI)

---

## 📂 Project Structure

```
crypto-portfolio-tracker/
│
├── db.py             # Initialize DB with schema.sql
├── schema.sql        # Tables: users, transactions, prices, alerts
├── seed.py           # Generate fake users + transactions
├── api.py            # Fetch prices (CoinGecko) + helpers
├── portfolio.py      # Portfolio calculations (BUY/SELL/SEND/RECEIVE)
├── export.py         # Export portfolios + transactions (CSV/JSON)
├── main.py           # CLI menu (14 options)
├── gui.py            # Tkinter GUI app (bonus): charts, PDF exports, alerts
├── queries.sql       # Useful SQL queries
├── crypto_venv/      # Virtual environment
└── .env              # Environment variables (DB + optional API key)
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

### CLI Menu 

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
### `Exports tip`
> CLI tips: exporting portfolios writes `portfolios.csv` + `portfolios.json`; exporting a user’s transactions writes `user_<id>_transactions.csv` + `.json`.&#x20;

---

### GUI (bonus)

Run the GUI:

```bash
python3 gui.py
```

**Tabs & actions**

* **Tkinter GUI** mirroring the CLI actions most people need (users, transactions, quick exports)
* **Dashboard**: quick stats for Users / Transactions / Coins tracked
* **Users**: list/add/search users
* **Transactions**: add, list by user, update/delete
* **Charts**:

  * Enter *User ID*
  * **Draw Pie (Allocation)** → snapshot allocation (USD)
  * **Draw Line (Historical)** → 30/90/180/**365** days (default 365)
  * **Export Chart (PDF)** → saves the currently visible chart
  * **Portfolio Report (PDF)** → full PDF: header + holdings table + Pie + Line
* **Alerts**:

  * Add alert (user, coin, `>`/`<`, price USD)
  * List alerts
  * **Check Alerts Now** (evaluates from latest prices and deactivates hits)

**Notes & behavior**

* Historical charts use caching + backoff; if CoinGecko limits are hit, the app falls back to an approximate line using latest prices.
* Stablecoins are treated as flat \~\$1 in charts to avoid noise.

**Coins performance** 
* Refer to `COINS.md` for the updates of which coin works, and which don't works yet
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

## 🧪 Known issues / Next steps

* Some coins may still hit CoinGecko rate limits for **historical** series (HTTP 429/400).
  The GUI retries with backoff + caching; a future improvement is auto-resolving tickers via `/search` and a “clear cache” button.
* Optional later: background **alert checker** (cron) to notify by email/Slack.
* Optional later: FX converter (USD/EUR/ILS) if needed — currently **USD only** for stability.

---

## 👨‍💻 Authors

* **Ariel Kossmann**
* **David Yarden**

Built with ❤️ during the **Developers Institute Hackathon 2025**.
