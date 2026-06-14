"""DRACO benchmark harness for the deep-research skill.

Evaluation tooling that lives OUTSIDE engine/ on purpose: the grading loop calls
a non-deterministic LLM judge, which must never enter the deterministic,
stdlib-only engine. bench/ holds only the deterministic pieces — dataset
loading (bench.draco), rubric parsing, and the exact DRACO scoring formula
(bench.score). The judge orchestration (running the skill + judging criteria)
lives in the agent/workflow layer that imports this package.

Reference: https://huggingface.co/datasets/perplexity-ai/draco
stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

__all__ = ["draco", "score"]
