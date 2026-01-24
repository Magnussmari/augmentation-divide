#!/usr/bin/env python3
"""
Layer 1: Google Trends Analysis
================================
Author-derived segmented regression on SVI time series.

Uses REAL data from Google Trends API exports.

Outputs:
- real_trends_analysis.csv
- layer1_real_trends.png

Key statistics reproduced:
- Spanish: +195% (19→56), p = 7.1e-13
- German: +83% (20→36.5), p = 2.8e-12
- French: +36% (38.5→52.5), p = 1.7e-8
- English: +34% (50→67), p = 1.2e-9

Author: Magnus Smári
Date: January 2026
"""

import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Raw data location - check both possible locations
DATA_RAW_PRIMARY = PROJECT_ROOT / "data" / "raw"
DATA_RAW_SECONDARY = PROJECT_ROOT.parent / "data" / "raw"

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
FIGURES = PROJECT_ROOT / "figures"

DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)


def find_data_dir():
    """Find the directory containing raw trends data."""
    if (DATA_RAW_PRIMARY / "trends_english.csv").exists():
        return DATA_RAW_PRIMARY
    elif (DATA_RAW_SECONDARY / "trends_english.csv").exists():
        return DATA_RAW_SECONDARY
    else:
        raise FileNotFoundError(
            f"Could not find trends_english.csv in {DATA_RAW_PRIMARY} or {DATA_RAW_SECONDARY}"
        )


def load_real_trends_data():
    """
    Load REAL Google Trends data from CSV exports.

    The data was obtained via pytrends 4.9.2 from Google Trends API on 2026-01-23.
    Files: trends_english.csv, trends_german.csv, trends_french.csv, trends_spanish.csv
    """
    data_dir = find_data_dir()

    # Load each language file
    files = {
        'English': 'trends_english.csv',
        'German': 'trends_german.csv',
        'French': 'trends_french.csv',
        'Spanish': 'trends_spanish.csv'
    }

    # Column name mapping (the actual column names in the files)
    col_mapping = {
        'English': 'critical thinking',
        'German': 'kritisches Denken',
        'French': 'pensée critique',
        'Spanish': 'pensamiento crítico'
    }

    dfs = []
    for lang, filename in files.items():
        filepath = data_dir / filename
        df = pd.read_csv(filepath, parse_dates=['date'])
        df = df.set_index('date')
        # Rename the SVI column to the language name
        svi_col = col_mapping[lang]
        df = df[[svi_col]].rename(columns={svi_col: lang})
        dfs.append(df)

    # Merge all languages
    combined = pd.concat(dfs, axis=1)

    print(f"   Loaded {len(combined)} monthly observations from {data_dir}")
    print(f"   Date range: {combined.index.min().date()} to {combined.index.max().date()}")

    return combined


def analyze_trends(df):
    """
    Perform Mann-Whitney U test and segmented regression.

    Break point: November 2022 (ChatGPT release)
    """
    results = []
    break_date = '2022-11-01'
    break_ts = pd.Timestamp(break_date)

    for lang in df.columns:
        series = df[lang].dropna()
        pre = series[series.index < break_ts]
        post = series[series.index >= break_ts]

        # Mann-Whitney U test (one-sided: post > pre)
        stat, p_value = mannwhitneyu(pre, post, alternative='less')

        # Effect size
        pre_median = pre.median()
        post_median = post.median()
        effect_pct = ((post_median - pre_median) / pre_median) * 100

        # Volatility / "responsiveness" proxy: average absolute month-to-month change
        diff = series.diff().dropna()
        pre_diff = diff[diff.index < break_ts]
        post_diff = diff[diff.index >= break_ts]
        pre_abs_diff_mean = float(pre_diff.abs().mean()) if len(pre_diff) else np.nan
        post_abs_diff_mean = float(post_diff.abs().mean()) if len(post_diff) else np.nan
        if np.isfinite(pre_abs_diff_mean) and np.isfinite(post_abs_diff_mean) and pre_abs_diff_mean != 0:
            volatility_ratio = post_abs_diff_mean / pre_abs_diff_mean
        else:
            volatility_ratio = np.nan

        # Segmented regression
        series_reset = series.reset_index()
        series_reset.columns = ['date', 'svi']
        series_reset['time'] = range(len(series_reset))
        series_reset['post'] = (series_reset['date'] >= break_ts).astype(int)
        series_reset['time_post'] = series_reset['time'] * series_reset['post']

        X = sm.add_constant(series_reset[['time', 'post', 'time_post']])
        # HAC robust SEs (monthly data): Newey-West with 6 lags (~half-year).
        model = OLS(series_reset['svi'], X).fit(cov_type='HAC', cov_kwds={'maxlags': 6})

        slope_pre = float(model.params['time'])
        slope_change = float(model.params['time_post'])
        slope_post = slope_pre + slope_change

        results.append({
            'Language': lang,
            'Pre_Median': round(pre_median, 1),
            'Post_Median': round(post_median, 1),
            'Effect_Pct': round(effect_pct, 1),
            'Mann_Whitney_U': round(stat, 1),
            'MW_P_Value': p_value,
            'Slope_Pre': round(slope_pre, 4),
            'Slope_Change': round(slope_change, 4),
            'Slope_Post': round(slope_post, 4),
            'R_Squared': round(model.rsquared, 4),
            'Slope_Change_P_HAC': model.pvalues['time_post'],
            'Pre_AbsDiff_Mean': round(pre_abs_diff_mean, 3) if np.isfinite(pre_abs_diff_mean) else np.nan,
            'Post_AbsDiff_Mean': round(post_abs_diff_mean, 3) if np.isfinite(post_abs_diff_mean) else np.nan,
            'Volatility_Ratio': round(volatility_ratio, 3) if np.isfinite(volatility_ratio) else np.nan,
        })

    return pd.DataFrame(results)


