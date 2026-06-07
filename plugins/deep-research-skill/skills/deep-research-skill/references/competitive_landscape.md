# Competitive Landscape: Deep Research Solutions
## Исследование конкурентной среды для проекта "Deep Research Skill" (Claude Desktop)

**Дата исследования:** 2026-06-13  
**Методология:** Web search, GitHub analysis, arXiv/Scholar papers, documentation review  
**Всего решений проанализировано:** 15+ систем, 10+ научных статей, 5 бенчмарков  

---

## Содержание

1. [GitHub Open-Source Solutions](#1-github-open-source-solutions)
2. [Проприетарные решения](#2-проприетарные-решения)
3. [Multi-Agent Frameworks](#3-multi-agent-frameworks)
4. [Научные статьи и исследования](#4-научные-статьи-и-исследования)
5. [Бенчмарки и оценки](#5-бенчмарки-и-оценки)
6. [Best Practices и архитектурные паттерны](#6-best-practices-и-архитектурные-паттерны)
7. [Summary Table](#7-summary-table)
8. [Key Insights](#8-key-insights)
9. [Gaps (возможности для нас)](#9-gaps-возможности-для-нас)
10. [Recommendations](#10-recommendations)

---

## 1. GitHub Open-Source Solutions

### 1.1 STORM (Stanford OVAL)

| Атрибут | Данные |
|---------|--------|
| **Название** | STORM: Synthesis of Topic Outlines through Retrieval and Multi-perspective Question Asking |
| **Ссылка** | https://github.com/stanford-oval/storm |
| **Автор/организация** | Stanford OVAL Lab (Yijia Shao et al.) |
| **Stars** | 28.3k |
| **Лицензия** | MIT |
| **Язык** | Python |

**Ключевые возможности:**
- Генерация Wikipedia-подобных статей с цитированием на основе интернет-поиска
- Two-stage pipeline: pre-writing (research) → writing (article generation)
- **Perspective-Guided Question Asking**: обнаружение разных точек зрения на тему через анализ существующих статей
- **Simulated Conversation**: симуляция диалога между писателем и экспертом для генерации follow-up вопросов
- Co-STORM: совместная human-AI система с динамическим mind map
- Поддержка локальных документов (VectorRM) и поисковых движков (YouRM, BingSearch)
- Интеграция с LiteLLM для гибкого выбора моделей

**Архитектурные решения:**
- Модульная архитектура на базе DSPy
- Разделение компонентов: `conv_simulator_lm`, `question_asker_lm`, `outline_gen_lm`, `article_gen_lm`, `article_polish_lm`
- Возможность использования разных моделей для разных этапов (дешёвая для симуляции, мощная для генерации)
- Класс `STORMWikiRunner` с флагами `do_research`, `do_generate_outline`, `do_generate_article`, `do_polish_article`

**Сильные стороны:**
- Научно обоснованный подход (accepted at NAACL 2024, EMNLP 2024 for Co-STORM)
- Отличное качество генерации вопросов и охват темы
- Высокая модульность и кастомизируемость
- Поддержка работы с локальными документами

**Слабые стороны:**
- Фокус на Wikipedia-подобные статьи (не универсальный research)
- Нет real-time веб-поиска по умолчанию (требует API ключей)
- Нет поддержки Claude Skills / MCP из коробки

**Relevance:** **High** — отличная база для research pipeline

**Что можно позаимствовать:**
- Perspective-guided question asking для расширения охвата темы
- Simulated conversation для углубления исследования
- Архитектуру разделения на этапы research → outline → write → polish
- LiteLLM интеграцию для мульти-модельных пайплайнов

---

### 1.2 GPT Researcher

| Атрибут | Данные |
|---------|--------|
| **Название** | GPT Researcher |
| **Ссылка** | https://github.com/assafelovic/gpt-researcher |
| **Автор/организация** | Assaf Elovic и команда (27.5k stars, 224 контрибьютора) |
| **Stars** | 27.5k |
| **Лицензия** | Apache-2.0 |
| **Язык** | Python 57.2%, TypeScript 26.4% |

**Ключевые возможности:**
- Автономный агент глубокого исследования для web и local documents
- **Planner + Execution архитектура**: planner генерирует research questions, execution agents собирают информацию
- **Deep Research**: recursive tree-like exploration с configurable depth и breadth
- Поддержка 20+ источников на research для объективных выводов
- Генерация отчётов 2000+ слов с экспортом в PDF, Word, Markdown
- **MCP Client и MCP Server** интеграция
- **Установка как Claude Skill**: `npx skills add assafelovic/gpt-researcher`
- AI-generated inline images (Google Gemini)
- Multi-agent assistants (LangGraph и AG2)
- Frontend: lightweight (HTML/CSS/JS) и production-ready (NextJS + Tailwind)
- Поддержка Docker, PIP package
- LangSmith observability

**Архитектурные решения:**
- Параллелизация агентов для скорости
- Cost-optimization: использование `gpt-4o-mini` для простых задач, `gpt-4o` для сложных
- Средняя стоимость: ~$0.005 за research task (~3 минуты)
- Deep Research: ~$0.40 за research (o3-mini, high reasoning)
- Tree-like exploration с concurrent processing
- Поддержка гибридного retriever: `tavily,mcp`

**Сильные стороны:**
- Очень высокая relevance к нашему проекту (Claude Skill!)
- Уже работает как Claude Skill — доказанная интеграция
- MCP интеграция для подключения к специализированным источникам
- Deep Research с контролируемой глубиной и шириной
- Отличная документация и активное сообщество
- Multi-agent orchestration через LangGraph

**Слабые стороны:**
- Зависимость от внешних API (Tavily, OpenAI)
- Может быть избыточным для простых запросов
- Требует Python backend

**Relevance:** **Very High** — прямой конкурент/партнёр, уже интегрирован с Claude

**Что можно позаимствовать:**
- Формат интеграции как Claude Skill (`npx skills add`)
- Deep Research tree-like exploration pattern
- MCP client/server архитектуру для расширяемости
- Cost-tracking и token optimization подходы
- LangGraph multi-agent orchestration

---

### 1.3 Open Deep Research (LangChain)

| Атрибут | Данные |
|---------|--------|
| **Название** | Open Deep Research |
| **Ссылка** | https://github.com/langchain-ai/open_deep_research |
| **Автор/организация** | LangChain (Harrison Chase et al.) |
| **Stars** | ~2k+ (растущий) |
| **Лицензия** | MIT |

**Ключевые возможности:**
- #6 на Deep Research Bench Leaderboard (score 0.4344)
- Трёхфазный pipeline: **Scope → Research → Write**
- **Research Supervisor** с sub-agent orchestration
- Параллелизация sub-agents для независимых sub-topics
- Поддержка MCP servers
- Работает с множеством моделей и поисковых движков
- LangGraph Studio для визуализации и отладки

**Архитектурные решения (ключевые):**
- **Supervisor-Subagent pattern**: supervisor определяет независимые sub-topics и делегирует sub-agents
- **Context Engineering**: сжатие chat history в focused research brief, sub-agents "чистят" findings перед возвратом supervisor
- **Iterative depth control**: supervisor может спаунить дополнительных sub-agents для углубления
- Heuristics для определения параллелизации vs single-thread research
- Research brief как "north star" для всего процесса

**Сильные стороны:**
- Отличная архитектура supervisor/sub-agent (от Anthropic research)
- Context engineering для борьбы с token bloat
- Гибкость: supervisor адаптирует глубину исследования к запросу
- Высокая позиция на бенчмарках
- Полностью open-source с хорошей документацией

**Слабые стороны:**
- Зависимость от LangChain экосистемы
- Сложнее развертывание по сравнению с GPT Researcher
- Требует LangGraph Server

**Relevance:** **Very High** — production-ready архитектура

**Что можно позаимствовать:**
- Supervisor-subagent orchestration pattern
- Context engineering techniques (brief compression, finding pruning)
- Трёхфазный pipeline (Scope → Research → Write)
- Research brief как центральный артефакт
- Depth-tuning heuristics

---

### 1.4 AutoGPT

| Атрибут | Данные |
|---------|--------|
| **Название** | AutoGPT |
| **Ссылка** | https://github.com/Significant-Gravitas/AutoGPT |
| **Автор/организация** | Significant Gravitas Ltd. (Toran Bruce Richards) |
| **Stars** | 185k |
| **Лицензия** | Custom (proprietary для платформы) |
| **Язык** | Python 68.5%, TypeScript 30% |

**Ключевые возможности:**
- Классический autonomous AI agent (один из первых)
- Task creation, prioritization, execution, evaluation loop
- Long-term and short-term memory (vector DB)
- Plugin system для расширения функциональности
- AutoGPT Platform (no-code/low-code визуальный редактор)
- Поддержка множества LLM через OpenRouter
- "AutoPilot skills" — skill marketplace

**Архитектурные решения:**
- Classical agent loop: User Input → Task Creation → Task Prioritization → Execution → Evaluation
- Memory system: short-term (context) + long-term (vector DB)
- Plugin architecture для интеграции инструментов
- Agent-to-Agent (A2A) protocol support

**Сильные стороны:**
- Огромное community (185k stars, 814 контрибьюторов)
- Зрелая платформа с визуальным редактором
- Хорошая memory management
- OpenRouter интеграция для мульти-модельности

**Слабые стороны:**
- Часто "застревает" в бесконечных loops
- Высокая стоимость API calls при длительной работе
- Слишком общего назначения (не специализирован на research)
- Over-engineered для простых research задач

**Relevance:** **Medium** — хороший reference для autonomous agents, но не research-specific

**Что можно позаимствовать:**
- Memory management patterns
- Plugin/skill architecture
- OpenRouter интеграцию для model routing

---

### 1.5 MetaGPT

| Атрибут | Данные |
|---------|--------|
| **Название** | MetaGPT: The Multi-Agent Framework |
| **Ссылка** | https://github.com/FoundationAgents/MetaGPT |
| **Автор/организация** | DeepWisdom (Chenglin Wu) |
| **Stars** | 68.6k |
| **Лицензия** | MIT |
| **Язык** | Python 97.5% |

**Ключевые возможности:**
- Multi-agent collaborative framework: "AI Software Company"
- Role-based agents: Product Manager, Architect, Project Manager, Engineer, QA
- Standard Operating Procedures (SOPs) для каждой роли
- One-line requirement → full software solution
- Global message pool (publish-subscribe)
- Structured communication (не natural language, а документы и диаграммы)
- MGX (MetaGPT X) — продукт для natural language programming

**Архитектурные решения:**
- **SOP-driven orchestration**: `Code = SOP(Team)`
- **Structured communication protocol**: агенты общаются через structured outputs (PRD, diagrams, docs)
- **Global message pool**: publish-subscribe для обмена между агентами
- **Assembly-line paradigm**: инкрементальная разработка через передачу deliverables

**Сильные стороны:**
- Отличная абстракция ролей и процессов
- Structured communication уменьшает "telephone game" эффект
- Высокая масштабируемость для сложных проектов
- ICLR 2024 oral presentation (top 1.2%)

**Слабые стороны:**
- Ориентирован на software development, не research
- Высокая latency из-за последовательной передачи между ролями
- Overhead от structured communication

**Relevance:** **Medium** — паттерны orchestration применимы к research

**Что можно позаимствовать:**
- SOP-driven orchestration pattern
- Structured communication между агентами
- Role-based agent design
- Global message pool pattern

---

### 1.6 CrewAI

| Атрибут | Данные |
|---------|--------|
| **Название** | CrewAI |
| **Ссылка** | https://github.com/crewaiinc/crewAI |
| **Автор/организация** | João Moura и команда |
| **Stars** | ~25k+ |
| **Лицензия** | MIT |
| **Язык** | Python |

**Ключевые возможности:**
- Framework для orchestrating role-playing autonomous AI agents
- **Crews**: автономные агенты с collaborative intelligence
- **Flows**: event-driven production architecture
- YAML-конфигурация агентов и задач
- Agent roles, goals, backstories
- Process types: sequential, hierarchical, parallel
- Memory и knowledge sources для RAG
- Tool integration (web search, APIs, DB queries)
- CrewAI AMP Suite (enterprise)

**Архитектурные решения:**
- Role-based agent definition через YAML/Python
- Process orchestration: sequential, hierarchical, parallel
- Task delegation между агентами
- Memory: short-term, long-term, entity memory
- Knowledge sources для RAG

**Сильные стороны:**
- Простота определения агентов и задач
- Хорошая документация и community (100k+ certified developers)
- Независим от LangChain
- Production-ready Flows architecture

**Слабые стороны:**
- Меньше специализации для deep research
- Enterprise фокус с paid features
- Ограниченная гибкость для research-specific workflows

**Relevance:** **Medium** — хороший framework, но требует adaptation для research

**Что можно позаимствовать:**
- Role-based agent definition (YAML/code hybrid)
- Process orchestration patterns
- Memory и Knowledge integration

---

## 2. Проприетарные решения

### 2.1 OpenAI Deep Research (o3)

| Атрибут | Данные |
|---------|--------|
| **Название** | OpenAI Deep Research |
| **Модель** | o3 (reasoning model) |
| **Компания** | OpenAI |
| **Статус** | Proprietary (ChatGPT Pro/Plus) |

**Ключевые возможности:**
- End-to-end research с web browsing, data analysis, synthesis
- Reasoning model o3 для multi-hop reasoning
- До 64 browsing actions per research task
- Детальные цитаты и source verification
- BrowseComp: ~51.5% accuracy (best in class)

**Архитектурные решения (известные):**
- Test-time compute scaling: performance улучшается с увеличением compute
- Aggregation strategies: majority voting, weighted voting, best-of-N
- Specialized browsing-trained agent model
- Multi-hop reasoning с persistent web navigation

**Сильные стороны:**
- Лучший в классе на BrowseComp и других бенчмарках
- Мощное reasoning (o3)
- Production scale (миллионы пользователей)

**Слабые стороны:**
- Closed-source
- Высокая стоимость ($200/month для Pro)
- Ограниченная кастомизация

**Relevance:** **High** — benchmark leader, но closed-source

**Что можно позаимствовать:**
- Test-time compute scaling pattern
- Aggregation strategies (best-of-N для quality)
- Multi-hop browsing architecture

---

### 2.2 Perplexity Deep Research

| Атрибут | Данные |
|---------|--------|
| **Название** | Perplexity Deep Research |
| **Модели** | Sonar (Llama-based), R1 1776 (DeepSeek R1) |
| **Компания** | Perplexity AI |
| **Статус** | Proprietary (free tier + Pro $20/month) |

**Ключевые возможности:**
- Multi-pass querying (20-50 targeted queries per research)
- 200+ sources на отчёт
- Test Time Compute (TTC) expansion framework
- Chain-of-thought reasoning
- Встроенные визуализации (timelines, pros/cons)
- Iterative refinement через follow-up
- 93.9% accuracy на SimpleQA
- 21.1% на Humanity's Last Exam

**Архитектурные решения:**
- **Iterative research process**: search → read → refine plan → repeat
- **TTC expansion**: систематическое исследование через analysis cycles
- Кастомные модели: Sonar (быстрый поиск) + R1 1776 (reasoning)
- Result clustering по relevance и recency

**Сильные стороны:**
- Один из самых быстрых (~3 минуты на отчёт)
- Отличный баланс speed/quality/cost
- Model Council (сравнение моделей)
- Открытая версия R1 1776

**Слабые стороны:**
- Closed-source основная система
- Зависимость от Perplexity инфраструктуры
- Ограниченная кастомизация

**Relevance:** **High** — лучший пример production deep research

**Что можно позаимствовать:**
- Multi-pass querying strategy
- TTC expansion pattern
- Iterative refinement с feedback loop
- Speed/quality/cost баланс

---

### 2.3 Google Deep Research (Gemini)

| Атрибут | Данные |
|---------|--------|
| **Название** | Google Deep Research |
| **Модель** | Gemini 2.5 Pro / 3 Pro |
| **Компания** | Google |
| **Статус** | Proprietary (Gemini Advanced) |

**Ключевые возможности:**
- Интеграция с Google Search и Workspace
- Multi-step reasoning с grounding в web sources
- Высокая скорость (1.8 минуты на отчёт)
- Интеграция с Google Docs, Sheets, Drive

**Архитектурные решения:**
- Native интеграция с Google Search index
- Gemini multi-modal reasoning (text + image + video)
- Tight integration с Google ecosystem

**Сильные стороны:**
- Быстрый доступ к свежей информации
- Отличная интеграция с Google Workspace
- Мощная multi-modal reasoning

**Слабые стороны:**
- Закрытая экосистема Google
- Ограниченная кастомизация

**Relevance:** **Medium** — хороший reference, но closed ecosystem

---

### 2.4 Anthropic Claude Research (Cowork)

| Атрибут | Данные |
|---------|--------|
| **Название** | Claude Research / Cowork |
| **Модель** | Claude Sonnet 4.6+ |
| **Компания** | Anthropic |
| **Статус** | Proprietary (Claude Pro/Max) |

**Ключевые возможности:**
- Multi-agent research system (lead agent + parallel sub-agents)
- Web search + Google Workspace + integrations
- Computer Use: VM sandbox для выполнения кода
- Chrome MCP для browser automation
- Dispatch: удалённое управление с телефона

**Архитектурные решения (из blog post):**
- **Lead agent + sub-agents**: lead планирует research, sub-agents исследуют параллельно
- **Subagent output to filesystem**: агенты пишут в файлы, передают lightweight references
- **Context compression**: агенты суммируют завершённые фазы перед продолжением
- **End-state evaluation**: оценка финального результата вместо turn-by-turn
- **Fresh subagents with clean contexts**: при приближении к context limit
- Chrome MCP: browser control через extension + native messaging bridge
- VM sandbox: gVisor + MITM proxy + domain allowlist

**Сильные стороны:**
- Мощная multi-agent архитектура (от создателей Claude)
- Production-grade (миллионы пользователей)
- Отличная безопасность (VM sandbox, ephemeral CA)
- Chrome MCP — отличный pattern для browser integration

**Слабые стороны:**
- Closed-source
- Зависимость от Anthropic инфраструктуры

**Relevance:** **Very High** — мы строим skill для этой же платформы!

**Что можно позаимствовать:**
- Lead + sub-agent orchestration pattern
- Subagent output to filesystem pattern
- Context compression strategies
- Chrome MCP integration pattern
- End-state evaluation approach

---

## 3. Multi-Agent Frameworks

### 3.1 LangGraph

| Атрибут | Данные |
|---------|--------|
| **Название** | LangGraph |
| **Организация** | LangChain |
| **Паттерны** | Subagents, Handoffs, Skills, Router, Custom Workflow |

**Ключевые паттерны:**

| Паттерн | Описание | Применимость |
|---------|----------|-------------|
| **Subagents** | Main agent координирует subagents как tools | Research decomposition |
| **Handoffs** | Передача control между агентами через tool calls | Task specialization |
| **Skills** | Специализированные prompts/knowledge on-demand | Domain expertise |
| **Router** | Routing step классифицирует input и направляет | Query classification |
| **Custom Workflow** | Bespoke execution flows с deterministic + agentic | Complex pipelines |

**Relevance:** **High** — паттерны применимы к research orchestration

---

### 3.2 DSPy

| Атрибут | Данные |
|---------|--------|
| **Название** | DSPy |
| **Организация** | Stanford |
| **Назначение** | Framework for programming (not prompting) language models |

**Ключевые возможности:**
- Модульные building blocks (Predict, ChainOfThought, Retrieve, etc.)
- Автоматическая оптимизация prompts
- Компиляция программ для повышения качества
- Используется в STORM

**Relevance:** **Medium** — хорош для research pipeline composition

---

## 4. Научные статьи и исследования

### 4.1 REFLECT: Reliable Fine-grained LLM Judge Evaluation

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | arXiv:2605.19196 |
| **Авторы** | Leyao Wang et al. |
| **Ключевой тезис** | LLM judges unreliable для deep research agents (best <55% accuracy) |

**Инсайты:**
- Meta-evaluation проблема: перед deployment LLM judges нужно оценивать
- Controlled interventions для создания verifiable test cases
- Таксономия failure modes: process-level и outcome-level
- Evidence verification — самая слабая сторона LLM judges

**Relevance:** **High** — важно для evaluation нашего research skill

---

### 4.2 DataSTORM: Deep Research on Large-Scale Databases

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | arXiv:2604.06474 |
| **Авторы** | Shicheng Liu et al. (Stanford) |
| **Ключевой тезис** | Deep research над structured data требует thesis-driven analytical process |

**Инсайты:**
- Exploratory Data Analysis + Data Storytelling principles
- Thesis discovery → validation → analytical narrative
- SOTA на InsightBench: +19.4% relative improvement
- Outperforms ChatGPT Deep Research на structured data

**Relevance:** **High** — для research с табличными данными

---

### 4.3 Deep Researcher Agent: 24/7 Deep Learning Experiments

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | arXiv:2604.05854 |
| **Автор** | Xiangyue Zhang |
| **GitHub** | https://github.com/Xiangyue-Zhang/auto-deep-researcher-24x7 |

**Инсайты:**
- **Zero-Cost Monitoring**: 0 LLM API costs во время training (process-level checks + log reads)
- **Two-Tier Constant-Size Memory**: ~5K characters cap, независимо от runtime
- **Leader-Worker Architecture**: worker agents с 3-5 tools, -73% token overhead
- 500+ experiment cycles за 30 дней, $0.08 per 24-hour cycle

**Relevance:** **High** — cost-efficiency паттерны

---

### 4.4 Empirical Study of Multi-Agent Collaboration for Automated Research

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | arXiv:2603.29632 |
| **Авторы** | Yang Shen et al. |
| **Ключевой тезис** | Trade-off между operational stability и theoretical deliberation |

**Инсайты:**
- **Subagent mode**: resilient, high-throughput (optimal для shallow optimizations)
- **Agent team topology**: deep theoretical alignment (optimal для complex refactoring)
- **Динамически routed architectures** адаптируют структуру к task complexity
- Git worktree isolation для execution-based testing

**Relevance:** **Very High** — прямое руководство по multi-agent design

---

### 4.5 DOVA: Deliberation-First Multi-Agent Orchestration

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | arXiv:2603.13327 |
| **Авторы** | Aaron Shen, Alfred Shen |
| **Ключевой тезис** | Deliberation-first orchestration с adaptive token budgeting |

**Инсайты:**
- **Deliberation-first**: explicit meta-reasoning перед tool invocation
- **Hybrid collaborative reasoning**: ensemble diversity + blackboard transparency + iterative refinement
- **Adaptive multi-tiered thinking**: 6-level token-budget allocation
- Cost reduction: 40-60% на simple tasks
- Persistent user model и entity-aware conversation context

**Relevance:** **Very High** — cost-aware routing и deliberation pattern

---

### 4.6 O-Researcher: Multi-Agent Distillation and Agentic RL

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | arXiv:2601.03743 |
| **Авторы** | Yi Yao et al. |
| **Ключевой тезис** | Мulti-agent workflow для synthesis of research-grade training data |

**Инсайты:**
- Collaborative AI agents симулируют complex tool-integrated reasoning
- Two-stage training: SFT + novel RL method
- State-of-the-art на deep research benchmarks для open-source models
- Scalable pathway без proprietary data

**Relevance:** **Medium** — data synthesis approach

---

### 4.7 Anthropic: How we built our multi-agent research system

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | https://www.anthropic.com/engineering/multi-agent-research-system |
| **Авторы** | Jeremy Hadfield et al. |

**Ключевые инсайты:**
- Multi-agent systems = vital way to scale performance once intelligence threshold reached
- **Essence of search is compression**: subagents distill insights from vast corpus
- **Subagents for separation of concerns**: distinct tools, prompts, exploration trajectories
- **15x more tokens** чем typical chat (token-heavy task)
- **Fresh subagents with clean contexts** при приближении к context limit
- **End-state evaluation** для state-mutating agents

**Relevance:** **Very High** — прямой опыт создателей Claude

---

## 5. Бенчмарки и оценки

### 5.1 DeepResearch Bench II

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | https://agentresearchlab.com/benchmarks/deepresearch-bench-ii/ |
| **Организация** | USTC-CMI |
| **Метрики** | InfoRecall, Analysis, Presentation, TotalScore |
| **Размер** | 132 research tasks, 9,430 expert-written rubrics |

**Топ-3 (2026):**
1. iFlow-Researcher (NJU&Alibaba): 59.91%
2. Xiaoyi DeepResearch 6.0 (Huawei): 58.72%
3. CMCC-DeepInsight (China Mobile): 55.39%

**Open-source baseline:**
- OpenAI-GPT-o3 Deep Research: 45.40%
- Gemini-3-Pro Deep Research: 44.60%
- Open Deep Research (LangChain): ~43%

---

### 5.2 BrowseComp (OpenAI)

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | https://openai.com/index/browsecomp/ |
| **Организация** | OpenAI |
| **Размер** | 1,266 questions |
| **Фокус** | Persistent web navigation, multi-hop reasoning |

**Результаты:**
- GPT-4o + browsing: 1.9%
- OpenAI Deep Research: ~51.5% (single attempt), ~78% (best-of-64)
- Тест-time compute scaling показывает плавный рост

---

### 5.3 xbench-DeepSearch

| Атрибут | Данные |
|---------|--------|
| **Ссылка** | https://xbench.org/agi/aisearch |
| **Фокус** | End-to-end deep search (planning → search → reasoning → summarization) |
| **Контекст** | Chinese-context focused |

**Топ-3 (2026):**
1. ChatGPT-5-Pro: 79
2. Gemini Pro: 53
3. Kimi K2.5 Thinking: 46

---

### 5.4 Humanity's Last Exam

| Атрибут | Данные |
|---------|--------|
| **Размер** | 3,000+ questions, 100+ subjects |
| **Фокус** | Rigorous assessment across math, science, history, literature |

**Результаты:**
- Perplexity Deep Research: 21.1%
- Other models: o3-mini, DeepSeek R1 ниже

---

## 6. Best Practices и архитектурные паттерны

### 6.1 Multi-Agent Orchestration Patterns

```
┌─────────────────────────────────────────────────────────────┐
│                 Deep Research Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE: User query → Clarification → Research Brief      │
│            (context compression, brief generation)           │
│                                                             │
│  2. RESEARCH: Supervisor agent                              │
│     ├── Sub-agent 1: Topic A (parallel)                     │
│     ├── Sub-agent 2: Topic B (parallel)                     │
│     ├── Sub-agent 3: Topic C (parallel)                     │
│     └── Iterative depth control                             │
│                                                             │
│  3. WRITE: Report generation with citations                 │
│     ├── Section synthesis                                   │
│     ├── Source deduplication                                │
│     └── Citation formatting                                 │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Context Engineering Best Practices

Из опыта LangChain и Anthropic:

1. **Compress chat history into research brief** — предотвращает token bloat
2. **Sub-agents prune findings** — чистят raw tool-call results перед возвратом
3. **Fresh subagents with clean contexts** — при приближении к context limit
4. **Subagent output to filesystem** — artifact-based, не через conversation
5. **End-state evaluation** — оценивать результат, не процесс

### 6.3 Cost-Aware Routing

Из DOVA paper и GPT Researcher:

1. **Tiered model selection**: дешёвая модель для simple tasks, дорогая для complex
2. **Adaptive token budgeting**: 6-level allocation (DOVA)
3. **Model cascading**: пробовать дешёвую модель первой, эскалировать при необходимости
4. **Cost tracking per research task**: средняя стоимость $0.005-0.40

### 6.4 Tool-Augmented LLM Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Research Agent Architecture                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Planner    │───→│  Supervisor  │───→│   Writer     │   │
│  │   Agent      │    │   Agent      │    │   Agent      │   │
│  └──────────────┘    └──────┬───────┘    └──────────────┘   │
│                             │                                │
│                    ┌────────┼────────┐                       │
│                    ↓        ↓        ↓                       │
│              ┌────────┐┌────────┐┌────────┐                 │
│              │Search  ││Search  ││Search  │                 │
│              │Agent 1 ││Agent 2 ││Agent N │                 │
│              └───┬────┘└───┬────┘└───┬────┘                 │
│                  │         │         │                        │
│              ┌───┴─────────┴─────────┴───┐                   │
│              │   Web Search / MCP Tools    │                  │
│              │   (Tavily, Brave, Exa...)   │                  │
│              └─────────────────────────────┘                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. Summary Table

| # | Решение | Тип | Stars/Scale | Relevance | Архитектура | Ключевой инсайт |
|---|---------|-----|-------------|-----------|-------------|-----------------|
| 1 | **STORM** | OSS | 28.3k | **High** | Perspective-guided QA + Simulated conversation | Perspective discovery для глубокого охвата |
| 2 | **GPT Researcher** | OSS | 27.5k | **Very High** | Planner + Execution agents, Deep Research tree | Уже Claude Skill, MCP интеграция |
| 3 | **Open Deep Research** | OSS | ~2k | **Very High** | Supervisor-Subagent (Scope→Research→Write) | Context engineering, depth-tuning |
| 4 | **AutoGPT** | OSS | 185k | Medium | Task loop + Memory + Plugins | Plugin architecture, memory management |
| 5 | **MetaGPT** | OSS | 68.6k | Medium | SOP-driven multi-role agents | Structured communication, SOPs |
| 6 | **CrewAI** | OSS | ~25k | Medium | Role-based crews + flows | YAML agent definition, process orchestration |
| 7 | **OpenAI Deep Research** | Prop | ChatGPT Pro | High | o3 + browsing, test-time compute | Best-of-N aggregation, multi-hop reasoning |
| 8 | **Perplexity Deep Research** | Prop | 200M ARR | High | TTC expansion, multi-pass querying | Speed/quality/cost баланс |
| 9 | **Google Deep Research** | Prop | Gemini Adv. | Medium | Gemini + Google Search index | Workspace интеграция |
| 10 | **Claude Research** | Prop | Claude Pro/Max | **Very High** | Lead + sub-agents, Chrome MCP | Subagent→filesystem, context compression |
| 11 | **LangGraph** | Framework | LangChain | **High** | Subagents, Handoffs, Router, Skills | Мульти-паттерн orchestration |
| 12 | **DSPy** | Framework | Stanford | Medium | Modular blocks, prompt compilation | Pipeline composition |

---

## 8. Key Insights

### 8.1 Архитектурные инсайты

1. **Supervisor-Subagent — доминирующий паттерн**. Все production системы (Claude Research, Open Deep Research, GPT Researcher multi-agent) используют lead/supervisor агента с parallel sub-agents. Это позволяет масштабировать исследование без линейного роста latency.

2. **Context engineering критична**. Research — token-heavy задача (Anthropic: 15x больше токенов чем chat). Без compression и pruning система быстро упирается в context limits и растут costs.

3. **Planning-first approach**. Успешные системы (STORM, Open Deep Research, Perplexity) начинают с генерации research plan / brief, который служит "north star" для всего процесса.

4. **Tree-like exploration для deep research**. GPT Researcher и OpenAI используют рекурсивное исследование с configurable depth/breadth. Это позволяет адаптировать глубину к сложности темы.

5. **MCP — emerging standard для интеграции**. GPT Researcher, Claude Desktop, многие агенты переходят на Model Context Protocol для подключения tools. Это наш путь интеграции.

### 8.2 Продуктовые инсайты

6. **Claude Skill формат — проверенный путь**. GPT Researcher уже работает как `npx skills add assafelovic/gpt-researcher`. Это доказанная модель distribution.

7. **Cost range: $0.005 - $0.40 per research**. Системы оптимизируют costs через tiered model selection. Simple research = дёшево, Deep research = можно потратить больше.

8. **Speed vs Quality trade-off управляется через depth-tuning**. Хорошая система позволяет пользователю выбирать между быстрым summary и глубоким research.

9. **Benchmark leadership требует specialization**. Общие агенты (GPT-4o + browsing) показывают 1.9% на BrowseComp. Специализированные deep research агенты — 51%+. Разница в архитектуре, не модели.

10. **Evaluation — нерешённая проблема**. Даже лучшие LLM judges достигают <55% accuracy на evidence verification (REFLECT paper). Нужны специализированные evaluation frameworks.

---

## 9. Gaps (возможности для нас)

### 9.1 Что не покрывают существующие решения

1. **Native Claude Desktop integration**. GPT Researcher требует Python backend. Нет решений, которые работают natively в Claude Desktop без external сервера (кроме простых skills).

2. **Adaptive cost-quality routing**. Большинство систем используют фиксированные модели. Нет intelligent routing, который адаптирует model selection к сложности query в real-time.

3. **Persistent memory across research sessions**. Системы не запоминают предыдущие исследования пользователя для building upon prior work.

4. **Structured data deep research**. DataSTORM покрывает databases, но большинство OSS фокусируются на web text. Мало решений для research на structured/tabular данных.

5. **Research reproducibility and versioning**. Нет системы, которая версионирует research steps, sources, и позволяет replay/audit исследование.

6. **Collaborative research**. Co-STORM есть, но нет production-ready collaborative research с real-time editing.

7. **Vertical-specific research agents**. Большинство систем — general purpose. Нет специализации для конкретных доменов (biotech, legal, finance) в формате Claude Skill.

8. **Offline/Local-first research**. Большинство требуют cloud APIs. Мало решений для полностью локального research с local LLMs.

---

## 10. Recommendations

### 10.1 Архитектура (что позаимствовать)

| Компонент | Источник | Приоритет |
|-----------|----------|-----------|
| **Supervisor-Subagent orchestration** | Open Deep Research + Claude Research blog | **Critical** |
| **Research Brief as north star** | Open Deep Research | **Critical** |
| **Context compression** | Anthropic blog + LangChain | **Critical** |
| **Tree-like Deep Research** | GPT Researcher | **High** |
| **MCP integration** | GPT Researcher + Claude Desktop | **High** |
| **Subagent→Filesystem pattern** | Anthropic blog | **High** |
| **Perspective-guided questions** | STORM | Medium |
| **SOP-driven roles** | MetaGPT | Medium |
| **Cost tracking per task** | GPT Researcher | Medium |
| **Best-of-N aggregation** | OpenAI Deep Research | Medium |

### 10.2 Продукт (что реализовать)

1. **Claude Skill формат** — `npx skills add our/deep-research-skill` (как GPT Researcher)
2. **Tiered research modes** — Quick / Standard / Deep (как Perplexity, но с cost transparency)
3. **Research brief generation** — автоматическое уточнение scope перед началом
4. **Parallel sub-agent execution** — для независимых sub-topics
5. **Source management** — deduplication, credibility scoring, citation formatting
6. **Persistent memory** — research history, preferred sources, user feedback
7. **Adaptive model routing** — simple tasks = fast/cheap model, complex = powerful model

### 10.3 Технический стек (рекомендация)

```
Integration:     MCP (Model Context Protocol) — native Claude Desktop
Orchestration:   Supervisor-Subagent pattern (LangGraph-compatible)
Models:          LiteLLM для multi-provider support
                Claude Sonnet 4 (default), Haiku (quick), Opus (deep)
Search:          Pluggable retrievers (Tavily, Brave, Exa, Arxiv)
Memory:          Local file-based (Claude artifacts) + vector for context
Context Mgmt:    Compression + pruning + fresh subagents
Evaluation:      REFLECT-inspired meta-evaluation
```

### 10.4 Дифференциация

Наше уникальное позиционирование:
- **Native Claude Desktop skill** — не требует external backend
- **Adaptive cost-quality routing** — intelligent model selection
- **Vertical research templates** — pre-configured для доменов
- **Research reproducibility** — versioned, auditable research steps
- **Persistent research memory** — builds upon prior work

---

## Appendix A: Методология исследования

### Поисковые запросы (web search):
- "deep research agent" + "automation"
- "AI research assistant" open source
- "multi-agent research" orchestration
- "Claude plugin" OR "Claude skill" research
- "web scraping" + "AI agent" research pipeline
- GPT Researcher, AutoGPT, MetaGPT, STORM, OpenDeepResearch

### GitHub репозитории проанализированы:
- stanford-oval/storm
- assafelovic/gpt-researcher
- langchain-ai/open_deep_research
- Significant-Gravitas/AutoGPT
- FoundationAgents/MetaGPT
- crewaiinc/crewAI

### arXiv статьи проанализированы:
- arXiv:2605.19196 — REFLECT
- arXiv:2604.06474 — DataSTORM
- arXiv:2604.05854 — Deep Researcher Agent
- arXiv:2603.29632 — Multi-Agent Collaboration
- arXiv:2603.13327 — DOVA
- arXiv:2601.03743 — O-Researcher

### Бенчмарки:
- DeepResearch Bench II (USTC-CMI)
- BrowseComp (OpenAI)
- xbench-DeepSearch
- Humanity's Last Exam

---

*Файл подготовлен автоматически на основе deep research competitive landscape analysis.*
