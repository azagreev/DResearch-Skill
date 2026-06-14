"""Phase 14 unit tests — anti-fit veto layer + auditable score breakdown.

Covers score.VetoRules / disqualify / score_source veto path, the breakdown
trace summing to composite, its round-trip through the model serializer, and the
report.py rendering of both the breakdown and the veto reason.

Run from the skill dir:  python -m unittest tests.test_phase14_scoring -v
"""

import unittest

from engine import score
from engine.model import (
    Route,
    Depth,
    ScoreComponents,
    Snapshot,
    Source,
    TaskFrame,
    Tier,
    snapshot_from_dict,
    snapshot_to_dict,
)
from engine.report import render_markdown

NOW = "2026-06-14T00:00:00Z"


def _src(**kw):
    base = dict(id="S1", url="https://good.example/a", title="", published_at="2026-06-14")
    base.update(kw)
    return Source(**base)


class TestVeto(unittest.TestCase):
    def test_domain_veto_overrides_high_tier(self):
        src = _src(
            url="https://content-farm.example/post",
            tier=Tier.S,  # would otherwise score very high
            scores=ScoreComponents(authority=1.0, independence=1.0, traceability=1.0, corroboration=1.0),
        )
        score.score_source(src, now_utc=NOW)
        self.assertEqual(src.tier, Tier.D)
        self.assertEqual(src.scores.composite, 0.0)
        self.assertEqual(src.scores.disqualifiers, ["domain:content-farm.example"])

    def test_pattern_veto_on_title(self):
        # Inject a custom rule to exercise the pattern-match mechanism (the bare
        # word "retracted" is deliberately NOT in DEFAULT_VETO — see score.py).
        rules = score.VetoRules(patterns=("retracted",))
        src = _src(title="Landmark study [RETRACTED]", tier=Tier.A)
        score.score_source(src, now_utc=NOW, veto=rules)
        self.assertEqual(src.tier, Tier.D)
        self.assertEqual(src.scores.composite, 0.0)
        self.assertEqual(src.scores.disqualifiers, ["pattern:retracted"])

    def test_default_veto_does_not_false_positive_on_discussed_marker(self):
        # A legitimate, high-authority source that merely *mentions* a retraction
        # or a sponsor must NOT be vetoed by the conservative DEFAULT_VETO.
        src = _src(
            url="https://journal.example/article",
            title="Review: the 2019 study was later retracted; trial sponsored by NIH",
            tier=Tier.A,
            scores=ScoreComponents(independence=0.8, traceability=0.8, corroboration=0.8),
        )
        score.score_source(src, now_utc=NOW)
        self.assertEqual(src.scores.disqualifiers, [])
        self.assertGreater(src.scores.composite, 0.0)

    def test_empty_vetorules_disables_veto(self):
        # An injected empty VetoRules() must NOT veto, even a known-bad host.
        src = _src(
            url="https://content-farm.example/post",
            tier=Tier.A,
            scores=ScoreComponents(independence=0.8, traceability=0.8, corroboration=0.8),
        )
        score.score_source(src, now_utc=NOW, veto=score.VetoRules())
        self.assertEqual(src.scores.disqualifiers, [])
        self.assertGreater(src.scores.composite, 0.0)
        self.assertNotEqual(src.tier, None)

    def test_disqualifiers_sorted_and_stable(self):
        # Two markers in one source -> reasons are sorted and de-duplicated.
        rules = score.VetoRules(patterns=("retracted", "sponsored by"))
        src = _src(
            url="https://x.example/p",
            title="Sponsored by Acme — RETRACTED notice",
        )
        reasons = score.disqualify(src, rules)
        self.assertEqual(reasons, sorted(reasons))
        self.assertIn("pattern:retracted", reasons)
        self.assertIn("pattern:sponsored by", reasons)
        # Pure: a second call gives the identical list.
        self.assertEqual(reasons, score.disqualify(src, rules))

    def test_non_vetoed_source_has_empty_disqualifiers(self):
        src = _src(tier=Tier.A)
        score.score_source(src, now_utc=NOW)
        self.assertEqual(src.scores.disqualifiers, [])

    def test_veto_clears_stale_breakdown(self):
        # A source scored non-vetoed first (breakdown populated), then re-scored
        # under a rule that now vetoes it, must not carry the stale breakdown.
        src = _src(url="https://x.example/p", title="ok", tier=Tier.A)
        score.score_source(src, now_utc=NOW)
        self.assertTrue(src.scores.breakdown)  # populated on the clean pass
        rules = score.VetoRules(domains=frozenset({"x.example"}))
        score.score_source(src, now_utc=NOW, veto=rules)
        self.assertEqual(src.tier, Tier.D)
        self.assertEqual(src.scores.breakdown, [])
        self.assertEqual(src.scores.disqualifiers, ["domain:x.example"])


