import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from report import summarize


class ReportMetricTest(unittest.TestCase):
    def test_token_and_topic_summaries_are_present(self):
        import pandas as pd

        frame = pd.DataFrame(
            [
                {
                    "condition": "A",
                    "problem_id": "p1",
                    "round": 1,
                    "compile_ok": True,
                    "compile_elapsed_ms": 10,
                    "retrieved_examples": [],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
                    "diagnostic": {"category": "ok"},
                    "tags": ["logic"],
                    "difficulty": "easy",
                },
                {
                    "condition": "B",
                    "problem_id": "p1",
                    "round": 1,
                    "compile_ok": False,
                    "compile_elapsed_ms": 11,
                    "retrieved_examples": [],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
                    "diagnostic": {"category": "type_mismatch"},
                    "tags": ["logic"],
                    "difficulty": "easy",
                },
                {
                    "condition": "B",
                    "problem_id": "p1",
                    "round": 2,
                    "compile_ok": True,
                    "compile_elapsed_ms": 12,
                    "retrieved_examples": [],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 4, "total_tokens": 11},
                    "diagnostic": {"category": "ok"},
                    "tags": ["logic"],
                    "difficulty": "easy",
                },
            ]
        )
        summary, failures, report = summarize(frame)
        self.assertEqual(summary.loc[summary["condition"] == "B", "avg_total_tokens"].iloc[0], 18.0)
        self.assertEqual(report["by_tag"][0]["tag"], "logic")
        self.assertTrue(failures.empty)


if __name__ == "__main__":
    unittest.main()
