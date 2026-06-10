"""Phase 3 unit tests — composite score, tier thresholds, claim confidence.

Run from the skill dir:  python -m unittest discover -s tests -t .
"""

import unittest

from engine import score
from engine.model import Claim, ScoreComponents, Source, Tier


def sc(a, r, i, t, c):
    return ScoreComponents(authority=a, recency=r, independence=i, traceability=t, corroboration=c)


class TestComposite(unittest.TestCase):
    def test_worked_examples(self):
        # Values from source_authority_framework.md §3.4.
        self.assertAlmostEqual(score.composite_score(sc(1.0, 0.9, 1.0, 1.0, 0.8)), 0.955, places=4)
        self.assertAlmostEqual(score.composite_score(sc(0.9, 0.8, 0.8, 0.8, 0.8)), 0.83, places=4)
        self.assertAlmostEqual(score.composite_score(sc(0.8, 0.9, 0.8, 0.7, 0.6)), 0.79, places=4)
        self.assertAlmostEqual(score.composite_score(sc(0.4, 0.9, 0.7, 0.4, 0.2)), 0.565, places=4)

    def test_none_components_count_zero(self):
        self.assertAlmostEqual(score.composite_score(ScoreComponents(authority=1.0)), 0.30, places=4)

    def test_clamped(self):
        self.assertEqual(score.composite_score(sc(2.0, 2.0, 2.0, 2.0, 2.0)), 1.0)


class TestTier(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(score.tier_for_score(0.955), Tier.S)
        self.assertEqual(score.tier_for_score(0.90), Tier.S)
        self.assertEqual(score.tier_for_score(0.89), Tier.A)
        self.assertEqual(score.tier_for_score(0.79), Tier.A)   # per §3.5 table (not the example label)
        self.assertEqual(score.tier_for_score(0.75), Tier.A)
        self.assertEqual(score.tier_for_score(0.74), Tier.B)
        self.assertEqual(score.tier_for_score(0.565), Tier.B)  # per §3.5 table (not the example label)
        self.assertEqual(score.tier_for_score(0.55), Tier.B)
        self.assertEqual(score.tier_for_score(0.54), Tier.C)
        self.assertEqual(score.tier_for_score(0.35), Tier.C)
        self.assertEqual(score.tier_for_score(0.34), Tier.D)
        self.assertEqual(score.tier_for_score(0.0), Tier.D)

    def test_authority_component(self):
        self.assertEqual(score.authority_component(Tier.S), 1.0)
        self.assertEqual(score.authority_component(Tier.A), 0.85)
        self.assertEqual(score.authority_component(Tier.D), 0.15)
        self.assertEqual(score.authority_component(None), 0.0)


class TestScoreSource(unittest.TestCase):
    def test_fills_recency_composite_tier(self):
        src = Source(
            id="S1", url="u", published_at="2026-06-30",
            scores=ScoreComponents(authority=1.0, independence=1.0, traceability=1.0, corroboration=0.8),
        )
        score.score_source(src, now_utc="2026-06-30T00:00:00Z")
        self.assertEqual(src.scores.recency, 1.0)                 # published == now -> 1.0
        self.assertAlmostEqual(src.scores.composite, 0.98, places=4)
        self.assertEqual(src.tier, Tier.S)

    def test_no_now_leaves_recency_none(self):
        src = Source(id="S2", url="u", scores=ScoreComponents(authority=0.4, independence=0.2))
        score.score_source(src)
        self.assertIsNone(src.scores.recency)
        self.assertEqual(src.tier, Tier.D)  # composite 0.30*0.4 + 0.20*0.2 = 0.16


class TestClaimConfidence(unittest.TestCase):
    def setUp(self):
        self.by_id = {
            "S": Source(id="S", url="u", tier=Tier.S),
            "S2": Source(id="S2", url="u", tier=Tier.S),
            "A1": Source(id="A1", url="u", tier=Tier.A),
            "A2": Source(id="A2", url="u", tier=Tier.A),
            "B1": Source(id="B1", url="u", tier=Tier.B),
            "B2": Source(id="B2", url="u", tier=Tier.B),
            "C1": Source(id="C1", url="u", tier=Tier.C),
            "D1": Source(id="D1", url="u", tier=Tier.D),
        }

    def conf(self, *ids):
        return score.claim_confidence(Claim(id="C", text="x", sources=list(ids)), self.by_id)

    def test_ladder(self):
        self.assertEqual(self.conf("S", "S2"), 5)
        self.assertEqual(self.conf("S", "A1"), 4)
        self.assertEqual(self.conf("A1", "A2"), 4)
        self.assertEqual(self.conf("A1"), 3)
        self.assertEqual(self.conf("B1", "B2"), 3)
        self.assertEqual(self.conf("B1"), 2)
        self.assertEqual(self.conf("C1"), 2)
        self.assertEqual(self.conf("D1"), 1)
        self.assertEqual(self.conf(), 1)

    def test_score_claims_sets_confidence(self):
        claims = [Claim(id="C1", text="x", sources=["S", "S2"]), Claim(id="C2", text="y", sources=["D1"])]
        score.score_claims(claims, list(self.by_id.values()))
        self.assertEqual(claims[0].confidence, 5)
        self.assertEqual(claims[1].confidence, 1)


if __name__ == "__main__":
    unittest.main()
