"""Phase 1 unit tests — run from the skill dir:  python -m unittest discover -s tests -t .

Covers: snapshot round-trip (dict + JSON), validate_snapshot invariants,
fingerprint match/mismatch (+ acceptance_criteria exclusion), staleness windows,
carry_budget, assert_sources_readonly, checkpoint save/load + NN-1 fallback,
and resume_or_fresh (fresh -> resume -> restale).
"""

import json
import tempfile
import unittest
from pathlib import Path

from engine import state
from engine.model import (
    Budget,
    Claim,
    ClaimCategory,
    ClaimRole,
    ClaimStatus,
    DateConfidence,
    Depth,
    EvidenceCluster,
    GateResult,
    GateVerdict,
    Route,
    ScoreComponents,
    Snapshot,
    Source,
    SourceStatus,
    SubTask,
    SubTaskStatus,
    SubTaskType,
    Tier,
    snapshot_from_dict,
    snapshot_to_dict,
    validate_snapshot,
)


def make_task_frame() -> "state.TaskFrame":
    from engine.model import TaskFrame

    return TaskFrame(
        question="  Whoop prices on CDEK ",
        route=Route.FOCUSED,
        depth=Depth.STANDARD,
        scope=["cdek.shopping"],
        acceptance_criteria=["AC1"],
        language="ru",
    )


def make_snapshot() -> Snapshot:
    tf = make_task_frame()
    s1 = Source(
        id="S1", url="https://a", title="A", tier=Tier.S,
        fetched_via="native_web_search", status=SourceStatus.RENDERED,
        created_utc="2026-06-09T10:00:00Z", raw_path="raw/S1.txt", extract={"price": "100"},
        published_at="2026-06-01", date_confidence=DateConfidence.HIGH, time_sensitive=True,
        scores=ScoreComponents(authority=0.9, composite=0.8),
    )
    s2 = Source(id="S2", url="https://b")  # mostly defaults: tier None, scores all None
    c1 = Claim(
        id="C1", text="x", role=ClaimRole.EXTERNAL_CLAIM, category=ClaimCategory.VERIFIED,
        confidence=4, sources=["S1", "S2"], status=ClaimStatus.CONFIRMED, cluster_id="K1",
    )
    k1 = EvidenceCluster(id="K1", title="cluster", claim_ids=["C1"], representative_ids=["C1"])
    st1 = SubTask(id="ST-1", type=SubTaskType.SEARCH, status=SubTaskStatus.DONE)
    return Snapshot(
        run_id="r1", task_fingerprint=state.compute_fingerprint(tf), task_frame=tf,
        created_utc="2026-06-09T10:02:00Z", stage="cp_01_raw", phase_completed=2, next_phase=3,
        last_gate=GateResult(id="G1", verdict=GateVerdict.PASS),
        budget=Budget(limit_usd=0.2, spent_usd=0.05, loads_used=4, loads_cap=6),
        subtasks=[st1], sources=[s1, s2], claims=[c1], clusters=[k1],
        open_items=["oi"], resume_instruction="continue at phase 3",
    )


class TestRoundTrip(unittest.TestCase):
    def test_dict_round_trip(self):
        s = make_snapshot()
        self.assertEqual(snapshot_from_dict(snapshot_to_dict(s)), s)

    def test_json_round_trip(self):
        s = make_snapshot()
        restored = snapshot_from_dict(json.loads(json.dumps(snapshot_to_dict(s))))
        self.assertEqual(restored, s)

    def test_category_value_lowercase(self):
        d = snapshot_to_dict(make_snapshot())
        self.assertEqual(d["claims"][0]["category"], "verified")
        self.assertEqual(d["claims"][0]["role"], "external_claim")

    def test_none_fields_dropped(self):
        d = snapshot_to_dict(make_snapshot())
        # S2 has tier=None -> key omitted; S1 has tier set -> present.
        s2 = next(x for x in d["sources"] if x["id"] == "S2")
        self.assertNotIn("tier", s2)
        s1 = next(x for x in d["sources"] if x["id"] == "S1")
        self.assertEqual(s1["tier"], "S")

    def test_unsupported_version_raises(self):
        with self.assertRaises(ValueError):
            snapshot_from_dict({"checkpoint_version": "9.9"})


