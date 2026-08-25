import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationConsistencyTest(unittest.TestCase):
    """防止公开文档与当前 API 和候选处理行为再次脱节。"""

    def test_readme_documents_deepseek_and_safe_key_prompt(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("https://api.deepseek.com/chat/completions", readme)
        self.assertIn("--api-key-prompt", readme)
        self.assertIn("只显示字符数和末四位", readme)

    def test_readme_distinguishes_provider_and_compiler_failures(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("provider_error", readme)
        self.assertIn("compile_ok: false` 本身不代表 API 损坏", readme)

    def test_methodology_documents_candidate_normalization(self):
        methodology = (ROOT / "docs" / "methodology.md").read_text(encoding="utf-8")
        schema = (ROOT / "docs" / "jsonl_schema.md").read_text(encoding="utf-8")
        self.assertIn("旧 SQLite 缓存", methodology)
        self.assertIn("`provider_error`", schema)


if __name__ == "__main__":
    unittest.main()
