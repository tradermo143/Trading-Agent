"""
Trading Agent — Phase 1 daily runner.

Run this each evening after market close:
    python main.py

It will:
  1. Fetch the NYSE/NASDAQ universe
  2. Update the local OHLCV cache
  3. Run both scans
  4. Print every setup with entry, stop, R value, and position sizing
"""
import logging
import sys
from datetime import date
from pathlib import Path

from config import CONFIG
from data.universe import fetch_universe, fetch_exchange_map
from data.fetcher import update_cache
from screener.scanner import run_scans
from screener.indicators import compute_all
from analysis.contraction_detector import detect_contraction_zone
from analysis.position_sizer import compute_position, check_risk_gate
from broker.tradingview import TVWatchlistManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_DIVIDER = "─" * 62


def _save_watchlist_file(setup: list, contraction: list) -> Path:
    """
    Saves a combined watchlist text file with a section separator.
    Format is compatible with TradingView's manual 'Import list' feature.
    """
    today    = date.today().strftime('%Y-%m-%d')
    log_dir  = Path('logs')
    log_dir.mkdir(exist_ok=True)
    out_path = log_dir / f"watchlist_{today}.txt"

    lines = [
        f"### SETUP SCAN — {today}  ({len(setup)} tickers) ###",
        *setup,
        "",
        f"### CONTRACTION SCAN — {today}  ({len(contraction)} tickers) ###",
        *contraction,
    ]
    out_path.write_text('\n'.join(lines), encoding='utf-8')
    logger.info(f"Watchlist saved → {out_path}")
    return out_path


def _push_to_tradingview(setup: list, contraction: list):
    """Push today's scan results to TradingView as a named watchlist."""
    exchange_map = fetch_exchange_map(cache_dir=CONFIG.data.universe_cache_dir)
    tv = TVWatchlistManager()
    tv.push(setup, contraction, exchange_map)


def main():
    print(f"\n{'═' * 62}")
    print("  TRADING AGENT  —  Daily Scan  (Phase 1)")
    print(f"{'═' * 62}\n")

    # ── 1. Universe ───────────────────────────────────────────────────
    logger.info("Fetching universe…")
    tickers = fetch_universe(cache_dir=CONFIG.data.universe_cache_dir)
    logger.info(f"Universe: {len(tickers)} tickers\n")

    # ── 2. Data cache ─────────────────────────────────────────────────
    logger.info("Updating data cache (first run downloads ~400 days per ticker)…")
    data = update_cache(
        tickers,
        cache_dir=CONFIG.data.cache_dir,
        full_days=CONFIG.data.full_history_days,
    )
    logger.info(f"Data ready: {len(data)} tickers\n")

    # ── 3. Scans ──────────────────────────────────────────────────────
    logger.info("Running scans…")
    results = run_scans(data)
    print()

    # ── 4. Setup analysis ─────────────────────────────────────────────
    all_hits: dict = {}
    for t in results['scan1']:
        all_hits.setdefault(t, []).append('Setup')
    for t in results['scan2']:
        all_hits.setdefault(t, []).append('Contraction')

    setups = []
    for ticker, scan_types in all_hits.items():
        df_ind = compute_all(data[ticker])
        zone   = detect_contraction_zone(df_ind)
        if zone is None:
            continue
        sizing = compute_position(zone['entry_price'], zone['stop_price'])
        if sizing is None:
            continue
        can_trade, remaining = check_risk_gate(
            sizing['risk_dollars'],
            open_positions=[],   # Phase 3 will fill this from IBKR
        )
        setups.append({
            'ticker':     ticker,
            'scans':      scan_types,
            'zone':       zone,
            'sizing':     sizing,
            'can_trade':  can_trade,
            'remaining':  remaining,
        })

    # ── 5. Print results ──────────────────────────────────────────────
    if not setups:
        print("  No setups found today.\n")
        return

    print(f"{_DIVIDER}")
    print(f"  {len(setups)} SETUP(S) FOUND   "
          f"(account: ${CONFIG.risk.account_value:,.0f}  "
          f"risk/trade: {CONFIG.risk.risk_per_trade_pct*100:.1f}%)")
    print(f"{_DIVIDER}")

    for s in sorted(setups, key=lambda x: x['ticker']):
        t   = s['ticker']
        z   = s['zone']
        sz  = s['sizing']
        scn = ' + '.join(s['scans'])
        tgt = '  '.join(f"{k}=${v}" for k, v in sz['targets'].items())
        gate = "✓ OK" if s['can_trade'] else "✗ RISK GATE"

        print(f"\n  {t:<6}  [{scn}]  {gate}")
        print(f"  Zone: {z['zone_length']} bar(s)  "
              f"{z['zone_start_date'].strftime('%b %d')} – "
              f"{z['zone_end_date'].strftime('%b %d')}")
        print(f"  Entry : ${z['entry_price']:.2f}   "
              f"Stop : ${z['stop_price']:.2f}   "
              f"R : ${z['r_value']:.2f}/share")
        print(f"  Shares: {sz['shares']}   "
              f"Position: ${sz['position_value']:,.0f}   "
              f"Risk: ${sz['risk_dollars']:.0f} ({sz['risk_pct_actual']:.2f}%)")
        print(f"  Targets: {tgt}")

    print(f"\n{_DIVIDER}")
    print(f"  Open risk capacity remaining: ${setups[0]['remaining']:,.0f}")
    print(f"{_DIVIDER}\n")

    # ── 6. Save watchlist file ────────────────────────────────────────
    setup_tickers       = results['scan1']
    contraction_tickers = results['scan2']
    _save_watchlist_file(setup_tickers, contraction_tickers)

    # ── 7. Push to TradingView ────────────────────────────────────────
    _push_to_tradingview(setup_tickers, contraction_tickers)

    logger.info("Done. Run 'python ui/app.py' for the chart approval UI (Phase 2).")


if __name__ == "__main__":
    main()
