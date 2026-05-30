"""
Downloads daily OHLCV data via yfinance and keeps the local cache current.
"""
import logging
import pandas as pd
import yfinance as yf
from data.cache import DataCache

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


def _normalize(df: pd.DataFrame) -> pd.DataFrame | None:
    """Lowercase columns, validate required fields, strip timezone."""
    if df is None or df.empty:
        return None
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    required = {'open', 'high', 'low', 'close', 'volume'}
    if not required.issubset(df.columns):
        return None
    df = df[list(required)].dropna()
    if len(df) < 50:
        return None
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def _extract_ticker(raw: pd.DataFrame, ticker: str, batch_size: int) -> pd.DataFrame | None:
    """Pull a single ticker's slice out of a multi-ticker download."""
    if batch_size == 1:
        return _normalize(raw)
    if not isinstance(raw.columns, pd.MultiIndex):
        return None
    # yfinance ≥1.0 returns columns as (Price, Ticker) — level 1 is the ticker
    levels = raw.columns.get_level_values(1)
    if ticker not in levels:
        return None
    return _normalize(raw.xs(ticker, axis=1, level=1))


def _download_batch(tickers: list, period: str) -> dict:
    results = {}
    try:
        raw = yf.download(
            tickers,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if raw is None or raw.empty:
            return results
        for ticker in tickers:
            df = _extract_ticker(raw, ticker, len(tickers))
            if df is not None:
                results[ticker] = df
    except Exception as e:
        logger.error(f"Batch download error: {e}")
    return results


def download_history(tickers: list, days: int = 400) -> dict:
    """Download `days` of daily OHLCV for every ticker in `tickers`."""
    results = {}
    period  = f"{days}d"
    total   = len(tickers)

    for i in range(0, total, _BATCH_SIZE):
        batch = tickers[i: i + _BATCH_SIZE]
        pct   = min(i + _BATCH_SIZE, total)
        logger.info(f"  Downloading {pct}/{total}…")
        results.update(_download_batch(batch, period))

    return results


def update_cache(tickers: list, cache_dir: str = "data/cache", full_days: int = 400) -> dict:
    """
    Smart incremental updater:
      • First-seen tickers  → full history download
      • Stale tickers       → last-10-days download, merged into cache
      • Fresh tickers       → loaded straight from cache

    Returns a dict {ticker: DataFrame} ready for screening.
    """
    cache = DataCache(cache_dir)

    new_tickers   = [t for t in tickers if not cache.exists(t)]
    existing      = [t for t in tickers if cache.exists(t)]

    # Tickers whose history is shorter than 60 % of the target — re-download in full.
    # This runs automatically when full_history_days is increased in config.
    threshold     = int(full_days * 0.6)
    short_tickers = [t for t in existing if cache.row_count(t) < threshold]
    stale_tickers = [
        t for t in existing
        if t not in short_tickers and cache.needs_update(t)
    ]

    if new_tickers:
        logger.info(f"New tickers: {len(new_tickers)} — downloading {full_days} days of history…")
        for ticker, df in download_history(new_tickers, full_days).items():
            cache.save(ticker, df)

    if short_tickers:
        logger.info(
            f"Short-history tickers: {len(short_tickers)} — "
            f"re-downloading {full_days} days (history target increased)…"
        )
        for ticker, df in download_history(short_tickers, full_days).items():
            cache.save(ticker, df)   # overwrite, not append

    if stale_tickers:
        logger.info(f"Stale tickers: {len(stale_tickers)} — fetching recent bars…")
        for ticker, df in download_history(stale_tickers, days=10).items():
            cache.append(ticker, df)

    logger.info("Loading from cache…")
    data = {}
    for ticker in tickers:
        df = cache.load(ticker)
        if df is not None and len(df) >= 50:
            data[ticker] = df

    logger.info(f"Ready: {len(data)} tickers loaded")
    return data
