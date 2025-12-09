import os
import yaml
import numpy as np
from mahjong_sim.simulation import simulate_round, run_multiple_trials
from mahjong_sim.strategies import defensive_strategy, aggressive_strategy
from mahjong_sim.utils import compare_strategies, compute_statistics
from mahjong_sim.plotting import ensure_dir, save_hist, save_scatter_plot


def compute_nonlinear_utility(profit, missed_hu, deal_in_as_loser, crra_gamma=2.0):
    """
    Compute nonlinear utility with strong concave reward function and minimal penalties.
    
    Uses CRRA form for positive profits (strong concave) and greatly reduced penalties.
    
    Args:
        profit: Profit from the hand
        missed_hu: Boolean indicating if player missed a possible Hu
        deal_in_as_loser: Boolean indicating if player dealt in as loser
        crra_gamma: CRRA risk aversion parameter (default: 2.0)
    
    Returns:
        Utility value
    """
    # Strong concave reward function for positive profits
    if profit > 0:
        if crra_gamma == 1:
            # Log utility (concave)
            utility = np.log(1 + profit)
        else:
            # CRRA utility (strong concave for gamma > 1)
            utility = (1 + profit) ** (1 - crra_gamma) / (1 - crra_gamma)
        
        # Additional emotional reward for big wins (also concave)
        emotional_reward = 0.1 * np.sqrt(profit)  # Small concave bonus
        utility += emotional_reward
    else:
        # Negative profit: concave penalty (less severe than linear)
        utility = -np.sqrt(abs(profit))  # Concave penalty
    
    # Minimal penalties (greatly reduced)
    if missed_hu:
        utility -= 0.2  # Greatly reduced penalty for missing a Hu
    
    if deal_in_as_loser:
        utility -= 0.5  # Greatly reduced penalty for dealing in
    
    return utility


def simulate_round_with_custom_utility(player_strategy, cfg, utility_fn):
    """
    Simulate a round using custom utility function.
    
    Uses the same logic as simulate_round but applies custom utility function.
    """
    result = simulate_round(player_strategy, cfg)
    
    # Replace utility with custom utility function
    result["utility"] = utility_fn(
        result["profit"],
        result["missed_hu"],
        result["deal_in_as_loser"]
    )
    
    return result


def run_simulation_with_utility(strategy_fn, cfg, utility_fn, baseline_utility=200):
    """
    Run simulation with custom utility function.
    
    Args:
        strategy_fn: Strategy function
        cfg: Configuration dictionary
        utility_fn: Custom utility function
        baseline_utility: Baseline emotional utility at start (default: 200)
    """
    profits = []
    utilities = []
    fans = []
    wins = []
    deal_in_as_winner = []
    deal_in_as_loser = []
    missed_hu = []
    
    for _ in range(cfg["rounds_per_trial"]):
        result = simulate_round_with_custom_utility(strategy_fn, cfg, utility_fn)
        profits.append(result["profit"])
        utilities.append(result["utility"])  # Incremental utility per round
        fans.append(result["fan"])
        wins.append(result["won"])
        deal_in_as_winner.append(result["deal_in_as_winner"])
        deal_in_as_loser.append(result["deal_in_as_loser"])
        missed_hu.append(result["missed_hu"])
    
    # Total utility = baseline + sum of incremental utilities
    total_utility = baseline_utility + np.sum(utilities)
    
    return {
        "profit": np.sum(profits),
        "utility": total_utility,
        "mean_fan": np.mean([f for f in fans if f > 0]) if any(f > 0 for f in fans) else 0.0,
        "win_rate": np.mean(wins),
        "deal_in_rate": np.mean(deal_in_as_winner),
        "deal_in_loss_rate": np.mean(deal_in_as_loser),
        "missed_win_rate": np.mean(missed_hu),
        "fan_distribution": fans
    }


def run_multiple_trials_with_utility(strategy_fn, cfg, utility_fn, num_trials=None):
    """Run multiple trials with custom utility function."""
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
        result = run_simulation_with_utility(strategy_fn, cfg, utility_fn)
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


