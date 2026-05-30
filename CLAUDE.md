# Trading Agent — Project Intelligence

This file gives Claude complete context to continue development on any machine,
in any session, without re-explaining anything.

---

## What This Is

A fully automated trading agent for US stocks (NYSE/NASDAQ) that:
1. Scans ~5,000 stocks nightly using two custom strategies
2. Shows interactive charts in a browser for human approval
3. Places bracket orders (buy-stop + stop-loss) on IBKR paper/live account
4. Pushes results to a TradingView watchlist automatically
5. Maintains a historical log of all decisions for analysis

Built by systematising the owner's existing discretionary trading workflow.
Previously done manually with MarketInOut.com + TradingView + IBKR.

**GitHub:** https://github.com/tradermo143/Trading-Agent
**Stack:** Python 3.14, Flask, Plotly, yfinance, ib_insync, pandas 3.x, pyarrow

---

## The Two Scans

Both run on **daily bars** after market close.

### Scan 1 — Daily Setup (momentum breakout)

Stocks in a sustained uptrend that had a strong day.
Two OR conditions — A (large cap, advol > 10M) and B (mid/small cap, advol > 3M):

```
Condition A:
  exch(nyse,nasdaq) AND natr(50) > 3
  AND advol(20) > 10 AND advol(50) > 10
  AND NOT (sma(20) < sma(50)) in last 21 bars        ← @{0..20}
  AND NOT (price < sma(50) AND sma(50) trend_dn 20)
  AND price > sma(20) AND sma(10) > sma(20)
  AND price > close[1]                               ← up day
  AND atr(1) > atr(20) * 0.6                        ← decent range
  AND price > low + (high - low) * 0.4               ← strong close

Condition B (same but):
  advol(20) > 3  (lower volume threshold)
  type(stock)
  NOT sma(20) trend_dn 20  (instead of the @{0..20} check)
  price > sma(10)  (added)
```

### Scan 2 — Daily Contraction (VCP — Volatility Contraction Pattern)

Stocks in long-term uptrend that are coiling — range contracting before a breakout:

```
  exch(nyse,nasdaq) AND type(stock) AND advol(30) > 3
  AND NOT (sma(20) < sma(50)) in last 21 bars
  AND NOT (price < sma(50) AND sma(50) trend_dn 20)
  AND (price > sma(100) OR price > sma(200))
  AND sma(200) trend_up 60
  AND natr(50) > 1.5
  AND price > sma(50) - arange(0)                    ← not too far below SMA50
  AND (
    atr(1) < atr(5)*0.5 OR atr(1) < atr(20)*0.5 OR atr(1) < atr(50)*0.5
    OR
    (inside_day AND (atr(1) < atr(5)*0.75 OR atr(1) < atr(20)*0.75 OR atr(1) < atr(50)*0.75))
  )
  AND (pgo(50) < 2.5 OR pgo(20) < 2.5)             ← not extended from SMA
  AND rsi(7) < 60  one bar ago                       ← @1
```

### Confirmed Indicator Definitions

| Function | Definition | Confirmed |
|---|---|---|
| `atr(1)` | Single-day True Range (no averaging) | ✅ |
| `atr(n>1)` | Simple n-period rolling mean of TR | ✅ |
| `arange(0)` | Same as `atr(1)` — today's True Range | ✅ |
| `natr(n)` | `atr(n) / close * 100` | ✅ |
| `advol(n)` | Average daily volume in millions | ✅ |
| `pgo(n)` | `(close - sma(n)) / atr(n)` | ✅ |
| `@{0..20}` | Condition true at any of last 21 bars | ✅ |
| `@1` | Condition true 1 bar ago | ✅ |
| `trend_dn n` | `current < value_n_bars_ago` | ✅ |

---

## Entry & Exit Rules

### Entry
- **Buy-stop** at `max(contraction_zone_highs) + $0.05`
- Contraction zone = consecutive bars where `ATR(1) < ATR(20) × 0.75`, max 15 bars lookback
- 1–2 bar contraction → use that bar's high
- 3–5+ bars → use high of entire consolidated range

### Initial Stop Loss
- **Stop** at `min(contraction_zone_lows) - $0.05`
- If hit → **100% exit**, no partial

