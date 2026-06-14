"""Phase 14 unit tests — feedback ledger (append-only) + scoring isolation.

Covers AC14-4: record_feedback is APPEND-ONLY (N records -> N rows; two records
with the same item_id keep both), now_utc is honored verbatim, list_feedback
filters by kind/run_id, and the scoring path is wholly unaffected by the
presence of feedback rows (it is a human-reviewed calibration dataset, never a
scoring input).

Run from the skill dir:  python -m unittest tests.test_phase14_feedback -v
"""

import unittest

from engine import memory, score
from engine.model import (
    Claim,
    ScoreComponents,
    Source,
    Tier,
)

NOW = "2026-06-30T00:00:00Z"
LATER = "2026-07-01T00:00:00Z"


def _record(item_id="C1", kind="claim_category", human="verified", engine="unverified", run_id="r1"):
    return {
        "run_id": run_id,
        "item_id": item_id,
        "kind": kind,
        "engine_value": engine,
        "human_value": human,
        "trace_json": {"note": "reviewer disagreed"},
    }


class TestFeedbackAppendOnly(unittest.TestCase):
    def test_n_records_n_rows(self):
        conn = memory.connect()
        for _ in range(5):
            memory.record_feedback(conn, _record(), NOW)
        rows = memory.list_feedback(conn)
        self.assertEqual(len(rows), 5)

    def test_same_item_id_two_rows(self):
        conn = memory.connect()
        r1 = memory.record_feedback(conn, _record(item_id="C1", human="verified"), NOW)
        r2 = memory.record_feedback(conn, _record(item_id="C1", human="false"), LATER)
        # Two distinct rows, never an overwrite.
        self.assertNotEqual(r1["id"], r2["id"])
        rows = memory.list_feedback(conn, run_id="r1")
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["human_value"] for row in rows}, {"verified", "false"})

    def test_now_utc_honored(self):
        conn = memory.connect()
        memory.record_feedback(conn, _record(), NOW)
        memory.record_feedback(conn, _record(), LATER)
        rows = memory.list_feedback(conn)
        self.assertEqual([r["recorded_utc"] for r in rows], [NOW, LATER])

    def test_trace_json_serialized(self):
        conn = memory.connect()
        memory.record_feedback(conn, _record(), NOW)
        rows = memory.list_feedback(conn)
        self.assertIn("reviewer disagreed", rows[0]["trace_json"])

    def test_filter_by_kind(self):
        conn = memory.connect()
        memory.record_feedback(conn, _record(kind="claim_category"), NOW)
        memory.record_feedback(conn, _record(kind="source_tier"), NOW)
        self.assertEqual(len(memory.list_feedback(conn, kind="source_tier")), 1)
        self.assertEqual(len(memory.list_feedback(conn, kind="claim_category")), 1)
        self.assertEqual(len(memory.list_feedback(conn)), 2)


class TestFeedbackDoesNotAffectScoring(unittest.TestCase):
    def _sources_and_claim(self):
        src = Source(
            id="S1", url="https://a.gov/x", tier=Tier.S, published_at="2026-06-25",
            scores=ScoreComponents(
                authority=1.0, recency=0.9, independence=1.0, traceability=1.0, corroboration=0.8,
            ),
        )
        claim = Claim(id="C1", text="rate is 7 percent", sources=["S1"])
        return [src], [claim]

    def test_scoring_identical_with_and_without_feedback(self):
        # Baseline: score with NO feedback rows present.
        sources_a, claims_a = self._sources_and_claim()
        score.score_sources(sources_a, NOW)
        score.score_claims(claims_a, sources_a)
        baseline = (sources_a[0].tier, sources_a[0].scores.composite, claims_a[0].confidence)

        # Now populate a feedback ledger, then score a fresh identical input.
        conn = memory.connect()
        for _ in range(10):
            memory.record_feedback(conn, _record(item_id="C1", human="false"), NOW)
        self.assertEqual(len(memory.list_feedback(conn)), 10)

        sources_b, claims_b = self._sources_and_claim()
        score.score_sources(sources_b, NOW)
        score.score_claims(claims_b, sources_b)
        after = (sources_b[0].tier, sources_b[0].scores.composite, claims_b[0].confidence)

        # Scoring never reads the ledger -> identical output.
        self.assertEqual(baseline, after)


if __name__ == "__main__":
    unittest.main()
