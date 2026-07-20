"""Phase 10 — DAG executor over SubTask.depends_on (planning & scheduling).

The plan is the dependency graph implied by `SubTask.depends_on`. Each entry
optionally carries an edge KIND via a ":KIND" suffix ("ST-1:STRICT",
"ST-2:SOFT"); a bare "ST-1" means STRICT. This suffix is parsed HERE ONLY —
model.py / _subtask_from keep depends_on as opaque strings.

Edge kinds and how they affect the four operations:
  STRICT   — hard predecessor. Blocks readiness and constrains layering;
             may NOT take part in a cycle.
  SOFT     — ordering hint. Constrains layering (so a soft predecessor lands on
             an earlier level) but does NOT block readiness; may not cycle.
  NONE     — explicit no-edge. Ignored for ordering and readiness entirely.
  FEEDBACK — back-edge that intentionally closes a loop (revision / re-check).
             Ignored for ordering (so layering still terminates) and ALLOWED to
             form a cycle. Its runtime concern (max 3 iterations) lives in the
             executor, not in validation.

Pure, deterministic, stdlib-only. Python >= 3.10.
Frozen signatures (consumed by engine/runtime.py and tests/test_phase10.py):
  EdgeKind, MAX_CONCURRENT, parse_dep, topo_order, ready_set, validate_plan.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Tuple

from . import profiles
from .model import SubTask, SubTaskStatus

# Max sub-tasks that may run concurrently in one parallel level (AC10-5).
# Sourced from the scale profile (H7) so scale knobs live in one
# machine-readable place; the default profile pins the historical value (5).
MAX_CONCURRENT = profiles.DEFAULT.max_concurrent


class EdgeKind(str, Enum):
    """Dependency edge semantics encoded in a depends_on ":KIND" suffix."""
    STRICT = "STRICT"      # hard predecessor: blocks readiness + ordering
    SOFT = "SOFT"          # ordering hint only: constrains layering, not readiness
    NONE = "NONE"          # explicit no-edge: ignored everywhere
    FEEDBACK = "FEEDBACK"  # back-edge: ignored for ordering, allowed to cycle


# Edge kinds that impose a topological ORDERING constraint (drive layering).
_ORDERING_KINDS = frozenset({EdgeKind.STRICT, EdgeKind.SOFT})


def parse_dep(entry: str) -> Tuple[str, EdgeKind]:
    """Parse one depends_on entry into (predecessor_id, EdgeKind).

    "ST-1"          -> ("ST-1", EdgeKind.STRICT)   # bare == STRICT
    "ST-1:STRICT"   -> ("ST-1", EdgeKind.STRICT)
    "ST-2:SOFT"     -> ("ST-2", EdgeKind.SOFT)
    "ST-3:FEEDBACK" -> ("ST-3", EdgeKind.FEEDBACK)

    The id keeps its own embedded hyphens; only the LAST ":" introduces the
    kind suffix. An unknown / empty kind defaults to STRICT (safest: it can
    only ever over-constrain, never silently drop a real edge). Deterministic.
    """
    dep_id, sep, kind_part = entry.rpartition(":")
    if not sep:
        # No ":" present at all -> the whole string is the id, kind is STRICT.
        return entry, EdgeKind.STRICT
    kind_token = kind_part.strip().upper()
    try:
        kind = EdgeKind(kind_token)
    except ValueError:
        # Unrecognised suffix: treat the colon as part of the id is wrong here;
        # the contract reserves ":" for the kind, so fall back to STRICT.
        kind = EdgeKind.STRICT
    return dep_id, kind


def _parsed_deps(subtask: SubTask) -> List[Tuple[str, EdgeKind]]:
    return [parse_dep(d) for d in subtask.depends_on]


def topo_order(subtasks: List[SubTask]) -> List[List[str]]:
    """Kahn-style layering into parallel groups (AC10-4 / AC10-5).

    An edge constrains ordering iff its kind is STRICT or SOFT; NONE and
    FEEDBACK edges are ignored (FEEDBACK back-edges would otherwise make
    layering non-terminating). Each returned inner list is a set of ids with no
    remaining unsatisfied ordering-predecessor — i.e. they may run in parallel —
    split so no level exceeds MAX_CONCURRENT. Within a level ids are sorted
    ascending and, when split, the lexicographically smallest ids stay on the
    earlier sub-level. Fully deterministic.

    Edges to unknown ids and self-loops are ignored for layering (validate_plan
    reports the former); a residual cycle among real ordering edges leaves its
    members OUT of the result (validate_plan reports it).
    """
    ids = [t.id for t in subtasks]
    id_set = set(ids)

    # Build indegree over ORDERING edges only, ignoring unknown ids + self-loops.
    indegree: Dict[str, int] = {i: 0 for i in ids}
    successors: Dict[str, List[str]] = {i: [] for i in ids}
    for task in subtasks:
        seen_pred: set = set()
        for dep_id, kind in _parsed_deps(task):
            if kind not in _ORDERING_KINDS:
                continue
            if dep_id not in id_set or dep_id == task.id:
                continue
            if dep_id in seen_pred:
                continue  # collapse duplicate edges so indegree counts once
            seen_pred.add(dep_id)
            successors[dep_id].append(task.id)
            indegree[task.id] += 1

    levels: List[List[str]] = []
    remaining = dict(indegree)
    placed: set = set()

    while True:
        frontier = sorted(i for i in ids if i not in placed and remaining[i] == 0)
        if not frontier:
            break
        # Split the frontier so no parallel level exceeds MAX_CONCURRENT;
        # smallest ids first keeps the split stable.
        for start in range(0, len(frontier), MAX_CONCURRENT):
            levels.append(frontier[start:start + MAX_CONCURRENT])
        for node in frontier:
            placed.add(node)
        # Decrement successors only after the whole frontier is consumed, so a
        # node never appears on the same level as one of its predecessors.
        for node in frontier:
            for succ in successors[node]:
                if succ not in placed:
                    remaining[succ] -= 1

    return levels


def ready_set(subtasks: List[SubTask]) -> List[str]:
    """PENDING sub-task ids whose every STRICT predecessor is DONE (AC10-4).

    Only STRICT edges gate readiness — SOFT is an ordering hint, NONE/FEEDBACK
    are not gates. A STRICT edge to an unknown id is conservatively treated as
    UNSATISFIED (the predecessor can never be DONE), so such a task is withheld.
    Returns ids sorted ascending. Deterministic.
    """
    status_by_id = {t.id: t.status for t in subtasks}
    ready: List[str] = []
    for task in subtasks:
        if task.status != SubTaskStatus.PENDING:
            continue
        blocked = False
        for dep_id, kind in _parsed_deps(task):
            if kind is not EdgeKind.STRICT:
                continue
            if dep_id == task.id:
                continue  # a self STRICT edge is meaningless; don't deadlock on it
            if status_by_id.get(dep_id) is not SubTaskStatus.DONE:
                blocked = True
                break
        if not blocked:
            ready.append(task.id)
    return sorted(ready)


def validate_plan(subtasks: List[SubTask]) -> List[str]:
    """Structural plan validation (AC10-4). Returns sorted error strings; [] = ok.

    Reports:
      - unknown dependency ids ("subtask ST-X: unknown dependency ST-Y")
      - a cycle formed by NON-FEEDBACK edges ("cycle detected: ST-1 -> ST-2 ...")

    FEEDBACK edges are allowed to close a loop, so they are excluded from cycle
    detection (their 3-iteration cap is a runtime concern, not a validation
    error). NONE edges impose no dependency and are excluded too. Deterministic:
    cycle reported as the lexicographically smallest rotation of one found cycle.
    """
    errors: List[str] = []
    ids = [t.id for t in subtasks]
    id_set = set(ids)

    # 1. Unknown dependency ids (across ALL kinds except NONE, which asserts no
    #    real dependency). Deterministic order: by task id, then dep id.
    for task in sorted(subtasks, key=lambda t: t.id):
        for dep_id, kind in _parsed_deps(task):
            if kind is EdgeKind.NONE:
                continue
            if dep_id not in id_set:
                errors.append(f"subtask {task.id}: unknown dependency {dep_id}")

    # 2. Cycle among non-FEEDBACK, non-NONE edges (over KNOWN ids; unknown ids
    #    are reported above and can't close a real cycle anyway).
    adj: Dict[str, List[str]] = {i: [] for i in ids}
    for task in subtasks:
        for dep_id, kind in _parsed_deps(task):
            if kind in (EdgeKind.FEEDBACK, EdgeKind.NONE):
                continue
            if dep_id in id_set and dep_id != task.id:
                # edge predecessor(dep_id) -> task.id
                adj[dep_id].append(task.id)
    for node in adj:
        adj[node].sort()  # deterministic DFS traversal

    cycle = _find_cycle(ids, adj)
    if cycle:
        errors.append("cycle detected: " + " -> ".join(cycle))

    return sorted(errors)


def _find_cycle(ids: List[str], adj: Dict[str, List[str]]) -> List[str]:
    """Return one cycle as a path [a, b, ..., a] (closed), or [] if acyclic.

    DFS with a recursion stack; nodes and edges are visited in sorted order so
    the discovered cycle is deterministic. The returned cycle is rotated to
    start at its lexicographically smallest member for a stable error message.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {i: WHITE for i in ids}
    parent: Dict[str, str] = {}

    def walk(start: str) -> List[str]:
        # Iterative DFS to avoid recursion limits on large plans.
        stack: List[Tuple[str, int]] = [(start, 0)]
        color[start] = GRAY
        while stack:
            node, idx = stack[-1]
            if idx < len(adj[node]):
                stack[-1] = (node, idx + 1)
                nxt = adj[node][idx]
                if color[nxt] == GRAY:
                    # Back-edge nxt..node closes a cycle; reconstruct it.
                    cyc = [node]
                    cur = node
                    while cur != nxt:
                        cur = parent[cur]
                        cyc.append(cur)
                    cyc.reverse()
                    cyc.append(nxt)  # close the loop
                    return _canonical_cycle(cyc)
                if color[nxt] == WHITE:
                    parent[nxt] = node
                    color[nxt] = GRAY
                    stack.append((nxt, 0))
            else:
                color[node] = BLACK
                stack.pop()
        return []

    for i in sorted(ids):
        if color[i] == WHITE:
            found = walk(i)
            if found:
                return found
    return []


def _canonical_cycle(cycle: List[str]) -> List[str]:
    """Rotate a closed cycle [a,...,a] to start at its smallest node.

    Input has a duplicated closing node; we rotate the open node list and
    re-close so the message is stable regardless of DFS entry point.
    """
    open_nodes = cycle[:-1]  # drop duplicated closing node
    if not open_nodes:
        return cycle
    pivot = min(range(len(open_nodes)), key=lambda k: open_nodes[k])
    rotated = open_nodes[pivot:] + open_nodes[:pivot]
    return rotated + [rotated[0]]
