"""Robust, deterministic parsing of a judge's raw text response.

Adapted from OpenResearcher eval.py's `parse_judge_response`: extract the
labelled "extracted_final_answer" field BEFORE locating the MET/UNMET verdict,
so a verdict-shaped substring occurring inside the answer body itself can never
be mistaken for the real verdict that follows it. Tolerant of markdown bolding
around either label ('**status:**' as well as bare 'status:').

Pure function, stdlib-only (`re`, `json`), no model/network access — the LLM
call that PRODUCED `raw_text` happens in the agent/workflow layer; this module
only interprets text already returned. On an unparseable response returns
``ok=False`` so the caller (bench.judge.collate.build_verdicts) routes that
criterion into `unjudged` instead of guessing UNMET.

Python >= 3.10.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from .collate import met_from_status

# Markdown-tolerant "extracted_final_answer: <rest of line>" label. Optional
# `**` around the label, `_`/` ` interchangeable in the label word, optional
# run of `*`/whitespace between the colon and the value. The value is
# everything else on that line (case-insensitive, single-line only — `.`
# does not match `\n` by default).
_ANSWER_RE = re.compile(
    r"\*{0,2}\s*extracted[_ ]final[_ ]answer\s*\*{0,2}\s*:\s*[\s*]*(?P<ans>.*)",
    re.IGNORECASE,
)

# Markdown-tolerant "status: MET|UNMET" verdict. Optional `**` around the
# label and around/between the colon and value; any mix of whitespace/`*`
# between the colon and the token.
_VERDICT_RE = re.compile(
    r"\*{0,2}\s*(?:criterion_)?status\s*\*{0,2}\s*:\s*[\s*]*\b(MET|UNMET)\b",
    re.IGNORECASE,
)


def _strip_markdown(text: str) -> str:
    return text.strip().strip("*").strip()


def _try_json_fast_path(raw_text: str) -> Optional[Dict[str, Any]]:
    """If `raw_text` is itself a JSON object carrying a status field, use it
    directly (fast path). Returns None (falls through to regex cascade) for
    anything that is not a clean top-level JSON object."""
    stripped = raw_text.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return None
    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    status = data.get("status") or data.get("criterion_status")
    if status is None or str(status).strip().upper() not in ("MET", "UNMET"):
        return None
    status_norm = str(status).strip().upper()
    answer = data.get("extracted_final_answer")
    return {
        "ok": True,
        "extracted_final_answer": answer if answer is not None else None,
        "status": status_norm,
        "met": met_from_status(status_norm),
    }


def parse_judge_response(raw_text: str) -> Dict[str, Any]:
    """Parse a judge's raw text into ``{ok, extracted_final_answer, status, met}``.

    Step order (AC3.1, extract-before-verdict):
      1. Fast path: a clean top-level JSON object carrying its own status.
      2. Locate the "extracted_final_answer" label; record its match end.
      3. Search for the MET/UNMET verdict ONLY in the text AFTER that offset
         (falls back to the whole text when no answer label was found), so a
         verdict-shaped phrase inside the answer body can't be misread.
      4. Found -> ok=True, status=MET|UNMET, met=bool. Not found -> ok=False,
         status=None, met=None (caller treats the criterion as unjudged).
    """
    fast = _try_json_fast_path(raw_text)
    if fast is not None:
        return fast

    extracted_final_answer: Optional[str] = None
    search_start = 0

    answer_match = _ANSWER_RE.search(raw_text)
    if answer_match:
        extracted_final_answer = _strip_markdown(answer_match.group("ans"))
        search_start = answer_match.end()

    verdict_match = _VERDICT_RE.search(raw_text[search_start:])
    if verdict_match is None:
        return {
            "ok": False,
            "extracted_final_answer": extracted_final_answer,
            "status": None,
            "met": None,
        }

    status = verdict_match.group(1).upper()
    return {
        "ok": True,
        "extracted_final_answer": extracted_final_answer,
        "status": status,
        "met": met_from_status(status),
    }
