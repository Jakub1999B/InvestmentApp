from __future__ import annotations

from datetime import datetime

from .runtime import run_tool_loop, tool_schema
from .session import Workspace

TAX_TOOLS = [
    tool_schema(
        "get_tax_summary",
        "Return the PIT-38 helper totals for the report currently loaded in this session.",
        {},
    ),
    tool_schema(
        "get_pit38_fields",
        "Return numbered PIT-38 helper fields (variant 18 mapping) from the current report.",
        {},
    ),
    tool_schema(
        "get_realizations",
        "FIFO matched sales in the tax year. Optionally filter by symbol.",
        {"symbol": {"type": "string"}},
    ),
    tool_schema(
        "get_dividends",
        "Dividend rows in the tax year, including withholding tax and 19% Polish tax.",
        {"symbol": {"type": "string"}},
    ),
    tool_schema(
        "get_open_lots",
        "Unsold FIFO lots still held after all sales in the history.",
        {"symbol": {"type": "string"}},
    ),
    tool_schema(
        "get_pit_zg",
        "Foreign-source split by country for PIT/ZG attachments.",
        {},
    ),
    tool_schema(
        "get_warnings",
        "Parser skips and tax-engine warnings (missing cost basis, loss carryforward, etc.).",
        {},
    ),
    tool_schema(
        "polish_tax_rules",
        "Return the structured Polish stock-tax rules this app implements. Use instead of guessing the law.",
        {"topic": {"type": "string", "enum": ["fifo", "nbp", "belka", "dividends", "losses", "pit38", "all"]}},
    ),
]


RULES = {
    "fifo": (
        "Statutory FIFO per brokerage account (art. 24 ust. 10 PIT). Oldest purchase lots are consumed first. "
        "Fees on buys increase cost; fees on sells reduce proceeds. Matching is not pooled across brokers."
    ),
    "nbp": (
        "Each foreign-currency amount is converted at the NBP Table A (or B) mid rate from the last day "
        "NBP published a table before the transaction date (T-1, art. 11a). Weekends and Polish holidays skip backward. "
        "This app always fetches those tables live from api.nbp.pl — it does not keep a rate cache."
    ),
    "belka": (
        "19% flat tax on net capital gains (art. 30b). No annual exemption and no holding-period relief. "
        "Tax is rounded to full zloty (art. 63 Ordynacji podatkowej)."
    ),
    "dividends": (
        "Foreign dividends and interest: 19% on the gross PLN amount. Foreign withholding is creditable only up to "
        "the Polish 19% (treaty/credit method). Excess WHT is not refunded in Poland. Usually attach PIT/ZG per country."
    ),
    "losses": (
        "Securities losses carry forward 5 years in the same category (art. 9 ust. 3). In a given year you may deduct "
        "up to 50% of a given year's loss, or up to PLN 5m of a loss in one of those years. This app applies only the "
        "amount the user typed as prior-year losses — it does not auto-apply the 50%/5m election."
    ),
    "pit38": (
        "Helper mapping for PIT-38 variant 18 (2025 return): 22 revenue, 23 costs, 28 income, 29 loss, 30 prior losses, "
        "31 tax base, 33/35 tax due, 47–49 foreign dividends/interest, 51 total tax, 72 number of PIT/ZG attachments. "
        "Copy into Twój e-PIT. This is not an official e-Deklaracje file."
    ),
}


TAX_SYSTEM = """You are the tax agent for Belka. You explain a FIFO + NBP T-1 PIT-38 helper report.
Use tools. Do not invent PLN totals, lot matches, or NBP rates.
If no report is loaded, say so and tell the user to upload a broker CSV first.
Never present this as official tax advice or as a filed return. Mention it is a helper for a doradca podatkowy.
Today is {today}.
"""


def tax_handlers(workspace: Workspace) -> dict:
    def _need_report() -> dict | None:
        if workspace.report is None:
            return {"error": "No tax report in this session. Ask the user to calculate a broker export first."}
        return None

    def get_tax_summary() -> dict:
        missing = _need_report()
        if missing:
            return missing
        r = workspace.report
        return {
            "tax_year": r.tax_year,
            "brokers": r.brokers,
            "files": r.imported_files,
            "revenue_pln": r.revenue_pln,
            "costs_pln": r.costs_pln,
            "income_pln": r.income_pln,
            "loss_pln": r.loss_pln,
            "tax_base_pln": r.tax_base_pln,
            "capital_gains_tax_pln": r.capital_gains_tax_pln,
            "dividends_gross_pln": r.dividends_gross_pln,
            "dividends_to_pay_pln": r.dividends_to_pay_pln,
            "total_tax_pln": r.total_tax_pln,
            "unmatched_sold_qty": r.unmatched_sold_qty,
        }

    def get_pit38_fields() -> dict:
        missing = _need_report()
        if missing:
            return missing
        return workspace.report.pit38.model_dump()

    def get_realizations(symbol: str = "") -> dict:
        missing = _need_report()
        if missing:
            return missing
        rows = workspace.report.realizations
        if symbol:
            key = symbol.upper()
            rows = [row for row in rows if key in (row.symbol or "").upper()]
        return {"count": len(rows), "realizations": [row.model_dump() for row in rows[:80]]}

    def get_dividends(symbol: str = "") -> dict:
        missing = _need_report()
        if missing:
            return missing
        rows = workspace.report.dividends
        if symbol:
            key = symbol.upper()
            rows = [row for row in rows if key in (row.symbol or "").upper()]
        return {"count": len(rows), "dividends": [row.model_dump() for row in rows]}

    def get_open_lots(symbol: str = "") -> dict:
        missing = _need_report()
        if missing:
            return missing
        rows = workspace.report.open_lots
        if symbol:
            key = symbol.upper()
            rows = [row for row in rows if key in (row.symbol or "").upper()]
        return {"count": len(rows), "open_lots": [row.model_dump() for row in rows[:80]]}

    def get_pit_zg() -> dict:
        missing = _need_report()
        if missing:
            return missing
        return {"countries": [row.model_dump() for row in workspace.report.pit_zg]}

    def get_warnings() -> dict:
        missing = _need_report()
        if missing:
            return missing
        return {
            "warnings": [row.model_dump() for row in workspace.report.warnings],
            "skipped": workspace.report.skipped[:40],
        }

    def polish_tax_rules(topic: str = "all") -> dict:
        if topic and topic != "all" and topic in RULES:
            return {"topic": topic, "rule": RULES[topic]}
        return {"rules": RULES}

    return {
        "get_tax_summary": get_tax_summary,
        "get_pit38_fields": get_pit38_fields,
        "get_realizations": get_realizations,
        "get_dividends": get_dividends,
        "get_open_lots": get_open_lots,
        "get_pit_zg": get_pit_zg,
        "get_warnings": get_warnings,
        "polish_tax_rules": polish_tax_rules,
    }


def run_tax_agent(client, question: str, workspace: Workspace, history: list[dict] | None = None):
    return run_tool_loop(
        client,
        system=TAX_SYSTEM.format(today=datetime.now().date().isoformat()),
        messages=[*(history or []), {"role": "user", "content": question}],
        tools=TAX_TOOLS,
        handlers=tax_handlers(workspace),
        agent_name="tax",
        max_rounds=6,
    )
