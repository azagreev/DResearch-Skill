# Technical Debt Ledger

ABP «technical debt tracker» (architecture.md §Entropy management). Every deferred AC, sub-threshold `/code-review` finding, or expensive cross-effect lands here instead of being silently dropped. **Debt-sweep is the first step of every phase**: read this file, close what new code has made cheap, mark closed entries with the commit that resolved them.

Mirror of open items also appears in `CHANGELOG [x.y.z] → Deferred / Known gaps`.

| ID | Phase | AC | Deferred item | Reason | Source | Target release | Status |
|----|-------|----|---------------|--------|--------|----------------|--------|
| — | 8 | — | (none) | Phase 8 shipped with all AC met | — | — | — |

_No open debt as of v0.7.0._
