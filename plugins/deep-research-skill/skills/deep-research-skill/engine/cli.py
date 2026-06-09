"""CLI — the seam between the prose contract (SKILL.md) and the engine.

Phase 0: only `--version` and `doctor` are functional. Every pipeline
subcommand is registered as a stub that prints "planned in Phase N" and exits
2, so SKILL.md can reference the command surface now and have it light up
phase by phase without breaking. Roadmap: docs/REBUILD_PLAN.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Callable, Dict, Optional, Sequence, Tuple

from . import __version__, runtime

# subcommand -> (target phase, one-line purpose)
_PLANNED: Dict[str, Tuple[str, str]] = {
    "checkpoint": ("Phase 1", "serialize the run snapshot (AGENT.MD section 8.0)"),
    "resume":     ("Phase 1", "load a snapshot and resume from next_phase"),
    "ingest":     ("Phase 2", "normalize raw web_search results into Source records"),
    "rank":       ("Phase 2", "RRF fusion + authority weighting of sources"),
    "score":      ("Phase 3", "composite authority score -> tier + confidence 1-5"),
    "factcheck":  ("Phase 4", "claim<->source cross-reference, 6-category verdicts"),
    "memory":     ("Phase 5", "cross-run SQLite store (dedupe + retro)"),
    "eval":       ("Phase 5", "precision@k / nDCG@k / jaccard / coverage"),
    "report":     ("Phase 6", "render verified findings into output formats"),
}


def _cmd_doctor(_args: argparse.Namespace) -> int:
    """Print runtime diagnostics as JSON; exit 0 only if the engine is usable."""
    diag = runtime.diagnostics()
    print(json.dumps(diag, ensure_ascii=False, indent=2))
    return 0 if diag["python_ok"] else 1


def _make_stub(name: str) -> Callable[[argparse.Namespace], int]:
    def _stub(_args: argparse.Namespace) -> int:
        phase, purpose = _PLANNED[name]
        sys.stderr.write(
            f"engine {name}: not implemented yet - planned in {phase} ({purpose}).\n"
            "See docs/REBUILD_PLAN.md.\n"
        )
        return 2

    return _stub


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="engine",
        description="Deep Research Skill engine (Phase 0 skeleton).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"deep-research-engine {__version__}",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    doctor = sub.add_parser(
        "doctor",
        help="print runtime diagnostics (JSON); exit 0 if the engine is usable",
    )
    doctor.set_defaults(func=_cmd_doctor)

    for name, (phase, purpose) in _PLANNED.items():
        stub = sub.add_parser(name, help=f"[{phase}] {purpose}")
        stub.set_defaults(func=_make_stub(name))

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return func(args)
