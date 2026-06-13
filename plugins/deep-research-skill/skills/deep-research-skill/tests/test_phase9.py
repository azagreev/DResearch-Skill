"""Phase 9 unit tests — collect seam: normalize + ingest round-trip.

Run from the skill dir:  python -m unittest tests.test_phase9 -v

Tests cover:
  AC9-8(1)  normalize maps >=3 provider-native shapes into the unified item dict
  AC9-8(2)  snippet-cap truncates a 1500-char snippet and sets snippet_truncated=True
  AC9-8(3)  in-session URL cache: already-seen normalised URL suppresses duplicate item
  AC9-8(4)  risk_class per provider (SAFE vs ELEVATED), fetched_via stamped
  AC9-8(5)  error / rate_limited path -> status set, items==[], error populated,
            next_valid_actions non-empty
  AC9-8(6)  end-to-end: ingest_sources(normalize(...).items, NOW) yields valid
            Source objects; ingest stamps trust + _fence; collect did NOT pre-stamp _fence
"""

import unittest

from engine import collect, ingest
from engine.model import TrustLevel

NOW = "2026-06-30T00:00:00Z"

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_WEB_SEARCH_PAYLOAD = [
    {"url": "https://example.com/article1", "title": "Article One", "snippet": "Short snippet one."},
    {"url": "https://example.com/article2", "title": "Article Two", "snippet": "Short snippet two."},
]

_JINA_SEARCH_PAYLOAD = [
    {"url": "https://jina-source.io/page", "title": "Jina Page", "content": "Jina content here."},
]

_JINA_READER_PAYLOAD = [
    {"url": "https://reader.io/doc", "title": "Reader Doc", "text": "Reader text here."},
]

_FIRECRAWL_PAYLOAD = [
    {"url": "https://fire.crawled/page", "title": "Firecrawl Page", "markdown": "## Firecrawl content"},
]

_BROWSERBASE_PAYLOAD = [
    {"url": "https://bb.io/page", "title": "Browserbase Page", "content": "Browser content."},
]

_CURL_PAYLOAD = [
    {"url": "https://curl.io/resource", "title": "Curl Resource", "text": "Curl content."},
]


# ---------------------------------------------------------------------------
# AC9-8(1): normalize maps >=3 provider-native shapes into the unified item dict
# ---------------------------------------------------------------------------


class TestProviderShapeNormalisation(unittest.TestCase):
    """normalize must produce unified item dicts for each named provider."""

    def _assert_item_shape(self, item: dict, expected_url: str, provider: str) -> None:
        self.assertIn("url", item)
        self.assertIn("title", item)
        self.assertIn("snippet", item)
        self.assertIn("fetched_via", item)
        self.assertIn("metadata", item)
        self.assertEqual(item["url"], expected_url)
        self.assertEqual(item["fetched_via"], provider)
        self.assertIn("risk_class", item["metadata"])
        self.assertIn("snippet_truncated", item["metadata"])

    def test_native_web_search_shape(self):
        result = collect.normalize("native_web_search", _WEB_SEARCH_PAYLOAD)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.items), 2)
        self._assert_item_shape(result.items[0], "https://example.com/article1", "native_web_search")
        self._assert_item_shape(result.items[1], "https://example.com/article2", "native_web_search")

    def test_jina_search_shape(self):
        result = collect.normalize("jina_search", _JINA_SEARCH_PAYLOAD)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self._assert_item_shape(item, "https://jina-source.io/page", "jina_search")
        # content should land in snippet
        self.assertIn("Jina content", item["snippet"])

    def test_jina_reader_shape(self):
        result = collect.normalize("jina_reader", _JINA_READER_PAYLOAD)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.items), 1)
        self._assert_item_shape(result.items[0], "https://reader.io/doc", "jina_reader")

    def test_firecrawl_shape(self):
        result = collect.normalize("firecrawl", _FIRECRAWL_PAYLOAD)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self._assert_item_shape(item, "https://fire.crawled/page", "firecrawl")
        self.assertIn("Firecrawl content", item["snippet"])

    def test_firecrawl_metadata_title_fallback(self):
        """Firecrawl result with title in metadata.title instead of top-level."""
        payload = [
            {
                "url": "https://fire.crawled/meta",
                "markdown": "content here",
                "metadata": {"title": "Meta Title"},
            }
        ]
        result = collect.normalize("firecrawl", payload)
        self.assertEqual(result.items[0]["title"], "Meta Title")

    def test_native_web_search_description_field(self):
        """native_web_search should fall back to description when snippet absent."""
        payload = [{"url": "https://ex.com/x", "title": "T", "description": "desc text"}]
        result = collect.normalize("native_web_search", payload)
        self.assertIn("desc text", result.items[0]["snippet"])


