# OpenResearcher → Deep Research Skill (DRS): отчёт по переиспользованию

## 1. Что такое OpenResearcher (кратко)

**OpenResearcher** (TIGER-AI-Lab) — это полностью открытый пайплайн для **обучения, сервинга и бенчмаркинга** deep-research LLM (OpenResearcher-30B-A3B). Это **GPU-инфраструктура вокруг модели**, а не skill-обёртка как DRS. Архитектурные слои:

- **Агентский loop** (`deploy_agent.py` + `run_agent.sh`): per-question ReAct-loop (до 200 раундов) поверх сырой модели через `tokenizer.apply_chat_template(tools=...)`; планирование делегируется native function-calling самой модели. Two-tier парсинг tool-call (json5 -> regex/XML fallback), stop-string truncation на `<tool_response>`, DB-free distributed resumption через shard-glob + qid-dedup.
- **Retrieval-стек** (`browser.py`, `backend.py`, `scripts/deploy_search_service.py`): tool-surface search/open/find поверх сменных бэкендов — локальный BM25 (pyserini/Lucene) или Dense (Qwen3-Embedding + FAISS) над self-hosted корпусом (~11B токенов), либо live-web через Serper API. Всё нормализуется через один `process_html()`.
- **Слой оценки** (`eval.py`, `benchmarks.md`): offline LLM-as-judge грейдер против known `correct_answer`, dual-denominator accuracy, rate-limiter + backoff, корреляция tool-usage vs correctness, реестр бенчмарков (BrowseComp, BrowseComp-Plus, GAIA-text, xbench).
- **AI-инфра** (`data_utils.py`, `utils/openai_generator.py`, `utils/vllm_generator.py`): конфиг-загрузка, формат цитирования 【id†L..】, JSON-схема browser-инструментов, unified generator interface над HTTP-API и in-process vLLM.

**Ключевой вывод:** OR решает другую задачу (обучить/захостить/замерить модель), поэтому ~60% кодовой базы (vLLM/Megatron/локальный корпус/generator-adapter) для DRS **нерелевантно**. Ценность сосредоточена в четырёх узких зонах: устойчивый парсинг вывода LLM, формат цитирования, слой оценки качества, мелкие robustness-паттерны сбора.

---

## 2. Сводная таблица переиспользования

| Приоритет | Фича | Источник (OR) → Куда (DRS) | Тип | Усилия |
|---|---|---|---|---|
| 🔴 high | Two-stage парсинг вывода LLM (json5 -> regex-fallback) | `deploy_agent.py` → `engine/factcheck.py`, `verify.py`, `plan.py` | pattern | low |
| 🔴 high | Citation-формат 【id†L{start}-L{end}】 + лимит 10 слов | `data_utils.py` → SKILL.md (Phase 4/5), `engine/report.py` | prompt | low |
| 🔴 high | Dual-denominator accuracy (Judged vs Overall) | `eval.py` → `bench/`, `engine/eval.py` | pattern | low |
| 🔴 high | LLM-as-judge grader + parse_judge_response | `eval.py` → `bench/judge.py` (новый) | code | medium |
| 🟡 med | Санитизация запроса (smart-quotes/непарные кавычки) | `deploy_search_service.py`, `browser.py` → `engine/collect.py`/`providers.py` | code | low |
| 🟡 med | Multi-query fan-out с частичным отказом | `browser.py` → `engine/collect.py` | pattern | low |
| 🟡 med | ThreadRateLimiter + exponential backoff | `eval.py` → `engine/providers.py` | code | medium |
| 🟡 med | Always-emit-record-on-failure | `deploy_agent.py` → `engine/telemetry.py`, `report.py` | pattern | low |
| 🟡 med | Tool-usage vs correctness correlation | `eval.py` → `bench/` | idea | medium |
| 🟢 low | Реестр + внешний benchmark-suite | `benchmarks.md` → `bench/BENCHMARKS.md` | idea | high |
| 🟢 low | Session fetch-cache по URL + force-refresh | `browser.py` → `engine/collect.py`/`cache.py` | pattern | medium |
| 🟢 low | Env-driven factory + preflight checks | `backend.py`, `start_search_service.sh` → `engine doctor` | config | low |
| 🟢 low | Логирование response.text при HTTPStatusError | `utils/openai_generator.py` → `engine/providers.py` | code | low |
| 🟢 low | parse_opts_to_config (`a.b.c=value`) | `data_utils.py` → `engine/state.py`/`cli.py` | code | low |

