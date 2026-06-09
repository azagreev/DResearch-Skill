"""Runtime detection for the graceful prose-only fallback (Phase 0).

The skill must keep working on hosts WITHOUT a usable Python runtime / code
execution (e.g. claude.ai with code execution disabled). So the engine ships a
`doctor` probe; SKILL.md uses its exit code to decide engine-mode vs
prose-only mode. Nothing here imports a third-party package.
"""

from __future__ import annotations

import platform
import sys
from typing import Any, Dict

from . import __version__ as ENGINE_VERSION

# Minimum Python the engine targets. PEP-604 unions / `list[...]` at class scope
# and modern dataclass features make 3.10 the safe floor.
MIN_PYTHON = (3, 10)


def python_ok() -> bool:
    """True if the interpreter meets the engine's minimum version."""
    return sys.version_info[:2] >= MIN_PYTHON


def diagnostics() -> Dict[str, Any]:
    """Machine-readable runtime report (consumed by `engine doctor`)."""
    return {
        "engine_version": ENGINE_VERSION,
        "python_version": platform.python_version(),
        "python_ok": python_ok(),
        "min_python": ".".join(str(p) for p in MIN_PYTHON),
        "platform": platform.system(),
        "executable": sys.executable,
    }
