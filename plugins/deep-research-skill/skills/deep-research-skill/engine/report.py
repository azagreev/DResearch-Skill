"""Phase 6 — render verified findings into a cluster-first Markdown report.

Applies the role-aware disposition policy (engine/policy.py): VERIFIED ->
included, OUTDATED/INCOMPLETE/OPINION/UNVERIFIED -> flagged, FALSE external ->
a correction, FALSE own / UNVERIFIED-in-findings -> kept out (counted in the
footer). Deterministic. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from .model import Claim, ClaimCategory, Snapshot, Source, get_category_labels
from .policy import Disposition, ReportMode, disposition

_CONFIDENCE_EMOJI = {5: "🔵", 4: "🟢", 3: "🟡", 2: "🔴", 1: "⚪"}

_INCLUDED = {Disposition.INCLUDE, Disposition.INCLUDE_WITH_FLAG, Disposition.INCLUDE_AS_CORRECTION}

# Short labels for the inline score breakdown on each source line.
# Language-neutral shorthand — intentionally NOT translated.
_BREAKDOWN_ABBR = {
    "authority": "auth",
    "recency": "rec",
    "independence": "indep",
    "traceability": "trace",
    "corroboration": "corrob",
}

# Report section labels by language. "ru" is the default and reproduces the
# original output byte-for-byte; "en" is for English-only contexts (benchmarks,
# English tasks). Driven by TaskFrame.language (v1.4 — activates the field).
_LABELS = {
    "ru": {
        "title": "Отчёт",
        "agg_confidence": "Агрегированная уверенность",
        "findings": "выводов",
        "other_findings": "Прочие выводы",
        "corrections": "Опровергнуто / коррекции",
        "sources": "Источники",
        "footer": ("Выводов: {findings} · коррекций: {corrections} · "
                   "исключено-в-память: {excluded} · на пересмотр: {revision}"),
    },
    "en": {
        "title": "Report",
        "agg_confidence": "Aggregate confidence",
        "findings": "findings",
        "other_findings": "Other findings",
        "corrections": "Refuted / corrections",
        "sources": "Sources",
        "footer": ("Findings: {findings} · corrections: {corrections} · "
                   "excluded-to-memory: {excluded} · flagged-for-revision: {revision}"),
    },
}


def _labels(language: str) -> Dict[str, str]:
    """Section-label table for the report language; falls back to ru."""
    return _LABELS.get((language or "ru").lower(), _LABELS["ru"])


def confidence_emoji(confidence: int) -> str:
    return _CONFIDENCE_EMOJI.get(max(1, min(5, confidence)), "⚪")


def _source_annotation(source: Source) -> str:
    """Inline annotation for a source line: the compact score breakdown.
    Deterministic order. Pure formatting.
    """
    scores = source.scores
    if scores.breakdown:
        parts = [
            f"{_BREAKDOWN_ABBR.get(label, label)} {contribution:.2f}"
            for label, contribution in scores.breakdown
        ]
        return " — " + ", ".join(parts)
    return ""


def _flag(claim: Claim, language: str = "ru") -> str:
    label, emoji = get_category_labels(language).get(claim.category, ("", ""))
    return f" {emoji} _{label}_" if label else ""


def _cites(claim: Claim, sources_by_id: Dict[str, Source]) -> str:
    refs = [f"[{sid}]" for sid in claim.sources if sid in sources_by_id]
    return f" — {' '.join(refs)}" if refs else ""


def _finding_line(
    claim: Claim, disp: Disposition, sources_by_id: Dict[str, Source], language: str = "ru"
) -> str:
    flag = _flag(claim, language) if disp is Disposition.INCLUDE_WITH_FLAG else ""
    return f"- {confidence_emoji(claim.confidence)} {claim.text}{flag}{_cites(claim, sources_by_id)}"


def render_markdown(
    snapshot: Snapshot,
    report_mode: ReportMode = ReportMode.FINDINGS,
    language: Optional[str] = None,
) -> str:
    """Render `snapshot` to a cluster-first Markdown report under `report_mode`.

    `language` selects report labels — section headers AND per-claim category
    flags ("ru" default, "en" supported). When None it is derived from
    `snapshot.task_frame.language`, so the field drives the
    report language end-to-end for every caller (v1.4 — activates the field). An
    explicit value overrides the snapshot.
    """
    if language is None:
        language = snapshot.task_frame.language if snapshot.task_frame else "ru"
    labels = _labels(language)

    sources_by_id = {s.id: s for s in snapshot.sources}
    claims_by_id = {c.id: c for c in snapshot.claims}
    disp = {c.id: disposition(c, report_mode) for c in snapshot.claims}

    corrections = [c for c in snapshot.claims if disp[c.id] is Disposition.INCLUDE_AS_CORRECTION]
    findings = [
        c for c in snapshot.claims
        if disp[c.id] in _INCLUDED and disp[c.id] is not Disposition.INCLUDE_AS_CORRECTION
    ]

    question = snapshot.task_frame.question if snapshot.task_frame else snapshot.run_id
    lines: List[str] = [f"# {labels['title']}: {question}"]
    if findings:
        agg = round(sum(c.confidence for c in findings) / len(findings))
        lines.append(
            f"**{labels['agg_confidence']}:** {confidence_emoji(agg)} {agg}/5 · "
            f"{labels['findings']}: {len(findings)}"
        )
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
            lines.append(_finding_line(claim, disp[claim.id], sources_by_id, language))
        lines.append("")

    ungrouped = [c for c in findings if c.id not in grouped]
    if ungrouped:
        lines.append(f"## {labels['other_findings']}")
        for claim in ungrouped:
            lines.append(_finding_line(claim, disp[claim.id], sources_by_id, language))
        lines.append("")

    if corrections:
        lines.append(f"## {labels['corrections']}")
        for claim in corrections:
            lines.append(f"- ❌ {claim.text}{_cites(claim, sources_by_id)}")
        lines.append("")

    if snapshot.sources:
        lines.append(f"## {labels['sources']}")
        for source in snapshot.sources:
            tier = f" ({source.tier.value})" if source.tier is not None else ""
            lines.append(f"- [{source.id}]{tier} {source.url}{_source_annotation(source)}")
        lines.append("")

    counts = Counter(disp.values())
    lines.append("---")
    lines.append(
        "_" + labels["footer"].format(
            findings=len(findings),
            corrections=len(corrections),
            excluded=counts.get(Disposition.EXCLUDE_BUT_RECORD, 0),
            revision=counts.get(Disposition.TRIGGER_REVISION, 0),
        ) + "_"
    )
    return "\n".join(lines)