# ---------------------------------------------------------------------------
# AC9-8(2): snippet-cap truncates a 1500-char snippet to snippet_cap and
#           sets metadata["snippet_truncated"]=True
# ---------------------------------------------------------------------------


class TestSnippetCap(unittest.TestCase):
    _LONG_TEXT = "x" * 1500

    def test_snippet_capped_at_default_1000(self):
        payload = [{"url": "https://ex.com/long", "title": "Long", "snippet": self._LONG_TEXT}]
        result = collect.normalize("native_web_search", payload)
        item = result.items[0]
        self.assertEqual(len(item["snippet"]), 1000)
        self.assertTrue(item["metadata"]["snippet_truncated"])

    def test_snippet_capped_at_custom_cap(self):
        payload = [{"url": "https://ex.com/long2", "title": "Long2", "snippet": self._LONG_TEXT}]
        result = collect.normalize("native_web_search", payload, snippet_cap=500)
        item = result.items[0]
        self.assertEqual(len(item["snippet"]), 500)
        self.assertTrue(item["metadata"]["snippet_truncated"])

    def test_short_snippet_not_truncated(self):
        payload = [{"url": "https://ex.com/short", "title": "S", "snippet": "hello"}]
        result = collect.normalize("native_web_search", payload)
        item = result.items[0]
        self.assertEqual(item["snippet"], "hello")
        self.assertFalse(item["metadata"]["snippet_truncated"])

    def test_status_is_partial_when_capped(self):
        """status should reflect that content was capped (partial)."""
        payload = [{"url": "https://ex.com/p", "title": "T", "snippet": self._LONG_TEXT}]
        result = collect.normalize("native_web_search", payload)
        self.assertEqual(result.status, "partial")


# ---------------------------------------------------------------------------
# AC9-8(3): in-session URL cache suppresses duplicate items
# ---------------------------------------------------------------------------


