# seed.py

import os
import psycopg2
from dotenv import load_dotenv
from faker import Faker
import random

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join("crypto_venv", ".env"))

# Connect to PostgreSQL using environment variables
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

fake = Faker()

# --- Generate fake users ---
def seed_users(n=5):
    """
    Insert n fake users into the users table.
    Each user will have a random username and email.
    Duplicate entries are ignored (ON CONFLICT DO NOTHING).
    """
    for _ in range(n):
        username = fake.user_name()
        email = fake.email()
        cur.execute(
            """
            INSERT INTO users (username, email)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (username, email)
        )

# --- Generate fake transactions ---
def seed_transactions(n=20):
    """
    Insert n fake transactions into the transactions table.
    Each transaction is linked to a random existing user and includes:
    - A cryptocurrency (BTC, ETH, SOL, ADA, XRP)
    - Transaction type (BUY or SELL)
    - Random amount between 0.01 and 5.0
    - Random price between 100 and 50,000
    """
    crypto_choices = ["BTC", "ETH", "SOL", "ADA", "XRP"]
    types = ["BUY", "SELL"]

    # Get all user IDs from the users table
    cur.execute("SELECT id FROM users;")
    user_ids = [row[0] for row in cur.fetchall()]

    for _ in range(n):
        user_id = random.choice(user_ids)
        coin = random.choice(crypto_choices)          # Match schema: column = coin
        transaction_type = random.choice(types)       # Match schema: column = transaction_type
        amount = round(random.uniform(0.01, 5.0), 4)  # Quantity of crypto
        price = round(random.uniform(100, 50000), 2)  # Price in USD

        cur.execute(
            """
            INSERT INTO transactions (user_id, coin, transaction_type, amount, price)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (user_id, coin, transaction_type, amount, price)
        )

if __name__ == "__main__":
    seed_users(5)
    seed_transactions(20)
    conn.commit()
    print("✅ Database seeded with fake data!")
    cur.close()
    conn.close()
