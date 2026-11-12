"""Stage 11: the provider layer, without network or database."""

from __future__ import annotations

import io
import json
from typing import Any, ClassVar

import pytest

from app.ai import provider as prov
from app.ai.provider import AnthropicProvider, FakeProvider, ProviderMessage, ToolSpec

TOOLS = [
    ToolSpec("list_pending_approvals", "x", {"type": "object"}),
    ToolSpec("prepare_task", "x", {"type": "object"}),
]


def _ask(text: str) -> list[ProviderMessage]:
    return [ProviderMessage("user", [{"type": "text", "text": text}])]


def test_fake_provider_routes_only_to_offered_tools() -> None:
    fake = FakeProvider()
    r = fake.complete("", _ask("Show my approvals"), TOOLS, 100)
    assert r.tool_calls[0]["name"] == "list_pending_approvals"
    r = fake.complete("", _ask("Create task: Ring the bank"), TOOLS, 100)
    assert r.tool_calls[0]["input"] == {"title": "Ring the bank"}
    # Not offered → no tool call, a plain answer instead.
    r = fake.complete("", _ask("Which tenders close soon?"), TOOLS, 100)
    assert not r.tool_calls and r.text


def test_fake_provider_reports_tool_results_verbatim() -> None:
    msgs = [ProviderMessage("user", [{"type": "tool_result", "tool_use_id": "1", "content": "[]"}])]
    assert FakeProvider().complete("", msgs, TOOLS, 100).text.endswith("[]")


class _Resp(io.BytesIO):
    headers: ClassVar[dict[str, str]] = {"request-id": "req_123"}

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


def test_anthropic_request_shape_and_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float) -> _Resp:
        seen["url"], seen["headers"] = req.full_url, dict(req.header_items())
        seen["body"] = json.loads(req.data)
        payload = {
            "model": "m",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 12, "output_tokens": 3},
            "content": [
                {"type": "text", "text": "Checking."},
                {"type": "tool_use", "id": "t1", "name": "prepare_task", "input": {"title": "A"}},
            ],
        }
        return _Resp(json.dumps(payload).encode())

    monkeypatch.setattr(prov.urllib.request, "urlopen", fake_urlopen)
    p = AnthropicProvider("sk-test", "m", "https://api.example.invalid/", 5)
    r = p.complete("sys", _ask("hi"), TOOLS, 256)
    assert seen["url"] == "https://api.example.invalid/v1/messages"
    assert seen["headers"]["X-api-key"] == "sk-test"
    assert seen["body"]["system"] == "sys" and seen["body"]["max_tokens"] == 256
    assert seen["body"]["tools"][1]["name"] == "prepare_task"
    assert r.text == "Checking." and r.tool_calls[0]["id"] == "t1"
    assert (r.input_tokens, r.output_tokens, r.request_id) == (12, 3, "req_123")


def test_anthropic_errors_become_service_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(req: Any, timeout: float) -> None:
        raise prov.urllib.error.URLError("down")

    monkeypatch.setattr(prov.urllib.request, "urlopen", boom)
    with pytest.raises(prov.AIProviderError) as exc:
        AnthropicProvider("secret-key-value", "m", "https://x.invalid", 1).complete(
            "", _ask("hi"), [], 10
        )
    assert exc.value.status_code == 503
    assert "secret-key-value" not in exc.value.message  # never echo secrets


def test_api_key_is_secret_in_settings() -> None:
    from app.core.config import Settings

    s = Settings.model_validate({"anthropic_api_key": "sk-live-secret"})
    assert "sk-live-secret" not in repr(s) and "sk-live-secret" not in str(s.model_dump())
