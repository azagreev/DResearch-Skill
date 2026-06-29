# Pre-merge checklist

One authoritative gate that stitches together the project's previously-scattered rituals plus
the standing guards built to prevent the recurring bug classes in `docs/BUGLOG.md`. Run before
asking for merge («влей»). Most of it is enforced automatically by `.github/workflows/ci.yml`;
the rest is judgement that CI cannot make.

## Always (every change)

- [ ] **Debt-sweep first.** Read `docs/TECHDEBT.md`; close anything this change made cheap (mark
      the closing commit). Mirror open items in `CHANGELOG [x.y.z] → Deferred / Known gaps`.
- [ ] **Suites green, 0 skipped** (CI runs all of this; run locally if unsure):
      - engine: `cd plugins/deep-research-skill/skills/deep-research-skill && python -m unittest discover tests`
      - bench: `PYTHONPATH=. python -m unittest discover -s bench/tests -t .`
- [ ] **Determinism gate** — scorecards byte-identical across two runs:
      `PYTHONPATH=. python -m bench.trust` ×2 and `python -m bench.quality` ×2 → `diff` empty.
- [ ] **Golden-corpus regression** green: `python plugins/.../evals/ci_regression.py`.
- [ ] **`/code-review`** on the diff → fix or consciously dismiss every ≥80 finding (it caught
      bugs #3, #7, #12, #13). Post the verdict.
- [ ] **Docs match code.** No doc describes a removed symbol as live (the removed-symbol guard
      enforces `VetoRules`/`DEFAULT_VETO`/`disqualify`; extend `_REMOVED_API` when you cut more).
      No invented CLI verb/flag/JSON-in key (docs↔CLI guard).

## When adding a curated capability (inv #9, #10, #11)

- [ ] **Reachable e2e (#9):** registered CLI subparser-choice AND exercised end-to-end; appears
      reachable in the `doctor` manifest. `test_phase15_reachability.py` must stay green.
- [ ] **Fires on real input (#11):** a test/eval shows it **changes output or a measured score on
      a non-synthetic fixture** — not just a green mechanism test. (The v1.2 veto and the
      auto-verify would have failed this — they only fired on `.example` hosts / were constant.)
- [ ] **Moves a metric (#10):** if it claims value, it shows up in a value scorecard
      (`bench/quality`, `bench/trust`); if it moves nothing, it's a cut candidate, not a keep.

## When adding a deterministic checker / a CLI input parser (roots A, D)

- [ ] **Checker round-trip test:** for any new entry in a checker registry (e.g.
      `DETERMINISTIC_CHECKERS`), add a snapshot→verdict test in BOTH directions and register its id
      in `_TESTED_CHECKERS` — the meta-guard fails otherwise. (This is the guard that would have
      caught the cit3 inversion #12.)
- [ ] **Boundary test:** any code that parses external input (JSON loaders, `_coerce_*`, `_cmd_*`)
      gets a test feeding edge values — `null`, missing keys, malformed. (Caught-after-the-fact:
      the `grade` null→False bug #13.)

## When running a multi-agent contract-first build (root E)

- [ ] **Contract-smoke before fan-out:** after freezing the interface contract and BEFORE spawning
      downstream agents, verify every asserted symbol / import path actually resolves
      (`python -c "import ..."`). A contract may only assert facts that are already true. (The
      `Snapshot`-not-exported drift #14 came from asserting an import that didn't exist yet.)
- [ ] **Integration smoke after fan-out:** run the entry point once (`python -m <module>`) before
      writing tests — catch wiring drift early, cheaply.

## Release ritual (only on a version bump)

- [ ] **Version in 7 files:** `plugin.json`, `engine/__init__.py`, `SKILL.md`, `SKILL.master.md`,
      `AGENT.MD`, `CHANGELOG.md`, `README.md` (+ stamp `docs/TECHDEBT.md`).
- [ ] `CHANGELOG [x.y.z]` with **Added / Changed / Removed / Fixed / Deferred** as applicable;
      every fixed defect also gets a `docs/BUGLOG.md` row with its root cause and guard.
- [ ] `CHECKPOINT_VERSION` bumped only if a serialized field changed (else unchanged).
- [ ] After «влей»: ff-merge → `gh release create vX.Y.Z` (attach the skill zip if user-facing).

> Rule of thumb: **a bug fixed without a new guard is a bug that can recur.** Every fix should
> leave behind a test, an invariant, or a checklist line that would catch its class next time.
