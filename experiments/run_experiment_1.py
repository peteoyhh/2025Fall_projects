import os
import sys
import yaml
import numpy as np
from mahjong_sim.strategies import TempoDefender, ValueChaser
from mahjong_sim.real_mc import simulate_custom_table
from mahjong_sim.players import NeutralPolicy
from mahjong_sim.plotting import ensure_dir, save_bar_plot, save_hist, save_scatter_plot, save_kde_plot, save_stacked_fan_distribution
from mahjong_sim.utils import compare_strategies

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def build_players(test_strategy, test_label, cfg, neutral_thresholds=None):
    """
    Build 4-player table with 2v2 configuration:
    - 2 test players (DEF or AGG)
    - 2 neutral players (NEU)
    This provides a more balanced and fair comparison.
    """
    players = [
        {
            "strategy": test_strategy,
            "strategy_type": test_label
        },
        {
            "strategy": test_strategy,
            "strategy_type": test_label
        }
    ]
    for _ in range(2):
        players.append({
            "strategy": NeutralPolicy(seed=None, thresholds=neutral_thresholds),
            "strategy_type": "NEU"
        })
    return players


def summarize_trials(players_builder, cfg):
    """
    Summarize trials for 2v2 configuration.
    Aggregates statistics from both test players (positions 0 and 1).
    Also collects neutral players' fan distribution for total wins calculation.
    """
    profits = []
    win_rates = []
    deal_in_rates = []
    mean_fans = []
    fan_distributions = []
    neu_fan_distributions = []

    for _ in range(cfg["trials"]):
        players = players_builder()
        table_result = simulate_custom_table(players, cfg)
        # Aggregate stats from both test players (positions 0 and 1)
        tested_stats_0 = table_result["per_player"][0]
        tested_stats_1 = table_result["per_player"][1]
        
        # Average the two test players' stats
        profits.append((tested_stats_0["profit"] + tested_stats_1["profit"]) / 2)
        win_rates.append((tested_stats_0["win_rate"] + tested_stats_1["win_rate"]) / 2)
        deal_in_rates.append((tested_stats_0["deal_in_rate"] + tested_stats_1["deal_in_rate"]) / 2)
        mean_fans.append((tested_stats_0["mean_fan"] + tested_stats_1["mean_fan"]) / 2)
        
        # Collect fan distribution from both test players
        if "fan_distribution" in tested_stats_0:
            fan_distributions.extend(tested_stats_0["fan_distribution"])
        if "fan_distribution" in tested_stats_1:
            fan_distributions.extend(tested_stats_1["fan_distribution"])
        
        # Collect fan distribution from neutral players (positions 2 and 3)
        for i in [2, 3]:
            if i < len(table_result["per_player"]):
                neu_stats = table_result["per_player"][i]
                if "fan_distribution" in neu_stats:
                    neu_fan_distributions.extend(neu_stats["fan_distribution"])

    return {
        "profits": np.array(profits),
        "win_rates": np.array(win_rates),
        "deal_in_rates": np.array(deal_in_rates),
        "mean_fans": np.array(mean_fans),
        "fan_distribution": np.array(fan_distributions) if fan_distributions else np.array([]),
        "neu_fan_distribution": np.array(neu_fan_distributions) if neu_fan_distributions else np.array([]),
        # Also return means for backward compatibility
        "profit": np.mean(profits),
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
    print("Configuration: 2 test players vs 2 neutral players (2v2)")
    print("=" * 60)
    
    num_trials = cfg.get("trials")
    if num_trials is None:
        raise ValueError("trials must be specified in config")
    rounds_per_trial = cfg.get("rounds_per_trial")
    if rounds_per_trial is None:
        raise ValueError("rounds_per_trial must be specified in config")
    num_strategies = 2  # DEF and AGG
    total_trials = num_trials * num_strategies
    total_rounds = total_trials * rounds_per_trial
    
    print(f"\nRunning {num_trials} trials per strategy ({num_strategies} strategies)")
    print(f"Each trial consists of {rounds_per_trial} rounds")
    print(f"Table composition: 2 test players vs 2 neutral players")
    print(f"Total trials: {total_trials}")
    print(f"Total rounds: {total_rounds}\n")

    fan_min = cfg["fan_min"]
    t_fan_threshold = cfg["t_fan_threshold"]
    
    # Get strategy thresholds and weights from config
    strategy_cfg = cfg.get("strategy_thresholds", {})
    weights_cfg = cfg.get("scoring_weights", {})
    # Merge hand completion and post-discard weights into weights_cfg
    hand_completion_weights = cfg.get("hand_completion_weights", {})
    post_discard_weights = cfg.get("post_discard_weights", {})
    weights_cfg = {**weights_cfg, **hand_completion_weights, **post_discard_weights}
    tempo_thresholds = strategy_cfg.get("tempo_defender", {})
    value_thresholds = strategy_cfg.get("value_chaser", {})
    neutral_thresholds = strategy_cfg.get("neutral_policy", {})

    def def_builder():
        # Use TempoDefender strategy class for defensive play
        test_strategy = TempoDefender(thresholds=tempo_thresholds, weights=weights_cfg)
        return build_players(test_strategy, "DEF", cfg, neutral_thresholds)

    def agg_builder():
        # Use ValueChaser strategy class for aggressive play
        test_strategy = ValueChaser(target_threshold=t_fan_threshold, 
                                   thresholds=value_thresholds, 
                                   weights=weights_cfg)
        return build_players(test_strategy, "AGG", cfg, neutral_thresholds)

    def_results = summarize_trials(def_builder, cfg)
    agg_results = summarize_trials(agg_builder, cfg)

    print("\nDefensive Strategy Results:")
    print("  (All values are averages across all trials)")
    print(f"  Profit: {def_results['profit']:.2f}")
    print(f"  Win Rate: {def_results['win_rate']:.4f}")
    print(f"  Deal-in Rate: {def_results['deal_in_rate']:.4f}")
    print(f"  Mean Fan: {def_results['mean_fan']:.2f}")

    print("\nAggressive Strategy Results:")
    print("  (All values are averages across all trials)")
    print(f"  Profit: {agg_results['profit']:.2f}")
    print(f"  Win Rate: {agg_results['win_rate']:.4f}")
    print(f"  Deal-in Rate: {agg_results['deal_in_rate']:.4f}")
    print(f"  Mean Fan: {agg_results['mean_fan']:.2f}")

    # Statistical comparison
    results_def_for_comparison = {
        "profits": def_results["profits"],
        "win_rates": def_results["win_rates"],
        "mean_fans": def_results["mean_fans"]
    }
    results_agg_for_comparison = {
        "profits": agg_results["profits"],
        "win_rates": agg_results["win_rates"],
        "mean_fans": agg_results["mean_fans"]
    }
    
    comparison = compare_strategies(results_def_for_comparison, results_agg_for_comparison)
    
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
    
    # Bar chart: Relative Advantage (DEF vs AGG)
    # Calculate relative advantage: DEF advantage = DEF - AGG, AGG advantage = AGG - DEF
    def_advantage = def_results['profit'] - agg_results['profit']
    agg_advantage = agg_results['profit'] - def_results['profit']
    save_bar_plot(
        ["DEF", "AGG"],
        [def_advantage, agg_advantage],
        "Relative Advantage: Defensive vs Aggressive Strategy",
        os.path.join(plot_dir, "profit_comparison.png"),
        ylabel="Relative Advantage"
    )
    
    # Bar chart: Win rate (DEF vs AGG)
    save_bar_plot(
        ["DEF", "AGG"],
        [def_results['win_rate'], agg_results['win_rate']],
        "Win Rate Comparison: Defensive vs Aggressive Strategy",
        os.path.join(plot_dir, "win_rate_comparison.png"),
        ylabel="Win Rate"
    )
    
    # Stacked bar chart: Fan distribution separated by strategy
    def_fans = def_results['fan_distribution'] if len(def_results['fan_distribution']) > 0 else []
    agg_fans = agg_results['fan_distribution'] if len(agg_results['fan_distribution']) > 0 else []
    # Collect neutral players' fan distribution from both trials (use def_results as they have same neutral players)
    neu_fans = def_results.get('neu_fan_distribution', [])
    if len(neu_fans) == 0:
        neu_fans = agg_results.get('neu_fan_distribution', [])
    
    if len(def_fans) > 0 or len(agg_fans) > 0:
        save_stacked_fan_distribution(
            def_fans,
            agg_fans,
            "Fan Distribution by Strategy",
            os.path.join(plot_dir, "fan_distribution.png"),
            xlabel="Fan Value",
            ylabel="Frequency",
            neu_fans=neu_fans if len(neu_fans) > 0 else None
        )
    
    print(f"\nPlots saved to: {plot_dir}")


if __name__ == "__main__":
    main()
