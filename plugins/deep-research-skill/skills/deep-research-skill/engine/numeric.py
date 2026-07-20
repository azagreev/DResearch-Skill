"""Phase 6 — numeric-consistency audit (H6, hyperresearch reuse).

Flags numbers a claim asserts that are NOT traceable to a cited source: a claim
number is "supported" if its digit sequence appears in a cited source (optionally
within the cited line span). Read-only, warning-level audit surfaced by the
`engine numcheck` verb; NOT wired into rendering, so the report is always
byte-identical. Pure, deterministic, offline, stdlib-only. Python >= 3.10.

The digit-sequence comparison is intentionally lenient (ignores decimal-point
placement and thousands separators) so that "30 000" / "30000" match and only a
genuinely absent number is flagged — a warning, never a hard block.
"""

from __future__ import annotations

import re
from typing import Dict, List

from . import ingest
from .model import Claim, Snapshot, Source, _is_citation_span

# A number token: a digit run that may carry internal thousands/decimal
# separators (space, NBSP, thin space, comma, dot).
_NUM_RE = re.compile(r"\d[\d.,\u00a0\u202f\u2009 ]*\d|\d")

# Single-digit numbers ("3 causes", "top 5") trace by chance and generate noise,
# so only numbers with >= this many significant digits are checked. H7 may override.
MIN_DIGITS = 2


def _digit_key(token: str) -> str:
    """Comparison key: just the digits (separators/decimal point dropped)."""
    return re.sub(r"\D", "", token)


def _number_tokens(text: str) -> List[str]:
    """Number tokens in `text` with >= MIN_DIGITS significant digits, in text
    order (deterministic). Surrounding whitespace stripped from each token."""
    out: List[str] = []
    for m in _NUM_RE.finditer(text):
        tok = m.group().strip()
        if len(_digit_key(tok)) >= MIN_DIGITS:
            out.append(tok)
    return out


def _span_text(source: Source, span: List[int]) -> str:
    """Content of `source` within the 1-indexed [a, b] line span, clamped."""
    lines = ingest.content_lines(source)
    n = max(len(lines), 1)
    a = min(max(span[0], 1), n)
    b = min(max(span[1], 1), n)
    if a > b:
        a, b = b, a
    return "\n".join(lines[a - 1:b])


def _source_keys(source: Source, span) -> set:
    """Digit keys present in the source — within the span if one is given and
    well-formed, else across the whole content."""
    if _is_citation_span(span):
        text = _span_text(source, span)
    else:
        text = "\n".join(ingest.content_lines(source))
    return {_digit_key(t) for t in _number_tokens(text)}


def check_claim(claim: Claim, sources_by_id: Dict[str, Source]) -> List[str]:
    """Return the claim's number tokens not traceable to any cited source (at the
    cited span, if any). Empty for claims with no cited sources or no numbers —
    numeric-consistency is scoped to sourced, number-bearing claims."""
    if not claim.sources:
        return []
    numbers = _number_tokens(claim.text)
    if not numbers:
        return []
    spans = getattr(claim, "citation_spans", None) or {}
    keys: set = set()
    for sid in claim.sources:
        source = sources_by_id.get(sid)
        if source is None:
            continue
        keys |= _source_keys(source, spans.get(sid))
    return [tok for tok in numbers if _digit_key(tok) not in keys]


# Public seam: other engine modules (e.g. reconcile.py, H9) reuse the number
# tokenizer and digit-key without depending on a private underscore name.
number_tokens = _number_tokens
digit_key = _digit_key


def check_snapshot(snapshot: Snapshot) -> Dict[str, List[str]]:
    """{claim_id: [untraceable number tokens]} for every claim with >= 1
    untraceable number. Empty dict when everything traces."""
    sources_by_id = {s.id: s for s in snapshot.sources}
    issues: Dict[str, List[str]] = {}
    for claim in snapshot.claims:
        bad = check_claim(claim, sources_by_id)
        if bad:
            issues[claim.id] = bad
    return issues
