---
name: deep-research-skill
version: 0.2.0
author: Andrey Zagreev (https://t.me/zagreev)
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

# Deep Research Skill

> **Версия:** 0.2.0 | **Последнее обновление:** 2026-06-08
> **Полная документация:** `SKILL.master.md` (lazy loading)
> **Heartbeat/Checkpoint протокол:** `AGENT.MD`

---

## Core Philosophy

### 1. Cost-First Execution
Начни дешево, эскалируй дорого. Каждый subtask проходит через иерархию инструментов от бесплатных к премиум. Tier 1 (native tools) покрывает ~70% задач. Tier 4 (Firecrawl, Browserbase) — только когда всё остальное не работает.

### 2. Evidence-Based Only
Каждое утверждение в отчёте обязано иметь citation. Нет bare URLs в тексте — только нумерованные ссылки в реестре источников. Нет утверждений "из головы" — только то, что подтверждено источниками.

### 3. Anti-Hallucination Mandate
Zero tolerance к галлюцинациям. FactCheck Agent ветирует каждый факт перед включением в финальный отчёт. Если источник не найден — утверждение помечается "❓ Не удалось проверить" и явно дисклеймится.

### 4. Progressive Disclosure
Ответ строится по принципу: summary → findings → details. Пользователь получает сначала суть, затем — детали по запросу. Никаких стен текста без предварительного executive snapshot. Depth 1–2: только snapshot + findings. Depth 3: + methodology + analysis. Depth 4+: + implications + limitations + appendices.

### 5. Source Authority Awareness
Каждый источник оценивается по Tier S/A/B/C/D. Tier S (SEC filings, регуляторы, первичные данные) = ground truth. Tier D (форумы, соцсети) — не используется для фактов без верификации. Минимальный порог включения зависит от домена (см. Source Authority Framework).

### 6. Independent Verification
Кросс-модельная и кросс-источниковая проверка. Каждый ключевой факт — минимум 2 независимых источника. Для high-stakes утверждений: ≥3 источника, ≥1 Tier S или Tier A. Обнаружение circular reporting (A→B→A) — автоматический downrank. Правило разрешения конфликтов: Tier S > Tier A > freshness > independence > quantity.

### 7. Transparent Confidence
Каждый claim scored по шкале 1-5: 1=Speculative, 2=Low, 3=Moderate, 4=High, 5=Certain. Визуализация: 🔵🟢🟡🔴⚪. Aggregate confidence — в заголовке каждого отчёта. Нет скрытой неопределённости.

### 8. Checkpoint Recovery
Heartbeat по адаптивному интервалу (см. AGENT.MD §1.2 — для типичной задачи каждые 2–10 мин; watchdog = 2× интервала) + checkpoint после каждого phase gate. При прерывании — восстановление из последнего checkpoint: каждый `cp_NN_<stage>.md` начинается с машиночитаемого ```json `state`-блока (task_frame, sources с extract'ами, claims, budget, next_phase — см. AGENT.MD §8.0); resume читает его, восстанавливает собранные данные без повторного сбора и продолжает с next_phase. Откат гарантируется к последнему пройденному gate, а не к нулю — потеря ограничена работой текущей незавершённой фазы.

---

## Instructions: 6-Phase Workflow

### Phase 0: Task Analysis & Route Selection
**→ Загрузи: `references/strategy_guide.md`**

0. **Resume check (ДО классификации).** Проверь `./research_output/checkpoints/` на `cp_*.md` с валидным ```json `state`-блоком (см. AGENT.MD §8.0):
   - Нет файлов / `task_fingerprint` не совпал с текущим запросом → свежий прогон (новая run-папка, чужой `state` не затирай).
   - Совпал → объяви «↩ Resuming <run_id> from cp_NN (phase N)», восстанови `task_frame`/`sources` (с extract'ами)/`claims`/`budget` из `state`, **НЕ пере-собирай** уже отрендеренные источники (пере-сбор собранного = нарушение протокола, не оптимизация; служи `extract` из `state`), продолжи с `next_phase`. Бюджет (`spent_usd`, `loads_used`) переноси, не обнуляй.

1. **Классифицируй запрос** через 3-layer router:
   - Layer 1: Keyword matching (O(1)) — по хеш-таблице триггеров
   - Layer 2: Pattern classifier — регулярные выражения
   - Layer 3: LLM classifier — только для edge cases (confidence < 0.7)

2. **Выбери Route:**
   - **Route A (Wide Search):** Обзорные, exploratory темы — landscape, trends, key players
   - **Route B (Focused Search):** Конкретные вопросы — product deep-dive, pricing, troubleshooting
   - **Route C (File-Only):** Анализ только загруженных файлов
   - **Route D (File-Augmented):** Файлы + веб для валидации/бенчмаркинга

3. **Определи Depth Level:**
   - Quick (30 мин, 5-8 subtasks) → sanity check
   - Standard (1-2 ч, 10-15 subtasks) → structured analysis
   - Deep (3-5 ч, 20-30 subtasks) → expert research
   - Exhaustive (5+ ч, 30-50 subtasks) → publication-ready

4. **Сформулируй Acceptance Criteria** по SMART-R шаблону (см. `references/acceptance_framework.md`).

**Lazy loading:** Загружай `references/strategy_guide.md` только при необходимости уточнить sub-route (A1–A4, B1–B4) или правила parallel execution.

**Checkpoint:** AC определены, Route выбран, бюджет оценён.

---

### Phase 1: Decomposition
**→ Загрузи: `references/decomposition_guide.md`**

1. **Разбей задачу на atomic subtasks** по критериям:
   - Single Intent (один глагол)
   - Single Domain (один источник/инструмент)
   - Deterministic Output (проверяемый результат)
   - No Internal Branches
   - Bounded Scope (≤15 мин, ≤8000 tokens output)

2. **Определи тип каждого subtask:** SEARCH | EXTRACT | ANALYZE | COMPARE | SYNTHESIZE | VALIDATE | FORMAT | META

3. **Построй dependency graph:**
   - STRICT (A → B): B нельзя начать без A
   - SOFT (A - -> B): B может начать с partial output от A
   - NONE (A  B): параллельное выполнение
   - FEEDBACK (A ◄──► B): итеративное уточнение, max 3 итерации

4. **Спланируй параллельные группы:** max 5 concurrent subtasks.

**Granularity heuristic:** Simple задача → 3–7 subtasks, 1–2 уровня. Medium → 8–20 subtasks, 2–3 уровня. Complex → 20–50 subtasks, 3–5 уровней с feedback loops. Wicked → 50+ subtasks, 5+ уровней.

**Lazy loading:** Загружай `references/decomposition_guide.md` для сложных dependency graphs, типовых паттернов (Competitive Landscape, Technology Deep Dive, Market Sizing) и DRGN-нотации.

**Checkpoint:** DAG subtasks построен, зависимости разрешены, checkpoints назначены.

---

### Phase 2: Collection
**→ Загрузи: `references/tool_matrix.md`, `references/cost_matrix_full.md`**

1. **Выполняй сбор данных по tool hierarchy:**

```
Layer 1 (Free):     web_search, browser_visit, ipython, shell, file_*, data_sources
Layer 2 (Low):      Jina Reader (r.jina.ai), Jina Search (s.jina.ai), curl_cffi
Layer 3 (Mid):      generate_image/video, CloakBrowser
Layer 4 (Premium):  Firecrawl API, Jina DeepSearch, Browserbase
```

2. **Следуй fallback chain для каждого subtask:**
   - Статическая страница: browser_visit → Jina Reader → Firecrawl
   - JS-heavy SPA: browser_visit → click/scroll → Firecrawl (waitFor)
   - Anti-bot защита: browser_visit (detect) → Firecrawl (stealth)
   - Discovery → Deep Dive: web_search (batch) → parallel Jina Reader → ipython analysis

3. **Применяй cost estimation:**
   - Оцени стоимость ДО выполнения
   - Следи за budget guardrails (см. `references/cost_matrix_full.md`)
   - При приближении к лимиту — graceful degradation

4. **Используй structured data sources первыми** (бесплатно, быстро):
   - Финансы: yahoo_finance, stock_finance_data
   - Наука: arxiv, scholar
   - Экономика: world_bank_open_data, imf
   - Крипто: binance_crypto
   - Право (КНР): yuandian_law

5. **Large-output discipline (контроль токенов).** Не читай крупные выдачи инструментов целиком в контекст:
   - Если результат (web-scrape, лог, API-ответ) превышает ~5 КБ / ~1500 токенов — **сохрани в файл** `./research_output/<run>/raw/<source_id>.txt`, затем извлекай ТОЛЬКО нужный срез через grep/поиск по intent (цены, имена, факты по AC), а не Read целиком.
   - В source inventory / `state` клади **путь к raw-файлу + извлечённый срез** (`raw_path`, `extract`), а не весь сырой текст (см. AGENT.MD §8.0).
   - Режет расход на доминирующей статье (сбор) ~70–90% без внешних зависимостей.
   - *(Опц.)* Если подключён MCP `context-mode` — используй `ctx_fetch_and_index` / `ctx_search` вместо ручного save+grep (то же поведение, автоматически).

**Checkpoint:** Сырые данные собраны, source inventory создан, метаданные захвачены.

---

### Phase 3: Verification
**→ Загрузи: `references/factcheck_system.md`**

Запусти **FactCheck Agent (FCA)** — независимый валидатор:

1. **Извлечение:** Разложи findings на атомарные проверяемые утверждения
2. **Классификация:** Определи тип — факт, число, вывод, предсказание, цитата, сравнение
3. **Поиск:** Найди подтверждающие/опровергающие источники (Priority 1-5)
4. **Оценка:** Рассчитай SOURCE_QUALITY_SCORE для каждого источника
5. **Категоризация** по 6 категориям:
   - ✅ **ВЕРНО** — подтверждается источниками
   - ❌ **НЕВЕРНО** — противоречит источникам (исключается)
   - ⏰ **УСТАРЕЛО** — было верно, ситуация изменилась
   - ⚠️ **НЕПОЛНО** — факт верный, контекст искажает вывод
   - 🔮 **ОДНА ИЗ ТОЧЕК ЗРЕНИЯ** — есть альтернативные позиции
   - ❓ **НЕ УДАЛОСЬ ПРОВЕРИТЬ** — требует ручной проверки

6. **Документирование:** Зафиксируй citations, quotes, confidence scores
7. **Отчёт:** Сформируй сводку с метриками coverage, accuracy, source diversity

**Anti-Hallucination Mandate:** Если FCA не подтвердил — в отчёт не попадает. Нет исключений.

**Checkpoint:** Факты проверены, категории присвоены, отчёт FCA готов.

---

### Phase 4: Synthesis

1. **Объедини проверенные findings** из FCA:
   - Отбрось ❌ (неверные)
   - Обнови ⏰ (устаревшие) данными из re-search
   - Дополни ⚠️ (неполные) контекстом
   - Переформулируй 🔮 (точки зрения) с оговорками
   - Дисклейми ❓ (непроверенные)

2. **Проведи анализ:**
   - Synthesis: cross-source инсайты
   - Pattern Recognition: тренды, аномалии
   - Contradictions: разногласия между источниками
   - Critical Evaluation: сильные/слабые стороны evidence

3. **Присвой confidence scores** каждому claim:
```
Base score = f(source_tier, verification_level, evidence_strength)
Modifiers: +1 strong consensus (≥5 sources) | -1 conflicting evidence
           -1 single source below Tier A    | -1 stale data
Floor: 1, Ceiling: 5
```

4. **Сформируй выводы и рекомендации** — actionable, prioritized, с rationale.

**Synthesis quality checklist:**
- [ ] Все P0-findings синтезированы в выводы (100% coverage)
- [ ] Claim-evidence links проверены (100% claims → sources)
- [ ] Confidence scores присвоены (100% claims scored)
- [ ] Альтернативные интерпретации рассмотрены (≥2 на ключевой вывод)
- [ ] 0 критических logical contradictions
- [ ] ≥70% conclusions → actionable recommendations

**Checkpoint:** Синтез завершён, confidence scores присвоены, рекомендации сформулированы.

---

### Phase 5: Output Formatting
**→ Загрузи: `references/output_formats.md`**

Выбери формат по типу запроса:

| Запрос | Формат | Триггер |
|--------|--------|---------|
| Factual lookup | **Fact Sheet** | "факты о", "статистика" |
| Comparative | **Comparison Matrix** | "vs", "сравни", "лучший" |
| Chronological | **Timeline** | "история", "таймлайн", "эволюция" |
| Decision support | **Executive Brief** | "рекомендации", "что делать" |
| Deep exploration | **Research Report** | "анализ", "исследование", "почему" |
| Source discovery | **Annotated Bibliography** | "литература", "источники" |

**Citation system:**
- Inline: `[^N^]` — superscript numeric brackets
- Реестр в конце: `[^N^]: Author. "Title." Publication, Date. URL`
- Названия для типов: `[Type: direct_quote|paraphrase|data|inference|background|cross_ref]`

**Confidence visualization:**
- Per-claim: emoji после citation — 🔵Confirmed 🟢High 🟡Medium 🔴Low ⚪Unverifiable
- Aggregate: в заголовке отчёта — `🟢 72% (High)`

**Citation types** (опциональные теги в реестре):
- `[Type: direct_quote]` — дословная цитата
- `[Type: paraphrase]` — пересказ идей
- `[Type: data]` — статистика, числа
- `[Type: inference]` — логическое следствие (не авторский claim)
- `[Type: cross_ref]` — подтверждение другого источника

**Broken link handling:**
1. Попробуй archive.org
2. Если есть snapshot → добавь `[Archived](url)`
3. Если нет — поищи альтернативный URL
4. Флаг с ⚠️, никогда не удаляй cited source

**Metadata block** (в начале каждого документа):
```
> **Format:** {type} | **ID:** {prefix-YYYYMMDD-hash}
> **Depth:** {1-5} | **Sources:** {N consulted} / {N cited}
> **Confidence Aggregate:** {emoji} {pct}% ({level})
> **Routes:** {web_search | arxiv | ...} | **Cost:** {N calls} | {tokens}
```

**Checkpoint:** Отчёт отформатирован, citations разрешены, confidence отображён.

---

### Phase 6: Acceptance Validation
**→ Загрузи: `references/acceptance_framework.md`**

Проверь отчёт по 5 Quality Gates:

**Gate 1: Post-Collection** — sources ≥ N, diversity ≥ 4 типа, ≥60% Tier B+, freshness ≥60%

**Gate 2: Post-Processing** — dedup < 5%, structured, 0 PII leaks, quality ≥ 8/10

**Gate 3: Post-Analysis** — 100% P0 questions answered, findings ≥ 3 data points each

**Gate 4: Post-Synthesis** — 100% claims sourced & scored, alternatives considered, 0 contradictions

**Gate 5: Final Output** — CI ≥ 70, all citations present, format compliant, summary ≤ 1 page

**Re-search Loop:**
- Gate FAIL + retries < max → re-search с модифицированными параметрами
- Iteration 1: query refinement | Iteration 2: tool switching | Iteration 3: scope adjustment
- Retries exhausted + critical path → human escalation (L1 Advisory → L2 Blocking → L3 Override)

**Checkpoint:** Все gates пройдены, Quality Certificate выдан, audit trail сохранён.

---

## Tool Router

> **Полная матрица:** `references/tool_matrix.md` | **Cost-матрица:** `references/cost_matrix_full.md`

### Иерархия (4 Tier)

| Tier | Инструменты | Cost | Когда |
|------|-------------|------|-------|
| **1 — Native** | web_search, browser_*, ipython, shell, file_*, data_sources | $0 | Всегда первыми |
| **2 — Efficient** | Jina Reader/Search, curl_cffi, CloakBrowser | $0–$50/мес | Fallback от Tier 1 |
| **3 — Mid** | generate_*, Firecrawl (batch) | $50–$500/мес | Масштаб, AI-gen |
| **4 — Premium** | Firecrawl (single), Jina DeepSearch, Browserbase | $500+/мес | Anti-bot, deep research |

### Fallback Chains

```
Статическая страница:     browser_visit → Jina Reader → Firecrawl
SPA/JS-heavy:             browser_visit → click/scroll → Firecrawl (waitFor)
Anti-bot (Cloudflare):    browser_visit (detect) → Firecrawl → Browserbase
Поиск + извлечение:       web_search → Jina Reader → ipython analysis
Глубокое исследование:    Jina DeepSearch → GPT Researcher → manual chain
CAPTCHA:                  CloakBrowser (prevent) → CapSolver → 2Captcha → manual
```

### Structured Data Sources (Free, Tier 1)

| Домен | Source | Latency | Best For |
|-------|--------|---------|----------|
| Финансы | yahoo_finance | 🚀 1–3s | Stocks, markets, financials |
| Финансы | stock_finance_data | 🚀 1–5s | China A-shares, HK, US financials |
| Крипто | binance_crypto | ⚡ <1s | Real-time crypto prices, trading data |
| Наука | arxiv | 🚀 2–5s | Physics, CS, math preprints |
| Наука | scholar | 🚀 2–5s | Citation analysis, author profiles |
| Экономика | world_bank_open_data | 🚀 2–8s | GDP, population, poverty, 190+ countries |
| Экономика | imf | 🚀 2–8s | Macroeconomic forecasts, WEO |
| Право (КНР) | yuandian_law | 🚀 2–5s | PRC statutes, regulations, cases |

### Cost Formula
```
Total = Base_LLM + (Scrape_Qty × Cost_Per_Page) + (CAPTCHA_Qty × Solve_Cost)
        + Browser_Hours × Rate + DeepSearch_Tokens + Verification_Overhead(10%)
```

---

## Source Authority

> **Полный фреймворк:** `references/source_authority_framework.md`

### Tier Hierarchy

| Tier | Категория | Доверие | Примеры |
|------|-----------|---------|---------|
| **S** | Primary Authority | 95–100% | SEC filings, регуляторы, МВФ, Всемирный банк, переписи |
| **A** | Expert Authority | 80–95% | Big4/McKinsey/BCG, Gartner, Nature, Reuters, центральные банки |
| **B** | Professional Authority | 60–80% | WSJ, FT, The Economist, engineering blogs, отраслевые аналитики |
| **C** | Secondary Authority | 35–60% | Блоги экспертов, LinkedIn, пресс-релизы, Wikipedia (как старт) |
| **D** | Tertiary / Unverified | 0–35% | Форумы, соцсети, анонимные источники — не для фактов |

### Domain-Specific Min Threshold

| Домен | Min Score | Обязательные Tiers |
|-------|-----------|-------------------|
| Финансы | 0.70 | S, A, B |
| Технологии | 0.65 | S, A, B |
| Экономика | 0.75 | S, A |
| Право | 0.85 | S, A |
| Наука | 0.80 | S, A |
| Healthcare | 0.85 | S, A |
| Общий | 0.70 | S, A, B |

### Composite Score Formula
```
Score = (Authority × 0.30) + (Recency × 0.25) + (Independence × 0.20)
        + (Traceability × 0.15) + (Corroboration × 0.10)
Range: 0.00 – 1.00 | S: ≥0.90 | A: 0.75–0.89 | B: 0.55–0.74 | C: 0.35–0.54 | D: <0.35
```

### Red Flags (Auto-Exclude или Downrank)

| # | Red Flag | Действие |
|---|----------|----------|
| 1 | Отсутствие автора или институции | Исключить |
| 2 | Нет даты публикации | Исключить |
| 3 | Нет ссылок на первичные данные | Downrank до Tier D |
| 4 | Known disinformation source | Исключить + blacklist |
| 5 | Predatory journal | Исключить |
| 6 | Circular referencing (A→B→A) | Downrank на 1 tier |
| 7 | Astroturfing indicators | Downrank до Tier D |
| 8 | Спонсорство без раскрытия | Downrank на 1 tier |
| 9 | Cherry-picking данных | Downrank, искать полную картину |
| 10 | Extreme deviation от консенсуса | Проверить методологию |

---

## FactCheck Agent

> **Полная документация:** `references/factcheck_system.md`

### 6 Стратегий Проверки

| # | Стратегия | Применение | Модификатор confidence |
|---|-----------|------------|----------------------|
| 1 | **Primary Verification** | Проверка по первоисточнику (SEC, регулятор) | +0.30 |
| 2 | **Cross-Reference** | ≥2 независимых источника | +0.25 (совпад), −0.20 (противореч) |
| 3 | **Recency Check** | Актуальность данных по доменным окнам | −0.15 (stale), −0.30 (deprecated) |
| 4 | **Context Completeness** | Полнота контекста, отсутствие cherry-picking | −0.10 (cherry-pick), −0.20 (critical gap) |
| 5 | **Bias Detection** | Систематические искажения (confirmation, source, framing) | downrank при score >0.5 |
| 6 | **Quantitative Validation** | Проверка чисел: порядок, пропорции, единицы | +0.15 (success), −0.40 (arith error) |

### Workflow FCA (7 шагов)

```
STAGE 0: ROUTING (cost-aware, по stakes)
STAGE 1: EXTRACTION → atomic claims
STAGE 2: CLASSIFICATION → тип утверждения
STAGE 3: SEARCH → подтверждающие/опровергающие источники
STAGE 4: EVALUATE → SOURCE_QUALITY_SCORE
STAGE 5: CATEGORIZE → 6-категориальная система
STAGE 6: DOCUMENT → citations, quotes
STAGE 7: REPORT → финальный отчёт с метриками
```

### Recovery
- Источник >30 сек — failover на альтернативный
- <50% утверждений проверено — эскалация на ручную проверку
- >20% ❌ Неверно — блокировка, запрос пересмотра у Research Agent

### FCA Quality Metrics

| Метрика | Целевое значение | Действие при провале |
|---------|-----------------|----------------------|
| Verification Coverage | ≥90% | Ручная проверка оставшихся |
| Accuracy Rate (Research Agent) | ≥85% | Пересмотр промпта/модели |
| Source Diversity Index | ≥4 типа | Дополнительный поиск |
| Confidence Calibration Error | <0.05 | Перекалибровка scoring |
| Avg Verification Time | <60 сек/утверждение | Оптимизация pipeline |
| False Positive Rate | <3% | Аудит верификации |
| Escalation Rate | <10% | Улучшение source routing |

---

## Quality Gates

> **Детали:** `references/acceptance_framework.md`

### Gate 1: Post-Collection
- Sources ≥ N (по scope), diversity ≥ 4 типа
- ≥60% источников Tier B+, freshness ≥ 60%
- 0 blocking errors, checkpoint artifact создан

### Gate 2: Post-Processing
- Dedup < 5%, 100% данных в схеме, 0 утечек PII
- Quality score ≥ 8/10, потери < 10%

### Gate 3: Post-Analysis
- 100% P0 questions answered, каждый finding → ≥3 data points
- Stats checked, assumptions documented

### Gate 4: Post-Synthesis
- 100% claims → sources & scores, alternatives considered
- 0 critical contradictions, ≥70% conclusions → action

### Gate 5: Final Output
- Completeness Index ≥ 70, all citations present
- Confidence visualized, format compliant, exec summary ≤ 1 page

### Escalation

```
Gate FAIL → RCA (DMAIC-R: Define→Measure→Analyze→Improve→Control)
          → Retry (max 3 для Gate 1, max 2 для Gate 2/4/5)
          → Exhausted + critical → Human escalation (L1/L2/L3)
```

| Level | Trigger | Действие human |
|-------|---------|----------------|
| **L1 Advisory** | 2nd retry failed | Guidance on scope/tools (async, task continues) |
| **L2 Blocking** | 3rd retry + critical path | Direct intervention required (sync, task pauses) |
| **L3 Override** | Gate 5 failed | Final approve/reject with comments |

**Completeness Index (CI):**
```
CI = SC×0.25 + TC×0.35 + WR×0.20 + FD×0.20
SC = Source Coverage, TC = Topic Coverage, WR = Weighted Recency, FD = Fact Density
A: ≥85 proceed | B: 70–85 minor gaps | C: 55–70 re-search | D: 40–55 full re-search | F: <40 escalate
```

---

## Output Formats

> **Полная спецификация:** `references/output_formats.md`

### 6 Core Formats

| Формат | Триггер | Ключевые свойства |
|--------|---------|-------------------|
| **Research Report** | Deep exploration | Full structure: snapshot → intro → findings → analysis → implications → recommendations → limitations → sources |
| **Executive Brief** | Decision support | BLUF (Bottom Line Up Front), ≤800 words, quantified, actionable |
| **Fact Sheet** | Factual lookup | One fact per row, every fact traced to source, confidence rated |
| **Comparison Matrix** | Comparative | Weighted criteria, evidence-backed cells, no overall "winner" |
| **Timeline** | Chronological | Events sourced, confidence of date, parallel tracks supported |
| **Annotated Bibliography** | Source discovery | Each source summarized, relevance score, reading order |

### Progressive Disclosure Rule
```
Depth 1–2: Executive Snapshot + Key Findings + Sources
Depth 3:   + Methodology + Analysis
Depth 4:   + Implications + Limitations + TOC
Depth 5:   + Recommendations + Appendices (raw data, glossary)
```

---

## CAPTCHA Module

> **Полная документация:** `CAPTCHA_MODULE.md`

### Stealth-First Approach
1. **Prevention > Solving:** Используй CloakBrowser (C++ patched Chromium) для предотвращения появления CAPTCHA
2. **Detection:** browser_visit + screenshot → визуальная проверка на challenge
3. **Graceful degradation:** Если blocked → не паникуй, перейди к fallback

### Fallback Chain
```
CloakBrowser (prevent) → CapSolver (AI, 2-5s, $0.80/1K) 
                       → Anti-Captcha (cheap images, $0.50/1K)
                       → 2Captcha (widest support, $1-3/1K, 13-30s)
                       → Manual (last resort)
```

### Cost Tracking
- Каждый CAPTCHA-solve логируется: timestamp, type, cost, success/fail
- Автоматический подсчёт в общем budget research task

---

## References

| Файл | Описание |
|------|----------|
| `AGENT.MD` | Heartbeat/checkpoint protocol — восстановление после прерываний |
| `SKILL.master.md` | Полная документация (lazy loading) — все модули в деталях |
| `references/tool_matrix.md` | Полная матрица инструментов — все tools с атрибутами, fallback chains, rate limits |
| `references/strategy_guide.md` | Стратегии сбора — Route A/B/C/D, depth levels, parallelization rules, cost budgeting |
| `references/decomposition_guide.md` | Декомпозиция задач — atomic subtasks, dependency types, graph notation, patterns |
| `references/acceptance_framework.md` | Критерии приёмки — AC templates, quality gates, RCA protocol, re-search loop, confidence scoring |
| `references/output_formats.md` | Форматы вывода — 6 форматов с триггерами, citation system, confidence visualization |
| `references/factcheck_system.md` | Система фактчеккинга — 6 стратегий, 6 категорий, FCA workflow, метрики |
| `references/source_authority_framework.md` | Авторитетность источников — Tier S/A/B/C/D, domain-specific maps, composite score formula |
| `references/cost_matrix_full.md` | Cost-матрица — tier system, pricing, estimation calculator, optimization tips, hidden costs |
| `references/bypass_paywall_research.md` | Обход paywall (gray area) — методы доступа к закрытому контенту |
| `LEGAL_METHODS.md` | Легальные методы доступа — open access, library access, FOIA, авторские запросы |
| `references/HOOK_MIDDLEWARE.md` | Hook-driven middleware — PreToolUse/PostToolUse hooks, blocking validation, async observation, cost tracking, quality gates |
| `references/PLATFORM_DISTRIBUTION.md` | Multi-platform distribution — Claude Code, Claude.ai, Codex CLI, Copilot, Cursor, Windsurf, compatibility matrix |

---

*Deep Research Skill v0.2.0 — testing release. 18/18 Acceptance Criteria implemented. Полная документация: SKILL.master.md. Язык адаптируется к языку пользователя. All phase modules load on-demand — no eager loading.*
