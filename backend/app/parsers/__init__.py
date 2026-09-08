from __future__ import annotations

from ..csv_utils import decode_bytes, normalize_header, rows_from_csv
from ..models import ParsedFile
from .generic import parse_generic
from .trading212 import looks_like_trading212, parse_trading212
from .xtb import looks_like_xtb, parse_xtb


def parse_file(filename: str, data: bytes, account_currency: str = "PLN") -> ParsedFile:
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        return parse_xtb(filename, data, account_currency=account_currency)

    text = decode_bytes(data)
    headers, _ = rows_from_csv(text)
    normalized = [normalize_header(h) for h in headers]

    if looks_like_trading212(normalized):
        return parse_trading212(filename, text)
    if looks_like_xtb(normalized, text):
        return parse_xtb(filename, data, account_currency=account_currency)
    if _looks_like_generic(normalized):
        return parse_generic(filename, text)

    raise ValueError(
        f"{filename}: could not detect broker format. "
        "Use a Trading 212 history CSV, an XTB xStation export, or the generic CSV "
        "(date, type, symbol, quantity, price, currency)."
    )


def _looks_like_generic(headers: list[str]) -> bool:
    joined = " ".join(headers)
    return "date" in joined and "type" in joined and ("symbol" in joined or "ticker" in joined)
