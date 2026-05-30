"""
Helper functions for the lookback and trend operators used in MarketInOut syntax.
"""
import pandas as pd


def any_in_window(condition: pd.Series, n_bars: int) -> bool:
    """
    True if `condition` was True at any bar in the most recent n_bars bars.

    Implements MarketInOut's  @{0..N}  operator: pass n_bars = N + 1.
    Example: @{0..20} → any_in_window(cond, 21)
    """
    if len(condition) < n_bars:
        return bool(condition.any())
    return bool(condition.iloc[-n_bars:].any())


def was_true_at(condition: pd.Series, bars_ago: int) -> bool:
    """
    True if `condition` was True exactly `bars_ago` bars back.
    Implements MarketInOut's  @N  suffix.
    Example: (rsi(7) < 60)@1 → was_true_at(rsi7 < 60, bars_ago=1)
    """
    idx = -(bars_ago + 1)
    if abs(idx) > len(condition):
        return False
    return bool(condition.iloc[idx])


def series_trend_dn(series: pd.Series, n: int) -> bool:
    """
    True if series is lower today than it was n bars ago.
    Implements MarketInOut's  series trend_dn N.
    """
    if len(series) <= n:
        return False
    return float(series.iloc[-1]) < float(series.iloc[-(n + 1)])


def series_trend_up(series: pd.Series, n: int) -> bool:
    """
    True if series is higher today than it was n bars ago.
    Implements MarketInOut's  series trend_up N.
    """
    if len(series) <= n:
        return False
    return float(series.iloc[-1]) > float(series.iloc[-(n + 1)])
