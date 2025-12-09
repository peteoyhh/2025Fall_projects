from mahjong_sim.real_mc import run_simulation
from mahjong_sim.strategies import defensive_strategy


def test_simulation_runs():
    cfg = {
        "base_points": 1,
        "fan_min": 1,  # Must be >= 1 (Pi Hu is invalid)
        "t_fan_threshold": 3,
        "alpha": 0.1,
        "penalty_deal_in": 3,
        "rounds_per_trial": 10
    }
    result = run_simulation(lambda f: defensive_strategy(f, 1), cfg)
    assert "profit" in result
    assert "utility" in result
    assert "win_rate" in result
    assert "deal_in_rate" in result
    assert "deal_in_loss_rate" in result
    assert "missed_win_rate" in result
    # Win rate should be less than 1.0 (not every hand is winnable)
    assert 0 <= result["win_rate"] <= 1.0

