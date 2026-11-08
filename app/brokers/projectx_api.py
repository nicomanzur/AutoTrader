# app/brokers/projectx_api.py
"""
ProjectX API Client for TraderDesk V2.

This module provides a client for interacting with the ProjectX/TopStepX trading API.
It handles authentication, account management, contract lookup, historical data retrieval,
and order placement.
"""
from __future__ import annotations
import os, datetime as dt
from typing import Any, Dict, List, Optional
import requests
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv

load_dotenv()


def _https_base(url: str) -> str:
    """
    Ensure URL uses HTTPS scheme.

    Args:
        url: URL to process

    Returns:
        URL with HTTPS scheme
    """
    u = urlparse(url.strip())
    scheme = "https"
    netloc = u.netloc or u.path
    return urlunparse((scheme, netloc, "", "", "", ""))


class ProjectXClient:
    """
    Client for ProjectX/TopStepX API.

    Provides methods for authentication, account management, contract lookup,
    historical data retrieval, and order placement. Handles automatic token
    refresh on 401 errors.

    Attributes:
        base_api: Base API URL
        user: Username for authentication
        api_key: API key for authentication
        session: Requests session for connection pooling
        token: Authentication token (set after login)
    """
    def __init__(self) -> None:
        """
        Initialize ProjectX API client.

        Loads configuration from environment variables:
        - PROJECTX_API_BASE: API base URL (default: https://api.topstepx.com)
        - PROJECTX_USER: Username for authentication
        - PROJECTX_API_KEY: API key for authentication
        """
        base = os.getenv("PROJECTX_API_BASE", "https://api.topstepx.com")
        self.base_api = _https_base(base)
        self.user = os.getenv("PROJECTX_USER", "").strip()
        self.api_key = os.getenv("PROJECTX_API_KEY", "").strip()
        self.session = requests.Session()
        self.token: Optional[str] = None
        print(f"[ProjectXClient] base_api={self.base_api} user={self.user[:2]}***")

    def _headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for API requests.

        Returns:
            Dictionary of headers including Authorization if token is set
        """
        h = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _post(self, path: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Make POST request to API with automatic retry on 401.

        Args:
            path: API endpoint path
            payload: Request payload
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            requests.HTTPError: If request fails with non-401 error
        """
        url = f"{self.base_api}{path}"

        def do():
            return self.session.post(url, headers=self._headers(), json=payload, timeout=timeout)

        r = do()
        if r.status_code == 401:
            # token ausente/vencido → re-login y reintento 1 vez
            try:
                self.login_with_key()
                r = do()
            except Exception:
                pass

        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}

        if not r.ok:
            print("resp:", r.status_code, data)
            r.raise_for_status()
        return data

    # -------- Auth --------
    def login_with_key(self) -> str:
        """
        Authenticate with API using username and API key.

        Returns:
            Authentication token

        Raises:
            RuntimeError: If authentication fails or token is not returned
        """
        payload = {"userName": self.user, "apiKey": self.api_key}
        # endpoint correcto: /api/Auth/loginKey
        data = self._post("/api/Auth/loginKey", payload, timeout=20)
        if not data.get("success"):
            raise RuntimeError(f"Auth failed: {data}")
        token = data.get("token")
        if not token:
            raise RuntimeError(f"No token in response: {data}")
        self.token = token
        return token

    def validate_token(self) -> bool:
        """
        Validate current authentication token.

        Returns:
            True if token is valid, False otherwise
        """
        data = self._post("/api/Auth/validate", {}, timeout=10)
        return bool(data.get("success"))

    # -------- Accounts --------
    def search_accounts(self, only_active: bool = True) -> List[Dict[str, Any]]:
        """
        Search for trading accounts.

        Args:
            only_active: Only return active accounts if True

        Returns:
            List of account dictionaries

        Raises:
            RuntimeError: If API request fails
        """
        data = self._post("/api/Account/search", {"onlyActiveAccounts": only_active}, timeout=20)
        if not data.get("success"):
            raise RuntimeError(f"Account.search failed: {data}")
        return data.get("accounts", []) or data.get("items", [])

    # -------- Contracts --------
    def search_contracts(self, text: str, live: bool = False) -> List[Dict[str, Any]]:
        """
        Search for contracts by text.

        Args:
            text: Search text (e.g., "MNQ", "ES")
            live: Request live data subscription if True

        Returns:
            List of contract dictionaries

        Raises:
            RuntimeError: If API request fails
        """
        # API requires "live" parameter
        payload = {"searchText": text, "live": live}
        data = self._post("/api/Contract/search", payload, timeout=20)
        if not data.get("success"):
            raise RuntimeError(f"Contract.search failed: {data}")
        return data.get("contracts", []) or data.get("items", [])

    def search_contracts_by_id(self, contract_id: str) -> List[Dict[str, Any]]:
        """
        Search for contracts by contract ID.

        Args:
            contract_id: Contract identifier (e.g., "CON.F.US.MNQ.H25")

        Returns:
            List of contract dictionaries (usually single element)

        Raises:
            RuntimeError: If API request fails
        """
        data = self._post("/api/Contract/searchById", {"contractId": contract_id}, timeout=15)
        if not data.get("success"):
            raise RuntimeError(f"Contract.searchById failed: {data}")
        return data.get("contracts", []) or data.get("items", [])

    # -------- History (bars) --------
    def retrieve_bars(
        self,
        contract_id: str,
        live: bool = False,
        unit: int = 2,
        unit_number: int = 15,
        include_partial: bool = False,
        limit: int = 400,
        lookback_days: Optional[int] = None,
        start: Optional[dt.datetime] = None,
        end: Optional[dt.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve historical bar data for a contract.

        Args:
            contract_id: Contract identifier
            live: Request live data subscription if True
            unit: Bar unit type (1=Tick, 2=Minute, 3=Hour, 4=Day)
            unit_number: Bar size (e.g., 15 for 15-minute bars)
            include_partial: Include current/partial bar if True
            limit: Maximum number of bars to retrieve
            lookback_days: Number of days to look back (alternative to start/end)
            start: Start datetime (optional, defaults to lookback_days)
            end: End datetime (optional, defaults to now)

        Returns:
            List of bar dictionaries with OHLCV data

        Raises:
            RuntimeError: If API request fails
        """
        now = dt.datetime.now(dt.timezone.utc)
        if end is None:
            end = now
        if start is None:
            days = lookback_days or 7
            start = end - dt.timedelta(days=days)
        payload = {
            "contractId": contract_id,
            "live": bool(live),
            "unit": unit,
            "unitNumber": unit_number,
            "startTime": start.replace(microsecond=0).isoformat().replace("+00:00","Z"),
            "endTime":   end.replace(microsecond=0).isoformat().replace("+00:00","Z"),
            "limit": int(limit),
            "includePartialBar": bool(include_partial),
        }
        data = self._post("/api/History/retrieveBars", payload, timeout=30)
        if not data.get("success"):
            raise RuntimeError(f"retrieveBars failed: {data}")
        return data.get("bars") or []

    # -------- Orders --------
    def place_order(
        self,
        account_id: int,
        contract_id: str,
        side: int,                 # 0=Buy, 1=Sell
        size: int,
        order_type: int = 2,       # 2=Market, 1=Limit, 4=Stop
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        linked_order_id: Optional[int] = None,
        customTag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place a trading order.

        Args:
            account_id: Trading account ID
            contract_id: Contract identifier
            side: Order side (0=Buy, 1=Sell)
            size: Order quantity
            order_type: Order type (1=Limit, 2=Market, 4=Stop, etc.)
            limit_price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            linked_order_id: Parent order ID for linking (TP/SL orders)
            customTag: Custom tag for order identification

        Returns:
            Response dictionary with orderId and success status

        Raises:
            RuntimeError: If order placement fails
        """
        payload: Dict[str, Any] = {
            "accountId": account_id,
            "contractId": contract_id,
            "type": order_type,
            "side": side,
            "size": size,
        }
        if limit_price is not None:
            payload["limitPrice"] = float(limit_price)
        if stop_price is not None:
            payload["stopPrice"] = float(stop_price)
        if linked_order_id is not None:
            payload["linkedOrderId"] = linked_order_id
        if customTag:
            payload["customTag"] = customTag

        data = self._post("/api/Order/place", payload, timeout=20)
        if not data.get("success"):
            raise RuntimeError(f"order.place failed: {data}")
        return data

    def place_bracket_order(
        self,
        account_id: int,
        contract_id: str,
        side: int,                          # 0=Buy, 1=Sell
        size: int,
        tp_ticks: int,                      # Take Profit en ticks
        sl_ticks: int,                      # Stop Loss en ticks
        customTag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place a MARKET order with bracket orders (TP/SL) in a single API call.

        Implementation follows official API documentation. The bracket orders
        (Take Profit and Stop Loss) are automatically created and linked to
        the market order.

        Order Types Reference:
            1 = Limit
            2 = Market
            4 = Stop
            5 = TrailingStop
            6 = JoinBid
            7 = JoinAsk

        Args:
            account_id: Trading account ID
            contract_id: Contract identifier
            side: Order side (0=Buy, 1=Sell)
            size: Order quantity
            tp_ticks: Take profit offset in ticks (signed: +/- based on direction)
            sl_ticks: Stop loss offset in ticks (signed: +/- based on direction)
            customTag: Custom tag for order identification (must be unique)

        Returns:
            Response dictionary with orderId and success status

        Raises:
            RuntimeError: If order placement fails

        Note:
            For LONG positions (side=0): tp_ticks > 0, sl_ticks < 0
            For SHORT positions (side=1): tp_ticks < 0, sl_ticks > 0
        """
        payload: Dict[str, Any] = {
            "accountId": account_id,
            "contractId": contract_id,
            "type": 2,  # Market
            "side": side,
            "size": size,
            # TP as Limit; SL as Stop (per API documentation)
            "takeProfitBracket": {"ticks": int(tp_ticks), "type": 1},  # 1 = Limit
            "stopLossBracket": {"ticks": int(sl_ticks), "type": 4},    # 4 = Stop
        }

        if customTag:
            payload["customTag"] = customTag

        data = self._post("/api/Order/place", payload, timeout=20)
        if not data.get("success"):
            raise RuntimeError(f"bracket order.place failed: {data}")
        return data

    def search_trades(self, account_id: int, start_iso: str, end_iso: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for executed trades within a time range.

        Args:
            account_id: Trading account ID
            start_iso: Start timestamp in ISO format
            end_iso: End timestamp in ISO format (optional, defaults to now)

        Returns:
            List of trade dictionaries with execution details

        Raises:
            RuntimeError: If API request fails
        """
        payload: Dict[str, Any] = {"accountId": account_id, "startTimestamp": start_iso}
        if end_iso:
            payload["endTimestamp"] = end_iso
        data = self._post("/api/Trade/search", payload, timeout=20)
        if not data.get("success"):
            raise RuntimeError(f"Trade.search failed: {data}")
        return data.get("trades", []) or []

    def search_open_orders(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Órdenes abiertas de la cuenta (TopstepX Order/searchOpen).

        Ejemplo (equivalente a este cliente):
            POST {base}/api/Order/searchOpen
            Headers: Accept: text/plain, Content-Type: application/json
            Body: {"accountId": 212}

        Args:
            account_id: Trading account ID (entero, como en la API).

        Returns:
            Lista de órdenes (campo ``orders`` o ``items`` en la respuesta).

        Raises:
            RuntimeError: If API request fails
        """
        payload = {"accountId": int(account_id)}
        data = self._post("/api/Order/searchOpen", payload, timeout=20)
        if not data.get("success"):
            raise RuntimeError(f"Order.searchOpen failed: {data}")
        return data.get("orders", []) or data.get("items", [])

    def close_contract(self, account_id: int, contract_id: str) -> Dict[str, Any]:
        """
        Cierra la posición del contrato en la cuenta (API Position/closeContract).

        Documentación TopstepX: POST /api/Position/closeContract
        body: {"accountId": <int>, "contractId": "<CON...>"}
        """
        payload: Dict[str, Any] = {
            "accountId": int(account_id),
            "contractId": contract_id,
        }
        data = self._post("/api/Position/closeContract", payload, timeout=20)
        if not data.get("success"):
            raise RuntimeError(f"Position.closeContract failed: {data}")
        return data

    def cancel_order(self, account_id: int, order_id: int) -> Dict[str, Any]:
        """
        Cancela una orden pendiente (API Order/cancel).
        body: {"accountId": <int>, "orderId": <int>}
        """
        payload: Dict[str, Any] = {
            "accountId": int(account_id),
            "orderId": int(order_id),
        }
        data = self._post("/api/Order/cancel", payload, timeout=20)
        if not data.get("success"):
            raise RuntimeError(f"Order.cancel failed: {data}")
        return data