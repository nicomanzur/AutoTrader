"""
Constants module for TraderDesk V2.

This module contains all constant values used throughout the application,
including order types, sides, statuses, and other magic numbers.
"""
from __future__ import annotations


class OrderType:
    """Order type constants for ProjectX API."""
    LIMIT = 1
    MARKET = 2
    STOP = 4
    TRAILING_STOP = 5
    JOIN_BID = 6
    JOIN_ASK = 7


class OrderSide:
    """Order side constants for ProjectX API."""
    BUY = 0
    SELL = 1

    @staticmethod
    def to_string(side: int) -> str:
        """Convert numeric side to string representation."""
        return "BUY" if side == OrderSide.BUY else "SELL"

    @staticmethod
    def opposite(side: int) -> int:
        """Get the opposite side for closing positions."""
        return OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY


class OrderStatus:
    """Order status constants from ProjectX API."""
    WORKING = "Working"
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"

    # Active statuses - orders that are still working
    ACTIVE_STATUSES = frozenset([WORKING, PENDING, ACCEPTED, FILLED])


class SignalType:
    """Trading signal types."""
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = None


class MarketColor:
    """Market color indicators for EMA zones."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GRAY = "gray"


class BarUnit:
    """Bar unit types for historical data."""
    TICK = 1
    MINUTE = 2
    HOUR = 3
    DAY = 4


class BarTimestampMode:
    """Bar timestamp modes - whether bar is labeled by open or close time."""
    OPEN = "open"
    CLOSE = "close"


class TradingMode:
    """Trading mode constants."""
    DRY_RUN = "dry"
    LIVE = "live"


class SystemMode:
    """System operation modes."""
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"


class OrderPlacementMode:
    """Order placement strategies."""
    BRACKET = "bracket"  # Single API call with TP/SL
    SEPARATE = "separate"  # Separate market + TP/SL calls


# Default values
DEFAULT_BAR_MINUTES = 15
DEFAULT_REQUIRED_BARS = 205
DEFAULT_WARMUP_BARS = 1000
DEFAULT_LOOKBACK_DAYS = 14
DEFAULT_TICK_SIZE = 0.25

# Timing defaults
DEFAULT_CLOSE_LAG_SEC = 1.2
DEFAULT_RETRY_COUNT = 15
DEFAULT_RETRY_INTERVAL = 0.5
DEFAULT_ACTIVE_MONITOR_INTERVAL = 5
DEFAULT_REALTIME_STATUS_INTERVAL = 60

# Position limits
DEFAULT_MAX_ACTIVE_POSITIONS = 1
DEFAULT_MAX_POSITIONS_PER_SYMBOL = 1

# Contract identifiers
CONTRACT_PREFIX = "CON."

# RTH (Regular Trading Hours) defaults
DEFAULT_RTH_START = "09:30"
DEFAULT_RTH_END = "16:15"

# Chart session types
SESSION_ETH = "ETH"  # Extended Trading Hours
SESSION_RTH = "RTH"  # Regular Trading Hours

# Emoji flags
EMOJI_ROCKET = "🚀"
EMOJI_CHART_UP = "📈"
EMOJI_CHART_DOWN = "📉"
EMOJI_GREEN_CIRCLE = "🟢"
EMOJI_RED_CIRCLE = "🔴"
EMOJI_YELLOW_CIRCLE = "🟡"
EMOJI_WHITE_CIRCLE = "⚪"
EMOJI_WARNING = "⚠️"
EMOJI_CHECK = "✅"
EMOJI_CROSS = "❌"
EMOJI_STOP = "🛑"
EMOJI_LOCK = "🔒"
EMOJI_MAGNIFIER = "🔍"
EMOJI_LIGHTNING = "⚡"
