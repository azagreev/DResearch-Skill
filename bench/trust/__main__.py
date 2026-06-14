"""Print a deterministic trust scorecard for the built-in demo scenario.

    PYTHONPATH=. python -m bench.trust
"""

from __future__ import annotations

import json

from .metrics import demo_scenario, scorecard


def main() -> int:
    print(json.dumps(scorecard(demo_scenario()), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
