"""
4-player table composition Monte Carlo simulation.

This module simulates 4 players interacting at a Mahjong table with different
strategy compositions using REAL Monte Carlo simulation with actual tiles.

Key design:
- Real tile-based simulation with 136 tiles
- Actual deal, draw, discard mechanics
- Real hand state management and winning detection
"""

import numpy as np
from .real_mc import (
    Player,
    RealMCSimulation,
    simulate_real_mc_round
)
from .scoring import (
    compute_score,
    compute_winner_profit,
    compute_loser_cost
)
from .simulation import (
    compute_utility
)
from .strategies import defensive_strategy, aggressive_strategy


def simulate_table_round(players, cfg, dealer_index):
    """
    Simulate a single round with 4 players using REAL Monte Carlo.
    
    Args:
        players: List of player dicts with "strategy" and "strategy_type"
        cfg: Configuration dictionary
        dealer_index: Index of dealer player
    
    Returns:
        (results, round_meta) tuple
    """
    # Convert player dicts to Player objects
    mc_players = []
    fan_min = cfg.get("fan_min", 1)
    fan_threshold = cfg.get("t_fan_threshold", 3)
    
    for i, player_dict in enumerate(players):
        strategy_type = player_dict.get("strategy_type", "NEU")
        strategy_fn = player_dict.get("strategy")
        
        mc_player = Player(i, strategy_type, strategy_fn)
        mc_player.is_dealer = (i == dealer_index)
        mc_players.append(mc_player)
    
    # Simulate round using real Monte Carlo
    result = simulate_real_mc_round(mc_players, cfg, dealer_index)
    
    # Convert result to expected format
    results = []
    winner_idx = result.get("winner")
    is_self_draw = result.get("is_self_draw", False)
    fan = result.get("fan", 0)
    winner_profit = result.get("winner_profit", 0.0)
    
    # Initialize all players with zero results
    for i in range(len(players)):
        results.append({
            "profit": 0.0,
            "utility": 0.0,
            "fan": 0,
            "won": False,
            "deal_in_as_winner": False,
            "deal_in_as_loser": False,
            "missed_hu": False
        })
    
    if winner_idx is not None:
        # Someone won
        winner = mc_players[winner_idx]
        results[winner_idx]["won"] = True
        results[winner_idx]["fan"] = fan
        results[winner_idx]["profit"] = winner_profit
        results[winner_idx]["deal_in_as_winner"] = not is_self_draw
        results[winner_idx]["utility"] = compute_utility(
            winner_profit, 
            missed_hu=False, 
            deal_in_as_loser=False
        )
        
        # Calculate losses for other players
        score = compute_score(fan, cfg.get("base_points", 1))
        
        if is_self_draw:
            # Self-draw: all 3 opponents pay
            loser_cost = compute_loser_cost(
                score,
                cfg.get("penalty_deal_in", 3),
                is_deal_in_loser=False
            )
            for i in range(len(players)):
                if i != winner_idx:
                    results[i]["profit"] = loser_cost
                    results[i]["utility"] = compute_utility(
                        loser_cost,
                        missed_hu=False,
                        deal_in_as_loser=False
                    )
        else:
            # Deal-in: get deal_in_player from result
            deal_in_player_idx = result.get("deal_in_player_id")
            
            if deal_in_player_idx is not None:
                loser_cost = compute_loser_cost(
                    score,
                    cfg.get("penalty_deal_in", 3),
                    is_deal_in_loser=True
                )
                results[deal_in_player_idx]["profit"] = loser_cost
                results[deal_in_player_idx]["deal_in_as_loser"] = True
                results[deal_in_player_idx]["utility"] = compute_utility(
                    loser_cost,
                    missed_hu=False,
                    deal_in_as_loser=True
                )
            else:
                # Fallback: if deal_in_player_id is None but is_self_draw=False,
                # this should not happen in normal gameplay, but handle gracefully
                # In this case, we cannot determine who dealt in, so no one pays deal-in penalty
                # This is a safety fallback for edge cases
                pass
        
        # Check for missed Hu opportunities
        for i, player in enumerate(mc_players):
            if i != winner_idx and player.missed_hus > 0:
                results[i]["missed_hu"] = True
                # Update utility with missed Hu penalty
                results[i]["utility"] = compute_utility(
                    results[i]["profit"],
                    missed_hu=True,
                    deal_in_as_loser=results[i]["deal_in_as_loser"]
                )
    
    # Round metadata
    round_meta = {
        "winner_index": winner_idx,
        "winner_is_dealer": winner_idx == dealer_index if winner_idx is not None else False,
        "dealer_ready": False,  # Not used in real MC
        "dealer_continues": winner_idx == dealer_index if winner_idx is not None else False,
        "is_draw": winner_idx is None
    }
    
    return results, round_meta


