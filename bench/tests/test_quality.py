"""Tests for bench.quality — the BINEVAL-style report self-grader.

These exercise the static question bank, the deterministic aggregation math, the
graceful-degradation (unjudged) path, and the full deterministic + injected-judge
scorecard pipeline over the real engine's demo snapshot — no LLM, no network.

The critical property is NON-VACUITY (AC3): a "good" judge must score strictly and
substantially higher than a "bad" judge, proving the metric discriminates quality
rather than always passing.
"""

from __future__ import annotations

import unittest

from bench.draco import AXES
from bench.trust.metrics import demo_scenario
from bench.quality.questions import (
    DETERMINISTIC_CHECKERS,
    Polarity,
    QKind,
    QUESTION_BANK,
    validate_bank,
)
from bench.quality.grader import (
    answer_deterministic,
    grade,
    quality_scorecard,
)

# DRACO axis weights (mirror grader._AXIS_WEIGHTS) for independent hand-computation.
_AXIS_WEIGHTS = {
    "factual-accuracy": 0.52,
    "breadth-and-depth-of-analysis": 0.22,
    "presentation-quality": 0.14,
    "citation-quality": 0.12,
}


def _good_answer_fn(question, context):
    """A "good report" judge: POSITIVE -> True (property present),
    NEGATIVE -> False (error absent). Both map to good-score 1.0."""
    if question.polarity is Polarity.POSITIVE:
        return (True, "good")
    return (False, "good")


def _bad_answer_fn(question, context):
    """A "bad report" judge: POSITIVE -> False (property missing),
    NEGATIVE -> True (error present). Both map to good-score 0.0."""
    if question.polarity is Polarity.POSITIVE:
        return (False, "bad")
    return (True, "bad")


def _none_answer_fn(question, context):
    """A judge that abstains on every question (graceful-degradation path)."""
    return (None, "abstain")


def _raising_answer_fn(question, context):
    """A judge that always raises — must be swallowed as unjudged, never crash."""
    raise RuntimeError("judge exploded")


class QuestionBankTest(unittest.TestCase):
    """AC4 — structural integrity of the static question bank."""

    def test_validate_bank_passes(self):
        # validate_bank() also runs at import; calling it here makes the contract
        # an explicit assertion of this suite.
        validate_bank()  # must not raise

    def test_ids_unique(self):
        ids = [q.id for q in QUESTION_BANK]
        self.assertEqual(len(ids), len(set(ids)), "duplicate question ids")
        self.assertEqual(len(QUESTION_BANK), 16, "expected 16 questions (4 per axis)")

    def test_every_axis_is_a_draco_axis(self):
        for q in QUESTION_BANK:
            self.assertIn(q.axis, AXES, f"{q.id}: axis {q.axis!r} not in AXES")

    def test_deterministic_questions_match_checker_registry(self):
        det_ids = {q.id for q in QUESTION_BANK if q.kind is QKind.DETERMINISTIC}
        checker_ids = set(DETERMINISTIC_CHECKERS)
        # Every DETERMINISTIC question has a checker, and vice-versa (bijection).
        self.assertEqual(det_ids, checker_ids)
        self.assertEqual(len(checker_ids), 8, "expected 8 deterministic checkers")
        for fn in DETERMINISTIC_CHECKERS.values():
            self.assertTrue(callable(fn))

    def test_all_four_axes_have_questions(self):
        covered = {q.axis for q in QUESTION_BANK}
        self.assertEqual(covered, set(AXES))
        for axis in AXES:
            n = sum(1 for q in QUESTION_BANK if q.axis == axis)
            self.assertGreaterEqual(n, 1, f"axis {axis} has no questions")


class AggregationMathTest(unittest.TestCase):
    """Hand-computed per_axis + overall, respecting polarity (incl. NEGATIVE)."""

    def test_grade_matches_hand_computation(self):
        # Controlled verdicts over known ids (polarity from the bank):
        #   fa1  POSITIVE True  -> good 1.0   (factual-accuracy)
        #   fa2  NEGATIVE False -> good 1.0   (error ABSENT)
        #   dep3 POSITIVE True  -> good 1.0   (breadth)
        #   dep4 POSITIVE False -> good 0.0
        #   pres1 POSITIVE True -> good 1.0   (presentation)
        #   cit3 NEGATIVE True  -> good 0.0   (error PRESENT) (citation)
        verdicts = {
            "fa1": True,
            "fa2": False,
            "dep3": True,
            "dep4": False,
            "pres1": True,
            "cit3": True,
        }
        d = grade(verdicts).as_dict()

        expected_per_axis = {
            "factual-accuracy": 1.0,                 # mean(1.0, 1.0)
            "breadth-and-depth-of-analysis": 0.5,    # mean(1.0, 0.0)
            "presentation-quality": 1.0,             # mean(1.0)
            "citation-quality": 0.0,                 # mean(0.0)
        }
        self.assertEqual(d["per_axis"], expected_per_axis)

        # overall = weighted mean renormalised over the (here: all 4) judged axes.
        num = sum(_AXIS_WEIGHTS[a] * v for a, v in expected_per_axis.items())
        den = sum(_AXIS_WEIGHTS[a] for a in expected_per_axis)
        self.assertAlmostEqual(d["overall"], round(num / den, 4), places=4)
        self.assertEqual(d["overall"], 0.77)

        # coverage: 6 judged, 5 of them deterministic (fa2,dep3,dep4,pres1,cit3),
        # 10 unjudged (the rest of the 16-question bank).
        self.assertEqual(
            d["coverage"], {"judged": 6, "deterministic": 5, "unjudged": 10}
        )

    def test_negative_polarity_both_directions(self):
        # Same NEGATIVE question (cit3) flips good-score with its verdict.
        error_present = grade({"cit3": True}).as_dict()   # error present -> bad
        error_absent = grade({"cit3": False}).as_dict()   # error absent  -> good
        self.assertEqual(error_present["per_axis"]["citation-quality"], 0.0)
        self.assertEqual(error_absent["per_axis"]["citation-quality"], 1.0)
        self.assertEqual(error_present["overall"], 0.0)
        self.assertEqual(error_absent["overall"], 1.0)


