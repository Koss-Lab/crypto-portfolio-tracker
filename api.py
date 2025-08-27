# api.py

import os
import requests
import psycopg2
from dotenv import load_dotenv
from typing import Dict

# Load API key and DB credentials (compat with your current setup)
load_dotenv(dotenv_path=os.path.join("crypto_venv", ".env"))
if not os.getenv("DB_NAME"):
    # fallback: try a .env at repo root if present
    load_dotenv()

API_KEY = os.getenv("COINGECKO_API_KEY")

def _headers() -> Dict[str, str]:
    """Headers compatibles CoinGecko (demo/pro)."""
    if not API_KEY:
        return {}
    return {
        "x-cg-demo-api-key": API_KEY,   # demo/free
        "x-cg-pro-api-key": API_KEY,    # pro
        "X-CG-API-KEY": API_KEY,        # variantes
    }

def _connect():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )

# ---------------- Prices (déjà existant) ----------------

def get_top10_prices() -> Dict[str, float]:
    """
    Fetch top 10 cryptocurrencies by market cap (USD) from CoinGecko.
    Returns a dict like: {"BTC": 42000, "ETH": 2800, ...}
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1,
        "sparkline": "false",
    }
    response = requests.get(url, headers=_headers(), params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    prices = {}
    for coin in data:
        symbol = coin["symbol"].upper()
        prices[symbol] = float(coin["current_price"])
    return prices

def save_prices(prices: Dict[str, float]) -> None:
    """
    Save the latest prices in the DB (keeps same behavior as before).
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("TRUNCATE TABLE prices;")
    for coin, price in prices.items():
        cur.execute(
            "INSERT INTO prices (coin, price) VALUES (%s, %s);",
            (coin, price)
        )

    conn.commit()
    cur.close()
    conn.close()

# ---------------- FX rates (NOUVEAU) ----------------

def get_usd_fx_rates() -> Dict[str, float]:
    """
    Récupère les taux USD->EUR, USD->ILS depuis CoinGecko (simple/price).
    Pas d'appel ultérieur dans la GUI: on les lit ensuite via DB.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "usd", "vs_currencies": "eur,ils"}
    r = requests.get(url, headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    js = r.json() or {}
    # Exemple: {"usd": {"eur": 0.92, "ils": 3.7}}
    eur = float(js.get("usd", {}).get("eur", 0) or 0)
    ils = float(js.get("usd", {}).get("ils", 0) or 0)
    out = {}
    if eur > 0:
        out["EUR"] = eur
    if ils > 0:
        out["ILS"] = ils
    return out

def save_fx_rates(fx: Dict[str, float]) -> None:
    """
    Stocke les taux USD->XXX dans la table fx_rates.
    """
    if not fx:
        return
    conn = _connect()
    cur = conn.cursor()
    for curr, rate in fx.items():
        cur.execute(
            "INSERT INTO fx_rates (base_currency, currency, rate) VALUES ('USD', %s, %s);",
            (curr, rate)
        )
    conn.commit()
    cur.close()
    conn.close()

# -------- Wrapper (appelé par le GUI) --------
def update_prices() -> int:
    """
    Wrapper pour le GUI: met à jour les prix top10 ET les taux FX.
    Retourne le nombre de lignes de prix insérées (pour compat GUI).
    """
    prices = get_top10_prices()
    save_prices(prices)

    # on tente les FX, mais on n'échoue pas si ça rate (pas de casse GUI)
    try:
        fx = get_usd_fx_rates()
        save_fx_rates(fx)
    except Exception:
        pass

    return len(prices)

if __name__ == "__main__":
    prices = get_top10_prices()
    save_prices(prices)
    print("📈 Top 10 crypto prices (USD):")
    for coin, price in prices.items():
        print(f"{coin}: ${price}")

    try:
        fx = get_usd_fx_rates()
        save_fx_rates(fx)
        print("💱 FX rates (USD base) saved:", fx)
    except Exception as e:
        print("⚠️ FX fetch failed:", e)

    print("✅ DB updated")
