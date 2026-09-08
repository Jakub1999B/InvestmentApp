from __future__ import annotations

COUNTRY_NAMES: dict[str, str] = {
    "US": "United States",
    "GB": "United Kingdom",
    "IE": "Ireland",
    "DE": "Germany",
    "FR": "France",
    "NL": "Netherlands",
    "CH": "Switzerland",
    "LU": "Luxembourg",
    "BE": "Belgium",
    "AT": "Austria",
    "ES": "Spain",
    "IT": "Italy",
    "SE": "Sweden",
    "DK": "Denmark",
    "NO": "Norway",
    "FI": "Finland",
    "PL": "Poland",
    "CZ": "Czechia",
    "CA": "Canada",
    "AU": "Australia",
    "JP": "Japan",
    "HK": "Hong Kong",
    "SG": "Singapore",
    "KY": "Cayman Islands",
    "GG": "Guernsey",
    "JE": "Jersey",
    "IM": "Isle of Man",
    "PT": "Portugal",
    "GR": "Greece",
    "KR": "South Korea",
    "TW": "Taiwan",
    "IN": "India",
    "BR": "Brazil",
    "MX": "Mexico",
    "IL": "Israel",
    "ZA": "South Africa",
}

XTB_SUFFIX_CURRENCY: dict[str, tuple[str, str]] = {
    "US": ("USD", "US"),
    "UK": ("GBP", "GB"),
    "L": ("GBP", "GB"),
    "DE": ("EUR", "DE"),
    "FR": ("EUR", "FR"),
    "NL": ("EUR", "NL"),
    "ES": ("EUR", "ES"),
    "IT": ("EUR", "IT"),
    "CH": ("CHF", "CH"),
    "PL": ("PLN", "PL"),
    "SE": ("SEK", "SE"),
    "DK": ("DKK", "DK"),
    "NO": ("NOK", "NO"),
    "CZ": ("CZK", "CZ"),
    "JP": ("JPY", "JP"),
    "HK": ("HKD", "HK"),
    "AU": ("AUD", "AU"),
    "CA": ("CAD", "CA"),
    "BE": ("EUR", "BE"),
    "AT": ("EUR", "AT"),
    "PT": ("EUR", "PT"),
    "IE": ("EUR", "IE"),
    "LU": ("EUR", "LU"),
}


def country_from_isin(isin: str | None) -> str | None:
    if not isin:
        return None
    code = isin.strip().upper()
    if len(code) < 2:
        return None
    prefix = code[:2]
    if prefix.isalpha():
        return prefix
    return None


def country_name(code: str | None) -> str:
    if not code:
        return "Unknown"
    return COUNTRY_NAMES.get(code.upper(), code.upper())


def infer_from_xtb_symbol(symbol: str) -> tuple[str, str | None]:
    """Return (currency, country) from XTB-style SYMBOL.US tickers."""
    text = symbol.strip().upper()
    if "." in text:
        _, suffix = text.rsplit(".", 1)
        if suffix in XTB_SUFFIX_CURRENCY:
            currency, country = XTB_SUFFIX_CURRENCY[suffix]
            return currency, country
    return "PLN", None
