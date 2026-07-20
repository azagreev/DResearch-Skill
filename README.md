# Deep Research Skill

> **Навык глубокого исследования для Claude Code (testing release).** Многофазный workflow с cost-first выполнением, evidence-based отчётами, anti-hallucination протоколом и прозрачным confidence scoring.

**Версия:** 1.7.0 | **Лицензия:** MIT | **Язык:** русский (отчёт: ru/en через `TaskFrame.language`)
**Автор:** Andrey Zagreev | **Обратная связь:** [@zagreev](https://t.me/zagreev)

---

## Возможности

- **7-фазный workflow**: Анализ задачи → Декомпозиция → Сбор → Верификация → Синтез → Вывод → Приёмка
- **Cost-First выполнение**: 4-уровневая иерархия инструментов — начинай бесплатно, эскалируй только при необходимости
- **Evidence-Based отчёты**: каждое утверждение имеет verifiable citation с привязкой к строкам источника (【S†L{a}-L{b}】), каждый источник — tier
- **Anti-Hallucination протокол**: zero tolerance — FactCheck ветирует каждый факт; механический quote-integrity (дословные цитаты обязаны существовать в источнике) и retraction-veto (отозванные источники исключаются)
- **4 уровня глубины**: Quick (30 мин) → Standard (1–2 ч) → Deep (3–5 ч) → Exhaustive (5+ ч)
- **Confidence Scoring**: шкала 1–5 с визуальными индикаторами для каждого утверждения
- **Checkpoint Recovery**: адаптивный heartbeat (2–10 мин) + checkpoint на каждом gate — откат к последнему gate, а не к нулю
- **Cost & Cache телеметрия**: захват cache-сигналов, `cache_hit_rate`, `bundle_hash`, именованные границы компактизации, CLI `cost`
- **Typed Collection Seam**: единый контракт `CollectionResult` над любым провайдером (web_search/Jina/Firecrawl/…) со snippet-cap и risk_class
- **CI-регрессия**: 524 юнит-теста (428 engine + 96 bench), golden corpus, determinism-gate, опциональные cost/latency-пороги

### Новое в 1.7.0

Портировано из [hyperresearch](https://github.com/jordan-gibbs/hyperresearch) (jordan-gibbs) — анализ переиспользования в [`docs/HYPERRESEARCH_REUSE.md`](docs/HYPERRESEARCH_REUSE.md), сквозная трассировка REQ→критерий→тест в [`docs/TRACE_HYPERRESEARCH.md`](docs/TRACE_HYPERRESEARCH.md). 6 новых read-only CLI-verb'ов образуют верификационную батарею.

- **Механический quote-integrity** (`engine quotecheck`): дословная цитата claim'а обязана присутствовать в цитируемом источнике на указанных строках 【S†L{a}-L{b}】; own-finding с непроверенной цитатой не попадает в отчёт. + numeric-consistency (`numcheck`): числа трассируемы к источнику.
- **Syndication ≠ consensus** (`independence`): union-find кластеризует перепечатки/near-duplicate, каждая получает 1/cluster_size в composite (вес 0.20) → ниже tier/confidence; пять копий одной новости ≈ один голос. Тайбрейкер факт-чека учитывает independence.
- **Retraction-veto** (`retraction`): отозванный источник (флаг/детектор языка отзыва) исключается из support И contradicting в факт-чеке.
- **Scale-as-config-profile** (`profile`): scale-кнобы и пороги гейтов как машиночитаемый профиль (built-in по глубине, `extends`); `plan.MAX_CONCURRENT` из профиля. **Instruction-coverage** (`instrcheck`): пункты acceptance_criteria/scope без покрытия. **Patch-never-regenerate** дисциплина ревизии (SKILL.md + guard).

### Новое в 1.6.0

Портировано из [OpenResearcher](https://github.com/TIGER-AI-Lab/OpenResearcher) (TIGER-AI-Lab) — анализ переиспользования в [`docs/OPENRESEARCHER_REUSE.md`](docs/OPENRESEARCHER_REUSE.md), сквозная трассировка REQ→критерий→тест в [`docs/TRACE_OPENRESEARCHER.md`](docs/TRACE_OPENRESEARCHER.md).

- **Verifiable-citation формат** 【S†L{a}-L{b}】 — цитата привязана к конкретному диапазону строк источника (проверяемо и человеком, и верификатором) + правило «≤10 слов дословно» против скрытого копирайт-воспроизведения. Стабильная нумерация строк; обратная совместимость с legacy `[S1]` сохранена байт-в-байт.
- **Честная оценка качества** (`bench/`): LLM-судья с dual-denominator accuracy (Judged vs Overall — сбои судьи/парсинга не маскируются под ошибки движка), запинённый `JudgeConfig` (model + temperature + prompt_hash), рекурсивный двусторонний import-guard — весь недетерминизм строго вне движка.
- **Устойчивый вход CLI**: lenient-then-strict парсинг JSON (чинит markdown code-fence, smart-quotes, trailing commas), не ослабляя downstream типизированную валидацию.

---

## Выбор платформы

| Платформа | Для кого | Установка | Файл |
|-----------|----------|-----------|------|
| **Claude Code / Cowork** | Рекомендуется — установка в 1 клик, без файлов | Plugin marketplace (GitHub) | плагин |
| **Claude.ai** | Опытные пользователи, нужна загрузка скилла | Загрузка ZIP/`.skill` | папка скилла |

---

## Быстрый старт

### Claude Code / Cowork — плагин-маркетплейс (рекомендуется, без файлов)

**Cowork (для не-разработчиков):**
1. Открой **Customize** (слева внизу)
2. **Browse plugins → Personal → +**
3. **Add marketplace from GitHub**
4. Введи: `azagreev/DResearch-Skill`
5. Плагин **deep-research-skill** установится сам — навык подключится в один клик.

**Claude Code (CLI):**
```bash
/plugin marketplace add azagreev/DResearch-Skill
/plugin install deep-research-skill@deep-research-skill
```

**Активация.** Навык подключается автоматически по запросам вроде «проведи исследование», «deep research», «анализ рынка», «конкурентный анализ», «собери информацию о», «сравни», «тренды в», «due diligence». Можно вызвать и явно: `/deep-research-skill:deep-research-skill`.

#### Обновление плагина

Сторонние маркетплейсы (как этот) **не авто-обновляются по умолчанию** — авто-pull на старте сессии включён только для официального маркетплейса Anthropic. После нового релиза кнопка Update может оставаться неактивной, пока обновление не подтянуть.

**Рекомендуется — включить auto-update один раз** (дальше плагин обновляется сам на старте сессии):
- **Claude Code (CLI/desktop):** `/plugin` → **Marketplaces** → `deep-research-skill` → включить **auto-update**.
- **Cowork:** включи тумблер **auto-update** на странице плагина, если он показан.

**Разовое обновление вручную:**
- **Claude Code (CLI):** `/plugin marketplace update deep-research-skill` → обнови плагин → `/reload-plugins` (или перезапусти сессию).
- **Cowork (GUI):** Customize → `deep-research-skill` → **удали и добавь заново** (`+` → Add marketplace from GitHub → `azagreev/DResearch-Skill`) — форсит свежий клон.

### Claude.ai / Claude Desktop (ZIP-скилл)

Навык self-contained — его можно загрузить напрямую, **минуя маркетплейс**. Это рекомендуется, если нужно обойти и предупреждение о доверии к стороннему маркетплейсу, и запаздывание версии в кэше маркетплейса (ZIP всегда — текущий билд).

1. Скачай готовый ZIP из [релизов](https://github.com/azagreev/DResearch-Skill/releases/latest) — ассет `deep-research-skill-vX.Y.Z.zip`. В архиве **корневая папка** `deep-research-skill/` с `SKILL.md` внутри — именно эту структуру требует загрузка скилла в приложениях Claude (не файлы россыпью в корне архива).
   - Либо собери локально: `python scripts/build_skill.py` → `dist/deep-research-skill-vX.Y.Z.zip` (build-скрипт исключает `tests/`/`evals/`/кэши и нормализует переводы строк; критерии корректной сборки — `python -m pytest tests/release/test_skill_package.py -q`).
2. Claude → Настройки → Возможности → включи «Code execution and file creation».
3. Настроить → Скиллы → **+** → загрузи ZIP.
4. В любом чате попроси «проведи исследование …» — навык активируется.

> **Про предупреждение «Plugins installed from marketplaces are not controlled by Anthropic…».** Это штатное предупреждение Anthropic для **любого** стороннего marketplace-плагина — оно привязано к *маршруту установки из маркетплейса*, а не к содержимому скилла, и не является ошибкой. При установке из маркетплейса просто подтверди доверие; прямая загрузка ZIP этого шага не требует.

---

## Архитектура

```
SKILL.md (точка входа — 7-фазный workflow)
  ├── Phase 0: Анализ задачи & роутинг
  ├── Phase 1: Декомпозиция
  ├── Phase 2: Сбор              → engine/collect.py (CollectionResult)
  ├── Phase 3: Верификация       → engine/factcheck.py, engine/verify.py
  ├── Phase 4: Синтез
  ├── Phase 5: Вывод             → engine/report.py
  └── Phase 6: Приёмка

AGENT.MD (слой оркестрации)
  ├── Heartbeat Protocol (адаптивный интервал, §1.2)
  ├── Checkpoint Recovery (5 чекпоинтов)
  ├── Quality Gates (5 gate'ов с бюджетной аллокацией)
  └── Cost & Cache телеметрия (§3.4, именованные границы §8)

engine/ (Python-движок, stdlib-only, Python ≥3.10)
  ├── pipeline.py    — сборщик полного прогона
  ├── collect.py     — типизированный CollectionResult над провайдерами
  ├── ingest.py      — raw → Source + дедупликация
  ├── rank.py, score.py — ранжирование источников
  ├── factcheck.py   — FactCheck Agent, категории + claim-вердикты
  ├── verify.py      — независимая ре-деривация вердикта
  ├── cluster.py, memory.py — кластеризация и сессионная память
  ├── report.py      — генерация отчёта
  ├── eval.py        — IR-метрики + cost_efficiency
  ├── compact.py     — build_handoff + should_compact (named boundaries)
  ├── plan.py        — DAG-исполнитель SubTask
  ├── state.py       — gate_blocks_transition, validate_snapshot
  ├── telemetry.py   — GateCostTracker, RunTrace, cache helpers
  └── cli.py         — JSON-in/JSON-out CLI (15 subcommands)

evals/
  ├── golden_corpus.json      — baseline ранжирования
  ├── ci_regression.py        — CI-проверка метрик + cost/latency-пороги
  ├── activation_corpus.json  — should-trigger / should-not-trigger
  ├── injection_probe.json    — adversarial prompt-injection тесты
  └── grounding_probe.json    — grounding/false-confidence тесты

hooks/ (opt-in, inert по умолчанию)
  ├── budget_guard.py         — PreToolUse: блок при превышении бюджета
  ├── cost_tracker.py         — PostToolUse: трекинг стоимости
  ├── policy_guard.py         — PreToolUse: allow/deny список
  └── settings.example.json  — шаблон для ручной установки

tests/ (247 тестов, 0 skipped)
  └── test_phase1.py … test_phase13.py, test_adversarial.py, test_cli.py …

references/ (20 документов — источники истины для prose-режима)
  ├── tool_matrix.md, strategy_guide.md, decomposition_guide.md
  ├── acceptance_framework.md, output_formats.md, factcheck_system.md
  ├── source_authority_framework.md, cost_matrix_full.md
  └── … (HOOK_MIDDLEWARE.md, PLATFORM_DISTRIBUTION.md, исследования)
```

---

## Структура репозитория

```
DResearch-Skill/                              # маркетплейс (корень репозитория)
├── .claude-plugin/
│   └── marketplace.json                      # манифест маркетплейса
├── plugins/
│   └── deep-research-skill/
│       ├── .claude-plugin/
│       │   └── plugin.json                   # манифест плагина (version: 1.7.0)
│       └── skills/
│           └── deep-research-skill/          # self-contained навык
│               ├── SKILL.md                  # точка входа (7-фазный workflow)
│               ├── SKILL.master.md           # полная мастер-документация
│               ├── AGENT.MD                  # протокол оркестрации
│               ├── LEGAL_METHODS.md
│               ├── CAPTCHA_MODULE.md
│               ├── engine/                   # Python-движок (stdlib-only)
│               ├── evals/                    # CI-регрессия + корпуса
│               ├── hooks/                    # opt-in hook-скрипты
│               ├── tests/                    # 247 юнит-тестов
│               └── references/               # 20 reference-документов
├── docs/
│   ├── REBUILD_PLAN.md
│   ├── TECHDEBT.md
│   ├── installation.md
│   └── usage.md
├── examples/
│   └── supervised_orchestrator.workflow.js
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## CLI-подкоманды движка

```bash
# JSON-in/JSON-out (все subcommands):
python -m engine <subcommand> [--input file.json]

# Доступные subcommands:
run          — полный прогон pipeline
collect      — нормализация провайдера → CollectionResult
ingest       — raw → Source[]
rank         — ранжирование источников
score        — scoring источников (+ veto-слой и score-breakdown, v1.2.0)
factcheck    — верификация claims
verify       — независимая ре-деривация категорий (disagreement-флаг)  # новое v1.3.0
cluster      — кластеризация
plan         — валидация DAG / topo-порядок / ready-set  # новое v1.3.0
gate         — статус gate-сигналов (blocks_transition/should_stop/should_compact)  # новое v1.3.0
memory       — сессионная память (+ record-feedback/list-feedback, v1.2.0)
eval         — IR-метрики + cost_efficiency
cost         — per-gate cost-отчёт через GateCostTracker  # новое v1.1.0
rescore      — ре-деривация скоринга над замороженным набором  # новое v1.2.0
report       — генерация отчёта
compact      — build_handoff (do_not_redo)
checkpoint   — запись/чтение checkpoint
resume       — восстановление из checkpoint
hook         — list/test/fire hook-скриптов
doctor       — диагностика окружения
```

---

## Tool Tiers

| Tier | Инструменты | Cost | Покрытие |
|------|-------------|------|----------|
| **Tier 1** | Native Claude tools (web_search, browser) | Free | ~70% задач |
| **Tier 2** | Jina AI Reader, arXiv, Scholar | Free/low | ~20% задач |
| **Tier 3** | Browserbase, ECC, PubMed | Low/medium | ~8% задач |
| **Tier 4** | Firecrawl, premium APIs | Premium | ~2% задач |

Подробный прайсинг — в `references/cost_matrix_full.md`.

---

## Confidence Scale

| Балл | Уровень | Индикатор | Когда |
|------|---------|-----------|-------|
| 5 | Certain | 🔵 | Подтверждено несколькими Tier S источниками |
| 4 | High | 🟢 | Один Tier S или несколько Tier A |
| 3 | Moderate | 🟡 | Отраслевой консенсус, без прямого источника |
| 2 | Low | 🔴 | Ограниченные/слабые источники |
| 1 | Speculative | ⚪ | Вывод, без прямых доказательств |

---

## Source Authority Tiers

| Tier | Тип источника | Доверие |
|------|---------------|---------|
| **S** | SEC filings, регуляторы, первичные данные | Ground truth |
| **A** | Авторитетные СМИ, peer-reviewed журналы | High |
| **B** | Отраслевые отчёты, established blogs | Medium |
| **C** | Агрегаторы новостей, пресс-релизы | Low-medium |
| **D** | Форумы, соцсети | Low (сначала проверить) |

---

## Требования

- **Claude Code** ≥ 4.6 (или Claude.ai с включённым code execution)
- **Python** ≥ 3.10 (для запуска движка локально; stdlib-only, pip не нужен)
- **MCP-серверы** (опционально):
  - `browserbase` — облачная браузерная автоматизация
  - `file-system` — локальные файловые операции

---

## Оценка стоимости

| Глубина | Время | Subtasks | Прим. стоимость (API) |
|---------|-------|----------|-----------------------|
| Quick | 30 мин | 5–8 | $0–2 |
| Standard | 1–2 ч | 10–15 | $2–5 |
| Deep | 3–5 ч | 20–30 | $5–15 |
| Exhaustive | 5+ ч | 30–50 | $15–50 |

> Стоимость — только для внешних API. Native Claude tools бесплатны. Фактические затраты зависят от выбора инструментов и доступности источников.

---

## Hook Middleware — ручная установка

Навык включает три hook-скрипта (stdlib only, кросс-платформенные), которые перехватывают вызовы инструментов Claude Code:

| Скрипт | Тип | Назначение |
|--------|-----|-----------|
| `hooks/policy_guard.py` | PreToolUse (блокирующий) | Минимальный allow/deny список |
| `hooks/budget_guard.py` | PreToolUse (блокирующий) | Блокирует платные инструменты при превышении бюджета (exit 2) |
| `hooks/cost_tracker.py` | PostToolUse | Добавляет строку стоимости в JSON-вывод; всегда exit 0 |

> **Хуки НЕ активны по умолчанию.** Они поставляются как **inert-шаблон**
> `hooks/settings.example.json` и не загружаются Claude Code, пока ты явно не
> установишь их. Живой `.claude/settings.json` с блокирующим хуком в корне
> репозитория — footgun: мисскоупленный (`"*"`) PreToolUse-хук блокирует
> **каждый** вызов инструмента и может заблокировать саму сессию.

Чтобы включить хуки в **своём** проекте, скопируй шаблон в свой `.claude/settings.json`:

```bash
cp plugins/deep-research-skill/skills/deep-research-skill/hooks/settings.example.json \
   .claude/settings.json
```

Шаблон соблюдает два инварианта безопасности:

1. **Ни один блокирующий хук не на `"*"`.** `budget_guard`/`policy_guard` (PreToolUse, блокирующие) матчат только платные инструменты (`firecrawl|browserbase|serper_api|captcha_solve|generate_video`).
2. **Пути на якоре `$CLAUDE_PROJECT_DIR`** — резолвятся при любом текущем каталоге шелла.

### Проверка без живого Claude Code

```bash
# Просмотр хуков из inert-шаблона:
python -m engine hook --op list

# Тест budget_guard — платный инструмент превышает бюджет (ожидается exit 2):
echo '{"tool":"firecrawl","spent_usd":0.99,"limit_usd":1.00}' | \
  python plugins/deep-research-skill/skills/deep-research-skill/hooks/budget_guard.py

# Cost-отчёт через CLI:
echo '{"total_budget":1.0,"spends":[{"gate":"gate_3_analysis","amount":0.3}]}' | \
  python -m engine cost
```

---

## Разработка и процесс

- **Pre-merge чек-лист:** [`docs/PRE_MERGE_CHECKLIST.md`](docs/PRE_MERGE_CHECKLIST.md) — debt-sweep, сьюты, детерминизм, `/code-review`, version-ritual и стоячие гарды.
- **Журнал багов:** [`docs/BUGLOG.md`](docs/BUGLOG.md) — каждый дефект, его корневая причина и гард, который теперь ловит этот класс (14 багов за v1.3–v1.5 → 5 системных корней).
- **Инварианты:** `AGENT.MD` §10.1 (root-cause table #1–#11) + `docs/TECHDEBT.md`.
- **CI:** `.github/workflows/ci.yml` гоняет engine+bench сьюты, детерминизм-гейт и golden-corpus на каждый push/PR (stdlib-only).

---

## Безопасность и этика

- Все методы обхода следуют scope **ETHICAL_ONLY**
- Работа с CAPTCHA — через human-in-the-loop эскалацию
- Source authority awareness предотвращает распространение дезинформации
- Confidence scoring предотвращает завышение слабых утверждений
- Никакой автоматической эксплуатации — все техники документированы для прозрачности

---

## Обратная связь и вклад

- **Вопросы, баги, идеи:** Telegram [@zagreev](https://t.me/zagreev)
- PR приветствуются: форк → ветка `feature/name` → изменения в стиле проекта → pull request
- История версий — в [CHANGELOG.md](CHANGELOG.md)

---

## Лицензия

MIT License — см. [LICENSE](LICENSE).

---

<p align="center">
  <b>Deep Research Skill v1.5.0</b> · Автор: Andrey Zagreev · <a href="https://t.me/zagreev">@zagreev</a>
</p>
