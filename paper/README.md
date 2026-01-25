# Paper: The Augmentation Divide

**Title**: The Augmentation Divide: Cognitive Debt Stratification in the Generative AI Era  
**Author**: Magnús Smári Smárason  
**Version**: 2026-01-25 (post peer-review revisions)

## Files

| File | Description |
|------|-------------|
| `main.tex` | LaTeX source |
| `references.bib` | BibTeX bibliography |
| `main.pdf` | Compiled paper (15 pages) |
| `augmentation_divide_regional.png` | Figure 1: Regional enrollment imbalance |
| `augmentation_divide_2026-01-25.pdf` | Versioned PDF copy |

## Compilation

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Requires: TeX Live 2024+ with `natbib`, `booktabs`, `graphicx`, `hyperref`

## Submission Targets

- **SSRN**: Preprint (see `../SSRN_SUBMISSION_GUIDE.md`)
- **arXiv**: cs.CY or cs.HC (see `../ARXIV_SUBMISSION_GUIDE.md`)
- **Journal**: Under consideration

## Version History

| Date | Changes |
|------|---------|
| 2026-01-25 | Implemented all peer review revisions (see `docs/cursor_peer_review_250126.md`) |
| 2026-01-24 | Corrected MOOC data from Coursera PDF verification |
| 2026-01-23 | Initial draft with OpenAlex + UNDP data |

## Key Statistics (Verified)

| Claim | Value | Source |
|-------|-------|--------|
| Sub-Saharan Africa CT:GenAI ratio | 0.04 (22:1) | Coursera PDF p.63 |
| Latin America CT:GenAI ratio | 0.46 (2.2:1) | Coursera PDF p.41 |
| HDI research gap (totals) | 11.8× | OpenAlex + UNDP |
| HDI research gap (per-country) | 5.7× | OpenAlex + UNDP |
| Top 5 country share | 45% | OpenAlex |

## Data Availability

All data and replication materials available at:
https://github.com/magnussmari/augmentation-divide
