"""Phase 4 unit tests — factcheck (conflict resolution + verdict) and clustering.

Run from the skill dir:  python -m unittest discover -s tests -t .
"""

import unittest

from engine import cluster, factcheck
from engine.factcheck import Resolution
from engine.model import Claim, ClaimCategory, ClaimStatus, Source, Tier


def src(id_, tier=None, published=None, time_sensitive=False):
    return Source(id=id_, url="u", tier=tier, published_at=published, time_sensitive=time_sensitive)


class TestResolveConflict(unittest.TestCase):
    def test_basic(self):
        S, A = src("S", Tier.S), src("A", Tier.A)
        self.assertEqual(factcheck.resolve_conflict([], []), Resolution.NO_EVIDENCE)
        self.assertEqual(factcheck.resolve_conflict([S], []), Resolution.SUPPORTED)
        self.assertEqual(factcheck.resolve_conflict([], [S]), Resolution.CONTRADICTED)
        self.assertEqual(factcheck.resolve_conflict([S], [A]), Resolution.SUPPORTED)   # tier
        self.assertEqual(factcheck.resolve_conflict([A], [S]), Resolution.CONTRADICTED)

    def test_freshness_then_count_then_disputed(self):
        b_new = src("Bn", Tier.B, published="2026-06-10")
        b_old = src("Bo", Tier.B, published="2026-06-01")
        self.assertEqual(factcheck.resolve_conflict([b_new], [b_old]), Resolution.SUPPORTED)
        # equal tier, no dates -> count
        self.assertEqual(
            factcheck.resolve_conflict([src("B1", Tier.B), src("B2", Tier.B)], [src("B3", Tier.B)]),
            Resolution.SUPPORTED,
        )
        # equal tier, equal count, no dates -> disputed
        self.assertEqual(
            factcheck.resolve_conflict([src("B1", Tier.B)], [src("B2", Tier.B)]),
            Resolution.DISPUTED,
        )


class TestClassify(unittest.TestCase):
    def _by_id(self, *sources):
        return {s.id: s for s in sources}

    def test_unverified_false_opinion_verified(self):
        by_id = self._by_id(src("S", Tier.S), src("A", Tier.A), src("B1", Tier.B), src("B2", Tier.B))
        self.assertEqual(
            factcheck.classify_claim(Claim(id="C", text="x"), by_id), ClaimCategory.UNVERIFIED
        )
        self.assertEqual(
            factcheck.classify_claim(Claim(id="C", text="x", sources=["S"]), by_id),
            ClaimCategory.VERIFIED,
        )
        self.assertEqual(
            factcheck.classify_claim(Claim(id="C", text="x", sources=["B1"], contradicting_sources=["S"]), by_id),
            ClaimCategory.FALSE,
        )
        self.assertEqual(
            factcheck.classify_claim(Claim(id="C", text="x", sources=["B1"], contradicting_sources=["B2"]), by_id),
            ClaimCategory.OPINION,  # disputed
        )

    def test_outdated_when_fresher_contradiction(self):
        sup = src("sup", Tier.A, published="2026-01-01", time_sensitive=True)
        con = src("con", Tier.C, published="2026-06-01")  # lower tier but newer
        by_id = self._by_id(sup, con)
        claim = Claim(id="C", text="x", sources=["sup"], contradicting_sources=["con"])
        self.assertEqual(factcheck.classify_claim(claim, by_id), ClaimCategory.OUTDATED)

    def test_model_category_respected_when_supported(self):
        by_id = self._by_id(src("S", Tier.S))
        claim = Claim(id="C", text="x", sources=["S"])
        self.assertEqual(
            factcheck.classify_claim(claim, by_id, model_category=ClaimCategory.INCOMPLETE),
            ClaimCategory.INCOMPLETE,
        )


class TestFactcheckClaim(unittest.TestCase):
    def test_status_and_confidence(self):
        by_id = {s.id: s for s in [src("S", Tier.S), src("S2", Tier.S), src("B", Tier.B)]}
        verified = factcheck.factcheck_claim(Claim(id="C1", text="x", sources=["S", "S2"], confidence=5), by_id)
        self.assertEqual((verified.category, verified.status, verified.confidence),
                         (ClaimCategory.VERIFIED, ClaimStatus.CONFIRMED, 5))
        false = factcheck.factcheck_claim(
            Claim(id="C2", text="y", sources=["B"], contradicting_sources=["S"], confidence=3), by_id
        )
        self.assertEqual((false.category, false.status, false.confidence),
                         (ClaimCategory.FALSE, ClaimStatus.REJECTED, 1))


class TestCluster(unittest.TestCase):
    def test_groups_reps_and_ids(self):
        c1 = Claim(id="C1", text="Whoop 4.0 costs 30000 rubles on CDEK", sources=["S1"], confidence=4)
        c2 = Claim(id="C2", text="Whoop 4.0 price on CDEK is 30000 rubles", sources=["S2"], confidence=3)
        c3 = Claim(id="C3", text="Garmin Fenix battery lasts two weeks", sources=["S3"], confidence=5)
        clusters = cluster.cluster_claims([c1, c2, c3], sim_threshold=0.4)
        self.assertEqual(len(clusters), 2)
        first = next(k for k in clusters if "C1" in k.claim_ids)
        self.assertEqual(set(first.claim_ids), {"C1", "C2"})
        self.assertEqual(first.representative_ids[0], "C1")   # highest confidence seeds MMR
        self.assertIsNone(first.uncertainty)                  # two distinct sources
        self.assertEqual(c1.cluster_id, c2.cluster_id)
        self.assertNotEqual(c1.cluster_id, c3.cluster_id)
        lone = next(k for k in clusters if "C3" in k.claim_ids)
        self.assertEqual(lone.uncertainty, "thin-evidence")

    def test_single_source_uncertainty(self):
        d1 = Claim(id="D1", text="alpha beta gamma delta topic", sources=["X"], confidence=2)
        d2 = Claim(id="D2", text="alpha beta gamma delta topic extra", sources=["X"], confidence=2)
        clusters = cluster.cluster_claims([d1, d2], sim_threshold=0.4)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].uncertainty, "single-source")


if __name__ == "__main__":
    unittest.main()
