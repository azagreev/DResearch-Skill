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
    # AC15-6: surface the capability->verb reachability manifest alongside the
    # existing runtime diagnostics, so an operator can see at a glance whether
    # any curated capability lacks a CLI verb (reachable=False).
    diag["capabilities"] = _capability_manifest()
    _emit_json(diag)
    return 0 if diag["python_ok"] else 1


def _cmd_collect(args: argparse.Namespace) -> int:
    from .collect import normalize

    data = _read_input(args.input)
    seen_urls_raw = data.get("seen_urls")
    seen_urls = set(seen_urls_raw) if seen_urls_raw is not None else None
    result = normalize(
        data["provider"],
        data["raw_payload"],
        snippet_cap=data.get("snippet_cap", 1000),
        seen_urls=seen_urls,
    )
    _emit_json({
        "status": result.status,
        "summary": result.summary,
        "items": result.items,
        "next_valid_actions": result.next_valid_actions,
        "error": result.error,
    })
    return 0


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
    elif args.op == "record-feedback":
        # JSON-in: a single feedback record (or {"record": {...}}).
        data = _read_input(args.input)
        record = data.get("record", data)
        _emit_json(memory.record_feedback(conn, record, args.now or ""))
    elif args.op == "list-feedback":
        kind = getattr(args, "kind", None)
        run_id = getattr(args, "run_id", None)
        _emit_json({"feedback": memory.list_feedback(conn, kind=kind, run_id=run_id)})
    else:  # stats
        _emit_json(memory.get_stats(conn))
    return 0


def _cmd_rescore(args: argparse.Namespace) -> int:
    from . import report as report_mod
    from .model import ClaimCategory, snapshot_from_dict, snapshot_to_dict
    from .state import rescore_snapshot

    data = _read_input(args.input)
    snapshot = snapshot_from_dict(data["snapshot"])
    hints = {k: ClaimCategory(v) for k, v in (data.get("model_categories") or {}).items()}
    after, diff, changed = rescore_snapshot(
        snapshot,
        now_utc=data.get("now"),
        model_categories=hints,
        half_life_days=float(data.get("half_life_days", 30.0)),
        shallow=bool(getattr(args, "shallow", False)),
    )
    if changed:
        _emit_json({
            "error": "rescore mutated read-only source payload(s); aborting",
            "changed_ids": changed,
        })
        return 1

    out = {
        "snapshot": snapshot_to_dict(after),
        "diff": diff,
        "readonly_ok": True,
    }
    if getattr(args, "shallow", False):
        out["warning"] = (
            "shallow rescore: factcheck + clustering were skipped, so claim "
            "categories/verdicts may be stale relative to the new tiers"
        )
    if getattr(args, "out", None):
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(snapshot_to_dict(after), handle, ensure_ascii=False, indent=2)
    if getattr(args, "report", False):
        md = report_mod.render_markdown(after, _report_mode(args.mode))
        # Carry the shallow-staleness warning onto the Markdown path too, so it is
        # not silently dropped when --shallow is combined with --report.
        if out.get("warning"):
            md = f"> ⚠️ {out['warning']}\n\n{md}"
        _emit(md)
    else:
        _emit_json(out)
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


def _cmd_cost(args: argparse.Namespace) -> int:
    from .telemetry import GateCostTracker

    data = _read_input(args.input)
    tracker = GateCostTracker(float(data["total_budget"]))
    # Record each spend in order; keep the LAST snapshot per gate so the report
    # reflects cumulative state.  Track which gates are currently alerting.
    per_gate: dict = {}
    for entry in data.get("spends", []):
        snapshot = tracker.spend(entry["gate"], float(entry["amount"]))
        per_gate[entry["gate"]] = snapshot
    total_spent = round(sum(tracker.spent.values()), 2)
    alerts = [gate for gate, snap in per_gate.items() if snap["alert"] is not None]
    _emit_json({
        "per_gate": per_gate,
        "total_spent": total_spent,
        "total_remaining": round(tracker.total - total_spent, 2),
        "alerts": alerts,
    })
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


def _cmd_compact(args: argparse.Namespace) -> int:
    from .compact import build_handoff
    from .model import snapshot_from_dict

    snapshot = snapshot_from_dict(_read_input(args.input))
    _emit_json(build_handoff(snapshot))
    return 0


