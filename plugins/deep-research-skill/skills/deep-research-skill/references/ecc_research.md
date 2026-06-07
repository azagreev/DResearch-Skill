# ECC (Evolutionary Collective Control) — Глубокое исследование для Deep Research Skill

## Executive Summary

ECC (Everything Claude Code) — это крупнейшая в мире open-source экосистема для оптимизации performance AI-агентов, созданная Affaan Mustafa. С 209K+ stars и 32K+ forks на GitHub, ECC представляет собой не просто библиотеку, а полноценную **операционную систему для агентной работы** — с 63 специализированными агентами, 251+ skill'ами, 79 командами, hook-автоматизациями и cross-harness архитектурой, поддерживающей Claude Code, Codex, Cursor, OpenCode, Gemini, Zed, GitHub Copilot и другие AI-агентские harness'ы.

Проект эволюционировал за 10+ месяцев интенсивного ежедневного использования в production. ECC v1.10.0 (последний stable) и ECC 2.0 alpha (Rust-based control plane) представляют два поколения архитектуры: plugin-based (v1) и control-plane orchestration (v2).

---

## 1. ECC Architecture

### 1.1 Core Philosophy

ECC построен на пяти фундаментальных принципах (из SOUL.md и AGENTS.md):

| Принцип | Описание |
|---------|----------|
| **Agent-First** | Делегирование специализированным агентам для доменных задач. Работа маршрутизируется к правильному специалисту как можно раньше |
| **Test-Driven** | Тесты пишутся до реализации, 80%+ покрытие обязательно |
| **Security-First** | Валидация всех входов, защита секретов, safe defaults |
| **Immutability** | Предпочтение явных state transitions мутациям. Всегда создавать новые объекты |
| **Plan Before Execute** | Сложные изменения разбиваются на осознанные фазы |

### 1.2 Архитектурные компоненты

```
ECC v1.x Architecture (Plugin-Based)
=====================================
┌─────────────────────────────────────────────┐
│  AI Agent Harness (Claude Code/Cursor/etc)  │
├─────────────────────────────────────────────┤
│  Plugin Layer (.claude-plugin/.cursor/etc)  │
├─────────────────────────────────────────────┤
│  ┌─────────┐ ┌────────┐ ┌───────────────┐  │
│  │  Agents │ │ Skills │ │   Commands    │  │
│  │  (63)   │ │ (251+) │ │    (79)       │  │
│  └─────────┘ └────────┘ └───────────────┘  │
├─────────────────────────────────────────────┤
│  Hooks Layer (event-driven automations)     │
│  - PreToolUse/PostToolUse/Stop hooks        │
│  - SessionStart/SessionEnd lifecycle        │
│  - Memory persistence hooks                 │
├─────────────────────────────────────────────┤
│  Rules Layer (always-follow guidelines)     │
│  - common/ + per-language rules             │
├─────────────────────────────────────────────┤
│  Infrastructure                             │
│  - scripts/ (Node.js utilities)             │
│  - mcp-configs/ (14 MCP servers)            │
│  - hooks/memory-persistence/                │
│  - tests/ (978+ tests)                      │
└─────────────────────────────────────────────┘

ECC v2.0 Architecture (Rust Control Plane)
==========================================
┌─────────────────────────────────────────────┐
│  ecc2/ — Rust-based Control Plane           │
│  ┌─────────┐ ┌─────────┐ ┌───────────────┐ │
│  │   TUI   │ │ Session │ │  Worktree     │ │
│  │Dashboard│ │  Store  │ │   Manager     │ │
│  │ (tui/)  │ │(session)│ │  (worktree/)  │ │
│  └─────────┘ └─────────┘ └───────────────┘ │
│  ┌─────────┐ ┌─────────┐ ┌───────────────┐ │
│  │  Comms  │ │  Config │ │ Observability │ │
│  │(comms/) │ │(config/)│ │(observability)│ │
│  └─────────┘ └─────────┘ └───────────────┘ │
│  Background daemon mode, SQLite sessions    │
│  Risk-scoring primitives, multi-session     │
└─────────────────────────────────────────────┘
```

### 1.3 Ключевые директории и их назначение