class TestValidate(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(validate_snapshot(make_snapshot()), [])

    def test_violations(self):
        s = make_snapshot()
        s.sources.append(Source(id="S1", url="https://dup"))           # duplicate id
        s.claims[0].confidence = 9                                     # out of 1..5
        s.claims[0].sources = ["S1", "S9"]                             # dangling ref
        s.clusters[0].representative_ids = ["C9"]                      # rep not in claim_ids
        s.next_phase = 9                                               # out of 0..6
        s.budget.spent_usd = -1.0                                      # negative
        errs = validate_snapshot(s)
        joined = " | ".join(errs)
        self.assertIn("duplicate source id: S1", joined)
        self.assertIn("confidence 9", joined)
        self.assertIn("unknown source S9", joined)
        self.assertIn("representative C9 not in claim_ids", joined)
        self.assertIn("next_phase 9", joined)
        self.assertIn("budget.spent_usd negative", joined)


class TestFingerprint(unittest.TestCase):
    def test_stable_across_case_ws_scope_order(self):
        from engine.model import TaskFrame
        a = TaskFrame(question="Whoop  PRICES on cdek", route=Route.FOCUSED, depth=Depth.STANDARD, scope=["B", "a"])
        b = TaskFrame(question="  whoop prices on CDEK  ", route=Route.FOCUSED, depth=Depth.STANDARD, scope=["a", "B"])
        self.assertEqual(state.compute_fingerprint(a), state.compute_fingerprint(b))

    def test_differs_on_question_depth_scope(self):
        from engine.model import TaskFrame
        base = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD, scope=["x"])
        fp = state.compute_fingerprint(base)
        self.assertNotEqual(fp, state.compute_fingerprint(TaskFrame(question="q2", route=Route.FOCUSED, depth=Depth.STANDARD, scope=["x"])))
        self.assertNotEqual(fp, state.compute_fingerprint(TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.DEEP, scope=["x"])))
        self.assertNotEqual(fp, state.compute_fingerprint(TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD, scope=["x", "y"])))

    def test_excludes_acceptance_criteria(self):
        from engine.model import TaskFrame
        a = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD, scope=["x"], acceptance_criteria=["one"])
        b = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD, scope=["x"], acceptance_criteria=["two", "three"])
        self.assertEqual(state.compute_fingerprint(a), state.compute_fingerprint(b))


class TestStaleness(unittest.TestCase):
    def _snap(self, *sources):
        from engine.model import TaskFrame
        tf = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD)  # 168h window
        return Snapshot(run_id="r", task_fingerprint="fp", task_frame=tf, sources=list(sources))

    def test_stale_fresh_nonts_missing(self):
        now = "2026-06-10T00:00:00Z"
        old = Source(id="S1", url="u", time_sensitive=True, created_utc="2026-06-01T00:00:00Z")   # 216h > 168 -> stale
        fresh = Source(id="S2", url="u", time_sensitive=True, created_utc="2026-06-09T00:00:00Z")  # 24h -> fresh
        nonts = Source(id="S3", url="u", time_sensitive=False, created_utc="2026-01-01T00:00:00Z")  # old but not TS
        missing = Source(id="S4", url="u", time_sensitive=True, created_utc="")                    # unknown age -> stale
        snap = self._snap(old, fresh, nonts, missing)
        self.assertEqual(set(state.stale_source_ids(snap, now)), {"S1", "S4"})


class TestBudgetAndReadonly(unittest.TestCase):
    def test_carry_budget(self):
        prev = Budget(limit_usd=0.5, spent_usd=0.3, loads_used=5, loads_cap=10)
        fresh = Budget(limit_usd=0.2, spent_usd=0.0, loads_used=0, loads_cap=6)
        r = state.carry_budget(prev, fresh)
        self.assertEqual((r.limit_usd, r.spent_usd, r.loads_used, r.loads_cap), (0.2, 0.3, 5, 6))

    def test_sources_readonly_detects_mutation(self):
        before = make_snapshot()
        after = make_snapshot()
        after.sources[0].extract = {"price": "999"}          # mutate S1 payload
        after.sources.append(Source(id="S3", url="https://c"))  # a brand-new source is not a mutation
        self.assertEqual(state.assert_sources_readonly(before, after), ["S1"])

    def test_sources_readonly_clean(self):
        self.assertEqual(state.assert_sources_readonly(make_snapshot(), make_snapshot()), [])


class TestCheckpointIO(unittest.TestCase):
    def test_save_load_and_latest_with_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            s = make_snapshot()
            p1 = state.save_checkpoint(s, run_dir, "raw")
            self.assertTrue(p1.name.startswith("cp_01_raw"))
            p2 = state.save_checkpoint(s, run_dir, "verified")
            self.assertTrue(p2.name.startswith("cp_02_verified"))
            self.assertEqual(state.find_latest_checkpoint(run_dir), p2)
            self.assertEqual(state.load_checkpoint(p2), s)
            # corrupt a higher-NN checkpoint -> find_latest falls back to NN-1
            (run_dir / "cp_03_bad.md").write_text("```json\n{not json}\n```", encoding="utf-8")
            self.assertEqual(state.find_latest_checkpoint(run_dir), p2)


class TestResume(unittest.TestCase):
    def test_fresh_then_resume_then_restale(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tf = make_task_frame()
            now = "2026-06-09T11:00:00Z"  # 1h after S1 created -> not stale
            d0 = state.resume_or_fresh(tf, root, now)
            self.assertEqual(d0.mode, state.ResumeMode.FRESH)
            self.assertIsNone(d0.snapshot)

            state.save_checkpoint(make_snapshot(), d0.run_dir, "raw")

            d1 = state.resume_or_fresh(tf, root, now)
            self.assertEqual(d1.mode, state.ResumeMode.RESUME)
            self.assertIsNotNone(d1.snapshot)
            self.assertEqual(d1.stale_source_ids, [])

            d2 = state.resume_or_fresh(tf, root, "2026-07-01T00:00:00Z")  # weeks later
            self.assertEqual(d2.mode, state.ResumeMode.RESUME_RESTALE)
            self.assertIn("S1", d2.stale_source_ids)


if __name__ == "__main__":
    unittest.main()