class UnjudgedExclusionTest(unittest.TestCase):
    """AC7 — None verdicts / missing ids / abstaining or raising judges are
    excluded from the denominator and counted as unjudged; never crashes."""

    def setUp(self):
        self.snapshot, _md = demo_scenario().run()

    def test_none_verdict_excluded_from_denominator(self):
        # fa1 judged good, fa4 explicitly None -> only fa1 counts in the axis.
        d = grade({"fa1": True, "fa4": None}).as_dict()
        self.assertEqual(d["per_axis"]["factual-accuracy"], 1.0)
        # fa4 (None) plus every unmentioned id counts as unjudged.
        self.assertEqual(d["coverage"]["judged"], 1)
        self.assertEqual(d["coverage"]["unjudged"], len(QUESTION_BANK) - 1)

    def test_missing_id_is_unjudged(self):
        d = grade({}).as_dict()
        self.assertEqual(d["per_axis"], {})
        self.assertEqual(d["overall"], 0.0)
        self.assertEqual(d["coverage"]["judged"], 0)
        self.assertEqual(d["coverage"]["unjudged"], len(QUESTION_BANK))

    def test_abstaining_judge_does_not_raise_and_excludes_judgment(self):
        d = quality_scorecard(self.snapshot, _none_answer_fn)
        # All JUDGMENT questions abstained -> only deterministic ones are judged.
        n_judgment = sum(1 for q in QUESTION_BANK if q.kind is QKind.JUDGMENT)
        self.assertEqual(d["coverage"]["unjudged"], n_judgment)
        self.assertEqual(d["coverage"]["judged"], len(QUESTION_BANK) - n_judgment)
        self.assertEqual(d["coverage"]["deterministic"], 8)

    def test_raising_judge_is_swallowed(self):
        # Must not propagate the RuntimeError; degrades to unjudged for judgments.
        d = quality_scorecard(self.snapshot, _raising_answer_fn)
        n_judgment = sum(1 for q in QUESTION_BANK if q.kind is QKind.JUDGMENT)
        self.assertEqual(d["coverage"]["unjudged"], n_judgment)
        self.assertEqual(d["coverage"]["deterministic"], 8)


class ScorecardShapeTest(unittest.TestCase):
    """AC1 — full pipeline over the real demo snapshot returns the canonical shape."""

    def setUp(self):
        self.snapshot, _md = demo_scenario().run()

    def test_scorecard_has_all_required_keys(self):
        d = quality_scorecard(self.snapshot, _good_answer_fn)
        self.assertEqual(
            set(d.keys()), {"per_axis", "overall", "coverage", "questions"}
        )
        self.assertEqual(
            set(d["coverage"].keys()), {"judged", "deterministic", "unjudged"}
        )
        # 8 deterministic checkers all run against the demo snapshot.
        self.assertEqual(d["coverage"]["deterministic"], 8)

    def test_scorecard_values_in_unit_interval(self):
        d = quality_scorecard(self.snapshot, _good_answer_fn)
        self.assertGreaterEqual(d["overall"], 0.0)
        self.assertLessEqual(d["overall"], 1.0)
        for axis, v in d["per_axis"].items():
            self.assertIn(axis, AXES)
            self.assertGreaterEqual(v, 0.0, f"{axis} below 0")
            self.assertLessEqual(v, 1.0, f"{axis} above 1")

    def test_question_rows_well_formed(self):
        d = quality_scorecard(self.snapshot, _good_answer_fn)
        self.assertEqual(len(d["questions"]), len(QUESTION_BANK))
        for row in d["questions"]:
            self.assertEqual(
                set(row.keys()),
                {"id", "axis", "kind", "polarity", "verdict", "explanation"},
            )
            self.assertIn(row["verdict"], (True, False, None))


