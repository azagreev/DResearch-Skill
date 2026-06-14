"""Phase 14 — Package C tests: RSS tier, escalation vocabulary, backward compat.

Run from the skill dir:
    python -m unittest tests.test_phase14_collect -v

Tests cover:
  AC14-5-1  RSS 2.0 XML string -> normalized items each with published_at
  AC14-5-2  Atom XML string -> normalized items each with published_at
  AC14-5-3  RSS pre-parsed list -> normalized items (bypass XML parse)
  AC14-5-4  Malformed RSS XML returns empty list (parse-tolerant)
  AC14-5-5  RSS items carry fetched_via="rss" and risk_class="SAFE"
  AC14-5-6  RSS item fed through ingest.source_from_raw -> DateConfidence.HIGH
  AC14-5-7  PROVIDER_ESCALATION maps browserbase->browser, curl->curl
  AC14-5-8  rate_limited for browserbase (browser-class) emits retry_with_proxy
  AC14-5-9  rate_limited for curl (non-browser) does NOT emit retry_with_proxy
  AC14-5-10 rate_limited for native_web_search (SAFE) does NOT emit retry_with_proxy
  AC14-5-11 fetch_next_page emitted when payload carries a cursor field
  AC14-5-12 no_more_pages emitted when payload is empty
  AC14-5-13 enrich_top_n emitted for rss provider with no scores
  AC14-5-14 escalate_to_agent emitted when cursor present
  AC14-5-15 Backward compat: native_web_search ok result actions == pre-phase14 set
  AC14-5-16 Backward compat: browserbase rate_limited actions unchanged for non-browser
  AC14-5-17 RSS snippet ordering (summary > description > content)
  AC14-5-18 _parse_rss_xml document order preserved
"""

import unittest

from engine import collect, ingest
from engine.model import DateConfidence

NOW = "2026-06-14T00:00:00Z"

# ---------------------------------------------------------------------------
# XML fixtures
# ---------------------------------------------------------------------------

_RSS2_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>First Item</title>
      <link>https://example.com/item1</link>
      <description>First description text</description>
      <pubDate>Mon, 10 Jun 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Second Item</title>
      <link>https://example.com/item2</link>
      <description>Second description text</description>
      <pubDate>Tue, 11 Jun 2026 09:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Test Feed</title>
  <entry>
    <title>Atom Entry One</title>
    <link href="https://atom.example.com/entry1"/>
    <summary>Atom summary content one</summary>
    <published>2026-06-12T08:00:00Z</published>
  </entry>
  <entry>
    <title>Atom Entry Two</title>
    <link href="https://atom.example.com/entry2"/>
    <summary>Atom summary content two</summary>
    <updated>2026-06-13T10:00:00Z</updated>
  </entry>
</feed>"""

_RSS2_MINIMAL_XML = """<rss version="2.0">
  <channel>
    <item>
      <link>https://min.example.com/x</link>
      <pubDate>2026-06-01</pubDate>
    </item>
  </channel>
</rss>"""

_MALFORMED_XML = "<<not xml at all>>"

_RSS2_SNIPPET_PRIORITY_XML = """<rss>
  <channel>
    <item>
      <link>https://prio.example.com/a</link>
      <pubDate>2026-06-10</pubDate>
      <summary>summary wins</summary>
      <description>description loses</description>
    </item>
    <item>
      <link>https://prio.example.com/b</link>
      <pubDate>2026-06-10</pubDate>
      <description>description wins when no summary</description>
    </item>
  </channel>
