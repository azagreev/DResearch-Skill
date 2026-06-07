# Исследование: Паттерны распределения задач между LLM в models.dev / OpenCode

> **Дата исследования:** 2026-06-07
> **Источник:** https://github.com/anomalyco/models.dev + дополнительные материалы
> **Цель:** Изучить архитектуру models.dev и паттерны routing'а LLM в OpenCode для применения в Deep Research Skill

---

## 1. Executive Summary: Главное открытие

**Критически важное понимание:** `models.dev` — это **НЕ** система routing'а задач между LLM в традиционном смысле. Это **open-source catalog/база данных AI-моделей** с rich metadata. Однако он является **фундаментом** для routing-системы, реализованной в **OpenCode** (AI coding agent от той же компании AnomalyCo).

**OpenCode** использует `models.dev` как единый источник truth о 2400+ моделях от 75+ провайдеров и реализует поверх него изощренные паттерны routing'а:
- `small_model` pattern для lightweight задач
- Agent-based per-model routing
- `fallback_models` chains
- Tiered routing по сложности задач
- Rate-limit-aware dynamic routing

---

## 2. Models.dev Architecture

### 2.1 Core Philosophy

models.dev строится на принципах:

1. **Single Source of Truth** — единая структурированная база данных о всех AI-моделях
2. **Community-Driven** — открытые PR для добавления новых моделей/провайдеров
3. **Structured Metadata** — каждая модель описывается через TOML с полными характеристиками
4. **Programmable API** — сгенерированные JSON API + TypeScript types + npm package
5. **Provider Abstraction** — унифицированный интерфейс для любого провайдера

### 2.2 Архитектурные Компоненты

```
models.dev/
├── providers/                    # Провайдеры (75+)
│   ├── anthropic/
│   │   ├── provider.toml         # Конфиг провайдера
│   │   └── models/               # Модели провайдера
│   │       ├── claude-sonnet-4-6.toml
│   │       ├── claude-opus-4-7.toml
│   │       └── ...
│   ├── openai/
│   ├── google/
│   └── ...
├── models/                       # Альтернативная организация по моделям
├── labs/                         # Лаборатории/разработчики моделей
├── packages/
│   ├── core/                     # Core библиотека
│   │   ├── src/
│   │   │   ├── schema.ts         # Zod схемы валидации
│   │   │   ├── model.ts          # Model type definitions
│   │   │   ├── family.ts         # Model family logic
│   │   │   ├── provider.ts       # Provider type definitions
│   │   │   ├── generate.ts       # Code generation
│   │   │   └── index.ts          # Exports
│   │   └── script/
│   │       ├── validate.ts       # Валидация TOML файлов
│   │       └── sync-models.ts    # Синхронизация моделей
│   ├── function/                 # Cloudflare Worker
│   │   └── src/worker.ts         # API endpoint handler
│   └── web/                      # Web UI (浏览, поиск)
├── .opencode/                    # Конфигурация для OpenCode
└── AGENTS.md                     # Инструкции для AI-агентов
```

### 2.3 Data Model

#### Model TOML Schema (критически важно для routing)

Каждая модель описывается структурированным TOML:

```toml
id = "claude-sonnet-4-6"
name = "Claude Sonnet 4.6"
family = "claude-sonnet"

[capabilities]
attachment = true          # Поддержка файлов
reasoning = true           # Reasoning capabilities
tool_call = true           # Function calling
structured_output = true   # JSON output

[limits]
context = 1_000_000        # Context window size
output = 128_000           # Max output tokens

[cost]
input = 2.5                # $ per 1M input tokens
output = 15.0              # $ per 1M output tokens
cache_read = 0.25          # Cache read cost
cache_write = 0.0          # Cache write cost

# Tiered pricing (критически важно для cost routing!)
[[cost.tiers]]
input = 5.0
output = 22.5
cache_read = 0.25
tier = { type = "context", size = 272_000 }

[cost.context_over_200k]   # Special pricing for >200k context
input = 5.0
output = 22.5
```

#### Provider TOML Schema

```toml
id = "anthropic"
name = "Anthropic"
env = ["ANTHROPIC_API_KEY"]           # Required env vars
npm = "@ai-sdk/anthropic"             # SDK package
api = "https://api.anthropic.com/v1"  # Base URL
doc = "https://docs.anthropic.com"
```

#### Key Metadata Fields для Routing Decisions

