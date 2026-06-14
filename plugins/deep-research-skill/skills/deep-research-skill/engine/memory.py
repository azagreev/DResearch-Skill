"""Phase 5 — cross-run memory (SQLite WAL + FTS5).

Persists each run's sources and claims, deduping ACROSS runs (sources by
normalized URL, claims by normalized-text key), so the engine can answer "have
we seen this before?" and accumulate a searchable record for retro. The same
source/claim seen again bumps a sighting counter instead of duplicating.

stdlib-only (sqlite3). FTS5 is used when the local SQLite build provides it,
otherwise search falls back to LIKE. Python >= 3.10.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dedupe import normalize_text, normalize_url
from .model import Snapshot

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id           TEXT PRIMARY KEY,
  task_fingerprint TEXT,
  created_utc      TEXT,
  status           TEXT
);
CREATE TABLE IF NOT EXISTS sources (
  url_norm       TEXT PRIMARY KEY,
  url            TEXT,
  title          TEXT,
  tier           TEXT,
  first_seen     TEXT,
  last_seen      TEXT,
  sighting_count INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS claims (
  claim_key      TEXT PRIMARY KEY,
  text           TEXT,
  category       TEXT,
  confidence     INTEGER,
  first_seen     TEXT,
  last_seen      TEXT,
  sighting_count INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS feedback (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id        TEXT,
  item_id       TEXT,
  kind          TEXT,
  engine_value  TEXT,
  human_value   TEXT,
  trace_json    TEXT,
  recorded_utc  TEXT
);
CREATE INDEX IF NOT EXISTS idx_sources_tier ON sources(tier);
CREATE INDEX IF NOT EXISTS idx_claims_category ON claims(category);
CREATE INDEX IF NOT EXISTS idx_feedback_kind ON feedback(kind);
CREATE INDEX IF NOT EXISTS idx_feedback_run ON feedback(run_id);
"""


def _detect_fts5() -> bool:
    try:
        probe = sqlite3.connect(":memory:")
        probe.execute("CREATE VIRTUAL TABLE _t USING fts5(x)")
        probe.close()
        return True
    except sqlite3.OperationalError:
        return False


FTS5_AVAILABLE = _detect_fts5()


