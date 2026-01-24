# Methodology

## Overview

This document describes the four-layer validation methodology used to test the Cognitive Resurgence Hypothesis.

---

## Research Design

### Hypothesis

> The post-2022 generative AI period is temporally aligned with increased critical thinking interest and verification behavior. Placebo breakpoint and pre-trend tests indicate these shifts are better interpreted as acceleration of pre-existing trends rather than uniquely initiated by ChatGPT.

### Approach

We employ **methodological triangulation** across four distinct evidence types:

| Layer | Domain | Data Type | Method |
|-------|--------|-----------|--------|
| 1 | Public Interest | Search behavior | Time series analysis |
| 2 | Institutional Discourse | Academic publications | Bibliometric analysis |
| 3 | Behavioral Enactment | Verification participation | Time series + intensity/responsiveness metrics |
| 4 | Geographic Stratification | Cross-national comparison | Correlation analysis |

---

## Layer 1: Google Trends Analysis

### Data Collection
- **Source**: Google Trends API via pytrends
- **Terms**: "critical thinking" in English, Spanish, French, German
- **Period**: January 2016 - December 2025 (120 months)
- **Intervention point**: November 2022

### Statistical Methods

#### Mann-Whitney U Test
- **Purpose**: Non-parametric test for distribution shift
- **Null hypothesis**: Pre and post distributions are identical
- **Alternative**: Post-intervention distribution is shifted higher
- **Chosen because**: Robust to non-normality; appropriate for ordinal SVI data

```python
from scipy.stats import mannwhitneyu
stat, p_value = mannwhitneyu(pre, post, alternative='less')
```

#### Segmented Regression
- **Purpose**: Detect change in trend slope at intervention point
- **Model**: SVI = β₀ + β₁(time) + β₂(post) + β₃(time×post) + ε
- **Key parameter**: β₃ (slope change)
- **R²**: Variance explained by model
- **Inference**: Newey-West / HAC robust standard errors (monthly data)

```python
import statsmodels.api as sm
X = sm.add_constant(df[['time', 'post', 'time_post']])
model = OLS(df['svi'], X).fit(cov_type='HAC', cov_kwds={'maxlags': 6})
slope_change = model.params['time_post']
```

### Effect Size Calculation
```
Effect (%) = ((Post_Median - Pre_Median) / Pre_Median) × 100
```

---

## Layer 2: Bibliometric Analysis

### Data Collection
- **Source**: OpenAlex API
- **Query**: "critical thinking" AND ("artificial intelligence" OR "generative AI")
- **Period**: 2018-2025

### Statistical Methods

#### Year-over-Year Growth
```python
df['yoy'] = df['publications'].pct_change() * 100
```

#### Structural Break Detection
- **Method**: Pre/post regression comparison
- **Split point**: 2023
- **Metric**: Slope ratio (acceleration factor)

```python
# Pre-2023 regression
model_pre = OLS(y[pre_mask], X_pre).fit()
# Post-2023 regression
model_post = OLS(y[post_mask], X_post).fit()
# Acceleration
acceleration = model_post.params[1] / model_pre.params[1]
```

#### Burst Detection
- **Method**: Z-score threshold
- **Threshold**: z > 1.5
- **Interpretation**: Sustained deviation from historical pattern

```python
df['zscore'] = (df['pubs'] - df['pubs'].mean()) / df['pubs'].std()
df['burst'] = df['zscore'] > 1.5
```

#### Field-Normalized "Critical Ratio" (Signal-to-Noise Check)
**Purpose**: Control for overall growth in AI publications.

Critical Ratio = (CT+AI publications) / (Total AI publications)

In this repository, the denominator uses OpenAlex concept id `C154945302` (Artificial Intelligence), grouped by `publication_year`, and the ratio is scaled per 10,000 AI papers for interpretability.

---

## Layer 3: Community Notes Analysis

### Data Collection
- **Primary source**: Mohammadi et al. (2025; arXiv:2510.09585)
- **Dataset used here**: Zenodo record `10.5281/zenodo.16761304` (`notes_with_lang.csv`)
- **Period**: Jan 23, 2021 – Jan 23, 2025 (note-level timestamps)

### Derived Time-Series Metrics (No MAU Assumptions)
From the note-level file, we compute:
- Monthly notes created
- Monthly active note writers (unique authors)
- Notes per active writer (participation intensity)
- Median time-to-first-note (hours) using tweet-id snowflake decoding (responsiveness proxy)
- Global language distribution (note share + unique authors by language code)

### Quality Validation
- **Metric**: Four-year aggregate note outcomes reported in Mohammadi et al. (e.g., % "Helpful", % "Needs More Ratings")
- **Constraint**: This replication package does not recompute month-by-month note-status outcomes (e.g., Helpful vs Not Helpful) from raw ratings; it treats Mohammadi et al.'s aggregate outcomes as context.

---

## Layer 4: Stratification Analysis

### Data Collection
- **HDI data**: UNDP HDR23-24 time series CSV (HDI 2022 values + `hdicode` tiers)
- **Research output**: OpenAlex country-level attribution counts (`group_by=authorships.countries`; countries missing in OpenAlex are assigned 0)
- **MOOC data**: Coursera Global Skills Report 2025

### Statistical Methods

#### HDI-Research Correlation
```python
from scipy.stats import pearsonr
r, p = pearsonr(df['HDI'], df['Publications'])
```

#### Research Index Calculation
```python
baseline = agg.loc['Very High', 'ct_publications']
agg['research_index'] = (agg['ct_publications'] / baseline) × 100
agg['gap_pct'] = 100 - agg['research_index']
```

#### CT:GenAI Ratio
**Purpose**: Measure balance between critical thinking and AI adoption
```python
ratio = ct_growth / genai_growth
```

**Interpretation**:
- Ratio ≈ 1: Balanced development
- Ratio < 1: AI adoption outpacing CT development (debt accumulation)
- Ratio = 0.46 (Latin America): 2.2:1 imbalance (most balanced)
- Ratio = 0.04 (Sub-Saharan Africa): 22:1 imbalance (most unbalanced)

---

## Reproducibility

### Dependencies
See `requirements.txt` for exact package versions.

### Code Availability
All analysis scripts are provided in `scripts/` directory with inline documentation.

---

## Limitations

1. **Correlation ≠ causation**: Temporal alignment does not prove causal relationship
2. **Selection bias**: Community Notes contributors are self-selected
3. **Proxy measures**: Language as proxy for geography; enrollment as proxy for learning
4. **Community Notes validity**: Monthly participation metrics are real (timestamp-derived), but (a) they are confounded by the program's late-2022 expansion, and (b) note-status quality outcomes are not recomputed month-by-month in this repository.

---

## Validation Approach

The four-layer design provides:

1. **Convergence**: If all layers show aligned inflection points, confidence increases
2. **Independence**: Different data sources reduce common-method bias
3. **Complementarity**: Each layer addresses limitations of others
4. **Qualification**: Layer 4 qualifies findings from Layers 1-3

---

*Last updated: January 2026*
