# export.py

import os
import json
import csv
import psycopg2
from dotenv import load_dotenv
from portfolio import get_portfolio  # use the updated portfolio logic with BUY/SELL/SEND/RECEIVE

# Load environment variables
load_dotenv(dotenv_path=os.path.join("crypto_venv", ".env"))

def connect_db():
    """Connect to PostgreSQL using environment variables."""
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def export_all_users():
    """
    Export all users' portfolios to JSON and CSV.
    Uses get_portfolio from portfolio.py to ensure correct calculation of BUY/SELL/SEND/RECEIVE.
    """
    conn = connect_db()
    cur = conn.cursor()

    # Get all users
    cur.execute("SELECT id, username, email FROM users;")
    users = cur.fetchall()

    all_data = []

    # Prepare CSV file
    with open("portfolios.csv", "w", newline="") as csvfile:
        fieldnames = ["user", "email", "coin", "amount", "value_usd", "total_value_usd"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Loop through users and get portfolios
        for user_id, username, email in users:
            portfolio = get_portfolio(user_id)

            # Save data for JSON
            entry = {
                "user": username,
                "email": email,
                "portfolio": {k: v for k, v in portfolio.items() if k != "total_value_usd"},
                "total_value_usd": portfolio["total_value_usd"]
            }
            all_data.append(entry)

            # Write portfolio to CSV
            if portfolio["total_value_usd"] > 0:
                for coin, info in portfolio.items():
                    if coin != "total_value_usd":
                        writer.writerow({
                            "user": username,
                            "email": email,
                            "coin": coin,
                            "amount": info["amount"],
                            "value_usd": info["value_usd"],
                            "total_value_usd": portfolio["total_value_usd"]
                        })
            else:
                # User with no holdings
                writer.writerow({
                    "user": username,
                    "email": email,
                    "coin": "",
                    "amount": 0,
                    "value_usd": 0,
                    "total_value_usd": 0
                })

    # Save all data to JSON file
    with open("portfolios.json", "w") as jsonfile:
        json.dump(all_data, jsonfile, indent=4)

    cur.close()
    conn.close()
    print("✅ Export done: portfolios.csv & portfolios.json")

if __name__ == "__main__":
    export_all_users()
