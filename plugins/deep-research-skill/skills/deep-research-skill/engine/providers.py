"""Phase 6 — optional paid web-search providers (Tier-4 escalation).

OFF by default. The cost-first model keeps native web_search as the free Tier-1;
these paid backends (Brave / Exa / Serper) are an explicit opt-in escalation,
gated behind BOTH an API key AND the DRESEARCH_PAID_SEARCH flag.

Config precedence: process env > project .env. The HTTP call is injectable
(`http=` param) so the selection/enablement logic is testable without network.
stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_ENABLE_FLAG = "DRESEARCH_PAID_SEARCH"
_TRUE = {"1", "true", "yes", "on"}

# backend -> the env var holding its key, in auto-selection priority order.
_BACKENDS = (
    ("brave", "BRAVE_API_KEY"),
    ("exa", "EXA_API_KEY"),
    ("serper", "SERPER_API_KEY"),
)


def parse_dotenv(text: str) -> Dict[str, str]:
    """Parse a .env body: KEY=VALUE per line, '#'-comments, surrounding quotes
    stripped, blank lines ignored.
    """
    out: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def load_config(environ: Optional[Dict[str, str]] = None, dotenv_text: Optional[str] = None) -> Dict[str, str]:
    """Merge config with precedence: process env wins over .env."""
    config: Dict[str, str] = {}
    if dotenv_text:
        config.update(parse_dotenv(dotenv_text))
    config.update(environ if environ is not None else os.environ)
    return config


def enabled_backends(config: Dict[str, str]) -> List[str]:
    """Backends whose API key is present, in priority order."""
    return [name for name, key in _BACKENDS if config.get(key)]


def is_enabled(config: Dict[str, str]) -> bool:
    """Paid search runs only with the opt-in flag AND at least one key (default OFF)."""
    flag = str(config.get(_ENABLE_FLAG, "")).strip().lower() in _TRUE
    return flag and bool(enabled_backends(config))


def select_backend(config: Dict[str, str], preference: str = "auto") -> Optional[str]:
    """Resolve which backend to use. 'auto' picks the highest-priority available
    one; a named preference is used only if its key is present; else None.
    """
    available = enabled_backends(config)
    if not available:
        return None
    if preference == "auto":
        return available[0]
    return preference if preference in available else None


def _build_request(backend: str, query: str, config: Dict[str, str], count: int) -> Tuple[str, Dict[str, str]]:
    if backend == "brave":
        url = "https://api.search.brave.com/res/v1/web/search?" + urlencode({"q": query, "count": count})
        return url, {"X-Subscription-Token": config["BRAVE_API_KEY"], "Accept": "application/json"}
    if backend == "exa":
        return "https://api.exa.ai/search", {"x-api-key": config["EXA_API_KEY"], "Content-Type": "application/json"}
    if backend == "serper":
        return "https://google.serper.dev/search", {"X-API-KEY": config["SERPER_API_KEY"], "Content-Type": "application/json"}
    raise ValueError(f"unknown backend: {backend}")


def _default_http(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:  # noqa: S310 - explicit https endpoints
        return json.loads(response.read().decode("utf-8"))


def web_search(
    query: str,
    config: Dict[str, str],
    backend: str = "auto",
    count: int = 5,
    http: Optional[Callable[[str, Dict[str, str]], Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Run a paid web search. Returns (items, meta).

    Returns ([], {"status": "disabled"}) unless paid search is enabled. `http` is
    an injectable fetcher (url, headers) -> parsed-json for testing; defaults to
    a urllib GET. Items are normalized to {id, url, title, snippet, backend}.
    """
    if not is_enabled(config):
        return [], {"status": "disabled"}
    chosen = select_backend(config, backend)
    if chosen is None:
        return [], {"status": "no_backend"}

    fetch = http or _default_http
    url, headers = _build_request(chosen, query, config, count)
    try:
        payload = fetch(url, headers)
    except Exception as exc:  # network/parse failure -> graceful empty
        return [], {"status": "error", "backend": chosen, "error": str(exc)}

    items = _normalize(chosen, payload)
    return items, {"status": "ok", "backend": chosen, "count": len(items)}


def _normalize(backend: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw: List[Dict[str, Any]] = []
    if backend == "brave":
        raw = payload.get("web", {}).get("results", []) or []
    elif backend == "exa":
        raw = payload.get("results", []) or []
    elif backend == "serper":
        raw = payload.get("organic", []) or []
    items: List[Dict[str, Any]] = []
    for index, entry in enumerate(raw):
        items.append(
            {
                "id": f"{backend[:1].upper()}{index + 1}",
                "url": entry.get("url") or entry.get("link") or "",
                "title": entry.get("title") or "",
                "snippet": entry.get("description") or entry.get("snippet") or entry.get("text") or "",
                "backend": backend,
            }
        )
    return items
