"""
TradingView watchlist manager.

Uses TradingView's internal session-based REST API — the same endpoints
their web app uses. These are undocumented; if TV ever changes them the
push will fail gracefully with a logged error (the rest of the system
continues working fine).

Credentials are loaded from .env:
    TV_USERNAME=your_email@example.com
    TV_PASSWORD=yourpassword
"""
import json
import logging
import os
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_BASE    = 'https://www.tradingview.com'
_API     = 'https://api.tradingview.com'
_HEADERS = {
    'User-Agent':  (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Origin':  _BASE,
    'Referer': _BASE + '/',
}


class TVWatchlistManager:

    def __init__(self):
        self.username = os.getenv('TV_USERNAME', '').strip()
        self.password = os.getenv('TV_PASSWORD', '').strip()
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        self._logged_in = False

    # ── Authentication ────────────────────────────────────────────────

    def _login(self) -> bool:
        if self._logged_in:
            return True
        if not self.username or not self.password:
            logger.error(
                "TradingView credentials not found. "
                "Add TV_USERNAME and TV_PASSWORD to your .env file."
            )
            return False
        try:
            resp = self._session.post(
                f'{_BASE}/accounts/signin/',
                data={
                    'username':    self.username,
                    'password':    self.password,
                    'remember_me': 'on',
                },
                timeout=20,
            )
            resp.raise_for_status()
            body = resp.json()
            if 'error' in body:
                logger.error(f"TV login failed: {body['error']}")
                return False
            logger.info(f"Logged in to TradingView as '{self.username}'")
            self._logged_in = True
            return True
        except Exception as e:
            logger.error(f"TV login error: {e}")
            return False

    # ── Watchlist API ─────────────────────────────────────────────────

    def _list_watchlists(self) -> list:
        resp = self._session.get(
            f'{_API}/api/v1/symbols_groups/list/',
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _create(self, name: str, symbols: list) -> dict:
        resp = self._session.post(
            f'{_API}/api/v1/symbols_groups/',
            json={
                'name':    name,
                'symbols': {'content': [{'symbol': s} for s in symbols]},
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _update(self, wl_id, name: str, symbols: list) -> dict:
        resp = self._session.put(
            f'{_API}/api/v1/symbols_groups/{wl_id}/',
            json={
                'name':    name,
                'symbols': {'content': [{'symbol': s} for s in symbols]},
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Public interface ──────────────────────────────────────────────

    def push(
        self,
        setup_tickers:       list,
        contraction_tickers: list,
        exchange_map:        dict,
    ) -> bool:
        """
        Creates or overwrites the daily watchlist on TradingView.
        Watchlist name: "US Watchlist YYYY-MM-DD"
        Order: Setup tickers first, then Contraction tickers.
        """
        if not self._login():
            return False

        def tv_symbol(t: str) -> str:
            exch = exchange_map.get(t, 'NASDAQ')
            return f'{exch}:{t}'

        symbols = [tv_symbol(t) for t in setup_tickers] + \
                  [tv_symbol(t) for t in contraction_tickers]

        if not symbols:
            logger.warning("No tickers to push — watchlist not updated.")
            return False

        name = f"US Watchlist {date.today().strftime('%Y-%m-%d')}"

        try:
            watchlists = self._list_watchlists()
            existing   = next(
                (w for w in watchlists if w.get('name') == name), None
            )

            if existing:
                self._update(existing['id'], name, symbols)
                logger.info(
                    f"TradingView watchlist '{name}' updated "
                    f"({len(symbols)} tickers)"
                )
            else:
                self._create(name, symbols)
                logger.info(
                    f"TradingView watchlist '{name}' created "
                    f"({len(symbols)} tickers)"
                )
            return True

        except requests.HTTPError as e:
            logger.error(
                f"TV watchlist API error {e.response.status_code}: "
                f"{e.response.text[:200]}"
            )
        except Exception as e:
            logger.error(f"TV watchlist push failed: {e}")

        return False
