"""
Fetches the list of all NYSE / NASDAQ common stocks.
Results are cached locally for 24 hours to avoid hammering NASDAQ's servers.
"""
import logging
import requests
import pandas as pd
from io import StringIO
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

_NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
_OTHER_URL  = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


def _is_valid_ticker(t: str) -> bool:
    t = t.strip()
    if not t or len(t) > 5:
        return False
    bad = {'.', '+', '$', '^', '~', '/', '\\', ' ', '-', '=', '@'}
    return not any(c in t for c in bad)


def fetch_universe(cache_dir: str = "data") -> list:
    """
    Returns sorted list of NYSE / NASDAQ common stock tickers.
    Reads from a local cache file if it is less than 24 hours old.
    """
    cache_path = Path(cache_dir) / "universe_cache.txt"

    if cache_path.exists():
        age_hours = (datetime.now().timestamp() - cache_path.stat().st_mtime) / 3600
        if age_hours < 24:
            tickers = [t for t in cache_path.read_text().strip().splitlines() if t]
            logger.info(f"Universe loaded from cache: {len(tickers)} tickers")
            return tickers

    tickers = set()

    # ── NASDAQ-listed stocks ────────────────────────────────────────────
    try:
        resp = requests.get(_NASDAQ_URL, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), sep='|')
        df = df[(df['Test Issue'] == 'N') & (df['ETF'] == 'N')]
        for sym in df['Symbol'].dropna().astype(str):
            if _is_valid_ticker(sym):
                tickers.add(sym.strip())
        logger.info(f"NASDAQ symbols: {len(tickers)}")
    except Exception as e:
        logger.error(f"NASDAQ fetch failed: {e}")

    n_before = len(tickers)

    # ── NYSE-listed stocks ──────────────────────────────────────────────
    try:
        resp = requests.get(_OTHER_URL, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), sep='|')
        nyse = df[(df['Test Issue'] == 'N') & (df['ETF'] == 'N') & (df['Exchange'] == 'N')]
        for sym in nyse['ACT Symbol'].dropna().astype(str):
            if _is_valid_ticker(sym):
                tickers.add(sym.strip())
        logger.info(f"NYSE symbols added: {len(tickers) - n_before}")
    except Exception as e:
        logger.error(f"NYSE fetch failed: {e}")

    result = sorted(tickers)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text('\n'.join(result))
    logger.info(f"Universe: {len(result)} tickers saved to cache")
    return result


def fetch_exchange_map(cache_dir: str = "data") -> dict:
    """
    Returns {ticker: 'NASDAQ'|'NYSE'} for all tickers in the universe.
    Rebuilds from source if the universe cache is stale (same 24h window).
    """
    import json
    map_path = Path(cache_dir) / "exchange_map.json"

    if map_path.exists():
        age_hours = (datetime.now().timestamp() - map_path.stat().st_mtime) / 3600
        if age_hours < 24:
            return json.loads(map_path.read_text())

    exchange_map: dict = {}

    try:
        resp = requests.get(_NASDAQ_URL, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), sep='|')
        df = df[(df['Test Issue'] == 'N') & (df['ETF'] == 'N')]
        for sym in df['Symbol'].dropna().astype(str):
            if _is_valid_ticker(sym):
                exchange_map[sym.strip()] = 'NASDAQ'
    except Exception as e:
        logger.error(f"Exchange map — NASDAQ fetch failed: {e}")

    try:
        resp = requests.get(_OTHER_URL, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), sep='|')
        nyse = df[(df['Test Issue'] == 'N') & (df['ETF'] == 'N') & (df['Exchange'] == 'N')]
        for sym in nyse['ACT Symbol'].dropna().astype(str):
            if _is_valid_ticker(sym):
                exchange_map.setdefault(sym.strip(), 'NYSE')
    except Exception as e:
        logger.error(f"Exchange map — NYSE fetch failed: {e}")

    map_path.write_text(json.dumps(exchange_map))
    logger.info(f"Exchange map saved: {len(exchange_map)} tickers")
    return exchange_map