def _run_table(players, cfg, rounds_per_trial, baseline_utility=200):
    dealer_index = 0

    player_count = len(players)

    all_profits = [[] for _ in range(player_count)]
    all_utilities = [[] for _ in range(player_count)]
    all_fans = [[] for _ in range(player_count)]
    all_wins = [[] for _ in range(player_count)]
    all_deal_in_as_winner = [[] for _ in range(player_count)]
    all_deal_in_as_loser = [[] for _ in range(player_count)]
    all_missed_hu = [[] for _ in range(player_count)]

    dealer_round_stats = {
        "profits": [],
        "utilities": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": [],
        "fans": []
    }

    non_dealer_round_stats = {
        "profits": [],
        "utilities": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": [],
        "fans": []
    }

    for _ in range(rounds_per_trial):
        round_results, round_meta = simulate_table_round(players, cfg, dealer_index)

        for i, result in enumerate(round_results):
            all_profits[i].append(result["profit"])
            all_utilities[i].append(result["utility"])
            all_fans[i].append(result["fan"])
            all_wins[i].append(result["won"])
            all_deal_in_as_winner[i].append(result["deal_in_as_winner"])
            all_deal_in_as_loser[i].append(result["deal_in_as_loser"])
            all_missed_hu[i].append(result["missed_hu"])

            target_stats = dealer_round_stats if i == dealer_index else non_dealer_round_stats
            target_stats["profits"].append(result["profit"])
            target_stats["utilities"].append(result["utility"])
            target_stats["wins"].append(result["won"])
            target_stats["deal_in_as_winner"].append(result["deal_in_as_winner"])
            target_stats["deal_in_as_loser"].append(result["deal_in_as_loser"])
            target_stats["missed_hu"].append(result["missed_hu"])
            target_stats["fans"].append(result["fan"])

        if not round_meta["dealer_continues"]:
            dealer_index = (dealer_index + 1) % player_count

    def_stats = {
        "profits": [],
        "utilities": [],
        "fans": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": []
    }

    agg_stats = {
        "profits": [],
        "utilities": [],
        "fans": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": []
    }

    per_player_stats = []

    for i, player in enumerate(players):
        profit_sum = np.sum(all_profits[i])
        utility_sum = baseline_utility + np.sum(all_utilities[i])
        wins = all_wins[i]
        fans = [f for f in all_fans[i] if f > 0]

        stats = {
            "profit": profit_sum,
            "utility": utility_sum,
            "mean_fan": np.mean(fans) if len(fans) > 0 else 0.0,
            "win_rate": np.mean(wins),
            "deal_in_rate": np.mean(all_deal_in_as_winner[i]),
            "deal_in_loss_rate": np.mean(all_deal_in_as_loser[i]),
            "missed_win_rate": np.mean(all_missed_hu[i]),
            "fan_distribution": all_fans[i]
        }

        per_player_stats.append({
            "player_index": i,
            "strategy_type": player.get("strategy_type"),
            **stats
        })

        if player.get("strategy_type") == "DEF":
            def_stats["profits"].append(stats["profit"])
            def_stats["utilities"].append(stats["utility"])
            def_stats["fans"].extend(fans)
            def_stats["wins"].append(stats["win_rate"])
            def_stats["deal_in_as_winner"].append(stats["deal_in_rate"])
            def_stats["deal_in_as_loser"].append(stats["deal_in_loss_rate"])
            def_stats["missed_hu"].append(stats["missed_win_rate"])
        elif player.get("strategy_type") == "AGG":
            agg_stats["profits"].append(stats["profit"])
            agg_stats["utilities"].append(stats["utility"])
            agg_stats["fans"].extend(fans)
            agg_stats["wins"].append(stats["win_rate"])
            agg_stats["deal_in_as_winner"].append(stats["deal_in_rate"])
            agg_stats["deal_in_as_loser"].append(stats["deal_in_loss_rate"])
            agg_stats["missed_hu"].append(stats["missed_win_rate"])

    return {
        "defensive": def_stats,
        "aggressive": agg_stats,
        "dealer": dealer_round_stats,
        "non_dealer": non_dealer_round_stats,
        "per_player": per_player_stats
    }


