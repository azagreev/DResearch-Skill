# Browserbase Skills: Deep Research Report

## Исследование для интеграции в Deep Research Skill

**Дата исследования:** Июнь 2026
**Источники:** skills.sh, browserbase.com, GitHub, веб-поиск
**Цель:** Определить архитектурные паттерны, возможности и стратегию интеграции Browserbase Skills в наш Deep Research Skill

---

## 1. Browser-Trace Skill (Детальный разбор)

### 1.1 Что это такое

**Browser-trace** — skill для **наблюдения** (трассировки) браузерных сессий через CDP (Chrome DevTools Protocol). Это **read-only** инструмент, который:

- Подключается как **второй, read-only CDP клиент** к уже запущенной браузерной сессии
- Записывает полный поток DevTools-событий в NDJSON
- Параллельно делает скриншоты и DOM-дампы
- Разрезает всё на структурированное дерево директорий для поиска

**Ключевой принцип:** skill не управляет браузером — он только слушает. Для управления используется browser skill, browse CLI, Stagehand, Playwright.

### 1.2 Архитектура (3 компонента)

```
+------------+     +------------+     +------------+
|  Firehose  | --> |  Sampler   | --> |  Bisector  |
+------------+     +------------+     +------------+
| browse cdp |     | скриншоты  |     | raw.ndjson |
| поток CDP  |     | DOM-дампы  |     | --> buckets|
| событий    |     | (каждые 2с)|     | по страницам
+------------+     +------------+     +------------+
```

1. **Firehose** — `browse cdp <target>` стримит каждое CDP-событие как JSON-объект в `cdp/raw.ndjson`
2. **Sampler** — polling-цикл делает скриншоты (`browse screenshot --cdp`) и DOM-дампы (`browse get html body`) с интервалом (по умолчанию 2 сек)
3. **Bisector** — `bisect-cdp.mjs` проходит `raw.ndjson` и разрезает на bucket-файлы по CDP-методам и по страницам (границы — `Page.frameNavigated`)

### 1.3 Структура выходных данных

```
.o11y/
  <run-id>/
    manifest.json          # метаданные сессии
    cdp/
      raw.ndjson           # полный поток CDP
      summary.json         # сводка сессии
      network/
        requests.jsonl     # сгруппированные запросы
        responses.jsonl    # сгруппированные ответы
        failed.jsonl       # неудачные запросы
      console/
        logs.jsonl         # логи консоли
      page/
        navigations.jsonl  # навигации
      runtime/
        ...
      pages/<pid>/         # per-page данные
    screenshots/           # скриншоты с таймстампами
    dom/                   # DOM-дампы
    index.jsonl            # индекс скриншотов
```

### 1.4 Интеграция с Browserbase (удалённые сессии)

Для работы с Browserbase используются два хелпера:

- **`bb-capture.mjs`** — создаёт/подключается к сессии и запускает трассировку
- **`bb-finalize.mjs`** — вытягивает артефакты платформы (метаданные, логи, скачивания)

**Важно:** Browserbase завершает сессию, когда последний CDP-клиент отключается. Поэтому:
1. Создавать сессию с `--keep-alive`
2. Подключать основной automation client до (или вместе с) tracer
3. Использовать `bb-capture.mjs --new` для создания keep-alive сессии

### 1.5 Интеграция с Claude

Skill использует **Bash tool** для запуска CLI-команд (`browse cdp`, `node scripts/...`). Claude не напрямую управляет CDP — он вызывает shell-команды, которые взаимодействуют с браузером.

**Allowed tools:** Bash, Read, Grep

### 1.6 Когда использовать

- Отладка browser-automation (падающие формы, отсутствие элементов, зависшие навигации)
- Аттач трассировки mid-flight без перезапуска
- Анализ network/console/DOM/Page событий
- Получение скриншотов + DOM snapshots с привязкой к CDP-событиям по таймстампу

### 1.7 Метрики популярности

- **Installs:** 2.1K
- **GitHub Stars:** 3.5K
- **First Seen:** Apr 27, 2026
- **Security Audits:** Pass (Gen Agent Trust Hub, Socket), Warn (Snyk)

