# BUGLOG — bugs, root causes, and the guard that now prevents each

Living journal of defects found in the project, their **root cause** (the verification/process
gap that let them exist), and the standing **guard** that now catches the class. Compiled from
CHANGELOG, `docs/TECHDEBT.md`, git history, and `/code-review` findings (PR #5, #7).

"Bug" is read broadly: wrong behaviour, dead/unreachable code that was promised, docs that
describe code that doesn't exist, and inert capabilities that move no metric.

## Bugs over the last 3 releases (v1.3.0 → v1.5.0) + unreleased

| # | Release | Bug | Root cause (why it existed) | Fix | Guard now |
|---|---------|-----|------------------------------|-----|-----------|
| 1 | 1.3.0 | Orphan capabilities (TD-2): `verify`/`plan`/gate-oracles/`RunTrace` built + unit-green but unreachable (no CLI verb / not in `run_pipeline`), yet docs promised them | DoD = "unit test green", not "reachable e2e"; AC checked the module in isolation, not its integration | 3 verbs + `run_pipeline` wiring | inv #9 + `test_phase15_reachability.py` (reachability) |
| 2 | 1.3.0 | `run_pipeline` hardcoded `next_phase=5` regardless of gate state | scaffolding placeholder never replaced; test fixtures expected 5 and locked the stub | gate-consult `next_phase` | engine suite e2e assert + CI |
| 3 | 1.3.0 | `reverify_claim` called twice (`4a58334`) | two code paths each independently called the same helper; composed without tracing the call graph | de-duplicated | `/code-review` |
| 4 | 1.3.0 | Docs described an invented `verify` JSON-in variant (`4a58334`) | docs written from intended design, not reconciled against the real handler keys | doc corrected | **docs↔CLI consistency guard** (`DocsCliConsistencyTest`) |
| 5 | 1.3.0 | In-pipeline auto-verify `disagreement` signal scoped dishonestly — constant-False on the common hint-less path (`c0b30c2`) | feature specified abstractly; no analysis that it could ever fire on the common input | rescoped, then **cut in v1.5** | inv #11 (fires-on-real-input) |
| 6 | 1.4.0 | Dead field `TaskFrame.language` (TD-3): parsed but consumed by nobody → report always Russian, losing points on English tasks | producer built (field round-trips), consumer never wired; DoD stopped at "round-trips" not "changes output" | `render_markdown(language=)` + CLI-subprocess test | inv #9; CI |
| 7 | 1.5.0 | ~6 stale doc passages (PR #5): model.py disqualifiers docstring, AGENT.MD §3.5/§8/§10.3, SKILL.md verify/VETO sections described the removed veto/auto-verify as live | removal docs were duplicated across many scattered sites with no single source / grep-gate to find them all | `e165f73` purge | **removed-symbol guard** (`DocsNoActiveRemovedSymbolsTest`) |
| 8 | 1.5.0 | Inert anti-fit veto (TD-4): fired only on 3 `.example` hosts + 2 phrases → zero effect on real sources | pattern borrowed from another project and shipped without validating fit to THIS project's real data | removed (`a44415e`) | **inv #11** (fires-on-real-input) |
| 9 | 1.5.0 | Inert in-pipeline auto-verify (TD-4): wrote `claim.metadata["disagreement"]`, never rendered, constant-False | measured the mechanism (unit-green), never measured whether it moved a visible metric | removed (`af07c3a`) | inv #10 (value scorecard) + inv #11 |
| 10 | unreleased | Web-banner misdiagnosis: confident "bypass content → banner" hypothesis was wrong; real cause = generic marketplace-trust warning | causal claim from plausibility, not a controlled experiment isolating the variable | refuted via direct-zip test; `docs/BUG_WEB_SKILL_BANNER.md` | pre-mortem T1 discipline (checklist) |
| 11 | unreleased | README told users to zip with `SKILL.md` at the archive root; Claude apps require a root folder | install doc written from assumption, not verified by actually building+uploading a zip | PR #6 (release zip + correct structure) | `tests/release/test_skill_package.py` (structure assertion) |
| 12 | unreleased | `cit3` checker polarity inverted: dangling citations scored GOOD, clean scored BAD | checker authored by name-intuition without cross-checking its declared NEGATIVE polarity; tests exercised aggregation, never the checker's snapshot→verdict mapping | PR #7 `d6c150f` | **per-checker round-trip test** + `CheckerTestCoverageMetaGuard` |
| 13 | unreleased | `grade` CLI coerced JSON `null` → `False`, scoring an unjudged question as "not met" | `bool(v)` shortcut ignored that `null` is a meaningful third state; CLI JSON-loading path was untested (tests called `grade()` directly) | PR #7 `dea6362` (`_coerce_verdicts`) | **boundary tests** (`GradeCoercionBoundaryTest`, `CliVerdictCoercionTest`) |
| 14 | unreleased | Multi-agent contract asserted `from bench.trust._engine import Snapshot` before that export existed → hard-import crash | contract-first froze a fact that wasn't yet true; no import/smoke check between freeze and fan-out | additive export | CI import on push + contract-smoke rule (checklist) |

## 5 systemic roots

- **A — acceptance verified the part, not the connection/effect.** (#1, 2, 6, 9, 12, 13) Unit-green ≠ reachable / valuable / effectful end-to-end. **Dominant root.**
- **B — docs authored from intent/memory, not reconciled against code** (and duplicated with no single source). (#4, 7, 11)
- **C — capability adopted/specified without validating fit to real input.** (#5, 8, 9, 10)
- **D — local shortcut at a data boundary.** (#2, 3, 13)
- **E — contract asserted ahead of reality.** (#14)

The deepest common thread is **A + B**: a gap between *what was claimed/built* and *what is
actually reachable, effectful, and described truthfully*. No hard crash / data loss occurred in
3 releases — the failures are drift and inertness, which is exactly what a "green unit test"
does not catch.

## Root → standing measure

| Root | Bugs | Measure (where) |
|------|------|-----------------|
| A | 1,2,6,9,12,13 | CI (`.github/workflows/ci.yml`) · inv #9 reachability test · per-checker round-trip + boundary tests (`bench/tests/test_quality.py`) |
| B | 4,7,11 | docs↔CLI guard + **removed-symbol guard** (`tests/test_phase15_reachability.py`) · packaging structure test (`tests/release/test_skill_package.py`) · `docs/PRE_MERGE_CHECKLIST.md` |
| C | 5,8,9,10 | **invariant #11** "fires on real input = shipped" (AGENT.MD §10.1, TECHDEBT) · value scorecards (`bench/quality`, `bench/trust`) |
| D | 2,3,13 | CI · boundary tests · `/code-review` |
| E | 14 | CI import on push · contract-smoke rule (`docs/PRE_MERGE_CHECKLIST.md`) |

## How to extend this log

When a new bug is found: add a row (release, bug, **root cause**, fix commit, guard), map it to
a root A–E, and — if no standing guard would have caught it — add one (a test, an invariant, or a
checklist line) in the same PR. A bug without a new guard is a bug that can recur.
