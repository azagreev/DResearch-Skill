"""Phase 1 — checkpoint state & resume.

Enforces the AGENT.MD §8.0 resume invariants IN CODE (vs by instruction):
  - fingerprint guard: match -> resume from next_phase; mismatch -> fresh run dir
  - highest-NN checkpoint with NN-1 fallback on corruption
  - budget carry-forward (spent_usd / loads_used carried, never reset)
  - collected sources are READ-ONLY on resume (re-fetch = protocol violation)
  - staleness re-verify window per depth (Quick 24h / Standard 7d / Deep 14d)

Contract: docs/PHASE1_MODEL_STATE.md. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .freshness import parse_iso
from .model import (
    Budget,
    ClaimCategory,
    Depth,
    Snapshot,
    SubTaskStatus,
    TaskFrame,
    snapshot_from_dict,
    snapshot_to_dict,
)
from .plan import ready_set

# Staleness windows in hours, by depth (AGENT.MD §8.0).
STALENESS_WINDOW_HOURS: Dict[Depth, int] = {
    Depth.QUICK: 24,
    Depth.STANDARD: 24 * 7,
    Depth.DEEP: 24 * 14,
    Depth.EXHAUSTIVE: 24 * 14,
}

_CP_RE = re.compile(r"^cp_(\d+)_.*\.md$")
_JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


class ResumeMode(str, Enum):
    FRESH = "fresh"                    # no checkpoint, or fingerprint mismatch
    RESUME = "resume"                  # fingerprint match -> continue from next_phase
    RESUME_RESTALE = "resume_restale"  # match, but time_sensitive sources are stale


@dataclass
class ResumeDecision:
    mode: ResumeMode
    run_dir: Path                              # existing on resume, new on fresh
    snapshot: Optional[Snapshot] = None        # loaded state if RESUME*, else None
    stale_source_ids: List[str] = field(default_factory=list)  # only for RESUME_RESTALE
    reason: str = ""


# --------------------------------------------------------------------------- #
# Fingerprint
# --------------------------------------------------------------------------- #
def _norm(text: str) -> str:
    """lower + trim + collapse internal whitespace."""
    return " ".join(str(text).strip().lower().split())


def normalize_for_fingerprint(task_frame: TaskFrame) -> str:
    """Canonical string for fingerprinting: `question | route | depth | sorted(scope)`,
    each piece lower/trimmed/whitespace-collapsed. Pure, deterministic, no clock.
    `acceptance_criteria` is intentionally EXCLUDED — it is mutable refinement and
    must not change task identity.
    """
    scope = sorted(_norm(s) for s in task_frame.scope)
    return "|".join(
        [_norm(task_frame.question), _norm(task_frame.route.value), _norm(task_frame.depth.value), *scope]
    )


def compute_fingerprint(task_frame: TaskFrame) -> str:
    """sha1(normalize_for_fingerprint(task_frame)).hexdigest(). Pure."""
    return hashlib.sha1(normalize_for_fingerprint(task_frame).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Checkpoint I/O
# --------------------------------------------------------------------------- #
def load_checkpoint(path: Path) -> Snapshot:
    """Extract the leading ```json state block from a `cp_NN_*.md` and build a
    Snapshot via model.snapshot_from_dict. Raises if no block / invalid JSON /
    unsupported version.
    """
    text = Path(path).read_text(encoding="utf-8")
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError(f"no json state block in {path}")
    return snapshot_from_dict(json.loads(match.group(1)))


def find_latest_checkpoint(run_dir: Path) -> Optional[Path]:
    """Highest-NN `cp_NN_*.md` whose state block parses; falls back to the next
    lower NN if the top one is corrupt. Returns None if none are valid.
    """
    run_dir = Path(run_dir)
    if not run_dir.exists():
        return None
    candidates = []
    for entry in run_dir.iterdir():
        m = _CP_RE.match(entry.name)
        if m:
            candidates.append((int(m.group(1)), entry))
    for _, path in sorted(candidates, key=lambda t: t[0], reverse=True):
        try:
            load_checkpoint(path)
            return path
        except Exception:
            continue
    return None


def save_checkpoint(snapshot: Snapshot, run_dir: Path, stage: str) -> Path:
    """Atomically write `cp_NN_<stage>.md` with a leading ```json state block
    (write tmp + os.replace). NN = max existing + 1 (1-based). Returns the path.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for e in run_dir.iterdir() for m in [_CP_RE.match(e.name)] if m]
    nn = (max(nums) + 1) if nums else 1
    name = f"cp_{nn:02d}_{stage}.md"
    path = run_dir / name
    body = "```json\n" + json.dumps(snapshot_to_dict(snapshot), ensure_ascii=False, indent=2) + "\n```\n"
    tmp = run_dir / (name + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, path)
    return path


# --------------------------------------------------------------------------- #
# Resume invariants
# --------------------------------------------------------------------------- #
def carry_budget(previous: Budget, fresh: Budget) -> Budget:
    """Carry spent_usd / loads_used forward from `previous`; keep the limits
    (limit_usd / loads_cap) from `fresh`. Never resets spend. Pure.
    """
    return Budget(
        limit_usd=fresh.limit_usd,
        spent_usd=previous.spent_usd,
        loads_used=previous.loads_used,
        loads_cap=fresh.loads_cap,
    )