| Field | Значение для Routing |
|-------|---------------------|
| `family` | Группировка моделей по семейству (claude-sonnet, gpt-pro, и т.д.) |
| `cost.input/output` | Cost-per-token для бюджетирования |
| `cost.tiers` | Tiered pricing для больших контекстов |
| `cost.cache_read/write` | Cache pricing для оптимизации |
| `capabilities.reasoning` | Reasoning capability — нужен ли для задачи |
| `capabilities.tool_call` | Function calling support |
| `capabilities.structured_output` | JSON mode для programmatic output |
| `limits.context` | Max context window — критично для large tasks |
| `limits.output` | Max output length |
| `modalities` | Input/output modalities (text, image, video, audio) |
| `open_weights` | Open-source vs proprietary |

### 2.4 Generated Outputs

models.dev генерирует несколько артефактов:

1. **`api.json`** — полный API со всеми провайдерами и моделями (~3MB JSON)
2. **`models.json`** — упрощенный список моделей
3. **`catalog.json`** — каталог для веб-UI
4. **`model-schema.json`** — JSON Schema для валидации model IDs
5. **TypeScript types** — через `packages/core/src`
6. **npm package** `@models.dev/core`

---

## 3. Model Routing Patterns в OpenCode

OpenCode — это основной consumer models.dev. Routing реализован на уровне приложения (OpenCode), а не в самом models.dev.

### 3.1 Pattern 1: Small Model Routing

**Суть:** Использовать дешёвую/быструю модель для lightweight задач, expensive модель — для основной работы.

**Конфигурация:**
```json
{
  "model": "anthropic/claude-sonnet-4-6",
  "small_model": "anthropic/claude-haiku-4-5"
}
```

**Как работает:**
1. Если `small_model` явно задан — используется он
2. Иначе `Provider.getSmallModel(providerID)` выбирает small-модель из того же провайдера:
   - Приоритет: `claude-haiku-4-5` → `gemini-3-flash` → `gpt-5-nano`
3. Если small-модель не найдена — fallback к основной модели

**Используется для:**
- Генерации заголовков чатов
- Сессионная суммаризация
- Лёгкие utility задачи

### 3.2 Pattern 2: Agent-Based Model Routing

**Суть:** Каждый агент имеет свою dedicated модель, подобранную под его задачи.

**Пример конфигурации (Oh My Open Agent):**
```json
{
  "agents": {
    "sisyphus": {
      "model": "opencode-go/kimi-k2.6",
      "fallback_models": [
        "opencode-go/deepseek-v4-pro",
        "opencode-go/qwen3.6-plus"
      ]
    },
    "librarian": {
      "model": "opencode-go/deepseek-v4-flash",
      "fallback_models": "opencode-go/qwen3.5-plus"
    },
    "oracle": {
      "model": "opencode-go/glm-5.1",
      "fallback_models": ["opencode-go/kimi-k2.6", "opencode-go/deepseek-v4-pro"]
    }
  }
}
```

**Агенты и их модели:**

| Агент | Роль | Модель Tier | Почему |
|-------|------|-------------|--------|
| Sisyphus | Main orchestrator | Elite (Kimi K2.6) | Лучший agentic coder |
| Hephaestus | Deep worker | Standard (DeepSeek V4 Pro) | Принципиальный, GPT-like |
| Oracle | Architecture consultant | Elite (GLM-5.1) | Лучший reasoning |
| Librarian | Search agent | Volume (DeepSeek V4 Flash) | 31K req/5hr, never rate-limited |
| Explore | Code exploration | Volume (DeepSeek V4 Flash) | Speed модель |
| Prometheus | Planner | Elite (GLM-5.1) | Spec-writing, architectural planning |
| Metis/Momus | Review | Standard (Qwen3.6 Plus) | Аналитические задачи |

### 3.3 Pattern 3: Tiered Routing by Task Complexity

**Суть:** Маршрутизация на основе уровня сложности задачи.

**Тировая архитектура:**

