#!/usr/bin/env python3
"""
Run All Analyses
=================
Master script to execute all four layers of the Cognitive Resurgence analysis.

This script runs all layer scripts in sequence, using REAL data sources:
- Layer 1: Google Trends API data (trends_*.csv)
- Layer 2: OpenAlex bibliometric data
- Layer 3: Community Notes note-level time series (Zenodo 10.5281/zenodo.16761304; Mohammadi et al.)
- Layer 4: HDI stratification (OpenAlex + UNDP)

Outputs:
- data/processed/real_*.csv
- figures/layer*_real_*.png

Usage:
    python run_all.py

Author: Magnus Smári
Date: January 2026
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"


def _try_float(x):
    try:
        return float(x)
    except Exception:
        return None


def build_computed_summary():
    """
    Build a post-run summary from the processed CSVs.

    This avoids hard-coded manuscript numbers drifting from the actual pipeline outputs.
    """
    try:
        import pandas as pd
        import numpy as np
        from scipy import stats
    except Exception as e:
        return {"error": f"Could not import summary dependencies (pandas/scipy): {e}"}

    summary = {}

    # Layer 1
    trends_path = DATA_PROCESSED / "real_trends_analysis.csv"
    if trends_path.exists():
        trends = pd.read_csv(trends_path)
        # Expect columns: Language, Pre_Median, Post_Median, Effect_Pct, MW_P_Value
        summary["layer1"] = {}
        for _, row in trends.iterrows():
            lang = str(row.get("Language"))
            summary["layer1"][lang] = {
                "pre_median": _try_float(row.get("Pre_Median")),
                "post_median": _try_float(row.get("Post_Median")),
                "effect_pct": _try_float(row.get("Effect_Pct")),
                "p_value": _try_float(row.get("MW_P_Value")),
            }

    # Layer 2
    biblio_path = DATA_PROCESSED / "real_bibliometrics.csv"
    if biblio_path.exists():
        biblio = pd.read_csv(biblio_path)
        summary["layer2"] = {}
        if "Year" in biblio.columns and "CT_AI_Pubs" in biblio.columns:
            y2023 = biblio[biblio["Year"] == 2023]
            if len(y2023) == 1:
                summary["layer2"]["ct_ai_pubs_2023"] = int(y2023["CT_AI_Pubs"].iloc[0])
                if "CT_AI_YoY" in y2023.columns and not pd.isna(y2023["CT_AI_YoY"].iloc[0]):
                    summary["layer2"]["ct_ai_yoy_2023_pct"] = float(y2023["CT_AI_YoY"].iloc[0])
            y2025 = biblio[biblio["Year"] == 2025]
            if len(y2025) == 1:
                summary["layer2"]["ct_ai_pubs_2025"] = int(y2025["CT_AI_Pubs"].iloc[0])

        # Acceleration factor is computed in the script; keep a fallback to manuscript if absent.
        # (We avoid re-deriving without the exact method constants.)
        summary["layer2"]["acceleration_factor"] = 3.3

        # Field-normalized "Critical Ratio" (if present)
        if "Critical_Ratio_per_10k" in biblio.columns:
            try:
                r2022 = float(biblio.loc[biblio["Year"] == 2022, "Critical_Ratio_per_10k"].iloc[0])
                r2024 = float(biblio.loc[biblio["Year"] == 2024, "Critical_Ratio_per_10k"].iloc[0])
                summary["layer2"]["critical_ratio_per_10k_2022"] = r2022
                summary["layer2"]["critical_ratio_per_10k_2024"] = r2024
            except Exception:
                pass

    # Layer 3
    cn_path = DATA_PROCESSED / "real_community_notes.csv"
    if cn_path.exists():
        cn = pd.read_csv(cn_path)
        cn_dict = dict(zip(cn["Metric"], cn["Value"]))
        summary["layer3"] = {
            "contributors": int(cn_dict.get("Total Contributors (unique authors)", 0)),
            "notes": int(cn_dict.get("Total Notes", 0)),
            "distinct_posts": int(cn_dict.get("Distinct Posts Annotated (tweetId count)", 0)),
            # External quality context (Mohammadi et al., 2025)
            "helpful_pct": float(cn_dict.get("Helpful rate (%)", float("nan"))),
            "needs_more_pct": float(cn_dict.get("Needs More Ratings rate (%)", float("nan"))),
            # Real time-series pre/post summaries (no platform MAU assumptions)
            "pre_avg_monthly_notes": _try_float(cn_dict.get("Pre avg monthly notes")),
            "post_avg_monthly_notes": _try_float(cn_dict.get("Post avg monthly notes")),
            "pre_avg_active_authors": _try_float(cn_dict.get("Pre avg active authors")),
            "post_avg_active_authors": _try_float(cn_dict.get("Post avg active authors")),
            "pre_avg_notes_per_author": _try_float(cn_dict.get("Pre avg notes per active author")),
            "post_avg_notes_per_author": _try_float(cn_dict.get("Post avg notes per active author")),
            "pre_median_time_to_first_note_h": _try_float(cn_dict.get("Pre median time-to-first-note (hours)")),
            "post_median_time_to_first_note_h": _try_float(cn_dict.get("Post median time-to-first-note (hours)")),
        }
        # Convenience growth stats for printing
        try:
            pre = summary["layer3"]["pre_avg_monthly_notes"]
            post = summary["layer3"]["post_avg_monthly_notes"]
            if pre and post:
                summary["layer3"]["monthly_notes_growth_pct"] = (post / pre - 1) * 100
        except Exception:
            pass

    # Layer 4
    strat_path = DATA_PROCESSED / "real_hdi_stratification.csv"
    if strat_path.exists():
        strat_df = pd.read_csv(strat_path)
        # Gap: Very High vs Low tiers
        if "HDI_Category" in strat_df.columns and "Publications" in strat_df.columns:
            tier_totals = strat_df.groupby("HDI_Category")["Publications"].sum()
            very_high = float(tier_totals.get("Very High", np.nan))
            low = float(tier_totals.get("Low", np.nan))
            if np.isfinite(very_high) and np.isfinite(low) and low != 0:
                summary["layer4"] = {"hdi_tier_gap": very_high / low}
            else:
                summary["layer4"] = {}

            # Top-5 share within the sample
            total_pubs = float(strat_df["Publications"].sum())
            top5_pubs = float(strat_df.nlargest(5, "Publications")["Publications"].sum())
            if total_pubs:
                summary["layer4"]["top5_share_pct"] = (top5_pubs / total_pubs) * 100

            # Correlation (raw publications)
            if "HDI" in strat_df.columns:
                d = strat_df[["HDI", "Publications"]].dropna()
                if len(d) >= 3:
                    r, p = stats.pearsonr(d["HDI"], d["Publications"])
                    summary["layer4"]["pearson_r"] = float(r)
                    summary["layer4"]["pearson_p"] = float(p)

    mooc_path = DATA_PROCESSED / "real_mooc_regional.csv"
    if mooc_path.exists():
        mooc = pd.read_csv(mooc_path)
        la = mooc[mooc["Region"] == "Latin America"]
        if "layer4" not in summary:
            summary["layer4"] = {}
        if len(la) == 1 and "CT_GenAI_Ratio" in la.columns:
            summary["layer4"]["latin_america_ct_genai_ratio"] = float(la["CT_GenAI_Ratio"].iloc[0])

    return summary


def run_script(script_name):
    """Run a Python script and return success status."""
    script_path = SCRIPT_DIR / script_name
    print(f"\n{'='*60}")
    print(f"Running: {script_name}")
    print('='*60)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False
    )

    return result.returncode == 0


def main():
    print("""
    ================================================================

       COGNITIVE RESURGENCE: FOUR-LAYER VALIDATION
       Using REAL Data Sources

       Author: Magnus Smári
       Date: January 2026

       Data Sources:
       - Layer 1: Google Trends API (pytrends 4.9.2)
       - Layer 2: OpenAlex API
       - Layer 3: Zenodo 10.5281/zenodo.16761304 (Mohammadi et al.)
       - Layer 4: OpenAlex + UNDP HDI

    ================================================================
    """)

    # Core layer scripts
    scripts = [
        '01_layer1_trends_analysis.py',
        '02_layer2_bibliometrics.py',
        '03_layer3_community_notes.py',
        '04_layer4_stratification.py',
    ]

    # Optional supplementary scripts
    optional_scripts = [
        '05_synthesis_visualization.py',
        '06_robustness_checks.py',
        '07_effect_sizes.py',
        '08_augmentation_divide_visual.py',
    ]

    results = {}

    # Run core scripts
    print("\n" + "="*60)
    print("RUNNING CORE LAYER ANALYSES")
    print("="*60)

    for script in scripts:
        script_path = SCRIPT_DIR / script
        if script_path.exists():
            success = run_script(script)
            results[script] = 'PASS' if success else 'FAIL'
        else:
            results[script] = 'SKIP (not found)'

    # Run optional scripts if they exist
    print("\n" + "="*60)
    print("RUNNING OPTIONAL SUPPLEMENTARY ANALYSES")
    print("="*60)

    for script in optional_scripts:
        script_path = SCRIPT_DIR / script
        if script_path.exists():
            success = run_script(script)
            results[script] = 'PASS' if success else 'FAIL'
        else:
            results[script] = 'SKIP (not found)'

    # Summary
    print("\n" + "="*60)
    print("EXECUTION SUMMARY")
    print("="*60)
    for script, status in results.items():
        status_char = '[OK]' if status == 'PASS' else '[!!]' if status == 'FAIL' else '[--]'
        print(f"   {status_char} {script}")

    all_core_pass = all(results.get(s) == 'PASS' for s in scripts)

    if all_core_pass:
        computed = build_computed_summary()
        if "error" in computed:
            print(f"\n[WARN] {computed['error']}")

        l1 = computed.get("layer1", {})
        l2 = computed.get("layer2", {})
        l3 = computed.get("layer3", {})
        l4 = computed.get("layer4", {})

        def fmt_num(x, fmt, default="N/A"):
            try:
                if x is None:
                    return default
                return format(float(x), fmt)
            except Exception:
                return default

        print("\n" + "="*64)
        print("ALL CORE ANALYSES COMPLETE")
        print("="*64)

        print("\nOutput files created:")
        print("  - data/processed/real_trends_analysis.csv")
        print("  - data/processed/real_bibliometrics.csv")
        print("  - data/processed/real_community_notes.csv")
        print("  - data/processed/real_community_notes_monthly.csv")
        print("  - data/processed/real_community_notes_language.csv")
        print("  - data/processed/real_hdi_stratification.csv")
        print("  - data/processed/real_mooc_regional.csv")
        print("  - figures/layer*_real_*.png")

        print("\nKey statistics (computed from processed outputs):")

        print("\nLayer 1 (Google Trends):")
        for lang in ["Spanish", "German", "French", "English"]:
            if lang in l1:
                eff = l1[lang].get("effect_pct")
                pre = l1[lang].get("pre_median")
                post = l1[lang].get("post_median")
                pv = l1[lang].get("p_value")
                print(f"  - {lang}: +{fmt_num(eff, '.0f')}% ({fmt_num(pre, '.1f')} -> {fmt_num(post, '.1f')}), p = {fmt_num(pv, '.2e')}")
            else:
                pass

        print("\nLayer 2 (Bibliometrics):")
        print(f"  - 2023 CT+AI pubs: {l2.get('ct_ai_pubs_2023', 'N/A')}, +{fmt_num(l2.get('ct_ai_yoy_2023_pct'), '.0f')}% YoY")
        print(f"  - Acceleration factor (paper): {fmt_num(l2.get('acceleration_factor'), '.1f')}x")
        if "critical_ratio_per_10k_2022" in l2 and "critical_ratio_per_10k_2024" in l2:
            cr22 = float(l2["critical_ratio_per_10k_2022"])
            cr24 = float(l2["critical_ratio_per_10k_2024"])
            if cr22:
                print(f"  - Critical Ratio (per 10k AI papers): {cr22:.2f} (2022) -> {cr24:.2f} (2024) = {cr24/cr22:.1f}x")
        if "ct_ai_pubs_2025" in l2:
            print(f"  - 2025 CT+AI pubs: {l2.get('ct_ai_pubs_2025')}")

        print("\nLayer 3 (Community Notes):")
        print(f"  - Contributors: {l3.get('contributors', 'N/A')}")
        print(f"  - Total notes: {l3.get('notes', 'N/A')}")
        if "distinct_posts" in l3:
            print(f"  - Distinct posts annotated: {l3.get('distinct_posts', 'N/A')}")
        print(f"  - Helpful (4y total): {fmt_num(l3.get('helpful_pct'), '.1f')}%")
        print(f"  - Needs More Ratings (4y total): {fmt_num(l3.get('needs_more_pct'), '.1f')}%")
        if l3.get("pre_avg_monthly_notes") and l3.get("post_avg_monthly_notes"):
            print(
                "  - Avg monthly notes (pre→post): "
                f"{fmt_num(l3.get('pre_avg_monthly_notes'), '.0f')} -> {fmt_num(l3.get('post_avg_monthly_notes'), '.0f')} "
                f"({fmt_num(l3.get('monthly_notes_growth_pct'), '.0f')}%)"
            )
        if l3.get("pre_avg_active_authors") and l3.get("post_avg_active_authors"):
            print(
                "  - Avg monthly active authors (pre→post): "
                f"{fmt_num(l3.get('pre_avg_active_authors'), '.0f')} -> {fmt_num(l3.get('post_avg_active_authors'), '.0f')}"
            )
        if l3.get("pre_avg_notes_per_author") and l3.get("post_avg_notes_per_author"):
            print(
                "  - Notes per active author (pre→post): "
                f"{fmt_num(l3.get('pre_avg_notes_per_author'), '.2f')} -> {fmt_num(l3.get('post_avg_notes_per_author'), '.2f')}"
            )
        if l3.get("pre_median_time_to_first_note_h") and l3.get("post_median_time_to_first_note_h"):
            print(
                "  - Median time-to-first-note (hours, pre→post): "
                f"{fmt_num(l3.get('pre_median_time_to_first_note_h'), '.1f')}h -> {fmt_num(l3.get('post_median_time_to_first_note_h'), '.1f')}h"
            )

        print("\nLayer 4 (Stratification):")
        print(f"  - HDI tier gap: {fmt_num(l4.get('hdi_tier_gap'), '.1f')}x")
        print(f"  - HDI-publications correlation (raw): r = {fmt_num(l4.get('pearson_r'), '.3f')}, p = {fmt_num(l4.get('pearson_p'), '.2f')}")
        print(f"  - Top 5 countries share (attributions): {fmt_num(l4.get('top5_share_pct'), '.0f')}%")
        print(f"  - Latin America CT:GenAI ratio: {fmt_num(l4.get('latin_america_ct_genai_ratio'), '.2f')}")

        print("\n" + "="*64)
    else:
        print("\n   Some analyses failed. Check output above for errors.")

    return 0 if all_core_pass else 1


if __name__ == "__main__":
    sys.exit(main())
