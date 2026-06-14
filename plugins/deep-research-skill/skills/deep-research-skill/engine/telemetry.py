"""engine/telemetry.py — Gate cost tracking and run-trace for the deep-research engine.

Implemented in Phase 11 (AC11-4).  Pure / deterministic; stdlib only.
No system clock is called here — callers pass timestamps in.

Classes
-------
GateCostTracker
    Tracks spend per quality gate against a fractional budget allocation.
    Alert levels: WARNING (>= 75%), CRITICAL (>= 90%), EXHAUSTED (>= 100%).

RunTrace
    Append-only ordered log of engine events.  ts must be supplied by caller;
    as_list() returns JSON-serialisable dicts.
"""

from __future__ import annotations

import hashlib
from typing import Optional, Sequence


# ---------------------------------------------------------------------------
# Cache & cost helpers (Phase 13, AC13-1 / AC13-2)
# ---------------------------------------------------------------------------

def cache_hit_rate(read: Optional[int], write: Optional[int]) -> Optional[float]:
    """Fraction of cache traffic served from a read (prompt-cache hit rate).

    Returns ``read / (read + write)``.  Returns None when either operand is
    None (host did not report it) or when ``read + write == 0`` (no cache
    traffic — a rate would be undefined, not 0).  Pure / deterministic.
    """
    if read is None or write is None:
        return None
    denom = read + write
    if denom == 0:
        return None
    return read / denom


