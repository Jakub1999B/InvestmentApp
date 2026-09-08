from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import httpx

from .money import D

NBP_BASE = "https://api.nbp.pl/api/exchangerates"
MAX_CHUNK_DAYS = 90
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "BelkaTax/1.0 (+local; live NBP, no cache)",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


class RateLookup:
    def __init__(self, table_date: date, rate: Decimal, table: str = "A", table_no: str = ""):
        self.table_date = table_date
        self.rate = rate
        self.table = table
        self.table_no = table_no


class NbpClient:
    """Live NBP Table A + B mid rates. Nothing is persisted — every preload hits api.nbp.pl."""

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout
        self._tables: dict[str, dict[date, dict[str, Decimal]]] = {"A": {}, "B": {}}
        self._meta: dict[tuple[str, date], str] = {}

    def preload(self, start: date, end: date) -> None:
        for kind in ("A", "B"):
            cursor = start
            while cursor <= end:
                chunk_end = min(cursor + timedelta(days=MAX_CHUNK_DAYS - 1), end)
                self._load_chunk(kind, cursor, chunk_end)
                cursor = chunk_end + timedelta(days=1)

    def t_minus_1(self, currency: str, transaction_date: date) -> RateLookup:
        return self.rate_on_or_before(currency, transaction_date - timedelta(days=1))

    def rate_on_or_before(self, currency: str, on_date: date) -> RateLookup:
        code = _normalize_currency(currency)
        if code == "PLN":
            return RateLookup(on_date, Decimal("1"), "PLN", "")
        probe = on_date
        for _ in range(40):
            for kind in ("A", "B"):
                rates = self._tables[kind].get(probe)
                if rates and code in rates:
                    return RateLookup(probe, rates[code], kind, self._meta.get((kind, probe), ""))
            probe -= timedelta(days=1)
        raise LookupError(f"No live NBP Table A/B rate for {code} on or before {on_date.isoformat()}")

    def fetch_daily_table(self, on_date: date, kind: str = "A") -> dict | None:
        payload = self._get(f"{NBP_BASE}/tables/{kind}/{on_date.isoformat()}/")
        if payload is None:
            return None
        table = payload[0] if isinstance(payload, list) else payload
        self._absorb(kind, [table])
        return _public_table(kind, table)

    def fetch_latest_table(self, kind: str = "A") -> dict:
        payload = self._get(f"{NBP_BASE}/tables/{kind}/")
        if not payload:
            raise RuntimeError(f"NBP returned no current table {kind}")
        table = payload[0] if isinstance(payload, list) else payload
        self._absorb(kind, [table])
        return _public_table(kind, table)

    def fetch_rate_series(self, currency: str, start: date, end: date) -> list[dict]:
        code = _normalize_currency(currency)
        if code == "PLN":
            days = (end - start).days + 1
            return [
                {"date": (start + timedelta(days=i)).isoformat(), "code": "PLN", "mid": 1.0, "table": "PLN"}
                for i in range(days)
            ]
        rows: list[dict] = []
        for kind in ("A", "B"):
            cursor = start
            while cursor <= end:
                chunk_end = min(cursor + timedelta(days=MAX_CHUNK_DAYS - 1), end)
                payload = self._get(f"{NBP_BASE}/rates/{kind}/{code}/{cursor.isoformat()}/{chunk_end.isoformat()}/")
                cursor = chunk_end + timedelta(days=1)
                if not payload:
                    continue
                for item in payload.get("rates", []):
                    rows.append(
                        {
                            "date": item["effectiveDate"],
                            "code": code,
                            "mid": float(item["mid"]),
                            "table": kind,
                            "table_no": item.get("no", payload.get("table", "")),
                        }
                    )
                self._absorb_currency_series(kind, code, payload.get("rates", []))
            if rows:
                break
        rows.sort(key=lambda row: row["date"])
        return rows

    def convert(self, amount: Decimal, currency: str, on_date: date, mode: str = "t_minus_1") -> dict:
        lookup_date = on_date - timedelta(days=1) if mode == "t_minus_1" else on_date
        if mode == "t_minus_1":
            self.preload(lookup_date - timedelta(days=14), on_date)
            found = self.t_minus_1(currency, on_date)
        else:
            self.preload(lookup_date - timedelta(days=14), lookup_date)
            found = self.rate_on_or_before(currency, lookup_date)
        major, code = to_major_units(amount, currency)
        pln = major * found.rate
        return {
            "amount": float(major),
            "currency": code,
            "requested_currency": currency,
            "mode": mode,
            "transaction_date": on_date.isoformat(),
            "nbp_table_date": found.table_date.isoformat(),
            "nbp_table": found.table,
            "nbp_table_no": found.table_no,
            "rate": float(found.rate),
            "amount_pln": float(pln),
        }

    def _load_chunk(self, kind: str, start: date, end: date) -> None:
        payload = self._get(f"{NBP_BASE}/tables/{kind}/{start.isoformat()}/{end.isoformat()}/")
        if payload:
            self._absorb(kind, payload)

    def _absorb(self, kind: str, tables: list[dict]) -> None:
        for table in tables:
            effective = date.fromisoformat(table["effectiveDate"])
            rates = {row["code"].upper(): D(row["mid"]) for row in table.get("rates", [])}
            self._tables[kind][effective] = rates
            self._meta[(kind, effective)] = table.get("no", "")

    def _absorb_currency_series(self, kind: str, code: str, rates: list[dict]) -> None:
        for item in rates:
            effective = date.fromisoformat(item["effectiveDate"])
            bucket = self._tables[kind].setdefault(effective, {})
            bucket[code] = D(item["mid"])
            self._meta[(kind, effective)] = item.get("no", "")

    def _get(self, url: str):
        try:
            with httpx.Client(timeout=self.timeout, headers=HEADERS) as client:
                response = client.get(url, params={"format": "json"})
        except httpx.HTTPError as exc:
            raise RuntimeError(f"NBP API request failed: {url} ({exc})") from exc
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


class StaticRateClient:
    """Deterministic rates for unit tests only — never used in the live app."""

    def __init__(self, rates: dict[str, Decimal] | None = None, table_date: date | None = None):
        self.rates = {code.upper(): D(value) for code, value in (rates or {"USD": 4, "EUR": 4.3, "GBP": 5, "CHF": 4.5}).items()}
        self.rates["PLN"] = Decimal("1")
        self.table_date = table_date or date(2024, 1, 2)

    def preload(self, start: date, end: date) -> None:
        return None

    def t_minus_1(self, currency: str, transaction_date: date) -> RateLookup:
        code = _normalize_currency(currency)
        if code not in self.rates:
            raise LookupError(f"No static rate for {code}")
        table_date = min(self.table_date, transaction_date - timedelta(days=1))
        return RateLookup(table_date, self.rates[code], "TEST", "test")


def _public_table(kind: str, table: dict) -> dict:
    return {
        "table": kind,
        "no": table.get("no"),
        "effectiveDate": table.get("effectiveDate"),
        "rates": [
            {"code": row["code"], "currency": row.get("currency", ""), "mid": float(row["mid"])}
            for row in table.get("rates", [])
        ],
    }


def _normalize_currency(currency: str) -> str:
    code = (currency or "PLN").strip().upper()
    if code == "GBX":
        return "GBP"
    return code


def to_major_units(amount: Decimal, currency: str) -> tuple[Decimal, str]:
    code = (currency or "PLN").strip().upper()
    if code == "GBX":
        return amount / Decimal("100"), "GBP"
    return amount, code if code else "PLN"


def transaction_day(ts: datetime) -> date:
    return ts.date()
