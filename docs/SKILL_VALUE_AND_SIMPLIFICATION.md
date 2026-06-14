# Skill Value, Engine Simplification & Trust Metrics

> **Status:** decision document (no code changed yet). Saved 2026-06-15.
> **Origin:** the DRACO-benchmarking effort (see `bench/`, `docs/` tmp run artifacts) forced the question *"is the skill worth keeping?"* This doc records the answer and the two concrete deliverables that follow from it: **(A) what to simplify in the engine**, and **(C) what to measure instead of DRACO**.

---

## 0. Context — what the deep-research established (preserve these results)

Three grounded findings (code + external methodology), all converging:

1. **The deterministic engine cannot move the DRACO score upward on the part that matters.** DRACO weight is ~52% exact facts / 22% depth / 14% presentation / 12% citation. The engine **never edits claim text or numbers** (verified: no `claim.text = …` anywhere) — it only labels, scores, drops, and cites claims Claude already extracted. Bounded contribution of the engine *alone*, given the same claims:

   | Axis (weight) | Best | Worst |
   |---|---|---|
   | Factual (52%) — only *suppress* a wrong claim | +0.04 | **−0.06** (drops correct-but-under-sourced) |
   | Citation (12%) — guaranteed structured/tiered cites | +0.05 | −0.02 |
   | Depth (22%) — can only remove findings | 0 | −0.03 |
   | Presentation (14%) — verbose format | +0.01 | −0.03 |
   | **Engine Δ (normalized)** | **+0.06…+0.10** | **−0.10…−0.14** |

   **Expected value ≈ 0 or slightly negative.** The veto layer never fires on real sources; the in-pipeline `verify` result is never rendered → 0 score effect.

2. **The skill's *real* potential value is the prose collection discipline, not the engine** — tier-first to SEC/EDGAR, read-full-source-not-snippet, ≥2-source corroboration, arithmetic sanity checks, re-search-on-FAIL loops. This *can* move the 52% axis, but it is **not code-enforced** (depends on instruction-following) and would need **n≈20 tasks + multi-judge** (~$200–400) to measure — **n=1 cannot** (per-task judge noise ≥±3 pts; n=1 paired CI ≈ ±10 pts; DRACO uses 100 tasks × 5 grading runs and still runs no significance tests).

3. **DRACO does not measure what this engine is *for*.** Determinism, auditability, reproducibility, anti-hallucination discipline, cost-control — none are DRACO-scored. Judging the skill by DRACO is *"discarding a screwdriver for being a bad hammer."*

**Conclusion:** don't spend on an n=1 kill-test (can't decide) or the full $200–400 test (premature). Instead **(A) simplify the engine** to stop carrying complexity that earns nothing on *either* DRACO *or* trust, and **(C) measure the skill against trust/reproducibility metrics** it can actually win — cheaply and deterministically.

Sources: DRACO `arxiv.org/abs/2602.11685` (100 tasks, 5 grading runs, 25-pt cross-judge spread, stable rankings); Anthropic *Demystifying evals for AI agents* (20–50 tasks; small n only for large effects). Engine bounds derived from `engine/{score,factcheck,policy,report,verify}.py`.

---

## (A) Engine simplification

**Principle:** simplify *toward* the value we're keeping the skill for (trust/audit/anti-hallucination), and cut features that earn ~nothing on **both** DRACO **and** trust, or that are provably inert/invisible. Engine today: **4885 LOC / 24 modules** (`wc -l engine/*.py`).

### Cut / shrink candidates

| # | Feature (file, LOC) | DRACO | Trust/audit | Decision | Confidence | Verify before cut |
|---|---|---|---|---|---|---|
| 1 | **Veto layer** — `score.py` `VetoRules`/`disqualify`/`DEFAULT_VETO` (~Phase 14) | 0 (never fires) | ~0 | **CUT** rules + breakdown coupling (or shrink to no-op). `DEFAULT_VETO` matches only 3 `.example` domains + `"this is an advertisement"`/`"ignore previous instructions"` → inert on real sources. Prompt-injection is already handled by the ingest trust-fence (Phase 8), not this. | **HIGH** (code-confirmed) | Confirm no test/report depends on `scores.disqualifiers` beyond cosmetics |
| 2 | **In-pipeline auto-`verify` + `claim.metadata["disagreement"]`** — `verify.py` (61) + `pipeline.py:109-124` | 0 | 0 (**never rendered**) | **SURFACE or CUT.** Phase 15 made `verify` "reachable via verb" but its in-pipeline output is invisible in `render_markdown`. Either render the disagreement flag (make it earn its place) **or** drop the pipeline auto-run (keep the standalone `verify` CLI verb if wanted). | **HIGH** | — |
| 3 | **`plan.py`** — topo/validate DAG (265) | 0 | marginal (DAG validation not consumed by the run) | **CUT-CANDIDATE / KEEP-OPTIONAL.** Largest single low-value chunk. `ready_set` is the only historically-used piece; the `plan` verb was a Phase-15 reachability add. | **MEDIUM** | Grep real callers of `topo_order`/`validate_plan` outside tests |
| 4 | **Feedback ledger** — `memory.py` portion (~Phase 14) | 0 | marginal (append-only, **not auto-consumed** by scoring) | **SHRINK / KEEP-OPTIONAL.** Keep run-memory if used; the calibration ledger that nothing reads is dead weight. | **MEDIUM** | Confirm nothing consumes `record-feedback`/`list-feedback` |
| 5 | **Report cosmetic layer** — `report.py` confidence emojis + per-source `auth/rec/...` breakdown | neutral→**negative** (presentation) | tier matters, emojis don't | **SHRINK** — make emoji + score-breakdown optional; keep `[Sx]` + tier + URL (the audit-relevant citation). | **MEDIUM** | The needle A/B showed the verbose format neutral-to-slightly-negative |
| 6 | **`rescore`** (Phase 14, cli/score path) | 0 | some (re-score on new freshness) | **KEEP-OPTIONAL** — low priority, not core. | LOW | — |

