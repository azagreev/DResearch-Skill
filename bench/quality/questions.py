"""BINEVAL-style report self-grader question bank (a cheap DRACO proxy).

DRACO (bench/draco.py) grades a report's outcome quality via an expensive LLM
judge against a per-task rubric. This module decomposes that same evaluation into
a STATIC bank of atomic yes/no questions, grouped by the four DRACO axes, so a
report can be graded cheaply and interpretably:

  * DETERMINISTIC questions are answered by a pure function over a `Snapshot`
    (engine/model.py) — no LLM, no network, no clock/random. These cover the
    machine-checkable acceptance criteria (every finding cited, every claim
    confidence-scored, source diversity, no own-finding shipped as FALSE, ...).
  * JUDGMENT questions are subjective (factual accuracy vs sources, analytical
    depth, coherence, presentation) and are left to an external LLM judge.

Question text is seeded from the R/A/C/S acceptance criteria and the 5 quality
gates in references/acceptance_framework.md. The deterministic checkers REUSE
`bench.trust.metrics` and engine model fields rather than reimplementing citation
or suppression logic.

`Polarity` mirrors DRACO's signed rubric weights: a POSITIVE question rewards a
desirable property (yes = good); a NEGATIVE question describes an error (yes =
the error is PRESENT), exactly like a negative-weight DRACO criterion whose MET
verdict means the flaw exists.

stdlib-only, deterministic. Python >= 3.10.
See bench/draco.py (AXES), bench/trust/metrics.py, references/acceptance_framework.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Optional, Tuple

from bench.draco import AXES
# `Snapshot` is the engine run-state record the deterministic checkers read.
# All engine types come through the same bench bootstrap the trust layer uses
# (bench.trust._engine puts the engine package on sys.path and re-exports them).
from bench.trust._engine import (
    Claim,
    ClaimRole,
    Snapshot,
    snapshot_to_dict,  # noqa: F401  (re-exported for downstream convenience)
)


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class QKind(str, Enum):
    """How a question is answered."""

    DETERMINISTIC = "deterministic"  # pure function over a Snapshot, no LLM
    JUDGMENT = "judgment"            # needs an external LLM judge


class Polarity(str, Enum):
    """Sign of the question, mirroring DRACO signed rubric weights."""

    POSITIVE = "positive"  # yes = good (desirable property present)
    NEGATIVE = "negative"  # yes = error PRESENT (mirrors a negative-weight criterion)


# --------------------------------------------------------------------------- #
# Question record
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BinaryQuestion:
    """One atomic yes/no quality question.

    `axis` must be one of `bench.draco.AXES`. `polarity` says how to read a
    "yes": POSITIVE -> yes is good; NEGATIVE -> yes means the error is present.
    `kind` says whether a deterministic checker can answer it (DETERMINISTIC) or
    an LLM judge is required (JUDGMENT).
    """

    id: str
    axis: str
    text: str
    polarity: Polarity
    kind: QKind


# --------------------------------------------------------------------------- #
# Deterministic checker helpers (pure, over a Snapshot)
# --------------------------------------------------------------------------- #
# Each checker returns True (question MET) / False (UNMET) / None (not applicable
# -> leave unjudged). For NEGATIVE-polarity questions, True means the error IS
# present. Checkers must be deterministic: no clock, no random, no network.
#
# NOTE on "rendered": these checkers grade the Snapshot's claim set directly
# rather than re-running the engine to inspect the rendered Markdown. We treat a
# claim as a reportable FINDING when its role is OWN_FINDING and it carries at
# least one supporting source (the engine suppresses 0-source own findings); see
# engine/policy.py disposition logic. This keeps the checkers a pure function of
# the Snapshot (no pipeline re-run, fully deterministic).


def _own_findings(snapshot: "Snapshot") -> list:
    """Own-finding claims (the report's own assertions, not external claims)."""
    return [c for c in snapshot.claims if c.role == ClaimRole.OWN_FINDING]


def _reportable_findings(snapshot: "Snapshot") -> list:
    """Own findings that would survive into the report (>=1 supporting source).

    Mirrors the engine's suppression of 0-source own findings without re-running
    the pipeline, so the check stays a pure function of the Snapshot.
    """
    return [c for c in _own_findings(snapshot) if len(c.sources) >= 1]


def _check_all_findings_cited(snapshot: "Snapshot") -> Optional[bool]:
    """S-01 / Gate 4.2: every reportable own finding cites >=1 source.

    By construction a reportable finding has >=1 source, so the meaningful test
    is whether any own finding would be DROPPED for lack of a citation. Returns
    True when 100% of own findings carry a citation, False otherwise, None when
    there are no own findings to judge.
    """
    own = _own_findings(snapshot)
    if not own:
        return None
    return all(len(c.sources) >= 1 for c in own)


def _check_all_claims_confidence_scored(snapshot: "Snapshot") -> Optional[bool]:
    """S-04 / Gate 4.3: every claim carries a valid 1..5 confidence score."""
    if not snapshot.claims:
        return None
    return all(1 <= c.confidence <= 5 for c in snapshot.claims)


def _check_source_type_diversity(snapshot: "Snapshot") -> Optional[bool]:
    """R-02 / Gate 1.2: >=4 distinct source tiers/types present.

    Counts distinct authority tiers among scored sources as the diversity proxy
    (acceptance_framework R-02 / §6.4 require >=4 source types; tier is the
    machine-readable diversity signal in the Snapshot).
    """
    if not snapshot.sources:
        return None
    tiers = {s.tier for s in snapshot.sources if s.tier is not None}
    return len(tiers) >= 4


def _check_primary_source_present(snapshot: "Snapshot") -> Optional[bool]:
    """R-05 / §6.1: at least one Tier S (primary) source backs the research."""
    if not snapshot.sources:
        return None
    return any(getattr(s.tier, "value", None) == "S" for s in snapshot.sources)


def _check_no_false_own_finding(snapshot: "Snapshot") -> Optional[bool]:
    """NEGATIVE — Gate 4 / policy: an OWN finding is shipped as FALSE.

    A FALSE own finding must trigger revision, never be presented as a result.
    Returns True when the error IS present (>=1 own finding categorized FALSE),
    False when clean, None when there are no own findings.
    """
    own = _own_findings(snapshot)
    if not own:
        return None
    return any(getattr(c.category, "value", None) == "false" for c in own)


def _check_unverified_in_findings(snapshot: "Snapshot") -> Optional[bool]:
    """NEGATIVE — anti-hallucination: an UNVERIFIED claim is presented as a
    reportable finding (own finding with a citation yet still unverified).

    Returns True when the error IS present, False when clean, None when there
    are no reportable findings.
    """
    findings = _reportable_findings(snapshot)
    if not findings:
        return None
    return any(getattr(c.category, "value", None) == "unverified" for c in findings)


def _check_sources_tier_scored(snapshot: "Snapshot") -> Optional[bool]:
    """Gate 1.3 / auditability: 100% of sources carry an authority tier.

    A tier-less source cannot be quality-gated; full tier coverage is the
    machine-checkable form of "source attribution complete".
    """
    if not snapshot.sources:
        return None
    return all(s.tier is not None for s in snapshot.sources)


def _check_claims_reference_real_sources(snapshot: "Snapshot") -> Optional[bool]:
    """Gate 5.2 / auditability: detect dangling citations (cit3, NEGATIVE polarity).

    A citation pointing at a non-existent source id is a dangling reference (an
    un-auditable citation). cit3 is a NEGATIVE-polarity question, so the checker
    returns True when the error IS present (a dangling reference exists) and
    False when every cited id resolves to a real Source.
    """
    if not snapshot.claims:
        return None
    known = {s.id for s in snapshot.sources}
    for c in snapshot.claims:
        for sid in c.sources:
            if sid not in known:
                return True  # dangling reference -> error present
    return False  # all citations resolve -> error absent


# --------------------------------------------------------------------------- #
# Question bank
# --------------------------------------------------------------------------- #
QUESTION_BANK: Tuple[BinaryQuestion, ...] = (
    # ---- factual-accuracy ------------------------------------------------- #
    BinaryQuestion(
        id="fa1",
        axis="factual-accuracy",
        text="Is every factual claim in the report accurate with respect to its "
        "cited sources (no misrepresentation or fabrication)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.JUDGMENT,
    ),
    BinaryQuestion(
        id="fa2",
        axis="factual-accuracy",
        text="Does the report present any of its OWN findings that the engine "
        "categorized as FALSE (a known-false assertion shipped as a result)?",
        polarity=Polarity.NEGATIVE,
        kind=QKind.DETERMINISTIC,
    ),
    BinaryQuestion(
        id="fa3",
        axis="factual-accuracy",
        text="Does the report present an UNVERIFIED claim as a reportable "
        "finding (asserting something that was never verified)?",
        polarity=Polarity.NEGATIVE,
        kind=QKind.DETERMINISTIC,
    ),
    BinaryQuestion(
        id="fa4",
        axis="factual-accuracy",
        text="Are key facts cross-verified by >=2 independent sources where the "
        "claim's importance warrants it (R-05)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.JUDGMENT,
    ),
    # ---- breadth-and-depth-of-analysis ------------------------------------ #
    BinaryQuestion(
        id="dep1",
        axis="breadth-and-depth-of-analysis",
        text="Does the analysis reach >=3 levels of depth per subtopic "
        "(overview -> detailed -> granular), per R-03?",
        polarity=Polarity.POSITIVE,
        kind=QKind.JUDGMENT,
    ),
    BinaryQuestion(
        id="dep2",
        axis="breadth-and-depth-of-analysis",
        text="Does the report consider >=2 alternative explanations or "
        "interpretations for each key conclusion (S-03)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.JUDGMENT,
    ),
    BinaryQuestion(
        id="dep3",
        axis="breadth-and-depth-of-analysis",
        text="Does the report draw on >=4 distinct source tiers/types, giving "
        "the analysis breadth of evidence (R-02)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.DETERMINISTIC,
    ),
    BinaryQuestion(
        id="dep4",
        axis="breadth-and-depth-of-analysis",
        text="Is the research grounded in >=1 primary (Tier S) source rather "
        "than relying solely on secondary commentary (R-05 / §6.1)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.DETERMINISTIC,
    ),
    # ---- presentation-quality --------------------------------------------- #
    BinaryQuestion(
        id="pres1",
        axis="presentation-quality",
        text="Is every claim assigned a confidence score and visualized, so the "
        "reader can calibrate trust (S-04 / Gate 5.3)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.DETERMINISTIC,
    ),
    BinaryQuestion(
        id="pres2",
        axis="presentation-quality",
        text="Is the report logically coherent and free of critical logical "
        "fallacies or self-contradictions (S-02)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.JUDGMENT,
    ),
    BinaryQuestion(
        id="pres3",
        axis="presentation-quality",
        text="Is the report well-structured and readable (clear sections, "
        "executive summary, consistent formatting) per Gate 5.4/5.6?",
        polarity=Polarity.POSITIVE,
        kind=QKind.JUDGMENT,
    ),
    BinaryQuestion(
        id="pres4",
        axis="presentation-quality",
        text="Is uncertainty explicitly stated for the key conclusions rather "
        "than hidden (S-06)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.JUDGMENT,
    ),
    # ---- citation-quality ------------------------------------------------- #
    BinaryQuestion(
        id="cit1",
        axis="citation-quality",
        text="Does 100% of reportable findings cite >=1 source (no uncited "
        "assertions), per S-01 / Gate 4.2?",
        polarity=Polarity.POSITIVE,
        kind=QKind.DETERMINISTIC,
    ),
    BinaryQuestion(
        id="cit2",
        axis="citation-quality",
        text="Is every source carrying an authority tier so each citation can "
        "be quality-gated (Gate 1.3 / §6)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.DETERMINISTIC,
    ),
    BinaryQuestion(
        id="cit3",
        axis="citation-quality",
        text="Does any citation point at a source id that does not exist in the "
        "source inventory (a dangling, un-auditable reference)?",
        polarity=Polarity.NEGATIVE,
        kind=QKind.DETERMINISTIC,
    ),
    BinaryQuestion(
        id="cit4",
        axis="citation-quality",
        text="Do the cited sources actually support the specific claims they are "
        "attached to (no citation padding or mismatched attribution)?",
        polarity=Polarity.POSITIVE,
        kind=QKind.JUDGMENT,
    ),
)


# --------------------------------------------------------------------------- #
# Deterministic checker registry
# --------------------------------------------------------------------------- #
DETERMINISTIC_CHECKERS: Dict[str, Callable[["Snapshot"], Optional[bool]]] = {
    "fa2": _check_no_false_own_finding,
    "fa3": _check_unverified_in_findings,
    "dep3": _check_source_type_diversity,
    "dep4": _check_primary_source_present,
    "pres1": _check_all_claims_confidence_scored,
    "cit1": _check_all_findings_cited,
    "cit2": _check_sources_tier_scored,
    "cit3": _check_claims_reference_real_sources,
}


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_bank() -> None:
    """Assert the bank's structural contract. Raises AssertionError on violation.

    Checks: ids unique; every axis in AXES; every DETERMINISTIC question has a
    checker and every checker id maps to a DETERMINISTIC question; all 4 axes
    covered.
    """
    ids = [q.id for q in QUESTION_BANK]
    assert len(ids) == len(set(ids)), "duplicate question ids in QUESTION_BANK"

    by_id = {q.id: q for q in QUESTION_BANK}

    for q in QUESTION_BANK:
        assert q.axis in AXES, f"question {q.id}: unknown axis {q.axis!r}"

    det_ids = {q.id for q in QUESTION_BANK if q.kind is QKind.DETERMINISTIC}
    checker_ids = set(DETERMINISTIC_CHECKERS)
    missing = det_ids - checker_ids
    assert not missing, f"DETERMINISTIC questions without a checker: {sorted(missing)}"
    extra = checker_ids - det_ids
    assert not extra, f"checker ids not mapped to a DETERMINISTIC question: {sorted(extra)}"

    for cid, fn in DETERMINISTIC_CHECKERS.items():
        assert cid in by_id, f"checker id {cid!r} not in QUESTION_BANK"
        assert callable(fn), f"checker for {cid!r} is not callable"

    covered = {q.axis for q in QUESTION_BANK}
    assert covered == set(AXES), f"axes not fully covered: missing {set(AXES) - covered}"


# Fail loudly at import time if the static bank drifts out of contract.
validate_bank()