```
Tier 1: Volume Workhorse (никогда не упираемся в лимиты)
├── Models: DeepSeek V4 Flash, Qwen3.5 Plus, MiniMax M2.5
├── Cost: ~$0.14-0.30/1M input
├── Rate limit: 31,650 req/5hr
└── Use for: Code completion, simple bug fixes, code review, search, quick tasks

Tier 2: Standard Engineering (баланс)
├── Models: DeepSeek V4 Pro, Qwen3.6 Plus, MiniMax M2.7
├── Cost: ~$0.30-1.0/1M input
├── Rate limit: 3,300-3,450 req/5hr
└── Use for: Feature implementation, terminal automation, multi-step debugging

Tier 3: Complex Agentic (elite)
├── Models: Kimi K2.6, GLM-5.1, MiMo-V2.5-Pro
├── Cost: ~$0.60-2.5/1M input
├── Rate limit: 880-1,290 req/5hr
└── Use for: Multi-file refactoring, long-horizon runs, architecture decisions

Tier 4: Specialized Capabilities
├── Models: MiMo-V2-Omni (multimodal), GLM-5.1 (long-horizon)
└── Use for: Screenshot-to-code, 8-hour autonomous runs, spec-writing
```

**Rule of thumb:** Если задача требует >100 запросов — начинать с Tier 1. Эскалировать наверх только при необходимости.

### 3.4 Pattern 4: Fallback Model Chains

**Суть:** Определение цепочек fallback моделей для отказоустойчивости.

**Конфигурация:**
```json
{
  "model_fallback": true,
  "runtime_fallback": {
    "enabled": true,
    "retry_on_errors": [400, 429, 503, 529],
    "max_fallback_attempts": 3,
    "cooldown_seconds": 60,
    "timeout_seconds": 30,
    "notify_on_fallback": true
  }
}
```

**Механизм:**
1. При ошибке из `retry_on_errors` — переключение на fallback модель
2. Глобальный cooldown для rate-limited провайдеров
3. Чёрный список провайдеров до истечения cooldown
4. Максимум 3 fallback попытки

**Пример fallback chain:**
```
Sisyphus: kimi-k2.6 → deepseek-v4-pro → qwen3.6-plus
Librarian: deepseek-v4-flash → qwen3.5-plus
Oracle: glm-5.1 → kimi-k2.6 → deepseek-v4-pro
```

### 3.5 Pattern 5: Rate-Limit-Aware Dynamic Routing

**Суть:** Динамическое переключение моделей на основе текущего состояния rate limits.

**Механизм:**
1. Отслеживание использования rate limits per provider/model
2. Прогнозирование исчерпания лимита
3. Проактивное переключение на fallback ДО исчерпания
4. Cooldown-based provider blacklisting

**Rate Limit Budgeting (OpenCode Go):**
- 5-часовое окно: $12 usage
- Weekly: $30
- Monthly: $60

**Concurrency Control:**
```json
{
  "background_task": {
    "modelConcurrency": {
      "opencode-go/kimi-k2.6": 2,
      "opencode-go/deepseek-v4-pro": 3,
      "opencode-go/deepseek-v4-flash": 20,
      "opencode-go/glm-5.1": 1,
      "opencode-go/qwen3.6-plus": 5
    }
  }
}
```

### 3.6 Pattern 6: Task-Category-Based Routing

**Суть:** Routing на основе категории задачи.

```json
{
  "categories": {
    "deep": { "model": "kimi-k2.6", "fallback": "deepseek-v4-pro" },
    "quick": { "model": "deepseek-v4-flash" },
    "unspecified-low": { "model": "deepseek-v4-flash" },
    "unspecified-high": { "model": "deepseek-v4-pro", "fallback": "kimi-k2.6" },
    "writing": { "model": "qwen3.6-plus" },
    "visual-engineering": { "model": "mimo-v2-omni", "fallback": "qwen3.6-plus" }
  }
}
```

---

## 4. Cost Optimization Patterns

### 4.1 Cost Tracking и Budgeting

**В models.dev:**
- Структурированные cost данные для каждой модели
- Input/output/cache pricing
- Tiered pricing для разных размеров контекста

**В OpenCode:**
- Dollar-based budgeting (не token-based)
- Per-session cost estimation
- Per-agent cost allocation
- Historical cost tracking

### 4.2 Model Selection Based on Cost

**Cost Tiers (примерные данные):**

