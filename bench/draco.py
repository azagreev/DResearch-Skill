"""DRACO dataset loading + rubric parsing.

Loads the perplexity-ai/draco ``test.jsonl`` (100 tasks, one JSON object per
line) and parses each task's JSON-encoded rubric (``answer`` field) into typed
structures the scorer (bench.score) can grade against.

Each task row has: ``id`` (uuid), ``domain`` (one of 10), ``problem`` (the
research query), ``answer`` (a JSON STRING that decodes to the rubric). The
rubric decodes to ``{id, sections:[{id, title, criteria:[{id, weight,
requirement}]}]}`` where ``weight`` is an int — positive rewards a desirable
property, negative penalises an error (a MET verdict on a negative criterion
means the error is PRESENT).

stdlib-only, deterministic. Python >= 3.10.
Reference: https://huggingface.co/datasets/perplexity-ai/draco
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

# The four DRACO evaluation axes (rubric section ids), in canonical report order.
AXES = (
    "factual-accuracy",
    "breadth-and-depth-of-analysis",
    "presentation-quality",
    "citation-quality",
)

# The ten task domains, for stratified sampling / per-domain reporting.
DOMAINS = (
    "Finance",
    "Shopping/Product Comparison",
    "Academic",
    "Technology",
    "General Knowledge",
    "UX Design",
    "Law",
    "Medicine",
    "Needle in a Haystack",
    "Personalized Assistant",
)


@dataclass(frozen=True)
class Criterion:
    """One rubric line. ``weight`` > 0 rewards; ``weight`` < 0 penalises (a MET
    verdict means the error described by ``requirement`` is present)."""

    id: str
    weight: int
    requirement: str
    section_id: str  # which axis this criterion belongs to


@dataclass(frozen=True)
class Rubric:
    id: str
    criteria: List[Criterion]

    def by_section(self) -> Dict[str, List[Criterion]]:
        """Group criteria by axis (section id), preserving order."""
        out: Dict[str, List[Criterion]] = {}
        for criterion in self.criteria:
            out.setdefault(criterion.section_id, []).append(criterion)
        return out


@dataclass(frozen=True)
class Task:
    id: str
    domain: str
    problem: str
    rubric: Rubric


def parse_rubric(answer: str) -> Rubric:
    """Parse a task's ``answer`` field (a JSON-encoded rubric string) into a Rubric.

    Strict on the criterion ``weight`` (KeyError if absent) so malformed rubrics
    fail loudly rather than silently scoring a criterion as weight 0.
    """
    data = json.loads(answer)
    criteria: List[Criterion] = []
    for section in data.get("sections", []):
        section_id = section.get("id", "")
        for raw in section.get("criteria", []):
            criteria.append(
                Criterion(
                    id=raw["id"],
                    weight=int(raw["weight"]),
                    requirement=raw.get("requirement", ""),
                    section_id=section_id,
                )
            )
    return Rubric(id=data.get("id", ""), criteria=criteria)


def task_from_row(row: Dict) -> Task:
    """Build a Task from one decoded JSONL row."""
    return Task(
        id=row["id"],
        domain=row.get("domain", ""),
        problem=row.get("problem", ""),
        rubric=parse_rubric(row["answer"]),
    )


def load_draco(path: str) -> List[Task]:
    """Load DRACO ``test.jsonl`` (one task per line) into typed Task objects."""
    tasks: List[Task] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            tasks.append(task_from_row(json.loads(line)))
    return tasks
