"""Tests for bench.score — the exact DRACO scoring formula, hand-worked.

Reference rubric (positive_total = 10 + 20 + 10 = 40):
  factual-accuracy:  f1 (+10), f2 (+20), fneg (-100)
  citation-quality:  c1 (+10)
"""

from __future__ import annotations

import json
import unittest

from bench.draco import parse_rubric
from bench.score import aggregate, delta, score_rubric

_RUBRIC_JSON = json.dumps(
    {
        "id": "scoring-test",
        "sections": [
            {
                "id": "factual-accuracy",
                "title": "Factual Accuracy",
                "criteria": [
                    {"id": "f1", "weight": 10, "requirement": "r"},
                    {"id": "f2", "weight": 20, "requirement": "r"},
                    {"id": "fneg", "weight": -100, "requirement": "harmful claim present"},
                ],
            },
            {
                "id": "citation-quality",
                "title": "Citation Quality",
                "criteria": [{"id": "c1", "weight": 10, "requirement": "r"}],
            },
        ],
    }
)


def _rubric():
    return parse_rubric(_RUBRIC_JSON)


class ScoreFormulaTest(unittest.TestCase):
    def test_all_positive_met_no_penalty_is_100(self):
        v = {"f1": True, "f2": True, "c1": True, "fneg": False}
        s = score_rubric(_rubric(), v)
        self.assertAlmostEqual(s.raw, 40.0)
        self.assertAlmostEqual(s.positive_total, 40.0)
        self.assertAlmostEqual(s.normalized, 100.0)
        self.assertAlmostEqual(s.criteria_pass_rate, 100.0)
        self.assertEqual(s.n_negative_met, 0)
        self.assertEqual(s.n_unjudged, 0)

    def test_partial_positive(self):
        # f1 + c1 met (10+10=20), f2 missed, no penalty -> 20/40 = 50%
        v = {"f1": True, "f2": False, "c1": True, "fneg": False}
        s = score_rubric(_rubric(), v)
        self.assertAlmostEqual(s.raw, 20.0)
        self.assertAlmostEqual(s.normalized, 50.0)
        # unweighted: 2 of 3 positive criteria met
        self.assertAlmostEqual(s.criteria_pass_rate, 66.6667, places=3)

    def test_negative_criterion_penalises_and_clamps_to_zero(self):
        # all positive met (40) but harmful error present (-100) -> raw -60 -> clamp 0
        v = {"f1": True, "f2": True, "c1": True, "fneg": True}
        s = score_rubric(_rubric(), v)
        self.assertAlmostEqual(s.raw, -60.0)
        self.assertAlmostEqual(s.normalized, 0.0)
        # KEY divergence: unweighted pass rate is still 100% (all positives met),
        # yet the weighted score is 0 because of the penalty. Both are reported.
        self.assertAlmostEqual(s.criteria_pass_rate, 100.0)
        self.assertEqual(s.n_negative_met, 1)

    def test_per_axis_breakdown(self):
        v = {"f1": True, "f2": True, "c1": False, "fneg": True}
        s = score_rubric(_rubric(), v)
        self.assertEqual(set(s.axes), {"factual-accuracy", "citation-quality"})
        fa = s.axes["factual-accuracy"]
        # factual axis: positive_total 30, raw = 10 + 20 - 100 = -70 -> clamp 0
        self.assertAlmostEqual(fa.positive_total, 30.0)
        self.assertAlmostEqual(fa.raw, -70.0)
        self.assertAlmostEqual(fa.normalized, 0.0)
        self.assertEqual(fa.n_negative_met, 1)
        cit = s.axes["citation-quality"]
        # citation axis: c1 unmet -> 0
        self.assertAlmostEqual(cit.normalized, 0.0)
        self.assertAlmostEqual(cit.criteria_pass_rate, 0.0)

    def test_unjudged_criteria_counted_and_treated_unmet(self):
        # c1 has no verdict -> unjudged, treated as UNMET
        v = {"f1": True, "f2": True, "fneg": False}
        s = score_rubric(_rubric(), v)
        self.assertEqual(s.n_unjudged, 1)
        self.assertAlmostEqual(s.raw, 30.0)  # c1 contributes nothing
        self.assertAlmostEqual(s.normalized, 75.0)

    def test_no_positive_criteria_guard(self):
        only_neg = json.dumps(
            {
                "id": "neg-only",
                "sections": [
                    {
                        "id": "factual-accuracy",
                        "criteria": [{"id": "n1", "weight": -10, "requirement": "err"}],
                    }
                ],
            }
        )
        s_met = score_rubric(parse_rubric(only_neg), {"n1": True})
        self.assertAlmostEqual(s_met.normalized, 0.0)  # positive_total 0 -> guarded
        self.assertAlmostEqual(s_met.criteria_pass_rate, 0.0)
        self.assertEqual(s_met.n_negative_met, 1)


class AggregateTest(unittest.TestCase):
    def test_macro_mean_and_per_domain(self):
        r = _rubric()
        s1 = score_rubric(r, {"f1": True, "f2": True, "c1": True, "fneg": False},
                          task_id="t1", domain="Finance")   # 100
        s2 = score_rubric(r, {"f1": True, "f2": False, "c1": True, "fneg": False},
                          task_id="t2", domain="Law")        # 50
        summ = aggregate([s1, s2], arm="with_skill")
        self.assertEqual(summ.n_tasks, 2)
        self.assertAlmostEqual(summ.normalized_mean, 75.0)   # (100 + 50) / 2
        self.assertEqual(set(summ.per_domain), {"Finance", "Law"})
        self.assertAlmostEqual(summ.per_domain["Finance"], 100.0)
        self.assertIn("factual-accuracy", summ.per_axis)

    def test_delta_ab(self):
        r = _rubric()
        a = aggregate(
            [score_rubric(r, {"f1": True, "f2": False, "c1": False, "fneg": False},
                          task_id="t1", domain="Finance")],
            arm="no_skill",
        )
        b = aggregate(
            [score_rubric(r, {"f1": True, "f2": True, "c1": True, "fneg": False},
                          task_id="t1", domain="Finance")],
            arm="with_skill",
        )
        d = delta(a, b)
        self.assertEqual(d["arm_a"], "no_skill")
        self.assertEqual(d["arm_b"], "with_skill")
        # B (100) - A (25: only f1 of 40) = 75
        self.assertAlmostEqual(d["normalized_mean"], 75.0)
        self.assertGreater(d["per_axis"]["citation-quality"], 0.0)


if __name__ == "__main__":
    unittest.main()