class TestBreakdown(unittest.TestCase):
    def test_breakdown_sums_to_composite(self):
        src = _src(
            tier=Tier.B,
            scores=ScoreComponents(independence=0.7, traceability=0.5, corroboration=0.3),
        )
        score.score_source(src, now_utc=NOW)
        total = sum(contribution for _, contribution in src.scores.breakdown)
        self.assertAlmostEqual(total, src.scores.composite, delta=1e-9)

    def test_breakdown_label_order_and_count(self):
        src = _src(tier=Tier.A)
        score.score_source(src, now_utc=NOW)
        labels = [label for label, _ in src.scores.breakdown]
        self.assertEqual(
            labels,
            ["authority", "recency", "independence", "traceability", "corroboration"],
        )

    def test_breakdown_none_components_count_zero(self):
        # independence/traceability/corroboration unset -> their contribution 0.
        src = _src(tier=Tier.S, published_at=None)  # no recency either
        score.score_source(src, now_utc=NOW)
        contrib = dict(src.scores.breakdown)
        self.assertAlmostEqual(contrib["authority"], score.W_AUTHORITY * 1.0, delta=1e-9)
        self.assertEqual(contrib["recency"], 0.0)
        self.assertEqual(contrib["independence"], 0.0)
        self.assertAlmostEqual(
            sum(contrib.values()), src.scores.composite, delta=1e-9
        )

    def test_vetoed_source_breakdown_may_be_empty(self):
        src = _src(url="https://content-farm.example/p", tier=Tier.S)
        score.score_source(src, now_utc=NOW)
        self.assertEqual(src.scores.breakdown, [])
        self.assertEqual(src.scores.composite, 0.0)


class TestRoundTrip(unittest.TestCase):
    def _snap(self, sources):
        return Snapshot(
            run_id="R1",
            task_fingerprint="fp",
            task_frame=TaskFrame(question="Q?", route=Route.FOCUSED, depth=Depth.STANDARD),
            sources=sources,
        )

    def test_breakdown_round_trips(self):
        src = _src(
            tier=Tier.B,
            scores=ScoreComponents(independence=0.6, traceability=0.4, corroboration=0.2),
        )
        score.score_source(src, now_utc=NOW)
        original = [list(pair) for pair in src.scores.breakdown]

        snap = self._snap([src])
        restored = snapshot_from_dict(snapshot_to_dict(snap))
        rs = restored.sources[0].scores
        self.assertEqual(rs.breakdown, original)
        self.assertAlmostEqual(
            sum(c for _, c in rs.breakdown), rs.composite, delta=1e-9
        )

    def test_disqualifiers_round_trip(self):
        src = _src(url="https://content-farm.example/p", tier=Tier.S)
        score.score_source(src, now_utc=NOW)
        snap = self._snap([src])
        restored = snapshot_from_dict(snapshot_to_dict(snap))
        rs = restored.sources[0].scores
        self.assertEqual(rs.disqualifiers, ["domain:content-farm.example"])
        self.assertEqual(rs.composite, 0.0)


class TestReportRendering(unittest.TestCase):
    def _snap(self, sources):
        return Snapshot(
            run_id="R1",
            task_fingerprint="fp",
            task_frame=TaskFrame(question="Q?", route=Route.FOCUSED, depth=Depth.STANDARD),
            sources=sources,
        )

    def test_report_contains_breakdown_string(self):
        src = _src(tier=Tier.A)
        score.score_source(src, now_utc=NOW)
        out = render_markdown(self._snap([src]))
        self.assertIn("## Источники", out)
        self.assertIn("auth", out)
        self.assertIn("corrob", out)

    def test_report_contains_veto_reason(self):
        src = _src(url="https://content-farm.example/p", tier=Tier.S)
        score.score_source(src, now_utc=NOW)
        out = render_markdown(self._snap([src]))
        self.assertIn("veto", out)
        self.assertIn("domain:content-farm.example", out)


if __name__ == "__main__":
    unittest.main()
