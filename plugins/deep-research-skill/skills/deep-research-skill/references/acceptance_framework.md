# Deep Research Skill — Acceptance Framework

> **Version:** 1.0  
> **Purpose:** Определяет систему качества, критерии приёмки, quality gates и протоколы исправления для Deep Research Skill.  
> **Philosophy:** *Quality is not an act, it is a habit* — каждый этап проверяется, каждое утверждение оценивается, каждый провал анализируется.

---

## Table of Contents

1. [Acceptance Criteria Templates](#1-acceptance-criteria-templates)
2. [Quality Gates](#2-quality-gates)
3. [Root Cause Analysis Protocol](#3-root-cause-analysis-protocol)
4. [Re-search Loop Logic](#4-re-search-loop-logic)
5. [Confidence Scoring System](#5-confidence-scoring-system)
6. [Source Quality Rating](#6-source-quality-rating)
7. [Completeness Metrics](#7-completeness-metrics)
8. [Integration Flow](#8-integration-flow)
9. [Appendices](#9-appendices)

---

## 1. Acceptance Criteria Templates

### 1.1 AC Template Structure

Каждый research task получает набор AC, сформулированных ДО начала сбора. AC структурируются по принципу **SMART-R** (Specific, Measurable, Achievable, Relevant, Research-bound).

```
AC-[TYPE]-[ID]: [Критерий]
├── Priority: [P0 | P1 | P2]
├── Measurement: [Как измеряем]
├── Threshold: [Порог pass/fail]
└── Owner: [Кто отвечает за проверку]
```

### 1.2 Task-Type Specific Templates

#### Template R — Research (Исследование темы)

| ID | Criterion | Metric | Pass Threshold | Priority |
|----|-----------|--------|----------------|----------|
| R-01 | Source Coverage | % релевантных источников из доступного pool | ≥ 70% | P0 |
| R-02 | Source Diversity | Число уникальных типов источников | ≥ 4 типа | P0 |
| R-03 | Depth Level | Количество уровней детализации по каждому подтопику | ≥ 3 уровня (overview → detailed → granular) | P0 |
| R-04 | Freshness | % данных не старше freshness window | ≥ 60% за 12 мес | P1 |
| R-05 | Cross-verification | Ключевые факты подтверждены N источниками | ≥ 2 независимых подтверждения | P0 |
| R-06 | Bias Detection | Выявлены и аннотированы источники со специфическим bias | 100% спорных утверждений помечены | P1 |
| R-07 | Geographic Coverage | Охват регионов/рынков | Все заявленные рынки покрыты | P1 |

#### Template A — Analysis (Анализ данных)

| ID | Criterion | Metric | Pass Threshold | Priority |
|----|-----------|--------|----------------|----------|
| A-01 | Data Completeness | % ячеек/полей с данными vs. ожидаемых | ≥ 85% | P0 |
| A-02 | Methodology Soundness | Применённые методы соответствуют best practices | Peer-review pass | P0 |
| A-03 | Assumption Documentation | Все ключевые допущения документированы | 100% критичных допущений явно указаны | P0 |
| A-04 | Sensitivity Check | Анализ чувствительности для ключевых выводов | Выполнен для ≥ 3 ключевых переменных | P1 |
| A-05 | Outlier Treatment | Выбросы идентифицированы и обработаны | 100% выбросов аннотированы | P1 |
| A-06 | Statistical Significance | Ключевые корреляции проверены на значимость | p < 0.05 или置信区间 указан | P1 |

#### Template C — Comparison (Сравнительный анализ)

| ID | Criterion | Metric | Pass Threshold | Priority |
|----|-----------|--------|----------------|----------|
| C-01 | Entity Coverage | Число сущностей в сравнении | ≥ заявленное в scope | P0 |
| C-02 | Dimension Parity | Все сущности оценены по одинаковым критериям | 100% критериев применены ко всем | P0 |
| C-03 | Fair Baseline | Базовые условия сравнения определены и задокументированы | Да/Нет | P0 |
| C-04 | Missing Data Handling | Пропуски в данных обработаны прозрачно | Все gaps аннотированы с explanation | P1 |
| C-05 | Temporal Alignment | Данные приведены к общему временному срезу | ≥ 80% данных в ±3 мес окне | P1 |
| C-06 | Qualitative Factors | Неколичественные факторы учтены и аннотированы | ≥ 3 качественных аспекта | P2 |

#### Template S — Synthesis (Синтез и выводы)

| ID | Criterion | Metric | Pass Threshold | Priority |
|----|-----------|--------|----------------|----------|
| S-01 | Claim-Evidence Link | Каждый вывод связан с evidence | 100% claims → ≥ 1 source | P0 |
| S-02 | Logical Coherence | Аргументация логически непротиворечива | 0 критических logical fallacies | P0 |
| S-03 | Alternative Explanations | Рассмотрены альтернативные интерпретации | ≥ 2 альтернативы для каждого ключевого вывода | P1 |
| S-04 | Confidence Calibration | Каждый вывод оценён по шкале confidence | 100% claims scored | P0 |
| S-05 | Actionability | Выводы приводят к actionable рекомендациям | ≥ 70% выводов → recommendation | P1 |
| S-06 | Uncertainty Quantification | Неопределённость явно указана | Для всех P0-выводов | P1 |

### 1.3 Freshness Criteria by Domain

| Domain | Freshness Window | P0 Threshold | P1 Threshold |
|--------|------------------|--------------|--------------|
| Breaking News / Crises | 7 days | ≥ 80% ≤ 7d | ≥ 95% ≤ 30d |
| Technology / Product | 6 months | ≥ 60% ≤ 6mo | ≥ 80% ≤ 12mo |
| Markets / Finance | 3 months | ≥ 70% ≤ 3mo | ≥ 90% ≤ 6mo |
| Academic Research | 24 months | ≥ 40% ≤ 24mo | ≥ 60% ≤ 36mo |
| Regulatory / Legal | 12 months | ≥ 60% ≤ 12mo | ≥ 80% ≤ 18mo |
| Historical / Strategic | 60 months | ≥ 30% ≤ 60mo | ≥ 50% ≤ 120mo |

### 1.4 Cross-Verification Rules

```
Verification Level: V1 (Minimum) | V2 (Standard) | V3 (Maximum)

V1 [Default]:
  - Каждый ключевой факт подтверждён ≥ 2 независимыми источниками
  - Источники должны быть разных типов (e.g., не 2 новостных статьи от одного агентства)

V2 [High-stakes]:
  - Каждый ключевой факт подтверждён ≥ 3 независимыми источниками
  - ≥ 1 подтверждение из Tier S или Tier A
  - Проверка на circular reporting (A цитирует B, B цитирует A)

V3 [Critical]:
  - Каждый факт подтверждён ≥ 3 источниками
  - ≥ 1 первичный источник (Tier S)
  - Primary source verification: данные проверены по оригиналу
  - Conflicting evidence: задокументированы и разрешены
```

### 1.5 Coverage Criteria Calculator

```
Expected Source Pool (ESP) = Оценка числа релевантных источников по теме
  └─ Определяется через: поисковые запросы + аналогичные исследования + expert estimate

Actual Source Coverage (ASC) = Found / ESP × 100%

Pass: ASC ≥ 70%
Warn: 50% ≤ ASC < 70%
Fail: ASC < 50%
```

---

## 2. Quality Gates

### 2.1 Gate Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Gate 1:    │───▶│  Gate 2:    │───▶│  Gate 3:    │───▶│  Gate 4:    │───▶│  Gate 5:    │
│Post-Collect │    │Post-Process │    │Post-Analyze │    │Post-Synth   │    │Final Output │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
   Raw Data           Clean Data          Insights          Conclusions        Deliverable
```

**Правило:** Gate является **binary** — либо PASS (переход к следующему), либо FAIL (RCA + re-work/re-search). Нет partial credit.

### 2.2 Gate 1: Post-Collection

**Trigger:** Сбор сырых данных завершён.

| # | Checklist Item | Pass Criteria | Fail Action |
|---|---------------|---------------|-------------|
| 1.1 | Минимальное число источников собрано | ≥ N (определяется scope) | Re-search: expand queries |
| 1.2 | Source diversity достигнута | ≥ 4 типа источников | Re-search: target missing types |
| 1.3 | Tier quality threshold met | ≥ 60% источников Tier B+ | Re-search: target higher-tier sources |
| 1.4 | Данные не устарели | ≥ 60% в freshness window | Re-search: target recent sources |
| 1.5 | Нет критических tool failures | 0 blocking errors | RCA → retry with fallback tool |
| 1.6 | Raw data сохранены в checkpoint | Checkpoint artifact создан | Create checkpoint → retry |
| 1.7 | Metadata собраны для всех источников | 100% источников с author, date, publisher | Backfill metadata |

**Gate 1 Output:**
- Status: `[PASS / FAIL]`
- Raw Data Checkpoint: `[artifact_id]`
- Source Inventory: `[table with sources]`
- Issues Log: `[if any]`

### 2.3 Gate 2: Post-Processing

**Trigger:** Очистка, дедупликация, структурирование данных завершены.

| # | Checklist Item | Pass Criteria | Fail Action |
|---|---------------|---------------|-------------|
| 2.1 | Дедупликация выполнена | < 5% дубликатов | Re-run dedup algorithm |
| 2.2 | Данные структурированы | 100% данных в схеме | Restructure |
| 2.3 | PII/чувствительные данные обработаны | 0 утечек PII | Redact + audit |
| 2.4 | Data quality score | ≥ 8/10 по внутренней шкале | Cleanse data |
| 2.5 | Processing artifact сохранён | Checkpoint создан | Create checkpoint |
| 2.6 | Потери данных в процессе | < 10% полезных данных | Review pipeline |
| 2.7 | Нормализация форматов | Все даты, числа, валюты — единый формат | Normalize |

**Gate 2 Output:**
- Status: `[PASS / FAIL]`
- Processed Data Checkpoint: `[artifact_id]`
- Data Quality Report: `[score + issues]`

### 2.4 Gate 3: Post-Analysis

**Trigger:** Анализ данных (паттерны, корреляции, тренды) завершён.

| # | Checklist Item | Pass Criteria | Fail Action |
|---|---------------|---------------|-------------|
| 3.1 | Аналитические вопросы отвечены | 100% P0 questions answered | Expand analysis scope |
| 3.2 | Key findings подтверждены данными | Каждый finding → ≥ 3 data points | Strengthen evidence |
| 3.3 | Статистическая значимость проверена | p-values / CIs reported | Re-run stats |
| 3.4 | Assumptions документированы | 100% критичных допущений | Document assumptions |
| 3.5 | Bias mitigation применён | Known biases addressed | Apply corrections |
| 3.6 | Analysis artifact сохранён | Checkpoint создан | Create checkpoint |
| 3.7 | Peer-review по методологии | 0 критических замечаний | Revise methodology |

**Gate 3 Output:**
- Status: `[PASS / FAIL]`
- Analysis Checkpoint: `[artifact_id]`
- Key Findings Draft: `[document]`
- Assumptions Log: `[document]`

### 2.5 Gate 4: Post-Synthesis

**Trigger:** Синтез выводов, формирование рекомендаций завершены.

| # | Checklist Item | Pass Criteria | Fail Action |
|---|---------------|---------------|-------------|
| 4.1 | Все findings синтезированы в выводы | 100% P0 findings → conclusion | Expand synthesis |
| 4.2 | Claim-evidence links проверены | 100% claims → sources | Add citations |
| 4.3 | Confidence scores присвоены | 100% claims scored | Score all claims |
| 4.4 | Альтернативы рассмотрены | ≥ 2 альтернативы на ключевой вывод | Research alternatives |
| 4.5 | Непротиворечивость | 0 критических contradictions | Resolve contradictions |
| 4.6 | Actionable recommendations | ≥ 70% conclusions → action | Reframe conclusions |
| 4.7 | Synthesis artifact сохранён | Checkpoint создан | Create checkpoint |

**Gate 4 Output:**
- Status: `[PASS / FAIL]`
- Synthesis Checkpoint: `[artifact_id]`
- Recommendations Draft: `[document]`

### 2.6 Gate 5: Final Output

**Trigger:** Финальный отчёт сформирован.

| # | Checklist Item | Pass Criteria | Fail Action |
|---|---------------|---------------|-------------|
| 5.1 | Completeness metrics | Все 4 метрики ≥ threshold | Re-work specific metric |
| 5.2 | Source attribution | 100% claims с цитатами | Add missing citations |
| 5.3 | Confidence visualization | All claims confidence-scored и отображены | Add scores |
| 5.4 | Executive summary | ≤ 1 страница, covers all key points | Rewrite summary |
| 5.5 | Appendices & data | Все данные доступны для audit | Package appendices |
| 5.6 | Format compliance | Соответствует шаблону вывода | Format |
| 5.7 | Final quality score | ≥ 4.0 / 5.0 overall | Re-work |

**Gate 5 Output:**
- Status: `[PASS / FAIL]`
- Final Report: `[artifact_id]`
- Quality Certificate: `[score card]`
- Audit Trail: `[full log]`

### 2.7 Gate Escalation Matrix

| Gate | Max Retries | Escalation Trigger | Escalation Action |
|------|-------------|--------------------|--------------------|
| Gate 1 | 3 | После 3-х fails | Human-in-the-loop: смена инструментов/scope |
| Gate 2 | 2 | После 2-х fails | Human: review data pipeline |
| Gate 3 | 3 | После 3-х fails | Human: revise analytical framework |
| Gate 4 | 2 | После 2-х fails | Human: restructuring |
| Gate 5 | 2 | После 2-х fails | Human: final review + override |

---

## 3. Root Cause Analysis Protocol

### 3.1 RCA Framework: DMAIC-R

Адаптация Six Sigma DMAIC для research-контекста:

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Define   │──▶│ Measure  │──▶│ Analyze  │──▶│ Improve  │──▶│ Control  │
│ Проблема │   │ Масштаб  │   │ Причина  │   │ Исправл. │   │ Предотв. │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
   5 мин           10 мин         15 мин         20 мин         10 мин
```

### 3.2 RCA Step-by-Step

#### Step D: Define (5 min)

```yaml
Failure Record:
  gate: [Gate N]
  timestamp: [ISO 8601]
  checklist_item: [ID проваленного пункта]
  expected: [Что ожидалось]
  actual: [Что получилось]
  impact: [BLOCKING / DEGRADED / COSMETIC]
  task_scope: [Конкретный subtask или весь task]
```

#### Step M: Measure (10 min)

```yaml
Measurements:
  - metric: [Название метрики]
    expected: [Порог]
    actual: [Фактическое значение]
    delta: [Отклонение]
  - scope_affected: [% task или конкретные subtasks]
  - retries_consumed: [N из M]
  - time_spent: [HH:MM]
```

#### Step A: Analyze (15 min)

Используем **5 Whys** + Fishbone Diagram для структурирования.

**Typical Failure Categories:**

| Category | Description | Frequency |
|----------|-------------|-----------|
| Tool Failure | Инструмент не справился или вернул ошибку | 35% |
| Source Bias | Источники однобоки или имеют конфликт интересов | 20% |
| Coverage Gap | Не все аспекты темы покрыты | 25% |
| Quality Decay | Данные устарели или некачественны | 10% |
| Synthesis Error | Неверные выводы из корректных данных | 10% |

#### Step I: Improve (20 min)

| Failure Category | Root Cause | Specific Action | Prevention |
|------------------|-----------|-----------------|------------|
| **Tool Failure** | API rate limit / timeout | Switch to fallback tool; reduce batch size | Circuit breaker pattern; exponential backoff |
| **Tool Failure** | Tool returned irrelevant results | Refine query; add negative keywords | Query validation pre-flight |
| **Tool Failure** | Tool output format changed | Adapt parser; use structured output | Schema versioning |
| **Source Bias** | Single publisher dominance | Explicitly target opposing viewpoints | Source diversity checklist |
| **Source Bias** | Sponsored content | Flag commercial sources; verify independence | Tier-based filtering |
| **Source Bias** | Geographic bias | Add region-specific queries | Geographic coverage criteria |
| **Coverage Gap** | Query too narrow | Expand synonyms; broaden scope | Query expansion protocol |
| **Coverage Gap** | Hidden subdomain | Target specialized databases | Domain-specific tool selection |
| **Coverage Gap** | Temporal blind spot | Adjust date filters | Freshness criteria enforcement |
| **Quality Decay** | Stale primary data | Find updated releases | Auto-alert on source updates |
| **Quality Decay** | Deprecated methodology | Cross-check with recent reviews | Methodology versioning |
| **Synthesis Error** | Overgeneralization | Add caveats; scope narrowing | Claim-scoring enforcement |
| **Synthesis Error** | Confounding variables | Control for known confounders | Sensitivity analysis requirement |
| **Synthesis Error** | Correlation ≠ causation | Explicit language; alternative tests | Logic checklist |

#### Step C: Control (10 min)

```yaml
Control Actions:
  - action: [Превентивное действие]
    trigger: [Условие активации]
    owner: [Автоматизировано / Human]
  
  - added_to_playbook: [Yes / No]
  - similar_risk_tasks: [Список похожих задач для проверки]
  - monitoring_alert: [Метрика для отслеживания]
```

### 3.3 RCA Fast-Track

Для типовых, уже известных failure modes — пропускаем полный DMAIC:

```
IF failure_type IN known_failures AND confidence > 0.8:
    APPLY standard_fix
    LOG to playbook
    SKIP to Control
ELSE:
    RUN full_DMAIC-R
```

---

## 4. Re-search Loop Logic

### 4.1 Trigger Conditions

Re-search запускается при:

```yaml
Triggers:
  Mandatory:  # Всегда триггерят re-search
    - Gate FAIL + retry_count < max_retries
    - Coverage metric < 50% (critical gap)
    - Confidence score < 2.0 for P0 claims
    - 0 sources found for subtask
    
  Conditional:  # Триггерят при наличии capacity
    - Coverage metric 50-70% (warn zone)
    - Source diversity < 4 types
    - Freshness < threshold but > 50% threshold
    - Cross-verification < required level
    
  Never:  # Не триггерят re-search
    - Cosmetic formatting issues
    - Confidence score ≥ 3.0 for non-critical claims
    - Source availability beyond reasonable effort
```

### 4.2 Re-search Modification Protocol

При каждой итерации re-search меняем параметры по приоритету:

```
Iteration 1: Query Refinement
  - Expand keywords (synonyms, related terms)
  - Add domain-specific terminology
  - Remove overly restrictive filters
  
Iteration 2: Tool Switching
  - Switch primary search tool
  - Add specialized databases
  - Enable alternative APIs
  
Iteration 3: Scope Adjustment
  - Broaden geographic scope
  - Extend temporal window
  - Reduce granularity requirements
  
Iteration 4+: Human Escalation
  - Human-in-the-loop guidance
  - Manual source suggestions
  - Scope renegotiation
```

### 4.3 Re-search Config

```yaml
ReSearch:
  max_attempts_per_subtask: 3
  max_total_researches: 10  # на весь task
  backoff_strategy: exponential  # 1min, 2min, 4min
  
  iteration_rules:
    attempt_1: [query_refinement]
    attempt_2: [tool_switching, query_refinement]
    attempt_3: [scope_adjustment, tool_switching, query_refinement]
    
  escalation:
    after_max_attempts: human_in_the_loop
    timeout: 30_minutes_per_subtask
```

### 4.4 Escalation Decision Tree

```
Re-search failed?
│
├─ Yes → Retries exhausted?
│        │
│        ├─ No → Next iteration with modified params
│        │
│        └─ Yes → Is it critical path?
│                 │
│                 ├─ Yes → Human escalation (blocking)
│                 │         ├─ Human provides guidance → Resume
│                 │         └─ Human reduces scope → Adjust AC
│                 │
│                 └─ No → Degrade gracefully
│                          ├─ Document gap
│                          ├─ Lower confidence score
│                          └─ Continue with disclaimer
│
└─ No → Proceed to next gate
```

### 4.5 Human Escalation Levels

| Level | Trigger | Human Action | Response Time |
|-------|---------|--------------|---------------|
| L1: Advisory | 2nd retry failed | Guidance on scope/tools | Async (task continues) |
| L2: Blocking | 3rd retry + critical path | Direct intervention required | Sync (task pauses) |
| L3: Override | Quality gate 5 failed | Approve/reject with comments | Sync (final authority) |

---

## 5. Confidence Scoring System

### 5.1 Confidence Scale

Используем **5-point scale** с чёткими критериями:

| Score | Label | Criteria | Visual |
|-------|-------|----------|--------|
| 5 | **Certain** | Подтверждено первичными источниками, статистически значимо, широкий консенсус | █████ |
| 4 | **High** | Несколько независимых авторитетных подтверждений, незначительные caveats | ████░ |
| 3 | **Moderate** | Есть поддерживающие данные, но с ограничениями по scope или methodology | ███░░ |
| 2 | **Low** | Ограниченные данные, возможны альтернативные интерпретации | ██░░░ |
| 1 | **Speculative** | Предположение, экспертное мнение без данных, ранняя гипотеза | █░░░░ |

### 5.2 Per-Claim Scoring

Каждое утверждение в отчёте получает confidence score:

```yaml
Claim:
  id: C-001
  text: "AI market will reach $407B by 2027"
  confidence: 4
  
  evidence:
    - source: Gartner Report 2024
      tier: S
      supports: direct_projection
    - source: Bloomberg Intelligence
      tier: A
      supports: similar_estimate
      
  caveats:
    - "Assumes current growth rate continues"
    - "Sensitive to regulatory changes"
    
  alternatives:
    - "More conservative estimate: $300B (Mckinsey)"
```

**Confidence Calculation Algorithm:**

```
base_score = f(source_tier, verification_level, evidence_strength)
  
modifiers:
  - conflicting_evidence: -1
  - single_source: -1 (if not Tier S)
  - stale_data: -1
  - strong_consensus: +1 (if ≥ 5 sources agree)
  - primary_source_direct: +1
  
floor: 1
ceiling: 5
```

### 5.3 Aggregate Confidence

```
Report Confidence = weighted_average(claim_confidences, weights_by_importance)

Buckets:
  - P0 claims: weight 3×
  - P1 claims: weight 1×
  - P2 claims: weight 0.5×

Report Grade:
  A: ≥ 4.0
  B: 3.0 – 3.9
  C: 2.0 – 2.9
  D: 1.0 – 1.9
  F: < 1.0
```

### 5.4 Confidence Visualization in Output

```markdown
### Market Size Projection

**Claim:** AI market will reach $407B by 2027  
**Confidence:** ████░ High (4/5)

| Evidence | Source | Tier |
|----------|--------|------|
| Direct market forecast | Gartner, 2024 | S |
| Corroborating analysis | Bloomberg Intelligence, 2024 | A |

**Caveats:** Assumes sustained growth; regulatory risks not fully quantified  
**Alternative:** McKinsey estimates $300B (Confidence: ███░░ Moderate)
```

### 5.5 Confidence Override Rules

```yaml
Override Conditions:
  - If all evidence sources are Tier S: min_score = 3
  - If single source and Tier C or below: max_score = 2
  - If circular reporting detected: reduce by 1
  - If claim contradicts established consensus: require V3 verification
```

---

## 6. Source Quality Rating

### 6.1 Tier System

| Tier | Category | Examples | Min Threshold for Inclusion |
|------|----------|----------|----------------------------|
| **S** | Primary Sources | SEC filings, company reports, official statistics, court documents, raw datasets | Desirable; не менее 20% для P0 claims |
| **A** | Authoritative Media | Reuters, FT, Bloomberg, WSJ, The Economist, peer-reviewed journals | Обязательно; не менее 40% всех источников |
| **B** | Specialized Publications | TechCrunch, ArsTechnica, Nature News, IEEE Spectrum, industry analysts (Gartner, IDC) | Допустимо; может составлять до 40% |
| **C** | Commentary & Opinion | Blogs, LinkedIn articles, podcasts, newsletters, expert opinions | Ограниченно; не более 15%, обязательна маркировка |
| **D** | Unverified / Unknown | Forums, social media, unattributed content, AI-generated without human review | Не допускаются без явного disclaimer и cross-verification |

### 6.2 Tier Evaluation Criteria

```yaml
Source Evaluation:
  publisher_reputation:
    - history: > 5 years in domain
    - editorial_policy: publicly stated
    - corrections_policy: acknowledges and corrects errors
    
  author_credentials:
    - domain_expertise: demonstrated
    - conflict_of_interest: disclosed
    - track_record: previously accurate
    
  content_quality:
    - citations: includes sources
    - methodology: transparent
    - data_freshness: dated and current
    
  independence:
    - funding_source: independent or disclosed
    - commercial_pressure: minimal
    - political_bias: disclosed or negligible
```

### 6.3 Tier Scoring Rubric

| Criterion | Weight | S (10) | A (8) | B (6) | C (4) | D (2) |
|-----------|--------|--------|-------|-------|-------|-------|
| Authority / Primary | 30% | Original data | Top-tier media | Specialized pub | Opinion | Unknown |
| Editorial Standards | 25% | Rigorous audit | Professional edit | Editorial review | Self-published | None |
| Citation Practice | 20% | Full traceability | Cited sources | Some citations | Rarely cites | Never cites |
| Independence | 15% | Fully independent | Transparent funding | Some disclosure | Undisclosed | Hidden COI |
| Track Record | 10% | Verified history | Established | Growing | New/unknown | Poor record |

**Min Score for Inclusion: 4.0** (Tier C threshold)

### 6.4 Source Diversity Requirements

```yaml
Diversity Check:
  min_source_types: 4
  acceptable_types:
    - academic_journal
    - news_media
    - industry_report
    - government_data
    - expert_interview
    - company_filing
    - think_tank
    - book_monograph
    
  max_single_type_ratio: 40%  # Не более 40% источников одного типа
  max_single_publisher_ratio: 25%  # Не более 25% от одного издателя
```

### 6.5 Source Conflict Detection

```yaml
Conflict Rules:
  - IF source A contradicts source B:
      - both Tier S or A: flag for human review (HIGH priority)
      - one Tier S, other lower: note discrepancy, weight Tier S
      - both Tier B or lower: seek additional verification
      
  - IF source cites another source:
      - trace to primary: boost confidence
      - circular (A→B→A): reduce both by 1 tier
      - unattributed: flag as Tier D until verified
```

---

## 7. Completeness Metrics

### 7.1 Metric Definitions

#### M1: Source Coverage

```
Source Coverage (SC) = (Unique Sources Found / Expected Source Pool) × 100%

Expected Source Pool (ESP):
  ├─ Top 10 Google results (relevant only)
  ├─ Known authoritative sources for domain
  ├─ Referenced in similar high-quality research
  └─ Domain-specific databases

Grading:
  A: SC ≥ 80%
  B: 60% ≤ SC < 80%
  C: 40% ≤ SC < 60%
  D: 20% ≤ SC < 40%
  F: SC < 20%
```

#### M2: Topic Coverage

```
Topic Coverage (TC) = (Subtopics Covered / Total Subtopics in Scope) × 100%

Subtopic Identification:
  1. Extract from user query
  2. Expand via known taxonomies
  3. Cross-reference with similar research TOC

Depth per Subtopic:
  Level 1: Mentioned (1-2 sentences)
  Level 2: Described (paragraph with context)
  Level 3: Analyzed (data + interpretation)
  Level 4: Synthesized (connected to other subtopics)

Grading:
  A: TC ≥ 90% AND avg depth ≥ 3
  B: TC ≥ 75% AND avg depth ≥ 2.5
  C: TC ≥ 60% AND avg depth ≥ 2
  D: TC ≥ 40% OR avg depth ≥ 1.5
  F: TC < 40% AND avg depth < 1.5
```

#### M3: Recency

```
Recency (R) = (% Data Points within Freshness Window) × 100%

Weighted Recency (WR) = Σ(weight_i × recency_i) / Σ(weight_i)
  where weight_i = importance of data point i

Grading:
  A: WR ≥ 75%
  B: 60% ≤ WR < 75%
  C: 45% ≤ WR < 60%
  D: 30% ≤ WR < 45%
  F: WR < 30%
```

#### M4: Fact Density

```
Fact Density (FD) = Number of Cited Facts / Output Length (in pages)

Cited Fact Definition:
  - Statement attributed to ≥ 1 source
  - Contains specific data (number, date, name)
  - Verifiable

Grading:
  A: FD ≥ 15 facts/page
  B: 10 ≤ FD < 15
  C: 6 ≤ FD < 10
  D: 3 ≤ FD < 6
  F: FD < 3
```

### 7.2 Composite Completeness Score

```
Completeness Index (CI) = weighted_average(SC, TC, WR, FD)
  SC: 25%
  TC: 35%
  WR: 20%
  FD: 20%

Overall Grading:
  A: CI ≥ 85  → Proceed to output
  B: 70 ≤ CI < 85  → Minor gaps, document and proceed
  C: 55 ≤ CI < 70  → Moderate gaps, targeted re-search
  D: 40 ≤ CI < 55  → Significant gaps, full re-search
  F: CI < 40  → Critical gaps, escalate to human
```

### 7.3 Completeness Dashboard

```markdown
## Research Quality Dashboard

| Metric | Score | Grade | Threshold | Status |
|--------|-------|-------|-----------|--------|
| Source Coverage | 72% | B | 60% | ✅ Pass |
| Topic Coverage | 85% | B | 75% | ✅ Pass |
| Recency | 68% | C | 60% | ⚠️ Warn |
| Fact Density | 12/page | B | 10 | ✅ Pass |
| **Completeness Index** | **74** | **B** | **70** | ✅ **Pass** |

### Gaps Identified
- Recency below target: 12% sources older than 24 months
- Action: Target 2024 sources for regulatory section
```

---

## 8. Integration Flow

### 8.1 Heartbeat & Checkpoint Integration

```
Timeline:
  T+0min    → Start Checkpoint: AC defined, scope confirmed
  T+2-3min  → Heartbeat: progress %, current gate, issues
  T+gate1   → Checkpoint: raw data inventory
  T+gate2   → Checkpoint: processed dataset
  T+25%     → Heartbeat: 25% milestone, metrics snapshot
  T+gate3   → Checkpoint: analysis findings
  T+50%     → Heartbeat: 50% milestone, confidence check
  T+gate4   → Checkpoint: synthesis draft
  T+75%     → Heartbeat: 75% milestone, completeness check
  T+gate5   → Checkpoint: final output + quality certificate
  T+100%    → Final Checkpoint: delivery + audit trail
```

### 8.2 Recovery Protocol

```
ON crash / interruption:
  1. Read latest Heartbeat file
  2. Identify last completed Checkpoint
  3. Restore state from Checkpoint
  4. Resume from next Gate
  5. Log recovery action

Heartbeat File Format:
  timestamp: [ISO 8601]
  task_id: [uuid]
  current_gate: [1-5 or null]
  progress_pct: [0-100]
  last_checkpoint: [artifact_id]
  issues: [list]
  next_action: [description]
```

### 8.3 Full Execution Pipeline

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Define  │──▶│  Collect │──▶│ Process  │──▶│ Analyze  │──▶│ Synthesize│──▶│ Deliver  │
│    AC    │   │   Data   │   │   Data   │   │  Data    │   │  Output   │   │  Report  │
└──────────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────────┘
                    │              │              │              │
                    ▼              ▼              ▼              ▼
               ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
               │ Gate 1 │    │ Gate 2 │    │ Gate 3 │    │ Gate 4 │
               │Post-   │    │Post-   │    │Post-   │    │Post-   │
               │Collect │    │Process │    │Analyze │    │Synthesize
               └───┬────┘    └───┬────┘    └───┬────┘    └───┬────┘
                   │             │             │             │
              PASS/FAIL      PASS/FAIL      PASS/FAIL      PASS/FAIL
                   │             │             │             │
              ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
              │If FAIL: │   │If FAIL: │   │If FAIL: │   │If FAIL: │
              │RCA +    │   │RCA +    │   │RCA +    │   │RCA +    │
              │Re-search│   │Re-process│  │Re-analyze│  │Re-synth │
              └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

---

## 9. Appendices

### Appendix A: Quick Reference Card

```
┌────────────────────────────────────────────────────────────┐
│           DEEP RESEARCH — ACCEPTANCE QUICK CARD            │
├────────────────────────────────────────────────────────────┤
│ AC TYPES:  R=Research  A=Analysis  C=Comparison  S=Synth  │
│ QUALITY GATES:  5 gates, binary pass/fail                  │
│ RCA:  DMAIC-R, 60 min max, fast-track for known issues    │
│ RE-SEARCH:  max 3 attempts, escalate on exhaustion         │
│ CONFIDENCE:  1-5 scale, per-claim, aggregate weighted      │
│ SOURCE TIERS:  S > A > B > C > D, min C for inclusion     │
│ COMPLETENESS:  4 metrics, composite CI score               │
│ ESCALATION:  L1 Advisory → L2 Blocking → L3 Override       │
└────────────────────────────────────────────────────────────┘
```

### Appendix B: Gate Checklist Summary

**Gate 1 (Post-Collection):** sources ≥ N, diversity ≥ 4 types, tier ≥ 60% B+, freshness ≥ 60%, 0 blocking errors

**Gate 2 (Post-Processing):** dedup < 5%, structured, 0 PII leaks, quality ≥ 8/10, losses < 10%

**Gate 3 (Post-Analysis):** 100% P0 questions answered, findings ≥ 3 data points each, stats checked

**Gate 4 (Post-Synthesis):** 100% claims sourced, all scored, alternatives considered, 0 contradictions

**Gate 5 (Final Output):** CI ≥ 70, all citations present, confidence visualized, format compliant

### Appendix C: Confidence Score Decision Tree

```
Is claim supported by Tier S primary source?
├─ Yes → Base 4
│        Multiple Tier S? → 5
│        Any caveats? → 4
├─ No → Tier A sources?
│       ├─ Multiple (≥3) → 4
│       ├─ Two → 3
│       └─ One → 2
└─ Tier B or below only?
         ├─ Multiple + cross-verified → 3
         ├─ Two → 2
         └─ One / none → 1

Apply modifiers:
  +1: strong consensus (≥5 sources)
  -1: conflicting evidence
  -1: single source below Tier A
  -1: data older than 2× freshness window
  
Floor: 1, Ceiling: 5
```

### Appendix D: File & Artifact Naming Convention

```
[project_id]_[task_type]_[timestamp]_[artifact_type]_[version]

Examples:
  drs_2024q3_ai-market_20241115_121500_ac_v1.md
  drs_2024q3_ai-market_20241115_123000_gate1_checkpoint.json
  drs_2024q3_ai-market_20241115_124500_heartbeat.json
  drs_2024q3_ai-market_20241115_130000_gate3_checkpoint.json
  drs_2024q3_ai-market_20241115_133000_final_output.md
  drs_2024q3_ai-market_20241115_133000_quality_certificate.json
```

---

*End of Acceptance Framework v1.0*
