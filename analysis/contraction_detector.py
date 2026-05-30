"""
Identifies the contraction zone on the most recent bars and calculates
entry price, stop price, and R value.
"""
import pandas as pd
from screener.indicators import compute_all
from config import CONFIG

_MAX_LOOKBACK = 15    # Maximum bars to look back when building the zone


def detect_contraction_zone(
    df: pd.DataFrame,
    entry_buffer: float = None,
    stop_buffer:  float = None,
) -> dict | None:
    """
    Walks backwards from the most recent bar and collects consecutive bars
    whose True Range is below 75 % of the 20-day ATR.  Those bars form the
    'contraction zone'.

    Entry  = max(zone highs) + entry_buffer
    Stop   = min(zone lows)  - stop_buffer

    Returns a dict or None if no valid zone is found.
    """
    entry_buffer = entry_buffer if entry_buffer is not None else CONFIG.risk.entry_buffer
    stop_buffer  = stop_buffer  if stop_buffer  is not None else CONFIG.risk.stop_buffer

    if 'atr1' not in df.columns:
        df = compute_all(df)

    if len(df) < 5:
        return None

    atr20 = float(df['atr20'].iloc[-1])
    if pd.isna(atr20) or atr20 <= 0:
        return None

    threshold  = atr20 * 0.75
    n          = len(df)
    zone_end   = n - 1
    zone_start = zone_end

    for i in range(n - 1, max(n - 1 - _MAX_LOOKBACK, -1), -1):
        if float(df['atr1'].iloc[i]) < threshold:
            zone_start = i
        else:
            break

    zone = df.iloc[zone_start : zone_end + 1]
    if zone.empty:
        return None

    zone_high = float(zone['high'].max())
    zone_low  = float(zone['low'].min())

    entry_price = round(zone_high + entry_buffer, 2)
    stop_price  = round(zone_low  - stop_buffer,  2)
    r_value     = round(entry_price - stop_price,  2)

    if r_value <= 0:
        return None

    return {
        'zone_start_date': zone.index[0],
        'zone_end_date':   zone.index[-1],
        'zone_length':     len(zone),
        'zone_high':       zone_high,
        'zone_low':        zone_low,
        'entry_price':     entry_price,
        'stop_price':      stop_price,
        'r_value':         r_value,
    }
