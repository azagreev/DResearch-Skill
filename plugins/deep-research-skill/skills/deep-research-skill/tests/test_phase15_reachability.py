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
        # Every claim exposes a metadata dict (frozen contract). Once B's
        # auto-verify lands, it carries "disagreement"/"reverified_category";
        # until then the field still exists and is a dict — tolerate empty.
        self.assertTrue(snap.claims)
        for claim in snap.claims:
            self.assertIsInstance(claim.metadata, dict)
            if claim.metadata:
                # If populated by B's auto-verify, the contract keys are present.
                self.assertIn("disagreement", claim.metadata)
                self.assertIn("reverified_category", claim.metadata)

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


if __name__ == "__main__":
    unittest.main()
