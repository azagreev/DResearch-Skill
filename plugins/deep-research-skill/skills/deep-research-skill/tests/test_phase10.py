"""Phase 10 unit tests — gates, compact handoff, and DAG plan executor.

Run from the skill dir:  python -m unittest tests.test_phase10 -v

Covers (AC10-3 / AC10-4 / AC10-5 / AC10-7):
  GATES   state.gate_blocks_transition blocks phase>=5 while citations unverified,
          allows it once citations_verified flips True.
  COMPACT compact.build_handoff(snap)["do_not_redo"] lists a rendered source id
          and excludes a still-pending one.
  PLAN    plan.topo_order layers a small DAG, respects STRICT order, and never
          exceeds MAX_CONCURRENT (a 7-wide independent set -> 2 levels);
          parse_dep typing; validate_plan flags a non-FEEDBACK cycle and an
          unknown dep while a FEEDBACK back-edge does NOT; ready_set returns only
          STRICT-unblocked PENDING tasks.
"""

import unittest

from engine import compact, plan, state
from engine.model import (
    Depth,
    Route,
    Snapshot,
    Source,
    SourceStatus,
    SubTask,
    SubTaskStatus,
    SubTaskType,
    TaskFrame,
    validate_snapshot,
)


def _frame() -> TaskFrame:
    return TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD)


def _snap(**kw) -> Snapshot:
    base = dict(run_id="r", task_fingerprint="fp", task_frame=_frame())
    base.update(kw)
    return Snapshot(**base)


def _st(sid: str, deps=None, status=SubTaskStatus.PENDING) -> SubTask:
    return SubTask(
        id=sid,
        type=SubTaskType.SEARCH,
        status=status,
        depends_on=list(deps or []),
    )


# --------------------------------------------------------------------------- #
# GATES (AC10-7)
# --------------------------------------------------------------------------- #
class TestGateBlocksTransition(unittest.TestCase):
    def test_phase5_blocked_when_citations_unverified(self):
        # sources_screened > 0 so the citations gate is the one under test, not
        # the upstream sources-screened gate.
        snap = _snap(next_phase=5, sources_screened=3, citations_verified=False)
        reason = state.gate_blocks_transition(snap, 5)
        self.assertIsNotNone(reason)
        self.assertIn("citations_verified", reason)

    def test_phase5_allowed_when_citations_verified(self):
        snap = _snap(next_phase=5, sources_screened=3, citations_verified=True)
        self.assertIsNone(state.gate_blocks_transition(snap, 5))


# --------------------------------------------------------------------------- #
# COMPACT (AC10-7)
# --------------------------------------------------------------------------- #
class TestBuildHandoffDoNotRedo(unittest.TestCase):
    def test_do_not_redo_lists_rendered_excludes_pending(self):
        rendered = Source(id="S1", url="https://a.com", status=SourceStatus.RENDERED)
        pending = Source(id="S2", url="https://b.com", status=SourceStatus.PENDING)
        snap = _snap(sources=[rendered, pending])

        handoff = compact.build_handoff(snap)
        do_not_redo = handoff["do_not_redo"]

        self.assertIn("S1", do_not_redo)       # rendered -> do not re-fetch
        self.assertNotIn("S2", do_not_redo)    # still pending -> still to do


# --------------------------------------------------------------------------- #
# PLAN — parse_dep (AC10-4)
# --------------------------------------------------------------------------- #
class TestParseDep(unittest.TestCase):
    def test_bare_is_strict(self):
        self.assertEqual(plan.parse_dep("ST-1"), ("ST-1", plan.EdgeKind.STRICT))

    def test_explicit_kinds(self):
        self.assertEqual(plan.parse_dep("ST-1:STRICT"), ("ST-1", plan.EdgeKind.STRICT))
        self.assertEqual(plan.parse_dep("ST-2:SOFT"), ("ST-2", plan.EdgeKind.SOFT))
        self.assertEqual(plan.parse_dep("ST-3:NONE"), ("ST-3", plan.EdgeKind.NONE))
        self.assertEqual(plan.parse_dep("ST-4:FEEDBACK"), ("ST-4", plan.EdgeKind.FEEDBACK))

    def test_id_keeps_internal_hyphens(self):
        # Only the trailing ":KIND" is the suffix; the hyphenated id is intact.
        self.assertEqual(plan.parse_dep("ST-10:SOFT"), ("ST-10", plan.EdgeKind.SOFT))


