import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from api_server import _response_payload, make_handler
from provider import build_provider


class ApiInterfaceTest(unittest.TestCase):
    def test_direct_provider_configuration_is_not_secret_metadata(self):
        provider = build_provider(
            "openai_compatible",
            api_url="https://example.test/v1/chat/completions",
            api_key="secret-value",
            model="demo-model",
        )
        self.assertEqual(provider.metadata()["model"], "demo-model")
        self.assertNotIn("secret-value", str(provider.metadata()))

    def test_http_response_does_not_echo_api_key_or_candidate_config(self):
        payload = _response_payload({"compile_ok": False, "provider": "openai_compatible", "diagnostic": {"category": "provider_error"}, "usage": {}})
        self.assertNotIn("api_key", str(payload).lower())
        self.assertNotIn("secret", str(payload).lower())

    def test_http_access_log_redacts_key_in_malformed_url(self):
        handler = object.__new__(make_handler())
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            handler.log_message('%s', 'POST /solve?api_key=secret-value HTTP/1.1')
        self.assertNotIn("secret-value", output.getvalue())