### Profit Exit Rules (all configurable in config.py)
- **Day 5** from entry: exit `time_exit_fraction` (default 33%) of remaining position
  - Move stop to entry price (breakeven)
- **R-multiple ladder** (R = entry − stop per share):
  - At 1R gain: exit 25% of remaining
  - At 2R gain: exit 25% of remaining
  - At 3R gain: exit 25% of remaining
  - Remainder runs with trailing stop (to be defined in Phase 5)

### Position Sizing
```
risk_dollars  = account_value × risk_per_trade_pct   (default 0.5%)
R_per_share   = entry_price − stop_price
shares        = floor(risk_dollars / R_per_share)
```

### Open Risk Gate
```
total_open_risk = sum of (entry_i − stop_i) × shares_i  for all open positions
if total_open_risk >= max_open_risk_pct × account_value → block new trades
```
Both `risk_per_trade_pct` and `max_open_risk_pct` are configurable.

---

## Project Structure

```
D:\AI\Trading\
├── CLAUDE.md                    ← this file
├── config.py                    ← ALL configurable parameters
├── main.py                      ← daily scanner CLI runner
├── requirements.txt
├── setup.bat                    ← new machine setup (installs dependencies)
├── start.bat                    ← one-click launcher (app + ngrok tunnel)
├── .env                         ← credentials (never committed)
├── .env.example                 ← template for .env
│
├── data/
│   ├── universe.py              ← fetch NYSE/NASDAQ ticker list (cached 24h)
│   ├── fetcher.py               ← yfinance downloader (smart incremental cache)
│   └── cache.py                 ← per-ticker parquet file cache
│
├── screener/
│   ├── indicators.py            ← SMA, ATR, NATR, RSI, ADVOL, PGO — all from scratch
│   ├── conditions.py            ← @{0..n}, @n, trend_dn/up operators
│   ├── scan1_setup.py           ← Daily Setup scan (conditions A and B)
│   ├── scan2_contraction.py     ← Daily Contraction scan (VCP)
│   └── scanner.py               ← runs both scans, deduplicates
│
├── analysis/
│   ├── contraction_detector.py  ← detect zone, compute entry/stop prices
│   └── position_sizer.py        ← position size calculation + risk gate check
│
├── broker/
│   ├── ibkr.py                  ← IBKR connection + bracket order placement
│   └── tradingview.py           ← push watchlist to TradingView via session API
│
├── ui/
│   ├── app.py                   ← Flask server (all routes)
│   ├── charts.py                ← Plotly chart builders (daily + weekly)
│   └── templates/
│       ├── review.html          ← main approval UI (carousel, charts, buttons)
│       └── loading.html         ← shown while scans run in background
│
└── logs/                        ← created at runtime, not committed
    ├── watchlist_YYYY-MM-DD.txt ← daily ticker list with section headers
    ├── decisions_YYYY-MM-DD.json← per-session decisions
    └── scan_history.csv         ← cumulative history of all scan results + decisions
```

---

## Key Configuration (config.py)

```python
account_value        = 100_000.0   # USD — update to real account size
risk_per_trade_pct   = 0.005       # 0.5% per trade
max_open_risk_pct    = 0.05        # 5% total open risk cap
entry_buffer         = 0.05        # $0.05 above zone high
stop_buffer          = 0.05        # $0.05 below zone low
time_exit_days       = 5           # day 5 partial exit
time_exit_fraction   = 0.33        # sell 33% on day 5
r_exit_levels        = [(1.0, 0.25), (2.0, 0.25), (3.0, 0.25)]  # R-ladder
full_history_days    = 800         # ~3.2 years of daily data
daily_bars           = 150         # bars shown on daily chart
weekly_bars          = 150         # bars shown on weekly chart
ibkr.port            = 7497        # TWS paper=7497, live=7496, Gateway paper=4002
ibkr.paper           = True        # MUST be False to place live orders
```

---

## Credentials (.env file — never committed)

```
TV_USERNAME=tradingview_email
TV_PASSWORD=tradingview_password
UI_PASSWORD=web_ui_password_for_ngrok_access
```

---

## Build Phase Status