# --------------------------------------------------------------------------- #
# PLAN — topo_order (AC10-4 / AC10-5)
# --------------------------------------------------------------------------- #
class TestTopoOrder(unittest.TestCase):
    def test_strict_order_layers(self):
        # ST-1 -> ST-2 -> ST-3 (a chain). Three levels, in order.
        subtasks = [
            _st("ST-1"),
            _st("ST-2", ["ST-1"]),
            _st("ST-3", ["ST-2"]),
        ]
        levels = plan.topo_order(subtasks)
        self.assertEqual(levels, [["ST-1"], ["ST-2"], ["ST-3"]])

    def test_diamond_respects_strict_order(self):
        # ST-1 -> {ST-2, ST-3} -> ST-4
        subtasks = [
            _st("ST-1"),
            _st("ST-2", ["ST-1"]),
            _st("ST-3", ["ST-1"]),
            _st("ST-4", ["ST-2", "ST-3"]),
        ]
        levels = plan.topo_order(subtasks)
        self.assertEqual(levels, [["ST-1"], ["ST-2", "ST-3"], ["ST-4"]])
        # A predecessor must appear on an earlier level than its successor.
        flat = [lvl for lvl in levels]
        idx = {sid: i for i, lvl in enumerate(flat) for sid in lvl}
        self.assertLess(idx["ST-1"], idx["ST-2"])
        self.assertLess(idx["ST-2"], idx["ST-4"])
        self.assertLess(idx["ST-3"], idx["ST-4"])

    def test_soft_edge_constrains_layering(self):
        # SOFT predecessor still pushes the successor to a later level.
        subtasks = [
            _st("ST-1"),
            _st("ST-2", ["ST-1:SOFT"]),
        ]
        levels = plan.topo_order(subtasks)
        self.assertEqual(levels, [["ST-1"], ["ST-2"]])

    def test_feedback_edge_ignored_for_ordering(self):
        # A FEEDBACK back-edge ST-1 depends_on ST-2:FEEDBACK must NOT prevent
        # layering (would otherwise be a cycle). Forward STRICT edge wins.
        subtasks = [
            _st("ST-1", ["ST-2:FEEDBACK"]),
            _st("ST-2", ["ST-1:STRICT"]),
        ]
        levels = plan.topo_order(subtasks)
        self.assertEqual(levels, [["ST-1"], ["ST-2"]])

    def test_max_concurrent_split_seven_wide(self):
        # 7 independent tasks -> exactly 2 levels (5 + 2), none over MAX_CONCURRENT.
        subtasks = [_st(f"ST-{i}") for i in range(1, 8)]
        levels = plan.topo_order(subtasks)
        self.assertEqual(len(levels), 2)
        for lvl in levels:
            self.assertLessEqual(len(lvl), plan.MAX_CONCURRENT)
        # Every task placed exactly once.
        placed = [sid for lvl in levels for sid in lvl]
        self.assertEqual(sorted(placed), sorted(t.id for t in subtasks))
        # Stable split: smallest ids on the earlier sub-level.
        self.assertEqual(levels[0], ["ST-1", "ST-2", "ST-3", "ST-4", "ST-5"])
        self.assertEqual(levels[1], ["ST-6", "ST-7"])


