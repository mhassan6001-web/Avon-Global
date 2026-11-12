"""Provider-independent AI layer.

Business code depends only on :class:`AIProvider`. Content blocks use one
neutral shape (``text``, ``tool_use``, ``tool_result``) that each provider
adapter translates. Keys live in server environment secrets only and are
never logged or returned to clients.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import get_settings
from app.core.errors import ServiceUnavailableError

Block = dict[str, Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ProviderResult:
    content: list[Block]
    stop_reason: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    request_id: str | None = None

    @property
    def tool_calls(self) -> list[Block]:
        return [b for b in self.content if b.get("type") == "tool_use"]

    @property
    def text(self) -> str:
        return "\n".join(b["text"] for b in self.content if b.get("type") == "text").strip()


@dataclass
class ProviderMessage:
    role: str  # "user" | "assistant"
    content: list[Block] = field(default_factory=list)


class AIProviderError(ServiceUnavailableError):
    def __init__(self, message: str = "JARVIS could not reach the AI service. Try again shortly."):
        super().__init__(message)


class AIProvider(Protocol):
    name: str
    model: str

    def complete(
        self,
        system: str,
        messages: list[ProviderMessage],
        tools: list[ToolSpec],
        max_tokens: int,
        model: str | None = None,
    ) -> ProviderResult: ...


class AnthropicProvider:
    """Anthropic Messages API over HTTPS using only the standard library."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float) -> None:
        if not base_url.startswith(("https://", "http://")):
            raise ValueError("ANTHROPIC_BASE_URL must be an http(s) URL")
        self._key = api_key
        self.model = model
        self._url = base_url.rstrip("/") + "/v1/messages"
        self._timeout = timeout

    def complete(
        self,
        system: str,
        messages: list[ProviderMessage],
        tools: list[ToolSpec],
        max_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        body = {
            "model": model or self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "tools": [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ],
        }
        req = urllib.request.Request(  # noqa: S310 - scheme validated in __init__
            self._url,
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": self._key,
                "anthropic-version": "2023-06-01",
            },
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310  # nosec B310
                data = json.loads(resp.read())
                request_id = resp.headers.get("request-id")
        except urllib.error.HTTPError as exc:
            raise AIProviderError(f"The AI service refused the request (HTTP {exc.code}).") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise AIProviderError() from exc
        usage = data.get("usage") or {}
        return ProviderResult(
            content=[b for b in data.get("content", []) if b.get("type") in ("text", "tool_use")],
            stop_reason=str(data.get("stop_reason") or "end_turn"),
            model=str(data.get("model") or model or self.model),
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            latency_ms=int((time.monotonic() - started) * 1000),
            request_id=request_id,
        )


class FakeProvider:
    """Deterministic provider for tests and development without a key.

    It recognises a few phrases and proposes the matching tool, then reports
    tool results verbatim. It never invents business figures.
    """

    name = "fake"
    model = "fake-jarvis"

    RULES: tuple[tuple[str, str], ...] = (
        (r"\bapprovals?\b", "list_pending_approvals"),
        (r"\b(brief|briefing)\b", "daily_briefing"),
        (r"\bmy tasks\b", "list_my_tasks"),
        (r"\btenders?\b", "tenders_due"),
        (r"\b(stock|reorder)\b", "stock_below_reorder"),
        (r"\b(debtors|receivables?|owed)\b", "receivables_ageing"),
    )

    def complete(
        self,
        system: str,
        messages: list[ProviderMessage],
        tools: list[ToolSpec],
        max_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        self._model = model or self.model
        last = messages[-1]
        names = {t.name for t in tools}
        results = [b for b in last.content if b.get("type") == "tool_result"]
        if results:
            parts = [str(r.get("content", ""))[:600] for r in results]
            return self._text("Here is what the system returned:\n" + "\n".join(parts))
        said = " ".join(b.get("text", "") for b in last.content if b.get("type") == "text")
        task = re.match(r"(?i)^\s*(?:create|add) (?:a )?task:?\s*(.+)$", said)
        if task and "prepare_task" in names:
            return self._tool("prepare_task", {"title": task.group(1).strip()[:200]})
        for pattern, tool in self.RULES:
            if re.search(pattern, said, re.IGNORECASE) and tool in names:
                return self._tool(tool, {})
        return self._text(
            "I can answer from the records you are allowed to see. Ask about approvals, "
            "tenders, stock, debtors or your tasks."
        )

    def _text(self, text: str) -> ProviderResult:
        used = getattr(self, "_model", self.model)
        return ProviderResult([{"type": "text", "text": text}], "end_turn", used, 10, 10)

    def _tool(self, name: str, args: dict[str, Any]) -> ProviderResult:
        block = {"type": "tool_use", "id": f"fake_{name}_{time.monotonic_ns()}", "name": name}
        used = getattr(self, "_model", self.model)
        return ProviderResult([{**block, "input": args}], "tool_use", used, 10, 5)


def get_provider() -> AIProvider | None:
    """The configured provider, or ``None`` when JARVIS's AI is not set up."""
    s = get_settings()
    if s.ai_provider == "fake":
        return FakeProvider()
    if s.ai_provider == "anthropic":
        key = s.anthropic_api_key.get_secret_value()
        if not key:
            return None
        return AnthropicProvider(key, s.anthropic_model, s.anthropic_base_url, s.ai_timeout_seconds)
    return None
