# Prompt Master Deep Research: Extracted Patterns for Deep Research Skill

> **Research Date:** 2026-06-30
> **Source:** https://github.com/nidhinjs/prompt-master
> **Version Analyzed:** 1.6.0
> **Stars:** 8.9k | **Forks:** 1k | **License:** MIT

---

## Table of Contents

1. [Prompt Master Overview](#1-prompt-master-overview)
2. [Architecture Analysis](#2-architecture-analysis)
3. [Prompt Engineering Patterns](#3-prompt-engineering-patterns)
4. [Prompt Management System](#4-prompt-management-system)
5. [Research-Specific Prompts](#5-research-specific-prompts)
6. [Claude Integration Patterns](#6-claude-integration-patterns)
7. [Extractable Patterns with Value Assessment](#7-extractable-patterns-with-value-assessment)
8. [Prompt Library for Deep Research](#8-prompt-library-for-deep-research)
9. [Top-5 Most Valuable Patterns](#9-top-5-most-valuable-patterns)
10. [Implementation Recommendations](#10-implementation-recommendations)

---

## 1. Prompt Master Overview

### What is Prompt Master?

**Prompt Master** — это Claude Skill (плагин для Claude Desktop), который генерирует оптимизированные промпты для любого AI-инструмента. Проект создан для устранения главной проблемы пользователей AI: цикла "размытый промпт -> неправильный результат -> переспрашивание -> ...".

### Core Mission

> *"The best prompt is not the longest. It's the one where every word is load-bearing."*

Большинство "генераторов промптов" делают промпты длиннее. Prompt Master делает их **точнее**.

### Key Metrics

| Metric | Value |
|--------|-------|
| GitHub Stars | 8.9k |
| Forks | 1k |
| Contributors | 5 |
| Commits | 49 |
| Tool Profiles | 30+ |
| Prompt Templates | 13 (A-M) |
| Anti-Patterns Detected | 37 |
| Safe Techniques | 5 |
| Version | 1.6.0 |

### Scope of Support

Prompt Master поддерживает **30+ AI-инструментов** across categories:

- **Reasoning LLMs:** Claude, ChatGPT/GPT-5.x, Gemini, o3/o4-mini, Qwen, DeepSeek-R1, MiniMax
- **Agentic AI:** Claude Code, Devin, Manus
- **IDE AI:** Cursor, Windsurf, Cline, GitHub Copilot, Antigravity
- **Full-stack Generators:** Bolt, v0, Lovable, Figma Make, Google Stitch
- **Image AI:** Midjourney, DALL-E 3, Stable Diffusion, ComfyUI, SeeDream
- **Video AI:** Sora, Runway, Kling, LTX Video, Dream Machine
- **3D AI:** Meshy, Tripo, Rodin, Unity AI, BlenderGPT
- **Voice AI:** ElevenLabs
- **Workflow AI:** Zapier, Make, n8n
- **Computer-Use Agents:** Perplexity Comet, OpenAI Atlas, OpenClaw

### How It Works (7-Step Pipeline)

1. **Detects target tool** — определяет, для какой AI-системы пишется промпт
2. **Extracts 9 dimensions of intent** — task, input, output, constraints, context, audience, memory, success criteria, examples
3. **Asks clarifying questions** — максимум 3 вопроса, если не хватает критической информации
4. **Routes to the right framework** — выбирает правильный шаблон автоматически
5. **Applies safe techniques only** — role assignment, few-shot, XML structure, grounding anchors, memory block
6. **Runs token efficiency audit** — удаляет каждое слово, не влияющее на результат
7. **Delivers the prompt** — один готовый к копированию блок с однострочной стратегией

---

## 2. Architecture Analysis

### File Structure

```
prompt-master/
├── README.md              # Документация, примеры, overview
├── SKILL.md               # Основной skill-файл для Claude (448 lines, 25.7 KB)
├── LICENSE                # MIT
└── references/
    ├── templates.md       # 13 шаблонов (A-M)
    └── patterns.md        # 37 анти-паттернов
```

### SKILL.md Architecture (PAC2026 Positional Structure)

SKILL.md использует **трёхзонную архитектуру**, основанную на принципах позиционного кодирования внимания:

#### PRIMACY ZONE (30%) — Identity, Hard Rules, Output Lock

Размещается в начале файла. Содержит:
- **Identity definition** — кто AI при генерации промптов
- **Hard rules** — абсолютные запреты (никогда не нарушать)
- **Output format lock** — жёстко заданный формат вывода

**Паттерн:** Приоритетные инструкции в начале документа — модель уделяет им больше внимания.

#### MIDDLE ZONE (55%) — Execution Logic, Tool Routing, Diagnostics

Основная логика:
- **Intent Extraction** — 9 измерений намерения пользователя
- **Tool Routing** — специфичные инструкции для 30+ инструментов
- **Diagnostic Checklist** — сканирование на 6 категорий ошибок
- **Memory Block** — система контекста для сессий
- **Safe Techniques** — 5 безопасных техник
- **Input Sanitization** — защита от prompt injection

#### RECENCY ZONE (15%) — Verification and Success Lock

Финальная проверка:
- 6 verification questions перед выдачей результата
- Success criteria: *"Zero re-prompts needed. That is the only metric."*

### Reference Files (Lazy Loading)

| File | Read When |
|------|-----------|
| `references/templates.md` | Нужна полная структура шаблона |
| `references/patterns.md` | Пользователь просит исправить плохой промпт |

**Принцип:** Загружать только нужный reference, никогда оба сразу.

---

## 3. Prompt Engineering Patterns

### 3.1 9-Dimension Intent Extraction Framework

Перед написанием любого промпта извлекаются 9 измерений:

| Dimension | What to Extract | Critical? |
|-----------|----------------|-----------|
| **Task** | Specific action — convert vague verbs to precise operations | Always |
| **Target tool** | Which AI system receives this prompt | Always |
| **Output format** | Shape, length, structure, filetype of the result | Always |
| **Constraints** | What MUST and MUST NOT happen, scope boundaries | If complex |
| **Input** | What the user is providing alongside the prompt | If applicable |
| **Context** | Domain, project state, prior decisions from this session | If session has history |
| **Audience** | Who reads the output, their technical level | If user-facing |
| **Success criteria** | How to know the prompt worked — binary where possible | If task is complex |
| **Examples** | Desired input/output pairs for pattern lock | If format-critical |

**Value for Deep Research:** **HIGH** — Этот фреймворк можно напрямую адаптировать для извлечения параметров research-запроса.

### 3.2 13 Prompt Templates (A-M)

| Template | Full Name | Best For | Research Value |
|----------|-----------|----------|----------------|
| **A — RTF** | Role, Task, Format | Fast one-shot tasks | Medium |
| **B — CO-STAR** | Context, Objective, Style, Tone, Audience, Response | Professional documents | **High** |
| **C — RISEN** | Role, Instructions, Steps, End Goal, Narrowing | Complex multi-step projects | **High** |
| **D — CRISPE** | Capacity, Role, Insight, Statement, Personality, Experiment | Creative work | Medium |
| **E — Chain of Thought** | Step-by-step reasoning | Logic, math, analysis | **High** |
| **F — Few-Shot** | Input/output examples | Consistent structured output | **High** |
| **G — File-Scope** | File + Function + Scope | Code editing AI | Medium |
| **H — ReAct + Stop Conditions** | Reasoning + Acting + Stops | Autonomous agents | **High** |
| **I — Visual Descriptor** | Subject/Style/Mood/Lighting | Image generation | Low |
| **J — Reference Image Editing** | Delta-based editing | Image editing | Low |
| **K — ComfyUI** | Positive/Negative split | Node-based workflows | Low |
| **L — Prompt Decompiler** | Break down / Adapt / Split | Analysis of existing prompts | **High** |
| **M — Opus 4.7 Task Brief** | Full task brief | Complex multi-step on Opus 4.7 | **High** |

### 3.3 5 Safe Techniques

Prompt Master использует только техники с надёжным, предсказуемым эффектом:

| Technique | When to Apply | Example |
|-----------|--------------|---------|
| **Role Assignment** | Complex or specialized tasks | Weak: "You are a helpful assistant" → Strong: "You are a senior backend engineer specializing in distributed systems who prioritizes correctness over cleverness" |
| **Few-Shot Examples** | Format easier to show than describe | 2-5 examples, include edge cases, XML tags for wrapping |
| **XML Structural Tags** | Claude-based tools, complex multi-section | `<context>`, `<task>`, `<constraints>`, `<output_format>` |
| **Grounding Anchors** | Factual or citation tasks | "Use only information you are highly confident is accurate. If uncertain, write [uncertain]" |
| **Chain of Thought** | Logic, math, debugging on standard models | "Think through this step by step before answering" |

**Explicitly EXCLUDED (high fabrication risk):**
- Mixture of Experts
- Tree of Thought
- Graph of Thought
- Universal Self-Consistency
- Prompt chaining as layered technique

### 3.4 Chain-of-Thought (CoT) Pattern

Template E — специализированный шаблон для пошагового рассуждения:

```
[Task statement]

Before answering, think through this carefully:
<thinking>
1. What is the actual problem being asked?
2. What constraints must the solution respect?
3. What are the possible approaches?
4. Which approach is best and why?
</thinking>

Give your final answer in <answer> tags only.
```

**Critical rules:**
- Use ONLY for standard reasoning models (Claude, GPT-4o, Gemini, Qwen2.5, Llama)
- **NEVER** on o1/o3/o4-mini, DeepSeek-R1, Qwen3-thinking — they reason internally, CoT degrades output
- Not needed for simple tasks or creative tasks

### 3.5 Few-Shot Pattern

Template F — обучение на примерах:

```
[Task instruction]

Here are examples of the exact format needed:
<examples>
  <example>
    <input>[example input 1]</input>
    <output>[example output 1]</output>
  </example>
  <example>
    <input>[example input 2]</input>
    <output>[example output 2]</output>
  </example>
</examples>

Now apply this exact pattern to: [actual input]
```

**Rules:**
- 2 to 5 examples — sweet spot
- Include edge cases
- XML tags for надёжного парсинга
- Switch to few-shot после 2 неудачных попыток форматирования

### 3.6 Structured Output Pattern

Используется throughout все шаблоны:
- XML tags для section separation
- Binary acceptance criteria (checkboxes)
- Explicit format locks with labelled examples
- Word/sentence count constraints

### 3.7 Role-Based Prompting

Специфичные роли для разных задач:
- **Research/Orchestration AI** (Perplexity, Manus): specify search vs analyze vs compare, add citation requirements
- **Computer-Use/Browser Agents**: describe outcome, not navigation steps
- **Prompt Engineer** (identity of Prompt Master itself)

### 3.8 Memory Block Pattern

Система сохранения контекста между сессиями:

```
## Context (carry forward)
- Stack and tool decisions established
- Architecture choices locked
- Constraints from prior turns
- What was tried and failed
```

**Placement:** Первые 30% промпта — выживает при attention decay.

### 3.9 Token Efficiency Audit

Проверка перед выдачей:
- Каждое предложение должно быть load-bearing
- Нет vague adjectives
- Format explicit
- Scope bounded
- Every word should change the output

### 3.10 Signal Word Strength

Использование сильнейших сигнальных слов:
- **MUST** over should
- **NEVER** over avoid
- **ONLY** over prefer

---

## 4. Prompt Management System

### 4.1 Versioning System

| Version | Changes |
|---------|---------|
| 1.6.0 | Opus 4.7 update, Template M, patterns 36-37 |
| 1.5.0 | More tool routing, Agentic AI, 3D Model AI |
| 1.4.0 | Reference image editing, ComfyUI, Prompt Decompiler |
| 1.3.0 | PAC2026 positional structure, silent routing |
| 1.2.0 | Attention architecture, removed fabrication-prone techniques |
| 1.1.0 | Expanded tool coverage, memory block, 35 patterns |
| 1.0.0 | Initial release |

### 4.2 Organization & Categorization

**Templates organized by use case:**
- Simple tasks → RTF (A)
- Professional docs → CO-STAR (B)
- Complex projects → RISEN (C)
- Creative work → CRISPE (D)
- Logic/analysis → CoT (E)
- Format consistency → Few-Shot (F)
- Code editing → File-Scope (G)
- Autonomous agents → ReAct + Stop Conditions (H)
- Image generation → Visual Descriptor (I)
- Image editing → Reference Editing (J)
- Node workflows → ComfyUI (K)
- Prompt analysis → Decompiler (L)
- Opus 4.7 tasks → Task Brief (M)

**Patterns organized by failure category:**
- Task Patterns (7) — vague verbs, dual tasks, no success criteria
- Context Patterns (6) — assumed knowledge, hallucination invites
- Format Patterns (6) — missing format, implicit length, no role
- Scope Patterns (6) — no boundaries, no stop conditions, wrong template
- Reasoning Patterns (5) — missing CoT, CoT on reasoning models
- Agentic Patterns (7) — no starting/target state, silent agent, unlocked filesystem

### 4.3 Reusability Patterns

1. **Silent Routing** — шаблон выбирается автоматически, пользователь не видит название
2. **Lazy Loading** — reference-файлы загружаются только по необходимости
3. **Conditional Activation** — skill активируется только при явном запросе на работу с промптами
4. **Template Composition** — базовые шаблоны комбинируются с tool-specific дополнениями
5. **Progressive Enhancement** — простые техники предпочтительнее сложных

---

## 5. Research-Specific Prompts

### 5.1 Existing Research-Related Routing in Prompt Master

Prompt Master уже содержит специфичные инструкции для research-инструментов:

**Perplexity / SearchGPT:**
- Specify search vs analyze vs compare
- Add citation requirements
- Reframe hallucination-prone questions as grounded queries

**Manus / Perplexity Computer (multi-agent orchestrators):**
- Describe the end deliverable, not the steps
- They decompose internally
- Specify output artifact type (report / spreadsheet / code / summary)
- Add "Flag any data point you are not confident about"
- For long multi-step tasks: add verification checkpoints

**Computer-Use / Browser Agents (Perplexity Comet, OpenAI Atlas):**
- Describe the outcome, not navigation steps
- Specify constraints explicitly
- Add permission boundaries: "Do not make any purchase. Research only."
- Add stop condition for irreversible actions

### 5.2 Adaptable Patterns for Deep Research

#### A. Task Decomposition (from RISEN Template C)
```
Role: [Expert researcher in domain X]
Instructions: [Research question or objective]
Steps:
  1. [Information gathering — sources to consult]
  2. [Data extraction — what to extract from each source]
  3. [Analysis — how to analyze the extracted data]
  4. [Synthesis — how to combine findings]
  5. [Validation — fact-checking and verification]
End Goal: [What the final deliverable must achieve]
Narrowing: [Scope limits, sources to exclude, time boundaries]
```

#### B. Source Evaluation (from Grounding Anchors)
```
For each source, evaluate:
- Authority: [primary, secondary, tertiary]
- Recency: [publication date vs topic timeline]
- Bias: [known bias of source]
- Corroboration: [how many other sources confirm this]

Flag uncertain claims with [uncertain].
Never fabricate citations or statistics.
```

#### C. Structured Research Output (from CO-STAR Template B)
```
Context: [Research domain, existing knowledge, gap being addressed]
Objective: [Specific research question]
Style: [Academic / Technical / Executive summary]
Tone: [Neutral / Critical / Balanced]
Audience: [Technical experts / Business stakeholders / General public]
Response: [Format: structured report with sections, word count, citations]
```

#### D. Fact-Checking Protocol (from Few-Shot Template F)
```
Task: Evaluate the factual accuracy of the following claims.

For each claim, output:
<fact_check>
  <claim>[exact claim]</claim>
  <verdict>CONFIRMED / PARTIALLY_CONFIRMED / DISPUTED / UNVERIFIABLE</verdict>
  <sources>[supporting sources or "none found"]</sources>
  <confidence>HIGH / MEDIUM / LOW</confidence>
  <notes>[explanation]</notes>
</fact_check>
```

#### E. Confidence Scoring (from Diagnostic Checklist)
```
Confidence levels:
- HIGH: Multiple authoritative sources confirm, no contradictions
- MEDIUM: Limited sources or minor contradictions exist
- LOW: Single source or significant conflicting information
- UNVERIFIABLE: Cannot be confirmed with available sources

Apply to every factual assertion in the output.
```

---

## 6. Claude Integration Patterns

### 6.1 Skill Installation

**Recommended:** Claude.ai (browser)
1. Download repo as ZIP
2. claude.ai → Sidebar → Customize → Skills → Upload a Skill

**Alternative:** Claude Code
```bash
mkdir -p ~/.claude/skills
git clone https://github.com/nidhinjs/prompt-master.git ~/.claude/skills/prompt-master
```

### 6.2 Activation Pattern

Skill активируется **только** при явном запросе:
- "Write me a prompt for..."
- "Fix this prompt..."
- "Adapt this for..."

**Does NOT activate** для: general conversation, coding tasks, document writing.

### 6.3 Claude-Specific Prompting Rules (from Tool Routing)

**Claude 4.x / Opus 4.7:**
- Be explicit and specific — follows instructions literally
- XML tags for complex prompts: `<context>`, `<task>`, `<constraints>`, `<output_format>`
- Opus 4.x over-engineers by default — add "Only make changes directly requested"
- Provide WHY, not just WHAT — generalizes better from explanations
- Do NOT add "think step by step" — uses adaptive thinking
- Front-load everything in one turn for complex tasks
- Use Template M for agentic or multi-step tasks

**Claude Code:**
- Agentic — runs tools, edits files, executes commands
- Stop conditions are MANDATORY
- Starting state + target state + allowed actions + forbidden actions
- Session hygiene: new task = new session, /rewind, /compact at ~50%
- Human review triggers: "Stop and ask before deleting any file..."

### 6.4 Output Format for Claude

```
[prompt block]

🎯 Target: [tool name]
💡 [One sentence — what was optimized and why]
```

### 6.5 Best Practices for System Prompts (Extracted)

1. **Primacy Zone** — самые важные инструкции в начале
2. **Hard Rules** — абсолютные запреты, чётко выделенные
3. **Output Format Lock** — жёстко заданный формат вывода
4. **Silent Processing** — фреймворки не показываются пользователю
5. **Token Efficiency** — каждое слово должно нести нагрузку
6. **Recency Verification** — финальная проверка перед выдачей

---

## 7. Extractable Patterns with Value Assessment

### High Value Patterns (directly reusable)

| # | Pattern | Source | Adaptation Needed | Integration Point |
|---|---------|--------|-------------------|-------------------|
| 1 | **9-Dimension Intent Extraction** | SKILL.md Intent Extraction | Low — adapt dimensions for research queries | Query parsing module |
| 2 | **RISEN Template (C)** | references/templates.md | Low — change steps to research phases | Task decomposition engine |
| 3 | **CO-STAR Template (B)** | references/templates.md | Low — adapt for research report formatting | Report generation |
| 4 | **Chain of Thought (E)** | references/templates.md | None — use as-is for analysis tasks | Analysis agent |
| 5 | **Few-Shot Template (F)** | references/templates.md | Low — create research-specific examples | Format consistency |
| 6 | **ReAct + Stop Conditions (H)** | references/templates.md | Medium — adapt for research workflow control | Agent orchestration |
| 7 | **Grounding Anchors** | SKILL.md Safe Techniques | Low — add research-specific grounding rules | Fact-checking module |
| 8 | **Memory Block Pattern** | SKILL.md Memory Block | Low — adapt for research session context | Context management |
| 9 | **Diagnostic Checklist** | SKILL.md Diagnostics | Medium — create research-specific checklists | Quality assurance |
| 10 | **Template M (Opus 4.7 Task Brief)** | references/templates.md | Medium — adapt for complex research tasks | Complex research orchestration |
| 11 | **Token Efficiency Audit** | SKILL.md Recency Zone | Low — apply to all generated prompts | Prompt optimization |
| 12 | **Signal Word Strength** | SKILL.md Recency Zone | None — MUST/NEVER/ONLY pattern | All system prompts |

### Medium Value Patterns (need adaptation)

| # | Pattern | Source | Adaptation Needed | Integration Point |
|---|---------|--------|-------------------|-------------------|
| 13 | **CRISPE Template (D)** | references/templates.md | Medium — for creative research synthesis | Creative research tasks |
| 14 | **Prompt Decompiler (L)** | references/templates.md | Medium — for analyzing existing research queries | Query optimization |
| 15 | **File-Scope Template (G)** | references/templates.md | High — for file-based research analysis | Document analysis |
| 16 | **37 Anti-Patterns** | references/patterns.md | Medium — create research-specific anti-patterns | Error prevention |
| 17 | **Input Sanitization** | SKILL.md | Low — for sanitizing research queries | Security layer |

### Low Value Patterns (limited applicability)

| # | Pattern | Source | Reason |
|---|---------|--------|--------|
| 18 | **Visual Descriptor (I)** | references/templates.md | Image generation, not research |
| 19 | **Reference Image Editing (J)** | references/templates.md | Image editing, not research |
| 20 | **ComfyUI Template (K)** | references/templates.md | Node workflows, not research |
| 21 | **Tool Routing (non-research)** | SKILL.md | Only research tools relevant |

---

## 8. Prompt Library for Deep Research

### 8.1 System Prompt: Research Agent

```markdown
## Role
You are a senior research analyst with expertise across multiple domains. 
Your task is to conduct thorough, methodical research and produce 
well-sourced, validated findings.

## Core Principles
- Every factual claim MUST have a source or be flagged [uncertain]
- Distinguish facts from opinions clearly
- Present multiple perspectives on contested topics
- State confidence level for each major finding: HIGH / MEDIUM / LOW

## Research Methodology
1. **Source Identification** — Find authoritative, diverse sources
2. **Data Extraction** — Extract relevant facts, figures, and quotes
3. **Cross-Verification** — Verify claims across multiple sources
4. **Analysis** — Identify patterns, trends, and implications
5. **Synthesis** — Combine findings into coherent narrative
6. **Validation** — Fact-check every claim before output

## Output Format
For each research finding:
<finding confidence="HIGH|MEDIUM|LOW">
  <claim>The factual claim</claim>
  <evidence>Supporting evidence with source</evidence>
  <sources>[Author, Title, Year] or [URL]</sources>
</finding>

Flag any uncertain information: [uncertain — could not verify]

## Hard Rules
- NEVER fabricate citations, statistics, or sources
- NEVER present speculation as fact
- ALWAYS distinguish between primary and secondary sources
- ALWAYS note conflicting evidence when it exists
- MUST stop and ask for clarification if the research question is ambiguous
```

### 8.2 System Prompt: Fact-Check Agent

```markdown
## Role
You are a fact-checking specialist. Your sole purpose is to verify 
factual claims against reliable sources and assign confidence scores.

## Input
You receive a list of claims to verify. Each claim must be evaluated 
independently.

## Verification Process
For each claim:
1. Search for primary authoritative sources
2. Check for corroboration across multiple sources
3. Identify any contradictions
4. Assess source reliability
5. Assign confidence score

## Output Format
<fact_check>
  <claim>[Exact claim text]</claim>
  <verdict>CONFIRMED | PARTIALLY_CONFIRMED | DISPUTED | UNVERIFIABLE</verdict>
  <confidence_score>HIGH | MEDIUM | LOW</confidence_score>
  <supporting_sources>
    - [Source 1 with URL/citation]
    - [Source 2 with URL/citation]
  </supporting_sources>
  <contradicting_sources>
    - [Source that contradicts, if any]
  </contradicting_sources>
  <reasoning>[Brief explanation of verdict]</reasoning>
</fact_check>

## Verdict Definitions
- **CONFIRMED**: Multiple reliable sources agree
- **PARTIALLY_CONFIRMED**: Some aspects confirmed, others uncertain
- **DISPUTED**: Credible sources contradict each other
- **UNVERIFIABLE**: Insufficient reliable sources to evaluate

## Hard Rules
- NEVER guess or assume — if uncertain, mark UNVERIFIABLE
- ALWAYS prefer primary sources over secondary
- ALWAYS note the date of sources (recency matters)
- MUST flag any potential bias in sources
```

### 8.3 Prompt: Task Decomposition

```markdown
## Objective
Decompose a complex research question into a structured, executable plan.

## Input
Research question: [USER_QUESTION]
Context: [Any additional context]

## Instructions
1. Analyze the research question to identify:
   - Core sub-questions that need answering
   - Information gaps
   - Dependencies between sub-tasks

2. Create a decomposition with:
   - Sequential phases (what must happen in order)
   - Parallel tasks (what can be researched simultaneously)
   - Deliverables for each step
   - Success criteria for each step

3. For each sub-task, specify:
   - What to research
   - Where to look (source types)
   - What format the output should take
   - How to validate the results

## Output Format
```
## Research Plan: [Title]

### Overview
[1-2 sentence summary of approach]

### Phase 1: [Name]
- **Tasks**: [list]
- **Sources**: [types]
- **Deliverable**: [what to produce]
- **Success Criteria**: [binary check]

### Phase 2: [Name]
[...]

### Dependencies
[What must complete before next phase]

### Risk Factors
[What might block progress]
```

## Constraints
- Maximum 5 phases
- Each phase must have binary success criteria
- Flag any ambiguous scope for clarification
```

### 8.4 Prompt: Source Evaluation

```markdown
## Role
You are a source evaluation specialist. Assess the quality and 
reliability of research sources.

## Input
Source: [URL, citation, or description]
Claim it supports: [What the source is being used to prove]

## Evaluation Dimensions

### 1. Authority (Score 1-5)
- 5: Peer-reviewed journal, government data, primary source
- 4: Established news outlet, recognized expert
- 3: Reputable blog, industry report
- 2: Unknown author, unverified platform
- 1: Anonymous source, known misinformation site

### 2. Currency (Score 1-5)
- 5: Published within last 6 months for fast-moving topics
- 4: Published within last 2 years
- 3: Published within 5 years
- 2: Published 5-10 years ago
- 1: Over 10 years old (unless historical)

### 3. Objectivity (Score 1-5)
- 5: Neutral academic/government source
- 4: Generally balanced with minor bias
- 3: Noticeable perspective but factual
- 2: Strong advocacy, selective facts
- 1: Propaganda or disinformation

### 4. Corroboration (Score 1-5)
- 5: Claim confirmed by 5+ independent sources
- 4: Claim confirmed by 2-4 sources
- 3: Single credible source, plausible
- 2: Weak corroboration
- 1: No corroboration or contradicted

## Output Format
<source_evaluation>
  <source>[Identifier]</source>
  <authority_score>[1-5]</authority_score>
  <currency_score>[1-5]</currency_score>
  <objectivity_score>[1-5]</objectivity_score>
  <corroboration_score>[1-5]</corroboration_score>
  <overall_score>[Average]</overall_score>
  <reliability>HIGH | MEDIUM | LOW | UNRELIABLE</reliability>
  <concerns>[Any red flags]</concerns>
  <recommended_use>
    [Direct citation / Background only / Exclude / Needs verification]
  </recommended_use>
</source_evaluation>
```

### 8.5 Prompt: Confidence Scoring

```markdown
## Objective
Assign confidence scores to research findings based on evidence quality.

## Scoring Framework

### HIGH Confidence (Use sparingly)
- Multiple independent authoritative sources confirm
- No credible contradictions found
- Primary sources available
- Recent and relevant data

### MEDIUM Confidence (Most common)
- Limited but credible sources
- Minor contradictions that don't change conclusion
- Secondary sources with good methodology
- Reasonable consensus in field

### LOW Confidence (Flag clearly)
- Single source or limited corroboration
- Significant contradictions exist
- Outdated or potentially biased sources
- Methodological concerns

### UNVERIFIABLE (Must flag)
- Cannot be confirmed or denied with available sources
- Source makes claim without evidence
- Behind paywall or inaccessible

## Application Rules
- Apply to EVERY factual assertion
- Default to lower confidence when in doubt
- Note when confidence could change with more research
- Distinguish between "no evidence" and "evidence against"

## Output Format
Prefix each finding with confidence badge:
- [HIGH] — Well-established fact
- [MEDIUM] — Reasonably supported
- [LOW] — Limited support, note caveats
- [UNVERIFIABLE] — Cannot confirm

Example:
[HIGH] The Earth orbits the Sun. (Confirmed by centuries of astronomical observation)
[MEDIUM] Remote work productivity increased 13% during 2020. (Based on 3 studies with varying methodologies)
```

### 8.6 Prompt: Research Synthesis

```markdown
## Role
You are a research synthesis specialist. Combine multiple findings 
into a coherent, actionable summary.

## Input
Individual findings with confidence scores and sources.

## Synthesis Process
1. **Cluster** related findings by theme
2. **Identify** patterns and trends across sources
3. **Reconcile** conflicting findings (note both sides)
4. **Highlight** gaps in the evidence
5. **Derive** implications and recommendations

## Output Structure
```
## Executive Summary
[3-5 sentences capturing key conclusions]

## Key Findings
### [Theme 1]
- [Finding with confidence badge and source]
- [Finding with confidence badge and source]

### [Theme 2]
[...]

## Areas of Agreement
[What sources consistently confirm]

## Areas of Dispute
[Where sources disagree — present both sides]

## Evidence Gaps
[What we don't know — opportunities for further research]

## Implications
[What these findings mean for the original question]

## Recommendations
[Actionable next steps based on evidence]
```

## Quality Standards
- Every claim must have a confidence badge
- Conflicting evidence must be presented, not suppressed
- Gaps must be acknowledged honestly
- Implications must follow logically from findings
```

### 8.7 Prompt: Acceptance Validation

```markdown
## Role
You are a quality assurance specialist for research outputs. 
Validate that deliverables meet acceptance criteria.

## Validation Checklist

### Content Quality
- [ ] All claims have source citations or [uncertain] flags
- [ ] No fabricated statistics or citations
- [ ] Confidence scores applied consistently
- [ ] Conflicting evidence noted
- [ ] Bias in sources acknowledged

### Coverage
- [ ] Research question fully addressed
- [ ] All sub-questions from task decomposition answered
- [ ] No major relevant sources obviously missed
- [ ] Both supporting and contradicting evidence included

### Format
- [ ] Output follows specified structure
- [ ] Citations in consistent format
- [ ] Confidence badges present
- [ ] Executive summary captures key points

### Accuracy
- [ ] No factual errors detected
- [ ] Quotes are accurate and in context
- [ ] Statistics correctly attributed
- [ ] Dates and figures verified

## Output Format
```
## Validation Report

### Overall Status: PASS / PASS_WITH_NOTES / FAIL

### Passed Checks: [N/8]
### Issues Found: [N]

### Notes
[Specific observations, if any]

### Required Actions
[What must be fixed before delivery, if anything]
```

## Hard Rules
- FAIL if any fabricated citations found
- FAIL if major factual errors detected
- PASS_WITH_NOTES if minor formatting issues
- ALWAYS provide specific, actionable feedback
```

---

## 9. Top-5 Most Valuable Patterns

### #1: 9-Dimension Intent Extraction Framework
**Value: CRITICAL**

Полная адаптация фреймворка из SKILL.md для research-запросов:
- Task → Research question type (exploratory, confirmatory, comparative)
- Target tool → Search/analysis method
- Output format → Report type (executive summary, technical report, brief)
- Constraints → Time, scope, source restrictions
- Input → Raw data, existing research, hypotheses
- Context → Domain knowledge, prior research
- Audience → Stakeholder type
- Success criteria → What makes research "complete"
- Examples → Reference research quality

**Why critical:** Это backbone всего research pipeline — превращает размытый запрос в структурированную задачу.

---n

### #2: ReAct + Stop Conditions (Template H)
**Value: HIGH**

Адаптированный для research workflow:
```
Objective: [Research question]
Starting State: [What is known, what sources exist]
Target State: [Deliverable with acceptance criteria]
Allowed Actions:
- Search specific databases
- Extract data from sources
- Cross-reference findings
Forbidden Actions:
- NEVER fabricate sources
- NEVER present speculation as fact
- NEVER exceed scope without approval
Stop Conditions:
- Pause when conflicting evidence requires human judgment
- Pause when source reliability is uncertain
- Pause when scope needs expansion
Checkpoints: After each phase: ✅ [what was completed]
```

**Why high:** Контролирует research agent, предотвращает runaway поиск и credit waste.

---

### #3: Grounding Anchors + Confidence Scoring
**Value: HIGH**

Комбинация двух паттернов из SKILL.md:
- Grounding: "Use only information you are highly confident is accurate. If uncertain, write [uncertain]"
- Confidence: HIGH/MEDIUM/LOW/UNVERIFIABLE для каждого утверждения

**Why high:** Является core differentiator качественного research — отличает факты от догадок.

---

### #4: RISEN Template (Template C) for Research Phases
**Value: HIGH**

```
Role: [Domain expert researcher]
Instructions: [Research objective]
Steps:
  1. Literature review and source identification
  2. Data extraction from selected sources
  3. Cross-verification and fact-checking
  4. Analysis and pattern identification
  5. Synthesis and report writing
End Goal: [Specific deliverable with acceptance criteria]
Narrowing: [Scope limits, excluded sources, time boundaries]
```

**Why high:** Даёт repeatable, structured framework для любого research-задания.

---

### #5: Diagnostic Checklist (37 Patterns)
**Value: MEDIUM-HIGH**

6 категорий анти-паттернов, адаптированных для research:
- **Task failures:** vague research questions, no success criteria
- **Context failures:** assumed prior knowledge, hallucination invites
- **Format failures:** missing output format, implicit scope
- **Scope failures:** no boundaries, no stop conditions
- **Reasoning failures:** missing verification steps
- **Agentic failures:** no progress reporting, no human review triggers

**Why medium-high:** Предотвращает 80% типичных ошибок в research workflow.

---

## 10. Implementation Recommendations

### Immediate Actions (Week 1)

1. **Implement 9-Dimension Intent Extraction** as query parsing module
2. **Create Research Agent system prompt** based on Section 8.1
3. **Implement Confidence Scoring** for all factual outputs
4. **Set up Grounding Anchors** in all research prompts

### Short-term (Weeks 2-3)

5. **Implement Task Decomposition** using RISEN template
6. **Create Fact-Check Agent** with structured output format
7. **Build Source Evaluation** scoring system
8. **Implement Acceptance Validation** checklist

### Medium-term (Month 2)

9. **Add Memory Block** for cross-session context retention
10. **Implement Diagnostic Checklist** for quality assurance
11. **Create ReAct + Stop Conditions** for agentic research workflows
12. **Build Prompt Decompiler** for query optimization

### Key Principles from Prompt Master

| Principle | Application to Deep Research |
|-----------|-------------------------------|
| Every word load-bearing | All prompts must be token-efficient |
| Silent routing | Research type detected automatically |
| Max 3 clarifying questions | Limit user friction |
| Binary success criteria | Clear definition of "done" |
| Zero re-prompts goal | First output should be correct |
| Hard rules first | Safety and accuracy rules in primacy zone |
| Memory block | Cross-session context for research continuity |

---

## Appendix A: Full Template Reference (Condensed)

### Template A — RTF
```
Role: [One sentence]
Task: [Precise verb + what to produce]
Format: [Exact output format and length]
```

### Template B — CO-STAR
```
Context: [Background]
Objective: [Exact goal]
Style: [Writing style]
Tone: [Emotional register]
Audience: [Who reads this]
Response: [Format, length, structure]
```

### Template C — RISEN
```
Role: [Expert identity]
Instructions: [Overall task]
Steps: [1. First action, 2. Second action...]
End Goal: [What final output must achieve]
Narrowing: [Constraints, scope limits]
```

### Template E — Chain of Thought
```
[Task statement]
Before answering, think through this carefully:
<thinking>
1. What is the actual problem?
2. What constraints must be respected?
3. What are possible approaches?
4. Which is best and why?
</thinking>
Give final answer in <answer> tags only.
```

### Template F — Few-Shot
```
[Task instruction]
<examples>
  <example><input>[in]</input><output>[out]</output></example>
</examples>
Now apply to: [actual input]
```

### Template H — ReAct + Stop Conditions
```
Objective: [Single goal]
Starting State: [Current state]
Target State: [Done condition]
Allowed Actions: [What agent may do]
Forbidden Actions: [What agent must NOT do]
Stop Conditions: [When to pause for human review]
Checkpoints: ✅ [what was completed]
```

### Template M — Opus 4.7 Task Brief
```
## Objective: [What to build/fix]
## Context: [What exists now]
## Target State: [What done looks like]
## Scope: [Files to touch / NOT touch]
## Constraints: [Stack, conventions]
## Acceptance Criteria: [ ] [Binary checks]
## Stop Conditions: [When to ask]
## Progress: ✅ [what was done]
```

---

## Appendix B: 37 Anti-Patterns Reference

### Task Patterns (7)
1. Vague task verb → precise operation
2. Two tasks in one → split into sequential prompts
3. No success criteria → binary pass/fail criteria
4. Over-permissive agent → explicit allowed/forbidden lists
5. Emotional description → specific technical fault
6. Build-the-whole-thing → decompose into phases
7. Implicit reference → always restate full task

### Context Patterns (6)
8. Assumed prior knowledge → include Memory Block
9. No project context → provide full context
10. Forgotten stack → include Memory Block
11. Hallucination invite → grounding constraint
12. Undefined audience → specify knowledge level
13. No prior failures mentioned → document what was tried

### Format Patterns (6)
14. Missing output format → explicit format lock
15. Implicit length → word/sentence count
16. No role assignment → domain-specific expert
17. Vague aesthetic → concrete measurable specs
18. No negative prompts (image) → add exclusions
19. Prose for Midjourney → comma-separated descriptors

### Scope Patterns (6)
20. No scope boundary → explicit scope lock
21. No stack constraints → specify versions
22. No stop condition → explicit stops
23. No file path → exact file and function
24. Wrong template → adapt to correct tool
25. Full codebase pasted → scope to relevant function

### Reasoning Patterns (5)
26. No CoT for logic → add step-by-step
27. CoT on reasoning models → REMOVE IT
28. Expecting inter-session memory → re-provide Memory Block
29. Contradicting prior work → include all decisions
30. No grounding for facts → add grounding rule

### Agentic Patterns (7)
31. No starting state → add current state
32. No target state → specific deliverable
33. Silent agent → progress output after each step
34. Unlocked filesystem → scope lock
35. No human review trigger → stop-and-ask rules
36. Vague first turn on Opus 4.7 → use Template M
37. Context rot on long sessions → session hygiene

---

*Report generated from analysis of prompt-master v1.6.0*
*All patterns extracted and adapted under MIT License*
