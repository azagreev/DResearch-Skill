"""Phase 3 — computed source independence (H2, hyperresearch reuse).

"Syndication != consensus": N reworded reprints of ONE story must count as ~1
independent voice, not N. This clusters sources by near-duplicate body text (and
identical canonical URL) with union-find, then scores each member
`1 / cluster_size` in [0, 1]. That value fills ScoreComponents.independence
(weight 0.20 in the composite), so a syndicated source scores a lower composite
-> lower tier -> less confidence — WITHOUT touching the confidence ladder.

`consensus_strength` exposes the independence-weighted corroboration count for a
claim (five reprints ~= one vote). Pure, deterministic, offline, stdlib-only.

The near-duplicate threshold (default 0.70) is deliberately LOWER than dedupe's
0.85: dedupe collapses verbatim copies; independence must also catch reworded
syndication that dedupe intentionally kept as distinct rows. Python >= 3.10.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .dedupe import _source_text, char_ngrams, jaccard, normalize_url, tokens
from .model import Claim, Source

DEFAULT_SIM_THRESHOLD = 0.70


def compute_independence(sources: List[Source], sim_threshold: float = DEFAULT_SIM_THRESHOLD) -> Dict[str, float]:
    """Map source id -> independence in (0, 1]: 1/cluster_size, where sources are
    unioned when they share a canonical URL OR their body text similarity
    (char-trigram + token Jaccard blend, mirroring dedupe) is >= sim_threshold.
    Deterministic and order-independent per id (union root = lowest index)."""
    n = len(sources)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)  # lowest index wins -> deterministic

    texts = [_source_text(s) for s in sources]
    grams = [char_ngrams(t) for t in texts]
    toks = [tokens(t) for t in texts]
    nurls = [normalize_url(s.url) for s in sources]

    for i in range(n):
        for j in range(i + 1, n):
            same_url = bool(nurls[i]) and nurls[i] == nurls[j]
            sim = 0.5 * jaccard(grams[i], grams[j]) + 0.5 * jaccard(toks[i], toks[j])
            if same_url or sim >= sim_threshold:
                union(i, j)

    roots = [find(i) for i in range(n)]
    sizes = Counter(roots)
    return {sources[i].id: 1.0 / sizes[roots[i]] for i in range(n)}


def apply_independence(
    sources: List[Source],
    sim_threshold: float = DEFAULT_SIM_THRESHOLD,
    overwrite: bool = False,
) -> Dict[str, float]:
    """Compute independence and write it onto each source's ScoreComponents.
    By default only fills sources whose independence is unset (None), so an
    explicit caller-provided value is preserved (byte-identity). Returns the
    computed id->value map. Does NOT recompute the composite — callers re-run
    score.score_sources to fold the new component into composite/tier."""
    scores = compute_independence(sources, sim_threshold)
    for source in sources:
        if overwrite or source.scores.independence is None:
            source.scores.independence = scores[source.id]
    return scores


def consensus_strength(claim: Claim, sources_by_id: Dict[str, Source]) -> float:
    """Independence-weighted corroboration for a claim: sum of each cited
    source's independence. A source whose independence has not been computed
    counts as 1.0 (fully independent) — a safe default that never UNDER-counts
    consensus without an explicit syndication signal."""
    total = 0.0
    for sid in claim.sources:
        source = sources_by_id.get(sid)
        if source is None:
            continue
        value = source.scores.independence
        total += value if value is not None else 1.0
    return total
