from typing import Dict, List, Union, Any
import numpy as np
from scipy import stats


def compute_statistics(data: np.ndarray) -> Dict[str, Union[float, int]]:
    """
    Compute summary statistics for a data array.
    
    Returns:
        Dictionary with mean, std, CI (95% confidence interval)
    """
    mean = np.mean(data)
    std = np.std(data, ddof=1)
    n = len(data)
    se = std / np.sqrt(n)
    ci_95 = stats.t.interval(0.95, n - 1, loc=mean, scale=se)
    
    return {
        "mean": mean,
        "std": std,
        "ci_95_lower": ci_95[0],
        "ci_95_upper": ci_95[1],
        "n": n
    }


def compare_strategies(results_def: Dict[str, np.ndarray], results_agg: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """
    Compare defensive and aggressive strategies using two-sample t-test.
    
    Returns:
        Dictionary with comparison statistics
    """
    # Profit comparison
    profit_stat = stats.ttest_ind(results_def["profits"], results_agg["profits"])
    profit_def_stats = compute_statistics(results_def["profits"])
    profit_agg_stats = compute_statistics(results_agg["profits"])
    
    # Utility comparison
    utility_stat = stats.ttest_ind(results_def["utilities"], results_agg["utilities"])
    utility_def_stats = compute_statistics(results_def["utilities"])
    utility_agg_stats = compute_statistics(results_agg["utilities"])
    
    return {
        "profit": {
            "t_statistic": profit_stat.statistic,
            "p_value": profit_stat.pvalue,
            "defensive": profit_def_stats,
            "aggressive": profit_agg_stats,
            "difference": profit_def_stats["mean"] - profit_agg_stats["mean"]
        },
        "utility": {
            "t_statistic": utility_stat.statistic,
            "p_value": utility_stat.pvalue,
            "defensive": utility_def_stats,
            "aggressive": utility_agg_stats,
            "difference": utility_agg_stats["mean"] - utility_def_stats["mean"]
        }
    }


def analyze_composition_effect(theta_values: List[float], profit_results: Dict[float, np.ndarray]) -> Dict[str, Any]:
    """
    Analyze the effect of table composition (theta) on strategy performance.
    
    Args:
        theta_values: Array of theta (proportion of defensive players) values
        profit_results: Dictionary mapping theta to profit arrays
    
    Returns:
        Regression results and statistics
    """
    # Prepare data for regression
    X = np.array(theta_values)
    Y = np.array([np.mean(profit_results[t]) for t in theta_values])
    
    # Simple linear regression: profit = a + b * theta
    slope, intercept, r_value, p_value, std_err = stats.linregress(X, Y)
    
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_value ** 2,
        "p_value": p_value,
        "std_err": std_err,
        "theta_values": theta_values,
        "mean_profits": Y
    }


