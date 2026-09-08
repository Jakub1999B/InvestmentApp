from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from .fifo import FifoEngine
from .isin import country_from_isin, country_name
from .models import (
    DividendRow,
    InterestRow,
    Pit38Fields,
    PitZgCountry,
    TaxSummary,
    Transaction,
    TxType,
    WarningItem,
)
from .money import D, as_float, money, round_zloty
from .nbp import NbpClient, StaticRateClient, to_major_units, transaction_day

BELKA = Decimal("0.19")
DISCLAIMER = (
    "This report is an informational helper for PIT-38 / PIT-ZG, not tax advice. "
    "Polish capital gains use a 19% flat rate (podatek Belki), statutory FIFO per brokerage account "
    "(art. 24 ust. 10), and NBP Table A rates from the business day before each transaction (art. 11a). "
    "Verify figures with a doradca podatkowy before filing."
)


class TaxCalculator:
    def __init__(self, rates: NbpClient | StaticRateClient):
        self.rates = rates
        self.fifo = FifoEngine(rates)

    def calculate(
        self,
        transactions: list[Transaction],
        tax_year: int,
        prior_losses_pln: Decimal = D(0),
        filenames: list[str] | None = None,
        skipped: list[str] | None = None,
    ) -> TaxSummary:
        dates = [tx.timestamp.date() for tx in transactions]
        if dates:
            self.rates.preload(min(dates) - timedelta(days=14), max(dates))

        fifo = self.fifo.run(transactions, tax_year)
        warnings = list(fifo.warnings)

        revenue = D(0)
        costs = D(0)
        for row in fifo.realizations:
            revenue += D(row.proceeds_pln)
            costs += D(row.cost_pln)

        income_raw = money(revenue - costs)
        income = money(income_raw) if income_raw > 0 else D(0)
        loss = money(-income_raw) if income_raw < 0 else D(0)
        prior = money(max(D(0), prior_losses_pln))
        prior_applied = money(min(prior, income))
        tax_base_exact = money(income - prior_applied)
        tax_base = round_zloty(tax_base_exact) if tax_base_exact > 0 else D(0)
        cg_tax = round_zloty(tax_base * BELKA) if tax_base > 0 else D(0)

        dividends = self._dividends(transactions, tax_year, warnings)
        interest = self._interest(transactions, tax_year, warnings)

        div_gross = money(sum((D(row.gross_pln) for row in dividends), D(0)))
        div_wht = money(sum((D(row.withholding_pln) for row in dividends), D(0)))
        div_tax = round_zloty(div_gross * BELKA) if div_gross else D(0)
        div_credit = money(min(D(div_tax), div_wht))
        # Credit is applied against the 19% tax; round the payable amount.
        div_to_pay = round_zloty(max(D(0), D(div_tax) - div_credit))

        int_gross = money(sum((D(row.gross_pln) for row in interest), D(0)))
        int_wht = money(sum((D(row.withholding_pln) for row in interest), D(0)))
        int_tax_raw = round_zloty(int_gross * BELKA) if int_gross else D(0)
        int_to_pay = round_zloty(max(D(0), D(int_tax_raw) - int_wht))

        # Dividends and interest share Section G conceptually; we keep them visible separately
        # but map combined 19% tax / credit / to-pay into PIT-38 fields 47-49.
        section_g_tax = round_zloty((div_gross + int_gross) * BELKA) if (div_gross + int_gross) else D(0)
        section_g_credit = money(min(D(section_g_tax), div_wht + int_wht))
        section_g_to_pay = round_zloty(max(D(0), D(section_g_tax) - section_g_credit))

        total_tax = cg_tax + section_g_to_pay
        pit_zg = self._pit_zg(fifo.realizations, dividends, interest)

        if not any(tx.type in {TxType.BUY, TxType.SELL} for tx in transactions):
            warnings.append(
                WarningItem(
                    level="warning",
                    code="no_trades",
                    message="No buy/sell trades were found. If you sold shares this year, the export may be incomplete.",
                )
            )
        if loss > 0:
            warnings.append(
                WarningItem(
                    level="info",
                    code="loss_carryforward",
                    message=(
                        f"This year closed with a {as_float(loss):.2f} PLN securities loss. "
                        "File PIT-38 anyway so you can carry it forward for up to 5 years "
                        "(art. 9 ust. 3 — 50% per year, or up to PLN 5m in one year)."
                    ),
                )
            )

        brokers = sorted({tx.broker for tx in transactions})
        pit38 = Pit38Fields(
            field_22_revenue=as_float(revenue),
            field_23_costs=as_float(costs),
            field_28_income=as_float(income),
            field_29_loss=as_float(loss),
            field_30_prior_losses=as_float(prior_applied),
            field_31_tax_base=as_float(tax_base),
            field_33_tax=as_float(cg_tax),
            field_35_tax_due=as_float(cg_tax),
            field_47_div_tax=as_float(section_g_tax),
            field_48_foreign_credit=as_float(section_g_credit),
            field_49_div_to_pay=as_float(section_g_to_pay),
            field_51_total_tax=as_float(total_tax),
            field_72_pit_zg_count=len(pit_zg),
        )
        return TaxSummary(
            tax_year=tax_year,
            brokers=brokers,
            imported_files=filenames or [],
            transaction_count=len(transactions),
            buy_count=sum(1 for tx in transactions if tx.type == TxType.BUY),
            sell_count=sum(1 for tx in transactions if tx.type == TxType.SELL),
            dividend_count=len(dividends),
            revenue_pln=as_float(revenue),
            costs_pln=as_float(costs),
            income_pln=as_float(income),
            loss_pln=as_float(loss),
            prior_losses_applied_pln=as_float(prior_applied),
            tax_base_pln=as_float(tax_base),
            capital_gains_tax_pln=as_float(cg_tax),
            dividends_gross_pln=as_float(div_gross),
            dividends_withholding_pln=as_float(div_wht),
            dividends_tax_pln=as_float(div_tax),
            dividends_credit_pln=as_float(div_credit),
            dividends_to_pay_pln=as_float(div_to_pay),
            interest_gross_pln=as_float(int_gross),
            interest_tax_pln=as_float(int_to_pay),
            total_tax_pln=as_float(total_tax),
            unmatched_sold_qty=as_float(fifo.unmatched_sold_qty),
            pit38=pit38,
            realizations=fifo.realizations,
            dividends=dividends,
            interest=interest,
            open_lots=fifo.open_lots,
            pit_zg=pit_zg,
            warnings=warnings,
            skipped=skipped or [],
            disclaimer=DISCLAIMER,
        )

    def _dividends(self, transactions: list[Transaction], tax_year: int, warnings: list[WarningItem]) -> list[DividendRow]:
        rows: list[DividendRow] = []
        for tx in transactions:
            if tx.type != TxType.DIVIDEND or tx.timestamp.year != tax_year:
                continue
            qty = abs(tx.quantity)
            if tx.price > 0 and qty > 0:
                gross_orig = qty * tx.price
                gross_ccy = tx.currency
            else:
                gross_orig = abs(tx.price) if tx.price else D(0)
                gross_ccy = tx.currency
            gross_major, gross_ccy = to_major_units(gross_orig, gross_ccy)
            lookup = self.rates.t_minus_1(gross_ccy, transaction_day(tx.timestamp))
            gross_pln = money(gross_major * lookup.rate)
            wht = abs(tx.withholding_tax)
            wht_ccy = tx.withholding_currency or tx.currency
            wht_major, wht_ccy = to_major_units(wht, wht_ccy)
            wht_lookup = self.rates.t_minus_1(wht_ccy, transaction_day(tx.timestamp))
            wht_pln = money(wht_major * wht_lookup.rate)
            polish_tax = money(gross_pln * BELKA)
            credit = money(min(polish_tax, wht_pln))
            to_pay = money(max(D(0), polish_tax - credit))
            country = tx.country or country_from_isin(tx.isin)
            rows.append(
                DividendRow(
                    id=tx.id,
                    date=tx.timestamp.date().isoformat(),
                    symbol=tx.symbol,
                    isin=tx.isin,
                    name=tx.name,
                    broker=tx.broker,
                    country=country,
                    gross_pln=as_float(gross_pln),
                    withholding_pln=as_float(wht_pln),
                    polish_tax_19=as_float(polish_tax),
                    credit_pln=as_float(credit),
                    to_pay_pln=as_float(to_pay),
                    currency=gross_ccy,
                    nbp_rate=as_float(lookup.rate),
                    nbp_table_date=lookup.table_date.isoformat(),
                )
            )
        return rows

    def _interest(self, transactions: list[Transaction], tax_year: int, warnings: list[WarningItem]) -> list[InterestRow]:
        rows: list[InterestRow] = []
        for tx in transactions:
            if tx.type != TxType.INTEREST or tx.timestamp.year != tax_year:
                continue
            amount = abs(tx.price) if tx.price else abs(tx.quantity)
            major, ccy = to_major_units(amount, tx.currency)
            lookup = self.rates.t_minus_1(ccy, transaction_day(tx.timestamp))
            gross_pln = money(major * lookup.rate)
            wht = abs(tx.withholding_tax)
            wht_major, wht_ccy = to_major_units(wht, tx.withholding_currency or tx.currency)
            wht_lookup = self.rates.t_minus_1(wht_ccy, transaction_day(tx.timestamp))
            rows.append(
                InterestRow(
                    id=tx.id,
                    date=tx.timestamp.date().isoformat(),
                    broker=tx.broker,
                    gross_pln=as_float(gross_pln),
                    withholding_pln=as_float(money(wht_major * wht_lookup.rate)),
                    currency=ccy,
                    nbp_rate=as_float(lookup.rate),
                    nbp_table_date=lookup.table_date.isoformat(),
                    notes=tx.notes or tx.raw_action,
                )
            )
        return rows

    def _pit_zg(self, realizations, dividends: list[DividendRow], interest: list[InterestRow]) -> list[PitZgCountry]:
        bucket: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: D(0)))
        for row in realizations:
            country = row.country or "??"
            if country == "PL":
                continue
            bucket[country]["sec_rev"] += D(row.proceeds_pln)
            bucket[country]["sec_cost"] += D(row.cost_pln)
        for row in dividends:
            country = row.country or "??"
            if country == "PL":
                continue
            bucket[country]["div"] += D(row.gross_pln)
            bucket[country]["wht"] += D(row.withholding_pln)
        for row in interest:
            if D(row.gross_pln) == 0:
                continue
            bucket["??"]["int"] += D(row.gross_pln)
        result: list[PitZgCountry] = []
        for code, values in sorted(bucket.items(), key=lambda item: item[0]):
            income = money(values["sec_rev"] - values["sec_cost"])
            if all(v == 0 for v in values.values()):
                continue
            result.append(
                PitZgCountry(
                    country=code,
                    country_name=country_name(code),
                    securities_revenue_pln=as_float(values["sec_rev"]),
                    securities_costs_pln=as_float(values["sec_cost"]),
                    securities_income_pln=as_float(income if income > 0 else D(0)),
                    dividends_gross_pln=as_float(values["div"]),
                    dividends_withholding_pln=as_float(values["wht"]),
                    interest_gross_pln=as_float(values["int"]),
                )
            )
        return result
