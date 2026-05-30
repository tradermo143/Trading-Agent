"""
IBKR order placement via ib_insync.

Connects to Trader Workstation (TWS) or IB Gateway running locally.
Paper trading port : 7497  (TWS)  /  4002  (Gateway)
Live trading port  : 7496  (TWS)  /  4001  (Gateway)

Safety: CONFIG.ibkr.paper must be True to place any order.
"""
import asyncio
import logging
from dataclasses import dataclass

# Python 3.10+ no longer auto-creates an event loop outside async context.
# ib_insync's dependency (eventkit) requires one to exist at import time.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import IB, Stock, Order
import ib_insync

from config import CONFIG

logger = logging.getLogger(__name__)


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class TradeSetup:
    ticker:         str
    entry_price:    float   # buy-stop trigger
    stop_price:     float   # initial stop loss
    shares:         int
    r_value:        float
    scans:          list    # ['Setup'] | ['Contraction'] | ['Setup', 'Contraction']


@dataclass
class PlacedOrder:
    ticker:         str
    entry_order_id: int
    stop_order_id:  int
    entry_price:    float
    stop_price:     float
    shares:         int
    status:         str     # 'submitted' | 'error'
    message:        str = ''


# ── Connection ────────────────────────────────────────────────────────────────

class IBKRClient:

    def __init__(self):
        self.ib   = IB()
        self._connected = False

    def connect(self) -> bool:
        if self._connected and self.ib.isConnected():
            return True
        try:
            self.ib.connect(
                CONFIG.ibkr.host,
                CONFIG.ibkr.port,
                clientId=CONFIG.ibkr.client_id,
                timeout=10,
            )
            self._connected = True
            acct = self.ib.managedAccounts()
            logger.info(f"Connected to IBKR  port={CONFIG.ibkr.port}  accounts={acct}")
            return True
        except Exception as e:
            logger.error(f"IBKR connection failed: {e}")
            logger.error(
                "Make sure TWS / IB Gateway is running and "
                "API connections are enabled (Edit → Global Config → API → Settings)."
            )
            return False

    def disconnect(self):
        if self._connected:
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IBKR")

    def account_value(self) -> float:
        """Return Net Liquidation Value of the connected account."""
        vals = self.ib.accountValues()
        for v in vals:
            if v.tag == 'NetLiquidation' and v.currency == 'USD':
                return float(v.value)
        return 0.0

    # ── Order placement ───────────────────────────────────────────────────────

    def place_bracket(self, setup: TradeSetup) -> PlacedOrder:
        """
        Place a bracket order for one setup:
          1. BUY STOP  at entry_price  (triggers when price breaks above)
          2. STOP LOSS at stop_price   (attached, placed once parent fills)

        Uses IBKR's parent/child order linking so the stop loss is only
        active after the entry is filled.
        """
        if not CONFIG.ibkr.paper:
            raise RuntimeError(
                "Live trading is disabled. Set CONFIG.ibkr.paper = False "
                "only when you are ready to trade with real money."
            )

        contract = Stock(setup.ticker, 'SMART', 'USD')

        # ── Parent: buy-stop entry ────────────────────────────────────────
        parent = Order()
        parent.action          = 'BUY'
        parent.orderType       = 'STP'           # stop order
        parent.auxPrice        = setup.entry_price
        parent.totalQuantity   = setup.shares
        parent.transmit        = False            # hold — child order follows
        parent.tif             = 'GTC'            # good till cancelled

        # ── Child: stop-loss ──────────────────────────────────────────────
        stop_loss = Order()
        stop_loss.action        = 'SELL'
        stop_loss.orderType     = 'STP'
        stop_loss.auxPrice      = setup.stop_price
        stop_loss.totalQuantity = setup.shares
        stop_loss.transmit      = True            # transmit both orders together
        stop_loss.tif           = 'GTC'

        try:
            parent_trade = self.ib.placeOrder(contract, parent)
            self.ib.sleep(0.5)                    # let TWS assign the order ID

            stop_loss.parentId = parent_trade.order.orderId
            child_trade  = self.ib.placeOrder(contract, stop_loss)
            self.ib.sleep(0.5)

            logger.info(
                f"Bracket placed  {setup.ticker}  "
                f"entry={setup.entry_price}  stop={setup.stop_price}  "
                f"shares={setup.shares}  "
                f"entry_id={parent_trade.order.orderId}  "
                f"stop_id={child_trade.order.orderId}"
            )
            return PlacedOrder(
                ticker         = setup.ticker,
                entry_order_id = parent_trade.order.orderId,
                stop_order_id  = child_trade.order.orderId,
                entry_price    = setup.entry_price,
                stop_price     = setup.stop_price,
                shares         = setup.shares,
                status         = 'submitted',
            )

        except Exception as e:
            logger.error(f"Order placement failed for {setup.ticker}: {e}")
            return PlacedOrder(
                ticker         = setup.ticker,
                entry_order_id = -1,
                stop_order_id  = -1,
                entry_price    = setup.entry_price,
                stop_price     = setup.stop_price,
                shares         = setup.shares,
                status         = 'error',
                message        = str(e),
            )

    def place_all(self, setups: list) -> list:
        """Place bracket orders for a list of TradeSetup objects."""
        if not self.connect():
            return []

        results = []
        for setup in setups:
            result = self.place_bracket(setup)
            results.append(result)
            self.ib.sleep(0.3)      # small gap between orders

        self.disconnect()
        return results

    def open_positions(self) -> list:
        """Return current open positions as list of dicts."""
        if not self.connect():
            return []
        positions = []
        for pos in self.ib.positions():
            if pos.position != 0:
                positions.append({
                    'ticker':   pos.contract.symbol,
                    'shares':   pos.position,
                    'avg_cost': pos.avgCost,
                })
        return positions
