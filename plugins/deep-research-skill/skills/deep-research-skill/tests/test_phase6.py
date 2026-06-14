"""Phase 6 unit tests — disposition policy, report rendering, paid providers.

Run from the skill dir:  python -m unittest discover -s tests -t .
"""

import unittest

from engine import providers, report
from engine.model import (
    Claim,
    ClaimCategory,
    ClaimRole,
    Depth,
    EvidenceCluster,
    Route,
    Snapshot,
    Source,
    TaskFrame,
    Tier,
)
from engine.policy import Disposition, ReportMode, disposition


def claim(id_, category, role=ClaimRole.OWN_FINDING, conf=3, sources=None):
    return Claim(id=id_, text=f"text-{id_}", role=role, category=category, confidence=conf, sources=sources or [])


class TestDisposition(unittest.TestCase):
    def test_table(self):
        self.assertEqual(disposition(claim("C", ClaimCategory.VERIFIED), ReportMode.FINDINGS), Disposition.INCLUDE)
        for cat in (ClaimCategory.OUTDATED, ClaimCategory.INCOMPLETE, ClaimCategory.OPINION):
            self.assertEqual(disposition(claim("C", cat), ReportMode.FINDINGS), Disposition.INCLUDE_WITH_FLAG)
        self.assertEqual(disposition(claim("C", ClaimCategory.UNVERIFIED), ReportMode.FINDINGS), Disposition.EXCLUDE_BUT_RECORD)
        self.assertEqual(disposition(claim("C", ClaimCategory.UNVERIFIED), ReportMode.DEBUNK), Disposition.INCLUDE_WITH_FLAG)
        self.assertEqual(
            disposition(claim("C", ClaimCategory.FALSE, role=ClaimRole.EXTERNAL_CLAIM), ReportMode.FINDINGS),
            Disposition.INCLUDE_AS_CORRECTION,
        )
        self.assertEqual(
            disposition(claim("C", ClaimCategory.FALSE, role=ClaimRole.OWN_FINDING), ReportMode.FINDINGS),
            Disposition.TRIGGER_REVISION,
        )


class TestReport(unittest.TestCase):
    def _snapshot(self):
        return Snapshot(
            run_id="r1", task_fingerprint="fp",
            task_frame=TaskFrame(question="Цены Whoop на CDEK", route=Route.FOCUSED, depth=Depth.STANDARD),
            sources=[Source(id="S1", url="https://a.com", tier=Tier.S), Source(id="S2", url="https://b.com", tier=Tier.B)],
            claims=[
                Claim(id="C1", text="Whoop стоит 30000", category=ClaimCategory.VERIFIED, confidence=4, sources=["S1"]),
                Claim(id="C2", text="Мнение про рынок", category=ClaimCategory.OPINION, confidence=3, sources=["S2"]),
                Claim(id="C3", text="Миф о бесплатной доставке", role=ClaimRole.EXTERNAL_CLAIM, category=ClaimCategory.FALSE, confidence=1, sources=["S2"]),
                Claim(id="C4", text="Наш ошибочный вывод", category=ClaimCategory.FALSE, confidence=1),
                Claim(id="C5", text="Непроверяемое утверждение", category=ClaimCategory.UNVERIFIED, confidence=1),
            ],
            clusters=[EvidenceCluster(id="K1", title="Цены Whoop", claim_ids=["C1", "C2"], representative_ids=["C1"])],
        )

    def test_findings_mode(self):
        md = report.render_markdown(self._snapshot(), ReportMode.FINDINGS)
        self.assertIn("Whoop стоит 30000", md)              # VERIFIED
        self.assertIn("Мнение про рынок", md)               # OPINION (flagged)
        self.assertIn("## Цены Whoop", md)                  # cluster-first
        self.assertIn("Опровергнуто", md)                   # corrections section
        self.assertIn("Миф о бесплатной доставке", md)      # FALSE external -> correction
        self.assertNotIn("Наш ошибочный вывод", md)         # FALSE own -> revision (hidden)
        self.assertNotIn("Непроверяемое утверждение", md)   # UNVERIFIED in findings -> recorded
        self.assertIn("на пересмотр: 1", md)
        self.assertIn("исключено-в-память: 1", md)

    def test_debunk_shows_unverified(self):
        md = report.render_markdown(self._snapshot(), ReportMode.DEBUNK)
        self.assertIn("Непроверяемое утверждение", md)

    def test_english_labels_driven_by_task_frame(self):
        # v1.4: TaskFrame.language drives the report language end-to-end.
        snap = self._snapshot()
        snap.task_frame.language = "en"
        md = report.render_markdown(snap, ReportMode.FINDINGS)
        self.assertIn("# Report:", md)
        self.assertIn("**Aggregate confidence:**", md)
        self.assertIn("· findings: ", md)
        self.assertIn("## Sources", md)
        self.assertIn("Refuted / corrections", md)
        self.assertIn("ONE VIEWPOINT", md)               # OPINION flag, English
        self.assertIn("Findings: ", md)                  # footer
        # No Russian labels leaked (claim TEXT stays as authored — only labels switch)
        for ru in ("Отчёт", "Источники", "Опровергнуто", "ОДНА ИЗ ТОЧЕК ЗРЕНИЯ", "Выводов:"):
            self.assertNotIn(ru, md)

    def test_explicit_language_overrides_snapshot(self):
        # snapshot defaults to ru; an explicit language arg wins.
        md = report.render_markdown(self._snapshot(), ReportMode.FINDINGS, language="en")
        self.assertIn("## Sources", md)
        self.assertNotIn("Источники", md)

    def test_unknown_language_falls_back_to_ru(self):
        md = report.render_markdown(self._snapshot(), ReportMode.FINDINGS, language="zz")
        self.assertIn("# Отчёт:", md)
        self.assertIn("## Источники", md)


