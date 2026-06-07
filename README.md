# 🔍 Deep Research Skill

> **Production-ready навык глубокого исследования для Claude Code.** Многофазный workflow с cost-first выполнением, evidence-based отчётами, anti-hallucination протоколом и прозрачным confidence scoring.

**Версия:** 0.1.0 | **Лицензия:** MIT | **Язык:** русский
**Автор:** Andrey Zagreev | **Обратная связь:** [@zagreev](https://t.me/zagreev)

---

## Возможности

- **6-фазный workflow**: Анализ задачи → Декомпозиция → Сбор → Фактчекинг → Синтез → Вывод
- **Cost-First выполнение**: 4-уровневая иерархия инструментов — начинай бесплатно, эскалируй только при необходимости
- **Evidence-Based отчёты**: каждое утверждение имеет citation, каждый источник — tier
- **Anti-Hallucination протокол**: zero tolerance — FactCheck Agent ветирует каждый факт
- **4 уровня глубины**: Quick (30 мин) → Standard (1–2 ч) → Deep (3–5 ч) → Exhaustive (5+ ч)
- **Confidence Scoring**: шкала 1–5 с визуальными индикаторами для каждого утверждения
- **Checkpoint Recovery**: адаптивный heartbeat (2–10 мин) + checkpoint на каждом gate — откат к последнему gate, а не к нулю
- **50+ инструментов**: полная матрица с рейтингами cost/quality/authority

---

## Выбор платформы

| Платформа | Для кого | Установка | Файл |
|-----------|----------|-----------|------|
| **Claude Code / Cowork** | 🌟 Рекомендуется — установка в 1 клик, без файлов | Plugin marketplace (GitHub) | плагин |
| **Claude.ai** | Опытные пользователи, нужна загрузка скилла | Загрузка ZIP/`.skill` | папка скилла |

---

## Быстрый старт

### Claude Code / Cowork — плагин-маркетплейс 🌟 (рекомендуется, без файлов)

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

#### 🔄 Обновление плагина

Сторонние маркетплейсы (как этот) **не авто-обновляются по умолчанию** — авто-pull на старте сессии включён только для официального маркетплейса Anthropic. После нового релиза кнопка Update может оставаться неактивной, пока обновление не подтянуть.

**✅ Рекомендуется — включить auto-update один раз** (дальше плагин обновляется сам на старте сессии):
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
SKILL.md (точка входа)
  ├── Phase 0: Анализ задачи     → references/strategy_guide.md
  ├── Phase 1: Декомпозиция      → references/decomposition_guide.md
  ├── Phase 2: Сбор              → references/tool_matrix.md, references/cost_matrix_full.md
  ├── Phase 3: Фактчекинг        → references/factcheck_system.md
  ├── Phase 4: Синтез            → references/output_formats.md
  ├── Phase 5: Вывод             → references/output_formats.md
  └── Phase 6: Приёмка           → references/acceptance_framework.md

AGENT.MD (слой оркестрации)
  ├── Heartbeat Protocol (адаптивный интервал, §1.2)
  ├── Checkpoint Recovery
  ├── Quality Gates
  └── Cost Tracking

references/ (20 документов):
  ├── Core: tool_matrix, strategy_guide, decomposition_guide, acceptance_framework
  ├── Output: output_formats, factcheck_system, source_authority_framework, cost_matrix_full
  ├── Analysis: competitive_landscape
  ├── Infra: HOOK_MIDDLEWARE, PLATFORM_DISTRIBUTION
  └── Research: jina_reader, bypass_paywall, ecc, modelsdev, captcha,
                 academic_skills, skill_marketplace, browserbase, prompt_master
```

---

## Структура репозитория

```
DResearch-Skill/                              # маркетплейс (корень репозитория)
├── .claude-plugin/
│   └── marketplace.json                      # манифест маркетплейса (name, owner, plugins[])
├── plugins/
│   └── deep-research-skill/
│       ├── .claude-plugin/
│       │   └── plugin.json                   # манифест плагина
│       └── skills/
│           └── deep-research-skill/          # self-contained навык
│               ├── SKILL.md                  # точка входа навыка
│               ├── SKILL.master.md           # полная мастер-документация
│               ├── AGENT.MD                  # протокол оркестрации (heartbeat/checkpoint)
│               ├── LEGAL_METHODS.md          # этичные легальные методы доступа
│               ├── CAPTCHA_MODULE.md         # стратегии работы с CAPTCHA
│               └── references/               # 20 reference-документов
│                   ├── tool_matrix.md
│                   ├── strategy_guide.md
│                   ├── decomposition_guide.md
│                   ├── acceptance_framework.md
│                   ├── output_formats.md
│                   ├── factcheck_system.md
│                   ├── source_authority_framework.md
│                   ├── cost_matrix_full.md
│                   ├── competitive_landscape.md
│                   ├── HOOK_MIDDLEWARE.md
│                   ├── PLATFORM_DISTRIBUTION.md
│                   ├── jina_reader_research.md
│                   ├── bypass_paywall_research.md
│                   ├── ecc_research.md
│                   ├── modelsdev_research.md
│                   ├── captcha_research.md
│                   ├── academic_skills_research.md
│                   ├── skill_marketplace_research.md
│                   ├── browserbase_research.md
│                   └── prompt_master_research.md
├── docs/                                     # документация репозитория
│   ├── installation.md
│   └── usage.md
├── CHANGELOG.md
├── LICENSE                                   # MIT
└── README.md                                 # этот файл
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
  <b>Deep Research Skill v0.1.0</b> · Автор: Andrey Zagreev · <a href="https://t.me/zagreev">@zagreev</a>
</p>
