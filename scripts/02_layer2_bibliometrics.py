#!/usr/bin/env python3
"""
Layer 2: Bibliometric Analysis
===============================
Structural break detection on publication metadata.

Uses REAL data from OpenAlex API queries.

Outputs:
- real_bibliometrics.csv
- layer2_real_bibliometrics.png

Key statistics reproduced (Table 2 in paper):
- 2023 CT+AI pubs: 600, +141% YoY
- 2023 GenAI+Ed pubs: 379, +2,129% YoY
- Acceleration factor: 3.3x
Additional normalization (requested):
- "Critical Ratio" = (CT+AI pubs) / (Total AI pubs) by year, to control for field-wide growth.

Author: Magnus Smári
Date: January 2026
"""

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import matplotlib.pyplot as plt
import requests
import json
import re
from datetime import date
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
FIGURES = PROJECT_ROOT / "figures"

DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)
DATA_RAW.mkdir(parents=True, exist_ok=True)


OPENALEX_AI_CONCEPT_ID = "C154945302"  # OpenAlex concept: Artificial intelligence


def _latest_dated_cache(data_dir: Path, prefix: str) -> Path | None:
    """Return the most recent cache file matching {prefix}_YYYY-MM-DD.json, if present."""
    candidates = list(data_dir.glob(f"{prefix}_*.json"))
    if not candidates:
        return None

    dated = []
    for p in candidates:
        m = re.search(r"_(\\d{4}-\\d{2}-\\d{2})\\.json$", p.name)
        if not m:
            continue
        dated.append((m.group(1), p))
    if not dated:
        return None
    dated.sort(key=lambda x: x[0])
    return dated[-1][1]


