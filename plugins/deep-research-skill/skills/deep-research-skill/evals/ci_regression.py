"""CI regression runner for the deep-research-skill golden corpus.

Loads evals/golden_corpus.json, computes engine.eval metrics per case, and
checks each against configurable thresholds. Deterministic, stdlib + engine.eval
only. Python >= 3.10.

Usage:
    python evals/ci_regression.py            # run with default corpus + thresholds
    python -c "from evals.ci_regression import run_regression; print(run_regression())"

Public API (frozen for Phase 12):
    run_regression(corpus_path=None, thresholds=None) -> dict
        Returns {"passed": bool, "results": [per-case-dict, ...]}.
        passed=False when any single metric on any case falls below its threshold.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Locate the corpus relative to this file so it works regardless of cwd.
_EVALS_DIR = Path(__file__).parent
_SKILL_DIR = _EVALS_DIR.parent  # one level up from evals/
_DEFAULT_CORPUS = _EVALS_DIR / "golden_corpus.json"

# Ensure the skill root (which contains the `engine` package) is on sys.path
# so `from engine.eval import ...` works whether this script is invoked via
# `python evals/ci_regression.py` from the skill dir, or imported from anywhere.
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

# Default thresholds applied to every case.  Override via the `thresholds`
# parameter of run_regression().
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "ndcg_at_k": 0.6,
    "precision_at_k": 0.5,
    "source_coverage": 0.8,
}

# k used for position-sensitive metrics (ndcg / precision).
_K = 3


def _grades_from_relevant(ranked_ids: List[str], relevant_ids: List[str]) -> Dict[str, float]:
    """Binary grade map: 1.0 for relevant ids, 0.0 for others."""
    relevant_set = set(relevant_ids)
    return {sid: (1.0 if sid in relevant_set else 0.0) for sid in ranked_ids}


def _evaluate_case(case: Dict[str, Any], thresholds: Dict[str, float], k: int) -> Dict[str, Any]:
    """Evaluate one corpus case.  Returns a per-case result dict."""
    # Import here so the module is importable even from outside the skill dir,
    # but we defer the import to avoid a hard dependency at module load time.
    try:
        from engine.eval import ndcg_at_k, precision_at_k, source_coverage
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "engine.eval not found. Run from the skill directory or add it to sys.path."
        ) from exc

    ranked = case["ranked_ids"]
    relevant = case["relevant_ids"]
    grades = _grades_from_relevant(ranked, relevant)

    metrics: Dict[str, float] = {
        "ndcg_at_k": ndcg_at_k(ranked, grades, k),
        "precision_at_k": precision_at_k(ranked, relevant, k),
        "source_coverage": source_coverage(ranked, relevant),
    }

    failures: List[str] = []
    for metric_name, value in metrics.items():
        threshold = thresholds.get(metric_name, DEFAULT_THRESHOLDS.get(metric_name, 0.0))
        if value < threshold:
            failures.append(
                f"{metric_name}={value:.4f} < threshold={threshold:.4f}"
            )

    return {
        "query": case.get("query", ""),
        "metrics": metrics,
        "thresholds_applied": {
            m: thresholds.get(m, DEFAULT_THRESHOLDS.get(m, 0.0))
            for m in metrics
        },
        "passed": len(failures) == 0,
        "failures": failures,
    }


def run_regression(
    corpus_path: Optional[str] = None,
    thresholds: Optional[Dict[str, float]] = None,
    k: int = _K,
) -> Dict[str, Any]:
    """Run the CI regression suite against the golden corpus.

    Parameters
    ----------
    corpus_path:
        Path to a golden corpus JSON file (list of case dicts).  Defaults to
        evals/golden_corpus.json (resolved relative to this file).
    thresholds:
        Metric thresholds dict.  Keys: "ndcg_at_k", "precision_at_k",
        "source_coverage".  Missing keys fall back to DEFAULT_THRESHOLDS.
    k:
        Rank cutoff for position-sensitive metrics.  Default: 3.

    Returns
    -------
    dict with keys:
        passed  — True iff every case passed every threshold.
        results — list of per-case result dicts (see _evaluate_case).
    """
    resolved_path = Path(corpus_path) if corpus_path is not None else _DEFAULT_CORPUS
    with resolved_path.open(encoding="utf-8") as fh:
        corpus: List[Dict[str, Any]] = json.load(fh)

    effective_thresholds: Dict[str, float] = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    results: List[Dict[str, Any]] = []
    for case in corpus:
        # Skip documentation-only entries that lack ranked_ids.
        if "ranked_ids" not in case:
            continue
        result = _evaluate_case(case, effective_thresholds, k)
        results.append(result)

    overall_passed = all(r["passed"] for r in results)
    return {"passed": overall_passed, "results": results}


def _main() -> int:
    """CLI entry-point: run regression and print a human-readable summary."""
    outcome = run_regression()
    for r in outcome["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        metrics_str = ", ".join(f"{k}={v:.4f}" for k, v in r["metrics"].items())
        print(f"[{status}] {r['query'][:60]!r}  {metrics_str}")
        for failure in r["failures"]:
            print(f"       BELOW THRESHOLD: {failure}")
    print()
    if outcome["passed"]:
        print("Regression PASSED: all cases within thresholds.")
        return 0
    else:
        failed_cases = sum(1 for r in outcome["results"] if not r["passed"])
        print(f"Regression FAILED: {failed_cases}/{len(outcome['results'])} case(s) below threshold.")
        return 1


if __name__ == "__main__":
    sys.exit(_main())
