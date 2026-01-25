# The Augmentation Divide

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.XXXXXXX-blue)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**In Sub-Saharan Africa, people are learning to use generative AI at 22 times the rate they are learning to evaluate it.**

Replication materials for:

> Smárason, M. S. (2026). The Augmentation Divide: Cognitive Debt Stratification in the Generative AI Era. *SSRN Preprint*.

## The Core Finding

We document a stark stratification in global responses to generative AI:

- **The 22:1 Ratio**: Sub-Saharan Africa's CT:GenAI enrollment ratio of 0.04 means people are learning to *use* AI at 22 times the rate they are learning to *evaluate* it.
- **The Counter-Example**: Latin America shows balanced development is possible (CT:GenAI = 0.46, or 2.2:1), with critical thinking enrollment growing +194% YoY.
- **The 11.8× Research Gap**: Very-high HDI countries produce 11.8× more research on critical thinking and AI than low-HDI countries. The top 5 countries generate 45% of all output.

Regions without institutional investment in critical thinking are becoming consumer colonies for AI—importing tools without importing the frameworks to question them.

## Repository Structure

```
augmentation-divide/
├── README.md                   # This file
├── LICENSE                     # MIT License
├── requirements.txt            # Python dependencies
├── CITATION.cff               # Citation metadata
│
├── data/
│   ├── raw/                   # Raw API data files
│   │   ├── HDR23-24_Composite_indices_complete_time_series.csv
│   │   ├── openalex_ct_ai_authorships_countries_2026-01-23.json
│   │   ├── openalex_total_ai_by_year_2026-01-23.json
│   │   └── README.md
│   └── processed/             # Analysis outputs
│       ├── real_bibliometrics.csv
│       ├── real_hdi_stratification.csv
│       └── [supplementary data files]
│
├── scripts/
│   ├── 02_layer2_bibliometrics.py      # Primary: OpenAlex analysis
│   ├── 04_layer4_stratification.py     # Primary: HDI stratification
│   ├── 08_augmentation_divide_visual.py # Regional charts
│   └── [supplementary analysis scripts]
│
├── figures/
│   ├── augmentation_divide_regional.png # Main figure: regional stratification
│   ├── hdi_stratification_chart.png     # HDI tier research output
│   └── [additional figures]
│
└── docs/
    ├── AI_RESEARCH_METHODOLOGY.md  # Meta-methodology for AI-assisted research
    ├── methodology.md
    ├── data_sources.md
    └── cognitive_debt_framework.md
```

## Key Findings

### Primary Evidence: Stratification

| Metric | Finding | Implication |
|--------|---------|-------------|
| **Skills Gap (Worst)** | Sub-Saharan Africa CT:GenAI = 0.04 (22:1) | Dependency formation in real time |
| **Skills Gap (Best)** | Latin America CT:GenAI = 0.46 (2.2:1) | Balanced development is possible |
| **Research Gap** | 11.8× (Very High vs Low HDI) | Discourse shaped by wealthy nations |
| **Concentration** | Top 5 countries = 45% of output | Knowledge production is localized |

### HDI Stratification (OpenAlex + UNDP HDI 2022)

| HDI Category | Countries | Total Attributions | Ratio to Very High |
|--------------|-----------|------------|-------------------|
| Very High | 69 | 1,409 | 1.00× |
| High | 49 | 831 | 0.59× |
| Medium | 42 | 214 | 0.15× |
| Low | 33 | 119 | **0.08×** |

### Regional MOOC Enrollment (Coursera Global Skills Report 2025)

| Region | CT Growth | GenAI Growth | CT:GenAI Ratio |
|--------|-----------|--------------|----------------|
| **Latin America** | +194% | +425% | **0.46** (best) |
| Middle East & North Africa | +19% | +128% | 0.15 |
| Europe | +14% | +116% | 0.12 |
| North America | +15% | +135% | 0.11 |
| Asia Pacific | +12% | +132% | 0.09 |
| **Sub-Saharan Africa** | +6% | +134% | **0.04** (worst) |

### Supplementary Indicators (Confounded)

Google Trends and Community Notes data are included in the repository but demoted to supplementary status due to confounding:

- **Google Trends**: Shows increased search interest, but November 2022 was not uniquely powerful as a breakpoint. Pre-trends exist in 3/4 languages.
- **Community Notes**: 43-fold participation growth overlaps with platform's global expansion in late 2022. Cannot separate ChatGPT effect from platform scaling.

## Theoretical Framework

### Cognitive Debt

Algorithmic dependency that compounds over time. Each act of uncritical AI use erodes capacity for the next act of critical evaluation.

- **Thought**: Declining autonomous reasoning capacity
- **Feeling**: Eroded epistemic self-worth
- **Action**: Reduced intervention capability
- **Compounding**: Self-reinforcing capacity loss

### Augmentation Divide

Systematic stratification between populations building cognitive infrastructure (Global North) and those accumulating Cognitive Debt (Global South).

## Data Sources

| Layer | Source | Access |
|-------|--------|--------|
| Primary | OpenAlex API | [openalex.org](https://openalex.org) |
| Primary | Coursera Global Skills Report | [coursera.org](https://www.coursera.org/skills-reports/global) |
| Primary | UNDP HDR 2023/24 | [hdr.undp.org](https://hdr.undp.org) |
| Supplementary | Google Trends API | [trends.google.com](https://trends.google.com) |
| Supplementary | Community Notes (Zenodo) | [10.5281/zenodo.16761304](https://doi.org/10.5281/zenodo.16761304) |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/magnussmari/augmentation-divide.git
cd augmentation-divide

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run primary analyses
python scripts/02_layer2_bibliometrics.py
python scripts/04_layer4_stratification.py
python scripts/08_augmentation_divide_visual.py
```

## Citation

```bibtex
@article{smarason2026augmentation,
  title={The Augmentation Divide: Cognitive Debt Stratification in the Generative AI Era},
  author={Smárason, Magnús Smári},
  journal={SSRN Preprint},
  year={2026},
  doi={10.2139/ssrn.XXXXXXX}
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contact

- **Author**: Magnús Smári Smárason
- **Email**: magnus@smarason.is
- **Website**: [smarason.is](https://www.smarason.is)
- **Location**: Iceland

---

*Last updated: January 2026*
