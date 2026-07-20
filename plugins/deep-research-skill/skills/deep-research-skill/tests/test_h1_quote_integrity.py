"""H1 — mechanical quote-integrity gate (hyperresearch reuse).

Traceability: docs/TRACE_HYPERRESEARCH.md (AC1.1..AC1.E2E).

A verbatim quote a claim carries (in «»/""/"" delimiters) must actually appear in
the cited source's content at the cited line span. Scoped to claims that carry
citation_spans (the R2 verifiable-citation opt-in), so legacy no-span claims are
never touched -> byte-identical output. Pure/deterministic/offline/stdlib-only.

Run from the skill dir:
    python -m unittest tests.test_h1_quote_integrity -v
"""

import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path

from engine import quoteintegrity
from engine.model import (
    Claim,
    ClaimCategory,
    Depth,
    Route,
    Snapshot,
    Source,
    TaskFrame,
    Tier,
    snapshot_to_dict,
)
from engine.policy import ReportMode
from engine.report import render_markdown

SKILL_DIR = Path(__file__).resolve().parent.parent

# Line 3 (1-indexed) carries the only verbatim phrase we treat as ground truth.
_CONTENT = (
    "Вводный абзац без цифр.\n"
    "Второй абзац продолжает тему.\n"
    "Компания сообщила: выручка компании выросла заметно в этом году.\n"
    "Заключительный абзац отчёта.\n"
)


def _source(sid="S1"):
    return Source(id=sid, url="https://example.test/report", tier=Tier.A,
                  extract={"content": _CONTENT})


def _snapshot(claims):
    tf = TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD)
    return Snapshot(run_id="r", task_fingerprint="f", task_frame=tf,
                    sources=[_source()], claims=claims)


class Ac11SupportedQuotePassesTest(unittest.TestCase):
    def test_supported_quote_has_no_mismatch(self):
        c = Claim(id="C1", text='Отчёт: «выручка компании выросла заметно» за год',
                  category=ClaimCategory.VERIFIED,
                  confidence=4, sources=["S1"], citation_spans={"S1": [3, 3]})
        self.assertEqual(quoteintegrity.check_claim(c, {"S1": _source()}), [])


class Ac12FabricatedQuoteFlaggedTest(unittest.TestCase):
    def test_fabricated_quote_is_unsupported(self):
        c = Claim(id="C2", text='Данные: «продажи упали на пятьдесят процентов» источник',
                  confidence=3, sources=["S1"], citation_spans={"S1": [3, 3]})
        bad = quoteintegrity.check_claim(c, {"S1": _source()})
        self.assertEqual(len(bad), 1)
        self.assertIn("продажи упали", bad[0])

    def test_quote_outside_the_cited_span_is_unsupported(self):
        # The phrase exists in the source but NOT within the cited line span (1-1).
        c = Claim(id="C2b", text='Заявлено: «выручка компании выросла заметно» ранее',
                  confidence=3, sources=["S1"], citation_spans={"S1": [1, 1]})
        bad = quoteintegrity.check_claim(c, {"S1": _source()})
        self.assertEqual(len(bad), 1)


class Ac13FindingsHardBlockTest(unittest.TestCase):
    def test_mismatched_claim_excluded_and_note_surfaced_in_findings(self):
        from engine.model import ClaimCategory
        good = Claim(id="C1", text='Отчёт: «выручка компании выросла заметно» за год',
                     category=ClaimCategory.VERIFIED, confidence=4, sources=["S1"],
                     citation_spans={"S1": [3, 3]})
        bad = Claim(id="C2", text='Ложь: «продажи упали на пятьдесят процентов» тут',
                    category=ClaimCategory.VERIFIED, confidence=5, sources=["S1"],
                    citation_spans={"S1": [3, 3]})
        md = render_markdown(_snapshot([good, bad]), ReportMode.FINDINGS)
        self.assertIn("выручка компании выросла заметно", md)      # supported ships
        self.assertNotIn("продажи упали на пятьдесят процентов", md)  # fabricated blocked from body
        self.assertIn("quote-integrity", md.lower())                # surfaced note present


