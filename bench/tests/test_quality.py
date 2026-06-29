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


# ---------------------------------------------------------------------------
# Module-level set used by CheckerTestCoverageMetaGuard (defined before the
# test class so the guard itself can reference it as a plain name).
# ---------------------------------------------------------------------------
_TESTED_CHECKERS: frozenset = frozenset({
    "fa2",
    "fa3",
    "dep3",
    "dep4",
    "pres1",
    "cit1",
    "cit2",
    "cit3",
})


class DeterministicCheckerRoundTripTest(unittest.TestCase):
    """Standing guard for every deterministic checker's snapshot->verdict mapping.

    Each checker is exercised with:
      (a) a snapshot where the checked condition IS present / property IS met,
      (b) a snapshot where it is NOT,
      (c) an empty / not-applicable snapshot that should yield None.

    For NEGATIVE-polarity checkers, "condition present" returns True; for
    POSITIVE-polarity checkers, "property met" returns True.  The cit3 cases
    are the critical regression guard against the polarity-inversion bug (#12).
    """

    @classmethod
    def setUpClass(cls):
        # Import engine types after bench.trust._engine has put the engine on
        # sys.path (questions.py does the same bootstrap at import time).
        import copy
        from bench.trust._engine import Snapshot, Claim, ClaimRole
        from engine.model import Source, Tier, ClaimCategory

        cls._copy = copy
        cls._Snapshot = Snapshot
        cls._Claim = Claim
        cls._ClaimRole = ClaimRole
        cls._Source = Source
        cls._Tier = Tier
        cls._ClaimCategory = ClaimCategory

        # Build a base snapshot from the demo scenario (runs the real pipeline
        # once; all 8 checkers return non-None on this snapshot).
        cls._base_snapshot, _ = demo_scenario().run()

    # ------------------------------------------------------------------
    # Helper: fresh deep-copy of the demo snapshot with all claims/sources.
    # ------------------------------------------------------------------
    def _snap(self):
        return self._copy.deepcopy(self._base_snapshot)

    # ------------------------------------------------------------------
    # fa2: NEGATIVE — True iff an OWN finding has category "false"
    # ------------------------------------------------------------------
    def test_fa2_error_present(self):
        """fa2 returns True when >=1 own finding is categorized FALSE."""
        from bench.quality.questions import _check_no_false_own_finding
        snap = self._snap()
        # Force the first own finding to FALSE category.
        own = [c for c in snap.claims if c.role == self._ClaimRole.OWN_FINDING]
        self.assertTrue(own, "demo snapshot must have own findings")
        own[0].category = self._ClaimCategory.FALSE
        self.assertIs(_check_no_false_own_finding(snap), True)

    def test_fa2_error_absent(self):
        """fa2 returns False when no own finding is FALSE."""
        from bench.quality.questions import _check_no_false_own_finding
        snap = self._snap()
        own = [c for c in snap.claims if c.role == self._ClaimRole.OWN_FINDING]
        self.assertTrue(own)
        for c in own:
            c.category = self._ClaimCategory.VERIFIED  # clean
        self.assertIs(_check_no_false_own_finding(snap), False)

    def test_fa2_none_on_empty(self):
        """fa2 returns None when there are no own findings at all."""
        from bench.quality.questions import _check_no_false_own_finding
        snap = self._snap()
        snap.claims = []
        self.assertIsNone(_check_no_false_own_finding(snap))

    # ------------------------------------------------------------------
    # fa3: NEGATIVE — True iff a reportable finding has category "unverified"
    # ------------------------------------------------------------------
    def test_fa3_error_present(self):
        """fa3 returns True when a cited own finding is UNVERIFIED."""
        from bench.quality.questions import _check_unverified_in_findings
        snap = self._snap()
        # Pick a reportable finding (must have >=1 source).
        reportable = [
            c for c in snap.claims
            if c.role == self._ClaimRole.OWN_FINDING and len(c.sources) >= 1
        ]
        self.assertTrue(reportable, "demo snapshot must have reportable findings")
        reportable[0].category = self._ClaimCategory.UNVERIFIED
        self.assertIs(_check_unverified_in_findings(snap), True)

    def test_fa3_error_absent(self):
        """fa3 returns False when no reportable finding is UNVERIFIED."""
        from bench.quality.questions import _check_unverified_in_findings
        snap = self._snap()
        for c in snap.claims:
            if c.role == self._ClaimRole.OWN_FINDING and len(c.sources) >= 1:
                c.category = self._ClaimCategory.VERIFIED
        self.assertIs(_check_unverified_in_findings(snap), False)

    def test_fa3_none_on_no_reportable(self):
        """fa3 returns None when there are no reportable (cited) own findings."""
        from bench.quality.questions import _check_unverified_in_findings
        snap = self._snap()
        # Remove all source citations from own findings so none are reportable.
        for c in snap.claims:
            if c.role == self._ClaimRole.OWN_FINDING:
                c.sources = []
        self.assertIsNone(_check_unverified_in_findings(snap))

    # ------------------------------------------------------------------
    # dep3: POSITIVE — True iff >=4 distinct source tiers present
    # ------------------------------------------------------------------
    def test_dep3_property_met(self):
        """dep3 returns True when >=4 distinct tiers are present."""
        from bench.quality.questions import _check_source_type_diversity
        snap = self._snap()
        # Add sources with 4 distinct tiers (S, A, B, C).
        for tier, sid in [
            (self._Tier.S, "X1"),
            (self._Tier.A, "X2"),
            (self._Tier.B, "X3"),
            (self._Tier.C, "X4"),
        ]:
            snap.sources.append(
                self._Source(id=sid, url=f"https://example.com/{sid}", tier=tier)
            )
        self.assertIs(_check_source_type_diversity(snap), True)

    def test_dep3_property_unmet(self):
        """dep3 returns False when fewer than 4 distinct tiers are present."""
        from bench.quality.questions import _check_source_type_diversity
        snap = self._snap()
        # Collapse all sources to a single tier.
        for s in snap.sources:
            s.tier = self._Tier.A
        # Ensure fewer than 4 distinct tiers (only A).
        self.assertIs(_check_source_type_diversity(snap), False)

    def test_dep3_none_on_empty(self):
        """dep3 returns None when there are no sources."""
        from bench.quality.questions import _check_source_type_diversity
        snap = self._snap()
        snap.sources = []
        self.assertIsNone(_check_source_type_diversity(snap))

    # ------------------------------------------------------------------
    # dep4: POSITIVE — True iff >=1 Tier S source present
    # ------------------------------------------------------------------
    def test_dep4_property_met(self):
        """dep4 returns True when at least one Tier S source exists."""
        from bench.quality.questions import _check_primary_source_present
        snap = self._snap()
        # Ensure there is at least one Tier S source.
        snap.sources.append(
            self._Source(id="PRIMXYZ", url="https://sec.gov/primary", tier=self._Tier.S)
        )
        self.assertIs(_check_primary_source_present(snap), True)

    def test_dep4_property_unmet(self):
        """dep4 returns False when no Tier S source exists."""
        from bench.quality.questions import _check_primary_source_present
        snap = self._snap()
        for s in snap.sources:
            s.tier = self._Tier.B  # downgrade all to non-primary
        self.assertIs(_check_primary_source_present(snap), False)

    def test_dep4_none_on_empty(self):
        """dep4 returns None when there are no sources."""
        from bench.quality.questions import _check_primary_source_present
        snap = self._snap()
        snap.sources = []
        self.assertIsNone(_check_primary_source_present(snap))

    # ------------------------------------------------------------------
    # pres1: POSITIVE — True iff every claim confidence is in 1..5
    # ------------------------------------------------------------------
    def test_pres1_property_met(self):
        """pres1 returns True when all claims have confidence in 1..5."""
        from bench.quality.questions import _check_all_claims_confidence_scored
        snap = self._snap()
        for c in snap.claims:
            c.confidence = 3  # valid
        self.assertIs(_check_all_claims_confidence_scored(snap), True)

    def test_pres1_property_unmet(self):
        """pres1 returns False when any claim has confidence out of 1..5."""
        from bench.quality.questions import _check_all_claims_confidence_scored
        snap = self._snap()
        self.assertTrue(snap.claims)
        snap.claims[0].confidence = 0  # out-of-range
        self.assertIs(_check_all_claims_confidence_scored(snap), False)

    def test_pres1_none_on_empty(self):
        """pres1 returns None when there are no claims at all."""
        from bench.quality.questions import _check_all_claims_confidence_scored
        snap = self._snap()
        snap.claims = []
        self.assertIsNone(_check_all_claims_confidence_scored(snap))

    # ------------------------------------------------------------------
    # cit1: POSITIVE — True iff every OWN finding has >=1 source
    # ------------------------------------------------------------------
    def test_cit1_property_met(self):
        """cit1 returns True when every own finding has >=1 source."""
        from bench.quality.questions import _check_all_findings_cited
        snap = self._snap()
        # Ensure every own finding cites at least one source.
        src_id = snap.sources[0].id if snap.sources else "S1"
        for c in snap.claims:
            if c.role == self._ClaimRole.OWN_FINDING and not c.sources:
                c.sources = [src_id]
        self.assertIs(_check_all_findings_cited(snap), True)

    def test_cit1_property_unmet(self):
        """cit1 returns False when at least one own finding has no sources."""
        from bench.quality.questions import _check_all_findings_cited
        snap = self._snap()
        own = [c for c in snap.claims if c.role == self._ClaimRole.OWN_FINDING]
        self.assertTrue(own)
        own[0].sources = []  # strip citations
        self.assertIs(_check_all_findings_cited(snap), False)

    def test_cit1_none_on_empty(self):
        """cit1 returns None when there are no own findings."""
        from bench.quality.questions import _check_all_findings_cited
        snap = self._snap()
        snap.claims = []
        self.assertIsNone(_check_all_findings_cited(snap))

    # ------------------------------------------------------------------
    # cit2: POSITIVE — True iff every source has a non-None tier
    # ------------------------------------------------------------------
    def test_cit2_property_met(self):
        """cit2 returns True when every source carries a tier."""
        from bench.quality.questions import _check_sources_tier_scored
        snap = self._snap()
        for s in snap.sources:
            s.tier = self._Tier.A  # all tiered
        self.assertIs(_check_sources_tier_scored(snap), True)

    def test_cit2_property_unmet(self):
        """cit2 returns False when any source is missing a tier."""
        from bench.quality.questions import _check_sources_tier_scored
        snap = self._snap()
        self.assertTrue(snap.sources)
        snap.sources[0].tier = None  # un-tiered
        self.assertIs(_check_sources_tier_scored(snap), False)

    def test_cit2_none_on_empty(self):
        """cit2 returns None when there are no sources."""
        from bench.quality.questions import _check_sources_tier_scored
        snap = self._snap()
        snap.sources = []
        self.assertIsNone(_check_sources_tier_scored(snap))

    # ------------------------------------------------------------------
    # cit3: NEGATIVE — True iff a claim cites a source id absent from snapshot
    # This is the critical regression guard for bug #12 (polarity inversion).
    # ------------------------------------------------------------------
    def test_cit3_dangling_citation_returns_true(self):
        """cit3 MUST return True when a dangling citation exists (error present).

        This is the critical regression guard: if the polarity is ever inverted
        (returning False for dangling / True for clean), this test fails
        immediately, catching bug #12 before it ships.
        """
        from bench.quality.questions import _check_claims_reference_real_sources
        snap = self._snap()
        self.assertTrue(snap.claims, "fixture must have claims")
        # Append a bogus source id that does not exist in snap.sources.
        snap.claims[0].sources.append("NONEXISTENT_SOURCE_ID_XYZ")
        result = _check_claims_reference_real_sources(snap)
        self.assertIs(result, True,
                      "dangling citation must return True (error IS present); "
                      "got False — polarity is INVERTED (bug #12)")

    def test_cit3_clean_citations_return_false(self):
        """cit3 MUST return False when all citations resolve (error absent).

        Complementary guard: a clean snapshot must score as error-absent (False),
        not as error-present (True).
        """
        from bench.quality.questions import _check_claims_reference_real_sources
        snap = self._snap()
        known = {s.id for s in snap.sources}
        # Verify all existing citations are clean (no dangling refs in demo).
        for c in snap.claims:
            for sid in c.sources:
                self.assertIn(sid, known, f"demo snapshot has unexpected dangling ref: {sid}")
        result = _check_claims_reference_real_sources(snap)
        self.assertIs(result, False,
                      "clean snapshot must return False (error IS absent); "
                      "got True — polarity is INVERTED (bug #12)")

    def test_cit3_none_on_empty_claims(self):
        """cit3 returns None when there are no claims at all."""
        from bench.quality.questions import _check_claims_reference_real_sources
        snap = self._snap()
        snap.claims = []
        self.assertIsNone(_check_claims_reference_real_sources(snap))


