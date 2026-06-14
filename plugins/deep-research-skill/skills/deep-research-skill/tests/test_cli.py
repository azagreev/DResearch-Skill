"""CLI smoke tests — drive each subcommand through cli.main() with a JSON file
input and capture stdout. Run from the skill dir:
    python -m unittest discover -s tests -t .
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from engine import cli
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

NOW = "2026-06-30T00:00:00Z"


class CliTest(unittest.TestCase):
    def _write(self, obj) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(obj, handle)
        handle.close()
        self.addCleanup(lambda: os.unlink(handle.name))
        return handle.name

    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main(argv)
        return rc, buf.getvalue()

    def _json(self, argv):
        rc, out = self._run(argv)
        self.assertEqual(rc, 0)
        return json.loads(out)

    def test_ingest(self):
        p = self._write({"sources": [{"url": "https://a.com/x", "tier": "S"}, {"url": "https://www.a.com/x/"}], "now": NOW})
        out = self._json(["ingest", "-i", p])
        self.assertEqual(len(out["sources"]), 1)
        self.assertIn(["S1", "S2"], out["merges"])

    def test_rank(self):
        p = self._write({
            "sources": [{"id": "A", "url": "u", "tier": "S"}, {"id": "B", "url": "u2", "tier": "S"}],
            "streams": {"q1": ["A"], "q2": ["B"]},
        })
        out = self._json(["rank", "-i", p])
        self.assertEqual([r["id"] for r in out["ranked"]], ["A", "B"])  # equal score -> id asc

    def test_score(self):
        p = self._write({"sources": [{"id": "S1", "url": "u", "tier": "S", "published_at": "2026-06-28",
                                       "scores": {"independence": 0.9, "traceability": 0.9, "corroboration": 0.8}}], "now": NOW})
        out = self._json(["score", "-i", p])
        self.assertIn(out["sources"][0]["tier"], ("S", "A"))  # authority seeded -> high, not C/D

    def test_factcheck(self):
        p = self._write({"sources": [{"id": "S1", "url": "u", "tier": "S"}],
                         "claims": [{"id": "C1", "text": "x", "sources": ["S1"]}], "now": NOW})
        out = self._json(["factcheck", "-i", p])
        self.assertEqual(out["claims"][0]["category"], "verified")

    def test_cluster(self):
        p = self._write({"claims": [
            {"id": "C1", "text": "apple banana cherry", "sources": ["S1"], "confidence": 4},
            {"id": "C2", "text": "apple banana cherry date", "sources": ["S2"], "confidence": 3},
        ]})
        out = self._json(["cluster", "-i", p])
        self.assertEqual(len(out["clusters"]), 1)

    def test_eval(self):
        p = self._write({"ranked": ["a", "b", "c"], "relevant": ["a", "c"], "grades": {"a": 3, "c": 1}, "k": 2})
        out = self._json(["eval", "-i", p])
        self.assertEqual(out["precision_at_k"], 0.5)
        self.assertIn("ndcg_at_k", out)

    def test_memory_stats(self):
        out = self._json(["memory", "--op", "stats"])
        self.assertEqual(out["runs"], 0)

    def test_checkpoint_and_resume(self):
        tf = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD)
        snap = Snapshot(run_id="r", task_fingerprint="f", task_frame=tf, sources=[Source(id="S1", url="u")])
        with tempfile.TemporaryDirectory() as td:
            cp = self._json(["checkpoint", "-i", self._write(snapshot_to_dict(snap)), "--run-dir", td, "--stage", "raw"])
            self.assertTrue(cp["checkpoint"].endswith("cp_01_raw.md"))
            dec = self._json(["resume", "-i", self._write({"question": "q", "route": "B", "depth": "Standard"}),
                              "--run-root", td, "--now", NOW])
            self.assertEqual(dec["mode"], "fresh")  # empty root -> fresh

    def test_run_emits_report(self):
        p = self._write({
            "task_frame": {"question": "Whoop price", "route": "B", "depth": "Standard"},
            "sources": [{"url": "https://cdek.shopping/whoop", "tier": "S", "published_at": "2026-06-25",
                         "scores": {"independence": 0.9, "traceability": 0.9, "corroboration": 0.8}}],
            "claims": [{"id": "C1", "text": "Whoop 30000", "sources": ["S1"]}],
            "now": NOW,
        })
        rc, out = self._run(["run", "-i", p])
        self.assertEqual(rc, 0)
        self.assertIn("Отчёт", out)
        self.assertIn("Whoop 30000", out)

    def test_run_emits_english_report(self):
        # v1.4 / AC-A2: TaskFrame.language drives the report language through the
        # full `engine run` path (read_input -> run_pipeline -> render_markdown).
        p = self._write({
            "task_frame": {"question": "Whoop price", "route": "B", "depth": "Standard", "language": "en"},
            "sources": [{"url": "https://cdek.shopping/whoop", "tier": "S", "published_at": "2026-06-25",
                         "scores": {"independence": 0.9, "traceability": 0.9, "corroboration": 0.8}}],
            "claims": [{"id": "C1", "text": "Whoop 30000", "sources": ["S1"]}],
            "now": NOW,
        })
        rc, out = self._run(["run", "-i", p])
        self.assertEqual(rc, 0)
        self.assertIn("# Report:", out)
        self.assertIn("## Sources", out)
        self.assertIn("Whoop 30000", out)
        self.assertNotIn("Отчёт", out)
        self.assertNotIn("Источники", out)

    def test_report(self):
        snap = Snapshot(
            run_id="r", task_fingerprint="f",
            task_frame=TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD),
            sources=[Source(id="S1", url="u", tier=Tier.S)],
            claims=[Claim(id="C1", text="verified fact", category=ClaimCategory.VERIFIED, confidence=4, sources=["S1"])],
        )
        rc, out = self._run(["report", "-i", self._write(snapshot_to_dict(snap))])
        self.assertEqual(rc, 0)
        self.assertIn("verified fact", out)

    def test_report_emits_english(self):
        # v1.4: the `report` verb also honors TaskFrame.language end-to-end.
        snap = Snapshot(
            run_id="r", task_fingerprint="f",
            task_frame=TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD, language="en"),
            sources=[Source(id="S1", url="u", tier=Tier.S)],
            claims=[Claim(id="C1", text="verified fact", category=ClaimCategory.VERIFIED, confidence=4, sources=["S1"])],
        )
        rc, out = self._run(["report", "-i", self._write(snapshot_to_dict(snap))])
        self.assertEqual(rc, 0)
        self.assertIn("# Report:", out)
        self.assertIn("## Sources", out)
        self.assertNotIn("Отчёт", out)


if __name__ == "__main__":
    unittest.main()
