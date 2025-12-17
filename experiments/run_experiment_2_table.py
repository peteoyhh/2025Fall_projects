"""
Experiment 2: 4-Player Table Composition Analysis

Analyzes how strategy performance varies across different table compositions.

Simulates 5 different table compositions:
- θ=0: 4 AGG players
- θ=1: 3 DEF + 1 AGG
- θ=2: 2 DEF + 2 AGG
- θ=3: 1 DEF + 3 AGG
- θ=4: 4 DEF players
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import yaml
import numpy as np
from mahjong_sim.real_mc import run_composition_experiments
from mahjong_sim.utils import analyze_composition_effect, compute_statistics
from mahjong_sim.plotting import ensure_dir, save_line_plot, save_bar_plot, save_hist, save_stacked_fan_distribution


def main():
    config_path = os.path.join(project_root, "configs", "base.yaml")
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    
    print("=" * 70)
    print("Experiment 2: 4-Player Table Composition Analysis")
    print("Analyzing strategy performance across different table compositions (θ)")
    print("=" * 70)
    
    num_trials = cfg.get("trials")
    if num_trials is None:
        raise ValueError("trials must be specified in config")
    rounds_per_trial = cfg.get("rounds_per_trial")
    if rounds_per_trial is None:
        raise ValueError("rounds_per_trial must be specified in config")
    
    # Get experiment parameters from config
    experiment_cfg = cfg.get("experiment", {})
    num_compositions = experiment_cfg.get("num_compositions", 5)
    theta_values = experiment_cfg.get("theta_values", [0, 1, 2, 3, 4])
    total_trials = num_trials * num_compositions
    total_rounds = total_trials * rounds_per_trial
    
    print(f"\nRunning {num_trials} trials per composition ({num_compositions} compositions)")
    print(f"Each trial consists of {rounds_per_trial} rounds")
    print(f"Total trials: {total_trials}")
    print(f"Total rounds: {total_rounds}\n")
    
    results = run_composition_experiments(cfg, num_trials=num_trials)
    
    print("\n" + "=" * 70)
    print("RESULTS BY COMPOSITION")
    print("=" * 70)
    
    for composition in theta_values:
                num_def = composition
                num_agg = 4 - composition
                comp_results = results[composition]
                
                print(f"\n{'='*70}")
                print(f"Composition θ={composition}: {num_def} DEF, {num_agg} AGG")
                print(f"{'='*70}")
                
                if num_def > 0:
                    def_stats = comp_results["defensive"]
                    print(f"\nDEFENSIVE Players:")
                    print("  (All values are averages across all trials)")
                    print(f"  Mean Profit: {def_stats['mean_profit']:.2f} ± {def_stats['std_profit']:.2f}")
                    print(f"  Win Rate: {def_stats['win_rate']:.4f}")
                    print(f"  Deal-in Rate (as winner): {def_stats['deal_in_rate']:.4f}")
                    print(f"  Missed Hu Rate: {def_stats['missed_hu_rate']:.4f}")
                    print(f"  Mean Fan (when winning): {def_stats['mean_fan']:.2f}")
                
                if num_agg > 0:
                    agg_stats = comp_results["aggressive"]
                    print(f"\nAGGRESSIVE Players:")
                    print("  (All values are averages across all trials)")
                    print(f"  Mean Profit: {agg_stats['mean_profit']:.2f} ± {agg_stats['std_profit']:.2f}")
                    print(f"  Win Rate: {agg_stats['win_rate']:.4f}")
                    print(f"  Deal-in Rate (as winner): {agg_stats['deal_in_rate']:.4f}")
                    print(f"  Missed Hu Rate: {agg_stats['missed_hu_rate']:.4f}")
                    print(f"  Mean Fan (when winning): {agg_stats['mean_fan']:.2f}")

                dealer_stats = comp_results["dealer"]
                non_dealer_stats = comp_results["non_dealer"]

                print(f"\nDEALER ROUNDS:")
                print("  (All values are averages across all dealer rounds)")
                print(f"  Mean Profit: {dealer_stats['mean_profit']:.2f} ± {dealer_stats['std_profit']:.2f}")
                print(f"  Win Rate: {dealer_stats['win_rate']:.4f}")
                print(f"  Deal-in Rate (as winner): {dealer_stats['deal_in_rate']:.4f}")
                print(f"  Deal-in Loss Rate: {dealer_stats['deal_in_loss_rate']:.4f}")
                print(f"  Missed Hu Rate: {dealer_stats['missed_hu_rate']:.4f}")

                print(f"\nNON-DEALER ROUNDS:")
                print("  (All values are averages across all non-dealer rounds)")
                print(f"  Mean Profit: {non_dealer_stats['mean_profit']:.2f} ± {non_dealer_stats['std_profit']:.2f}")
                print(f"  Win Rate: {non_dealer_stats['win_rate']:.4f}")
                print(f"  Deal-in Rate (as winner): {non_dealer_stats['deal_in_rate']:.4f}")
                print(f"  Deal-in Loss Rate: {non_dealer_stats['deal_in_loss_rate']:.4f}")
                print(f"  Missed Hu Rate: {non_dealer_stats['missed_hu_rate']:.4f}")
    
    print("\n" + "=" * 70)
    print("REGRESSION ANALYSIS")
    print("=" * 70)
    
    regression_samples = experiment_cfg.get("regression_samples", 100)
    def_profits_for_regression = {}
    agg_profits_for_regression = {}
    
    for theta in theta_values:
                comp_results = results[theta]
                if len(comp_results["defensive"]["fan_distribution"]) > 0:
                    mean = comp_results["defensive"]["mean_profit"]
                    std = comp_results["defensive"]["std_profit"]
                    def_profits_for_regression[theta] = np.random.normal(mean, std, regression_samples)
                
                if len(comp_results["aggressive"]["fan_distribution"]) > 0:
                    mean = comp_results["aggressive"]["mean_profit"]
                    std = comp_results["aggressive"]["std_profit"]
                    agg_profits_for_regression[theta] = np.random.normal(mean, std, regression_samples)
    
    if len(def_profits_for_regression) > 1:
        def_regression = analyze_composition_effect(
            list(def_profits_for_regression.keys()),
            def_profits_for_regression
        )
        print("\nDefensive Strategy:")
        print(f"  Slope: {def_regression['slope']:.2f}")
        print(f"  R-squared: {def_regression['r_squared']:.4f}")
        print(f"  p-value: {def_regression['p_value']:.6f}")
    
    if len(agg_profits_for_regression) > 1:
        agg_regression = analyze_composition_effect(
            list(agg_profits_for_regression.keys()),
            agg_profits_for_regression
        )
        print("\nAggressive Strategy:")
        print(f"  Slope: {agg_regression['slope']:.2f}")
        print(f"  R-squared: {agg_regression['r_squared']:.4f}")
        print(f"  p-value: {agg_regression['p_value']:.6f}")
    
    print("\n" + "=" * 70)
    print("SUMMARY TABLE")
    print("=" * 70)
    print(f"\n{'θ':<5} {'DEF Profit':<15} {'AGG Profit':<15} {'Dealer Profit':<15} {'NonDealer Profit':<17}")
    print("-" * 70)
    
    for theta in sorted(theta_values):
        comp_results = results[theta]
        # Show mean_profit directly - it's already 0.0 if no players of that type
        def_profit = comp_results["defensive"]["mean_profit"]
        agg_profit = comp_results["aggressive"]["mean_profit"]
        dealer_profit = comp_results["dealer"]["mean_profit"]
        non_dealer_profit = comp_results["non_dealer"]["mean_profit"]
        
        print(f"{theta:<5} {def_profit:<15.2f} {agg_profit:<15.2f} {dealer_profit:<15.2f} {non_dealer_profit:<17.2f}")
    
    print("\n" + "=" * 70)
    print("INTERPRETATION")
    print("=" * 70)
    
    if len(agg_profits_for_regression) > 1:
        if agg_regression['slope'] > 0:
            print("\nAggressive strategy profit INCREASES as θ increases")
            print("   (More defensive opponents → Better aggressive performance)")
        else:
            print("\nAggressive strategy profit DECREASES as θ increases")
            print("   (More defensive opponents → Worse aggressive performance)")
    
    print("\n" + "=" * 70)
    
    # Generate plots
    plot_dir = os.path.join(project_root, "plots", "experiment_2")
    ensure_dir(plot_dir)

    # Extract data for plotting
    def_profits = []
    agg_profits = []
    def_win_rates = []
    agg_win_rates = []
    dealer_profits = []
    non_dealer_profits = []
    all_def_fans = []
    all_agg_fans = []
    
    for theta in sorted(theta_values):
        comp_results = results[theta]
        if len(comp_results["defensive"]["fan_distribution"]) > 0:
            def_profits.append(comp_results["defensive"]["mean_profit"])
            def_win_rates.append(comp_results["defensive"]["win_rate"])
        else:
            def_profits.append(0.0)
            def_win_rates.append(0.0)
        
        if len(comp_results["aggressive"]["fan_distribution"]) > 0:
            agg_profits.append(comp_results["aggressive"]["mean_profit"])
            agg_win_rates.append(comp_results["aggressive"]["win_rate"])
        else:
            agg_profits.append(0.0)
            agg_win_rates.append(0.0)
        
        dealer_profits.append(comp_results["dealer"]["mean_profit"])
        non_dealer_profits.append(comp_results["non_dealer"]["mean_profit"])
        
        # Collect fan distributions separately for DEF and AGG
        all_def_fans.extend([f for f in comp_results["defensive"]["fan_distribution"] if f > 0])
        all_agg_fans.extend([f for f in comp_results["aggressive"]["fan_distribution"] if f > 0])
    
    # θ vs Profit (DEF vs AGG) - Combined plot only
    save_line_plot(
        theta_values,
        def_profits,
        "Profit vs Composition (θ): Both Strategies",
        "θ (Number of DEF Players)",
        "Mean Profit",
        os.path.join(plot_dir, "profit_vs_theta_combined.png"),
        y2=agg_profits,
        label1="Defensive",
        label2="Aggressive"
    )
    
    # θ vs Win Rate
    save_line_plot(
        theta_values,
        def_win_rates,
        "Win Rate vs Composition (θ): Both Strategies",
        "θ (Number of DEF Players)",
        "Win Rate",
        os.path.join(plot_dir, "win_rate_vs_theta_combined.png"),
        y2=agg_win_rates,
        label1="Defensive",
        label2="Aggressive"
    )
    
    # Bar chart: Relative Advantage (DEF vs AGG) - average across all compositions
    avg_def_profit = np.mean(def_profits)
    avg_agg_profit = np.mean(agg_profits)
    def_advantage = avg_def_profit - avg_agg_profit
    agg_advantage = avg_agg_profit - avg_def_profit
    save_bar_plot(
        ["DEF", "AGG"],
        [def_advantage, agg_advantage],
        "Relative Advantage: Defensive vs Aggressive Strategy (Average Across All Compositions)",
        os.path.join(plot_dir, "profit_comparison.png"),
        ylabel="Relative Advantage"
    )
    
    # Bar chart: Dealer vs Non-dealer profit (average across all compositions)
    avg_dealer_profit = np.mean(dealer_profits)
    avg_non_dealer_profit = np.mean(non_dealer_profits)
    save_bar_plot(
        ["Dealer", "Non-Dealer"],
        [avg_dealer_profit, avg_non_dealer_profit],
        "Average Profit: Dealer vs Non-Dealer",
        os.path.join(plot_dir, "dealer_vs_non_dealer_profit.png"),
        ylabel="Mean Profit"
    )
    
    # Stacked bar chart: Overall fan distribution separated by strategy
    # Note: Experiment 2 has no neutral players (pure DEF vs AGG), so neu_fans=None
    if len(all_def_fans) > 0 or len(all_agg_fans) > 0:
        save_stacked_fan_distribution(
            all_def_fans,
            all_agg_fans,
            "Overall Fan Distribution by Strategy (All Compositions)",
            os.path.join(plot_dir, "fan_distribution.png"),
            xlabel="Fan Value",
            ylabel="Frequency",
            neu_fans=None  # Experiment 2 has no neutral players
        )
            
    print(f"\nPlots saved to: {plot_dir}")


if __name__ == "__main__":
    main()
