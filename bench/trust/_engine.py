"""Locate and import the deep-research engine package from the bench layer.

The engine lives deep under plugins/…; bench/ is at the repo root. This module
puts the engine's parent dir on sys.path once, so `import engine` works, and
re-exports the symbols the trust metrics need.
"""

from __future__ import annotations

import os
import sys

_ENGINE_PARENT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..",
        "plugins", "deep-research-skill", "skills", "deep-research-skill",
    )
)
if _ENGINE_PARENT not in sys.path:
    sys.path.insert(0, _ENGINE_PARENT)

from engine import pipeline, report  # noqa: E402
from engine import eval as engine_eval  # noqa: E402
from engine.model import (  # noqa: E402
    Claim,
    ClaimRole,
    Depth,
    Route,
    TaskFrame,
    snapshot_from_dict,
    snapshot_to_dict,
)

__all__ = [
    "pipeline", "report", "engine_eval",
    "Claim", "ClaimRole", "Depth", "Route", "TaskFrame",
    "snapshot_from_dict", "snapshot_to_dict",
]
