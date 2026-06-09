"""Deep Research Skill — executable engine.

Claim-centric, post-collection research engine. Collection stays with the
host's native web_search (free, Tier-1); this engine processes the RESULTS:
state/checkpoint, dedupe, rank, score, fact-check, cluster, memory, eval, report.

Design & roadmap: docs/REBUILD_PLAN.md.
Constraints: stdlib-only, Python >= 3.10.

Phase 0 (this release): package skeleton + runtime doctor + CLI seam.
Pipeline subcommands are registered stubs that light up phase by phase.
"""

__version__ = "0.5.0"
__all__ = ["__version__"]
