"""policy_guard.py — PreToolUse blocking hook (exit 2 = block).

Minimal allow/deny policy guard.  Reads JSON from stdin:
  {
    "tool":    str,      # tool name
    "input":   dict,     # tool parameters (optional)
    ...
  }

Exits (FAIL OPEN — a blocking hook must never deny a tool due to its own
malfunction; only an explicit deny-list match blocks):
  0 — allow (approved, not in deny list, or bad stdin)
  2 — BLOCK: tool explicitly denied by policy

Policy:
  DENY_LIST — tools that must never be called (safety / cost / legal).
  All other tools are approved by default.
"""

from __future__ import annotations

import json
import sys

# Explicitly denied tools (edit this list to extend the policy).
DENY_LIST: frozenset[str] = frozenset({
    # Example: tools that should never be auto-called in the skill context.
    # "some_dangerous_tool",
})


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as exc:
        # Fail OPEN: malformed input must approve (exit 0), never block.
        print(json.dumps({"action": "approve", "reason": f"policy_guard: bad stdin, failing open: {exc}"}))
        return 0

    tool: str = str(payload.get("tool", ""))

    if tool in DENY_LIST:
        msg = f"Policy violation: tool {tool!r} is explicitly denied."
        print(json.dumps({"action": "block", "reason": msg}))
        return 2

    print(json.dumps({"action": "approve"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
