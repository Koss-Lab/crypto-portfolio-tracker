# main.py

import os
import psycopg2
from dotenv import load_dotenv
from api import get_top10_prices
from portfolio import get_portfolio
from export import export_all_users
from datetime import datetime
import csv
import json

# Load env vars
load_dotenv(dotenv_path=os.path.join("crypto_venv", ".env"))

def connect_db():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def get_all_users():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email FROM users;")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

def add_user():
    username = input("Enter username: ")
    email = input("Enter email: ")
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, email) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
        (username, email)
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ User {username} added!")

def add_transaction():
    users = get_all_users()
    print("\n👥 Existing Users:")
    for uid, username, email in users:
        print(f" - {uid}: {username} ({email})")

    user_id = int(input("Select user_id: "))
    coin = input("Coin (e.g. BTC, ETH): ").upper()
    tx_type = input("Type (BUY/SELL/SEND/RECEIVE): ").upper()
    amount = float(input("Amount: "))

    # Date
    date_input = input("Date (YYYY-MM-DD HH:MM:SS) or leave empty for now: ")
    if date_input.strip() == "":
        tx_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        tx_date = date_input

    # Price: for BUY/SELL we ask manually, for SEND/RECEIVE we fetch from API
    if tx_type in ["BUY", "SELL"]:
        price = float(input("Price (USD): "))
    else:  # SEND/RECEIVE
        prices = get_top10_prices()
        price = prices.get(coin, 0)
        print(f"📈 Auto price for {coin} at {tx_date}: ${price}")

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO transactions (user_id, coin, transaction_type, amount, price, date)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (user_id, coin, tx_type, amount, price, tx_date)
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Transaction added: {tx_type} {amount} {coin} at ${price} on {tx_date}")

def show_user_transactions():
    user_id = int(input("Enter user ID: "))
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, coin, transaction_type, amount, price, date FROM transactions WHERE user_id = %s ORDER BY date DESC;",
        (user_id,)
    )
    transactions = cur.fetchall()
    cur.close()
    conn.close()

    print(f"\n📜 Transactions for user {user_id}:")
    if not transactions:
        print("⚠️ No transactions found")
    else:
        for tid, coin, tx_type, amount, price, date in transactions:
            print(f" - [{tid}] {tx_type} {amount} {coin} at ${price} on {date}")

def delete_transaction():
    tx_id = int(input("Enter transaction ID to delete: "))
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = %s RETURNING id;", (tx_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if deleted:
        print(f"🗑️ Transaction {tx_id} deleted.")
    else:
        print("⚠️ No transaction found with that ID.")

def update_transaction():
    tx_id = int(input("Enter transaction ID to update: "))

    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT transaction_type, coin FROM transactions WHERE id=%s;", (tx_id,))
    row = cur.fetchone()
    if not row:
        print("⚠️ No transaction found with that ID.")
        return
    tx_type, coin = row

    # BUY/SELL = amount + price manuals
    if tx_type in ["BUY", "SELL"]:
        amount = float(input("New amount: "))
        price = float(input("New price (USD): "))
    else:  # SEND/RECEIVE = price manual + price auto
        amount = float(input("New amount: "))
        prices = get_top10_prices()
        price = prices.get(coin, 0)
        print(f"📈 Auto price for {coin}: ${price}")

    cur.execute(
        "UPDATE transactions SET amount=%s, price=%s WHERE id=%s RETURNING id;",
        (amount, price, tx_id)
    )
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if updated:
        print(f"✏️ Transaction {tx_id} updated (amount={amount}, price={price}).")
    else:
        print("⚠️ Update failed.")

def top5_users():
    users = get_all_users()
    results = []
    for uid, username, email in users:
        portfolio = get_portfolio(uid)
        results.append((username, portfolio["total_value_usd"]))
    results.sort(key=lambda x: x[1], reverse=True)
    print("\n👑 Top 5 Users by Portfolio Value:")
    for i, (username, value) in enumerate(results[:5], start=1):
        print(f" {i}. {username} → ${value:.2f}")

