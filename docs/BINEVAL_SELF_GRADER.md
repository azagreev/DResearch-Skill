# BINEVAL Self-Grader — Design Rationale

> **Status:** design document for `bench/quality/`. Saved 2026-06-28.
> **Branch:** feat/bench-quality-self-grader.

---

## 1. Why

The existing `bench/trust/` harness measures what the engine is *for* — determinism, anti-hallucination, auditability — purely deterministically and at zero cost. That is the right first yardstick (see `docs/SKILL_VALUE_AND_SIMPLIFICATION.md §(C)`).

`bench/quality/` is the second yardstick: a cheap, interpretable **DRACO proxy** for measuring report *output quality* along the same four axes DRACO uses, without DRACO's cost ($200–400, noisy external judge, 100-task corpus). It answers "is this report any good?" in a way that can gate a single A/B comparison or a nightly sweep without renting a full benchmark run.

Concretely it serves two roles:

- **DRACO proxy.** Per-axis scores on the same four DRACO dimensions let you compare runs, prompt changes, or engine variants with a consistent signal before committing to a full DRACO evaluation.
- **A/B yardstick.** A reviewer or CI job can ingest a `Snapshot`, run the deterministic questions in milliseconds, optionally pass the judgment questions to an LLM, and get an interpretable per-dimension table rather than a single opaque number.

Relationship to `bench/trust/`: the two harnesses are complementary. `bench/trust/` grades the *engine's behaviour* (does it suppress unsupported claims? are checkpoints round-trippable?). `bench/quality/` grades the *output report* (is it factually consistent with its sources? does the analysis go deep?). You need both; neither subsumes the other.

---

## 2. What BINEVAL is

**BINEVAL** (Gao et al., arXiv:2606.27226) is an LLM evaluation framework that decomposes holistic criteria into atomic binary yes/no questions:

- Each evaluation criterion maps to one or more atomic questions, each with a natural-language explanation; a "yes" on a positive question means a desirable property is present, "yes" on a negative question means a flaw is present.
- Per-dimension score: `S_d = mean(binary verdicts in d)` — a plain unweighted average in [0, 1].
- Overall score: `S = mean(all verdicts)` across dimensions — again unweighted; an optional affine rescale to a 0–100 range is described but not central.
- Questions are auto-generated from a **task-agnostic meta-prompt** (summarise task → derive requirements → generate binary questions per dimension); the generator can be iteratively self-updated from failed questions (the self-improvement loop).
- A single evaluator LLM at temperature 0, averaged over two runs (not byte-deterministic; judge non-determinism is acknowledged as a residual variance source).
- On SummEval, Topical-Chat, and QAGS, BINEVAL matches or beats G-Eval and UniEval in Spearman correlation with human judgements.

---

## 3. Our adaptation and deliberate divergences

### (a) Static curated bank instead of auto-generated meta-prompt

BINEVAL generates questions at evaluation time via a meta-prompt that reads the task and derives requirements. We use a **static, versioned, manually curated bank** of 16 questions (4 per DRACO axis) seeded from the acceptance criteria in `references/acceptance_framework.md`.

*Why:* Determinism and reviewability are first-class constraints here. An auto-generated bank would produce a different question set per task and per model version, making A/B scores incomparable across runs and hard to audit. The curated bank can be diffed in git, reasoned about explicitly, and its coverage gaps documented.

*Trade-off:* less per-task adaptivity. A generated bank might surface a highly relevant criterion that the static bank misses for a given domain. This is acknowledged as a future-work item — the bank can be extended with domain-specific supplements while keeping a stable reviewed core.

### (b) Deterministic / judgment hybrid

BINEVAL's questions all go to an LLM judge. We split the bank into two kinds:

- **DETERMINISTIC** (8 of 16): answered by a pure function over a `Snapshot` (no LLM, no network, no clock or random). These cover machine-checkable acceptance criteria: every finding cited, every claim confidence-scored, source tier coverage, no FALSE own findings shipped, no UNVERIFIED claims in reportable findings, no dangling citation references. Checkers reuse `bench.trust.metrics` logic and engine model fields directly.
- **JUDGMENT** (8 of 16): subjective checks that require reading comprehension — factual accuracy vs. sources, analytical depth, logical coherence, uncertainty signalling, citation support quality. These are left to an external LLM judge.

*Why:* the project's determinism-first identity means the deterministic half costs $0, is reproducible to the bit, and can run in a unit test. Reserving the judge for genuinely subjective questions reduces per-run cost and keeps the deterministic core stdlib-only. The split also makes failures actionable: a failing deterministic check points at a specific engine invariant; a failing judgment check points at prompt or collection quality.

