"""H7 — scale-as-config-profile (hyperresearch reuse).

Traceability: docs/TRACE_HYPERRESEARCH.md (AC7.1..AC7.5).

Scale knobs and gate thresholds that lived as SKILL.md prose become a stdlib
dataclass Profile with named built-ins (by depth), `extends`-overlay, and
golden-pinned defaults. The engine consumes at least one threshold from the
profile (plan.MAX_CONCURRENT). Pure/deterministic/offline/stdlib-only.

Run from the skill dir:
    python -m unittest tests.test_h7_profiles -v
"""

import unittest

from engine import plan, profiles


class Ac71LoadIgnoreUnknownTest(unittest.TestCase):
    def test_from_mapping_overrides_and_ignores_unknown(self):
        p = profiles.from_mapping({"max_concurrent": 3, "bogus_key": 99})
        self.assertEqual(p.max_concurrent, 3)
        self.assertFalse(hasattr(p, "bogus_key"))


class Ac72ExtendsTest(unittest.TestCase):
    def test_extends_inherits_then_overrides(self):
        p = profiles.from_mapping({"extends": "deep", "max_concurrent": 2})
        self.assertEqual((p.subtasks_min, p.subtasks_max), (20, 30))  # inherited from deep
        self.assertEqual(p.max_concurrent, 2)                          # overridden

    def test_unknown_extends_falls_back_to_default(self):
        # graceful: an unknown extends name resolves to DEFAULT, never KeyError.
        p = profiles.from_mapping({"extends": "nonexistent", "max_concurrent": 7})
        self.assertEqual(p.max_concurrent, 7)
        self.assertEqual(p.subtasks_min, profiles.DEFAULT.subtasks_min)


class Ac73EngineReadsFromProfileTest(unittest.TestCase):
    def test_max_concurrent_sourced_from_profile(self):
        self.assertEqual(plan.MAX_CONCURRENT, profiles.DEFAULT.max_concurrent)
        self.assertEqual(plan.MAX_CONCURRENT, 5)


class Ac74GoldenPinnedDefaultsTest(unittest.TestCase):
    def test_standard_defaults_match_historical_literals(self):
        d = profiles.BUILTINS["standard"]
        self.assertEqual(d.max_concurrent, 5)
        self.assertEqual(d.tier_b_plus_ratio, 0.60)
        self.assertEqual(d.freshness_ratio, 0.60)
        self.assertEqual(d.completeness_index_min, 70)
        self.assertEqual(d.source_diversity_min, 4)

    def test_depth_subtask_bounds_match_skill_prose(self):
        self.assertEqual((profiles.BUILTINS["quick"].subtasks_min, profiles.BUILTINS["quick"].subtasks_max), (5, 8))
        self.assertEqual((profiles.BUILTINS["standard"].subtasks_min, profiles.BUILTINS["standard"].subtasks_max), (10, 15))
        self.assertEqual((profiles.BUILTINS["deep"].subtasks_min, profiles.BUILTINS["deep"].subtasks_max), (20, 30))
        self.assertEqual((profiles.BUILTINS["exhaustive"].subtasks_min, profiles.BUILTINS["exhaustive"].subtasks_max), (30, 50))


class Ac75DeterminismTest(unittest.TestCase):
    def test_from_mapping_is_deterministic(self):
        a = profiles.from_mapping({"extends": "deep", "max_concurrent": 2})
        b = profiles.from_mapping({"extends": "deep", "max_concurrent": 2})
        self.assertEqual(a, b)  # frozen dataclass value-equality


if __name__ == "__main__":
    unittest.main()