---

## 2. Browserbase Platform (Полный обзор)

### 2.1 Что такое Browserbase

**Browserbase** — managed cloud platform для AI-агентов, которая предоставляет:

- **Cloud browsers** — управляемые браузерные сессии с CDP-доступом
- **Web Search API** — быстрый поиск для агентов
- **Fetch API** — получение контента страниц как markdown/HTML/JSON
- **Functions** — serverless развёртывание browser-автоматизаций
- **Model Gateway** — роутинг запросов к 100+ LLM-провайдерам

**Слоган:** "Give your agents access to the whole web."

### 2.2 Ключевые API

| API | Описание | Пример использования |
|-----|----------|----------------------|
| **Browser API** | Создание, контроль, наблюдение за сессиями | `browse open <url> --remote` |
| **Search API** | Быстрый поиск, заточенный под агентов | `browse cloud search "query"` |
| **Fetch API** | Получение страниц как markdown/JSON | `browse cloud fetch <url>` |
| **Functions** | Serverless деплой автоматизаций | `browse functions deploy` |

### 2.3 Stealth & Anti-Detection Capabilities

#### Identity / Verified Browsers
- **Browserbase Identity** — persistent identity с cookies, localStorage, fingerprint
- **Verified browsers** — проходят проверку CAPTCHA и anti-bot
- **Browserbase Verified** — браузеры с "хорошей репутацией" для обхода bot detection

#### Proxies
- **Residential proxies** — 201 страна, гео-таргетинг
- **Auto-detection timezone/locale** по IP прокси
- **1-5+ GB** прокси-трафика в зависимости от плана

#### CAPTCHA Solving
- **Automatic CAPTCHA solving** — reCAPTCHA, hCaptcha обрабатываются автоматически
- **No CAPTCHA services** — решение происходит через browser automation

#### Anti-Detection Features
- CDP-совместимость (не Playwright shim)
- Native Chrome DevTools Protocol (меньше automation footprint)
- Custom extensions support
- Session persistence через contexts

### 2.4 Session Management

**Session lifecycle:**
```
1. Create session (with --keep-alive for remote)
2. Get connectUrl (CDP WebSocket URL)
3. Attach automation client(s)
4. Attach browser-trace (optional)
5. Run automation
6. Stop trace, finalize, release (optional --release)
```

**Key commands:**
- `browse open <url> --remote` — создать сессию
- `browse cloud sessions list` — список сессий
- `browse cloud sessions get <id>` — информация о сессии
- `browse cloud sessions logs <id>` — логи сессии
- `--keep-alive` — предотвращает авто-закрытие
- `--session <name>` — именование локальной сессии

### 2.5 Browse CLI (Ключевой интерфейс)

**Установка:** `npm install -g browse`

**Команды:**
| Команда | Описание |
|---------|----------|
| `browse open <url>` | Открыть URL |
| `browse snapshot` | Получить accessibility tree + refs |
| `browse click <ref>` | Клик по ref из snapshot |
| `browse type <text>` | Ввод текста |
| `browse fill <sel> <val>` | Заполнить поле |
| `browse screenshot` | Скриншот |
| `browse get <selector>` | Получить элемент |
| `browse cdp <target>` | CDP firehose |
| `browse stop` | Остановить демон |
| `browse status` | Проверить статус |

**Режимы:**
- `--local` — локальный Chrome
- `--remote` — Browserbase cloud
- `--auto-connect` — подключиться к запущенному Chrome
- `--cdp <port|url>` — подключиться к CDP target

### 2.6 Cost Model (Pricing)

| Plan | Price | Concurrent | Browser Hours | Search | Fetch | Proxies |
|------|-------|-----------|---------------|--------|-------|---------|
| **Free** | $0/mo | 3 | 1 hour | 1K | 1K | — |
| **Developer** | $20/mo | 25 | 100 hrs | 1K | 1K | 1 GB |
| **Startup** | $99/mo | 100 | 500 hrs | 1K | 10K | 5 GB |
| **Scale** | Custom | 250+ | 500+ | 10K+ | 10K+ | 5+ GB |

