#!/usr/bin/env python3
"""
Layer 4: Stratification Analysis
================================
HDI–research association and "Augmentation Divide" concentration metrics.

This script broadens Layer 4 beyond a high-output (10+ pubs) convenience sample by:
- Pulling country-level publication attributions from OpenAlex (group_by=authorships.countries)
- Merging to UNDP HDI (HDR23-24 time series file; uses 2022 HDI values + hdicode tiers)
- Assigning 0 publications to UNDP countries not present in the OpenAlex grouping

Outputs:
- data/processed/real_hdi_stratification.csv
- data/processed/real_mooc_regional.csv
- figures/layer4_real_stratification.png

Notes:
- OpenAlex `authorships.countries` counts are country attributions: a single multi-country paper can
  contribute to multiple countries. Totals therefore need not equal OpenAlex's works-count.

Author: Magnus Smári
Date: January 2026
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import requests
import pycountry


# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
FIGURES = PROJECT_ROOT / "figures"

DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)


# Inputs
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
OPENALEX_FILTER = (
    "title_and_abstract.search:critical thinking AND "
    "(artificial intelligence OR generative AI OR ChatGPT)"
)
OPENALEX_MAILTO = "maggismari@gmail.com"
OPENALEX_CACHE_JSON = DATA_RAW / "openalex_ct_ai_authorships_countries_2026-01-23.json"

UNDP_URL = (
    "https://hdr.undp.org/sites/default/files/2023-24_HDR/"
    "HDR23-24_Composite_indices_complete_time_series.csv"
)
UNDP_CSV = DATA_RAW / "HDR23-24_Composite_indices_complete_time_series.csv"
UNDP_HDI_YEAR = 2022


def iso2_to_iso3(iso2: str) -> str | None:
    """Convert ISO-3166 alpha-2 to alpha-3 (returns None if unknown)."""
    if not iso2:
        return None
    iso2 = iso2.strip().upper()

    # OpenAlex includes some non-ISO entities; keep explicit overrides small and transparent.
    overrides = {
        "XK": None,  # Kosovo not in UNDP HDR time series file
    }
    if iso2 in overrides:
        return overrides[iso2]

    c = pycountry.countries.get(alpha_2=iso2)
    if c is None:
        return None
    return getattr(c, "alpha_3", None)


def fetch_openalex_groupby(filter_str: str, group_by: str, per_page: int = 200) -> Dict:
    """
    Fetch an OpenAlex group_by result, paging if necessary.

    OpenAlex returns group_by results in pages; `meta.groups_count` indicates total groups.
    """
    groups: List[Dict] = []
    page = 1

    while True:
        params = {
            "filter": filter_str,
            "group_by": group_by,
            "per_page": per_page,
            "page": page,
            "mailto": OPENALEX_MAILTO,
        }
        resp = requests.get(OPENALEX_WORKS_URL, params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()

        page_groups = payload.get("group_by", [])
        groups.extend(page_groups)

        meta = payload.get("meta", {})
        groups_count = int(meta.get("groups_count", len(page_groups)) or 0)

        # Stop if we've collected all groups, or this page is empty.
        if not page_groups or len(groups) >= groups_count:
            payload["group_by"] = groups
            return payload

        page += 1


def load_openalex_country_counts() -> Tuple[pd.DataFrame, Dict]:
    """
    Load OpenAlex country attribution counts (cached if present; otherwise fetch and cache).
    """
    if OPENALEX_CACHE_JSON.exists():
        payload = json.loads(OPENALEX_CACHE_JSON.read_text(encoding="utf-8"))
    else:
        payload = fetch_openalex_groupby(OPENALEX_FILTER, "authorships.countries", per_page=200)
        OPENALEX_CACHE_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    rows = []
    for g in payload.get("group_by", []):
        key = g.get("key", "")
        # key is like: https://openalex.org/countries/US
        iso2 = key.rstrip("/").split("/")[-1].upper() if isinstance(key, str) else None
        rows.append(
            {
                "ISO2": iso2,
                "Country_OpenAlex": g.get("key_display_name"),
                "Publications": int(g.get("count", 0) or 0),
            }
        )

    df = pd.DataFrame(rows)
    df["ISO3"] = df["ISO2"].apply(lambda x: iso2_to_iso3(x) if isinstance(x, str) else None)
    return df, payload


def ensure_undp_file():
    """Download the UNDP HDR time series file if it isn't present."""
    if UNDP_CSV.exists():
        return
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    resp = requests.get(UNDP_URL, timeout=120)
    resp.raise_for_status()
    UNDP_CSV.write_bytes(resp.content)


