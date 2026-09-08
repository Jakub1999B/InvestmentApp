from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from .money import D


class TxType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    SPLIT = "split"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    CASH = "cash"
    UNKNOWN = "unknown"


class Transaction(BaseModel):
    id: str
    broker: str
    account: str = "default"
    timestamp: datetime
    type: TxType
    symbol: str = ""
    isin: str | None = None
    name: str | None = None
    quantity: Decimal = Field(default_factory=lambda: D(0))
    price: Decimal = Field(default_factory=lambda: D(0))
    currency: str = "PLN"
    fee: Decimal = Field(default_factory=lambda: D(0))
    fee_currency: str | None = None
    withholding_tax: Decimal = Field(default_factory=lambda: D(0))
    withholding_currency: str | None = None
    country: str | None = None
    notes: str = ""
    raw_action: str = ""

    @property
    def instrument_key(self) -> str:
        if self.isin:
            return self.isin.strip().upper()
        return self.symbol.strip().upper()

    @property
    def lot_key(self) -> str:
        return f"{self.broker}|{self.account}|{self.instrument_key}"


class ParsedFile(BaseModel):
    filename: str
    broker: str
    transactions: list[Transaction]
    skipped: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class WarningItem(BaseModel):
    level: str
    code: str
    message: str
    detail: str | None = None


class Realization(BaseModel):
    sell_id: str
    symbol: str
    isin: str | None
    name: str | None
    broker: str
    sell_date: str
    buy_date: str
    quantity: float
    proceeds_pln: float
    cost_pln: float
    fees_pln: float
    gain_pln: float
    sell_currency: str
    sell_price: float
    buy_price: float
    buy_currency: str
    nbp_sell_rate: float
    nbp_buy_rate: float
    nbp_sell_table_date: str
    nbp_buy_table_date: str
    country: str | None


class DividendRow(BaseModel):
    id: str
    date: str
    symbol: str
    isin: str | None
    name: str | None
    broker: str
    country: str | None
    gross_pln: float
    withholding_pln: float
    polish_tax_19: float
    credit_pln: float
    to_pay_pln: float
    currency: str
    nbp_rate: float
    nbp_table_date: str


class InterestRow(BaseModel):
    id: str
    date: str
    broker: str
    gross_pln: float
    withholding_pln: float
    currency: str
    nbp_rate: float
    nbp_table_date: str
    notes: str = ""


class OpenLot(BaseModel):
    symbol: str
    isin: str | None
    name: str | None
    broker: str
    buy_date: str
    quantity: float
    price: float
    currency: str
    cost_pln: float
    nbp_rate: float
    nbp_table_date: str


class PitZgCountry(BaseModel):
    country: str
    country_name: str
    securities_revenue_pln: float
    securities_costs_pln: float
    securities_income_pln: float
    dividends_gross_pln: float
    dividends_withholding_pln: float
    interest_gross_pln: float


class Pit38Fields(BaseModel):
    field_22_revenue: float
    field_23_costs: float
    field_28_income: float
    field_29_loss: float
    field_30_prior_losses: float
    field_31_tax_base: float
    field_33_tax: float
    field_35_tax_due: float
    field_47_div_tax: float
    field_48_foreign_credit: float
    field_49_div_to_pay: float
    field_51_total_tax: float
    field_72_pit_zg_count: int


class TaxSummary(BaseModel):
    tax_year: int
    brokers: list[str]
    imported_files: list[str]
    transaction_count: int
    buy_count: int
    sell_count: int
    dividend_count: int
    revenue_pln: float
    costs_pln: float
    income_pln: float
    loss_pln: float
    prior_losses_applied_pln: float
    tax_base_pln: float
    capital_gains_tax_pln: float
    dividends_gross_pln: float
    dividends_withholding_pln: float
    dividends_tax_pln: float
    dividends_credit_pln: float
    dividends_to_pay_pln: float
    interest_gross_pln: float
    interest_tax_pln: float
    total_tax_pln: float
    unmatched_sold_qty: float
    pit38: Pit38Fields
    realizations: list[Realization]
    dividends: list[DividendRow]
    interest: list[InterestRow]
    open_lots: list[OpenLot]
    pit_zg: list[PitZgCountry]
    warnings: list[WarningItem]
    skipped: list[str]
    disclaimer: str