### Keep-core (these ARE the trust/audit value — do not cut)

`model.py` (checkpoint/serialize/provenance → determinism+resume), `ingest.py`+`dedupe.py` (provenance, real dedup, trust-fence), `factcheck.py`+`policy.py` (**the anti-hallucination disposition — drop UNVERIFIED — is the actual value lever**), `report.py` core (citation rendering = the one DRACO-positive + audit), `freshness.py` (staleness→OUTDATED), `telemetry.py` (RunTrace = audit), `state.py` gates (process discipline), `collect.py`+`providers.py` (typed collection seam, opt-in paid), `compact.py` (cost-control), **`eval.py` (keep — repurposed in Part C)**.

### Estimated reduction & how to do it

- **LOC:** cutting #1–#4 + shrinking #5 ≈ **~500–700 LOC (~10–15%)**, but the real win is **conceptual**: it removes **3 whole "features" that don't bite** (veto, in-pipeline verify, plan-DAG) → less surface to reason about, fewer "reachable but inert" traps, and stops the docs over-claiming. It also resolves the irony that Phase-15's flagship (`verify` reachability) is invisible in the output.
- **Staged, test-guarded (own phase):** each cut updates/removes its tests; full `unittest discover` stays green, 0 skipped; `CHECKPOINT_VERSION` only bumps if a serialized field is removed (likely **not** — these are render/scoring-time). Version-bump ritual applies (→ v1.5.0). Sequence: #1 veto → #2 verify (decide surface-vs-cut) → #5 report cosmetics → #3/#4 behind a usage-grep confirmation.
- **Discipline note:** this is *exactly* the project's own invariant — *don't crystallize non-working machinery.* Veto (#1) and in-pipeline verify (#2) are the clearest cases of "built, shipped, inert."

---

## (C) Trust / reproducibility metrics — measure what the skill is *for* (instead of DRACO)

DRACO is a **$200–400, judge-noisy** yardstick that doesn't measure this skill's value props. The metrics below measure those props **deterministically, mostly at $0**, reusing `engine/eval.py` + synthetic fixtures. Lead with the **bold** four.

| Metric | Value prop | How (reuse) | Cost | Target |
|---|---|---|---|---|
| **Determinism / byte-reproducibility** | reproducibility | run `run_pipeline` 2× on identical inputs → `render_markdown` diff == 0; `now_utc` pinned | **$0** | 100% identical |
| **Unsupported-claim suppression rate** | anti-hallucination (recall) | held-out fixture: inject claims with 0 supporting sources → % that become UNVERIFIED → EXCLUDED from report (`policy.disposition`) | **$0** (synthetic) | ~100% suppressed |
| **False-suppression rate** | anti-hallucination (precision) | inject well-supported claims → % wrongly dropped (FALSE/UNVERIFIED) | **$0** | ~0% |
| **Citation completeness** | auditability | % findings with ≥1 source + % sources with tier+scores (`eval.source_coverage`) | **$0** | 100% claims cited |
| Checkpoint round-trip fidelity | resumability | `snapshot_to_dict→from_dict→to_dict` idempotent; resume == continue | $0 | 100% |
| Confidence calibration | calibration | labeled set: reliability curve `P(correct \| conf=k)` monotone in k | small (labels) | monotone |
| Source-set stability | robustness | `eval.overlap_retention` between two collections of the same task | web only | high retention |
| Gate correctness | process discipline | synthetic snapshots → gate precision/recall (blocks when criteria unmet) | $0 | high |
| Cost / latency per run | efficiency | `eval.cost_efficiency` (`cost_per_item`, `items_per_sec`) instrumented | $0 | track/trend |

**Why this is the right yardstick:** these express exactly *"trustworthy, auditable, reproducible, doesn't assert unsupported facts, cost-aware"* — and (unlike DRACO) they are **reproducible and cheap**, so they can gate every release as deterministic tests. The anti-hallucination pair (suppression recall **and** precision) is the honest measure of `factcheck`+`policy` — the engine's one genuine lever — *without* renting a noisy LLM judge.

**Harness sketch:** a small `bench/trust/` (stdlib, deterministic, unit-test-shaped) over `engine/eval.py` + synthetic `Snapshot` fixtures (supported / unsupported / conflicting claims). Most metrics become assertions in the existing test discipline; only calibration + source-stability need real labels/web. Estimated build: comparable to `bench/` Phase 0 (small, $0 to run).

---

## Decision summary & next steps

1. **Do NOT** run the n=1 hard DRACO test (can't decide) or the full $200–400 test (premature). The engine's DRACO ceiling is already known from architecture (EV≈0/neg).
2. **Engine simplification (A):** cut/shrink the inert features (#1 veto, #2 in-pipeline verify, #5 cosmetics; confirm-then-cut #3 plan, #4 ledger) → ~10–15% LOC, 3 fewer dead concepts, → v1.5.0, test-guarded.
3. **Trust metrics (C):** build the `bench/trust/` deterministic harness; adopt the bold-four as release gates **in place of** a DRACO pass-rate.
4. **Only if** you later want the workflow's factual lift proven empirically: a properly-powered **n≈20, multi-judge** DRACO A/B (~$200–400), *not* n=1 — and temper expectations (the engine won't move the 52% axis; the *collection discipline* might).
5. **Don't bury the skill on DRACO** — its plausible value (collection discipline + auditability/determinism) is not captured by that benchmark.
