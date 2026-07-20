"""R2 - verifiable-citation format 【S†L{start}-L{end}】 + "<=10 words verbatim" rule.

Covers AC2.1..AC2.5 and AC2.E2E for the citation-span feature layered on top of
the existing legacy `[S1]` citation rendering. Backward compatibility (AC2.5)
is mandatory: a claim carrying no span must render byte-identically to today's
output.

Written TDD-red: the new surface (ingest.content_lines, Claim.citation_spans,
report.resolve_citation_spans, span-aware `_cites` rendering, SKILL.md
documentation) does not exist yet. Every test below imports only symbols that
already exist and asserts on behavior/attributes — so failures surface as
AssertionError, never ImportError, per the run rules for this phase.

Run from the skill dir:
    python -m unittest tests.test_r2_citations -v
"""

import dataclasses
import unittest

from engine import ingest, report
from engine.model import Claim, Source, Tier

NOW = "2026-07-19T00:00:00Z"


def _dummy_source(source_id="S1", content="Line one.\nLine two.\nLine three.\n"):
    raw = {"url": "https://example.org/a", "title": "A", "tier": "S", "extract": {"content": content}}
    return ingest.source_from_raw(raw, source_id, NOW)


class Ac21LineNumberingStableTest(unittest.TestCase):
    """AC2.1 - stable line numbering: identical raw content re-ingested twice
    must number lines identically (precondition for the whole feature)."""

    def test_ac2_1_line_numbering_stable_across_reingest(self):
        raw = {
            "url": "https://example.org/a",
            "title": "A",
            "tier": "S",
            "extract": {"content": "First fact.\nSecond fact.\nThird fact.\n"},
        }
        source_a = ingest.source_from_raw(dict(raw), "S1", NOW)
        source_b = ingest.source_from_raw(dict(raw), "S1", NOW)

        content_lines = getattr(ingest, "content_lines", None)
        self.assertIsNotNone(
            content_lines,
            "ingest.content_lines(source) helper not implemented yet (AC2.1 precondition)",
        )

        lines_a = content_lines(source_a)
        lines_b = content_lines(source_b)
        self.assertEqual(lines_a, lines_b, "re-ingest of identical raw content must yield identical numbering")
        self.assertEqual(lines_a[0], "First fact.")
        self.assertEqual(lines_a[1], "Second fact.")
        self.assertEqual(lines_a[2], "Third fact.")

        # Normalized CRLF/CR content must number the same as LF content (stability
        # across platform/source newline conventions is part of "stable").
        raw_crlf = dict(raw)
        raw_crlf["extract"] = {"content": "First fact.\r\nSecond fact.\r\nThird fact.\r\n"}
        source_c = ingest.source_from_raw(raw_crlf, "S1", NOW)
        self.assertEqual(content_lines(source_c), lines_a, "CRLF content must normalize to the same line numbering")


class Ac22SpanRendersCitationTest(unittest.TestCase):
    """AC2.2 - a claim with a citation_spans entry for a source renders
    【S{id}†L{a}-L{b}】; a claim with no span renders the legacy `[S{id}]`."""

    def test_ac2_2_span_renders_verifiable_citation_else_legacy(self):
        source = _dummy_source("S1")
        sources_by_id = {"S1": source}

        claim_with_span = Claim(id="C1", text="fact", sources=["S1"])
        # citation_spans is a new, optional field — attach it dynamically so this
        # test does not depend on the constructor accepting the kwarg yet.
        setattr(claim_with_span, "citation_spans", {"S1": [2, 3]})

        rendered = report._cites(claim_with_span, sources_by_id)
        self.assertEqual(
            rendered, " — 【S1†L2-L3】",
            "claim with a citation_spans entry must render the verifiable 【S1†L2-L3】 form",
        )

        claim_no_span = Claim(id="C2", text="fact2", sources=["S1"])
        rendered_legacy = report._cites(claim_no_span, sources_by_id)
        self.assertEqual(rendered_legacy, " — [S1]", "claim without a span must keep rendering the legacy [S1] form")


