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
}


def _cmd_doctor(_args: argparse.Namespace) -> int:
    """Print runtime diagnostics as JSON; exit 0 only if the engine is usable."""
    diag = runtime.diagnostics()
    print(json.dumps(diag, ensure_ascii=False, indent=2))
    return 0 if diag["python_ok"] else 1


def _emit(text: str) -> None:
    """Write UTF-8 to stdout regardless of the console code page (the report
    contains emoji/Cyrillic; a cp1251/cp866 console would otherwise crash)."""
    try:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    except (AttributeError, ValueError):
        sys.stdout.write(text + "\n")


def _read_input(path: Optional[str]) -> dict:
    if not path or path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as handle:
        return json.loads(handle.read())


def _report_mode(name: str):
    from .policy import ReportMode

    try:
        return ReportMode(name)
    except ValueError:
        return ReportMode.FINDINGS


def _cmd_report(args: argparse.Namespace) -> int:
    """Render a snapshot JSON (AGENT.MD §8.0 shape) to Markdown."""
    from . import report as report_mod
    from .model import snapshot_from_dict

    snapshot = snapshot_from_dict(_read_input(args.input))
    _emit(report_mod.render_markdown(snapshot, _report_mode(args.mode)))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """End-to-end: {task_frame, sources, claims, now, model_categories?} -> report."""
    from . import pipeline
    from . import report as report_mod
    from .model import ClaimCategory, _claim_from, _task_frame_from, snapshot_to_dict

    data = _read_input(args.input)
    task_frame = _task_frame_from(data["task_frame"])
    claims = [_claim_from(c) for c in data.get("claims", [])]
    model_categories = {k: ClaimCategory(v) for k, v in (data.get("model_categories") or {}).items()}
    snapshot, _merges = pipeline.run_pipeline(
        data.get("run_id", "run"),
        task_frame,
        data.get("sources", []),
        claims,
        data.get("now", ""),
        model_categories=model_categories,
    )
    if getattr(args, "out", None):
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(snapshot_to_dict(snapshot), handle, ensure_ascii=False, indent=2)
    _emit(report_mod.render_markdown(snapshot, _report_mode(args.mode)))
    return 0


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

    run = sub.add_parser("run", help="end-to-end: raw sources + claims JSON -> Markdown report")
    run.add_argument("-i", "--input", default="-", help="input JSON file (default: stdin)")
    run.add_argument("--mode", default="findings", help="report mode: findings|debunk|mixed")
    run.add_argument("--out", default=None, help="also write the resulting snapshot JSON here")
    run.set_defaults(func=_cmd_run)

    report = sub.add_parser("report", help="render a snapshot JSON to Markdown")
    report.add_argument("-i", "--input", default="-", help="snapshot JSON file (default: stdin)")
    report.add_argument("--mode", default="findings", help="report mode: findings|debunk|mixed")
    report.set_defaults(func=_cmd_report)

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