def claim_key(text: str) -> str:
    """Stable dedup key for a claim: sha1 of its normalized text."""
    return hashlib.sha1(normalize_text(text).encode("utf-8")).hexdigest()


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open (and migrate) the memory DB. db_path=None -> in-memory (tests)."""
    conn = sqlite3.connect(":memory:" if db_path is None else str(db_path))
    conn.row_factory = sqlite3.Row
    if db_path is not None:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(_SCHEMA)
    if FTS5_AVAILABLE:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(claim_key UNINDEXED, text)")
    conn.commit()
    return conn


def record_run(conn: sqlite3.Connection, snapshot: Snapshot, now_utc: str) -> Dict[str, int]:
    """Persist a snapshot's sources + claims, deduping across runs. Returns
    {"new_sources","updated_sources","new_claims","updated_claims"}.
    """
    stats = {"new_sources": 0, "updated_sources": 0, "new_claims": 0, "updated_claims": 0}

    conn.execute(
        "INSERT OR REPLACE INTO runs(run_id, task_fingerprint, created_utc, status) VALUES (?,?,?,?)",
        (snapshot.run_id, snapshot.task_fingerprint, snapshot.created_utc, "recorded"),
    )

    for source in snapshot.sources:
        url_norm = normalize_url(source.url)
        if not url_norm:
            continue
        tier = source.tier.value if source.tier is not None else None
        exists = conn.execute("SELECT 1 FROM sources WHERE url_norm=?", (url_norm,)).fetchone()
        if exists:
            conn.execute(
                "UPDATE sources SET last_seen=?, sighting_count=sighting_count+1, "
                "title=COALESCE(NULLIF(?,''), title), tier=COALESCE(?, tier) WHERE url_norm=?",
                (now_utc, source.title, tier, url_norm),
            )
            stats["updated_sources"] += 1
        else:
            conn.execute(
                "INSERT INTO sources(url_norm, url, title, tier, first_seen, last_seen, sighting_count) "
                "VALUES (?,?,?,?,?,?,1)",
                (url_norm, source.url, source.title, tier, now_utc, now_utc),
            )
            stats["new_sources"] += 1

    for claim in snapshot.claims:
        key = claim_key(claim.text)
        exists = conn.execute("SELECT 1 FROM claims WHERE claim_key=?", (key,)).fetchone()
        if exists:
            conn.execute(
                "UPDATE claims SET last_seen=?, sighting_count=sighting_count+1, category=?, confidence=? "
                "WHERE claim_key=?",
                (now_utc, claim.category.value, claim.confidence, key),
            )
            stats["updated_claims"] += 1
        else:
            conn.execute(
                "INSERT INTO claims(claim_key, text, category, confidence, first_seen, last_seen, sighting_count) "
                "VALUES (?,?,?,?,?,?,1)",
                (key, claim.text, claim.category.value, claim.confidence, now_utc, now_utc),
            )
            if FTS5_AVAILABLE:
                conn.execute("INSERT INTO claims_fts(claim_key, text) VALUES (?,?)", (key, claim.text))
            stats["new_claims"] += 1

    conn.commit()
    return stats


def seen_source(conn: sqlite3.Connection, url: str) -> bool:
    url_norm = normalize_url(url)
    if not url_norm:
        return False
    return conn.execute("SELECT 1 FROM sources WHERE url_norm=?", (url_norm,)).fetchone() is not None


def seen_claim(conn: sqlite3.Connection, text: str) -> bool:
    return conn.execute("SELECT 1 FROM claims WHERE claim_key=?", (claim_key(text),)).fetchone() is not None


def _fts_query(query: str) -> str:
    """Turn arbitrary user text into a safe FTS5 MATCH expression: each token is
    wrapped as a quoted literal (internal quotes doubled), so FTS5 operators in
    the text (&, +, -, :, *, AND/OR, unbalanced quotes) are matched literally
    instead of crashing the parser.
    """
    tokens = [t for t in query.split() if t]
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


def search_claims(conn: sqlite3.Connection, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Full-text search over recorded claims (FTS5 if available, else LIKE)."""
    if not query.strip():
        return []
    if FTS5_AVAILABLE:
        try:
            rows = conn.execute(
                "SELECT c.* FROM claims_fts f JOIN claims c ON c.claim_key=f.claim_key "
                "WHERE claims_fts MATCH ? ORDER BY rank LIMIT ?",
                (_fts_query(query), limit),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            pass  # malformed FTS expression -> fall back to LIKE
    rows = conn.execute("SELECT * FROM claims WHERE text LIKE ? LIMIT ?", (f"%{query}%", limit)).fetchall()
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------- #
# Feedback ledger — append-only human-vs-engine calibration record (AC14-4)
# --------------------------------------------------------------------------- #
# This is a HUMAN-REVIEWED calibration dataset, NOT an input to scoring. The
# scoring path (score.py / factcheck.py) must never read from `feedback`; the
# presence of rows here must not change any score, tier, or verdict the engine
# produces. It is consumed only by offline retro/analysis.
def record_feedback(conn: sqlite3.Connection, record: dict, now_utc: str) -> Dict[str, Any]:
    """Append one feedback row. APPEND-ONLY: always INSERT, never UPDATE — two
    records with the same item_id produce two distinct rows (a full review
    history is kept). `now_utc` is passed in (ISO); the engine reads no clock.
    `trace_json` is stored verbatim if a string, else JSON-encoded.

    Returns {"id": <new rowid>} for the inserted row.
    """
    trace = record.get("trace_json")
    if trace is not None and not isinstance(trace, str):
        trace = json.dumps(trace, ensure_ascii=False)
    cur = conn.execute(
        "INSERT INTO feedback(run_id, item_id, kind, engine_value, human_value, trace_json, recorded_utc) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            record.get("run_id"),
            record.get("item_id"),
            record.get("kind"),
            record.get("engine_value"),
            record.get("human_value"),
            trace,
            now_utc,
        ),
    )
    conn.commit()
    return {"id": cur.lastrowid}


def list_feedback(
    conn: sqlite3.Connection,
    *,
    kind: Optional[str] = None,
    run_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return feedback rows (oldest first by insertion order / rowid), optionally
    filtered by `kind` and/or `run_id`. Read-only.
    """
    where: List[str] = []
    params: List[Any] = []
    if kind is not None:
        where.append("kind=?")
        params.append(kind)
    if run_id is not None:
        where.append("run_id=?")
        params.append(run_id)
    sql = "SELECT * FROM feedback"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def get_stats(conn: sqlite3.Connection) -> Dict[str, int]:
    def count(table: str) -> int:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    return {
        "runs": count("runs"),
        "sources": count("sources"),
        "claims": count("claims"),
        "feedback": count("feedback"),
    }
