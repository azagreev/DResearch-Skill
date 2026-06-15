"""Phase 15 — reachability acceptance (AC15-7).

A capability is only "done" this phase if it is reachable end-to-end: a CLI verb
exists AND/OR run_pipeline calls it. This module enforces that bar three ways:

  (a) build_parser() registers a subparser for every curated capability verb —
      any orphan (curated capability with no verb) FAILS the build;
  (b) subprocess-smoke `python -m engine <verb>` for verify/plan/gate on minimal
      fixtures exits 0 and returns the contract's top-level keys;
  (c) an end-to-end check that pipeline.run_pipeline produces a snapshot carrying
      a gate-consulted next_phase and per-claim metadata (and, once B's wiring
      lands, a non-empty trace).

Imports pipeline.run_pipeline directly for (c) so it does not depend on B's CLI
wiring beyond the shared verb I/O contract. Fixed NOW; never the clock. Run from
the skill dir:
    python -m unittest tests.test_phase15_reachability -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from engine import cli
from engine.cli import CAPABILITY_VERBS
from engine.model import (
    Claim,
    Depth,
    Route,
    Source,
    TaskFrame,
    snapshot_to_dict,
)

NOW = "2026-06-30T00:00:00Z"

# The curated capability registry the phase pins (mirrors cli.CAPABILITY_VERBS).
CURATED_CAPABILITIES = (
    "collect", "ingest", "rank", "score", "factcheck", "cluster", "memory",
    "eval", "cost", "compact", "checkpoint", "resume", "rescore", "report",
    "run", "doctor", "hook", "verify", "plan", "gate",
)

# Skill root (parent of tests/) is the cwd `python -m engine` must run from.
SKILL_DIR = Path(__file__).resolve().parent.parent


def _subparser_choices() -> set:
    import argparse

    parser = cli.build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    return set()


class RegistryReachabilityTest(unittest.TestCase):
    def test_every_curated_capability_has_a_verb(self):
        choices = _subparser_choices()
        orphans = [cap for cap in CURATED_CAPABILITIES if CAPABILITY_VERBS.get(cap) not in choices]
        self.assertEqual(orphans, [], f"unreachable capabilities (no verb registered): {orphans}")

    def test_curated_registry_matches_cli_module(self):
        # Guard against the test's curated tuple drifting from the engine's map.
        self.assertEqual(set(CURATED_CAPABILITIES), set(CAPABILITY_VERBS))

    def test_doctor_manifest_marks_all_reachable(self):
        manifest = cli._capability_manifest()
        by_cap = {row["capability"]: row for row in manifest}
        for cap in CURATED_CAPABILITIES:
            self.assertIn(cap, by_cap)
            self.assertTrue(by_cap[cap]["reachable"], f"{cap} flagged unreachable in doctor manifest")


class SubprocessSmokeTest(unittest.TestCase):
    """`python -m engine <verb>` on a minimal stdin fixture -> exit 0 + keys."""

    def _run(self, verb: str, payload: dict) -> dict:
        proc = subprocess.run(
            [sys.executable, "-m", "engine", verb],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(SKILL_DIR),
        )
        self.assertEqual(proc.returncode, 0, f"{verb} exited {proc.returncode}: {proc.stderr}")
        return json.loads(proc.stdout)

    def _snapshot(self):
        tf = TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD)
        from engine.model import Snapshot, Tier

        snap = Snapshot(
            run_id="r", task_fingerprint="f", task_frame=tf,
            next_phase=5, sources_screened=1, citations_verified=False,
            sources=[Source(id="S1", url="u", tier=Tier.S)],
            claims=[Claim(id="C1", text="fact", confidence=4, sources=["S1"])],
        )
        return snapshot_to_dict(snap)

    def test_verify_smoke(self):
        out = self._run("verify", {"snapshot": self._snapshot(), "now": NOW})
        self.assertIn("results", out)
        self.assertIn("summary", out)
        self.assertIn("n_claims", out["summary"])

    def test_plan_smoke(self):
        payload = {"subtasks": [
            {"id": "ST-1", "type": "SEARCH", "depends_on": []},
            {"id": "ST-2", "type": "ANALYZE", "depends_on": ["ST-1"]},
        ]}
        out = self._run("plan", payload)
        for key in ("status", "layers", "ready", "max_concurrent"):
            self.assertIn(key, out)
        self.assertEqual(out["status"], "valid")

    def test_gate_smoke(self):
        out = self._run("gate", {"snapshot": self._snapshot(), "target_phase": 5})
        for key in ("blocks_transition", "should_stop", "should_compact"):
            self.assertIn(key, out)

    def test_doctor_smoke_carries_capabilities(self):
        proc = subprocess.run(
            [sys.executable, "-m", "engine", "doctor"],
            capture_output=True, text=True, cwd=str(SKILL_DIR),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        # Existing diagnostics fields preserved + new capabilities manifest.
        self.assertIn("python_ok", out)
        self.assertIn("capabilities", out)
        verbs_seen = {row["capability"] for row in out["capabilities"]}
        self.assertEqual(verbs_seen, set(CURATED_CAPABILITIES))


class PipelineE2EReachabilityTest(unittest.TestCase):
    """End-to-end: run_pipeline output must be gate-consultable + carry claim
    metadata (and a non-empty trace once B's wiring lands). Imports the pipeline
    directly so this does not depend on B's CLI wiring beyond the contract."""

    def _run_pipeline(self):
        from engine import pipeline

        tf = TaskFrame(question="Whoop price", route=Route.FOCUSED, depth=Depth.STANDARD)
        raw_sources = [{
            "url": "https://cdek.shopping/whoop", "title": "Whoop", "tier": "S",
            "published_at": "2026-06-25",
            "scores": {"independence": 0.9, "traceability": 0.9, "corroboration": 0.8},
        }]
        claims = [Claim(id="C1", text="Whoop 30000", confidence=1, sources=["S1"])]
        snapshot, _merges = pipeline.run_pipeline("run", tf, raw_sources, claims, NOW)
        return snapshot

    def test_snapshot_is_gate_consultable(self):
        snap = self._run_pipeline()
        # next_phase is set by the pipeline (gate-consulted boundary) and is in
        # the valid phase range — gate.should_compact keys on exactly this.
        self.assertTrue(1 <= snap.next_phase <= 6)
        from engine.compact import should_compact
        from engine.state import gate_blocks_transition, should_stop

        # These oracles must run without error on a real pipeline snapshot.
        gate_blocks_transition(snap, snap.next_phase or 5)
        should_stop(snap)
        should_compact(snap)

    def test_claims_carry_metadata_field(self):
        snap = self._run_pipeline()
        # Every claim exposes a metadata dict (frozen contract). The v1.5
        # simplification removed the in-pipeline auto-verify (inert: never
        # rendered, constant-False on hint-less runs), so run_pipeline now
        # leaves metadata empty. On-demand re-derivation stays in `engine verify`.
        self.assertTrue(snap.claims)
        for claim in snap.claims:
            self.assertIsInstance(claim.metadata, dict)
            self.assertEqual(claim.metadata, {})

    def test_trace_present_or_tolerated(self):
        snap = self._run_pipeline()
        # trace is a list on every snapshot (frozen contract). B's wiring fills
        # it with one event per stage; tolerate empty until that lands, but if
        # present each entry must be an {event, ts, ...} dict.
        self.assertIsInstance(snap.trace, list)
        for entry in snap.trace:
            self.assertIsInstance(entry, dict)
            self.assertIn("event", entry)
            self.assertIn("ts", entry)


# ---------------------------------------------------------------------------
# Docs <-> CLI consistency — regression guard for the recurring "docs describe a
# CLI that does not exist" class (Phase 14 AGENT.MD §9 invented --flags/verbs;
# Phase 15 verify's invented `{snapshot, subtasks}` JSON-in key — both escaped
# human review). Cheap, parser/AST-driven; no fuzzy guessing.
# ---------------------------------------------------------------------------
import ast
import re

_DOC_FILES = ("AGENT.MD", "SKILL.md")

# The JSON-in key check is scoped to the snapshot-input verbs (where the incident
# occurred). memory's JSON-in is a nested feedback *record*, not a top-level data
# contract, so it is intentionally excluded to keep the guard false-positive-free.
_KEY_CHECK_VERBS = frozenset({"verify", "plan", "gate", "rescore"})

_INLINE_CODE = re.compile(r"`([^`]+)`")
_FENCED = re.compile(r"```.*?```", re.DOTALL)
_ENGINE_VERB = re.compile(r"(?:python -m )?engine\s+([a-z][a-z0-9_-]*)")
_FLAG = re.compile(r"--[a-z][a-z0-9-]*")


def _doc_text():
    return {name: (SKILL_DIR / name).read_text(encoding="utf-8") for name in _DOC_FILES}


def _code_fragments(text: str):
    return _FENCED.findall(text) + [m.group(1) for m in _INLINE_CODE.finditer(text)]


# Match only an actual engine COMMAND, not prose that happens to contain "engine".
_VERB_CMD = re.compile(r"^(?:python -m )?engine\s+([a-z][a-z0-9_-]*)")


def _documented_verbs(text: str) -> set:
    """engine verbs that appear as a real command: an inline-code span that *is*
    `engine <verb>` (or `python -m engine <verb>`), or a `python -m engine <verb>`
    line inside a fenced block. Prose mentions of the word 'engine' are ignored."""
    verbs = set()
    for m in _INLINE_CODE.finditer(text):
        mm = _VERB_CMD.match(m.group(1).strip())
        if mm:
            verbs.add(mm.group(1))
    for block in _FENCED.findall(text):
        verbs.update(re.findall(r"python -m engine\s+([a-z][a-z0-9_-]*)", block))
    return verbs


def _documented_flags(text: str) -> set:
    """--flags that appear in an engine-command fragment (inline span starting with
    `engine`/`python -m engine`, or a fenced block that runs `python -m engine`)."""
    flags = set()
    for m in _INLINE_CODE.finditer(text):
        span = m.group(1).strip()
        if _VERB_CMD.match(span):
            flags.update(_FLAG.findall(span))
    for block in _FENCED.findall(text):
        if "python -m engine" in block:
            flags.update(_FLAG.findall(block))
    return flags


def _real_flag_set() -> set:
    """Every long-option (--flag) the real parser accepts, top parser + subparsers."""
    import argparse

    flags: set = set()

    def collect(p):
        for a in p._actions:
            flags.update(o for o in a.option_strings if o.startswith("--"))

    parser = cli.build_parser()
    collect(parser)
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                collect(sub)
    return flags


def _handler_input_keys() -> dict:
    """verb -> {literal keys each `_cmd_<verb>` reads off the JSON `data` dict}
    (data["k"] / data.get("k")), extracted from cli.py via AST (no execution)."""
    tree = ast.parse((SKILL_DIR / "engine" / "cli.py").read_text(encoding="utf-8"))
    keys: dict = {}
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name.startswith("_cmd_")):
            continue
        found: set = set()
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name)
                    and sub.value.id == "data" and isinstance(sub.slice, ast.Constant)
                    and isinstance(sub.slice.value, str)):
                found.add(sub.slice.value)
            elif (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == "get" and isinstance(sub.func.value, ast.Name)
                    and sub.func.value.id == "data" and sub.args
                    and isinstance(sub.args[0], ast.Constant)
                    and isinstance(sub.args[0].value, str)):
                found.add(sub.args[0].value)
        keys[node.name[len("_cmd_"):]] = found
    return keys


