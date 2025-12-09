"""Tests for mahjong_sim.strategies module."""

from mahjong_sim.strategies import defensive_strategy, aggressive_strategy


def test_defensive_strategy_accepts_min_fan():
    """Test defensive strategy accepts at minimum fan."""
    assert defensive_strategy(fan=1, fan_min=1) is True
    assert defensive_strategy(fan=2, fan_min=1) is True


def test_defensive_strategy_rejects_below_min():
    """Test defensive strategy rejects below minimum fan."""
    assert defensive_strategy(fan=0, fan_min=1) is False


def test_defensive_strategy_custom_min():
    """Test defensive strategy with custom fan_min."""
    assert defensive_strategy(fan=3, fan_min=3) is True
    assert defensive_strategy(fan=2, fan_min=3) is False


def test_aggressive_strategy_accepts_threshold():
    """Test aggressive strategy accepts at threshold."""
    assert aggressive_strategy(fan=3, threshold=3) is True
    assert aggressive_strategy(fan=4, threshold=3) is True


def test_aggressive_strategy_rejects_below_threshold():
    """Test aggressive strategy rejects below threshold."""
    assert aggressive_strategy(fan=2, threshold=3) is False
    assert aggressive_strategy(fan=1, threshold=3) is False


def test_aggressive_strategy_custom_threshold():
    """Test aggressive strategy with custom threshold."""
    assert aggressive_strategy(fan=5, threshold=5) is True
    assert aggressive_strategy(fan=4, threshold=5) is False


def test_strategies_with_float_fan():
    """Test strategies work with float fan values."""
    assert defensive_strategy(fan=1.5, fan_min=1) is True
    assert aggressive_strategy(fan=3.5, threshold=3) is True

