"""Collate per-criterion judge verdicts into a bench verdicts file.

Pure, deterministic, LLM-free — the actual judging (LLM calls) happens in the
agent/driver layer; this module only assembles results into the format
`bench/__main__.py` consumes:

    {"arm": ..., "verdicts": {task_id: {criterion_id: bool}}, "judge": {...}}

Graceful degradation (AC-B3/(D)): a criterion whose judge call FAILED (no parseable
verdict) is OMITTED from the verdicts map — so `bench.score` counts it in
`n_unjudged` rather than silently scoring it UNMET with no trace. Omitted ids are
also listed under `unjudged` for human audit (the scorer ignores that key).

stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping


def met_from_status(status: str) -> bool:
    """Map the judge's `criterion_status` string to a bool. MET → True."""
    return str(status).strip().upper() == "MET"


def build_verdicts(
    arm: str,
    task_id: str,
    results: List[Mapping[str, Any]],
    judge: Mapping[str, Any],
) -> Dict[str, Any]:
    """Assemble one arm's verdicts file from per-criterion judge results.

    Each result maps `criterion_id` plus EITHER `status` ("MET"/"UNMET", the raw
    judge field) or `met` (bool). A result with `ok` == False (judge failed /
    output unparseable) is treated as UNJUDGED: omitted from the verdicts map.
    """
    verdicts: Dict[str, bool] = {}
    unjudged: List[str] = []
    for r in results:
        cid = r["criterion_id"]
        if r.get("ok") is False:
            unjudged.append(cid)
        elif "met" in r:
            verdicts[cid] = bool(r["met"])
        elif "status" in r:
            verdicts[cid] = met_from_status(r["status"])
        else:
            unjudged.append(cid)
    return {
        "arm": arm,
        "verdicts": {task_id: verdicts},
        "judge": dict(judge),
        "unjudged": {task_id: unjudged},
    }


def write_verdicts(path: str, payload: Mapping[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