| Директория | Назначение |
|-----------|-----------|
| `agents/` | 63 специализированных агента (planner, architect, code-reviewer, security-reviewer, build-error-resolver, и т.д.) |
| `skills/` | 251+ workflow skills и domain knowledge (каноническая workflow surface) |
| `commands/` | 79 slash commands (legacy compatibility surface) |
| `hooks/` | Event-driven automations (PreToolUse, PostToolUse, SessionStart/End, PreCompact) |
| `rules/` | Always-follow guidelines (common + per-language: typescript/, python/, golang/) |
| `scripts/` | Cross-platform Node.js utilities (install-plan.js, catalog.js, consult.js, ecc.js) |
| `mcp-configs/` | 14 MCP server configurations |
| `ecc2/` | Rust-based ECC 2.0 control plane (alpha) |
| `docs/` | Документация, architecture docs, roadmaps |
| `config/` | Конфигурационные файлы |
| `contexts/` | Context templates |
| `manifests/` | Install manifests для selective install |

### 1.4 How Evolutionary Collective Control Works

ECC реализует эволюционный подход через несколько механизмов:

1. **Continuous Learning v2** — Instinct-based learning с confidence scoring, import/export, evolution. Hooks автоматически извлекают паттерны из сессий и превращают их в reusable skills
2. **Hook-Driven Feedback Loops** — PreToolUse/PostToolUse hooks перехватывают каждый tool call, анализируют качество и записывают observations для continuous improvement
3. **Agent Evolution** — Агенты обновляются через PR (#1991, #2024 и др.) с учётом real-world usage
4. **Skill Stocktake** — Периодический аудит skills для удаления устаревших и продвижения эффективных
5. **Cross-Harness Adaptation** — Каждый компонент адаптируется под разные harness'ы через adapter pattern

---

## 2. Agent Orchestration Patterns

### 2.1 Как ECC координирует множество агентов

ECC использует **proactive agent orchestration** — агенты вызываются автоматически без явного запроса пользователя на основе контекста:

```
Complex feature requests → planner
Code just written/modified → code-reviewer
Bug fix or new feature → tdd-guide
Architectural decision → architect
Security-sensitive code → security-reviewer
Autonomous loops / loop monitoring → loop-operator
Harness config reliability and cost → harness-optimizer
```

Ключевые паттерны оркестрации (из skills/autonomous-loops/SKILL.md):

| Паттерн | Сложность | Лучше всего для |
|---------|-----------|---------------|
| **Sequential Pipeline** | Low | Ежедневные dev-шаги, скриптованные workflow |
| **NanoClaw REPL** | Low | Интерактивные persistent сессии |
| **Infinite Agentic Loop** | Medium | Параллельная генерация контента, spec-driven работа |
| **Continuous Claude PR Loop** | Medium | Многодневные итеративные проекты с CI gates |
| **De-Sloppify Pattern** | Add-on | Quality cleanup после любого Implementer шага |
| **Ralphinho / RFC-Driven DAG** | High | Большие фичи, multi-unit параллельная работа с merge queue |

### 2.2 Communication Protocols

ECC использует несколько уровней коммуникации:

1. **Direct Invocation** — Прямой вызов агентов через командный интерфейс harness (Claude Code commands)
2. **Hook-Based Messaging** — Event-driven коммуникация через hooks.json:
   - PreToolUse hooks (blocking и non-blocking)
   - PostToolUse hooks (анализ output)
   - Stop hooks (после каждого response)
   - Session lifecycle hooks
3. **File-Based Coordination** — Агенты координируются через файлы (plan.md, статусы, логи)
4. **Script-Mediated** — Node.js скрипты в scripts/ оркестрируют сложные workflow

### 2.3 Message Passing Mechanisms

Из hooks/hooks.json — ECC реализует sophisticated hook dispatcher:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "node scripts/hooks/pre-bash-dispatcher.js"}],
        "id": "pre:bash:dispatcher"
      },
      {
        "matcher": "Write",
        "hooks": [{"type": "command", "command": "...doc-file-warning.js"}],
        "id": "pre:write:doc-file-warning"
      },
      {
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": "...suggest-compact.js"}],
        "id": "pre:edit-write:suggest-compact"
      },
      {
        "matcher": "*",
        "hooks": [{"type": "command", "command": "...observe-runner.js", "async": true, "timeout": 10}],
        "id": "pre:observe:continuous-learning"
      }
    ]
  }
}
```

### 2.4 Task Distribution Strategies

1. **Role-Based Distribution** — Каждый агент имеет чёткую роль и вызывается при соответствующем типе задачи
2. **Parallel Execution** — Независимые операции запускаются одновременно (launch multiple agents simultaneously)
3. **Hierarchical Delegation** — Complex tasks → planner → разбиение на subtasks → специализированные агенты
4. **Selective Install** — Manifest-driven install pipeline позволяет устанавливать только нужные компоненты
5. **Cross-Harness Routing** — Задачи маршрутизируются к разным harness'ам через adapter layer

---

## 3. Consensus Mechanisms

### 3.1 Как агенты приходят к согласию

ECC не использует явный voting/consensus в традиционном понимании. Вместо этого применяется **layered quality assurance**:

1. **Hook-Based Validation** — PreToolUse hooks блокируют (exit code 2) или предупреждают (stderr) о проблемах до выполнения
2. **Multi-Agent Review Pipeline**:
   - code-reviewer проверяет после написания/изменения кода
   - security-reviewer проверяет перед коммитами
   - build-error-resolver проверяет при падении сборки
3. **TDD Workflow** — Тесты являются формой consensus: implementation считается валидной только если проходит тесты
4. **Quality Gates** — 80%+ coverage, no security vulnerabilities, performance benchmarks

### 3.2 Quality Assurance между агентами

```
Developer Request
    ↓
