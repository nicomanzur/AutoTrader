"""
Trading utilities for TraderDesk V2.

This module provides trading-related utility functions for price calculations,
tick rounding, account selection, and other trading operations.
"""
from __future__ import annotations
from typing import Optional, Any
from app.constants import OrderSide, DEFAULT_TICK_SIZE


def round_to_tick(price: float, tick_size: float) -> float:
    """
    Round price to nearest tick size.

    Args:
        price: Price to round
        tick_size: Tick size for the instrument

    Returns:
        Price rounded to nearest tick

    Example:
        >>> round_to_tick(100.37, 0.25)
        100.25
    """
    if tick_size <= 0:
        return price
    return round(round(price / tick_size) * tick_size, 10)


def points_to_ticks(points: float, tick_size: float) -> int:
    """
    Convert points to number of ticks.

    Args:
        points: Price points
        tick_size: Tick size for the instrument

    Returns:
        Number of ticks

    Example:
        >>> points_to_ticks(10.0, 0.25)
        40
    """
    if tick_size <= 0:
        return 0
    return int(round(points / tick_size))


def ticks_to_points(ticks: int, tick_size: float) -> float:
    """
    Convert number of ticks to points.

    Args:
        ticks: Number of ticks
        tick_size: Tick size for the instrument

    Returns:
        Price points

    Example:
        >>> ticks_to_points(40, 0.25)
        10.0
    """
    return ticks * tick_size


def calculate_tp_price(fill_price: float, tp_points: float, side: int,
                       tick_size: float) -> float:
    """
    Calculate take profit price.

    Args:
        fill_price: Fill price of the entry order
        tp_points: Take profit points
        side: Order side (BUY or SELL)
        tick_size: Tick size for the instrument

    Returns:
        Take profit price rounded to tick
    """
    if side == OrderSide.BUY:
        tp_price = fill_price + tp_points
    else:  # SELL
        tp_price = fill_price - tp_points

    return round_to_tick(tp_price, tick_size)


def calculate_sl_price(fill_price: float, sl_points: float, side: int,
                       tick_size: float) -> float:
    """
    Calculate stop loss price.

    Args:
        fill_price: Fill price of the entry order
        sl_points: Stop loss points
        side: Order side (BUY or SELL)
        tick_size: Tick size for the instrument

    Returns:
        Stop loss price rounded to tick
    """
    if side == OrderSide.BUY:
        sl_price = fill_price - sl_points
    else:  # SELL
        sl_price = fill_price + sl_points

    return round_to_tick(sl_price, tick_size)


def calculate_tp_sl_sides(entry_side: int) -> tuple[int, int]:
    """
    Calculate the order sides for TP and SL orders.

    For LONG positions, TP and SL are SELL orders.
    For SHORT positions, TP and SL are BUY orders.

    Args:
        entry_side: Entry order side (BUY or SELL)

    Returns:
        Tuple of (tp_side, sl_side)
    """
    exit_side = OrderSide.opposite(entry_side)
    return (exit_side, exit_side)


def calculate_bracket_ticks(tp_points: float, sl_points: float, side: int,
                            tick_size: float) -> tuple[int, int]:
    """
    Calculate TP/SL ticks for bracket orders with correct signs.

    For LONG (BUY): TP is positive (above), SL is negative (below)
    For SHORT (SELL): TP is negative (below), SL is positive (above)

    Args:
        tp_points: Take profit points
        sl_points: Stop loss points
        side: Order side (BUY or SELL)
        tick_size: Tick size for the instrument

    Returns:
        Tuple of (tp_ticks, sl_ticks) with correct signs
    """
    tp_ticks_base = points_to_ticks(tp_points, tick_size)
    sl_ticks_base = points_to_ticks(sl_points, tick_size)

    if side == OrderSide.BUY:
        # LONG: TP positive (above), SL negative (below)
        return (tp_ticks_base, -sl_ticks_base)
    else:
        # SHORT: TP negative (below), SL positive (above)
        return (-tp_ticks_base, sl_ticks_base)


def get_tick_size_from_contract(api_client: Any, contract_id: str,
                                default: float = DEFAULT_TICK_SIZE) -> float:
    """
    Get tick size for a contract from the API.

    Args:
        api_client: ProjectX API client instance
        contract_id: Contract identifier
        default: Default tick size if retrieval fails

    Returns:
        Tick size for the contract
    """
    try:
        contracts = api_client.search_contracts_by_id(contract_id)
        if contracts and len(contracts) > 0:
            tick_size = contracts[0].get("tickSize")
            if tick_size is not None:
                return float(tick_size)
    except Exception as e:
        print(f"[WARN] Failed to get tick size for {contract_id}: {e}")

    return default


