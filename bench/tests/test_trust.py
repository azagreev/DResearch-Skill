"""Tests for bench.trust.metrics — deterministic trust metrics over the real engine.

These run the actual engine.run_pipeline on a labeled synthetic fixture and
assert the skill's value-prop invariants (determinism, anti-hallucination
suppression, citation completeness, checkpoint fidelity) — no LLM, no network.
"""

from __future__ import annotations

import unittest

from bench.trust.metrics import (
    Scenario,
    checkpoint_fidelity,
    citation_completeness,
    cost_efficiency,
    demo_scenario,
    determinism,
    false_suppression_rate,
    suppression_recall,
)
from bench.trust._engine import ClaimRole


class TrustMetricsTest(unittest.TestCase):
    def setUp(self):
        self.s = demo_scenario()

    def test_determinism(self):
        # Two runs on identical inputs render byte-identically (no clock/random).
        self.assertTrue(determinism(self.s))

    def test_suppression_recall_perfect(self):
        # The unsupported (0-source) claim is routed UNVERIFIED -> excluded.
        self.assertEqual(suppression_recall(self.s), 1.0)

    def test_no_false_suppression(self):
        # Both well-supported claims survive into the report.
        self.assertEqual(false_suppression_rate(self.s), 0.0)

    def test_citation_completeness(self):
        c = citation_completeness(self.s)
        self.assertEqual(c["rendered_findings"], 2.0)         # C1, C3 survive; C2 suppressed
        self.assertEqual(c["claims_cited_fraction"], 1.0)      # every surviving finding cited
        self.assertEqual(c["sources_tiered_fraction"], 1.0)    # every source tier-scored

    def test_checkpoint_fidelity(self):
        self.assertTrue(checkpoint_fidelity(self.s))

    def test_cost_efficiency_passthrough(self):
        out = cost_efficiency(10, 5.0, 2.0)
        self.assertAlmostEqual(out["cost_per_item"], 0.5)
        self.assertAlmostEqual(out["items_per_sec"], 5.0)

    def test_metric_catches_a_regression(self):
        # Non-vacuous: a scenario whose "unsupported" claim is given a source
        # would FAIL suppression (recall < 1) — proving the metric measures real
        # engine behavior, not a constant.
        leaky = Scenario(
            name="leaky",
            now="2026-06-14T00:00:00Z",
            question="q",
            raw_sources=[{"url": "https://www.sec.gov/x", "tier": "S",
                          "scores": {"authority": 0.9, "independence": 0.8,
                                     "traceability": 0.9, "corroboration": 0.7}}],
            claim_specs=[("C1", "SHOULD_HAVE_BEEN_SUPPRESSED", ["S1"], 4, ClaimRole.OWN_FINDING)],
            expect_present=frozenset(),
            expect_absent=frozenset({"C1"}),  # mislabeled: it IS supported, so it survives
        )
        self.assertLess(suppression_recall(leaky), 1.0)  # metric correctly reports the leak


if __name__ == "__main__":
    unittest.main()
