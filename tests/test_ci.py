import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContinuousIntegrationTest(unittest.TestCase):
    def test_lean_is_installed_before_end_to_end_tests(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertLess(workflow.index("- name: Install Lean"), workflow.index("- name: Run tests"))
