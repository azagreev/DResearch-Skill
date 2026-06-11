"""Phase 4 — evidence clustering of claims.

Greedy text-similarity grouping (reusing dedupe.text_similarity) + Maximal
Marginal Relevance (MMR) to pick a small, diverse set of representative claims
per cluster. Deterministic. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from typing import List, Optional

from .dedupe import text_similarity
from .model import Claim, EvidenceCluster


def _mmr_select(group: List[Claim], max_reps: int, lambda_: float) -> List[str]:
    """MMR over a cluster's claims: relevance = confidence/5, diversity = 1 - max
    similarity to already-picked. Highest-confidence claim seeds the set; then
    each pick maximizes lambda*relevance - (1-lambda)*max_sim. Ties break by id.
    """
    if not group:
        return []
    remaining = sorted(group, key=lambda c: (-c.confidence, c.id))
    selected = [remaining.pop(0)]
    while remaining and len(selected) < max_reps:
        best: Optional[Claim] = None
        best_score = None
        for cand in remaining:
            relevance = cand.confidence / 5.0
            max_sim = max(text_similarity(cand.text, s.text) for s in selected)
            mmr = lambda_ * relevance - (1.0 - lambda_) * max_sim
            if best_score is None or mmr > best_score or (mmr == best_score and cand.id < best.id):
                best_score = mmr
                best = cand
        selected.append(best)
        remaining.remove(best)
    return [c.id for c in selected]


def _cluster_uncertainty(group: List[Claim]) -> Optional[str]:
    if len(group) == 1:
        return "thin-evidence"
    sources = set()
    for claim in group:
        sources.update(claim.sources)
    if len(sources) <= 1:
        return "single-source"
    return None


def cluster_claims(
    claims: List[Claim],
    sim_threshold: float = 0.55,
    max_reps: int = 2,
    lambda_: float = 0.6,
) -> List[EvidenceCluster]:
    """Group `claims` into evidence clusters by text similarity (>= sim_threshold
    to any member), pick MMR representatives, and flag thin/single-source clusters.

    MUTATES each claim's `cluster_id` to its assigned cluster. Order-stable: a
    claim joins the first cluster it is similar to, else starts a new one.
    """
    groups: List[List[Claim]] = []
    for claim in claims:
        placed = False
        for group in groups:
            if any(text_similarity(claim.text, member.text) >= sim_threshold for member in group):
                group.append(claim)
                placed = True
                break
        if not placed:
            groups.append([claim])

    clusters: List[EvidenceCluster] = []
    for index, group in enumerate(groups, start=1):
        cluster_id = f"K{index}"
        for member in group:
            member.cluster_id = cluster_id
        title = max(group, key=lambda c: (c.confidence, c.id)).text
        clusters.append(
            EvidenceCluster(
                id=cluster_id,
                title=title[:120],
                claim_ids=[c.id for c in group],
                representative_ids=_mmr_select(group, max_reps, lambda_),
                uncertainty=_cluster_uncertainty(group),
            )
        )
    return clusters