def bundle_hash(text: str) -> str:
    """sha256 hex digest of ``text`` encoded as UTF-8.

    Deterministic, pure.  Used to detect prompt/tool prefix drift between turns
    (a changed hash means the cacheable prefix moved and the cache was busted).
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_fragmentation(
    history: Sequence[Optional[int]],
    *,
    threshold: int = 3,
) -> Optional[str]:
    """Detect a run of zero cached_tokens at the END of ``history``.

    Parameters
    ----------
    history
        Per-turn ``cached_tokens`` values (ints, or None when the host did not
        report a turn).  Passed in by the caller — no clock is read.
    threshold
        How many trailing consecutive *exact* zeros constitute fragmentation.

    Returns
    -------
    "WARNING" when the last ``threshold`` entries are all exactly 0; otherwise
    None.  A None entry (unknown) breaks the zero-run — unknown is not the same
    as fragmented.  Fewer than ``threshold`` entries -> None.  Deterministic.
    """
    if threshold <= 0 or len(history) < threshold:
        return None
    tail = history[-threshold:]
    if all(value == 0 for value in tail):
        return "WARNING"
    return None


# ---------------------------------------------------------------------------
# GateCostTracker
# ---------------------------------------------------------------------------

class GateCostTracker:
    """Track spend per quality gate against a fractional budget allocation.

    Ported from AGENT.MD §3.4 (pseudocode).
    Implemented in engine/telemetry.py (Phase 11).
    """

    # Fractional allocation of total_budget_usd per gate (must sum to 1.0).
    BUDGET_ALLOCATION: dict[str, float] = {
        "gate_1_collection": 0.15,   # 15% of budget
        "gate_2_processing": 0.10,   # 10% of budget
        "gate_3_analysis":   0.25,   # 25% of budget
        "gate_4_synthesis":  0.20,   # 20% of budget
        "gate_5_final":      0.10,   # 10% of budget
        "factcheck_agent":   0.15,   # 15% of budget
        "contingency":       0.05,   # 5%  reserve
    }

    def __init__(self, total_budget_usd: float) -> None:
        self.total: float = total_budget_usd
        self.spent: dict[str, float] = {k: 0.0 for k in self.BUDGET_ALLOCATION}
        self.retries_cost: float = 0.0

    # ------------------------------------------------------------------
    # spend
    # ------------------------------------------------------------------

    def spend(self, gate: str, amount_usd: float) -> dict:
        """Record *amount_usd* against *gate* and return a status snapshot.

        Returns
        -------
        dict with keys:
            gate          – the gate name
            spent         – cumulative spend on this gate (rounded to 2 dp)
            allocated     – dollar amount allocated to this gate
            remaining     – allocated minus spent (may be negative on over-run)
            pct_used      – percentage of gate allocation consumed (1 dp)
            alert         – None | 'WARNING' | 'CRITICAL' | 'EXHAUSTED'
            total_spent   – cumulative spend across all gates
            total_remaining – total_budget minus total_spent
        """
        if gate not in self.BUDGET_ALLOCATION:
            raise KeyError(f"Unknown gate {gate!r}. Known gates: {list(self.BUDGET_ALLOCATION)}")

        self.spent[gate] += amount_usd

        allocated = self.total * self.BUDGET_ALLOCATION[gate]
        remaining = allocated - self.spent[gate]
        pct_used  = (self.spent[gate] / allocated * 100) if allocated > 0 else 0.0

        # Alert thresholds per FROZEN CONTRACT §AC11-4
        alert: Optional[str]
        if pct_used >= 100:
            alert = "EXHAUSTED"
        elif pct_used >= 90:
            alert = "CRITICAL"
        elif pct_used >= 75:
            alert = "WARNING"
        else:
            alert = None

        total_spent = sum(self.spent.values())

        return {
            "gate":            gate,
            "spent":           round(self.spent[gate], 2),
            "allocated":       round(allocated, 2),
            "remaining":       round(remaining, 2),
            "pct_used":        round(pct_used, 1),
            "alert":           alert,
            "total_spent":     round(total_spent, 2),
            "total_remaining": round(self.total - total_spent, 2),
        }

    # ------------------------------------------------------------------
    # log_gate_result
    # ------------------------------------------------------------------

    def log_gate_result(self, gate: str, status: str) -> str:
        """Return a formatted log line for *gate* at *status* without mutating state.

        Parameters
        ----------
        gate   – gate key (must be in BUDGET_ALLOCATION)
        status – e.g. 'PASS', 'FAIL', 'RETRY'

        Returns
        -------
        A single-line string suitable for appending to a gate log file.
        No timestamp is embedded (caller supplies one if needed); the line
        is deterministic given the current spend state.
        """
        if gate not in self.BUDGET_ALLOCATION:
            raise KeyError(f"Unknown gate {gate!r}. Known gates: {list(self.BUDGET_ALLOCATION)}")

        # Read-only snapshot — do NOT call spend(gate, 0) which would be
        # semantically misleading; compute directly.
        allocated = self.total * self.BUDGET_ALLOCATION[gate]
        gate_spent = self.spent[gate]
        pct_used   = (gate_spent / allocated * 100) if allocated > 0 else 0.0

        if pct_used >= 100:
            alert: Optional[str] = "EXHAUSTED"
        elif pct_used >= 90:
            alert = "CRITICAL"
        elif pct_used >= 75:
            alert = "WARNING"
        else:
            alert = None

        return (
            f"[GATE-COST] {gate}={status} | "
            f"${gate_spent:.2f}/${allocated:.2f} "
            f"({pct_used:.0f}%) | "
            f"alert={alert}"
        )


# ---------------------------------------------------------------------------
# RunTrace
# ---------------------------------------------------------------------------

class RunTrace:
    """Append-only ordered log of engine events.

    *ts* is always caller-supplied — this class never reads the system clock.
    ``as_list()`` returns a copy of the internal list, each element a plain
    dict that is JSON-serialisable (no custom objects).

    Usage
    -----
    >>> trace = RunTrace()
    >>> trace.append("search_complete", tool_hash="abc123", ts="2026-01-01T00:00:00Z")
    >>> trace.as_list()
    [{'event': 'search_complete', 'tool_hash': 'abc123', 'ts': '2026-01-01T00:00:00Z', ...}]
    """

    def __init__(self) -> None:
        self.events: list[dict] = []

    def append(
        self,
        event: str,
        *,
        tool_hash:  Optional[str] = None,
        source_ref: Optional[str] = None,
        claim_id:   Optional[str] = None,
        why_stopped: Optional[str] = None,
        ts:         Optional[str] = None,
        prompt_bundle_hash: Optional[str] = None,
        tool_bundle_hash:   Optional[str] = None,
        cache_read_tokens:  Optional[int] = None,
        cache_write_tokens: Optional[int] = None,
        cached_tokens:      Optional[int] = None,
    ) -> None:
        """Append an event record to the trace.

        Parameters
        ----------
        event       – human-readable event label (required)
        tool_hash   – optional hash of the tool call that produced the event
        source_ref  – optional reference to a source document
        claim_id    – optional claim identifier
        why_stopped – optional reason why the engine stopped at this point
        ts          – ISO-8601 timestamp string (caller-supplied; no default)
        prompt_bundle_hash – optional hash of the cacheable prompt prefix (drift)
        tool_bundle_hash   – optional hash of the cacheable tool-definition prefix
        cache_read_tokens  – optional prompt-cache read tokens this turn
        cache_write_tokens – optional prompt-cache write tokens this turn
        cached_tokens      – optional cached_tokens reported by the host this turn

        The cache/bundle fields are sparse: each is added to the record ONLY
        when not None, matching the existing optional-field pattern, so a host
        that does not report cache metrics leaves the record graceful.
        """
        record: dict = {"event": event}
        # Include optional fields only when supplied so as_list() stays sparse.
        if tool_hash  is not None: record["tool_hash"]   = tool_hash
        if source_ref is not None: record["source_ref"]  = source_ref
        if claim_id   is not None: record["claim_id"]    = claim_id
        if why_stopped is not None: record["why_stopped"] = why_stopped
        if ts         is not None: record["ts"]          = ts
        if prompt_bundle_hash is not None: record["prompt_bundle_hash"] = prompt_bundle_hash
        if tool_bundle_hash   is not None: record["tool_bundle_hash"]   = tool_bundle_hash
        if cache_read_tokens  is not None: record["cache_read_tokens"]  = cache_read_tokens
        if cache_write_tokens is not None: record["cache_write_tokens"] = cache_write_tokens
        if cached_tokens      is not None: record["cached_tokens"]      = cached_tokens
        self.events.append(record)

    def as_list(self) -> list[dict]:
        """Return a shallow copy of all event records as plain dicts."""
        return list(self.events)
