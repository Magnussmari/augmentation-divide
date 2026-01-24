#!/usr/bin/env python3
"""
08_augmentation_divide_visual.py

Visualization of the Augmentation Divide: Regional skill growth imbalance
showing the gap between GenAI adoption and Critical Thinking evaluation capacity.

Data Source: Coursera Global Skills Report 2025 (PDF archived in data/raw/)
URL: https://www.coursera.org/skills-reports/global
Data extracted: January 2026

Regional enrollment trends (Year-over-Year growth, March 2024 - February 2025):
- Page 21: Asia Pacific – GenAI +132%, Critical Thinking +12%
- Page 33: Europe – GenAI +116%, Critical Thinking +14%
- Page 41: Latin America and the Caribbean – GenAI +425%, Critical Thinking +194%
- Page 49: Middle East & North Africa – GenAI +128%, Critical Thinking +19%
- Page 57: North America – GenAI +135%, Critical Thinking +15%
- Page 63: Sub-Saharan Africa – GenAI +134%, Critical Thinking +6%
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
FIGURES_DIR = SCRIPT_DIR.parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)


def create_augmentation_divide_chart():
    """
    Create bar chart showing CT vs GenAI skill growth by region.
    Highlights Sub-Saharan Africa 'danger zone' with 22:1 ratio and
    Latin America as the positive example with 2.2:1 ratio.
    """
    # Data from Coursera Global Skills Report 2025 - sorted by CT:GenAI ratio (best to worst)
    regions = ['Latin\nAmerica', 'Middle East\n& N. Africa', 'Europe', 'North\nAmerica', 'Asia\nPacific', 'Sub-Saharan\nAfrica']
    ct_growth = [194, 19, 14, 15, 12, 6]           # Critical Thinking Growth %
    genai_growth = [425, 128, 116, 135, 132, 134]  # GenAI Skills Growth %
    ratios = [0.46, 0.15, 0.12, 0.11, 0.09, 0.04]  # CT:GenAI Ratio

    # Setup for the grouped bar chart
    x = np.arange(len(regions))
    width = 0.35

    fig, ax = plt.subplots(figsize=(14, 7))

    # Create bars with color gradient based on ratio (green = good, red = bad)
    colors_ct = ['#1a9641', '#66bd63', '#a6d96a', '#d9ef8b', '#fee08b', '#d73027']
    colors_genai = ['#d7191c'] * len(regions)

    rects1 = ax.bar(x - width/2, ct_growth, width,
                    label='Critical Thinking Growth (%)',
                    color=colors_ct, edgecolor='white', linewidth=0.7)
    rects2 = ax.bar(x + width/2, genai_growth, width,
                    label='GenAI Skills Growth (%)',
                    color='#d7191c', edgecolor='white', linewidth=0.7, alpha=0.8)

    # Formatting
    ax.set_ylabel('Growth Percentage (%)', fontsize=12)
    ax.set_xlabel('')
    ax.set_title('The Augmentation Divide: Skill Growth Imbalance by Region\n(Coursera Global Skills Report 2025)',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(regions, fontsize=10)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)

    # Set y-axis limit to accommodate annotations
    ax.set_ylim(0, 520)

    # Annotate the "Danger Zone" for Sub-Saharan Africa (22:1 gap)
    ax.annotate(f'CT:GenAI = {ratios[5]}\n(22× Gap)',
                xy=(x[5] + width/2, genai_growth[5]),
                xytext=(x[5] - 0.3, 300),
                ha='center', va='center',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.4", fc="#ffcdd2", ec="#d73027", alpha=0.9),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.2", color='#d73027', lw=1.5))

    # Annotate Latin America as the success case
    ax.annotate(f'CT:GenAI = {ratios[0]}\n(2.2× Ratio)\nBalanced Growth',
                xy=(x[0] - width/2, ct_growth[0]),
                xytext=(x[0] + 0.8, 350),
                ha='center', va='center',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.4", fc="#c8e6c9", ec="#1a9641", alpha=0.9),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.2", color='#1a9641', lw=1.5))

    # Add ratio labels above other bars for context
    for i in [1, 2, 3, 4]:
        ax.text(x[i], max(ct_growth[i], genai_growth[i]) + 20,
                f'Ratio: {ratios[i]}',
                ha='center', fontsize=9, fontweight='bold', color='#555555')

    # Add value labels on bars
    for rect in rects1:
        height = rect.get_height()
        ax.annotate(f'{int(height)}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, fontweight='bold', color='#1a5a1a')

    for rect in rects2:
        height = rect.get_height()
        ax.annotate(f'{int(height)}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, fontweight='bold', color='#8b0000')

    plt.tight_layout()

    # Save figure
    output_path = FIGURES_DIR / "augmentation_divide_regional.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"   Saved: {output_path}")

    plt.close()
    return output_path


def create_hdi_stratification_chart():
    """
    Create bar chart showing research output by HDI tier.
    Visualizes the 11.8× concentration gap.
    """
    # Data from Layer 4 analysis
    hdi_tiers = ['Very High\nHDI', 'High\nHDI', 'Medium\nHDI', 'Low\nHDI']
    attributions = [1409, 831, 214, 119]
    countries = [69, 49, 42, 33]
    ratios_to_vh = [1.00, 0.59, 0.15, 0.08]

    # Calculate per-country averages
    per_country = [a/c for a, c in zip(attributions, countries)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left panel: Total attributions
    colors = ['#1a9641', '#a6d96a', '#fdae61', '#d7191c']
    bars1 = ax1.bar(hdi_tiers, attributions, color=colors, edgecolor='white', linewidth=1)
    ax1.set_ylabel('Total Publication Attributions', fontsize=12)
    ax1.set_title('CT+AI Research Output by HDI Tier\n(OpenAlex 2016-2025)', fontsize=13, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    ax1.set_axisbelow(True)

    # Add value and ratio labels
    for bar, attr, ratio in zip(bars1, attributions, ratios_to_vh):
        height = bar.get_height()
        ax1.annotate(f'{attr:,}\n({ratio:.2f}×)',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Annotate the 11.8× gap
    ax1.annotate('11.8× Gap',
                xy=(3, attributions[3]),
                xytext=(2.5, 600),
                ha='center', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", fc="#ffeb3b", ec="orange"),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-.3", color='orange', lw=1.5))

    # Right panel: Per-country average
    bars2 = ax2.bar(hdi_tiers, per_country, color=colors, edgecolor='white', linewidth=1)
    ax2.set_ylabel('Attributions per Country', fontsize=12)
    ax2.set_title('Per-Country Research Output by HDI Tier', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    ax2.set_axisbelow(True)

    # Add value labels
    for bar, val, n in zip(bars2, per_country, countries):
        height = bar.get_height()
        ax2.annotate(f'{val:.1f}\n(n={n})',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    # Save figure
    output_path = FIGURES_DIR / "hdi_stratification_chart.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"   Saved: {output_path}")

    plt.close()
    return output_path


def create_adoption_evaluation_gap():
    """
    Create visualization specifically highlighting the adoption vs evaluation gap.
    """
    fig, ax = plt.subplots(figsize=(12, 7))

    # Data: Adoption (GenAI growth) vs Evaluation (CT growth) - sorted by ratio
    regions = ['Latin\nAmerica', 'ME &\nN. Africa', 'Europe', 'North\nAmerica', 'Asia\nPacific', 'Sub-Saharan\nAfrica']
    adoption = [425, 128, 116, 135, 132, 134]
    evaluation = [194, 19, 14, 15, 12, 6]
    gap = [a - e for a, e in zip(adoption, evaluation)]

    x = np.arange(len(regions))

    # Stacked bar: evaluation (bottom) + gap (top)
    bars_eval = ax.bar(x, evaluation, label='Evaluation Capacity (CT Growth)',
                       color='#2c7bb6', edgecolor='white')
    bars_gap = ax.bar(x, gap, bottom=evaluation, label='Adoption-Evaluation Gap',
                      color='#d7191c', alpha=0.7, edgecolor='white')

    ax.set_ylabel('Growth Percentage (%)', fontsize=12)
    ax.set_title('The Adoption-Evaluation Gap by Region\nGenAI Adoption vs Critical Evaluation Capacity (Coursera 2025)',
                 fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(regions, fontsize=10)
    ax.legend(loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)

    # Highlight Sub-Saharan Africa (worst ratio)
    ax.patches[5].set_edgecolor('#d73027')
    ax.patches[5].set_linewidth(3)
    ax.patches[11].set_edgecolor('#d73027')  # The gap bar for SSA
    ax.patches[11].set_linewidth(3)

    # Highlight Latin America (best ratio)
    ax.patches[0].set_edgecolor('#1a9641')
    ax.patches[0].set_linewidth(3)
    ax.patches[6].set_edgecolor('#1a9641')
    ax.patches[6].set_linewidth(3)

    # Add annotation for Sub-Saharan Africa
    ax.annotate('128% Gap\n(22× imbalance)',
                xy=(5, adoption[5]),
                xytext=(4.3, 250),
                ha='center', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", fc="#ffcdd2", ec="#d73027"),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-.2", color='#d73027', lw=1.5))

    # Add annotation for Latin America
    ax.annotate('231% Gap\n(2.2× ratio)\nBalanced!',
                xy=(0, adoption[0]),
                xytext=(0.8, 500),
                ha='center', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", fc="#c8e6c9", ec="#1a9641"),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2", color='#1a9641', lw=1.5))

    plt.tight_layout()

    # Save figure
    output_path = FIGURES_DIR / "adoption_evaluation_gap.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"   Saved: {output_path}")

    plt.close()
    return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("AUGMENTATION DIVIDE VISUALIZATIONS")
    print("=" * 60)
    print()

    print("1. Creating regional skill imbalance chart...")
    create_augmentation_divide_chart()

    print("\n2. Creating HDI stratification chart...")
    create_hdi_stratification_chart()

    print("\n3. Creating adoption-evaluation gap chart...")
    create_adoption_evaluation_gap()

    print()
    print("=" * 60)
    print("All visualizations complete.")
    print("=" * 60)
