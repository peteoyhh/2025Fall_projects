import os
import sys
import yaml
import numpy as np
from mahjong_sim.strategies import defensive_strategy, aggressive_strategy
from mahjong_sim.real_mc import simulate_custom_table
from mahjong_sim.players import NeutralPolicy
from mahjong_sim.plotting import ensure_dir, save_bar_plot, save_hist, save_scatter_plot, save_kde_plot
from mahjong_sim.utils import compare_strategies

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def build_players(test_strategy, test_label, cfg):
    players = [{
        "strategy": test_strategy,
        "strategy_type": test_label
    }]
    for _ in range(3):
        seed = int(np.random.randint(0, 2**32 - 1))
        players.append({
            "strategy": NeutralPolicy(seed=seed),
            "strategy_type": "NEU"
        })
    return players


def summarize_trials(players_builder, cfg):
    profits = []
    utilities = []
    win_rates = []
    deal_in_rates = []
    mean_fans = []
    fan_distributions = []

    for _ in range(cfg["trials"]):
        players = players_builder()
        table_result = simulate_custom_table(players, cfg)
        tested_stats = table_result["per_player"][0]
        profits.append(tested_stats["profit"])
        utilities.append(tested_stats["utility"])
        win_rates.append(tested_stats["win_rate"])
        deal_in_rates.append(tested_stats["deal_in_rate"])
        mean_fans.append(tested_stats["mean_fan"])
        # Collect fan distribution if available
        if "fan_distribution" in tested_stats:
            fan_distributions.extend(tested_stats["fan_distribution"])

    return {
        "profits": np.array(profits),
        "utilities": np.array(utilities),
        "win_rates": np.array(win_rates),
        "deal_in_rates": np.array(deal_in_rates),
        "mean_fans": np.array(mean_fans),
        "fan_distribution": np.array(fan_distributions) if fan_distributions else np.array([]),
        # Also return means for backward compatibility
        "profit": np.mean(profits),
        "utility": np.mean(utilities),
        "win_rate": np.mean(win_rates),
        "deal_in_rate": np.mean(deal_in_rates),
        "mean_fan": np.mean(mean_fans)
    }


