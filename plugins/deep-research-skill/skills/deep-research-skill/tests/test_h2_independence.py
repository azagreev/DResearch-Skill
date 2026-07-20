"""H2 — computed source independence (hyperresearch reuse).

Traceability: docs/TRACE_HYPERRESEARCH.md (AC2.1..AC2.6).

'Syndication != consensus': N reworded reprints of one story cluster into ~1
independent voice (each scored 1/cluster_size), filling the independence
component (weight 0.20) so a syndicated source scores lower composite -> lower
tier -> less confidence, with NO change to the confidence ladder. Also an
independence tiebreaker in resolve_conflict (SKILL.md:104). Deterministic,
offline, stdlib-only.

Run from the skill dir:
    python -m unittest tests.test_h2_independence -v
"""

import unittest

from engine import independence
from engine.factcheck import Resolution, resolve_conflict
from engine.model import Claim, ScoreComponents, Source, Tier

_BASE = "Центральный банк повысил ключевую ставку до пятнадцати процентов из-за инфляции и роста цен на товары."
_REPRINT2 = "Центральный банк повысил ключевую ставку до пятнадцати процентов из-за инфляции и роста цен."
_REPRINT3 = "Центральный банк поднял ключевую ставку до пятнадцати процентов из-за инфляции и роста цен на товары."
_DISTINCT = "Погода в регионе на выходных ожидается солнечной, температура около двадцати градусов тепла без осадков вовсе."


def _src(sid, text, url=None):
    return Source(id=sid, url=url or f"https://example.test/{sid}", tier=Tier.B,
                  extract={"content": text})


def _reprints():
    return [_src("S1", _BASE), _src("S2", _REPRINT2), _src("S3", _REPRINT3), _src("S4", _DISTINCT)]


class Ac21DeterministicOrderIndependentTest(unittest.TestCase):
    def test_deterministic(self):
        s = _reprints()
        self.assertEqual(independence.compute_independence(s), independence.compute_independence(s))

    def test_order_independent_per_id(self):
        s = _reprints()
        a = independence.compute_independence(s)
        b = independence.compute_independence(list(reversed(s)))
        self.assertEqual(a, b)


class Ac22ReprintsClusterTest(unittest.TestCase):
    def test_reprints_share_one_vote_distinct_is_full(self):
        scores = independence.compute_independence(_reprints())
        # S1/S2/S3 are the same story reworded -> cluster of 3 -> 1/3 each.
        self.assertAlmostEqual(scores["S1"], 1.0 / 3)
        self.assertAlmostEqual(scores["S2"], 1.0 / 3)
        self.assertAlmostEqual(scores["S3"], 1.0 / 3)
        # S4 is a different story -> fully independent.
        self.assertAlmostEqual(scores["S4"], 1.0)


class Ac23ConsensusStrengthTest(unittest.TestCase):
    def test_reprints_count_as_about_one(self):
        srcs = _reprints()
        independence.apply_independence(srcs)
        by_id = {s.id: s for s in srcs}
        # A claim citing all three reprints has consensus ~1.0, not 3.0.
        c = Claim(id="C1", text="ставка выросла", sources=["S1", "S2", "S3"])
        self.assertAlmostEqual(independence.consensus_strength(c, by_id), 1.0)

    def test_distinct_sources_accumulate(self):
        srcs = [_src("A", _DISTINCT), _src("B", "Совсем другой текст про экономику региона и бюджет города."),
                _src("C", "Ещё один независимый материал о транспортной реформе в стране целиком.")]
        independence.apply_independence(srcs)
        by_id = {s.id: s for s in srcs}
        c = Claim(id="C2", text="x", sources=["A", "B", "C"])
        self.assertAlmostEqual(independence.consensus_strength(c, by_id), 3.0)


class Ac22NoFalseSyndicationTest(unittest.TestCase):
    def test_distinct_same_topic_articles_stay_independent(self):
        # Two DIFFERENT-wording articles on the same topic must NOT cluster
        # (guards against threshold drift causing false syndication).
        a = _src("A", "Инфляция ускорилась в марте, аналитики связывают это с ростом цен на энергоносители.")
        b = _src("B", "Годовой рост потребительских цен замедлился по данным ведомства на фоне укрепления рубля.")
        scores = independence.compute_independence([a, b])
        self.assertAlmostEqual(scores["A"], 1.0)
        self.assertAlmostEqual(scores["B"], 1.0)


class Ac24ThresholdAndSafeDefaultTest(unittest.TestCase):
    def test_threshold_configurable(self):
        # An impossibly high threshold clusters nothing -> everyone independent.
        scores = independence.compute_independence(_reprints(), sim_threshold=0.999)
        self.assertTrue(all(abs(v - 1.0) < 1e-9 for v in scores.values()))

    def test_apply_does_not_overwrite_explicit_independence(self):
        s = _src("S1", _BASE)
        s.scores = ScoreComponents(independence=0.42)
        independence.apply_independence([s, _src("S2", _REPRINT2), _src("S3", _REPRINT3)])
        # explicit value preserved (byte-identity for callers that set it)
        self.assertEqual(s.scores.independence, 0.42)


class Ac25ResolveConflictTiebreakerTest(unittest.TestCase):
    def test_independence_breaks_tie_when_tier_and_freshness_equal(self):
        sup = [_src("A1", _DISTINCT)]; sup[0].scores.independence = 0.9
        con = [_src("B1", "иное")]; con[0].scores.independence = 0.2
        # equal tier (B), no dates -> freshness neutral; equal count -> would be
        # DISPUTED, but independence now breaks the tie for the supporting side.
        self.assertEqual(resolve_conflict(sup, con), Resolution.SUPPORTED)

    def test_no_independence_signal_falls_through_to_count(self):
        # Both sides lack an independence signal -> unchanged legacy behavior
        # (equal tier/freshness/count -> DISPUTED). Byte-safe.
        sup = [_src("A1", "x")]
        con = [_src("B1", "y")]
        self.assertEqual(resolve_conflict(sup, con), Resolution.DISPUTED)


if __name__ == "__main__":
    unittest.main()
