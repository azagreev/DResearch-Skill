"""Phase 13 unit tests — Cost & Cache (Packet A).

Covers the FROZEN Phase-13 contract:
  telemetry  cache_hit_rate / bundle_hash / cache_fragmentation + the 5 sparse
             RunTrace.append cache/bundle kwargs (graceful absence when None).
  eval       cost_efficiency (division-by-zero safe).
  compact    COMPACTION_BOUNDARIES tuple + should_compact phase mapping.
  ci         ci_regression cost/latency thresholds (pass + fail), backward
             compatibility with the existing golden_corpus.json.
  cli        the `cost` subcommand end-to-end.
  determinism engine-emitted JSON has stable key order (serialised twice ->
              byte-identical).

Conventions mirror tests/test_phase11.py / test_phase12.py: stdlib unittest,
fixed NOW (no clock / no randomness), absolute engine imports, paths resolved
relative to this file. NO skip guards — every Packet-A file lands together.

Run from the skill dir:  python -m unittest tests.test_phase13 -v
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

_TESTS_DIR = Path(__file__).parent
_SKILL_DIR = _TESTS_DIR.parent
_EVALS_DIR = _SKILL_DIR / "evals"

if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

from engine import cli
from engine import compact as _compact
from engine import telemetry as _telemetry
from engine.eval import cost_efficiency
from engine.model import (
    Depth,
    Route,
    Snapshot,
    TaskFrame,
)
from engine.telemetry import (
    RunTrace,
    bundle_hash,
    cache_fragmentation,
    cache_hit_rate,
)

NOW = "2026-06-30T00:00:00Z"


def _snap(next_phase: int = 0, **kw) -> Snapshot:
    defaults = dict(
        run_id="r1",
        task_fingerprint="fp",
        task_frame=TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD),
        next_phase=next_phase,
    )
    defaults.update(kw)
    return Snapshot(**defaults)


# ===========================================================================
# AC13-1 — cache_hit_rate / bundle_hash / RunTrace cache-field graceful presence
# ===========================================================================

class TestCacheHitRate(unittest.TestCase):
    def test_basic_ratio(self):
        self.assertEqual(cache_hit_rate(75, 25), 0.75)

    def test_all_reads(self):
        self.assertEqual(cache_hit_rate(10, 0), 1.0)

    def test_all_writes(self):
        self.assertEqual(cache_hit_rate(0, 10), 0.0)

    def test_zero_division_returns_none(self):
        # read+write == 0 -> rate undefined, must be None (not 0.0).
        self.assertIsNone(cache_hit_rate(0, 0))

    def test_none_read_returns_none(self):
        self.assertIsNone(cache_hit_rate(None, 5))

    def test_none_write_returns_none(self):
        self.assertIsNone(cache_hit_rate(5, None))

    def test_both_none_returns_none(self):
        self.assertIsNone(cache_hit_rate(None, None))


class TestBundleHash(unittest.TestCase):
    def test_known_sha256_of_empty_string(self):
        # sha256("") is a fixed, well-known digest — proves it is real sha256.
        self.assertEqual(
            bundle_hash(""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_deterministic(self):
        self.assertEqual(bundle_hash("prefix-A"), bundle_hash("prefix-A"))

    def test_drift_changes_hash(self):
        self.assertNotEqual(bundle_hash("prefix-A"), bundle_hash("prefix-A "))

    def test_utf8_encoding(self):
        # Non-ASCII must hash without error and stay deterministic.
        self.assertEqual(bundle_hash("Москва"), bundle_hash("Москва"))
        self.assertEqual(len(bundle_hash("Москва")), 64)  # hex digest length


class TestRunTraceCacheFields(unittest.TestCase):
    def test_cache_fields_present_when_supplied(self):
        trace = RunTrace()
        trace.append(
            "turn",
            ts=NOW,
            prompt_bundle_hash="ph",
            tool_bundle_hash="th",
            cache_read_tokens=100,
            cache_write_tokens=20,
            cached_tokens=100,
        )
        row = trace.as_list()[0]
        self.assertEqual(row["prompt_bundle_hash"], "ph")
        self.assertEqual(row["tool_bundle_hash"], "th")
        self.assertEqual(row["cache_read_tokens"], 100)
        self.assertEqual(row["cache_write_tokens"], 20)
        self.assertEqual(row["cached_tokens"], 100)

    def test_cache_fields_absent_when_none(self):
        # Graceful: a host that reports no cache metrics leaves keys absent.
        trace = RunTrace()
        trace.append("turn", ts=NOW)
        row = trace.as_list()[0]
        for key in (
            "prompt_bundle_hash",
            "tool_bundle_hash",
            "cache_read_tokens",
            "cache_write_tokens",
            "cached_tokens",
        ):
            self.assertNotIn(key, row)
        # Only the always-present 'event' (+ supplied ts) remain.
        self.assertEqual(set(row), {"event", "ts"})

    def test_partial_cache_fields(self):
        # cached_tokens reported, the rest absent -> only that key appears.
        trace = RunTrace()
        trace.append("turn", cached_tokens=0)
        row = trace.as_list()[0]
        self.assertIn("cached_tokens", row)
        self.assertEqual(row["cached_tokens"], 0)  # 0 is reported, not dropped
        self.assertNotIn("cache_read_tokens", row)

    def test_existing_fields_unchanged(self):
        # Pure-additive: the original kwargs still behave as before.
        trace = RunTrace()
        trace.append("collect", tool_hash="h1", source_ref="S1", claim_id="C1",
                     why_stopped="budget", ts=NOW)
        row = trace.as_list()[0]
        self.assertEqual(row, {
            "event": "collect", "tool_hash": "h1", "source_ref": "S1",
            "claim_id": "C1", "why_stopped": "budget", "ts": NOW,
        })


# ===========================================================================
# AC13-2 — cache_fragmentation
# ===========================================================================

class TestCacheFragmentation(unittest.TestCase):
    def test_three_trailing_zeros_warns(self):
        self.assertEqual(cache_fragmentation([100, 0, 0, 0]), "WARNING")

    def test_exactly_three_zeros_warns(self):
        self.assertEqual(cache_fragmentation([0, 0, 0]), "WARNING")

    def test_mixed_tail_no_warning(self):
        # Last three are 0, 5, 0 -> not all zero.
        self.assertIsNone(cache_fragmentation([0, 0, 5, 0]))

    def test_none_breaks_zero_run(self):
        # A None in the trailing window means "unknown" != fragmented.
        self.assertIsNone(cache_fragmentation([0, None, 0]))

    def test_short_history_returns_none(self):
        self.assertIsNone(cache_fragmentation([0, 0]))      # fewer than threshold
        self.assertIsNone(cache_fragmentation([]))           # empty

    def test_leading_zeros_ignored_if_tail_nonzero(self):
        # Fragmentation looks only at the TAIL run.
        self.assertIsNone(cache_fragmentation([0, 0, 0, 50]))

    def test_custom_threshold(self):
        self.assertEqual(cache_fragmentation([0, 0], threshold=2), "WARNING")
        self.assertIsNone(cache_fragmentation([5, 0], threshold=2))

    def test_longer_run_than_threshold_still_warns(self):
        self.assertEqual(cache_fragmentation([0, 0, 0, 0, 0]), "WARNING")


# ===========================================================================
# AC13-3 — deterministic engine-emitted JSON key order
# ===========================================================================

class TestJsonDeterminism(unittest.TestCase):
    def test_runtrace_as_list_serialises_byte_identical(self):
        trace = RunTrace()
        trace.append("a", tool_hash="h", cache_read_tokens=10, cache_write_tokens=2, ts=NOW)
        trace.append("b", cached_tokens=0, ts=NOW)
        first = json.dumps(trace.as_list(), ensure_ascii=False)
        second = json.dumps(trace.as_list(), ensure_ascii=False)
        self.assertEqual(first, second)

    def test_cost_cli_output_byte_identical_across_runs(self):
        # The `cost` subcommand must emit the same bytes for the same input.
        payload = {
            "total_budget": 100.0,
            "spends": [
                {"gate": "gate_1_collection", "amount": 5.0},
                {"gate": "gate_3_analysis", "amount": 10.0},
            ],
        }
        out1 = _run_cost(payload)
        out2 = _run_cost(payload)
        self.assertEqual(out1, out2)


# ===========================================================================
# AC13-4 — COMPACTION_BOUNDARIES + should_compact
# ===========================================================================

class TestCompactionBoundaries(unittest.TestCase):
    def test_boundaries_exact_tuple(self):
        self.assertEqual(
            _compact.COMPACTION_BOUNDARIES,
            ("post_collection", "pre_synthesis", "pre_report"),
        )
        self.assertIsInstance(_compact.COMPACTION_BOUNDARIES, tuple)

    def test_post_collection_boundary(self):
        # cp_01_raw (AGENT.MD §8.0): collection done -> about to process (next_phase 3).
        self.assertEqual(_compact.should_compact(_snap(next_phase=3)), "post_collection")

    def test_pre_synthesis_boundary(self):
        # pipeline.build_snapshot sets next_phase=5 once about to synthesize.
        self.assertEqual(_compact.should_compact(_snap(next_phase=5)), "pre_synthesis")

    def test_pre_report_boundary(self):
        self.assertEqual(_compact.should_compact(_snap(next_phase=6)), "pre_report")

    def test_off_boundary_returns_none(self):
        # next_phase 2 is *pre*-collection (cp_01_raw is next_phase 3), so it is
        # off-boundary; 0/1/4 are likewise not compaction points.
        for np in (0, 1, 2, 4):
            self.assertIsNone(
                _compact.should_compact(_snap(next_phase=np)),
                f"next_phase={np} should be off-boundary",
            )

    def test_every_boundary_name_is_reachable(self):
        produced = {
            _compact.should_compact(_snap(next_phase=np))
            for np in (3, 5, 6)
        }
        self.assertEqual(produced, set(_compact.COMPACTION_BOUNDARIES))

    def test_should_compact_is_pure(self):
        snap = _snap(next_phase=3)
        before = snap.next_phase
        _compact.should_compact(snap)
        self.assertEqual(snap.next_phase, before)


# ===========================================================================
# AC13-5 — cost_efficiency + ci_regression cost thresholds + golden backward-compat
# ===========================================================================

class TestCostEfficiency(unittest.TestCase):
    def test_basic_math(self):
        result = cost_efficiency(n_items=10, cost_usd=5.0, elapsed_sec=2.0)
        self.assertEqual(result["cost_per_item"], 0.5)
        self.assertEqual(result["items_per_sec"], 5.0)

    def test_zero_items_safe(self):
        result = cost_efficiency(n_items=0, cost_usd=5.0, elapsed_sec=2.0)
        self.assertEqual(result["cost_per_item"], 0.0)
        self.assertEqual(result["items_per_sec"], 0.0)

    def test_zero_elapsed_safe(self):
        result = cost_efficiency(n_items=10, cost_usd=5.0, elapsed_sec=0.0)
        self.assertEqual(result["items_per_sec"], 0.0)
        self.assertEqual(result["cost_per_item"], 0.5)

    def test_returns_only_two_keys(self):
        self.assertEqual(
            set(cost_efficiency(1, 1.0, 1.0)),
            {"cost_per_item", "items_per_sec"},
        )


class TestCiRegressionCost(unittest.TestCase):
    def _run_regression(self):
        from evals.ci_regression import run_regression
        return run_regression

    def _cost_corpus(self) -> str:
        """A one-case corpus carrying cost_usd + elapsed_sec + n_items.

        IR metrics are perfect (ranked == relevant), so any pass/fail is driven
        solely by the cost/latency thresholds — non-vacuous.
        """
        corpus = [{
            "query": "cost case",
            "ranked_ids": ["S1", "S2"],
            "relevant_ids": ["S1", "S2"],
            "n_items": 10,
            "cost_usd": 5.0,      # -> cost_per_item 0.5
            "elapsed_sec": 2.0,   # -> items_per_sec 5.0
        }]
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(corpus, handle)
        handle.close()
        self.addCleanup(lambda: os.unlink(handle.name))
        return handle.name

    def test_cost_threshold_pass(self):
        run_regression = self._run_regression()
        outcome = run_regression(
            corpus_path=self._cost_corpus(),
            thresholds={"cost_per_item_max": 1.0, "min_items_per_sec": 1.0},
        )
        self.assertTrue(outcome["passed"], outcome["results"])
        metrics = outcome["results"][0]["metrics"]
        self.assertEqual(metrics["cost_per_item"], 0.5)
        self.assertEqual(metrics["items_per_sec"], 5.0)

    def test_cost_threshold_fail_on_cost(self):
        run_regression = self._run_regression()
        outcome = run_regression(
            corpus_path=self._cost_corpus(),
            thresholds={"cost_per_item_max": 0.1},  # 0.5 > 0.1 -> fail
        )
        self.assertFalse(outcome["passed"])
        failures = outcome["results"][0]["failures"]
        self.assertTrue(any("cost_per_item" in f for f in failures), failures)

    def test_cost_threshold_fail_on_latency(self):
        run_regression = self._run_regression()
        outcome = run_regression(
            corpus_path=self._cost_corpus(),
            thresholds={"min_items_per_sec": 100.0},  # 5.0 < 100 -> fail
        )
        self.assertFalse(outcome["passed"])
        failures = outcome["results"][0]["failures"]
        self.assertTrue(any("items_per_sec" in f for f in failures), failures)

    def test_case_without_cost_keys_skips_cost_check(self):
        # Backward compat: even an impossibly strict cost threshold cannot fail a
        # case that carries no cost_usd/elapsed_sec.
        run_regression = self._run_regression()
        outcome = run_regression(
            thresholds={"cost_per_item_max": 0.0, "min_items_per_sec": 1e9},
        )
        # The golden corpus has no cost keys, so cost thresholds are inert.
        self.assertTrue(outcome["passed"], outcome["results"])
        for r in outcome["results"]:
            self.assertNotIn("cost_per_item", r["metrics"])

    def test_existing_golden_corpus_still_passes(self):
        # AC13-5 explicit backward-compat: the shipped golden_corpus.json must
        # still return passed=True with default thresholds.
        run_regression = self._run_regression()
        outcome = run_regression()
        self.assertTrue(outcome["passed"], outcome["results"])


# ===========================================================================
# AC13-5 — cli `cost` subcommand end-to-end
# ===========================================================================

def _run_cost(payload: dict) -> str:
    """Drive `cost` through cli.main with a temp JSON file; return raw stdout."""
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(payload, handle)
    handle.close()
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main(["cost", "-i", handle.name])
        assert rc == 0, f"cost exited {rc}"
        return buf.getvalue()
    finally:
        os.unlink(handle.name)


class TestCostCli(unittest.TestCase):
    def test_cost_end_to_end_report_shape(self):
        out = json.loads(_run_cost({
            "total_budget": 100.0,
            "spends": [
                {"gate": "gate_1_collection", "amount": 5.0},
                {"gate": "gate_3_analysis", "amount": 10.0},
            ],
        }))
        self.assertEqual(set(out), {"per_gate", "total_spent", "total_remaining", "alerts"})
        self.assertEqual(out["total_spent"], 15.0)
        self.assertEqual(out["total_remaining"], 85.0)
        self.assertIn("gate_1_collection", out["per_gate"])
        self.assertIn("gate_3_analysis", out["per_gate"])
        # Modest spends -> no alerts.
        self.assertEqual(out["alerts"], [])

    def test_cost_alert_surfaces(self):
        # gate_2_processing allocation = 10% of 100 = 10.0; spending 9.5 -> 95% -> CRITICAL.
        out = json.loads(_run_cost({
            "total_budget": 100.0,
            "spends": [{"gate": "gate_2_processing", "amount": 9.5}],
        }))
        self.assertIn("gate_2_processing", out["alerts"])
        self.assertEqual(out["per_gate"]["gate_2_processing"]["alert"], "CRITICAL")

    def test_cost_accumulates_per_gate(self):
        # Two spends on the same gate accumulate; per_gate keeps the last snapshot.
        out = json.loads(_run_cost({
            "total_budget": 100.0,
            "spends": [
                {"gate": "gate_1_collection", "amount": 3.0},
                {"gate": "gate_1_collection", "amount": 4.0},
            ],
        }))
        self.assertEqual(out["per_gate"]["gate_1_collection"]["spent"], 7.0)
        self.assertEqual(out["total_spent"], 7.0)

    def test_cost_no_spends(self):
        out = json.loads(_run_cost({"total_budget": 50.0, "spends": []}))
        self.assertEqual(out["total_spent"], 0.0)
        self.assertEqual(out["total_remaining"], 50.0)
        self.assertEqual(out["per_gate"], {})
        self.assertEqual(out["alerts"], [])


if __name__ == "__main__":
    unittest.main()