**Overages:**
- Browser hours: $0.10-0.12/hr
- Search: $7/1K calls
- Fetch: $1-4/1K calls (with proxies: $4-7/1K)
- Proxies: $10-12/GB

---

## 3. Skills.sh Platform (Полный обзор)

### 3.1 Что такое Skills.sh

**Skills.sh** — это **open-source marketplace** для AI agent skills, созданный Vercel.

- **Каталог:** leaderboard skills по популярности
- **CLI:** `npx skills add <owner>/<repo> --skill <name>`
- **Телеметрия:** анонимная, только для ранжирования
- **Агенты:** Claude Code, Cursor, Codex, GitHub Copilot, Windsurf, Gemini, Cline

### 3.2 Формат Skill-файлов (SKILL.md)

Каждый skill — это GitHub-репозиторий с файлом `SKILL.md` и дополнительными ресурсами.

**Frontmatter (YAML metadata):**
```yaml
name: browser-trace
description: Capture a full DevTools-protocol trace...
compatibility: Requires Node 18+, the browse CLI...
license: MIT
allowed-tools: Bash, Read, Grep
metadata:
  openclaw:
    requires:
      bins: browse
    install:
      kind: package
      bins: node
    homepage: https://github.com/browserbase/skills
```

**Структура SKILL.md:**
1. **Frontmatter** — метаданные (name, description, compatibility, license, allowed-tools)
2. **H1 заголовок** — название skill
3. **Краткое описание** — что делает
4. **When to use** — сценарии использования
5. **Setup check** — проверка окружения
6. **How it works** — архитектура
7. **Quickstart** — примеры команд
8. **Best practices** — рекомендации
9. **Troubleshooting** — типичные проблемы

### 3.3 Как Skills подключаются

```bash
# Установка
npx skills add browserbase/skills --skill browser-trace

# Что происходит:
1. CLI клонирует/скачивает репозиторий
2. Извлекает указанный skill из поддиректории skills/
3. Регистрирует skill для AI агента
4. Отправляет анонимную телеметрию (skill name + timestamp)
```

### 3.4 Интеграция с Claude Code

Skills работают через **Claude Code context**:
- SKILL.md добавляется в системный промпт
- Команды (Bash, Read, Grep) выполняются через Claude Code tools
- Skill предоставляет **procedural knowledge** — какие команды использовать и когда

### 3.5 Каталог доступных skills (browserbase/skills)

| Skill | Installs | Описание |
|-------|----------|----------|
| **browser** | 4.4K | Браузерная автоматизация через browse CLI |
| **browserbase-cli** | 2.1K | CLI для Functions и platform API |
| **browser-trace** | 2.1K | CDP-трассировка сессий |
| **fetch** | 2.1K | Fetch API — получение страниц без браузера |
| **functions** | 2.0K | Serverless деплой автоматизаций |
| **search** | 2.0K | Web search API |
| **ui-test** | 2.0K | UI-тестирование |
| **autobrowse** | 1.9K | Автоматический browsing |
| **cookie-sync** | 1.8K | Синхронизация cookies |
| **company-research** | 1.5K | Исследование компаний |
| **event-prospecting** | 1.3K | Проспектинг событий |
| **browser-to-api** | 1.1K | Конвертация browser в API |
| **safe-browser** | 987 | Безопасный browser с allowlist |
| **what-antibot** | 280 | Детектор anti-bot систем |

**Всего:** 17 skills, 25.8K total installs

---

## 4. Сравнение с конкурентами

### 4.1 Browserbase vs Obscura (Rust headless)

| Критерий | Browserbase | Obscura |
|----------|-------------|---------|
| **Язык** | Node.js/Cloud | Rust |
| **Размер** | Cloud service | ~70 MB binary |
| **Память** | Cloud-managed | ~30 MB |
| **Запуск** | API call | Instant |
| **CDP** | Полная поддержка | Full CDP-compatible |
| **Stealth** | Verified browsers | Built-in --stealth |
| **Anti-bot** | CAPTCHA solving, proxies | Anti-fingerprinting, tracker blocking |
| **Модель** | SaaS ($0-99+/mo) | Open-source, self-hosted |
| **Лучше для** | Production, scalability | Локальное использование, скорость |

