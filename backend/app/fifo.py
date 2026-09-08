from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .isin import country_from_isin
from .models import OpenLot, Realization, Transaction, TxType, WarningItem
from .money import D, as_float, money
from .nbp import NbpClient, StaticRateClient, to_major_units, transaction_day


@dataclass
class Lot:
    buy: Transaction
    remaining: Decimal
    unit_cost_pln: Decimal
    allocated_fee_pln: Decimal
    nbp_rate: Decimal
    nbp_table_date: date
    price_major: Decimal
    currency_major: str


@dataclass
class FifoResult:
    realizations: list[Realization] = field(default_factory=list)
    open_lots: list[OpenLot] = field(default_factory=list)
    warnings: list[WarningItem] = field(default_factory=list)
    unmatched_sold_qty: Decimal = field(default_factory=lambda: D(0))


class FifoEngine:
    def __init__(self, rates: NbpClient | StaticRateClient):
        self.rates = rates

    def run(self, transactions: list[Transaction], tax_year: int) -> FifoResult:
        result = FifoResult()
        lots: dict[str, deque[Lot]] = defaultdict(deque)
        ordered = sorted(
            [tx for tx in transactions if tx.type in {TxType.BUY, TxType.SELL, TxType.SPLIT, TxType.TRANSFER_IN, TxType.TRANSFER_OUT}],
            key=lambda tx: (tx.timestamp, 0 if tx.type in {TxType.BUY, TxType.TRANSFER_IN, TxType.SPLIT} else 1, tx.id),
        )
        for tx in ordered:
            if tx.type in {TxType.BUY, TxType.TRANSFER_IN}:
                self._push_buy(lots, tx)
            elif tx.type == TxType.SPLIT:
                self._apply_split(lots, tx, result)
            elif tx.type in {TxType.SELL, TxType.TRANSFER_OUT}:
                self._consume_sell(lots, tx, tax_year, result)
        for queue in lots.values():
            for lot in queue:
                if lot.remaining <= 0:
                    continue
                remaining_cost = money(lot.remaining * lot.unit_cost_pln)
                result.open_lots.append(
                    OpenLot(
                        symbol=lot.buy.symbol,
                        isin=lot.buy.isin,
                        name=lot.buy.name,
                        broker=lot.buy.broker,
                        buy_date=lot.buy.timestamp.date().isoformat(),
                        quantity=as_float(lot.remaining),
                        price=as_float(lot.price_major),
                        currency=lot.currency_major,
                        cost_pln=as_float(remaining_cost),
                        nbp_rate=as_float(lot.nbp_rate),
                        nbp_table_date=lot.nbp_table_date.isoformat(),
                    )
                )
        result.open_lots.sort(key=lambda row: (row.broker, row.symbol, row.buy_date))
        return result

    def _push_buy(self, lots: dict[str, deque[Lot]], tx: Transaction) -> None:
        qty = abs(tx.quantity)
        if qty <= 0:
            return
        price_major, ccy = to_major_units(tx.price, tx.currency)
        lookup = self.rates.t_minus_1(ccy, transaction_day(tx.timestamp))
        gross_pln = money(qty * price_major * lookup.rate)
        fee_pln = self._fee_pln(tx)
        unit_cost = money((gross_pln + fee_pln) / qty) if qty else D(0)
        lots[tx.lot_key].append(
            Lot(
                buy=tx,
                remaining=qty,
                unit_cost_pln=unit_cost,
                allocated_fee_pln=fee_pln,
                nbp_rate=lookup.rate,
                nbp_table_date=lookup.table_date,
                price_major=price_major,
                currency_major=ccy,
            )
        )

    def _apply_split(self, lots: dict[str, deque[Lot]], tx: Transaction, result: FifoResult) -> None:
        ratio = tx.quantity
        if ratio <= 0:
            result.warnings.append(
                WarningItem(level="warning", code="split_ratio", message=f"Ignored stock split for {tx.symbol}: ratio was {ratio}.")
            )
            return
        matched = False
        for key, queue in lots.items():
            if not key.endswith(f"|{tx.instrument_key}"):
                continue
            matched = True
            for lot in queue:
                lot.remaining = money(lot.remaining * ratio)
                lot.unit_cost_pln = money(lot.unit_cost_pln / ratio)
                lot.price_major = money(lot.price_major / ratio)
        if not matched:
            result.warnings.append(
                WarningItem(
                    level="warning",
                    code="split_no_lots",
                    message=f"Stock split for {tx.symbol} had no open lots to adjust.",
                )
            )

    def _consume_sell(self, lots: dict[str, deque[Lot]], tx: Transaction, tax_year: int, result: FifoResult) -> None:
        remaining = abs(tx.quantity)
        if remaining <= 0:
            return
        price_major, ccy = to_major_units(tx.price, tx.currency)
        sell_lookup = self.rates.t_minus_1(ccy, transaction_day(tx.timestamp))
        fee_pln = self._fee_pln(tx)
        fee_per_share = (fee_pln / remaining) if remaining else D(0)
        queue = lots[tx.lot_key]
        while remaining > 0 and queue:
            lot = queue[0]
            taken = min(lot.remaining, remaining)
            proceeds = money(taken * price_major * sell_lookup.rate)
            cost = money(taken * lot.unit_cost_pln)
            sell_fees = money(taken * fee_per_share)
            net_proceeds = money(proceeds - sell_fees)
            if tx.timestamp.year == tax_year and tx.type == TxType.SELL:
                result.realizations.append(
                    Realization(
                        sell_id=tx.id,
                        symbol=tx.symbol or lot.buy.symbol,
                        isin=tx.isin or lot.buy.isin,
                        name=tx.name or lot.buy.name,
                        broker=tx.broker,
                        sell_date=tx.timestamp.date().isoformat(),
                        buy_date=lot.buy.timestamp.date().isoformat(),
                        quantity=as_float(taken),
                        proceeds_pln=as_float(net_proceeds),
                        cost_pln=as_float(cost),
                        fees_pln=as_float(sell_fees),
                        gain_pln=as_float(money(net_proceeds - cost)),
                        sell_currency=ccy,
                        sell_price=as_float(price_major),
                        buy_price=as_float(lot.price_major),
                        buy_currency=lot.currency_major,
                        nbp_sell_rate=as_float(sell_lookup.rate),
                        nbp_buy_rate=as_float(lot.nbp_rate),
                        nbp_sell_table_date=sell_lookup.table_date.isoformat(),
                        nbp_buy_table_date=lot.nbp_table_date.isoformat(),
                        country=tx.country or lot.buy.country or country_from_isin(tx.isin or lot.buy.isin),
                    )
                )
            lot.remaining = money(lot.remaining - taken)
            remaining = money(remaining - taken)
            if lot.remaining <= 0:
                queue.popleft()
        if remaining > 0:
            result.unmatched_sold_qty += remaining
            proceeds = money(remaining * price_major * sell_lookup.rate)
            sell_fees = money(remaining * fee_per_share)
            net_proceeds = money(proceeds - sell_fees)
            if tx.timestamp.year == tax_year and tx.type == TxType.SELL:
                result.realizations.append(
                    Realization(
                        sell_id=tx.id,
                        symbol=tx.symbol,
                        isin=tx.isin,
                        name=tx.name,
                        broker=tx.broker,
                        sell_date=tx.timestamp.date().isoformat(),
                        buy_date="",
                        quantity=as_float(remaining),
                        proceeds_pln=as_float(net_proceeds),
                        cost_pln=0.0,
                        fees_pln=as_float(sell_fees),
                        gain_pln=as_float(net_proceeds),
                        sell_currency=ccy,
                        sell_price=as_float(price_major),
                        buy_price=0.0,
                        buy_currency=ccy,
                        nbp_sell_rate=as_float(sell_lookup.rate),
                        nbp_buy_rate=0.0,
                        nbp_sell_table_date=sell_lookup.table_date.isoformat(),
                        nbp_buy_table_date="",
                        country=tx.country or country_from_isin(tx.isin),
                    )
                )
                result.warnings.append(
                    WarningItem(
                        level="error",
                        code="missing_cost_basis",
                        message=(
                            f"{tx.symbol}: sold {as_float(remaining)} shares on {tx.timestamp.date().isoformat()} "
                            "without a matching purchase. Cost was treated as 0 PLN — import earlier history."
                        ),
                        detail=tx.id,
                    )
                )

    def _fee_pln(self, tx: Transaction) -> Decimal:
        fee = abs(tx.fee)
        if fee <= 0:
            return D(0)
        fee_ccy = tx.fee_currency or tx.currency
        amount, ccy = to_major_units(fee, fee_ccy)
        lookup = self.rates.t_minus_1(ccy, transaction_day(tx.timestamp))
        return money(amount * lookup.rate)
