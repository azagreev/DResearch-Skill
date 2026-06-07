# Исследование Academic Research Skills: Паттерны верификации данных

## Дата исследования: 2026-06-08
## Репозиторий: https://github.com/Imbad0202/academic-research-skills
## Версия проекта: v3.11.1
## Исследователь: Academic Skills Researcher

---

## 1. Academic Research Skills — Обзор проекта

### 1.1 Что это за проект

**Academic Research Skills (ARS)** — это comprehensive suite of Claude Code skills для академических исследований, охватывающая полный pipeline от исследования до публикации. Проект создан как open-source инструментарий (28.2k звёзд, 2.3k форков) для Claude Code и представляет собой один из наиболее зрелых примеров AI-academic tooling.

**Ключевый принцип:** "AI is your copilot, not the pilot" — инструмент не пишет работу за исследователя, а берёт на себя рутину (поиск референсов, форматирование цитат, верификацию данных, проверку логической непротиворечивости), позволяя человеку сосредоточиться на содержательных задачах.

### 1.2 Архитектура и организация

Проект состоит из **4 основных skill'ов** и **32+ агентов**:

| Skill | Назначение | Агенты | Версия |
|-------|-----------|--------|--------|
| `deep-research` | Глубокое исследование темы | 13 | v2.9.4 |
| `academic-paper` | Написание академической работы | 12 | — |
| `academic-paper-reviewer` | Рецензирование работы | 7 | v1.10.0 |
| `academic-pipeline` | Оркестрация полного pipeline | 5 | v3.11.1 |

**10-стадийный pipeline:**
1. **RESEARCH** — Исследование темы
2. **WRITE** — Написание работы
3. **REVIEW** — Первичное рецензирование
4. **REVISE** — Ревизия
5. **INTEGRITY 2.5** — Проверка целостности (блокирующая)
6. **RE-REVIEW** — Повторное рецензирование
7. **RE-REVISE** — Повторная ревизия
8. **INTEGRITY 4.5** — Финальная проверка целостности
9. **FINALIZE** — Финализация
10. **PROCESS SUMMARY** — Документирование процесса

### 1.3 Файловая структура

```
academic-research-skills/
├── .claude-plugin/          # Plugin packaging для Claude Code
├── .claude/                 # Routing discipline, CLAUDE.md
├── .github/                 # GitHub Actions, templates
├── academic-paper/          # Написание работы (12 агентов)
├── academic-paper-reviewer/ # Рецензирование (7 агентов)
├── academic-pipeline/       # Оркестрация (5 агентов)
│   ├── agents/
│   ├── references/          # Протоколы, failure modes
│   └── templates/
├── commands/                # CLI-команды (15+ команд ars-*)
├── deep-research/           # Глубокое исследование (13 агентов)
│   ├── agents/
│   ├── references/          # API protocols, style guides
│   └── templates/
├── docs/                    # ARCHITECTURE.md, SETUP.md, PERFORMANCE.md
├── evals/                   # Система оценки
├── examples/                # Примеры выходных документов
├── hooks/                   # PreToolUse hooks
├── scripts/                 # Проверки pipeline integrity
├── shared/                  # Общие паттерны и протоколы
│   ├── agents/
│   ├── contracts/
│   ├── policy_data/
│   ├── references/
│   └── templates/
├── skills/                  # Skill definitions
└── tests/                   # Тесты
```

### 1.4 Метаданные и аннотации

Каждый skill декларирует:
- **`data_access_level`**: `raw` / `redacted` / `verified_only` — уровень доступа к данным
- **`task_type`**: `open-ended` / `outcome-gradable` — тип задачи
- **`status`**: active / deprecated — статус
- **`depends_on`**: зависимости от других skills

**Ценность**: Это production-ready система с чёткой архитектурой, явными контрактами между компонентами и многоуровневой системой верификации.

---

## 2. Verification Patterns — Паттерны верификации данных

