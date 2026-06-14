# `bench/` — DRACO benchmark harness

Evaluation tooling for the deep-research skill against Perplexity's
[DRACO benchmark](https://huggingface.co/datasets/perplexity-ai/draco)
(100 real deep-research tasks, expert rubrics, ~40 criteria each, 4 axes).

## Why it lives outside `engine/`

The grading loop calls a **non-deterministic LLM judge**, which must never enter
the deterministic, stdlib-only engine. So `bench/` holds **only the
deterministic pieces** — dataset loading, rubric parsing, and the exact scoring
formula. The judge orchestration (run the skill on a task → judge each criterion)
lives in the agent/workflow layer that *imports* `bench`.

```
bench/
  draco.py    # load_draco(jsonl), parse_rubric, Task/Rubric/Criterion, AXES, DOMAINS
  score.py    # score_task → TaskScore (overall + per-axis), aggregate → Summary, delta (A/B)
  __main__.py # CLI: `score` one arm, `diff` two arms
  tests/      # hand-worked unit tests for the exact formula (incl. negative weights)
```

## Scoring (verbatim from the DRACO dataset card)

```
raw        = sum(verdict_i * weight_i  for all criteria)
positive   = sum(weight_i for weight_i > 0)
normalized = clamp(raw / positive, 0, 1) * 100
```

Negative-weight criteria describe errors: a **MET** verdict means the error is
*present* and subtracts from `raw`. We also report an unweighted
`criteria_pass_rate` (the Perplexity write-up's "% of criteria met"), clearly
labelled — `normalized` is primary.

## Usage

```bash
# data (not committed — license/size): downloaded into tmp/draco/
#   https://huggingface.co/datasets/perplexity-ai/draco/resolve/main/test.jsonl

PYTHONPATH=. python -m bench score --tasks tmp/draco/test.jsonl --verdicts with_skill.json
PYTHONPATH=. python -m bench diff  --tasks tmp/draco/test.jsonl --a no_skill.json --b with_skill.json

# unit tests
PYTHONPATH=. python -m unittest discover -s bench/tests -t .
```

A **verdicts file** (one per arm) is what the judge layer produces:

```json
{ "arm": "with_skill",
  "verdicts": { "<task_uuid>": { "<criterion_id>": true, "<criterion_id>": false } } }
```

## Designed for the A/B ablation

A single DRACO score mostly grades *Claude + web tools*, not the skill (52% of
criterion weight is exact factual retrieval the engine never produces). To
isolate the **skill's** contribution, run each task **twice** — `no_skill` vs
`with_skill` — and read `bench diff`'s **per-axis** deltas. The skill is expected
to help on **citation quality** and on **factual accuracy via suppressing
unsupported (negative-weight) claims**, not on raw fact-finding.

## Methodology notes / not-yet-done (honesty ledger)

- **Judge must be pinned + independent.** Use one capable judge model at temp 0,
  recorded with the run. Absolute scores drift across judges; only compare arms
  *within* one judge config (DRACO's own finding).
- **Live engine wiring is the next fidelity step.** The first smoke used a
  faithful skill-*format* report; a real run must invoke `engine.run_pipeline`
  per arm.
- **Static snapshot.** Rubrics freeze late-2025 facts; live browsing can fetch
  newer values the judge marks UNMET. Confound, not a bug.
- **`report.py` renders Russian section headers** (`# Отчёт:`, `Источники`) —
  DRACO is English-only and judged on presentation; fix before scored runs.