class TestInSessionUrlDedup(unittest.TestCase):

    def test_seen_url_suppresses_duplicate(self):
        """Second item whose normalised URL is already in seen_urls must be skipped."""
        seen: set = {"https://example.com/article1"}  # pre-populate
        payload = [
            {"url": "https://example.com/article1", "title": "Dup", "snippet": "dup"},
            {"url": "https://example.com/article2", "title": "New", "snippet": "new"},
        ]
        result = collect.normalize("native_web_search", payload, seen_urls=seen)
        urls = [item["url"] for item in result.items]
        self.assertNotIn("https://example.com/article1", urls)
        self.assertIn("https://example.com/article2", urls)

    def test_seen_urls_updated_with_new_url(self):
        """After normalise, seen_urls must contain newly-added URLs."""
        seen: set = set()
        payload = [{"url": "https://new.com/page", "title": "N", "snippet": "s"}]
        collect.normalize("native_web_search", payload, seen_urls=seen)
        # The normalised form of https://new.com/page should be in seen
        self.assertTrue(any("new.com" in u for u in seen))

    def test_two_calls_dedup_across_batches(self):
        """Simulate two successive normalize calls sharing the same seen_urls set."""
        seen: set = set()
        payload1 = [{"url": "https://shared.com/a", "title": "A", "snippet": "a"}]
        payload2 = [
            {"url": "https://shared.com/a", "title": "A-dup", "snippet": "a-dup"},
            {"url": "https://shared.com/b", "title": "B", "snippet": "b"},
        ]
        r1 = collect.normalize("native_web_search", payload1, seen_urls=seen)
        r2 = collect.normalize("native_web_search", payload2, seen_urls=seen)
        self.assertEqual(len(r1.items), 1)
        self.assertEqual(len(r2.items), 1)  # only /b passes
        self.assertEqual(r2.items[0]["url"], "https://shared.com/b")

    def test_trailing_slash_and_scheme_normalised(self):
        """https://ex.com/a/ and http://ex.com/a should collide after normalisation."""
        seen: set = set()
        payload1 = [{"url": "https://ex.com/a/", "title": "T", "snippet": "s"}]
        payload2 = [{"url": "https://ex.com/a", "title": "T2", "snippet": "s2"}]
        r1 = collect.normalize("native_web_search", payload1, seen_urls=seen)
        r2 = collect.normalize("native_web_search", payload2, seen_urls=seen)
        self.assertEqual(len(r1.items), 1)
        self.assertEqual(len(r2.items), 0)  # duplicate suppressed


# ---------------------------------------------------------------------------
# AC9-8(4): risk_class per provider, fetched_via stamped
# ---------------------------------------------------------------------------


class TestRiskClass(unittest.TestCase):
    _SAFE_PROVIDERS = [
        ("native_web_search", [{"url": "https://a.com", "title": "t", "snippet": "s"}]),
        ("jina_reader", [{"url": "https://b.com", "title": "t", "text": "s"}]),
        ("jina_search", [{"url": "https://c.com", "title": "t", "content": "s"}]),
        ("firecrawl", [{"url": "https://d.com", "title": "t", "markdown": "s"}]),
    ]
    _ELEVATED_PROVIDERS = [
        ("browserbase", [{"url": "https://e.com", "title": "t", "content": "s"}]),
        ("curl", [{"url": "https://f.com", "title": "t", "text": "s"}]),
    ]

    def test_safe_providers(self):
        for provider, payload in self._SAFE_PROVIDERS:
            with self.subTest(provider=provider):
                result = collect.normalize(provider, payload)
                self.assertGreater(len(result.items), 0, f"{provider} should produce items")
                for item in result.items:
                    self.assertEqual(item["metadata"]["risk_class"], "SAFE", provider)
                    self.assertEqual(item["fetched_via"], provider)

    def test_elevated_providers(self):
        for provider, payload in self._ELEVATED_PROVIDERS:
            with self.subTest(provider=provider):
                result = collect.normalize(provider, payload)
                self.assertGreater(len(result.items), 0, f"{provider} should produce items")
                for item in result.items:
                    self.assertEqual(item["metadata"]["risk_class"], "ELEVATED", provider)
                    self.assertEqual(item["fetched_via"], provider)

    def test_provider_risk_dict_completeness(self):
        """PROVIDER_RISK must map all known providers."""
        required = {"native_web_search", "jina_reader", "jina_search", "firecrawl", "browserbase", "curl"}
        self.assertTrue(required.issubset(collect.PROVIDER_RISK.keys()))

    def test_safe_providers_in_dict(self):
        for p in ("native_web_search", "jina_reader", "jina_search", "firecrawl"):
            self.assertEqual(collect.PROVIDER_RISK[p], "SAFE")

    def test_elevated_providers_in_dict(self):
        for p in ("browserbase", "curl"):
            self.assertEqual(collect.PROVIDER_RISK[p], "ELEVATED")


# ---------------------------------------------------------------------------
# AC9-8(5): error / rate_limited path
# ---------------------------------------------------------------------------


