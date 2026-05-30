"""
Risk-based position sizing and open-risk gate.
"""
import math
from config import CONFIG


def compute_position(
    entry_price: float,
    stop_price: float,
    account_value: float = None,
    risk_pct: float = None,
) -> dict | None:
    """
    Compute position size using a fixed risk-percentage of account.

        shares = floor( (account × risk_pct) / (entry − stop) )

    Returns a dict with shares, position value, risk in dollars, and
    pre-computed R-multiple profit targets, or None if the math is invalid.
    """
    account_value = account_value if account_value is not None else CONFIG.risk.account_value
    risk_pct      = risk_pct      if risk_pct      is not None else CONFIG.risk.risk_per_trade_pct

    r_per_share = entry_price - stop_price
    if r_per_share <= 0:
        return None

    risk_dollars = account_value * risk_pct
    shares       = math.floor(risk_dollars / r_per_share)
    if shares <= 0:
        return None

    targets = {
        f"{r}R": round(entry_price + r * r_per_share, 2)
        for r, _ in CONFIG.risk.r_exit_levels
    }

    return {
        'shares':         shares,
        'position_value': round(shares * entry_price, 2),
        'risk_dollars':   round(shares * r_per_share, 2),
        'risk_pct_actual':round(shares * r_per_share / account_value * 100, 3),
        'r_per_share':    round(r_per_share, 2),
        'entry_price':    entry_price,
        'stop_price':     stop_price,
        'targets':        targets,
    }


def check_risk_gate(
    new_trade_risk: float,
    open_positions: list,
    account_value: float = None,
    max_open_risk_pct: float = None,
) -> tuple:
    """
    Returns (can_trade: bool, remaining_capacity_dollars: float).

    open_positions: list of dicts, each with a 'risk_dollars' key.
    """
    account_value     = account_value     if account_value     is not None else CONFIG.risk.account_value
    max_open_risk_pct = max_open_risk_pct if max_open_risk_pct is not None else CONFIG.risk.max_open_risk_pct

    max_risk      = account_value * max_open_risk_pct
    current_risk  = sum(p.get('risk_dollars', 0) for p in open_positions)
    remaining     = max_risk - current_risk
    can_trade     = (current_risk + new_trade_risk) <= max_risk

    return can_trade, round(remaining, 2)
