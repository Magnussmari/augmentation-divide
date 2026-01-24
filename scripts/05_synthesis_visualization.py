#!/usr/bin/env python3
"""
Synthesis: Four-Layer Summary Visualization
==========================================
Creates a compact synthesis figure that summarizes all four layers using REAL data.

Design intent:
- Be visually useful for readers.
- Avoid over-claiming causality (placebo tests show Nov 2022 is not uniquely identified).
- Prefer proportional/efficiency signals when available (e.g., Layer 2 "Critical Ratio",
  Layer 3 notes/author and time-to-first-note).

Outputs:
- figures/four_layer_synthesis.png

Author: Magnus Smári
Date: January 2026
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
FIGURES = PROJECT_ROOT / "figures"

FIGURES.mkdir(parents=True, exist_ok=True)


CHATGPT_BREAK_YEAR = 2022.5  # visual marker for Nov 2022 on annual plots


def _pct_change(pre: float, post: float) -> float:
    if np.isfinite(pre) and np.isfinite(post) and pre != 0:
        return (post / pre - 1) * 100
    return np.nan


def main():
    print("=" * 60)
    print("SYNTHESIS: FOUR-LAYER SUMMARY (REAL DATA)")
    print("=" * 60)

    print("\n1. Loading processed real data...")
    trends = pd.read_csv(DATA_PROCESSED / "real_trends_analysis.csv")
    biblio = pd.read_csv(DATA_PROCESSED / "real_bibliometrics.csv")
    cn = pd.read_csv(DATA_PROCESSED / "real_community_notes.csv")
    cn_lang_path = DATA_PROCESSED / "real_community_notes_language.csv"
    cn_lang = pd.read_csv(cn_lang_path) if cn_lang_path.exists() else None
    strat = pd.read_csv(DATA_PROCESSED / "real_hdi_stratification.csv")
    mooc = pd.read_csv(DATA_PROCESSED / "real_mooc_regional.csv")
    robustness_path = DATA_PROCESSED / "robustness_checks.csv"
    robustness = pd.read_csv(robustness_path) if robustness_path.exists() else None

    print("\n2. Creating synthesis visualization...")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # -----------------------
    # Layer 1: Google Trends
    # -----------------------
    ax1 = axes[0, 0]
    order = ["Spanish", "German", "French", "English"]
    trends = trends.set_index("Language", drop=False)

    use_slope = "Slope_Change" in trends.columns
    if use_slope:
        vals = [float(trends.loc[l, "Slope_Change"]) for l in order]
        p_col = "Slope_Change_P_HAC" if "Slope_Change_P_HAC" in trends.columns else None
        p_values = [float(trends.loc[l, p_col]) if p_col else np.nan for l in order]
        ylabel = "Slope change (SVI / month)"
        title = "Layer 1: Public Interest\n(Google Trends; ITS slope-change)"
    else:
        vals = [float(trends.loc[l, "Effect_Pct"]) for l in order]
        p_values = [float(trends.loc[l, "MW_P_Value"]) for l in order]
        ylabel = "Median shift (%)"
        title = "Layer 1: Public Interest\n(Google Trends; median shift)"

    colors_l1 = ["#2c3e50" if (np.isfinite(p) and p < 0.05) else "#95a5a6" for p in p_values]
    bars = ax1.bar(order, vals, color=colors_l1, alpha=0.85)
    ax1.axhline(0, color="black", linewidth=0.5)
    ax1.set_ylabel(ylabel)
    ax1.set_title(title, fontweight="bold")
    for bar, val, pv in zip(bars, vals, p_values):
        if np.isfinite(pv):
            p_str = "p < .001" if pv < 0.001 else f"p = {pv:.3f}"
        else:
            p_str = "p = N/A"

        if use_slope:
            txt = f"{val:+.3f}\n{p_str}"
            y_off = (max(vals) - min(vals)) * 0.03 if len(vals) else 0.0
        else:
            txt = f"{val:+.0f}%\n{p_str}"
            y_off = 5

        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + y_off,
            txt,
            ha="center",
            fontsize=9,
            fontweight="bold" if (np.isfinite(pv) and pv < 0.05) else "normal",
        )

    if robustness is not None and "chatgpt_median_strongest" in robustness.columns:
        n_strong = int(robustness["chatgpt_median_strongest"].sum())
        ax1.text(
            0.02,
            0.02,
            f"Placebo check: Nov 2022 strongest in {n_strong}/4 languages",
            transform=ax1.transAxes,
            fontsize=9,
            color="#7f8c8d",
        )

    # -------------------------
    # Layer 2: Bibliometrics
    # -------------------------
    ax2 = axes[0, 1]
    if "Critical_Ratio_per_10k" in biblio.columns:
        ax2.plot(
            biblio["Year"],
            biblio["Critical_Ratio_per_10k"],
            "o-",
            color="#2ecc71",
            linewidth=2,
            markersize=8,
            label="CT+AI per 10k AI papers",
        )
        ax2.axvline(CHATGPT_BREAK_YEAR, color="red", linestyle="--", alpha=0.7, label="ChatGPT")
        ax2.set_ylabel("CT+AI per 10,000 AI papers")
        ax2.set_title(
            "Layer 2: Institutional Discourse\n(OpenAlex; field-normalized ratio)",
            fontweight="bold",
        )
    else:
        ax2.semilogy(
            biblio["Year"],
            biblio["CT_AI_Pubs"],
            "o-",
            color="#e74c3c",
            linewidth=2,
            markersize=8,
            label="CT+AI",
        )
        ax2.semilogy(
            biblio["Year"],
            biblio["GenAI_Ed_Pubs"],
            "s--",
            color="#3498db",
            linewidth=2,
            markersize=7,
            label="GenAI+Ed",
        )
        ax2.axvline(CHATGPT_BREAK_YEAR, color="red", linestyle="--", alpha=0.7, label="ChatGPT")
        ax2.set_ylabel("Publications (log scale)")
        ax2.set_title("Layer 2: Institutional Discourse\n(OpenAlex; volume)", fontweight="bold")

    ax2.set_xlabel("Year")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)

    # -------------------------------
    # Layer 3: Community Notes
    # -------------------------------
    ax3 = axes[1, 0]
    ax3.axis("off")
    ax3.set_title(
        "Layer 3: Behavioral Enactment\n(Community Notes; real monthly series)",
        fontweight="bold",
    )

    cn_dict = dict(zip(cn["Metric"], cn["Value"]))
    total_contributors = float(cn_dict.get("Total Contributors (unique authors)", cn_dict.get("Total Contributors", 0)))
    total_notes = float(cn_dict.get("Total Notes", 0))
    helpful_pct = float(cn_dict.get("Helpful rate (%)", cn_dict.get("Helpfulness Rate (%)", np.nan)))
    needs_more_pct = float(cn_dict.get("Needs More Ratings rate (%)", np.nan))

    pre_notes = float(cn_dict.get("Pre avg monthly notes", np.nan))
    post_notes = float(cn_dict.get("Post avg monthly notes", np.nan))
    pre_auth = float(cn_dict.get("Pre avg active authors", np.nan))
    post_auth = float(cn_dict.get("Post avg active authors", np.nan))
    pre_npa = float(cn_dict.get("Pre avg notes per active author", np.nan))
    post_npa = float(cn_dict.get("Post avg notes per active author", np.nan))
    pre_ttf = float(cn_dict.get("Pre median time-to-first-note (hours)", np.nan))
    post_ttf = float(cn_dict.get("Post median time-to-first-note (hours)", np.nan))

    g_notes = _pct_change(pre_notes, post_notes)
    g_auth = _pct_change(pre_auth, post_auth)
    g_npa = _pct_change(pre_npa, post_npa)
    g_ttf = _pct_change(pre_ttf, post_ttf)

    lines = [
        f"Notes/month: {pre_notes:,.0f} → {post_notes:,.0f} ({g_notes:+.0f}%)" if np.isfinite(g_notes) else "Notes/month: N/A",
        f"Active authors/month: {pre_auth:,.0f} → {post_auth:,.0f} ({g_auth:+.0f}%)" if np.isfinite(g_auth) else "Active authors/month: N/A",
        f"Notes/author: {pre_npa:.2f} → {post_npa:.2f} ({g_npa:+.0f}%)" if np.isfinite(g_npa) else "Notes/author: N/A",
        f"Median time-to-first-note: {pre_ttf:.1f}h → {post_ttf:.1f}h ({g_ttf:+.0f}%)" if np.isfinite(g_ttf) else "Median time-to-first-note: N/A",
        "",
        f"Totals: {total_contributors:,.0f} authors | {total_notes:,.0f} notes",
        f"Quality context (4y total): Helpful={helpful_pct:.1f}% | NeedsMoreRatings={needs_more_pct:.1f}%",
    ]
    if cn_lang is not None and "Notes_Share" in cn_lang.columns and len(cn_lang) > 0:
        top = cn_lang.iloc[0]
        lines.append(f"Language concentration: top={top['Language']} ({top['Notes_Share']*100:.1f}% of notes)")

    ax3.text(
        0.02,
        0.90,
        "\n".join(lines),
        transform=ax3.transAxes,
        fontsize=12,
        va="top",
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.95),
    )

    # -------------------------
    # Layer 4: Stratification
    # -------------------------
    ax4 = axes[1, 1]
    ax4.axis("off")
    ax4.set_title("Layer 4: Stratification\n(OpenAlex + UNDP + Coursera)", fontweight="bold")

    strat_by_hdi = strat.groupby("HDI_Category")["Publications"].sum()
    very_high = float(strat_by_hdi.get("Very High", np.nan))
    low = float(strat_by_hdi.get("Low", np.nan))
    gap_ratio = (very_high / low) if np.isfinite(very_high) and np.isfinite(low) and low != 0 else np.nan

    la_ratio = float(mooc.loc[mooc["Region"] == "Latin America", "CT_GenAI_Ratio"].iloc[0])
    top5_share = float(strat.nlargest(5, "Publications")["Publications"].sum() / strat["Publications"].sum() * 100)

    ax4.text(
        0.5,
        0.70,
        f"{gap_ratio:.1f}x" if np.isfinite(gap_ratio) else "N/A",
        fontsize=70,
        ha="center",
        va="center",
        transform=ax4.transAxes,
        color="#e74c3c",
        fontweight="bold",
    )
    ax4.text(0.5, 0.45, "HDI Tier Gap\n(Very High vs Low)", fontsize=14, ha="center", va="center", transform=ax4.transAxes)
    ax4.text(
        0.5,
        0.27,
        f"Latin America CT:GenAI = {la_ratio:.2f} (17:1 imbalance)",
        fontsize=11,
        ha="center",
        va="center",
        transform=ax4.transAxes,
        color="darkred",
    )
    ax4.text(
        0.5,
        0.17,
        f"Top-5 share (attributions): {top5_share:.1f}%",
        fontsize=11,
        ha="center",
        va="center",
        transform=ax4.transAxes,
        color="#7f8c8d",
    )
    ax4.text(
        0.5,
        0.09,
        "Concentration + Imbalance",
        fontsize=11,
        ha="center",
        va="center",
        transform=ax4.transAxes,
        color="#7f8c8d",
        style="italic",
    )

    plt.suptitle(
        "Four-Layer Triangulation (Real Data)\n"
        "Acceleration-consistent signals + structural concentration",
        fontsize=16,
        fontweight="bold",
    )
    plt.tight_layout()

    out = FIGURES / "four_layer_synthesis.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"   Saved: {out}")

    # Console summary (conservative; avoids re-asserting causality)
    print("\n" + "=" * 60)
    print("SYNTHESIS SUMMARY (CONSERVATIVE)")
    print("=" * 60)
    if robustness is not None and "chatgpt_median_strongest" in robustness.columns:
        n_strong = int(robustness["chatgpt_median_strongest"].sum())
        n_pre = int(robustness["pre_trend_significant"].sum()) if "pre_trend_significant" in robustness.columns else None
        print(f"Layer 1 placebo: Nov 2022 strongest median shift in {n_strong}/4 languages")
        if n_pre is not None:
            print(f"Layer 1 pre-trends: significant pre-trend in {n_pre}/4 languages")

    if "Critical_Ratio_per_10k" in biblio.columns:
        try:
            r2022 = float(biblio.loc[biblio["Year"] == 2022, "Critical_Ratio_per_10k"].iloc[0])
            r2024 = float(biblio.loc[biblio["Year"] == 2024, "Critical_Ratio_per_10k"].iloc[0])
            print(f"Layer 2 ratio (CT+AI per 10k AI papers): {r2022:.2f} (2022) → {r2024:.2f} (2024) = {r2024/r2022:.1f}x")
        except Exception:
            pass

    if np.isfinite(g_notes):
        print(f"Layer 3: notes/month +{g_notes:.0f}%; authors/month +{g_auth:.0f}%; notes/author +{g_npa:.0f}%")

    if np.isfinite(gap_ratio):
        print(f"Layer 4: HDI tier gap {gap_ratio:.1f}x; Latin America CT:GenAI {la_ratio:.2f}")

    print("=" * 60)
    print("Synthesis complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()

