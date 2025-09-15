# 📁 Perfect Trader Files - What Each Does

## 🎮 **ESSENTIAL FILES (4 Main Files)**

| File | Purpose | When to Use |
|------|---------|-------------|
| **`download_historical_data.py`** | 📊 **One-time data setup** | First run only - downloads 105 stock data |
| **`quick_test.py`** | ⚡ **Quick signal check** | Fast 2-minute market scan |
| **`paper_trading.py`** | 🧪 **Virtual trading with ₹250K** | Main testing - trailing stops included |
| **`live_trading.py`** | 💰 **Real money trading** | After 60%+ win rate in paper trading |

## 📋 **PORTFOLIO & STATE FILES (Auto-generated)**

| File | Purpose | Contents |
|------|---------|----------|
| **`paper_trading_portfolio.json`** | 💾 **Position persistence** | Current holdings, capital, trade history |
| **`daily_portfolio_state.json`** | 📊 **Daily tracking** | End-of-day balances and performance |
| **`check_portfolio.py`** | 🔍 **Portfolio viewer** | Check positions without trading |

## ⚙️ **CONFIGURATION FILES**

| File | Purpose | Key Settings |
|------|---------|--------------|
| **`hybrid_config.json`** | 🎯 **Trading parameters** | ₹250K capital, trailing stops, 105 stocks |
| **`zerodha_config.json`** | 🔑 **API credentials** | Your Zerodha login details |
| **`requirements.txt`** | 📦 **Dependencies** | Python packages needed |

## 🧠 **CORE ENGINE FILES (Auto-managed)**

| File | Purpose | Function |
|------|---------|----------|
| `mtfa_strategy.py` | 📈 **Multi-timeframe analysis** | Daily/60min/15min signals |
| `hybrid_trading_orchestrator.py` | 🤖 **Live trading engine** | Real money execution with trailing stops |
| `zerodha_loader.py` | 📡 **Data source** | Real-time Zerodha data only |
| `data_cache_manager.py` | 💾 **Smart caching** | Efficient data management |

## 📁 **ARCHIVE FOLDER**

| File | Status | Notes |
|------|---------|-------|
| `archive/` | 🗄️ **Old/backup files** | Moved unused files here for cleanup |

## 🚀 **Quick Start Sequence**

```bash
# 1. One-time setup (15-20 minutes)
python download_historical_data.py

# 2. Quick market check (2 minutes)
python quick_test.py

# 3. Full paper trading (4+ hours)
python paper_trading.py
```

**New Features:**
- ✅ **₹250,000 virtual capital** (increased from ₹100K)
- ✅ **Trailing stop loss** (2% trail after 1.5% profit)
- ✅ **Position persistence** (resume positions across sessions)
- ✅ **105 stock coverage** (complete NSE universe)
- ✅ **Zerodha-only data** (removed Yahoo Finance dependency)