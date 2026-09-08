from __future__ import annotations

from datetime import date, datetime

from ..money import D
from ..nbp import NbpClient
from .runtime import tool_schema
from .session import Workspace


def _parse_day(value: str) -> date:
    text = (value or "").strip()[:10]
    return date.fromisoformat(text)


FX_TOOLS = [
    tool_schema(
        "get_nbp_daily_table",
        "Fetch the LIVE NBP exchange-rate table for a calendar day (all currencies on that table). Table A is daily on business days; table B is weekly. Never invent rates.",
        {
            "on_date": {"type": "string", "description": "YYYY-MM-DD"},
            "table": {"type": "string", "enum": ["A", "B"], "description": "NBP table. Default A."},
        },
        ["on_date"],
    ),
    tool_schema(
        "get_latest_nbp_table",
        "Fetch the current LIVE NBP table (all currencies). Use when the user asks for today's / latest rates.",
        {"table": {"type": "string", "enum": ["A", "B"]}},
    ),
    tool_schema(
        "get_nbp_rate",
        "Look up the LIVE mid rate of one currency vs PLN. mode=published uses that calendar day (or previous published day if weekend/holiday). mode=t_minus_1 is the Polish tax rule: business day before the transaction.",
        {
            "currency": {"type": "string", "description": "ISO code, e.g. USD, EUR, GBP, CHF. GBX is treated as GBP pence."},
            "on_date": {"type": "string", "description": "YYYY-MM-DD transaction or requested date"},
            "mode": {"type": "string", "enum": ["t_minus_1", "published"], "description": "Default t_minus_1"},
        },
        ["currency", "on_date"],
    ),
    tool_schema(
        "get_nbp_rate_series",
        "Fetch LIVE daily NBP mid rates for one currency between two dates (inclusive). Chunked against the NBP API; no local cache.",
        {
            "currency": {"type": "string"},
            "start_date": {"type": "string", "description": "YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "YYYY-MM-DD"},
        },
        ["currency", "start_date", "end_date"],
    ),
    tool_schema(
        "convert_to_pln",
        "Convert an amount to PLN with a LIVE NBP rate. Default mode t_minus_1 matches PIT-38.",
        {
            "amount": {"type": "number"},
            "currency": {"type": "string"},
            "on_date": {"type": "string"},
            "mode": {"type": "string", "enum": ["t_minus_1", "published"]},
        },
        ["amount", "currency", "on_date"],
    ),
]


FX_SYSTEM = """You are the FX agent for Belka, a Polish investment-tax app.
You MUST call tools for every rate, table, or conversion. Never use memory, training data, or guessed FX numbers.
NBP Table A (major currencies) is published on Polish business days. Table B (other currencies) is typically weekly.
If a date has no table (weekend/holiday), say so and use the last published table — that is not a cache, it is how NBP publishes.
For Polish capital-gains tax, the legal rate is Table A/B mid from the last business day BEFORE the transaction (T-1, art. 11a).
Quote the table date, table number, and mid rate. Amounts in GBX are pence: divide by 100 then use GBP.
Today's date is {today}. This is not tax advice.
"""


def fx_handlers(_workspace: Workspace | None = None) -> dict:
    def get_nbp_daily_table(on_date: str, table: str = "A") -> dict:
        client = NbpClient()
        kind = (table or "A").upper()
        result = client.fetch_daily_table(_parse_day(on_date), kind)
        if result is None:
            return {
                "published": False,
                "date": on_date,
                "table": kind,
                "message": "NBP did not publish this table on that calendar day (weekend or holiday). Use get_nbp_rate with mode=published to walk back to the last published table.",
            }
        return {"published": True, **result}

    def get_latest_nbp_table(table: str = "A") -> dict:
        return NbpClient().fetch_latest_table((table or "A").upper())

    def get_nbp_rate(currency: str, on_date: str, mode: str = "t_minus_1") -> dict:
        client = NbpClient()
        day = _parse_day(on_date)
        converted = client.convert(D(1), currency, day, mode=mode or "t_minus_1")
        return {
            "currency": converted["currency"],
            "mode": converted["mode"],
            "transaction_date": converted["transaction_date"],
            "nbp_table_date": converted["nbp_table_date"],
            "nbp_table": converted["nbp_table"],
            "nbp_table_no": converted["nbp_table_no"],
            "mid_pln": converted["rate"],
            "fetched": "live NBP HTTP, no cache",
        }

    def get_nbp_rate_series(currency: str, start_date: str, end_date: str) -> dict:
        start = _parse_day(start_date)
        end = _parse_day(end_date)
        if end < start:
            start, end = end, start
        if (end - start).days > 366:
            return {"error": "Range too long. Ask for at most 366 days."}
        rows = NbpClient().fetch_rate_series(currency, start, end)
        return {"currency": currency.upper(), "count": len(rows), "rates": rows, "fetched": "live NBP HTTP, no cache"}

    def convert_to_pln(amount: float, currency: str, on_date: str, mode: str = "t_minus_1") -> dict:
        return NbpClient().convert(D(amount), currency, _parse_day(on_date), mode=mode or "t_minus_1")

    return {
        "get_nbp_daily_table": get_nbp_daily_table,
        "get_latest_nbp_table": get_latest_nbp_table,
        "get_nbp_rate": get_nbp_rate,
        "get_nbp_rate_series": get_nbp_rate_series,
        "convert_to_pln": convert_to_pln,
    }


def run_fx_agent(client, question: str, history: list[dict] | None = None):
    from .runtime import run_tool_loop

    return run_tool_loop(
        client,
        system=FX_SYSTEM.format(today=datetime.now().date().isoformat()),
        messages=[*(history or []), {"role": "user", "content": question}],
        tools=FX_TOOLS,
        handlers=fx_handlers(),
        agent_name="fx",
        max_rounds=6,
    )
