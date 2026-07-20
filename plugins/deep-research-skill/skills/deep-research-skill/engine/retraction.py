"""Phase 4 — retraction flag-and-veto (H3, hyperresearch reuse).

A source flagged retracted must not prop up a finding: factcheck.classify_claim
strips retracted supporters unless the claim explicitly acknowledges the
retraction (a debunk about it). The veto hot-path keys on the explicit
Source.retracted flag only (zero false positives on legacy fixtures). A separate
deterministic language detector (en+ru) can pre-mark sources from their content
via `mark_retractions` (opt-in, e.g. the `retraction` verb) — the engine cannot
reach a live retraction feed, so the flag is set by the caller or the detector.

Pure, deterministic, offline, stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

import re
from typing import Dict, List

from .model import Claim, Source

# Retraction-notice language, English + Russian. Intentionally specific so
# mark_retractions doesn't flag a source that merely mentions the topic.
_RETRACTION_RE = re.compile(
    r"has been retracted|was retracted|\bretracted\b|retraction notice|"
    r"notice of retraction|отозван[аоы]?|ретрагирова|отзыв стать|статья отозвана",
    re.IGNORECASE,
)


def detect_retraction(text: str) -> bool:
    """True iff `text` contains retraction-notice language."""
    return bool(text) and bool(_RETRACTION_RE.search(text))


def is_retracted(source: Source) -> bool:
    """The veto predicate: keyed on the explicit flag only (deterministic, no
    false positives on sources that merely discuss retractions)."""
    return bool(source.retracted)


def _source_content(source: Source) -> str:
    content = source.extract.get("content")
    if content is None:
        content = source.extract.get("snippet") or ""
    return content or ""


def mark_retractions(sources: List[Source]) -> List[str]:
    """Set source.retracted=True for any source whose content carries retraction
    language, ONLY where the flag is unset (None) — an explicit True/False is
    preserved. Returns the ids newly flagged (in input order). Opt-in: not called
    by the default pipeline, so it never changes existing behavior implicitly."""
    flagged: List[str] = []
    for source in sources:
        if source.retracted is None and detect_retraction(_source_content(source)):
            source.retracted = True
            flagged.append(source.id)
    return flagged


def acknowledges_retraction(claim: Claim) -> bool:
    """True when the claim itself is about the retraction (a debunk) — so its
    retracted source is the subject, not hidden support, and must be kept.

    The metadata flag `acknowledges_retraction` is the PRIMARY, reliable
    signal: a real debunk's text carries the claim under adjudication (e.g.
    'Vaccine X causes Y'), not meta-commentary, so the text heuristic below is
    best-effort only. Callers building a debunk of retracted work should set
    metadata['acknowledges_retraction'] = True."""
    if claim.metadata.get("acknowledges_retraction"):
        return True
    return detect_retraction(claim.text)


def retracted_support(claim: Claim, sources_by_id: Dict[str, Source]) -> List[str]:
    """Cited source ids that are retracted and NOT acknowledged (the ids that
    classify_claim strips from support). Empty when the claim acknowledges."""
    if acknowledges_retraction(claim):
        return []
    return [
        sid for sid in claim.sources
        if sources_by_id.get(sid) is not None and is_retracted(sources_by_id[sid])
    ]