def stale_source_ids(snapshot: Snapshot, now_utc: str) -> List[str]:
    """Ids of `time_sensitive` sources whose `created_utc` is older than the
    depth window (STALENESS_WINDOW_HOURS). `now_utc` is passed in (ISO) — the
    engine reads no system clock. A time_sensitive source with a missing or
    unparseable `created_utc` is treated as stale (safer to re-verify). Pure.
    """
    now = parse_iso(now_utc)
    window_h = STALENESS_WINDOW_HOURS.get(snapshot.task_frame.depth)
    if now is None or window_h is None:
        return []
    stale: List[str] = []
    for src in snapshot.sources:
        if not src.time_sensitive:
            continue
        created = parse_iso(src.created_utc)
        if created is None:
            stale.append(src.id)
            continue
        age_hours = (now - created).total_seconds() / 3600.0
        if age_hours > window_h:
            stale.append(src.id)
    return stale


def resume_or_fresh(task_frame: TaskFrame, run_root: Path, now_utc: str) -> ResumeDecision:
    """Top-level decision the CLI `resume` command calls:
      1. compute fingerprint of task_frame
      2. look in run_root/run-<fingerprint>/ for the latest valid checkpoint
      3. match -> RESUME (or RESUME_RESTALE if stale_source_ids is non-empty)
      4. no match -> FRESH with a NEW run_dir (never clobbers an existing one)

    The run dir is keyed by the full fingerprint, so a different task always maps
    to a different dir and an existing checkpoint is never clobbered.
    """
    fingerprint = compute_fingerprint(task_frame)
    run_dir = Path(run_root) / f"run-{fingerprint}"
    checkpoint = find_latest_checkpoint(run_dir)
    if checkpoint is not None:
        snapshot = load_checkpoint(checkpoint)
        if snapshot.task_fingerprint == fingerprint:
            stale = stale_source_ids(snapshot, now_utc)
            if stale:
                return ResumeDecision(
                    ResumeMode.RESUME_RESTALE, run_dir, snapshot, stale,
                    f"resume {snapshot.run_id} from phase {snapshot.next_phase}; "
                    f"{len(stale)} stale time-sensitive source(s) to re-verify",
                )
            return ResumeDecision(
                ResumeMode.RESUME, run_dir, snapshot, [],
                f"resume {snapshot.run_id} from phase {snapshot.next_phase}",
            )
        # Stored fingerprint disagrees with the dir key (hash collision): do not
        # clobber it — start fresh in a sibling dir.
        run_dir = Path(run_root) / f"run-{fingerprint}-new"
    return ResumeDecision(ResumeMode.FRESH, run_dir, None, [], "fresh run (no matching checkpoint)")


# --------------------------------------------------------------------------- #
# Gate enforcement
# --------------------------------------------------------------------------- #
def gate_blocks_transition(snapshot: Snapshot, target_phase: int) -> Optional[str]:
    """Return a reason string if transitioning to `target_phase` is blocked by
    a gate signal on `snapshot`, or None if the transition is allowed.

    Rules (AGENT.MD §3.1 gates):
      - target_phase >= 5 (synthesis / output) requires citations_verified True.
      - target_phase >= 2 (processing) requires sources_screened > 0.

    Pure function: no I/O, no side effects, deterministic.
    """
    if target_phase >= 2 and snapshot.sources_screened <= 0:
        return (
            f"gate blocked: target_phase {target_phase} requires sources_screened > 0, "
            f"got {snapshot.sources_screened}"
        )
    if target_phase >= 5 and not snapshot.citations_verified:
        return (
            f"gate blocked: target_phase {target_phase} requires citations_verified True, "
            f"but citations_verified is False"
        )
    return None


def assert_sources_readonly(before: Snapshot, after: Snapshot) -> List[str]:
    """In-code enforcement of the §8.0 read-only rule: a resumed run must not
    mutate already-collected source payloads. Returns the ids whose
    url / raw_path / extract changed (empty list = invariant held). New sources
    in `after` (no matching id in `before`) are not mutations and are ignored. Pure.
    """
    before_map = {s.id: s for s in before.sources}
    changed: List[str] = []
    for src in after.sources:
        prior = before_map.get(src.id)
        if prior is None:
            continue
        if src.url != prior.url or src.raw_path != prior.raw_path or src.extract != prior.extract:
            changed.append(src.id)
    return changed


# --------------------------------------------------------------------------- #
# Stop-condition oracle
# --------------------------------------------------------------------------- #
def should_stop(snapshot: Snapshot) -> Optional[str]:
    """Return a reason string when the run should stop, else None.  Pure, no I/O.

    Rules (checked in priority order):
      1. budget_exhausted  — budget.spent_usd >= budget.limit_usd > 0.
      2. done_condition_met — task_frame.done_condition is set AND
                              snapshot.citations_verified AND snapshot.next_phase >= 5.
      3. stalled_uncertainty — no PENDING subtask is STRICT-ready (via plan.ready_set)
                               AND at least one claim has category UNVERIFIED.
    """
    b = snapshot.budget
    if b.limit_usd > 0 and b.spent_usd >= b.limit_usd:
        return "budget_exhausted"

    if (
        snapshot.task_frame.done_condition is not None
        and snapshot.citations_verified
        and snapshot.next_phase >= 5
    ):
        return "done_condition_met"

    has_unverified = any(
        c.category == ClaimCategory.UNVERIFIED for c in snapshot.claims
    )
    if has_unverified:
        # ready_set returns PENDING subtask ids whose every STRICT predecessor is DONE.
        pending_ready = ready_set(snapshot.subtasks)
        if not pending_ready:
            return "stalled_uncertainty"

    return None
