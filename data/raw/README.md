# Raw Data Sources

## Layer 1: Google Trends

- **Source**: Google Trends API via pytrends 4.9.2
- **Query date**: January 23, 2026
- **Timeframe**: 2016-01-01 to 2025-12-31
- **Terms**:
  - `critical thinking` (English)
  - `kritisches Denken` (German)
  - `pensée critique` (French)
  - `pensamiento crítico` (Spanish)
- **Files**:
  - `trends_english.csv`
  - `trends_german.csv`
  - `trends_french.csv`
  - `trends_spanish.csv`

### Replication Code

```python
from pytrends.request import TrendReq
import time

pytrends = TrendReq(hl='en-US', tz=0)

queries = {
    'english': 'critical thinking',
    'german': 'kritisches Denken',
    'french': 'pensée critique',
    'spanish': 'pensamiento crítico'
}

for lang, term in queries.items():
    pytrends.build_payload([term], cat=0, timeframe='2016-01-01 2025-12-31')
    df = pytrends.interest_over_time()
    df.to_csv(f'trends_{lang}.csv')
    time.sleep(60)  # Rate limit compliance
```

## Layer 2: OpenAlex

- **Source**: OpenAlex API (https://api.openalex.org)
- **Query date**: January 23, 2026
- **Endpoint**: `/works`
- **Filters**:
  - CT+AI: `title_and_abstract.search:critical thinking AND (artificial intelligence OR generative AI OR ChatGPT)`
  - GenAI+Ed: `title_and_abstract.search:(generative AI OR ChatGPT OR large language model) AND education`
- **Denominator (normalization)**:
  - Total AI output by year: OpenAlex concept id `C154945302` (Artificial Intelligence), grouped by `publication_year`
- **Cached raw output**:
  - `openalex_total_ai_by_year_2026-01-23.json`
- **Grouping**: `publication_year`
- **Output**: See `../processed/real_bibliometrics.csv`

### Replication Code

```python
import requests

base_url = "https://api.openalex.org/works"

# Query 1: CT+AI by year
params = {
    'filter': 'title_and_abstract.search:critical thinking AND (artificial intelligence OR generative AI OR ChatGPT)',
    'group_by': 'publication_year',
    'mailto': 'your-email@example.com'
}
response = requests.get(base_url, params=params)
data = response.json()

# Query 2: GenAI+Education by year
params2 = {
    'filter': 'title_and_abstract.search:(generative AI OR ChatGPT OR large language model) AND education',
    'group_by': 'publication_year',
    'mailto': 'your-email@example.com'
}
response2 = requests.get(base_url, params=params2)
```

## Layer 3: Community Notes

- **Primary source**: Mohammadi, S., Chinichian, N., & González-Bailón, S. (2025). From Birdwatch to Community Notes, from Twitter to X: Four years of community-based content moderation. arXiv:2510.09585
- **Dataset used in this replication**: Zenodo record `10.5281/zenodo.16761304`
  - File: `community_notes_zenodo/notes_with_lang.csv` (large; note-level export with language tags)
  - Coverage: Jan 23, 2021 – Jan 23, 2025
- **Metrics computed from note-level timestamps (no platform MAU assumptions)**:
  - Monthly notes created
  - Monthly active note writers (unique authors)
  - Notes per active writer (participation intensity)
  - Time-to-first-note (hours) via tweet snowflake decoding (responsiveness proxy)
  - Global language distribution (note share + unique authors by language code)
- **Quality context (reported by Mohammadi et al., 2025; not recomputed here)**:
  - Helpful (four-year total): 8.3%
  - Needs More Ratings (four-year total): 87.7%
- **Outputs**:
  - `../processed/real_community_notes.csv`
  - `../processed/real_community_notes_monthly.csv`
  - `../processed/real_community_notes_language.csv`

## Layer 4: HDI Stratification

- **Sources**:
  - OpenAlex API (country-level publication counts via `authorships.countries` grouping)
  - UNDP HDR23-24 composite indices time series (HDI 2022 values + `hdicode` tiers)
- **Query date**: January 23, 2026
- **Filter**: `title_and_abstract.search:critical thinking AND (artificial intelligence OR generative AI OR machine learning)`
- **Output**: See `../processed/real_hdi_stratification.csv`
- **UNDP file stored in-repo**: `HDR23-24_Composite_indices_complete_time_series.csv` (HDI values and tiers; uses `hdi_2022` and `hdicode`)
- **OpenAlex raw output stored in-repo**: `openalex_ct_ai_authorships_countries_2026-01-23.json` (group-by response)

### Replication Code

```python
import requests

params = {
    'filter': 'title_and_abstract.search:critical thinking AND (artificial intelligence OR generative AI OR machine learning)',
    'group_by': 'authorships.countries',
    'mailto': 'your-email@example.com'
}
response = requests.get("https://api.openalex.org/works", params=params)
country_data = response.json()
```

---

## Data Integrity

All raw data files in this directory are unmodified API outputs from queries conducted January 23, 2026. Processing steps are documented in `../processed/` and scripts in `../../scripts/`.

---

*Last updated: January 23, 2026*
