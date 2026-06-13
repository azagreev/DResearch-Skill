"""budget_guard.py — PreToolUse blocking hook (exit 2 = block).

Reads JSON from stdin:
  {
    "tool":         str,           # tool name being called
    "spent_usd":    float,         # total USD spent so far in this session
    "limit_usd":    float,         # total session budget limit
    "est_cost_usd": float | null   # optional caller-supplied cost estimate
  }

Exits (FAIL OPEN — a blocking hook must never deny a tool due to its own
malfunction; only an explicit budget-exceeded condition blocks):
  0 — allow the tool call (incl. on bad stdin / non-numeric fields)
  2 — BLOCK: paid tool would exceed budget

Paid tools (from HOOK_MIDDLEWARE.md §6.2):
  firecrawl, browserbase, serper_api, captcha_solve, generate_video
"""

from __future__ import annotations

import json
import sys

# §6.2 cost estimates — base cost per call for paid tools only
COST_ESTIMATES: dict[str, float] = {
    "firecrawl":      0.001,
    "browserbase":    0.010,
    "serper_api":     0.001,
    "captcha_solve":  0.001,
    "generate_video": 0.050,
}

PAID_TOOLS = frozenset(COST_ESTIMATES)


def main() -> int:
    # Fail OPEN on any malformed input: bad JSON must approve (exit 0), never
    # block. A blocking hook that fails closed can lock a whole session.
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
    except Exception as exc:
        print(json.dumps({"action": "approve", "reason": f"budget_guard: bad stdin, failing open: {exc}"}))
        return 0

    tool: str = str(payload.get("tool", ""))

    # If the tool is not a paid tool, allow it immediately.
    if tool not in PAID_TOOLS:
        print(json.dumps({"action": "approve"}))
        return 0

    # Coerce the numeric budget fields; non-numeric -> fail open (approve).
    try:
        spent: float = float(payload.get("spent_usd", 0.0))
        limit: float = float(payload.get("limit_usd", 0.0))
        if payload.get("est_cost_usd") is not None:
            est: float = float(payload["est_cost_usd"])
        else:
            est = COST_ESTIMATES[tool]
    except (TypeError, ValueError):
        print(json.dumps({"action": "approve", "reason": "budget_guard: non-numeric budget fields, failing open"}))
        return 0

    # Block if spent + estimated cost >= limit.
    if spent + est >= limit:
        msg = (
            f"Budget exceeded: tool={tool!r} est=${est:.4f} "
            f"spent=${spent:.4f} limit=${limit:.4f}"
        )
        print(json.dumps({"action": "block", "reason": msg}))
        return 2

    print(json.dumps({"action": "approve", "estimated_cost_usd": est}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
