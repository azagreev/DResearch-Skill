# Technical Debt Ledger

ABP «technical debt tracker» (architecture.md §Entropy management). Every deferred AC, sub-threshold `/code-review` finding, or expensive cross-effect lands here instead of being silently dropped. **Debt-sweep is the first step of every phase**: read this file, close what new code has made cheap, mark closed entries with the commit that resolved them.

Mirror of open items also appears in `CHANGELOG [x.y.z] → Deferred / Known gaps`.

| ID | Phase | AC | Deferred item | Reason | Source | Target release | Status |
|----|-------|----|---------------|--------|--------|----------------|--------|
| TD-1 | 10 | AC10-5 | `model.validate_snapshot` flags an unknown dep id behind a `:NONE` edge, while `plan.validate_plan` skips NONE edges — the two validators disagree on `depends_on=["ST-99:NONE"]` with ST-99 missing | Aligning would pull `EdgeKind` parsing into `model.py` (layering violation) for an edge case with no real-world trigger (no producer emits `:NONE` suffixes today) | /code-review (Opus reviewer, low severity) | v1.0.0 (Phase 12 — consolidate validation) | open |

_1 open low-severity item as of v0.9.0 (TD-1)._
