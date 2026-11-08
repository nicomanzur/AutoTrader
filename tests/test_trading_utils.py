"""
Unit tests for trading utilities.
"""
from __future__ import annotations
import pytest
from app.utils.trading import (
    round_to_tick,
    points_to_ticks,
    ticks_to_points,
    calculate_tp_price,
    calculate_sl_price,
    calculate_bracket_ticks,
    format_order_side,
    validate_trade_parameters,
)
from app.constants import OrderSide


class TestTickOperations:
    """Tests for tick-related operations."""

    def test_round_to_tick(self):
        """Test price rounding to tick size."""
        assert round_to_tick(100.37, 0.25) == 100.25
        assert round_to_tick(100.38, 0.25) == 100.5
        assert round_to_tick(100.0, 0.25) == 100.0
        assert round_to_tick(100.1, 0.5) == 100.0

    def test_round_to_tick_zero_tick_size(self):
        """Test that zero tick size returns original price."""
        assert round_to_tick(100.37, 0.0) == 100.37

    def test_points_to_ticks(self):
        """Test conversion of points to ticks."""
        assert points_to_ticks(10.0, 0.25) == 40
        assert points_to_ticks(5.0, 0.5) == 10
        assert points_to_ticks(1.0, 1.0) == 1
        assert points_to_ticks(2.5, 0.25) == 10

    def test_ticks_to_points(self):
        """Test conversion of ticks to points."""
        assert ticks_to_points(40, 0.25) == 10.0
        assert ticks_to_points(10, 0.5) == 5.0
        assert ticks_to_points(1, 1.0) == 1.0


class TestTPSLCalculations:
    """Tests for TP/SL calculations."""

    def test_calculate_tp_price_long(self):
        """Test TP calculation for LONG position."""
        tp_price = calculate_tp_price(100.0, 10.0, OrderSide.BUY, 0.25)
        assert tp_price == 110.0

    def test_calculate_tp_price_short(self):
        """Test TP calculation for SHORT position."""
        tp_price = calculate_tp_price(100.0, 10.0, OrderSide.SELL, 0.25)
        assert tp_price == 90.0

    def test_calculate_sl_price_long(self):
        """Test SL calculation for LONG position."""
        sl_price = calculate_sl_price(100.0, 5.0, OrderSide.BUY, 0.25)
        assert sl_price == 95.0

    def test_calculate_sl_price_short(self):
        """Test SL calculation for SHORT position."""
        sl_price = calculate_sl_price(100.0, 5.0, OrderSide.SELL, 0.25)
        assert sl_price == 105.0

    def test_calculate_bracket_ticks_long(self):
        """Test bracket ticks for LONG position."""
        tp_ticks, sl_ticks = calculate_bracket_ticks(10.0, 5.0, OrderSide.BUY, 0.25)
        assert tp_ticks == 40   # Positive (above)
        assert sl_ticks == -20  # Negative (below)

    def test_calculate_bracket_ticks_short(self):
        """Test bracket ticks for SHORT position."""
        tp_ticks, sl_ticks = calculate_bracket_ticks(10.0, 5.0, OrderSide.SELL, 0.25)
        assert tp_ticks == -40  # Negative (below)
        assert sl_ticks == 20   # Positive (above)


class TestValidation:
    """Tests for trade parameter validation."""

    def test_validate_trade_parameters_valid(self):
        """Test validation with valid parameters."""
        # Should not raise any exception
        validate_trade_parameters("MNQ", OrderSide.BUY, 1, 60.0, 30.0)

    def test_validate_trade_parameters_invalid_symbol(self):
        """Test validation with empty symbol."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            validate_trade_parameters("", OrderSide.BUY, 1, 60.0, 30.0)

    def test_validate_trade_parameters_invalid_side(self):
        """Test validation with invalid side."""
        with pytest.raises(ValueError, match="Invalid side"):
            validate_trade_parameters("MNQ", 99, 1, 60.0, 30.0)

    def test_validate_trade_parameters_invalid_quantity(self):
        """Test validation with invalid quantity."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            validate_trade_parameters("MNQ", OrderSide.BUY, 0, 60.0, 30.0)

    def test_validate_trade_parameters_invalid_tp(self):
        """Test validation with invalid TP."""
        with pytest.raises(ValueError, match="Take profit points must be positive"):
            validate_trade_parameters("MNQ", OrderSide.BUY, 1, 0.0, 30.0)

    def test_validate_trade_parameters_invalid_sl(self):
        """Test validation with invalid SL."""
        with pytest.raises(ValueError, match="Stop loss points must be positive"):
            validate_trade_parameters("MNQ", OrderSide.BUY, 1, 60.0, 0.0)


class TestFormatting:
    """Tests for formatting functions."""

    def test_format_order_side(self):
        """Test order side formatting."""
        assert format_order_side(OrderSide.BUY) == "BUY"
        assert format_order_side(OrderSide.SELL) == "SELL"