class DeterminismTest(unittest.TestCase):
    """AC2 — same snapshot + same answer_fn -> identical scorecard dict."""

    def setUp(self):
        self.snapshot, _md = demo_scenario().run()

    def test_two_runs_are_equal(self):
        a = quality_scorecard(self.snapshot, _good_answer_fn)
        b = quality_scorecard(self.snapshot, _good_answer_fn)
        self.assertEqual(a, b)

    def test_deterministic_verdicts_stable(self):
        self.assertEqual(
            answer_deterministic(self.snapshot), answer_deterministic(self.snapshot)
        )


class NonVacuousTest(unittest.TestCase):
    """AC3 (critical) — the metric must DISCRIMINATE quality, not always pass."""

    def setUp(self):
        self.snapshot, _md = demo_scenario().run()

    def test_good_judge_beats_bad_judge_on_real_snapshot(self):
        good = quality_scorecard(self.snapshot, _good_answer_fn)
        bad = quality_scorecard(self.snapshot, _bad_answer_fn)
        # Strict separation: flipping every JUDGMENT answer lowers the score.
        self.assertGreater(good["overall"], bad["overall"])
        # The good judge must not be dragged below the bad one on any axis either.
        for axis in good["per_axis"]:
            self.assertGreaterEqual(good["per_axis"][axis], bad["per_axis"][axis])

    def test_fully_controlled_verdicts_span_the_full_range(self):
        # With every question (deterministic ids included) forced good vs bad via
        # grade(), the metric spans the full [0,1] range: high>0.8, low<0.2.
        good_v = {q.id: (q.polarity is Polarity.POSITIVE) for q in QUESTION_BANK}
        bad_v = {q.id: (q.polarity is not Polarity.POSITIVE) for q in QUESTION_BANK}
        good = grade(good_v).as_dict()
        bad = grade(bad_v).as_dict()
        self.assertGreater(good["overall"], bad["overall"])
        self.assertGreater(good["overall"], 0.8, "good report should score high")
        self.assertLess(bad["overall"], 0.2, "bad report should score low")
        self.assertEqual(good["overall"], 1.0)
        self.assertEqual(bad["overall"], 0.0)
        # Every deterministic checker's question is judged in this construction.
        self.assertEqual(good["coverage"]["deterministic"], 8)
        self.assertEqual(bad["coverage"]["deterministic"], 8)


class PerAxisOmissionTest(unittest.TestCase):
    """An axis with zero judged questions is dropped from per_axis and excluded
    from the overall renormalisation.

    NOTE: via the full `quality_scorecard` pipeline this is unreachable for a
    healthy snapshot, because every one of the four axes owns >=1 DETERMINISTIC
    question whose checker returns a non-None verdict (the demo snapshot has
    claims + sources, so all 8 checkers fire). We therefore exercise the omission
    through the bare `grade()` path (which treats unmentioned ids as unjudged) and
    additionally assert the renormalisation invariant: `overall` equals the
    weighted mean over exactly the present axes.
    """

    def test_unjudged_axis_omitted_and_overall_renormalised(self):
        # Judge ONLY factual-accuracy and citation-quality; leave breadth and
        # presentation entirely unjudged.
        verdicts = {"fa1": True, "fa2": False, "cit1": True, "cit3": False}
        d = grade(verdicts).as_dict()

        present = set(d["per_axis"])
        self.assertEqual(present, {"factual-accuracy", "citation-quality"})
        self.assertNotIn("breadth-and-depth-of-analysis", d["per_axis"])
        self.assertNotIn("presentation-quality", d["per_axis"])

        # Renormalisation invariant: overall = weighted mean over PRESENT axes only.
        num = sum(_AXIS_WEIGHTS[a] * d["per_axis"][a] for a in present)
        den = sum(_AXIS_WEIGHTS[a] for a in present)
        self.assertAlmostEqual(d["overall"], round(num / den, 4), places=4)
        # Both judged axes are perfect here, so the renormalised overall is 1.0
        # (not dragged down by the two omitted axes).
        self.assertEqual(d["per_axis"]["factual-accuracy"], 1.0)
        self.assertEqual(d["per_axis"]["citation-quality"], 1.0)
        self.assertEqual(d["overall"], 1.0)


class CliVerdictCoercionTest(unittest.TestCase):
    """The `grade --verdicts` path must preserve JSON null as None (unjudged),
    not coerce it to False. Regression for the bool(None)->False bug."""

    def test_json_null_preserved_as_unjudged(self):
        from bench.quality.__main__ import _coerce_verdicts

        coerced = _coerce_verdicts({"fa1": None, "fa2": True, "cit1": False})
        self.assertIsNone(coerced["fa1"])          # null -> None, NOT False
        self.assertIs(coerced["fa2"], True)
        self.assertIs(coerced["cit1"], False)

        # A null verdict must land in `unjudged`, never scored as "not met".
        d = grade(coerced).as_dict()
        ids = {q["id"]: q["verdict"] for q in d["questions"]}
        self.assertIsNone(ids["fa1"])
        self.assertEqual(d["coverage"]["unjudged"],
                         sum(1 for v in ids.values() if v is None))


if __name__ == "__main__":
    unittest.main()