# --------------------------------------------------------------------------- #
# PLAN — ready_set (AC10-4)
# --------------------------------------------------------------------------- #
class TestReadySet(unittest.TestCase):
    def test_only_strict_unblocked_pending(self):
        subtasks = [
            _st("ST-1", status=SubTaskStatus.DONE),     # done, not pending -> excluded
            _st("ST-2", ["ST-1"]),                       # STRICT pred DONE -> ready
            _st("ST-3", ["ST-4"]),                       # STRICT pred PENDING -> blocked
            _st("ST-4", status=SubTaskStatus.PENDING),   # no deps -> ready
        ]
        ready = plan.ready_set(subtasks)
        self.assertEqual(ready, ["ST-2", "ST-4"])

    def test_soft_pred_does_not_block_readiness(self):
        # SOFT predecessor pending must NOT keep the task out of the ready set.
        subtasks = [
            _st("ST-1", status=SubTaskStatus.PENDING),
            _st("ST-2", ["ST-1:SOFT"]),
        ]
        self.assertEqual(plan.ready_set(subtasks), ["ST-1", "ST-2"])

    def test_done_task_not_returned(self):
        subtasks = [_st("ST-1", status=SubTaskStatus.DONE)]
        self.assertEqual(plan.ready_set(subtasks), [])


# --------------------------------------------------------------------------- #
# PLAN — validate_plan (AC10-4)
# --------------------------------------------------------------------------- #
class TestValidatePlan(unittest.TestCase):
    def test_clean_dag_has_no_errors(self):
        subtasks = [
            _st("ST-1"),
            _st("ST-2", ["ST-1"]),
            _st("ST-3", ["ST-1", "ST-2"]),
        ]
        self.assertEqual(plan.validate_plan(subtasks), [])

    def test_unknown_dependency_flagged(self):
        subtasks = [_st("ST-1", ["ST-99"])]
        errors = plan.validate_plan(subtasks)
        self.assertTrue(any("unknown dependency ST-99" in e for e in errors))

    def test_non_feedback_cycle_flagged(self):
        # ST-1 -> ST-2 -> ST-1 via STRICT edges: a disallowed cycle.
        subtasks = [
            _st("ST-1", ["ST-2:STRICT"]),
            _st("ST-2", ["ST-1:STRICT"]),
        ]
        errors = plan.validate_plan(subtasks)
        self.assertTrue(any("cycle detected" in e for e in errors))

    def test_feedback_back_edge_does_not_cycle(self):
        # Same loop shape but the back-edge is FEEDBACK -> allowed, no error.
        subtasks = [
            _st("ST-1", ["ST-2:FEEDBACK"]),
            _st("ST-2", ["ST-1:STRICT"]),
        ]
        errors = plan.validate_plan(subtasks)
        self.assertEqual(errors, [])

    def test_reports_both_unknown_and_cycle(self):
        subtasks = [
            _st("ST-1", ["ST-2:STRICT", "ST-X"]),
            _st("ST-2", ["ST-1:STRICT"]),
        ]
        errors = plan.validate_plan(subtasks)
        self.assertTrue(any("unknown dependency ST-X" in e for e in errors))
        self.assertTrue(any("cycle detected" in e for e in errors))


# --------------------------------------------------------------------------- #
# TYPED-EDGE x validate_snapshot (integration regression)
# --------------------------------------------------------------------------- #
class TestTypedDepValidatesAgainstSnapshot(unittest.TestCase):
    """validate_snapshot must accept typed-edge depends_on ('ST-1:STRICT') by
    isolating the id part, not treating the whole string as an unknown id."""

    def test_typed_dep_is_not_flagged_unknown(self):
        snap = _snap(subtasks=[_st("ST-1"), _st("ST-2", deps=["ST-1:STRICT"])])
        self.assertEqual(validate_snapshot(snap), [])

    def test_unknown_typed_dep_flagged_by_id_part(self):
        snap = _snap(subtasks=[_st("ST-2", deps=["ST-9:SOFT"])])
        errors = validate_snapshot(snap)
        self.assertTrue(any("ST-9" in e for e in errors))
        self.assertFalse(any("ST-9:SOFT" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
