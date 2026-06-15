"""Phase 15 unit tests — run_pipeline wiring (AC15-5).

Exercises the reachability additions inside engine.pipeline.run_pipeline:
  1. auto-trace      — one event per stage, in order, on snapshot.trace
  2. gate-consult    — snapshot.next_phase is the highest non-blocked target,
                       snapshot.last_gate carries the reason (None on a clean run)
(The in-pipeline auto-verify was removed in v1.5 — never rendered, constant-False
on hint-less runs; on-demand re-derivation stays in the `verify` CLI verb.)

Conventions mirror tests/test_phase11.py: stdlib unittest, a fixed NOW (no
clock/random), absolute-import the engine package.

Run from the skill dir:  python -m unittest tests.test_phase15_pipeline -v
"""

import unittest

from engine.model import (
    Claim,
    Depth,
    GateVerdict,
    Route,
    TaskFrame,
    Tier,
    snapshot_to_dict,
)
from engine.pipeline import run_pipeline

NOW = "2026-06-30T00:00:00Z"

_STAGE_ORDER = ["ingest", "score", "factcheck", "cluster", "build"]


def _task_frame() -> TaskFrame:
    return TaskFrame(question="q?", route=Route.FOCUSED, depth=Depth.STANDARD)


def _raw_sources():
    # Two distinct Tier-S sources; extract carries a snippet (plus the ingest
    # fence) so extraction_table_complete is True.
    return [
        {"url": "https://a.example/1", "title": "A", "snippet": "alpha", "tier": "S"},
        {"url": "https://b.example/2", "title": "B", "snippet": "beta", "tier": "S"},
    ]


class CleanRunTest(unittest.TestCase):
    def _run_clean(self):
        claims = [
            Claim(id="C1", text="supported claim", sources=["S1"]),
            Claim(id="C2", text="second claim", sources=["S2"]),
        ]
        return run_pipeline("run1", _task_frame(), _raw_sources(), claims, NOW)

    def test_clean_run_reaches_phase_5_with_no_block_reason(self):
        snap, _ = self._run_clean()
        self.assertEqual(snap.next_phase, 5)
        self.assertIsNotNone(snap.last_gate)
        self.assertEqual(snap.last_gate.verdict, GateVerdict.PASS)
        self.assertIsNone(snap.last_gate.reason)
        # Gate signals were set (and thus available to the gate consult).
        self.assertEqual(snap.sources_screened, 2)
        self.assertTrue(snap.citations_verified)
        self.assertTrue(snap.extraction_table_complete)

    def test_trace_non_empty_in_stage_order(self):
        snap, _ = self._run_clean()
        self.assertTrue(snap.trace)  # non-empty
        events = [row["event"] for row in snap.trace]
        self.assertEqual(events, _STAGE_ORDER)
        for row in snap.trace:
            self.assertEqual(row["ts"], NOW)  # ts is always now_utc


class GateBlockedRunTest(unittest.TestCase):
    def test_no_supporting_sources_caps_next_phase_below_5(self):
        # A claim with NO supporting source -> citations_verified False -> the
        # gate blocks the >=5 transition, so next_phase is capped at 4.
        claims = [Claim(id="C1", text="unsupported", sources=[])]
        snap, _ = run_pipeline("run2", _task_frame(), _raw_sources(), claims, NOW)
        self.assertFalse(snap.citations_verified)
        self.assertLess(snap.next_phase, 5)
        self.assertEqual(snap.next_phase, 4)
        self.assertEqual(snap.last_gate.verdict, GateVerdict.FAIL)
        self.assertIsNotNone(snap.last_gate.reason)
        self.assertIn("citations_verified", snap.last_gate.reason)

    def test_no_sources_at_all_caps_next_phase_at_1(self):
        # No sources -> sources_screened 0 -> gate blocks every >=2 transition,
        # so only phase 1 is reachable.
        claims = [Claim(id="C1", text="x", sources=[])]
        snap, _ = run_pipeline("run3", _task_frame(), [], claims, NOW)
        self.assertEqual(snap.sources_screened, 0)
        self.assertEqual(snap.next_phase, 1)
        self.assertEqual(snap.last_gate.verdict, GateVerdict.FAIL)
        self.assertIsNotNone(snap.last_gate.reason)


class DeterminismTest(unittest.TestCase):
    def test_same_inputs_yield_identical_snapshot_dict(self):
        def build():
            claims = [
                Claim(id="C1", text="supported claim", sources=["S1"]),
                Claim(id="C2", text="second claim", sources=["S2"]),
            ]
            snap, _ = run_pipeline("run5", _task_frame(), _raw_sources(), claims, NOW)
            return snapshot_to_dict(snap)

        first = build()
        second = build()
        self.assertEqual(first, second)
        # trace is part of the serialized form and must be reproduced verbatim.
        self.assertEqual(first["trace"], second["trace"])
        self.assertTrue(first["trace"])


if __name__ == "__main__":
    unittest.main()
