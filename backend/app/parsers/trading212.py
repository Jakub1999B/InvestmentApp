from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from ..csv_utils import RowView, rows_from_csv
from ..isin import country_from_isin
from ..models import ParsedFile, Transaction, TxType
from ..money import D, money

BUY_ACTIONS = {
    "market buy",
    "limit buy",
    "stop buy",
    "stop limit buy",
}
SELL_ACTIONS = {
    "market sell",
    "limit sell",
    "stop sell",
    "stop limit sell",
}


def looks_like_trading212(headers: list[str]) -> bool:
    return "action" in headers and ("time" in headers or "time utc" in headers) and (
        "no. of shares" in headers or "no of shares" in headers or "ticker" in headers
    )


def parse_trading212(filename: str, text: str) -> ParsedFile:
    headers, rows = rows_from_csv(text)
    transactions: list[Transaction] = []
    skipped: list[str] = []
    notes: list[str] = []
    seen_ids: set[str] = set()

    for index, row in enumerate(rows, start=2):
        action = row.get("Action").strip()
        if not action:
            continue
        action_key = re.sub(r"\s+", " ", action).strip()
        kind = _classify(action_key)
        if kind is None:
            skipped.append(f"Row {index}: ignored '{action}'")
            continue
        try:
            ts = _parse_time(row)
        except ValueError as exc:
            skipped.append(f"Row {index}: {exc}")
            continue

        tx_id = row.get("ID") or f"t212-{index}"
        if tx_id in seen_ids:
            tx_id = f"{tx_id}-{index}"
        seen_ids.add(tx_id)

        shares = abs(row.number("No. of shares", "No of shares", "Shares"))
        price = abs(row.number("Price / share", "Price/share", "Price"))
        currency = (row.get("Currency (Price / share)", "Currency (Price/share)", "Currency") or row.currency_of("Price / share")).upper()
        if not currency:
            currency = row.account_currency() or "EUR"

        fee = _sum_fees(row)
        fee_ccy = row.account_currency() or currency
        wht = abs(row.number("Withholding tax"))
        wht_ccy = row.get("Currency (Withholding tax)") or currency
        ticker = row.get("Ticker")
        isin = row.get("ISIN") or None
        name = row.get("Name") or None

        if kind == TxType.DIVIDEND:
            if not (shares > 0 and price > 0):
                total = abs(row.number("Total"))
                if total:
                    price = total
                    shares = D(1)
                    currency = row.account_currency() or currency
        elif kind in {TxType.INTEREST, TxType.CASH}:
            total = abs(row.number("Total"))
            total_ccy = row.account_currency() or currency
            price = total
            currency = total_ccy
            shares = D(0)
        elif kind == TxType.SPLIT:
            ratio = _split_ratio(row.get("Notes"), shares)
            shares = ratio
            price = D(0)

        transactions.append(
            Transaction(
                id=tx_id,
                broker="trading212",
                timestamp=ts,
                type=kind if kind != TxType.CASH else TxType.CASH,
                symbol=ticker,
                isin=isin,
                name=name,
                quantity=shares,
                price=price,
                currency=currency or "EUR",
                fee=fee,
                fee_currency=fee_ccy,
                withholding_tax=wht,
                withholding_currency=wht_ccy.upper() if wht_ccy else currency,
                country=country_from_isin(isin),
                notes=row.get("Notes"),
                raw_action=action,
            )
        )

    if not transactions:
        notes.append("Trading 212 file contained no supported buy/sell/dividend rows.")
    return ParsedFile(filename=filename, broker="trading212", transactions=transactions, skipped=skipped, notes=notes)


def _classify(action: str) -> TxType | None:
    key = action.lower().strip()
    if key in BUY_ACTIONS:
        return TxType.BUY
    if key in SELL_ACTIONS:
        return TxType.SELL
    if key.startswith("dividend"):
        return TxType.DIVIDEND
    if "interest" in key:
        return TxType.INTEREST
    if key in {"deposit", "withdrawal", "transfer in", "transfer out"}:
        return TxType.CASH
    if "split" in key:
        return TxType.SPLIT
    if key in {"bonus"}:
        return TxType.BUY
    return None


def _parse_time(row: RowView) -> datetime:
    from ..csv_utils import parse_datetime

    value = row.get("Time", "Time (UTC)")
    if not value:
        raise ValueError("missing Time")
    return parse_datetime(value)


def _sum_fees(row: RowView) -> Decimal:
    total = D(0)
    for name in (
        "Charge amount",
        "Stamp duty reserve tax",
        "Stamp duty",
        "Transaction fee",
        "Finra fee",
        "Currency conversion fee",
        "French transaction tax",
        "Deposit fee",
        "Taxes",
    ):
        total += abs(row.number(name))
    return money(total)


def _split_ratio(notes: str, shares: Decimal) -> Decimal:
    text = (notes or "").lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:for|:)\s*(\d+(?:\.\d+)?)", text)
    if match:
        return D(match.group(1)) / D(match.group(2))
    match = re.search(r"(?:ratio|split)\s*[x×]?\s*(\d+(?:\.\d+)?)", text)
    if match:
        return D(match.group(1))
    if shares > 0:
        return shares
    return D(1)
