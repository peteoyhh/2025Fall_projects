from typing import Union
import numpy as np


def compute_score(fan: int, base_points: int = 1) -> int:
    """
    Compute base score for a winning hand.
    
    Score formula: B * 2^fan
    where B is base_points and fan is the total fan count.
    
    Args:
        fan: Total fan count (including Gong bonuses)
        base_points: Base point value (default: 1)
    
    Returns:
        Base score value
    """
    return base_points * (2 ** fan)


def compute_winner_profit(score: float, is_self_draw: bool, deal_in_occurred: bool, 
                         penalty_multiplier: float = 1.0) -> float:
    """
    Compute profit for the winner.
    
    Beijing Mahjong scoring rules:
    - If self-draw: Winner receives score * 3 (one share from each of 3 opponents)
    - If deal-in: Winner receives score * penalty_multiplier (equal transfer from deal-in player)
    
    Important: Winner should NEVER receive negative profit.
    
    Args:
        score: Base score (B * 2^fan)
        is_self_draw: Boolean indicating if winner self-drew
        deal_in_occurred: Boolean indicating if deal-in occurred
        penalty_multiplier: Multiplier for deal-in penalty (default: 1.0)
    
    Returns:
        Profit for the winner (always >= 0)
    """
    if is_self_draw:
        # Self-draw: receive from all 3 opponents
        return score * 3
    elif deal_in_occurred:
        # Deal-in: receive score * penalty_multiplier from the player who dealt in
        # This ensures equal transfer: winner gets what loser pays
        return score * penalty_multiplier
    else:
        # Should not happen, but default to self-draw
        return score * 3


def compute_loser_cost(score: float, penalty_multiplier: float, is_deal_in_loser: bool) -> float:
    """
    Compute cost for the losing player.
    
    Beijing Mahjong penalty rules:
    - If player dealt in: Pay score * penalty_multiplier
    - If opponent self-drew: Pay score (one of three shares)
    
    Args:
        score: Base score (B * 2^fan)
        penalty_multiplier: Multiplier for deal-in penalty
        is_deal_in_loser: Boolean indicating if this player dealt in
    
    Returns:
        Cost for the loser (negative value, representing loss)
    """
    if is_deal_in_loser:
        # Dealt in: pay penalty
        return -score * penalty_multiplier
    else:
        # Opponent self-drew: pay base score
        return -score


