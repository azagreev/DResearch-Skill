# Rebuild Plan — spec-only → claim-центричный исполняемый движок

> **Статус:** план (source of truth). Код по фазам ещё не написан, кроме Phase 0 · STEP 0.
> **Решение зафиксировано:** полный rebuild слоя исполнения с нуля (своя архитектура, не клон last30days);
> **прозаический контракт сохраняется как spec-слой** (6 фаз, тиры S/A/B/C/D, confidence 1–5, cost-first, gates).
> Методология не выбрасывается — переписывается слой ИСПОЛНЕНИЯ.

---

## 0. Почему вообще

`Glob **/*.py` по всему репозиторию → **0 файлов**. `**/*.js` → ровно один (`examples/supervised_orchestrator.workflow.js`, вне пакета скилла).
Все 7 фаз (0–6), роутер, cost-matrix, тиры, FactCheck-агент, confidence, quality-gates — **прозаический контракт, который модель исполняет «в голове»**. Отсюда корень всех наблюдавшихся багов: re-fetch врёт про «0 вызовов», плавающий confidence, недетерминированный дедуп.

last30days — зеркальная противоположность: реальный Python-движок (`scripts/last30days.py` + ~60 модулей `lib/`), а SKILL.md лишь вызывает его.

**Вывод:** «оптимизировать» нечего (нет кода). Выбор — достроить **исполняемое ядро**: «модель делает в уме» → «модель оркеструет детерминированный пайплайн».

---

## 1. Целевая архитектура (наша, claim-центричная)

Ключевое отличие от last30days: **движок — пост-сборочный + state + верификация, НЕ краулер.**
Сбор остаётся за нативным Claude `web_search` (бесплатно, Tier-1). Модель = планировщик/сборщик/нарратор; движок = позвоночник, держащий state и инварианты.

```
МОДЕЛЬ (prose-контракт сохранён): план → web_search(free) → предлагает claims (JSON) → нарратив синтеза
                                        │ raw results + claims
                                        ▼
ДВИЖОК engine/ (Python, stdlib-only, проектируем с нуля):
  cli.py       единый шов: python -m engine <ingest|rank|score|factcheck|checkpoint|resume|memory|eval|report>
  model.py     TaskFrame, Source(tier S/A/B/C/D), Claim(verdict,confidence), EvidenceCluster, Snapshot  (== AGENT.MD §8.0 JSON)
  state.py     checkpoint save/load/resume, fingerprint, budget carry-forward, инварианты §8.0 В КОДЕ
  dedupe.py    URL-normalize + near-dup (детерминированно)
  rank.py      RRF-слияние мульти-запросов + authority-взвешивание
  score.py     ТВОЯ формула как реальная арифметика → tier + confidence 1–5
  freshness.py staleness-окна (Quick 24h / Standard 7d / Deep 14d), recency
  factcheck.py НОВОЕ, без донора: claim↔source cross-ref, 6 категорий вердиктов, детект противоречий
  cluster.py   evidence-кластеры вокруг claims (MMR-репрезентанты)
  memory.py    SQLite WAL+FTS5: кросс-прогонный дедуп + ретро («видели ли этот источник/claim»)
  eval.py      precision@k / nDCG@k / jaccard / coverage между релизами
  providers.py опц. Tier-4 платно (Brave/Exa/Serper) за ключами, DEFAULT OFF + env-паттерны
  report.py    6 форматов вывода + cluster-first
```

### Сознательные отклонения от last30days («другими подходами»)

| Их подход | Наш подход (почему) |
|---|---|
| Collection-first (краулер с API-ключами) | **Post-collection** поверх бесплатного Claude `web_search` — сохраняет cost-first |
| Скоринг на соц-engagement (лайки/репосты) | Скоринг на **authority + independence + corroboration + traceability** |
| Item/post-центричная модель | **Claim-центричная** (единица — проверяемое утверждение, не пост) |
| store как накопитель находок | memory **+ resumable checkpoint с инвариантом no-refetch** (§8.0 — first-class) |
| Нет фактчека | **Фактчек — ядро** (6 категорий, cross-ref, противоречия) |

---

## 2. Три риска полного rebuild (нельзя замолчать)

