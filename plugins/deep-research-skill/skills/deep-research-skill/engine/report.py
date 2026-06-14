"""Phase 6 — render verified findings into a cluster-first Markdown report.

Applies the role-aware disposition policy (engine/policy.py): VERIFIED ->
included, OUTDATED/INCOMPLETE/OPINION/UNVERIFIED -> flagged, FALSE external ->
a correction, FALSE own / UNVERIFIED-in-findings -> kept out (counted in the
footer). Deterministic. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .model import CATEGORY_LABELS, Claim, ClaimCategory, Snapshot, Source
from .policy import Disposition, ReportMode, disposition

_CONFIDENCE_EMOJI = {5: "🔵", 4: "🟢", 3: "🟡", 2: "🔴", 1: "⚪"}

_INCLUDED = {Disposition.INCLUDE, Disposition.INCLUDE_WITH_FLAG, Disposition.INCLUDE_AS_CORRECTION}

# Short labels for the inline score breakdown on each source line.
_BREAKDOWN_ABBR = {
    "authority": "auth",
    "recency": "rec",
    "independence": "indep",
    "traceability": "trace",
    "corroboration": "corrob",
}


def confidence_emoji(confidence: int) -> str:
    return _CONFIDENCE_EMOJI.get(max(1, min(5, confidence)), "⚪")


def _source_annotation(source: Source) -> str:
    """Inline annotation for a source line: a veto reason when disqualified,
    otherwise the compact score breakdown. Deterministic order. Pure formatting.
    """
    scores = source.scores
    if scores.disqualifiers:
        return " — ⛔ veto: " + ", ".join(scores.disqualifiers)
    if scores.breakdown:
        parts = [
            f"{_BREAKDOWN_ABBR.get(label, label)} {contribution:.2f}"
            for label, contribution in scores.breakdown
        ]
        return " — " + ", ".join(parts)
    return ""


def _flag(claim: Claim) -> str:
    label, emoji = CATEGORY_LABELS.get(claim.category, ("", ""))
    return f" {emoji} _{label}_" if label else ""


def _cites(claim: Claim, sources_by_id: Dict[str, Source]) -> str:
    refs = [f"[{sid}]" for sid in claim.sources if sid in sources_by_id]
    return f" — {' '.join(refs)}" if refs else ""


def _finding_line(claim: Claim, disp: Disposition, sources_by_id: Dict[str, Source]) -> str:
    flag = _flag(claim) if disp is Disposition.INCLUDE_WITH_FLAG else ""
    return f"- {confidence_emoji(claim.confidence)} {claim.text}{flag}{_cites(claim, sources_by_id)}"


def render_markdown(
    snapshot: Snapshot,
    report_mode: ReportMode = ReportMode.FINDINGS,
) -> str:
    """Render `snapshot` to a cluster-first Markdown report under `report_mode`."""
    sources_by_id = {s.id: s for s in snapshot.sources}
    claims_by_id = {c.id: c for c in snapshot.claims}
    disp = {c.id: disposition(c, report_mode) for c in snapshot.claims}

    corrections = [c for c in snapshot.claims if disp[c.id] is Disposition.INCLUDE_AS_CORRECTION]
    findings = [
        c for c in snapshot.claims
        if disp[c.id] in _INCLUDED and disp[c.id] is not Disposition.INCLUDE_AS_CORRECTION
    ]

    question = snapshot.task_frame.question if snapshot.task_frame else snapshot.run_id
    lines: List[str] = [f"# Отчёт: {question}"]
    if findings:
        agg = round(sum(c.confidence for c in findings) / len(findings))
        lines.append(f"**Агрегированная уверенность:** {confidence_emoji(agg)} {agg}/5 · выводов: {len(findings)}")
    lines.append("")

    # cluster-first
    grouped: set = set()
    for cluster in snapshot.clusters:
        in_cluster = [claims_by_id[cid] for cid in cluster.claim_ids if claims_by_id.get(cid) in findings]
        if not in_cluster:
            continue
        lines.append(f"## {cluster.title}")
        if cluster.uncertainty:
            lines.append(f"> ⚠️ {cluster.uncertainty}")
        for claim in in_cluster:
            grouped.add(claim.id)
            lines.append(_finding_line(claim, disp[claim.id], sources_by_id))
        lines.append("")

    ungrouped = [c for c in findings if c.id not in grouped]
    if ungrouped:
        lines.append("## Прочие выводы")
        for claim in ungrouped:
            lines.append(_finding_line(claim, disp[claim.id], sources_by_id))
        lines.append("")

    if corrections:
        lines.append("## Опровергнуто / коррекции")
        for claim in corrections:
            lines.append(f"- ❌ {claim.text}{_cites(claim, sources_by_id)}")
        lines.append("")

    if snapshot.sources:
        lines.append("## Источники")
        for source in snapshot.sources:
            tier = f" ({source.tier.value})" if source.tier is not None else ""
            lines.append(f"- [{source.id}]{tier} {source.url}{_source_annotation(source)}")
        lines.append("")

    counts = Counter(disp.values())
    lines.append("---")
    lines.append(
        f"_Выводов: {len(findings)} · коррекций: {len(corrections)} · "
        f"исключено-в-память: {counts.get(Disposition.EXCLUDE_BUT_RECORD, 0)} · "
        f"на пересмотр: {counts.get(Disposition.TRIGGER_REVISION, 0)}_"
    )
    return "\n".join(lines)
