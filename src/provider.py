"""Model-provider boundary for proof generation."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from dataclasses import dataclass, field


def configured_pricing() -> dict[str, float]:
    return {
        "input_price_per_1k": float(os.environ.get("LEAN_PROOF_INPUT_PRICE_PER_1K", "0")),
        "output_price_per_1k": float(os.environ.get("LEAN_PROOF_OUTPUT_PRICE_PER_1K", "0")),
    }


@dataclass
class Generation:
    candidate: str
    usage: dict[str, int] = field(default_factory=dict)
    provider: str = "unknown"
    raw: dict = field(default_factory=dict)


class Provider:
    name = "provider"

    def generate(self, prompt: str) -> Generation:
        raise NotImplementedError

    def metadata(self) -> dict[str, object]:
        """Non-secret configuration used in logs and exact-request cache keys."""
        return {"provider": self.name, **configured_pricing()}


class CommandProvider(Provider):
    name = "command"

    def __init__(self, command: str, timeout: float = 60.0) -> None:
        if not command.strip():
            raise ValueError("command provider 不能为空")
        self.command = command
        self.timeout = timeout

    def generate(self, prompt: str) -> Generation:
        request = json.dumps({"prompt": prompt}, ensure_ascii=False)
        process = subprocess.run(
            self.command,
            input=request,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=self.timeout,
            shell=True,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(f"provider command 失败: {process.stderr[-1000:]}")
        return parse_generation(process.stdout, self.name)

    def metadata(self) -> dict[str, object]:
        return {"provider": self.name, "command": self.command, "timeout_s": self.timeout, **configured_pricing()}


class OpenAICompatibleProvider(Provider):
    name = "openai_compatible"

    def __init__(self, url: str, api_key: str, model: str, temperature: float, max_tokens: int) -> None:
        self.url = url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, prompt: str) -> Generation:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You repair Lean 4 proofs. Output only a local proof term."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
        return parse_generation(json.dumps(body, ensure_ascii=False), self.name)

    def metadata(self) -> dict[str, object]:
        return {
            "provider": self.name,
            "url": self.url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **configured_pricing(),
        }


class MockProvider(Provider):
    """Test-only provider; production evaluation must use command or API provider."""

    name = "mock"

    def __init__(self, candidate: str) -> None:
        self.candidate = candidate

    def generate(self, prompt: str) -> Generation:
        return Generation(self.candidate, {"prompt_chars": len(prompt)}, self.name)

    def metadata(self) -> dict[str, object]:
        return {"provider": self.name, "test_only": True, **configured_pricing()}


def parse_generation(text: str, provider_name: str) -> Generation:
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        return Generation(text.strip(), {}, provider_name)
    if "candidate" in body:
        return Generation(str(body["candidate"]).strip(), body.get("usage", {}), provider_name, body)
    choices = body.get("choices") or []
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        return Generation(str(content).strip(), body.get("usage", {}), provider_name, body)
    if "output_text" in body:
        return Generation(str(body["output_text"]).strip(), body.get("usage", {}), provider_name, body)
    raise ValueError("provider 输出缺少 candidate/choices/output_text")


def build_provider(name: str, command: str | None = None, mock_candidate: str | None = None) -> Provider:
    if name == "command":
        return CommandProvider(command or os.environ.get("LEAN_PROOF_PROVIDER_COMMAND", ""))
    if name == "openai_compatible":
        url = os.environ.get("LEAN_PROOF_API_URL", "").strip()
        key = os.environ.get("LEAN_PROOF_API_KEY", "").strip()
        model = os.environ.get("LEAN_PROOF_MODEL", "gpt-4.1-mini")
        if not url or not key:
            raise ValueError("openai_compatible 需要 LEAN_PROOF_API_URL 和 LEAN_PROOF_API_KEY")
        return OpenAICompatibleProvider(url, key, model, float(os.environ.get("LEAN_PROOF_TEMPERATURE", "0")), int(os.environ.get("LEAN_PROOF_MAX_TOKENS", "800")))
    if name == "mock":
        if mock_candidate is None:
            raise ValueError("mock provider 需要 --mock-candidate，仅用于测试")
        return MockProvider(mock_candidate)
    raise ValueError(f"未知 provider: {name}")
