#!/usr/bin/env python3
"""
readability_analysis.py

Comprehensive readability analysis of academic papers from LaTeX source.
Computes Flesch-Kincaid metrics with detailed section-by-section breakdown,
complex word analysis, and actionable insights.

Usage:
    python readability_analysis.py [path_to_tex_file]
"""

import re
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone


def count_syllables(word: str) -> int:
    """
    Estimate syllable count for a word using a heuristic approach.
    """
    word = word.lower().strip()
    if len(word) <= 2:
        return 1

    # Remove trailing silent-e (but not -le, -les)
    if word.endswith('e') and not word.endswith(('le', 'les', 'ee', 'ie')):
        word = word[:-1]

    # Count vowel groups
    vowels = 'aeiouy'
    count = 0
    prev_vowel = False

    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    # Adjustments for common patterns
    if word.endswith('ed') and len(word) > 3:
        if word[-3] not in 'dt':
            count = max(1, count - 1)

    if word.endswith('es') and len(word) > 3:
        if word[-3] in 'sxz' or word[-4:-2] in ('ch', 'sh'):
            pass
        else:
            count = max(1, count - 1)

    return max(1, count)


def strip_latex(text: str) -> str:
    """Remove LaTeX commands and environments to extract plain text."""
    # Remove comments
    text = re.sub(r'%.*$', '', text, flags=re.MULTILINE)

    # Remove document structure commands
    text = re.sub(r'\\documentclass\[.*?\]\{.*?\}', '', text)
    text = re.sub(r'\\usepackage\[.*?\]\{.*?\}', '', text)
    text = re.sub(r'\\usepackage\{.*?\}', '', text)

    # Remove begin/end environments but keep content (except for unwanted ones)
    unwanted_envs = ['figure', 'table', 'tabular', 'equation', 'align', 'lstlisting', 'verbatim']
    for env in unwanted_envs:
        text = re.sub(rf'\\begin\{{{env}\}}.*?\\end\{{{env}\}}', '', text, flags=re.DOTALL)

    text = re.sub(r'\\begin\{.*?\}', '', text)
    text = re.sub(r'\\end\{.*?\}', '', text)

    # Remove specific commands but keep their content
    text = re.sub(r'\\(?:textbf|textit|emph|underline|texttt)\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\(?:section|subsection|subsubsection|paragraph)\*?\{([^}]*)\}', r'\1. ', text)
    text = re.sub(r'\\title\{([^}]*)\}', r'\1. ', text)
    text = re.sub(r'\\author\{([^}]*)\}', '', text)

    # Remove citations and references
    text = re.sub(r'\\cite[pt]?\{[^}]*\}', '', text)
    text = re.sub(r'\\ref\{[^}]*\}', '', text)
    text = re.sub(r'\\label\{[^}]*\}', '', text)
    text = re.sub(r'\\url\{[^}]*\}', '', text)
    text = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\footnote\{[^}]*\}', '', text)

    # Remove math
    text = re.sub(r'\$[^$]+\$', ' NUMBER ', text)
    text = re.sub(r'\\\[.*?\\\]', ' EQUATION ', text, flags=re.DOTALL)
    text = re.sub(r'\\\(.*?\\\)', ' NUMBER ', text, flags=re.DOTALL)

    # Remove remaining LaTeX commands
    text = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?', '', text)
    text = re.sub(r'\\[^a-zA-Z]', '', text)

    # Clean up
    text = re.sub(r'[{}]', '', text)
    text = re.sub(r'~', ' ', text)
    text = re.sub(r'--', '—', text)
    text = re.sub(r"``|''", '"', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def extract_sections(tex_content: str) -> dict:
    """Extract text by section from LaTeX content."""
    sections = {}

    # Find all sections
    pattern = r'\\section\*?\{([^}]+)\}'
    matches = list(re.finditer(pattern, tex_content))

    if not matches:
        sections['Full Document'] = tex_content
        return sections

    # Extract abstract
    abstract_match = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', tex_content, re.DOTALL)
    if abstract_match:
        sections['Abstract'] = abstract_match.group(1)

    # Extract each section
    for i, match in enumerate(matches):
        section_name = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(tex_content)
        sections[section_name] = tex_content[start:end]

    return sections


def get_sentences(text: str) -> list:
    """Extract sentences from text."""
    clean_text = strip_latex(text)
    sentences = re.split(r'[.!?]+', clean_text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def get_words(text: str) -> list:
    """Extract words from text."""
    clean_text = strip_latex(text)
    words = re.findall(r'\b[a-zA-Z]+\b', clean_text)
    return [w for w in words if len(w) > 1]


def compute_metrics(text: str) -> dict:
    """Compute comprehensive readability metrics."""
    sentences = get_sentences(text)
    words = get_words(text)

    if not words or not sentences:
        return None

    # Syllable analysis
    word_syllables = [(w, count_syllables(w)) for w in words]
    total_syllables = sum(s for _, s in word_syllables)

    # Complex words (3+ syllables)
    complex_words = [(w, s) for w, s in word_syllables if s >= 3]
    complex_word_count = len(complex_words)

    # Basic counts
    total_words = len(words)
    total_sentences = len(sentences)
    avg_sentence_length = total_words / total_sentences
    avg_syllables_per_word = total_syllables / total_words

    # Sentence length analysis
    sentence_lengths = [len(re.findall(r'\b[a-zA-Z]+\b', s)) for s in sentences]
    long_sentences = [(s, l) for s, l in zip(sentences, sentence_lengths) if l > 30]

    # Flesch Reading Ease
    fre = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)

    # Flesch-Kincaid Grade Level
    fkgl = (0.39 * avg_sentence_length) + (11.8 * avg_syllables_per_word) - 15.59

    # Gunning Fog Index
    fog = 0.4 * (avg_sentence_length + 100 * (complex_word_count / total_words))

    # SMOG Index (simplified)
    smog = 1.0430 * ((complex_word_count * (30 / total_sentences)) ** 0.5) + 3.1291 if total_sentences >= 30 else None

    # Coleman-Liau Index
    L = (total_words / total_sentences) * 100 / total_words * 100  # avg letters per 100 words (approx)
    S = (total_sentences / total_words) * 100  # avg sentences per 100 words
    # Simplified: use character count
    total_chars = sum(len(w) for w in words)
    L = (total_chars / total_words) * 100
    cli = 0.0588 * L - 0.296 * S - 15.8

    return {
        'words': total_words,
        'sentences': total_sentences,
        'syllables': total_syllables,
        'complex_words': complex_word_count,
        'complex_word_pct': (complex_word_count / total_words) * 100,
        'avg_sentence_length': avg_sentence_length,
        'avg_syllables_per_word': avg_syllables_per_word,
        'avg_word_length': total_chars / total_words,
        'flesch_reading_ease': fre,
        'flesch_kincaid_grade': fkgl,
        'gunning_fog': fog,
        'smog_index': smog,
        'coleman_liau': cli,
        'long_sentences': long_sentences[:5],  # Top 5 longest
        'complex_word_list': complex_words,
        'sentence_lengths': sentence_lengths
    }


def interpret_fre(score: float) -> tuple:
    """Interpret Flesch Reading Ease score with color indicator."""
    if score >= 90:
        return ("Very Easy", "5th grade", "🟢")
    elif score >= 80:
        return ("Easy", "6th grade", "🟢")
    elif score >= 70:
        return ("Fairly Easy", "7th grade", "🟢")
    elif score >= 60:
        return ("Standard", "8th-9th grade", "🟡")
    elif score >= 50:
        return ("Fairly Difficult", "10th-12th grade", "🟡")
    elif score >= 30:
        return ("Difficult", "College", "🟠")
    else:
        return ("Very Difficult", "Graduate", "🔴")


def interpret_fkgl(grade: float) -> tuple:
    """Interpret Flesch-Kincaid Grade Level."""
    if grade < 8:
        return ("Middle school", "🟢")
    elif grade < 12:
        return ("High school", "🟡")
    elif grade < 14:
        return ("College freshman", "🟡")
    elif grade < 16:
        return ("College senior", "🟠")
    elif grade < 18:
        return ("Graduate", "🟠")
    else:
        return ("Post-graduate", "🔴")


def make_bar(value: float, max_val: float, width: int = 30, fill: str = "█", empty: str = "░") -> str:
    """Create a text-based progress bar."""
    filled = int((value / max_val) * width)
    return fill * filled + empty * (width - filled)


def print_header(text: str, char: str = "=", width: int = 70):
    """Print a formatted header."""
    print(f"\n{char * width}")
    print(f"  {text}")
    print(char * width)


def print_subheader(text: str, char: str = "-", width: int = 70):
    """Print a formatted subheader."""
    print(f"\n{char * width}")
    print(f"  {text}")
    print(char * width)


def main():
    # Default to main.tex in current directory
    if len(sys.argv) > 1:
        tex_path = Path(sys.argv[1])
    else:
        tex_path = Path(__file__).parent / "main.tex"

    if not tex_path.exists():
        print(f"Error: File not found: {tex_path}")
        sys.exit(1)

    # Read the LaTeX file
    tex_content = tex_path.read_text(encoding='utf-8')

    # Extract body content
    body_match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', tex_content, re.DOTALL)
    body_content = body_match.group(1) if body_match else tex_content

    # Compute overall metrics
    metrics = compute_metrics(body_content)
    if not metrics:
        print("Error: Could not extract text from document")
        sys.exit(1)

    # =========================================================================
    # HEADER
    # =========================================================================
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  READABILITY ANALYSIS REPORT".center(68) + "█")
    print("█" + f"  {tex_path.name}".center(68) + "█")
    print("█" + f"  {timestamp}".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    # =========================================================================
    # EXECUTIVE SUMMARY
    # =========================================================================
    print_header("EXECUTIVE SUMMARY")

    fre_label, fre_level, fre_icon = interpret_fre(metrics['flesch_reading_ease'])
    fkgl_label, fkgl_icon = interpret_fkgl(metrics['flesch_kincaid_grade'])

    print(f"""
  Document Statistics:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Total Words:        {metrics['words']:>6,}                                   │
  │  Total Sentences:    {metrics['sentences']:>6,}                                   │
  │  Total Syllables:    {metrics['syllables']:>6,}                                   │
  │  Complex Words (3+): {metrics['complex_words']:>6,}  ({metrics['complex_word_pct']:.1f}%)                        │
  └─────────────────────────────────────────────────────────────────┘

  Primary Readability Scores:
  ┌─────────────────────────────────────────────────────────────────┐
  │                                                                 │
  │  {fre_icon} Flesch Reading Ease:     {metrics['flesch_reading_ease']:>5.1f}                            │
  │     {fre_label} ({fre_level}){' ' * (40 - len(fre_label) - len(fre_level))}│
  │                                                                 │
  │  {fkgl_icon} Flesch-Kincaid Grade:   {metrics['flesch_kincaid_grade']:>5.1f}                            │
  │     {fkgl_label}{' ' * (49 - len(fkgl_label))}│
  │                                                                 │
  └─────────────────────────────────────────────────────────────────┘
""")

    # =========================================================================
    # DETAILED METRICS
    # =========================================================================
    print_header("DETAILED READABILITY METRICS")

    print(f"""
  ┌─────────────────────────────────────────────────────────────────┐
  │  METRIC                          SCORE    INTERPRETATION        │
  ├─────────────────────────────────────────────────────────────────┤
  │  Flesch Reading Ease             {metrics['flesch_reading_ease']:>5.1f}    {fre_label:<20} │
  │  Flesch-Kincaid Grade Level      {metrics['flesch_kincaid_grade']:>5.1f}    Grade {metrics['flesch_kincaid_grade']:.0f} reading level  │
  │  Gunning Fog Index               {metrics['gunning_fog']:>5.1f}    {metrics['gunning_fog']:.0f} years of education   │""")

    if metrics['smog_index']:
        print(f"  │  SMOG Index                      {metrics['smog_index']:>5.1f}    Grade {metrics['smog_index']:.0f} reading level  │")
    else:
        print(f"  │  SMOG Index                        N/A    (needs 30+ sentences)  │")

    print(f"""  │  Coleman-Liau Index              {metrics['coleman_liau']:>5.1f}    Grade {metrics['coleman_liau']:.0f} reading level  │
  └─────────────────────────────────────────────────────────────────┘
""")

    # =========================================================================
    # SENTENCE ANALYSIS
    # =========================================================================
    print_header("SENTENCE ANALYSIS")

    lengths = metrics['sentence_lengths']
    avg_len = metrics['avg_sentence_length']
    max_len = max(lengths) if lengths else 0
    min_len = min(lengths) if lengths else 0

    # Distribution buckets
    short = sum(1 for l in lengths if l <= 15)
    medium = sum(1 for l in lengths if 15 < l <= 25)
    long = sum(1 for l in lengths if 25 < l <= 35)
    very_long = sum(1 for l in lengths if l > 35)

    total = len(lengths)

    print(f"""
  Average Sentence Length: {avg_len:.1f} words
  Range: {min_len} - {max_len} words

  Sentence Length Distribution:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Short (≤15 words):      {short:>3} ({100*short/total:>4.1f}%)  {make_bar(short, total, 25)} │
  │  Medium (16-25 words):   {medium:>3} ({100*medium/total:>4.1f}%)  {make_bar(medium, total, 25)} │
  │  Long (26-35 words):     {long:>3} ({100*long/total:>4.1f}%)  {make_bar(long, total, 25)} │
  │  Very Long (>35 words):  {very_long:>3} ({100*very_long/total:>4.1f}%)  {make_bar(very_long, total, 25)} │
  └─────────────────────────────────────────────────────────────────┘
""")

    # Longest sentences
    if metrics['long_sentences']:
        print_subheader("LONGEST SENTENCES (may need simplification)")
        for i, (sent, length) in enumerate(metrics['long_sentences'][:3], 1):
            truncated = sent[:100] + "..." if len(sent) > 100 else sent
            print(f"\n  {i}. [{length} words]")
            print(f"     \"{truncated}\"")

    # =========================================================================
    # WORD COMPLEXITY
    # =========================================================================
    print_header("WORD COMPLEXITY ANALYSIS")

    print(f"""
  Average Word Length:       {metrics['avg_word_length']:.2f} characters
  Average Syllables/Word:    {metrics['avg_syllables_per_word']:.2f}
  Complex Words (3+ syll):   {metrics['complex_words']:,} ({metrics['complex_word_pct']:.1f}%)
""")

    # Most frequent complex words
    complex_counter = Counter(w.lower() for w, s in metrics['complex_word_list'])
    top_complex = complex_counter.most_common(15)

    if top_complex:
        print("  Most Frequent Complex Words:")
        print("  ┌────────────────────────────────────────────┐")
        for word, count in top_complex:
            syllables = count_syllables(word)
            bar = "●" * min(count, 20)
            print(f"  │  {word:<20} ({syllables} syll) {count:>3}× {bar:<20} │"[:47] + "│")
        print("  └────────────────────────────────────────────┘")

    # =========================================================================
    # SECTION-BY-SECTION
    # =========================================================================
    print_header("SECTION-BY-SECTION ANALYSIS")

    sections = extract_sections(body_content)
    section_data = []

    for section_name, section_content in sections.items():
        sec_metrics = compute_metrics(section_content)
        if sec_metrics and sec_metrics['words'] > 30:
            section_data.append((section_name, sec_metrics))

    # Sort by grade level
    section_data.sort(key=lambda x: x[1]['flesch_kincaid_grade'], reverse=True)

    print(f"""
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  SECTION                           WORDS    FRE   GRADE   COMPLEXITY     │
  ├──────────────────────────────────────────────────────────────────────────┤""")

    for section_name, sec_metrics in section_data:
        name = section_name[:30] + ".." if len(section_name) > 32 else section_name
        grade = sec_metrics['flesch_kincaid_grade']

        # Visual grade indicator
        if grade < 12:
            indicator = "🟢"
        elif grade < 15:
            indicator = "🟡"
        elif grade < 17:
            indicator = "🟠"
        else:
            indicator = "🔴"

        grade_bar = make_bar(min(grade, 20), 20, 10, "▓", "░")

        print(f"  │  {name:<32} {sec_metrics['words']:>5}  {sec_metrics['flesch_reading_ease']:>5.1f}  {grade:>5.1f}   {indicator} {grade_bar} │")

    print("  └──────────────────────────────────────────────────────────────────────────┘")

    # =========================================================================
    # COMPARISON & BENCHMARKS
    # =========================================================================
    print_header("BENCHMARKS & COMPARISON")

    grade = metrics['flesch_kincaid_grade']
    fre = metrics['flesch_reading_ease']

    benchmarks = [
        ("Your Paper", grade, fre, "◆"),
        ("Scientific Journals (typical)", 16.0, 25.0, "│"),
        ("Academic Papers (typical)", 14.0, 35.0, "│"),
        ("New York Times", 11.0, 55.0, "│"),
        ("Time Magazine", 10.0, 60.0, "│"),
        ("Reader's Digest", 8.0, 65.0, "│"),
    ]

    print("""
  Grade Level Comparison:
  ┌───────────────────────────────────────────────────────────────────────┐
  │  6    8    10   12   14   16   18   20                                │
  │  │    │    │    │    │    │    │    │                                 │""")

    for name, g, f, marker in benchmarks:
        pos = int((g - 6) * 2.5)  # Scale to fit
        pos = max(0, min(pos, 35))
        line = " " * pos + marker
        if marker == "◆":
            print(f"  │  {line:<35} ◆ {name} (Grade {g:.1f})       │")
        else:
            print(f"  │  {line:<35}   {name:<25} │")

    print("""  │  └────┴────┴────┴────┴────┴────┴────┘                                 │
  │  HS        College     Graduate                                      │
  └───────────────────────────────────────────────────────────────────────┘
""")

    # =========================================================================
    # RECOMMENDATIONS
    # =========================================================================
    print_header("ANALYSIS & RECOMMENDATIONS")

    issues = []
    positives = []

    # Check various metrics
    if metrics['flesch_kincaid_grade'] > 17:
        issues.append("Grade level is very high (>17). Consider simplifying for broader accessibility.")
    elif metrics['flesch_kincaid_grade'] > 15:
        issues.append("Grade level is typical for academic writing but could be more accessible.")

    if metrics['avg_sentence_length'] > 25:
        issues.append(f"Average sentence length ({metrics['avg_sentence_length']:.1f} words) is high. Consider breaking up long sentences.")
    elif metrics['avg_sentence_length'] < 20:
        positives.append(f"Good sentence length average ({metrics['avg_sentence_length']:.1f} words).")

    if metrics['complex_word_pct'] > 25:
        issues.append(f"High percentage of complex words ({metrics['complex_word_pct']:.1f}%). Consider using simpler alternatives where possible.")
    elif metrics['complex_word_pct'] < 20:
        positives.append(f"Reasonable use of complex vocabulary ({metrics['complex_word_pct']:.1f}%).")

    if very_long > total * 0.15:
        issues.append(f"{very_long} sentences ({100*very_long/total:.0f}%) exceed 35 words. These may lose readers.")

    if metrics['flesch_kincaid_grade'] >= 14 and metrics['flesch_kincaid_grade'] <= 17:
        positives.append("Grade level is appropriate for academic/professional audience.")

    if section_data:
        hardest = section_data[0]
        easiest = section_data[-1]
        if hardest[1]['flesch_kincaid_grade'] - easiest[1]['flesch_kincaid_grade'] > 4:
            issues.append(f"Large readability gap between sections ({hardest[0]}: {hardest[1]['flesch_kincaid_grade']:.1f} vs {easiest[0]}: {easiest[1]['flesch_kincaid_grade']:.1f}).")

    print("\n  ✓ STRENGTHS:")
    if positives:
        for p in positives:
            print(f"    • {p}")
    else:
        print("    • Document is complete and analyzable")

    print("\n  ⚠ AREAS FOR IMPROVEMENT:")
    if issues:
        for issue in issues:
            print(f"    • {issue}")
    else:
        print("    • No significant issues detected")

    # =========================================================================
    # SUMMARY BOX
    # =========================================================================
    print_header("FINAL VERDICT")

    if grade < 14:
        verdict = "ACCESSIBLE"
        verdict_icon = "🟢"
        verdict_desc = "More accessible than typical academic writing"
    elif grade < 16:
        verdict = "STANDARD ACADEMIC"
        verdict_icon = "🟡"
        verdict_desc = "Appropriate for academic/professional audience"
    elif grade < 18:
        verdict = "ADVANCED"
        verdict_icon = "🟠"
        verdict_desc = "Suitable for specialized academic audience"
    else:
        verdict = "HIGHLY TECHNICAL"
        verdict_icon = "🔴"
        verdict_desc = "May benefit from simplification"

    print(f"""
  ┌─────────────────────────────────────────────────────────────────┐
  │                                                                 │
  │   {verdict_icon}  {verdict:^20}  {verdict_icon}                              │
  │                                                                 │
  │   {verdict_desc:^57} │
  │                                                                 │
  │   Flesch-Kincaid Grade: {grade:.1f}                                    │
  │   Flesch Reading Ease:  {fre:.1f}                                    │
  │   Target Audience:      Graduate/Professional                   │
  │                                                                 │
  └─────────────────────────────────────────────────────────────────┘
""")

    print("=" * 70)
    print(f"  Analysis complete. Generated: {timestamp}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
