"""Deterministic trust / reproducibility metrics over the real engine.

Each metric runs the actual `engine.run_pipeline` + `render_markdown` on a
synthetic, LABELED scenario and measures the rendered artifact — no LLM judge,
no network, fully reproducible. These express the skill's real value props
(determinism, anti-hallucination, auditability) that DRACO does not measure.

A `Scenario` carries claim *specs* (not live Claim objects) so each run rebuilds
fresh claims — `run_pipeline` mutates claims (scores/labels them), so reuse
across runs would corrupt the determinism check.

stdlib-only at this layer. See docs/SKILL_VALUE_AND_SIMPLIFICATION.md §(C).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Tuple

from ._engine import (
    Claim,
    ClaimRole,
    Depth,
    Route,
    TaskFrame,
    engine_eval,
    pipeline,
    report,
    snapshot_from_dict,
    snapshot_to_dict,
)

# A claim spec: (id, text, source_ids, confidence, role)
ClaimSpec = Tuple[str, str, List[str], int, "ClaimRole"]


@dataclass(frozen=True)
class Scenario:
    """A labeled, synthetic input for trust metrics.

    `expect_present` / `expect_absent` are the ground-truth labels: which claim
    ids SHOULD survive into the rendered report (well-supported) vs SHOULD be
    suppressed (unsupported). Detection is by claim text substring in the report,
    so claim texts must be unique sentinels.
    """

    name: str
    now: str
    question: str
    raw_sources: List[Dict[str, Any]]
    claim_specs: List[ClaimSpec]
    expect_present: FrozenSet[str]
    expect_absent: FrozenSet[str]
    route: "Route" = Route.FOCUSED
    depth: "Depth" = Depth.STANDARD

    @property
    def texts(self) -> Dict[str, str]:
        return {cid: text for (cid, text, *_rest) in self.claim_specs}

    def _task_frame(self) -> "TaskFrame":
        return TaskFrame(question=self.question, route=self.route, depth=self.depth)

    def _fresh_claims(self) -> List["Claim"]:
        return [
            Claim(id=cid, text=text, role=role, sources=list(srcs), confidence=conf)
            for (cid, text, srcs, conf, role) in self.claim_specs
        ]

    def run(self):
        """Run the real pipeline once with fresh inputs. Returns (snapshot, report_text)."""
        snapshot, _merges = pipeline.run_pipeline(
            run_id=self.name,
            task_frame=self._task_frame(),
            raw_sources=[dict(s) for s in self.raw_sources],
            claims=self._fresh_claims(),
            now_utc=self.now,
        )
        return snapshot, report.render_markdown(snapshot)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def determinism(scenario: Scenario) -> bool:
    """Reproducibility: two runs on identical inputs render byte-identically.

    Exercises the engine's strict-determinism invariant (now_utc passed in, no
    clock/random). A False here is a serious regression.
    """
    _s1, r1 = scenario.run()
    _s2, r2 = scenario.run()
    return r1 == r2


def suppression_recall(scenario: Scenario) -> float:
    """Anti-hallucination RECALL: share of should-suppress claims absent from
    the report. The engine routes a 0-source claim → UNVERIFIED → excluded."""
    if not scenario.expect_absent:
        return 1.0
    _snap, report_text = scenario.run()
    suppressed = sum(
        1 for cid in scenario.expect_absent if scenario.texts[cid] not in report_text
    )
    return suppressed / len(scenario.expect_absent)


def false_suppression_rate(scenario: Scenario) -> float:
    """Anti-hallucination PRECISION (as an error rate): share of should-present
    (well-supported) claims wrongly dropped. Lower is better; 0.0 ideal."""
    if not scenario.expect_present:
        return 0.0
    _snap, report_text = scenario.run()
    dropped = sum(
        1 for cid in scenario.expect_present if scenario.texts[cid] not in report_text
    )
    return dropped / len(scenario.expect_present)


def citation_completeness(scenario: Scenario) -> Dict[str, float]:
    """Auditability: among findings that actually SURVIVE into the report, the
    share carrying ≥1 citation (target 1.0), plus the share of sources that are
    tier-scored. Measured on the rendered artifact (a suppressed claim doesn't
    count against citation completeness)."""
    snapshot, report_text = scenario.run()
    rendered = [c for c in snapshot.claims if c.text in report_text]
    cited = sum(1 for c in rendered if len(c.sources) >= 1)
    sources_total = len(snapshot.sources)
    tiered = sum(1 for s in snapshot.sources if s.tier is not None)
    return {
        "rendered_findings": float(len(rendered)),
        "claims_cited_fraction": (cited / len(rendered)) if rendered else 1.0,
        "sources_tiered_fraction": (tiered / sources_total) if sources_total else 1.0,
    }


def checkpoint_fidelity(scenario: Scenario) -> bool:
    """Resumability: snapshot → dict → snapshot → dict is idempotent (no field
    lost across a checkpoint round-trip)."""
    snapshot, _ = scenario.run()
    d1 = snapshot_to_dict(snapshot)
    d2 = snapshot_to_dict(snapshot_from_dict(d1))
    return d1 == d2


def cost_efficiency(n_items: int, cost_usd: float, elapsed_sec: float) -> Dict[str, float]:
    """Efficiency passthrough to engine.eval.cost_efficiency (cost_per_item,
    items_per_sec) — the place to wire real per-run $/latency telemetry."""
    return engine_eval.cost_efficiency(n_items, cost_usd, elapsed_sec)


def scorecard(scenario: Scenario) -> Dict[str, Any]:
    """Run every deterministic trust metric on `scenario` and return a report."""
    cit = citation_completeness(scenario)
    return {
        "scenario": scenario.name,
        "determinism": determinism(scenario),
        "suppression_recall": round(suppression_recall(scenario), 4),
        "false_suppression_rate": round(false_suppression_rate(scenario), 4),
        "citation_completeness": {k: round(v, 4) for k, v in cit.items()},
        "checkpoint_fidelity": checkpoint_fidelity(scenario),
    }


# --------------------------------------------------------------------------- #
# Built-in demo scenario
# --------------------------------------------------------------------------- #
def demo_scenario() -> Scenario:
    """A 3-claim fixture: two well-supported (should survive) + one unsupported
    (should be suppressed). Sentinel claim texts for substring detection."""
    return Scenario(
        name="trust-demo",
        now="2026-06-14T00:00:00Z",
        question="Trust metrics demo",
        raw_sources=[
            {"url": "https://www.sec.gov/filing-a", "title": "10-Q", "tier": "S",
             "scores": {"authority": 0.9, "independence": 0.8, "traceability": 0.9, "corroboration": 0.7}},
            {"url": "https://www.reuters.com/b", "title": "News", "tier": "A",
             "scores": {"authority": 0.7, "independence": 0.7, "corroboration": 0.6}},
        ],
        claim_specs=[
            ("C1", "SUPPORTED_FACT_ALPHA", ["S1"], 4, ClaimRole.OWN_FINDING),
            ("C2", "UNSUPPORTED_FACT_BETA", [], 1, ClaimRole.OWN_FINDING),
            ("C3", "SUPPORTED_FACT_GAMMA", ["S2"], 3, ClaimRole.OWN_FINDING),
        ],
        expect_present=frozenset({"C1", "C3"}),
        expect_absent=frozenset({"C2"}),
    )
