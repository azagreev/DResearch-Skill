# Deep Research Skill

> Production-ready deep research skill for Claude Desktop. Multi-phase workflow with cost-first execution, evidence-based reporting, and anti-hallucination protocols.

**Version:** 2.0.0 | **License:** MIT | **Language:** Russian

---

## Features

- **6-Phase Workflow**: Task Analysis → Decomposition → Collection → Fact-Checking → Synthesis → Output
- **Cost-First Execution**: 4-tier tool hierarchy — start free, escalate only when necessary
- **Evidence-Based Reporting**: Every claim has a citation, every source has a tier
- **Anti-Hallucination Protocol**: Zero tolerance — FactCheck Agent vets every fact
- **4 Depth Levels**: Quick (30 min) → Standard (1-2h) → Deep (3-5h) → Exhaustive (5+h)
- **Confidence Scoring**: 1-5 scale with visual indicators for every claim
- **Checkpoint Recovery**: Heartbeat every 30s — never lose progress
- **50+ Tools**: Comprehensive tool matrix with cost/quality/authority ratings

---

## Quick Start

### Installation via Claude Code CLI

```bash
# Install the skill directly from the repository
npx skills add <path-to-repo>/plugins/deep-research-skill

# Example with local clone:
git clone https://github.com/deep-research-skill/deep-research-skill.git
npx skills add ./deep-research-skill/plugins/deep-research-skill
```

### Installation via Claude Marketplace

1. Open Claude Code
2. Navigate to Skills Marketplace
3. Search for "deep-research-skill"
4. Click **Install**

### Post-Installation Setup

```bash
# Create output directory for research artifacts
mkdir -p ./research_output/{heartbeats,subtasks,sources,reports}

# Optional: Set environment variables for external APIs
export BROWSERBASE_API_KEY="your-key"      # Optional - cloud browser
export JINA_API_KEY="your-key"             # Optional - article extraction
export FIRECRAWL_API_KEY="your-key"        # Optional - web scraping
```

---

## Usage

### Activation Triggers

The skill activates automatically on phrases like:

- "Проведи исследование..." / "Deep research on..."
- "Анализ рынка..." / "Market analysis..."
- "Конкурентный анализ..." / "Competitive analysis..."
- "Собери информацию о..." / "Gather information on..."
- "Что известно о..." / "What is known about..."
- "Сравни..." / "Compare..."
- "Тренды в..." / "Trends in..."
- "Обзор технологий..." / "Technology overview..."
- "Due diligence..."

### Example Sessions

**Quick Research:**
```
User: "Проведи исследование трендов в AI-чипах 2026"
→ Quick depth (30 min, 5-8 subtasks)
→ Executive summary + key findings
```

**Deep Research:**
```
User: "Deep research: рынок RAG-систем, конкуренты, цены, тренды"
→ Deep depth (3-5 hours, 20-30 subtasks)
→ Full report with methodology, analysis, implications
```

**File-Augmented Research:**
```
User: "Проанализируй эти отчеты и найди в вебе актуальные данные для сравнения"
→ Route D: File-Augmented
→ Upload analysis + web validation + benchmarking
```

---

## Architecture

```
SKILL.md (entry point)
  ├── Phase 0: Task Analysis → strategy_guide.md
  ├── Phase 1: Decomposition → decomposition_guide.md
  ├── Phase 2: Collection → tool_matrix.md
  ├── Phase 3: Fact-Checking → factcheck_system.md
  ├── Phase 4: Synthesis → output_formats.md
  └── Phase 5: Output → acceptance_framework.md

AGENT.MD (orchestration layer)
  ├── Heartbeat Protocol (every 30s)
  ├── Checkpoint Recovery
  ├── Quality Gates
  └── Cost Tracking

References (18 documents):
  ├── Core: tool_matrix, strategy_guide, decomposition_guide, acceptance_framework
  ├── Output: output_formats, factcheck_system, source_authority_framework, cost_matrix
  ├── Analysis: competitive_landscape
  └── Research: jina_reader, bypass_paywall, ecc, modelsdev, captcha,
                 academic_skills, skill_marketplace, browserbase, prompt_master
```

