"""Phase 14 unit tests — rescore (full re-derivation) + read-only invariant.

Covers AC14-3: rescore_snapshot recomputes tiers/confidence/verdicts from the
*cached* score components, propagates a tier change into claim confidence AND
factcheck category (deep mode), leaves the category stale + warns (--shallow),
is idempotent on an unchanged rubric, and is deterministic. The source payload
(url / raw_path / extract) is held read-only; a mutating fixture surfaces via
the changed-id list and the CLI exit-1 path.

Run from the skill dir:  python -m unittest tests.test_phase14_rescore -v
"""

import io
import json
import unittest
from contextlib import redirect_stdout

from engine import cli
from engine.model import (
    Claim,
    ClaimCategory,
    Depth,
    Route,
    ScoreComponents,
    Snapshot,
    Source,
    SourceStatus,
    TaskFrame,
    Tier,
    snapshot_to_dict,
)
from engine.state import rescore_snapshot

# Fixed clock — tests never read the system clock.
NOW = "2026-06-30T00:00:00Z"


def _components_for_tier_s() -> ScoreComponents:
    """Cached components whose composite (~0.955) re-derives to Tier S.
    All five sub-scores are already filled, so score_source leaves Authority
    untouched (it only seeds when authority is None) and the rescore is a pure
    re-derivation of composite -> tier."""
    return ScoreComponents(
        authority=1.0, recency=0.9, independence=1.0, traceability=1.0, corroboration=0.8,
    )


def make_snapshot(*, stale_tier=Tier.B, stale_category=ClaimCategory.UNVERIFIED):
    """A snapshot whose stored tier/category are deliberately STALE relative to
    the cached components, so a correct rescore visibly changes them."""
    return Snapshot(
        run_id="r1",
        task_fingerprint="fp",
        task_frame=TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD),
        created_utc=NOW,
        sources=[
            Source(
                id="S1",
                url="https://a.gov/x",
                title="A",
                tier=stale_tier,                 # stale: cached components say Tier S
                status=SourceStatus.RENDERED,
                published_at="2026-06-25",
                raw_path="raw/S1.txt",
                extract={"key": "value"},
                scores=_components_for_tier_s(),
            ),
        ],
        claims=[
            Claim(
                id="C1",
                text="The rate is 7 percent",
                category=stale_category,          # stale: not yet factchecked
                confidence=1,
                sources=["S1"],
            ),
        ],
    )


class TestRescoreReadonly(unittest.TestCase):
    def test_readonly_invariant_held(self):
        before = make_snapshot()
        _after, _diff, changed = rescore_snapshot(before, now_utc=NOW)
        self.assertEqual(changed, [])

    def test_input_snapshot_not_mutated(self):
        before = make_snapshot()
        before_json = snapshot_to_dict(before)
        rescore_snapshot(before, now_utc=NOW)
        # The working copy is fully detached: the input is untouched.
        self.assertEqual(snapshot_to_dict(before), before_json)


class TestRescorePropagation(unittest.TestCase):
    def test_tier_change_propagates_into_confidence_and_category(self):
        # Stored tier B + category UNVERIFIED; cached components -> Tier S.
        before = make_snapshot()
        hints = {"C1": ClaimCategory.INCOMPLETE}
        after, diff, changed = rescore_snapshot(
            before, now_utc=NOW, model_categories=hints,
        )
        self.assertEqual(changed, [])

        # Source tier re-derived B -> S.
        sdiff = {d["id"]: d for d in diff["sources"]}
        self.assertEqual(sdiff["S1"]["tier_before"], "B")
        self.assertEqual(sdiff["S1"]["tier_after"], "S")
        self.assertEqual(after.sources[0].tier, Tier.S)

        # Claim confidence rose (1 Tier-S supporting source -> base 4) and the
        # factcheck category moved off the stale UNVERIFIED to the model hint.
        cdiff = {d["id"]: d for d in diff["claims"]}
        self.assertEqual(cdiff["C1"]["confidence_before"], 1)
        self.assertEqual(cdiff["C1"]["confidence_after"], 4)
        self.assertEqual(cdiff["C1"]["category_before"], "unverified")
        self.assertEqual(cdiff["C1"]["category_after"], "incomplete")
        self.assertEqual(after.claims[0].category, ClaimCategory.INCOMPLETE)