def load_undp_hdi() -> pd.DataFrame:
    """
    Load UNDP HDR time series and return a compact country-level HDI dataset.
    """
    ensure_undp_file()
    df = pd.read_csv(UNDP_CSV, encoding="latin-1", low_memory=False)

    hdi_col = f"hdi_{UNDP_HDI_YEAR}"
    required = ["iso3", "country", "hdicode", hdi_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"UNDP file missing required columns: {missing}")

    # Drop UNDP aggregate rows (e.g., "World", regional aggregates) whose iso3 is not a 3-letter country code.
    df = df[df["iso3"].astype(str).str.len() == 3].copy()

    out = df[required].copy()
    out = out.rename(
        columns={
            "iso3": "ISO3",
            "country": "Country",
            "hdicode": "HDI_Category",
            hdi_col: "HDI",
        }
    )
    # Keep HDI as numeric; leave missing as NaN.
    out["HDI"] = pd.to_numeric(out["HDI"], errors="coerce")
    out["HDI_Category"] = out["HDI_Category"].replace({None: np.nan})
    return out


def load_real_mooc_data() -> pd.DataFrame:
    """
    Load REAL regional MOOC enrollment data from Coursera Global Skills Report 2025.
    
    Source: Coursera Global Skills Report 2025 (PDF archived in data/raw/)
    URL: https://www.coursera.org/skills-reports/global
    Data extracted: January 2026
    
    Regional enrollment trends (Year-over-Year growth, March 2024 - February 2025):
    - Page 41: Latin America and the Caribbean - GenAI +425%, CT +194%
    - Page 57: North America - GenAI +135%, CT +15%
    - Page 21: Asia Pacific - GenAI +132%, CT +12%
    - Page 33: Europe - GenAI +116%, CT +14%
    - Page 49: Middle East & North Africa - GenAI +128%, CT +19%
    - Page 63: Sub-Saharan Africa - GenAI +134%, CT +6%
    
    CT_GenAI_Ratio = CT_Growth / GenAI_Growth
    """
    return pd.DataFrame(
        {
            "Region": [
                "Europe",
                "North America",
                "Asia Pacific",
                "Latin America",
                "Middle East & North Africa",
                "Sub-Saharan Africa",
            ],
            "CT_Growth": [14, 15, 12, 194, 19, 6],
            "GenAI_Growth": [116, 135, 132, 425, 128, 134],
            "CT_GenAI_Ratio": [0.12, 0.11, 0.09, 0.46, 0.15, 0.04],
        }
    )