class Ac14LegacyByteIdenticalTest(unittest.TestCase):
    def test_quote_without_spans_is_not_checked_and_not_excluded(self):
        from engine.model import ClaimCategory
        # A no-span claim that quotes text absent from any source must be UNTOUCHED
        # (legacy behavior) — never checked, never excluded, no note.
        legacy = Claim(id="C1", text='Слух: «этой фразы нет ни в одном источнике вообще» да',
                       category=ClaimCategory.VERIFIED, confidence=4, sources=["S1"])
        md = render_markdown(_snapshot([legacy]), ReportMode.FINDINGS)
        self.assertIn("этой фразы нет ни в одном источнике вообще", md)
        self.assertNotIn("quote-integrity", md.lower())
        self.assertEqual(quoteintegrity.check_claim(legacy, {"S1": _source()}), [])


class Ac15DeterminismAndStdlibTest(unittest.TestCase):
    def test_check_is_deterministic(self):
        from engine.model import ClaimCategory
        c = Claim(id="C2", text='Ложь: «продажи упали на пятьдесят процентов» тут',
                  category=ClaimCategory.VERIFIED, confidence=5, sources=["S1"],
                  citation_spans={"S1": [3, 3]})
        snap = _snapshot([c])
        self.assertEqual(quoteintegrity.check_snapshot(snap), quoteintegrity.check_snapshot(snap))

    def test_module_imports_only_stdlib_and_engine_data(self):
        src = (SKILL_DIR / "engine" / "quoteintegrity.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        allowed_engine = {"ingest", "model"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("engine"):
                # relative imports show as level>0 with module like 'ingest'/'model'
                pass
            if isinstance(node, ast.ImportFrom) and node.level and node.module:
                self.assertIn(node.module.split(".")[0], allowed_engine,
                              f"quoteintegrity must not couple to engine.{node.module}")


class Ac1E2ESubprocessTest(unittest.TestCase):
    def _run(self, verb, payload):
        # engine _emit writes UTF-8 deliberately (report carries Cyrillic/emoji);
        # force UTF-8 decode so a cp1252 locale can't turn stdout into None
        # (root cause of the intermittent None-stdout class on Windows).
        proc = subprocess.run([sys.executable, "-m", "engine", verb],
                              input=json.dumps(payload), capture_output=True,
                              text=True, encoding="utf-8", cwd=str(SKILL_DIR))
        return proc

    def test_quotecheck_verb_flags_fabricated_quote(self):
        from engine.model import ClaimCategory
        bad = Claim(id="C2", text='Ложь: «продажи упали на пятьдесят процентов» тут',
                    category=ClaimCategory.VERIFIED, confidence=5, sources=["S1"],
                    citation_spans={"S1": [3, 3]})
        proc = self._run("quotecheck", {"snapshot": snapshot_to_dict(_snapshot([bad]))})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertIn("results", out)
        self.assertIn("summary", out)
        self.assertEqual(out["summary"]["n_failed"], 1)


class Ac13DebunkNotSuppressedTest(unittest.TestCase):
    """Regression (review MAJOR): a debunk (EXTERNAL_CLAIM + FALSE ->
    INCLUDE_AS_CORRECTION) verbatim-quotes the refuted assertion, whose text
    is NOT in the refuting source it cites. The gate must NOT drop it."""

    def test_correction_with_unbacked_myth_quote_still_ships(self):
        from engine.model import ClaimRole
        myth = Claim(id="D1", text='Миф: «вакцина вызывает аутизм у детей точно» — опровергнуто',
                     role=ClaimRole.EXTERNAL_CLAIM, category=ClaimCategory.FALSE,
                     confidence=1, sources=["S1"], citation_spans={"S1": [3, 3]})
        md = render_markdown(_snapshot([myth]), ReportMode.FINDINGS)
        # The debunk ships as a correction (its quote is the thing refuted)...
        self.assertIn("вакцина вызывает аутизм у детей точно", md)
        # ...and it must NOT be reported as a quote-integrity block.
        self.assertNotIn("quote-integrity", md.lower())


class Ac13NoteOnlyForBlockedFindingsTest(unittest.TestCase):
    """A claim already excluded by disposition (UNVERIFIED in FINDINGS ->
    EXCLUDE_BUT_RECORD) that also has a bad quote must not add a note line —
    the reader never saw it in the body anyway."""

    def test_no_note_for_already_excluded_claim(self):
        unv = Claim(id="C9", text='Слух: «продажи упали на пятьдесят процентов» да',
                    category=ClaimCategory.UNVERIFIED, confidence=1, sources=["S1"],
                    citation_spans={"S1": [3, 3]})
        md = render_markdown(_snapshot([unv]), ReportMode.FINDINGS)
        self.assertNotIn("quote-integrity", md.lower())


if __name__ == "__main__":
    unittest.main()