**Вывод:** Obscura — лучше для локальной разработки, Browserbase — для production и обхода сложной защиты.

### 4.2 Browserbase vs CloakBrowser

| Критерий | Browserbase | CloakBrowser |
|----------|-------------|--------------|
| **Подход** | Cloud browsers | Patched Chromium (49 C++ модификаций) |
| **Playwright** | Через browse CLI | Drop-in replacement |
| **Anti-detection** | Verified + proxies | Source-level fingerprint patches |
| **Human-like** | Нет | Bezier mouse, natural keyboard, scroll physics |
| **CAPTCHA** | Auto-solving | Prevention (no CAPTCHA appears) |
| **Модель** | SaaS | Open-source (free) |
| **reCAPTCHA score** | Н/Д | 0.9 |
| **Лучше для** | Облачная автоматизация | Локальный anti-detect browsing |

**Вывод:** CloakBrowser — лучше для локального anti-detect browsing с human-like поведением. Browserbase — для облачного масштабирования.

### 4.3 Browserbase vs Playwright/Puppeteer

| Критерий | Browserbase | Playwright/Puppeteer |
|----------|-------------|----------------------|
| **Тип** | Managed platform | Библиотека |
| **Инфраструктура** | Cloud | Self-hosted |
| **Stealth** | Verified browsers, proxies | Требует stealt-плагинов |
| **CAPTCHA** | Built-in solving | Требует внешних сервисов |
| **CDP** | Full access | Full access |
| **Session mgmt** | Cloud-native | Ручное |
| **Proxy** | Built-in residential | Требует настройки |
| **Лучше для** | Production AI agents | Разработка, кастомные решения |

**Вывод:** Playwright — для полного контроля и кастомизации. Browserbase — для быстрого старта и production.

### 4.4 Browserbase vs Firecrawl

| Критерий | Browserbase | Firecrawl |
|----------|-------------|-----------|
| **Фокус** | Browser automation + AI agents | Web scraping + data extraction |
| **API** | Browser, Search, Fetch, Functions | Scrape, Crawl, Search, Map, Agent |
| **Output** | Markdown, HTML, JSON, скриншоты | Markdown, JSON, скриншоты |
| **Anti-blocking** | Verified browsers, CAPTCHA solving | 96% coverage, rotating proxies |
| **Browser control** | Full (click, type, navigate) | Actions (click, scroll, type, wait) |
| **Speed** | Browser session | P95 3.4s latency |
| **AI Agent** | Functions + Model Gateway | FIRE-1 Agent, Deep Research API |
| **Модель** | Pay per session/hour | Pay per credit |
| **Open-source** | CLI частично | Core open-source |
| **Цена** | $0-99+/mo | $0-599+/mo |

**Вывод:** Firecrawl — лучше для pure scraping. Browserbase — для interactive browser automation.

### 4.5 Сводная матрица

| Задача | Browserbase | CloakBrowser | Firecrawl | Obscura | Playwright |
|--------|-------------|--------------|-----------|---------|------------|
| **Simple scraping** | + | ++ | +++ | ++ | + |
| **Anti-detect** | ++ | +++ | ++ | ++ | + |
| **Interactive browsing** | +++ | ++ | + | ++ | +++ |
| **CAPTCHA solving** | +++ | +++ | + | + | + |
| **Scale/Cloud** | +++ | + | +++ | + | ++ |
| **Cost-effective** | + | +++ | ++ | +++ | ++ |
| **Speed** | ++ | ++ | +++ | +++ | ++ |
| **AI Agent ready** | +++ | + | +++ | ++ | ++ |

---

## 5. Паттерны для переиспользования

### 5.1 Архитектурные решения из browser-trace

