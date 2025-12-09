"""Extended tests for mahjong_sim.simulation module."""

import numpy as np
import pytest
from mahjong_sim.real_mc import (
    compute_utility,
    run_simulation,
    run_multiple_trials
)
from mahjong_sim.strategies import defensive_strategy, aggressive_strategy


def test_compute_utility_positive_profit():
    """Test utility computation with positive profit."""
    utility = compute_utility(profit=100.0, missed_hu=False, deal_in_as_loser=False)
    assert utility > 0
    # Current formula: sqrt(profit) * 3
    assert utility == pytest.approx(np.sqrt(100.0) * 3)


def test_compute_utility_negative_profit():
    """Test utility computation with negative profit."""
    utility = compute_utility(profit=-50.0, missed_hu=False, deal_in_as_loser=False)
    assert utility < 0
    # Current formula: -sqrt(abs(profit)) * 3
    assert utility == pytest.approx(-np.sqrt(50.0) * 3)


def test_compute_utility_zero_profit():
    """Test utility computation with zero profit."""
    utility = compute_utility(profit=0.0, missed_hu=False, deal_in_as_loser=False)
    assert utility == 0.0


def test_compute_utility_with_missed_hu():
    """Test utility computation with missed Hu penalty."""
    utility_with_penalty = compute_utility(
        profit=100.0, missed_hu=True, deal_in_as_loser=False
    )
    utility_without_penalty = compute_utility(
        profit=100.0, missed_hu=False, deal_in_as_loser=False
    )
    assert utility_with_penalty < utility_without_penalty
    # Penalty is 0.2
    assert utility_with_penalty == pytest.approx(utility_without_penalty - 0.2, abs=0.01)


def test_compute_utility_with_deal_in():
    """Test utility computation with deal-in penalty."""
    utility_with_penalty = compute_utility(
        profit=100.0, missed_hu=False, deal_in_as_loser=True
    )
    utility_without_penalty = compute_utility(
        profit=100.0, missed_hu=False, deal_in_as_loser=False
    )
    assert utility_with_penalty < utility_without_penalty
    # Penalty is 0.5
    assert utility_with_penalty == pytest.approx(utility_without_penalty - 0.5, abs=0.01)


def test_run_simulation_basic():
    """Test run_simulation returns expected keys."""
    cfg = {
        "base_points": 1,
        "fan_min": 1,
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10
    }
    result = run_simulation(lambda f: defensive_strategy(f, 1), cfg)
    
    assert "profit" in result
    assert "utility" in result
    assert "mean_fan" in result
    assert "win_rate" in result
    assert "deal_in_rate" in result
    assert "deal_in_loss_rate" in result
    assert "missed_win_rate" in result
    assert "fan_distribution" in result
    assert 0 <= result["win_rate"] <= 1.0


def test_run_simulation_utility_baseline():
    """Test that run_simulation includes baseline utility."""
    cfg = {
        "base_points": 1,
        "fan_min": 1,
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10
    }
    # Test with explicit baseline values
    result_low = run_simulation(lambda f: defensive_strategy(f, 1), cfg, baseline_utility=50)
    result_high = run_simulation(lambda f: defensive_strategy(f, 1), cfg, baseline_utility=200)
    
    # Higher baseline should result in higher utility
    # The difference should be approximately 200 - 50 = 150
    # But due to randomness in simulation (different random seeds), allow variance
    utility_diff = result_high["utility"] - result_low["utility"]
    # The difference should be positive and roughly around 150
    # Allow wide variance (50-250) due to randomness in simulation
    assert utility_diff > 0  # Should be positive
    assert 50 < utility_diff < 250  # Should be roughly around 150, but allow variance


def test_run_multiple_trials():
    """Test run_multiple_trials returns expected structure."""
    cfg = {
        "base_points": 1,
        "fan_min": 1,
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10,
        "trials": 5
    }
    results = run_multiple_trials(lambda f: defensive_strategy(f, 1), cfg, num_trials=5)
    
    assert "profits" in results
    assert "utilities" in results
    assert "mean_fans" in results
    assert "win_rates" in results
    assert len(results["profits"]) == 5
    assert len(results["utilities"]) == 5


def test_run_multiple_trials_custom_num():
    """Test run_multiple_trials with custom num_trials."""
    cfg = {
        "base_points": 1,
        "fan_min": 1,
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10,
        "trials": 100
    }
    results = run_multiple_trials(lambda f: defensive_strategy(f, 1), cfg, num_trials=3)
    
    assert len(results["profits"]) == 3  # Should use num_trials parameter, not cfg["trials"]


def test_compute_utility_with_fan_bonus():
    """Test utility computation with fan >= 2 bonus multiplier."""
    # Without fan bonus (fan < 2)
    utility_low_fan = compute_utility(profit=100.0, missed_hu=False, deal_in_as_loser=False, fan=1)
    # With fan bonus (fan >= 2)
    utility_high_fan = compute_utility(profit=100.0, missed_hu=False, deal_in_as_loser=False, fan=2)
    
    # High fan should be 3x the low fan utility
    assert utility_high_fan == pytest.approx(utility_low_fan * 3, abs=0.01)
    assert utility_high_fan > utility_low_fan


def test_compute_utility_fan_3():
    """Test utility computation with fan = 3."""
    utility = compute_utility(profit=100.0, missed_hu=False, deal_in_as_loser=False, fan=3)
    # Should be sqrt(100) * 3 * 3 = 10 * 3 * 3 = 90
    assert utility == pytest.approx(90.0, abs=0.01)


def test_compute_utility_combined_penalties():
    """Test utility computation with both missed_hu and deal_in penalties."""
    utility = compute_utility(
        profit=100.0, 
        missed_hu=True, 
        deal_in_as_loser=True,
        fan=2
    )
    # Base: sqrt(100) * 3 * 3 = 90
    # Penalties: -0.2 - 0.5 = -0.7
    # Expected: 90 - 0.7 = 89.3
    assert utility == pytest.approx(89.3, abs=0.01)