def pick_practice_account(api_client: Any, explicit_id: Optional[int] = None) -> int:
    """
    Select a practice account for trading.

    Prefers PRACTICE accounts, falls back to any tradeable account.

    Args:
        api_client: ProjectX API client instance
        explicit_id: Explicit account ID to use (overrides selection)

    Returns:
        Account ID to use for trading

    Raises:
        RuntimeError: If no suitable account is found
    """
    # Use explicit ID if provided
    if explicit_id is not None:
        return int(explicit_id)

    # Search for accounts
    accounts = api_client.search_accounts(only_active=True)

    # First pass: look for PRACTICE accounts
    for account in accounts:
        name = str(account.get("name", "")).upper()
        if "PRACTICE" in name:
            return int(account["id"])

    # Second pass: look for any tradeable account
    for account in accounts:
        if account.get("canTrade"):
            return int(account["id"])

    raise RuntimeError("No PRACTICE or tradeable account found")


def validate_trade_parameters(symbol: str, side: int, quantity: int,
                              tp_points: float, sl_points: float) -> None:
    """
    Validate trade parameters before placing orders.

    Args:
        symbol: Trading symbol
        side: Order side
        quantity: Order quantity
        tp_points: Take profit points
        sl_points: Stop loss points

    Raises:
        ValueError: If any parameter is invalid
    """
    if not symbol:
        raise ValueError("Symbol cannot be empty")

    if side not in (OrderSide.BUY, OrderSide.SELL):
        raise ValueError(f"Invalid side: {side}. Must be {OrderSide.BUY} (BUY) or {OrderSide.SELL} (SELL)")

    if quantity <= 0:
        raise ValueError(f"Quantity must be positive: {quantity}")

    if tp_points <= 0:
        raise ValueError(f"Take profit points must be positive: {tp_points}")

    if sl_points <= 0:
        raise ValueError(f"Stop loss points must be positive: {sl_points}")


def format_order_side(side: int) -> str:
    """
    Format order side as human-readable string.

    Args:
        side: Order side (0=BUY, 1=SELL)

    Returns:
        Formatted string ("BUY" or "SELL")
    """
    return OrderSide.to_string(side)


def calculate_pnl(entry_price: float, exit_price: float, side: int,
                  quantity: int, tick_value: float = 1.0) -> float:
    """
    Calculate profit/loss for a trade.

    Args:
        entry_price: Entry price
        exit_price: Exit price
        side: Order side (BUY or SELL)
        quantity: Number of contracts
        tick_value: Value per tick (default: 1.0)

    Returns:
        P&L in dollars (positive = profit, negative = loss)
    """
    if side == OrderSide.BUY:
        points = exit_price - entry_price
    else:  # SELL
        points = entry_price - exit_price

    return points * quantity * tick_value


def should_close_long_position(current_price: float, tp_price: Optional[float],
                               sl_price: Optional[float]) -> tuple[bool, str]:
    """
    Check if a LONG position should be closed.

    Args:
        current_price: Current market price
        tp_price: Take profit price (None if not set)
        sl_price: Stop loss price (None if not set)

    Returns:
        Tuple of (should_close, reason)
    """
    if tp_price is not None and current_price >= tp_price:
        return (True, f"TP hit: {current_price} >= {tp_price}")

    if sl_price is not None and current_price <= sl_price:
        return (True, f"SL hit: {current_price} <= {sl_price}")

    return (False, "")


def should_close_short_position(current_price: float, tp_price: Optional[float],
                                sl_price: Optional[float]) -> tuple[bool, str]:
    """
    Check if a SHORT position should be closed.

    Args:
        current_price: Current market price
        tp_price: Take profit price (None if not set)
        sl_price: Stop loss price (None if not set)

    Returns:
        Tuple of (should_close, reason)
    """
    if tp_price is not None and current_price <= tp_price:
        return (True, f"TP hit: {current_price} <= {tp_price}")

    if sl_price is not None and current_price >= sl_price:
        return (True, f"SL hit: {current_price} >= {sl_price}")

    return (False, "")