def _cmd_hook(args: argparse.Namespace) -> int:
    """Manage and test hook middleware scripts.

    --op list  — print all hooks registered in .claude/settings.json
    --op test  — run a single hook script on a fixture payload and report exit code
    --op fire  — alias for test (fire the hook with the given payload)
    """
    import subprocess

    op: str = args.op

    # The canonical hook config is an INERT, opt-in template shipped with the
    # skill: hooks/settings.example.json. We deliberately do NOT auto-read a live
    # repo-root .claude/settings.json — a live blocking hook in the dev repo is a
    # footgun (a mis-scoped "*"-matcher PreToolUse hook can lock the maintainer's
    # own session). Users opt in by copying the template to their own
    # .claude/settings.json (see README). --config overrides the source.
    skill_root = Path(__file__).resolve().parent.parent  # <skill_root>
    default_cfg = skill_root / "hooks" / "settings.example.json"
    cfg_arg = getattr(args, "config", None)
    settings_path = Path(cfg_arg) if cfg_arg else default_cfg

    if op == "list":
        if not settings_path.exists():
            _emit_json({"error": f"hook config not found: {settings_path}"})
            return 1
        try:
            with open(settings_path, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except Exception as exc:
            _emit_json({"error": f"cannot read settings.json: {exc}"})
            return 1
        hooks_cfg = cfg.get("hooks", {})
        result: dict = {}
        for event, entries in hooks_cfg.items():
            result[event] = []
            for entry in entries:
                for hook in entry.get("hooks", []):
                    result[event].append({
                        "matcher": entry.get("matcher", "*"),
                        "command": hook.get("command", ""),
                        "type": hook.get("type", "command"),
                    })
        _emit_json(result)
        return 0

    if op in ("test", "fire"):
        # --script selects which hook script to run; --payload supplies stdin JSON.
        script: Optional[str] = getattr(args, "script", None)
        payload_arg: Optional[str] = getattr(args, "payload", None)

        if not script:
            _emit_json({"error": "--script is required for --op test/fire"})
            return 1

        if payload_arg:
            # Accept either a JSON string or a file path.
            payload_path = Path(payload_arg)
            if payload_path.exists():
                stdin_text = payload_path.read_text(encoding="utf-8")
            else:
                stdin_text = payload_arg  # treat as raw JSON string
        else:
            stdin_text = sys.stdin.read()

        try:
            result_proc = subprocess.run(
                ["python", script],
                input=stdin_text,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            _emit_json({"error": f"cannot run script: {exc}"})
            return 1

        _emit_json({
            "script": script,
            "exit_code": result_proc.returncode,
            "stdout": result_proc.stdout,
            "stderr": result_proc.stderr,
            "blocked": result_proc.returncode == 2,
        })
        return 0

    _emit_json({"error": f"unknown --op: {op!r}"})
    return 1


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


def _cmd_verify(args: argparse.Namespace) -> int:
    """AC15-2 — independent re-verification of a snapshot's claims.

    JSON-in {snapshot, now?}. For each claim we re-derive its category from
    claim text + the snapshot's sources (verify.reverify_claim, which never
    reads claim.verdict_explanation) and flag disagreement with the recorded
    category. The input snapshot/claims are NOT mutated — reverify/disagreement
    are read-only on the claim.
    """
    from .model import snapshot_from_dict
    from .verify import reverify_claim

    data = _read_input(args.input)
    snapshot = snapshot_from_dict(data["snapshot"])
    now = data.get("now")
    results = []
    n_disagreements = 0
    for claim in snapshot.claims:
        # Re-derive once; `disagreement` is just `reverified != claim.category`,
        # so calling both helpers would re-run reverify_claim a second time.
        reverified = reverify_claim(claim, snapshot.sources, now)
        dis = reverified != claim.category
        if dis:
            n_disagreements += 1
        results.append({
            "claim_id": claim.id,
            "original_category": claim.category.value,
            "reverified_category": reverified.value,
            "disagreement": dis,
        })
    _emit_json({
        "results": results,
        "summary": {"n_claims": len(results), "n_disagreements": n_disagreements},
    })
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    """AC15-3 — validate + layer a sub-task DAG.

    JSON-in either {snapshot} (reads snapshot.subtasks) or {subtasks} (a list of
    subtask dicts). Reports validation errors; on a valid plan, the parallel
    layering, the STRICT-ready set, and MAX_CONCURRENT.
    """
    from .model import _subtask_from, snapshot_from_dict
    from .plan import MAX_CONCURRENT, ready_set, topo_order, validate_plan

    data = _read_input(args.input)
    if "snapshot" in data:
        subtasks = snapshot_from_dict(data["snapshot"]).subtasks
    else:
        subtasks = [_subtask_from(s) for s in data.get("subtasks", [])]

    errors = validate_plan(subtasks)
    if errors:
        _emit_json({"status": "invalid", "errors": errors})
        return 0
    _emit_json({
        "status": "valid",
        "errors": [],
        "layers": topo_order(subtasks),
        "ready": ready_set(subtasks),
        "max_concurrent": MAX_CONCURRENT,
    })
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    """AC15-4 — consult the three gate oracles for a snapshot.

    JSON-in {snapshot, target_phase?}. Emits whether a phase transition is
    blocked (state.gate_blocks_transition), whether the run should stop
    (state.should_stop), and whether a compaction boundary is due
    (compact.should_compact). target_phase defaults to snapshot.next_phase or 5.
    """
    from . import compact
    from .model import snapshot_from_dict
    from .state import gate_blocks_transition, should_stop

    data = _read_input(args.input)
    snapshot = snapshot_from_dict(data["snapshot"])
    target = data.get("target_phase", snapshot.next_phase or 5)
    _emit_json({
        "blocks_transition": gate_blocks_transition(snapshot, int(target)),
        "should_stop": should_stop(snapshot),
        "should_compact": compact.should_compact(snapshot),
    })
    return 0


# --------------------------------------------------------------------------- #
# Capability reachability manifest (AC15-6 / AC15-7)
# --------------------------------------------------------------------------- #
# Curated map of engine capability -> the CLI verb that makes it reachable.
# `doctor` and the reachability test both consult this single source of truth:
# a capability is reachable iff its verb is a registered subparser choice.
CAPABILITY_VERBS: dict = {
    "collect": "collect",
    "ingest": "ingest",
    "rank": "rank",
    "score": "score",
    "factcheck": "factcheck",
    "cluster": "cluster",
    "memory": "memory",
    "eval": "eval",
    "cost": "cost",
    "compact": "compact",
    "checkpoint": "checkpoint",
    "resume": "resume",
    "rescore": "rescore",
    "report": "report",
    "run": "run",
    "doctor": "doctor",
    "hook": "hook",
    "verify": "verify",
    "plan": "plan",
    "gate": "gate",
}


def _registered_subcommands() -> set:
    """The set of subparser choices on the freshly-built parser."""
    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    return set()


def _capability_manifest() -> list:
    """Build the doctor `capabilities` list from CAPABILITY_VERBS vs the actually
    registered subparser choices. reachable=True iff the verb exists."""
    registered = _registered_subcommands()
    return [
        {"capability": cap, "verb": verb, "reachable": verb in registered}
        for cap, verb in sorted(CAPABILITY_VERBS.items())
    ]


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

    collect = sub.add_parser("collect", help="normalize provider payload -> ingest-ready dicts (CollectionResult JSON)")
    _add_input(collect)
    collect.set_defaults(func=_cmd_collect)

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
    memory.add_argument(
        "--op",
        choices=("record", "search", "stats", "record-feedback", "list-feedback"),
        default="stats",
    )
    memory.add_argument("--query", default=None, help="search query (op=search)")
    memory.add_argument("--limit", type=int, default=10)
    memory.add_argument("--now", default=None)
    memory.add_argument("--kind", default=None, help="filter feedback by kind (op=list-feedback)")
    memory.add_argument("--run-id", dest="run_id", default=None, help="filter feedback by run_id (op=list-feedback)")
    memory.set_defaults(func=_cmd_memory)

    rescore = sub.add_parser("rescore", help="re-derive tiers/confidence/verdicts from cached components")
    _add_input(rescore)
    rescore.add_argument("--shallow", action="store_true", help="skip factcheck + clustering (verdicts may be stale)")
    rescore.add_argument("--report", action="store_true", help="render the rescored snapshot as Markdown instead of JSON")
    rescore.add_argument("--mode", default="findings", help="report mode (with --report): findings|debunk|mixed")
    rescore.add_argument("--out", default=None, help="also write the rescored snapshot JSON here")
    rescore.set_defaults(func=_cmd_rescore)

    eval_ = sub.add_parser("eval", help="precision@k / nDCG@k / jaccard / coverage")
    _add_input(eval_)
    eval_.set_defaults(func=_cmd_eval)

    cost = sub.add_parser("cost", help="per-gate budget report + alerts (GateCostTracker)")
    _add_input(cost)
    cost.set_defaults(func=_cmd_cost)

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

    compact = sub.add_parser("compact", help="snapshot JSON -> compact handoff dict (JSON)")
    _add_input(compact)
    compact.set_defaults(func=_cmd_compact)

    verify = sub.add_parser("verify", help="independent re-verification of a snapshot's claims (disagreement report)")
    _add_input(verify)
    verify.set_defaults(func=_cmd_verify)

    plan = sub.add_parser("plan", help="validate + layer a sub-task DAG (status/errors/layers/ready)")
    _add_input(plan)
    plan.set_defaults(func=_cmd_plan)

    gate = sub.add_parser("gate", help="gate oracles: blocks_transition / should_stop / should_compact")
    _add_input(gate)
    gate.set_defaults(func=_cmd_gate)

    hook = sub.add_parser(
        "hook",
        help="manage/test hook middleware (list|test|fire); for self-test without live Claude Code",
    )
    hook.add_argument(
        "--op",
        choices=("list", "test", "fire"),
        default="list",
        help="list: show registered hooks; test/fire: run a hook script on a fixture payload",
    )
    hook.add_argument(
        "--script",
        default=None,
        metavar="PATH",
        help="path to hook script (required for --op test/fire)",
    )
    hook.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="hook config to list (default: hooks/settings.example.json, the inert opt-in template)",
    )
    hook.add_argument(
        "--payload",
        default=None,
        metavar="JSON_OR_FILE",
        help="JSON string or path to JSON file piped to the hook script as stdin",
    )
    hook.set_defaults(func=_cmd_hook)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return func(args)