[planner] → Creates implementation plan
    ↓
[tdd-guide] → Writes tests first (RED)
    ↓
Developer implements
    ↓
[code-reviewer] → Reviews code quality (auto-triggered)
    ↓
[security-reviewer] → Security scan (if sensitive code)
    ↓
[build-error-resolver] → Build verification
    ↓
[e2e-runner] → End-to-end testing (critical flows)
    ↓
Commit with conventional format
```

### 3.3 Conflict Resolution

ECC использует несколько уровней разрешения конфликтов:

1. **Priority-Based** — Security issues имеют highest priority: STOP → security-reviewer → fix CRITICAL → rotate secrets → review codebase
2. **Rule-Based** — rules/ directory содержит always-follow guidelines, которые не могут быть переопределены
3. **Hook Enforcement** — PreToolUse hooks могут блокировать операции, нарушающие политики
4. **GateGuard** — Механизм fact-force restate-retry для предотвращения model repetition traps (issue #2142)

---

## 4. Error Handling & Recovery

### 4.1 Failure отдельного агента

ECC имеет несколько механизмов обработки failures:

1. **Agent Specialization for Errors** — Для каждого типа ошибки есть специализированный агент:
   - `build-error-resolver` — исправляет build/type errors
   - `cpp-build-resolver`, `go-build-resolver`, `kotlin-build-resolver` и т.д. — языкоспецифичные
   - `harness-optimizer` — tuning reliability, cost, throughput

2. **Hook-Based Error Detection** — PreToolUse hooks перехватывают ошибки до их выполнения

3. **Loop Monitoring** — loop-operator агент мониторит autonomous loops на предмет stalls и intervenes

### 4.2 Self-Healing Mechanisms

1. **Continuous Learning** — Hooks auto-extract patterns из failed sessions для предотвращения повторения
2. **Auto-Recovery Sessions** — Session store (SQLite в v2) позволяет resume interrupted workflows
3. **Context Monitor** — Предупреждает о "stuck loops" и context pressure (issue #2120)
4. **Suggest-Compact** — Автоматически предлагает compaction при достижении логических интервалов

### 4.3 Retry Strategies

ECC не использует явный exponential backoff. Вместо этого:

1. **Incremental Fix** — build-error-resolver анализирует errors → фиксит incrementally → verify after each fix
2. **Test-Driven Recovery** — RED → GREEN → REFACTOR цикл
3. **Session Resume** — ECC 2.0 поддерживает session start/stop/resume flows

### 4.4 Circuit Breakers

1. **GateGuard** — Блокирует повторяющиеся паттерны, которые приводят к model repetition traps
2. **PreToolUse Blocking** — Hooks могут вернуть exit code 2 для блокировки операции
3. **Token Optimization** — Рекомендация избегать последних 20% context window для больших refactoring

---

## 5. Scalability Patterns

### 5.1 Масштабирование количества агентов

ECC демонстрирует хорошую горизонтальную масштабируемость:

- **63 агента** в production (по состоянию на v1.10.0)
- **251+ skills** для различных доменов
- **14 MCP server configurations**
- **12+ языковых экосистем**
- **7+ harness'ов** (Claude Code, Codex, Cursor, OpenCode, Gemini, Zed, Copilot)

### 5.2 Performance Characteristics

| Метрика | Значение |
|---------|----------|
| Звёзды | 209K+ |
| Forks | 32.1K+ |
| Contributors | 207+ |
| Commits | 2,003+ |
| Tests | 978+ internal tests |
| Время установки | < 2 минут |
| Языки | JS (61.3%), Rust (29.3%), Python (5.3%), Shell (3%) |

### 5.3 Bottlenecks (из Issues)

1. **Context Window Pressure** — При длинных сессиях context window заполняется, требуется compaction (issues #2155, #2156)
2. **Session tmp files accumulation** — Временные файлы сессий накапливаются (issue #2151)
3. **Hook Performance** — PreToolUse hooks добавляют latency к каждому tool call
4. **Cross-Harness Compatibility** — Разные harness'ы имеют разные hook/plugin surfaces, требующие adaptation
5. **GateGuard Repetition Traps** — В длинных сессиях fact-force restate-retry loop может усиливать repetition (issue #2142)

---

## 6. Comparison with Other Frameworks

### 6.1 ECC vs CrewAI

| Аспект | ECC | CrewAI |
|--------|-----|--------|
| **Модель** | Plugin + Agent Library | Role-based crews |
| **Агенты** | 63 специализированных | Crew with roles |
| **Оркестрация** | Proactive agent invocation + Hooks | Task delegation chains |
| **Cross-Harness** | Да (7+ harness'ов) | Нет (Python-only) |
| **Observability** | Hook-based continuous learning | Enterprise dashboard |
| **Разработка** | 10+ месяцев production use | Open source проект |
| **Community** | 209K stars, 207 contributors | 20K+ stars |
| **Cost predictability** | Hook-based governance capture | Sequential predictable; hierarchical surprises |

### 6.2 ECC vs LangGraph

| Аспект | ECC | LangGraph |
|--------|-----|-----------|
| **Модель** | Plugin + Skills + Hooks | Graph-based state machines |
| **Control** | High (hook-based enforcement) | Maximum (explicit graph) |
| **State** | Session persistence (SQLite in v2) | Checkpointing, time-travel |
| **HITL** | Agent-driven review loops | Native, first-class |
| **Observability** | Continuous learning hooks | LangSmith tracing |
| **Production** | Production-ready (10+ месяцев) | Production-grade |
| **Learning curve** | Moderate | Steepest |

### 6.3 ECC vs AutoGen

| Аспект | ECC | AutoGen |
|--------|-----|---------|
| **Модель** | Specialized agents + Skills | Conversation-based collaboration |
| **Контроль** | High | Medium |
| **Cost** | Predictable (hook governance) | Unpredictable без termination caps |
| **Code execution** | Through agents/tools | Native (Docker sandbox) |
| **Azure integration** | Нет | Native |
| **Async** | Limited | Native async |

### 6.4 ECC vs наш Orchestrator Pattern

| Аспект | ECC | Наш Orchestrator |
|--------|-----|------------------|
| **Purpose** | AI coding assistant optimization | Deep Research multi-agent |
| **Orchestration** | Proactive agent + Hook-driven | Centralized orchestrator |
| **Consensus** | Layered QA (review pipeline) | Предстоит определить |
| **Error recovery** | Specialized error agents + Hooks | Предстоит реализовать |
| **Cross-harness** | Да (7+ harness'ов) | Нет (Claude Desktop focus) |
| **Memory** | Session persistence + Continuous learning | Предстоит реализовать |

### 6.5 Ключевые отличия ECC

1. **Multi-Harness vs Single-Platform** — ECC уникален в поддержке 7+ различных AI agent harness'ов
2. **Hook-Driven Architecture** — Event-driven automations на уровне tool calls — редкий паттерн
3. **Continuous Learning** — Автоматическое извлечение паттернов из сессий в skills
4. **Security-First by Design** — AgentShield интеграция, 1282 теста, 102 правила
5. **Cross-Harness Plugin System** — Единый код работает в Claude Code, Cursor, Codex, и т.д.

---

## 7. Extractable Patterns для Deep Research Skill

### 7.1 Паттерны, которые можно переиспользовать

#### A. Agent Registry Pattern
**Из:** `AGENTS.md`, `agents/*.md`, `docs/COMMAND-AGENT-MAP.md`

ECC использует строгий registry агентов с:
- Чётким определением роли (name, description, purpose, when to use)
- Model specification (planner uses `opus`, code-reviewer uses `sonnet`, etc.)
- Tool permissions (Read, Grep, Glob, etc.)
- Prompt defense baselines

**Адаптация:** Создать `AGENTS.md` с registry research-агентов (searcher, analyzer, synthesizer, fact-checker).

#### B. Hook-Driven Quality Assurance
**Из:** `hooks/hooks.json`, `hooks/README.md`

PreToolUse/PostToolUse hooks обеспечивают:
- Blocking validation (exit code 2)
- Async observation (continuous learning)
- Governance capture (policy violations)
- Timeout management

**Адаптация:** Реализовать hook-like middleware для research operations с validation и logging.

#### C. Skill Catalog Pattern
**Из:** `skills/`, `scripts/catalog.js`, `SKILL.md` format

Каждый skill содержит:
- `SKILL.md` с frontmatter (name, description, origin, when to use)
- Структурированное описание how it works, examples
- Self-contained workflow

**Адаптация:** Структурировать research capabilities как skills с единым SKILL.md форматом.

#### D. Continuous Learning / Memory Persistence
**Из:** `hooks/memory-persistence/`, `skills/continuous-learning-v2-spec.md`

Session lifecycle hooks:
- SessionStart — загрузка контекста
- PreCompact — сохранение state перед compaction
- SessionEnd — финализация и извлечение паттернов

**Адаптация:** Реализовать session persistence для research flows с автоматическим извлечением patterns.

#### E. Multi-Agent Orchestration Trigger Map
**Из:** `AGENTS.md` — Agent Orchestration секция

```
Complex feature requests → planner
Code just written/modified → code-reviewer
Bug fix or new feature → tdd-guide
Architectural decision → architect
Security-sensitive code → security-reviewer
```

**Адаптация:** Создать trigger map для research:
```
Complex research query → planner
Data gathered → analyzer
Facts collected → fact-checker
Synthesis ready → synthesizer
```

#### F. Selective Install Architecture
**Из:** `manifests/`, `scripts/install-plan.js`, `scripts/install-apply.js`

Manifest-driven install pipeline:
- Сканирование доступных компонентов
- Targeted installation по профилям (minimal/core/full)
- State store для отслеживания установленного

**Адаптация:** Модульная загрузка research skills/agents по необходимости.

#### G. Error Resolution Specialization
**Из:** `build-error-resolver.md`, `*-build-resolver.md` pattern

Для каждого типа ошибки — свой specialized агент.

**Адаптация:** Создать specialized error handlers для research failures (source-unavailable, contradictory-data, insufficient-context).

### 7.2 Компоненты для адаптации

| ECC Компонент | Адаптация для Deep Research |
|--------------|---------------------------|
| `agents/planner.md` | Research planner — декомпозиция сложных запросов |
| `agents/code-reviewer.md` | Quality reviewer — проверка качества research output |
| `agents/security-reviewer.md` | Source credibility reviewer — оценка надёжности источников |
| `hooks/hooks.json` | Research pipeline middleware |
| `skills/autonomous-loops/SKILL.md` | Autonomous research loop patterns |
| `scripts/catalog.js` | Research skill discovery |
| `rules/common/` | Research quality guidelines |
| `ecc2/src/session/` | Session management для research flows |
| `ecc2/src/observability/` | Research progress tracking |

### 7.3 Integration Points

```
Deep Research Skill + ECC Patterns
===================================
┌─────────────────────────────────────────────┐
│  Claude Desktop (MCP Host)                  │
├─────────────────────────────────────────────┤
│  Deep Research Skill                        │
│  ┌─────────┐ ┌────────┐ ┌───────────────┐  │
│  │[ECC]    │ │[ECC]   │ │[ECC]          │  │
│  │ Agent   │ │ Skill  │ │ Hook-inspired │  │
│  │Registry │ │Catalog │ │   Middleware  │  │
│  │Pattern  │ │Pattern │ │    Pattern    │  │
│  └─────────┘ └────────┘ └───────────────┘  │
│  ┌─────────┐ ┌────────┐ ┌───────────────┐  │
│  │[ECC]    │ │[ECC]   │ │[ECC]          │  │
│  │ Session │ │Selective│ │ Continuous   │  │
│  │ Persistence│ Install│ │ Learning     │  │
│  │Pattern  │ │Pattern │ │   Pattern    │  │
│  └─────────┘ └────────┘ └───────────────┘  │
├─────────────────────────────────────────────┤
│  MCP Tools (Search, Browser, etc.)          │
└─────────────────────────────────────────────┘
```

### 7.4 Конкретные рекомендации по внедрению

1. **Создать Agent Registry** — Определить 5-10 research-специализированных агентов с чёткими ролями и trigger conditions
2. **Реализовать Quality Pipeline** — Pre-check → Research → Analysis → Synthesis → Review (inspired by ECC code review pipeline)
3. **Session Persistence** — SQLite-based session store для сохранения research state
4. **Skill-Based Architecture** — Разделить research capabilities на skills с SKILL.md форматом
5. **Error Specialization** — Создать dedicated error recovery agents для типичных research failures
6. **Continuous Improvement** — Логирование research sessions и автоматическое извлечение effective patterns

---

## 8. Выводы и рекомендации

### 8.1 Ключевые находки

1. **ECC — это не framework, а операционная система** для агентной работы. Она включает agents, skills, hooks, rules, scripts, и cross-harness adaptation — всё для production-ready AI coding.

2. **Hook-driven architecture** — ключевой инновационный паттерн ECC. Event-driven automations на уровне tool calls обеспечивают continuous learning, quality enforcement, и governance capture.

3. **Proactive agent orchestration** — агенты вызываются автоматически на основе контекста, без явного запроса. Это обеспечивает high-quality output через layered review.

4. **Cross-harness portability** — ECC работает в Claude Code, Cursor, Codex, OpenCode, Gemini, Zed, и Copilot через adapter layer. Это уникальное преимущество.

5. **Security-first design** — AgentShield integration, 1282 теста, prompt defense baselines, governance capture hooks.

### 8.2 Применимость к Deep Research Skill

| Область | Применимость | Приоритет |
|---------|-------------|-----------|
| Agent Registry Pattern | Высокая | P0 |
| Hook-inspired Middleware | Высокая | P0 |
| Session Persistence | Высокая | P1 |
| Skill Catalog Pattern | Высокая | P1 |
| Error Specialization | Высокая | P1 |
| Continuous Learning | Средняя | P2 |
| Cross-Harness Adaptation | Низкая (Claude Desktop focus) | P3 |
| Selective Install | Средняя | P2 |

### 8.3 Следующие шаги

1. Создать Agent Registry для Deep Research (planner, searcher, analyzer, synthesizer, fact-checker, quality-reviewer)
2. Реализовать quality pipeline inspired by ECC review flow
3. Добавить session persistence для research workflows
4. Создать skill catalog для research capabilities
5. Реализовать error recovery specialization

---

*Исследование проведено на основе ECC v1.10.0 и ECC 2.0 alpha (Rust). Репозиторий: https://github.com/affaan-m/ECC*
*Дата исследования: Июнь 2026*
