# Data Sources Documentation

## Overview

This document details all data sources used in the four-layer validation of the Cognitive Resurgence Hypothesis.

---

## Layer 1: Google Trends

### Source
- **Platform**: Google Trends (trends.google.com)
- **API**: pytrends Python library
- **Access**: Public, free

### Query Parameters
| Parameter | Value |
|-----------|-------|
| Terms | "critical thinking", "pensamiento crítico", "pensée critique", "kritisches Denken" |
| Timeframe | 2016-01-01 to 2025-12-31 |
| Geography | Worldwide |
| Frequency | Monthly |

### Data Description
- **Search Volume Index (SVI)**: Relative measure (0-100) of search interest
- **Observations**: 120 monthly data points per language
- **Intervention point**: November 2022 (ChatGPT launch)

### Access Instructions
```python
from pytrends.request import TrendReq

pytrends = TrendReq(hl='en-US', tz=0)
pytrends.build_payload(['critical thinking'], timeframe='2016-01-01 2025-12-31')
df = pytrends.interest_over_time()
```

### Limitations
- API rate limits may require batching
- Relative (not absolute) search volume
- Geographic aggregation may mask regional variation

---

## Layer 2: OpenAlex Bibliometric Data

### Source
- **Platform**: OpenAlex (openalex.org)
- **API**: REST API
- **Access**: Public, free, no authentication required

### Query Parameters
| Parameter | Value |
|-----------|-------|
| Search terms | "critical thinking" AND ("artificial intelligence" OR "generative AI" OR "ChatGPT") |
| Date range | 2016-2025 |
| Document types | Journal articles, conference papers |

### Data Description
- **Publication counts**: Annual totals by query
- **Metadata**: DOIs, abstracts, author affiliations, publication dates
- **Derived metrics**: YoY growth, burst detection (z-score), and a field-normalized "Critical Ratio" (CT+AI / Total AI papers) per year

### Access Instructions
```python
import requests

query = 'https://api.openalex.org/works?filter=title_and_abstract.search:critical thinking AND artificial intelligence,publication_year:2023&per_page=1'
response = requests.get(query).json()
count = response['meta']['count']
```

### Alternative Sources
- Scopus (requires institutional access)
- Web of Science (requires institutional access)
- Semantic Scholar (public API)

---

## Layer 3: Community Notes

### Source
- **Primary source**: Mohammadi et al. (2025; arXiv:2510.09585)
- **Dataset used in this replication**: Zenodo record `10.5281/zenodo.16761304` (cited by Mohammadi et al.)
  - File used: `notes_with_lang.csv` (note-level export with language tags)
- **Alternative raw source**: Community Notes publishes downloadable TSVs at https://communitynotes.x.com/guide/en/under-the-hood/download-data

### Data Description
- **Coverage used here**: Jan 23, 2021 – Jan 23, 2025 (note-level timestamps)
- **Key computed metrics** (author-derived from the note-level file):
  - Monthly notes created
  - Monthly active note writers (unique authors)
  - Notes per active writer (participation intensity)
  - Median time-to-first-note (hours) using tweet-id snowflake decoding (responsiveness proxy)
  - Language distribution (note share + unique authors by language code)
- **Quality context**:
  - The helpfulness/visibility aggregates (e.g., % Helpful, % Needs More Ratings) are taken from Mohammadi et al. (2025) and included as context; note-status outcomes are not recomputed month-by-month in this repository.

---

## Layer 4: HDI and Stratification Data

### Human Development Index
- **Source**: UNDP HDR23-24 composite indices time series CSV (HDI 2022 values + `hdicode` tiers)
- **File stored in-repo**: `data/raw/HDR23-24_Composite_indices_complete_time_series.csv`

### HDI Categories
| Category | HDI Range | Example Countries |
|----------|-----------|-------------------|
| Very High | ≥ 0.800 | US, UK, Germany, Japan, Australia |
| High | 0.700-0.799 | China, Brazil, Mexico, Thailand, Turkey |
| Medium | 0.550-0.699 | India, Indonesia, South Africa, Vietnam |
| Low | < 0.550 | Nigeria, Ethiopia, Bangladesh, Pakistan |

### Research Output Data
- **Source**: Author-derived from OpenAlex queries by country
- **Period**: All years returned by OpenAlex for the specified query (queried January 23, 2026)
- **Metric**: Country-level publication attributions (`group_by=authorships.countries`) for the Layer 4 query (multi-country papers can contribute to multiple countries; see `scripts/04_layer4_stratification.py`)

### MOOC Enrollment Data
- **Source**: Coursera Global Skills Report 2025
- **URL**: https://www.coursera.org/skills-reports/global
- **Metrics**: YoY growth by skill category and region

### Digital Infrastructure Data
- **Source**: CSIS (2025) "From Divide to Delivery"
- **URL**: https://www.csis.org/analysis/divide-delivery-how-ai-can-serve-global-south
- **Metrics**: Data center capacity, internet penetration by region

---

## Data Processing Notes

### API Data Collection
All time series data were obtained directly from public APIs (Google Trends via pytrends, OpenAlex) during queries conducted January 23, 2026. Raw API outputs are stored in `data/raw/` directories.

### Community Notes Estimates
Layer 3 no longer relies on MAU assumptions or timeline-derived monthly estimates. It computes a real monthly series directly from note timestamps in the Zenodo export `notes_with_lang.csv` (10.5281/zenodo.16761304).

### Aggregation
HDI-research correlations use country-level aggregation of publication counts. Individual publication metadata is not stored to reduce repository size; counts are reproducible via the provided OpenAlex queries.

---

## Citation Requirements

When using these data sources, please cite:

1. **Google Trends**: Google LLC. (2026). Google Trends. https://trends.google.com
2. **OpenAlex**: Priem, J., Piwowar, H., & Orr, R. (2022). OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts. arXiv:2205.01833
3. **Community Notes**: Twitter/X. (2025). Community Notes Guide. https://communitynotes.x.com
4. **UNDP HDR**: United Nations Development Programme. (2024). Human Development Report 2023/24 (HDI time series data). https://hdr.undp.org
5. **Coursera**: Coursera. (2025). Global Skills Report 2025. https://www.coursera.org/skills-reports/global

---

*Last updated: January 2026*