def simulate_table(composition, cfg, baseline_utility=200):
    """
    Simulate a full table trial with given composition using REAL Monte Carlo.
    """
    num_def = composition
    num_agg = 4 - composition

    players = []
    fan_min = cfg["fan_min"]
    t_fan_threshold = cfg["t_fan_threshold"]

    for _ in range(num_def):
        players.append({
            "strategy": lambda f, fm=fan_min: defensive_strategy(f, fm),
            "strategy_type": "DEF"
        })
    for _ in range(num_agg):
        players.append({
            "strategy": lambda f, th=t_fan_threshold: aggressive_strategy(f, th),
            "strategy_type": "AGG"
        })

    result = _run_table(players, cfg, cfg["rounds_per_trial"], baseline_utility)
    result["composition"] = composition
    return result


def simulate_custom_table(players, cfg, rounds_per_trial=None, baseline_utility=200):
    """
    Run a table simulation with a custom list of players using REAL Monte Carlo.
    
    Args:
        players: List of player dicts with "strategy" and "strategy_type"
        cfg: Configuration dictionary
        rounds_per_trial: Number of rounds (defaults to cfg["rounds_per_trial"])
        baseline_utility: Baseline utility (default: 200)
    
    Returns:
        Dictionary with aggregated statistics
    """
    rounds = rounds_per_trial or cfg["rounds_per_trial"]
    result = _run_table(players, cfg, rounds, baseline_utility)
    result["composition"] = None
    return result


