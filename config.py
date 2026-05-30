"""
Central configuration for the trading agent.
Edit the values in AppConfig to adjust behaviour — no other files need touching.
"""
from dataclasses import dataclass, field


@dataclass
class RiskConfig:
    account_value: float = 100_000.0        # Total account size in USD

    # Per-trade risk: fraction of account to risk on each position
    risk_per_trade_pct: float = 0.005       # 0.5 % default

    # Maximum total open risk across all positions simultaneously
    max_open_risk_pct: float = 0.05         # 5 % default

    # Entry / stop tolerance (dollars added/subtracted)
    entry_buffer: float = 0.05
    stop_buffer:  float = 0.05

    # Time-based exit (trading days from entry)
    time_exit_days:     int   = 5
    time_exit_fraction: float = 0.33        # Sell 33 % of remaining position on Day 5
    move_stop_to_breakeven: bool = True      # Move stop to entry price after Day 5 exit

    # R-multiple profit-exit ladder
    # Each entry: (r_multiple, fraction_of_remaining_position_to_sell)
    # Example: at 1R gain sell 25 % of what is still open, then at 2R sell another 25 %, etc.
    r_exit_levels: list = field(default_factory=lambda: [
        (1.0, 0.25),
        (2.0, 0.25),
        (3.0, 0.25),
        # Remainder runs with trailing stop — define in future exit rules
    ])


@dataclass
class IBKRConfig:
    host:      str  = "127.0.0.1"
    port:      int  = 7497    # TWS paper = 7497 | TWS live = 7496 | Gateway paper = 4002
    client_id: int  = 1
    paper:     bool = True    # Safety flag — must be False to place live orders


@dataclass
class DataConfig:
    cache_dir:          str   = "data/cache"
    universe_cache_dir: str   = "data"
    full_history_days:  int   = 800    # Days downloaded on first run (~3.2 years)
    min_price:          float = 2.0    # Ignore stocks below this price


@dataclass
class UIConfig:
    host:         str = "127.0.0.1"
    port:         int = 5000
    daily_bars:   int = 150    # ~6 months of daily candles
    weekly_bars:  int = 150    # same bar count as daily chart


@dataclass
class AppConfig:
    risk: RiskConfig = field(default_factory=RiskConfig)
    ibkr: IBKRConfig = field(default_factory=IBKRConfig)
    data: DataConfig = field(default_factory=DataConfig)
    ui:   UIConfig   = field(default_factory=UIConfig)


CONFIG = AppConfig()
