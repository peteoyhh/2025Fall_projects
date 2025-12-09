import os
import yaml
import numpy as np
from mahjong_sim.simulation import run_multiple_trials
from mahjong_sim.strategies import defensive_strategy, aggressive_strategy
from mahjong_sim.utils import compute_statistics
from mahjong_sim.plotting import ensure_dir, save_line_plot


def main():
    with open("configs/base.yaml") as f:
        base_cfg = yaml.safe_load(f)
    print("=" * 60)
    print("Experiment 4: Sensitivity Analysis")
    print("Varying key parameters: P (penalty), alpha, and fan threshold")
    print("=" * 60)
    
    # Sensitivity to deal-in penalty (P)
    print("\n" + "-" * 60)
    print("SENSITIVITY TO DEAL-IN PENALTY (P):")
    print("-" * 60)
    penalty_values = [1, 2, 3, 4, 5]
    penalty_def_profits = []
    penalty_agg_profits = []
    
    for penalty in penalty_values:
        cfg = base_cfg.copy()
        cfg["penalty_deal_in"] = penalty
        
        print(f"\nPenalty = {penalty}:")
        results_def = run_multiple_trials(
            lambda f: defensive_strategy(f, cfg["fan_min"]),
            cfg,
            num_trials=10
        )
        results_agg = run_multiple_trials(
            lambda f: aggressive_strategy(f, cfg["t_fan_threshold"]),
            cfg,
            num_trials=10
        )
        
        def_stats = compute_statistics(results_def["profits"])
        agg_stats = compute_statistics(results_agg["profits"])
        
        penalty_def_profits.append(def_stats['mean'])
        penalty_agg_profits.append(agg_stats['mean'])
        
        print(f"  Defensive mean profit: {def_stats['mean']:.2f}")
        print(f"  Aggressive mean profit: {agg_stats['mean']:.2f}")
        print(f"  Difference (Def - Agg): {def_stats['mean'] - agg_stats['mean']:.2f}")
    
    # Sensitivity to alpha (fan growth rate / utility weight)
    print("\n" + "-" * 60)
    print("SENSITIVITY TO ALPHA (utility weight):")
    print("-" * 60)
    alpha_values = [0.1, 0.3, 0.5, 0.7, 0.9]
    alpha_def_utilities = []
    alpha_agg_utilities = []
    
    for alpha in alpha_values:
        cfg = base_cfg.copy()
        cfg["alpha"] = alpha
        
        print(f"\nAlpha = {alpha}:")
        results_def = run_multiple_trials(
            lambda f: defensive_strategy(f, cfg["fan_min"]),
            cfg,
            num_trials=10
        )
        results_agg = run_multiple_trials(
            lambda f: aggressive_strategy(f, cfg["t_fan_threshold"]),
            cfg,
            num_trials=10
        )
        
        def_stats = compute_statistics(results_def["utilities"])
        agg_stats = compute_statistics(results_agg["utilities"])
        
        alpha_def_utilities.append(def_stats['mean'])
        alpha_agg_utilities.append(agg_stats['mean'])
        
        print(f"  Defensive mean utility: {def_stats['mean']:.2f}")
        print(f"  Aggressive mean utility: {agg_stats['mean']:.2f}")
        print(f"  Difference (Agg - Def): {agg_stats['mean'] - def_stats['mean']:.2f}")
    
    # Sensitivity to fan threshold (for aggressive strategy)
    print("\n" + "-" * 60)
    print("SENSITIVITY TO FAN THRESHOLD (t_fan_threshold):")
    print("-" * 60)
    threshold_values = [1, 2, 3, 4, 5]
    threshold_agg_profits = []
    threshold_agg_utilities = []
    
    for threshold in threshold_values:
        cfg = base_cfg.copy()
        cfg["t_fan_threshold"] = threshold
        
        print(f"\nThreshold = {threshold}:")
        results_agg = run_multiple_trials(
            lambda f: aggressive_strategy(f, threshold),
            cfg,
            num_trials=10
        )
        
        agg_stats = compute_statistics(results_agg["profits"])
        agg_util_stats = compute_statistics(results_agg["utilities"])
        win_rate = np.mean(results_agg["win_rates"])
        
        threshold_agg_profits.append(agg_stats['mean'])
        threshold_agg_utilities.append(agg_util_stats['mean'])
        
        print(f"  Aggressive mean profit: {agg_stats['mean']:.2f}")
        print(f"  Win rate: {win_rate:.4f}")
        print(f"  Mean fan: {np.mean(results_agg['mean_fans']):.2f}")
    
    # Sensitivity to base_points
    print("\n" + "-" * 60)
    print("SENSITIVITY TO BASE POINTS:")
    print("-" * 60)
    base_values = [1, 2, 4]
    
    for base in base_values:
        cfg = base_cfg.copy()
        cfg["base_points"] = base
        
        print(f"\nBase points = {base}:")
        results_def = run_multiple_trials(
            lambda f: defensive_strategy(f, cfg["fan_min"]),
            cfg,
            num_trials=10
        )
        results_agg = run_multiple_trials(
            lambda f: aggressive_strategy(f, cfg["t_fan_threshold"]),
            cfg,
            num_trials=10
        )
        
        def_stats = compute_statistics(results_def["profits"])
        agg_stats = compute_statistics(results_agg["profits"])
        
        print(f"  Defensive mean profit: {def_stats['mean']:.2f}")
        print(f"  Aggressive mean profit: {agg_stats['mean']:.2f}")
    
    print("\n" + "=" * 60)
    print("Sensitivity analysis complete!")
    
    # Generate plots
    plot_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plots", "experiment_4")
    ensure_dir(plot_dir)
    
    # Parameter vs Profit (penalty)
    save_line_plot(
        penalty_values,
        penalty_def_profits,
        "Profit vs Deal-in Penalty (P): Both Strategies",
        "Penalty (P)",
        "Mean Profit",
        os.path.join(plot_dir, "profit_vs_penalty.png"),
        y2=penalty_agg_profits,
        label1="Defensive",
        label2="Aggressive"
    )
    
    # Parameter vs Utility (alpha)
    save_line_plot(
        alpha_values,
        alpha_def_utilities,
        "Utility vs Alpha: Both Strategies",
        "Alpha (Utility Weight)",
        "Mean Utility",
        os.path.join(plot_dir, "utility_vs_alpha.png"),
        y2=alpha_agg_utilities,
        label1="Defensive",
        label2="Aggressive"
    )
    
    # Parameter vs Profit (threshold)
    save_line_plot(
        threshold_values,
        threshold_agg_profits,
        "Profit vs Fan Threshold (Aggressive Strategy)",
        "Fan Threshold",
        "Mean Profit",
        os.path.join(plot_dir, "profit_vs_threshold.png")
    )
    
    # Parameter vs Utility (threshold)
    save_line_plot(
        threshold_values,
        threshold_agg_utilities,
        "Utility vs Fan Threshold (Aggressive Strategy)",
        "Fan Threshold",
        "Mean Utility",
        os.path.join(plot_dir, "utility_vs_threshold.png")
    )
    
    print(f"\nPlots saved to: {plot_dir}")


if __name__ == "__main__":
    main()
