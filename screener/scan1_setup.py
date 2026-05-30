"""
Daily Setup Scan — momentum breakout filter.

Condition A: High-volume NYSE/NASDAQ stocks in strong uptrend with a strong day.
Condition B: Mid/small-cap stocks (lower volume threshold) with same momentum profile.
"""
import pandas as pd
from screener.conditions import any_in_window, series_trend_dn

_MIN_BARS = 210   # need 200-day SMA + buffer


def passes_scan1(df: pd.DataFrame) -> bool:
    """
    Returns True if the ticker passes either Condition A or Condition B.
    df must already have indicator columns attached (via compute_all).
    """
    if len(df) < _MIN_BARS:
        return False

    r  = df.iloc[-1]    # current bar
    r1 = df.iloc[-2]    # previous bar

    # ── Conditions shared by both A and B ─────────────────────────────
    natr_ok      = r['natr50'] > 3
    above_sma20  = r['close']  > r['sma20']
    sma_stack    = r['sma10']  > r['sma20']             # sma(10) > sma(20)
    up_day       = r['close']  > r1['close']            # price > c[1]
    atr_ok       = r['atr1']   > r['atr20'] * 0.6      # atr(1) > atr(20)*0.6
    strong_close = r['close']  > r['low'] + (r['high'] - r['low']) * 0.4

    # ! (sma(20) < sma(50))@{0..20} — SMA20 never below SMA50 in last 21 bars
    no_sma_cross = not any_in_window(df['sma20'] < df['sma50'], 21)

    # ! (price < sma(50) and sma(50) trend_dn 20)
    not_in_downtrend = not (
        r['close'] < r['sma50'] and series_trend_dn(df['sma50'], 20)
    )

    # ── Condition A: large-cap / higher volume ─────────────────────────
    if (
        r['advol20'] > 10 and
        r['advol50'] > 10 and
        no_sma_cross and
        not_in_downtrend and
        above_sma20 and
        sma_stack and
        up_day and
        atr_ok and
        strong_close and
        natr_ok
    ):
        return True

    # ── Condition B: mid/small-cap stocks, lower volume threshold ───────
    return (
        r['advol20'] > 3 and
        not series_trend_dn(df['sma20'], 20) and
        r['close'] > r['sma10'] and
        above_sma20 and
        sma_stack and
        up_day and
        atr_ok and
        strong_close and
        natr_ok
    )
