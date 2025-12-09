from typing import Dict, Callable, Union, Any, Optional
import numpy as np
from .real_mc import (
    Player,
    RealMCSimulation,
    simulate_real_mc_round,
    run_real_mc_trial
)
from .scoring import (
    compute_score,
    compute_winner_profit,
    compute_loser_cost
)


def compute_utility(profit: float, missed_hu: bool, deal_in_as_loser: bool, 
                   missed_penalty: float = 0.2, deal_in_penalty: float = 0.5) -> float:
    """
    Compute utility using strong concave reward function with minimal penalties.
    
    U = concave_reward(profit) - small_penalties
    
    Key design principles:
    - Strong concave (non-linear) reward function for positive profits
    - Utility is monotone increasing with profit
    - Penalties are minimal and do not overpower rewards
    - Winners always have strongly positive utility contribution
    
    Args:
        profit: Profit from the hand (can be negative if lost)
        missed_hu: Boolean indicating if player missed a possible Hu
        deal_in_as_loser: Boolean indicating if player dealt in as loser
        missed_penalty: Penalty for missing a Hu (default: 0.2, greatly reduced)
        deal_in_penalty: Penalty for dealing in as loser (default: 0.5, greatly reduced)
    
    Returns:
        Utility value
    """
    # Strong concave reward function for positive profits
    # Using sqrt for stronger concavity than log, ensuring non-linear positive rewards
    if profit > 0:
        # Positive profit: strong concave utility (sqrt is more concave than log)
        # This ensures diminishing returns but always positive and non-linear
        utility = np.sqrt(profit)  # Strong concave, always positive for profit > 0
    elif profit < 0:
        # Negative profit: concave penalty (less severe than linear)
        # Use sqrt of absolute value to make penalty concave (less harsh)
        utility = -np.sqrt(abs(profit))  # Concave penalty, less severe than linear
    else:
        # Zero profit
        utility = 0.0
    
    # Apply minimal penalties only when they occur
    # Penalties are greatly reduced to not overpower the concave rewards
    if missed_hu:
        utility -= missed_penalty
    
    if deal_in_as_loser:
        utility -= deal_in_penalty
    
    return utility


DEALER_READY_THRESHOLD = 0.6


def simulate_round_real(player_strategy: Callable[[Union[int, float]], bool], 
                       cfg: Dict[str, Any], is_dealer: bool = False) -> Dict[str, Union[float, int, bool]]:
    """
    Simulate a single round using REAL Monte Carlo (actual tiles).
    
    This uses the real_mc module for actual tile-based simulation.
    """
    from .real_mc import Player
    
    # Determine strategy type
    fan_min = cfg.get("fan_min", 1)
    fan_threshold = cfg.get("t_fan_threshold", 3)
    
    # Create test player
    strategy_type = "DEF"  # Default
    if player_strategy(fan_min):
        strategy_type = "DEF"
    elif not player_strategy(fan_threshold - 1):
        strategy_type = "AGG"
    
    player = Player(0, strategy_type, player_strategy)
    player.is_dealer = is_dealer
    
    # Create 3 neutral opponents
    opponents = [
        Player(1, "NEU", None),
        Player(2, "NEU", None),
        Player(3, "NEU", None)
    ]
    
    all_players = [player] + opponents
    
    # Simulate round
    result = simulate_real_mc_round(all_players, cfg, dealer_index=0 if is_dealer else 1)
    
    # Convert result format
    if result["winner"] == 0:
        # Our player won
        profit = result.get("winner_profit", 0.0)
        fan = result.get("fan", 0)
        is_self_draw = result.get("is_self_draw", False)
        
        return {
            "profit": profit,
            "utility": compute_utility(profit, missed_hu=False, deal_in_as_loser=False),
            "fan": fan,
            "won": True,
            "deal_in_as_winner": not is_self_draw,
            "deal_in_as_loser": False,
            "missed_hu": False
        }
    elif result["winner"] is not None:
        # Opponent won, check if we dealt in
        # Use deal_in_player_id from result to accurately determine if we dealt in
        deal_in_player_id = result.get("deal_in_player_id")
        dealt_in = (deal_in_player_id == 0)  # Our player is player_id=0
        
        profit = 0.0
        if dealt_in:
            # Calculate loss
            fan = result.get("fan", 0)
            score = compute_score(fan, cfg.get("base_points", 1))
            profit = compute_loser_cost(score, cfg.get("penalty_deal_in", 3), is_deal_in_loser=True)
        
        return {
            "profit": profit,
            "utility": compute_utility(profit, missed_hu=False, deal_in_as_loser=dealt_in),
            "fan": 0,
            "won": False,
            "deal_in_as_winner": False,
            "deal_in_as_loser": dealt_in,
            "missed_hu": False
        }
    else:
        # Draw
        return {
            "profit": 0.0,
            "utility": 0.0,
            "fan": 0,
            "won": False,
            "deal_in_as_winner": False,
            "deal_in_as_loser": False,
            "missed_hu": False
        }


