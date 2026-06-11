"""CLI — the seam between the prose contract (SKILL.md) and the engine.

All subcommands speak JSON: input from --input file or stdin, result to stdout
(UTF-8). `doctor`/`--version` are diagnostics; the rest drive the pipeline.
Roadmap: docs/REBUILD_PLAN.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__, runtime


# --------------------------------------------------------------------------- #
# I/O helpers
# --------------------------------------------------------------------------- #
def _emit(text: str) -> None:
    """Write UTF-8 to stdout regardless of the console code page (reports carry
    emoji/Cyrillic; a cp1251/cp866 console would otherwise crash)."""
    try:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    except (AttributeError, ValueError):
        sys.stdout.write(text + "\n")


def _emit_json(obj) -> None:
    _emit(json.dumps(obj, ensure_ascii=False, indent=2))


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


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def _cmd_doctor(_args: argparse.Namespace) -> int:
    diag = runtime.diagnostics()
    _emit_json(diag)
    return 0 if diag["python_ok"] else 1


def _cmd_ingest(args: argparse.Namespace) -> int:
    from .ingest import ingest_sources
    from .model import _jsonable

    data = _read_input(args.input)
    sources, merges = ingest_sources(
        data.get("sources", []),
        data.get("now", ""),
        start_index=data.get("start_index", 1),
        dedupe=data.get("dedupe", True),
    )
    _emit_json({"sources": [_jsonable(s) for s in sources], "merges": [list(m) for m in merges]})
    return 0


def _cmd_rank(args: argparse.Namespace) -> int:
    from .model import _source_from
    from .rank import rank_sources

    data = _read_input(args.input)
    sources = [_source_from(s) for s in data.get("sources", [])]
    ranked = rank_sources(sources, data.get("streams", {}), data.get("weights"), data.get("k", 60))
    _emit_json({"ranked": [{"id": s.id, "score": sc} for s, sc in ranked]})
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    from . import score
    from .model import _claim_from, _jsonable, _source_from

    data = _read_input(args.input)
    sources = [_source_from(s) for s in data.get("sources", [])]
    score.score_sources(sources, data.get("now"))
    out = {"sources": [_jsonable(s) for s in sources]}
    if "claims" in data:
        claims = [_claim_from(c) for c in data["claims"]]
        score.score_claims(claims, sources)
        out["claims"] = [_jsonable(c) for c in claims]
    _emit_json(out)
    return 0


def _cmd_factcheck(args: argparse.Namespace) -> int:
    from . import factcheck
    from .model import ClaimCategory, _claim_from, _jsonable, _source_from

    data = _read_input(args.input)
    sources = [_source_from(s) for s in data.get("sources", [])]
    claims = [_claim_from(c) for c in data.get("claims", [])]
    hints = {k: ClaimCategory(v) for k, v in (data.get("model_categories") or {}).items()}
    factcheck.factcheck_claims(claims, sources, data.get("now"), model_categories=hints)
    _emit_json({"claims": [_jsonable(c) for c in claims]})
    return 0


def _cmd_cluster(args: argparse.Namespace) -> int:
    from .cluster import cluster_claims
    from .model import _claim_from, _jsonable

    data = _read_input(args.input)
    claims = [_claim_from(c) for c in data.get("claims", [])]
    clusters = cluster_claims(claims, data.get("sim_threshold", 0.55), data.get("max_reps", 2))
    _emit_json({"clusters": [_jsonable(k) for k in clusters], "claims": [_jsonable(c) for c in claims]})
    return 0


def _cmd_memory(args: argparse.Namespace) -> int:
    from . import memory
    from .model import snapshot_from_dict

    conn = memory.connect(Path(args.db) if args.db else None)
    if args.op == "record":
        snapshot = snapshot_from_dict(_read_input(args.input))
        _emit_json(memory.record_run(conn, snapshot, args.now or ""))
    elif args.op == "search":
        _emit_json({"results": memory.search_claims(conn, args.query or "", args.limit)})
    else:  # stats
        _emit_json(memory.get_stats(conn))
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    from . import eval as ev

    data = _read_input(args.input)
    k = data.get("k", 5)
    out = {}
    ranked = data.get("ranked")
    if ranked is not None and data.get("relevant") is not None:
        out["precision_at_k"] = ev.precision_at_k(ranked, data["relevant"], k)
        out["recall_at_k"] = ev.recall_at_k(ranked, data["relevant"], k)
        out["source_coverage"] = ev.source_coverage(ranked, data["relevant"])
    if ranked is not None and data.get("grades") is not None:
        grades = {str(key): float(val) for key, val in data["grades"].items()}
        out["ndcg_at_k"] = ev.ndcg_at_k(ranked, grades, k)
    if data.get("baseline") is not None and data.get("candidate") is not None:
        out["jaccard"] = ev.jaccard(data["baseline"], data["candidate"])
        out["retention"] = ev.overlap_retention(data["baseline"], data["candidate"])
    _emit_json(out)
    return 0


def _cmd_checkpoint(args: argparse.Namespace) -> int:
    from .model import snapshot_from_dict
    from .state import save_checkpoint

    snapshot = snapshot_from_dict(_read_input(args.input))
    path = save_checkpoint(snapshot, Path(args.run_dir), args.stage)
    _emit_json({"checkpoint": str(path)})
    return 0


def _cmd_resume(args: argparse.Namespace) -> int:
    from .model import _task_frame_from, snapshot_to_dict
    from .state import resume_or_fresh

    task_frame = _task_frame_from(_read_input(args.input))
    decision = resume_or_fresh(task_frame, Path(args.run_root), args.now or "")
    out = {
        "mode": decision.mode.value,
        "run_dir": str(decision.run_dir),
        "stale_source_ids": decision.stale_source_ids,
        "reason": decision.reason,
    }
    if decision.snapshot is not None:
        out["snapshot"] = snapshot_to_dict(decision.snapshot)
    _emit_json(out)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from . import report as report_mod
    from .model import snapshot_from_dict

    snapshot = snapshot_from_dict(_read_input(args.input))
    _emit(report_mod.render_markdown(snapshot, _report_mode(args.mode)))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from . import pipeline
    from . import report as report_mod
    from .model import ClaimCategory, _claim_from, _task_frame_from, snapshot_to_dict

    data = _read_input(args.input)
    task_frame = _task_frame_from(data["task_frame"])
    claims = [_claim_from(c) for c in data.get("claims", [])]
    hints = {k: ClaimCategory(v) for k, v in (data.get("model_categories") or {}).items()}
    snapshot, _merges = pipeline.run_pipeline(
        data.get("run_id", "run"),
        task_frame,
        data.get("sources", []),
        claims,
        data.get("now", ""),
        model_categories=hints,
    )
    if getattr(args, "out", None):
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(snapshot_to_dict(snapshot), handle, ensure_ascii=False, indent=2)
    _emit(report_mod.render_markdown(snapshot, _report_mode(args.mode)))
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def _add_input(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-i", "--input", default="-", help="input JSON file (default: stdin)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="engine", description="Deep Research Skill engine.")
    parser.add_argument("--version", action="version", version=f"deep-research-engine {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("doctor", help="runtime diagnostics (JSON); exit 0 if usable").set_defaults(func=_cmd_doctor)

    run = sub.add_parser("run", help="end-to-end: raw sources + claims JSON -> Markdown report")
    _add_input(run)
    run.add_argument("--mode", default="findings", help="report mode: findings|debunk|mixed")
    run.add_argument("--out", default=None, help="also write the resulting snapshot JSON here")
    run.set_defaults(func=_cmd_run)

    report = sub.add_parser("report", help="snapshot JSON -> Markdown")
    _add_input(report)
    report.add_argument("--mode", default="findings", help="report mode: findings|debunk|mixed")
    report.set_defaults(func=_cmd_report)

    ingest = sub.add_parser("ingest", help="raw search dicts -> Source records (+ dedupe)")
    _add_input(ingest)
    ingest.set_defaults(func=_cmd_ingest)

    rank = sub.add_parser("rank", help="RRF fusion + authority tilt over sources")
    _add_input(rank)
    rank.set_defaults(func=_cmd_rank)

    score = sub.add_parser("score", help="composite authority -> tier (+ claim confidence)")
    _add_input(score)
    score.set_defaults(func=_cmd_score)

    factcheck = sub.add_parser("factcheck", help="claim<->source verdict (6 categories)")
    _add_input(factcheck)
    factcheck.set_defaults(func=_cmd_factcheck)

    cluster = sub.add_parser("cluster", help="group claims into evidence clusters (MMR reps)")
    _add_input(cluster)
    cluster.set_defaults(func=_cmd_cluster)

    memory = sub.add_parser("memory", help="cross-run SQLite store")
    _add_input(memory)
    memory.add_argument("--db", default=None, help="SQLite path (omit -> in-memory)")
    memory.add_argument("--op", choices=("record", "search", "stats"), default="stats")
    memory.add_argument("--query", default=None, help="search query (op=search)")
    memory.add_argument("--limit", type=int, default=10)
    memory.add_argument("--now", default=None)
    memory.set_defaults(func=_cmd_memory)

    eval_ = sub.add_parser("eval", help="precision@k / nDCG@k / jaccard / coverage")
    _add_input(eval_)
    eval_.set_defaults(func=_cmd_eval)

    checkpoint = sub.add_parser("checkpoint", help="serialize a snapshot to cp_NN_<stage>.md")
    _add_input(checkpoint)
    checkpoint.add_argument("--run-dir", required=True)
    checkpoint.add_argument("--stage", default="cp")
    checkpoint.set_defaults(func=_cmd_checkpoint)

    resume = sub.add_parser("resume", help="task_frame JSON -> resume decision")
    _add_input(resume)
    resume.add_argument("--run-root", required=True)
    resume.add_argument("--now", default=None)
    resume.set_defaults(func=_cmd_resume)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return func(args)
