"""Phase 5 unit tests — cross-run memory + eval metrics.

Run from the skill dir:  python -m unittest discover -s tests -t .
"""

import math
import unittest

from engine import eval as ev
from engine import memory
from engine.model import (
    Claim,
    ClaimCategory,
    Depth,
    Route,
    Snapshot,
    Source,
    TaskFrame,
    Tier,
)

NOW = "2026-06-30T00:00:00Z"


def make_snapshot():
    return Snapshot(
        run_id="r1",
        task_fingerprint="fp",
        task_frame=TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD),
        sources=[
            Source(id="S1", url="https://a.com/x", title="A", tier=Tier.S),
            Source(id="S2", url="https://b.com", tier=Tier.B),
        ],
        claims=[
            Claim(id="C1", text="Whoop costs 30000 rubles", category=ClaimCategory.VERIFIED, confidence=4),
            Claim(id="C2", text="Garmin battery lasts two weeks", category=ClaimCategory.OPINION, confidence=3),
        ],
    )


class TestMemory(unittest.TestCase):
    def test_record_dedupe_and_search(self):
        conn = memory.connect()  # in-memory
        first = memory.record_run(conn, make_snapshot(), NOW)
        self.assertEqual((first["new_sources"], first["new_claims"]), (2, 2))

        # same run again -> everything is a re-sighting, nothing new
        second = memory.record_run(conn, make_snapshot(), "2026-07-01T00:00:00Z")
        self.assertEqual((second["new_sources"], second["new_claims"]), (0, 0))
        self.assertEqual((second["updated_sources"], second["updated_claims"]), (2, 2))

        # cross-run "have we seen this?" — normalized URL + normalized claim text
        self.assertTrue(memory.seen_source(conn, "http://www.a.com/x/"))
        self.assertFalse(memory.seen_source(conn, "https://never.com"))
        self.assertTrue(memory.seen_claim(conn, "whoop costs 30000 rubles"))

        hits = memory.search_claims(conn, "Whoop")
        self.assertTrue(any("Whoop" in h["text"] for h in hits))

        stats = memory.get_stats(conn)
        self.assertEqual((stats["runs"], stats["sources"], stats["claims"]), (1, 2, 2))


class TestEval(unittest.TestCase):
    def test_precision_recall(self):
        self.assertEqual(ev.precision_at_k(["a", "b", "c"], {"a", "c"}, 2), 0.5)
        self.assertEqual(ev.recall_at_k(["a", "b", "c"], {"a", "c"}, 2), 0.5)

    def test_ndcg(self):
        ranked = ["a", "b", "c"]
        grades = {"a": 3, "b": 0, "c": 1}
        # dcg = 7/1 + 0 + 1/2 = 7.5 ; idcg (ideal grade order [3,1,0]) = 7 + 1/log2(3)
        idcg = 7.0 + 1.0 / math.log2(3)
        self.assertAlmostEqual(ev.ndcg_at_k(ranked, grades, 3), 7.5 / idcg, places=4)
        # perfect ranking -> 1.0
        self.assertAlmostEqual(ev.ndcg_at_k(["a", "c", "b"], grades, 3), 1.0, places=6)
        self.assertEqual(ev.ndcg_at_k(["a"], {}, 3), 0.0)

    def test_jaccard_retention_coverage(self):
        self.assertAlmostEqual(ev.jaccard({"a", "b"}, {"b", "c"}), 1 / 3)
        self.assertEqual(ev.jaccard(set(), set()), 1.0)
        self.assertEqual(ev.overlap_retention(["a", "b"], ["b", "c", "d"]), 0.5)
        self.assertEqual(ev.source_coverage(["a", "x"], {"a", "b"}), 0.5)


if __name__ == "__main__":
    unittest.main()
