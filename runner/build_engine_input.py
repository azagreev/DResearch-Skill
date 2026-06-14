"""Build the `engine run` JSON input for arm B (with_skill).

The 1-task fidelity loop collects a source/claim set ONCE; both arms consume the
identical set (fair ablation). This turns the DRACO task + that shared set into
the exact JSON `python -m engine run --input <f>` expects, pinned to route B /
depth Standard / language "en" (so the engine renders an English report).

stdlib-only, deterministic. Python >= 3.10.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


def build_engine_input(
    task_id: str,
    problem: str,
    sources: List[Dict[str, Any]],
    claims: List[Dict[str, Any]],
    now: str,
    *,
    route: str = "B",
    depth: str = "Standard",
    language: str = "en",
) -> Dict[str, Any]:
    """Assemble the `engine run` input dict. `sources` are raw source dicts
    (url/title/snippet/tier?/scores?); `claims` are claim dicts
    ({id, text, sources, role?, category?, confidence?}); `now` is an ISO string."""
    return {
        "run_id": task_id,
        "task_frame": {
            "question": problem,
            "route": route,
            "depth": depth,
            "language": language,
        },
        "sources": list(sources),
        "claims": list(claims),
        "now": now,
    }


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
