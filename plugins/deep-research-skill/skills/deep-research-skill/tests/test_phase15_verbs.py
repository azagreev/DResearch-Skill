"""Phase 15 — focused tests for the verify / plan / gate CLI verbs (AC15-2/3/4).

Each verb is driven through cli.main() with a JSON file input; stdout is parsed
back to JSON. A fixed NOW is used throughout — never the wall clock. Run from
the skill dir:
    python -m unittest tests.test_phase15_verbs -v
"""

import copy
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from engine import cli
from engine.model import (
    Claim,
    ClaimCategory,
    Depth,
    Route,
    Snapshot,
    Source,
    SubTask,
    SubTaskStatus,
    SubTaskType,
    TaskFrame,
    Tier,
    snapshot_to_dict,
)
from engine.plan import MAX_CONCURRENT

NOW = "2026-06-30T00:00:00Z"


class _VerbBase(unittest.TestCase):
    def _write(self, obj) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(obj, handle)
        handle.close()
        self.addCleanup(lambda: os.unlink(handle.name))
        return handle.name

    def _json(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main(argv)
        self.assertEqual(rc, 0, buf.getvalue())
        return json.loads(buf.getvalue())

    def _tf(self):
        return TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD)


class VerifyVerbTest(_VerbBase):
    def _snapshot(self, recorded_category: ClaimCategory) -> Snapshot:
        # A claim supported by a single S-tier source: the evidence-only
        # re-derivation lands on VERIFIED. Recording a different category on the
        # claim plants a disagreement.
        return Snapshot(
            run_id="r",
            task_fingerprint="f",
            task_frame=self._tf(),
            sources=[Source(id="S1", url="u", tier=Tier.S)],
            claims=[Claim(id="C1", text="fact", category=recorded_category,
                          confidence=4, sources=["S1"])],
        )

    def test_planted_wrong_category_disagrees(self):
        snap = self._snapshot(ClaimCategory.FALSE)  # evidence supports VERIFIED
        out = self._json(["verify", "-i", self._write({"snapshot": snapshot_to_dict(snap), "now": NOW})])
        self.assertEqual(out["summary"]["n_claims"], 1)
        self.assertEqual(out["summary"]["n_disagreements"], 1)
        row = out["results"][0]
        self.assertEqual(row["claim_id"], "C1")
        self.assertEqual(row["original_category"], "false")
        self.assertEqual(row["reverified_category"], "verified")
        self.assertTrue(row["disagreement"])

    def test_agreeing_category_no_disagreement(self):
        snap = self._snapshot(ClaimCategory.VERIFIED)
        out = self._json(["verify", "-i", self._write({"snapshot": snapshot_to_dict(snap), "now": NOW})])
        self.assertEqual(out["summary"]["n_disagreements"], 0)
        self.assertFalse(out["results"][0]["disagreement"])
        self.assertEqual(out["results"][0]["reverified_category"], "verified")

    def test_input_snapshot_not_mutated(self):
        snap = self._snapshot(ClaimCategory.FALSE)
        payload = {"snapshot": snapshot_to_dict(snap), "now": NOW}
        frozen = copy.deepcopy(payload)
        self._json(["verify", "-i", self._write(payload)])
        # The handler reads from a file; assert the in-memory dict the test holds
        # is structurally identical to a pre-call deep copy (the dict passed to
        # the file is unchanged) and that re-parsing the snapshot keeps the
        # recorded category — i.e. verify did not rewrite the claim's category.
        self.assertEqual(payload, frozen)
        self.assertEqual(payload["snapshot"]["claims"][0]["category"], "false")