class TestErrorPaths(unittest.TestCase):

    def test_error_status_items_empty(self):
        payload = {"status": "error", "error": {"type": "network_error", "message": "timeout"}}
        result = collect.normalize("native_web_search", payload)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.items, [])
        self.assertIsNotNone(result.error)
        self.assertIn("type", result.error)
        self.assertIn("message", result.error)
        self.assertGreater(len(result.next_valid_actions), 0)

    def test_rate_limited_status(self):
        payload = {"status": "rate_limited"}
        result = collect.normalize("native_web_search", payload)
        self.assertEqual(result.status, "rate_limited")
        self.assertEqual(result.items, [])
        self.assertIsNotNone(result.error)
        self.assertGreater(len(result.next_valid_actions), 0)
        # recovery action should mention backoff
        actions_str = " ".join(result.next_valid_actions)
        self.assertIn("retry", actions_str)

    def test_disabled_status(self):
        payload = {"status": "disabled"}
        result = collect.normalize("native_web_search", payload)
        self.assertEqual(result.status, "disabled")
        self.assertEqual(result.items, [])
        self.assertGreater(len(result.next_valid_actions), 0)

    def test_error_via_error_key(self):
        """Dict with top-level 'error' key should also produce status=error."""
        payload = {"error": {"type": "auth_error", "message": "invalid API key"}}
        result = collect.normalize("jina_search", payload)
        self.assertIn(result.status, ("error", "rate_limited"))
        self.assertEqual(result.items, [])
        self.assertGreater(len(result.next_valid_actions), 0)

    def test_error_next_valid_actions_nonempty(self):
        """next_valid_actions must always be non-empty on error paths."""
        for payload in [
            {"status": "error", "error": {"type": "t", "message": "m"}},
            {"status": "rate_limited"},
            {"status": "disabled"},
        ]:
            with self.subTest(payload=payload):
                result = collect.normalize("firecrawl", payload)
                self.assertGreater(len(result.next_valid_actions), 0)


# ---------------------------------------------------------------------------
# AC9-8(6): end-to-end: ingest_sources(collect.normalize(...).items, NOW)
#           yields valid Source objects; ingest stamps trust + _fence;
#           collect did NOT pre-stamp _fence
# ---------------------------------------------------------------------------


