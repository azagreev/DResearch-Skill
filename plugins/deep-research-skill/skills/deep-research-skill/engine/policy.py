"""Phase 6 — report disposition policy. SIGNATURE + CONTRACT, no logic yet.

What happens to a claim in the final report is NOT a static property of its
fact-check category. It depends on:
  - the claim's ROLE (model.ClaimRole): own finding vs external claim under review
  - the report MODE: findings report vs debunk vs mixed

This replaces the old static `REPORTABLE_CATEGORIES` frozenset, which wrongly
treated FALSE as a blanket exclusion. A FALSE *external* claim is the entire
point of a debunk; a FALSE *own finding* must loop back for revision, not be
silently dropped.

Disposition table (the contract `disposition()` implements in Phase 6):

  category    | role            | -> disposition
  ------------|-----------------|---------------------------------------------
  VERIFIED    | any             | INCLUDE
  OUTDATED    | any             | INCLUDE_WITH_FLAG   (note the current state)
  INCOMPLETE  | any             | INCLUDE_WITH_FLAG   (add missing context)
  OPINION     | any             | INCLUDE_WITH_FLAG   (frame as "one view")
  UNVERIFIED  | any             | INCLUDE_WITH_FLAG   ("could not verify"); may be
              |                 |   EXCLUDE_BUT_RECORD in FINDINGS mode if low-value
  FALSE       | EXTERNAL_CLAIM  | INCLUDE_AS_CORRECTION  (the debunk IS the value)
  FALSE       | OWN_FINDING     | TRIGGER_REVISION; if revision exhausted ->
              |                 |   EXCLUDE_BUT_RECORD (never publish own falsehood)

`report_mode` shifts the borderline calls (e.g. DEBUNK biases UNVERIFIED toward
INCLUDE_WITH_FLAG for transparency; FINDINGS may EXCLUDE_BUT_RECORD it). It does
NOT override the FALSE/role branch above.

EXCLUDE_BUT_RECORD always writes to cross-run memory (Phase 5) so the same
claim is not silently re-derived on a later run.

stdlib-only. Python >= 3.10.
"""

from __future__ import annotations

from enum import Enum

from .model import Claim, ClaimCategory, ClaimRole


class ReportMode(str, Enum):
    FINDINGS = "findings"  # standard research report (assert what's true)
    DEBUNK = "debunk"      # the question itself is about a claim's truth
    MIXED = "mixed"        # both


class Disposition(str, Enum):
    INCLUDE = "include"
    INCLUDE_WITH_FLAG = "include_with_flag"
    INCLUDE_AS_CORRECTION = "include_as_correction"
    EXCLUDE_BUT_RECORD = "exclude_but_record"   # dropped from report, kept in memory
    TRIGGER_REVISION = "trigger_revision"       # feedback loop: agent must revise


def disposition(claim: Claim, report_mode: ReportMode) -> Disposition:
    """Decide what to do with `claim` in a report of `report_mode`.

    Pure, deterministic; implements the table in this module's docstring.
    `report_mode` is decided upstream (Phase 0 intent), not stored on the claim.
    """
    category = claim.category

    if category is ClaimCategory.VERIFIED:
        return Disposition.INCLUDE

    if category in (ClaimCategory.OUTDATED, ClaimCategory.INCOMPLETE, ClaimCategory.OPINION):
        return Disposition.INCLUDE_WITH_FLAG

    if category is ClaimCategory.UNVERIFIED:
        # FINDINGS asserts what's true; an unverifiable claim is not a finding —
        # keep it out of the report but record it (memory). Otherwise flag it.
        if report_mode is ReportMode.FINDINGS:
            return Disposition.EXCLUDE_BUT_RECORD
        return Disposition.INCLUDE_WITH_FLAG

    # FALSE — branches on role.
    if claim.role is ClaimRole.EXTERNAL_CLAIM:
        return Disposition.INCLUDE_AS_CORRECTION  # the debunk IS the value
    return Disposition.TRIGGER_REVISION           # never publish our own falsehood
