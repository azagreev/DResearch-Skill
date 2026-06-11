"""Phase 7 — pipeline glue: assemble loose lists into a Snapshot and run the
full post-collection flow end to end.

The per-step functions (ingest/score/factcheck/cluster) operate on bare lists;
this module wires them into the Snapshot spine so report/memory/state have
something to consume. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from . import factcheck, score
from .cluster import cluster_claims
from .ingest import ingest_sources
from .model import Claim, ClaimCategory, EvidenceCluster, Snapshot, Source, TaskFrame
from .state import compute_fingerprint


def reconcile_merges(claims: List[Claim], merges: List[Tuple[str, str]]) -> List[Claim]:
    """After dedupe, rewrite any dropped source id referenced by a claim to the
    kept id (per the merge map [(kept_id, dropped_id)]), de-duplicating the
    resulting id lists. MUTATES and returns `claims`. Prevents dangling refs that
    validate_snapshot would flag.
    """
    remap = {dropped: kept for kept, dropped in merges}

    def fix(ids: List[str]) -> List[str]:
        out: List[str] = []
        for i in ids:
            mapped = remap.get(i, i)
            if mapped not in out:
                out.append(mapped)
        return out

    for claim in claims:
        claim.sources = fix(claim.sources)
        claim.contradicting_sources = fix(claim.contradicting_sources)
    return claims


def build_snapshot(
    run_id: str,
    task_frame: TaskFrame,
    sources: List[Source],
    claims: List[Claim],
    clusters: Optional[List[EvidenceCluster]] = None,
    now_utc: str = "",
    next_phase: int = 0,
) -> Snapshot:
    """Assemble the engine spine: a Snapshot with a computed task_fingerprint."""
    return Snapshot(
        run_id=run_id,
        task_fingerprint=compute_fingerprint(task_frame),
        task_frame=task_frame,
        created_utc=now_utc,
        next_phase=next_phase,
        sources=list(sources),
        claims=list(claims),
        clusters=list(clusters or []),
    )


def run_pipeline(
    run_id: str,
    task_frame: TaskFrame,
    raw_sources: List[Dict[str, Any]],
    claims: List[Claim],
    now_utc: str,
    model_categories: Optional[Dict[str, ClaimCategory]] = None,
    dedupe: bool = True,
) -> Tuple[Snapshot, List[Tuple[str, str]]]:
    """End-to-end post-collection flow:
      ingest(raw -> Source, dedupe) -> reconcile claim refs -> score sources
      (tier) -> score claims (base confidence) -> factcheck (verdict + cap) ->
      cluster -> build Snapshot.
    Returns (snapshot, merges). The model supplies `claims` (with per-source
    stance) and optional `model_categories` hints.
    """
    sources, merges = ingest_sources(raw_sources, now_utc, dedupe=dedupe)
    reconcile_merges(claims, merges)
    score.score_sources(sources, now_utc)
    score.score_claims(claims, sources)
    factcheck.factcheck_claims(claims, sources, now_utc, model_categories=model_categories)
    clusters = cluster_claims(claims)
    snapshot = build_snapshot(run_id, task_frame, sources, claims, clusters, now_utc, next_phase=5)
    return snapshot, merges
