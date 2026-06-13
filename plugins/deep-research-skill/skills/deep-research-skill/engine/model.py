"""Phase 1 — core data model (claim-centric). SIGNATURES + CONTRACT, no logic yet.

Defines the run state the engine serializes to a checkpoint and reloads on
resume. Mirrors and EXTENDS the JSON `state` block in AGENT.MD §8.0
(additively — older checkpoints stay loadable). The dataclass/enum SHAPE is
fixed here; serialization / validation LOGIC lands in Phase 1 implementation.

Field-by-field JSON contract: docs/PHASE1_MODEL_STATE.md.
stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

CHECKPOINT_VERSION = "1.0"


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class Route(str, Enum):
    WIDE = "A"            # Wide / exploratory
    FOCUSED = "B"         # Focused / specific
    FILE_ONLY = "C"       # File-only
    FILE_AUGMENTED = "D"  # File + web


class Depth(str, Enum):
    QUICK = "Quick"
    STANDARD = "Standard"
    DEEP = "Deep"
    EXHAUSTIVE = "Exhaustive"


class Tier(str, Enum):
    """Source authority tier (references/source_authority_framework.md)."""
    S = "S"  # primary / regulators — ground truth
    A = "A"  # authoritative media / peer-reviewed
    B = "B"  # industry reports / established blogs
    C = "C"  # aggregators / press releases
    D = "D"  # forums / social — verify first


class SubTaskType(str, Enum):
    SEARCH = "SEARCH"
    EXTRACT = "EXTRACT"
    ANALYZE = "ANALYZE"
    COMPARE = "COMPARE"
    SYNTHESIZE = "SYNTHESIZE"
    VALIDATE = "VALIDATE"
    FORMAT = "FORMAT"
    META = "META"


class SubTaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class SourceStatus(str, Enum):
    PENDING = "pending"
    RENDERED = "rendered"
    FAILED = "failed"


class DateConfidence(str, Enum):
    HIGH = "high"
    MED = "med"
    LOW = "low"


class TrustLevel(str, Enum):
    """Whether a source's content may be treated as authoritative instructions.

    Retrieved web content is UNTRUSTED by default: it is evidence to be
    evaluated, never policy to be followed. Any instructions embedded inside it
    (prompt injection) are data, not commands. Only sources explicitly marked
    trusted (e.g. internal data_sources) are TRUSTED.
    """
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class ClaimCategory(str, Enum):
    """The 6 fact-check categories (references/factcheck_system.md §4.1).

    Member NAMES are uppercase for readability; serialized VALUES are lowercase
    to match the AGENT.MD §8.0 checkpoint example (`"category": "verified"`), so
    older §8.0 checkpoints load without aliasing. Label + emoji: CATEGORY_LABELS.
    """
    VERIFIED = "verified"      # ВЕРНО
    FALSE = "false"            # НЕВЕРНО
    OUTDATED = "outdated"      # УСТАРЕЛО
    INCOMPLETE = "incomplete"  # НЕПОЛНО
    OPINION = "opinion"        # ОДНА ИЗ ТОЧЕК ЗРЕНИЯ
    UNVERIFIED = "unverified"  # НЕ УДАЛОСЬ ПРОВЕРИТЬ


# machine key -> (Russian label, emoji)
CATEGORY_LABELS: Dict["ClaimCategory", Tuple[str, str]] = {
    ClaimCategory.VERIFIED:   ("ВЕРНО", "✅"),
    ClaimCategory.FALSE:      ("НЕВЕРНО", "❌"),
    ClaimCategory.OUTDATED:   ("УСТАРЕЛО", "⏰"),
    ClaimCategory.INCOMPLETE: ("НЕПОЛНО", "⚠️"),
    ClaimCategory.OPINION:    ("ОДНА ИЗ ТОЧЕК ЗРЕНИЯ", "🔮"),
    ClaimCategory.UNVERIFIED: ("НЕ УДАЛОСЬ ПРОВЕРИТЬ", "❓"),
}

# NOTE: reportability is NOT a static property of a category. Whether a claim
# enters the report depends on the claim's ROLE (own finding vs external claim
# under review) and the report mode — e.g. a FALSE *external* claim is the whole
# point of a debunk, while a FALSE *own finding* must trigger revision. That
# role-aware policy lives in engine/policy.py (Phase 6), not here. See
# docs/PHASE1_MODEL_STATE.md §"Reportability".


class ClaimStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ClaimRole(str, Enum):
    """Whose claim is this — decides how a FALSE verdict is handled."""
    OWN_FINDING = "own_finding"        # the research itself asserts it (synthesized)
    EXTERNAL_CLAIM = "external_claim"  # a third-party claim under adjudication


class GateVerdict(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


# --------------------------------------------------------------------------- #
# Data records
# --------------------------------------------------------------------------- #
@dataclass
class Budget:
    limit_usd: float = 0.0
    spent_usd: float = 0.0
    loads_used: int = 0
    loads_cap: int = 0


@dataclass
class TaskFrame:
    question: str
    route: Route
    depth: Depth
    scope: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    language: str = "ru"  # output language; the skill adapts to the user


@dataclass
class GateResult:
    id: str
    verdict: GateVerdict


@dataclass
class SubTask:
    id: str
    type: SubTaskType
    status: SubTaskStatus = SubTaskStatus.PENDING
    depends_on: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ScoreComponents:
    """Inputs to the authority composite (source_authority_framework.md).

    composite = Authority*0.30 + Recency*0.25 + Independence*0.20
              + Traceability*0.15 + Corroboration*0.10
    All values in [0, 1]; None = not yet scored (filled by score.py in Phase 3).
    """
    authority: Optional[float] = None
    recency: Optional[float] = None
    independence: Optional[float] = None
    traceability: Optional[float] = None
    corroboration: Optional[float] = None
    composite: Optional[float] = None


@dataclass
class Source:
    id: str                         # "S1"
    url: str
    title: str = ""
    tier: Optional[Tier] = None
    fetched_via: str = ""           # native_web_search | jina | firecrawl | ...
    status: SourceStatus = SourceStatus.PENDING
    created_utc: str = ""           # ISO; when collected (drives staleness)
    raw_path: Optional[str] = None  # raw/S1.txt — full payload kept off-context
    extract: Dict[str, Any] = field(default_factory=dict)  # grepped slice in-context
    trust: TrustLevel = TrustLevel.UNTRUSTED  # retrieved web content is data, not instructions
    published_at: Optional[str] = None
    date_confidence: DateConfidence = DateConfidence.LOW
    time_sensitive: bool = False    # drives staleness re-verify on resume
    scores: ScoreComponents = field(default_factory=ScoreComponents)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Claim:
    id: str                         # "C1"
    text: str
    role: ClaimRole = ClaimRole.OWN_FINDING
    category: ClaimCategory = ClaimCategory.UNVERIFIED
    confidence: int = 1             # 1..5
    sources: List[str] = field(default_factory=list)                # supporting Source ids
    contradicting_sources: List[str] = field(default_factory=list)  # contradicting Source ids
    status: ClaimStatus = ClaimStatus.PENDING
    cluster_id: Optional[str] = None
    verdict_explanation: Optional[str] = None
    remediation: Optional[str] = None  # machine-readable "Violation: … Fix: …" when self-healable


@dataclass
class EvidenceCluster:
    id: str                         # "K1"
    title: str
    claim_ids: List[str] = field(default_factory=list)
    representative_ids: List[str] = field(default_factory=list)  # subset of claim_ids
    uncertainty: Optional[str] = None  # "single-source" | "thin-evidence" | None


@dataclass
class Snapshot:
    """Resumable run state. Serialized form == AGENT.MD §8.0 `state` block."""
    run_id: str
    task_fingerprint: str
    task_frame: TaskFrame
    created_utc: str = ""
    checkpoint_version: str = CHECKPOINT_VERSION
    stage: str = ""                 # "cp_01_raw"
    phase_completed: int = 0
    next_phase: int = 0
    sources_screened: int = 0           # gate signal: # sources past Tier/freshness screen
    extraction_table_complete: bool = False  # gate signal: all sources extracted
    citations_verified: bool = False    # gate signal: every claim has a checked source
    last_gate: Optional[GateResult] = None
    budget: Budget = field(default_factory=Budget)
    subtasks: List[SubTask] = field(default_factory=list)
    sources: List[Source] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    clusters: List[EvidenceCluster] = field(default_factory=list)
    open_items: List[str] = field(default_factory=list)
    resume_instruction: str = ""


# --------------------------------------------------------------------------- #
# Serialization / validation — SIGNATURES ONLY (Phase 1 implementation)
# --------------------------------------------------------------------------- #
def _jsonable(value: Any) -> Any:
    """Recursively convert dataclasses/enums to JSON-native types.

    Dataclass FIELDS that are None are dropped (the §8.0 shape omits them);
    enums become their .value; lists/dicts recurse. Arbitrary dict contents
    (extract/metadata/engagement) are passed through opaquely, including None.
    """
    if is_dataclass(value) and not isinstance(value, type):
        out: Dict[str, Any] = {}
        for f in fields(value):
            v = getattr(value, f.name)
            if v is None:
                continue
            out[f.name] = _jsonable(v)
        return out
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def snapshot_to_dict(snapshot: Snapshot) -> Dict[str, Any]:
    """Serialize a Snapshot to its JSON-ready dict (AGENT.MD §8.0 shape).

    Enums -> their .value; nested dataclasses -> dicts; None scalar fields are
    dropped per the contract in docs/PHASE1_MODEL_STATE.md.
    """
    return _jsonable(snapshot)


def _budget_from(d: Dict[str, Any]) -> Budget:
    return Budget(
        limit_usd=float(d.get("limit_usd", 0.0)),
        spent_usd=float(d.get("spent_usd", 0.0)),
        loads_used=int(d.get("loads_used", 0)),
        loads_cap=int(d.get("loads_cap", 0)),
    )


def _task_frame_from(d: Dict[str, Any]) -> TaskFrame:
    return TaskFrame(
        question=d["question"],
        route=Route(d["route"]),
        depth=Depth(d["depth"]),
        scope=list(d.get("scope", [])),
        acceptance_criteria=list(d.get("acceptance_criteria", [])),
        language=d.get("language", "ru"),
    )


def _gate_from(d: Dict[str, Any]) -> GateResult:
    return GateResult(id=d["id"], verdict=GateVerdict(d["verdict"]))


def _subtask_from(d: Dict[str, Any]) -> SubTask:
    return SubTask(
        id=d["id"],
        type=SubTaskType(d["type"]),
        status=SubTaskStatus(d.get("status", "pending")),
        depends_on=list(d.get("depends_on", [])),
        description=d.get("description", ""),
    )


def _scores_from(d: Dict[str, Any]) -> ScoreComponents:
    return ScoreComponents(
        authority=d.get("authority"),
        recency=d.get("recency"),
        independence=d.get("independence"),
        traceability=d.get("traceability"),
        corroboration=d.get("corroboration"),
        composite=d.get("composite"),
    )


def _source_from(d: Dict[str, Any]) -> Source:
    return Source(
        id=d["id"],
        url=d["url"],
        title=d.get("title", ""),
        tier=Tier(d["tier"]) if d.get("tier") is not None else None,
        fetched_via=d.get("fetched_via", ""),
        status=SourceStatus(d.get("status", "pending")),
        created_utc=d.get("created_utc", ""),
        raw_path=d.get("raw_path"),
        extract=dict(d.get("extract", {})),
        trust=TrustLevel(d.get("trust", "untrusted")),
        published_at=d.get("published_at"),
        date_confidence=DateConfidence(d.get("date_confidence", "low")),
        time_sensitive=bool(d.get("time_sensitive", False)),
        scores=_scores_from(d.get("scores", {})),
        metadata=dict(d.get("metadata", {})),
    )


def _claim_from(d: Dict[str, Any]) -> Claim:
    return Claim(
        id=d["id"],
        text=d["text"],
        role=ClaimRole(d.get("role", "own_finding")),
        category=ClaimCategory(d.get("category", "unverified")),
        confidence=int(d.get("confidence", 1)),
        sources=list(d.get("sources", [])),
        contradicting_sources=list(d.get("contradicting_sources", [])),
        status=ClaimStatus(d.get("status", "pending")),
        cluster_id=d.get("cluster_id"),
        verdict_explanation=d.get("verdict_explanation"),
        remediation=d.get("remediation"),
    )


def _cluster_from(d: Dict[str, Any]) -> EvidenceCluster:
    return EvidenceCluster(
        id=d["id"],
        title=d.get("title", ""),
        claim_ids=list(d.get("claim_ids", [])),
        representative_ids=list(d.get("representative_ids", [])),
        uncertainty=d.get("uncertainty"),
    )


def snapshot_from_dict(payload: Dict[str, Any]) -> Snapshot:
    """Inverse of snapshot_to_dict, with version check.

    Unknown `checkpoint_version` raises (never silently load). Missing optional
    keys fall back to dataclass defaults, so a value dropped by snapshot_to_dict
    round-trips back to its default (None / "" / []).
    """
    version = payload.get("checkpoint_version", CHECKPOINT_VERSION)
    if version != CHECKPOINT_VERSION:
        raise ValueError(f"Unsupported checkpoint_version: {version!r}")
    gate = payload.get("last_gate")
    return Snapshot(
        run_id=payload["run_id"],
        task_fingerprint=payload["task_fingerprint"],
        task_frame=_task_frame_from(payload["task_frame"]),
        created_utc=payload.get("created_utc", ""),
        checkpoint_version=version,
        stage=payload.get("stage", ""),
        phase_completed=int(payload.get("phase_completed", 0)),
        next_phase=int(payload.get("next_phase", 0)),
        sources_screened=int(payload.get("sources_screened", 0)),
        extraction_table_complete=bool(payload.get("extraction_table_complete", False)),
        citations_verified=bool(payload.get("citations_verified", False)),
        last_gate=_gate_from(gate) if gate else None,
        budget=_budget_from(payload.get("budget", {})),
        subtasks=[_subtask_from(x) for x in payload.get("subtasks", [])],
        sources=[_source_from(x) for x in payload.get("sources", [])],
        claims=[_claim_from(x) for x in payload.get("claims", [])],
        clusters=[_cluster_from(x) for x in payload.get("clusters", [])],
        open_items=list(payload.get("open_items", [])),
        resume_instruction=payload.get("resume_instruction", ""),
    )


def validate_snapshot(snapshot: Snapshot) -> List[str]:
    """Return a list of contract violations (empty list = valid). Pure, no I/O.

    Checks: id uniqueness (S*/C*/ST*/K*); claim.sources & contradicting_sources
    reference existing Source ids; confidence in 1..5; representative_ids subset
    of claim_ids; cluster_id references an existing cluster; next_phase in 0..6;
    budget fields non-negative.
    """
    errors: List[str] = []

    def _dups(ids: List[str]) -> List[str]:
        seen: set = set()
        dup: set = set()
        for i in ids:
            if i in seen:
                dup.add(i)
            seen.add(i)
        return sorted(dup)

    source_ids = [s.id for s in snapshot.sources]
    claim_ids = [c.id for c in snapshot.claims]
    subtask_ids = [t.id for t in snapshot.subtasks]
    cluster_ids = [k.id for k in snapshot.clusters]

    for kind, ids in (
        ("source", source_ids),
        ("claim", claim_ids),
        ("subtask", subtask_ids),
        ("cluster", cluster_ids),
    ):
        for d in _dups(ids):
            errors.append(f"duplicate {kind} id: {d}")

    source_set = set(source_ids)
    claim_set = set(claim_ids)
    cluster_set = set(cluster_ids)

    for c in snapshot.claims:
        if not (1 <= c.confidence <= 5):
            errors.append(f"claim {c.id}: confidence {c.confidence} out of 1..5")
        for sid in c.sources:
            if sid not in source_set:
                errors.append(f"claim {c.id}: unknown source {sid}")
        for sid in c.contradicting_sources:
            if sid not in source_set:
                errors.append(f"claim {c.id}: unknown contradicting source {sid}")
        if c.cluster_id is not None and c.cluster_id not in cluster_set:
            errors.append(f"claim {c.id}: unknown cluster_id {c.cluster_id}")

    for k in snapshot.clusters:
        member_set = set(k.claim_ids)
        for cid in k.claim_ids:
            if cid not in claim_set:
                errors.append(f"cluster {k.id}: unknown claim {cid}")
        for rid in k.representative_ids:
            if rid not in member_set:
                errors.append(f"cluster {k.id}: representative {rid} not in claim_ids")

    if not (0 <= snapshot.next_phase <= 6):
        errors.append(f"next_phase {snapshot.next_phase} out of 0..6")

    # Structural DAG check: every depends_on edge must reference a known subtask.
    # depends_on entries may carry a typed-edge suffix ("ST-1:STRICT") parsed by
    # engine/plan.py; here we only isolate the id part (everything before the
    # last ':') — cycle detection / scheduling policy lives in plan.py, not here.
    subtask_set = set(subtask_ids)
    for t in snapshot.subtasks:
        for dep in t.depends_on:
            dep_id = dep.rsplit(":", 1)[0]
            if dep_id not in subtask_set:
                errors.append(f"subtask {t.id}: unknown dependency {dep_id}")

    for name in ("limit_usd", "spent_usd", "loads_used", "loads_cap"):
        if getattr(snapshot.budget, name) < 0:
            errors.append(f"budget.{name} negative")

    return errors
