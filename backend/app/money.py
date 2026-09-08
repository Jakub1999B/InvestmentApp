from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

GROSZE = Decimal("0.01")
ZLOTY = Decimal("1")


def D(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not text or text in {"-", "—", "n/a", "N/A"}:
        return Decimal("0")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        left, _, right = text.partition(",")
        if len(right) <= 2:
            text = f"{left}.{right}"
        else:
            text = text.replace(",", "")
    return Decimal(text)


def money(value: Decimal) -> Decimal:
    return value.quantize(GROSZE, rounding=ROUND_HALF_UP)


def round_zloty(value: Decimal) -> Decimal:
    """Art. 63 Ordynacji podatkowej: round to full PLN, 50 gr up."""
    return value.quantize(ZLOTY, rounding=ROUND_HALF_UP)


def as_float(value: Decimal) -> float:
    return float(money(value))