### (c) DRACO axis weighting on top of BINEVAL's unweighted mean

BINEVAL aggregates with a plain unweighted mean. Our overall score applies the DRACO axis weights (factual-accuracy 0.52, breadth-and-depth-of-analysis 0.22, presentation-quality 0.14, citation-quality 0.12) on top of the per-axis means, so the overall score is a DRACO-aligned weighted mean rather than a flat average.

*Why:* the purpose of the module is a *DRACO proxy*. Applying DRACO weights preserves the relative importance DRACO assigns to axes (factual correctness dominates), keeping the proxy score comparable in character to the benchmark it approximates. Within each axis the questions are still averaged equally — no intra-axis weighting is applied or implied.

### (d) External judge seam

The LLM judge is called externally, outside `bench/quality/` itself. The grader consumes a pre-computed verdicts file (or dict), exactly as the DRACO harness consumes its judge output from `bench/judge/`. This keeps the entire `bench/` tree stdlib-only and deterministically testable with a synthetic fake-judge fixture — no live LLM calls, no API keys, no network required to run the test suite.

The judge prompt lives in `bench/quality/prompt_quality.txt` and is structurally parallel to `bench/judge/prompt_draco.txt`: one question per call, temperature 0, returns `{"explanation": "...", "status": "MET" | "UNMET"}` as raw JSON. Polarity (`positive` / `negative`) is passed explicitly so the judge applies the same sign convention as BINEVAL and DRACO's signed-weight rubric.

---

## 4. Limitations inherited and how we mitigate them

| BINEVAL limitation | Our design response |
|---|---|
| **Over-decomposition harshness.** Decomposing a holistic criterion into strict atomic checks produces a harsher evaluator than a human would be. | The bank is kept deliberately small (4 questions per axis, 16 total) and questions are written to be holistic-aware where possible (e.g. "key facts" cross-verified, not every fact). The static bank can be recalibrated if scores track systematically harsh vs. human judgement. |
| **Question-quality dependency.** "If important criteria are missing, the final score will miss them." | The bank is versioned, git-diffable, seeded from the reviewed acceptance framework, and editable without touching any code. Coverage gaps are visible by inspection and can be addressed incrementally. The `validate_bank()` call in `questions.py` enforces structural contracts at import time. |
| **Prompt bloat over self-update iterations** (from the self-improvement loop). | We do not build the self-update loop (see §5). The static bank cannot bloat. |
| **Prompting can't fix capability gaps** (counting/computation). | The deterministic checkers handle exactly those checks — citation counts, tier counts, confidence-score ranges — as pure functions over the Snapshot, completely bypassing the LLM. Judgment questions are scoped to semantics where LLMs are strong. |
| **Judge non-determinism.** Temperature 0 plus two-run averaging is not byte-deterministic. | The non-deterministic component lives entirely outside the deterministic core. The deterministic half (8 questions) is perfectly reproducible. For the judgment half the variance is the same as any LLM-judge harness and must be tolerated; running two calls per question and averaging (as BINEVAL recommends) is left to the caller. |

---

## 5. What we did NOT build

The following BINEVAL components were considered and consciously excluded from this phase:

- **Self-update loop** — the iterative meta-prompt that rewrites failed questions. Excluded because it introduces prompt non-determinism, meta-prompt cost, and version instability into the bank. Reviewability of the bank is more valuable at this stage than per-task adaptivity.
- **Meta-prompt auto-generation** — deriving questions from a task description at evaluation time. Same reason as above; the static bank is preferred.
- **In-bench LLM calls** — the `bench/quality/` package makes no live API calls. The judge is external, as documented in §3(d) and consistent with `bench/judge/`.
- **Cross-model evaluator alignment** — BINEVAL's second self-improvement loop, which aligns evaluator models. Out of scope for a proxy harness at this scale.

---

## 6. Pointers

| Item | Location |
|---|---|
| Question bank (16 questions, deterministic checkers) | `bench/quality/questions.py` |
| Grader (aggregation: per-axis mean + DRACO-weighted overall, graceful degradation) | `bench/quality/grader.py` |
| LLM judge prompt (one question per call) | `bench/quality/prompt_quality.txt` |
| DRACO axis list and rubric types | `bench/draco.py` (`AXES`) |
| Trust / deterministic harness (complementary) | `bench/trust/metrics.py` |
| Acceptance criteria the questions are seeded from | `references/acceptance_framework.md` |
| Engine Snapshot model | `engine/model.py` |

**How to run** (once `grader.py` is in place):

```
python -m bench.quality
```

**Paper:** arXiv:2606.27226 — *Ask, Don't Judge: Binary Questions for Interpretable LLM Evaluation and Self-Improvement* (Gao et al.).