### 2.1 Многоуровневая система верификации (Multi-Tier Verification)

ARS использует **4 уровня (tiers) верификации**, дополненных кросс-индексной триангуляцией:

| Tier | Метод | Покрытие | Назначение |
|------|-------|----------|------------|
| **T1** | WebSearch (title + author) | Все источники | Первичная проверка существования |
| **T2** | Semantic Scholar API | ~200M papers | Структурированная проверка метаданных |
| **T3** | Crossref API (DOI registry) | DOI-индексированные | Проверка DOI и публикационных данных |
| **T4** | arXiv API (Atom feed) | arXiv preprints | Проверка preprint-источников |

**Кросс-индексная триангуляция (v3.9.0+):** Каждый источник проверяется через минимум 2 независимых индекса (S2 + CrossRef + OpenAlex). Несоответствия флагируются как `crossref_unmatched` или `s2_unmatched`.

### 2.2 Five-Type Citation Hallucination Taxonomy

Integrity Verification Agent использует систематическую таксономию галлюцинаций цитат (GPTZero x NeurIPS 2025; Adams et al., 2026):

| Тип | Код | Частота | Описание | Стратегия обнаружения |
|-----|-----|---------|----------|----------------------|
| **Total Fabrication** | TF | ~28% | Целая статья не существует | WebSearch title+author → no results |
| **Plausible Author/Conference** | PAC | ~23% | Реальный учёный, но работа не его | Проверка публикаций через Google Scholar |
| **Incomplete Hallucination** | IH | ~19% | Отсутствуют детали (DOI, volume, pages) | Флаг, если нет DOI + volume + pages |
| **Partial Hallucination** | PH | ~18% | Микс реальных элементов из разных источников | Кросс-проверка ВСЕХ метаданных |
| **Minor Distortion** | MD | ~12% | Небольшие искажения (год, инициалы, venue) | Поштучное сравнение каждого поля |

### 2.3 Integrity Verification Agent — детальный протокол

**Core principle: Zero tolerance.** Каждая сфабрикованная ссылка или ошибочная цитата должна быть найдена.

**Anti-Hallucination Mandate:**
- **NEVER** полагаться на память/знания AI для верификации
- Каждая ссылка верифицируется через WebSearch, независимо от того, насколько "знакомой" она кажется
- "Трудно верифицировать" — недопустимый вердикт. Каждая ссылка должна получить статус VERIFIED или NOT_FOUND
- Книжные главы требуют усиленной верификации (поиск TOC или DOI)
- Кросс-проверка похожих ссылок (чтобы отловить mashup-галлюцинации)

**7-модальная блокирующая проверка (Stage 2.5 & 4.5):**
1. Implementation bugs passing AI self-review
2. Hallucinated citations
3. Shortcut reliance (spurious correlations)
4. Hallucinated results (fabricated data)
5. Bug-as-insight reframing
6. Methodology fabrication
7. Frame-lock (cognitive fixation)

### 2.4 Claim-Reference Alignment Audit (v3.8, opt-in)

**ARS_CLAIM_AUDIT=1** включает L3 audit gate на переходе Stage 4 → Stage 5:

- Fetch cited source against each anchor
- Judge whether the claim is actually supported
- Five HIGH-WARN classes gate-refuse output:
  1. `claim-not-supported`
  2. `negative-constraint-violation`
  3. `fabricated-reference`
  4. `anchorless`
  5. `constraint-violation-uncited`

**Calibration:** 20-tuple gold set с порогами FNR<0.15 + FPR<0.10

### 2.5 Same-Source Hallucination Problem

Ключевая инсайт: стресс-тест 68 AI-генерированных цитат показал, что 31% имели проблемы — и все прошли 3 раунда same-model проверки целостности. Причина: верифицирующий AI и генерирующий AI разделяют одно и то же training data distribution.

