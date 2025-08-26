# api.py

import os
import requests
import psycopg2
from dotenv import load_dotenv

# Load API key and DB credentials
load_dotenv(dotenv_path=os.path.join("crypto_venv", ".env"))
API_KEY = os.getenv("COINGECKO_API_KEY")

def get_top10_prices():
    """
    Fetch top 10 cryptocurrencies by market cap (USD) from CoinGecko.
    Returns a dict like:
    {"BTC": 42000, "ETH": 2800, ...}
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    headers = {"x-cg-demo-api-key": API_KEY}
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1,
        "sparkline": "false"
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    prices = {}
    for coin in data:
        symbol = coin["symbol"].upper()
        prices[symbol] = coin["current_price"]

    return prices

def save_prices(prices):
    """
    Save the latest prices in the DB (replaces old snapshot).
    """
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    cur = conn.cursor()

    # Clear old snapshot
    cur.execute("TRUNCATE TABLE prices;")

    # Insert new snapshot
    for coin, price in prices.items():
        cur.execute(
            "INSERT INTO prices (coin, price) VALUES (%s, %s);",
            (coin, price)
        )

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    prices = get_top10_prices()
    save_prices(prices)  # save in DB
    print("📈 Top 10 crypto prices (USD):")
    for coin, price in prices.items():
        print(f"{coin}: ${price}")
    print("✅ Prices updated in DB")
