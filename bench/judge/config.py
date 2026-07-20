"""Pinned judge configuration — the "judge must be pinned + independent" honesty
gap called out in bench/README.md.

`JudgeConfig` is a frozen, validated record of exactly which model/temperature/
prompt version produced a run's verdicts. It requires the three pinned fields
(model, temperature, prompt_hash) to be PRESENT (not merely truthy — temperature
0.0, the honest value, must not be rejected). It is stdlib-only and performs no
model/network calls; the agent/workflow layer builds one instance per run and
stamps `cfg.as_dict()` into `bench.judge.collate.build_verdicts(..., judge=...)`,
which already records it verbatim in the verdicts file's `judge` field.

Python >= 3.10.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Tuple

REQUIRED_FIELDS: Tuple[str, str, str] = ("model", "temperature", "prompt_hash")


@dataclass(frozen=True)
class JudgeConfig:
    """A pinned judge configuration: model + temperature + prompt_hash.

    `extra` carries any additional bookkeeping fields (e.g. a DRACO dataset
    ref or run timestamp) the caller wants recorded alongside the three
    pinned fields, without weakening what is required.
    """

    model: str
    temperature: float
    prompt_hash: str
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "JudgeConfig":
        """Validate and build a JudgeConfig from a plain mapping.

        Presence (and not-None), not truthiness, is what's checked — so
        ``temperature: 0`` (falsy but a perfectly valid, in fact the
        recommended honest, value) is accepted while an absent or
        explicit-None field is rejected.
        """
        missing = [
            name
            for name in REQUIRED_FIELDS
            if name not in mapping or mapping[name] is None
        ]
        if missing:
            raise ValueError(
                "JudgeConfig missing required field(s): " + ", ".join(missing)
            )
        extra = {k: v for k, v in mapping.items() if k not in REQUIRED_FIELDS}
        return cls(
            model=mapping["model"],
            temperature=mapping["temperature"],
            prompt_hash=mapping["prompt_hash"],
            extra=extra,
        )

    def as_dict(self) -> Dict[str, Any]:
        """Pinned fields first, then any extras — this is what gets recorded
        verbatim into a verdicts file's `judge` field."""
        out: Dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "prompt_hash": self.prompt_hash,
        }
        out.update(self.extra)
        return out


def prompt_hash_of(prompt_text: str) -> str:
    """Deterministic pin for a prompt's exact text (sha256 hex digest).

    Lets the agent layer compute `prompt_hash` reproducibly from
    `bench/judge/prompt_draco.txt` (or whatever prompt was actually sent)
    rather than hand-typing a version string.
    """
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
