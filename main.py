import sys
import os
import argparse
import contextlib
import yaml
from mahjong_sim.real_mc import run_multiple_trials
from mahjong_sim.strategies import TempoDefender, ValueChaser
from mahjong_sim.utils import compare_strategies, compute_statistics


def run_experiment_1(cfg):
    """Run Experiment 1: Strategy Comparison"""
    import experiments.run_experiment_1 as exp1
    exp1.main()


def run_experiment_2(cfg):
    """Run Experiment 2: Table Composition Analysis (4-player table)"""
    import experiments.run_experiment_2_table as exp2t
    exp2t.main()


def run_quick_demo(cfg):
    """Quick demonstration with single trial"""
    print("=" * 60)
    print("Quick Demo: Single Trial Comparison")
    print("=" * 60)
    
    print(f"\nRunning {cfg['rounds_per_trial']} rounds...")
    
    # Get strategy thresholds and weights from config
    strategy_cfg = cfg.get("strategy_thresholds", {})
    weights_cfg = cfg.get("scoring_weights", {})
    tempo_thresholds = strategy_cfg.get("tempo_defender", {})
    value_thresholds = strategy_cfg.get("value_chaser", {})
    
    # Use TempoDefender for defensive strategy
    results_def = run_multiple_trials(
        TempoDefender(thresholds=tempo_thresholds, weights=weights_cfg),
        cfg,
        num_trials=1
    )
    # Use ValueChaser for aggressive strategy
    results_agg = run_multiple_trials(
        ValueChaser(target_threshold=cfg["t_fan_threshold"], 
                   thresholds=value_thresholds, 
                   weights=weights_cfg),
        cfg,
        num_trials=1
    )
    
    print("\nDefensive Strategy Results:")
    print(f"  Profit: {results_def['profits'][0]:.2f}")
    print(f"  Mean Fan: {results_def['mean_fans'][0]:.2f}")
    print(f"  Win Rate: {results_def['win_rates'][0]:.4f}")
    
    print("\nAggressive Strategy Results:")
    print(f"  Profit: {results_agg['profits'][0]:.2f}")
    print(f"  Mean Fan: {results_agg['mean_fans'][0]:.2f}")
    print(f"  Win Rate: {results_agg['win_rates'][0]:.4f}")


class TeeStream:
    """Helper that duplicates stdout writes to multiple streams."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def run_with_logging(filename, func, cfg):
    # Create output directory if it doesn't exist
    project_root = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as outfile:
        tee = TeeStream(sys.stdout, outfile)
        with contextlib.redirect_stdout(tee):
            func(cfg)
    print(f"\nCompleted run. Output saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mahjong Strategy Simulation")
    parser.add_argument(
        "--experiment",
        type=int,
        choices=[1, 2],
        help="Run specific experiment (1 or 2)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all experiments"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run quick demo (single trial)"
    )
    
    args = parser.parse_args()
    
    with open("configs/base.yaml") as f:
        cfg = yaml.safe_load(f)
    
    if args.demo:
        run_quick_demo(cfg)
    elif args.experiment:
        experiment_map = {
            1: ("experiment1_output.txt", run_experiment_1),
            2: ("experiment2_output.txt", run_experiment_2),
        }
        filename, func = experiment_map[args.experiment]
        run_with_logging(filename, func, cfg)
    elif args.all:
        # Create output directory if it doesn't exist
        project_root = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(project_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "all_experiments_output.txt")
        with open(output_path, "w", encoding="utf-8") as outfile:
            tee = TeeStream(sys.stdout, outfile)
            with contextlib.redirect_stdout(tee):
                print("Running all experiments...\n")
                run_experiment_1(cfg)
                print("\n\n")
                print("Running Experiment 2: 4-player table composition analysis...\n")
                run_experiment_2(cfg)
        print(f"\nCompleted all experiments. Output saved to {output_path}")
    else:
        # Default: run quick demo
        print("No experiment specified. Running quick demo...")
        print("Use --experiment N to run experiment N, --all to run all, or --demo for quick demo\n")
        run_quick_demo(cfg)