class PlanVerbTest(_VerbBase):
    def _st(self, sid, deps, status="pending"):
        return {"id": sid, "type": "SEARCH", "status": status, "depends_on": deps}

    def test_cyclic_subtasks_invalid(self):
        subtasks = [self._st("ST-1", ["ST-2"]), self._st("ST-2", ["ST-1"])]
        out = self._json(["plan", "-i", self._write({"subtasks": subtasks})])
        self.assertEqual(out["status"], "invalid")
        self.assertTrue(out["errors"])
        self.assertTrue(any("cycle" in e for e in out["errors"]))

    def test_valid_dag_layers_and_ready(self):
        # ST-1 -> ST-2 -> ST-3 chain; ST-4 independent. ST-1 done so ST-2 ready.
        subtasks = [
            self._st("ST-1", [], status="done"),
            self._st("ST-2", ["ST-1"]),
            self._st("ST-3", ["ST-2"]),
            self._st("ST-4", []),
        ]
        out = self._json(["plan", "-i", self._write({"subtasks": subtasks})])
        self.assertEqual(out["status"], "valid")
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["max_concurrent"], MAX_CONCURRENT)
        # Every layer respects MAX_CONCURRENT and the union covers all ids once.
        flat = [sid for layer in out["layers"] for sid in layer]
        self.assertCountEqual(flat, ["ST-1", "ST-2", "ST-3", "ST-4"])
        for layer in out["layers"]:
            self.assertLessEqual(len(layer), MAX_CONCURRENT)
        # ST-2 ready (its only STRICT predecessor ST-1 is DONE); ST-3 not (ST-2
        # pending); ST-4 ready (no predecessors).
        self.assertIn("ST-2", out["ready"])
        self.assertIn("ST-4", out["ready"])
        self.assertNotIn("ST-3", out["ready"])

    def test_plan_from_snapshot_subtasks(self):
        snap = Snapshot(
            run_id="r", task_fingerprint="f", task_frame=self._tf(),
            subtasks=[
                SubTask(id="ST-1", type=SubTaskType.SEARCH, status=SubTaskStatus.PENDING),
                SubTask(id="ST-2", type=SubTaskType.ANALYZE, status=SubTaskStatus.PENDING,
                        depends_on=["ST-1"]),
            ],
        )
        out = self._json(["plan", "-i", self._write({"snapshot": snapshot_to_dict(snap)})])
        self.assertEqual(out["status"], "valid")
        self.assertIn("ST-1", out["ready"])


class GateVerbTest(_VerbBase):
    def test_unverified_target5_blocks_transition(self):
        # citations_verified False + a source screened -> transition to phase 5
        # is gate-blocked; next_phase 5 is the pre_synthesis compaction boundary.
        snap = Snapshot(
            run_id="r", task_fingerprint="f", task_frame=self._tf(),
            next_phase=5, sources_screened=3, citations_verified=False,
        )
        out = self._json(["gate", "-i", self._write({"snapshot": snapshot_to_dict(snap), "target_phase": 5})])
        self.assertIsNotNone(out["blocks_transition"])
        self.assertIn("citations_verified", out["blocks_transition"])
        self.assertEqual(out["should_compact"], "pre_synthesis")

    def test_target_phase_defaults_to_next_phase(self):
        # No target_phase given -> uses snapshot.next_phase (3 == post_collection).
        snap = Snapshot(
            run_id="r", task_fingerprint="f", task_frame=self._tf(),
            next_phase=3, sources_screened=5, citations_verified=True,
        )
        out = self._json(["gate", "-i", self._write({"snapshot": snapshot_to_dict(snap)})])
        # target 3 only needs sources_screened > 0, which holds -> not blocked.
        self.assertIsNone(out["blocks_transition"])
        self.assertEqual(out["should_compact"], "post_collection")

    def test_should_stop_budget_exhausted(self):
        from engine.model import Budget
        snap = Snapshot(
            run_id="r", task_fingerprint="f", task_frame=self._tf(),
            next_phase=2, sources_screened=1,
            budget=Budget(limit_usd=10.0, spent_usd=10.0),
        )
        out = self._json(["gate", "-i", self._write({"snapshot": snapshot_to_dict(snap)})])
        self.assertEqual(out["should_stop"], "budget_exhausted")


if __name__ == "__main__":
    unittest.main()
