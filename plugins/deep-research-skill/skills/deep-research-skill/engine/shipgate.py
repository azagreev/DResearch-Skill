"""Phase 6 — ship-gate aggregator (H8, hyperresearch reuse: runs.verify_run).

Composes the v1.7.0 verification battery into ONE consolidated GO/NO-GO verdict
over a snapshot — the single "is this shippable?" call. Pure, deterministic,
offline, stdlib-only, READ-ONLY: it inspects the snapshot the way report.py
would ship it, but never mutates state and is not wired into rendering, so it
cannot affect byte-identity.

Verdict: FAIL if any blocking check trips, else WARN if any warning trips, else
PASS. Blocking = own-finding with an unbacked verbatim quote (H1), a shipped
claim citing a retracted source (H3), citation-density below the profile floor,
or an empty report. Warning = untraceable numbers (H6), uncovered
acceptance-criteria/scope (H5). Thresholds come from the scale profile (H7).
Python >= 3.10.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from . import instrcov, numeric, profiles, quoteintegrity, retraction
from .model import ClaimRole, Snapshot
from .policy import Disposition, ReportMode, disposition

_INCLUDED = {Disposition.INCLUDE, Disposition.INCLUDE_WITH_FLAG, Disposition.INCLUDE_AS_CORRECTION}


def _shipped(snapshot: Snapshot, report_mode: ReportMode):
    """Claims that would appear in the report: included by disposition, minus
    own-findings whose verbatim quote is unbacked (H1 gate drops those; a
    correction is never dropped). Mirrors report.render_markdown."""
    disp = {c.id: disposition(c, report_mode) for c in snapshot.claims}
    quote_issues = quoteintegrity.check_snapshot(snapshot)
    shipped = []
    for c in snapshot.claims:
        if disp[c.id] not in _INCLUDED:
            continue
        if c.id in quote_issues and disp[c.id] is not Disposition.INCLUDE_AS_CORRECTION:
            continue
        shipped.append(c)
    return shipped, disp, quote_issues


def check(
    snapshot: Snapshot,
    report_mode: ReportMode = ReportMode.FINDINGS,
    profile: Optional[profiles.Profile] = None,
) -> Dict:
    """Return {verdict, blocking, warnings, checks} for `snapshot`. Deterministic;
    read-only. `profile` supplies thresholds (defaults to profiles.DEFAULT)."""
    prof = profile or profiles.DEFAULT
    shipped, disp, quote_issues = _shipped(snapshot, report_mode)
    findings = [c for c in shipped if disp[c.id] is not Disposition.INCLUDE_AS_CORRECTION]

    checks: Dict[str, Dict] = {}
    blocking: List[str] = []
    warnings: List[str] = []

    by_id = {s.id: s for s in snapshot.sources}
    src_ids = set(by_id)
    shipped_ids = {c.id for c in shipped}

    # 1. quote-integrity — a finding that WOULD ship (included by disposition)
    #    but was dropped by the H1 gate for an unbacked verbatim quote: a real
    #    finding lost to a fabricated quote is worth blocking for human review.
    #    Already-excluded own claims (UNVERIFIED/FALSE-own) never ship, so a bad
    #    quote on one of them is not a lie about the shipped report -> not blocked.
    own_blocked = sorted(
        c.id for c in snapshot.claims
        if c.role is ClaimRole.OWN_FINDING
        and disp[c.id] in _INCLUDED and disp[c.id] is not Disposition.INCLUDE_AS_CORRECTION
        and c.id in quote_issues
    )
    checks["quote_integrity"] = {"blocked": own_blocked, "ok": not own_blocked}
    if own_blocked:
        blocking.append(f"quote-integrity: {len(own_blocked)} shippable finding(s) dropped for an unbacked verbatim quote")

    # 2. retraction — a shipped claim cites a retracted source (blocking). A
    #    retracted source merely LISTED in the bibliography (report.py renders
    #    every source) but cited by nothing shipped is a WARN, not a block.
    retr = sorted(c.id for c in shipped if retraction.retracted_support(c, by_id))
    bib_retracted = sorted(s.id for s in snapshot.sources if retraction.is_retracted(s))
    checks["retraction"] = {"claims": retr, "in_bibliography": bib_retracted, "ok": not retr}
    if retr:
        blocking.append(f"retraction: {len(retr)} shipped claim(s) cite a retracted source")
    elif bib_retracted:
        warnings.append(f"retraction: {len(bib_retracted)} retracted source(s) listed in the bibliography (uncited)")

    # 3. citation-density — fraction of findings whose citation actually renders:
    #    a source id is cited only if it resolves in snapshot.sources (mirrors
    #    report._cites), so a dangling id can't count as 'cited'.
    cited = sum(1 for c in findings if any(sid in src_ids for sid in c.sources))
    density = (cited / len(findings)) if findings else 1.0
    dens_ok = density >= prof.citation_density_min
    checks["citation_density"] = {"density": round(density, 4), "floor": prof.citation_density_min, "ok": dens_ok}
    if not dens_ok:
        blocking.append(f"citation-density {density:.2f} < floor {prof.citation_density_min}")

    # 4. completeness — a report is empty only if NOTHING ships. Corrections
    #    (a debunk of all-FALSE external claims) are substantive shipped content
    #    (report.py '## Refuted / corrections'), so completeness keys on `shipped`.
    checks["completeness"] = {"n_findings": len(findings), "n_shipped": len(shipped), "ok": bool(shipped)}
    if not shipped:
        blocking.append("completeness: report is empty (no shipped findings or corrections)")

    # 5. numeric-consistency over the SHIPPED claims only (WARN).
    num = sorted(cid for cid in numeric.check_snapshot(snapshot) if cid in shipped_ids)
    checks["numeric_consistency"] = {"flagged": num, "ok": not num}
    if num:
        warnings.append(f"numeric-consistency: {len(num)} shipped claim(s) with untraceable numbers")

    # 6. instruction-coverage over the SHIPPED findings only (WARN): a criterion
    #    'covered' solely by an excluded claim is NOT covered by what ships.
    uncovered = instrcov.uncovered_criteria(snapshot, claims=findings)
    checks["instruction_coverage"] = {"uncovered": uncovered, "ok": not uncovered}
    if uncovered:
        warnings.append(f"instruction-coverage: {len(uncovered)} uncovered item(s)")

    verdict = "FAIL" if blocking else ("WARN" if warnings else "PASS")
    return {"verdict": verdict, "blocking": blocking, "warnings": warnings, "checks": checks}
