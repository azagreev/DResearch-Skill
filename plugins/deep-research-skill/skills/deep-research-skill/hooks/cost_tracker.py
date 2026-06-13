"""cost_tracker.py — PostToolUse non-blocking hook (exit 0 always).

Reads JSON from stdin (Claude Code PostToolUse envelope):
  {
    "tool":          str,
    "input":         dict,
    "output":        str | dict | null,
    "latency_ms":    float | null,
    "session_id":    str | null,
    "spent_usd":     float | null,
    ...
  }

Appends a cost-line entry to the output JSON written to stdout and exits 0.
Failures are silently ignored (never return non-zero from a PostToolUse hook).

Output: JSON dict with a "cost_line" key appended to whatever was passed in.
"""

from __future__ import annotations

import json
import sys

# §6.2 base cost estimates (paid tools; free tools default to 0.0)
COST_ESTIMATES: dict[str, float] = {
    "firecrawl":      0.001,
    "browserbase":    0.010,
    "serper_api":     0.001,
    "captcha_solve":  0.001,
    "generate_video": 0.050,
}


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    tool: str = str(payload.get("tool", "unknown"))
    latency_ms = payload.get("latency_ms")
    session_id = payload.get("session_id", "")
    spent_usd = payload.get("spent_usd")

    # Estimate the cost of this call.
    est_cost: float = COST_ESTIMATES.get(tool, 0.0)

    cost_line: dict = {
        "tool": tool,
        "est_cost_usd": est_cost,
        "latency_ms": latency_ms,
        "session_id": session_id,
    }
    if spent_usd is not None:
        try:
            cost_line["new_total_usd"] = float(spent_usd) + est_cost
        except (TypeError, ValueError):
            pass

    out = dict(payload)
    out["cost_line"] = cost_line
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
