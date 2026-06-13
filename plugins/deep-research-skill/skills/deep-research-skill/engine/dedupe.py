"""Phase 2 — deterministic dedupe of collected sources.

URL canonicalization + near-duplicate text detection (char-n-gram + token
Jaccard), so the engine collapses duplicates reproducibly instead of leaving it
to the model's discretion. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .model import Source

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_HOST_PREFIXES = ("www.", "m.", "mobile.", "old.", "amp.")
_TRACKING_PREFIXES = ("utm_", "utm-")
_TRACKING_KEYS = frozenset({"gclid", "fbclid", "yclid", "mc_eid", "igshid", "ref", "ref_src"})


def normalize_url(url: str) -> str:
    """Canonical key for a URL: force https, drop a leading host prefix
    (www./m./...), strip a trailing slash, remove tracking params, sort the rest,
    drop the fragment. Two URLs that point to the same page get the same key.
    """
    if not url:
        return ""
    raw = url.strip()
    # Scheme-less input ("example.com/a") would otherwise land the host in the
    # path; give urlsplit a netloc to parse.
    if "://" not in raw and not raw.startswith("//"):
        raw = "//" + raw
    parts = urlsplit(raw)
    host = parts.netloc.lower()
    if host.endswith(":80"):
        host = host[:-3]
    elif host.endswith(":443"):
        host = host[:-4]
    for prefix in _HOST_PREFIXES:
        if host.startswith(prefix):
            host = host[len(prefix):]
            break
    path = parts.path.rstrip("/")
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING_PREFIXES) and k.lower() not in _TRACKING_KEYS
    ]
    query = urlencode(sorted(kept))
    return urlunsplit(("https", host, path, query, ""))


def normalize_text(text: str) -> str:
    """lower + strip punctuation + collapse whitespace."""
    stripped = _PUNCT_RE.sub(" ", (text or "").lower())
    return _WS_RE.sub(" ", stripped).strip()


def char_ngrams(text: str, n: int = 3) -> Set[str]:
    compact = normalize_text(text).replace(" ", "")
    if len(compact) < n:
        return {compact} if compact else set()
    return {compact[i:i + n] for i in range(len(compact) - n + 1)}


def tokens(text: str) -> Set[str]:
    return set(normalize_text(text).split())


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def text_similarity(a: str, b: str) -> float:
    """Blend of char-trigram and token Jaccard, each in [0, 1]."""
    return 0.5 * jaccard(char_ngrams(a), char_ngrams(b)) + 0.5 * jaccard(tokens(a), tokens(b))


def _source_text(source: Source) -> str:
    parts: List[str] = []
    if source.title:
        parts.append(source.title)
    if source.extract:
        # Skip sentinel/meta keys (e.g. "_fence" trust boundary) — they are
        # identical across all sources and would pollute similarity scoring.
        parts.extend(str(v) for k, v in source.extract.items() if not str(k).startswith("_"))
    if not parts:
        parts.append(source.url)
    return " ".join(p for p in parts if p)


def dedupe_sources(
    sources: List[Source], threshold: float = 0.85
) -> Tuple[List[Source], List[Tuple[str, str]]]:
    """Collapse duplicate sources. Returns (kept, merges) where `merges` is a
    list of (kept_id, dropped_id). Order-stable: the first occurrence is kept.

    Pass 1: exact normalized-URL match. Pass 2: near-duplicate text similarity
    >= `threshold` against already-kept sources.
    """
    kept: List[Source] = []
    merges: List[Tuple[str, str]] = []
    url_to_id: Dict[str, str] = {}
    kept_text: List[Tuple[str, Set[str], Set[str]]] = []  # (id, char_ngrams, tokens)

    for source in sources:
        nurl = normalize_url(source.url)
        if nurl and nurl in url_to_id:
            merges.append((url_to_id[nurl], source.id))
            continue

        text = _source_text(source)
        grams = char_ngrams(text)
        toks = tokens(text)
        duplicate_of = None
        for kid, kgrams, ktoks in kept_text:
            sim = 0.5 * jaccard(grams, kgrams) + 0.5 * jaccard(toks, ktoks)
            if sim >= threshold:
                duplicate_of = kid
                break
        if duplicate_of is not None:
            merges.append((duplicate_of, source.id))
            continue

        kept.append(source)
        if nurl:
            url_to_id[nurl] = source.id
        kept_text.append((source.id, grams, toks))

    return kept, merges
