"""Phase 6 — mechanical quote-integrity gate (H1, hyperresearch reuse).

Verifies that every verbatim quote a claim carries (text inside «»/""/"" quote
delimiters) actually appears in a cited source's content AT the cited line span.
A fabricated or misattributed quote is a QUOTE_MISMATCH.

Scoped deliberately to claims that carry `citation_spans` (the R2
verifiable-citation opt-in): a claim without spans is never checked, so legacy
reports stay byte-identical and the golden corpus is untouched. Pure,
deterministic, offline, stdlib-only. Python >= 3.10.

The gate never echoes an unverified quote into the report (report.py surfaces the
claim id only) — hallucinated text must not be propagated even in a warning.
"""

from __future__ import annotations

import re
from typing import Dict, List

from . import ingest
from .model import Claim, Snapshot, Source, _is_citation_span

# Quotes shorter than this (in words) are NOT integrity-checked: 1-3 word spans
# match too readily by chance and would produce noise. The R2 "<=10 words
# verbatim" rule bounds the upper end; this bounds the lower. H7 may override.
MIN_QUOTE_WORDS = 4

# Ordered quote-delimiter patterns. Each captures the quoted inner text in
# group 1. Guillemets, curly doubles, German low-high, and straight ASCII.
_QUOTE_PATTERNS = (
    re.compile(r"«([^«»]+)»"),
    re.compile(r"“([^“”]+)”"),
    re.compile(r"„([^„“”]+)[“”]"),
    re.compile(r'"([^"]+)"'),
)


def _norm(text: str) -> str:
    """Whitespace-normalized form for verbatim comparison: runs of any
    whitespace collapse to a single space, leading/trailing stripped. Case is
    preserved (a verbatim quote must match case)."""
    return " ".join(text.split())


def extract_quoted_spans(text: str) -> List[str]:
    """Return the verbatim quoted substrings in `text` (>= MIN_QUOTE_WORDS
    words). Deterministic: pattern order fixed, matches in text order per
    pattern. Delimiters themselves are excluded from the returned span."""
    out: List[str] = []
    for rx in _QUOTE_PATTERNS:
        for m in rx.finditer(text):
            quote = m.group(1).strip()
            if quote and len(quote.split()) >= MIN_QUOTE_WORDS:
                out.append(quote)
    return out


def _span_text(source: Source, span: List[int]) -> str:
    """Concatenated content of `source` within the 1-indexed [a, b] line span,
    clamped into the source's actual content bounds (mirrors report.py clamp)."""
    lines = ingest.content_lines(source)
    n = max(len(lines), 1)
    a = min(max(span[0], 1), n)
    b = min(max(span[1], 1), n)
    if a > b:
        a, b = b, a
    return "\n".join(lines[a - 1:b])


def check_claim(claim: Claim, sources_by_id: Dict[str, Source]) -> List[str]:
    """Return the claim's verbatim quotes NOT supported by any cited source at
    its cited span. Empty list = clean (and always empty for a claim with no
    citation_spans, i.e. legacy claims are never flagged)."""
    spans = getattr(claim, "citation_spans", None)
    if not spans:
        return []
    quotes = extract_quoted_spans(claim.text)
    if not quotes:
        return []
    # Candidate haystacks: the spanned content of every cited source that has a
    # well-formed span. A quote is supported if it appears (whitespace-normalized)
    # in ANY of them.
    haystacks: List[str] = []
    for sid in claim.sources:
        span = spans.get(sid)
        source = sources_by_id.get(sid)
        if source is None or not _is_citation_span(span):
            continue
        haystacks.append(_norm(_span_text(source, span)))
    unsupported: List[str] = []
    seen: set = set()
    for quote in quotes:
        needle = _norm(quote)
        if needle in seen:
            continue  # dedupe nested/overlapping delimiter matches (order-stable)
        seen.add(needle)
        if not any(needle in hay for hay in haystacks):
            unsupported.append(quote)
    return unsupported


def check_snapshot(snapshot: Snapshot) -> Dict[str, List[str]]:
    """{claim_id: [unsupported quotes]} for every claim with >= 1 unsupported
    verbatim quote. Empty dict when nothing fails (the common case) — callers
    key byte-identical output on that."""
    sources_by_id = {s.id: s for s in snapshot.sources}
    issues: Dict[str, List[str]] = {}
    for claim in snapshot.claims:
        bad = check_claim(claim, sources_by_id)
        if bad:
            issues[claim.id] = bad
    return issues
