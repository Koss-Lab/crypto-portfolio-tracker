# seed.py

import os
import psycopg2
from dotenv import load_dotenv
from faker import Faker
import random
from api import get_top10_prices  # on récupère des prix réalistes
from datetime import datetime, timedelta

# Load environment variables
load_dotenv(dotenv_path=os.path.join("crypto_venv", ".env"))

# Connect to DB
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

fake = Faker()

def seed_users(n=50):
    for _ in range(n):
        username = fake.user_name()
        email = fake.email()
        cur.execute(
            "INSERT INTO users (username, email) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (username, email)
        )

def seed_transactions(n=500):
    crypto_choices = ["BTC", "ETH", "SOL", "ADA", "XRP", "BNB", "USDT", "USDC", "DOGE", "TRX"]
    tx_types = ["BUY", "SELL", "SEND", "RECEIVE"]

    # Get latest prices from API
    prices = get_top10_prices()

    # Get all user IDs
    cur.execute("SELECT id FROM users;")
    user_ids = [row[0] for row in cur.fetchall()]

    for _ in range(n):
        user_id = random.choice(user_ids)
        coin = random.choice(crypto_choices)
        tx_type = random.choice(tx_types)
        amount = round(random.uniform(0.01, 5.0), 4)

        # Fake date within last 6 months
        days_back = random.randint(0, 180)
        tx_date = datetime.now() - timedelta(days=days_back)

        # Price logic
        if tx_type in ["BUY", "SELL"]:
            price = round(random.uniform(100, 50000), 2)  # simulation
        else:  # SEND/RECEIVE use market price
            price = prices.get(coin, random.uniform(100, 50000))

        cur.execute(
            """
            INSERT INTO transactions (user_id, coin, transaction_type, amount, price, date)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (user_id, coin, tx_type, amount, price, tx_date)
        )

if __name__ == "__main__":
    seed_users(50)
    seed_transactions(500)
    conn.commit()
    print("✅ Database seeded with users + transactions (BUY/SELL/SEND/RECEIVE)")
    cur.close()
    conn.close()