**Решение ARS:**
- Обязательная верификация через внешние API (не через parametric memory)
- Кросс-модельная верификация (опционально, через ARS_CROSS_MODEL)
- Anti-leakage protocol: проверка, что утверждения пришли из session material, а не из training-time memory

---

## 3. Citation Management — Система цитирования

### 3.1 Three-Layer Citation Anchors (v3.7.3)

Каждая цитата несёт трёхслойный якорь для claim-level аудита:

```
Citation Anchor Structure:
├── Layer 1: Source existence proof (S2/CrossRef ID)
├── Layer 2: Claim-to-source locator (specific page/section)
└── Layer 3: Claim fidelity assessment (supported/partial/unsupported)
```

### 3.2 Trust-Chain Frontmatter (v3.7.1)

Каждый документ включает provenance-блок:
- `lookup_verified`: true/false — была ли цитата верифицирована через API
- `semantic_scholar_id`: ID в S2
- `crossref_status`: matched/unmatched
- `verification_timestamp`: когда была проведена верификация

### 3.3 Bibliography Agent — систематический подход

**Core Principles:**
- Systematic, not ad hoc — каждый поиск следует документированной стратегии
- Reproducibility — другой исследователь должен мочь воспроизвести поиск
- Inclusion/exclusion transparency — критерии определяются ДО поиска
- APA 7.0 compliance — все цитаты в формате APA 7th edition
- Breadth before depth — широкая сеть, затем строгая фильтрация

**Verification Tiers для Bibliography:**
1. **Broad Discovery**: Web search для поиска релевантных источников
2. **S2 API Verification**: Последовательная верификация через Semantic Scholar
3. **Cross-Index Triangulation**: Проверка через CrossRef + OpenAlex
4. **Manual Sources**: Отдельная маркировка `obtained_via: 'manual'`

### 3.4 arXiv Resolver + Verification Cache (v3.10)

- Atom feed parsing для arXiv ID resolution
- Skip on no-ID + non-Atom 200 guard
- Verification cache для избежания повторных запросов
- Cache invalidation через `/ars-cache-invalidate`

### 3.5 Citation Gate — форматтерный hard gate

Форматтерный агент имеет 10 REFUSE-правил (6-10 добавлены в v3.8):
- REFUSE 6: claim-not-supported
- REFUSE 7: negative-constraint-violation
- REFUSE 8: fabricated-reference
- REFUSE 9: anchorless
- REFUSE 10: constraint-violation-uncited

---

## 4. Source Quality Assessment — Оценка качества источников

### 4.1 Evidence Hierarchy (7 Levels)

Используется pyramid of evidence с 7 уровнями:

| Level | Тип доказательства | Вес | Примеры |
|-------|-------------------|-----|---------|
| **I** | Systematic Reviews / Meta-analyses | Highest | Cochrane, Campbell |
| **II** | Randomized Controlled Trials | Very High | RCT с пререгистрацией |
| **III** | Controlled Studies (non-randomized) | High | Quasi-experimental |
| **IV** | Case-Control / Cohort Studies | Moderate | Longitudinal studies |
| **V** | Systematic Reviews of Descriptive Studies | Moderate-Low | — |
| **VI** | Single Descriptive / Qualitative Studies | Low | Case studies |
| **VII** | Expert Opinion / Committee Reports | Lowest | Consensus reports |

### 4.2 Source Verification Agent — полный чеклист

Агент проверяет:
1. **Evidence grade** — применяет иерархию доказательств
2. **Predatory journal detection** — Beall's list + Cabells + DOAJ
3. **Conflict of Interest (COI) flags** — funding disclosures
4. **Currency check** — в fast-moving fields приоритет свежим источникам
5. **Per-claim verification** — каждое утверждение верифицируется против множественных источников

### 4.3 Risk of Bias Agent (ROB)

Специализированный агент для оценки риска смещения:
- Selection bias
- Performance bias
- Detection bias
- Attrition bias
- Reporting bias
- Other bias

