"""H9 — stance-target grouping / reconciliation (hyperresearch reuse).

Traceability: docs/TRACE_HYPERRESEARCH.md (AC9.1..AC9.E2E).

Claims carrying a (LLM-provided) `stance_target` are grouped by that key and the
engine deterministically reconciles them: consensus (all affirm) / contradicted
(affirm + deny) / disputed (mixed or opinion), surfacing the quantified values
in each group. Read-only; the field is Optional and drops from serialization
when None (byte-identical). Run from the skill dir:
    python -m unittest tests.test_h9_reconcile -v
"""

import unittest

from engine import reconcile
from engine.model import Claim, ClaimCategory, _jsonable


def _c(cid, text, cat, target=None, **kw):
    return Claim(id=cid, text=text, category=cat, stance_target=target, **kw)


class Ac91ByteIdentityTest(unittest.TestCase):
    def test_stance_target_none_drops(self):
        self.assertNotIn("stance_target", _jsonable(_c("C1", "x", ClaimCategory.VERIFIED)))

    def test_stance_target_serializes_when_set(self):
        self.assertEqual(_jsonable(_c("C1", "x", ClaimCategory.VERIFIED, target="цена"))["stance_target"], "цена")


class Ac92GroupingTest(unittest.TestCase):
    def test_groups_by_target_excludes_keyless(self):
        claims = [
            _c("C1", "a", ClaimCategory.VERIFIED, target="цена Whoop"),
            _c("C2", "b", ClaimCategory.VERIFIED, target="цена Whoop"),
            _c("C3", "c", ClaimCategory.VERIFIED),  # no target -> excluded
        ]
        groups = reconcile.group_by_target(claims)
        self.assertEqual(set(groups), {"цена Whoop"})
        self.assertEqual([c.id for c in groups["цена Whoop"]], ["C1", "C2"])


class Ac93ReconciliationTest(unittest.TestCase):
    def _verdict(self, claims):
        return {r["target"]: r["verdict"] for r in reconcile.reconcile(claims)}

    def test_consensus_all_affirm(self):
        v = self._verdict([_c("C1", "a", ClaimCategory.VERIFIED, target="T"),
                           _c("C2", "b", ClaimCategory.VERIFIED, target="T")])
        self.assertEqual(v["T"], "consensus")

    def test_contradicted_affirm_and_deny(self):
        v = self._verdict([_c("C1", "a", ClaimCategory.VERIFIED, target="T"),
                           _c("C2", "b", ClaimCategory.FALSE, target="T")])
        self.assertEqual(v["T"], "contradicted")

    def test_inconclusive_on_only_opinion(self):
        v = self._verdict([_c("C1", "a", ClaimCategory.OPINION, target="T"),
                           _c("C2", "b", ClaimCategory.OUTDATED, target="T")])
        self.assertEqual(v["T"], "inconclusive")  # no decisive verdict -> nothing to dispute

    def test_refuted_all_false(self):
        v = self._verdict([_c("C1", "a", ClaimCategory.FALSE, target="T"),
                           _c("C2", "b", ClaimCategory.FALSE, target="T")])
        self.assertEqual(v["T"], "refuted")  # unanimous refutation is agreement, not dispute

    def test_disputed_decisive_mixed_with_opinion(self):
        v = self._verdict([_c("C1", "a", ClaimCategory.VERIFIED, target="T"),
                           _c("C2", "b", ClaimCategory.OPINION, target="T")])
        self.assertEqual(v["T"], "disputed")


class Ac94QuantifiedValuesTest(unittest.TestCase):
    def test_numbers_surfaced_per_target(self):
        rows = reconcile.reconcile([
            _c("C1", "Whoop стоит 30000 рублей", ClaimCategory.VERIFIED, target="цена"),
            _c("C2", "скидка достигает 25 процентов", ClaimCategory.VERIFIED, target="цена"),
        ])
        row = {r["target"]: r for r in rows}["цена"]
        self.assertIn("30000", row["numbers"])
        self.assertIn("25", row["numbers"])


class Ac93NumericDivergenceTest(unittest.TestCase):
    def test_consensus_of_verdict_flags_value_divergence(self):
        # both VERIFIED (verdict consensus) but assert DIFFERENT single values.
        rows = reconcile.reconcile([
            _c("C1", "цена 30000 рублей", ClaimCategory.VERIFIED, target="цена"),
            _c("C2", "цена 45000 рублей", ClaimCategory.VERIFIED, target="цена"),
        ])
        row = {r["target"]: r for r in rows}["цена"]
        self.assertEqual(row["verdict"], "consensus")
        self.assertTrue(row["numeric_divergence"])  # value disagreement surfaced


class Ac95ReadOnlyDeterministicTest(unittest.TestCase):
    def test_report_does_not_import_reconcile(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "report.py").read_text(encoding="utf-8")
        self.assertNotIn("reconcile", src)

    def test_deterministic(self):
        claims = [_c("C1", "a 10", ClaimCategory.VERIFIED, target="B"),
                  _c("C2", "b 20", ClaimCategory.FALSE, target="A")]
        self.assertEqual(reconcile.reconcile(claims), reconcile.reconcile(claims))
        # sorted by target for stable output
        self.assertEqual([r["target"] for r in reconcile.reconcile(claims)], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
