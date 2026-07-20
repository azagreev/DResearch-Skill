"""DRACO judge layer.

`prompt_draco.txt` — verbatim per-criterion grading prompt, transcribed from
DRACO's reference grading implementation (The-LLM-Data-Company/rubric, cited by
arXiv:2602.11685); full provenance in the file header. `collate.py` — pure, deterministic assembly of per-criterion
verdicts into a bench verdicts file. `parse.py` — pure, markdown-tolerant
parsing of a judge's raw text response into a verdict (extract-before-verdict;
`ok=False` on anything unparseable, routed to `unjudged` by `collate`).
`config.py` — a pinned, validated `JudgeConfig` (model + temperature +
prompt_hash) that the agent layer stamps into `collate.build_verdicts(...,
judge=...)`. The actual LLM judging happens in the agent/driver layer; nothing
in this package calls a model or the network (keeps the deterministic core
LLM-free — see bench/README.md's honesty ledger, "judge must be pinned +
independent").
"""

from __future__ import annotations

__all__ = ["collate", "parse", "config"]