1. **Раскол аудитории по рантайму.** Сейчас скилл — чистые инструкции, работает в Claude Code И в claude.ai-ZIP без зависимостей. Движок требует **Python + включённый code-execution**. ⇒ обязателен **graceful degradation**: нет Python → откат в текущий prose-only режим (требование Phase 0).
2. **Спека ↔ код должны быть синхронны.** last30days держит это через `SKILL_DIR`-подстановку + stale-clone-check. Рассинхрон «SKILL.md говорит одно, движок делает другое» — главный будущий источник багов.
3. **Объём.** Это 6 релизов (0.5.0 → 1.0.0), не патч. Фактчек-ядро пишется без донора. Разбито так, чтобы **каждая фаза была отгружаемым релизом** с откатом.

---

## 3. План по фазам

### Phase 0 — Фундамент и защита рантайма (релиз 0.5.0)
- **Делаем:** (1) **stale-clone STEP 0** в SKILL.md — ✅ сделано (см. §4). (2) Runtime-контракт: детект `python` + code-execution; нет → prose-only fallback. (3) Скелет `engine/` + `NOTICE` (атрибуция MIT last30days за алгоритмы-референсы). (4) `python -m engine --version`.
- **Acceptance:** STEP 0 реально перечитывает свежий cache при stale-clone; `--version` запускается; без Python скилл работает как раньше.
- **Риск:** минимальный, аддитивно.

### Phase 1 — Модель данных + state (позвоночник) (0.6.0)
- **Цель:** «checkpoint — placeholder / resume по инструкции» → реальный сериализуемый объект.
- **Делаем:** `model.py` зеркалит §8.0 JSON 1:1 (round-trip); `state.py`: save/load/resume, fingerprint = sha1(normalize(question|route|depth|scope)), budget carry-forward, инварианты в коде (источники read-only на resume; highest-NN с fallback NN-1).
- **Acceptance:** snapshot→resume; fingerprint match/mismatch; **тест: мутация resumed-источника падает**.
- **Закрывает:** известное ограничение 0.2.0 «native resume не enforce-ит read-only».

### Phase 2 — Детерминированная обработка (0.7.0)
- **Делаем:** `dedupe.py`, `rank.py` (RRF + authority), `freshness.py`. SKILL.md Phase 2/3 передаёт raw web_search → `engine ingest`+`rank`.
- **Acceptance:** golden-set — одинаковый вход → байт-в-байт одинаковый ранжир; известные дубли схлопываются.

### Phase 3 — Скоринг (confidence/authority как реальная математика) (0.8.0)
- **Цель:** `Authority·0.30 + Recency·0.25 + Independence·0.20 + Traceability·0.15 + Corroboration·0.10` → код.
- **Делаем:** `score.py`: композит → tier S/A/B/C/D; verification-state → confidence 1–5. Phase 4 prose-confidence → вызов движка.
- **Acceptance:** известные источники → ожидаемый tier/confidence; сверка с ручными оценками прошлых прогонов.

### Phase 4 — Фактчек-ядро (уникальный слой, с нуля) (0.9.0)
- **Делаем:** `factcheck.py` + `cluster.py`: claim-extract (модель→JSON), cross-ref (supports/contradicts), 6-категорийный вердикт, детект противоречий, evidence-кластеры.
- **Acceptance:** на теме с известным противоречием движок флагует его; claim без ≥1 supporting-источника → unverified (не в «verified»).

### Phase 5 — Кросс-прогонная память + eval (0.10.0)
- **Делаем:** `memory.py` (SQLite WAL+FTS5+BM25, дедуп между прогонами, sightings-ledger); `eval.py` (precision@k/nDCG@k/jaccard/coverage).
- **Acceptance:** 2-й прогон по теме дедупит против 1-го (sighting_count++); eval считает метрики между релизами.

### Phase 6 — Вывод + платные провайдеры + оркестратор (1.0.0)
- **Делаем:** `report.py` (6 форматов + cluster-first); `providers.py` (Tier-4 платно, **default OFF**, env-паттерны: precedence-loader, .env-parse, JWT-expiry, Windows-aware perms); подключить `supervised_orchestrator.workflow.js` к CLI движка.
- **Acceptance:** полный прогон → отчёт с реальными citations+confidence; resume → **collection=0 (внешний счётчик)**; платный путь только при ключах.

---

## 4. Сквозной инвариант: спека ↔ код синхронны

Каждая фаза обновляет SKILL.md/AGENT.MD в том же релизе, что и код; CHANGELOG фиксирует, что стало executable. Иначе вернутся баги «инструкция врёт про поведение».

---

## 5. Лицензия / атрибуция

Алгоритмы-референсы (RRF, MMR, nDCG, jaccard, SQLite-FTS5 паттерн) вдохновлены MIT-скиллом `last30days` (автор mvanhorn). Код движка пишется заново; атрибуция — в `NOTICE` при появлении `engine/`.
