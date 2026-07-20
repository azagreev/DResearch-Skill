"""H6 — numeric-consistency check (hyperresearch reuse).

Traceability: docs/TRACE_HYPERRESEARCH.md (AC6.1..AC6.4).

A number asserted in a claim should be traceable to the cited source's content
(same digit sequence), optionally within the cited line span. Read-only audit
(a warning surface via `engine numcheck`); NOT wired into the report, so report
output is always byte-identical. Pure/deterministic/offline/stdlib-only.

Run from the skill dir:
    python -m unittest tests.test_h6_numeric -v
"""

import ast
import unittest
from pathlib import Path

from engine import numeric
from engine.model import (
    Claim, ClaimCategory, Depth, Route, Snapshot, Source, TaskFrame, Tier,
)

SKILL_DIR = Path(__file__).resolve().parent.parent

_CONTENT = (
    "Обзор рынка за отчётный период.\n"
    "Выручка составила 30000 рублей за квартал.\n"
    "Доля рынка достигла 45% по итогам года.\n"
    "Прочий заключительный текст без цифр.\n"
)


def _source(sid="S1"):
    return Source(id=sid, url="https://example.test/x", tier=Tier.A,
                  extract={"content": _CONTENT})


def _snapshot(claims):
    tf = TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD)
    return Snapshot(run_id="r", task_fingerprint="f", task_frame=tf,
                    sources=[_source()], claims=claims)


class Ac61TraceableNumberPassesTest(unittest.TestCase):
    def test_number_present_in_source_is_not_flagged(self):
        c = Claim(id="C1", text="Выручка равна 30 000 рублей", confidence=4, sources=["S1"])
        self.assertEqual(numeric.check_claim(c, {"S1": _source()}), [])


class Ac62UntraceableNumberFlaggedTest(unittest.TestCase):
    def test_number_absent_from_source_is_flagged(self):
        c = Claim(id="C2", text="Прибыль выросла на 78 пунктов", confidence=3, sources=["S1"])
        bad = numeric.check_claim(c, {"S1": _source()})
        self.assertEqual(bad, ["78"])

    def test_number_outside_cited_span_is_flagged(self):
        # 45 exists in the source (line 3) but the claim cites only line 2.
        c = Claim(id="C5", text="Доля рынка 45%", confidence=3, sources=["S1"],
                  citation_spans={"S1": [2, 2]})
        bad = numeric.check_claim(c, {"S1": _source()})
        self.assertEqual(bad, ["45"])

    def test_claim_without_sources_is_skipped(self):
        c = Claim(id="C4", text="Число 999 без источника", confidence=1, sources=[])
        self.assertEqual(numeric.check_claim(c, {"S1": _source()}), [])

    def test_claim_without_numbers_is_clean(self):
        c = Claim(id="C3", text="Рынок стабильно растёт", confidence=3, sources=["S1"])
        self.assertEqual(numeric.check_claim(c, {"S1": _source()}), [])


class Ac63DeterminismTest(unittest.TestCase):
    def test_check_snapshot_is_deterministic(self):
        c = Claim(id="C2", text="Прибыль выросла на 78 пунктов", confidence=3, sources=["S1"])
        snap = _snapshot([c])
        self.assertEqual(numeric.check_snapshot(snap), numeric.check_snapshot(snap))
        self.assertEqual(numeric.check_snapshot(snap), {"C2": ["78"]})


class Ac64ReportUntouchedTest(unittest.TestCase):
    def test_report_does_not_import_numeric(self):
        # H6 is a read-only audit verb; it must NOT be wired into rendering, so
        # the report path stays byte-identical regardless of numeric findings.
        src = (SKILL_DIR / "engine" / "report.py").read_text(encoding="utf-8")
        self.assertNotIn("numeric", src)

    def test_module_imports_only_stdlib_and_engine_data(self):
        src = (SKILL_DIR / "engine" / "numeric.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        allowed = {"ingest", "model"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level and node.module:
                self.assertIn(node.module.split(".")[0], allowed)


if __name__ == "__main__":
    unittest.main()
