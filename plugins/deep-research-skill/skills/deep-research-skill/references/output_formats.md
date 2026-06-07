# Deep Research Skill — Output Format Specification

> **Version:** 1.0 | **Last Updated:** 2025-01-20 | **Status:** Draft

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Core Output Formats](#2-core-output-formats)
   - 2.1 [Research Report](#21-research-report)
   - 2.2 [Executive Brief](#22-executive-brief)
   - 2.3 [Fact Sheet](#23-fact-sheet)
   - 2.4 [Comparison Matrix](#24-comparison-matrix)
   - 2.5 [Timeline](#25-timeline)
   - 2.6 [Annotated Bibliography](#26-annotated-bibliography)
3. [Citation System](#3-citation-system)
4. [Confidence Visualization](#4-confidence-visualization)
5. [Section Structure Template](#5-section-structure-template)
6. [Output Templates (Ready-to-Use)](#6-output-templates-ready-to-use)
7. [Adaptive Format Selection](#7-adaptive-format-selection)
8. [Progressive Disclosure](#8-progressive-disclosure)
9. [Appendix: Metadata Schema](#9-appendix-metadata-schema)

---

## 1. Design Philosophy

The Output Format Specification is built on five architectural principles derived from the reference skills:

| Principle | Source Inspiration | Application |
|---|---|---|
| **Tiered Architecture** | Life Planning Coach SKILL.md | Core formats are always available; advanced formats lazy-loaded on demand |
| **Markdown-Native** | Fintech Discovery Skill | All output is valid, renderable Markdown — no proprietary syntax |
| **Evidence-First** | Deep Research Swarm | Every claim is traceable to a source; confidence is explicit |
| **Progressive Disclosure** | Life Planning Coach | Summary first, details on demand; never overwhelm |
| **Connection-First** | Life Planning Coach | The reader must immediately see value, not structure |

### Format Decision Tree (High-Level)

```
User Query
    |
    +---> Factual lookup (who, what, when) -----> Fact Sheet
    |
    +---> Comparative (vs, compare, best) -------> Comparison Matrix
    |
    +---> Chronological (history, evolution) ----> Timeline
    |
    +---> Decision support (should, recommend) --> Executive Brief (+ Matrix)
    |
    +---> Deep exploration (why, how, analyze) ---> Research Report
    |
    +---> Source discovery (papers, references) -> Annotated Bibliography
    |
    +---> Unspecified / complex -----------------> Research Report + Brief
```

---

## 2. Core Output Formats

### 2.1 Research Report

**Purpose:** Comprehensive, publication-grade research document for deep exploration.

**Trigger:** `depth_level >= 3`, complex analytical queries, "explain", "analyze", "research" intents.

**Characteristics:**
- Full argumentation with supporting evidence
- Methodology transparency
- Multi-source synthesis
- Critical analysis, not just compilation

**Structure:**

```markdown
# [Title]: [Research Question]

> **Research ID:** `rr-{YYYYMMDD}-{hash}`
> **Generated:** {timestamp}
> **Query Depth:** {1-5}
> **Routes Used:** {web_search | arxiv | scholar | ...}
> **Sources Consulted:** {N}
> **Confidence Aggregate:** {score}

---

## Executive Snapshot

<!-- Always first: the entire report in 150 words -->

## 1. Introduction

<!-- Context, research question scope, why it matters -->

## 2. Methodology

<!-- Search strategy, sources consulted, filtering criteria, limitations -->

## 3. Key Findings

<!-- Numbered, each with confidence indicator and inline citation -->

## 4. Analysis

<!-- Synthesis across sources, pattern identification, critical evaluation -->

## 5. Implications

<!-- What the findings mean for different stakeholders -->

## 6. Recommendations

<!-- Actionable, prioritized, with rationale -->

## 7. Limitations & Gaps

<!-- Honest assessment of what we don't know -->

## 8. Sources

<!-- Full citation registry -->

## Appendices (Optional)

<!-- Raw data tables, extended methodology, glossary -->
```

**Length Guidelines:**

| Depth | Target Length | Sections |
|-------|--------------|----------|
| 3 (Standard) | 1,500–3,000 words | Snapshot, Intro, Findings (3-5), Analysis, Sources |
| 4 (Deep) | 3,000–6,000 words | Full structure + Methodology + Implications |
| 5 (Exhaustive) | 6,000–10,000 words | Full structure + Limitations + Appendices |

---

### 2.2 Executive Brief

**Purpose:** Decision-making document for time-constrained stakeholders.

**Trigger:** "summarize", "brief", "executive summary", user preference `format: brief`, follow-up to Research Report.

**Characteristics:**
- Maximum 2 pages (~800 words)
- Lead with conclusion (BLUF: Bottom Line Up Front)
- Quantified findings prioritized
- Recommendations are explicit and actionable

**Structure:**

```markdown
# Executive Brief: [Topic]

> **Brief ID:** `eb-{YYYYMMDD}-{hash}`
> **Generated:** {timestamp}
> **Based On:** Research Report `rr-{id}` (if applicable)
> **Confidence Aggregate:** {score}

---

## Bottom Line

<!-- 2-3 sentences: the answer to the user's question -->

## Key Numbers

<!-- 3-5 quantified findings in a table -->

| Metric | Value | Source |
|--------|-------|--------|

## Critical Findings

<!-- 3-5 bullet points, most important first -->

## Recommended Actions

<!-- Prioritized table: Action | Impact | Effort | Confidence -->

| Priority | Action | Expected Impact | Effort | Confidence |
|----------|--------|-----------------|--------|------------|

## Risk Factors

<!-- What could change these conclusions -->

## Sources Summary

<!-- Compact citation list (5-10 key sources only) -->
```

**Constraints:**
- No unquantified superlatives ("significant", "important" without numbers)
- Every claim has a citation
- Recommendations use "should" (not "could") when confidence >= HIGH
- Append-only: never contradict the underlying Research Report

---

### 2.3 Fact Sheet

**Purpose:** Atomic fact database with provenance and confidence for verification-heavy queries.

**Trigger:** "facts about", "what is", "who is", "statistics on", verification requests.

**Characteristics:**
- One fact per row
- Every fact traced to source
- Confidence explicitly rated
- Chronological where relevant

**Structure:**

```markdown
# Fact Sheet: [Topic]

> **Sheet ID:** `fs-{YYYYMMDD}-{hash}`
> **Generated:** {timestamp}
> **Facts Verified:** {N}
> **Coverage:** {topic scope}

---

## Facts

| # | Claim | Category | Source | Confidence | Date Verified |
|---|-------|----------|--------|------------|---------------|
| 1 | ... | Statistic | [^1^] | 🟢 | 2025-01-20 |
| 2 | ... | Biography | [^2^] | 🔵 | 2025-01-20 |
| 3 | ... | Quote | [^3^] | 🟡 | 2025-01-20 |

## Confidence Legend

- 🔵 **Confirmed** — Multiple independent sources corroborate
- 🟢 **High** — Authoritative primary source, no contradiction
- 🟡 **Medium** — Credible source, limited corroboration
- 🔴 **Low** — Single source, unverified, or preliminary

## Sources

<!-- Full registry -->
```

**Row Categories:** `Statistic`, `Quote`, `Event`, `Definition`, `Relationship`, `Claim`, `Projection`

**Rules:**
- Each claim is atomic (one assertion only)
- No synthesis or interpretation in the Claim column
- Source must be primary where possible
- Date is the fact's date, not retrieval date

---

### 2.4 Comparison Matrix

**Purpose:** Side-by-side comparison of options against weighted criteria.

**Trigger:** "vs", "compare", "best", "which", "alternatives", decision support.

**Characteristics:**
- Criteria are explicit and weighted (where possible)
- Each cell is evidence-backed
- Options scored where quantifiable
- Winner highlighted per criterion, not overall

**Structure:**

```markdown
# Comparison: [Option A] vs [Option B] vs [Option C]

> **Matrix ID:** `cm-{YYYYMMDD}-{hash}`
> **Generated:** {timestamp}
> **Dimensions Compared:** {N}
> **Winner by Dimension:** {summary}

---

## At a Glance

<!-- Emoji scorecard -->

| Dimension | {Option A} | {Option B} | {Option C} | Weight |
|-----------|------------|------------|------------|--------|

## Detailed Comparison

### Dimension 1: [Criterion Name] (Weight: {X}%)

| Aspect | {Option A} | {Option B} | {Option C} | Source |
|--------|------------|------------|------------|--------|

**Verdict:** [Which option leads, with rationale and confidence]

<!-- Repeat for each dimension -->

## Scoring Summary

| Option | Weighted Score | Best At | Weakest At |
|--------|---------------|---------|------------|

## Recommendation

<!-- Conditional, based on user priorities -->

**If you prioritize [X]:** → [Option]
**If you prioritize [Y]:** → [Option]

## Sources
```

**Scoring Scale per Cell:**

| Symbol | Meaning |
|--------|---------|
| ✅ **Strong** | Clear advantage |
| ⚖️ **Comparable** | No meaningful difference |
| ❌ **Weak** | Clear disadvantage |
| ❓ **Unknown** | Insufficient data |
| 📊 `{N}` | Quantified value (e.g., price, speed) |

**Rules:**
- No overall "winner" row — let the reader decide based on their weights
- Every cell verdict cites a source
- Weights are explicit (default: equal if user doesn't specify)

---

### 2.5 Timeline

**Purpose:** Chronological reconstruction of events with provenance.

**Trigger:** "history of", "when did", "timeline", "evolution of", "sequence".

**Characteristics:**
- Events in chronological order
- Each event sourced
- Confidence indicates certainty of date/event
- Supports parallel tracks (e.g., two organizations)

**Structure:**

```markdown
# Timeline: [Topic]

> **Timeline ID:** `tl-{YYYYMMDD}-{hash}`
> **Generated:** {timestamp}
> **Coverage:** {start_date} – {end_date}
> **Events Tracked:** {N}

---

## Chronology

### [Year / Era Name]

| Date | Event | Significance | Source | Confidence |
|------|-------|--------------|--------|------------|
| YYYY-MM | ... | ... | [^1^] | 🟢 |
| YYYY-MM | ... | ... | [^2^] | 🟡 |

<!-- Repeat by era/year -->

## Parallel Tracks (Optional)

<!-- For comparing timelines side-by-side -->

| Date | Track A | Track B | Source |
|------|---------|---------|--------|

## Sources
```

**Date Granularity Rules:**
- Exact date known → `YYYY-MM-DD`
- Month known → `YYYY-MM`
- Year only → `YYYY`
- Approximate → `c. YYYY` with 🔴 confidence
- Ongoing → `YYYY–present`

---

### 2.6 Annotated Bibliography

**Purpose:** Curated source list with relevance assessment for deep-dive research.

**Trigger:** "literature review", "sources", "papers on", "what to read", "references".

**Characteristics:**
- Each source summarized
- Relevance score to the query
- Quality assessment
- Suggested reading order

**Structure:**

```markdown
# Annotated Bibliography: [Topic]

> **Bib ID:** `ab-{YYYYMMDD}-{hash}`
> **Generated:** {timestamp}
> **Sources Evaluated:** {N}
> **Highly Relevant:** {N} | **Moderately Relevant:** {N} | **Background:** {N}

---

## Reading Guide

<!-- Suggested order through the sources -->

1. **Start here:** [Source title] — best overview
2. **Then:** [Source title] — core evidence
3. **Deep dive:** [Source title] — methodology
4. **Context:** [Source title] — background

## Sources by Relevance

### 🔴 Highly Relevant

#### [^1^] [Title]

- **Authors:** ...
- **Date:** ...
- **Source Type:** {academic_paper | news | report | book | blog | dataset}
- **Access:** {open_access | paywalled | subscription}
- **Quality Tier:** {T1 | T2 | T3} (see Appendix)
- **Relevance Score:** {1-10}/10
- **Summary:** 3-5 sentences capturing the core contribution
- **Key Finding:** The most important takeaway
- **Limitations:** Known weaknesses of this source
- **Cited By:** How this source is used in the research

### 🟡 Moderately Relevant

<!-- Same structure -->

### 🟢 Background Reading

<!-- Same structure -->

## Source Quality Tiers

| Tier | Description | Examples |
|------|-------------|----------|
| T1 | Peer-reviewed, primary, authoritative | Nature, IEEE, official government data |
| T2 | Credible secondary, expert-reviewed | Reuters, analyst reports, reputable outlets |
| T3 | informed opinion, tertiary | Blogs, Wikipedia, opinion pieces |
| TX | Unverified / flagged | Preprints, anonymous sources (flagged) |

## Search Strategy (Optional)

<!-- How these sources were found — for reproducibility -->
```

---

## 3. Citation System

### 3.1 Inline Citation Format

All citations use **superscript numeric brackets** — renderable in all Markdown parsers:

```markdown
The global AI market reached $196B in 2024 [^1^], with projections 
suggesting $1.8T by 2030 [^2^][^3^].
```

**Rules:**
- Numbers are sequential in order of **first appearance**
- Multiple citations for one claim: `[^1^][^2^]` (no commas, no spaces)
- Citation always follows the claim, before punctuation where possible
- Never use bare URLs in text — always registry-reference

### 3.2 Source Registry

Every output document ends with a **Sources** section:

```markdown
## Sources

[^1^]: Author(s). "Title." *Publication/Source*, Date. URL (accessed YYYY-MM-DD).
[^2^]: Organization. *Report Title* (Edition). Date. URL.
[^3^]: LastName, FirstName. *Book Title*. Publisher, Year. ISBN.
[^4^]: "Article Title." *Website Name*. Date. URL. [Archived](archive-url)
```

**Registry Format by Source Type:**

| Type | Format | Example |
|------|--------|---------|
| **Web page** | `[^N^]: "Title." *Site*, YYYY-MM-DD. URL` | `[^1^]: "AI Market Size." *Statista*, 2024-06-15. https://...` |
| **News article** | `[^N^]: Author. "Title." *Publication*, YYYY-MM-DD. URL` | `[^2^]: Smith, J. "AI Boom Continues." *Reuters*, 2024-05-01. https://...` |
| **Academic paper** | `[^N^]: Authors. "Title." *Journal*, Vol, Year. DOI/URL` | `[^3^]: Chen et al. "Deep Learning Survey." *Nature ML*, 2024. doi:...` |
| **Report** | `[^N^]: Org. *Title* (ver). Date. URL` | `[^4^]: McKinsey. *State of AI* (2024). 2024-03. https://...` |
| **Book** | `[^N^]: Author. *Title*. Publisher, Year. ISBN` | `[^5^]: Russell, S. *Human Compatible*. Viking, 2019. 978-0-525-55861-3` |
| **Dataset** | `[^N^]: Creator. *Dataset Name* [repository]. Date. URL` | `[^6^]: World Bank. *GDP Data* [World Bank Open Data]. 2024. https://...` |

### 3.3 Citation Types (Metadata)

Each source in the registry may include an optional **citation type tag**:

```markdown
[^1^]: Smith, J. "AI Trends." *TechCrunch*, 2024. https://... [Type: data]
```

| Tag | Meaning | Use When |
|-----|---------|----------|
| `[Type: direct_quote]` | Exact words quoted | Verbatim text in quotation marks |
| `[Type: paraphrase]` | Ideas restated in our words | Substance attributed, wording ours |
| `[Type: data]` | Statistics, numbers, measurements | Any quantified claim |
| `[Type: inference]` | Our conclusion from source | Logical extension, not author's claim |
| `[Type: background]` | Context, not directly cited | Supporting understanding |
| `[Type: cross_ref]` | Source verifies another source | Corroboration entries |

### 3.4 Broken Link Handling

When a source URL is unreachable during research:

```markdown
[^7^]: Author. "Title." *Site*, Date. URL ⚠️ **BROKEN** 
      [Archived](https://web.archive.org/...) (accessed YYYY-MM-DD)
      [Alternative](backup-url)
```

**Protocol:**
1. Always attempt archive.org retrieval first
2. If archived version exists → add `[Archived](url)` link
3. If no archive → search for alternative URL from same source
4. Flag with ⚠️ in registry
5. If source is critical and irretrievable → downgrade confidence to 🟡 or 🔴
6. Never remove a cited source — maintain integrity even if link dies

---

## 4. Confidence Visualization

### 4.1 Confidence Scale

Every verifiable claim carries a **confidence indicator**:

| Emoji | Level | Definition | Criteria |
|-------|-------|------------|----------|
| 🔵 **Confirmed** | 4/4 | Consensus across multiple independent authoritative sources | 3+ T1 sources agree; no credible contradiction |
| 🟢 **High** | 3/4 | Authoritative source, well-supported | Primary source or 2+ T2 sources; limited uncertainty |
| 🟡 **Medium** | 2/4 | Credible but limited or preliminary | Single T1/T2 source; or T3 with corroboration |
| 🔴 **Low** | 1/4 | Weak evidence, speculative, or contested | Single T3 source; significant uncertainty; emerging claim |
| ⚪ **Unverifiable** | 0/4 | Cannot be verified with available sources | No direct evidence; opinion; prediction without basis |

### 4.2 Per-Claim Indicators

**Inline format:**

```markdown
The Earth revolves around the Sun [^1^] 🟢.

Climate change is accelerating beyond IPCC projections [^2^][^3^] 🔵.

Some researchers suggest cold fusion may be viable [^4^] 🔴.
```

**Rules:**
- Emoji follows the citation(s), before sentence-ending punctuation
- Only one confidence emoji per claim
- When multiple sources with different confidences → use the *highest supported* level
- If sources contradict → use 🟡 with `[Conflict: sources disagree]` note

### 4.3 Aggregate Confidence Score

Every document header includes:

```markdown
> **Confidence Aggregate:** 🟢 72% (High)
> 
> Breakdown: 🔵 12% | 🟢 45% | 🟡 30% | 🔴 10% | ⚪ 3%
```

**Calculation:**
```
Aggregate = Σ(confidence_level_i × claim_weight_i) / Σ(claim_weight_i)
```

Where `claim_weight_i` is 2 for central claims, 1 for peripheral/contextual claims.

**Display thresholds:**

| Aggregate Range | Display |
|-----------------|---------|
| 85-100% | 🔵 **Confirmed** |
| 65-84% | 🟢 **High** |
| 40-64% | 🟡 **Medium** |
| 15-39% | 🔴 **Low** |
| 0-14% | ⚪ **Unverifiable** |

### 4.4 Confidence by Source Tier

Optional section in Research Reports:

```markdown
### Confidence by Evidence Base

| Source Tier | Claims Supported | Avg Confidence | Sources |
|-------------|-----------------|---------------|---------|
| T1 (Primary/Peer-reviewed) | 23 | 🟢 82% | 8 |
| T2 (Credible Secondary) | 15 | 🟡 58% | 12 |
| T3 (Tertiary/Opinion) | 5 | 🟡 45% | 4 |
| TX (Flagged/Unverified) | 2 | 🔴 25% | 2 |
```

---

## 5. Section Structure Template

### 5.1 Standard Research Report Structure

```
Document
├── Metadata Block (required)
├── Executive Snapshot (required, always first)
├── Table of Contents (auto-generated, depth >= 4)
│
├── 1. Introduction (required)
│   ├── Context
│   ├── Research Question
│   ├── Scope & Boundaries
│   └── Significance
│
├── 2. Methodology (required for depth >= 4)
│   ├── Search Strategy
│   ├── Source Evaluation Criteria
│   ├── Coverage Map (what was searched)
│   └── Limitations
│
├── 3. Key Findings (required)
│   ├── Finding 1: [Title] (confidence)
│   ├── Finding 2: [Title] (confidence)
│   └── ...
│
├── 4. Analysis (required for depth >= 3)
│   ├── Synthesis
│   ├── Pattern Recognition
│   ├── Contradictions & Gaps
│   └── Critical Evaluation
│
├── 5. Implications (optional, depth >= 4)
│   ├── For Industry/Field
│   ├── For Policy
│   └── For Future Research
│
├── 6. Recommendations (optional)
│   ├── Priority 1
│   ├── Priority 2
│   └── Priority 3
│
├── 7. Limitations & Future Research (required for depth >= 4)
│
├── 8. Sources (required)
│   └── Full Citation Registry
│
└── Appendices (optional, depth >= 5)
    ├── A. Raw Data Tables
    ├── B. Extended Methodology
    ├── C. Glossary
    └── D. Search Logs
```

### 5.2 Metadata Block (All Formats)

Every output document MUST begin with:

```markdown
> **Format:** {research_report | executive_brief | fact_sheet | comparison_matrix | timeline | annotated_bibliography}
> **Document ID:** `{prefix}-{YYYYMMDD}-{hash}`
> **Generated:** {ISO 8601 timestamp}
> **Query:** "{original user query}"
> **Query Depth:** {1 | 2 | 3 | 4 | 5}
> **Routes Used:** {web_search | arxiv | scholar | finance | news | ...}
> **Sources Consulted:** {N}
> **Sources Cited:** {N}
> **Confidence Aggregate:** {emoji} {percentage} ({level})
> **Session Cost:** {N} tool calls | {tokens} tokens
```

### 5.3 Optional Section Activation Matrix

| Section | Depth 1-2 | Depth 3 | Depth 4 | Depth 5 |
|---------|-----------|---------|---------|---------|
| Executive Snapshot | ✅ | ✅ | ✅ | ✅ |
| Methodology | ❌ | ⚪ | ✅ | ✅ |
| Analysis | ❌ | ✅ | ✅ | ✅ |
| Implications | ❌ | ⚪ | ✅ | ✅ |
| Recommendations | ❌ | ⚪ | ⚪ | ✅ |
| Limitations | ❌ | ⚪ | ✅ | ✅ |
| Appendices | ❌ | ❌ | ❌ | ✅ |
| TOC | ❌ | ❌ | ✅ | ✅ |

> ✅ = Required | ⚪ = Optional (context-dependent) | ❌ = Omitted

---

## 6. Output Templates (Ready-to-Use)

### 6.1 Research Report Template

```markdown
# [Research Report]: {{RESEARCH_QUESTION}}

> **Format:** research_report
> **Document ID:** `rr-{{YYYYMMDD}}-{{HASH}}`
> **Generated:** {{TIMESTAMP}}
> **Query:** "{{ORIGINAL_QUERY}}"
> **Query Depth:** {{DEPTH_LEVEL}}
> **Routes Used:** {{ROUTES}}
> **Sources Consulted:** {{N}}
> **Confidence Aggregate:** {{CONFIDENCE_EMOJI}} {{CONFIDENCE_PCT}}% ({{CONFIDENCE_LEVEL}})

---

## Executive Snapshot

{{150_WORD_SUMMARY}}

---

## Table of Contents

<!-- auto-generated -->

## 1. Introduction

### Context

{{WHY_THIS_QUESTION_MATTERS}}

### Research Question

>{{PRECISE_QUESTION}}

### Scope

{{BOUNDARIES}}

---

## 2. Methodology

### Search Strategy

{{SEARCH_TERMS_AND_ROUTES}}

### Source Evaluation

{{INCLUSION_CRITERIA}}

### Coverage

| Source Type | Searched | Found | Used |
|-------------|----------|-------|------|
| Academic | {{N}} | {{N}} | {{N}} |
| News | {{N}} | {{N}} | {{N}} |
| Reports | {{N}} | {{N}} | {{N}} |
| Data | {{N}} | {{N}} | {{N}} |

### Limitations

{{HONEST_LIMITATIONS}}

---

## 3. Key Findings

### Finding 1: {{TITLE}} {{CONFIDENCE_EMOJI}}

{{EVIDENCE_AND_ANALYSIS}}

> **Sources:** [^{{N}}^][^{{N}}^] | **Confidence:** {{LEVEL}}

### Finding 2: {{TITLE}} {{CONFIDENCE_EMOJI}}

{{EVIDENCE_AND_ANALYSIS}}

> **Sources:** [^{{N}}^] | **Confidence:** {{LEVEL}}

<!-- Repeat as needed -->

---

## 4. Analysis

### Synthesis

{{CROSS_SOURCE_SYNTHESIS}}

### Patterns

{{RECOGNIZED_PATTERNS}}

### Contradictions

{{DIVERGENT_EVIDENCE}}

---

## 5. Implications

{{WHAT_THIS_MEANS}}

---

## 6. Recommendations

| Priority | Recommendation | Rationale | Confidence |
|----------|---------------|-----------|------------|
| P1 | {{REC}} | {{WHY}} | {{CONF}} |
| P2 | {{REC}} | {{WHY}} | {{CONF}} |
| P3 | {{REC}} | {{WHY}} | {{CONF}} |

---

## 7. Limitations & Future Research

{{KNOWN_GAPS}}

---

## 8. Sources

<!-- Auto-populated citation registry -->

{{CITATION_REGISTRY}}
```

### 6.2 Executive Brief Template

```markdown
# Executive Brief: {{TOPIC}}

> **Format:** executive_brief
> **Document ID:** `eb-{{YYYYMMDD}}-{{HASH}}`
> **Generated:** {{TIMESTAMP}}
> **Based On:** Research Report `rr-{{ID}}` (if applicable)
> **Confidence Aggregate:** {{CONFIDENCE_EMOJI}} {{CONFIDENCE_PCT}}%

---

## Bottom Line

{{2-3_SENTENCES_ANSWER}}

---

## Key Numbers

| # | Metric | Value | Trend | Source |
|---|--------|-------|-------|--------|
| 1 | {{NAME}} | {{VALUE}} | {{↑↓→}} | [^{{N}}^] |
| 2 | {{NAME}} | {{VALUE}} | {{↑↓→}} | [^{{N}}^] |
| 3 | {{NAME}} | {{VALUE}} | {{↑↓→}} | [^{{N}}^] |
| 4 | {{NAME}} | {{VALUE}} | {{↑↓→}} | [^{{N}}^] |
| 5 | {{NAME}} | {{VALUE}} | {{↑↓→}} | [^{{N}}^] |

---

## Critical Findings

1. **{{FINDING_1}}** — [^{{N}}^] {{CONFIDENCE_EMOJI}}
2. **{{FINDING_2}}** — [^{{N}}^] {{CONFIDENCE_EMOJI}}
3. **{{FINDING_3}}** — [^{{N}}^] {{CONFIDENCE_EMOJI}}
4. **{{FINDING_4}}** — [^{{N}}^] {{CONFIDENCE_EMOJI}} (if applicable)
5. **{{FINDING_5}}** — [^{{N}}^] {{CONFIDENCE_EMOJI}} (if applicable)

---

## Recommended Actions

| Priority | Action | Impact | Effort | Confidence | Owner |
|----------|--------|--------|--------|------------|-------|
| Must | {{ACTION}} | {{HIGH/MED/LOW}} | {{HIGH/MED/LOW}} | {{CONF}} | {{WHO}} |
| Should | {{ACTION}} | {{HIGH/MED/LOW}} | {{HIGH/MED/LOW}} | {{CONF}} | {{WHO}} |
| Could | {{ACTION}} | {{HIGH/MED/LOW}} | {{HIGH/MED/LOW}} | {{CONF}} | {{WHO}} |

---

## Risk Factors

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {{RISK}} | {{HIGH/MED/LOW}} | {{HIGH/MED/LOW}} | {{HOW}} |

---

## Sources Summary

{{TOP_5_KEY_SOURCES}}
```

### 6.3 Fact Sheet Template

```markdown
# Fact Sheet: {{TOPIC}}

> **Format:** fact_sheet
> **Document ID:** `fs-{{YYYYMMDD}}-{{HASH}}`
> **Generated:** {{TIMESTAMP}}
> **Query:** "{{ORIGINAL_QUERY}}"
> **Facts Verified:** {{N}}
> **Coverage:** {{SCOPE}}

---

## Quick Stats

| Category | Count |
|----------|-------|
| Total Facts | {{N}} |
| 🔵 Confirmed | {{N}} |
| 🟢 High Confidence | {{N}} |
| 🟡 Medium Confidence | {{N}} |
| 🔴 Low Confidence | {{N}} |
| ⚪ Unverifiable | {{N}} |

---

## Facts

| # | Claim | Category | Source | Confidence | Date |
|---|-------|----------|--------|------------|------|
| 1 | {{FACT}} | {{CATEGORY}} | [^{{N}}^] | {{EMOJI}} | {{DATE}} |
| 2 | {{FACT}} | {{CATEGORY}} | [^{{N}}^] | {{EMOJI}} | {{DATE}} |
| 3 | {{FACT}} | {{CATEGORY}} | [^{{N}}^] | {{EMOJI}} | {{DATE}} |
| 4 | {{FACT}} | {{CATEGORY}} | [^{{N}}^] | {{EMOJI}} | {{DATE}} |
| 5 | {{FACT}} | {{CATEGORY}} | [^{{N}}^] | {{EMOJI}} | {{DATE}} |

<!-- Continue to N -->

---

## Fact Categories Breakdown

| Category | Count | Avg Confidence |
|----------|-------|---------------|
| Statistic | {{N}} | {{EMOJI}} {{PCT}}% |
| Quote | {{N}} | {{EMOJI}} {{PCT}}% |
| Event | {{N}} | {{EMOJI}} {{PCT}}% |
| Definition | {{N}} | {{EMOJI}} {{PCT}}% |
| Relationship | {{N}} | {{EMOJI}} {{PCT}}% |
| Projection | {{N}} | {{EMOJI}} {{PCT}}% |

---

## Confidence Legend

- 🔵 **Confirmed** — Multiple independent T1 sources corroborate
- 🟢 **High** — Authoritative primary source, no contradiction
- 🟡 **Medium** — Credible source, limited corroboration
- 🔴 **Low** — Single source, unverified, or preliminary
- ⚪ **Unverifiable** — Cannot be verified with available sources

---

## Sources

{{CITATION_REGISTRY}}
```

### 6.4 Comparison Matrix Template

```markdown
# Comparison: {{SUBJECT}}

> **Format:** comparison_matrix
> **Document ID:** `cm-{{YYYYMMDD}}-{{HASH}}`
> **Generated:** {{TIMESTAMP}}
> **Options Compared:** {{N}} — {{OPTION_NAMES}}
> **Dimensions:** {{N}}

---

## At a Glance

| Dimension | Weight | {{OPT_A}} | {{OPT_B}} | {{OPT_C}} |
|-----------|--------|-----------|-----------|-----------|
| {{DIM_1}} | {{W}}% | {{SCORE}} | {{SCORE}} | {{SCORE}} |
| {{DIM_2}} | {{W}}% | {{SCORE}} | {{SCORE}} | {{SCORE}} |
| {{DIM_3}} | {{W}}% | {{SCORE}} | {{SCORE}} | {{SCORE}} |
| {{DIM_4}} | {{W}}% | {{SCORE}} | {{SCORE}} | {{SCORE}} |
| {{DIM_5}} | {{W}}% | {{SCORE}} | {{SCORE}} | {{SCORE}} |
| **Weighted Total** | **100%** | **{{TOTAL}}** | **{{TOTAL}}** | **{{TOTAL}}** |

---

## Detailed Comparison

### {{DIM_1}} (Weight: {{W}}%)

| Aspect | {{OPT_A}} | {{OPT_B}} | {{OPT_C}} | Source |
|--------|-----------|-----------|-----------|--------|
| {{ASPECT}} | {{VAL}} | {{VAL}} | {{VAL}} | [^{{N}}^] |

**Verdict:** {{WHICH_LEADS}} — {{RATIONALE}} {{CONFIDENCE_EMOJI}}

---

### {{DIM_2}} (Weight: {{W}}%)

<!-- Same structure -->

---

## Scoring Summary

| Option | Score | Best At | Weakest At | Overall |
|--------|-------|---------|------------|---------|
| {{OPT_A}} | {{SCORE}} | {{DIM}} | {{DIM}} | {{ASSESSMENT}} |
| {{OPT_B}} | {{SCORE}} | {{DIM}} | {{DIM}} | {{ASSESSMENT}} |
| {{OPT_C}} | {{SCORE}} | {{DIM}} | {{DIM}} | {{ASSESSMENT}} |

---

## Scenario-Based Recommendations

**If you prioritize {{DIM_X}}:** → {{OPTION}}
**If you prioritize {{DIM_Y}}:** → {{OPTION}}
**If you prioritize {{DIM_Z}}:** → {{OPTION}}
**Balanced choice:** → {{OPTION}}

---

## Sources

{{CITATION_REGISTRY}}
```

---

## 7. Adaptive Format Selection

### 7.1 Format-by-Query-Type Mapping

| Query Pattern | Example Query | Primary Format | Secondary Format |
|---------------|---------------|----------------|------------------|
| **Factual lookup** | "What is the GDP of India?" | Fact Sheet | — |
| **Definition** | "What is transformer architecture?" | Fact Sheet | Annotated Bibliography |
| **Comparison** | "React vs Vue vs Angular" | Comparison Matrix | Executive Brief |
| **Evaluation** | "Best project management tool" | Comparison Matrix | Executive Brief |
| **Chronology** | "History of SpaceX launches" | Timeline | Fact Sheet |
| **Cause/Effect** | "Why did SVB collapse?" | Research Report | Timeline |
| **Trend** | "AI chip market trends 2024" | Research Report | Executive Brief |
| **How-to/Process** | "How does CRISPR work?" | Research Report | Fact Sheet |
| **Strategic** | "Should we enter SE Asia market?" | Executive Brief | Comparison Matrix |
| **Literature** | "Key papers on diffusion models" | Annotated Bibliography | — |
| **Open-ended** | "Tell me about quantum computing" | Research Report | — |
| **Verification** | "Is it true that X?" | Fact Sheet | Research Report |

### 7.2 Format-by-Depth-Level Mapping

| Depth Level | Name | Default Format | Detail |
|-------------|------|----------------|--------|
| 1 | **Quick Answer** | Fact Sheet | Single fact, 50-100 words |
| 2 | **Brief** | Executive Brief | Key points, 300-500 words |
| 3 | **Standard** | Research Report (abridged) | Core findings + analysis, 1,500-3,000 words |
| 4 | **Deep** | Research Report (full) | Full methodology + implications, 3,000-6,000 words |
| 5 | **Exhaustive** | Research Report + Bibliography | Everything + appendices, 6,000-10,000+ words |

### 7.3 User Preference Overrides

Users can request specific formats via:

```
"Give me a brief" → Executive Brief (regardless of depth)
"Show me the facts" → Fact Sheet
"Compare them" → Comparison Matrix
n"Full report" → Research Report (forces depth >= 3)
"Sources only" → Annotated Bibliography
"Timeline view" → Timeline
```

**Override Priority:** Explicit user request > Query-type inference > Depth default

### 7.4 Multi-Format Output

When the query benefits from multiple perspectives, output **primary + secondary** formats:

```markdown
## Primary Output: [Format Name]

<!-- Full primary document -->

---

## Supplement: [Format Name]

<!-- Condensed secondary format — key points only -->
```

**Multi-format triggers:**
- Depth >= 4 with comparative element → Research Report + Comparison Matrix
- Strategic decision query → Executive Brief + Fact Sheet
- Literature-heavy topic → Research Report + Annotated Bibliography
- Historical analysis → Research Report + Timeline

---

## 8. Progressive Disclosure

### 8.1 Display Strategy: "Layer Cake"

Inspired by the Life Planning Coach's "Connection First, Progressive Disclosure" principle:

```
Layer 1 (Immediate): Executive Snapshot — 150 words, 10 seconds to read
Layer 2 (Quick):    Key Findings / At a Glance — 2-minute scan
Layer 3 (Standard): Full document body — 10-15 minute read
Layer 4 (Deep):     Methodology, Appendices, Full Sources — on demand
```

**Implementation in Markdown:**

```markdown
<!-- Layer 1: Always visible, always first -->
## Executive Snapshot

{{SUMMARY}}

---

<!-- Layer 2: TOC-linked, scannable -->
## Key Findings at a Glance

| # | Finding | Confidence |
|---|---------|------------|

---

<!-- Layer 3: Main content -->
## 1. Introduction
...

---

<!-- Layer 4: Collapsed by default (rendered as <details> in HTML) -->
<details>
<summary>📋 Full Methodology (click to expand)</summary>

## Methodology
...
</details>

<details>
<summary>📚 Complete Source Registry ({{N}} sources)</summary>

## Sources
...
</details>
```

### 8.2 Expandable Sections

Use native HTML `<details>` tags for collapsible content:

```markdown
<details>
<summary>🔍 View Search Strategy</summary>

**Queries executed:**
- "AI market size 2024"
- "artificial intelligence industry growth forecast"
- "AI adoption statistics enterprise"

**Sources queried:** Web Search, Statista, McKinsey reports
</details>
```

**Sections suitable for collapsing:**
- Full Methodology
- Complete Source Registry (>10 sources)
- Appendices
- Raw Data Tables
- Alternative Scenarios
- Detailed Calculations

### 8.3 Navigation (Table of Contents)

Auto-generated TOC for depth >= 4:

```markdown
## Table of Contents

- [Executive Snapshot](#executive-snapshot)
- [1. Introduction](#1-introduction)
  - [Context](#context)
  - [Research Question](#research-question)
- [2. Methodology](#2-methodology)
- [3. Key Findings](#3-key-findings)
  - [Finding 1: ...](#finding-1-...)
  - [Finding 2: ...](#finding-2-...)
- [4. Analysis](#4-analysis)
- [5. Sources](#5-sources)
```

**TOC Rules:**
- Always linked to section anchors
- Include only H2 and H3 headings
- Maximum 15 entries (collapse subsections if more)
- Not included for depth < 4 (document is short enough)

### 8.4 Reading Time Indicators

```markdown
> **Reading time:** ~12 minutes (3,800 words)
> **Snapshot:** ~1 minute
```

---

## 9. Appendix: Metadata Schema

### Document Metadata (JSON, for programmatic access)

```json
{
  "document": {
    "format": "research_report",
    "id": "rr-20250120-a1b2c3d4",
    "version": "1.0",
    "generated_at": "2025-01-20T14:30:00Z",
    "query": {
      "original": "How is the AI chip market evolving?",
      "depth_level": 4,
      "routes_used": ["web_search", "yahoo_finance", "arxiv"],
      "estimated_cost": {
        "tool_calls": 12,
        "tokens": 45000
      }
    },
    "content": {
      "title": "The AI Chip Market: Evolution and Trajectory",
      "word_count": 5200,
      "section_count": 7,
      "reading_time_minutes": 18
    },
    "sources": {
      "consulted": 24,
      "cited": 18,
      "by_tier": {
        "T1": 8,
        "T2": 10,
        "T3": 4,
        "TX": 2
      }
    },
    "confidence": {
      "aggregate": {
        "score": 0.72,
        "level": "high",
        "emoji": "🟢"
      },
      "distribution": {
        "confirmed": 0.12,
        "high": 0.45,
        "medium": 0.30,
        "low": 0.10,
        "unverifiable": 0.03
      }
    },
    "formats_available": [
      "research_report",
      "executive_brief",
      "fact_sheet"
    ]
  }
}
```

### Source Registry Entry Schema

```json
{
  "source": {
    "id": 1,
    "citation_key": "^1^",
    "type": "web_page",
    "authors": ["Smith, John"],
    "title": "The State of AI Chips in 2024",
    "publication": "TechCrunch",
    "date": "2024-06-15",
    "url": "https://techcrunch.com/...",
    "archive_url": "https://web.archive.org/...",
    "accessed": "2025-01-20",
    "doi": null,
    "isbn": null,
    "tier": "T2",
    "citation_type": "data",
    "confidence": "high",
    "status": "active",
    "claims_supported": [3, 7, 12]
  }
}
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-20 | Deep Research Skill Team | Initial specification |

---

*End of Output Format Specification*
