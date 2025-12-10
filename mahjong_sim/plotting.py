"""
Plotting utilities for Mahjong Monte-Carlo experiments.

All plots are saved as PNG files (dpi=200) in non-interactive mode.
"""

import os
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np


def ensure_dir(path):
    """Ensure directory exists, create if it doesn't."""
    os.makedirs(path, exist_ok=True)


def save_line_plot(x, y, title, xlabel, ylabel, outfile, y2=None, label1=None, label2=None, legend=True, color1=None, color2=None):
    """
    Save a line plot.
    
    Args:
        x: X-axis values
        y: Y-axis values (single line)
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        outfile: Output file path
        y2: Optional second Y-axis values for dual-line plot
        label1: Optional label for first line (default: ylabel if no y2, else 'Line 1')
        label2: Optional label for second line
        legend: Whether to show legend
        color1: Optional color for first line (auto-assigned based on label if None)
        color2: Optional color for second line (auto-assigned based on label if None)
    """
    plt.figure(figsize=(8, 6))
    # Use label1 if provided, otherwise use ylabel if no y2, else default to 'Line 1'
    first_label = label1 if label1 is not None else (ylabel if not y2 else 'Line 1')
    
    # Auto-assign colors based on labels if not provided
    if color1 is None:
        if first_label and ('defensive' in first_label.lower() or 'def' in first_label.lower()):
            color1 = 'green'
        elif first_label and ('aggressive' in first_label.lower() or 'agg' in first_label.lower()):
            color1 = 'red'
        else:
            color1 = '#1f77b4'  # Default blue
    
    plt.plot(x, y, marker='o', linewidth=2, markersize=6, label=first_label, color=color1)
    
    if y2 is not None:
        second_label = label2 or 'Line 2'
        # Auto-assign color for second line
        if color2 is None:
            if second_label and ('defensive' in second_label.lower() or 'def' in second_label.lower()):
                color2 = 'green'
            elif second_label and ('aggressive' in second_label.lower() or 'agg' in second_label.lower()):
                color2 = 'red'
            else:
                color2 = '#ff7f0e'  # Default orange
        plt.plot(x, y2, marker='s', linewidth=2, markersize=6, label=second_label, color=color2)
    
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel if y2 is None else 'Value', fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    if legend and (y2 is not None or label2 is not None):
        plt.legend()
    
    plt.tight_layout()
    plt.savefig(outfile, dpi=200, bbox_inches='tight')
    plt.close()


