"""
Trading Agent — Phase 2 Approval UI
Run from the project root:  python ui/app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import threading
import webbrowser
from datetime import date
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request, Response
from functools import wraps

from config import CONFIG
from data.universe import fetch_universe
from data.fetcher import update_cache
from screener.scanner import run_scans
from screener.indicators import compute_all
from analysis.contraction_detector import detect_contraction_zone
from analysis.position_sizer import compute_position
from ui.charts import build_daily, build_weekly
from broker.ibkr import IBKRClient, TradeSetup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Optional password protection (set UI_PASSWORD in .env) ───────────────────
def _check_password(password: str) -> bool:
    ui_pw = os.getenv('UI_PASSWORD', '')
    return not ui_pw or password == ui_pw          # no password set = open

def _require_auth(f):
    """Wrap a route with HTTP Basic Auth when UI_PASSWORD is set in .env."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not os.getenv('UI_PASSWORD', ''):
            return f(*args, **kwargs)              # local mode — skip auth
        auth = request.authorization
        if not auth or not _check_password(auth.password):
            return Response(
                'Login required.',
                401,
                {'WWW-Authenticate': 'Basic realm="Trading Agent"'},
            )
        return f(*args, **kwargs)
    return decorated

# Apply auth to every route automatically
@app.before_request
def _global_auth():
    ui_pw = os.getenv('UI_PASSWORD', '')
    if not ui_pw:
        return                                     # no password set — allow all
    auth = request.authorization
    if not auth or not _check_password(auth.password):
        return Response(
            'Login required.',
            401,
            {'WWW-Authenticate': 'Basic realm="Trading Agent"'},
        )

# ── Session state (populated once on startup) ─────────────────────────────────
_setups    = []    # list of JSON-serialisable setup dicts
_dfs       = {}    # {ticker: enriched DataFrame} — not serialised
_decisions = {}    # {ticker: 'approve'|'skip'|'watchlist'}
_status    = {'ready': False, 'message': 'Starting up…', 'error': None}


def _load():
    """Run scans and populate _setups / _dfs. Runs in a background thread."""
    global _setups

    try:
        _status['message'] = 'Fetching universe…'
        logger.info("Fetching universe…")
        tickers = fetch_universe(cache_dir=CONFIG.data.universe_cache_dir)

        _status['message'] = 'Updating data cache…'
        logger.info("Updating data cache…")
        data = update_cache(tickers, CONFIG.data.cache_dir, CONFIG.data.full_history_days)

        _status['message'] = 'Running scans…'
        logger.info("Running scans…")
        results = run_scans(data)
    except Exception as e:
        _status['error'] = str(e)
        logger.error(f"Load failed: {e}")
        return

    hits: dict = {}
    for t in results['scan1']:
        hits.setdefault(t, []).append('Setup')
    for t in results['scan2']:
        hits.setdefault(t, []).append('Contraction')

    setups = []
    for ticker, scan_types in hits.items():
        df_ind = compute_all(data[ticker])
        zone   = detect_contraction_zone(df_ind)
        if not zone:
            continue
        sizing = compute_position(zone['entry_price'], zone['stop_price'])
        if not sizing:
            continue

        _dfs[ticker] = df_ind

        # Make zone dates JSON-safe
        zone_safe = {
            k: v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else v
            for k, v in zone.items()
        }

        setups.append({
            'ticker': ticker,
            'scans':  scan_types,
            'zone':   zone_safe,
            'sizing': sizing,
        })

    _setups = sorted(setups, key=lambda x: x['ticker'])
    _status['ready']   = True
    _status['message'] = f"{len(_setups)} setup(s) ready for review"
    logger.info(f"UI ready — {len(_setups)} setup(s) to review")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if not _status['ready']:
        return render_template('loading.html', status=_status)
    return render_template(
        'review.html',
        setups_json=json.dumps(_setups),
        total=len(_setups),
        account=f"${CONFIG.risk.account_value:,.0f}",
        risk_pct=f"{CONFIG.risk.risk_per_trade_pct * 100:.1f}%",
    )


@app.route('/api/status')
def api_status():
    return jsonify(_status)


@app.route('/api/chart/daily/<ticker>')
def api_daily(ticker):
    df    = _dfs.get(ticker)
    setup = next((s for s in _setups if s['ticker'] == ticker), None)
    if df is None or setup is None:
        return jsonify({'error': 'not found'}), 404
    return jsonify(build_daily(df, setup['zone'], CONFIG.ui.daily_bars))


@app.route('/api/chart/weekly/<ticker>')
def api_weekly(ticker):
    df = _dfs.get(ticker)
    if df is None:
        return jsonify({'error': 'not found'}), 404
    return jsonify(build_weekly(df, CONFIG.ui.weekly_bars))


def _persist_decisions() -> dict:
    """
    Write current decisions to logs/decisions_YYYY-MM-DD.json.
    Called after every decision so progress is never lost.
    """
    today   = date.today().strftime('%Y-%m-%d')
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    summary = {
        'date': today,
        'decisions': dict(_decisions),
        'approved': [
            {
                'ticker': s['ticker'],
                'entry':  s['zone']['entry_price'],
                'stop':   s['zone']['stop_price'],
                'r':      s['zone']['r_value'],
                'shares': s['sizing']['shares'],
            }
            for s in _setups if _decisions.get(s['ticker']) == 'approve'
        ],
        'watchlist': [t for t, d in _decisions.items() if d == 'watchlist'],
        'skipped':   [t for t, d in _decisions.items() if d == 'skip'],
    }
    (log_dir / f'decisions_{today}.json').write_text(
        json.dumps(summary, indent=2)
    )
    return summary


