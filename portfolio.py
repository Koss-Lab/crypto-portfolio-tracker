# portfolio.py

import os
import psycopg2
from dotenv import load_dotenv
from api import get_top10_prices

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

def get_portfolio(user_id):
    """Calculate the portfolio of a user (with BUY/SELL/SEND/RECEIVE logic)."""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT coin, transaction_type, amount FROM transactions WHERE user_id = %s;",
        (user_id,)
    )
    transactions = cur.fetchall()
    cur.close()
    conn.close()

    # Initialize holdings
    holdings = {}

    # Apply transaction logic
    for coin, tx_type, amount in transactions:
        if coin not in holdings:
            holdings[coin] = 0

        if tx_type in ["BUY", "RECEIVE"]:
            holdings[coin] += float(amount)
        elif tx_type in ["SELL", "SEND"]:
            holdings[coin] -= float(amount)

    # Get live prices
    prices = get_top10_prices()

    # Calculate value
    portfolio = {"total_value_usd": 0}
    for coin, amount in holdings.items():
        if amount > 0:
            price = prices.get(coin, 0)
            value = round(amount * price, 2)
            portfolio[coin] = {"amount": round(amount, 4), "value_usd": value}
            portfolio["total_value_usd"] += value

    portfolio["total_value_usd"] = round(portfolio["total_value_usd"], 2)
    return portfolio

if __name__ == "__main__":
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
