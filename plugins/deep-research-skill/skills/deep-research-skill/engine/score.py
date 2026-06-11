"""Phase 3 — authority scoring (real arithmetic, not the model's judgement).

Two levels, both deterministic:
  - source: ScoreComponents -> composite -> Tier S/A/B/C/D
  - claim:  confidence 1..5 from the tiers of its supporting sources

Formula + thresholds mirror references/source_authority_framework.md §3.3/§3.5;
the confidence ladder mirrors SKILL.md Principle #7 / README. stdlib-only.

NOTE: the framework's §3.5 categorization TABLE is canonical here. Its inline
worked examples label 0.79 as "B" and 0.565 as "C", which contradicts the table
(0.75-0.89 = A, 0.55-0.74 = B). We follow the table.

Python >= 3.10.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .freshness import recency_score
from .model import Claim, ScoreComponents, Source, Tier

# Composite weights (source_authority_framework.md §3.3). Sum = 1.0.
W_AUTHORITY = 0.30
W_RECENCY = 0.25
W_INDEPENDENCE = 0.20
W_TRACEABILITY = 0.15
W_CORROBORATION = 0.10

# Authority criterion value by initial tier classification (§1.2-1.6 weights).
_AUTHORITY_COMPONENT: Dict[Tier, float] = {
    Tier.S: 1.0,
    Tier.A: 0.85,
    Tier.B: 0.65,
    Tier.C: 0.40,
    Tier.D: 0.15,
}


def authority_component(tier: Optional[Tier]) -> float:
    """The Authority sub-score [0,1] for a source pre-classified into `tier`.
    A caller seeds `ScoreComponents.authority` with this before scoring; unknown
    tier -> 0.0.
    """
    if tier is None:
        return 0.0
    return _AUTHORITY_COMPONENT.get(tier, 0.0)


def composite_score(components: ScoreComponents) -> float:
    """Weighted composite in [0,1]. A None component counts as 0.0 (not yet
    scored), so an incomplete ScoreComponents yields a conservative low score.
    """
    def v(x: Optional[float]) -> float:
        return x if x is not None else 0.0

    total = (
        v(components.authority) * W_AUTHORITY
        + v(components.recency) * W_RECENCY
        + v(components.independence) * W_INDEPENDENCE
        + v(components.traceability) * W_TRACEABILITY
        + v(components.corroboration) * W_CORROBORATION
    )
    return max(0.0, min(1.0, total))


def tier_for_score(score: float) -> Tier:
    """Map a composite score to a Tier (source_authority_framework.md §3.5)."""
    if score >= 0.90:
        return Tier.S
    if score >= 0.75:
        return Tier.A
    if score >= 0.55:
        return Tier.B
    if score >= 0.35:
        return Tier.C
    return Tier.D


def score_source(
    source: Source,
    now_utc: Optional[str] = None,
    half_life_days: float = 30.0,
) -> Source:
    """Fill `source.scores.composite` and (re)assign `source.tier` from it.
    MUTATES and returns `source`.

    If `now_utc` is given and the recency component is not yet set, it is filled
    from freshness.recency_score(source.published_at, now_utc, half_life_days),
    wiring the Phase-2 recency signal into the Phase-3 composite.
    """
    components = source.scores
    # Seed the Authority component from the source's initial tier classification
    # (the §1.2-1.6 weight) when it hasn't been set, so the composite is not
    # recency-only. The composite then re-derives the FINAL tier below.
    if components.authority is None and source.tier is not None:
        components.authority = authority_component(source.tier)
    if now_utc and components.recency is None and source.published_at:
        components.recency = recency_score(source.published_at, now_utc, half_life_days)
    components.composite = composite_score(components)
    source.tier = tier_for_score(components.composite)
    return source


def score_sources(
    sources: List[Source],
    now_utc: Optional[str] = None,
    half_life_days: float = 30.0,
) -> List[Source]:
    return [score_source(s, now_utc, half_life_days) for s in sources]


def claim_confidence(claim: Claim, sources_by_id: Dict[str, Source]) -> int:
    """Confidence 1..5 from the tiers of a claim's supporting sources
    (SKILL.md Principle #7 / README):

      5  >= 2 Tier-S
      4  >= 1 Tier-S  OR  >= 2 Tier-A
      3  >= 1 Tier-A  OR  >= 2 Tier-B
      2  >= 1 Tier-B  OR  >= 1 Tier-C
      1  otherwise (no sources, or Tier-D only)

    Contradictions are NOT applied here — that is Phase 4 (factcheck). This is the
    base confidence from supporting evidence only.
    """
    counts: Dict[Tier, int] = {tier: 0 for tier in Tier}
    for sid in claim.sources:
        source = sources_by_id.get(sid)
        if source is not None and source.tier is not None:
            counts[source.tier] += 1

    if counts[Tier.S] >= 2:
        return 5
    if counts[Tier.S] >= 1 or counts[Tier.A] >= 2:
        return 4
    if counts[Tier.A] >= 1 or counts[Tier.B] >= 2:
        return 3
    if counts[Tier.B] >= 1 or counts[Tier.C] >= 1:
        return 2
    return 1


def score_claim(claim: Claim, sources_by_id: Dict[str, Source]) -> Claim:
    """Set `claim.confidence` from its supporting sources. MUTATES and returns."""
    claim.confidence = claim_confidence(claim, sources_by_id)
    return claim


def score_claims(claims: List[Claim], sources: List[Source]) -> List[Claim]:
    by_id = {s.id: s for s in sources}
    return [score_claim(c, by_id) for c in claims]
