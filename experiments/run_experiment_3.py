import os
import yaml
import numpy as np
from mahjong_sim.simulation import run_multiple_trials
from mahjong_sim.strategies import defensive_strategy, aggressive_strategy
from mahjong_sim.utils import analyze_composition_effect, compute_statistics
from mahjong_sim.plotting import ensure_dir, save_line_plot


def simulate_round_with_composition(theta, player_strategy, cfg):
    """
    Simulate a round with table composition theta.
    
    Adjusts deal-in risk based on composition:
    - More defensive players -> lower deal-in risk (they play safer)
    """
    import numpy as np
    from mahjong_sim.variables import (
        sample_hand_quality,
        sample_base_fan,
        sample_kong_events,
        can_complete_hand
    )
    from mahjong_sim.scoring import (
        compute_score,
        compute_winner_profit,
        compute_loser_cost,
        compute_total_fan
    )
    from mahjong_sim.simulation import compute_utility
    
    # Sample random variables
    Q = sample_hand_quality()
    
    # Adjust deal-in risk based on composition
    # More defensive players -> lower deal-in risk (they play safer)
    base_R = sample_deal_in_risk()
    R_adjusted = base_R * (1 - theta * 0.3)  # Reduce risk by up to 30% with all defensive
    
    # Check if hand can be completed
    can_win = can_complete_hand(Q)
    
    if not can_win:
        return {
            "profit": 0.0,
            "utility": 0.0,
            "fan": 0,
            "won": False,
            "deal_in_as_winner": False,
            "deal_in_as_loser": False,
            "missed_hu": False
        }
    
    # Hand can be completed
    base_fan = sample_base_fan()
    kong_count = sample_kong_events(lam=0.2, max_kongs=2)  # Cap Kongs at 2
    total_fan = compute_total_fan(base_fan, kong_count, max_total_fan=16)  # Cap total fan at 16
    
    # Check if strategy accepts
    strategy_accepts = player_strategy(total_fan)
    
    if not strategy_accepts:
        # Strategy rejected - missed Hu
        deal_in_as_loser = np.random.rand() < R_adjusted
        
        profit = 0.0
        if deal_in_as_loser:
            # Opponent won, we dealt in
            opponent_base_fan = sample_base_fan()
            opponent_kong = sample_kong_events(lam=0.2, max_kongs=2)
            opponent_fan = compute_total_fan(opponent_base_fan, opponent_kong, max_total_fan=16)
            opponent_score = compute_score(opponent_fan, cfg["base_points"])
            profit = compute_loser_cost(
                opponent_score,
                cfg["penalty_deal_in"],
                is_deal_in_loser=True
            )
        
        utility = compute_utility(
            profit,
            missed_hu=True,
            deal_in_as_loser=deal_in_as_loser
        )
        
        return {
            "profit": profit,
            "utility": utility,
            "fan": 0,
            "won": False,
            "deal_in_as_winner": False,
            "deal_in_as_loser": deal_in_as_loser,
            "missed_hu": True
        }
    
    # Strategy accepts - player wins
    score = compute_score(total_fan, cfg["base_points"])
    
    # Use adjusted deal-in risk
    deal_in_occurred = np.random.rand() < R_adjusted
    
    if deal_in_occurred:
        profit = compute_winner_profit(score, is_self_draw=False, deal_in_occurred=True)
        utility = compute_utility(
            profit,
            missed_hu=False,
            deal_in_as_loser=False
        )
        
        return {
            "profit": profit,
            "utility": utility,
            "fan": total_fan,
            "won": True,
            "deal_in_as_winner": True,
            "deal_in_as_loser": False,
            "missed_hu": False
        }
    else:
        profit = compute_winner_profit(score, is_self_draw=True, deal_in_occurred=False)
        utility = compute_utility(
            profit,
            missed_hu=False,
            deal_in_as_loser=False
        )
        
        return {
            "profit": profit,
            "utility": utility,
            "fan": total_fan,
            "won": True,
            "deal_in_as_winner": False,
            "deal_in_as_loser": False,
            "missed_hu": False
        }


def run_simulation_with_composition(theta, strategy_fn, cfg):
    """Run simulation with table composition theta."""
    profits = []
    utilities = []
    fans = []
    wins = []
    deal_in_as_winner = []
    deal_in_as_loser = []
    missed_hu = []
    
    for _ in range(cfg["rounds_per_trial"]):
        result = simulate_round_with_composition(theta, strategy_fn, cfg)
        profits.append(result["profit"])
        utilities.append(result["utility"])
        fans.append(result["fan"])
        wins.append(result["won"])
        deal_in_as_winner.append(result["deal_in_as_winner"])
        deal_in_as_loser.append(result["deal_in_as_loser"])
        missed_hu.append(result["missed_hu"])
    
    return {
        "profit": np.sum(profits),
        "utility": np.sum(utilities),
        "mean_fan": np.mean([f for f in fans if f > 0]) if any(f > 0 for f in fans) else 0.0,
        "win_rate": np.mean(wins),
        "deal_in_rate": np.mean(deal_in_as_winner),
        "deal_in_loss_rate": np.mean(deal_in_as_loser),
        "missed_win_rate": np.mean(missed_hu),
        "fan_distribution": fans
    }


