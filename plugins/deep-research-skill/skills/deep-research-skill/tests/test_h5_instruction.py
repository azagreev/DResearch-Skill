"""H5 — instruction-coverage audit (hyperresearch reuse).

Traceability: docs/TRACE_HYPERRESEARCH.md (AC5.1..AC5.4).

The instruction-critic's mechanical core: flag acceptance-criteria / scope items
that NO finding addresses (zero significant-term overlap with any claim text or
cluster title). Read-only, warning-level (`engine instrcheck`); NOT wired into
the report -> byte-identical. The dialectic-critic (semantic counter-evidence)
stays a review pass in the agent layer, outside the deterministic engine.

Run from the skill dir:
    python -m unittest tests.test_h5_instruction -v
"""

import unittest

from engine import instrcov
from engine.model import (
    Claim, Depth, EvidenceCluster, Route, Snapshot, TaskFrame,
)


def _snapshot(criteria, claims, scope=None, clusters=None):
    tf = TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD,
                   acceptance_criteria=list(criteria), scope=list(scope or []))
    return Snapshot(run_id="r", task_fingerprint="f", task_frame=tf,
                    claims=list(claims), clusters=list(clusters or []))


class Ac52CoveredCriterionNotFlaggedTest(unittest.TestCase):
    def test_criterion_addressed_by_a_finding_is_covered(self):
        snap = _snapshot(
            ["Оценить стоимость лицензии на сервер"],
            [Claim(id="C1", text="Стоимость серверной лицензии составляет заметную сумму")],
        )
        self.assertEqual(instrcov.uncovered_criteria(snap), [])


class Ac52UncoveredCriterionFlaggedTest(unittest.TestCase):
    def test_criterion_with_no_overlap_is_flagged(self):
        snap = _snapshot(
            ["Проанализировать климатические риски региона"],
            [Claim(id="C1", text="Стоимость серверной лицензии составляет заметную сумму")],
        )
        self.assertEqual(instrcov.uncovered_criteria(snap),
                         ["Проанализировать климатические риски региона"])

    def test_scope_items_are_also_checked(self):
        snap = _snapshot(
            [],
            [Claim(id="C1", text="Обзор рынка серверов и лицензий")],
            scope=["транспортная реформа города"],
        )
        self.assertEqual(instrcov.uncovered_criteria(snap), ["транспортная реформа города"])

    def test_cluster_titles_count_as_coverage(self):
        snap = _snapshot(
            ["климатические риски региона"],
            [Claim(id="C1", text="нерелевантный текст про сервера")],
            clusters=[EvidenceCluster(id="K1", title="Климатические риски региона и меры")],
        )
        self.assertEqual(instrcov.uncovered_criteria(snap), [])


class Ac54EdgeAndDeterminismTest(unittest.TestCase):
    def test_no_criteria_is_clean(self):
        snap = _snapshot([], [Claim(id="C1", text="что угодно")])
        self.assertEqual(instrcov.uncovered_criteria(snap), [])

    def test_deterministic(self):
        snap = _snapshot(["альфа бета гамма", "дельта эпсилон"],
                         [Claim(id="C1", text="альфа бета обзор")])
        self.assertEqual(instrcov.uncovered_criteria(snap), instrcov.uncovered_criteria(snap))


class Ac51ReadOnlyTest(unittest.TestCase):
    def test_report_does_not_import_instrcov(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "report.py").read_text(encoding="utf-8")
        self.assertNotIn("instrcov", src)


if __name__ == "__main__":
    unittest.main()
