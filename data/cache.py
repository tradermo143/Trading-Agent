"""
Parquet-based local cache for per-ticker OHLCV DataFrames.
"""
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, date

logger = logging.getLogger(__name__)


class DataCache:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, ticker: str) -> Path:
        return self.cache_dir / f"{ticker}.parquet"

    def exists(self, ticker: str) -> bool:
        return self._path(ticker).exists()

    def save(self, ticker: str, df: pd.DataFrame):
        if df is None or df.empty:
            return
        df.to_parquet(self._path(ticker))

    def load(self, ticker: str) -> pd.DataFrame | None:
        p = self._path(ticker)
        if not p.exists():
            return None
        try:
            return pd.read_parquet(p)
        except Exception as e:
            logger.warning(f"Cache load failed for {ticker}: {e}")
            return None

    def last_date(self, ticker: str) -> date | None:
        df = self.load(ticker)
        if df is None or df.empty:
            return None
        return pd.Timestamp(df.index[-1]).date()

    def needs_update(self, ticker: str) -> bool:
        """True if no cache exists or last bar is more than 1 day old."""
        if not self.exists(ticker):
            return True
        last = self.last_date(ticker)
        if last is None:
            return True
        return (datetime.now().date() - last).days > 1

    def append(self, ticker: str, new_df: pd.DataFrame):
        """Merge new bars into existing cache, deduplicate, keep latest."""
        existing = self.load(ticker)
        if existing is None:
            self.save(ticker, new_df)
            return
        combined = pd.concat([existing, new_df])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined.sort_index(inplace=True)
        self.save(ticker, combined)

    def row_count(self, ticker: str) -> int:
        """Return number of cached rows without loading the full DataFrame."""
        p = self._path(ticker)
        if not p.exists():
            return 0
        try:
            import pyarrow.parquet as pq
            return pq.read_metadata(str(p)).num_rows
        except Exception:
            return 0

    def list_tickers(self) -> list:
        return [p.stem for p in self.cache_dir.glob("*.parquet")]