def simulate_round(player_strategy: Callable[[Union[int, float]], bool], 
                  cfg: Dict[str, Any], is_dealer: bool = False) -> Dict[str, Union[float, int, bool]]:
    """
    Simulate a single round of Beijing Mahjong using REAL Monte Carlo.
    
    Uses actual tile-based simulation with 136 tiles.
    
    Args:
        player_strategy: Strategy function that takes fan and returns bool
        cfg: Configuration dictionary
        is_dealer: Whether player is dealer
    
    Returns:
        Dictionary with round results
    """
    # Use real Monte Carlo simulation
    return simulate_round_real(player_strategy, cfg, is_dealer)


def run_simulation(strategy_fn: Callable[[Union[int, float]], bool], 
                  cfg: Dict[str, Any], baseline_utility: int = 200) -> Dict[str, Any]:
    """
    Run a single trial (multiple rounds) of the simulation.
    
    Args:
        strategy_fn: Strategy function
        cfg: Configuration dictionary
        baseline_utility: Baseline emotional utility at start (default: 200)
    
    Returns:
        Dictionary with aggregated statistics for this trial
    """
    profits = []
    utilities = []
    fans = []
    wins = []
    deal_in_as_winner = []
    deal_in_as_loser = []
    missed_hu = []
    
    for _ in range(cfg["rounds_per_trial"]):
        result = simulate_round(strategy_fn, cfg)
        profits.append(result["profit"])
        utilities.append(result["utility"])  # Incremental utility per round
        fans.append(result["fan"])
        wins.append(result["won"])
        deal_in_as_winner.append(result["deal_in_as_winner"])
        deal_in_as_loser.append(result["deal_in_as_loser"])
        missed_hu.append(result["missed_hu"])
    
    # Incremental utility cannot drive total utility below the baseline.
    # Clamp at zero so baseline_utility acts as a guaranteed floor.
    incremental_utility = np.sum(utilities)
    incremental_utility = max(0.0, incremental_utility)
    total_utility = baseline_utility + incremental_utility
    
    return {
        "profit": np.sum(profits),
        "utility": total_utility,
        "mean_fan": np.mean([f for f in fans if f > 0]) if any(f > 0 for f in fans) else 0.0,
        "win_rate": np.mean(wins),
        "deal_in_rate": np.mean(deal_in_as_winner),  # Deal-in as winner
        "deal_in_loss_rate": np.mean(deal_in_as_loser),  # Deal-in as loser
        "missed_win_rate": np.mean(missed_hu),
        "fan_distribution": fans
    }


def run_multiple_trials(strategy_fn: Callable[[Union[int, float]], bool], 
                       cfg: Dict[str, Any], num_trials: Optional[int] = None) -> Dict[str, Any]:
    """
    Run multiple trials and aggregate results for statistical analysis.
    
    Args:
        strategy_fn: Strategy function
        cfg: Configuration dictionary
        num_trials: Number of trials (defaults to cfg["trials"])
    
    Returns:
        Dictionary with aggregated statistics across all trials
    """
    if num_trials is None:
        num_trials = cfg.get("trials", 2000)
    
    all_profits = []
    all_utilities = []
    all_mean_fans = []
    all_win_rates = []
    all_deal_in_rates = []
    all_deal_in_loss_rates = []
    all_missed_win_rates = []
    all_fan_distributions = []
    
    for _ in range(num_trials):
        result = run_simulation(strategy_fn, cfg)
        all_profits.append(result["profit"])
        all_utilities.append(result["utility"])
        all_mean_fans.append(result["mean_fan"])
        all_win_rates.append(result["win_rate"])
        all_deal_in_rates.append(result["deal_in_rate"])
        all_deal_in_loss_rates.append(result["deal_in_loss_rate"])
        all_missed_win_rates.append(result["missed_win_rate"])
        all_fan_distributions.extend(result["fan_distribution"])
    
    return {
        "profits": np.array(all_profits),
        "utilities": np.array(all_utilities),
        "mean_fans": np.array(all_mean_fans),
        "win_rates": np.array(all_win_rates),
        "deal_in_rates": np.array(all_deal_in_rates),
        "deal_in_loss_rates": np.array(all_deal_in_loss_rates),
        "missed_win_rates": np.array(all_missed_win_rates),
        "fan_distribution": np.array(all_fan_distributions),
        "num_trials": num_trials
    }
