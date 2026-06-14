"""Tests for bench.draco — rubric parsing + JSONL loading."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from bench.draco import AXES, DOMAINS, Rubric, load_draco, parse_rubric, task_from_row


# A rubric shaped exactly like a real DRACO `answer` string: a JSON STRING whose
# value decodes to {id, sections:[{id, title, criteria:[{id, weight, requirement}]}]}.
_REAL_SHAPE_RUBRIC = json.dumps(
    {
        "id": "cme-financial-analysis-evaluation",
        "sections": [
            {
                "id": "factual-accuracy",
                "title": "Factual Accuracy",
                "criteria": [
                    {"id": "ocf-q1-2025", "weight": 10, "requirement": "States Q1 2025 OCF as $1,116.6m"},
                    {"id": "hallucinated-figure", "weight": -25, "requirement": "States an unsupported figure"},
                ],
            },
            {
                "id": "citation-quality",
                "title": "Citation Quality",
                "criteria": [
                    {"id": "cites-10q", "weight": 10, "requirement": "Cites the 10-Q primary source"},
                ],
            },
        ],
    }
)


class ParseRubricTest(unittest.TestCase):
    def test_parses_sections_and_weights(self):
        rubric = parse_rubric(_REAL_SHAPE_RUBRIC)
        self.assertIsInstance(rubric, Rubric)
        self.assertEqual(rubric.id, "cme-financial-analysis-evaluation")
        self.assertEqual(len(rubric.criteria), 3)
        # weight is parsed as an int and section_id is threaded onto each criterion
        by_id = {c.id: c for c in rubric.criteria}
        self.assertEqual(by_id["ocf-q1-2025"].weight, 10)
        self.assertIsInstance(by_id["ocf-q1-2025"].weight, int)
        self.assertEqual(by_id["ocf-q1-2025"].section_id, "factual-accuracy")
        self.assertEqual(by_id["hallucinated-figure"].weight, -25)
        self.assertEqual(by_id["cites-10q"].section_id, "citation-quality")

    def test_by_section_groups(self):
        rubric = parse_rubric(_REAL_SHAPE_RUBRIC)
        grouped = rubric.by_section()
        self.assertEqual(set(grouped), {"factual-accuracy", "citation-quality"})
        self.assertEqual(len(grouped["factual-accuracy"]), 2)

    def test_missing_weight_fails_loud(self):
        bad = json.dumps(
            {"id": "x", "sections": [{"id": "factual-accuracy", "criteria": [{"id": "c1"}]}]}
        )
        with self.assertRaises(KeyError):
            parse_rubric(bad)

    def test_axis_and_domain_constants(self):
        # Guard against typos drifting from the dataset card.
        self.assertIn("factual-accuracy", AXES)
        self.assertIn("citation-quality", AXES)
        self.assertEqual(len(AXES), 4)
        self.assertEqual(len(DOMAINS), 10)
        self.assertIn("Needle in a Haystack", DOMAINS)


class LoadDracoTest(unittest.TestCase):
    def test_loads_jsonl_rows(self):
        rows = [
            {"id": "uuid-1", "domain": "Finance", "problem": "Q1", "answer": _REAL_SHAPE_RUBRIC},
            {"id": "uuid-2", "domain": "Law", "problem": "Q2", "answer": _REAL_SHAPE_RUBRIC},
        ]
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row) + "\n")
                handle.write("\n")  # blank line is skipped, not an error
            tasks = load_draco(path)
        finally:
            os.remove(path)

        self.assertEqual([t.id for t in tasks], ["uuid-1", "uuid-2"])
        self.assertEqual(tasks[0].domain, "Finance")
        self.assertEqual(len(tasks[0].rubric.criteria), 3)

    def test_task_from_row(self):
        task = task_from_row(
            {"id": "u", "domain": "Medicine", "problem": "p", "answer": _REAL_SHAPE_RUBRIC}
        )
        self.assertEqual(task.domain, "Medicine")
        self.assertEqual(task.rubric.id, "cme-financial-analysis-evaluation")


if __name__ == "__main__":
    unittest.main()
