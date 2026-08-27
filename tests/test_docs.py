import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationConsistencyTest(unittest.TestCase):
    """防止公开文档与当前 API 和候选处理行为再次脱节。"""

    def readmes(self):
        return {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in ("README.md", "README.zh-CN.md")
        }

    def test_readme_documents_deepseek_and_safe_key_prompt(self):
        confirmations = {
            "README.md": "only its length and last four characters",
            "README.zh-CN.md": "只显示字符数和末四位",
        }
        for name, readme in self.readmes().items():
            with self.subTest(language=name):
                self.assertIn("https://api.deepseek.com/chat/completions", readme)
                self.assertIn("--api-key-prompt", readme)
                self.assertIn(confirmations[name], readme)

    def test_readme_distinguishes_provider_and_compiler_failures(self):
        explanations = {
            "README.md": "compile_ok: false` alone does not mean the API is broken",
            "README.zh-CN.md": "compile_ok: false` 本身不代表 API 损坏",
        }
        for name, readme in self.readmes().items():
            with self.subTest(language=name):
                self.assertIn("provider_error", readme)
                self.assertIn(explanations[name], readme)

    def test_readmes_default_to_english_with_reciprocal_links(self):
        readmes = self.readmes()
        self.assertIn("**English** | [简体中文](README.zh-CN.md)", readmes["README.md"][:200])
        self.assertIn("[English](README.md) | **简体中文**", readmes["README.zh-CN.md"][:200])
        self.assertIn("## Quick start", readmes["README.md"])
        self.assertIn("## 快速开始", readmes["README.zh-CN.md"])
        for name, readme in readmes.items():
            with self.subTest(language=name):
                self.assertIn("](TRACER.png)", readme)
                self.assertEqual(14, len(re.findall(r"^## ", readme, re.MULTILINE)))

    def test_readme_commands_match_between_languages(self):
        # 仅比较执行命令；图中标签、目录注释和报错提示允许翻译。
        commands = []
        for name, readme in self.readmes().items():
            blocks = re.findall(r"^```[^\n]*\n(.*?)^```", readme, re.MULTILINE | re.DOTALL)
            with self.subTest(language=name):
                self.assertEqual(17, len(blocks))
            commands.append([
                line for block in blocks for line in block.splitlines()
                if line.startswith(("python ", "lake ", "git ", "cd ", "$env:", "./scripts/", "bash "))
            ])
        self.assertTrue(commands[0])
        self.assertEqual(commands[0], commands[1])

    def test_readme_pilot_numbers_match_published_summary(self):
        expected = [
            ["18", "18/18(100.0%)", "18/18(100.0%)", "1.000", "1,750.4"],
            ["18", "16/18(88.9%)", "18/18(100.0%)", "1.111", "1,841.9"],
            ["18", "18/18(100.0%)", "18/18(100.0%)", "1.000", "2,906.1"],
        ]
        for name, readme in self.readmes().items():
            rows = []
            for line in readme.splitlines():
                if re.match(r"^\| [ABC][:：]", line):
                    cells = line.strip("|").split("|")[1:]
                    rows.append([
                        cell.replace("（", "(").replace("）", ")").replace(" ", "")
                        for cell in cells
                    ])
            with self.subTest(language=name):
                self.assertEqual(expected, rows)

    def test_readmes_share_evidence_links_and_repository_license(self):
        evidence = []
        for name, readme in self.readmes().items():
            links = set(re.findall(r"\]\((published/[^)]+)\)", readme))
            with self.subTest(language=name):
                self.assertEqual(6, len(links))
                self.assertIn("[MIT License](LICENSE)", readme)
                self.assertIn("MIT License", (ROOT / "LICENSE").read_text(encoding="utf-8"))
            evidence.append(links)
        self.assertEqual(evidence[0], evidence[1])

    def test_methodology_documents_candidate_normalization(self):
        methodology = (ROOT / "docs" / "methodology.md").read_text(encoding="utf-8")
        schema = (ROOT / "docs" / "jsonl_schema.md").read_text(encoding="utf-8")
        self.assertIn("旧 SQLite 缓存", methodology)
        self.assertIn("`provider_error`", schema)


if __name__ == "__main__":
    unittest.main()
