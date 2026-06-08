# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.2.0
[0.1.0]: https://github.com/azagreev/DResearch-Skill/releases/tag/v0.1.0
