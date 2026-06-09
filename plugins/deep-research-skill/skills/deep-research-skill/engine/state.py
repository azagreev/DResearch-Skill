"""Phase 1 — checkpoint state & resume. SIGNATURES + CONTRACT, no logic yet.

Enforces the AGENT.MD §8.0 resume invariants IN CODE (vs by instruction):
  - fingerprint guard: match -> resume from next_phase; mismatch -> fresh run dir
  - highest-NN checkpoint with NN-1 fallback on corruption
  - budget carry-forward (spent_usd / loads_used carried, never reset)
  - collected sources are READ-ONLY on resume (re-fetch = protocol violation)
  - staleness re-verify window per depth (Quick 24h / Standard 7d / Deep 14d)

Contract: docs/PHASE1_MODEL_STATE.md. stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .model import Budget, Depth, Snapshot, TaskFrame

# Staleness windows in hours, by depth (AGENT.MD §8.0).
STALENESS_WINDOW_HOURS: Dict[Depth, int] = {
    Depth.QUICK: 24,
    Depth.STANDARD: 24 * 7,
    Depth.DEEP: 24 * 14,
    Depth.EXHAUSTIVE: 24 * 14,
}


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
def normalize_for_fingerprint(task_frame: TaskFrame) -> str:
    """Canonical string for fingerprinting: lower/trim/collapse-whitespace of
    `question | route | depth | sorted(scope)`. Pure, deterministic, no clock.
    """
    raise NotImplementedError("Phase 1: normalize_for_fingerprint")


def compute_fingerprint(task_frame: TaskFrame) -> str:
    """sha1(normalize_for_fingerprint(task_frame)).hexdigest(). Pure."""
    raise NotImplementedError("Phase 1: compute_fingerprint")


# --------------------------------------------------------------------------- #
# Checkpoint I/O
# --------------------------------------------------------------------------- #
def find_latest_checkpoint(run_dir: Path) -> Optional[Path]:
    """Highest-NN `cp_NN_*.md` whose state block parses; falls back to NN-1 if
    the top one is corrupt. Returns None if none are valid.
    """
    raise NotImplementedError("Phase 1: find_latest_checkpoint")


def load_checkpoint(path: Path) -> Snapshot:
    """Extract the leading ```json state block from a `cp_NN_*.md` and build a
    Snapshot via model.snapshot_from_dict.
    """
    raise NotImplementedError("Phase 1: load_checkpoint")


def save_checkpoint(snapshot: Snapshot, run_dir: Path, stage: str) -> Path:
    """Atomically write `cp_NN_<stage>.md` with a leading ```json state block
    (write tmp + os.replace). Returns the written path.
    """
    raise NotImplementedError("Phase 1: save_checkpoint")


# --------------------------------------------------------------------------- #
# Resume invariants
# --------------------------------------------------------------------------- #
def carry_budget(previous: Budget, fresh: Budget) -> Budget:
    """Carry spent_usd / loads_used forward from `previous`; keep limits from
    `fresh`. Never resets spend. Pure.
    """
    raise NotImplementedError("Phase 1: carry_budget")


def stale_source_ids(snapshot: Snapshot, now_utc: str) -> List[str]:
    """Ids of `time_sensitive` sources whose `created_utc` is older than the
    depth window (STALENESS_WINDOW_HOURS). `now_utc` is passed in (ISO) — the
    engine reads no system clock. Pure.
    """
    raise NotImplementedError("Phase 1: stale_source_ids")


def resume_or_fresh(task_frame: TaskFrame, run_root: Path, now_utc: str) -> ResumeDecision:
    """Top-level decision the CLI `resume` command calls:
      1. compute fingerprint of task_frame
      2. scan run_root for a checkpoint whose snapshot.task_fingerprint matches
      3. match -> RESUME (or RESUME_RESTALE if stale_source_ids is non-empty)
      4. no match -> FRESH with a NEW run_dir (never clobbers an existing one)
    """
    raise NotImplementedError("Phase 1: resume_or_fresh")


def assert_sources_readonly(before: Snapshot, after: Snapshot) -> List[str]:
    """In-code enforcement of the §8.0 read-only rule: a resumed run must not
    mutate already-collected source payloads. Returns the ids whose
    url / raw_path / extract changed (empty list = invariant held). Pure.
    """
    raise NotImplementedError("Phase 1: assert_sources_readonly")
