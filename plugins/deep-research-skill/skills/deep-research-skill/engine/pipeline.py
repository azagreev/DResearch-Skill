"""Phase 7 — pipeline glue: assemble loose lists into a Snapshot and run the
full post-collection flow end to end.

The per-step functions (ingest/score/factcheck/cluster) operate on bare lists;
this module wires them into the Snapshot spine so report/memory/state have
something to consume. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from . import factcheck, score, state, verify
from .cluster import cluster_claims
from .ingest import ingest_sources
from .model import (
    Claim,
    ClaimCategory,
    EvidenceCluster,
    GateResult,
    GateVerdict,
    Snapshot,
    Source,
    TaskFrame,
)
from .state import compute_fingerprint
from .telemetry import RunTrace


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

    Note: collect.CollectionResult.items are valid raw_sources — the dicts
    produced by collect.normalize() already carry url, title, snippet,
    fetched_via, and metadata, which is exactly what ingest.source_from_raw
    consumes.  No adapter is needed.
    """
    # AC15-5: deterministic per-stage run trace. ts is always now_utc (no clock).
    trace = RunTrace()

    sources, merges = ingest_sources(raw_sources, now_utc, dedupe=dedupe)
    reconcile_merges(claims, merges)
    trace.append("ingest", ts=now_utc)

    score.score_sources(sources, now_utc)
    score.score_claims(claims, sources)
    trace.append("score", ts=now_utc)

    factcheck.factcheck_claims(claims, sources, now_utc, model_categories=model_categories)
    trace.append("factcheck", ts=now_utc)

    # AC15-5 auto-verify: independently re-derive each claim's category from the
    # evidence (verify ignores verdict_explanation — independence preserved) and
    # record the result + disagreement flag on the claim's metadata. Done AFTER
    # factcheck so claim.category reflects the finalized verdict being checked.
    # SCOPE NOTE: factcheck and verify share classify_claim, so on a hint-less run
    # they agree by construction and `disagreement` is always False. The flag only
    # fires when a `model_categories` hint was *honored* by factcheck but diverges
    # from the pure-evidence re-derivation — i.e. it catches an honored author/model
    # semantic override, NOT general evidence-vs-recorded drift. Broader drift
    # detection (e.g. perturbation-based reverify) is a deliberate future follow-up.
    for claim in claims:
        claim.metadata["disagreement"] = verify.disagreement(claim, sources, now_utc)
        claim.metadata["reverified_category"] = verify.reverify_claim(
            claim, sources, now_utc
        ).value
    trace.append("verify", ts=now_utc)

    clusters = cluster_claims(claims)
    trace.append("cluster", ts=now_utc)

    snapshot = build_snapshot(run_id, task_frame, sources, claims, clusters, now_utc)
    trace.append("build", ts=now_utc)
    snapshot.trace = trace.as_list()

    # Gate signal fields (AC10-6) — MUST be set BEFORE consulting the gate, since
    # gate_blocks_transition reads sources_screened / citations_verified.
    snapshot.sources_screened = len(sources)
    # citations_verified: every claim has at least one supporting source
    snapshot.citations_verified = bool(claims) and all(len(c.sources) >= 1 for c in claims)
    # extraction_table_complete: every source has a non-empty extract dict
    snapshot.extraction_table_complete = (
        all(bool(s.extract) for s in sources) if sources else False
    )

    # AC15-5 gate-consult next_phase (replaces the hardcoded 5): the highest
    # target phase in 1..5 the gate does not block. A clean run reaches 5;
    # citations_verified False caps it at 4; sources_screened 0 caps it at 1.
    next_phase = max(
        (p for p in range(1, 6) if state.gate_blocks_transition(snapshot, p) is None),
        default=0,
    )
    snapshot.next_phase = next_phase

    blocked_at_5 = state.gate_blocks_transition(snapshot, 5)
    snapshot.last_gate = GateResult(
        id="gate_transition",
        verdict=GateVerdict.PASS if blocked_at_5 is None else GateVerdict.FAIL,
        reason=blocked_at_5,
    )

    return snapshot, merges
