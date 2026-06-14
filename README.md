# Deep Research Skill

> **Навык глубокого исследования для Claude Code (testing release).** Многофазный workflow с cost-first выполнением, evidence-based отчётами, anti-hallucination протоколом и прозрачным confidence scoring.

**Версия:** 1.2.0 | **Лицензия:** MIT | **Язык:** русский
**Автор:** Andrey Zagreev | **Обратная связь:** [@zagreev](https://t.me/zagreev)

---

## Возможности

- **7-фазный workflow**: Анализ задачи → Декомпозиция → Сбор → Верификация → Синтез → Вывод → Приёмка
- **Cost-First выполнение**: 4-уровневая иерархия инструментов — начинай бесплатно, эскалируй только при необходимости
- **Evidence-Based отчёты**: каждое утверждение имеет citation, каждый источник — tier
- **Anti-Hallucination протокол**: zero tolerance — FactCheck Agent ветирует каждый факт
- **4 уровня глубины**: Quick (30 мин) → Standard (1–2 ч) → Deep (3–5 ч) → Exhaustive (5+ ч)
- **Confidence Scoring**: шкала 1–5 с визуальными индикаторами для каждого утверждения
- **Checkpoint Recovery**: адаптивный heartbeat (2–10 мин) + checkpoint на каждом gate — откат к последнему gate, а не к нулю
- **Cost & Cache телеметрия**: захват cache-сигналов, `cache_hit_rate`, `bundle_hash`, именованные границы компактизации, CLI `cost`
- **Typed Collection Seam**: единый контракт `CollectionResult` над любым провайдером (web_search/Jina/Firecrawl/…) со snippet-cap и risk_class
- **CI-регрессия**: 247 юнит-тестов, golden corpus, opional cost/latency-пороги

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

### Claude.ai (ZIP-скилл)

Навык self-contained, поэтому его можно загрузить и в Claude.ai как обычный скилл:

1. Заархивируй папку скилла `plugins/deep-research-skill/skills/deep-research-skill/` в ZIP (в корне архива должны лежать `SKILL.md` и `references/`).
2. Claude → Настройки → Возможности → включи «Code execution and file creation».
3. Настроить → Скиллы → **+** → загрузи ZIP.
4. В любом чате попроси «проведи исследование …» — навык активируется.

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
│       │   └── plugin.json                   # манифест плагина (version: 1.2.0)
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
cluster      — кластеризация
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
  <b>Deep Research Skill v1.2.0</b> · Автор: Andrey Zagreev · <a href="https://t.me/zagreev">@zagreev</a>
</p>
