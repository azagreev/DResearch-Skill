"""Phase 1 — core data model (claim-centric). SIGNATURES + CONTRACT, no logic yet.

Defines the run state the engine serializes to a checkpoint and reloads on
resume. Mirrors and EXTENDS the JSON `state` block in AGENT.MD §8.0
(additively — older checkpoints stay loadable). The dataclass/enum SHAPE is
fixed here; serialization / validation LOGIC lands in Phase 1 implementation.

Field-by-field JSON contract: docs/PHASE1_MODEL_STATE.md.
stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
def snapshot_to_dict(snapshot: Snapshot) -> Dict[str, Any]:
    """Serialize a Snapshot to its JSON-ready dict (AGENT.MD §8.0 shape).

    Enums -> their .value; nested dataclasses -> dicts; None scalar fields are
    dropped per the contract in docs/PHASE1_MODEL_STATE.md.
    """
    raise NotImplementedError("Phase 1: snapshot_to_dict")


def snapshot_from_dict(payload: Dict[str, Any]) -> Snapshot:
    """Inverse of snapshot_to_dict, with version check + validation.

    Unknown `checkpoint_version` must raise (never silently load).
    """
    raise NotImplementedError("Phase 1: snapshot_from_dict")


def validate_snapshot(snapshot: Snapshot) -> List[str]:
    """Return a list of contract violations (empty list = valid). Pure, no I/O.

    Checks: id uniqueness (S*/C*/ST*/K*); claim.sources & contradicting_sources
    reference existing Source ids; confidence in 1..5; representative_ids subset
    of claim_ids; cluster_id references an existing cluster; next_phase in 0..6;
    budget fields non-negative.
    """
    raise NotImplementedError("Phase 1: validate_snapshot")