1. **CDP Read-only Observer Pattern**
   - Подключаться как второй CDP-клиент (не мешать основному)
   - Только observation domains: Network, Console, Runtime, Log, Page
   - Никогда не отправлять action-команды

2. **Firehose + Bisect Pattern**
   - Записывать raw stream в NDJSON
   - Пост-обработка разрезкой на bucket-файлы
   - Per-page группировка по navigation events

3. **Sampler Pattern**
   - Параллельный polling скриншотов + DOM-дампов
   - Таймстампная синхронизация с CDP-событиями

4. **Query Interface**
   - Единый `query.mjs <run-id> <command>` для исследования
   - Команды: list, page, errors, hosts, summary

### 5.2 Архитектурные решения из browser skill

1. **Local vs Remote Environment Selection**
   - Авто-определение по env var (BROWSERBASE_API_KEY)
   - Явные флаги `--local`, `--remote`, `--auto-connect`
   - Fallback с remote на local при ошибках

2. **Session Persistence**
   - `--keep-alive` для предотвращения авто-закрытия
   - Именование сессий через `--session`
   - Context-based cookie/auth persistence

3. **Snapshot-based Interaction**
   - `browse snapshot` для получения accessibility tree
   - Ref-based клики (`browse click @0-5`)
   - Confirm-after-action паттерн

4. **Snapshot Ref Pattern**
   - Refs из accessibility tree для стабильной идентификации элементов
   - Не зависеть от CSS-селекторов (часто меняются)

### 5.3 Формат SKILL.md (для нашего skill)

```yaml
name: deep-research-browser
description: Deep web research using multiple browser backends...
compatibility: Requires Node 18+, browse CLI, optional BROWSERBASE_API_KEY...
license: MIT
allowed-tools: Bash, Read, Grep, Edit
```

### 5.4 Команды для интеграции

```bash
# Установка skill
npx skills add https://github.com/browserbase/skills --skill browser
npx skills add https://github.com/browserbase/skills --skill browser-trace
npx skills add https://github.com/browserbase/skills --skill fetch
npx skills add https://github.com/browserbase/skills --skill search
```

---

## 6. Integration Architecture

### 6.1 Как Browserbase интегрируется в Deep Research Skill

```
+---------------------------------------------+
|         Deep Research Skill                 |
+---------------------------------------------+
|                                             |
|  +-------------------------------------+    |
|  |     Research Orchestrator           |    |
|  |  (plan → execute → synthesize)      |    |
|  +-------------------------------------+    |
|                   |                         |
|       +-----------+-----------+             |
|       |                       |             |
|  +----v----+            +----v----+        |
|  | Search  |            | Browse  |        |
|  | Module  |            | Module  |        |
|  +----+----+            +----+----+        |
|       |                       |             |
|       |          +------------v----------+  |
|       |          |   Browser Backend     |  |
|       |          |   Abstraction Layer   |  |
|       |          +------------+----------+  |
|       |                       |             |
|       |   +---------+---------+--------+    |
|       |   |         |         |        |    |
|       | Browser Obscura Cloak  Firecrawl |    |
|       | (cloud)  (local) (local) (API)  |    |
|       +---------------------------------+    |
|                                             |
|  +-------------------------------------+    |
|  |     browser-trace (optional)        |    |
|  |     CDP tracing for debugging       |    |
|  +-------------------------------------+    |
|                                             |
+---------------------------------------------+
```

### 6.2 Fallback Chain (Стратегия отказоустойчивости)

```
При ошибке на каждом уровне — fallback:

1. Browserbase (cloud) →
2. Obscura (local, Rust) →
3. CloakBrowser (local, anti-detect) →
4. Firecrawl (API, no browser) →
5. Direct HTTP fetch (curl)

Критерии fallback:
- Browserbase fails (timeout, CAPTCHA не пройден, API error)
- Стоимость превышает лимит
- Требуется локальное выполнение
- Сайт требует anti-detect (CloakBrowser лучше)
- Только статический контент (Firecrawl быстрее)
```

### 6.3 Session Reuse Strategies

