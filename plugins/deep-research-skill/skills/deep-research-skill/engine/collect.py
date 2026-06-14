"""Phase 9 — collect: provider-native search results -> ingest-ready raw dicts.

Sits in front of ``ingest.source_from_raw``: takes the varying shapes returned by
different fetch providers (native web_search, jina reader/search, firecrawl, ...)
and normalizes each into a uniform, ingest-ready item dict. It snippet-caps long
text, dedupes against an in-session URL cache, and stamps provider risk class.

It deliberately does NOT stamp ``extract["_fence"]`` or ``trust`` — ``ingest``
owns those downstream. Carrying them here would duplicate (and risk diverging
from) the trust boundary ingest enforces.

stdlib-only, deterministic (no time/random). Python >= 3.10.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .dedupe import normalize_url

# Risk classification per provider. SAFE providers are server-side managed
# fetchers; ELEVATED ones execute less-sandboxed fetches (raw curl, remote
# browser) and warrant an escalation hint for the caller.
PROVIDER_RISK = {
    "native_web_search": "SAFE",
    "jina_reader": "SAFE",
    "jina_search": "SAFE",
    "firecrawl": "SAFE",
    "rss": "SAFE",
    "browserbase": "ELEVATED",
    "curl": "ELEVATED",
}

# Escalation class for ELEVATED providers.  "browser" means a remote headless
# browser (e.g. browserbase); "curl" means a raw HTTP fetch.  On rate_limited
# for a browser-class provider the orchestrator should also try a proxy.
PROVIDER_ESCALATION = {
    "browserbase": "browser",
    "curl": "curl",
}

# Providers we have an explicit shape mapping for.
_JINA_PROVIDERS = frozenset({"jina_reader", "jina_search"})

# ---------------------------------------------------------------------------
# RSS helper — pure stdlib, deterministic, namespace-tolerant
# ---------------------------------------------------------------------------

# Atom namespace prefix used in ElementTree tag strings.
_ATOM_NS = "http://www.w3.org/2005/Atom"


def _strip_ns(tag: str) -> str:
    """Return the local name of an ElementTree tag, stripping any namespace."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _text(el: ET.Element | None) -> str:
    """Safely get the text content of an ElementTree element."""
    if el is None:
        return ""
    return (el.text or "").strip()