class TestRescoreShallow(unittest.TestCase):
    def test_shallow_leaves_category_stale(self):
        before = make_snapshot()
        hints = {"C1": ClaimCategory.INCOMPLETE}
        after, diff, changed = rescore_snapshot(
            before, now_utc=NOW, model_categories=hints, shallow=True,
        )
        self.assertEqual(changed, [])
        cdiff = {d["id"]: d for d in diff["claims"]}
        # Source tier + base confidence are re-derived even in shallow mode...
        self.assertEqual(diff["sources"][0]["tier_after"], "S")
        self.assertEqual(cdiff["C1"]["confidence_after"], 4)
        # ...but the verdict category is NOT re-run, so it stays stale.
        self.assertEqual(cdiff["C1"]["category_after"], "unverified")
        self.assertEqual(after.claims[0].category, ClaimCategory.UNVERIFIED)


class TestRescoreIdempotencyDeterminism(unittest.TestCase):
    def test_idempotent_on_unchanged_rubric(self):
        # First rescore brings the snapshot to its fixed point; a second rescore
        # of THAT result yields an empty diff.
        before = make_snapshot()
        hints = {"C1": ClaimCategory.INCOMPLETE}
        once, _d1, _c1 = rescore_snapshot(before, now_utc=NOW, model_categories=hints)
        twice, diff2, changed2 = rescore_snapshot(once, now_utc=NOW, model_categories=hints)
        self.assertEqual(changed2, [])
        for d in diff2["sources"]:
            self.assertEqual(d["tier_before"], d["tier_after"])
        for d in diff2["claims"]:
            self.assertEqual(d["confidence_before"], d["confidence_after"])
            self.assertEqual(d["category_before"], d["category_after"])

    def test_deterministic(self):
        a, _, _ = rescore_snapshot(make_snapshot(), now_utc=NOW)
        b, _, _ = rescore_snapshot(make_snapshot(), now_utc=NOW)
        self.assertEqual(snapshot_to_dict(a), snapshot_to_dict(b))


class TestRescoreCLI(unittest.TestCase):
    def _run(self, argv, payload):
        buf = io.StringIO()
        # Feed the JSON payload on stdin.
        import sys
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(payload))
        try:
            with redirect_stdout(buf):
                code = cli.main(argv)
        finally:
            sys.stdin = old_stdin
        return code, buf.getvalue()

    def test_cli_happy_path(self):
        payload = {
            "snapshot": snapshot_to_dict(make_snapshot()),
            "now": NOW,
            "model_categories": {"C1": "incomplete"},
        }
        code, out = self._run(["rescore"], payload)
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertTrue(result["readonly_ok"])
        self.assertEqual(result["diff"]["sources"][0]["tier_after"], "S")
        self.assertNotIn("warning", result)

    def test_cli_shallow_emits_warning(self):
        payload = {"snapshot": snapshot_to_dict(make_snapshot()), "now": NOW}
        code, out = self._run(["rescore", "--shallow"], payload)
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertIn("warning", result)
        self.assertIn("stale", result["warning"])

    def test_cli_readonly_violation_exits_1(self):
        # A snapshot whose cached "after-extract" differs is simulated by feeding
        # a before-snapshot, rescoring, then asserting the engine path itself is
        # read-only.  To exercise the exit-1 branch we monkeypatch the rescore to
        # report a changed id.
        from engine import state

        orig = state.rescore_snapshot

        def fake(snapshot, **kw):
            after, diff, _changed = orig(snapshot, **kw)
            return after, diff, ["S1"]  # force a read-only violation

        state.rescore_snapshot = fake
        try:
            payload = {"snapshot": snapshot_to_dict(make_snapshot()), "now": NOW}
            code, out = self._run(["rescore"], payload)
        finally:
            state.rescore_snapshot = orig
        self.assertEqual(code, 1)
        result = json.loads(out)
        self.assertEqual(result["changed_ids"], ["S1"])
        self.assertIn("error", result)


class TestRescoreMutatingFixture(unittest.TestCase):
    def test_mutated_source_payload_surfaces_as_changed(self):
        # assert_sources_readonly compares url/raw_path/extract.  Build a "before"
        # and an "after" that share an id but differ in extract -> non-empty list.
        from engine.state import assert_sources_readonly

        before = make_snapshot()
        after = make_snapshot()
        after.sources[0].extract = {"key": "MUTATED"}
        changed = assert_sources_readonly(before, after)
        self.assertEqual(changed, ["S1"])


if __name__ == "__main__":
    unittest.main()