def main():
    config_path = os.path.join(project_root, "configs", "base.yaml")
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    print("=" * 60)
    print("Experiment 1: Strategy Performance (4-player table)")
    print("=" * 60)
    
    num_trials = cfg.get("trials", 10)
    rounds_per_trial = cfg.get("rounds_per_trial", 20)
    num_strategies = 2  # DEF and AGG
    total_trials = num_trials * num_strategies
    total_rounds = total_trials * rounds_per_trial
    
    print(f"\nRunning {num_trials} trials per strategy ({num_strategies} strategies)")
    print(f"Each trial consists of {rounds_per_trial} rounds")
    print(f"Total trials: {total_trials}")
    print(f"Total rounds: {total_rounds}\n")

    fan_min = cfg["fan_min"]
    t_fan_threshold = cfg["t_fan_threshold"]

    def def_builder():
        test_strategy = lambda f, fm=fan_min: defensive_strategy(f, fm)
        return build_players(test_strategy, "DEF", cfg)

    def agg_builder():
        test_strategy = lambda f, th=t_fan_threshold: aggressive_strategy(f, th)
        return build_players(test_strategy, "AGG", cfg)

    def_results = summarize_trials(def_builder, cfg)
    agg_results = summarize_trials(agg_builder, cfg)

    print("\nDefensive Strategy Results:")
    print("  (All values are averages across all trials)")
    print(f"  Profit: {def_results['profit']:.2f}")
    print(f"  Utility: {def_results['utility']:.2f}")
    print(f"  Win Rate: {def_results['win_rate']:.4f}")
    print(f"  Deal-in Rate: {def_results['deal_in_rate']:.4f}")
    print(f"  Mean Fan: {def_results['mean_fan']:.2f}")

    print("\nAggressive Strategy Results:")
    print("  (All values are averages across all trials)")
    print(f"  Profit: {agg_results['profit']:.2f}")
    print(f"  Utility: {agg_results['utility']:.2f}")
    print(f"  Win Rate: {agg_results['win_rate']:.4f}")
    print(f"  Deal-in Rate: {agg_results['deal_in_rate']:.4f}")
    print(f"  Mean Fan: {agg_results['mean_fan']:.2f}")

    # Statistical comparison using utility
    results_def_for_comparison = {
        "profits": def_results["profits"],
        "utilities": def_results["utilities"],
        "win_rates": def_results["win_rates"],
        "mean_fans": def_results["mean_fans"]
    }
    results_agg_for_comparison = {
        "profits": agg_results["profits"],
        "utilities": agg_results["utilities"],
        "win_rates": agg_results["win_rates"],
        "mean_fans": agg_results["mean_fans"]
    }
    
    comparison = compare_strategies(results_def_for_comparison, results_agg_for_comparison)
    
    print("\n" + "-" * 60)
    print("STATISTICAL COMPARISON:")
    print("-" * 60)
    print(f"Defensive Strategy:")
    print(f"  Mean Utility: {comparison['utility']['defensive']['mean']:.2f}")
    print(f"  95% CI: [{comparison['utility']['defensive']['ci_95_lower']:.2f}, {comparison['utility']['defensive']['ci_95_upper']:.2f}]")
    print(f"\nAggressive Strategy:")
    print(f"  Mean Utility: {comparison['utility']['aggressive']['mean']:.2f}")
    print(f"  95% CI: [{comparison['utility']['aggressive']['ci_95_lower']:.2f}, {comparison['utility']['aggressive']['ci_95_upper']:.2f}]")
    print(f"\nDifference (Agg - Def): {comparison['utility']['difference']:.2f}")
    print(f"t-statistic: {comparison['utility']['t_statistic']:.4f}")
    print(f"p-value: {comparison['utility']['p_value']:.6f}")
    
    print("\n" + "-" * 60)
    print("PROFIT COMPARISON:")
    print("-" * 60)
    print(f"Defensive Mean: {comparison['profit']['defensive']['mean']:.2f}")
    print(f"Aggressive Mean: {comparison['profit']['aggressive']['mean']:.2f}")
    print(f"Difference (Def - Agg): {comparison['profit']['difference']:.2f}")
    print(f"t-statistic: {comparison['profit']['t_statistic']:.4f}")
    print(f"p-value: {comparison['profit']['p_value']:.6f}")

    print("\n" + "=" * 60)
    
    # Generate plots
    plot_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plots", "experiment_1")
    ensure_dir(plot_dir)
    
    # Bar chart: Profit (DEF vs AGG)
    save_bar_plot(
        ["DEF", "AGG"],
        [def_results['profit'], agg_results['profit']],
        "Profit Comparison: Defensive vs Aggressive Strategy",
        os.path.join(plot_dir, "profit_comparison.png"),
        ylabel="Profit"
    )
    
    # Bar chart: Utility (DEF vs AGG)
    save_bar_plot(
        ["DEF", "AGG"],
        [def_results['utility'], agg_results['utility']],
        "Utility Comparison: Defensive vs Aggressive Strategy",
        os.path.join(plot_dir, "utility_comparison.png"),
        ylabel="Utility"
    )
    
    # Bar chart: Win rate (DEF vs AGG)
    save_bar_plot(
        ["DEF", "AGG"],
        [def_results['win_rate'], agg_results['win_rate']],
        "Win Rate Comparison: Defensive vs Aggressive Strategy",
        os.path.join(plot_dir, "win_rate_comparison.png"),
        ylabel="Win Rate"
    )
    
    # KDE plot: Utility distribution (separated by strategy)
    # Better for large number of trials (e.g., 1000+)
    save_kde_plot(
        data_dict={
            "Defensive": def_results['utilities'],
            "Aggressive": agg_results['utilities']
        },
        title="Utility Distribution by Strategy",
        outfile=os.path.join(plot_dir, "utility_distribution.png"),
        xlabel="Utility",
        ylabel="Density"
    )
    
    # Scatter plot: Profit vs Utility (with fit lines, separated by strategy)
    save_scatter_plot(
        def_results['profits'],
        def_results['utilities'],
        "Profit vs Utility",
        "Profit",
        "Utility",
        os.path.join(plot_dir, "profit_vs_utility.png"),
        alpha=0.5,
        fit_line=True,
        x2=agg_results['profits'],
        y2=agg_results['utilities'],
        label1="Defensive",
        label2="Aggressive"
    )
    
    # Histogram: Fan distribution (combined from both strategies)
    all_fans = []
    if len(def_results['fan_distribution']) > 0:
        all_fans.extend(def_results['fan_distribution'])
    if len(agg_results['fan_distribution']) > 0:
        all_fans.extend(agg_results['fan_distribution'])
    
    if len(all_fans) > 0:
        # Filter out zeros for fan distribution
        all_fans = [f for f in all_fans if f > 0]
        if len(all_fans) > 0:
            save_hist(
                all_fans,
                "Fan Distribution (Tested Players)",
                os.path.join(plot_dir, "fan_distribution.png"),
                xlabel="Fan Value",
                ylabel="Frequency",
                bins=15
            )
    
    print(f"\nPlots saved to: {plot_dir}")


if __name__ == "__main__":
    main()
