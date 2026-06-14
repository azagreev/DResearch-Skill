# Phase v1.5.0 — Engine Simplification ("cut the inert")

> **Status:** plan (not executed). Saved 2026-06-15.
> **Basis:** `docs/SKILL_VALUE_AND_SIMPLIFICATION.md` §(A). The DRACO research proved several engine features are **inert** — they move neither the DRACO score nor any trust metric. This phase removes them.
> **Acceptance instrument:** the deterministic trust harness `bench/trust/` (§ "Gating"). The cuts are correct iff the trust metrics are **unchanged** after them — i.e. we removed dead code, not value.

## Context

Engine today: **4885 LOC / 24 modules**. The deterministic engine's DRACO upside is ~0 (it never edits claim text); its genuine value is the **anti-hallucination disposition** (drop UNVERIFIED), **citation rendering**, and **checkpoint/provenance/determinism**. Several shipped features contribute to *none* of that:

- **Veto layer** (`score.py`): `DEFAULT_VETO` matches only 3 `.example` domains + `"this is an advertisement"` / `"ignore previous instructions"` → never fires on real sources. Prompt-injection is handled by the Phase-8 ingest trust-fence, not this.
- **In-pipeline auto-`verify`**: `pipeline.py` re-derives each claim's category and writes `claim.metadata["disagreement"]` — which `render_markdown` **never reads**. Invisible in the output (ironic, since Phase 15's headline was `verify` "reachability").

**New invariant (record in AGENT.MD root-cause table): #10 — "shipped ≠ valuable."** A feature that moves no measured metric (DRACO *or* the trust suite) is a cut candidate, not a keep. This is the same discipline as invariant #9, applied to *value* rather than *reachability*.

**Invariants preserved:** stdlib-only, strict determinism, engine read-only over sources, host-safety. Prefer to **keep serialized fields** (deserialize to empty) over removing them, so `CHECKPOINT_VERSION` stays `1.3` (no migration churn) — only bump if a field is actually dropped.

## Cuts (packets)

| # | Cut | Files | Action | Confidence | CHECKPOINT impact |
|---|---|---|---|---|---|
| **1** | Veto layer | `engine/score.py` | Remove `DEFAULT_VETO` rules + the `disqualify()` call in `score_source`. **Keep** `ScoreComponents.disqualifiers` field (default `[]`) and the `report.py` veto-annotation branch (now never triggered) — or remove both in one sweep if no test needs them. | HIGH | none (field kept empty) |
| **2** | In-pipeline auto-verify | `engine/pipeline.py` (the per-claim `reverify_claim` loop + `claim.metadata` writes) | Remove the auto-run from `run_pipeline`. **Keep** the standalone `verify` CLI verb (still reachable) and the `claim.metadata` field. *(Alternative: SURFACE the disagreement flag in `render_markdown` instead of cutting — decide at build time; cutting is the simpler honest default.)* | HIGH | none |
| **3** | Plan DAG | `engine/plan.py` (`topo_order`/`validate_plan`/`EdgeKind`), `plan` CLI verb | **Confirm-then-cut.** Keep `ready_set` if used by `state.py`. Drop the rest + the verb if `git grep` shows no non-test caller. | MEDIUM | none |
| **4** | Feedback ledger | `engine/memory.py` (record/list-feedback path) | **Confirm-then-shrink.** Keep run-memory if consumed; drop the calibration ledger that nothing reads. | MEDIUM | check `memory.py` serialized shape |
| **5** | Report cosmetics | `engine/report.py` | Make confidence emojis + per-source `auth/rec/...` breakdown **optional** (off by default). Keep `[Sx]` + tier + URL (audit-relevant). | MEDIUM | none |

### Pre-work (gates #3/#4 before cutting)
```
git grep -n "topo_order\|validate_plan\|EdgeKind"   # outside tests/ → keep; else cut (#3)
git grep -n "record_feedback\|list_feedback\|feedback_ledger"  # consumers? (#4)
```
Anything dropped is named in `CHANGELOG → Removed` and `docs/TECHDEBT.md` (no silent caps).

## Gating — the trust harness is the acceptance test

Run **before and after** every cut; the value props must be byte-identical:

```
PYTHONPATH=. python -m bench.trust                       # determinism / suppression / citation / checkpoint
PYTHONPATH=. python -m unittest discover -s bench/tests -t .   # 24 tests incl. test_trust
```
- **determinism == true**, **suppression_recall == 1.0**, **false_suppression_rate == 0.0**, **citation claims_cited_fraction == 1.0**, **checkpoint_fidelity == true** — unchanged across the cut. If any moves, the cut touched value, not dead code → revert/rescope.
- Full engine suite: `cd plugins/deep-research-skill/skills/deep-research-skill && python -m unittest discover tests -v` → green, **0 skipped** (362 minus the tests for removed features, which are deleted with their feature).

## Sequence
1. Debt-sweep + invariant #10 into `docs/TECHDEBT.md` / `AGENT.MD`. Branch `feat/phase-v1.5-simplify` from `main`.
2. Baseline: capture `bench/trust` scorecard + full suite green.
3. Cut #1 (veto) → #2 (verify; decide surface-vs-cut) → #5 (cosmetics) → grep-gate #3/#4.
4. After each: trust scorecard unchanged + suite green; delete the removed feature's own tests.
5. Version bump `1.4.0 → 1.5.0` (7 files + `TECHDEBT` + `CHANGELOG [1.5.0] Removed/Changed`). `CHECKPOINT_VERSION` stays `1.3` unless a field was dropped.
6. `/code-review` on the diff (focus: no KEEP-core behavior change; trust metrics stable; deleted tests correspond only to removed features) → your "влей" → merge → `gh release create v1.5.0`.

## Expected outcome
- **~500–700 LOC removed (~10–15%)** and, more importantly, **3 fewer dead concepts** (veto, in-pipeline verify, plan-DAG) → smaller reasoning surface, no more "reachable-but-inert" traps, docs stop over-claiming.
- **Zero change** to the trust scorecard ⇒ provable evidence the cuts removed dead weight, not value. This is the project's own discipline — *don't carry non-working machinery* — made measurable.

## Risks
- **Hidden consumer of a "dead" feature** → the grep-gates (#3/#4) + full suite + trust scorecard catch it; revert that packet.
- **Veto field removal** would force a `CHECKPOINT_VERSION` bump + migration → avoided by keeping `ScoreComponents.disqualifiers` as an empty default.
- **`verify` surfacing vs cutting** is a genuine fork — if you want the independent re-derivation visible, SURFACE it in `render_markdown` (then it earns its place and is no longer a cut); otherwise cut the pipeline auto-run. Decide at build time; both are honest.
