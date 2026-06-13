"""Phase 10 — compact handoff builder.

Converts a Snapshot into a concise context-transfer dict for agent hand-offs
between research phases. Pure function — no I/O, no randomness, deterministic.

AC10-3: build_handoff(snapshot) -> dict with EXACTLY these keys:
    objective, active_plan, inspected_sources, decisions, pending,
    next_step, do_not_redo
"""

from __future__ import annotations

from typing import Any, Dict, List

from .model import ClaimStatus, Snapshot, SourceStatus


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def build_handoff(snapshot: Snapshot) -> Dict[str, Any]:
    """Build a compact handoff dict from *snapshot*.

    Parameters
    ----------
    snapshot:
        A fully-loaded Snapshot (no I/O; caller is responsible for loading).

    Returns
    -------
    dict with EXACTLY the keys:
        objective          – the research question (str)
        active_plan        – list of {"id": str, "description": str, "status": str}
                             for every subtask in the snapshot
        inspected_sources  – list of {"id": str, "url": str} for sources whose
                             status == RENDERED (no extract bodies)
        decisions          – list of brief notes derived from gate results and
                             confirmed/rejected claims (confidence + verdict)
        pending            – snapshot.open_items (list of str)
        next_step          – snapshot.resume_instruction (str)
        do_not_redo        – list of ids: already-rendered source ids PLUS ids of
                             confirmed claims (status == CONFIRMED)
    """
    # --- objective -----------------------------------------------------------
    objective: str = snapshot.task_frame.question

    # --- active_plan ---------------------------------------------------------
    active_plan: List[Dict[str, str]] = [
        {
            "id": st.id,
            "description": st.description,
            "status": st.status.value,
        }
        for st in snapshot.subtasks
    ]

    # --- inspected_sources ---------------------------------------------------
    # Only RENDERED sources; extract bodies are intentionally excluded.
    inspected_sources: List[Dict[str, str]] = [
        {"id": src.id, "url": src.url}
        for src in snapshot.sources
        if src.status == SourceStatus.RENDERED
    ]

    # --- decisions -----------------------------------------------------------
    # Build brief notes from:
    #   1. last_gate result (if any)
    #   2. gate-signal fields on the snapshot
    #   3. confirmed / rejected claims (confidence + verdict explanation)
    decisions: List[str] = []

    # Gate-signal fields
    if snapshot.sources_screened:
        decisions.append(f"sources_screened: {snapshot.sources_screened}")
    if snapshot.extraction_table_complete:
        decisions.append("extraction_table_complete: True")
    if snapshot.citations_verified:
        decisions.append("citations_verified: True")

    # Last gate result
    if snapshot.last_gate is not None:
        gate = snapshot.last_gate
        decisions.append(f"gate {gate.id}: {gate.verdict.value}")

    # Per-claim brief notes (only for non-PENDING claims to keep it compact)
    for claim in snapshot.claims:
        if claim.status == ClaimStatus.PENDING:
            continue
        # Build a compact note: id + status + category + confidence + optional explanation
        note_parts = [
            f"claim {claim.id} [{claim.status.value}]",
            f"category={claim.category.value}",
            f"confidence={claim.confidence}/5",
        ]
        if claim.verdict_explanation:
            # Truncate long explanations to keep handoff compact
            explanation = claim.verdict_explanation
            if len(explanation) > 120:
                explanation = explanation[:117] + "..."
            note_parts.append(f"verdict={explanation!r}")
        decisions.append("; ".join(note_parts))

    # --- pending -------------------------------------------------------------
    pending: List[str] = list(snapshot.open_items)

    # --- next_step -----------------------------------------------------------
    next_step: str = snapshot.resume_instruction

    # --- do_not_redo ---------------------------------------------------------
    # Rendered source ids (already fetched & extracted — do not re-fetch)
    rendered_source_ids = [
        src.id
        for src in snapshot.sources
        if src.status == SourceStatus.RENDERED
    ]
    # Confirmed claim ids (fact-checked and accepted — do not re-verify)
    confirmed_claim_ids = [
        claim.id
        for claim in snapshot.claims
        if claim.status == ClaimStatus.CONFIRMED
    ]
    do_not_redo: List[str] = rendered_source_ids + confirmed_claim_ids

    return {
        "objective": objective,
        "active_plan": active_plan,
        "inspected_sources": inspected_sources,
        "decisions": decisions,
        "pending": pending,
        "next_step": next_step,
        "do_not_redo": do_not_redo,
    }
