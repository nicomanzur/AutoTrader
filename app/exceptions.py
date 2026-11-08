"""
Custom exceptions for TraderDesk V2.

This module defines specific exception classes for better error handling
and debugging throughout the application.
"""
from __future__ import annotations
from typing import Optional, Any


class TradingError(Exception):
    """Base exception for all trading-related errors."""

    def __init__(self, message: str, code: Optional[str] = None, details: Optional[dict[str, Any]] = None):
        """
        Initialize trading error.

        Args:
            message: Error message
            code: Optional error code for tracking
            details: Optional dictionary with additional error details
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class APIError(TradingError):
    """Exception for API communication failures."""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 response: Optional[dict[str, Any]] = None):
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response: API response data
        """
        details = {"status_code": status_code, "response": response}
        super().__init__(message, code="API_ERROR", details=details)
        self.status_code = status_code
        self.response = response


class AuthenticationError(APIError):
    """Exception for authentication and token issues."""

    def __init__(self, message: str = "Authentication failed"):
        """Initialize authentication error."""
        super().__init__(message, code="AUTH_ERROR")


class InsufficientDataError(TradingError):
    """Exception when there's not enough historical data."""

    def __init__(self, message: str, required: Optional[int] = None, available: Optional[int] = None):
        """
        Initialize insufficient data error.

        Args:
            message: Error message
            required: Number of bars required
            available: Number of bars available
        """
        details = {"required": required, "available": available}
        super().__init__(message, code="INSUFFICIENT_DATA", details=details)
        self.required = required
        self.available = available


class ContractNotFoundError(TradingError):
    """Exception when contract cannot be resolved."""

    def __init__(self, symbol: str, message: Optional[str] = None):
        """
        Initialize contract not found error.

        Args:
            symbol: Symbol that couldn't be resolved
            message: Optional custom message
        """
        message = message or f"Contract not found for symbol: {symbol}"
        details = {"symbol": symbol}
        super().__init__(message, code="CONTRACT_NOT_FOUND", details=details)
        self.symbol = symbol


class OrderPlacementError(TradingError):
    """Exception for order placement failures."""

    def __init__(self, message: str, order_type: Optional[str] = None,
                 symbol: Optional[str] = None, api_response: Optional[dict[str, Any]] = None):
        """
        Initialize order placement error.

        Args:
            message: Error message
            order_type: Type of order (market, limit, etc.)
            symbol: Symbol for the order
            api_response: API response data
        """
        details = {
            "order_type": order_type,
            "symbol": symbol,
            "api_response": api_response
        }
        super().__init__(message, code="ORDER_PLACEMENT_FAILED", details=details)
        self.order_type = order_type
        self.symbol = symbol
        self.api_response = api_response


class DuplicateOrderError(TradingError):
    """Exception when attempting to place duplicate orders."""

    def __init__(self, tag: str, existing_orders: Optional[list[dict[str, Any]]] = None):
        """
        Initialize duplicate order error.

        Args:
            tag: Order tag that already exists
            existing_orders: List of existing orders with this tag
        """
        message = f"Orders with tag '{tag}' already exist"
        details = {"tag": tag, "existing_orders": existing_orders}
        super().__init__(message, code="DUPLICATE_ORDER", details=details)
        self.tag = tag
        self.existing_orders = existing_orders or []


class PositionLimitError(TradingError):
    """Exception when position limits are exceeded."""

    def __init__(self, message: str, current: Optional[int] = None,
                 limit: Optional[int] = None, symbol: Optional[str] = None):
        """
        Initialize position limit error.

        Args:
            message: Error message
            current: Current number of positions
            limit: Position limit
            symbol: Symbol if limit is per-symbol
        """
        details = {"current": current, "limit": limit, "symbol": symbol}
        super().__init__(message, code="POSITION_LIMIT_EXCEEDED", details=details)
        self.current = current
        self.limit = limit
        self.symbol = symbol


class ConfigurationError(TradingError):
    """Exception for configuration validation failures."""

    def __init__(self, message: str, parameter: Optional[str] = None):
        """
        Initialize configuration error.

        Args:
            message: Error message
            parameter: Parameter name that failed validation
        """
        details = {"parameter": parameter}
        super().__init__(message, code="CONFIG_ERROR", details=details)
        self.parameter = parameter


class DataValidationError(TradingError):
    """Exception for data validation failures."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        """
        Initialize data validation error.

        Args:
            message: Error message
            field: Field name that failed validation
            value: Invalid value
        """
        details = {"field": field, "value": str(value) if value is not None else None}
        super().__init__(message, code="VALIDATION_ERROR", details=details)
        self.field = field
        self.value = value


class MarketDataError(TradingError):
    """Exception for market data retrieval issues."""

    def __init__(self, message: str, symbol: Optional[str] = None,
                 bar_time: Optional[str] = None):
        """
        Initialize market data error.

        Args:
            message: Error message
            symbol: Symbol for which data retrieval failed
            bar_time: Expected bar time
        """
        details = {"symbol": symbol, "bar_time": bar_time}
        super().__init__(message, code="MARKET_DATA_ERROR", details=details)
        self.symbol = symbol
        self.bar_time = bar_time


class SignalProcessingError(TradingError):
    """Exception for signal processing failures."""

    def __init__(self, message: str, symbol: Optional[str] = None,
                 signal_type: Optional[str] = None):
        """
        Initialize signal processing error.

        Args:
            message: Error message
            symbol: Symbol for the signal
            signal_type: Type of signal (LONG/SHORT)
        """
        details = {"symbol": symbol, "signal_type": signal_type}
        super().__init__(message, code="SIGNAL_PROCESSING_ERROR", details=details)
        self.symbol = symbol
        self.signal_type = signal_type