Использует инструменты: Cochrane RoB 2, ROBINS-I, Newcastle-Ottawa Scale

### 4.4 Triangulation Policy Layer (v3.10)

- Кросс-индексная триангуляция: S2 + CrossRef + OpenAlex
- Совпадение ≥2 индексов = высокая уверенность
- Несовпадение = advisory flag (`crossref_unmatched`, `s2_unmatched`)
- Опциональный strict mode: `contamination_triangulation` может повысить k=3 сигнал до terminal block

---

## 5. Research Methodology — Методы исследования

### 5.1 Модели исследования (7 modes в deep-research)

| Mode | Выход | Надзор | Триггеры |
|------|-------|--------|----------|
| `full` | APA 7.0 report, 3K-8K слов | High | "research [topic]" |
| `quick` | Research brief, 500-1.5K слов | Medium | "quick brief" |
| `review` | Reviewer report | High | "review this paper" |
| `lit-review` | Annotated bibliography + synthesis | Medium | "literature review" |
| `fact-check` | Claim-by-claim verification | Medium | "verify claims" |
| `socratic` | Research Plan + INSIGHT collection | Very High | "guide my research" |
| `systematic-review` | PRISMA 2020 report, 5K-15K слов | Medium | "systematic review" |

### 5.2 PRISMA Systematic Review Protocol

- Pre-registered protocol
- Comprehensive search across multiple databases
- Explicit inclusion/exclusion criteria
- Quality assessment of included studies
- Statistical pooling (meta-analysis)
- PRISMA reporting guidelines

### 5.3 Phase-Based Agent Architecture

Deep-research разделён на 6 фаз, каждый агент закреплён за одной фазой:

| Phase | Агенты | Deliverable |
|-------|--------|-------------|
| Phase 1 (Scoping) | research_question_agent, socratic_mentor_agent | RQ Brief + Methodology Blueprint |
| Phase 2 (Investigation) | bibliography_agent, source_verification_agent | Annotated Bibliography + Verification Report |
| Phase 3 (Analysis) | synthesis_agent, meta_analysis_agent, timeline_extraction_agent | Synthesis Report + Meta-Analysis |
| Phase 4 (Compilation) | report_compiler_agent | APA 7.0 Report |
| Phase 5 (Review) | editor_in_chief_agent, devils_advocate_agent | Editorial Review + Challenges |
| Phase 6 (Revision) | ethics_review_agent, monitoring_agent | Ethics Clearance + Monitoring Plan |

### 5.4 Socratic Mode

- SCR Loop (State-Challenge-Reflect)
- State-Challenge-Reflect mechanism
- Reading Probe для диагностики понимания
- Idea-diversity advisories (v3.5+)

---

## 6. Fact-Checking Protocols — Протоколы проверки фактов

### 6.1 Fact-Check Mode (deep-research)

Специализированный режим: **claim-by-claim verification report**

- Каждое утверждение разбирается отдельно
- Для каждого claim: evidence for / evidence against / confidence level
- Cross-reference against multiple sources
- Final verdict: supported / partially supported / unsupported / inconclusive

### 6.2 Sub-Claim Decomposition (v3.11.1)

Перед citation judgment каждое утверждение декомпозируется на sub-claims:
- Atomic claims (неделимые утверждения)
- Каждый sub-claim проверяется независимо
- Aggregation logic для финального вердикта

### 6.3 Cross-Model Verification (опционально)

**ARS_CROSS_MODEL** включает верификацию через вторую модель:

| Primary | Cross-Verifier | Провайдер |
|---------|---------------|-----------|
| Claude Opus 4.8 | GPT-5.4 Pro | OpenAI |
| Claude Opus 4.8 | Gemini 3.1 Pro | Google |

**Результаты:** Оценочное снижение ошибок с 31% до ~5-10%

