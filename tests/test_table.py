"""Tests for mahjong_sim.table module."""

import numpy as np
import pytest
from mahjong_sim.real_mc import (
    simulate_table,
    simulate_custom_table
)
from mahjong_sim.strategies import defensive_strategy, aggressive_strategy
from mahjong_sim.players import NeutralPolicy


# Note: adjust_risk_for_composition and adjust_fan_growth_for_composition
# functions were removed as they were not part of the core simulation logic.


def test_simulate_table_basic():
    """Test simulate_table with basic composition."""
    cfg = {
        "base_points": 1,
        "fan_min": 1,
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10
    }
    
    # Test composition 2 (2 DEF, 2 AGG)
    result = simulate_table(composition=2, cfg=cfg)
    
    assert "defensive" in result
    assert "aggressive" in result
    assert "dealer" in result
    assert "non_dealer" in result
    assert "per_player" in result


def test_simulate_table_all_def():
    """Test simulate_table with all defensive players."""
    cfg = {
        "base_points": 1,
        "fan_min": 1,
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10
    }
    
    result = simulate_table(composition=4, cfg=cfg)  # 4 DEF
    
    assert len(result["defensive"]["profits"]) > 0
    assert len(result["aggressive"]["profits"]) == 0  # No AGG players


def test_simulate_table_all_agg():
    """Test simulate_table with all aggressive players."""
    cfg = {
        "base_points": 1,
        "fan_min": 1,
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10
    }
    
    result = simulate_table(composition=0, cfg=cfg)  # 0 DEF (4 AGG)
    
    assert len(result["defensive"]["profits"]) == 0  # No DEF players
    assert len(result["aggressive"]["profits"]) > 0


def test_simulate_custom_table():
    """Test simulate_custom_table with custom players."""
    cfg = {
        "base_points": 1,
        "fan_min": 1,
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10
    }
    
    players = [
        {"strategy": lambda f: defensive_strategy(f, 1), "strategy_type": "DEF"},
        {"strategy": NeutralPolicy(seed=42), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=43), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=44), "strategy_type": "NEU"}
    ]
    
    result = simulate_custom_table(players, cfg)
    
    assert "defensive" in result
    assert "aggressive" in result
    assert "per_player" in result
    assert len(result["per_player"]) == 4  # 4 players


def test_simulate_table_per_player_stats():
    """Test that per_player stats are correctly structured."""
    cfg = {
        "base_points": 1,
        "fan_min": 1,
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10
    }
    
    result = simulate_table(composition=2, cfg=cfg)
    
    assert len(result["per_player"]) == 4
    for player_stat in result["per_player"]:
        assert "player_index" in player_stat
        assert "strategy_type" in player_stat
        assert "profit" in player_stat
        assert "utility" in player_stat
        assert "win_rate" in player_stat