def main():
    with open("configs/base.yaml") as f:
        cfg = yaml.safe_load(f)
    
    print("=" * 60)
    print("Experiment 2: Utility Function Analysis")
    print("Testing H2: Aggressive strategy utility > Defensive strategy utility")
    print("Using CRRA utility function with emotional rewards")
    print("=" * 60)
    
    # Define utility function
    utility_fn = lambda profit, missed_hu, deal_in_as_loser: compute_nonlinear_utility(
        profit, missed_hu, deal_in_as_loser, crra_gamma=2.0
    )
    
    print(f"\nRunning {cfg['trials']} trials with {cfg['rounds_per_trial']} rounds each...")
    results_def = run_multiple_trials_with_utility(
        lambda f: defensive_strategy(f, cfg["fan_min"]),
        cfg,
        utility_fn
    )
    results_agg = run_multiple_trials_with_utility(
        lambda f: aggressive_strategy(f, cfg["t_fan_threshold"]),
        cfg,
        utility_fn
    )
    
    # Statistical comparison
    comparison = compare_strategies(results_def, results_agg)
    
    print("\n" + "-" * 60)
    print("UTILITY COMPARISON (with nonlinear CRRA utility):")
    print("-" * 60)
    print(f"Defensive Strategy:")
    print(f"  Mean: {comparison['utility']['defensive']['mean']:.2f}")
    print(f"  95% CI: [{comparison['utility']['defensive']['ci_95_lower']:.2f}, {comparison['utility']['defensive']['ci_95_upper']:.2f}]")
    print(f"\nAggressive Strategy:")
    print(f"  Mean: {comparison['utility']['aggressive']['mean']:.2f}")
    print(f"  95% CI: [{comparison['utility']['aggressive']['ci_95_lower']:.2f}, {comparison['utility']['aggressive']['ci_95_upper']:.2f}]")
    print(f"\nDifference (Agg - Def): {comparison['utility']['difference']:.2f}")
    print(f"t-statistic: {comparison['utility']['t_statistic']:.4f}")
    print(f"p-value: {comparison['utility']['p_value']:.6f}")
    
    print("\n" + "-" * 60)
    print("PROFIT COMPARISON (for reference):")
    print("-" * 60)
    print(f"Defensive Mean: {comparison['profit']['defensive']['mean']:.2f}")
    print(f"Aggressive Mean: {comparison['profit']['aggressive']['mean']:.2f}")
    print(f"Difference (Def - Agg): {comparison['profit']['difference']:.2f}")
    
    print("\n" + "-" * 60)
    print("ADDITIONAL METRICS:")
    print("-" * 60)
    print(f"Defensive Win Rate: {np.mean(results_def['win_rates']):.4f}")
    print(f"Aggressive Win Rate: {np.mean(results_agg['win_rates']):.4f}")
    print(f"Defensive Missed Win Rate: {np.mean(results_def['missed_win_rates']):.4f}")
    print(f"Aggressive Missed Win Rate: {np.mean(results_agg['missed_win_rates']):.4f}")
    
    print("\n" + "=" * 60)
    
    # Generate plots
    plot_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plots", "experiment_2")
    ensure_dir(plot_dir)
    
    # Histogram: Utility distribution (combined)
    all_utilities = np.concatenate([results_def['utilities'], results_agg['utilities']])
    save_hist(
        all_utilities,
        "Utility Distribution (All Strategies)",
        os.path.join(plot_dir, "utility_distribution.png"),
        xlabel="Utility",
        ylabel="Frequency",
        bins=30
    )
    
    # Scatter plot: Profit vs Utility (combined)
    all_profits = np.concatenate([results_def['profits'], results_agg['profits']])
    all_utilities_combined = np.concatenate([results_def['utilities'], results_agg['utilities']])
    save_scatter_plot(
        all_profits,
        all_utilities_combined,
        "Profit vs Utility",
        "Profit",
        "Utility",
        os.path.join(plot_dir, "profit_vs_utility.png"),
        alpha=0.3
    )
    
    # Histogram: Fan distribution (combined, non-zero only)
    all_fans = results_def['fan_distribution']
    all_fans = np.concatenate([all_fans, results_agg['fan_distribution']])
    all_fans = all_fans[all_fans > 0]  # Filter out zeros
    if len(all_fans) > 0:
        save_hist(
            all_fans,
            "Fan Distribution (All Strategies)",
            os.path.join(plot_dir, "fan_distribution.png"),
            xlabel="Fan Value",
            ylabel="Frequency",
            bins=15
        )
    
    print(f"\nPlots saved to: {plot_dir}")


if __name__ == "__main__":
    main()
