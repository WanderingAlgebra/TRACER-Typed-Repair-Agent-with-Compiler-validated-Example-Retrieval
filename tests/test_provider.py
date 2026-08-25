import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from provider import CommandProvider, OpenAICompatibleProvider, clean_candidate, parse_generation


class ProviderTest(unittest.TestCase):
    def test_command_json_shape(self):
        result = parse_generation('{"candidate":"by rfl","usage":{"total_tokens":4}}', "command")
        self.assertEqual(result.candidate, "by rfl")
        self.assertEqual(result.usage["total_tokens"], 4)

    def test_openai_chat_shape(self):
        result = parse_generation('{"choices":[{"message":{"content":"by rfl"}}]}', "openai_compatible")
        self.assertEqual(result.candidate, "by rfl")

    def test_markdown_lean_fence_is_removed(self):
        self.assertEqual(clean_candidate("```lean\nby\n  rfl\n```"), "by\n  rfl")

    def test_http_error_keeps_provider_response_body(self):
        provider = OpenAICompatibleProvider("https://example.test", "secret", "demo", 0.0, 800)
        error = urllib.error.HTTPError(
            provider.url,
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"error":{"message":"invalid model"}}'),
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "invalid model"):
                provider.generate("demo prompt")

    def test_provider_metadata_separates_model_configuration(self):
        left = OpenAICompatibleProvider("https://example.test", "secret", "model-a", 0.0, 800)
        right = OpenAICompatibleProvider("https://example.test", "secret", "model-b", 0.0, 800)
        self.assertNotEqual(left.metadata(), right.metadata())

    def test_command_metadata_contains_command_configuration(self):
        provider = CommandProvider("python provider.py", timeout=12)
        self.assertEqual(provider.metadata()["command"], "python provider.py")
        self.assertEqual(provider.metadata()["timeout_s"], 12)