class Ac23OutOfBoundsClampedTest(unittest.TestCase):
    """AC2.3 - a span outside the source's content bounds is clamped, and the
    clamp is recorded as a trace/note — never applied silently."""

    def test_ac2_3_out_of_bounds_span_clamped_with_trace(self):
        source = _dummy_source("S1", content="Only one line.\n")
        resolve_citation_spans = getattr(report, "resolve_citation_spans", None)
        self.assertIsNotNone(
            resolve_citation_spans,
            "report.resolve_citation_spans not implemented yet (AC2.3 clamp-with-trace)",
        )

        claim = Claim(id="C1", text="fact", sources=["S1"])
        setattr(claim, "citation_spans", {"S1": [5, 9]})  # way past the single line of content

        notes = resolve_citation_spans([claim], {"S1": source})
        self.assertTrue(notes, "clamping an out-of-bounds span must produce a non-empty trace of adjustments")
        self.assertEqual(claim.citation_spans["S1"], [1, 1], "out-of-bounds span must be clamped into content bounds")


class Ac24SkillMdDocumentsFormatTest(unittest.TestCase):
    """AC2.4 - SKILL.md documents the citation format and the <=10-word
    verbatim-quote rule; the docs<->CLI reachability guard stays green
    (verified separately by running tests.test_phase15_reachability)."""

    def test_ac2_4_skill_md_documents_citation_format_and_quote_limit(self):
        from pathlib import Path

        skill_md = Path(__file__).resolve().parent.parent / "SKILL.md"
        text = skill_md.read_text(encoding="utf-8")

        self.assertIn("【S1†L", text, "SKILL.md must document the 【S{id}†L{a}-L{b}】 citation format")
        self.assertTrue(
            ("10 слов" in text) or ("10 words" in text),
            "SKILL.md must document the <=10-word verbatim-quote rule",
        )


class Ac25BackwardCompatByteIdenticalTest(unittest.TestCase):
    """AC2.5 - report golden output is byte-identical when no span is present
    (existing report tests + the determinism gate must keep passing)."""

    def test_ac2_5_report_byte_identical_without_span(self):
        field_names = {f.name for f in dataclasses.fields(Claim)}
        self.assertIn(
            "citation_spans", field_names,
            "Claim.citation_spans field not added yet (must default to None for byte-identical serialization)",
        )

        from engine.model import (
            Depth, Route, Snapshot, TaskFrame, snapshot_to_dict,
        )
        from engine.report import render_markdown

        tf = TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD)
        source = Source(id="S1", url="https://example.org/a", tier=Tier.S)
        claim = Claim(id="C1", text="fact", confidence=4, sources=["S1"])
        snap = Snapshot(run_id="r", task_fingerprint="f", task_frame=tf, sources=[source], claims=[claim])

        rendered = render_markdown(snap)
        self.assertIn("[S1]", rendered, "no-span claim must still render the legacy [S1] citation")
        self.assertNotIn("†L", rendered, "no-span claim must never render a 【...†L..】 span citation")

        # citation_spans must default to None so serialization stays byte-identical
        # (dropped by _jsonable, exactly like Claim.metadata's None-able siblings).
        as_dict = snapshot_to_dict(snap)
        claim_dict = as_dict["claims"][0]
        self.assertNotIn(
            "citation_spans", claim_dict,
            "citation_spans must default to None and be dropped from serialization when unset",
        )


class Ac2E2ECollectIngestReportTest(unittest.TestCase):
    """AC2.E2E - collect -> ingest -> report: a citation resolves to a real
    line range inside the actually-ingested source content."""

    def test_ac2_e2e_collect_ingest_report_resolves_real_line_span(self):
        raw_results = [{
            "url": "https://example.org/whoop",
            "title": "Whoop",
            "tier": "S",
            "extract": {"content": "Intro line.\nWhoop costs 30000 rubles.\nOutro line.\n"},
        }]
        sources, _merges = ingest.ingest_sources(raw_results, NOW, dedupe=False)
        source = sources[0]

        content_lines = getattr(ingest, "content_lines", None)
        self.assertIsNotNone(content_lines, "ingest.content_lines not implemented yet")
        lines = content_lines(source)
        target_line_no = next(i for i, ln in enumerate(lines, start=1) if "30000" in ln)

        claim = Claim(id="C1", text="Whoop costs 30000 rubles", sources=[source.id])
        setattr(claim, "citation_spans", {source.id: [target_line_no, target_line_no]})

        resolve_citation_spans = getattr(report, "resolve_citation_spans", None)
        self.assertIsNotNone(resolve_citation_spans, "report.resolve_citation_spans not implemented yet")
        resolve_citation_spans([claim], {source.id: source})

        rendered = report._cites(claim, {source.id: source})
        expected = f" — 【{source.id}†L{target_line_no}-L{target_line_no}】"
        self.assertEqual(rendered, expected, "resolved span must cite the real line the fact appears on")


