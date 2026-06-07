# Usage Guide

## Deep Research Skill — How to Use

---

## Overview

Deep Research Skill automatically activates when you ask research-related questions. It follows a structured 6-phase workflow to deliver high-quality, evidence-based research reports.

---

## Activation

### Automatic Triggers

The skill activates on keywords and phrases:

**Russian:**
- "Проведи исследование..."
- "Анализ рынка..."
- "Конкурентный анализ..."
- "Собери информацию о..."
- "Что известно о..."
- "Сравни..."
- "Тренды в..."
- "Обзор технологий..."

**English:**
- "Deep research on..."
- "Market analysis of..."
- "Competitive analysis..."
- "Gather information about..."
- "What is known about..."
- "Compare..."
- "Trends in..."
- "Technology overview..."
- "Due diligence on..."

### Manual Activation

If the skill doesn't activate automatically, start your message with:

```
/deep-research <your question>
```
or simply mention:
```
Use deep research skill to investigate...
```

---

## Research Depth Levels

Choose the depth based on your needs:

| Depth | Time | Subtasks | Use Case | Cost |
|-------|------|----------|----------|------|
| **Quick** | 30 min | 5-8 | Sanity check, quick overview | Free-$2 |
| **Standard** | 1-2h | 10-15 | Structured analysis | $2-5 |
| **Deep** | 3-5h | 20-30 | Expert research | $5-15 |
| **Exhaustive** | 5+h | 30-50 | Publication-ready | $15-50 |

### How to Specify Depth

```
"Quick research on AI chips 2026"           → Quick
"Standard analysis of RAG market"           → Standard
"Deep research on quantum computing players" → Deep
"Exhaustive due diligence on Company X"     → Exhaustive
```

If not specified, the skill defaults to **Standard**.

---

## Search Routes

The skill automatically selects the best route:

| Route | Description | When Used |
|-------|-------------|-----------|
| **Route A** — Wide Search | Overview, exploratory | Broad topics, trends |
| **Route B** — Focused Search | Specific questions | Product deep-dive, pricing |
| **Route C** — File-Only | Analyze uploaded files | Document analysis |
| **Route D** — File-Augmented | Files + web validation | Benchmarking, validation |

---

## Example Sessions

### Example 1: Quick Market Overview

```
User: "Quick research: тренды в AI-чипах в 2026"

Skill:
✓ Phase 0: Task classified → Route A (Wide), Quick depth
✓ Phase 1: 6 subtasks created
✓ Phase 2: Sources collected (web, news, arXiv)
✓ Phase 3: Facts verified
✓ Phase 4: Synthesis complete
✓ Phase 5: Output generated

--- Executive Summary ---
AI Chip Market Trends 2026
Confidence: 🟢 High (4/5)
Sources: 12 | Facts verified: 23/23

Key Findings:
1. NVIDIA maintains ~80% market share [1,3,7]
2. AMD MI350 shows 15% performance gain [2,5]
3. Custom ASICs from Google/Amazon gaining traction [4,8]
...

--- Full Report Available ---
Type "show full report" for details.
```

### Example 2: Competitive Analysis

```
User: "Конкурентный анализ: RAG-системы на рынке"

Skill:
✓ Phase 0: Route B (Focused), Standard depth
✓ Phase 1: 12 subtasks covering products, pricing, features
✓ Phase 2: 8 sources collected
✓ Phase 3: Cross-verification complete
✓ Phase 4: Comparison matrix built
✓ Phase 5: Competitive report generated

--- Competitive Landscape: RAG Systems ---

| Product | Price | Context | Latency | Score |
|---------|-------|---------|---------|-------|
| Product A | $500/m | 128K | 200ms | 4.2/5 |
| Product B | $200/m | 64K | 350ms | 3.8/5 |
| ... | ... | ... | ... | ... |

[Full analysis with citations]
```

### Example 3: File-Augmented Research

