"""Trust / reproducibility metrics for the deep-research engine.

The DRACO benchmark (bench/draco.py) measures a report's outcome quality via a
$$$ LLM judge. This package measures what DRACO does NOT and what the skill is
actually FOR — determinism, anti-hallucination suppression, citation
completeness, checkpoint fidelity — **deterministically and at ~$0**, by running
the real engine over synthetic labeled fixtures (no LLM judge, no network).

See docs/SKILL_VALUE_AND_SIMPLIFICATION.md §(C).
stdlib-only at the bench layer; imports the engine package (located at import).
"""

from __future__ import annotations

__all__ = ["metrics"]
