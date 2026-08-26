import io
import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from provider import (
    MAX_PROVIDER_ERROR_BYTES,
    MAX_PROVIDER_RESPONSE_BYTES,
    CommandProvider,
    OpenAICompatibleProvider,
    ProviderSecurityError,
    SameOriginRedirectHandler,
    clean_candidate,
    parse_generation,
)


class FakeResponse:
    def __init__(self, body: bytes, headers=None):
        self.body = io.BytesIO(body)
        self.headers = headers or {}

    def read(self, size=-1):
        return self.body.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


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

    def test_candidate_cleaning_does_not_scan_inside_lean_or_prose(self):
        candidate = 'by\n  exact "```lean\\nnot a wrapper\\n```"'
        self.assertEqual(clean_candidate(candidate), candidate)
        prose = "proof follows\n```lean\nby rfl\n```"
        self.assertEqual(clean_candidate(prose), prose)

    def test_http_error_keeps_provider_response_body(self):
        provider = OpenAICompatibleProvider("https://example.test", "secret", "demo", 0.0, 800)
        error = urllib.error.HTTPError(
            provider.url,
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"error":{"message":"invalid model"}}'),
        )
        with patch("provider._safe_urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "invalid model"):
                provider.generate("demo prompt")

    def test_http_error_body_is_bounded_and_reflected_key_is_redacted(self):
        secret = "sk-proj-super-secret-value"
        provider = OpenAICompatibleProvider("https://example.test", secret, "demo", 0.0, 800)

        class TrackingBody(io.BytesIO):
            requested = []

            def read(self, size=-1):
                self.requested.append(size)
                return super().read(size)

        body = TrackingBody(
            json.dumps({"error": {"message": f"invalid key {secret}"}}).encode()
            + b"x" * (MAX_PROVIDER_ERROR_BYTES * 2)
        )
        error = urllib.error.HTTPError(provider.url, 401, "Unauthorized", {}, body)
        with patch("provider._safe_urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as raised:
                provider.generate("demo prompt")
        self.assertNotIn(secret, str(raised.exception))
        self.assertEqual(body.requested, [MAX_PROVIDER_ERROR_BYTES + 1])

    def test_success_response_has_a_hard_size_limit(self):
        provider = OpenAICompatibleProvider("https://example.test", "secret", "demo", 0.0, 800)
        response = FakeResponse(b"x" * (MAX_PROVIDER_RESPONSE_BYTES + 1))
        with patch("provider._safe_urlopen", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "响应超过"):
                provider.generate("demo prompt")

    def test_success_response_cannot_reflect_api_key_into_candidate(self):
        secret = "sk-proj-super-secret-value"
        provider = OpenAICompatibleProvider("https://example.test", secret, "demo", 0.0, 800)
        body = json.dumps({"choices": [{"message": {"content": f"by exact {secret}"}}]}).encode()
        with patch("provider._safe_urlopen", return_value=FakeResponse(body)):
            with self.assertRaisesRegex(ProviderSecurityError, "包含认证密钥"):
                provider.generate("demo prompt")

    def test_redirect_handler_refuses_cross_origin_authorization(self):
        request = urllib.request.Request(
            "https://provider.test/start", headers={"Authorization": "Bearer secret"}
        )
        handler = SameOriginRedirectHandler()
        with self.assertRaisesRegex(ProviderSecurityError, "跨源重定向"):
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://attacker.test/collect"
            )
        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://provider.test/next"
        )
        self.assertEqual(redirected.get_header("Authorization"), "Bearer secret")

    def test_remote_http_and_embedded_credentials_are_rejected(self):
        with self.assertRaises(ProviderSecurityError):
            OpenAICompatibleProvider("http://example.test", "secret", "demo", 0.0, 800)
        with self.assertRaises(ProviderSecurityError):
            OpenAICompatibleProvider("https://user:pass@example.test", "secret", "demo", 0.0, 800)
        OpenAICompatibleProvider("http://127.0.0.1:8000", "secret", "demo", 0.0, 800)

    def test_provider_metadata_separates_model_configuration(self):
        left = OpenAICompatibleProvider("https://example.test", "secret", "model-a", 0.0, 800)
        right = OpenAICompatibleProvider("https://example.test", "secret", "model-b", 0.0, 800)
        self.assertNotEqual(left.metadata(), right.metadata())

    def test_provider_url_rejects_sensitive_query_and_keeps_api_version(self):
        with self.assertRaises(ProviderSecurityError):
            OpenAICompatibleProvider(
                "https://example.test/chat?api_key=secret-value",
                "secret",
                "demo",
                0.0,
                800,
            )
        provider = OpenAICompatibleProvider(
            "https://example.test/chat?api-version=1",
            "secret",
            "demo",
            0.0,
            800,
        )
        metadata = str(provider.metadata())
        self.assertIn("api-version=1", metadata)

    def test_command_metadata_contains_command_configuration(self):
        provider = CommandProvider("python provider.py", timeout=12)
        self.assertEqual(provider.metadata()["command"], "python provider.py")
        self.assertEqual(provider.metadata()["timeout_s"], 12)