**Consent boundary:** Перед отправкой unpublished manuscripts требуется явное согласие пользователя.

### 6.4 Anti-Leakage Protocol

Проверка, что утверждения и цитаты пришли из материалов сессии, а не из training-time памяти модели. Предотвращает "same-source hallucination".

---

## 7. Integration with Academic Databases — Интеграция с академическими базами данных

### 7.1 Semantic Scholar API

```
API: https://api.semanticscholar.org/graph/v1
Rate limit: 1 req/s (unauthenticated), 10 req/s (with key)
API key: S2_API_KEY
```

**Query Patterns:**
1. Title Search (primary) — Levenshtein similarity >= 0.70
2. DOI Lookup — exact match + title cross-check
3. S2 ID Lookup — для re-verification

**PaperOrchestra (Song et al., 2026) inspiration:**
- Two-phase citation pipeline: broad discovery → sequential verification
- P0 Recall +2-6%, P1 Recall +12-14% over baselines

### 7.2 CrossRef API

```
API: https://api.crossref.org
Rate limit: 10 req/s (polite pool with mailto:)
Env var: CROSSREF_POLITE_EMAIL
```

**Query Patterns:**
1. DOI Lookup with Title Cross-Check — Levenshtein 0.70 threshold
2. Title Search — fallback when DOI absent

### 7.3 arXiv API

```
API: https://export.arxiv.org/api/query
Format: Atom feed
```

**Резолюция:**
- arXiv ID → Atom entry
- Skip on no-ID + non-Atom 200 guard
- Verification cache

### 7.4 OpenAlex API

```
API: https://api.openalex.org
Rate limit: 10 req/s
```

Используется как третий индекс для кросс-индексной триангуляции (v3.9.0).

### 7.5 Search Strategy Framework

Bibliography Agent следует систематическому подходу:

1. **Define Search Parameters**: databases, date range, language, study types
2. **Build Search Strings**: Boolean operators, MeSH terms, keyword variants
3. **Execute Across Databases**: systematic execution
4. **Document Strategy**: поисковая стратегия документируется для воспроизводимости
5. **Apply Inclusion/Exclusion Criteria**: предопределённые критерии
6. **Create PRISMA Flow Diagram**: визуализация процесса отбора

---

## 8. Extractable Value — Извлекаемая ценность для Deep Research Skill

### 8.1 Топ-15 паттернов с оценкой ценности

| # | Паттерн | Ценность | Переиспользование | Адаптация | Комментарий |
|---|---------|----------|-------------------|-----------|-------------|
| **1** | **Five-Type Citation Hallucination Taxonomy** | **HIGH** | As-is | Нет | Систематическая классификация галлюцинаций цитат, готовая для интеграции |
| **2** | **Multi-Tier Verification (T1-T4)** | **HIGH** | С адаптацией | API endpoints | Архитектура проверки через WebSearch → S2 → CrossRef → arXiv |
| **3** | **Anti-Hallucination Mandate** | **HIGH** | As-is | Нет | Принцип "NEVER rely on AI memory" — критически важен |
| **4** | **Cross-Index Triangulation (k=2+)** | **HIGH** | С адаптацией | Наши API | Проверка через 2+ независимых индекса |
| **5** | **Ground-Truth Isolation Pattern** | **HIGH** | As-is | Нет | 3-layer data access (raw → verified → redacted) |
| **6** | **7-Level Evidence Hierarchy** | **HIGH** | As-is | Нет | Pyramid of evidence для оценки качества источников |
| **7** | **Claim-Reference Alignment Audit** | **HIGH** | С адаптацией | Наш gate | L3 audit с 5 HIGH-WARN классами |
| **8** | **Sub-Claim Decomposition** | **MEDIUM** | С адаптацией | Наш формат | Разбиение утверждений на atomic claims |
| **9** | **Phase-Boundary Agent Architecture** | **MEDIUM** | Концепция | Наша архитектура | Single-phase assignment с запретом на phase inflation |
| **10** | **PRISMA Systematic Review Protocol** | **MEDIUM** | С адаптацией | Наши триггеры | Полный протокол систематического обзора |
| **11** | **Anti-Leakage Protocol** | **MEDIUM** | Концепция | Наша реализация | Проверка источника утверждений |
| **12** | **Cross-Model Verification** | **MEDIUM** | Концепция | Наши модели | Верификация через вторую модель |
| **13** | **Socratic Mode (SCR Loop)** | **MEDIUM** | С адаптацией | Наш диалог | State-Challenge-Reflect механизм |
| **14** | **Trust-Chain Frontmatter** | **MEDIUM** | С адаптацией | Наш формат | Provenance-блок для каждой цитаты |
| **15** | **7-Mode Failure Checklist** | **LOW** | Концепция | Наши failure modes | AI Research Failure Mode Checklist |