1. **Context Persistence**
   - Browserbase contexts для сохранения cookies/auth между сессиями
   - Cookie-sync skill для синхронизации local → cloud

2. **Keep-Alive Sessions**
   - `--keep-alive` для длительных research-сессий
   - `--timeout` настраивается под длительность research

3. **Session Pool**
   - Пул Browserbase сессий для параллельных исследований
   - Reuse для одинаковых доменов (сохраняется кэш, cookies)

4. **browser-trace для дебага**
   - Attach trace к проблемным сессиям
   - Bisect для анализа network/console errors

### 6.4 Cost-Benefit Analysis

| Backend | Cost | Speed | Anti-detect | Лучший юзкейс |
|---------|------|-------|-------------|---------------|
| **Browserbase** | $0.12/hr | Medium | Good | Interactive sites, auth required |
| **Obscura** | Free | Fast | Medium | Local dev, speed-critical |
| **CloakBrowser** | Free | Medium | Excellent | Anti-detect required |
| **Firecrawl** | $0.0005/page | Very Fast | Good | Static content, bulk scraping |
| **Direct HTTP** | Free | Fastest | None | Simple API endpoints |

**Рекомендуемая стратегия:**
- Начинать с **Firecrawl** для статического контента
- Переходить на **Browserbase** для interactive browsing
- Использовать **CloakBrowser** как fallback для anti-detect
- **Obscura** для локальной разработки

### 6.5 Практические рекомендации для Deep Research Skill

1. **Использовать company-research skill как референс**
   - Plan → Research → Synthesize паттерн
   - Выход в ~/Desktop/{slug}_research_{date}/
   - Markdown + CSV выход

2. **Интегрировать browser-trace для дебага**
   - Трассировка сложных research-задач
   - Анализ failed requests, JS errors

3. **Использовать search skill для discovery**
   - Быстрый поиск релевантных URL
   - Fetch для получения контента

4. **Fallback chain в коде**
   - Try Browserbase → Obscura → CloakBrowser → Firecrawl
   - Configurable priority order

5. **Session reuse для multi-page research**
   - Keep-alive сессии для одного домена
   - Context persistence для auth

---

## 7. Ключевые находки (Summary)

### Что важно для нашего Deep Research Skill

1. **Browserbase — не просто браузер, а платформа** с Search, Fetch, Functions, Model Gateway. Это даёт нам multiple entry points.

2. **browser-trace — уникальный инструмент** для дебага. Read-only CDP observer pattern можно переиспользовать для аудита research-сессий.

3. **Skills.sh формат (SKILL.md) — простой и мощный**:
   - YAML frontmatter + Markdown документация
   - Описание when-to-use, setup check, troubleshooting
   - Bash-команды для интеграции

4. **Fallback chain обязателен**:
   - Ни один backend не покрывает все сценарии
   - Browserbase для cloud, CloakBrowser для anti-detect, Firecrawl для speed

5. **Cost optimization**:
   - Firecrawl для bulk/static scraping
   - Browserbase только для interactive
   - Session reuse через keep-alive + contexts

6. **Browse CLI — унифицированный интерфейс**:
   - Одни команды для local и remote
   - `--cdp` для подключения к любому CDP target
   - Интеграция с Playwright, Stagehand, Puppeteer

7. **17 skills от browserbase** — готовая экосистема, которую можно компоновать:
   - browser (4.4K installs) — основа
   - search (2.0K) — discovery
   - fetch (2.1K) — content extraction
   - browser-trace (2.1K) — debugging
   - company-research (1.5K) — research pattern reference

---

## 8. Рекомендации по реализации

### Phase 1: MVP Integration
- Интегрировать browser + search skills
- Fallback: Browserbase → Firecrawl

### Phase 2: Advanced Features
- Добавить browser-trace для дебага
- Session reuse с contexts

### Phase 3: Full Ecosystem
- CloakBrowser fallback для anti-detect
- Obscura для локальной разработки
- Custom skill packaging

---

*Исследование завершено. Рекомендуется начать с browser + search skills как основы Deep Research Skill, с fallback на Firecrawl для статического контента.*
