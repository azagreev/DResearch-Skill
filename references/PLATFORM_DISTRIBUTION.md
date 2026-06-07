# Multi-Platform Distribution Guide

> **Version:** 2.0.0
> **Status:** Production-ready
> **Scope:** Distribution mechanics for Deep Research Skill across all supported AI agent platforms
> **Philosophy:** *One skill, every platform, zero friction*

---

## 1. Platform Overview

### 1.1 Supported Platforms

| # | Platform | Type | Priority | Status | Skill Format |
|---|----------|------|----------|--------|--------------|
| 1 | **Claude Code** | CLI desktop | Primary | Production-ready | `SKILL.md` + `.claude-plugin/` |
| 2 | **Claude.ai** | Web | High | Production-ready | YAML frontmatter in `SKILL.md` |
| 3 | **OpenAI Codex CLI** | CLI | High | Production-ready | `SKILL.md` (Codex format) |
| 4 | **GitHub Copilot** | IDE/Editor | Medium | In review | VS Code extension format |
| 5 | **Cursor** | IDE desktop | Medium | Production-ready | `.cursor/rules/` + `SKILL.md` |
| 6 | **Windsurf** | IDE | Medium | Beta | `.windsurf/rules/` format |

### 1.2 Distribution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Deep Research Skill — Source of Truth              │
│                       SKILL.master.md                           │
├─────────────────────────────────────────────────────────────────┤
│              SKILL.md (Universal Entry Point)                   │
│        YAML frontmatter + Phase structure + References          │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│ Claude Code  │ Claude.ai    │ Codex CLI    │ Cursor / Windsurf  │
│ (.claude-    │ (claude.ai   │ (codex       │ (.cursor/rules/    │
│  plugin/)    │  web plugin) │  skill.md)   │  .windsurf/rules/) │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│ GitHub Copilot (extension)                                      │
│ - VS Code marketplace                                           │
│ - GitHub Copilot Chat integration                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Claude Code (Primary Platform)

### 2.1 Format: `SKILL.md` + `.claude-plugin/`

Claude Code is the **primary target platform**. The skill uses the native Claude Code plugin format.

**File Structure:**
```
.claude-plugin/
├── marketplace.json          # Plugin metadata
└── ...
SKILL.md                      # Main skill file (lean entry point)
SKILL.master.md               # Full documentation (lazy loading)
AGENT.MD                      # Agent protocol
references/                   # On-demand loaded modules
```

### 2.2 SKILL.md Format for Claude Code

```yaml
---
name: deep-research-skill
version: 2.0.0
author: Deep Research Skill Team
last_updated: 2026-06-07
description: |
  Выполняй глубокое исследование по заданной задаче. Собирай информацию
  из множества источников, верифицируй факты, анализируй и выдавай
  структурированный отчёт с citations и confidence scoring.
  Активируй при: "проведи исследование", "deep research", "анализ рынка",
  "конкурентный анализ", "собери информацию о", "что известно о",
  "сравни", "тренды в", "обзор технологий", "due diligence".
  НЕ активируй на: личные советы, терапевтические запросы,
  творческое письмо, юридическая консультация.
min_claude_version: 4.6
runtime: claude.ai
requires_mcp: browserbase (optional), file-system
---
```

### 2.3 marketplace.json Format

```json
{
  "name": "deep-research-skill",
  "version": "2.0.0",
  "description": "Production-grade deep research skill with cost-aware tool routing, multi-model orchestration, and anti-hallucination fact checking",
  "author": "Deep Research Skill Team",
  "license": "MIT",
  "categories": ["research", "productivity", "analysis"],
  "tags": ["deep-research", "fact-checking", "multi-model", "cost-aware", "mcp"],
  "min_claude_version": "4.6",
  "entry_point": "SKILL.md",
  "lazy_loading": {
    "master_doc": "SKILL.master.md",
    "references_dir": "references/",
    "agent_protocol": "AGENT.MD"
  },
  "requires_mcp": [
    {"name": "browserbase", "required": false, "description": "Cloud browser automation"},
    {"name": "file-system", "required": true, "description": "File read/write operations"}
  ],
  "activation_triggers": {
    "positive": [
      "проведи исследование",
      "deep research",
      "анализ рынка",
      "конкурентный анализ",
      "собери информацию о",
      "что известно о",
      "сравни",
      "тренды в",
      "обзор технологий",
      "due diligence"
    ],
    "negative": [
      "личные советы",
      "терапевтические запросы",
      "творческое письмо",
      "юридическая консультация",
      "медицинский диагноз"
    ]
  }
}
```

