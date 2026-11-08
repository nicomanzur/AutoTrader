"""
Configuration module for TraderDesk V2.

This module centralizes all environment variable loading and provides
type-safe, validated configuration objects for the application.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

from app.constants import (
    DEFAULT_BAR_MINUTES,
    DEFAULT_REQUIRED_BARS,
    DEFAULT_WARMUP_BARS,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_TICK_SIZE,
    DEFAULT_CLOSE_LAG_SEC,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_INTERVAL,
    DEFAULT_ACTIVE_MONITOR_INTERVAL,
    DEFAULT_REALTIME_STATUS_INTERVAL,
    DEFAULT_MAX_ACTIVE_POSITIONS,
    DEFAULT_MAX_POSITIONS_PER_SYMBOL,
    DEFAULT_RTH_START,
    DEFAULT_RTH_END,
    SESSION_ETH,
    BarTimestampMode,
    TradingMode,
    OrderPlacementMode,
)

# Load environment variables
load_dotenv()


def _get_bool_env(key: str, default: str = "false") -> bool:
    """Get boolean value from environment variable."""
    return os.getenv(key, default).lower() in ("1", "true", "yes")


def _get_int_env(key: str, default: int) -> int:
    """Get integer value from environment variable."""
    return int(os.getenv(key, str(default)))


def _get_float_env(key: str, default: float) -> float:
    """Get float value from environment variable."""
    return float(os.getenv(key, str(default)))


def _get_str_env(key: str, default: str = "") -> str:
    """Get string value from environment variable."""
    return os.getenv(key, default).strip()


@dataclass
class APIConfig:
    """API configuration."""
    base_url: str = field(default_factory=lambda: _get_str_env("PROJECTX_API_BASE", "https://api.topstepx.com"))
    username: str = field(default_factory=lambda: _get_str_env("PROJECTX_USER"))
    api_key: str = field(default_factory=lambda: _get_str_env("PROJECTX_API_KEY"))

    def validate(self) -> None:
        """Validate API configuration."""
        if not self.username:
            raise ValueError("PROJECTX_USER environment variable is required")
        if not self.api_key:
            raise ValueError("PROJECTX_API_KEY environment variable is required")


@dataclass
class TradingConfig:
    """Trading configuration."""
    dry_run: bool = field(default_factory=lambda: _get_bool_env("DRY_RUN", "true"))
    mode: str = field(default_factory=lambda: _get_str_env("TRADING_MODE", TradingMode.DRY_RUN))

    # Account
    practice_account_id: Optional[int] = field(default_factory=lambda: int(_get_str_env("PRACTICE_ACCOUNT_ID")) if _get_str_env("PRACTICE_ACCOUNT_ID") else None)

    # Order sizes by symbol
    order_size_mnq: int = field(default_factory=lambda: _get_int_env("ORDER_SIZE_MNQ", _get_int_env("ORDER_SIZE", 1)))
    order_size_es: int = field(default_factory=lambda: _get_int_env("ORDER_SIZE_ES", _get_int_env("ORDER_SIZE", 1)))

    # Take profit points by symbol
    tp_points_mnq: float = field(default_factory=lambda: _get_float_env("TP_POINTS_MNQ", 60.0))
    tp_points_es: float = field(default_factory=lambda: _get_float_env("TP_POINTS_ES", 8.0))

    # Stop loss points by symbol
    sl_points_mnq: float = field(default_factory=lambda: _get_float_env("SL_POINTS_MNQ", 30.0))
    sl_points_es: float = field(default_factory=lambda: _get_float_env("SL_POINTS_ES", 4.0))

    # Order placement mode
    order_placement_mode: str = field(default_factory=lambda: _get_str_env("ORDER_PLACEMENT_MODE", OrderPlacementMode.BRACKET))

    # Position limits
    max_active_positions: int = field(default_factory=lambda: _get_int_env("MAX_ACTIVE_POSITIONS", DEFAULT_MAX_ACTIVE_POSITIONS))
    max_positions_per_symbol: int = field(default_factory=lambda: _get_int_env("MAX_POSITIONS_PER_SYMBOL", DEFAULT_MAX_POSITIONS_PER_SYMBOL))

    # Signal processing
    process_signals_while_active: bool = field(default_factory=lambda: _get_bool_env("PROCESS_SIGNALS_WHILE_ACTIVE", "false"))

    def get_order_size(self, symbol: str) -> int:
        """Get order size for a symbol."""
        if symbol.upper() == "MNQ":
            return self.order_size_mnq
        elif symbol.upper() == "ES":
            return self.order_size_es
        return 1

    def get_tp_points(self, symbol: str) -> float:
        """Get take profit points for a symbol."""
        if symbol.upper() == "MNQ":
            return self.tp_points_mnq
        elif symbol.upper() == "ES":
            return self.tp_points_es
        return 0.0

    def get_sl_points(self, symbol: str) -> float:
        """Get stop loss points for a symbol."""
        if symbol.upper() == "MNQ":
            return self.sl_points_mnq
        elif symbol.upper() == "ES":
            return self.sl_points_es
        return 0.0


@dataclass
class TimingConfig:
    """Timing and scheduling configuration."""
    bar_minutes: int = field(default_factory=lambda: _get_int_env("BAR_MINUTES", DEFAULT_BAR_MINUTES))
    bar_timestamp_mode: str = field(default_factory=lambda: _get_str_env("BAR_TIMESTAMP_MODE", BarTimestampMode.OPEN))
    align_timezone: str = field(default_factory=lambda: _get_str_env("ALIGN_TIMEZONE", "UTC"))

    close_lag_sec: float = field(default_factory=lambda: _get_float_env("CLOSE_LAG_SEC", DEFAULT_CLOSE_LAG_SEC))
    retry_count: int = field(default_factory=lambda: _get_int_env("CLOSE_RETRY_COUNT", DEFAULT_RETRY_COUNT))
    retry_interval: float = field(default_factory=lambda: _get_float_env("CLOSE_RETRY_INTERVAL", DEFAULT_RETRY_INTERVAL))

    active_monitor_interval: int = field(default_factory=lambda: _get_int_env("ACTIVE_MONITOR_INTERVAL", DEFAULT_ACTIVE_MONITOR_INTERVAL))

    show_realtime_status: bool = field(default_factory=lambda: _get_bool_env("SHOW_REALTIME_STATUS", "false"))
    realtime_status_interval: int = field(default_factory=lambda: _get_int_env("REALTIME_STATUS_INTERVAL", DEFAULT_REALTIME_STATUS_INTERVAL))


@dataclass
class MarketDataConfig:
    """Market data configuration."""
    required_bars: int = field(default_factory=lambda: _get_int_env("REQUIRED_BARS", DEFAULT_REQUIRED_BARS))
    warmup_bars: int = field(default_factory=lambda: _get_int_env("WARMUP_BARS", DEFAULT_WARMUP_BARS))
    lookback_days: int = field(default_factory=lambda: _get_int_env("BARS_LOOKBACK_DAYS", DEFAULT_LOOKBACK_DAYS))

    force_live: bool = field(default_factory=lambda: _get_bool_env("FORCE_LIVE", "false"))
    include_partial_bars: bool = field(default_factory=lambda: _get_bool_env("INCLUDE_PARTIAL_BARS", "false"))

    # Session
    chart_session: str = field(default_factory=lambda: _get_str_env("CHART_SESSION", SESSION_ETH))
    rth_start: str = field(default_factory=lambda: _get_str_env("RTH_START", DEFAULT_RTH_START))
    rth_end: str = field(default_factory=lambda: _get_str_env("RTH_END", DEFAULT_RTH_END))

    # EMA settings
    exact_match_on_close: bool = field(default_factory=lambda: _get_bool_env("EXACT_MATCH_ON_CLOSE", "true"))
    ema_cross_eps: float = field(default_factory=lambda: _get_float_env("EMA_CROSS_EPS", 0.0))
    ema200_smooth_type: str = field(default_factory=lambda: _get_str_env("EMA200_SMOOTH_TYPE", ""))
    ema200_smooth_length: int = field(default_factory=lambda: _get_int_env("EMA200_SMOOTH_LENGTH", 9))

    # Contract IDs
    contract_id_mnq: str = field(default_factory=lambda: _get_str_env("CONTRACT_ID_MNQ") or _get_str_env("CONTRACT_ID_NQ"))
    contract_id_es: str = field(default_factory=lambda: _get_str_env("CONTRACT_ID_ES"))


@dataclass
class NotificationConfig:
    """Notification configuration."""
    # Telegram
    use_telegram: bool = field(default_factory=lambda: _get_bool_env("NOTIFY_TELEGRAM", "false"))
    telegram_token: str = field(default_factory=lambda: _get_str_env("TELEGRAM_BOT_TOKEN"))
    telegram_chat_id: str = field(default_factory=lambda: _get_str_env("TELEGRAM_CHAT_ID"))

    # Email
    use_email: bool = field(default_factory=lambda: _get_bool_env("NOTIFY_EMAIL", "false"))
    smtp_host: str = field(default_factory=lambda: _get_str_env("SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: _get_int_env("SMTP_PORT", 0))
    smtp_user: str = field(default_factory=lambda: _get_str_env("SMTP_USER"))
    smtp_pass: str = field(default_factory=lambda: _get_str_env("SMTP_PASS"))
    email_from: str = field(default_factory=lambda: _get_str_env("EMAIL_FROM") or _get_str_env("SMTP_USER"))
    email_to: str = field(default_factory=lambda: _get_str_env("EMAIL_TO"))

    notify_on_dry_run: bool = field(default_factory=lambda: _get_bool_env("NOTIFY_ON_DRY_RUN", "false"))

    def is_telegram_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return self.use_telegram and bool(self.telegram_token) and bool(self.telegram_chat_id)

    def is_email_configured(self) -> bool:
        """Check if Email is properly configured."""
        return (self.use_email and bool(self.smtp_host) and
                self.smtp_port > 0 and bool(self.smtp_user) and
                bool(self.smtp_pass) and bool(self.email_to) and bool(self.email_from))


@dataclass
class LoggingConfig:
    """Logging configuration."""
    trades_log: str = field(default_factory=lambda: _get_str_env("TRADES_LOG", "trades.log"))
    seen_signals_file: str = field(default_factory=lambda: _get_str_env("SEEN_SIGNALS_FILE", "seen_signals.json"))
    debug_trade: bool = field(default_factory=lambda: _get_bool_env("DEBUG_TRADE", "false"))
    debug_trader: bool = field(default_factory=lambda: _get_bool_env("DEBUG_TRADER", "false"))


@dataclass
class SystemConfig:
    """System-wide configuration."""
    run_symbols: list[str] = field(default_factory=lambda: [s.strip().upper() for s in _get_str_env("RUN_SYMBOLS", "MNQ,ES").split(",") if s.strip()])
    use_emojis: bool = field(default_factory=lambda: _get_bool_env("USE_EMOJIS", "true"))


@dataclass
class Config:
    """Main configuration container."""
    api: APIConfig = field(default_factory=APIConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    system: SystemConfig = field(default_factory=SystemConfig)

    def validate(self) -> None:
        """Validate all configuration."""
        self.api.validate()

        # Validate timing
        if self.timing.bar_minutes <= 0:
            raise ValueError("BAR_MINUTES must be positive")

        # Validate trading
        if self.trading.max_active_positions < 0:
            raise ValueError("MAX_ACTIVE_POSITIONS cannot be negative")
        if self.trading.max_positions_per_symbol < 0:
            raise ValueError("MAX_POSITIONS_PER_SYMBOL cannot be negative")

        # Validate symbols
        if not self.system.run_symbols:
            raise ValueError("RUN_SYMBOLS cannot be empty")


# Global configuration instance
def load_config() -> Config:
    """Load and validate configuration from environment."""
    config = Config()
    config.validate()
    return config


# Convenience function for backward compatibility
def get_config() -> Config:
    """Get configuration instance."""
    return load_config()
