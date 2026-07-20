"""DRACO scoring — turn per-criterion MET/UNMET verdicts into scores.

Implements the exact DRACO scoring formula (dataset card -> "Scoring"):

    raw        = sum(verdict_i * weight_i        for all criteria i)
    positive   = sum(weight_i for weight_i > 0)
    normalized = clamp(raw / positive, 0, 1) * 100

``verdict_i`` is 1 when the judge ruled criterion i MET, else 0. For a
negative-weight criterion a MET verdict means the *error is present*, so it
subtracts from ``raw`` — a system that makes penalised mistakes scores below
what its positive-criteria performance alone would imply.

Two metrics are reported, both clearly labelled (neither dropped):
  * ``normalized``  — the weighted score above (DRACO card's primary metric).
  * ``criteria_pass_rate`` — UNWEIGHTED share of positive criteria MET. The
    Perplexity write-up headlines "pass rate (% of criteria met)", which is a
    different, unweighted metric; we surface it for comparability but treat
    ``normalized`` as primary.

Scores are computed overall AND per axis, so an A/B ablation (skill vs no-skill)
can be read per dimension — the skill is expected to help most on citation
quality and on factual accuracy via suppressing unsupported (negative-weight)
claims, NOT on raw fact retrieval.

Verdicts are a mapping ``{criterion_id: bool}``; a criterion with no verdict is
treated as UNMET and counted in ``n_unjudged`` so silent coverage gaps surface.

stdlib-only, deterministic. Python >= 3.10.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping

from .draco import AXES, Criterion, Rubric, Task


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class _Tally:
    raw: float
    positive_total: float
    n_criteria: int
    n_met: int
    n_negative_met: int
    n_positive: int
    n_positive_met: int
    n_unjudged: int

    @property
    def normalized(self) -> float:
        """Weighted 0..100 score; 0.0 when there are no positive-weight criteria."""
        if self.positive_total <= 0:
            return 0.0
        return _clamp(self.raw / self.positive_total, 0.0, 1.0) * 100.0

    @property
    def criteria_pass_rate(self) -> float:
        """Unweighted 0..100: positive criteria MET / positive criteria."""
        if self.n_positive <= 0:
            return 0.0
        return self.n_positive_met / self.n_positive * 100.0


def _tally(criteria: Iterable[Criterion], verdicts: Mapping[str, bool]) -> _Tally:
    raw = 0.0
    positive_total = 0.0
    n_criteria = n_met = n_negative_met = 0
    n_positive = n_positive_met = n_unjudged = 0
    for c in criteria:
        n_criteria += 1
        if c.id not in verdicts:
            n_unjudged += 1
        met = bool(verdicts.get(c.id, False))
        if c.weight > 0:
            positive_total += c.weight
            n_positive += 1
            if met:
                n_positive_met += 1
        if met:
            n_met += 1
            raw += c.weight
            if c.weight < 0:
                n_negative_met += 1
    return _Tally(
        raw=raw,
        positive_total=positive_total,
        n_criteria=n_criteria,
        n_met=n_met,
        n_negative_met=n_negative_met,
        n_positive=n_positive,
        n_positive_met=n_positive_met,
        n_unjudged=n_unjudged,
    )


@dataclass(frozen=True)
class AxisScore:
    section_id: str
    normalized: float
    criteria_pass_rate: float
    raw: float
    positive_total: float
    n_criteria: int
    n_met: int
    n_negative_met: int  # penalised errors triggered within this axis

    def as_dict(self) -> Dict:
        return {
            "section_id": self.section_id,
            "normalized": round(self.normalized, 2),
            "criteria_pass_rate": round(self.criteria_pass_rate, 2),
            "raw": self.raw,
            "positive_total": self.positive_total,
            "n_criteria": self.n_criteria,
            "n_met": self.n_met,
            "n_negative_met": self.n_negative_met,
        }


@dataclass(frozen=True)
class TaskScore:
    task_id: str
    domain: str
    normalized: float            # overall weighted 0..100
    criteria_pass_rate: float    # overall unweighted 0..100
    raw: float
    positive_total: float
    n_criteria: int
    n_met: int
    n_negative_met: int
    n_unjudged: int
    axes: Dict[str, AxisScore] = field(default_factory=dict)

    def as_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "domain": self.domain,
            "normalized": round(self.normalized, 2),
            "criteria_pass_rate": round(self.criteria_pass_rate, 2),
            "raw": self.raw,
            "positive_total": self.positive_total,
            "n_criteria": self.n_criteria,
            "n_met": self.n_met,
            "n_negative_met": self.n_negative_met,
            "n_unjudged": self.n_unjudged,
            "axes": {sid: a.as_dict() for sid, a in self.axes.items()},
        }


def score_rubric(
    rubric: Rubric,
    verdicts: Mapping[str, bool],
    *,
    task_id: str = "",
    domain: str = "",
) -> TaskScore:
    """Score one rubric against a ``{criterion_id: MET?}`` verdict map.

    Overall metrics use ALL criteria with the global positive-weight total (the
    DRACO card formula is over all i). Per-axis metrics restrict to each section
    and use that section's own positive total — so axes sum independently.
    """
    overall = _tally(rubric.criteria, verdicts)
    axes: Dict[str, AxisScore] = {}
    for section_id, criteria in rubric.by_section().items():
        t = _tally(criteria, verdicts)
        axes[section_id] = AxisScore(
            section_id=section_id,
            normalized=t.normalized,
            criteria_pass_rate=t.criteria_pass_rate,
            raw=t.raw,
            positive_total=t.positive_total,
            n_criteria=t.n_criteria,
            n_met=t.n_met,
            n_negative_met=t.n_negative_met,
        )
    return TaskScore(
        task_id=task_id,
        domain=domain,
        normalized=overall.normalized,
        criteria_pass_rate=overall.criteria_pass_rate,
        raw=overall.raw,
        positive_total=overall.positive_total,
        n_criteria=overall.n_criteria,
        n_met=overall.n_met,
        n_negative_met=overall.n_negative_met,
        n_unjudged=overall.n_unjudged,
        axes=axes,
    )


def score_task(task: Task, verdicts: Mapping[str, bool]) -> TaskScore:
    """Convenience: score a Task (carries id + domain through)."""
    return score_rubric(task.rubric, verdicts, task_id=task.id, domain=task.domain)


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@dataclass(frozen=True)
class Summary:
    """Macro-averaged summary of one arm's TaskScores (mean of per-task scores)."""

    arm: str
    n_tasks: int
    normalized_mean: float
    criteria_pass_rate_mean: float
    total_negative_met: int
    total_unjudged: int
    per_axis: Dict[str, float]      # axis -> mean normalized
    per_domain: Dict[str, float]    # domain -> mean normalized

    def as_dict(self) -> Dict:
        return {
            "arm": self.arm,
            "n_tasks": self.n_tasks,
            "normalized_mean": round(self.normalized_mean, 2),
            "criteria_pass_rate_mean": round(self.criteria_pass_rate_mean, 2),
            "total_negative_met": self.total_negative_met,
            "total_unjudged": self.total_unjudged,
            "per_axis": {k: round(v, 2) for k, v in self.per_axis.items()},
            "per_domain": {k: round(v, 2) for k, v in self.per_domain.items()},
        }


