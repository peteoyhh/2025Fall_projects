import os
import yaml
import numpy as np
from mahjong_sim.strategies import defensive_strategy, aggressive_strategy
from mahjong_sim.table import simulate_custom_table
from mahjong_sim.players import NeutralPolicy
from mahjong_sim.plotting import ensure_dir, save_bar_plot, save_hist


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
        "profit": np.mean(profits),
        "utility": np.mean(utilities),
        "win_rate": np.mean(win_rates),
        "deal_in_rate": np.mean(deal_in_rates),
        "mean_fan": np.mean(mean_fans),
        "fan_distribution": np.array(fan_distributions) if fan_distributions else np.array([])
    }


def main():
    with open("configs/base.yaml") as f:
        cfg = yaml.safe_load(f)

    print("=" * 60)
    print("Experiment 1: Strategy Performance (4-player table)")
    print("=" * 60)

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
    print(f"  Profit: {def_results['profit']:.2f}")
    print(f"  Utility: {def_results['utility']:.2f}")
    print(f"  Win Rate: {def_results['win_rate']:.4f}")
    print(f"  Deal-in Rate: {def_results['deal_in_rate']:.4f}")
    print(f"  Mean Fan: {def_results['mean_fan']:.2f}")

    print("\nAggressive Strategy Results:")
    print(f"  Profit: {agg_results['profit']:.2f}")
    print(f"  Utility: {agg_results['utility']:.2f}")
    print(f"  Win Rate: {agg_results['win_rate']:.4f}")
    print(f"  Deal-in Rate: {agg_results['deal_in_rate']:.4f}")
    print(f"  Mean Fan: {agg_results['mean_fan']:.2f}")

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