def save_bar_plot(labels, values, title, outfile, ylabel="Value", color=None):
    """
    Save a bar chart.
    
    Args:
        labels: X-axis labels
        values: Y-axis values
        title: Plot title
        outfile: Output file path
        ylabel: Y-axis label
        color: Bar color (optional)
    """
    plt.figure(figsize=(8, 6))
    bars = plt.bar(labels, values, color=color, alpha=0.7, edgecolor='black', linewidth=1.5)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom', fontsize=10)
    
    plt.xlabel('Category', fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(outfile, dpi=200, bbox_inches='tight')
    plt.close()


def save_hist(data=None, title=None, outfile=None, xlabel="Value", ylabel="Frequency", bins=20, density=False, 
              data_dict=None, labels=None, colors=None):
    """
    Save a histogram.
    
    Args:
        data: Data array (list or numpy array) - for single histogram
        title: Plot title
        outfile: Output file path
        xlabel: X-axis label
        ylabel: Y-axis label
        bins: Number of bins
        density: Whether to normalize as density
        data_dict: Optional dictionary of {label: data_array} for multiple histograms
        labels: Optional list of labels (used with data_dict)
        colors: Optional list of colors for different series
    """
    plt.figure(figsize=(8, 6))
    
    # If data_dict is provided, plot multiple histograms
    if data_dict is not None:
        default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        if colors is None:
            colors = default_colors
        
        # Collect all data to determine common bin edges for consistent comparison
        all_data = []
        data_list = []
        labels_list = []
        for label, series_data in data_dict.items():
            if not isinstance(series_data, np.ndarray):
                series_data = np.array(series_data)
            series_data = series_data[np.isfinite(series_data)]
            if len(series_data) > 0:
                all_data.extend(series_data)
                data_list.append(series_data)
                labels_list.append(label)
        
        if len(all_data) == 0:
            print(f"Warning: No valid data for histogram: {title}")
            plt.close()
            return
        
        # Use common bin edges for all histograms to ensure fair comparison
        all_data = np.array(all_data)
        _, bin_edges = np.histogram(all_data, bins=bins)
        
        # Plot each histogram with common bins, using step style for better visibility
        for i, (label, series_data) in enumerate(zip(labels_list, data_list)):
            counts, _ = np.histogram(series_data, bins=bin_edges, density=density)
            # Use step plot for clearer visibility when overlapping
            plt.step(bin_edges[:-1], counts, where='post', linewidth=2, 
                    label=label, color=colors[i % len(colors)], alpha=0.8)
            # Fill under the step for better visual effect
            plt.fill_between(bin_edges[:-1], counts, step='post', 
                           alpha=0.3, color=colors[i % len(colors)])
        
        plt.legend()
    else:
        # Single histogram
        if data is None:
            print(f"Warning: No data provided for histogram: {title}")
            plt.close()
            return
        
        # Convert to numpy array if needed
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        
        # Filter out any NaN or inf values
        data = data[np.isfinite(data)]
        
        if len(data) == 0:
            print(f"Warning: No valid data for histogram: {title}")
            plt.close()
            return
        
        plt.hist(data, bins=bins, density=density, alpha=0.7, edgecolor='black', linewidth=1.5)
    
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(outfile, dpi=200, bbox_inches='tight')
    plt.close()


def save_scatter_plot(x, y, title, xlabel, ylabel, outfile, alpha=0.5, fit_line=False, 
                     x2=None, y2=None, label1=None, label2=None):
    """
    Save a scatter plot.
    
    Args:
        x: X-axis values (list or numpy array)
        y: Y-axis values (list or numpy array)
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        outfile: Output file path
        alpha: Transparency (0-1)
        fit_line: Whether to add linear fit line
        x2: Optional second X-axis values for dual scatter plot
        y2: Optional second Y-axis values for dual scatter plot
        label1: Optional label for first series
        label2: Optional label for second series
    """
    from scipy import stats
    
    # Convert to numpy arrays if needed
    if not isinstance(x, np.ndarray):
        x = np.array(x)
    if not isinstance(y, np.ndarray):
        y = np.array(y)
    
    # Ensure same length
    if len(x) != len(y):
        min_len = min(len(x), len(y))
        x = x[:min_len]
        y = y[:min_len]
    
    # Filter out any NaN or inf values
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    
    if len(x) == 0:
        print(f"Warning: No valid data for scatter plot: {title}")
        return
    
    plt.figure(figsize=(8, 6))
    
    # Determine colors based on labels
    # Default: first series green (Defensive), second series red (Aggressive)
    color1 = 'green' if label1 and 'defensive' in label1.lower() else 'blue'
    color2 = 'red' if label2 and 'aggressive' in label2.lower() else 'orange'
    
    # Plot first series
    plt.scatter(x, y, alpha=alpha, s=20, label=label1, color=color1)
    
    # Add fit line for first series if requested
    if fit_line and len(x) > 1:
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        line_x = np.linspace(x.min(), x.max(), 100)
        line_y = slope * line_x + intercept
        plt.plot(line_x, line_y, color=color1, linestyle='--', linewidth=2, 
                label=f'Fit (R²={r_value**2:.3f})' if label1 is None else f'{label1} Fit (R²={r_value**2:.3f})')
    
    # Plot second series if provided
    if x2 is not None and y2 is not None:
        if not isinstance(x2, np.ndarray):
            x2 = np.array(x2)
        if not isinstance(y2, np.ndarray):
            y2 = np.array(y2)
        
        if len(x2) != len(y2):
            min_len = min(len(x2), len(y2))
            x2 = x2[:min_len]
            y2 = y2[:min_len]
        
        valid2 = np.isfinite(x2) & np.isfinite(y2)
        x2 = x2[valid2]
        y2 = y2[valid2]
        
        if len(x2) > 0:
            plt.scatter(x2, y2, alpha=alpha, s=20, label=label2, color=color2)
            
            # Add fit line for second series if requested
            if fit_line and len(x2) > 1:
                slope2, intercept2, r_value2, p_value2, std_err2 = stats.linregress(x2, y2)
                line_x2 = np.linspace(x2.min(), x2.max(), 100)
                line_y2 = slope2 * line_x2 + intercept2
                plt.plot(line_x2, line_y2, color=color2, linestyle='--', linewidth=2,
                        label=f'{label2} Fit (R²={r_value2**2:.3f})' if label2 else f'Fit 2 (R²={r_value2**2:.3f})')
    
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    if label1 is not None or label2 is not None or fit_line:
        plt.legend()
    
    plt.tight_layout()
    plt.savefig(outfile, dpi=200, bbox_inches='tight')
    plt.close()


def save_kde_plot(data_dict, title, outfile, xlabel="Value", ylabel="Density", colors=None, bins=50):
    """
    Save a smoothed percentage distribution plot for multiple data series.
    Uses histogram to calculate actual percentages, then smooths with interpolation.
    Best for large datasets (e.g., 1000+ trials).
    
    Args:
        data_dict: Dictionary of {label: data_array}
        title: Plot title
        outfile: Output file path
        xlabel: X-axis label
        ylabel: Y-axis label (default: "Density", will be changed to "Percentage (%)")
        colors: Optional list of colors
        bins: Number of bins for histogram (default: 50)
    """
    from scipy.interpolate import interp1d
    
    plt.figure(figsize=(8, 6))
    
    default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    if colors is None:
        colors = default_colors
    
    # Determine common x range and bin edges
    all_data = []
    for series_data in data_dict.values():
        if not isinstance(series_data, np.ndarray):
            series_data = np.array(series_data)
        series_data = series_data[np.isfinite(series_data)]
        if len(series_data) > 0:
            all_data.extend(series_data)
    
    if len(all_data) == 0:
        print(f"Warning: No valid data for KDE plot: {title}")
        plt.close()
        return
    
    all_data = np.array(all_data)
    x_min, x_max = np.min(all_data), np.max(all_data)
    x_range = x_max - x_min
    # Use common bin edges for fair comparison
    _, bin_edges = np.histogram(all_data, bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_width = bin_edges[1] - bin_edges[0]
    
    # Create smooth x range for plotting
    x_plot = np.linspace(x_min - 0.05*x_range, x_max + 0.05*x_range, 1000)
    
    # Plot smoothed percentage distribution for each series
    has_data = False
    for i, (label, series_data) in enumerate(data_dict.items()):
        if not isinstance(series_data, np.ndarray):
            series_data = np.array(series_data)
        series_data = series_data[np.isfinite(series_data)]
        
        if len(series_data) > 0:
            # Calculate histogram counts (not density)
            counts, _ = np.histogram(series_data, bins=bin_edges)
            # Convert to percentage: (count / total) * 100
            total = len(series_data)
            percentages = (counts / total) * 100
            
            # Smooth using interpolation
            if len(bin_centers) > 1 and np.sum(percentages) > 0:
                # Use cubic interpolation for smooth curve
                try:
                    # Only interpolate where we have data
                    valid_mask = percentages > 0
                    if np.sum(valid_mask) > 1:
                        f = interp1d(bin_centers[valid_mask], percentages[valid_mask], 
                                   kind='cubic', bounds_error=False, fill_value=0)
                        y_plot = f(x_plot)
                        # Ensure non-negative
                        y_plot = np.maximum(y_plot, 0)
                    else:
                        # Fallback to linear if not enough points
                        f = interp1d(bin_centers, percentages, 
                                   kind='linear', bounds_error=False, fill_value=0)
                        y_plot = f(x_plot)
                        y_plot = np.maximum(y_plot, 0)
                    
                    plt.plot(x_plot, y_plot, linewidth=2, label=label, 
                            color=colors[i % len(colors)])
                    plt.fill_between(x_plot, y_plot, alpha=0.3, 
                                   color=colors[i % len(colors)])
                    has_data = True
                except:
                    # Fallback to step plot if interpolation fails
                    plt.step(bin_edges[:-1], percentages, where='post', linewidth=2,
                            label=label, color=colors[i % len(colors)], alpha=0.8)
                    plt.fill_between(bin_edges[:-1], percentages, step='post', alpha=0.3,
                                   color=colors[i % len(colors)])
                    has_data = True
    
    if not has_data:
        print(f"Warning: No valid data for KDE plot: {title}")
        plt.close()
        return
    
    plt.xlabel(xlabel, fontsize=12)
    # Always show as percentage
    plt.ylabel("Percentage (%)", fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(outfile, dpi=200, bbox_inches='tight')
    plt.close()


def save_multi_bar_plot(labels, data_dict, title, outfile, ylabel="Value"):
    """
    Save a grouped bar chart.
    
    Args:
        labels: X-axis labels
        data_dict: Dictionary of {series_name: [values]}
        title: Plot title
        outfile: Output file path
        ylabel: Y-axis label
    """
    plt.figure(figsize=(10, 6))
    x = np.arange(len(labels))
    width = 0.35
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    for i, (series_name, values) in enumerate(data_dict.items()):
        offset = (i - len(data_dict)/2 + 0.5) * width / len(data_dict)
        plt.bar(x + offset, values, width/len(data_dict), label=series_name, 
                color=colors[i % len(colors)], alpha=0.7, edgecolor='black', linewidth=1)
    
    plt.xlabel('Category', fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xticks(x, labels)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(outfile, dpi=200, bbox_inches='tight')
    plt.close()


def save_stacked_fan_distribution(def_fans, agg_fans, title, outfile, xlabel="Fan Value", ylabel="Frequency"):
    """
    Save a stacked bar chart for fan distribution with DEF and AGG counts, plus a total bar.
    
    Args:
        def_fans: List/array of fan values for defensive strategy (filter out 0)
        agg_fans: List/array of fan values for aggressive strategy (filter out 0)
        title: Plot title
        outfile: Output file path
        xlabel: X-axis label
        ylabel: Y-axis label
    """
    # Filter out zeros and convert to arrays
    def_fans = np.array([f for f in def_fans if f > 0])
    agg_fans = np.array([f for f in agg_fans if f > 0])
    
    if len(def_fans) == 0 and len(agg_fans) == 0:
        print(f"Warning: No valid fan data for stacked distribution: {title}")
        return
    
    # Get all unique fan values
    all_fans = np.concatenate([def_fans, agg_fans]) if len(def_fans) > 0 and len(agg_fans) > 0 else (def_fans if len(def_fans) > 0 else agg_fans)
    unique_fans = np.unique(all_fans)
    unique_fans = np.sort(unique_fans)
    
    # Count occurrences for each fan value
    def_counts = [np.sum(def_fans == f) for f in unique_fans]
    agg_counts = [np.sum(agg_fans == f) for f in unique_fans]
    total_counts = [d + a for d, a in zip(def_counts, agg_counts)]
    
    # Calculate overall total
    overall_total = len(def_fans) + len(agg_fans)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # X positions for bars
    x_pos = np.arange(len(unique_fans) + 1)  # +1 for total bar
    
    # Colors: green for DEF, red for AGG, gray for total
    def_color = 'green'
    agg_color = 'red'
    total_color = 'gray'
    
    # Plot stacked bars for each fan value
    bottom = np.zeros(len(unique_fans))
    
    # DEF bars (bottom)
    def_bars = ax.bar(x_pos[:-1], def_counts, bottom=bottom, label='Defensive', 
                      color=def_color, alpha=0.7, edgecolor='black', linewidth=1)
    
    # AGG bars (on top of DEF)
    agg_bars = ax.bar(x_pos[:-1], agg_counts, bottom=def_counts, label='Aggressive', 
                      color=agg_color, alpha=0.7, edgecolor='black', linewidth=1)
    
    # Total bar (at the end)
    total_bar = ax.bar(x_pos[-1], overall_total, label='Total', 
                       color=total_color, alpha=0.7, edgecolor='black', linewidth=1)
    
    # Add value labels on bars
    for i, (d, a, t) in enumerate(zip(def_counts, agg_counts, total_counts)):
        if d > 0:
            ax.text(x_pos[i], d/2, str(d), ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        if a > 0:
            ax.text(x_pos[i], d + a/2, str(a), ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        if t > 0:
            ax.text(x_pos[i], d + a, str(t), ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Label for total bar
    ax.text(x_pos[-1], overall_total/2, str(overall_total), ha='center', va='center', 
            fontsize=10, fontweight='bold', color='white')
    
    # Set x-axis labels
    x_labels = [str(int(f)) for f in unique_fans] + ['Total']
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels)
    
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(outfile, dpi=200, bbox_inches='tight')
    plt.close()

