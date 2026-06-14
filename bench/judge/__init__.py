"""DRACO judge layer.

`prompt_draco.txt` — verbatim per-criterion grading prompt, transcribed from
DRACO's reference grading implementation (The-LLM-Data-Company/rubric, cited by
arXiv:2602.11685); full provenance in the file header. `collate.py` — pure, deterministic assembly of per-criterion
verdicts into a bench verdicts file. The actual LLM judging happens in the
agent/driver layer; nothing here calls a model (keeps the deterministic core
LLM-free).
"""

from __future__ import annotations

__all__ = ["collate"]
