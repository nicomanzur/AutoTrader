"""
Logging utilities for TraderDesk V2.

This module provides structured logging with different levels and formats.
"""
from __future__ import annotations
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone


class ColoredFormatter(logging.Formatter):
    """Formatter that adds color to console output."""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color."""
        if sys.stdout.isatty():  # Only use colors in terminal
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"

        return super().format(record)


def setup_logger(name: str, level: int = logging.INFO,
                log_file: Optional[str] = None,
                use_colors: bool = True) -> logging.Logger:
    """
    Set up a logger with console and optional file output.

    Args:
        name: Logger name
        level: Logging level (e.g., logging.INFO)
        log_file: Optional file path for file logging
        use_colors: Use colored output for console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if use_colors:
        console_format = '%(asctime)s | %(levelname)s | %(message)s'
        console_formatter = ColoredFormatter(
            console_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_format = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        console_formatter = logging.Formatter(
            console_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        # Ensure directory exists
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)

        file_format = '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
        file_formatter = logging.Formatter(
            file_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class TradingLogger:
    """Specialized logger for trading operations."""

    def __init__(self, name: str = "TraderDesk", level: int = logging.INFO,
                 log_file: Optional[str] = None, use_emojis: bool = True):
        """
        Initialize trading logger.

        Args:
            name: Logger name
            level: Logging level
            log_file: Optional log file path
            use_emojis: Use emoji prefixes in messages
        """
        self.logger = setup_logger(name, level, log_file)
        self.use_emojis = use_emojis

    def _format_message(self, emoji: str, message: str) -> str:
        """Format message with optional emoji."""
        if self.use_emojis:
            return f"{emoji} {message}"
        return message

    def info(self, message: str, emoji: str = "ℹ️") -> None:
        """Log info message."""
        self.logger.info(self._format_message(emoji, message))

    def warning(self, message: str, emoji: str = "⚠️") -> None:
        """Log warning message."""
        self.logger.warning(self._format_message(emoji, message))

    def error(self, message: str, emoji: str = "❌") -> None:
        """Log error message."""
        self.logger.error(self._format_message(emoji, message))

    def debug(self, message: str, emoji: str = "🔍") -> None:
        """Log debug message."""
        self.logger.debug(self._format_message(emoji, message))

    def trade(self, symbol: str, signal: str, quantity: int,
             dry_run: bool = False) -> None:
        """Log trade execution."""
        prefix = "[DRY]" if dry_run else "[LIVE]"
        emoji = "🧪" if dry_run else "💰"
        message = f"{prefix} {symbol} {signal} x{quantity}"
        self.logger.info(self._format_message(emoji, message))

    def signal(self, symbol: str, signal_type: str, price: float) -> None:
        """Log trading signal."""
        emoji = "🟢" if signal_type == "LONG" else "🔴"
        message = f"Signal: {symbol} {signal_type} @ {price:.2f}"
        self.logger.info(self._format_message(emoji, message))

    def position(self, symbol: str, action: str, reason: Optional[str] = None) -> None:
        """Log position action."""
        emoji = "📊"
        message = f"Position: {symbol} {action}"
        if reason:
            message += f" - {reason}"
        self.logger.info(self._format_message(emoji, message))

    def api_call(self, endpoint: str, success: bool = True) -> None:
        """Log API call."""
        emoji = "✅" if success else "❌"
        status = "SUCCESS" if success else "FAILED"
        message = f"API {endpoint}: {status}"
        if success:
            self.logger.debug(self._format_message(emoji, message))
        else:
            self.logger.error(self._format_message(emoji, message))

    def startup(self, message: str) -> None:
        """Log startup message."""
        self.logger.info(self._format_message("🚀", message))

    def shutdown(self, message: str) -> None:
        """Log shutdown message."""
        self.logger.info(self._format_message("🛑", message))

    def market_data(self, symbol: str, price: float, ema50: float,
                   ema200: float) -> None:
        """Log market data update."""
        emoji = "📈"
        message = (f"Market: {symbol} Price={price:.2f} "
                  f"EMA50={ema50:.2f} EMA200={ema200:.2f}")
        self.logger.debug(self._format_message(emoji, message))


def log_exception(logger: logging.Logger, exc: Exception,
                 context: Optional[str] = None) -> None:
    """
    Log exception with full traceback.

    Args:
        logger: Logger instance
        exc: Exception to log
        context: Optional context message
    """
    import traceback

    if context:
        logger.error(f"{context}: {exc}")
    else:
        logger.error(f"Exception: {exc}")

    # Log full traceback at debug level
    tb = ''.join(traceback.format_tb(exc.__traceback__))
    logger.debug(f"Traceback:\n{tb}")


def create_performance_logger(log_file: str) -> logging.Logger:
    """
    Create a logger specifically for performance metrics.

    Args:
        log_file: Path to performance log file

    Returns:
        Performance logger instance
    """
    logger = setup_logger('performance', logging.INFO, log_file, use_colors=False)
    return logger


def log_timing(logger: logging.Logger, operation: str,
              start_time: datetime, end_time: Optional[datetime] = None) -> None:
    """
    Log timing information for an operation.

    Args:
        logger: Logger instance
        operation: Operation name
        start_time: Start time
        end_time: End time (defaults to now)
    """
    if end_time is None:
        end_time = datetime.now(timezone.utc)

    duration = (end_time - start_time).total_seconds()
    logger.info(f"[TIMING] {operation}: {duration:.3f}s")


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, logger: logging.Logger, operation: str):
        """
        Initialize performance timer.

        Args:
            logger: Logger instance
            operation: Operation name
        """
        self.logger = logger
        self.operation = operation
        self.start_time: Optional[datetime] = None

    def __enter__(self) -> PerformanceTimer:
        """Start timing."""
        self.start_time = datetime.now(timezone.utc)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End timing and log result."""
        if self.start_time:
            log_timing(self.logger, self.operation, self.start_time)
