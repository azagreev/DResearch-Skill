# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.5.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.5.0
[0.4.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.4.0
[0.3.1]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.3.1
[0.3.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.3.0
[0.2.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.2.0
[0.1.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.1.0