| Model | Input Cost | Output Cost | Context | SWE-Pro |
|-------|-----------|------------|---------|---------|
| Claude Opus 4.7 | $5.00 | $25.00 | 1M | 64.3% |
| GPT-5.4 Pro | $30.00 | $180.00 | 922K | — |
| Kimi K2.6 | $0.95 | $4.00 | 262K | 58.6% |
| DeepSeek V4 Pro | $0.435 | $0.87 | 1M | 55.4% |
| GLM-5.1 | $0.60 | $2.60 | 204K | 58.4% |
| Qwen3.6 Plus | $0.45 | $2.70 | 1M | — |
| DeepSeek V4 Flash | $0.14 | $0.28 | 1M | — |
| Claude Haiku 4.5 | $1.00 | $5.00 | 200K | — |
| GPT-5 Nano | $0.05 | $0.40 | 400K | — |

### 4.3 Fallback to Cheaper Models

**Механизм:**
1. Primary: expensive high-quality model
2. Fallback 1: medium-cost model
3. Fallback 2: cheap volume model
4. Final fallback: пользовательская локальная модель

**Пример:**
```
Architecture planning:
  Primary: GLM-5.1 ($0.60/$2.60)
  Fallback: DeepSeek V4 Pro ($0.435/$0.87)
  
Code implementation:
  Primary: DeepSeek V4 Pro ($0.435/$0.87)
  Fallback: DeepSeek V4 Flash ($0.14/$0.28)
```

### 4.4 Small Model Optimization

**Ключевой insight:** ~30-40% запросов в coding agent — это lightweight задачи (title generation, summarization, simple queries). Использование small model для них даёт **10-20x экономию**.

---

## 5. Quality vs Cost Trade-off

### 5.1 Quality Metrics per Model

**OpenCode использует benchmarks для model selection:**

| Benchmark | Что измеряет | Топ модели |
|-----------|-------------|-----------|
| SWE-Bench Pro | Real-world bug fixing | Opus 4.7 (64.3%), Kimi K2.6 (58.6%), GLM-5.1 (58.4%) |
| SWE-Bench Verified | Bug fixing (verified) | V4 Pro (80.6%), Opus 4.7 (87.6%) |
| LiveCodeBench | Competitive programming | V4 Pro (93.5%) |
| Terminal-Bench | Agentic terminal work | Qwen3.6 Plus (61.6%), Claude 4.5 (59.3%) |

### 5.2 Adaptive Quality Thresholds

**OpenCode Go Positioning:**
- **~80-90% frontier quality** при **~10-20x lower cost**
- 80% coding tasks — разница невидима
- 20% complex tasks — нужно 1-2 extra итерации

### 5.3 Graceful Degradation

**Механизм:**
1. Попытка с elite моделью
2. При rate limit/error — fallback к standard
3. При повторном rate limit — fallback к volume
4. При budget constraint — использовать volume tier

---

## 6. Fallback Mechanisms

### 6.1 Retry Strategies

```json
{
  "runtime_fallback": {
    "retry_on_errors": [400, 429, 503, 529],
    "max_fallback_attempts": 3,
    "cooldown_seconds": 60,
    "timeout_seconds": 30
  }
}
```

### 6.2 Model Fallback Chain

**Пример:**
```
Primary: opencode-go/kimi-k2.6
  → Error 429 (rate limit)
  → Fallback 1: opencode-go/deepseek-v4-pro
    → Error 503 (service unavailable)
    → Fallback 2: opencode-go/qwen3.6-plus
      → Error 529 (overloaded)
      → Fallback 3: opencode-go/deepseek-v4-flash
        → Success!
```

### 6.3 Provider Health Monitoring

**Механизм:**
1. Каждый failed request логируется
2. При ошибке из списка — провайдер добавляется в blacklist
3. Cooldown timer запускается
4. Все новые сессии пропускают blacklisted провайдеров
5. После cooldown — провайдер возвращается в rotation

### 6.4 Error Recovery

**Уровни recovery:**
1. **Request-level** — retry with same model (3 attempts)
2. **Model-level** — switch to fallback model
3. **Provider-level** — switch to different provider
4. **Tier-level** — downgrade to cheaper tier

---

## 7. Provider Management

### 7.1 Provider.toml Structure

```toml
id = "anthropic"
name = "Anthropic"
env = ["ANTHROPIC_API_KEY"]
npm = "@ai-sdk/anthropic"
api = "https://api.anthropic.com/v1"
doc = "https://docs.anthropic.com"
```

### 7.2 API Key Management

**Через environment variables:**
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- И т.д. (автоопределение из env)

### 7.3 Rate Limit Handling

