"""Tests for R3 — honest judge: robust parse + dual-denominator accuracy + pinned
JudgeConfig + import-guard (bench.judge stays LLM-free; engine stays bench-free).

Style follows bench/tests/test_collate.py. Modules under test
(bench/judge/parse.py, bench/judge/config.py) do not exist yet at RED time; we
import them defensively inside setUp/helpers so a missing module surfaces as an
assertion failure (`self.fail(...)`), not a bare ImportError/collection error.
"""

from __future__ import annotations

import ast
import importlib
import os
import unittest


def _try_import(module_name: str):
    """Import `module_name`, returning (module, error_message_or_None)."""
    try:
        return importlib.import_module(module_name), None
    except Exception as exc:  # noqa: BLE001 - want any import failure surfaced
        return None, f"{module_name} failed to import: {exc!r}"


class ParseJudgeResponseTest(unittest.TestCase):
    """AC3.1 — extract-before-verdict, markdown tolerance, ok=False when unparsable."""

    def setUp(self):
        module, err = _try_import("bench.judge.parse")
        if module is None:
            self.fail(
                "bench.judge.parse does not exist yet (RED expected): " + str(err)
            )
        self.parse_judge_response = getattr(module, "parse_judge_response", None)
        if self.parse_judge_response is None:
            self.fail("bench.judge.parse.parse_judge_response is not defined")

    def test_extracted_final_answer_before_verdict_bold_markdown(self):
        raw = (
            "Reasoning: the answer discusses status of the pipeline.\n"
            "**extracted_final_answer:** The paper reports a 12% reduction.\n"
            "**status:** **MET**\n"
        )
        out = self.parse_judge_response(raw)
        self.assertTrue(out["ok"])
        self.assertEqual(out["status"], "MET")
        self.assertTrue(out["met"])
        self.assertIn("12% reduction", out["extracted_final_answer"])

    def test_plain_status_no_markdown(self):
        raw = "extracted_final_answer: no citation found\nstatus: UNMET\n"
        out = self.parse_judge_response(raw)
        self.assertTrue(out["ok"])
        self.assertEqual(out["status"], "UNMET")
        self.assertFalse(out["met"])

    def test_verdict_only_searched_after_extracted_answer_offset(self):
        # The word "status: MET" appears INSIDE the extracted-answer body itself
        # (same line, so it cannot spill into the next line's real verdict); the
        # real verdict directly follows on its own line and must win.
        raw = (
            "extracted_final_answer: The report mentions status: MET nowhere else.\n"
            "status: UNMET\n"
        )
        out = self.parse_judge_response(raw)
        self.assertTrue(out["ok"])
        self.assertEqual(out["status"], "UNMET")
        self.assertFalse(out["met"])

    def test_unparsable_returns_ok_false(self):
        raw = "The judge rambles with no clear verdict token anywhere in here."
        out = self.parse_judge_response(raw)
        self.assertFalse(out["ok"])
        self.assertIsNone(out["status"])
        self.assertIsNone(out["met"])

    def test_case_and_spacing_tolerant(self):
        raw = "extracted_final_answer: x\nStatus : Met\n"
        out = self.parse_judge_response(raw)
        self.assertTrue(out["ok"])
        self.assertEqual(out["status"], "MET")
        self.assertTrue(out["met"])


class DualAccuracyTest(unittest.TestCase):
    """AC3.2 — judged vs overall accuracy + breakdown; equal when all judged."""

    def setUp(self):
        module, err = _try_import("bench.score")
        if module is None:
            self.fail("bench.score failed to import: " + str(err))
        self.dual_accuracy = getattr(module, "dual_accuracy", None)
        if self.dual_accuracy is None:
            self.fail(
                "bench.score.dual_accuracy is not defined yet (RED expected for AC3.2)"
            )

    def test_all_judged_accuracies_equal(self):
        out = self.dual_accuracy(met=7, unmet=3, unjudged=0)
        self.assertAlmostEqual(out["judged_accuracy"], out["overall_accuracy"])
        self.assertAlmostEqual(out["judged_accuracy"], 0.7)
        self.assertEqual(
            out["breakdown"], {"met": 7, "unmet": 3, "unjudged": 0, "total": 10}
        )

    def test_partial_unjudged_denominators_differ(self):
        out = self.dual_accuracy(met=6, unmet=2, unjudged=2)
        self.assertAlmostEqual(out["judged_accuracy"], 6 / 8)
        self.assertAlmostEqual(out["overall_accuracy"], 6 / 10)
        self.assertNotAlmostEqual(out["judged_accuracy"], out["overall_accuracy"])
        self.assertEqual(out["breakdown"]["total"], 10)

    def test_zero_denominators_do_not_raise(self):
        out = self.dual_accuracy(met=0, unmet=0, unjudged=0)
        self.assertEqual(out["judged_accuracy"], 0.0)
        self.assertEqual(out["overall_accuracy"], 0.0)