### 2.4 Installation (Claude Code)

```bash
# Method 1: Install from GitHub repository
claude skill install github.com/your-org/deep-research-skill

# Method 2: Install from local directory
claude skill install ./deep-research-skill

# Method 3: Install from marketplace
claude skill install deep-research-skill

# Verify installation
claude skill list | grep deep-research

# Update
claude skill update deep-research-skill

# Uninstall
claude skill uninstall deep-research-skill
```

### 2.5 Activation in Claude Code

```bash
# The skill auto-activates on matching triggers:
claude "проведи исследование рынка AI-агентов"
claude "deep research on quantum computing trends"
claude "анализ конкурентов для стартапа в EdTech"

# Manual activation (if auto-detection fails):
claude skill run deep-research-skill "your research query"
```

---

## 3. Claude.ai (Web)

### 3.1 Format: Web Plugin

Claude.ai web platform supports skills via the Projects feature with custom instructions.

**Distribution Method:**
- Upload `SKILL.md` as Project instructions
- Full documentation (`SKILL.master.md`) available for reference
- AGENT.MD protocol runs in the background

### 3.2 SKILL.md Adaptation for Claude.ai

The same `SKILL.md` works on Claude.ai with these adaptations:

| Feature | Claude Code | Claude.ai (Web) |
|---------|-------------|-----------------|
| YAML frontmatter | Supported | Supported ( Projects ) |
| MCP servers | Desktop config | Project-level config |
| File system access | Full access | Project files only |
| Browser tools | Native | Limited (screenshot) |
| Agent protocol (AGENT.MD) | Full | Heartbeat simplified |
| Cost tracking | Full | Estimation only |

### 3.3 Installation (Claude.ai Web)

```
1. Navigate to claude.ai
2. Create a new Project (or open existing)
3. Click "Project Settings" → "Custom Instructions"
4. Copy-paste the contents of SKILL.md into the instructions field
5. Upload SKILL.master.md and AGENT.MD as project files
6. Upload references/ directory files for lazy loading
7. Save and start a new conversation in the project
```

### 3.4 Web-Specific Limitations

| Limitation | Workaround |
|------------|------------|
| No direct file system | Use project file upload/download |
| No persistent heartbeat | Use conversation state as checkpoint |
| No MCP server access | Use built-in web search + browsing |
| Browser automation limited | Rely on web_search + user-provided content |
| Cost tracking simplified | Manual budget annotation in conversation |

---

## 4. OpenAI Codex CLI

### 4.1 Format: Codex Skill Markdown

Codex CLI uses a similar markdown-based skill system with OpenAI-specific conventions.

**Required Adaptations:**
- Rename YAML frontmatter keys to Codex format
- Convert phase structure to Codex "modes"
- Replace Claude-specific tool references with Codex equivalents

### 4.2 SKILL.md Format for Codex CLI

```markdown
---
name: deep-research-skill
version: 2.0.0
author: Deep Research Skill Team
description: |
  Conduct deep research on any topic. Collect information from multiple sources,
  verify facts, analyze data, and produce structured reports with citations
  and confidence scoring.
type: skill
---

# Deep Research Skill

## Activation Triggers
- "research" | "deep research" | "investigate" | "analyze" | "due diligence"
- "market analysis" | "competitive analysis" | "technology review"

## Deactivation Triggers
- Personal advice | Therapy | Creative writing | Legal consultation

## Execution Modes

### Mode: Planning
On research request:
1. Parse user intent → define Acceptance Criteria (SMART-R)
2. Select Route (A: Search | B: Deep | C: Comparison | D: Emergency)
3. Assess Depth (Quick | Standard | Deep | Exhaustive)
4. Estimate budget using Cost Estimation Calculator

### Mode: Decomposition
1. Break task into atomic subtasks (single intent, single domain, deterministic output)
2. Define dependency graph: STRICT | SOFT | NONE | FEEDBACK
3. Plan parallel groups (max 5 concurrent)

### Mode: Collection
Follow tool hierarchy (cheapest first):
- Tier 1: web_search, browser_visit, ipython (free)
- Tier 2: Jina Reader, data source APIs (low-cost)
- Tier 3: Firecrawl, Serper (mid-range)
- Tier 4: Browserbase, CAPTCHA solving (enterprise)

### Mode: Verification
1. FactCheck Agent validates every claim
2. Cross-source verification (min 2 independent sources)
3. Source Authority scoring (Tier S/A/B/C/D)
4. Confidence scoring (1-5 scale)

### Mode: Synthesis
1. Aggregate findings by confidence level
2. Resolve conflicts (Tier S > Tier A > freshness > independence)
3. Apply output format template
4. Run Quality Gates G1-G5

### Mode: Delivery
1. Progressive disclosure: summary → findings → details
2. Citation registry with numbered references
3. Confidence visualization in header
4. Disclaimer for unverified claims

## References
- AGENT.MD: Agent protocol for recovery and checkpoints
- SKILL.master.md: Full documentation
- references/: On-demand loaded modules
```

