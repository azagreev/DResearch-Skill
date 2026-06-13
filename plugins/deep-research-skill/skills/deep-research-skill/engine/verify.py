"""Phase 11 — independent verifier (AC11-5).

The verifier RE-DERIVES a claim's category from first principles — claim text +
the evidence (its supporting / contradicting Source ids) — using ONLY the pure
functions in engine.factcheck (classify_claim / resolve_conflict). It never calls
factcheck_claim (which mutates), never mutates the claim it is handed, and never
reads claim.verdict_explanation. That last point is what makes the verifier
*independent*: it does not borrow the author's stated reasoning, so when the
author's recorded category disagrees with what the evidence actually supports,
the disagreement surfaces instead of being rubber-stamped.

stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .factcheck import classify_claim
from .model import Claim, ClaimCategory, Source


def _sources_by_id(sources: List[Source]) -> Dict[str, Source]:
    return {s.id: s for s in sources}


def reverify_claim(
    claim: Claim,
    sources: List[Source],
    now_utc: Optional[str] = None,
) -> ClaimCategory:
    """Re-derive the claim's category purely from claim + sources.

    Reuses engine.factcheck.classify_claim (which in turn uses resolve_conflict)
    with NO model_category hint — the author's semantic guess is deliberately
    withheld so the verdict reflects the evidence alone.

    Guarantees:
      * does NOT mutate `claim` (classify_claim is read-only on the claim) or any
        Source in `sources`;
      * does NOT read `claim.verdict_explanation` (independence from the author's
        reasoning);
      * deterministic — same (claim, sources, now_utc) -> same category.
    """
    return classify_claim(
        claim,
        _sources_by_id(sources),
        now_utc=now_utc,
        model_category=None,
    )


def disagreement(
    claim: Claim,
    sources: List[Source],
    now_utc: Optional[str] = None,
) -> bool:
    """True when the independently re-derived category differs from the category
    currently recorded on the claim — i.e. the author's verdict is not what the
    evidence supports."""
    return reverify_claim(claim, sources, now_utc=now_utc) != claim.category
