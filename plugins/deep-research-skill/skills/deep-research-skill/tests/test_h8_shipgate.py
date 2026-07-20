"""H8 — ship-gate aggregator (hyperresearch reuse, `runs.verify_run`).

Traceability: docs/TRACE_HYPERRESEARCH.md (AC8.1..AC8.E2E).

Composes the v1.7.0 verification battery into ONE PASS/WARN/FAIL verdict:
blocking = quote-integrity own-finding block, retracted-cite, citation-density
below the profile floor, empty report; warning = numeric-consistency,
instruction-coverage. Read-only, deterministic; NOT wired into rendering.

Run from the skill dir:
    python -m unittest tests.test_h8_shipgate -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from engine import shipgate
from engine.model import (
    Claim, ClaimCategory, ClaimRole, Depth, Route, Snapshot, Source, TaskFrame,
    Tier, snapshot_to_dict,
)
from engine.policy import ReportMode

SKILL_DIR = Path(__file__).resolve().parent.parent
_CONTENT = "Строка один.\nВыручка выросла на 30000 рублей за год.\nСтрока три.\n"


def _src(sid="S1", retracted=None):
    return Source(id=sid, url=f"https://example.test/{sid}", tier=Tier.A,
                  retracted=retracted, extract={"content": _CONTENT})


def _snap(claims, sources=None, criteria=None):
    tf = TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD,
                   acceptance_criteria=list(criteria or []))
    return Snapshot(run_id="r", task_fingerprint="f", task_frame=tf,
                    sources=list(sources or [_src()]), claims=list(claims))


def _finding(cid="C1", text="проверенный факт о рынке", sources=("S1",), **kw):
    return Claim(id=cid, text=text, category=ClaimCategory.VERIFIED,
                 confidence=4, sources=list(sources), **kw)


class Ac81AggregatesTest(unittest.TestCase):
    def test_clean_snapshot_passes_with_all_checks(self):
        out = shipgate.check(_snap([_finding()]))
        self.assertEqual(out["verdict"], "PASS")
        for key in ("quote_integrity", "retraction", "citation_density",
                    "completeness", "numeric_consistency", "instruction_coverage"):
            self.assertIn(key, out["checks"])


class Ac82BlockingFailTest(unittest.TestCase):
    def test_quote_block_own_finding_fails(self):
        bad = _finding("C1", text='Ложь: «этой фразы точно нет в источнике вовсе» да',
                       citation_spans={"S1": [1, 1]})
        out = shipgate.check(_snap([bad]))
        self.assertEqual(out["verdict"], "FAIL")
        self.assertTrue(any("quote" in b.lower() for b in out["blocking"]))

    def test_retracted_cite_fails(self):
        out = shipgate.check(_snap([_finding(sources=("S1",))], sources=[_src(retracted=True)]))
        self.assertEqual(out["verdict"], "FAIL")
        self.assertTrue(any("retract" in b.lower() for b in out["blocking"]))


class Ac83WarnNotFailTest(unittest.TestCase):
    def test_untraceable_number_is_warn(self):
        c = _finding("C1", text="Прибыль выросла на 77 пунктов")  # 77 not in source
        out = shipgate.check(_snap([c]))
        self.assertEqual(out["verdict"], "WARN")
        self.assertEqual(out["blocking"], [])
        self.assertTrue(any("numeric" in w.lower() for w in out["warnings"]))

    def test_uncovered_criterion_is_warn(self):
        out = shipgate.check(_snap([_finding()], criteria=["совершенно иная непокрытая тема"]))
        self.assertEqual(out["verdict"], "WARN")
        self.assertTrue(any("instruction" in w.lower() for w in out["warnings"]))


class Ac84CitationDensityTest(unittest.TestCase):
    def test_uncited_finding_fails_against_profile_floor(self):
        c = _finding("C1", text="утверждение без источника", sources=())
        out = shipgate.check(_snap([c]))
        self.assertEqual(out["verdict"], "FAIL")
        self.assertTrue(any("citation" in b.lower() for b in out["blocking"]))
        self.assertFalse(out["checks"]["citation_density"]["ok"])


class Ac81MirrorReportShipSetTest(unittest.TestCase):
    """Regression (review MAJOR/MINOR): the gate's shipped-set must match what
    report.py renders."""

    def test_corrections_only_debunk_is_not_empty(self):
        # a debunk (EXTERNAL_CLAIM + FALSE -> INCLUDE_AS_CORRECTION) ships as a
        # correction; completeness must NOT call it empty.
        deb = Claim(id="D1", text="миф о рынке опровергнут источником",
                    role=ClaimRole.EXTERNAL_CLAIM, category=ClaimCategory.FALSE,
                    confidence=1, sources=["S1"])
        out = shipgate.check(_snap([deb]))
        self.assertNotIn("completeness", " ".join(out["blocking"]))
        self.assertTrue(out["checks"]["completeness"]["ok"])

    def test_dangling_source_id_fails_citation_density(self):
        # finding cites S9 (not in snapshot) -> report renders it UNCITED -> FAIL.
        c = _finding("C1", sources=("S9",))
        out = shipgate.check(_snap([c], sources=[_src("S1")]))
        self.assertEqual(out["verdict"], "FAIL")
        self.assertFalse(out["checks"]["citation_density"]["ok"])

    def test_excluded_own_finding_bad_quote_does_not_block(self):
        # a good VERIFIED finding ships; an UNVERIFIED own-finding (excluded in
        # FINDINGS) with a fabricated quote must NOT fail the gate.
        good = _finding("C1")
        junk = Claim(id="C2", text='Слух: «этой фразы точно нет в источнике вовсе» да',
                     category=ClaimCategory.UNVERIFIED, confidence=1, sources=["S1"],
                     citation_spans={"S1": [1, 1]})
        out = shipgate.check(_snap([good, junk]))
        self.assertTrue(out["checks"]["quote_integrity"]["ok"])
        self.assertNotEqual(out["verdict"], "FAIL")

    def test_uncited_retracted_source_in_bibliography_is_warn(self):
        good = _finding("C1", sources=("S1",))
        out = shipgate.check(_snap([good], sources=[_src("S1"), _src("S2", retracted=True)]))
        self.assertEqual(out["verdict"], "WARN")
        self.assertEqual(out["blocking"], [])
        self.assertIn("S2", out["checks"]["retraction"]["in_bibliography"])


class Ac85ReadOnlyDeterministicTest(unittest.TestCase):
    def test_report_does_not_import_shipgate(self):
        src = (SKILL_DIR / "engine" / "report.py").read_text(encoding="utf-8")
        self.assertNotIn("shipgate", src)

    def test_deterministic(self):
        snap = _snap([_finding()])
        self.assertEqual(shipgate.check(snap), shipgate.check(snap))


class Ac8E2ESubprocessTest(unittest.TestCase):
    def _run(self, payload):
        return subprocess.run([sys.executable, "-m", "engine", "shipcheck"],
                              input=json.dumps(payload), capture_output=True,
                              text=True, encoding="utf-8", cwd=str(SKILL_DIR))

    def test_shipcheck_verb(self):
        proc = self._run({"snapshot": snapshot_to_dict(_snap([_finding()]))})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["verdict"], "PASS")
        self.assertIn("checks", out)


if __name__ == "__main__":
    unittest.main()
