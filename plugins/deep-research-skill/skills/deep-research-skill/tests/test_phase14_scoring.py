"""Phase 14 unit tests — auditable score breakdown.

Covers the breakdown trace summing to composite, its round-trip through the model
serializer, and report.py rendering of the breakdown. (The anti-fit veto layer
was removed in v1.5 as inert; the `disqualifiers` field is kept for checkpoint
backward-compat and is covered by a direct round-trip test below.)

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

    def test_disqualifiers_field_round_trips(self):
        # The veto layer was removed in v1.5, but the `disqualifiers` FIELD is kept
        # for checkpoint backward-compat — an old snapshot carrying it must still
        # round-trip losslessly (the field is no longer populated by scoring).
        src = _src(scores=ScoreComponents(disqualifiers=["legacy:domain"]))
        snap = self._snap([src])
        restored = snapshot_from_dict(snapshot_to_dict(snap))
        self.assertEqual(restored.sources[0].scores.disqualifiers, ["legacy:domain"])


class TestReportRendering(unittest.TestCase):
    def _snap(self, sources):
        return Snapshot(
            run_id="R1",
            task_fingerprint="fp",
            task_frame=TaskFrame(question="Q?", route=Route.FOCUSED, depth=Depth.STANDARD),
            sources=sources,
        )

    def test_breakdown_omitted_by_default_present_with_verbose(self):
        # v1.5: the per-source score breakdown is decoration, omitted from the lean
        # default report and shown only under verbose=True.
        src = _src(tier=Tier.A)
        score.score_source(src, now_utc=NOW)
        lean = render_markdown(self._snap([src]))
        self.assertIn("## Источники", lean)
        self.assertNotIn("corrob", lean)
        verbose = render_markdown(self._snap([src]), verbose=True)
        self.assertIn("auth", verbose)
        self.assertIn("corrob", verbose)


if __name__ == "__main__":
    unittest.main()