---

## 3. Топ-рекомендации (детали)

### 3.1 🔴 Two-stage парсинг вывода LLM (lenient-then-strict)
**Источник:** `tmp/OpenResearcher/deploy_agent.py` — dual-format tool-call parsing.
**Куда:** `engine/factcheck.py`, `engine/verify.py` (парсинг free-text вердиктов), `engine/plan.py` (plan JSON).
OR сначала пробует `json5.loads` (терпит near-valid JSON), при провале — regex-fallback (`<function=name>`/`<parameter=x>`) с coercion digit-string -> int. DRS постоянно потребляет полу-структурный вывод модели (6-категорийные вердикты FCA). Паттерн снижает хрупкие сбои на near-miss синтаксисе, затрагивая **только input-boundary**, не сам типизированный контракт.
**Риск:** мягкий парс может «проглотить» семантически неверный вывод — обязательно валидировать результат через `model.validate_*` после парса, а не доверять факту успешного `parse`.

### 3.2 🔴 Формат цитирования с привязкой к строкам + лимит дословности
**Источник:** `tmp/OpenResearcher/data_utils.py` — `DEVELOPER_CONTENT` / `TOOL_CONTENT`.
**Куда:** промпты FactCheck-агента и фазы синтеза в SKILL.md; рендер сносок в `engine/report.py`.
Формат 【{id}†L{start}-L{end}】 + правило «не более 10 слов дословной цитаты» даёт **verifiable citation** — не URL, а конкретный диапазон строк. Это прямое усиление anti-hallucination DRS: и `verify.py`, и человек могут сверить цитату по строке; лимит 10 слов снижает риск копирайт-воспроизведения.
**Риск:** `ingest.source_from_raw` должен сохранять стабильную нумерацию строк, иначе ссылки протухают между ре-фетчами. Это предусловие внедрения.

### 3.3 🔴 Dual-denominator accuracy + LLM-as-judge grader
**Источник:** `tmp/OpenResearcher/eval.py` — `GRADER_TEMPLATE`, `parse_judge_response()`, `LLMJudge`, `__main__` (PrettyTable).
**Куда:** `bench/` reporting, новый `bench/judge.py`.
Два взаимодополняющих приёма. (а) **Dual accuracy**: `Judged` = correct/parsed-ok против `Overall` = correct/total — сбои судьи/парсинга не маскируются под ошибки движка. У DRS уже есть 'honesty ledger' в `bench/README.md`, признающий fidelity-gap; эта метрика чисто аддитивна. (б) **Grader** с шагом `extracted_final_answer` перед yes/no (форс-коммит снижает waffling) + regex-каскад, толерантный к markdown-вариациям вердикта. Закрывает главный gap bench/: DRACO judge не запинен и оценивает рукописный отчёт, а не вывод `engine.run_pipeline`.
**Риск:** судья добавляет стоимость/недетерминизм — держать СТРОГО вне детерминированного движка (как уже сделано для DRACO); нужен независимый/запиненный судья во избежание self-preference bias.

### 3.4 🟡 Robustness-набор для collect/providers
Три дешёвых паттерна, закрывающих признанные gaps `engine/`:
- **Санитизация запроса** (`deploy_search_service.py`, `browser.py`): нормализация smart-кавычек + удаление непарных до вызова провайдера → `engine/collect.py`. Несколько строк, устраняет класс сбоев 'malformed quotes'. Совместимо с cost-first (провал запроса = потраченный бюджет).
- **Multi-query fan-out с частичным отказом** (`browser.py`): `asyncio.gather`, пустой под-запрос логируется и продолжает, ошибка только если ВСЕ пусты → `engine/collect.py`. Точно подходит под fan-out по под-задачам DAG. Результаты направлять в существующие `dedupe.py`/`rank.py` (RRF), не отдавать сырыми.
- **ThreadRateLimiter + backoff** (`eval.py`): закрывает признанный gap `providers.py` (нет retry/backoff/circuit-breaker). Интегрировать с `should_stop`/budget, чтобы retry не обходил cost-cap.

### 3.5 🟡 Always-emit-record + tool-usage correlation
- **Always-emit-record** (`deploy_agent.py`): `{status, error, attempts, latency_s}` даже при провале → `engine/telemetry.py`. Точно совпадает с audit-этосом DRS (Phase 6 приёмка, никаких silent drops).
- **Tool-usage vs correctness** (`eval.py`, `count_tool_usage`/`count_assistant_turns`): диагностика в `bench/`, эмпирически проверяющая cost-first иерархию — коррелирует ли over-invoke web_search/Jina/Firecrawl с confidence/качеством. Основа для тюнинга бюджетов фаз. Нормировать по depth-классу (корреляция != причинность).

