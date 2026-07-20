"""Phase 6 — stance-target grouping / reconciliation (H9, hyperresearch reuse).

`claims.group_by_target` / `literature_matrix` from hyperresearch, offline: claims
carrying a (LLM-provided) `stance_target` are grouped by that key, and the engine
deterministically reconciles each group into consensus / contradicted / disputed,
surfacing the quantified values it mentions. This is the meta-analysis view a
synthesis step wants ("do these sources agree about X?"), computed — not guessed.

The stance detection stays in the agent layer (it sets `stance_target`); the
engine only groups + reconciles, so it stays pure/deterministic/offline/stdlib.
A claim without `stance_target` is simply not in the matrix. Python >= 3.10.
"""

from __future__ import annotations

from typing import Dict, List

from .model import Claim, ClaimCategory
from .numeric import digit_key, number_tokens


def group_by_target(claims: List[Claim]) -> Dict[str, List[Claim]]:
    """{stance_target: [claims]} preserving input order within each group; claims
    with no `stance_target` are excluded."""
    groups: Dict[str, List[Claim]] = {}
    for claim in claims:
        target = getattr(claim, "stance_target", None)
        if not target:
            continue
        groups.setdefault(target, []).append(claim)
    return groups


def _verdict(group: List[Claim]) -> str:
    """Honest reconciliation label from claim categories:
      consensus     — all affirm (only VERIFIED)
      refuted       — all deny (only FALSE): unanimous refutation is agreement
      contradicted  — affirm AND deny both present (VERIFIED + FALSE)
      inconclusive  — no decisive verdict at all (only OPINION/OUTDATED/
                      INCOMPLETE/UNVERIFIED) — nothing to dispute
      disputed      — a decisive verdict mixed with non-decisive ones
    NOTE: this is a CATEGORY-agreement view; 'consensus' means every claim is
    individually VERIFIED, not that they assert the same value — see
    numeric_divergence in reconcile() for value-level disagreement."""
    cats = {c.category for c in group}
    has_v = ClaimCategory.VERIFIED in cats
    has_f = ClaimCategory.FALSE in cats
    if has_v and has_f:
        return "contradicted"
    if cats == {ClaimCategory.VERIFIED}:
        return "consensus"
    if cats == {ClaimCategory.FALSE}:
        return "refuted"
    if not has_v and not has_f:
        return "inconclusive"
    return "disputed"


def reconcile(claims: List[Claim]) -> List[Dict]:
    """Per stance_target: verdict + members + category counts + quantified values.
    Targets sorted ascending; numbers sorted — fully deterministic output."""
    groups = group_by_target(claims)
    rows: List[Dict] = []
    for target in sorted(groups):
        group = groups[target]
        cat_counts: Dict[str, int] = {}
        for c in group:
            cat_counts[c.category.value] = cat_counts.get(c.category.value, 0) + 1
        # Canonical values: dedupe on digit-key so '30 000' and '30000' are one
        # entry (fixes the raw-token false-split). numeric_divergence flags a
        # group whose members mention >1 distinct value — so a 'consensus' of
        # verdicts can't hide a disagreement of numbers.
        numbers = sorted({digit_key(tok) for c in group for tok in number_tokens(c.text)})
        rows.append({
            "target": target,
            "claim_ids": [c.id for c in group],
            "n_claims": len(group),
            "verdict": _verdict(group),
            "categories": cat_counts,
            "numbers": numbers,
            "numeric_divergence": len(numbers) > 1,
        })
    return rows
