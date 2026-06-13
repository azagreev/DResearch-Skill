"""Phase 11 unit tests — independent verifier + budget/telemetry/hook plumbing.

Conventions mirror tests/test_phase7.py: stdlib `unittest`, a fixed NOW (no
clock/random), absolute-import the engine package.

This module owns the verifier (engine/verify.py, this builder) and exercises the
FROZEN contracts of telemetry (Builder B) and the hooks + hook CLI (Builder A),
which land in the same tree. Tests that depend on another builder's file skip
cleanly (skipUnless / skipIf) when that file is not present yet, so this suite is
green on its own and tightens automatically once A/B land.

Run from the skill dir:  python -m unittest tests.test_phase11 -v
"""

import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
import unittest

from engine import verify
from engine.model import (
    Claim,
    ClaimCategory,
    ClaimStatus,
    Source,
    Tier,
)

NOW = "2026-06-30T00:00:00Z"

# --------------------------------------------------------------------------- #
# Locate sibling-builder artifacts (may not exist until A/B land).
# --------------------------------------------------------------------------- #
_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.abspath(os.path.join(_SKILL_DIR, "..", "..", "..", ".."))
_HOOKS_DIR = os.path.join(_SKILL_DIR, "hooks")
_BUDGET_GUARD = os.path.join(_HOOKS_DIR, "budget_guard.py")

_HAS_TELEMETRY = importlib.util.find_spec("engine.telemetry") is not None
_HAS_BUDGET_GUARD = os.path.isfile(_BUDGET_GUARD)


