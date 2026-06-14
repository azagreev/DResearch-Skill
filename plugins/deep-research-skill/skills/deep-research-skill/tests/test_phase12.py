"""Phase 12 unit tests — golden corpus CI regression + activation eval +
migration + goal violations + stop signal.

Run from the skill dir:  python -m unittest tests.test_phase12 -v

Coverage (per frozen contract):
  MIGRATION  snapshot_from_dict accepts a v1.0 dict missing gate/goal fields and
             produces a valid snapshot (validate_snapshot == []); a future-version
             dict raises ValueError.
  GOAL       TaskFrame round-trips done_condition + forbidden_actions through
             snapshot_to_dict / snapshot_from_dict; goal_violations reports
             a forbidden action present in open_items and is empty otherwise.
  STOP       state.should_stop returns the correct reason string or None for
             budget-exhausted, done-condition-met, and in-progress snapshots.
  CI         evals/ci_regression.run_regression() passes on the golden corpus at
             baseline thresholds, and fails (passed=False) with a deliberately
             too-high threshold.
  ACTIVATION evals/activation_corpus.json loads and has non-empty lists.

Conventions mirror tests/test_phase7.py: stdlib unittest, fixed NOW, no
clock/random. Builder A owns model.py + state.py; tests that depend on fields
not yet added skip cleanly via hasattr guards.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Path helpers — resolve corpus files relative to this file, not cwd.
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).parent
_SKILL_DIR = _TESTS_DIR.parent
_EVALS_DIR = _SKILL_DIR / "evals"

# Ensure the skill dir is on sys.path so `engine` is importable.
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

# ---------------------------------------------------------------------------
# Detect which frozen-contract additions are already present in model / state.
# ---------------------------------------------------------------------------
from engine import model as _model
from engine import state as _state
from engine.model import (
    Budget,
    Claim,
    ClaimCategory,
    Depth,
    Route,
    Snapshot,
    SubTask,
    SubTaskStatus,
    SubTaskType,
    TaskFrame,
    snapshot_from_dict,
    snapshot_to_dict,
    validate_snapshot,
)

# Phase-12 additions land in Builder A's model.py drop.
# NOTE: use the dataclass field set, not hasattr(TaskFrame, ...): a
# default_factory field (forbidden_actions) has NO class-level attribute, so
# hasattr would falsely report it absent and skip the whole class.
_TF_FIELDS = set(TaskFrame.__dataclass_fields__)
_HAS_MIGRATE = hasattr(_model, "_migrate")
_HAS_DONE_CONDITION = "done_condition" in _TF_FIELDS
_HAS_FORBIDDEN_ACTIONS = "forbidden_actions" in _TF_FIELDS
_HAS_GOAL_VIOLATIONS = hasattr(_model, "goal_violations")
_HAS_SHOULD_STOP = hasattr(_state, "should_stop")

NOW = "2026-06-30T00:00:00Z"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_task_frame() -> TaskFrame:
    return TaskFrame(question="test query", route=Route.FOCUSED, depth=Depth.STANDARD)


def _minimal_snap(**kw) -> Snapshot:
    """Build a minimal valid Snapshot, optionally overriding fields."""
    defaults: Dict[str, Any] = dict(
        run_id="r1",
        task_fingerprint="fp",
        task_frame=_base_task_frame(),
    )
    defaults.update(kw)
    return Snapshot(**defaults)


def _v10_dict(**overrides) -> Dict[str, Any]:
    """A hand-crafted v1.0 checkpoint dict WITHOUT the Phase-12 gate/goal fields.

    This is what an old checkpoint written before Phase 12 would look like.  The
    migration path must fill missing fields with safe defaults before loading.
    """
    d: Dict[str, Any] = {
        "run_id": "run-old",
        "task_fingerprint": "fp-old",
        "checkpoint_version": "1.0",
        "task_frame": {
            "question": "old question",
            "route": "B",
            "depth": "Standard",
            "scope": [],
            "acceptance_criteria": [],
            "language": "ru",
            # Intentionally OMIT done_condition and forbidden_actions.
        },
        "stage": "",
        "phase_completed": 0,
        "next_phase": 0,
        # Intentionally OMIT sources_screened, extraction_table_complete,
        # citations_verified (the three gate signals added post-v1.0).
        "budget": {},
        "subtasks": [],
        "sources": [],
        "claims": [],
        "clusters": [],
        "open_items": [],
        "resume_instruction": "",
    }
    d.update(overrides)
    return d


# ===========================================================================
# MIGRATION tests
# ===========================================================================

class TestMigration(unittest.TestCase):
    """AC12-5 MIGRATION: model._migrate + snapshot_from_dict version handling."""

    def test_v10_dict_loads_without_new_fields(self):
        """A v1.0 dict missing gate signals + goal fields loads cleanly.

        Once Builder A lands _migrate and CHECKPOINT_VERSION="1.1", this test
        exercises the full migration path.  Until then, v1.0 is the current
        version and snapshot_from_dict already handles missing gate fields via
        .get() with defaults — so the test passes either way.
        """
        payload = _v10_dict()
        snap = snapshot_from_dict(payload)
        errors = validate_snapshot(snap)
        self.assertEqual(errors, [], f"Unexpected validation errors: {errors}")

    def test_v10_missing_gate_signals_default_correctly(self):
        """Gate signals absent from a v1.0 dict must default to falsy values."""
        payload = _v10_dict()
        snap = snapshot_from_dict(payload)
        # sources_screened, extraction_table_complete, citations_verified
        self.assertEqual(snap.sources_screened, 0)
        self.assertFalse(snap.extraction_table_complete)
        self.assertFalse(snap.citations_verified)

    def test_future_version_raises(self):
        """A checkpoint whose version is greater than CHECKPOINT_VERSION must
        raise ValueError — never silently load a format from the future.
        """
        payload = _v10_dict(checkpoint_version="99.0")
        with self.assertRaises(ValueError):
            snapshot_from_dict(payload)

    @unittest.skipUnless(_HAS_MIGRATE, "model._migrate not yet present (Builder A)")
    def test_migrate_1_0_to_1_1_fills_defaults(self):
        """_migrate upgrades a 1.0 payload to 1.1 by filling missing fields."""
        payload = _v10_dict()
        migrated = _model._migrate(payload)
        # After migration the dict must have gate signals at their defaults.
        self.assertIn("sources_screened", migrated)
        self.assertEqual(migrated["sources_screened"], 0)
        self.assertIn("extraction_table_complete", migrated)
        self.assertFalse(migrated["extraction_table_complete"])
        self.assertIn("citations_verified", migrated)
        self.assertFalse(migrated["citations_verified"])

    @unittest.skipUnless(_HAS_MIGRATE, "model._migrate not yet present (Builder A)")
    def test_migrate_future_version_raises(self):
        """_migrate raises ValueError for a version greater than CHECKPOINT_VERSION."""
        payload = _v10_dict(checkpoint_version="99.0")
        with self.assertRaises(ValueError):
            _model._migrate(payload)

    @unittest.skipUnless(_HAS_MIGRATE, "model._migrate not yet present (Builder A)")
    def test_snapshot_from_dict_calls_migrate_first(self):
        """snapshot_from_dict on a 1.0 dict (post-Builder-A) goes through _migrate
        and still yields a valid snapshot."""
        payload = _v10_dict()
        # If _migrate is present the CHECKPOINT_VERSION is expected to be "1.1",
        # but the payload is "1.0" — migration handles the version bump.
        snap = snapshot_from_dict(payload)
        self.assertEqual(validate_snapshot(snap), [])


# ===========================================================================
# GOAL tests (TaskFrame.done_condition / forbidden_actions + goal_violations)
# ===========================================================================

@unittest.skipUnless(
    _HAS_DONE_CONDITION and _HAS_FORBIDDEN_ACTIONS and _HAS_GOAL_VIOLATIONS,
    "TaskFrame.done_condition / forbidden_actions / goal_violations not yet present (Builder A)",
)
class TestGoalFields(unittest.TestCase):
    """AC12-5 GOAL: TaskFrame fields + goal_violations pure function."""

    def _make_tf(self, done_condition=None, forbidden_actions=None) -> TaskFrame:
        """Build a TaskFrame with the Phase-12 goal fields set."""
        tf = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD)
        if done_condition is not None:
            tf.done_condition = done_condition
        if forbidden_actions is not None:
            tf.forbidden_actions = list(forbidden_actions)
        return tf

    def test_taskframe_roundtrip_done_condition(self):
        """done_condition survives snapshot_to_dict -> snapshot_from_dict."""
        tf = self._make_tf(done_condition="all_claims_verified")
        snap = _minimal_snap(task_frame=tf)
        d = snapshot_to_dict(snap)
        snap2 = snapshot_from_dict(d)
        self.assertEqual(snap2.task_frame.done_condition, "all_claims_verified")

    def test_taskframe_roundtrip_forbidden_actions(self):
        """forbidden_actions list survives snapshot_to_dict -> snapshot_from_dict."""
        tf = self._make_tf(forbidden_actions=["web_search", "paid_provider"])
        snap = _minimal_snap(task_frame=tf)
        d = snapshot_to_dict(snap)
        snap2 = snapshot_from_dict(d)
        self.assertEqual(snap2.task_frame.forbidden_actions, ["web_search", "paid_provider"])

    def test_taskframe_defaults_are_preserved(self):
        """done_condition defaults to None; forbidden_actions defaults to []."""
        tf = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD)
        self.assertIsNone(tf.done_condition)
        self.assertEqual(tf.forbidden_actions, [])

    def test_goal_violations_empty_when_no_forbidden(self):
        """goal_violations returns [] when forbidden_actions is empty."""
        tf = self._make_tf(forbidden_actions=[])
        snap = _minimal_snap(task_frame=tf, open_items=["web_search used"])
        self.assertEqual(_model.goal_violations(snap), [])

    def test_goal_violations_empty_when_no_match(self):
        """goal_violations returns [] when no forbidden tag appears in open_items."""
        tf = self._make_tf(forbidden_actions=["paid_provider"])
        snap = _minimal_snap(task_frame=tf, open_items=["web_search used", "review needed"])
        self.assertEqual(_model.goal_violations(snap), [])

    def test_goal_violations_detects_breach(self):
        """goal_violations returns a non-empty list when a forbidden action tag
        appears in any open_items entry (substring / exact match per contract).
        """
        tf = self._make_tf(forbidden_actions=["paid_provider"])
        snap = _minimal_snap(task_frame=tf, open_items=["paid_provider invoked at phase 2"])
        violations = _model.goal_violations(snap)
        self.assertTrue(len(violations) > 0, "Expected at least one violation")

    def test_goal_violations_multiple_forbidden_one_breach(self):
        """Only the breached forbidden actions appear in violations list."""
        tf = self._make_tf(forbidden_actions=["paid_provider", "web_search"])
        snap = _minimal_snap(task_frame=tf, open_items=["paid_provider invoked"])
        violations = _model.goal_violations(snap)
        # At least one violation for paid_provider; web_search not breached.
        self.assertTrue(any("paid_provider" in v for v in violations))

    def test_goal_violations_is_pure(self):
        """goal_violations does not mutate the snapshot."""
        tf = self._make_tf(forbidden_actions=["web_search"])
        snap = _minimal_snap(task_frame=tf, open_items=["web_search used"])
        original_open_items = list(snap.open_items)
        _model.goal_violations(snap)
        self.assertEqual(snap.open_items, original_open_items)


# ===========================================================================
# STOP tests (state.should_stop)
# ===========================================================================

@unittest.skipUnless(_HAS_SHOULD_STOP, "state.should_stop not yet present (Builder A)")
class TestShouldStop(unittest.TestCase):
    """AC12-5 STOP: state.should_stop pure stop-signal function."""

    def _snap_budget(self, limit_usd: float, spent_usd: float) -> Snapshot:
        return _minimal_snap(budget=Budget(limit_usd=limit_usd, spent_usd=spent_usd))

    def test_budget_exhausted_when_spent_ge_limit(self):
        """Returns 'budget_exhausted' when spent_usd >= limit_usd > 0."""
        snap = self._snap_budget(limit_usd=10.0, spent_usd=10.0)
        result = _state.should_stop(snap)
        self.assertEqual(result, "budget_exhausted")

    def test_budget_exhausted_when_spent_exceeds_limit(self):
        """Returns 'budget_exhausted' when spent_usd > limit_usd > 0."""
        snap = self._snap_budget(limit_usd=5.0, spent_usd=6.5)
        result = _state.should_stop(snap)
        self.assertEqual(result, "budget_exhausted")

    def test_budget_not_exhausted_when_limit_zero(self):
        """When limit_usd == 0, budget enforcement is disabled — not 'budget_exhausted'."""
        snap = self._snap_budget(limit_usd=0.0, spent_usd=100.0)
        result = _state.should_stop(snap)
        self.assertNotEqual(result, "budget_exhausted")

    def test_budget_not_exhausted_when_under_limit(self):
        """When spent < limit, budget is not exhausted."""
        snap = self._snap_budget(limit_usd=10.0, spent_usd=4.9)
        result = _state.should_stop(snap)
        self.assertNotEqual(result, "budget_exhausted")

    @unittest.skipUnless(_HAS_DONE_CONDITION, "TaskFrame.done_condition not yet present (Builder A)")
    def test_done_condition_met_when_satisfied(self):
        """Returns 'done_condition_met' when done_condition is set AND
        citations_verified is True AND next_phase >= 5.
        """
        tf = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD)
        tf.done_condition = "all_claims_verified"
        snap = _minimal_snap(
            task_frame=tf,
            citations_verified=True,
            next_phase=5,
        )
        result = _state.should_stop(snap)
        self.assertEqual(result, "done_condition_met")

    @unittest.skipUnless(_HAS_DONE_CONDITION, "TaskFrame.done_condition not yet present (Builder A)")
    def test_done_condition_not_met_when_citations_unverified(self):
        """done_condition_met not returned when citations_verified is False."""
        tf = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD)
        tf.done_condition = "all_claims_verified"
        snap = _minimal_snap(
            task_frame=tf,
            citations_verified=False,
            next_phase=5,
        )
        result = _state.should_stop(snap)
        self.assertNotEqual(result, "done_condition_met")

    @unittest.skipUnless(_HAS_DONE_CONDITION, "TaskFrame.done_condition not yet present (Builder A)")
    def test_done_condition_not_met_when_phase_too_low(self):
        """done_condition_met not returned when next_phase < 5."""
        tf = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD)
        tf.done_condition = "all_claims_verified"
        snap = _minimal_snap(
            task_frame=tf,
            citations_verified=True,
            next_phase=4,
        )
        result = _state.should_stop(snap)
        self.assertNotEqual(result, "done_condition_met")

    def test_none_on_fresh_in_progress_snapshot(self):
        """Returns None for a fresh, in-progress snapshot with no stop conditions."""
        snap = _minimal_snap(
            budget=Budget(limit_usd=100.0, spent_usd=1.0),
            next_phase=2,
            citations_verified=False,
        )
        result = _state.should_stop(snap)
        self.assertIsNone(result)

    def test_stalled_uncertainty_when_unverified_claims_and_no_ready_tasks(self):
        """Returns 'stalled_uncertainty' when there are UNVERIFIED claims and no
        STRICT-ready PENDING subtask exists.

        A snapshot with one UNVERIFIED claim and no subtasks at all has an empty
        ready_set (nothing is STRICT-ready), so it must be stalled.
        """
        claim = Claim(id="C1", text="unverified claim", category=ClaimCategory.UNVERIFIED)
        snap = _minimal_snap(
            claims=[claim],
            subtasks=[],  # no subtasks -> ready_set == []
        )
        result = _state.should_stop(snap)
        self.assertEqual(result, "stalled_uncertainty")

    def test_not_stalled_when_pending_subtask_ready(self):
        """Not stalled when there is at least one STRICT-ready PENDING subtask."""
        claim = Claim(id="C1", text="unverified claim", category=ClaimCategory.UNVERIFIED)
        st = SubTask(id="ST-1", type=SubTaskType.SEARCH, status=SubTaskStatus.PENDING, depends_on=[])
        snap = _minimal_snap(claims=[claim], subtasks=[st])
        result = _state.should_stop(snap)
        # With a ready task and no budget/done triggers -> should NOT be stalled.
        self.assertNotEqual(result, "stalled_uncertainty")

    def test_not_stalled_when_no_unverified_claims(self):
        """Not stalled when there are no claims with category UNVERIFIED."""
        claim = Claim(id="C1", text="verified claim", category=ClaimCategory.VERIFIED)
        snap = _minimal_snap(claims=[claim], subtasks=[])
        result = _state.should_stop(snap)
        self.assertNotEqual(result, "stalled_uncertainty")


# ===========================================================================
# CI regression tests
# ===========================================================================

class TestCiRegression(unittest.TestCase):
    """AC12-5 CI: evals/ci_regression.run_regression() behaviour."""

    def setUp(self):
        # Make evals importable regardless of cwd.
        if str(_SKILL_DIR) not in sys.path:
            sys.path.insert(0, str(_SKILL_DIR))

    def _import_run_regression(self):
        """Import run_regression, adding evals dir to path if needed."""
        evals_parent = str(_SKILL_DIR)
        if evals_parent not in sys.path:
            sys.path.insert(0, evals_parent)
        from evals.ci_regression import run_regression
        return run_regression

    def test_regression_passes_on_golden_corpus_baseline(self):
        """run_regression() with no arguments passes on the bundled golden corpus
        at the default (baseline) thresholds."""
        run_regression = self._import_run_regression()
        outcome = run_regression()
        self.assertIn("passed", outcome)
        self.assertIn("results", outcome)
        self.assertTrue(outcome["passed"], f"Regression unexpectedly failed: {outcome['results']}")

    def test_regression_has_per_case_results(self):
        """run_regression() results list is non-empty and each entry has expected keys."""
        run_regression = self._import_run_regression()
        outcome = run_regression()
        self.assertTrue(len(outcome["results"]) >= 2, "Expected at least 2 corpus cases")
        for r in outcome["results"]:
            self.assertIn("query", r)
            self.assertIn("metrics", r)
            self.assertIn("passed", r)
            self.assertIn("failures", r)

    def test_regression_fails_on_too_high_threshold(self):
        """run_regression() with thresholds=1.0 fails on all metrics, proving
        the regression runner can detect regressions.
        """
        run_regression = self._import_run_regression()
        # Setting all thresholds to 1.0 (perfect score) guarantees failure unless
        # the corpus happens to score perfectly — which our fixed corpus does not.
        outcome = run_regression(thresholds={
            "ndcg_at_k": 1.0,
            "precision_at_k": 1.0,
            "source_coverage": 1.0,
        })
        self.assertFalse(
            outcome["passed"],
            "Expected regression to FAIL with impossibly high thresholds, but it PASSED",
        )

    def test_regression_custom_corpus_path(self):
        """run_regression(corpus_path=...) accepts an explicit path to a corpus file."""
        run_regression = self._import_run_regression()
        corpus_path = str(_EVALS_DIR / "golden_corpus.json")
        outcome = run_regression(corpus_path=corpus_path)
        self.assertIn("passed", outcome)

    def test_regression_metrics_are_floats_in_range(self):
        """All reported metric values are floats in [0.0, 1.0]."""
        run_regression = self._import_run_regression()
        outcome = run_regression()
        for r in outcome["results"]:
            for metric_name, value in r["metrics"].items():
                self.assertIsInstance(value, float, f"{metric_name} is not a float")
                self.assertGreaterEqual(value, 0.0, f"{metric_name} below 0")
                self.assertLessEqual(value, 1.0, f"{metric_name} above 1")


# ===========================================================================
# ACTIVATION corpus tests
# ===========================================================================

class TestActivationCorpus(unittest.TestCase):
    """AC12-5 ACTIVATION: evals/activation_corpus.json shape and content."""

    def _load(self) -> Dict[str, Any]:
        path = _EVALS_DIR / "activation_corpus.json"
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def test_activation_corpus_file_exists(self):
        path = _EVALS_DIR / "activation_corpus.json"
        self.assertTrue(path.exists(), f"activation_corpus.json not found at {path}")

    def test_activation_corpus_has_should_trigger(self):
        data = self._load()
        self.assertIn("should_trigger", data)
        triggers = data["should_trigger"]
        self.assertIsInstance(triggers, list)
        self.assertTrue(len(triggers) > 0, "should_trigger list must be non-empty")

    def test_activation_corpus_has_should_not_trigger(self):
        data = self._load()
        self.assertIn("should_not_trigger", data)
        non_triggers = data["should_not_trigger"]
        self.assertIsInstance(non_triggers, list)
        self.assertTrue(len(non_triggers) > 0, "should_not_trigger list must be non-empty")

    def test_activation_corpus_entries_are_strings(self):
        data = self._load()
        for key in ("should_trigger", "should_not_trigger"):
            for item in data[key]:
                self.assertIsInstance(item, str, f"Entry in {key!r} is not a string: {item!r}")

    def test_activation_corpus_no_overlap(self):
        """No query should appear in both lists."""
        data = self._load()
        triggers = set(data.get("should_trigger", []))
        non_triggers = set(data.get("should_not_trigger", []))
        overlap = triggers & non_triggers
        self.assertEqual(overlap, set(), f"Queries in both lists: {overlap}")


# ===========================================================================
# TD-1 fix regression — validate_snapshot skips ":NONE" deps
# ===========================================================================

class TestValidateSnapshotNoneDep(unittest.TestCase):
    """TD-1 debt-sweep: validate_snapshot must treat a depends_on entry whose
    typed suffix is ':NONE' as NOT a real dependency and skip the unknown-id
    check for it.
    """

    def _snap_with_none_dep(self) -> Snapshot:
        st1 = SubTask(id="ST-1", type=SubTaskType.SEARCH, status=SubTaskStatus.PENDING)
        # ST-2 has a :NONE edge to "ST-99" which does NOT exist; that must NOT
        # trigger an "unknown dependency" validation error.
        st2 = SubTask(
            id="ST-2",
            type=SubTaskType.ANALYZE,
            status=SubTaskStatus.PENDING,
            depends_on=["ST-99:NONE"],
        )
        return _minimal_snap(subtasks=[st1, st2])

    def test_none_dep_not_flagged_unknown(self):
        """:NONE edge to a non-existent id must not produce a validation error."""
        snap = self._snap_with_none_dep()
        errors = validate_snapshot(snap)
        # There must be NO error mentioning ST-99.
        none_errors = [e for e in errors if "ST-99" in e]
        self.assertEqual(none_errors, [], f"Unexpected errors for :NONE dep: {none_errors}")

    def test_none_dep_clean_snapshot_validates(self):
        """The full snapshot with a :NONE dep validates cleanly."""
        snap = self._snap_with_none_dep()
        errors = validate_snapshot(snap)
        self.assertEqual(errors, [], f"Validation errors: {errors}")

    def test_real_unknown_dep_still_flagged(self):
        """A genuine unknown STRICT dep (no :NONE suffix) is still caught."""
        st = SubTask(
            id="ST-1",
            type=SubTaskType.SEARCH,
            depends_on=["ST-GHOST"],  # no :NONE suffix -> real unknown
        )
        snap = _minimal_snap(subtasks=[st])
        errors = validate_snapshot(snap)
        self.assertTrue(
            any("ST-GHOST" in e for e in errors),
            f"Expected ST-GHOST unknown-dep error, got: {errors}",
        )


class TestReviewHardening(unittest.TestCase):
    """Regressions for the three LOW findings from the v1.0.0 /code-review."""

    def test_patch_version_strings_migrate(self):
        # Older checkpoints must load and normalize to the current version
        # (compare on major.minor). 1.2 -> 1.3 ladder added in Phase 15.
        for v in ("1.0.0", "1.1.0", "1.0", "1.1", "1.2", "1.3"):
            snap = snapshot_from_dict(_v10_dict(checkpoint_version=v))
            self.assertEqual(snap.checkpoint_version, "1.3")
            self.assertEqual(validate_snapshot(snap), [])
        with self.assertRaises(ValueError):
            snapshot_from_dict(_v10_dict(checkpoint_version="9.9"))

    @unittest.skipUnless(_HAS_GOAL_VIOLATIONS and _HAS_FORBIDDEN_ACTIONS, "goal fields not present")
    def test_goal_violations_word_boundary(self):
        # "search" must NOT match inside "researched" (no false positive)...
        tf = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD,
                       forbidden_actions=["search"])
        clean = _minimal_snap(task_frame=tf, open_items=["researched the topic"])
        self.assertEqual(_model.goal_violations(clean), [])
        # ...but a whole-word occurrence IS a violation.
        breach = _minimal_snap(task_frame=tf, open_items=["did a search anyway"])
        self.assertEqual(len(_model.goal_violations(breach)), 1)

    def test_none_edge_case_insensitive(self):
        st = SubTask(id="ST-1", type=SubTaskType.SEARCH, depends_on=["ST-9:none"])
        snap = _minimal_snap(subtasks=[st])
        self.assertEqual(validate_snapshot(snap), [])  # lowercase :none == NONE
        st2 = SubTask(id="ST-2", type=SubTaskType.SEARCH, depends_on=["ST-9:STRICT"])
        self.assertTrue(any("ST-9" in e for e in validate_snapshot(_minimal_snap(subtasks=[st2]))))


if __name__ == "__main__":
    unittest.main()
