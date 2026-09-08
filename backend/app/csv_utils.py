from __future__ import annotations

import csv
import io
import re
from datetime import datetime

from .money import D


CURRENCY_IN_HEADER = re.compile(r"\s*\(([A-Z]{3})\)\s*")


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1250", "iso-8859-2", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def sniff_dialect(text: str) -> csv.Dialect:
    sample = text[:8000]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel()
        if sample.count(";") > sample.count(","):
            dialect.delimiter = ";"
        return dialect


def normalize_header(name: str) -> str:
    cleaned = name.replace("\ufeff", "").strip()
    cleaned = CURRENCY_IN_HEADER.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def header_currency(name: str) -> str | None:
    match = CURRENCY_IN_HEADER.search(name.replace("\ufeff", ""))
    return match.group(1) if match else None


class RowView:
    def __init__(self, row: dict[str, str], original_headers: list[str]):
        self._raw = {k: (v or "").strip() for k, v in row.items() if k is not None}
        self._by_norm: dict[str, str] = {}
        self._header_currency: dict[str, str] = {}
        for original in original_headers:
            value = self._raw.get(original, "")
            key = normalize_header(original)
            if key and key not in self._by_norm:
                self._by_norm[key] = value
            currency = header_currency(original)
            if currency and key:
                self._header_currency[key] = currency

    def get(self, *names: str, default: str = "") -> str:
        for name in names:
            key = normalize_header(name)
            if key in self._by_norm and self._by_norm[key] != "":
                return self._by_norm[key]
        for name in names:
            key = normalize_header(name)
            for existing, value in self._by_norm.items():
                if existing.startswith(key) and value != "":
                    return value
        return default

    def number(self, *names: str) -> D:
        return D(self.get(*names))

    def currency_of(self, *names: str, fallback: str = "EUR") -> str:
        for name in names:
            key = normalize_header(name)
            if key in self._header_currency:
                return self._header_currency[key]
            explicit = self.get(f"Currency ({name})", f"Currency {name}")
            if explicit:
                return explicit.upper()
        price_ccy = self.get("Currency (Price / share)", "Currency (Price/share)", "Currency")
        if price_ccy:
            return price_ccy.upper()
        return fallback

    def account_currency(self) -> str | None:
        for key, ccy in self._header_currency.items():
            if key in {"total", "result", "charge amount"}:
                return ccy
        total_ccy = self.get("Currency (Total)", "Currency (Result)")
        return total_ccy.upper() if total_ccy else None


def parse_datetime(value: str) -> datetime:
    text = value.strip().replace("T", " ")
    text = re.sub(r"Z$", "", text)
    text = re.sub(r"([+-]\d{2}:\d{2})$", "", text).strip()
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {value!r}")


def rows_from_csv(text: str) -> tuple[list[str], list[RowView]]:
    dialect = sniff_dialect(text)
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = [h for h in (reader.fieldnames or []) if h]
    views = [RowView(row, headers) for row in reader if any((v or "").strip() for v in row.values())]
    return headers, views
