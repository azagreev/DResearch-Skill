"""Phase 6 — instruction-coverage audit (H5, hyperresearch reuse).

The mechanical core of an instruction-critic: flag acceptance-criteria and scope
items that NO finding addresses — an item is "covered" if it shares at least one
significant term (>= 4 chars, minus common ru/en stopwords) with some claim text
or cluster title. Read-only, warning-level, surfaced by `engine instrcheck`; NOT
wired into rendering, so the report stays byte-identical.

This is the deterministic half of "did we answer what was asked, in the shape
asked". The dialectic half (un-engaged counter-evidence) is semantic and stays a
review pass in the agent layer, outside the deterministic engine. Pure,
deterministic, offline, stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

import re
from typing import List, Set

from .model import Snapshot

# Common ru/en function words that carry no topical signal — excluded so overlap
# reflects content terms, not glue.
_STOP = frozenset((
    "и во не что он на со как то все она так его но да ты же вы за бы по только ее "
    "мне было вот от меня еще нет из ему для или при над под это эта эти этот тот "
    "the and for that this with are was from have has not but you your they them "
    "will can may per via into over under about which whose when then than").split())

_WORD_RE = re.compile(r"[\w-]{4,}", re.UNICODE)


def _terms(text: str) -> Set[str]:
    return {w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOP}


def uncovered_criteria(snapshot: Snapshot) -> List[str]:
    """Acceptance-criteria + scope items with ZERO significant-term overlap with
    any finding (claim text) or cluster title, in declaration order (criteria
    then scope). An item with no significant terms of its own is never flagged."""
    pool: Set[str] = set()
    for claim in snapshot.claims:
        pool |= _terms(claim.text)
    for cluster in snapshot.clusters:
        pool |= _terms(cluster.title)

    tf = snapshot.task_frame
    items = list(tf.acceptance_criteria) + list(tf.scope)
    uncovered: List[str] = []
    for item in items:
        item_terms = _terms(item)
        if item_terms and not (item_terms & pool):
            uncovered.append(item)
    return uncovered
