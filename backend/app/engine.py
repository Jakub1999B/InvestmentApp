from __future__ import annotations

from decimal import Decimal

from .models import ParsedFile, TaxSummary, Transaction
from .money import D
from .nbp import NbpClient, StaticRateClient
from .parsers import parse_file
from .tax import TaxCalculator


def parse_uploads(files: list[tuple[str, bytes]], account_currency: str = "PLN") -> tuple[list[Transaction], list[str], list[str], list[str]]:
    transactions: list[Transaction] = []
    skipped: list[str] = []
    filenames: list[str] = []
    brokers: list[str] = []
    seen: set[str] = set()
    for filename, data in files:
        parsed: ParsedFile = parse_file(filename, data, account_currency=account_currency)
        filenames.append(filename)
        brokers.append(parsed.broker)
        skipped.extend(parsed.skipped)
        skipped.extend(parsed.notes)
        for tx in parsed.transactions:
            key = f"{tx.broker}|{tx.id}|{tx.type}|{tx.timestamp.isoformat()}"
            if key in seen:
                continue
            seen.add(key)
            transactions.append(tx)
    return transactions, filenames, skipped, brokers


def calculate_from_files(
    files: list[tuple[str, bytes]],
    tax_year: int,
    prior_losses_pln: Decimal = D(0),
    account_currency: str = "PLN",
    use_live_nbp: bool = True,
) -> TaxSummary:
    transactions, filenames, skipped, _ = parse_uploads(files, account_currency=account_currency)
    if not transactions:
        raise ValueError("No supported transactions were found in the uploaded files.")
    rates: NbpClient | StaticRateClient = NbpClient() if use_live_nbp else StaticRateClient()
    return TaxCalculator(rates).calculate(
        transactions,
        tax_year=tax_year,
        prior_losses_pln=prior_losses_pln,
        filenames=filenames,
        skipped=skipped,
    )