### 8.2 Что можно переиспользовать as-is

1. **Five-Type Hallucination Taxonomy** — готовая классификация с частотами и стратегиями обнаружения
2. **Anti-Hallucination Mandate** — core principle для любой verification системы
3. **Evidence Hierarchy (7 levels)** — стандартная в академическом сообществе иерархия
4. **Ground-Truth Isolation Pattern** — 3-layer архитектура изоляции данных
5. **Levenshtein similarity threshold (0.70)** — доказанный экспериментально порог для title matching

### 8.3 Что нужно адаптировать

1. **Multi-Tier Verification** — адаптировать API endpoints под наши инструменты (search, scholar, arxiv)
2. **Cross-Index Triangulation** — интегрировать с нашими data source tools
3. **Claim-Reference Alignment Audit** — адаптировать gate-логику под наш pipeline
4. **Phase-Boundary Architecture** — адаптировать концепцию к нашей multi-agent системе
5. **Trust-Chain Frontmatter** — адаптировать формат метаданных цитат

### 8.4 Что не подходит для нашего use case

1. **APA 7.0 formatting** — специфично для академических работ, не нужно для generic research
2. **LaTeX hardening / DOCX conversion** — специфично для paper writing
3. **Peer-review simulation (5 reviewers)** — избыточно для research reports
4. **IRB Decision Tree / Ethics Checklist** — специфично для human subjects research
5. **VLM Figure Verification** — узкоспециализировано

---

## 9. Comparison with Our Approach — Сравнение с нашим подходом

### 9.1 Что academic-research-skills делает лучше нас

| Область | ARS | Наш skill | Рекомендация |
|---------|-----|-----------|--------------|
| **Проверка цитат** | 5-type taxonomy + zero-tolerance gate | Нет систематической проверки | Внедрить Five-Type Taxonomy |
| **Иерархия доказательств** | 7-level pyramid | Нет явной иерархии | Внедрить Evidence Hierarchy |
| **Кросс-индексная триангуляция** | S2 + CrossRef + OpenAlex | Один источник | Множественная верификация |
| **Anti-hallucination** | "Never rely on AI memory" | Частично | Формализовать Anti-Hallucination Mandate |
| **Архитектура агентов** | 32+ специализированных агента | Меньше | Расширить число специализированных агентов |
| **Claim-level audit** | L3 audit с HIGH-WARN classes | Нет | Внедрить Claim Audit Gate |
| **Ground-truth isolation** | 3-layer data access | Нет | Внедрить data_access_level аннотации |

### 9.2 Что наш skill должен делать лучше

| Область | ARS | Наш skill | Преимущество |
|---------|-----|-----------|--------------|
| **Гибкость задач** | Academic-only | Universal research | Ширше scope |
| **Web integration** | Через WebSearch tool | Нативный browser + search | Богаче источники |
| **Мультимодальность** | VLM для figures | Полная мультимодальность | Шире форматы |
| **Скорость** | Full pipeline ~$4-6 | Оптимизированный | Быстрее |
| **Интерактивность** | Checkpoint-based | Real-time feedback | Гибче |

