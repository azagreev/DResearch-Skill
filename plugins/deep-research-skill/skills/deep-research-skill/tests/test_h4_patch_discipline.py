"""H4 — patch-never-regenerate discipline (hyperresearch reuse).

Traceability: docs/TRACE_HYPERRESEARCH.md (AC4.1..AC4.4).

DRS orchestrates via the skill (SKILL.md) + Claude Code's native tools; there is
no separate agent-roster file. So the patch-never-regenerate discipline is a
skill-layer contract, ENFORCED here as a structural guard (mirroring the existing
docs<->CLI guards): SKILL.md must document that post-factcheck edits are
tool-locked to [Read, Edit], per-hunk, with escalation (never silent rewrite),
and that an unapplied critical finding blocks ship. The guard fails if the
discipline is ever silently dropped from the prose.

Run from the skill dir:
    python -m unittest tests.test_h4_patch_discipline -v
"""

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"


class H4PatchDisciplineDocumentedTest(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_ac41_section_and_tool_lock_present(self):
        # AC4.1 — the discipline section exists and names the [Read, Edit] tool-lock.
        self.assertIn("Патч, а не регенерация", self.text)
        self.assertIn("[Read, Edit]", self.text)

    def test_ac42_per_hunk_cap_documented(self):
        # AC4.2 — edits are per-hunk / bounded, not whole-report rewrites.
        self.assertRegex(self.text, r"(?i)hunk")

    def test_ac43_escalation_not_silent_rewrite(self):
        # AC4.3 — findings that don't fit escalate (TRIGGER_REVISION), and an
        # unapplied critical blocks ship — never a silent regenerate.
        self.assertIn("TRIGGER_REVISION", self.text)
        self.assertRegex(self.text, r"(?i)(блокирует ship|patch-surgery)")

    def test_guard_is_non_vacuous(self):
        # If the discipline markers vanish, at least one assertion above must break.
        markers = ["Патч, а не регенерация", "[Read, Edit]", "TRIGGER_REVISION"]
        self.assertTrue(all(m in self.text for m in markers))


if __name__ == "__main__":
    unittest.main()