class TestEndToEndIngest(unittest.TestCase):

    def test_normalised_items_ingestible(self):
        """Items from normalize should round-trip through ingest_sources without error."""
        payload = [
            {
                "url": "https://trusted.gov/report",
                "title": "Official Report",
                "snippet": "Key finding: GDP grew 3.2%",
                "tier": "S",
                "published_at": "2026-05-01",
                "scores": {"independence": 0.9, "traceability": 0.8},
            },
            {
                "url": "https://blog.example.com/post",
                "title": "Blog Post",
                "snippet": "Opinion piece",
                "tier": "C",
            },
        ]
        cr = collect.normalize("native_web_search", payload)
        self.assertEqual(cr.status, "ok")
        sources, merges = ingest.ingest_sources(cr.items, NOW)
        self.assertGreater(len(sources), 0)

    def test_ingest_stamps_fence(self):
        """ingest.source_from_raw must stamp extract['_fence'] on every source."""
        payload = [{"url": "https://ex.com/a", "title": "T", "snippet": "s"}]
        cr = collect.normalize("native_web_search", payload)
        sources, _ = ingest.ingest_sources(cr.items, NOW)
        self.assertTrue(sources, "should produce at least one source")
        for src in sources:
            self.assertIn("_fence", src.extract)

    def test_collect_does_not_pre_stamp_fence(self):
        """collect.normalize items must NOT carry '_fence' in 'extract' key.

        The fence is ingest's responsibility; carrying it here risks divergence.
        """
        payload = [{"url": "https://ex.com/b", "title": "T", "snippet": "s"}]
        cr = collect.normalize("native_web_search", payload)
        for item in cr.items:
            extract = item.get("extract", {})
            self.assertNotIn("_fence", extract,
                             "collect.normalize must not pre-stamp _fence; that belongs to ingest")

    def test_ingest_stamps_trust_untrusted_by_default(self):
        """All collect-produced items should land as UNTRUSTED in ingest."""
        payload = [{"url": "https://ex.com/c", "title": "T", "snippet": "s"}]
        cr = collect.normalize("native_web_search", payload)
        sources, _ = ingest.ingest_sources(cr.items, NOW)
        for src in sources:
            self.assertEqual(src.trust, TrustLevel.UNTRUSTED)

    def test_collect_drops_injected_trust_trusted(self):
        """Trust-boundary regression (code-review Phase 9): a remote provider
        payload carrying trust='trusted' must NOT escalate the source to TRUSTED.
        collect drops trust entirely; ingest defaults it to UNTRUSTED."""
        payload = [{"url": "https://evil.com/x", "title": "T", "snippet": "s",
                    "trust": "trusted"}]
        cr = collect.normalize("firecrawl", payload)
        # collect item must not carry a trust key at all
        self.assertNotIn("trust", cr.items[0])
        sources, _ = ingest.ingest_sources(cr.items, NOW)
        self.assertEqual(sources[0].trust, TrustLevel.UNTRUSTED)

    def test_metadata_string_values_are_capped(self):
        """Full-body guarantee (code-review Phase 9): a long string inside the
        provider metadata dict is capped, not smuggled in uncapped."""
        payload = [{"url": "https://fc.com/x", "title": "T", "markdown": "short",
                    "metadata": {"description": "z" * 1500}}]
        cr = collect.normalize("firecrawl", payload, snippet_cap=1000)
        self.assertEqual(len(cr.items[0]["metadata"]["description"]), 1000)

    def test_end_to_end_multi_provider(self):
        """Collect from multiple providers, merge into one ingest batch."""
        ws_items = collect.normalize("native_web_search", [
            {"url": "https://ws.com/a", "title": "WS A", "snippet": "web search content"},
        ]).items
        jina_items = collect.normalize("jina_reader", [
            {"url": "https://jina.com/b", "title": "Jina B", "text": "jina content"},
        ]).items
        fc_items = collect.normalize("firecrawl", [
            {"url": "https://fc.com/c", "title": "FC C", "markdown": "firecrawl content"},
        ]).items

        all_items = ws_items + jina_items + fc_items
        sources, _ = ingest.ingest_sources(all_items, NOW)
        self.assertEqual(len(sources), 3)
        # Each source should have _fence stamped by ingest
        for src in sources:
            self.assertIn("_fence", src.extract)
        # fetched_via should be preserved from item into Source
        fvs = {src.fetched_via for src in sources}
        self.assertEqual(fvs, {"native_web_search", "jina_reader", "firecrawl"})

    def test_collect_result_is_typed_collection_result(self):
        """normalize must return a CollectionResult with the required fields."""
        cr = collect.normalize("native_web_search", _WEB_SEARCH_PAYLOAD)
        self.assertIsInstance(cr, collect.CollectionResult)
        self.assertIsInstance(cr.status, str)
        self.assertIsInstance(cr.summary, str)
        self.assertIsInstance(cr.items, list)
        self.assertIsInstance(cr.next_valid_actions, list)

    def test_ok_result_next_valid_actions_includes_ingest(self):
        """On a successful 'ok' result, next_valid_actions should guide caller to ingest."""
        cr = collect.normalize("native_web_search", _WEB_SEARCH_PAYLOAD)
        self.assertEqual(cr.status, "ok")
        self.assertGreater(len(cr.next_valid_actions), 0)
        # At least one action should reference ingest
        actions_str = " ".join(cr.next_valid_actions)
        self.assertIn("ingest", actions_str)


if __name__ == "__main__":
    unittest.main()