**OpenCode механизмы:**
- `enabled_providers` whitelist
- `modelConcurrency` per model
- `providerConcurrency` per provider
- Cooldown-based blacklisting
- Dollar-based rate limiting

### 7.4 Provider Health Monitoring

**Индикаторы health:**
- Error rate per provider
- Response latency
- Rate limit exhaustion rate
- Cost per successful request

---

## 8. Benchmarking Methodology

### 8.1 Performance Benchmarks

**OpenCode использует:**
- SWE-Bench (Pro, Verified) — software engineering
- LiveCodeBench — competitive programming
- Terminal-Bench — agentic terminal usage
- Aider Polyglot — multilingual coding
- HumanEval — function completion

### 8.2 Cost Benchmarks

**Метрики:**
- Cost per request (средний)
- Cost per task (полный цикл)
- Requests per dollar
- Effective cost с учётом retries

### 8.3 Model Evaluation Methodology

**Подход:**
1. Запуск стандартизированных benchmark'ов
2. Сравнение по нескольким осям (quality, speed, cost, reliability)
3. Регулярное обновление scores
4. Community-driven evaluation

---

## 9. Паттерны для Deep Research Skill

### 9.1 Адаптивная маршрутизация research subtasks

```typescript
// Концепт: Research Task Router
interface ResearchTask {
  type: 'deep_research' | 'fact_check' | 'summarize' | 'synthesize' | 'generate_query';
  complexity: 'low' | 'medium' | 'high' | 'frontier';
  expected_tokens: number;
  requires_reasoning: boolean;
  requires_vision: boolean;
  time_budget_ms: number;
}

// Routing logic
function routeResearchTask(task: ResearchTask): ModelSelection {
  if (task.complexity === 'low') {
    return { model: 'deepseek-v4-flash', tier: 1 };
  }
  if (task.complexity === 'medium' && !task.requires_reasoning) {
    return { model: 'qwen3.6-plus', tier: 2 };
  }
  if (task.complexity === 'high' || task.requires_reasoning) {
    return { model: 'kimi-k2.6', tier: 3 };
  }
  return { model: 'claude-opus-4-7', tier: 4 };
}
```

### 9.2 Cost Budgeting per Research Session

```typescript
interface ResearchSessionBudget {
  total_dollar_budget: number;
  allocation: {
    planning: number;      // 10% — cheap model
    search_queries: number; // 20% — cheap model
    deep_analysis: number;  // 50% — elite model
    synthesis: number;     // 15% — medium model
    contingency: number;   // 5% — reserve
  };
  spent: number;
  current_tier: number;
}
```

### 9.3 Integration Architecture

```
Deep Research Skill
├── Task Decomposer          # Разбивает research на subtasks
│   └── Model: cheap/fast (GPT-4o-mini, Haiku)
├── Subtask Router           # Маршрутизирует на основе metadata
│   ├── Web Search           → Fast model (Flash, V4 Flash)
│   ├── Deep Analysis        → Elite model (K2.6, GLM-5.1)
│   ├── Fact Checking        → Medium model (V4 Pro)
│   ├── Synthesis            → Medium model (Qwen3.6)
│   └── Report Generation    → Best available (Opus 4.7)
├── Fallback Manager         # Управляет fallback chains
├── Cost Monitor             # Отслеживает бюджет
└── Quality Evaluator        # Оценивает quality vs cost trade-off
```

### 9.4 Concrete Patterns для Implementation

**Pattern A: Tiered Research Pipeline**
```
Stage 1 (Discovery):    Cheap model → generates search queries
Stage 2 (Collection):   Volume model → executes searches, extracts info
Stage 3 (Analysis):     Elite model → deep analysis of findings
Stage 4 (Synthesis):    Medium model → synthesizes results
Stage 5 (Review):       Elite model → quality review
```

**Pattern B: Adaptive Quality Escalation**
```
1. Начать с cheap model
2. Evaluate output quality (self-evaluation)
3. Если quality < threshold → escalate to better model
4. Повторять до достижения threshold или исчерпания budget
```

**Pattern C: Parallel Model Execution**
```
1. Запустить задачу на 2-3 моделях разных tiers параллельно
2. Использовать fastest result для UX
3. Compare quality, использовать best result
4. Learn optimal model для данного типа задач
```

### 9.5 Metadata-Driven Model Selection

**Использование models.dev metadata:**

