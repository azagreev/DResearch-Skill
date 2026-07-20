"""H3 — retraction flag-and-veto (hyperresearch reuse).

Traceability: docs/TRACE_HYPERRESEARCH.md (AC3.1..AC3.5).

A cited source flagged retracted cannot prop up a finding: it is stripped from
the supporting evidence in classify_claim UNLESS the claim explicitly
acknowledges the retraction (e.g. a debunk about it). A deterministic detector
recognizes retraction language (en+ru). Offline; the veto hot-path keys on the
explicit flag only (no false positives on legacy fixtures). Byte-identical when
no source is retracted (the field is Optional -> dropped from serialization when
None). Run from the skill dir:
    python -m unittest tests.test_h3_retraction -v
"""

import unittest

from engine import retraction
from engine.factcheck import classify_claim
from engine.model import Claim, ClaimCategory, ClaimRole, Source, Tier, _jsonable


def _src(sid="S1", retracted=None, content="Обычное содержимое источника о рынке."):
    return Source(id=sid, url=f"https://example.test/{sid}", tier=Tier.A,
                  retracted=retracted, extract={"content": content})


class Ac31RetractedSourceVetoedTest(unittest.TestCase):
    def test_claim_on_only_retracted_source_is_unverified(self):
        src = _src(retracted=True)
        claim = Claim(id="C1", text="обычное утверждение без упоминания отзыва", sources=["S1"])
        self.assertEqual(classify_claim(claim, {"S1": src}), ClaimCategory.UNVERIFIED)

    def test_non_retracted_source_supports_normally(self):
        src = _src(retracted=None)
        claim = Claim(id="C1", text="обычное утверждение", sources=["S1"])
        self.assertEqual(classify_claim(claim, {"S1": src}), ClaimCategory.VERIFIED)

    def test_one_valid_source_survives_a_retracted_co_citation(self):
        good = _src("S1", retracted=None)
        bad = _src("S2", retracted=True)
        claim = Claim(id="C1", text="утверждение", sources=["S1", "S2"])
        # the valid source still supports the claim; only the retracted one is dropped
        self.assertEqual(classify_claim(claim, {"S1": good, "S2": bad}), ClaimCategory.VERIFIED)


class Ac31RetractedContradictorTest(unittest.TestCase):
    """Regression (review MAJOR): a retracted source is unreliable in BOTH
    directions — it must not push a valid claim to FALSE/OUTDATED."""

    def test_retracted_contradictor_does_not_falsify_valid_claim(self):
        good = Source(id="S1", url="u1", tier=Tier.A, extract={"content": "x"})
        # higher-tier retracted contradictor would win (-> FALSE) if not stripped
        bad = Source(id="S2", url="u2", tier=Tier.S, retracted=True, extract={"content": "y"})
        claim = Claim(id="C1", text="обычное утверждение", sources=["S1"],
                      contradicting_sources=["S2"])
        self.assertEqual(classify_claim(claim, {"S1": good, "S2": bad}), ClaimCategory.VERIFIED)


class Ac32DetectorMarksSourcesTest(unittest.TestCase):
    def test_detect_retraction_language(self):
        self.assertTrue(retraction.detect_retraction("This article has been retracted."))
        self.assertTrue(retraction.detect_retraction("Статья была отозвана редакцией в 2025."))
        self.assertFalse(retraction.detect_retraction("Обычный материал о рынке и ценах."))

    def test_mark_retractions_sets_flag_from_content(self):
        srcs = [_src("S1", content="Notice: this paper was retracted in 2025."),
                _src("S2", content="Совершенно обычный текст без пометок.")]
        flagged = retraction.mark_retractions(srcs)
        self.assertEqual(flagged, ["S1"])
        self.assertIs(srcs[0].retracted, True)
        self.assertIsNone(srcs[1].retracted)

    def test_mark_retractions_does_not_overwrite_explicit_flag(self):
        s = _src("S1", retracted=False, content="this was retracted")
        retraction.mark_retractions([s])
        self.assertIs(s.retracted, False)  # explicit value preserved


class Ac33AcknowledgmentLiftsVetoTest(unittest.TestCase):
    def test_acknowledged_retraction_is_not_stripped(self):
        src = _src(retracted=True)
        claim = Claim(id="C1", text="Статья S1 была отозвана — это установленный факт",
                      role=ClaimRole.EXTERNAL_CLAIM, sources=["S1"])
        # the claim discusses the retraction, so its (retracted) source stays and
        # the claim resolves normally instead of being vetoed to UNVERIFIED.
        self.assertEqual(classify_claim(claim, {"S1": src}), ClaimCategory.VERIFIED)


class Ac34DeterminismTest(unittest.TestCase):
    def test_mark_and_classify_are_deterministic(self):
        # fresh objects each call: mark_retractions is idempotent (mutates the
        # flag), so re-marking the SAME objects is a no-op by design.
        mk = lambda: [_src("S1", content="this paper was retracted")]
        self.assertEqual(retraction.mark_retractions(mk()), retraction.mark_retractions(mk()))
        src = _src(retracted=True)
        c = Claim(id="C1", text="x", sources=["S1"])
        self.assertEqual(classify_claim(c, {"S1": src}), classify_claim(c, {"S1": src}))


class Ac35ByteIdentityTest(unittest.TestCase):
    def test_retracted_none_drops_from_serialization(self):
        src = _src(retracted=None)
        self.assertNotIn("retracted", _jsonable(src))

    def test_retracted_true_serializes(self):
        src = _src(retracted=True)
        self.assertIs(_jsonable(src)["retracted"], True)


if __name__ == "__main__":
    unittest.main()
