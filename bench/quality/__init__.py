"""Quality metrics for the deep-research engine — BINEVAL-style report self-grader.

This package measures report quality via per-question LLM-as-judge evaluation,
mirroring the DRACO benchmark (bench/draco.py) but at per-criterion granularity
and without benchmarking overhead. Used as a DRACO proxy for rapid quality
assessment across research report suites.

See docs/SKILL_VALUE_AND_SIMPLIFICATION.md §(C).
stdlib-only at the bench layer; imports the engine package (located at import).
"""

from __future__ import annotations

__all__ = ["grader"]
