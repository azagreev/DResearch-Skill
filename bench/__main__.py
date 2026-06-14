"""bench CLI — deterministic DRACO scoring from judge verdicts.

The non-deterministic part (running the skill on a task, then running an LLM
judge over each rubric criterion) happens in the orchestrator/agent layer. That
layer dumps a *verdicts file* per arm; this CLI turns verdicts into scores —
purely, repeatably, with no network or model calls.

Verdicts file (one per arm)::

    {
      "arm": "with_skill",
      "verdicts": {
        "<task_uuid>": {"<criterion_id>": true, "<criterion_id>": false, ...},
        ...
      }
    }

Usage::

    python -m bench score --tasks test.jsonl --verdicts with_skill.json
    python -m bench diff  --tasks test.jsonl --a no_skill.json --b with_skill.json

stdlib-only, deterministic. Python >= 3.10.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List

from .draco import Task, load_draco
from .score import TaskScore, aggregate, delta, score_task


def _load_verdicts(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if "verdicts" not in data:
        raise ValueError(f"{path}: missing 'verdicts' key")
    return data


def _score_arm(tasks: List[Task], run: Dict) -> List[TaskScore]:
    by_id = {t.id: t for t in tasks}
    verdicts = run["verdicts"]
    scores: List[TaskScore] = []
    for task_id, criterion_verdicts in verdicts.items():
        task = by_id.get(task_id)
        if task is None:
            print(f"warning: verdicts for unknown task {task_id!r} ignored", file=sys.stderr)
            continue
        scores.append(score_task(task, criterion_verdicts))
    return scores


def _cmd_score(args: argparse.Namespace) -> int:
    tasks = load_draco(args.tasks)
    run = _load_verdicts(args.verdicts)
    scores = _score_arm(tasks, run)
    summary = aggregate(scores, arm=run.get("arm", ""))
    json.dump(
        {"summary": summary.as_dict(), "tasks": [s.as_dict() for s in scores]},
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    tasks = load_draco(args.tasks)
    run_a = _load_verdicts(args.a)
    run_b = _load_verdicts(args.b)
    summary_a = aggregate(_score_arm(tasks, run_a), arm=run_a.get("arm", "A"))
    summary_b = aggregate(_score_arm(tasks, run_b), arm=run_b.get("arm", "B"))
    json.dump(
        {
            "delta": delta(summary_a, summary_b),
            "arm_a": summary_a.as_dict(),
            "arm_b": summary_b.as_dict(),
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bench", description="DRACO benchmark scoring")
    sub = parser.add_subparsers(dest="command", required=True)

    score = sub.add_parser("score", help="score one arm's verdicts against the rubrics")
    score.add_argument("--tasks", required=True, help="path to DRACO test.jsonl")
    score.add_argument("--verdicts", required=True, help="path to an arm's verdicts JSON")
    score.set_defaults(func=_cmd_score)

    diff = sub.add_parser("diff", help="A/B delta between two arms' verdicts")
    diff.add_argument("--tasks", required=True, help="path to DRACO test.jsonl")
    diff.add_argument("--a", required=True, help="arm A verdicts JSON (baseline)")
    diff.add_argument("--b", required=True, help="arm B verdicts JSON (treatment)")
    diff.set_defaults(func=_cmd_diff)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
