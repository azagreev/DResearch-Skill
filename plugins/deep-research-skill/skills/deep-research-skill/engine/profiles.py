"""Phase 0 — scale-as-config-profile (H7, hyperresearch reuse).

Scale knobs and quality-gate thresholds that used to live only as SKILL.md prose
(subtask counts per depth, max parallel fan-out, Tier-B+ ratio, freshness ratio,
source diversity, completeness index) become a single machine-readable
`Profile` dataclass with named built-ins by depth, `extends`-based overlay, and
golden-pinned defaults. The engine consumes at least one threshold from here
(plan.MAX_CONCURRENT), so scale is config, not a literal scattered across code.

Pure, deterministic, offline, stdlib-only. Values mirror SKILL.md exactly, so the
default profile is byte-compatible with the pre-H7 behavior. Python >= 3.10.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Profile:
    """A named bundle of scale knobs + gate thresholds. Frozen (value-equality,
    hashable, immutable) so a profile is a stable, comparable config object."""
    name: str = "standard"
    max_concurrent: int = 5           # plan.MAX_CONCURRENT (SKILL.md: max 5 concurrent)
    subtasks_min: int = 10            # SKILL.md depth table
    subtasks_max: int = 15
    tier_b_plus_ratio: float = 0.60   # Gate 1: >=60% Tier B+
    freshness_ratio: float = 0.60     # Gate 1: freshness >=60%
    source_diversity_min: int = 4     # Gate 1: diversity >=4 types
    completeness_index_min: int = 70  # Gate 5: CI >=70


# Depth-keyed built-ins. Subtask bounds mirror SKILL.md's depth table; the gate
# thresholds are depth-invariant (Gate 1/5 apply the same bar), so they inherit
# the dataclass defaults.
BUILTINS: Dict[str, Profile] = {
    "quick": Profile(name="quick", subtasks_min=5, subtasks_max=8),
    "standard": Profile(name="standard", subtasks_min=10, subtasks_max=15),
    "deep": Profile(name="deep", subtasks_min=20, subtasks_max=30),
    "exhaustive": Profile(name="exhaustive", subtasks_min=30, subtasks_max=50),
}

# The default scale profile the engine reads when no profile is selected. Pins the
# historical literals so pre-H7 behavior is unchanged.
DEFAULT = BUILTINS["standard"]


def _field_names() -> set:
    return {f.name for f in fields(Profile)}


def get_profile(name: str = "standard") -> Profile:
    """Built-in profile by name; unknown name -> DEFAULT (never raises)."""
    return BUILTINS.get(name, DEFAULT)


def from_mapping(data: Dict[str, Any], base: Optional[Profile] = None) -> Profile:
    """Build a Profile from a mapping. An optional `extends` (a built-in name or a
    nested mapping) selects the base; then known keys overlay it and UNKNOWN keys
    are ignored (forward-compat, mirroring hyperresearch config). `base` overrides
    the starting point when `extends` is absent. Deterministic."""
    if base is None:
        base = DEFAULT
    ext = data.get("extends")
    if ext is not None:
        # A string names a built-in; resolve via get_profile so an unknown
        # name falls back to DEFAULT (consistent with get_profile) instead of
        # raising KeyError out of the verb. A mapping recurses.
        base = get_profile(ext) if isinstance(ext, str) else from_mapping(ext)
    known = _field_names()
    kwargs = {k: v for k, v in data.items() if k in known and k != "extends"}
    return replace(base, **kwargs)