def _brace_groups(s: str):
    """Top-level balanced {...} group contents (nested braces stay inside)."""
    groups, i = [], 0
    while i < len(s):
        if s[i] == "{":
            depth, start = 0, i
            while i < len(s):
                if s[i] == "{":
                    depth += 1
                elif s[i] == "}":
                    depth -= 1
                    if depth == 0:
                        groups.append(s[start + 1:i])
                        break
                i += 1
        i += 1
    return groups


def _top_level_split(s: str, sep: str):
    parts, depth, cur = [], 0, ""
    for c in s:
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        if c == sep and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += c
    parts.append(cur)
    return parts


def _keys_from_group(group: str):
    out = []
    for tok in _top_level_split(group, ","):
        key = _top_level_split(tok, ":")[0].strip().strip("`'\"?<> ").strip()
        if re.fullmatch(r"[a-z_][a-z0-9_]*", key or ""):
            out.append(key)
    return out


def _jsonin_violations(text: str, handler_keys: dict):
    """Return [(verb, key)] for documented JSON-in keys no handler actually reads."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if "JSON-in" not in line:
            continue
        m = _ENGINE_VERB.search(line)
        verb = m.group(1) if m else None
        if verb is None:  # attribute to the nearest preceding `engine <verb>` mention
            for j in range(i - 1, max(-1, i - 11), -1):
                m2 = _ENGINE_VERB.search(lines[j])
                if m2:
                    verb = m2.group(1)
                    break
        if verb not in _KEY_CHECK_VERBS or verb not in handler_keys:
            continue
        after = line.split("JSON-in", 1)[1]
        # Everything up to the first output marker is the input contract; parse
        # ALL input brace groups there (a verb may document alternatives, e.g.
        # plan's `{snapshot}` or `{subtasks}`, or verify's invented `{snapshot,
        # subtasks}` variant — both must be checked).
        cut = len(after)
        for marker in ("→", "->", "JSON-out", "returns", "Returns"):
            idx = after.find(marker)
            if idx != -1:
                cut = min(cut, idx)
        groups = _brace_groups(after[:cut])
        for g in groups:
            out.extend((verb, k) for k in _keys_from_group(g) if k not in handler_keys[verb])
    return out


class DocsCliConsistencyTest(unittest.TestCase):
    """Every engine verb / --flag / snapshot-input JSON-in key the docs mention
    must actually exist in the parser / handler — so an invented CLI contract
    (the recurring failure class) fails CI instead of a human reviewer."""

    def setUp(self):
        self.choices = _subparser_choices()
        self.real_flags = _real_flag_set()
        self.handler_keys = _handler_input_keys()
        self.docs = _doc_text()

    def test_documented_verbs_exist(self):
        bad = {}
        for name, text in self.docs.items():
            missing = sorted(v for v in _documented_verbs(text) if v not in self.choices)
            if missing:
                bad[name] = missing
        self.assertEqual(bad, {}, f"docs name engine verbs with no subparser: {bad}")

    def test_documented_flags_exist(self):
        bad = {}
        for name, text in self.docs.items():
            missing = sorted(f for f in _documented_flags(text) if f not in self.real_flags)
            if missing:
                bad[name] = missing
        self.assertEqual(bad, {}, f"docs name --flags the parser rejects: {bad}")

    def test_documented_jsonin_keys_exist(self):
        bad = {}
        for name, text in self.docs.items():
            v = sorted(set(_jsonin_violations(text, self.handler_keys)))
            if v:
                bad[name] = v
        self.assertEqual(bad, {}, f"docs document JSON-in keys no handler reads: {bad}")

    def test_checker_is_non_vacuous(self):
        # An invented key MUST be caught (guards the guard from silently passing).
        bad = "- `engine verify` — JSON-in `{snapshot, bogus_key?}` → `{results}`"
        self.assertIn(("verify", "bogus_key"), _jsonin_violations(bad, self.handler_keys))
        # A correct line must produce no violation.
        ok = "- `engine verify` — JSON-in `{snapshot, now?}` → `{results}`"
        self.assertEqual(_jsonin_violations(ok, self.handler_keys), [])


if __name__ == "__main__":
    unittest.main()
