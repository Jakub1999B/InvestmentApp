from __future__ import annotations

import json
from typing import Any, Callable

from openai import OpenAI

from .. import settings

ToolHandler = Callable[..., Any]


def make_client(api_key: str | None = None) -> OpenAI:
    key = (api_key or settings.OPENAI_API_KEY or "").strip()
    if not key:
        raise RuntimeError(
            "Missing LLM API key. Add CURSOR_API_KEY / LLM_API_KEY to backend/.env, or paste it in the chat panel."
        )
    if settings.is_cursor_dashboard_key(key) and not settings.OPENAI_BASE_URL:
        raise RuntimeError("Cursor keys are handled by the Cursor SDK path, not OpenAI chat completions.")
    kwargs: dict[str, Any] = {"api_key": key}
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL
    elif key.startswith("sk-or-"):
        kwargs["base_url"] = "https://openrouter.ai/api/v1"
    return OpenAI(**kwargs)


def openai_ready(api_key: str | None = None) -> bool:
    return bool((api_key or settings.OPENAI_API_KEY or "").strip())


def run_tool_loop(
    client: OpenAI,
    *,
    system: str,
    messages: list[dict],
    tools: list[dict],
    handlers: dict[str, ToolHandler],
    model: str | None = None,
    max_rounds: int = 8,
    agent_name: str = "agent",
) -> tuple[str, list[dict]]:
    transcript: list[dict] = [{"role": "system", "content": system}, *messages]
    traces: list[dict] = []
    chosen_model = model or settings.OPENAI_MODEL

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=chosen_model,
            messages=transcript,
            tools=tools or None,
            tool_choice="auto" if tools else None,
            temperature=0.1,
        )
        choice = response.choices[0].message
        payload = choice.model_dump(exclude_none=True)
        transcript.append(payload)
        calls = choice.tool_calls or []
        if not calls:
            return (choice.content or "").strip(), traces
        for call in calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = handlers.get(name)
            if handler is None:
                result: Any = {"error": f"Unknown tool {name}"}
            else:
                try:
                    result = handler(**args)
                except TypeError as exc:
                    result = {"error": f"Bad arguments for {name}: {exc}"}
                except Exception as exc:  # noqa: BLE001 — surface tool failures to the model
                    result = {"error": str(exc)}
            traces.append({"agent": agent_name, "tool": name, "args": args, "ok": "error" not in result if isinstance(result, dict) else True})
            transcript.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, default=str, ensure_ascii=False),
                }
            )
    return "I hit the tool-call limit before finishing. Ask me to continue.", traces


def tool_schema(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }
