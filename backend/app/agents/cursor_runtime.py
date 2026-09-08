from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .fx_agent import FX_SYSTEM, FX_TOOLS, fx_handlers
from .session import get_workspace
from .tax_agent import TAX_SYSTEM, TAX_TOOLS, tax_handlers
from .. import settings

ROOT = Path(__file__).resolve().parents[2]


def _custom_tools(openai_tools: list[dict], handlers: dict, traces: list[dict], agent_name: str):
    from cursor_sdk import CustomTool

    custom = {}
    for spec in openai_tools:
        fn = spec["function"]
        name = fn["name"]
        handler = handlers[name]

        def execute(args, context, _handler=handler, _name=name):  # noqa: ARG001
            payload = dict(args or {})
            try:
                result = _handler(**payload)
                ok = not (isinstance(result, dict) and "error" in result)
            except TypeError:
                try:
                    result = _handler()
                    ok = True
                except Exception as exc:  # noqa: BLE001
                    result = {"error": str(exc)}
                    ok = False
            except Exception as exc:  # noqa: BLE001
                result = {"error": str(exc)}
                ok = False
            traces.append({"agent": agent_name, "tool": _name, "args": payload, "ok": ok})
            if isinstance(result, (dict, list)):
                return result
            return str(result)

        custom[name] = CustomTool(
            description=fn.get("description") or name,
            input_schema=fn.get("parameters") or {"type": "object", "properties": {}},
            execute=execute,
        )
    return custom


def run_cursor_desk(
    messages: list[dict],
    *,
    session_id: str,
    api_key: str | None = None,
    language: str = "pl",
) -> dict:
    try:
        from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions
    except ImportError as exc:
        raise RuntimeError("Install cursor-sdk (pip install cursor-sdk) to use a Cursor API key.") from exc

    workspace = get_workspace(session_id)
    traces: list[dict] = []
    key = (api_key or settings.OPENAI_API_KEY).strip()
    lang = "Polish" if language.startswith("pl") else "English"
    today = datetime.now().date().isoformat()
    prompt = _build_prompt(messages, language=lang, today=today, has_report=workspace.report is not None)
    custom = {}
    custom.update(_custom_tools(FX_TOOLS, fx_handlers(), traces, "fx"))
    custom.update(_custom_tools(TAX_TOOLS, tax_handlers(workspace), traces, "tax"))

    try:
        with Agent.create(
            AgentOptions(
                model=settings.CURSOR_MODEL,
                api_key=key,
                tools=["mcp"],
                local=LocalAgentOptions(
                    cwd=str(ROOT),
                    setting_sources=[],
                    custom_tools=custom,
                ),
            )
        ) as agent:
            run = agent.send(prompt)
            result = run.wait()
    except CursorAgentError as exc:
        raise RuntimeError(f"Cursor agent failed to start: {exc}") from exc

    if getattr(result, "status", None) == "error":
        raise RuntimeError("Cursor agent run failed. Check the Cursor dashboard for that run.")

    answer = _extract_text(run, result)
    workspace.traces = traces
    return {
        "answer": answer,
        "traces": traces,
        "has_report": workspace.report is not None,
        "provider": "cursor",
    }


def _build_prompt(messages: list[dict], *, language: str, today: str, has_report: bool) -> str:
    transcript = "\n".join(f"{msg['role'].upper()}: {msg['content']}" for msg in messages)
    return f"""You are Belka, a Polish stock-tax desk. Answer in {language}.
Today is {today}. A FIFO/PIT-38 report is {"loaded" if has_report else "NOT loaded"} in this session.

You have live NBP tools (no cache) and tax-report tools. Rules:
- NEVER invent an exchange rate. Always call get_nbp_rate / get_nbp_daily_table / convert_to_pln / get_nbp_rate_series.
- For Polish tax FX use mode=t_minus_1 (NBP table from the business day before the transaction).
- For PIT-38 / lots / dividends / PIT-ZG, call the tax tools. If no report is loaded, say so.
- Do not edit files, run a shell, or search the repo. Only use the provided tools.
- This is not tax advice.

Conversation:
{transcript}
"""


def _extract_text(run, result) -> str:
    text = ""
    if hasattr(run, "text"):
        try:
            text = (run.text() or "").strip()
        except Exception:  # noqa: BLE001
            text = ""
    if text:
        return text
    for attr in ("result", "message", "output"):
        value = getattr(result, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return json.dumps(getattr(result, "__dict__", {"status": getattr(result, "status", "finished")}), default=str)
