# Data Provenance

## Layer 1: Google Trends

| File | Source | Query Term | Timeframe | Query Date | Script |
|------|--------|------------|-----------|------------|--------|
| `trends_english.csv` | Google Trends API (pytrends 4.9.2) | "critical thinking" | 2016-01-01 to 2025-12-31 | 2026-01-23 | `01_layer1_trends_analysis.py` |
| `trends_german.csv` | Google Trends API (pytrends 4.9.2) | "kritisches Denken" | 2016-01-01 to 2025-12-31 | 2026-01-23 | `01_layer1_trends_analysis.py` |
| `trends_french.csv` | Google Trends API (pytrends 4.9.2) | "pensée critique" | 2016-01-01 to 2025-12-31 | 2026-01-23 | `01_layer1_trends_analysis.py` |
| `trends_spanish.csv` | Google Trends API (pytrends 4.9.2) | "pensamiento crítico" | 2016-01-01 to 2025-12-31 | 2026-01-23 | `01_layer1_trends_analysis.py` |

## Layer 2: OpenAlex Bibliometrics

| File | Source | Filter | Grouping | Query Date | Script |
|------|--------|--------|----------|------------|--------|
| `real_bibliometrics.csv` | OpenAlex API | `title_and_abstract.search:critical thinking AND (artificial intelligence OR generative AI OR ChatGPT)` | `publication_year` | 2026-01-23 | `02_layer2_bibliometrics.py` |
| `openalex_total_ai_by_year_2026-01-23.json` | OpenAlex API | `concept.id:C154945302` (Artificial Intelligence) | `publication_year` | 2026-01-23 | `02_layer2_bibliometrics.py` |

## Layer 3: Community Notes

| File | Source | Dataset | Coverage | Access Date | Script |
|------|--------|---------|----------|-------------|--------|
| `data/raw/community_notes_zenodo/notes_with_lang.csv` | Zenodo (10.5281/zenodo.16761304), cited by Mohammadi et al. (2025; arXiv:2510.09585) | Note-level export with language tags | Jan 2021–Jan 2025 | 2026-01-23 | `03_layer3_community_notes.py` |
| `real_community_notes.csv` | Derived from Zenodo notes file + Mohammadi aggregate context | Monthly participation + responsiveness summary | Jan 2021–Jan 2025 | 2026-01-23 | `03_layer3_community_notes.py` |
| `real_community_notes_monthly.csv` | Derived from Zenodo notes file | Monthly time series (notes, active authors, notes/author, time-to-first-note) | Jan 2021–Jan 2025 | 2026-01-23 | `03_layer3_community_notes.py` |
| `real_community_notes_language.csv` | Derived from Zenodo notes file | Global language distribution (note share + unique authors by language) | Jan 2021–Jan 2025 | 2026-01-23 | `03_layer3_community_notes.py` |

## Layer 4: HDI Stratification

| File | Source | Parameters | Query Date | Script |
|------|--------|------------|------------|--------|
| `real_hdi_stratification.csv` | OpenAlex API + UNDP HDR (HDR23-24 time series CSV; HDI 2022 values) | OpenAlex group-by cached as `data/raw/openalex_ct_ai_authorships_countries_2026-01-23.json`; UNDP file `data/raw/HDR23-24_Composite_indices_complete_time_series.csv`; merged by ISO3 (missing pubs set to 0) | 2026-01-23 | `04_layer4_stratification.py` |

## Layer 4: MOOC Enrollment Data

| File | Source | Coverage | Access Date | Script |
|------|--------|----------|-------------|--------|
| `real_mooc_regional.csv` | Coursera Global Skills Report 2025 | Regional YoY enrollment growth (March 2024–February 2025) | 2026-01-24 | `04_layer4_stratification.py` |
| `data/raw/Global_Skills_Report_2025.pdf` | Coursera | Full report PDF (archived for reproducibility) | 2026-01-24 | — |

### MOOC Data Extraction Details

**Source URL**: https://www.coursera.org/skills-reports/global

**Extraction Method**: Manual extraction from PDF using `pdftotext`. Regional enrollment trends appear in the "Regional enrollment trends" sections of each regional chapter.

**Page References** (in PDF):
- Page 21: Asia Pacific – GenAI +132%, Critical Thinking +12%
- Page 33: Europe – GenAI +116%, Critical Thinking +14%
- Page 41: Latin America and the Caribbean – GenAI +425%, Critical Thinking +194%
- Page 49: Middle East & North Africa – GenAI +128%, Critical Thinking +19%
- Page 57: North America – GenAI +135%, Critical Thinking +15%
- Page 63: Sub-Saharan Africa – GenAI +134%, Critical Thinking +6%

**Ratio Calculation**: `CT_GenAI_Ratio = CT_Growth / GenAI_Growth`

**Note**: The original paper incorrectly reported Latin America CT growth as +25% (yielding a 17:1 ratio). The correct figure from the Coursera report is +194% (yielding a 2.2:1 ratio). This correction was made on 2026-01-24 after verification against the source PDF.

## Robustness Checks

| File | Analysis | Parameters | Script |
|------|----------|------------|--------|
| `robustness_checks.csv` | Pre-trend + placebo breakpoint checks | Pre-trend slope (HAC/Newey-West). Placebo breakpoints for median shift and ITS slope-change. | `06_robustness_checks.py` |
| `placebo_breakpoint_analysis.csv` | Placebo breakpoint grid | Median shift (Mann–Whitney) + ITS slope-change (HAC/Newey-West) across candidate breakpoints | `06_robustness_checks.py` |