def _cli_has_hook_subcommand() -> bool:
    """True once Builder A wires the `hook` subcommand into engine/cli.py.

    Probed by running `python -m engine hook --op list` and checking that argparse
    accepted `hook` as a valid choice (a missing subcommand prints
    'invalid choice: hook'). Independent of whether the op itself succeeds.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "engine", "hook", "--op", "list"],
            cwd=_SKILL_DIR,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return "invalid choice: 'hook'" not in (proc.stdout + proc.stderr)


_HAS_HOOK_CLI = _HAS_BUDGET_GUARD and _cli_has_hook_subcommand()


# --------------------------------------------------------------------------- #
# AC11-5 — independent verifier
# --------------------------------------------------------------------------- #
class TestVerify(unittest.TestCase):
    def test_reverify_matches_factcheck_on_agreeing_case(self):
        """A claim backed by a single Tier-S source re-derives to VERIFIED, the
        same verdict engine.factcheck would assign; disagreement() is False."""
        sources = [Source(id="S1", url="u", tier=Tier.S)]
        claim = Claim(
            id="C1",
            text="x",
            sources=["S1"],
            category=ClaimCategory.VERIFIED,  # author's recorded verdict
        )
        self.assertEqual(verify.reverify_claim(claim, sources, NOW), ClaimCategory.VERIFIED)
        self.assertFalse(verify.disagreement(claim, sources, NOW))

    def test_disagreement_true_when_category_tampered(self):
        """Non-vacuous disagreement: the EVIDENCE (one Tier-S *contradicting*
        source, zero supporting) supports FALSE, but the claim's category field
        has been hand-set to VERIFIED. The verifier re-derives FALSE from the
        evidence alone, so it must flag the mismatch.

        This is not vacuously true: reverify_claim independently computes the
        correct category (FALSE) — proven by the explicit assertion below — and
        FALSE != the tampered VERIFIED is what makes disagreement() True. Swap
        the contradicting source back to a supporting one and the same claim
        would re-derive VERIFIED and disagreement() would be False (covered by
        the agreeing-case test), so the True result is driven by the evidence,
        not by the verifier always returning True."""
        sources = [Source(id="S1", url="u", tier=Tier.S)]
        tampered = Claim(
            id="C1",
            text="x",
            sources=[],                       # no supporting evidence
            contradicting_sources=["S1"],     # a strong source contradicts it
            category=ClaimCategory.VERIFIED,  # ...yet recorded as VERIFIED (tampered)
        )
        # The independent re-derivation reflects the evidence, not the field.
        self.assertEqual(verify.reverify_claim(tampered, sources, NOW), ClaimCategory.FALSE)
        self.assertNotEqual(verify.reverify_claim(tampered, sources, NOW), tampered.category)
        self.assertTrue(verify.disagreement(tampered, sources, NOW))

    def test_reverify_does_not_mutate_claim(self):
        """reverify_claim is read-only on the claim: every field (including
        status/confidence/category) is byte-for-byte identical afterwards."""
        sources = [Source(id="S1", url="u", tier=Tier.S)]
        claim = Claim(
            id="C1",
            text="x",
            sources=["S1"],
            category=ClaimCategory.UNVERIFIED,
            confidence=2,
            status=ClaimStatus.PENDING,
        )
        before = dataclasses.asdict(claim)
        result = verify.reverify_claim(claim, sources, NOW)
        self.assertEqual(dataclasses.asdict(claim), before)  # untouched
        self.assertEqual(result, ClaimCategory.VERIFIED)     # but still derived a verdict

    def test_reverify_ignores_verdict_explanation(self):
        """Independence: the author's verdict_explanation must NOT influence the
        verdict. Two claims with identical evidence but different (and even
        misleading) explanations re-derive to the same category."""
        sources = [Source(id="S1", url="u", tier=Tier.S)]
        with_misleading = Claim(
            id="C1", text="x", sources=["S1"],
            verdict_explanation="author says this is FALSE and unsupported",
        )
        without = Claim(id="C2", text="x", sources=["S1"], verdict_explanation=None)
        self.assertEqual(
            verify.reverify_claim(with_misleading, sources, NOW),
            verify.reverify_claim(without, sources, NOW),
        )
        self.assertEqual(verify.reverify_claim(with_misleading, sources, NOW), ClaimCategory.VERIFIED)


# --------------------------------------------------------------------------- #
# Budget-guard hook (Builder A) — run via subprocess per HOOK_MIDDLEWARE §3.1.
# --------------------------------------------------------------------------- #
@unittest.skipUnless(_HAS_BUDGET_GUARD, "hooks/budget_guard.py not present yet (Builder A)")
class TestBudgetGuardHook(unittest.TestCase):
    def _fire(self, payload: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, _BUDGET_GUARD],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
        )

    def test_paid_tool_over_budget_blocks_exit_2(self):
        proc = self._fire(
            {"tool": "firecrawl", "spent_usd": 9.95, "limit_usd": 10.0, "est_cost_usd": 0.10}
        )
        self.assertEqual(proc.returncode, 2)  # paid tool && spent+est >= limit -> block

    def test_paid_tool_within_budget_allows_exit_0(self):
        proc = self._fire(
            {"tool": "firecrawl", "spent_usd": 1.0, "limit_usd": 10.0, "est_cost_usd": 0.10}
        )
        self.assertEqual(proc.returncode, 0)  # comfortably under limit -> allow

    def test_fail_open_on_malformed_stdin(self):
        """A blocking PreToolUse hook must FAIL OPEN: malformed input -> exit 0,
        never block. (Code-review hardening; fail-closed once risked locking the
        whole session.)"""
        proc = subprocess.run(
            [sys.executable, _BUDGET_GUARD],
            input="not json at all {{{",
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0)

    def test_fail_open_on_non_numeric_budget(self):
        proc = self._fire(
            {"tool": "firecrawl", "spent_usd": "lots", "limit_usd": 10.0}
        )
        self.assertEqual(proc.returncode, 0)  # non-numeric -> fail open, not block

    def test_policy_guard_fails_open_on_malformed_stdin(self):
        policy = os.path.join(_HOOKS_DIR, "policy_guard.py")
        proc = subprocess.run(
            [sys.executable, policy],
            input="}{ broken",
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0)


# --------------------------------------------------------------------------- #
# Hook CLI: `python -m engine hook --op test` (Builder A wires cli.py).
# --------------------------------------------------------------------------- #
class TestHookCli(unittest.TestCase):
    def _run_module(self, argv):
        return subprocess.run(
            [sys.executable, "-m", "engine", *argv],
            cwd=_SKILL_DIR,
            capture_output=True,
            text=True,
        )

    @unittest.skipUnless(_HAS_HOOK_CLI, "`hook` subcommand not wired into cli.py yet (Builder A)")
    def test_hook_op_test_reports_block_exit_code(self):
        """`hook --op test --script <hook> --payload <json>` runs a hook on a
        fixture and reports its exit code. Firing budget_guard with an
        over-budget paid-tool fixture must surface exit_code 2 + blocked=True
        (the blocking exit per HOOK_MIDDLEWARE §3.1)."""
        fixture = json.dumps(
            {"tool": "firecrawl", "spent_usd": 9.95, "limit_usd": 10.0, "est_cost_usd": 0.10}
        )
        proc = self._run_module(
            ["hook", "--op", "test", "--script", _BUDGET_GUARD, "--payload", fixture]
        )
        self.assertEqual(proc.returncode, 0)  # the CLI wrapper itself succeeds
        report = json.loads(proc.stdout)
        self.assertEqual(report["exit_code"], 2)  # underlying hook blocked
        self.assertTrue(report["blocked"])

    @unittest.skipUnless(_HAS_HOOK_CLI, "`hook` subcommand not wired into cli.py yet (Builder A)")
    def test_hook_op_list_runs(self):
        """`hook --op list` enumerates registered hooks without error."""
        proc = self._run_module(["hook", "--op", "list"])
        self.assertEqual(proc.returncode, 0)


# --------------------------------------------------------------------------- #
# Telemetry (Builder B) — GateCostTracker alerts + RunTrace shape.
# --------------------------------------------------------------------------- #
@unittest.skipUnless(_HAS_TELEMETRY, "engine/telemetry.py not present yet (Builder B)")
class TestTelemetry(unittest.TestCase):
    def _tracker(self, gate: str, total_budget: float = 100.0):
        """Build a tracker and return (tracker, gate, gate_allocation_usd)."""
        from engine.telemetry import GateCostTracker

        tracker = GateCostTracker(total_budget)
        frac = GateCostTracker.BUDGET_ALLOCATION[gate]
        return tracker, gate, total_budget * frac

    def test_spend_crosses_alert_thresholds(self):
        from engine.telemetry import GateCostTracker

        gate = next(iter(GateCostTracker.BUDGET_ALLOCATION))  # any allocated gate
        tracker, gate, alloc = self._tracker(gate)

        # Below 75% of this gate's allocation -> no alert.
        r = tracker.spend(gate, alloc * 0.50)
        self.assertIsNone(r["alert"])
        # Cross 75% -> WARNING.
        r = tracker.spend(gate, alloc * 0.30)  # cumulative 0.80
        self.assertEqual(r["alert"], "WARNING")
        # Cross 90% -> CRITICAL.
        r = tracker.spend(gate, alloc * 0.12)  # cumulative 0.92
        self.assertEqual(r["alert"], "CRITICAL")
        # Cross 100% -> EXHAUSTED.
        r = tracker.spend(gate, alloc * 0.10)  # cumulative 1.02
        self.assertEqual(r["alert"], "EXHAUSTED")

    def test_budget_allocation_fractions_sane(self):
        from engine.telemetry import GateCostTracker

        self.assertTrue(GateCostTracker.BUDGET_ALLOCATION)  # non-empty (ported from §3.4)
        for frac in GateCostTracker.BUDGET_ALLOCATION.values():
            self.assertGreaterEqual(frac, 0.0)
            self.assertLessEqual(frac, 1.0)

    def test_runtrace_append_and_as_list_shape(self):
        from engine.telemetry import RunTrace

        trace = RunTrace()
        trace.append("collect", tool_hash="h1", source_ref="S1", ts=NOW)
        trace.append("stop", why_stopped="budget", claim_id="C1", ts=NOW)

        self.assertEqual(len(trace.events), 2)
        rows = trace.as_list()
        self.assertIsInstance(rows, list)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIsInstance(row, dict)
            self.assertIn("event", row)
        self.assertEqual(rows[0]["event"], "collect")
        self.assertEqual(rows[1]["event"], "stop")


if __name__ == "__main__":
    unittest.main()
