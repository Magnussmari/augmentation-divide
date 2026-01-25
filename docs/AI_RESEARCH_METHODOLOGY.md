# AI-Assisted Research Methodology

A framework for conducting rigorous, reproducible research with generative AI assistance.

**Author**: Magnús Smári Smárason  
**Version**: 1.0 (2026-01-25)  
**Context**: Developed during the creation of "The Augmentation Divide: Cognitive Debt Stratification in the Generative AI Era"

---

## Core Principle: Trust but Verify

AI assistants are powerful research accelerators, but they can:
- Hallucinate citations, statistics, and facts
- Misremember or conflate sources
- Generate plausible-sounding but incorrect data
- Introduce systematic biases

**The researcher remains the source of truth.** AI is a tool, not an authority.

---

## Phase 1: Data Collection and Provenance

### 1.1 Primary Source Doctrine

Every quantitative claim must trace to a primary source document that you have personally verified.

**Anti-pattern**: Trusting AI-generated statistics  
**Correct pattern**: Download the source PDF, extract data manually, document page numbers

**Example from this project**:
```
WRONG: "Latin America shows +25% critical thinking growth" (AI-generated figure)
RIGHT: "Latin America shows +194% critical thinking growth" (PDF page 41, manually verified)
```

This single error—accepting an AI-generated figure without verification—would have invalidated the paper's central claim (17:1 ratio → 2.2:1 ratio).

### 1.2 Source Archiving Protocol

For every data source:

1. **Download** the original file (PDF, CSV, JSON)
2. **Archive** it in `data/raw/` with a descriptive filename including date
3. **Document** the URL, access date, and extraction method in `DATA_PROVENANCE.md`
4. **Extract** data programmatically where possible (not manually)
5. **Version control** everything

**Folder structure**:
```
data/
├── raw/                          # Immutable original sources
│   ├── sources/                  # Cited papers (PDFs)
│   │   ├── lee2025_genai_critical_thinking.pdf
│   │   ├── mohammadi2025_community_notes.pdf
│   │   └── SOURCES.md
│   ├── Global_Skills_Report_2025.pdf
│   ├── HDR23-24_Composite_indices_complete_time_series.csv
│   └── README.md
└── processed/                    # Analysis outputs (reproducible from raw)
    ├── real_mooc_regional.csv
    └── real_hdi_stratification.csv
```

### 1.3 Open Access Preference

For 100% reproducibility, prefer sources in this order:

1. **Open Access PDFs** (arXiv, author websites, institutional repositories)
2. **Government/NGO reports** (UNDP, UNESCO, World Bank)
3. **API data with persistent identifiers** (OpenAlex, Crossref)
4. **DOI-registered paywalled sources** (verifiable, if not directly accessible)
5. **Books** (cite specific editions; archive relevant excerpts under fair use)

---

## Phase 2: AI-Assisted Analysis

### 2.1 Code Generation

AI can generate analysis code, but:

1. **Review every function** before execution
2. **Validate outputs** against known values
3. **Test edge cases** manually
4. **Document assumptions** in comments

**Example workflow**:
```python
def load_real_mooc_data() -> pd.DataFrame:
    """
    Load REAL regional MOOC enrollment data from Coursera Global Skills Report 2025.
    
    Source: Coursera Global Skills Report 2025 (PDF archived in data/raw/)
    URL: https://www.coursera.org/skills-reports/global
    Data extracted: January 2026
    
    Page references:
    - Page 41: Latin America - GenAI +425%, CT +194%
    - Page 57: North America - GenAI +135%, CT +15%
    [...]
    """
```

### 2.2 Calculation Verification

For every calculated metric:

1. **Show your work** in code comments
2. **Sanity check** results (is a 17:1 ratio plausible?)
3. **Cross-reference** with source where possible
4. **Log intermediate values** for debugging

### 2.3 The "Adversarial Prompt" Pattern

After completing analysis, ask the AI to critique it:

```
"Act as a hostile peer reviewer. Find every weakness in this methodology,
every questionable assumption, and every potential error in the data."
```

