#!/usr/bin/env python3
"""
Robustness checks for Cognitive Resurgence analysis.
Addresses reviewer concerns about causal attribution.

Tests:
1. Placebo breakpoint analysis - tests alternative intervention dates
2. Pre-trend analysis - checks for existing trends before ChatGPT

Upgrade (Jan 2026):
- Adds interrupted time-series (segmented regression) slope-change tests with HAC/Newey-West SEs.
- Keeps the original median-shift (Mann–Whitney) placebo check as a descriptive complement.
"""

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'raw')
PROCESSED_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'processed')

CHATGPT_BREAK = pd.Timestamp("2022-11-01")

def load_trends_data():
    """Load all trends CSVs."""
    dfs = {}
    col_map = {
        'english': 'critical thinking',
        'german': 'kritisches Denken',
        'french': 'pensée critique',
        'spanish': 'pensamiento crítico'
    }

    for lang in ['english', 'german', 'french', 'spanish']:
        path = os.path.join(RAW_DIR, f'trends_{lang}.csv')
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=['date'])
            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])
            dfs[lang] = (df, col_map[lang])
    return dfs

def _fit_segmented(df, col, break_dt, maxlags=6):
    """
    Interrupted time-series via segmented regression:
      y = b0 + b1*time + b2*post + b3*time_post + e

    Returns slope-change estimate (b3) with HAC/Newey-West p-value.
    """
    d = df[['date', col]].dropna().sort_values('date').copy()
    d['time'] = np.arange(len(d), dtype=int)
    d['post'] = (d['date'] >= break_dt).astype(int)
    d['time_post'] = d['time'] * d['post']

    n_pre = int((d['post'] == 0).sum())
    n_post = int((d['post'] == 1).sum())
    if n_pre < 12 or n_post < 12:
        return None

    X = sm.add_constant(d[['time', 'post', 'time_post']])
    lags = int(min(maxlags, max(0, len(d) - 1)))
    model = OLS(d[col].astype(float), X).fit(cov_type='HAC', cov_kwds={'maxlags': lags})

    slope_pre = float(model.params.get('time', np.nan))
    slope_change = float(model.params.get('time_post', np.nan))
    slope_post = slope_pre + slope_change

    return {
        'n_pre': n_pre,
        'n_post': n_post,
        'slope_pre': slope_pre,
        'slope_change': slope_change,
        'slope_post': slope_post,
        'p_slope_change_hac': float(model.pvalues.get('time_post', np.nan)),
        'level_change': float(model.params.get('post', np.nan)),
        'p_level_change_hac': float(model.pvalues.get('post', np.nan)),
        'r_squared': float(model.rsquared),
    }


def placebo_test(df, col, real_break=CHATGPT_BREAK, placebo_breaks=None):
    """
    Test alternative breakpoints to assess specificity of ChatGPT effect.
    If ChatGPT is causal, the Nov 2022 break should show stronger effect
    than placebo dates.
    """
    if placebo_breaks is None:
        placebo_breaks = [
            '2020-03-01',  # COVID onset
            '2021-01-01',  # Arbitrary
            '2021-06-01',  # Arbitrary
            '2022-01-01',  # Pre-ChatGPT
            '2022-10-01',  # Just before ChatGPT (sensitivity)
            '2022-12-01',  # Just after ChatGPT (sensitivity)
            '2023-01-01',  # Early post-ChatGPT (sensitivity)
            '2023-06-01',  # Post-ChatGPT
        ]

    results = []

    for break_date in [real_break.strftime("%Y-%m-%d")] + placebo_breaks:
        break_dt = pd.to_datetime(break_date)
        pre = df[df['date'] < break_dt][col].dropna()
        post = df[df['date'] >= break_dt][col].dropna()

        if len(pre) > 5 and len(post) > 5:
            stat, p = stats.mannwhitneyu(pre, post, alternative='less')
            effect = (post.median() - pre.median()) / pre.median() * 100 if pre.median() > 0 else 0

            seg = _fit_segmented(df, col, break_dt)

            results.append({
                'break_date': break_date,
                'is_chatgpt': break_dt == real_break,
                'pre_median': pre.median(),
                'post_median': post.median(),
                'effect_pct': effect,
                'p_value': p,
                'significant': p < 0.001,
                # ITS slope-change diagnostics (may be NA if not enough data)
                'its_slope_pre': seg['slope_pre'] if seg else np.nan,
                'its_slope_change': seg['slope_change'] if seg else np.nan,
                'its_slope_post': seg['slope_post'] if seg else np.nan,
                'its_slope_change_p_hac': seg['p_slope_change_hac'] if seg else np.nan,
                'its_n_pre': seg['n_pre'] if seg else np.nan,
                'its_n_post': seg['n_post'] if seg else np.nan,
                'its_r_squared': seg['r_squared'] if seg else np.nan,
            })

    return pd.DataFrame(results)