def run_composition_experiments(cfg, num_trials=1000):
    """
    Run experiments for all table compositions (θ = 0 to 4).
    
    Args:
        cfg: Configuration dictionary
        num_trials: Number of trials per composition (default: 1000)
    
    Returns:
        Dictionary with results for each composition
    """
    compositions = [0, 1, 2, 3, 4]  # θ = number of DEF players
    results = {}
    
    for composition in compositions:
        print(f"Running composition θ={composition} ({composition} DEF, {4-composition} AGG)...")
        
        all_def_profits = []
        all_def_utilities = []
        all_agg_profits = []
        all_agg_utilities = []
        all_def_win_rates = []
        all_agg_win_rates = []
        all_def_deal_in_rates = []
        all_agg_deal_in_rates = []
        all_def_missed_hu_rates = []
        all_agg_missed_hu_rates = []
        all_def_fans = []
        all_agg_fans = []
        all_dealer_profits = []
        all_dealer_utilities = []
        all_dealer_wins = []
        all_dealer_deal_in_rates = []
        all_dealer_deal_in_loss_rates = []
        all_dealer_missed_hu = []
        all_dealer_fans = []
        all_non_dealer_profits = []
        all_non_dealer_utilities = []
        all_non_dealer_wins = []
        all_non_dealer_deal_in_rates = []
        all_non_dealer_deal_in_loss_rates = []
        all_non_dealer_missed_hu = []
        all_non_dealer_fans = []
        
        for _ in range(num_trials):
            trial_result = simulate_table(composition, cfg)
            
            if len(trial_result["defensive"]["profits"]) > 0:
                all_def_profits.extend(trial_result["defensive"]["profits"])
                all_def_utilities.extend(trial_result["defensive"]["utilities"])
                all_def_win_rates.extend(trial_result["defensive"]["wins"])
                all_def_deal_in_rates.extend(trial_result["defensive"]["deal_in_as_winner"])
                all_def_missed_hu_rates.extend(trial_result["defensive"]["missed_hu"])
                all_def_fans.extend(trial_result["defensive"]["fans"])
            
            if len(trial_result["aggressive"]["profits"]) > 0:
                all_agg_profits.extend(trial_result["aggressive"]["profits"])
                all_agg_utilities.extend(trial_result["aggressive"]["utilities"])
                all_agg_win_rates.extend(trial_result["aggressive"]["wins"])
                all_agg_deal_in_rates.extend(trial_result["aggressive"]["deal_in_as_winner"])
                all_agg_missed_hu_rates.extend(trial_result["aggressive"]["missed_hu"])
                all_agg_fans.extend(trial_result["aggressive"]["fans"])
            
            dealer_stats = trial_result["dealer"]
            non_dealer_stats = trial_result["non_dealer"]
            
            all_dealer_profits.extend(dealer_stats["profits"])
            all_dealer_utilities.extend(dealer_stats["utilities"])
            all_dealer_wins.extend(dealer_stats["wins"])
            all_dealer_deal_in_rates.extend(dealer_stats["deal_in_as_winner"])
            all_dealer_deal_in_loss_rates.extend(dealer_stats["deal_in_as_loser"])
            all_dealer_missed_hu.extend(dealer_stats["missed_hu"])
            all_dealer_fans.extend(dealer_stats["fans"])
            
            all_non_dealer_profits.extend(non_dealer_stats["profits"])
            all_non_dealer_utilities.extend(non_dealer_stats["utilities"])
            all_non_dealer_wins.extend(non_dealer_stats["wins"])
            all_non_dealer_deal_in_rates.extend(non_dealer_stats["deal_in_as_winner"])
            all_non_dealer_deal_in_loss_rates.extend(non_dealer_stats["deal_in_as_loser"])
            all_non_dealer_missed_hu.extend(non_dealer_stats["missed_hu"])
            all_non_dealer_fans.extend(non_dealer_stats["fans"])
        
        results[composition] = {
            "defensive": {
                "mean_profit": np.mean(all_def_profits) if len(all_def_profits) > 0 else 0.0,
                "std_profit": np.std(all_def_profits) if len(all_def_profits) > 0 else 0.0,
                "mean_utility": np.mean(all_def_utilities) if len(all_def_utilities) > 0 else 0.0,
                "std_utility": np.std(all_def_utilities) if len(all_def_utilities) > 0 else 0.0,
                "win_rate": np.mean(all_def_win_rates) if len(all_def_win_rates) > 0 else 0.0,
                "deal_in_rate": np.mean(all_def_deal_in_rates) if len(all_def_deal_in_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_def_missed_hu_rates) if len(all_def_missed_hu_rates) > 0 else 0.0,
                "mean_fan": np.mean(all_def_fans) if len(all_def_fans) > 0 else 0.0,
                "fan_distribution": all_def_fans
            },
            "aggressive": {
                "mean_profit": np.mean(all_agg_profits) if len(all_agg_profits) > 0 else 0.0,
                "std_profit": np.std(all_agg_profits) if len(all_agg_profits) > 0 else 0.0,
                "mean_utility": np.mean(all_agg_utilities) if len(all_agg_utilities) > 0 else 0.0,
                "std_utility": np.std(all_agg_utilities) if len(all_agg_utilities) > 0 else 0.0,
                "win_rate": np.mean(all_agg_win_rates) if len(all_agg_win_rates) > 0 else 0.0,
                "deal_in_rate": np.mean(all_agg_deal_in_rates) if len(all_agg_deal_in_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_agg_missed_hu_rates) if len(all_agg_missed_hu_rates) > 0 else 0.0,
                "mean_fan": np.mean(all_agg_fans) if len(all_agg_fans) > 0 else 0.0,
                "fan_distribution": all_agg_fans
            },
            "dealer": {
                "mean_profit": np.mean(all_dealer_profits) if len(all_dealer_profits) > 0 else 0.0,
                "std_profit": np.std(all_dealer_profits) if len(all_dealer_profits) > 0 else 0.0,
                "mean_utility": np.mean(all_dealer_utilities) if len(all_dealer_utilities) > 0 else 0.0,
                "std_utility": np.std(all_dealer_utilities) if len(all_dealer_utilities) > 0 else 0.0,
                "win_rate": np.mean(all_dealer_wins) if len(all_dealer_wins) > 0 else 0.0,
                "deal_in_rate": np.mean(all_dealer_deal_in_rates) if len(all_dealer_deal_in_rates) > 0 else 0.0,
                "deal_in_loss_rate": np.mean(all_dealer_deal_in_loss_rates) if len(all_dealer_deal_in_loss_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_dealer_missed_hu) if len(all_dealer_missed_hu) > 0 else 0.0,
                "mean_fan": np.mean([f for f in all_dealer_fans if f > 0]) if len(all_dealer_fans) > 0 else 0.0,
                "fan_distribution": all_dealer_fans
            },
            "non_dealer": {
                "mean_profit": np.mean(all_non_dealer_profits) if len(all_non_dealer_profits) > 0 else 0.0,
                "std_profit": np.std(all_non_dealer_profits) if len(all_non_dealer_profits) > 0 else 0.0,
                "mean_utility": np.mean(all_non_dealer_utilities) if len(all_non_dealer_utilities) > 0 else 0.0,
                "std_utility": np.std(all_non_dealer_utilities) if len(all_non_dealer_utilities) > 0 else 0.0,
                "win_rate": np.mean(all_non_dealer_wins) if len(all_non_dealer_wins) > 0 else 0.0,
                "deal_in_rate": np.mean(all_non_dealer_deal_in_rates) if len(all_non_dealer_deal_in_rates) > 0 else 0.0,
                "deal_in_loss_rate": np.mean(all_non_dealer_deal_in_loss_rates) if len(all_non_dealer_deal_in_loss_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_non_dealer_missed_hu) if len(all_non_dealer_missed_hu) > 0 else 0.0,
                "mean_fan": np.mean([f for f in all_non_dealer_fans if f > 0]) if len(all_non_dealer_fans) > 0 else 0.0,
                "fan_distribution": all_non_dealer_fans
            }
        }
    
    return results

