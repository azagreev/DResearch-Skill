"""Phase 2 — rank sources: reciprocal rank fusion across streams + authority tilt.

Collection feeds several ranked streams (one per sub-query / provider). RRF fuses
them into one order; the source's authority tier then tilts the result so a
high-authority source outranks an equal-RRF low-authority one. Deterministic and
explainable — no model discretion. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .model import Source, Tier

RRF_K = 60

# Authority tier -> multiplier in (0, 1]. Floored at 0.5 so RRF still matters
# for low-tier sources rather than being crushed to zero.
_AUTHORITY_WEIGHT: Dict[Tier, float] = {
    Tier.S: 1.0,
    Tier.A: 0.9,
    Tier.B: 0.8,
    Tier.C: 0.65,
    Tier.D: 0.5,
}
_DEFAULT_AUTHORITY = 0.6  # unknown / unset tier


def authority_weight(tier: Optional[Tier]) -> float:
    """Multiplier for a source's authority tier; unknown tier -> default."""
    if tier is None:
        return _DEFAULT_AUTHORITY
    return _AUTHORITY_WEIGHT.get(tier, _DEFAULT_AUTHORITY)


def reciprocal_rank_fusion(
    streams: Dict[str, List[str]],
    weights: Optional[Dict[str, float]] = None,
    k: int = RRF_K,
) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion over ranked streams.

    `streams`: stream_name -> ordered list of source ids (best first).
    `weights`: optional per-stream weight (default 1.0). Returns [(id, score)]
    sorted by score desc, ties broken by id asc (stable, deterministic).
    """
    weights = weights or {}
    scores: Dict[str, float] = {}
    for name, ranked in streams.items():
        weight = weights.get(name, 1.0)
        for rank, item in enumerate(ranked):
            scores[item] = scores.get(item, 0.0) + weight * (1.0 / (k + rank + 1))
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def rank_sources(
    sources: List[Source],
    streams: Dict[str, List[str]],
    weights: Optional[Dict[str, float]] = None,
    k: int = RRF_K,
) -> List[Tuple[Source, float]]:
    """Fuse `streams` (RRF) then tilt by source authority:
    `final = rrf_score * authority_weight(tier)`.

    Every source in `sources` is returned; one absent from all streams gets
    rrf 0 -> final 0 and ranks last. Sorted by final desc, ties by id asc.
    """
    rrf = dict(reciprocal_rank_fusion(streams, weights, k))
    ranked = [
        (source, rrf.get(source.id, 0.0) * authority_weight(source.tier))
        for source in sources
    ]
    ranked.sort(key=lambda pair: (-pair[1], pair[0].id))
    return ranked