---

## Repository Structure

```
deep-research-skill/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace metadata
├── plugins/
│   └── deep-research-skill/
│       └── SKILL.md              # Skill entry point (main)
├── AGENT.MD                      # Agent orchestration protocol
├── SKILL.master.md               # Complete master documentation
├── LEGAL_METHODS.md              # Ethical legal bypass techniques
├── CAPTCHA_MODULE.md             # CAPTCHA handling strategies
├── GRAY_METHODS.md               # ⚠️ Separate document (NOT in skill bundle)
├── CHANGELOG.md                  # Version history
├── LICENSE                       # MIT License
├── README.md                     # This file
├── references/                   # 18 reference documents
│   ├── tool_matrix.md
│   ├── strategy_guide.md
│   ├── decomposition_guide.md
│   ├── acceptance_framework.md
│   ├── output_formats.md
│   ├── factcheck_system.md
│   ├── source_authority_framework.md
│   ├── cost_matrix_full.md
│   ├── competitive_landscape.md
│   ├── jina_reader_research.md
│   ├── bypass_paywall_research.md
│   ├── ecc_research.md
│   ├── modelsdev_research.md
│   ├── captcha_research.md
│   ├── academic_skills_research.md
│   ├── skill_marketplace_research.md
│   ├── browserbase_research.md
│   └── prompt_master_research.md
└── docs/                         # Additional documentation (optional)
```

---

## Tool Tiers

| Tier | Tools | Cost | Coverage |
|------|-------|------|----------|
| **Tier 1** | Native Claude tools (web_search, browser) | Free | ~70% tasks |
| **Tier 2** | Jina AI Reader, arXiv, Scholar | Free/low | ~20% tasks |
| **Tier 3** | Browserbase, ECC, PubMed | Low/medium | ~8% tasks |
| **Tier 4** | Firecrawl, premium APIs | Premium | ~2% tasks |

See `references/cost_matrix_full.md` for detailed pricing.

---

## Confidence Scale

| Score | Level | Indicator | Usage |
|-------|-------|-----------|-------|
| 5 | Certain | 🔵 | Verified by multiple Tier S sources |
| 4 | High | 🟢 | Single Tier S or multiple Tier A |
| 3 | Moderate | 🟡 | Industry consensus, no direct source |
| 2 | Low | 🔴 | Limited/weak sources |
| 1 | Speculative | ⚪ | Inference, no direct evidence |

---

## Source Authority Tiers

| Tier | Source Type | Trust Level |
|------|-------------|-------------|
| **S** | SEC filings, regulators, primary data | Ground truth |
| **A** | Reputable media, peer-reviewed journals | High |
| **B** | Industry reports, established blogs | Medium |
| **C** | News aggregators, press releases | Low-medium |
| **D** | Forums, social media | Low (verify first) |

---

## Requirements

- **Claude Desktop** ≥ 4.6
- **Runtime**: claude.ai
- **MCP Servers** (optional):
  - `browserbase` — cloud browser automation
  - `file-system` — local file operations

---

## Cost Estimates

| Depth | Time | Subtasks | Est. Cost (APIs) |
|-------|------|----------|-----------------|
| Quick | 30 min | 5-8 | $0-2 |
| Standard | 1-2h | 10-15 | $2-5 |
| Deep | 3-5h | 20-30 | $5-15 |
| Exhaustive | 5+h | 30-50 | $15-50 |

> Note: Costs are for external APIs only. Native Claude tools are free. Actual costs depend on tool selection and source availability.

---

## Safety & Ethics

- All legal bypass methods follow ETHICAL_ONLY scope
- CAPTCHA handling uses human-in-the-loop escalation
- Source authority awareness prevents misinformation spread
- Confidence scoring prevents overstatement of weak claims
- No automated exploitation — all techniques are documented for transparency

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/name`
3. Make changes following the existing style
4. Test with actual research tasks
5. Submit a pull request

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Built for Claude Desktop ecosystem
- Inspired by production research workflows at leading AI labs
- Tool research based on extensive benchmarking (see `references/`)
- Community feedback and contributions welcome