### 4.3 Installation (OpenAI Codex CLI)

```bash
# Method 1: Install from GitHub
codex skill install https://github.com/your-org/deep-research-skill

# Method 2: Local install
codex skill install ./deep-research-skill/SKILL.md

# Method 3: Add to Codex config directory
mkdir -p ~/.config/codex/skills
cp ./deep-research-skill/SKILL.md ~/.config/codex/skills/deep-research.md

# Verify
codex skill list

# Usage
codex "research quantum computing market trends"
```

### 4.4 Codex-Specific Tool Mapping

| Claude Tool | Codex Equivalent | Notes |
|-------------|-----------------|-------|
| `mshtools-web_search` | `web_search` | Native |
| `mshtools-browser_visit` | `browser` | Codex browser tool |
| `mshtools-ipython` | `python` | Code execution |
| `mshtools-shell` | `shell` | Shell commands |
| `mshtools-read_file` | `read` | File reading |
| `mshtools-write_file` | `write` | File writing |
| `AGENT.MD` | `codex.md` | Agent protocol file |

---

## 5. GitHub Copilot

### 5.1 Format: VS Code Extension + Custom Instructions

GitHub Copilot supports custom instructions via `.github/copilot-instructions.md` and VS Code settings.

### 5.2 SKILL.md Adaptation for Copilot

```markdown
# Deep Research Skill — GitHub Copilot Edition

## Role
You are a Deep Research Agent specializing in comprehensive topic investigation.

## Instructions
When user asks for research, analysis, or investigation:

1. **Clarify Intent**: Confirm scope, depth, and output format
2. **Plan**: Create structured research plan with milestones
3. **Collect**: Use available tools in cost order:
   - web_search (free)
   - browser_visit (free)
   - ipython/code execution (free)
   - APIs (if configured)
4. **Verify**: Cross-reference facts, cite sources, score confidence
5. **Synthesize**: Produce structured report with citations

## Output Formats
- Research Report (full)
- Executive Brief (summary)
- Fact Sheet (key facts only)
- Comparison Matrix (side-by-side)
- Timeline (chronological)
- Annotated Bibliography (sources)

## Quality Rules
- Every claim needs a citation
- Minimum 2 independent sources per fact
- Source tiers: S (primary) > A (authoritative) > B (reputable) > C (general) > D (unverified)
- Flag unverified claims with confidence score
- Never fabricate information
```

### 5.3 Installation (GitHub Copilot)

```bash
# Method 1: Repository-level instructions
cat > .github/copilot-instructions.md << 'EOF'
# Deep Research Skill
[Insert adapted SKILL.md content here]
EOF

# Method 2: VS Code User Settings (global)
# Add to VS Code settings.json:
{
  "github.copilot.chat.customInstructions": [
    {
      "text": "# Deep Research Skill\n[skill instructions]",
      "description": "Deep Research Skill"
    }
  ]
}

# Method 3: VS Code Extension (workspaces)
# Create .vscode/settings.json:
{
  "github.copilot.advanced": {
    "instructionFiles": [".github/copilot-instructions.md"]
  }
}
```

### 5.4 Copilot-Specific Considerations

| Feature | Claude Code | Copilot | Workaround |
|---------|-------------|---------|------------|
| YAML frontmatter | Supported | Not supported | Use markdown headers |
| MCP servers | Full | Limited | Use Copilot extensions |
| Agent protocol | Full | Not supported | Manual checkpointing |
| Cost tracking | Full | Not supported | Manual annotation |
| File operations | Full | Workspace only | Use workspace files |
| Lazy loading | Full | Not supported | Inline key content |

---

## 6. Cursor

### 6.1 Format: `.cursor/rules/` + `SKILL.md`

Cursor supports custom rules via the `.cursor/rules/` directory. Rules can be project-specific or global.

