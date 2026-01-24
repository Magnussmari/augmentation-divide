#!/usr/bin/env python3
"""
Calculate effect sizes, confidence intervals, and multiple testing corrections.
"""

import pandas as pd
import numpy as np
from scipy import stats
import os

RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')

def cohens_d(group1, group2):
    """Calculate Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    var1, var2 = group1.var(), group2.var()
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    return (group2.mean() - group1.mean()) / pooled_std

def bootstrap_ci(data, statistic=np.median, n_boot=10000, ci=95, rng=None):
    """Bootstrap confidence interval."""
    if rng is None:
        rng = np.random.default_rng(42)  # deterministic for exact reproducibility
    boot_stats = [statistic(rng.choice(data, size=len(data), replace=True))
                  for _ in range(n_boot)]
    lower = np.percentile(boot_stats, (100-ci)/2)
    upper = np.percentile(boot_stats, 100 - (100-ci)/2)
    return lower, upper

def bonferroni_correction(p_values, alpha=0.05):
    """Apply Bonferroni correction."""
    n = len(p_values)
    corrected_alpha = alpha / n
    return [p < corrected_alpha for p in p_values], corrected_alpha

def analyze_trends_with_effects():
    """Add effect sizes and CIs to trends analysis."""
    results = []
    rng = np.random.default_rng(42)  # deterministic bootstrap stream

    for lang in ['english', 'german', 'french', 'spanish']:
        path = os.path.join(RAW_DIR, f'trends_{lang}.csv')
        df = pd.read_csv(path, parse_dates=['date'])
        col = [c for c in df.columns if c not in ['date', 'isPartial']][0]

        pre = df[df['date'] < '2022-11-01'][col].dropna()
        post = df[df['date'] >= '2022-11-01'][col].dropna()

        # Effect size
        d = cohens_d(pre, post)

        # Bootstrap CIs for medians
        pre_ci = bootstrap_ci(pre.values, rng=rng)
        post_ci = bootstrap_ci(post.values, rng=rng)

        # Mann-Whitney with effect size (rank-biserial correlation)
        stat, p = stats.mannwhitneyu(pre, post, alternative='less')
        n1, n2 = len(pre), len(post)
        r = 1 - (2*stat)/(n1*n2)  # rank-biserial correlation

        results.append({
            'language': lang,
            'pre_median': pre.median(),
            'pre_ci_lower': pre_ci[0],
            'pre_ci_upper': pre_ci[1],
            'post_median': post.median(),
            'post_ci_lower': post_ci[0],
            'post_ci_upper': post_ci[1],
            'cohens_d': d,
            'rank_biserial_r': r,
            'p_value': p
        })

    df_results = pd.DataFrame(results)

    # Bonferroni correction
    corrected, alpha = bonferroni_correction(df_results['p_value'].tolist())
    df_results['bonferroni_significant'] = corrected
    df_results['bonferroni_alpha'] = alpha

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    df_results.to_csv(os.path.join(PROCESSED_DIR, 'effect_sizes_trends.csv'), index=False)
    print("Effect sizes saved to effect_sizes_trends.csv")
    print(df_results.to_string())

    return df_results

if __name__ == '__main__':
    analyze_trends_with_effects()
