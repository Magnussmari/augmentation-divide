#!/usr/bin/env python3
"""
Layer 3: Community Notes Analysis
=================================
Behavioral enactment: participation + responsiveness.

This script replaces the prior assumption-based "platform MAU" normalization with a real time-series
computed from note-level Community Notes data (note creation timestamps + author ids + tweet ids).

Primary dataset used here:
- Mohammadi et al. (2025; arXiv:2510.09585) curated dataset hosted on Zenodo (DOI: 10.5281/zenodo.16761304)
  File: notes_with_lang.csv (covers Jan 23, 2021 – Jan 23, 2025; 1,614,743 notes)

We compute:
- Monthly notes created
- Monthly active note writers (unique authors)
- Notes per active writer (participation "efficiency")
- Time-to-first-note (hours): for each tweet, time from tweet creation (decoded from tweet snowflake)
  to the first Community Note created on that tweet; summarized as monthly medians
- Global language distribution (note share + unique authors by language code)

We also retain (as external context, not recomputed here) aggregate outcomes reported by Mohammadi et al.:
- 8.3% of notes achieve "Helpful" status
- 87.7% remain "Needs More Ratings"
- Most prolific contributor authored 33,186 notes
- ~26-hour average delay before a note becomes publicly visible as "Helpful"

Outputs:
- data/processed/real_community_notes.csv (key metrics)
- data/processed/real_community_notes_monthly.csv (monthly series)
- data/processed/real_community_notes_language.csv (global language distribution)
- figures/layer3_real_community_notes.png

Author: Magnus Smári
Date: January 2026
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
FIGURES = PROJECT_ROOT / "figures"

DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)


# Input (large) dataset: Zenodo record 16761304 (Mohammadi et al.)
NOTES_WITH_LANG = DATA_RAW / "community_notes_zenodo" / "notes_with_lang.csv"
ZENODO_NOTES_URL = "https://zenodo.org/api/records/16761304/files/notes_with_lang.csv/content"


# Twitter/X snowflake epoch (ms)
TWITTER_EPOCH_MS = 1288834974657


CHATGPT_BREAK = pd.Timestamp("2022-11-01", tz="UTC")


@dataclass(frozen=True)
class ExternalQualityContext:
    """Aggregate outcomes reported by Mohammadi et al. (2025); kept for context."""

    helpfulness_rate: float = 0.083
    needs_more_ratings_rate: float = 0.877
    top_contributor_notes: int = 33186
    avg_hours_to_helpful_visible: int = 26


def _ensure_notes_file(path: Path) -> Path:
    if path.exists():
        return path
    raise FileNotFoundError(
        "\n".join(
            [
                f"Missing Community Notes dataset: {path}",
                "",
                "This script expects Mohammadi et al. (2025) Zenodo export:",
                "  DOI: 10.5281/zenodo.16761304",
                "  File: notes_with_lang.csv",
                "",
                "Download (large file ~443MB):",
                f"  curl -L --fail -o {path} {ZENODO_NOTES_URL}",
            ]
        )
    )


def _tweet_id_to_timestamp_ms(tweet_id_arr: np.ndarray) -> np.ndarray:
    """
    Convert tweet snowflake ids to creation timestamp in ms since epoch.

    Twitter snowflake format: timestamp_ms = (id >> 22) + TWITTER_EPOCH_MS
    """
    # Ensure uint64-like behavior for shifts; tweet ids fit into signed int64 but shifting is safer in uint64.
    ids = tweet_id_arr.astype("uint64", copy=False)
    return (ids >> np.uint64(22)).astype("int64") + TWITTER_EPOCH_MS


def compute_monthly_metrics(notes_csv: Path, chunksize: int = 200_000) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """
    Stream-process the notes file and compute:
    - monthly note counts
    - monthly active authors
    - notes per active author
    - time-to-first-note monthly medians (hours)
    - global totals
    """
    usecols = ["noteAuthorParticipantId", "tweetId", "date", "Timestamp", "language"]
    dtypes = {
        "noteAuthorParticipantId": "string",
        "tweetId": "int64",
        "date": "string",
        "Timestamp": "string",
        "language": "string",
    }

    month_note_counts: dict[str, int] = defaultdict(int)
    month_authors: dict[str, set[str]] = defaultdict(set)
    all_authors: set[str] = set()

    lang_note_counts: dict[str, int] = defaultdict(int)
    lang_authors: dict[str, set[str]] = defaultdict(set)

    # First-note timing: keep earliest note timestamp (ms) per tweetId.
    # Expect ~1M distinct tweets; dict is manageable and enables a real "response speed" proxy.
    earliest_note_ms_by_tweet: dict[int, int] = {}

    total_rows = 0
    dropped_rows = 0

    reader = pd.read_csv(
        notes_csv,
        usecols=usecols,
        dtype=dtypes,
        chunksize=chunksize,
    )

    for chunk in reader:
        total_rows += len(chunk)

        # Build note timestamp (UTC). Dataset stores date and time separately.
        note_ts = pd.to_datetime(chunk["date"].astype(str) + " " + chunk["Timestamp"].astype(str), utc=True, errors="coerce")
        chunk = chunk.assign(note_ts=note_ts)

        before = len(chunk)
        chunk = chunk.dropna(subset=["note_ts", "noteAuthorParticipantId", "tweetId"])
        dropped_rows += before - len(chunk)
        if chunk.empty:
            continue

        # Language distribution (global; not month-specific)
        lang = chunk["language"].fillna("unk").astype(str)
        vc_lang = lang.value_counts()
        for k, v in vc_lang.items():
            lang_note_counts[str(k)] += int(v)
        for k, sub in chunk.groupby(lang)["noteAuthorParticipantId"]:
            vals = sub.dropna().astype(str).unique().tolist()
            lang_authors[str(k)].update(vals)

        # Convert to period without emitting tz-drop warnings (timezone isn't meaningful at month granularity).
        month = chunk["note_ts"].dt.tz_convert(None).dt.to_period("M").astype(str)

        # Monthly note counts
        vc = month.value_counts()
        for m, c in vc.items():
            month_note_counts[m] += int(c)

        # Monthly active authors (exact, via sets)
        for m, sub in chunk.groupby(month)["noteAuthorParticipantId"]:
            # sub is a Series of strings
            vals = sub.dropna().astype(str).unique().tolist()
            month_authors[str(m)].update(vals)

        # Global unique authors
        all_authors.update(chunk["noteAuthorParticipantId"].dropna().astype(str).unique().tolist())

        # Per-tweet earliest note timestamp
        note_ms = (chunk["note_ts"].astype("int64") // 1_000_000).astype("int64")
        tmp = pd.DataFrame({"tweetId": chunk["tweetId"].astype("int64"), "note_ms": note_ms})
        min_per_tweet = tmp.groupby("tweetId", sort=False)["note_ms"].min()
        for tid, ms in min_per_tweet.items():
            tid_int = int(tid)
            ms_int = int(ms)
            prev = earliest_note_ms_by_tweet.get(tid_int)
            if prev is None or ms_int < prev:
                earliest_note_ms_by_tweet[tid_int] = ms_int

    # Assemble monthly dataframe
    months = sorted(month_note_counts.keys())
    monthly = pd.DataFrame(
        {
            "Month": months,
            "Notes": [month_note_counts[m] for m in months],
            "Active_Authors": [len(month_authors[m]) for m in months],
        }
    )
    monthly["Notes_per_Author"] = monthly["Notes"] / monthly["Active_Authors"].replace({0: np.nan})
    monthly["MonthStart"] = pd.to_datetime(monthly["Month"] + "-01", utc=True)

    # Time-to-first-note per tweet, grouped by month of the first note
    tweet_ids = np.fromiter(earliest_note_ms_by_tweet.keys(), dtype=np.int64, count=len(earliest_note_ms_by_tweet))
    first_note_ms = np.fromiter(earliest_note_ms_by_tweet.values(), dtype=np.int64, count=len(earliest_note_ms_by_tweet))
    tweet_ms = _tweet_id_to_timestamp_ms(tweet_ids)
    delta_hours = (first_note_ms - tweet_ms) / (1000 * 60 * 60)

    first_note_ts = pd.to_datetime(first_note_ms, unit="ms", utc=True)
    first_month = first_note_ts.tz_convert(None).to_period("M").astype(str)

    df_first = pd.DataFrame({"Month": first_month, "TimeToFirstNote_hours": delta_hours})
    # Remove pathological values (negative deltas can occur if ids are malformed; extreme values are retained)
    df_first = df_first[(df_first["TimeToFirstNote_hours"].notna()) & (df_first["TimeToFirstNote_hours"] >= 0)]
    first_median = df_first.groupby("Month")["TimeToFirstNote_hours"].median().rename("Median_TimeToFirstNote_hours")
    monthly = monthly.merge(first_median, on="Month", how="left")

    totals = {
        "total_notes": int(total_rows),
        "total_contributors": int(len(all_authors)),
        "total_distinct_posts": int(len(earliest_note_ms_by_tweet)),
        "dropped_rows": int(dropped_rows),
    }

    # Global language distribution
    lang_rows = []
    for k, v in lang_note_counts.items():
        lang_rows.append(
            {
                "Language": k,
                "Notes": int(v),
                "Notes_Share": (float(v) / float(total_rows)) if total_rows else np.nan,
                "Unique_Authors": int(len(lang_authors.get(k, set()))),
            }
        )
    lang_df = pd.DataFrame(lang_rows).sort_values("Notes", ascending=False)

    return monthly, totals, lang_df


def summarize_pre_post(monthly: pd.DataFrame) -> dict:
    pre = monthly[monthly["MonthStart"] < CHATGPT_BREAK]
    post = monthly[monthly["MonthStart"] >= CHATGPT_BREAK]

    # Use means for comparability with earlier "monthly average" reporting.
    out = {
        "pre_months": int(len(pre)),
        "post_months": int(len(post)),
        "pre_avg_monthly_notes": float(pre["Notes"].mean()),
        "post_avg_monthly_notes": float(post["Notes"].mean()),
        "pre_avg_active_authors": float(pre["Active_Authors"].mean()),
        "post_avg_active_authors": float(post["Active_Authors"].mean()),
        "pre_avg_notes_per_author": float(pre["Notes_per_Author"].mean()),
        "post_avg_notes_per_author": float(post["Notes_per_Author"].mean()),
        "pre_median_time_to_first_note_h": float(pre["Median_TimeToFirstNote_hours"].median()),
        "post_median_time_to_first_note_h": float(post["Median_TimeToFirstNote_hours"].median()),
    }

    # Growth factors
    out["raw_monthly_notes_growth_pct"] = (out["post_avg_monthly_notes"] / out["pre_avg_monthly_notes"] - 1) * 100
    out["active_authors_growth_pct"] = (out["post_avg_active_authors"] / out["pre_avg_active_authors"] - 1) * 100
    out["notes_per_author_growth_pct"] = (out["post_avg_notes_per_author"] / out["pre_avg_notes_per_author"] - 1) * 100
    out["time_to_first_note_change_pct"] = (out["post_median_time_to_first_note_h"] / out["pre_median_time_to_first_note_h"] - 1) * 100

    return out


def export_summary_csv(totals: dict, prepost: dict, ctx: ExternalQualityContext) -> pd.DataFrame:
    rows = [
        {"Metric": "Total Contributors (unique authors)", "Value": totals["total_contributors"], "Source": "Zenodo notes_with_lang.csv"},
        {"Metric": "Total Notes", "Value": totals["total_notes"], "Source": "Zenodo notes_with_lang.csv"},
        {"Metric": "Distinct Posts Annotated (tweetId count)", "Value": totals["total_distinct_posts"], "Source": "Zenodo notes_with_lang.csv"},
        {"Metric": "Pre-ChatGPT months", "Value": prepost["pre_months"], "Source": "Computed"},
        {"Metric": "Post-ChatGPT months", "Value": prepost["post_months"], "Source": "Computed"},
        {"Metric": "Pre avg monthly notes", "Value": round(prepost["pre_avg_monthly_notes"], 1), "Source": "Computed"},
        {"Metric": "Post avg monthly notes", "Value": round(prepost["post_avg_monthly_notes"], 1), "Source": "Computed"},
        {"Metric": "Raw monthly notes growth (%)", "Value": round(prepost["raw_monthly_notes_growth_pct"], 0), "Source": "Computed"},
        {"Metric": "Pre avg active authors", "Value": round(prepost["pre_avg_active_authors"], 1), "Source": "Computed"},
        {"Metric": "Post avg active authors", "Value": round(prepost["post_avg_active_authors"], 1), "Source": "Computed"},
        {"Metric": "Active authors growth (%)", "Value": round(prepost["active_authors_growth_pct"], 0), "Source": "Computed"},
        {"Metric": "Pre avg notes per active author", "Value": round(prepost["pre_avg_notes_per_author"], 3), "Source": "Computed"},
        {"Metric": "Post avg notes per active author", "Value": round(prepost["post_avg_notes_per_author"], 3), "Source": "Computed"},
        {"Metric": "Notes per author growth (%)", "Value": round(prepost["notes_per_author_growth_pct"], 0), "Source": "Computed"},
        {"Metric": "Pre median time-to-first-note (hours)", "Value": round(prepost["pre_median_time_to_first_note_h"], 2), "Source": "Computed"},
        {"Metric": "Post median time-to-first-note (hours)", "Value": round(prepost["post_median_time_to_first_note_h"], 2), "Source": "Computed"},
        {"Metric": "Time-to-first-note change (%)", "Value": round(prepost["time_to_first_note_change_pct"], 0), "Source": "Computed"},
        {"Metric": "Helpful rate (%)", "Value": ctx.helpfulness_rate * 100, "Source": "Mohammadi et al. (2025)"},
        {"Metric": "Needs More Ratings rate (%)", "Value": ctx.needs_more_ratings_rate * 100, "Source": "Mohammadi et al. (2025)"},
        {"Metric": "Top contributor notes", "Value": ctx.top_contributor_notes, "Source": "Mohammadi et al. (2025)"},
        {"Metric": "Avg hours to Helpful visible", "Value": ctx.avg_hours_to_helpful_visible, "Source": "Mohammadi et al. (2025)"},
        {"Metric": "Dropped rows (timestamp parse failures)", "Value": totals["dropped_rows"], "Source": "Computed"},
    ]
    return pd.DataFrame(rows)


def create_visualization(monthly: pd.DataFrame, prepost: dict, ctx: ExternalQualityContext):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: Monthly notes
    ax1 = axes[0, 0]
    ax1.plot(monthly["MonthStart"], monthly["Notes"], color="#3498db", linewidth=1.8)
    ax1.axvline(CHATGPT_BREAK, color="red", linestyle="--", alpha=0.7)
    ax1.set_title("Monthly Notes Created", fontweight="bold")
    ax1.set_ylabel("Notes / month")
    ax1.grid(True, alpha=0.3)

    # Panel 2: Monthly active authors
    ax2 = axes[0, 1]
    ax2.plot(monthly["MonthStart"], monthly["Active_Authors"], color="#2ecc71", linewidth=1.8)
    ax2.axvline(CHATGPT_BREAK, color="red", linestyle="--", alpha=0.7)
    ax2.set_title("Monthly Active Note Writers", fontweight="bold")
    ax2.set_ylabel("Unique authors / month")
    ax2.grid(True, alpha=0.3)

    # Panel 3: Notes per active author (efficiency / intensity)
    ax3 = axes[1, 0]
    ax3.plot(monthly["MonthStart"], monthly["Notes_per_Author"], color="#9b59b6", linewidth=1.8)
    ax3.axvline(CHATGPT_BREAK, color="red", linestyle="--", alpha=0.7)
    ax3.set_title("Notes per Active Writer (Participation Intensity)", fontweight="bold")
    ax3.set_ylabel("Notes / active author / month")
    ax3.grid(True, alpha=0.3)

    # Panel 4: Time-to-first-note (median, hours)
    ax4 = axes[1, 1]
    ax4.plot(monthly["MonthStart"], monthly["Median_TimeToFirstNote_hours"], color="#e67e22", linewidth=1.8)
    ax4.axvline(CHATGPT_BREAK, color="red", linestyle="--", alpha=0.7, label="ChatGPT (Nov 2022)")
    ax4.set_title("Responsiveness: Median Time-to-First-Note", fontweight="bold")
    ax4.set_ylabel("Hours (median)")
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc="upper right")

    # Subtitle / key summary box
    subtitle = (
        "Layer 3 (Community Notes): Real time-series (Zenodo 10.5281/zenodo.16761304)\n"
        f"Pre→Post avg monthly notes: {prepost['pre_avg_monthly_notes']:.0f} → {prepost['post_avg_monthly_notes']:.0f} "
        f"({prepost['raw_monthly_notes_growth_pct']:.0f}%) | "
        f"Active authors: {prepost['pre_avg_active_authors']:.0f} → {prepost['post_avg_active_authors']:.0f} "
        f"({prepost['active_authors_growth_pct']:.0f}%)\n"
        f"Notes/author: {prepost['pre_avg_notes_per_author']:.2f} → {prepost['post_avg_notes_per_author']:.2f} "
        f"({prepost['notes_per_author_growth_pct']:.0f}%) | "
        f"Median time-to-first-note: {prepost['pre_median_time_to_first_note_h']:.1f}h → {prepost['post_median_time_to_first_note_h']:.1f}h\n"
        f"Context (Mohammadi et al., 2025): Helpful={ctx.helpfulness_rate*100:.1f}% | NeedsMoreRatings={ctx.needs_more_ratings_rate*100:.1f}%"
    )
    plt.suptitle(subtitle, fontsize=12, fontweight="bold")
    plt.tight_layout(rect=[0, 0.02, 1, 0.92])
    return fig


def main():
    print("=" * 60)
    print("LAYER 3: COMMUNITY NOTES ANALYSIS (REAL TIME-SERIES)")
    print("=" * 60)

    notes_path = _ensure_notes_file(NOTES_WITH_LANG)
    ctx = ExternalQualityContext()

    print("\n1. Loading note-level Community Notes data (Zenodo: 10.5281/zenodo.16761304)...")
    print(f"   File: {notes_path}")

    print("\n2. Computing monthly participation + responsiveness metrics (streaming)...")
    monthly, totals, lang_df = compute_monthly_metrics(notes_path)
    prepost = summarize_pre_post(monthly)

    print("\n3. Key totals (from dataset):")
    print(f"   Total Contributors: {totals['total_contributors']:,}")
    print(f"   Total Notes: {totals['total_notes']:,}")
    print(f"   Distinct Posts Annotated: {totals['total_distinct_posts']:,}")
    if totals["dropped_rows"] > 0:
        print(f"   Dropped rows (timestamp parse): {totals['dropped_rows']:,}")

    print("\n4. Pre/Post ChatGPT (real time-series; no platform MAU assumptions):")
    print(f"   Pre months: {prepost['pre_months']} | Post months: {prepost['post_months']}")
    print(f"   Avg monthly notes: {prepost['pre_avg_monthly_notes']:.0f} -> {prepost['post_avg_monthly_notes']:.0f} "
          f"({prepost['raw_monthly_notes_growth_pct']:.0f}%)")
    print(f"   Avg monthly active authors: {prepost['pre_avg_active_authors']:.0f} -> {prepost['post_avg_active_authors']:.0f} "
          f"({prepost['active_authors_growth_pct']:.0f}%)")
    print(f"   Avg notes per active author: {prepost['pre_avg_notes_per_author']:.2f} -> {prepost['post_avg_notes_per_author']:.2f} "
          f"({prepost['notes_per_author_growth_pct']:.0f}%)")
    print(f"   Median time-to-first-note (hours): {prepost['pre_median_time_to_first_note_h']:.1f}h -> "
          f"{prepost['post_median_time_to_first_note_h']:.1f}h ({prepost['time_to_first_note_change_pct']:.0f}%)")

    print("\n   External quality context (Mohammadi et al., 2025):")
    print(f"   Helpful (4y total): {ctx.helpfulness_rate*100:.1f}%")
    print(f"   Needs More Ratings (4y total): {ctx.needs_more_ratings_rate*100:.1f}%")
    print(f"   Top contributor notes: {ctx.top_contributor_notes:,}")
    print(f"   Avg hours to 'Helpful' visible: {ctx.avg_hours_to_helpful_visible}")

    # Save outputs
    monthly_out = monthly.drop(columns=["MonthStart"]).copy()
    monthly_out.to_csv(DATA_PROCESSED / "real_community_notes_monthly.csv", index=False)

    summary = export_summary_csv(totals, prepost, ctx)
    summary.to_csv(DATA_PROCESSED / "real_community_notes.csv", index=False)

    # Language distribution (global)
    lang_df.to_csv(DATA_PROCESSED / "real_community_notes_language.csv", index=False)

    print(f"\n   Saved: {DATA_PROCESSED / 'real_community_notes.csv'}")
    print(f"   Saved: {DATA_PROCESSED / 'real_community_notes_monthly.csv'}")
    print(f"   Saved: {DATA_PROCESSED / 'real_community_notes_language.csv'}")

    print("\n5. Creating visualization...")
    fig = create_visualization(monthly, prepost, ctx)
    fig.savefig(FIGURES / "layer3_real_community_notes.png", dpi=150, bbox_inches="tight")
    print(f"   Saved: {FIGURES / 'layer3_real_community_notes.png'}")

    print("\n" + "=" * 60)
    print("Layer 3 analysis complete.")
    print("=" * 60)

    return monthly, totals, prepost


if __name__ == "__main__":
    main()
