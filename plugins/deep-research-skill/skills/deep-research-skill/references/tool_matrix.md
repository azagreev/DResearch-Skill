# Tool Matrix: Deep Research Skill for Claude Desktop

> **Version:** 1.0 | **Date:** 2025-01-20 | **Skill:** Deep Research Skill
>
> Этот документ описывает полную матрицу инструментов для агента глубокого исследования, включая стратегии fallback, оценку стоимости и алгоритм выбора инструмента.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Tool Matrix](#2-tool-matrix)
3. [Data Sources Matrix](#3-data-sources-matrix)
4. [Cost Estimation Formula](#4-cost-estimation-formula)
5. [Tool Selection Algorithm](#5-tool-selection-algorithm)
6. [Hybrid Fallback Chains](#6-hybrid-fallback-chains)
7. [Cost-Aware Execution Budgets](#7-cost-aware-execution-budgets)
8. [Anti-Patterns & Guardrails](#8-anti-patterns--guardrails)
9. [Integration with SKILL.md Phases](#9-integration-with-skillmd-phases)

---

## 1. Architecture Overview

### Philosophy: Cost-First Hierarchical Execution

Deep Research Skill следует философии **"start cheap, escalate expensive"** (начни дёшево, эскалируй дорого), вдохновлённой Fintech Discovery Scraping Skill. Каждый subtask проходит через иерархию инструментов от бесплатных к премиум, пока не будет достигнут критерий качества.

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│  LAYER 1: NATIVE (Free — built into Claude Desktop) │
│  web_search, browser_*, ipython, shell, file_*      │
├─────────────────────────────────────────────────────┤
│  LAYER 2: EFFICIENT (Low cost — API wrappers)       │
│  Jina AI Reader, Jina Search, curl/requests          │
├─────────────────────────────────────────────────────┤
│  LAYER 3: PREMIUM (High cost — silver bullet)       │
│  Firecrawl API, Jina DeepSearch                      │
└─────────────────────────────────────────────────────┘
```

### Decision Flow

```
Subtask received
       │
       ▼
┌──────────────────────┐
│  Is structured data  │
│  source available?   │
│  (Yahoo/IMF/arXiv/   │
│   Scholar/World Bank)│
└───┬────────────┬─────┘
    │YES         │NO
    ▼            ▼
Use Datasource  ┌──────────────────────┐
(Free, fast)    │  Is it a search      │
                │  or navigation task? │
                └───┬────────┬─────────┘
                    │YES     │NO
                    ▼        ▼
              ┌──────────┐ ┌──────────────────────┐
              │ Layer 1  │ │  Does page need      │
              │ web_     │ │  JavaScript render?  │
              │ search/  │ │  or is behind        │
              │ browser  │ │  bot protection?     │
              └────┬─────┘ └───┬────────┬─────────┘
                   │           │YES     │NO
                   │           ▼        ▼
                   │     ┌──────────┐ ┌──────────┐
                   │     │ Layer 3  │ │ Layer 2  │
                   │     │ Firecrawl│ │ Jina     │
                   │     │ or Jina  │ │ Reader / │
                   │     │ DeepSea- │ │ curl     │
                   │     │ rch      │ └────┬─────┘
                   │     └────┬─────┘      │
                   │          │            │
                   └──────────┴────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ Quality gate passed?│
                   │ (content_complete   │
                   │  checkpoint)        │
                   └───┬────────┬────────┘
                       │YES     │NO
                       ▼        ▼
                    Return   Escalate to
                    result   next tier
```

---

## 2. Tool Matrix

### 2.1 Web Search & Discovery

#### 2.1.1 `mshtools-web_search`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-web_search |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Быстрый (~1-3 сек) |
| **Когда использовать** | • Первичный поиск источников по ключевым словам<br>• Поиск актуальных новостей и событий<br>• Поиск конкретных сайтов или организаций<br>• Разведка темы перед глубоким анализом<br>• Поиск определений, фактов, дат |
| **Когда НЕ использовать** | • Нужно содержимое целой страницы (только сниппеты)<br>• Поиск по изображениям или видео<br>• Нужна структурированная выгрузка с сайта<br>• Работа с paywall/требующими авторизацию страницами<br>• Поиск по научным статьям (используй arXiv/Scholar) |
| **Fallback-цепочка** | `web_search` → `mshtools-search_image_by_text` (если нужны визуальные данные) → `s.jina.ai` (если нужен более чистый результат) → `firecrawl_search` (если нужны структурированные данные) |
| **Input/Output** | **Input:** `queries: string[]` — список поисковых запросов<br>**Output:** Список результатов поиска с заголовками, URL, сниппетами |
| **Rate limits** | Не документированы; предположительно ~100 запросов/сессия. Практика показывает устойчивость к нагрузке. |
| **Пример** | `web_search({"queries": ["renewable energy investment trends 2024", "clean energy venture capital funding"}]})` |

#### 2.1.2 `Jina AI Search (s.jina.ai)`

| Attribute | Value |
|-----------|-------|
| **Название** | Jina AI Search (s.jina.ai) |
| **Tier стоимости** | 2 (низкая — требует бесплатного API ключа, 1M free tokens) |
| **Латентность** | Быстрый (~2.5 сек) |
| **Когда использовать** | • Нужен поиск + чистый markdown результат в одном запросе<br>• `web_search` возвращает слишком много шума<br>• Нужно до 20 результатов с чистым контентом<br>• Поиск с фильтрами по домену, языку, типу файла<br>• Нужен поиск + извлечение за один вызов |
| **Когда НЕ использовать** | • Нет API ключа (Reader работает без ключа, Search — нет)<br>• Нужен интерактивный поиск по странице<br>• Нужен JavaScript рендеринг сложных SPA<br>• Rate limit 100 RPM может быть превышен |
| **Fallback-цепочка** | `web_search` → `s.jina.ai` (если нужен чистый контент) → `firecrawl_search` (если нужна структурированная выгрузка) |
| **Input/Output** | **Input:** `q: string`, опционально `count`, `language`, `site:`, `filetype:` и др.<br>**Output:** JSON с результатами поиска — заголовок, URL, чистый markdown контент |
| **Rate limits** | 100 RPM с free/paid API key; 1000 RPM с premium key. Фиксированная стоимость: 10,000 tokens/запрос. |
| **Пример** | `curl -H "Authorization: Bearer KEY" "https://s.jina.ai/search?q=renewable+energy+investment+2024&count=10"` |

#### 2.1.3 `Firecrawl Search`

| Attribute | Value |
|-----------|-------|
| **Название** | Firecrawl Search API |
| **Tier стоимости** | 4 (высокая — 2 credits/10 результатов; ~$0.003/результат на Free tier) |
| **Латентность** | Средний (~3-5 сек) |
| **Когда использовать** | • Нужны структурированные результаты поиска с метаданными<br>• Нужен поиск + scrape в одной цепочке<br>• `web_search` и `s.jina.ai` не дали качественных результатов<br>• Нужна семантическая выдача (AI-ранжирование)<br>• Silver bullet для discovery-фазы |
| **Когда НЕ использовать** | • Только разведка темы (слишком дорого)<br>• Нужен быстрый ответ (latency выше)<br>• Нет кредитов на Firecrawl аккаунте |
| **Fallback-цепочка** | `web_search` → `s.jina.ai` → `firecrawl_search` |
| **Input/Output** | **Input:** `query: string`, `limit: number`, `lang: string`, опционально `scrapeOptions`<br>**Output:** JSON с результатами поиска, каждый с URL, title, markdown content, metadata |
| **Rate limits** | Зависит от плана: Free = 2 concurrent requests + low rate limits; Hobby = 5 concurrent; Standard = 50 concurrent. |
| **Пример** | `POST /v1/search {"query": "renewable energy 2024", "limit": 10, "lang": "en"}` |

---

### 2.2 Page Scraping & Content Extraction

#### 2.2.1 `mshtools-browser_visit`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-browser_visit |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Средний (~3-10 сек в зависимости от страницы) |
| **Когда использовать** | • Нужно посмотреть на страницу и получить текстовое представление<br>• Страница требует JavaScript рендеринг (SPA, React, Vue)<br>• Нужно взаимодействовать с элементами (клики, скролл, формы)<br>• Нужен скриншот для визуального анализа<br>• Страница защищена простой bot-detection |
| **Когда НЕ использовать** | • Только текстовый контент со статической страницы (используй Jina Reader)<br>• Нужна массовая обработка URL (слишком медленно)<br>• Страница блокирует headless браузер (Cloudflare, DataDome) — используй Firecrawl<br>• Rate limit на количество browser-сессий |
| **Fallback-цепочка** | `browser_visit` → `Jina Reader` (если просто нужен текст) → `firecrawl_scrape` (если блокирует) |
| **Input/Output** | **Input:** `url: string`, опционально `need_screenshot: boolean`<br>**Output:** Текстовое представление страницы (как видит пользователь), список интерактивных элементов с индексами, scroll-информация |
| **Rate limits** | Не документированы; практически ~50-100 визитов/сессия без проблем. Каждый визит создаёт отдельную страницу в сессии. |
| **Пример** | `browser_visit({"url": "https://example.com/report", "need_screenshot": true})` |

#### 2.2.2 `mshtools-browser_click` / `browser_scroll` / `browser_find` / `browser_input`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-browser_click, browser_scroll_down/up, browser_find, browser_input |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Быстрый-средний (~1-3 сек/действие) |
| **Когда использовать** | • **click** — кнопки "Load more", пагинация, раскрытие аккордеонов, навигация по меню<br>• **scroll** — бесконечный скролл, lazy-loading контента, доступ к нижней части страницы<br>• **find** — поиск конкретного текста на большой странице<br>• **input** — заполнение поисковых форм, фильтров, авторизационных полей |
| **Когда НЕ использовать** | • CAPTCHA или сложные anti-bot системы<br>• Нужно множество последовательных действий (latency накапливается)<br>• Данные доступны через API или direct scraping<br>• Бот-детекция блокирует последовательные действия |
| **Fallback-цепочка** | `browser_click/scroll/input` → `browser_screenshot` (визуальная проверка) → `firecrawl_interact` (если нужна автоматизация) |
| **Input/Output** | **Input:** element_index (для click/input), scroll_amount (для scroll), keyword (для find), content (для input)<br>**Output:** Обновлённое состояние страницы с новыми элементами |
| **Rate limits** | Общие с browser_visit; каждое действие обновляет страницу |
| **Пример** | `browser_click({"element_index": 5})` — клик по кнопке "Accept cookies" |

#### 2.2.3 `mshtools-browser_screenshot`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-browser_screenshot |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Быстрый (~1-2 сек) |
| **Когда использовать** | • Визуальная верификация результата действия<br>• Извлечение данных из таблиц/диаграмм, которые плохо конвертируются в текст<br>• Проверка, не блокирует ли страница бота (CAPTCHA detection)<br>• Документирование результатов исследования<br>• Анализ UI/UX, макетов страниц |
| **Когда НЕ использовать** | • Только текстовый контент (избыточно)<br>• Массовый мониторинг (неэффективно)<br>• Автоматизированный data extraction (нужен OCR дополнительно) |
| **Fallback-цепочка** | `browser_screenshot` → `generate_image` (если нужна обработка) → `find_asset_bbox` + `crop_and_replicate_assets_in_image` (если нужно извлечь визуальные элементы) |
| **Input/Output** | **Input:** Опционально `download_screenshot_path: string`<br>**Output:** Скриншот страницы в виде изображения |
| **Rate limits** | Общие с browser_visit |
| **Пример** | `browser_screenshot({"download_screenshot_path": "/tmp/page_capture.png"})` |

#### 2.2.4 `Jina AI Reader (r.jina.ai)`

| Attribute | Value |
|-----------|-------|
| **Название** | Jina AI Reader (r.jina.ai) |
| **Tier стоимости** | 2 (низкая — бесплатно без ключа/с ключом; оплата по токенам output) |
| **Латентность** | Средний (~7.9 сек среднее; 2-15 сек реальный диапазон) |
| **Когда использовать** | • Быстрое извлечение чистого markdown с любой страницы<br>• Массовая обработка URL (поддержка batch/parallel)<br>• Работа с PDF файлами (автоматическая конвертация)<br>• Нужен только основной контент (без навигации, рекламы)<br>• Обработка страниц с CSS-селекторами (extract only)<br>• До 10 параллельных запросов |
| **Когда НЕ использовать** | • Страница требует кликов/интеракций для раскрытия контента<br>• Сложная anti-bot защита (Cloudflare, DataDome) — возможны блокировки<br>• Нужен JavaScript рендеринг сложных SPA (работает, но медленно)<br>• Rate limit 20 RPM без ключа / 500 RPM с ключом |
| **Fallback-цепочка** | `browser_visit` (если нужен JS-рендеринг) → `Jina Reader` (если просто нужен текст быстро) → `firecrawl_scrape` (если Reader не справился с защитой) |
| **Input/Output** | **Input:** URL (prefix `https://r.jina.ai/https://example.com`), опционально CSS-селекторы, API key<br>**Output:** Чистый markdown с заголовком, контентом, ссылками, изображениями |
| **Rate limits** | 20 RPM без API key; 500 RPM с free/paid API key; 5000 RPM с premium key. Токеты: считаются по output response. |
| **Пример** | `curl "https://r.jina.ai/https://en.wikipedia.org/wiki/Artificial_intelligence"` |

#### 2.2.5 `Firecrawl Scrape API`

| Attribute | Value |
|-----------|-------|
| **Название** | Firecrawl Scrape API |
| **Tier стоимости** | 4 (высокая — 1 credit/page; Free tier: 1000 pages/мес) |
| **Латентность** | Средний (~3-8 сек) |
| **Когда использовать** | • **Silver bullet** — когда всё остальное не работает<br>• Страница с сильной anti-bot защитой (Cloudflare, DataDome, PerimeterX)<br>• Нужен JavaScript рендеринг + чистый markdown<br>• Нужна структурированная выгрузка (JSON schema)<br>• Нужен скриншот + markdown одновременно<br>• Работа с формами и авторизацией |
| **Когда НЕ использовать** | • Простые статические страницы (переплата)<br>• Массовая обработка без необходимости premium-фич<br>• Rate limit критичен (низкие лимиты на Free tier)<br>• Бюджет исследования ограничен |
| **Fallback-цепочка** | `browser_visit` → `Jina Reader` → `firecrawl_scrape` (финальный fallback) |
| **Input/Output** | **Input:** `url: string`, опционально `formats: ["markdown", "html", "screenshot"]`, `onlyMainContent: boolean`, `waitFor: number`, actions<br>**Output:** Чистый markdown/HTML, скриншот base64, метаданные страницы, links на странице |
| **Rate limits** | Free: 2 concurrent requests; Hobby: 5; Standard: 50; Growth: 100. 1000 credits/мес на Free tier. |
| **Пример** | `POST /v1/scrape {"url": "https://example.com", "formats": ["markdown", "screenshot"]}` |

---

### 2.3 Multi-Page Crawling

#### 2.3.1 `Firecrawl Crawl API`

| Attribute | Value |
|-----------|-------|
| **Название** | Firecrawl Crawl API |
| **Tier стоимости** | 4 (высокая — 1 credit/page) |
| **Латентность** | Медленный (зависит от глубины; фоновый процесс) |
| **Когда использовать** | • Нужно просканировать весь сайт или раздел<br>• Deep research требует анализа множества связанных страниц<br>• Поиск всех URL на домене (sitemap generation)<br>• Мониторинг изменений на сайте (/monitor endpoint) |
| **Когда НЕ использовать** | • Нужна только одна страница (используй scrape)<br>• Ограниченный бюджет (кредиты расходуются быстро)<br>• Нет необходимости в полном обходе сайта |
| **Fallback-цепочка** | `browser_visit` + ручная навигация → `firecrawl_crawl` (автоматический обход) |
| **Input/Output** | **Input:** `url: string`, `limit: number`, `includePaths: string[]`, `excludePaths: string[]`, `scrapeOptions: object`<br>**Output:** Массив просканированных страниц с markdown контентом, метаданными, ссылками |
| **Rate limits** | Те же, что и для Scrape API |
| **Пример** | `POST /v1/crawl {"url": "https://docs.example.com", "limit": 50, "scrapeOptions": {"formats": ["markdown"]}}` |

---

### 2.4 Deep Research & Autonomous Agents

#### 2.4.1 `Jina AI DeepSearch`

| Attribute | Value |
|-----------|-------|
| **Название** | Jina AI DeepSearch (deepsearch.jina.ai) |
| **Tier стоимости** | 4 (высокая — оплата по токенам всего процесса; средняя latency 56.7 сек) |
| **Латентность** | Медленный (~30-120 сек в зависимости от сложности запроса) |
| **Когда использовать** | • Нужен автономный многошаговый поиск с reasoning<br>• Сложный вопрос требующий синтеза из множества источников<br>• **Перекрёстная проверка фактов** из разных источников<br>• Исследование "с нуля" когда неясно где искать<br>• Нужен список источников (citations) с ответом |
| **Когда НЕ использовать** | • Простой фактический запрос (переплата по токенам)<br>• Время критично (>60 сек ожидания)<br>• Нужен контроль над каждым шагом (лучше ручная цепочка)<br>• Rate limit 50 RPM (free/paid key) |
| **Fallback-цепочка** | `web_search` + `browser_visit` (ручная цепочка) → `Jina DeepSearch` (автономный агент) |
| **Input/Output** | **Input:** OpenAI-compatible chat completions API; `messages`, `model: "jina-deep-search-v1"`, опционально `token_budget`<br>**Output:** Полный ответ с reasoning steps, citations (URL-источники), пошаговым логом |
| **Rate limits** | 50 RPM с free/paid API key; 500 RPM с premium key. Токены: считаются за весь процесс (input + output + search). |
| **Пример** | `POST /v1/chat/completions {"model": "jina-deep-search-v1", "messages": [{"role": "user", "content": "What are the latest breakthroughs in fusion energy research?"}], "stream": true}` |

#### 2.4.2 `Firecrawl Agent (Preview)`

| Attribute | Value |
|-----------|-------|
| **Название** | Firecrawl Agent API |
| **Tier стоимости** | 4 (высокая — 5 free daily runs; далее dynamic pricing) |
| **Латентность** | Медленный (зависит от сложности задачи) |
| **Когда использовать** | • Нужен полностью автономный агент: поиск + навигация + извлечение<br>• Неизвестны конкретные URL — только описание нужных данных<br>• Сложная многостраничная навигация с извлечением<br>• Структурированный вывод с JSON schema |
| **Когда НЕ использовать** | • Известны конкретные URL (избыточно)<br>• Ограниченный бюджет (dynamic pricing)<br>• Нужен предсказуемый cost (лучше явная цепочка)<br>• 5 free runs/day limit |
| **Fallback-цепочка** | `firecrawl_agent` → Ручная цепочка: `firecrawl_search` → `firecrawl_scrape` |
| **Input/Output** | **Input:** `prompt: string`, опционально `urls: string[]`, `schema: object` (Pydantic/BaseModel)<br>**Output:** Структурированные данные + список источников |
| **Rate limits** | 5 free daily runs; далее требуется paid plan |
| **Пример** | `POST /v1/agent {"prompt": "Find the pricing plans for Notion", "schema": {"plans": [{"name": "str", "price": "str"}]}}` |

---

### 2.5 Image Tools

#### 2.5.1 `mshtools-search_image_by_text`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-search_image_by_text |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Быстрый (~2-4 сек) |
| **Когда использовать** | • Поиск изображений по ключевым словам<br>• Нужны визуальные примеры, иллюстрации, диаграммы<br>• Поиск логотипов, брендинга, UI-макетов<br>• Сбор визуальных данных для отчёта |
| **Когда НЕ использовать** | • Поиск конкретного изображения (используй search_image_by_image)<br>• Генерация нового изображения (используй generate_image)<br>• Нужны только текстовые данные |
| **Fallback-цепочка** | `search_image_by_text` → `search_image_by_image` (если нашёл похожее и хочет найти оригинал) → `generate_image` (если не нашёл подходящее) |
| **Input/Output** | **Input:** `queries: string[]`, `total_count: number` (1-10), `need_download: boolean`<br>**Output:** Список изображений с URL, заголовками, превью |
| **Rate limits** | Не документированы; предположительно ~50-100 запросов/сессия |
| **Пример** | `search_image_by_text({"queries": ["renewable energy infographic 2024"], "total_count": 5})` |

#### 2.5.2 `mshtools-search_image_by_image`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-search_image_by_image |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Быстрый (~2-4 сек) |
| **Когда использовать** | • Обратный поиск изображения (найти источник)<br>• Поиск похожих изображений<br>• Идентификация объектов, людей, мест на фото<br>• Проверка подлинности изображения |
| **Когда НЕ использовать** | • Поиск по текстовому описанию (используй search_image_by_text)<br>• Генерация изображения<br>• Анализ видео |
| **Fallback-цепочка** | `search_image_by_image` → `search_image_by_text` (если reverse search не дал результатов, описать текстом) |
| **Input/Output** | **Input:** `image_url: string` (URL или локальный путь), `total_count: number`<br>**Output:** Список похожих изображений с источниками |
| **Rate limits** | Не документированы |
| **Пример** | `search_image_by_image({"image_url": "/tmp/screenshot.png", "total_count": 5})` |

#### 2.5.3 `mshtools-generate_image`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-generate_image |
| **Tier стоимости** | 3 (средняя — AI generation) |
| **Латентность** | Медленный (~5-15 сек) |
| **Когда использовать** | • Создание иллюстраций для отчёта<br>• Генерация диаграмм/схем, которые невозможно найти<br>• Визуализация концепций и идей<br>• Создание mockup-ов, UI концептов |
| **Когда НЕ использовать** | • Можно найти реальное изображение (используй search)<br>• Нужна фотографическая точность (возможны артефакты)<br>• Ограниченный бюджет на генерацию |
| **Fallback-цепочка** | `search_image_by_text` → `generate_image` (если не нашёл подходящее) |
| **Input/Output** | **Input:** `description: string`, `output_file: string`, `ratio: string`, `resolution: string`, опционально `reference_images_urls`<br>**Output:** Сгенерированное изображение в указанном формате |
| **Rate limits** | Зависит от провайдера; обычно ~10-50 генераций/час |
| **Пример** | `generate_image({"description": "Infographic showing renewable energy growth 2020-2024", "output_file": "/tmp/energy_growth.png", "ratio": "16:9"})` |

---

### 2.6 Video & Audio Tools

#### 2.6.1 `mshtools-generate_video`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-generate_video |
| **Tier стоимости** | 3 (средняя — AI video generation) |
| **Латентность** | Медленный (~30-120 сек) |
| **Когда использовать** | • Создание видео-иллюстраций для отчёта<br>• Визуализация процессов/динамики<br>• Презентационные материалы |
| **Когда НЕ использовать** | • Нужен анализ существующего видео (не поддерживается)<br>• Время критично<br>• Ограниченный бюджет |
| **Fallback-цепочка** | N/A (уникальная функция) |
| **Input/Output** | **Input:** `description: string`, `output_file: string`, `duration: number` (4-12 сек), `ratio: string`, опционально `reference_images_urls`<br>**Output:** Сгенерированное видео в формате MP4 |
| **Rate limits** | ~5-10 генераций/сессия |
| **Пример** | `generate_video({"description": "Animation of wind turbines spinning", "output_file": "/tmp/wind.mp4", "duration": 5})` |

#### 2.6.2 `mshtools-generate_speech`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-generate_speech |
| **Tier стоимости** | 2 (низкая — требуется voice_id) |
| **Латентность** | Быстрый (~2-5 сек) |
| **Когда использовать** | • Создание аудио-версии отчёта<br>• Голосовые пояснения к данным<br>• Accessibility — аудио-формат для слабовидящих |
| **Когда НЕ использовать** | • Только текстовый отчёт (избыточно)<br>• Нет подходящего voice_id |
| **Fallback-цепочка** | `generate_speech` (единственный вариант TTS) |
| **Input/Output** | **Input:** `text: string`, `voice_id: string`, `output_path: string`<br>**Output:** Аудиофайл (MP3/WAV) |
| **Rate limits** | Зависит от voice provider (ElevenLabs) |
| **Пример** | `generate_speech({"text": "Summary of renewable energy report...", "voice_id": "Adam", "output_path": "/tmp/summary.mp3"})` |

---

### 2.7 Computation & Execution

#### 2.7.1 `mshtools-ipython`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-ipython (Python execution) |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Быстрый-средний (~1-10 сек в зависимости от задачи) |
| **Когда использовать** | • Data analysis — обработка, фильтрация, агрегация данных<br>• Визуализация данных (matplotlib, seaborn, plotly)<br>• Web scraping через requests/BeautifulSoup (curl fallback)<br>• Парсинг HTML/XML/JSON<br>• Статистический анализ, ML-моделирование<br>• Автоматизация обработки файлов<br>• PDF parsing (PyPDF2, pdfplumber) |
| **Когда НЕ использовать** | • Нужен headless браузер (используй browser_*)<br>• Задача требует системных вызовов (используй shell)<br>• Ограничения по памяти/CPU для больших задач |
| **Fallback-цепочка** | `ipython` (requests/BS4 scraping) → `browser_visit` (если нужен JS) → `Jina Reader` → `firecrawl_scrape` |
| **Input/Output** | **Input:** `code: string` (Python code), опционально `restart: boolean`<br>**Output:** Результат выполнения (stdout, изображения matplotlib, ошибки) |
| **Rate limits** | Сессия сохраняется между вызовами; переменные и импорты persist. Можно устанавливать пакеты через `!pip install`. |
| **Пример** | `ipython({"code": "import pandas as pd; df = pd.read_csv('data.csv'); df.describe()"})` |

#### 2.7.2 `mshtools-shell`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-shell (Shell execution) |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Быстрый (~0.5-3 сек) |
| **Когда использовать** | • Системные операции: ls, find, grep, cat<br>• Управление файлами: mkdir, cp, mv, rm<br>• Git операции<br>• curl/wget для HTTP запросов (без Python)<br>• Текстовая обработка: awk, sed, jq<br>• Архивирование: tar, zip, unzip |
| **Когда НЕ использовать** | • Сложная обработка данных (используй ipython)<br>• Нужен headless браузер (используй browser_*)<br>• Опасные команды (rm -rf, перезапись системных файлов) |
| **Fallback-цепочка** | `shell` (curl) → `ipython` (requests) → `browser_visit` |
| **Input/Output** | **Input:** `command: string`, опционально `description: string`, `timeout: number`<br>**Output:** stdout + stderr вывода команды |
| **Rate limits** | Неперсистентное окружение (каждый вызов — новая сессия) |
| **Пример** | `shell({"command": "curl -s https://api.example.com/data | jq '.results[0]'", "description": "Fetch API data"})` |

---

### 2.8 File Operations

#### 2.8.1 `mshtools-read_file`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-read_file |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Мгновенный |
| **Когда использовать** | • Чтение файлов отчётов, конфигов, данных<br>• Чтение текстовых файлов (TXT, CSV, JSON, MD, PY, JS)<br>• Чтение изображений (PNG, JPG — отображается)<br>• Чтение видео (MP4, MOV — отображается)<br>• Чтение бинарных файлов (Office, PDF — конвертируется в markdown) |
| **Когда НЕ использовать** | • Файл >200 MB (текст) или >100 MB (видео) или >20 MB (бинарные)<br>• Нужно редактирование (используй edit_file) |
| **Fallback-цепочка** | `read_file` → `ipython` (pandas для больших CSV) → `shell` (grep для поиска в файле) |
| **Input/Output** | **Input:** `file_path: string`, опционально `offset: number`, `limit: number`<br>**Output:** Содержимое файла (текст или отображение медиа) |
| **Rate limits** | До 1000 строк за раз (для текстовых файлов) |
| **Пример** | `read_file({"file_path": "/mnt/agents/output/report.md", "limit": 100})` |

#### 2.8.2 `mshtools-write_file`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-write_file |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Мгновенный |
| **Когда использовать** | • Создание отчётов, артефактов исследования<br>• Сохранение данных (JSON, CSV)<br>• Создание конфигурационных файлов<br>• Логирование результатов |
| **Когда НЕ использовать** | • Перезапись существующего файла без чтения (обязательно read перед write)<br>• Очень большие файлы (>100K chars за раз) |
| **Fallback-цепочка** | `write_file` → `ipython` (для сложной генерации контента) |
| **Input/Output** | **Input:** `file_path: string`, `content: string`, опционально `append: boolean`<br>**Output:** Подтверждение записи |
| **Rate limits** | Max 100,000 chars за вызов; используй `append: true` для больших файлов |
| **Пример** | `write_file({"file_path": "/mnt/agents/output/report.md", "content": "# Report\n\n## Section 1\n..."})` |

#### 2.8.3 `mshtools-edit_file`

| Attribute | Value |
|-----------|-------|
| **Название** | mshtools-edit_file |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Мгновенный |
| **Когда использовать** | • Правка существующих файлов без полной перезаписи<br>• Рефакторинг кода, переименование переменных<br>• Обновление конфигурационных значений<br>• Исправление ошибок в отчётах |
| **Когда НЕ использовать** | • Нужно полностью переписать файл (используй write_file)<br>• Не читали файл перед правкой (обязательно read перед edit)<br>• Слишком много изменений (лучше переписать) |
| **Fallback-цепочка** | `edit_file` → `write_file` (если изменений слишком много) |
| **Input/Output** | **Input:** `file_path: string`, `old_string: string`, `new_string: string`, опционально `replace_all: boolean`<br>**Output:** Подтверждение редактирования |
| **Rate limits** | old_string должен быть уникальным (или использовать `replace_all`) |
| **Пример** | `edit_file({"file_path": "config.json", "old_string": "\"timeout\": 30", "new_string": "\"timeout\": 60"})` |

---

### 2.9 HTTP Direct Access

#### 2.9.1 `curl / requests` (via shell / ipython)

| Attribute | Value |
|-----------|-------|
| **Название** | curl (shell) / requests (ipython) |
| **Tier стоимости** | 1 (бесплатно) |
| **Латентность** | Быстрый (~0.5-3 сек) |
| **Когда использовать** | • Прямой HTTP запрос к API или статической странице<br>• Загрузка файлов (PDF, CSV, изображения)<br>• REST API вызовы (GET, POST с JSON)<br>• Head-запросы для проверки доступности<br>• Проверка HTTP статусов, редиректов |
| **Когда НЕ использовать** | • Страница требует JavaScript (используй browser_visit)<br>• Сложная anti-bot защита (используй firecrawl_scrape)<br>• Нужен рендеринг или взаимодействие |
| **Fallback-цепочка** | `curl` → `Jina Reader` (если нужен чистый текст) → `browser_visit` (если нужен JS) → `firecrawl_scrape` |
| **Input/Output** | **Input:** URL, headers, method, body<br>**Output:** HTTP response (body, status, headers) |
| **Rate limits** | Нет внешних лимитов; лимитировано целевым сервером |
| **Пример** | `shell({"command": "curl -s -H 'Accept: application/json' https://api.example.com/data"})` |

---

## 3. Data Sources Matrix

| Data Source | Domain | Tier | Latency | Best For | Anti-Patterns |
|-------------|--------|------|---------|----------|---------------|
| **yahoo_finance** | Stocks, markets, financial data | 1 (free) | Fast | Stock prices, company financials, historical data | Non-financial research; real-time tick data |
| **arxiv** | Scientific papers, preprints | 1 (free) | Fast | Physics, CS, math, biology papers; literature review | Proprietary research; non-academic topics |
| **world_bank_open_data** | Economic, social, environmental indicators | 1 (free) | Medium | GDP, population, poverty, education, health data | Non-country-level analysis; real-time data |
| **binance_crypto** | Cryptocurrency prices, trading | 1 (free) | Fast | BTC, ETH, crypto market analysis | Non-crypto research; fundamental analysis |
| **scholar** | Academic papers, citations, authors | 1 (free) | Medium | Citation analysis, author profiles, h-index | Full-text paper access (use arXiv instead) |
| **stock_finance_data** | China A-shares, HK, US financials | 1 (free) | Fast | Chinese market analysis, financial statements | Non-Chinese markets without coverage |
| **imf** | Macroeconomic forecasts, global data | 1 (free) | Medium | GDP growth, inflation, debt, trade balances | Company-level research; non-macro topics |
| **yuandian_law** | Chinese law, regulations, cases | 1 (free) | Medium | PRC legal research, compliance | Non-Chinese law; non-legal research |

### Data Source Fallback Strategy

```
Need financial data on company?
  ├── yahoo_finance (US stocks)
  ├── stock_finance_data (China/HK stocks)
  └── web_search: "[company] annual report [year]" → browser_visit

Need scientific papers?
  ├── arxiv (CS/physics/math preprints)
  ├── scholar (broader academic search, citations)
  └── web_search: "[topic] paper pdf" → Jina Reader

Need economic/country data?
  ├── world_bank_open_data (development indicators)
  ├── imf (macroeconomic forecasts)
  └── web_search: "[country] [indicator] statistics"

Need legal data (China)?
  ├── yuandian_law (statutes, cases)
  └── web_search: "[law] 中华人民共和国 [regulation]"
```

---

## 4. Cost Estimation Formula

### 4.1 Task Decomposition Model

Перед началом исследования агент выполняет **cost estimation** на основе декомпозиции задачи.

```python
class ResearchTask:
    """Описание задачи исследования для оценки стоимости"""
    
    def __init__(self, query: str, depth: str = "standard", 
                 max_sources: int = 10, output_format: str = "report"):
        self.query = query
        self.depth = depth  # "quick", "standard", "deep", "exhaustive"
        self.max_sources = max_sources
        self.output_format = output_format

def estimate_cost(task: ResearchTask) -> dict:
    """
    Оценивает стоимость задачи исследования.
    
    Returns: {
        "tier_1_cost": int,      # Native tool calls (free)
        "tier_2_cost": float,    # Jina API tokens ($)
        "tier_4_cost": float,    # Firecrawl credits ($)
        "total_time_sec": int,   # Estimated time
        "fallback_rate": float   # Expected fallback percentage
    }
    """
    
    # Base costs per depth level
    depth_multipliers = {
        "quick":       {"searches": 2,  "pages": 3,  "tier2_chance": 0.1, "tier4_chance": 0.05},
        "standard":    {"searches": 5,  "pages": 10, "tier2_chance": 0.3, "tier4_chance": 0.15},
        "deep":        {"searches": 10, "pages": 25, "tier2_chance": 0.5, "tier4_chance": 0.30},
        "exhaustive":  {"searches": 20, "pages": 50, "tier2_chance": 0.7, "tier4_chance": 0.50}
    }
    
    d = depth_multipliers[task.depth]
    
    # Tier 1: Native tools (always free)
    tier_1_calls = d["searches"] + d["pages"]  # web_search + browser_visit
    
    # Tier 2: Jina Reader/Search
    tier_2_calls = int(d["pages"] * d["tier2_chance"])
    # ~$0.001 per page (token-based, very low)
    tier_2_cost = tier_2_calls * 0.001
    
    # Tier 4: Firecrawl (most expensive)
    tier_4_calls = int(d["pages"] * d["tier4_chance"])
    # Free tier: 1000 credits/month; Hobby: $16/5000 credits
    # Effective cost: ~$0.003/credit on Free tier, ~$0.0032 on Hobby
    tier_4_cost = tier_4_calls * 0.003
    
    # Time estimates (seconds)
    time_per_search = 2
    time_per_page_tier1 = 5      # browser_visit
    time_per_page_tier2 = 8      # Jina Reader
    time_per_page_tier4 = 6      # Firecrawl scrape
    
    total_time = (
        d["searches"] * time_per_search +
        d["pages"] * time_per_page_tier1 * (1 - d["tier2_chance"] - d["tier4_chance"]) +
        tier_2_calls * time_per_page_tier2 +
        tier_4_calls * time_per_page_tier4
    )
    
    return {
        "tier_1_cost": tier_1_calls,           # count (free)
        "tier_2_cost_usd": round(tier_2_cost, 4),
        "tier_4_cost_usd": round(tier_4_cost, 4),
        "total_estimated_cost_usd": round(tier_2_cost + tier_4_cost, 4),
        "total_time_sec": int(total_time),
        "total_time_min": round(total_time / 60, 1),
        "tier_2_calls": tier_2_calls,
        "tier_4_calls": tier_4_calls,
        "fallback_rate": round((d["tier2_chance"] + d["tier4_chance"]) * 100, 1)
    }
```

### 4.2 Cost Estimation Quick Reference

| Depth Level | Searches | Pages | Tier 2 Calls | Tier 4 Calls | Est. Time | Est. Cost |
|-------------|----------|-------|--------------|--------------|-----------|-----------|
| Quick | 2 | 3 | 0 | 0 | 20 sec | Free |
| Standard | 5 | 10 | 3 | 2 | 2 min | ~$0.009 |
| Deep | 10 | 25 | 13 | 8 | 5 min | ~$0.037 |
| Exhaustive | 20 | 50 | 35 | 25 | 12 min | ~$0.110 |

### 4.3 Budget Guardrails

```python
BUDGET_LIMITS = {
    "quick":       {"max_tier4": 0,  "max_total_usd": 0.00,  "max_time_sec": 60},
    "standard":    {"max_tier4": 3,  "max_total_usd": 0.01,  "max_time_sec": 180},
    "deep":        {"max_tier4": 10, "max_total_usd": 0.05,  "max_time_sec": 600},
    "exhaustive":  {"max_tier4": 30, "max_total_usd": 0.15,  "max_time_sec": 1800}
}

def check_budget(task_depth: str, tier_4_used: int, total_cost_usd: float, 
                 elapsed_sec: int) -> dict:
    """Проверяет, не превышен ли бюджет, и предлагает корректировки"""
    limits = BUDGET_LIMITS[task_depth]
    
    status = "ok"
    warnings = []
    
    if tier_4_used > limits["max_tier4"]:
        status = "warning"
        warnings.append(f"Tier 4 usage ({tier_4_used}) exceeds limit ({limits['max_tier4']})")
    
    if total_cost_usd > limits["max_total_usd"]:
        status = "critical"
        warnings.append(f"Cost ${total_cost_usd:.4f} exceeds budget ${limits['max_total_usd']:.4f}")
    
    if elapsed_sec > limits["max_time_sec"]:
        status = "critical"
        warnings.append(f"Time {elapsed_sec}s exceeds limit {limits['max_time_sec']}s")
    
    return {
        "status": status,  # "ok" | "warning" | "critical"
        "warnings": warnings,
        "should_escalate": status == "critical",
        "suggested_action": "continue" if status == "ok" else 
                           "reduce_tier4" if status == "warning" else "abort_or_downgrade"
    }
```

---

## 5. Tool Selection Algorithm

### 5.1 Decision Tree

```
FUNCTION select_tool(subtask: SubTask, context: ExecutionContext) -> ToolChain:
    """
    Алгоритм выбора инструмента для subtask.
    
    Параметры:
        subtask: Описание подзадачи
        context: Контекст выполнения (budget_used, time_elapsed, previous_failures)
    
    Возвращает:
        ToolChain: Цепочку инструментов с fallback'ами
    """
    
    # ─── STEP 1: Check structured data sources first (always free) ───
    IF subtask.domain in ["finance", "stocks", "crypto"]:
        IF subtask.ticker AND subtask.ticker in US_EXCHANGES:
            RETURN ToolChain([yahoo_finance, web_search_fallback])
        IF subtask.ticker AND subtask.ticker in CHINA_HK_EXCHANGES:
            RETURN ToolChain([stock_finance_data, web_search_fallback])
        IF subtask.is_crypto:
            RETURN ToolChain([binance_crypto, web_search_fallback])
    
    IF subtask.domain == "academic_research":
        IF subtask.needs_fulltext:
            RETURN ToolChain([arxiv, scholar, browser_visit])
        ELSE:
            RETURN ToolChain([scholar, arxiv])
    
    IF subtask.domain in ["economics", "country_data"]:
        RETURN ToolChain([world_bank_open_data, imf, web_search])
    
    IF subtask.domain == "china_law":
        RETURN ToolChain([yuandian_law, web_search])
    
    # ─── STEP 2: Classify the interaction type ───
    IF subtask.type == "search_discovery":
        # Start with free web search
        primary = web_search
        
        # Check if we need cleaner results
        IF subtask.needs_clean_content:
            primary = jina_search  # s.jina.ai
        
        # Check if we need structured/semantic search
        IF subtask.needs_structured:
            primary = firecrawl_search
        
        RETURN ToolChain([primary, browser_visit_fallback])
    
    IF subtask.type == "page_extraction":
        url = subtask.target_url
        
        # Check URL characteristics
        is_static = likely_static(url)      # .html, .md, no JS framework
        needs_js = likely_spa(url)           # React, Vue, Angular patterns
        has_protection = known_protection(url)  # Cloudflare, DataDome sites
        
        IF is_static AND NOT has_protection:
            RETURN ToolChain([jina_reader, browser_visit, firecrawl_scrape])
        
        IF needs_js AND NOT has_protection:
            RETURN ToolChain([browser_visit, jina_reader, firecrawl_scrape])
        
        IF has_protection:
            # Skip straight to premium
            RETURN ToolChain([firecrawl_scrape, jina_reader])
        
        # Default: try cheapest first
        RETURN ToolChain([jina_reader, browser_visit, firecrawl_scrape])
    
    IF subtask.type == "multi_page_crawl":
        # Only Firecrawl supports true crawling
        RETURN ToolChain([firecrawl_crawl, manual_browser_sequence])
    
    IF subtask.type == "interaction":
        # Browser automation for forms, clicks, etc.
        RETURN ToolChain([browser_visit_with_clicks, firecrawl_interact])
    
    IF subtask.type == "deep_research":
        # Autonomous research agents
        IF context.budget_allows_tier4:
            RETURN ToolChain([jina_deepsearch, firecrawl_agent, manual_chain])
        ELSE:
            RETURN ToolChain([manual_web_search_chain])  # web_search → visit → extract loop
    
    IF subtask.type == "visual_extraction":
        RETURN ToolChain([browser_screenshot, find_asset_bbox, crop_and_replicate])
    
    IF subtask.type == "image_search":
        IF subtask.has_reference_image:
            RETURN ToolChain([search_image_by_image, search_image_by_text])
        ELSE:
            RETURN ToolChain([search_image_by_text, generate_image])
    
    IF subtask.type == "data_processing":
        RETURN ToolChain([ipython, shell])
    
    IF subtask.type == "file_management":
        RETURN ToolChain([read_file, write_file, edit_file])
    
    # ─── STEP 3: Default fallback ───
    RETURN ToolChain([web_search, browser_visit, jina_reader, firecrawl_scrape])
```

### 5.2 URL Classification Heuristics

```python
def likely_static(url: str) -> bool:
    """Определяет, является ли страница статической"""
    static_indicators = [
        ".html", ".htm", ".md", ".txt", ".pdf",
        "/blog/", "/news/", "/article/", "/post/",
        "wikipedia.org", "github.com", "medium.com",
        ".gov", ".edu"
    ]
    return any(ind in url.lower() for ind in static_indicators)

def likely_spa(url: str) -> bool:
    """Определяет, требует ли страница JavaScript рендеринг"""
    spa_indicators = [
        "#", "!/", "/app/", "dashboard", "portal",
        "twitter.com", "x.com", "linkedin.com",
        "instagram.com", "facebook.com",
        "react", "vue", "angular", "next.js", "nuxt"
    ]
    return any(ind in url.lower() for ind in spa_indicators)

def known_protection(url: str) -> bool:
    """Определяет, есть ли у страницы сильная защита"""
    protected_domains = [
        "cloudflare", "datadome", "perimeterx",
        "akamai", "reblaze", "sucuri",
        "bloomberg.com", "wsj.com", "ft.com",
        "seekingalpha.com", " crunchbase.com"
    ]
    # Note: This is a heuristic; actual protection detection happens at runtime
    return any(ind in url.lower() for ind in protected_domains)
```

### 5.3 Quality Gate Checkpoints

```python
def quality_gate_check(extracted_content: str, subtask: SubTask) -> dict:
    """
    Проверяет, удовлетворяет ли извлечённый контент требованиям.
    Если нет — триггерит fallback на следующий tier.
    """
    
    checks = {
        "has_content": len(extracted_content.strip()) > 100,
        "has_required_keywords": all(
            kw.lower() in extracted_content.lower() 
            for kw in subtask.required_keywords
        ) if subtask.required_keywords else True,
        "not_captcha": "captcha" not in extracted_content.lower()[:500],
        "not_blocked": "access denied" not in extracted_content.lower()[:500],
        "not_paywall": all(
            phrase not in extracted_content.lower()[:1000]
            for phrase in ["subscribe to continue", "premium content", 
                          "please log in", "sign up to read"]
        ),
        "reasonable_length": len(extracted_content) > 500,
    }
    
    passed = all(checks.values())
    
    return {
        "passed": passed,
        "failed_checks": [k for k, v in checks.items() if not v],
        "content_length": len(extracted_content),
        "should_fallback": not passed
    }
```

---

## 6. Hybrid Fallback Chains

### 6.1 Chain A: "Static Page Extraction" (Стандартная цепочка)

**Сценарий:** Нужно извлечь контент с обычной веб-страницы (новости, блог, вики).

```
TIER 1 (Free)                          TIER 2 (Low Cost)                     TIER 4 (Premium)
┌──────────────────┐    FAIL/EMPTY    ┌──────────────────┐    FAIL/BLOCK    ┌──────────────────┐
│                  │ ──────────────── │                  │ ──────────────── │                  │
│   browser_visit  │                  │  Jina Reader     │                  │ Firecrawl Scrape │
│                  │ ──────────────── │  (r.jina.ai)     │ ──────────────── │                  │
│  + screenshot    │   JS-render OK   │                  │   Anti-bot       │                  │
└──────────────────┘   Content found  └──────────────────┘   protection     └──────────────────┘
        │                                     │
        ▼                                     ▼
   QUALITY_GATE                          QUALITY_GATE
   Passed? ✓                            Passed? ✓
        │                                     │
        ▼                                     ▼
   Return content                     Return content
```

**Expected flow:** browser_visit → Jina Reader (fallback) → Firecrawl (rare)
**Cost profile:** Free in 80% cases, ~$0.001 in 15%, ~$0.003 in 5%

### 6.2 Chain B: "SPA/Dynamic Content" (JavaScript-рендеринг)

**Сценарий:** Страница использует React/Vue/Angular, контент загружается динамически.

```
TIER 1 (Free)                          TIER 2 (Low Cost)                     TIER 4 (Premium)
┌──────────────────┐    JS REQUIRED    ┌──────────────────┐    BLOCKED      ┌──────────────────┐
│                  │ ───────────────── │                  │ ─────────────── │                  │
│   browser_visit  │                   │  browser_visit   │                 │ Firecrawl Scrape │
│                  │ ───────────────── │  + click/scroll  │                 │ (with waitFor)   │
│  JS rendering    │   Need interact   │  sequence        │                 │                  │
└──────────────────┘                   └──────────────────┘                 └──────────────────┘
        │
        ▼
   Wait for dynamic
   content to load
        │
        ▼
   QUALITY_GATE
   (is dynamic content present?)
        │
   ┌────┴────┐
   │YES      │NO
   ▼         ▼
Return   Try click/scroll
         sequence (TIER 1)
              │
              ▼
         Still no content?
              │
         ┌────┴────┐
         │YES      │NO
         ▼         ▼
    Firecrawl   Return content
    (TIER 4)
```

**Expected flow:** browser_visit (wait) → click/scroll sequence → Firecrawl (rare)
**Cost profile:** Free in 70%, ~$0.003 in 30% (if Firecrawl needed)

### 6.3 Chain C: "Anti-Bot / Protected Site" (Silver Bullet)

**Сценарий:** Сайт с Cloudflare, DataDome, PerimeterX или paywall.

```
TIER 1 (Free)                          TIER 2 (Low Cost)                     TIER 4 (Premium)
┌──────────────────┐    CAPTCHA/       ┌──────────────────┐    STILL        ┌──────────────────┐
│                  │    BLOCKED        │                  │    BLOCKED    │                  │
│   browser_visit  │ ────────────────  │  Jina Reader     │ ──────────────  │ Firecrawl Scrape │
│                  │                   │  (r.jina.ai)     │                 │                  │
│  Screenshot:     │   Quick check     │                  │                 │ Premium stealth  │
│  "Access Denied" │   if simple site  │                  │                 │ proxy rotation   │
└──────────────────┘                   └──────────────────┘                 └──────────────────┘
        │                                                                     │
        ▼                                                                     ▼
   BLOCKED DETECTED                                                    QUALITY_GATE
        │                                                              Passed? ✓
        ▼                                                                     │
   Skip straight to                                                    Return content
   Firecrawl (TIER 4)
   (don't waste time
    on TIER 1/2)
```

**Expected flow:** browser_visit (detect block) → Firecrawl Scrape (direct)
**Cost profile:** ~$0.003/page (always TIER 4 for known protected sites)

### 6.4 Chain D: "Discovery → Deep Dive" (Многостраничное исследование)

**Сценарий:** Нужно найти источники, затем глубоко изучить каждый.

```
PHASE 1: DISCOVERY (Free)              PHASE 2: EXTRACTION (Tier 1-2)       PHASE 3: DEEP ANALYSIS
┌──────────────────┐                   ┌──────────────────┐                   ┌──────────────────┐
│                  │                   │                  │                   │                  │
│   web_search     │ ──URL list─────  │  For each URL:   │  ──All content──  │   ipython        │
│   (batch of      │                   │  ├─ Jina Reader  │                   │   (analysis)     │
│    queries)      │                   │  ├─ browser_visit│                   │                  │
│                  │                   │  └─ firecrawl_   │                   │  ├─ Aggregation  │
│  Get 10-20 URLs  │                   │     scrape       │                   │  ├─ Visualization│
└──────────────────┘                   │     (fallback)   │                   │  ├─ Insights     │
                                       └──────────────────┘                   │                  │
                                                                              └──────────────────┘
```

**Expected flow:** web_search (batch) → parallel Jina Reader (all URLs) → ipython analysis
**Cost profile:** Free search + ~$0.01-0.03 for 10-30 pages + Free analysis = ~$0.03 total

### 6.5 Chain E: "Autonomous Deep Research" (Максимальная автоматизация)

**Сценарий:** Сложный вопрос, требующий reasoning + многошагового поиска. Бюджет позволяет TIER 4.

```
OPTION 1: Jina DeepSearch (TIER 4)          OPTION 2: Firecrawl Agent (TIER 4)
┌──────────────────────────┐                ┌──────────────────────────┐
│                          │                │                          │
│   jina_deepsearch        │                │   firecrawl_agent        │
│   (autonomous agent)     │                │   (autonomous agent)     │
│                          │                │                          │
│  Input: research query   │                │  Input: prompt + schema  │
│  Model: jina-deep-search │                │  Output: structured JSON │
│                          │                │                          │
│  Process:                │                │  Process:                │
│  1. Decompose query      │                │  1. Search web           │
│  2. Search sources       │                │  2. Navigate pages       │
│  3. Read & reason        │                │  3. Extract structured   │
│  4. Cross-reference      │                │     data                 │
│  5. Synthesize answer    │                │  4. Return JSON          │
│                          │                │                          │
│  Output:                 │                │  Fallback:               │
│  - Synthesized answer    │                │  If JSON schema fails →  │
│  - Citations [URL]       │                │  manual chain            │
│  - Reasoning steps       │                │                          │
│                          │                │  Rate limit: 5/day free  │
│  Latency: 30-120 sec     │                │                          │
│  Rate limit: 50 RPM      │                │                          │
└──────────────────────────┘                └──────────────────────────┘
        │                                              │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
                    If both fail → Manual Chain:
                    ┌──────────────────────────┐
                    │  web_search → browser_   │
                    │  visit → jina_reader →   │
                    │  ipython_analysis loop   │
                    └──────────────────────────┘
```

**Expected flow:** jina_deepsearch OR firecrawl_agent → manual chain (fallback)
**Cost profile:** Jina DeepSearch: ~$0.02-0.10/запрос (токены процесса); Firecrawl Agent: 5 free/day, далее dynamic

---

## 7. Cost-Aware Execution Budgets

### 7.1 Default Budgets by Task Type

| Task Type | Max Tier 4 Calls | Max Total Cost | Max Time | Strategy |
|-----------|------------------|----------------|----------|----------|
| Quick answer | 0 | $0.00 | 1 min | Tier 1 only |
| Fact check | 1 | $0.005 | 2 min | Tier 1 → 1×Tier 4 if blocked |
| Standard research | 3 | $0.01 | 5 min | Tier 1 → selective Tier 2 |
| Deep research | 10 | $0.05 | 15 min | Tier 1 → Tier 2 → selective Tier 4 |
| Exhaustive research | 30 | $0.15 | 30 min | All tiers, parallel where possible |
| Enterprise-grade | Unlimited | $1.00 | 60 min | Full silver bullet access |

### 7.2 Dynamic Budget Adjustment

```python
def adjust_budget_dynamically(context: ExecutionContext) -> dict:
    """
    Динамически корректирует бюджет на основе промежуточных результатов.
    """
    
    success_rate = context.successful_extractions / context.total_attempts
    avg_cost_per_page = context.total_cost / context.pages_processed
    
    adjustments = {}
    
    # If Tier 1/2 has high success, reduce Tier 4 allocation
    if success_rate > 0.8:
        adjustments["tier4_allowance"] = int(context.initial_budget["tier4"] * 0.5)
        adjustments["strategy"] = "lean: rely on cheap tools"
    
    # If success rate is low, increase Tier 4 but cap total
    elif success_rate < 0.4:
        adjustments["tier4_allowance"] = context.initial_budget["tier4"] + 5
        adjustments["strategy"] = "aggressive: more silver bullets"
    
    # If running out of time, escalate to Tier 4 faster
    time_ratio = context.elapsed_time / context.max_time
    if time_ratio > 0.7 and context.completion_ratio < 0.5:
        adjustments["skip_tier2"] = True
        adjustments["strategy"] = "time-critical: skip to Tier 4"
    
    return adjustments
```

---

## 8. Anti-Patterns & Guardrails

### 8.1 Tool Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| **"Tier 4 First"** | Использование Firecrawl для простых статических страниц | Always start with browser_visit or Jina Reader |
| **"Browser Spam"** | Множественные browser_visit туда-сюда вместо batch-обработки | Batch URLs with Jina Reader parallel (up to 10) |
| **"No Quality Gate"** | Принятие пустого/blocked контента без проверки | Always run quality_gate_check() after extraction |
| **"Infinite Fallback Loop"** | Fallback Tier 4 → Tier 1 → Tier 4... | Track attempted tools per URL; never retry same tool |
| **"Budget Blindness"** | Продолжение исследования при превышении бюджета | check_budget() после каждого major step |
| **"Parallel Panic"** | Параллельный запуск всех tier'ов одновременно | Sequential escalation: T1 → T2 → T4 |
| **"Image Overload"** | Генерация изображений без необходимости | search_image_by_text first; generate only if needed |
| **"DeepSearch Overuse"** | Jina DeepSearch для простых фактов | Use web_search + browser_visit; reserve DeepSearch for synthesis |

### 8.2 Guardrails Implementation

```python
class ToolExecutor:
    """Безопасный executor с guardrails"""
    
    def __init__(self, budget: dict):
        self.budget = budget
        self.tier4_used = 0
        self.total_cost = 0.0
        self.attempted_tools = {}  # url -> set of attempted tools
        self.call_log = []
    
    async def execute(self, tool_call: ToolCall) -> Result:
        # Guardrail 1: Budget check
        budget_status = check_budget(
            self.budget["depth"], 
            self.tier4_used, 
            self.total_cost,
            self.elapsed_time
        )
        if budget_status["should_escalate"]:
            # Graceful degradation вместо жёсткого abort (раньше здесь был
            # raise BudgetExceededException, терявший весь прогон при достижении ceiling).
            # Прекращаем эскалацию tier'ов и сигналим оркестратору финализировать отчёт
            # по уже собранному (deliver partial-with-confidence — см. SKILL.md §8 и §1.8).
            return Result.degraded(reason="budget_ceiling", warnings=budget_status["warnings"])
        
        # Guardrail 2: No retry loops
        url = tool_call.target_url
        tool_name = tool_call.tool_name
        if url in self.attempted_tools and tool_name in self.attempted_tools[url]:
            raise RetryLoopException(f"Already attempted {tool_name} on {url}")
        
        self.attempted_tools.setdefault(url, set()).add(tool_name)
        
        # Guardrail 3: Quality gate after extraction
        result = await self._run_tool(tool_call)
        
        if tool_call.expects_content:
            quality = quality_gate_check(result.content, tool_call.subtask)
            if not quality["passed"]:
                result.quality_passed = False
                result.failed_checks = quality["failed_checks"]
        
        # Update budget tracking
        if tool_call.tier == 4:
            self.tier4_used += 1
        self.total_cost += tool_call.estimated_cost
        
        self.call_log.append({
            "tool": tool_name,
            "url": url,
            "success": result.success,
            "quality_passed": getattr(result, "quality_passed", True),
            "cost": tool_call.estimated_cost,
            "time": result.elapsed_ms
        })
        
        return result
```

---

## 9. Integration with SKILL.md Phases

### 9.1 Phase → Tool Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SKILL.md PHASES                                    │
├──────────────────┬──────────────────────────────────────────────────────────┤
│ Phase 1: PLAN    │ Tool: ipython (task decomposition)                       │
│                  │ Tool: web_search (initial landscape scan)                │
│                  │                                                          │
│ Phase 2: GATHER  │ Primary: web_search, data sources                        │
│                  │ Secondary: jina_reader, browser_visit                    │
│                  │ Fallback: firecrawl_scrape                               │
│                  │                                                          │
│ Phase 3: DEEPEN  │ Primary: browser_visit (+ clicks/scroll)                 │
│                  │ Secondary: jina_deepsearch (for synthesis)               │
│                  │ Fallback: firecrawl_agent                                │
│                  │                                                          │
│ Phase 4: VERIFY  │ Tool: web_search (cross-reference)                       │
│                  │ Tool: ipython (data validation)                          │
│                  │ Tool: browser_screenshot (visual verification)           │
│                  │                                                          │
│ Phase 5: SYNTH   │ Tool: ipython (analysis, visualization)                  │
│                  │ Tool: generate_image (report illustrations)              │
│                  │ Tool: write_file (report generation)                     │
├──────────────────┴──────────────────────────────────────────────────────────┤
│ Lazy Loading: Tools from TIER 2/4 are loaded only when TIER 1 fails         │
│ Checkpoint: After each phase — log tool usage, cost, success rate           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 AGENT.MD Heartbeat Integration

```yaml
# Checkpoint format (logged after each tool execution)
checkpoint:
  timestamp: "2025-01-20T10:30:00Z"
  phase: "GATHER"
  subtask_id: "extract_company_info_001"
  tool_chain:
    - tool: "web_search"
      tier: 1
      status: "success"
      cost_usd: 0.0
      latency_ms: 2300
    - tool: "jina_reader"
      tier: 2
      status: "success"
      cost_usd: 0.001
      latency_ms: 7800
  quality_gate:
    passed: true
    content_length: 4523
  budget_status:
    tier4_used: 0
    total_cost_usd: 0.001
    time_elapsed_sec: 45
    status: "ok"
```

---

## Appendix A: Quick Reference Card

### Provider Risk Classification (collect seam — Phase 9 / Phase 14)

The `collect.normalize()` seam stamps `metadata["risk_class"]` on every
collected item before it reaches `ingest`.  Risk class reflects the fetch
posture of each provider:

| Provider | `fetched_via` key | `risk_class` | Escalation class | Notes |
|----------|-------------------|--------------|-----------------|-------|
| Native web search | `native_web_search` | **SAFE** | — | Server-managed, sandboxed |
| Jina Reader (r.jina.ai) | `jina_reader` | **SAFE** | — | Server-side proxy fetch |
| Jina Search (s.jina.ai) | `jina_search` | **SAFE** | — | Server-side proxy fetch |
| Firecrawl scrape/search | `firecrawl` | **SAFE** | — | Server-managed headless |
| **RSS feed** | `rss` | **SAFE** | — | Cheapest tier; stdlib urllib host-side fetch; engine normalizes pre-fetched payload |
| Browserbase | `browserbase` | **ELEVATED** | **browser** | Remote browser, less sandboxed |
| Direct curl / requests | `curl` | **ELEVATED** | **curl** | Raw network fetch, no proxy |

**RSS provider notes (Phase 14, AC14-5):**
- The engine normalizes an RSS payload that the host has already fetched (via stdlib `urllib` or any HTTP client).  The engine itself never opens a socket — it only parses the XML/list.
- An RSS endpoint reached with a browser `User-Agent` (host-side detail) can bypass JS challenges; the engine simply normalizes the payload delivered to it.
- RSS items carry `published_at` (extracted from `<pubDate>` / `<published>` / `<updated>`), which causes downstream `ingest.source_from_raw` to assign `DateConfidence.HIGH`.
- RSS is the **cheapest** tier: no external API credit is consumed by the engine layer.

`ELEVATED` providers add `"escalate_to_firecrawl"` to `next_valid_actions`
as a recovery hint.  Callers MAY use `risk_class` to gate logging, rate-limit
policies, or human-review thresholds.

### Escalation Actions Vocabulary (collect seam)

`next_valid_actions` strings returned by `collect.normalize()`:

| Action string | When emitted | Phase introduced |
|--------------|--------------|-----------------|
| `ingest_items` | Result list is non-empty | Phase 9 |
| `retry_after_backoff` | Provider returned rate_limited or error | Phase 9 |
| `escalate_to_firecrawl` | Provider is ELEVATED (browserbase, curl) | Phase 9 |
| `enable_provider` | Provider returned status="disabled" | Phase 9 |
| `fix_caller_payload_shape` | raw_payload is neither list nor control dict | Phase 9 |
| `retry_with_proxy` | Provider is **browser-class** ELEVATED (browserbase) AND rate_limited | Phase 14 |
| `fetch_next_page` | Any item in the payload carries a `"cursor"` field | Phase 14 |
| `no_more_pages` | Payload list is empty (final page exhausted) | Phase 14 |
| `enrich_top_n` | Provider is `rss` AND collected items have no `scores` field | Phase 14 |
| `escalate_to_agent` | Cursor present (paginated result suggests agent-level depth needed) | Phase 14 |

**PROVIDER_ESCALATION map (Phase 14):** distinguishes browser-class vs curl-class ELEVATED providers.
```python
PROVIDER_ESCALATION = {
    "browserbase": "browser",   # Remote headless browser → retry_with_proxy on rate-limit
    "curl":        "curl",      # Raw HTTP fetch → no proxy hint
}
```

### Cost Tier Summary

| Tier | Tools | Cost | When |
|------|-------|------|------|
| **TIER 1** | web_search, browser_*, ipython, shell, file_*, data sources | Free | Always start here |
| **TIER 2** | Jina Reader, Jina Search | ~$0.001/call | When Tier 1 is slow or blocked |
| **TIER 3** | generate_image, generate_video | Variable | Only when creative assets needed |
| **TIER 4** | Firecrawl (scrape/crawl/search/agent), Jina DeepSearch | ~$0.003/call+ | Silver bullet — when all else fails |

### Latency Summary

| Speed | Tools | Avg Latency |
|-------|-------|-------------|
| Instant | read_file, write_file, edit_file, ipython (simple) | <1 sec |
| Fast | web_search, browser_click, shell, data sources | 1-3 sec |
| Medium | browser_visit, jina_search, firecrawl_scrape | 3-10 sec |
| Slow | jina_reader, jina_deepsearch, firecrawl_crawl | 8-120 sec |

### Tool Selection Cheat Sheet

| I need to... | Start with | Fallback |
|-------------|-----------|----------|
| Search for sources | `web_search` | `s.jina.ai` → `firecrawl_search` |
| Extract page text | `browser_visit` | `r.jina.ai` → `firecrawl_scrape` |
| Handle JS-heavy page | `browser_visit` (+wait) | `firecrawl_scrape` (with waitFor) |
| Bypass anti-bot | `firecrawl_scrape` | — |
| Crawl entire site | `firecrawl_crawl` | Manual browser sequence |
| Deep autonomous research | `jina_deepsearch` | Manual web_search loop |
| Extract structured data | `firecrawl_agent` | `browser_visit` + `ipython` parsing |
| Find images | `search_image_by_text` | `search_image_by_image` → `generate_image` |
| Process/analyze data | `ipython` | `shell` |
| Cross-check facts | `web_search` (multiple queries) | `jina_deepsearch` |

---

*Document generated for Deep Research Skill v1.0. Aligns with AGENT.MD heartbeat protocol and SKILL.md phase architecture.*
