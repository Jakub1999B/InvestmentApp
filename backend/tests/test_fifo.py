from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.fifo import FifoEngine
from app.models import Transaction, TxType
from app.money import D
from app.nbp import StaticRateClient
from app.tax import TaxCalculator


def _tx(**kwargs) -> Transaction:
    return Transaction(**kwargs)


def test_fifo_matches_oldest_lot_first():
    rates = StaticRateClient({"USD": Decimal("4.00"), "EUR": Decimal("4.30"), "GBP": Decimal("5.00")})
    txs = [
        _tx(id="b1", broker="t", timestamp=datetime(2024, 1, 10, 12, 0), type=TxType.BUY, symbol="AAPL", isin="US0378331005", quantity=D(10), price=D(100), currency="USD"),
        _tx(id="b2", broker="t", timestamp=datetime(2024, 6, 10, 12, 0), type=TxType.BUY, symbol="AAPL", isin="US0378331005", quantity=D(5), price=D(120), currency="USD"),
        _tx(id="s1", broker="t", timestamp=datetime(2025, 3, 10, 12, 0), type=TxType.SELL, symbol="AAPL", isin="US0378331005", quantity=D(12), price=D(150), currency="USD"),
    ]
    result = FifoEngine(rates).run(txs, tax_year=2025)
    assert len(result.realizations) == 2
    first, second = result.realizations
    assert first.quantity == 10
    assert first.cost_pln == 4000
    assert first.proceeds_pln == 6000
    assert second.quantity == 2
    assert second.cost_pln == 960
    assert second.proceeds_pln == 1200
    assert len(result.open_lots) == 1
    assert result.open_lots[0].quantity == 3


def test_tax_rounds_belka_to_full_zloty():
    rates = StaticRateClient({"USD": Decimal("4.00")})
    txs = [
        _tx(id="b1", broker="t", timestamp=datetime(2024, 1, 10), type=TxType.BUY, symbol="AAPL", isin="US0378331005", quantity=D(10), price=D(100), currency="USD"),
        _tx(id="b2", broker="t", timestamp=datetime(2024, 6, 10), type=TxType.BUY, symbol="AAPL", isin="US0378331005", quantity=D(5), price=D(120), currency="USD"),
        _tx(id="s1", broker="t", timestamp=datetime(2025, 3, 10), type=TxType.SELL, symbol="AAPL", isin="US0378331005", quantity=D(12), price=D(150), currency="USD"),
        _tx(
            id="d1",
            broker="t",
            timestamp=datetime(2025, 5, 1),
            type=TxType.DIVIDEND,
            symbol="AAPL",
            isin="US0378331005",
            quantity=D(3),
            price=D(1),
            currency="USD",
            withholding_tax=D(0.45),
            withholding_currency="USD",
            country="US",
        ),
    ]
    report = TaxCalculator(rates).calculate(txs, tax_year=2025)
    assert report.revenue_pln == 7200
    assert report.costs_pln == 4960
    assert report.income_pln == 2240
    assert report.tax_base_pln == 2240
    assert report.capital_gains_tax_pln == 426
    assert report.dividends_gross_pln == 12
    assert report.pit38.field_72_pit_zg_count >= 1


def test_missing_history_flags_zero_cost():
    rates = StaticRateClient({"USD": Decimal("4.00")})
    txs = [
        _tx(id="s1", broker="t", timestamp=datetime(2025, 3, 10), type=TxType.SELL, symbol="AAPL", quantity=D(2), price=D(150), currency="USD"),
    ]
    result = FifoEngine(rates).run(txs, tax_year=2025)
    assert result.unmatched_sold_qty == D(2)
    assert result.realizations[0].cost_pln == 0
    assert any(w.code == "missing_cost_basis" for w in result.warnings)


def test_buy_fees_increase_cost_basis():
    rates = StaticRateClient({"USD": Decimal("4.00")})
    txs = [
        _tx(id="b1", broker="t", timestamp=datetime(2024, 1, 10), type=TxType.BUY, symbol="AAPL", quantity=D(10), price=D(100), currency="USD", fee=D(10), fee_currency="USD"),
        _tx(id="s1", broker="t", timestamp=datetime(2025, 3, 10), type=TxType.SELL, symbol="AAPL", quantity=D(10), price=D(100), currency="USD"),
    ]
    result = FifoEngine(rates).run(txs, tax_year=2025)
    assert result.realizations[0].cost_pln == 4040
    assert result.realizations[0].gain_pln == -40
