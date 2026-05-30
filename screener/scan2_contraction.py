"""
Daily Contraction Scan — Volatility Contraction Pattern (VCP-style).

Finds stocks in long-term uptrends that are coiling: today's range is
significantly smaller than the recent average, signalling a potential breakout.
"""
import pandas as pd
from screener.conditions import any_in_window, was_true_at, series_trend_dn, series_trend_up

_MIN_BARS = 210


def passes_scan2(df: pd.DataFrame) -> bool:
    """
    Returns True if the ticker matches the contraction pattern.
    df must already have indicator columns attached (via compute_all).
    """
    if len(df) < _MIN_BARS:
        return False

    r  = df.iloc[-1]    # current bar
    r1 = df.iloc[-2]    # previous bar

    # advol(30) > 3
    if r['advol30'] <= 3:
        return False

    # ! (sma(20) < sma(50))@{0..20}
    if any_in_window(df['sma20'] < df['sma50'], 21):
        return False

    # ! (price < sma(50) and sma(50) trend_dn 20)
    if r['close'] < r['sma50'] and series_trend_dn(df['sma50'], 20):
        return False

    # price > sma(100) or price > sma(200)
    if not (r['close'] > r['sma100'] or r['close'] > r['sma200']):
        return False

    # sma(200) trend_up 60
    if not series_trend_up(df['sma200'], 60):
        return False

    # natr(50) > 1.5
    if r['natr50'] <= 1.5:
        return False

    # price > sma(50) - arange(0)
    if r['close'] <= r['sma50'] - r['arange0']:
        return False

    # ── Volatility contraction ─────────────────────────────────────────
    a1, a5, a20, a50 = r['atr1'], r['atr5'], r['atr20'], r['atr50']

    strong = (a1 < a5 * 0.5) or (a1 < a20 * 0.5) or (a1 < a50 * 0.5)

    inside_day = r['close'] < r1['high'] and r['close'] > r1['low']
    moderate   = (a1 < a5 * 0.75) or (a1 < a20 * 0.75) or (a1 < a50 * 0.75)

    if not (strong or (inside_day and moderate)):
        return False

    # (pgo(50) < 2.5 or pgo(20) < 2.5)
    if not (r['pgo50'] < 2.5 or r['pgo20'] < 2.5):
        return False

    # (rsi(7) < 60)@1 — RSI(7) was below 60 yesterday
    if not was_true_at(df['rsi7'] < 60, bars_ago=1):
        return False

    return True