```
User: "Проанализируй этот отчет и найди актуальные данные для сравнения"
[Uploads: report_2025.pdf]

Skill:
✓ Phase 0: Route D (File-Augmented), Deep depth
✓ Phase 1: 18 subtasks (file analysis + web search)
✓ Phase 2: File extracted + 15 web sources
✓ Phase 3: All facts cross-verified
✓ Phase 4: Benchmark analysis complete
✓ Phase 5: Comprehensive report

--- Benchmark Report ---
Uploaded Report (2025) vs. Current Market Data (2026)

Key Changes:
- Market size grew 23% (from $X to $Y) [verified: 3 sources]
- New entrant: Company Z captured 5% share
- Pricing dropped 15% on average

[Full comparison with methodology]
```

---

## Output Formats

The skill produces structured reports with:

### Standard Sections

1. **Executive Summary** — Key findings in 3-5 bullets
2. **Methodology** — Sources, tools, verification method
3. **Findings** — Detailed results with citations
4. **Analysis** — Interpretation and implications
5. **Limitations** — Known gaps and caveats
6. **Sources** — Full citation registry

### Confidence Indicators

Every claim is scored:

| Score | Meaning | How to Interpret |
|-------|---------|------------------|
| 🔵 5/5 | Certain | Multiple authoritative sources agree |
| 🟢 4/5 | High | Authoritative source or strong consensus |
| 🟡 3/5 | Moderate | Limited sources, plausible |
| 🔴 2/5 | Low | Weak evidence, speculative |
| ⚪ 1/5 | Speculative | Inference, needs verification |

---

## Interactive Commands

During research, you can say:

| Command | Action |
|---------|--------|
| "Show full report" | Display complete report |
| "Show methodology" | Explain research approach |
| "Show sources" | List all citations |
| "Go deeper on X" | Expand specific finding |
| "Simplify" | Reduce technical detail |
| "Save report" | Save to file |
| "Stop" | Halt research gracefully |

---

## Best Practices

### For Best Results

1. **Be specific** — "AI chips for training" is better than "AI"
2. **Specify depth** — Add "quick" or "deep" to your request
3. **Upload files** — For analysis of existing documents
4. **Provide context** — Mention industry, timeframe, purpose
5. **Ask follow-ups** — The skill remembers context

### What to Avoid

- **Personal advice** — Skill activates on facts, not opinions
- **Creative writing** — Use other skills for creative tasks
- **Legal consultation** — Research only, not legal advice
- **Therapeutic queries** — Use appropriate resources

### Cost Management

- Start with **Quick** depth for exploration
- Use native tools (Tier 1) — they're free
- Only escalate to premium tools when necessary
- Monitor the cost tracker in heartbeat output

---

## Advanced Features

### Checkpoint Recovery

If research is interrupted:
- Simply re-ask the same question
- The skill resumes from the last checkpoint
- No duplicate work or API calls

### Multi-Agent Coordination

Behind the scenes:
- **Research Agent** — Collects and analyzes sources
- **FactCheck Agent** — Verifies every claim
- **Format Agent** — Structures the final output

All agents report via heartbeat protocol.

### Customization

Advanced users can modify:
- `references/acceptance_framework.md` — Quality thresholds
- `references/tool_matrix.md` — Tool preferences
- `references/cost_matrix_full.md` — Budget limits

---

## Tips and Tricks

1. **Chain research** — "Now compare this with..." continues context
2. **Focus areas** — "Focus on pricing" narrows the research
3. **Time ranges** — "Only 2025-2026 data" filters sources
4. **Exclude sources** — "Exclude blog posts" improves quality
5. **Language** — Works in Russian and English; sources can be multilingual

---

## Getting Help

- Read `SKILL.master.md` for complete technical documentation
- Check `AGENT.MD` for orchestration details
- Review `references/` for tool and methodology guides
- See `CHANGELOG.md` for recent updates
