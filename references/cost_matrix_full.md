# Deep Research Skill: Исчерпывающая Cost Matrix

> **Version:** 1.0.0
> **Last Updated:** 2025-06-28
> **Purpose:** Полное руководство по стоимости, ограничениям и оптимизации использования всех инструментов Deep Research Skill

---

## Содержание

1. [Легенда и методология](#1-легенда-и-методология)
2. [Полная матрица инструментов](#2-полная-матрица-инструментов)
3. [Сравнительные таблицы по категориям](#3-сравнительные-таблицы-по-категориям)
4. [Cost Estimation Calculator](#4-cost-estimation-calculator)
5. [Budget Allocation Templates](#5-budget-allocation-templates)
6. [Cost Optimization Tips](#6-cost-optimization-tips)
7. [Hidden Costs Matrix](#7-hidden-costs-matrix)
8. [Fallback Chains](#8-fallback-chains)
9. [Частотные сценарии использования](#9-частотные-сценарии-использования)
10. [Итоговые рекомендации](#10-итоговые-рекомендации)

---

## 1. Легенда и методология

### Tier System (1-4)

| Tier | Name | Description | Typical Monthly Budget |
|------|------|-------------|----------------------|
| **1** | Free/Native | Нативные инструменты Claude Desktop, open-source | $0 |
| **2** | Low-Cost | Бюджетные API, self-hosted решения | $0 - $50 |
| **3** | Mid-Range | Профессиональные API с расширенными возможностями | $50 - $500 |
| **4** | Enterprise | Полный набор: браузеры, капча-решения, масштабирование | $500+ |

### Quality Score (1-10)

| Score | Description |
|-------|-------------|
| 10 | Публикационное качество, минимум галлюцинаций |
| 8-9 | Отличное качество, пригодное для профессионального использования |
| 6-7 | Хорошее качество, требует проверки |
| 4-5 | Удовлетворительное, значительные ограничения |
| 1-3 | Базовое, только для черновиков |

### Time Cost Legend

| Badge | Latency | Description |
|-------|---------|-------------|
| ⚡ | < 1s | Мгновенный ответ |
| 🚀 | 1-5s | Быстрый |
| ⏱️ | 5-15s | Средний |
| 🐢 | 15-30s | Медленный |
| ⏳ | 30s+ | Очень медленный |

---

## 2. Полная матрица инструментов

### 2.1 Native Tools (Claude Desktop)

| Tool Name | Category | Tier | Monetary Cost | Time Cost | Quality | Best For | Limitations | Rate Limits | Reliability | Setup Complexity | Maintenance | Fallback Chain |
|-----------|----------|------|---------------|-----------|---------|----------|-------------|-------------|-------------|------------------|-------------|----------------|
| `mshtools-web_search` | search | 1 | Free (included) | 🚀 1-3s | 7/10 | Быстрый поиск фактов, новостей, общей информации | Нет прямого доступа к paywall-контенту; результаты зависят от индексации | Не документированы, ~50-100 queries/session | 99% | None | None | web_search → browser_visit |
| `mshtools-browser_visit` | browser | 1 | Free (included) | ⏱️ 5-10s | 8/10 | Рендеринг JS-heavy сайтов, визуальная проверка, screenshot | Без stealth-режима; некоторые сайты блокируют автоматизацию | Не документированы, ~20-50 visits/session | 95% | None | None | browser_visit → Jina Reader → Firecrawl |
| `mshtools-browser_click` | browser | 1 | Free (included) | 🚀 0.5-2s | 8/10 | Навигация по страницам, взаимодействие с UI | Требует предварительного browser_visit; может сломаться при обновлении сайта | ~100 clicks/session | 90% | None | None | browser_click → curl_cffi (для простых форм) |
| `mshtools-browser_scroll` | browser | 1 | Free (included) | 🚀 1-3s | 8/10 | Загрузка lazy-content, бесконечные скроллы | Нет точного контроля над позицией; timing-зависим | ~100 scrolls/session | 90% | None | None | scroll → direct API call if available |
| `mshtools-browser_input` | browser | 1 | Free (included) | 🚀 0.5-2s | 8/10 | Заполнение форм поиска, авторизация | CAPTCHA блокирует; не работает с 2FA | ~50 inputs/session | 85% | None | None | input → direct API call → captcha_solver |
| `mshtools-browser_find` | browser | 1 | Free (included) | 🚀 0.5-1s | 7/10 | Поиск текста на странице, навигация к разделам | Только текстовый поиск; не работает с изображениями | ~100 finds/session | 95% | None | None | find → browser_screenshot + vision analysis |
| `mshtools-browser_screenshot` | browser | 1 | Free (included) | 🚀 1-2s | 9/10 | Визуальная верификация, извлечение данных из изображений | Статичный скриншот; не захватывает dynamic changes | ~50 screenshots/session | 98% | None | None | screenshot → browser_visit + extraction |
| `mshtools-search_image_by_text` | image | 1 | Free (included) | 🚀 2-5s | 6/10 | Поиск изображений по текстовому описанию | Ограниченный выбор; качество зависит от провайдера | ~20-50 searches/session | 95% | None | None | search_image → generate_image (as fallback) |
| `mshtools-search_image_by_image` | image | 1 | Free (included) | 🚀 2-5s | 6/10 | Reverse image search, поиск похожих изображений | Не всегда точный; зависит от индекса | ~20-50 searches/session | 90% | None | None | search_by_image → manual description + text_search |
| `mshtools-ipython` | compute | 1 | Free (included) | ⚡ <1s (code exec) | 9/10 | Data processing, analysis, visualization, format conversion | Ограничения памяти (~2GB); нет persistence между сессиями | ~100 code executions/session | 99% | None | None | ipython → shell → external API |
| `mshtools-shell` | compute | 1 | Free (included) | ⚡ <1s (local), ⏱️ 5-30s (network) | 8/10 | File operations, git, curl, data pipeline automation | Ограниченные права; no sudo; sandboxed | ~50 commands/session | 98% | None | None | shell → ipython → external service |
| `mshtools-read_file` | file | 1 | Free (included) | ⚡ <0.5s | 10/10 | Чтение локальных файлов, code review, document analysis | Размер файла до 200MB; текстовые/бинарные ≤20MB | ~200 reads/session | 99% | None | None | read_file → shell cat → download + read |
| `mshtools-write_file` | file | 1 | Free (included) | ⚡ <0.5s | 10/10 | Сохранение результатов, создание артефактов | Путь должен быть абсолютным; max 100K chars/write | ~100 writes/session | 99% | None | None | write_file → shell echo/redirect |
| `mshtools-edit_file` | file | 1 | Free (included) | ⚡ <0.5s | 10/10 | Правка существующих файлов, refactoring | Требует предварительного read_file; old_string должен быть уникальным | ~100 edits/session | 99% | None | None | edit_file → write_file (overwrite) |
| `mshtools-generate_image` | generate | 1 | Free (included) | ⏱️ 5-10s | 8/10 | Создание иллюстраций, диаграмм, визуальных концептов | AI-generated artifacts; может потребовать доработки | ~20 generations/session | 95% | None | None | generate_image → search_image |
| `mshtools-generate_video` | generate | 1 | Free (included) | ⏳ 30-120s | 7/10 | Создание коротких видео для демонстраций | Max 12 секунд; 4-12s range; resource-intensive | ~5 generations/session | 90% | None | None | generate_video → image sequence + assembly |
| `mshtools-generate_speech` | generate | 1 | Free (included) | ⏱️ 5-15s | 8/10 | Озвучка текста, создание аудио-контента | Требует voice_id; ограниченный выбор голосов | ~20 generations/session | 95% | None | None | generate_speech → external TTS |
| `mshtools-get_data_source` | data | 1 | Free (included) | 🚀 2-10s | 9/10 | Финансовые данные, академические статьи, экономические показатели, законы | Зависит от внешнего API провайдера; rate limits применяются | ~50 calls/session | 95% | API keys required | None | get_data_source → web_search → browser_visit |

### 2.2 Web Scraping APIs

| Tool Name | Category | Tier | Monetary Cost | Time Cost | Quality | Best For | Limitations | Rate Limits | Reliability | Setup Complexity | Maintenance | Fallback Chain |
|-----------|----------|------|---------------|-----------|---------|----------|-------------|-------------|-------------|------------------|-------------|----------------|
| **Jina AI Reader** (`r.jina.ai`) | scrape | 2 | **Free tier:** 20 requests/day<br>**Paid:** ~$5/1K requests (or $0.02/M tokens PAYG)<br>**Pro:** $18 ≈ 1M tokens | 🚀 1-3s | 8/10 | Быстрое извлечение markdown с любого URL; отличная структура | Не обходит paywall; ReaderLM-v2 стоит 3x токены; timeout на медленных страницах | Free: 20 req/day<br>Paid: до 5000 RPM по ключу | 97% | None (prefix) / API key (paid) | None | Jina Reader → Firecrawl → browser_visit |
| **Jina AI Search** (`s.jina.ai`) | search | 2 | **Free:** 10M tokens включено<br>**PAYG:** ~$0.02/M tokens<br>**Top-up:** от $18 | 🚀 2-4s | 7/10 | LLM-friendly веб-поиск с результатами в markdown | Ограниченная глубина; 5 результатов на запрос | Free: 10M tokens<br>Paid: зависит от баланса | 96% | API key | None | Jina Search → web_search → browser_visit |
| **Jina DeepSearch** | search | 2 | **Free:** self-hosted (open source)<br>**API:** токены по прайсу Jina | ⏳ 30-120s | 9/10 | Глубокий рекурсивный поиск с reasoning; ищет пока не найдёт ответ или не закончится бюджет | Требует токен-бюджет; может быть дорогим при большой глубине | Зависит от ключа | 94% | Medium (self-host) / Low (API) | Monitoring токенов | DeepSearch → Jina Search + manual synthesis |
| **Firecrawl API** (`scrape_url`) | scrape | 3 | **Free:** 1,000 credits/mo<br>**Hobby:** $16/mo (3K credits)<br>**Standard:** $83/mo (100K)<br>**Growth:** $333/mo (500K)<br>**Scale:** $679/mo (1M)<br>1 page = 1 credit | 🚀 0.5-5s (P95: 3.4s) | 9/10 | Профессиональный scraping с JS-рендерингом, markdown/JSON/screenshot output; 96% coverage веба | Нет PAYG (только планы); credits не переносятся; FIRE-1 agent всегда биллится даже при ошибке | Free: 2 concurrent<br>Hobby: 5 concurrent<br>Standard: 50 concurrent<br>Growth: 100 concurrent | 98% (слабая) | API key + SDK | None | Firecrawl → Jina Reader → curl_cffi |
| **Firecrawl API** (`crawl_url`) | scrape | 3 | Те же credits: 1 page = 1 credit | ⏱️ 10-60s (зависит от depth) | 9/10 | Полный crawl сайтов с контролем depth, path filters, scheduled syncs | Может быстро исчерпать credits на больших сайтах; robots.txt ограничения | Те же, что и scrape_url | 96% | API key + SDK | None | crawl_url → sitemap + batch_scrape |
| **curl_cffi** | scrape | 2 | **Free** (open source MIT) | 🚀 0.1-2s | 7/10 | Быстрый scraping с impersonation браузерных TLS/JA3/HTTP2 fingerprints; обход fingerprint-based detection | Нет JS-движка (не обходит Cloudflare Turnstile); требует прокси для масштаба; только HTTP-клиент | Лимит только прокси и целевого сайта | 95% | Low (`pip install curl_cffi`) | Update fingerprints | curl_cffi → CloakBrowser → Firecrawl |
| **Obscura** | browser | 3 | **Unknown / N/A** — headless Rust browser | ⏱️ 2-8s | ?/10 | (Мало данных) Предположительно stealth-автоматизация на Rust | **Недостаточно данных**; сообщество меньше чем у CloakBrowser | Unknown | Unknown | Unknown | Unknown | Obscura → CloakBrowser → Browserbase |
| **CloakBrowser** | browser | 2 | **Free** (open source, MIT)<br>Enterprise: $0 (self-hosted) | ⏱️ 3-10s | 8/10 | Stealth Chromium с C++ source-level patching; проходит bot detection; drop-in Playwright/Puppeteer replacement | Требует собственные прокси; не решает CAPTCHA (предотвращает появление); нужен Docker для Profile Manager | Зависит от инфраструктуры | 92% | Medium (Docker/pip/npm) | Chrome updates | CloakBrowser → Browserbase → 2Captcha+Chrome |
| **Browserbase** | browser | 3 | **Free:** $0 (3 concurrent, 1 hr, 1K Search, 1K Fetch)<br>**Developer:** $20/mo (25 concurrent, 100 hrs)<br>**Startup:** $99/mo (100 concurrent, 500 hrs)<br>**Scale:** Custom | 🚀 0.5-3s (sub-second cold start) | 9/10 | Полноценный cloud browser: captcha solving, proxies 195+ стран, identity management, session recording | Браузерные часы расходуются быстро; overage: $0.10-0.12/hr; Search API: $7/1K после лимита | Free: 3 concurrent, 15 min/session<br>Dev: 25 concurrent<br>Startup: 100 concurrent | 99.5% | Low (API key) | None | Browserbase → CloakBrowser + captcha_solver |

### 2.3 Data Sources

| Tool Name | Category | Tier | Monetary Cost | Time Cost | Quality | Best For | Limitations | Rate Limits | Reliability | Setup Complexity | Maintenance | Fallback Chain |
|-----------|----------|------|---------------|-----------|---------|----------|-------------|-------------|-------------|------------------|-------------|----------------|
| **Yahoo Finance** (via `get_data_source`) | data | 1 | Free tier included | 🚀 1-3s | 8/10 | Stock prices, financial metrics, earnings, dividends | Нет real-time данных; 15-min delay для некоторых рынков | ~100 calls/day free | 99% | None (pre-configured) | None | Yahoo Finance → web_search → Alpha Vantage |
| **arXiv** (via `get_data_source`) | data | 1 | Free (arXiv API) | 🚀 2-5s | 9/10 | Академические препринты, научные статьи, цитирования | Нет полного текста для некоторых; формат PDF требует обработки | 3 requests/second (arXiv limit) | 99% | None (pre-configured) | None | arXiv → Google Scholar → Semantic Scholar |
| **Google Scholar** (via `get_data_source`) | data | 1 | Free tier included | 🚀 2-5s | 8/10 | Поиск академических статей, citation analysis, author profiles | Ограниченная API access; может требовать scraping для полных данных | ~100 calls/day | 95% | None (pre-configured) | None | Scholar → arXiv → Microsoft Academic |
| **World Bank Open Data** (via `get_data_source`) | data | 1 | Free (WB API) | 🚀 2-8s | 9/10 | Макроэкономические показатели 190+ стран, временные ряды с 1960 | Обновление с задержкой; не все индикаторы актуальны | 100 requests/10 sec | 99% | None (pre-configured) | None | WB → IMF → national statistics |
| **IMF WEO** (via `get_data_source`) | data | 1 | Free (IMF API) | 🚀 2-8s | 9/10 | Global macroeconomic forecasts, GDP, inflation, trade balances, COFER | Прогнозы обновляются 2x в год; исторические данные ограничены | 10 requests/min | 99% | None (pre-configured) | None | IMF → World Bank → OECD |
| **Stock Finance Data** (via `get_data_source`) | data | 1 | Free tier included | 🚀 1-5s | 8/10 | China A-shares, Hong Kong, US markets; financial statements, screening | China-centric; less coverage for EU markets | ~100 calls/day | 97% | None (pre-configured) | None | Stock Finance → Yahoo Finance |
| **Binance** (via `get_data_source`) | data | 1 | Free (Binance API) | ⚡ <1s | 9/10 | Real-time crypto prices, K-line data, 24h statistics, trading volume | Только криптовалюты; ограничения по IP | 1200 request weight/min | 99.9% | None (pre-configured) | None | Binance → CoinGecko → CoinMarketCap |
| **Yuandian Law** (via `get_data_source`) | data | 1 | Free tier included | 🚀 2-5s | 7/10 | Chinese law database: statutes, regulations, court cases | Только mainland PRC law; на китайском языке | ~50 calls/day | 95% | None (pre-configured) | None | Yuandian → web_search → official sources |

### 2.4 Verification Sources

| Tool Name | Category | Tier | Monetary Cost | Time Cost | Quality | Best For | Limitations | Rate Limits | Reliability | Setup Complexity | Maintenance | Fallback Chain |
|-----------|----------|------|---------------|-----------|---------|----------|-------------|-------------|-------------|------------------|-------------|----------------|
| **archive.org** (Wayback Machine) | verify | 1 | Free | ⏱️ 5-15s | 8/10 | Проверка исторических версий страниц, восстановление мёртвых ссылок | Не все страницы архивированы; snapshot может быть устаревшим | ~15 requests/min | 95% | None | None | archive.org → archive.today → manual search |
| **archive.today** (Archive.is) | verify | 1 | Free | ⏱️ 10-30s | 7/10 | Создание snapshot текущей страницы, проверка контента | Часто перегружен; CAPTCHA при массовом использовании | ~5 requests/min (неофициально) | 80% | None | None | archive.today → archive.org → screenshot |
| **factcheck.org** | verify | 1 | Free (website) | 🚀 2-5s | 9/10 | Проверка политических заявлений, фактчекинг | US-centric; ограниченное покрытие не-политических тем | Web scraping limits | 99% | None | None | factcheck.org → snopes → Reuters Fact Check |
| **snopes.com** | verify | 1 | Free (website) | 🚀 2-5s | 8/10 | Проверка urban legends, viral claims, общих мифов | Популярные темы только; может быть медленным | Web scraping limits | 98% | None | None | snopes → factcheck.org → web_search |
| **Wikipedia** | verify | 1 | Free (API + web) | 🚀 1-3s | 7/10 | Базовая проверка фактов, общие сведения, ссылки на источники | Не авторитетный первичный источник; вандализм; устаревшие статьи | 200 requests/min (API) | 99% | None | None | Wikipedia → primary sources → Google Scholar |

### 2.5 CAPTCHA Solving

| Tool Name | Category | Tier | Monetary Cost | Time Cost | Quality | Best For | Limitations | Rate Limits | Reliability | Setup Complexity | Maintenance | Fallback Chain |
|-----------|----------|------|---------------|-----------|---------|----------|-------------|-------------|-------------|------------------|-------------|----------------|
| **solvecaptcha-python** | captcha | 3 | **$0.50-$2.99/1K** (зависит от типа) | 🐢 10-30s | 8/10 | Python SDK для интеграции различных captcha-сервисов | Зависит от backend-сервиса; требует настройки provider | Provider-dependent | 90% | Medium (pip install + config) | Provider rotation | solvecaptcha → direct API → manual |
| **2Captcha** | captcha | 3 | **reCAPTCHA v2:** $1.00-2.99/1K<br>**Turnstile:** $1.45/1K<br>**hCaptcha:** $1-3/1K<br>Min payment: $3 | 🐢 13-30s (human solvers) | 9/10 | Широчайшая поддержка 30+ типов CAPTCHA; human solvers; 99% accuracy | Медленнее AI-решений; зависит от доступности workforce; этические вопросы | ~1000 workers online; 1000/min capacity | 99% | Low (API key) | Balance monitoring | 2Captcha → Anti-Captcha → CapSolver |
| **Anti-Captcha** | captcha | 3 | **Images:** $0.50-0.70/1K<br>**reCAPTCHA v2:** $0.95-2.00/1K<br>**reCAPTCHA v3:** $1-2/1K<br>**Enterprise:** $5/1K<br>**Turnstile:** $2/1K | 🐢 5-10s | 9/10 | Самая низкая цена на image CAPTCHA; browser plugin; 99.99% uptime с 2007 | Human solvers (медленнее AI); русскоязычный интерфейс может сбивать с толку | 1000 workers online; 1000/min capacity | 99.99% | Low (API key) | Balance monitoring | Anti-Captcha → 2Captcha → CapSolver |
| **CapSolver** | captcha | 2 | **reCAPTCHA v2:** $0.80/1K<br>**reCAPTCHA v3:** $1.00/1K<br>**Turnstile:** $1.20/1K<br>**Cloudflare Challenge:** $1.20/1K<br>**ImageToText:** $0.40/1K | ⚡-🚀 2-10s (AI-powered) | 9/10 | Самый быстрый AI solver; отличная поддержка Cloudflare; pay-for-success | AI может не справиться с новыми типами; меньше типов чем у 2Captcha | High concurrency supported | 98% | Low (API key) | None | CapSolver → 2Captcha → Anti-Captcha |

### 2.6 Multi-Agent Frameworks

| Tool Name | Category | Tier | Monetary Cost | Time Cost | Quality | Best For | Limitations | Rate Limits | Reliability | Setup Complexity | Maintenance | Fallback Chain |
|-----------|----------|------|---------------|-----------|---------|----------|-------------|-------------|-------------|------------------|-------------|----------------|
| **ECC** (affaan-m/ECC) | multi-agent | 2 | **Free** (MIT open source)<br>**ECC Pro:** $?? (GitHub App for private repos) | N/A (framework) | 8/10 | Полноценная система skills/agents/hooks для Claude Code; 63 subagents; 251 skills; cross-harness | Требует Claude Code; learning curve; plugin-based ecosystem | N/A (local execution) | 95% | High (plugin install + rules setup) | Weekly updates | ECC → native Claude tools → manual workflow |
| **STORM** (Stanford) | multi-agent | 2 | **Free** (open source)<br>**Self-hosted:** LLM API costs only | ⏳ 5-15 min (full pipeline) | 9/10 | Генерация Wikipedia-quality статей с многоступенчатым research; multi-perspective questioning; outline-first | Требует LLM API keys; длительное выполнение; output требует human review | N/A (self-hosted) | 90% | Medium (Python env + API keys) | LLM provider monitoring | STORM → GPT Researcher → manual research |
| **GPT Researcher** | multi-agent | 2 | **Free** (open source)<br>**Per run:** ~$0.01 (GPT-4)<br>**Deep Research:** ~$0.40 (o3-mini high) | ⏱️ 2-5 min (standard)<br>⏳ 5-15 min (deep) | 9/10 | Мature open-source research agent; planner+executors+publisher; 20+ sources; PDF/DOCX/Markdown export | Зависит от search API (Tavily/etc); токены LLM основная статья расходов | N/A (self-hosted) | 92% | Medium (Docker or pip install) | API key rotation | GPT Researcher → STORM → Jina DeepSearch |

---

## 3. Сравнительные таблицы по категориям

### 3.1 Search Tools Comparison

| Metric | web_search (native) | Jina Search | Jina DeepSearch | browser_visit |
|--------|---------------------|-------------|-----------------|---------------|
| **Cost per 1K queries** | $0 | ~$0.02 | $0.10-$2.00* | $0 |
| **Latency (median)** | 2s | 3s | 60s | 7s |
| **Source attribution** | Partial | Yes | Full citations | Visual only |
| **Paywall bypass** | No | No | Partial | No |
| **Best depth** | Surface | Surface | Deep | Visual confirmation |
| **LLM-friendly output** | Yes | Yes | Yes | No (raw HTML) |

*Зависит от токен-бюджета и глубины

### 3.2 Scraping Tools Comparison (Latency vs Cost)

| Tool | Cost per 1K pages | Latency P95 | JS Rendering | Stealth | Best for |
|------|-------------------|-------------|--------------|---------|----------|
| curl_cffi | $0 (infra only) | 500ms | No | TLS only | Static sites, API endpoints |
| Jina Reader | $5 | 2.1s | Yes (basic) | No | Quick markdown extraction |
| CloakBrowser | $0 (infra only) | 5s | Yes | Full (C++ patches) | Stealth automation |
| Firecrawl | $16-679/mo | 3.4s | Yes | Partial | Professional scraping at scale |
| Browserbase | $20-99+/mo | 2s | Yes | Full + captcha | Complex interactive workflows |

### 3.3 CAPTCHA Solvers Comparison

| Service | Speed | reCAPTCHA v2/1K | Turnstile/1K | Method | Best for |
|---------|-------|-----------------|--------------|--------|----------|
| CapSolver | 2-5s | $0.80 | $1.20 | AI/ML | Speed, Cloudflare, high volume |
| Anti-Captcha | 5s | $0.95-2.00 | $2.00 | Human | Lowest price images, reliability |
| 2Captcha | 13s | $1.00-2.99 | $1.45 | Human | Widest type support, accuracy |
| FastCaptcha | 0.3s | $1.00 | $1.00 | AI | Ultra-fast, budget |

### 3.4 Multi-Agent Research Comparison

| Framework | Cost/run | Time | Sources | Output | Best for |
|-----------|----------|------|---------|--------|----------|
| GPT Researcher | $0.01-0.40 | 2-15 min | 20+ | PDF/DOCX/MD | General research, reports |
| STORM | $0.05-0.50 | 5-15 min | 50-100 | Wikipedia-style article | Long-form writing with citations |
| ECC | N/A (framework) | Varies | N/A | Code/Skills | Development workflow automation |

---

## 4. Cost Estimation Calculator

### 4.1 Базовая формула

```
Total Cost = Σ(Native Tools) + Σ(API Calls) + Σ(CAPTCHA) + Σ(Infrastructure) + Σ(LLM Tokens) + Hidden Costs
```

### 4.2 Детальная формула

```
Total Research Cost = 
    Base_LLM_Cost                          // Стоимость токенов Claude/ChatGPT
    + (WebSearch_Qty × WebSearch_Cost)     // $0 для native, ~$0.02 для Jina
    + (Scrape_Qty × Scrape_Cost_Per_Page)  // $0.005 Jina, $0.0008 Firecrawl (Standard)
    + (Browser_Hours × Browser_Rate)       // $0.02-0.12/hr (Browserbase)
    + (CAPTCHA_Qty × CAPTCHA_Cost)         // $0.0008-0.003 per solve
    + (Data_API_Calls × Data_API_Cost)     // $0 для free tiers
    + (MultiAgent_Runs × MA_Cost_Per_Run)  // $0.01-0.50 для GPT Researcher/STORM
    + Verification_Overhead                 // 10-20% на повторные проверки
    + Proxy_Cost                            // Если используются
```

### 4.3 Примеры расчётов

#### Сценарий A: Базовое исследование (Depth Level 1)
```
- 10 web_search queries (native)        = $0
- 5 Jina Reader extractions              = $0 (free tier)
- 0 CAPTCHA                              = $0
- LLM processing (~50K tokens)           = ~$0.50
─────────────────────────────────────────────────
Total: ~$0.50 per research task
Monthly (100 tasks): ~$50
```

#### Сценарий B: Стандартное исследование (Depth Level 2)
```
- 50 web_search queries (native)         = $0
- 30 Jina Reader extractions             = $0.15 (остаётся в free tier)
- 10 Firecrawl scrape (Hobby plan)       = $16/mo / 300 = $0.05 per page
- 5 CAPTCHA solves (CapSolver)           = 5 × $0.0008 = $0.004
- 1 GPT Researcher run (standard)        = $0.01
- LLM processing (~200K tokens)          = ~$2.00
─────────────────────────────────────────────────
Total: ~$2.21 per research task
Monthly (100 tasks): ~$221 → округляем до $220 + $16 (Hobby) = $236
```

#### Сценарий C: Глубокое исследование (Depth Level 3)
```
- 100 web_search queries (native)        = $0
- 50 Jina Reader extractions             = $0.25
- 30 Firecrawl scrape (Standard 100K)    = $83/mo / 100K = $0.00083 per page
- 20 CAPTCHA solves (CapSolver)          = 20 × $0.0008 = $0.016
- 1 Jina DeepSearch (token budget 100K)  = ~$2.00
- 1 GPT Researcher Deep Research         = $0.40
- 1 STORM run                            = $0.25
- Browserbase: 2 hours                   = $0.20
- LLM processing (~1M tokens)            = ~$10.00
- Verification (archive + factcheck)     = $0
─────────────────────────────────────────────────
Total: ~$13.08 per deep research task
Monthly (50 tasks): ~$654 + $83 (Standard) = $737
```

#### Сценарий D: Enterprise-уровень (Depth Level 4)
```
- 500 web_search queries                 = $0
- 200 Jina Reader                        = $1.00
- 200 Firecrawl (Growth 500K)            = $333/mo / 500K = $0.00067 per page
- 100 CAPTCHA (CapSolver)                = $0.08
- 10 Jina DeepSearch                     = $20.00
- 10 GPT Researcher Deep Research        = $4.00
- Browserbase: 50 hours (Startup)        = $9.90
- Dedicated proxies (10GB)               = $50.00
- LLM processing (~10M tokens)           = ~$100.00
- ECC framework orchestration            = $0
─────────────────────────────────────────────────
Total: ~$185.00 per enterprise research
Monthly (100 tasks): ~$18,500 + подписки ($333 + $99) = $18,932
```

### 4.4 Параметрический калькулятор

```python
def estimate_research_cost(
    depth_level: int,           # 1-4
    pages_to_scrape: int,       # Количество страниц для scraping
    search_queries: int,        # Количество поисковых запросов
    captcha_expected: int,      # Ожидаемое количество CAPTCHA
    browser_hours: float,       # Часы использования cloud browser
    use_deep_search: bool,      # Использовать ли глубокий поиск
    use_multi_agent: bool,      # Использовать ли multi-agent framework
    llm_tokens_k: int,          # Тысячи токенов LLM
    firecrawl_plan: str = "Standard",  # Free/Hobby/Standard/Growth/Scale
    captcha_provider: str = "CapSolver",  # CapSolver/2Captcha/AntiCaptcha
    jina_usage: bool = True,    # Использовать Jina Reader
):
    """
    Параметрический калькулятор стоимости исследования.
    
    Returns: dict с breakdown по категориям и total.
    """
    costs = {
        "native_tools": 0,
        "scraping": 0,
        "captcha": 0,
        "browser": 0,
        "deep_search": 0,
        "multi_agent": 0,
        "llm": 0,
        "infrastructure": 0,
        "verification": 0,
    }
    
    # Native tools всегда free
    costs["native_tools"] = 0
    
    # Scraping costs
    if jina_usage and pages_to_scrape <= 600:  # free tier 20/day
        costs["scraping"] = 0
    elif jina_usage:
        costs["scraping"] = (pages_to_scrape * 5) / 1000  # $5/1K
    
    # Firecrawl plan costs (monthly amortized per page)
    firecrawl_rates = {
        "Free": (0, 1000),
        "Hobby": (16, 3000),
        "Standard": (83, 100000),
        "Growth": (333, 500000),
        "Scale": (679, 1000000),
    }
    fc_monthly, fc_credits = firecrawl_rates.get(firecrawl_plan, (83, 100000))
    costs["infrastructure"] = fc_monthly  # monthly base
    
    # CAPTCHA costs
    captcha_rates = {
        "CapSolver": 0.0008,
        "2Captcha": 0.0015,
        "AntiCaptcha": 0.0012,
    }
    c_rate = captcha_rates.get(captcha_provider, 0.0008)
    costs["captcha"] = captcha_expected * c_rate
    
    # Browser costs
    if browser_hours > 0:
        costs["browser"] = max(20, browser_hours * 0.12)  # min $20 plan
    
    # Deep search
    if use_deep_search:
        costs["deep_search"] = 2.0 * depth_level  # приблизительно
    
    # Multi-agent
    if use_multi_agent:
        costs["multi_agent"] = 0.4 * depth_level
    
    # LLM (Claude Sonnet ~$3/M input tokens)
    costs["llm"] = (llm_tokens_k * 3) / 1000
    
    # Verification overhead (~10%)
    subtotal = sum(costs.values())
    costs["verification"] = subtotal * 0.10
    
    costs["total"] = subtotal + costs["verification"]
    return costs
```

---

## 5. Budget Allocation Templates

### 5.1 Depth Level 1: Quick Scan ($0-10/task)

> **Цель:** Быстрая проверка фактов, поверхностный обзор темы

| Category | Tool | Allocation | Monthly Budget |
|----------|------|------------|----------------|
| Search (80%) | Native web_search | $0 | $0 |
| Scraping (15%) | Jina Reader (free tier) | $0 | $0 |
| LLM (5%) | Claude Desktop | ~$0.50/task | $50 (100 tasks) |
| **Total** | | **~$0.50/task** | **~$50/mo** |

**Recommended stack:** `web_search` → `Jina Reader` (free) → `ipython` analysis

### 5.2 Depth Level 2: Standard Research ($2-5/task)

> **Цель:** Структурированный отчёт с 10-20 источниками

| Category | Tool | Allocation | Monthly Budget |
|----------|------|------------|----------------|
| Search (30%) | Native web_search + Jina Search | $0.02/task | $2 |
| Scraping (40%) | Firecrawl Hobby ($16/mo) | $0.16/task | $16 |
| CAPTCHA (5%) | CapSolver | $0.01/task | $1 |
| Multi-Agent (10%) | GPT Researcher | $0.01/task | $1 |
| LLM (15%) | Claude Desktop | ~$0.75/task | $75 |
| **Total** | | **~$0.95/task** | **~$95/mo** |

**Recommended stack:** `web_search` → `Jina Reader` → `Firecrawl` (при необходимости JS) → `GPT Researcher` → `factcheck.org`

### 5.3 Depth Level 3: Deep Research ($10-25/task)

> **Цель:** Исчерпывающий отчёт с 30-50+ источниками, проверкой фактов, анализом данных

| Category | Tool | Allocation | Monthly Budget |
|----------|------|------------|----------------|
| Search (15%) | Native + Jina Search + DeepSearch | $2.00/task | $100 |
| Scraping (25%) | Firecrawl Standard ($83/mo) | $0.83/task | $83 |
| Browser (15%) | Browserbase Developer | $0.20/task | $20 |
| CAPTCHA (5%) | CapSolver | $0.02/task | $2 |
| Multi-Agent (15%) | GPT Researcher Deep + STORM | $0.65/task | $65 |
| Data Sources (10%) | Native get_data_source | $0 | $0 |
| LLM (15%) | Claude Desktop | ~$3.00/task | $300 |
| **Total** | | **~$6.70/task** | **~$570/mo** |

**Recommended stack:** `web_search` → `Jina DeepSearch` → `Firecrawl Standard` → `Browserbase` (interactive) → `GPT Researcher Deep` → `STORM` → `archive.org` verification → `get_data_source` (finance/academic)

### 5.4 Depth Level 4: Enterprise Intelligence ($50-200/task)

> **Цель:** Полномасштабное исследование: 100+ источников, первичные данные, мониторинг, аналитика

| Category | Tool | Allocation | Monthly Budget |
|----------|------|------------|----------------|
| Search (10%) | All search tools | $5.00/task | $500 |
| Scraping (20%) | Firecrawl Growth ($333/mo) | $3.33/task | $333 |
| Browser (15%) | Browserbase Startup ($99/mo) | $0.99/task | $99 |
| CAPTCHA (5%) | CapSolver + 2Captcha backup | $0.20/task | $20 |
| Multi-Agent (15%) | GPT Researcher + STORM + ECC | $8.00/task | $800 |
| Data Sources (10%) | All native + custom APIs | $2.00/task | $200 |
| Proxies (10%) | Residential proxies (10GB) | $5.00/task | $500 |
| LLM (15%) | Claude + custom models | ~$15.00/task | $1500 |
| **Total** | | **~$39.52/task** | **~$3,952/mo** |

**Recommended stack:** Full stack + `ECC orchestration` + `CloakBrowser` (self-hosted) + `dedicated proxies` + `parallel execution`

---

## 6. Cost Optimization Tips

### 6.1 Must-Do (Экономия 50-80%)

1. **Всегда начинайте с native tools.** `web_search`, `browser_visit`, `ipython` — бесплатны и покрывают 70% задач. Используйте paid APIs только когда native инструментов недостаточно.

2. **Используйте Jina Reader free tier максимально.** 20 requests/day = 600/month. Для большинства задач этого достаточно. Добавьте `r.jina.ai/` prefix к URL — никакой регистрации не требуется.

3. **Кэшируйте результаты scraping.** Не скрейпите одну и ту же страницу дважды. Используйте `read_file` для проверки наличия cached данных перед вызовом API.

4. **CapSolver вместо 2Captcha для высоких объёмов.** $0.80/1K vs $1.00-2.99/1K — экономия до 73%. CapSolver быстрее (2-5s vs 13-30s) и надёжнее для Cloudflare.

### 6.2 Should-Do (Экономия 20-50%)

5. **Выбирайте правильный Firecrawl план.** При <3K страниц/мес берите Hobby ($16), не Standard ($83). При >100K страниц Growth ($333) окупается vs Standard. Credits не переносятся — не переплачивайте.

6. **Используйте curl_cffi для static sites.** При скрейпинге статических сайтов curl_cffi в 5-10x быстрее и дешевле чем headless browser. Переключайтесь на браузер только при необходимости JS-рендеринга.

7. **Батчинг запросов.** Группируйте Firecrawl scrape calls в batch jobs. 100 отдельных запросов медленнее и дороже чем 1 batch на 100 страниц.

8. **CloakBrowser вместо Browserbase для регулярных задач.** Если нужен stealth браузер для предсказуемых workflow — self-hosted CloakBrowser = $0 vs $20-99+/mo Browserbase.

9. **GPT Researcher вместо коммерческих research API.** $0.01-0.40/run vs $5-20 за аналогичный отчёт от коммерческих провайдеров.

### 6.3 Nice-to-Do (Экономия 10-20%)

10. **Мониторьте token usage.** Используйте `/cost` в Claude Code и устанавливайте `MAX_THINKING_TOKENS`. Компактифицируйте (`/compact`) на логических breakpoints.

11. **Амортизируйте Browserbase часы.** Планируйте browser session на конкретное время — не держите idle browsers. Overage стоит $0.10-0.12/hr.

12. **2Captcha для сложных CAPTCHA, CapSolver для простых.** Гибридный подход: CapSolver для reCAPTCHA v2/v3 (AI справляется), 2Captcha только для сложных типов (FunCaptcha, TikTok).

13. **Используйте `get_data_source` вместо scraping для structured data.** Yahoo Finance, arXiv, World Bank — уже интегрированы и не требуют дополнительных вызовов.

14. **Параллельное выполнение с ECC.** Используйте `/multi-plan` и `/multi-execute` для распараллеливания независимых задач — ускорение до 3-5x.

15. **Stealth rotation: CloakBrowser + Browserbase fallback.** Для масштабных операций: CloakBrowser (self-hosted) как primary → Browserbase при блокировке. Экономия 60-80% vs Browserbase-only.

---

## 7. Hidden Costs Matrix

| Tool | Hidden Cost | Impact | Mitigation |
|------|-------------|--------|------------|
| **Jina Reader** | ReaderLM-v2 стоит 3x токены; крупные страницы потребляют больше токенов | 3x расход при сложных сайтах | Использовать default pipeline где возможно |
| **Jina Reader** | Timeout на медленных страницах = потраченные токены без результата | Потеря ~10-20% вызовов | Устанавливать адекватный timeout |
| **Firecrawl** | Credits не переносятся на следующий месяц | Потеря неиспользованных credits | Точное планирование объёмов |
| **Firecrawl** | FIRE-1 agent всегда биллится, даже при ошибке | Плата за failed requests | Использовать standard scrape где возможно |
| **Firecrawl** | Search стоит 2 credits per 10 results | 2x стоимость vs scrape | Использовать native web_search для поиска |
| **Browserbase** | Overage: $0.10-0.12/hr после лимита | +50-100% к счёту при пиках | Мониторинг hours; авто-shutdown idle sessions |
| **Browserbase** | Proxy overage: $10-12/GB | $50-100+ при интенсивном использовании | Собственные прокси; кэширование |
| **Browserbase** | Search API: $7/1K после лимита | Внезапные расходы при массовом поиске | Использовать Jina Search как primary |
| **2Captcha** | Минимальный платёж $3; средства не возвращаются | Блокировка $3 при низком usage | CapSolver для низких объёмов (PAYG) |
| **CapSolver** | Cloudflare Challenge требует proxy (доп. расход) | +$5-10/GB на прокси | Использовать CloakBrowser для предотвращения |
| **CloakBrowser** | Требует собственные прокси ($5-50/mo) | Инфраструктурные расходы | Бесплатные proxy lists для разработки |
| **CloakBrowser** | Chrome updates могут ломать патчи | Необходимость ручного обновления | Автоматизация через Docker + watchtower |
| **curl_cffi** | TLS fingerprinting не справляется с JS-challenge | Потраченное время на debugging | Быстрый fallback к CloakBrowser |
| **GPT Researcher** | Tavily API требует отдельную регистрацию | Ещё один API key для управления | Self-hosted с кастомным search backend |
| **STORM** | Длительное выполнение = накопление LLM costs | $0.50 может превратиться в $5 при ошибках | Token budget caps; timeout monitoring |
| **ECC** | Plugin conflicts при обновлениях Claude Code | Потеря времени на debugging | `ECC_HOOK_PROFILE=minimal`; `/repair` command |
| **Native browser** | Нет stealth-режима = блокировка сайтами | Потеря времени на retry | Быстрый fallback chain к CloakBrowser |

---

## 8. Fallback Chains

### 8.1 Universal Fallback Chain

```
Level 1 (Free):     web_search → browser_visit → ipython analysis
Level 2 (Low-cost): Jina Reader → Jina Search → curl_cffi
Level 3 (Mid):      Firecrawl → CloakBrowser → CapSolver
Level 4 (Full):     Browserbase → 2Captcha → STORM/GPT Researcher
```

### 8.2 Category-Specific Chains

#### Scraping Fallback Chain
```
curl_cffi (static) → Jina Reader (quick markdown) → Firecrawl (JS render) 
    → CloakBrowser (stealth) → Browserbase (full cloud) + CapSolver (captcha)
```

#### Search Fallback Chain
```
web_search (native) → Jina Search (LLM-friendly) → Jina DeepSearch (recursive)
    → browser_visit + manual exploration → GPT Researcher (multi-agent)
```

#### Browser Automation Fallback Chain
```
browser_visit (native) → CloakBrowser (stealth self-hosted)
    → Browserbase Developer ($20) → Browserbase Startup ($99)
    → Browserbase Scale (custom) + dedicated proxies
```

#### CAPTCHA Fallback Chain
```
CloakBrowser (prevention) → CapSolver (AI, fast, cheap)
    → Anti-Captcha (cheapest images) → 2Captcha (widest support)
    → Manual solving (last resort)
```

#### Verification Fallback Chain
```
Wikipedia (quick) → web_search cross-reference → archive.org (historical)
    → factcheck.org (political) → snopes (general) → primary sources
```

### 8.3 Failure Decision Tree

```
Запрос выполнен?
├── Нет → Ошибка сети?
│   ├── Да → Retry × 3 → Другой provider
│   └── Нет → CAPTCHA?
│       ├── Да → CapSolver → Retry
│       └── Нет → Paywall?
│           ├── Да → archive.org → Jina Reader
│           └── Нет → JS-required?
│               ├── Да → Firecrawl → CloakBrowser → Browserbase
│               └── Нет → Rate limited?
│                   ├── Да → Пауза → Proxy rotation
│                   └── Нет → Unknown → Log → Skip → Fallback
└── Да → Quality adequate?
    ├── Да → Cache result → Continue
    └── Нет → Alternative source?
        ├── Да → Switch source
        └── Нет → Lower standards → Flag for review
```

---

## 9. Частотные сценарии использования

### Сценарий: "Быстрая проверка факта"
**Tools:** `web_search` (native)
**Cost:** $0
**Time:** 5-15 seconds
**Quality:** 7/10

### Сценарий: "Извлечь статью в markdown"
**Tools:** `r.jina.ai/{url}` (Jina Reader free tier)
**Cost:** $0 (до 20/day)
**Time:** 2-3 seconds
**Quality:** 8/10

### Сценарий: "Проскрейпить JS-heavy сайт"
**Tools:** `Firecrawl scrape_url` → `browser_screenshot` (verify)
**Cost:** $0.00083-0.005/page
**Time:** 3-10 seconds
**Quality:** 9/10

### Сценарий: "Обойти Cloudflare"
**Tools:** `CloakBrowser` (prevention) → `CapSolver` (if challenged)
**Cost:** $0 + $0.001-0.003/solve
**Time:** 3-15 seconds
**Quality:** 8/10

### Сценарий: "Глубокое исследование темы"
**Tools:** `Jina DeepSearch` + `GPT Researcher` + `factcheck.org`
**Cost:** $2-5
**Time:** 5-15 minutes
**Quality:** 9/10

### Сценарий: "Финансовый анализ"
**Tools:** `get_data_source` (Yahoo Finance, Stock Finance) + `get_data_source` (World Bank/IMF)
**Cost:** $0
**Time:** 10-30 seconds
**Quality:** 9/10

### Сценарий: "Академическое исследование"
**Tools:** `get_data_source` (arXiv, Scholar) + `GPT Researcher` (deep)
**Cost:** $0.01-0.40
**Time:** 2-10 minutes
**Quality:** 9/10

### Сценарий: "Мониторинг цен / конкурентов"
**Tools:** `curl_cffi` (static) → `CloakBrowser` (if blocked) → `Firecrawl` (schedule)
**Cost:** $0-16/month
**Time:** 1-5 minutes setup, automated runs
**Quality:** 8/10

### Сценарий: "Проверка юридических документов (КНР)"
**Tools:** `get_data_source` (Yuandian Law) + `web_search` (cross-reference)
**Cost:** $0
**Time:** 10-30 seconds
**Quality:** 7/10

---

## 10. Итоговые рекомендации

### Для индивидуального исследователя ($0-50/мес)
- **Primary:** Все native tools + Jina Reader (free tier)
- **Fallback:** curl_cffi для static scraping
- **Research:** GPT Researcher ($0.01/run)
- **CAPTCHA:** CapSolver (PAYG, минимальные объёмы)

### Для команды/стартапа ($50-500/мес)
- **Primary:** Native tools + Firecrawl Standard ($83) + Jina Search
- **Browser:** CloakBrowser (self-hosted, $0) + Browserbase Developer ($20) fallback
- **CAPTCHA:** CapSolver ($0.80/1K)
- **Research:** GPT Researcher Deep + STORM
- **Orchestration:** ECC framework

### Для enterprise ($500+/мес)
- **Primary:** Full stack + Firecrawl Growth ($333) + Browserbase Startup ($99)
- **Proxies:** Dedicated residential (10GB+)
- **CAPTCHA:** CapSolver + 2Captcha backup
- **Multi-Agent:** GPT Researcher + STORM + ECC orchestration
- **Monitoring:** Custom cost tracking, auto-fallback chains

### Золотые правила

1. **Tier 1 first:** Всегда начинайте с native tools — они бесплатны и мощны
2. **Prefix power:** `r.jina.ai/` превращает любой URL в markdown без регистрации
3. **Prevention > Solving:** CloakBrowser предотвращает CAPTCHA дешевле чем их решение
4. **Cache everything:** Не платите дважды за один и тот же контент
5. **Measure:** Используйте `/cost` в Claude Code и отслеживайте расходы

---

## Appendix A: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│              DEEP RESEARCH SKILL - COST CHEAT SHEET             │
├─────────────────────────────────────────────────────────────────┤
│ FREE TIER (per month):                                          │
│   • web_search:           unlimited                             │
│   • browser_visit:        ~20-50/session                        │
│   • Jina Reader:          20/day (600/mo)                       │
│   • Jina Search:          10M tokens                            │
│   • get_data_source:      ~50-100 calls/day each                │
│   • Firecrawl:            1,000 credits                         │
│   • Browserbase:          1 browser hour                        │
│   • curl_cffi:            unlimited                             │
│   • CloakBrowser:         unlimited                             │
│   • ECC/STORM/GPT Res:    unlimited (self-hosted)               │
├─────────────────────────────────────────────────────────────────┤
│ CHEAPEST PAID:                                                  │
│   • CapSolver:            $0.80/1K captcha solves               │
│   • Firecrawl Hobby:      $16/mo (3K pages)                     │
│   • Browserbase Dev:      $20/mo (100 hrs)                      │
│   • Anti-Captcha:         $0.50/1K image CAPTCHA                │
│   • Jina Reader:          $5/1K requests                        │
├─────────────────────────────────────────────────────────────────┤
│ QUALITY TIERS:                                                  │
│   • 9-10/10: Fact verification, academic data, Firecrawl       │
│   • 7-8/10:  Jina Reader, CloakBrowser, browser tools          │
│   • 5-6/10:  Basic search, image search                        │
├─────────────────────────────────────────────────────────────────┤
│ FASTEST:                                                        │
│   • web_search:           1-3s                                  │
│   • curl_cffi:            100-500ms                             │
│   • Jina Reader:          1-3s                                  │
│   • Binance API:          <100ms                                │
├─────────────────────────────────────────────────────────────────┤
│ SLOWEST:                                                        │
│   • STORM:                5-15 min                              │
│   • GPT Researcher Deep:  5-15 min                              │
│   • Jina DeepSearch:      30-120s                               │
│   • 2Captcha:             13-30s                                │
└─────────────────────────────────────────────────────────────────┘
```

## Appendix B: Tool URLs

| Tool | URL / Command |
|------|---------------|
| Jina Reader | `https://r.jina.ai/{URL}` |
| Jina Search | `https://s.jina.ai/{query}` |
| Jina DeepSearch | `https://github.com/jina-ai/deepsearch` |
| Firecrawl | `https://www.firecrawl.dev` |
| curl_cffi | `pip install curl_cffi` |
| CloakBrowser | `pip install cloakbrowser` / `npm install cloakbrowser` |
| Browserbase | `https://www.browserbase.com` |
| CapSolver | `https://www.capsolver.com` |
| 2Captcha | `https://2captcha.com` |
| Anti-Captcha | `https://anti-captcha.com` |
| ECC | `https://github.com/affaan-m/ECC` |
| STORM | `https://github.com/stanford-oval/storm` |
| GPT Researcher | `https://github.com/assafelovic/gpt-researcher` |
| Archive.org | `https://web.archive.org/save/{URL}` |
| FactCheck.org | `https://www.factcheck.org` |
| Snopes | `https://www.snopes.com` |

---

> **Disclaimer:** Цены актуальны на июнь 2025 и могут измениться. Всегда проверяйте актуальные тарифы на официальных сайтах провайдеров перед принятием решений.
