from __future__ import annotations

from ..csv_utils import parse_datetime, rows_from_csv
from ..isin import country_from_isin
from ..models import ParsedFile, Transaction, TxType
from ..money import D

TYPE_MAP = {
    "buy": TxType.BUY,
    "purchase": TxType.BUY,
    "kupno": TxType.BUY,
    "sell": TxType.SELL,
    "sale": TxType.SELL,
    "sprzedaz": TxType.SELL,
    "sprzedaż": TxType.SELL,
    "dividend": TxType.DIVIDEND,
    "dywidenda": TxType.DIVIDEND,
    "interest": TxType.INTEREST,
    "odsetki": TxType.INTEREST,
    "split": TxType.SPLIT,
    "transfer_in": TxType.TRANSFER_IN,
    "transfer in": TxType.TRANSFER_IN,
    "transfer_out": TxType.TRANSFER_OUT,
    "transfer out": TxType.TRANSFER_OUT,
}


def parse_generic(filename: str, text: str) -> ParsedFile:
    _, rows = rows_from_csv(text)
    transactions: list[Transaction] = []
    skipped: list[str] = []
    for index, row in enumerate(rows, start=2):
        raw_type = row.get("type", "Type", "action", "Action").strip().lower()
        kind = TYPE_MAP.get(raw_type)
        if kind is None:
            skipped.append(f"Row {index}: unknown type '{raw_type}'")
            continue
        date_value = row.get("date", "Date", "time", "Time")
        if not date_value:
            skipped.append(f"Row {index}: missing date")
            continue
        try:
            ts = parse_datetime(date_value)
        except ValueError as exc:
            skipped.append(f"Row {index}: {exc}")
            continue
        isin = row.get("isin", "ISIN") or None
        transactions.append(
            Transaction(
                id=row.get("id", "ID") or f"generic-{index}",
                broker=row.get("broker", "Broker") or "generic",
                timestamp=ts,
                type=kind,
                symbol=row.get("symbol", "ticker", "Ticker", "Symbol"),
                isin=isin,
                name=row.get("name", "Name") or None,
                quantity=abs(row.number("quantity", "qty", "shares", "No. of shares")),
                price=abs(row.number("price", "Price", "price_per_share")),
                currency=(row.get("currency", "Currency") or "PLN").upper(),
                fee=abs(row.number("fee", "Fee", "commission")),
                fee_currency=(row.get("fee_currency", "Fee currency") or None),
                withholding_tax=abs(row.number("withholding_tax", "withholding", "WHT")),
                withholding_currency=(row.get("withholding_currency") or None),
                country=row.get("country", "Country") or country_from_isin(isin),
                notes=row.get("notes", "Notes"),
                raw_action=raw_type,
            )
        )
    return ParsedFile(filename=filename, broker="generic", transactions=transactions, skipped=skipped)