class Ac23MalformedSpanNoCrashTest(unittest.TestCase):
    """AC2.3 (R2 finding #3) - a malformed citation span (one-element,
    non-int, len>2, etc.) must never crash resolve_citation_spans / _cites;
    the span is ignored and the claim renders the legacy [S1] form."""

    def test_ac2_3_malformed_span_no_crash(self):
        source = _dummy_source("S1")
        sources_by_id = {"S1": source}

        malformed_spans = (
            [5],            # one-element
            [1, 2, 3],      # len > 2
            ["a", "b"],     # non-int
            [1, "b"],       # partially non-int
            [True, 3],      # bool masquerading as int
            "xx",           # not a sequence of ints
            [],             # empty
        )
        for bad in malformed_spans:
            with self.subTest(span=bad):
                claim = Claim(id="C1", text="fact", sources=["S1"])
                setattr(claim, "citation_spans", {"S1": bad})

                # Must not raise IndexError/TypeError.
                notes = report.resolve_citation_spans([claim], sources_by_id)
                self.assertEqual(notes, [], "malformed span {!r} must be ignored, not clamped".format(bad))

                rendered = report._cites(claim, sources_by_id)
                self.assertEqual(
                    rendered, " — [S1]",
                    "malformed span {!r} must fall back to the legacy [S1] rendering".format(bad),
                )


class Ac23ModelBoundaryNormalizationTest(unittest.TestCase):
    """AC2.3 (R2 finding #3) - malformed spans are dropped at the single
    normalization boundary (_citation_spans_from) so only well-formed [a, b]
    pairs (two ints, 1 <= a <= b) ever propagate outward."""

    def test_ac2_3_malformed_spans_dropped_at_model_boundary(self):
        from engine.model import _citation_spans_from

        raw = {
            "S1": [2, 3],       # valid - kept
            "S2": [5],          # len 1 - dropped
            "S3": [1, 2, 3],    # len 3 - dropped
            "S4": ["a", "b"],   # non-int - dropped
            "S5": [3, 1],       # a > b - dropped
            "S6": [0, 2],       # < 1 - dropped
        }
        normalized = _citation_spans_from(raw)
        self.assertEqual(normalized, {"S1": [2, 3]})

        # A mapping with only malformed entries collapses to None (byte-identical
        # to a claim carrying no spans).
        self.assertIsNone(_citation_spans_from({"S2": [5], "S5": [3, 1]}))


class Ac23ClampNoteSurfacedTest(unittest.TestCase):
    """AC2.3 (R2 finding #1) - when a clamp actually happens, render_markdown
    surfaces a trace line for it (not silent for the end user)."""

    def test_ac2_3_clamp_note_surfaced_in_render(self):
        from engine.model import Depth, Route, Snapshot, TaskFrame
        from engine.report import render_markdown

        tf = TaskFrame(question="Q", route=Route.FOCUSED, depth=Depth.STANDARD)
        source = _dummy_source("S1", content="Only one line.\n")
        claim = Claim(id="C1", text="fact", confidence=4, sources=["S1"])
        setattr(claim, "citation_spans", {"S1": [5, 9]})  # out of bounds -> clamped
        snap = Snapshot(run_id="r", task_fingerprint="f", task_frame=tf, sources=[source], claims=[claim])

        rendered = render_markdown(snap)
        self.assertIn(
            "clamp", rendered.lower(),
            "an actual clamp must surface a trace line in render_markdown output",
        )
        self.assertIn("C1", rendered, "the clamp trace must identify the affected claim")


class Ac23SpanForUncitedSourceNoNoteTest(unittest.TestCase):
    """AC2.3 (pre-release review #2) - resolve_citation_spans must only clamp/
    annotate spans for sources the claim actually cites. A span for a source
    present in sources_by_id but NOT in claim.sources renders nothing (_cites
    iterates claim.sources), so it must not emit a misleading clamp note."""

    def test_span_for_uncited_source_produces_no_note(self):
        s1 = _dummy_source("S1", content="Only one line.\n")
        s2 = _dummy_source("S2", content="Only one line.\n")
        claim = Claim(id="C1", text="fact", confidence=4, sources=["S1"])
        # Out-of-bounds span, but for S2 which the claim does NOT cite.
        setattr(claim, "citation_spans", {"S2": [5, 9]})
        notes = report.resolve_citation_spans([claim], {"S1": s1, "S2": s2})
        self.assertEqual(
            notes, [],
            "a span for a source not in claim.sources must not be clamped/annotated",
        )


if __name__ == "__main__":
    unittest.main()
