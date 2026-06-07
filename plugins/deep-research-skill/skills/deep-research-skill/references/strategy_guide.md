# Deep Research Skill — Strategy Guide

## Document Control

| Property | Value |
|----------|-------|
| Version | 1.0 |
| Status | Draft |
| Author | AI Architecture Team |
| Last Updated | 2025-06-28 |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Principles](#2-architecture-principles)
3. [Route Classification](#3-route-classification)
4. [Execution Strategy per Route](#4-execution-strategy-per-route)
5. [Task-to-Route Router](#5-task-to-route-router)
6. [Depth Levels](#6-depth-levels)
7. [Parallelization Rules](#7-parallelization-rules)
8. [Cost Budgeting](#8-cost-budgeting)
9. [Quality Gates & Validation](#9-quality-gates--validation)
10. [Error Handling & Fallbacks](#10-error-handling--fallbacks)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Appendices](#12-appendices)

---

## 1. Executive Summary

Deep Research Skill — это Claude Desktop plugin, выполняющий многоступенчатое глубокое исследование по заданной задаче. Скилл комбинирует четыре ключевых компетенции: интеллектуальную маршрутизацию запросов, параллельное выполнение subtasks, адаптивный контроль глубины исследования и оптимизацию стоимости.

### Core Value Proposition

- **Adaptive Routing**: Автоматический выбор стратегии исследования на основе анализа входного запроса
- **Parallel Execution**: Максимальное распараллеливание независимых задач для сокращения времени
- **Depth Control**: Четыре уровня глубины от 30-минутного обзора до экспертного исследования
- **Cost Governance**: Прозрачное бюджетирование и early stopping criteria

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUERY                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  Task Router    │  ← NLP-based classification
              │  (Phase 0)      │
              └────────┬────────┘
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
      ┌────────┐ ┌────────┐ ┌──────────────┐
      │ Route  │ │ Route  │ │ Route D      │
      │ A-C    │ │ File   │ │ File-Aug     │
      │ (Web)  │ │ Only   │ │ (Hybrid)     │
      └────┬───┘ └────┬───┘ └──────┬───────┘
           │          │            │
           └──────────┼────────────┘
                      │
              ┌───────▼────────┐
              │  Depth Level   │  ← Quick / Standard / Deep / Exhaustive
              │  Selector      │
              └───────┬────────┘
                      │
              ┌───────▼────────┐
              │  Execution     │  ← Parallel/Sequential orchestration
              │  Engine        │
              └───────┬────────┘
                      │
              ┌───────▼────────┐
              │  Synthesis &   │
              │  Output        │
              └────────────────┘
```

---

## 2. Architecture Principles

### 2.1 Routing-First Design

Каждый запрос проходит через многоуровневую классификацию прежде чем начинается выполнение. Router работает за O(1) по отношению к сложности запроса, используя комбинацию keyword matching, pattern classification и LLM-based analysis для edge cases.

### 2.2 Progressive Disclosure

Скилл использует архитектуру lazy loading:
- **SKILL.md** — lean metadata + routing logic (~200 tokens)
- **Phase modules** — загружаются on-demand по мере необходимости
- **Reference files** — domain-specific knowledge, подгружается при активации соответствующего Route

### 2.3 Tool Abstraction Layer

Все инструменты (Firecrawl, Obscura, CloakBrowser) скрыты за统一ным интерфейсом. Execution Engine не знает о конкретных реализациях — он работает с абстракциями типа `WebFetcher`, `ProtectedSiteFetcher`, `FileAnalyzer`.

### 2.4 Cost-Aware Execution

Каждый subtask имеет declared cost tier. Execution Engine оптимизирует расписание выполнения с учётом бюджета: при приближении к лимиту происходит graceful degradation (переход на более дешёвые инструменты или сокращение scope).

### 2.5 Deterministic Outputs

Все операции преобразования данных (парсинг, агрегация, форматирование) выполняются кодом, не моделью. LLM используется только для: маршрутизации, синтеза, качественной оценки.

---

## 3. Route Classification

### 3.1 Route Decision Matrix

| Route | Type | Primary Source | Secondary Source | When to Activate |
|-------|------|---------------|------------------|------------------|
| **A** | Wide Search | Web (Firecrawl + Obscura) | — | Обзорные, exploratory темы |
| **B** | Focused Search | Web (Obscura primary) | Firecrawl for detail | Конкретные, well-scoped вопросы |
| **C** | File-Only | Local files | — | Запрос явно ограничен файлами |
| **D** | File-Augmented | Local files | Web for supplementation | Анализ файлов + внешний контекст |

### 3.2 Route A: Wide Search — Detailed Breakdown

**Activation Criteria:**
- Запрос содержит слова-индикаторы: "landscape", "overview", "state of", "trends", "market", "industry", "comparison", "players", "ecosystem"
- Отсутствуют конкретные named entities (продукты, компании, даты)
- Вопрос начинается с "What is...", "How does... work", "Explain..."

**Sub-routes:**

#### Route A1: Industry Landscape
**When:** Запрос о рыночной нише, индустрии, секторе
**Keywords:** "industry landscape", "market overview", "sector analysis", "key players", "market structure"
**Example Queries:**
- "AI agent infrastructure landscape 2025"
- "Who are the key players in vector databases?"
- "Martech ecosystem overview"

**Execution Pattern:**
1. Parallel search: top-10 companies + market size + recent funding rounds
2. Sequential: synthesis of competitive positioning
3. Quality gate: coverage check (min 7/10 major players identified)

#### Route A2: Trend Analysis
**When:** Запрос о трендах, направлениях развития, будущем
**Keywords:** "trends", "future of", "emerging", "where is X heading", "predictions", "outlook"
**Example Queries:**
- "What are the emerging trends in AI code generation?"
- "Future of edge computing in 2025-2027"
- "How is the API economy evolving?"

**Execution Pattern:**
1. Parallel: recent reports + expert opinions + data trends + sentiment analysis
2. Sequential: trend synthesis + confidence scoring
3. Quality gate: temporal consistency (конфликтующие прогнозы должны быть отмечены)

#### Route A3: Technology Comparison
**When:** Запрос сравнивает технологии, подходы, стеки
**Keywords:** "vs", "versus", "comparison", "differences between", "which is better", "pros and cons"
**Example Queries:**
- "Supabase vs Firebase vs Appwrite"
- "REST vs GraphQL vs gRPC for microservices"
- "Vector databases comparison: Pinecone vs Weaviate vs Milvus"

**Execution Pattern:**
1. Parallel: individual deep-dive per technology + community sentiment + performance benchmarks
2. Sequential: structured comparison matrix + recommendation logic
3. Quality gate: dimensional coverage (min 5 сравнительных критериев)

#### Route A4: Regulatory / Compliance Landscape
**When:** Запрос о регуляторике, compliance, правовых рамках
**Keywords:** "regulation", "compliance", "GDPR", "legal requirements", "policy", "framework"
**Example Queries:**
- "AI Act compliance requirements for startups"
- "Data residency laws by country"
- "SOC 2 vs ISO 27001 requirements"

**Execution Pattern:**
1. Parallel: official sources + legal analysis + industry interpretation + regional differences
2. Sequential: compliance checklist synthesis
3. Quality gate: source authority check (только .gov, .eu, официальные документы для factual claims)

### 3.3 Route B: Focused Search — Detailed Breakdown

**Activation Criteria:**
- Запрос содержит конкретный named entity (компания, продукт, технология)
- Есть чёткий вопрос, требующий ответа Yes/No или конкретного факта
- Вопрос про "how to", "why does", "what caused"

**Sub-routes:**

#### Route B1: Product Deep-Dive
**When:** Анализ конкретного продукта, сервиса, компании
**Keywords:** product name + "pricing", "features", "architecture", "review", "how it works"
**Example Queries:**
- "How does Firecrawl handle JavaScript rendering?"
- "Claude 3.5 Sonnet context window architecture"
- "Stripe Treasury product capabilities"

**Execution Pattern:**
1. Parallel: official docs + engineering blog + community discussion + competitor comparison
2. Sequential: technical analysis + limitation identification
3. Quality gate: primary source verification (все factual claims должны иметь ссылку на первоисточник)

#### Route B2: Troubleshooting / Debug
**When:** Проблема, ошибка, неожиданное поведение
**Keywords:** "error", "bug", "not working", "fails", "exception", "timeout", "crash"
**Example Queries:**
- "Why does my Firecrawl extraction return empty results?"
- "OpenAI API rate limiting errors 429"
- "Docker container OOM kills troubleshooting"

**Execution Pattern:**
1. Parallel: documentation check + community issues + known bugs + workaround search
2. Sequential: root cause analysis + solution ranking
3. Quality gate: solution verification (минимум 2 независимых подтверждения workaround)

#### Route B3: Integration Guide
**When:** Запрос о соединении двух систем
**Keywords:** "integrate", "connect", "setup", "configure", "with", "and"
**Example Queries:**
- "How to integrate Firecrawl with LangChain?"
- "Claude Desktop with custom MCP server setup"
- "Stripe + Salesforce integration patterns"

**Execution Pattern:**
1. Parallel: official integration guides + community examples + SDK documentation + compatibility matrix
2. Sequential: step-by-step guide synthesis + prerequisite checklist
3. Quality gate: completeness check (все шаги от setup до verification)

#### Route B4: Pricing / Business Model Analysis
**When:** Анализ ценообразования, бизнес-модели
**Keywords:** "pricing", "cost", "business model", "revenue", "plans", "tiers"
**Example Queries:**
- "Claude API pricing calculator strategy"
- "How does Vercel pricing work for enterprise?"
- "AWS vs GCP cost comparison for AI workloads"

**Execution Pattern:**
1. Parallel: official pricing + hidden costs + enterprise terms + community cost reports
2. Sequential: total cost of ownership model + scenario analysis
3. Quality gate: price freshness (проверка даты последнего обновления цен)

### 3.4 Route C: File-Only — Detailed Breakdown

**Activation Criteria:**
- Явное указание на файлы: "in this document", "from the uploaded file", "analyze my"
- Отсутствие потребности во внешних данных
- Работа с конфиденциальными данными

**Sub-routes:**

#### Route C1: Document Analysis
**When:** Анализ содержимого документа
**Keywords:** "analyze this", "summarize", "extract", "from the document"
**Example Queries:**
- "Summarize the key points from this contract"
- "Extract all deadlines from the project plan"
- "What are the main risks in this investment memo?"

#### Route C2: Cross-Document Synthesis
**When:** Анализ нескольких документов вместе
**Keywords:** "compare these", "across all files", "synthesize", "find inconsistencies"
**Example Queries:**
- "Find inconsistencies between the proposal and the contract"
- "Synthesize market research across all uploaded reports"
- "Compare Q1 and Q2 financial statements"

#### Route C3: Data Extraction & Transformation
**When:** Структурированный вывод данных из файлов
**Keywords:** "convert to", "extract as", "table", "CSV", "JSON", "structured"
**Example Queries:**
- "Extract all contact information into a table"
- "Convert this requirements document to JSON schema"
- "Pull all API endpoints from the documentation"

### 3.5 Route D: File-Augmented — Detailed Breakdown

**Activation Criteria:**
- Запрос содержит и файлы, и запрос внешнего контекста
- Нужно "enrich", "validate", "compare with market"
- Файлы требуют external benchmarking

**Sub-routes:**

#### Route D1: Document Validation
**When:** Проверка документа на актуальность, корректность
**Keywords:** "validate", "check against", "up to date", "accurate", "verify"
**Example Queries:**
- "Check if this API documentation is up to date with the latest release"
- "Validate these compliance requirements against current regulations"
- "Verify the technical claims in this whitepaper"

#### Route D2: Market Benchmarking
**When:** Сравнение внутренних данных с рыночными
**Keywords:** "benchmark", "compare to market", "industry standard", "how do we compare"
**Example Queries:**
- "How does our pricing compare to market rates?"
- "Benchmark our tech stack against industry standards"
- "Compare our metrics to public company benchmarks"

#### Route D3: Gap Analysis
**When:** Выявление недостающего по сравнению с лучшими практиками
**Keywords:** "gaps", "missing", "what's lacking", "improvements", "vs best practices"
**Example Queries:**
- "What security controls are we missing compared to SOC 2 requirements?"
- "Identify gaps in our documentation vs industry standards"
- "What's missing from our API compared to competitors?"

---

## 4. Execution Strategy per Route

### 4.1 Execution Framework

Каждый Route следует единому шаблону:

```
Phase 0: Routing (always)       → LLM-based classification
Phase 1: Discovery              → parallel where possible
Phase 2: Deep Dive              → mixed parallel/sequential
Phase 3: Synthesis              → sequential
Phase 4: Validation             → parallel checks
Phase 5: Output Generation      → sequential
```

### 4.2 Route A: Wide Search Execution

#### Phase Breakdown

| Phase | Subtasks | Parallel | Sequential | Tools | Est. Time |
|-------|----------|----------|------------|-------|-----------|
| P1: Discovery | Query expansion (5-10 variants) | 5-10 queries | — | Firecrawl (batch) | 2-5 min |
| P1: Discovery | Source identification | — | Source ranking | Obscura | 1-2 min |
| P2: Deep Dive | Per-source extraction | 3-5 sources | — | Firecrawl + Obscura | 5-15 min |
| P2: Deep Dive | Cross-reference | — | Fact linking | Internal | 2-3 min |
| P3: Synthesis | Theme identification | — | Clustering | LLM | 2-3 min |
| P3: Synthesis | Narrative construction | — | Writing | LLM | 3-5 min |
| P4: Validation | Fact-check | 5-10 claims | — | Web search | 2-5 min |
| P4: Validation | Completeness check | — | Coverage analysis | Internal | 1 min |
| P5: Output | Format & deliver | — | Rendering | Internal | 1 min |

#### Subtask-to-Tool Mapping

```yaml
Route_A_Execution:
  Discovery:
    - task: "Query expansion"
      tool: "LLM (internal)"
      cost: "~0.001$"
      output: "5-10 search query variants"
    
    - task: "Batch web search"
      tool: "Firecrawl (batch mode)"
      cost: "~0.01-0.05$"
      output: "Raw search results (10-20 pages)"
      parallel: true
      max_parallel: 10
    
    - task: "Source quality scoring"
      tool: "Obscura (headless)"
      cost: "~0.02$"
      output: "Ranked source list with credibility scores"
  
  Deep_Dive:
    - task: "Deep extraction per source"
      tool: "Firecrawl (detailed)"
      cost: "~0.01-0.03$ per source"
      output: "Structured content per source"
      parallel: true
      max_parallel: 5
      trigger: "source score > threshold"
    
    - task: "Protected content fallback"
      tool: "Obscura"
      cost: "~0.03$ per source"
      output: "Content from JS-heavy sites"
      condition: "Firecrawl returns < 50% content"
  
  Synthesis:
    - task: "Theme clustering"
      tool: "LLM"
      cost: "~0.005$"
      output: "Identified themes with evidence"
    
    - task: "Narrative writing"
      tool: "LLM"
      cost: "~0.01-0.05$"
      output: "Structured research report"
  
  Validation:
    - task: "Fact verification"
      tool: "Web search (spot checks)"
      cost: "~0.01$"
      output: "Verified claims with citations"
      parallel: true
      sample_rate: "20% of claims"
```

#### Quality Gates

```yaml
Route_A_Quality_Gates:
  Gate_1_PostDiscovery:
    - "Min 10 unique sources found"
    - "Source diversity: min 3 domains"
    - "Max 30% sources from same domain"
    - Action_if_fail: "Expand query set, retry"
  
  Gate_2_PostDeepDive:
    - "Content extracted from min 70% of targeted sources"
    - "Average content length > 500 tokens per source"
    - "No single source > 40% of total content"
    - Action_if_fail: "Add fallback tools (Obscura), expand source list"
  
  Gate_3_PostSynthesis:
    - "Min 3 distinct themes identified"
    - "Every major claim has citation"
    - "No hallucinated statistics"
    - Action_if_fail: "Return to Deep Dive phase for missing data"
  
  Gate_4_PostValidation:
    - "90%+ of checked facts verified"
    - "Conflicting information explicitly noted"
    - Action_if_fail: "Flag uncertain claims, add confidence labels"
```

### 4.3 Route B: Focused Search Execution

#### Phase Breakdown

| Phase | Subtasks | Parallel | Sequential | Tools | Est. Time |
|-------|----------|----------|------------|-------|-----------|
| P1: Discovery | Entity resolution | — | Canonical name | Search | 1 min |
| P1: Discovery | Multi-source search | 3-5 queries | — | Obscura primary | 3-5 min |
| P2: Deep Dive | Official docs crawl | — | Structured path | Firecrawl | 3-10 min |
| P2: Deep Dive | Community analysis | 2-3 sources | — | Obscura | 3-5 min |
| P2: Deep Dive | Technical validation | — | Reproduction | Code exec | 2-5 min |
| P3: Synthesis | Answer formulation | — | Structured | LLM | 2-3 min |
| P4: Validation | Source verification | 3-5 sources | — | Web | 2 min |
| P5: Output | Format answer | — | Template | Internal | 1 min |

#### Subtask-to-Tool Mapping

```yaml
Route_B_Execution:
  Discovery:
    - task: "Entity resolution"
      tool: "LLM + Search"
      cost: "~0.002$"
      output: "Canonical entity name, aliases"
    
    - task: "Targeted search"
      tool: "Obscura (primary)"
      cost: "~0.02$"
      output: "Official docs, GitHub, forums"
      parallel: true
      max_parallel: 5
  
  Deep_Dive:
    - task: "Official documentation crawl"
      tool: "Firecrawl (2-4 key pages)"
      cost: "~0.02$"
      output: "Structured technical content"
      sequential: true  # Follow links depth-first
      max_depth: 2
    
    - task: "Community sentiment"
      tool: "Obscura (Hacker News, Reddit, Twitter)"
      cost: "~0.015$"
      output: "User experiences, edge cases"
      parallel: true
      max_parallel: 3
    
    - task: "Technical reproduction"
      tool: "Code execution"
      cost: "~0.001$"
      output: "Verified code samples, API responses"
      condition: "query involves code/config"
  
  Synthesis:
    - task: "Answer structuring"
      tool: "LLM"
      cost: "~0.005$"
      output: "Hierarchical answer with sources"
      template: "Direct answer → Details → Sources → Related"
  
  Validation:
    - task: "Primary source check"
      tool: "Web fetch"
      cost: "~0.005$"
      output: "Link validation, content freshness"
      parallel: true
```

#### Quality Gates

```yaml
Route_B_Quality_Gates:
  Gate_1_PostDiscovery:
    - "Entity unambiguously identified"
    - "Official source located"
    - Action_if_fail: "Disambiguation prompt to user"
  
  Gate_2_PostDeepDive:
    - "Official docs content extracted"
    - "At least 1 community source analyzed"
    - "Code samples verified (if applicable)"
    - Action_if_fail: "Switch to alternative tools, prompt user"
  
  Gate_3_PostSynthesis:
    - "Direct answer provided upfront"
    - "Supporting evidence cited"
    - "Limitations acknowledged"
    - Action_if_fail: "Restructure output, add missing sections"
  
  Gate_4_PostValidation:
    - "All citations resolve"
    - "No contradiction between official and community sources (or explained)"
    - Action_if_fail: "Add confidence flags, note discrepancies"
```

### 4.4 Route C: File-Only Execution

#### Phase Breakdown

| Phase | Subtasks | Parallel | Sequential | Tools | Est. Time |
|-------|----------|----------|------------|-------|-----------|
| P1: Discovery | File inventory | — | Parse structure | Internal | 1 min |
| P1: Discovery | Format detection | All files | — | Internal | 1 min |
| P2: Deep Dive | Content extraction | All files | — | Internal | 2-5 min |
| P2: Deep Dive | Cross-reference | — | Link analysis | Internal | 1-2 min |
| P3: Synthesis | Analysis/Summary | — | Structured | LLM | 2-5 min |
| P4: Validation | Consistency check | — | Automated | Internal | 1 min |
| P5: Output | Format output | — | Template | Internal | 1 min |

#### Subtask-to-Tool Mapping

```yaml
Route_C_Execution:
  Discovery:
    - task: "File parsing"
      tool: "Internal (format-specific parsers)"
      cost: "0$"
      output: "Structured document tree"
      formats: ["pdf", "docx", "txt", "md", "csv", "json", "xlsx"]
  
  Deep_Dive:
    - task: "Content extraction"
      tool: "Internal + LLM (for semantic chunking)"
      cost: "~0.002$ per file"
      output: "Semantic chunks with metadata"
      parallel: true
      max_parallel: "all files"
    
    - task: "Cross-reference mapping"
      tool: "Internal"
      cost: "0$"
      output: "Entity relationship graph"
  
  Synthesis:
    - task: "Analysis"
      tool: "LLM"
      cost: "~0.005-0.02$"
      output: "Structured analysis"
      depends_on: "extraction complete"
  
  Validation:
    - task: "Self-consistency"
      tool: "Internal"
      cost: "0$"
      output: "Conflict report"
```

### 4.5 Route D: File-Augmented Execution

#### Phase Breakdown

| Phase | Subtasks | Parallel | Sequential | Tools | Est. Time |
|-------|----------|----------|------------|-------|-----------|
| P1: Discovery | File analysis | All files | — | Internal | 2-3 min |
| P1: Discovery | Web context search | 3-5 queries | — | Firecrawl + Obscura | 3-5 min |
| P2: Deep Dive | File deep extraction | — | Structured | Internal + LLM | 3-5 min |
| P2: Deep Dive | Web deep extraction | 2-3 sources | — | Obscura primary | 3-5 min |
| P2: Deep Dive | Cross-reference | — | Mapping | Internal | 2 min |
| P3: Synthesis | Integrated analysis | — | Blended | LLM | 3-5 min |
| P4: Validation | Dual verification | File + Web | — | Mixed | 2 min |
| P5: Output | Unified report | — | Template | Internal | 1 min |

#### Subtask-to-Tool Mapping

```yaml
Route_D_Execution:
  Discovery:
    - task: "File preprocessing"
      tool: "Internal"
      cost: "0$"
      output: "File summary, key entities"
      parallel: true
    
    - task: "Context web search"
      tool: "Firecrawl (batch)"
      cost: "~0.02$"
      output: "External benchmarks, latest data"
      parallel: true
      triggered_by: "file content analysis"
  
  Deep_Dive:
    - task: "File semantic analysis"
      tool: "LLM"
      cost: "~0.01$"
      output: "Key claims, assumptions, gaps"
    
    - task: "External source deep extraction"
      tool: "Obscura"
      cost: "~0.02$"
      output: "Current market data, regulations"
      parallel: true
    
    - task: "Cross-reference mapping"
      tool: "Internal"
      cost: "0$"
      output: "File claim ↔ External source links"
  
  Synthesis:
    - task: "Integrated analysis"
      tool: "LLM"
      cost: "~0.02$"
      output: "Unified report with internal/external perspectives"
      approach: "File data as baseline, web data as augmentation"
  
  Validation:
    - task: "Dual-source verification"
      tool: "Mixed"
      cost: "~0.005$"
      output: "Confidence scores per claim"
      file_claims: "verified against web sources"
      web_claims: "checked for recency"
```

---

## 5. Task-to-Route Router

### 5.1 Router Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     ROUTER PIPELINE                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │  Layer 1:   │ →  │  Layer 2:   │ →  │  Layer 3:       │  │
│  │  Keyword    │    │  Pattern    │    │  LLM Classifier │  │
│  │  Matcher    │    │  Classifier │    │  (Edge Cases)   │  │
│  │  (O(1))     │    │  (O(n))     │    │  (O(LLM))       │  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
│         │                  │                    │             │
│         └──────────────────┴────────────────────┘             │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │  Route +       │                        │
│                    │  Confidence    │                        │
│                    └───────┬────────┘                        │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │  Depth Level   │                        │
│                    │  Selector      │                        │
│                    └────────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Layer 1: Keyword Matcher (Fast Path)

Работает за O(1) с использованием хеш-таблицы. Вход: нормализованный запрос (lower case, стемминг).

```python
KEYWORD_ROUTES = {
    # Route C triggers (highest priority — explicit file references)
    "this file": "C",
    "this document": "C",
    "uploaded file": "C",
    "the attached": "C",
    "from my file": "C",
    "analyze this": "C",
    "summarize this": "C",
    "extract from": "C",
    "in these documents": "C",
    "across all files": "C",
    
    # Route D triggers (file + web hybrid)
    "validate against": "D",
    "check against market": "D",
    "benchmark against": "D",
    "compare to industry": "D",
    "how do we compare": "D",
    "up to date": "D",
    "current regulations": "D",
    "market standard": "D",
    "best practices": "D",
    
    # Route A triggers (wide / exploratory)
    "landscape": "A",
    "overview": "A",
    "state of": "A",
    "ecosystem": "A",
    "market analysis": "A",
    "industry trends": "A",
    "key players": "A",
    "who are the": "A",
    "what are the": "A",
    "comparison of": "A",
    "vs ": "A",
    "versus": "A",
    "pros and cons": "A",
    "guide to": "A",
    "introduction to": "A",
    "getting started": "A",
    
    # Route B triggers (focused)
    "how to": "B",
    "how does": "B",
    "why does": "B",
    "what causes": "B",
    "error": "B",
    "bug": "B",
    "not working": "B",
    "pricing": "B",
    "cost of": "B",
    "setup": "B",
    "configure": "B",
    "integrate": "B",
    "troubleshoot": "B",
    "debug": "B",
}
```

**Priority Rules:**
1. Если найден Route C keyword → сразу Route C (unless found D keyword within 5 words)
2. Если найден Route D keyword → Route D
3. Если несколько Route A keywords → Route A
4. Если найден Route B keyword → Route B
5. Если conflict → Layer 2

### 5.3 Layer 2: Pattern Classifier

Использует регулярные выражения и структурные паттерны.

```python
PATTERN_ROUTES = [
    # Route C: File-only patterns
    {
        "pattern": r"(summarize|analyze|extract|convert)\s+(this|the|these|my)\s+(file|document|pdf|doc|spreadsheet)",
        "route": "C",
        "confidence": 0.95
    },
    {
        "pattern": r"(in|from)\s+(the\s+)?(attached|uploaded)\s+(file|document)",
        "route": "C",
        "confidence": 0.95
    },
    # Route D: File + context patterns
    {
        "pattern": r"(compare|benchmark|validate)\s+(this|our|my)\s+.*\s+(against|with|to)\s+(market|industry|competitors|standards)",
        "route": "D",
        "confidence": 0.90
    },
    {
        "pattern": r"(check|verify)\s+if\s+(this|the)\s+.*\s+(is\s+)?(still\s+)?(accurate|current|up.to.date|valid)",
        "route": "D",
        "confidence": 0.85
    },
    # Route A: Wide exploration patterns
    {
        "pattern": r"^(what is|who are|explain|describe|tell me about)\s+.*\?(\s*$|\s+(in general|overview|landscape))",
        "route": "A",
        "confidence": 0.80
    },
    {
        "pattern": r"(top\s+\d+|best|leading|major)\s+.*\s+(companies|players|tools|frameworks|platforms)",
        "route": "A1",
        "confidence": 0.85
    },
    {
        "pattern": r"(trends?|future|outlook|forecast|predictions?)\s+.*\s+(202\d|20\d\d\s*-\s*20\d\d)",
        "route": "A2",
        "confidence": 0.85
    },
    {
        "pattern": r"(\w+)\s+vs\.?\s+(\w+)(\s+vs\.?\s+(\w+))?",
        "route": "A3",
        "confidence": 0.75
    },
    # Route B: Focused question patterns
    {
        "pattern": r"(how (do|can|to|would|should)|what's the best way to)\s+.*\?",
        "route": "B",
        "confidence": 0.70
    },
    {
        "pattern": r"(why|what causes|what's causing)\s+.*\s+(to|error|fail|crash|timeout)",
        "route": "B2",
        "confidence": 0.80
    },
    {
        "pattern": r"(pricing|cost|price)\s+(of|for)\s+\w+",
        "route": "B4",
        "confidence": 0.85
    },
    {
        "pattern": r"(integrate|connect|setup)\s+\w+\s+(with|and)\s+\w+",
        "route": "B3",
        "confidence": 0.85
    },
]
```

### 5.4 Layer 3: LLM Classifier (Edge Cases)

Вызывается только когда Layer 1 и 2 дают:
- Confidence < 0.70
- Conflicting routes
- Ни один паттерн не сработал

**Prompt Template:**
```
Classify the following research query into one of these routes:
- Route A (Wide Search): Broad, exploratory, overview topics
- Route B (Focused Search): Specific question about a product/technology/issue
- Route C (File-Only): Analysis limited to uploaded files
- Route D (File-Augmented): File analysis augmented with web research

Also classify depth: Quick / Standard / Deep / Exhaustive

Query: "{user_query}"
Files attached: {file_count > 0}

Respond in JSON:
{
  "route": "A|B|C|D",
  "sub_route": "A1|A2|A3|A4|B1|B2|B3|B4|C1|C2|C3|D1|D2|D3",
  "confidence": 0.0-1.0,
  "depth": "Quick|Standard|Deep|Exhaustive",
  "reasoning": "brief explanation"
}
```

### 5.5 Edge Cases & Ambiguity Resolution

| Scenario | Resolution Strategy |
|----------|-------------------|
| Query matches both A and B | Prefer B if named entity present, else A |
| File attached but query doesn't reference it | Route A/B (ignore file unless explicitly referenced) |
| Query references file AND asks for external data | Route D |
| Multiple files with conflicting formats | Route C2 or D2 based on query |
| Very short query (< 5 words) | Ask clarifying question |
| Query in non-English | Translate → classify → note for tool selection |
| Mixed language query | Classify on English keywords if present, else LLM |
| Code-heavy query | Route B with technical validation flag |
| Pricing + Comparison | Route A3 if multiple products, B4 if single product |
| "Research X for me" without specifics | Route A + ask for depth clarification |
| Urgency indicators ("ASAP", "quickly") | Reduce depth by 1 level, use faster tools |

### 5.6 Router Decision Flow

```
User Query
    │
    ▼
┌───────────────────┐
│ Has attached files│──Yes──┐
│ not referenced?   │       │
└───────────────────┘       │
    No                      │
    │                       ▼
    ▼              ┌────────────────┐
┌─────────────────┐│ Route C/D check│
│ Layer 1: Keyword││ File ref + web │
│ Match?          ││ = Route D      │
└─────────────────┘│ File only = C  │
    │              └────────────────┘
    │ Match found
    ▼
┌──────────────────┐
│ Confidence > 0.7?│──No──┐
└──────────────────┘      │
    Yes                   ▼
    │            ┌─────────────────┐
    │            │ Layer 2: Pattern│
    │            │ Match?          │
    │            └─────────────────┘
    │                  │
    │                  ▼
    │         ┌──────────────────┐
    │         │ Confidence > 0.7?│──No──┐
    │         └──────────────────┘      │
    │              Yes                  ▼
    │              │           ┌───────────────┐
    │              │           │ Layer 3: LLM  │
    │              │           │ Classifier    │
    │              │           └───────────────┘
    │              │                  │
    │              └──────────────────┘
    │
    ▼
┌────────────────────┐
│ Route + Confidence │
│ Depth Level        │
└────────────────────┘
```

---

## 6. Depth Levels

### 6.1 Depth Level Matrix

| Level | Time | Subtasks | Tools | Cost Range | Use Case |
|-------|------|----------|-------|------------|----------|
| **Quick** | 30 min | 5-8 | Firecrawl (batch), basic search | $0.01-0.10 | Initial exploration, sanity check |
| **Standard** | 1-2 hrs | 10-15 | Firecrawl + Obscura + LLM | $0.10-0.50 | Structured analysis, decision support |
| **Deep** | 3-5 hrs | 20-30 | Full toolset + code exec | $0.50-2.00 | Expert research, comprehensive report |
| **Exhaustive** | 5+ hrs | 30-50 | All tools + recursive search | $2.00-10.00 | Maximum completeness, publication-ready |

### 6.2 Quick Depth (30 minutes)

**Characteristics:**
- Top-level facts only
- 3-5 sources
- Batch operations where possible
- No deep extraction
- Template-based output

**Subtask Distribution:**
```yaml
Quick_Depth:
  Discovery: 2 subtasks (parallel)
    - "Top-level search (3 query variants)"
    - "Source identification (5 sources)"
  
  Extraction: 3 subtasks (parallel)
    - "Quick scrape of top 3 sources"
    - "Key fact extraction"
    - "Source metadata capture"
  
  Synthesis: 1 subtask
    - "Template-based summary (3-5 paragraphs)"
  
  Validation: 1 subtask
    - "Spot check 2-3 key facts"
  
  Output: 1 subtask
    - "Formatted summary with citations"
```

**Tool Selection:**
| Task | Tool | Rationale |
|------|------|-----------|
| Discovery | Firecrawl batch | Cheapest for broad search |
| Extraction | Firecrawl single | Fast, no JS needed for most |
| Synthesis | LLM (light) | Minimal token usage |
| Validation | Quick search | Verify 2-3 critical facts |

**Cost Estimate:** $0.01 - $0.10

### 6.3 Standard Depth (1-2 hours)

**Characteristics:**
- Structured analysis with sections
- 8-15 sources
- Mix of batch and targeted extraction
- Quality gates at each phase
- Custom output format

**Subtask Distribution:**
```yaml
Standard_Depth:
  Discovery: 3 subtasks
    - "Query expansion (5 variants)"
    - "Multi-source search (10 sources)"
    - "Source quality scoring"
  
  Deep_Dive: 5 subtasks
    - "Deep extraction of top 5 sources"
    - "Cross-reference analysis"
    - "Gap identification"
    - "Supplementary search for gaps"
    - "Data consolidation"
  
  Synthesis: 2 subtasks
    - "Theme identification"
    - "Structured report writing"
  
  Validation: 2 subtasks
    - "Fact verification (20% sample)"
    - "Source freshness check"
  
  Output: 1 subtask
    - "Formatted report with TOC, citations, appendix"
```

**Tool Selection:**
| Task | Tool | Rationale |
|------|------|-----------|
| Discovery | Firecrawl batch + Obscura | Balance cost and coverage |
| Deep Dive | Firecrawl detailed + Obscura fallback | Handle JS-heavy sites |
| Synthesis | LLM (standard) | Quality writing |
| Validation | Web search + metadata check | Verify claims |

**Cost Estimate:** $0.10 - $0.50

### 6.4 Deep Depth (3-5 hours)

**Characteristics:**
- Full research with multiple angles
- 15-25 sources
- Recursive search (findings lead to new queries)
- Code-level validation where applicable
- Multiple synthesis iterations
- Comprehensive report

**Subtask Distribution:**
```yaml
Deep_Depth:
  Discovery: 4 subtasks
    - "Query expansion (10 variants)"
    - "Multi-source search (15 sources)"
    - "Source quality + credibility scoring"
    - "Snowball sampling (follow references)"
  
  Deep_Dive: 10 subtasks
    - "Deep extraction of top 10 sources"
    - "Protected site handling (if needed)"
    - "Community source analysis"
    - "Technical validation / reproduction"
    - "Data extraction to structured format"
    - "Temporal analysis (date ranges)"
    - "Author/organization credibility check"
    - "Contradiction detection"
    - "Supplementary gap-filling search"
    - "Data consolidation and cleaning"
  
  Synthesis: 4 subtasks
    - "Theme identification + clustering"
    - "Evidence strength assessment"
    - "Narrative construction"
    - "Executive summary + detailed sections"
  
  Validation: 3 subtasks
    - "Fact verification (50% sample)"
    - "Source freshness + link validation"
    - "Peer review simulation"
  
  Output: 2 subtasks
    - "Report generation with full citations"
    - "Appendix with methodology + raw data"
```

**Tool Selection:**
| Task | Tool | Rationale |
|------|------|-----------|
| Discovery | Firecrawl + Obscura + CloakBrowser | Maximum coverage |
| Deep Dive | All tools including code exec | Comprehensive |
| Synthesis | LLM (extended) | High-quality writing |
| Validation | Multi-tool verification | Rigorous checking |

**Cost Estimate:** $0.50 - $2.00

### 6.5 Exhaustive Depth (5+ hours)

**Characteristics:**
- Maximum completeness
- 25-50+ sources
- Recursive and snowball search
- Full reproducibility
- Multiple validation passes
- Publication-ready output
- Methodology documentation

**Subtask Distribution:**
```yaml
Exhaustive_Depth:
  Discovery: 6 subtasks
    - "Systematic query generation (15+ variants)"
    - "Exhaustive source search (30+ sources)"
    - "Citation graph traversal"
    - "Grey literature search"
    - "Expert/authority identification"
    - "Source quality + bias assessment"
  
  Deep_Dive: 18 subtasks
    - "Full extraction of all relevant sources"
    - "Multi-tool fallback for each source"
    - "Structured data extraction to database"
    - "Temporal trend analysis"
    - "Geographic coverage analysis"
    - "Stakeholder perspective mapping"
    - "Technical deep-dives (multiple)"
    - "Reproduction of key claims"
    - "Statistical validation (if applicable)"
    - "Contradiction resolution"
    - "Confidence scoring per claim"
    - "Gap analysis with explicit limitations"
    - "Multiple supplementary search rounds"
    - "Archive/historical comparison"
    - "Cross-language source inclusion"
    - "Full data lineage tracking"
  
  Synthesis: 6 subtasks
    - "Multi-dimensional theme analysis"
    - "Evidence hierarchy construction"
    - "Scenario analysis (if applicable)"
    - "Iterative narrative refinement"
    - "Executive summaries (multiple lengths)"
    - "Visualizations + data tables"
  
  Validation: 5 subtasks
    - "100% fact verification"
    - "Source link validation"
    - "External expert review (if applicable)"
    - "Reproducibility verification"
    - "Bias audit"
  
  Output: 3 subtasks
    - "Full publication-ready report"
    - "Methodology appendix"
    - "Raw data + reproducibility package"
```

**Cost Estimate:** $2.00 - $10.00+

### 6.6 Depth Selection Guidelines

| User Signal | Recommended Depth |
|-------------|-------------------|
| "Quick check", "briefly", "tldr" | Quick |
| No depth signal | Standard (default) |
| "Thorough", "detailed", "comprehensive" | Deep |
| "Exhaustive", "complete", "academic", "publish" | Exhaustive |
| "Urgent", "ASAP", "fast" | Quick or Standard |
| Follow-up to previous research | Previous depth + 1 |
| Budget mentioned / constrained | Reduce by 1 level |

---

## 7. Parallelization Rules

### 7.1 Parallelization Framework

```yaml
Parallelization_Principles:
  Always_Parallel:
    - "Independent search queries"
    - "Fetching different URLs"
    - "File parsing (multiple files)"
    - "Fact verification checks"
    - "Source quality scoring"
    - "Content extraction from different sources"
  
  Never_Parallel:
    - "Query depends on previous query results"
    - "Synthesis depends on extraction completion"
    - "Validation depends on synthesis output"
    - "Narrative construction depends on theme identification"
    - "Output formatting depends on final content"
    - "Cross-reference analysis depends on all extractions"
  
  Conditional_Parallel:
    - "Deep extraction: parallel if sources independent"
    - "Supplementary search: parallel to synthesis if gap found early"
    - "Multi-tool fallback: parallel attempt if uncertain which tool works"
```

### 7.2 Max Parallel Agents per Depth Level

| Depth | Max Parallel | Rationale |
|-------|-------------|-----------|
| Quick | 5 | Fast turnaround, limited value from more parallelism |
| Standard | 10 | Balance speed and cost |
| Deep | 15 | Complex research benefits from parallel deep-dives |
| Exhaustive | 20 | Maximum throughput for long-running research |

### 7.3 Route-Specific Parallelization

```yaml
Route_A_Parallelization:
  Phase1_Discovery:
    parallel: true
    max_agents: "min(source_count, max_parallel)"
    pattern: "Each agent handles 1 source"
  
  Phase2_DeepDive:
    parallel: true
    max_agents: "min(priority_sources, 5)"
    pattern: "Top N sources in parallel"
  
  Phase3_Synthesis:
    parallel: false
    depends_on: "All Phase2 agents complete"
  
  Phase4_Validation:
    parallel: true
    max_agents: "min(claims_to_verify, 5)"
    pattern: "Spot-check claims in parallel"

Route_B_Parallelization:
  Phase1_Discovery:
    parallel: true
    max_agents: 3
    pattern: "Official + Community + Technical"
  
  Phase2_DeepDive:
    parallel: true
    max_agents: 3
    pattern: "Docs + Code + Discussion"
  
  Phase3_Synthesis:
    parallel: false
    depends_on: "Technical validation complete"

Route_C_Parallelization:
  All_Phases:
    parallel: true
    max_agents: "file_count"
    note: "All files processed simultaneously"
    exception: "Cross-document synthesis is sequential"

Route_D_Parallelization:
  Phase1_Discovery:
    parallel: true
    max_agents: "file_count + 3"
    pattern: "All files + 3 web queries in parallel"
  
  Phase2_DeepDive:
    parallel: true
    max_agents: 5
    pattern: "File analysis + Web extraction + Cross-ref"
  
  Phase3_Synthesis:
    parallel: false
    depends_on: "Both file and web analysis complete"
```

### 7.4 Dependency Graph Example (Route A, Standard Depth)

```
[Discovery]                    [Deep Dive]                   [Synthesis]
┌─────────────┐               ┌─────────────┐              ┌─────────────┐
│ Query Exp   │               │ Extract S1  │────┐         │ Theme ID    │
│ (parallel)  │──┐            │ Extract S2  │────┤         │ (sequential)│
│             │  │            │ Extract S3  │────┼──┐      └──────┬──────┘
│ Q1 → Search │  │            │ Extract S4  │────┤  │             │
│ Q2 → Search │──┼──┐         │ Extract S5  │────┘  │             │
│ Q3 → Search │  │  │         └─────────────┘       │      ┌──────▼──────┐
│ Q4 → Search │──┘  │                  │            │      │ Narrative   │
│ Q5 → Search │     │                  └────────────┘      │ Writing     │
└─────────────┘     │                                     └──────┬──────┘
                    │                                            │
                    │              [Validation]                  │
                    │              ┌─────────────┐               │
                    │              │ Verify C1   │────┐          │
                    └─────────────►│ Verify C2   │────┼──────────┘
                                   │ Verify C3   │────┘
                                   └─────────────┘
```

### 7.5 Parallelization Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| "Shotgun parallel" — запускать всё подряд | Перерасход на нерелевантных источниках | Quality gating перед parallel execution |
| "False parallelism" — параллельные задачи с shared state | Race conditions, inconsistent data | Immutable data per agent, merge only at phase boundaries |
| "Over-parallelization" — слишком мелкое дробление | Накладные расходы на coordination | Min task size: 30 seconds of work |
| "Sequential bias" — делать последовательно из осторожности | Ненужные задержки | Explicit dependency declaration |
| "Cascading dependencies" — каждая задача ждёт предыдущую | Отсутствие параллелизма | Look-ahead execution для независимых подзадач |

---

## 8. Cost Budgeting

### 8.1 Budget Tiers

```yaml
Budget_Tiers:
  Low:
    max_cost: "$0.10"
    description: "Minimal cost, basic research"
    default_depth: "Quick"
    available_routes: ["A", "B", "C"]
    tool_restrictions:
      - "Firecrawl batch only"
      - "No Obscura (unless Firecrawl fails)"
      - "No CloakBrowser"
      - "LLM: light synthesis only"
    early_stop: "After $0.08"
  
  Medium:
    max_cost: "$0.50"
    description: "Standard research, good coverage"
    default_depth: "Standard"
    available_routes: ["A", "B", "C", "D"]
    tool_restrictions:
      - "Firecrawl + Obscura allowed"
      - "CloakBrowser: 1 use max"
      - "LLM: standard synthesis"
    early_stop: "After $0.40"
  
  High:
    max_cost: "$2.00"
    description: "Deep research, comprehensive"
    default_depth: "Deep"
    available_routes: ["A", "B", "C", "D"]
    tool_restrictions:
      - "All tools available"
      - "CloakBrowser: unlimited"
      - "LLM: extended synthesis"
      - "Code execution: allowed"
    early_stop: "After $1.60"
  
  Unlimited:
    max_cost: "No limit"
    description: "Maximum completeness"
    default_depth: "Exhaustive"
    available_routes: ["A", "B", "C", "D"]
    tool_restrictions: "None"
    early_stop: "None (run to completion)"
    soft_guidance: "Warn if projecting > $5.00"
```

### 8.2 Cost Allocation per Phase

| Phase | Low | Medium | High | Unlimited |
|-------|-----|--------|------|-----------|
| Discovery | 40% | 25% | 20% | 15% |
| Deep Dive | 30% | 35% | 35% | 35% |
| Synthesis | 20% | 25% | 25% | 25% |
| Validation | 10% | 15% | 20% | 25% |

### 8.3 Tool Cost Matrix

| Tool | Cost per Use | When to Use | When to Avoid |
|------|-------------|-------------|---------------|
| Firecrawl (batch) | $0.005 | Discovery, simple sites | JS-heavy sites |
| Firecrawl (single) | $0.01 | Targeted extraction | Budget constraints |
| Firecrawl (detailed) | $0.03 | Deep extraction of key pages | Low budget |
| Obscura | $0.02 | JS sites, dynamic content | Simple static pages |
| CloakBrowser | $0.05 | Protected/WAF sites | Normal sites |
| LLM (light) | $0.005 | Quick synthesis | Complex analysis |
| LLM (standard) | $0.02 | Standard synthesis | Budget mode |
| LLM (extended) | $0.05 | Deep synthesis | Low budget |
| Code Execution | $0.001 | Validation, data processing | N/A |

### 8.4 Cost Control Mechanisms

```yaml
Cost_Control:
  Pre_Execution:
    - "Estimate cost based on route + depth"
    - "Warn user if estimate > tier limit"
    - "Suggest depth reduction if needed"
  
  During_Execution:
    - "Track cumulative cost per phase"
    - "Check against budget at each phase gate"
    - "Apply tool substitution if over 80% budget"
    - "Reduce scope if over 90% budget"
  
  Tool_Substitution_Hierarchy:
    if_over_budget:
      - "Replace Obscura → Firecrawl batch"
      - "Replace Firecrawl detailed → Firecrawl single"
      - "Replace LLM extended → LLM standard"
      - "Reduce source count by 50%"
      - "Skip validation phase (spot-check only)"
  
  Early_Stopping_Criteria:
    Low:
      - "80% budget spent"
      - "Minimum viable output achieved"
      action: "Complete with current results, flag as partial"
    
    Medium:
      - "80% budget spent"
      - "Quality gate 3 passed"
      action: "Skip to validation + output"
    
    High:
      - "80% budget spent"
      - "All quality gates passed"
      action: "Reduce validation scope, complete"
    
    Unlimited:
      - "Projected cost > $5.00 → warn user"
      - "Projected cost > $10.00 → require confirmation"
```

### 8.5 Cost Estimation Formula

```python
def estimate_cost(route, depth, source_count_hint=None):
    """
    Estimates total cost before execution.
    Returns: {estimated_cost, confidence_range, breakdown}
    """
    base_costs = {
        "A": {"Quick": 0.03, "Standard": 0.15, "Deep": 0.80, "Exhaustive": 3.00},
        "B": {"Quick": 0.02, "Standard": 0.12, "Deep": 0.60, "Exhaustive": 2.50},
        "C": {"Quick": 0.01, "Standard": 0.05, "Deep": 0.20, "Exhaustive": 1.00},
        "D": {"Quick": 0.04, "Standard": 0.25, "Deep": 1.20, "Exhaustive": 5.00}
    }
    
    source_multiplier = 1.0
    if source_count_hint:
        if source_count_hint > 20:
            source_multiplier = 1.5
        elif source_count_hint > 10:
            source_multiplier = 1.2
        elif source_count_hint < 3:
            source_multiplier = 0.7
    
    protection_likelihood = {
        "A": 0.2, "B": 0.1, "C": 0.0, "D": 0.15
    }
    
    protection_multiplier = 1 + (protection_likelihood[route] * 0.5)  # 50% cost increase for protected sites
    
    base = base_costs[route][depth]
    estimated = base * source_multiplier * protection_multiplier
    
    return {
        "estimated_cost": round(estimated, 2),
        "confidence_range": (round(estimated * 0.7, 2), round(estimated * 1.3, 2)),
        "breakdown": {
            "base": base,
            "source_multiplier": source_multiplier,
            "protection_multiplier": protection_multiplier
        }
    }
```

---

## 9. Quality Gates & Validation

### 9.1 Universal Quality Gates

Каждый Route и Depth level использует единый набор quality gates, адаптированный по строгости.

```yaml
Quality_Gate_Framework:
  Gate_L1_Existence:
    description: "Content exists and is extractable"
    checks:
      - "Non-empty extraction from source"
      - "Extracted content > 100 tokens"
      - "No extraction errors"
    severity: "BLOCKING"
  
  Gate_L2_Relevance:
    description: "Content matches query intent"
    checks:
      - "Semantic similarity to query > threshold"
      - "At least 1 relevant passage per source"
      - "Source topic matches query domain"
    severity: "WARNING"
  
  Gate_L3_Coverage:
    description: "Sufficient breadth of research"
    checks:
      - "Min source count met"
      - "Domain diversity achieved"
      - "No single source dominates (>40%)"
    severity: "WARNING"
  
  Gate_L4_Accuracy:
    description: "Factual claims are verifiable"
    checks:
      - "Spot-check facts against sources"
      - "No hallucinated statistics"
      - "Dates and numbers consistent"
    severity: "BLOCKING"
  
  Gate_L5_Currency:
    description: "Information is up-to-date"
    checks:
      - "Source publication date within acceptable range"
      - "No broken links (sample)"
      - "Pricing/data from current period"
    severity: "ADVISORY"
  
  Gate_L6_Synthesis:
    description: "Output is coherent and useful"
    checks:
      - "Answer addresses original question"
      - "Structure follows best practices"
      - "Citations present for major claims"
      - "Confidence levels stated"
    severity: "BLOCKING"
```

### 9.2 Depth-Level Quality Thresholds

| Gate | Quick | Standard | Deep | Exhaustive |
|------|-------|----------|------|------------|
| L1 Existence | 80% pass | 90% pass | 95% pass | 98% pass |
| L2 Relevance | 70% pass | 80% pass | 90% pass | 95% pass |
| L3 Coverage | 3 sources | 8 sources | 15 sources | 25 sources |
| L4 Accuracy | Spot-check 1 | Spot-check 20% | Spot-check 50% | Verify 100% |
| L5 Currency | Any date | < 2 years | < 1 year | < 6 months |
| L6 Synthesis | Brief answer | Structured | Comprehensive | Publication-ready |

### 9.3 Auto-Remediation Actions

```yaml
Auto_Remediation:
  L1_Existence_Fail:
    - "Retry with alternative tool"
    - "Reduce extraction depth"
    - "Flag source as failed, continue"
    max_retries: 2
  
  L2_Relevance_Fail:
    - "Refine query"
    - "Add exclusion terms"
    - "Remove source from pool"
  
  L3_Coverage_Fail:
    - "Expand query set"
    - "Add related topics"
    - "Reduce depth threshold"
  
  L4_Accuracy_Fail:
    - "Flag claim as unverified"
    - "Search for corroborating source"
    - "Remove claim if unverifiable"
  
  L5_Currency_Fail:
    - "Add freshness warning"
    - "Search for updated source"
    - "Note date in output"
  
  L6_Synthesis_Fail:
    - "Restructure output"
    - "Add missing sections"
    - "Escalate to higher-capacity model"
```

---

## 10. Error Handling & Fallbacks

### 10.1 Tool Failure Matrix

| Scenario | Primary Action | Fallback | Last Resort |
|----------|---------------|----------|-------------|
| Firecrawl timeout | Retry once | Switch to Obscura | Skip source, note in output |
| Obscura blocked | Retry with different proxy | Switch to CloakBrowser | Skip source, note in output |
| CloakBrowser fail | Retry once | Switch to Obscura | Manual flag for user |
| LLM rate limit | Backoff 5s, retry | Reduce request size | Use lighter model |
| All web tools fail | — | Use cached results if available | Inform user, suggest File-only route |
| File parse fail | Try alternative parser | Extract raw text | Inform user of unsupported format |

### 10.2 Degradation Cascade

```
Full Functionality
    │
    ▼ (tool failure)
Reduced Toolset
    │
    ▼ (budget exceeded)
Minimal Toolset
    │
    ▼ (multiple failures)
Partial Results + Explanation
    │
    ▼ (critical failure)
User Notification + Recommendations
```

### 10.3 Recovery Patterns

```yaml
Recovery_Patterns:
  Circuit_Breaker:
    description: "Temporarily disable failing tool"
    threshold: "3 failures in 5 minutes"
    recovery_time: "10 minutes"
    fallback: "Use alternative tools"
  
  Retry_With_Backoff:
    description: "Exponential backoff for transient failures"
    max_retries: 3
    backoff: "1s, 2s, 4s"
    applies_to: ["Firecrawl", "Obscura", "LLM"]
  
  Graceful_Degradation:
    description: "Reduce scope but deliver value"
    triggers: ["budget 80%", "time limit", "tool unavailability"]
    actions:
      - "Reduce source count"
      - "Use faster/cheaper tools"
      - "Skip non-critical validation"
      - "Deliver partial results"
  
  Checkpoint_Recovery:
    description: "Save progress at each phase"
    save_points: ["Post-Discovery", "Post-DeepDive", "Post-Synthesis"]
    benefit: "Resume from last checkpoint on failure"
```

---

## 11. Implementation Roadmap

### 11.1 Phase 1: Foundation (Week 1-2)

```yaml
Phase1_Foundation:
  deliverables:
    - "Task Router (Layer 1 + 2)"
    - "Route A execution pipeline"
    - "Quick + Standard depth levels"
    - "Basic quality gates (L1-L3)"
    - "Low + Medium budget tiers"
  
  components:
    - "Keyword matcher with hash table"
    - "Pattern classifier with regex library"
    - "Firecrawl integration (batch + single)"
    - "Basic LLM synthesis pipeline"
    - "Cost tracker"
  
  success_criteria:
    - "90%+ routing accuracy on test set"
    - "Average Quick research < 30 min"
    - "Average Standard research < 2 hours"
    - "Cost within budget tier 95% of time"
```

### 11.2 Phase 2: Enhancement (Week 3-4)

```yaml
Phase2_Enhancement:
  deliverables:
    - "Route B + C execution pipelines"
    - "LLM Router (Layer 3) for edge cases"
    - "Deep depth level"
    - "Obscura integration"
    - "Full quality gates (L1-L6)"
    - "High budget tier"
  
  components:
    - "Obscura headless browser integration"
    - "File parser library (PDF, DOCX, CSV, etc.)"
    - "LLM-based disambiguation"
    - "Cross-reference analyzer"
    - "Enhanced cost estimation"
  
  success_criteria:
    - "95%+ routing accuracy"
    - "Route B focused questions answered precisely"
    - "Route C file analysis working"
    - "Deep research completes in 3-5 hours"
```

### 11.3 Phase 3: Advanced (Week 5-6)

```yaml
Phase3_Advanced:
  deliverables:
    - "Route D (File-Augmented)"
    - "Exhaustive depth level"
    - "CloakBrowser integration"
    - "Unlimited budget tier"
    - "Advanced parallelization"
    - "Full error recovery"
  
  components:
    - "CloakBrowser proxy rotation"
    - "Recursive search algorithm"
    - "Citation graph traversal"
    - "Advanced parallel orchestrator"
    - "Checkpoint/recovery system"
  
  success_criteria:
    - "All routes functional"
    - "Exhaustive research produces publication-ready output"
    - "Zero data loss on failures (checkpoint recovery)"
    - "Tool failure auto-remediation works"
```

### 11.4 Phase 4: Optimization (Week 7-8)

```yaml
Phase4_Optimization:
  deliverables:
    - "Performance optimization"
    - "Cost optimization"
    - "User feedback integration"
    - "Analytics dashboard"
    - "Documentation"
  
  focus_areas:
    - "Parallel execution efficiency"
    - "Cache hit rates"
    - "Cost per research task"
    - "User satisfaction scores"
    - "Routing accuracy improvements"
```

---

## 12. Appendices

### Appendix A: Route Decision Quick Reference

| If query contains... | And has files... | Then Route | Sub-route likely |
|---------------------|------------------|------------|------------------|
| "landscape", "overview", "players" | No | A | A1 |
| "trends", "future", "outlook" | No | A | A2 |
| "X vs Y", "comparison" | No | A | A3 |
| "regulation", "compliance", "GDPR" | No | A | A4 |
| "how does X work", "architecture" | No | B | B1 |
| "error", "not working", "bug" | No | B | B2 |
| "integrate X with Y" | No | B | B3 |
| "pricing", "cost", "business model" | No | B | B4 |
| "summarize this file" | Yes | C | C1 |
| "compare these documents" | Yes (multiple) | C | C2 |
| "extract as table" | Yes | C | C3 |
| "validate against market" | Yes | D | D1 |
| "benchmark against industry" | Yes | D | D2 |
| "what are we missing" | Yes | D | D3 |

### Appendix B: Tool Selection Decision Tree

```
Need to fetch web content?
├── Yes → Is it a protected/WAF site?
│   ├── Yes → CloakBrowser
│   └── No → Is it JS-heavy?
│       ├── Yes → Obscura
│       └── No → Firecrawl
│
└── No → Working with files?
    ├── Yes → What format?
    │   ├── PDF → pdfplumber / PyPDF2
    │   ├── DOCX → python-docx
    │   ├── CSV/JSON → pandas
    │   └── TXT/MD → direct read
    │
    └── No → Synthesis only?
        └── Yes → LLM (tier-appropriate)
```

### Appendix C: Cost Optimization Cheat Sheet

| Situation | Optimization |
|-----------|-------------|
| Budget running low | Switch Firecrawl detailed → batch |
| JS site not needed | Skip Obscura, use Firecrawl |
| Repeated similar queries | Cache results, reuse |
| Many sources needed | Batch where possible |
| Only summary needed | Skip deep extraction |
| Validation expensive | Spot-check instead of full verify |
| LLM cost high | Use lighter model for synthesis |
| Time critical | Parallelize more, accept higher cost |

### Appendix D: Sub-route Pattern Library

```yaml
Sub_Route_Patterns:
  A1_Industry_Landscape:
    query_patterns:
      - "{industry} landscape"
      - "key players in {industry}"
      - "{industry} market overview"
      - "who are the leaders in {industry}"
    entities_required: ["industry/sector name"]
    
  A2_Trend_Analysis:
    query_patterns:
      - "{topic} trends"
      - "future of {topic}"
      - "where is {topic} heading"
      - "{topic} outlook 202{5-8}"
    entities_required: ["topic/technology"]
    
  A3_Technology_Comparison:
    query_patterns:
      - "{tech1} vs {tech2}"
      - "{tech1} or {tech2}"
      - "compare {tech1} and {tech2}"
    entities_required: ["2+ technologies to compare"]
    
  A4_Regulatory_Landscape:
    query_patterns:
      - "{regulation} requirements"
      - "{regulation} compliance"
      - "{topic} regulations"
    entities_required: ["regulation name or domain"]
    
  B1_Product_Deep_Dive:
    query_patterns:
      - "how does {product} work"
      - "{product} architecture"
      - "{product} features"
      - "{product} review"
    entities_required: ["product/company name"]
    
  B2_Troubleshooting:
    query_patterns:
      - "{product} error {code}"
      - "{product} not working"
      - "{product} fails with {symptom}"
    entities_required: ["product name", "error/symptom"]
    
  B3_Integration:
    query_patterns:
      - "{product1} {product2} integration"
      - "connect {product1} to {product2}"
      - "{product1} with {product2} setup"
    entities_required: ["2+ products to integrate"]
    
  B4_Pricing:
    query_patterns:
      - "{product} pricing"
      - "{product} cost"
      - "{product} business model"
    entities_required: ["product/company name"]
    
  C1_Document_Analysis:
    query_patterns:
      - "summarize this {document}"
      - "analyze this {document}"
      - "what are the key points in this {document}"
    entities_required: ["file reference"]
    
  C2_Cross_Document:
    query_patterns:
      - "compare these documents"
      - "find inconsistencies"
      - "synthesize across files"
    entities_required: ["multiple files"]
    
  C3_Data_Extraction:
    query_patterns:
      - "extract as {format}"
      - "convert to {format}"
      - "pull all {data_type}"
    entities_required: ["file reference", "target format/type"]
    
  D1_Document_Validation:
    query_patterns:
      - "check if this is up to date"
      - "validate against {standard}"
      - "verify these claims"
    entities_required: ["file reference", "validation target"]
    
  D2_Market_Benchmarking:
    query_patterns:
      - "how do we compare to market"
      - "benchmark against {standard}"
      - "are we competitive"
    entities_required: ["internal data (files)", "benchmark target"]
    
  D3_Gap_Analysis:
    query_patterns:
      - "what are we missing"
      - "gaps in our {domain}"
      - "compared to best practices"
    entities_required: ["internal data (files)", "reference standard"]
```

### Appendix E: Confidence Scoring Framework

```yaml
Confidence_Scoring:
  Source_Level:
    factors:
      - "Domain authority (.edu, .gov, official): +0.3"
      - "Publication date (recent): +0.2"
      - "Author expertise: +0.2"
      - "Citation count: +0.1"
      - "Primary vs secondary: +0.2"
    scale: "0.0 to 1.0"
  
  Claim_Level:
    factors:
      - "Multiple corroborating sources: +0.4"
      - "Primary source verification: +0.3"
      - "Statistical evidence: +0.2"
      - "Expert consensus: +0.1"
    scale: "0.0 to 1.0"
  
  Output_Level:
    High: "0.8-1.0 — Strong evidence, verified"
    Medium: "0.5-0.79 — Reasonable evidence, some uncertainty"
    Low: "0.2-0.49 — Limited evidence, preliminary"
    Speculative: "0.0-0.19 — Hypothesis, needs validation"
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-06-28 | Initial version — full architecture, all routes, depth levels, cost model |

---

*End of Strategy Guide*