This pattern caught the 17:1 → 2.2:1 error in this project.

---

## Phase 3: Writing and Claims

### 3.1 Claim-Source Mapping

Every empirical claim should map directly to a source:

| Claim | Source | Verification |
|-------|--------|--------------|
| "22:1 imbalance in Sub-Saharan Africa" | Coursera PDF p.63 | 6/134 = 0.045 ✓ |
| "11.8× research gap" | OpenAlex + UNDP calculation | Script verified ✓ |

### 3.2 Framing Transparency

When data can be interpreted multiple ways, acknowledge it:

**Example from this project**:
- "11.8× gap" = total publications (Very High HDI / Low HDI)
- "5.67× gap" = per-country average
- Both are mathematically correct; the paper uses totals with explanation

### 3.3 AI Disclosure

Disclose AI assistance explicitly:

```latex
\paragraph{AI Assistance Disclosure}
During preparation of this work, the author used Claude (Anthropic, Opus 4.5) for:
(1) Python code development, (2) LaTeX formatting, and (3) adversarial review.
After using these tools, the author verified all outputs and edited as needed.
All analyses, interpretations, and conclusions are the author's own.
```

---

## Phase 4: Reproducibility Checklist

Before submission:

### Data
- [ ] All raw data files archived in `data/raw/`
- [ ] Source PDFs downloaded and archived
- [ ] `DATA_PROVENANCE.md` documents every file with URL, date, method
- [ ] `SOURCES.md` documents all cited papers with access status

### Code
- [ ] All analysis scripts in `scripts/` directory
- [ ] `requirements.txt` with pinned versions
- [ ] `run_all.py` or equivalent to reproduce analysis
- [ ] Comments document data sources and assumptions

### Verification
- [ ] Every quantitative claim manually verified against source
- [ ] Key calculations spot-checked with calculator
- [ ] Adversarial review completed
- [ ] At least one external fact-check

### Repository
- [ ] GitHub repository public and accessible
- [ ] README includes reproduction instructions
- [ ] License file (MIT, CC-BY, etc.)
- [ ] CITATION.cff for proper attribution

---

## Anti-Patterns to Avoid

### 1. "The AI Said So"
Never accept AI-generated statistics without verification. AI can hallucinate convincing but false data.

### 2. Hardcoded Mystery Numbers
```python
# BAD
ct_growth = [28, 28, 35, 25, 22]  # Where did these come from?

# GOOD
ct_growth = [14, 15, 12, 194, 19, 6]  # Coursera 2025, pages 21/33/41/49/57/63
```

### 3. Orphan Claims
Claims without traceable sources. If you can't point to the page number, don't make the claim.

### 4. Verification Theater
Pretending to verify without actually reading sources. The PDF must be opened. The page must be found.

### 5. Assuming API Data is Correct
APIs can have bugs, outdated data, or unexpected filtering. Validate samples against known values.

---

## The Meta-Irony

This paper argues that uncritical AI use creates "Cognitive Debt." During its creation, accepting an AI-generated figure without verification nearly invalidated the central empirical claim.

**The lesson**: The framework we propose is not academic abstraction. It describes a real and present danger—one we almost fell victim to ourselves.

The fact-check that caught the error—conducted by an AI at our request—demonstrates the proper use pattern: AI as adversarial assistant, human as final authority.

---

## Tool Recommendations

### For Source Management
- Zotero (open source) for reference management
- WebArchive/archive.org for URL preservation
- Git LFS for large PDF storage

### For Data Verification
- `pdftotext` for extracting PDF content
- OpenAlex API for bibliometric verification
- Direct source comparison (side-by-side with claims)

### For AI-Assisted Research
- Claude, GPT-4, or equivalent for code generation
- Same tools for adversarial review ("find errors in this")
- Always verify outputs independently

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-25 | Initial release after Latin America data correction |

---

*"The capacity for critical evaluation is what distinguishes humans from AI. The irony of needing to exercise that capacity when using AI to study that capacity is not lost on us."*