def run_multiple_trials_with_composition(theta, strategy_fn, cfg, num_trials=None):
    """Run multiple trials with table composition theta."""
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
        result = run_simulation_with_composition(theta, strategy_fn, cfg)
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
    
    # Note: Real Monte Carlo simulation does not use random seed
    
    print("=" * 60)
    print("Experiment 3: Table Composition Analysis")
    print("Testing H3: Strategy performance depends on opponent composition (theta)")
    print("=" * 60)
    
    theta_values = [0.0, 0.33, 0.67, 1.0]
    
    # Test defensive strategy across different compositions
    print("\n" + "-" * 60)
    print("DEFENSIVE STRATEGY across compositions:")
    print("-" * 60)
    def_profits_by_theta = {}
    
    for theta in theta_values:
        print(f"\nRunning trials for theta = {theta:.2f}...")
        results = run_multiple_trials_with_composition(
            theta,
            lambda f: defensive_strategy(f, cfg["fan_min"]),
            cfg
        )
        def_profits_by_theta[theta] = results["profits"]
        stats = compute_statistics(results["profits"])
        print(f"  Mean profit: {stats['mean']:.2f}")
        print(f"  95% CI: [{stats['ci_95_lower']:.2f}, {stats['ci_95_upper']:.2f}]")
        print(f"  Win rate: {np.mean(results['win_rates']):.4f}")
    
    # Test aggressive strategy across different compositions
    print("\n" + "-" * 60)
    print("AGGRESSIVE STRATEGY across compositions:")
    print("-" * 60)
    agg_profits_by_theta = {}
    
    for theta in theta_values:
        print(f"\nRunning trials for theta = {theta:.2f}...")
        results = run_multiple_trials_with_composition(
            theta,
            lambda f: aggressive_strategy(f, cfg["t_fan_threshold"]),
            cfg
        )
        agg_profits_by_theta[theta] = results["profits"]
        stats = compute_statistics(results["profits"])
        print(f"  Mean profit: {stats['mean']:.2f}")
        print(f"  95% CI: [{stats['ci_95_lower']:.2f}, {stats['ci_95_upper']:.2f}]")
        print(f"  Win rate: {np.mean(results['win_rates']):.4f}")
    
    # Regression analysis
    print("\n" + "-" * 60)
    print("REGRESSION ANALYSIS:")
    print("-" * 60)
    
    def_regression = analyze_composition_effect(theta_values, def_profits_by_theta)
    agg_regression = analyze_composition_effect(theta_values, agg_profits_by_theta)
    
    print("\nDefensive Strategy:")
    print(f"  Slope: {def_regression['slope']:.2f}")
    print(f"  R-squared: {def_regression['r_squared']:.4f}")
    print(f"  p-value: {def_regression['p_value']:.6f}")
    
    print("\nAggressive Strategy:")
    print(f"  Slope: {agg_regression['slope']:.2f}")
    print(f"  R-squared: {agg_regression['r_squared']:.4f}")
    print(f"  p-value: {agg_regression['p_value']:.6f}")
    
    print("\n" + "-" * 60)
    print("INTERPRETATION:")
    print("-" * 60)
    if def_regression['slope'] < 0:
        print("Defensive strategy profit DECREASES as theta increases (more defensive opponents)")
    else:
        print("Defensive strategy profit INCREASES as theta increases")
    
    if agg_regression['slope'] > 0:
        print("Aggressive strategy profit INCREASES as theta increases (more defensive opponents)")
    else:
        print("Aggressive strategy profit DECREASES as theta increases")
    
    print("\n" + "=" * 60)
    
    # Generate plots
    plot_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plots", "experiment_3A")
    ensure_dir(plot_dir)
    
    # Calculate mean profits for each theta
    def_mean_profits = [np.mean(def_profits_by_theta[theta]) for theta in theta_values]
    agg_mean_profits = [np.mean(agg_profits_by_theta[theta]) for theta in theta_values]
    
    # θ vs Profit (line plot with both strategies)
    save_line_plot(
        theta_values,
        def_mean_profits,
        "Profit vs Composition (θ): Defensive Strategy",
        "θ (Proportion of Defensive Opponents)",
        "Mean Profit",
        os.path.join(plot_dir, "def_profit_vs_theta.png")
    )
    
    save_line_plot(
        theta_values,
        agg_mean_profits,
        "Profit vs Composition (θ): Aggressive Strategy",
        "θ (Proportion of Defensive Opponents)",
        "Mean Profit",
        os.path.join(plot_dir, "agg_profit_vs_theta.png")
    )
    
    # Combined plot
    save_line_plot(
        theta_values,
        def_mean_profits,
        "Profit vs Composition (θ): Both Strategies",
        "θ (Proportion of Defensive Opponents)",
        "Mean Profit",
        os.path.join(plot_dir, "profit_vs_theta_combined.png"),
        y2=agg_mean_profits,
        label1="Defensive",
        label2="Aggressive"
    )
    
    print(f"\nPlots saved to: {plot_dir}")


if __name__ == "__main__":
    main()