def create_visualization(df, results):
    """Create four-panel visualization with real data."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = {'English': '#3498db', 'German': '#e74c3c',
              'French': '#2ecc71', 'Spanish': '#f39c12'}

    for ax, lang in zip(axes.flatten(), ['English', 'German', 'French', 'Spanish']):
        series = df[lang]
        ax.plot(series.index, series.values, color=colors[lang], alpha=0.5, linewidth=1)
        rolling = series.rolling(window=6).mean()
        ax.plot(series.index, rolling.values, color=colors[lang], linewidth=2.5,
                label=f'{lang} (6-mo avg)')

        ax.axvline(pd.Timestamp('2022-11-01'), color='red', linestyle='--',
                   linewidth=2, alpha=0.7, label='ChatGPT Launch')

        row = results[results['Language'] == lang].iloc[0]
        p_formatted = f"{row['MW_P_Value']:.2e}" if row['MW_P_Value'] < 0.001 else f"{row['MW_P_Value']:.3f}"
        sp = row.get('Slope_Change_P_HAC', np.nan)
        sp_formatted = f"{sp:.2e}" if pd.notna(sp) and sp < 0.001 else (f"{sp:.3f}" if pd.notna(sp) else "N/A")
        stats_text = (
            f"Median shift: +{row['Effect_Pct']:.0f}%\n"
            f"MW p = {p_formatted}\n"
            f"Slope Δ (HAC): {row['Slope_Change']:.3f}/mo (p={sp_formatted})"
        )
        ax.text(0.97, 0.05, stats_text, transform=ax.transAxes, fontsize=10,
                va='bottom', ha='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

        ax.set_title(f'{lang}: "critical thinking" SVI', fontweight='bold', fontsize=12)
        ax.set_ylabel('Search Volume Index')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

    plt.suptitle('Layer 1: Google Trends Analysis (Real API Data)\n'
                 'Mann-Whitney U + Segmented Regression | Nov 2022 Breakpoint',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig


def main():
    print("="*60)
    print("LAYER 1: GOOGLE TRENDS ANALYSIS (REAL DATA)")
    print("="*60)

    print("\n1. Loading real Google Trends data...")
    df = load_real_trends_data()

    print("\n2. Running statistical analysis...")
    results = analyze_trends(df)

    # Sort by effect size for display
    results_sorted = results.sort_values('Effect_Pct', ascending=False)
    results_sorted.to_csv(DATA_PROCESSED / 'real_trends_analysis.csv', index=False)
    print(f"   Saved: {DATA_PROCESSED / 'real_trends_analysis.csv'}")

    print("\n3. Results Summary (sorted by effect size):")
    print("-" * 80)
    for _, row in results_sorted.iterrows():
        p_str = f"{row['MW_P_Value']:.2e}"
        print(f"   {row['Language']:10} | Pre: {row['Pre_Median']:5.1f} -> Post: {row['Post_Median']:5.1f} | "
              f"Effect: +{row['Effect_Pct']:5.1f}% | p = {p_str}")
    print("-" * 80)

    print("\n   Paper Table 1 verification:")
    print("   - Spanish: +195% (19→56), p = 7.1e-13  [Expected]")
    print("   - German:  +83%  (20→36.5), p = 2.8e-12  [Expected]")
    print("   - French:  +36%  (38.5→52.5), p = 1.7e-8  [Expected]")
    print("   - English: +34%  (50→67), p = 1.2e-9  [Expected]")

    print("\n4. Creating visualization...")
    fig = create_visualization(df, results)
    fig.savefig(FIGURES / 'layer1_real_trends.png', dpi=150, bbox_inches='tight')
    print(f"   Saved: {FIGURES / 'layer1_real_trends.png'}")

    print("\n" + "="*60)
    print("Layer 1 analysis complete.")
    print("="*60)

    return df, results


if __name__ == "__main__":
    df, results = main()
