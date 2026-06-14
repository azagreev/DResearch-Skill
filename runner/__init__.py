"""DRACO 1-task fidelity-loop runner helpers (deterministic input builders).

The live orchestration (collect once, run both arms, judge) is driven by the
agent layer; this package only holds the pure functions that turn a DRACO task
plus a shared collected source/claim set into engine inputs. stdlib-only.
"""

from __future__ import annotations

__all__ = ["build_engine_input"]