### 9.3 Complementarity — как дополняют друг друга

**ARS как reference implementation:**
- ARS — это production-grade академическая система с 499 коммитами, 14 контрибьюторами, 28.2k звёздами
- Она доказала свою эффективность в реальных академических сценариях
- Её паттерны verification и citation management являются gold standard

**Наш skill как universal research tool:**
- Мы не ограничены академическим форматом
- У нас более гибкая архитектура
- Мы можем адаптировать лучшие паттерны ARS под universal use case

**Рекомендация:** Адаптировать паттерны #1-#7 из ARS как core verification layer для нашего Deep Research Skill, сохраняя при этом нашу универсальность и гибкость.

---

## 10. Топ-5 ценных паттернов для переиспользования

### Паттерн #1: Five-Type Citation Hallucination Taxonomy
**Ценность: HIGH**
- Систематическая классификация 5 типов галлюцинаций цитат с частотами и стратегиями обнаружения
- Основан на исследованиях (GPTZero x NeurIPS 2025; Adams et al., 2026)
- Каждый тип имеет конкретный detection strategy
- **Применение:** Интегрировать в наш verification layer как стандартный чеклист

### Паттерн #2: Multi-Tier Verification Architecture
**Ценность: HIGH**
- 4 уровня: WebSearch → S2 API → CrossRef API → arXiv API
- Каждый уровень имеет конкретный matching rule (Levenshtein threshold)
- Graceful degradation при недоступности API
- **Применение:** Адаптировать под наши data source tools

### Паттерн #3: Ground-Truth Isolation Pattern
**Ценность: HIGH**
- 3-layer mental model: raw inputs → verified artifacts → redacted outputs
- Однонаправленный flow: artifact can be promoted, never demoted
- Layer 3 material cannot appear as input to Layer 1/2 processes
- **Применение:** Внедрить data_access_level аннотации для всех skills

### Паттерн #4: Anti-Hallucination Mandate
**Ценность: HIGH**
- Core principle: "NEVER rely on AI memory/knowledge to verify a reference"
- Каждая ссылка ВСЕГДА верифицируется через WebSearch/API
- "Difficult to verify is NOT an acceptable verdict"
- **Применение:** Формализовать как обязательный принцип нашего skill

### Паттерн #5: Claim-Reference Alignment Audit (L3 Audit)
**Ценность: HIGH**
- Fetch cited source against each anchor
- 5 HIGH-WARN classes с gate-refuse logic
- Calibration: 20-tuple gold set с FNR<0.15 + FPR<0.10
- **Применение:** Адаптировать как опциональный audit layer

---

## 11. Детальные находки по секциям

### 11.1 Data Access Level Metadata (v3.3.2+)

Каждый skill декларирует `data_access_level`:
- **`raw`** — непроверенные входные данные (deep-research)
- **`verified_only`** — только верифицированные артефакты (academic-pipeline)
- **`redacted`** — анонимизированные данные для evaluation

Паттерн адаптирован из Anthropic's automated-w2s-researcher (2026).

### 11.2 Compliance Report Schema (v3.3.5+)

JSON Schema для honest benchmark comparisons:
- `benchmark_report.schema.json` — стандартизированный формат
- `evals_lift_report.schema.json` — отчёты об улучшениях
- `compliance_report.schema.json` — compliance отчёты (Schema 12)

### 11.3 Artifact Reproducibility Lockfile (v3.3.5+)

- Optional `repro_lock` sub-block на Material Passport
- Configuration documentation, NOT replay guarantee
- LLM outputs are not byte-reproducible

### 11.4 RAISE Framework

4 principles + 8-role matrix для human-AI collaboration:
- **R**espect — уважение к экспертизе человека
- **A**ccountability — ясное разделение ответственности
- **I**ntegrity — академическая честность
- **S**kepticism — здоровый скептицизм
- **E**xcellence — стремление к качеству