def search_user():
    keyword = input("Enter username or email keyword: ").lower()
    users = get_all_users()
    print("\n🔎 Search results:")
    found = False
    for uid, username, email in users:
        if keyword in username.lower() or keyword in email.lower():
            print(f" - {uid}: {username} ({email})")
            found = True
    if not found:
        print("⚠️ No user found with that keyword.")

def export_user_transactions():
    """Export transactions of a user to CSV + JSON"""
    user_id = int(input("Enter user ID to export: "))
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, coin, transaction_type, amount, price, date FROM transactions WHERE user_id = %s ORDER BY date;",
        (user_id,)
    )
    transactions = cur.fetchall()
    cur.close()
    conn.close()

    if not transactions:
        print("⚠️ No transactions found for this user.")
        return

    # CSV
    csv_file = f"user_{user_id}_transactions.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "coin", "transaction_type", "amount", "price", "date"])
        writer.writerows(transactions)

    # JSON
    json_file = f"user_{user_id}_transactions.json"
    data = [
        {"id": tid, "coin": coin, "transaction_type": tx_type,
         "amount": float(amount), "price": float(price), "date": str(date)}
        for tid, coin, tx_type, amount, price, date in transactions
    ]
    with open(json_file, "w") as f:
        json.dump(data, f, indent=4)

    print(f"✅ Transactions exported: {csv_file}, {json_file}")

def menu():
    while True:
        print("\n=============================")
        print("   Crypto Portfolio Tracker")
        print("=============================")
        print("1. Update prices")
        print("2. Show all users")
        print("3. Show portfolio of a user")
        print("4. Show portfolios of all users")
        print("5. Add User")
        print("6. Add Transaction (BUY/SELL/SEND/RECEIVE)")
        print("7. Show all transactions of a user")
        print("8. Delete a transaction")
        print("9. Update a transaction")
        print("10. Top 5 richest users")
        print("11. Search user by username/email")
        print("12. Export all portfolios (JSON + CSV)")
        print("13. Export transactions of a user (CSV + JSON)")
        print("14. Exit")

        choice = input("👉 Choose an option: ")

        if choice == "1":
            prices = get_top10_prices()
            print("\n📈 Top 10 Crypto Prices (USD):")
            for coin, price in prices.items():
                print(f" - {coin}: ${price}")
            print("✅ Prices updated (not stored, snapshot only).")

        elif choice == "2":
            users = get_all_users()
            print("\n👥 Users:")
            for uid, username, email in users:
                print(f" - {uid}: {username} ({email})")

        elif choice == "3":
            user_id = int(input("Enter user ID: "))
            result = get_portfolio(user_id)
            print(f"\n📊 Portfolio for user {user_id}:")
            if result["total_value_usd"] == 0:
                print("⚠️ No active holdings")
            else:
                for coin, info in result.items():
                    if coin != "total_value_usd":
                        print(f" - {coin}: {info['amount']} units → ${info['value_usd']}")
                print(f"💰 Total Portfolio Value: ${result['total_value_usd']}")

        elif choice == "4":
            users = get_all_users()
            for uid, username, email in users:
                result = get_portfolio(uid)
                print(f"\n📊 Portfolio for {username} ({email}):")
                if result["total_value_usd"] == 0:
                    print("⚠️ No active holdings")
                else:
                    for coin, info in result.items():
                        if coin != "total_value_usd":
                            print(f" - {coin}: {info['amount']} units → ${info['value_usd']}")
                    print(f"💰 Total Portfolio Value: ${result['total_value_usd']}")

        elif choice == "5":
            add_user()

        elif choice == "6":
            add_transaction()

        elif choice == "7":
            show_user_transactions()

        elif choice == "8":
            delete_transaction()

        elif choice == "9":
            update_transaction()

        elif choice == "10":
            top5_users()

        elif choice == "11":
            search_user()

        elif choice == "12":
            export_all_users()
            print("✅ Export done → portfolios.csv & portfolios.json")

        elif choice == "13":
            export_user_transactions()

        elif choice == "14":
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice, try again.")

if __name__ == "__main__":
    menu()
