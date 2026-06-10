"""Phase 2 unit tests — dedupe, rank (RRF + authority), freshness.

Run from the skill dir:  python -m unittest discover -s tests -t .
"""

import unittest

from engine import dedupe, freshness, rank
from engine.model import Source, Tier


class TestDedupe(unittest.TestCase):
    def test_normalize_url(self):
        self.assertEqual(
            dedupe.normalize_url("http://www.Example.com/path/?utm_source=x&a=1#frag"),
            "https://example.com/path?a=1",
        )
        # m./trailing slash/fragment collapse; tracking key dropped
        self.assertEqual(
            dedupe.normalize_url("https://m.example.com/p/?fbclid=zzz"),
            "https://example.com/p",
        )

    def test_exact_url_and_near_dup(self):
        s1 = Source(id="S1", url="https://example.com/a", title="Whoop 4.0 review and price")
        s2 = Source(id="S2", url="https://www.example.com/a/", title="totally different title")  # same URL
        s3 = Source(id="S3", url="https://other.com/x", title="Whoop 4.0 review and price")       # near-dup text
        s4 = Source(id="S4", url="https://z.com/q", title="Garmin watch comparison guide")        # distinct
        kept, merges = dedupe.dedupe_sources([s1, s2, s3, s4], threshold=0.85)
        self.assertEqual({k.id for k in kept}, {"S1", "S4"})
        self.assertIn(("S1", "S2"), merges)  # exact-URL
        self.assertIn(("S1", "S3"), merges)  # near-dup text

    def test_distinct_kept(self):
        a = Source(id="A", url="https://a.com", title="apples and oranges")
        b = Source(id="B", url="https://b.com", title="quantum chromodynamics primer")
        kept, merges = dedupe.dedupe_sources([a, b])
        self.assertEqual(len(kept), 2)
        self.assertEqual(merges, [])

    def test_jaccard_edges(self):
        self.assertEqual(dedupe.jaccard(set(), set()), 1.0)
        self.assertEqual(dedupe.jaccard({"a"}, set()), 0.0)
        self.assertAlmostEqual(dedupe.jaccard({"a", "b"}, {"b", "c"}), 1 / 3)


class TestRank(unittest.TestCase):
    def test_rrf_order_and_ties(self):
        streams = {"q1": ["A", "B", "C"], "q2": ["B", "A", "D"]}
        order = [i for i, _ in rank.reciprocal_rank_fusion(streams)]
        # A and B tie -> id asc; C and D tie -> id asc
        self.assertEqual(order, ["A", "B", "C", "D"])

    def test_weights_shift_order(self):
        streams = {"q1": ["A"], "q2": ["B"]}
        order = [i for i, _ in rank.reciprocal_rank_fusion(streams, weights={"q2": 2.0})]
        self.assertEqual(order[0], "B")

    def test_authority_weight(self):
        self.assertEqual(rank.authority_weight(Tier.S), 1.0)
        self.assertEqual(rank.authority_weight(Tier.D), 0.5)
        self.assertEqual(rank.authority_weight(None), 0.6)

    def test_rank_sources_authority_tilt(self):
        # equal RRF (each tops one stream), but B is Tier S vs A Tier D -> B first.
        sources = [
            Source(id="A", url="u1", tier=Tier.D),
            Source(id="B", url="u2", tier=Tier.S),
            Source(id="C", url="u3", tier=Tier.S),  # absent from streams -> score 0, last
        ]
        ranked = rank.rank_sources(sources, {"q1": ["A"], "q2": ["B"]})
        self.assertEqual([s.id for s, _ in ranked], ["B", "A", "C"])
        self.assertEqual(ranked[-1][1], 0.0)


class TestFreshness(unittest.TestCase):
    def test_now_is_one(self):
        self.assertEqual(freshness.recency_score("2026-06-30T00:00:00Z", "2026-06-30T00:00:00Z"), 1.0)

    def test_half_life(self):
        # 30 days old, half_life 30 -> 0.5
        self.assertAlmostEqual(
            freshness.recency_score("2026-05-31T00:00:00Z", "2026-06-30T00:00:00Z", half_life_days=30),
            0.5, places=4,
        )
        # 60 days old -> 0.25
        self.assertAlmostEqual(
            freshness.recency_score("2026-05-01T00:00:00Z", "2026-06-30T00:00:00Z", half_life_days=30),
            0.25, places=4,
        )

    def test_missing_and_future(self):
        self.assertEqual(freshness.recency_score(None, "2026-06-30T00:00:00Z"), 0.5)
        self.assertEqual(freshness.recency_score("not-a-date", "2026-06-30T00:00:00Z"), 0.5)
        self.assertEqual(freshness.recency_score("2027-01-01", "2026-06-30T00:00:00Z"), 1.0)

    def test_parse_iso(self):
        self.assertIsNotNone(freshness.parse_iso("2026-06-01"))
        self.assertIsNotNone(freshness.parse_iso("2026-06-01T10:00:00Z"))
        self.assertIsNone(freshness.parse_iso(""))
        self.assertIsNone(freshness.parse_iso("garbage"))


if __name__ == "__main__":
    unittest.main()