def pre_trend_test(df, col, break_dt=CHATGPT_BREAK):
    """
    Test for pre-existing trend before ChatGPT.
    If trend already existed, ChatGPT attribution is weakened.
    """
    pre_data = df[df['date'] < break_dt].copy()
    pre_data['time'] = range(len(pre_data))

    if len(pre_data) < 12:
        return {
            'pre_slope': np.nan,
            'pre_r_squared': np.nan,
            'pre_p_value_hac': np.nan,
            'pre_trend_significant': False,
        }

    X = sm.add_constant(pre_data[['time']])
    lags = int(min(6, max(0, len(pre_data) - 1)))
    model = OLS(pre_data[col].astype(float), X).fit(cov_type='HAC', cov_kwds={'maxlags': lags})
    slope = float(model.params.get('time', np.nan))
    p = float(model.pvalues.get('time', np.nan))

    return {
        'pre_slope': slope,
        'pre_r_squared': float(model.rsquared),
        'pre_p_value_hac': p,
        'pre_trend_significant': bool(np.isfinite(p) and p < 0.05)
    }

def run_robustness():
    """Run all robustness checks."""
    print("=" * 70)
    print("ROBUSTNESS CHECKS FOR COGNITIVE RESURGENCE HYPOTHESIS")
    print("Addressing reviewer concerns about causal attribution")
    print("=" * 70)

    dfs = load_trends_data()

    if not dfs:
        print("ERROR: No trends data found in", RAW_DIR)
        return None

    all_results = []
    all_placebo_results = []

    for lang, (df, col) in dfs.items():
        print(f"\n{'='*70}")
        print(f"{lang.upper()}: '{col}'")
        print("=" * 70)

        # Placebo tests
        placebo_results = placebo_test(df, col)
        placebo_results['language'] = lang
        all_placebo_results.append(placebo_results)

        print("\nPlacebo Breakpoint Analysis (Median Shift + ITS Slope Change):")
        print("-" * 50)
        for _, row in placebo_results.iterrows():
            marker = ">>> CHATGPT" if row['is_chatgpt'] else "    placebo"
            sig = "***" if row['significant'] else ""
            its = ""
            if np.isfinite(row.get("its_slope_change", np.nan)):
                its_p = row.get("its_slope_change_p_hac", np.nan)
                its_p_str = f"{its_p:.2e}" if np.isfinite(its_p) and its_p < 0.001 else (f"{its_p:.3f}" if np.isfinite(its_p) else "NA")
                its = f" | ITS slopeΔ={row['its_slope_change']:+.3f}/mo (p={its_p_str})"
            print(f"{marker} {row['break_date']}: medianΔ={row['effect_pct']:+6.1f}%, MW p={row['p_value']:.2e} {sig}{its}")

        # Check if ChatGPT break is strongest (median shift)
        chat_row = placebo_results[placebo_results['is_chatgpt']].iloc[0]
        chatgpt_effect = float(chat_row['effect_pct'])
        max_placebo = float(placebo_results[~placebo_results['is_chatgpt']]['effect_pct'].max())
        chatgpt_strongest = bool(chatgpt_effect > max_placebo)

        # Check if ChatGPT break is strongest (ITS slope change)
        chat_slope_change = float(chat_row.get("its_slope_change", np.nan))
        placebo_slope_max = float(placebo_results[~placebo_results['is_chatgpt']]["its_slope_change"].max())
        chatgpt_slope_strongest = bool(np.isfinite(chat_slope_change) and np.isfinite(placebo_slope_max) and chat_slope_change > placebo_slope_max)

        print(f"\nChatGPT effect: {chatgpt_effect:+.1f}%")
        print(f"Max placebo effect: {max_placebo:+.1f}%")
        print(f"ChatGPT > all placebos: {chatgpt_strongest}")
        if np.isfinite(chat_slope_change):
            print(f"\nChatGPT ITS slope change: {chat_slope_change:+.3f}/month")
            print(f"Max placebo ITS slope change: {placebo_slope_max:+.3f}/month")
            print(f"ChatGPT ITS slopeΔ > all placebos: {chatgpt_slope_strongest}")

        # Pre-trend test
        pre_trend = pre_trend_test(df, col)
        print(f"\nPre-trend Analysis (before Nov 2022):")
        print("-" * 50)
        print(f"  Slope: {pre_trend['pre_slope']:.4f} units/month")
        print(f"  R²: {pre_trend['pre_r_squared']:.4f}")
        print(f"  p-value (HAC): {pre_trend['pre_p_value_hac']:.4e}")
        print(f"  Significant pre-trend: {pre_trend['pre_trend_significant']}")

        all_results.append({
            'language': lang,
            # Median-shift placebo check
            'chatgpt_median_effect_pct': chatgpt_effect,
            'max_placebo_effect_pct': max_placebo,
            'chatgpt_median_strongest': chatgpt_strongest,
            # ITS slope-change placebo check
            'chatgpt_its_slope_change': chat_slope_change,
            'max_placebo_its_slope_change': placebo_slope_max,
            'chatgpt_its_slope_strongest': chatgpt_slope_strongest,
            'chatgpt_its_slope_change_p_hac': float(chat_row.get("its_slope_change_p_hac", np.nan)),
            # Pre-trend
            'pre_trend_slope': pre_trend['pre_slope'],
            'pre_trend_r_squared': pre_trend['pre_r_squared'],
            'pre_trend_p_value_hac': pre_trend['pre_p_value_hac'],
            'pre_trend_significant': pre_trend['pre_trend_significant']
        })

    # Save results
    results_df = pd.DataFrame(all_results)
    output_path = os.path.join(PROCESSED_DIR, 'robustness_checks.csv')
    results_df.to_csv(output_path, index=False)

    # Save detailed placebo results
    all_placebo_df = pd.concat(all_placebo_results, ignore_index=True)
    placebo_path = os.path.join(PROCESSED_DIR, 'placebo_breakpoint_analysis.csv')
    all_placebo_df.to_csv(placebo_path, index=False)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    n_strongest = int(results_df['chatgpt_median_strongest'].sum())
    n_strongest_slope = int(results_df['chatgpt_its_slope_strongest'].sum())
    n_pretrend = results_df['pre_trend_significant'].sum()

    print(f"\nChatGPT break strongest effect in: {n_strongest}/4 languages")
    print(f"ChatGPT break strongest ITS slope change in: {n_strongest_slope}/4 languages")
    print(f"Significant pre-existing trend in: {n_pretrend}/4 languages")

    print("\nInterpretation:")
    if n_strongest >= 3:
        print("  - ChatGPT breakpoint shows STRONGER effect than placebos in most languages")
        print("  - This supports (but does not prove) causal attribution")
    else:
        print("  - ChatGPT breakpoint effect is NOT consistently stronger than placebos")
        print("  - Temporal alignment should be framed as acceleration-consistent, not uniquely identified")

    if n_strongest_slope >= 3:
        print("  - ITS slope-change test supports a uniquely stronger post-2022 acceleration")
    else:
        print("  - ITS slope-change is not uniquely strongest at Nov 2022 in most languages")

    if n_pretrend >= 3:
        print("  - Significant pre-trends exist, suggesting ChatGPT ACCELERATED existing trends")
    else:
        print("  - No significant pre-trends, suggesting ChatGPT INITIATED the trend change")

    print(f"\nResults saved to:")
    print(f"  - {output_path}")
    print(f"  - {placebo_path}")

    return results_df

if __name__ == '__main__':
    run_robustness()
