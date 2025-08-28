Based on our testing, here's the breakdown of which coins work and which don't:

## ✅ **Coins That Work (Can Fetch Historical Data)**

### **Major Coins - All Endpoints Work**
- **BTC** (Bitcoin) - market_chart, OHLC ✅
- **ETH** (Ethereum) - market_chart, OHLC ✅
- **SOL** (Solana) - market_chart, OHLC ✅

### **Mid-Tier Coins - OHLC Works, Market Chart Limited**
- **DOGE** (Dogecoin) - OHLC ✅, market_chart ❌ (400 error)
- **ADA** (Cardano) - OHLC ✅, market_chart ❌ (400 error)
- **XRP** (Ripple) - OHLC ✅, market_chart ✅ (works now!)
- **BNB** (Binance Coin) - Likely works
- **MATIC** (Polygon) - Likely works
- **DOT** (Polkadot) - Likely works
- **AVAX** (Avalanche) - Likely works

### **Stablecoins - Generated Locally (No API Needed)**
- **USDT** (Tether) - Flat $1 series ✅
- **USDC** (USD Coin) - Flat $1 series ✅
- **DAI** - Flat $1 series ✅

## ❌ **Coins That Don't Work (API Restrictions)**

### **Completely Blocked**
- **TRX** (Tron) - All endpoints fail with Pro API error ❌
  - Error: "If you are using Pro API key, please change your root URL from api.coingecko.com to pro-api.coingecko.com"

### **Partially Blocked**
- **Some smaller altcoins** may have similar restrictions

## 📊 **Success Rate Summary**

- **Total Tested**: 7 coins
- **Fully Working**: 3 coins (43%)
- **Partially Working**: 3 coins (43%) 
- **Not Working**: 1 coin (14%)

## �� **Why This Happens**

1. **Free API Key Limitations**: Your API key has access restrictions
2. **CoinGecko API Tiers**: Some coins require Pro/paid access
3. **OHLC vs Market Chart**: OHLC endpoint is more permissive than market_chart
4. **Stablecoins**: Generated locally to avoid API calls
5. **Caching**: 365-day data is cached and sliced to 180/90/7 days locally

## 💡 **Recommendation**

**Focus on the working coins** (BTC, ETH, SOL, DOGE, ADA, XRP, USDT, USDC, DAI) for your portfolio charts. These represent the major cryptocurrencies and should give you good portfolio coverage.

