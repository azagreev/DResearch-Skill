# Technical Debt Ledger

ABP «technical debt tracker» (architecture.md §Entropy management). Every deferred AC, sub-threshold `/code-review` finding, or expensive cross-effect lands here instead of being silently dropped. **Debt-sweep is the first step of every phase**: read this file, close what new code has made cheap, mark closed entries with the commit that resolved them.

Mirror of open items also appears in `CHANGELOG [x.y.z] → Deferred / Known gaps`.

| ID | Phase | AC | Deferred item | Reason | Source | Target release | Status |
|----|-------|----|---------------|--------|--------|----------------|--------|
| TD-1 | 10 | AC10-5 | `model.validate_snapshot` flagged an unknown dep id behind a `:NONE` edge, while `plan.validate_plan` skips NONE edges | Aligned parse-free (split on last `:`, skip when suffix == `"NONE"`) — no `EdgeKind` import into `model.py` | /code-review (Opus reviewer, low severity) | v1.0.0 (Phase 12) | **closed** in Phase 12 (`feat/phase-12-hardening`); regression test `TestValidateSnapshotNoneDep` |
| TD-2 | 15 | AC15-2/5/7 | **Orphan capabilities**: `verify.py`, `plan.py` (topo/validate), gate enforcement (`gate_blocks_transition`/`should_stop`), `telemetry.RunTrace` were built + unit-green but **unreachable** — no CLI verb and/or not called in `run_pipeline`; `SKILL.md`/`AGENT.MD` promised them. Root cause: AC verified the module, not its integration/reachability. | Same failure-class family as README drift + AGENT.MD §9 mismatch — surfaced by the post-v1.2.0 integration audit (grep of `run_pipeline` + CLI subparser registry) | post-v1.2.0 integration audit | **closing in Phase 15** (`feat/phase-15-integration-reachability`): `verify`/`plan`/`gate` verbs + `run_pipeline` wiring + permanent regression eval `test_phase15_reachability.py` |
| TD-3 | i18n (v1.4) | AC-A1/A2 | **Dead field `TaskFrame.language`** — parsed by `_task_frame_from` but consumed by no caller; the report always rendered in Russian, costing presentation/citation points on English tasks (e.g. the DRACO benchmark). | Same invariant-#9 class as TD-2 (parsed/built but unreachable); surfaced by the DRACO benchmarking prep | post-v1.3.0 (DRACO eval prep) | **closed** in v1.4.0 (`feat/engine-i18n`): `report.render_markdown(language=)` + `model.get_category_labels`; the field drives report language e2e; CLI-subprocess regression test (`test_run_emits_english_report`) |

**Invariant #9 (new, from TD-2) — «built but unreachable = dead integration».** Every curated engine capability MUST have a registered CLI subparser-choice AND be exercised end-to-end. **Acceptance criterion = reachable e2e, not only a green unit test.** Enforced by `test_phase15_reachability.py` (fails on any orphan). Added to the project root-cause invariant table (AGENT.MD).

_0 open items as of v1.2.0 — TD-1 closed (Phase 12); TD-2 closing in Phase 15 with its regression eval. Phase 13/14 debt-sweeps confirmed nothing new._
