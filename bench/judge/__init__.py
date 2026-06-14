"""DRACO judge layer.

`prompt_draco.txt` — verbatim official per-criterion grading prompt (provenance
in the file header). `collate.py` — pure, deterministic assembly of per-criterion
verdicts into a bench verdicts file. The actual LLM judging happens in the
agent/driver layer; nothing here calls a model (keeps the deterministic core
LLM-free).
"""

from __future__ import annotations

__all__ = ["collate"]
