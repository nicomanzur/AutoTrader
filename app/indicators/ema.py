"""
Exponential Moving Average (EMA) indicator for TraderDesk V2.

This module provides EMA calculation using TA-Lib when available,
with a fallback to pandas implementation.
"""
from __future__ import annotations
from typing import Sequence, Optional, Iterable
import pandas as pd
import numpy as np

try:
    import talib as ta
    HAVE_TALIB = True
except Exception:
    HAVE_TALIB = False


def _to_series(x: Iterable) -> pd.Series:
    """
    Convert iterable to pandas Series with float64 dtype.

    Args:
        x: Iterable of numeric values

    Returns:
        Pandas Series with float64 dtype
    """
    if isinstance(x, pd.Series):
        return pd.Series(x, dtype="float64")
    return pd.Series(list(map(float, x)), dtype="float64")


def ema(series: Sequence[float], period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Uses TA-Lib if available for better performance, otherwise falls
    back to pandas implementation.

    Args:
        series: Sequence of price data
        period: EMA period (e.g., 50, 200)

    Returns:
        Pandas Series with EMA values

    Note:
        First `period` values will be NaN until enough data is available.
    """
    s = _to_series(series)
    if HAVE_TALIB:
        out = ta.EMA(s.to_numpy(dtype="float64"), timeperiod=period)
        return pd.Series(out, index=s.index, dtype="float64")
    # fallback TA-style
    return s.ewm(span=period, adjust=False, min_periods=period).mean()


def exponential_moving_average(data: Sequence[float], period: int) -> Optional[float]:
    """
    Calculate the latest EMA value from a data sequence.

    Convenience function that returns just the most recent EMA value
    instead of the full series.

    Args:
        data: Sequence of price data
        period: EMA period

    Returns:
        Latest EMA value, or None if insufficient data or result is NaN

    Example:
        >>> prices = [100, 101, 102, 103, 104]
        >>> ema_value = exponential_moving_average(prices, 3)
    """
    s = ema(_to_series(data), period)
    if s.empty or pd.isna(s.iloc[-1]):
        return None
    return float(s.iloc[-1])
