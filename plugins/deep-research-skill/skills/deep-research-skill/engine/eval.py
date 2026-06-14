"""Phase 5 — evaluation metrics for comparing ranked outputs across runs/revisions.

Pure functions over id sequences + a relevance/grade map, so a release can be
measured against a baseline instead of eyeballed. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, Sequence


def precision_at_k(ranked: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Fraction of the top-k that is relevant."""
    if k <= 0:
        return 0.0
    top = list(ranked)[:k]
    if not top:
        return 0.0
    relevant_set = set(relevant)
    return sum(1 for item in top if item in relevant_set) / len(top)


def recall_at_k(ranked: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Fraction of all relevant items present in the top-k."""
    relevant_set = set(relevant)
    if not relevant_set:
        return 0.0
    top = set(list(ranked)[:k])
    return len(top & relevant_set) / len(relevant_set)


def dcg_at_k(ranked: Sequence[str], grades: Dict[str, float], k: int) -> float:
    """Discounted cumulative gain over the top-k: sum (2^grade - 1)/log2(rank+1)."""
    total = 0.0
    for index, item in enumerate(list(ranked)[:k]):
        grade = grades.get(item, 0.0)
        total += (2.0 ** grade - 1.0) / math.log2(index + 2)
    return total


def ndcg_at_k(ranked: Sequence[str], grades: Dict[str, float], k: int) -> float:
    """Normalized DCG@k in [0,1] (DCG / ideal DCG). 0 when no positive grades."""
    ideal_grades = sorted(grades.values(), reverse=True)[:k]
    idcg = sum((2.0 ** g - 1.0) / math.log2(i + 2) for i, g in enumerate(ideal_grades))
    if idcg == 0.0:
        return 0.0
    return dcg_at_k(ranked, grades, k) / idcg


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """Set overlap |A∩B| / |A∪B|; two empty sets -> 1.0."""
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def overlap_retention(previous: Iterable[str], current: Iterable[str]) -> float:
    """Share of `previous` still present in `current` (candidate-vs-baseline stability)."""
    prev = set(previous)
    if not prev:
        return 0.0
    return len(prev & set(current)) / len(prev)


def source_coverage(retrieved: Iterable[str], relevant: Iterable[str]) -> float:
    """Share of the relevant pool that was retrieved at all (rank-agnostic recall)."""
    relevant_set = set(relevant)
    if not relevant_set:
        return 0.0
    return len(set(retrieved) & relevant_set) / len(relevant_set)


def cost_efficiency(n_items: int, cost_usd: float, elapsed_sec: float) -> Dict[str, float]:
    """Cost / throughput summary for a run (Phase 13, AC13-5).

    Returns ``{"cost_per_item": cost_usd/n_items, "items_per_sec": n_items/elapsed_sec}``,
    with both quotients defaulting to 0.0 on a zero (or non-positive) denominator
    so the function is division-by-zero safe.  Pure, deterministic — no clock.
    """
    return {
        "cost_per_item": cost_usd / n_items if n_items > 0 else 0.0,
        "items_per_sec": n_items / elapsed_sec if elapsed_sec > 0 else 0.0,
    }