```typescript
function selectModel(requirements: TaskRequirements): string {
  // Filter by capabilities
  const candidates = models.filter(m => 
    m.capabilities.tool_call === requirements.needsTools &&
    m.capabilities.reasoning === requirements.needsReasoning &&
    m.limits.context >= requirements.minContext &&
    m.modalities.input.includes(requirements.inputType)
  );
  
  // Sort by cost within quality tier
  candidates.sort((a, b) => {
    const qualityDiff = b.benchmarks.swe_pro - a.benchmarks.swe_pro;
    if (Math.abs(qualityDiff) > 5) return qualityDiff; // Quality first
    return a.cost.input - b.cost.input; // Then cost
  });
  
  // Return best value
  return candidates[0]?.id;
}
```

---

## 10. Технические детали

### 10.1 API Endpoints (models.dev)

| Endpoint | Описание |
|----------|----------|
| `https://models.dev/api.json` | Полный API со всеми провайдерами и моделями |
| `https://models.dev/models.json` | Упрощенный список моделей |
| `https://models.dev/catalog.json` | Каталог для UI |
| `https://models.dev/model-schema.json` | JSON Schema для валидации |

### 10.2 NPM Package

```bash
npm install @models.dev/core
```

```typescript
import { models, providers } from '@models.dev/core';

// Получить все модели с ценами
const cheapModels = models.filter(m => m.cost.input < 1.0);

// Получить модели с reasoning
const reasoningModels = models.filter(m => m.capabilities.reasoning);
```

### 10.3 Cloudflare Worker Implementation

Worker обрабатывает:
1. **Analytics** — tracking hits от opencode/bun агентов через PostHog и Datalake
2. **Schema Generation** — динамическая генерация `model-schema.json` из актуальных данных
3. **Static Assets** — раздача сгенерированных JSON файлов
4. **Logo Fallback** — fallback на default logo при отсутствии провайдерного

---

## 11. Ключевые выводы

### 11.1 Что models.dev делает хорошо
1. **Стандартизация** — единый формат для 2400+ моделей
2. **Rich Metadata** — cost, capabilities, limits в структурированном виде
3. **Programmable** — JSON API + TypeScript + npm
4. **Community** — открытый вклад через PR
5. **Freshness** — регулярные обновления

### 11.2 Чего не хватает в models.dev (для routing)
1. **Benchmark scores** — нет встроенных performance benchmarks
2. **Latency data** — нет информации о скорости ответа
3. **Reliability metrics** — нет uptime/reliability данных
4. **Dynamic routing logic** — models.dev это data source, не router

### 11.3 Что OpenCode добавляет сверху
1. **Small Model Pattern** — intelligent lightweight task routing
2. **Agent-Based Routing** — per-agent model selection
3. **Fallback Chains** — resilient multi-level fallbacks
4. **Rate Limit Awareness** — dynamic load balancing
5. **Cost Budgeting** — per-session dollar budgets
6. **Tiered Architecture** — complexity-based routing

### 11.4 Рекомендации для Deep Research Skill

1. **Использовать models.dev как data source** для model metadata
2. **Реализовать Small Model Pattern** для lightweight задач (summarization, query generation)
3. **Создать Tiered Router** — разные tiers для разных типов research subtasks
4. **Настроить Fallback Chains** — минимум 2 fallback модели на каждую задачу
5. **Внедрить Cost Budgeting** — per-session budget с аллокацией по stages
6. **Добавить Rate Limit Tracking** — proactive switching до исчерпания
7. **Реализовать Adaptive Escalation** — начинать cheap, эскалировать при необходимости
8. **Использовать Parallel Execution** — для критичных задач запускать на 2+ моделях

---

## 12. Ссылки

1. **Репозиторий:** https://github.com/anomalyco/models.dev
2. **API:** https://models.dev/api.json
3. **OpenCode:** https://opencode.ai
4. **OpenCode Config Docs:** https://opencode.ai/docs/config/
5. **Oh My Open Agent:** https://github.com/code-yeongyu/oh-my-openagent
6. **OpenCode Go:** https://opencode.ai/docs/go/
7. **HN Discussion:** https://news.ycombinator.com/item?id=47460525
8. **OpenCode Internals Deep Dive:** https://cefboud.com/posts/coding-agents-internals-opencode-deepdive/

---

*Исследование выполнено для проекта "Deep Research Skill" — Claude Desktop skill.*
