"""Phase 4 — fact-check core: deterministic verdict from the evidence structure.

The MODEL proposes claims and, per source, a stance (supporting vs contradicting)
+ an optional semantic category (INCOMPLETE / OPINION / OUTDATED). The ENGINE then
deterministically resolves conflicts and finalizes the 6-category verdict +
confidence + status, so the same evidence always yields the same verdict.

Conflict resolution follows source_authority_framework.md (Tier S > Tier A >
freshness > quantity). The 6 categories are factcheck_system.md §4.1.
stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from .freshness import parse_iso
from .model import Claim, ClaimCategory, ClaimStatus, Source, Tier

_TIER_RANK: Dict[Tier, int] = {Tier.S: 5, Tier.A: 4, Tier.B: 3, Tier.C: 2, Tier.D: 1}


def _tier_rank(tier: Optional[Tier]) -> int:
    return _TIER_RANK.get(tier, 0) if tier is not None else 0


class Resolution(str, Enum):
    NO_EVIDENCE = "no_evidence"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    DISPUTED = "disputed"  # opposing evidence of comparable strength


def _newest(sources: List[Source]):
    dates = [parse_iso(s.published_at) for s in sources]
    dates = [d for d in dates if d is not None]
    return max(dates) if dates else None


def resolve_conflict(
    supporting: List[Source],
    contradicting: List[Source],
    now_utc: Optional[str] = None,  # reserved; relative comparison needs no clock
) -> Resolution:
    """Decide which side wins by: max tier, then freshness, then count; an
    irreducible tie is DISPUTED. `now_utc` is accepted for signature symmetry but
    not required (freshness here is a relative date comparison).
    """
    if not supporting and not contradicting:
        return Resolution.NO_EVIDENCE
    if not contradicting:
        return Resolution.SUPPORTED
    if not supporting:
        return Resolution.CONTRADICTED

    sup_max = max(_tier_rank(s.tier) for s in supporting)
    con_max = max(_tier_rank(s.tier) for s in contradicting)
    if sup_max > con_max:
        return Resolution.SUPPORTED
    if con_max > sup_max:
        return Resolution.CONTRADICTED

    sup_fresh = _newest(supporting)
    con_fresh = _newest(contradicting)
    if sup_fresh and con_fresh and sup_fresh != con_fresh:
        return Resolution.SUPPORTED if sup_fresh > con_fresh else Resolution.CONTRADICTED

    if len(supporting) > len(contradicting):
        return Resolution.SUPPORTED
    if len(contradicting) > len(supporting):
        return Resolution.CONTRADICTED
    return Resolution.DISPUTED


def classify_claim(
    claim: Claim,
    sources_by_id: Dict[str, Source],
    now_utc: Optional[str] = None,
    model_category: Optional[ClaimCategory] = None,
) -> ClaimCategory:
    """Finalize a claim's category from its evidence:

      no evidence            -> UNVERIFIED
      contradiction wins      -> FALSE
      comparable opposition   -> OPINION (no consensus, §4.1)
      supported but a fresher contradicting source exists (time-sensitive)
                              -> OUTDATED
      supported               -> the model's semantic category if it set
                                 INCOMPLETE / OPINION / OUTDATED, else VERIFIED
    """
    supporting = [sources_by_id[s] for s in claim.sources if s in sources_by_id]
    contradicting = [sources_by_id[s] for s in claim.contradicting_sources if s in sources_by_id]

    resolution = resolve_conflict(supporting, contradicting, now_utc)
    if resolution is Resolution.NO_EVIDENCE:
        return ClaimCategory.UNVERIFIED
    if resolution is Resolution.CONTRADICTED:
        return ClaimCategory.FALSE
    if resolution is Resolution.DISPUTED:
        return ClaimCategory.OPINION

    # SUPPORTED — check "was true, newer data differs" before accepting.
    if contradicting and any(s.time_sensitive for s in supporting):
        newest_sup = _newest(supporting)
        newest_con = _newest(contradicting)
        if newest_sup and newest_con and newest_con > newest_sup:
            return ClaimCategory.OUTDATED

    if model_category in (ClaimCategory.INCOMPLETE, ClaimCategory.OPINION, ClaimCategory.OUTDATED):
        return model_category
    return ClaimCategory.VERIFIED


def _cap_confidence(category: ClaimCategory, base: int) -> int:
    """Bound the Phase-3 base confidence by the verdict. Confidence = how strongly
    the claim (as a TRUE statement) is supported, so FALSE/UNVERIFIED collapse to 1.
    """
    base = max(1, min(5, base))
    if category is ClaimCategory.VERIFIED:
        return base
    if category is ClaimCategory.INCOMPLETE:
        return min(base, 4)
    if category in (ClaimCategory.OUTDATED, ClaimCategory.OPINION):
        return min(base, 3)
    return 1  # FALSE, UNVERIFIED


def _compute_remediation(claim: Claim) -> Optional[str]:
    """Return a machine-readable Violation/Fix string when the claim needs
    remediation, or None when none is required (AC-4, AC-5).

    Decision table (evaluated after category and confidence are finalised):
      UNVERIFIED (0 supporting sources) -> guidance to gather sources.
      OPINION (disputed)                -> guidance to break the tie.
      OUTDATED (newer contradicting)    -> guidance to refresh the value.
      VERIFIED with fewer than 2 sources-> guidance to corroborate.
      Any other case (VERIFIED >=2, FALSE, INCOMPLETE) -> None.
    """
    cid = claim.id
    if claim.category is ClaimCategory.UNVERIFIED:
        return (
            f"Violation: claim {cid} has no supporting sources. "
            "Fix: web_search for the claim's key terms to gather >=2 sources."
        )
    if claim.category is ClaimCategory.OPINION:
        return (
            f"Violation: claim {cid} is disputed by comparable-tier sources. "
            "Fix: web_search a tier-S/regulator source to break the tie."
        )
    if claim.category is ClaimCategory.OUTDATED:
        return (
            f"Violation: claim {cid} is outdated (newer contradicting source). "
            "Fix: re-fetch the latest value and update."
        )
    if claim.category is ClaimCategory.VERIFIED and len(claim.sources) < 2:
        return (
            f"Violation: claim {cid} is VERIFIED on a single source. "
            "Fix: web_search a second independent source to corroborate."
        )
    return None


def factcheck_claim(
    claim: Claim,
    sources_by_id: Dict[str, Source],
    now_utc: Optional[str] = None,
    model_category: Optional[ClaimCategory] = None,
) -> Claim:
    """Set claim.category, claim.confidence (capped), claim.status, and
    claim.remediation from the evidence. MUTATES and returns the claim.
    Assumes claim.confidence already holds the Phase-3 base (else treated as 1).
    """
    category = classify_claim(claim, sources_by_id, now_utc, model_category)
    claim.category = category
    claim.confidence = _cap_confidence(category, claim.confidence)
    if category is ClaimCategory.VERIFIED:
        claim.status = ClaimStatus.CONFIRMED
    elif category is ClaimCategory.FALSE:
        claim.status = ClaimStatus.REJECTED
    else:
        claim.status = ClaimStatus.PENDING
    claim.remediation = _compute_remediation(claim)
    return claim


def factcheck_claims(
    claims: List[Claim],
    sources: List[Source],
    now_utc: Optional[str] = None,
    model_categories: Optional[Dict[str, ClaimCategory]] = None,
) -> List[Claim]:
    """Batch factcheck. `model_categories` maps claim.id -> the model's semantic
    category hint (INCOMPLETE/OPINION/OUTDATED), honored only when the claim is
    SUPPORTED (see classify_claim).
    """
    by_id = {s.id: s for s in sources}
    hints = model_categories or {}
    return [factcheck_claim(c, by_id, now_utc, hints.get(c.id)) for c in claims]