| Phase | Status | Description |
|---|---|---|
| 1 — Screening | ✅ Done | NYSE/NASDAQ scan, contraction detector, position sizer |
| 2 — Approval UI | ✅ Done | Flask/Plotly charts, daily+weekly, approve/skip/watchlist |
| 3 — IBKR Orders | ✅ Done | Bracket orders (buy-stop + stop-loss), paper trading |
| 4 — Trade Monitor | ⏳ Next | Intraday watcher, auto-exit on stop hit |
| 5 — Profit Exits | ⏳ Pending | Day-5 partial, R-ladder, breakeven stop management |

---

## Daily Workflow

```
1. After market close → python main.py
   - Scans NYSE/NASDAQ (~5,000 stocks)
   - Saves logs/watchlist_YYYY-MM-DD.txt
   - Pushes "US Watchlist YYYY-MM-DD" to TradingView automatically

2. Review session → python ui/app.py  (or double-click start.bat for ngrok)
   - Browser opens automatically at http://127.0.0.1:5000
   - Review each ticker: daily chart + weekly chart side by side
   - SMA 20/50/200 overlaid on both charts
   - Contraction zone highlighted, entry/stop lines annotated
   - Keys: A=approve  S=skip  W=watchlist  ←→=navigate

3. Click "Finish Review"
   - Summary popup: approved / watchlist / skipped
   - Confirm → bracket orders placed on IBKR paper account
   - Appends to logs/scan_history.csv (cumulative history)
```

---

## Remote Access (ngrok setup)

- **`start.bat`** launches both the app and an ngrok tunnel
- ngrok path: `C:\Users\Sheddy\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe`
- ngrok version: 3.39.5 (updated from 3.3.1 which was too old)
- Free tier URL changes on each restart
- App is password-protected when accessed via ngrok (UI_PASSWORD in .env)
- From any browser anywhere: open ngrok URL → leave username blank → enter UI_PASSWORD

---

## Important Technical Notes

1. **Python 3.14 asyncio issue**: `ib_insync` requires an event loop at import time.
   Fixed in `broker/ibkr.py` with `asyncio.set_event_loop(asyncio.new_event_loop())` before the import.

2. **yfinance 1.4+ multi-ticker**: Returns MultiIndex columns `(Price, Ticker)`.
   Use `df.xs(ticker, axis=1, level=1)` to extract per-ticker data.

3. **pandas 3.x**: Copy-on-Write is default. Always use `.copy()` before modifying.
   `indicators.py` `compute_all()` does `df = df.copy()` for this reason.

4. **Chart x-axis**: Set to `type='category'` to eliminate weekend/holiday gaps.

5. **Flask startup**: `_load()` runs in a background thread so Flask starts immediately
   (port 5000 is available within ~2 seconds). Loading page polls `/api/status`
   and redirects automatically when scans complete (~30 seconds).

6. **Data cache first run**: ~10 minutes to download 800 days × 5,000 tickers.
   Subsequent daily updates: ~30–60 seconds.
   Cache auto-extends if `full_history_days` increased (detects <60% of target).

7. **TradingView push**: Uses undocumented internal session API. If it breaks,
   the rest of the system continues working. Fix by updating endpoints in `broker/tradingview.py`.

---

## What to Build Next (Phase 4 — Trade Monitor)

The intraday monitor should:
- Connect to IBKR and watch all open positions during market hours
- Track current P&L and price vs stop for each position
- Automatically execute exit if stop is hit (IBKR order already placed, but monitor confirms)
- On Day 5 from entry: alert user to take partial profit, move stop to breakeven
- Track R-multiple levels reached and trigger partial exits per the ladder
- Log all exits to scan_history.csv with outcome data

File to create: `monitor/monitor.py`
File to create: `monitor/exits.py`
Should be startable alongside the UI: `python monitor/monitor.py`

---

## Potential Future Improvements

- Replit deployment (for access without home machine running)
- IBKR Web REST API integration (cloud order placement without local TWS)
- Performance analytics on scan_history.csv (win rate by scan type, R achieved, etc.)
- Email/WhatsApp notification of ngrok URL on startup
- Backtesting module using historical scan results
- Refinement of scan criteria based on historical performance data
