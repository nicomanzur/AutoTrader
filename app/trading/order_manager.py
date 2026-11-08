"""
Order management module for TraderDesk V2.

This module provides a unified interface for placing and managing orders,
including bracket orders, TP/SL management, and order verification.
"""
from __future__ import annotations
import time
from typing import Optional, Any
from datetime import datetime, timezone, timedelta

from app.constants import OrderType, OrderSide, OrderStatus
from app.exceptions import (
    OrderPlacementError,
    DuplicateOrderError,
    APIError,
)
from app.utils.trading import (
    calculate_tp_price,
    calculate_sl_price,
    calculate_tp_sl_sides,
    calculate_bracket_ticks,
    round_to_tick,
    validate_trade_parameters,
)


class OrderManager:
    """
    Manages order placement and tracking.

    Provides a unified interface for placing market orders, bracket orders,
    and managing TP/SL orders.
    """

    def __init__(self, api_client: Any, account_id: int):
        """
        Initialize order manager.

        Args:
            api_client: ProjectX API client instance
            account_id: Trading account ID
        """
        self.api_client = api_client
        self.account_id = account_id

    def check_existing_orders_by_tag(self, tag_prefix: str) -> list[dict[str, Any]]:
        """
        Check for existing orders with a specific tag prefix.

        Args:
            tag_prefix: Tag prefix to search for

        Returns:
            List of matching orders
        """
        try:
            open_orders = self.api_client.search_open_orders(self.account_id)
            matching = []

            for order in open_orders:
                tag = str(order.get("customTag", "") or "")
                if tag.startswith(tag_prefix):
                    matching.append(order)

            return matching
        except Exception as e:
            print(f"[ORDER_MANAGER][WARN] Failed to check existing orders: {e}")
            return []

    def check_duplicate_orders(self, contract_id: str, tag_prefix: str) -> bool:
        """
        Check if there are duplicate orders for a contract with a tag prefix.

        Args:
            contract_id: Contract ID
            tag_prefix: Tag prefix to check

        Returns:
            True if duplicates exist, False otherwise
        """
        matching_orders = self.check_existing_orders_by_tag(tag_prefix)

        for order in matching_orders:
            if order.get("contractId") == contract_id:
                return True

        return False

    def poll_fill_price(self, contract_id: str, max_wait_sec: int = 30) -> Optional[float]:
        """
        Poll for fill price of a market order.

        Args:
            contract_id: Contract ID
            max_wait_sec: Maximum time to wait in seconds

        Returns:
            Fill price if found, None otherwise
        """
        start_iso = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        waited = 0

        while waited < max_wait_sec:
            try:
                trades = self.api_client.search_trades(self.account_id, start_iso)

                # Search in reverse (most recent first)
                for trade in reversed(trades):
                    if trade.get("contractId") == contract_id:
                        price = trade.get("price")
                        if price is not None:
                            return float(price)
            except Exception as e:
                print(f"[ORDER_MANAGER][WARN] Error polling fill price: {e}")

            time.sleep(1)
            waited += 1

        return None

    def place_market_order(self, contract_id: str, side: int, quantity: int,
                          custom_tag: Optional[str] = None) -> dict[str, Any]:
        """
        Place a market order.

        Args:
            contract_id: Contract ID
            side: Order side (BUY or SELL)
            quantity: Order quantity
            custom_tag: Optional custom tag

        Returns:
            Dictionary with order_id and success status

        Raises:
            OrderPlacementError: If order placement fails
            DuplicateOrderError: If duplicate order exists
        """
        result = {
            "order_id": None,
            "success": False,
            "error": None
        }

        # Check for duplicates
        if custom_tag:
            if self.check_existing_orders_by_tag(custom_tag):
                raise DuplicateOrderError(custom_tag)

        try:
            response = self.api_client.place_order(
                account_id=self.account_id,
                contract_id=contract_id,
                side=side,
                size=quantity,
                order_type=OrderType.MARKET,
                customTag=custom_tag
            )

            result["order_id"] = response.get("orderId")
            result["success"] = True

            return result
        except Exception as e:
            raise OrderPlacementError(
                f"Failed to place market order: {e}",
                order_type="MARKET",
                api_response=str(e)
            ) from e

    def place_tp_sl_orders(self, contract_id: str, side: int, quantity: int,
                          fill_price: float, tp_points: float, sl_points: float,
                          tick_size: float, tag_prefix: str,
                          linked_order_id: Optional[int] = None) -> dict[str, Any]:
        """
        Place Take Profit and Stop Loss orders.

        Args:
            contract_id: Contract ID
            side: Entry order side
            quantity: Order quantity
            fill_price: Fill price of entry order
            tp_points: Take profit points
            sl_points: Stop loss points
            tick_size: Tick size for the contract
            tag_prefix: Tag prefix for the orders
            linked_order_id: Optional ID of the parent order to link to

        Returns:
            Dictionary with TP/SL order details

        Raises:
            OrderPlacementError: If order placement fails
        """
        result = {
            "tp_order_id": None,
            "sl_order_id": None,
            "tp_price": None,
            "sl_price": None,
            "success": False,
            "error": None
        }

        # Calculate TP/SL prices
        tp_price = calculate_tp_price(fill_price, tp_points, side, tick_size)
        sl_price = calculate_sl_price(fill_price, sl_points, side, tick_size)

        # Get exit sides
        tp_side, sl_side = calculate_tp_sl_sides(side)

        result["tp_price"] = tp_price
        result["sl_price"] = sl_price

        try:
            # Place Take Profit (Limit order)
            tp_tag = f"{tag_prefix}-TP"
            tp_response = self.api_client.place_order(
                account_id=self.account_id,
                contract_id=contract_id,
                side=tp_side,
                size=quantity,
                order_type=OrderType.LIMIT,
                limit_price=tp_price,
                linked_order_id=linked_order_id,
                customTag=tp_tag
            )
            result["tp_order_id"] = tp_response.get("orderId")

            # Place Stop Loss (Stop order)
            sl_tag = f"{tag_prefix}-SL"
            sl_response = self.api_client.place_order(
                account_id=self.account_id,
                contract_id=contract_id,
                side=sl_side,
                size=quantity,
                order_type=OrderType.STOP,
                stop_price=sl_price,
                linked_order_id=linked_order_id,
                customTag=sl_tag
            )
            result["sl_order_id"] = sl_response.get("orderId")

            result["success"] = True
            return result
        except Exception as e:
            result["error"] = str(e)
            raise OrderPlacementError(
                f"Failed to place TP/SL orders: {e}",
                order_type="TP/SL",
                api_response=str(e)
            ) from e

    def place_bracket_order(self, contract_id: str, side: int, quantity: int,
                           tp_points: float, sl_points: float, tick_size: float,
                           custom_tag: Optional[str] = None) -> dict[str, Any]:
        """
        Place a bracket order (market + TP/SL in single API call).

        Args:
            contract_id: Contract ID
            side: Order side (BUY or SELL)
            quantity: Order quantity
            tp_points: Take profit points
            sl_points: Stop loss points
            tick_size: Tick size for the contract
            custom_tag: Optional custom tag

        Returns:
            Dictionary with order details

        Raises:
            OrderPlacementError: If order placement fails
            DuplicateOrderError: If duplicate order exists
        """
        result = {
            "order_id": None,
            "success": False,
            "error": None
        }

        # Check for duplicates
        if custom_tag:
            if self.check_existing_orders_by_tag(custom_tag):
                raise DuplicateOrderError(custom_tag)

        # Calculate bracket ticks with correct signs
        tp_ticks, sl_ticks = calculate_bracket_ticks(tp_points, sl_points, side, tick_size)

        try:
            response = self.api_client.place_bracket_order(
                account_id=self.account_id,
                contract_id=contract_id,
                side=side,
                size=quantity,
                tp_ticks=tp_ticks,
                sl_ticks=sl_ticks,
                customTag=custom_tag
            )

            result["order_id"] = response.get("orderId")
            result["success"] = True

            return result
        except Exception as e:
            result["error"] = str(e)
            raise OrderPlacementError(
                f"Failed to place bracket order: {e}",
                order_type="BRACKET",
                api_response=str(e)
            ) from e

    def place_market_and_brackets(self, contract_id: str, side: int, quantity: int,
                                 tp_points: float, sl_points: float, tick_size: float,
                                 tag_prefix: str, wait_for_fill: bool = True) -> dict[str, Any]:
        """
        Place a market order and then TP/SL orders (separate API calls).

        Args:
            contract_id: Contract ID
            side: Order side (BUY or SELL)
            quantity: Order quantity
            tp_points: Take profit points
            sl_points: Stop loss points
            tick_size: Tick size for the contract
            tag_prefix: Tag prefix for the orders
            wait_for_fill: Wait for market order fill before placing TP/SL

        Returns:
            Dictionary with all order details

        Raises:
            OrderPlacementError: If order placement fails
        """
        result = {
            "order_id": None,
            "fill_price": None,
            "tp_order_id": None,
            "sl_order_id": None,
            "tp_price": None,
            "sl_price": None,
            "success": False,
            "error": None
        }

        try:
            # Place market order
            market_result = self.place_market_order(
                contract_id=contract_id,
                side=side,
                quantity=quantity,
                custom_tag=tag_prefix
            )
            result["order_id"] = market_result["order_id"]

            if not result["order_id"]:
                raise OrderPlacementError("Market order ID not returned")

            # Wait for fill if requested
            if wait_for_fill:
                time.sleep(1)  # Brief pause
                fill_price = self.poll_fill_price(contract_id, max_wait_sec=10)

                if not fill_price:
                    print("[ORDER_MANAGER][WARN] Could not confirm fill price")
                    result["error"] = "no_fill_price"
                    return result

                result["fill_price"] = fill_price

                # Place TP/SL orders
                tp_sl_result = self.place_tp_sl_orders(
                    contract_id=contract_id,
                    side=side,
                    quantity=quantity,
                    fill_price=fill_price,
                    tp_points=tp_points,
                    sl_points=sl_points,
                    tick_size=tick_size,
                    tag_prefix=tag_prefix,
                    linked_order_id=result["order_id"]
                )

                result.update(tp_sl_result)

            result["success"] = True
            return result
        except (OrderPlacementError, DuplicateOrderError):
            raise
        except Exception as e:
            result["error"] = str(e)
            raise OrderPlacementError(
                f"Failed to place market and brackets: {e}",
                api_response=str(e)
            ) from e

    def close_position(self, contract_id: str, entry_side: int, quantity: int,
                      custom_tag: Optional[str] = None) -> dict[str, Any]:
        """
        Close a position by placing an opposing market order.

        Args:
            contract_id: Contract ID
            entry_side: Original entry side (will place opposite)
            quantity: Order quantity
            custom_tag: Optional custom tag

        Returns:
            Dictionary with order details
        """
        # Opposite side to close
        close_side = OrderSide.opposite(entry_side)

        return self.place_market_order(
            contract_id=contract_id,
            side=close_side,
            quantity=quantity,
            custom_tag=custom_tag
        )

    def get_open_orders(self, contract_id: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Get all open orders, optionally filtered by contract.

        Args:
            contract_id: Optional contract ID to filter by

        Returns:
            List of open orders
        """
        try:
            orders = self.api_client.search_open_orders(self.account_id)

            if contract_id:
                return [o for o in orders if o.get("contractId") == contract_id]

            return orders
        except Exception as e:
            print(f"[ORDER_MANAGER][WARN] Failed to get open orders: {e}")
            return []

    def verify_orders(self, tag_prefix: str, expected_count: Optional[int] = None) -> bool:
        """
        Verify that orders were created correctly.

        Args:
            tag_prefix: Tag prefix to search for
            expected_count: Expected number of orders (None = any count > 0)

        Returns:
            True if verification passed, False otherwise
        """
        orders = self.check_existing_orders_by_tag(tag_prefix)

        if expected_count is not None:
            return len(orders) == expected_count

        return len(orders) > 0