class TestProviders(unittest.TestCase):
    def test_parse_and_precedence(self):
        cfg = providers.load_config(
            environ={"BRAVE_API_KEY": "env-key"},
            dotenv_text='BRAVE_API_KEY="file-key"\n# comment\nEXA_API_KEY=ek\n',
        )
        self.assertEqual(cfg["BRAVE_API_KEY"], "env-key")   # env wins over .env
        self.assertEqual(cfg["EXA_API_KEY"], "ek")

    def test_enablement_default_off(self):
        self.assertFalse(providers.is_enabled({"BRAVE_API_KEY": "k"}))                       # no flag
        self.assertFalse(providers.is_enabled({"DRESEARCH_PAID_SEARCH": "1"}))               # no key
        self.assertTrue(providers.is_enabled({"DRESEARCH_PAID_SEARCH": "1", "BRAVE_API_KEY": "k"}))

    def test_select_backend(self):
        cfg = {"EXA_API_KEY": "e", "SERPER_API_KEY": "s"}
        self.assertEqual(providers.select_backend(cfg, "auto"), "exa")   # priority order
        self.assertEqual(providers.select_backend(cfg, "serper"), "serper")
        self.assertIsNone(providers.select_backend(cfg, "brave"))        # key absent
        self.assertIsNone(providers.select_backend({}, "auto"))

    def test_web_search_disabled_and_injected_http(self):
        self.assertEqual(providers.web_search("q", {"BRAVE_API_KEY": "k"}), ([], {"status": "disabled"}))

        def fake_http(url, headers, body=None):
            self.assertIn("brave.com", url)
            self.assertIsNone(body)  # Brave is a GET, no body
            return {"web": {"results": [{"url": "https://x", "title": "T", "description": "D"}]}}

        cfg = {"DRESEARCH_PAID_SEARCH": "1", "BRAVE_API_KEY": "k"}
        items, meta = providers.web_search("q", cfg, http=fake_http)
        self.assertEqual(meta["status"], "ok")
        self.assertEqual(meta["backend"], "brave")
        self.assertEqual(items[0]["url"], "https://x")
        self.assertEqual(items[0]["backend"], "brave")


if __name__ == "__main__":
    unittest.main()
