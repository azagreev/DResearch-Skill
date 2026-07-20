"""Phase 6 — render verified findings into a cluster-first Markdown report.

Applies the role-aware disposition policy (engine/policy.py): VERIFIED ->
included, OUTDATED/INCOMPLETE/OPINION/UNVERIFIED -> flagged, FALSE external ->
a correction, FALSE own / UNVERIFIED-in-findings -> kept out (counted in the
footer). Deterministic. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from . import ingest, quoteintegrity
from .model import Claim, ClaimCategory, Snapshot, Source, _is_citation_span, get_category_labels
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
        "clamp_note": "Скорректированные цитатные диапазоны (clamp)",
        "quote_fail_note": "Заблокировано проверкой дословности цитат (quote-integrity)",
        "quote_fail_line": "claim {cid}: дословная цитата не подтверждена источником ({srcs})",
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
        "clamp_note": "Adjusted citation spans (clamped)",
        "quote_fail_note": "Blocked by quote-integrity check",
        "quote_fail_line": "claim {cid}: verbatim quote not supported by source ({srcs})",
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


def resolve_citation_spans(claims: List[Claim], sources_by_id: Dict[str, Source]) -> List[str]:
    """Clamp every claim.citation_spans entry into its source's actual content
    bounds (R2 / AC2.3), mutating the spans in place. A span outside
    [1, len(content_lines)] is clamped, never silently — each adjustment is
    recorded and returned as a note. No-op (returns []) for claims/spans that
    don't exist, so calling this on a snapshot with no spans is always safe.
    """
    notes: List[str] = []
    for claim in claims:
        spans = getattr(claim, "citation_spans", None)
        if not spans:
            continue
        for sid, span in list(spans.items()):
            # Only clamp/annotate spans for sources the claim actually cites;
            # _cites renders by claim.sources, so a span for any other sid would
            # produce a clamp note for a citation that never appears (misleading).
            if sid not in claim.sources:
                continue
            source = sources_by_id.get(sid)
            if source is None or not _is_citation_span(span):
                continue
            lines = ingest.content_lines(source)
            max_line = max(len(lines), 1)
            a, b = span[0], span[1]
            new_a = min(max(a, 1), max_line)
            new_b = min(max(b, 1), max_line)
            if new_a > new_b:
                new_a, new_b = new_b, new_a
            if [new_a, new_b] != [a, b]:
                notes.append(
                    f"claim {claim.id}: citation span {sid} L{a}-L{b} out of bounds "
                    f"(content has {len(lines)} line(s)) — clamped to L{new_a}-L{new_b}"
                )
                spans[sid] = [new_a, new_b]
    return notes


def _cites(claim: Claim, sources_by_id: Dict[str, Source]) -> str:
    spans = getattr(claim, "citation_spans", None) or {}
    refs = []
    for sid in claim.sources:
        if sid not in sources_by_id:
            continue
        span = spans.get(sid)
        if _is_citation_span(span):
            refs.append(f"【{sid}†L{span[0]}-L{span[1]}】")
        else:
            refs.append(f"[{sid}]")
    return f" — {' '.join(refs)}" if refs else ""


def _finding_line(
    claim: Claim, disp: Disposition, sources_by_id: Dict[str, Source],
    language: str = "ru", verbose: bool = False,
) -> str:
    flag = _flag(claim, language) if disp is Disposition.INCLUDE_WITH_FLAG else ""
    emoji = f"{confidence_emoji(claim.confidence)} " if verbose else ""
    return f"- {emoji}{claim.text}{flag}{_cites(claim, sources_by_id)}"


def render_markdown(
    snapshot: Snapshot,
    report_mode: ReportMode = ReportMode.FINDINGS,
    language: Optional[str] = None,
    verbose: bool = False,
) -> str:
    """Render `snapshot` to a cluster-first Markdown report under `report_mode`.

    `language` selects report labels — section headers AND per-claim category
    flags ("ru" default, "en" supported). When None it is derived from
    `snapshot.task_frame.language`, so the field drives the
    report language end-to-end for every caller (v1.4 — activates the field). An
    explicit value overrides the snapshot.

    `verbose` (v1.5, default False) adds the confidence emojis and the per-source
    score breakdown. The lean default omits both — they are decoration, not
    content; opt in via `--verbose` / `verbose=True`.
    """
    if language is None:
        language = snapshot.task_frame.language if snapshot.task_frame else "ru"
    labels = _labels(language)

    sources_by_id = {s.id: s for s in snapshot.sources}
    claims_by_id = {c.id: c for c in snapshot.claims}
    # Safe no-op when no claim carries a citation_spans entry (R2 / AC2.3):
    # clamps any out-of-bounds span before rendering so _cites never emits an
    # unresolved/invalid line range. When a clamp actually happens the notes
    # are surfaced in the report footer below (AC2.3 — never silent for the
    # reader); with no clamp, clamp_notes is empty and output is byte-identical.
    clamp_notes = resolve_citation_spans(snapshot.claims, sources_by_id)
    disp = {c.id: disposition(c, report_mode) for c in snapshot.claims}

    # H1 quote-integrity gate: a claim whose verbatim quote is not backed by
    # the cited source at the cited span never ships (any mode). Scoped to
    # claims carrying citation_spans (R2 opt-in), so no-span claims are
    # untouched and output stays byte-identical when nothing fails. The
    # unverified quote text is deliberately NOT echoed — only the claim id.
    quote_issues = quoteintegrity.check_snapshot(snapshot)

    # Corrections (debunks: EXTERNAL_CLAIM + FALSE -> INCLUDE_AS_CORRECTION)
    # quote the REFUTED assertion verbatim; that quote is the thing being
    # debunked, not a fact we assert, and its provenance is contradicting_
    # sources, not sources. So the quote-integrity gate must NOT suppress a
    # correction — it protects our OWN asserted findings only.
    corrections = [c for c in snapshot.claims if disp[c.id] is Disposition.INCLUDE_AS_CORRECTION]
    _finding_candidates = [
        c for c in snapshot.claims
        if disp[c.id] in _INCLUDED and disp[c.id] is not Disposition.INCLUDE_AS_CORRECTION
    ]
    # A finding whose verbatim quote is not backed by the cited source at the
    # cited span never ships (H1). Intersect with the would-be-included set so
    # the note lists only claims a reader would otherwise have seen (no noise
    # for claims already excluded by disposition). Order follows snapshot.claims
    # (deterministic).
    quote_blocked = [c for c in _finding_candidates if c.id in quote_issues]
    _blocked_ids = {c.id for c in quote_blocked}
    findings = [c for c in _finding_candidates if c.id not in _blocked_ids]

    question = snapshot.task_frame.question if snapshot.task_frame else snapshot.run_id
    lines: List[str] = [f"# {labels['title']}: {question}"]
    if findings:
        agg = round(sum(c.confidence for c in findings) / len(findings))
        conf = f"{confidence_emoji(agg)} " if verbose else ""
        lines.append(
            f"**{labels['agg_confidence']}:** {conf}{agg}/5 · "
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
            lines.append(_finding_line(claim, disp[claim.id], sources_by_id, language, verbose))
        lines.append("")

    ungrouped = [c for c in findings if c.id not in grouped]
    if ungrouped:
        lines.append(f"## {labels['other_findings']}")
        for claim in ungrouped:
            lines.append(_finding_line(claim, disp[claim.id], sources_by_id, language, verbose))
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
            ann = _source_annotation(source) if verbose else ""
            lines.append(f"- [{source.id}]{tier} {source.url}{ann}")
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

    # AC2.3 (R2 finding #1): surface clamp adjustments to the reader, but ONLY
    # when a clamp actually occurred — with no clamp this block adds nothing and
    # the output stays byte-identical to the pre-R2 render (AC2.5 / determinism).
    if clamp_notes:
        lines.append("")
        lines.append(f"> ⚠️ _{labels['clamp_note']}_")
        for note in clamp_notes:
            lines.append(f"> - {note}")

    # H1: surface quote-integrity blocks — claim id + cited sources only,
    # never the unverified quote text. Byte-identical when nothing failed.
    if quote_blocked:
        lines.append("")
        lines.append(f"> ⚠️ _{labels['quote_fail_note']}_")
        for claim in quote_blocked:
            srcs = ", ".join(claim.sources)
            lines.append("> - " + labels['quote_fail_line'].format(cid=claim.id, srcs=srcs))

    return "\n".join(lines)
