# Skill Marketplace Research: TrendShift, Claude Code, GPT Store & Beyond

> **Дата исследования:** 2026-05-20
> **Цель:** Изучить экосистему distribution для AI-агентских skill'ов, проанализировать TrendShift.io как источник ранних сигналов, и сформулировать стратегию распространения Deep Research Skill

---

## 1. TrendShift (trendshift.io)

### 1.1. Что это за платформа

**TrendShift** — аналитическая платформа для отслеживания трендов open-source проектов на GitHub. Платформа позиционирует себя как "alternative to GitHub Trending" с фокусом на **early detection** — catching repositories as they rise, not after they peak.

**Ключевые характеристики:**
- **100K+ monthly visitors** (по данным сайта)
- **High-intent audience:** разработчики, отслеживающие, что набирает популярность в OSS
- Нет tracking pixels, no popups — privacy-friendly подход
- Реаль-time мониторинг упоминаний на X (Twitter)

### 1.2. Какие данные собирает

| Тип данных | Описание |
|-----------|----------|
| **GitHub Stars** | Ежедневный прирост звезд для каждого репозитория |
| **GitHub Forks** | Динамика форков |
| **Social Mentions** | Live-упоминания на X (Twitter) в реальном времени |
| **Topics/Tags** | Категоризация по темам (#AI-agent, #RAG, #MCP и др.) |
| **Programming Languages** | Распределение по языкам программирования |
| **Fragmentation Index** | Индекс концентрации/фрагментации по топикам |
| **Historical Trends** | Данные с 2025 года (ежемесячная агрегация) |

### 1.3. Какие тренды показывает

**Топ трендовые темы (Daily, на момент исследования):**

| # | Topic | Stars (daily) | Релевантность для Deep Research |
|---|-------|---------------|--------------------------------|
| 1 | #AI agent | 4.7k | **Критическая** — наш skill именно для агентов |
| 2 | #AI coding assistant | 1.6k | Средняя — соседняя категория |
| 3 | #AI skills | 1.6k | **Критическая** — прямая категория нашего продукта |
| 4 | #Self-hosted | 1.1k | Средняя — возможен self-hosted вариант |
| 5 | #Web scraping | 682 | **Высокая** — research требует scraping |
| 6 | #Curated list | 680 | Низкая |
| 7 | #RAG | 632 | **Высокая** — RAG + research идут рука об руку |
| 8 | #AI workflow | 592 | **Высокая** — research как workflow |
| 9 | #AI infrastructure | 533 | Средняя |
| 10 | #MCP | 431 | **Высокая** — интеграция с MCP servers |

**Ключевое наблюдение:** Категория #AI skills находится на **3-м месте** по дневному приросту звезд, что подтверждает высокий спрос на агентские skills и выбранное направление.

### 1.4. API

TrendShift предоставляет **публичный API для бейджей**:

```
https://trendshift.io/api/badge/repositories/{repository_id}
```

Пример использования:
```html
<a href="https://trendshift.io/repositories/10421" target="_blank">
  <img src="https://trendshift.io/api/badge/repositories/10421" 
       alt="Repo | Trendshift" style="width: 250px; height: 55px;" />
</a>
```

**Возможности интеграции с AI-агентами:**
- **Badge API** — для отображения трендовых метрик в README
- **Live Mentions Feed** — мониторинг социальных сигналов (web scraping адаптер)
- **Topics API** (implicit) — через парсинг HTML или reverse engineering
- **No official REST API** — но данные доступны через веб-скрапинг

### 1.5. Использование в Deep Research (Early Signal Detection)

**Стратегия использования TrendShift для раннего обнаружения:**

1. **Repository Monitoring**
   - Отслеживать новые репозитории в категориях #AI-skills, #AI-agent, #AI-workflow
   - Настроить алерты на появление skills с >50 stars/day

2. **Topic Fragmentation Analysis**
   - Использовать Fragmentation Index для определения зрелости рынка
   - Высокая фрагментация = возможность для consolidation (наш шанс)

3. **Social Signal Tracking**
   - Live mentions показывают, что обсуждают разработчики прямо сейчас
   - Можно выявить emerging topics до их попадания в топы

4. **Competitive Intelligence**
   - Мониторить конкурирующие research skills
   - Отслеживать их рост и adoption

**Интеграция с AI-агентами:**
```python
# Концепт адаптера для Deep Research Skill
class TrendShiftAdapter:
    """Адаптер для получения early signals из TrendShift"""
    
    BASE_URL = "https://trendshift.io"
    
    async def get_trending_topics(self, period="daily"):
        """Получить трендовые топики за период"""
        # Парсинг или API call
        pass
    
    async def get_repository_momentum(self, repo_full_name):
        """Получить моментум конкретного репозитория"""
        pass
    
    async def get_live_mentions(self, topic_filter=None):
        """Получить live-упоминания по теме"""
        pass
```

---

## 2. Claude Code Marketplace

### 2.1. Формат .claude-plugin/marketplace.json

**Структура marketplace-репозитория:**
```
.claude-plugin/
  marketplace.json    # Описание маркетплейса
  icons/
    icon.svg          # Иконка маркетплейса

skills/
  skill-name/
    SKILL.md          # Основной файл skill'а
    scripts/          # Исполняемые скрипты
    references/       # Справочные материалы
    assets/           # Шаблоны, ресурсы
```

**Формат marketplace.json:**
```json
{
  "name": "Anthropic Skills",
  "description": "Official skills from Anthropic",
  "icon": "icons/icon.svg",
  "skills": [
    {
      "name": "skill-name",
      "path": "skills/skill-name",
      "description": "What this skill does"
    }
  ]
}
```

### 2.2. Требования к Skills

**SKILL.md — обязательный формат (спецификация agentskills.io):**

```yaml
---
name: deep-research          # max 64 chars, lowercase + hyphens
description: >               # max 1024 chars, THE MOST IMPORTANT FIELD
  Conduct comprehensive multi-source research on any topic. 
  Use when user asks to 'research', 'deep dive', 'analyze', 
  'investigate', 'find information about', or needs grounded 
  synthesis from multiple sources.
license: Apache-2.0
compatibility: Requires internet access, Python 3.10+
metadata:
  author: your-org
  version: "1.0.0"
  category: research
  tags: [research, analysis, web-scraping, synthesis]
allowed-tools: Bash Read Write Fetch
---

# Deep Research Skill

## Workflow
1. Plan research scope
2. Search multiple sources
3. Synthesize findings
4. Cite sources
```

**Ключевые требования:**
| Требование | Описание |
|-----------|----------|
| `name` | lowercase, hyphens, 1-64 chars, = directory name |
| `description` | **Ключевое поле для trigger'а** — описывает ЧТО и КОГДА |
| `SKILL.md` | Должен быть < 500 lines (рекомендация) |
| Progressive disclosure | Только frontmatter загружается всегда, полные инструкции — по trigger'у |
| `scripts/` | Опционально, исполняемый код |
| `references/` | Опционально, документация |

### 2.3. Категории

**Основные категории skills в marketplace:**

| Категория | Примеры | Спрос |
|-----------|---------|-------|
| **Developer Tools** | git-helpers, testing, debugging | Высокий |
| **Productivity** | document-processing, automation | Высокий |
| **AI & ML** | model-evaluation, data-analysis | Очень высокий |
| **Security** | audit, vulnerability-scanning | Средний |
| **Design** | frontend-design, UI/UX | Средний |
| **Office & Docs** | docx, pdf, pptx, xlsx | Высокий |

**Deep Research Skill попадает в:** AI & ML + Productivity + Developer Tools (кросс-категория)

### 2.4. Success Stories

**Топовые skills и их метрики:**

| Skill | Stars | Установки | Что делает |
|-------|-------|-----------|------------|
| `anthropics/skills` | 147k | — | Официальный репозиторий |
| `trailofbits/skills` | ~500 | Высокие | Security skills |
| `ComposioHQ/awesome-claude-skills` | 3.2k | Средние | Коллекция офисных skills |
| `NeoLabHQ/skills` | 433 | Средние | AI & Dev tools |
| `superpowers` (obra) | Популярный | Высокие | Методологический фреймворк |

**Факторы успеха:**
1. **Trigger reliability** — description должна точно описывать activation condition
2. **Progressive disclosure** — минимальный контекстный footprint
3. **Хорошие scripts** — рабочий код, а не только инструкции
4. **Community adoption** — форки, звезды, PR'ы
5. **Cross-platform compatibility** — работает на Claude Code, Codex CLI, Copilot

### 2.5. Как попасть в Marketplace

**Способ 1: Официальный marketplace (anthropics/skills)**
1. Создать SKILL.md по спецификации
2. Пройти валидацию на agentskills.io
3. Отправить Pull Request в `anthropics/skills`
4. Пройти code review

**Способ 2: Собственный marketplace**
```bash
# Создать marketplace.json
# Опубликовать на GitHub
# Пользователи добавляют:
/plugin marketplace add your-username/your-marketplace
/plugin install your-skill-name
```

**Способ 3: Community marketplaces**
- `skillsmp.com` — community marketplace
- `skills.sh` — каталог от Vercel
- `travisvn/awesome-claude-skills` — awesome-лист

**Способ 4: npx distribution**
```bash
npx skills add your-username/your-skill-name
```

**Способ 5: gh skill (новый стандарт, 2026 Q2)**
```bash
gh skill install owner/repo[/path][@tag] --agent claude-code
gh skill publish  # публикация своего skill'а
```

---

## 3. GPT Store

### 3.1. Research-related GPTs

**Категории в GPT Store:**
- Research & Analysis
- Writing & Content
- Programming
- Data Analysis
- Education
- Lifestyle

**Что популярно в Research-категории:**

| Тип GPT | Описание | Популярность |
|---------|----------|--------------|
| **Academic Research** | Поиск и анализ научных статей | Высокая |
| **Web Search + Synthesis** | Поиск в интернете + обобщение | Очень высокая |
| **Data Analysis** | Анализ CSV, Excel, визуализация | Высокая |
| **Writing Assistant** | Помощь в написании текстов | Очень высокая |
| **Code Analysis** | Анализ кодовых баз | Средняя |

### 3.2. Бизнес-модель

**GPT Store Revenue Model:**
- **Creator payouts**: OpenAI распределяет часть дохода между создателями популярных GPTs
- **Usage-based**: чем больше использований, тем выше выплаты
- **No direct pricing**: GPTs бесплатны для пользователей ChatGPT Plus/Pro
- **Discovery problem**: сложность поиска среди миллионов GPTs

**Проблемы GPT Store:**
1. **Oversaturation** — слишком много GPTs, сложно выделиться
2. **No code execution** — ограниченная функциональность vs skills
3. **Closed ecosystem** — только OpenAI, нет cross-platform
4. **Limited customization** — нет скриптов, нет progressive disclosure

### 3.3. Уроки для нас

| Урок | Применение к Deep Research Skill |
|------|----------------------------------|
| **Discovery — главная проблема** | Инвестировать в SEO, awesome-листы, социальные сигналы |
| **Code execution matters** | В skill можно включить реальные скрипты — большое преимущество |
| **Cross-platform wins** | Skill работает на Claude, Codex, Copilot — покрываем всё |
| **Trigger quality > quantity** | Хорошее description важнее длинных инструкций |
| **Community matters** | Нужно активное community engagement |

---

## 4. Другие Платформы

### 4.1. npx skills add

**Как работает:**
```bash
# Установка через npx — без глобальной установки
npx skills add your-username/your-skill-name

# Что происходит:
# 1. npx проверяет локальную установку
# 2. Если нет — временно загружает из npm registry
# 3. Выполняет команду
# 4. Очищает временные файлы
```

**Преимущества npx-дистрибуции:**
- Нет необходимости глобальной установки
- Всегда актуальная версия
- Работает в любом проекте
- Простота для пользователя

### 4.2. npm Distribution

**Подход:**
- Публикация skill'а как npm-пакета
- В package.json указать `bin` для CLI
- Пользователи устанавливают: `npm install -g @your-org/deep-research-skill`

**Преимущества:**
- Semantic versioning из коробки
- Dependency management
- Широкая экосистема
- CI/CD интеграция

### 4.3. Cursor Marketplace

**Технические детали:**
- Cursor использует **OpenVSX** (Eclipse Foundation), а не Microsoft Marketplace
- Совместимость с VS Code extensions (.vsix формат)
- Некоторые Microsoft extensions недоступны из-за лицензионных ограничений
- Extensions можно устанавливать из VSIX вручную

**Особенности для skills:**
- Cursor поддерживает Agent Skills стандарт (agentskills.io)
- Skills читаются из `.cursor/skills/` или `.claude/skills/`
- Progressive disclosure работает аналогично

### 4.4. VS Code Extensions для Research

**Популярные research-related extensions:**

| Extension | Установки | Назначение |
|-----------|-----------|------------|
| **Jupyter** | 100M+ | Data analysis, notebooks |
| **Python** | 150M+ | Python development |
| **Markdown All in One** | 10M+ | Markdown editing |
| **Rainbow CSV** | 5M+ | CSV visualization |
| **GitLens** | 30M+ | Git analysis |
| **Prettier** | 50M+ | Code formatting |

**Ключевой вывод:** VS Code marketplace — для editor extensions, не для agent skills. Наш фокус — на skill marketplaces (Claude, Codex, Copilot).

---

## 5. Distribution Strategy для Deep Research Skill

### 5.1. Multi-Platform Approach

**Tier 1: Основные платформы (обязательно)**

| Платформа | Priority | Формат | Установка |
|-----------|----------|--------|-----------|
| **Claude Code** | P0 | SKILL.md + marketplace.json | `/plugin marketplace add` |
| **Claude.ai web** | P0 | SKILL.md | Settings → Capabilities → Skills |
| **OpenAI Codex CLI** | P1 | SKILL.md + openai.yaml | `$skill-installer` |
| **GitHub Copilot** | P1 | SKILL.md в `.github/skills/` | Авто-обнаружение |
| **Cursor** | P1 | SKILL.md в `.cursor/skills/` | Авто-обнаружение |

**Tier 2: Расширение reach**

| Канал | Priority | Действие |
|-------|----------|----------|
| **TrendShift** | P2 | Мониторинг + badge на репозитории |
| **skills.sh (Vercel)** | P2 | Каталог + Snyk security scanning |
| **skillsmp.com** | P2 | Community marketplace |
| **Awesome-листы** | P2 | PR в awesome-claude-skills |
| **npm registry** | P2 | Пакет для programmatic access |

### 5.2. Versioning Strategy

**Semantic Versioning для skills:**
```
v1.0.0  # Initial release
v1.1.0  # New features (новые источники данных)
v1.2.0  # New features (новые форматы вывода)
v2.0.0  # Breaking changes (новая архитектура)
```

**GitHub Releases:**
```bash
# Создание релиза
git tag -a v1.0.0 -m "Initial Deep Research Skill release"
git push origin v1.0.0

# Пользователи устанавливают конкретную версию:
gh skill install owner/repo@v1.0.0 --agent claude-code
```

**Branch strategy:**
- `main` — стабильная версия
- `develop` — разработка
- `feature/*` — новые фичи
- `release/v1.x` — релизные ветки

### 5.3. Updates & Maintenance

**Автоматические обновления:**
```bash
# Пользователи могут обновлять:
gh skill update --all

# Или для конкретного skill'а:
gh skill update deep-research
```

**Breaking changes communication:**
- CHANGELOG.md в репозитории
- GitHub Releases с описанием
- Migration guides для major versions
- Deprecation warnings в skill'е

### 5.4. Success Metrics

| Метрика | Целевое значение | Срок |
|---------|-----------------|------|
| GitHub Stars | 1,000 | 3 месяца |
| Установок (Claude Code) | 500 | 3 месяца |
| Forks | 100 | 3 месяца |
| PR от community | 20 | 3 месяца |
| TrendShift ranking (AI skills) | Top 50 | 6 месяцев |
| Cross-platform adoption | 3+ платформы | 3 месяца |

### 5.5. План запуска

**Phase 1: Foundation (Week 1-2)**
- [ ] Создать SKILL.md по спецификации agentskills.io
- [ ] Настроить .claude-plugin/marketplace.json
- [ ] Создать README.md с примерами использования
- [ ] Добавить LICENSE (Apache 2.0)
- [ ] Пройти валидацию на agentskills.io
- [ ] Опубликовать на GitHub

**Phase 2: Claude Ecosystem (Week 2-3)**
- [ ] Отправить PR в anthropics/skills
- [ ] Добавить в community marketplaces (skillsmp.com, skills.sh)
- [ ] Создать marketplace-публикацию
- [ ] Написать блог-пост о skill'е

**Phase 3: Cross-Platform (Week 3-4)**
- [ ] Тестирование на OpenAI Codex CLI
- [ ] Адаптация для GitHub Copilot (.github/skills/)
- [ ] Тестирование на Cursor
- [ ] Публикация в awesome-листы

**Phase 4: Growth (Month 2-3)**
- [ ] TrendShift badge на репозитории
- [ ] Community engagement (Reddit, Discord, X)
- [ ] Демо-видео использования
- [ ] Guest posts в AI-блогах
- [ ] Коллекция use cases от пользователей

**Phase 5: Scale (Month 3-6)**
- [ ] npm пакет для programmatic access
- [ ] Интеграция с CI/CD
- [ ] Enterprise features (team skills)
- [ ] Monetization exploration

---

## 6. Ключевые Находки

### 6.1. Главные выводы

1. **Skills — это новый npm**: Agent Skills стали стандартом де-факто для расширения AI-агентов. Это масштабируемая экосистема, а не временный тренд.

2. **Open standard wins**: Спецификация agentskills.io принята Claude Code, OpenAI Codex, GitHub Copilot, Cursor, Gemini CLI и 16+ другими платформами. Skill написанный сегодня работает везде.

3. **#AI skills — топ-3 тренд**: На TrendShift категория AI skills набирает 1.6k stars/day, что подтверждает огромный спрос.

4. **Description — ключ к success**: Поле `description` в SKILL.md определяет, будет ли skill активирован. Это важнее длинных инструкций.

5. **Progressive disclosure — killer feature**: В отличие от GPTs, skills загружаются progressively, что позволяет иметь сотни skills без перегрузки контекста.

6. **gh skill — будущее**: GitHub CLI с подкомандами `gh skill install/publish/update` становится стандартным инструментом distribution (2026 Q2).

7. **Security matters**: 13.4% skills имеют критические проблемы. Snyk сканирование и `allowed-tools` — необходимость.

### 6.2. Рекомендации

1. **Начать с Claude Code** — самая зрелая экосистема (147k stars на anthropics/skills)
2. **Использовать open standard** — SKILL.md agentskills.io для cross-platform compatibility
3. **Фокус на description quality** — тестировать trigger reliability с 5+ разными формулировками
4. **Публиковать на GitHub** — основной канал discovery
5. **Мониторить TrendShift** — для early signal detection и competitive intelligence
6. **Планировать cross-platform** — сразу думать о Claude, Codex, Copilot, Cursor
7. **Версионирование через GitHub Releases** — immutable releases для enterprise adoption

---

## 7. Ресурсы

### 7.1. Ссылки

| Ресурс | URL | Назначение |
|--------|-----|------------|
| TrendShift | https://trendshift.io/ | Тренды OSS |
| Agent Skills Spec | https://agentskills.io/ | Спецификация |
| Anthropic Skills | https://github.com/anthropics/skills | Официальный репозиторий |
| Skills.sh | https://skills.sh/ | Каталог от Vercel |
| SkillsMP | https://skillsmp.com/ | Community marketplace |
| OpenAI Codex Skills | https://developers.openai.com/codex/skills | Документация Codex |
| Microsoft Agent Skills | https://learn.microsoft.com/en-us/agent-framework/agents/skills | MS docs |

### 7.2. Установочные команды для пользователей

```bash
# Claude Code
/plugin marketplace add your-org/deep-research-skill
/plugin install deep-research

# Или через npx
npx skills add your-org/deep-research-skill

# GitHub CLI (2026+)
gh skill install your-org/deep-research-skill --agent claude-code

# Codex CLI
$skill-installer your-org/deep-research-skill

# Manual (любая платформа)
git clone https://github.com/your-org/deep-research-skill.git
# Скопировать SKILL.md в .claude/skills/ или .codex/skills/ или .github/skills/
```

---

*Исследование выполнено: 2026-05-20*
*Следующий шаг: Создание SKILL.md и публикация в ecosystem*