def merge_country_counts(openalex_df: pd.DataFrame, undp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge OpenAlex country attributions to UNDP HDI countries.

    Countries in UNDP without OpenAlex attributions get Publications=0.
    Countries in OpenAlex without UNDP HDI are not included in the merged output.
    """
    # Aggregate OpenAlex by ISO3 (multi-country entities without ISO3 are dropped here).
    oa = openalex_df.dropna(subset=["ISO3"]).copy()
    oa = oa.groupby("ISO3", as_index=False).agg(
        {
            "Publications": "sum",
            "Country_OpenAlex": lambda s: s.dropna().iloc[0] if len(s.dropna()) else None,
            "ISO2": lambda s: s.dropna().iloc[0] if len(s.dropna()) else None,
        }
    )

    merged = undp_df.merge(oa, on="ISO3", how="left")
    merged["Publications"] = merged["Publications"].fillna(0).astype(int)

    # Derived fields for plotting / indices
    merged["Log_Pubs"] = np.log10(merged["Publications"] + 1)
    max_log = merged["Log_Pubs"].max()
    merged["Research_Index"] = (merged["Log_Pubs"] / max_log * 100).round(1) if max_log > 0 else 0.0

    return merged


def compute_stratification(df: pd.DataFrame) -> pd.DataFrame:
    """Compute stratification metrics by HDI category (drops missing categories)."""
    d = df.dropna(subset=["HDI_Category"]).copy()
    agg = d.groupby("HDI_Category").agg(
        HDI_Mean=("HDI", "mean"),
        Total_Pubs=("Publications", "sum"),
        Country_Count=("ISO3", "count"),
        Avg_Pubs=("Publications", "mean"),
        Median_Pubs=("Publications", "median"),
    )
    agg = agg.round(2)

    # Ratio to Very High total publications (if present)
    if "Very High" in agg.index and agg.loc["Very High", "Total_Pubs"] > 0:
        very_high_pubs = agg.loc["Very High", "Total_Pubs"]
        agg["Ratio_to_VeryHigh"] = (agg["Total_Pubs"] / very_high_pubs).round(2)
    else:
        agg["Ratio_to_VeryHigh"] = np.nan

    order = ["Very High", "High", "Medium", "Low"]
    agg = agg.reindex([c for c in order if c in agg.index])
    return agg


def compute_correlations(df: pd.DataFrame) -> Dict[str, float]:
    """Compute Pearson and Spearman correlations (raw pubs and log10(pubs+1))."""
    d = df.dropna(subset=["HDI"]).copy()

    # Pearson (raw)
    pear_r, pear_p = stats.pearsonr(d["HDI"], d["Publications"])
    # Pearson (log)
    pear_log_r, pear_log_p = stats.pearsonr(d["HDI"], d["Log_Pubs"])
    # Spearman (raw)
    spear_r, spear_p = stats.spearmanr(d["HDI"], d["Publications"])

    return {
        "pearson_r_raw": float(pear_r),
        "pearson_p_raw": float(pear_p),
        "pearson_r_log": float(pear_log_r),
        "pearson_p_log": float(pear_log_p),
        "spearman_r_raw": float(spear_r),
        "spearman_p_raw": float(spear_p),
        "n_countries_hdi": int(len(d)),
    }


def compute_key_statistics(df: pd.DataFrame, agg: pd.DataFrame) -> Dict[str, float]:
    """Compute key concentration and gap metrics."""
    total_pubs = int(df["Publications"].sum())
    top5 = df.nlargest(5, "Publications")
    top10 = df.nlargest(10, "Publications")
    top5_pubs = int(top5["Publications"].sum())
    top10_pubs = int(top10["Publications"].sum())

    top5_share = (top5_pubs / total_pubs * 100) if total_pubs else np.nan
    top10_share = (top10_pubs / total_pubs * 100) if total_pubs else np.nan

    vh = float(agg.loc["Very High", "Total_Pubs"]) if "Very High" in agg.index else np.nan
    low = float(agg.loc["Low", "Total_Pubs"]) if "Low" in agg.index else np.nan
    hdi_gap = (vh / low) if (np.isfinite(vh) and np.isfinite(low) and low != 0) else np.nan

    return {
        "total_publications": float(total_pubs),
        "top5_publications": float(top5_pubs),
        "top10_publications": float(top10_pubs),
        "top5_share_pct": float(top5_share),
        "top10_share_pct": float(top10_share),
        "hdi_tier_gap_total": float(hdi_gap),
    }


def create_visualization(
    df: pd.DataFrame,
    agg: pd.DataFrame,
    corr: Dict[str, float],
    key_stats: Dict[str, float],
    mooc_df: pd.DataFrame,
) -> plt.Figure:
    """Create four-panel stratification visualization (full-country sample)."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors_hdi = {
        "Very High": "#27ae60",
        "High": "#3498db",
        "Medium": "#f39c12",
        "Low": "#e74c3c",
    }

    categories = [c for c in ["Very High", "High", "Medium", "Low"] if c in agg.index]

    # Panel 1: Publications by HDI tier (totals)
    ax1 = axes[0, 0]
    pubs = [agg.loc[c, "Total_Pubs"] for c in categories]
    bars = ax1.bar(categories, pubs, color=[colors_hdi[c] for c in categories], alpha=0.85)
    for bar, c in zip(bars, categories):
        count = int(agg.loc[c, "Country_Count"])
        val = float(agg.loc[c, "Total_Pubs"])
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(pubs) * 0.02,
            f"{int(val)}\n({count} countries)",
            ha="center",
            fontsize=9,
        )
    gap = key_stats.get("hdi_tier_gap_total", np.nan)
    gap_str = f"{gap:.1f}x" if np.isfinite(gap) else "N/A"
    ax1.set_ylabel("Country-Level Publication Attributions")
    ax1.set_title(f"Publications by HDI Tier (Totals)\n(Very High / Low = {gap_str})", fontweight="bold")

    # Panel 2: HDI vs Publications (log scale)
    ax2 = axes[0, 1]
    # Plot all points; use log1p to avoid 0.
    d = df.dropna(subset=["HDI"]).copy()
    for c in categories:
        subset = d[d["HDI_Category"] == c]
        ax2.scatter(subset["HDI"], subset["Log_Pubs"], c=colors_hdi[c], s=45, alpha=0.65, label=c)

    # Trend line in log space
    z = np.polyfit(d["HDI"], d["Log_Pubs"], 1)
    p = np.poly1d(z)
    x_line = np.linspace(0.35, 1.0, 100)
    ax2.plot(x_line, p(x_line), "k--", alpha=0.5)

    ax2.set_xlabel("Human Development Index (HDI, 2022)")
    ax2.set_ylabel("log10(Publications + 1)")
    ax2.set_title(
        "HDI vs Research Output (log scale)\n"
        f"Pearson r(log) = {corr['pearson_r_log']:.3f}, p = {corr['pearson_p_log']:.2g} (n={corr['n_countries_hdi']})",
        fontweight="bold",
    )
    ax2.legend(title="HDI Tier", loc="lower right", fontsize=8)
    ax2.grid(True, alpha=0.25)

    # Panel 3: "Cognitive trade deficit" scatter (CT growth vs GenAI growth)
    ax3 = axes[1, 0]
    ratios = mooc_df["CT_GenAI_Ratio"].astype(float).values
    colors_mooc = ["#27ae60" if r > 0.15 else "#f39c12" if r > 0.10 else "#e74c3c" for r in ratios]

    # Diagonal = "balanced" growth (CT == GenAI). With current data, all regions fall below.
    max_x = float(mooc_df["GenAI_Growth"].max()) if len(mooc_df) else 1.0
    ax3.plot([0, max_x], [0, max_x], "k--", alpha=0.35, linewidth=1.2, label="1:1 balance")

    ax3.scatter(
        mooc_df["GenAI_Growth"],
        mooc_df["CT_Growth"],
        c=colors_mooc,
        s=90,
        alpha=0.9,
        edgecolors="white",
        linewidth=0.8,
    )
    for _, row in mooc_df.iterrows():
        ax3.annotate(
            f"{row['Region']} ({row['CT_GenAI_Ratio']:.2f})",
            xy=(row["GenAI_Growth"], row["CT_Growth"]),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8,
            color="#2c3e50",
        )

    ax3.set_xlabel("GenAI Skills Growth (%)")
    ax3.set_ylabel("Critical Thinking Growth (%)")
    ax3.set_title(
        "MOOC Enrollment: GenAI vs Critical Thinking\n(Below diagonal = adoption outpacing evaluation)",
        fontweight="bold",
    )
    ax3.grid(True, alpha=0.25)
    ax3.legend(loc="upper left", fontsize=8)

    # Panel 4: Top countries and concentration
    ax4 = axes[1, 1]
    top15 = df.nlargest(15, "Publications").copy()
    y_pos = np.arange(len(top15))
    tier_colors = [colors_hdi.get(c, "#7f8c8d") for c in top15["HDI_Category"].fillna("")]
    bars = ax4.barh(y_pos, top15["Publications"], color=tier_colors, alpha=0.85)
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(top15["Country"])
    ax4.invert_yaxis()
    ax4.set_xlabel("Publication Attributions")

    top5_share = key_stats.get("top5_share_pct", np.nan)
    top5_str = f"{top5_share:.0f}%" if np.isfinite(top5_share) else "N/A"
    ax4.set_title(f"Top Countries (Top-5 share = {top5_str})", fontweight="bold")
    for bar, val in zip(bars, top15["Publications"]):
        ax4.text(val + max(top15["Publications"]) * 0.01, bar.get_y() + bar.get_height() / 2, f"{int(val)}", va="center", fontsize=8)

    plt.suptitle(
        "Layer 4: Stratification Analysis (OpenAlex + UNDP HDI)\nFull-country merge (countries without attributions set to 0)",
        fontsize=13,
        fontweight="bold",
    )
    plt.tight_layout()
    return fig