class CheckerTestCoverageMetaGuard(unittest.TestCase):
    """Meta-test: every deterministic checker must have a round-trip test.

    `_TESTED_CHECKERS` (module-level frozenset above) must equal exactly
    the set of keys in DETERMINISTIC_CHECKERS.  Adding a new checker without
    updating _TESTED_CHECKERS (and writing the actual round-trip tests) will
    fail this guard.
    """

    def test_all_checkers_have_round_trip_tests(self):
        checker_ids = set(DETERMINISTIC_CHECKERS)
        self.assertEqual(
            _TESTED_CHECKERS,
            checker_ids,
            f"Coverage mismatch.\n"
            f"  In DETERMINISTIC_CHECKERS but not in _TESTED_CHECKERS: "
            f"{sorted(checker_ids - _TESTED_CHECKERS)}\n"
            f"  In _TESTED_CHECKERS but not in DETERMINISTIC_CHECKERS: "
            f"{sorted(_TESTED_CHECKERS - checker_ids)}",
        )

    def test_tested_checkers_is_frozenset(self):
        """The sentinel must be a frozenset (immutable; accidental mutation is a bug)."""
        self.assertIsInstance(_TESTED_CHECKERS, frozenset)

    def test_tested_checkers_count(self):
        """There are exactly 8 deterministic checkers; guard against silent additions."""
        self.assertEqual(len(_TESTED_CHECKERS), 8)


