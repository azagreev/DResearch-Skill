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

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlsplit

from .freshness import recency_score
from .model import Claim, ScoreComponents, Source, Tier

# Composite weights (source_authority_framework.md §3.3). Sum = 1.0.
W_AUTHORITY = 0.30
W_RECENCY = 0.25
W_INDEPENDENCE = 0.20
W_TRACEABILITY = 0.15
W_CORROBORATION = 0.10

# Breakdown label order — mirrors the composite term order above. Each entry is
# (label, weight, ScoreComponents attribute) so breakdown and composite share a
# single source of truth and can never drift apart.
_BREAKDOWN_TERMS = (
    ("authority", W_AUTHORITY, "authority"),
    ("recency", W_RECENCY, "recency"),
    ("independence", W_INDEPENDENCE, "independence"),
    ("traceability", W_TRACEABILITY, "traceability"),
    ("corroboration", W_CORROBORATION, "corroboration"),
)


# --------------------------------------------------------------------------- #
# Anti-fit veto layer (Phase 14)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VetoRules:
    """Disqualification rules: a source that matches is vetoed to composite=0 / D.

    `domains`  — exact-host match (case-insensitive), e.g. a known content farm.
    `patterns` — substrings/regexes tested (case-insensitive) against the source's
                 title + snippet + url; self-declaring markers like an advertorial
                 banner or an embedded prompt-injection payload.
    An empty VetoRules() disables veto entirely (matches nothing).
    """
    domains: frozenset = field(default_factory=frozenset)
    patterns: tuple = field(default_factory=tuple)


# Conservative default seed: known content-farm / injection example hosts plus
# only *self-declaring* markers that disqualify a source wherever they appear.
# Deliberately NOT included: bare content words like "retracted" / "sponsored by"
# — for a fact-checking engine a legitimate, high-authority source routinely
# *discusses* a retraction or names a sponsor in its snippet, so substring-veto on
# those inverts the signal. Operators who want them can inject a stricter
# VetoRules; the mechanism stays fully general.
DEFAULT_VETO = VetoRules(
    domains=frozenset({
        "content-farm.example",
        "spamblog.example",
        "ai-generated-news.example",
    }),
    patterns=(
        "this is an advertisement",
        "ignore previous instructions",
    ),
)


def _host(url: str) -> str:
    """Lowercased host of `url` (no port), '' when unparseable."""
    netloc = urlsplit(url).netloc.lower()
    if "@" in netloc:
        netloc = netloc.rsplit("@", 1)[1]
    if ":" in netloc:
        netloc = netloc.rsplit(":", 1)[0]
    return netloc


def disqualify(source: Source, rules: VetoRules) -> List[str]:
    """Return the sorted, de-duplicated veto reasons matched by `source`.

    Pure: no mutation. Empty list = not vetoed. A domain hit reads
    `domain:<host>`; a pattern hit reads `pattern:<pattern>`. The matched
    haystack is title + extract snippet + url, lowercased.
    """
    reasons: set = set()

    host = _host(source.url)
    for domain in rules.domains:
        if host == domain.lower():
            reasons.add(f"domain:{domain}")

    snippet = source.extract.get("snippet", "") if isinstance(source.extract, dict) else ""
    haystack = " ".join((source.title or "", str(snippet), source.url or "")).lower()
    for pat in rules.patterns:
        lowered = pat.lower()
        hit = lowered in haystack
        if not hit:
            try:
                hit = re.search(pat, haystack, re.IGNORECASE) is not None
            except re.error:
                hit = False
        if hit:
            reasons.add(f"pattern:{pat}")

    return sorted(reasons)

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


def _breakdown(components: ScoreComponents) -> List:
    """The auditable [label, contribution] trace for a scored source.

    contribution = weight * (component value, None -> 0.0), mirroring
    composite_score's None-handling so sum(contributions) == composite exactly.
    """
    return [
        [label, weight * (getattr(components, attr) or 0.0)]
        for label, weight, attr in _BREAKDOWN_TERMS
    ]


def score_source(
    source: Source,
    now_utc: Optional[str] = None,
    half_life_days: float = 30.0,
    veto: Optional[VetoRules] = None,
) -> Source:
    """Fill `source.scores.composite` and (re)assign `source.tier` from it.
    MUTATES and returns `source`.

    If `now_utc` is given and the recency component is not yet set, it is filled
    from freshness.recency_score(source.published_at, now_utc, half_life_days),
    wiring the Phase-2 recency signal into the Phase-3 composite.

    Anti-fit veto (Phase 14): if the source matches `veto` (defaults to
    DEFAULT_VETO; pass an empty VetoRules() to disable), its composite is forced
    to 0.0, tier to D, and the matched reasons recorded in scores.disqualifiers —
    overriding any high authority tier. A non-vetoed source additionally gets its
    auditable scores.breakdown populated.
    """
    components = source.scores
    rules = veto if veto is not None else DEFAULT_VETO
    reasons = disqualify(source, rules)
    if reasons:
        components.composite = 0.0
        components.disqualifiers = reasons
        source.tier = Tier.D
        return source

    # Seed the Authority component from the source's initial tier classification
    # (the §1.2-1.6 weight) when it hasn't been set, so the composite is not
    # recency-only. The composite then re-derives the FINAL tier below.
    if components.authority is None and source.tier is not None:
        components.authority = authority_component(source.tier)
    if now_utc and components.recency is None and source.published_at:
        components.recency = recency_score(source.published_at, now_utc, half_life_days)
    components.composite = composite_score(components)
    components.breakdown = _breakdown(components)
    components.disqualifiers = []
    source.tier = tier_for_score(components.composite)
    return source


def score_sources(
    sources: List[Source],
    now_utc: Optional[str] = None,
    half_life_days: float = 30.0,
    veto: Optional[VetoRules] = None,
) -> List[Source]:
    return [score_source(s, now_utc, half_life_days, veto) for s in sources]


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