### 6.2 File Structure for Cursor

```
.cursor/
└── rules/
    └── deep-research.mdc    # Cursor rule file
SKILL.md                      # Main skill (shared)
SKILL.master.md               # Full documentation
```

### 6.3 `.cursor/rules/deep-research.mdc` Format

```markdown
---
description: Deep Research Skill — comprehensive research with cost-aware routing
alwaysApply: false  # Only apply when triggered
globs: []           # Apply to all files
---

# Deep Research Skill

## Activation
Activate when user mentions: research, deep research, analysis, investigate, due diligence, market analysis, competitive analysis, technology review

## Workflow

### Phase 1: Planning
- Parse user intent and define acceptance criteria
- Select route (A/B/C/D) and depth (Quick/Standard/Deep/Exhaustive)
- Estimate cost and set budget

### Phase 2: Decomposition
- Break into atomic subtasks
- Build dependency graph
- Plan parallel execution (max 5 concurrent)

### Phase 3: Collection
Follow tool hierarchy (cheapest first):
1. web_search, browser_visit, ipython (free)
2. Jina Reader, data APIs (low-cost)
3. Firecrawl, Serper (mid-range)
4. Browserbase, CAPTCHA solving (enterprise)

### Phase 4: Verification
- Cross-source fact checking
- Source authority scoring (S/A/B/C/D)
- Confidence scoring (1-5)

### Phase 5: Synthesis
- Aggregate by confidence
- Resolve conflicts
- Apply output format
- Quality gates G1-G5

### Phase 6: Delivery
- Progressive disclosure
- Citation registry
- Confidence header
- Disclaimer for unverified claims

## Quality Rules
- Every claim must have a citation
- Minimum 2 independent sources
- Tier S > Tier A > freshness > independence > quantity
- Flag unverified claims
- Never hallucinate

## Output Formats
Research Report | Executive Brief | Fact Sheet | Comparison Matrix | Timeline | Annotated Bibliography

## References
- Full docs: SKILL.master.md
- Agent protocol: AGENT.MD
- Lazy-loaded modules: references/
```

### 6.4 Installation (Cursor)

```bash
# Method 1: Project-level rules (recommended)
mkdir -p .cursor/rules
cp references/PLATFORM_DISTRIBUTION.md .cursor/rules/deep-research.mdc

# Method 2: Global rules
cp .cursor/rules/deep-research.mdc ~/.cursor/rules/

# Method 3: Cursor marketplace (future)
# Cursor > Settings > Rules > Install from marketplace
# Search: "deep-research-skill"

# Activation in Cursor
cmd+k "research quantum computing trends"
# or
@deep-research "analyze competitive landscape for AI coding assistants"
```

---

## 7. Windsurf

### 7.1 Format: `.windsurf/rules/`

Windsurf (by Codeium) supports custom rules via the `.windsurf/rules/` directory, similar to Cursor.

### 7.2 `.windsurf/rules/deep-research.md` Format

```markdown
# Deep Research Skill — Windsurf Edition

## Activation
research | deep research | analyze | investigate | due diligence

## Instructions
When activated, follow this workflow:

1. **Plan**: Clarify intent, set AC, choose route+depth, estimate budget
2. **Decompose**: Atomic subtasks, dependency graph, parallel groups
3. **Collect**: Cheapest tools first (web_search → browser → APIs → premium)
4. **Verify**: Cross-source facts, authority tiers, confidence scores
5. **Synthesize**: Aggregate, resolve conflicts, apply format, quality gates
6. **Deliver**: Progressive disclosure, citations, confidence header

## Rules
- Every claim: citation required
- Min 2 sources per fact
- Authority: S > A > B > C > D
- Confidence: 1-5 scale
- No hallucination
- Progressive disclosure

## Tools (by priority)
1. web_search (free)
2. browser_visit (free)
3. ipython (free)
4. Jina Reader (free/low-cost)
5. Firecrawl (mid-range)
6. Browserbase (premium)
```

### 7.3 Installation (Windsurf)

```bash
# Method 1: Project rules
mkdir -p .windsurf/rules
cp ./deep-research-skill/references/windsurf_rules.md .windsurf/rules/deep-research.md

# Method 2: Global rules
mkdir -p ~/.windsurf/rules
cp .windsurf/rules/deep-research.md ~/.windsurf/rules/

# Activation
# Use Cascade chat: "research topic X"
# Rules auto-apply on activation triggers
```