---

## 4. Что брать не стоит

1. **vLLM/Megatron обучение и сервинг** (`scripts/deploy_vllm_service.py`, `start_nemotron_servers.sh`) — DRS не хостит и не обучает LLM; работает поверх Claude-хоста.
2. **Unified generator adapter** (HTTP vs in-process vLLM, `utils/*_generator.py`) — своего LLM-inference-транспорта у DRS нет, подменять нечего. (Паттерн адаптера DRS уже применяет к search-провайдерам.)
3. **Локальный self-hosted корпус** — BM25/pyserini + DenseSearcher (FAISS + Qwen3-Embedding), `Corpus` over parquet, FAISS integrity check (`backend.py`, `deploy_search_service.py`). DRS **осознанно** не хостит корпус; затраты несопоставимы с ценностью.
4. **'Fake-HTML round-trip'** — рендер search-результатов в `<ul><li>` под `web-search://` URL с ре-парсом (`browser.py`). Признанный анти-паттерн; `collect.normalize` уже отдаёт типизированные item-dict напрямую — чище.
5. **Chat-template tool-planning + stop-string truncation** (`deploy_agent.py`) — относятся к самостоятельному ReAct-loop поверх сырой модели; DRS использует native tool-calling Claude и детерминированный engine-CLI.
6. **Loose multi-pattern stop-condition** (`deploy_agent.py`) — у DRS уже есть `should_stop`-оракул (budget/done/stalled); рыхлое текст-матчинг снизило бы строгость.
7. **Shard-glob + qid-dedup resumption** (`deploy_agent.py`) — у DRS богаче checkpoint/resume (5 checkpoint'ов, migration ladder, checksum). Заимствовать нечего.
8. **XOR/SHA256/canary-decryption gold-ответов** (`data_utils.py`) — узко; только если DRS будет шипить собственные зашифрованные эталоны. Держать как отдалённую идею anti-contamination для bench.

---

## 5. Где DRS уже сильнее

| Измерение | DRS | OpenResearcher |
|---|---|---|
| **Anti-hallucination** | Независимая ре-верификация `verify.py` (classify БЕЗ hint/verdict) + 6 категорий + FCA-veto | Только binary yes/no LLM-judge финала против gold; нет per-claim ветирования |
| **Collection seam** | Типизированный `{status, summary, items[], next_valid_actions[]}`, snippet-cap, risk_class | build-HTML->reparse; multi-query без dedup/fusion |
| **Confidence** | `score.py` 5-компонентный взвешенный composite -> Tier S-D + шкала 1-5, auditable breakdown | Нет framework (judge confidence 0-100 как метаданные) |
| **Source Authority** | Tier S/A/B/C/D + conflict resolution + детекция circular reporting | Отсутствует |
| **Dedupe / rank** | URL-канонизация + trigram/token Jaccard @0.85; RRF k=60 + tier-multiplier | Нет dedup и rank-fusion |
| **Injection defense** | Trust-fence: retrieved content = DATA, штамп только `ingest.source_from_raw` | Не описано |
| **Cost-first** | 4-уровневая иерархия + оценка до вызова + budget-guardrails | Бинарный local/serper switch |
| **Checkpoint/resume** | 5 checkpoint'ов, versioned migration ladder, checksum, staleness windows, budget carry-forward | Coarse shard-glob (гранулярность = целый вопрос) |
| **Trust-метрики** | `bench/trust/metrics.py` на реальном `run_pipeline`: byte-identical replay, suppression_recall, citation_completeness | Только accuracy финала |
| **Deployment** | Валидный prose-only fallback без Python/code-execution | Жёсткая привязка к vLLM/FastAPI/tokenizer |

**Итог:** DRS архитектурно зрелее OR по всей цепочке доверия (verify → score → authority → dedupe → injection → checkpoint). Из OR стоит взять точечно: устойчивость парсинга (3.1), verifiable-citation формат (3.2) и слой честной оценки качества (3.3) — именно там, где у DRS есть признанные gaps (fidelity-gap в bench/, отсутствие retry/backoff в providers.py, хрупкий парсинг free-text вердиктов).
