"""Tests for bench.judge.collate — pure verdict assembly + graceful degradation."""

from __future__ import annotations

import unittest

from bench.judge.collate import build_verdicts, met_from_status


class CollateTest(unittest.TestCase):
    def test_status_mapping(self):
        self.assertTrue(met_from_status("MET"))
        self.assertTrue(met_from_status(" met "))
        self.assertFalse(met_from_status("UNMET"))
        self.assertFalse(met_from_status("anything else"))

    def test_build_verdicts_status_and_met(self):
        out = build_verdicts(
            arm="with_skill",
            task_id="T1",
            results=[
                {"criterion_id": "c1", "status": "MET"},
                {"criterion_id": "c2", "status": "UNMET"},
                {"criterion_id": "c3", "met": True},
            ],
            judge={"model": "opus", "temperature": 0, "draco_ref": "2602.11685"},
        )
        self.assertEqual(out["arm"], "with_skill")
        self.assertEqual(out["verdicts"]["T1"], {"c1": True, "c2": False, "c3": True})
        self.assertEqual(out["judge"]["draco_ref"], "2602.11685")
        self.assertEqual(out["unjudged"]["T1"], [])

    def test_graceful_degradation_omits_failed(self):
        # A failed judge call (ok=False) or a result with neither status nor met
        # is omitted from verdicts → surfaces as unjudged (and as bench n_unjudged).
        out = build_verdicts(
            arm="no_skill",
            task_id="T1",
            results=[
                {"criterion_id": "c1", "status": "MET"},
                {"criterion_id": "c2", "ok": False, "status": "MET"},  # failed → omit
                {"criterion_id": "c3"},                                 # no verdict → omit
            ],
            judge={"model": "opus"},
        )
        self.assertEqual(out["verdicts"]["T1"], {"c1": True})
        self.assertEqual(sorted(out["unjudged"]["T1"]), ["c2", "c3"])


if __name__ == "__main__":
    unittest.main()
