"""bench.quality CLI — report quality self-grader.

Two subcommands:

``demo`` (default when no args given)
    Runs the built-in demo scenario through the full deterministic + stub-judge
    pipeline and prints the quality scorecard as JSON.  Byte-identical across
    runs (no randomness, no clock).

``grade --verdicts PATH``
    Loads a ``{question_id: bool}`` verdicts JSON file and prints the
    aggregated QualityScore dict.  Accepts an optional ``--report PATH`` for
    context/parity (not required to score).

Usage::

    python -m bench.quality
    python -m bench.quality demo
    python -m bench.quality grade --verdicts verdicts.json
    python -m bench.quality grade --verdicts verdicts.json --report report.md

stdlib-only, deterministic. Python >= 3.10.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List, Optional, Tuple

from .grader import grade, quality_scorecard
from .questions import BinaryQuestion, Polarity, QKind
from bench.trust.metrics import demo_scenario


# --------------------------------------------------------------------------- #
# Demo answer stub
# --------------------------------------------------------------------------- #
def demo_answer_fn(
    question: BinaryQuestion,
    context: Any,
) -> Tuple[Optional[bool], str]:
    """Deterministic stub judge for the demo subcommand.

    For every JUDGMENT question returns a "good report" answer:
    - POSITIVE polarity → (True,  "demo: assumed satisfied")
    - NEGATIVE polarity → (False, "demo: no error present")

    No randomness, no clock — byte-identical across runs.
    """
    if question.polarity is Polarity.POSITIVE:
        return (True, "demo: assumed satisfied")
    # NEGATIVE polarity: verdict False means the error is absent (good)
    return (False, "demo: no error present")


# --------------------------------------------------------------------------- #
# Subcommand handlers
# --------------------------------------------------------------------------- #
def _cmd_demo(args: argparse.Namespace) -> int:  # noqa: ARG001
    snapshot, _md = demo_scenario().run()
    scorecard = quality_scorecard(snapshot, demo_answer_fn)
    print(json.dumps(scorecard, indent=2, ensure_ascii=False))
    return 0


def _cmd_grade(args: argparse.Namespace) -> int:
    with open(args.verdicts, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        print(
            f"error: {args.verdicts}: expected a JSON object, got {type(raw).__name__}",
            file=sys.stderr,
        )
        return 1
    # Coerce values to bool (JSON true/false are already bool; guard strings)
    verdicts = {k: bool(v) for k, v in raw.items()}
    result = grade(verdicts)
    print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bench.quality",
        description="Report quality self-grader (BINEVAL-style, stdlib-only)",
    )
    sub = parser.add_subparsers(dest="command")

    # demo
    demo_p = sub.add_parser(
        "demo",
        help="run the built-in demo scenario and print the quality scorecard",
    )
    demo_p.set_defaults(func=_cmd_demo)

    # grade
    grade_p = sub.add_parser(
        "grade",
        help="aggregate a pre-computed verdicts JSON into a QualityScore",
    )
    grade_p.add_argument(
        "--verdicts",
        required=True,
        metavar="PATH",
        help="path to a JSON file mapping {question_id: bool}",
    )
    grade_p.add_argument(
        "--report",
        required=False,
        metavar="PATH",
        help="path to the report file (accepted for parity/context; not used for scoring)",
    )
    grade_p.set_defaults(func=_cmd_grade)

    return parser


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Default to 'demo' when no subcommand is given (mirrors bench/trust/__main__.py style)
    if args.command is None:
        return _cmd_demo(args)

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
