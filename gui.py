#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI for the Crypto Portfolio Tracker (Tkinter).

NEW:
- Export the displayed chart to PDF (button).
- “Alerts” tab: add/list/check price alerts (alerts table).
- “Portfolio Report (PDF)” export: text + holdings table + Pie + Line.
- Robust historical loader for ALL coins in CG_IDS (DOGE/ADA etc.), cache-first,
  multiple endpoints, segmented range fallback, and a “Smart Prewarm” button
  (downloads 365d once, derives 180/90d locally).

UNCHANGED:
- CLI and portfolio calculations remain intact.
- Existing CSV/JSON exports stay in USD.
- ***Currency converter removed: everything displays in USD.***
"""

from __future__ import annotations

import os
import sys
import json
import csv
import time
import random
import tempfile
import datetime as dt
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# ReportLab for PDF report
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Optional project modules
try:
    import api as api_module  # must expose update_prices()
except Exception:
    api_module = None

# ---------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------
HIST_DEBUG = True
CACHE_TTL_SECONDS = 6 * 3600      # 6h validity for cached historical series
THROTTLE_BETWEEN_COINS_SEC = 0.85 # gentle pacing between API calls
SESSION = requests.Session()

# =====================================================================
# DB helpers
# =====================================================================

def get_conn():
    load_dotenv()
    params = dict(
        dbname=os.getenv("DB_NAME", "crypto_portfolio"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
    )
    return psycopg2.connect(**params)

def fetch_all(query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()

def fetch_one(query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

def execute(query: str, params: Tuple = ()) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount

# =====================================================================
# Domain logic (portfolios & prices)
# =====================================================================

def list_users() -> List[Dict[str, Any]]:
    return fetch_all("SELECT id, username, email FROM users ORDER BY id ASC;")

def add_user(username: str, email: str) -> None:
    execute("INSERT INTO users (username, email) VALUES (%s, %s);", (username, email))

def search_users(keyword: str) -> List[Dict[str, Any]]:
    kw = f"%{keyword}%"
    return fetch_all(
        "SELECT id, username, email FROM users "
        "WHERE username ILIKE %s OR email ILIKE %s ORDER BY id ASC;",
        (kw, kw),
    )

def user_transactions(user_id: int) -> List[Dict[str, Any]]:
    return fetch_all(
        "SELECT id, coin, transaction_type, amount, price, date "
        "FROM transactions WHERE user_id = %s ORDER BY date ASC;",
        (user_id,),
    )

def add_transaction(user_id: int, coin: str, ttype: str,
                    amount: Decimal, price: Decimal,
                    date: Optional[dt.datetime] = None) -> None:
    if date is None:
        execute(
            "INSERT INTO transactions (user_id, coin, transaction_type, amount, price) "
            "VALUES (%s, %s, %s, %s, %s);",
            (user_id, coin.upper(), ttype.upper(), amount, price),
        )
    else:
        execute(
            "INSERT INTO transactions (user_id, coin, transaction_type, amount, price, date) "
            "VALUES (%s, %s, %s, %s, %s, %s);",
            (user_id, coin.upper(), ttype.upper(), amount, price, date),
        )

def delete_transaction(tx_id: int) -> None:
    execute("DELETE FROM transactions WHERE id = %s;", (tx_id,))

def update_transaction(tx_id: int, coin: str, ttype: str,
                       amount: Decimal, price: Decimal) -> None:
    execute(
        "UPDATE transactions SET coin=%s, transaction_type=%s, amount=%s, price=%s "
        "WHERE id=%s;", (coin.upper(), ttype.upper(), amount, price, tx_id)
    )

def update_prices_via_api() -> int:
    if api_module and hasattr(api_module, "update_prices"):
        return int(api_module.update_prices())
    raise RuntimeError("api.update_prices() not found. Please implement it in api.py")

def latest_prices() -> Dict[str, Decimal]:
    rows = fetch_all(
        "SELECT DISTINCT ON (coin) coin, price, date FROM prices ORDER BY coin, date DESC;"
    )
    return {r["coin"].upper(): Decimal(r["price"]) for r in rows}

def net_amounts_by_coin(user_id: int) -> Dict[str, Decimal]:
    txs = user_transactions(user_id)
    out: Dict[str, Decimal] = {}
    for t in txs:
        coin = t["coin"].upper()
        amt = Decimal(t["amount"])
        delta = amt if t["transaction_type"].upper() in ("BUY", "RECEIVE") else -amt
        out[coin] = out.get(coin, Decimal("0")) + delta
    return out

def user_portfolio(user_id: int) -> Dict[str, Any]:
    prices = latest_prices()
    net = net_amounts_by_coin(user_id)

    detail: Dict[str, Any] = {}
    total = Decimal("0")
    for coin, amt in net.items():
        if amt <= 0:
            continue
        p = prices.get(coin)
        if p is None:
            continue
        val = amt * p
        detail[coin] = {"amount": float(amt), "price_usd": float(p), "value_usd": float(val)}
        total += val
    return {"user_id": user_id, "holdings": detail, "total_value_usd": float(total)}

def top5_richest() -> List[Dict[str, Any]]:
    prices = latest_prices()
    users = list_users()
    out = []
    for u in users:
        net = net_amounts_by_coin(u["id"])
        total = Decimal("0")
        for c, a in net.items():
            if a <= 0:
                continue
            p = prices.get(c)
            if p is not None:
                total += a * p
        out.append({"user_id": u["id"], "username": u["username"], "total_value_usd": float(total)})
    out.sort(key=lambda r: r["total_value_usd"], reverse=True)
    return out[:5]

def portfolio_timeseries_approx(user_id: int) -> List[Tuple[dt.date, float]]:
    txs = user_transactions(user_id)
    if not txs:
        return []
    prices = latest_prices()
    cumulative: Dict[str, Decimal] = {}
    series: List[Tuple[dt.date, float]] = []
    prev_date: Optional[dt.date] = None
    for t in txs:
        d = t["date"].date()
        coin = t["coin"].upper()
        amt = Decimal(t["amount"])
        delta = amt if t["transaction_type"].upper() in ("BUY", "RECEIVE") else -amt
        cumulative[coin] = cumulative.get(coin, Decimal("0")) + delta
        if prev_date is None or d != prev_date:
            tot = Decimal("0")
            for c, a in cumulative.items():
                if a > 0 and c in prices:
                    tot += a * prices[c]
            series.append((d, float(tot)))
            prev_date = d
    return series

# =====================================================================
# Historical prices (robust, cache-first)
# =====================================================================

CG_IDS = {
    # L1 / majors
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "TRX": "tron",
    "DOT": "polkadot", "LTC": "litecoin", "ATOM": "cosmos", "NEAR": "near",
    "AVAX": "avalanche-2", "TON": "toncoin", "MATIC": "matic-network",
    "POL": "pol-ex-matic", "ETC": "ethereum-classic", "ICP": "internet-computer",
    "ALGO": "algorand", "EGLD": "multiversx", "KAS": "kaspa", "SEI": "sei-network",
    "TIA": "celestia", "STX": "stacks", "RON": "ronin", "AR": "arweave",
    "OP": "optimism", "ARB": "arbitrum", "APT": "aptos", "SUI": "sui",
    "KAVA": "kava", "FTM": "fantom", "HBAR": "hedera-hashgraph",
    # stables
    "USDT": "tether", "USDC": "usd-coin", "DAI": "dai", "FRAX": "frax",
    "TUSD": "true-usd", "USDD": "usdd",
    # wrapped / staking
    "WBTC": "wrapped-bitcoin", "WETH": "weth", "RPL": "rocket-pool", "LDO": "lido-dao",
    # DeFi / infra
    "AAVE": "aave", "UNI": "uniswap", "SNX": "synthetix-network-token",
    "COMP": "compound-governance-token", "GMX": "gmx", "DYDX": "dydx",
    "PENDLE": "pendle", "AERO": "aerodrome-finance", "ONDO": "ondo",
    "ETHFI": "ether-fi", "W": "wormhole",
    # Oracles / data
    "LINK": "chainlink", "PYTH": "pyth-network",
    # AI / compute
    "RNDR": "render", "GRT": "the-graph",
    # Storage
    "FIL": "filecoin",
    # L2 / ZK
    "STRK": "starknet", "ZK": "zksync",
    # Solana eco
    "JUP": "jupiter", "JTO": "jito", "RAY": "raydium", "BONK": "bonk", "WIF": "dogwifhat",
    # Memes
    "PEPE": "pepe", "SHIB": "shiba-inu", "FLOKI": "floki",
    # Exchange & governance / misc majors
    "INJ": "injective", "MKR": "maker", "RUNE": "thorchain", "LRC": "loopring",
    # Gaming
    "AXS": "axie-infinity", "SAND": "the-sandbox", "MANA": "decentraland", "IMX": "immutable",
    # Wallet/CEX & misc
    "TWT": "trust-wallet-token", "JASMY": "jasmycoin", "JOE": "joe",
    # Worldcoin / identity
    "WLD": "worldcoin",
    # BTC ordinals
    "ORDI": "ordi",
    # More majors
    "BCH": "bitcoin-cash", "XLM": "stellar", "XMR": "monero", "DASH": "dash", "ZEC": "zcash", "VET": "vechain",
    # Requested
    "VRA": "verasity",
}

STABLES = {"USDT", "USDC", "DAI", "FRAX", "TUSD", "USDD"}

CG_BASE = "https://api.coingecko.com/api/v3"
CG_CACHE_DIR = ".cg_cache"
os.makedirs(CG_CACHE_DIR, exist_ok=True)

def _cg_api_key() -> str:
    load_dotenv()
    return (os.getenv("COINGECKO_API_KEY") or os.getenv("COINGECKO_API") or "").strip()

def _headers() -> dict:
    # clé UNIQUEMENT en headers (jamais en query)
    key = _cg_api_key()
    h = {"Accept": "application/json", "User-Agent": "CryptoPortfolioTracker/1.0 (+gui)"}
    if key:
        for k in ("x-cg-pro-api-key", "x-cg-demo-api-key", "X-CG-API-KEY", "x_cg_demo_api_key"):
            h[k] = key
    return h

def _auth_query() -> dict:
    return {}  # never put the key in query-string

# ---- cache helpers ----
def _cache_path(cg_id: str, days: int) -> str:
    return os.path.join(CG_CACHE_DIR, f"{cg_id}_{days}.json")

def _cache_get(cg_id: str, days: int) -> Optional[List[List[float]]]:
    p = _cache_path(cg_id, days)
    if not os.path.exists(p):
        return None
    try:
        if time.time() - os.path.getmtime(p) > CACHE_TTL_SECONDS:
            return None
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("prices")
    except Exception:
        return None

def _cache_get_raw(cg_id: str, days: int) -> Optional[List[List[float]]]:
    """Read cached file even if older than TTL (handy to slice from 365 -> 180/90)."""
    p = _cache_path(cg_id, days)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("prices")
    except Exception:
        return None

def _ms(d: dt.date) -> int:
    return int(dt.datetime.combine(d, dt.time.min, tzinfo=dt.timezone.utc).timestamp() * 1000)

def _cache_set(cg_id: str, days: int, payload: List[List[float]]) -> None:
    try:
        with open(_cache_path(cg_id, days), "w", encoding="utf-8") as f:
            json.dump({"prices": payload, "cached_at": time.time()}, f)
    except Exception:
        pass

def _dedupe_by_day(prices_array: List[List[float]]) -> List[Tuple[dt.date, float]]:
    per: Dict[dt.date, float] = {}
    for ts_ms, price in prices_array:
        d = dt.date.fromtimestamp(ts_ms / 1000.0)
        per[d] = float(price)
    return sorted(per.items(), key=lambda x: x[0])

def _slice_last_days(series: List[Tuple[dt.date, float]], days: int):
    if not series:
        return []
    cutoff = series[-1][0] - dt.timedelta(days=days-1)
    return [(d, v) for (d, v) in series if d >= cutoff]

def _req(url: str, params: dict, tries: int = 4) -> dict:
    last = None
    hdrs = _headers()
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, headers=hdrs, timeout=25)
            if r.status_code in (429, 418):
                sleep = (1.6 ** i) + random.uniform(0.4, 0.9)
                if HIST_DEBUG:
                    print(f"[hist] 429 -> sleeping {sleep:.2f}s before retry")
                time.sleep(sleep); continue
            if 500 <= r.status_code < 600:
                time.sleep(0.5 + 0.3 * i); continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last = e
            time.sleep(0.35 + 0.25 * i + random.uniform(0.0, 0.25))
    if last:
        raise last
    raise RuntimeError("Unknown HTTP error")

def _fetch_range_segmented(cg_id: str, days: int) -> List[List[float]]:
    now = int(time.time())
    start = now - days * 86400
    window = 30 * 86400  # 30-day chunks
    acc: List[List[float]] = []
    cur = start
    while cur < now:
        end = min(cur + window, now)
        params = {"vs_currency": "usd", "from": cur, "to": end, **_auth_query()}
        data = _req(f"{CG_BASE}/coins/{cg_id}/market_chart/range", params)
        acc.extend(data.get("prices", []))
        cur = end
        time.sleep(random.uniform(0.15, 0.35))
    return acc

def fetch_daily_prices_with_reason(symbol: str, days: int) -> Tuple[List[Tuple[dt.date, float]], Optional[str]]:
    """
    Returns (series, reason) for SYMBOL over N days.
    Order: cache -> market_chart(daily) -> market_chart -> max(slice)
           -> ohlc(slice) -> range segmented. Stablecoins = flat $1 (no calls).
    """
    sym = symbol.upper()

    # Stablecoins: flat @ $1
    if sym in STABLES:
        today = dt.date.today()
        series = [(today - dt.timedelta(days=i), 1.0) for i in range(days-1, -1, -1)]
        if HIST_DEBUG: print(f"[hist] {sym} flat @ $1 (stable)")
        return series, None

    cg_id = CG_IDS.get(sym)
    if not cg_id:
        return [], f"{sym}: no mapping"

    # Cache (exact)
    cached = _cache_get(cg_id, days)
    if cached:
        if HIST_DEBUG: print(f"[hist] {sym} CACHE hit (exact {days}): {len(cached)} raw points")
        return _dedupe_by_day(cached), None

    # Cache (parent) slice
    for parent in (365, 180, 90):
        if parent > days:
            cpar = _cache_get(cg_id, parent)
            if cpar:
                series_parent = _dedupe_by_day(cpar)
                if len(series_parent) >= days:
                    if HIST_DEBUG: print(f"[hist] {sym} CACHE slice {parent}->{days}")
                    return series_parent[-days:], None

    reason = None

    # 1) market_chart (interval=daily)
    try:
        params = {"vs_currency": "usd", "days": int(days), "interval": "daily", **_auth_query()}
        data = _req(f"{CG_BASE}/coins/{cg_id}/market_chart", params)
        arr = data.get("prices", [])
        if arr:
            series = _dedupe_by_day(arr)
            if len(series) > days:
                series = series[-days:]
            payload = [[_ms(d), v] for d, v in series]
            _cache_set(cg_id, days, payload)
            if HIST_DEBUG: print(f"[hist] {sym} OK via standard+daily: {len(series)} pts")
            return series, None
    except Exception as e:
        reason = f"daily: {getattr(e, 'args', [str(e)])[0]}"

    # 2) market_chart (standard)
    try:
        params = {"vs_currency": "usd", "days": int(days), **_auth_query()}
        data = _req(f"{CG_BASE}/coins/{cg_id}/market_chart", params)
        arr = data.get("prices", [])
        if arr:
            series = _dedupe_by_day(arr)
            if len(series) > days:
                series = series[-days:]
            payload = [[_ms(d), v] for d, v in series]
            _cache_set(cg_id, days, payload)
            if HIST_DEBUG: print(f"[hist] {sym} OK via standard: {len(series)} pts")
            return series, None
    except Exception as e:
        reason = f"{reason or ''}; standard: {getattr(e, 'args', [str(e)])[0]}"

    # 3) days=max then slice
    try:
        params = {"vs_currency": "usd", "days": "max", "interval": "daily", **_auth_query()}
        data = _req(f"{CG_BASE}/coins/{cg_id}/market_chart", params)
        arr = data.get("prices", [])
        if arr:
            series_all = _dedupe_by_day(arr)
            series = series_all[-days:] if len(series_all) > days else series_all
            payload = [[_ms(d), v] for d, v in series]
            _cache_set(cg_id, days, payload)
            if HIST_DEBUG: print(f"[hist] {sym} OK via max->slice: {len(series)} pts")
            return series, None
    except Exception as e:
        reason = f"{reason or ''}; max: {getattr(e, 'args', [str(e)])[0]}"

    # 4) ohlc with nearest allowed period then slice
    try:
        allowed = [365, 180, 90, 30, 14, 7]
        d_used = next((d for d in allowed if d <= int(days)), 7)
        params = {"vs_currency": "usd", "days": d_used, **_auth_query()}
        arr = _req(f"{CG_BASE}/coins/{cg_id}/ohlc", params)
        if isinstance(arr, list) and arr:
            prices = [[row[0], row[4]] for row in arr]
            series = _slice_last_days(_dedupe_by_day(prices), days)
            payload = [[_ms(d), v] for d, v in series]
            _cache_set(cg_id, days, payload)
            if HIST_DEBUG: print(f"[hist] {sym} OK via ohlc({d_used})->slice: {len(series)} pts")
            return series, None
    except Exception as e:
        reason = f"{reason or ''}; ohlc: {getattr(e, 'args', [str(e)])[0]}"

    # 5) range segmented (30d windows)
    try:
        seg = _fetch_range_segmented(cg_id, int(days))
        if seg:
            series = _slice_last_days(_dedupe_by_day(seg), days)
            payload = [[_ms(d), v] for d, v in series]
            _cache_set(cg_id, days, payload)
            if HIST_DEBUG: print(f"[hist] {sym} OK via range(30d): {len(series)} pts")
            return series, None
    except Exception as e:
        reason = f"{reason or ''}; range: {getattr(e, 'args', [str(e)])[0]}"

    if HIST_DEBUG: print(f"[hist] OK coins: none")
    return [], (reason or "no data")

# =====================================================================
# Alerts (DB helpers)
# =====================================================================

def alerts_list() -> List[Dict[str, Any]]:
    return fetch_all(
        "SELECT id, user_id, coin, operator, threshold, active, created_at, triggered_at "
        "FROM alerts ORDER BY active DESC, created_at DESC;"
    )

def alerts_add(user_id: int, coin: str, operator: str, threshold: float) -> None:
    execute(
        "INSERT INTO alerts (user_id, coin, operator, threshold, active) VALUES (%s, %s, %s, %s, TRUE);",
        (user_id, coin.upper(), operator, threshold)
    )

def alerts_deactivate(alert_id: int) -> None:
    execute(
        "UPDATE alerts SET active=FALSE, triggered_at=NOW() WHERE id=%s;",
        (alert_id,)
    )

def alerts_check_now() -> List[str]:
    """
    Check active alerts vs latest prices in DB.
    Deactivate those that trigger.
    Returns a list of messages to show.
    """
    prices = latest_prices()
    rows = fetch_all("SELECT id, user_id, coin, operator, threshold FROM alerts WHERE active=TRUE;")
    messages = []
    for r in rows:
        coin = r["coin"].upper()
        price = float(prices.get(coin, 0))
        if price <= 0:
            continue
        op = r["operator"]
        th = float(r["threshold"])
        triggered = (price > th) if op == ">" else (price < th)
        if triggered:
            alerts_deactivate(int(r["id"]))
            messages.append(
                f"Alert #{r['id']} (U{r['user_id']} {coin} {op} {th}) TRIGGERED — current={price}"
            )
    return messages

# =====================================================================
# Tk application
# =====================================================================

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("💹 Crypto Portfolio Tracker — GUI")
        self.geometry("1280x760")
        self.minsize(1100, 660)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = ttk.Frame(self, padding=(10, 10))
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.rowconfigure(99, weight=1)

        self.content = ttk.Notebook(self)
        self.content.grid(row=0, column=1, sticky="nsew")

        self.tab_dashboard = ttk.Frame(self.content, padding=12)
        self.tab_users = ttk.Frame(self.content, padding=12)
        self.tab_transactions = ttk.Frame(self.content, padding=12)
        self.tab_charts = ttk.Frame(self.content, padding=12)
        self.tab_alerts = ttk.Frame(self.content, padding=12)
        self.content.add(self.tab_dashboard, text="Dashboard")
        self.content.add(self.tab_users, text="Users")
        self.content.add(self.tab_transactions, text="Transactions")
        self.content.add(self.tab_charts, text="Charts")
        self.content.add(self.tab_alerts, text="Alerts")

        # State (USD only now)
        self._last_figure: Optional[Figure] = None
        self._last_chart_title: str = ""

        # Build UI
        self._make_sidebar()
        self._build_dashboard()
        self._build_users_tab()
        self._build_transactions_tab()
        self._build_charts_tab()
        self._build_alerts_tab()

    def _make_sidebar(self) -> None:
        mkbtn = lambda txt, cmd: ttk.Button(self.sidebar, text=txt, command=cmd)
        ttk.Label(self.sidebar, text="Menu", font=("Arial", 14, "bold")).grid(sticky="w", pady=(0, 8))

        mkbtn("1) Update prices", self.action_update_prices).grid(sticky="ew", pady=2)
        mkbtn("2) Show all users", self.action_show_users).grid(sticky="ew", pady=2)
        mkbtn("3) Show portfolio (user)", self.action_show_portfolio_of_user).grid(sticky="ew", pady=2)
        mkbtn("4) Show portfolios (all users)", self.action_show_portfolios_all).grid(sticky="ew", pady=2)
        mkbtn("5) Add user", self.action_add_user).grid(sticky="ew", pady=2)
        mkbtn("6) Add transaction", self.action_add_tx).grid(sticky="ew", pady=2)
        mkbtn("7) Show transactions (user)", self.action_show_user_txs).grid(sticky="ew", pady=2)
        mkbtn("8) Delete a transaction", self.action_delete_tx).grid(sticky="ew", pady=2)
        mkbtn("9) Update a transaction", self.action_update_tx).grid(sticky="ew", pady=2)
        mkbtn("10) Top 5 richest", self.action_top5).grid(sticky="ew", pady=2)
        mkbtn("11) Search users", self.action_search_users).grid(sticky="ew", pady=2)
        mkbtn("12) Export all portfolios", self.action_export_all_portfolios).grid(sticky="ew", pady=2)
        mkbtn("13) Export user transactions", self.action_export_user_txs).grid(sticky="ew", pady=2)
        mkbtn("14) Exit", self.destroy).grid(sticky="ew", pady=2)

    # ---------------- Dashboard/Users/Txs ----------------

    def _build_dashboard(self) -> None:
        frame = self.tab_dashboard
        for w in frame.winfo_children(): w.destroy()

        ttk.Label(frame, text="Welcome to Crypto Portfolio Tracker GUI", font=("Arial", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Use the left menu to perform actions. Tabs above show data and charts.",
                  foreground="#555").pack(anchor="w", pady=(4, 12))

        try:
            users_count = fetch_one("SELECT COUNT(*) AS c FROM users;")["c"]
        except Exception:
            users_count = "?"
        try:
            tx_count = fetch_one("SELECT COUNT(*) AS c FROM transactions;")["c"]
        except Exception:
            tx_count = "?"
        try:
            price_rows = fetch_all("SELECT COUNT(*) AS c FROM (SELECT DISTINCT ON (coin) coin, date FROM prices) x;")
            coins_tracked = price_rows[0]["c"] if price_rows else 0
        except Exception:
            coins_tracked = "?"

        stats = ttk.Frame(frame); stats.pack(fill="x")
        for label, value in (("Users", users_count), ("Transactions", tx_count), ("Coins tracked", coins_tracked)):
            c = ttk.Frame(stats, borderwidth=1, relief="groove", padding=10)
            c.pack(side="left", padx=6, pady=6, expand=True, fill="x")
            ttk.Label(c, text=str(value), font=("Arial", 18, "bold")).pack()
            ttk.Label(c, text=label).pack()

    def _build_users_tab(self) -> None:
        frame = self.tab_users
        for w in frame.winfo_children(): w.destroy()

        toolbar = ttk.Frame(frame); toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Refresh", command=self.action_show_users).pack(side="left")
        ttk.Button(toolbar, text="Add user", command=self.action_add_user).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Search…", command=self.action_search_users).pack(side="left", padx=(6, 0))

        columns = ("id", "username", "email")
        self.users_table = ttk.Treeview(frame, columns=columns, show="headings", height=18)
        for c in columns:
            self.users_table.heading(c, text=c)
            self.users_table.column(c, width=220 if c != "id" else 80, anchor="center")
        self.users_table.pack(fill="both", expand=True, pady=6)
        self.action_show_users()

    def _build_transactions_tab(self) -> None:
        frame = self.tab_transactions
        for w in frame.winfo_children(): w.destroy()

        toolbar = ttk.Frame(frame); toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Add TX", command=self.action_add_tx).pack(side="left")
        ttk.Button(toolbar, text="Delete TX", command=self.action_delete_tx).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Update TX", command=self.action_update_tx).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Show TX (user)", command=self.action_show_user_txs).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Refresh All", command=self._load_all_txs).pack(side="left", padx=(6, 0))

        columns = ("id", "user_id", "coin", "transaction_type", "amount", "price", "date")
        self.txs_table = ttk.Treeview(frame, columns=columns, show="headings", height=18)
        for c in columns:
            self.txs_table.heading(c, text=c)
            w = 120
            if c in ("id", "user_id"): w = 80
            if c == "date": w = 180
            self.txs_table.column(c, width=w, anchor="center")
        self.txs_table.pack(fill="both", expand=True, pady=6)
        self._load_all_txs()

    def _load_all_txs(self) -> None:
        for i in self.txs_table.get_children(): self.txs_table.delete(i)
        rows = fetch_all(
            "SELECT id, user_id, coin, transaction_type, amount, price, date "
            "FROM transactions ORDER BY date DESC;")
        for r in rows:
            self.txs_table.insert("", "end", values=(
                r["id"], r["user_id"], r["coin"], r["transaction_type"], r["amount"], r["price"], r["date"]
            ))

    # ---------------- Charts ----------------

    def _build_charts_tab(self) -> None:
        frame = self.tab_charts
        for w in frame.winfo_children(): w.destroy()

        ctl = ttk.Frame(frame); ctl.pack(fill="x")
        ttk.Label(ctl, text="User ID:").pack(side="left")
        self.chart_user_id_var = tk.StringVar(value="")
        ttk.Entry(ctl, textvariable=self.chart_user_id_var, width=8).pack(side="left", padx=(4, 8))

        ttk.Label(ctl, text="Period (days):").pack(side="left", padx=(12, 0))
        self.period_var = tk.StringVar(value="365")
        ttk.Combobox(ctl, textvariable=self.period_var, values=["30", "90", "180", "365"],
                     width=6, state="readonly").pack(side="left", padx=(4, 8))

        ttk.Button(ctl, text="Draw Pie (Allocation)", command=self.draw_pie).pack(side="left")
        ttk.Button(ctl, text="Draw Line (Historical)", command=self.draw_line).pack(side="left", padx=(6, 0))
        ttk.Button(ctl, text="Export Chart (PDF)", command=self.export_current_chart_pdf).pack(side="left", padx=(12, 0))
        ttk.Button(ctl, text="Export Report (PDF)", command=self.action_export_pdf_report).pack(side="left", padx=(6, 0))
        ttk.Button(ctl, text="Smart Prewarm (365→180/90)", command=self.action_prewarm_cache_smart).pack(side="left", padx=(6, 0))

        self.chart_area = ttk.Frame(frame); self.chart_area.pack(fill="both", expand=True, pady=8)

    def _clear_chart_area(self) -> None:
        for w in self.chart_area.winfo_children(): w.destroy()
        self._last_figure = None
        self._last_chart_title = ""

    def draw_pie(self) -> None:
        uid = self._ask_user_id_from_entry(self.chart_user_id_var)
        if uid is None: return
        try:
            data = user_portfolio(uid)
            labels, sizes = [], []
            for coin, info in data["holdings"].items():
                v_usd = float(info.get("value_usd") or 0.0)
                if v_usd > 0:
                    labels.append(coin); sizes.append(v_usd)
            if not sizes:
                messagebox.showinfo("No data", "This user has no valued holdings."); return

            # Aggregate tiny slices into OTHER
            total = sum(sizes)
            new_labels, new_sizes, other = [], [], 0.0
            for lab, sz in zip(labels, sizes):
                if sz / total < 0.01: other += sz
                else: new_labels.append(lab); new_sizes.append(sz)
            if other > 0: new_labels.append("OTHER"); new_sizes.append(other)

            self._clear_chart_area()
            fig = Figure(figsize=(7.8, 4.8), dpi=100); ax = fig.add_subplot(111)
            wedges, texts, autotexts = ax.pie(new_sizes, labels=new_labels, autopct="%1.1f%%",
                                              startangle=120, wedgeprops={"linewidth": 1, "edgecolor": "white"})
            ax.axis("equal")
            ax.set_title(f"Portfolio Allocation (User {uid}) — USD")
            legend_labels = [f"{lab}: USD {sz:,.2f}" for lab, sz in zip(new_labels, new_sizes)]
            ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1.0, 0.5))
            canvas = FigureCanvasTkAgg(fig, master=self.chart_area); canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

            self._last_figure = fig
            self._last_chart_title = f"Portfolio_Allocation_User{uid}_USD"
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def draw_line(self) -> None:
        uid = self._ask_user_id_from_entry(self.chart_user_id_var)
        if uid is None: return
        try:
            net = net_amounts_by_coin(uid)
            amounts = {c: a for c, a in net.items() if a > 0}
            if not amounts:
                messagebox.showinfo("No data", "This user has no positive holdings."); return

            days = int(self.period_var.get() or "365")
            series_by_coin: Dict[str, List[Tuple[dt.date, float]]] = {}
            failures: List[str] = []
            for coin in amounts.keys():
                time.sleep(THROTTLE_BETWEEN_COINS_SEC)
                series, reason = fetch_daily_prices_with_reason(coin, days)
                if series:
                    series_by_coin[coin] = series
                else:
                    failures.append(reason or coin)

            if not series_by_coin:
                ts = portfolio_timeseries_approx(uid)
                if not ts:
                    messagebox.showwarning("No data", "Unable to build any time series for this user.")
                    return
                dates = [t[0] for t in ts]
                totals_usd = [t[1] for t in ts]
            else:
                all_dates = sorted({d for s in series_by_coin.values() for (d, _) in s})
                price_map: Dict[str, Dict[dt.date, float]] = {c: {d: p for d, p in s} for c, s in series_by_coin.items()}
                txs = user_transactions(uid)
                cum: Dict[str, Decimal] = {}
                cum_by_day: Dict[dt.date, Dict[str, Decimal]] = {}
                j = 0
                for d in all_dates:
                    while j < len(txs) and txs[j]["date"].date() <= d:
                        t = txs[j]
                        coin = t["coin"].upper()
                        amt = Decimal(str(t["amount"]))
                        delta = amt if t["transaction_type"].upper() in ("BUY", "RECEIVE") else -amt
                        cum[coin] = cum.get(coin, Decimal("0")) + delta
                        j += 1
                    snap = {c: (a if a > 0 else Decimal("0")) for c, a in cum.items()}
                    cum_by_day[d] = snap

                dates, totals_usd = [], []
                for d in all_dates:
                    total = Decimal("0")
                    snap = cum_by_day.get(d, {})
                    for c, a in snap.items():
                        p = price_map.get(c, {}).get(d)
                        if p is None or a <= 0:
                            continue
                        total += a * Decimal(str(p))
                    dates.append(d); totals_usd.append(float(total))

            self._clear_chart_area()
            fig = Figure(figsize=(8.6, 4.8), dpi=100); ax = fig.add_subplot(111)
            ax.plot(dates, totals_usd, marker="o")
            ax.set_title(f"Portfolio Value — User {uid} — last {days} days — USD")
            ax.set_xlabel("Date"); ax.set_ylabel("Value (USD)")
            ax.grid(True, linestyle="--", alpha=0.3); fig.autofmt_xdate()
            canvas = FigureCanvasTkAgg(fig, master=self.chart_area); canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

            self._last_figure = fig
            self._last_chart_title = f"Portfolio_Value_User{uid}_{days}d_USD"

            if failures:
                messagebox.showinfo("Partial data",
                                    "Some coins had no historical series and were skipped:\n- " +
                                    "\n- ".join(failures))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def export_current_chart_pdf(self) -> None:
        if not self._last_figure:
            messagebox.showinfo("No chart", "Draw a chart first (Pie or Line).")
            return
        path = filedialog.asksaveasfilename(
            title="Save chart as PDF",
            defaultextension=".pdf",
            initialfile=f"{self._last_chart_title or 'chart'}.pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path:
            return
        try:
            self._last_figure.savefig(path, format="pdf", bbox_inches="tight")
            messagebox.showinfo("Saved", f"Chart exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- Smart Prewarm ----------------

    def action_prewarm_cache_smart(self) -> None:
        """
        Smart prewarm:
          - downloads 365d (interval=daily) once per coin,
          - derives 180d/90d caches locally (slice),
          - optional env CG_PREWARM_COINS=BTC,ETH,SOL to limit,
          - stops early if rate-limit persists.
        """
        messagebox.showinfo(
            "Smart prewarm",
            "Caching historical series for mapped coins (365 days only).\n"
            "We will derive 180/90 day caches locally to minimize API calls.\n"
            "Tip: set CG_PREWARM_COINS=BTC,ETH,SOL,... to limit the batch."
        )

        env_list = os.getenv("CG_PREWARM_COINS", "").strip()
        if env_list:
            symbols = [s.strip().upper() for s in env_list.split(",") if s.strip()]
            symbols = [s for s in symbols if s in CG_IDS and s not in STABLES]
        else:
            symbols = [s for s in sorted(CG_IDS.keys()) if s not in STABLES]

        if not symbols:
            messagebox.showinfo("Smart prewarm", "No symbols to prewarm.")
            return

        ok, skipped = [], []
        consecutive_rate_limits = 0

        for sym in symbols:
            cg_id = CG_IDS[sym]
            try:
                # If 365 exists (even stale), slice locally
                raw365 = _cache_get_raw(cg_id, 365)
                if raw365:
                    series365 = _dedupe_by_day(raw365)
                    # derive 180/90
                    s180 = series365[-180:] if len(series365) > 180 else series365
                    s090 = series365[-90:]  if len(series365) > 90  else series365
                    _cache_set(cg_id, 180, [[_ms(d), v] for d, v in s180])
                    _cache_set(cg_id, 90,  [[_ms(d), v] for d, v in s090])
                    ok.append(sym + " (cache)")
                    consecutive_rate_limits = 0
                else:
                    # fetch fresh 365 (daily)
                    series, reason = fetch_daily_prices_with_reason(sym, 365)
                    if series:
                        _cache_set(cg_id, 365, [[_ms(d), v] for d, v in series])
                        s180 = series[-180:] if len(series) > 180 else series
                        s090 = series[-90:]  if len(series) > 90  else series
                        _cache_set(cg_id, 180, [[_ms(d), v] for d, v in s180])
                        _cache_set(cg_id, 90,  [[_ms(d), v] for d, v in s090])
                        ok.append(sym)
                        consecutive_rate_limits = 0
                    else:
                        skipped.append(f"{sym}: {reason}")
                        if reason and ("429" in str(reason) or "rate" in str(reason).lower()):
                            consecutive_rate_limits += 1
                        else:
                            consecutive_rate_limits = 0

                time.sleep(THROTTLE_BETWEEN_COINS_SEC + random.uniform(0.05, 0.25))

                if consecutive_rate_limits >= 5:
                    skipped.append("Stopped early due to persistent rate limit.")
                    break
            except Exception as e:
                skipped.append(f"{sym}: {e}")

        msg = []
        if ok:
            msg.append(f"✅ Cached: {', '.join(ok[:10])}" + ("…" if len(ok) > 10 else ""))
        if skipped:
            msg.append("⚠️ Skipped:\n- " + "\n- ".join(skipped[:10]) + ("…" if len(skipped) > 10 else ""))
        messagebox.showinfo("Smart prewarm — done", "\n".join(msg) or "Done.")

    # ---------------- Alerts tab ----------------

    def _build_alerts_tab(self) -> None:
        frame = self.tab_alerts
        for w in frame.winfo_children(): w.destroy()

        top = ttk.Frame(frame); top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="User ID:").pack(side="left")
        self.alert_uid_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.alert_uid_var, width=8).pack(side="left", padx=(4, 10))

        ttk.Label(top, text="Coin:").pack(side="left")
        self.alert_coin_var = tk.StringVar(value="BTC")
        ttk.Entry(top, textvariable=self.alert_coin_var, width=8).pack(side="left", padx=(4, 10))

        ttk.Label(top, text="Op:").pack(side="left")
        self.alert_op_var = tk.StringVar(value=">")
        ttk.Combobox(top, textvariable=self.alert_op_var, values=[">", "<"], width=3, state="readonly").pack(side="left", padx=(4, 10))

        ttk.Label(top, text="Threshold (USD):").pack(side="left")
        self.alert_th_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.alert_th_var, width=10).pack(side="left", padx=(4, 10))

        ttk.Button(top, text="Add Alert", command=self.action_add_alert).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="Check Alerts Now", command=self.action_check_alerts).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Refresh List", command=self._load_alerts_table).pack(side="left", padx=(6, 0))

        columns = ("id", "user_id", "coin", "operator", "threshold", "active", "created_at", "triggered_at")
        self.alerts_table = ttk.Treeview(frame, columns=columns, show="headings", height=16)
        for c in columns:
            self.alerts_table.heading(c, text=c)
            w = 120
            if c in ("id", "user_id"): w = 80
            if c in ("active",): w = 80
            self.alerts_table.column(c, width=w, anchor="center")
        self.alerts_table.pack(fill="both", expand=True, pady=6)
        self._load_alerts_table()

    def _load_alerts_table(self) -> None:
        for i in self.alerts_table.get_children(): self.alerts_table.delete(i)
        rows = alerts_list()
        for r in rows:
            self.alerts_table.insert("", "end", values=(
                r["id"], r["user_id"], r["coin"], r["operator"], r["threshold"],
                "YES" if r["active"] else "NO", r["created_at"], r.get("triggered_at")
            ))

    def action_add_alert(self) -> None:
        try:
            uid = int(self.alert_uid_var.get().strip())
        except Exception:
            messagebox.showerror("Missing", "Enter a valid User ID."); return
        coin = self.alert_coin_var.get().strip().upper()
        op = self.alert_op_var.get().strip()
        try:
            th = float(self.alert_th_var.get().strip())
        except Exception:
            messagebox.showerror("Missing", "Enter a numeric threshold in USD."); return
        try:
            alerts_add(uid, coin, op, th)
            messagebox.showinfo("OK", f"Alert added for U{uid}: {coin} {op} {th} USD.")
            self._load_alerts_table()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def action_check_alerts(self) -> None:
        try:
            msgs = alerts_check_now()
            if not msgs:
                messagebox.showinfo("Alerts", "No alerts triggered.")
            else:
                messagebox.showinfo("Alerts triggered", "\n".join(msgs))
            self._load_alerts_table()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- Actions ----------------

    def action_update_prices(self) -> None:
        try:
            rows = update_prices_via_api()
            messagebox.showinfo("Prices updated", f"Price rows inserted/updated: {rows}")
        except Exception as e:
            messagebox.showerror("Update failed",
                                 f"Could not update prices via api.py.\n{e}\n\n"
                                 "Tip: ensure api.update_prices() exists and .env has DB_* variables.")

    def action_show_users(self) -> None:
        try:
            rows = list_users()
            for i in self.users_table.get_children(): self.users_table.delete(i)
            for r in rows:
                self.users_table.insert("", "end", values=(r["id"], r["username"], r["email"]))
            self.content.select(self.tab_users)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def action_show_portfolio_of_user(self) -> None:
        uid = self._ask_user_id()
        if uid is None: return
        try:
            data = user_portfolio(uid)
            self._popup_json("User Portfolio (USD snapshot)", data)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def action_show_portfolios_all(self) -> None:
        try:
            results = [user_portfolio(u["id"]) for u in list_users()]
            self._popup_json("All Portfolios (USD snapshot)", results)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def action_add_user(self) -> None:
        def submit():
            username = ent_user.get().strip()
            email = ent_mail.get().strip()
            if not username or not email:
                messagebox.showwarning("Missing", "Username and email are required."); return
            try:
                add_user(username, email)
                messagebox.showinfo("OK", f"User '{username}' added.")
                top.destroy(); self.action_show_users()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        top = tk.Toplevel(self); top.title("Add User")
        ttk.Label(top, text="Username").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        ent_user = ttk.Entry(top, width=30); ent_user.grid(row=0, column=1, padx=6, pady=6)
        ttk.Label(top, text="Email").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        ent_mail = ttk.Entry(top, width=30); ent_mail.grid(row=1, column=1, padx=6, pady=6)
        ttk.Button(top, text="Add", command=submit).grid(row=2, column=0, columnspan=2, pady=10)

    def action_add_tx(self) -> None:
        def submit():
            try:
                uid = int(ent_uid.get()); coin = ent_coin.get().strip().upper()
                ttype = cb_type.get().strip().upper()
                amount = Decimal(ent_amount.get()); price = Decimal(ent_price.get())
                custom_date = ent_date.get().strip()
                if custom_date:
                    try:
                        dval = dt.datetime.fromisoformat(custom_date) if len(custom_date) > 10 \
                            else dt.datetime.fromisoformat(custom_date + " 00:00:00")
                    except Exception:
                        messagebox.showerror("Bad date", "Use ISO: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"); return
                    add_transaction(uid, coin, ttype, amount, price, dval)
                else:
                    add_transaction(uid, coin, ttype, amount, price)
                messagebox.showinfo("OK", "Transaction added.")
                top.destroy(); self._load_all_txs()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        top = tk.Toplevel(self); top.title("Add Transaction")
        labels = ["User ID", "Coin", "Type (BUY/SELL/SEND/RECEIVE)", "Amount", "Price (USD)", "Date (optional ISO)"]
        for i, lab in enumerate(labels):
            ttk.Label(top, text=lab).grid(row=i, column=0, sticky="e", padx=6, pady=6)
        ent_uid = ttk.Entry(top, width=12); ent_uid.grid(row=0, column=1, padx=6, pady=6)
        ent_coin = ttk.Entry(top, width=12); ent_coin.grid(row=1, column=1, padx=6, pady=6)
        cb_type = ttk.Combobox(top, values=["BUY", "SELL", "SEND", "RECEIVE"], state="readonly", width=12)
        cb_type.current(0); cb_type.grid(row=2, column=1, padx=6, pady=6)
        ent_amount = ttk.Entry(top, width=12); ent_amount.grid(row=3, column=1, padx=6, pady=6)
        ent_price = ttk.Entry(top, width=12); ent_price.grid(row=4, column=1, padx=6, pady=6)
        ent_date = ttk.Entry(top, width=18); ent_date.grid(row=5, column=1, padx=6, pady=6)
        ttk.Button(top, text="Add", command=submit).grid(row=6, column=0, columnspan=2, pady=10)

    def action_show_user_txs(self) -> None:
        uid = self._ask_user_id()
        if uid is None: return
        try:
            rows = user_transactions(uid)
            self.content.select(self.tab_transactions)
            for i in self.txs_table.get_children(): self.txs_table.delete(i)
            for r in rows:
                self.txs_table.insert("", "end", values=(
                    r["id"], uid, r["coin"], r["transaction_type"], r["amount"], r["price"], r["date"]
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def action_delete_tx(self) -> None:
        tx_id = self._ask_int("Transaction ID to delete")
        if tx_id is None: return
        try:
            delete_transaction(tx_id)
            messagebox.showinfo("OK", f"Transaction {tx_id} deleted."); self._load_all_txs()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def action_update_tx(self) -> None:
        tx_id = self._ask_int("Transaction ID to update")
        if tx_id is None:
            return
        row = fetch_one(
            "SELECT id, coin, transaction_type, amount, price FROM transactions WHERE id = %s;", (tx_id,)
        )
        if not row:
            messagebox.showwarning("Not found", f"Transaction {tx_id} does not exist.")
            return

        def submit():
            try:
                coin = ent_coin.get().strip().upper()
                ttype = cb_type.get().strip().upper()
                amount = Decimal(ent_amount.get())
                price = Decimal(ent_price.get())
                update_transaction(row["id"], coin, ttype, amount, price)
                messagebox.showinfo("OK", "Transaction updated."); top.destroy(); self._load_all_txs()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        top = tk.Toplevel(self); top.title(f"Update Transaction #{row['id']}")
        ttk.Label(top, text="Coin").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        ent_coin = ttk.Entry(top, width=14); ent_coin.insert(0, row["coin"]); ent_coin.grid(row=0, column=1, padx=6, pady=6)
        ttk.Label(top, text="Type").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        cb_type = ttk.Combobox(top, values=["BUY", "SELL", "SEND", "RECEIVE"], state="readonly", width=12)
        try: idx = ["BUY", "SELL", "SEND", "RECEIVE"].index(row["transaction_type"].upper())
        except Exception: idx = 0
        cb_type.current(idx); cb_type.grid(row=1, column=1, padx=6, pady=6)
        ttk.Label(top, text="Amount").grid(row=2, column=0, sticky="e", padx=6, pady=6)
        ent_amount = ttk.Entry(top, width=14); ent_amount.insert(0, str(row["amount"])); ent_amount.grid(row=2, column=1, padx=6, pady=6)
        ttk.Label(top, text="Price (USD)").grid(row=3, column=0, sticky="e", padx=6, pady=6)
        ent_price = ttk.Entry(top, width=14); ent_price.insert(0, str(row["price"])); ent_price.grid(row=3, column=1, padx=6, pady=6)
        ttk.Button(top, text="Save", command=submit).grid(row=4, column=0, columnspan=2, pady=10)

    def action_top5(self) -> None:
        try:
            rows = top5_richest()
            self._popup_table("Top 5 richest (USD)", ["user_id", "username", "total_value_usd"], rows)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def action_search_users(self) -> None:
        kw = simpledialog.askstring("Search", "Keyword (username or email):", parent=self)
        if not kw: return
        try:
            rows = search_users(kw)
            self.content.select(self.tab_users)
            for i in self.users_table.get_children(): self.users_table.delete(i)
            for r in rows:
                self.users_table.insert("", "end", values=(r["id"], r["username"], r["email"]))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def action_export_all_portfolios(self) -> None:
        try:
            users = list_users()
            data = [user_portfolio(u["id"]) for u in users]
            folder = filedialog.askdirectory(title="Choose export folder")
            if not folder: return

            json_path = os.path.join(folder, "portfolios.json")
            with open(json_path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)

            csv_path = os.path.join(folder, "portfolios.csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["user_id", "coin", "amount", "value_usd", "total_value_usd"])
                for item in data:
                    uid = item["user_id"]; total = item["total_value_usd"]
                    if not item["holdings"]:
                        w.writerow([uid, "", 0, 0, total])
                    else:
                        for coin, info in item["holdings"].items():
                            w.writerow([uid, coin, info["amount"], info["value_usd"], total])
            messagebox.showinfo("Export done", f"Saved:\n- {json_path}\n- {csv_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def action_export_user_txs(self) -> None:
        uid = self._ask_user_id()
        if uid is None: return
        try:
            rows = user_transactions(uid)
            folder = filedialog.askdirectory(title="Choose export folder")
            if not folder: return
            json_path = os.path.join(folder, f"user_{uid}_transactions.json")
            csv_path = os.path.join(folder, f"user_{uid}_transactions.csv")
            with open(json_path, "w", encoding="utf-8") as f: json.dump(rows, f, default=str, indent=2)
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(["id", "coin", "transaction_type", "amount", "price", "date"])
                for r in rows:
                    w.writerow([r["id"], r["coin"], r["transaction_type"], r["amount"], r["price"], r["date"]])
            messagebox.showinfo("Export done", f"Saved:\n- {json_path}\n- {csv_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- PDF Report (USD) ----------------

    def action_export_pdf_report(self) -> None:
        uid = self._ask_user_id_from_entry(self.chart_user_id_var)
        if uid is None: return
        try:
            days = int(self.period_var.get() or "365")

            # Data
            port = user_portfolio(uid)
            holdings = port.get("holdings", {})

            # Temporary chart images
            tmp_dir = tempfile.gettempdir()
            pie_png = os.path.join(tmp_dir, f"pie_user{uid}.png")
            line_png = os.path.join(tmp_dir, f"line_user{uid}_{days}d.png")

            # Pie
            if holdings:
                fig_pie = Figure(figsize=(6, 4), dpi=120); axp = fig_pie.add_subplot(111)
                labels, vals = [], []
                for c, info in holdings.items():
                    v = float(info["value_usd"])
                    if v > 0: labels.append(c); vals.append(v)
                if vals:
                    axp.pie(vals, labels=labels, autopct="%1.1f%%", startangle=120)
                    axp.axis("equal"); axp.set_title("Allocation — USD")
                    fig_pie.savefig(pie_png, bbox_inches="tight")

            # Line
            dates, totals_usd = [], []
            net = net_amounts_by_coin(uid)
            coins = {c: a for c, a in net.items() if a > 0}
            if coins:
                series_by_coin = {}
                for coin in coins:
                    time.sleep(0.2)
                    s, _ = fetch_daily_prices_with_reason(coin, days)
                    if s: series_by_coin[coin] = s
                if series_by_coin:
                    all_dates = sorted({d for s in series_by_coin.values() for (d, _) in s})
                    price_map = {c: {d: p for d, p in s} for c, s in series_by_coin.items()}
                    txs = user_transactions(uid)
                    cum: Dict[str, Decimal] = {}
                    cum_by_day: Dict[dt.date, Dict[str, Decimal]] = {}
                    j = 0
                    for d in all_dates:
                        while j < len(txs) and txs[j]["date"].date() <= d:
                            t = txs[j]
                            coin = t["coin"].upper()
                            amt = Decimal(str(t["amount"]))
                            delta = amt if t["transaction_type"].upper() in ("BUY", "RECEIVE") else -amt
                            cum[coin] = cum.get(coin, Decimal("0")) + delta
                            j += 1
                        snap = {c: (a if a > 0 else Decimal("0")) for c, a in cum.items()}
                        cum_by_day[d] = snap
                    for d in all_dates:
                        total = Decimal("0")
                        for c, a in cum_by_day.get(d, {}).items():
                            p = price_map.get(c, {}).get(d)
                            if p is not None and a > 0:
                                total += a * Decimal(str(p))
                        dates.append(d); totals_usd.append(float(total))
            if not dates:
                approx = portfolio_timeseries_approx(uid)
                if approx:
                    dates = [d for d, _ in approx]; totals_usd = [v for _, v in approx]

            if dates:
                fig_line = Figure(figsize=(7.5, 4), dpi=120); axl = fig_line.add_subplot(111)
                axl.plot(dates, totals_usd, marker="o")
                axl.set_title(f"Portfolio Value — last {days} days — USD")
                axl.set_xlabel("Date"); axl.set_ylabel("Value (USD)")
                axl.grid(True, linestyle="--", alpha=0.3); fig_line.autofmt_xdate()
                fig_line.savefig(line_png, bbox_inches="tight")

            # Compose PDF
            path = filedialog.asksaveasfilename(
                title="Save Portfolio Report (PDF)",
                defaultextension=".pdf",
                initialfile=f"Portfolio_Report_User{uid}.pdf",
                filetypes=[("PDF", "*.pdf")]
            )
            if not path:
                return

            styles = getSampleStyleSheet()
            story = []
            story.append(Paragraph(f"<b>Crypto Portfolio Report — User {uid}</b>", styles["Title"]))
            story.append(Spacer(1, 0.3 * cm))
            now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            story.append(Paragraph(f"Generated at: {now}", styles["Normal"]))
            story.append(Paragraph(f"Display currency: <b>USD</b>", styles["Normal"]))
            story.append(Spacer(1, 0.5 * cm))

            # Holdings table (USD)
            table_data = [["Coin", "Amount", "Value (USD)"]]
            total_usd = 0.0
            if holdings:
                for c, info in holdings.items():
                    amount = float(info["amount"])
                    v_usd = float(info["value_usd"])
                    total_usd += v_usd
                    table_data.append([c, f"{amount:.6f}", f"{v_usd:,.2f}"])
            table_data.append(["", "TOTAL", f"{total_usd:,.2f}"])
            tbl = Table(table_data, colWidths=[4*cm, 4*cm, 6*cm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
                ("ALIGN", (1,1), (-1,-1), "RIGHT"),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 0.6 * cm))

            # Images (if saved)
            if os.path.exists(pie_png):
                story.append(Paragraph("Allocation", styles["Heading2"]))
                story.append(Image(pie_png, width=15*cm, height=9*cm))
                story.append(Spacer(1, 0.6 * cm))
            if os.path.exists(line_png):
                story.append(Paragraph("Historical Value", styles["Heading2"]))
                story.append(Image(line_png, width=18*cm, height=9*cm))

            doc = SimpleDocTemplate(path, pagesize=A4)
            doc.build(story)

            messagebox.showinfo("Saved", f"PDF report exported:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # -------- utilities --------

    def _popup_json(self, title: str, data: Any) -> None:
        top = tk.Toplevel(self); top.title(title); top.geometry("740x520")
        txt = tk.Text(top, wrap="word"); txt.pack(fill="both", expand=True)
        txt.insert("1.0", json.dumps(data, indent=2, default=str)); txt.config(state="disabled")

    def _popup_table(self, title: str, columns: List[str], rows: List[Dict[str, Any]]) -> None:
        top = tk.Toplevel(self); top.title(title); top.geometry("640x400")
        table = ttk.Treeview(top, columns=columns, show="headings", height=12)
        for c in columns:
            table.heading(c, text=c); table.column(c, width=180 if c != "user_id" else 100, anchor="center")
        table.pack(fill="both", expand=True)
        for r in rows:
            table.insert("", "end", values=[r.get(c, "") for c in columns])

    def _ask_user_id(self) -> Optional[int]:
        val = simpledialog.askstring("User ID", "Enter user ID:", parent=self)
        if not val: return None
        try: return int(val)
        except Exception:
            messagebox.showerror("Bad ID", "Please enter a valid integer."); return None

    def _ask_int(self, prompt: str) -> Optional[int]:
        val = simpledialog.askstring("Input", prompt, parent=self)
        if not val: return None
        try: return int(val)
        except Exception:
            messagebox.showerror("Bad number", "Please enter a valid integer."); return None

    def _ask_user_id_from_entry(self, var: tk.StringVar) -> Optional[int]:
        val = var.get().strip()
        if not val: return self._ask_user_id()
        try: return int(val)
        except Exception:
            messagebox.showerror("Bad ID", "Please enter a valid integer."); return None

# =====================================================================
# Main
# =====================================================================

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
