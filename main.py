import sys
import os
import argparse
import contextlib
import yaml
from mahjong_sim.real_mc import run_multiple_trials
from mahjong_sim.strategies import defensive_strategy, aggressive_strategy
from mahjong_sim.utils import compare_strategies, compute_statistics


def run_experiment_1(cfg):
    """Run Experiment 1: Strategy Comparison"""
    import experiments.run_experiment_1 as exp1
    exp1.main()


def run_experiment_3(cfg):
    """Run Experiment 3: Table Composition Analysis (4-player table)"""
    import experiments.run_experiment_3_table as exp3t
    exp3t.main()


def run_experiment_4(cfg):
    """Run Experiment 4: Sensitivity Analysis"""
    import experiments.run_sensitivity as exp4
    exp4.main()


def run_quick_demo(cfg):
    """Quick demonstration with single trial"""
    print("=" * 60)
    print("Quick Demo: Single Trial Comparison")
    print("=" * 60)
    
    print(f"\nRunning {cfg['rounds_per_trial']} rounds...")
    results_def = run_multiple_trials(
        lambda f: defensive_strategy(f, cfg["fan_min"]),
        cfg,
        num_trials=1
    )
    results_agg = run_multiple_trials(
        lambda f: aggressive_strategy(f, cfg["t_fan_threshold"]),
        cfg,
        num_trials=1
    )
    
    print("\nDefensive Strategy Results:")
    print(f"  Profit: {results_def['profits'][0]:.2f}")
    print(f"  Utility: {results_def['utilities'][0]:.2f}")
    print(f"  Mean Fan: {results_def['mean_fans'][0]:.2f}")
    print(f"  Win Rate: {results_def['win_rates'][0]:.4f}")
    
    print("\nAggressive Strategy Results:")
    print(f"  Profit: {results_agg['profits'][0]:.2f}")
    print(f"  Utility: {results_agg['utilities'][0]:.2f}")
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
        choices=[1, 3, 4],
        help="Run specific experiment (1, 3, or 4)"
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
            3: ("experiment3_output.txt", run_experiment_3),
            4: ("experiment4_output.txt", run_experiment_4),
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
                print("Running Experiment 3: 4-player table composition analysis...\n")
                run_experiment_3(cfg)
                print("\n\n")
                run_experiment_4(cfg)
        print(f"\nCompleted all experiments. Output saved to {output_path}")
    else:
        # Default: run quick demo
        print("No experiment specified. Running quick demo...")
        print("Use --experiment N to run experiment N, --all to run all, or --demo for quick demo\n")
        run_quick_demo(cfg)

