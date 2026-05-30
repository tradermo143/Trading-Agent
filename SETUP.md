# Trading Agent — New Machine Setup

## What this system does
Scans NYSE/NASDAQ daily for momentum and volatility-contraction setups,
shows you interactive charts for approval, then places bracket orders
(buy-stop + stop-loss) on your IBKR paper/live account automatically.

---

## Requirements
- **Python 3.11+** — https://python.org (check "Add Python to PATH" on install)
- **Git** — https://git-scm.com
- **Trader Workstation (IBKR)** — logged into paper account, API enabled

---

## First-time setup on a new machine

### 1. Clone the repo
```
git clone https://github.com/YOUR_USERNAME/trading-agent.git
cd trading-agent
```

### 2. Install dependencies (double-click or run in terminal)
```
setup.bat
```

### 3. Create your `.env` file
Copy `.env.example` to `.env` and fill in your TradingView credentials:
```
TV_USERNAME=your_email@example.com
TV_PASSWORD=yourpassword
```
The `.env` file is **never committed** — you create it manually on each machine.

### 4. Set your account size
Open `config.py` and update:
```python
account_value: float = 100_000.0   # your actual account size
```

### 5. Enable IBKR API in Trader Workstation
`Edit → Global Configuration → API → Settings`
- ✅ Enable ActiveX and Socket Clients
- Socket port: `7497` (paper)
- ✅ Allow connections from localhost only

---

## Daily workflow

```
python main.py        # run the scanner + saves watchlist + pushes to TradingView
python ui/app.py      # opens the chart approval UI in your browser
```

**First run on a new machine** downloads ~800 days of price data for ~5,000 stocks.
This takes about 10 minutes and only happens once. After that, daily updates take ~30–60 seconds.

---

## Keeping code up to date across machines

On any machine, before running:
```
git pull
```
This pulls the latest version of the code from GitHub.

---

## Files that live only on your machine (not in git)
| File / Folder | What it is |
|---|---|
| `.env` | Your TradingView credentials — recreate manually on each machine |
| `data/cache/` | Downloaded price data — auto-rebuilds on first run (~10 min) |
| `logs/` | Daily watchlists, decisions, scan history |

> **Tip — avoid re-downloading on every new machine:**
> Copy the `data/cache/` folder from your main machine to the new one via USB or cloud storage.
> The system detects existing cache and skips the download.
