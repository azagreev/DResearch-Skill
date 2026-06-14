# Technical Debt Ledger

ABP «technical debt tracker» (architecture.md §Entropy management). Every deferred AC, sub-threshold `/code-review` finding, or expensive cross-effect lands here instead of being silently dropped. **Debt-sweep is the first step of every phase**: read this file, close what new code has made cheap, mark closed entries with the commit that resolved them.

Mirror of open items also appears in `CHANGELOG [x.y.z] → Deferred / Known gaps`.

| ID | Phase | AC | Deferred item | Reason | Source | Target release | Status |
|----|-------|----|---------------|--------|--------|----------------|--------|
| TD-1 | 10 | AC10-5 | `model.validate_snapshot` flagged an unknown dep id behind a `:NONE` edge, while `plan.validate_plan` skips NONE edges | Aligned parse-free (split on last `:`, skip when suffix == `"NONE"`) — no `EdgeKind` import into `model.py` | /code-review (Opus reviewer, low severity) | v1.0.0 (Phase 12) | **closed** in Phase 12 (`feat/phase-12-hardening`); regression test `TestValidateSnapshotNoneDep` |

_0 open items as of v1.1.0 — TD-1 closed in Phase 12 debt-sweep; Phase 13 debt-sweep confirmed nothing new to open._
