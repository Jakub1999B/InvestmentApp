from __future__ import annotations

from datetime import datetime

from .. import settings
from .cursor_runtime import run_cursor_desk
from .fx_agent import run_fx_agent
from .runtime import make_client, run_tool_loop, tool_schema
from .session import get_workspace
from .tax_agent import run_tax_agent

DESK_TOOLS = [
    tool_schema(
        "consult_fx_agent",
        "Ask the FX specialist. It fetches LIVE NBP Table A/B rates (no cache) for any date, full daily tables, series, and PLN conversions.",
        {"question": {"type": "string"}},
        ["question"],
    ),
    tool_schema(
        "consult_tax_agent",
        "Ask the tax specialist about the current FIFO/PIT-38 report, lots, dividends, PIT/ZG, or the Polish rules this app implements.",
        {"question": {"type": "string"}},
        ["question"],
    ),
]


DESK_SYSTEM = """You are the desk agent for Belka, a Polish stock-tax workshop.
You coordinate two specialists and answer in {language}:
- FX agent: live NBP currency rates for every published day (Table A and B). Never quote a rate yourself.
- Tax agent: FIFO lots, PIT-38 helper fields, dividends, warnings for the report loaded in this session.
If the user asks about a rate, conversion, or NBP table, you MUST call consult_fx_agent.
If they ask about tax, lots, PIT-38, dividends, or their uploaded trades, call consult_tax_agent.
You may call both. Keep answers concrete: numbers, dates, table numbers. This is not tax advice.
Today is {today}. Session has a tax report: {has_report}.
"""


def run_desk(
    messages: list[dict],
    *,
    session_id: str,
    api_key: str | None = None,
    language: str = "pl",
) -> dict:
    workspace = get_workspace(session_id)
    if settings.is_cursor_dashboard_key(api_key):
        return run_cursor_desk(messages, session_id=session_id, api_key=api_key, language=language)
    client = make_client(api_key)
    traces: list[dict] = []

    def consult_fx_agent(question: str) -> dict:
        answer, fx_traces = run_fx_agent(client, question)
        traces.extend(fx_traces)
        return {"agent": "fx", "answer": answer}

    def consult_tax_agent(question: str) -> dict:
        answer, tax_traces = run_tax_agent(client, question, workspace)
        traces.extend(tax_traces)
        return {"agent": "tax", "answer": answer}

    lang = "Polish" if language.startswith("pl") else "English"
    answer, desk_traces = run_tool_loop(
        client,
        system=DESK_SYSTEM.format(
            language=lang,
            today=datetime.now().date().isoformat(),
            has_report="yes" if workspace.report else "no",
        ),
        messages=messages,
        tools=DESK_TOOLS,
        handlers={"consult_fx_agent": consult_fx_agent, "consult_tax_agent": consult_tax_agent},
        agent_name="desk",
        max_rounds=6,
    )
    traces = desk_traces + traces
    workspace.traces = traces
    return {"answer": answer, "traces": traces, "has_report": workspace.report is not None}
