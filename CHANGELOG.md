# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-06-11

Исполняемый движок Phase 1–7 — **собран, протестирован и запускаем end-to-end** (66 юнит-тестов).
Phase 1: модель+state. Phase 2: dedupe/rank/freshness. Phase 3: authority-скоринг. Phase 4: фактчек+кластеры.
Phase 5: кросс-прогонная память+eval. Phase 6: вывод+disposition-политика+опц. платные провайдеры.
Phase 7: интеграция (`ingest` raw→Source, `pipeline.run_pipeline`, CLI `run`/`report`) + фиксы блокеров
по итогам 5-агентного ревью. `python -m engine run` принимает JSON (сырьё+claims) и выдаёт cluster-first
отчёт. Контракт-слой (SKILL.md/AGENT.MD) сохранён; переписан слой ИСПОЛНЕНИЯ.

### Added
- **`docs/PHASE1_MODEL_STATE.md`** — контракт Phase 1: claim-центричный JSON-snapshot, расширяющий
  AGENT.MD §8.0 (аддитивно: `clusters[]`, `scores{}`, `time_sensitive`, `contradicting_sources`,
  `role`, `language`, DAG-поля subtask'ов); 6 категорий фактчека ↔ enum; fingerprint-алгоритм;
  5 resume-инвариантов с функциями-энфорсерами; правила round-trip/валидации; atomic-запись checkpoint.
- **`engine/model.py`** — dataclasses + 11 enums (Snapshot/TaskFrame/Source/Claim/EvidenceCluster/Budget/
  SubTask/ScoreComponents; `ClaimCategory` = 6 категорий из `factcheck_system.md §4.1` с label+emoji).
  **Реализованы** `snapshot_to_dict`/`snapshot_from_dict` (round-trip; None-поля дропаются и восстанавливаются
  дефолтами; version-guard) и `validate_snapshot` (id-уникальность, ссылки claim→source, confidence 1..5,
  representative_ids ⊆ claim_ids, cluster_id существует, next_phase 0..6, budget ≥ 0).
- **`engine/state.py`** — state-машина **реализована**: `compute_fingerprint` (sha1, исключает
  `acceptance_criteria`), `resume_or_fresh` (→ `ResumeDecision{FRESH|RESUME|RESUME_RESTALE}`, run-папка по
  fingerprint), `find_latest_checkpoint` (highest-NN + NN-1 fallback), `save/load_checkpoint` (atomic
  `os.replace`, ведущий ```json-блок), `carry_budget`, `stale_source_ids`, `assert_sources_readonly`.
- **`engine/policy.py`** (Phase 6) — роль-зависимая reportability: `disposition(claim, report_mode) ->
  Disposition` (сигнатура + таблица-контракт); enums `ReportMode{findings,debunk,mixed}` и
  `Disposition{include,include_with_flag,include_as_correction,exclude_but_record,trigger_revision}`.
- **`tests/test_phase1.py`** — 16 юнит-тестов (round-trip dict+JSON, инварианты, fingerprint match/mismatch
  + исключение `acceptance_criteria`, staleness-окна, `carry_budget`, read-only источников, checkpoint
  save/load + NN-1 fallback, resume fresh→resume→restale). Запуск: `python -m unittest discover -s tests -t .`
- **`engine/dedupe.py`** (Phase 2) — детерминированный дедуп: `normalize_url` (https, www./m./amp., trailing
  slash, utm/тех-параметры, fragment), `text_similarity` (char-trigram + token Jaccard), `dedupe_sources`
  (exact-URL → near-dup ≥ threshold, order-stable, возвращает kept + merge-map).
- **`engine/rank.py`** (Phase 2) — `reciprocal_rank_fusion` (RRF, веса по стримам, tie-break по id) +
  `authority_weight` (Tier S/A/B/C/D → множитель) + `rank_sources` (`final = rrf · authority`).
- **`engine/freshness.py`** (Phase 2) — `parse_iso` (единый ISO-парсер движка) + `recency_score`
  (экспоненциальный спад, half-life; now/future → 1.0; missing → нейтраль). Сигнал свежести для ранжира,
  отдельно от resume-staleness.
- **`tests/test_phase2.py`** — 12 юнит-тестов (normalize_url, exact+near-dup, RRF-порядок/веса/tie,
  authority-tilt, recency half-life/now/future/missing, parse_iso).
- **`engine/score.py`** (Phase 3) — authority-скоринг реальной арифметикой: `composite_score`
  (`Authority·0.30 + Recency·0.25 + Independence·0.20 + Traceability·0.15 + Corroboration·0.10`),
  `tier_for_score` (§3.5: S≥0.90, A≥0.75, B≥0.55, C≥0.35, D<0.35), `authority_component` (tier→под-скор),
  `score_source` (заполняет recency из `freshness`, composite, переназначает tier), `claim_confidence`
  (1–5 из тиров источников claim'а: ≥2 S→5, S/≥2 A→4, A/≥2 B→3, B/C→2, иначе→1), `score_claim(s)`.
- **`tests/test_phase3.py`** — 9 юнит-тестов (3 worked-примера composite, пороги tier на границах,
  authority_component, score_source recency→composite→tier, лестница confidence 1–5).
- **`engine/factcheck.py`** (Phase 4) — детерминированный вердикт из структуры доказательств: `resolve_conflict`
  (Tier > freshness > count → `SUPPORTED/CONTRADICTED/DISPUTED/NO_EVIDENCE`), `classify_claim`
  (нет улик→UNVERIFIED; противоречие сильнее→FALSE; равновесие→OPINION; свежее опровержение по time-sensitive→
  OUTDATED; иначе VERIFIED / семантическая категория модели), `factcheck_claim(s)` (категория + cap confidence
  + status). Модель даёт claims+стансы, движок выносит воспроизводимый вердикт.
- **`engine/cluster.py`** (Phase 4) — evidence-кластеры: жадная группировка по `text_similarity` + MMR-выбор
  репрезентантов (relevance=confidence, diversity), флаг `uncertainty` (thin-evidence / single-source);
  проставляет `claim.cluster_id`.
- **`tests/test_phase4.py`** — 8 юнит-тестов (resolve_conflict: tier/freshness/count/disputed; classify:
  UNVERIFIED/VERIFIED/FALSE/OPINION/OUTDATED + уважение model_category; status+confidence cap; кластеризация:
  группы/репрезентанты/uncertainty).
- **`engine/memory.py`** (Phase 5) — кросс-прогонная память на SQLite (WAL + FTS5, LIKE-fallback):
  `record_run` (дедуп источников по normalized URL, claims по normalized-text key, sighting-счётчики),
  `seen_source`/`seen_claim`, `search_claims` (full-text), `get_stats`. «Видели ли это раньше» + ретро.
- **`engine/eval.py`** (Phase 5) — метрики качества между прогонами: `precision_at_k`, `recall_at_k`,
  `dcg_at_k`/`ndcg_at_k`, `jaccard`, `overlap_retention`, `source_coverage`.
- **`engine/policy.py`** (Phase 6) — **реализована** `disposition()` (была сигнатура): VERIFIED→INCLUDE;
  OUTDATED/INCOMPLETE/OPINION→INCLUDE_WITH_FLAG; UNVERIFIED→EXCLUDE_BUT_RECORD (findings) / FLAG (debunk);
  FALSE×external→INCLUDE_AS_CORRECTION; FALSE×own→TRIGGER_REVISION.
- **`engine/report.py`** (Phase 6) — cluster-first Markdown-рендер с применением disposition: выводы по
  кластерам, флаги категорий, секция «Опровергнуто/коррекции», источники, footer-счётчики
  (исключено-в-память / на пересмотр), агрегированная уверенность + emoji.
- **`engine/providers.py`** (Phase 6) — опц. платный Tier-4 (Brave/Exa/Serper), **default OFF**:
  `parse_dotenv`, `load_config` (env > .env), `is_enabled` (флаг `DRESEARCH_PAID_SEARCH` + ключ),
  `select_backend`, `web_search` (инъектируемый `http=` для тестов; disabled→`[]`).
- **`tests/test_phase5.py`** (4) + **`tests/test_phase6.py`** (7) — память (дедуп/поиск/stats), eval-метрики,
  disposition-таблица, рендер findings/debunk, providers (precedence/enablement/select/web_search).
- **`engine/ingest.py`** (Phase 7) — `source_from_raw` / `ingest_sources`: сырые dict'ы поиска → типизированные
  `Source` (id'ы, created_utc, date_confidence, начальный tier, score-компоненты) + дедуп.
- **`engine/pipeline.py`** (Phase 7) — обвязка: `reconcile_merges` (переписывает дропнутые id источников в
  claim'ах после дедупа), `build_snapshot` (сборка spine с fingerprint), `run_pipeline` (end-to-end:
  ingest→reconcile→score→factcheck→cluster→Snapshot).
- **CLI `run` и `report`** (`engine/cli.py`) — `python -m engine run` (JSON сырьё+claims → cluster-first
  отчёт, опц. `--out snapshot.json`) и `report` (snapshot JSON → Markdown). UTF-8 вывод (не падает на
  cp1251-консоли). Остальные подкоманды — заглушки.
- **`tests/test_phase7.py`** (10) — ingest, reconcile, build_snapshot, end-to-end `run_pipeline` (+ валидный
  snapshot), authority-засев, normalize_url (scheme-less/порты), FTS-спецсимволы, exa POST-тело, batch hints.

### Fixed (блокеры по итогам 5-агентного ревью движка)
- **Тихая деградация скоринга:** `score_source` теперь засевает `ScoreComponents.authority` из начального
  tier (раньше composite был ~только recency → все источники падали в C/D).
- **Сборка пайплайна:** добавлены `ingest` (raw→Source) и `build_snapshot` — движок собирается end-to-end
  (раньше эти связки отсутствовали, `Snapshot` никто не наполнял).
- **`normalize_url`:** чинит URL без схемы (`example.com/a` больше не ломается) и срезает порты `:80/:443`
  → дедуп и memory-PK срабатывают.
- **`search_claims`:** безопасный FTS5-запрос (токены в кавычках) + fallback на LIKE — больше не падает на
  `&`, `+`, кавычках и т.п.
- **`providers` exa/serper:** шлют POST с JSON-телом (раньше GET без тела → query терялся).
- **`factcheck_claims`:** принимает `model_categories` (раньше batch-API терял семантический хинт модели).

### Changed (по итогам code-review + дизайн-критики FALSE-исключения)
- **`ClaimCategory` значения → lowercase** (`"verified"` …), совпадают с примером AGENT.MD §8.0 — старые
  checkpoint'ы грузятся без алиасинга (фикс находки ревью: было UPPERCASE vs lowercase в §8.0).
- **Reportability больше НЕ статична.** Удалён `REPORTABLE_CATEGORIES` (он выкидывал любой FALSE).
  Добавлены роль claim'а `ClaimRole{own_finding,external_claim}` и роль-зависимая политика в `policy.py`:
  FALSE *внешнего* утверждения → `INCLUDE_AS_CORRECTION` (дебанк = ценность), FALSE *своего вывода* →
  `TRIGGER_REVISION`. Политика вынесена в Phase 6 (render), не в модель данных.
- **ISO-парсер централизован.** `state.py` больше не держит свой `_parse_iso` — импортирует
  `freshness.parse_iso` (единый источник разбора дат для staleness и recency).

### Verified
- **66/66 юнит-тестов проходят** (`python -m unittest discover -s tests -t .`): Phase 1–6 (как раньше) +
  Phase 7 (ingest, reconcile, build_snapshot, end-to-end run_pipeline → валидный snapshot, authority-засев,
  normalize_url scheme-less/порты, FTS-спецсимволы, exa POST, batch hints). **CLI `run` smoke прошёл
  end-to-end** (сырьё+claim JSON → cluster-first отчёт, источник tier S, claim VERIFIED conf 4).
  `disposition()` реализована; категории lowercase; staleness Standard=168ч; FTS5 доступен.

### Known doc inconsistency (не код)
- `references/source_authority_framework.md`: worked-примеры (§3.4) подписывают `0.79 → Tier B` и
  `0.565 → Tier C`, что противоречит таблице §3.5 (`0.75–0.89 → A`, `0.55–0.74 → B`). `score.py` следует
  **таблице §3.5** (канон). Подписи примеров стоит поправить в доке.

## [0.5.0] - 2026-06-09

Phase 0 полной пересборки (spec-only → claim-центричный исполняемый движок): план, STEP 0, скелет
`engine/` + runtime-контракт. Контракт сохраняется; переписывается слой ИСПОЛНЕНИЯ. План — `docs/REBUILD_PLAN.md`.

### Added
- **`docs/REBUILD_PLAN.md`** — source of truth пересборки: целевая архитектура `engine/` (stdlib-only,
  claim-центричная, post-collection), сознательные отклонения от last30days, фазовый план 0.5.0→1.0.0,
  три риска rebuild, инвариант «спека ↔ код синхронны».
- **STEP 0: STALE-CLONE SELF-CHECK** (`SKILL.md`, в самом верху) — самопроверка на загрузку спеки из
  отставшего git-клона маркетплейса (`~/.claude/plugins/marketplaces/…`) вместо свежего версионированного
  кэша. PowerShell (Windows) + bash варианты; обрабатывает nested vs flat layout кэша (пути выверены по
  диску: nested `…/<version>/skills/deep-research-skill/SKILL.md`).
- **Скелет `engine/`** (`plugins/deep-research-skill/skills/deep-research-skill/engine/`) — stdlib-only
  Python-пакет (≥3.10): `python -m engine` с `--version` и `doctor` (JSON-диагностика рантайма). Пайплайн-
  команды (`checkpoint/resume/ingest/rank/score/factcheck/memory/eval/report`) зарегистрированы как
  заглушки (exit 2, «planned in Phase N») — поверхность CLI зафиксирована, загорается фаза за фазой.
- **RUNTIME CONTRACT** (`SKILL.md`) — проба `python -m engine doctor` решает: engine-режим или **graceful
  prose-only fallback**. claude.ai без code-execution и любой хост без Python продолжают работать как раньше.
- **`NOTICE`** — атрибуция MIT: алгоритмы-референсы (RRF/MMR/nDCG/jaccard/FTS5) изучены по MIT-скиллу
  last30days; код движка написан с нуля, исходники не копировались.

### Note (honest scope)
- В 0.5.0 функциональны только `doctor`/`--version`; реального рисёрча движок ещё не делает — скилл
  работает в prose-only режиме. STEP 0 митигирует только «загрузку из отставшего клона»; корневую причину
  сломанного `marketplace update`/`re-add` (клон не двигает HEAD) он НЕ чинит — это ограничение платформы
  Claude Code (см. README → «Обновление плагина»). Фазы 1–6 (state, обработка, скоринг, фактчек, память,
  вывод) — впереди.

## [0.4.0] - 2026-06-08

Supervised orchestrator: staleness re-verify on resume + an honest negative finding on hard no-fetch.

### Added
- **Staleness re-verify on resume** (`examples/supervised_orchestrator.workflow.js`): when a resumed
  snapshot's `time_sensitive` sources are older than the freshness window (Quick 24h / Standard 7d /
  Deep 14d), the loop re-collects ONLY those — a bounded re-fetch that increments
  `loop_collection_calls_total` (never silent). "Now" is passed via `args.now` (ISO); the script reads
  no system clock. Snapshot schema gains `created_utc` + `time_sensitive`.
- `hard_nofetch` mode + staleness fields in the run journal (for retro).
- Forward-hook: `.claude/agents/no-fetch-analyst.md` (tool-restricted: Read/Grep/Glob, no web).

### Finding (honest negative result)
- **Hard no-fetch via a custom restricted `agentType` does NOT work in the current Workflow runtime.**
  Verified by smoke test: `agent({agentType})` resolves only built-in types (claude, Explore,
  general-purpose, Plan, …) — all of which have web tools — and does not load custom `.claude/agents/*.md`.
  So Verify/Format run in **soft** mode (instruction-only) by default; `hardNoFetch:true` is opt-in and
  gracefully falls back to soft (recorded in the journal) instead of breaking. Real enforcement remains
  loop-level (the loop never re-invokes collection).

### Changed
- `loop_collection_calls_total` on resume is no longer always 0 — it becomes 1 if a staleness re-verify
  fired (correct: re-verify IS collection, and it's externally counted).

## [0.3.1] - 2026-06-08

Honesty & consistency patch (no behavior change). Removes overclaims surfaced by an internal audit.

### Fixed
- Dropped "Production-ready" / "18/18 Acceptance Criteria implemented" overclaims from user-facing text
  (README header, `plugin.json` + `marketplace.json` descriptions, `SKILL.md` footer, `AGENT.MD` status) —
  this is a testing release.
- License unified to MIT in `SKILL.master.md` (was Apache-2.0 in places; conflicted with `LICENSE`).
- Corrected `docs/usage.md` recovery claim ("No duplicate work or API calls" → native resume restores
  state but does not enforce zero re-fetch; use the supervised orchestrator for that).
- Version stragglers (`AGENT.MD` 2.0.0 → 0.3.x); tool count aligned to 30+ in README; `your-org`
  placeholders → `azagreev/DResearch-Skill`.

### Added
- `examples/retro_checklist.md` — retrospective checklist for reviewing a `run_journal`.

## [0.3.0] - 2026-06-08

Supervised control-loop (variant A) — the enforcement layer the earlier "known limitations" pointed to.
`examples/supervised_orchestrator.workflow.js` is now a real, runnable orchestrator, not a skeleton.

### Added
- **Supervised orchestrator** (`examples/supervised_orchestrator.workflow.js`): a deterministic control
  loop (Workflow script) running Research / Verify / Format as separate subagents. Collection happens in
  ONE stage and is cached; Verify/Format receive the cached snapshot — the loop never re-invokes
  collection, so no-refetch is enforced by control flow, not by asking the model.
- **Resume-aware**: a loader stage reads a prior `snapshot.json`; on a topic (fingerprint) match it SKIPS
  Research entirely. The no-refetch metric (`loop_collection_calls_total`) is counted by the loop itself —
  externally observed, not self-reported.
- **Run journal**: every run writes `research_output/<runId>/run_journal.{json,md}` (+ `snapshot.json`)
  with a step-by-step log and a retro block — after-action review material.

### Tested (two demo runs, same runId)
- Fresh run: `loop_collection_calls_total = 1` (collection ran once), 3 sources, status done.
- Resume run: `resumed = true`, Research SKIPPED, **`loop_collection_calls_total = 0`** — proven no-refetch.

### Honest notes
- Resume's token saving scales with how expensive collection was; on a trivial task the delta is small
  (the demo resume still cost ~150k because Verify/Format reasoning, not collection, dominated). The value
  is the enforced, externally-counted no-refetch mechanism — not a guaranteed token cut on every run.
- Subagent-level hard no-fetch (Verify/Format physically without web tools) is available via a
  tool-restricted `agentType`; the example enforces no-refetch at the loop level + instruction.
- The native (non-orchestrated) skill still cannot enforce no-refetch — use this orchestrator for that.

## [0.2.0] - 2026-06-08

Checkpoint-resume + token discipline. Honest scope: resume delivers state continuity and integrity
guards, but native execution does not enforce no-refetch — see Known limitations.

### Added
- **Checkpoint state schema (AGENT.MD §8.0)** — every `cp_NN_<stage>.md` begins with a machine-loadable
  `json` `state` block: `task_fingerprint`, `sources` (with `extract` + `raw_path`), `claims`, `budget`, `next_phase`.
- **Resume entry point (SKILL.md Phase 0 · Step-0)** with a fingerprint guard: a matching task resumes
  from `next_phase`; a mismatching task starts a fresh run dir and never clobbers the existing checkpoint.
- **Budget carry-forward** on resume (`spent_usd` / `loads_used` carried, never reset).
- **Phase-2 large-output discipline** — tool results larger than ~5 KB are saved to `raw/<id>.txt` and
  grepped by intent; only the slice (`extract`) enters context. Cuts the dominant (collection) token cost.
- Workflow skeleton: the `checkpoint` placeholder is replaced with a real serialized `snapshot`.

### Tested
- Resume MATCH: state loaded, fingerprint matched, budget carried, pipeline finished, no fabricated facts.
- Resume MISMATCH: different question → fresh run dir, prior checkpoint left intact (independently verified).
- Save+grep discipline: confirmed (`raw/` files + `extract` slices) on a real run.

### Known limitations
- **Native resume does not enforce read-only reuse.** A model with web access may re-fetch
  already-collected sources and under-report the count (observed: logged `0` while actually re-fetching).
  Native resume reliably provides state continuity + integrity guards, **not guaranteed token savings**;
  hard enforcement requires the supervised control-loop (`examples/`), where the fetch count is observed
  externally rather than self-reported.
- Multi-agent resilience still runs inside a single Claude context (carried over from 0.1.0).

## [0.1.0] - 2026-06-07

First public release, intended for testing. The skill is feature-complete on paper, but the
multi-agent resilience layer is not yet executed as real processes — see Known limitations.

### Added
- 6-phase research workflow: Task Analysis, Decomposition, Collection, Fact-Checking, Synthesis, Output
- Cost-first execution model with a 4-tier tool hierarchy (native tools → premium APIs)
- Evidence-based reporting with mandatory citations and confidence scoring (1–5 scale)
- Anti-hallucination mandate with a zero-tolerance fact-checking protocol
- Source Authority Framework with Tier S/A/B/C/D classification
- 4 research depth levels (Quick, Standard, Deep, Exhaustive) and 4 search routes
- Agent orchestration protocol (AGENT.MD): heartbeat, checkpoints, quality gates, cost tracking
- 20 reference documents (tools, APIs, techniques), lazy-loaded for token efficiency
- Marketplace packaging: `.claude-plugin/marketplace.json` + plugin `.claude-plugin/plugin.json`
- `examples/supervised_orchestrator.workflow.js` — reference external control-loop skeleton

### Pre-release hardening
- Unified heartbeat cadence to a single source of truth (AGENT.MD §1.2); removed three
  conflicting definitions (flat 30s / 2h / 30min) across SKILL.md, README, factcheck_system, decomposition_guide
- Budget ceiling now triggers graceful degradation (finalize partial-with-confidence) instead of
  raising `BudgetExceededException` and aborting the run (fixed in both ToolExecutor copies)
- Runtime artifacts (`research_output/`) resolved to an absolute path to avoid silent write
  failures on Windows; added to `.gitignore`
- Quality-gate timeout given an explicit fallback (WARN + proceed + checkpoint) instead of a silent stop
- Recovery claim corrected: rollback to the last passed gate, not "no progress loss"

### Known limitations
- Multi-agent resilience (watchdog / restart / circuit-breaker) is specified but runs inside a
  single Claude context; true fault tolerance requires the external control-loop (see `examples/`)
- The checkpoint token is a placeholder; resumable state serialization is not yet implemented

[0.6.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.6.0
[0.5.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.5.0
[0.4.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.4.0
[0.3.1]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.3.1
[0.3.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.3.0
[0.2.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.2.0
[0.1.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.1.0