def main():
    print("=" * 60)
    print("LAYER 4: STRATIFICATION ANALYSIS (REAL DATA, FULL SAMPLE)")
    print("=" * 60)

    print("\n1. Loading OpenAlex country attributions...")
    openalex_df, meta = load_openalex_country_counts()
    print(f"   OpenAlex groups: {len(openalex_df)}")
    print(f"   OpenAlex works count (meta): {meta.get('meta', {}).get('count')}")
    print(f"   Sum of country attributions: {openalex_df['Publications'].sum()}")

    print("\n2. Loading UNDP HDI data...")
    undp_df = load_undp_hdi()
    print(f"   UNDP countries in file: {len(undp_df)}")
    print(f"   HDI year used: {UNDP_HDI_YEAR}")

    print("\n3. Merging datasets (missing pubs set to 0)...")
    merged = merge_country_counts(openalex_df, undp_df)
    print(f"   Merged rows: {len(merged)}")

    print("\n4. Computing stratification aggregates...")
    agg = compute_stratification(merged)
    print(agg.to_string())

    print("\n5. Computing correlations...")
    corr = compute_correlations(merged)
    print(
        f"   Pearson r (raw): {corr['pearson_r_raw']:.3f}, p = {corr['pearson_p_raw']:.2g} (n={corr['n_countries_hdi']})"
    )
    print(
        f"   Pearson r (log10(pubs+1)): {corr['pearson_r_log']:.3f}, p = {corr['pearson_p_log']:.2g} (n={corr['n_countries_hdi']})"
    )
    print(
        f"   Spearman rho (raw): {corr['spearman_r_raw']:.3f}, p = {corr['spearman_p_raw']:.2g} (n={corr['n_countries_hdi']})"
    )

    print("\n6. Key concentration statistics...")
    key_stats = compute_key_statistics(merged, agg)
    print(f"   Total attributions: {int(key_stats['total_publications']):,}")
    print(f"   Top 5 share: {key_stats['top5_share_pct']:.1f}%")
    print(f"   Top 10 share: {key_stats['top10_share_pct']:.1f}%")
    if np.isfinite(key_stats["hdi_tier_gap_total"]):
        print(f"   HDI tier gap (Very High / Low, totals): {key_stats['hdi_tier_gap_total']:.1f}x")

    print("\n7. Loading regional MOOC data...")
    mooc_df = load_real_mooc_data()

    # Save outputs
    merged.to_csv(DATA_PROCESSED / "real_hdi_stratification.csv", index=False)
    mooc_df.to_csv(DATA_PROCESSED / "real_mooc_regional.csv", index=False)
    print(f"\n   Saved: {DATA_PROCESSED / 'real_hdi_stratification.csv'}")
    print(f"   Saved: {DATA_PROCESSED / 'real_mooc_regional.csv'}")

    print("\n8. Creating visualization...")
    fig = create_visualization(merged, agg, corr, key_stats, mooc_df)
    fig.savefig(FIGURES / "layer4_real_stratification.png", dpi=150, bbox_inches="tight")
    print(f"   Saved: {FIGURES / 'layer4_real_stratification.png'}")

    print("\n" + "=" * 60)
    print("Layer 4 analysis complete.")
    print("=" * 60)

    return merged, agg, corr, mooc_df


if __name__ == "__main__":
    df, agg, corr, mooc_df = main()
