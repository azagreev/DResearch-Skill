"""Coverage-gap tests called out by the 5-agent review: error/edge paths that
the per-phase suites skipped. Run from the skill dir:
    python -m unittest discover -s tests -t .
"""

import tempfile
import unittest
from pathlib import Path

from engine import cluster, eval as ev, factcheck, memory, score, state
from engine.model import (
    Budget,
    Claim,
    ClaimCategory,
    ClaimRole,
    Depth,
    EvidenceCluster,
    Route,
    Snapshot,
    Source,
    SubTask,
    SubTaskType,
    TaskFrame,
    Tier,
    snapshot_from_dict,
    validate_snapshot,
)
from engine.policy import Disposition, ReportMode, disposition

NOW = "2026-06-30T00:00:00Z"


def _tf(q="q"):
    return TaskFrame(question=q, route=Route.FOCUSED, depth=Depth.STANDARD)


def _snap(tf, run_id="r"):
    return Snapshot(run_id=run_id, task_fingerprint=state.compute_fingerprint(tf), task_frame=tf)


class TestResumeMismatchNoClobber(unittest.TestCase):
    def test_different_task_does_not_clobber(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tf_a, tf_b = _tf("question A"), _tf("question B")
            d_a = state.resume_or_fresh(tf_a, root, NOW)
            self.assertEqual(d_a.mode, state.ResumeMode.FRESH)
            state.save_checkpoint(_snap(tf_a, "rA"), d_a.run_dir, "raw")

            d_b = state.resume_or_fresh(tf_b, root, NOW)
            self.assertEqual(d_b.mode, state.ResumeMode.FRESH)        # different fingerprint
            self.assertNotEqual(d_b.run_dir, d_a.run_dir)             # separate dir
            self.assertIsNone(d_b.snapshot)

            d_a2 = state.resume_or_fresh(tf_a, root, NOW)
            self.assertEqual(d_a2.mode, state.ResumeMode.RESUME)      # A still intact


class TestCheckpointErrors(unittest.TestCase):
    def test_load_and_find_errors(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "cp_01_noblock.md").write_text("no json here", encoding="utf-8")
            with self.assertRaises(ValueError):
                state.load_checkpoint(run_dir / "cp_01_noblock.md")
            (run_dir / "cp_02_bad.md").write_text("```json\n{bad}\n```", encoding="utf-8")
            # all checkpoints corrupt -> None
            self.assertIsNone(state.find_latest_checkpoint(run_dir))

    def test_from_dict_missing_key(self):
        with self.assertRaises(KeyError):
            snapshot_from_dict({"task_fingerprint": "f", "task_frame": {"question": "q", "route": "B", "depth": "Standard"}})


class TestValidateRemaining(unittest.TestCase):
    def test_more_violations(self):
        tf = _tf()
        snap = Snapshot(
            run_id="r", task_fingerprint="f", task_frame=tf,
            sources=[Source(id="S1", url="u")],
            subtasks=[SubTask(id="ST-1", type=SubTaskType.SEARCH), SubTask(id="ST-1", type=SubTaskType.SEARCH)],
            claims=[Claim(id="C1", text="x", contradicting_sources=["S9"], cluster_id="K9")],
            clusters=[EvidenceCluster(id="K1", title="t", claim_ids=["C7"], representative_ids=[])],
        )
        joined = " | ".join(validate_snapshot(snap))
        self.assertIn("duplicate subtask id: ST-1", joined)
        self.assertIn("unknown contradicting source S9", joined)
        self.assertIn("unknown cluster_id K9", joined)
        self.assertIn("cluster K1: unknown claim C7", joined)


class TestEvalEdges(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(ev.precision_at_k(["a"], {"a"}, 0), 0.0)
        self.assertEqual(ev.precision_at_k(["a"], {"a"}, 5), 1.0)        # k>len -> over available
        self.assertEqual(ev.recall_at_k(["a"], set(), 3), 0.0)          # empty relevant
        self.assertEqual(ev.overlap_retention([], ["a"]), 0.0)          # empty previous
        self.assertEqual(ev.source_coverage(["a"], set()), 0.0)


class TestFtsLikeFallback(unittest.TestCase):
    def test_like_path_when_no_fts5(self):
        original = memory.FTS5_AVAILABLE
        memory.FTS5_AVAILABLE = False
        try:
            conn = memory.connect()
            snap = Snapshot(
                run_id="r", task_fingerprint="f", task_frame=_tf(),
                claims=[Claim(id="C1", text="Whoop pricing detail", category=ClaimCategory.VERIFIED, confidence=4)],
            )
            memory.record_run(conn, snap, NOW)
            hits = memory.search_claims(conn, "Whoop")
            self.assertTrue(any("Whoop" in h["text"] for h in hits))
        finally:
            memory.FTS5_AVAILABLE = original


class TestFactcheckCaps(unittest.TestCase):
    def _by_id(self, *s):
        return {x.id: x for x in s}

    def test_outdated_gate_requires_time_sensitive(self):
        sup = Source(id="sup", url="u", tier=Tier.A, published_at="2026-01-01", time_sensitive=False)
        con = Source(id="con", url="u", tier=Tier.C, published_at="2026-06-01")
        cat = factcheck.classify_claim(Claim(id="C", text="x", sources=["sup"], contradicting_sources=["con"]),
                                       self._by_id(sup, con))
        self.assertEqual(cat, ClaimCategory.VERIFIED)  # not time-sensitive -> not OUTDATED

    def test_intermediate_caps(self):
        by_id = self._by_id(Source(id="S1", url="u", tier=Tier.S), Source(id="S2", url="u", tier=Tier.S))
        # OPINION via disputed (S vs S, equal count, no dates), base 4 -> cap 3
        opinion = factcheck.factcheck_claim(
            Claim(id="C", text="x", sources=["S1"], contradicting_sources=["S2"], confidence=4), by_id)
        self.assertEqual((opinion.category, opinion.confidence), (ClaimCategory.OPINION, 3))
        # INCOMPLETE (model hint, supported), base 5 -> cap 4
        incomplete = factcheck.factcheck_claim(
            Claim(id="C", text="x", sources=["S1"], confidence=5), by_id, model_category=ClaimCategory.INCOMPLETE)
        self.assertEqual((incomplete.category, incomplete.confidence), (ClaimCategory.INCOMPLETE, 4))


class TestDispositionNoOverride(unittest.TestCase):
    def test_false_own_stays_revision_across_modes(self):
        c = Claim(id="C", text="x", role=ClaimRole.OWN_FINDING, category=ClaimCategory.FALSE)
        for mode in (ReportMode.FINDINGS, ReportMode.DEBUNK, ReportMode.MIXED):
            self.assertEqual(disposition(c, mode), Disposition.TRIGGER_REVISION)


class TestMmrDiversity(unittest.TestCase):
    def test_second_pick_is_diverse(self):
        seed = Claim(id="C1", text="apple banana cherry fruit", confidence=5)
        near = Claim(id="C2", text="apple banana cherry fruit date", confidence=4)  # similar, higher rel
        far = Claim(id="C3", text="zebra yak xenon wolf", confidence=3)             # dissimilar
        reps = cluster._mmr_select([seed, near, far], max_reps=2, lambda_=0.6)
        self.assertEqual(reps, ["C1", "C3"])  # diversity beats the more-similar higher-rel claim


if __name__ == "__main__":
    unittest.main()
