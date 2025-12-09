from mahjong_sim.scoring import (
    compute_score,
    compute_winner_profit,
    compute_loser_cost
)


def test_compute_score_basic():
    assert compute_score(0, base_points=1) == 1
    assert compute_score(1, base_points=1) == 2
    assert compute_score(2, base_points=1) == 4


def test_compute_winner_profit():
    """Test that winners always receive positive profit."""
    # Self-draw
    profit = compute_winner_profit(score=10, is_self_draw=True, deal_in_occurred=False)
    assert profit == 30  # score * 3
    
    # Deal-in
    profit = compute_winner_profit(score=10, is_self_draw=False, deal_in_occurred=True)
    assert profit == 10  # score
    
    # Winner should never have negative profit
    assert profit > 0


def test_compute_loser_cost():
    """Test that losers pay negative amounts."""
    # Deal-in loser
    cost = compute_loser_cost(score=10, penalty_multiplier=3, is_deal_in_loser=True)
    assert cost == -30  # -score * penalty_multiplier
    
    # Self-draw loser
    cost = compute_loser_cost(score=10, penalty_multiplier=3, is_deal_in_loser=False)
    assert cost == -10  # -score
    
    # Loser should always pay (negative)
    assert cost < 0


def test_compute_score_various_fan():
    """Test compute_score with various fan values."""
    assert compute_score(0, base_points=1) == 1  # 2^0 = 1
    assert compute_score(3, base_points=1) == 8  # 2^3 = 8
    assert compute_score(4, base_points=2) == 32  # 2^4 * 2 = 32


def test_compute_winner_profit_edge_cases():
    """Test compute_winner_profit edge cases."""
    # Default case (should not happen but handled)
    profit = compute_winner_profit(score=10, is_self_draw=False, deal_in_occurred=False)
    assert profit == 30  # Defaults to self-draw