class GradeCoercionBoundaryTest(unittest.TestCase):
    """Boundary coverage for bench.quality.__main__._coerce_verdicts.

    CliVerdictCoercionTest covers the basic null->None regression.  This class
    adds complementary boundary cases: true, false, missing keys, and
    non-bool truthy/falsey values.  No overlap with the existing test.
    """

    def setUp(self):
        from bench.quality.__main__ import _coerce_verdicts
        self._coerce = _coerce_verdicts

    # --- null -> None (unjudged) -------------------------------------------
    def test_null_becomes_none(self):
        """JSON null must coerce to Python None (not False)."""
        result = self._coerce({"q1": None})
        self.assertIsNone(result["q1"])

    # --- true -> True, false -> False (identity for booleans) ---------------
    def test_true_becomes_true(self):
        result = self._coerce({"q1": True})
        self.assertIs(result["q1"], True)

    def test_false_becomes_false(self):
        result = self._coerce({"q1": False})
        self.assertIs(result["q1"], False)

    # --- missing keys: _coerce_verdicts only touches keys in raw dict --------
    def test_missing_keys_not_invented(self):
        """Keys absent from the raw dict must not appear in the coerced result."""
        result = self._coerce({"fa1": True})
        self.assertNotIn("fa2", result)
        self.assertNotIn("cit3", result)

    # --- non-bool truthy value: 1 -> True, 0 -> False -----------------------
    def test_truthy_int_becomes_true(self):
        """A truthy non-bool (e.g. 1) should coerce to True, not None."""
        result = self._coerce({"q1": 1})
        self.assertIs(result["q1"], True)
        self.assertIsNotNone(result["q1"])  # must NOT be treated as unjudged

    def test_falsey_int_zero_becomes_false(self):
        """A falsey non-bool (e.g. 0) should coerce to False, not None."""
        result = self._coerce({"q1": 0})
        self.assertIs(result["q1"], False)
        self.assertIsNotNone(result["q1"])  # must NOT be treated as unjudged

    # --- mixed bag: null, bool, and truthy together -------------------------
    def test_mixed_coercion(self):
        """All three variants can coexist in one call."""
        result = self._coerce({"a": None, "b": True, "c": False, "d": 1})
        self.assertIsNone(result["a"])
        self.assertIs(result["b"], True)
        self.assertIs(result["c"], False)
        self.assertIs(result["d"], True)

    # --- null lands in unjudged (integration with grade()) ------------------
    def test_null_verdict_lands_in_unjudged(self):
        """After coercion a null entry must increase the unjudged count, not the
        judged count — integration check that None really flows through grade()."""
        coerced = self._coerce({"fa1": True, "fa2": None})
        d = grade(coerced).as_dict()
        # fa2 is None -> unjudged; fa1 is True -> judged
        self.assertEqual(d["coverage"]["judged"], 1)
        ids = {q["id"]: q["verdict"] for q in d["questions"]}
        self.assertIsNone(ids["fa2"])


if __name__ == "__main__":
    unittest.main()