@app.route('/api/decide', methods=['POST'])
def api_decide():
    body     = request.get_json() or {}
    ticker   = body.get('ticker', '')
    decision = body.get('decision', '')
    if ticker and decision in ('approve', 'skip', 'watchlist'):
        _decisions[ticker] = decision
    elif ticker and decision == 'clear':
        _decisions.pop(ticker, None)

    _persist_decisions()   # auto-save after every change

    counts = {d: sum(1 for v in _decisions.values() if v == d)
              for d in ('approve', 'skip', 'watchlist')}
    return jsonify({'ok': True, **counts})


def _save_history() -> Path:
    """
    Append today's full scan results to logs/scan_history.csv.

    Every ticker that appeared in the UI is recorded — whether approved,
    watchlisted, skipped, or never reviewed.  Today's rows are replaced
    on each call so running the review twice doesn't create duplicates.
    """
    today        = date.today().strftime('%Y-%m-%d')
    log_dir      = Path('logs')
    history_path = log_dir / 'scan_history.csv'
    log_dir.mkdir(exist_ok=True)

    rows = []
    for s in _setups:
        ticker = s['ticker']
        rows.append({
            'date':           today,
            'ticker':         ticker,
            'scans':          ' + '.join(s['scans']),
            'decision':       _decisions.get(ticker, 'no_decision'),
            'entry_price':    s['zone']['entry_price'],
            'stop_price':     s['zone']['stop_price'],
            'r_value':        s['zone']['r_value'],
            'zone_bars':      s['zone']['zone_length'],
            'shares':         s['sizing']['shares'],
            'position_value': s['sizing']['position_value'],
            'risk_dollars':   s['sizing']['risk_dollars'],
        })

    today_df = pd.DataFrame(rows)

    if history_path.exists():
        existing = pd.read_csv(history_path, dtype=str)
        existing = existing[existing['date'] != today]   # drop today if re-running
        history  = pd.concat([existing, today_df], ignore_index=True)
    else:
        history = today_df

    history.to_csv(history_path, index=False)
    logger.info(
        f"History updated → {history_path}  "
        f"({len(today_df)} rows today, {len(history)} total)"
    )
    return history_path


@app.route('/api/finish', methods=['POST'])
def api_finish():
    """Called when the user clicks Finish Review. Saves decisions + history."""
    summary      = _persist_decisions()
    history_path = _save_history()

    logger.info(
        f"Review finished — "
        f"Approved: {len(summary['approved'])}  "
        f"Watchlist: {len(summary['watchlist'])}  "
        f"Skipped: {len(summary['skipped'])}"
    )

    summary['history_file'] = str(history_path)
    summary['total_shown']  = len(_setups)
    return jsonify(summary)


@app.route('/api/place_orders', methods=['POST'])
def api_place_orders():
    """
    Place bracket orders on IBKR for all approved tickers.
    Called after the user confirms the Finish Review summary.
    """
    approved = [s for s in _setups if _decisions.get(s['ticker']) == 'approve']

    if not approved:
        return jsonify({'ok': False, 'message': 'No approved tickers.'}), 400

    setups = [
        TradeSetup(
            ticker      = s['ticker'],
            entry_price = s['zone']['entry_price'],
            stop_price  = s['zone']['stop_price'],
            shares      = s['sizing']['shares'],
            r_value     = s['zone']['r_value'],
            scans       = s['scans'],
        )
        for s in approved
    ]

    client  = IBKRClient()
    results = client.place_all(setups)

    placed  = [r for r in results if r.status == 'submitted']
    failed  = [r for r in results if r.status == 'error']

    logger.info(f"Orders placed: {len(placed)}  failed: {len(failed)}")

    return jsonify({
        'ok':     True,
        'placed': [{'ticker': r.ticker, 'entry_order_id': r.entry_order_id,
                    'stop_order_id': r.stop_order_id, 'shares': r.shares,
                    'entry': r.entry_price, 'stop': r.stop_price}
                   for r in placed],
        'failed': [{'ticker': r.ticker, 'message': r.message}
                   for r in failed],
    })


@app.route('/api/approved')
def api_approved():
    approved = [
        {
            'ticker': s['ticker'],
            'entry':  s['zone']['entry_price'],
            'stop':   s['zone']['stop_price'],
            'r':      s['zone']['r_value'],
            'shares': s['sizing']['shares'],
        }
        for s in _setups
        if _decisions.get(s['ticker']) == 'approve'
    ]
    return jsonify(approved)


# ── Entry point ───────────────────────────────────────────────────────────────

def run():
    # Start scan in background — Flask comes up immediately
    threading.Thread(target=_load, daemon=True).start()

    def _open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://{CONFIG.ui.host}:{CONFIG.ui.port}")
    threading.Thread(target=_open_browser, daemon=True).start()

    print(f"\n  ┌─ Trading Agent — Approval UI ──────────────────────┐")
    print(f"  │  Open: http://{CONFIG.ui.host}:{CONFIG.ui.port}              │")
    print(f"  │  Scans running in background — loading page shown   │")
    print(f"  │  Press Ctrl+C to stop.                              │")
    print(f"  └────────────────────────────────────────────────────┘\n")

    app.run(host=CONFIG.ui.host, port=CONFIG.ui.port, debug=False, use_reloader=False)


if __name__ == '__main__':
    run()