---

## 8. Compatibility Matrix

### 8.1 Feature Compatibility

| Feature | Claude Code | Claude.ai | Codex CLI | Copilot | Cursor | Windsurf |
|---------|:-----------:|:---------:|:---------:|:-------:|:------:|:--------:|
| YAML frontmatter | Yes | Yes | Partial | No | No | No |
| Native skill format | Yes | Yes | Yes | Partial | Yes (rules) | Yes (rules) |
| MCP servers | Yes | Limited | Partial | No | No | No |
| Agent protocol (AGENT.MD) | Full | Simplified | No | No | No | No |
| Cost tracking | Full | Estimation | No | No | No | No |
| Tool hierarchy | Full | Full | Full | Partial | Partial | Partial |
| Lazy loading | Full | Full | No | No | No | No |
| Heartbeat/checkpoint | Full | Simplified | No | No | No | No |
| Quality gates | Full | Full | Partial | Partial | Partial | Partial |
| File operations | Full | Project | Full | Workspace | Workspace | Workspace |
| Plugin marketplace | Yes | No | No | VS Code | Future | No |

### 8.2 Tool Availability Matrix

| Tool | Claude Code | Claude.ai | Codex CLI | Copilot | Cursor | Windsurf |
|------|:-----------:|:---------:|:---------:|:-------:|:------:|:--------:|
| web_search | Yes | Yes | Yes | Yes | No | No |
| browser_visit | Yes | Limited | Yes | No | No | No |
| ipython | Yes | Yes | Yes | No | No | No |
| shell | Yes | No | Yes | No | No | No |
| file read/write | Yes | Yes | Yes | Yes | Yes | Yes |
| image generation | Yes | Yes | Yes | No | No | No |
| data sources | Yes | Yes | Yes | No | No | No |
| browser automation | Yes | No | No | No | No | No |
| code execution | Yes | Yes | Yes | No | No | No |

### 8.3 Format Conversion Guide

| From → To | Method | Effort |
|-----------|--------|--------|
| Claude Code → Claude.ai | Direct (same format) | None |
| Claude Code → Codex CLI | Convert YAML frontmatter | Low |
| Claude Code → Copilot | Extract instructions, no YAML | Medium |
| Claude Code → Cursor | Convert to .mdc rule format | Low |
| Claude Code → Windsurf | Convert to .md rule format | Low |
| Cursor ↔ Windsurf | Direct (similar format) | None |

---

## 9. Unified Distribution Strategy

### 9.1 Primary Distribution Flow

```
                    GitHub Repository (source of truth)
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
     Claude Code        Claude.ai Web        Codex CLI
     (native plugin)   (Projects)           (skill install)
          │                   │                   │
    ┌─────┴─────┐            │            ┌─────┴─────┐
    │           │            │            │           │
  Cursor    Windsurf     Copilot     Marketplace  Manual
  (rules)   (rules)    (instructions)  (future)    (copy-paste)
```

### 9.2 Release Checklist

| Step | Action | Platform |
|------|--------|----------|
| 1 | Update SKILL.md with new version | All |
| 2 | Update `.claude-plugin/marketplace.json` | Claude Code |
| 3 | Tag release on GitHub | All |
| 4 | Test on Claude Code | Claude Code |
| 5 | Update Project instructions template | Claude.ai |
| 6 | Convert and test on Codex CLI | Codex CLI |
| 7 | Update `.cursor/rules/` | Cursor |
| 8 | Update `.windsurf/rules/` | Windsurf |
| 9 | Update `.github/copilot-instructions.md` | Copilot |
| 10 | Announce on release channels | All |

### 9.3 Version Management

| Platform | Version Source | Update Frequency |
|----------|---------------|-----------------|
| Claude Code | `SKILL.md` frontmatter + marketplace.json | Per release |
| Claude.ai | `SKILL.md` frontmatter | Per release |
| Codex CLI | `SKILL.md` frontmatter | Per release |
| Copilot | Copilot-instructions.md header | Per release |
| Cursor | `.mdc` file frontmatter | Per release |
| Windsurf | `.md` file header | Per release |

All platforms should update simultaneously when `SKILL.md` version changes. The `CHANGELOG.md` documents all platform-specific changes.

---

*Multi-Platform Distribution v2.0.0 — Deep Research Skill is available on Claude Code (primary), Claude.ai, OpenAI Codex CLI, GitHub Copilot, Cursor, and Windsurf. One skill source, every platform, zero friction.*