class PinnedJudgeConfigTest(unittest.TestCase):
    """AC3.3 — JudgeConfig requires model+temperature+prompt_hash; recorded in verdicts."""

    def setUp(self):
        module, err = _try_import("bench.judge.config")
        if module is None:
            self.fail(
                "bench.judge.config does not exist yet (RED expected): " + str(err)
            )
        self.JudgeConfig = getattr(module, "JudgeConfig", None)
        if self.JudgeConfig is None:
            self.fail("bench.judge.config.JudgeConfig is not defined")

    def test_valid_config_round_trips_as_dict(self):
        cfg = self.JudgeConfig.from_mapping(
            {"model": "opus", "temperature": 0.0, "prompt_hash": "abc123"}
        )
        d = cfg.as_dict()
        self.assertEqual(d["model"], "opus")
        self.assertEqual(d["temperature"], 0.0)
        self.assertEqual(d["prompt_hash"], "abc123")

    def test_missing_field_is_rejected(self):
        with self.assertRaises(ValueError):
            self.JudgeConfig.from_mapping({"model": "opus", "temperature": 0.0})

    def test_temperature_zero_is_not_treated_as_missing(self):
        # temperature == 0 is falsy in Python; must be accepted (presence, not truthiness).
        cfg = self.JudgeConfig.from_mapping(
            {"model": "opus", "temperature": 0, "prompt_hash": "deadbeef"}
        )
        self.assertEqual(cfg.as_dict()["temperature"], 0)

    def test_config_is_recorded_via_build_verdicts(self):
        from bench.judge.collate import build_verdicts

        cfg = self.JudgeConfig.from_mapping(
            {"model": "opus", "temperature": 0.0, "prompt_hash": "deadbeef"}
        )
        out = build_verdicts(
            arm="with_skill",
            task_id="T1",
            results=[{"criterion_id": "c1", "status": "MET"}],
            judge=cfg.as_dict(),
        )
        self.assertEqual(out["judge"]["prompt_hash"], "deadbeef")
        self.assertEqual(out["judge"]["model"], "opus")


class ImportGuardTest(unittest.TestCase):
    """AC3.4 — bench.judge does not import the engine-side judge; engine does not
    import bench. Static AST scan, deterministic, no runtime sys.modules pollution."""

    _REPO_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    _BENCH_JUDGE_DIR = os.path.join(_REPO_ROOT, "bench", "judge")
    _ENGINE_DIR = os.path.join(
        _REPO_ROOT,
        "plugins", "deep-research-skill", "skills", "deep-research-skill", "engine",
    )

    def _imported_module_names(self, path: str):
        with open(path, "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module)
        return names

    @staticmethod
    def _py_files(root: str):
        """All .py files under root, recursively (defence-in-depth: a future
        subpackage importing across the boundary is still caught)."""
        found = []
        for dirpath, _dirs, files in os.walk(root):
            if "__pycache__" in dirpath:
                continue
            for fname in files:
                if fname.endswith(".py"):
                    found.append(os.path.join(dirpath, fname))
        return sorted(found)

    def test_bench_judge_does_not_import_engine(self):
        self.assertTrue(
            os.path.isdir(self._BENCH_JUDGE_DIR),
            f"expected {self._BENCH_JUDGE_DIR} to exist",
        )
        offenders = []
        for path in self._py_files(self._BENCH_JUDGE_DIR):
            fname = os.path.relpath(path, self._BENCH_JUDGE_DIR)
            for name in self._imported_module_names(path):
                if name == "engine" or name.startswith("engine."):
                    offenders.append((fname, name))
                if name in ("bench.trust", "bench.trust._engine") or name.startswith(
                    "bench.trust."
                ):
                    offenders.append((fname, name))
        self.assertEqual(
            offenders, [], f"bench/judge must not import the engine-side judge: {offenders}"
        )

    def test_engine_does_not_import_bench(self):
        if not os.path.isdir(self._ENGINE_DIR):
            self.skipTest(f"engine dir not found at {self._ENGINE_DIR}; skipping")
        offenders = []
        for path in self._py_files(self._ENGINE_DIR):
            fname = os.path.relpath(path, self._ENGINE_DIR)
            for name in self._imported_module_names(path):
                if name == "bench" or name.startswith("bench."):
                    offenders.append((fname, name))
        self.assertEqual(
            offenders, [], f"engine must not import bench: {offenders}"
        )


class DeterminismTest(unittest.TestCase):
    """AC3.5 — bench pure functions are deterministic (same input -> same output)."""

    def test_parse_judge_response_is_deterministic(self):
        module, err = _try_import("bench.judge.parse")
        if module is None:
            self.fail(
                "bench.judge.parse does not exist yet (RED expected): " + str(err)
            )
        parse_judge_response = module.parse_judge_response
        raw = "extracted_final_answer: x\n**status:** **MET**\n"
        results = {parse_judge_response(raw)["status"] for _ in range(20)}
        self.assertEqual(results, {"MET"})

    def test_dual_accuracy_is_deterministic(self):
        from bench.score import dual_accuracy

        results = {
            (
                dual_accuracy(met=5, unmet=2, unjudged=1)["judged_accuracy"],
                dual_accuracy(met=5, unmet=2, unjudged=1)["overall_accuracy"],
            )
            for _ in range(20)
        }
        self.assertEqual(len(results), 1)

    def test_judge_config_from_mapping_is_deterministic(self):
        module, err = _try_import("bench.judge.config")
        if module is None:
            self.fail(
                "bench.judge.config does not exist yet (RED expected): " + str(err)
            )
        JudgeConfig = module.JudgeConfig
        mapping = {"model": "opus", "temperature": 0.0, "prompt_hash": "abc"}
        outs = {
            tuple(sorted(JudgeConfig.from_mapping(mapping).as_dict().items()))
            for _ in range(20)
        }
        self.assertEqual(len(outs), 1)


if __name__ == "__main__":
    unittest.main()