def aggregate(scores: List[TaskScore], *, arm: str = "") -> Summary:
    """Macro-average a list of TaskScores into a Summary.

    Per-axis mean is taken only over tasks that actually contain that axis, so a
    rubric missing an axis does not dilute it toward zero.
    """
    per_axis: Dict[str, float] = {}
    for axis in AXES:
        vals = [s.axes[axis].normalized for s in scores if axis in s.axes]
        if vals:
            per_axis[axis] = _mean(vals)

    per_domain: Dict[str, float] = {}
    domains = sorted({s.domain for s in scores if s.domain})
    for domain in domains:
        vals = [s.normalized for s in scores if s.domain == domain]
        per_domain[domain] = _mean(vals)

    return Summary(
        arm=arm,
        n_tasks=len(scores),
        normalized_mean=_mean([s.normalized for s in scores]),
        criteria_pass_rate_mean=_mean([s.criteria_pass_rate for s in scores]),
        total_negative_met=sum(s.n_negative_met for s in scores),
        total_unjudged=sum(s.n_unjudged for s in scores),
        per_axis=per_axis,
        per_domain=per_domain,
    )


def dual_accuracy(*, met: int, unmet: int, unjudged: int) -> Dict:
    """Honest dual-denominator accuracy (OpenResearcher eval.py's "Judged vs
    Overall" split), reported alongside -- never in place of -- the DRACO
    ``normalized``/``criteria_pass_rate`` formula above.

    This is the UNWEIGHTED criterion MET-rate under two denominators:
      * ``judged_accuracy``  = met / (met + unmet)            -- only over
        criteria a judge actually returned a verdict for.
      * ``overall_accuracy`` = met / (met + unmet + unjudged) -- over every
        criterion, so silent judge failures can't inflate the score.

    The two are equal exactly when ``unjudged == 0`` (nothing to hide);
    divergence is itself the signal that some criteria went unjudged. Both
    denominators default to 0.0 (never raise) when empty.
    """
    judged = met + unmet
    total = met + unmet + unjudged
    judged_accuracy = (met / judged) if judged > 0 else 0.0
    overall_accuracy = (met / total) if total > 0 else 0.0
    return {
        "judged_accuracy": judged_accuracy,
        "overall_accuracy": overall_accuracy,
        "breakdown": {
            "met": met,
            "unmet": unmet,
            "unjudged": unjudged,
            "total": total,
        },
    }


def delta(arm_a: Summary, arm_b: Summary) -> Dict:
    """B - A deltas for the ablation read-out (positive => arm B better).

    Axes/domains present in either arm are reported; a side absent from one arm
    contributes 0 on that side.
    """
    axes = sorted(set(arm_a.per_axis) | set(arm_b.per_axis))
    domains = sorted(set(arm_a.per_domain) | set(arm_b.per_domain))
    return {
        "arm_a": arm_a.arm,
        "arm_b": arm_b.arm,
        "normalized_mean": round(arm_b.normalized_mean - arm_a.normalized_mean, 2),
        "criteria_pass_rate_mean": round(
            arm_b.criteria_pass_rate_mean - arm_a.criteria_pass_rate_mean, 2
        ),
        "total_negative_met": arm_b.total_negative_met - arm_a.total_negative_met,
        "per_axis": {
            ax: round(arm_b.per_axis.get(ax, 0.0) - arm_a.per_axis.get(ax, 0.0), 2)
            for ax in axes
        },
        "per_domain": {
            d: round(arm_b.per_domain.get(d, 0.0) - arm_a.per_domain.get(d, 0.0), 2)
            for d in domains
        },
    }
