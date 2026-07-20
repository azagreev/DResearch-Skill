"""R1 - lenient-then-strict CLI input parsing (bounded, stdlib-only repair).

Covers AC1.1..AC1.5 and the AC1.E2E end-to-end path through `cli run`.
Invariant under test: a successful (possibly repaired) parse NEVER bypasses
the downstream typed validators (`_source_from`/`_claim_from`/
`_task_frame_from`/`snapshot_from_dict`) - repair fixes syntax only.

Run from the skill dir:
    python -m unittest tests.test_r1_lenient_input -v
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from engine import cli

NOW = "2026-06-30T00:00:00Z"


class LenientInputTest(unittest.TestCase):
    def _write_text(self, text: str) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        handle.write(text)
        handle.close()
        self.addCleanup(lambda: os.unlink(handle.name))
        return handle.name

    def _run(self, argv):
        out_buf, err_buf = io.StringIO(), io.StringIO()
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            rc = cli.main(argv)
        return rc, out_buf.getvalue(), err_buf.getvalue()

    # AC1.1 - valid JSON parses identically (no regression).
    def test_ac1_1_valid_json_parses_identically(self):
        obj = {"sources": [{"id": "S1", "url": "u", "tier": "S"}], "streams": {"q1": ["S1"]}}
        raw = json.dumps(obj)
        parsed = cli._lenient_loads(raw)
        self.assertEqual(parsed, obj)

        p = self._write_text(raw)
        rc, out, _err = self._run(["rank", "-i", p])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["ranked"][0]["id"], "S1")

    # AC1.2a - markdown code-fence stripped.
    def test_ac1_2a_markdown_code_fence_repaired(self):
        obj = {"sources": [{"id": "S1", "url": "u", "tier": "S"}]}
        fenced = "```json\n" + json.dumps(obj) + "\n```"
        parsed = cli._lenient_loads(fenced)
        self.assertEqual(parsed, obj)

    # AC1.2b - trailing commas removed.
    def test_ac1_2b_trailing_commas_repaired(self):
        raw = '{"sources": [{"id": "S1", "url": "u", "tier": "S",},],}'
        parsed = cli._lenient_loads(raw)
        self.assertEqual(parsed, {"sources": [{"id": "S1", "url": "u", "tier": "S"}]})

    # AC1.2c - smart/typographic quotes normalized to straight quotes.
    def test_ac1_2c_smart_typographic_quotes_repaired(self):
        raw = "{“sources”: []}"
        parsed = cli._lenient_loads(raw)
        self.assertEqual(parsed, {"sources": []})

    # AC1.3 - repaired SYNTAX still passes through real typed validation.
    def test_ac1_3_repaired_syntax_still_rejected_by_downstream_typed_validation(self):
        from engine.model import _source_from

        raw = '{"id": "S1", "url": "u", "tier": "NOT_A_REAL_TIER",}'
        parsed = cli._lenient_loads(raw)
        self.assertEqual(parsed["tier"], "NOT_A_REAL_TIER")

        with self.assertRaises(ValueError):
            _source_from(parsed)

        p = self._write_text('{"sources": [{"id": "S1", "url": "u", "tier": "NOT_A_REAL_TIER",}], "now": "%s"}' % NOW)
        with self.assertRaises(ValueError):
            self._run(["score", "-i", p])

    # AC1.4 - unrepairable input -> explicit error, non-zero exit, never None.
    def test_ac1_4_unrepairable_input_raises_explicit_error_nonzero_exit(self):
        raw = "{ this is not json at all :::: [[[ "
        with self.assertRaises(cli.InputParseError):
            cli._lenient_loads(raw)

        p = self._write_text(raw)
        rc, out, err = self._run(["rank", "-i", p])
        self.assertNotEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertTrue(err)

    # AC1.5 - stdlib-only, deterministic.
    def test_ac1_5_stdlib_only_and_deterministic(self):
        import engine.cli as cli_mod

        with open(cli_mod.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("json5", src)

        raw = "```json\n" + '{"a": [1, 2, 3,],}' + "\n```"
        first = cli._lenient_loads(raw)
        second = cli._lenient_loads(raw)
        third = cli._lenient_loads(raw)
        self.assertEqual(first, second)
        self.assertEqual(second, third)
        self.assertEqual(first, {"a": [1, 2, 3]})

    # AC1.E2E - code-fence AND trailing comma together, through `cli run`.
    def test_ac1_e2e_code_fence_and_trailing_comma_through_run(self):
        body = """
{
  "task_frame": {"question": "Whoop price", "route": "B", "depth": "Standard"},
  "sources": [
    {
      "url": "https://cdek.shopping/whoop",
      "tier": "S",
      "published_at": "2026-06-25",
      "scores": {"independence": 0.9, "traceability": 0.9, "corroboration": 0.8},
    },
  ],
  "claims": [{"id": "C1", "text": "Whoop 30000", "sources": ["S1"]}],
  "now": "%s"
}
""" % NOW
        fenced = "```json\n" + body + "\n```"

        p = self._write_text(fenced)
        rc, out, _err = self._run(["run", "-i", p])
        self.assertEqual(rc, 0)
        self.assertIn("Whoop 30000", out)


if __name__ == "__main__":
    unittest.main()