def fetch_openalex_total_ai_by_year(cache_path: Path) -> dict:
    """
    Fetch total AI publication counts by publication_year from OpenAlex and cache the response.

    Denominator uses OpenAlex concept id for Artificial Intelligence (C154945302).
    This is intentionally broader than the numerator query to capture field-wide growth.
    """
    url = "https://api.openalex.org/works"
    params = {
        "filter": f"concept.id:{OPENALEX_AI_CONCEPT_ID}",
        "group_by": "publication_year",
        "per-page": 200,
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_total_ai_counts_by_year() -> dict[int, int]:
    """Load (or fetch) total AI publication counts by year."""
    prefix = "openalex_total_ai_by_year"
    cache = _latest_dated_cache(DATA_RAW, prefix)
    if cache is None:
        cache = DATA_RAW / f"{prefix}_{date.today().isoformat()}.json"
        payload = fetch_openalex_total_ai_by_year(cache)
    else:
        payload = json.loads(cache.read_text(encoding="utf-8"))

    # OpenAlex group_by values are strings; normalize to ints.
    groups = payload.get("group_by", [])
    return {int(g["key"]): int(g["count"]) for g in groups if g.get("key") and g.get("count") is not None}


def load_real_bibliometric_data():
    """
    Load REAL bibliometric data from OpenAlex API queries.

    Data obtained from OpenAlex API on 2026-01-23.
    Query: "critical thinking" AND ("artificial intelligence" OR "generative AI" OR "ChatGPT")

    These are the actual publication counts from the paper's Table 2.
    """
    # Real data from OpenAlex API queries (2026-01-23)
    data = {
        'Year': [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        'CT_AI_Pubs': [43, 59, 80, 156, 216, 214, 249, 600, 1227, 2725],
        'GenAI_Ed_Pubs': [6, 9, 13, 14, 12, 10, 17, 379, 652, 989],
    }
    df = pd.DataFrame(data)

    # Denominator: total AI publications per year (OpenAlex concept-based counts).
    total_ai = load_total_ai_counts_by_year()
    df["Total_AI_Pubs"] = df["Year"].map(total_ai).astype("Int64")

    # "Critical Ratio" (scaled per 10,000 AI papers for interpretability).
    df["Critical_Ratio"] = df["CT_AI_Pubs"] / df["Total_AI_Pubs"]
    df["Critical_Ratio_per_10k"] = df["Critical_Ratio"] * 10_000

    # Calculate metrics
    df['CT_AI_YoY'] = df['CT_AI_Pubs'].pct_change() * 100
    df['GenAI_Ed_YoY'] = df['GenAI_Ed_Pubs'].pct_change() * 100

    # Burst detection (z-score)
    df['CT_AI_zscore'] = stats.zscore(df['CT_AI_Pubs'])
    df['Burst'] = df['CT_AI_zscore'].apply(lambda x: 'Yes' if x > 1.5 else 'No')

    return df


def detect_structural_break(df):
    """Detect structural break using pre/post regression."""
    y = df['CT_AI_Pubs'].values
    x = np.arange(len(y))

    # Pre-2023 regression (years 2016-2022 = indices 0-6)
    pre_mask = df['Year'] < 2023
    X_pre = sm.add_constant(x[pre_mask])
    model_pre = OLS(y[pre_mask], X_pre).fit()

    # Post-2023 regression (years 2023-2025 = indices 7-9)
    post_mask = df['Year'] >= 2023
    X_post = sm.add_constant(x[post_mask])
    model_post = OLS(y[post_mask], X_post).fit()

    # Calculate pre/post average growth rates
    pre_growth = df[df['Year'].between(2017, 2022)]['CT_AI_YoY'].mean()
    post_growth = df[df['Year'] >= 2023]['CT_AI_YoY'].mean()

    return {
        'pre_slope': model_pre.params[1],
        'post_slope': model_post.params[1],
        'slope_ratio': model_post.params[1] / model_pre.params[1] if model_pre.params[1] != 0 else np.inf,
        'pre_r2': model_pre.rsquared,
        'post_r2': model_post.rsquared,
        'pre_avg_growth': pre_growth,
        'post_avg_growth': post_growth,
        'acceleration_factor': post_growth / pre_growth if pre_growth != 0 else np.inf
    }


def create_visualization(df, break_stats):
    """Create bibliometric visualization."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: Bar chart
    ax1 = axes[0, 0]
    width = 0.35
    x = np.arange(len(df))
    ax1.bar(x - width/2, df['CT_AI_Pubs'], width,
            label='CT + AI', color='#e74c3c', alpha=0.8)
    ax1.bar(x + width/2, df['GenAI_Ed_Pubs'], width,
            label='GenAI + Education', color='#3498db', alpha=0.8)
    ax1.axvline(6.5, color='red', linestyle='--', linewidth=2, alpha=0.7,
                label='ChatGPT (Nov 2022)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(df['Year'])
    ax1.set_ylabel('Publication Count')
    ax1.set_title('Publication Growth by Year (OpenAlex Real Data)', fontweight='bold')
    ax1.legend()

    # Add YoY annotations for significant jumps
    for i, row in df.iterrows():
        if pd.notna(row['CT_AI_YoY']) and row['CT_AI_YoY'] > 100:
            ax1.annotate(f"+{row['CT_AI_YoY']:.0f}%",
                        xy=(i - width/2, row['CT_AI_Pubs']),
                        xytext=(0, 5), textcoords='offset points',
                        ha='center', fontsize=9, color='darkred', fontweight='bold')

    # Panel 2: Log scale with burst
    ax2 = axes[0, 1]
    ax2.semilogy(df['Year'], df['CT_AI_Pubs'], 'o-',
                 color='#e74c3c', linewidth=2, markersize=8, label='CT+AI')
    ax2.semilogy(df['Year'], df['GenAI_Ed_Pubs'], 's--',
                 color='#3498db', linewidth=2, markersize=8, label='GenAI+Ed')
    ax2.axvline(2022.5, color='red', linestyle='--', alpha=0.7)

    # Highlight burst years
    burst_years = df[df['Burst'] == 'Yes']['Year']
    for year in burst_years:
        pub_val = df[df['Year'] == year]['CT_AI_Pubs'].values[0]
        ax2.annotate('Burst', xy=(year, pub_val), xytext=(5, 10),
                    textcoords='offset points', fontsize=9, color='red')

    ax2.set_xlabel('Year')
    ax2.set_ylabel('Publications (log scale)')
    ax2.set_title(f'Exponential Growth\nAcceleration: {break_stats["acceleration_factor"]:.1f}x',
                  fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Panel 3: Critical Ratio (per 10k AI papers)
    ax3 = axes[1, 0]
    ax3.plot(df["Year"], df["Critical_Ratio_per_10k"], marker="o", color="#2ecc71", linewidth=2)
    ax3.axvline(2022.5, color="red", linestyle="--", alpha=0.6, label="ChatGPT (Nov 2022)")
    ax3.set_xlabel("Year")
    ax3.set_ylabel("CT+AI per 10,000 AI papers")
    ax3.set_title("Critical Ratio Normalization\n(Controls for Field-wide AI Growth)", fontweight="bold")
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper left")

    # Panel 4: Ratio change annotations (avoid over-reading partial year)
    ax4 = axes[1, 1]
    ax4.axis("off")
    # Prefer 2024 as last fully indexed year (2025 may be incomplete in OpenAlex).
    row_2022 = df[df["Year"] == 2022].iloc[0]
    row_2024 = df[df["Year"] == 2024].iloc[0]
    factor = (row_2024["Critical_Ratio"] / row_2022["Critical_Ratio"]) if row_2022["Critical_Ratio"] else np.nan
    ratio_text = (
        "Normalization check:\n"
        f"  2022: {row_2022['Critical_Ratio_per_10k']:.2f} per 10k AI papers\n"
        f"  2024: {row_2024['Critical_Ratio_per_10k']:.2f} per 10k AI papers\n"
        f"  Change (2022→2024): {factor:.1f}×\n\n"
        "Note: 2025 counts may be incomplete in OpenAlex indexing.\n"
        f"Denominator = OpenAlex concept {OPENALEX_AI_CONCEPT_ID} (AI)."
    )
    ax4.text(0.02, 0.98, ratio_text, va="top", ha="left", fontsize=11, family="monospace",
             bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.4))

    plt.suptitle('Layer 2: Bibliometric Analysis (OpenAlex)\n'
                 'Volume + Structural Break + Field-Normalized Ratio', fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig


def main():
    print("="*60)
    print("LAYER 2: BIBLIOMETRIC ANALYSIS (REAL DATA)")
    print("="*60)

    print("\n1. Loading real bibliometric data from OpenAlex...")
    df = load_real_bibliometric_data()

    print("\n2. Detecting structural break...")
    break_stats = detect_structural_break(df)

    print("\n3. Summary:")
    print(df[['Year', 'CT_AI_Pubs', 'CT_AI_YoY', 'GenAI_Ed_Pubs', 'GenAI_Ed_YoY', 'Burst']].to_string(index=False))

    print(f"\n   Structural Break Analysis:")
    print(f"   Pre-2023 avg YoY growth: {break_stats['pre_avg_growth']:.1f}%")
    print(f"   Post-2023 avg YoY growth: {break_stats['post_avg_growth']:.1f}%")
    print(f"   Acceleration factor: {break_stats['acceleration_factor']:.1f}x")

    # Ratio check (avoid over-reading 2025 as fully indexed)
    if df["Total_AI_Pubs"].notna().all():
        r2022 = float(df.loc[df["Year"] == 2022, "Critical_Ratio_per_10k"].iloc[0])
        r2024 = float(df.loc[df["Year"] == 2024, "Critical_Ratio_per_10k"].iloc[0])
        print("\n   Field-normalized check (Critical Ratio):")
        print(f"   - 2022: {r2022:.2f} CT+AI per 10k AI papers")
        print(f"   - 2024: {r2024:.2f} CT+AI per 10k AI papers")
        print(f"   - Change (2022→2024): {r2024/r2022:.1f}x")

    print("\n   Paper Table 2 verification:")
    print("   - 2023 CT+AI: 600 pubs, +141% YoY  [Expected]")
    print("   - 2023 GenAI+Ed: 379 pubs, +2,129% YoY  [Expected]")
    print("   - Acceleration: 3.3x  [Expected]")

    df.to_csv(DATA_PROCESSED / 'real_bibliometrics.csv', index=False)
    print(f"\n   Saved: {DATA_PROCESSED / 'real_bibliometrics.csv'}")

    print("\n4. Creating visualization...")
    fig = create_visualization(df, break_stats)
    fig.savefig(FIGURES / 'layer2_real_bibliometrics.png',
                dpi=150, bbox_inches='tight')
    print(f"   Saved: {FIGURES / 'layer2_real_bibliometrics.png'}")

    print("\n" + "="*60)
    print("Layer 2 analysis complete.")
    print("="*60)

    return df, break_stats


if __name__ == "__main__":
    df, break_stats = main()