### 11.5 Sprint Contract Schema

`generator-evaluator contract` для структурированного взаимодействия агентов:
- Explicit deliverables
- Acceptance criteria
- Quality thresholds

---

## 12. Рекомендации для внедрения

### Приоритет 1 (HIGH, реализовать немедленно)

1. **Five-Type Hallucination Taxonomy** — интегрировать в verification layer
2. **Anti-Hallucination Mandate** — сделать core principle
3. **Evidence Hierarchy** — внедрить для source quality scoring
4. **Multi-Tier Verification** — адаптировать под наши data sources

### Приоритет 2 (MEDIUM, реализовать в следующей итерации)

5. **Cross-Index Triangulation** — добавить как опцию
6. **Claim-Reference Alignment Audit** — опциональный audit gate
7. **Ground-Truth Isolation** — data_access_level аннотации
8. **Cross-Model Verification** — для high-stakes judgments

### Приоритет 3 (LOW, рассмотреть в будущем)

9. **PRISMA Protocol** — для systematic review mode
10. **Socratic Mode (SCR Loop)** — для guided research
11. **Peer-Review Simulation** — для quality assurance
12. **Calibration Framework** — gold sets для FNR/FPR

---

## 13. Заключение

Academic Research Skills представляет собой **зрелую, production-ready систему** с одной из наиболее продвинутых архитектур верификации данных среди open-source AI-инструментов. Ключевые инсайты:

1. **Same-source hallucination** — критическая проблема, которую нельзя решить в рамках одной модели. Требуется внешняя верификация.

2. **Zero-tolerance principle** — для цитат и фактов нужен абсолютный порог, без компромиссов.

3. **Layered architecture** — разделение на raw/verified/redacted уровни предотвращает reward hacking.

4. **Explicit taxonomy** — систематическая классификация failure modes позволяет их находить.

5. **Cross-reference is essential** — ни один источник не является достаточным; триангуляция обязательна.

Для нашего Deep Research Skill рекомендуется адаптировать паттерны #1-#7 как core verification layer, сохраняя универсальность и гибкость нашей архитектуры.

---

## Приложение: Полный список источников из репозитория

### Основные файлы для изучения
- `docs/ARCHITECTURE.md` — полная архитектура pipeline
- `academic-pipeline/SKILL.md` — оркестрация (621 строк)
- `deep-research/SKILL.md` — исследование (507 строк)
- `academic-paper-reviewer/SKILL.md` — рецензирование (424 строки)
- `shared/cross_model_verification.md` — кросс-модельная верификация
- `shared/ground_truth_isolation_pattern.md` — изоляция ground truth
- `deep-research/agents/source_verification_agent.md` — верификация источников
- `deep-research/agents/bibliography_agent.md` — управление цитированием
- `academic-pipeline/agents/integrity_verification_agent.md` — проверка целостности
- `academic-pipeline/agents/claim_ref_alignment_audit_agent.md` — аудит цитат
- `deep-research/references/source_quality_hierarchy.md` — иерархия доказательств
- `deep-research/references/semantic_scholar_api_protocol.md` — S2 API
- `deep-research/references/crossref_api_protocol.md` — CrossRef API
- `deep-research/references/arxiv_api_protocol.md` — arXiv API
- `deep-research/references/systematic_review_protocol.md` — PRISMA
- `academic-pipeline/references/ai_research_failure_modes.md` — failure modes
- `MODE_REGISTRY.md` — реестр всех 25 режимов

### Контекст
- Репозиторий: https://github.com/Imbad0202/academic-research-skills
- Версия: v3.11.1
- Звёзды: 28.2k | Форки: 2.3k | Коммиты: 499 | Контрибьюторы: 14
- Лицензия: CC BY-NC 4.0
