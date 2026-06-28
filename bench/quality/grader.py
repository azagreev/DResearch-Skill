"""BINEVAL-style deterministic aggregation core for the report self-grader.

Converts per-question verdicts (deterministic or injected from an external LLM
judge) into a DRACO-axis-weighted quality scorecard.  No third-party imports,
no network, no LLM calls — the judge is injected by the caller.

Public API
----------
QualityScore          Frozen dataclass; `.as_dict()` → canonical scorecard dict.
build_context         Assemble a serializable judge context from a Snapshot.
answer_deterministic  Run all DETERMINISTIC_CHECKERS over a Snapshot.
grade                 Build a QualityScore from a bare verdicts mapping (no Snapshot).
quality_scorecard     Full pipeline: deterministic + injected judge → scorecard dict.

Scoring convention (mirrors the FROZEN CONTRACT in the build spec)
------------------------------------------------------------------
For each judged question, good-score = 1.0 iff:
  - POSITIVE polarity and verdict is True   (desirable property present)
  - NEGATIVE polarity and verdict is False  (error absent)
verdict is None → question excluded from numerator AND denominator.

per_axis  = mean(good-scores) over judged questions in that axis.
            Axes with 0 judged questions are omitted from per_axis.
overall   = Σ(w_axis × per_axis[axis]) renormalised over judged axes.
            If no axis is judged → overall = 0.0.

DRACO axis weights: factual-accuracy 0.52, breadth-and-depth-of-analysis 0.22,
                    presentation-quality 0.14, citation-quality 0.12.

All floats are rounded to 4 decimal places.

stdlib-only, deterministic. Python >= 3.10.
See bench/quality/questions.py, bench/draco.py, bench/trust/metrics.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from bench.draco import AXES
from bench.quality.questions import (
    BinaryQuestion,
    DETERMINISTIC_CHECKERS,
    Polarity,
    QKind,
    QUESTION_BANK,
)
from bench.trust._engine import Snapshot, report

# --------------------------------------------------------------------------- #
# Axis weights (DRACO canonical)
# --------------------------------------------------------------------------- #
_AXIS_WEIGHTS: Dict[str, float] = {
    "factual-accuracy": 0.52,
    "breadth-and-depth-of-analysis": 0.22,
    "presentation-quality": 0.14,
    "citation-quality": 0.12,
}

# Sentinel: every axis must appear in the weight table.
assert set(_AXIS_WEIGHTS) == set(AXES), (
    f"_AXIS_WEIGHTS keys don't match AXES: "
    f"missing={set(AXES) - set(_AXIS_WEIGHTS)!r}, "
    f"extra={set(_AXIS_WEIGHTS) - set(AXES)!r}"
)


# --------------------------------------------------------------------------- #
# Per-question result row
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _QuestionRow:
    """Internal representation of one evaluated question."""

    id: str
    axis: str
    kind: str          # QKind.value
    polarity: str      # Polarity.value
    verdict: Optional[bool]
    explanation: str

    def good_score(self) -> Optional[float]:
        """1.0 = good, 0.0 = bad, None = unjudged (excluded from scoring)."""
        if self.verdict is None:
            return None
        if self.polarity == Polarity.POSITIVE.value:
            return 1.0 if self.verdict else 0.0
        # NEGATIVE polarity: error absent (verdict False) is good
        return 0.0 if self.verdict else 1.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "axis": self.axis,
            "kind": self.kind,
            "polarity": self.polarity,
            "verdict": self.verdict,
            "explanation": self.explanation,
        }


# --------------------------------------------------------------------------- #
# QualityScore
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class QualityScore:
    """Aggregated quality scorecard for one report.

    Produced by `_aggregate`; consumed by callers or serialised via `.as_dict()`.
    """

    per_axis: Dict[str, float]       # only axes with >=1 judged question
    overall: float                   # weighted average over judged axes, 0..1
    coverage: Dict[str, int]         # judged / deterministic / unjudged counts
    _rows: Tuple["_QuestionRow", ...] = field(repr=False)  # internal; iterable

    def as_dict(self) -> Dict[str, Any]:
        """Produce the canonical scorecard dict shape.

        Shape::

            {
              "per_axis":  {axis: float},       # only judged axes
              "overall":   float,               # 0..1, 4 dp
              "coverage":  {"judged": int, "deterministic": int, "unjudged": int},
              "questions": [{"id":str, "axis":str, "kind":str, "polarity":str,
                             "verdict":bool|None, "explanation":str}, ...],
            }
        """
        return {
            "per_axis": {ax: round(v, 4) for ax, v in self.per_axis.items()},
            "overall": round(self.overall, 4),
            "coverage": dict(self.coverage),
            "questions": [r.as_dict() for r in self._rows],
        }


# --------------------------------------------------------------------------- #
# Context builder
# --------------------------------------------------------------------------- #
def build_context(snapshot: "Snapshot") -> Dict[str, Any]:
    """Assemble a serializable judge context from a Snapshot.

    Returns a plain dict with two top-level keys:

    ``report_markdown``
        The rendered report text (via ``engine.report.render_markdown``).

    ``structured_facts``
        Compact structured representation: list of claim records
        (``text``, ``category``, ``sources`` list of source ids), and a
        separate list of source records (``id``, ``tier``).  An external LLM
        judge can read both the rendered narrative and the underlying data
        without re-running the pipeline.

    The function is deterministic and makes no network calls; it is safe to
    call multiple times on the same Snapshot.
    """
    markdown = report.render_markdown(snapshot)

    claims_data: List[Dict[str, Any]] = [
        {
            "text": c.text,
            "category": getattr(c.category, "value", None) if c.category is not None else None,
            "sources": list(c.sources),
        }
        for c in snapshot.claims
    ]

    sources_data: List[Dict[str, Any]] = [
        {
            "id": s.id,
            "tier": getattr(s.tier, "value", None) if s.tier is not None else None,
        }
        for s in snapshot.sources
    ]

    return {
        "report_markdown": markdown,
        "structured_facts": {
            "claims": claims_data,
            "sources": sources_data,
        },
    }


# --------------------------------------------------------------------------- #
# Deterministic answering
# --------------------------------------------------------------------------- #
def answer_deterministic(snapshot: "Snapshot") -> Dict[str, Optional[bool]]:
    """Run every DETERMINISTIC_CHECKERS entry over *snapshot*.

    Returns a mapping ``{question_id: verdict}`` where:

    * ``True``  — checker returned True (question MET; for NEGATIVE polarity
                  this means the *error is present*).
    * ``False`` — checker returned False (question UNMET).
    * ``None``  — checker returned None (not applicable → unjudged).

    Only ids present in DETERMINISTIC_CHECKERS are included in the result.
    The iteration order matches QUESTION_BANK for stability.
    """
    results: Dict[str, Optional[bool]] = {}
    for q in QUESTION_BANK:
        if q.kind is QKind.DETERMINISTIC and q.id in DETERMINISTIC_CHECKERS:
            try:
                results[q.id] = DETERMINISTIC_CHECKERS[q.id](snapshot)
            except Exception:
                # Checker raised — treat as unjudged (graceful degradation).
                results[q.id] = None
    return results


# --------------------------------------------------------------------------- #
# Core aggregation
# --------------------------------------------------------------------------- #
def _aggregate(
    verdicts: Mapping[str, Optional[bool]],
    explanations: Mapping[str, str],
) -> "QualityScore":
    """Aggregate per-question verdicts and explanations into a QualityScore.

    Questions not present in *verdicts* are treated as None (unjudged).
    Iteration order follows QUESTION_BANK for deterministic output.

    Parameters
    ----------
    verdicts:
        Mapping from question id to verdict (True/False/None).
    explanations:
        Mapping from question id to a human-readable explanation string.
        Missing ids default to an empty string.
    """
    rows: List[_QuestionRow] = []
    for q in QUESTION_BANK:
        v = verdicts.get(q.id, None)
        expl = explanations.get(q.id, "")
        rows.append(
            _QuestionRow(
                id=q.id,
                axis=q.axis,
                kind=q.kind.value,
                polarity=q.polarity.value,
                verdict=v,
                explanation=expl,
            )
        )

    # -- per-axis mean of good-scores --
    per_axis: Dict[str, float] = {}
    for axis in AXES:
        axis_rows = [r for r in rows if r.axis == axis]
        scored = [(r, r.good_score()) for r in axis_rows if r.good_score() is not None]
        if not scored:
            continue  # omit axes with 0 judged questions
        per_axis[axis] = sum(gs for _, gs in scored) / len(scored)

    # -- renormalised overall --
    if not per_axis:
        overall = 0.0
    else:
        raw_weight = sum(_AXIS_WEIGHTS[ax] for ax in per_axis)
        if raw_weight <= 0.0:
            overall = 0.0
        else:
            overall = sum(_AXIS_WEIGHTS[ax] * per_axis[ax] for ax in per_axis) / raw_weight

    # -- coverage counts --
    judged = sum(1 for r in rows if r.verdict is not None)
    det_judged = sum(
        1 for r in rows
        if r.kind == QKind.DETERMINISTIC.value and r.verdict is not None
    )
    unjudged = sum(1 for r in rows if r.verdict is None)

    return QualityScore(
        per_axis={ax: round(v, 4) for ax, v in per_axis.items()},
        overall=round(overall, 4),
        coverage={"judged": judged, "deterministic": det_judged, "unjudged": unjudged},
        _rows=tuple(rows),
    )


# --------------------------------------------------------------------------- #
# grade() — CLI / external-verdicts path
# --------------------------------------------------------------------------- #
def grade(verdicts: Mapping[str, bool]) -> "QualityScore":
    """Build a QualityScore from a bare verdicts mapping (no Snapshot needed).

    This is the CLI ``grade --verdicts`` path: the caller supplies a complete
    ``{question_id: True/False}`` dict (e.g. from a JSON file), and this
    function wraps ``_aggregate`` with empty explanations.

    Questions not present in *verdicts* are treated as unjudged (None).
    """
    # Cast to Optional[bool] to satisfy _aggregate's type signature.
    opt_verdicts: Dict[str, Optional[bool]] = dict(verdicts)
    return _aggregate(opt_verdicts, {})


# --------------------------------------------------------------------------- #
# quality_scorecard() — full pipeline
# --------------------------------------------------------------------------- #
def quality_scorecard(
    snapshot: "Snapshot",
    answer_fn: Callable[["BinaryQuestion", Any], Tuple[Optional[bool], str]],
) -> Dict[str, Any]:
    """Run the full deterministic + LLM-judge pipeline and return a scorecard dict.

    Parameters
    ----------
    snapshot:
        The engine Snapshot to evaluate.
    answer_fn:
        Callable with signature
        ``(question: BinaryQuestion, context: Any) -> (verdict: bool|None, explanation: str)``
        invoked for every JUDGMENT question.  May return ``(None, ...)`` or
        raise — in either case the question is treated as unjudged (graceful
        degradation; never crashes the scorecard run).

    Flow
    ----
    1. Build the judge context once via ``build_context(snapshot)``.
    2. For DETERMINISTIC questions: run ``answer_deterministic(snapshot)``.
    3. For JUDGMENT questions: call ``answer_fn(question, context)``.
       Exceptions from ``answer_fn`` → unjudged (None verdict, empty explanation).
    4. Collect all verdicts + explanations and call ``_aggregate``.
    5. Return ``QualityScore.as_dict()``.
    """
    context = build_context(snapshot)
    det_verdicts = answer_deterministic(snapshot)

    all_verdicts: Dict[str, Optional[bool]] = {}
    all_explanations: Dict[str, str] = {}

    for q in QUESTION_BANK:
        if q.kind is QKind.DETERMINISTIC:
            v = det_verdicts.get(q.id, None)
            all_verdicts[q.id] = v
            all_explanations[q.id] = ""
        else:
            # JUDGMENT question — delegate to the injected judge.
            try:
                result = answer_fn(q, context)
                if result is None or (isinstance(result, tuple) and len(result) == 2 and result[0] is None):
                    v = None
                    expl = result[1] if isinstance(result, tuple) and len(result) == 2 else ""
                elif isinstance(result, tuple) and len(result) == 2:
                    v, expl = result
                    v = bool(v) if v is not None else None
                else:
                    v = None
                    expl = ""
            except Exception:
                v = None
                expl = ""
            all_verdicts[q.id] = v
            all_explanations[q.id] = expl if isinstance(expl, str) else ""

    return _aggregate(all_verdicts, all_explanations).as_dict()