def _parse_rss_xml(xml_text: str) -> list[dict]:
    """Parse an Atom or RSS 2.0 XML string into a list of entry dicts.

    Each dict contains: {url, title, snippet, published_at}.  Keys with no
    value are present but set to "".  Ordering is document order (deterministic).

    Tolerant of:
    * Atom (<feed>/<entry>) and RSS 2.0 (<rss>/<channel>/<item>) shapes.
    * Arbitrary namespace prefixes; only local tag names are matched.
    * Missing or partial entry fields — best-effort extraction.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    root_local = _strip_ns(root.tag)
    entries: list[ET.Element] = []

    if root_local == "feed":
        # Atom: <feed><entry>…</entry></feed>
        for child in root:
            if _strip_ns(child.tag) == "entry":
                entries.append(child)
    else:
        # RSS 2.0: <rss><channel><item>…</item></channel></rss>
        # Root may be <rss> or directly <channel>.
        channels = [child for child in root if _strip_ns(child.tag) == "channel"]
        if not channels:
            # Root itself might be <channel>
            channels = [root] if root_local == "channel" else []
        for channel in channels:
            for child in channel:
                if _strip_ns(child.tag) == "item":
                    entries.append(child)

    results: list[dict] = []
    for entry in entries:
        # Build a {local_tag: element} index for the direct children.
        children: dict[str, ET.Element] = {}
        for child in entry:
            local = _strip_ns(child.tag)
            if local not in children:  # keep first occurrence
                children[local] = child

        # URL: Atom uses <link href="…"/> or <link>url</link>; RSS uses <link>.
        url = ""
        link_el = children.get("link")
        if link_el is not None:
            href = link_el.get("href", "")
            url = href if href else _text(link_el)

        title = _text(children.get("title"))

        # Snippet: prefer summary > description > content
        snippet = (
            _text(children.get("summary"))
            or _text(children.get("description"))
            or _text(children.get("content"))
        )

        # Publication date: Atom uses <published> or <updated>; RSS uses <pubDate>.
        published_at = (
            _text(children.get("published"))
            or _text(children.get("updated"))
            or _text(children.get("pubDate"))
        )

        results.append(
            {
                "url": url,
                "title": title,
                "snippet": snippet,
                "published_at": published_at,
            }
        )

    return results


@dataclass
class CollectionResult:
    status: str                       # "ok" | "partial" | "error" | "rate_limited" | "disabled"
    summary: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    next_valid_actions: List[str] = field(default_factory=list)
    error: Optional[Dict[str, Any]] = None


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def _cap(text: str, cap: int) -> tuple[str, bool]:
    """Truncate ``text`` to ``cap`` chars. Returns (text, truncated?)."""
    if cap is not None and cap >= 0 and len(text) > cap:
        return text[:cap], True
    return text, False


def _extract_fields(provider: str, raw: Dict[str, Any]) -> tuple[str, str, str]:
    """Pull (url, title, snippet) from one provider-native result dict.

    Tolerant of missing keys across the supported shapes:
      native web_search: {url|link, title, snippet|description|text}
      jina:              {url, title, content|text}
      firecrawl:         {url, markdown|content, metadata{title?}}
    """
    url = _as_str(raw.get("url") or raw.get("link"))
    title = _as_str(raw.get("title"))
    meta = raw.get("metadata")
    if not title and isinstance(meta, dict):
        title = _as_str(meta.get("title"))

    if provider == "firecrawl":
        snippet = _as_str(raw.get("markdown") or raw.get("content") or raw.get("text"))
    elif provider in _JINA_PROVIDERS:
        snippet = _as_str(raw.get("content") or raw.get("text") or raw.get("snippet"))
    elif provider == "native_web_search":
        snippet = _as_str(raw.get("snippet") or raw.get("description") or raw.get("text"))
    elif provider == "rss":
        snippet = _as_str(
            raw.get("snippet")
            or raw.get("summary")
            or raw.get("description")
            or raw.get("content")
            or raw.get("text")
        )
    else:
        # Generic best-effort: union of known body keys.
        snippet = _as_str(
            raw.get("snippet")
            or raw.get("description")
            or raw.get("content")
            or raw.get("markdown")
            or raw.get("text")
        )
    return url, title, snippet


def _build_item(provider: str, raw: Dict[str, Any], risk: str, snippet_cap: int) -> tuple[Dict[str, Any], bool]:
    """Map one raw result to an ingest-ready item. Returns (item, capped?)."""
    url, title, snippet = _extract_fields(provider, raw)
    snippet, snip_trunc = _cap(snippet, snippet_cap)

    # Preserve any caller-supplied metadata, then stamp our fields. Cap long
    # string values so a fat provider metadata field (e.g. firecrawl
    # description) can't smuggle a full body into the item past snippet_cap.
    raw_meta = raw.get("metadata")
    metadata: Dict[str, Any] = {}
    meta_capped = False
    if isinstance(raw_meta, dict):
        for k, v in raw_meta.items():
            if isinstance(v, str):
                metadata[k], t = _cap(v, snippet_cap)
                meta_capped = meta_capped or t
            else:
                metadata[k] = v
    metadata["risk_class"] = risk
    metadata["snippet_truncated"] = snip_trunc

    item: Dict[str, Any] = {
        "url": url,
        "title": title,
        "snippet": snippet,
        "fetched_via": provider,
        "metadata": metadata,
    }

    # Carry through optional ingest-recognized fields when present, capping any
    # long extract text so full bodies never leak into items.
    extract_capped = False
    extract = raw.get("extract")
    if isinstance(extract, dict):
        new_extract: Dict[str, Any] = {}
        for k, v in extract.items():
            if isinstance(v, str):
                capped, t = _cap(v, snippet_cap)
                new_extract[k] = capped
                extract_capped = extract_capped or t
            else:
                new_extract[k] = v
        item["extract"] = new_extract

    # NOTE: `trust` is intentionally NOT carried through. Every collect provider
    # serves remote, attacker-influenceable content, so a collected source must
    # never arrive pre-marked trusted — ingest defaults it to UNTRUSTED and the
    # TRUSTED opt-in is reserved for non-collect (internal) sources.
    for key in ("tier", "published_at", "time_sensitive", "scores"):
        if key in raw and raw[key] is not None:
            item[key] = raw[key]

    return item, (snip_trunc or extract_capped or meta_capped)


def normalize(
    provider: str,
    raw_payload: Any,
    *,
    snippet_cap: int = 1000,
    seen_urls: Optional[set] = None,
) -> CollectionResult:
    """Normalize provider-native results into ingest-ready item dicts.

    ``raw_payload`` is normally a ``list`` of provider-native result dicts. Each
    is mapped to a uniform item dict that ``ingest.source_from_raw`` consumes.

    Control-signal trigger (testable, deterministic): pass a ``dict`` as
    ``raw_payload`` to signal a non-success outcome instead of a result list:
      * ``{"status": "disabled"}``     -> status "disabled" (mirrors
        ``providers.web_search`` meta), items=[].
      * ``{"status": "rate_limited"}`` (or an ``error`` mentioning "rate")
        -> status "rate_limited", items=[], with a backoff recovery action.
      * ``{"status": "error", ...}`` or ``{"error": ...}`` -> status "error",
        items=[], error={type,message}, with a concrete recovery action.

    Behavior on a list payload:
      * (AC9-2) Each snippet (and any long extract text) is truncated to
        ``snippet_cap`` chars; ``metadata["snippet_truncated"]`` flags truncation.
        Full bodies are never carried into items.
      * (AC9-3) When ``seen_urls`` is provided, items whose ``normalize_url(url)``
        is already present are skipped; their normalized form is added to
        ``seen_urls`` and the skip count is noted in ``summary``.
      * (AC9-4) ``metadata["risk_class"]`` and ``fetched_via`` are stamped per
        provider; ELEVATED providers add an escalation hint to
        ``next_valid_actions``.
      * (AC9-5) status is "ok" when nothing was skipped/capped, else "partial".

    Does NOT stamp ``extract["_fence"]`` or ``trust`` — ingest does that.
    """
    risk = PROVIDER_RISK.get(provider, "ELEVATED")
    escalation: List[str] = []
    if risk == "ELEVATED":
        escalation.append("escalate_to_firecrawl")

    # --- control-signal payloads (dict) ---------------------------------
    if isinstance(raw_payload, dict):
        return _control_result(provider, raw_payload, escalation)

    # --- RSS XML string: parse into list before normal processing --------
    if provider == "rss" and isinstance(raw_payload, str):
        raw_payload = _parse_rss_xml(raw_payload)

    # --- normal list payloads -------------------------------------------
    if raw_payload is None:
        items_in: List[Any] = []
    elif isinstance(raw_payload, list):
        items_in = raw_payload
    else:
        return CollectionResult(
            status="error",
            summary=f"unexpected payload type: {type(raw_payload).__name__}",
            items=[],
            next_valid_actions=["fix_caller_payload_shape", *escalation],
            error={
                "type": "bad_payload",
                "message": f"raw_payload must be a list or control dict, got {type(raw_payload).__name__}",
            },
        )

    items: List[Dict[str, Any]] = []
    skipped = 0
    capped = 0
    for raw in items_in:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        item, was_capped = _build_item(provider, raw, risk, snippet_cap)
        if seen_urls is not None:
            nurl = normalize_url(item["url"])
            if nurl and nurl in seen_urls:
                skipped += 1
                continue
            if nurl:
                seen_urls.add(nurl)
        if was_capped:
            capped += 1
        items.append(item)

    parts = [f"{len(items)} item{'s' if len(items) != 1 else ''}"]
    if skipped:
        parts.append(f"{skipped} duplicate{'s' if skipped != 1 else ''} skipped")
    if capped:
        parts.append(f"{capped} capped")
    summary = ", ".join(parts)

    next_actions: List[str] = []
    if items:
        next_actions.append("ingest_items")
    next_actions.extend(escalation)

    # Pagination signals: emit fetch_next_page when any item in the payload
    # carries a "cursor" field (explicit cursor token), and no_more_pages when
    # the caller receives an explicitly empty payload (items_in was empty).
    # These are additive; they do NOT appear for ordinary non-paginated calls.
    if isinstance(raw_payload, list):
        has_cursor = any(
            isinstance(r, dict) and r.get("cursor") for r in raw_payload
        )
        if has_cursor:
            next_actions.append("fetch_next_page")
        elif not items_in:
            # Empty payload signals the final (exhausted) page.
            next_actions.append("no_more_pages")

    # Enrichment hint (rss provider): RSS feeds carry dates but no relevance
    # scores, so suggest the caller enrich the top-N after ingest.
    if items and provider == "rss" and not any("scores" in it for it in items):
        next_actions.append("enrich_top_n")

    # Escalate to autonomous agent hint: when a cursor-paginated provider
    # returns results but further depth would require agent-level navigation.
    if items and isinstance(raw_payload, list) and any(
        isinstance(r, dict) and r.get("cursor") for r in raw_payload
    ):
        next_actions.append("escalate_to_agent")

    status = "partial" if (skipped or capped) else "ok"
    return CollectionResult(
        status=status,
        summary=summary,
        items=items,
        next_valid_actions=next_actions,
        error=None,
    )


def _control_result(
    provider: str, payload: Dict[str, Any], escalation: List[str]
) -> CollectionResult:
    """Build a CollectionResult for a non-success control-signal dict payload."""
    raw_status = _as_str(payload.get("status")).lower()
    err = payload.get("error")
    if isinstance(err, dict):
        err_msg = _as_str(err.get("message"))
        err_type = _as_str(err.get("type")) or "error"
    elif isinstance(err, str):
        err_msg = err
        err_type = "error"
    else:
        err_msg = ""
        err_type = "error"
    err_text = err_msg.lower()

    is_disabled = raw_status == "disabled"
    is_rate = raw_status == "rate_limited" or "rate" in raw_status or "rate" in err_text
    has_error = bool(err) or raw_status in ("error", "failed")

    if is_disabled:
        return CollectionResult(
            status="disabled",
            summary=f"{provider} disabled",
            items=[],
            next_valid_actions=["enable_provider"],
            error=None,
        )

    if is_rate:
        rate_actions: List[str] = ["retry_after_backoff"]
        # Browser-class ELEVATED providers additionally suggest a proxy retry.
        if PROVIDER_ESCALATION.get(provider) == "browser":
            rate_actions.append("retry_with_proxy")
        rate_actions.extend(escalation)
        return CollectionResult(
            status="rate_limited",
            summary=f"{provider} rate limited",
            items=[],
            next_valid_actions=rate_actions,
            error={"type": "rate_limited", "message": err_msg or f"{provider} rate limited"},
        )

    if has_error:
        return CollectionResult(
            status="error",
            summary=f"{provider} error",
            items=[],
            next_valid_actions=["retry_after_backoff", *escalation],
            error={"type": err_type, "message": err_msg or f"{provider} returned an error"},
        )

    # A dict with status ok/success but no list of items -> nothing collected.
    return CollectionResult(
        status="ok",
        summary="0 items",
        items=[],
        next_valid_actions=[*escalation],
        error=None,
    )
