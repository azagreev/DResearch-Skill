"""Phase 2 — recency scoring (a ranking signal).

This is distinct from the *resume staleness* in state.py: there the question is
"is a collected time-sensitive source too old to trust on resume?"; here it is
"how fresh is this source, as a [0,1] signal feeding the rank/score?".

`parse_iso` is the single ISO-8601 parser the engine uses (state.py imports it).
stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp or date (accepts a trailing 'Z'); a naive
    value is assumed UTC. Returns None if empty or unparseable.
    """
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def recency_score(
    published_at: Optional[str],
    now_utc: str,
    half_life_days: float = 30.0,
    default: float = 0.5,
) -> float:
    """Exponential-decay recency in [0, 1]: 1.0 at `now`, 0.5 at one half-life,
    approaching 0 for old items. `now_utc` is passed in (no system clock).

    Missing/unparseable `published_at` -> `default` (neutral). A future date
    (published_at after now) clamps to 1.0.
    """
    now = parse_iso(now_utc)
    published = parse_iso(published_at)
    if now is None or published is None:
        return default
    age_days = (now - published).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    if half_life_days <= 0:
        return 0.0
    return 2.0 ** (-age_days / half_life_days)
