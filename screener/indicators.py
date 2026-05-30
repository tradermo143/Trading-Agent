"""
All technical indicators required by the two scans.
All functions accept and return pandas Series; compute_all() enriches a full OHLCV DataFrame.
"""
import numpy as np
import pandas as pd


# ── Primitives ────────────────────────────────────────────────────────────────

def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=n).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    """
    ATR(1)  = single-day True Range (no smoothing) — matches MarketInOut atr(1).
    ATR(n>1)= simple n-period rolling mean of TR.
    """
    tr = true_range(high, low, close)
    return tr if n == 1 else tr.rolling(n, min_periods=n).mean()


def natr(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    """Normalised ATR: ATR(n) / Close * 100  (percentage of price)."""
    return atr(high, low, close, n) / close * 100


def rsi(close: pd.Series, n: int) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(n, min_periods=n).mean()
    loss  = (-delta.clip(upper=0)).rolling(n, min_periods=n).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def advol(volume: pd.Series, n: int) -> pd.Series:
    """Average Daily Volume in millions of shares."""
    return volume.rolling(n, min_periods=n).mean() / 1_000_000


def pgo(close: pd.Series, high: pd.Series, low: pd.Series, n: int) -> pd.Series:
    """
    Price Gap Oscillator: (Close - SMA(n)) / ATR(n).
    Measures how many ATRs the price is away from its n-day moving average.
    """
    return (close - sma(close, n)) / atr(high, low, close, n)


# ── Full enrichment ───────────────────────────────────────────────────────────

def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach all required indicator columns to a copy of the OHLCV DataFrame.
    Input columns expected: open, high, low, close, volume  (lower-case).
    """
    df = df.copy()
    h, l, c, v = df['high'], df['low'], df['close'], df['volume']

    df['sma10']  = sma(c, 10)
    df['sma20']  = sma(c, 20)
    df['sma50']  = sma(c, 50)
    df['sma100'] = sma(c, 100)
    df['sma200'] = sma(c, 200)

    df['atr1']  = atr(h, l, c, 1)
    df['atr5']  = atr(h, l, c, 5)
    df['atr20'] = atr(h, l, c, 20)
    df['atr50'] = atr(h, l, c, 50)

    df['natr50'] = natr(h, l, c, 50)
    df['rsi7']   = rsi(c, 7)

    df['advol20'] = advol(v, 20)
    df['advol30'] = advol(v, 30)
    df['advol50'] = advol(v, 50)

    df['pgo20'] = pgo(c, h, l, 20)
    df['pgo50'] = pgo(c, h, l, 50)

    df['arange0'] = df['atr1']   # arange(0) ≡ today's True Range

    return df