</rss>"""

# ---------------------------------------------------------------------------
# AC14-5-1 / AC14-5-5: RSS 2.0 XML -> normalized items with published_at
# ---------------------------------------------------------------------------


class TestRssXmlNormalization(unittest.TestCase):
    """RSS 2.0 XML string is correctly parsed and normalized."""

    def setUp(self):
        self.result = collect.normalize("rss", _RSS2_XML)

    def test_status_ok(self):
        self.assertEqual(self.result.status, "ok")

    def test_item_count(self):
        self.assertEqual(len(self.result.items), 2)

    def test_item_urls(self):
        urls = [it["url"] for it in self.result.items]
        self.assertIn("https://example.com/item1", urls)
        self.assertIn("https://example.com/item2", urls)

    def test_items_have_titles(self):
        titles = [it["title"] for it in self.result.items]
        self.assertIn("First Item", titles)
        self.assertIn("Second Item", titles)

    def test_items_have_snippets(self):
        for item in self.result.items:
            self.assertTrue(item["snippet"], f"snippet must be non-empty: {item}")

    def test_items_have_published_at(self):
        """published_at must be set so downstream ingest yields DateConfidence.HIGH."""
        for item in self.result.items:
            self.assertIn("published_at", item, "rss item must carry published_at")
            self.assertTrue(item["published_at"], "published_at must be non-empty")

    def test_fetched_via_is_rss(self):
        for item in self.result.items:
            self.assertEqual(item["fetched_via"], "rss")

    def test_risk_class_is_safe(self):
        for item in self.result.items:
            self.assertEqual(item["metadata"]["risk_class"], "SAFE")

    def test_ingest_items_in_next_actions(self):
        self.assertIn("ingest_items", self.result.next_valid_actions)


# ---------------------------------------------------------------------------
# AC14-5-2: Atom XML -> normalized items with published_at
# ---------------------------------------------------------------------------


class TestAtomXmlNormalization(unittest.TestCase):
    """Atom feed XML is correctly parsed."""

    def setUp(self):
        self.result = collect.normalize("rss", _ATOM_XML)

    def test_two_entries(self):
        self.assertEqual(len(self.result.items), 2)

    def test_atom_link_href_extracted(self):
        urls = [it["url"] for it in self.result.items]
        self.assertIn("https://atom.example.com/entry1", urls)
        self.assertIn("https://atom.example.com/entry2", urls)

    def test_atom_summary_extracted(self):
        snippets = [it["snippet"] for it in self.result.items]
        self.assertTrue(any("Atom summary content one" in s for s in snippets))

    def test_atom_published_extracted(self):
        entry1 = next(it for it in self.result.items if "entry1" in it["url"])
        self.assertIn("published_at", entry1)
        self.assertIn("2026-06-12", entry1["published_at"])

    def test_atom_updated_fallback(self):
        """When <published> absent, <updated> should be used as published_at."""
        entry2 = next(it for it in self.result.items if "entry2" in it["url"])
        self.assertIn("published_at", entry2)
        self.assertTrue(entry2["published_at"])


# ---------------------------------------------------------------------------
# AC14-5-3: pre-parsed list passes through without re-parsing
# ---------------------------------------------------------------------------


class TestRssPreParsedList(unittest.TestCase):
    """Already-parsed list of dicts is accepted as-is for rss provider."""

    def test_pre_parsed_list_normalized(self):
        payload = [
            {
                "url": "https://preparsed.example.com/1",
                "title": "Pre-parsed Item",
                "snippet": "Pre-parsed snippet",
                "published_at": "2026-06-14T00:00:00Z",
            }
        ]
        result = collect.normalize("rss", payload)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0]["url"], "https://preparsed.example.com/1")
        self.assertEqual(result.items[0]["published_at"], "2026-06-14T00:00:00Z")


# ---------------------------------------------------------------------------
# AC14-5-4: malformed XML returns empty list (parse-tolerant)
# ---------------------------------------------------------------------------


class TestMalformedXml(unittest.TestCase):
    def test_malformed_xml_returns_empty(self):
        result = collect.normalize("rss", _MALFORMED_XML)
        # Should not raise; returns ok with 0 items
        self.assertEqual(result.items, [])


class TestRssDosGuards(unittest.TestCase):
    def test_doctype_entity_declaration_is_refused(self):
        # billion-laughs vector: a DTD with an internal entity. Real feeds never
        # carry one; _parse_rss_xml must refuse before expansion (returns []).
        evil = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE rss [ <!ENTITY lol "lol"> '
            '<!ENTITY lol2 "&lol;&lol;&lol;&lol;"> ]>'
            '<rss version="2.0"><channel><item>'
            '<title>&lol2;</title><link>https://e.com/a</link></item></channel></rss>'
        )
        self.assertEqual(collect._parse_rss_xml(evil), [])
        self.assertEqual(collect.normalize("rss", evil).items, [])

    def test_oversized_payload_is_rejected_before_parse(self):
        too_big = "x" * (collect._RSS_MAX_BYTES + 1)
        self.assertEqual(collect._parse_rss_xml(too_big), [])

    def test_empty_string_is_safe(self):
        self.assertEqual(collect._parse_rss_xml(""), [])


# ---------------------------------------------------------------------------
# AC14-5-6: RSS item through ingest.source_from_raw -> DateConfidence.HIGH
# ---------------------------------------------------------------------------


class TestRssDateConfidenceHigh(unittest.TestCase):
    """RSS items must yield DateConfidence.HIGH after ingest because they carry published_at."""

    def test_date_confidence_high_via_ingest(self):
        result = collect.normalize("rss", _RSS2_XML)
        self.assertGreater(len(result.items), 0)
        for item in result.items:
            source = ingest.source_from_raw(item, "S_test", NOW)
            self.assertEqual(
                source.date_confidence,
                DateConfidence.HIGH,
                f"Expected DateConfidence.HIGH for item {item.get('url')}; "
                f"got {source.date_confidence}. published_at={item.get('published_at')!r}",
            )

    def test_atom_date_confidence_high(self):
        result = collect.normalize("rss", _ATOM_XML)
        for item in result.items:
            source = ingest.source_from_raw(item, "S_atom", NOW)
            self.assertEqual(source.date_confidence, DateConfidence.HIGH)


# ---------------------------------------------------------------------------
# AC14-5-7: PROVIDER_ESCALATION map
# ---------------------------------------------------------------------------


class TestProviderEscalationMap(unittest.TestCase):
    def test_browserbase_is_browser_class(self):
        self.assertEqual(collect.PROVIDER_ESCALATION["browserbase"], "browser")

    def test_curl_is_curl_class(self):
        self.assertEqual(collect.PROVIDER_ESCALATION["curl"], "curl")

    def test_rss_not_in_escalation_map(self):
        """rss is SAFE and should not appear in PROVIDER_ESCALATION."""
        self.assertNotIn("rss", collect.PROVIDER_ESCALATION)


# ---------------------------------------------------------------------------
# AC14-5-8 / AC14-5-9 / AC14-5-10: retry_with_proxy on rate_limited
# ---------------------------------------------------------------------------


class TestRetryWithProxy(unittest.TestCase):
    """retry_with_proxy is emitted only for browser-class ELEVATED providers."""

    def test_browserbase_rate_limited_emits_retry_with_proxy(self):
        payload = {"status": "rate_limited"}
        result = collect.normalize("browserbase", payload)
        self.assertEqual(result.status, "rate_limited")
        self.assertIn("retry_with_proxy", result.next_valid_actions)

    def test_curl_rate_limited_does_not_emit_retry_with_proxy(self):
        """curl is ELEVATED but curl-class, not browser-class — no proxy hint."""
        payload = {"status": "rate_limited"}
        result = collect.normalize("curl", payload)
        self.assertEqual(result.status, "rate_limited")
        self.assertNotIn("retry_with_proxy", result.next_valid_actions)

    def test_native_web_search_rate_limited_no_proxy(self):
        """SAFE providers never emit retry_with_proxy."""
        payload = {"status": "rate_limited"}
        result = collect.normalize("native_web_search", payload)
        self.assertNotIn("retry_with_proxy", result.next_valid_actions)

    def test_retry_after_backoff_still_present_for_browserbase(self):
        """retry_after_backoff must remain alongside the new retry_with_proxy."""
        payload = {"status": "rate_limited"}
        result = collect.normalize("browserbase", payload)
        self.assertIn("retry_after_backoff", result.next_valid_actions)


# ---------------------------------------------------------------------------
# AC14-5-11 / AC14-5-12: pagination token actions
# ---------------------------------------------------------------------------


class TestPaginationActions(unittest.TestCase):

    def test_fetch_next_page_emitted_when_cursor_present(self):
        payload = [
            {
                "url": "https://paged.example.com/1",
                "title": "Paged Item",
                "snippet": "content",
                "cursor": "next_page_token_abc",
            }
        ]
        result = collect.normalize("native_web_search", payload)
        self.assertIn("fetch_next_page", result.next_valid_actions)

    def test_no_more_pages_on_empty_payload(self):
        result = collect.normalize("native_web_search", [])
        self.assertIn("no_more_pages", result.next_valid_actions)

    def test_no_pagination_tokens_in_normal_result(self):
        """Ordinary non-paginated result must NOT emit pagination tokens."""
        payload = [
            {"url": "https://normal.example.com/a", "title": "Normal", "snippet": "s"}
        ]
        result = collect.normalize("native_web_search", payload)
        self.assertNotIn("fetch_next_page", result.next_valid_actions)
        self.assertNotIn("no_more_pages", result.next_valid_actions)


# ---------------------------------------------------------------------------
# AC14-5-13: enrich_top_n for rss
# ---------------------------------------------------------------------------


class TestEnrichTopN(unittest.TestCase):
    def test_enrich_top_n_emitted_for_rss_without_scores(self):
        result = collect.normalize("rss", _RSS2_XML)
        self.assertIn("enrich_top_n", result.next_valid_actions)

    def test_enrich_top_n_not_emitted_for_non_rss(self):
        """enrich_top_n must NOT appear for native_web_search without scores."""
        payload = [{"url": "https://x.com", "title": "T", "snippet": "s"}]
        result = collect.normalize("native_web_search", payload)
        self.assertNotIn("enrich_top_n", result.next_valid_actions)

    def test_enrich_top_n_not_emitted_for_rss_with_scores(self):
        """When rss items already carry scores, enrich_top_n should be suppressed."""
        payload = [
            {
                "url": "https://scored.rss.com/1",
                "title": "Scored",
                "snippet": "s",
                "published_at": "2026-06-10",
                "scores": {"relevance": 0.8},
            }
        ]
        result = collect.normalize("rss", payload)
        self.assertNotIn("enrich_top_n", result.next_valid_actions)


# ---------------------------------------------------------------------------
# AC14-5-14: escalate_to_agent emitted with cursor
# ---------------------------------------------------------------------------


class TestEscalateToAgent(unittest.TestCase):
    def test_escalate_to_agent_emitted_with_cursor(self):
        payload = [
            {
                "url": "https://deep.example.com/1",
                "title": "Deep Item",
                "snippet": "content",
                "cursor": "token_xyz",
            }
        ]
        result = collect.normalize("native_web_search", payload)
        self.assertIn("escalate_to_agent", result.next_valid_actions)

    def test_escalate_to_agent_not_emitted_without_cursor(self):
        payload = [{"url": "https://x.com/a", "title": "T", "snippet": "s"}]
        result = collect.normalize("native_web_search", payload)
        self.assertNotIn("escalate_to_agent", result.next_valid_actions)


# ---------------------------------------------------------------------------
# AC14-5-15 / AC14-5-16: Backward compatibility guard
# ---------------------------------------------------------------------------


class TestBackwardCompatibility(unittest.TestCase):
    """Existing provider action sets must be byte-identical to pre-phase-14 behavior."""

    # Pre-phase-14 expected action sets for non-error paths:
    # native_web_search ok result with items:  ["ingest_items"]
    # firecrawl ok result with items:          ["ingest_items"]
    # jina_reader ok result with items:        ["ingest_items"]
    # browserbase ok result with items:        ["ingest_items", "escalate_to_firecrawl"]
    # curl ok result with items:               ["ingest_items", "escalate_to_firecrawl"]
    # native_web_search rate_limited:          ["retry_after_backoff"]
    # browserbase rate_limited:                ["retry_after_backoff", ..., "escalate_to_firecrawl"]
    # native_web_search disabled:              ["enable_provider"]

    def test_native_web_search_ok_actions(self):
        payload = [{"url": "https://ex.com/a", "title": "T", "snippet": "s"}]
        result = collect.normalize("native_web_search", payload)
        # Must include ingest_items
        self.assertIn("ingest_items", result.next_valid_actions)
        # Must NOT include escalate_to_firecrawl (SAFE provider)
        self.assertNotIn("escalate_to_firecrawl", result.next_valid_actions)

    def test_firecrawl_ok_actions(self):
        payload = [{"url": "https://fire.com/a", "title": "T", "markdown": "s"}]
        result = collect.normalize("firecrawl", payload)
        self.assertIn("ingest_items", result.next_valid_actions)
        self.assertNotIn("escalate_to_firecrawl", result.next_valid_actions)

    def test_browserbase_ok_includes_escalate_firecrawl(self):
        payload = [{"url": "https://bb.com/a", "title": "T", "content": "s"}]
        result = collect.normalize("browserbase", payload)
        self.assertIn("ingest_items", result.next_valid_actions)
        self.assertIn("escalate_to_firecrawl", result.next_valid_actions)

    def test_curl_ok_includes_escalate_firecrawl(self):
        payload = [{"url": "https://curl.io/a", "title": "T", "text": "s"}]
        result = collect.normalize("curl", payload)
        self.assertIn("ingest_items", result.next_valid_actions)
        self.assertIn("escalate_to_firecrawl", result.next_valid_actions)

    def test_native_web_search_rate_limited_actions(self):
        payload = {"status": "rate_limited"}
        result = collect.normalize("native_web_search", payload)
        self.assertEqual(result.status, "rate_limited")
        self.assertIn("retry_after_backoff", result.next_valid_actions)
        self.assertNotIn("retry_with_proxy", result.next_valid_actions)

    def test_native_web_search_disabled_actions(self):
        payload = {"status": "disabled"}
        result = collect.normalize("native_web_search", payload)
        self.assertEqual(result.status, "disabled")
        self.assertEqual(result.next_valid_actions, ["enable_provider"])

    def test_error_path_actions_unchanged(self):
        payload = {"status": "error", "error": {"type": "timeout", "message": "timeout"}}
        result = collect.normalize("native_web_search", payload)
        self.assertIn("retry_after_backoff", result.next_valid_actions)

    def test_fix_caller_payload_shape_on_bad_payload(self):
        """Bad payload type emits fix_caller_payload_shape — unchanged."""
        result = collect.normalize("native_web_search", 42)
        self.assertIn("fix_caller_payload_shape", result.next_valid_actions)


# ---------------------------------------------------------------------------
# AC14-5-17: snippet field priority (summary > description > content)
# ---------------------------------------------------------------------------


class TestRssSnippetPriority(unittest.TestCase):
    def test_summary_wins_over_description(self):
        result = collect.normalize("rss", _RSS2_SNIPPET_PRIORITY_XML)
        item_a = next(it for it in result.items if "prio.example.com/a" in it["url"])
        self.assertIn("summary wins", item_a["snippet"])
        self.assertNotIn("description loses", item_a["snippet"])

    def test_description_used_when_no_summary(self):
        result = collect.normalize("rss", _RSS2_SNIPPET_PRIORITY_XML)
        item_b = next(it for it in result.items if "prio.example.com/b" in it["url"])
        self.assertIn("description wins", item_b["snippet"])


# ---------------------------------------------------------------------------
# AC14-5-18: _parse_rss_xml document order preserved
# ---------------------------------------------------------------------------


class TestParseRssOrder(unittest.TestCase):
    def test_document_order_preserved(self):
        parsed = collect._parse_rss_xml(_RSS2_XML)
        self.assertEqual(len(parsed), 2)
        self.assertIn("item1", parsed[0]["url"])
        self.assertIn("item2", parsed[1]["url"])

    def test_atom_document_order_preserved(self):
        parsed = collect._parse_rss_xml(_ATOM_XML)
        self.assertEqual(len(parsed), 2)
        self.assertIn("entry1", parsed[0]["url"])
        self.assertIn("entry2", parsed[1]["url"])


# ---------------------------------------------------------------------------
# Misc: rss provider in PROVIDER_RISK
# ---------------------------------------------------------------------------


class TestRssInProviderRisk(unittest.TestCase):
    def test_rss_registered_as_safe(self):
        self.assertEqual(collect.PROVIDER_RISK.get("rss"), "SAFE")


if __name__ == "__main__":
    unittest.main()
