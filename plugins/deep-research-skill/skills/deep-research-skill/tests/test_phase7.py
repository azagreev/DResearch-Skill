"""Phase 7 unit tests — integration glue + robustness fixes from the review.

Run from the skill dir:  python -m unittest discover -s tests -t .
"""

import unittest

from engine import dedupe, factcheck, ingest, memory, pipeline, providers, score
from engine.model import (
    Claim,
    ClaimCategory,
    ClaimRole,
    Depth,
    Route,
    ScoreComponents,
    Source,
    TaskFrame,
    Tier,
    validate_snapshot,
)

NOW = "2026-06-30T00:00:00Z"


class TestNormalizeUrlFixes(unittest.TestCase):
    def test_scheme_less_and_ports(self):
        self.assertEqual(dedupe.normalize_url("example.com/a"), "https://example.com/a")
        self.assertEqual(dedupe.normalize_url("http://example.com:80/a"), "https://example.com/a")
        self.assertEqual(dedupe.normalize_url("https://example.com:443/a/"), "https://example.com/a")

    def test_scheme_less_dedupe(self):
        kept, merges = dedupe.dedupe_sources(
            [Source(id="S1", url="https://e.com/a"), Source(id="S2", url="e.com/a")]
        )
        self.assertEqual([s.id for s in kept], ["S1"])
        self.assertIn(("S1", "S2"), merges)


class TestAuthoritySeeding(unittest.TestCase):
    def test_authority_seeded_from_tier(self):
        src = Source(id="x", url="u", tier=Tier.S)  # authority unset
        score.score_source(src)
        self.assertEqual(src.scores.authority, 1.0)  # seeded from Tier.S


class TestIngest(unittest.TestCase):
    def test_source_from_raw_and_dedupe(self):
        raw = [
            {"url": "https://a.com/x", "title": "A", "tier": "S", "published_at": "2026-06-01",
             "snippet": "snip", "scores": {"independence": 0.9}},
            {"link": "https://www.a.com/x/"},  # same page -> merged
            {"url": "https://b.com", "tier": "d"},
        ]
        kept, merges = ingest.ingest_sources(raw, NOW)
        self.assertEqual([s.id for s in kept], ["S1", "S3"])
        self.assertIn(("S1", "S2"), merges)
        s1 = kept[0]
        self.assertEqual(s1.tier, Tier.S)
        self.assertEqual(s1.extract, {"snippet": "snip"})
        self.assertEqual(s1.created_utc, NOW)
        self.assertEqual(s1.scores.independence, 0.9)


class TestReconcileAndBuild(unittest.TestCase):
    def test_reconcile_merges(self):
        claims = [Claim(id="C1", text="x", sources=["S1", "S2"], contradicting_sources=["S3"])]
        pipeline.reconcile_merges(claims, [("S1", "S2")])
        self.assertEqual(claims[0].sources, ["S1"])
        self.assertEqual(claims[0].contradicting_sources, ["S3"])

    def test_build_snapshot_fingerprint(self):
        tf = TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD)
        from engine.state import compute_fingerprint
        snap = pipeline.build_snapshot("r", tf, [Source(id="S1", url="u")], [])
        self.assertEqual(snap.task_fingerprint, compute_fingerprint(tf))


class TestRunPipeline(unittest.TestCase):
    def test_end_to_end(self):
        tf = TaskFrame(question="Whoop price CDEK", route=Route.FOCUSED, depth=Depth.STANDARD)
        raw = [
            {"url": "https://cdek.shopping/whoop", "title": "Whoop 4.0 price", "tier": "S",
             "published_at": "2026-06-25", "time_sensitive": True,
             "scores": {"independence": 0.9, "traceability": 0.9, "corroboration": 0.8}},
            {"url": "https://www.cdek.shopping/whoop/"},          # dup of S1
            {"url": "https://forum.ru/thread", "title": "chatter", "tier": "d"},
        ]
        claims = [Claim(id="C1", text="Whoop 4.0 стоит 30000 руб", role=ClaimRole.OWN_FINDING, sources=["S1", "S2"])]
        snapshot, merges = pipeline.run_pipeline("r1", tf, raw, claims, NOW)

        self.assertIn(("S1", "S2"), merges)
        self.assertEqual(len(snapshot.sources), 2)                 # deduped
        self.assertEqual(snapshot.claims[0].sources, ["S1"])       # reconciled
        cdek = next(s for s in snapshot.sources if "cdek" in s.url)
        self.assertIn(cdek.tier, (Tier.S, Tier.A))                 # authority seeded -> high, not C/D
        forum = next(s for s in snapshot.sources if "forum" in s.url)
        self.assertEqual(forum.tier, Tier.D)
        self.assertEqual(snapshot.claims[0].category, ClaimCategory.VERIFIED)
        self.assertTrue(snapshot.clusters)
        self.assertEqual(validate_snapshot(snapshot), [])          # coherent, no dangling refs


class TestFtsSpecialChars(unittest.TestCase):
    def test_no_crash_on_operators(self):
        conn = memory.connect()
        from engine.model import Snapshot
        snap = Snapshot(
            run_id="r", task_fingerprint="fp",
            task_frame=TaskFrame(question="q", route=Route.FOCUSED, depth=Depth.STANDARD),
            claims=[Claim(id="C1", text="AT&T pricing in 2026", category=ClaimCategory.VERIFIED, confidence=4)],
        )
        memory.record_run(conn, snap, NOW)
        for q in ("AT&T", 'a "quote', "c++", "foo OR", "near:"):
            self.assertIsInstance(memory.search_claims(conn, q), list)  # no OperationalError
        self.assertTrue(memory.search_claims(conn, "pricing"))


class TestProvidersPost(unittest.TestCase):
    def test_exa_posts_body(self):
        captured = {}

        def fake(url, headers, body):
            captured["url"], captured["body"] = url, body
            return {"results": [{"url": "https://e", "title": "T", "text": "snip"}]}

        cfg = {"DRESEARCH_PAID_SEARCH": "1", "EXA_API_KEY": "k"}
        items, meta = providers.web_search("hello", cfg, backend="exa", http=fake)
        self.assertEqual(captured["body"], {"query": "hello", "numResults": 5})
        self.assertEqual(meta["backend"], "exa")
        self.assertEqual(items[0]["url"], "https://e")


class TestFactcheckModelCategories(unittest.TestCase):
    def test_hint_honored(self):
        sources = [Source(id="S", url="u", tier=Tier.S)]
        c = Claim(id="C1", text="x", sources=["S"])
        factcheck.factcheck_claims([c], sources, NOW, model_categories={"C1": ClaimCategory.INCOMPLETE})
        self.assertEqual(c.category, ClaimCategory.INCOMPLETE)


if __name__ == "__main__":
    unittest.main()
